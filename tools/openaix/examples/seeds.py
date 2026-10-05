"""OIR values for the minimal and maximal examples (examples/pairs.py) that no curated OIR example gives.

Navigation records that the curated examples give only for KDEN: a runway, a final approach path, a hold, a minimum
safe altitude, a Grid MORA row, an airway and an airspace around Muwaffaq Salti (OJMS). Field values for the shapes and
schedules that no curated OIR record uses. The runway and the VORTAC data come
from examples/airfields.py; the procedure values (hold, MSA, MORA, route) are invented planning values that
agree with the I31 approach and the terrain of eastern Jordan.
"""
from copy import deepcopy

from openaix.examples.aco import MISSION_ID, position
from openaix.examples.airfields import DCS_SOURCE, DECLINATION, NAVAIDS, feet, length, offset, ojms, ojms_navigation
from openaix.sim.dcs import extension as dcs

RESOURCES_REF = {"id": "oir-resources", "revision": "1"}
GHI, ABC = NAVAIDS["ojms"], NAVAIDS["prince-hassan"]
BLUE = {"color": "0x3366FFFF", "thickness": 2, "visible": True}


def drawing(name, primitive, **fields):
    """A DCS map drawing on the Blue layer of the OIR mission."""
    return {"kind": "drawing", "name": "OIR " + name, "mission_id": MISSION_ID, "layer": "Blue", "primitive_type": primitive,
            **fields, "style": dict(BLUE)}


def magnetic(value):
    return {"value": value, "reference": "magnetic", "declination_deg": DECLINATION}


def fix(navaid):
    return {"ident": navaid["ident"], "position": deepcopy(navaid["position"])}


def urn(name, version):
    return f"urn:openaix:schema:{name}:{version}"


def runway(version):
    record = deepcopy(next(item for item in ojms()["runways"] if item["designator"] == "13/31"))
    record["name"] = "Muwaffaq Salti runway 13/31"
    for end in record["ends"]:
        end["threshold_crossing_height"] = length(50)
    record["ends"][0]["displaced_threshold"] = length(300)
    return {"$schema": urn("runway", version), **record, "airfield": "ojms", "source": DCS_SOURCE,
            "extensions": dcs([drawing("Salti runway 13/31", "Line", line_mode="segments", closed=True)]),
            "resources_ref": deepcopy(RESOURCES_REF)}


def path_point(version):
    ends = {end["designator"]: end for end in ojms()["runways"][1]["ends"]}
    threshold, far_end = ends["31"]["threshold"], ends["13"]["threshold"]
    return {"$schema": urn("path-point", version), "id": "ojms-r31-path-point", "kind": "path-point",
            "name": "Muwaffaq Salti RNAV runway 31 final approach path", "airfield": "ojms", "runway": "31", "approach": "R31",
            "approach_type": "LPV", "landing_threshold_point": deepcopy(threshold),
            "landing_threshold_elevation": {"value": 498.7, "unit": "m", "reference": "MSL"},
            "flight_path_alignment_point": offset(far_end, 311.1, 305), "glide_path_angle_deg": 3.0,
            "threshold_crossing_height": length(50), "course_width_at_threshold": length(105, "m"),
            "final_approach_course": magnetic(306.1), "source": DCS_SOURCE,
            "extensions": dcs([drawing("RW31 threshold", "TextBox", text="RW31 LTP")]), "resources_ref": deepcopy(RESOURCES_REF)}


def holding(version):
    return {"$schema": urn("holding", version), "id": "ghi-hold", "kind": "holding", "name": "GHI missed-approach hold, OJMS I31",
            "hold": {"fix": fix(GHI), "inbound_course": magnetic(306.0), "turn_direction": "right",
                     "altitude": {"kind": "at_or_above", "lower": feet(5000)}, "leg_time": {"value": 1.0, "unit": "min"}},
            "source": DCS_SOURCE, "extensions": dcs([drawing("GHI hold", "Line", line_mode="segments", closed=True)]),
            "resources_ref": deepcopy(RESOURCES_REF)}


