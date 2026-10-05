"""The DCS profile of simulator data: `extensions.sim.dcs` (DCSData), its object references (DCSObjectRef), the
binding policies and map conversion.

DCSData holds every DCS value of a record: `bindings` link the record to objects placed in a DCS mission; the other
keys are DCS data that is not a mission object (aircraft type name, store class identifiers, pylons, Mission Editor
settings, UnitPayloads load, ALIC code, drawing angle). Native field names follow Vox Bellica's mission reader,
including the `verticies` spelling of DCS.
"""
from copy import deepcopy

from openaix.build.units import LENGTH_UNITS


SIM = "dcs"
DATA = "DCSData"
OBJECT = "DCSObjectRef"
KINDS = ("unit", "group", "static", "scenery", "airbase", "stand", "drawing", "trigger_zone")
STYLE_FIELDS = {"color": "colorString", "fill_color": "fillColorString", "thickness": "thickness", "visible": "visible", "font_size": "fontSize"}
GEOMETRY_FIELDS = {"name", "type", "primitiveType", "polygonMode", "lineMode", "closed", "x", "y", "mapX", "mapY", "points", "verticies", "radius", "width", "height", "r1", "r2", "angle", "text", "file"}

MAP_KINDS = ("drawing", "trigger_zone")
# Object kinds that each binding policy accepts in DCS (sim/bindings.py POLICIES).
POLICIES = {
    "area": MAP_KINDS,
    "orbit": MAP_KINDS,
    "route": ("drawing",),
    "hold": ("drawing",),
    "line": ("drawing",),
    "map_point": MAP_KINDS,
    "point": ("drawing", "trigger_zone", "unit", "group", "static", "scenery", "airbase"),
    "host": ("unit", "group", "static", "drawing", "trigger_zone"),
    "fixed_target": ("unit", "group", "static", "scenery", "drawing", "trigger_zone"),
    "mobile_target": ("unit", "group", "drawing", "trigger_zone"),
    "emitter": ("unit", "group", "static", "drawing", "trigger_zone"),
    "airfield": ("airbase", "unit", "static", "drawing", "trigger_zone"),
    "navaid": ("unit", "static", "scenery", "drawing", "trigger_zone"),
    "flight": ("group",),
    "aircraft": ("unit",),
    "stand": ("stand",),
    "aimpoint_object": ("unit", "group", "static", "scenery"),
    "fixed_airfield": ("airbase", *MAP_KINDS),
    "farp": ("static", "airbase", *MAP_KINDS),
    "carrier": ("unit", "airbase", *MAP_KINDS),
}
# DCSData keys that each kind of record can have, besides `bindings` (sim/bindings.py). Every key is a fact
# about DCS or its mission objects; how an application uses them (for example the observers of a Vox Bellica JTAC)
# is in the namespace of that application.
DATA_KEYS = {
    "aimpoint": ("bindings", "objects"),
    "emitter": ("bindings", "alic_code"),
    "store": ("clsids",),
    "aircraft_type": ("type",),
    "scl": ("payload",),
    "station": ("pylon", "label", "clsid", "settings"),
    "shape": ("angle_deg", "projection"),
}


def policy_schema(policy):
    """The DCS constraints of one binding policy: object kinds and, for map policies, the drawing primitive."""
    schema = {"properties": {"kind": {"enum": list(POLICIES[policy])}}}
    if policy in {"area", "orbit", "route", "line", "hold"}:
        schema["properties"]["primitive_type"] = {"enum": ["Line"] if policy == "line" else ["Polygon", "Line"]}
        if policy == "area":
            schema["allOf"] = [{"if": {"properties": {"primitive_type": {"const": "Line"}}, "required": ["primitive_type"]},
                                "then": {"required": ["closed"], "properties": {"closed": {"const": True}}}}]
        elif policy == "line":
            schema["properties"]["closed"] = {"const": False}
    return schema


def overlay(policies, keys):
    """The DCSData of one kind of record: its allowed keys and the binding policy of each binding list."""
    properties = {}
    for key, policy in policies.items():
        properties[key] = {"items": policy_schema(policy)}
    return {"propertyNames": {"enum": list(keys)}, "properties": properties}


