"""OPORD annexes A to Z (formats in FM 5-0, Appendix E; letters in FM 6-0). Letters I, O, T, X and Y have no
annex; FM 6-0 puts air and missile defence in Annex D (Fires)."""
from openaix.build.opord.schema import (agencies_ref, agency_ref, airfield_ref, AIRSPACE_CATEGORIES, ANNEXES,
                                        ATO_MISSIONS, boolean, channel_ref, channels_ref, choice, common, define,
                                        DIRECTIONS, EFFECTS, ident, integer, local, many, measure_ref, measures_ref,
                                        missions_ref, name, number, ORDER_ENEMY_UNITS, ORDER_ORGANIZATIONS,
                                        ORDER_REQUIREMENTS, phase_ref, point_ref, points_ref, position, rank, ref,
                                        refs, RELATIONSHIPS, remarks, RISK_LEVELS, string, summary, SUPPLY_CLASSES,
                                        texts, unit_ref, units_ref, when, window)
from openaix.describe import templates as d


# ---- Annexes ------------------------------------------------------------------------------------------
def annex(letter, fields, notes=()):
    name_, title = ANNEXES[letter]
    return define(name_, d.entity("Annex for " + title.lower().replace("host-nation", "host-nation"), "the annex with the letter `" + letter + "` in the order", *notes), {
        **fields, "summary": summary("Annex " + letter), "remarks": remarks("Annex " + letter)})


define("CommandRelationship", d.entity("Command relationship", "the command or support relationship of one unit"), {
    "unit": unit_ref("the entry is for"),
    "relationship": (choice(*RELATIONSHIPS), d.enum("command relationship or support relationship")),
    "to": unit_ref("is the other unit of the entry"),
    "headquarters": (string(), d.text("name of the other headquarters of the entry, when it is not in the task organization")),
    "phase": phase_ref("the entry is applicable to"),
    "effective": when("the start of the entry"),
}, ("unit", "relationship"), any_of=("to", "headquarters"))
annex("A", {"relationships": (many("CommandRelationship"), d.list_of("command and support relationships"))})

define("ThreatAssessment", d.entity("Threat assessment", "the assessment of one threat of the resource catalogue"), {
    "threat": (ref("threats"), d.reference("threat of the resource catalogue", "the assessment refers to")),
    "emitters": (refs("emitters"), d.references("emitters of the resource catalogue", "the assessment refers to",
                                                "Each emitter gives the position and the engagement ring")),
    "enemy_unit": (ref(ORDER_ENEMY_UNITS), d.reference("enemy unit of paragraph 1", "has the threat")),
    "capability": (string(), d.text("capability of the threat")),
    "position": position("the threat at the time of the assessment"),
    "as_of": when("the assessment"),
    "confidence": (choice("low", "moderate", "high"), d.enum("confidence level of the assessment")),
}, ("threat",))
define("HighValueTarget", d.entity("High-value target", "one target that is necessary for the mission of the enemy commander"), {
    "id": ident("target", "the order"),
    "name": name("target"),
    "function": (choice("command_and_control", "fires", "air_defense", "maneuver", "reconnaissance", "sustainment", "engineer",
                        "electronic_warfare", "aviation"), d.enum("enemy function of the target")),
    "target": (ref("targets"), d.reference("target of the resource catalogue", "this entry is for")),
    "threat": (ref("threats"), d.reference("threat of the resource catalogue", "this entry is for")),
}, ("id", "name", "function"))
define("IntelligenceProduct", d.entity("Intelligence product", "one intelligence product and its distribution"), {
    "id": ident("intelligence product", "the order"),
    "name": name("intelligence product"),
    "recipients": units_ref("receive the intelligence product"),
    "agencies": agencies_ref("receive the intelligence product"),
    "due": when("the first issue of the intelligence product"),
    "interval_minutes": (integer(1), d.quantity("time between two issues of the intelligence product", None, "minutes")),
    "channel": channel_ref("sends the intelligence product"),
}, ("id", "name"))
annex("B", {
    "threat_assessments": (many("ThreatAssessment"), d.list_of("threat assessments")),
    "high_value_targets": (many("HighValueTarget"), d.list_of("high-value targets")),
    "products": (many("IntelligenceProduct"), d.list_of("intelligence products")),
})

