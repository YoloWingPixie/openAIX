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
                     "continuation_number": 0, "schema_version": "0.2.0-draft.1"}
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

    def test_approach_minima_follow_the_line_and_the_manoeuvre(self):
        def ils_line(document):
            return document["minima"][0]

        def circling(document):
            return next(line for line in document["minima"] if line["manoeuvre"] == "circling")

        def swap(item, old, new):
            item[new] = item.pop(old)

        cases = (
            ("decision line with a minimum descent altitude", lambda doc: swap(ils_line(doc)["category_minima"][0], "decision_altitude", "minimum_descent_altitude")),
            ("both altitudes", lambda doc: ils_line(doc)["category_minima"][0].update(minimum_descent_altitude=feet(1900))),
            ("neither altitude", lambda doc: ils_line(doc)["category_minima"][0].pop("decision_altitude")),
            ("circling with a runway", lambda doc: circling(doc).update(runway="31")),
            ("circling with a decision altitude", lambda doc: swap(circling(doc)["category_minima"][0], "minimum_descent_altitude", "decision_altitude")),
            ("circling height from the threshold", lambda doc: circling(doc).update(height_reference="threshold")),
            ("straight-in without a runway", lambda doc: ils_line(doc).pop("runway")),
            ("localizer line with an ILS category", lambda doc: doc["minima"][2].update(ils_category="I")),
            ("ILS line with an RNP value", lambda doc: ils_line(doc).update(rnp_value={"value": 0.3, "unit": "nm"})),
            ("unknown approach category", lambda doc: ils_line(doc)["category_minima"][0]["categories"].append("F")),
            ("repeated approach category", lambda doc: ils_line(doc)["category_minima"][0]["categories"].append("A")),
            ("visibility in an unknown unit", lambda doc: ils_line(doc)["category_minima"][0]["visibility"].update(unit="ft")),
            ("RVR in nautical miles", lambda doc: ils_line(doc)["category_minima"][0]["runway_visual_range"].update(unit="nm")),
            ("minima on a departure", lambda doc: doc.update(procedure_type="departure")),
        )
        validate_procedure(self, "ojms-i31")
        for name, change in cases:
            with self.subTest(case=name):
                validate_procedure(self, "ojms-i31", change, valid=False)

    def test_radar_approach_follows_the_approach_type(self):
        cases = (
            ("ojms-par31", "PAR without a glide path angle", lambda doc: doc["radar_approach"].pop("glide_path_angle_deg")),
            ("ojms-par31", "PAR with recommended altitudes",
             lambda doc: doc["radar_approach"].update(recommended_altitudes=[{"distance": {"value": 3, "unit": "nm"}, "altitude": feet(2600)}])),
            ("ojms-par31", "PAR with an ASR missed approach point",
             lambda doc: doc["radar_approach"].update(missed_approach_point_distance={"value": 1, "unit": "nm"})),
            ("ojms-par31", "radar approach without its data", lambda doc: doc.pop("radar_approach")),
            ("ojms-asr13", "ASR with a glide path angle", lambda doc: doc["radar_approach"].update(glide_path_angle_deg=3.0)),
            ("ojms-asr13", "ASR with a threshold crossing height", lambda doc: doc["radar_approach"].update(threshold_crossing_height={"value": 50, "unit": "ft"})),
            ("ojms-asr13", "ASR with elevation limits", lambda doc: doc["radar_approach"]["coverage"].update(elevation_upper_deg=7)),
            ("ojms-asr13", "ASR with a decision altitude", lambda doc: doc["minima"][0]["category_minima"][0].update(
                decision_altitude=doc["minima"][0]["category_minima"][0].pop("minimum_descent_altitude"))),
            ("ojms-i31", "ILS with radar approach data", lambda doc: doc.update(radar_approach=procedure("ojms-par31")["radar_approach"])),
            ("ojms-i31", "radar approach data without an approach type",
             lambda doc: (doc.pop("approach_type"), doc.update(radar_approach=procedure("ojms-par31")["radar_approach"]))),
        )
        for identifier in ("ojms-par31", "ojms-asr13"):
            with self.subTest(procedure=identifier):
                validate_procedure(self, identifier)
        for identifier, name, change in cases:
            with self.subTest(procedure=identifier, case=name):
                validate_procedure(self, identifier, change, valid=False)

    def test_only_radar_approaches_may_omit_transitions(self):
        self.assertNotIn("transitions", procedure("ojms-par31"))
        self.assertTrue(procedure("ojms-asr13")["transitions"])
        cases = (
            ("ojms-par31", "PAR without legs", None, True),
            ("ojms-asr13", "ASR without legs", lambda doc: doc.pop("transitions"), True),
            ("ojms-asr13", "ASR with legs", None, True),
            ("ojms-par31", "PAR with an empty transition list", lambda doc: doc.update(transitions=[]), False),
            ("ojms-i31", "ILS without legs", lambda doc: doc.pop("transitions"), False),
            ("ojms-salat1", "departure without legs", lambda doc: doc.pop("transitions"), False),
            ("ojms-par31", "approach without a type and without legs", lambda doc: (doc.pop("approach_type"), doc.pop("radar_approach")), False),
        )
        for identifier, name, change, valid in cases:
            with self.subTest(procedure=identifier, case=name):
                validate_procedure(self, identifier, change, valid=valid)

    def test_navigation_specification_matches_the_navigation_type(self):
        cases = (
            ("ojms-i31", "conventional with a specification", lambda spec: spec.update(specification="rnav_1")),
            ("ojms-i31", "conventional with an RNP value", lambda spec: spec.update(rnp_value={"value": 1, "unit": "nm"})),
            ("ojms-salat1", "RNAV with an RNP specification", lambda spec: spec.update(specification="rnp_1")),
            ("ojms-salat1", "RNAV with an RNP value", lambda spec: spec.update(rnp_value={"value": 1, "unit": "nm"})),
            ("ojms-salat1", "RNAV without a specification", lambda spec: spec.pop("specification")),
            ("ojms-r13", "RNP with an RNAV specification", lambda spec: spec.update(specification="rnav_2")),
            ("ojms-r13", "RNP value in kilometres", lambda spec: spec["rnp_value"].update(unit="km")),
            ("ojms-r13", "unknown sensor", lambda spec: spec["sensors"].append("loran")),
            ("ojms-i31", "plain fix as a required navigation aid", lambda spec: spec["required_navaids"].append({"kind": "control_measure", "id": "ip-silver"})),
        )
        for identifier in ("ojms-i31", "ojms-salat1", "ojms-r13"):
            with self.subTest(procedure=identifier):
                validate_procedure(self, identifier)
        for identifier, name, change in cases:
            with self.subTest(procedure=identifier, case=name):
                validate_procedure(self, identifier, lambda doc: change(doc["navigation_specification"]), valid=False)
        legs_of = procedure("ojms-r13")["transitions"][0]["legs"]
        self.assertEqual({leg["rnp_value"]["value"] for leg in legs_of}, {1, 0.3})

    def test_climb_gradients_and_takeoff_minima_belong_to_their_procedure_types(self):
        cases = (
            ("ojms-salat1", "gradient without a limit", lambda doc: doc["climb_gradients"][1].pop("until_fix")),
            ("ojms-salat1", "gradient in an unknown unit", lambda doc: doc["climb_gradients"][0]["gradient"].update(unit="m/km")),
            ("ojms-salat1", "gradient reason outside the list", lambda doc: doc["climb_gradients"][0].update(reason="noise")),
            ("ojms-salat1", "takeoff minimum without visibility or RVR", lambda doc: doc["takeoff_minima"][1].pop("runway_visual_range")),
            ("ojms-salat1", "climb gradients on an arrival", lambda doc: (doc.update(procedure_type="arrival"), doc.pop("takeoff_minima"))),
            ("ojms-salat1", "takeoff minima on an arrival", lambda doc: (doc.update(procedure_type="arrival"), doc.pop("climb_gradients"))),
            ("ojms-i31", "takeoff minima on an approach", lambda doc: doc.update(takeoff_minima=procedure("ojms-salat1")["takeoff_minima"])),
        )
        validate_procedure(self, "ojms-salat1")
        for identifier, name, change in cases:
            with self.subTest(procedure=identifier, case=name):
                validate_procedure(self, identifier, change, valid=False)

    def test_procedure_turn_data_stay_on_procedure_turn_legs(self):
        def turn_leg(document):
            return next(leg for leg in legs(document) if leg["leg_type"] == "procedure_turn")

        turn = turn_leg(procedure("ojms-i31"))
        self.assertEqual((turn["procedure_turn"]["turn_type"], turn["turn_direction"]), ("turn_45_180", "left"))
        self.assertEqual(turn["procedure_turn"]["remain_within"], {"value": 10, "unit": "nm"})
        cases = (
            ("course reversal type outside the list", lambda doc: turn_leg(doc)["procedure_turn"].update(turn_type="racetrack")),
            ("procedure turn data without a type", lambda doc: turn_leg(doc)["procedure_turn"].pop("turn_type")),
            ("procedure turn data on another leg", lambda doc: legs(doc)[0].update(procedure_turn={"turn_type": "base_turn"})),
        )
        for name, change in cases:
            with self.subTest(case=name):
                validate_procedure(self, "ojms-i31", change, valid=False)

    def test_obstacle_assessment_and_provenance_are_typed(self):
        cases = (
            ("AIRAC cycle 15", lambda doc: doc["provenance"].update(airac_cycle="2615")),
            ("AIRAC cycle as a date", lambda doc: doc["provenance"].update(airac_cycle="2026-10-01")),
            ("unknown derivation", lambda doc: doc["provenance"].update(derivation="guessed")),
            ("provenance without a derivation", lambda doc: doc["provenance"].pop("derivation")),
            ("segment without its minimum altitude", lambda doc: doc["obstacle_assessment"]["segments"][0].pop("minimum_altitude")),
            ("obstacle clearance of zero", lambda doc: doc["obstacle_assessment"]["segments"][0]["obstacle_clearance"].update(value=0)),
            ("obstacle elevation above ground level",
             lambda doc: doc["obstacle_assessment"]["segments"][0]["controlling_obstacle"]["elevation"].update(reference="AGL")),
            ("unknown criteria", lambda doc: doc["obstacle_assessment"].update(criteria="faa")),
        )
        for name, change in cases:
            with self.subTest(case=name):
                validate_procedure(self, "ojms-i31", change, valid=False)
        published = {"derivation": "published", "authority": "FAA", "airac_cycle": "2610",
                     "effective_from": "2026-10-01T09:01:00Z", "effective_until": "2026-10-29T09:01:00Z"}
        for name in NAVIGATION:
            with self.subTest(name=name):
                document = example(name)
                document["provenance"] = deepcopy(published)
                validate(document)


