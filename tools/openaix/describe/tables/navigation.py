"""Navigation records. Keys follow describe/resolve.py; every value is a describe/templates.py template.

Leg types are the 23 path terminators, named in words. Their sources, published wording and openAIX
definitions are in sources/leg-type-definitions.json: PANS-OPS (Doc 8168, Volume II, Part III, Section 2,
Chapter 5) for twelve, the FAA Instrument Procedures Handbook (FAA-H-8083-16B, Chapter 6) and FAA Order
8260.3G for the other eleven. Other terms follow FAA CIFP and FAA AIM 5-4. MSA sector bearings are bearings
to the centre, swept clockwise.

"Shall" appears only where the schema or a validator rejects a violation (d.enforced); facts use the
present tense.
"""
import json

from openaix import ROOT
from openaix.describe import templates as d


LEG_TYPE_SOURCE = json.loads((ROOT / "sources/leg-type-definitions.json").read_text())
MEASURE_CODES = json.loads((ROOT / "sources/measure-definitions.json").read_text())["codes"]
# Airway types with a catalogue code: the enumerated value uses the definition of that code.
AIRWAY_TYPE_CODES = {"advisory": "ADVRTE", "airway": "ARWY", "area_navigation": "NAVRTE", "air_traffic_services": "ATSRTE",
                     "conditional": "CDR"}


SUBJECTS = {
    "airfield": "airfield",
    "runway": "runway",
    "localizer": "localizer",
    "procedure": "procedure",
    "holding": "record of a hold",
    "path-point": "path point",
    "msa": "record of a minimum safe altitude",
    "grid-mora": "record of a grid of minimum off-route altitudes",
    "measures/navaid": "navigation aid",
    "measures/airway": "airway",
}

SOURCE_NOTES = ("The value gives the authority that publishes the data, and the cycle, for example `FAA CIFP cycle 2610`",
                "A record that an author writes does not have this field")


def _record(schema, subject, kind=True, resources=True):
    """Root fields that each navigation record has, written for one schema."""
    entries = {
        (schema, "$schema"): d.reference("schema", "validates this document"),
        (schema, "id"): d.identifier(subject, None, "Other resources and orders use this stable identifier to refer to this " + subject),
        (schema, "name"): d.name(subject),
        (schema, "source"): d.source("record", *SOURCE_NOTES),
        (schema, "extensions"): d.extension(),
    }
    if kind:
        record = ("a " + subject) if subject.startswith("record of") else ("a " + subject + " record")
        entries[(schema, "kind")] = d.discriminator(record, "The value selects this navigation contract")
    if resources:
        entries[(schema, "resources_ref")] = d.reference(
            "resource catalogue", "resolves the references of this " + subject,
            "The reference gives the identifier and the revision of the catalogue")
    return entries


AIRFIELD = d.reference("airfield of this record", None, "An example is `kden`")


def _altitude_constraint(context, of):
    """Fields of an inline altitude constraint (`kind`, `lower` and `upper` of `Leg.altitude` or `Hold.altitude`)."""
    return {
        (context, "kind"): d.enum("type of the altitude constraint " + of,
                                  "The type tells which of the fields `lower` and `upper` the altitude constraint has"),
        (context, "lower"): d.quantity("lower altitude of the altitude constraint", "Altitude", None,
                                       "It is the crossing altitude for `at`, and the minimum for `at_or_above` and `between`"),
        (context, "upper"): d.quantity("higher altitude of the altitude constraint", "Altitude", None,
                                       "It is the maximum for `at_or_below` and `between`"),
    }


ALTITUDE_CONSTRAINT_KINDS = d.values({
    "at": d.value_sentence("The aircraft is at the `lower` altitude at the fix."),
    "at_or_above": d.value_sentence("The aircraft is at or above the `lower` altitude at the fix."),
    "at_or_below": d.value_sentence("The aircraft is at or below the `upper` altitude at the fix."),
    "between": d.value_sentence("The aircraft is between the `lower` altitude and the `upper` altitude at the fix."),
})


def _links(items, record):
    """The rule that a listed record which identifies an airfield identifies this airfield (validator)."""
    return d.enforced("When " + items + " in this list identifies an airfield, that airfield shall be this airfield",
                      "validator:openaix.check.navigation.airfield_links")