define("DecisionPoint", d.entity("Decision point", "one possible decision of the commander, with its time, area and information"), {
    "id": ident("decision point", "the order"),
    "name": name("decision point"),
    "decision": (string(), d.text("decision")),
    "trigger": (string(), d.text("event or condition that starts the decision")),
    "position": position("the decision point"),
    "measures": measures_ref("the decision refers to, such as named areas of interest"),
    "requirements": (refs(ORDER_REQUIREMENTS), d.references("information requirements", "support the decision")),
    "phase": phase_ref("the decision is in"),
    "latest_time": when("the last time at which the commander makes the decision"),
}, ("id", "name", "decision"))
define("AirspaceAppendix", d.entity("Airspace appendix", "`Appendix 10 (Airspace)` of Annex C"), {
    "airspace_control_agency": agency_ref("controls the airspace"),
    "coordinating_altitude": measure_ref("gives the coordinating altitude", ["acm"]),
    "measures": measures_ref("are airspace coordinating measures", AIRSPACE_CATEGORIES),
    "agencies": agencies_ref("control parts of the airspace"),
    "summary": summary("the airspace plan"),
})
define("RecoveryAppendix", d.entity("Appendix for personnel recovery", "`Appendix 16 (Personnel Recovery)` of Annex C"), {
    "recovery_forces": missions_ref("are recovery forces"),
    "agency": agency_ref("coordinates personnel recovery"),
    "channels": channels_ref("are for isolated personnel and recovery forces"),
    "safe_areas": measures_ref("are safe areas for isolated personnel"),
    "contact_points": points_ref("are contact points for recovery forces", ["control"]),
    "summary": summary("the personnel recovery plan"),
})
define("EmissionControlPeriod", d.entity("Emission control period", "one emission control level for a time interval"), {
    "id": ident("period", "the order"),
    "level": (choice("unrestricted", "reduced", "minimum", "silent"), d.enum("emission control level")),
    "window": window("the level is in effect"),
    "units": units_ref("the level is applicable to"),
    "measures": measures_ref("give the area of the level"),
    "ato_missions": missions_ref("the level is applicable to"),
}, ("id", "level", "window"))
define("JammingCoordination", d.entity("Jamming coordination", "one time interval of electromagnetic attack, with its emitters and the frequencies that it keeps clear"), {
    "id": ident("entry", "the order"),
    "window": window("the jamming occurs"),
    "emitters": (refs("emitters"), d.references("emitters of the resource catalogue", "are the objects of the jamming")),
    "ato_missions": missions_ref("do the jamming"),
    "area": (ref("areas"), d.reference("area of the resource catalogue", "the jamming aircraft operate in")),
    "protected_frequencies": (many("RestrictedFrequency"), d.list_of("frequencies that the jamming does not have an effect on")),
    "authority": agency_ref("gives approval for the jamming"),
}, ("id", "window"))
define("ElectromagneticAppendix", d.entity("Appendix for cyberspace electromagnetic activities", "`Appendix 12` of Annex C"), {
    "emission_control": (many("EmissionControlPeriod"), d.list_of("emission control periods", None, ordered=True)),
    "jamming_authority": agency_ref("gives approval for electromagnetic attack"),
    "jamming": (many("JammingCoordination"), d.list_of("jamming coordination entries")),
    "summary": summary("the cyberspace electromagnetic activities"),
})
annex("C", {
    "operation_overlay": measures_ref("are on the operation overlay"),
    "decision_points": (many("DecisionPoint"), d.list_of("decision points of the decision support products")),
    "airspace": (local("AirspaceAppendix"), d.statement("This field gives `Appendix 10 (Airspace)`")),
    "rules_of_engagement": (many("RoeRule"), d.list_of("rules of `Appendix 11 (Rules of Engagement)`")),
    "electromagnetic": (local("ElectromagneticAppendix"), d.statement("This field gives `Appendix 12 (Cyberspace Electromagnetic Activities)`")),
    "personnel_recovery": (local("RecoveryAppendix"), d.statement("This field gives `Appendix 16 (Personnel Recovery)`")),
})

