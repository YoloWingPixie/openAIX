"""Shared constants, schema-building helpers and the common.schema.json primitive set."""
import copy
import json

from openaix import ROOT
from openaix.build.points import point_location
from openaix.build.spatial import definitions as spatial_definitions
from openaix.build.units import LENGTH_UNITS, RADIO_BANDS
from openaix.sim.bindings import EXTENSION, profile_definitions
from openaix.sim.dcs import geometry_definitions as dcs_geometry_definitions


VERSION = "0.1.0-draft.1"
DIALECT = "https://json-schema.org/draft/2020-12/schema"
BASE = "urn:openaix:schema:"
COMMON = BASE + "common:" + VERSION
RESOURCES = BASE + "resources:" + VERSION
IDENTIFIER = r"^[a-z][a-z0-9_.-]*$"
NAMESPACE = r"^[a-z][a-z0-9-]*(\.[a-z0-9-]+)+$"
LASER_CODE = r"^1[1-7][1-8][1-8]$"
RUNWAY_DESIGNATOR = r"^(0[1-9]|[12][0-9]|3[0-6])[LRCWSGU]?$"
COALITIONS = ("blue", "red", "neutral")
GEOMETRY_NAMES = ("point", "line", "polygon", "circle", "corridor", "racetrack", "track_racetrack", "sector", "polyarc", "figure_eight", "vertical", "description")


def read(path):
    return json.loads((ROOT / path).read_text())


def text(**extra):
    return {"type": "string", "minLength": 1, **extra}


def ref(name):
    return {"$ref": "#/$defs/" + name}


def external(name):
    return {"$ref": COMMON + "#/$defs/" + name}


def obj(properties, required=()):
    return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required)}


