"""Shared parts of the OPORD, FRAGO and SPINS contracts: identifiers, annex letters, schema node helpers,
recurring field texts and the entries that several paragraphs use.

`define` records every `$defs` entry in DEFS and its description texts in TEXTS; the paragraph, annex and SPINS
modules call it at import time, and documents.py publishes the result. Descriptions are describe/templates.py
template texts kept beside their fields.
"""
from openaix.describe import templates as d

# The same values as build/common.py; this module cannot import it (common imports the description tables).
# build/orders.py checks that the two agree.
VERSION = "0.1.0-draft.1"
DIALECT = "https://json-schema.org/draft/2020-12/schema"
BASE = "urn:openaix:schema:"
COMMON = BASE + "common:" + VERSION

# ---- Annex letters (FM 6-0, May 2022; formats in FM 5-0, Appendix E) ---------------------------------
ANNEXES = {
    "A": ("TaskOrganizationAnnex", "Task Organization"), "B": ("IntelligenceAnnex", "Intelligence"),
    "C": ("OperationsAnnex", "Operations"), "D": ("FiresAnnex", "Fires"), "E": ("ProtectionAnnex", "Protection"),
    "F": ("SustainmentAnnex", "Sustainment"), "G": ("EngineerAnnex", "Engineer"), "H": ("SignalAnnex", "Signal"),
    "J": ("PublicAffairsAnnex", "Public Affairs"), "K": ("CivilAffairsAnnex", "Civil Affairs Operations"),
    "L": ("InformationCollectionAnnex", "Information Collection"), "M": ("AssessmentAnnex", "Assessment"),
    "N": ("SpaceOperationsAnnex", "Space Operations"), "P": ("HostNationSupportAnnex", "Host-Nation Support"),
    "Q": ("KnowledgeManagementAnnex", "Knowledge Management"), "R": ("ReportsAnnex", "Reports"),
    "S": ("SpecialTechnicalOperationsAnnex", "Special Technical Operations"),
    "U": ("InspectorGeneralAnnex", "Inspector General"), "V": ("InteragencyCoordinationAnnex", "Interagency Coordination"),
    "W": ("OperationalContractSupportAnnex", "Operational Contract Support"), "Z": ("DistributionAnnex", "Distribution"),
}

# Catalogues that x-catalog references resolve in. Resource catalogue maps: control_measures, agencies, channels,
# places, routes, targets, threats, reports and procedures. Order-local catalogues come from
# check/orders.py (ORDER_CATALOGUES) and the linked ATO (`ato_missions`).
ORDER_UNITS, ORDER_PHASES, ORDER_REQUIREMENTS = "order_units", "order_phases", "order_requirements"
ORDER_DECISION_POINTS, ORDER_COMMAND_POSTS, ORDER_ORGANIZATIONS = "order_decision_points", "order_command_posts", "order_organizations"
ORDER_ENEMY_UNITS, ORDER_PROTECTED_SITES = "order_enemy_units", "order_protected_sites"
ATO_MISSIONS, ATO_FLIGHTS = "ato_missions", "ato_flights"
# Catalogue classes (catalogues/control-measures.json `category`) of airspace coordinating measures.
AIRSPACE_CATEGORIES = ["acm", "arm", "adm", "mdm", "atcm"]

DEFS = {}
TEXTS = {}
POINTER = r"^(/([^~/]|~[01])*)+$"


# ---- Schema node helpers -------------------------------------------------------------------------------
def common(name, **extra):
    return {"$ref": COMMON + "#/$defs/" + name, **extra}


def local(name):
    return {"$ref": "#/$defs/" + name}


def string(**extra):
    return {"type": "string", "minLength": 1, **extra}


def integer(minimum=None, maximum=None):
    node = {"type": "integer"}
    if minimum is not None:
        node["minimum"] = minimum
    if maximum is not None:
        node["maximum"] = maximum
    return node


def number(minimum=None):
    node = {"type": "number"}
    if minimum is not None:
        node["minimum"] = minimum
    return node


def boolean():
    return {"type": "boolean"}


def choice(*values):
    return {"type": "string", "enum": list(values)}


def items(node, minimum=0, unique=False):
    result = {"type": "array", "items": node, "minItems": minimum}
    if unique:
        result["uniqueItems"] = True
    return result


def many(name, minimum=0):
    return items(local(name), minimum)