define("HighPayoffTarget", d.entity("High-payoff target", "one entry of the attack guidance: the target, the time and method of attack, and the effect"), {
    "id": ident("entry", "the order"),
    "priority": rank(),
    "target": (ref("targets"), d.reference("target of the resource catalogue", "this entry is for")),
    "threat": (ref("threats"), d.reference("threat of the resource catalogue", "this entry is for")),
    "emitter": (ref("emitters"), d.reference("emitter of the resource catalogue", "this entry is for")),
    "timing": (choice("immediate", "planned", "as_acquired"), d.enum("time of attack")),
    "units": units_ref("attack the target"),
    "ato_missions": missions_ref("attack the target"),
    "effect": (choice(*EFFECTS), d.enum("effect on the target")),
    "assessment_required": (boolean(), d.flag("units send a BDA report after the attack")),
    "phase": phase_ref("the entry is applicable to"),
}, ("id", "priority", "effect"), any_of=("target", "threat", "emitter"))
define("TimeSensitiveTarget", d.entity("Time-sensitive target", "one TST of the order"), {
    "id": ident("entry", "the order"),
    "tst_number": (string(), d.text("number of the TST, such as `TST-01`")),
    "target": (ref("targets"), d.reference("target of the resource catalogue", "this TST is for")),
    "priority": rank(),
    "window": window("the target is possibly active"),
    "engagement_authority": agency_ref("gives approval for the engagement"),
    "ato_missions": missions_ref("can attack the target"),
}, ("id", "tst_number", "target"))
define("TargetingAppendix", d.entity("Appendix for targets", "`Appendix 3 (Targeting)` of Annex D"), {
    "high_payoff_targets": (many("HighPayoffTarget"), d.list_of("attack guidance entries", None, ordered=True)),
    "time_sensitive_targets": (many("TimeSensitiveTarget"), d.list_of("TST entries")),
    "target_reference_points": measures_ref("are target reference points"),
})
define("CasAllocation", d.entity("CAS allocation", "the CAS for one supported unit"), {
    "unit": unit_ref("receives the CAS"),
    "sorties": (integer(0), d.count("CAS sorties")),
    "window": window("the CAS is available"),
    "ato_missions": missions_ref("give the CAS"),
    "phase": phase_ref("the allocation is applicable to"),
}, ("unit",))
define("CasBrief", d.entity("CAS brief", "one 9-line CAS brief of JP 3-09.3"), {
    "id": ident("brief", "the order"),
    "ato_mission": (ref(ATO_MISSIONS), d.reference("mission of the ATO", "receives the brief", "The `orders` field identifies the ATO")),
    "controller": agency_ref("gives the brief"),
    "control_type": (choice("type_1", "type_2", "type_3"), d.enum("type of terminal attack control")),
    "method_of_attack": (choice("bomb_on_target", "bomb_on_coordinate"), d.enum("method of attack")),
    "initial_point": point_ref("is the initial point", ["initial"]),
    "heading": (common("Bearing"), d.quantity("heading from the initial point to the target", "Bearing")),
    "distance": (common("Length"), d.quantity("distance from the initial point to the target", "Length")),
    "target_elevation": (common("Elevation"), d.quantity("elevation of the target", "Elevation")),
    "target_description": (string(), d.text("target description")),
    "target_position": position("the target"),
    "target": (ref("targets"), d.reference("target of the resource catalogue", "the brief is for")),
    "mark": (choice("none", "laser", "infrared", "white_phosphorus", "smoke", "illumination"), d.enum("type of mark")),
    "laser_code": (common("LaserCode"), d.quantity("code of the laser mark", "LaserCode")),
    "laser_target_line": (common("Bearing"), d.quantity("laser target line", "Bearing")),
    "friendly_direction": (choice(*DIRECTIONS), d.enum("direction from the target to the nearest friendly forces")),
    "friendly_distance": (common("Length"), d.quantity("distance from the target to the nearest friendly forces", "Length")),
    "egress_point": point_ref("is the egress point", ["egress"]),
    "time_on_target": when("the TOT"),
    "remarks": remarks("the brief"),
}, ("id", "target_position", "target_description"))
define("AirSupportAppendix", d.entity("Air support appendix", "`Appendix 5 (Air Support)` of Annex D"), {
    "cas_allocations": (many("CasAllocation"), d.list_of("CAS allocations")),
    "cas_briefs": (many("CasBrief"), d.list_of("CAS briefs that the staff writes before the mission")),
    "agencies": agencies_ref("control air support"),
    "points": points_ref("are contact points, initial points and holding points for air support", ["control", "initial", "marshalling"]),
    "ato_missions": missions_ref("give air interdiction and air reconnaissance"),
})
define("FieldArtilleryAppendix", d.entity("Field artillery appendix", "`Appendix 4 (Field Artillery Support)` of Annex D"), {
    "units": units_ref("give field artillery support"),
    "position_areas": measures_ref("are position areas of the field artillery"),
    "priorities": (many("Priority"), d.list_of("priorities of field artillery fires")),
})
define("NavalFireAppendix", d.entity("Appendix for naval fire support", "`Appendix 6 (Naval Fire Support)` of Annex D"), {
    "units": units_ref("give naval fire support"),
    "fire_support_areas": measures_ref("are fire support areas and fire support stations"),
})
define("WeaponsControl", d.entity("Weapons control order", "one weapons control status for an area and a time interval"), {
    "status": (choice("free", "tight", "hold"), d.enum("weapons control status")),
    "measure": measure_ref("gives the area of the weapons control status"),
    "window": window("the weapons control status is in effect"),
}, ("status",))
define("AirDefenseWarning", d.entity("Air defence warning", "one air defence warning for an area and a time interval"), {
    "level": (choice("white", "yellow", "red"), d.enum("air defence warning")),
    "measure": measure_ref("gives the area of the air defence warning"),
    "window": window("the air defence warning is in effect"),
}, ("level",))
define("DefendedAsset", d.entity("Defended asset", "one asset that air defence gives protection to, with its priority"), {
    "id": ident("asset", "the order"),
    "name": name("asset"),
    "priority": rank(),
    "position": position("the asset"),
    "airfield": airfield_ref("is the asset"),
    "unit": unit_ref("is the asset"),
}, ("id", "name", "priority"))
define("AirDefenseAppendix", d.entity("Appendix for air and missile defence", "`Appendix 7 (Air and Missile Defense)` of Annex D",
                                      "FM 6-0 (2022) puts these data in Annex D", "FM 5-0 (2024) puts them in a different annex, Annex I, which openAIX does not use"), {
    "weapons_control": (many("WeaponsControl"), d.list_of("weapons control orders")),
    "warnings": (many("AirDefenseWarning"), d.list_of("air defence warnings")),
    "defended_assets": (many("DefendedAsset"), d.list_of("defended assets", None, ordered=True)),
    "engagement_authorities": agencies_ref("have engagement authority"),
    "measures": measures_ref("are air defence measures", ["adm"]),
})
annex("D", {
    "fire_support_coordination_measures": measures_ref("are FSCM entries", ["fscm"]),
    "priority_of_fires": (many("Priority"), d.list_of("priorities of fires")),
    "targeting": (local("TargetingAppendix"), d.statement("This field gives `Appendix 3 (Targeting)`")),
    "field_artillery": (local("FieldArtilleryAppendix"), d.statement("This field gives `Appendix 4 (Field Artillery Support)`")),
    "air_support": (local("AirSupportAppendix"), d.statement("This field gives `Appendix 5 (Air Support)`")),
    "naval_fire_support": (local("NavalFireAppendix"), d.statement("This field gives `Appendix 6 (Naval Fire Support)`")),
    "air_and_missile_defense": (local("AirDefenseAppendix"), d.statement("This field gives `Appendix 7 (Air and Missile Defense)`")),
}, (d.enforced("Each reference in `fire_support_coordination_measures` shall identify a measure of the FSCM class", "validator:openaix.check.validate.references"),))

