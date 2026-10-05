"""FRAGO changes and SPINS sections. A FRAGO is a delta: JSON Pointer changes to an identified OPORD, ATO, ACO or
SPINS revision. A SPINS publication has typed sections."""
from openaix.build.opord.schema import (agencies_ref, agency_ref, airfield_ref, ATO_FLIGHTS, channel_ref,
                                        channels_ref, choice, common, define, DEFS, ident, integer, items, local,
                                        many, measure, measure_ref, measures_ref, missions_ref, name, orbit_ref,
                                        ORDER_PROTECTED_SITES, phases_ref, point_ref, POINTER, points_ref, rank,
                                        ref, refs, remarks, ROLE_RULE, string, summary, units_ref, window)
from openaix.describe import templates as d


# ---- FRAGO and SPINS changes ---------------------------------------------------------------------------
def change(name_, target):
    fields = {
        "op": (choice("add", "replace", "remove"), d.enum("operation of the change")),
        "path": (string(pattern=POINTER), d.statement("This field gives the location of the change, as a JSON Pointer of `RFC 6901`")),
        "value": ({}, d.statement("This field gives the new value at the location",
                                  d.enforced("An `add` or `replace` change shall have this field", "schema:then"),
                                  d.enforced("A `remove` change shall not have this field", "schema:else"))),
        "remarks": remarks("the change"),
    }
    required = ["op", "path"]
    if target:
        fields = {"target": (local("ChangeTarget"), d.reference("order", "the change is for")), **fields}
        required.insert(0, "target")
    define(name_, d.entity("Change", "one change to " + ("an identified order" if target else "the base publication")), fields, required)
    DEFS[name_]["allOf"] = [{"if": {"properties": {"op": {"enum": ["add", "replace"]}}},
                             "then": {"required": ["value"]}, "else": {"not": {"required": ["value"]}}}]


define("ChangeTarget", d.entity("Change target", "the type, identifier and revision of the order that a change is for"), {
    "kind": (choice("opord", "ato", "aco", "spins"), d.enum("type of the order")),
    "id": (common("Identifier"), d.reference("order", "the change is for", "The value is the `meta.id` field of the order")),
    "revision": (string(), d.statement("This field gives the revision of the order that the change is for")),
}, ("kind", "id", "revision"))
change("OrderChange", True)
change("PublicationChange", False)

