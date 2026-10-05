"""OIR mission briefs: the typed brief of every ATO tasking, the air interdiction, SCAR, FAC(A),
air assault and airdrop missions, and the resource-catalogue records they refer to.

examples/scenario.py merges `brief_resources()` into the shared resource catalogue and calls
`add_briefs()` on the ATO missions. Positions are on the DCS Syria map.
"""
from copy import deepcopy

from openaix.examples.aco import position, window
from openaix.sim.dcs import extension as dcs

EXERCISE = {"org.cjtf-oir.ato": {"ato_day": "214"}}
SPINS_ROE = {"id": "oir-spins", "revision": "1", "title": "OIR SPINS", "section": "ROE summary"}


def at(hhmm):
    return "2026-10-02T" + hhmm[:2] + ":" + hhmm[2:] + ":00Z"


def feet(value, reference="MSL"):
    return {"value": value, "unit": "ft", "reference": reference}


def flight_level(value):
    return {"value": value, "unit": "flight_level", "reference": "FL"}


def block(lower, upper):
    return {"lower": lower, "upper": upper}


def nm(value):
    return {"value": value, "unit": "nm"}


def magnetic(value):
    return {"value": value, "reference": "magnetic"}


def ref(identifier):
    return {"kind": "control_measure", "id": identifier}


def refs(*identifiers):
    return [ref(identifier) for identifier in identifiers]


def contact(agency, channel, alternate=None):
    result = {"agency": agency, "channel": channel}
    if alternate:
        result["alternate_channel"] = alternate
    return result


# ---------------------------------------------------------------------------------------------
# Resource-catalogue records
# ---------------------------------------------------------------------------------------------

def zone(version, identifier, name, code, center, radius, ceiling, purpose):
    return {"$schema": f"urn:openaix:schema:measure-volume:{version}", "id": identifier, "name": name, "type": code,
            "active": window(), "description": purpose, "purpose": purpose,
            "controlling_agency": "banshee", "channels": ["banshee-uhf"],
            "components": [{"id": identifier + "-volume", "name": name, "operation": "add",
                            "geometry": {"kind": "circle", "center": center, "radius": nm(radius)},
                            "lower_limit": {"surface": True}, "upper_limit": feet(ceiling, "AGL"), "active": window()}],
            "extensions": deepcopy(EXERCISE)}


def point(version, identifier, name, coordinates, roles, description):
    return {"$schema": f"urn:openaix:schema:point:{version}", "id": identifier, "name": name, "type": "POINT", "roles": roles,
            "position": coordinates, "active": window(), "description": description,
            "extensions": deepcopy(EXERCISE)}


def nfa(version, identifier, name, center, radius_m, description):
    return {"$schema": f"urn:openaix:schema:measure-area:{version}", "id": identifier, "name": name, "type": "NFA", "active": window(),
            "description": description, "geometry": {"kind": "circle", "center": center, "radius": {"value": radius_m, "unit": "m"}},
            "restrictions": ["No fires or effects into the area unless Kingpin approves each mission."], "extensions": deepcopy(EXERCISE)}