DESCRIPTIONS = {
    # ---- airfield ------------------------------------------------------------------------------
    ("airfield", None): d.entity(
        "Airfield", "an aircraft operating location: a fixed airfield with runways, an aircraft carrier or a FARP",
        "The record has the position, the radio frequencies, the traffic pattern and the links to navigation records"),
    **_record("airfield", "airfield", kind=False),
    ("airfield", "kind"): d.enum(
        "type of the operating location",
        d.enforced("An `airfield` record shall have `position`, `elevation` and one or more runways", "schema:then"),
        d.enforced("A `farp` record shall have `position` and `elevation`, and no runways", "schema:then"),
        d.enforced("A `carrier` record shall have `carrier`, and no runways or landing pads", "schema:then")),
    ("airfield", "approach_instructions"): d.list_of(
        "local arrival and approach instructions for mission aircraft, as free text"),
    ("airfield", "atis"): d.statement(
        "This field gives the static data of the ATIS broadcast for a simulator.",
        "The ATIS frequency is an item of `frequencies` with the role `atis`",
        "The simulator gives the weather"),
    ("airfield", "calm_wind_runway"): d.statement(
        "This field gives the designator of the calm wind runway: the runway end that the airfield uses for a calm wind.",
        d.enforced("The value shall be the designator of an end of a runway of this airfield",
                   "validator:openaix.check.navigation.runway_end_references")),
    ("airfield", "carrier"): d.statement(
        "This field gives the data of an aircraft carrier.",
        "The data are the hull number, the TACAN, the ICLS channel and the case recovery data",
        d.enforced("A record with a different `kind` shall not have this field", "schema:not")),
    ("airfield", "coalition"): d.enum("coalition that controls the operating location"),
    ("airfield", "controlling_agency"): d.reference("agency", "controls the air traffic at the airfield"),
    ("airfield", "sim"): d.statement(
        "This field identifies the native object in a simulator for this operating location.",
        "In DCS, it is the airbase of a fixed airfield or the ship unit of a carrier",
        "For a FARP in DCS, it is the airbase or the static object",
        d.enforced("In DCS, a fixed airfield shall use `airbase`, and a carrier shall use `unit` or `airbase`", "schema:then"),
        "The position of a carrier changes, and thus this unit gives its position"),
    ("airfield", "elevation"): d.quantity("published elevation of the airfield above mean sea level", "Elevation"),
    ("airfield", "frequencies"): d.list_of(
        "radio frequencies of the stations at the operating location", None,
        "Each item has the role of the station, for example tower, ground or ATIS"),
    ("airfield", "ident"): d.identifier(
        "airfield in published data", None, "Examples are the ICAO location indicator and the FAA identifier"),
    ("airfield", "localizers"): d.references(
        "localizers", "are for the runways of this airfield", _links("a localizer", "localizer")),
    ("airfield", "magnetic_variation_deg"): d.quantity(
        "magnetic variation at the airfield", None, "degrees",
        "Values for east are more than zero, and values for west are less than zero"),
    ("airfield", "navaids"): d.list_of(
        "navigation aids of the airfield: `VOR`, `VORTAC`, `TACAN`, `NDB` or `DME` stations",
        None, "The TACAN of a fixed airfield or a FARP is in this list", "It is a `TACAN` or `VORTAC` station",
        _links("a navigation aid", "navigation aid")),
    ("airfield", "operating_hours"): d.statement(
        "This field gives the hours of each week, in UTC, when the operating location is open.",
        "The schedule is the same for all weeks, and the location is not open at other times",
        "When the record does not have this field, the location is always open"),
    ("airfield", "pads"): d.list_of("landing pads of a FARP or of a helicopter area of an airfield"),
    ("airfield", "position"): d.position("the airfield reference point"),
    ("airfield", "procedures"): d.references(
        "instrument procedures", "start or stop at this airfield: SID, STAR or approach",
        _links("a procedure", "procedure")),
    ("airfield", "runways"): d.list_of(
        "runways of the airfield", None, "Each item is one runway with its two ends"),
    ("airfield", "traffic_pattern"): d.statement(
        "This field gives the traffic pattern of the airfield.",
        "Its values are the default values",
        "A runway end can give different values for that end"),
    ("airfield", "transition_altitude"): d.quantity(
        "transition altitude", "Altitude", None,
        "At or below this altitude, the vertical position of an aircraft is its altitude above mean sea level"),

    ("StationFrequency", None): d.entity(
        "Station frequency", "one radio frequency of a station at an operating location, with the role of the station"),
    ("StationFrequency", "callsign"): d.text("radio callsign of the station, for example `Muwaffaq Salti Tower`"),
    ("StationFrequency", "frequency"): d.quantity(
        "frequency of the station", "Frequency", None, "The unit is megahertz, and the field `modulation` is mandatory"),
    ("StationFrequency.frequency", "unit"): d.statement("This field gives the unit of the station frequency: megahertz (`MHz`)"),
    ("StationFrequency", "hours"): d.statement(
        "This field gives the hours of each week, in UTC, when the station uses this frequency.",
        "When the record does not have this field, the station uses the frequency during the hours of the operating location"),
    ("StationFrequency", "notes"): d.text("notes about this frequency"),
    ("StationFrequency", "role"): d.enum("role of the station on this frequency"),

    ("Atis", None): d.entity(
        "ATIS data", "the static data that a simulator puts into the ATIS broadcast",
        "The weather is not part of this data"),
    ("Atis", "remarks"): d.list_of("notes at the end of the broadcast, as free text"),
    ("Atis", "runway_in_use"): d.statement(
        "This field gives the designator of the active runway end in the broadcast.",
        d.enforced("The value shall be the designator of an end of a runway of this airfield",
                   "validator:openaix.check.navigation.runway_end_references")),
    ("Atis", "transition_level"): d.quantity("transition level that the broadcast gives", "Altitude"),
    ("Atis.transition_level", "reference"): d.statement("This field gives the reference of the transition level: flight level (`FL`)"),

    ("Carrier", None): d.entity("Aircraft carrier", "a record with the identifier and the recovery data of an aircraft carrier",
                                "The carrier moves, and thus its position comes from its unit in the simulator"),
    ("Carrier", "case_recovery"): d.statement("This field gives the case recovery that the carrier plans, and the marshal data"),
    ("Carrier", "hull_number"): d.identifier("carrier as its hull number", None, "An example is `CVN-72`"),
    ("Carrier", "tacan"): d.statement(
        "This field gives the channel and the band of the TACAN of the carrier.",
        "The TACAN moves with the ship, and thus it is not a fixed navigation aid in `navaids`"),
    ("Carrier", "icls_channel"): d.statement("This field gives the channel of the ICLS of the carrier, from 1 to 20"),

    ("CaseRecovery", None): d.entity(
        "Case recovery", "the recovery procedure that a carrier plans, and the position of its marshal stack",
        "The marshal frequency is an item of `frequencies` with the role `marshal`"),
    ("CaseRecovery", "case"): d.enum("case recovery that the carrier plans"),
    ("CaseRecovery", "marshal_altitude"): d.quantity(
        "altitude of the lowest level of the marshal stack, above mean sea level", "Altitude"),
    ("CaseRecovery.marshal_altitude", "reference"): d.statement(
        "This field gives the reference of the marshal altitude: mean sea level (`MSL`)"),
    ("CaseRecovery", "marshal_distance"): d.quantity("distance of the marshal stack from the carrier", "Length"),
    ("CaseRecovery", "marshal_radial"): d.quantity("radial from the carrier on which the marshal stack is", "Bearing"),

    ("airfield", "parking"): d.list_of("parking stands of the operating location"),
    ("airfield", "taxi"): d.statement(
        "This field gives the taxi graph of the airfield: the taxi nodes, with their names, and the edges between them.",
        "The graph does not give the shape of the taxiways"),

    ("Stand", None): d.entity("Parking stand", "one parking position for one aircraft"),
    ("Stand", "category"): d.enum("largest aircraft class that can use the parking stand"),
    ("Stand", "heading"): d.quantity("heading of an aircraft on the parking stand", "Bearing"),
    ("Stand", "helicopters"): d.flag("helicopters can also use the parking stand"),
    ("Stand", "id"): d.identifier("parking stand", "its airfield", "A taxi node refers to the parking stand with this identifier"),
    ("Stand", "length"): d.quantity("length of the parking stand", "Length"),
    ("Stand", "name"): d.text("name of the parking stand in the radio calls of ATC, for example `41`"),
    ("Stand", "position"): d.position("the centre of the parking stand"),
    ("Stand", "ramp"): d.text("name of the ramp or apron of the parking stand"),
    ("Stand", "shelter"): d.flag("the parking stand is in an aircraft shelter"),
    ("Stand", "width"): d.quantity("width of the parking stand", "Length"),

    ("TaxiGraph", None): d.entity(
        "Taxi graph", "the taxi routes of an airfield as nodes and edges",
        "A program finds a taxi route along the edges from a parking stand to a hold-short node"),
    ("TaxiGraph", "edges"): d.list_of("edges between the taxi nodes"),
    ("TaxiGraph", "nodes"): d.list_of("taxi nodes of the airfield"),
    ("TaxiNode", None): d.entity("Taxi node", "one point of the taxi graph"),
    ("TaxiNode", "id"): d.identifier("taxi node", "its airfield"),
    ("TaxiNode", "kind"): d.enum(
        "type of the taxi node",
        d.enforced("A `hold_short` or `runway_connection` node shall have `runway_end`", "schema:then"),
        d.enforced("A `parking` node shall have `stand`", "schema:then")),
    ("TaxiNode", "name"): d.text("name of the taxi node, for example `A3`"),
    ("TaxiNode", "position"): d.position("the taxi node"),
    ("TaxiNode", "runway_end"): d.statement(
        "This field gives the designator of the runway end to which this node connects, or before which aircraft stop at this node.",
        d.enforced("The value shall be the designator of an end of a runway of this airfield",
                   "validator:openaix.check.navigation.runway_end_references")),
    ("TaxiNode", "stand"): d.reference(
        "parking stand", "this node connects to",
        d.enforced("The value shall be the identifier of a stand of this airfield", "validator:openaix.check.navigation.runway_end_references")),
    ("TaxiEdge", None): d.entity("Taxi edge", "a taxi route between two taxi nodes"),
    ("TaxiEdge", "category"): d.enum("largest aircraft class that can use the edge"),
    ("TaxiEdge", "from"): d.reference(
        "taxi node", "is at the start of the edge",
        d.enforced("The value shall be the identifier of a node of this graph", "validator:openaix.check.navigation.runway_end_references")),
    ("TaxiEdge", "one_way"): d.flag("aircraft can taxi on the edge only from `from` to `to`",
                                    "aircraft can taxi on the edge in the two directions"),
    ("TaxiEdge", "taxiway"): d.text("name of the taxiway of the edge, for example `Alpha`"),
    ("TaxiEdge", "to"): d.reference(
        "taxi node", "is at the end of the edge",
        d.enforced("The value shall be the identifier of a different node of this graph",
                   "validator:openaix.check.navigation.runway_end_references")),
    ("TaxiEdge", "width"): d.quantity("width of the taxiway of the edge", "Length"),

    ("Pad", None): d.entity("Landing pad", "one helicopter or vertical landing pad"),
    ("Pad", "name"): d.name("landing pad"),
    ("Pad", "position"): d.position("the centre of the landing pad"),

    ("TrafficPattern", None): d.entity(
        "Traffic pattern", "a set of pattern values, with more values for each aircraft category",
        "A consumer gets each value from the runway end first, then from the airfield, and then from the traffic pattern profile",
        "A value for an aircraft category replaces the general value for that aircraft category"),
    ("TrafficPattern", "categories"): d.statement(
        "This field gives the pattern values for each aircraft category.",
        "Each aircraft category gives only the values that are different"),
    ("TrafficPattern.categories", "fighter"): d.statement("This field gives the pattern values for fighters and attack aircraft"),
    ("TrafficPattern.categories", "heavy"): d.statement("This field gives the pattern values for heavy aircraft and tanker aircraft"),
    ("TrafficPattern.categories", "helicopter"): d.statement("This field gives the pattern values for helicopters"),
    ("TrafficPattern.categories", "trainer"): d.statement("This field gives the pattern values for trainer aircraft"),
    ("TrafficPattern", "profile"): d.reference(
        "traffic pattern profile", "gives the values that this pattern does not give"),
    ("PatternSet", None): d.entity("Pattern values", "the values of a traffic pattern for one aircraft category",
                                   "Each value is optional"),

    ("InitialPoint", None): d.entity(
        "Initial point", "the start of the initial leg of an overhead pattern",
        "It is a point with a name, or a distance and a bearing from the runway threshold"),
    ("InitialPoint", "bearing"): d.quantity(
        "bearing from the runway threshold to the initial point", "Bearing", None,
        "When the record does not have this field, the point is on the extended centreline of the runway"),
    ("InitialPoint", "distance"): d.quantity("distance from the runway threshold to the initial point", "Length"),
    ("InitialPoint", "point"): d.statement("This field gives the point, with its name, at the start of the initial leg"),
    # ---- runway --------------------------------------------------------------------------------
    ("runway", None): d.entity(
        "Runway", "one runway with its two ends, its dimensions and its surface",
        "Each end has the threshold, the heading and the equipment that is necessary for a flight simulator"),
    **_record("runway", "runway"),
    ("runway", "airfield"): d.reference(
        "airfield that has this runway", None,
        d.enforced("In the runway list of an airfield, the value shall be the identifier of that airfield",
                   "validator:openaix.check.navigation.runway_end_references")),
    ("runway", "designator"): d.statement(
        "This field gives the designator of the runway, for example `03L/21R`.",
        d.enforced("The value shall contain the designators of the two runway ends, with `/` between them",
                   "validator:openaix.check.navigation.runway_ends")),
    ("runway", "ends"): d.list_of(
        "the two ends of the runway", None,
        d.enforced("The two ends shall have opposite designators", "validator:openaix.check.navigation.runway_ends"),
        "Each runway end in the airfield has a different designator"),
    ("runway", "length"): d.quantity("published length of the runway", "Length"),
    ("runway", "surface"): d.enum("surface of the runway"),
    ("runway", "width"): d.quantity("published width of the runway", "Length"),

    ("RunwayEnd", None): d.entity(
        "Runway end", "one end of a runway and the landing direction to that end",
        "It has the threshold, the heading, the approach equipment and the local pattern values"),
    ("RunwayEnd", "arresting_gear"): d.list_of("arresting gear across the runway", None,
                                               "Distances are from the threshold of this end"),
    ("RunwayEnd", "designator"): d.statement(
        "This field gives the designator of this runway end.",
        "It is the magnetic heading in degrees divided by 10, with an optional suffix `L`, `R`, `C`, `W`, `S`, `G` or `U`"),
    ("RunwayEnd", "displaced_threshold"): d.quantity(
        "distance from the runway end to the displaced threshold", "Length", None,
        "The record does not have this field when the landing threshold is at the runway end"),
    ("RunwayEnd", "heading"): d.quantity(
        "bearing of the runway in this landing direction", "Bearing", None,
        "A magnetic heading includes the declination of the airfield",
        "Thus, a consumer can calculate the true heading from it"),
    ("RunwayEnd", "lighting"): d.statement("This field gives the runway lighting for this landing direction"),
    ("RunwayEnd", "localizer"): d.reference(
        "localizer", "is for this runway end",
        d.enforced("The field `runway` of the localizer shall identify this runway end", "validator:openaix.check.navigation.airfield_links")),
    ("RunwayEnd", "threshold"): d.position("the landing threshold for this landing direction"),
    ("RunwayEnd", "threshold_crossing_height"): d.quantity(
        "TCH of the approach path", "Length", None, "It is the height of the approach path above the landing threshold"),
    ("RunwayEnd", "threshold_elevation"): d.quantity("elevation of the landing threshold above mean sea level", "Elevation"),
    ("RunwayEnd", "traffic_pattern"): d.statement(
        "This field gives the traffic pattern values for this landing direction.",
        "They replace the values of the airfield pattern, and each value is optional"),

    ("Lighting", None): d.entity("Runway lighting", "the approach lights, the runway lights and the visual slope indicator"),
    ("Lighting", "approach_lighting"): d.enum("approach lighting system"),
    ("Lighting", "edge_lights"): d.flag("the runway has edge lights", "the runway has no edge lights"),
    ("Lighting", "reil"): d.flag("the runway end has REIL", "the runway end has no REIL"),
    ("Lighting", "slope_indicator"): d.enum("visual slope indicator for the approach"),

    ("ArrestingGear", None): d.entity("Arresting gear", "one cable or barrier across the runway that stops aircraft"),
    ("ArrestingGear", "distance_from_threshold"): d.quantity(
        "distance from the landing threshold of this end to the cable", "Length"),
    ("ArrestingGear", "type"): d.enum("type of the arresting gear"),

    # ---- localizer -----------------------------------------------------------------------------
    ("localizer", None): d.entity(
        "Localizer",
        "the transmitter of an ILS that shows the lateral position of the aircraft in relation to the course",
        "The record has its frequency, its course and, when the ILS has one, its glide slope"),
    **_record("localizer", "localizer"),
    ("localizer", "airfield"): d.reference(
        "airfield of the localizer", None,
        d.enforced("When the airfield has a list of its localizers, the list shall include this localizer",
                   "validator:openaix.check.navigation.airfield_links")),
    ("localizer", "ils_category"): d.enum(
        "ILS Category of the localizer",
        "A localizer without a glide slope does not have this field"),
    ("localizer", "course"): d.quantity(
        "front course of the localizer", "Bearing", None,
        "A magnetic course includes the station declination, which is more than zero for east"),
    ("localizer", "frequency"): d.quantity("frequency of the localizer", "Frequency", None, "The unit is megahertz"),
    ("localizer.frequency", "unit"): d.statement("This field gives the unit of the localizer frequency: megahertz (`MHz`)"),
    ("localizer", "glide_slope"): d.statement(
        "This field gives the glide slope transmitter for the same runway, when the runway has one"),
    ("localizer", "ident"): d.identifier(
        "localizer as the station transmits it in Morse code", None, "An example is `IDQQ`"),
    ("localizer", "position"): d.position("the localizer antenna"),
    ("localizer", "runway"): d.statement("This field gives the designator of the runway of the localizer"),
    ("localizer", "threshold_crossing_height"): d.quantity(
        "TCH of the glide slope", "Length", None, "It is the height of the glide slope above the landing threshold"),
    ("GlideSlope", "angle_deg"): d.quantity("angle between the glide path and a horizontal line", None, "degrees"),
    ("GlideSlope", "elevation"): d.quantity("elevation of the glide slope antenna above mean sea level", "Elevation"),
    ("GlideSlope", "position"): d.position("the glide slope antenna"),

    # ---- procedure -----------------------------------------------------------------------------
    ("procedure", None): d.entity(
        "Instrument procedure", "a SID, a STAR or an approach",
        "It is a sequence of legs with altitude constraints and speed constraints"),
    **_record("procedure", "procedure"),
    ("procedure", "airfield"): d.reference(
        "airfield at the start or at the end of the procedure", None,
        d.enforced("When the airfield has a list of its procedures, the list shall include this procedure",
                   "validator:openaix.check.navigation.airfield_links")),
    ("procedure", "ident"): d.identifier("procedure as published", None, "An example is `I16R`"),
    ("procedure", "procedure_type"): d.enum("type of the procedure"),
    ("procedure", "transitions"): d.list_of(
        "transitions and common route segments of the procedure", None,
        "A transition without an identifier is the common route or the final approach"),

    ("Transition", None): d.entity("Transition", "one transition or route segment of a procedure"),
    ("Transition", "ident"): d.identifier(
        "transition", None, "Examples are the entry fix and the runway",
        "The common route and the final approach do not have this field"),
    ("Transition", "legs"): d.list_of("the legs of the transition, in the sequence of flight", ordered=True),

    ("Leg", None): d.entity(
        "Leg", "one leg of a procedure: a path and the point at the end of the path",
        "For each leg type, conditional rules make sure that the leg has the necessary data"),
    ("Leg", "altitude"): d.statement("This field gives the altitude constraint at the end of the leg"),
    **_altitude_constraint("Leg.altitude", "at the end of the leg"),
    ("Leg", "approach_fix"): d.enum("approach function of the fix of the leg"),
    ("Leg", "arc_center"): d.statement(
        "This field gives the fix at the centre of the constant-radius arc of a `radius_to_fix` leg.",
        d.enforced("A `radius_to_fix` leg shall have this field", "schema:required")),
    ("Leg", "arc_radius"): d.quantity(
        "radius of the constant-radius arc of a `radius_to_fix` leg", "Length", None,
        d.enforced("A `radius_to_fix` leg shall have this field", "schema:required")),
    ("Leg", "course"): d.quantity(
        "course, the track or the heading of the aircraft on the leg", "Bearing", None,
        "The reference is magnetic north or true north"),
    ("Leg", "distance"): d.quantity("published distance of the leg", "Length"),
    ("Leg", "fix"): d.statement(
        "This field gives the fix at the end of the leg.",
        "For `fix_to_altitude`, `track_from_fix_for_distance`, `track_from_fix_to_dme_distance`, "
        "`fix_to_manual_termination` and `procedure_turn` legs, it is the fix at the start of the leg"),
    ("Leg", "fly_over"): d.flag(
        "the aircraft is above the fix before it turns onto the next leg",
        "the aircraft starts the turn before the fix, as at a fly-by fix"),
    ("Leg", "hold"): d.statement(
        "This field gives the holding pattern that the aircraft flies on a `hold_to_altitude`, `hold_to_fix` or "
        "`hold_to_manual_termination` leg.",
        "The hold has the fix, the course, the altitude constraint and the speed constraint of the leg",
        d.enforced("Other leg types shall not have this field", "schema:not")),
    ("Leg", "missed_approach"): d.flag("the leg is part of the missed approach procedure"),
    ("Leg", "leg_type"): d.enum(
        "type of the leg",
        "The type gives the path that the aircraft flies and the point at the end of the leg",
        "Each value is a path terminator, and the text of the value gives its code of two letters",
        "An example is `track_to_fix`, which has the code `TF`"),
    ("Leg", "recommended_navaid"): d.statement(
        "This field gives the recommended navigation aid: the navigation aid that gives the course, the radial or "
        "the distance for the leg"),
    ("Leg", "speed"): d.statement("This field gives the speed constraint at the end of the leg"),
    ("Leg", "time"): d.statement("This field gives the published flight time of the leg, in minutes"),
    ("Leg", "turn_direction"): d.enum("direction of the turn onto this leg"),
    ("Leg", "vertical_angle_deg"): d.quantity(
        "vertical path angle to the fix", None, "degrees", "A value less than zero is a descent"),

    ("Hold", None): d.entity(
        "Hold", "a holding pattern with a fix, an inbound course, a turn direction, and a leg length or a leg time",
        "Altitude constraints and speed constraints are optional"),
    ("Hold", "altitude"): d.statement("This field gives the altitude constraint for the hold"),
    **_altitude_constraint("Hold.altitude", "for the hold"),
    ("Hold", "fix"): d.statement("This field gives the fix of the holding pattern"),
    ("Hold", "inbound_course"): d.quantity("course of the inbound leg to the holding fix", "Bearing"),
    ("Hold", "leg_length"): d.quantity(
        "length of each holding leg", "Length", None, "When the hold has this length, it does not have a leg time"),
    ("Hold", "leg_time"): d.statement(
        "This field gives the flight time of each holding leg, in minutes.",
        "When the hold has this time, it does not have a leg length"),
    ("Hold", "speed"): d.statement("This field gives the speed constraint for the hold"),
    ("Hold", "turn_direction"): d.enum("direction of the turns in the holding pattern"),

    ("SpeedConstraint", None): d.entity("Speed constraint", "a speed restriction with its type and its speed"),
    ("SpeedConstraint", "kind"): d.enum("type of the speed restriction"),
    ("SpeedConstraint", "value"): d.quantity("speed of the restriction", "Speed"),

    ("Duration", None): d.entity("Time interval", "a time interval in minutes"),
    ("Duration", "unit"): d.statement("This field gives the unit of the time interval: minutes"),
    ("Duration", "value"): d.count("minutes"),

    ("Fix", None): d.entity(
        "Fix", "a navigation fix: its published identifier and position, or a reference to a point or a navigation aid "
        "in the resource catalogue"),
    ("Fix", "ident"): d.identifier("fix as published", None, "An example is `ZOOKS`"),
    ("Fix", "position"): d.position("the fix"),

    ("NavaidRef", None): d.entity(
        "Navigation aid reference",
        "a navigation aid: its identifier and position, or a reference to a navigation aid in the resource catalogue"),
    ("NavaidRef", "ident"): d.identifier("navigation aid"),
    ("NavaidRef", "position"): d.position("the navigation aid"),

    # ---- holding -------------------------------------------------------------------------------
    ("holding", None): d.entity(
        "Hold record", "a holding pattern at a fix",
        "An author writes the hold for an ATC holding stack, or a published holding leg of a procedure gives it"),
    **_record("holding", "record of a hold"),
    ("holding", "hold"): d.statement(
        "This field gives the holding pattern of this record.",
        "It has the same definition as the holding legs of a procedure"),

    # ---- path point ----------------------------------------------------------------------------
    ("path-point", None): d.entity(
        "Path point", "the geometry of the final approach segment of an approach that uses satellite navigation",
        "It has the LTP, the FPAP, the glide path angle and the TCH"),
    **_record("path-point", "path point"),
    ("path-point", "airfield"): AIRFIELD,
    ("path-point", "approach"): d.reference("approach procedure", None, "An example is `R16RY`"),
    ("path-point", "approach_type"): d.statement("This field gives the published type of the approach, for example `LPV` or `LP`"),
    ("path-point", "course_width_at_threshold"): d.quantity(
        "course width at the LTP", "Length", None,
        "It is the lateral distance from the course centreline at which full-scale deflection occurs"),
    ("path-point", "final_approach_course"): d.quantity("final approach course", "Bearing"),
    ("path-point", "flight_path_alignment_point"): d.position(
        "the FPAP", "With the LTP, this point gives the direction of the final approach course"),
    ("path-point", "glide_path_angle_deg"): d.quantity("angle between the glide path and a horizontal line", None, "degrees"),
    ("path-point", "landing_threshold_elevation"): d.quantity(
        "orthometric height of the LTP above mean sea level", "Elevation"),
    ("path-point", "landing_threshold_point"): d.position(
        "the LTP", "The path of the final approach goes above this point at the threshold crossing height"),
    ("path-point", "runway"): d.statement("This field gives the designator of the runway of the approach"),
    ("path-point", "threshold_crossing_height"): d.quantity(
        "TCH of the path of the final approach", "Length", None,
        "It is the height of the path of the final approach above the LTP"),

    # ---- minimum safe altitude -----------------------------------------------------------------
    ("msa", None): d.root(
        "Minimum safe altitude", "MSA",
        "the minimum altitudes in sectors around a centre fix, in the radius of the sectors",
        "The bearings of a sector are bearings to the centre",
        "Each sector goes in the clockwise direction from the bearing at its start to the bearing at its end"),
    **_record("msa", "record of a minimum safe altitude"),
    ("msa", "airfield"): AIRFIELD,
    ("msa", "center"): d.statement(
        "This field gives the fix at the centre of the sectors: a navigation aid, a waypoint or an airport reference point"),
    ("msa", "sectors"): d.list_of(
        "sectors around the centre", None, "Together, the sectors make the full circle",
        "Each sector goes in the clockwise direction from the bearing at its start to the bearing at its end"),
    ("Sector", None): d.entity(
        "MSA sector", "one sector around the centre fix",
        "Its bearings are bearings to the centre, as the chart shows them, and they are usually magnetic",
        "The sector goes in the clockwise direction from `start_bearing` to `end_bearing`"),
    ("Sector", "end_bearing"): d.quantity(
        "bearing to the centre at the end of the sector", "Bearing", None,
        "It is equal to `start_bearing` only for a full circle"),
    ("Sector", "full_circle"): d.flag(
        "this one sector is the full circle", None, "Then, equal bearings do not identify a sector of zero width"),
    ("Sector", "minimum_altitude"): d.quantity("MSA in the sector, above mean sea level", "Altitude"),
    ("Sector.minimum_altitude", "reference"): d.statement(
        "This field gives the reference of the sector altitude: mean sea level (`MSL`)"),
    ("Sector", "radius"): d.quantity("radius of the sector from the centre", "Length"),
    ("Sector", "start_bearing"): d.quantity(
        "bearing to the centre at the start of the sector", "Bearing", None,
        "From this bearing, the sector goes in the clockwise direction"),

    # ---- grid minimum off-route altitude -------------------------------------------------------
    ("grid-mora", None): d.root(
        "Grid of minimum off-route altitudes", None,
        "a set of one-degree cells, each with its MORA",
        "Each cell has one degree of latitude by one degree of longitude",
        "A cell with an unknown value does not have the value zero"),
    **_record("grid-mora", "record of a grid of minimum off-route altitudes", resources=False),
    ("grid-mora", "cells"): d.list_of(
        "one-degree cells", None, "The list does not include cells without published data"),
    ("Cell", None): d.entity(
        "Grid cell", "one cell of the grid, with one degree of latitude and one degree of longitude",
        "Its edges are on full degrees of latitude and longitude"),
    ("Cell", "minimum_altitude"): d.quantity("MORA of the cell, above mean sea level", "Altitude"),
    ("Cell.minimum_altitude", "reference"): d.statement(
        "This field gives the reference of the cell altitude: mean sea level (`MSL`)"),
    ("Cell", "northeast"): d.position(
        "the north-east corner of the cell",
        "This corner is one degree north and one degree east of the south-west corner"),
    ("Cell", "southwest"): d.position("the south-west corner of the cell"),
    ("Cell", "status"): d.enum("condition of the MORA of the cell", "An unknown value is not zero"),

    # ---- navigation aid ------------------------------------------------------------------------
    ("measures/navaid", None): d.root(
        "Navigation aid", "NAVAID",
        "a radio navigation facility",
        "The record has its equipment class, its position, and its frequency or the channel of its TACAN"),
    **_record("measures/navaid", "navigation aid", kind=False),
    ("measures/navaid", "airfield"): d.reference(
        "airfield at which the navigation aid is", None,
        d.enforced("When the airfield has a list of its navigation aids, the list shall include this navigation aid",
                   "validator:openaix.check.navigation.airfield_links")),
    ("measures/navaid", "type"): d.discriminator(
        "a control measure for a navigation aid, with the catalogue code `NAVAID`",
        "The value selects this contract in a catalogue of control measures"),
    ("measures/navaid", "class"): d.enum("equipment class of the navigation aid"),
    ("measures/navaid", "dme_position"): d.position(
        "the DME antenna", "The record has this field when the source publishes this position",
        "A station with only a DME or only a TACAN does not always have a second position"),
    ("measures/navaid", "elevation"): d.quantity("elevation of the DME antenna above mean sea level", "Elevation"),
    ("measures/navaid", "frequency"): d.quantity(
        "frequency of the station", "Frequency", None, "The unit is kilohertz for an NDB",
        "For the other classes, the unit is megahertz",
        "A station with only a TACAN has no frequency"),
    ("measures/navaid", "ident"): d.identifier("navigation aid as the station transmits it in Morse code"),
    ("measures/navaid", "magnetic_variation_deg"): d.quantity(
        "station declination", None, "degrees",
        "The declination is the magnetic variation that the station uses to align its radials",
        "Values for east are more than zero, and values for west are less than zero"),
    ("measures/navaid", "position"): d.position("the `VOR`, `NDB` or `TACAN` station"),
    ("measures/navaid", "tacan"): d.statement(
        "This field gives the channel and the band of the TACAN of the station.",
        "For a `VORTAC`, it is the channel that the DME channel pairing table gives for the `VOR` frequency"),

    # ---- airway --------------------------------------------------------------------------------
    ("measures/airway", None): d.entity(
        "Airway",
        "an en-route route as a sequence of fixes, with the course, the distance and the altitude limits of each segment"),
    **_record("measures/airway", "airway", kind=False),
    ("measures/airway", "type"): d.discriminator(
        "a control measure for an airway, with the catalogue code `AIRWAY`",
        "The value selects this contract in a catalogue of control measures"),
    ("measures/airway", "airway_type"): d.enum("class of the airway"),
    ("measures/airway", "ident"): d.identifier("airway as published", None, "An example is `V356`"),
    ("measures/airway", "level"): d.enum("altitude structure of the airway"),
    ("measures/airway", "segments"): d.list_of(
        "the fixes, in airway sequence", None,
        "Each item has a fix and the segment from that fix to the next fix", ordered=True),
    ("measures/airway.segments", "#items"): d.entity(
        "Airway segment", "one airway fix and the segment from this fix to the next fix"),
    ("measures/airway.segments", "directional_restriction"): d.enum("direction restriction of the segment"),
    ("measures/airway.segments", "distance"): d.quantity("distance from this fix to the next fix", "Length"),
    ("measures/airway.segments", "fix"): d.statement("This field gives the airway fix at the start of this segment"),
    ("measures/airway.segments", "inbound_course"): d.quantity("course to this fix from the previous fix", "Bearing"),
    ("measures/airway.segments", "maximum_altitude"): d.quantity("MAA of the segment from this fix", "Altitude"),
    ("measures/airway.segments", "minimum_altitude"): d.quantity("MEA of the segment from this fix", "Altitude"),
    ("measures/airway.segments", "outbound_course"): d.quantity("course from this fix to the next fix", "Bearing"),
}