def array(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def local_references(value):
    if isinstance(value, dict):
        if value.get("$ref", "").startswith("#/$defs/"):
            yield value["$ref"].removeprefix("#/$defs/")
        for child in value.values():
            yield from local_references(child)
    elif isinstance(value, list):
        for child in value:
            yield from local_references(child)


def trim_definitions(schema):
    available = schema.get("$defs", {})
    body = {key: value for key, value in schema.items() if key != "$defs"}
    pending = list(local_references(body))
    selected = {}
    while pending:
        name = pending.pop()
        if name not in selected:
            selected[name] = available[name]
            pending.extend(local_references(available[name]))
    if selected:
        schema["$defs"] = selected
    else:
        schema.pop("$defs", None)
    return schema


def common_schema(source):
    original = source["$defs"]
    defs = {name: copy.deepcopy(original[name]) for name in ("GeoPoint", "Altitude", "AltitudeBlock", "Period", "Window", "Offset", "Metadata", "DocumentRef", "PinnedRef", "TACAN")}
    source_closure = trim_definitions({"$defs": original, "anyOf": [ref(name) for name in defs]})["$defs"]
    defs = copy.deepcopy(source_closure)
    defs["Identifier"] = text(pattern=IDENTIFIER)
    # Extensions: `sim` (simulator data by simulator, sim/bindings.py) and namespaced consumer data.
    defs["Extensions"] = {"type": "object", "properties": {EXTENSION: ref("SimData")},
                          "propertyNames": {"anyOf": [{"const": EXTENSION}, {"pattern": NAMESPACE}]}, "additionalProperties": True}
    defs["ResourceRef"] = obj({"id": ref("Identifier"), "revision": text()}, ("id", "revision"))
    defs.update(profile_definitions(COMMON))
    defs["PointLocation"] = point_location(COMMON)
    defs["Length"] = obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"enum": list(LENGTH_UNITS)}}, ("value", "unit"))
    defs["DateTime"] = {"type": "string", "format": "date-time"}
    defs["VerticalLimit"] = {"oneOf": [ref("Altitude"), obj({"surface": {"const": True}}, ("surface",)), obj({"unlimited": {"const": True}}, ("unlimited",))]}
    defs["AltitudeBlock"]["properties"] = {"lower": ref("VerticalLimit"), "upper": ref("VerticalLimit")}
    defs["Speed"] = obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"enum": ["kt", "mach", "km/h"]}}, ("value", "unit"))
    defs["Frequency"] = obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"enum": ["kHz", "MHz"]}, "modulation": {"enum": ["AM", "FM"]},
                             "band": {"enum": list(RADIO_BANDS)}}, ("value", "unit"))
    defs["Coalition"] = {"type": "string", "enum": list(COALITIONS)}
    defs["Metadata"]["properties"]["coalition"] = ref("Coalition")
    defs["LaserCode"] = {"type": "string", "pattern": LASER_CODE}
    defs["RunwayDesignator"] = {"type": "string", "pattern": RUNWAY_DESIGNATOR}
    for name, definition in defs.items():
        if name != "DateTime":
            defs[name] = date_time_references(definition)
    defs["Elevation"] = obj({"value": {"type": "number"}, "reference": {"const": "MSL"}, "unit": {"enum": ["ft", "m"]}}, ("value", "reference", "unit"))
    defs["Bearing"] = obj({"value": {"type": "number", "minimum": 0, "exclusiveMaximum": 360}, "reference": {"enum": ["true", "magnetic"]}, "declination_deg": {"type": "number", "minimum": -180, "maximum": 180}}, ("value", "reference"))
    defs["Altitude"]["allOf"] = [{"if": {"properties": {"reference": {"const": "FL"}}}, "then": {"properties": {"unit": {"const": "flight_level"}}}, "else": {"properties": {"unit": {"enum": ["ft", "m"]}}}}]
    point, points = ref("GeoPoint"), array(ref("GeoPoint"), 2)
    shapes = {
        "point": obj({"kind": {"const": "point"}, "position": point}, ("kind", "position")),
        "line": obj({"kind": {"const": "line"}, "points": points}, ("kind", "points")),
        "polygon": obj({"kind": {"const": "polygon"}, "rings": array(array(point, 4), 1)}, ("kind", "rings")),
        "circle": obj({"kind": {"const": "circle"}, "center": point, "radius": ref("Length")}, ("kind", "center", "radius")),
        "corridor": obj({"kind": {"const": "corridor"}, "points": points, "width": ref("Length"), "one_way": {"type": "boolean"}}, ("kind", "points", "width")),
        "racetrack": obj({"kind": {"const": "racetrack"}, "point": point, "radial": ref("Bearing"), "turns": {"enum": ["left", "right"]}, "leg_length": ref("Length"), "turn_radius": ref("Length")}, ("kind", "point", "radial", "turns", "leg_length")),
        "track_racetrack": obj({"kind": {"const": "track_racetrack"}, "a": point, "b": point, "width": ref("Length"), "turns": {"enum": ["left", "right"]}}, ("kind", "a", "b", "width", "turns")),
        "sector": obj({"kind": {"const": "sector"}, "center": point, "start_bearing": ref("Bearing"), "end_bearing": ref("Bearing"), "outer_radius": ref("Length"), "inner_radius": ref("Length")}, ("kind", "center", "start_bearing", "end_bearing", "outer_radius")),
        "figure_eight": obj({"kind": {"const": "figure_eight"}, "point": point, "axis": ref("Bearing"), "leg_length": ref("Length"), "turn_radius": ref("Length")}, ("kind", "point", "axis", "leg_length")),
        "vertical": {"oneOf": [
            obj({"kind": {"const": "vertical"}, "level": ref("Altitude")}, ("kind", "level")),
            obj({"kind": {"const": "vertical"},
                 "height": {"allOf": [ref("Altitude"), {"properties": {"reference": {"const": "AGL"}}}]},
                 "altitude": {"allOf": [ref("Altitude"), {"properties": {"reference": {"const": "MSL"}}}]}}, ("kind", "height", "altitude")),
        ]},
        "description": obj({"kind": {"const": "description"}, "text": text()}, ("kind", "text")),
    }
    for name, shape in shapes.items():
        defs["Geometry_" + name] = shape
    line = obj({"kind": {"const": "line"}, "start": point, "end": point}, ("kind", "start", "end"))
    arc = obj({"kind": {"const": "arc"}, "center": point, "radius": ref("Length"), "start_bearing": ref("Bearing"), "end_bearing": ref("Bearing"), "turns": {"enum": ["left", "right"]}}, ("kind", "center", "radius", "start_bearing", "end_bearing", "turns"))
    defs["Geometry_polyarc"] = obj({"kind": {"const": "polyarc"}, "segments": array({"oneOf": [line, arc]}, 2)}, ("kind", "segments"))
    defs["Geometry"] = {"oneOf": [ref("Geometry_" + name) for name in GEOMETRY_NAMES]}
    drawing_shapes = dcs_geometry_definitions(COMMON)
    defs.update(drawing_shapes)
    defs["Geometry"]["oneOf"].extend(ref(name) for name in drawing_shapes)
    defs["ControlMeasureSelection"] = obj({"kind": {"const": "control_measure"}, "id": ref("Identifier") | {"x-catalog": "control_measures"}}, ("kind", "id"))
    defs["MeasureCatalogue"] = {"type": "object", "propertyNames": ref("Identifier"), "additionalProperties": ref("ControlMeasure")}
    defs.update(spatial_definitions(COMMON))
    return {"$schema": DIALECT, "$id": COMMON, "title": "openAIX common resources", "$defs": defs}


