"""OIR OPORD, FRAGO and SPINS examples (Operation INHERENT RESOLVE on the DCS Syria map, 2 October 2026).

The OPORD gives every paragraph and every annex of build/opord/ typed content. Its references resolve in the
shared resource catalogue (examples/resources.json) and in the OIR ATO (examples/ato-oir.json).
The FRAGO is a delta against OPORD revision 1, the SPINS and the ATO. The extra ground graphics and the alternate
CAS channel that the orders use are added to the resource catalogue by examples/scenario.py.
"""
from copy import deepcopy

RESOURCES_REF = {"id": "oir-resources", "revision": "1"}
ORDERS = {"ato": {"id": "oir-ato", "revision": "1"}, "aco": {"id": "oir-aco", "revision": "2"},
          "spins": {"id": "oir-spins", "revision": "1"}}
EXERCISE = {"org.cjtf-oir.ato": {"ato_day": "214"}}
PRINT = {"org.opord-builder.print": {
    "classification_banner": "UNCLASSIFIED", "caveats": ["REL TO CJTF-OIR"], "copy_number": 1,
    "number_of_copies": 12, "place_of_issue": "Muwaffaq Salti, Jordan", "message_reference_number": "IR-26-01",
    "logo": "assets/oir.png", "page_icon": "assets/oir-icon.png"}}


def at(hhmm, day=2):
    return f"2026-10-{day:02d}T{hhmm[:2]}:{hhmm[2:]}:00Z"


def window(start, end):
    return {"start": start, "end": end}


def point(lat, lon):
    return {"latitude": lat, "longitude": lon}


def feet(value, reference="MSL"):
    return {"value": value, "unit": "ft", "reference": reference}


PERIOD = window(at("1300"), at("1500"))


# ---------------------------------------------------------------------------------------------
# Resource additions: ground graphics for the OPORD and the alternate CAS channel for the FRAGO
# ---------------------------------------------------------------------------------------------

def area_measure(identifier, code, name, ring, description):
    return {"id": identifier, "type": code, "name": name, "active": deepcopy(PERIOD), "description": description,
            "geometry": {"kind": "polygon", "rings": [[point(*corner) for corner in (*ring, ring[0])]]}}


def order_measures():
    """Objective, named areas of interest and assembly area of Task Force Bastion."""
    return {
        "obj-cobalt": area_measure("obj-cobalt", "OBJ", "OBJ COBALT", ((35.085, 40.284), (35.085, 40.326), (35.110, 40.324), (35.110, 40.285)),
                                   "Objective of Task Force Bastion: the ISIS command post and vehicle park."),
        "nai-gainful": area_measure("nai-gainful", "NAI", "NAI 1 GAINFUL", ((35.155, 40.175), (35.155, 40.375), (35.275, 40.375), (35.275, 40.175)),
                                    "Named area of interest for the relocating SA-6 battery."),
        "nai-junction": area_measure("nai-junction", "NAI", "NAI 2 JUNCTION", ((35.165, 40.305), (35.165, 40.345), (35.195, 40.345), (35.195, 40.305)),
                                     "Road junction north of Cobalt that the SA-6 uses to relocate."),
        "aa-bastion": area_measure("aa-bastion", "AA", "AA BASTION", ((34.755, 40.204), (34.755, 40.303), (34.815, 40.304), (34.815, 40.205)),
                                  "Assembly area of Task Force Bastion south of PL BRASS."),
    }


def spins_measures():
    """Safe lane, IFF lines, minimum-risk route, identification safety point and jettison area of the SPINS."""
    def base(identifier, code, name, schema, description, **fields):
        return {"$schema": "urn:openaix:schema:" + schema + ":0.1.0-draft.1", "id": identifier, "type": code, "name": name,
                "active": deepcopy(PERIOD), "description": description, **fields}

    def line(west, east):
        return {"kind": "line", "points": [point(*west), point(*east)]}

    return {
        "sl-sage": base("sl-sage", "SL", "SL SAGE", "measure-route", "Safe lane through the Sage SHORAD engagement zone for aircraft that return to FARP Sage.",
                        geometry={"kind": "corridor", "points": [point(34.835, 40.225), point(34.529, 40.003)], "width": {"value": 2, "unit": "nm"}},
                        altitude={"lower": feet(7000), "upper": feet(9000)}, controlling_agency="darkstar", channels=["control-uhf"]),
        "iffoff-zinc": base("iffoff-zinc", "IFFOFF", "IFFOFF ZINC", "measure-line", "Northbound aircraft set Mode 3/A and Mode 1 to standby north of this line.",
                            geometry=line((35.005, 39.925), (35.005, 40.626))),
        "iffon-nickel": base("iffon-nickel", "IFFON", "IFFON NICKEL", "measure-line", "Southbound aircraft set every IFF mode on south of this line.",
                             geometry=line((34.975, 39.925), (34.975, 40.624))),
        "mrr-tinsel": base("mrr-tinsel", "MRR", "MRR TINSEL", "measure-route", "Minimum-risk return route from the Cobalt kill box to Cedar, east of the CAP and tanker orbits.",
                           geometry={"kind": "corridor", "points": [point(34.985, 40.475), point(34.529, 40.301), point(33.590, 39.002)], "width": {"value": 4, "unit": "nm"}},
                           altitude={"lower": feet(12000), "upper": feet(14000)}, controlling_agency="darkstar", channels=["control-uhf"]),
        "isp-tinsel": base("isp-tinsel", "POINT", "ISP TINSEL", "point", "Identification safety point on MRR TINSEL; returning flights report it to Darkstar.",
                           roles=["identification_safety"], position=point(34.529, 40.301), contact_agency="darkstar", channels=["control-uhf"]),
        "jettison-tin": base("jettison-tin", "ROZ", "Tin Flat jettison area", "measure-volume", "Desert area for the release of hung or unused stores before recovery.",
                             controlling_agency="banshee", channels=["banshee-uhf"],
                             components=[{"id": "tin-flat", "operation": "add", "geometry": {"kind": "circle", "center": point(34.835, 40.675), "radius": {"value": 2, "unit": "nm"}},
                                          "lower_limit": {"surface": True}, "upper_limit": feet(8000), "active": deepcopy(PERIOD)}]),
    }


def order_channels():
    return {"cas-alt-uhf": {"name": "Warhawk CAS alternate", "frequency": {"value": 318.4, "unit": "MHz", "modulation": "AM", "band": "uhf"},
                            "usage": "Alternate CAS check-in and terminal control with Axeman", "notes": "Use when Warhawk CAS is jammed or saturated; Axeman monitors both."}}


# ---------------------------------------------------------------------------------------------
# OPORD
# ---------------------------------------------------------------------------------------------

def task_organization():
    def unit(name, echelon, unit_type, callsign=None, parent=None, **extra):
        value = {"name": name, "echelon": echelon, "unit_type": unit_type, "coalition": "blue", **extra}
        if callsign:
            value["callsign"] = callsign
        if parent:
            value["parent"] = parent
        return value

    return {
        "caoc": unit("CJTF-OIR CAOC", "wing", "Combined air operations centre", "Kingpin", agency="caoc",
                           position=point(31.825, 36.781), commander="Col. Reyes"),
        "tf-bastion": unit("Task Force Bastion", "battalion", "Armoured infantry task force", "Bastion 6", "caoc", position=point(34.785, 40.255)),
        "tf-basin": unit("Task Force Basin", "battalion", "Mechanized infantry task force", "Basin 6", "caoc", position=point(34.785, 40.025)),
        "tacp-axeman": unit("Axeman TACP", "team", "Tactical air control party", "Axeman", "tf-bastion", position=point(35.005, 40.265)),
        "asoc-warhawk": unit("Warhawk ASOC", "squadron", "Air support operations squadron", "Warhawk", "caoc", agency="warhawk",
                             position=point(32.965, 37.794)),
        "strike-sqn": unit("Blue strike squadron", "squadron", "F-15E squadron", "Rage", "caoc"),
        "sead-sqn": unit("Blue suppression squadron", "squadron", "F-16CM squadron", "Weasel", "caoc"),
        "fighter-sqn": unit("Blue fighter squadron", "squadron", "F-15C and F-16C squadron", "Dodge", "caoc"),
        "cas-sqn": unit("Blue CAS squadron", "squadron", "A-10C squadron", "Hawg", "caoc"),
        "rescue-sqn": unit("Blue rescue squadron", "squadron", "HH-60G squadron", "Pedro", "caoc"),
        "awacs-sqn": unit("Darkstar detachment", "flight", "E-3G detachment", "Darkstar", "caoc", agency="darkstar"),
        "ada-btry": unit("Sage SHORAD battery", "platoon", "Short-range air defence platoon", "Sage", "tf-bastion", position=point(34.735, 40.225)),
        "sust-det": unit("Sage FARP detachment", "section", "Forward arming and refuelling detachment", "Sage Fuel", "tf-bastion",
                         position=point(34.735, 40.225)),
    }