def emitters():
    """OIR air defence emitters. ALIC codes and RWR symbols: DCS F-16C Early Access Guide, Appendix B and the HARM table."""
    km = lambda value: {"value": value, "unit": "km"}  # noqa: E731
    return {
        "sa6-gainful": {"id": "sa6-gainful", "name": "Cobalt SA-6 battery (captured)", "system_id": "SA-6", "reporting_name": "Gainful",
                        "native_designation": "2K12 Kub", "radar_reporting_name": "Straight Flush", "radar_system_id": "1S91",
                        "radar_roles": ["target_acquisition", "target_illumination"], "rwr_symbol": "6",
                        "position": position(35.215, 40.265), "status": "active", "last_seen": at("1215"), "mobility": "relocatable",
                        "side": "red", "max_engagement_range": km(24), "min_engagement_range": km(4), "detection_range": km(75),
                        "engagement_floor": feet(300, "AGL"), "engagement_ceiling": feet(46000), "measures": refs("gainful-misarc"),
                        "extensions": dcs([{"kind": "group", "name": "OIR Gainful battery", "mission_id": "oir-syria", "group_category": "vehicle"}],
                                          alic_code=108),
                        "remarks": "Relocates up to 5 nautical miles after it emits; last seen on the river road north of Cobalt."},
        "sa3-zinc": {"id": "sa3-zinc", "name": "Zinc SA-3 site (captured)", "system_id": "SA-3", "reporting_name": "Goa", "native_designation": "S-125",
                     "radar_reporting_name": "Low Blow", "radar_system_id": "SNR-125", "radar_roles": ["target_tracking"], "extensions": dcs(alic_code=123),
                     "rwr_symbol": "3", "position": position(35.255, 39.905), "status": "active", "mobility": "fixed", "side": "red",
                     "max_engagement_range": km(25), "min_engagement_range": km(3.5), "detection_range": km(60),
                     "engagement_floor": feet(65, "AGL"), "engagement_ceiling": feet(59000), "measures": refs("zinc-mez")},
        "sa8-nickel": {"id": "sa8-nickel", "name": "Nickel SA-8 platoon", "system_id": "SA-8", "reporting_name": "Gecko",
                       "native_designation": "9K33 Osa", "radar_reporting_name": "Land Roll",
                       "radar_roles": ["target_acquisition", "target_tracking"], "extensions": dcs(alic_code=117), "rwr_symbol": "8",
                       "position": position(35.115, 40.175), "status": "suspected", "last_seen": at("1130"), "mobility": "mobile", "side": "red",
                       "max_engagement_range": km(10), "min_engagement_range": km(1.5), "detection_range": km(30),
                       "engagement_floor": feet(30, "AGL"), "engagement_ceiling": feet(16000)},
    }


