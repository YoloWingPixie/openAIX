"""The OIR scenario: one coherent set of order examples around the OIR ACO.

Operation INHERENT RESOLVE on the DCS Syria map, 2 October 2026, 1300Z-1500Z: coalition aircraft from Muwaffaq
Salti (OJMS) and Prince Hassan (H5) strike ISIS targets in the Euphrates valley near Deir ez-Zor and support a
partner ground force. Setting, period, measures, agencies and channels are those of examples/aco.py. The shared
resource catalogue is published once (examples/resources.json) and linked by the ATO with `resources_ref`. Targets,
units, callsigns and missions are invented; aircraft types, fuel loads and altitudes are planning values for DCS.
"""
from copy import deepcopy

from openaix.examples.aco import (MISSION_ID, START, agencies, build_aco_example, channels, frequency, point, position,
                                  window)
from openaix.examples.airfields import carrier, prince_hassan, farp, ojms, ojms_navigation, tacans, h4, usaf_standard
from openaix.examples.briefs import add_briefs, brief_resources, role_missions
from openaix.examples.measures import measures as measure_examples
from openaix.examples.opord import order_channels, order_examples, order_measures, spins_measures
from openaix.examples.scls import aircraft_type, aircraft_types, scl_example, scls, stores
from openaix.sim.dcs import extension as dcs

PERIOD = window()
RESOURCES_REF = {"id": "oir-resources", "revision": "1"}
EXERCISE = {"org.cjtf-oir.ato": {"ato_day": "214"}}


def at(hhmm):
    return "2026-10-02T" + hhmm[:2] + ":" + hhmm[2:] + ":00Z"


def feet(value, reference="MSL"):
    return {"value": value, "unit": "ft", "reference": reference}


def flight_level(value):
    return {"value": value, "unit": "flight_level", "reference": "FL"}


def block(lower, upper):
    return {"lower": lower, "upper": upper}


def pounds(value):
    return {"value": value, "unit": "lb"}


def measure(identifier):
    return {"kind": "control_measure", "id": identifier}


def area(identifier):
    return {"area": identifier}


# ---------------------------------------------------------------------------------------------
# Shared resource catalogue
# ---------------------------------------------------------------------------------------------

def resources(version):
    result = base_resources(version)
    for collection, records in brief_resources(version).items():
        result[collection] = {**result.get(collection, {}), **records}
    return result


