"""Control-measure catalogue and contracts: what a measure document may and may not say."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, schemas, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


def catalogue():
    return json.loads((ROOT / "catalogues/control-measures.json").read_text())


def entry(code):
    return next(item for item in catalogue()["types"] if item["code"] == code)


APP_LABELS = ("CAP_STATION", "TANKER_TRACK", "AEW_ORBIT", "MARSHALL", "CORRIDOR", "KILLBOX", "KEYHOLE", "PROC_POINT",
              "HELO_POS", "CSAR_POINT", "AIC_SECTOR", "SAR", "SAFE", "ANCHOR", "EGRESS_PT", "WAYPOINT")


def document_for(code):
    """An authored example of the code's contract, retyped to the code or to its projection."""
    item = entry(code)
    for path in sorted((ROOT / "examples").rglob("*.json")):
        document = json.loads(path.read_text())
        if document.get("$schema") == item["schema"] and path.parent.name not in {"minimal", "maximal"}:
            document.update(copy.deepcopy(item.get("projection", {"type": code})))
            document.pop("airspace_class_code", None)
            if code == "RFA" or "restrictions" in document:
                document.setdefault("restrictions", ["Coordinate fires that exceed the stated limits."])
            return document
    raise AssertionError("no authored example for " + item["schema"])


def with_geometry(document, path, geometry):
    result = copy.deepcopy(document)
    if path == "components/geometry":
        for part in result["components"]:
            part.update(geometry=copy.deepcopy(geometry), operation="add")
    else:
        result["geometry"] = copy.deepcopy(geometry)
    return result


