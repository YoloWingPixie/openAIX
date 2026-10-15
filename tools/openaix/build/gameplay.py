"""Per-aircraft, package, communication, fuel and CAS data that crews and simulators need to fly a plan.

- Per aircraft: board number, crew, laser code and a Link 16 data set (`AircraftOverride`, `Identification`).
- Package timing: time on target, push time and push point.
- Communications: radio assignments by flight operation, and reusable communication plans.
- Fuel: the fuel that the mission requires and the burn rate.
- Steerpoint numbers on route points.
- One CAS brief definition in common.schema.json, shared by the ATO and the OPORD, with one target-mark enumeration.
- Word-valued enumerations that earlier used upper case are lower case (see ENUM_CASE below).

Descriptions come from describe/tables/gameplay.py. The OPORD weather, carrier and print-extension additions are
authored in build/opord/ and build/navigation.py.
"""
from copy import deepcopy

from openaix.build.opord.schema import DIRECTIONS

# Marks of a target (JP 3-09.3 (2014) Chapter III lists laser, infrared pointer, smoke, indirect fire, tracer and talk-on;
# white phosphorus and illumination come from the earlier OPORD CAS brief). One enumeration for every target-mark field.
TARGET_MARKS = ("laser", "infrared_pointer", "smoke", "white_phosphorus", "illumination", "indirect_fire", "tracer", "talk_on")
# openAIX planning values for the means that mark the friendly position; JP 3-09.3 leaves the means to the controller.
FRIENDLY_MARKINGS = ("panel", "smoke", "mirror", "strobe", "infrared_strobe", "chemical_light", "flare")
CREW_ROLES = ("pilot", "copilot", "weapon_systems_officer", "radar_intercept_officer", "gunner", "other")
HAZARD_KINDS = ("obstruction", "wires", "terrain", "friendly_aircraft", "indirect_fire", "weather", "other")
OFFSET_DIRECTIONS = ("left", "right")
PRESSURE_UNITS = ("inHg", "hPa")
FUEL_RATE_UNITS = ("kg/h", "lb/h")
# Link 16 station numbers are five octal digits (STN 00001 to 77777); MIDS channels are 1 to 127.
STN = r"^[0-7]{5}$"
MIDS_CHANNELS = (1, 127)

# Word-valued enumerations that the imported models spell in upper case. openAIX spells enumeration values in
# lower case snake_case; upper case stays for codes (acronyms, designators, units and classification markings).
# (schema, definition, field) of each enumeration to change. tests/enum_case_test.py lists the codes that stay.
ENUM_CASE = (
    ("ato", "AttackAssignment", "desired_effect"),
    ("jiptl", "JIPTLTarget", "desired_effect"),
    ("jiptl", "JIPTLTarget", "status"),
    ("resources", "ReportDefinition", "precedence"),
)


def lowercase_enums(artifacts):
    for schema, definition, field in ENUM_CASE:
        node = artifacts["schemas/" + schema + ".schema.json"]["$defs"][definition]["properties"][field]
        node["enum"] = [value.lower() for value in node["enum"]]
        if isinstance(node.get("default"), str):
            node["default"] = node["default"].lower()


def _nodes(prefix):
    """Schema node builders; `prefix` is the schema that `$ref` values to common definitions point into."""
    def c(name):
        return {"$ref": prefix + "#/$defs/" + name}

    def ident(collection=None):
        node = c("Identifier")
        if collection:
            node["x-catalog"] = collection
        return node

    def text():
        return {"type": "string", "minLength": 1}

    def array(items, minimum=None, unique=True):
        node = {"type": "array", "items": items}
        if minimum:
            node["minItems"] = minimum
        if unique:
            node["uniqueItems"] = True
        return node

    def obj(properties, required=()):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required)}

    def sel(kinds, roles=None):
        node = c("ControlMeasureSelection") | {"x-measure-kinds": list(kinds)}
        if roles:
            node["x-point-roles"] = list(roles)
        return node

    return c, ident, text, array, obj, sel


def _localize(node, prefix):
    """Point references to common definitions at the definitions of the schema that holds them."""
    if isinstance(node, dict):
        return {key: (value[len(prefix):] if key == "$ref" and isinstance(value, str) and value.startswith(prefix + "#") else _localize(value, prefix))
                for key, value in node.items()}
    if isinstance(node, list):
        return [_localize(item, prefix) for item in node]
    return node


