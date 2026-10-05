import argparse
import hashlib
import json
import math
import re
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource

from openaix import ROOT
from openaix.build.availability import schedule_errors
from openaix.build.units import LENGTH_UNITS
from openaix.check import emitters as emitter_checks
from openaix.check import measures as measure_checks
from openaix.check import navigation as navigation_checks
from openaix.check import orders as order_checks
from openaix.check import scl as scl_checks
from openaix.check.consistency import binding_conflicts
from openaix.check.contract import ContractError, check_limits, component_limits, instant, interval, pointer


FORMAT_CHECKER = FormatChecker()
if "date-time" not in FORMAT_CHECKER.checkers:
    raise SystemExit("rfc3339-validator is required: jsonschema cannot enforce date-time without it")
# Area semantic checks. Each module provides semantic(value, path, period), catalogues(document, resources)
# and document(document, resources); areas add checks there without editing this engine.
AREAS = (navigation_checks, measure_checks, order_checks, emitter_checks, scl_checks)


# Record kinds that one schema validates under another name: carriers and FARPs are airfield records.
KIND_SCHEMAS = {"carrier": "airfield", "farp": "airfield"}


def unavailable(uri):
    raise NoSuchResource(ref=uri)


_SCHEMAS = {}
# Linked documents (resource catalogues, ATOs, OPORDs) that passed validation, by content digest.
_VALIDATED = set()


def use_schemas(records):
    """Validate against these schema records (name -> schema) instead of the files in schemas/; generation uses this."""
    registry = Registry(retrieve=unavailable).with_resources((schema["$id"], Resource.from_contents(schema)) for schema in records.values())
    _SCHEMAS["current"] = (records, registry)
    _VALIDATED.clear()


def schemas():
    if "current" not in _SCHEMAS:
        use_schemas({str(path.relative_to(ROOT / "schemas")).removesuffix(".schema.json"): json.loads(path.read_text())
                     for path in (ROOT / "schemas").rglob("*.schema.json")})
    return _SCHEMAS["current"]


def validate_linked(document, schema_name, resource_document=None, linked=None):
    """validate_document for a linked document; a document that passed once is not validated again."""
    key = (schema_name, hashlib.sha256(json.dumps([document, resource_document, linked], sort_keys=True).encode()).hexdigest())
    if key not in _VALIDATED:
        validate_document(document, schema_name, resource_document, linked)
        _VALIDATED.add(key)


@lru_cache(maxsize=1)
def measure_categories():
    """Catalogue class of each measure code (catalogues/control-measures.json). An instance of a canonical kind has no
    code: points are air reference measures, orbits airspace coordinating measures, and airspace, airways and
    navigation aids air traffic control measures."""
    catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
    canonical = {"POINT": "arm", "ORBIT": "acm", "AIRSPACE": "atcm", "AIRWAY": "atcm", "NAVAID": "atcm"}
    return {**canonical, **{entry["code"]: entry["category"] for entry in catalogue["types"]}}


def linked_ato(document, resource_document, linked):
    """Missions of the ATO that an OPORD, FRAGO or SPINS links in `orders.ato`; the ATO is validated before use."""
    orders = document.get("orders")
    if not isinstance(orders, dict) or "ato" not in orders:
        return {}
    expected = orders["ato"]
    ato = (linked or {}).get(expected["id"])
    if ato is None:
        raise ContractError("/orders/ato", "linked ATO required")
    if ato.get("kind") != "ato" or ato.get("meta", {}).get("revision") != expected["revision"]:
        raise ContractError("/orders/ato", "linked ATO identity or revision mismatch")
    try:
        validate_linked(ato, "ato", resource_document)
    except ContractError as error:
        raise ContractError("/orders/ato", "invalid linked ATO: " + error.code) from error
    return {"ato_missions": {mission["id"]: mission for mission in ato["missions"]},
            "ato_flights": {flight["id"]: flight for mission in ato["missions"] for flight in mission["flights"]}}


