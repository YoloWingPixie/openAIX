"""Description tables for common primitives, measure schemas, the measure catalogue and generic fields.

Every value is built by a describe/templates.py template. Keys follow describe/resolve.py.
Measure definitions come from sources/measure-definitions.json: `definition` is the openAIX text,
`source_text` the first-party wording and `paraphrase` the earlier openAIX restatement.
"""
import json

from openaix import ROOT
from openaix.describe import templates as d


MEASURE_SOURCE = json.loads((ROOT / "sources/measure-definitions.json").read_text())


def measure_definition(code):
    """The source-table row for a catalogue code."""
    return MEASURE_SOURCE["codes"][code]


def measure_aliases():
    return MEASURE_SOURCE["aliases"]


def technical_name(name):
    """Sentence case of a catalogue name: "Kill Box" becomes "kill box"; acronyms and proper names keep their case."""
    keep = {"NATO", "IFF", "A", "B", "C", "D", "E", "F", "G"}
    words = []
    for word in name.split(" "):
        parts = [part if part in keep or (part.isupper() and len(part) > 1) else part.lower() for part in word.split("-")]
        words.append("-".join(parts))
    return " ".join(words)


def measure_text(code):
    """The definition of a catalogue code as a full sentence: "A <name> (<CODE>) is <definition>"."""
    entry = measure_definition(code)
    name = d.ACRONYMS.get(code) or technical_name(entry["name"])
    return d.statement(d._definition(name, code if code in d.ACRONYMS else None, entry["definition"]))


def measure_summary(code):
    """Root template for a catalogue code: "<Technical name> (<CODE>). <definition>"."""
    entry = measure_definition(code)
    name = d.ACRONYMS.get(code) or technical_name(entry["name"])
    return d.root(name, code if code in d.ACRONYMS else None, entry["definition"])


def measure_note(code):
    note = measure_definition(code).get("note")
    return d.statement(note) if note else None


MEASURE_TYPE = d.enum("catalogue code of this control measure",
                      "The code identifies the definition of the control measure in doctrine",
                      "The catalogue of control measures gives its class and the source of its definition")


def measure_type_field(codes):
    """The `type` property of a schema shared by several catalogue codes."""
    return {"enum": list(codes), "description": MEASURE_TYPE, "x-enum-descriptions": {code: measure_summary(code) for code in codes}}


# Generic templates by property name, applied where no (context, property) key exists and the node has
# no description. Each takes the subject noun phrase of the owning object.
GENERIC = {
    "$schema": lambda subject: d.reference("schema", "validates this document"),
    "id": lambda subject: d.identifier(subject, None, "Other records and orders use it to refer to this " + subject),
    "name": lambda subject: d.name(subject),
    "notes": lambda subject: d.text("notes about this " + subject),
    "description": lambda subject: d.text("information about this " + subject + " and its local conditions"),
    "extensions": lambda subject: d.extension(),
    "resources_ref": lambda subject: d.reference("resource catalogue", "resolves the references of this " + subject,
                                                 "The reference gives the identifier and the revision of the catalogue"),
}


def _refers(node, name):
    if not isinstance(node, dict):
        return False
    if node.get("$ref", "").endswith("/" + name):
        return True
    return any(_refers(branch, name) for keyword in ("allOf", "oneOf", "anyOf") for branch in node.get(keyword, []))


def shape_rule(field, node, subject):
    """Template chosen by node shape for a field that recurs in many contexts, or None."""
    if field == "source" and _refers(node, "DocumentRef"):
        return d.reference("source document", None,
                           "The reference gives the identifier of the document, and it can also give a revision and a locator")
    if field in ("start", "end") and _refers(node, "GeoPoint"):
        return d.position("the " + field + " of the boundary segment")
    return None


# ---- Simulator binding texts --------------------------------------------------------------------
# One text per binding policy (sim/bindings.py POLICIES): the objects that a policy lets
# `extensions.sim.<sim>.bindings` contain.
BINDINGS = {
    "area": d.list_of("map objects", "show the boundary of the area", "These objects are not forces that operate in the area"),
    "orbit": d.list_of("map objects", "show the orbit",
                       "An order or an assignment contains the aircraft that fly the orbit, not this list"),
    "route": d.list_of("map drawings", "show the route or corridor", "The aircraft that fly the route are not part of this list"),
    "hold": d.list_of("map drawings", "show the holding pattern",
                      "An order or an assignment contains the aircraft that hold there, not this list"),
    "line": d.list_of("line drawings", "show this coordination boundary"),
    "map_point": d.list_of("map objects", "show the positions of the published navigation aids for the approach",
                           "These coordinates do not come from mobile objects"),
    "point": d.list_of("objects", "have a location that gives or shows this point",
                       "A unit or a group in this list is a reference for the location, not a flight with a task"),
    "host": d.list_of("simulator objects or observers for this agency, or map objects that show its location"),
    "fixed_target": d.list_of("simulator objects of the fixed target, or map objects that identify its location",
                              None, "The aircraft that attack the target are not part of this list"),
    "mobile_target": d.list_of("simulator units or groups of the mobile target, or map objects that show the location "
                               "from the last report", None, "The aircraft that attack the target are not part of this list"),
    "emitter": d.list_of("simulator units, groups or static objects of the emitter, or map objects that show its location",
                         None, "The aircraft that attack the emitter are not part of this list"),
    "airfield": d.list_of("simulator airbases or map objects that identify the airfield", None,
                          "The aircraft at the airfield are not airfield bindings"),
    "navaid": d.list_of("navigation equipment or map objects that identify the position of the facility"),
    "flight": d.list_of("simulator groups", "are this flight in the simulation"),
    "aircraft": d.list_of("simulator units", "are this aircraft in the simulation"),
    "stand": d.list_of("parking positions in the simulator", "are this stand, for example `G03` in DCS"),
}


# ---- Subjects for generic templates ------------------------------------------------------------
MEASURE_SUBJECTS = {
    "measures/volume": "airspace coordination volume", "measures/route": "route", "measures/line": "coordination line",
    "measures/fire-support-line": "fire support line", "measures/area": "area", "measures/aor": "area of responsibility",
    "measures/kb": "kill box", "measures/mez": "missile engagement zone", "measures/cl": "coordination level or coordinating altitude",
    "measures/tl": "traverse level", "measures/aca": "airspace coordination area", "measures/isr": "identification safety range",
    "measures/misarc": "missile arc", "measures/orbit": "orbit", "measures/airspace": "airspace", "measures/point": "point",
}
GEOMETRY_SUBJECTS = {"Geometry_" + name: name.replace("_", " ") + " geometry" for name in (
    "point", "line", "polygon", "circle", "corridor", "racetrack", "track_racetrack", "sector", "polyarc", "figure_eight",
    "vertical", "rectangle", "ellipse")}
GEOMETRY_SUBJECTS["Geometry_description"] = "`description` geometry"
SUBJECTS = {
    **MEASURE_SUBJECTS, **GEOMETRY_SUBJECTS,
    "SimData": "simulator data", "DCSData": "DCS data", "DCSObjectRef": "DCS object reference", "DCSObjectRef.style": "display style", "control-measure": "control measure",
    "common": "definition", "TACAN": "TACAN channel", "DocumentRef": "document reference",
    "PinnedRef": "pinned reference", "ResourceRef": "resource reference", "Metadata": "document",
}


