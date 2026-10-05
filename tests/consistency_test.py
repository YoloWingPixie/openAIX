import copy
import json
from pathlib import Path
import sys
import unittest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.contract import contained_interval
from openaix.check.validate import ContractError, validate_document, export_document, import_document, schemas


def scheduled():
    return {"start": "2026-10-05T00:00:00Z", "end": "2026-10-12T00:00:00Z",
            "schedule": {"time_reference": "UTC", "periods": [
                {"weekdays": ["mon", "wed"], "start_time": "08:00:00", "end_time": "16:00:00", "end_day_offset": 0}],
                "exclusions": [{"start": "2026-10-05T12:00:00Z", "end": "2026-10-05T13:00:00Z"}]}}


class ConsistencyTests(unittest.TestCase):
    def test_dcs_shapes_resolve_through_the_public_geometry_union(self):
        records, registry = schemas()
        schema = {"$ref": records["common"]["$id"] + "#/$defs/Geometry"}
        validator = Draft202012Validator(schema, registry=registry)
        for kind, dimensions in (("rectangle", {"width_m": 2000, "height_m": 1000}),
                                 ("ellipse", {"north_radius_m": 1000, "east_radius_m": 500})):
            with self.subTest(kind=kind):
                geometry = {"kind": kind, "center": {"latitude": 37, "longitude": -115}, **dimensions,
                            "extensions": {"sim": {"dcs": {"projection": "Syria", "angle_deg": 0}}}}
                validator.validate(geometry)

    def test_scheduled_airspace_and_unlimited_ceiling_round_trip(self):
        document = json.loads((ROOT / "examples/airspace-class-b.json").read_text())
        document["active"] = scheduled()
        for part in document["components"]:
            part.pop("active", None)
        document["components"][-1]["upper_limit"] = {"unlimited": True}
        document["components"][-1]["minimum_limit"] = {"value": 2000, "unit": "ft", "reference": "AGL"}
        catalogue = json.loads((ROOT / "examples/resources-kden.json").read_text())
        self.assertEqual(import_document(export_document(document, resource_document=catalogue), resource_document=catalogue), document)

    def test_parent_schedule_excludes_closed_days_and_exceptions(self):
        parent = scheduled()
        cases = [("2026-10-05T08:00:00Z", "2026-10-05T12:00:00Z", True),
                 ("2026-10-05T12:00:00Z", "2026-10-05T14:00:00Z", False),
                 ("2026-10-06T08:00:00Z", "2026-10-06T09:00:00Z", False),
                 ("2026-10-07T15:00:00Z", "2026-10-07T16:00:00Z", True),
                 ("2026-10-07T15:00:00Z", "2026-10-07T17:00:00Z", False)]
        for start, end, allowed in cases:
            with self.subTest(start=start, end=end):
                child = {"start": start, "end": end}
                if allowed:
                    contained_interval(child, parent, None, ())
                else:
                    with self.assertRaises(ContractError):
                        contained_interval(child, parent, None, ())

    def test_vertical_overrides_raise_resolved_limits_without_replacing_higher_values(self):
        document = json.loads((ROOT / "examples/airspace-class-b.json").read_text())
        part = document["components"][1]
        part["minimum_limit"] = {"value": 5000, "unit": "ft", "reference": "MSL"}
        part["maximum_limit"] = {"value": 1000, "unit": "ft", "reference": "MSL"}
        validate_document(document)
        part["minimum_limit"]["value"] = 15000
        with self.assertRaises(ContractError):
            validate_document(document)
        part["maximum_limit"]["value"] = 20000
        validate_document(document)

    def test_overnight_and_recurring_children_follow_start_weekday(self):
        parent = scheduled()
        parent["schedule"] = {"time_reference": "UTC", "periods": [
            {"weekdays": ["mon"], "start_time": "22:00:00", "end_time": "02:00:00", "end_day_offset": 1}]}
        contained_interval({"start": "2026-10-06T00:00:00Z", "end": "2026-10-06T02:00:00Z"}, parent, None, ())
        child = copy.deepcopy(parent)
        child["schedule"]["periods"][0]["start_time"] = "23:00:00"
        contained_interval(child, parent, None, ())
        child["schedule"]["periods"][0]["weekdays"] = ["tue"]
        with self.assertRaises(ContractError):
            contained_interval(child, parent, None, ())

    def test_invalid_weekly_durations_and_exclusions_fail(self):
        document = json.loads((ROOT / "examples/airspace-class-b.json").read_text())
        for part in document["components"]:
            part.pop("active", None)
        mutations = [lambda w: w["schedule"]["periods"][0].update(end_time="08:00:00"),
                     lambda w: w["schedule"]["periods"][0].update(end_day_offset=1),
                     lambda w: w["schedule"]["exclusions"][0].update(end="2026-10-13T00:00:00Z")]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                document["active"] = scheduled()
                mutate(document["active"])
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_two_bindings_cannot_disagree_on_the_identity_of_one_object(self):
        document = json.loads((ROOT / "examples/airfield.json").read_text())
        bindings = [{"kind": "airbase", "name": "Muwaffaq Salti", "object_id": 12},
                    {"kind": "airbase", "name": "Muwaffaq Salti", "object_id": 12}]
        document["extensions"] = {"sim": {"dcs": {"bindings": bindings}}}
        catalogue = json.loads((ROOT / "examples/resources-kden.json").read_text())
        validate_document(document, resource_document=catalogue)
        bindings[1]["object_id"] = 13
        with self.assertRaisesRegex(ContractError, "conflicting bindings"):
            validate_document(document, resource_document=catalogue)
        bindings[1]["mission_id"] = "different-mission"
        bindings[0]["mission_id"] = "source-mission"
        validate_document(document, resource_document=catalogue)

    def test_unrecognized_native_metadata_does_not_become_domain_geometry(self):
        document = json.loads((ROOT / "examples/airfield.json").read_text())
        document["extensions"] = {"sim": {"dcs": {"bindings": [{"kind": "drawing", "name": "Airfield label", "primitive_type": "TextBox", "text": "Airfield",
                                                                "native_fields": {"components": "native metadata", "lower": "low", "upper": "high"}}]}}}
        catalogue = json.loads((ROOT / "examples/resources-kden.json").read_text())
        self.assertEqual(import_document(export_document(document, resource_document=catalogue), resource_document=catalogue), document)
