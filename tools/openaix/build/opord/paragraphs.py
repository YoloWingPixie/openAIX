"""OPORD base order, paragraphs 1 to 5 (FM 5-0, Appendix D): situation, mission, execution, sustainment, and
command and signal."""
from openaix.build.opord.schema import (agencies_ref, agency_ref, airfield_ref, AIRSPACE_CATEGORIES, boolean,
                                        channel_ref, channels_ref, choice, common, define, DIRECTIONS, ECHELONS,
                                        ident, integer, items, local, many, measure_ref, measures_ref, missions_ref,
                                        name, number, ORDER_COMMAND_POSTS, ORDER_DECISION_POINTS, ORDER_UNITS,
                                        phase_ref, phases_ref, position, ref, refs, RELATIONSHIPS, string, summary,
                                        SUPPLY_CLASSES, texts, unit_ref, units_ref, when, window)
from openaix.describe import templates as d


# ---- Paragraph 1: Situation -----------------------------------------------------------------------------
define("AreaOfInterest", d.entity("Area of interest", "the area of interest of the operation, as control measures"), {
    "measures": measures_ref("give the area of interest"),
    "summary": summary("the area of interest"),
})
define("KeyTerrain", d.entity("Key terrain", "one area or point of key terrain"), {
    "id": ident("key terrain", "the order"),
    "name": name("key terrain"),
    "position": position("the key terrain"),
    "measure": measure_ref("gives the area of the key terrain"),
    "significance": (string(), d.text("effect of the key terrain on the operation")),
}, ("id", "name"), any_of=("position", "measure"))
define("AvenueOfApproach", d.entity("Avenue of approach", "one avenue of approach for a force of one echelon"), {
    "id": ident("avenue of approach", "the order"),
    "name": name("avenue of approach"),
    "measures": measures_ref("give the path of the avenue of approach"),
    "echelon": (choice(*ECHELONS), d.enum("largest echelon that the avenue of approach can hold")),
    "direction": (choice(*DIRECTIONS), d.enum("direction of movement on the avenue of approach")),
}, ("id", "name"))
define("Terrain", d.entity("Terrain", "the terrain data of the area of operations"), {
    "key_terrain": (many("KeyTerrain"), d.list_of("areas and points of key terrain")),
    "avenues_of_approach": (many("AvenueOfApproach"), d.list_of("avenues of approach")),
    "summary": summary("the effects of the terrain on the operation"),
})
define("Temperature", d.entity("Temperature", "a temperature with its unit"), {
    "value": (number(), d.statement("This field gives the value of the temperature, in the unit of `unit`")),
    "unit": (choice("C", "F"), d.enum("unit of the temperature, `C` or `F`")),
}, ("value", "unit"))
define("WeatherForecast", d.entity("Weather forecast", "the forecast weather for one time interval"), {
    "window": window("the forecast is applicable"),
    "ceiling": (common("Altitude"), d.quantity("lowest cloud ceiling", "Altitude")),
    "visibility": (common("Length"), d.quantity("horizontal visibility", "Length")),
    "wind_direction": (common("Bearing"), d.quantity("direction from which the wind blows", "Bearing")),
    "wind_speed": (common("Speed"), d.quantity("speed of the wind", "Speed")),
    "temperature": (local("Temperature"), d.statement("This field gives the temperature at the surface, with its unit")),
    "precipitation": (choice("none", "rain", "drizzle", "snow", "hail", "thunderstorm"), d.enum("type of precipitation")),
    "effects": (string(), d.text("effects of the weather on the operation")),
}, ("window",))
define("LightData", d.entity("Light data", "the times of sunrise, sunset, moonrise and moonset for one day of the operation"), {
    "date": (string(format="date"), d.statement("This field gives the date of the light data, as a `YYYY-MM-DD` date")),
    "begin_morning_nautical_twilight": when("the begin morning nautical twilight"),
    "sunrise": when("sunrise"),
    "sunset": when("sunset"),
    "end_evening_nautical_twilight": when("the end evening nautical twilight"),
    "moonrise": when("moonrise"),
    "moonset": when("moonset"),
    "moon_illumination_percent": (integer(0, 100), d.quantity("illumination of the moon", None, "percent")),
}, ("date",))
define("Weather", d.entity("Weather", "the weather data of the area of operations"), {
    "forecasts": (many("WeatherForecast"), d.list_of("weather forecasts", None, ordered=True)),
    "light_data": (many("LightData"), d.list_of("light data for each day", None, ordered=True)),
    "summary": summary("the effects of the weather on the operation"),
})
define("AreaOfOperations", d.entity("Area of operations", "the area of operations of the unit, with its terrain and weather"), {
    "measures": measures_ref("give the area of operations and its boundaries"),
    "terrain": (local("Terrain"), d.statement("This field gives the terrain data of the area of operations")),
    "weather": (local("Weather"), d.statement("This field gives the weather data of the area of operations")),
    "summary": summary("the area of operations"),
})
define("EnemyUnit", d.entity("Enemy unit", "one enemy unit, with its composition, disposition and strength"), {
    "id": ident("enemy unit", "the order"),
    "name": name("enemy unit"),
    "unit_type": (string(), d.text("type of the enemy unit")),
    "echelon": (choice(*ECHELONS), d.enum("echelon of the enemy unit")),
    "strength_percent": (integer(0, 100), d.quantity("strength of the enemy unit", None, "percent of its full strength")),
    "position": position("the enemy unit"),
    "measure": measure_ref("gives the area of the enemy unit"),
    "threats": (refs("threats"), d.references("threats of the resource catalogue", "this enemy unit has")),
    "emitters": (refs("emitters"), d.references("emitters of the resource catalogue", "this enemy unit operates")),
    "targets": (refs("targets"), d.references("targets of the resource catalogue", "are parts of this enemy unit")),
    "as_of": when("the data about the enemy unit"),
}, ("id", "name"))
define("EnemyCourseOfAction", d.entity("Enemy course of action", "one COA that the enemy can use"), {
    "id": ident("enemy COA", "the order"),
    "kind": (choice("most_likely", "most_dangerous", "other"), d.enum("type of the enemy COA")),
    "name": name("enemy COA"),
    "measures": measures_ref("the enemy COA refers to"),
    "summary": summary("the enemy COA"),
}, ("id", "kind"))
define("EnemyForces", d.entity("Enemy forces", "the enemy units and the courses of action that they can use"), {
    "units": (many("EnemyUnit"), d.list_of("enemy units")),
    "courses_of_action": (many("EnemyCourseOfAction"), d.list_of("courses of action that the enemy can use")),
    "summary": summary("the enemy forces and their capabilities"),
})
define("HigherHeadquarters", d.entity("Higher headquarters", "the mission and intent of one higher headquarters"), {
    "name": name("headquarters"),
    "order": (common("DocumentRef"), d.reference("order of the higher headquarters", None)),
    "mission": (string(), d.text("mission statement of the higher headquarters")),
    "commanders_intent": (string(), d.text("intent of the commander of the higher headquarters")),
    "concept_of_operations": (string(), d.text("concept of operations of the higher headquarters")),
}, ("name",))
define("AdjacentUnit", d.entity("Adjacent unit", "one adjacent unit and its mission"), {
    "id": ident("adjacent unit", "the order"),
    "name": name("adjacent unit"),
    "direction": (choice(*DIRECTIONS), d.enum("direction from this unit to the adjacent unit")),
    "boundary": measure_ref("is the boundary with the adjacent unit"),
    "agency": agency_ref("controls the adjacent unit"),
    "mission": (string(), d.text("mission of the adjacent unit")),
}, ("id", "name"))
define("FriendlyForces", d.entity("Friendly forces", "the higher headquarters, the adjacent units and the agencies that support the unit"), {
    "higher_two_levels": (local("HigherHeadquarters"), d.statement("This field gives the headquarters two levels above the unit")),
    "higher_one_level": (local("HigherHeadquarters"), d.statement("This field gives the headquarters one level above the unit")),
    "adjacent_units": (many("AdjacentUnit"), d.list_of("adjacent units")),
    "supporting_agencies": agencies_ref("support the operation"),
})
define("InteragencyOrganization", d.entity("Interagency organization", "one organization that is not part of the armed forces and that has a part in the operation"), {
    "id": ident("organization", "the order"),
    "name": name("organization"),
    "kind": (choice("interagency", "intergovernmental", "nongovernmental"), d.enum("type of the organization")),
    "objectives": (texts(), d.list_of("objectives of the organization")),
    "position": position("the office of the organization"),
    "liaison": unit_ref("is the liaison to the organization"),
    "channels": channels_ref("the organization uses for coordination"),
}, ("id", "name", "kind"))
define("CivilConsideration", d.entity("Entry of the civil considerations", "one entry of the civil considerations, with its ASCOPE class"), {
    "id": ident("entry", "the order"),
    "category": (choice("areas", "structures", "capabilities", "organizations", "people", "events"), d.enum("ASCOPE class of the entry")),
    "name": name("entry"),
    "position": position("the entry"),
    "measure": measure_ref("gives the area of the entry"),
    "window": window("the event occurs"),
    "significance": (string(), d.text("effect of the entry on the operation")),
}, ("id", "category", "name"))
define("CivilConsiderations", d.entity("Civil considerations", "the very important parts of the situation of the population"), {
    "entries": (many("CivilConsideration"), d.list_of("civil considerations")),
    "summary": summary("the situation of the population"),
})
define("AttachmentDetachment", d.entity("Attachment or detachment", "one change of the headquarters of a unit"), {
    "unit": unit_ref("goes to a different headquarters"),
    "action": (choice("attach", "detach"), d.enum("type of the change, attachment or detachment")),
    "relationship": (choice(*RELATIONSHIPS), d.enum("command or support relationship after the change")),
    "headquarters": (string(), d.text("name of the headquarters that receives or releases the unit")),
    "effective": when("the change"),
    "phase": phase_ref("the change occurs in"),
}, ("unit", "action"))
define("Assumption", d.entity("Assumption", "one assumption of the plan"), {
    "id": ident("assumption", "the order"),
    "assumption": (string(), d.text("assumption")),
}, ("id", "assumption"))
define("Situation", d.entity("Situation", "paragraph 1 of the order"), {
    "area_of_interest": (local("AreaOfInterest"), d.statement("This field gives the area of interest")),
    "area_of_operations": (local("AreaOfOperations"), d.statement("This field gives the area of operations, with its terrain and weather")),
    "enemy_forces": (local("EnemyForces"), d.statement("This field gives the enemy forces")),
    "friendly_forces": (local("FriendlyForces"), d.statement("This field gives the friendly forces")),
    "interagency_organizations": (many("InteragencyOrganization"), d.list_of("organizations that are not part of the armed forces")),
    "civil_considerations": (local("CivilConsiderations"), d.statement("This field gives the civil considerations")),
    "attachments_and_detachments": (many("AttachmentDetachment"), d.list_of("attachments and detachments")),
    "assumptions": (many("Assumption"), d.list_of("assumptions of the plan")),
})