class CatalogueTests(unittest.TestCase):
    def test_every_catalogue_code_validates_against_its_contract(self):
        for item in catalogue()["types"]:
            with self.subTest(code=item["code"]):
                document = document_for(item["code"])
                validate_document(document)
                validate_document(document, "control-measure")

    def test_codes_are_real_doctrinal_codes_with_expanded_names_and_sources(self):
        types = catalogue()["types"]
        codes = {item["code"] for item in types}
        self.assertEqual(codes & set(APP_LABELS), set())
        for item in types:
            with self.subTest(code=item["code"]):
                self.assertNotEqual(item["name"], item["code"])
                self.assertTrue(item["definition"])
                self.assertTrue(item["definition_source"]["locator"])
        self.assertEqual(entry("ACA")["name"], "Airspace Coordination Area")
        self.assertEqual(entry("NFA")["name"], "No-Fire Area")
        self.assertEqual(entry("RFA")["name"], "Restrictive Fire Area")

    def test_app_labels_are_rejected_as_measure_types(self):
        roz = example("measures/roz")
        for label in ("CAP_STATION", "KILLBOX", "CORRIDOR", "TANKER_TRACK", "EGRESS_PT"):
            with self.subTest(label=label):
                document = dict(roz, type=label)
                with self.assertRaises(ContractError):
                    validate_document(document, "control-measure")

    def test_aliases_are_doctrinal_synonyms_of_catalogue_codes(self):
        cat = catalogue()
        codes = {item["code"] for item in cat["types"]}
        self.assertEqual(set(cat["aliases"]), {"HIMEZ", "LOMEZ", "SHORADEZ", "ROA"})
        examples = {"MEZ": "measures/mez", "ROZ": "measures/roz"}
        for name, alias in cat["aliases"].items():
            with self.subTest(alias=name):
                self.assertNotIn(name, APP_LABELS)
                self.assertNotIn(name, codes)
                self.assertIn(alias["code"], codes)
                self.assertTrue(alias["definition_source"]["locator"])
                document = example(examples[alias["code"]])
                document.update(alias["values"])
                validate_document(document)

    def test_missile_engagement_zone_kinds_resolve_from_their_alias_codes(self):
        aliases = catalogue()["aliases"]
        self.assertEqual({name: alias["values"] for name, alias in aliases.items() if alias["code"] == "MEZ"},
                         {"HIMEZ": {"mez_kind": "high"}, "LOMEZ": {"mez_kind": "low"},
                          "SHORADEZ": {"mez_kind": "short_range"}})
        self.assertEqual(aliases["SHORADEZ"]["definition_source"]["source"], "joint-jp-3-01-2017")
        shoradez = example("measures/shoradez")
        self.assertEqual((shoradez["type"], shoradez["mez_kind"]), ("MEZ", "short_range"))
        validate_document(shoradez)

    def test_restricted_operations_area_is_only_an_older_name_of_the_zone(self):
        alias = catalogue()["aliases"]["ROA"]
        self.assertEqual((alias["code"], alias["values"]), ("ROZ", {}))
        self.assertEqual(alias["definition_source"]["source"], "joint-jp-3-52-2004")
        with self.assertRaises(ContractError):
            validate_document(dict(example("measures/roz"), type="ROA"), "control-measure")

    def test_alias_and_application_labels_are_not_measure_types(self):
        mez = example("measures/mez")
        validate_document(mez)
        for code in ("HIMEZ", "LOMEZ", "SHORADEZ"):
            with self.subTest(code=code), self.assertRaises(ContractError):
                validate_document(dict(mez, type=code), "control-measure")
        for field, value in (("mez_kind", "HIGH"), ("mez_kind", "medium")):
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                validate_document(dict(mez, **{field: value}))

    def test_categories_follow_their_first_party_sources(self):
        self.assertEqual(entry("JEZ")["category"], "adm")
        self.assertEqual(entry("MEZ")["category"], "adm")
        self.assertEqual(entry("ACA")["category"], "acm")
        self.assertIn("5.d", entry("ACA")["definition_source"]["locator"])
        for code in ("NFA", "RFA", "FFA", "KB", "FSCL", "CFL"):
            self.assertEqual(entry(code)["category"], "fscm")

    def test_samez_is_the_annex_b_code_of_the_missile_engagement_zone(self):
        samez = entry("SAMEZ")
        self.assertEqual(samez["schema"], entry("MEZ")["schema"])
        self.assertEqual(samez["projection"], {"type": "MEZ"})
        self.assertIn("Table B-5", samez["definition_source"]["locator"])

    def test_listed_geometries_validate_and_unlisted_ones_do_not(self):
        from openaix.build.measures import probe_geometries
        probes = probe_geometries()
        for item in catalogue()["types"]:
            if "geometries" not in item:
                continue
            base = document_for(item["code"])
            authored = [base["geometry"]] if "geometry" in base else [part["geometry"] for part in base.get("components", [])]
            for kind, probe in probes.items():
                candidates = [probe, *(geometry for geometry in authored if geometry["kind"] == kind)]
                accepted = False
                for candidate in candidates:
                    try:
                        validate_document(with_geometry(base, item["geometry_path"], candidate))
                        accepted = True
                        break
                    except ContractError:
                        pass
                with self.subTest(code=item["code"], kind=kind):
                    self.assertEqual(accepted, kind in item["geometries"])
        self.assertNotIn("point", entry("NFZ")["geometries"])
        self.assertEqual(entry("MRR")["geometries"], ["corridor"])

    def test_projected_codes_use_the_shared_point_airspace_and_airway_contracts(self):
        records, _ = schemas()
        airway_types = records["measures/airway"]["properties"]["airway_type"]["enum"]
        airspace_types = records["measures/airspace"]["properties"]["airspace_type"]["enum"]
        roles = records["measures/point"]["properties"]["roles"]["items"]["enum"]
        for item in catalogue()["types"]:
            projection = item.get("projection")
            if not projection:
                continue
            with self.subTest(code=item["code"]):
                if projection["type"] == "AIRWAY":
                    self.assertIn(projection["airway_type"], airway_types)
                elif projection["type"] == "AIRSPACE":
                    self.assertIn(projection["airspace_type"], airspace_types)
                elif projection["type"] == "POINT":
                    self.assertLessEqual(set(projection["roles"]), set(roles))
                else:
                    self.assertEqual(projection["type"], "MEZ")

    def test_catalogue_has_no_planner_or_exclusion_bookkeeping(self):
        cat = catalogue()
        self.assertNotIn("excluded_source_types", cat)
        for item in cat["types"]:
            self.assertFalse([key for key in item if key.startswith("planner_")], item["code"])