def msa(version):
    return {"$schema": urn("msa", version), "id": "ojms-msa", "kind": "msa", "name": "Muwaffaq Salti minimum safe altitude",
            "airfield": "ojms", "center": fix(GHI),
            "sectors": [{"start_bearing": magnetic(0), "end_bearing": magnetic(0), "full_circle": True,
                         "radius": length(25, "nm"), "minimum_altitude": feet(4700)}],
            "source": DCS_SOURCE, "extensions": dcs([drawing("Salti MSA", "Polygon", polygon_mode="circle")]),
            "resources_ref": deepcopy(RESOURCES_REF)}


def grid_mora(version):
    cells = [(35, 6200), (36, 5100), (37, 4400), (38, 4200)]
    return {"$schema": urn("grid-mora", version), "id": "mora-n31e035", "kind": "grid-mora", "name": "Grid MORA row N31 E035 eastward",
            "cells": [{"southwest": position(31, east), "northeast": position(32, east + 1), "status": "known",
                       "minimum_altitude": feet(altitude)} for east, altitude in cells],
            "source": DCS_SOURCE, "extensions": dcs([drawing("MORA row N31", "Polygon", polygon_mode="free")])}


def airway(version):
    middle = offset(GHI["position"], 43.6, 13.6 * 1852)
    return {"$schema": urn("airway", version), "id": "w610", "type": "AIRWAY", "name": "ATS route W610, GHI to ABC", "ident": "W610",
            "airway_type": "air_traffic_services", "level": "low",
            "segments": [
                {"fix": fix(GHI), "outbound_course": magnetic(38.6), "distance": length(13.6, "nm"),
                 "minimum_altitude": feet(5000), "maximum_altitude": feet(19500), "directional_restriction": "forward"},
                {"fix": {"ident": "SALAT", "position": middle}, "inbound_course": magnetic(38.6), "outbound_course": magnetic(38.8),
                 "distance": length(13.6, "nm"), "minimum_altitude": feet(5000), "maximum_altitude": feet(19500)},
                {"fix": fix(ABC), "inbound_course": magnetic(38.8)}],
            "source": DCS_SOURCE, "extensions": dcs([drawing("W610", "Line", line_mode="segments")]),
            "resources_ref": deepcopy(RESOURCES_REF)}


def airspace(version):
    return {"$schema": urn("airspace", version), "id": "salti-ctr", "type": "AIRSPACE", "name": "Salti control zone",
            "designator": "OJMS CTR", "airspace_type": "CTR", "airspace_class_code": "D", "local_type": "Military control zone",
            "description": "Control zone of Muwaffaq Salti from the surface to 4,500 feet MSL.",
            "purpose": "Protect arrivals and departures at Muwaffaq Salti.",
            "components": [{"id": "salti-ctr-core", "name": "Salti CTR", "operation": "add",
                            "geometry": {"kind": "circle", "center": deepcopy(ojms()["position"]), "radius": length(5, "nm")},
                            "lower_limit": {"surface": True}, "upper_limit": feet(4500)}],
            "active": {"continuous": True}, "controlling_agency": "salti-tower", "channels": ["salti-uhf"],
            "coordination_instructions": ["Contact Salti Tower before entry."],
            "restrictions": ["No entry without a clearance from Salti Tower."],
            "notes": "Tower combines ground, tower and approach.",
            "extensions": dcs([drawing("Salti CTR", "Polygon", polygon_mode="circle")]), "resources_ref": deepcopy(RESOURCES_REF)}


def navaid(version):
    """The Muwaffaq Salti VORTAC with its DME antenna and its map icon."""
    return {"$schema": urn("navaid", version), "id": GHI["id"], "type": "NAVAID", "name": GHI["name"], "ident": GHI["ident"],
            "class": "VORTAC", "airfield": "ojms", "position": deepcopy(GHI["position"]), "dme_position": position(31.83478, 36.77861),
            "elevation": feet(1636), "magnetic_variation_deg": DECLINATION, "frequency": {"value": GHI["frequency"], "unit": "MHz"},
            "tacan": {"channel": GHI["channel"], "band": "X", "identifier": GHI["ident"]}, "source": DCS_SOURCE,
            "extensions": dcs([drawing("GHI VORTAC", "Icon", icon="P91000009.png")]), "resources_ref": deepcopy(RESOURCES_REF)}


