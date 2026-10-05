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
    result = {"id": identifier, "kind": "airfield", "name": name, "ident": ident, "coalition": "blue",
              "position": reference, "elevation": feet(elevation), "magnetic_variation_deg": DECLINATION,
              "transition_altitude": feet(13000), "runways": runways, "frequencies": frequencies,
              "extensions": dcs([{"kind": "airbase", "name": name, "mission_id": MISSION_ID}]), "source": DCS_SOURCE, **extra}
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
                 station("atis", 251.85, "Salti Information"), station("pmsv", 344.6, "Salti Metro"), station("ops", 255.4, "Kingpin")],
                runways, calm_wind_runway="13", controlling_agency="salti-tower",
                atis={"runway_in_use": "13", "transition_level": {"value": 150, "unit": "flight_level", "reference": "FL"},
                      "remarks": ["Tower combines ground, tower and approach on 253.15 and 120.5; BAK-12 cables 1500 feet from both runway 13 and 31 thresholds.",
                                  "Transient fighters park on stands 40 and 41; shelters are at the north-west end."]},
                traffic_pattern={"profile": "usaf-standard", "overhead_altitude": feet(3600), "initial": [{"distance": length(5, "nm")}]},
                localizers=["ojms-ils-31", "ojms-ils-26"], procedures=["ojms-i31"],
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
    return {"id": "farp-sage", "kind": "farp", "name": "Sage FARP", "coalition": "blue", "position": reference,
            "elevation": feet(1150), "pads": [{"name": "Pad 1", "position": offset(reference, 0, 30)},
                                              {"name": "Pad 2", "position": offset(reference, 180, 30)}],
            "frequencies": [station("ops", 41.5, "Sage Ops", "fm", "FM"), station("ops", 285.0, "Sage Ops")],
            "controlling_agency": "banshee", "extensions": dcs([{"kind": "static", "name": "OIR Sage FARP", "mission_id": MISSION_ID}])}


def usaf_standard():
    """Named pattern profile with typical US Air Force values: overhead 500 ft above a rectangular pattern."""
    return {"direction": "left", "altitude": feet(1500, "AGL"), "overhead_altitude": feet(2000, "AGL"), "break_point": "approach_end",
            "initial": [{"distance": length(5, "nm")}],
            "categories": {"trainer": {"altitude": feet(1000, "AGL"), "overhead_altitude": feet(1500, "AGL")},
                           "helicopter": {"altitude": feet(500, "AGL")}}}


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
    procedure = {"id": "ojms-i31", "kind": "procedure", "name": "Muwaffaq Salti ILS runway 31 approach (I31)", "airfield": "ojms",
                 "ident": "I31", "procedure_type": "approach", "transitions": [{"legs": [
                     {"leg_type": "initial_fix", "fix": {"ident": "FAF31", "position": final_fix}, "approach_fix": "final_approach_fix",
                      "altitude": {"kind": "at", "lower": feet(3300)}},
                     {"leg_type": "track_to_fix", "fix": {"ident": "RW31", "position": threshold}, "approach_fix": "missed_approach_point"},
                     {"leg_type": "course_to_altitude", "course": course,
                      "altitude": {"kind": "at_or_above", "lower": feet(5000)}, "missed_approach": True}]}]}
    return localizers, procedure


def carrier(version):
    """The carrier in the eastern Mediterranean: the ship unit gives the position."""
    return {"$schema": "urn:openaix:schema:airfield:" + version, "id": "cvn-72", "kind": "carrier", "name": "Abraham Lincoln",
            "coalition": "blue", "carrier": {"hull_number": "CVN-72", "tacan": {"channel": 72, "band": "X", "identifier": "ABE"},
                                              "icls_channel": 12, "case_recovery": {
                "case": "case_iii", "marshal_radial": {"value": 150, "reference": "magnetic"}, "marshal_altitude": feet(6000),
                "marshal_distance": length(21, "nm")}},
            "frequencies": [station("tower", 308.475, "Lincoln Tower"), station("marshal", 285.675, "Lincoln Marshal"),
                            station("approach", 264.0, "Lincoln Approach"), station("departure", 254.3, "Lincoln Departure")],
            "extensions": dcs([{"kind": "unit", "name": "OIR Abraham Lincoln", "mission_id": MISSION_ID, "unit_type": "CVN_72"}])}
