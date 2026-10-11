"""Navigation record schemas (sim core, NAV-18/NAV-19) and their KDEN examples.

Navigation records share a small root: id, name, optional provenance (`source`), extensions and,
where the binding policy allows, simulator bindings in `extensions.sim`. Shared leg, hold, fix and constraint definitions live
in procedure.schema.json `$defs` and are referenced by URN from holding, MSA and airway.
Descriptions come from describe/tables/navigation.py through describe/resolve.py.
"""
from copy import deepcopy

from openaix.build.points import build_point
from openaix.sim.bindings import sim_overlay


AIRWAY_TYPES = {"ADVRTE": "advisory", "ARWY": "airway", "NAVRTE": "area_navigation", "ATSRTE": "air_traffic_services",
                "CDR": "conditional"}
ROOT_SCHEMAS = ("airfield", "runway", "localizer", "procedure", "holding", "path-point", "msa", "grid-mora")
NAVAID_CLASSES = ("VOR", "VOR_DME", "VORTAC", "TACAN", "DME", "NDB", "ILS_DME")
# Leg types: the 23 path terminators, named in words; sources and definitions in sources/leg-type-definitions.json.
# The two-letter code is in each value's description, not in the data.
LEG_TYPES = ("initial_fix", "track_to_fix", "course_to_fix", "direct_to_fix", "fix_to_altitude",
             "track_from_fix_for_distance", "track_from_fix_to_dme_distance", "fix_to_manual_termination",
             "course_to_altitude", "course_to_dme_distance", "course_to_intercept", "course_to_radial", "radius_to_fix",
             "arc_to_fix", "heading_to_altitude", "heading_to_dme_distance", "heading_to_intercept",
             "heading_to_manual_termination", "heading_to_radial", "procedure_turn", "hold_to_altitude", "hold_to_fix",
             "hold_to_manual_termination")
# Legs that start or end at a published fix; holds carry their fix in `hold`.
FIX_LEGS = ("initial_fix", "track_to_fix", "course_to_fix", "direct_to_fix", "radius_to_fix", "arc_to_fix", "fix_to_altitude",
            "track_from_fix_for_distance", "track_from_fix_to_dme_distance", "fix_to_manual_termination", "procedure_turn")
COURSE_LEGS = ("course_to_altitude", "course_to_dme_distance", "course_to_fix", "course_to_intercept", "course_to_radial",
               "fix_to_altitude", "track_from_fix_for_distance", "track_from_fix_to_dme_distance", "fix_to_manual_termination",
               "heading_to_altitude", "heading_to_dme_distance", "heading_to_intercept", "heading_to_manual_termination",
               "heading_to_radial", "procedure_turn")
