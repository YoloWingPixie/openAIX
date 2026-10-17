"""OIR operating locations on the DCS Syria map: Muwaffaq Salti (OJMS), Prince Hassan (H5) and H4 airfields, the
Sage FARP and a carrier in the eastern Mediterranean.

Runway ends, stands and the taxi graph come from the DCS Syria airfield layer (AirfieldsTaxiways, as decoded by the
Vox Bellica map pack); tower frequencies from the terrain's radio.lua; VORTAC and ILS data from its beacons.lua.
Elevations come from the DCS beacon heights where the field has a beacon. Magnetic variation is approximate.
"""
import math
from copy import deepcopy

from openaix.examples.aco import MISSION_ID, position
from openaix.sim.dcs import extension as dcs

EARTH_RADIUS_M = 6371008.8
FOOT = 0.3048
DECLINATION = 5.0  # degrees east, approximate for eastern Jordan
DCS_SOURCE = "DCS World Syria map: AirfieldsTaxiways layer, radio.lua and beacons.lua"


def offset(origin, bearing_deg, distance_m):
    """Position at a true bearing and a distance from an origin, on a sphere, rounded to six decimals."""
    lat, lon = math.radians(origin["latitude"]), math.radians(origin["longitude"])
    angle, bearing = distance_m / EARTH_RADIUS_M, math.radians(bearing_deg)
    end_lat = math.asin(math.sin(lat) * math.cos(angle) + math.cos(lat) * math.sin(angle) * math.cos(bearing))
    end_lon = lon + math.atan2(math.sin(bearing) * math.sin(angle) * math.cos(lat), math.cos(angle) - math.sin(lat) * math.sin(end_lat))
    return position(round(math.degrees(end_lat), 6), round(math.degrees(end_lon), 6))


def radial_dme(origin, target, navaid_id, nm_digits=1):
    """Radial (magnetic) and distance of a target from a navigation aid, as a Fix radial and distance definition."""
    lat1, lon1 = math.radians(origin["latitude"]), math.radians(origin["longitude"])
    lat2, lon2 = math.radians(target["latitude"]), math.radians(target["longitude"])
    bearing = math.atan2(math.sin(lon2 - lon1) * math.cos(lat2),
                         math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1))
    arc = 2 * math.asin(math.sqrt(math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2))
    return {"navaid": {"kind": "control_measure", "id": navaid_id},
            "radial": {"value": round((math.degrees(bearing) - DECLINATION) % 360, 1), "reference": "magnetic", "declination_deg": DECLINATION},
            "distance": {"value": round(arc * EARTH_RADIUS_M / 1852, nm_digits), "unit": "nm"}}


def feet(value, reference="MSL"):
    return {"value": value, "unit": "ft", "reference": reference}


def length(value, unit="ft"):
    return {"value": value, "unit": unit}


def station(role, megahertz, callsign, band=None, modulation="AM"):
    band = band or ("uhf" if megahertz >= 225 else "vhf")
    return {"role": role, "frequency": {"value": megahertz, "unit": "MHz", "modulation": modulation, "band": band}, "callsign": callsign}


def runway(airfield_id, pair, ends, length_m, width_m, elevation, extras=None):
    """A runway from the two DCS runway points: `ends` maps each designator to (latitude, longitude, true heading)."""
    result = {"id": airfield_id + "-rw" + pair.replace("/", "-").lower(), "kind": "runway", "name": pair, "designator": pair,
              "length": length(round(length_m / FOOT)), "width": length(round(width_m / FOOT)), "surface": "hard", "ends": []}
    for name in pair.split("/"):
        latitude, longitude, true_heading = ends[name]
        end = {"designator": name, "threshold": position(latitude, longitude), "threshold_elevation": feet(elevation),
               "heading": {"value": round((true_heading - DECLINATION) % 360, 1), "reference": "magnetic", "declination_deg": DECLINATION}}
        end.update(deepcopy((extras or {}).get(name, {})))
        result["ends"].append(end)
    return result


# The VORTAC of each airfield that has one in the DCS Syria beacons.lua.
NAVAIDS = {
    "ojms": {"id": "ghi", "name": "Muwaffaq Salti VORTAC", "ident": "GHI", "position": position(31.834683, 36.778475),
             "frequency": 113.8, "channel": 85},
    "prince-hassan": {"id": "abc", "name": "Prince Hassan VORTAC", "ident": "ABC", "position": position(32.159572, 37.148259),
                      "frequency": 115.9, "channel": 106},
}
ELEVATIONS = {"ojms": 1636, "prince-hassan": 2165}


def base(identifier, name, ident, reference, elevation, frequencies, runways, **extra):
    result = {"id": identifier, "kind": "airfield", "name": name, "ident": ident, "use": "military",
              "position": reference, "elevation": feet(elevation), "magnetic_variation_deg": DECLINATION,
              "transition_altitude": feet(13000), "runways": runways, "frequencies": frequencies,
              "extensions": dcs([{"kind": "airbase", "name": name, "mission_id": MISSION_ID}], coalition=extra.pop("coalition", "blue")),
              "source": DCS_SOURCE, **extra}
    if identifier in NAVAIDS:
        result["navaids"] = [{"kind": "control_measure", "id": NAVAIDS[identifier]["id"]}]
    return result