define("ProtectedAsset", d.entity("Protection priority", "one asset of the list of protection priorities"), {
    "id": ident("asset", "the order"),
    "priority": rank(),
    "name": name("asset"),
    "unit": unit_ref("is the asset"),
    "position": position("the asset"),
    "measure": measure_ref("gives the area of the asset"),
    "airfield": airfield_ref("is the asset"),
}, ("id", "priority", "name"))
define("RiskControl", d.entity("Risk control", "one hazard and its control"), {
    "id": ident("control", "the order"),
    "hazard": (string(), d.text("hazard")),
    "control": (string(), d.text("control of the hazard")),
    "initial_risk": (choice(*RISK_LEVELS), d.enum("risk level before the control")),
    "residual_risk": (choice(*RISK_LEVELS), d.enum("risk level after the control")),
    "units": units_ref("apply the control"),
}, ("id", "hazard", "control"))
define("ReactionForce", d.entity("Reaction force", "one reaction force with its area and its time of movement"), {
    "unit": unit_ref("is the reaction force"),
    "area": measure_ref("gives the area of the reaction force"),
    "response_minutes": (integer(0), d.quantity("time from the alert to the movement of the reaction force", None, "minutes")),
}, ("unit",))
annex("E", {
    "protection_priorities": (many("ProtectedAsset"), d.list_of("protection priorities", None, ordered=True)),
    "risk_controls": (many("RiskControl"), d.list_of("risk controls")),
    "reaction_forces": (many("ReactionForce"), d.list_of("reaction forces")),
    "eefi": (many("EEFI"), d.list_of("essential elements of friendly information for operations security")),
    "mopp_level": (choice("mopp_ready", "mopp_0", "mopp_1", "mopp_2", "mopp_3", "mopp_4"), d.enum("protective posture against CBRN hazards")),
})