# ---- SPINS sections -------------------------------------------------------------------------------------
define("SpinsRoe", d.entity("SPINS ROE summary", "the ROE summary for aircrews"), {
    "rules": (many("RoeRule"), d.list_of("ROE")),
    "measures": measures_ref("the ROE refer to"),
    "summary": summary("the ROE"),
})
define("SpinsNet", d.entity("SPINS net", "one radio net for aircrews"), {
    "id": ident("net", "the publication"),
    "name": name("net"),
    "channel": channel_ref("the net refers to"),
    "agency": agency_ref("controls the net"),
    "purpose": (string(), d.text("purpose of the net")),
}, ("id", "name", "channel"))
define("BrevityTerm", d.entity("Brevity word", "one brevity word and its definition for this operation"), {
    "id": ident("brevity word", "the publication"),
    "term": (string(), d.text("brevity word")),
    "meaning": (string(), d.text("definition of the brevity word")),
}, ("id", "term", "meaning"))
define("SpinsCommunications", d.entity("SPINS communications", "the radio nets and the brevity words"), {
    "nets": (many("SpinsNet"), d.list_of("radio nets")),
    "brevity": (many("BrevityTerm"), d.list_of("brevity words of the operation")),
    "remarks": remarks("communications"),
})
define("IffAssignment", d.entity("IFF assignment", "one IFF mode and code for a time interval"), {
    "id": ident("assignment", "the publication"),
    "mode": (choice("mode_1", "mode_2", "mode_3a", "mode_4", "mode_5", "mode_s"), d.enum("IFF mode")),
    "code": (string(pattern=r"^[0-7]{2,4}$"), d.statement("This field gives the code, as two or four octal digits",
                                                            "Modes 4 and 5 use key names, not codes, and do not have this field")),
    "window": window("the code is in effect"),
    "ato_missions": missions_ref("use the code"),
    "measures": measures_ref("give the areas or lines where the code changes, such as `IFFON` and `IFFOFF` lines"),
}, ("id", "mode"))
define("CodeWord", d.entity("Code word", "one code word and its definition for a time interval"), {
    "id": ident("code word", "the publication"),
    "word": (string(), d.text("code word")),
    "meaning": (string(), d.text("definition of the code word")),
    "window": window("the code word is in effect"),
}, ("id", "word", "meaning"))
define("SpinsIdentification", d.entity("SPINS identification", "the IFF assignments and code words"), {
    "iff": (many("IffAssignment"), d.list_of("IFF assignments")),
    "code_words": (many("CodeWord"), d.list_of("code words")),
})
define("RecoveryAuthentication", d.entity("Recovery authentication", "the authentication values of isolated personnel for one time interval"), {
    "window": window("the values are in effect"),
    "number": (integer(0, 9), d.statement("This field gives the number of the day, from 0 to 9")),
    "letter": (string(pattern=r"^[A-Z]$"), d.statement("This field gives the letter of the day")),
    "word": (string(), d.text("word of the day")),
}, ("window",))
define("SpinsRecovery", d.entity("SPINS personnel recovery", "the CSAR and personnel recovery procedures"), {
    "agency": agency_ref("controls personnel recovery"),
    "rescue_forces": missions_ref("are rescue forces"),
    "channels": channels_ref("are for isolated personnel and rescue forces"),
    "procedures": (refs("procedures"), d.references("procedures of the resource catalogue", "are for isolated personnel and rescue forces")),
    "authentication": (many("RecoveryAuthentication"), d.list_of("authentication values", None, ordered=True)),
    "safe_areas": measures_ref("are safe areas for isolated personnel"),
    "isoprep": (string(), d.statement("This field gives the identifier of the ISOPREP data for recovery forces",
                                      "The publication does not contain data that identifies a person")),
    "remarks": remarks("personnel recovery"),
})
define("AbortCriterion", d.entity("Abort condition", "one condition that stops a mission, and the procedure of the aircrew"), {
    "id": ident("abort condition", "the publication"),
    "condition": (string(), d.text("condition")),
    "action": (choice("abort", "return_to_base", "divert", "hold", "continue_with_approval"), d.enum("procedure of the aircrew")),
}, ("id", "condition", "action"))
define("DivertAirfield", d.entity("Divert airfield", "one airfield for diversion, with its priority"), {
    "airfield": airfield_ref("is the divert airfield"),
    "priority": rank(),
    "conditions": (string(), d.text("conditions for a diversion to the airfield")),
}, ("airfield", "priority"))
define("SpinsDivertAbort", d.entity("SPINS diversion data", "the abort conditions and the divert airfields"), {
    "abort_criteria": (many("AbortCriterion"), d.list_of("abort conditions")),
    "divert_airfields": (many("DivertAirfield"), d.list_of("divert airfields", None, ordered=True)),
    "abort_code": (string(), d.text("abort code")),
})
define("AirspaceNote", d.entity("Airspace note", "one note about control measures for aircrews"), {
    "id": ident("note", "the publication"),
    "measures": (items(measure(), 1, True), d.references("control measures", "the note refers to")),
    "note": (string(), d.text("note")),
}, ("id", "measures", "note"))
CHECK_IN_ITEMS = ("mission_number", "callsign", "aircraft", "position", "altitude", "ordnance", "playtime", "abort_code", "capabilities")
define("CheckInProcedure", d.entity("Agency procedure", "the procedure when aircrews start and stop the communication with one agency"), {
    "id": ident("procedure", "the publication"),
    "agency": agency_ref("receives the first message of the aircrews"),
    "channels": channels_ref("aircrews contact the agency on"),
    "contact_point": point_ref("is the point at which aircrews first contact the agency", ["control"]),
    "procedure": (ref("procedures"), d.reference("procedure of the resource catalogue", "gives the steps")),
    "check_in_items": (items(choice(*CHECK_IN_ITEMS), 0, True), d.list_of("items that aircrews give when they first contact the agency, in order", None, ordered=True)),
    "check_out": (string(), d.text("instructions for the end of the communication")),
}, ("id", "agency"))
define("TankerProcedure", d.entity("Tanker procedure", "the procedure for one refuelling track or anchor"), {
    "id": ident("procedure", "the publication"),
    "track": orbit_ref("is the refuelling track or anchor"),
    "channels": channels_ref("are for the tanker and receivers"),
    "tacan": (common("TACAN"), d.statement("This field gives the channel of the tanker for TACAN")),
    "altitude": (common("AltitudeBlock"), d.altitude_block("the refuelling")),
    "procedure": (ref("procedures"), d.reference("procedure of the resource catalogue", "gives the rendezvous steps")),
    "ato_missions": missions_ref("are tanker missions on the track"),
    "remarks": remarks("the procedure"),
}, ("id", "track"))