def base_resources(version):
    aco = build_aco_example(version)["resources"]
    ip = point(version, "ip-silver", "Silver", position(34.955, 40.045), ["initial"], "marshal-entry", "darkstar", "banshee")
    ip["description"] = "Initial point for attacks into the Cobalt kill box from the southwest."
    ip["position_description"] = "Desert road bend south-west of the Cobalt compound."
    localizers, procedure = ojms_navigation(version)
    return {
        "places": {"ojms": ojms(), "prince-hassan": prince_hassan(), "h4": h4(), "farp-sage": farp()},
        "localizers": {localizer["id"]: localizer for localizer in localizers},
        "instrument_procedures": {procedure["id"]: procedure},
        "pattern_profiles": {"usaf-standard": usaf_standard()},
        "agencies": {**agencies(), "warhawk": {"id": "warhawk", "kind": "c2-agency", "callsign": "Warhawk", "role": "ASOC",
                                                "channels": ["cas-uhf"], "position": position(32.965, 37.794)}},
        "channels": {**channels(),
            "tanker-uhf": {"name": "Shell boom", "frequency": frequency(276.1), "usage": "Tanker rendezvous and boom operations", "notes": "Primary tanker for the eastern stack; expect 15 minutes on the boom per two-ship."},
            "cas-uhf": {"name": "Warhawk CAS", "frequency": frequency(309.2), "usage": "CAS check-in and terminal control with Axeman", "notes": "Check in 10 nm before Dagger; Warhawk stacks CAS from 15000 feet."},
            "rescue-uhf": {"name": "Rescue common", "frequency": frequency(282.8), "usage": "On-scene personnel recovery coordination", "notes": "Guard 243.0 is the backup survivor frequency."},
            "strike-vhf": {"name": "Anvil package", "frequency": {"value": 138.75, "unit": "MHz", "modulation": "AM"}, "usage": "Strike package inter-flight"},
            **order_channels()},
        "routes": deepcopy(aco["routes"]),
        "control_measures": {**deepcopy(aco["control_measures"]), "ip-silver": ip, **tacans(), **ground_measures(version)},
        "areas": {
            "sweep-north": {"name": "North sweep area", "geometry": {"kind": "polygon", "rings": [[
                position(35.235, 39.925), position(35.235, 40.525), position(35.435, 40.525), position(35.435, 39.925), position(35.235, 39.925)]]},
                "altitude": block(flight_level(200), flight_level(350)), "active": deepcopy(PERIOD),
                "restrictions": ["Remain north of the Cobalt kill box while it is open."]},
            "jamming-orbit": {"name": "Grizzly stand-off area", "geometry": {"kind": "circle", "center": position(34.835, 39.974), "radius": {"value": 8, "unit": "nm"}},
                "altitude": block(flight_level(240), flight_level(260)), "active": deepcopy(PERIOD)},
            "recce-box": {"name": "Gainful search box", "geometry": {"kind": "polygon", "rings": [[
                position(35.155, 40.125), position(35.155, 40.425), position(35.285, 40.425), position(35.285, 40.125), position(35.155, 40.125)]]},
                "altitude": block(feet(15000), feet(20000)), "active": deepcopy(PERIOD)},
            "red-air": {"name": "Northern threat axis", "geometry": {"kind": "corridor", "points": [position(35.485, 39.825), position(35.485, 40.525)],
                "width": {"value": 10, "unit": "nm"}}, "altitude": block(flight_level(150), flight_level(350)), "active": deepcopy(PERIOD)},
            "azraq-training": {"name": "Azraq training area", "geometry": {"kind": "polygon", "rings": [[
                position(31.900, 37.100), position(31.900, 37.500), position(32.100, 37.500), position(32.100, 37.100), position(31.900, 37.100)]]},
                "altitude": block(feet(5000), flight_level(250)), "active": deepcopy(PERIOD)},
            "range-sweep": {"name": "Cobalt clearance area", "geometry": {"kind": "circle", "center": position(35.095, 40.305), "radius": {"value": 6, "unit": "nm"}},
                "altitude": block({"surface": True}, feet(1000, "AGL")), "active": window(START, at("1320"))},
        },
        "procedures": {
            "cas-check-in": {"title": "Warhawk CAS check-in", "steps": [
                {"action": "Check in with Warhawk: mission number, aircraft, position and altitude, ordnance, playtime, abort code."},
                {"action": "Receive the situation update and the JTAC assignment.", "completion": "Warhawk hands the flight to Axeman."}]},
            "tanker-rendezvous": {"title": "Shell rendezvous", "steps": [
                {"action": "Contact Shell on the tanker frequency 20 nautical miles from Shell anchor."},
                {"action": "Join 1000 feet below the tanker's flight level, then climb to pre-contact when cleared.", "condition": "Visual with the tanker."}]},
            "cap-commit": {"title": "Falcon commit criteria", "steps": [
                {"action": "Commit on hostile or unknown tracks entering the sweep area below flight level 350.", "condition": "Darkstar declares the track."},
                {"action": "Do not pursue south of the Cobalt kill box while it is open."}]},
            "sar-recognition": {"title": "Rescue recognition", "steps": [
                {"action": "Authenticate the survivor with the SARNEG word and the number of the day."},
                {"action": "Survivor marks with day smoke or an infrared strobe at night."}]},
            "recovery-ojms": {"title": "Muwaffaq Salti recovery", "steps": [
                {"action": "Leave the operating area via Cedar; contact Banshee.", "completion": "Handed over to Salti Tower."}]},
            "range-debrief": {"title": "Mission debrief", "steps": [{"action": "Debrief at Muwaffaq Salti 1700Z with weapons-system video and the JTAC log."}]},
        },
        "reports": {
            "misrep": {"name": "Mission report (MISREP)", "precedence": "PRIORITY", "recipient": "caoc", "trigger": "Within 30 minutes of landing",
                       "medium": "voice", "channel": "ops-uhf"},
            "inflightrep": {"name": "In-flight report (INFLIGHTREP)", "precedence": "IMMEDIATE", "recipient": "darkstar", "trigger": "Time-sensitive observation airborne",
                            "medium": "voice", "channel": "control-uhf"},
            "bda": {"name": "Battle damage assessment", "precedence": "PRIORITY", "recipient": "caoc", "trigger": "After each attack",
                    "medium": "voice", "channel": "ops-uhf", "classification": "UNCLASSIFIED"},
        },
        "aircraft_types": aircraft_types(),
        "stores": stores(),
        "scls": scls(),
        "targets": {
            "cobalt-array": {"kind": "fixed", "name": "Cobalt compound", "target_number": "IR-0001",
                "description": "ISIS command post and vehicle park in a walled compound west of the Euphrates.",
                "identification_features": ["Two hardened shelters north of the road junction", "Revetted vehicle park"],
                "threat_refs": ["sa-6"], "aimpoints": {
                    "bunker-north": {"name": "North bunker", "position": position(35.100, 40.300), "elevation": {"value": 690, "unit": "ft", "reference": "MSL"}},
                    "vehicle-park": {"name": "Vehicle park", "position": position(35.093, 40.314), "elevation": {"value": 685, "unit": "ft", "reference": "MSL"}}}},
            "gainful-battery": {"kind": "mobile", "name": "Captured SA-6 battery", "target_number": "IR-0002",
                "description": "SA-6 Gainful battery that ISIS captured and moves along the river road north of Cobalt.",
                "identification_features": ["Straight Flush radar vehicle with three launchers"],
                "last_known": {"position": position(35.215, 40.265), "as_of": at("1215")}, "search_area": area("recce-box"),
                "expected_movement": "Relocates up to 5 nautical miles after emitting.", "threat_refs": ["sa-6"]},
            "unknown-track": {"kind": "mobile", "name": "Unidentified aircraft formation", "target_number": "IR-0003",
                "description": "Track of two aircraft from the north-west without a flight plan or deconfliction call; identity is not assumed.",
                "last_known": {"position": position(35.585, 40.125), "as_of": at("1250")}},
        },
        "threats": {
            "sa-6": {"kind": "air_defense", "name": "SA-6 Gainful", "system": "2K12 Kub", "area": area("recce-box"), "emitters": ["sa6-gainful"],
                     "expected_activity": "Radar emits when strike aircraft approach Cobalt.", "as_of": at("1200")},
            "red-air-fighters": {"kind": "air", "name": "Third-party fighters", "system": "MiG-29", "area": area("red-air"),
                                 "expected_activity": "Two to four aircraft can approach from the north-west between 1310Z and 1400Z."},
        },
    }