def localizer(version):
    """The IGHI localizer of runway 31 with its glide slope and its map label."""
    record = deepcopy(next(item for item in ojms_navigation(version)[0] if item["id"] == "ojms-ils-31"))
    return {"$schema": urn("localizer", version), **record, "glide_slope": {"angle_deg": 3.0, "position": position(31.828, 36.7905),
                                                                           "elevation": feet(1636)},
            "threshold_crossing_height": length(50), "extensions": dcs([drawing("IGHI localizer", "TextBox", text="IGHI 108.9")]),
            "resources_ref": deepcopy(RESOURCES_REF)}


def seed_fields():
    """Schema name -> fields that the richest curated OIR record of the schema does not give, for that record."""
    exercise = {"org.cjtf-oir.ato": {"ato_day": "214"}}
    return {
        "measures/aca": {"purpose": "Protect aircraft from the Anvil battery fires into Onyx.",
                         "notes": "Active only while Anvil fires; Warhawk announces each fire mission.",
                         "extensions": dcs([drawing("Anvil ACA", "Polygon", polygon_mode="free")])},
        "measures/aor": {"notes": "The AOR boundary follows the Jordanian and Syrian borders in the south and the west.",
                         "extensions": dcs([drawing("OIR AOR", "Line", line_mode="segments", closed=True)])},
        "measures/area": {"notes": "No fires into the logistics site without the clearance of Task Force Bastion."},
        "measures/cl": {"notes": "Warhawk controls the airspace below the coordinating altitude; Banshee controls the airspace above it.",
                        "extensions": {"org.cjtf-oir.aco": {"acm_serial": "CA-01"}}},
        "measures/fire-support-line": {"notes": "Fires across the RFL need the clearance of the other task force.",
                                       "extensions": dcs([drawing("Pewter RFL", "Line", line_mode="segments")])},
        "measures/isr": {"notes": "Aircraft inside the range show IFF modes 1, 3 and 4 to Kestrel.",
                         "extensions": dcs([{"kind": "trigger_zone", "name": "OIR Kestrel ISR", "mission_id": MISSION_ID, "zone_type": "circle"}])},
        "measures/line": {"notes": "Fires across the boundary need coordination between Task Force Bastion and Task Force Basin.",
                          "extensions": dcs([drawing("Bastion Basin boundary", "Line", line_mode="segments")])},
        "measures/mez": {"purpose": "Protect the Sage FARP from low-level air attack.",
                         "notes": "Avenger weapons tight; engage only hostile aircraft inside the zone."},
        "measures/misarc": {"notes": "Aircraft remain clear of the arc while Kestrel fires."},
        "measures/orbit": {"notes": "Falcon is the CAP station on the northern threat axis."},
        "measures/route": {"extensions": dcs([drawing("South transit", "Line", line_mode="segments")])},
        "measures/tl": {"notes": "Cross the Granite area at the traverse level only.",
                        "extensions": {"org.cjtf-oir.aco": {"acm_serial": "TL-01"}}},
        "procedure": {"extensions": dcs([drawing("I31 approach", "Line", line_mode="segments")])},
        "jiptl": {"extensions": exercise}, "tst": {"extensions": exercise}, "spins": {"extensions": exercise},
    }


def navigation_seeds(version):
    """Schema name -> OIR record for the navigation schemas with only KDEN or US civil curated examples."""
    return {"runway": runway(version), "path-point": path_point(version), "holding": holding(version), "msa": msa(version),
            "grid-mora": grid_mora(version), "measures/airway": airway(version), "measures/airspace": airspace(version),
            "measures/navaid": navaid(version), "localizer": localizer(version)}


DEIR_EZ_ZOR = position(35.335, 40.14)