# ---- Shared measure fields -----------------------------------------------------------------------
def _measure_field(field, subject):
    """Standard text of a field that many measure schemas share."""
    table = {
        "active": lambda: d.window("this " + subject + " is active",
                                   "The value is an interval with a start and an end, a schedule for each week, "
                                   "or continuous activation"),
        "channels": lambda: d.references("communications channels of this " + subject),
        "controlling_agency": lambda: d.reference("agency", "controls the operations in this " + subject),
        "establishing_authority": lambda: d.reference("authority", "set this " + subject),
        "purpose": lambda: d.text("task or objective of this " + subject),
        "restrictions": lambda: d.list_of("conditions", "control the operations in this " + subject),
        "coordination_instructions": lambda: d.list_of(
            "instructions", "coordinate entry, operations and handover",
            "The instructions are for the agencies or forces that this " + subject + " has an effect on"),
    }
    if field in table:
        return table[field]()
    return GENERIC[field](subject)


def _measure_entries(context, binding, fields, specific):
    """Entries of one measure schema: the shared fields, the binding list, the kind constant and specific fields."""
    subject = MEASURE_SUBJECTS[context]
    entries = {(context, field): _measure_field(field, subject) for field in fields}
    entries.update({(context, field): text for field, text in specific.items()})
    return entries


def _root(code, *notes):
    """Root of a single-code measure schema: the catalogue name, the code and the definition."""
    entry = measure_definition(code)
    name = d.ACRONYMS.get(code) or technical_name(entry["name"])
    return d.root(name, code, entry["definition"], *notes)


SHARED = ("$schema", "id", "name", "notes", "description", "extensions", "resources_ref", "active")
COORDINATED = SHARED + ("coordination_instructions",)
CONTROLLED = COORDINATED + ("channels", "controlling_agency", "purpose", "restrictions")


def _kind(subject, *notes):
    return d.discriminator(subject, "The value selects the data contract of the control measure", *notes)