def tacans():
    """The airfield VORTAC stations as navigation aids that name their airfield."""
    result = {}
    for airfield, data in NAVAIDS.items():
        result[data["id"]] = {"id": data["id"], "type": "NAVAID", "name": data["name"], "ident": data["ident"], "class": "VORTAC",
                              "airfield": airfield, "position": deepcopy(data["position"]), "elevation": feet(ELEVATIONS[airfield]),
                              "frequency": {"value": data["frequency"], "unit": "MHz"},
                              "tacan": {"channel": data["channel"], "band": "X", "identifier": data["ident"]},
                              "source": DCS_SOURCE}
    return result


BAK_12 = [{"type": "BAK_12", "distance_from_threshold": length(1500)}]
OJMS_REFERENCE = position(31.825431, 36.781257)
OJMS_ENDS = {"08": (31.815801, 36.766644, 79.9), "26": (31.819432, 36.790728, 259.9),
             "13": (31.841077, 36.773265, 131.1), "31": (31.825413, 36.79439, 311.1)}
OJMS_ENDS_POSITION = {name: position(latitude, longitude) for name, (latitude, longitude, _) in OJMS_ENDS.items()}


def ojms():
    runways = [
        runway("ojms", "08/26", OJMS_ENDS, 2316, 60, 1636,
               {"26": {"localizer": "ojms-ils-26", "lighting": {"edge_lights": True}}}),
        runway("ojms", "13/31", OJMS_ENDS, 2649, 60, 1636,
               {"13": {"lighting": {"edge_lights": True}, "arresting_gear": BAK_12},
                "31": {"localizer": "ojms-ils-31", "arresting_gear": BAK_12, "traffic_pattern": {"direction": "right"},
                       "lighting": {"edge_lights": True, "slope_indicator": "PAPI", "approach_lighting": "SSALR"}}}),
    ]

    def stand(number, at, heading, category, width, depth, **extra):
        return {"id": "stand-" + number.lower(), "name": number, "position": position(*at), "heading": {"value": heading, "reference": "true"},
                "category": category, "width": length(width, "m"), "length": length(depth, "m"),
                "extensions": dcs([{"kind": "stand", "name": number}]), **extra}

    stands = [
        stand("40", (31.834801, 36.786459), 324.9, "fighter", 24, 26, ramp="Main ramp"),
        stand("41", (31.834627, 36.786673), 325.2, "fighter", 24, 26, ramp="Main ramp"),
        stand("29", (31.844813, 36.779449), 339.3, "fighter", 13, 18, shelter=True, ramp="North-west shelters"),
        stand("31", (31.843114, 36.776102), 281.2, "fighter", 13, 18, shelter=True, ramp="North-west shelters"),
        stand("115", (31.824955, 36.792494), 184.8, "heavy", 52, 60, ramp="South-east apron"),
        stand("H01", (31.828852, 36.794642), 250.3, "helicopter", 15, 18, helicopters=True, ramp="South-east apron"),
    ]
    # A reduced taxi graph from the DCS junctions: the main ramp to the runway 13 entry. DCS does not name the taxiways.
    nodes = [
        {"id": "stand-40-lead", "kind": "parking", "stand": "stand-40", "position": position(31.834355, 36.785792)},
        {"id": "stand-41-lead", "kind": "parking", "stand": "stand-41", "position": position(31.834198, 36.786004)},
        {"id": "ramp-exit", "kind": "intersection", "name": "Ramp exit", "position": position(31.835153, 36.784718)},
        {"id": "parallel-north", "kind": "intersection", "name": "North-west corner", "position": position(31.839513, 36.778844)},
        {"id": "entry-turn", "kind": "intersection", "name": "Runway 13 entry turn", "position": position(31.839171, 36.778002)},
        {"id": "hold-13", "kind": "hold_short", "name": "Holding point runway 13", "runway_end": "13", "position": position(31.837092, 36.778961)},
        {"id": "entry-13", "kind": "runway_connection", "runway_end": "13", "position": position(31.836528, 36.779398)},
    ]
    wide = length(52, "m")
    edges = [
        {"from": "stand-40-lead", "to": "ramp-exit", "width": wide},
        {"from": "stand-41-lead", "to": "stand-40-lead", "width": wide},
        {"from": "ramp-exit", "to": "parallel-north", "width": wide, "category": "heavy"},
        {"from": "parallel-north", "to": "entry-turn", "width": wide},
        {"from": "entry-turn", "to": "hold-13", "width": wide, "one_way": True},
        {"from": "hold-13", "to": "entry-13", "width": wide},
    ]
    return base("ojms", "Muwaffaq Salti", "OJMS", OJMS_REFERENCE, 1636,
                [station("tower", 253.15, "Salti Tower"), station("tower", 120.5, "Salti Tower"),
                 station("ground", 253.15, "Salti Tower"), station("approach", 253.15, "Salti Tower"),
                 station("atis", 251.85, "Salti Information"), station("pmsv", 344.6, "Salti Metro"), station("ops", 255.4, "Kingpin"),
                 station("final", 262.85, "Salti Final")],
                runways, calm_wind_runway="13", hung_ordnance_runway="31", controlling_agency="salti-tower",
                # End-of-runway arming and hot brake pads at the runway 31 threshold, and the hung ordnance pad.
                pads=[{"name": "EOR 31", "position": offset(OJMS_ENDS_POSITION["31"], 41.1, 180), "use": ["arm_dearm", "hot_brake"]},
                      {"name": "Hung ordnance pad", "position": offset(OJMS_ENDS_POSITION["31"], 221.1, 250), "use": ["hung_ordnance"]}],
                atis={"runway_in_use": "13", "transition_level": {"value": 150, "unit": "flight_level", "reference": "FL"},
                      "remarks": ["Tower combines ground, tower and approach on 253.15 and 120.5; BAK-12 cables 1500 feet from both runway 13 and 31 thresholds.",
                                  "Transient fighters park on stands 40 and 41; shelters are at the north-west end."]},
                traffic_pattern={"profile": "usaf-standard", "overhead_altitude": feet(3600), "initial": [{"distance": length(5, "nm")}],
                                 "reentry": {"point": {"kind": "control_measure", "id": "vrp-salti-dam"}, "altitude": feet(3600)},
                                 "go_around": {"altitude": feet(4600), "heading": {"value": 306, "reference": "magnetic"}}},
                localizers=["ojms-ils-31", "ojms-ils-26"],
                procedures=["ojms-i31", "ojms-par31", "ojms-asr13", "ojms-r13", "ojms-salat1"],
                holdings=["ghi-hold"], msas=["ojms-msa"],
                parking=stands, taxi={"nodes": nodes, "edges": edges})