# ---- SPINS: air defence, CAS and laser, emergency, recovery, electromagnetic, restrictions, reports, night ----
ID_CRITERIA = ("iff_mode_5", "iff_mode_4", "iff_mode_3a_code", "minimum_risk_route", "safe_passage", "point_of_origin",
               "flight_profile", "visual_identification", "electronic_identification", "controller_declaration",
               "hostile_act", "hostile_intent")
DECLARATIONS = ("friend", "neutral", "bogey", "bandit", "hostile")
RETURN_ROUTE_KINDS = ["MRR", "SC", "TC", "AIRCOR", "SAAFR", "LLTR"]
TASKINGS = ("preplanned_attack", "on_call_cas", "cap", "escort", "refueling", "airborne_control", "reconnaissance", "electromagnetic",
            "transport", "personnel_recovery", "training", "custom", "counterair", "counterland_control")
FLIGHT_PHASES = ("ground", "departure", "en_route", "air_refueling", "target_area", "recovery", "landing")


def measure_kinds_ref(clause, kinds, minimum=0):
    rule = d.enforced("Each measure shall have the type " + " or ".join("`" + kind + "`" for kind in kinds), ROLE_RULE)
    return items(ref("control_measures", **{"x-measure-kinds": list(kinds)}), minimum, True), d.references("control measures", clause, rule)


def flights_ref(clause):
    return refs(ATO_FLIGHTS), d.references("flights of the ATO", clause, "The `orders` field identifies the ATO")


def squawk(clause):
    return string(pattern=r"^[0-7]{4}$"), d.statement("This field gives the Mode 3/A code that " + clause + ", as four octal digits")


define("IdentificationCriterion", d.entity("Identification matrix row", "one row of the identification matrix: a declaration and the conditions that give it"), {
    "id": ident("row", "the publication"),
    "declaration": (choice(*DECLARATIONS), d.enum("declaration that the conditions give")),
    "criteria": (items(choice(*ID_CRITERIA), 1, True), d.list_of("conditions of the declaration")),
    "minimum_criteria": (integer(1), d.count("conditions that are necessary for the declaration")),
    "authority": agency_ref("makes the declaration"),
    "measures": measures_ref("give the area where this row is applicable"),
    "window": window("this row is in effect"),
    "remarks": remarks("this row"),
}, ("id", "declaration", "criteria"))
define("CommitCriterion", d.entity("Commit criterion", "one condition at which fighters fly to intercept a track"), {
    "id": ident("commit criterion", "the publication"),
    "threats": (refs("threats"), d.references("threats of the resource catalogue", "this commit criterion is for")),
    "orbit": orbit_ref("the fighters fly before the commit"),
    "measures": measures_ref("give the area in which a track causes the commit"),
    "commit_range": (common("Length"), d.quantity("distance from the fighters to the track at the commit", "Length")),
    "altitude": (common("AltitudeBlock"), d.altitude_block("the tracks that cause the commit")),
    "declarations": (items(choice("bogey", "bandit", "hostile"), 0, True), d.list_of("declarations that a track has before a commit")),
    "ato_missions": missions_ref("use this commit criterion"),
    "procedure": (ref("procedures"), d.reference("procedure of the resource catalogue", "gives the steps of the commit")),
    "remarks": remarks("this commit criterion"),
}, ("id",), any_of=("commit_range", "measures"))
define("ReturnToForce", d.entity("Return-to-force procedure", "the safe passage of friendly aircraft back through friendly air defence"), {
    "id": ident("procedure", "the publication"),
    "name": name("procedure"),
    "agency": agency_ref("controls the safe passage"),
    "safe_lanes": measure_kinds_ref("are safe lanes through friendly air defence", ["SL"]),
    "routes": measure_kinds_ref("are minimum-risk routes and corridors back to friendly forces", RETURN_ROUTE_KINDS),
    "checkpoints": points_ref("are the identification checkpoints on the route back", ["identification_safety"]),
    "squawk": squawk("aircraft set on the route back"),
    "altitude": (common("AltitudeBlock"), d.altitude_block("the route back")),
    "maximum_speed": (common("Speed"), d.quantity("maximum speed in the safe lanes", "Speed")),
    "channels": channels_ref("aircraft use on the route back"),
    "window": window("the procedure is in effect"),
    "ato_missions": missions_ref("use the procedure"),
    "remarks": remarks("the procedure"),
}, ("id", "name"), any_of=("safe_lanes", "routes"))
define("SpinsAirDefense", d.entity("SPINS air defence", "the air defence procedures for aircrews",
                                   "It uses the weapons control orders and the air defence warnings of Annex D, Appendix 7, of the OPORD"), {
    "weapons_control": (many("WeaponsControl"), d.list_of("weapons control orders")),
    "warnings": (many("AirDefenseWarning"), d.list_of("air defence warnings")),
    "engagement_authorities": agencies_ref("have engagement authority"),
    "identification_matrix": (many("IdentificationCriterion"), d.list_of("rows of the identification matrix")),
    "commit_criteria": (many("CommitCriterion"), d.list_of("commit criteria")),
    "return_to_force": (many("ReturnToForce"), d.list_of("return-to-force procedures")),
    "summary": summary("the air defence procedures"),
})