MEASURES = {}
MEASURES.update(_measure_entries("measures/volume", "area", CONTROLLED, {
    None: d.root("airspace coordination volume", None, "an airspace with a name and given dimensions, made of components in sequence",
                 "Each component has a horizontal boundary, a floor and a ceiling",
                 "The type is a code from NATO AJP-3.3.5 Annex B or from doctrine",
                 "The code gives the task of the volume and the airspace users that can or cannot go in it",
                 "The agency that controls the volume does the coordination of entry and operations"),
    "components": d.list_of("airspace components of the volume", None,
                            "Each component has a horizontal boundary, a floor and a ceiling", ordered=True),
    "type": MEASURE_TYPE,
}))
MEASURES.update(_measure_entries("measures/route", "route", CONTROLLED, {
    None: d.root("air route or corridor", None, "a centreline with points in sequence and with mandatory vertical limits",
                 "Corridor codes also have a lateral width",
                 "The type code gives the task of the route, and it tells if the route has air traffic services",
                 "It also gives the area that the route is for: a rear area, a forward area, a maritime force or a base defence zone",
                 "Aircraft can fly a corridor in the two directions, but not when its geometry has the `one_way` flag"),
    "altitude": d.altitude_block("the route or corridor"),
    "geometry": d.geometry("the route", "a centreline, or a corridor with its total lateral width",
                           d.enforced("When doctrine gives a code as a corridor, the code shall use the corridor geometry", "schema:then")),
    "type": MEASURE_TYPE,
}))
MEASURES.update(_measure_entries("measures/line", "line", COORDINATED + ("establishing_authority",), {
    None: d.root("coordination line", None, "a line on the ground, with points in sequence, for the coordination of manoeuvre "
                 "or identification",
                 "The line is the FLOT, the FEBA or a ground manoeuvre graphic",
                 "These graphics are the phase line, the boundary, the LOA, the LD and the LC",
                 "Other lines show where friendly aircraft set their IFF equipment to off or on"),
    "geometry": d.geometry("the line", "geographic positions in sequence"),
    "type": MEASURE_TYPE,
}))
MEASURES.update(_measure_entries("measures/fire-support-line", "line", COORDINATED + ("establishing_authority",), {
    None: d.root("fire support line", None, "one of four lines for the coordination of fires",
                 "The headquarters of a ground force, of an amphibious force or of the two forces together sets it",
                 "On the far side of a CFL, in the boundaries of its headquarters, standard indirect fires can "
                 "occur without more coordination",
                 "Other forces should coordinate their fires on the far side of an FSCL with its commander",
                 "An RFL between friendly forces that come together prevents fires and their effects across it "
                 "without coordination",
                 "Between a BCL and the FSCL, Marine aircraft can attack surface targets without approval from the "
                 "GCE commander"),
    "establishing_authority": d.reference("headquarters", "set the line"),
    "geometry": d.geometry("the line", "geographic positions in sequence"),
    "type": MEASURE_TYPE,
}))
MEASURES.update(_measure_entries("measures/area", "area", COORDINATED + ("restrictions",), {
    None: d.root("surface fire support or manoeuvre area", None,
                 "an area on the ground in two dimensions, with no vertical limits",
                 "The code `NFA` prevents fires and their effects, and with the code `FFA`, fires can occur without more coordination",
                 "With the code `RFA`, fires that do not obey the restrictions of the area can occur only with coordination",
                 "The code `EA` identifies the engagement area that the commander plans, and `AOA` identifies the amphibious "
                 "objective area",
                 "The codes `OBJ`, `BP`, `AA`, `NAI` and `TAI` identify ground manoeuvre graphics",
                 "The code `FSA` identifies a sea area for fire support ships"),
    "establishing_authority": d.reference("headquarters", "set the area"),
    "geometry": d.geometry("the area on the ground or at sea", "a polygon, or a radius from a centre point",
                           "The boundary follows terrain features that are easy to identify"),
    "restrictions": d.list_of("restrictions on fires or tasks", None,
                              d.enforced("An RFA shall give them", "schema:then")),
    "type": MEASURE_TYPE,
}))
MEASURES.update(_measure_entries("measures/aor", "area", SHARED, {
    None: _root("AOR", "The `responsible_agency` and `gates` fields are openAIX planning fields"),
    "gates": d.references("entry and exit gates of this area"),
    "geometry": d.geometry("the area of responsibility", "a polygon, a circle, a rectangle or an ellipse"),
    "responsible_agency": d.reference("agency", "controls this area"),
    "type": _kind("an area of responsibility"),
}))
MEASURES.update(_measure_entries("measures/kb", "area", CONTROLLED + ("establishing_authority",), {
    None: _root("KB", "The `killbox_kind` field gives the type, a blue kill box or a purple kill box, from FM 3-09 (2024), paragraph B-19",
                "The firing status `open` or `closed` comes from the assignments in the ACO, not from this record"),
    "components": d.list_of("airspace components of the kill box volume", None,
                            "A blue kill box starts at the surface or at its coordinating altitude",
                            "A purple kill box has a floor above the surface"),
    "grid_label": d.text("grid reference for display, such as a cell and a keypad label", "This field is optional",
                         "The components keep the coordinates in WGS 84 decimal degrees"),
    "killbox_kind": d.enum("type of kill box: a blue kill box or a purple kill box",
                           "A blue kill box lets aircraft attack surface targets, and it starts at the surface or at its "
                           "coordinating altitude",
                           "A purple kill box also lets surface units fire at surface targets, and it has an altitude floor"),
    "type": _kind("a kill box"),
    "coordinating_altitude": d.quantity("coordinating altitude of the kill box", "Altitude", None,
                                        "A blue kill box can start at this altitude, not at the surface",
                                        "The source is the multi-service procedures for the kill box (2009)"),
}))
MEASURES.update(_measure_entries("measures/mez", "area", CONTROLLED, {
    None: _root("MEZ", "The `mez_kind` field gives the type of zone from JP 3-01 (2012), V-11"),
    "components": d.list_of("airspace components of the engagement volume", None,
                            "The volume is a sector, or an area with a range and a bearing from the firing unit"),
    "mez_kind": d.enum("type of missile engagement zone, when the source gives it",
                       "The value is a HIMEZ, a LOMEZ or a SHORADEZ",
                       "Each of the catalogue codes `HIMEZ`, `LOMEZ` and `SHORADEZ` agrees with one of these values"),
    "type": _kind("a missile engagement zone", "The code `SAMEZ` in Table B-5 of NATO also agrees with this value"),
}))
MEASURES.update(_measure_entries("measures/cl", None, COORDINATED, {
    None: d.root("coordination level or coordinating altitude", None, "one altitude or height that divides airspace users",
                 "The code `CL` is the NATO coordination level, and the code `CA` is the coordinating altitude of JP 3-52",
                 "The record can identify the agencies that control the airspace below and above the level",
                 "The lateral limits come from text or from unit boundaries, not from this record"),
    "geometry": d.geometry("the coordination level", "one altitude or height", part="Vertical geometry"),
    "responsibility_above": d.reference("agency", "controls the airspace above the level"),
    "responsibility_below": d.reference("agency", "controls the airspace below the level"),
    "type": MEASURE_TYPE,
}))
MEASURES.update(_measure_entries("measures/tl", None, COORDINATED, {
    None: _root("TL", "The record gives the level as a height above the ground and as an altitude above mean sea level"),
    "geometry": d.geometry("the traverse level", "a height above the ground and an altitude above mean sea level",
                           part="Vertical geometry"),
    "type": _kind("a traverse level"),
}))
MEASURES.update(_measure_entries("measures/aca", "area", CONTROLLED + ("establishing_authority",), {
    None: _root("ACA"),
    "aca_kind": d.enum("type of ACA: `formal` or `informal`",
                       "In openAIX, an ACA of the type `formal` is a volume, and an ACA of the type `informal` gives only "
                       "its method of separation",
                       "The airspace control authority makes an ACA of the type `formal` when a component sends a request for it",
                       "It has altitudes, a baseline, a width and the times when it is active",
                       "In an ACA of the type `informal`, time, lateral distance or altitude gives the separation "
                       "between aircraft and surface fires",
                       "A battalion or a higher unit gives the approval for an ACA of the type `informal`"),
    "components": d.list_of("airspace components of the coordination volume", None,
                            "A formal ACA is usually a corridor component along its baseline, between the minimum and "
                            "maximum altitudes"),
    "separation": d.enum("method of separation between aircraft and surface fires in an informal ACA"),
    "type": _kind("an airspace coordination area"),
}))
MEASURES.update(_measure_entries("measures/isr", "area", COORDINATED + ("establishing_authority", "restrictions"), {
    None: _root("ISR", "The range moves with the maritime force",
                "A record can give a circle geometry for display at a specified time"),
    "establishing_authority": d.reference("officer in tactical command", "set the range"),
    "geometry": d.geometry("the range", "an optional circle around the position of the force at a specified time, for display",
                           "When the two do not agree, the `range` value is correct"),
    "range": d.quantity("identification safety range", "Length", None,
                        "An aircraft may close to this range from the force without positive identification as a friendly aircraft"),
    "reference_force": d.statement("This field gives the name of the maritime force at the centre of the range"),
    "reference_position": d.position("the maritime force at the time when the range starts",
                                     "The record gives it only when the position is known"),
    "type": _kind("an identification safety range"),
}))
MEASURES.update(_measure_entries("measures/misarc", "area", COORDINATED + ("controlling_agency", "restrictions"), {
    None: _root("MISARC", "The arc has its centre on the firing unit, and its axis is the bearing of the target",
                "Its width is 10 degrees by default, and its range is the maximum range of the surface-to-air missile"),
    "altitude": d.altitude_block("the arc", "This field is optional"),
    "axis": d.quantity("bearing of the target from the firing unit", "Bearing", None, "The arc has its centre on this bearing"),
    "center": d.position("the firing unit at the centre of the arc"),
    "firing_unit": d.statement("This field gives the name of the ship or unit that fires the surface-to-air missile"),
    "range": d.quantity("maximum range of the surface-to-air missile", "Length"),
    "width_deg": d.quantity("total angular width of the arc, with the axis at its centre", None, "degrees",
                            "The width is 10 degrees, but the officer in tactical command can give an order for a different width"),
    "type": _kind("a missile arc"),
}))
MEASURES.update(_measure_entries("measures/orbit", "orbit", CONTROLLED, {
    None: d.root("orbit", None, "a flight pattern with an altitude block and the times when it is active",
                 "More than one assignment can use the same orbit",
                 "An ACO assignment gives the mission role: CAP, AEW, air-to-air refuelling or holding",
                 "The orbit has no role"),
    "altitude": d.altitude_block("the orbit", "The block gives the altitudes that aircraft can use"),
    "geometry": d.geometry("the flight pattern", None,
                           "A racetrack has an anchor, a radial, a turn direction and a straight-leg length",
                           "A point, a line or a text geometry can record a pattern, but more data is necessary to fly it"),
    "purpose": d.text("general task of the orbit"),
    "type": d.discriminator("an orbit", "The value is the same for all orbits, and the mission of an assignment does not change it"),
}))
MEASURES.update(_measure_entries("measures/airspace", "area", CONTROLLED, {
    None: d.root("airspace", None, "a region of airspace with a name, made of volumes that each have a horizontal boundary "
                 "and vertical limits",
                 "The `airspace_type` field gives the class or the type of operation",
                 "Shelves, sectors and subtracted volumes use the same structure of components",
                 "The control measures for air traffic in Annex B use this contract",
                 "Examples are class B airspace, control zones and restricted areas"),
    "airspace_type": d.enum("class or type of operation of the airspace, such as `ClassB`, `ClassD`, `MTA` or `TMA`",
                            "`MTA` is a military training area, and `TMA` is a terminal control area"),
    "airspace_class_code": d.enum("airspace class that the source gives", "When the code is empty, the source gives no class",
                                  "All classes use the same structure for geometry and altitude"),
    "components": d.list_of("airspace volumes of this airspace", None, "Each volume has a floor and a ceiling", ordered=True),
    "designator": d.statement("This field gives the designator that a publication or an assignment gives to the airspace",
                              "An example is the designator of a restricted area"),
    "local_type": d.text("local type name of the airspace when `airspace_type` is `Other`"),
    "type": d.discriminator("an airspace, which is a region made of airspace volumes"),
}))
MEASURES.update(_measure_entries("measures/point", "point", COORDINATED + ("channels", "restrictions"), {
    None: d.root("point", None, "a position with a name, for navigation or control",
                 "The roles tell how aircraft use the point, for example for ingress, egress, initial approach, contact "
                 "point and handover",
                 "The air reference points of Annex B (`ACP`, `CP`, `EG`, `HG`, `MG`, `ISP`) are points with the applicable role",
                 "The initial point, the bullseye, a target reference point and a fire support station are also points with "
                 "the applicable role"),
    "aor": d.reference("area of responsibility", "this gate is for"),
    "contact_agency": d.reference("agency", "aircraft speak to at this point"),
    "handover_agency": d.reference("agency", "controls the aircraft after this gate"),
    "instructions": d.list_of("instructions for operations at this point"),
    "position": d.position("the point"),
    "reference_agency": d.reference("agency for this point or line"),
    "roles": d.list_of("roles of this point in operations", None, "One point can have more than one role"),
    "route": d.reference("route of this task or connection"),
    "type": d.discriminator("a point control measure", "This value is the same for all roles of a point"),
}))


