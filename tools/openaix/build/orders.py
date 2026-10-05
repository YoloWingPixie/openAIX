"""ATO, ACO, shared resources, C2 agency, FAC, SCL and imported order documents, with the OIR examples.

Imported opord-builder models arrive typed (build/convert.py, SCHEMA-04). This module applies the
order keep/cut decisions (ORDERS-01/02/03/05, DOCTRINE-06/07, PLAN-03/04) and publishes the one
authored OIR scenario (examples/scenario.py). OPORD, FRAGO and SPINS are authored typed contracts in
build/opord/. Descriptions come from describe/resolve.py.
"""
import copy

from openaix.build.assignments import schema as assignment_schema
from openaix.build.ato_briefs import enrich_briefs
from openaix.build.common import (BASE, COMMON, DIALECT, RESOURCES, VERSION, array, external, obj, ref, text,
                                  trim_definitions)
from openaix.build.convert import load_model
from openaix.build.fac_profile import enrich_fac
from openaix.build.opord import schema as opord_schema
from openaix.build.opord.documents import order_document_schemas
from openaix.build.order_typing import type_orders
from openaix.build.planning_fields import enrich_planning
from openaix.build.scl import enrich_scl, scl_schema
from openaix.build.targeting import target_list
from openaix.examples.aco import build_aco_example, build_minimal_aco_example
from openaix.examples.scenario import scenario_examples


DOCUMENT_MODELS = {"tst": "tst", "jiptl": "jpitl"}
AIRFIELD = BASE + "airfield:" + VERSION
C2_AGENCY = BASE + "c2-agency:" + VERSION
# Command-and-control agency roles (ORDERS-05): Air Operations Center, Control and Reporting Centre,
# Air Support Operations Center, Direct Air Support Center, Tactical Air Control Party, Airborne
# Warning and Control System, Joint Terminal Attack Controller and Air Traffic Control.
C2_ROLES = ("AOC", "CRC", "ASOC", "DASC", "TACP", "AWACS", "JTAC", "ATC")
# Inline catalogue or a linked shared catalogue, never both (PLAN-04).
INLINE_OR_LINKED = [{"required": ["resources"], "not": {"required": ["resources_ref"]}},
                    {"required": ["resources_ref"], "not": {"required": ["resources"]}}]


def ato_model(source):
    """The imported ATO model with the ORDERS-01/02/05 decisions applied; ATO and resources derive from it."""
    model = copy.deepcopy(source)
    defs = model["$defs"]
    # Weather is set by the simulation environment and the OPORD; the ATO tasks aircraft.
    model["properties"].pop("weather", None)
    defs["Mission"]["properties"].pop("briefing", None)
    defs["CargoItem"]["properties"].pop("mass_each", None)
    # The tanker's method is owned by the Refueling tasking; a receiver's interface follows its aircraft type.
    defs["Flight"]["properties"].pop("refueling_method", None)
    # Simulator objects are in `extensions.sim` (sim/bindings.py), not DCS-only fields of the core record.
    defs["Aimpoint"]["properties"].pop("dcs_objects")
    defs["Flight"]["properties"].pop("dcs_group")
    defs["AircraftOverride"]["properties"].pop("dcs_unit")
    defs["Place"]["properties"].pop("dcs", None)
    defs.pop("DCSObjectRef", None)
    defs["Mission"]["required"] = sorted(set(defs["Mission"]["required"]) | {"mission_number"})
    # Airspace is selected by control-measure reference only; the legacy OPORD airspace selection is cut.
    defs["AirspaceSelection"] = external("ControlMeasureSelection")
    defs.pop("AirspaceRef", None)
    defs["Area"]["properties"]["geometry"] = {"oneOf": [external("Geometry_circle"), external("Geometry_polygon"), external("Geometry_corridor")]}
    for name in ("Circle", "Polygon", "Corridor"):
        defs.pop(name, None)
    for name in ("GeoPoint", "Altitude", "AltitudeBlock", "Period", "Window", "Offset", "Metadata", "DocumentRef", "PinnedRef", "TACAN"):
        defs[name] = external(name)
    return model


