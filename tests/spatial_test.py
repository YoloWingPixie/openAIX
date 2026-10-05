import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


class SpatialTests(unittest.TestCase):
    def test_orbit_carries_no_service_role_or_tanker_fields(self):
        document = example("orbit")
        self.assertEqual(document["type"], "ORBIT")
        self.assertEqual(import_document(export_document(document)), document)
        for field, value in (("refueling_method", "boom"), ("role", "cap")):
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_document(dict(document, **{field: value}))

    def test_airspace_classes_share_one_contract(self):
        document = example("airspace-class-b")
        for code in "ABCDEFG":
            with self.subTest(code=code):
                document.update(airspace_type="Class" + code, airspace_class_code=code)
                self.assertEqual(import_document(export_document(document)), document)
        self.assertEqual(example("airspace-class-d")["$schema"], document["$schema"])

    def test_shelves_retain_independent_floors_and_ceilings(self):
        document = example("airspace-class-b")
        self.assertGreaterEqual(len(document["components"]), 3)
        self.assertGreater(len({json.dumps(part["lower_limit"]) for part in document["components"]}), 1)
        for field in ("lower_limit", "upper_limit", "geometry"):
            invalid = copy.deepcopy(document)
            del invalid["components"][1][field]
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_document(invalid)
        invalid = copy.deepcopy(document)
        invalid["components"][1]["lower_limit"] = {"value": 11000, "unit": "ft", "reference": "MSL"}
        with self.assertRaises(ContractError):
            validate_document(invalid)

    def test_measure_activation_is_explicit_and_ordered(self):
        for path in sorted((ROOT / "examples/measures").glob("*.json")):
            document = json.loads(path.read_text())
            if document["type"] in {"NAVAID", "AIRWAY"}:
                continue
            self.assertTrue("active" in document, path.name + ": activation missing")
            if "start" in document["active"]:
                document["active"]["end"] = document["active"]["start"]
                with self.subTest(example=path.name), self.assertRaises(ContractError):
                    validate_document(document)

    def test_subtraction_requires_a_preceding_volume(self):
        document = example("measures/hidacz")
        self.assertEqual(document["components"][1]["operation"], "subtract")
        validate_document(document)
        document["components"].reverse()
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_distinct_roles_can_reference_the_same_orbit(self):
        document = example("orbit-assignments")
        self.assertEqual({item["role"] for item in document["assignments"]}, {"cap", "aew"})
        self.assertEqual(len({item["measure"] for item in document["assignments"]}), 1)
        self.assertEqual(import_document(export_document(document)), document)

    def test_components_carry_no_raw_source_bookkeeping(self):
        for field, value in (("source_fields", {"lower_limit": "GND  "}), ("raw_records", ["S" + " " * 131]),
                             ("published_boundary", [{"sequence_number": 10, "path": "circle"}])):
            document = example("airspace-class-b")
            document["components"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_document(document)


if __name__ == "__main__":
    unittest.main()