def brief_resources(version):
    """Records that the briefs refer to: LZ, PZ, DZ, NAI, air assault points, the bullseye, the JTAC, procedures, targets."""
    nai = {"$schema": f"urn:openaix:schema:measure-area:{version}", "id": "nai-gainful", "name": "NAI 1 Gainful", "type": "NAI",
           "active": window(), "description": "Road junctions where the SA-6 battery is expected to relocate.",
           "geometry": {"kind": "polygon", "rings": [[position(35.175, 40.205), position(35.175, 40.345), position(35.255, 40.345),
                                                       position(35.255, 40.205), position(35.175, 40.205)]]},
           "extensions": deepcopy(EXERCISE)}
    return {
        "control_measures": {
            "range-camp-nfa": nfa(version, "range-camp-nfa", "Displaced-persons camp NFA", position(35.065, 40.405), 1852,
                              "No-fire area around the occupied displaced-persons camp east of the Cobalt compound."),
            "zinc-pump-nfa": nfa(version, "zinc-pump-nfa", "Zinc pumping station NFA", position(35.225, 39.885), 500,
                                 "No-fire area around the civilian water pumping station beside the Zinc depot."),
            "carp-tin": point(version, "carp-tin", "DZ Tin release point", position(34.660, 40.439), ["control"],
                              "Planned CARP for the personnel drop on DZ Tin."),
            "pi-tin": point(version, "pi-tin", "DZ Tin point of impact", position(34.676, 40.462), ["control"],
                            "Personnel point of impact on DZ Tin, marked by the raised angle marker."),
            "zinc-mez": {"$schema": f"urn:openaix:schema:measure-mez:{version}", "id": "zinc-mez", "name": "Zinc LOMEZ", "type": "MEZ",
                         "mez_kind": "low", "active": window(),
                         "description": "Missile engagement zone of the hostile SA-3 site that defends the Zinc depot.",
                         "components": [{"id": "zinc-mez-volume", "operation": "add", "active": window(),
                                         "geometry": {"kind": "circle", "center": position(35.255, 39.905), "radius": {"value": 25, "unit": "km"}},
                                         "lower_limit": {"surface": True}, "upper_limit": feet(60000)}],
                         "extensions": deepcopy(EXERCISE)},
            "gainful-misarc": {"$schema": f"urn:openaix:schema:measure-misarc:{version}", "id": "gainful-misarc", "name": "Gainful missile arc",
                               "type": "MISARC", "active": window(), "center": position(35.215, 40.265),
                               "axis": {"value": 200, "reference": "true"}, "range": {"value": 24, "unit": "km"}, "width_deg": 60,
                               "description": "Expected engagement sector of the SA-6 battery toward the Anvil ingress from the south-west.",
                               "extensions": deepcopy(EXERCISE)},
            "pz-sage": zone(version, "pz-sage", "PZ Sage", "PZ", position(34.740, 40.220), 0.3, 500,
                            "Pickup zone for the Task Force Bastion air assault, beside Sage FARP."),
            "lz-nickel": zone(version, "lz-nickel", "LZ Nickel", "LZ", position(34.895, 40.304), 0.3, 500,
                              "Landing zone for the Task Force Bastion air assault, between PL BRASS and PL NICKEL."),
            "dz-tin": zone(version, "dz-tin", "DZ Tin", "DZ", position(34.685, 40.475), 0.5, 1500,
                           "Drop zone for the airborne platoon on the south flank of Task Force Bastion, south of PL BRASS."),
            "nai-gainful": nai,
            "sp-sage": point(version, "sp-sage", "SP Sage", position(34.775, 40.234), ["control"], "Start point of the air assault serials."),
            "rp-nickel": point(version, "rp-nickel", "RP Nickel", position(34.865, 40.284), ["control"], "Release point of the air assault serials."),
            "bastion-bullseye": point(version, "bastion-bullseye", "Bastion bullseye", position(34.215, 39.647), ["bullseye"],
                                     "Bullseye for air-to-air calls in OIR."),
        },
        "emitters": emitters(),
        "agencies": {"axeman": {"id": "axeman", "kind": "c2-agency", "callsign": "Axeman", "role": "JTAC", "channels": ["cas-uhf"],
                                "position": position(35.005, 40.265)}},
        "procedures": {
            "harm-employment": {"title": "Weasel HARM employment", "steps": [
                {"action": "Fire only at emitters of the SA-6 battery inside the Cobalt kill box.", "condition": "The kill box is open."},
                {"action": "Call the missile shot on the Anvil package frequency."}]},
            "dz-authentication": {"title": "DZ Tin authentication", "steps": [
                {"action": "Authenticate the DZ support team with the number of the day before the one-minute call."},
                {"action": "Drop only on green smoke at the raised angle marker.", "condition": "Clear-to-drop signal seen."}]},
            "training-rules": {"title": "Azraq training rules", "steps": [
                {"action": "Call knock-it-off on Darkstar control for any safety concern."},
                {"action": "Keep 1000 feet vertical or 1 nautical mile horizontal from other aircraft in a merge."}]},
        },
        "targets": {
            "zinc-depot": {"kind": "fixed", "name": "Zinc supply depot", "target_number": "IR-0004",
                           "description": "ISIS fuel and ammunition depot that supplies the fighters in the valley.",
                           "identification_features": ["Four fuel tanks east of the road", "Long vehicle shed"],
                           "aimpoints": {
                               "fuel-tanks": {"name": "Fuel tanks", "position": position(35.217, 39.877), "elevation": feet(720)},
                               "vehicle-shed": {"name": "Vehicle shed", "position": position(35.214, 39.870), "elevation": feet(715)}}},
        },
    }


# ---------------------------------------------------------------------------------------------
# Briefs of the existing missions
# ---------------------------------------------------------------------------------------------

CAS_BRIEF = {
    "controllers": [contact("axeman", "cas-uhf", "banshee-uhf")],
    "contact_points": refs("marshal"), "initial_points": refs("ip-silver"), "holding": refs("mesa"),
    "holding_altitude": block(feet(14000), feet(16000)),
    "fire_support_measures": refs("oir-fscl", "pewter-rfl", "cobalt-box"),
    "friendly_lines": refs("pl-nickel", "pl-zinc", "bastion-basin-boundary"),
    "ground_scheme_summary": "Task Force Bastion attacks north from PL BRASS to PL ZINC; friendlies report the last phase line crossed.",
    "laser_codes": ["1688", "1511"], "marks": ["laser", "smoke"],
}


