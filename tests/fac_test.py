import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, validate_document


class FacTests(unittest.TestCase):
    def test_point_references_match_initial_or_egress_roles(self):
        for field, accepted, rejected in (("initial_points", ("initial", "fix"), ("control", "egress")),
                                          ("egress_points", ("egress", "gate", "fix"), ("control", "initial"))):
            document = json.loads((ROOT / "examples/fac.json").read_text())
            resources = json.loads((ROOT / "examples/resources.json").read_text())
            point = json.loads((ROOT / "examples/measures/ip.json").read_text())
            resources["resources"]["control_measures"][point["id"]] = point
            document[field] = [{"kind": "control_measure", "id": point["id"]}]
            for role in accepted:
                with self.subTest(field=field, accepted=role):
                    point["roles"] = [role]
                    validate_document(document, resource_document=resources)
            for role in rejected:
                with self.subTest(field=field, rejected=role):
                    point["roles"] = [role]
                    with self.assertRaises(ContractError) as error:
                        validate_document(document, resource_document=resources)
                    self.assertEqual(error.exception.path, f"/{field}/0/id")

    def test_equipment_coordinate_source_and_consumer_behavior_round_trip_together(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        for field in ("resources_ref", "channels", "initial_points", "egress_points"):
            document.pop(field, None)
        document.update({"coordinate_source": "lrf", "default_laser_code": "1688", "smoke_color": "white",
                         "equipment": [{"id": "lrf-1", "kind": "laser_rangefinder", "quantity": 1, "available": True,
                                        "max_range": {"value": 8, "unit": "km"}, "horizontal_accuracy": {"value": 10, "unit": "m"}}],
                         "extensions": {"org.example.jtac": {"search_range_m": 10000, "laser_range_m": 8000}}})
        self.assertEqual(import_document(export_document(document)), document)
        changed = json.loads(json.dumps(document))
        changed["coordinate_source"] = "gps"
        with self.assertRaises(ContractError):
            validate_document(changed)

    def test_target_location_error_name_and_application_tuning_are_not_portable_fields(self):
        # DOCTRINE-06: `tle` held a coordinate source, not a CAT I-VI target location error; ORDERS-05: application tuning is namespaced.
        document = json.loads((ROOT / "examples/fac.json").read_text())
        resources = json.loads((ROOT / "examples/resources.json").read_text())
        validate_document(document, resource_document=resources)
        for field, value in (("tle", "lrf"), ("search_range_m", 10000), ("laser_range_m", 8000), ("availability", {"start": "2026-10-02T13:00:00Z", "end": "2026-10-02T15:00:00Z"})):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(document))
                changed[field] = value
                with self.assertRaises(ContractError) as error:
                    validate_document(changed, resource_document=resources)
                self.assertEqual(error.exception.code, "schema constraint: additionalProperties")

    def test_equipment_ranges_use_typed_lengths(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        resources = json.loads((ROOT / "examples/resources.json").read_text())
        for value in (8000, {"value": 8000}, {"value": -1, "unit": "m"}):
            with self.subTest(value=value):
                changed = json.loads(json.dumps(document))
                changed["equipment"][0]["max_range"] = value
                with self.assertRaises(ContractError):
                    validate_document(changed, resource_document=resources)
        changed = json.loads(json.dumps(document))
        changed["equipment"][0]["max_range_m"] = 8000
        with self.assertRaises(ContractError):
            validate_document(changed, resource_document=resources)

    def test_supplied_equipment_and_dcs_observers_are_validated(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        for field in ("resources_ref", "channels", "initial_points", "egress_points"):
            document.pop(field, None)
        document["equipment"] = [{"id": "lrf-1", "kind": "laser_rangefinder", "horizontal_accuracy": {"value": -1, "unit": "m"}}]
        with self.assertRaises(ContractError):
            validate_document(document)
        document.pop("equipment")
        # Observers are not DCS data of the controller; an application keeps them in its own namespace.
        document["extensions"]["sim"]["dcs"]["observers"] = [{"kind": "unit", "name": "OIR Axeman OP"}]
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_coalition_is_dcs_data_not_a_core_field(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        resources = json.loads((ROOT / "examples/resources.json").read_text())
        self.assertEqual(document["extensions"]["sim"]["dcs"]["coalition"], "blue")
        changed = json.loads(json.dumps(document))
        changed["coalition"] = "blue"
        with self.assertRaises(ContractError) as error:
            validate_document(changed, resource_document=resources)
        self.assertEqual(error.exception.code, "schema constraint: additionalProperties")

    def test_schema_has_no_application_settings(self):
        schema = json.loads((ROOT / "schemas/fac.schema.json").read_text())
        self.assertNotIn("VoxJTACSettings", schema.get("$defs", {}))
        self.assertNotIn("vox", json.dumps(schema).lower())