def prince_hassan():
    ends = {"13": (32.169103, 37.138014, 131.0), "31": (32.152366, 37.160789, 311.0)}
    hours = {"time_reference": "UTC", "periods": [{"weekdays": ["sun", "mon", "tue", "wed", "thu"], "start_time": "03:00:00",
                                                    "end_time": "01:00:00", "end_day_offset": 1}]}
    return base("prince-hassan", "Prince Hassan", "OJHR", position(32.160735, 37.149403), 2165,
                [station("tower", 252.95, "PrinceHassan Tower"), station("tower", 122.6, "PrinceHassan Tower")],
                [runway("prince-hassan", "13/31", ends, 2839, 60, 2165)],
                calm_wind_runway="31", operating_hours=hours, traffic_pattern={"profile": "usaf-standard"})


def h4():
    ends = {"10": (32.541449, 38.183712, 102.7), "28": (32.537115, 38.206446, 282.7)}
    return base("h4", "H4", "OJHF", position(32.539282, 38.19508), 2251,
                [station("tower", 250.15, "H4 Tower"), station("tower", 122.6, "H4 Tower")],
                [runway("h4", "10/28", ends, 2188, 45, 2251)], calm_wind_runway="28", traffic_pattern={"profile": "usaf-standard"})


def farp():
    reference = position(34.735, 40.225)
    return {"id": "farp-sage", "kind": "farp", "name": "Sage FARP", "use": "military", "position": reference,
            "elevation": feet(1150), "pads": [{"name": "Pad 1", "position": offset(reference, 0, 30)},
                                              {"name": "Pad 2", "position": offset(reference, 180, 30)}],
            "frequencies": [station("ops", 41.5, "Sage Ops", "fm", "FM"), station("ops", 285.0, "Sage Ops")],
            "controlling_agency": "banshee",
            "extensions": dcs([{"kind": "static", "name": "OIR Sage FARP", "mission_id": MISSION_ID}], coalition="blue")}


def tiyas():
    """Tiyas (T4), the base of the third-party fighters: a hostile airfield in the DCS Syria mission (red coalition)."""
    ends = {"09": (34.52271, 37.6125, 89.8), "27": (34.52229, 37.6455, 269.8)}
    return base("tiyas", "Tiyas", "OSTF", position(34.5225, 37.6297), 1797, [station("tower", 120.5, "Tiyas Tower", "vhf")],
                [runway("tiyas", "09/27", ends, 3030, 45, 1797)], coalition="red")


