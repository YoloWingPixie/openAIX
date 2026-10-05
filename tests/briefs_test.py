"""ATO mission briefs, the AI, SCAR, FAC(A), air assault and airdrop roles, emitters and typed target lists."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


def mission(document, identifier):
    return next(item for item in document["missions"] if item["id"] == identifier)


class BriefTests(unittest.TestCase):
    def setUp(self):
        self.ato, self.resources = example("ato-oir"), example("resources")

    def rejects(self, document, resources=None, path=None):
        with self.assertRaises(ContractError) as error:
            validate_document(document, resource_document=resources or self.resources)
        if path:
            self.assertEqual(error.exception.path, path)

    def test_every_oir_tasking_has_a_brief(self):
        self.assertEqual([item["id"] for item in self.ato["missions"] if "brief" not in item["tasking"]], [])

    def test_new_roles_are_in_the_example(self):
        roles = {(item["tasking"]["kind"], item["tasking"].get("role") or item["tasking"].get("mission_type")) for item in self.ato["missions"]}
        for role in (("preplanned_attack", "air_interdiction"), ("counterland_control", "scar"), ("counterland_control", "fac_a"),
                     ("transport", "air_assault"), ("transport", "airdrop")):
            self.assertIn(role, roles)

    def test_point_references_need_the_matching_role(self):
        document = deepcopy(self.ato)
        brief = mission(document, "strike-cobalt")["tasking"]["brief"]
        brief["initial_points"] = [{"kind": "control_measure", "id": "cedar"}]
        self.rejects(document)

    def test_brief_references_resolve(self):
        for change in (lambda brief: brief["sead"]["emitters"][0].update(emitter="missing"),
                       lambda brief: brief.update(threat_emitters=["missing"]),
                       lambda brief: brief["sead"].update(protected_missions=["missing"])):
            document = deepcopy(self.ato)
            change(mission(document, "sead-cobalt")["tasking"]["brief"])
            with self.subTest(change=change):
                self.rejects(document)

    def test_air_assault_and_airdrop_need_their_brief_data(self):
        document = deepcopy(self.ato)
        del mission(document, "assault-nickel")["tasking"]["brief"]["air_assault"]
        self.rejects(document)
        document = deepcopy(self.ato)
        mission(document, "drop-tin")["tasking"]["delivery_method"] = "land"
        self.rejects(document)
        document = deepcopy(self.ato)
        del mission(document, "airlift-prince-hassan")["tasking"]["destination"]
        self.rejects(document)

    def test_air_movement_line_uses_pickup_and_landing_zone_measures(self):
        document = deepcopy(self.ato)
        line = mission(document, "assault-nickel")["tasking"]["brief"]["air_assault"]["air_movement_table"][0]
        line["landing_zone"] = {"kind": "control_measure", "id": "pz-sage"}
        self.rejects(document)

    def test_scar_and_faca_take_their_own_brief(self):
        document = deepcopy(self.ato)
        scar = mission(document, "scar-gainful")["tasking"]
        scar["brief"] = deepcopy(mission(document, "faca-nail")["tasking"]["brief"])
        self.rejects(document)


class EmitterTests(unittest.TestCase):
    def setUp(self):
        self.resources = example("resources")

    def emitters(self):
        return self.resources["resources"]["emitters"]

    def test_oir_emitters_use_dcs_alic_codes(self):
        codes = {emitter["system_id"]: emitter["extensions"]["sim"]["dcs"]["alic_code"] for emitter in self.emitters().values()}
        self.assertEqual(codes, {"SA-6": 108, "SA-3": 123, "SA-8": 117})

    def test_missile_arc_starts_at_the_emitter(self):
        self.emitters()["sa6-gainful"]["position"] = {"latitude": 37.60, "longitude": -115.66}
        with self.assertRaises(ContractError) as error:
            validate_document(self.resources)
        self.assertEqual(error.exception.path, "/resources/emitters/sa6-gainful/measures/0/id")

    def test_emitter_is_inside_its_engagement_zone(self):
        self.emitters()["sa3-zinc"]["position"] = {"latitude": 38.10, "longitude": -116.02}
        with self.assertRaises(ContractError):
            validate_document(self.resources)

    def test_minimum_range_is_below_the_maximum(self):
        self.emitters()["sa8-nickel"]["min_engagement_range"] = {"value": 12, "unit": "km"}
        with self.assertRaises(ContractError):
            validate_document(self.resources)

    def test_emitter_needs_a_position_or_a_binding(self):
        emitter = self.emitters()["sa8-nickel"]
        del emitter["position"]
        del emitter["extensions"]
        with self.assertRaises(ContractError):
            validate_document(self.resources)
        emitter["extensions"] = {"sim": {"dcs": {"bindings": [{"kind": "group", "name": "OIR Nickel SA-8"}]}}}
        validate_document(self.resources)

    def test_emitter_measures_are_air_defence_measures(self):
        self.emitters()["sa8-nickel"]["measures"] = [{"kind": "control_measure", "id": "cobalt-box"}]
        with self.assertRaises(ContractError):
            validate_document(self.resources)


class TargetListTests(unittest.TestCase):
    def test_target_list_references_resolve_in_the_linked_catalogue(self):
        resources = example("resources")
        for name, field, value in (("tst", "engagement_authority", "Kingpin (AOC)"), ("tst", "target", "missing"),
                                   ("jiptl", "target", "missing")):
            document = example(name)
            validate_document(document, resource_document=resources)
            document["targets"][0][field] = value
            with self.subTest(name=name, field=field), self.assertRaises(ContractError):
                validate_document(document, resource_document=resources)


if __name__ == "__main__":
    unittest.main()
