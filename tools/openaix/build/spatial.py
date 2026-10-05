"""Shared spatial definitions (Activation, AirspaceComponent) and the Orbit and Airspace measure contracts.

Descriptions come from describe/resolve.py; see describe_artifacts for the (context, property) tables.
"""
from copy import deepcopy

from openaix.build.airspace_types import schema as airspace_type_schema
from openaix.build.availability import definitions as availability_definitions
from openaix.describe.resolve import schema_description


EXAMPLE_WINDOW = {"start": "2026-10-02T06:00:00Z", "end": "2026-10-02T18:00:00Z"}
AREA_GEOMETRIES = ("polygon", "circle", "sector", "polyarc", "corridor")


def definitions(common):
    def ref(name):
        return {"$ref": common + "#/$defs/" + name}

    return {
        **availability_definitions(common),
        "Activation": {
            "oneOf": [ref("Window"), ref("ScheduledWindow"), {"type": "object", "additionalProperties": False,
                                      "properties": {"continuous": {"const": True}},
                                      "required": ["continuous"]}],
        },
        "AirspaceComponent": {
            "type": "object", "additionalProperties": False,
            "properties": {
                "id": ref("Identifier"),
                "name": {"type": "string", "minLength": 1},
                "operation": {"enum": ["add", "subtract", "intersect"]},
                "geometry": {"oneOf": [ref("Geometry_" + kind) for kind in AREA_GEOMETRIES]},
                "lower_limit": ref("VerticalLimit"),
                "upper_limit": ref("VerticalLimit"),
                "minimum_limit": ref("Altitude"),
                "maximum_limit": ref("Altitude"),
                "active": ref("Activation"),
            },
            "required": ["id", "operation", "geometry", "lower_limit", "upper_limit"],
        },
    }


def root_fields(common):
    """Fields every measure contract shares: identity, availability, authoring notes and extensions."""
    def ref(name):
        return {"$ref": common + "#/$defs/" + name}

    return {
        "$schema": {"type": "string"},
        "id": ref("Identifier"),
        "name": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "active": ref("Activation"),
        "notes": {"type": "string"},
        "resources_ref": ref("ResourceRef"),
        "extensions": ref("Extensions"),
    }


def coordination_fields(common):
    """Fields shared by measures controlled by an agency: agency, channels, purpose, restrictions and instructions."""
    texts = {"type": "array", "items": {"type": "string", "minLength": 1}}
    return {
        "controlling_agency": {"$ref": common + "#/$defs/Identifier", "x-catalog": "agencies"},
        "channels": {"type": "array", "items": {"$ref": common + "#/$defs/Identifier"}, "x-catalog": "channels"},
        "purpose": {"type": "string", "minLength": 1},
        "restrictions": deepcopy(texts),
        "coordination_instructions": deepcopy(texts),
    }


def models(base, version, dialect, common):
    def ref(name):
        return {"$ref": common + "#/$defs/" + name}

    shared = {**root_fields(common), **coordination_fields(common)}
    orbit = {
        "$schema": dialect, "$id": base + "orbit:" + version, "title": "Orbit", "type": "object", "additionalProperties": False,
        "description": schema_description("measures/orbit"),
        "properties": {**deepcopy(shared), "type": {"const": "ORBIT"},
                       "geometry": {"oneOf": [ref("Geometry_" + kind) for kind in ("circle", "racetrack", "track_racetrack", "figure_eight", "line", "point", "description")]},
                       "altitude": ref("AltitudeBlock")},
        "required": ["id", "name", "type", "geometry", "altitude", "active"],
    }
    airspace = {
        "$schema": dialect, "$id": base + "airspace:" + version, "title": "Airspace", "type": "object", "additionalProperties": False,
        "description": schema_description("measures/airspace"),
        "properties": {**deepcopy(shared),
                       "type": {"const": "AIRSPACE"},
                       "airspace_type": airspace_type_schema(),
                       "designator": {"type": "string", "minLength": 1},
                       "local_type": {"type": "string", "minLength": 1},
                       "airspace_class_code": {"enum": [*"ABCDEFG", "", " "]},
                       "components": {"type": "array", "minItems": 1, "items": ref("AirspaceComponent")}},
        "required": ["id", "name", "type", "airspace_type", "components", "active"],
        "allOf": [
            {"if": {"properties": {"airspace_type": {"const": "Class" + code}}, "required": ["airspace_type"]},
             "then": {"properties": {"airspace_class_code": {"enum": [code, "", " "]}}}} for code in "ABCDEFG"
        ] + [{"if": {"properties": {"airspace_type": {"const": "Other"}}, "required": ["airspace_type"]},
              "then": {"required": ["local_type"]}}],
    }
    return {"orbit": orbit, "airspace": airspace}


def component(identifier, geometry, lower=0, upper=10000, reference="MSL", operation="add"):
    return {"id": identifier, "operation": operation, "geometry": deepcopy(geometry),
            "lower_limit": {"value": lower, "unit": "ft", "reference": reference},
            "upper_limit": {"value": upper, "unit": "ft", "reference": "MSL"}}


def class_b_components():
    center = {"latitude": 37.1, "longitude": -115.5}
    return [component(name, {"kind": "circle", "center": center, "radius": {"value": radius, "unit": "nm"}}, lower, upper, reference)
            for name, radius, lower, upper, reference in (
                ("surface", 5, 0, 10000, "AGL"), ("inner-shelf", 10, 2500, 10000, "MSL"),
                ("outer-shelf", 20, 5000, 9000, "MSL"))]