def situation():
    return {
        "area_of_interest": {"measures": ["oir-aor"], "summary": "Eastern Jordan and eastern Syria up to the Euphrates valley; third-party fighters can enter from the north-west."},
        "area_of_operations": {
            "measures": ["oir-aor", "bastion-basin-boundary"],
            "terrain": {
                "key_terrain": [{"id": "kt-ridge", "name": "Cobalt ridge", "position": point(35.135, 40.295),
                                 "significance": "Observation over OBJ COBALT and the road junction."},
                                {"id": "kt-junction", "name": "Road junction", "measure": "nai-junction",
                                 "significance": "The SA-6 battery uses the junction to relocate."}],
                "avenues_of_approach": [{"id": "aoa-east", "name": "East valley road", "measures": ["pl-brass", "pl-nickel", "pl-zinc"],
                                         "echelon": "battalion", "direction": "north"}],
                "summary": "Flat desert and low ridges west of the Euphrates; the desert road to Deir ez-Zor is the only vehicle route north."},
            "weather": {
                "forecasts": [{"window": window(at("1200"), at("1600")), "ceiling": feet(25000), "visibility": {"value": 10, "unit": "km"},
                               "wind_direction": {"value": 230, "reference": "true"}, "wind_speed": {"value": 12, "unit": "kt"},
                               "temperature": {"value": 24, "unit": "C"}, "precipitation": "none",
                               "effects": "No restrictions on medium-altitude attacks or laser designation."}],
                "light_data": [{"date": "2026-10-02", "begin_morning_nautical_twilight": at("0225"), "sunrise": at("0315"),
                                "sunset": at("1505"), "end_evening_nautical_twilight": at("1555"), "moonrise": at("1640"),
                                "moonset": at("0840"), "moon_illumination_percent": 68}],
                "summary": "Clear, light south-west wind; the operation ends at sunset."}},
        "enemy_forces": {
            "units": [{"id": "red-sa6", "name": "SA-6 battery", "unit_type": "Surface-to-air missile battery", "echelon": "company",
                       "strength_percent": 100, "position": point(35.215, 40.265), "measure": "nai-gainful", "threats": ["sa-6"], "emitters": ["sa6-gainful"],
                       "targets": ["gainful-battery"], "as_of": at("1215")},
                      {"id": "red-cp", "name": "Cobalt command post", "unit_type": "Battalion command post", "echelon": "battalion",
                       "position": point(35.100, 40.300), "measure": "obj-cobalt", "targets": ["cobalt-array"], "as_of": at("1000")},
                      {"id": "red-air", "name": "Third-party fighter flight", "unit_type": "Fighter flight", "echelon": "flight",
                       "threats": ["red-air-fighters"], "as_of": at("1200")}],
            "courses_of_action": [{"id": "ecoa-1", "kind": "most_likely", "name": "Emit and relocate", "measures": ["nai-gainful", "nai-junction"],
                                   "summary": "The SA-6 emits as strikers approach Silver, then relocates north through the junction."},
                                  {"id": "ecoa-2", "kind": "most_dangerous", "name": "Ambush from the junction", "measures": ["nai-junction"],
                                   "summary": "The SA-6 stays silent at the junction and engages the strike package on egress."}],
            "summary": "A captured SA-6 battery defends the Cobalt command post; third-party fighters can approach from the north-west between 1310Z and 1400Z."},
        "friendly_forces": {
            "higher_two_levels": {"name": "CJTF-OIR land component", "mission": "Defeat ISIS in the Middle Euphrates River Valley with partner forces.",
                                  "commanders_intent": "Partner forces hold the west bank south of Deir ez-Zor with coalition fires."},
            "higher_one_level": {"name": "CJTF-OIR CAOC", "order": {"id": "oir-exord", "title": "OIR air operations directive"},
                                 "mission": "Give air support to the partner offensive near Deir ez-Zor on 2 October 2026.",
                                 "commanders_intent": "Destroy ISIS command and supply nodes without civilian harm.",
                                 "concept_of_operations": "Counterair first, then strike, CAS and rescue under one ATO and ACO."},
            "adjacent_units": [{"id": "adj-basin", "name": "Task Force Basin", "direction": "west", "boundary": "bastion-basin-boundary",
                                "mission": "Screen the west flank of Task Force Bastion."},
                               {"id": "adj-pewter", "name": "Task Force Pewter", "direction": "north",
                                "mission": "Hold north of the Bastion and Pewter RFL."}],
            "supporting_agencies": ["darkstar", "warhawk", "banshee"]},
        "interagency_organizations": [{"id": "blm-range", "name": "Deir ez-Zor civil council", "kind": "interagency",
                                       "objectives": ["No damage to the Quarry Springs pumping station"], "position": point(31.789, 36.715),
                                       "liaison": "caoc", "channels": ["banshee-uhf"]}],
        "civil_considerations": {
            "entries": [{"id": "cc-quarry", "category": "structures", "name": "Quarry Springs water facility", "measure": "quarry-nfa",
                         "significance": "No fires into the NFA."},
                        {"id": "cc-ranchers", "category": "people", "name": "Herders and farm traffic", "position": point(34.885, 39.975),
                         "significance": "Civilian vehicles on the west road; positive identification before any attack."}],
            "summary": "Civilians remain in the valley; one protected civil facility and one displaced-persons camp are in the area of operations."},
        "attachments_and_detachments": [{"unit": "tacp-axeman", "action": "attach", "relationship": "attached", "headquarters": "Task Force Bastion",
                                         "effective": at("1200")},
                                        {"unit": "ada-btry", "action": "attach", "relationship": "operational_control",
                                         "headquarters": "Task Force Bastion", "effective": at("1200")}],
        "assumptions": [{"id": "as-1", "assumption": "Weather permits medium-altitude operations."},
                        {"id": "as-2", "assumption": "The SA-6 relocates only after it emits."}],
    }