def style_schema():
    color = {"type": "string", "pattern": "^0x[0-9a-fA-F]{8}$"}
    return {"type": "object", "additionalProperties": False, "properties": {
        "color": color, "fill_color": deepcopy(color), "thickness": {"type": "number", "minimum": 0},
        "visible": {"type": "boolean"}, "font_size": {"type": "number", "minimum": 0},
    }}


def object_schema(common):
    """DCSObjectRef: one object placed in a DCS mission (unit, group, static, scenery, airbase, stand, drawing or
    trigger zone), with the typed DCS attributes of drawings and zones."""
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "kind": {"enum": list(KINDS)},
            "name": {"type": "string", "minLength": 1},
            "object_id": {"type": "integer"},
            "mission_id": {"type": "string"},
            "layer": {"type": "string"},
            "primitive_type": {"enum": ["Polygon", "Line", "TextBox", "Icon"]},
            "polygon_mode": {"enum": ["circle", "oval", "rect", "free", "arrow"]},
            "line_mode": {"enum": ["segment", "segments", "free"]},
            "closed": {"type": "boolean"},
            "zone_type": {"enum": ["circle", "quad"]},
            "unit_type": {"type": "string"},
            "group_category": {"enum": ["airplane", "helicopter", "vehicle", "ship", "train"]},
            "text": {"type": "string"}, "icon": {"type": "string"},
            "angle_deg": {"type": "number"},
            "style": style_schema(),
            "native_fields": {"type": "object", "propertyNames": {"not": {"enum": sorted(GEOMETRY_FIELDS | set(STYLE_FIELDS.values()))}}},
        },
        "required": ["kind"],
        "anyOf": [{"required": ["name"]}, {"required": ["object_id"]}],
        "allOf": [
            {"if": {"anyOf": [{"required": [key]} for key in ("layer", "primitive_type", "polygon_mode", "line_mode", "closed", "text", "icon", "style", "angle_deg")]},
             "then": {"properties": {"kind": {"const": "drawing"}}}},
            {"if": {"required": ["zone_type"]}, "then": {"properties": {"kind": {"const": "trigger_zone"}}}},
            {"if": {"required": ["polygon_mode"]}, "then": {"required": ["primitive_type"], "properties": {"primitive_type": {"const": "Polygon"}}}},
            {"if": {"required": ["line_mode"]}, "then": {"required": ["primitive_type"], "properties": {"primitive_type": {"const": "Line"}}}},
            {"if": {"required": ["closed"]}, "then": {"required": ["primitive_type"], "properties": {"primitive_type": {"const": "Line"}}}},
            {"if": {"required": ["text"]}, "then": {"required": ["primitive_type"], "properties": {"primitive_type": {"const": "TextBox"}}}},
            {"if": {"required": ["icon"]}, "then": {"required": ["primitive_type"], "properties": {"primitive_type": {"const": "Icon"}}}},
            {"if": {"required": ["angle_deg"]}, "then": {
                "required": ["primitive_type"], "properties": {"primitive_type": {"enum": ["Polygon", "TextBox", "Icon"]}},
                "allOf": [{"if": {"properties": {"primitive_type": {"const": "Polygon"}}},
                           "then": {"required": ["polygon_mode"], "properties": {"polygon_mode": {"const": "circle"}}}}]}},
            {"if": {"properties": {"style": {"required": ["font_size"]}}, "required": ["style"]},
             "then": {"required": ["primitive_type"], "properties": {"primitive_type": {"const": "TextBox"}}}},
            {"if": {"required": ["group_category"]}, "then": {"properties": {"kind": {"const": "group"}}}},
            {"if": {"required": ["unit_type"]}, "then": {"properties": {"kind": {"enum": ["unit", "static"]}}}},
        ],
    }