def briefs():
    """Brief of each OIR mission, by mission identifier."""
    air = {"controller": contact("darkstar", "control-uhf"), "bullseye": ref("bastion-bullseye"),
           "identification_procedure": "cap-commit", "roe_reference": deepcopy(SPINS_ROE)}
    return {
        "sweep": {**deepcopy(air), "commit_criteria": [{"threat": "red-air-fighters", "range": nm(40), "boundary": ref("cobalt-box")}],
                  "remarks": "Push at 1305Z; clear the area north of the Cobalt kill box only."},
        "intercept": {**deepcopy(air), "commit_criteria": [{"procedure": "cap-commit"}],
                      "remarks": "Visual identification only; no weapons employment without Darkstar clearance."},
        "cap-falcon": {**deepcopy(air), "commit_criteria": [{"threat": "red-air-fighters", "range": nm(30)}],
                       "protected_missions": ["shell-aar", "sentinel-aew"], "protected_measures": refs("shell", "sentinel"),
                       "threat_emitters": ["sa6-gainful"]},
        "strike-cobalt": {"initial_points": refs("ip-silver"), "egress_points": refs("cedar"),
                          "ingress_route": "marshal-entry", "egress_route": "marshal-exit",
                          "restricted_areas": refs("range-camp-nfa"), "threat_emitters": ["sa6-gainful", "sa8-nickel"],
                          "bda": {"method": "weapon_system_video", "report": "bda", "recipient": "caoc", "deadline": at("1430")}},
        "sead-cobalt": {"initial_points": refs("ip-silver"), "egress_points": refs("cedar"),
                        "sead": {"emitters": [{"emitter": "sa6-gainful", "target": "gainful-battery", "priority": 1}],
                                 "employment_procedure": "harm-employment", "protected_missions": ["strike-cobalt"],
                                 "suppression_window": window(at("1320"), at("1335"))}},
        "escort-anvil": {**deepcopy(air), "commit_criteria": [{"threat": "red-air-fighters", "range": nm(20)}],
                         "protected_missions": ["strike-cobalt"]},
        "jam-anvil": {"emitters": [{"emitter": "sa6-gainful", "target": "gainful-battery", "priority": 1}],
                      "protected_channels": ["strike-vhf", "control-uhf"]},
        "cas-cobalt": {**deepcopy(CAS_BRIEF), "check_in": {"procedure": "cas-check-in", "items": [
            "mission_number", "aircraft_number_and_type", "position_and_altitude", "ordnance", "time_on_station", "capabilities", "abort_code"],
            "abort_code": "SILVER"}},
        "shell-aar": {"anchor": ref("shell"), "rendezvous": "anchor", "rendezvous_point": ref("marshal"), "control_time": at("1340"),
                      "receiver_altitude": flight_level(180)},
        "sentinel-aew": {"orbit": ref("sentinel"), "controlled_channels": ["control-uhf", "tanker-uhf"], "bullseye": ref("bastion-bullseye"),
                         "sectors": [{"name": "North", "area": {"area": "sweep-north"}, "altitude": block(flight_level(200), flight_level(350)),
                                      "channel": "control-uhf", "missions": ["sweep", "intercept"]},
                                     {"name": "South", "area": ref("falcon"), "channel": "control-uhf", "missions": ["cap-falcon", "shell-aar"]}],
                         "handover_points": refs("juniper")},
        "recce-gainful": {"named_areas": refs("nai-gainful"),
                          "reporting": {"reports": ["inflightrep"], "recipient": "warhawk", "channel": "cas-uhf", "method": "voice", "deadline": at("1315")}},
        "airlift-prince-hassan": {"onload": {"place": "ojms", "window": window(at("1240"), at("1300"))},
                           "offload": {"place": "prince-hassan", "window": window(at("1330"), at("1345")), "agency": "banshee"},
                           "load_plan": [{"flight": "reach", "manifest": {"cargo": [{"name": "Munitions pallet", "quantity": 2}], "passengers": 12}}]},
        "pedro-csar": {"survivors": [{"id": "survivor-1", "callsign": "Spade 1", "last_known": {"position": position(34.529, 40.551), "as_of": at("1300")},
                                      "condition": "injured", "isoprep_ref": "IR-ISO-0042", "authentication_procedure": "sar-recognition"}],
                       "on_scene_commander": "pedro", "rescort_missions": ["cas-cobalt"], "egress_route": "marshal-exit",
                       "pickup_window": window(at("1330"), at("1400"))},
        "red-air": {"range_controller": contact("darkstar", "control-uhf"), "knock_it_off_channel": "control-uhf",
                    "minimum_altitude": feet(5000), "safety_procedure": "training-rules"},
        "range-clear": {"namespace": "org.cjtf-oir.clearance", "data": {"pass_altitude_ft_agl": 500, "clear_call": "AREA CLEAR"}},
    }


