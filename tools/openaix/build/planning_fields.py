"""Typed planning additions to the ATO and ACO, and the planning-inventory check.

Descriptions and enumeration meanings come from describe/resolve.py; doctrinal citations for
these fields are listed in sources/planning-field-inventory.json (no per-field citation annotations).
"""
from copy import deepcopy


def validate_planning_inventory(inventory, authorities):
    """Order-field coverage rows (ACMREQ sets, documents, mission types) cite a known authority with a locator."""
    for row in [*inventory["documents"], *inventory.get("mission_type_mapping", [])]:
        source = row.get("source")
        if not source or source not in authorities or not row.get("locator"):
            raise ValueError("planning source requires a known authority and locator")
    request = inventory["acmreq"]
    if request["source"] not in authorities or not request.get("locator"):
        raise ValueError("request inventory requires a known authority and locator")
    if request["complete_field_dictionary"]:
        raise ValueError("a public message-set inventory cannot establish complete field-dictionary coverage")
    sequences = [row["sequence"] for row in request["sets"]]
    if len(sequences) != len(set(sequences)) or sorted(sequences) != list(range(1, 26)):
        raise ValueError("public request inventory must account for each Annex C set exactly once")


def enrich_counterair(ato):
    patrol = ato["$defs"]["Patrol"]["properties"]
    properties = {key: deepcopy(patrol[key]) for key in (
        "area", "altitude", "objective", "engagement_instructions", "abort_criteria", "success_criteria", "report_refs",
    )}
    for field in properties.values():
        field.pop("description", None)
    properties.update({
        "kind": {"const": "counterair"},
        "mission_type": {"enum": ["fighter_sweep", "interception"]},
        "operating_window": {k: v for k, v in patrol["station_window"].items() if k != "description"},
        "target": {"$ref": "#/$defs/MobileSelection", "x-target-kinds": ["mobile"]},
    })
    ato["$defs"]["CounterAir"] = {
        "type": "object", "additionalProperties": False, "title": "Counterair task",
        "properties": properties, "required": ["kind", "mission_type"],
        "allOf": [{"if": {"properties": {"mission_type": {"const": "fighter_sweep"}}},
                   "then": {"required": ["area"]},
                   "else": {"anyOf": [{"required": ["area"]}, {"required": ["target"]}]}}],
    }
    tasking = ato["$defs"]["Mission"]["properties"]["tasking"]
    reference = "#/$defs/CounterAir"
    if {"$ref": reference} not in tasking["oneOf"]:
        tasking["oneOf"].append({"$ref": reference})


def enrich_planning(artifacts, common):
    def ref(name, catalogue=None):
        value = {"$ref": common + "#/$defs/" + name}
        if catalogue:
            value["x-catalog"] = catalogue
        return value

    def texts():
        return {"type": "array", "items": {"type": "string", "minLength": 1}}

    aco = artifacts["schemas/aco.schema.json"]
    assignment = aco["properties"]["assignments"]["items"]
    # Fields mapped from the AJP-3.3.5 Annex C ACMREQ (request) message sets.
    assignment["properties"].update({
        "controlling_agency": ref("Identifier", "agencies"),
        "control_points": {"type": "array", "minItems": 1, "uniqueItems": True,
                           "items": ref("ControlMeasureSelection") | {"x-measure-kinds": ["POINT", "NAVAID"]}},
        "transit_instructions": texts(),
        "purpose": {"type": "string", "minLength": 1},
    })
    references = {"type": "array", "items": ref("DocumentRef")}
    aco["properties"]["references"] = deepcopy(references)
    ato = artifacts["schemas/ato.schema.json"]
    enrich_counterair(ato)
    ato["properties"]["aco"] = ref("DocumentRef")
    ato["$defs"]["Transport"]["properties"]["role"] = {
        "enum": ["airlift", "aeromedical_evacuation", "noncombatant_evacuation", "humanitarian_assistance"]}
    ato["$defs"]["PersonnelRecovery"]["properties"]["role"] = {"enum": ["search_and_rescue", "combat_search_and_rescue"]}
    # JP 3-09.3 (2014) para 27: preplanned CAS is scheduled or on call; on-call and immediate CAS use the OnCallCAS tasking.
    role = ato["$defs"]["PreplannedAttack"]["properties"]["role"]
    role["enum"] = ["scheduled_cas" if value == "preplanned_cas" else value for value in role["enum"]]