# ---- Paragraph 2: Mission ------------------------------------------------------------------------------
define("MissionParagraph", d.entity("Mission", "paragraph 2 of the order: the units, the task, the time, the area and the purpose"), {
    "statement": (string(), d.text("mission statement")),
    "units": units_ref("do the mission"),
    "task": (string(), d.text("task of the mission")),
    "purpose": (string(), d.text("purpose of the mission")),
    "window": window("the unit does the mission"),
    "objectives": measures_ref("are the objectives of the mission"),
}, ("statement",))

# ---- Paragraph 3: Execution ----------------------------------------------------------------------------
define("KeyTask", d.entity("Key task", "one key task of the intent of the commander"), {
    "id": ident("key task", "the order"),
    "task": (string(), d.text("key task")),
    "measures": measures_ref("the key task refers to"),
}, ("id", "task"))
define("EndStateCondition", d.entity("End state condition", "one condition of the end state"), {
    "id": ident("condition", "the end state"),
    "domain": (choice("enemy", "terrain", "friendly", "civil"), d.enum("part of the situation that the condition refers to")),
    "condition": (string(), d.text("condition")),
}, ("id", "condition"))
define("EndState", d.entity("End state", "the conditions that the operation sets at its end"), {
    "conditions": (many("EndStateCondition"), d.list_of("conditions of the end state")),
    "summary": summary("the end state"),
})
define("CommandersIntent", d.entity("Commander's intent", "the purpose, key tasks and end state of the operation"), {
    "purpose": (string(), d.text("expanded purpose of the operation")),
    "key_tasks": (many("KeyTask"), d.list_of("key tasks")),
    "end_state": (local("EndState"), d.statement("This field gives the end state")),
}, ("purpose",))
define("Phase", d.entity("Phase", "one phase of the concept of operations"), {
    "id": ident("phase", "the order"),
    "number": (integer(1), d.statement("This field gives the number of the phase", "The order writes the number as a Roman numeral")),
    "name": name("phase"),
    "start": when("the start of the phase"),
    "end": when("the end of the phase"),
    "start_condition": (string(), d.text("condition that starts the phase")),
    "end_condition": (string(), d.text("condition that completes the phase")),
    "main_effort": unit_ref("is the main effort in the phase"),
    "measures": measures_ref("the phase refers to"),
    "ato_missions": missions_ref("are in the phase"),
    "summary": summary("the phase"),
}, ("id", "number", "name"))
define("ConceptOfOperations", d.entity("Concept of operations", "the sequence of tasks of the force, with its main effort, areas and phases"), {
    "main_effort": unit_ref("is the main effort"),
    "supporting_efforts": units_ref("are supporting efforts of the operation"),
    "reserve": unit_ref("is the reserve"),
    "deep_area": measure_ref("gives the deep area"),
    "close_area": measure_ref("gives the close area"),
    "rear_area": measure_ref("gives the rear area"),
    "phases": (many("Phase"), d.list_of("phases of the operation", None, ordered=True)),
    "summary": summary("the concept of operations"),
})

