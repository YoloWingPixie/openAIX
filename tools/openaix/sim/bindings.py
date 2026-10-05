"""Simulator data: `extensions.sim.<sim>` of every record, its simulator profiles and the binding policies.

The core records are simulator-agnostic. Every simulator value of a record is in `extensions.sim`, keyed by the
simulator, so that one record can carry data for several simulators side by side. A profile types the data of one
simulator; DCS (sim/dcs.py, `extensions.sim.dcs`) is the first profile. The data of a simulator without a
profile is any object.

In a profile, `bindings` link the record to objects placed in a simulator mission (units, groups, statics,
drawings, trigger zones, airbases, parking stands); the other keys are simulator data that is not a mission object.
A binding policy names the objects that may represent one kind of entity. Each profile maps every policy to its own
object kinds, and a new measure kind fails generation until it has a policy.
"""
from openaix.describe.tables.common import BINDINGS
from openaix.sim import dcs


EXTENSION = "sim"
PROFILES = {dcs.SIM: dcs}
POLICIES = {name: BINDINGS[name] for name in (
    "area", "orbit", "route", "hold", "line", "map_point", "point", "host", "fixed_target", "mobile_target",
    "emitter", "airfield", "navaid", "flight", "aircraft", "stand")}
MEASURE_POLICIES = {
    "volume": "area", "area": "area", "aor": "area", "kb": "area", "mez": "area", "aca": "area", "isr": "area", "misarc": "area",
    "airspace": "area", "route": "route", "airway": "route", "line": "line", "fire-support-line": "line",
    "point": "point", "navaid": "navaid", "orbit": "orbit", "cl": None, "tl": None,
}
ROOT_POLICIES = {
    "airfield": "airfield", "c2-agency": "host", "fac": "host",
    "runway": "area", "localizer": "navaid", "procedure": "route", "holding": "hold",
    "path-point": "map_point", "msa": "area", "grid-mora": "area",
}
DEFINITION_POLICIES = {
    "AirspaceComponent": "area", "Aimpoint": "fixed_target", "RoutePoint": "point",
    "Agency": "host", "Area": "area", "FixedTarget": "fixed_target", "MobileTarget": "mobile_target", "AreaTarget": "area",
    "Flight": "flight", "AircraftOverride": "aircraft", "Stand": "stand", "Emitter": "emitter",
}
# Records whose simulator data has keys other than `bindings` (dcs.DATA_KEYS), by schema or definition name.
DATA_ROLES = {"Aimpoint": "aimpoint", "Emitter": "emitter", "Store": "store", "AircraftType": "aircraft_type",
              "scl": "scl", "StationLoad": "station", "Geometry_rectangle": "shape", "Geometry_ellipse": "shape"}
# Binding lists other than `bindings`, with their policy, by data role.
ROLE_LISTS = {"aimpoint": {"objects": "aimpoint_object"}}
for _name, _profile in PROFILES.items():
    _missing = {policy for policy in POLICIES} - _profile.POLICIES.keys()
    if _missing:
        raise ValueError("simulator profile " + _name + " has no binding policy for: " + ", ".join(sorted(_missing)))


def data_schema(common):
    """SimData (`extensions.sim`): the data of each simulator, keyed by the simulator identifier."""
    return {"type": "object", "propertyNames": {"$ref": common + "#/$defs/Identifier"},
            "properties": {name: {"$ref": common + "#/$defs/" + profile.DATA} for name, profile in PROFILES.items()},
            "additionalProperties": {"type": "object"}}


def profile_definitions(common):
    result = {"SimData": data_schema(common)}
    for profile in PROFILES.values():
        result[profile.OBJECT] = profile.object_schema(common)
        result[profile.DATA] = profile.data_schema(common)
    return result


def sim_overlay(policy=None, role=None):
    """The simulator data of one kind of record: allowed keys and binding policies in each profile."""
    result = {}
    for name, profile in PROFILES.items():
        keys = profile.DATA_KEYS.get(role, ("bindings",) if policy else ())
        policies = {key: value for key, value in ROLE_LISTS.get(role, {}).items() if key in keys}
        if policy and "bindings" in keys:
            policies["bindings"] = policy
        result[name] = profile.overlay(policies, keys)
    return {"properties": {EXTENSION: {"properties": result}}}


def attach_policy(schema, common, policy=None, role=None):
    """Restrict the `extensions.sim` data of a record to its binding policy and data role. A record with neither
    has no DCS data."""
    properties = schema.setdefault("properties", {})
    overlay = sim_overlay(policy, role)
    current = properties.get("extensions")
    if current is None or set(current) <= {"$ref", "description"}:
        properties["extensions"] = {"$ref": common + "#/$defs/Extensions", "allOf": [overlay]}
    elif "allOf" in current:
        current["allOf"].append(overlay)
    else:
        properties["extensions"] = {"allOf": [current, overlay]}


def attach_bindings(artifacts, common):
    for path, schema in artifacts.items():
        if not path.startswith("schemas/"):
            continue
        name = path.removeprefix("schemas/").removesuffix(".schema.json")
        if name.startswith("measures/"):
            contract = name.removeprefix("measures/")
            if contract not in MEASURE_POLICIES:
                raise ValueError("control measure requires an explicit simulator binding policy: " + contract)
            attach_policy(schema, common, MEASURE_POLICIES[contract])
        elif name in ROOT_POLICIES or name in DATA_ROLES:
            attach_policy(schema, common, ROOT_POLICIES.get(name), DATA_ROLES.get(name))
        for definition_name, definition in schema.get("$defs", {}).items():
            if (definition_name in DEFINITION_POLICIES or definition_name in DATA_ROLES) and "properties" in definition:
                attach_policy(definition, common, DEFINITION_POLICIES.get(definition_name), DATA_ROLES.get(definition_name))
        for branch in schema.get("$defs", {}).get("ControlMeasure", {}).get("oneOf", []):
            # Measure contracts are $ref branches with their own policy; only the namespaced extension branch is inline.
            if "properties" in branch and "pattern" in branch["properties"]["type"]:
                attach_policy(branch, common, "area")