# ---- Common primitives ---------------------------------------------------------------------------
WINDOW_LIMIT = "The value is an absolute date-time or an offset from the period of the order that contains it"
ABSOLUTE = "The value is an absolute date-time"
NO_LIMIT = "an altitude with its reference, or no limit"

COMMON = {
    ("common", None): d.root("definitions for all openAIX documents", None,
                             "the identifiers, positions, geometry, units, time intervals and resource references that "
                             "more than one type of document contains"),
    ("control-measure", None): d.root("control measure", None,
                                      "one of the openAIX control measure contracts, and its type selects the contract"),

    ("Activation", None): d.entity("Activation", "the time when a control measure is available",
                                   "It is an interval, a UTC schedule for each week in an interval, or continuous activation"),
    ("Activation", "continuous"): d.flag("the control measure is active all the time, with no scheduled period in which "
                                         "it is not active"),

    ("AirspaceComponent", None): d.entity("Airspace component",
                                          "one part of an airspace in three dimensions, with a boundary, a floor and a ceiling",
                                          "Each component adds a volume, subtracts a volume or intersects a volume, in sequence"),
    ("AirspaceComponent", "active"): d.window("this component is available, in the time interval of the parent control "
                                              "measure", "This field is optional"),
    ("AirspaceComponent", "geometry"): d.geometry("this component", "points, distances and bearings in a format for a simulator",
                                                  part="Horizontal boundary"),
    ("AirspaceComponent", "id"): d.identifier("component", "its parent airspace"),
    ("AirspaceComponent", "lower_limit"): d.vertical_limit("floor", "this component"),
    ("AirspaceComponent", "upper_limit"): d.vertical_limit("ceiling", "this component", NO_LIMIT),
    ("AirspaceComponent", "maximum_limit"): d.quantity("maximum limit of this component", "Altitude", None,
                                                       "Where this value is higher than `upper_limit`, it increases the ceiling",
                                                       "Each value keeps its reference"),
    ("AirspaceComponent", "minimum_limit"): d.quantity("minimum floor of this component", "Altitude", None,
                                                       "Where this value is higher than `lower_limit`, it replaces the floor",
                                                       "To compare limits with different references, a consumer uses terrain or "
                                                       "atmospheric data"),
    ("AirspaceComponent", "name"): d.name("sector or shelf"),
    ("AirspaceComponent", "operation"): d.enum("operation of this component on the volume that the components before it make",
                                               "The components operate in the sequence of the array, and the first "
                                               "component adds a volume"),

    ("Altitude", None): d.entity("Altitude", "A vertical position with its unit and its reference: MSL, AGL or FL"),
    ("AltitudeBlock", None): d.entity("Altitude block", "a vertical band between a floor and a ceiling",
                                      "The floor can be the surface, and the ceiling can have no limit"),
    ("Bearing", None): d.entity("Bearing", "a direction with its value and its north reference: true north or magnetic north",
                                "A magnetic bearing keeps the reference that its author gives", "The declination is optional",
                                "When the declination is not available, a consumer should show that it cannot change the "
                                "bearing to true north"),
    ("ClassificationLevel", None): d.entity("Classification level",
                                            "a security classification of the American government that the banner of an "
                                            "OPORD can show"),

    ("ControlMeasure", None): d.entity("Control measure", "one openAIX control measure: a reference to one control measure "
                                       "contract, or an extension control measure with a namespace",
                                       "The `type` field selects the contract"),
    ("ControlMeasure", "$schema"): GENERIC["$schema"]("extension control measure"),
    ("ControlMeasure", "active"): d.window("the extension control measure is available",
                                          "The value is a schedule or a flag for continuous activation"),
    ("ControlMeasure", "description"): GENERIC["description"]("extension control measure"),
    ("ControlMeasure", "extensions"): GENERIC["extensions"]("extension control measure"),
    ("ControlMeasure", "geometry"): d.geometry("the extension control measure", "a position or a boundary",
                                               "The geometry uses points, distances and bearings in a format for a simulator"),
    ("ControlMeasure", "id"): GENERIC["id"]("extension control measure"),
    ("ControlMeasure", "name"): GENERIC["name"]("extension control measure"),
    ("ControlMeasure", "notes"): GENERIC["notes"]("extension control measure"),
    ("ControlMeasure", "resources_ref"): GENERIC["resources_ref"]("extension control measure"),
    ("ControlMeasure", "type"): d.statement("This field gives the type of the extension control measure, as a name with a "
                                            "namespace"),
    ("ControlMeasureSelection", "id"): d.reference("control measure of this selection"),

    ("Extensions", "sim"): d.statement("This field contains the simulator data of the record, with the simulator identifier as the key"),
    ("SimData", "dcs"): d.statement("This field contains the DCS data of the record"),
    ("SimData", None): d.entity("simulator data", "the data of a record for each simulator, with the simulator identifier as the key, "
                                "for example `dcs`",
                                "The other fields of the record do not change with a simulator",
                                "The DCS data has fixed fields, and the data of a different simulator is an object with no fixed fields"),
    ("DCSData", None): d.entity("DCS data", "the data of a record for DCS",
                                "The `bindings` field contains the objects in a DCS mission that are this record or that show it",
                                "The other fields contain DCS values that are not objects of a mission"),
    ("DCSData", "bindings"): d.list_of("objects in a DCS mission", "are this record or show it on the map",
                                       "The record keeps its geometry in latitude and longitude, independently of these objects"),
    ("DCSData", "objects"): d.list_of("units, groups or static objects in a DCS mission", "are parts of the aimpoint"),
    ("DCSData", "type"): d.statement("This field gives the DCS type name of the aircraft type, for example `F-16C_50`"),
    ("DCSData", "clsids"): d.list_of("DCS class identifiers (CLSID)", "agree with this store"),
    ("DCSData", "payload"): d.statement("This field identifies the load in the `UnitPayloads` file of the aircraft that agrees with this SCL"),
    ("DCSData.payload", "name"): d.statement("This field gives the name of the load in the `UnitPayloads` file"),
    ("DCSData.payload", "unit_type"): d.statement("This field gives the DCS type name of the aircraft of the load"),
    ("DCSData.payload", "task_ids"): d.list_of("DCS task numbers of the load", None,
                                               "The mission editor shows the load for these tasks, for example `31` for CAS"),
    ("DCSData", "pylon"): d.statement("This field gives the DCS pylon number of this station"),
    ("DCSData", "label"): d.statement("This field gives the label of the pylon in the mission editor"),
    ("DCSData", "clsid"): d.statement("This field gives the DCS class identifier (CLSID) of the load on the pylon",
                                      "For a rack, the CLSID identifies the rack together with its stores"),
    ("DCSData", "settings"): d.statement("This field contains the values of the pylon in the mission editor, such as the fuze values",
                                         "The record keeps them for round trips"),
    ("DCSData", "alic_code"): d.statement("This field gives the DCS ALIC code of the radar", "The HARM of the DCS F-16C uses this code",
                                          "Appendix B of the `DCS F-16C Early Access Guide` gives the codes"),
    ("DCSData", "angle_deg"): d.quantity("drawing angle from the DCS mission", None, "degrees",
                                         "This angle is not a true bearing or a magnetic bearing",
                                         "Only a consumer with a correct adapter for DCS should use this angle to turn the shape"),
    ("DCSData", "projection"): d.reference("theatre projection of DCS", "gives the dimensions and the drawing angle"),
    ("DCSObjectRef", None): d.entity("DCS object reference", "a link to one object in a DCS mission",
                                     "The record that contains this reference keeps its geometry in latitude and longitude, "
                                     "independently of this identifier"),
    ("DCSObjectRef", "name"): d.name("DCS object"),
    ("DCSObjectRef", "mission_id"): d.statement("This field identifies the mission in which a consumer resolves names and "
                                                "number identifiers", "This field is optional"),
    ("DCSObjectRef", "angle_deg"): d.quantity("DCS angle of a point or circle drawing", None, "degrees",
                                              "The angle is not a true bearing"),
    ("DCSObjectRef", "icon"): d.statement("This field gives the DCS identifier of the icon file"),
    ("DCSObjectRef", "layer"): d.statement("This field gives the drawing layer in the mission editor, such as `Blue` or `Author`"),
    ("DCSObjectRef", "native_fields"): d.statement("This field contains the attributes from DCS that have no typed field",
                                                   "The record keeps them for round trips",
                                                   d.enforced("A typed field for identifiers, geometry or style shall not go "
                                                              "in this object", "schema:propertyNames")),
    ("DCSObjectRef", "style"): d.statement("This field contains display attributes from the mission editor, when they are known",
                                           "The geometry does not change with them"),
    ("DCSObjectRef.style", "color"): d.statement("This field gives the DCS colour of the line or text in the format `0xRRGGBBAA`",
                                                 "The format gives the red value, green value, blue value and alpha"),
    ("DCSObjectRef.style", "fill_color"): d.statement("This field gives the DCS fill colour in the format `0xRRGGBBAA`",
                                                      "The format gives the red value, green value, blue value and alpha"),
    ("DCSObjectRef", "unit_type"): d.statement("This field gives the DCS type name of the unit or the static object, when known"),
    ("DCSObjectRef", "zone_type"): d.enum("DCS type of the trigger zone",
                                          "The value `circle` is zone type 0, and the value `quad` is zone type 2"),

    ("DateTime", None): d.entity("Date-time", "an RFC 3339 date-time with a UTC designator or an offset from UTC, "
                                 "such as `2026-10-02T06:00:00Z`"),
    ("DocumentRef", None): d.entity("Document reference", "a document that a record refers to",
                                    "Consumers do not get the document automatically through a network"),
    ("DocumentRef", "id"): d.reference("document", "the record refers to"),
    ("Frequency", None): d.entity("Frequency", "a radio frequency in kilohertz or megahertz",
                                  "The modulation is AM or FM", "The modulation and the radio band are optional"),
    ("Coalition", None): d.entity("Coalition", "the side of a record in the simulation: `blue`, `red` or `neutral`"),
    ("GeoPoint", None): d.entity("Geographic point", "a position in WGS 84 decimal degrees",
                                 "An adapter is necessary for the Cartesian coordinates of a simulator"),
    ("GeoPoint", "latitude"): d.quantity("latitude north of the equator", None, "decimal degrees",
                                         "A south latitude is a negative value"),
    ("GeoPoint", "longitude"): d.quantity("longitude east of Greenwich", None, "decimal degrees",
                                          "A west longitude is a negative value"),

    ("Geometry_circle", None): d.entity("Circle geometry", "A horizontal disc with a centre and a radius"),
    ("Geometry_circle", "center"): d.position("the centre of the circle"),
    ("Geometry_circle", "radius"): d.quantity("horizontal distance from the centre to the boundary", "Length"),
    ("Geometry_corridor", None): d.entity("Corridor geometry", "A route centreline with a total lateral width"),
    ("Geometry_corridor", "one_way"): d.flag("aircraft fly the corridor only in the sequence of its points",
                                             "aircraft fly the corridor in the two directions"),
    ("Geometry_corridor", "width"): d.quantity("total lateral width of the corridor, with the centreline at its centre", "Length"),
    ("Geometry_description", None): d.entity("`description` geometry",
                                             "a text that gives a geographic position or an area, with no coordinates"),
    ("Geometry_ellipse", None): d.entity("Ellipse geometry", "an ellipse with a centre in latitude and longitude and "
                                         "with dimensions in metres", "It is not a polygon of sample points",
                                         "A DCS drawing keeps its angle and its theatre projection in `extensions.sim.dcs`"),
    ("Geometry_ellipse", "center"): d.position("the centre of the ellipse"),
    ("Geometry_ellipse", "east_radius_m"): d.quantity("east radius before a simulator turns the drawing", None, "metres"),
    ("Geometry_ellipse", "north_radius_m"): d.quantity("north radius before a simulator turns the drawing", None, "metres"),
    ("Geometry_rectangle", None): d.entity("Rectangle geometry", "a rectangle with a centre in latitude and longitude "
                                           "and with dimensions in metres", "It is not a polygon of sample points",
                                           "A DCS drawing keeps its angle and its theatre projection in `extensions.sim.dcs`"),
    ("Geometry_rectangle", "center"): d.position("the centre of the rectangle"),
    ("Geometry_rectangle", "width_m"): d.quantity("width before a simulator turns the drawing", None, "metres"),
    ("Geometry_rectangle", "height_m"): d.quantity("height before a simulator turns the drawing", None, "metres"),
    ("Geometry_figure_eight", None): d.entity("Figure-eight geometry", "a figure-eight flight pattern with an anchor, "
                                              "an axis, a leg length and a turn radius"),
    ("Geometry_figure_eight", "leg_length"): d.quantity("length of each straight leg, without the turns", "Length"),
    ("Geometry_figure_eight", "turn_radius"): d.quantity("radius of the turns of the flight pattern, when given", "Length"),
    ("Geometry_line", None): d.entity("Line geometry", "a sequence of geographic positions that makes an open line"),
    ("Geometry_point", None): d.entity("Point geometry", "One geographic position"),
    ("Geometry_point", "position"): d.position("the point"),
    ("Geometry_polyarc", None): d.entity("Polyarc geometry",
                                         "a horizontal boundary of straight segments and circular-arc segments in sequence"),
    ("Geometry_polyarc.segments", "start"): d.position("the start of the boundary segment"),
    ("Geometry_polyarc.segments", "end"): d.position("the end of the boundary segment"),
    ("Geometry_polyarc.segments", "center"): d.position("the centre of the arc"),
    ("Geometry_polyarc.segments", "radius"): d.quantity("radius of the arc", "Length"),
    ("Geometry_polyarc.segments", "turns"): d.enum("direction of the arc from its start to its end",
                                                   "With the value `left`, the arc turns to the left side, and with "
                                                   "`right`, it turns to the right side"),
    ("Geometry_polygon", None): d.entity("Polygon geometry", "A closed horizontal boundary",
                                         "The first ring is the external boundary, and the next rings are holes"),
    ("Geometry_polygon", "rings"): d.list_of("closed rings of positions", None,
                                             "The external boundary is first, and the holes come after it", ordered=True),
    ("Geometry_racetrack", None): d.entity("Racetrack geometry", "A racetrack with an anchor, an outbound radial, "
                                           "a turn direction and a straight-leg length"),
    ("Geometry_racetrack", "leg_length"): d.quantity("length of each straight leg, without the turns", "Length"),
    ("Geometry_racetrack", "radial"): d.quantity("outbound bearing from the anchor", "Bearing", None,
                                                 "The reference is always given: true north or magnetic north",
                                                 "The reciprocal course is the course of the inbound leg"),
    ("Geometry_racetrack", "turn_radius"): d.quantity("radius of the turns of the flight pattern, when given", "Length"),
    ("Geometry_racetrack", "turns"): d.enum("direction of the turns around the flight pattern"),
    ("Geometry_sector", None): d.entity("Sector geometry", "a horizontal sector with a centre, a start bearing, an end bearing, "
                                        "and an inner and an outer radius"),
    ("Geometry_sector", "center"): d.position("the centre of the sector"),
    ("Geometry_track_racetrack", None): d.entity("Track racetrack geometry", "A racetrack with two end anchors, "
                                                 "a lateral width and a turn direction"),
    ("Geometry_track_racetrack", "turns"): d.enum("direction of the turns around the flight pattern"),
    ("Geometry_track_racetrack", "width"): d.quantity("horizontal width of the racetrack", "Length"),
    ("Geometry_vertical", None): d.entity("Vertical geometry", "a coordination level, or the two values of a traverse level",
                                          "The values of a traverse level are a height above the ground and an altitude "
                                          "above mean sea level"),
    ("Geometry_vertical", "altitude"): d.quantity("altitude of the traverse level above mean sea level", "Altitude"),

    ("LaserCode", None): d.entity("Laser code", "a code of four digits for the PRF of a laser, from `1111` to `1788`",
                                  "The second digit is 1 to 7, and the last two digits are 1 to 8"),
    ("Length", None): d.entity("Length", "A horizontal distance or dimension with its unit: metres, feet, nautical miles or kilometres"),
    ("Metadata", "id"): GENERIC["id"]("document"),
    ("Offset", None): d.entity("Offset", "a number of minutes from the start of the period of the ATO that contains it",
                               "The value can be less than zero"),
    ("Period", None): d.entity("Period", "a time interval between two absolute date-times in the RFC 3339 format"),
    ("Period", "start"): d.time("the start of the period", ABSOLUTE),
    ("Period", "end"): d.time("the end of the period", ABSOLUTE),
    ("PinnedRef", None): d.entity("Pinned reference", "a dependency on a local document that consumers examine by identifier "
                                  "and revision"),
    ("PinnedRef", "id"): d.reference("local document of this dependency"),
    ("PointLocation", None): d.entity("Point location", "a geographic point, a location in free text, or the two"),
    ("PointLocation", "position"): d.position("the point"),
    ("PointLocation", "position_description"): d.text("location", "The text is for a location without accurate coordinates, "
                                                      "or it gives more information about the coordinates"),
    ("ResourceRef", "id"): d.reference("external resource catalogue"),
    ("RunwayDesignator", None): d.entity("Runway designator",
                                         "the magnetic heading of the runway in units of 10 degrees, from `01` to `36`",
                                         "A suffix can follow: `L`, `R` or `C` for left, right or centre, or `W` for water",
                                         "Other suffixes are `S` for STOL, `G` for glider and `U` for ultralight aircraft"),
    ("ScheduledWindow", None): d.entity("Scheduled window", "a time interval between two absolute date-times, with a UTC "
                                        "schedule for each week in it"),
    ("ScheduledWindow", "start"): d.time("the start of the interval", ABSOLUTE),
    ("ScheduledWindow", "end"): d.time("the end of the interval", ABSOLUTE),
    ("Speed", None): d.entity("Speed", "a speed with its unit: knots, Mach number or kilometres in one hour"),
    ("TACAN", None): d.entity("Tactical Air Navigation", "The channel, band and identifier of a TACAN station", abbr="TACAN"),
    ("VerticalLimit", None): d.entity("Vertical limit", "a floor or a ceiling: an altitude with its reference, the surface, "
                                      "or no limit",
                                      "The surface is below all altitudes, and the value `unlimited` is above all altitudes"),
    ("WeeklyPeriod", "weekdays"): d.list_of("UTC weekdays on which this period starts"),
    ("WeeklyPeriod", "start_time"): d.time("the start of the period, in UTC, as `HH:MM:SS`", "The period includes the start time"),
    ("WeeklyPeriod", "end_time"): d.time("the end of the period, in UTC, as `HH:MM:SS`",
                                         "The period does not include the end time"),
    ("WeeklyPeriod", "end_day_offset"): d.enum("day on which the period stops",
                                               "With the value `0`, the period stops on its start day, and with `1`, it "
                                               "stops on the next day"),
    ("WeeklySchedule", None): d.entity("Schedule for each week", "the UTC times in the week when something is available, in the "
                                       "interval that contains it",
                                       "The intervals in `exclusions` are not part of the schedule"),
    ("WeeklySchedule", "exclusions"): d.list_of("time intervals with absolute date-times", "the schedule subtracts from its "
                                                "periods"),
    ("WeeklySchedule.exclusions", "start"): d.time("the start of the interval that the schedule does not include", ABSOLUTE),
    ("WeeklySchedule.exclusions", "end"): d.time("the end of the interval that the schedule does not include", ABSOLUTE),
    ("Window", None): d.entity("Window", "a time interval with limits that are absolute date-times or offsets from the "
                               "period of the order that contains it"),
    ("Window", "start"): d.time("the start of the interval", WINDOW_LIMIT),
    ("Window", "end"): d.time("the end of the interval", WINDOW_LIMIT),
}

