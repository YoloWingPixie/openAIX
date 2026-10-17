"""Communications standard: the channels, radio plans, flights, support, ships, Link 16, IFF and laser codes of one force.

The record is `schemas/comms-standard.schema.json`; the instance of the CSG8 standard is hand-authored in
`standards/csg8/comms-standard.json`. The document is explicit: it gives every per-member value (STN, laser code,
Mode 3), and `rules` states the patterns that the values follow. check/comms_standard.py checks that the tables obey
the patterns, that the codes are unique and that the restrictions hold. Consumers look values up and never compute them.
Every record that holds values has a `status` (`adopted` or `proposed`), the proposals it carries and a source locator.
Descriptions are in describe/tables/comms_standard.py.
"""
from openaix.build.common import BASE, COMMON, DIALECT, RESOURCES, VERSION, array, external, obj, ref, text
from openaix.build.gameplay import MIDS_CHANNELS, STN

COMMS_STANDARD = BASE + "comms-standard:" + VERSION
SPINS = BASE + "spins:" + VERSION
STATUSES = ("adopted", "proposed")
# The closed list of radios that a radio plan names; add a value only when a consumer needs it.
RADIOS = ("uhf_1", "uhf_2", "vhf", "arc_159", "arc_182", "mids")
SUPPORT_ROLES = ("tanker", "recovery_tanker", "awacs")
REFUEL_TYPES = ("boom", "basket")
RULE_FIELDS = ("stn", "laser_code", "mode_3", "mode_1", "tacan_wing")
MODE_4 = ("on", "off", "as_directed")
TEAM_RULES = ("flight_members",)
DONOR_RULES = ("awacs_and_flight_leads",)
OCTAL4 = r"^[0-7]{4}$"
OCTAL2 = r"^[0-7]{2}$"
MODE_1 = r"^[0-7][0-3]$"


def identifier(collection=None):
    node = external("Identifier")
    if collection:
        node["x-catalog"] = collection
    return node


def mids(minimum=MIDS_CHANNELS[0]):
    return {"type": "integer", "minimum": minimum, "maximum": MIDS_CHANNELS[1]}


def record(properties, required=()):
    """A record that holds values: its status, the proposals it carries (A1, B11) and the place of its values in the source."""
    return obj({**properties, "status": ref("Status"), "proposals": {**array({"type": "string", "pattern": r"^[a-d][0-9]+$"}, 1), "uniqueItems": True},
                "source": external("DocumentRef")}, required)


def collection(name):
    return {"type": "object", "additionalProperties": ref(name), "propertyNames": external("Identifier")}