SCHEMES = {
    "SchemeOfManeuver": ("scheme of manoeuvre", "the employment of the manoeuvre units", {
        "reserve": unit_ref("is the reserve"),
        "reserve_priorities": (many("Priority"), d.list_of("priorities of the reserve")),
    }),
    "SchemeOfIntelligence": ("scheme of intelligence", "the intelligence support to the operation", {
        "priority_of_effort": (items(choice("situation_development", "targeting", "assessment"), 0, True),
                               d.list_of("intelligence tasks, in the sequence of priority", None, ordered=True)),
    }),
    "SchemeOfInformationCollection": ("scheme of information collection", "the reconnaissance and surveillance tasks", {
        "reconnaissance_objectives": measures_ref("are the primary reconnaissance objectives"),
        "ato_missions": missions_ref("do reconnaissance or surveillance"),
    }),
    "SchemeOfFires": ("scheme of fires", "the priorities, allocation and restrictions of fires", {
        "air_support": missions_ref("give air support"),
        "restrictions": (many("Instruction"), d.list_of("restrictions on fires")),
    }),
    "SchemeOfProtection": ("scheme of protection", "the priorities of protection by unit and area", {
        "reaction_forces": units_ref("are reaction forces"),
    }),
    "SchemeOfEngineering": ("scheme of engineering", "the mobility, countermobility, survivability, general and geospatial engineering tasks", {}),
    "SchemeOfAirAndMissileDefense": ("scheme of air and missile defence", "the priorities, allocation and restrictions of air defence", {
        "weapons_control_status": (choice("free", "tight", "hold"), d.enum("weapons control status at the start of the operation")),
        "air_defense_warning": (choice("white", "yellow", "red"), d.enum("air defence warning at the start of the operation")),
        "engagement_authority": agency_ref("has the engagement authority"),
    }),
    "SchemeOfAirspaceControl": ("scheme of airspace control", "the control of the airspace above the area of operations", {
        "agencies": agencies_ref("control the airspace"),
        "coordinating_altitude": measure_ref("gives the coordinating altitude", ["acm"]),
    }),
}
for _name, (_title, _what, _extra) in SCHEMES.items():
    define(_name, d.entity(_title[0].upper() + _title[1:], "the part of the concept of operations that gives " + _what), {
        "priorities": (many("Priority"), d.list_of("priorities of the " + _title)),
        "phases": phases_ref("the " + _title + " gives data for"),
        "units": units_ref("do the " + _title),
        "measures": measures_ref("the " + _title + " refers to"),
        **_extra,
        "summary": summary("the " + _title),
    })