define("StackBlock", d.entity("Stack level", "one altitude block of a CAS stack and the missions that use it"), {
    "altitude": (common("AltitudeBlock"), d.altitude_block("the level")),
    "use": (choice("working", "holding", "rotary_wing"), d.enum("purpose of the level")),
    "ato_missions": missions_ref("use the level"),
}, ("altitude",))
define("CasStack", d.entity("CAS stack", "one holding stack for CAS aircraft above a point or an orbit"), {
    "id": ident("stack", "the publication"),
    "name": name("stack"),
    "orbit": orbit_ref("is the holding pattern of the stack"),
    "point": point_ref("is the centre of the stack", ["marshalling", "control", "initial"]),
    "agency": agency_ref("assigns the levels of the stack"),
    "levels": (many("StackBlock", 1), d.list_of("levels of the stack, from the top", None, ordered=True)),
    "window": window("the stack is in effect"),
    "remarks": remarks("the stack"),
}, ("id", "name", "levels"), any_of=("orbit", "point"))
define("LaserCodeAllocation", d.entity("Laser code allocation", "one laser code and the units, flights or agencies that use it"), {
    "code": (common("LaserCode"), d.quantity("laser code", "LaserCode")),
    "use": (choice("designation", "marking", "spot_tracking"), d.enum("purpose of the code")),
    "units": units_ref("use the code"),
    "flights": flights_ref("use the code"),
    "agencies": agencies_ref("use the code"),
    "window": window("the allocation is in effect"),
}, ("code",), any_of=("units", "flights", "agencies"))
define("BearingSector", d.entity("Direction sector", "the sector of directions clockwise from the value of `from` to the value of `to`"), {
    "from": (common("Bearing"), d.quantity("first bearing of the sector", "Bearing")),
    "to": (common("Bearing"), d.quantity("second bearing of the sector", "Bearing")),
}, ("from", "to"))
define("LasingRestriction", d.entity("Laser restriction", "one area and time interval in which a laser has limits"), {
    "id": ident("restriction", "the publication"),
    "kind": (choice("no_lasing", "permitted_target_lines", "eye_safe_only"), d.enum("type of the restriction")),
    "measures": measures_ref("give the area of the restriction"),
    "window": window("the restriction is in effect"),
    "target_lines": (many("BearingSector"), d.list_of("sectors of laser target lines that aircrews can use in the area")),
    "minimum_altitude": (common("Altitude"), d.quantity("lowest altitude for a laser from an aircraft", "Altitude")),
    "remarks": remarks("the restriction"),
}, ("id", "kind"))
define("SpinsCas", d.entity("SPINS CAS and laser procedures", "the CAS stacks, the laser code plan and the laser restrictions"), {
    "stacks": (many("CasStack"), d.list_of("CAS stacks")),
    "laser_codes": (many("LaserCodeAllocation"), d.list_of("entries of the laser code plan")),
    "lasing_restrictions": (many("LasingRestriction"), d.list_of("laser restrictions")),
    "remarks": remarks("the CAS and laser procedures"),
})

