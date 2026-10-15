"""Descriptions of the per-aircraft, package, communication, fuel, CAS and carrier fields (build/gameplay.py).

Keys follow describe/resolve.py; every value is a describe/templates.py template. The OPORD weather and print
extension descriptions are beside their fields in build/opord/.
"""
from openaix.describe import templates as d
from openaix.describe.tables.ato import role_rule
from openaix.describe.tables.order_fields import timing

SUBJECTS = {"CasBrief": "CAS brief", "Link16": "Link 16 data set", "CrewMember": "crew member", "CommPlan": "communication plan"}

DESCRIPTIONS = {
    # ---- Primitives ------------------------------------------------------------------------------
    ("Pressure", None): d.entity("Pressure", "an atmospheric pressure with its unit: inches of mercury or hectopascals"),
    ("Pressure", "value"): d.statement("This field gives the value of the pressure, in the unit of `unit`"),
    ("Pressure", "unit"): d.enum("unit of the pressure: inches of mercury or hectopascals"),
    ("TargetMark", None): d.entity("Target mark", "the means that marks a target for the aircrew",
                                   "The CAS briefs of the ATO and the OPORD use this one list of values"),
    ("FriendlyMarking", None): d.entity("Friendly marking", "the means that marks the position of the friendly forces for the aircrew"),
    ("BearingRange", None): d.entity("Bearing range", "a range of bearings from a start bearing clockwise to an end bearing"),
    ("BearingRange", "start_bearing"): d.quantity("start of the range of bearings", "Bearing"),
    ("BearingRange", "end_bearing"): d.quantity("end of the range of bearings", "Bearing"),
    ("Hazard", None): d.entity("Hazard", "a danger to the aircraft in the target area that is not a threat"),
    ("Hazard", "kind"): d.enum("type of hazard"),
    ("Hazard", "position"): d.position("the hazard"),
    ("Hazard", "description"): d.text("hazard"),

    # ---- Radio assignments ----------------------------------------------------------------------
    ("RadioAssignment", "activities"): d.references("flight operations", "use this radio assignment",
                                                    d.enforced("Each identifier shall refer to an item of `activities` of the flight",
                                                               "validator:openaix.check.orders.document"),
                                                    "When the list is not given, the assignment is for the complete mission"),
    ("ResourceData", "comm_plans"): d.map_of("communication plans, which are named sets of radio assignments that flights share"),
    ("CommPlan", None): d.entity("Communication plan", "a named set of radio assignments that several flights can use"),
    ("CommPlan", "name"): d.name("communication plan"),
    ("CommPlan", "assignments"): d.list_of("radio assignments of the plan"),
    ("Flight", "comm_plan"): d.reference("communication plan", "gives radio assignments to this flight in addition to `communications`",
                                         "Each identifier refers to the `comm_plans` map of the resource catalogue"),

    # ---- Per-aircraft data ----------------------------------------------------------------------
    ("AircraftOverride", "board_number"): d.text("board number of this aircraft, also called the modex, painted on the airframe"),
    ("AircraftOverride", "crew"): d.list_of("crew members of this aircraft"),
    ("AircraftOverride", "laser_code"): d.quantity("laser code of this aircraft", "LaserCode"),
    ("CrewMember", None): d.entity("Crew member", "one person in the crew of an aircraft"),
    ("CrewMember", "name"): d.text("name of the crew member, as a name or a callsign"),
    ("CrewMember", "role"): d.enum("role of the crew member in the aircraft"),
    ("Identification", "link16"): d.statement("This field gives the Link 16 data set of this flight or aircraft"),
    ("Link16", None): d.entity("Link 16 data set", "the Link 16 station number and the channels of the MIDS terminal of an aircraft"),
    ("Link16", "stn"): d.statement("This field gives the Link 16 station number of the aircraft, as five octal digits"),
    ("Link16", "fighter_channel"): d.statement("This field gives the MIDS channel of the fighter net, from 1 to 127"),
    ("Link16", "mission_channel"): d.statement("This field gives the MIDS channel of the mission net, from 1 to 127"),
    ("Link16", "special_channel"): d.statement("This field gives the MIDS channel of the special net, from 1 to 127"),
    ("Link16", "donors"): d.list_of("station numbers of the donors, which are the stations that send the track data to the aircraft"),
    ("Link16", "team"): d.list_of("station numbers of the team members of the aircraft"),
    ("LinkStation", None): d.entity("Link 16 station number", "a Link 16 STN, which is five octal digits"),

    # ---- Package timing, fuel -------------------------------------------------------------------
    ("Package", "time_on_target"): timing("the time on target of the package"),
    ("Package", "push_time"): timing("the push of the package"),
    ("Package", "push_point"): d.reference("control point", "is the push point of the package", role_rule("push", single=True)),
    ("FuelPlan", "mission_required"): d.statement("This field gives the fuel that the mission requires, as a fuel quantity with its unit"),
    ("FuelPlan", "burn_rate"): d.statement("This field gives the fuel burn rate, as a fuel quantity for each hour with its unit"),
    ("FuelRate", None): d.entity("Fuel rate", "a fuel quantity for each hour, with its unit"),
    ("FuelRate", "value"): d.statement("This field gives the fuel quantity for each hour, in the unit that `unit` gives"),
    ("FuelRate", "unit"): d.enum("unit of the fuel rate: kilograms or pounds for each hour"),
    ("RoutePoint", "number"): d.statement("This field gives the steerpoint number of this route point in the aircraft, from 1"),

    # ---- CAS brief ------------------------------------------------------------------------------
    ("CasBrief", None): d.entity("CAS brief", "the data that the aircrew get for one CAS attack: the 9-line data of JP 3-09.3 and the mission-level data of the ATO",
                                 "The ATO and the OPORD use this one definition", "A field that a use does not need stays out of the record",
                                 "JP 3-09.3 (2014) Chapter V gives the check-in briefing and the CAS brief"),
    ("CasBrief", "id"): d.identifier("CAS brief", "the order", "Other parts of the order use it to refer to this CAS brief"),
    ("CasBrief", "ato_mission"): d.reference("mission of the ATO", "receives the brief", "The `orders` field of the OPORD identifies the ATO"),
    ("CasBrief", "controller"): d.reference("command and control agency", "gives the brief"),
    ("CasBrief", "controllers"): d.list_of("agencies and radio channels that control the CAS for this brief"),
    ("CasBrief", "control_type"): d.enum("type of terminal attack control"),
    ("CasBrief", "method_of_attack"): d.enum("method of attack"),
    ("CasBrief", "check_in"): d.statement("This field gives the check-in data for the controller"),
    ("CasBrief", "contact_points"): d.references("contact points", "the aircraft fly to before the controller gives them a task", role_rule("control")),
    ("CasBrief", "initial_points"): d.references("initial points", "start the attack runs of the aircraft", role_rule("initial")),
    ("CasBrief", "holding"): d.references("orbits, points or zones", "the aircraft use to hold before they get a task"),
    ("CasBrief", "holding_altitude"): d.altitude_block("the holding stack"),
    ("CasBrief", "fire_support_measures"): d.references("fire support coordination measures", "apply to the CAS mission"),
    ("CasBrief", "friendly_lines"): d.references("lines and boundaries", "show the positions of the friendly ground forces"),
    ("CasBrief", "ground_scheme_summary"): d.text("plan of the friendly ground forces, in short form"),
    ("CasBrief", "initial_point"): d.reference("point", "is the initial point of the attack", role_rule("initial", single=True)),
    ("CasBrief", "heading"): d.quantity("heading from the initial point to the target", "Bearing"),
    ("CasBrief", "distance"): d.quantity("distance from the initial point to the target", "Length"),
    ("CasBrief", "offset_direction"): d.enum("side of the line from the initial point to the target on which the aircraft fly the attack"),
    ("CasBrief", "target_elevation"): d.quantity("elevation of the target", "Elevation"),
    ("CasBrief", "target_description"): d.text("target description"),
    ("CasBrief", "target_position"): d.position("the target"),
    ("CasBrief", "target"): d.reference("target of the resource catalogue", "the brief is for"),
    ("CasBrief", "mark"): d.enum("type of mark of the target"),
    ("CasBrief", "marks"): d.list_of("types of target mark", "the controller can supply", "JP 3-09.3 (2014) gives these marks"),
    ("CasBrief", "laser_code"): d.quantity("code of the laser mark", "LaserCode"),
    ("CasBrief", "laser_codes"): d.list_of("laser codes for the controller and the aircraft in this brief"),
    ("CasBrief", "laser_target_line"): d.quantity("laser target line", "Bearing"),
    ("CasBrief", "friendly_direction"): d.enum("direction from the target to the nearest friendly forces"),
    ("CasBrief", "friendly_distance"): d.quantity("distance from the target to the nearest friendly forces", "Length"),
    ("CasBrief", "friendly_marking"): d.enum("means that marks the position of the nearest friendly forces"),
    ("CasBrief", "danger_close"): d.flag("the friendly forces are inside the danger-close distance of the weapons for the attack",
                                         "the friendly forces are outside that distance"),
    ("CasBrief", "egress_point"): d.reference("point", "is the egress point", role_rule("egress", single=True)),
    ("CasBrief", "final_attack_headings"): d.list_of("ranges of final attack headings", "the aircraft can use for the attack",
                                                     "Each range goes clockwise from its start bearing to its end bearing"),
    ("CasBrief", "time_on_target"): d.time("at which the weapons hit the target"),
    ("CasBrief", "time_to_target_seconds"): d.quantity("time from the time of the brief to the time on target", None, "seconds"),
    ("CasBrief", "threats"): d.references("threats of the resource catalogue", "are a danger to the aircraft in the target area"),
    ("CasBrief", "hazards"): d.list_of("hazards in the target area that are not threats"),
    ("CasBrief", "remarks"): d.text("notes for the aircrews that are not in the other fields of this brief"),
    ("Carrier", "link4"): d.statement("This field gives the frequency of the Link 4 data link of the carrier, in megahertz"),
    ("Carrier", "acls"): d.flag("the carrier has an ACLS for the recovery of aircraft",
                                "the carrier has no ACLS"),
    ("Carrier", "recovery_windows"): d.list_of("recovery windows of the carrier", None, ordered=True),
    ("RecoveryWindow", None): d.entity("Recovery window", "a time interval in which the carrier recovers aircraft with one case recovery"),
    ("RecoveryWindow", "window"): d.window("the carrier recovers aircraft"),
    ("RecoveryWindow", "case"): d.enum("case recovery in the window"),
    ("RecoveryWindow", "brc"): d.quantity("base recovery course, which is the heading of the carrier during the recovery", "Bearing"),
}