def data_schema(common):
    """DCSData: `extensions.sim.dcs` of a record."""
    reference = {"$ref": common + "#/$defs/" + OBJECT}
    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "bindings": {"type": "array", "items": deepcopy(reference)},
            "objects": {"type": "array", "items": deepcopy(reference)},
            "type": {"type": "string", "minLength": 1},
            "clsids": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1, "uniqueItems": True},
            "payload": {"type": "object", "additionalProperties": False, "required": ["name"], "properties": {
                "name": {"type": "string", "minLength": 1}, "unit_type": {"type": "string", "minLength": 1},
                "task_ids": {"type": "array", "items": {"type": "integer", "minimum": 0}, "minItems": 1, "uniqueItems": True}}},
            "pylon": {"type": "integer", "minimum": 1},
            "label": {"type": "string", "minLength": 1},
            "clsid": {"type": "string", "minLength": 1},
            "settings": {"type": "object"},
            "alic_code": {"type": "integer", "minimum": 1},
            "angle_deg": {"type": "number"},
            "projection": {"type": "string", "minLength": 1},
        },
        "dependentRequired": {"label": ["pylon"], "clsid": ["pylon"], "settings": ["pylon"]},
    }


def geometry_definitions(common):
    """Rectangle and ellipse geometries: a centre and dimensions in metres; DCS keeps its drawing angle and theatre
    projection in `extensions.sim.dcs`."""
    dimensions = {"rectangle": ("width_m", "height_m"), "ellipse": ("north_radius_m", "east_radius_m")}
    return {
        "Geometry_" + kind: {
            "type": "object", "additionalProperties": False,
            "properties": {"kind": {"const": kind}, "center": {"$ref": common + "#/$defs/GeoPoint"},
                           **{name: {"type": "number", "exclusiveMinimum": 0} for name in fields},
                           "extensions": {"$ref": common + "#/$defs/Extensions"}},
            "required": ["kind", "center", *fields],
        } for kind, fields in dimensions.items()
    }


def extension(bindings=None, **data):
    """`extensions` value with DCS data, for authored records: {"sim": {"dcs": {"bindings": [...], ...}}}."""
    return {"sim": {SIM: {**({"bindings": list(bindings)} if bindings else {}), **data}}}


def shape_data(geometry):
    return geometry.get("extensions", {}).get("sim", {}).get(SIM, {})


# ---- Native map objects: drawings and trigger zones ---------------------------------------------------
def apply_metadata(binding, native):
    extras = binding.get("native_fields", {})
    forbidden = GEOMETRY_FIELDS | set(STYLE_FIELDS.values())
    if forbidden & extras.keys():
        raise ValueError("native_fields cannot override typed geometry, identity or display attributes")
    return {**deepcopy(extras), **{native_key: binding["style"][key] for key, native_key in STYLE_FIELDS.items() if key in binding.get("style", {})}, **native}


def validate_binding_geometry(binding, geometry):
    from jsonschema import Draft202012Validator
    from openaix.check.validate import schemas, semantic

    records, registry = schemas()
    common = records["common"]
    validator = Draft202012Validator(common, registry=registry)
    validator.evolve(schema={"$ref": common["$id"] + "#/$defs/" + OBJECT}).validate(binding)
    schema = geometry_definitions(common["$id"]).get("Geometry_" + geometry.get("kind", ""), {"$ref": common["$id"] + "#/$defs/Geometry"})
    validator.evolve(schema=schema).validate(geometry)
    semantic(geometry, {}, None)


def export_map_object(binding, geometry, project, *, projection=None):
    validate_binding_geometry(binding, geometry)
    native = map_object(binding, geometry, project, projection=projection)
    if "angle_deg" in binding:
        if geometry["kind"] not in {"point", "circle"}:
            raise ValueError("angle_deg applies only to point and circle drawings")
        native["angle"] = binding["angle_deg"]
    return {"binding": deepcopy(binding), "object": apply_metadata(binding, native)}