def execution():
    return {
        "commanders_intent": {
            "purpose": "Remove the Cobalt command post so that Task Force Bastion can advance to PL ZINC.",
            "key_tasks": [{"id": "kt-1", "task": "Clear the north before the push", "measures": ["cobalt-box"]},
                          {"id": "kt-2", "task": "Strike Cobalt during the kill-box window", "measures": ["obj-cobalt", "cobalt-box"]},
                          {"id": "kt-3", "task": "Recover the isolated aircrew", "measures": ["rescue-reservation"]}],
            "end_state": {"conditions": [{"id": "es-1", "domain": "enemy", "condition": "Cobalt aimpoints struck and the SA-6 suppressed."},
                                         {"id": "es-2", "domain": "friendly", "condition": "All aircraft recovered; rescue complete."}],
                          "summary": "Cobalt destroyed, no coalition losses, no civilian harm."}},
        "concept_of_operations": {
            "main_effort": "strike-sqn", "supporting_efforts": ["sead-sqn", "fighter-sqn", "cas-sqn", "tf-bastion"], "reserve": "rescue-sqn",
            "deep_area": "cobalt-box", "close_area": "obj-cobalt",
            "phases": [{"id": "ph-1", "number": 1, "name": "Counterair", "start": at("1300"), "end": at("1315"), "main_effort": "fighter-sqn",
                        "measures": ["falcon"], "ato_missions": ["sweep", "intercept", "cap-falcon"],
                        "end_condition": "Darkstar declares the north clear.", "summary": "Sweep and CAP gain control of the north."},
                       {"id": "ph-2", "number": 2, "name": "Strike", "start": at("1315"), "end": at("1350"), "main_effort": "strike-sqn",
                        "measures": ["juniper", "ip-silver", "cobalt-box"], "ato_missions": ["strike-cobalt", "sead-cobalt", "escort-anvil", "jam-anvil", "cas-cobalt"],
                        "start_condition": "Anvil package pushes from Juniper.", "summary": "Anvil strikes Cobalt with suppression and jamming; TF Bastion attacks to the LOA."},
                       {"id": "ph-3", "number": 3, "name": "Recovery", "start": at("1350"), "end": at("1500"), "main_effort": "rescue-sqn",
                        "measures": ["rescue-reservation", "cedar"], "ato_missions": ["pedro-csar"], "summary": "Rescue of the isolated aircrew and recovery to Muwaffaq Salti."}],
            "summary": "Counterair, then a package strike on Cobalt with CAS for Task Force Bastion, then rescue and recovery."},
        "schemes": {
            "maneuver": {"units": ["tf-bastion"], "measures": ["aa-bastion", "pl-brass", "pl-nickel", "pl-zinc", "obj-cobalt"],
                         "reserve": "tf-basin", "reserve_priorities": [{"rank": 1, "measure": "bastion-basin-boundary"}],
                         "summary": "TF Bastion crosses PL BRASS at 1330Z and attacks north to PL ZINC."},
            "intelligence": {"priority_of_effort": ["targeting", "situation_development"], "priorities": [{"rank": 1, "measure": "nai-gainful"}],
                             "summary": "Locate the SA-6 before the push."},
            "information_collection": {"reconnaissance_objectives": ["nai-gainful", "nai-junction"], "ato_missions": ["recce-gainful"],
                                       "summary": "Ghost searches NAI 1 and NAI 2 from 1300Z."},
            "fires": {"priorities": [{"rank": 1, "unit": "tf-bastion", "phase": "ph-2"}], "phases": ["ph-2"],
                      "air_support": ["strike-cobalt", "sead-cobalt", "cas-cobalt"], "measures": ["oir-fscl", "cobalt-box", "quarry-nfa"],
                      "restrictions": [{"id": "fr-1", "instruction": "No fires into the Quarry Springs NFA.", "measures": ["quarry-nfa"]}],
                      "summary": "Air interdiction beyond the FSCL in the Cobalt kill box; CAS short of the FSCL under Axeman."},
            "protection": {"priorities": [{"rank": 1, "asset": "Sage FARP", "measure": "sage-shoradez"}], "reaction_forces": ["tf-basin"],
                           "summary": "SHORAD covers the FARP; Basin is the reaction force."},
            "engineering": {"priorities": [{"rank": 1, "measure": "pl-brass"}], "units": ["tf-bastion"],
                            "summary": "Mark one lane through the wire at PL BRASS."},
            "air_and_missile_defense": {"units": ["ada-btry"], "measures": ["sage-shoradez"], "weapons_control_status": "tight",
                                        "air_defense_warning": "yellow", "engagement_authority": "darkstar",
                                        "summary": "Sage defends the FARP in weapons tight."},
            "airspace_control": {"agencies": ["darkstar", "banshee", "warhawk"], "coordinating_altitude": "bastion-ca",
                                 "measures": ["south-transit", "mesa", "cobalt-box", "rescue-reservation"],
                                 "summary": "Darkstar controls the orbits and the corridor; Warhawk controls below 11000 feet MSL over TF Bastion."}},
        "tasks_to_subordinate_units": [
            {"unit": "tf-bastion", "tasks": [{"id": "t-bastion-1", "task": "Attack to PL ZINC (LOA)", "purpose": "Fix the Cobalt defenders",
                                             "phase": "ph-2", "window": window(at("1330"), at("1450")), "measures": ["pl-brass", "pl-zinc", "obj-cobalt"]}]},
            {"unit": "strike-sqn", "tasks": [{"id": "t-strike-1", "task": "Strike the Cobalt aimpoints", "purpose": "Destroy the command post",
                                              "phase": "ph-2", "ato_missions": ["strike-cobalt"], "measures": ["cobalt-box"]}]},
            {"unit": "rescue-sqn", "tasks": [{"id": "t-pedro-1", "task": "Recover the isolated aircrew", "phase": "ph-3", "ato_missions": ["pedro-csar"],
                                              "measures": ["rescue-reservation"]}]}],
        "coordinating_instructions": {
            "effective_time": at("1200"),
            "timeline": [{"id": "tl-push", "event": "Anvil push from Juniper", "time": at("1315"), "phase": "ph-2"},
                         {"id": "tl-ld", "event": "TF Bastion crosses PL BRASS", "time": at("1330"), "phase": "ph-2"},
                         {"id": "tl-kb", "event": "Cobalt kill box closes", "time": at("1350")},
                         {"id": "tl-rescue", "event": "Rescue starts", "condition": "Darkstar reports the survivor position.", "phase": "ph-3"}],
            "ccir": {"priority_intelligence_requirements": [
                        {"id": "pir-1", "number": "PIR 1", "question": "Where is the SA-6 battery at 1315Z?",
                         "indicators": ["Straight Flush radar emission", "Launcher movement through the junction"],
                         "measures": ["nai-gainful", "nai-junction"], "decision_point": "dp-1", "latest_time": at("1310"), "report_to": "caoc"}],
                     "friendly_force_information_requirements": [
                        {"id": "ffir-1", "number": "FFIR 1", "question": "Is any aircraft isolated?", "report_to": "darkstar"}]},
            "eefi": [{"id": "eefi-1", "item": "Push time of the Anvil package"}],
            "fire_support_coordination_measures": ["oir-fscl", "pewter-rfl", "cobalt-box", "quarry-nfa"],
            "airspace_coordinating_measures": ["bastion-ca", "south-transit", "rescue-reservation", "sage-shoradez"],
            "rules_of_engagement": [{"id": "roe-1", "number": "R-1", "rule": "Collateral damage estimate before every preplanned strike."},
                                    {"id": "roe-2", "number": "R-2", "rule": "Positive identification before any attack.", "measures": ["cobalt-box"]}],
            "risk_reduction": {"mopp_level": "mopp_0", "emission_control": "unrestricted", "fratricide_measures": ["pl-zinc", "oir-fscl"],
                               "instructions": [{"id": "rr-1", "instruction": "CAS aircraft use the last reported phase line of TF Bastion."}]},
            "personnel_recovery": {"recovery_forces": ["pedro-csar"], "agency": "darkstar", "channels": ["rescue-uhf"], "measures": ["rescue-reservation"],
                                   "summary": "Isolated aircrew evade south to the rescue reservation and authenticate per the SPINS."},
            "themes_and_messages": [{"id": "msg-1", "kind": "emphasize", "message": "Coalition strikes target ISIS, not the population.", "audience": "Local population"}],
            "other": [{"id": "ci-1", "instruction": "All times are UTC."}]},
    }


def sustainment():
    return {
        "priorities": [{"rank": 1, "unit": "tf-bastion"}, {"rank": 2, "unit": "rescue-sqn"}],
        "logistics": {"supply_points": [{"id": "sp-sage", "name": "FARP Sage", "kind": "forward_arming_and_refuelling_point", "classes": ["III", "V"],
                                         "airfield": "farp-sage", "unit": "sust-det", "window": deepcopy(PERIOD)}],
                      "routes": ["marshal-entry"], "summary": "Helicopters refuel at FARP Sage; fixed-wing aircraft recover to Muwaffaq Salti or Prince Hassan."},
        "personnel": {"casualty_report": "misrep", "summary": "Units report casualties in the MISREP."},
        "health_service_support": {
            "facilities": [{"id": "mtf-ojms", "name": "Muwaffaq Salti clinic", "role": 2, "airfield": "ojms"},
                           {"id": "mtf-amman", "name": "Amman military hospital", "role": 3, "position": point(31.972, 35.992)}],
            "evacuation": {"agency": "banshee", "request_channels": ["banshee-uhf"],
                           "exchange_points": [{"id": "axp-1", "name": "AXP Sage", "position": point(34.735, 40.215)}],
                           "summary": "Banshee coordinates casualty evacuation from AXP Sage to Muwaffaq Salti."},
            "summary": "Role 2 care at Muwaffaq Salti; casualties from the valley go through AXP Sage."},
        "financial_management": {"programs": [{"id": "fund-ex", "name": "Contingency flying hours", "unit": "caoc",
                                               "limit": {"amount": 250000, "currency": "USD"}}],
                                 "summary": "Flying costs come from the contingency flying-hour program."},
        "summary": "Sustainment supports TF Bastion first; the FARP opens at 1300Z.",
    }


def command_and_signal():
    return {
        "command": {"leaders": [{"role": "commander", "unit": "caoc", "command_post": "cp-main"},
                                {"role": "TF Bastion commander", "unit": "tf-bastion", "command_post": "cp-bastion", "phase": "ph-2"}],
                    "succession": ["caoc", "tf-bastion", "tf-basin"],
                    "liaison": [{"id": "lno-1", "unit": "tf-bastion", "agency": "warhawk", "position": point(32.965, 37.794)}]},
        "command_posts": [{"id": "cp-main", "name": "Kingpin", "kind": "main", "unit": "caoc", "agency": "caoc",
                           "position": point(31.825, 36.781), "operational": window(at("1000"), at("1700"))},
                          {"id": "cp-bastion", "name": "TF Bastion TAC", "kind": "tactical", "unit": "tf-bastion", "position": point(34.805, 40.267),
                           "operational": deepcopy(PERIOD), "controls": ["ph-2"]}],
        "signal": {"pace_plans": [{"id": "pace-cmd", "function": "command", "primary": {"method": "voice_uhf", "channel": "ops-uhf"},
                                   "alternate": {"method": "voice_uhf", "channel": "control-uhf"}, "contingency": {"method": "chat"},
                                   "emergency": {"method": "telephone"}}],
                   "channels": ["ops-uhf", "control-uhf", "banshee-uhf", "cas-uhf", "rescue-uhf", "tanker-uhf", "strike-vhf"],
                   "summary": "UHF voice on the resource catalogue channels; Link 16 through Darkstar."},
    }


