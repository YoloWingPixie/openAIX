import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


class SimulationTests(unittest.TestCase):
    def test_optional_source_fields_still_reject_invalid_values(self):
        document = example("airfield")
        for value in ({"cycle_code": "not-a-cycle"}, "", 2610):
            with self.subTest(value=value):
                document["source"] = value
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_all_tasking_families_accept_core_simulation_plans(self):
        core = {
            "airborne_control": ["kind", "area"], "cap": ["kind", "area"],
            "custom": ["kind", "name", "assigned_actions"], "electromagnetic": ["kind", "area", "assigned_effect"],
            "escort": ["kind", "supported_missions"], "on_call_cas": ["kind", "area"],
            "personnel_recovery": ["kind", "incident", "search_area"], "preplanned_attack": ["kind", "role", "assignments"],
            "reconnaissance": ["kind", "requirements"], "refueling": ["kind", "area", "method"],
            "training": ["kind", "events"], "transport": ["kind", "pickup", "destination"],
            "counterair": ["kind", "mission_type", "area", "target"],
            "counterland_control": ["kind", "mission_type", "area"],
        }
        # Air assault and airdrop are transport roles whose brief carries the zones and the drop data.
        role_core = {"air_assault": ["kind", "role", "pickup", "brief"], "airdrop": ["kind", "role", "pickup", "brief"]}
        document, resources = example("ato-oir"), example("resources")
        document.pop("meta")
        document.pop("schema_version")
        document.pop("packages")
        document["missions"] = [{"id": mission["id"], "mission_number": mission["mission_number"],
                                 "tasking": {key: value for key, value in mission["tasking"].items()
                                             if key in role_core.get(mission["tasking"].get("role"), core[mission["tasking"]["kind"]])},
                                 "flights": [{key: flight[key] for key in ("id", "callsign", "aircraft_type", "count")} for flight in mission["flights"]]}
                                for mission in document["missions"]]
        self.assertEqual({mission["tasking"]["kind"] for mission in document["missions"]}, set(core))
        self.assertEqual(import_document(export_document(document, resource_document=resources), resource_document=resources), document)

    def test_partial_catalogue_cannot_satisfy_an_explicit_revision_pin(self):
        resources = example("resources")
        resources.pop("meta")
        validate_document(resources)
        with self.assertRaises(ContractError) as error:
            validate_document(example("fac"), resource_document=resources)
        self.assertEqual(error.exception.path, "/resources_ref")

    def test_geometry_units_and_measure_activation_remain_required(self):
        for field in ("active", "geometry", "altitude"):
            document = example("orbit")
            del document[field]
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_document(document)
        document = example("orbit")
        del document["geometry"]["leg_length"]["unit"]
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_target_lists_have_real_entries_with_minimum_target_identity(self):
        document = example("jiptl")
        self.assertGreaterEqual(len(document["targets"]), 2)
        minimal = {"$schema": document["$schema"], "kind": "jiptl", "targets": [{"target_number": "TGT-001", "priority_rank": 1}]}
        self.assertEqual(import_document(export_document(minimal)), minimal)
        for invalid in ({"target_number": "TGT-001"}, {"priority_rank": 1}, {"target_number": "TGT-001", "priority_rank": 0}):
            minimal["targets"] = [invalid]
            with self.subTest(target=invalid), self.assertRaises(ContractError):
                validate_document(minimal)
        for name in ("jiptl", "tst"):
            document = example(name)
            self.assertTrue(document["targets"])
            del document["targets"]
            with self.subTest(name=name), self.assertRaises(ContractError):
                validate_document(document)

    def test_standalone_hpt_is_removed_while_embedded_hvt_round_trips(self):
        retired = {"$schema": "urn:openaix:schema:hpt:0.1.0-draft.1", "kind": "hpt", "targets": []}
        with self.assertRaises(ContractError):
            validate_document(retired)
        document = example("opord")
        linked = {"resource_document": example("resources"), "linked": {"oir-ato": example("ato-oir")}}
        document["annexes"]["B"]["high_value_targets"] = [{"id": "hvt-cp", "name": "Enemy command post", "function": "command_and_control",
                                                            "target": "cobalt-array"}]
        self.assertEqual(import_document(export_document(document, **linked), **linked), document)
