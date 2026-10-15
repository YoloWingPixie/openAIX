"""Communications standard checks (schemas/comms-standard.schema.json). Hooks follow the check/validate.py area contract.

Errors:
- an STN, a laser code of a member or a Mode 3 is used twice across flights and support (laser alternates are a separate
  table and are not compared);
- a TACAN channel and band is used by two support or ship records;
- a TACAN channel is in `restrictions.tacan`, or a Mode 3 is in `restrictions.mode_3`;
- a channel reference does not resolve;
- the lead and wing air-to-air TACAN channels of a flight are not 63 apart, or their bands differ;
- a member value does not match its `rules` pattern;
- a frequency outside its band is rejected by check/navigation.py, which every frequency in the document goes through.
Warning (`warnings`, printed by `openaix validate`): a laser code above 1788, outside band I of most DCS aircraft.
"""
from openaix.check.contract import ContractError, pointer

WING_OFFSET = 63
BAND_I_LIMIT = "1788"
# Member fields whose values a rule pattern computes.
PATTERNS = ("stn", "laser_code", "mode_3")


def semantic(value, path, period):
    pass


def catalogues(document, resources):
    if document.get("kind") != "comms_standard":
        return {}
    return {"channels": document.get("channels", {}), "support": document.get("support", {}), "flights": document.get("flights", {}),
            "squadrons": document.get("squadrons", {})}


def fail(path, reason):
    raise ContractError(pointer(path), reason)


def unique(seen, key, path, what):
    if key in seen:
        fail(path, f"duplicate {what} {key}")
    seen[key] = path


def member_context(flight, member):
    block = flight.get("stn_block", "")
    return {"stn_block": block, "stn_tail": block[1:], "laser_block": flight.get("laser_block", ""), "member": member["member"]}


def rule_checks(document):
    rules = {rule["field"]: rule["pattern"] for rule in document.get("rules", [])}
    for key, flight in document.get("flights", {}).items():
        for index, member in enumerate(flight["members"]):
            for field, pattern in rules.items():
                if field in PATTERNS and field in member:
                    expected = pattern.format(**member_context(flight, member))
                    if member[field] != expected:
                        fail(("flights", key, "members", index, field), f"{field} {member[field]} does not match rule {pattern} ({expected})")


def document(document, resources):
    if document.get("kind") != "comms_standard":
        return
    stns, lasers, modes, beacons = {}, {}, {}, {}
    banned_modes = set(document.get("restrictions", {}).get("mode_3", []))
    banned_tacan = {(channel, restriction["band"]) for restriction in document.get("restrictions", {}).get("tacan", [])
                    for channel in restriction["channels"]}
    for key, flight in document.get("flights", {}).items():
        for index, member in enumerate(flight["members"]):
            where = ("flights", key, "members", index)
            unique(stns, member["stn"], where, "STN")
            unique(modes, member["mode_3"], where, "Mode 3")
            if "laser_code" in member:
                unique(lasers, member["laser_code"], where, "laser code")
        lead, wing = flight["tacan_aa"]["lead"], flight["tacan_aa"]["wing"]
        if wing["channel"] - lead["channel"] != WING_OFFSET or wing["band"] != lead["band"]:
            fail(("flights", key, "tacan_aa"), f"wing TACAN must be {WING_OFFSET} above the lead TACAN, in the same band")
        for position in ("lead", "wing"):
            if (flight["tacan_aa"][position]["channel"], flight["tacan_aa"][position]["band"]) in banned_tacan:
                fail(("flights", key, "tacan_aa", position), "TACAN channel is restricted")
    for key, support in document.get("support", {}).items():
        unique(stns, support["stn"], ("support", key), "STN")
        unique(modes, support["mode_3"], ("support", key), "Mode 3")
    for group in ("support", "ships"):
        for key, record in document.get(group, {}).items():
            beacon = (record["tacan"]["channel"], record["tacan"]["band"])
            unique(beacons, beacon, (group, key), "TACAN")
            if beacon in banned_tacan:
                fail((group, key, "tacan"), "TACAN channel is restricted")
    for key, flight in document.get("flights", {}).items():
        for index, member in enumerate(flight["members"]):
            if member["mode_3"] in banned_modes:
                fail(("flights", key, "members", index, "mode_3"), "Mode 3 is restricted")
    for key, support in document.get("support", {}).items():
        if support["mode_3"] in banned_modes:
            fail(("support", key, "mode_3"), "Mode 3 is restricted")
    rule_checks(document)


def warnings(document):
    """(JSON pointer, text) for each laser code above 1788; most DCS aircraft and weapons accept only band I."""
    codes = [(("flights", key, "members", index, "laser_code"), member["laser_code"]) for key, flight in document.get("flights", {}).items()
             for index, member in enumerate(flight["members"]) if "laser_code" in member]
    laser = document.get("laser", {})
    codes += [(("laser", "jtac", index, "code"), entry["code"]) for index, entry in enumerate(laser.get("jtac", []))]
    codes += [(("laser", "alternates", key), code) for key, code in laser.get("alternates", {}).items()]
    return [(pointer(path), f"laser code {code} is outside band I (1111 to 1788); verify in DCS") for path, code in codes if code > BAND_I_LIMIT]
