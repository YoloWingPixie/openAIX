"""Authored measure examples for the OIR scenario on the DCS Syria map, and standalone US civil airspace examples.

One example per measure contract and per distinct use. The OIR measures lie between Muwaffaq Salti and the
Euphrates valley near Deir ez-Zor; all their times fall inside the OIR order period, 2026-10-02 13:00Z to 15:00Z.
The US civil airspace examples (Class B, Class D, MOA, ATCAA, TFR and MTA) are separate: they show US airspace
types around a fictional Juniper Field in southern Nevada and are not part of the OIR scenario.
"""
from copy import deepcopy

from openaix.sim.dcs import extension as dcs


BASE = "urn:openaix:schema:"
PERIOD = {"start": "2026-10-02T13:00:00Z", "end": "2026-10-02T15:00:00Z"}


def urn(name, version):
    plain = {"orbit", "airspace", "point"}
    return BASE + (name if name in plain else "measure-" + name) + ":" + version


def at(latitude, longitude):
    return {"latitude": latitude, "longitude": longitude}


def ft(value, reference="MSL"):
    return {"value": value, "unit": "ft", "reference": reference}


def fl(value):
    return {"value": value, "unit": "flight_level", "reference": "FL"}


def nm(value):
    return {"value": value, "unit": "nm"}


def window(start, end):
    return {"start": "2026-10-02T" + start + ":00Z", "end": "2026-10-02T" + end + ":00Z"}


def box(south, west, north, east):
    return {"kind": "polygon", "rings": [[at(south, west), at(south, east), at(north, east), at(north, west), at(south, west)]]}


def circle(latitude, longitude, radius):
    return {"kind": "circle", "center": at(latitude, longitude), "radius": nm(radius)}


def part(identifier, geometry, lower, upper, operation="add", name=None):
    result = {"id": identifier, "operation": operation, "geometry": geometry, "lower_limit": lower, "upper_limit": upper}
    if name:
        result["name"] = name
    return result


SURFACE = {"surface": True}