def canonical_ato(source):
    result = ato_model(source)
    result["$schema"] = DIALECT
    result["$id"] = BASE + "ato:" + VERSION
    result.pop("description", None)
    result["properties"]["schema_version"]["const"] = VERSION
    result["properties"]["$schema"] = text(format="uri")
    result["properties"]["extensions"] = external("Extensions")
    result["properties"]["resources"] = {"$ref": RESOURCES + "#/$defs/ResourceData"}
    result["properties"]["resources_ref"] = external("ResourceRef")
    result["oneOf"] = copy.deepcopy(INLINE_OR_LINKED)
    defs = result["$defs"]
    for name in ("Mission", "Flight", "Package", "CustomTask"):
        defs[name]["properties"]["extensions"] = external("Extensions")
    defs["Mission"]["properties"]["flights"]["minItems"] = 0
    defs["Mission"].pop("description", None)
    for model, field, collection in (
        ("Mission", "package", "packages"), ("Activity", "support_flight", "flights"),
        ("FlightSelection", "flight", "flights"), ("ReceiverSlot", "flight", "flights"),
        ("SelfControl", "responsible_flight", "flights"), ("SupportLink", "flight", "flights"),
        ("Escort", "supported_missions", "missions"), ("AirborneControl", "supported_missions", "missions"),
        ("ElectromagneticTask", "supported_missions", "missions"),
    ):
        defs[model]["properties"][field]["x-catalog"] = collection
    # Rendezvous points are air control points, not airfields.
    for model in ("Escort", "Package"):
        defs[model]["properties"]["rendezvous"]["x-catalog"] = "control_measures"
    defs["FlightSelection"]["x-selection"] = "flight"
    defs["FixedSelection"]["x-selection"] = "fixed-target"
    return trim_definitions(result)


def c2_agency_schema():
    """One command-and-control agency definition, used directly and by resources.agencies."""
    channels = array(external("Identifier"), 1) | {"x-catalog": "channels"}
    return {"$schema": DIALECT, "$id": C2_AGENCY, "title": "Command and control agency",
            **obj({"$schema": text(format="uri"), "id": external("Identifier"), "kind": {"const": "c2-agency"},
                   "callsign": text(), "role": {"enum": list(C2_ROLES)}, "channels": channels,
                   "position": external("GeoPoint"), "resources_ref": external("ResourceRef"), "extensions": external("Extensions")},
                  ("id", "kind", "callsign", "role"))}


def fac_schema():
    fac = c2_agency_schema()
    fac["$id"] = BASE + "fac:" + VERSION
    fac["title"] = "Forward air controller"
    fac["properties"]["kind"] = {"const": "fac"}
    fac["properties"]["role"] = {"enum": ["fac", "jtac", "fac_a"]}
    fac["properties"]["terminal_control"] = array({"enum": ["type_1", "type_2", "type_3"]}, 1)
    fac["properties"]["platform"] = {"enum": ["ground", "airborne"]}
    fac["properties"]["laser_codes"] = array(external("LaserCode"))
    enrich_fac(fac, COMMON)
    return fac


def aco_schema():
    return {
        "$schema": DIALECT, "$id": BASE + "aco:" + VERSION, "title": "openAIX ACO",
        **obj({"$schema": text(format="uri"), "kind": {"const": "aco"}, "schema_version": {"const": VERSION},
               "meta": external("Metadata"), "period": external("Period"), "resources": {"$ref": RESOURCES + "#/$defs/ResourceData"},
               "resources_ref": external("ResourceRef"), "assignments": array(assignment_schema(COMMON)),
               "instructions": array(text()), "extensions": external("Extensions")},
              ("kind", "schema_version", "meta", "period", "assignments")),
        "oneOf": copy.deepcopy(INLINE_OR_LINKED),
    }


def document_schema(name, source):
    result = copy.deepcopy(source)
    result["$schema"] = DIALECT
    result["$id"] = BASE + name + ":" + VERSION
    result.pop("description", None)
    result["properties"]["$schema"] = text(format="uri")
    result["properties"]["extensions"] = external("Extensions")
    if "schema_version" in result["properties"]:
        result["properties"]["schema_version"]["const"] = VERSION
    else:
        result["properties"]["schema_version"] = {"const": VERSION}
    if name in {"jiptl", "tst"}:
        target_list(result, name)
    return trim_definitions(result)