define("Schemes", d.entity("Schemes", "the schemes of support that the concept of operations contains"), {
    "maneuver": (local("SchemeOfManeuver"), d.statement("This field gives the scheme of manoeuvre")),
    "intelligence": (local("SchemeOfIntelligence"), d.statement("This field gives the scheme of intelligence")),
    "information_collection": (local("SchemeOfInformationCollection"), d.statement("This field gives the scheme of information collection")),
    "fires": (local("SchemeOfFires"), d.statement("This field gives the scheme of fires")),
    "protection": (local("SchemeOfProtection"), d.statement("This field gives the scheme of protection")),
    "engineering": (local("SchemeOfEngineering"), d.statement("This field gives the scheme of engineering")),
    "air_and_missile_defense": (local("SchemeOfAirAndMissileDefense"), d.statement("This field gives the scheme of air and missile defence")),
    "airspace_control": (local("SchemeOfAirspaceControl"), d.statement("This field gives the scheme of airspace control")),
})
define("UnitTasks", d.entity("Tasks to a unit", "the tasks to one subordinate unit"), {
    "unit": unit_ref("receives the tasks"),
    "tasks": (many("Task", 1), d.list_of("tasks to the unit")),
}, ("unit", "tasks"))
define("InformationRequirement", d.entity("Information requirement", "one PIR or FFIR of the CCIR"), {
    "id": ident("requirement", "the order"),
    "number": (string(), d.text("number of the requirement, such as `PIR 1`")),
    "question": (string(), d.text("requirement, as a question")),
    "indicators": (texts(), d.list_of("indicators that give data for the requirement")),
    "measures": measures_ref("the requirement refers to, such as named areas of interest"),
    "decision_point": (ref(ORDER_DECISION_POINTS), d.reference("decision point", "the requirement supports")),
    "latest_time": when("the last time at which the information is of value"),
    "report_to": agency_ref("receives the reports"),
}, ("id", "question"))
define("CCIR", d.entity("Commander's critical information requirements", "the PIR and FFIR lists"), {
    "priority_intelligence_requirements": (many("InformationRequirement"), d.list_of("PIR entries", None, ordered=True)),
    "friendly_force_information_requirements": (many("InformationRequirement"), d.list_of("FFIR entries", None, ordered=True)),
})
define("EEFI", d.entity("Essential element of friendly information", "one item of friendly information that the operation keeps from the enemy"), {
    "id": ident("item", "the order"),
    "item": (string(), d.text("item of friendly information")),
}, ("id", "item"))
define("RiskReduction", d.entity("Risk reduction measures", "the risk controls of the operation that the unit procedures do not include"), {
    "mopp_level": (choice("mopp_ready", "mopp_0", "mopp_1", "mopp_2", "mopp_3", "mopp_4"), d.enum("protective posture against CBRN hazards")),
    "emission_control": (choice("unrestricted", "reduced", "minimum", "silent"), d.enum("emission control level")),
    "fratricide_measures": measures_ref("prevent fratricide"),
    "instructions": (many("Instruction"), d.list_of("other risk controls")),
})
define("PersonnelRecoveryMeasures", d.entity("Measures for personnel recovery", "the measures for personnel recovery in the operation"), {
    "recovery_forces": missions_ref("are personnel recovery forces"),
    "agency": agency_ref("controls personnel recovery"),
    "channels": channels_ref("are for isolated personnel and recovery forces"),
    "measures": measures_ref("the recovery refers to, such as safe areas and contact points"),
    "summary": summary("the instructions for isolated personnel"),
})
define("CoordinatingInstructions", d.entity("Coordinating instructions", "the instructions and tasks that are applicable to two or more units"), {
    "effective_time": when("the start of the effect of the order"),
    "effective_condition": (string(), d.text("condition that starts the effect of the order, when there is no time")),
    "timeline": (many("TimelineEvent"), d.list_of("very important times and events", None, ordered=True)),
    "ccir": (local("CCIR"), d.statement("This field gives the CCIR")),
    "eefi": (many("EEFI"), d.list_of("essential elements of friendly information")),
    "fire_support_coordination_measures": measures_ref("are FSCM entries that two or more units use", ["fscm"]),
    "airspace_coordinating_measures": measures_ref("are airspace coordinating measures that two or more units use", AIRSPACE_CATEGORIES),
    "rules_of_engagement": (many("RoeRule"), d.list_of("ROE")),
    "risk_reduction": (local("RiskReduction"), d.statement("This field gives the risk reduction measures")),
    "personnel_recovery": (local("PersonnelRecoveryMeasures"), d.statement("This field gives the measures for personnel recovery")),
    "themes_and_messages": (many("Message"), d.list_of("themes and messages")),
    "other": (many("Instruction"), d.list_of("other coordinating instructions")),
})
define("Execution", d.entity("Execution", "paragraph 3 of the order"), {
    "commanders_intent": (local("CommandersIntent"), d.statement("This field gives the intent of the commander")),
    "concept_of_operations": (local("ConceptOfOperations"), d.statement("This field gives the concept of operations")),
    "schemes": (local("Schemes"), d.statement("This field gives the schemes of support")),
    "tasks_to_subordinate_units": (many("UnitTasks"), d.list_of("tasks to subordinate units", None, "The units are in the sequence of the task organization", ordered=True)),
    "coordinating_instructions": (local("CoordinatingInstructions"), d.statement("This field gives the coordinating instructions")),
})

