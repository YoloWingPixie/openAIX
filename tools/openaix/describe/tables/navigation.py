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
                "A record that an author writes does not have this field",
                "The field `provenance` gives the same facts as structured data")


def _record(schema, subject, kind=True, resources=True):
    """Root fields that each navigation record has, written for one schema."""
    entries = {
        (schema, "$schema"): d.reference("schema", "validates this document"),
        (schema, "id"): d.identifier(subject, None, "Other resources and orders use this stable identifier to refer to this " + subject),
        (schema, "name"): d.name(subject),
        (schema, "source"): d.source("record", *SOURCE_NOTES),
        (schema, "provenance"): d.statement(
            "This field gives the provenance of this " + subject + " as structured data: how the data were made, the authority, "
            "the AIRAC cycle and the tool that made them"),
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
LIMIT_ANY = "an altitude with its reference, the surface or no limit"


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
    ("airfield", "use"): d.enum("use of the operating location: civil, military, or joint civil and military use",
                                "Aerodrome data publish it"),
    ("airfield", "hung_ordnance_runway"): d.statement(
        "This field gives the designator of the runway end that aircraft with hung ordnance use for landing.",
        "A base publishes it in its local emergency procedures",
        d.enforced("The value shall be the designator of an end of a runway of this airfield",
                   "validator:openaix.check.navigation.runway_end_references"),
        d.enforced("A `carrier` record shall not have this field", "schema:not")),
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

    ("Pad", None): d.entity("Pad", "one prepared surface of the operating location: a helicopter or vertical landing pad, "
                            "or a ground pad for aircraft with live ordnance or hot brakes",
                            "A pad without a use is a landing pad"),
    ("Pad", "name"): d.name("pad"),
    ("Pad", "position"): d.position("the centre of the pad"),
    ("Pad", "use"): d.list_of("uses of the ground pad", None, "One pad can have more than one use"),

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
    ("Reentry", None): d.entity("Re-entry", "the procedure that aircraft use to enter the overhead pattern again",
                                "It has the point or the name of the re-entry point, and its altitude"),
    ("Reentry", "point"): d.reference("point at which aircraft start the re-entry"),
    ("Reentry", "name"): d.text("name of the re-entry point, when no point record identifies it"),
    ("Reentry", "altitude"): d.quantity("altitude of the re-entry", "Altitude", None,
                                        "The reference is above ground level or mean sea level"),
    ("Reentry.altitude", "reference"): d.statement(
        "This field gives the reference of the re-entry altitude: above ground level (`AGL`) or mean sea level (`MSL`)"),
    ("GoAround", None): d.entity("Go-around", "the local climb-out instructions for a go-around",
                                 "When the record has no heading, aircraft fly the runway heading"),
    ("GoAround", "altitude"): d.quantity("altitude to which aircraft climb on a go-around", "Altitude", None,
                                         "The reference is above ground level or mean sea level"),
    ("GoAround.altitude", "reference"): d.statement(
        "This field gives the reference of the go-around altitude: above ground level (`AGL`) or mean sea level (`MSL`)"),
    ("GoAround", "heading"): d.quantity("heading that aircraft fly on a go-around", "Bearing"),
    ("SimulatedFlameout", None): d.entity("Simulated flameout pattern", "the altitudes of the high key and the low key of an SFO pattern",
                                          "The base publishes them"),
    ("SimulatedFlameout", "high_key"): d.altitude_block("the high key", "The block gives the altitudes that aircraft can use at the high key"),
    ("SimulatedFlameout", "low_key"): d.altitude_block("the low key", "The block gives the altitudes that aircraft can use at the low key"),

    ("InitialPoint", None): d.entity(
        "Initial point", "the start of the initial leg of an overhead pattern",
        "It is a point with a name, or a distance and a bearing from the runway threshold"),
    ("InitialPoint", "bearing"): d.quantity(
        "bearing from the runway threshold to the initial point", "Bearing", None,
        "When the record does not have this field, the point is on the extended centreline of the runway"),
    ("InitialPoint", "distance"): d.quantity("distance from the runway threshold to the initial point", "Length"),
    ("InitialPoint", "point"): d.statement("This field gives the point, with its name, at the start of the initial leg"),
    # ---- NOTAM ---------------------------------------------------------------------------------
    ("notam", None): d.root(
        "notice to air missions", "NOTAM",
        "a notice about the establishment, condition or change of an aeronautical facility, service, procedure or hazard",
        "This record has the basic items of the ICAO NOTAM format of Annex 15: the number, the location, the NOTAM Code, "
        "the effective time interval, the text and the vertical limits",
        "Planners write NOTAMs before the operation"),
    ("notam", "$schema"): d.reference("schema", "validates this document"),
    ("notam", "id"): d.identifier("NOTAM", None, "Other resources and orders use this stable identifier to refer to this NOTAM"),
    ("notam", "kind"): d.discriminator("a NOTAM record", "The value selects this contract"),
    ("notam", "extensions"): d.extension(),
    ("notam", "resources_ref"): d.reference("resource catalogue", "resolves the references of this NOTAM",
                                            "The reference gives the identifier and the revision of the catalogue"),
    ("notam", "number"): d.statement("This field gives the NOTAM number: the series, the number in the series and the year",
                                     "An example is `A0123/26`"),
    ("NotamNumber", None): d.entity("NOTAM number", "the series letter, the number and the year that identify a NOTAM"),
    ("NotamNumber", "series"): d.text("series letter of the NOTAM, for example `A`"),
    ("NotamNumber", "number"): d.statement("This field gives the number of the NOTAM in its series and year, from 1 to 9999"),
    ("NotamNumber", "year"): d.statement("This field gives the year of the NOTAM, with four digits",
                                         "The NOTAM number shows its last two digits"),
    ("notam", "location"): d.reference("operating location that the NOTAM is about", None, "It is item A of the NOTAM"),
    ("notam", "code"): d.statement("This field gives the NOTAM Code of item Q: the letter `Q`, two letters for the subject "
                                   "and two letters for its condition, for example `QMRLC` for a closed runway",
                                   "ICAO Doc 8126 gives the NOTAM Code"),
    ("notam", "effective"): d.window("the NOTAM is in effect", "It is items B and C of the NOTAM"),
    ("notam", "text"): d.text("text of the NOTAM, in the abbreviations of the NOTAM", "It is item E of the NOTAM"),
    ("notam", "lower"): d.vertical_limit("floor", "the area that the NOTAM is about", LIMIT_ANY, "It is item F of the NOTAM"),
    ("notam", "upper"): d.vertical_limit("ceiling", "the area that the NOTAM is about", LIMIT_ANY, "It is item G of the NOTAM"),
    ("notam", "affects"): d.list_of(
        "runways, navigation aids, airspace and instrument procedures that the NOTAM is about", None,
        "Each item is a runway end of the location, a control measure or an instrument procedure",
        d.enforced("A runway shall be an end of a runway of the location", "validator:openaix.check.navigation.airfield_links")),
    ("RunwaySelection", None): d.entity("Runway selection", "a reference to one runway end of the location of the NOTAM"),
    ("RunwaySelection", "kind"): d.discriminator("a runway selection"),
    ("RunwaySelection", "designator"): d.statement("This field gives the designator of the runway end, for example `03L`"),
    ("ProcedureSelection", None): d.entity("Procedure selection", "a reference to one instrument procedure of the resource catalogue"),
    ("ProcedureSelection", "kind"): d.discriminator("an instrument procedure selection"),
    ("ProcedureSelection", "id"): d.reference("instrument procedure that the NOTAM is about"),
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
    ("procedure", "approach_type"): d.enum(
        "guidance of the final approach segment of an approach",
        d.enforced("Only an approach shall have this field", "schema:not"),
        d.enforced("A `par` or `asr` approach shall have `radar_approach`, and other procedures shall not have it", "schema:then")),
    ("procedure", "navigation_specification"): d.statement(
        "This field gives the navigation specification of the procedure: conventional navigation, RNAV or RNP, "
        "and the sensors and navigation aids that it needs"),
    ("procedure", "minima"): d.list_of(
        "published minima lines of the approach", None, d.enforced("Only an approach shall have this field", "schema:not")),
    ("procedure", "radar_approach"): d.statement(
        "This field gives the final approach of a PAR or an ASR approach: the runway, the course, the glide path and the radar coverage"),
    ("procedure", "climb_gradients"): d.list_of(
        "minimum climb gradients of a departure or of the missed approach of an approach", None,
        d.enforced("An arrival shall not have this field", "schema:not")),
    ("procedure", "takeoff_minima"): d.list_of(
        "takeoff minima of a departure", None, d.enforced("Only a departure shall have this field", "schema:not")),
    ("procedure", "obstacle_assessment"): d.statement(
        "This field gives the result of the obstacle clearance assessment of the procedure, segment by segment"),
    ("procedure", "transitions"): d.list_of(
        "transitions and common route segments of the procedure", None,
        "A transition without an identifier is the common route or the final approach",
        d.enforced("A procedure shall have this field, except a `par` or `asr` approach", "schema:else")),

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

    ("Leg", "rnp_value"): d.quantity(
        "lateral navigation accuracy that the leg needs, as an RNP value in nautical miles", "Length", None,
        "It applies to this leg only, for example a leg of an RNP approach with authorization required",
        "When the leg does not have this field, the value of the navigation specification applies"),
    ("Leg", "procedure_turn"): d.statement(
        "This field gives the type and the limits of the procedure turn of a `procedure_turn` leg.",
        "The field `course` of the leg is the outbound course, `turn_direction` is the direction of the first turn, "
        "and `altitude` is the procedure turn altitude",
        d.enforced("Other leg types shall not have this field", "schema:not")),

    ("ProcedureTurn", None): d.entity(
        "Procedure turn", "a course reversal from the outbound course onto the inbound course of an approach",
        "The aircraft stays on the manoeuvring side of the outbound course and in the distance in `remain_within`"),
    ("ProcedureTurn", "turn_type"): d.enum("type of the course reversal"),
    ("ProcedureTurn", "remain_within"): d.quantity(
        "distance from the fix of the leg in which the aircraft completes the procedure turn", "Length"),
    ("ProcedureTurn", "outbound_time"): d.statement(
        "This field gives the flight time on the outbound leg before the aircraft turns back, in minutes.",
        "Base turns and some procedure turns publish this time"),
    ("ProcedureTurn", "inbound_course"): d.quantity("course of the inbound leg after the course reversal", "Bearing"),

    # ---- approach minima -----------------------------------------------------------------------
    ("MinimaLine", None): d.entity(
        "Minima line", "one line of the published minima of an approach: the minima for one type of guidance and one manoeuvre",
        "It gives the minima for each aircraft approach category"),
    ("MinimaLine", "line"): d.enum("guidance that the minima line uses"),
    ("MinimaLine", "label"): d.statement(
        "This field gives the name of the minima line as the chart shows it, for example `S-ILS 31` or `LNAV/VNAV`"),
    ("MinimaLine", "manoeuvre"): d.enum(
        "manoeuvre after the approach",
        d.enforced("A `circling` line shall not have `runway`, and other lines shall have it", "schema:then"),
        d.enforced("The minima of a `circling` line shall be minimum descent altitudes, with the height above the aerodrome",
                   "schema:then")),
    ("MinimaLine", "runway"): d.statement(
        "This field gives the designator of the runway of a straight-in line, or of the runway after a sidestep"),
    ("MinimaLine", "ils_category"): d.enum(
        "ILS category of the minima",
        d.enforced("Only a line of type `ils` or `gls` shall have this field", "schema:not")),
    ("MinimaLine", "rnp_value"): d.quantity(
        "RNP value of the minima line, in nautical miles", "Length", None,
        "An approach with authorization required can publish one line for each RNP value",
        d.enforced("Only a line of type `rnp` shall have this field", "schema:not")),
    ("MinimaLine", "height_reference"): d.enum(
        "elevation from which the heights of the line are measured"),
    ("MinimaLine", "condition"): d.text(
        "condition in which this line applies, for example a remote altimeter setting or inoperative approach lights",
        "A line without this field gives the standard minima"),
    ("MinimaLine", "category_minima"): d.list_of(
        "minima of the line for the aircraft approach categories", None,
        "Each item gives the minima for one or more categories",
        d.enforced("A straight-in line with vertical guidance shall give decision altitudes, and other lines shall give "
                   "minimum descent altitudes", "schema:then")),
    ("MinimaLine", "remarks"): d.list_of("remarks for this minima line, as free text"),

    ("CategoryMinimum", None): d.entity(
        "Category minimum", "the minima of a minima line for one or more aircraft approach categories",
        "It has a decision altitude or an MDA, a height and a visibility or an RVR"),
    ("CategoryMinimum", "categories"): d.list_of(
        "aircraft approach categories to which these minima apply", None,
        "Categories `A` to `E` follow the speed at the threshold, and category `H` is for helicopters"),
    ("CategoryMinimum", "decision_altitude"): d.quantity(
        "decision altitude above mean sea level", "Altitude", None,
        "At this altitude the pilot starts the missed approach when the required visual references are not visible",
        d.enforced("The minima shall have this field or `minimum_descent_altitude`, but not both", "schema:oneOf")),
    ("CategoryMinimum", "minimum_descent_altitude"): d.quantity(
        "MDA above mean sea level", "Altitude", None,
        "The aircraft does not descend below this altitude without the required visual references"),
    ("CategoryMinimum", "height"): d.quantity(
        "height of the decision altitude or the MDA above the elevation that `height_reference` of the line names",
        "Length", None, "For a decision altitude, this height is the decision height"),
    ("CategoryMinimum", "visibility"): d.statement(
        "This field gives the minimum visibility for the approach, as a visibility with its unit"),
    ("CategoryMinimum", "runway_visual_range"): d.quantity(
        "minimum RVR for the approach", "Length", None, "The unit is feet or metres"),

    ("Visibility", None): d.entity("Visibility", "a horizontal visibility with its unit"),
    ("Visibility", "value"): d.statement("This field gives the value of the visibility, in the unit of `unit`"),
    ("Visibility", "unit"): d.enum("unit of the visibility"),

    # ---- navigation specification --------------------------------------------------------------
    ("NavigationSpecification", None): d.entity(
        "Navigation specification", "the navigation that the procedure needs: conventional navigation, RNAV or RNP",
        "It gives the PBN navigation specification, the RNP value, the sensors and the navigation aids"),
    ("NavigationSpecification", "navigation_type"): d.enum(
        "type of navigation of the procedure",
        d.enforced("A `conventional` procedure shall not have `specification` or `rnp_value`", "schema:then"),
        d.enforced("An `rnav` or `rnp` procedure shall have a `specification` of its type", "schema:then")),
    ("NavigationSpecification", "specification"): d.enum("PBN navigation specification of the procedure"),
    ("NavigationSpecification", "rnp_value"): d.quantity(
        "lateral navigation accuracy of the procedure, as an RNP value in nautical miles", "Length", None,
        d.enforced("An `rnav` procedure shall not have this field", "schema:not")),
    ("NavigationSpecification", "sensors"): d.list_of(
        "navigation sensors that the procedure needs", None, "The aircraft uses one or more of them"),
    ("NavigationSpecification", "required_navaids"): d.list_of(
        "navigation aids that are necessary to fly the procedure", None,
        "Each item is a navigation aid with its identifier and position, or a reference to a navigation aid in the resource catalogue"),
    ("NavigationSpecification", "notes"): d.text("notes about the navigation equipment of the procedure"),

    # ---- radar approach ------------------------------------------------------------------------
    ("RadarApproach", None): d.entity(
        "Radar approach", "the final approach of a PAR or an ASR approach, which a controller gives from the radar",
        "The field `approach_type` of the procedure gives the type of radar"),
    ("RadarApproach", "runway"): d.statement("This field gives the designator of the runway of the radar approach"),
    ("RadarApproach", "final_approach_course"): d.quantity("final approach course of the radar approach", "Bearing"),
    ("RadarApproach", "glide_path_angle_deg"): d.quantity(
        "angle between the PAR glide path and a horizontal line", None, "degrees",
        d.enforced("A PAR approach shall have this field, and an ASR approach shall not have it", "schema:then")),
    ("RadarApproach", "threshold_crossing_height"): d.quantity(
        "TCH of the PAR glide path", "Length", None, "It is the height of the glide path above the landing threshold"),
    ("RadarApproach", "position"): d.position("the radar antenna"),
    ("RadarApproach", "coverage"): d.statement("This field gives the volume in which the radar gives the approach"),
    ("RadarApproach", "recommended_altitudes"): d.list_of(
        "altitudes that the controller recommends at distances from the runway on an ASR approach", None,
        d.enforced("A PAR approach shall not have this field", "schema:not")),
    ("RadarApproach", "missed_approach_point_distance"): d.quantity(
        "distance of the missed approach point of an ASR approach from the runway threshold", "Length", None,
        d.enforced("A PAR approach shall not have this field", "schema:not")),
    ("RadarApproach", "lost_communications"): d.list_of("lost communications instructions for the radar approach, as free text"),

    ("RadarCoverage", None): d.entity(
        "Radar coverage", "the volume of the radar on the final approach",
        "The azimuth limits are angles from the final approach course, and the elevation limits are angles above a horizontal line"),
    ("RadarCoverage", "range"): d.quantity("range of the radar coverage on the final approach, from the runway threshold", "Length"),
    ("RadarCoverage", "azimuth_left_deg"): d.quantity("azimuth limit left of the final approach course", None, "degrees"),
    ("RadarCoverage", "azimuth_right_deg"): d.quantity("azimuth limit right of the final approach course", None, "degrees"),
    ("RadarCoverage", "elevation_lower_deg"): d.quantity(
        "lower elevation limit of the PAR", None, "degrees", "A value less than zero is below the horizontal",
        d.enforced("An ASR approach shall not have this field", "schema:not")),
    ("RadarCoverage", "elevation_upper_deg"): d.quantity(
        "upper elevation limit of the PAR", None, "degrees", d.enforced("An ASR approach shall not have this field", "schema:not")),

    ("RecommendedAltitude", None): d.entity(
        "Recommended altitude", "an altitude that the controller recommends at one distance from the runway on an ASR approach"),
    ("RecommendedAltitude", "distance"): d.quantity("distance from the runway threshold", "Length"),
    ("RecommendedAltitude", "altitude"): d.quantity("recommended altitude above mean sea level at this distance", "Altitude"),

    # ---- climb gradients and takeoff minima ----------------------------------------------------
    ("ClimbGradient", None): d.entity(
        "Climb gradient", "a minimum climb gradient of a departure or a missed approach",
        "The aircraft climbs at this gradient or more until the altitude in `until` or the fix in `until_fix`"),
    ("ClimbGradient", "gradient"): d.statement("This field gives the minimum climb gradient, as a gradient with its unit"),
    ("ClimbGradient", "until"): d.quantity(
        "altitude above mean sea level up to which the climb gradient applies", "Altitude", None,
        d.enforced("The climb gradient shall have this field or `until_fix`", "schema:anyOf")),
    ("ClimbGradient", "until_fix"): d.statement("This field gives the fix up to which the climb gradient applies"),
    ("ClimbGradient", "reason"): d.enum("reason for the climb gradient"),
    ("ClimbGradient", "runway"): d.statement("This field gives the designator of the departure runway of the climb gradient"),
    ("ClimbGradient", "notes"): d.text("notes about the climb gradient"),

    ("Gradient", None): d.entity("Gradient", "a climb gradient with its unit"),
    ("Gradient", "value"): d.statement("This field gives the value of the gradient, in the unit of `unit`"),
    ("Gradient", "unit"): d.enum("unit of the gradient"),

    ("TakeoffMinimum", None): d.entity(
        "Takeoff minimum", "the lowest weather for a takeoff on this departure",
        d.enforced("It shall have `visibility` or `runway_visual_range`", "schema:anyOf")),
    ("TakeoffMinimum", "runway"): d.statement("This field gives the designator of the runway of the takeoff minimum"),
    ("TakeoffMinimum", "ceiling"): d.quantity("lowest ceiling for the takeoff, above the aerodrome", "Length"),
    ("TakeoffMinimum", "visibility"): d.statement("This field gives the lowest visibility for the takeoff"),
    ("TakeoffMinimum", "runway_visual_range"): d.quantity("lowest RVR for the takeoff", "Length", None, "The unit is feet or metres"),
    ("TakeoffMinimum", "climb_gradient"): d.statement(
        "This field gives the climb gradient that the aircraft needs to use these minima"),
    ("TakeoffMinimum", "condition"): d.text("condition in which this takeoff minimum applies, for example the number of engines"),
    ("TakeoffMinimum", "remarks"): d.list_of("remarks for the takeoff, for example obstacle notes, as free text"),

    # ---- obstacle clearance assessment ---------------------------------------------------------
    ("ObstacleAssessment", None): d.entity(
        "Obstacle clearance assessment", "the result of an assessment of the terrain and the obstacles under the procedure",
        "For each segment it gives the controlling obstacle, the obstacle clearance and the lowest altitude"),
    ("ObstacleAssessment", "criteria"): d.enum("design criteria of the assessment"),
    ("ObstacleAssessment", "criteria_document"): d.statement(
        "This field gives the document and the edition of the criteria, for example `FAA Order 8260.3G`"),
    ("ObstacleAssessment", "obstacle_data"): d.text(
        "terrain data and obstacle data of the assessment, for example the name of the elevation model and its resolution"),
    ("ObstacleAssessment", "assessed_at"): d.time("the assessment"),
    ("ObstacleAssessment", "tool"): d.statement("This field gives the software that made the assessment"),
    ("ObstacleAssessment", "segments"): d.list_of("results of the assessment for the segments of the procedure"),
    ("ObstacleAssessment", "notes"): d.text("notes about the assessment"),

    ("SegmentAssessment", None): d.entity(
        "Segment assessment", "the obstacle clearance result for one segment of the procedure"),
    ("SegmentAssessment", "segment"): d.enum("type of the segment"),
    ("SegmentAssessment", "transition"): d.statement(
        "This field gives the identifier of the transition of the segment, as in `ident` of the transition"),
    ("SegmentAssessment", "from_fix"): d.statement("This field gives the identifier of the fix at the start of the segment"),
    ("SegmentAssessment", "to_fix"): d.statement("This field gives the identifier of the fix at the end of the segment"),
    ("SegmentAssessment", "controlling_obstacle"): d.statement(
        "This field gives the controlling obstacle: the obstacle that sets the lowest altitude of the segment"),
    ("SegmentAssessment", "obstacle_clearance"): d.quantity(
        "obstacle clearance that the assessment applies above the controlling obstacle", "Length", None,
        "It is the minimum obstacle clearance of ICAO Doc 8168 or the required obstacle clearance of FAA Order 8260.3"),
    ("SegmentAssessment", "minimum_altitude"): d.quantity(
        "lowest altitude of the segment above mean sea level that keeps the obstacle clearance", "Altitude"),
    ("SegmentAssessment", "satisfied"): d.flag(
        "the published altitudes of the segment are at or above `minimum_altitude`",
        "a published altitude of the segment is below `minimum_altitude`"),
    ("SegmentAssessment", "notes"): d.text("notes about the result for the segment"),

    ("Obstacle", None): d.entity("Obstacle", "terrain or an object that the assessment of a segment uses"),
    ("Obstacle", "ident"): d.identifier("obstacle in its source data", None, "An example is the number of the obstacle in an obstacle file"),
    ("Obstacle", "obstacle_type"): d.enum("type of the obstacle"),
    ("Obstacle", "position"): d.position("the obstacle"),
    ("Obstacle", "elevation"): d.quantity("elevation of the top of the obstacle above mean sea level", "Elevation"),
    ("Obstacle", "height"): d.quantity("height of the obstacle above the ground", "Length"),

    # ---- provenance ----------------------------------------------------------------------------
    ("Tool", None): d.entity("Tool", "a software tool with its version"),
    ("Tool", "name"): d.statement("This field gives the name of the software tool"),
    ("Tool", "version"): d.statement("This field gives the version of the software tool"),

    ("Provenance", None): d.entity(
        "Provenance", "the origin of a navigation record: how its data were made, by which authority, for which AIRAC cycle "
        "and with which tool"),
    ("Provenance", "derivation"): d.enum("way in which the data of the record were made"),
    ("Provenance", "authority"): d.statement(
        "This field gives the name of the authority that publishes the source data, for example `FAA`"),
    ("Provenance", "airac_cycle"): d.statement(
        "This field gives the AIRAC cycle of the data, as two digits of the year and two digits of the cycle, for example `2610`"),
    ("Provenance", "effective_from"): d.time("the start of the period in which the data are effective"),
    ("Provenance", "effective_until"): d.time("the end of the period in which the data are effective"),
    ("Provenance", "publication"): d.reference(
        "publication from which the data come", None, "An example is the chart of the procedure"),
    ("Provenance", "tool"): d.statement("This field gives the software tool that converted or made the data"),
    ("Provenance", "generated_at"): d.time("the conversion or the generation of the data"),

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
        (_context, "reentry"): d.statement("This field gives the re-entry procedure of the overhead pattern"),
        (_context, "go_around"): d.statement("This field gives the go-around instructions of the pattern"),
        (_context, "departure_ceiling"): d.quantity("highest altitude for departures while aircraft use the overhead pattern", "Altitude",
                                                    None, "The reference is above ground level or mean sea level"),
        (_context + ".departure_ceiling", "reference"): d.statement(
            "This field gives the reference of the departure ceiling: above ground level (`AGL`) or mean sea level (`MSL`)"),
        (_context, "sfo"): d.statement("This field gives the SFO pattern",
                                       "When the record has no SFO pattern, the pattern values do not give one"),
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
    ("airfield", "use"): d.values({
        "civil": "an operating location for civil aviation",
        "military": "an operating location of armed forces",
        "joint": "an operating location that civil aviation and armed forces use together",
    }),
    ("Pad", "use"): d.values({
        "hot_brake": "a hot brake area, where aircraft with hot brakes stop until the brakes are cool",
        "hung_ordnance": "a hung ordnance area, where ground crews make safe the ordnance that did not release",
        "arm_dearm": "an arming and disarming area at the end of the runway, where ground crews arm aircraft before take-off and "
                     "disarm them after landing",
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
        "final": d.value("the final controller of a PAR approach", "The final controller gives the azimuth and glide path corrections"),
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
    ("procedure", "approach_type"): d.values({
        "ils": "an ILS approach, with a localizer and a glide slope",
        "localizer": "a localizer approach, with lateral guidance from a localizer and no glide slope",
        "gls": "a GLS approach, with lateral and vertical guidance from a GBAS ground station",
        "rnav": "an RNAV or RNP approach with satellite navigation, for example `RNAV (GPS)` or `RNP`",
        "vor": "an approach with lateral guidance from a VOR station, with or without DME",
        "tacan": "an approach with lateral guidance from a TACAN station",
        "ndb": "an approach with guidance from an NDB station",
        "par": "a PAR approach: a controller gives the course and the glide path from a precision radar",
        "asr": "an ASR approach: a controller gives the course and recommended altitudes from a surveillance radar",
    }),
    ("MinimaLine", "line"): d.values({
        "ils": "minima for an ILS approach, with a decision altitude",
        "gls": "minima for a GLS approach, with a decision altitude",
        "par": "minima for a PAR approach, with a decision altitude",
        "lpv": "minima with LPV vertical guidance from satellite augmentation, with a decision altitude",
        "lnav_vnav": "minima with LNAV and barometric or satellite vertical guidance, with a decision altitude",
        "rnp": "minima of an RNP approach with authorization required, with a decision altitude for one RNP value",
        "lp": "minima with LP lateral guidance and no vertical guidance, with an MDA",
        "lnav": "minima with LNAV lateral guidance only, with an MDA",
        "localizer": "minima for a localizer approach without the glide slope, with an MDA",
        "vor": "minima for an approach with guidance from a VOR station, with an MDA",
        "tacan": "minima for an approach with guidance from a TACAN station, with an MDA",
        "ndb": "minima for an approach with guidance from an NDB station, with an MDA",
        "asr": "minima for an ASR approach, with an MDA",
    }),
    ("MinimaLine", "manoeuvre"): d.values({
        "straight_in": "a landing straight ahead on the runway of the final approach course",
        "circling": "a visual manoeuvre around the aerodrome to land on a different runway or direction",
        "sidestep": "a visual manoeuvre to land on a parallel runway next to the runway of the final approach",
    }),
    ("MinimaLine", "ils_category"): d.values({
        "I": "Category `I` minima with a decision height of 200 feet or more",
        "II": "Category `II` minima with a decision height from 100 feet to less than 200 feet",
        "III": "Category `III` minima with a decision height of less than 100 feet, or with no decision height",
    }),
    ("MinimaLine", "height_reference"): d.values({
        "touchdown_zone": "the highest elevation of the first 3000 feet of the landing surface, as for FAA heights above touchdown",
        "threshold": "the elevation of the runway threshold, as for ICAO decision heights",
        "aerodrome": "the published elevation of the aerodrome, as for circling heights",
    }),
    ("CategoryMinimum", "categories"): d.values({
        "A": "aircraft with a threshold speed of less than 91 knots",
        "B": "aircraft with a threshold speed from 91 knots to less than 121 knots",
        "C": "aircraft with a threshold speed from 121 knots to less than 141 knots",
        "D": "aircraft with a threshold speed from 141 knots to less than 166 knots",
        "E": "aircraft with a threshold speed from 166 knots to less than 211 knots",
        "H": "helicopters that fly a procedure for helicopters",
    }),
    ("Visibility", "unit"): d.values({
        "m": "a visibility in metres",
        "km": "a visibility in kilometres",
        "sm": "a visibility in statute miles, as United States charts publish it",
    }),
    ("NavigationSpecification", "navigation_type"): d.values({
        "conventional": "navigation on courses and radials of ground navigation aids, without area navigation",
        "rnav": "an RNAV navigation specification, without on-board performance monitoring and alerting",
        "rnp": "an RNP navigation specification, with on-board performance monitoring and alerting",
    }),
    ("NavigationSpecification", "specification"): d.values({
        "rnav_10": "the `RNAV 10` specification for oceanic and remote routes, with 10 nautical miles accuracy",
        "rnav_5": "the `RNAV 5` specification for continental routes, with 5 nautical miles accuracy",
        "rnav_2": "the `RNAV 2` specification for routes and terminal areas, with 2 nautical miles accuracy",
        "rnav_1": "the `RNAV 1` specification for departures, arrivals and terminal areas, with 1 nautical mile accuracy",
        "rnp_4": "the `RNP 4` specification for oceanic and remote routes, with 4 nautical miles accuracy",
        "rnp_2": "the `RNP 2` specification for continental and remote routes, with 2 nautical miles accuracy",
        "rnp_1": "the `RNP 1` specification for departures and arrivals, with 1 nautical mile accuracy",
        "advanced_rnp": "the `A-RNP` specification for routes, terminal areas and approaches, with radius-to-fix legs",
        "rnp_apch": "the `RNP APCH` specification for approaches with LNAV, LNAV/VNAV, LP or LPV minima",
        "rnp_ar_apch": "the `RNP AR APCH` specification for approaches that need a special authorization",
        "rnp_0_3": "the `RNP 0.3` specification for helicopter routes and terminal areas",
    }),
    ("NavigationSpecification", "sensors"): d.values({
        "gnss": "a GNSS receiver for satellite navigation, for example GPS",
        "gbas": "a GBAS receiver for a GLS approach",
        "dme_dme": "area navigation from the distances to two or more DME stations",
        "dme_dme_iru": "area navigation from DME distances with an IRU for gaps in DME coverage",
        "vor_dme": "area navigation from the bearing and the distance of a VOR station with DME",
        "vor": "a VOR receiver for courses and radials",
        "dme": "an interrogator in the aircraft that measures the slant range to a DME station",
        "tacan": "TACAN equipment for the bearing and the distance of a TACAN station",
        "ndb": "an automatic direction finder for the bearing to an NDB station",
        "ils": "an ILS receiver for the localizer and the glide slope",
    }),
    ("ClimbGradient", "reason"): d.values({
        "obstacle": "a gradient that keeps the obstacle clearance above the obstacles under the climb",
        "atc": "a gradient that ATC needs for airspace or for separation from other traffic",
    }),
    ("Gradient", "unit"): d.values({
        "ft/nm": "a gradient in feet of climb for each nautical mile of distance",
        "percent": "a gradient as a percentage of vertical climb to horizontal distance",
    }),
    ("ProcedureTurn", "turn_type"): d.values({
        "turn_45_180": "a 45 degree turn away from the outbound course, a straight leg, then a 180 degree turn back to the inbound course",
        "turn_80_260": "an 80 degree turn away from the outbound course and then a 260 degree turn the other way to the inbound course",
        "base_turn": "a turn from an outbound course that diverges from the inbound course, as in a teardrop course reversal",
    }),
    ("ObstacleAssessment", "criteria"): d.values({
        "pans_ops": "the ICAO criteria for the construction of instrument procedures in Doc 8168",
        "terps": "the United States Standard for Terminal Instrument Procedures in FAA Order 8260.3",
        "other": "national or military criteria that `criteria_document` names",
    }),
    ("SegmentAssessment", "segment"): d.values({
        "departure": "the climb from the runway along a departure route",
        "arrival": "the route from the en-route structure to the start of the approach",
        "feeder": "a route from the en-route structure to the initial approach fix",
        "initial": "the initial approach segment, from the initial approach fix to the intermediate fix",
        "intermediate": "the intermediate approach segment, from the intermediate fix to the final approach fix",
        "final": "the final approach segment, from the final approach fix to the runway or the missed approach point",
        "missed_approach": "the climb from the missed approach point to the holding fix or the en-route structure",
        "circling": "the visual manoeuvring area around the aerodrome for a circling approach",
        "holding": "the protected area of a holding pattern of the procedure",
    }),
    ("Obstacle", "obstacle_type"): d.values({
        "terrain": "the ground surface, for example a ridge or a peak",
        "structure": "a building, a tower, an antenna or another object that people built",
        "vegetation": "trees or other plants above the ground surface",
    }),
    ("Provenance", "derivation"): d.values({
        "published": "data that an authority publishes, taken without changes",
        "derived": "data that a tool converted or computed from published data",
        "synthesized": "data that a tool designed where no published procedure or record exists",
        "authored": "data that a person wrote for a mission or a scenario",
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
        **{value: d.value(*d.sentences(MEASURE_CODES[code]["definition"])) for value, code in AIRWAY_TYPE_CODES.items()},
        "vfr": d.value("a published route for flights under VFR, for example around, under or through complex airspace",
                       "It has no catalogue code")},
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
