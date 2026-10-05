"""Forward Air Controller (FAC/JTAC) record and the namespaced Vox Bellica JTAC settings.

The portable record keeps identity, role, position, channels, laser codes, terminal control,
initial and egress points, smoke and equipment (ORDERS-05). Application settings (the DCS unit and the
observers that the Vox JTAC takes its position and sight from, search and laser range, stacking, night,
attack-heading and timing settings) live only in the `org.vox-bellica.jtac` extension. Descriptions come from describe/resolve.py.
"""
from copy import deepcopy

# Vox Bellica names and units are kept inside its own extension: they mirror its configuration file.
VOX_EXTENSION = "org.vox-bellica.jtac"
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

    def number(minimum=0, maximum=None):
        value = {"type": "number", "minimum": minimum}
        if maximum is not None:
            value["maximum"] = maximum
        return value

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
        "coalition": ref("Coalition"),
        "equipment": {"type": "array", "items": equipment},
        "coordinate_source": {"enum": list(COORDINATE_SOURCES)},
        "initial_points": points(["initial", "fix"]),
        "egress_points": points(["egress", "gate", "fix"]),
        "default_laser_code": deepcopy(code),
        "smoke_color": {"enum": ["white", "red", "green", "orange", "blue"]},
    })
    duration = text()
    stack = obj({"concurrent": boolean(), **{name: number() for name in (
        "radius_m", "block_ft", "helo_block_ft", "separation_ft", "helo_floor_ft", "slow_floor_ft", "fast_floor_ft")}})
    night = obj({"mode": {"enum": ["auto", "day", "night"]}, "sun_deg": number(-90, 90),
                 "start_hour": {"type": "integer", "minimum": 0, "maximum": 23}, "end_hour": {"type": "integer", "minimum": 0, "maximum": 23},
                 "utc_offset_h": number(-14, 14), "ir_mark": boolean(), "snake_amplitude_m": number(), "snake_period": deepcopy(duration)})
    settings = obj({"source_unit": text(), "group": text(), "observers": {"type": "array", "items": text(), "uniqueItems": True},
                    "search_range_m": number(), "laser_range_m": number(),
                    "voice_id": text(), "memory_file": text(), "readback_timeout_s": number(), "impact_window_s": number(),
                    "precise_coords_delay_s": {"type": "number", "maximum": 120},
                    "last_call_on_loss": boolean(), "town_ips": boolean(), "stack": stack, "night": night,
                    "launch_warnings": obj({"enabled": boolean(), "range_m": number(),
                                            "delay_min": deepcopy(duration), "delay_max": deepcopy(duration), "coalesce": deepcopy(duration)}),
                    "fah": obj({"laser_cone": boolean(), "laser_cone_deg": number(0, 180), "laser_prefer_deg": number(0, 180),
                                "observer_buffer_m": number(), "friendly_parallel_reds": number(),
                                "valley_min_depth_m": number(), "road_max_m": number(), "terrain": boolean()}),
                    "danger_close": obj({"initials": text()})})
    schema.setdefault("$defs", {})["VoxJTACSettings"] = settings
    schema["properties"]["extensions"] = {"allOf": [ref("Extensions"), {"properties": {VOX_EXTENSION: {"$ref": "#/$defs/VoxJTACSettings"}}}]}
