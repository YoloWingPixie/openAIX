"""Order-document regressions: mission numbers, ATO/ACO service ownership, typed quantities,
target lists, FRAGO exclusivity, linked resource catalogues and the OIR scenario."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.examples.aco import build_aco_example
from openaix.check.validate import ContractError, export_document, import_document, schemas, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


def mission(document, identifier):
    return next(item for item in document["missions"] if item["id"] == identifier)


class OrderTests(unittest.TestCase):
    def setUp(self):
        self.ato, self.resources = example("ato-oir"), example("resources")

    def rejected(self, document, path=None, resources=None):
        with self.assertRaises(ContractError) as error:
            validate_document(document, resource_document=resources or self.resources)
        if path is not None:
            self.assertEqual(error.exception.path, path)
        return error.exception

    # ORDERS-02 -------------------------------------------------------------------------------
    def test_mission_number_is_required(self):
        del self.ato["missions"][2]["mission_number"]
        self.rejected(self.ato)

    def test_mission_number_is_unique_within_the_order(self):
        self.ato["missions"][3]["mission_number"] = self.ato["missions"][0]["mission_number"]
        error = self.rejected(self.ato, "/missions/3/mission_number")
        self.assertEqual(error.code, "duplicate mission number")

    # ORDERS-01 -------------------------------------------------------------------------------
    def test_aco_assignment_rejects_tanker_and_surveillance_service_fields(self):
        for field, value in (("refueling_method", "boom"), ("tacan", {"channel": 31, "band": "Y"}),
                             ("tanker_types_supported", ["KC-135R"]), ("coverage_responsibility", "North")):
            with self.subTest(field=field):
                document = build_aco_example(self.ato["schema_version"])
                shell = next(item for item in document["assignments"] if item.get("role") == "refueling")
                shell[field] = value
                with self.assertRaises(ContractError) as error:
                    validate_document(document)
                self.assertEqual(error.exception.code, "schema constraint: additionalProperties")

    def test_ato_refueling_tasking_owns_method_and_tacan(self):
        tanker = mission(self.ato, "shell-aar")["tasking"]
        self.assertEqual((tanker["method"], tanker["tacan"]["channel"], tanker["tacan"]["band"]), ("boom", 31, "Y"))
        validate_document(self.ato, resource_document=self.resources)
        changed = deepcopy(self.ato)
        del mission(changed, "shell-aar")["tasking"]["method"]
        self.rejected(changed)
        changed = deepcopy(self.ato)
        mission(changed, "shell-aar")["tasking"]["tacan"]["channel"] = 127
        self.rejected(changed)

    def test_flight_has_no_separate_refuelling_method(self):
        mission(self.ato, "cap-falcon")["flights"][0]["refueling_method"] = "boom"
        self.rejected(self.ato)

    # ORDERS-03 -------------------------------------------------------------------------------
    def test_assignment_usage_is_an_enumerated_filter_consistent_with_the_orbit_role(self):
        document = build_aco_example(self.ato["schema_version"])
        self.assertEqual({item.get("usage") for item in document["assignments"]}, {"cap", "aew", "aar", "holding", "transit", "fires", None})
        changed = deepcopy(document)
        changed["assignments"][0]["usage"] = "air_show"
        with self.assertRaises(ContractError):
            validate_document(changed)
        shell = next(index for index, item in enumerate(document["assignments"]) if item.get("role") == "refueling")
        document["assignments"][shell]["usage"] = "cap"
        with self.assertRaises(ContractError) as error:
            validate_document(document)
        self.assertEqual(error.exception.path, f"/assignments/{shell}/usage")

    # ORDERS-05 -------------------------------------------------------------------------------
    def test_ato_cuts_weather_briefing_attachments_cargo_mass_and_legacy_airspace(self):
        cases = [
            ((), "weather", {"winds": "Light and variable"}),
            (("missions", 0), "briefing", [{"kind": "image", "path": "brief.png"}]),
            (("missions", 11, "tasking", "manifest", "cargo", 0), "mass_each", {"value": 500, "unit": "kg"}),
            (("missions", 2, "tasking"), "area", {"airspace": {"collection": "cap_tracks", "name": "Falcon"}}),
        ]
        for path, field, value in cases:
            with self.subTest(field=field):
                document = deepcopy(self.ato)
                target = document
                for key in path:
                    target = target[key]
                target[field] = value
                self.rejected(document)

    def test_resources_cut_legacy_places_legacy_airspace_and_unit_suffixed_fields(self):
        cases = [
            (("resources",), "airspace", {"geo_refs": []}),
            (("resources", "places"), "carrier", {"kind": "carrier", "name": "Carrier"}),
            (("resources", "channels", "control-uhf"), "frequency_mhz", 251.0),
            (("resources", "areas", "jamming-orbit", "geometry"), "radius_nm", 8),
            (("resources", "targets", "cobalt-array", "aimpoints", "bunker-north"), "elevation_msl_ft", 4720),
        ]
        for path, field, value in cases:
            with self.subTest(field=field):
                document = deepcopy(self.resources)
                target = document
                for key in path:
                    target = target[key]
                target[field] = value
                self.rejected(document)

    def test_agency_is_one_c2_agency_definition_with_a_doctrinal_role(self):
        records = schemas()[0]
        self.assertNotIn("Agency", records["resources"].get("$defs", {}))
        self.assertEqual(records["resources"]["$defs"]["ResourceData"]["properties"]["agencies"]["additionalProperties"]["$ref"], records["c2-agency"]["$id"])
        self.assertEqual(set(records["c2-agency"]["properties"]["role"]["enum"]), {"AOC", "CRC", "ASOC", "DASC", "TACP", "AWACS", "JTAC", "ATC"})
        document = example("c2-agency")
        document["role"] = "range_control"
        self.rejected(document)
        changed = deepcopy(self.resources)
        changed["resources"]["agencies"]["darkstar"] = {"callsign": "Darkstar", "role": "AWACS"}
        self.rejected(changed)

    def test_spins_cut_presentation_and_publication_metadata(self):
        document = example("spins")
        linked = {"resource_document": self.resources, "linked": {self.ato["meta"]["id"]: self.ato, "oir-opord": example("opord")}}
        validate_document(document, **linked)
        for field, value in (("presentation", {"font": "serif"}), ("meta", {"id": "oir-spins", "handling": "Exercise only"})):
            with self.subTest(field=field):
                changed = deepcopy(document)
                changed[field] = value
                with self.assertRaises(ContractError):
                    validate_document(changed, **linked)

    # DOCTRINE-07 -----------------------------------------------------------------------------
    def test_time_sensitive_target_priority_is_numeric_and_category_is_open(self):
        document = example("tst")
        target = document["targets"][0]
        self.assertEqual(target["priority"], 1)
        target["category"] = "any locally defined category"
        validate_document(document, resource_document=example("resources"))
        for field, value in (("priority", "TST-1"), ("priority", 0), ("priority_class", "TST-1"), ("linked_pir", [1]), ("collection_requirements", ["ISR"])):
            with self.subTest(field=field, value=value):
                changed = deepcopy(document)
                changed["targets"][0][field] = value
                with self.assertRaises(ContractError):
                    validate_document(changed, resource_document=example("resources"))

    def test_jiptl_components_exclude_information_operations_and_approval_fields(self):
        document = example("jiptl")
        for field, value in (("component_tasked", "IO"), ("review_dtg", "021300ZOCT26"), ("approval_authority", "JTCB")):
            with self.subTest(field=field):
                changed = deepcopy(document)
                changed["targets"][0][field] = value
                with self.assertRaises(ContractError):
                    validate_document(changed, resource_document=example("resources"))
        document["targets"][0]["component_tasked"] = "MARITIME"
        validate_document(document, resource_document=example("resources"))

    # SCHEMA-04 -------------------------------------------------------------------------------
    def test_order_contracts_have_no_unit_suffixed_quantities_or_date_time_groups(self):
        suffix = re.compile(r"_(nm|ft|m|kt|km|mhz|khz|dtg)$")
        records = schemas()[0]
        for name in ("ato", "aco", "resources", "opord", "frago", "spins", "tst", "jiptl", "c2-agency", "fac"):
            schema = deepcopy(records[name])
            schema.get("$defs", {}).pop("VoxJTACSettings", None)
            found = []

            def visit(node, path):
                if isinstance(node, dict):
                    for key, child in node.get("properties", {}).items() if isinstance(node.get("properties"), dict) else ():
                        if suffix.search(key) or key == "dtg":
                            found.append(path + "." + key)
                    if node.get("pattern") == r"^\d{6}Z[A-Z]{3}\d{2}$":
                        found.append(path)
                    for key, child in node.items():
                        visit(child, path + "/" + key)
                elif isinstance(node, list):
                    for child in node:
                        visit(child, path)

            visit(schema, name)
            with self.subTest(schema=name):
                self.assertEqual(found, [])

    def test_date_time_group_text_is_rejected_where_a_date_time_is_required(self):
        cases = [(example("frago"), ("date_time",)), (example("opord"), ("date_time",)),
                 (example("opord"), ("execution", "coordinating_instructions", "timeline", 0, "time")),
                 (example("tst"), ("targets", 0, "activity_window", "start"))]
        linked = {"resource_document": self.resources, "linked": {self.ato["meta"]["id"]: self.ato}}
        for document, path in cases:
            with self.subTest(document=document["kind"], path=path):
                validate_document(document, **linked)
                target = document
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = "021245ZOCT26"
                with self.assertRaises(ContractError):
                    validate_document(document, **linked)

    def test_order_positions_are_geographic_points_not_grid_text(self):
        document = example("opord")
        linked = {"resource_document": self.resources, "linked": {self.ato["meta"]["id"]: self.ato}}
        site = document["annexes"]["H"]["retransmission_sites"][0]
        validate_document(document, **linked)
        for value in ("11SPA1234567890", {"latitude": 36.8, "longitude": -115.8, "mgrs": "11SPA1234567890"}):
            with self.subTest(value=value):
                site["position"] = value
                with self.assertRaises(ContractError):
                    validate_document(document, **linked)

    # PLAN-03 ---------------------------------------------------------------------------------
    def test_frago_is_a_delta_without_order_sections(self):
        typed = example("frago")
        validate_document(typed)
        for field, value in (("situation", {"assumptions": ["Weather permits medium-altitude operations."]}), ("annexes", {}),
                             ("execution", {}), ("base_order", "opord.json"), ("target", {"kind": "ato", "id": "oir-ato", "revision": "1"})):
            with self.subTest(field=field):
                mixed = deepcopy(typed)
                mixed[field] = value
                with self.assertRaises(ContractError):
                    validate_document(mixed)
        bare = {key: typed[key] for key in ("$schema", "kind", "schema_version", "frago_number", "date_time", "base_order")}
        with self.assertRaises(ContractError):
            validate_document(bare)
        bare["mission"] = "OIR air forces delay the strike by 15 minutes."
        self.assertEqual(import_document(export_document(bare)), bare)

    # PLAN-04 ---------------------------------------------------------------------------------
    def test_ato_resolves_a_linked_resource_catalogue(self):
        self.assertIn("resources_ref", self.ato)
        self.assertEqual(import_document(export_document(self.ato, resource_document=self.resources), resource_document=self.resources), self.ato)
        with self.assertRaises(ContractError) as error:
            validate_document(self.ato)
        self.assertEqual(error.exception.path, "/resources_ref")
        changed = deepcopy(self.resources)
        del changed["resources"]["places"]["prince-hassan"]
        self.rejected(self.ato, resources=changed)

    def test_aco_resolves_a_linked_resource_catalogue(self):
        document = build_aco_example(self.ato["schema_version"])
        del document["resources"]
        document["resources_ref"] = {"id": self.resources["meta"]["id"], "revision": self.resources["meta"]["revision"]}
        self.assertEqual(import_document(export_document(document, resource_document=self.resources), resource_document=self.resources), document)
        changed = deepcopy(self.resources)
        del changed["resources"]["control_measures"]["shell"]
        self.rejected(document, resources=changed)
        del document["resources_ref"]
        self.rejected(document)

    def test_inline_and_linked_resources_are_exclusive(self):
        aco = build_aco_example(self.ato["schema_version"])
        aco["resources_ref"] = {"id": self.resources["meta"]["id"], "revision": self.resources["meta"]["revision"]}
        self.ato["resources"] = deepcopy(self.resources["resources"])
        for document in (aco, self.ato):
            with self.subTest(kind=document["kind"]):
                self.rejected(document, "/")

    # EXAMPLES-01 -----------------------------------------------------------------------------
    def test_oir_scenario_is_coherent_and_free_of_placeholders(self):
        aco = example("aco-oir.maximal")
        self.assertEqual(self.ato["period"], aco["period"])
        self.assertEqual(self.ato["aco"]["id"], aco["meta"]["id"])
        names = ("ato-oir", "resources", "opord", "frago", "spins", "tst", "jiptl", "c2-agency", "fac")
        for name in names:
            with self.subTest(example=name):
                self.assertNotRegex(json.dumps(example(name)).lower(), r'"example|placeholder')
        types = set()
        for item in self.ato["missions"]:
            for flight in item["flights"]:
                types.add(flight["aircraft_type"])
                self.assertGreaterEqual(flight["fuel"]["initial"]["value"], 1000)
                self.assertEqual(flight["fuel"]["initial"]["unit"], "lb")
                self.assertGreater(flight["fuel"]["initial"]["value"], flight["fuel"]["bingo"]["value"])
            block = item["tasking"].get("altitude")
            if block:
                self.assertGreater(block["upper"]["value"], block["lower"]["value"])
        self.assertTrue({"f-16c-50", "f-15c", "f-15e", "a-10c", "kc-135r", "e-3a", "hh-60g", "c-130j", "ea-18g"} <= types)


class OirGroundTests(unittest.TestCase):
    """Task Force Bastion graphics: the OPORD overlay, the 9-line brief and the resource catalogue agree."""

    def setUp(self):
        self.opord, self.resources = example("opord"), example("resources")["resources"]["control_measures"]

    def test_overlay_graphics_name_resource_measures_of_the_same_kind(self):
        kinds = {"pl-brass": "LD", "pl-nickel": "PL", "pl-zinc": "LOA", "bastion-basin-boundary": "BOUNDARY", "trp-01": "POINT",
                 "obj-cobalt": "OBJ", "aa-bastion": "AA", "oir-aor": "AOR"}
        overlay = self.opord["annexes"]["C"]["operation_overlay"]
        self.assertEqual(set(overlay), set(kinds))
        for identifier in overlay:
            with self.subTest(measure=identifier):
                self.assertEqual(self.resources[identifier]["type"], kinds[identifier])

    def test_nine_line_brief_uses_the_initial_point_and_a_target_near_the_trp(self):
        brief = self.opord["annexes"]["D"]["air_support"]["cas_briefs"][0]
        self.assertEqual(brief["initial_point"], "ip-silver")
        self.assertIn("initial", self.resources["ip-silver"]["roles"])
        trp = self.resources["trp-01"]
        self.assertEqual(trp["roles"], ["target_reference"])
        self.assertLess(abs(brief["target_position"]["latitude"] - trp["position"]["latitude"]), 0.01)

    def test_limit_of_advance_stays_short_of_the_fscl_and_the_jtac_behind_it(self):
        loa = max(point["latitude"] for point in self.resources["pl-zinc"]["geometry"]["points"])
        fscl = min(point["latitude"] for point in self.resources["oir-fscl"]["geometry"]["points"])
        brass = max(point["latitude"] for point in self.resources["pl-brass"]["geometry"]["points"])
        self.assertLess(brass, loa)
        self.assertLess(loa, fscl)
        self.assertLess(example("fac")["position"]["latitude"], loa)

    def test_coordinating_altitude_is_msl_and_named_in_the_airspace_scheme(self):
        ca = self.resources["bastion-ca"]
        self.assertEqual((ca["type"], ca["geometry"]["level"]["reference"]), ("CA", "MSL"))
        self.assertEqual(self.opord["execution"]["schemes"]["airspace_control"]["coordinating_altitude"], "bastion-ca")


if __name__ == "__main__":
    unittest.main()