define("JettisonArea", d.entity("Jettison area", "one area in which aircrews release hung stores and other stores before they land"), {
    "id": ident("area", "the publication"),
    "measure": measure_ref("gives the area"),
    "stores": (items(choice("hung_ordnance", "unexpended_ordnance", "external_tanks", "all_stores"), 1, True), d.list_of("stores that aircrews can release in the area")),
    "altitude": (common("AltitudeBlock"), d.altitude_block("the aircraft when they release stores")),
    "heading": (common("Bearing"), d.quantity("heading of the aircraft when they release stores", "Bearing")),
    "agency": agency_ref("gives clearance to release stores in the area"),
    "channel": channel_ref("aircrews use for the clearance"),
    "window": window("the area is available"),
}, ("id", "measure", "stores"))
define("DamagedAircraftRoute", d.entity("Route for an aircraft with damage", "the route that an aircraft with damage or an emergency flies to an airfield"), {
    "id": ident("route", "the publication"),
    "condition": (choice("battle_damage", "fuel_emergency", "hung_ordnance", "medical"), d.enum("condition for the route")),
    "routes": (refs("routes"), d.references("routes of the resource catalogue", "the aircraft flies")),
    "measures": measure_kinds_ref("the aircraft flies", RETURN_ROUTE_KINDS),
    "airfield": airfield_ref("receives the aircraft"),
    "squawk": squawk("the aircraft sets"),
    "agency": agency_ref("receives the first call of the aircraft"),
    "channel": channel_ref("the aircraft uses"),
}, ("id", "condition", "airfield"), any_of=("routes", "measures"))
define("LostCommunicationStep", d.entity("Lost communication step", "one step of a lost communication procedure"), {
    "action": (choice("squawk", "continue_mission", "proceed", "hold", "climb", "descend", "return_to_base", "land", "rejoin"), d.enum("task of the step")),
    "after_minutes": (integer(0), d.quantity("time from the start of the lost communication to the step", None, "minutes")),
    "squawk": squawk("the aircraft sets"),
    "measure": measure_ref("is the point or the area of the step"),
    "route": (ref("routes"), d.reference("route of the resource catalogue", "the aircraft flies")),
    "altitude": (common("Altitude"), d.quantity("altitude of the step", "Altitude")),
    "airfield": airfield_ref("the aircraft lands at"),
}, ("action",))
define("LostCommunicationProcedure", d.entity("Lost communication procedure", "the steps that aircrews do when they cannot speak to an agency"), {
    "id": ident("procedure", "the publication"),
    "agency": agency_ref("aircrews cannot speak to"),
    "phases": phases_ref("the procedure is applicable to"),
    "ato_missions": missions_ref("use the procedure"),
    "steps": (many("LostCommunicationStep", 1), d.list_of("steps", None, ordered=True)),
}, ("id", "steps"), any_of=("agency", "phases"))
define("SpinsEmergency", d.entity("SPINS emergency procedures", "the jettison areas, the routes for aircraft with damage and the lost communication procedures"), {
    "jettison_areas": (many("JettisonArea"), d.list_of("jettison areas")),
    "damaged_aircraft_routes": (many("DamagedAircraftRoute"), d.list_of("routes for aircraft with damage")),
    "lost_communication": (many("LostCommunicationProcedure"), d.list_of("lost communication procedures")),
    "remarks": remarks("the emergency procedures"),
})

define("RecoveryAirfield", d.entity("Recovery airfield", "one airfield for aircraft that come back, with its entry point and its procedure"), {
    "airfield": airfield_ref("receives the aircraft"),
    "priority": rank(),
    "entry_point": point_ref("is the entry point to the airfield", ["control", "gate", "marshalling"]),
    "route": (ref("routes"), d.reference("route of the resource catalogue", "aircraft fly to the airfield")),
    "procedure": (ref("procedures"), d.reference("procedure of the resource catalogue", "gives the steps of the recovery")),
    "channels": channels_ref("aircraft use for the recovery"),
    "ato_missions": missions_ref("use the airfield"),
}, ("airfield", "priority"))
define("SpinsRecoveryRouting", d.entity("SPINS recovery routes", "the IFF lines, the routes back and the recovery airfields"), {
    "iff_lines": measure_kinds_ref("are lines at which aircraft set the IFF on or off", ["IFFON", "IFFOFF"]),
    "return_routes": measure_kinds_ref("are routes back to friendly airspace", RETURN_ROUTE_KINDS),
    "routes": (refs("routes"), d.references("routes of the resource catalogue", "aircraft fly back to the airfields")),
    "recovery_airfields": (many("RecoveryAirfield"), d.list_of("recovery airfields", None, ordered=True)),
    "remarks": remarks("the recovery routes"),
})