def annexes():
    return {
        "A": {"relationships": [{"unit": "tacp-axeman", "relationship": "attached", "to": "tf-bastion", "effective": at("1200")},
                                {"unit": "ada-btry", "relationship": "operational_control", "to": "tf-bastion"},
                                {"unit": "asoc-warhawk", "relationship": "direct_support", "to": "tf-bastion", "phase": "ph-2"},
                                {"unit": "cas-sqn", "relationship": "tactical_control", "headquarters": "Kingpin"}],
              "summary": "Air units stay under Kingpin; Axeman and Sage go to TF Bastion."},
        "B": {"threat_assessments": [{"threat": "sa-6", "enemy_unit": "red-sa6", "capability": "Medium-altitude engagement to 14 km.",
                                      "emitters": ["sa6-gainful", "sa3-zinc", "sa8-nickel"],
                                      "position": point(35.215, 40.265), "as_of": at("1215"), "confidence": "moderate"},
                                     {"threat": "red-air-fighters", "capability": "Two to four fighters with semi-active missiles.",
                                      "as_of": at("1200"), "confidence": "high"}],
              "high_value_targets": [{"id": "hvt-1", "name": "Cobalt command post", "function": "command_and_control", "target": "cobalt-array"},
                                     {"id": "hvt-2", "name": "SA-6 battery", "function": "air_defense", "target": "gainful-battery", "threat": "sa-6"}],
              "products": [{"id": "intsum", "name": "Intelligence summary", "recipients": ["tf-bastion"], "agencies": ["darkstar", "warhawk"],
                            "due": at("1230"), "interval_minutes": 60, "channel": "ops-uhf"}],
              "summary": "The SA-6 location is the main intelligence gap."},
        "C": {"operation_overlay": ["oir-aor", "bastion-basin-boundary", "aa-bastion", "pl-brass", "pl-nickel", "pl-zinc", "obj-cobalt", "trp-01"],
              "decision_points": [{"id": "dp-1", "name": "DP 1 push", "decision": "Push Anvil, or delay the push by 10 minutes.",
                                   "trigger": "SA-6 location unknown at 1310Z.", "measures": ["nai-gainful"], "requirements": ["pir-1"],
                                   "phase": "ph-2", "latest_time": at("1310")}],
              "airspace": {"airspace_control_agency": "darkstar", "coordinating_altitude": "bastion-ca",
                           "measures": ["south-transit", "mesa", "rescue-reservation", "sage-shoradez", "bastion-ca"],
                           "agencies": ["banshee", "warhawk"], "summary": "Procedural control below the CA; positive control above."},
              "rules_of_engagement": [{"id": "roe-c-1", "number": "R-3", "rule": "Hostile declaration only by Darkstar.", "measures": ["falcon"]}],
              "electromagnetic": {"emission_control": [{"id": "emcon-1", "level": "reduced", "window": window(at("1300"), at("1315")),
                                                        "units": ["tf-bastion"]}],
                                  "jamming_authority": "caoc", "jamming": [jamming_window()],
                                  "summary": "Grizzly jams only in the Anvil window."},
              "personnel_recovery": {"recovery_forces": ["pedro-csar"], "agency": "darkstar", "channels": ["rescue-uhf"],
                                     "safe_areas": ["rescue-reservation"], "contact_points": ["cedar"],
                                     "summary": "Pedro holds at Cedar until Darkstar clears the rescue."},
              "summary": "Operation overlay, decision support, airspace, ROE, CEMA and personnel recovery."},
        "D": {"fire_support_coordination_measures": ["oir-fscl", "pewter-rfl", "cobalt-box", "quarry-nfa"],
              "priority_of_fires": [{"rank": 1, "unit": "tf-bastion", "phase": "ph-2"}],
              "targeting": {"high_payoff_targets": [{"id": "hpt-1", "priority": 1, "target": "gainful-battery", "threat": "sa-6", "emitter": "sa6-gainful", "timing": "immediate",
                                                     "ato_missions": ["sead-cobalt"], "effect": "suppress", "assessment_required": True, "phase": "ph-2"},
                                                    {"id": "hpt-2", "priority": 2, "target": "cobalt-array", "timing": "planned",
                                                     "ato_missions": ["strike-cobalt"], "effect": "destroy", "assessment_required": True, "phase": "ph-2"}],
                            "time_sensitive_targets": [],
                            "target_reference_points": ["trp-01"]},
              "field_artillery": {"units": ["tf-bastion"], "priorities": [{"rank": 1, "measure": "obj-cobalt"}]},
              "air_support": {"cas_allocations": [{"unit": "tf-bastion", "sorties": 2, "window": window(at("1330"), at("1430")), "ato_missions": ["cas-cobalt"], "phase": "ph-2"}],
                              "cas_briefs": [{
                                  "id": "cas-1", "ato_mission": "cas-cobalt", "controller": "warhawk", "control_type": "type_2", "method_of_attack": "bomb_on_target",
                                  "initial_point": "ip-silver", "heading": {"value": 46, "reference": "magnetic"}, "distance": {"value": 15.3, "unit": "nm"},
                                  "target_elevation": {"value": 685, "unit": "ft", "reference": "MSL"},
                                  "target_description": "Revetted vehicle park, four trucks.", "target_position": point(35.093, 40.314),
                                  "target": "cobalt-array", "mark": "laser", "laser_code": "1688", "laser_target_line": {"value": 13, "reference": "magnetic"},
                                  "friendly_direction": "south_west", "friendly_distance": {"value": 10.7, "unit": "km"}, "egress_point": "cedar",
                                  "time_on_target": at("1340"), "remarks": "Friendlies are south of PL ZINC. No attack headings over the Lantern village."}],
                              "agencies": ["warhawk"], "points": ["ip-silver", "cedar", "marshal"], "ato_missions": ["strike-cobalt", "recce-gainful"]},
              "naval_fire_support": {"units": [], "fire_support_areas": []},
              "air_and_missile_defense": {"weapons_control": [{"status": "tight", "measure": "sage-shoradez", "window": deepcopy(PERIOD)}],
                                          "warnings": [{"level": "yellow", "measure": "oir-aor", "window": deepcopy(PERIOD)}],
                                          "defended_assets": [{"id": "da-farp", "name": "FARP Sage", "priority": 1, "airfield": "farp-sage"}],
                                          "engagement_authorities": ["darkstar"], "measures": ["sage-shoradez"]},
              "summary": "Fires support TF Bastion short of the FSCL; air interdiction in the Cobalt kill box."},
        "E": {"protection_priorities": [{"id": "pp-1", "priority": 1, "name": "FARP Sage", "airfield": "farp-sage"},
                                        {"id": "pp-2", "priority": 2, "name": "TF Bastion TAC", "unit": "tf-bastion"}],
              "risk_controls": [{"id": "rc-1", "hazard": "Fratricide between CAS and TF Bastion", "control": "Type 2 control and the last reported phase line.",
                                 "initial_risk": "high", "residual_risk": "medium", "units": ["tf-bastion", "cas-sqn"]},
                                {"id": "rc-2", "hazard": "Mid-air collision in Mesa holding", "control": "One flight per level, assigned by Darkstar.",
                                 "initial_risk": "medium", "residual_risk": "low"}],
              "reaction_forces": [{"unit": "tf-basin", "area": "oir-aor", "response_minutes": 30}],
              "eefi": [{"id": "eefi-e-1", "item": "Location of FARP Sage"}], "mopp_level": "mopp_0"},
        "F": {"supply_points": [{"id": "sp-f-sage", "name": "FARP Sage", "kind": "forward_arming_and_refuelling_point", "classes": ["III", "V"],
                                 "airfield": "farp-sage", "unit": "sust-det"}],
              "allocations": [{"unit": "rescue-sqn", "supply_class": "III", "item": "JP-8", "quantity": 2000, "unit_of_measure": "gal"}],
              "movements": [{"id": "mv-1", "unit": "tf-bastion", "start_point": "aa-bastion", "release_point": "pl-brass",
                             "departure": at("1300"), "arrival": at("1325")}],
              "maintenance_priorities": [{"rank": 1, "unit": "rescue-sqn"}],
              "medical_facilities": [{"id": "mtf-f-ojms", "name": "Muwaffaq Salti clinic", "role": 2, "airfield": "ojms"}],
              "medical_evacuation": {"agency": "banshee", "request_channels": ["banshee-uhf"]}},
        "G": {"obstacles": [{"id": "obs-1", "name": "Wire at PL BRASS", "kind": "wire", "effect": "disrupt", "position": point(34.847, 40.297),
                             "status": "prepared"}],
              "lanes": [{"id": "lane-1", "name": "Lane RED", "entry": point(34.840, 40.293), "exit": point(34.853, 40.297),
                         "width": {"value": 8, "unit": "m"}, "marking": "Orange panels by day, green chemical lights by night", "unit": "tf-bastion"}],
              "obstacle_zones": [], "survivability_priorities": [{"rank": 1, "asset": "TF Bastion TAC"}]},
        "H": {"nets": [{"id": "net-cmd", "name": "Bastion command", "kind": "command", "primary": "ops-uhf", "alternate": "control-uhf",
                        "control": "caoc", "members": ["tf-bastion", "tf-basin"]},
                       {"id": "net-air", "name": "Darkstar control", "kind": "air_ground", "primary": "control-uhf", "control": "darkstar"},
                       {"id": "net-cas", "name": "Warhawk CAS", "kind": "fires", "primary": "cas-uhf", "control": "warhawk", "members": ["tacp-axeman"]},
                       {"id": "net-rescue", "name": "Rescue common", "kind": "air_ground", "primary": "rescue-uhf", "control": "darkstar"}],
              "call_signs": [{"unit": "tacp-axeman", "callsign": "Axeman 1-1", "window": deepcopy(PERIOD)},
                             {"agency": "warhawk", "callsign": "Warhawk"}],
              "retransmission_sites": [{"id": "rt-ridge", "name": "Cobalt ridge relay", "position": point(34.985, 40.225), "channels": ["cas-uhf"],
                                        "unit": "tf-bastion", "window": deepcopy(PERIOD)}],
              "restricted_frequencies": [{"channel": "rescue-uhf", "kind": "protected", "agency": "darkstar"},
                                         {"frequency": {"value": 243.0, "unit": "MHz", "modulation": "AM", "band": "uhf"}, "kind": "taboo"}],
              "comsec": [{"id": "key-1", "key": "BASTION KEY 02", "window": window(at("0000"), at("0000", 3)), "channels": ["ops-uhf"]}]},
        "J": {"objectives": [{"id": "pa-1", "objective": "Show precise coalition strikes that protect civilians."}],
              "messages": [{"id": "pa-msg-1", "kind": "emphasize", "message": "Coalition aircraft avoid the river crossings and the camp.", "audience": "Local population"}],
              "release_authorities": [{"topic": "Strike imagery", "unit": "caoc"}],
              "ground_rules": [{"id": "gr-1", "objective": "No imagery of the FARP."}]},
        "K": {"protected_sites": [{"id": "ps-quarry", "name": "Quarry Springs water facility", "kind": "infrastructure", "restriction": "no_strike",
                                   "measure": "quarry-nfa"}],
              "dislocated_civilian_routes": [],
              "tasks": [{"id": "k-1", "task": "Warn the civil council of the road closure times", "window": window(at("0900"), at("1000"))}],
              "centres": [{"id": "cmoc-1", "name": "Tanf CMOC", "position": point(33.495, 38.640), "unit": "caoc", "channel": "banshee-uhf"}]},
        "L": {"named_areas_of_interest": ["nai-gainful", "nai-junction"],
              "collection_tasks": [{"id": "ct-1", "requirement": "pir-1", "indicator": "Straight Flush radar emission", "measure": "nai-gainful",
                                    "ato_mission": "recce-gainful", "window": window(at("1300"), at("1340")), "report_to": "caoc", "report": "inflightrep"},
                                   {"id": "ct-2", "requirement": "pir-1", "indicator": "Launcher movement through the junction", "measure": "nai-junction",
                                    "unit": "tacp-axeman", "window": window(at("1300"), at("1400")), "report_to": "warhawk"}],
              "handover_lines": ["pl-zinc"]},
        "M": {"measures_of_effectiveness": [{"id": "moe-1", "statement": "The SA-6 does not engage the Anvil package.",
                                             "indicators": [{"id": "ind-1", "indicator": "SA-6 shots against Anvil", "threshold": "Zero"}]}],
              "measures_of_performance": [{"id": "mop-1", "task": "Strike the Cobalt aimpoints", "indicator": "Aimpoints struck within TOT plus or minus 1 minute",
                                           "units": ["strike-sqn"]}],
              "reframing_criteria": [{"id": "rf-1", "objective": "Two or more coalition losses before 1330Z."}]},
        "N": {"capabilities": [{"id": "sp-gps", "mission_area": "positioning_navigation_timing", "provider": "GPS", "window": deepcopy(PERIOD),
                                "units": ["strike-sqn", "tf-bastion"]}],
              "navigation_outages": [{"id": "gps-jam-1", "window": window(at("1320"), at("1335")), "measure": "nai-gainful",
                                      "expected_error": {"value": 50, "unit": "m"}}],
              "satellite_channels": []},
        "P": {"agreements": [{"id": "agr-range", "name": "Host nation basing agreement", "kind": "technical", "parties": ["CJTF-OIR", "Royal Jordanian Air Force"],
                              "effective": window(at("0000"), at("0000", 3))}],
              "support": [{"id": "hns-fuel", "category": "fuel", "provider": "Prince Hassan fuel section", "agreement": "agr-range", "airfield": "prince-hassan"}]},
        "Q": {"battle_rhythm": [{"id": "br-1", "name": "Mass brief", "kind": "briefing", "start": at("1100"), "duration_minutes": 60, "chair": "caoc"},
                                {"id": "br-2", "name": "Ops update", "kind": "update", "start": at("1300"), "interval_minutes": 30, "duration_minutes": 10,
                                 "chair": "caoc", "attendees": ["tf-bastion"], "channel": "ops-uhf"},
                                {"id": "br-3", "name": "Mission debrief", "kind": "meeting", "start": at("1700"), "duration_minutes": 90, "chair": "caoc"}],
              "information_systems": [{"id": "is-tacview", "name": "Air picture recorder", "purpose": "Records the air picture for the debrief", "units": ["caoc"]},
                                      {"id": "is-link16", "name": "Link 16 network", "purpose": "Air picture to fighters and Darkstar", "channels": ["control-uhf"]}]},
        "R": {"reports": [{"report": "misrep", "from_units": ["strike-sqn", "cas-sqn", "fighter-sqn"], "to_agency": "caoc",
                           "trigger": "Within 30 minutes of landing", "channel": "ops-uhf"},
                          {"report": "bda", "from_units": ["strike-sqn"], "to_agency": "caoc", "trigger": "After each attack"},
                          {"report": "inflightrep", "from_units": ["fighter-sqn"], "to_agency": "darkstar", "channel": "control-uhf"}]},
        "S": {"classified_annex": {"id": "oir-annex-s", "title": "Annex S, held by the CAOC"},
              "capabilities": [{"id": "sto-1", "name": "Special technical operations item", "functional_area": "area_1", "phase": "ph-2", "coordinator": "caoc"}],
              "summary": "The CAOC holds the details; this order contains no classified data."},
        "U": {"inspections": [{"id": "ig-1", "subject": "FARP fuel safety procedures", "units": ["sust-det"], "window": window(at("1100"), at("1200"))}],
              "assistance_points": [{"id": "iga-1", "unit": "caoc", "position": point(31.825, 36.781), "window": window(at("0800"), at("1800"))}]},
        "V": {"tasks": [{"id": "v-1", "task": "Confirm the road closure with the civil council", "organization": "blm-range", "unit": "caoc",
                         "time": at("1000"), "area": "other"}],
              "legal_considerations": [{"id": "lc-1", "objective": "Strikes stay inside the approved target list and the coalition ROE."}]},
        "W": {"requirements": [{"id": "ocs-1", "requirement": "Contract fuel truck for FARP Sage", "category": "theater_support", "contractor": "Desert Fuel Services",
                                "units": ["sust-det"], "airfield": "farp-sage", "window": deepcopy(PERIOD)},
                               {"id": "ocs-2", "requirement": "Transient aircraft maintenance", "category": "external_support", "contractor": "Jordan Aero Services",
                                "airfield": "ojms", "window": window(at("0800"), at("1800"))}],
              "offices": [{"id": "ko-ojms", "name": "Muwaffaq Salti contracting office", "unit": "caoc", "position": point(31.825, 36.781)}],
              "accountability_report": "misrep"},
        "Z": {"recipients": [{"unit": "tf-bastion", "purpose": "action", "copies": 2}, {"unit": "tf-basin", "purpose": "action", "copies": 2},
                             {"agency": "darkstar", "purpose": "action", "copies": 1}, {"agency": "warhawk", "purpose": "action", "copies": 1},
                             {"name": "Deir ez-Zor civil council", "purpose": "information", "copies": 1}]},
    }


