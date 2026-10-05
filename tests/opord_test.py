"""OPORD, FRAGO and SPINS: typed paragraphs and annexes, FM 6-0 annex letters, references to openAIX records,
the FRAGO delta and the typed SPINS sections."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import (ContractError, export_document, import_document, measure_categories, schemas,
                                    validate_document)

ANNEX_LETTERS = set("ABCDEFGHJKLMNPQRSUVWZ")
DOCUMENTS = {"opord": "opord", "ato": "ato-oir", "spins": "spins"}


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


def apply_changes(document, changes):
    """A minimal JSON Pointer (RFC 6901) consumer for the tests; openAIX itself does not apply changes."""
    result = deepcopy(document)
    for change in changes:
        *parents, last = [part.replace("~1", "/").replace("~0", "~") for part in change["path"].split("/")[1:]]
        node = result
        for part in parents:
            node = node[int(part)] if isinstance(node, list) else node[part]
        if isinstance(node, list):
            if change["op"] == "add":
                node.insert(len(node) if last == "-" else int(last), change["value"])
            elif change["op"] == "replace":
                node[int(last)] = change["value"]
            else:
                del node[int(last)]
        else:
            if change["op"] == "remove":
                del node[last]
            else:
                if change["op"] == "replace" and last not in node:
                    raise KeyError(change["path"])
                node[last] = change["value"]
    return result


class OrderDocumentTests(unittest.TestCase):
    def setUp(self):
        self.resources, self.ato = example("resources"), example("ato-oir")
        self.opord, self.frago, self.spins = example("opord"), example("frago"), example("spins")
        self.linked = {"resource_document": self.resources, "linked": {self.ato["meta"]["id"]: self.ato, self.opord["meta"]["id"]: self.opord}}

    def valid(self, document):
        validate_document(document, **self.linked)

    def rejected(self, document, path=None):
        with self.assertRaises(ContractError) as error:
            validate_document(document, **self.linked)
        if path is not None:
            self.assertEqual(error.exception.path, path)
        return error.exception

    # Annex letters and typing --------------------------------------------------------------
    def test_annex_letters_follow_fm_6_0_and_the_example_fills_every_annex(self):
        annexes = schemas()[0]["opord"]["$defs"]["Annexes"]
        self.assertEqual(set(annexes["properties"]), ANNEX_LETTERS)
        self.assertFalse(annexes["additionalProperties"])
        self.assertEqual(set(self.opord["annexes"]), ANNEX_LETTERS)
        for letter in "IOTXY":
            with self.subTest(letter=letter):
                changed = deepcopy(self.opord)
                changed["annexes"][letter] = {"summary": "Not used."}
                self.rejected(changed)

    def test_no_generic_body_table_or_appendix_containers(self):
        forbidden = {"body", "typed_body", "appendices", "rows", "columns", "content", "blocks", "kneeboards"}
        for name in ("opord", "frago", "spins"):
            schema = schemas()[0][name]
            found = []

            def visit(node, path):
                if isinstance(node, dict):
                    if isinstance(node.get("properties"), dict):
                        found.extend(path + "." + key for key in node["properties"] if key in forbidden)
                    if node.get("type") == "object" and "properties" not in node and node.get("additionalProperties") not in (False, None) \
                            and "propertyNames" not in node:
                        found.append(path + " (open object)")
                    for key, child in node.items():
                        visit(child, path + "/" + key)
                elif isinstance(node, list):
                    for child in node:
                        visit(child, path)

            visit(schema, name)
            with self.subTest(schema=name):
                self.assertEqual([item for item in found if "extensions" not in item.lower()], [])

    def test_every_annex_has_typed_fields_beside_its_narrative(self):
        definitions = schemas()[0]["opord"]["$defs"]
        for letter, field in definitions["Annexes"]["properties"].items():
            annex = definitions[field["$ref"].rsplit("/", 1)[1]]
            typed = set(annex["properties"]) - {"summary", "remarks"}
            with self.subTest(annex=letter):
                self.assertTrue(typed)
                self.assertTrue(set(self.opord["annexes"][letter]) & typed)

    # Times, positions and print data ------------------------------------------------------
    def test_times_are_date_times_and_positions_are_points(self):
        self.valid(self.opord)
        for path, value in ((("date_time",), "011800ZOCT26"), (("situation", "enemy_forces", "units", 0, "position"), "11SPA1234567890"),
                            (("execution", "concept_of_operations", "phases", 0, "start"), "1300Z")):
            with self.subTest(path=path):
                changed = deepcopy(self.opord)
                target = changed
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.rejected(changed)

    def test_print_furniture_is_extension_data(self):
        self.assertIn("classification_banner", self.opord["extensions"]["org.opord-builder.print"])
        for field in ("classification_banner", "copy_number", "number_of_copies", "place_of_issue", "logo", "watermark"):
            with self.subTest(field=field):
                changed = deepcopy(self.opord)
                changed[field] = "x"
                self.rejected(changed, "/")

    # References -------------------------------------------------------------------------
    def test_fscm_list_accepts_every_fscm_code_and_only_fscm_codes(self):
        catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
        codes = {entry["code"] for entry in catalogue["types"] if entry["category"] == "fscm"}
        self.assertTrue({"FSCL", "CFL", "RFL", "BCL", "NFA", "FFA", "RFA", "KB"} <= codes)
        self.assertTrue(all(measure_categories()[code] == "fscm" for code in codes))
        listed = self.opord["annexes"]["D"]["fire_support_coordination_measures"]
        types = {self.resources["resources"]["control_measures"][identifier]["type"] for identifier in listed}
        self.assertTrue({"FSCL", "RFL", "KB", "NFA"} <= types)
        changed = deepcopy(self.opord)
        changed["annexes"]["D"]["fire_support_coordination_measures"].append("pl-zinc")
        self.rejected(changed, "/annexes/D/fire_support_coordination_measures/4")

    def test_point_references_need_the_matching_role(self):
        changed = deepcopy(self.opord)
        changed["annexes"]["D"]["air_support"]["cas_briefs"][0]["initial_point"] = "cedar"
        self.rejected(changed, "/annexes/D/air_support/cas_briefs/0/initial_point")
        changed = deepcopy(self.spins)
        changed["tanker_procedures"][0]["track"] = "juniper"
        self.rejected(changed, "/tanker_procedures/0/track")

    def test_order_local_and_catalogue_references_resolve(self):
        for path, value in ((("execution", "tasks_to_subordinate_units", 0, "unit"), "tf-steel"),
                            (("annexes", "L", "collection_tasks", 0, "requirement"), "pir-9"),
                            (("annexes", "B", "threat_assessments", 0, "enemy_unit"), "red-sa10"),
                            (("annexes", "H", "nets", 0, "primary"), "ops-vhf"),
                            (("annexes", "D", "targeting", "high_payoff_targets", 0, "ato_missions", 0), "strike-onyx")):
            with self.subTest(path=path):
                changed = deepcopy(self.opord)
                target = changed
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.rejected(changed, "/" + "/".join(map(str, path)))
        changed = deepcopy(self.opord)
        changed["execution"]["concept_of_operations"]["phases"][1]["id"] = "ph-1"
        self.rejected(changed, "/execution/concept_of_operations/phases/1/id")

    def test_ato_missions_resolve_in_the_linked_ato_revision(self):
        with self.assertRaises(ContractError) as error:
            validate_document(self.opord, resource_document=self.resources)
        self.assertEqual(error.exception.path, "/orders/ato")
        stale = deepcopy(self.ato)
        stale["meta"]["revision"] = "2"
        with self.assertRaises(ContractError) as error:
            validate_document(self.opord, resource_document=self.resources, linked={stale["meta"]["id"]: stale})
        self.assertEqual(error.exception.path, "/orders/ato")

    def test_opord_round_trips(self):
        self.assertEqual(import_document(export_document(self.opord, **self.linked), **self.linked), self.opord)

    # FRAGO --------------------------------------------------------------------------------
    def test_frago_changes_apply_to_their_target_revisions(self):
        self.valid(self.frago)
        targets = {(change["target"]["kind"], change["target"]["id"], change["target"]["revision"]) for change in self.frago["changes"]}
        documents = {kind: example(name) for kind, name in DOCUMENTS.items()}
        for kind, identifier, revision in targets:
            self.assertEqual((documents[kind]["meta"]["id"], documents[kind]["meta"]["revision"]), (identifier, revision))
        self.assertEqual(self.frago["base_order"], {"id": self.opord["meta"]["id"], "revision": self.opord["meta"]["revision"]})
        for kind, document in documents.items():
            changes = [change for change in self.frago["changes"] if change["target"]["kind"] == kind]
            with self.subTest(kind=kind):
                self.assertTrue(changes)
                patched = apply_changes(document, changes)
                self.assertNotEqual(patched, document)
                validate_document(patched, **self.linked) if kind != "ato" else validate_document(patched, resource_document=self.resources)
        patched = apply_changes(self.opord, [change for change in self.frago["changes"] if change["target"]["kind"] == "opord"])
        task = patched["execution"]["tasks_to_subordinate_units"][0]["tasks"][0]
        self.assertIn("pl-nickel", task["measures"])
        self.assertEqual(patched["annexes"]["D"]["targeting"]["time_sensitive_targets"][0]["target"], "gainful-battery")
        self.assertEqual(patched["annexes"]["H"]["nets"][2]["primary"], "cas-alt-uhf")

    def test_frago_change_structure_is_checked(self):
        for change, valid in (({"op": "remove", "value": 1}, False), ({"op": "add"}, False), ({"path": "missions/0"}, False),
                              ({"target": {"kind": "resources", "id": "oir-resources", "revision": "1"}}, False),
                              ({"target": {"kind": "ato", "id": "oir-ato"}}, False)):
            changed = deepcopy(self.frago)
            item = changed["changes"][0]
            item.update(change)
            if change.get("op") == "add":
                item.pop("value")
            with self.subTest(change=change):
                with self.assertRaises(ContractError):
                    validate_document(changed)

    # SPINS --------------------------------------------------------------------------------
    def test_spins_sections_are_typed_and_keep_base_and_changes(self):
        self.valid(self.spins)
        properties = set(schemas()[0]["spins"]["properties"])
        self.assertTrue({"rules_of_engagement", "communications", "identification", "personnel_recovery", "divert_and_abort", "airspace_notes",
                         "check_in", "tanker_procedures", "air_defense", "cas", "emergency", "recovery_routing", "electromagnetic",
                         "restrictions", "reports", "night_operations", "remarks", "base", "changes"} <= properties)
        delta = {key: self.spins[key] for key in ("$schema", "kind", "schema_version", "scope", "meta", "resources_ref")}
        delta.update({"scope": "mission", "base": {"id": "oir-spins", "revision": "1", "path": "spins.json"},
                      "changes": [{"op": "replace", "path": "/communications/nets/2/channel", "value": "cas-alt-uhf"}]})
        validate_document(delta, resource_document=self.resources)
        changed = deepcopy(self.spins)
        changed["identification"]["iff"][0]["code"] = "8888"
        self.rejected(changed)

    def test_spins_sections_share_order_types_and_resolve_in_the_linked_opord(self):
        defs = schemas()[0]["spins"]["$defs"]
        air_defense = defs["SpinsAirDefense"]["properties"]
        self.assertEqual(air_defense["weapons_control"]["items"]["$ref"], "#/$defs/WeaponsControl")
        self.assertEqual(air_defense["warnings"]["items"]["$ref"], "#/$defs/AirDefenseWarning")
        self.assertEqual(defs["SpinsElectromagnetic"]["properties"]["emission_control"]["items"]["$ref"], "#/$defs/EmissionControlPeriod")
        self.assertEqual(schemas()[0]["spins"]["properties"]["reports"]["items"]["$ref"], "#/$defs/ReportRequirement")
        self.assertEqual(defs["SpinsRestrictions"]["properties"]["protected_sites"]["items"]["x-catalog"], "order_protected_sites")
        unlinked = {"resource_document": self.resources, "linked": {self.ato["meta"]["id"]: self.ato}}
        with self.assertRaises(ContractError) as error:
            validate_document(self.spins, **unlinked)
        self.assertEqual(error.exception.path, "/orders/opord")
        cases = [
            (("restrictions", "protected_sites", 0), "ps-unknown", "/restrictions/protected_sites/0"),
            (("emergency", "lost_communication", 0, "phases", 0), "ph-9", "/emergency/lost_communication/0/phases/0"),
            (("cas", "laser_codes", 2, "flights", 0), "no-such-flight", "/cas/laser_codes/2/flights/0"),
            (("recovery_routing", "iff_lines", 0), "pl-nickel", "/recovery_routing/iff_lines/0"),
            (("air_defense", "return_to_force", 0, "checkpoints", 0), "cedar", "/air_defense/return_to_force/0/checkpoints/0"),
            (("cas", "laser_codes", 0, "code"), "1899", None),
        ]
        for steps, value, path in cases:
            with self.subTest(steps=steps):
                changed = deepcopy(self.spins)
                node = changed
                for step in steps[:-1]:
                    node = node[step]
                node[steps[-1]] = value
                self.rejected(changed, path)


if __name__ == "__main__":
    unittest.main()
