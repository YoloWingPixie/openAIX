"""Typed mission-briefing data for every ATO tasking, and the AI, SCAR, FAC(A), air assault and airdrop roles.

Each tasking carries an optional `brief`: the typed data that crews are briefed on to fly the mission.
A brief refers to resource-catalogue records (agencies, channels, control measures, routes, procedures,
reports, targets, threats, stores) and to other missions and flights; it does not copy them. Narrative
text is only in `remarks`. Doctrinal sources and locators are in sources/planning-field-inventory.json;
descriptions come from describe/tables/ato.py.

- Air interdiction (AI) is a `preplanned_attack` role. SCAR and FAC(A) are the two mission types of the
  `counterland_control` family. Air assault and airdrop are `transport` roles.
- Fields that the tasking already owns (area, altitude block, windows, receivers, targets of attack
  assignments) stay on the tasking; the brief adds only what the tasking does not hold.
"""
from copy import deepcopy

# JP 3-09.3 (2014) Figure V-4, CAS check-in briefing (MNPOPCA).
CHECK_IN_ITEMS = ("mission_number", "aircraft_number_and_type", "position_and_altitude", "ordnance",
                  "time_on_station", "capabilities", "abort_code")
# JP 3-09.3 (2014) Chapter III, paragraph on marks (page III-77): laser, infrared pointer, smoke, indirect fire,
# tracer and talk-on.
MARKS = ("laser", "infrared_pointer", "smoke", "indirect_fire", "tracer", "talk_on")
TERMINAL_CONTROL = ("type_1", "type_2", "type_3")
# openAIX planning values for SCAR target priorities; no doctrinal code list.
TARGET_CATEGORIES = ("armor", "artillery", "air_defense", "missile_launcher", "logistics_vehicle", "command_post",
                     "personnel", "infrastructure", "other")
FUZE_FUNCTIONS = ("instantaneous", "delay", "proximity", "airburst")
BDA_METHODS = ("weapon_system_video", "visual", "imagery", "sensor_report")
REPORT_METHODS = ("voice", "datalink", "chat", "imagery_transfer", "debrief")
SENSORS = ("electro_optical", "infrared", "electro_optical_infrared", "radar", "synthetic_aperture_radar",
           "signals", "visual", "other")
PRODUCTS = ("full_motion_video", "still_imagery", "coordinates", "voice_report", "written_report", "signals_report")
RENDEZVOUS = ("point_parallel", "en_route", "anchor")
# FM 3-21.38 (2006) paragraphs 6-30 and 6-48: release methods and drop zone markings; FM 3-99 paragraph 5-18:
# container delivery, heavy drop, door bundles and precision airdrop.
RELEASE_METHODS = ("carp", "harp", "gmrs", "virs")
DROP_LOADS = ("personnel", "heavy_equipment", "container_delivery_system", "door_bundle", "precision_airdrop")
PARACHUTE_TECHNIQUES = ("static_line", "halo", "haho")
DZ_MARKINGS = ("raised_angle_marker", "code_letter", "panels", "lights", "smoke")
CLEAR_TO_DROP = ("radio", "smoke", "code_letter", "light")
# FM 3-99 (2015, incl. C1) Chapter 11 landing formations.
LANDING_FORMATIONS = ("trail", "staggered_trail", "echelon", "vee", "diamond", "heavy")
SURVIVOR_CONDITIONS = ("uninjured", "injured", "unknown")
HOLDING_KINDS = ["ORBIT", "POINT", "ROZ"]
FRIENDLY_LINES = ["FLOT", "FEBA", "PL", "LOA", "LD", "BOUNDARY"]
CORRIDORS = ["AIRCOR", "SAAFR", "MRR", "TMRR", "LLTR", "SC"]

TRANSPORT_ROLES = ("air_assault", "airdrop")


