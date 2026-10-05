"""ATO, ACO, SPINS, TST, JIPTL, resource and agency fields that have no description in the source models.

One helper for each field that recurs across tasking kinds, so that the wording is uniform. Keys follow
describe/resolve.py; every value is a describe/templates.py template.
"""
from openaix.describe import templates as d
from openaix.describe.tables.orders import EXTERNAL_REF, SCHEMA_ID, SOURCE, stable_id


TIME_FORMS = "The value is a date and time, or an offset in minutes from the start of the order period"


def tasking_kind(subject):
    return d.discriminator(subject)


def objective(task):
    return d.text("result that the " + task + " is for")


def success_criteria(task):
    return d.text("conditions that show a satisfactory result of the " + task)


def abort_criteria(task):
    return d.list_of("conditions in which the flights stop the " + task)


def report_refs(task):
    return d.references("report definitions of the reports", "the " + task + " sends",
                        "Each identifier refers to the `reports` map of the resource catalogue")


def task_area(clause):
    return d.statement("This field identifies the planning area or control measure " + clause)


def supported_missions(task):
    return d.references("missions", "the " + task + " helps")


def procedure_ref(clause):
    return d.reference("procedure", clause)


def agency_ref(clause):
    return d.reference("command and control agency", clause)


def airfield_ref(clause):
    return d.reference("airfield, carrier or FARP", clause)


def time_point(clause):
    return d.time(clause, TIME_FORMS)


def timing(event):
    return d.statement("This field gives the time condition for " + event,
                       "The condition is at a time, in a window, not before a time, not after a time, or on order")


def schema_version(document):
    return d.statement("This field gives the version of the openAIX schema that this " + document + " agrees with")


def meta(document):
    return d.statement("This field gives the identification, revision and issue data of this " + document)


def briefing(subject):
    return d.list_of("attachments for the brief on this " + subject, None, "An attachment is an image, a map, a document or a link")


def identification_features(subject):
    return d.list_of("signs that identify this " + subject)


def threat_refs(subject):
    return d.references("possible threats", "are applicable to this " + subject)


def target_number(subject):
    return d.identifier(subject + " in target lists", None, "An example is `CS-0001`")