ALTITUDE_LEGS = ("course_to_altitude", "fix_to_altitude", "heading_to_altitude")
HOLD_LEGS = ("hold_to_altitude", "hold_to_fix", "hold_to_manual_termination")
# Operating locations that one Airfield record describes. A fixed airfield has runways; a carrier moves and binds
# to its simulator unit; a forward arming and refuelling point (FARP) has landing pads.
AIRFIELD_KINDS = ("airfield", "carrier", "farp")
# Station roles of an airfield frequency: the positions of FAA JO 7110.65 and openAIP airport frequency types,
# military operations and pilot-to-metro service, and the carrier marshal of CV NATOPS.
FREQUENCY_ROLES = ("tower", "ground", "clearance_delivery", "approach", "departure", "atis", "ops", "pmsv", "unicom", "marshal")
# Aircraft categories for traffic pattern defaults; each category has its own pattern altitudes.
PATTERN_CATEGORIES = ("fighter", "trainer", "heavy", "helicopter")
BREAK_POINTS = ("approach_end", "midfield", "departure_end")
ILS_CATEGORIES = ("I", "II", "III")
# FAA approach lighting systems (Aeronautical Information Manual 2-1-1).
APPROACH_LIGHTING = ("ALSF_1", "ALSF_2", "MALSR", "MALSF", "MALS", "SSALR", "SSALF", "SSALS", "ODALS")
SLOPE_INDICATORS = ("PAPI", "VASI")
ARRESTING_GEAR = ("BAK_12", "BAK_13", "BAK_14", "BAK_15", "MA_1A", "E_5", "E_28")
RECOVERY_CASES = ("case_i", "case_ii", "case_iii")
# Parking and taxi graph. A stand category is the largest aircraft class that the stand takes; simulator
# parking types (for example the DCS terminal types) separate shelters, fighter, medium and large stands and helicopter spots in the same way.
STAND_CATEGORIES = ("fighter", "medium", "heavy", "helicopter")
TAXI_NODE_KINDS = ("hold_short", "runway_connection", "runway", "intersection", "parking")
RUNWAY_PAIR = r"^(0[1-9]|[12][0-9]|3[0-6])[LRCWSGU]?/(0[1-9]|[12][0-9]|3[0-6])[LRCWSGU]?$"
# Approach types by the guidance of the final approach segment (FAA AIM 5-4-5, ICAO Doc 8168 Volume II).
APPROACH_TYPES = ("ils", "localizer", "gls", "rnav", "vor", "tacan", "ndb", "par", "asr")
RADAR_APPROACHES = ("par", "asr")
# Minima lines of an approach chart, by the guidance that each line uses (FAA Order 8260.3G, ICAO Doc 8168).
MINIMA_LINES = ("ils", "gls", "par", "lpv", "lnav_vnav", "rnp", "lp", "lnav", "localizer", "vor", "tacan", "ndb", "asr")
# Lines with vertical guidance: their straight-in minima are a decision altitude; the others are a minimum descent altitude.
DECISION_LINES = ("ils", "gls", "par", "lpv", "lnav_vnav", "rnp")
MANOEUVRES = ("straight_in", "circling", "sidestep")
HEIGHT_REFERENCES = ("touchdown_zone", "threshold", "aerodrome")
# Aircraft approach categories A to E by threshold speed (ICAO Doc 8168 Volume I, FAA Order 8260.3G); H for helicopters.
APPROACH_CATEGORIES = ("A", "B", "C", "D", "E", "H")
VISIBILITY_UNITS = ("m", "km", "sm")
# Navigation specifications of the ICAO Performance-based Navigation (PBN) Manual, Doc 9613.
NAVIGATION_TYPES = ("conventional", "rnav", "rnp")
RNAV_SPECIFICATIONS = ("rnav_10", "rnav_5", "rnav_2", "rnav_1")
RNP_SPECIFICATIONS = ("rnp_4", "rnp_2", "rnp_1", "advanced_rnp", "rnp_apch", "rnp_ar_apch", "rnp_0_3")
SENSORS = ("gnss", "gbas", "dme_dme", "dme_dme_iru", "vor_dme", "vor", "dme", "tacan", "ndb", "ils")
CLIMB_GRADIENT_REASONS = ("obstacle", "atc")
GRADIENT_UNITS = ("ft/nm", "percent")
PROCEDURE_TURN_TYPES = ("turn_45_180", "turn_80_260", "base_turn")
# Procedure segments that an obstacle clearance assessment covers (ICAO Doc 8168 Volume II, FAA Order 8260.3G).
ASSESSED_SEGMENTS = ("departure", "arrival", "feeder", "initial", "intermediate", "final", "missed_approach", "circling", "holding")
OBSTACLE_TYPES = ("terrain", "structure", "vegetation")
ASSESSMENT_CRITERIA = ("pans_ops", "terps", "other")
DERIVATIONS = ("published", "derived", "synthesized", "authored")
AIRAC_CYCLE = r"^[0-9]{2}(0[1-9]|1[0-4])$"