def measures(version):
    """Every authored example keyed by file name under examples/measures/, plus top-level shared examples."""
    def measure(schema, identifier, name, kind, active, description, **fields):
        return {"$schema": urn(schema, version), "id": identifier, "name": name, "type": kind, "active": active,
                "description": description, **fields}

    examples = {
        # Volume: one contract, distinct uses.
        "measures/roz.json": measure("volume", "anvil-roz", "Anvil fires ROZ", "ROZ", window("13:15", "14:45"),
            "Restricted Operating Zone around the Anvil HIMARS firing point while it fires into the Onyx kill box.",
            purpose="Protect aircraft from the surface fires of the Anvil battery.",
            notes="Hot 1315Z to 1445Z; expect short-notice extension for troops in contact.",
            restrictions=["Aircraft other than the Anvil observation flight remain outside while the zone is active."],
            coordination_instructions=["Request transit from Banshee; expect to hold at Bolt until the battery checks fire."],
            components=[part("anvil-volume", box(34.935, 39.954, 35.005, 40.065), SURFACE, ft(12000))]),
        "measures/hidacz.json": measure("volume", "basin-hidacz", "Basin HIDACZ", "HIDACZ", window("13:00", "15:00"),
            "High-density airspace control zone over the northern objective area, where helicopters, observation drones and fires are concentrated; the Lantern no-fly zone is cut out of it.",
            purpose="Coordinate the concentrated objective-area users under one controlling agency.",
            restrictions=["Enter only with a clearance from the Basin airspace control element."],
            coordination_instructions=["Check in on the Basin control frequency 10 nm before the boundary."],
            components=[part("basin-main", box(35.035, 39.825, 35.335, 40.175), SURFACE, ft(17000), name="Objective area"),
                        part("lantern-cutout", circle(35.195, 40.075, 3), SURFACE, ft(10000), operation="subtract", name="Lantern exclusion")]),
        "measures/nfz.json": measure("volume", "lantern-nfz", "Lantern no-fly zone", "NFZ", {"continuous": True},
            "No-fly zone over the Lantern village inside the objective area.",
            restrictions=["No aircraft operations except those authorised by Banshee as the enforcing authority."],
            components=[part("lantern-volume", circle(35.195, 40.075, 3), SURFACE, ft(10000))]),
        "measures/bz.json": measure("volume", "cobalt-buffer", "Cobalt buffer zone", "BZ", window("13:00", "15:00"),
            "Buffer zone separating the Basin HIDACZ from the Cobalt and Onyx kill boxes to the east.",
            purpose="Keep a lateral buffer between objective-area traffic and kill box attacks.",
            components=[part("cobalt-buffer-volume", box(35.035, 40.177, 35.155, 40.225), SURFACE, ft(17000))]),
        "measures/aara.json": measure("volume", "shell-aara", "Shell refuelling area", "AARA", window("13:00", "15:00"),
            "Air-to-air refuelling area over the Syria-Iraq-Jordan border triangle, around the Shell tanker track.",
            purpose="Reserve a block for tanker and receiver join-ups.",
            restrictions=["Non-refuelling traffic remains clear unless coordinated with Darkstar."],
            components=[part("shell-block", box(33.000, 38.850, 33.120, 39.250), fl(170), fl(210))]),
        "measures/aewa.json": measure("volume", "sentinel-aewa", "Sentinel early warning area", "AEWA", window("13:00", "15:00"),
            "Airborne early warning area over eastern Jordan around the Sentinel surveillance orbit.",
            purpose="Reserve airspace for the airborne early warning aircraft.",
            components=[part("sentinel-block", circle(32.700, 38.400, 25), fl(270), fl(310))]),
        # Route: corridor and minimum-risk route.
        "measures/tc.json": measure("route", "silver-tc", "Silver transit corridor", "TC", window("13:00", "15:00"),
            "Rear-area transit corridor from the Jordanian bases to the Juniper ingress gate, routing aircraft through friendly air defences.",
            purpose="Route inbound and outbound traffic past the Granite missile engagement zone with minimum risk.",
            restrictions=["Air traffic services are not provided inside the corridor."],
            geometry={"kind": "corridor", "points": [at(32.025, 37.003), at(32.807, 37.775), at(33.590, 38.552)], "width": nm(5)},
            altitude={"lower": ft(8000), "upper": ft(10000)}),
        "measures/mrr.json": measure("route", "bastion-mrr", "Bastion minimum-risk route", "MRR", window("13:30", "14:30"),
            "Low-level minimum-risk route from Cedar across the forward line of own troops for helicopter and low-flying traffic.",
            purpose="Cross the FLOT with the least known hazard from friendly fires.",
            geometry={"kind": "corridor", "points": [at(33.590, 39.002), at(34.372, 40.225), at(34.835, 40.627), at(34.935, 40.574)], "width": nm(2)},
            altitude={"lower": ft(300, "AGL"), "upper": ft(1500, "AGL")}),
        # Lines.
        "measures/flot.json": measure("line", "oir-flot", "OIR FLOT", "FLOT", window("13:00", "15:00"),
            "Forward line of own troops of the partner land force at the start of the period.",
            geometry={"kind": "line", "points": [at(34.835, 39.724), at(34.855, 40.025), at(34.815, 40.374), at(34.835, 40.725)]}),
        "measures/fscl.json": measure("fire-support-line", "oir-fscl", "OIR FSCL", "FSCL", window("13:00", "15:00"),
            "Fire support coordination line set by the partner land force north of the FLOT; the Cobalt and Onyx kill boxes lie beyond it.",
            coordination_instructions=["Fires short of the line that may affect the land force are coordinated with its fire support element."],
            geometry={"kind": "line", "points": [at(35.025, 39.725), at(35.030, 40.125), at(35.025, 40.725)]}),
        # Ground manoeuvre graphics of Task Force Bastion, the ground element that JTAC Axeman supports. It attacks north
        # from PL BRASS (the LD) to PL ZINC (the LOA), short of the FSCL; Task Force Basin is west of the boundary and
        # Task Force Pewter converges from the east.
        "measures/ld.json": measure("line", "pl-brass", "PL BRASS", "LD", window("13:00", "15:00"),
            "Phase line BRASS, designated as the line of departure of Task Force Bastion; it follows the FLOT at the start of the period.",
            coordination_instructions=["Task Force Bastion crosses PL BRASS at 1330Z after the Cobalt kill box opens."],
            geometry={"kind": "line", "points": [at(34.845, 40.127), at(34.850, 40.305), at(34.845, 40.476)]}),
        "measures/pl.json": measure("line", "pl-nickel", "PL NICKEL", "PL", window("13:00", "15:00"),
            "Phase line NICKEL along the desert road to Deir ez-Zor; Task Force Bastion reports crossing it to Warhawk and Axeman.",
            coordination_instructions=["Report PL NICKEL to Warhawk; CAS friendlies lines use the last reported phase line."],
            geometry={"kind": "line", "points": [at(34.925, 40.125), at(34.920, 40.307), at(34.925, 40.474)]}),
        "measures/loa.json": measure("line", "pl-zinc", "PL ZINC", "LOA", window("13:00", "15:00"),
            "Phase line ZINC, the limit of advance of Task Force Bastion, short of the FSCL and the Cobalt and Onyx kill boxes.",
            coordination_instructions=["No Task Force Bastion element advances beyond PL ZINC; security forces may push to it."],
            geometry={"kind": "line", "points": [at(35.015, 40.125), at(35.015, 40.476)]}),
        "measures/boundary.json": measure("line", "bastion-basin-boundary", "Task Force Bastion and Task Force Basin boundary", "BOUNDARY",
            window("13:00", "15:00"),
            "Lateral boundary between Task Force Bastion to the east and Task Force Basin to the west, from PL BRASS to PL ZINC.",
            coordination_instructions=["Fires across the boundary are coordinated with the adjacent task force."],
            geometry={"kind": "line", "points": [at(34.835, 40.126), at(35.025, 40.125)]}),
        "measures/rfl.json": measure("fire-support-line", "pewter-rfl", "Bastion and Pewter RFL", "RFL", window("13:30", "15:00"),
            "Restrictive fire line between Task Force Bastion attacking north and Task Force Pewter converging from the east; set by the partner land force, the common commander.",
            coordination_instructions=["No fires or their effects across the line without coordination with the affected task force."],
            geometry={"kind": "line", "points": [at(34.855, 40.475), at(34.935, 40.485), at(35.015, 40.476)]}),
        # Surface areas.
        "measures/nfa.json": measure("area", "quarry-nfa", "Quarry Springs NFA", "NFA", window("13:00", "15:00"),
            "No-fire area that protects a civilian water pumping station between the FLOT and the FSCL.",
            restrictions=["No fires or effects into the area unless the establishing headquarters approves each mission."],
            geometry={"kind": "circle", "center": at(34.935, 40.324), "radius": {"value": 1000, "unit": "m"}}),
        "measures/rfa.json": measure("area", "juniper-wash-rfa", "Juniper Wash RFA", "RFA", window("13:00", "15:00"),
            "Restrictive fire area over a friendly logistics site south of the FLOT.",
            restrictions=["No improved conventional munitions.", "Fires that exceed these restrictions require coordination with the land force fire support element."],
            geometry=box(34.715, 40.225, 34.775, 40.325)),
        "measures/aor.json": measure("aor", "oir-aor", "OIR area of responsibility", "AOR", {"continuous": True},
            "Area of responsibility of the CJTF-OIR air component in this order, from eastern Jordan to the Euphrates valley; the airspace control area follows it.",
            geometry=box(32.54, 36.90, 35.80, 40.90)),
        # Dedicated contracts.
        "measures/kb.json": measure("kb", "onyx-box", "Onyx kill box", "KB", window("13:30", "14:30"),
            "Purple kill box east of Cobalt for combined air and surface fires against the Cobalt compound and its supply routes.",
            killbox_kind="purple", grid_label="Onyx 2, keypad 5",
            restrictions=["Aircraft remain at or above the 8000 ft MSL floor while the box is open."],
            components=[part("onyx-volume", box(35.035, 40.374, 35.155, 40.525), ft(8000), ft(18000))]),
        "measures/mez.json": measure("mez", "granite-mez", "Granite missile engagement zone", "MEZ", window("13:00", "15:00"),
            "Low- to medium-altitude missile engagement zone around the coalition Granite surface-to-air missile battery.",
            mez_kind="low",
            coordination_instructions=["Coordinate with the air defence controller before entering; use the Silver transit corridor otherwise."],
            components=[part("granite-volume", circle(34.735, 39.924, 12), SURFACE, ft(15000))]),
        "measures/shoradez.json": measure("mez", "sage-shoradez", "Sage SHORADEZ", "MEZ", window("13:00", "15:00"),
            "Short-range air defence engagement zone over the Sage FARP, where an Avenger platoon has engagement responsibility.",
            mez_kind="short_range",
            coordination_instructions=["Helicopters inbound to Sage enter on the Sage FARP approach after the air defence controller confirms weapons hold."],
            components=[part("sage-shorad-volume", circle(34.735, 40.225, 2.5), SURFACE, ft(8000))]),
        "measures/ca.json": measure("cl", "bastion-ca", "OIR coordinating altitude", "CA", window("13:00", "15:00"),
            "Coordinating altitude over Task Force Bastion, from the boundary to the RFL and from PL BRASS to the FSCL; Warhawk controls the assigned airspace below it, and Darkstar the airspace above it.",
            coordination_instructions=["Coordinate with Warhawk and Darkstar before flying or firing through 11000 feet MSL inside the Task Force Bastion area.",
                                       "No coordinating altitude applies beyond the FSCL or inside an open kill box."],
            geometry={"kind": "vertical", "level": ft(11000)}),
        "measures/cl.json": measure("cl", "oir-cl", "OIR coordination level", "CL", window("13:00", "15:00"),
            "Coordination level separating land-component aviation below from fixed-wing traffic above.",
            geometry={"kind": "vertical", "level": ft(3500, "AGL")}),
        "measures/tl.json": measure("tl", "granite-tl", "Granite traverse level", "TL", window("13:00", "15:00"),
            "Traverse level for crossing the Granite low-level air defence area.",
            geometry={"kind": "vertical", "height": ft(2000, "AGL"), "altitude": ft(7500)}),
        "measures/aca.json": measure("aca", "anvil-aca", "Anvil ACA", "ACA", window("13:30", "14:30"),
            "Formal airspace coordination area along the Anvil battery's line of fire into Onyx; aircraft inside it are reasonably safe from the surface fires.",
            aca_kind="formal",
            components=[part("anvil-baseline", {"kind": "corridor", "points": [at(34.975, 40.024), at(35.095, 40.446)], "width": nm(2)}, ft(9000), ft(12000))]),
        "measures/isr.json": measure("isr", "kestrel-isr", "Kestrel identification safety range", "ISR", window("13:00", "15:00"),
            "Identification safety range around the Kestrel surface action group in the eastern Mediterranean, south-east of Cyprus.",
            reference_force="Kestrel surface action group", reference_position=at(34.35, 34.40), range=nm(15),
            geometry=circle(34.35, 34.40, 15)),
        "measures/misarc.json": measure("misarc", "kestrel-misarc", "Kestrel missile arc", "MISARC", window("13:40", "14:00"),
            "Missile arc from the Kestrel destroyer toward an inbound target track from the north-east.",
            firing_unit="Kestrel (Arleigh Burke-class destroyer)", center=at(34.35, 34.40), axis={"value": 45, "reference": "true"},
            width_deg=10, range=nm(30), altitude={"lower": SURFACE, "upper": fl(450)}),
        # Points: one contract, catalogue codes become roles.
        "measures/ip.json": measure("point", "bolt-ip", "Bolt", "POINT", window("13:00", "15:00"),
            "Initial point for attack runs into the Cobalt and Onyx kill boxes.",
            roles=["initial"], position=at(34.935, 40.175)),
        "measures/trp.json": measure("point", "trp-01", "TRP 01", "POINT", window("13:00", "15:00"),
            "Target reference point at the road junction south-east of the Cobalt vehicle park; Axeman gives Cobalt targets as offsets from it.",
            roles=["target_reference"], position=at(35.091, 40.318),
            position_description="Road junction south-east of the revetted vehicle park in the Cobalt compound."),
        "measures/cp.json": measure("point", "dagger-cp", "Dagger", "POINT", window("13:00", "15:00"),
            "Contact point where strike flight leads check in with Banshee.",
            roles=["control"], position=at(34.785, 40.273)),
        "measures/eg.json": measure("point", "silver-gate", "Silver gate", "POINT", window("13:00", "15:00"),
            "Entry and exit gate where recovering and departing aircraft begin their transit in the Silver transit corridor.",
            roles=["gate", "ingress", "egress"], position=at(32.807, 37.775)),
        "measures/bullseye.json": measure("point", "bastion-bullseye", "Bastion", "POINT", {"continuous": True},
            "OIR bullseye for bearing and range calls; bearings from it are magnetic.",
            roles=["bullseye"], position=at(34.735, 40.326)),
        # Orbit and airspace.
        "orbit.json": measure("orbit", "tiger-orbit", "Tiger", "ORBIT", window("13:00", "15:00"),
            "Racetrack north-west of the objective area, used first for combat air patrol and then for airborne early warning.",
            geometry={"kind": "racetrack", "point": at(35.235, 39.625), "radial": {"value": 90, "reference": "true"},
                      "turns": "right", "leg_length": nm(20)},
            altitude={"lower": fl(240), "upper": fl(260)}),
        # XFORM-OFF
        "airspace-class-b.json": measure("airspace", "juniper-field-class-b", "Juniper Field Class B", "AIRSPACE", {"continuous": True},
            "US Class B airspace with a surface area and two shelves around Juniper Field; each shelf has its own floor and ceiling.",
            airspace_type="ClassB", airspace_class_code="B",
            components=[part("surface", circle(36.35, -115.25, 5), SURFACE, ft(10000)),
                        part("inner-shelf", circle(36.35, -115.25, 10), ft(2500), ft(10000)),
                        part("outer-shelf", circle(36.35, -115.25, 20), ft(5000), ft(9000))]),
        "airspace-class-d.json": measure("airspace", "cedar-strip-class-d", "Cedar Strip Class D", "AIRSPACE", {"continuous": True},
            "US Class D airspace around the Cedar Strip airfield, from the surface to 2500 feet above it.",
            airspace_type="ClassD", airspace_class_code="D",
            components=[part("cedar-strip", circle(36.70, -115.30, 4), SURFACE, ft(6500))]),
        "airspace-moa.json": measure("airspace", "desert-moa", "Desert MOA", "AIRSPACE", window("13:00", "15:00"),
            "US military operations area west of Juniper Field. It ends below flight level 180, and the Desert ATCAA lies above it.",
            airspace_type="MOA", designator="DESERT MOA", restrictions=["Nonparticipating IFR traffic is cleared through only when ATC separates it."],
            components=[part("desert-moa-volume", box(36.40, -116.45, 36.75, -116.05), ft(500, "AGL"), fl(180))]),
        "airspace-atcaa.json": measure("airspace", "desert-atcaa", "Desert ATCAA", "AIRSPACE", window("13:00", "15:00"),
            "ATC-assigned airspace over the Desert MOA, from flight level 180 to flight level 260; it extends the MOA activity into Class A airspace.",
            airspace_type="ATCAA", designator="DESERT ATCAA",
            coordination_instructions=["The using agency requests the ATCAA from the air route traffic control centre; it is not charted."],
            components=[part("desert-atcaa-volume", box(36.40, -116.45, 36.75, -116.05), fl(180), fl(260))]),
        "airspace-tfr.json": measure("airspace", "mesquite-tfr", "Mesquite fire TFR", "AIRSPACE", window("13:00", "15:00"),
            "Temporary flight restriction under 14 CFR 91.137 around a wildfire east of Juniper Field.",
            airspace_type="TFR", designator="FDC 6/0213",
            restrictions=["Only aircraft that support the fire suppression enter the TFR."],
            components=[part("mesquite-tfr-volume", circle(36.95, -114.98, 5), SURFACE, ft(8000))]),
        "airspace-mta.json": measure("airspace", "sierra-mta", "Sierra Training Area", "AIRSPACE", window("13:00", "15:00"),
            "Military training area north of the Desert MOA for air combat training.",
            airspace_type="MTA", restrictions=["Coordinate entry with the scheduling agency."],
            components=[part("sierra-block", box(37.85, -116.40, 38.10, -115.90), ft(500, "AGL"), ft(12000))]),
        # XFORM-ON
    }
    for document in examples.values():
        if "start" in document["active"]:
            for item in document.get("components", []):
                item["active"] = deepcopy(document["active"])  # each volume is active for the whole window
    examples["sim-bound-roz.json"] = bound_roz(examples["measures/roz.json"])
    examples["orbit-assignments.json"] = orbit_order(version, examples["orbit.json"])
    examples["aco-all-measures.json"] = measures_order(version, examples)
    return examples