# ---- Fields of common primitives, geometry kinds and references --------------------------------
def _geometry_kind(shape, value):
    return d.discriminator("a " + shape + " geometry", "The value is `" + value + "`")


PRIMITIVE_FIELDS = {
    ("Altitude", "value"): d.statement("This field gives the value of the altitude, in the unit of `unit`"),
    ("Altitude", "unit"): d.enum("unit of the altitude: feet, metres or flight level"),
    ("Altitude", "reference"): d.enum("vertical reference of the altitude", "The value is MSL, AGL or FL"),
    ("AltitudeBlock", "lower"): d.vertical_limit("floor", "the altitude block"),
    ("AltitudeBlock", "upper"): d.vertical_limit("ceiling", "the altitude block", NO_LIMIT),
    ("Bearing", "value"): d.statement("This field gives the value of the bearing, in degrees from 0 to less than 360"),
    ("Bearing", "reference"): d.enum("north reference of the bearing: true north or magnetic north"),
    ("Bearing", "declination_deg"): d.quantity("magnetic declination that changes a bearing from true north to magnetic north",
                                               None, "degrees", "This field is optional"),
    ("Elevation", "value"): d.statement("This field gives the value of the elevation, in the unit of `unit`"),
    ("Elevation", "unit"): d.enum("unit of the elevation: feet or metres"),
    ("Elevation", "reference"): d.statement("This field gives the vertical reference of the elevation", "The value is always `MSL`"),
    ("Frequency", "value"): d.statement("This field gives the value of the frequency, in the unit of `unit`"),
    ("Frequency", "unit"): d.enum("unit of the frequency: kilohertz or megahertz"),
    ("Frequency", "modulation"): d.enum("modulation of the radio frequency: AM or FM", "This field is optional"),
    ("Frequency", "band"): d.enum(
        "radio band of the frequency",
        d.enforced("The band shall agree with the value of the frequency", "validator:openaix.check.navigation.frequency_band"),
        "The limits are 2 to 30 MHz for HF, and 30 to 88 MHz for FM",
        "The limits are 108 to 174 MHz for VHF, and 225 to 400 MHz for UHF"),
    ("Length", "value"): d.statement("This field gives the value of the length, in the unit of `unit`"),
    ("Length", "unit"): d.enum("unit of the length: metres, feet, nautical miles or kilometres"),
    ("Speed", "value"): d.statement("This field gives the value of the speed, in the unit of `unit`"),
    ("Speed", "unit"): d.enum("unit of the speed: knots, Mach number or kilometres in one hour"),
    ("Offset", "offset_minutes"): d.quantity("time from the start of the period of the ATO that contains it", None, "minutes",
                                             "A negative value is before the start of the period"),
    ("TACAN", "channel"): d.statement("This field gives the channel number of the station, from 1 to 126"),
    ("TACAN", "band"): d.enum("band of the channel: `X` or `Y`"),
    ("TACAN", "identifier"): d.identifier("station"),
    ("ScheduledWindow", "schedule"): d.statement("This field gives the UTC schedule for each week in the interval"),
    ("WeeklySchedule", "periods"): d.list_of("time intervals in each week"),
    ("WeeklySchedule", "time_reference"): d.statement("This field gives the time reference of the schedule",
                                                      "The value is always `UTC`"),
    ("ControlMeasureSelection", "kind"): d.discriminator("a control measure selection", "The value is `control_measure`"),

    ("DocumentRef", "path"): d.statement("This field gives the file path of the document"),
    ("DocumentRef", "revision"): d.statement("This field gives the revision of the document"),
    ("DocumentRef", "section"): d.statement("This field gives the part of the document that the record refers to, such as a "
                                            "section or a paragraph"),
    ("DocumentRef", "title"): d.statement("This field gives the title of the document"),
    ("PinnedRef", "path"): d.statement("This field gives the file path of the local document"),
    ("PinnedRef", "revision"): d.statement("This field gives the revision of the local document",
                                           "Consumers examine this revision"),
    ("ResourceRef", "revision"): d.statement("This field gives the revision of the external resource catalogue"),

    ("Metadata", "author"): d.statement("This field gives the name of the author of the document"),
    ("Metadata", "classification"): d.enum("security classification of the document"),
    ("Metadata", "coalition"): d.enum("coalition of the document: `blue`, `red` or `neutral`"),
    ("Metadata", "distribution"): d.list_of("addressees that receive the document"),
    ("Metadata", "issued_at"): d.time("issue of the document"),
    ("Metadata", "issuing_unit"): d.statement("This field gives the name of the unit that publishes the document"),
    ("Metadata", "operation"): d.statement("This field gives the name of the operation that the document is for"),
    ("Metadata", "references"): d.list_of("documents", "this document refers to"),
    ("Metadata", "revision"): d.statement("This field gives the revision of the document"),
    ("Metadata", "supersedes"): d.statement("This field identifies the document that this document replaces"),
    ("Metadata", "title"): d.statement("This field gives the title of the document"),

    ("FixedSelection", "kind"): d.discriminator("a selection of a fixed target", "The value is `fixed`"),
    ("FixedSelection", "target"): d.reference("fixed target", "this selection names"),
    ("FixedSelection", "aimpoints"): d.references("aimpoint entries", "this selection names on the fixed target"),

    ("DCSObjectRef", "kind"): d.enum("type of the DCS object", "The types are units, groups, static objects, "
                                     "`scenery` objects, airbases, parking stands, drawings and trigger zones"),
    ("DCSObjectRef", "object_id"): d.statement("This field gives the DCS number that identifies the object in the mission"),
    ("DCSObjectRef", "group_category"): d.enum("class of the group: `airplane`, `helicopter`, `vehicle`, `ship` or `train`"),
    ("DCSObjectRef", "primitive_type"): d.enum("drawing primitive in DCS", "The value is a polygon, a line, a text box or an icon"),
    ("DCSObjectRef", "polygon_mode"): d.enum("mode of a polygon drawing in DCS"),
    ("DCSObjectRef", "line_mode"): d.enum("mode of a line drawing in DCS"),
    ("DCSObjectRef", "closed"): d.flag("the line drawing is a closed shape", "the line drawing is an open line"),
    ("DCSObjectRef", "text"): d.text("text of a text box drawing"),
    ("DCSObjectRef.style", "font_size"): d.statement("This field gives the font size of the text in DCS"),
    ("DCSObjectRef.style", "thickness"): d.statement("This field gives the width of the line in DCS"),
    ("DCSObjectRef.style", "visible"): d.flag("the drawing shows on the map", "the drawing does not show on the map"),

    ("Geometry_circle", "kind"): _geometry_kind("circle", "circle"),
    ("Geometry_corridor", "kind"): _geometry_kind("corridor", "corridor"),
    ("Geometry_corridor", "points"): d.list_of("geographic positions of the centreline", None, "The first position is the start",
                                               ordered=True),
    ("Geometry_description", "kind"): _geometry_kind("`description`", "description"),
    ("Geometry_description", "text"): d.text("geographic position or area"),
    ("Geometry_ellipse", "kind"): _geometry_kind("ellipse", "ellipse"),
    ("Geometry_figure_eight", "kind"): _geometry_kind("figure-eight", "figure_eight"),
    ("Geometry_figure_eight", "point"): d.position("the anchor of the flight pattern"),
    ("Geometry_figure_eight", "axis"): d.quantity("direction of the axis of the flight pattern from its anchor", "Bearing"),
    ("Geometry_line", "kind"): _geometry_kind("line", "line"),
    ("Geometry_line", "points"): d.list_of("geographic positions of the open line", None, "The first position is the start",
                                           ordered=True),
    ("Geometry_point", "kind"): _geometry_kind("point", "point"),
    ("Geometry_polyarc", "kind"): _geometry_kind("polyarc", "polyarc"),
    ("Geometry_polyarc", "segments"): d.list_of("straight segments and circular-arc segments", "make the boundary",
                                                ordered=True),
    ("Geometry_polyarc.segments", "kind"): d.discriminator("a boundary segment",
                                                           "The value is `line` for a straight segment and `arc` for an arc"),
    ("Geometry_polyarc.segments", "start_bearing"): d.quantity("bearing from the centre to the start of the arc", "Bearing"),
    ("Geometry_polyarc.segments", "end_bearing"): d.quantity("bearing from the centre to the end of the arc", "Bearing"),
    ("Geometry_polygon", "kind"): _geometry_kind("polygon", "polygon"),
    ("Geometry_racetrack", "kind"): _geometry_kind("racetrack", "racetrack"),
    ("Geometry_racetrack", "point"): d.position("the anchor of the racetrack"),
    ("Geometry_rectangle", "kind"): _geometry_kind("rectangle", "rectangle"),
    ("Geometry_sector", "kind"): _geometry_kind("sector", "sector"),
    ("Geometry_sector", "start_bearing"): d.quantity("bearing of the first side of the sector, from its centre", "Bearing"),
    ("Geometry_sector", "end_bearing"): d.quantity("bearing of the second side of the sector, from its centre", "Bearing"),
    ("Geometry_sector", "inner_radius"): d.quantity("inner radius of the sector", "Length"),
    ("Geometry_sector", "outer_radius"): d.quantity("outer radius of the sector", "Length"),
    ("Geometry_track_racetrack", "kind"): _geometry_kind("track racetrack", "track_racetrack"),
    ("Geometry_track_racetrack", "a"): d.position("the first end anchor of the racetrack"),
    ("Geometry_track_racetrack", "b"): d.position("the second end anchor of the racetrack"),
    ("Geometry_vertical", "kind"): _geometry_kind("vertical", "vertical"),
    ("Geometry_vertical", "height"): d.quantity("height of the traverse level above the ground", "Altitude"),
    ("VerticalLimit", "surface"): d.flag("the limit is the surface", None, "The value is always `true`",
                                         "The surface is below all altitudes"),
    ("VerticalLimit", "unlimited"): d.flag("the limit has no maximum", None, "The value is always `true`",
                                           "This limit is above all altitudes"),
    ("Geometry_vertical", "level"): d.quantity("altitude of the coordination level", "Altitude"),

    ("measures/point", "position_description"): COMMON[("PointLocation", "position_description")],
}
for _schema in ("ato", "resources"):
    PRIMITIVE_FIELDS[(_schema + ":Speed", "unit")] = d.enum(
        "unit of the speed: knots, kilometres in one hour or Mach number",
        "The suffix `_ias` identifies an IAS, and the suffix `_tas` identifies a TAS")