define("SupplyAllocation", d.entity("Supply allocation", "one allocation of a class of supply to a unit"), {
    "unit": unit_ref("receives the allocation"),
    "supply_class": (choice(*SUPPLY_CLASSES), d.enum("class of supply")),
    "item": (string(), d.text("item of supply, such as `JP-8` or `GBU-12`")),
    "quantity": (number(0), d.statement("This field gives the quantity, in the unit of `unit_of_measure`")),
    "unit_of_measure": (choice("gal", "l", "lb", "kg", "rounds", "each", "pallets"), d.enum("unit of the quantity")),
}, ("unit", "supply_class", "quantity", "unit_of_measure"))
define("Movement", d.entity("Movement", "one movement of a unit on a route"), {
    "id": ident("movement", "the order"),
    "unit": unit_ref("moves"),
    "route": (ref("routes"), d.reference("route of the resource catalogue", "the unit follows")),
    "start_point": measure_ref("is the start point"),
    "release_point": measure_ref("is the release point"),
    "departure": when("departure from the start point"),
    "arrival": when("arrival at the release point"),
}, ("id", "unit"))
annex("F", {
    "supply_points": (many("SupplyPoint"), d.list_of("supply points")),
    "allocations": (many("SupplyAllocation"), d.list_of("supply allocations")),
    "movements": (many("Movement"), d.list_of("movements")),
    "maintenance_priorities": (many("Priority"), d.list_of("priorities of maintenance")),
    "medical_facilities": (many("MedicalFacility"), d.list_of("medical treatment facilities")),
    "medical_evacuation": (local("MedicalEvacuation"), d.statement("This field gives the medical evacuation plan")),
})

define("Obstacle", d.entity("Obstacle", "one obstacle, with its effect and its unit"), {
    "id": ident("obstacle", "the order"),
    "name": name("obstacle"),
    "kind": (choice("minefield", "wire", "ditch", "crater", "abatis", "roadblock", "rubble", "other"), d.enum("type of the obstacle")),
    "effect": (choice("block", "fix", "turn", "disrupt"), d.enum("effect of the obstacle")),
    "position": position("the obstacle"),
    "measure": measure_ref("gives the area of the obstacle"),
    "unit": unit_ref("controls the obstacle"),
    "complete_by": when("the end of the work on the obstacle"),
    "status": (choice("planned", "prepared", "executed", "cleared"), d.enum("condition of the obstacle")),
}, ("id", "name", "kind"), any_of=("position", "measure"))
define("Lane", d.entity("Lane", "one lane through an obstacle"), {
    "id": ident("lane", "the order"),
    "name": name("lane"),
    "entry": position("the entry of the lane"),
    "exit": position("the exit of the lane"),
    "width": (common("Length"), d.quantity("width of the lane", "Length")),
    "marking": (string(), d.text("marking of the lane")),
    "unit": unit_ref("opens the lane"),
}, ("id", "name", "entry", "exit"))
annex("G", {
    "obstacles": (many("Obstacle"), d.list_of("obstacles")),
    "lanes": (many("Lane"), d.list_of("lanes")),
    "obstacle_zones": measures_ref("are obstacle control areas"),
    "survivability_priorities": (many("Priority"), d.list_of("priorities of survivability work")),
})

define("Net", d.entity("Radio net", "one radio net, its channels and its members"), {
    "id": ident("net", "the order"),
    "name": name("net"),
    "kind": (choice("command", "operations_and_intelligence", "fires", "administrative_and_logistics", "air_ground", "data_link", "other"),
             d.enum("type of the net")),
    "primary": channel_ref("is the primary channel of the net"),
    "alternate": channel_ref("is the alternate channel of the net"),
    "control": agency_ref("controls the net"),
    "members": units_ref("are members of the net"),
    "agencies": agencies_ref("are members of the net"),
}, ("id", "name", "primary"))
define("CallSign", d.entity("Call sign", "one call sign of a unit or an agency for a time interval"), {
    "unit": unit_ref("uses the call sign"),
    "agency": agency_ref("uses the call sign"),
    "callsign": (string(), d.text("call sign")),
    "window": window("the call sign is in effect"),
}, ("callsign",), any_of=("unit", "agency"))
define("RetransmissionSite", d.entity("Retransmission site", "one site that sends radio signals again to extend the range"), {
    "id": ident("site", "the order"),
    "name": name("site"),
    "position": position("the site"),
    "channels": channels_ref("the retransmission site sends again"),
    "unit": unit_ref("operates the site"),
    "window": window("the site operates"),
}, ("id", "name", "position"))
define("RestrictedFrequency", d.entity("Restricted frequency", "one entry of the restricted frequency list"), {
    "channel": channel_ref("the restriction is for"),
    "frequency": (common("Frequency"), d.quantity("frequency of the restriction, when no channel identifies it", "Frequency")),
    "kind": (choice("taboo", "protected", "guarded"), d.enum("type of the restriction")),
    "agency": agency_ref("controls the frequency"),
}, ("kind",), any_of=("channel", "frequency"))
define("KeyPeriod", d.entity("COMSEC key period", "one period of COMSEC key material"), {
    "id": ident("key period", "the order"),
    "key": (string(), d.text("name of the key, as the exercise key list gives it")),
    "window": window("the key is in effect"),
    "channels": channels_ref("use the key"),
}, ("id", "key", "window"))
annex("H", {
    "nets": (many("Net"), d.list_of("radio nets")),
    "call_signs": (many("CallSign"), d.list_of("call signs")),
    "retransmission_sites": (many("RetransmissionSite"), d.list_of("retransmission sites")),
    "restricted_frequencies": (many("RestrictedFrequency"), d.list_of("restricted frequencies")),
    "comsec": (many("KeyPeriod"), d.list_of("COMSEC key periods", None, ordered=True)),
})