def salti_vfr(version):
    """A visual reporting point north of Muwaffaq Salti, the published VFR route from the point to the field, and the
    published VFR arrival from the east that arcs around the field to the point and joins that route."""
    dam = offset(OJMS_REFERENCE, 20, 8 * 1852)
    vrp = {"$schema": f"urn:openaix:schema:point:{version}", "id": "vrp-salti-dam", "name": "Salti Dam", "type": "POINT",
           "roles": ["visual_reporting"], "position": dam, "active": {"continuous": True},
           "description": "Visual reporting point at the dam north-east of Muwaffaq Salti; the re-entry point of the overhead pattern."}
    route = {"$schema": f"urn:openaix:schema:measure-route:{version}", "id": "vfr-salti-north", "type": "VFRRTE",
             "name": "Salti north VFR route", "active": {"continuous": True},
             "geometry": {"kind": "line", "points": [deepcopy(dam), deepcopy(OJMS_REFERENCE)]},
             "altitude": {"lower": feet(3500), "upper": feet(4500)},
             "vertices": [{"index": 0, "name": "DAM", "point": "vrp-salti-dam"}, {"index": 1, "name": "OJMS"}]}
    east, arc_start = offset(OJMS_REFERENCE, 90, 14 * 1852), offset(OJMS_REFERENCE, 60, 8 * 1852)
    arrival = {"$schema": f"urn:openaix:schema:measure-route:{version}", "id": "vfr-salti-east", "type": "VFRRTE",
               "name": "Salti east VFR arrival", "active": {"continuous": True},
               "description": "Published VFR arrival from the highway east of Muwaffaq Salti; it arcs north at 8 nm to Salti Dam.",
               "purpose": "Keep VFR arrivals clear of the runway 31 final approach.",
               "geometry": {"kind": "path", "segments": [
                   {"kind": "line", "start": east, "end": arc_start},
                   {"kind": "arc", "center": deepcopy(OJMS_REFERENCE), "radius": length(8, "nm"),
                    "start_bearing": {"value": 60, "reference": "true"}, "end_bearing": {"value": 20, "reference": "true"}, "turns": "left"}]},
               "altitude": {"lower": {"surface": True}, "upper": feet(4500)},
               "vertices": [{"index": 0, "name": "HIGHWAY"}, {"index": 2, "name": "DAM", "point": "vrp-salti-dam"}],
               "joins": [{"route": "vfr-salti-north", "vertex": 2}],
               "serves": [{"airfield": "ojms", "runway": "31"}, {"airfield": "ojms", "runway": "26"}],
               "controlling_agency": "salti-tower", "channels": ["salti-uhf"],
               "restrictions": ["Remain at or below 4,500 feet MSL until Salti Dam."],
               "coordination_instructions": ["Report HIGHWAY to Salti Tower; continue on the north route from Salti Dam."],
               "notes": "Not sterile of other traffic; helicopters use the same highway."}
    return {"vrp-salti-dam": vrp, "vfr-salti-north": route, "vfr-salti-east": arrival}


def usaf_standard():
    """Named pattern profile with typical US Air Force values: overhead 500 ft above a rectangular pattern."""
    return {"direction": "left", "altitude": feet(1500, "AGL"), "overhead_altitude": feet(2000, "AGL"), "break_point": "approach_end",
            "initial": [{"distance": length(5, "nm")}],
            "reentry": {"name": "Re-entry point", "altitude": feet(2000, "AGL")}, "go_around": {"altitude": feet(2000, "AGL")},
            "sfo": {"high_key": {"lower": feet(7000, "AGL"), "upper": feet(9000, "AGL")},
                    "low_key": {"lower": feet(3000, "AGL"), "upper": feet(5000, "AGL")}},
            "categories": {"trainer": {"altitude": feet(1000, "AGL"), "overhead_altitude": feet(1500, "AGL")},
                           "helicopter": {"altitude": feet(500, "AGL")},
                           "heavy": {"departure_ceiling": feet(1000, "AGL"), "go_around": {"altitude": feet(2500, "AGL")}}}}


