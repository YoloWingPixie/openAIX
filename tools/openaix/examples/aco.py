from copy import deepcopy

from openaix.sim.dcs import extension as dcs


MISSION_ID = "oir-syria"
START = "2026-10-02T13:00:00Z"
END = "2026-10-02T15:00:00Z"


def window(start=START, end=END):
    return {"start": start, "end": end}


def position(latitude, longitude):
    return {"latitude": latitude, "longitude": longitude}


def altitude(value, reference="MSL"):
    return {"value": value, "unit": "ft", "reference": reference}


def altitude_block(lower, upper):
    return {"lower": altitude(lower), "upper": altitude(upper)}


def document_ref(identifier, title, section):
    return {"id": identifier, "revision": "1", "title": title, "section": section, "path": identifier + ".json"}


def measure(version, identifier, name, kind, description):
    schema_name = kind.lower() if kind in {"POINT", "ORBIT"} else "measure-" + {"SC": "route", "ROZ": "volume"}.get(kind, kind.lower())
    return {"$schema": f"urn:openaix:schema:{schema_name}:{version}",
            "id": identifier, "name": name, "type": kind, "active": window(),
            "description": description}


def orbit(version, identifier, name, point, lower, upper, radial, length, reference="MSL"):
    result = measure(version, identifier, name, "ORBIT", "Reserved flight pattern; its service is assigned by this order.")
    result.update({"geometry": {"kind": "racetrack", "point": point,
        "radial": {"value": radial, "reference": "true"}, "turns": "right",
        "leg_length": {"value": length, "unit": "nm"}, "turn_radius": {"value": 2, "unit": "nm"}},
        "altitude": ({"lower": {"value": lower, "unit": "flight_level", "reference": "FL"},
                      "upper": {"value": upper, "unit": "flight_level", "reference": "FL"}} if reference == "FL" else altitude_block(lower, upper)),
        "channels": ["control-uhf"], "controlling_agency": "darkstar",
        "purpose": "Reserve a separated operating block for the assigned airborne service.",
        "restrictions": ["Remain within the published block until Darkstar assigns another altitude."],
        "coordination_instructions": ["Report entry and departure to Darkstar on 251.000 MHz AM."]})
    return result


def point(version, identifier, name, coordinates, roles, route, contact, handover):
    result = measure(version, identifier, name, "POINT", "Named coordination point on the OIR transit route.")
    result.update({"roles": roles, "position": coordinates,
        "reference_agency": "darkstar", "contact_agency": contact,
        "handover_agency": handover, "channels": ["control-uhf", "banshee-uhf"], "route": route,
        "instructions": ["Report this point by name; bearings elsewhere in the order are true."],
        "restrictions": ["A point report does not authorize entry into the restricted operating zone."],
        "coordination_instructions": ["Retain the current controller until the handover is acknowledged."]})
    return result


def component(identifier, name, geometry, floor, ceiling, binding):
    return {"id": identifier, "name": name, "operation": "add", "geometry": geometry,
            "lower_limit": floor, "upper_limit": ceiling, "active": window(), "extensions": dcs([binding])}


def route_point(identifier, name, coordinates, action, height, instruction):
    return {"id": identifier, "name": name, "position": coordinates, "action": action,
            "altitude": altitude(height), "speed": {"value": 250, "unit": "knots_ias"},
            "timing": {"kind": "window", "window": window()}, "instructions": [instruction]}


def frequency(megahertz):
    return {"value": megahertz, "unit": "MHz", "modulation": "AM", "band": "uhf" if megahertz >= 225 else "vhf"}


def agencies():
    """OIR command-and-control agencies shared by the ACO and the resource catalogue."""
    return {
        "caoc": {"id": "caoc", "kind": "c2-agency", "callsign": "Kingpin", "role": "AOC", "channels": ["ops-uhf"],
            "position": position(31.838, 36.803)},
        "darkstar": {"id": "darkstar", "kind": "c2-agency", "callsign": "Darkstar", "role": "AWACS", "channels": ["control-uhf"],
            "extensions": dcs([{"kind": "unit", "name": "OIR Darkstar E-3A", "mission_id": MISSION_ID, "object_id": 11, "unit_type": "E-3A"}])},
        "salti-tower": {"id": "salti-tower", "kind": "c2-agency", "callsign": "Salti Tower", "role": "ATC", "channels": ["salti-uhf"],
            "position": position(31.825431, 36.781257)},
        "banshee": {"id": "banshee", "kind": "c2-agency", "callsign": "Banshee", "role": "CRC", "channels": ["banshee-uhf"],
            "position": position(32.546, 38.214)},
    }


