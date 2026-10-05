"""OPORD, FRAGO and SPINS contracts, with the description of every field beside its schema.

The OPORD follows the five-paragraph base order and the annex formats of FM 5-0 (November 2024, Change 1),
Appendix D and Appendix E. The annex letters follow FM 6-0 (May 2022): A to H, J to N, P to S, U to W and Z.
Every paragraph, subsection, annex and appendix is typed: entries carry identifiers, refer to openAIX records
(control measures, airfields, agencies, channels, ATO missions) and use the shared time and position types.
Free text is only in named narrative fields (`summary`, `remarks`, a mission statement) beside typed data.
Print furniture (logos, banners, copy numbers and similar) is extension data of opord-builder, not part of
this contract.

The definitions are in schema.py (shared entries), paragraphs.py, annexes.py and spins.py. This module builds
the three root schemas and publishes DESCRIPTIONS, the description table for describe/resolve.py.
"""
from openaix.build.opord.schema import (BASE, choice, common, DEFS, DIALECT, items, local, many, remarks, string,
                                        summary, TEXTS, VERSION, when)
from openaix.describe import templates as d

# Importing these modules registers their definitions in DEFS; the import order is the order of `$defs`.
from openaix.build.opord import paragraphs, annexes, spins  # noqa: E402,F401,I001


# ---- Roots ---------------------------------------------------------------------------------------------
def root_schema(name_, title, fields, required):
    properties = {}
    for field, (node, text) in fields.items():
        properties[field] = node
        TEXTS[(name_, field)] = text
    return {"$schema": DIALECT, "$id": BASE + name_ + ":" + VERSION, "title": title, "type": "object",
            "additionalProperties": False, "properties": properties, "required": list(required), "$defs": {}}


def header_fields(document):
    return {
        "$schema": (string(format="uri"), d.reference("schema", "validates this document")),
        "kind": ({"type": "string", "const": document}, d.discriminator("a " + {"opord": "OPORD", "frago": "FRAGO", "spins": "SPINS publication"}[document])),
        "schema_version": ({"type": "string", "const": VERSION}, d.statement("This field gives the version of the openAIX schema that this document agrees with")),
        "meta": (common("Metadata"), d.statement("This field gives the identification, revision and issue data of this document")),
    }


TIME_ZONE = (string(pattern=r"^[A-IK-Z]$"), d.statement("This field gives the letter of the time zone that the order uses for display, such as `Z`",
                                                         "Each time in the document contains an offset"))
EXTENSIONS = (common("Extensions"), d.extension("The namespace `org.opord-builder.print` contains the data that `opord-builder` puts on each page"))


def opord_schema():
    return root_schema("opord", "openAIX OPORD", {
        **header_fields("opord"),
        "order_number": (string(), d.text("number of the order, such as `26-01`")),
        "operation_name": (string(), d.text("code name of the operation")),
        "issuing_headquarters": (string(), d.text("name of the headquarters that publishes the order")),
        "date_time": when("signature of the order"),
        "time_zone": TIME_ZONE,
        "effective_time": when("the start of the effect of the order"),
        "period": (common("Period"), d.window("the operation occurs")),
        "orders": (local("OrderLinks"), d.statement("This field gives the ATO, ACO and SPINS of the order")),
        "resources_ref": (common("ResourceRef"), d.reference("resource catalogue", "resolves the references of this order")),
        "references": (items(common("DocumentRef")), d.list_of("maps, charts and documents that the order refers to")),
        "task_organization": ({"type": "object", "propertyNames": common("Identifier"), "additionalProperties": local("Unit")},
                              d.map_of("units of the task organization")),
        "situation": (local("Situation"), d.statement("This field gives paragraph 1 (Situation)")),
        "mission": (local("MissionParagraph"), d.statement("This field gives paragraph 2 (Mission)")),
        "execution": (local("Execution"), d.statement("This field gives paragraph 3 (Execution)")),
        "sustainment": (local("Sustainment"), d.statement("This field gives paragraph 4 (Sustainment)")),
        "command_and_signal": (local("CommandAndSignal"), d.statement("This field gives paragraph 5 (Command and Signal)")),
        "acknowledgement": (local("Acknowledgement"), d.statement("This field gives the acknowledgement instructions")),
        "authentication": (local("Authentication"), d.statement("This field gives the signature block")),
        "annexes": (local("Annexes"), d.statement("This field gives the annexes, by letter")),
        "extensions": EXTENSIONS,
    }, ("kind", "schema_version", "mission"))


def frago_schema():
    schema = root_schema("frago", "openAIX FRAGO", {
        **header_fields("frago"),
        "frago_number": (string(), d.text("number of the FRAGO, such as `01`")),
        "issuing_headquarters": (string(), d.text("name of the headquarters that publishes the FRAGO")),
        "date_time": when("signature of the FRAGO"),
        "time_zone": TIME_ZONE,
        "effective_time": when("the start of the effect of the FRAGO"),
        "base_order": (local("OrderRef"), d.reference("base order", "this FRAGO changes", "The reference gives the identifier and the revision, not a file path")),
        "summary": summary("the FRAGO"),
        "mission": (string(), d.text("changed mission statement")),
        "commanders_intent": (string(), d.text("changed intent of the commander")),
        "changes": (many("OrderChange"), d.list_of("changes", None, "A consumer makes the changes in the sequence of the list",
                                                    "Validation examines only the structure, and consumers make the changes", ordered=True)),
        "references": (items(common("DocumentRef")), d.list_of("documents that the FRAGO refers to")),
        "acknowledgement": (local("Acknowledgement"), d.statement("This field gives the acknowledgement instructions")),
        "authentication": (local("Authentication"), d.statement("This field gives the signature block")),
        "extensions": EXTENSIONS,
    }, ("kind", "schema_version", "frago_number", "date_time", "base_order"))
    schema["anyOf"] = [{"required": ["changes"]}, {"required": ["mission"]}, {"required": ["commanders_intent"]}]
    return schema