def schemas(base, version, dialect, common):
    """All navigation schemas, keyed by artifact name (root schemas) or model name (navaid, airway)."""
    def ref(name, catalogue=None):
        node = {"$ref": common + "#/$defs/" + name}
        if catalogue:
            node["x-catalog"] = catalogue
        return node

    def text():
        return {"type": "string", "minLength": 1}

    def obj(properties, required=(), **extra):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required), **extra}

    def array(items, minimum=0):
        return {"type": "array", "items": items, "minItems": minimum}

    def when(field, values, then, otherwise=None):
        condition = {"if": {"properties": {field: {"enum": list(values)}}, "required": [field]}, "then": then}
        if otherwise:
            condition["else"] = otherwise
        return condition

    def unit(name, value):
        return {"allOf": [ref(name), {"properties": {"unit": {"const": value}}}]}

    procedure_id = base + "procedure:" + version

    def shared(name):
        return {"$ref": procedure_id + "#/$defs/" + name}

    def root(properties, required, kind=None, measure=None, catalogue=False):
        fields = {"$schema": text(), "id": ref("Identifier"), "name": text(), "source": text(), "provenance": shared("Provenance")}
        if kind:
            fields["kind"] = {"const": kind}
        if measure:
            fields["type"] = {"const": measure}
        if catalogue:
            fields["resources_ref"] = ref("ResourceRef")
        fields.update(properties)
        fields["extensions"] = ref("Extensions")
        return obj(fields, ["id", *(["kind"] if kind else []), *(["type"] if measure else []), "name", *required])

    def schema(name, body, identifier=None):
        title = {"msa": "Minimum Safe Altitude (MSA)", "grid-mora": "Grid Minimum Off-Route Altitude (MORA)",
                 "navaid": "Navigation aid", "path-point": "Path point"}.get(name, name.capitalize())
        # x-navigation-profile only groups these schemas under "Navigation & facilities" in the viewer.
        return {"$schema": dialect, "$id": base + (identifier or name) + ":" + version, "title": title,
                "x-navigation-profile": name, **body}

    fix = obj({"ident": text(), "position": ref("GeoPoint")}, ("ident", "position"))

    def altitude_constraint():
        # Inline (not $defs): review examples would build an invalid `between` variant from a single-limit seed.
        node = obj({"kind": {"enum": ["at", "at_or_above", "at_or_below", "between"]}, "lower": ref("Altitude"), "upper": ref("Altitude")},
            ("kind",), allOf=[
                when("kind", ["between"], {"required": ["lower", "upper"]}),
                when("kind", ["at", "at_or_above"], {"required": ["lower"], "not": {"required": ["upper"]}}),
                when("kind", ["at_or_below"], {"required": ["upper"], "not": {"required": ["lower"]}})])
        return node

    def msl():
        return {"allOf": [ref("Altitude"), {"properties": {"reference": {"const": "MSL"}}}]}

    def rnp():
        return unit("Length", "nm")

    def rvr():
        return {"allOf": [ref("Length"), {"properties": {"unit": {"enum": ["ft", "m"]}}}]}

    definitions = {
        "Fix": {"oneOf": [fix, ref("ControlMeasureSelection") | {"x-measure-kinds": ["POINT", "NAVAID"]}]},
        "NavaidRef": {"oneOf": [deepcopy(fix), ref("ControlMeasureSelection") | {"x-measure-kinds": ["NAVAID"]}]},
        "SpeedConstraint": obj({"kind": {"enum": ["at", "at_or_below", "at_or_above"]}, "value": ref("Speed")}, ("kind", "value")),
        "Duration": obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"const": "min"}}, ("value", "unit")),
        "Hold": obj({"fix": {"$ref": "#/$defs/Fix"}, "inbound_course": ref("Bearing"), "turn_direction": {"enum": ["left", "right"]},
                     "leg_length": ref("Length"), "leg_time": {"$ref": "#/$defs/Duration"},
                     "altitude": altitude_constraint(), "speed": {"$ref": "#/$defs/SpeedConstraint"}},
                    ("fix", "inbound_course", "turn_direction"),
                    anyOf=[{"required": ["leg_length"]}, {"required": ["leg_time"]}],
                    allOf=[{"if": {"required": ["leg_length"]}, "then": {"not": {"required": ["leg_time"]}}}]),
        "Leg": obj({"leg_type": {"enum": list(LEG_TYPES)}, "fix": {"$ref": "#/$defs/Fix"},
                    "recommended_navaid": {"$ref": "#/$defs/NavaidRef"}, "turn_direction": {"enum": ["left", "right", "either"]},
                    "course": ref("Bearing"), "distance": ref("Length"), "time": {"$ref": "#/$defs/Duration"},
                    "altitude": altitude_constraint(), "speed": {"$ref": "#/$defs/SpeedConstraint"},
                    "vertical_angle_deg": {"type": "number", "minimum": -90, "maximum": 90},
                    "arc_center": {"$ref": "#/$defs/Fix"}, "arc_radius": ref("Length"), "hold": {"$ref": "#/$defs/Hold"},
                    "fly_over": {"type": "boolean"},
                    "approach_fix": {"enum": ["initial_approach_fix", "intermediate_fix", "final_approach_course_fix", "final_approach_fix", "missed_approach_point"]},
                    "missed_approach": {"type": "boolean"}, "rnp_value": rnp(),
                    "procedure_turn": {"$ref": "#/$defs/ProcedureTurn"}},
                   ("leg_type",), allOf=[
                       when("leg_type", FIX_LEGS, {"required": ["fix"]}),
                       when("leg_type", COURSE_LEGS, {"required": ["course"]}),
                       when("leg_type", ALTITUDE_LEGS, {"required": ["altitude"]}),
                       when("leg_type", ["radius_to_fix"], {"required": ["arc_center", "arc_radius"]}),
                       when("leg_type", HOLD_LEGS, {"required": ["hold"]}, {"not": {"required": ["hold"]}}),
                       when("leg_type", [leg for leg in LEG_TYPES if leg != "procedure_turn"], {"not": {"required": ["procedure_turn"]}})]),
        "Transition": obj({"ident": text(), "legs": array({"$ref": "#/$defs/Leg"}, 1)}, ("legs",)),
        "ProcedureTurn": obj({"turn_type": {"enum": list(PROCEDURE_TURN_TYPES)}, "remain_within": ref("Length"),
                              "outbound_time": {"$ref": "#/$defs/Duration"}, "inbound_course": ref("Bearing")}, ("turn_type",)),
        "Visibility": obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"enum": list(VISIBILITY_UNITS)}}, ("value", "unit")),
        "Gradient": obj({"value": {"type": "number", "exclusiveMinimum": 0}, "unit": {"enum": list(GRADIENT_UNITS)}}, ("value", "unit")),
        "MinimaLine": obj({"line": {"enum": list(MINIMA_LINES)}, "label": text(), "manoeuvre": {"enum": list(MANOEUVRES)},
                           "runway": ref("RunwayDesignator"), "ils_category": {"enum": list(ILS_CATEGORIES)}, "rnp_value": rnp(),
                           "height_reference": {"enum": list(HEIGHT_REFERENCES)}, "condition": text(),
                           "category_minima": array({"$ref": "#/$defs/CategoryMinimum"}, 1), "remarks": array(text(), 1)},
                          ("line", "manoeuvre", "category_minima"), allOf=[
                              when("manoeuvre", ["circling"],
                                   {"not": {"required": ["runway"]},
                                    "properties": {"height_reference": {"const": "aerodrome"},
                                                   "category_minima": {"items": {"not": {"required": ["decision_altitude"]}}}}},
                                   {"required": ["runway"]}),
                              when("line", [line for line in MINIMA_LINES if line not in DECISION_LINES],
                                   {"properties": {"category_minima": {"items": {"not": {"required": ["decision_altitude"]}}}}}),
                              {"if": {"properties": {"line": {"enum": list(DECISION_LINES)}, "manoeuvre": {"const": "straight_in"}},
                                      "required": ["line", "manoeuvre"]},
                               "then": {"properties": {"category_minima": {"items": {"not": {"required": ["minimum_descent_altitude"]}}}}}},
                              when("line", [line for line in MINIMA_LINES if line not in ("ils", "gls")], {"not": {"required": ["ils_category"]}}),
                              when("line", [line for line in MINIMA_LINES if line != "rnp"], {"not": {"required": ["rnp_value"]}})]),
        "CategoryMinimum": obj({"categories": {**array({"enum": list(APPROACH_CATEGORIES)}, 1), "uniqueItems": True},
                                "decision_altitude": msl(), "minimum_descent_altitude": msl(), "height": ref("Length"),
                                "visibility": {"$ref": "#/$defs/Visibility"}, "runway_visual_range": rvr()},
                               ("categories",), oneOf=[{"required": ["decision_altitude"]}, {"required": ["minimum_descent_altitude"]}]),
        "NavigationSpecification": obj({"navigation_type": {"enum": list(NAVIGATION_TYPES)},
                                        "specification": {"enum": list(RNAV_SPECIFICATIONS + RNP_SPECIFICATIONS)}, "rnp_value": rnp(),
                                        "sensors": {**array({"enum": list(SENSORS)}, 1), "uniqueItems": True},
                                        "required_navaids": array({"$ref": "#/$defs/NavaidRef"}, 1), "notes": text()},
                                       ("navigation_type",), allOf=[
                                           when("navigation_type", ["conventional"],
                                                {"not": {"anyOf": [{"required": ["specification"]}, {"required": ["rnp_value"]}]}}),
                                           when("navigation_type", ["rnav"], {"required": ["specification"],
                                                                              "properties": {"specification": {"enum": list(RNAV_SPECIFICATIONS)}},
                                                                              "not": {"required": ["rnp_value"]}}),
                                           when("navigation_type", ["rnp"], {"required": ["specification"],
                                                                             "properties": {"specification": {"enum": list(RNP_SPECIFICATIONS)}}})]),
        "RadarApproach": obj({"runway": ref("RunwayDesignator"), "final_approach_course": ref("Bearing"),
                              "glide_path_angle_deg": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 90},
                              "threshold_crossing_height": ref("Length"), "position": ref("GeoPoint"),
                              "coverage": {"$ref": "#/$defs/RadarCoverage"},
                              "recommended_altitudes": array({"$ref": "#/$defs/RecommendedAltitude"}, 1),
                              "missed_approach_point_distance": ref("Length"), "lost_communications": array(text(), 1)},
                             ("runway", "final_approach_course")),
        "RadarCoverage": obj({"range": ref("Length"), "azimuth_left_deg": {"type": "number", "minimum": 0, "maximum": 90},
                              "azimuth_right_deg": {"type": "number", "minimum": 0, "maximum": 90},
                              "elevation_lower_deg": {"type": "number", "minimum": -10, "maximum": 90},
                              "elevation_upper_deg": {"type": "number", "exclusiveMinimum": 0, "maximum": 90}}, ("range",)),
        "RecommendedAltitude": obj({"distance": ref("Length"), "altitude": msl()}, ("distance", "altitude")),
        "ClimbGradient": obj({"gradient": {"$ref": "#/$defs/Gradient"}, "until": msl(), "until_fix": {"$ref": "#/$defs/Fix"},
                              "reason": {"enum": list(CLIMB_GRADIENT_REASONS)}, "runway": ref("RunwayDesignator"), "notes": text()},
                             ("gradient", "reason"), anyOf=[{"required": ["until"]}, {"required": ["until_fix"]}]),
        "TakeoffMinimum": obj({"runway": ref("RunwayDesignator"), "ceiling": ref("Length"), "visibility": {"$ref": "#/$defs/Visibility"},
                               "runway_visual_range": rvr(), "climb_gradient": {"$ref": "#/$defs/ClimbGradient"}, "condition": text(),
                               "remarks": array(text(), 1)},
                              (), anyOf=[{"required": ["visibility"]}, {"required": ["runway_visual_range"]}]),
        "ObstacleAssessment": obj({"criteria": {"enum": list(ASSESSMENT_CRITERIA)}, "criteria_document": text(), "obstacle_data": text(),
                                   "assessed_at": ref("DateTime"), "tool": {"$ref": "#/$defs/Tool"},
                                   "segments": array({"$ref": "#/$defs/SegmentAssessment"}, 1), "notes": text()},
                                  ("criteria", "segments")),
        "SegmentAssessment": obj({"segment": {"enum": list(ASSESSED_SEGMENTS)}, "transition": text(), "from_fix": text(), "to_fix": text(),
                                  "controlling_obstacle": {"$ref": "#/$defs/Obstacle"}, "obstacle_clearance": ref("Length"),
                                  "minimum_altitude": msl(), "satisfied": {"type": "boolean"}, "notes": text()},
                                 ("segment", "obstacle_clearance", "minimum_altitude")),
        "Obstacle": obj({"ident": text(), "obstacle_type": {"enum": list(OBSTACLE_TYPES)}, "position": ref("GeoPoint"),
                         "elevation": ref("Elevation"), "height": ref("Length")}, ("obstacle_type", "elevation")),
        "Tool": obj({"name": text(), "version": text()}, ("name",)),
        "Provenance": obj({"derivation": {"enum": list(DERIVATIONS)}, "authority": text(),
                           "airac_cycle": {"type": "string", "pattern": AIRAC_CYCLE}, "effective_from": ref("DateTime"),
                           "effective_until": ref("DateTime"), "publication": ref("DocumentRef"), "tool": {"$ref": "#/$defs/Tool"},
                           "generated_at": ref("DateTime")}, ("derivation",)),
    }
    navigation = {}
    airfield_id = base + "airfield:" + version

    def airfield_def(name):
        return {"$ref": airfield_id + "#/$defs/" + name}

    def airfield_ref():
        return ref("Identifier", "places")

    def pattern_altitude():
        return {"allOf": [ref("Altitude"), {"properties": {"reference": {"enum": ["MSL", "AGL"]}}}]}

    end = obj({"designator": ref("RunwayDesignator"), "threshold": ref("GeoPoint"), "threshold_elevation": ref("Elevation"),
               "displaced_threshold": ref("Length"), "heading": ref("Bearing"), "threshold_crossing_height": ref("Length"),
               "localizer": ref("Identifier", "localizers"), "lighting": {"$ref": "#/$defs/Lighting"},
               "arresting_gear": array({"$ref": "#/$defs/ArrestingGear"}), "traffic_pattern": airfield_def("TrafficPattern")},
              ("designator", "threshold", "heading"))
    runway = root({"airfield": airfield_ref(), "designator": {"type": "string", "pattern": RUNWAY_PAIR},
                   "length": ref("Length"), "width": ref("Length"), "surface": {"enum": ["hard", "soft", "water"]},
                   "ends": {**array({"$ref": "#/$defs/RunwayEnd"}, 2), "maxItems": 2}},
                  ("designator", "length", "ends"), kind="runway", catalogue=True)
    navigation["runway"] = schema("runway", {**runway, "$defs": {
        "RunwayEnd": end,
        "Lighting": obj({"approach_lighting": {"enum": list(APPROACH_LIGHTING)}, "edge_lights": {"type": "boolean"},
                         "reil": {"type": "boolean"}, "slope_indicator": {"enum": list(SLOPE_INDICATORS)}}),
        "ArrestingGear": obj({"type": {"enum": list(ARRESTING_GEAR)}, "distance_from_threshold": ref("Length")},
                             ("type", "distance_from_threshold")),
    }})

    pattern_fields = {"direction": {"enum": ["left", "right"]}, "altitude": pattern_altitude(),
                      "overhead_altitude": pattern_altitude(), "break_point": {"enum": list(BREAK_POINTS)},
                      "initial": array({"$ref": "#/$defs/InitialPoint"})}
    pattern_set = obj(deepcopy(pattern_fields))
    traffic_pattern = obj({"profile": ref("Identifier", "pattern_profiles"), **deepcopy(pattern_fields),
                           "categories": obj({category: {"$ref": "#/$defs/PatternSet"} for category in PATTERN_CATEGORIES})})
    initial_point = {"oneOf": [
        obj({"point": ref("ControlMeasureSelection") | {"x-measure-kinds": ["POINT"], "x-point-roles": ["initial"]}}, ("point",)),
        obj({"distance": ref("Length"), "bearing": ref("Bearing")}, ("distance",)),
    ]}
    station_frequency = obj({"role": {"enum": list(FREQUENCY_ROLES)},
                             "frequency": {"allOf": [ref("Frequency"), {"properties": {"unit": {"const": "MHz"}}, "required": ["modulation"]}]},
                             "callsign": text(), "hours": ref("WeeklySchedule"), "notes": text()}, ("role", "frequency"))
    atis = obj({"runway_in_use": ref("RunwayDesignator"),
                "transition_level": {"allOf": [ref("Altitude"), {"properties": {"reference": {"const": "FL"}}}]},
                "remarks": array(text())})
    carrier = obj({"hull_number": text(), "tacan": ref("TACAN"), "icls_channel": {"type": "integer", "minimum": 1, "maximum": 20},
                   "case_recovery": {"$ref": "#/$defs/CaseRecovery"}}, ("hull_number",))
    case_recovery = obj({"case": {"enum": list(RECOVERY_CASES)}, "marshal_radial": ref("Bearing"),
                         "marshal_altitude": {"allOf": [ref("Altitude"), {"properties": {"reference": {"const": "MSL"}}}]},
                         "marshal_distance": ref("Length")}, ("case",))
    pad = obj({"name": text(), "position": ref("GeoPoint")}, ("position",))
    stand = obj({"id": ref("Identifier"), "name": text(), "position": ref("GeoPoint"), "heading": ref("Bearing"),
                 "category": {"enum": list(STAND_CATEGORIES)}, "helicopters": {"type": "boolean"}, "width": ref("Length"),
                 "length": ref("Length"), "shelter": {"type": "boolean"}, "ramp": text(), },
                ("id", "position"))
    taxi_node = obj({"id": ref("Identifier"), "position": ref("GeoPoint"), "kind": {"enum": list(TAXI_NODE_KINDS)},
                     "name": text(), "runway_end": ref("RunwayDesignator"), "stand": ref("Identifier")}, ("id", "position"),
                    allOf=[when("kind", ["hold_short", "runway_connection"], {"required": ["runway_end"]}),
                           when("kind", ["parking"], {"required": ["stand"]})])
    taxi_edge = obj({"from": ref("Identifier"), "to": ref("Identifier"), "taxiway": text(), "one_way": {"type": "boolean"},
                     "width": ref("Length"), "category": {"enum": list(STAND_CATEGORIES)}}, ("from", "to"))
    taxi = obj({"nodes": array({"$ref": "#/$defs/TaxiNode"}, 2), "edges": array({"$ref": "#/$defs/TaxiEdge"}, 1)}, ("nodes", "edges"))

    airfield = root(
        {"ident": text(), "coalition": ref("Coalition"), "operating_hours": ref("WeeklySchedule"),
         "position": ref("GeoPoint"), "elevation": ref("Elevation"), "magnetic_variation_deg": {"type": "number", "minimum": -180, "maximum": 180},
         "transition_altitude": ref("Altitude"), "runways": array({"$ref": base + "runway:" + version}), "calm_wind_runway": ref("RunwayDesignator"),
         "pads": array({"$ref": "#/$defs/Pad"}, 1), "parking": array({"$ref": "#/$defs/Stand"}, 1), "taxi": {"$ref": "#/$defs/TaxiGraph"}, "frequencies": array({"$ref": "#/$defs/StationFrequency"}, 1), "atis": {"$ref": "#/$defs/Atis"},
         "navaids": array(ref("ControlMeasureSelection") | {"x-measure-kinds": ["NAVAID"]}, 1),
         "localizers": array(ref("Identifier"), 1) | {"x-catalog": "localizers"},
         "procedures": array(ref("Identifier"), 1) | {"x-catalog": "instrument_procedures"},
         "traffic_pattern": {"$ref": "#/$defs/TrafficPattern"}, "carrier": {"$ref": "#/$defs/Carrier"},
         "controlling_agency": ref("Identifier", "agencies"), "approach_instructions": array(text())},
        (), catalogue=True)
    airfield["properties"]["kind"] = {"enum": list(AIRFIELD_KINDS)}
    airfield["required"].insert(1, "kind")
    airfield["allOf"] = [
        when("kind", ["airfield"], {"required": ["position", "elevation", "runways"],
                                    "properties": {"runways": {"minItems": 1}, "extensions": sim_overlay("fixed_airfield")},
                                    "not": {"anyOf": [{"required": ["carrier"]}]}}),
        when("kind", ["farp"], {"required": ["position", "elevation"], "properties": {"extensions": sim_overlay("farp")},
                                "not": {"anyOf": [{"required": ["carrier"]}, {"required": ["runways"]}]}}),
        when("kind", ["carrier"], {"required": ["carrier"], "properties": {"extensions": sim_overlay("carrier")},
                                   "not": {"anyOf": [{"required": ["runways"]}, {"required": ["pads"]}, {"required": ["calm_wind_runway"]}]}}),
    ]
    navigation["airfield"] = schema("airfield", {**airfield, "$defs": {
        "StationFrequency": station_frequency, "Atis": atis, "Carrier": carrier, "CaseRecovery": case_recovery, "Pad": pad,
        "Stand": stand, "TaxiGraph": taxi, "TaxiNode": taxi_node, "TaxiEdge": taxi_edge,
        "TrafficPattern": traffic_pattern, "PatternSet": pattern_set, "InitialPoint": initial_point}})
    navigation["localizer"] = schema("localizer", {**root(
        {"airfield": airfield_ref(), "ident": text(), "runway": ref("RunwayDesignator"), "ils_category": {"enum": list(ILS_CATEGORIES)},
         "frequency": unit("Frequency", "MHz"), "course": ref("Bearing"),
         "position": ref("GeoPoint"), "glide_slope": {"$ref": "#/$defs/GlideSlope"}, "threshold_crossing_height": ref("Length")},
        ("frequency", "course", "position"), kind="localizer", catalogue=True),
        "$defs": {"GlideSlope": obj({"angle_deg": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 90}, "position": ref("GeoPoint"),
                                     "elevation": ref("Elevation")}, ("angle_deg", "position"))}})
    procedure = root(
        {"airfield": airfield_ref(), "ident": text(), "procedure_type": {"enum": ["departure", "arrival", "approach"]},
         "approach_type": {"enum": list(APPROACH_TYPES)},
         "transitions": array({"$ref": "#/$defs/Transition"}, 1),
         "navigation_specification": {"$ref": "#/$defs/NavigationSpecification"},
         "minima": array({"$ref": "#/$defs/MinimaLine"}, 1), "radar_approach": {"$ref": "#/$defs/RadarApproach"},
         "climb_gradients": array({"$ref": "#/$defs/ClimbGradient"}, 1), "takeoff_minima": array({"$ref": "#/$defs/TakeoffMinimum"}, 1),
         "obstacle_assessment": {"$ref": "#/$defs/ObstacleAssessment"}}, (), kind="procedure", catalogue=True)
    procedure["properties"]["provenance"] = {"$ref": "#/$defs/Provenance"}

    def excluded(*fields):
        return {"not": {"anyOf": [{"required": [field]} for field in fields]}}

    procedure["allOf"] = [
        when("procedure_type", ["departure", "arrival"], excluded("approach_type", "minima", "radar_approach")),
        when("procedure_type", ["arrival", "approach"], excluded("takeoff_minima")),
        when("procedure_type", ["arrival"], excluded("climb_gradients")),
        # A radar approach can have no coded legs: the controller gives the final approach from the radar.
        when("approach_type", RADAR_APPROACHES, {"required": ["radar_approach"]}, {**excluded("radar_approach"), "required": ["transitions"]}),
        when("approach_type", ["par"], {"properties": {"radar_approach": {
            "required": ["glide_path_angle_deg"], **excluded("recommended_altitudes", "missed_approach_point_distance")}}}),
        when("approach_type", ["asr"], {"properties": {"radar_approach": {
            **excluded("glide_path_angle_deg", "threshold_crossing_height"),
            "properties": {"coverage": excluded("elevation_lower_deg", "elevation_upper_deg")}}}}),
    ]
    navigation["procedure"] = schema("procedure", {**procedure, "$defs": definitions})
    navigation["holding"] = schema("holding", root({"hold": shared("Hold")}, ("hold",), kind="holding", catalogue=True))
    navigation["path-point"] = schema("path-point", root(
        {"airfield": airfield_ref(), "approach": text(), "runway": ref("RunwayDesignator"), "approach_type": text(),
         "landing_threshold_point": ref("GeoPoint"), "landing_threshold_elevation": ref("Elevation"),
         "flight_path_alignment_point": ref("GeoPoint"), "glide_path_angle_deg": {"type": "number", "exclusiveMinimum": 0, "exclusiveMaximum": 90},
         "threshold_crossing_height": ref("Length"), "course_width_at_threshold": ref("Length"), "final_approach_course": ref("Bearing")},
        ("landing_threshold_point", "flight_path_alignment_point", "glide_path_angle_deg", "threshold_crossing_height"), kind="path-point",
        catalogue=True))
    msa_altitude = {"allOf": [ref("Altitude"), {"properties": {"reference": {"const": "MSL"}}}]}
    navigation["msa"] = schema("msa", {**root(
        {"airfield": airfield_ref(), "center": shared("Fix"), "sectors": array({"$ref": "#/$defs/Sector"}, 1)},
        ("center", "sectors"), kind="msa", catalogue=True),
        "$defs": {"Sector": obj({"start_bearing": ref("Bearing"), "end_bearing": ref("Bearing"), "full_circle": {"type": "boolean"},
                                 "radius": ref("Length"), "minimum_altitude": deepcopy(msa_altitude)},
                                ("start_bearing", "end_bearing", "full_circle", "radius", "minimum_altitude"))}})
    cell = obj({"southwest": ref("GeoPoint"), "northeast": ref("GeoPoint"), "status": {"enum": ["known", "unknown"]},
                "minimum_altitude": deepcopy(msa_altitude)}, ("southwest", "northeast", "status"),
               allOf=[{"if": {"properties": {"status": {"const": "known"}}, "required": ["status"]},
                       "then": {"required": ["minimum_altitude"]}, "else": {"not": {"required": ["minimum_altitude"]}}}])
    navigation["grid-mora"] = schema("grid-mora", {**root({"cells": array({"$ref": "#/$defs/Cell"}, 1)}, ("cells",), kind="grid-mora"),
                                                    "$defs": {"Cell": cell}})
    vhf = {"properties": {"frequency": {"properties": {"unit": {"const": "MHz"}}}}}
    navaid = root({"airfield": airfield_ref(), "ident": text(), "class": {"enum": list(NAVAID_CLASSES)}, "position": ref("GeoPoint"), "dme_position": ref("GeoPoint"),
                   "elevation": ref("Elevation"), "frequency": ref("Frequency"), "tacan": ref("TACAN"),
                   "magnetic_variation_deg": {"type": "number", "minimum": -180, "maximum": 180}},
                  ("class",), measure="NAVAID", catalogue=True)
    navaid["anyOf"] = [{"required": ["position"]}, {"required": ["dme_position"]}]
    navaid["allOf"] = [
        when("class", ["TACAN", "VORTAC"], {"required": ["tacan"]}),
        when("class", ["TACAN"], {"not": {"required": ["frequency"]}}, {"required": ["frequency"]}),
        when("class", ["NDB"], {"properties": {"frequency": {"properties": {"unit": {"const": "kHz"}}}}}, vhf),
    ]
    navigation["navaid"] = schema("navaid", navaid)
    segment = obj({"fix": shared("Fix"), "inbound_course": ref("Bearing"), "outbound_course": ref("Bearing"), "distance": ref("Length"),
                   "minimum_altitude": ref("Altitude"), "maximum_altitude": ref("Altitude"),
                   "directional_restriction": {"enum": ["forward", "backward"]}}, ("fix",))
    # Inline, not $defs: measure bodies are copied into the common ControlMeasure union.
    navigation["airway"] = schema("airway", root(
        {"ident": text(), "airway_type": {"enum": list(dict.fromkeys(AIRWAY_TYPES.values()))}, "level": {"enum": ["low", "high", "both"]},
         "segments": array(segment, 2)}, ("airway_type", "segments"), measure="AIRWAY", catalogue=True))
    return navigation