# Task Force Bastion graphics and the fire support and airspace measures around it (examples/measures.py).
GROUND_MEASURES = ("measures/ld.json", "measures/pl.json", "measures/loa.json", "measures/boundary.json", "measures/rfl.json",
                   "measures/trp.json", "measures/ca.json", "measures/shoradez.json", "measures/fscl.json",
                   "measures/aor.json", "measures/nfa.json")


def ground_measures(version):
    examples = measure_examples(version)
    return {**{examples[path]["id"]: deepcopy(examples[path]) for path in GROUND_MEASURES}, **order_measures(), **spins_measures()}


def resource_catalogue(version):
    return {"$schema": f"urn:openaix:schema:resources:{version}", "kind": "resources", "schema_version": version,
            "meta": {"id": RESOURCES_REF["id"], "revision": RESOURCES_REF["revision"], "title": "OIR shared resources",
                     "issuing_unit": "CJTF-OIR CAOC", "operation": "INHERENT RESOLVE", "issued_at": at("1100")},
            "resources": resources(version)}


# ---------------------------------------------------------------------------------------------
# Air Tasking Order
# ---------------------------------------------------------------------------------------------

def flight(identifier, callsign, aircraft, count, scl_id, fuel, joker, bingo, takeoff, radios, modes, unit, **extra):
    result = {"id": identifier, "callsign": callsign, "aircraft_type": aircraft_type(aircraft), "count": count, "unit": unit,
              "participation": "player", "extensions": dcs([{"kind": "group", "name": "OIR " + callsign, "mission_id": MISSION_ID}]),
              "fuel": {"initial": pounds(fuel), "joker": pounds(joker), "bingo": pounds(bingo)},
              "launch": {"kind": "scheduled", "departure": "ojms", "startup": at(minus(takeoff, 30)), "taxi": at(minus(takeoff, 15)), "takeoff": at(takeoff)},
              "recovery": {"destination": "ojms", "alternates": ["prince-hassan"], "procedure": "recovery-ojms"},
              "communications": [{"channel": channel, "preset": preset, "radio": "UHF" if channel != "strike-vhf" else "VHF", "purpose": purpose}
                                 for preset, (channel, purpose) in enumerate(radios, 1)],
              "identification": {"mode_1": modes[0], "mode_3": modes[1], "mode_4": "on", "mode_5": "on"}}
    if scl_id:
        result["configuration"] = {"primary_scl": scl_id}
    result.update(extra)
    return result


def minus(hhmm, minutes):
    total = int(hhmm[:2]) * 60 + int(hhmm[2:]) - minutes
    return f"{total // 60:02d}{total % 60:02d}"