DESCRIPTIONS = {**COMMON, **PRIMITIVE_FIELDS, **MEASURES}


# ---- catalogues/airspace-types.json: the catalogue description and one description per airspace type ----
AIRSPACE_TYPES_DESCRIPTION = d.statement("This catalogue gives the names of airspace types for openAIX authors",
                                         "AIXM is only a reference for the names",
                                         "These names are not AIXM wire codes")
# Airspace types that a catalogue code defines. The enumerated value uses the definition of that code, so the
# schema and the control-measure catalogue agree. Extra sentences come from ICAO Annex 11, paragraph 2.5.2.2.
CONTROLLED = "ATC gives ATC service to IFR flights in it. Its ICAO class sets the ATC service for VFR flights"
AIRSPACE_TYPE_CODES = {
    "CTA": ("CTA", CONTROLLED), "CTR": ("CTZ", CONTROLLED), "TMA": ("TCA", CONTROLLED), "FIR": ("FIR", None),
    "Danger": ("DA", None), "Restricted": ("RA", None), "Prohibited": ("PROHIB", None), "ROZ": ("ROZ", None),
    "TRA": ("TRA", None), "TSA": ("TSA", None), "ADIZ": ("ADIZ", None),
    "MTA": ("TRNG", "AJP-3.3.5 gives this area as the training area (TRNG)"),
}
AIRSPACE_TYPE_NAMES = {"Danger": "danger area", "Restricted": "restricted area", "Prohibited": "prohibited area"}
AIRSPACE_TYPE_VALUES = {
    "Other": d.value_sentence("The airspace has a local type that is not in this list",
                              "The `local_type` field gives the local name of the type"),
}