def map_object(binding, geometry, project, *, projection=None):
    def point(position):
        north, east = project(position["latitude"], position["longitude"])
        return {"x": north, "y": east}

    name = binding.get("name", str(binding.get("object_id", "")))
    if geometry["kind"] == "point" and binding["kind"] == "drawing":
        primitive = binding.get("primitive_type")
        if primitive not in {"TextBox", "Icon"}:
            raise ValueError("point geometry requires a text or icon drawing")
        key = "text" if primitive == "TextBox" else "icon"
        if key not in binding:
            raise ValueError("point drawing requires " + key)
        center = point(geometry["position"])
        return {"name": name, "primitiveType": primitive, "mapX": center["x"], "mapY": center["y"], "text" if key == "text" else "file": binding[key]}
    if geometry["kind"] in {"rectangle", "ellipse"}:
        if projection != shape_data(geometry).get("projection"):
            raise ValueError("shape projection must match the supplied theatre projection")
        mode = "rect" if geometry["kind"] == "rectangle" else "oval"
        if binding["kind"] != "drawing" or binding.get("primitive_type", "Polygon") != "Polygon" or binding.get("polygon_mode", mode) != mode:
            raise ValueError("exact rectangle/ellipse needs its matching drawing mode")
        center = point(geometry["center"])
        dimensions = {"width": geometry["width_m"], "height": geometry["height_m"]} if mode == "rect" else {"r1": geometry["north_radius_m"], "r2": geometry["east_radius_m"]}
        return {"name": name, "primitiveType": "Polygon", "polygonMode": mode, "mapX": center["x"], "mapY": center["y"], "angle": shape_data(geometry).get("angle_deg", 0), **dimensions}
    if geometry["kind"] == "circle":
        center = point(geometry["center"])
        radius = geometry["radius"]["value"] * LENGTH_UNITS[geometry["radius"]["unit"]]
        if binding["kind"] == "trigger_zone":
            if binding.get("zone_type", "circle") != "circle":
                raise ValueError("circle geometry requires a circle trigger zone")
            return {"name": name, "type": 0, **center, "radius": radius}
        if binding["kind"] == "drawing" and binding.get("primitive_type", "Polygon") == "Polygon" and binding.get("polygon_mode", "circle") == "circle":
            return {"name": name, "primitiveType": "Polygon", "polygonMode": "circle", "mapX": center["x"], "mapY": center["y"], "radius": radius}
    if geometry["kind"] in {"polygon", "line"}:
        if geometry["kind"] == "polygon":
            if len(geometry["rings"]) != 1:
                raise ValueError("native map export cannot silently discard polygon holes")
            positions = geometry["rings"][0][:-1]
        else:
            positions = geometry["points"]
        points = [point(value) for value in positions]
        if binding["kind"] == "trigger_zone":
            if geometry["kind"] != "polygon" or len(points) != 4 or binding.get("zone_type", "quad") != "quad":
                raise ValueError("quad trigger zone requires a four-corner polygon")
            return {"name": name, "type": 2, "x": sum(p["x"] for p in points) / 4, "y": sum(p["y"] for p in points) / 4, "verticies": points}
        if binding["kind"] == "drawing":
            primitive = "Polygon" if geometry["kind"] == "polygon" else "Line"
            if geometry["kind"] == "polygon" and binding.get("primitive_type") == "Line" and binding.get("closed"):
                primitive = "Line"
            mode_field = "polygon_mode" if primitive == "Polygon" else "line_mode"
            default_mode = "free" if primitive == "Polygon" else "segments"
            if binding.get("primitive_type", primitive) != primitive or binding.get(mode_field, default_mode) not in ({"free", "arrow"} if primitive == "Polygon" else {"segment", "segments", "free"}):
                raise ValueError("drawing mode requires an explicit compatible geometry conversion")
            if primitive == "Line" and binding.get("line_mode") == "segment" and len(points) != 2:
                raise ValueError("a segment drawing requires exactly two points")
            if geometry["kind"] == "line" and binding.get("closed"):
                raise ValueError("closed drawing requires polygon geometry")
            origin = points[0]
            return {"name": name, "primitiveType": primitive, "polygonMode" if primitive == "Polygon" else "lineMode": binding.get(mode_field, default_mode),
                    "mapX": origin["x"], "mapY": origin["y"], "closed": primitive == "Polygon" or binding.get("closed", False),
                    "points": [{"x": p["x"] - origin["x"], "y": p["y"] - origin["y"]} for p in points]}
    raise ValueError("this geometry/binding needs a renderer-specific conversion")