def date_time_references(node):
    """Point inline date-time strings at the shared DateTime primitive, keeping sibling annotations."""
    if isinstance(node, list):
        return [date_time_references(item) for item in node]
    if not isinstance(node, dict):
        return node
    if node.get("type") == "string" and node.get("format") == "date-time":
        return {"$ref": "#/$defs/DateTime", **{key: value for key, value in node.items() if key not in ("type", "format")}}
    return {key: date_time_references(value) for key, value in node.items()}


def geometry_example(kind):
    p = {"latitude": 37.1, "longitude": -115.5}
    q = {"latitude": 36.9, "longitude": -115.4}
    length = {"value": 20, "unit": "nm"}
    bearing = {"value": 180, "reference": "magnetic", "declination_deg": 12.8}
    examples = {
        "point": {"kind": "point", "position": p},
        "line": {"kind": "line", "points": [p, q]},
        "polygon": {"kind": "polygon", "rings": [[p, q, {"latitude": 37.0, "longitude": -115.7}, p]]},
        "circle": {"kind": "circle", "center": p, "radius": length},
        "corridor": {"kind": "corridor", "points": [p, q], "width": {"value": 2, "unit": "nm"}, "one_way": False},
        "racetrack": {"kind": "racetrack", "point": p, "radial": bearing, "turns": "left", "leg_length": length},
        "track_racetrack": {"kind": "track_racetrack", "a": p, "b": q, "width": {"value": 2, "unit": "nm"}, "turns": "right"},
        "sector": {"kind": "sector", "center": p, "start_bearing": {"value": 90, "reference": "true"}, "end_bearing": {"value": 180, "reference": "true"}, "outer_radius": length},
        "polyarc": {"kind": "polyarc", "segments": [{"kind": "line", "start": p, "end": q}, {"kind": "arc", "center": p, "radius": length, "start_bearing": {"value": 90, "reference": "true"}, "end_bearing": {"value": 180, "reference": "true"}, "turns": "left"}]},
        "figure_eight": {"kind": "figure_eight", "point": p, "axis": bearing, "leg_length": length},
        "vertical": {"kind": "vertical", "level": {"value": 5000, "unit": "ft", "reference": "MSL"}},
        "description": {"kind": "description", "text": "Retained source geographic description; no implicit position inference."},
    }
    return copy.deepcopy(examples[kind])