define("Objective", d.entity("Objective", "one objective with an identifier"), {
    "id": ident("objective", "its list"),
    "objective": (string(), d.text("objective")),
}, ("id", "objective"))
define("ReleaseAuthority", d.entity("Release authority", "the authority that releases information of one type"), {
    "topic": (string(), d.text("type of information")),
    "unit": unit_ref("releases the information"),
    "agency": agency_ref("releases the information"),
}, ("topic",), any_of=("unit", "agency"))
annex("J", {
    "objectives": (many("Objective"), d.list_of("public affairs objectives")),
    "messages": (many("Message"), d.list_of("themes and messages")),
    "release_authorities": (many("ReleaseAuthority"), d.list_of("release authorities")),
    "ground_rules": (many("Objective"), d.list_of("media ground rules")),
})

define("ProtectedSite", d.entity("Protected site", "one site that the operation keeps safe from attack"), {
    "id": ident("site", "the order"),
    "name": name("site"),
    "kind": (choice("cultural", "religious", "medical", "school", "infrastructure", "humanitarian", "other"), d.enum("type of the site")),
    "restriction": (choice("no_strike", "restricted_target"), d.enum("restriction on attacks against the site")),
    "position": position("the site"),
    "measure": measure_ref("gives the area of the site"),
}, ("id", "name", "kind", "restriction"), any_of=("position", "measure"))
define("CivilMilitaryCentre", d.entity("Civil-military operations centre", "one centre for coordination with organizations of the population"), {
    "id": ident("centre", "the order"),
    "name": name("centre"),
    "position": position("the centre"),
    "unit": unit_ref("operates the centre"),
    "channel": channel_ref("the centre refers to"),
}, ("id", "name"))
annex("K", {
    "protected_sites": (many("ProtectedSite"), d.list_of("protected sites")),
    "dislocated_civilian_routes": (refs("routes"), d.references("routes of the resource catalogue for dislocated civilians")),
    "tasks": (many("Task"), d.list_of("tasks of the execution matrix")),
    "centres": (many("CivilMilitaryCentre"), d.list_of("civil-military operations centres")),
})

define("CollectionTask", d.entity("Collection task", "one row of the information collection plan"), {
    "id": ident("task", "the order"),
    "requirement": (ref(ORDER_REQUIREMENTS), d.reference("information requirement", "the task gives data for")),
    "indicator": (string(), d.text("indicator that the task looks for")),
    "measure": measure_ref("is the named area of interest of the task"),
    "unit": unit_ref("does the task"),
    "ato_mission": (ref(ATO_MISSIONS), d.reference("mission of the ATO", "does the task", "The `orders` field identifies the ATO")),
    "window": window("the task is in effect"),
    "report_to": agency_ref("receives the reports"),
    "report": (ref("reports"), d.reference("report of the resource catalogue", "gives the results of the task")),
}, ("id",), any_of=("unit", "ato_mission"))
annex("L", {
    "named_areas_of_interest": measures_ref("give the named areas of interest"),
    "collection_tasks": (many("CollectionTask"), d.list_of("collection tasks")),
    "handover_lines": measures_ref("are intelligence handover lines"),
})