def comms_standard_schema():
    preset = {"oneOf": [external("RadioAssignment"), obj({"preset": {"type": "integer", "minimum": 1}, "flight_channel": {"enum": ["intraflight"]}},
                                                          ("preset", "flight_channel"))]}
    member = obj({"member": {"type": "integer", "minimum": 1, "maximum": 4}, "stn": external("LinkStation"), "laser_code": external("LaserCode"),
                  "mode_3": text(pattern=OCTAL4), "tacan": external("TACAN")}, ("member", "mode_3"))
    defs = {
        "Status": {"enum": list(STATUSES), "default": "adopted"},
        "Radio": obj({"radio": {"enum": list(RADIOS)}, "label": text(), "start_preset": {"type": "integer", "minimum": 1},
                      "presets": array(preset)}, ("radio", "presets")),
        "RadioPlan": record({"name": text(), "aircraft_types": array(external("Identifier"), 1), "radios": array(ref("Radio"), 1)},
                            ("name", "aircraft_types", "radios")),
        "Squadron": record({"name": text(), "aircraft_type": external("Identifier"), "flights": array(identifier("flights")),
                            "stn_prefix": text(pattern=OCTAL2), "mode_1": text(pattern=MODE_1),
                            "mids": obj({"voca": mids(), "vocb": mids()})}, ("name", "aircraft_type", "stn_prefix", "mode_1")),
        "Member": member,
        "TacanPair": obj({"lead": external("TACAN"), "wing": external("TACAN")}, ("lead", "wing")),
        "Flight": record({"callsign": text(), "squadron": identifier("squadrons"), "aircraft_type": external("Identifier"),
                          "datalink_callsign": text(pattern=r"^[A-Z]{2}$"), "intraflight": identifier("channels"), "mids_channel": mids(),
                          "stn_block": text(pattern=OCTAL4), "laser_block": text(pattern=r"^[1-8][1-8]$"), "members": array(ref("Member"), 1),
                          "tacan_aa": ref("TacanPair")},
                         ("callsign", "squadron", "aircraft_type", "intraflight", "stn_block", "members", "tacan_aa")),
        "Support": record({"callsign": text(), "role": {"enum": list(SUPPORT_ROLES)}, "aircraft_type": external("Identifier"),
                           "refuel": {"enum": list(REFUEL_TYPES)}, "channels": array(identifier("channels"), 1), "tacan": external("TACAN"),
                           "datalink_callsign": text(pattern=r"^[A-Z]{2}$"), "stn": external("LinkStation"), "mode_1": text(pattern=MODE_1),
                           "mode_3": text(pattern=OCTAL4)},
                          ("callsign", "role", "aircraft_type", "channels", "tacan", "datalink_callsign", "stn", "mode_3")),
        "Ship": record({"hull": text(pattern=r"^[A-Za-z0-9_]+$"), "name": text(), "tacan": external("TACAN"),
                        "icls_channel": {"type": "integer", "minimum": 0, "maximum": 19}, "link4": external("Frequency"), "acls": {"type": "boolean"},
                        "radio": identifier("channels"), "awacs": identifier("support"), "recovery_tanker": identifier("support"),
                        "standard": {"type": "boolean"}}, ("hull", "name", "tacan", "icls_channel", "link4")),
        "FieldOverride": obj({"tacan": external("TACAN"), "ils": external("Frequency"), "channels": array(identifier("channels"), 1)}),
        "Airfields": record({"rule": {"enum": ["airfield_record"]}, "link4": {"const": False}, "overrides": {"type": "object", "additionalProperties": ref("FieldOverride"),
                                                                                                           "propertyNames": external("Identifier")}}, ("rule", "link4")),
        "HornetNet": record({"aic": mids(), "ff1": mids(), "ff2": mids()}, ("aic", "ff1", "ff2")),
        "Datalink": record({"network": obj({"fighter_channel": mids(), "mission_channel": mids(), "special_channel": mids(),
                                            "transmit_power": {"type": "integer", "minimum": 0}}, ("fighter_channel", "mission_channel", "special_channel")),
                            "hornet": ref("HornetNet"), "team_rule": {"enum": list(TEAM_RULES)},
                            "donor_rule": {"enum": list(DONOR_RULES)}}, ("network",)),
        "Iff": record({"defaults": obj({"mode_2": text(pattern=OCTAL4), "mode_4": {"enum": list(MODE_4)}, "mode_c": {"type": "boolean"}}, ("mode_4", "mode_c"))},
                      ("defaults",)),
        "JtacCode": record({"code": external("LaserCode")}, ("code",)),
        "Laser": record({"jtac": array(ref("JtacCode")), "blocks": {"type": "object", "additionalProperties": text(pattern=r"^[1-8][1-8]$"),
                                                                       "propertyNames": external("Identifier")},
                         "alternates": {"type": "object", "additionalProperties": external("LaserCode"), "propertyNames": external("Identifier")}}),
        "Rule": obj({"field": {"enum": list(RULE_FIELDS)}, "pattern": text(), "text": text()}, ("field", "pattern")),
        "TacanRestriction": obj({"channels": array({"type": "integer", "minimum": 1, "maximum": 126}, 1), "band": {"enum": ["X", "Y"]},
                                 "reason": text()}, ("channels", "band")),
        "Restrictions": record({"tacan": array(ref("TacanRestriction")), "frequencies": array({"$ref": SPINS + "#/$defs/RestrictedFrequency"}),
                                "mode_3": array(text(pattern=OCTAL4))}),
    }
    properties = {
        "$schema": text(format="uri"), "kind": {"const": "comms_standard"}, "schema_version": {"const": VERSION}, "meta": external("Metadata"),
        "sources": array(external("DocumentRef")), "extensions": external("Extensions"),
        "channels": {"type": "object", "additionalProperties": {"$ref": RESOURCES + "#/$defs/Channel"}, "propertyNames": external("Identifier")},
        "radio_plans": collection("RadioPlan"), "squadrons": collection("Squadron"), "flights": collection("Flight"),
        "support": collection("Support"), "ships": collection("Ship"), "airfields": ref("Airfields"), "datalink": ref("Datalink"),
        "iff": ref("Iff"), "laser": ref("Laser"), "rules": array(ref("Rule")), "restrictions": ref("Restrictions"),
    }
    return {"$schema": DIALECT, "$id": COMMS_STANDARD, "title": "Communications standard", "$defs": defs,
            **obj(properties, ("kind", "schema_version", "meta"))}