def field_values():
    """OIR values by field name, for the fields that no curated OIR record gives."""
    return [
        {"geometry": {"kind": "point", "position": position(35.21, 40.17)}},
        {"geometry": {"kind": "description", "text": "Euphrates west bank from the Deir ez-Zor bridge to the Al Busayrah ferry"}},
        {"geometry": {"kind": "rectangle", "center": position(35.21, 40.17), "projection": "Syria", "dcs_angle_deg": 30,
                      "width_m": 4000, "height_m": 2000}},
        {"geometry": {"kind": "ellipse", "center": position(35.18, 40.24), "projection": "Syria", "dcs_angle_deg": 30,
                      "north_radius_m": 3000, "east_radius_m": 1500}},
        {"geometry": {"kind": "figure_eight", "point": position(34.95, 39.8), "axis": magnetic(90),
                      "leg_length": length(20, "nm"), "turn_radius": length(5, "nm")}},
        {"geometry": {"kind": "sector", "center": deepcopy(DEIR_EZ_ZOR), "start_bearing": magnetic(60), "end_bearing": magnetic(150),
                      "inner_radius": length(5, "nm"), "outer_radius": length(15, "nm")}},
        {"geometry": {"kind": "track_racetrack", "a": position(34.6, 39.3), "b": position(34.9, 39.7), "width": length(10, "nm"),
                      "turns": "right"}},
        {"geometry": {"kind": "polyarc", "segments": [
            {"kind": "line", "start": position(35.2, 40.0), "end": position(35.2, 40.3)},
            {"kind": "arc", "center": deepcopy(DEIR_EZ_ZOR), "radius": length(10, "nm"), "start_bearing": magnetic(120),
             "end_bearing": magnetic(240), "turns": "right"}]}},
        {"push": {"offset_minutes": 30}},
        {"extensions": {"org.cjtf-oir.ato": {"ato_day": "214"}}},
        # DCS object attributes in `extensions.sim.dcs`: a mission object number and the Blue layer colours.
        {"bindings": [{"closed": False}]},
        {"bindings": [{"object_id": 44, "closed": True, "angle_deg": 0, "group_category": "airplane"}]},
        {"style": {"fill_color": "0x3366FF20", "font_size": 14}},
        # Airspace components: a terrain-following floor and a raised ceiling.
        {"components": [{"minimum_limit": feet(500, "AGL"), "maximum_limit": feet(18000)}]},
        # Airfields and runways of eastern Jordan.
        {"lighting": {"reil": True}},
        {"categories": {"fighter": {"altitude": feet(1500, "AGL"), "overhead_altitude": feet(2500, "AGL")},
                        "heavy": {"altitude": feet(2000, "AGL")}}},
        {"initial": [{"distance": length(5, "nm"), "bearing": magnetic(126.1)}]},
        {"frequencies": [{"hours": {"time_reference": "UTC", "periods": [
            {"weekdays": ["fri"], "start_time": "04:00:00", "end_time": "20:00:00", "end_day_offset": 0}]},
                          "notes": "Monitor guard 243.0 MHz outside the tower hours."}]},
        {"edges": [{"taxiway": "A"}]},
        {"hold": {"speed": {"kind": "at_or_below", "value": {"value": 230, "unit": "kt"}}}},
        {"legs": [{"fly_over": True, "recommended_navaid": {"kind": "control_measure", "id": "ghi"},
                   "speed": {"kind": "at_or_below", "value": {"value": 210, "unit": "kt"}}, "time": {"value": 1.0, "unit": "min"},
                   "vertical_angle_deg": -3.0, "arc_center": {"kind": "control_measure", "id": "ghi"}, "arc_radius": length(10, "nm")}]},
        {"equipment": [{"notes": "Spare batteries for 24 hours of operation."}]},
        # ATO missions, flights and taskings of 2 October.
        {"missions": [{"constraints": ["No weapons release within 500 m of the Euphrates bridges."],
                       "contingencies": [{"condition": "Ceiling over the target below 3000 feet.",
                                          "action": "Hold at Marshal and wait for the Banshee weather update.",
                                          "decision_authority": "banshee", "alternate_route": "marshal-exit", "divert": "prince-hassan"}],
                       "request_refs": [{"id": "asr-214-07", "revision": "1", "title": "Air support request 214-07"}],
                       "tasking_relationship": "assigned"}]},
        {"control": {"handovers": ["darkstar"]}},
        {"flights": [{"notes": "Flight lead briefs the package at 1145Z in the Salti operations building.",
                      "alternate_routes": ["marshal-exit"], "spins_paragraphs": ["rules_of_engagement", "personnel_recovery"]}]},
        {"activities": [{"description": "Air refuelling from Shell before the push."}]},
        {"fuel": {"notes": "Bingo includes the fuel for a divert to Prince Hassan.", "reserve": {"value": 2000, "unit": "lb"}}},
        {"identification": {"mode_2": "5201"}},
        {"recovery": {"planned_time": "2026-10-02T14:55:00Z"}},
        {"tasking": {"supporting_request": {"id": "asr-214-07", "revision": "1", "title": "Air support request 214-07"},
                     "request_refs": [{"id": "asr-214-09", "revision": "1", "title": "Air support request 214-09"}],
                     "target_assignment_procedure": "cas-check-in", "tasking_procedure": "sar-recognition",
                     "coordination_procedure": "harm-employment", "ground_coordination": "warhawk"}},
        {"pickup_time": {"tolerance_seconds": 300}},
        {"assignments": [{"activation_condition": "Banshee reports the target area clear of civilian traffic."}]},
        {"air_assault": {"corridors": [{"kind": "control_measure", "id": "mrr-tinsel"}]}},
        {"airdrop": {"code_letter": "T"}},
        {"brief": {"patients": {"litter": 0, "ambulatory": 2, "attendants": 1},
                   "schema": "urn:cjtf-oir:schema:range-clearance:1",
                   "training_areas": [{"kind": "control_measure", "id": "jettison-tin"}],
                   "cas": {"check_in": {"procedure": "cas-check-in", "abort_code": "Black"}}}},
        {"manifest": {"personnel_notes": "Two passengers with personal weapons; seats on the left side."}},
        # OPORD annexes and paragraphs.
        {"reports": [{"to_unit": "caoc"}]},
        {"obstacles": [{"complete_by": "2026-10-02T12:00:00Z"}]},
        {"coordinating_instructions": {"effective_condition": "At the start of the ATO period or on the CAOC execute order."}},
        {"concept_of_operations": {"rear_area": "aa-bastion"}},
        {"approach_instructions": ["Expect radar vectors to the ILS runway 31 final from GHI.", "Report 10 nm final to Salti Tower."]},
        {"base": {"id": "oir-spins", "revision": "1", "path": "/remarks"}},
        {"changes": [{"op": "replace", "path": "/remarks", "value": "All times are UTC. Transition altitude 13000 feet; QNH below it.",
                      "remarks": "The transition altitude is the Jordanian value for the whole AOR."}]},
        {"separation": "altitude"},
        {"gates": ["sp-sage", "rp-nickel"], "responsible_agency": "caoc", "aor": "oir-aor"},
        {"responsibility_above": "darkstar", "responsibility_below": "warhawk"},
        {"coordinating_altitude": feet(10000)},

        {"active": {"start": "2026-10-02T13:00:00Z", "end": "2026-10-02T15:00:00Z",
                    "schedule": {"time_reference": "UTC", "periods": [
                        {"weekdays": ["fri"], "start_time": "13:00:00", "end_time": "15:00:00", "end_day_offset": 0}],
                        "exclusions": [{"start": "2026-10-02T13:40:00Z", "end": "2026-10-02T14:00:00Z"}]}}},
    ]