def prince_hassan_launch(takeoff):
    return {"kind": "scheduled", "departure": "prince-hassan", "startup": at(minus(takeoff, 30)), "taxi": at(minus(takeoff, 15)), "takeoff": at(takeoff)}


def mission(identifier, number, tasking, flights, **extra):
    return {"id": identifier, "mission_number": number, "tasking": tasking, "flights": flights, **extra}


def ato(version):
    station = window(at("1310"), at("1450"))
    missions = [
        mission("sweep", "1101", {"kind": "counterair", "mission_type": "fighter_sweep", "area": area("sweep-north"),
            "altitude": block(flight_level(250), flight_level(350)), "operating_window": window(at("1305"), at("1345")),
            "objective": "Clear the northern sweep area of hostile air before the Anvil package pushes.", "engagement_instructions": "cap-commit",
            "success_criteria": "No hostile air south of the sweep area at 1345Z.", "report_refs": ["misrep"]},
            [flight("dodge", "Dodge 1", "F-15C", 4, "f15c-aa", 25000, 9000, 6000, "1235",
                    [("control-uhf", "Darkstar control"), ("ops-uhf", "Kingpin")], ("11", "4101"), "Blue fighter squadron",
                    route="marshal-entry")],
            control={"kind": "agency", "agency": "darkstar"}),
        mission("intercept", "1102", {"kind": "counterair", "mission_type": "interception", "target": {"kind": "mobile", "target": "unknown-track"},
            "objective": "Intercept and identify the unknown track; report its identity to Darkstar.",
            "success_criteria": "Visual identification reported to Darkstar.", "report_refs": ["inflightrep"]},
            [flight("pontiac", "Pontiac 1", "F-16C", 2, "f16-cap", 12000, 5000, 3500, "1240",
                    [("control-uhf", "Darkstar control")], ("11", "4102"), "Blue fighter squadron",
                    launch={"kind": "alert", "departure": "ojms", "readiness_minutes": 15, "availability": deepcopy(PERIOD), "release_authority": "darkstar"})],
            control={"kind": "agency", "agency": "darkstar"}),
        mission("cap-falcon", "1103", {"kind": "cap", "area": measure("falcon"), "altitude": block(flight_level(220), flight_level(260)),
            "station_window": deepcopy(station), "objective": "Defend the Shell and Sentinel orbits.",
            "coverage_responsibility": "Air threats north of Falcon toward Shell and Sentinel.", "engagement_instructions": "cap-commit",
            "handover": "Hand over the station to the relief flight in Falcon at 1450Z.", "report_refs": ["misrep"]},
            [flight("viper", "Viper 1", "F-16C", 2, "f16-cap", 12000, 5000, 3500, "1240",
                    [("control-uhf", "Darkstar control"), ("tanker-uhf", "Shell boom")], ("11", "4103"), "Blue fighter squadron",
                    route="marshal-entry", activities=[{"id": "viper-station", "kind": "station", "area": measure("falcon"),
                        "window": deepcopy(station), "altitude": flight_level(240)},
                        {"id": "viper-refuel", "kind": "refuel", "area": measure("shell"), "window": window(at("1350"), at("1410")),
                         "altitude": flight_level(190), "support_flight": "shell"}])],
            control={"kind": "agency", "agency": "darkstar"}),
        mission("strike-cobalt", "1104", {"kind": "preplanned_attack", "role": "strike", "objective": "Destroy the Cobalt command post and vehicle park.",
            "assignments": [
                {"id": "bunker", "target": {"kind": "fixed", "target": "cobalt-array", "aimpoints": ["bunker-north"]},
                 "assigned_to": [{"flight": "rage", "members": [1]}], "desired_effect": "DESTROY", "required_stores": ["gbu-31v3"],
                 "timing": {"kind": "window", "window": window(at("1325"), at("1330"))}, "priority": 1, "role": "primary",
                 "restrictions": ["Attack only while the Cobalt kill box is open."]},
                {"id": "vehicles", "target": {"kind": "fixed", "target": "cobalt-array", "aimpoints": ["vehicle-park"]},
                 "assigned_to": [{"flight": "rage", "members": [2]}], "desired_effect": "DESTROY", "required_stores": ["gbu-12"],
                 "timing": {"kind": "window", "window": window(at("1325"), at("1330"))}, "priority": 2, "role": "primary"}],
            "success_criteria": "Both aimpoints struck inside the time-on-target window.", "report_refs": ["bda", "misrep"]},
            [flight("rage", "Rage 1", "F-15E", 2, "f15e-strike", 23000, 9000, 6500, "1245",
                    [("strike-vhf", "Anvil package"), ("banshee-uhf", "Banshee"), ("tanker-uhf", "Shell boom")], ("12", "4104"), "Blue strike squadron",
                    route="marshal-entry")],
            package="anvil", control={"kind": "agency", "agency": "darkstar"},
            support=[{"role": "escort", "flight": "chevy"}, {"role": "suppression", "flight": "weasel"}, {"role": "tanker", "flight": "shell", "window": window(at("1350"), at("1410"))}]),
        mission("sead-cobalt", "1105", {"kind": "preplanned_attack", "role": "sead", "objective": "Suppress the SA-6 during the Anvil attack window.",
            "assignments": [{"id": "gainful", "target": {"kind": "mobile", "target": "gainful-battery"}, "assigned_to": [{"flight": "weasel"}],
                             "desired_effect": "SUPPRESS", "required_stores": ["agm-88c"], "timing": {"kind": "window", "window": window(at("1320"), at("1335"))}}]},
            [flight("weasel", "Weasel 1", "F-16C", 2, "f16-sead", 12000, 5000, 3500, "1240",
                    [("strike-vhf", "Anvil package"), ("control-uhf", "Darkstar control")], ("12", "4105"), "Blue fighter squadron", route="marshal-entry",
                    configuration={"primary_scl": "f16-sead", "alternatives": [{"scl": "f16-sead-pre2015", "authority": "caoc",
                                   "condition": "The Sniper pods are not serviceable; Weasel keeps the HTS."}]})],
            package="anvil"),
        mission("escort-anvil", "1106", {"kind": "escort", "supported_missions": ["strike-cobalt"], "rendezvous": "juniper",
            "rendezvous_time": {"kind": "window", "window": window(at("1310"), at("1315"))}, "protection_window": window(at("1310"), at("1345")),
            "separation_instructions": "Stay 5 nautical miles ahead of Rage and 4000 feet above.", "release_condition": "Rage egressing past Cedar."},
            [flight("chevy", "Chevy 1", "F-16C", 2, "f16-cap", 12000, 5000, 3500, "1240",
                    [("strike-vhf", "Anvil package"), ("control-uhf", "Darkstar control")], ("11", "4106"), "Blue fighter squadron", route="marshal-entry")],
            package="anvil"),
        mission("jam-anvil", "1107", {"kind": "electromagnetic", "area": area("jamming-orbit"), "assigned_effect": "Stand-off jamming of the SA-6 acquisition and tracking radars.",
            "equipment_requirements": ["Three AN/ALQ-99 pods"], "restrictions": ["Jam only the SA-6 bands; no emission on coalition frequencies."],
            "operating_window": window(at("1315"), at("1340")), "supported_missions": ["strike-cobalt", "sead-cobalt"]},
            [flight("grizzly", "Grizzly 1", "EA-18G", 2, "ea18g-ea", 21000, 8000, 5500, "1240",
                    [("strike-vhf", "Anvil package"), ("control-uhf", "Darkstar control")], ("12", "4107"), "Blue electronic attack squadron")],
            package="anvil"),
        mission("cas-cobalt", "1108", {"kind": "on_call_cas", "area": measure("cobalt-box"), "availability": window(at("1330"), at("1430")),
            "tasking_agency": "warhawk", "terminal_control": "assigned_by_controller", "check_in_procedure": "cas-check-in",
            "supported_force": "Task Force Bastion ground element with JTAC Axeman", "report_refs": ["bda", "misrep"]},
            [flight("hawg", "Hawg 1", "A-10C", 2, "a10-cas", 11000, 4500, 3000, "1235",
                    [("cas-uhf", "Warhawk and Axeman"), ("banshee-uhf", "Banshee")], ("13", "4110"), "Blue attack squadron", route="marshal-entry")],
            control={"kind": "agency", "agency": "warhawk", "check_in": "cas-check-in"}),
        mission("shell-aar", "1109", {"kind": "refueling", "area": measure("shell"), "altitude": block(flight_level(180), flight_level(200)),
            "method": "boom", "tacan": {"channel": 31, "band": "Y", "identifier": "SHL"}, "channel": "tanker-uhf",
            "station_window": window(at("1315"), at("1450")), "planned_offload": pounds(60000), "rendezvous_procedure": "tanker-rendezvous",
            "receivers": [{"flight": "viper", "window": window(at("1350"), at("1410")), "planned_offload": pounds(12000)},
                          {"flight": "rage", "window": window(at("1340"), at("1400")), "planned_offload": pounds(18000)}],
            "unassigned_receiver_policy": "Unscheduled receivers call Shell; Darkstar sets priority."},
            [flight("shell", "Shell 1", "KC-135R", 1, None, 160000, 60000, 45000, "1215",
                    [("tanker-uhf", "Boom"), ("control-uhf", "Darkstar control")], ("14", "4111"), "Blue air refueling squadron")],
            control={"kind": "agency", "agency": "darkstar"}),
        mission("sentinel-aew", "1110", {"kind": "airborne_control", "area": measure("sentinel"), "altitude": block(flight_level(280), flight_level(300)),
            "station_window": window(at("1300"), at("1500")),
            "control_responsibilities": ["Surveillance of Falcon, Shell and the southern transit route",
                                         "Control of counterair flights and tanker rendezvous", "Report traffic approaching the rescue reservation"],
            "supported_missions": ["sweep", "intercept", "cap-falcon", "shell-aar"],
            "datalink": {"datalink_type": "Link 16", "datalink_network": "OIR", "datalink_station": "00011"}},
            [flight("darkstar-flight", "Darkstar", "E-3A", 1, None, 140000, 40000, 30000, "1200",
                    [("control-uhf", "Control"), ("ops-uhf", "Kingpin")], ("14", "4112"), "Blue airborne control squadron")]),
        mission("recce-gainful", "1111", {"kind": "reconnaissance", "objective": "Locate the SA-6 battery before the Anvil push.",
            "requirements": [{"id": "gainful-location", "information_required": "Current position and posture of the SA-6 battery.",
                              "area": area("recce-box"), "target": "gainful-battery", "collection_window": window(at("1300"), at("1320")),
                              "latest_useful_time": at("1315"),
                              "recipient": "warhawk"}], "report_refs": ["inflightrep"]},
            [flight("ghost", "Ghost 1", "MQ-9", 1, None, 3900, 1500, 1000, "1130",
                    [("cas-uhf", "Warhawk")], ("13", "4113"), "Blue attack squadron", participation="ai",
                    launch=prince_hassan_launch("1130"), recovery={"destination": "prince-hassan", "alternates": ["ojms"]})]),
        mission("airlift-prince-hassan", "1112", {"kind": "transport", "role": "airlift", "pickup": "ojms", "destination": "prince-hassan",
            "pickup_time": {"kind": "at", "at": at("1300")}, "delivery_time": {"kind": "not_after", "at": at("1345")},
            "delivery_method": "land", "manifest": {"cargo": [{"name": "Munitions pallet", "quantity": 2, "handling": "Forklift at destination; hazardous cargo"}], "passengers": 12}},
            [flight("reach", "Reach 1", "C-130J", 1, None, 45000, 15000, 10000, "1310",
                    [("banshee-uhf", "Banshee")], ("15", "4114"), "Blue airlift squadron")]),
        mission("pedro-csar", "1113", {"kind": "personnel_recovery", "role": "combat_search_and_rescue",
            "incident": "Hawg 2 pilot ejected east of the transit route after an engine fire; beacon and voice contact.",
            "search_area": measure("rescue-reservation"), "availability": window(at("1300"), at("1420")), "recovery_method": "hoist",
            "recovery_destination": "farp-sage", "coordination_agency": "darkstar", "recognition_procedure": "sar-recognition",
            "medical_requirements": "Lower-leg injury; litter required."},
            [flight("pedro", "Pedro 1", "HH-60G", 2, None, 4500, 1800, 1200, "1245",
                    [("rescue-uhf", "On-scene"), ("banshee-uhf", "Banshee")], ("15", "4115"), "Blue rescue squadron",
                    launch={"kind": "scheduled", "departure": "farp-sage", "startup": at("1215"), "taxi": at("1230"), "takeoff": at("1245")})]),
        mission("red-air", "1114", {"kind": "training", "area": area("azraq-training"), "exercise_window": window(at("1310"), at("1400")),
            "objective": "Dissimilar air combat training with partner F-16s in the Azraq training area.",
            "events": [{"action": "Two-ship presentation from the east at flight level 200.", "condition": "Fight's on call from Salti Tower's area controller."},
                       {"action": "Regenerate once at the eastern edge of the area.", "completion": "Knock-it-off on the training frequency."}],
            "restrictions": ["No live weapons; master arm safe.", "Remain above 5000 feet MSL."], "debrief_procedure": "range-debrief"},
            [flight("bandit", "Bandit 1", "F-16C", 2, "f16-cap", 12000, 5000, 3500, "1240",
                    [("control-uhf", "Darkstar control")], ("16", "4116"), "Partner F-16 squadron", participation="ai")]),
        mission("range-clear", "1115", {"kind": "custom", "name": "Kill box clearance pass", "area": area("range-sweep"),
            "operating_window": window(at("1300"), at("1320")), "objective": "Confirm the Cobalt area is clear of civilian traffic before the kill box opens.",
            "assigned_actions": [{"action": "Fly a pass around the Cobalt compound and the river road.", "completion": "Report the area clear to Banshee."}],
            "required_capabilities": ["Low-level visual search"], "coordination": "Banshee releases the kill box only after this report."},
            [flight("sweeper", "Sweeper 1", "AH-64D", 1, "ah64-hellfire", 2500, 900, 600, "1235",
                    [("banshee-uhf", "Banshee")], ("16", "4117"), "Attack helicopter troop",
                    launch={"kind": "scheduled", "departure": "farp-sage", "startup": at("1205"), "taxi": at("1225"), "takeoff": at("1235")},
                    recovery={"destination": "farp-sage"})]),
    ]
    missions.extend(role_missions(mission, flight, lambda place, takeoff: {
        "kind": "scheduled", "departure": place, "startup": at(minus(takeoff, 30)), "taxi": at(minus(takeoff, 15)), "takeoff": at(takeoff)}))
    add_briefs(missions)
    packages = [{"id": "anvil", "name": "Anvil strike package", "objective": "Strike the Cobalt compound with suppression and escort.",
                 "commander": {"flight": "rage", "members": [1]}, "rendezvous": "juniper",
                 "rendezvous_time": {"kind": "window", "window": window(at("1310"), at("1315"))},
                 "coordination": ["Push from Juniper at 1315Z.", "Weasel and Grizzly on station before Rage crosses Silver."]}]
    return {"$schema": f"urn:openaix:schema:ato:{version}", "kind": "ato", "schema_version": version,
            "meta": {"id": "oir-ato", "revision": "1", "title": "OIR Air Tasking Order", "issued_at": at("1100"),
                     "issuing_unit": "CJTF-OIR CAOC", "operation": "INHERENT RESOLVE", "coalition": "blue", "classification": "UNCLASSIFIED"},
            "period": deepcopy(PERIOD), "resources_ref": deepcopy(RESOURCES_REF),
            "aco": {"id": "oir-aco", "revision": "2", "title": "OIR ACO"},
            "spins": {"id": "oir-spins", "revision": "1", "path": "spins.json"},
            "general_instructions": ["All times are UTC. Coalition ROE apply; positive identification before every release.",
                                     "Airspace, holding and kill-box status follow the OIR ACO; procedures follow the OIR SPINS."],
            "packages": packages, "missions": missions, "extensions": deepcopy(EXERCISE)}


