"""Standard conventional load (SCL): one store configuration of one aircraft type, as a first-class record.

The shape follows what the owner's scl-tools carries for each load (src/scl, profiles/*.json, src/solver,
src/payloads): an identity and the unit's SCL number, an optional SCL code in the compact notation of the unit
(`2A88.3A.1X.2`), the aircraft type, the missions and the era with its variant tags, the bill of stores (what the
load is) and the station layout (where each store goes), the fuze of each store (profiles/fuzing.json), the gun
rounds, countermeasures and a default laser code. The aircraft type is an entry of the `aircraft_types` catalogue.
Simulator data is in `extensions.sim` (sim/bindings.py): the DCS load of the SCL, the DCS pylon, label, class
identifier (CLSID) and Mission Editor settings of each station, the CLSIDs of a store and the DCS type name of an
aircraft type.

The record is `schemas/scl.schema.json`. The resource catalogue `scls` map holds the same record; ATO flights,
aircraft overrides, SCL alternatives, weapon loads and target-list engagement means refer to it by identifier.
check/scl.py validates the bill against the stations, the flights against their loads and the DCS
stations against sources/dcs/aircraft-stations.json. Descriptions are in describe/tables/orders.py.
"""
from openaix.build.common import BASE, COMMON, DIALECT, VERSION, array, external, obj, ref, text
from openaix.sim.bindings import attach_policy

SCL = BASE + "scl:" + VERSION
# Fuze functions of a weapon (the ATO weapon load and the SCL share the Fuze definition).
FUZE_FUNCTIONS = ("instantaneous", "delay", "proximity", "airburst")
# Pod functions: the SCL code pod classes of scl-tools (J, T, WW, DL, REC) and the tactical jamming and
# navigation pods of the OIR loads.
POD_ROLES = ("targeting", "navigation", "self_protection_jamming", "tactical_jamming", "emitter_targeting",
             "datalink", "reconnaissance", "other")
# The SCL code grammar of scl-tools (src/scl/codes.ts): elements of digits and capital letters joined by ".".
CODE_PATTERN = r"^[0-9A-Z]+(\.[0-9A-Z]+)*$"
AIRCRAFT_CATEGORIES = ("airplane", "helicopter", "unmanned")
# Tasking definitions of the ATO and the field that gives their role or mission type.
ROLE_FIELDS = ("role", "mission_type")


def identifier(collection=None):
    node = external("Identifier")
    if collection:
        node["x-catalog"] = collection
    return node


def count(minimum=1):
    return {"type": "integer", "minimum": minimum}


def fuze():
    return obj({"function": {"enum": list(FUZE_FUNCTIONS)}, "nose_fuze": text(), "tail_fuze": text(),
                "arming_delay_s": {"type": "number", "minimum": 0}, "delay_ms": {"type": "number", "minimum": 0},
                "height_of_burst": external("Length")}, ("function",))


def scl_schema():
    """The SCL record. `SCLMission` gets its tasking families and roles from the ATO in `enrich_scl`."""
    defs = {
        "SCLMission": obj({"tasking": {"enum": []}, "role": {"enum": []}}, ("tasking",)),
        "StoreLoad": obj({"store": identifier("stores"), "quantity": count(), "fuze": ref("Fuze"),
                          "laser_code": external("LaserCode"), "program": text()}, ("store", "quantity")),
        "StationLoad": obj({"station": text(), "rack": identifier("stores"), "items": array(ref("StoreLoad"), 1),
                            "extensions": external("Extensions")},
                           ("station", "items")),
        "Countermeasures": obj({"chaff": count(0), "flares": count(0), "program": text()}),
        "Fuze": fuze(),
    }
    properties = {
        "$schema": text(format="uri"), "id": external("Identifier"), "kind": {"const": "scl"},
        "name": text(), "scl_number": text(), "code": text(pattern=CODE_PATTERN),
        "aircraft_type": identifier("aircraft_types"),
        "missions": {**array(ref("SCLMission"), 1), "uniqueItems": True},
        "era": text(), "variant_tags": {**array(text(), 1), "uniqueItems": True},
        "stores": array(ref("StoreLoad")), "stations": array(ref("StationLoad"), 1),
        "gun_rounds": count(0), "countermeasures": ref("Countermeasures"), "laser_code": external("LaserCode"),
        "remarks": text(), "source": external("DocumentRef"),
        "resources_ref": external("ResourceRef"), "extensions": external("Extensions"),
    }
    return {"$schema": DIALECT, "$id": SCL, "title": "Standard conventional load", "$defs": defs,
            **obj(properties, ("id", "kind", "name", "aircraft_type"))}