DESCRIPTIONS = {
    # ---- Document roots ---------------------------------------------------------------------------
    ("aco", "kind"): d.discriminator("an ACO"),
    ("aco", "meta"): meta("ACO"),
    ("aco", "schema_version"): schema_version("ACO"),
    ("ato", "kind"): d.discriminator("an ATO"),
    ("ato", "meta"): meta("ATO"),
    ("ato", "schema_version"): schema_version("ATO"),
    ("jiptl", "kind"): d.discriminator("a JIPTL"),
    ("jiptl", "schema_version"): schema_version("JIPTL"),
    ("resources", "kind"): d.discriminator("a resource catalogue"),
    ("resources", "meta"): meta("resource catalogue"),
    ("resources", "resources"): d.statement("This field contains the resources of this catalogue, in maps",
                                            "Each map identifies its items by their identifiers"),
    ("resources", "schema_version"): schema_version("resource catalogue"),
    ("tst", "kind"): d.discriminator("a TST list"),
    ("tst", "schema_version"): schema_version("TST list"),

    # ---- Flights and their parts ----------------------------------------------------------------
    ("Flight", "activities"): d.list_of("operations of this flight in the plan, such as transit, hold, station, refuelling and recovery"),
    ("Flight", "aircraft_type"): d.reference("aircraft type", "the aircraft of this flight have"),
    ("Flight", "alternate_routes"): d.references("routes", "this flight may use as an alternative to its route"),
    ("Flight", "callsign"): d.text("radio call sign of this flight, such as `Viper 1`"),
    ("Flight", "communications"): d.list_of("radio assignments of this flight"),
    ("Flight", "configuration"): d.statement("This field gives the store configuration of the aircraft in this flight, as the plan gives it"),
    ("Flight", "count"): d.count("aircraft in this flight"),
    ("Flight", "fuel"): d.statement("This field gives the fuel plan of this flight"),
    ("Flight", "identification"): d.statement("This field gives the IFF codes of this flight", "It also gives the values of the data link and the TACAN of the flight"),
    ("Flight", "launch"): d.statement("This field gives the launch of this flight: a scheduled launch, an alert launch or a start in the air"),
    ("Flight", "participation"): d.enum("control of the aircraft in this flight: pilots, the simulator or the two"),
    ("Flight", "recovery"): d.statement("This field gives the recovery plan of this flight after the mission"),
    ("Flight", "spins_paragraphs"): d.references("SPINS blocks", "are applicable to this flight"),
    ("Flight", "unit"): d.text("unit that supplies this flight, such as `Blue fighter squadron`"),
    ("FlightSelection", "flight"): d.reference("flight", "this selection gets aircraft from"),
    ("FlightSelection", "members"): d.list_of("position numbers of the selected aircraft in the flight", None,
                                              "Without this field, the selection contains all aircraft of the flight"),
    ("Activity", "area"): task_area("in which the flight does this operation"),
    ("Activity", "kind"): d.enum("type of flight operation"),
    ("Activity", "support_flight"): d.reference("flight", "helps with this operation, such as the tanker for a refuelling operation"),
    ("Activity", "window"): d.window("the flight does this operation"),
    ("AircraftOverride", "fuel"): d.statement("This field gives the fuel plan of this aircraft, which replaces the fuel plan of the flight"),
    ("AircraftOverride", "identification"): d.statement("This field gives the identification values of this aircraft, which replace the values of the flight"),
    ("AircraftOverride", "member"): d.statement("This field gives the position number of this aircraft in the flight, from 1"),
    ("AircraftOverride", "scl"): d.reference("SCL", "this aircraft has, which replaces the primary SCL of the flight"),
    ("Configuration", "alternatives"): d.list_of("SCLs that the flight can use as alternatives, and the conditions in which it uses them"),
    ("Configuration", "member_overrides"): d.list_of("values for one aircraft that are different from the values of the flight"),
    ("Configuration", "primary_scl"): d.reference("SCL", "all aircraft of the flight have, unless an aircraft entry gives a different load"),
    ("Configuration", "secondary_purpose"): d.text("function of the SCL in `secondary_scl`"),
    ("Configuration", "secondary_scl"): d.reference("SCL", "the flight has for a second function"),
    ("SCLAlternative", "authority"): agency_ref("gives approval for the SCL of this alternative"),
    ("SCLAlternative", "condition"): d.text("condition in which the flight uses the SCL of this alternative"),
    ("SCLAlternative", "scl"): d.reference("SCL of this alternative"),
    ("FuelPlan", "bingo"): d.statement("This field gives the bingo fuel, which is the fuel quantity at which the flight starts to go back to base"),
    ("FuelPlan", "initial"): d.statement("This field gives the fuel at the start of the mission",
                                         "The value is a quantity with its unit, or a percentage of full fuel in the aircraft and in the external tanks"),
    ("FuelPlan", "joker"): d.statement("This field gives the joker fuel, which is a fuel quantity more than the bingo fuel",
                                       "At the joker fuel, the flight changes its plan"),
    ("FuelPlan", "reserve"): d.statement("This field gives the fuel that the flight keeps as a reserve at landing"),
    ("InternalFuel", "external_percent"): d.quantity("fuel in the external tanks, as a part of their full fuel", None, "percent"),
    ("InternalFuel", "internal_percent"): d.quantity("fuel in the tanks in the aircraft, as a part of their full fuel", None, "percent"),
    ("Mass", "unit"): d.enum("unit of the fuel quantity"),
    ("Mass", "value"): d.statement("This field gives the fuel quantity as a number, in the unit that `unit` gives"),
    ("Identification", "datalink_network"): d.text("name of the data link network of this flight"),
    ("Identification", "datalink_station"): d.text("station number of this flight in the data link"),
    ("Identification", "datalink_type"): d.text("type of data link, such as `Link 16`"),
    ("Identification", "mode_1"): d.statement("This field gives the IFF mode 1 code, as two digits from 0 to 7"),
    ("Identification", "mode_2"): d.statement("This field gives the IFF mode 2 code, as four digits from 0 to 7"),
    ("Identification", "mode_3"): d.statement("This field gives the IFF mode 3 code, as four digits from 0 to 7"),
    ("Identification", "mode_4"): d.enum("condition of IFF mode 4"),
    ("Identification", "mode_5"): d.enum("condition of IFF mode 5"),
    ("Identification", "tacan"): d.statement("This field gives the channel, band and identifier of the TACAN of this flight, for air-to-air operation"),
    ("RadioAssignment", "channel"): d.reference("radio channel", "this assignment uses"),
    ("RadioAssignment", "preset"): d.statement("This field gives the preset number of the radio channel on the radio of the aircraft"),
    ("RadioAssignment", "radio"): d.text("radio of the aircraft that uses the channel, such as `UHF` or `VHF`"),
    ("ScheduledLaunch", "departure"): airfield_ref("the flight starts its mission from"),
    ("ScheduledLaunch", "kind"): d.discriminator("a scheduled launch"),
    ("ScheduledLaunch", "startup"): time_point("at which the flight starts the engines of its aircraft"),
    ("ScheduledLaunch", "takeoff"): time_point("at which the flight does the take-off"),
    ("ScheduledLaunch", "taxi"): time_point("at which the flight starts to taxi"),
    ("AlertLaunch", "departure"): airfield_ref("keeps the alert aircraft"),
    ("AlertLaunch", "kind"): d.discriminator("an alert launch"),
    ("AlertLaunch", "readiness_minutes"): d.quantity("time from the launch order until the aircraft are in the air", None, "minutes"),
    ("AlertLaunch", "release_authority"): agency_ref("gives the order to launch the alert aircraft"),
    ("AirborneLaunch", "at"): time_point("at which the flight starts in the air"),
    ("AirborneLaunch", "kind"): d.discriminator("an airborne start"),
    ("AirborneLaunch", "speed"): d.quantity("speed of the flight at the start in the air", "Speed"),
    ("Recovery", "alternates"): d.references("alternative operating locations", "the flight may use for recovery",
                                             "An operating location is an airfield, a carrier or a FARP"),
    ("Recovery", "destination"): airfield_ref("the flight goes back to"),
    ("Recovery", "planned_time"): time_point("the recovery, as the plan gives it"),
    ("Recovery", "procedure"): procedure_ref("the flight follows for recovery"),
    ("SupportLink", "coordination"): d.text("coordination between this mission and the flight that helps it"),
    ("SupportLink", "flight"): d.reference("flight", "helps this mission"),
    ("SupportLink", "role"): d.enum("role of the flight that helps this mission"),
    ("SupportLink", "window"): d.window("the flight helps this mission"),

    # ---- Missions and packages --------------------------------------------------------------------
    ("Mission", "constraints"): d.list_of("limits that are applicable to this mission"),
    ("Mission", "contingencies"): d.list_of("steps in the plan for conditions that change the plan of this mission"),
    ("Mission", "control"): d.statement("This field gives the control of this mission: a command and control agency, or one of the flights of the mission"),
    ("Mission", "package"): d.reference("package", "contains this mission"),
    ("Mission", "priority"): d.statement("This field gives the priority of this mission in the order", "Priority 1 is the highest"),
    ("Mission", "request_refs"): d.list_of("references to the requests that this mission is for"),
    ("Mission", "support"): d.list_of("flights that help this mission, with their roles"),
    ("Mission", "tasking_relationship"): d.enum("relation between the order and this mission"),
    ("Mission", "threat_refs"): threat_refs("mission"),
    ("Contingency", "action"): d.text("step that the flight does when the condition occurs"),
    ("Contingency", "alternate_route"): d.reference("route", "the flight uses for this contingency"),
    ("Contingency", "condition"): d.text("condition that starts this contingency"),
    ("Contingency", "decision_authority"): agency_ref("makes the decision for this contingency"),
    ("Contingency", "divert"): airfield_ref("the flight goes to for this contingency"),
    ("AgencyControl", "agency"): agency_ref("controls the mission"),
    ("AgencyControl", "check_in"): procedure_ref("the flights follow when they first contact the agency"),
    ("AgencyControl", "handovers"): d.references("command and control agencies", "get the control of the mission after the first agency",
                                                 "The list is in the sequence of the handovers"),
    ("AgencyControl", "kind"): d.discriminator("control by an agency"),
    ("SelfControl", "kind"): d.discriminator("self control"),
    ("SelfControl", "responsible_flight"): d.reference("flight", "controls the mission"),
    ("Package", "commander"): d.statement("This field identifies the flight and the aircraft of the package commander"),
    ("Package", "coordination"): d.list_of("coordination instructions for the missions of the package"),
    ("Package", "objective"): objective("package"),
    ("Package", "rendezvous_time"): timing("the rendezvous of the package"),

    # ---- Time conditions ---------------------------------------------------------------------------
    ("AtTime", "at"): time_point("at which the event occurs"),
    ("AtTime", "kind"): d.discriminator("a time condition at a time"),
    ("AtTime", "tolerance_seconds"): d.quantity("maximum time interval between the event and the time in `at`", None, "seconds",
                                                "The limit is applicable before and after that time"),
    ("InWindow", "kind"): d.discriminator("a time condition in a window"),
    ("InWindow", "window"): d.window("the event occurs"),
    ("BeforeTime", "at"): time_point("after which the event does not occur"),
    ("BeforeTime", "kind"): d.discriminator("a time condition not after a time"),
    ("AfterTime", "at"): time_point("before which the event does not occur"),
    ("AfterTime", "kind"): d.discriminator("a time condition not before a time"),
    ("OnOrder", "authority"): agency_ref("gives the order for the event"),
    ("OnOrder", "condition"): d.text("condition in which the authority gives the order for the event"),
    ("OnOrder", "kind"): d.discriminator("a time condition on order"),

    # ---- Taskings ------------------------------------------------------------------------------
    ("CounterAir", "kind"): tasking_kind("a counterair tasking"),

    ("AirborneControl", "abort_criteria"): abort_criteria("airborne control task"),
    ("AirborneControl", "area"): task_area("in which the airborne control station is"),
    ("AirborneControl", "control_responsibilities"): d.list_of("control and surveillance tasks of the airborne control mission"),
    ("AirborneControl", "datalink"): d.statement("This field gives the data link and identification values of the airborne control task"),
    ("AirborneControl", "handover"): d.text("instructions for the handover of the airborne control station"),
    ("AirborneControl", "kind"): tasking_kind("an airborne control tasking"),
    ("AirborneControl", "objective"): objective("airborne control task"),
    ("AirborneControl", "report_refs"): report_refs("airborne control task"),
    ("AirborneControl", "station_window"): d.window("the airborne control aircraft are on station"),
    ("AirborneControl", "success_criteria"): success_criteria("airborne control task"),
    ("AirborneControl", "supported_missions"): supported_missions("airborne control task"),

    ("CustomTask", "abort_criteria"): abort_criteria("custom task"),
    ("CustomTask", "area"): task_area("in which the custom task occurs"),
    ("CustomTask", "assigned_actions"): d.list_of("steps of the custom task", None, "The flights do the steps in their sequence", ordered=True),
    ("CustomTask", "coordination"): d.text("coordination for the custom task"),
    ("CustomTask", "kind"): tasking_kind("a tasking for a custom task"),
    ("CustomTask", "objective"): objective("custom task"),
    ("CustomTask", "operating_window"): d.window("the custom task occurs"),
    ("CustomTask", "report_refs"): report_refs("custom task"),
    ("CustomTask", "required_capabilities"): d.list_of("functions that are necessary for the flights of the custom task"),
    ("CustomTask", "success_criteria"): success_criteria("custom task"),

    ("ElectromagneticTask", "abort_criteria"): abort_criteria("electromagnetic task"),
    ("ElectromagneticTask", "area"): task_area("in which the electromagnetic task occurs"),
    ("ElectromagneticTask", "assigned_effect"): d.text("electromagnetic effect that the flights give", "An example is `Stand-off jamming of the SA-6 radars`"),
    ("ElectromagneticTask", "coordination_procedure"): procedure_ref("coordinates the electromagnetic task"),
    ("ElectromagneticTask", "equipment_requirements"): d.list_of("equipment that is necessary for the electromagnetic task"),
    ("ElectromagneticTask", "kind"): tasking_kind("an electromagnetic tasking"),
    ("ElectromagneticTask", "objective"): objective("electromagnetic task"),
    ("ElectromagneticTask", "operating_window"): d.window("the electromagnetic task occurs"),
    ("ElectromagneticTask", "report_refs"): report_refs("electromagnetic task"),
    ("ElectromagneticTask", "success_criteria"): success_criteria("electromagnetic task"),
    ("ElectromagneticTask", "supported_missions"): supported_missions("electromagnetic task"),

    ("Escort", "abort_criteria"): abort_criteria("escort"),
    ("Escort", "kind"): tasking_kind("an escort tasking"),
    ("Escort", "objective"): objective("escort"),
    ("Escort", "protection_window"): d.window("the escort gives protection to the missions"),
    ("Escort", "release_condition"): d.text("condition at which the escort stops the protection of the missions"),
    ("Escort", "rendezvous_time"): timing("the rendezvous of the escort"),
    ("Escort", "report_refs"): report_refs("escort"),
    ("Escort", "separation_instructions"): d.text("position of the escort in relation to the missions that it gives protection to"),
    ("Escort", "success_criteria"): success_criteria("escort"),
    ("Escort", "supported_missions"): supported_missions("escort"),

    ("OnCallCAS", "abort_criteria"): abort_criteria("on-call CAS"),
    ("OnCallCAS", "area"): task_area("in which the on-call CAS operates"),
    ("OnCallCAS", "check_in_procedure"): procedure_ref("the flights follow at the start of the on-call CAS"),
    ("OnCallCAS", "kind"): tasking_kind("an on-call CAS tasking"),
    ("OnCallCAS", "objective"): objective("on-call CAS"),
    ("OnCallCAS", "report_refs"): report_refs("on-call CAS"),
    ("OnCallCAS", "request_refs"): d.list_of("references to the air support requests that this tasking is for"),
    ("OnCallCAS", "success_criteria"): success_criteria("on-call CAS"),
    ("OnCallCAS", "supported_force"): d.text("ground force that the on-call CAS helps"),
    ("OnCallCAS", "target_assignment_procedure"): procedure_ref("gives targets to the on-call CAS flights"),
    ("OnCallCAS", "tasking_agency"): agency_ref("tasks the on-call CAS flights"),
    ("OnCallCAS", "terminal_control"): d.enum("type of terminal attack control for the on-call CAS"),

    ("Patrol", "abort_criteria"): abort_criteria("CAP"),
    ("Patrol", "area"): task_area("that contains the CAP station"),
    ("Patrol", "coverage_responsibility"): d.text("air threats and airspace that are the task of the CAP"),
    ("Patrol", "engagement_instructions"): procedure_ref("gives the commit criteria and the engagement conditions of the CAP"),
    ("Patrol", "handover"): d.text("instructions for the handover of the CAP station to the subsequent flight"),
    ("Patrol", "kind"): tasking_kind("a CAP tasking"),
    ("Patrol", "objective"): objective("CAP"),
    ("Patrol", "report_refs"): report_refs("CAP"),
    ("Patrol", "station_window"): d.window("the CAP flights are on station"),
    ("Patrol", "success_criteria"): success_criteria("CAP"),

    ("PersonnelRecovery", "abort_criteria"): abort_criteria("personnel recovery"),
    ("PersonnelRecovery", "coordination_agency"): agency_ref("coordinates the personnel recovery"),
    ("PersonnelRecovery", "incident"): d.text("event that isolates the personnel"),
    ("PersonnelRecovery", "kind"): tasking_kind("a personnel recovery tasking"),
    ("PersonnelRecovery", "medical_requirements"): d.text("medical treatment that is necessary for the isolated personnel"),
    ("PersonnelRecovery", "objective"): objective("personnel recovery"),
    ("PersonnelRecovery", "recognition_procedure"): procedure_ref("lets the recovery force and the isolated personnel identify each other"),
    ("PersonnelRecovery", "recovery_destination"): airfield_ref("receives the personnel after the recovery"),
    ("PersonnelRecovery", "recovery_method"): d.enum("method that the aircraft use for the recovery"),
    ("PersonnelRecovery", "report_refs"): report_refs("personnel recovery"),
    ("PersonnelRecovery", "search_area"): task_area("in which the recovery force does a search for the isolated personnel"),
    ("PersonnelRecovery", "success_criteria"): success_criteria("personnel recovery"),
    ("PersonnelRecovery", "tasking_procedure"): procedure_ref("tasks the recovery force"),

    ("PreplannedAttack", "abort_criteria"): abort_criteria("preplanned attack"),
    ("PreplannedAttack", "assignments"): d.list_of("attack assignments of the preplanned attack", None,
                                                   "Each assignment gives one target to one or more selected aircraft"),
    ("PreplannedAttack", "kind"): tasking_kind("a preplanned attack tasking"),
    ("PreplannedAttack", "objective"): objective("preplanned attack"),
    ("PreplannedAttack", "report_refs"): report_refs("preplanned attack"),
    ("PreplannedAttack", "success_criteria"): success_criteria("preplanned attack"),
    ("PreplannedAttack", "supporting_request"): d.statement("This field gives a reference to the air support request that the preplanned attack is for"),
    ("AttackAssignment", "activation_condition"): d.text("condition in which this attack assignment starts"),
    ("AttackAssignment", "assigned_to"): d.list_of("flights and aircraft that attack the target"),
    ("AttackAssignment", "priority"): d.statement("This field gives the priority of this attack assignment in the tasking", "Priority 1 is the highest"),
    ("AttackAssignment", "required_stores"): d.references("stores", "are necessary for the attack on the target"),
    ("AttackAssignment", "role"): d.enum("role of this attack assignment: `primary` or `alternate`"),
    ("AttackAssignment", "success_criteria"): success_criteria("attack assignment"),
    ("AttackAssignment", "target"): d.statement("This field gives the target of this attack assignment",
                                                "The target is a fixed target with aimpoint identifiers, a mobile target or an area target"),
    ("AttackAssignment", "timing"): timing("the attack"),
    ("AreaTargetSelection", "kind"): d.discriminator("a selected area target"),
    ("AreaTargetSelection", "target"): d.reference("area target", "this selection contains"),
    ("MobileSelection", "kind"): d.discriminator("a selected mobile target"),
    ("MobileSelection", "target"): d.reference("mobile target", "this selection contains"),

    ("Reconnaissance", "abort_criteria"): abort_criteria("reconnaissance"),
    ("Reconnaissance", "kind"): tasking_kind("a reconnaissance tasking"),
    ("Reconnaissance", "objective"): objective("reconnaissance"),
    ("Reconnaissance", "report_refs"): report_refs("reconnaissance"),
    ("Reconnaissance", "reporting_procedure"): procedure_ref("the flights follow to send the information"),
    ("Reconnaissance", "requirements"): d.list_of("collection entries of the reconnaissance"),
    ("Reconnaissance", "success_criteria"): success_criteria("reconnaissance"),
    ("CollectionRequirement", "area"): task_area("in which the flight collects the information"),
    ("CollectionRequirement", "collection_window"): d.window("the flight collects the information"),
    ("CollectionRequirement", "information_required"): d.text("information that the flight gets"),
    ("CollectionRequirement", "latest_useful_time"): time_point("after which the information has no value"),
    ("CollectionRequirement", "product"): d.enum("output that the flight sends"),
    ("CollectionRequirement", "recipient"): agency_ref("receives the output"),
    ("CollectionRequirement", "sensor"): d.enum("type of sensor that the flight uses for the collection"),
    ("CollectionRequirement", "target"): d.reference("target", "the collection is about"),

    ("Refueling", "abort_criteria"): abort_criteria("refuelling task"),
    ("Refueling", "area"): task_area("that contains the refuelling track or anchor"),
    ("Refueling", "channel"): d.reference("radio channel", "connects the tanker and the receivers"),
    ("Refueling", "kind"): tasking_kind("a refuelling tasking"),
    ("Refueling", "objective"): objective("refuelling task"),
    ("Refueling", "planned_offload"): d.statement("This field gives the total fuel that the tanker plans to give on this tasking"),
    ("Refueling", "rendezvous_procedure"): procedure_ref("the receivers follow to go to the tanker"),
    ("Refueling", "report_refs"): report_refs("refuelling task"),
    ("Refueling", "station_window"): d.window("the tanker is on station"),
    ("Refueling", "success_criteria"): success_criteria("refuelling task"),
    ("Refueling", "unassigned_receiver_policy"): d.text("instruction for receivers that have no window in the schedule of the tanker"),
    ("ReceiverSlot", "flight"): d.reference("receiver flight", "this entry gives a refuelling window to"),
    ("ReceiverSlot", "planned_offload"): d.statement("This field gives the fuel that the tanker plans to give to the receiver flight in this window"),
    ("ReceiverSlot", "window"): d.window("the receiver flight gets fuel from the tanker"),

    ("Training", "abort_criteria"): abort_criteria("training"),
    ("Training", "area"): task_area("in which the training occurs"),
    ("Training", "debrief_procedure"): procedure_ref("the flights follow to examine the training after it stops"),
    ("Training", "events"): d.list_of("events of the training", None, "The events occur in their sequence", ordered=True),
    ("Training", "exercise_window"): d.window("the training occurs"),
    ("Training", "kind"): tasking_kind("a training tasking"),
    ("Training", "objective"): objective("training"),
    ("Training", "report_refs"): report_refs("training"),
    ("Training", "success_criteria"): success_criteria("training"),

    ("Transport", "abort_criteria"): abort_criteria("transport mission"),
    ("Transport", "delivery_method"): d.enum("method that moves the load out of the aircraft at the airfield that receives it"),
    ("Transport", "delivery_time"): timing("the load at the airfield that receives it"),
    ("Transport", "destination"): airfield_ref("receives the load"),
    ("Transport", "ground_coordination"): agency_ref("coordinates the transport on the ground"),
    ("Transport", "kind"): tasking_kind("a transport tasking"),
    ("Transport", "loading_procedure"): procedure_ref("the flight follows to put the cargo and the persons on the aircraft"),
    ("Transport", "manifest"): d.statement("This field gives the cargo and the persons on the aircraft of the transport mission"),
    ("Transport", "objective"): objective("transport mission"),
    ("Transport", "pickup"): airfield_ref("the flight collects the load from"),
    ("Transport", "pickup_time"): timing("the collection of the load"),
    ("Transport", "report_refs"): report_refs("transport mission"),
    ("Transport", "success_criteria"): success_criteria("transport mission"),
    ("Manifest", "cargo"): d.list_of("cargo items of the transport mission"),
    ("Manifest", "passengers"): d.count("persons on the aircraft of the transport mission"),
    ("Manifest", "personnel_notes"): d.text("notes about the personnel on the aircraft of the transport mission"),
    ("CargoItem", "handling"): d.text("handling instructions for this cargo item"),
    ("CargoItem", "quantity"): d.count("units of this cargo item"),

    ("ProcedureStep", "action"): d.text("task of this step"),
    ("ProcedureStep", "completion"): d.text("condition at which this step is completed"),
    ("ProcedureStep", "condition"): d.text("condition in which this step is applicable"),


    # ---- Resource catalogue ---------------------------------------------------------------------
    ("AreaSelection", "area"): d.reference("planning area", "this selection contains"),
    ("Aimpoint", "briefing"): briefing("aimpoint"),
    ("AreaTarget", "area"): task_area("that contains the area target"),
    ("AreaTarget", "briefing"): briefing("area target"),
    ("AreaTarget", "identification_features"): identification_features("area target"),
    ("AreaTarget", "kind"): d.discriminator("an area target"),
    ("AreaTarget", "target_number"): target_number("area target"),
    ("AreaTarget", "target_population"): d.text("types of target objects in the target area"),
    ("AreaTarget", "threat_refs"): threat_refs("area target"),
    ("Attachment", "caption"): d.text("short text that goes with this attachment"),
    ("Attachment", "kind"): d.enum("type of attachment"),
    ("Attachment", "path"): d.text("path or link of the file of the attachment",
                                   "A path starts at the folder of the document that contains the attachment"),
    ("Attachment", "title"): d.text("title of this attachment"),
    ("CleanPayload", "kind"): d.discriminator("a load with no stores"),
    ("FixedTarget", "aimpoints"): d.map_of("aimpoint entries of the fixed target"),
    ("FixedTarget", "briefing"): briefing("fixed target"),
    ("FixedTarget", "identification_features"): identification_features("fixed target"),
    ("FixedTarget", "kind"): d.discriminator("a fixed target"),
    ("FixedTarget", "target_number"): target_number("fixed target"),
    ("FixedTarget", "threat_refs"): threat_refs("fixed target"),
    ("LastKnownPosition", "as_of"): d.time("the last known position"),
    ("MobileTarget", "briefing"): briefing("mobile target"),
    ("MobileTarget", "expected_movement"): d.text("possible movement of the mobile target"),
    ("MobileTarget", "identification_features"): identification_features("mobile target"),
    ("MobileTarget", "kind"): d.discriminator("a mobile target"),
    ("MobileTarget", "last_known"): d.statement("This field gives the last known position of the mobile target, with its time"),
    ("MobileTarget", "search_area"): task_area("in which flights do a search for the mobile target"),
    ("MobileTarget", "target_number"): target_number("mobile target"),
    ("MobileTarget", "threat_refs"): threat_refs("mobile target"),
    ("Procedure", "references"): d.list_of("documents that the procedure refers to"),
    ("Procedure", "steps"): d.list_of("steps of the procedure", None, "Units do the steps in their sequence", ordered=True),
    ("Procedure", "title"): d.text("title of the procedure"),
    ("Route", "contingencies"): d.list_of("instructions for contingencies on the route"),
    ("Route", "points"): d.list_of("points of the route", None, "The points are in the sequence of the flight", ordered=True),
    ("RoutePoint", "action"): d.enum("flight phase at this route point"),
    ("RoutePoint", "speed"): d.quantity("speed that the plan gives for this route point", "Speed"),
    ("RoutePoint", "timing"): timing("the flight at this point"),
    ("Store", "kind"): d.enum("type of store"),

    # ---- Standard conventional load (build/scl.py) -----------------------------------------------
    ("scl", None): d.root("Standard conventional load", "SCL", "one store configuration of one aircraft type",
                          "It gives the stores of each aircraft, their stations and fuzes, the gun rounds and the countermeasures",
                          "The load does not show that it is possible to install the stores on the aircraft"),
    ("scl", "$schema"): SCHEMA_ID,
    ("scl", "id"): stable_id("SCL"),
    ("scl", "kind"): d.discriminator("an SCL"),
    ("scl", "name"): d.name("SCL", "An example is `AI-1 GBU-12`"),
    ("scl", "scl_number"): d.text("number of the load in the table of the unit, such as `DTA05` or `101`"),
    ("scl", "code"): d.statement("This field gives the SCL code of the load, such as `4G12.3A.1X.2`",
                                 "Some units use these short codes", "They are not a standard for all units",
                                 "openAIX does not use the code to find the stores", "The stores and the stations of the record are the reference"),
    ("scl", "aircraft_type"): d.reference("aircraft type", "this load is for",
                                          d.enforced("Each flight with this SCL shall have this aircraft type", "validator:openaix.check.scl.flight_errors")),
    ("scl", "missions"): d.list_of("tasking families and roles", "this load is applicable to",
                                   d.enforced("The list shall include the tasking of each flight that has this load as its primary load",
                                              "validator:openaix.check.scl.flight_errors")),
    ("scl", "era"): d.text("era of the load, such as `modern` or `retro`", "The unit sets its eras"),
    ("scl", "variant_tags"): d.list_of("labels of this load variant, such as `120B` or `Pre-2015`", None,
                                       "Each label shows a difference from the other load variants with the same number"),
    ("scl", "stores"): d.list_of("stores of the load, with the quantity of each store in each aircraft", None,
                                 "This list does not give the stations",
                                 d.enforced("Each store shall occur one time in the list", "validator:openaix.check.scl.scl_errors"),
                                 d.enforced("With stations, the quantity of each store shall be equal to the sum on its stations",
                                            "validator:openaix.check.scl.scl_errors")),
    ("scl", "stations"): d.list_of("weapon stations of the load, with the stores on each station"),
    ("scl", "gun_rounds"): d.count("gun rounds in each aircraft"),
    ("scl", "countermeasures"): d.statement("This field gives the chaff, the flares and the countermeasure program of the load"),
    ("scl", "laser_code"): d.statement("This field gives the default laser code for the weapons of this load",
                                       "A store entry can give a different code"),
    ("scl", "remarks"): d.text("remarks about the load"),
    ("scl", "source"): SOURCE,
    ("scl", "resources_ref"): EXTERNAL_REF,
    ("scl", "extensions"): d.extension(),
    ("AircraftType", None): d.entity("Aircraft type", "a type and version of aircraft that flights and SCLs refer to",
                                     "The type names of simulators are in `extensions.sim`"),
    ("AircraftType", "name"): d.name("aircraft type", "An example is `F-16C Fighting Falcon Block 50`"),
    ("AircraftType", "category"): d.enum("class of the aircraft type"),
    ("AircraftType", "extensions"): d.extension(),
    ("SCLMission", None): d.entity("SCL mission", "a tasking family and a role for which the load is applicable"),
    ("SCLMission", "tasking"): d.enum("tasking family, as the `kind` field of an ATO tasking gives it"),
    ("SCLMission", "role"): d.enum("role or mission type in the tasking family",
                                   "It agrees with the `role` field or the `mission_type` field of the tasking",
                                   "If the entry does not give a role, the load is applicable to all roles of the tasking family",
                                   d.enforced("The role shall be a role of the tasking family", "schema:allOf")),
    ("StationLoad", None): d.entity("Station load", "the stores on one weapon station of the aircraft"),
    ("StationLoad", "items"): d.list_of("stores on this station"),
    ("StationLoad", "rack"): d.reference("store of the `rack` type", "has the other stores on this station"),
    ("StationLoad", "station"): d.text("label of the weapon station in the flight manual or the simulator, such as `3` or `5L`",
                                       d.enforced("Each station shall occur one time in the list of stations", "validator:openaix.check.scl.scl_errors")),
    ("StoreLoad", None): d.entity("Store load", "one store of a load with its quantity, fuze, laser code and program"),
    ("StoreLoad", "fuze"): d.statement("This field gives the fuze setting of the store"),
    ("StoreLoad", "laser_code"): d.statement("This field gives the laser code of the store",
                                             "It replaces the laser code of the SCL for this store"),
    ("StoreLoad", "program"): d.text("weapon program of the store"),
    ("StoreLoad", "quantity"): d.count("items of the store in each aircraft, or on the station in a station entry"),
    ("StoreLoad", "store"): d.reference("store", "this entry is for"),
    ("Countermeasures", None): d.entity("Countermeasure load", "the chaff, the flares and the dispenser program of a load"),
    ("Countermeasures", "chaff"): d.count("chaff cartridges in each aircraft"),
    ("Countermeasures", "flares"): d.count("flares in each aircraft"),
    ("Countermeasures", "program"): d.text("countermeasure program of the dispensers"),
    ("Threat", "area"): task_area("in which the threat operates"),
    ("Threat", "as_of"): d.time("the threat data"),
    ("Threat", "briefing"): briefing("threat"),
    ("Threat", "expected_activity"): d.text("possible operations of the threat"),
    ("Threat", "kind"): d.enum("type of threat"),
    ("Threat", "system"): d.text("system of the threat, such as `2K12 Kub`"),

    # ---- SPINS blocks ---------------------------------------------------------------------------
}