# ---------------------------------------------------------------------------------------------
# Other orders and records
# ---------------------------------------------------------------------------------------------

def tst(version):
    return {"$schema": f"urn:openaix:schema:tst:{version}", "kind": "tst", "schema_version": version,
            "meta": {"id": "oir-tst", "revision": "1", "title": "OIR time-sensitive targets", "issued_at": at("1200")},
            "resources_ref": deepcopy(RESOURCES_REF),
            "targets": [{"tst_number": "TST-01", "target": "gainful-battery",
                         "target_description": "Captured SA-6 battery that relocates along the river road after it emits.",
                         "priority": 1, "category": "air defense",
                         "expected_locations": [{"name": "Gainful search box centre", "position": position(35.215, 40.265)},
                                                {"name": "Road junction north of Cobalt", "position": position(35.175, 40.325)}],
                         "activity_window": window(at("1300"), at("1400")),
                         "authorized_engagement_means": [{"system": "F-16C", "scl": "f16-sead", "store": "agm-88c"},
                                                         {"system": "F-15E", "scl": "f15e-scar", "store": "gbu-38"},
                                                         {"system": "A-10C", "scl": "a10-cas", "store": "agm-65d"}],
                         "engagement_authority": "caoc", "roe_constraints": "Positive identification by two sources; no strikes within 500 m of the Lantern village.",
                         "expiration_criteria": "Battery assessed destroyed.", "expires_at": at("1400")}]}