# ---- Paragraph 4: Sustainment ------------------------------------------------------------------------
define("SupplyPoint", d.entity("Supply point", "one point where units get supplies or services"), {
    "id": ident("supply point", "the order"),
    "name": name("supply point"),
    "kind": (choice("ammunition_transfer_point", "ammunition_supply_point", "fuel_point", "water_point", "ration_point",
                    "maintenance_collection_point", "logistics_release_point", "forward_arming_and_refuelling_point", "supply_support_activity"),
             d.enum("type of the supply point")),
    "classes": (items(choice(*SUPPLY_CLASSES), 0, True), d.list_of("classes of supply at the point")),
    "position": position("the supply point"),
    "airfield": airfield_ref("has the supply point"),
    "unit": unit_ref("operates the supply point"),
    "window": window("the supply point operates"),
}, ("id", "name", "kind"), any_of=("position", "airfield"))
define("Logistics", d.entity("Logistics", "the logistics plan of the order"), {
    "supply_points": (many("SupplyPoint"), d.list_of("supply points")),
    "routes": (refs("routes"), d.references("supply routes of the resource catalogue", "the units follow")),
    "priorities": (many("Priority"), d.list_of("priorities of logistics support")),
    "summary": summary("the logistics plan"),
})
define("Personnel", d.entity("Personnel support", "the personnel support plan of the order"), {
    "strength_report": (ref("reports"), d.reference("report of the resource catalogue", "gives the personnel strength")),
    "casualty_report": (ref("reports"), d.reference("report of the resource catalogue", "gives the casualties")),
    "summary": summary("the personnel support"),
})
define("MedicalFacility", d.entity("Medical treatment facility", "one medical facility and its role of care"), {
    "id": ident("facility", "the order"),
    "name": name("facility"),
    "role": (integer(1, 4), d.statement("This field gives the role of care of the facility, from 1 to 4")),
    "position": position("the facility"),
    "airfield": airfield_ref("has the facility"),
    "unit": unit_ref("operates the facility"),
}, ("id", "name", "role"))
define("ExchangePoint", d.entity("Ambulance exchange point", "one point where casualties change from one ambulance to a different ambulance"), {
    "id": ident("ambulance exchange point", "the order"),
    "name": name("ambulance exchange point"),
    "position": position("the ambulance exchange point"),
    "measure": measure_ref("gives the ambulance exchange point"),
}, ("id", "name"), any_of=("position", "measure"))
define("MedicalEvacuation", d.entity("Medical evacuation", "the medical evacuation plan of the order"), {
    "agency": agency_ref("receives medical evacuation requests"),
    "request_channels": channels_ref("units send medical evacuation requests on"),
    "exchange_points": (many("ExchangePoint"), d.list_of("ambulance exchange points")),
    "ato_missions": missions_ref("are medical evacuation aircraft"),
    "summary": summary("the medical evacuation plan"),
})
define("HealthServiceSupport", d.entity("Health service support", "the medical support plan of the order"), {
    "facilities": (many("MedicalFacility"), d.list_of("medical treatment facilities")),
    "evacuation": (local("MedicalEvacuation"), d.statement("This field gives the medical evacuation plan")),
    "summary": summary("the health service support"),
})
define("Money", d.entity("Value in a currency", "a value with its currency"), {
    "amount": (number(0), d.statement("This field gives the value, in the currency of `currency`")),
    "currency": (string(pattern=r"^[A-Z]{3}$"), d.statement("This field gives the currency, as a code of `ISO 4217` such as `USD`")),
}, ("amount", "currency"))
define("FundingProgram", d.entity("Program of funds", "one source of funds for the operation"), {
    "id": ident("program", "the order"),
    "name": name("program"),
    "unit": unit_ref("controls the funds"),
    "limit": (local("Money"), d.statement("This field gives the maximum value of the program")),
}, ("id", "name"))
define("FinancialManagement", d.entity("Financial management", "the plan for the funds of the order"), {
    "programs": (many("FundingProgram"), d.list_of("programs of funds")),
    "summary": summary("the financial management support"),
})
define("Sustainment", d.entity("Sustainment", "paragraph 4 of the order"), {
    "priorities": (many("Priority"), d.list_of("priorities of sustainment by unit or area")),
    "logistics": (local("Logistics"), d.statement("This field gives the logistics plan")),
    "personnel": (local("Personnel"), d.statement("This field gives the personnel support plan")),
    "health_service_support": (local("HealthServiceSupport"), d.statement("This field gives the plan for health service support")),
    "financial_management": (local("FinancialManagement"), d.statement("This field gives the financial management plan")),
    "summary": summary("the scheme of sustainment"),
})

