"""Forward Air Controller (FAC/JTAC) record.

The portable record keeps identity, role, position, channels, laser codes, terminal control,
initial and egress points, smoke and equipment (ORDERS-05). Application settings are in the namespace of each
application, under `extensions`. Descriptions come from describe/resolve.py.
"""
from copy import deepcopy

EQUIPMENT_KINDS = ("laser_designator", "laser_rangefinder", "gps", "day_optic", "thermal_imager", "night_vision",
                   "ir_pointer", "smoke", "illumination", "radio", "other")
# How the controller's reported target coordinates are produced (DOCTRINE-06). A doctrinal target
# location error category (CAT I-VI, JP 3-09.3 (2014) Figure III-5) is not modelled: no consuming application uses one.
COORDINATE_SOURCES = ("lrf", "visual", "exact")


def enrich_fac(schema, common):
    def ref(name):
        return {"$ref": common + "#/$defs/" + name}

    def text():
        return {"type": "string", "minLength": 1}

    def obj(properties, required=()):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required)}

    def boolean():
        return {"type": "boolean"}

    def points(roles):
        return {"type": "array", "items": ref("ControlMeasureSelection") | {"x-measure-kinds": ["POINT"], "x-point-roles": roles}}

    code = ref("LaserCode")
    equipment = obj({
        "id": ref("Identifier"), "name": text(), "kind": {"enum": list(EQUIPMENT_KINDS)},
        "quantity": {"type": "integer", "minimum": 1}, "available": boolean(),
        "max_range": ref("Length"), "horizontal_accuracy": ref("Length"), "vertical_accuracy": ref("Length"),
        "laser_codes": {"type": "array", "items": deepcopy(code)}, "notes": text(),
    }, ["id", "kind"])
    schema["properties"].update({
        "equipment": {"type": "array", "items": equipment},
        "coordinate_source": {"enum": list(COORDINATE_SOURCES)},
        "initial_points": points(["initial", "fix"]),
        "egress_points": points(["egress", "gate", "fix"]),
        "default_laser_code": deepcopy(code),
        "smoke_color": {"enum": ["white", "red", "green", "orange", "blue"]},
    })