def jiptl(version):
    return {"$schema": f"urn:openaix:schema:jiptl:{version}", "kind": "jiptl", "schema_version": version,
            "meta": {"id": "oir-jiptl", "revision": "1", "title": "OIR prioritized targets", "issued_at": at("1000")},
            "resources_ref": deepcopy(RESOURCES_REF),
            "targets": [
                {"target_number": "IR-0001", "target": "cobalt-array", "priority_rank": 1, "target_name": "Cobalt compound",
                 "target_description": "ISIS command post and vehicle park.", "location": position(35.100, 40.300),
                 "desired_effect": "DESTROY", "component_tasked": "AIR",
                 "authorized_engagement_means": [{"system": "F-15E", "scl": "f15e-strike", "store": "gbu-31v3"}], "status": "APPROVED"},
                {"target_number": "IR-0002", "target": "gainful-battery", "priority_rank": 2, "target_name": "SA-6 battery",
                 "target_description": "Mobile surface-to-air missile battery.",
                 "location": position(35.215, 40.265), "desired_effect": "SUPPRESS", "component_tasked": "AIR",
                 "authorized_engagement_means": [{"system": "F-16C", "scl": "f16-sead", "store": "agm-88c"}, {"system": "EA-18G", "scl": "ea18g-ea"}],
                 "status": "APPROVED"},
                {"target_number": "IR-0004", "target": "zinc-depot", "priority_rank": 3, "target_name": "Zinc supply depot",
                 "target_description": "Fuel and ammunition depot that supplies the northern enemy force.",
                 "location": position(35.216, 39.874), "desired_effect": "DESTROY", "component_tasked": "AIR",
                 "authorized_engagement_means": [{"system": "F-16C", "scl": "f16-ai", "store": "gbu-12"}], "status": "APPROVED"},
            ]}