def jamming_window():
    """Grizzly stand-off jamming in the Anvil push window; Annex C, Appendix 12 and the SPINS share it."""
    return {"id": "jam-anvil-window", "window": window(at("1320"), at("1345")), "emitters": ["sa6-gainful", "sa3-zinc"],
            "ato_missions": ["jam-anvil"], "area": "jamming-orbit", "authority": "caoc",
            "protected_frequencies": [{"channel": "control-uhf", "kind": "protected", "agency": "darkstar"},
                                      {"channel": "rescue-uhf", "kind": "protected", "agency": "darkstar"},
                                      {"frequency": {"value": 243.0, "unit": "MHz", "modulation": "AM", "band": "uhf"}, "kind": "taboo"}]}


def opord(version):
    return {"$schema": f"urn:openaix:schema:opord:{version}", "kind": "opord", "schema_version": version,
            "meta": {"id": "oir-opord", "revision": "1", "title": "OIR OPORD 26-01", "issued_at": at("1130"),
                     "issuing_unit": "CJTF-OIR CAOC", "operation": "INHERENT RESOLVE", "classification": "UNCLASSIFIED", "coalition": "blue"},
            "order_number": "26-01", "operation_name": "INHERENT RESOLVE", "issuing_headquarters": "CJTF-OIR CAOC",
            "date_time": at("1130"), "time_zone": "Z", "effective_time": at("1200"), "period": deepcopy(PERIOD),
            "orders": deepcopy(ORDERS), "resources_ref": deepcopy(RESOURCES_REF),
            "references": [{"id": "oir-aco", "revision": "2", "title": "OIR ACO"},
                           {"id": "oir-spins", "revision": "1", "title": "OIR SPINS"}],
            "task_organization": task_organization(), "situation": situation(),
            "mission": {"statement": "OIR air forces destroy the Cobalt compound on 2 October 2026 between 1300Z and 1500Z to train a coordinated strike, counterair, CAS and rescue package.",
                        "units": ["strike-sqn", "sead-sqn", "fighter-sqn", "cas-sqn", "rescue-sqn", "tf-bastion"], "task": "Destroy the Cobalt compound",
                        "purpose": "Train a coordinated strike, counterair, CAS and rescue package", "window": deepcopy(PERIOD), "objectives": ["obj-cobalt"]},
            "execution": execution(), "sustainment": sustainment(), "command_and_signal": command_and_signal(),
            "acknowledgement": {"acknowledge": True, "instructions": "Acknowledge on Bastion command by 1200Z."},
            "authentication": {"commander_name": "Reyes", "commander_rank": "Colonel", "authenticator_name": "Major Lin", "authenticator_position": "CAOC operations officer"},
            "annexes": annexes(), "extensions": {**deepcopy(EXERCISE), **deepcopy(PRINT)}}


