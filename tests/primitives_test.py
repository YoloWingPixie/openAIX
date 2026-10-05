import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, validate_document


def example(name):
    return json.loads((ROOT / "examples" / name).read_text())


SURFACE, UNLIMITED = {"surface": True}, {"unlimited": True}
FL220 = {"value": 220, "unit": "flight_level", "reference": "FL"}


class VerticalLimitTests(unittest.TestCase):
    def order(self):
        return example("aco-oir.maximal.json")

    def test_orbit_and_route_blocks_accept_surface_to_unlimited(self):
        for measure in ("falcon", "south-transit"):
            with self.subTest(measure=measure):
                document = self.order()
                document["resources"]["control_measures"][measure]["altitude"] = {"lower": SURFACE, "upper": UNLIMITED}
                validate_document(document)

    def test_surface_floor_and_unlimited_ceiling_bound_any_altitude(self):
        document = self.order()
        orbit = document["resources"]["control_measures"]["falcon"]
        orbit["altitude"] = {"lower": SURFACE, "upper": FL220}
        validate_document(document)
        orbit["altitude"] = {"lower": FL220, "upper": UNLIMITED}
        validate_document(document)

    def test_unlimited_floor_and_surface_ceiling_are_rejected(self):
        for block in ({"lower": UNLIMITED, "upper": UNLIMITED}, {"lower": FL220, "upper": SURFACE},
                      {"lower": UNLIMITED, "upper": FL220}, {"lower": SURFACE, "upper": SURFACE}):
            with self.subTest(block=block):
                document = self.order()
                document["resources"]["control_measures"]["falcon"]["altitude"] = block
                with self.assertRaises(ContractError) as raised:
                    validate_document(document)
                self.assertEqual(raised.exception.path, "/resources/control_measures/falcon/altitude")

    def test_airspace_component_limits_use_surface_and_unlimited(self):
        document = self.order()
        component = document["resources"]["control_measures"]["rescue-reservation"]["components"][0]
        component.update({"lower_limit": SURFACE, "upper_limit": UNLIMITED})
        validate_document(document)
        for lower, upper in ((UNLIMITED, UNLIMITED), (SURFACE, SURFACE), (FL220, FL220)):
            with self.subTest(lower=lower, upper=upper):
                invalid = copy.deepcopy(document)
                invalid["resources"]["control_measures"]["rescue-reservation"]["components"][0].update({"lower_limit": lower, "upper_limit": upper})
                with self.assertRaises(ContractError):
                    validate_document(invalid)

    def test_maximum_limit_raises_a_surface_based_component_ceiling(self):
        document = self.order()
        component = document["resources"]["control_measures"]["rescue-reservation"]["components"][0]
        component.update({"lower_limit": SURFACE, "upper_limit": {"value": 3000, "unit": "ft", "reference": "MSL"},
                          "maximum_limit": {"value": 5000, "unit": "ft", "reference": "MSL"}})
        validate_document(document)


class CodedValueTests(unittest.TestCase):
    def test_store_load_laser_code_must_be_a_valid_prf_code(self):
        document = example("resources.json")
        store = document["resources"]["scls"]["a10-cas"]["stores"][0]
        store["laser_code"] = "1688"
        validate_document(document)
        for code in ("8888", "1811", "1190", "1111X"):
            with self.subTest(code=code):
                store["laser_code"] = code
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_fac_laser_codes_share_the_same_rule(self):
        document, resources = example("fac.json"), example("resources.json")
        validate_document(document, resource_document=resources)
        for field, value in (("default_laser_code", "8888"), ("laser_codes", ["1688", "1190"])):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(document))
                changed[field] = value
                with self.assertRaises(ContractError) as error:
                    validate_document(changed, resource_document=resources)
                self.assertTrue(error.exception.path.startswith("/" + field))

    def test_runway_designators_accept_type_suffixes_and_reject_impossible_headings(self):
        from openaix.check.navigation import reciprocal
        document = example("runway.json")
        document.pop("airfield")
        document.pop("resources_ref")
        document["ends"][0].pop("localizer")
        for designator in ("36W", "09G", "18L", "01", "27S", "04U"):
            with self.subTest(designator=designator):
                document["ends"][0]["designator"] = designator
                document["ends"][1]["designator"] = reciprocal(designator)
                document["designator"] = designator + "/" + reciprocal(designator)
                validate_document(document)
        for designator in ("00", "37", "9", "09X", "40L"):
            with self.subTest(designator=designator):
                document["ends"][0]["designator"] = designator
                document["designator"] = designator + "/" + document["ends"][1]["designator"]
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_length_accepts_feet_and_kilometres(self):
        document = example("aco-oir.maximal.json")
        geometry = document["resources"]["control_measures"]["rescue-reservation"]["components"][0]["geometry"]
        self.assertIn("radius", geometry)
        for unit in ("ft", "km"):
            with self.subTest(unit=unit):
                geometry["radius"] = {"value": 12, "unit": unit}
                validate_document(document)
        geometry["radius"] = {"value": 12, "unit": "mi"}
        with self.assertRaises(ContractError):
            validate_document(document)


if __name__ == "__main__":
    unittest.main()