def ojms_navigation(version):
    """The two DCS localizers of Muwaffaq Salti (IGHI runway 31, IGHS runway 26) and the ILS approach to runway 31."""
    threshold = ojms()["runways"][1]["ends"][1]["threshold"]
    course = {"value": round(312.2 - DECLINATION, 1), "reference": "magnetic", "declination_deg": DECLINATION}
    localizers = [
        {"id": "ojms-ils-31", "kind": "localizer", "name": "Muwaffaq Salti ILS runway 31 localizer", "airfield": "ojms",
         "ident": "IGHI", "runway": "31", "ils_category": "I", "frequency": {"value": 108.9, "unit": "MHz"},
         "course": deepcopy(course), "position": position(31.844333, 36.768847), "source": DCS_SOURCE},
        {"id": "ojms-ils-26", "kind": "localizer", "name": "Muwaffaq Salti ILS runway 26 localizer", "airfield": "ojms",
         "ident": "IGHS", "runway": "26", "ils_category": "I", "frequency": {"value": 109.7, "unit": "MHz"},
         "course": {"value": round(261.2 - DECLINATION, 1), "reference": "magnetic", "declination_deg": DECLINATION},
         "position": position(31.815141, 36.76229), "source": DCS_SOURCE},
    ]
    final_fix = offset(threshold, 132.2, 5.2 * 1852)
    outbound = {"value": round(course["value"] - 180, 1), "reference": "magnetic", "declination_deg": DECLINATION}
    ghi = {"ident": NAVAIDS["ojms"]["ident"], "position": deepcopy(NAVAIDS["ojms"]["position"])}
    procedure = {"id": "ojms-i31", "kind": "procedure", "name": "Muwaffaq Salti ILS runway 31 approach (I31)", "airfield": "ojms",
                 "ident": "I31", "procedure_type": "approach", "approach_type": "ils", "runways": ["31"],
                 "holdings": ["ghi-hold"], "msa": "ojms-msa",
                 "remarks": ["Procedure turn not authorized when radar vectors to the final approach course are given.",
                             "Missed approach: climb on the runway 31 course to 5000 feet, then hold at GHI."],
                 "transitions": [
                     {"ident": "GHI", "transition_type": "approach_transition", "legs": [
                         {"leg_type": "initial_fix", "fix": deepcopy(ghi), "approach_fix": ["initial_approach_fix"],
                          "altitude": {"kind": "at_or_above", "lower": feet(5000)}},
                         {"leg_type": "track_to_fix", "fix": {"ident": "FAF31", "position": deepcopy(final_fix),
                                                              "radial_dme": {**radial_dme(NAVAIDS["ojms"]["position"], final_fix, "ghi"),
                                                                             "additional_radials": [{k: v for k, v in radial_dme(
                                                                                 NAVAIDS["prince-hassan"]["position"], final_fix, "abc").items()
                                                                                 if k != "distance"}]}},
                          "altitude": {"kind": "at_or_above", "lower": feet(4000)}},
                         {"leg_type": "procedure_turn", "fix": {"ident": "FAF31", "position": deepcopy(final_fix)}, "course": deepcopy(outbound),
                          "turn_direction": "left", "altitude": {"kind": "at_or_above", "lower": feet(4000)},
                          "procedure_turn": {"turn_type": "turn_45_180", "remain_within": length(10, "nm"),
                                             "outbound_time": {"value": 1.0, "unit": "min"}, "inbound_course": deepcopy(course)}},
                         {"leg_type": "course_to_fix", "fix": {"ident": "FAF31", "position": deepcopy(final_fix)}, "course": deepcopy(course),
                          "recommended_navaid": {"kind": "localizer", "id": "ojms-ils-31"}, "altitude": {"kind": "at", "lower": feet(3300)}}]},
                     {"transition_type": "final_approach", "legs": [
                         {"leg_type": "initial_fix", "fix": {"ident": "FAF31", "position": final_fix}, "approach_fix": ["final_approach_fix"],
                          "altitude": {"kind": "glide_slope_intercept", "lower": feet(3300)}},
                         {"leg_type": "track_to_fix", "fix": {"ident": "RW31", "position": threshold}, "approach_fix": ["missed_approach_point"]},
                         {"leg_type": "course_to_altitude", "course": course,
                          "altitude": {"kind": "at_or_above", "lower": feet(5000)}, "missed_approach": True},
                         {"leg_type": "hold_to_fix", "fix": deepcopy(ghi), "hold": ojms_holding()["hold"],
                          "approach_fix": ["missed_approach_holding_fix"], "missed_approach": True}]}],
                 "navigation_specification": {"navigation_type": "conventional", "sensors": ["ils", "vor", "dme"],
                                              "required_navaids": [{"kind": "control_measure", "id": "ghi"}],
                                              "notes": "GHI DME is necessary for the procedure turn entry from the GHI transition."},
                 "minima": [
                     {"line": "ils", "label": "S-ILS 31", "manoeuvre": "straight_in", "runway": "31", "ils_category": "I",
                      "height_reference": "threshold",
                      "category_minima": [{"categories": ["A", "B", "C", "D"], "decision_altitude": feet(1836), "height": length(200),
                                           "visibility": {"value": 800, "unit": "m"}, "runway_visual_range": length(550, "m")}]},
                     {"line": "ils", "label": "S-ILS 31", "manoeuvre": "straight_in", "runway": "31", "ils_category": "I",
                      "height_reference": "threshold", "condition": "Approach lights of runway 31 out of service.",
                      "category_minima": [{"categories": ["A", "B", "C", "D"], "decision_altitude": feet(1836), "height": length(200),
                                           "visibility": {"value": 1200, "unit": "m"}}]},
                     {"line": "localizer", "label": "S-LOC 31", "manoeuvre": "straight_in", "runway": "31", "height_reference": "threshold",
                      "category_minima": [
                          {"categories": ["A", "B"], "minimum_descent_altitude": feet(2100), "height": length(464),
                           "visibility": {"value": 1200, "unit": "m"}},
                          {"categories": ["C", "D"], "minimum_descent_altitude": feet(2100), "height": length(464),
                           "visibility": {"value": 1600, "unit": "m"}}]},
                     {"line": "localizer", "label": "CIRCLING", "manoeuvre": "circling", "height_reference": "aerodrome",
                      "category_minima": [
                          {"categories": ["A", "B"], "minimum_descent_altitude": feet(2200), "height": length(564),
                           "visibility": {"value": 1600, "unit": "m"}},
                          {"categories": ["C", "D"], "minimum_descent_altitude": feet(2500), "height": length(864),
                           "visibility": {"value": 4000, "unit": "m"}}],
                      "remarks": ["Circling north-east of runway 13/31 is not authorized: the shelters are there."]}],
                 "climb_gradients": [{"gradient": {"value": 250, "unit": "ft/nm"}, "until": feet(5000), "reason": "obstacle",
                                      "notes": "Missed approach climb over the ridge 6 nm north-west of the airfield."}],
                 "obstacle_assessment": {
                     "criteria": "pans_ops", "criteria_document": "ICAO Doc 8168 Volume II, seventh edition",
                     "obstacle_data": "DCS Syria terrain sampled every 100 m in each protection area",
                     "assessed_at": "2026-09-28T10:00:00Z", "tool": {"name": "Salti procedure check", "version": "1.2.0"},
                     "segments": [
                         {"segment": "initial", "transition": "GHI", "from_fix": "GHI", "to_fix": "FAF31", "obstacle_clearance": length(1000),
                          "minimum_altitude": feet(3600), "satisfied": True,
                          "controlling_obstacle": {"ident": "T-0412", "obstacle_type": "terrain", "position": position(31.776, 36.851),
                                                   "elevation": feet(2580)}},
                         {"segment": "final", "from_fix": "FAF31", "to_fix": "RW31", "obstacle_clearance": length(250),
                          "minimum_altitude": feet(2050), "satisfied": True,
                          "controlling_obstacle": {"ident": "OB-0031", "obstacle_type": "structure", "position": position(31.809, 36.815),
                                                   "elevation": feet(1795), "height": length(120)},
                          "notes": "The radio mast south-east of the threshold controls the localizer minimum descent altitude."},
                         {"segment": "missed_approach", "from_fix": "RW31", "obstacle_clearance": length(164),
                          "minimum_altitude": feet(4100), "satisfied": True,
                          "controlling_obstacle": {"obstacle_type": "terrain", "position": position(31.905, 36.69), "elevation": feet(3920)}}],
                     "notes": "The missed approach needs 250 ft/nm to 5000 feet to clear the ridge north-west of the airfield."},
                 "provenance": {"derivation": "synthesized", "authority": "CJTF-OIR airspace control cell", "airac_cycle": "2610",
                                "effective_from": "2026-10-01T00:00:00Z", "effective_until": "2026-10-29T00:00:00Z",
                                "publication": {"id": "ojms-i31-chart", "title": "Muwaffaq Salti ILS runway 31 chart", "revision": "2610"},
                                "tool": {"name": "Salti procedure check", "version": "1.2.0"}, "generated_at": "2026-09-28T10:00:00Z"}}
    return localizers, procedure