define("SpinsElectromagnetic", d.entity("SPINS emission control and electromagnetic attack", "the emission control periods and the jamming coordination",
                                        "It uses the types of Annex C, Appendix 12, of the OPORD"), {
    "emission_control": (many("EmissionControlPeriod"), d.list_of("emission control periods", None, ordered=True)),
    "jamming_authority": agency_ref("gives approval for electromagnetic attack"),
    "jamming": (many("JammingCoordination"), d.list_of("jamming coordination entries")),
    "remarks": remarks("the emission control and electromagnetic attack procedures"),
})

define("WeatherMinimum", d.entity("Weather minimum", "the lowest ceiling and visibility for one type of tasking or one phase of flight"), {
    "id": ident("minimum", "the publication"),
    "taskings": (items(choice(*TASKINGS), 0, True), d.list_of("types of typed tasking that the minimum is applicable to")),
    "phase": (choice(*FLIGHT_PHASES), d.enum("phase of flight that the minimum is applicable to")),
    "ceiling": (common("Length"), d.quantity("lowest height of the cloud base above the ground", "Length")),
    "visibility": (common("Length"), d.quantity("lowest flight visibility", "Length")),
    "airfield": airfield_ref("the minimum is applicable to"),
    "ato_missions": missions_ref("the minimum is applicable to"),
}, ("id",), any_of=("ceiling", "visibility"))
define("SpinsRestrictions", d.entity("SPINS restrictions", "the sites that aircrews do not attack and the weather minimums"), {
    "protected_sites": (refs(ORDER_PROTECTED_SITES), d.references("protected sites of Annex K of the OPORD", "aircrews do not attack",
                                                                    "The `orders` field identifies the OPORD")),
    "other_protected_sites": (many("ProtectedSite"), d.list_of("protected sites that the OPORD does not give")),
    "weather_minimums": (many("WeatherMinimum"), d.list_of("weather minimums")),
    "remarks": remarks("the restrictions"),
})

define("NvgProcedure", d.entity("NVG procedure", "the procedure for flight with NVG in one area and time interval"), {
    "id": ident("procedure", "the publication"),
    "window": window("the procedure is in effect"),
    "measures": measures_ref("give the area of the procedure"),
    "ato_missions": missions_ref("use the procedure"),
    "minimum_altitude": (common("Altitude"), d.quantity("lowest altitude for flight with NVG", "Altitude")),
    "minimum_illumination": (integer(0, 100), d.quantity("lowest illumination of the moon for flight with NVG", None, "percent")),
    "lighting": (choice("overt", "covert"), d.enum("lighting of the aircraft")),
}, ("id", "window"))
define("LightsOutArea", d.entity("Lights-out area", "one area in which the aircraft lights are off"), {
    "id": ident("area", "the publication"),
    "measures": (items(measure(), 1, True), d.references("control measures", "give the area")),
    "window": window("the area is in effect"),
    "altitude": (common("AltitudeBlock"), d.altitude_block("the area")),
    "ato_missions": missions_ref("fly in the area"),
}, ("id", "measures", "window"))
define("LightingRule", d.entity("Lighting rule", "the condition of the aircraft lights in one phase of flight"), {
    "id": ident("rule", "the publication"),
    "phase": (choice(*FLIGHT_PHASES), d.enum("phase of flight of the rule")),
    "lights": (items(choice("position", "anti_collision", "formation", "landing", "covert_infrared"), 1, True), d.list_of("aircraft lights of the rule")),
    "setting": (choice("on", "off", "dim", "covert"), d.enum("condition of the aircraft lights")),
    "measures": measures_ref("give the area of the rule"),
    "window": window("the rule is in effect"),
}, ("id", "phase", "lights", "setting"))
define("SpinsNight", d.entity("SPINS night procedures", "the NVG procedures, the lights-out areas and the lighting rules"), {
    "nvg": (many("NvgProcedure"), d.list_of("NVG procedures")),
    "lights_out_areas": (many("LightsOutArea"), d.list_of("lights-out areas")),
    "lighting": (many("LightingRule"), d.list_of("lighting rules")),
    "remarks": remarks("the night procedures"),
})
