from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, schemas, validate_document

NAVIGATION = ("airfield", "runway", "localizer", "procedure", "holding", "path-point", "msa", "grid-mora", "navaid", "airway")


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


CATALOGUES = {document["meta"]["id"]: document for document in (example(name) for name in ("resources", "resources-kden"))}


def linked(document):
    """The resource catalogue example that the document's `resources_ref` names."""
    return CATALOGUES.get(document.get("resources_ref", {}).get("id"))


def validate(document):
    validate_document(document, resource_document=linked(document))


def legs(document):
    return [leg for transition in document["transitions"] for leg in transition["legs"]]


def rejected(test, document):
    with test.assertRaises(ContractError):
        validate(document)


class NavigationTests(unittest.TestCase):
    def test_kden_examples_keep_their_provenance_and_catalogue_link(self):
        from openaix.examples.kden import CATALOGUE_REF, PROVENANCE
        from openaix.coordinates import parse_packed_dms
        for name in (*NAVIGATION, "fix"):
            with self.subTest(name=name):
                document = example(name)
                if name in ("airfield", "runway", "localizer", "procedure", "msa", "path-point", "navaid"):
                    self.assertEqual(document["resources_ref"], CATALOGUE_REF)
                validate(document)
                if name in ("airfield", "localizer", "navaid"):
                    # The source keeps the PackedDMS text of the position; it decodes to the stored decimals.
                    self.assertTrue(document["source"].startswith(PROVENANCE + ", position "))
                    self.assertEqual(parse_packed_dms(document["source"].split()[-2]),
                                     (document["position"]["latitude"], document["position"]["longitude"]))
                elif name != "fix":
                    self.assertEqual(document["source"], PROVENANCE)
        self.assertEqual(example("airfield")["ident"], "KDEN")
        # Six physical runways with two ends each.
        self.assertEqual(len(example("airfield")["runways"]), 6)
        self.assertTrue(all(len(runway["ends"]) == 2 for runway in example("airfield")["runways"]))
        self.assertEqual(example("procedure")["ident"], "I16R")
        self.assertEqual(example("navaid")["tacan"], {"channel": 94, "band": "X"})

    def test_unknown_leg_type_is_rejected(self):
        document = example("procedure")
        document["transitions"][0]["legs"][1]["leg_type"] = "ZZ"
        rejected(self, document)

    def test_leg_types_are_readable_names_not_two_letter_codes(self):
        # a leg names its path terminator in words; the two-letter code is only in the value description.
        document = example("procedure")
        leg = legs(document)[1]
        self.assertEqual(leg["leg_type"], "track_to_fix")
        for code in ("CF", "TF", "RF", "HM"):
            with self.subTest(code=code):
                leg["leg_type"] = code
                rejected(self, document)
        document = example("procedure")
        leg = legs(document)[1]
        leg["path_terminator"] = leg.pop("leg_type")
        rejected(self, document)

    def test_every_leg_type_description_gives_its_icao_code(self):
        records, _ = schemas()
        leg_type = records["procedure"]["$defs"]["Leg"]["properties"]["leg_type"]
        self.assertEqual(len(leg_type["enum"]), 23)
        for value in leg_type["enum"]:
            with self.subTest(value=value):
                self.assertRegex(value, "^[a-z]+(_[a-z]+)+$")
                self.assertRegex(leg_type["x-enum-descriptions"][value], r"\(`[A-Z]{2}`\)\.")
        self.assertIn("(`TF`)", leg_type["x-enum-descriptions"]["track_to_fix"])
        self.assertIn("(`RF`)", leg_type["x-enum-descriptions"]["radius_to_fix"])
        self.assertIn("one circuit", leg_type["x-enum-descriptions"]["hold_to_fix"])

    def test_standard_does_not_name_a_source_record_format(self):
        # Schemas, catalogues, examples, the acronyms, authority roles and the viewer do not name a source record format.
        import re
        paths = sorted(path for folder in ("schemas", "catalogues", "examples") for path in (ROOT / folder).rglob("*.json"))
        paths += [
            ROOT / "tools/openaix/describe/acronyms.json", ROOT / "sources/authorities.json",
            ROOT / "sources/leg-type-definitions.json", *sorted(path for path in (ROOT / "viewer").rglob("*") if path.is_file())]
        notes = []
        for path in paths:
            for number, line in enumerate(path.read_text().splitlines(), 1):
                if re.search("arinc", line, re.IGNORECASE):
                    notes.append((path.relative_to(ROOT).as_posix(), number, line))
        self.assertEqual(notes, [])

    def test_every_leg_type_has_a_verified_first_party_source(self):
        # all 23 leg types are verified; the eleven not defined by ICAO cite the FAA.
        from openaix.sources.authorities import load_authorities
        from openaix.build.navigation import LEG_TYPES
        from openaix.sources.audit import leg_type_errors
        table = json.loads((ROOT / "sources/leg-type-definitions.json").read_text())
        rows = table["codes"]
        self.assertEqual(len(rows), 23)
        self.assertEqual((rows["TF"]["leg_type"], rows["RF"]["leg_type"], rows["AF"]["leg_type"], rows["HF"]["leg_type"]),
                         ("track_to_fix", "radius_to_fix", "arc_to_fix", "hold_to_fix"))
        self.assertEqual(tuple(row["leg_type"] for row in rows.values()), LEG_TYPES)
        self.assertEqual(leg_type_errors(table, load_authorities()), [])
        for code in ("FC", "FD", "CD", "CI", "CR", "AF", "VD", "VR", "PI", "HA", "HF"):
            with self.subTest(code=code):
                sources = {rows[code]["source"]} | {reference["source"] for reference in rows[code].get("references", [])}
                self.assertTrue(sources & {"faa-h-8083-16b-2017", "faa-order-8260-3g-2024"})
                self.assertIn(code, rows[code]["source_text"])
        self.assertEqual(rows["CI"]["source"], "faa-order-8260-3g-2024")
        broken = json.loads(json.dumps(table))
        broken["codes"]["CR"]["source"] = "unread-source"
        broken["codes"]["PI"]["verified"] = False
        self.assertEqual(len(leg_type_errors(broken, load_authorities())), 2)

    def test_leg_type_descriptions_are_the_source_table_definitions(self):
        records, _ = schemas()
        descriptions = records["procedure"]["$defs"]["Leg"]["properties"]["leg_type"]["x-enum-descriptions"]
        rows = json.loads((ROOT / "sources/leg-type-definitions.json").read_text())["codes"]
        acronyms = json.loads((ROOT / "tools/openaix/describe/acronyms.json").read_text(encoding="utf-8"))
        for code, row in rows.items():
            text = descriptions[row["leg_type"]]
            for acronym, expansion in acronyms.items():
                text = text.replace(expansion + " (" + acronym + ")", acronym)
            with self.subTest(code=code):
                self.assertEqual(text, row["definition"])

    def test_leg_type_meanings_follow_the_faa_wording(self):
        # a course or heading to a radial ends at a VOR radial; a procedure turn has an outbound leg and a
        # 180-degree turn; the fix-to-distance legs fly a track over the ground.
        records, _ = schemas()
        descriptions = records["procedure"]["$defs"]["Leg"]["properties"]["leg_type"]["x-enum-descriptions"]
        for value in ("course_to_radial", "heading_to_radial"):
            with self.subTest(value=value):
                self.assertIn("radial of a very high frequency omnidirectional range (VOR)", descriptions[value])
        self.assertIn("outbound leg", descriptions["procedure_turn"])
        self.assertIn("180 degrees", descriptions["procedure_turn"])
        for value in ("track_from_fix_for_distance", "track_from_fix_to_dme_distance"):
            with self.subTest(value=value):
                self.assertIn("track over the ground", descriptions[value])

    def test_initial_fix_is_the_initial_fix_in_icao_and_faa_sources(self):
        # PANS-OPS and the FAA call the path terminator IF the initial fix; Doc 9613 lists only the
        # intermediate fix of an approach under the same abbreviation.
        row = json.loads((ROOT / "sources/leg-type-definitions.json").read_text())["codes"]["IF"]
        self.assertEqual((row["leg_type"], row["name"]), ("initial_fix", "Initial fix"))
        texts = {reference["source"]: reference["source_text"] for reference in row["references"]}
        self.assertTrue(texts["faa-order-8260-19k-2025"].startswith("Initial fix."))
        self.assertIn("Initial Fix leg (IF)", texts["faa-order-8260-58d-2025"])
        self.assertIn("Intermediate fix", texts["icao-doc-9613-2023"])

    def test_fix_terminated_leg_without_fix_is_rejected(self):
        document = example("procedure")
        leg = next(leg for leg in legs(document) if leg["leg_type"] == "track_to_fix")
        del leg["fix"]
        rejected(self, document)

    def test_course_and_altitude_terminated_legs_need_their_terminator(self):
        document = example("procedure")
        leg = next(leg for leg in legs(document) if leg["leg_type"] == "course_to_altitude")
        del leg["altitude"]
        rejected(self, document)
        document = example("procedure")
        del next(leg for leg in legs(document) if leg["leg_type"] == "course_to_fix")["course"]
        rejected(self, document)

    def test_rf_leg_needs_arc_centre_and_radius(self):
        document = example("procedure")
        leg = legs(document)[1]
        leg.update(leg_type="radius_to_fix", arc_center=deepcopy(leg["fix"]), arc_radius={"value": 3.61, "unit": "nm"})
        validate(document)
        del leg["arc_radius"]
        rejected(self, document)

    def test_altitude_constraint_kinds_need_their_limits(self):
        document = example("procedure")
        leg = legs(document)[1]
        lower = {"value": 9000, "unit": "ft", "reference": "MSL"}
        leg["altitude"] = {"kind": "between", "lower": lower}
        rejected(self, document)
        leg["altitude"] = {"kind": "between", "lower": lower, "upper": {"value": 11000, "unit": "ft", "reference": "MSL"}}
        validate(document)
        leg["altitude"]["upper"]["value"] = 8000
        rejected(self, document)
        leg["altitude"] = {"kind": "at_or_below", "lower": lower}
        rejected(self, document)
        leg["altitude"] = {"kind": "at", "lower": lower, "upper": lower}
        rejected(self, document)
        leg["speed"] = {"kind": "faster", "value": {"value": 200, "unit": "kt"}}
        rejected(self, document)

    def test_speed_constraints_use_the_altitude_constraint_words(self):
        # `max` and `min` became `at_or_below` and `at_or_above`.
        document = example("procedure")
        leg = legs(document)[1]
        for kind in ("at", "at_or_below", "at_or_above"):
            with self.subTest(kind=kind):
                leg["speed"] = {"kind": kind, "value": {"value": 210, "unit": "kt"}}
                validate(document)
        for kind in ("max", "min"):
            with self.subTest(kind=kind):
                leg["speed"] = {"kind": kind, "value": {"value": 210, "unit": "kt"}}
                rejected(self, document)

    def test_airway_types_are_written_in_words(self):
        # `rnav` and `ats` became `area_navigation` and `air_traffic_services`.
        document = example("airway")
        for value in ("area_navigation", "air_traffic_services", "advisory", "conditional"):
            with self.subTest(value=value):
                document["airway_type"] = value
                validate(document)
        for value in ("rnav", "ats"):
            with self.subTest(value=value):
                document["airway_type"] = value
                rejected(self, document)

    def test_runway_without_flyable_geometry_is_rejected(self):
        for field in ("length", "designator", "ends"):
            with self.subTest(field=field):
                document = example("runway")
                del document[field]
                rejected(self, document)
        for field in ("heading", "threshold", "designator"):
            with self.subTest(end_field=field):
                document = example("runway")
                del document["ends"][1][field]
                rejected(self, document)

    def test_localizer_without_frequency_course_or_position_is_rejected(self):
        for field in ("frequency", "course", "position"):
            with self.subTest(field=field):
                document = example("localizer")
                del document[field]
                rejected(self, document)
        document = example("localizer")
        document["frequency"]["unit"] = "kHz"
        rejected(self, document)

    def test_hold_needs_course_turn_and_one_leg_extent(self):
        for field in ("inbound_course", "turn_direction", "fix", "leg_time"):
            with self.subTest(field=field):
                document = example("holding")
                del document["hold"][field]
                rejected(self, document)
        document = example("holding")
        document["hold"]["leg_length"] = {"value": 4, "unit": "nm"}
        rejected(self, document)
        del document["hold"]["leg_time"]
        validate(document)

    def test_procedure_holds_and_authored_holds_share_one_definition(self):
        procedure = example("procedure")
        hold_leg = next(leg for leg in legs(procedure) if leg["leg_type"] == "hold_to_manual_termination")
        self.assertEqual(hold_leg["hold"], example("holding")["hold"])
        del hold_leg["hold"]
        rejected(self, procedure)
        procedure = example("procedure")
        legs(procedure)[1]["hold"] = deepcopy(example("holding")["hold"])
        rejected(self, procedure)

    def test_msa_sectors_must_sweep_clockwise_once(self):
        def sector(start, end, altitude):
            return {"start_bearing": {"value": start, "reference": "magnetic"}, "end_bearing": {"value": end, "reference": "magnetic"},
                    "full_circle": False, "radius": {"value": 25, "unit": "nm"},
                    "minimum_altitude": {"value": altitude, "unit": "ft", "reference": "MSL"}}
        document = example("msa")
        document["sectors"] = [sector(270, 0, 2200), sector(0, 270, 1500)]
        validate(document)
        gap = deepcopy(document)
        gap["sectors"][0]["end_bearing"]["value"] = (gap["sectors"][0]["end_bearing"]["value"] - 10) % 360
        partial = example("msa")
        partial["sectors"][0].update(full_circle=False)
        partial["sectors"][0]["end_bearing"]["value"] = 90
        mixed = deepcopy(document)
        mixed["sectors"][1]["end_bearing"]["reference"] = "true"
        for name, case in (("gap", gap), ("partial", partial), ("mixed", mixed)):
            with self.subTest(case=name):
                rejected(self, case)

    def test_grid_mora_cells_are_one_degree_and_unknown_is_not_zero(self):
        document = example("grid-mora")
        document["cells"][0]["northeast"]["latitude"] += 1
        rejected(self, document)
        document = example("grid-mora")
        document["cells"][0]["status"] = "unknown"
        rejected(self, document)
        del document["cells"][0]["minimum_altitude"]
        validate(document)
        document["cells"].append(deepcopy(document["cells"][0]))
        rejected(self, document)

    def test_navaid_class_selects_frequency_or_tacan_channel(self):
        document = example("navaid")
        del document["tacan"]
        rejected(self, document)
        document = example("navaid")
        document["class"] = "TACAN"
        rejected(self, document)
        del document["frequency"]
        validate(document)
        document = example("navaid")
        document.update({"class": "NDB", "frequency": {"value": 114.7, "unit": "MHz"}})
        del document["tacan"]
        rejected(self, document)
        document["frequency"] = {"value": 530, "unit": "kHz"}
        validate(document)
        document["class"] = "VOT"
        rejected(self, document)

    def test_navigation_records_carry_no_measure_or_source_record_bookkeeping(self):
        additions = {"active": {"continuous": True}, "category": "arm", "channels": ["uhf"], "coordination_instructions": ["Coordinate."],
                     "record_family": "PG", "icao_code": "K2", "customer_area_code": "USA", "raw_records": ["S" + " " * 131],
                     "continuation_number": 0, "schema_version": "0.1.0-draft.1"}
        for name in NAVIGATION:
            for field, value in additions.items():
                with self.subTest(name=name, field=field):
                    document = example(name)
                    document[field] = value
                    rejected(self, document)
        records, _ = schemas()

        def keys(node):
            if isinstance(node, dict):
                yield from node
                for child in node.values():
                    yield from keys(child)
            elif isinstance(node, list):
                for child in node:
                    yield from keys(child)

        for name in NAVIGATION:
            schema = records["measures/" + name if name in {"navaid", "airway"} else name]
            names = set(keys(schema))
            with self.subTest(schema=name):
                self.assertFalse({"x-source", "x-field-completeness", "x-basis", "raw_fields", "record_family"} & names)
                self.assertFalse([key for key in names if key.endswith("_coded")])

    def test_authored_records_need_no_provenance(self):
        for name in (*NAVIGATION, "fix"):
            with self.subTest(name=name):
                document = example(name)
                document.pop("source", None)
                self.assertEqual(import_document(export_document(document, resource_document=linked(document)), resource_document=linked(document)), document)

    def test_shared_navigation_definitions_are_not_aliased(self):
        from openaix.build.common import BASE, COMMON, DIALECT, VERSION
        from openaix.build.navigation import schemas as navigation_schemas
        built = navigation_schemas(BASE, VERSION, DIALECT, COMMON)
        point = built["path-point"]["properties"]
        self.assertIsNot(point["course_width_at_threshold"], point["threshold_crossing_height"])
        seen = {}

        def visit(node, path):
            if isinstance(node, dict):
                if id(node) in seen:
                    self.fail(path + " shares one object with " + seen[id(node)])
                seen[id(node)] = path
                for key, child in node.items():
                    visit(child, path + "/" + key)
            elif isinstance(node, list):
                for index, child in enumerate(node):
                    visit(child, path + "/" + str(index))

        for name, schema in built.items():
            visit(schema, name)

    def test_holding_binding_is_a_drawing_not_the_holding_aircraft(self):
        document = example("holding")
        document["extensions"] = {"sim": {"dcs": {"bindings": [{"kind": "drawing", "name": "ZOOKS hold", "primitive_type": "Line", "line_mode": "segments", "closed": True}]}}}
        validate(document)
        document["extensions"] = {"sim": {"dcs": {"bindings": [{"kind": "group", "name": "Holding flight"}]}}}
        rejected(self, document)

    def test_recommended_navaid_reference_rejects_a_plain_fix(self):
        resources = example("resources")
        fix = example("fix")
        resources["resources"]["control_measures"][fix["id"]] = fix
        document = example("procedure")
        document["resources_ref"] = {"id": resources["meta"]["id"], "revision": resources["meta"]["revision"]}
        del document["airfield"]
        leg = next(leg for leg in legs(document) if "recommended_navaid" in leg)
        leg["recommended_navaid"] = {"kind": "control_measure", "id": fix["id"]}
        with self.assertRaises(ContractError):
            validate_document(document, resource_document=resources)
        leg["fix"] = {"kind": "control_measure", "id": fix["id"]}
        del leg["recommended_navaid"]
        validate_document(document, resource_document=resources)

    def test_authored_airway_uses_shared_fixes(self):
        resources = example("resources")
        fix = example("fix")
        resources["resources"]["control_measures"][fix["id"]] = fix
        document = example("airway")
        document.pop("source")
        document["resources_ref"] = {"id": resources["meta"]["id"], "revision": resources["meta"]["revision"]}
        document["segments"][0]["fix"] = {"kind": "control_measure", "id": fix["id"]}
        self.assertEqual(import_document(export_document(document, resource_document=resources), resource_document=resources), document)
        document["segments"][0]["fix"]["id"] = "missing"
        with self.assertRaises(ContractError):
            validate_document(document, resource_document=resources)
        document["segments"] = document["segments"][:1]
        document["segments"][0]["fix"] = example("airway")["segments"][0]["fix"]
        rejected(self, document)

    def test_leg_rejects_coded_twins_of_typed_constraints(self):
        # NAV-14/NAV-18: the decoder keeps only typed values; raw source codes are not a second encoding.
        for field, value in (("altitude_description", "+"), ("leg_type_coded", "TF"), ("speed_limit_description", "-"),
                             ("raw_record", "S" + " " * 131), ("turn_direction_coded", "R")):
            with self.subTest(field=field):
                document = example("procedure")
                legs(document)[1][field] = value
                rejected(self, document)
        document = example("procedure")
        legs(document)[1]["leg_type"] = "Course_To_Fix"
        rejected(self, document)

    def test_empty_flyable_records_are_rejected(self):
        for name in ("runway", "localizer", "holding", "procedure"):
            with self.subTest(name=name):
                document = example(name)
                rejected(self, {key: document[key] for key in ("$schema", "id", "kind", "name")})
        document = example("procedure")
        document["transitions"][0]["legs"] = []
        rejected(self, document)

    def test_mission_fix_can_retain_a_textual_location(self):
        document = example("fix")
        document.pop("position")
        document["position_description"] = "Planned reporting point at the north end of the valley."
        self.assertEqual(import_document(export_document(document, resource_document=linked(document)), resource_document=linked(document)), document)
        del document["position_description"]
        rejected(self, document)

    def test_catalogue_airfields_use_the_navigation_contract(self):
        document = example("resources")
        airfield = example("airfield")
        for field in ("localizers", "procedures", "navaids", "traffic_pattern", "resources_ref"):
            airfield.pop(field, None)
        for runway in airfield["runways"]:
            for end in runway["ends"]:
                end.pop("localizer", None)
        airfield.update(id="example", extensions={"sim": {"dcs": {"bindings": [{"kind": "airbase", "name": "Mission-Airfield"}]}}},
                        approach_instructions=["Contact approach before entry."])
        document["resources"]["places"]["example"] = airfield
        self.assertEqual(import_document(export_document(document, resource_document=linked(document)), resource_document=linked(document)), document)
        airfield["runways"][0]["ends"][0]["heading"] = {"value": 400, "reference": "magnetic"}
        rejected(self, document)


if __name__ == "__main__":
    unittest.main()