def ref(catalogue, **extra):
    """Identifier of a record in a resource catalogue map, an order-local catalogue or the linked ATO."""
    return common("Identifier", **{"x-catalog": catalogue, **extra})


def refs(catalogue, **extra):
    return items(ref(catalogue, **extra), 0, True)


def measure(categories=None):
    extra = {"x-measure-categories": list(categories)} if categories else {}
    return ref("control_measures", **extra)


def measures(categories=None):
    return items(measure(categories), 0, True)


def texts(minimum=0):
    return items(string(), minimum)


def define(name, text, fields, required=(), any_of=None):
    """One `$defs` object: `fields` maps each property to (schema node, description)."""
    properties = {}
    for field, (node, description) in fields.items():
        properties[field] = node
        TEXTS[(name, field)] = description
    TEXTS[(name, None)] = text
    definition = {"type": "object", "additionalProperties": False, "title": name, "properties": properties,
                  "required": list(required)}
    if any_of:
        definition["anyOf"] = [{"required": [field]} for field in any_of]
    DEFS[name] = definition
    return local(name)


# ---- Recurring field texts -------------------------------------------------------------------------------
def summary(of):
    return string(), d.text("summary of " + of)


def remarks(of):
    return string(), d.text("remarks about " + of)


def ident(subject, scope):
    return common("Identifier"), d.identifier(subject, scope, "Other parts of the order use it to refer to this " + subject)


def unit_ref(clause):
    return ref(ORDER_UNITS), d.reference("unit of the task organization", clause)


def units_ref(clause):
    return refs(ORDER_UNITS), d.references("units of the task organization", clause)


def phase_ref(clause="this entry is applicable to"):
    return ref(ORDER_PHASES), d.reference("phase of the operation", clause)


def phases_ref(clause="this entry is applicable to"):
    return refs(ORDER_PHASES), d.references("phases of the operation", clause)


def measures_ref(clause, categories=None):
    return measures(categories), d.references("control measures", clause)


ROLE_RULE = "validator:openaix.check.validate.references"


def point_ref(clause, roles):
    """Reference to a Point measure that has one of the roles; validate.references checks the role."""
    rule = d.enforced("The point shall have the role " + " or ".join("`" + role + "`" for role in roles), ROLE_RULE)
    return ref("control_measures", **{"x-point-roles": list(roles)}), d.reference("point", clause, rule)


def points_ref(clause, roles):
    rule = d.enforced("Each point shall have the role " + " or ".join("`" + role + "`" for role in roles), ROLE_RULE)
    return items(ref("control_measures", **{"x-point-roles": list(roles)}), 0, True), d.references("points", clause, rule)


def orbit_ref(clause):
    rule = d.enforced("The measure shall be an orbit", ROLE_RULE)
    return ref("control_measures", **{"x-measure-kinds": ["ORBIT"]}), d.reference("orbit", clause, rule)


def measure_ref(clause, categories=None):
    return measure(categories), d.reference("control measure", clause)


def agency_ref(clause):
    return ref("agencies"), d.reference("command and control agency", clause)


def agencies_ref(clause):
    return refs("agencies"), d.references("command and control agencies", clause)


def channel_ref(clause):
    return ref("channels"), d.reference("radio channel", clause)


def channels_ref(clause):
    return refs("channels"), d.references("radio channels", clause)


def missions_ref(clause):
    return refs(ATO_MISSIONS), d.references("missions of the ATO", clause, "The `orders` field identifies the ATO")


def airfield_ref(clause):
    return ref("places"), d.reference("airfield", clause)


def position(of):
    return common("GeoPoint"), d.position(of)


def window(clause):
    return common("Window"), d.window(clause)


def when(event):
    return common("DateTime"), d.time(event)


def name(subject):
    return string(), d.name(subject)


def rank():
    return integer(1), d.statement("This field gives the priority of this entry", "The value 1 is the highest priority")


# ---- Shared entries ----------------------------------------------------------------------------------------
ECHELONS = ("team", "squad", "section", "platoon", "company", "battalion", "regiment", "brigade", "division", "corps", "army",
            "flight", "squadron", "group", "wing")
RELATIONSHIPS = ("organic", "assigned", "attached", "operational_control", "tactical_control", "administrative_control",
                 "direct_support", "reinforcing", "general_support_reinforcing", "general_support")