def c2_agency(version):
    agency = deepcopy(resources(version)["agencies"]["warhawk"])
    return {"$schema": f"urn:openaix:schema:c2-agency:{version}", **agency, "resources_ref": deepcopy(RESOURCES_REF)}


def fac(version):
    return {"$schema": f"urn:openaix:schema:fac:{version}", "id": "axeman", "kind": "fac", "callsign": "Axeman 1-1", "role": "jtac",
            "platform": "ground", "coalition": "blue", "channels": ["cas-uhf"], "position": position(35.005, 40.265),
            "terminal_control": ["type_1", "type_2", "type_3"], "laser_codes": ["1688", "1511"], "default_laser_code": "1688",
            "coordinate_source": "lrf", "initial_points": [measure("ip-silver")], "egress_points": [measure("cedar")], "smoke_color": "white",
            "equipment": [
                {"id": "designator", "kind": "laser_designator", "name": "Ground laser target designator", "quantity": 1, "available": True,
                 "max_range": {"value": 10, "unit": "km"}, "laser_codes": ["1688", "1511"]},
                {"id": "rangefinder", "kind": "laser_rangefinder", "name": "Handheld laser rangefinder", "quantity": 1, "available": True,
                 "max_range": {"value": 8, "unit": "km"}, "horizontal_accuracy": {"value": 10, "unit": "m"}, "vertical_accuracy": {"value": 5, "unit": "m"}},
                {"id": "radio", "kind": "radio", "name": "Multiband manpack radio", "quantity": 2, "available": True}],
            "resources_ref": deepcopy(RESOURCES_REF),
            "extensions": {**dcs([{"kind": "unit", "name": "OIR Axeman", "object_id": 42, "unit_type": "Hummer", "mission_id": MISSION_ID}]),
                           "org.vox-bellica.jtac": {"source_unit": "OIR Axeman", "group": "OIR Axeman team", "observers": ["OIR Axeman OP"],
                                                    "search_range_m": 10000, "laser_range_m": 8000, "readback_timeout_s": 60,
                                                    "stack": {"concurrent": False, "radius_m": 3000, "block_ft": 2000, "separation_ft": 1000,
                                                              "slow_floor_ft": 12000, "fast_floor_ft": 16000}}}}


def scenario_examples(version):
    """Published OIR examples (the ACO is published by examples/aco.py)."""
    return {
        "examples/resources.json": resource_catalogue(version),
        "examples/ato-oir.json": ato(version),
        **order_examples(version),
        "examples/tst.json": tst(version),
        "examples/jiptl.json": jiptl(version),
        "examples/c2-agency.json": c2_agency(version),
        "examples/fac.json": fac(version),
        "examples/scl.json": scl_example(version, RESOURCES_REF),
        "examples/carrier.json": carrier(version),
        "examples/farp.json": {"$schema": f"urn:openaix:schema:airfield:{version}", **farp(), "resources_ref": deepcopy(RESOURCES_REF)},
    }