def ojms_holding():
    """The missed approach hold of the I31 approach at GHI; the hold legs of the approach use the same definition."""
    course = {"value": 306.0, "reference": "magnetic", "declination_deg": DECLINATION}
    return {"id": "ghi-hold", "kind": "holding", "name": "GHI missed-approach hold, OJMS I31", "airfield": "ojms",
            "hold": {"fix": {"ident": NAVAIDS["ojms"]["ident"], "position": deepcopy(NAVAIDS["ojms"]["position"])},
                     "inbound_course": course, "turn_direction": "right", "altitude": {"kind": "at_or_above", "lower": feet(5000)},
                     "leg_time": {"value": 1.0, "unit": "min"}},
            "source": DCS_SOURCE}


def ojms_msa():
    """The minimum safe altitude of Muwaffaq Salti: one sector around GHI, which the I31 chart shows."""
    return {"id": "ojms-msa", "kind": "msa", "name": "Muwaffaq Salti minimum safe altitude", "airfield": "ojms",
            "center": {"ident": NAVAIDS["ojms"]["ident"], "position": deepcopy(NAVAIDS["ojms"]["position"])},
            "sectors": [{"start_bearing": {"value": 0, "reference": "magnetic", "declination_deg": DECLINATION},
                         "end_bearing": {"value": 0, "reference": "magnetic", "declination_deg": DECLINATION}, "full_circle": True,
                         "radius": length(25, "nm"), "minimum_altitude": feet(4700)}],
            "source": DCS_SOURCE}