for _context in ("TrafficPattern", "PatternSet"):
    DESCRIPTIONS.update({
        (_context, "altitude"): d.quantity("altitude of the rectangular traffic pattern", "Altitude", None,
                                           "The reference is above ground level or mean sea level"),
        (_context, "break_point"): d.enum("position along the runway at which aircraft start the overhead break"),
        (_context, "direction"): d.enum("direction of the turns in the traffic pattern"),
        (_context, "initial"): d.list_of("initial points of the overhead pattern"),
        (_context, "overhead_altitude"): d.quantity("altitude of the initial leg and of the overhead break", "Altitude", None,
                                                    "The reference is above ground level or mean sea level"),
        (_context + ".altitude", "reference"): d.statement(
            "This field gives the reference of the pattern altitude: above ground level (`AGL`) or mean sea level (`MSL`)"),
        (_context + ".overhead_altitude", "reference"): d.statement(
            "This field gives the reference of the overhead altitude: above ground level (`AGL`) or mean sea level (`MSL`)"),
    })


PATTERN_ENUMS = {
    "direction": d.values({
        "left": d.value_sentence("Each turn in the pattern is a left turn."),
        "right": d.value_sentence("Each turn in the pattern is a right turn."),
    }),
    "break_point": d.values({
        "approach_end": d.value_sentence("The overhead break starts above the approach end of the runway."),
        "midfield": d.value_sentence("The overhead break starts above the middle of the runway."),
        "departure_end": d.value_sentence("The overhead break starts above the departure end of the runway."),
    }),
}