ENUMS = {
    ("TargetMark", None): d.values({
        "laser": "a mark from a laser designator, which the seeker of the weapon or the targeting pod of the aircraft detects",
        "infrared_pointer": "a mark from an infrared pointer. Aircrew with night vision devices can see it on the target",
        "smoke": "a mark from smoke ammunition at or near the target",
        "white_phosphorus": "a mark from white phosphorus ammunition at or near the target",
        "illumination": "a mark from illumination ammunition above or near the target",
        "indirect_fire": "a mark from artillery, mortar or naval gun fire",
        "tracer": "a mark from tracer rounds, which show the line of fire to the target",
        "talk_on": "a talk-on, in which the controller tells the aircrew how to find the target by voice",
    }),
    ("FriendlyMarking", None): d.values({
        "panel": "a panel with a bright colour on the ground", "smoke": "coloured smoke from a grenade or a canister at the friendly position",
        "mirror": "a mirror that reflects the light of the sun", "strobe": "a visible strobe light that flashes at the friendly position",
        "infrared_strobe": "an infrared strobe light that aircrew with night vision devices can see",
        "chemical_light": "a chemical light stick that gives light for a short time, usually at night", "flare": "a pyrotechnic flare that burns bright at the friendly position",
    }),
    ("Hazard", "kind"): d.values({
        "obstruction": "an obstruction, such as a tower or a mast", "wires": "wires or cables in the air",
        "terrain": "high ground in or near the attack run", "friendly_aircraft": "other friendly aircraft in the target area",
        "indirect_fire": "friendly artillery, mortar or naval gun fire in the target area",
        "weather": "a dangerous weather condition in the target area",
        "other": "a hazard that the other values do not include",
    }),
    ("CrewMember", "role"): d.values({
        "pilot": "the crew member who has command and flies the aircraft", "copilot": "the second pilot, who helps the pilot in the front or the side seat",
        "weapon_systems_officer": "a crew member who runs the weapons and the sensors from a rear seat",
        "radar_intercept_officer": "a crew member who runs the radar and the intercept from a rear seat",
        "gunner": "the crew member who aims and fires the guns and the missiles of a helicopter", "other": "a crew member that the other values do not include",
    }),
    ("Pressure", "unit"): d.values({
        "inHg": d.value_sentence("The pressure is in inches of mercury."),
        "hPa": d.value_sentence("The pressure is in hectopascals."),
    }),
    ("FuelRate", "unit"): d.values({
        "kg/h": d.value_sentence("The fuel quantity is in kilograms for each hour."),
        "lb/h": d.value_sentence("The fuel quantity is in pounds for each hour. One pound is 0.45359237 kilograms."),
    }),
    ("CasBrief", "offset_direction"): d.values({
        "left": d.value_sentence("The aircraft fly the attack to the left of the line from the initial point to the target."),
        "right": d.value_sentence("The aircraft fly the attack to the right of the line from the initial point to the target."),
    }),
    ("CasBrief", "control_type"): d.values({
        "type_1": "type 1 terminal attack control, in which the controller sees the target and the aircraft",
        "type_2": "type 2 terminal attack control, in which the controller does not see the target or the aircraft",
        "type_3": "type 3 terminal attack control, in which the controller gives clearance for all attacks in an area",
    }),
}
