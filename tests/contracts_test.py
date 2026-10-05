import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import (ContractError, capability_report, export_document, import_document, schemas,
                                    validate_document)


def fixture(name):
    return json.loads((ROOT / "examples" / name).read_text())


class ContractTests(unittest.TestCase):
    def test_each_measure_example_declares_the_contract_of_its_type(self):
        records, _ = schemas()
        catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
        contracts = {item.get("projection", {}).get("type", item["code"]): item["schema"] for item in catalogue["types"]}
        contracts.update({"POINT": records["measures/point"]["$id"], "ORBIT": records["measures/orbit"]["$id"]})
        for path in sorted((ROOT / "examples/measures").glob("*.json")):
            document = json.loads(path.read_text())
            with self.subTest(example=path.name):
                self.assertEqual(document["$schema"], contracts[document["type"]])
                validate_document(document)

    def test_military_air_route_is_distinct_from_civil_airway(self):
        original = fixture("measures/tc.json")
        document = {key: original[key] for key in ("$schema", "id", "name", "geometry", "altitude", "active")}
        document["type"] = "AIRRTE"
        validate_document(document)
        document["segments"] = fixture("airway.json")["segments"]
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_measure_specific_fields_do_not_spread_to_unrelated_types(self):
        for name, field, value in (("measures/fscl", "refueling_method", "boom"), ("orbit", "record_type", "ER"), ("measures/kb", "mez_kind", "low")):
            with self.subTest(example=name, field=field):
                document = fixture(name + ".json")
                document[field] = value
                with self.assertRaises(ContractError):
                    validate_document(document)
                order = fixture("aco-all-measures.json")
                order["resources"]["control_measures"][document["id"]] = document
                with self.assertRaises(ContractError):
                    validate_document(order)

    def test_all_source_tasking_variants_and_fields_are_retained(self):
        from openaix.build.convert import load_model
        source = json.loads((ROOT / "sources/opord-builder/ato-0.2.model.json").read_text())
        typed = load_model("ato-0.2")
        records, registry = schemas()
        expected = source["$defs"]["Mission"]["properties"]["tasking"]
        actual = records["ato"]["$defs"]["Mission"]["properties"]["tasking"]
        for branch in expected["oneOf"]:
            self.assertIn(branch, actual["oneOf"])
        self.assertNotIn("discriminator", actual)

        def kinds(model, union):
            return {model["$defs"][branch["$ref"].split("/")[-1]]["properties"]["kind"]["const"] for branch in union["oneOf"]}

        self.assertEqual(kinds(records["ato"], actual) - kinds(source, expected), {"counterair", "counterland_control"})
        self.assertEqual({m["tasking"]["kind"] for m in fixture("ato-oir.json")["missions"]}, kinds(records["ato"], actual))
        # Decided cuts (ORDERS-01/05): definitions replaced by shared contracts or removed, and removed fields.
        replaced = {"Place", "Agency", "AirspaceRef", "AirspaceSelection", "Circle", "Polygon", "Corridor",
                    "Weather", "WeatherPeriodForecast", "LightData", "AirspaceControl", "GeoRef", "AARTrack", "AWACSOrbit",
                    "AICSector", "CAPTrack", "AirspaceZone", "MinimumRiskRoute", "DCSObjectRef",
                    # The SCL record (schemas/scl.schema.json) replaces the source SCL and its payload union.
                    "SCL", "SummaryPayload", "StationPayload", "CleanPayload"}
        # DCS-only object names became simulator bindings: `sim_bindings` and `sim_objects` (SimObjectRef).
        removed = {"Flight": {"refueling_method", "dcs_group"}, "Mission": {"briefing"}, "CargoItem": {"mass_each"},
                   "AircraftOverride": {"dcs_unit"}, "Aimpoint": {"dcs_objects"}, "Store": {"dcs_clsid"}}
        for name, definition in typed["$defs"].items():
            if name in replaced:
                continue
            with self.subTest(model=name):
                target = records["ato"].get("$defs", {}).get(name)
                if target is None:
                    if name == "Resources":
                        target = records["resources"]["$defs"]["ResourceData"]
                    else:
                        target = next(record["$defs"][name] for record in (records["resources"], records["common"], records["scl"]) if name in record.get("$defs", {}))
                if "$ref" in target:
                    target = registry.resolver(records["ato"]["$id"]).lookup(target["$ref"]).contents
                retained = set(definition.get("properties", {})) - removed.get(name, set()) - ({"airspace"} if name == "Resources" else set())
                self.assertLessEqual(retained, set(target.get("properties", {})))

    def test_every_schema_reference_resolves_offline_including_optional_fields(self):
        records, registry = schemas()
        def references(value):
            if isinstance(value, dict):
                if "$ref" in value:
                    yield value["$ref"]
                for child in value.values():
                    yield from references(child)
            elif isinstance(value, list):
                for child in value:
                    yield from references(child)
        for name, schema in records.items():
            for reference in references(schema):
                with self.subTest(schema=name, reference=reference):
                    registry.resolver(schema["$id"]).lookup(reference)

    def test_order_resource_ownership_is_independent_of_ato(self):
        records, _ = schemas()
        self.assertIn("resources:", records["aco"]["properties"]["resources"]["$ref"])
        self.assertIn("resources:", records["ato"]["properties"]["resources"]["$ref"])
        for name in ("GeoRef", "AARTrack", "AWACSOrbit", "AirspaceControl"):
            self.assertNotIn(name, records["ato"]["$defs"])

    def test_all_taskings_round_trip_even_when_execution_support_is_narrow(self):
        document, resources = fixture("ato-oir.json"), fixture("resources.json")
        imported = import_document(export_document(document, resource_document=resources), resource_document=resources)
        self.assertEqual(imported, document)
        before = copy.deepcopy(imported)
        report = capability_report(imported, taskings={"cap", "on_call_cas"}, measures={"ORBIT"})
        self.assertIn("airlift-prince-hassan", report["unhandled_taskings"])
        self.assertIn("pedro-csar", report["unhandled_taskings"])
        self.assertNotIn("cap-falcon", report["unhandled_taskings"])
        self.assertEqual(imported, before)

    def test_unknown_namespaced_measure_data_is_preserved(self):
        document = fixture("aco-all-measures.json")
        document["resources"]["control_measures"]["future"] = {
            "name": "Future", "type": "org.example.future",
            "geometry": {"kind": "description", "text": "Source geometry awaiting a renderer"},
            "extensions": {"org.example.future": {"opaque": [1, False, {"value": "kept"}]}},
        }
        self.assertEqual(import_document(export_document(document)), document)

    def test_unknown_reference_reports_its_path(self):
        document = fixture("aco-all-measures.json")
        document["assignments"][0]["measure"] = "missing"
        with self.assertRaises(ContractError) as error:
            validate_document(document)
        self.assertEqual(error.exception.path, "/assignments/0/measure")

    def test_gate_resolves_its_route_from_shared_resources(self):
        document = fixture("aco-all-measures.json")
        gate = document["resources"]["control_measures"]["silver-gate"]
        gate["route"] = "transit"
        with self.assertRaises(ContractError) as error:
            validate_document(document)
        self.assertTrue(error.exception.path.endswith("/route"))
        resources = fixture("resources.json")["resources"]
        document["resources"]["routes"] = {"transit": resources["routes"]["marshal-entry"]}
        validate_document(document)

    def test_cap_radial_turns_and_leg_units_remain_explicit(self):
        original = fixture("orbit.json")
        for turns in ("left", "right"):
            for length in (10, 20, 30):
                with self.subTest(turns=turns, length=length):
                    document = copy.deepcopy(original)
                    document["geometry"]["turns"] = turns
                    document["geometry"]["leg_length"]["value"] = length
                    self.assertEqual(import_document(export_document(document)), document)
        original["geometry"]["turns"] = "clockwise-ish"
        with self.assertRaises(ContractError):
            validate_document(original)

    def test_one_point_can_serve_several_control_and_navigation_roles(self):
        original = fixture("measures/cp.json")
        for roles in (("control",), ("initial", "egress"), ("gate", "handover", "fix")):
            with self.subTest(roles=roles):
                document = copy.deepcopy(original)
                document["roles"] = list(roles)
                self.assertEqual(import_document(export_document(document)), document)
        for roles in ([], ["control", "control"], ["PROC_POINT"]):
            document = copy.deepcopy(original)
            document["roles"] = roles
            with self.subTest(roles=roles), self.assertRaises(ContractError):
                validate_document(document)

    def test_polyarc_segment_positions_are_not_treated_as_timestamps(self):
        document = fixture("measures/roz.json")
        point = {"latitude": 37.0, "longitude": -115.0}
        document["components"][0]["geometry"] = {"kind": "polyarc", "segments": [
            {"kind": "line", "start": point, "end": {"latitude": 37.2, "longitude": -115.0}},
            {"kind": "arc", "center": point, "radius": {"value": 2, "unit": "nm"}, "start_bearing": {"value": 0, "reference": "true"}, "end_bearing": {"value": 180, "reference": "true"}, "turns": "left"},
        ]}
        validate_document(document)

    def test_fac_and_airfield_examples_are_standalone_resources(self):
        resources = fixture("resources.json")
        for name in ("fac", "c2-agency", "airfield", "farp"):
            with self.subTest(resource=name):
                document = fixture(name + ".json")
                linked = fixture("resources-kden.json") if name == "airfield" else resources
                self.assertEqual(import_document(export_document(document, resource_document=linked), resource_document=linked), document)
        resources["meta"]["revision"] = "2"
        with self.assertRaises(ContractError) as error:
            validate_document(fixture("fac.json"), resource_document=resources)
        self.assertEqual(error.exception.path, "/resources_ref")

    def test_airfield_elevation_cannot_be_an_assigned_flight_level(self):
        document = fixture("airfield.json")
        document["elevation"] = {"value": 180, "reference": "FL", "unit": "flight_level"}
        with self.assertRaises(ContractError):
            validate_document(document, resource_document=fixture("resources-kden.json"))

    def test_catalogue_definition_sources_resolve_to_first_party_authorities(self):
        from openaix.sources.authorities import load_authorities
        from openaix.sources.audit import citation_errors
        authorities = load_authorities()
        catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
        self.assertEqual(citation_errors(catalogue, authorities), [])
        entry = {"code": "TEST", "definition_source": {"source": "unverified-source", "locator": "p. 1"}}
        self.assertEqual(len(citation_errors({"types": [entry]}, authorities)), 1)
        entry["definition_source"] = {"source": "nato-ajp-3-3-5"}
        self.assertEqual(citation_errors({"types": [entry]}, authorities), ["TEST: definition source has no locator"])

    def test_first_party_traverse_level_retains_height_and_altitude(self):
        document = fixture("measures/tl.json")
        document["geometry"] = {"kind": "vertical", "height": {"value": 1000, "unit": "ft", "reference": "AGL"},
                                "altitude": {"value": 2000, "unit": "ft", "reference": "MSL"}}
        self.assertEqual(import_document(export_document(document)), document)
        document["geometry"]["height"]["reference"] = "MSL"
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_frago_preserves_typed_base_and_sparse_change_semantics(self):
        document = fixture("frago.json")
        self.assertEqual(document["base_order"], {"id": "oir-opord", "revision": "1"})
        self.assertEqual(import_document(export_document(document)), document)
        document["changes"][0]["op"] = "remove"
        with self.assertRaises(ContractError):
            validate_document(document)
        del document["changes"][0]["value"]
        validate_document(document)
        document["base_order"] = "unrelated.yaml"
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_schema_validation_does_not_read_remote_references(self):
        document = fixture("ato-oir.json")
        document["$schema"] = "https://example.invalid/unknown.schema.json"
        with self.assertRaises(ContractError):
            import_document(json.dumps(document))

    def test_time_and_altitude_bounds_are_validated_without_flattening_units(self):
        document = fixture("aco-all-measures.json")
        document["period"]["end"] = document["period"]["start"]
        with self.assertRaises(ContractError):
            validate_document(document)
        measure = fixture("measures/roz.json")
        part = measure["components"][0]
        part["lower_limit"] = {"value": 2000, "unit": "m", "reference": "MSL"}
        part["upper_limit"] = {"value": 1000, "unit": "ft", "reference": "MSL"}
        with self.assertRaises(ContractError):
            validate_document(measure)
        part["lower_limit"] = {"value": 0, "unit": "ft", "reference": "AGL"}
        self.assertEqual(import_document(export_document(measure)), measure)

    def test_non_finite_numbers_and_unclosed_polygons_are_rejected(self):
        document = fixture("measures/roz.json")
        document["components"][0]["geometry"]["rings"][0][-1]["latitude"] = float("nan")
        with self.assertRaises(ContractError):
            validate_document(document)
        document = fixture("measures/roz.json")
        document["components"][0]["geometry"]["rings"][0][-1]["latitude"] += 0.2
        with self.assertRaises(ContractError):
            validate_document(document)


if __name__ == "__main__":
    unittest.main()