def magnetic(value):
    return {"value": value, "reference": "magnetic", "declination_deg": 5.0}


class InterchangeGapTests(unittest.TestCase):
    """Procedure runways, links to holds and MSA, TCH, remarks, localizer references, theta and rho, altitude kinds,
    approach fix roles, DCS beacons, navigation aid classes and the optional glide slope position."""

    def test_procedure_runways_are_runway_designators_of_the_airfield(self):
        self.assertEqual(example("procedure")["runways"], ["16R"])
        validate(example("procedure"))
        cases = (
            ("unknown designator", lambda doc: doc.update(runways=["16X"])),
            ("no runway", lambda doc: doc.update(runways=[])),
            ("repeated runway", lambda doc: doc.update(runways=["16R", "16R"])),
            ("not an end of the airfield", lambda doc: doc.update(runways=["10"])),
        )
        for name, change in cases:
            with self.subTest(case=name):
                document = example("procedure")
                change(document)
                rejected(self, document)
        for identifier in ("ojms-salat1", "ojms-par31"):
            self.assertEqual(procedure(identifier)["runways"], ["31"])

    def test_procedure_links_to_holds_and_the_msa_in_the_catalogues(self):
        resources = example("resources")["resources"]
        self.assertEqual(set(resources["holdings"]), {"ghi-hold"})
        self.assertEqual(set(resources["msas"]), {"ojms-msa"})
        self.assertEqual((resources["places"]["ojms"]["holdings"], resources["places"]["ojms"]["msas"]), (["ghi-hold"], ["ojms-msa"]))
        record = procedure("ojms-i31")
        self.assertEqual((record["holdings"], record["msa"]), (["ghi-hold"], "ojms-msa"))
        cases = (
            ("unresolved hold", lambda doc: doc.update(holdings=["nowhere"])),
            ("unresolved MSA", lambda doc: doc.update(msa="nowhere")),
            ("no hold", lambda doc: doc.update(holdings=[])),
            ("repeated hold", lambda doc: doc.update(holdings=["ghi-hold", "ghi-hold"])),
            ("MSA as a list", lambda doc: doc.update(msa=["ojms-msa"])),
        )
        for name, change in cases:
            with self.subTest(case=name):
                validate_procedure(self, "ojms-i31", change, valid=False)
        for field, key in (("holdings", "ghi-hold"), ("msas", "ojms-msa")):
            with self.subTest(list=field):
                catalogue = example("resources")
                catalogue["resources"][field][key]["airfield"] = "h4"
                with self.assertRaises(ContractError):
                    validate_document(procedure("ojms-i31"), resource_document=catalogue)
                catalogue = example("resources")
                catalogue["resources"]["places"]["ojms"][field] = ["other"]
                catalogue["resources"][field]["other"] = deepcopy(catalogue["resources"][field][key]) | {"id": "other"}
                with self.assertRaises(ContractError):
                    validate_document(catalogue, "resources")

    def test_hold_record_names_its_airfield(self):
        record = deepcopy(example("resources")["resources"]["holdings"]["ghi-hold"])
        self.assertEqual(record["airfield"], "ojms")
        record["resources_ref"] = {"id": "oir-resources", "revision": example("resources")["meta"]["revision"]}
        validate_document(record, resource_document=example("resources"))
        catalogue = example("resources")
        catalogue["resources"]["places"]["ojms"]["holdings"] = ["other"]
        catalogue["resources"]["holdings"]["other"] = deepcopy(record) | {"id": "other"}
        del catalogue["resources"]["holdings"]["other"]["resources_ref"]
        with self.assertRaisesRegex(ContractError, "does not list"):
            validate_document(record, resource_document=catalogue)

    def test_top_altitude_belongs_to_a_departure(self):
        self.assertEqual(procedure("ojms-salat1")["top_altitude"], feet(6000))
        validate_procedure(self, "ojms-salat1", lambda doc: doc.update(top_altitude={"value": 150, "unit": "flight_level", "reference": "FL"}))
        for identifier in ("ojms-i31", "ojms-r13"):
            with self.subTest(procedure=identifier):
                validate_procedure(self, identifier, lambda doc: doc.update(top_altitude=feet(6000)), valid=False)
        validate_procedure(self, "ojms-salat1", lambda doc: doc.update(top_altitude={"value": 6000, "unit": "ft"}), valid=False)

    def test_procedure_remarks_are_free_text(self):
        self.assertEqual(len(procedure("ojms-i31")["remarks"]), 2)
        validate_procedure(self, "ojms-salat1", lambda doc: doc.update(remarks=["Departure end of runway 31 is not usable at night."]))
        for value in ([], [""], "Remark"):
            with self.subTest(value=value):
                validate_procedure(self, "ojms-salat1", lambda doc: doc.update(remarks=value), valid=False)

    def test_threshold_crossing_height_belongs_to_a_non_radar_approach(self):
        self.assertEqual(procedure("ojms-r13")["threshold_crossing_height"], {"value": 50, "unit": "ft"})
        validate_procedure(self, "ojms-i31", lambda doc: doc.update(threshold_crossing_height={"value": 54, "unit": "ft"}))
        for identifier in ("ojms-salat1", "ojms-par31", "ojms-asr13"):
            with self.subTest(procedure=identifier):
                validate_procedure(self, identifier, lambda doc: doc.update(threshold_crossing_height={"value": 50, "unit": "ft"}), valid=False)
        validate_procedure(self, "ojms-r13", lambda doc: doc.update(threshold_crossing_height={"value": 0, "unit": "ft"}), valid=False)

    def test_a_fix_can_be_defined_by_a_radial_and_a_distance(self):
        def defined(document):
            return next(leg["fix"] for leg in legs(document) if leg.get("fix", {}).get("ident") == "FAF31")

        definition = defined(procedure("ojms-i31"))["radial_dme"]
        self.assertEqual(definition["navaid"], {"kind": "control_measure", "id": "ghi"})
        self.assertEqual(len(definition["additional_radials"]), 1)

        def without_extra(document):
            del defined(document)["radial_dme"]["additional_radials"]

        def without_definition(document):
            del defined(document)["radial_dme"]

        validate_procedure(self, "ojms-i31", without_extra)
        validate_procedure(self, "ojms-i31", without_definition)
        cases = (
            ("unresolved navaid", lambda doc: defined(doc)["radial_dme"].update(navaid={"kind": "control_measure", "id": "nowhere"})),
            ("an airfield as a navaid", lambda doc: defined(doc)["radial_dme"].update(navaid={"kind": "airfield", "id": "ojms"})),
            ("no distance", lambda doc: defined(doc)["radial_dme"].pop("distance")),
            ("no radial", lambda doc: defined(doc)["radial_dme"].pop("radial")),
            ("distance in an extra radial", lambda doc: defined(doc)["radial_dme"]["additional_radials"][0].update(distance={"value": 5, "unit": "nm"})),
            ("empty extra radials", lambda doc: defined(doc)["radial_dme"].update(additional_radials=[])),
            ("no position", lambda doc: defined(doc).pop("position")),
        )
        for name, change in cases:
            with self.subTest(case=name):
                validate_procedure(self, "ojms-i31", change, valid=False)

    def test_a_localizer_can_be_a_recommended_navaid_or_a_fix(self):
        leg = next(leg for leg in legs(procedure("ojms-i31")) if leg.get("recommended_navaid", {}).get("kind") == "localizer")
        self.assertEqual(leg["recommended_navaid"], {"kind": "localizer", "id": "ojms-ils-31"})

        def fix_on_localizer(document):
            target = next(item for item in legs(document) if item["leg_type"] == "track_to_fix")
            target["fix"] = {"kind": "localizer", "id": "ojms-ils-26"}

        validate_procedure(self, "ojms-i31", fix_on_localizer)
        cases = (
            ("unresolved localizer", lambda doc: legs(doc)[3].update(recommended_navaid={"kind": "localizer", "id": "nowhere"})),
            ("unresolved localizer fix", lambda doc: legs(doc)[1].update(fix={"kind": "localizer", "id": "nowhere"})),
            ("localizer selection without an identifier", lambda doc: legs(doc)[3].update(recommended_navaid={"kind": "localizer"})),
            ("an airfield as a navaid", lambda doc: legs(doc)[3].update(recommended_navaid={"kind": "airfield", "id": "ojms"})),
        )
        for name, change in cases:
            with self.subTest(case=name):
                validate_procedure(self, "ojms-i31", change, valid=False)

    def test_theta_and_rho_need_the_recommended_navaid(self):
        departure = procedure("ojms-salat1")
        radial = next(leg for leg in legs(departure) if leg["leg_type"] == "course_to_radial")
        self.assertEqual((radial["theta"], radial["recommended_navaid"]["id"]), (magnetic(355.0), "ghi"))
        navaid = {"kind": "control_measure", "id": "ghi"}
        cases = (
            ("radial leg without theta", lambda doc: legs(doc)[1].pop("theta"), False),
            ("radial leg without a navaid", lambda doc: legs(doc)[1].pop("recommended_navaid"), False),
            ("heading to a radial", lambda doc: legs(doc)[1].update(leg_type="heading_to_radial"), True),
            ("theta on a track to a fix", lambda doc: legs(doc)[3].update(theta=magnetic(38.6), recommended_navaid=navaid), True),
            ("theta without a navaid", lambda doc: legs(doc)[3].update(theta=magnetic(38.6)), False),
            ("rho on a track to a fix", lambda doc: legs(doc)[3].update(rho={"value": 13.6, "unit": "nm"}, recommended_navaid=navaid), True),
            ("rho without a navaid", lambda doc: legs(doc)[3].update(rho={"value": 13.6, "unit": "nm"}), False),
            ("rho of zero", lambda doc: legs(doc)[3].update(rho={"value": 0, "unit": "nm"}, recommended_navaid=navaid), False),
            ("theta of 360 degrees", lambda doc: legs(doc)[1].update(theta={"value": 360, "reference": "magnetic"}), False),
        )
        for name, change, valid in cases:
            with self.subTest(case=name):
                validate_procedure(self, "ojms-salat1", change, valid=valid)

        def arc(document):
            target = legs(document)[3]
            target.update(leg_type="arc_to_fix", turn_direction="right")
            return target

        validate_procedure(self, "ojms-salat1", lambda doc: arc(doc).update(recommended_navaid=navaid, rho={"value": 13.6, "unit": "nm"}))
        validate_procedure(self, "ojms-salat1", lambda doc: arc(doc).update(recommended_navaid=navaid), valid=False)
        validate_procedure(self, "ojms-salat1", lambda doc: arc(doc).update(rho={"value": 13.6, "unit": "nm"}), valid=False)

    def test_glide_slope_intercept_and_stepdown_altitudes_have_one_limit(self):
        kinds = {leg["altitude"]["kind"] for identifier in ("ojms-i31", "ojms-asr13") for leg in legs(procedure(identifier)) if "altitude" in leg}
        self.assertLessEqual({"glide_slope_intercept", "stepdown"}, kinds)
        for kind in ("glide_slope_intercept", "stepdown"):
            for name, altitude, valid in (
                    ("lower limit", {"kind": kind, "lower": feet(3300)}, True),
                    ("no limit", {"kind": kind}, False),
                    ("upper limit only", {"kind": kind, "upper": feet(3300)}, False),
                    ("both limits", {"kind": kind, "lower": feet(3300), "upper": feet(3600)}, False)):
                with self.subTest(kind=kind, case=name):
                    validate_procedure(self, "ojms-i31", lambda doc: legs(doc)[1].update(altitude=altitude), valid=valid)

            def hold(document):
                target = next(leg for leg in legs(document) if leg["leg_type"] == "hold_to_fix")
                target["hold"]["altitude"] = {"kind": kind, "lower": feet(5000)}

            with self.subTest(kind=kind, case="hold altitude"):
                validate_procedure(self, "ojms-i31", hold, valid=False)

    def test_glide_slope_intercept_altitude_belongs_to_that_kind_only(self):
        for kind, extra, valid in (
                ("glide_slope_intercept", feet(3400), True), ("stepdown", feet(3400), False), ("at", feet(3400), False)):
            with self.subTest(kind=kind):
                altitude = {"kind": kind, "lower": feet(3300), "glide_slope_intercept_altitude": extra}
                validate_procedure(self, "ojms-i31", lambda doc: legs(doc)[1].update(altitude=altitude), valid=valid)

        def hold(document):
            target = next(leg for leg in legs(document) if leg["leg_type"] == "hold_to_fix")
            target["hold"]["altitude"] = {"kind": "at", "lower": feet(5000), "glide_slope_intercept_altitude": feet(3400)}

        validate_procedure(self, "ojms-i31", hold, valid=False)

    def test_holding_remarks_share_the_procedure_definition(self):
        records, _ = schemas()
        schema = records["procedure"]["$defs"]["Remarks"]
        self.assertEqual(records["holding"]["properties"]["remarks"]["$ref"].rsplit("#", 1)[1], "/$defs/Remarks")
        self.assertEqual(schema["items"], {"type": "string", "minLength": 1})
        document = example("holding")
        validate(document)
        for remarks, valid in ((["Expect further clearance."], True), ([], False), ([""], False)):
            with self.subTest(remarks=remarks):
                changed = {**document, "remarks": remarks}
                if valid:
                    validate(changed)
                else:
                    rejected(self, changed)

    def test_transition_type_names_the_role_of_the_transition(self):
        types = {transition["transition_type"] for identifier in ("ojms-i31", "ojms-salat1") for transition in procedure(identifier)["transitions"]}
        self.assertLessEqual({"approach_transition", "final_approach", "runway_transition"}, types)
        for value, valid in (("common_route", True), ("enroute_transition", True), ("runway", False)):
            with self.subTest(value=value):
                validate_procedure(self, "ojms-i31", lambda doc: doc["transitions"][0].update(transition_type=value), valid=valid)

    def test_localizer_has_an_optional_elevation(self):
        document = example("localizer")
        validate(document)
        document["elevation"] = feet(5333)
        validate(document)
        document["elevation"] = {"value": "high", "unit": "ft"}
        rejected(self, document)

    def test_approach_fix_is_a_list_of_roles(self):
        roles = {role for identifier in ("ojms-i31", "ojms-asr13", "ojms-r13") for leg in legs(procedure(identifier)) for role in leg.get("approach_fix", [])}
        self.assertLessEqual({"stepdown_fix", "missed_approach_holding_fix", "initial_approach_fix", "intermediate_fix"}, roles)
        self.assertEqual(legs(procedure("ojms-r13"))[0]["approach_fix"], ["initial_approach_fix", "intermediate_fix"])
        for name, value, valid in (
                ("one role", ["stepdown_fix"], True),
                ("a role as a string", "stepdown_fix", False),
                ("no role", [], False),
                ("repeated role", ["stepdown_fix", "stepdown_fix"], False),
                ("unknown role", ["alternate_fix"], False)):
            with self.subTest(case=name):
                validate_procedure(self, "ojms-i31", lambda doc: legs(doc)[1].update(approach_fix=value), valid=valid)
        self.assertTrue(all(isinstance(leg.get("approach_fix", []), list) for leg in legs(example("procedure"))))

    def test_dcs_beacon_is_dcs_data_of_a_navaid_or_a_localizer(self):
        beacon = {"ident": "IDQQ", "frequency": {"value": 111.1, "unit": "MHz"}, "channel": 3}
        for name in ("navaid", "localizer"):
            for case, value, valid in (
                    ("full beacon", beacon, True),
                    ("ident only", {"ident": "IDQQ"}, True),
                    ("empty beacon", {}, False),
                    ("channel of zero", {"channel": 0}, False),
                    ("unknown key", {"ident": "IDQQ", "type": "ILS"}, False),
                    ("frequency without a unit", {"frequency": {"value": 111.1}}, False)):
                with self.subTest(record=name, case=case):
                    document = example(name)
                    document["extensions"] = {"sim": {"dcs": {"beacon": value}}}
                    if valid:
                        validate(document)
                    else:
                        rejected(self, document)
        for name in ("airfield", "procedure", "msa"):
            with self.subTest(record=name):
                document = example(name)
                document["extensions"] = {"sim": {"dcs": {"beacon": beacon}}}
                rejected(self, document)
        self.assertNotIn("beacon", schemas()[0]["measures/navaid"]["properties"])

    def test_new_navaid_classes_select_their_frequency(self):
        def navaid(change):
            document = example("navaid")
            del document["tacan"]
            change(document)
            return document

        kilohertz = {"value": 380, "unit": "kHz"}
        for name, change, valid in (
                ("NDB with a DME", lambda doc: doc.update({"class": "NDB_DME", "frequency": kilohertz}), True),
                ("NDB with a DME on a VHF frequency", lambda doc: doc.update({"class": "NDB_DME", "frequency": {"value": 114.7, "unit": "MHz"}}), False),
                ("NDB with a DME without a frequency", lambda doc: (doc.update({"class": "NDB_DME"}), doc.pop("frequency")), False),
                ("marker beacon without a frequency", lambda doc: (doc.update({"class": "MARKER"}), doc.pop("frequency")), True),
                ("marker beacon on 75 MHz", lambda doc: doc.update({"class": "MARKER", "frequency": {"value": 75, "unit": "MHz"}}), True),
                ("marker beacon in kilohertz", lambda doc: doc.update({"class": "MARKER", "frequency": kilohertz}), False),
                ("RSBN on UHF", lambda doc: doc.update({"class": "RSBN", "frequency": {"value": 870, "unit": "MHz"}}), True),
                ("RSBN without a frequency", lambda doc: (doc.update({"class": "RSBN"}), doc.pop("frequency")), False),
                ("RSBN in kilohertz", lambda doc: doc.update({"class": "RSBN", "frequency": kilohertz}), False)):
            with self.subTest(case=name):
                document = navaid(change)
                if valid:
                    validate(document)
                else:
                    rejected(self, document)

    def test_prmg_is_a_landing_system_of_the_localizer_record(self):
        localizer = example("localizer")
        self.assertNotIn("system", localizer)
        for value, valid in (("ils", True), ("prmg", True), ("mls", False), ("PRMG", False)):
            with self.subTest(system=value):
                document = example("localizer")
                document["system"] = value
                if valid:
                    validate(document)
                else:
                    rejected(self, document)
        self.assertNotIn("PRMG", schemas()[0]["measures/navaid"]["properties"]["class"]["enum"])

    def test_glide_slope_position_is_optional(self):
        document = example("localizer")
        slope = document["glide_slope"]
        self.assertIn("position", slope)
        del slope["position"]
        validate(document)
        del slope["angle_deg"]
        rejected(self, document)
        document = example("localizer")
        document["glide_slope"]["position"] = {"latitude": 91, "longitude": 0}
        rejected(self, document)


def feet(value):
    return {"value": value, "unit": "ft", "reference": "MSL"}


def procedure(identifier):
    """An OJMS procedure of the OIR resource catalogue, as a standalone document."""
    resources = example("resources")
    record = deepcopy(resources["resources"]["instrument_procedures"][identifier])
    return {"$schema": example("procedure")["$schema"], **record,
            "resources_ref": {"id": resources["meta"]["id"], "revision": resources["meta"]["revision"]}}


def validate_procedure(test, identifier, change=None, valid=True):
    document = procedure(identifier)
    if change:
        change(document)
    if valid:
        validate(document)
    else:
        rejected(test, document)


if __name__ == "__main__":
    unittest.main()