def ojms_procedures(version):
    """Radar approaches, an RNP approach and a departure at Muwaffaq Salti, with planning values that agree with the I31 approach."""
    ends = {name: position(latitude, longitude) for name, (latitude, longitude, _) in OJMS_ENDS.items()}

    def magnetic(true_heading):
        return {"value": round((true_heading - DECLINATION) % 360, 1), "reference": "magnetic", "declination_deg": DECLINATION}

    authored = {"derivation": "authored", "authority": "CJTF-OIR airspace control cell", "airac_cycle": "2610"}
    final_13 = offset(ends["13"], 311.1, 5.0 * 1852)
    lost_communications = ["If no transmission is received for one minute on final, climb to 5000 feet on the runway heading and "
                           "contact Salti Tower on 253.15.",
                           "If no transmission is received for five seconds below the glide path intercept altitude, execute the missed approach."]
    par = {"id": "ojms-par31", "kind": "procedure", "name": "Muwaffaq Salti PAR runway 31", "airfield": "ojms", "ident": "PAR31",
           "procedure_type": "approach", "approach_type": "par", "runways": ["31"],
           "radar_approach": {"runway": "31", "final_approach_course": magnetic(311.1), "glide_path_angle_deg": 3.0,
                              "threshold_crossing_height": length(50), "position": position(31.826, 36.7955),
                              "coverage": {"range": length(10, "nm"), "azimuth_left_deg": 10, "azimuth_right_deg": 10,
                                           "elevation_lower_deg": -1, "elevation_upper_deg": 7},
                              "lost_communications": lost_communications},
           "minima": [{"line": "par", "label": "PAR 31", "manoeuvre": "straight_in", "runway": "31", "height_reference": "touchdown_zone",
                       "category_minima": [{"categories": ["A", "B", "C", "D", "E"], "decision_altitude": feet(1836), "height": length(200),
                                            "visibility": {"value": 0.5, "unit": "sm"}, "runway_visual_range": length(2400)}]}],
           "provenance": deepcopy(authored)}
    asr = {"id": "ojms-asr13", "kind": "procedure", "name": "Muwaffaq Salti ASR runway 13", "airfield": "ojms", "ident": "ASR13",
           "procedure_type": "approach", "approach_type": "asr", "runways": ["13"], "transitions": [{"transition_type": "final_approach", "legs": [
               {"leg_type": "initial_fix", "fix": {"ident": "FAF13", "position": final_13}, "approach_fix": ["final_approach_fix"],
                "altitude": {"kind": "at_or_above", "lower": feet(3200)}},
               {"leg_type": "track_to_fix", "fix": {"ident": "STP13", "position": offset(ends["13"], 311.1, 3.0 * 1852)},
                "approach_fix": ["stepdown_fix"], "altitude": {"kind": "stepdown", "lower": feet(2600)}},
               {"leg_type": "track_to_fix", "fix": {"ident": "MAP13", "position": offset(ends["13"], 311.1, 1852)},
                "approach_fix": ["missed_approach_point"], "altitude": {"kind": "at_or_above", "lower": feet(2120)}},
               {"leg_type": "course_to_altitude", "course": magnetic(131.1), "altitude": {"kind": "at_or_above", "lower": feet(5000)},
                "missed_approach": True}]}],
           "radar_approach": {"runway": "13", "final_approach_course": magnetic(131.1), "position": position(31.8297, 36.7866),
                              "coverage": {"range": length(15, "nm")},
                              "recommended_altitudes": [{"distance": length(distance, "nm"), "altitude": feet(altitude)}
                                                        for distance, altitude in ((4, 2900), (3, 2600), (2, 2300))],
                              "missed_approach_point_distance": length(1, "nm"), "lost_communications": lost_communications[:1]},
           "minima": [{"line": "asr", "label": "ASR 13", "manoeuvre": "straight_in", "runway": "13", "height_reference": "touchdown_zone",
                       "category_minima": [{"categories": ["A", "B", "C", "D"], "minimum_descent_altitude": feet(2120), "height": length(484),
                                            "visibility": {"value": 1, "unit": "sm"}}]},
                      {"line": "asr", "label": "ASR circling", "manoeuvre": "circling", "height_reference": "aerodrome",
                       "category_minima": [{"categories": ["A", "B", "C"], "minimum_descent_altitude": feet(2200), "height": length(564),
                                            "visibility": {"value": 1.5, "unit": "sm"}},
                                           {"categories": ["D", "E"], "minimum_descent_altitude": feet(2500), "height": length(864),
                                            "visibility": {"value": 3, "unit": "sm"}}]}],
           "provenance": deepcopy(authored)}
    rf_center = offset(ends["13"], 311.1, 9.0 * 1852)
    rnp = {"id": "ojms-r13", "kind": "procedure", "name": "Muwaffaq Salti RNP runway 13 approach (R13)", "airfield": "ojms", "ident": "R13",
           "procedure_type": "approach", "approach_type": "rnav", "runways": ["13"], "threshold_crossing_height": length(50),
           "transitions": [{"transition_type": "final_approach", "legs": [
               {"leg_type": "initial_fix", "fix": {"ident": "SALTI", "position": offset(rf_center, 221.1, 3 * 1852)},
                "approach_fix": ["initial_approach_fix", "intermediate_fix"], "altitude": {"kind": "at_or_above", "lower": feet(5000)},
                "rnp_value": length(1, "nm")},
               {"leg_type": "radius_to_fix", "fix": {"ident": "FAF13", "position": final_13}, "arc_center": {"ident": "CTR13", "position": rf_center},
                "arc_radius": length(3, "nm"), "turn_direction": "left", "approach_fix": ["final_approach_fix"],
                "altitude": {"kind": "at", "lower": feet(3200)}, "rnp_value": length(1, "nm")},
               {"leg_type": "track_to_fix", "fix": {"ident": "RW13", "position": deepcopy(ends["13"])}, "approach_fix": ["missed_approach_point"],
                "vertical_angle_deg": -3.0, "rnp_value": length(0.3, "nm")},
               {"leg_type": "course_to_altitude", "course": magnetic(131.1), "altitude": {"kind": "at_or_above", "lower": feet(5000)},
                "missed_approach": True, "rnp_value": length(1, "nm")}]}],
           "navigation_specification": {"navigation_type": "rnp", "specification": "rnp_ar_apch", "rnp_value": length(0.3, "nm"),
                                        "sensors": ["gnss"]},
           "minima": [{"line": "rnp", "label": "RNP 0.30", "manoeuvre": "straight_in", "runway": "13", "rnp_value": length(0.3, "nm"),
                       "height_reference": "threshold",
                       "category_minima": [{"categories": ["A", "B", "C", "D"], "decision_altitude": feet(1920), "height": length(284),
                                            "visibility": {"value": 1200, "unit": "m"}}]}],
           "provenance": {**deepcopy(authored), "derivation": "synthesized", "tool": {"name": "Salti procedure check", "version": "1.2.0"},
                          "generated_at": "2026-09-28T10:00:00Z"}}
    salat = {"ident": "SALAT", "position": offset(NAVAIDS["ojms"]["position"], 43.6, 13.6 * 1852)}
    departure = {"id": "ojms-salat1", "kind": "procedure", "name": "Muwaffaq Salti SALAT 1 departure", "airfield": "ojms",
                 "ident": "SALAT1", "procedure_type": "departure", "runways": ["31"], "top_altitude": feet(6000),
                 "transitions": [{"ident": "RW31", "transition_type": "runway_transition", "legs": [
                     {"leg_type": "course_to_altitude", "course": magnetic(311.1), "altitude": {"kind": "at_or_above", "lower": feet(2200)}},
                     {"leg_type": "course_to_radial", "course": magnetic(60), "turn_direction": "right",
                      "recommended_navaid": {"kind": "control_measure", "id": "ghi"}, "theta": magnetic(0),
                      "altitude": {"kind": "at_or_above", "lower": feet(3000)}},
                     {"leg_type": "direct_to_fix", "fix": {"ident": "GHI", "position": deepcopy(NAVAIDS["ojms"]["position"])},
                      "turn_direction": "right", "altitude": {"kind": "at_or_above", "lower": feet(4000)}},
                     {"leg_type": "track_to_fix", "fix": deepcopy(salat), "altitude": {"kind": "at_or_above", "lower": feet(6000)}}]}],
                 "navigation_specification": {"navigation_type": "rnav", "specification": "rnav_1", "sensors": ["gnss", "dme_dme_iru"]},
                 "climb_gradients": [
                     {"gradient": {"value": 350, "unit": "ft/nm"}, "until": feet(5000), "reason": "obstacle", "runway": "31",
                      "notes": "Terrain rises to 3900 feet 9 nm north-west of the airfield."},
                     {"gradient": {"value": 5.0, "unit": "percent"}, "until_fix": deepcopy(salat), "reason": "atc", "runway": "31",
                      "notes": "Keeps departures below the Marshal stack until SALAT."}],
                 "takeoff_minima": [
                     {"runway": "31", "ceiling": length(500), "visibility": {"value": 1600, "unit": "m"},
                      "climb_gradient": {"gradient": {"value": 350, "unit": "ft/nm"}, "until": feet(5000), "reason": "obstacle"},
                      "condition": "Aircraft with one or two engines.",
                      "remarks": ["Radio mast 0.6 nm from the departure end of runway 31, 120 feet above ground, 1795 feet MSL."]},
                     {"runway": "31", "runway_visual_range": length(550, "m"), "condition": "Aircraft with three or more engines."}],
                 "obstacle_assessment": {
                     "criteria": "terps", "criteria_document": "FAA Order 8260.3G", "assessed_at": "2026-09-28T10:00:00Z",
                     "segments": [{"segment": "departure", "transition": "RW31", "to_fix": "SALAT", "obstacle_clearance": length(1000),
                                   "minimum_altitude": feet(4900), "satisfied": True,
                                   "controlling_obstacle": {"obstacle_type": "terrain", "position": position(31.905, 36.69),
                                                            "elevation": feet(3920)}}]},
                 "provenance": deepcopy(authored)}
    return [par, asr, rnp, departure]