# ---------------------------------------------------------------------------------------------
# FRAGO: a delta against OPORD revision 1, the SPINS and the ATO
# ---------------------------------------------------------------------------------------------

def frago(version):
    opord_ref = {"kind": "opord", "id": "oir-opord", "revision": "1"}
    return {"$schema": f"urn:openaix:schema:frago:{version}", "kind": "frago", "schema_version": version,
            "meta": {"id": "oir-frago-01", "revision": "1", "title": "FRAGO 01 to OIR OPORD 26-01", "issued_at": at("1245"),
                     "issuing_unit": "CJTF-OIR CAOC", "operation": "INHERENT RESOLVE"},
            "frago_number": "01", "issuing_headquarters": "CJTF-OIR CAOC", "date_time": at("1245"), "time_zone": "Z",
            "effective_time": at("1300"), "base_order": {"id": "oir-opord", "revision": "1"},
            "summary": "SA-6 reported at the junction: the LOA moves back to PL NICKEL, the SA-6 becomes TST-01, CAS moves to the alternate frequency and Hawg stays 15 minutes longer.",
            "changes": [
                {"target": dict(opord_ref), "op": "replace", "path": "/execution/tasks_to_subordinate_units/0/tasks/0/task", "value": "Attack to PL NICKEL (LOA)"},
                {"target": dict(opord_ref), "op": "replace", "path": "/execution/tasks_to_subordinate_units/0/tasks/0/measures/1", "value": "pl-nickel",
                 "remarks": "The limit of advance moves from PL ZINC to PL NICKEL."},
                {"target": dict(opord_ref), "op": "add", "path": "/annexes/D/targeting/time_sensitive_targets/-",
                 "value": {"id": "tst-01", "tst_number": "TST-01", "target": "gainful-battery", "priority": 1, "window": window(at("1300"), at("1400")),
                           "engagement_authority": "caoc", "ato_missions": ["sead-cobalt", "strike-cobalt"]}},
                {"target": dict(opord_ref), "op": "replace", "path": "/annexes/H/nets/2/primary", "value": "cas-alt-uhf"},
                {"target": {"kind": "spins", "id": "oir-spins", "revision": "1"}, "op": "replace", "path": "/communications/nets/2/channel",
                 "value": "cas-alt-uhf"},
                {"target": {"kind": "ato", "id": "oir-ato", "revision": "1"}, "op": "replace", "path": "/missions/7/tasking/availability/end",
                 "value": at("1445")},
                {"target": dict(opord_ref), "op": "remove", "path": "/execution/coordinating_instructions/ccir/priority_intelligence_requirements/0/decision_point"},
                {"target": dict(opord_ref), "op": "remove", "path": "/annexes/C/decision_points/0", "remarks": "The SA-6 location answers DP 1."},
            ],
            "acknowledgement": {"acknowledge": True, "instructions": "Acknowledge on Bastion command."},
            "authentication": {"commander_name": "Reyes", "commander_rank": "Colonel"},
            "references": [{"id": "oir-opord", "revision": "1", "title": "OIR OPORD 26-01"}],
            "extensions": deepcopy(EXERCISE)}


# ---------------------------------------------------------------------------------------------
# SPINS
# ---------------------------------------------------------------------------------------------

