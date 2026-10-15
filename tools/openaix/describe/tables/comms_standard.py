"""Descriptions of the communications standard (build/comms_standard.py)."""
from openaix.describe import templates as d
from openaix.describe.tables.common import GENERIC


def gives(phrase, *notes):
    return d.statement("This field gives " + phrase, *notes)


def contains(phrase, *notes):
    return d.statement("This list contains " + phrase, *notes)


RECORDS = {"RadioPlan": "radio plan", "Squadron": "squadron", "Flight": "flight", "Support": "support aircraft", "Ship": "ship",
           "Airfields": "airfield rule", "Datalink": "data link network", "HornetNet": "Hornet data link set", "Iff": "identification setting",
           "JtacCode": "JTAC laser code", "Laser": "laser code plan", "Restrictions": "set of restrictions"}
SUBJECTS = {"Iff": "identification setting", "JtacCode": "joint terminal attack controller laser code", "TacanPair": "pair of TACAN channels"}

DESCRIPTIONS = {
    ("comms-standard", None): d.root("Communications standard", None, "one force's standing plan for radio channels, TACAN, Link 16 station numbers, "
                                     "identification codes and laser codes",
                                     "It gives every value of every aircraft, and `rules` gives the patterns that the values follow",
                                     "A consumer looks the values up and does not compute them"),
    ("comms-standard", "$schema"): GENERIC["$schema"]("communications standard"),
    ("comms-standard", "kind"): d.discriminator("a communications standard"),
    ("comms-standard", "schema_version"): d.statement("This field gives the version of the openAIX schema that this communications standard agrees with"),
    ("comms-standard", "meta"): d.statement("This field gives the identification, revision and issue data of this communications standard"),
    ("comms-standard", "sources"): contains("the documents that the values of the standard come from"),
    ("comms-standard", "extensions"): GENERIC["extensions"]("communications standard"),
    ("comms-standard", "channels"): d.map_of("radio channels, which are the frequency ladder, the tanker and support channels and the flight channels"),
    ("comms-standard", "radio_plans"): d.map_of("radio plans, which give the presets of the radios of an aircraft type"),
    ("comms-standard", "squadrons"): d.map_of("squadrons, which give the codes that a squadron shares"),
    ("comms-standard", "flights"): d.map_of("flights, which give the callsign, channels and the values of each member"),
    ("comms-standard", "support"): d.map_of("support aircraft: tankers and airborne early warning aircraft"),
    ("comms-standard", "ships"): d.map_of("ships, which give the beacons and the channels of a ship"),
    ("comms-standard", "airfields"): gives("the rule for the beacons and channels of land airfields"),
    ("comms-standard", "datalink"): gives("the Link 16 network and the rules for the team and the donors"),
    ("comms-standard", "iff"): gives("the default identification settings"),
    ("comms-standard", "laser"): gives("the laser codes of the controllers, the blocks and the alternatives"),
    ("comms-standard", "rules"): contains("the patterns that the values of the members follow", "The check validates the tables against these patterns"),
    ("comms-standard", "restrictions"): gives("the TACAN channels, frequencies and identification codes that nothing uses"),

    ("Status", None): d.entity("Status", "whether the owner adopted the value of a record or only proposed it"),
    ("TacanPair", "lead"): gives("the air-to-air TACAN channel of the lead aircraft"),
    ("TacanPair", "wing"): gives("the air-to-air TACAN channel of the wing aircraft"),

    ("Radio", None): d.entity("Radio", "one radio of an aircraft with its presets"),
    ("Radio", "radio"): d.enum("radio of the aircraft"),
    ("Radio", "label"): d.text("label of the radio, for display"),
    ("Radio", "start_preset"): gives("the number of the first preset of the radio"),
    ("Radio", "presets"): contains("the presets of the radio", "A preset gives a channel, or takes the intraflight channel of the flight"),
    ("Radio.presets", "preset"): gives("the number of the preset"),
    ("Radio.presets", "flight_channel"): d.enum("channel that the flight selects for this preset"),
    ("RadioPlan", "name"): d.name("radio plan"),
    ("RadioPlan", "aircraft_types"): d.references("aircraft types", "use this radio plan"),
    ("RadioPlan", "radios"): contains("the radios of the aircraft"),
    ("Squadron", "name"): d.name("squadron"),
    ("Squadron", "aircraft_type"): gives("the aircraft type of the squadron, as an identifier"),
    ("Squadron", "flights"): d.references("flights", "belong to this squadron"),
    ("Squadron", "stn_prefix"): gives("the first two octal digits of the Link 16 station numbers of the squadron"),
    ("Squadron", "mode_1"): gives("the identification Mode 1 code of the squadron, as two octal digits"),
    ("Squadron", "mids"): gives("the channels of the Link 16 voice nets of the squadron"),
    ("Squadron.mids", "voca"): gives("the channel of voice net A"),
    ("Squadron.mids", "vocb"): gives("the channel of voice net B, which is the net of the squadron"),
    ("Flight", "callsign"): gives("the callsign of the flight"),
    ("Flight", "squadron"): d.reference("squadron", "this flight belongs to"),
    ("Flight", "aircraft_type"): gives("the aircraft type of the flight, as an identifier"),
    ("Flight", "datalink_callsign"): gives("the callsign of the flight in the data link, as two capital letters"),
    ("Flight", "intraflight"): d.reference("radio channel", "the flight uses between its members"),
    ("Flight", "mids_channel"): gives("the channel of voice net A of the Link 16 terminal of the flight, from 1 to 127"),
    ("Flight", "stn_block"): gives("the first four octal digits of the Link 16 station numbers of the flight"),
    ("Flight", "laser_block"): gives("the two digits that follow the leading `1` in the laser codes of the flight"),
    ("Flight", "members"): contains("the members of the flight, with their codes"),
    ("Flight", "tacan_aa"): gives("the air-to-air TACAN channels of the lead and the wing of the flight"),
    ("Member", "member"): gives("the position of the aircraft in the flight, from 1 to 4"),
    ("Member", "stn"): gives("the Link 16 station number of the aircraft"),
    ("Member", "laser_code"): d.quantity("laser code of the aircraft", "LaserCode"),
    ("Member", "mode_3"): gives("the identification Mode 3 code of the aircraft, as four octal digits"),
    ("Member", "tacan"): gives("the TACAN channel of the aircraft, when it differs from the pair of the flight"),
    ("Support", "callsign"): gives("the callsign of the support aircraft"),
    ("Support", "role"): d.enum("role of the support aircraft"),
    ("Support", "aircraft_type"): gives("the aircraft type of the support aircraft, as an identifier"),
    ("Support", "refuel"): d.enum("refuelling method of the tanker"),
    ("Support", "channels"): d.references("radio channels", "the support aircraft uses"),
    ("Support", "tacan"): gives("the TACAN channel of the support aircraft"),
    ("Support", "datalink_callsign"): gives("the callsign of the support aircraft in the data link, as two capital letters"),
    ("Support", "stn"): gives("the Link 16 station number of the support aircraft"),
    ("Support", "mode_1"): gives("the identification Mode 1 code of the support aircraft, as two octal digits"),
    ("Support", "mode_3"): gives("the identification Mode 3 code of the support aircraft, as four octal digits"),
    ("Ship", "hull"): gives("the DCS hull type of the ship, such as `CVN_75`"),
    ("Ship", "name"): d.name("ship"),
    ("Ship", "tacan"): gives("the TACAN channel of the ship"),
    ("Ship", "icls_channel"): gives("the instrument carrier landing system channel of the ship, from 0 to 19"),
    ("Ship", "link4"): d.quantity("Link 4 frequency of the ship", "Frequency"),
    ("Ship", "acls"): d.flag("the ship has an automatic carrier landing system"),
    ("Ship", "radio"): d.reference("radio channel", "the ship uses for its control"),
    ("Ship", "awacs"): d.reference("support aircraft", "is the airborne early warning aircraft of the ship"),
    ("Ship", "recovery_tanker"): d.reference("support aircraft", "is the recovery tanker of the ship"),
    ("Ship", "standard"): d.flag("the standard names this ship as the standard carrier", "the ship is supported but is not the standard carrier"),
    ("FieldOverride", "tacan"): gives("the TACAN channel of the airfield, when it differs from the airfield record"),
    ("FieldOverride", "ils"): d.quantity("frequency of the instrument landing system of the airfield, when it differs from the airfield record", "Frequency"),
    ("FieldOverride", "channels"): d.references("radio channels", "the airfield uses instead of the channels of the airfield record"),
    ("Airfields", "rule"): d.enum("rule that gives the beacons and the channels of an airfield"),
    ("Airfields", "link4"): d.flag("an airfield has Link 4", "an airfield has no Link 4"),
    ("Airfields", "overrides"): d.map_of("values that differ from the airfield record", key="airfield identifier"),
    ("Datalink", "network"): gives("the Link 16 channels of the network"),
    ("Datalink.network", "fighter_channel"): gives("the channel of the fighter net, from 1 to 127"),
    ("Datalink.network", "mission_channel"): gives("the channel of the mission net, from 1 to 127"),
    ("Datalink.network", "special_channel"): gives("the channel of the special net, from 1 to 127"),
    ("Datalink.network", "transmit_power"): gives("the transmit power setting of the Link 16 terminal"),
    ("Datalink", "hornet"): gives("the Link 16 settings of the Hornet"),
    ("Datalink", "team_rule"): d.enum("rule that selects the team members of an aircraft"),
    ("Datalink", "donor_rule"): d.enum("rule that selects the donors of an aircraft"),
    ("HornetNet", "aic"): gives("the channel of the air intercept control net, from 1 to 127"),
    ("HornetNet", "ff1"): gives("the channel of the first fighter-to-fighter net, from 1 to 127"),
    ("HornetNet", "ff2"): gives("the channel of the second fighter-to-fighter net, from 1 to 127"),
    ("Iff", "defaults"): gives("the identification settings that apply when an order gives none"),
    ("Iff.defaults", "mode_2"): gives("the identification Mode 2 code, as four octal digits"),
    ("Iff.defaults", "mode_4"): d.enum("setting of identification Mode 4"),
    ("Iff.defaults", "mode_c"): d.flag("identification Mode C is on", "Mode C is off"),
    ("JtacCode", "code"): d.quantity("laser code of the controller", "LaserCode"),
    ("Laser", "jtac"): contains("the laser codes of the joint terminal attack controllers"),
    ("Laser", "blocks"): d.map_of("laser code blocks of the flights", key="flight identifier"),
    ("Laser", "alternates"): d.map_of("laser codes for a plan that gives one code to each flight", key="flight identifier"),
    ("Rule", None): d.entity("Rule", "the pattern that the values of one field of the members follow"),
    ("Rule", "field"): d.enum("field that the rule is for"),
    ("Rule", "pattern"): gives("the pattern, in which `{stn_block}`, `{stn_tail}`, `{laser_block}` and `{member}` stand for the values of the flight and the member"),
    ("Rule", "text"): d.text("explanation of the rule"),
    ("TacanRestriction", "channels"): contains("the TACAN channels that nothing uses"),
    ("TacanRestriction", "band"): d.enum("band of the restricted channels"),
    ("TacanRestriction", "reason"): d.text("reason for the restriction"),
    ("Restrictions", "tacan"): contains("the TACAN channels that nothing uses"),
    ("Restrictions", "frequencies"): contains("the frequencies that nothing uses as a preset"),
    ("Restrictions", "mode_3"): contains("the Mode 3 codes that nothing uses"),
}
for _name, _subject in RECORDS.items():
    DESCRIPTIONS[(_name, "status")] = d.enum("status of this " + _subject + ": the owner adopted its values, or only proposed them",
                                             "A proposed value can change")
    DESCRIPTIONS[(_name, "proposals")] = contains("the identifiers of the proposals that this " + _subject + " still carries, such as `a1` or `b11`")
    DESCRIPTIONS[(_name, "source")] = d.reference("source document", None, "The reference gives the identifier of the document, and the path and the section give the file and the line")
for _name in ("Flight",):
    DESCRIPTIONS[(_name, "extensions")] = GENERIC["extensions"]("flight")

# Definition names such as Flight and Ship also exist in other schemas: key every entry to this schema.
DESCRIPTIONS = {(key[0] if key[0] == "comms-standard" else "comms-standard:" + key[0], key[1]): text for key, text in DESCRIPTIONS.items()}