def linked_opord(document, resource_document, linked):
    """Order-local catalogues (units, phases, protected sites) of the OPORD that a SPINS links in `orders.opord`."""
    orders = document.get("orders")
    if document.get("kind") == "opord" or not isinstance(orders, dict) or "opord" not in orders:
        return {}
    expected = orders["opord"]
    opord = (linked or {}).get(expected["id"])
    if opord is None:
        raise ContractError("/orders/opord", "linked OPORD required")
    if opord.get("kind") != "opord" or opord.get("meta", {}).get("revision") != expected["revision"]:
        raise ContractError("/orders/opord", "linked OPORD identity or revision mismatch")
    try:
        validate_linked(opord, "opord", resource_document, linked)
    except ContractError as error:
        raise ContractError("/orders/opord", "invalid linked OPORD: " + error.code) from error
    return order_checks.order_catalogues(opord)


def finite(value, path=()):
    if isinstance(value, float) and not math.isfinite(value):
        raise ContractError(pointer(path), "non-finite number")
    if isinstance(value, dict):
        for key, child in value.items():
            finite(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            finite(child, (*path, index))


def semantic(value, resources, period, path=()):
    if isinstance(value, dict):
        if isinstance(value.get("extensions"), dict) and "sim" in value["extensions"]:
            for relative, reason in binding_conflicts(value):
                raise ContractError(pointer((*path, *relative)), reason)
        if "schedule" in value and {"start", "end"} <= value.keys():
            for relative, reason in schedule_errors(value, instant):
                raise ContractError(pointer((*path, *relative)), reason)
        for area in AREAS:
            area.semantic(value, path, period)
        if set(("lower", "upper")) <= value.keys():
            check_limits(value["lower"], value["upper"], path)
        if {"lower_limit", "upper_limit", "geometry"} <= value.keys():
            component_limits(value, path)
        if set(("start", "end")) <= value.keys() and all(
            (isinstance(value[key], dict) and "offset_minutes" in value[key]) or isinstance(value[key], str)
            for key in ("start", "end")
        ):
            interval(value, period, path)
        if value.get("kind") == "polygon" and "rings" in value:
            for index, ring in enumerate(value["rings"]):
                if ring[0] != ring[-1] or len({json.dumps(p, sort_keys=True) for p in ring[:-1]}) < 3:
                    raise ContractError(pointer((*path, "rings", index)), "polygon ring must close around three distinct points")
        if value.get("kind") == "track_racetrack" and value["a"] == value["b"]:
            raise ContractError(pointer(path), "racetrack anchors coincide")
        if value.get("kind") == "sector" and "inner_radius" in value:
            inner, outer = value["inner_radius"], value["outer_radius"]
            if inner["value"] * LENGTH_UNITS[inner["unit"]] >= outer["value"] * LENGTH_UNITS[outer["unit"]]:
                raise ContractError(pointer((*path, "inner_radius")), "inner radius must be smaller than outer radius")
        for key, child in value.items():
            if key == "rows" and value.get("kind") == "table":
                continue
            if key == "value" and {"op", "path"} <= value.keys():
                continue
            if key not in ("extensions", "attributes", "source_fields", "raw_fields", "native_fields"):
                semantic(child, resources, period, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            semantic(child, resources, period, (*path, index))


def references(value, node, base_uri, registry, resources, path=()):
    if not isinstance(node, dict):
        return
    if "$ref" in node:
        resolved = registry.resolver(base_uri).lookup(node["$ref"])
        next_base = base_uri if node["$ref"].startswith("#") else node["$ref"].split("#", 1)[0]
        references(value, resolved.contents, next_base, registry, resources, path)
    catalogue = node.get("x-catalog")
    if catalogue:
        values = value if isinstance(value, list) else [value]
        for index, identifier in enumerate(values):
            if identifier is not None and identifier not in resources.get(catalogue, {}):
                suffix = (index,) if isinstance(value, list) else ()
                raise ContractError(pointer((*path, *suffix)), "unresolved " + catalogue + " reference")
    for keyword in ("anyOf", "oneOf"):
        for branch in node.get(keyword, []):
            validator = Draft202012Validator(registry.contents(base_uri), registry=registry).evolve(schema=branch)
            if validator.is_valid(value):
                references(value, branch, base_uri, registry, resources, path)
                break
    for branch in node.get("allOf", []):
        references(value, branch, base_uri, registry, resources, path)
    if isinstance(value, dict):
        for key, child in value.items():
            if key in node.get("properties", {}):
                references(child, node["properties"][key], base_uri, registry, resources, (*path, key))
            elif isinstance(node.get("additionalProperties"), dict):
                references(child, node["additionalProperties"], base_uri, registry, resources, (*path, key))
            else:
                for pattern, child_schema in node.get("patternProperties", {}).items():
                    if re.search(pattern, key):
                        references(child, child_schema, base_uri, registry, resources, (*path, key))
    elif isinstance(value, list) and "items" in node:
        for index, child in enumerate(value):
            references(child, node["items"], base_uri, registry, resources, (*path, index))
    if node.get("x-selection") == "flight":
        flight = resources["flights"][value["flight"]]
        members = value.get("members", [])
        if len(set(members)) != len(members) or any(member > flight["count"] for member in members):
            raise ContractError(pointer((*path, "members")), "members must be distinct aircraft within the selected flight")
    elif node.get("x-selection") == "fixed-target":
        target = resources["targets"][value["target"]]
        if target["kind"] != "fixed":
            raise ContractError(pointer((*path, "target")), "fixed selection requires a fixed target")
        for index, aimpoint in enumerate(value["aimpoints"]):
            if aimpoint not in target["aimpoints"]:
                raise ContractError(pointer((*path, "aimpoints", index)), "unresolved aimpoint reference")
    if "x-measure-kinds" in node:
        identifier = value if isinstance(value, str) else value["id"]
        target = resources["control_measures"][identifier]
        if target["type"] not in node["x-measure-kinds"]:
            raise ContractError(pointer(path if isinstance(value, str) else (*path, "id")), "navigation reference requires one of: " + ", ".join(node["x-measure-kinds"]))
    if "x-point-roles" in node:
        identifier = value if isinstance(value, str) else value["id"]
        target = resources["control_measures"][identifier]
        if target["type"] != "POINT" or not set(target["roles"]) & set(node["x-point-roles"]):
            raise ContractError(pointer(path if isinstance(value, str) else (*path, "id")), "point role requires one of: " + ", ".join(node["x-point-roles"]))
    if "x-measure-categories" in node:
        target = resources["control_measures"][value]
        if measure_categories().get(target["type"]) not in node["x-measure-categories"]:
            raise ContractError(pointer(path), "measure class requires one of: " + ", ".join(node["x-measure-categories"]))
    if "x-target-kinds" in node:
        target = resources["targets"][value["target"]]
        if target["kind"] not in node["x-target-kinds"]:
            raise ContractError(pointer((*path, "target")), "target selection requires one of: " + ", ".join(node["x-target-kinds"]))


def validate_document(document, schema_name=None, resource_document=None, linked=None):
    if not isinstance(document, dict):
        raise ContractError("/", "document must be a JSON object")
    records, registry = schemas()
    selected = next((name for name, schema in records.items() if schema["$id"] == document.get("$schema")), None)
    if "$schema" in document and selected is None and schema_name is None:
        raise ContractError("/$schema", "unknown schema")
    selected = schema_name or selected or KIND_SCHEMAS.get(document.get("kind"), document.get("kind"))
    if selected not in records:
        raise ContractError("/$schema", "unknown schema")
    schema = records[selected]
    finite(document)
    validator = Draft202012Validator(schema, registry=registry, format_checker=FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(document), key=lambda error: (pointer(error.absolute_path), str(error.validator)))
    if errors:
        error = errors[0]
        raise ContractError(pointer(error.absolute_path), "schema constraint: " + str(error.validator))
    resources = document.get("resources", {})
    if "resources_ref" in document:
        if resource_document is None:
            raise ContractError("/resources_ref", "linked resource catalogue required")
        try:
            validate_linked(resource_document, "resources")
        except ContractError as error:
            raise ContractError("/resources_ref", "invalid resource catalogue: " + error.code) from error
        expected = document["resources_ref"]
        if any(expected[key] != resource_document.get("meta", {}).get(key) for key in ("id", "revision")):
            raise ContractError("/resources_ref", "resource catalogue identity or revision mismatch")
        resources = resource_document["resources"]
    semantic(document, resources, document.get("period"))
    reference_catalogues = dict(resources)
    reference_catalogues.update(linked_ato(document, resource_document, linked))
    reference_catalogues.update(linked_opord(document, resource_document, linked))
    for area in AREAS:
        reference_catalogues.update(area.catalogues(document, resources))
    references(document, schema, schema["$id"], registry, reference_catalogues)
    for area in AREAS:
        area.document(document, resources)


def validate_definitions(document):
    """An example of common.schema.json gives one value for each definition, under the name of the definition."""
    records, registry = schemas()
    common = records["common"]
    for name, value in document.items():
        if name == "$schema":
            continue
        if name not in common["$defs"]:
            raise ContractError(pointer((name,)), "unknown common definition")
        validator = Draft202012Validator({"$ref": common["$id"] + "#/$defs/" + name}, registry=registry, format_checker=FORMAT_CHECKER)
        errors = sorted(validator.iter_errors(value), key=lambda error: pointer(error.absolute_path))
        if errors:
            raise ContractError(pointer((name, *errors[0].absolute_path)), "schema constraint: " + str(errors[0].validator))
        finite(value, (name,))
        semantic(value, {}, None, (name,))


def import_document(text, schema_name=None, resource_document=None, linked=None):
    document = json.loads(text)
    validate_document(document, schema_name, resource_document, linked)
    return document


def export_document(document, schema_name=None, resource_document=None, linked=None):
    validate_document(document, schema_name, resource_document, linked)
    return json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def capability_report(document, taskings=(), measures=()):
    supported_taskings, supported_measures = set(taskings), set(measures)
    return {
        "unhandled_taskings": [mission["id"] for mission in document.get("missions", []) if mission["tasking"]["kind"] not in supported_taskings],
        "unhandled_measures": [identifier for identifier, measure in document.get("resources", {}).get("control_measures", {}).items() if measure["type"] not in supported_measures],
    }


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("document", nargs="?", type=Path)
    parser.add_argument("--schema")
    parser.add_argument("--resources", type=Path)
    parser.add_argument("--ato", type=Path, help="linked ATO of an OPORD, FRAGO or SPINS (orders.ato)")
    parser.add_argument("--opord", type=Path, help="linked OPORD of a SPINS (orders.opord)")
    args = parser.parse_args()
    if args.document:
        resources = json.loads(args.resources.read_text()) if args.resources else None
        ato = json.loads(args.ato.read_text()) if args.ato else None
        opord = json.loads(args.opord.read_text()) if args.opord else None
        linked = {document["meta"]["id"]: document for document in (ato, opord) if document} or None
        validate_document(json.loads(args.document.read_text()), args.schema, resources, linked)
        print("Document contract passed.")
        return
    records, _ = schemas()
    for schema in records.values():
        Draft202012Validator.check_schema(schema)
    for name, metadata in json.loads((ROOT / "sources/manifest.json").read_text()).items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != metadata["snapshot_sha256"]:
            raise ContractError("/" + name, "source snapshot digest changed")
    count = 0
    paths = sorted((ROOT / "examples").rglob("*.json"))
    # An example links the resource catalogue example whose meta identifier its `resources_ref` names. The generated
    # minimal and maximal examples (examples/minimal, examples/maximal) link the curated documents only.
    generated = (ROOT / "examples/minimal", ROOT / "examples/maximal")
    documents = [json.loads(path.read_text()) for path in paths if path.parent not in generated]
    catalogues = {document["meta"]["id"]: document for document in documents
                  if document.get("kind") == "resources" and "id" in document.get("meta", {})}
    # An OPORD, FRAGO or SPINS links the ATO example whose meta identifier its `orders.ato` names; a SPINS also links its OPORD.
    linked = {document["meta"]["id"]: document for document in documents if document.get("kind") in {"ato", "opord"} and "id" in document.get("meta", {})}
    for path in paths:
        try:
            document = json.loads(path.read_text())
            if "$schema" not in document:
                raise ContractError("/$schema", "example must declare its schema")
            if document["$schema"] == records["common"]["$id"]:
                validate_definitions(document)
            else:
                validate_document(document, resource_document=catalogues.get(document.get("resources_ref", {}).get("id")), linked=linked)
        except ContractError as error:
            raise SystemExit(str(path.relative_to(ROOT)) + ": " + str(error))
        count += 1
    print(f"Validated {len(records)} schemas and {count} examples offline.")


def main():
    try:
        run()
    except (ContractError, ValueError) as error:
        raise SystemExit(str(error))