def spins_schema():
    return root_schema("spins", "openAIX SPINS", {
        **header_fields("spins"),
        "scope": (choice("standing", "mission"), d.enum("type of the instructions: permanent instructions (`standing`) or instructions for one mission (`mission`)")),
        "period": (common("Period"), d.window("the instructions are in effect")),
        "orders": (local("OrderLinks"), d.statement("This field gives the OPORD, the ATO and the ACO of the publication")),
        "resources_ref": (common("ResourceRef"), d.reference("resource catalogue", "resolves the references of this publication")),
        "base": (common("PinnedRef"), d.reference("base publication", "this publication changes", "The reference identifies one revision of the publication")),
        "changes": (many("PublicationChange"), d.list_of("changes to the base publication", None, "A consumer makes the changes in the sequence of the list", ordered=True)),
        "rules_of_engagement": (local("SpinsRoe"), d.statement("This field gives the ROE summary")),
        "communications": (local("SpinsCommunications"), d.statement("This field gives the radio nets and the brevity words")),
        "identification": (local("SpinsIdentification"), d.statement("This field gives the IFF assignments and code words")),
        "personnel_recovery": (local("SpinsRecovery"), d.statement("This field gives the CSAR and personnel recovery procedures")),
        "divert_and_abort": (local("SpinsDivertAbort"), d.statement("This field gives the abort conditions and the divert airfields")),
        "airspace_notes": (many("AirspaceNote"), d.list_of("airspace notes")),
        "check_in": (many("CheckInProcedure"), d.list_of("procedures for each agency at the start and at the end of a task")),
        "tanker_procedures": (many("TankerProcedure"), d.list_of("tanker procedures")),
        "air_defense": (local("SpinsAirDefense"), d.statement("This field gives the air defence procedures")),
        "cas": (local("SpinsCas"), d.statement("This field gives the CAS stacks, the laser code plan and the laser restrictions")),
        "emergency": (local("SpinsEmergency"), d.statement("This field gives the emergency procedures")),
        "recovery_routing": (local("SpinsRecoveryRouting"), d.statement("This field gives the IFF lines, the routes back and the recovery airfields")),
        "electromagnetic": (local("SpinsElectromagnetic"), d.statement("This field gives the emission control periods and the jamming coordination")),
        "restrictions": (local("SpinsRestrictions"), d.statement("This field gives the protected sites and the weather minimums")),
        "reports": (many("ReportRequirement"), d.list_of("report requirements for aircrews, such as the MISREP, the in-flight report and the BDA report")),
        "night_operations": (local("SpinsNight"), d.statement("This field gives the NVG procedures, the lights-out areas and the lighting rules")),
        "references": (items(common("DocumentRef")), d.list_of("coordination documents for the publication, such as the ATO or the ACO")),
        "remarks": remarks("the publication"),
        "extensions": EXTENSIONS,
    }, ("kind", "schema_version", "scope"))


ROOTS = {
    "opord": (opord_schema, d.root("Operation order", "OPORD", "a directive that coordinates the execution of an operation, in five paragraphs with annexes",
                                   "The structure follows FM 5-0 and FM 6-0")),
    "frago": (frago_schema, d.root("Fragmentary order", "FRAGO", "an order that changes one or more identified orders",
                                   "The orders are an OPORD, an ATO, an ACO or a SPINS publication",
                                   "It contains only the changes, as JSON Pointer changes to one identified revision")),
    "spins": (spins_schema, d.root("Special instructions", "SPINS",
                                   "a publication that adds procedures, restrictions and coordination instructions to the tasking of all missions",
                                   "It contains permanent instructions, or changes to a base publication with a pinned reference")),
}


def order_document_schemas():
    """The OPORD, FRAGO and SPINS schemas; generate.py trims each to the definitions it reaches."""
    artifacts = {}
    for document, (build, text) in ROOTS.items():
        schema = build()
        schema["$defs"] = {key: value for key, value in DEFS.items()}
        TEXTS[(document, None)] = text
        artifacts["schemas/" + document + ".schema.json"] = schema
    return artifacts


def _table():
    """Description table for describe/resolve.py. Definition texts are scoped to the three schemas, so that a
    definition with the same name in a different schema keeps its own text."""
    table = {}
    for (context, field), text in TEXTS.items():
        if text is None:
            continue
        if context in ROOTS:
            table[(context, field)] = text
        else:
            for document in ROOTS:
                table[(document + ":" + context, field)] = text
    return table


for _document, (_build, _text) in ROOTS.items():
    _build()
    TEXTS[(_document, None)] = _text
DESCRIPTIONS = _table()