def import_map_object(native, kind, unproject, *, layer=None, projection=None):
    def point(north, east):
        latitude, longitude = unproject(north, east)
        return {"latitude": latitude, "longitude": longitude}

    data = deepcopy(native)
    name = data.pop("name", None)
    if not isinstance(name, str) or not name:
        raise ValueError("native map object needs a nonempty name")
    binding = {"kind": kind, "name": name}
    if kind == "drawing":
        if layer is not None:
            binding["layer"] = layer
        primitive = data.pop("primitiveType")
        binding["primitive_type"] = primitive
        north, east = data.pop("mapX"), data.pop("mapY")
        center = point(north, east)
        if primitive in {"TextBox", "Icon"}:
            binding["text" if primitive == "TextBox" else "icon"] = data.pop("text" if primitive == "TextBox" else "file")
            geometry = {"kind": "point", "position": center}
            if "angle" in data:
                binding["angle_deg"] = data.pop("angle")
        elif primitive == "Polygon" and data.get("polygonMode") in {"circle", "rect", "oval"}:
            mode = data.pop("polygonMode")
            binding["polygon_mode"] = mode
            if mode == "circle":
                geometry = {"kind": "circle", "center": center, "radius": {"value": data.pop("radius"), "unit": "m"}}
                if "angle" in data:
                    binding["angle_deg"] = data.pop("angle")
            else:
                if not projection:
                    raise ValueError("rectangle and ellipse require the theatre projection identifier")
                geometry = {"kind": "rectangle" if mode == "rect" else "ellipse", "center": center,
                            "extensions": {"sim": {SIM: {"angle_deg": data.pop("angle", 0), "projection": projection}}}}
                mapping = {"width_m": "width", "height_m": "height"} if mode == "rect" else {"north_radius_m": "r1", "east_radius_m": "r2"}
                geometry.update({key: data.pop(source) for key, source in mapping.items()})
        elif primitive in {"Polygon", "Line"}:
            binding["polygon_mode" if primitive == "Polygon" else "line_mode"] = data.pop("polygonMode" if primitive == "Polygon" else "lineMode")
            closed = data.pop("closed", primitive == "Polygon")
            if primitive == "Line":
                binding["closed"] = closed
            positions = []
            for item in data.pop("points"):
                if set(item) != {"x", "y"}:
                    raise ValueError("point metadata requires a consumer-specific conversion")
                positions.append(point(north + item["x"], east + item["y"]))
            if primitive == "Polygon" or closed:
                if positions and positions[0] != positions[-1]:
                    positions.append(deepcopy(positions[0]))
                geometry = {"kind": "polygon", "rings": [positions]}
            else:
                geometry = {"kind": "line", "points": positions}
        else:
            raise ValueError("unsupported drawing primitive")
    elif kind == "trigger_zone":
        zone_type = data.pop("type")
        north, east = data.pop("x"), data.pop("y")
        if zone_type == 0:
            binding["zone_type"] = "circle"
            geometry = {"kind": "circle", "center": point(north, east), "radius": {"value": data.pop("radius"), "unit": "m"}}
        elif zone_type == 2:
            binding["zone_type"] = "quad"
            vertices = data.pop("verticies")
            if len(vertices) != 4 or any(set(p) != {"x", "y"} for p in vertices):
                raise ValueError("quad zone requires four plain coordinate vertices")
            positions = [point(p["x"], p["y"]) for p in vertices]
            geometry = {"kind": "polygon", "rings": [[*positions, deepcopy(positions[0])]]}
        else:
            raise ValueError("unsupported trigger zone type")
    else:
        raise ValueError("map conversion supports drawings and trigger zones")
    style = {key: data.pop(source) for key, source in STYLE_FIELDS.items() if source in data}
    if style:
        binding["style"] = style
    if data:
        if GEOMETRY_FIELDS & data.keys():
            raise ValueError("unconsumed native geometry attributes require explicit conversion")
        binding["native_fields"] = data
    validate_binding_geometry(binding, geometry)
    return {"binding": binding, "geometry": geometry}