class ContractTests(unittest.TestCase):
    def test_control_measure_union_references_contracts_without_inline_copies(self):
        records, _ = schemas()
        union = records["common"]["$defs"]["ControlMeasure"]["oneOf"]
        identifiers = {schema["$id"] for name, schema in records.items() if name.startswith("measures/")}
        references = {branch["$ref"] for branch in union if "$ref" in branch}
        self.assertEqual(references, identifiers)
        inline = [branch for branch in union if "$ref" not in branch]
        self.assertEqual(len(inline), 1)
        self.assertIn("pattern", inline[0]["properties"]["type"])

    def test_references_inside_union_members_still_resolve(self):
        order = example("aco-oir.maximal")
        validate_document(order)
        order["resources"]["control_measures"]["rescue-reservation"]["controlling_agency"] = "missing-agency"
        with self.assertRaises(ContractError) as raised:
            validate_document(order)
        self.assertEqual(raised.exception.path, "/resources/control_measures/rescue-reservation/controlling_agency")

    def test_instances_carry_no_category_source_type_or_planner_attributes(self):
        cases = (("measures/roz", "category", "acm"), ("measures/kb", "source_type", "KILLBOX"), ("orbit", "source_type", "CAP_STATION"),
                 ("airspace-class-b", "source_type", "CLSB"), ("measures/ip", "source_type", "IP"), ("measures/ip", "category", "arm"),
                 ("measures/kb", "attributes", {"killboxKind": "PURPLE"}), ("measures/tc", "corridor_kind", "TRANSIT"),
                 ("measures/tc", "one_way", True))
        for name, field, value in cases:
            with self.subTest(example=name, field=field):
                document = example(name)
                document[field] = value
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_kill_box_kind_is_lower_case_only_and_firing_status_is_not_a_measure_field(self):
        document = example("measures/kb")
        for kind in ("BLUE", "PURPLE"):
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                validate_document(dict(document, killbox_kind=kind))
        with self.assertRaises(ContractError):
            validate_document(dict(document, killbox_status="open"))

    def test_kill_box_floor_follows_its_kind(self):
        purple = example("measures/kb")
        validate_document(purple)
        purple["components"][0]["lower_limit"] = {"surface": True}
        with self.assertRaises(ContractError) as raised:
            validate_document(purple)
        self.assertEqual(raised.exception.path, "/components/0/lower_limit")
        blue = example("measures/kb")
        blue["killbox_kind"] = "blue"
        with self.assertRaises(ContractError):
            validate_document(blue)
        blue["components"][0]["lower_limit"] = {"value": 0, "unit": "ft", "reference": "AGL"}
        self.assertEqual(import_document(export_document(blue)), blue)

    def test_blue_kill_box_may_start_at_its_coordinating_altitude_but_no_other_floor(self):
        blue = example("measures/kb")
        blue["killbox_kind"] = "blue"
        floor = {"value": 8000, "unit": "ft", "reference": "MSL"}
        blue["components"][0]["lower_limit"] = dict(floor)
        with self.assertRaises(ContractError):
            validate_document(blue)
        blue["coordinating_altitude"] = dict(floor)
        validate_document(blue)
        blue["coordinating_altitude"] = {"value": 6000, "unit": "ft", "reference": "MSL"}
        with self.assertRaises(ContractError) as raised:
            validate_document(blue)
        self.assertEqual(raised.exception.path, "/components/0/lower_limit")
        blue["coordinating_altitude"] = {"value": 8000, "unit": "ft", "reference": "AGL"}
        with self.assertRaises(ContractError):
            validate_document(blue)

    def test_kill_box_grid_label_is_display_text_beside_decimal_coordinates(self):
        document = example("measures/kb")
        document["grid_label"] = "4 keypad 7"
        validate_document(document)
        document["grid"] = {"system": "GARS", "cell": "006AG"}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_identification_safety_range_requires_a_range(self):
        document = example("measures/isr")
        self.assertEqual(import_document(export_document(document)), document)
        del document["range"]
        with self.assertRaises(ContractError):
            validate_document(document)
        document = example("measures/isr")
        document["range"] = {"value": 15}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_missile_arc_width_defaults_to_ten_degrees_within_one_revolution(self):
        records, _ = schemas()
        self.assertEqual(records["measures/misarc"]["properties"]["width_deg"]["default"], 10)
        document = example("measures/misarc")
        del document["width_deg"]
        validate_document(document)
        for width, valid in ((0, False), (-5, False), (360, True), (361, False), (25, True)):
            with self.subTest(width=width):
                document["width_deg"] = width
                if valid:
                    validate_document(document)
                else:
                    with self.assertRaises(ContractError):
                        validate_document(document)
        document = example("measures/misarc")
        del document["axis"]
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_buffer_zone_requires_vertical_limits(self):
        document = example("measures/bz")
        for field in ("lower_limit", "upper_limit"):
            with self.subTest(field=field):
                invalid = copy.deepcopy(document)
                del invalid["components"][0][field]
                with self.assertRaises(ContractError):
                    validate_document(invalid)
        invalid = copy.deepcopy(document)
        invalid["geometry"] = invalid["components"][0]["geometry"]
        del invalid["components"]
        with self.assertRaises(ContractError):
            validate_document(invalid)

    def test_refuelling_area_carries_no_tanker_service_fields(self):
        document = example("measures/aara")
        validate_document(document)
        for field, value in (("refueling_method", "boom"), ("tanker_types_supported", ["KC-135"])):
            with self.subTest(field=field), self.assertRaises(ContractError):
                validate_document(dict(document, **{field: value}))

    def test_corridor_routes_need_a_width_and_air_routes_may_be_centrelines(self):
        route = example("measures/tc")
        centreline = {"kind": "line", "points": route["geometry"]["points"]}
        for code in ("TC", "TR", "LLTR", "SC", "MRR", "SL", "APPCOR", "TMRR"):
            with self.subTest(code=code), self.assertRaises(ContractError):
                validate_document(dict(route, type=code, geometry=centreline))
        for code in ("AIRRTE", "SAAFR"):
            with self.subTest(code=code):
                validate_document(dict(route, type=code, geometry=centreline))

    def test_restrictive_fire_area_states_its_restrictions(self):
        document = example("measures/rfa")
        del document["restrictions"]
        with self.assertRaises(ContractError):
            validate_document(document)
        document["type"] = "NFA"
        validate_document(document)

    def test_new_codes_use_the_shape_family_of_their_doctrine(self):
        expected = {"RFL": "fire-support-line", "BCL": "fire-support-line", "PL": "line", "BOUNDARY": "line", "LOA": "line",
                    "LD": "line", "LC": "line", "OBJ": "area", "BP": "area", "AA": "area", "NAI": "area", "TAI": "area",
                    "FSA": "area", "AIRCOR": "route", "CA": "cl", "TRP": "point", "FSS": "point"}
        for code, contract in expected.items():
            with self.subTest(code=code):
                self.assertTrue(entry(code)["schema"].startswith("urn:openaix:schema:" + ("" if contract == "point" else "measure-") + contract + ":"))
        self.assertEqual(entry("TRP")["projection"], {"type": "POINT", "roles": ["target_reference"]})
        self.assertEqual(entry("FSS")["projection"], {"type": "POINT", "roles": ["fire_support_station"]})
        self.assertEqual(entry("PL")["geometries"], ["line"])
        self.assertNotIn("line", entry("OBJ")["geometries"])

    def test_new_codes_carry_their_doctrinal_category(self):
        for code in ("RFL", "BCL"):
            self.assertEqual(entry(code)["category"], "fscm")
        for code in ("AIRCOR", "CA"):
            self.assertEqual(entry(code)["category"], "acm")
        for code in ("PL", "BOUNDARY", "OBJ", "BP", "AA", "TRP", "NAI", "TAI", "LOA", "LD", "LC", "FSA", "FSS"):
            with self.subTest(code=code):
                self.assertEqual(entry(code)["category"], "mcm")
                self.assertIn("mcm", entry(code)["definition_source"]["note"])

    def test_restrictive_fire_line_is_a_line_between_converging_forces(self):
        rfl = example("measures/rfl")
        validate_document(rfl)
        for kind in ("polygon", "circle"):
            with self.subTest(kind=kind), self.assertRaises(ContractError):
                validate_document(dict(rfl, geometry=example("measures/nfa")["geometry"] if kind == "circle"
                                       else example("measures/rfa")["geometry"]))

    def test_air_corridor_needs_a_corridor_width_and_vertical_limits(self):
        corridor = dict(example("measures/tc"), type="AIRCOR")
        validate_document(corridor)
        with self.assertRaises(ContractError):
            validate_document(dict(corridor, geometry={"kind": "line", "points": corridor["geometry"]["points"]}))
        without_altitude = dict(corridor)
        without_altitude.pop("altitude")
        with self.assertRaises(ContractError):
            validate_document(without_altitude)

    def test_coordinating_altitude_is_one_level_on_the_coordination_level_contract(self):
        ca = example("measures/ca")
        self.assertEqual(ca["type"], "CA")
        self.assertEqual(entry("CA")["schema"], entry("CL")["schema"])
        validate_document(ca)
        with self.assertRaises(ContractError):
            validate_document(dict(ca, geometry={"kind": "vertical", "height": ca["geometry"]["level"],
                                                 "altitude": ca["geometry"]["level"]}))
        with self.assertRaises(ContractError):
            validate_document(dict(ca, type="COORDINATING_ALTITUDE"))

    def test_target_reference_point_is_a_point_role_not_a_point_type(self):
        trp = example("measures/trp")
        self.assertEqual((trp["type"], trp["roles"]), ("POINT", ["target_reference"]))
        validate_document(trp)
        with self.assertRaises(ContractError):
            validate_document(dict(trp, type="TRP"), "control-measure")

    def test_holding_is_a_use_of_existing_measures_not_a_code(self):
        codes = {item["code"] for item in catalogue()["types"]} | set(catalogue()["aliases"])
        for label in ("HA", "HP", "HOLDING_AREA", "HOLDING_POINT", "CASHA"):
            self.assertNotIn(label, codes)

    def test_saafr_catalogue_entry_shows_both_expansions_with_sources(self):
        expansions = {item["usage"]: item for item in entry("SAAFR")["expansions"]}
        self.assertEqual(set(expansions), {"NATO", "US"})
        self.assertEqual(expansions["US"]["name"], "Standard Use Army Aircraft Flight Route")
        self.assertEqual(expansions["NATO"]["name"], entry("SAAFR")["name"])
        for item in expansions.values():
            self.assertTrue(item["locator"])

    def test_measure_type_must_belong_to_its_contract(self):
        for name, code in (("measures/roz", "FSCL"), ("measures/fscl", "ROZ"), ("measures/tc", "NFZ"), ("measures/nfa", "TC")):
            with self.subTest(example=name, code=code):
                with self.assertRaises(ContractError):
                    validate_document(dict(example(name), type=code))

    def test_examples_use_distinct_shapes_inside_the_oir_period(self):
        from openaix.check.contract import instant
        period = example("aco-oir.maximal")["period"]
        start, end = instant(period["start"], None), instant(period["end"], None)
        shapes = set()
        for path in sorted((ROOT / "examples/measures").glob("*.json")):
            document = json.loads(path.read_text())
            with self.subTest(example=path.name):
                active = document["active"]
                if "start" in active:
                    self.assertGreaterEqual(instant(active["start"], None), start)
                    self.assertLessEqual(instant(active["end"], None), end)
                shape = document.get("geometry") or document.get("position") or [part["geometry"] for part in document.get("components", [])] or document.get("center")
                shapes.add(json.dumps(shape, sort_keys=True))
        self.assertEqual(len(shapes), len(list((ROOT / "examples/measures").glob("*.json"))))


if __name__ == "__main__":
    unittest.main()