ENUMS = {
    **{(context, field): values for context in ("TrafficPattern", "PatternSet") for field, values in PATTERN_ENUMS.items()},
    **{(context, "category"): d.values({
        "fighter": "fighters and other small aircraft",
        "medium": "aircraft of moderate dimensions, for example a transport aircraft with two engines",
        "heavy": "heavy aircraft, for example a tanker aircraft or a large transport aircraft",
        "helicopter": "a stand or a taxiway only for helicopters, not for fixed-wing aircraft",
    }) for context in ("Stand", "TaxiEdge")},
    ("TaxiNode", "kind"): d.values({
        "hold_short": d.value(
            "a hold-short point before a runway",
            "Aircraft stop at this point until they get a clearance"),
        "runway_connection": d.value(
            "a point where a taxiway connects to a runway",
            "Aircraft go onto the runway or off the runway at this point"),
        "runway": "a point on the runway centreline",
        "intersection": "a point where two or more taxiways connect",
        "parking": "a point where the taxi graph connects to a parking stand",
    }),
    ("airfield", "kind"): d.values({
        "airfield": "a fixed airfield with one or more runways",
        "carrier": d.value("an aircraft carrier", "Its position comes from its unit in the simulator"),
        "farp": "a FARP with landing pads",
    }),
    ("StationFrequency", "role"): d.values({
        "tower": d.value("the aerodrome control tower", "On a carrier, it is the primary flight control"),
        "ground": "the ground control for the movement area",
        "clearance_delivery": "the clearance delivery for IFR clearances before taxi",
        "approach": d.value("the approach control", "On a military airfield, it is the RAPCON"),
        "departure": d.value("the departure control",
                             "It controls IFR flights after they take off, until the en-route centre controls them"),
        "atis": "the ATIS broadcast, which gives the weather, the active runway and other airfield information all the time",
        "ops": "the operations desk of the unit or of the FARP",
        "pmsv": "the PMSV for weather information",
        "unicom": "the UNICOM at an airfield without a control tower",
        "marshal": "the carrier marshal control for recovery",
    }),
    ("CaseRecovery", "case"): d.values({
        "case_i": "the Case `I` recovery for visual conditions by day",
        "case_ii": "the Case `II` recovery: a descent in instrument conditions to visual conditions below the cloud",
        "case_iii": "the Case `III` recovery for instrument conditions, or for a recovery at night",
    }),
    ("Lighting", "approach_lighting"): d.values({
        "ALSF_1": "`ALSF-1`: a high intensity approach lighting system with sequenced flashing lights, for Category `I` approaches",
        "ALSF_2": "`ALSF-2`: a high intensity approach lighting system with sequenced flashing lights, for Category `II` and `III` approaches",
        "MALSR": "`MALSR`: a medium intensity approach lighting system with runway alignment indicator lights",
        "MALSF": "`MALSF`: a medium intensity approach lighting system with sequenced flashing lights",
        "MALS": "`MALS`: a medium intensity approach lighting system",
        "SSALR": "`SSALR`: a simplified short approach lighting system with runway alignment indicator lights",
        "SSALF": "`SSALF`: a simplified short approach lighting system with sequenced flashing lights",
        "SSALS": "`SSALS`: a simplified short approach lighting system",
        "ODALS": "`ODALS`: an omnidirectional approach lighting system",
    }),
    ("Lighting", "slope_indicator"): d.values({
        "PAPI": d.value("the PAPI", "It is one row of light units that show the aircraft position in relation to the approach path"),
        "VASI": d.value("the VASI", "It is two or three rows of light units that show the aircraft position in relation to the approach path"),
    }),
    ("ArrestingGear", "type"): d.values({
        "BAK_12": "the `BAK-12` arresting gear with a cable",
        "BAK_13": "the `BAK-13` arresting gear with a cable",
        "BAK_14": "the `BAK-14` arresting gear with a cable that retracts",
        "BAK_15": "the `BAK-15` barrier with a net",
        "MA_1A": "the `MA-1A` barrier with a net and a cable",
        "E_5": "the `E-5` arresting gear with a chain",
        "E_28": "the `E-28` arresting gear with a cable",
    }),
    ("localizer", "ils_category"): d.values({
        "I": "an ILS for approaches with a decision height of 200 feet or more",
        "II": "an ILS for approaches with a decision height from 100 feet to less than 200 feet",
        "III": "an ILS for approaches with a decision height of less than 100 feet, or with no decision height",
    }),
    ("runway", "surface"): d.values({
        "hard": "a surface of asphalt, concrete or an equivalent hard material",
        "soft": "a surface of gravel, grass or ground, without asphalt or concrete",
        "water": "an area of water that seaplanes use as a runway",
    }),
    ("procedure", "procedure_type"): d.values({
        "departure": "a SID: an IFR route from the runway to the en-route structure",
        "arrival": "a STAR: an IFR route from the en-route structure to the approach",
        "approach": "an instrument approach procedure, from the initial approach fix to a landing or a missed approach",
    }),
    # Path terminators: the definition of each code in sources/leg-type-definitions.json, as full sentences.
    ("Leg", "leg_type"): d.values({row["leg_type"]: d.value_sentence(row["definition"])
                                   for row in LEG_TYPE_SOURCE["codes"].values()}),
    ("Leg", "approach_fix"): d.values({
        "initial_approach_fix": "the fix at the start of the initial approach segment",
        "intermediate_fix": "the fix at the end of the initial approach segment and the start of the intermediate approach segment",
        "final_approach_course_fix": "a fix on the extension of the final approach course, before the final approach fix",
        "final_approach_fix": "the fix at the start of the final approach segment, where the descent to the runway starts",
        "missed_approach_point": d.value("the point at or before which the aircraft starts the missed approach procedure",
                                         "This keeps the minimum obstacle clearance"),
    }),
    ("Leg", "turn_direction"): d.values({
        "left": d.value_sentence("The aircraft makes a left turn onto the leg."),
        "right": d.value_sentence("The aircraft makes a right turn onto the leg."),
        "either": d.value_sentence("The aircraft can make a left turn or a right turn onto the leg."),
    }),
    ("Leg.altitude", "kind"): ALTITUDE_CONSTRAINT_KINDS,
    ("Hold.altitude", "kind"): ALTITUDE_CONSTRAINT_KINDS,
    ("Hold", "turn_direction"): d.values({
        "right": d.value_sentence("Each turn is a right turn. This is the standard holding pattern."),
        "left": d.value_sentence("Each turn is a left turn. This is not the standard holding pattern."),
    }),
    ("SpeedConstraint", "kind"): d.values({
        "at": d.value_sentence("The aircraft flies at the speed in `value`."),
        "at_or_below": d.value_sentence("The speed is a maximum speed. The aircraft flies at or below the speed in `value`."),
        "at_or_above": d.value_sentence("The speed is a minimum speed. The aircraft flies at or above the speed in `value`."),
    }),
    ("Cell", "status"): d.values({
        "known": d.value_sentence("The source publishes a MORA for the cell."),
        "unknown": d.value_sentence("The source identifies the MORA of the cell as unknown. An unknown value is not zero."),
    }),
    ("measures/navaid", "class"): d.values({
        "VOR": d.value("a `VOR` station", "Its VHF signal gives the aircraft its magnetic bearing from the station"),
        "VOR_DME": d.value("a `VOR` station with a `DME` at the same site",
                           "It gives the aircraft its bearing from the station and its slant distance to the station"),
        "VORTAC": d.value("a `VORTAC` station: a `VOR` and a `TACAN` at one site",
                          "Aircraft of civil aviation use the `VOR`, and aircraft of armed forces use the `TACAN`"),
        "TACAN": d.value("a `TACAN` station", "On UHF, it gives aircraft of armed forces their magnetic bearing and slant distance from the station"),
        "DME": d.value("a `DME` station", "It gives the aircraft its slant distance to the station"),
        "NDB": d.value("an `NDB` station", "It transmits a signal in all directions",
                       "A direction finder in the aircraft shows the direction to the station"),
        "ILS_DME": "a `DME` that operates with the localizer of an ILS",
    }),
    ("measures/airway", "airway_type"): {
        value: d.value(*d.sentences(MEASURE_CODES[code]["definition"])) for value, code in AIRWAY_TYPE_CODES.items()},
    ("measures/airway", "level"): d.values({
        "low": "the low altitude structure",
        "high": "the high altitude structure",
        "both": "the low and the high altitude structures",
    }),
    ("measures/airway.segments", "directional_restriction"): d.values({
        "forward": d.value_sentence("Aircraft can fly the segment only in airway sequence."),
        "backward": d.value_sentence("Aircraft can fly the segment only in the direction opposite to airway sequence."),
    }),
}