def bound_roz(roz):
    bound = deepcopy(roz)
    bound.update({"id": "anvil-roz-bound", "name": "Anvil fires ROZ (mission editor)"})
    bound["components"][0]["geometry"] = circle(34.970, 40.009, 3)
    bound["extensions"] = dcs([{"kind": "drawing", "name": "Anvil ROZ", "layer": "Blue", "primitive_type": "Polygon", "polygon_mode": "circle"},
                               {"kind": "trigger_zone", "name": "Anvil ROZ", "object_id": 21, "zone_type": "circle"}])
    return bound


def order(version, identifier, title, measures, assignments):
    return {"$schema": BASE + "aco:" + version, "kind": "aco", "schema_version": version,
            "meta": {"id": identifier, "title": title, "revision": "1"}, "period": deepcopy(PERIOD),
            "resources": {"control_measures": measures}, "assignments": assignments}


def orbit_order(version, orbit):
    return order(version, "tiger-assignments", "Tiger orbit: patrol then surveillance", {orbit["id"]: deepcopy(orbit)}, [
        {"measure": orbit["id"], "state": "active", "role": "cap", "effective": window("13:00", "14:00")},
        {"measure": orbit["id"], "state": "active", "role": "aew", "purpose": "Surveillance of the northern objective area",
         "effective": window("14:00", "15:00")},
    ])


def measures_order(version, examples):
    entries = {}
    assignments = []
    for path, document in sorted(examples.items()):
        if not isinstance(document, dict) or document.get("kind") == "aco" or "type" not in document or path == "sim-bound-roz.json":
            continue
        entries[document["id"]] = deepcopy(document)
        active = document["active"]
        effective = deepcopy(active) if "start" in active else deepcopy(PERIOD)
        assignment = {"measure": document["id"], "state": "active", "effective": effective}
        if document["type"] == "ORBIT":
            assignment["role"] = "cap"
        assignments.append(assignment)
    return order(version, "measure-examples", "All measure contracts: the OIR measures and the US civil airspace types", entries, assignments)