def spins(version):
    return {"$schema": f"urn:openaix:schema:spins:{version}", "kind": "spins", "schema_version": version, "scope": "standing",
            "meta": {"id": "oir-spins", "revision": "1", "title": "OIR Special Instructions (SPINS)", "issued_at": at("1100"),
                     "issuing_unit": "CJTF-OIR CAOC", "operation": "INHERENT RESOLVE"},
            "period": deepcopy(PERIOD), "orders": {"opord": {"id": "oir-opord", "revision": "1"}, "ato": deepcopy(ORDERS["ato"]), "aco": deepcopy(ORDERS["aco"])},
            "resources_ref": deepcopy(RESOURCES_REF),
            "rules_of_engagement": {"rules": [{"id": "spins-roe-1", "number": "R-1", "rule": "Collateral damage estimate before every preplanned strike."},
                                              {"id": "spins-roe-2", "number": "R-2", "rule": "Attacks in the Cobalt kill box need Banshee clearance.",
                                               "measures": ["cobalt-box"], "window": window(at("1320"), at("1350"))},
                                              {"id": "spins-roe-3", "number": "R-3", "rule": "No fires into the Quarry Springs NFA.", "measures": ["quarry-nfa"]}],
                                    "measures": ["cobalt-box", "quarry-nfa", "oir-fscl"], "summary": "Positive identification before any attack."},
            "communications": {"nets": [{"id": "sn-control", "name": "Darkstar control", "channel": "control-uhf", "agency": "darkstar", "purpose": "Air picture and control"},
                                        {"id": "sn-range", "name": "Banshee", "channel": "banshee-uhf", "agency": "banshee", "purpose": "Kill box status and procedural control"},
                                        {"id": "sn-cas", "name": "Warhawk CAS", "channel": "cas-uhf", "agency": "warhawk", "purpose": "CAS check-in"},
                                        {"id": "sn-tanker", "name": "Shell boom", "channel": "tanker-uhf", "purpose": "Tanker rendezvous"},
                                        {"id": "sn-rescue", "name": "Rescue common", "channel": "rescue-uhf", "agency": "darkstar", "purpose": "Personnel recovery"}],
                               "brevity": [{"id": "br-bastion", "term": "BASTION", "meaning": "Cobalt kill box is open."},
                                           {"id": "br-knock", "term": "KNOCK IT OFF", "meaning": "All flights stop the engagement for a safety problem."}],
                               "remarks": "Brevity per ATP 1-02.1 unless this section changes it."},
            "identification": {"iff": [{"id": "iff-m1", "mode": "mode_1", "code": "22", "window": deepcopy(PERIOD)},
                                       {"id": "iff-m3", "mode": "mode_3a", "code": "4521", "window": deepcopy(PERIOD),
                                        "ato_missions": ["strike-cobalt", "sead-cobalt", "escort-anvil", "jam-anvil"]},
                                       {"id": "iff-m4", "mode": "mode_4", "window": deepcopy(PERIOD)}],
                               "code_words": [{"id": "cw-1", "word": "BRONZE", "meaning": "Strike complete", "window": deepcopy(PERIOD)}]},
            "personnel_recovery": {"agency": "darkstar", "rescue_forces": ["pedro-csar"], "channels": ["rescue-uhf"], "procedures": ["sar-recognition"],
                                   "authentication": [{"window": deepcopy(PERIOD), "number": 7, "letter": "K", "word": "OLIVE"}],
                                   "safe_areas": ["rescue-reservation"], "isoprep": "oir-isoprep",
                                   "remarks": "Survivors mark with day smoke or an infrared strobe at night."},
            "divert_and_abort": {"abort_criteria": [{"id": "ab-1", "condition": "Weather below 3000 feet ceiling at Muwaffaq Salti", "action": "divert"},
                                                    {"id": "ab-2", "condition": "Loss of Darkstar control for more than 5 minutes in the kill box", "action": "hold"},
                                                    {"id": "ab-3", "condition": "Loss of the tanker before the push", "action": "abort"}],
                                 "divert_airfields": [{"airfield": "prince-hassan", "priority": 1}, {"airfield": "h4", "priority": 2, "conditions": "East of 38E only"}],
                                 "abort_code": "TUMBLEWEED"},
            "airspace_notes": [{"id": "an-transit", "measures": ["south-transit", "juniper", "marshal"],
                                "note": "Inbound traffic uses the south transit corridor from Juniper to Marshal between 10000 and 12000 feet MSL."},
                               {"id": "an-holding", "measures": ["mesa"], "note": "Mesa holding at Marshal: one flight per level, 14000 or 16000 feet MSL, assigned by Darkstar."},
                               {"id": "an-ca", "measures": ["bastion-ca"], "note": "Below 11000 feet MSL over TF Bastion, contact Warhawk."}],
            "check_in": [{"id": "ci-darkstar", "agency": "darkstar", "channels": ["control-uhf"], "contact_point": "juniper",
                          "check_in_items": ["callsign", "mission_number", "position", "altitude", "playtime"], "check_out": "Check out at Cedar on egress."},
                         {"id": "ci-warhawk", "agency": "warhawk", "channels": ["cas-uhf"], "contact_point": "cedar", "procedure": "cas-check-in",
                          "check_in_items": ["mission_number", "callsign", "aircraft", "position", "altitude", "ordnance", "playtime", "abort_code"],
                          "check_out": "Check out with Warhawk; give BDA."}],
            "tanker_procedures": [{"id": "tk-shell", "track": "shell", "channels": ["tanker-uhf"], "tacan": {"channel": 63, "band": "Y"},
                                   "altitude": {"lower": {"value": 180, "unit": "flight_level", "reference": "FL"},
                                                "upper": {"value": 200, "unit": "flight_level", "reference": "FL"}},
                                   "procedure": "tanker-rendezvous", "ato_missions": ["shell-aar"], "remarks": "Boom only."}],
            **spins_sections(),
            "references": [{"id": "oir-aco", "revision": "2", "title": "OIR ACO"}, {"id": "oir-ato", "revision": "1", "title": "OIR ATO"},
                           {"id": "oir-opord", "revision": "1", "title": "OIR OPORD 26-01"}],
            "remarks": "All times are UTC. Jordanian transition altitude 13000 feet; QNH below it."}


