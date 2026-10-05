from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, validate_document
from openaix.build.planning_fields import validate_planning_inventory


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


def round_trip(document, resources):
    return import_document(export_document(document, resource_document=resources), resource_document=resources)


def tasking(document, kind, mission_type=None):
    return next(mission["tasking"] for mission in document["missions"]
                if mission["tasking"]["kind"] == kind and mission["tasking"].get("mission_type", mission_type) == mission_type)


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.ato, self.resources = example("ato-oir"), example("resources")

    def assignment_order(self):
        document = example("aco-all-measures")
        document["assignments"] = document["assignments"][:1]
        document["resources"].setdefault("agencies", {})["control-west"] = {"id": "control-west", "kind": "c2-agency", "callsign": "Control West", "role": "AWACS"}
        document["assignments"][0].update({
            "controlling_agency": "control-west",
            "control_points": [{"kind": "control_measure", "id": "dagger-cp"}],
            "purpose": "Coordinate the mission's entry period.",
            "transit_instructions": ["Contact Control West before entering."],
        })
        document["references"] = [{"id": "standing-spins", "revision": "3", "section": "Airspace procedures"}]
        return document

    def test_assignment_coordination_round_trip_preserves_standing_measure(self):
        document = self.assignment_order()
        original_measure = deepcopy(document["resources"]["control_measures"]["shell-aara"])
        restored = import_document(export_document(document))
        self.assertEqual(restored, document)
        self.assertEqual(restored["resources"]["control_measures"]["shell-aara"], original_measure)

    def test_assignment_rejects_unresolved_and_non_point_control_references(self):
        for identifier in ("missing", "shell-aara"):
            with self.subTest(identifier=identifier):
                document = self.assignment_order()
                document["assignments"][0]["control_points"][0]["id"] = identifier
                with self.assertRaises(ContractError):
                    validate_document(document)
        document = self.assignment_order()
        document["assignments"][0]["controlling_agency"] = "missing"
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_related_aco_reference_remains_optional_but_supplied_identity_is_checked(self):
        document = self.ato
        self.assertEqual(round_trip(document, self.resources), document)
        document.pop("aco")
        validate_document(document, resource_document=self.resources)
        document["aco"] = {"revision": "2"}
        with self.assertRaises(ContractError):
            validate_document(document, resource_document=self.resources)

    def test_transport_purpose_is_distinct_from_delivery_and_recovery_method(self):
        transport = tasking(self.ato, "transport")
        original_delivery = transport.get("delivery_method")
        for role in ("airlift", "aeromedical_evacuation", "noncombatant_evacuation", "humanitarian_assistance"):
            with self.subTest(role=role):
                transport["role"] = role
                self.assertEqual(round_trip(self.ato, self.resources), self.ato)
                self.assertEqual(transport.get("delivery_method"), original_delivery)
        transport["role"] = "combat_search_and_rescue"
        with self.assertRaises(ContractError):
            validate_document(self.ato, resource_document=self.resources)

    def test_preplanned_attack_names_scheduled_cas_not_the_old_preplanned_cas_value(self):
        attack = tasking(self.ato, "preplanned_attack")
        attack["role"] = "scheduled_cas"
        # The SCL of the attack flight lists the roles that it is for (tools/openaix/check/scl.py).
        self.resources["resources"]["scls"]["f15e-strike"]["missions"].append({"tasking": "preplanned_attack", "role": "scheduled_cas"})
        self.assertEqual(round_trip(self.ato, self.resources), self.ato)
        attack["role"] = "preplanned_cas"
        with self.assertRaises(ContractError):
            validate_document(self.ato, resource_document=self.resources)

    def test_counterair_sweep_and_interception_round_trip_without_a_patrol_orbit(self):
        sweep, interception = tasking(self.ato, "counterair", "fighter_sweep"), tasking(self.ato, "counterair", "interception")
        self.assertIn("area", sweep)
        self.assertNotIn("area", interception)
        self.assertEqual(round_trip(self.ato, self.resources), self.ato)
        interception.pop("target")
        interception["area"] = deepcopy(sweep["area"])
        validate_document(self.ato, resource_document=self.resources)

    def test_counterair_requires_scope_and_rejects_missing_or_fixed_air_targets(self):
        cases = [
            {"kind": "counterair", "mission_type": "fighter_sweep"},
            {"kind": "counterair", "mission_type": "interception"},
            {"kind": "counterair", "mission_type": "fighter_sweep", "target": {"kind": "mobile", "target": "unknown-track"}},
            {"kind": "counterair", "mission_type": "interception", "target": {"kind": "mobile", "target": "missing"}},
            {"kind": "counterair", "mission_type": "interception", "target": {"kind": "mobile", "target": "cobalt-array"}},
        ]
        index = next(i for i, mission in enumerate(self.ato["missions"]) if mission["tasking"].get("mission_type") == "interception")
        for case in cases:
            with self.subTest(tasking=case):
                document = deepcopy(self.ato)
                document["missions"][index]["tasking"] = case
                with self.assertRaises(ContractError):
                    validate_document(document, resource_document=self.resources)

    def test_search_and_rescue_roles_preserve_personnel_recovery_details(self):
        recovery = tasking(self.ato, "personnel_recovery")
        original = deepcopy(recovery)
        for role in ("search_and_rescue", "combat_search_and_rescue"):
            with self.subTest(role=role):
                recovery["role"] = role
                restored = tasking(round_trip(self.ato, self.resources), "personnel_recovery")
                self.assertEqual(restored.pop("role"), role)
                self.assertEqual(restored, {key: value for key, value in original.items() if key != "role"})
        recovery["role"] = "SAR"
        with self.assertRaises(ContractError):
            validate_document(self.ato, resource_document=self.resources)

    def test_search_and_rescue_is_an_order_task_with_a_referenced_search_area(self):
        recovery = tasking(self.ato, "personnel_recovery")
        self.assertEqual(recovery["search_area"], {"kind": "control_measure", "id": "rescue-reservation"})
        recovery.pop("search_area")
        with self.assertRaises(ContractError):
            validate_document(self.ato, resource_document=self.resources)

    def test_public_request_inventory_does_not_claim_field_completeness(self):
        inventory = json.loads((ROOT / "sources/planning-field-inventory.json").read_text())
        authorities = json.loads((ROOT / "sources/authorities.json").read_text())
        validate_planning_inventory(inventory, authorities)
        self.assertNotIn("measure_review", inventory)
        invalid = deepcopy(inventory)
        invalid["acmreq"]["complete_field_dictionary"] = True
        with self.assertRaisesRegex(ValueError, "complete field-dictionary"):
            validate_planning_inventory(invalid, authorities)
        invalid = deepcopy(inventory)
        invalid["acmreq"]["sets"].pop()
        with self.assertRaisesRegex(ValueError, "each Annex C set"):
            validate_planning_inventory(invalid, authorities)
        invalid = deepcopy(inventory)
        invalid["documents"][0].pop("source")
        with self.assertRaisesRegex(ValueError, "known authority"):
            validate_planning_inventory(invalid, authorities)
        interception = next(row for row in inventory["mission_type_mapping"] if row["values"].get("mission_type") == "interception")
        self.assertEqual(interception["source"], "joint-jp-3-01-2012")


if __name__ == "__main__":
    unittest.main()