def complete(name, seed, resources):
    """Fields of one record that depend on the record itself: MGRS of its positions, its brief attachments, the
    reports it defines and, for the ACO, the airfield records that its inline catalogue refers to."""
    from openaix.coordinates import format_mgrs

    def mgrs(point):
        return format_mgrs(point["latitude"], point["longitude"])

    if name == "jiptl":
        for target in seed["targets"]:
            if "location" in target:
                target["location_mgrs"] = mgrs(target["location"])
    if name == "tst":
        for target in seed["targets"]:
            for location in target.get("expected_locations", []):
                location["mgrs"] = mgrs(location["position"])
    if name == "fac":
        vox = seed["extensions"]["org.vox-bellica.jtac"]
        vox.update({"voice_id": "jtac-axeman", "memory_file": "local/axeman-memory.json", "impact_window_s": 20,
                    "precise_coords_delay_s": 30, "last_call_on_loss": True, "town_ips": True,
                    "night": {"mode": "auto", "sun_deg": -6, "start_hour": 18, "end_hour": 5, "utc_offset_h": 3,
                              "ir_mark": True, "snake_amplitude_m": 50, "snake_period": "4s"},
                    "launch_warnings": {"enabled": True, "range_m": 15000, "delay_min": "2.5s", "delay_max": "6s", "coalesce": "5s"},
                    "fah": {"laser_cone": True, "laser_cone_deg": 10, "laser_prefer_deg": 45, "observer_buffer_m": 500,
                            "friendly_parallel_reds": 2, "valley_min_depth_m": 30, "road_max_m": 200, "terrain": True},
                    "danger_close": {"initials": "AX"}})
        vox["stack"].update({"helo_block_ft": 500, "helo_floor_ft": 1000})
    if name == "ato":
        flights = {flight["id"]: flight for mission in seed["missions"] for flight in mission["flights"]}
        # Rage (F-15E strike): a SCAR load as the secondary load. Weasel 2 has no serviceable Sniper pod and flies the
        # pre-2015 SEAD load.
        flights["rage"]["configuration"].update({
            "secondary_scl": "f15e-scar", "secondary_purpose": "SCAR on the Cobalt vehicle park when the strike target is closed."})
        weasel = flights["weasel"]
        weasel["configuration"]["member_overrides"] = [{"member": 2, "scl": "f16-sead-pre2015", "fuel": deepcopy(weasel["fuel"]),
                                                        "identification": {"mode_3": "4106"}}]
        flights["dodge"]["identification"]["tacan"] = {"channel": 37, "band": "Y", "identifier": "DDG"}
    if name == "scl":
        seed["source"]["path"] = "scl/f-16c-viper"
    if name == "resources":
        catalogue = seed["resources"]
        catalogue["targets"]["gainful-battery"]["briefing"] = [{"kind": "map", "path": "briefs/gainful-search-box.png",
                                                               "title": "Gainful search box", "caption": "Last report on the river road north of Cobalt."}]
        catalogue["targets"]["cobalt-array"]["briefing"] = [{"kind": "image", "path": "briefs/cobalt-compound.png",
                                                            "title": "Cobalt compound", "caption": "Command post and vehicle park west of the Euphrates."}]
        catalogue["targets"]["unknown-track"]["briefing"] = [{"kind": "document", "path": "briefs/unknown-track.pdf",
                                                             "title": "Unknown air track report"}]
        depot = catalogue["targets"]["zinc-depot"]
        depot["briefing"] = [{"kind": "image", "path": "briefs/zinc-depot.png", "title": "Zinc supply depot",
                              "caption": "Four fuel tanks east of the road; the vehicle shed is to the west."}]
        depot["aimpoints"]["fuel-tanks"]["briefing"] = [{"kind": "image", "path": "briefs/zinc-depot-tanks.png",
                                                         "title": "Zinc fuel tanks", "caption": "Aimpoint on the north tank."}]
        depot["aimpoints"]["fuel-tanks"]["extensions"] = dcs(objects=[
            {"kind": "static", "name": "OIR Zinc fuel tank 1", "mission_id": MISSION_ID},
            {"kind": "static", "name": "OIR Zinc fuel tank 2", "mission_id": MISSION_ID}])
        catalogue["threats"]["sa-6"]["briefing"] = [{"kind": "document", "path": "briefs/sa-6-gainful.pdf",
                                                    "title": "Gainful battery threat brief"}]
        catalogue["reports"]["misrep"].update({"format_ref": "USMTF MISREP", "frequency": "Within 30 minutes of landing",
                                               "submitter": "Flight lead"})
    if name == "aco":
        source = resources["resources"]
        catalogue = seed.setdefault("resources", {})
        for group, keys in (("places", ("ojms",)), ("localizers", ("ojms-ils-31", "ojms-ils-26")),
                            ("instrument_procedures", ("ojms-i31",)), ("pattern_profiles", ("usaf-standard",)),
                            ("control_measures", ("ghi", "gainful-misarc", "zinc-mez")), ("emitters", ("sa6-gainful", "sa3-zinc"))):
            for key in keys:
                catalogue.setdefault(group, {}).setdefault(key, deepcopy(source[group][key]))
        for key in source["agencies"]:
            catalogue.setdefault("agencies", {}).setdefault(key, deepcopy(source["agencies"][key]))
        for key in source["channels"]:
            catalogue.setdefault("channels", {}).setdefault(key, deepcopy(source["channels"][key]))
    return seed