def common_definitions(schema, catalogue, ato):
    """Pressure, target marks, radio assignments and the CAS brief in common.schema.json.

    The ATO CAS brief and the OPORD 9-line brief are the two uses of the one CAS brief definition; the controller
    contact and the check-in move to common with it.
    """
    c, ident, text, array, obj, sel = _nodes("")
    defs, ato_defs = schema["$defs"], ato["$defs"]
    common_id = schema["$id"]
    fscm = sorted(entry["code"] for entry in catalogue["types"] if entry["category"] == "fscm") + ["ACA"]
    defs["Pressure"] = obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"enum": list(PRESSURE_UNITS)}}, ("value", "unit"))
    defs["LinkStation"] = {"type": "string", "pattern": STN}
    defs["TargetMark"] = {"type": "string", "enum": list(TARGET_MARKS)}
    defs["FriendlyMarking"] = {"type": "string", "enum": list(FRIENDLY_MARKINGS)}
    defs["BearingRange"] = obj({"start_bearing": c("Bearing"), "end_bearing": c("Bearing")}, ("start_bearing", "end_bearing"))
    defs["Hazard"] = obj({"kind": {"enum": list(HAZARD_KINDS)}, "position": c("GeoPoint"), "description": text()}, ("kind",))
    defs["RadioAssignment"] = obj({
        "channel": ident("channels"), "radio": text(), "preset": {"type": "integer", "minimum": 1}, "purpose": text(),
        "activities": array({"type": "string", "pattern": r"^[a-z][a-z0-9_.-]*$"}, 1),
    }, ("channel",))
    for name in ("ControllerContact", "CheckIn"):
        defs[name] = _localize(ato_defs[name], common_id)
    defs["CasBrief"] = obj({
        # Identity and control
        "id": c("Identifier"),
        "ato_mission": ident("ato_missions"),
        "controller": ident("controllers"),
        "controllers": array(c("ControllerContact"), 1),
        "control_type": {"enum": ["type_1", "type_2", "type_3"]},
        "method_of_attack": {"enum": ["bomb_on_target", "bomb_on_coordinate"]},
        "check_in": c("CheckIn"),
        # Ground and airspace picture
        "contact_points": array(sel(["POINT"], ["control"])),
        "initial_points": array(sel(["POINT"], ["initial"])),
        "holding": array(sel(["ORBIT", "POINT", "ROZ"])),
        "holding_altitude": c("AltitudeBlock"),
        "fire_support_measures": array(sel(fscm)),
        "friendly_lines": array(sel(["FLOT", "FEBA", "PL", "LOA", "LD", "BOUNDARY"])),
        "ground_scheme_summary": text(),
        # The nine lines
        "initial_point": ident("control_measures") | {"x-point-roles": ["initial"]},
        "heading": c("Bearing"),
        "distance": c("Length"),
        "offset_direction": {"enum": list(OFFSET_DIRECTIONS)},
        "target_elevation": c("Elevation"),
        "target_description": text(),
        "target_position": c("GeoPoint"),
        "target": ident("targets"),
        "mark": c("TargetMark"),
        "marks": array(c("TargetMark")),
        "laser_code": c("LaserCode"),
        "laser_codes": array(c("LaserCode")),
        "laser_target_line": c("Bearing"),
        "friendly_direction": {"enum": list(DIRECTIONS)},
        "friendly_distance": c("Length"),
        "friendly_marking": c("FriendlyMarking"),
        "danger_close": {"type": "boolean"},
        "egress_point": ident("control_measures") | {"x-point-roles": ["egress"]},
        "final_attack_headings": array(c("BearingRange"), 1),
        "time_on_target": c("DateTime"),
        "time_to_target_seconds": {"type": "number", "minimum": 0},
        "threats": array(ident("threats")),
        "hazards": array(c("Hazard")),
        "remarks": text(),
    })


def enrich_gameplay(artifacts, common):
    """Apply the gameplay additions to the ATO, the resource catalogue and common.schema.json."""
    c, ident, text, array, obj, sel = _nodes(common)
    shared = artifacts["schemas/common.schema.json"]
    ato = artifacts["schemas/ato.schema.json"]
    resources = artifacts["schemas/resources.schema.json"]
    common_definitions(shared, artifacts["catalogues/control-measures.json"], ato)
    defs = ato["$defs"]
    for name in ("ControllerContact", "CheckIn", "RadioAssignment"):
        defs[name] = c(name)
    defs["CASBrief"] = c("CasBrief")

    # Per-aircraft data
    defs["CrewMember"] = obj({"name": text(), "role": {"enum": list(CREW_ROLES)}}, ("name", "role"))
    defs["AircraftOverride"]["properties"].update({
        "board_number": {"type": "string", "minLength": 1, "maxLength": 6},
        "crew": array({"$ref": "#/$defs/CrewMember"}, 1, unique=False),
        "laser_code": c("LaserCode"),
    })
    channel = {"type": "integer", "minimum": MIDS_CHANNELS[0], "maximum": MIDS_CHANNELS[1]}
    defs["Link16"] = obj({
        "stn": c("LinkStation"), "fighter_channel": dict(channel), "mission_channel": dict(channel),
        "special_channel": dict(channel), "donors": array(c("LinkStation")),
        "team": array(c("LinkStation")),
    })
    defs["Identification"]["properties"]["link16"] = {"$ref": "#/$defs/Link16"}

    # Package timing
    package = defs["Package"]["properties"]
    for field in ("time_on_target", "push_time"):
        package[field] = deepcopy(package["rendezvous_time"])
        package[field].pop("description", None)
    package["push_point"] = ident("control_measures") | {"x-point-roles": ["push"]}

    # Communication plans
    defs["Flight"]["properties"]["comm_plan"] = ident("comm_plans")

    # Fuel
    defs["FuelRate"] = obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"enum": list(FUEL_RATE_UNITS)}}, ("value", "unit"))
    fuel = defs["FuelPlan"]["properties"]
    fuel["mission_required"] = {"$ref": "#/$defs/Mass"}
    fuel["burn_rate"] = {"$ref": "#/$defs/FuelRate"}

    # Resource catalogue: communication plans and steerpoint numbers
    rdefs = resources["$defs"]
    rdefs["RadioAssignment"] = c("RadioAssignment")
    rdefs["CommPlan"] = obj({"name": text(), "assignments": array({"$ref": "#/$defs/RadioAssignment"}, 1, unique=False)}, ("name", "assignments"))
    rdefs["ResourceData"]["properties"]["comm_plans"] = {
        "type": "object", "additionalProperties": {"$ref": "#/$defs/CommPlan"}, "propertyNames": c("Identifier")}
    rdefs["RoutePoint"]["properties"]["number"] = {"type": "integer", "minimum": 1}

    lowercase_enums(artifacts)
