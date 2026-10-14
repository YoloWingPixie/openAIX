"""Territory records and air defense sectors: affiliation, required shape, country codes and optional vertical limits."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, validate_document


RESOURCES = json.loads((ROOT / "examples/resources.json").read_text())
MEASURES = RESOURCES["resources"]["control_measures"]


def territory(identifier):
    return {"$schema": "urn:openaix:schema:territory:0.1.0-draft.2", **deepcopy(MEASURES[identifier])}


class TerritoryTests(unittest.TestCase):
    def test_hostile_and_friendly_territories_validate(self):
        for identifier, affiliation in (("isis-held", "hostile"), ("jordan", "friend")):
            with self.subTest(territory=identifier):
                document = territory(identifier)
                self.assertEqual(document["affiliation"], affiliation)
                validate_document(document)

    def test_shape_and_affiliation_are_required(self):
        for field in ("geometry", "affiliation"):
            document = territory("jordan")
            document.pop(field)
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_document(document)

    def test_affiliation_and_country_codes_are_closed_values(self):
        for field, value in (("affiliation", "unknown"), ("affiliation", "enemy"), ("countries", ["SY"]), ("countries", ["syr"]),
                             ("countries", ["JOR", "JOR"]), ("countries", [])):
            document = territory("jordan")
            document[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                validate_document(document)

    def test_territory_vertical_limits_are_optional(self):
        hostile = territory("isis-held")
        self.assertEqual(hostile["lower_limit"], {"value": 1000, "unit": "ft", "reference": "MSL"})
        self.assertEqual(hostile["upper_limit"], {"unlimited": True})
        friendly = territory("jordan")
        self.assertNotIn("lower_limit", friendly)
        self.assertNotIn("upper_limit", friendly)
        for limits in ({}, {"lower_limit": {"surface": True}}, {"upper_limit": {"value": 10000, "unit": "ft", "reference": "MSL"}},
                       {"lower_limit": {"value": 500, "unit": "ft", "reference": "AGL"}, "upper_limit": {"unlimited": True}}):
            with self.subTest(limits=limits):
                validate_document({**territory("jordan"), **limits})

    def test_territory_rejects_bad_limits_altitude_block_and_curves(self):
        for field, value in (("altitude", {"lower": {"surface": True}, "upper": {"unlimited": True}}),
                             ("lower_limit", {"value": 1000}), ("upper_limit", {"unlimited": False}),
                             ("geometry", {"kind": "circle", "center": {"latitude": 31.5, "longitude": 37.0}, "radius": {"value": 20, "unit": "nm"}})):
            document = territory("jordan")
            document[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_document(document)

    def test_territory_floor_must_be_below_its_ceiling(self):
        document = territory("isis-held")
        document["upper_limit"] = {"value": 500, "unit": "ft", "reference": "MSL"}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_coalition_is_not_a_territory_field(self):
        document = territory("isis-held")
        document["coalition"] = "red"
        with self.assertRaises(ContractError):
            validate_document(document)


class AirDefenseSectorTests(unittest.TestCase):
    def test_air_defense_sector_is_a_volume_code_from_jp_3_01(self):
        catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
        entry = next(item for item in catalogue["types"] if item["code"] == "ADS")
        self.assertEqual(entry["schema"], "urn:openaix:schema:measure-volume:0.1.0-draft.2")
        self.assertEqual(entry["category"], "adm")
        self.assertEqual(entry["definition_source"]["source"], "joint-jp-3-01-2017")
        self.assertIn("air defence region", entry["definition"])

    def test_sector_from_the_surface_without_upper_limit_validates(self):
        document = {"$schema": "urn:openaix:schema:measure-volume:0.1.0-draft.2", **deepcopy(MEASURES["ads-north"]),
                    "resources_ref": {"id": RESOURCES["meta"]["id"], "revision": RESOURCES["meta"]["revision"]}}
        self.assertEqual(document["components"][0]["lower_limit"], {"surface": True})
        self.assertEqual(document["components"][0]["upper_limit"], {"unlimited": True})
        validate_document(document, resource_document=RESOURCES)


if __name__ == "__main__":
    unittest.main()
