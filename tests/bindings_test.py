import copy
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.sim.dcs import export_map_object
from openaix.check.validate import ContractError, schemas, export_document, import_document, validate_document


def project(latitude, longitude):
    return (latitude - 36) * 1000, (longitude + 115) * 2000


def dcs(bindings=None, **data):
    return {"sim": {"dcs": {**({"bindings": bindings} if bindings is not None else {}), **data}}}


def extensions(schema):
    """Validator of the `extensions` field of a record schema: its simulator data and binding policies."""
    _, registry = schemas()
    return Draft202012Validator(schema["properties"]["extensions"], registry=registry)


class BindingTests(unittest.TestCase):
    def test_bindings_enforce_object_kind_and_drawing_subtype(self):
        records, registry = schemas()
        validator = Draft202012Validator({"$ref": records["common"]["$id"] + "#/$defs/DCSObjectRef"}, registry=registry)
        cases = [
            ({"kind": "unit", "name": "Observer", "unit_type": "Hummer"}, True),
            ({"kind": "group", "object_id": 23, "group_category": "vehicle"}, True),
            ({"kind": "drawing", "name": "Area", "primitive_type": "Polygon", "polygon_mode": "free", "layer": "Blue"}, True),
            ({"kind": "trigger_zone", "name": "Area", "zone_type": "quad"}, True),
            ({"kind": "group", "name": "Bad", "zone_type": "circle"}, False),
            ({"kind": "unit", "object_id": None}, False),
            ({"kind": "drawing", "name": "Bad", "primitive_type": "Line", "polygon_mode": "free"}, False),
            ({"kind": "drawing", "name": "Bad", "primitive_type": "Polygon", "text": "Label"}, False),
            ({"kind": "drawing", "name": "Bad", "primitive_type": "Icon", "closed": True}, False),
        ]
        for binding, expected in cases:
            with self.subTest(binding=binding):
                self.assertEqual(validator.is_valid(binding), expected)

    def test_position_and_bindings_survive_entity_round_trip(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        for field in ("resources_ref", "channels", "initial_points", "egress_points"):
            document.pop(field, None)
        document["position"] = {"latitude": 36.1, "longitude": -115.2}
        document["extensions"] = dcs([{"kind": "unit", "name": "Axeman", "object_id": 42},
                                      {"kind": "group", "name": "Observation team"}])
        self.assertEqual(import_document(export_document(document)), document)

    def test_circle_export_preserves_binding_and_projects_horizontal_axes(self):
        geometry = {"kind": "circle", "center": {"latitude": 37, "longitude": -114}, "radius": {"value": 2, "unit": "nm"}}
        for binding in ({"kind": "trigger_zone", "name": "ROZ", "zone_type": "circle", "object_id": 42},
                        {"kind": "drawing", "name": "ROZ", "primitive_type": "Polygon", "polygon_mode": "circle", "layer": "Blue"}):
            with self.subTest(binding=binding):
                result = export_map_object(binding, geometry, project)
                self.assertEqual(result["binding"], binding)
                native = result["object"]
                self.assertEqual(native["radius"], 3704)
                self.assertEqual(native.get("x", native.get("mapX")), 1000)
                self.assertEqual(native.get("y", native.get("mapY")), 2000)

    def test_quad_and_drawing_reconstruct_the_same_geographic_corners(self):
        ring = [{"latitude": lat, "longitude": lon} for lat, lon in [(36, -115), (37, -115), (37, -114), (36, -114), (36, -115)]]
        geometry = {"kind": "polygon", "rings": [ring]}
        quad = export_map_object({"kind": "trigger_zone", "name": "Area", "zone_type": "quad"}, geometry, project)["object"]
        drawing = export_map_object({"kind": "drawing", "name": "Area", "primitive_type": "Polygon", "polygon_mode": "free"}, geometry, project)["object"]
        self.assertEqual(quad["type"], 2)
        reconstructed = [{"x": drawing["mapX"] + p["x"], "y": drawing["mapY"] + p["y"]} for p in drawing["points"]]
        self.assertEqual(reconstructed, quad["verticies"])
        self.assertEqual((quad["x"], quad["y"]), (500, 1000))
        closed = export_map_object({"kind": "drawing", "name": "Boundary", "primitive_type": "Line", "line_mode": "segments", "closed": True}, geometry, project)["object"]
        self.assertEqual(closed["primitiveType"], "Line")
        self.assertTrue(closed["closed"])
        self.assertEqual(closed["points"], drawing["points"])
        geometry["rings"].append(copy.deepcopy(ring))
        with self.assertRaisesRegex(ValueError, "holes"):
            export_map_object({"kind": "drawing", "name": "Area"}, geometry, project)

    def test_line_export_retains_every_point_and_rejects_lossy_segment(self):
        geometry = {"kind": "line", "points": [{"latitude": lat, "longitude": -115} for lat in (36, 37, 38)]}
        binding = {"kind": "drawing", "name": "Route", "primitive_type": "Line", "line_mode": "segments"}
        native = export_map_object(binding, geometry, project)["object"]
        self.assertEqual(native["points"], [{"x": x, "y": 0} for x in (0, 1000, 2000)])
        binding["line_mode"] = "segment"
        with self.assertRaisesRegex(ValueError, "exactly two"):
            export_map_object(binding, geometry, project)
        binding["line_mode"] = "segments"
        binding["closed"] = True
        with self.assertRaisesRegex(ValueError, "polygon"):
            export_map_object(binding, geometry, project)

    def test_native_rectangles_ellipses_labels_and_icons_round_trip_without_sampling(self):
        from openaix.sim.dcs import import_map_object

        def unproject(north, east):
            return 36 + north / 1000, -115 + east / 2000

        base = {"name": "Review", "mapX": 1000, "mapY": 2000, "colorString": "0xff804080", "visible": False, "editorVersion": 7}
        shapes = [
            {"primitiveType": "Polygon", "polygonMode": "rect", "width": 2000, "height": 1000, "angle": 90},
            {"primitiveType": "Polygon", "polygonMode": "oval", "r1": 1000, "r2": 500, "angle": -34},
            {"primitiveType": "TextBox", "text": "UNLTD-12000", "fontSize": 12, "angle": -34},
            {"primitiveType": "Icon", "file": "P91000009.png", "angle": 0},
        ]
        for shape in shapes:
            native = base | shape
            with self.subTest(shape=shape):
                decoded = import_map_object(native, "drawing", unproject, layer="Blue", projection="test-theatre")
                self.assertEqual(decoded["binding"]["style"]["color"], "0xff804080")
                self.assertEqual(decoded["binding"]["native_fields"], {"editorVersion": 7})
                self.assertEqual(decoded["binding"]["layer"], "Blue")
                center = decoded["geometry"].get("center", decoded["geometry"].get("position"))
                self.assertEqual(center, {"latitude": 37, "longitude": -114})
                self.assertEqual(export_map_object(decoded["binding"], decoded["geometry"], project, projection="test-theatre")["object"], native)
                if shape.get("polygonMode") in {"rect", "oval"}:
                    with self.assertRaisesRegex(ValueError, "projection"):
                        export_map_object(decoded["binding"], decoded["geometry"], project, projection="wrong-theatre")

    def test_native_metadata_cannot_override_geometry_or_typed_style(self):
        geometry = {"kind": "circle", "center": {"latitude": 37, "longitude": -114}, "radius": {"value": 2, "unit": "nm"}}
        for key in ("mapX", "radius", "colorString", "name"):
            with self.subTest(key=key), self.assertRaises(ValidationError):
                export_map_object({"kind": "drawing", "name": "Area", "native_fields": {key: 99}}, geometry, project)

    def test_native_import_rejects_unknown_shape_and_unhandled_vertex_metadata(self):
        from openaix.sim.dcs import import_map_object
        native = {"name": "Bad", "primitiveType": "Line", "lineMode": "segments", "mapX": 0, "mapY": 0,
                  "points": [{"x": 0, "y": 0, "unknown": True}, {"x": 100, "y": 200}]}
        with self.assertRaisesRegex(ValueError, "point metadata"):
            import_map_object(native, "drawing", lambda n, e: (36, -115))
        with self.assertRaisesRegex(ValueError, "unsupported trigger"):
            import_map_object({"name": "Bad", "type": 9, "x": 0, "y": 0}, "trigger_zone", lambda n, e: (36, -115))

    def test_native_circle_zone_and_paths_preserve_geographic_coverage(self):
        from openaix.sim.dcs import import_map_object
        unproject = lambda n, e: (36 + n / 1000, -115 + e / 2000)
        native = {"name": "Sector", "type": 0, "x": 1000, "y": 2000, "radius": 3704, "zoneId": 7}
        decoded = import_map_object(native, "trigger_zone", unproject)
        self.assertEqual(export_map_object(decoded["binding"], decoded["geometry"], project)["object"], native)
        line = {"name": "Path", "primitiveType": "Line", "lineMode": "segments", "closed": False,
                "mapX": 1000, "mapY": 2000, "points": [{"x": 0, "y": 0}, {"x": 1000, "y": 2000}]}
        decoded = import_map_object(line, "drawing", unproject)
        self.assertEqual(export_map_object(decoded["binding"], decoded["geometry"], project)["object"], line)

    def test_exact_shape_validation_rejects_missing_projection_and_nonpositive_dimensions(self):
        from openaix.sim.dcs import validate_binding_geometry
        binding = {"kind": "drawing", "name": "Rectangle", "primitive_type": "Polygon", "polygon_mode": "rect"}
        shape = {"kind": "rectangle", "center": {"latitude": 37, "longitude": -114}, "width_m": 2000, "height_m": 1000,
                 "extensions": dcs(projection="Syria", angle_deg=90)}
        for field, value in (("width_m", 0), ("height_m", -1), ("extensions", dcs(projection="Syria", stations=[]))):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_binding_geometry(binding, shape | {field: value})
        with self.assertRaises(ValidationError):
            validate_binding_geometry(binding, shape | {"extensions": dcs(projection="")})

    def test_entity_bindings_distinguish_representation_from_assigned_aircraft(self):
        from openaix.sim.bindings import attach_bindings
        records, registry = schemas()
        common = records["common"]["$id"]
        artifacts = {}
        for path in (ROOT / "schemas").rglob("*.schema.json"):
            artifacts[path.relative_to(ROOT).as_posix()] = json.loads(path.read_text())
        attach_bindings(artifacts, common)
        cases = [
            ("measures/orbit", {"kind": "unit", "name": "CAP flight"}, False),
            ("measures/orbit", {"kind": "group", "name": "CAP flight"}, False),
            ("measures/orbit", {"kind": "drawing", "name": "CAP Alpha", "primitive_type": "Line", "line_mode": "segments"}, True),
            ("measures/orbit", {"kind": "trigger_zone", "name": "CAP anchor", "zone_type": "circle"}, True),
            ("measures/airspace", {"kind": "unit", "name": "Aircraft"}, False),
            ("measures/airspace", {"kind": "drawing", "name": "Sector", "primitive_type": "Line", "closed": False}, False),
            ("measures/airspace", {"kind": "drawing", "name": "Sector", "primitive_type": "Line", "closed": True}, True),
            ("measures/fire-support-line", {"kind": "drawing", "name": "Boundary", "primitive_type": "Polygon"}, False),
            ("measures/fire-support-line", {"kind": "drawing", "name": "Boundary", "primitive_type": "Line"}, True),
            ("measures/volume", {"kind": "unit", "name": "Aircraft"}, False),
            ("measures/volume", {"kind": "trigger_zone", "name": "Boundary", "zone_type": "circle"}, True),
            ("measures/point", {"kind": "unit", "name": "Mobile reference"}, True),
            ("fac", {"kind": "unit", "name": "Observer"}, True),
            ("c2-agency", {"kind": "group", "name": "Command post"}, True),
            ("airfield", {"kind": "airbase", "name": "Muwaffaq Salti"}, True),
            ("airfield", {"kind": "group", "name": "Parked aircraft"}, False),
            ("procedure", {"kind": "drawing", "name": "Procedure", "primitive_type": "Line"}, True),
            ("procedure", {"kind": "group", "name": "Aircraft"}, False),
        ]
        for entity, binding, expected in cases:
            with self.subTest(entity=entity, binding=binding):
                self.assertEqual(extensions(artifacts["schemas/" + entity + ".schema.json"]).is_valid(dcs([binding])), expected)
        resources = artifacts["schemas/resources.schema.json"]["$defs"]
        for entity, kind, expected in (("FixedTarget", "scenery", True), ("MobileTarget", "static", False),
                                       ("MobileTarget", "group", True), ("AreaTarget", "unit", False),
                                       ("AreaTarget", "trigger_zone", True), ("Aimpoint", "static", True)):
            with self.subTest(entity=entity, kind=kind):
                self.assertEqual(extensions(resources[entity]).is_valid(dcs([{"kind": kind, "name": "Target"}])), expected)

    def test_airfield_aimpoint_and_drawing_angles_follow_their_meanings(self):
        records, registry = schemas()
        common = records["common"]["$id"]
        airfield = extensions(records["airfield"])
        self.assertFalse(airfield.is_valid(dcs([{"kind": "group", "name": "Parked aircraft"}])))
        self.assertTrue(airfield.is_valid(dcs([{"kind": "airbase", "name": "Muwaffaq Salti"}])))
        # A fixed airfield is a native airbase; only a carrier binds to its ship unit and a FARP to a static object.
        resources = json.loads((ROOT / "examples/resources.json").read_text())
        ojms = copy.deepcopy(resources["resources"]["places"]["ojms"])
        ojms["extensions"]["sim"]["dcs"]["bindings"].append({"kind": "unit", "name": "Parked aircraft"})
        with self.assertRaises(ContractError):
            validate_document(ojms, "airfield", resources)
        carrier = json.loads((ROOT / "examples/carrier.json").read_text())
        validate_document(carrier)
        carrier["extensions"]["sim"]["dcs"]["bindings"][0]["kind"] = "stand"
        with self.assertRaises(ContractError):
            validate_document(carrier)
        aimpoint = extensions(records["resources"]["$defs"]["Aimpoint"])
        self.assertFalse(aimpoint.is_valid(dcs(objects=[{"kind": "drawing", "name": "Label"}])))
        self.assertTrue(aimpoint.is_valid(dcs(objects=[{"kind": "static", "name": "Warehouse"}])))
        drawing = {"kind": "drawing", "name": "Drawing", "angle_deg": 90}
        validator = Draft202012Validator({"$ref": common + "#/$defs/DCSObjectRef"}, registry=registry)
        self.assertFalse(validator.is_valid(drawing | {"primitive_type": "Line"}))
        self.assertFalse(validator.is_valid(drawing | {"primitive_type": "Polygon", "polygon_mode": "rect"}))
        self.assertTrue(validator.is_valid(drawing | {"primitive_type": "TextBox", "text": "Label"}))

    def test_vertical_constraints_have_no_map_binding_and_path_points_are_not_mobile_sources(self):
        records, registry = schemas()
        for name in ("cl", "tl"):
            schema = records["measures/" + name]
            with self.subTest(name=name):
                document = json.loads((ROOT / "examples/measures" / (name + ".json")).read_text())
                document["extensions"] = dcs([{"kind": "trigger_zone", "name": "Unlocated level"}])
                self.assertFalse(Draft202012Validator(schema, registry=registry).is_valid(document))
        validator = extensions(records["path-point"])
        self.assertFalse(validator.is_valid(dcs([{"kind": "unit", "name": "Aircraft"}])))
        self.assertFalse(validator.is_valid(dcs([{"kind": "group", "name": "Flight"}])))
        self.assertTrue(validator.is_valid(dcs([{"kind": "drawing", "name": "Threshold", "primitive_type": "TextBox", "text": "Threshold"}])))

    def test_core_records_have_no_simulator_fields(self):
        records, _ = schemas()

        def fields(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    if key == "properties" and isinstance(value, dict):
                        yield from value
                    if key not in ("extensions", "SimData", "DCSData", "DCSObjectRef", "VoxJTACSettings"):
                        yield from fields(value)
            elif isinstance(node, list):
                for item in node:
                    yield from fields(item)

        for name, schema in records.items():
            with self.subTest(schema=name):
                names = set(fields(schema))
                self.assertFalse({"sim_bindings", "sim_objects", "source_unit", "observer_group", "observers"} & names)
                self.assertFalse([field for field in names if field.startswith("dcs_")])


class SimulatorProfileTests(unittest.TestCase):
    def test_dcs_data_has_only_facts_about_dcs_and_its_mission_objects(self):
        """Every DCSData key is a fact about DCS or a mission object; application settings are in their own namespace."""
        records, _ = schemas()
        self.assertEqual(sorted(records["common"]["$defs"]["DCSData"]["properties"]),
                         ["alic_code", "angle_deg", "bindings", "clsid", "clsids", "label", "objects", "payload",
                          "projection", "pylon", "settings", "type"])
        self.assertEqual(sorted(records["common"]["$defs"]["DCSObjectRef"]["properties"]),
                         ["angle_deg", "closed", "group_category", "icon", "kind", "layer", "line_mode", "mission_id", "name",
                          "native_fields", "object_id", "polygon_mode", "primitive_type", "style", "text", "unit_type", "zone_type"])
        for path in sorted((ROOT / "examples").rglob("*.json")):
            text = json.dumps(json.loads(path.read_text()).get("extensions", {}).get("sim", {}))
            with self.subTest(example=path.name):
                self.assertNotIn("vox", text.lower())

    def test_unknown_simulator_data_is_an_object_beside_the_dcs_data(self):
        roz = json.loads((ROOT / "examples/sim-bound-roz.json").read_text())
        roz["extensions"]["sim"]["falcon-bms"] = {"objective": "obj-217", "campaign": "Syria", "owner": 2}
        validate_document(roz)
        records, registry = schemas()
        validator = Draft202012Validator({"$ref": records["common"]["$id"] + "#/$defs/SimData"}, registry=registry)
        self.assertTrue(validator.is_valid({"falcon-bms": {"bindings": [{"objective": "obj-217"}]}}))
        self.assertFalse(validator.is_valid({"falcon-bms": "objective 217"}))
        self.assertFalse(validator.is_valid({"Falcon BMS": {}}))
        self.assertFalse(validator.is_valid({"dcs": {"bindings": [{"kind": "objective", "name": "Not a DCS kind"}]}}))
        self.assertFalse(validator.is_valid({"dcs": {"bindings": [{"kind": "unit", "object_id": "42"}]}}))
        self.assertFalse(validator.is_valid({"dcs": {"bindings": [{"sim": "dcs", "kind": "unit", "name": "Old binding"}]}}))
        self.assertFalse(validator.is_valid({"dcs": {"unknown": 1}}))

    def test_binding_policies_and_data_keys_apply_per_record(self):
        records, _ = schemas()
        orbit = extensions(records["measures/orbit"])
        self.assertFalse(orbit.is_valid(dcs([{"kind": "unit", "name": "CAP flight"}])))
        self.assertTrue(orbit.is_valid({"sim": {"other-sim": {"bindings": [{"kind": "unit", "name": "CAP flight"}]}}}))
        self.assertFalse(orbit.is_valid(dcs(clsids=["{AN_AAQ_33}"])))
        stand = extensions(records["airfield"]["$defs"]["Stand"])
        self.assertTrue(stand.is_valid(dcs([{"kind": "stand", "name": "G03"}])))
        self.assertFalse(stand.is_valid(dcs([{"kind": "airbase", "name": "Muwaffaq Salti"}])))
        store = extensions(records["resources"]["$defs"]["Store"])
        self.assertTrue(store.is_valid(dcs(clsids=["{AN_AAQ_33}"])))
        self.assertFalse(store.is_valid(dcs([{"kind": "unit", "name": "Pod"}])))