ASSIGNMENT_DATA = {
    ("strike-cobalt", "bunker"): {"weaponeering": [{"flight": "rage", "scl": "f15e-strike", "store": "gbu-31v3", "quantity": 2,
                                                    "release_altitude": feet(20000), "attack_heading": magnetic(13)}],
                                  "target_list_entry": {"document": {"id": "oir-jiptl", "revision": "1"}, "entry": "IR-0001"}},
    ("strike-cobalt", "vehicles"): {"weaponeering": [{"flight": "rage", "store": "gbu-12", "quantity": 2, "laser_code": "1511",
                                                      "release_altitude": feet(20000), "attack_heading": magnetic(13)}],
                                    "target_list_entry": {"document": {"id": "oir-jiptl", "revision": "1"}, "entry": "IR-0001"}},
    ("sead-cobalt", "gainful"): {"weaponeering": [{"flight": "weasel", "store": "agm-88c", "quantity": 2}],
                                 "target_list_entry": {"document": {"id": "oir-jiptl", "revision": "1"}, "entry": "IR-0002"}},
}


def add_briefs(missions):
    table = briefs()
    for mission in missions:
        if mission["id"] in table:
            mission["tasking"]["brief"] = table[mission["id"]]
        for assignment in mission["tasking"].get("assignments", []):
            assignment.update(deepcopy(ASSIGNMENT_DATA.get((mission["id"], assignment["id"]), {})))
        for requirement in mission["tasking"].get("requirements", []):
            requirement.update({"sensor": "electro_optical_infrared", "product": "full_motion_video",
                                "eeis": [{"id": "eei-1", "question": "Is the SA-6 radar emitting, and in which direction does it point?", "priority": 1},
                                         {"id": "eei-2", "question": "Are the launchers loaded and ready to move?", "priority": 2}]})
    return missions


# ---------------------------------------------------------------------------------------------
# Missions for the new roles
# ---------------------------------------------------------------------------------------------

