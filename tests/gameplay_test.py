"""Gameplay fields: per-aircraft data, package timing, weather, radio activities and communication plans, the shared
CAS brief, carrier recovery, fuel, steerpoints, the print extension, optional annexes and the enumeration case."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from jsonschema import Draft202012Validator

from openaix.check.validate import ContractError, schemas, validate_document

# Property and definition names whose enumeration values are codes (acronyms, designators, units, classification
# markings), which keep their upper case. Every other enumeration value is lower case snake_case.
CODE_FIELDS = {
    "ClassificationLevel", "airspace_class_code", "airspace_type", "approach_lighting", "band", "categories", "class", "classes",
    "ils_category", "modulation", "primitive_type", "reference", "role", "slope_indicator", "supply_class", "type", "unit",
}
SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


def enumerations(node, owner, path=""):
    """(owner, path, value) of every string enumeration value in a schema."""
    if isinstance(node, dict):
        if isinstance(node.get("enum"), list):
            for value in node["enum"]:
                if isinstance(value, str):
                    yield owner, path, value
        for key, child in node.items():
            if key in ("x-enum-descriptions", "propertyNames", "examples", "default", "const"):
                continue
            if key == "properties" and isinstance(child, dict):
                for name, field in child.items():
                    yield from enumerations(field, name, path + "/properties/" + name)
            elif key == "$defs":
                for name, definition in child.items():
                    yield from enumerations(definition, name, path + "/$defs/" + name)
            else:
                yield from enumerations(child, owner, path + "/" + key)
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from enumerations(child, owner, path + "/" + str(index))


class GameplayTests(unittest.TestCase):
    def setUp(self):
        self.resources, self.ato = example("resources"), example("ato-oir")
        self.opord, self.carrier = example("opord"), example("carrier")
        self.linked = {"resource_document": self.resources, "linked": {self.ato["meta"]["id"]: self.ato, self.opord["meta"]["id"]: self.opord}}

    def schema_valid(self, document):
        """True when the schema accepts the document; references between parts of an order are not examined."""
        records, registry = schemas()
        return Draft202012Validator(records[document["kind"]], registry=registry).is_valid(document)

    def flight(self, document, identifier):
        return next(flight for mission in document["missions"] for flight in mission["flights"] if flight["id"] == identifier)

    def valid_ato(self, document):
        validate_document(document, resource_document=self.resources)

    def rejected_ato(self, document, path=None):
        with self.assertRaises(ContractError) as error:
            validate_document(document, resource_document=self.resources)
        if path is not None:
            self.assertEqual(error.exception.path, path)

    # Per-aircraft data -------------------------------------------------------------------------
    def test_aircraft_override_gives_board_number_crew_laser_code_and_link16(self):
        override = self.flight(self.ato, "weasel")["configuration"]["member_overrides"][0]
        self.assertEqual({"board_number", "crew", "laser_code"} | {"member", "identification"}, set(override))
        self.assertEqual(set(override["identification"]["link16"]), {"stn", "fighter_channel", "mission_channel", "special_channel", "donors", "team"})
        self.valid_ato(self.ato)

    def test_laser_codes_outside_1111_to_1788_are_rejected(self):
        for code in ("1099", "1088", "1189", "1811", "1789", "0111", "168", "16880", "abcd", 1688):
            with self.subTest(code=code):
                document = deepcopy(self.ato)
                self.flight(document, "weasel")["configuration"]["member_overrides"][0]["laser_code"] = code
                self.rejected_ato(document)
        for code in ("1111", "1788", "1688", "1511"):
            with self.subTest(code=code):
                document = deepcopy(self.ato)
                self.flight(document, "weasel")["configuration"]["member_overrides"][0]["laser_code"] = code
                self.valid_ato(document)

    def test_link16_station_numbers_are_five_octal_digits_and_channels_are_1_to_127(self):
        for field, value in (("stn", "03481"), ("stn", "3401"), ("donors", ["99999"]), ("team", ["0340"]),
                             ("fighter_channel", 0), ("mission_channel", 128), ("special_channel", "12")):
            with self.subTest(field=field, value=value):
                document = deepcopy(self.ato)
                self.flight(document, "weasel")["configuration"]["member_overrides"][0]["identification"]["link16"][field] = value
                self.rejected_ato(document)

    def test_crew_members_need_a_name_and_a_known_role(self):
        for crew in ([{"name": "Ruiz"}], [{"name": "Ruiz", "role": "PILOT"}], [{"role": "pilot"}], []):
            with self.subTest(crew=crew):
                document = deepcopy(self.ato)
                self.flight(document, "weasel")["configuration"]["member_overrides"][0]["crew"] = crew
                self.rejected_ato(document)

    # Package timing and steerpoints --------------------------------------------------------------
    def test_package_gives_time_on_target_push_time_and_push_point(self):
        package = next(item for item in self.ato["packages"] if item["id"] == "anvil")
        self.assertTrue({"time_on_target", "push_time", "push_point"} <= set(package))
        self.valid_ato(self.ato)

    def test_push_point_needs_the_push_role(self):
        document = deepcopy(self.ato)
        next(item for item in document["packages"] if item["id"] == "anvil")["push_point"] = "ip-silver"
        self.rejected_ato(document)

    def test_push_time_is_a_time_condition(self):
        document = deepcopy(self.ato)
        next(item for item in document["packages"] if item["id"] == "anvil")["push_time"] = "1315Z"
        self.rejected_ato(document)

    def test_point_roles_include_push_rendezvous_anchor_and_hold(self):
        roles = schemas()[0]["measures/point"]["properties"]["roles"]["items"]["enum"]
        self.assertTrue({"push", "rendezvous", "anchor", "hold"} <= set(roles))
        roles_in_use = {role for measure in self.resources["resources"]["control_measures"].values() for role in measure.get("roles", [])}
        self.assertTrue({"push", "rendezvous", "anchor", "hold"} <= roles_in_use)

    def test_route_points_have_a_steerpoint_number_from_1(self):
        route = next(iter(self.resources["resources"]["routes"].values()))
        self.assertEqual([point["number"] for point in route["points"]], list(range(1, len(route["points"]) + 1)))
        for number in (0, -1, 1.5, "1"):
            with self.subTest(number=number):
                document = deepcopy(self.resources)
                next(iter(document["resources"]["routes"].values()))["points"][0]["number"] = number
                with self.assertRaises(ContractError):
                    validate_document(document)

    # Fuel ----------------------------------------------------------------------------------------
    def test_fuel_plan_gives_the_required_fuel_and_the_burn_rate(self):
        fuel = self.flight(self.ato, "viper")["fuel"]
        self.assertEqual(fuel["burn_rate"], {"value": 4800, "unit": "lb/h"})
        self.assertEqual(fuel["mission_required"]["unit"], "lb")
        for rate in ({"value": 4800, "unit": "lb"}, {"value": 0, "unit": "lb/h"}, {"value": 2000, "unit": "kg/s"}, {"value": 2000}):
            with self.subTest(rate=rate):
                document = deepcopy(self.ato)
                self.flight(document, "viper")["fuel"]["burn_rate"] = rate
                self.rejected_ato(document)

    # Radio assignments by flight operation, communication plans -------------------------------
    def test_radio_assignment_names_activities_of_its_flight(self):
        viper = self.flight(self.ato, "viper")
        self.assertEqual([item["activities"] for item in viper["communications"]], [["viper-station"], ["viper-refuel"]])
        document = deepcopy(self.ato)
        self.flight(document, "viper")["communications"][0]["activities"] = ["missing"]
        index = next(index for index, mission in enumerate(document["missions"]) if any(item["id"] == "viper" for item in mission["flights"]))
        self.rejected_ato(document, f"/missions/{index}/flights/0/communications/0/activities/0")
        document = deepcopy(self.ato)
        self.flight(document, "viper")["communications"][0]["activities"] = []
        self.rejected_ato(document)

    def test_flight_uses_a_reusable_communication_plan(self):
        plan = self.resources["resources"]["comm_plans"]["anvil-comms"]
        self.assertTrue(plan["assignments"])
        self.assertEqual(self.flight(self.ato, "chevy")["comm_plan"], "anvil-comms")
        document = deepcopy(self.ato)
        self.flight(document, "chevy")["comm_plan"] = "missing"
        self.rejected_ato(document)
        resources = deepcopy(self.resources)
        resources["resources"]["comm_plans"]["anvil-comms"]["assignments"][0]["channel"] = "missing"
        with self.assertRaises(ContractError):
            validate_document(self.ato, resource_document=resources)
        resources = deepcopy(self.resources)
        resources["resources"]["comm_plans"]["anvil-comms"]["assignments"][0]["activities"] = ["viper-station"]
        with self.assertRaises(ContractError):
            validate_document(self.ato, resource_document=resources)

    def test_a_document_without_communication_plans_validates(self):
        resources = deepcopy(self.resources)
        del resources["resources"]["comm_plans"]
        document = deepcopy(self.ato)
        del self.flight(document, "chevy")["comm_plan"]
        validate_document(document, resource_document=resources)

    # Weather ---------------------------------------------------------------------------------------
    def test_weather_forecast_gives_altimeter_cloud_layers_and_winds_aloft(self):
        forecast = self.opord["situation"]["area_of_operations"]["weather"]["forecasts"][0]
        self.assertEqual(forecast["altimeter"], {"value": 29.92, "unit": "inHg"})
        self.assertEqual({layer["coverage"] for layer in forecast["clouds"]}, {"few", "scattered"})
        self.assertEqual({"altitude", "direction", "speed"}, set(forecast["winds_aloft"][0]))
        validate_document(self.opord, **self.linked)

    def test_bad_weather_values_are_rejected(self):
        changes = (("altimeter", {"value": 29.92, "unit": "INHG"}), ("altimeter", {"value": 29.92}), ("altimeter", {"value": -1, "unit": "hPa"}),
                   ("clouds", [{"coverage": "Broken", "base": {"value": 3000, "unit": "ft", "reference": "AGL"}}]),
                   ("clouds", [{"coverage": "broken"}]), ("winds_aloft", [{"altitude": {"value": 10000, "unit": "ft", "reference": "MSL"}}]))
        for field, value in changes:
            with self.subTest(field=field, value=value):
                document = deepcopy(self.opord)
                document["situation"]["area_of_operations"]["weather"]["forecasts"][0][field] = value
                with self.assertRaises(ContractError):
                    validate_document(document, **self.linked)

    # CAS brief ---------------------------------------------------------------------------------------
    def test_ato_and_opord_share_one_cas_brief_definition(self):
        records = schemas()[0]
        shared = records["common"]["$id"] + "#/$defs/CasBrief"
        self.assertEqual(records["ato"]["$defs"]["CASBrief"], {"$ref": shared, "description": records["ato"]["$defs"]["CASBrief"].get("description")} if "description" in records["ato"]["$defs"]["CASBrief"] else {"$ref": shared})
        self.assertEqual(records["opord"]["$defs"]["AirSupportAppendix"]["properties"]["cas_briefs"]["items"]["$ref"], shared)
        self.assertNotIn("CasBrief", records["opord"]["$defs"])
        self.assertEqual({"id", "target_position", "target_description"}, set(records["opord"]["$defs"]["AirSupportAppendix"]["properties"]["cas_briefs"]["items"]["required"]))

    def test_cas_brief_gives_the_nine_line_completeness_fields(self):
        brief = self.opord["annexes"]["D"]["air_support"]["cas_briefs"][0]
        for field in ("danger_close", "final_attack_headings", "offset_direction", "time_to_target_seconds", "threats", "hazards", "friendly_marking"):
            self.assertIn(field, brief)
        ato_brief = next(mission["tasking"]["brief"] for mission in self.ato["missions"] if mission["id"] == "cas-cobalt")
        self.assertIn("danger_close", ato_brief)
        validate_document(self.opord, **self.linked)
        self.valid_ato(self.ato)

    def test_bad_cas_brief_values_are_rejected_in_both_documents(self):
        changes = {"laser_code": "1999", "mark": "LASER", "friendly_marking": "Panel", "offset_direction": "up", "danger_close": "no",
                   "final_attack_headings": [{"start_bearing": {"value": 10, "reference": "magnetic"}}], "time_to_target_seconds": -1,
                   "threats": ["missing"], "hazards": [{"kind": "WIRES"}]}
        for field, value in changes.items():
            with self.subTest(document="opord", field=field):
                document = deepcopy(self.opord)
                document["annexes"]["D"]["air_support"]["cas_briefs"][0][field] = value
                with self.assertRaises(ContractError):
                    validate_document(document, **self.linked)
        for field, value in changes.items():
            if field == "mark":
                continue
            with self.subTest(document="ato", field=field):
                document = deepcopy(self.ato)
                next(mission["tasking"]["brief"] for mission in document["missions"] if mission["id"] == "cas-cobalt")[field] = value
                self.rejected_ato(document)

    def test_one_target_mark_enumeration_serves_every_mark_field(self):
        records = schemas()[0]
        marks = records["common"]["$defs"]["TargetMark"]["enum"]
        self.assertEqual(len(marks), len(set(marks)))
        brief = records["common"]["$defs"]["CasBrief"]["properties"]
        self.assertEqual(brief["mark"]["$ref"], "#/$defs/TargetMark")
        self.assertEqual(brief["marks"]["items"]["$ref"], "#/$defs/TargetMark")
        self.assertEqual(records["ato"]["$defs"]["FACABrief"]["properties"]["marks"]["items"]["$ref"], records["common"]["$id"] + "#/$defs/TargetMark")
        for value in ("infrared", "none", "LASER", "laser "):
            with self.subTest(value=value):
                document = deepcopy(self.opord)
                document["annexes"]["D"]["air_support"]["cas_briefs"][0]["mark"] = value
                with self.assertRaises(ContractError):
                    validate_document(document, **self.linked)

    # Carrier -------------------------------------------------------------------------------------------
    def test_carrier_gives_link4_acls_and_recovery_windows(self):
        carrier = self.carrier["carrier"]
        self.assertEqual({"link4", "acls", "recovery_windows"} <= set(carrier), True)
        validate_document(self.carrier)

    def test_bad_carrier_values_are_rejected(self):
        changes = (("link4", {"value": 336.0, "unit": "kHz"}), ("acls", "yes"), ("recovery_windows", []),
                   ("recovery_windows", [{"case": "case_iii", "brc": {"value": 330, "reference": "magnetic"}}]),
                   ("recovery_windows", [{"window": {"start": "2026-10-02T13:30:00Z", "end": "2026-10-02T14:15:00Z"}, "case": "CASE_III"}]),
                   ("recovery_windows", [{"window": {"start": "2026-10-02T13:30:00Z", "end": "2026-10-02T14:15:00Z"}, "case": "case_iv"}]))
        for field, value in changes:
            with self.subTest(field=field, value=value):
                document = deepcopy(self.carrier)
                document["carrier"][field] = value
                with self.assertRaises(ContractError):
                    validate_document(document)

    # Print extension ------------------------------------------------------------------------------------
    def test_print_extension_has_a_schema(self):
        print_data = self.opord["extensions"]["org.opord-builder.print"]
        self.assertTrue({"logo", "watermark", "copy_number", "number_of_copies", "classification_caveat"} <= set(print_data))
        validate_document(self.opord, **self.linked)
        for field, value in (("copy_number", 0), ("number_of_copies", "12"), ("logo", ""), ("watermark", 1), ("classification_banner", "SECRET//X"),
                             ("unknown_field", "x")):
            with self.subTest(field=field):
                document = deepcopy(self.opord)
                document["extensions"]["org.opord-builder.print"][field] = value
                with self.assertRaises(ContractError):
                    validate_document(document, **self.linked)

    # Optional annexes ------------------------------------------------------------------------------------
    def test_every_annex_is_optional_in_its_parent(self):
        record = schemas()[0]["opord"]
        self.assertFalse(record["$defs"]["Annexes"].get("required"))
        self.assertNotIn("annexes", record["required"])
        minimal = example("minimal/opord")
        self.assertNotIn("annexes", minimal)
        validate_document(minimal)
        document = deepcopy(self.opord)
        del document["annexes"]
        self.assertTrue(self.schema_valid(document))
        for letter in self.opord["annexes"]:
            with self.subTest(annex=letter):
                document = deepcopy(self.opord)
                del document["annexes"][letter]
                self.assertTrue(self.schema_valid(document))

    def test_annex_sections_are_optional_in_their_parents(self):
        sections = (("F", "supply_points"), ("F", "financial_management"), ("H", "comsec"), ("Q", "battle_rhythm"), ("J", None), ("K", None),
                    ("U", None), ("W", None), ("P", None))
        for letter, field in sections:
            with self.subTest(annex=letter, field=field):
                document = deepcopy(self.opord)
                if field:
                    document["annexes"][letter].pop(field, None)
                else:
                    document["annexes"][letter] = {}
                self.assertTrue(self.schema_valid(document))
        document = deepcopy(self.opord)
        document["sustainment"].pop("financial_management", None)
        self.assertTrue(self.schema_valid(document))

    # Enumeration case, spelling, codes -------------------------------------------------------------------
    def test_enumeration_values_are_lower_case_snake_case_unless_they_are_codes(self):
        wrong = []
        for name, schema in schemas()[0].items():
            for owner, path, value in enumerations(schema, name):
                if value and not SNAKE.match(value) and owner not in CODE_FIELDS:
                    wrong.append((name, path, value))
        self.assertEqual(wrong, [])

    def test_word_valued_enumerations_were_lowercased(self):
        records = schemas()[0]
        self.assertEqual(records["ato"]["$defs"]["AttackAssignment"]["properties"]["desired_effect"]["enum"],
                         ["destroy", "neutralize", "suppress", "disrupt", "degrade", "deny", "divert"])
        entry = records["jiptl"]["$defs"]["JIPTLTarget"]["properties"]
        self.assertEqual(entry["component_tasked"]["enum"], ["land", "air", "maritime", "sof", "cyber", "space"])
        self.assertEqual(entry["status"]["enum"], ["approved", "pending", "denied", "executed", "expired"])
        self.assertEqual(records["resources"]["$defs"]["ReportDefinition"]["properties"]["precedence"]["enum"],
                         ["flash", "immediate", "priority", "routine"])

    def test_upper_case_enumeration_values_are_rejected(self):
        document = deepcopy(self.ato)
        assignment = next(m for m in document["missions"] if m["id"] == "strike-cobalt")["tasking"]["assignments"][0]
        assignment["desired_effect"] = assignment["desired_effect"].upper()
        self.rejected_ato(document)
        target_list = example("jiptl")
        target_list["targets"][0]["status"] = "APPROVED"
        with self.assertRaises(ContractError):
            validate_document(target_list, resource_document=self.resources)

    def test_the_target_list_is_spelled_jiptl_everywhere(self):
        for path in [*(ROOT / "schemas").rglob("*.json"), *(ROOT / "examples").rglob("*.json"), *(ROOT / "catalogues").rglob("*.json"),
                     *(ROOT / "tools").rglob("*.py"), *(ROOT / "tests").glob("*.py"), ROOT / "README.md", ROOT / "viewer/index.html"]:
            text = path.read_text()
            if path.name in {"convert.py", "orders.py", "targeting.py", "gameplay_test.py", "citations_test.py"}:
                # These name the vendored opord-builder files and models, which keep the upstream spelling.
                continue
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                self.assertNotIn("jpitl", text.lower())

    # Control-measure codes ------------------------------------------------------------------------------
    def test_axis_and_critical_friendly_zone_are_catalogue_codes_with_a_cited_definition(self):
        catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
        entries = {entry["code"]: entry for entry in catalogue["types"]}
        for code in ("AXIS", "CFZ"):
            with self.subTest(code=code):
                self.assertTrue(entries[code]["definition_source"]["locator"])
                self.assertTrue(entries[code]["schema"].endswith("measure-area:" + schemas()[0]["common"]["$id"].rsplit(":", 1)[1]))
                self.assertIn(code, schemas()[0]["measures/area"]["properties"]["type"]["enum"])
        self.assertEqual(entries["CFZ"]["category"], "fscm")


if __name__ == "__main__":
    unittest.main()