def tasking_roles(ato):
    """(tasking kind, role values) for each typed tasking of the ATO, in the order of the tasking union."""
    defs = ato["$defs"]
    result = []
    for branch in defs["Mission"]["properties"]["tasking"]["oneOf"]:
        properties = defs[branch["$ref"].removeprefix("#/$defs/")]["properties"]
        roles = next((properties[name]["enum"] for name in ROLE_FIELDS if "enum" in properties.get(name, {})), [])
        result.append((properties["kind"]["const"], list(roles)))
    return result


def enrich_scl(artifacts):
    """Typed SCL references after the ATO taskings are complete: mission roles, store roles, the shared fuze."""
    ato = artifacts["schemas/ato.schema.json"]
    scl = artifacts["schemas/scl.schema.json"]
    families = tasking_roles(ato)
    mission = scl["$defs"]["SCLMission"]
    mission["properties"]["tasking"]["enum"] = [kind for kind, _ in families]
    mission["properties"]["role"]["enum"] = sorted({role for _, roles in families for role in roles})
    mission["allOf"] = [{"if": {"properties": {"tasking": {"const": kind}}},
                         "then": {"properties": {"role": {"enum": roles}}} if roles else {"not": {"required": ["role"]}}}
                        for kind, roles in families]

    # The ATO weapon load uses the SCL fuze and can name the SCL of the flight that carries the weapons.
    defs = ato["$defs"]
    defs.pop("Fuze", None)
    load = defs["WeaponLoad"]["properties"]
    load["fuze"] = {"$ref": SCL + "#/$defs/Fuze"}
    load["scl"] = identifier("scls")

    # Flights name an aircraft type of the catalogue, as SCLs do.
    defs["Flight"]["properties"]["aircraft_type"] = identifier("aircraft_types")

    # Resource catalogue: the `scls` map holds SCL records; a store has a family and, for a pod, a role.
    resources = artifacts["schemas/resources.schema.json"]
    rdefs = resources["$defs"]
    rdefs["ResourceData"]["properties"]["scls"] = {"type": "object", "additionalProperties": {"$ref": SCL},
                                                   "propertyNames": external("Identifier")}
    store = rdefs["Store"]
    store["properties"].pop("dcs_clsid", None)
    store["properties"]["family"] = text()
    store["properties"]["role"] = {"enum": list(POD_ROLES)}
    store["allOf"] = [{"if": {"required": ["role"]}, "then": {"properties": {"kind": {"const": "pod"}}}}]
    # Aircraft types: a neutral identifier and name; simulator type names are in `extensions.sim`.
    aircraft = obj({"name": text(), "category": {"enum": list(AIRCRAFT_CATEGORIES)}, "extensions": external("Extensions")}, ("name",))
    attach_policy(aircraft, COMMON, None, "aircraft_type")
    rdefs["AircraftType"] = aircraft
    rdefs["ResourceData"]["properties"]["aircraft_types"] = {"type": "object", "additionalProperties": {"$ref": "#/$defs/AircraftType"},
                                                             "propertyNames": external("Identifier")}
    for name in ("SCL", "SCLPayload", "SummaryPayload", "StationPayload", "CleanPayload", "StoreLoad", "StationLoad"):
        rdefs.pop(name, None)