def enrich_briefs(artifacts, common):
    ato = artifacts["schemas/ato.schema.json"]
    defs = ato["$defs"]
    catalogue = artifacts["catalogues/control-measures.json"]
    resources = artifacts["schemas/resources.schema.json"]["$id"]
    fscm = sorted(entry["code"] for entry in catalogue["types"] if entry["category"] == "fscm") + ["ACA"]

    def c(name):
        return {"$ref": common + "#/$defs/" + name}

    def local(name):
        return {"$ref": "#/$defs/" + name}

    def text():
        return {"type": "string", "minLength": 1}

    def ident(collection=None):
        node = c("Identifier")
        if collection:
            node["x-catalog"] = collection
        return node

    def array(items, minimum=None, unique=True):
        node = {"type": "array", "items": items}
        if minimum:
            node["minItems"] = minimum
        if unique:
            node["uniqueItems"] = True
        return node

    def idents(collection, minimum=None):
        return array(ident(collection), minimum)

    def enum(values):
        return {"enum": list(values)}

    def enums(values, minimum=None):
        return array(enum(values), minimum)

    def integer(minimum=1):
        return {"type": "integer", "minimum": minimum}

    def obj(properties, required=()):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required)}

    def sel(kinds, roles=None):
        node = c("ControlMeasureSelection") | {"x-measure-kinds": list(kinds)}
        if roles:
            node["x-point-roles"] = list(roles)
        return node

    def sels(kinds, roles=None, minimum=None):
        return array(sel(kinds, roles), minimum)

    def area():
        node = deepcopy(defs["Patrol"]["properties"]["area"])
        node.pop("description", None)
        return node

    # ---- Shared pieces ---------------------------------------------------------------------------
    defs["ControllerContact"] = obj({"agency": ident("agencies"), "channel": ident("channels"),
                                     "alternate_channel": ident("channels")}, ("agency",))
    defs["ReportingPlan"] = obj({"reports": idents("reports"), "recipient": ident("agencies"), "channel": ident("channels"),
                                 "method": enum(REPORT_METHODS), "deadline": c("DateTime")})
    defs["BDARequirement"] = obj({"method": enum(BDA_METHODS), "report": ident("reports"), "recipient": ident("agencies"),
                                  "deadline": c("DateTime")}, ("method",))
    defs["EmitterTarget"] = obj({"emitter": ident("emitters"), "target": ident("targets"), "priority": integer()}, ("emitter",))
    defs["CheckIn"] = obj({"procedure": ident("procedures"), "items": enums(CHECK_IN_ITEMS), "abort_code": text()})
    defs["Fuze"] = obj({"function": enum(FUZE_FUNCTIONS), "delay_ms": {"type": "number", "minimum": 0},
                        "height_of_burst": c("Length")}, ("function",))
    defs["WeaponLoad"] = obj({"flight": ident("flights"), "store": ident("stores"), "quantity": integer(),
                              "fuze": local("Fuze"), "laser_code": c("LaserCode"), "release_altitude": local("Altitude"),
                              "attack_heading": c("Bearing")}, ("store",))
    defs["TargetListEntry"] = obj({"document": local("DocumentRef"), "entry": text()}, ("document", "entry"))

    cas_fields = {
        "controllers": array(local("ControllerContact"), 1),
        "contact_points": sels(["POINT"], ["control"]),
        "initial_points": sels(["POINT"], ["initial"]),
        "holding": sels(HOLDING_KINDS),
        "holding_altitude": local("AltitudeBlock"),
        "fire_support_measures": sels(fscm),
        "friendly_lines": sels(FRIENDLY_LINES),
        "ground_scheme_summary": text(),
        "laser_codes": array(c("LaserCode")),
        "marks": enums(MARKS),
        "remarks": text(),
    }
    defs["CASBrief"] = obj({**deepcopy(cas_fields), "check_in": local("CheckIn")})
    defs["SEADBrief"] = obj({"emitters": array(local("EmitterTarget"), 1), "employment_procedure": ident("procedures"),
                             "protected_missions": idents("missions"), "suppression_window": local("Window")})
    defs["AttackBrief"] = obj({
        "initial_points": sels(["POINT"], ["initial"]),
        "egress_points": sels(["POINT"], ["egress", "gate"]),
        "ingress_route": ident("routes"), "egress_route": ident("routes"),
        "restricted_areas": sels(["NFA", "RFA", "NFZ"]),
        "threat_emitters": idents("emitters"),
        "bda": local("BDARequirement"),
        "sead": local("SEADBrief"),
        "cas": local("CASBrief"),
        "remarks": text(),
    })
    defs["SCARBrief"] = obj({
        "controller": local("ControllerContact"),
        "attack_missions": idents("missions"),
        "target_priorities": array(obj({"category": enum(TARGET_CATEGORIES), "priority": integer()}, ("category", "priority"))),
        "entry_points": sels(["POINT"], ["control", "ingress", "gate"]),
        "holding": sels(HOLDING_KINDS),
        "stack": array(obj({"altitude": local("AltitudeBlock"), "mission": ident("missions")}, ("altitude", "mission"))),
        "reporting": local("ReportingPlan"),
        "remarks": text(),
    })
    defs["FACABrief"] = obj({**deepcopy(cas_fields), "supported_unit": text(), "cas_missions": idents("missions"),
                             "terminal_control": enums(TERMINAL_CONTROL)})
    defs["CommitCriterion"] = obj({"threat": ident("threats"), "range": c("Length"), "boundary": c("ControlMeasureSelection"),
                                   "procedure": ident("procedures")})
    defs["CommitCriterion"]["anyOf"] = [{"required": ["range"]}, {"required": ["boundary"]}, {"required": ["procedure"]}]
    defs["AirToAirBrief"] = obj({
        "controller": local("ControllerContact"),
        "bullseye": sel(["POINT"], ["bullseye"]),
        "commit_criteria": array(local("CommitCriterion")),
        "identification_procedure": ident("procedures"),
        "roe_reference": local("DocumentRef"),
        "protected_missions": idents("missions"),
        "protected_measures": sels(["ORBIT", "AARA", "AEWA"]),
        "threat_emitters": idents("emitters"),
        "remarks": text(),
    })
    defs["RefuelingBrief"] = obj({
        "anchor": sel(["ORBIT", "POINT", "AARA"]),
        "rendezvous": enum(RENDEZVOUS),
        "rendezvous_point": sel(["POINT"]),
        "control_time": c("DateTime"),
        "receiver_altitude": local("Altitude"),
        "remarks": text(),
    })
    defs["ControlSector"] = obj({"name": text(), "area": area(), "altitude": local("AltitudeBlock"), "channel": ident("channels"),
                                 "flights": idents("flights"), "missions": idents("missions")}, ("name",))
    defs["AirborneControlBrief"] = obj({
        "orbit": sel(["ORBIT", "AEWA"]),
        "controlled_channels": idents("channels"),
        "bullseye": sel(["POINT"], ["bullseye"]),
        "sectors": array(local("ControlSector")),
        "handover_points": sels(["POINT"], ["handover", "control"]),
        "remarks": text(),
    })
    defs["ReconnaissanceBrief"] = obj({"named_areas": sels(["NAI", "TAI", "RECCE"]), "reporting": local("ReportingPlan"), "remarks": text()})
    defs["ElectromagneticBrief"] = obj({"emitters": array(local("EmitterTarget")), "orbit": sel(["ORBIT", "ROZ"]),
                                        "protected_channels": idents("channels"), "remarks": text()})
    defs["TransferPoint"] = obj({"place": ident("places"), "window": local("Window"), "procedure": ident("procedures"),
                                 "agency": ident("agencies")}, ("place",))
    defs["AirdropBrief"] = obj({
        "drop_zone": sel(["DZ"]),
        "run_in_heading": c("Bearing"),
        "release_method": enum(RELEASE_METHODS),
        "release_point": sel(["POINT"]),
        "point_of_impact": sel(["POINT"]),
        "drop_altitude": local("Altitude"),
        "drop_airspeed": local("Speed"),
        "load_type": enum(DROP_LOADS),
        "parachute_technique": enum(PARACHUTE_TECHNIQUES),
        "markings": enums(DZ_MARKINGS),
        "code_letter": {"type": "string", "pattern": "^[A-Z]$"},
        "clear_to_drop_signal": enum(CLEAR_TO_DROP),
        "authentication_procedure": ident("procedures"),
        "drop_window": local("Window"),
        "drop_zone_controller": local("ControllerContact"),
        "remarks": text(),
    }, ("drop_zone",))
    defs["AirMovementLine"] = obj({
        "line": integer(), "lift": integer(), "serial": integer(), "chalks": array(integer(), 1),
        "flight": ident("flights"), "lifted_unit": text(),
        "pickup_zone": sel(["PZ"]), "load_time": c("DateTime"), "takeoff_time": c("DateTime"),
        "start_point": sel(["POINT"]), "start_point_time": c("DateTime"),
        "release_point": sel(["POINT"]), "release_point_time": c("DateTime"),
        "landing_zone": sel(["LZ"]), "landing_time": c("DateTime"), "landing_heading": c("Bearing"),
        "landing_formation": enum(LANDING_FORMATIONS), "route": ident("routes"), "load": local("Manifest"),
        "remarks": text(),
    }, ("line", "lift", "serial", "flight", "pickup_zone", "landing_zone"))
    defs["AirAssaultBrief"] = obj({
        "pickup_zones": sels(["PZ"], minimum=1), "landing_zones": sels(["LZ"], minimum=1),
        "h_hour": c("DateTime"),
        "air_movement_table": array(local("AirMovementLine"), 1),
        "routes": idents("routes"), "corridors": sels(CORRIDORS),
        "escort_missions": idents("missions"),
        "remarks": text(),
    }, ("pickup_zones", "landing_zones"))
    defs["TransportBrief"] = obj({
        "onload": local("TransferPoint"), "offload": local("TransferPoint"),
        "load_plan": array(obj({"flight": ident("flights"), "manifest": local("Manifest")}, ("flight", "manifest"))),
        "patients": obj({"litter": integer(0), "ambulatory": integer(0), "attendants": integer(0)}),
        "airdrop": local("AirdropBrief"),
        "air_assault": local("AirAssaultBrief"),
        "remarks": text(),
    })
    defs["Survivor"] = obj({"id": ident(), "callsign": text(), "last_known": {"$ref": resources + "#/$defs/LastKnownPosition"},
                            "condition": enum(SURVIVOR_CONDITIONS), "isoprep_ref": text(),
                            "authentication_procedure": ident("procedures")}, ("id",))
    defs["PersonnelRecoveryBrief"] = obj({
        "survivors": array(local("Survivor")),
        "on_scene_commander": ident("flights"),
        "rescort_missions": idents("missions"),
        "holding": sels(HOLDING_KINDS),
        "ingress_route": ident("routes"), "egress_route": ident("routes"),
        "pickup_window": local("Window"),
        "remarks": text(),
    })
    defs["TrainingBrief"] = obj({
        "range_controller": local("ControllerContact"),
        "knock_it_off_channel": ident("channels"),
        "minimum_altitude": local("Altitude"),
        "safety_procedure": ident("procedures"),
        "training_areas": sels(["TRNG", "ROZ", "KB", "RECCE", "UAA", "AIRSPACE"]),
        "remarks": text(),
    })
    namespace = {"type": "string", "pattern": r"^[a-z][a-z0-9-]*(\.[a-z0-9-]+)+$"}
    defs["CustomBrief"] = obj({"namespace": namespace, "schema": {"type": "string", "format": "uri"},
                               "data": {"type": "object"}, "remarks": text()}, ("namespace", "data"))

    # ---- Attach a brief to every tasking ---------------------------------------------------------
    briefs = {"OnCallCAS": "CASBrief", "PreplannedAttack": "AttackBrief", "Patrol": "AirToAirBrief",
              "CounterAir": "AirToAirBrief", "Escort": "AirToAirBrief", "Refueling": "RefuelingBrief",
              "AirborneControl": "AirborneControlBrief", "Reconnaissance": "ReconnaissanceBrief",
              "ElectromagneticTask": "ElectromagneticBrief", "Transport": "TransportBrief",
              "PersonnelRecovery": "PersonnelRecoveryBrief", "Training": "TrainingBrief", "CustomTask": "CustomBrief"}
    for tasking, brief in briefs.items():
        defs[tasking]["properties"]["brief"] = local(brief)

    # ---- Roles ---------------------------------------------------------------------------------
    role = defs["PreplannedAttack"]["properties"]["role"]
    role["enum"] = [*role["enum"], "air_interdiction"]
    attack = defs["AttackAssignment"]["properties"]
    attack["weaponeering"] = array(local("WeaponLoad"))
    attack["target_list_entry"] = local("TargetListEntry")

    patrol = defs["Patrol"]["properties"]
    control = {key: deepcopy(patrol[key]) for key in ("area", "altitude", "objective", "abort_criteria", "success_criteria", "report_refs")}
    for field in control.values():
        field.pop("description", None)
    control.update({"kind": {"const": "counterland_control"}, "mission_type": enum(("scar", "fac_a")),
                    "operating_window": local("Window"), "brief": {"anyOf": [local("SCARBrief"), local("FACABrief")]}})
    defs["CounterlandControl"] = {
        "type": "object", "additionalProperties": False, "title": "Counterland control task", "properties": control,
        "required": ["kind", "mission_type", "area"],
        "allOf": [{"if": {"properties": {"mission_type": {"const": "scar"}}},
                   "then": {"properties": {"brief": local("SCARBrief")}},
                   "else": {"properties": {"brief": local("FACABrief")}}}],
    }
    tasking = defs["Mission"]["properties"]["tasking"]
    if local("CounterlandControl") not in tasking["oneOf"]:
        tasking["oneOf"].append(local("CounterlandControl"))

    transport = defs["Transport"]
    transport["properties"]["role"]["enum"] = [*transport["properties"]["role"]["enum"], *TRANSPORT_ROLES]
    transport["required"] = ["kind"]
    transport["allOf"] = [
        {"if": {"properties": {"role": {"const": "air_assault"}}, "required": ["role"]},
         "then": {"required": ["brief"], "properties": {"brief": {"required": ["air_assault"]}}}},
        {"if": {"properties": {"role": {"const": "airdrop"}}, "required": ["role"]},
         "then": {"required": ["pickup", "brief"], "properties": {"brief": {"required": ["airdrop"]}, "delivery_method": {"const": "airdrop"}}}},
        {"if": {"not": {"properties": {"role": {"enum": list(TRANSPORT_ROLES)}}, "required": ["role"]}},
         "then": {"required": ["pickup", "destination"]}},
    ]

    # ---- Typed fields that held free text ------------------------------------------------------
    defs["Contingency"]["properties"]["decision_authority"] = ident("agencies")
    defs["SCLAlternative"]["properties"]["authority"] = ident("agencies")
    requirement = defs["CollectionRequirement"]["properties"]
    requirement["sensor"] = enum(SENSORS)
    requirement["product"] = enum(PRODUCTS)
    requirement["eeis"] = array(obj({"id": ident(), "question": text(), "priority": integer()}, ("id", "question")))
    requirement["reporting"] = local("ReportingPlan")