def role_missions(mission, flight, launch_from):
    """Air interdiction, SCAR, FAC(A), air assault and airdrop missions, built with the scenario helpers."""
    ai = mission("ai-zinc", "1116", {"kind": "preplanned_attack", "role": "air_interdiction",
        "objective": "Destroy the Zinc supply depot to cut fuel to the ISIS fighters in the valley.",
        "assignments": [
            {"id": "tanks", "target": {"kind": "fixed", "target": "zinc-depot", "aimpoints": ["fuel-tanks"]},
             "assigned_to": [{"flight": "venom", "members": [1]}], "desired_effect": "DESTROY", "required_stores": ["gbu-12"],
             "timing": {"kind": "window", "window": window(at("1400"), at("1410"))}, "priority": 1, "role": "primary",
             "weaponeering": [{"flight": "venom", "store": "gbu-12", "quantity": 2,
                               "release_altitude": feet(22000), "attack_heading": magnetic(300)}],
             "target_list_entry": {"document": {"id": "oir-jiptl", "revision": "1"}, "entry": "IR-0004"}},
            {"id": "shed", "target": {"kind": "fixed", "target": "zinc-depot", "aimpoints": ["vehicle-shed"]},
             "assigned_to": [{"flight": "venom", "members": [2]}], "desired_effect": "DESTROY", "required_stores": ["gbu-12"],
             "timing": {"kind": "window", "window": window(at("1400"), at("1410"))}, "priority": 2, "role": "primary",
             "weaponeering": [{"flight": "venom", "store": "gbu-12", "quantity": 2,
                               "fuze": {"function": "delay", "tail_fuze": "FMU-139", "arming_delay_s": 4, "delay_ms": 10},
                               "release_altitude": feet(22000), "attack_heading": magnetic(300)}]}],
        "success_criteria": "Both aimpoints struck inside the window.", "report_refs": ["bda"],
        "brief": {"initial_points": refs("ip-silver"), "egress_points": refs("cedar"), "ingress_route": "marshal-entry", "egress_route": "marshal-exit",
                  "restricted_areas": refs("zinc-pump-nfa"), "threat_emitters": ["sa3-zinc"],
                  "bda": {"method": "weapon_system_video", "report": "bda", "recipient": "caoc", "deadline": at("1500")},
                  "remarks": "Target is beyond the FSCL; no coordination with Task Force Bastion needed. Stay out of the Cobalt kill box."}},
        [flight("venom", "Venom 1", "F-16C", 2, "f16-ai", 12000, 5000, 3500, "1320",
                [("control-uhf", "Darkstar control"), ("ops-uhf", "Kingpin")], ("12", "4120"), "Blue fighter squadron", route="marshal-entry")],
        control={"kind": "agency", "agency": "darkstar"})
    scar = mission("scar-gainful", "1117", {"kind": "counterland_control", "mission_type": "scar", "area": {"area": "recce-box"},
        "altitude": block(feet(15000), feet(22000)), "operating_window": window(at("1340"), at("1440")),
        "objective": "Find the relocated SA-6 battery and its resupply vehicles and pass them to the attack flights.",
        "success_criteria": "Every target found is handed to an attack flight or reported.", "report_refs": ["inflightrep", "bda"],
        "brief": {"controller": contact("darkstar", "control-uhf"), "attack_missions": ["ai-zinc", "sead-cobalt"],
                  "target_priorities": [{"category": "air_defense", "priority": 1}, {"category": "logistics_vehicle", "priority": 2}],
                  "entry_points": refs("juniper"), "holding": refs("mesa"),
                  "stack": [{"altitude": block(feet(16000), feet(17000)), "mission": "ai-zinc"},
                            {"altitude": block(feet(18000), feet(19000)), "mission": "sead-cobalt"}],
                  "reporting": {"reports": ["inflightrep"], "recipient": "darkstar", "channel": "control-uhf", "method": "voice"}}},
        [flight("dude", "Dude 1", "F-15E", 2, "f15e-scar", 23000, 9000, 6500, "1310",
                [("control-uhf", "Darkstar control"), ("strike-vhf", "Anvil package")], ("12", "4121"), "Blue strike squadron", route="marshal-entry")],
        control={"kind": "agency", "agency": "darkstar"})
    faca = mission("faca-nail", "1118", {"kind": "counterland_control", "mission_type": "fac_a", "area": ref("cobalt-box"),
        "altitude": block(feet(14000), feet(18000)), "operating_window": window(at("1330"), at("1430")),
        "objective": "Control CAS for Task Force Bastion when Axeman cannot see the target.",
        "report_refs": ["bda"],
        "brief": {**deepcopy(CAS_BRIEF), "supported_unit": "Task Force Bastion ground element", "cas_missions": ["cas-cobalt"],
                  "terminal_control": ["type_1", "type_2", "type_3"], "marks": ["laser", "smoke", "infrared_pointer"]}},
        [flight("nail", "Nail 1", "A-10C", 1, "a10-faca", 11000, 4500, 3000, "1245",
                [("cas-uhf", "Warhawk and Axeman"), ("banshee-uhf", "Banshee")], ("13", "4122"), "Blue attack squadron", route="marshal-entry")],
        control={"kind": "agency", "agency": "warhawk", "check_in": "cas-check-in"})
    assault = mission("assault-nickel", "1119", {"kind": "transport", "role": "air_assault", "pickup": "farp-sage", "delivery_method": "land",
        "pickup_time": {"kind": "at", "at": at("1335")}, "delivery_time": {"kind": "at", "at": at("1345")},
        "objective": "Land one rifle company on LZ Nickel to seize the road junction before PL NICKEL.",
        "abort_criteria": ["LZ Nickel reported under direct fire", "Fewer than two aircraft available for lift 1"],
        "brief": {"air_assault": {
            "pickup_zones": refs("pz-sage"), "landing_zones": refs("lz-nickel"), "h_hour": at("1345"),
            "air_movement_table": [
                {"line": 1, "lift": 1, "serial": 1, "chalks": [1, 2], "flight": "hook", "lifted_unit": "A Company, Task Force Bastion",
                 "pickup_zone": ref("pz-sage"), "load_time": at("1330"), "takeoff_time": at("1335"), "start_point": ref("sp-sage"),
                 "start_point_time": at("1337"), "release_point": ref("rp-nickel"), "release_point_time": at("1343"),
                 "landing_zone": ref("lz-nickel"), "landing_time": at("1345"), "landing_heading": magnetic(20), "landing_formation": "trail",
                 "load": {"passengers": 66}},
                {"line": 2, "lift": 2, "serial": 1, "chalks": [1, 2], "flight": "hook", "lifted_unit": "A Company mortars and resupply",
                 "pickup_zone": ref("pz-sage"), "load_time": at("1400"), "takeoff_time": at("1405"), "start_point": ref("sp-sage"),
                 "start_point_time": at("1407"), "release_point": ref("rp-nickel"), "release_point_time": at("1413"),
                 "landing_zone": ref("lz-nickel"), "landing_time": at("1415"), "landing_heading": magnetic(20), "landing_formation": "trail",
                 "load": {"passengers": 20, "cargo": [{"name": "120 mm mortar ammunition pallet", "quantity": 2, "handling": "Sling load"}]},
                 "remarks": "Second turn after a hot refuel at Sage FARP."}],
            "escort_missions": ["faca-nail", "cas-cobalt"]},
            "remarks": "Flights hold at PZ Sage if LZ Nickel is not reported clear by Axeman."}},
        [flight("hook", "Hook 1", "CH-47F", 2, None, 6800, 2500, 1800, "1320",
                [("cas-uhf", "Axeman"), ("banshee-uhf", "Banshee")], ("15", "4123"), "Blue assault helicopter company",
                launch=launch_from("farp-sage", "1320"), recovery={"destination": "farp-sage"})])
    airdrop = mission("drop-tin", "1120", {"kind": "transport", "role": "airdrop", "pickup": "ojms", "delivery_method": "airdrop",
        "pickup_time": {"kind": "at", "at": at("1315")}, "delivery_time": {"kind": "window", "window": window(at("1400"), at("1405"))},
        "objective": "Drop one airborne platoon on DZ Tin to secure the south flank of Task Force Bastion.",
        "manifest": {"passengers": 40},
        "brief": {"onload": {"place": "ojms", "window": window(at("1300"), at("1315"))},
                  "airdrop": {"drop_zone": ref("dz-tin"), "run_in_heading": magnetic(0), "release_method": "carp",
                              "release_point": ref("carp-tin"), "point_of_impact": ref("pi-tin"),
                              "drop_altitude": feet(1250, "AGL"), "drop_airspeed": {"value": 130, "unit": "knots_ias"},
                              "load_type": "personnel", "parachute_technique": "static_line",
                              "markings": ["raised_angle_marker", "smoke"], "clear_to_drop_signal": "smoke",
                              "authentication_procedure": "dz-authentication", "drop_window": window(at("1400"), at("1405")),
                              "drop_zone_controller": contact("banshee", "banshee-uhf")}}},
        [flight("herky", "Herky 1", "C-130J", 1, None, 42000, 15000, 10000, "1320",
                [("banshee-uhf", "Banshee"), ("control-uhf", "Darkstar control")], ("15", "4124"), "Blue airlift squadron")])
    return [ai, scar, faca, assault, airdrop]