define("Indicator", d.entity("Indicator", "one indicator of an assessment measure, with its threshold"), {
    "id": ident("indicator", "its measure"),
    "indicator": (string(), d.text("indicator")),
    "threshold": (string(), d.text("value of the indicator that shows that the operation is on plan")),
}, ("id", "indicator"))
define("EffectivenessMeasure", d.entity("Measure of effectiveness", "one MOE, with its indicators"), {
    "id": ident("measure", "the order"),
    "statement": (string(), d.text("measure")),
    "indicators": (many("Indicator"), d.list_of("indicators")),
}, ("id", "statement"))
define("PerformanceMeasure", d.entity("Measure of performance", "one MOP for a task"), {
    "id": ident("measure", "the order"),
    "task": (string(), d.text("task that the measure is for")),
    "indicator": (string(), d.text("indicator of performance")),
    "units": units_ref("the measure is applicable to"),
}, ("id", "task", "indicator"))
annex("M", {
    "measures_of_effectiveness": (many("EffectivenessMeasure"), d.list_of("MOE entries")),
    "measures_of_performance": (many("PerformanceMeasure"), d.list_of("MOP entries")),
    "reframing_criteria": (many("Objective"), d.list_of("conditions that cause the staff to change the plan")),
})

define("SpaceCapability", d.entity("Space capability", "one space capability that the operation uses"), {
    "id": ident("capability", "the order"),
    "mission_area": (choice("positioning_navigation_timing", "satellite_communications", "missile_warning", "intelligence_surveillance_reconnaissance",
                            "environmental_monitoring", "space_control"), d.enum("space mission area")),
    "provider": (string(), d.text("name of the provider of the capability")),
    "window": window("the capability is available"),
    "units": units_ref("use the capability"),
}, ("id", "mission_area"))
define("NavigationOutage", d.entity("Navigation outage", "one time interval in which satellite navigation has a large position error"), {
    "id": ident("navigation outage", "the order"),
    "window": window("satellite navigation has a large position error"),
    "measure": measure_ref("gives the area of the navigation outage"),
    "expected_error": (common("Length"), d.quantity("possible position error", "Length")),
}, ("id", "window"))
annex("N", {
    "capabilities": (many("SpaceCapability"), d.list_of("space capabilities")),
    "navigation_outages": (many("NavigationOutage"), d.list_of("navigation outages")),
    "satellite_channels": channels_ref("are satellite channels"),
})

HNS_CATEGORIES = ("accommodations", "ammunition", "communications", "finance", "fuel", "labor", "maintenance", "medical", "movement",
                  "rations", "supplies", "translation", "transportation", "water")
define("Agreement", d.entity("Agreement", "one agreement with the host nation"), {
    "id": ident("agreement", "the order"),
    "name": name("agreement"),
    "kind": (choice("status_of_forces", "acquisition_cross_servicing", "technical", "other"), d.enum("type of the agreement")),
    "parties": (texts(), d.list_of("organizations that sign the agreement")),
    "effective": window("the agreement is in effect"),
}, ("id", "name", "kind"))
define("HostNationSupport", d.entity("Host-nation support item", "one type of support that the host nation gives"), {
    "id": ident("item", "the order"),
    "category": (choice(*HNS_CATEGORIES), d.enum("class of the support")),
    "provider": (string(), d.text("name of the provider")),
    "agreement": (common("Identifier"), d.statement("This field gives the identifier of the agreement for the support, from `agreements`")),
    "airfield": airfield_ref("receives the support"),
    "position": position("the support"),
}, ("id", "category"))
annex("P", {
    "agreements": (many("Agreement"), d.list_of("agreements")),
    "support": (many("HostNationSupport"), d.list_of("host-nation support items")),
})

define("BattleRhythmEvent", d.entity("Battle rhythm event", "one meeting, board, report or update in the battle rhythm"), {
    "id": ident("event", "the order"),
    "name": name("event"),
    "kind": (choice("meeting", "board", "working_group", "update", "report", "briefing"), d.enum("type of the event")),
    "start": when("the first event"),
    "interval_minutes": (integer(1), d.quantity("time between two events", None, "minutes")),
    "duration_minutes": (integer(1), d.quantity("length of the event", None, "minutes")),
    "chair": unit_ref("controls the event"),
    "attendees": units_ref("are at the event"),
    "channel": channel_ref("the event refers to"),
}, ("id", "name", "kind", "start"))
define("InformationSystem", d.entity("Information system", "one information system for command and control"), {
    "id": ident("system", "the order"),
    "name": name("system"),
    "purpose": (string(), d.text("purpose of the system")),
    "channels": channels_ref("the system refers to"),
    "units": units_ref("use the system"),
}, ("id", "name"))
annex("Q", {
    "battle_rhythm": (many("BattleRhythmEvent"), d.list_of("battle rhythm events")),
    "information_systems": (many("InformationSystem"), d.list_of("information systems")),
})