def point_model(spatial, base, version, common):
    """Seam: the measures area owns Point. This keeps today's Point (measure root plus point roles)
    without building it from a source fix profile; replace it with the measures builder."""
    shared = {key: deepcopy(value) for key, value in spatial["airspace"]["properties"].items()
              if key in {"$schema", "id", "name", "description", "active", "channels", "restrictions", "coordination_instructions", "notes", "resources_ref", "extensions"}}
    skeleton = {"$schema": spatial["airspace"]["$schema"], "type": "object", "additionalProperties": False,
                "properties": {**shared, "reference_agency": {"$ref": common + "#/$defs/Identifier", "x-catalog": "agencies"},
                               "instructions": {"type": "array", "items": {"type": "string", "minLength": 1}}},
                "required": ["id", "name"]}
    return build_point(skeleton, base, version, common)


def airspace_model(spatial):
    """Seam: the measures area owns Airspace; navigation merges no source record bookkeeping into it."""
    return deepcopy(spatial["airspace"])


def airspace_example(model):
    """Seam: synthetic Class B demonstration kept at examples/airspace.json for the measures area."""
    from openaix.build.spatial import EXAMPLE_WINDOW, class_b_components
    return {"$schema": model["$id"], "id": "airspace-demo", "name": "Demonstration Airspace", "type": "AIRSPACE",
            "airspace_type": "ClassB", "airspace_class_code": "B", "components": class_b_components(),
            "active": deepcopy(EXAMPLE_WINDOW)}


def build_navigation(kden, spatial, base, version, common):
    """Navigation schemas, the navaid/airway/point/airspace models and the KDEN examples."""
    navigation = schemas(base, version, spatial["airspace"]["$schema"], common)
    artifacts = {"schemas/" + name + ".schema.json": navigation[name] for name in ROOT_SCHEMAS}
    models = {"navaid": navigation["navaid"], "airway": navigation["airway"],
              "point": point_model(spatial, base, version, common), "airspace": airspace_model(spatial)}
    identifiers = {name: value["$id"] for name, value in navigation.items()}
    identifiers.update(point=models["point"]["$id"], airspace=models["airspace"]["$id"])
    for name, document in kden.items():
        target = "point" if name == "fix" else name
        example = {"$schema": identifiers[target], **deepcopy(document)}
        if name == "fix" and "active" in models["point"]["required"]:
            example["active"] = {"continuous": True}
        artifacts["examples/" + name + ".json"] = example
    artifacts["examples/airspace.json"] = airspace_example(models["airspace"])
    from openaix.examples.kden import kden_catalogue
    artifacts["examples/resources-kden.json"] = kden_catalogue(kden, version)
    return artifacts, models
