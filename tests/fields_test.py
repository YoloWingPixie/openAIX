import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


class FieldTests(unittest.TestCase):
    def test_attack_selection_resolves_aimpoints_and_aircraft_members(self):
        for invalid in ("aimpoint", "member", "duplicate-member"):
            with self.subTest(invalid=invalid):
                document, resources = example("ato-oir"), example("resources")
                validate_document(document, resource_document=resources)
                mission = next(item for item in document["missions"] if item["tasking"]["kind"] == "preplanned_attack")
                assignment = mission["tasking"]["assignments"][0]
                if invalid == "aimpoint":
                    assignment["target"]["aimpoints"] = ["missing"]
                else:
                    assignment["assigned_to"][0]["members"] = [3] if invalid == "member" else [1, 1]
                with self.assertRaises(ContractError):
                    validate_document(document, resource_document=resources)

    def test_ground_area_cannot_be_a_flight_pattern(self):
        for code in ("FFA", "NFA", "RFA", "EA", "AOA"):
            with self.subTest(code=code):
                document = example("measures/rfa")
                document["type"] = code
                validate_document(document)
                document["geometry"] = example("orbit")["geometry"]
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_air_corridors_require_vertical_limits(self):
        for code in ("AIRRTE", "LLTR", "MRR", "APPCOR", "SL"):
            with self.subTest(code=code):
                document = example("measures/tc")
                document["type"] = code
                validate_document(document)
                document.pop("altitude", None)
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_coordination_area_requires_a_volume(self):
        document = example("measures/aca")
        document["components"] = example("airspace-class-b")["components"]
        self.assertEqual(import_document(export_document(document)), document)
        del document["components"][0]["upper_limit"]
        with self.assertRaises(ContractError):
            validate_document(document)
        formal = example("measures/aca")
        del formal["components"]
        with self.assertRaises(ContractError):
            validate_document(formal)
        informal = dict(formal, aca_kind="informal")
        with self.assertRaises(ContractError):
            validate_document(informal)
        informal["separation"] = "altitude"
        validate_document(informal)

    def test_coordination_level_rejects_traverse_pair(self):
        document = example("measures/cl")
        document["geometry"] = example("measures/tl")["geometry"]
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_order_references_resolve_missions_packages_and_flights(self):
        for field in ("supported_missions", "package", "responsible_flight"):
            with self.subTest(field=field):
                document, resources = example("ato-oir"), example("resources")
                validate_document(document, resource_document=resources)
                mission = next(item for item in document["missions"] if item["tasking"]["kind"] == "escort")
                if field == "supported_missions":
                    mission["tasking"][field] = ["missing-mission"]
                elif field == "package":
                    mission[field] = "missing-package"
                else:
                    mission["control"] = {"kind": "self_controlled", field: "missing-flight", "instructions": "Local control"}
                with self.assertRaises(ContractError) as error:
                    validate_document(document, resource_document=resources)
                self.assertTrue(error.exception.code.startswith("unresolved"))

    def test_flight_identifiers_are_unique_across_the_order(self):
        document, resources = example("ato-oir"), example("resources")
        document["missions"][1]["flights"][0]["id"] = document["missions"][0]["flights"][0]["id"]
        with self.assertRaises(ContractError) as error:
            validate_document(document, resource_document=resources)
        self.assertEqual(error.exception.code, "duplicate identifier")

    def test_spins_has_no_untyped_publication_blocks(self):
        document = example("spins")
        document["content"] = [{"kind": "table", "caption": "Component names", "columns": [{"key": "components", "heading": "Component"}], "rows": [{"components": "North"}]}]
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_airfield_retains_its_navigation_and_approach_fields(self):
        document = example("airfield")
        document.update({"approach_instructions": ["Contact approach before entry."]})
        catalogue = example("resources-kden")
        self.assertEqual(import_document(export_document(document, resource_document=catalogue), resource_document=catalogue), document)

    def test_nested_aimpoint_keys_cannot_bypass_validation(self):
        document = example("resources")
        document["resources"]["targets"]["cobalt-array"]["aimpoints"]["Invalid key!"] = {"untyped": "value"}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_airspace_type_supports_classes_and_training_areas(self):
        for kind, classification in (("ClassB", "B"), ("ClassD", "D"), ("MTA", "G"), ("TMA", "C"), ("MOA", "E"), ("ROZ", None)):
            with self.subTest(kind=kind):
                document = example("airspace-class-b")
                document["airspace_type"] = kind
                if classification:
                    document["airspace_class_code"] = classification
                else:
                    document.pop("airspace_class_code", None)
                self.assertEqual(import_document(export_document(document)), document)

    def test_classification_cannot_contradict_airspace_type(self):
        document = example("airspace-class-b")
        document["airspace_type"] = "ClassB"
        document["airspace_class_code"] = "D"
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_airspace_type_is_required_and_local_types_are_explicit(self):
        document = example("airspace-class-b")
        del document["airspace_type"]
        with self.assertRaises(ContractError):
            validate_document(document)
        document["airspace_type"] = "ClassZ"
        with self.assertRaises(ContractError):
            validate_document(document)
        document["airspace_type"] = "Other"
        with self.assertRaises(ContractError):
            validate_document(document)
        document["local_type"] = "Research area"
        self.assertEqual(import_document(export_document(document)), document)

    def test_civil_airspace_types_are_data_with_a_first_party_source(self):
        types = json.loads((ROOT / "catalogues/airspace-types.json").read_text())
        civil = ("ATCAA", "CFA", "NSA", "TFR", "SFRA", "TRSA", "ModeCVeil", "RMZ", "TMZ")
        codes = {item["code"] for item in json.loads((ROOT / "catalogues/control-measures.json").read_text())["types"]}
        for kind in civil:
            with self.subTest(kind=kind):
                self.assertIn(kind, types["types"])
                self.assertNotIn(kind, codes)
                source = types["definition_sources"][kind]
                self.assertTrue(source["locator"])
                self.assertNotIn("verified", source)
                document = example("airspace-tfr")
                document["airspace_type"] = kind
                self.assertEqual(import_document(export_document(document)), document)
        self.assertEqual(types["definition_sources"]["RMZ"]["source"], "eu-sera-923-2012-2025")
        document = example("airspace-tfr")
        document["airspace_class_code"] = "B"
        self.assertEqual(import_document(export_document(document)), document)

    def test_desert_atcaa_sits_on_top_of_the_desert_moa(self):
        moa, atcaa = example("airspace-moa"), example("airspace-atcaa")
        self.assertEqual((moa["airspace_type"], atcaa["airspace_type"]), ("MOA", "ATCAA"))
        self.assertEqual(moa["components"][0]["geometry"], atcaa["components"][0]["geometry"])
        self.assertEqual(moa["components"][0]["upper_limit"], atcaa["components"][0]["lower_limit"])
        self.assertEqual(atcaa["components"][0]["lower_limit"], {"value": 180, "unit": "flight_level", "reference": "FL"})

    def test_standalone_agency_requires_identity(self):
        resources = example("resources")
        for name in ("c2-agency", "fac"):
            with self.subTest(name=name):
                document = example(name)
                del document["id"]
                with self.assertRaises(ContractError):
                    validate_document(document, resource_document=resources)

    def test_assignment_fields_require_their_role(self):
        for field, value in (("stack_instructions", ["hold north"]), ("entry_route", "marshal-entry")):
            with self.subTest(field=field):
                document = example("orbit-assignments")
                document["assignments"][0][field] = value
                with self.assertRaises(ContractError):
                    validate_document(document)

    def test_orbit_role_cannot_be_assigned_to_a_fire_line(self):
        document = example("aco-all-measures")
        assignment = next(item for item in document["assignments"] if item["measure"] == "oir-fscl")
        assignment["role"] = "cap"
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_assignment_interval_stays_inside_measure_availability(self):
        document = example("orbit-assignments")
        document["assignments"][0]["effective"]["start"] = "2026-10-02T05:00:00Z"
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_component_interval_stays_inside_airspace_availability(self):
        document = example("airspace-mta")
        document["components"][0]["active"] = {"start": "2026-10-02T12:00:00Z", "end": "2026-10-02T14:00:00Z"}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_mixed_times_need_an_order_period(self):
        document = example("orbit")
        document["active"] = {"start": {"offset_minutes": 30}, "end": "2026-10-02T07:00:00Z"}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_sector_inner_radius_is_smaller_than_outer(self):
        document = example("airspace-class-b")
        document["components"][0]["geometry"] = {"kind": "sector", "center": {"latitude": 37, "longitude": -115},
            "start_bearing": {"value": 90, "reference": "true"}, "end_bearing": {"value": 180, "reference": "true"},
            "inner_radius": {"value": 10, "unit": "nm"}, "outer_radius": {"value": 1000, "unit": "m"}}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_untyped_frago_patch_value_remains_opaque(self):
        document = example("frago")
        document["changes"][0]["value"] = {"components": ["opaque data for a future target schema"]}
        self.assertEqual(import_document(export_document(document)), document)

    def test_resource_catalogue_keys_must_be_identifiers(self):
        document = example("resources")
        document["resources"]["agencies"]["Invalid identifier!"] = {"arbitrary": "data"}
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_linked_resource_catalogue_is_validated_before_use(self):
        document = example("fac")
        with self.assertRaises(ContractError) as error:
            validate_document(document, resource_document={"resources": {}})
        self.assertEqual(error.exception.path, "/resources_ref")

    def test_document_boundary_rejects_non_object_json(self):
        for value in (None, [], "not an object"):
            with self.subTest(value=value), self.assertRaises(ContractError):
                import_document(json.dumps(value))