def spins_sections():
    """Air defence, CAS and laser, emergency, recovery, EMCON and EW, restrictions, reports and night sections of the SPINS."""
    cas_window = window(at("1330"), at("1430"))
    dark = window(at("1450"), at("1500"))  # sunset in the objective area is about 1505Z on 2 October
    magnetic = lambda value: {"value": value, "reference": "magnetic"}
    block = lambda lower, upper: {"lower": feet(lower), "upper": feet(upper)}
    strikers = ["strike-cobalt", "sead-cobalt", "escort-anvil", "ai-zinc"]
    return {
        "air_defense": {
            "weapons_control": [{"status": "tight", "measure": "sage-shoradez", "window": deepcopy(PERIOD)}],
            "warnings": [{"level": "yellow", "measure": "oir-aor", "window": deepcopy(PERIOD)}],
            "engagement_authorities": ["darkstar"],
            "identification_matrix": [
                {"id": "idm-friend", "declaration": "friend", "criteria": ["iff_mode_5", "iff_mode_3a_code", "minimum_risk_route"], "minimum_criteria": 2,
                 "authority": "darkstar", "measures": ["oir-aor"], "window": deepcopy(PERIOD)},
                {"id": "idm-bandit", "declaration": "bandit", "criteria": ["electronic_identification", "point_of_origin", "flight_profile"], "minimum_criteria": 2,
                 "authority": "darkstar", "measures": ["oir-aor"], "window": deepcopy(PERIOD)},
                {"id": "idm-hostile", "declaration": "hostile", "criteria": ["controller_declaration"], "minimum_criteria": 1, "authority": "darkstar",
                 "measures": ["oir-aor"], "window": deepcopy(PERIOD), "remarks": "Only Darkstar declares a track hostile (OPORD ROE R-3)."}],
            "commit_criteria": [
                {"id": "cc-falcon", "threats": ["red-air-fighters"], "orbit": "falcon", "commit_range": {"value": 40, "unit": "nm"},
                 "altitude": {"lower": {"value": 150, "unit": "flight_level", "reference": "FL"}, "upper": {"value": 350, "unit": "flight_level", "reference": "FL"}},
                 "declarations": ["bogey", "bandit", "hostile"], "ato_missions": ["cap-falcon", "sweep"], "procedure": "cap-commit"},
                {"id": "cc-cobalt", "threats": ["red-air-fighters"], "measures": ["cobalt-box"], "commit_range": {"value": 20, "unit": "nm"},
                 "declarations": ["bandit", "hostile"], "ato_missions": ["intercept", "escort-anvil"],
                 "remarks": "Escorts stay with the strikers unless Darkstar commits them."}],
            "return_to_force": [
                {"id": "rtf-tinsel", "name": "Tinsel return", "agency": "darkstar", "routes": ["mrr-tinsel"], "checkpoints": ["isp-tinsel"], "squawk": "4521",
                 "altitude": block(12000, 14000), "maximum_speed": {"value": 350, "unit": "kt"}, "channels": ["control-uhf"], "window": deepcopy(PERIOD),
                 "ato_missions": [*strikers, "cas-cobalt"]},
                {"id": "rtf-sage", "name": "Sage safe passage", "agency": "darkstar", "safe_lanes": ["sl-sage"], "squawk": "4532",
                 "altitude": block(7000, 9000), "maximum_speed": {"value": 140, "unit": "kt"}, "channels": ["control-uhf"], "window": deepcopy(PERIOD),
                 "ato_missions": ["assault-nickel", "pedro-csar"], "remarks": "Sage holds fire on tracks in the safe lane that squawk 4532."}],
            "summary": "Weapons tight in the Sage SHORADEZ; Darkstar alone declares hostile."},
        "cas": {
            "stacks": [
                {"id": "stack-mesa", "name": "Mesa CAS stack", "orbit": "mesa", "agency": "warhawk", "window": cas_window,
                 "levels": [{"altitude": block(15000, 16000), "use": "holding", "ato_missions": ["scar-gainful"]},
                            {"altitude": block(14000, 15000), "use": "holding", "ato_missions": ["cas-cobalt"]}]},
                {"id": "stack-silver", "name": "Silver working stack", "point": "ip-silver", "agency": "warhawk", "window": cas_window,
                 "levels": [{"altitude": block(13000, 14000), "use": "working", "ato_missions": ["faca-nail"]},
                            {"altitude": block(11000, 13000), "use": "working", "ato_missions": ["cas-cobalt"]}],
                 "remarks": "Below 11000 feet MSL the CA applies; contact Warhawk before descent."}],
            "laser_codes": [
                {"code": "1688", "use": "marking", "units": ["tacp-axeman"], "agencies": ["axeman"], "window": cas_window},
                {"code": "1511", "use": "designation", "units": ["tacp-axeman"], "agencies": ["axeman"], "window": cas_window},
                {"code": "1522", "use": "designation", "flights": ["hawg"], "window": cas_window},
                {"code": "1611", "use": "designation", "flights": ["rage"], "window": window(at("1320"), at("1350"))},
                {"code": "1622", "use": "designation", "flights": ["dude"], "window": deepcopy(PERIOD)},
                {"code": "1633", "use": "marking", "flights": ["nail"], "window": deepcopy(PERIOD)}],
            "lasing_restrictions": [
                {"id": "lr-nfa", "kind": "no_lasing", "measures": ["quarry-nfa", "range-camp-nfa"], "window": deepcopy(PERIOD)},
                {"id": "lr-cobalt", "kind": "permitted_target_lines", "measures": ["cobalt-box"], "window": window(at("1320"), at("1450")),
                 "target_lines": [{"from": magnetic(300), "to": magnetic(60)}], "minimum_altitude": feet(10000),
                 "remarks": "Target lines point away from TF Bastion south-west of the kill box."}],
            "remarks": "Codes are deconflicted for the whole period; Axeman confirms the code on every 9-line."},
        "emergency": {
            "jettison_areas": [{"id": "jett-tin", "measure": "jettison-tin", "stores": ["hung_ordnance", "unexpended_ordnance", "external_tanks"],
                                "altitude": block(7000, 8000), "heading": magnetic(90), "agency": "banshee", "channel": "banshee-uhf",
                                "window": deepcopy(PERIOD)}],
            "damaged_aircraft_routes": [
                {"id": "dmg-ojms", "condition": "battle_damage", "measures": ["mrr-tinsel"], "airfield": "ojms", "squawk": "7700",
                 "agency": "darkstar", "channel": "control-uhf"},
                {"id": "dmg-prince-hassan", "condition": "fuel_emergency", "routes": ["marshal-exit"], "airfield": "prince-hassan", "squawk": "7700",
                 "agency": "darkstar", "channel": "control-uhf"},
                {"id": "dmg-hung", "condition": "hung_ordnance", "measures": ["mrr-tinsel"], "airfield": "ojms", "agency": "banshee",
                 "channel": "banshee-uhf"}],
            "lost_communication": [
                {"id": "lc-darkstar", "agency": "darkstar", "phases": ["ph-1", "ph-2", "ph-3"],
                 "steps": [{"action": "squawk", "after_minutes": 0, "squawk": "7600"},
                           {"action": "hold", "after_minutes": 0, "measure": "marshal", "altitude": feet(14000)},
                           {"action": "return_to_base", "after_minutes": 5, "route": "marshal-exit", "altitude": feet(12000)},
                           {"action": "land", "airfield": "ojms"}]},
                {"id": "lc-warhawk", "agency": "warhawk", "phases": ["ph-2"], "ato_missions": ["cas-cobalt", "faca-nail"],
                 "steps": [{"action": "squawk", "after_minutes": 0, "squawk": "7600"},
                           {"action": "hold", "after_minutes": 0, "measure": "ip-silver", "altitude": feet(14000)},
                           {"action": "return_to_base", "after_minutes": 10, "measure": "mrr-tinsel", "altitude": feet(13000)},
                           {"action": "land", "airfield": "ojms"}]}],
            "remarks": "Squawk 7700 for any emergency; Darkstar gives the nearest suitable airfield."},
        "recovery_routing": {
            "iff_lines": ["iffoff-zinc", "iffon-nickel"],
            "return_routes": ["mrr-tinsel"],
            "routes": ["marshal-exit"],
            "recovery_airfields": [
                {"airfield": "ojms", "priority": 1, "entry_point": "cedar", "route": "marshal-exit", "procedure": "recovery-ojms",
                 "channels": ["control-uhf", "banshee-uhf"], "ato_missions": [*strikers, "cap-falcon", "sweep", "intercept", "cas-cobalt"]},
                {"airfield": "prince-hassan", "priority": 2, "entry_point": "cedar", "channels": ["control-uhf"], "ato_missions": ["airlift-prince-hassan", "faca-nail"]},
                {"airfield": "farp-sage", "priority": 3, "channels": ["banshee-uhf"], "ato_missions": ["assault-nickel", "pedro-csar"]}],
            "remarks": "Set every IFF mode on at IFFON NICKEL before ISP TINSEL."},
        "electromagnetic": {
            "emission_control": [{"id": "emcon-ingress", "level": "reduced", "window": window(at("1300"), at("1320")), "measures": ["oir-aor"],
                                  "units": ["strike-sqn", "sead-sqn"], "ato_missions": strikers},
                                 {"id": "emcon-push", "level": "unrestricted", "window": window(at("1320"), at("1500")), "ato_missions": strikers}],
            "jamming_authority": "caoc", "jamming": [jamming_window()],
            "remarks": "Air-to-air radars stay in standby until the push at 1320Z."},
        "restrictions": {
            "protected_sites": ["ps-quarry"],
            "other_protected_sites": [{"id": "ps-range-camp", "name": "Displaced-persons camp", "kind": "infrastructure", "restriction": "no_strike", "measure": "range-camp-nfa"}],
            "weather_minimums": [
                {"id": "wx-attack", "taskings": ["preplanned_attack", "on_call_cas", "counterland_control"], "phase": "target_area",
                 "ceiling": {"value": 5000, "unit": "ft"}, "visibility": {"value": 8, "unit": "km"}},
                {"id": "wx-aar", "taskings": ["refueling"], "phase": "air_refueling", "visibility": {"value": 3, "unit": "nm"}},
                {"id": "wx-rotary", "taskings": ["transport", "personnel_recovery"], "phase": "en_route",
                 "ceiling": {"value": 1000, "unit": "ft"}, "visibility": {"value": 3, "unit": "km"}},
                {"id": "wx-ojms", "phase": "landing", "airfield": "ojms", "ceiling": {"value": 3000, "unit": "ft"}, "visibility": {"value": 5, "unit": "km"}}],
            "remarks": "Divert per the abort conditions when Muwaffaq Salti is below its minimum."},
        "reports": [
            {"report": "misrep", "from_units": ["strike-sqn", "cas-sqn", "fighter-sqn"], "to_agency": "caoc", "trigger": "Within 30 minutes of landing",
             "channel": "ops-uhf", "ato_missions": ["strike-cobalt", "cas-cobalt", "cap-falcon"]},
            {"report": "inflightrep", "to_agency": "darkstar", "trigger": "Time-sensitive observation airborne", "channel": "control-uhf",
             "ato_missions": ["recce-gainful", "scar-gainful", "cap-falcon"]},
            {"report": "bda", "to_agency": "warhawk", "trigger": "At check-out after each attack", "channel": "cas-uhf", "ato_missions": ["cas-cobalt", "faca-nail"]},
            {"report": "bda", "from_units": ["strike-sqn"], "to_agency": "caoc", "trigger": "After each attack", "channel": "ops-uhf",
             "ato_missions": ["strike-cobalt", "ai-zinc", "sead-cobalt"]}],
        "night_operations": {
            "nvg": [{"id": "nvg-dusk", "window": dark, "measures": ["oir-aor"], "ato_missions": ["assault-nickel", "pedro-csar", "range-clear"],
                     "minimum_altitude": feet(500, "AGL"), "minimum_illumination": 20, "lighting": "covert"}],
            "lights_out_areas": [{"id": "lo-cobalt", "measures": ["cobalt-box"], "window": dark, "altitude": {"lower": {"surface": True}, "upper": feet(18000)},
                                  "ato_missions": ["strike-cobalt", "sead-cobalt", "escort-anvil"]}],
            "lighting": [{"id": "lt-ground", "phase": "ground", "lights": ["position", "anti_collision"], "setting": "on"},
                         {"id": "lt-aar", "phase": "air_refueling", "lights": ["position", "formation"], "setting": "dim", "measures": ["shell"]},
                         {"id": "lt-target", "phase": "target_area", "lights": ["position", "anti_collision", "formation"], "setting": "off",
                          "measures": ["cobalt-box"], "window": dark},
                         {"id": "lt-recovery", "phase": "recovery", "lights": ["position", "anti_collision", "landing"], "setting": "on"}],
            "remarks": "Sunset in the objective area is about 1505Z; helicopters go to NVG and the kill box goes lights-out from 1450Z."}}


def order_examples(version):
    return {"examples/opord.json": opord(version), "examples/frago.json": frago(version), "examples/spins.json": spins(version)}