DIRECTIONS = ("north", "north_east", "east", "south_east", "south", "south_west", "west", "north_west")
SUPPLY_CLASSES = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X")
EFFECTS = ("destroy", "neutralize", "suppress", "disrupt", "degrade", "deny", "delay", "divert")
RISK_LEVELS = ("low", "medium", "high", "extremely_high")

define("Unit", d.entity("Unit", "one unit of the task organization of the order"), {
    "name": name("unit"),
    "echelon": (choice(*ECHELONS), d.enum("echelon of the unit")),
    "unit_type": (string(), d.text("type of the unit, such as `armoured infantry` or `F-16C squadron`")),
    "callsign": (string(), d.text("call sign of the unit")),
    "parent": unit_ref("is the parent of this unit in the task organization"),
    "coalition": (common("Coalition"), d.enum("coalition of the unit")),
    "agency": agency_ref("this unit operates"),
    "position": position("the unit at the time of issue"),
    "commander": (string(), d.text("name of the commander of the unit")),
    "remarks": remarks("this unit"),
}, ("name",))

define("Priority", d.entity("Priority entry", "one entry of a priority list, with a rank and the unit, area, phase or asset that it is for"), {
    "rank": rank(),
    "unit": unit_ref("has this priority"),
    "measure": measure_ref("has this priority"),
    "phase": phase_ref("this priority is applicable to"),
    "asset": (string(), d.text("name of the asset that has this priority, when no unit or control measure identifies it")),
    "remarks": remarks("this priority"),
}, ("rank",), any_of=("unit", "measure", "asset"))

define("TimelineEvent", d.entity("Timeline event", "one very important time or condition of the operation"), {
    "id": ident("event", "the timeline"),
    "event": (string(), d.text("name of the event")),
    "time": when("the event"),
    "condition": (string(), d.text("condition that starts the event, when the event has no fixed time")),
    "phase": phase_ref("starts or stops at this event"),
}, ("id", "event"), any_of=("time", "condition"))

define("OrderRef", d.entity("Order reference", "the identifier and the revision of one order"), {
    "id": (common("Identifier"), d.reference("order", "this reference is for", "The value is the `meta.id` field of the order")),
    "revision": (string(), d.statement("This field gives the revision of the order", "The value is the `meta.revision` field of the order")),
}, ("id", "revision"))

define("OrderLinks", d.entity("Order links", "the orders that this document uses",
                              "Validation finds each mission reference in the ATO that this field identifies",
                              "References to units, phases and protected sites of an OPORD use the OPORD that this field identifies"), {
    "opord": (local("OrderRef"), d.reference("OPORD", "this document uses")),
    "ato": (local("OrderRef"), d.reference("ATO", "this document uses")),
    "aco": (local("OrderRef"), d.reference("ACO", "this document uses")),
    "spins": (local("OrderRef"), d.reference("SPINS publication", "this document uses")),
})

define("Instruction", d.entity("Instruction", "one instruction of the coordinating instructions, with an identifier"), {
    "id": ident("instruction", "its list"),
    "instruction": (string(), d.text("instruction")),
    "units": units_ref("the instruction is for"),
    "measures": measures_ref("the instruction refers to"),
    "window": window("the instruction is in effect"),
}, ("id", "instruction"))

define("RoeRule", d.entity("Rule of engagement", "one rule of the ROE, with its number and its control measures"), {
    "id": ident("rule", "the order"),
    "number": (string(), d.text("number of the rule in the ROE, such as `R-101`")),
    "rule": (string(), d.text("rule")),
    "measures": measures_ref("the rule is applicable to"),
    "units": units_ref("the rule is applicable to"),
    "window": window("the rule is in effect"),
}, ("id", "rule"))

define("Message", d.entity("Theme or message", "one theme or message that units use or avoid"), {
    "id": ident("message", "its list"),
    "kind": (choice("emphasize", "avoid"), d.enum("instruction for the message: use the message or avoid it")),
    "message": (string(), d.text("theme or message")),
    "audience": (string(), d.text("group of persons that receives the message")),
}, ("id", "kind", "message"))

define("Task", d.entity("Task", "one task to a unit, with its purpose, its time and the records that it refers to"), {
    "id": ident("task", "the order"),
    "task": (string(), d.text("task, as a verb with its object")),
    "purpose": (string(), d.text("purpose of the task")),
    "phase": phase_ref("the task is in"),
    "window": window("the unit does the task"),
    "measures": measures_ref("the task refers to"),
    "ato_missions": missions_ref("do the task"),
}, ("id", "task"))