def carrier(version):
    """The carrier in the eastern Mediterranean: the ship unit gives the position."""
    return {"$schema": "urn:openaix:schema:airfield:" + version, "id": "cvn-72", "kind": "carrier", "name": "Abraham Lincoln",
            "use": "military", "carrier": {"hull_number": "CVN-72", "tacan": {"channel": 72, "band": "X", "identifier": "ABE"},
                                              "icls_channel": 12, "case_recovery": {
                "case": "case_iii", "marshal_radial": {"value": 150, "reference": "magnetic"}, "marshal_altitude": feet(6000),
                "marshal_distance": length(21, "nm")},
                                              "link4": {"value": 336.0, "unit": "MHz", "modulation": "AM", "band": "uhf"}, "acls": True,
                                              "recovery_windows": [{
                "window": {"start": "2026-10-02T13:30:00Z", "end": "2026-10-02T14:15:00Z"}, "case": "case_iii",
                "brc": {"value": 330, "reference": "magnetic"}}]},
            "frequencies": [station("tower", 308.475, "Lincoln Tower"), station("marshal", 285.675, "Lincoln Marshal"),
                            station("approach", 264.0, "Lincoln Approach"), station("departure", 254.3, "Lincoln Departure")],
            "extensions": dcs([{"kind": "unit", "name": "OIR Abraham Lincoln", "mission_id": MISSION_ID, "unit_type": "CVN_72"}],
                              coalition="blue")}