define("ReportRequirement", d.entity("Report requirement", "one report that units send, with its time and recipient"), {
    "report": (ref("reports"), d.reference("report of the resource catalogue", "this requirement is for")),
    "from_units": units_ref("send the report"),
    "to_agency": agency_ref("receives the report"),
    "to_unit": unit_ref("receives the report"),
    "due": when("the first report"),
    "interval_minutes": (integer(1), d.quantity("time between two reports", None, "minutes")),
    "trigger": (string(), d.text("event that causes the report")),
    "channel": channel_ref("sends the report"),
    "ato_missions": missions_ref("send the report"),
}, ("report",))
annex("R", {"reports": (many("ReportRequirement"), d.list_of("report requirements"))})

define("StoCapability", d.entity("Entry for special technical operations", "one unclassified entry of the capabilities integration matrix"), {
    "id": ident("entry", "the order"),
    "name": name("entry"),
    "functional_area": (choice("area_1", "area_2"), d.enum("functional area")),
    "phase": phase_ref("the entry is applicable to"),
    "coordinator": unit_ref("coordinates the entry"),
}, ("id", "name"))
annex("S", {
    "classified_annex": (common("DocumentRef"), d.reference("classified annex", "contains the full data")),
    "capabilities": (many("StoCapability"), d.list_of("unclassified entries of the capabilities integration matrix")),
}, ("An openAIX document contains only unclassified data",))

define("Inspection", d.entity("Inspection", "one inspection of the inspector general"), {
    "id": ident("inspection", "the order"),
    "subject": (string(), d.text("procedure, equipment or area of the inspection")),
    "units": units_ref("the inspection is for"),
    "window": window("the inspection occurs"),
}, ("id", "subject"))
define("AssistancePoint", d.entity("Inspector general office", "one office where personnel can speak to the inspector general"), {
    "id": ident("point", "the order"),
    "unit": unit_ref("operates the office"),
    "position": position("the office"),
    "window": window("the office is open"),
    "channel": channel_ref("the office refers to"),
}, ("id",), any_of=("unit", "position"))
annex("U", {
    "inspections": (many("Inspection"), d.list_of("inspections")),
    "assistance_points": (many("AssistancePoint"), d.list_of("offices of the inspector general")),
})

define("InteragencyTask", d.entity("Coordination task", "one task or milestone with an organization that is not part of the armed forces"), {
    "id": ident("task", "the order"),
    "task": (string(), d.text("task or milestone")),
    "organization": (ref(ORDER_ORGANIZATIONS), d.reference("interagency organization", "the task is with")),
    "unit": unit_ref("does the task"),
    "time": when("the milestone"),
    "area": (choice("humanitarian", "economic", "political", "other"), d.enum("area of the coordination")),
}, ("id", "task"))
annex("V", {
    "tasks": (many("InteragencyTask"), d.list_of("tasks and milestones with organizations that are not part of the armed forces", None, ordered=True)),
    "legal_considerations": (many("Objective"), d.list_of("legal considerations")),
})

define("ContractRequirement", d.entity("Contract support requirement", "one requirement that contractors support"), {
    "id": ident("requirement", "the order"),
    "requirement": (string(), d.text("requirement")),
    "category": (choice("theater_support", "external_support", "systems_support"), d.enum("type of contract support")),
    "contractor": (string(), d.text("name of the contractor")),
    "units": units_ref("receive the support"),
    "airfield": airfield_ref("the support is at"),
    "position": position("the support"),
    "window": window("the contract is in effect"),
}, ("id", "requirement", "category"))
define("ContractingOffice", d.entity("Contracting office", "one office that makes and controls contracts"), {
    "id": ident("office", "the order"),
    "name": name("office"),
    "unit": unit_ref("operates the office"),
    "position": position("the office"),
    "channel": channel_ref("the office refers to"),
}, ("id", "name"))
annex("W", {
    "requirements": (many("ContractRequirement"), d.list_of("contract support requirements")),
    "offices": (many("ContractingOffice"), d.list_of("contracting offices")),
    "accountability_report": (ref("reports"), d.reference("report of the resource catalogue", "gives the accountability of contractors")),
})

define("Recipient", d.entity("Recipient", "one addressee of the order"), {
    "unit": unit_ref("receives the order"),
    "agency": agency_ref("receives the order"),
    "name": name("recipient, when no unit or agency identifies it"),
    "purpose": (choice("action", "information"), d.enum("purpose of the copy")),
    "copies": (integer(1), d.count("copies")),
}, ("purpose",), any_of=("unit", "agency", "name"))
annex("Z", {"recipients": (many("Recipient"), d.list_of("recipients"))})

define("Annexes", d.entity("Annexes", "the annexes of the order, by letter",
                           d.enforced("The order shall not have an annex with the letter I, O, T, X or Y", "schema:additionalProperties")), {
    letter: (local(definition), d.statement("This field gives the annex for " + title.lower()))
    for letter, (definition, title) in ANNEXES.items()
})