# ---- Paragraph 5: Command and signal ---------------------------------------------------------------
define("LeaderLocation", d.entity("Leader location", "the location of the commander or of one key leader"), {
    "role": (string(), d.text("role of the leader, such as `commander`")),
    "unit": unit_ref("the leader is in"),
    "command_post": (ref(ORDER_COMMAND_POSTS), d.reference("command post", "the leader is at")),
    "position": position("the leader"),
    "phase": phase_ref("the location is applicable to"),
}, ("role",), any_of=("command_post", "position"))
define("Liaison", d.entity("Liaison requirement", "one liaison element of the operation"), {
    "id": ident("liaison element", "the order"),
    "unit": unit_ref("sends the liaison element"),
    "headquarters": (string(), d.text("name of the headquarters that receives the liaison element")),
    "agency": agency_ref("receives the liaison element"),
    "position": position("the liaison element"),
}, ("id",), any_of=("headquarters", "agency"))
define("Command", d.entity("Command", "the location of the leaders and the succession of command"), {
    "leaders": (many("LeaderLocation"), d.list_of("locations of the commander and key leaders")),
    "succession": (refs(ORDER_UNITS), d.references("units of the task organization", None, "The list gives the succession of command, in order")),
    "liaison": (many("Liaison"), d.list_of("liaison requirements")),
})
define("CommandPost", d.entity("Command post", "one command post, its location and the time when it operates"), {
    "id": ident("command post", "the order"),
    "name": name("command post"),
    "kind": (choice("main", "tactical", "rear", "support_area", "early_entry", "mobile_command_group", "alternate"), d.enum("type of the command post")),
    "unit": unit_ref("the command post is for"),
    "agency": agency_ref("the command post operates as"),
    "position": position("the command post"),
    "operational": window("the command post operates"),
    "controls": phases_ref("the command post controls"),
}, ("id", "name", "kind"))
define("PaceMeans", d.entity("Communication method", "one method of a PACE plan"), {
    "method": (choice("voice_hf", "voice_vhf", "voice_uhf", "voice_fm", "satellite", "data_link", "chat", "telephone", "messenger", "visual"),
               d.enum("type of the method")),
    "channel": channel_ref("the method refers to"),
}, ("method",))
define("PacePlan", d.entity("PACE plan", "the methods of communication for one function, in the PACE sequence"), {
    "id": ident("plan", "the order"),
    "function": (string(), d.text("function or net of the plan, such as `command`")),
    "primary": (local("PaceMeans"), d.statement("This field gives the primary method")),
    "alternate": (local("PaceMeans"), d.statement("This field gives the alternate method")),
    "contingency": (local("PaceMeans"), d.statement("This field gives the contingency method")),
    "emergency": (local("PaceMeans"), d.statement("This field gives the emergency method")),
}, ("id", "function", "primary"))
define("Signal", d.entity("Signal", "the concept of signal support"), {
    "pace_plans": (many("PacePlan"), d.list_of("PACE plans")),
    "channels": channels_ref("the order refers to"),
    "summary": summary("the concept of signal support"),
})
define("CommandAndSignal", d.entity("Command and signal", "paragraph 5 of the order"), {
    "command": (local("Command"), d.statement("This field gives the command data")),
    "command_posts": (many("CommandPost"), d.list_of("command posts")),
    "signal": (local("Signal"), d.statement("This field gives the signal data")),
})
define("Acknowledgement", d.entity("Acknowledgement", "the instructions for the acknowledgement of the order"), {
    "acknowledge": (boolean(), d.flag("each addressee acknowledges the order")),
    "instructions": (string(), d.text("instructions for the acknowledgement")),
}, ("acknowledge",))
define("Authentication", d.entity("Authentication", "the signature block of the order"), {
    "commander_name": (string(), d.text("last name of the commander")),
    "commander_rank": (string(), d.text("rank of the commander")),
    "authenticator_name": (string(), d.text("name of the staff officer who authenticates the order")),
    "authenticator_position": (string(), d.text("position of the staff officer who authenticates the order")),
}, ("commander_name",))