def channels():
    return {
        "ops-uhf": {"name": "Kingpin", "frequency": frequency(255.4), "usage": "Mission changes, aborts and battle-damage reports", "notes": "Monitored 0300Z to 2100Z; outside those hours relay through Darkstar."},
        "control-uhf": {"name": "Darkstar control", "frequency": frequency(251.0), "usage": "Orbit, corridor and holding coordination", "notes": "Primary air control frequency; Link 16 carries the same air picture."},
        "banshee-uhf": {"name": "Banshee", "frequency": frequency(305.0), "usage": "Kill box status, rescue reservation and procedural control east of H4", "notes": "Banshee gives kill box open and closed calls; read back the status."},
        "salti-uhf": {"name": "Salti Tower", "frequency": frequency(253.15), "usage": "Muwaffaq Salti tower, ground and approach (combined)", "notes": "VHF 120.5 is the same position."},
    }


def assignment(measure_id, agency, point_id, purpose, instruction, restriction, **fields):
    return {"measure": measure_id, "state": "active", "effective": window(),
            "controlling_agency": agency, "control_points": [{"kind": "control_measure", "id": point_id}],
            "purpose": purpose, "transit_instructions": [instruction], "restrictions": [restriction],
            **fields}


def build_aco_example(version):
    juniper = position(33.590, 38.552)
    marshal = position(34.059, 39.477)
    cedar = position(33.590, 39.002)
    points = {
        "juniper": point(version, "juniper", "Juniper", juniper, ["control", "ingress", "gate"], "marshal-entry", "banshee", "darkstar"),
        "marshal": point(version, "marshal", "Marshal", marshal, ["control", "marshalling"], "marshal-entry", "darkstar", "darkstar"),
        "cedar": point(version, "cedar", "Cedar", cedar, ["control", "egress", "gate"], "marshal-exit", "darkstar", "banshee"),
    }
    for identifier, description in {
        "juniper": "Southwestern ingress gate; beginning of the Juniper-to-Marshal transit corridor.",
        "marshal": "Northern end of the inbound corridor and the reference point for Mesa holding.",
        "cedar": "Southeastern egress gate reached after release from Mesa holding.",
    }.items():
        points[identifier]["position_description"] = description
    points["juniper"].update({
        "description": "Ingress gate west of At Tanf where traffic from Muwaffaq Salti enters the operating area under Darkstar control.",
        "notes": "Expect a Darkstar picture call at Juniper; squawk the ATO Mode 3 code before the gate.",
        "instructions": ["Report Juniper with altitude and playtime; Darkstar assigns the corridor slot."],
        "restrictions": ["Do not pass Juniper northbound without a Darkstar check-in."],
        "coordination_instructions": ["Banshee hands inbound flights to Darkstar at Juniper."]})
    points["marshal"].update({
        "description": "Holding fix at the north end of the transit corridor and the anchor of Mesa holding.",
        "notes": "Marshal is the hand-off point from Banshee procedural control to Darkstar.",
        "instructions": ["Report Marshal level; expect a Mesa holding level of 14000 or 16000 feet MSL."],
        "restrictions": ["A Marshal report does not clear a flight into the Cobalt kill box."],
        "coordination_instructions": ["Darkstar keeps control from Marshal to the push from holding."]})
    points["cedar"].update({
        "description": "Egress gate where flights leave the operating area for recovery to Muwaffaq Salti or Prince Hassan.",
        "notes": "Report Cedar with fuel state; Banshee gives the recovery altimeter.",
        "instructions": ["Report Cedar with fuel state; give BDA to Warhawk before check-out."],
        "restrictions": ["Do not route through the rescue reservation from Cedar while it is active."],
        "coordination_instructions": ["Darkstar hands outbound flights to Banshee at Cedar."]})
    orbits = {
        "falcon": orbit(version, "falcon", "Falcon patrol", position(34.885, 40.275), 220, 260, 270, 20, reference="FL"),
        "sentinel": orbit(version, "sentinel", "Sentinel surveillance", position(32.700, 38.400), 280, 300, 180, 20, reference="FL"),
        "shell": orbit(version, "shell", "Shell refuelling", position(33.060, 39.050), 180, 200, 270, 15, reference="FL"),
        "mesa": orbit(version, "mesa", "Mesa holding", marshal, 14000, 16000, 180, 10),
    }
    orbit_texts = {
        "falcon": ("Combat air patrol racetrack north of the support orbits, facing the northern threat axis.",
                   "Falcon protects the strike package and the high-value orbits from the north.",
                   "Remain between FL220 and FL260; do not cross south of Shell without Darkstar approval.",
                   "Report Falcon on station and off station to Darkstar on 251.000 MHz AM."),
        "sentinel": ("Airborne early warning orbit over eastern Jordan for Darkstar.",
                     "Sentinel gives Darkstar radar cover from H4 to the Euphrates valley.",
                     "Remain between FL280 and FL300; fighters stay clear of Sentinel by 5 nm.",
                     "Darkstar reports any move of Sentinel to Kingpin on 255.400 MHz AM."),
        "shell": ("Air-to-air refuelling anchor east of the transit corridor, south of the Cobalt kill box.",
                  "Shell gives fuel to the fighters and the strike package before and after the push.",
                  "Receivers join 1000 feet below the tanker and stay between FL180 and FL200.",
                  "Contact Shell on 276.100 MHz AM 20 nm from the anchor; Darkstar keeps radar control."),
        "mesa": ("Holding racetrack at Marshal for flights that wait for the kill box or the tanker.",
                 "Mesa separates holding flights by level above the transit corridor.",
                 "One flight per level at 14000 or 16000 feet MSL, as Darkstar assigns.",
                 "Leave Mesa only on Darkstar release, via Cedar for recovery or Marshal for the push."),
    }
    for identifier, (description, purpose, restriction, coordination) in orbit_texts.items():
        orbits[identifier].update({"description": description, "purpose": purpose, "restrictions": [restriction],
                                   "coordination_instructions": [coordination],
                                   })
    orbits["falcon"]["extensions"] = dcs([{"kind": "drawing", "name": "OIR Falcon Track", "mission_id": MISSION_ID,
        "object_id": 43, "layer": "Blue", "primitive_type": "Line", "line_mode": "segments", "closed": True,
        "style": {"color": "0x66CCFFFF", "thickness": 2, "visible": True}}])
    corridor = measure(version, "south-transit", "South transit corridor", "SC", "Special Corridor (SC) for the inbound route from Juniper to Marshal, below Mesa holding.")
    corridor.update({"geometry": {"kind": "corridor", "points": [juniper, marshal],
        "width": {"value": 3, "unit": "nm"}, "one_way": True}, "altitude": altitude_block(10000, 12000),
        "channels": ["control-uhf"], "controlling_agency": "darkstar",
        "purpose": "Keep inbound traffic below the holding stack.", "restrictions": ["Inbound only; outbound traffic uses Marshal to Cedar."],
        "coordination_instructions": ["Request climb at Marshal; do not climb into the stack without clearance."],
        "notes": "Maximum 300 knots indicated; outside the period the published Jordanian routes apply."})
    roz = measure(version, "rescue-reservation", "Rescue reservation", "ROZ", "Restricted Operating Zone (ROZ) that protects the search for the isolated aircrew of Hawg 2, east of the transit route.")
    roz.update({"controlling_agency": "banshee", "channels": ["banshee-uhf"], "purpose": "Reserve the search area for the rescue package.",
        "restrictions": ["Other aircraft remain outside until Banshee releases the reservation."],
        "coordination_instructions": ["Contact Banshee on 305.000 MHz AM before approaching the boundary."],
        "notes": "Survivor last reported on the eastern edge; Pedro has on-scene command.",
        "components": [component("search-volume", "Search volume", {"kind": "circle", "center": position(34.529, 40.551), "radius": {"value": 3, "unit": "nm"}},
            {"surface": True}, altitude(10000), {"kind": "trigger_zone", "name": "OIR Rescue Search", "mission_id": MISSION_ID, "object_id": 41, "zone_type": "circle"})]})
    box = measure(version, "cobalt-box", "Cobalt kill box", "KB", "Kill Box (KB) over the Cobalt compound west of the Euphrates, north of the transit and rescue areas.")
    box.update({"killbox_kind": "blue", "grid_label": "Cobalt 1", "controlling_agency": "banshee", "channels": ["banshee-uhf"],
        "purpose": "Air-to-surface attacks on the Cobalt compound and vehicle park.",
        "coordination_instructions": ["Enter only from Marshal after Banshee reports the box open."],
        "establishing_authority": "caoc", "restrictions": ["Firing status follows the assignment intervals below; no attacks on the river crossings."],
        "notes": "Banshee opens the box only after Sweeper reports the area clear of civilian traffic.",
        "components": [component("cobalt-volume", "Cobalt volume", {"kind": "polygon", "rings": [[
            position(35.035, 40.225), position(35.035, 40.374), position(35.155, 40.375), position(35.155, 40.225), position(35.035, 40.225)]]},
            {"surface": True}, altitude(13000), {"kind": "drawing", "name": "OIR Cobalt Boundary", "mission_id": MISSION_ID,
                "object_id": 42, "layer": "Blue", "primitive_type": "Polygon", "polygon_mode": "free",
                "style": {"color": "0x3366FFFF", "fill_color": "0x3366FF20", "thickness": 2, "visible": True}})]})
    resources = {
        "agencies": agencies(),
        "channels": channels(),
        "routes": {
            "marshal-entry": {"name": "Juniper to Marshal", "points": [
                route_point("entry-juniper", "Juniper", juniper, "ingress", 10000, "Check in with Darkstar before entering the corridor."),
                route_point("entry-marshal", "Marshal", marshal, "hold", 12000, "Request a climb to the assigned Mesa holding level.")],
                "contingencies": ["If no holding level is available, remain below 12000 feet MSL and follow Darkstar instructions."]},
            "marshal-exit": {"name": "Marshal to Cedar", "points": [
                route_point("exit-marshal", "Marshal", marshal, "egress", 12000, "Descend only after Darkstar releases the holding level."),
                route_point("exit-cedar", "Cedar", cedar, "egress", 10000, "Contact Banshee after handover.")],
                "contingencies": ["For lost communications, continue to Cedar at the last assigned altitude; do not enter an active reservation."]},
        },
        "control_measures": {**points, **orbits, "south-transit": corridor, "rescue-reservation": roz, "cobalt-box": box},
        "areas": {}, "places": {}, "procedures": {}, "reports": {}, "scls": {}, "stores": {}, "targets": {}, "threats": {},
    }
    assignments = [
        assignment("falcon", "darkstar", "marshal", "Combat Air Patrol (CAP) north of the support orbits.", "Enter Falcon at flight level 220 or the flight level assigned by Darkstar.",
            "Do not pursue south of the Cobalt kill box while it is open.", role="cap", usage="cap"),
        assignment("sentinel", "darkstar", "juniper", "Airborne Early Warning (AEW) and control for OIR.", "Remain in Sentinel between flight levels 280 and 300.",
            "Do not leave Sentinel without a relief or Kingpin approval.", role="aew", usage="aew"),
        assignment("shell", "darkstar", "marshal", "Air-to-air refuelling for the counterair and strike flights.", "Request tanker clearance before joining Shell between flight levels 180 and 200; hold the last assigned altitude or flight level until cleared.",
            "Boom receivers only; no probe-and-drogue refuelling on Shell.", role="refueling", usage="aar"),
        assignment("mesa", "darkstar", "marshal", "Holding before kill box or tanker entry.", "Join at Marshal at the assigned level; leave via Cedar after release.",
            "No climb or descent in the stack without a Darkstar clearance.", role="holding", usage="holding",
            stack_instructions=["Assign 14000 or 16000 feet MSL; one flight per level.", "Maintain the assigned level until Darkstar clears a climb or descent."], entry_route="marshal-entry", exit_route="marshal-exit"),
        assignment("south-transit", "darkstar", "juniper", "Activate the inbound transit corridor.", "Fly Juniper to Marshal between 10000 and 12000 feet MSL.",
            "Inbound only; maximum 300 knots indicated in the corridor.", usage="transit"),
        assignment("rescue-reservation", "banshee", "cedar", "Protect the rescue search from unrelated traffic.", "Rescue aircraft enter only after Banshee confirms the reservation is active.",
            "Aircraft not in the rescue package stay outside the reservation.", effective=window(START, "2026-10-02T14:20:00Z")),
        assignment("rescue-reservation", "banshee", "cedar", "Release the rescue reservation after the recovery.", "Normal coordination resumes; this deactivation is not a landing clearance.",
            "Rescue helicopters leave the area by Cedar before 1430Z.", state="deactivated", effective=window("2026-10-02T14:20:00Z", END)),
        assignment("cobalt-box", "banshee", "marshal", "Keep the kill box closed until the area is clear.", "Remain outside the box until the firing window opens.",
            "No aircraft below 13000 feet MSL in the box while Sweeper clears the area.", usage="fires", killbox_status="closed", effective=window(START, "2026-10-02T13:20:00Z")),
        assignment("cobalt-box", "banshee", "marshal", "Permit the scheduled firing phase.", "Banshee confirms clearance and target identification before each attack.",
            "Attack headings stay between 300 and 060 degrees magnetic, away from TF Bastion.", usage="fires", killbox_status="open", effective=window("2026-10-02T13:20:00Z", "2026-10-02T13:50:00Z")),
        assignment("cobalt-box", "banshee", "marshal", "Close the box after the firing phase.", "Cease attacks; depart under Banshee instructions.",
            "No re-attack after the box closes; report BDA on egress.", usage="fires", killbox_status="closed", effective=window("2026-10-02T13:50:00Z", END)),
    ]
    reference = document_ref("oir-spins", "OIR Special Instructions (SPINS)", "Airspace coordination")
    return {"$schema": f"urn:openaix:schema:aco:{version}", "kind": "aco", "schema_version": version,
        "meta": {"id": "oir-aco", "revision": "2", "title": "OIR Airspace Control Order", "author": "CAOC airspace cell",
            "classification": "UNCLASSIFIED", "coalition": "blue", "distribution": ["Darkstar", "Banshee", "Salti Tower", "All OIR flights"],
            "issued_at": "2026-10-02T12:30:00Z", "issuing_unit": "CJTF-OIR CAOC", "operation": "INHERENT RESOLVE",
            "references": [deepcopy(reference)], "supersedes": {**document_ref("oir-aco", "OIR preliminary ACO", "Entire order"), "revision": "1"}},
        "period": window(), "resources": resources, "assignments": assignments, "references": [reference],
        "instructions": ["All times are UTC. Altimeter: QNH below the Jordanian transition altitude of 13000 feet, standard pressure above.",
            "Use the explicit vertical reference: flight levels use standard pressure; MSL and AGL values are feet. No pressure-to-height conversion is implied. Orbit radials are true bearings.",
            "This order allocates airspace. Flight tasking and permissions to engage remain separate."],
        "extensions": {"org.cjtf-oir.ato": {"mission_id": MISSION_ID, "ato_day": "214"}}}


def build_minimal_aco_example(version):
    document = build_aco_example(version)
    document["assignments"] = [{"measure": "south-transit", "state": "active", "effective": window()}]
    corridor = document["resources"]["control_measures"]["south-transit"]
    corridor = {key: corridor[key] for key in ("id", "name", "type", "active", "geometry", "altitude")}
    return {"$schema": document["$schema"], "kind": "aco", "period": window(),
            "resources": {"control_measures": {"south-transit": corridor}}, "assignments": document["assignments"]}