def resource_schema(source):
    model = ato_model(source)
    definitions = model["$defs"]
    resource_data = definitions.pop("Resources")
    resource_data["properties"].pop("airspace", None)
    resource_data["properties"]["places"] = {"type": "object", "additionalProperties": {"$ref": AIRFIELD}}
    # Navigation records that airfields link to: localizers, instrument procedures and named traffic pattern profiles.
    resource_data["properties"]["localizers"] = {"type": "object", "additionalProperties": {"$ref": BASE + "localizer:" + VERSION}}
    resource_data["properties"]["instrument_procedures"] = {"type": "object", "additionalProperties": {"$ref": BASE + "procedure:" + VERSION}}
    resource_data["properties"]["pattern_profiles"] = {"type": "object", "additionalProperties": {"$ref": AIRFIELD + "#/$defs/TrafficPattern"}}
    resource_data["properties"]["agencies"] = {"type": "object", "additionalProperties": {"$ref": C2_AGENCY}}
    definitions["FixedTarget"]["properties"]["aimpoints"]["additionalProperties"] = False
    for collection in resource_data["properties"].values():
        if "patternProperties" in collection:
            collection["additionalProperties"] = False
        if collection.get("type") == "object":
            collection["propertyNames"] = external("Identifier")
    resource_data["properties"].update({"control_measures": external("MeasureCatalogue"), "extensions": external("Extensions")})
    definitions["ResourceData"] = resource_data
    resource = {"$schema": DIALECT, "$id": RESOURCES, "$defs": definitions,
        **obj({"$schema": text(format="uri"), "kind": {"const": "resources"}, "schema_version": {"const": VERSION},
               "meta": external("Metadata"), "resources": ref("ResourceData"), "extensions": external("Extensions")},
              ("kind", "schema_version", "meta", "resources"))}
    return trim_definitions(resource)


def order_schemas(source, documents):
    """Schemas for ATO, ACO, shared resources, C2 agency, FAC and the imported order documents."""
    artifacts = {"schemas/ato.schema.json": canonical_ato(source), "schemas/aco.schema.json": aco_schema(),
                 "schemas/resources.schema.json": resource_schema(source),
                 "schemas/c2-agency.schema.json": c2_agency_schema(), "schemas/fac.schema.json": fac_schema(),
                 "schemas/scl.schema.json": scl_schema()}
    for name, model in documents.items():
        artifacts["schemas/" + name + ".schema.json"] = document_schema(name, model)
    # OPORD, FRAGO and SPINS are authored contracts (build/opord/), not imported models.
    if (opord_schema.VERSION, opord_schema.DIALECT, opord_schema.COMMON) != (VERSION, DIALECT, COMMON):
        raise ValueError("build/opord/schema.py schema identifiers disagree with build/common.py")
    artifacts.update(order_document_schemas())
    return artifacts


def order_examples(artifacts):
    """The authored OIR examples: ACO, ATO, OPORD, FRAGO, SPINS, TST, JIPTL, resources, agency and FAC."""
    artifacts.update(scenario_examples(VERSION))
    artifacts["examples/aco-oir.maximal.json"] = build_aco_example(VERSION)
    artifacts["examples/aco-oir.minimal.json"] = build_minimal_aco_example(VERSION)


ORDER_SCHEMAS = ("ato", "aco", "resources", "c2-agency", "fac", "scl", "opord", "frago", "spins", *DOCUMENT_MODELS)


def enrich_orders(artifacts):
    """Typed planning additions made after the requiredness policy and simulator bindings are applied."""
    enrich_planning(artifacts, COMMON)
    enrich_briefs(artifacts, COMMON)
    enrich_scl(artifacts)
    type_orders(artifacts, COMMON)
    for name in ORDER_SCHEMAS:
        trim_definitions(artifacts["schemas/" + name + ".schema.json"])


def load_documents():
    return {name: load_model(model) for name, model in DOCUMENT_MODELS.items()}