ENUMS = {
    ("Activity", "kind"): d.values({
        "transit": "a flight from one point to a different point", "hold": d.value_sentence("The flight holds at a point or in an area."),
        "station": "time on station in an area", "refuel": "air-to-air refuelling from a flight that helps",
        "task": "the execution of the tasking of the mission",
        "recovery": d.value_sentence("The flight goes back to an airfield for the landing."),
        "other": "an operation that the other values do not include",
    }),
    ("Flight", "participation"): d.values({
        "player": d.value_sentence("Pilots fly all aircraft of the flight."),
        "ai": d.value_sentence("The simulator flies all aircraft of the flight."),
        "mixed": d.value_sentence("Pilots and the simulator fly the aircraft of the flight."),
    }),
    ("Identification", "mode_4"): d.values({"on": d.value_sentence("The IFF transponder operates in Mode 4."),
                                            "off": d.value_sentence("The IFF transponder does not operate in Mode 4."),
                                            "as_directed": d.value_sentence("The flight sets the mode as the instructions of the mission tell it.")}),
    ("Identification", "mode_5"): d.values({"on": d.value_sentence("The IFF transponder operates in Mode 5."),
                                            "off": d.value_sentence("The IFF transponder does not operate in Mode 5."),
                                            "as_directed": d.value_sentence("The flight sets the mode as the instructions of the mission tell it.")}),
    ("Mass", "unit"): d.values({"kg": d.value_sentence("The mass is in kilograms."),
                                "lb": d.value_sentence("The mass is in pounds. One pound is 0.45359237 kilograms.")}),
    ("Mission", "tasking_relationship"): d.values({
        "assigned": d.value_sentence("The order tasks the mission."),
        "coordination_only": d.value_sentence("The order shows the mission only for coordination, and does not task it."),
    }),
    ("SupportLink", "role"): d.values({
        "tanker": "a tanker that gives fuel to the aircraft of the mission in flight",
        "escort": "an escort that defends the mission against enemy aircraft",
        "airborne_control": "an aircraft, such as an AWACS aircraft, that gives surveillance and control to the mission",
        "suppression": "a flight that neutralizes or degrades the enemy air defences that are a threat to the mission",
        "recovery": "a personnel recovery flight that collects the aircrew of the mission when they become isolated",
        "controller": "a JTAC or a FAC(A) that gives terminal attack control to the mission",
        "other": "a support role that the other values do not include",
    }),
    ("OnCallCAS", "terminal_control"): d.values({
        "type_1": d.value("terminal attack control of type 1",
                          "The controller sees the attack aircraft and the target, and gives clearance for each attack"),
        "type_2": d.value("terminal attack control of type 2",
                          "The controller gives clearance for each attack, but cannot see the attack aircraft or the target "
                          "when the aircraft releases the weapon"),
        "type_3": d.value("terminal attack control of type 3",
                          "The controller gives one clearance for more than one attack in one engagement, with attack restrictions"),
        "assigned_by_controller": d.value_sentence("The controller sets the type for each attack."),
    }),
    ("PersonnelRecovery", "recovery_method"): d.values({
        "land": d.value_sentence("The aircraft lands to get the personnel."),
        "hoist": d.value_sentence("The aircraft stays in the air and lifts the personnel into it."),
        "pickup": "a pickup of the personnel from the surface",
        "assigned_on_scene": d.value_sentence("The commander at the site of the recovery sets the method."),
    }),
    ("AttackAssignment", "role"): d.values({
        "primary": d.value_sentence("The selected aircraft do this assignment first."),
        "alternate": d.value_sentence("The selected aircraft do this assignment when the primary assignment is not possible."),
    }),
    ("Transport", "delivery_method"): d.values({
        "land": d.value_sentence("The aircraft lands, and then the load goes out of the aircraft."),
        "airdrop": d.value_sentence("The aircraft releases the load in flight."),
        "sling_load": d.value_sentence("The load is a sling load below the aircraft until the aircraft releases it."),
        "hover": d.value_sentence("The load goes out of the aircraft while the aircraft stays at one position in the air."),
    }),
    ("Attachment", "kind"): d.values({"image": "an image file that shows an area, an object or a plan",
                                      "map": "a file that shows a map or a chart of an area",
                                      "document": "a file with written text, for example an order or a brief",
                                      "link": "a link to an external resource"}),
    ("RoutePoint", "action"): d.values({
        "departure": d.value_sentence("The flight starts its route from the departure airfield at this point."),
        "transit": "a transit between two points", "ingress": "the ingress to the task area",
        "egress": "the egress from the task area", "hold": d.value_sentence("The flight holds at the point."),
        "approach": d.value_sentence("At this point, the flight starts its approach to an airfield for the landing."),
        "recovery": d.value_sentence("At this point, the flight starts to go back to an airfield after the task."),
    }),
    ("Store", "role"): d.values({
        "targeting": "a pod that finds, tracks and designates targets", "navigation": "a pod with sensors for navigation at night or at low altitude",
        "self_protection_jamming": "a jammer that gives protection to the aircraft that has it",
        "tactical_jamming": "a jammer that attacks enemy radars and radios for other aircraft",
        "emitter_targeting": "a pod that finds enemy radars and gives their positions to weapons such as the HARM",
        "datalink": "a pod that sends data to the weapons of the aircraft or receives data from them",
        "reconnaissance": "a pod that collects images or other data for reconnaissance",
        "other": "a pod with a function that the other values do not include",
    }),
    ("Store", "kind"): d.values({
        "weapon": "a weapon, such as a missile, that the aircraft fires or drops",
        "pod": "a pod with sensors or other equipment, such as a targeting pod. The aircraft does not release it",
        "tank": "an external fuel tank",
        "rack": "a store that has other stores on it",
        "cargo": "a load in the aircraft that goes to other units", "other": "a store that the other values do not include",
    }),
    ("Threat", "kind"): d.values({
        "air": "enemy aircraft", "air_defense": "surface-to-air weapons, such as SAMs and air defence guns", "surface": "surface forces other than air defence",
        "electromagnetic": "an electromagnetic threat to radio or radar equipment",
        "environmental": "a dangerous condition from the weather or the terrain",
        "other": "a threat that the other values do not include",
    }),
}