def airspace_type_source(name):
    """The source-table row of an airspace type, or None for a type without one."""
    return MEASURE_SOURCE.get("airspace_types", {}).get(name)


def airspace_type_note(name):
    note = airspace_type_source(name).get("note")
    return d.statement(note) if note else None


def _airspace_type_value(name, label, definition, *notes):
    sentences = d.sentences(definition)
    return d.value_sentence(d._definition(name if name in d.ACRONYMS else label, None, sentences[0]), *sentences[1:], *notes)


for _name, (_code, _note) in AIRSPACE_TYPE_CODES.items():
    AIRSPACE_TYPE_VALUES[_name] = _airspace_type_value(_name, AIRSPACE_TYPE_NAMES.get(_name), measure_definition(_code)["definition"], _note)
for _name, _row in MEASURE_SOURCE.get("airspace_types", {}).items():
    AIRSPACE_TYPE_VALUES[_name] = _airspace_type_value(_name, technical_name(_row["name"]), _row["definition"], _row.get("us_note"))


# ---- Enumerated values ---------------------------------------------------------------------------
ENUMS = {
    ("measures/aca", "aca_kind"): d.values({
        "formal": d.value_sentence("The airspace control authority makes the ACA when a component sends a request for it",
                                   "It has a minimum and a maximum altitude, a baseline, a width and the times when it is "
                                   "active (JP 3-09, Appendix A, 5.d)"),
        "informal": d.value_sentence("Time, lateral distance or altitude gives the separation between aircraft and surface fires",
                                     "A battalion or a higher unit gives the approval for it (JP 3-09, Appendix A, 5.d)"),
    }),
    ("measures/aca", "separation"): d.values({
        "time": d.value_sentence("Aircraft and surface fires use the area at different times"),
        "lateral": d.value_sentence("Lateral distance gives the separation between aircraft and surface fires"),
        "altitude": d.value_sentence("Altitude gives the separation between aircraft and surface fires"),
        "combined": "Separation by time, lateral distance and altitude together",
    }),
    ("measures/mez", "mez_kind"): d.values({
        "high": "A HIMEZ, in which high-altitude surface-to-air missiles usually engage the aircraft",
        "low": "A LOMEZ, in which surface-to-air missiles for low and moderate altitudes usually engage the aircraft",
        "short_range": "A SHORADEZ, in which SHORAD weapons usually engage the aircraft",
    }),
    ("measures/kb", "killbox_kind"): {key: d.value_sentence(text) for key, text in measure_definition("KB")["kinds"]["values"].items()},
    ("measures/airspace", "airspace_type"): dict(AIRSPACE_TYPE_VALUES),
    ("Frequency", "band"): d.values({
        "hf": "The HF band, from 3 to 30 MHz, for radio communication at long range.",
        "fm": "The VHF band with FM that army radios use, from 30 to 88 MHz.",
        "vhf": "The VHF band of aircraft radios, from 118 to 137 MHz.",
        "uhf": "The UHF band of the aircraft radios of armed forces, from 225 to 400 MHz.",
    }),
}
