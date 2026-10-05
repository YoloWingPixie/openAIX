"""Minimal and maximal OIR examples for every schema: examples/minimal/ and examples/maximal/.

A maximal example starts from the richest OIR record of its schema and adds each field that the schema allows and the
record does not have yet. The added values come from the OIR records (curated examples, the shared resource catalogue
and examples/seeds.py), so every value belongs to the scenario. Each field of each schema object occurs at
least once; list items and map entries that add no field are removed. A field that cannot occur together with the
fields of the record (another `oneOf` branch, a conditional rule) is recorded in catalogues/example-notes.json.

A minimal example keeps only the fields that the schemas and the semantic checks require.
"""
from copy import deepcopy
import hashlib
import json
import multiprocessing
import os

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

from openaix import ROOT
from openaix.check import validate
from openaix.check.contract import ContractError, pointer
from openaix.examples.seeds import complete, field_values, navigation_seeds, seed_fields


SCENARIO_BOX = {"latitude": (30.6, 38.5), "longitude": (32.0, 41.0)}
CANDIDATE_LIMIT = 12
# Fields that belong to one record: a value from another record would not describe this one. Simulator data
# (`extensions`) links one record to its own simulator objects.
OWN_FIELDS = {"extensions", "name", "description", "notes", "remarks", "purpose", "callsign", "title", "path"}
COMMON_ID = "urn:openaix:schema:common:0.1.0-draft.1"
FORMAT_CHECKER = FormatChecker()


def absolute(node, base):
    """Copy of a schema with each local `$ref` made absolute, so that each node can be validated alone."""
    if isinstance(node, dict):
        return {key: base + value if key == "$ref" and value.startswith("#") else absolute(value, base) for key, value in node.items()}
    if isinstance(node, list):
        return [absolute(value, base) for value in node]
    return node


def dump(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def size(value):
    return len(dump(value))


def nested(value, path=()):
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from nested(child, (*path, key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from nested(child, (*path, index))


def in_scenario(document):
    """True when every position of the document is in the OIR scenario box (the DCS Syria map)."""
    for _, value in nested(document):
        if isinstance(value, dict) and isinstance(value.get("latitude"), (int, float)) and isinstance(value.get("longitude"), (int, float)):
            if not all(low <= value[axis] <= high for axis, (low, high) in SCENARIO_BOX.items()):
                return False
    return True


def get(value, path):
    for key in path:
        value = value[key]
    return value


def locate(value, location):
    """The value at a JSON pointer, or None."""
    for part in location.split("/")[1:]:
        part = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        elif isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None
    return value


def context(path):
    """The nearest field name of a path, or None: the parent field of a value."""
    return next((key for key in reversed(path) if isinstance(key, str)), None)


def generic(path):
    return "/".join("*" if isinstance(key, int) else str(key) for key in path)


class View:
    """The fields that apply to one object value: the properties of every schema branch that the value matches."""

    def __init__(self):
        self.properties, self.required, self.entries, self.items, self.branches = {}, set(), [], [], []
        self.min_items = self.min_properties = 0
        self.names = []


class Engine:
    def __init__(self, records, resources, linked):
        self.records = {name: absolute(schema, schema["$id"]) for name, schema in records.items()}
        self.registry = Registry().with_resources((schema["$id"], Resource.from_contents(schema)) for schema in self.records.values())
        self.resources = resources
        self.linked = linked
        self.validators = {}
        self.shared_documents = []
        self.document_entries = {}
        # Fields whose values a schema rule of an enclosing object rejected: a conditional rule excludes them.
        self.schema_rejections = set()
        self.shared = {}
        self.wrappers = {}

    # -- schema access --------------------------------------------------------------------------------------------

    def lookup(self, reference):
        return self.registry.resolver().lookup(reference).contents

    def valid(self, node, value):
        validator = self.validators.get(id(node))
        if validator is None:
            validator = self.validators[id(node)] = (node, Draft202012Validator(node, registry=self.registry, format_checker=FORMAT_CHECKER))
        return validator[1].is_valid(value)

    def combined(self, nodes):
        if len(nodes) == 1:
            return nodes[0]
        key = tuple(id(node) for node in nodes)
        if key not in self.wrappers:
            self.wrappers[key] = {"allOf": list(nodes)}
        return self.wrappers[key]

    def view(self, node, value, result=None):
        result = result or View()
        if not isinstance(node, dict):
            return result
        if "$ref" in node:
            self.view(self.lookup(node["$ref"]), value, result)
        for name, child in node.get("properties", {}).items():
            result.properties.setdefault(name, []).append((node, child))
        result.required.update(node.get("required", []))
        if isinstance(node.get("propertyNames"), dict):
            result.names.append(node["propertyNames"])
        result.min_items = max(result.min_items, node.get("minItems", 0))
        result.min_properties = max(result.min_properties, node.get("minProperties", 0))
        for child in node.get("patternProperties", {}).values():
            result.entries.append(child)
        if isinstance(node.get("additionalProperties"), dict):
            result.entries.append(node["additionalProperties"])
        if isinstance(node.get("items"), dict):
            result.items.append(node["items"])
        for branch in node.get("allOf", []):
            self.view(branch, value, result)
        for keyword in ("oneOf", "anyOf"):
            if keyword in node:
                matched = [branch for branch in node[keyword] if self.valid(branch, value)]
                for index, branch in enumerate(matched[:1] if keyword == "oneOf" else matched):
                    # One matching `anyOf` branch is enough: only the first one adds required fields.
                    required = set(result.required)
                    self.view(branch, value, result)
                    if index:
                        result.required = required
                if keyword == "oneOf" and matched:
                    result.branches.append((node[keyword], matched[0]))
        if "if" in node:
            branch = node.get("then") if self.valid(node["if"], value) else node.get("else")
            if branch is not None:
                self.view(branch, value, result)
        return result

    def allowed(self, view, name):
        """False when a `propertyNames` rule of the object does not let the field occur."""
        return all(self.valid(rule, name) for rule in view.names)

    def label(self, branch):
        """Short name of a `oneOf` branch: its title, its discriminator constant or the last part of its reference."""
        node = self.lookup(branch["$ref"]) if "$ref" in branch else branch
        for name in ("type", "kind", "airspace_type", "op", "sim"):
            field = node.get("properties", {}).get(name, {})
            if "const" in field:
                return str(field["const"])
        if node.get("title"):
            return node["title"]
        if node.get("required"):
            return " + ".join(node["required"])
        return branch.get("$ref", "").split("/")[-1] or "alternative"

    # -- coverage -------------------------------------------------------------------------------------------------

    def coverage(self, node, value, counts=None):
        """Count of each (schema object, field) pair that occurs in the value."""
        counts = {} if counts is None else counts
        if isinstance(value, dict):
            view = self.view(node, value)
            for name, child in value.items():
                owners = view.properties.get(name)
                if owners:
                    for owner, _ in owners:
                        key = (id(owner), name)
                        counts[key] = counts.get(key, 0) + 1
                    self.coverage(self.combined([child for _, child in owners]), child, counts)
                elif view.entries:
                    self.coverage(self.combined(view.entries), child, counts)
        elif isinstance(value, list):
            view = self.view(node, value)
            if view.items:
                for item in value:
                    self.coverage(self.combined(view.items), item, counts)
        return counts

    # -- candidate values -----------------------------------------------------------------------------------------

    def entries(self, document):
        """(key, encoded value, size, value) of each field value of one document, computed once per document."""
        cached = self.document_entries.get(id(document))
        if cached is not None:
            return cached[1]
        shared = any(document is item for item in self.shared_documents)
        result = []
        for path, value in nested(document):
            if not path or not isinstance(path[-1], str) or value in ([], {}, ""):
                continue
            encoded = dump(value)
            if shared:
                # Scenario-wide values are indexed by their parent field too, for example ("fuel", "notes").
                result.append(((context(path[:-1]), path[-1]), encoded, len(encoded), value, True))
            result.append((path[-1], encoded, len(encoded), value, shared))
        self.document_entries[id(document)] = (document, result)
        return result

    def pool(self, documents, own=1):
        """Field values of the OIR records by field name, the `own` records of this schema first, smaller values first.
        A field that names or describes one record (OWN_FIELDS) takes values from the records of this schema only;
        scenario-wide values for it are taken by parent field only."""
        result = {}
        for index, document in enumerate(documents):
            rank = 0 if index < own else 1
            for key, encoded, length, value, shared in self.entries(document):
                if isinstance(key, str) and key in OWN_FIELDS and (rank or shared) and not (shared and key == "extensions"):
                    continue
                result.setdefault(key, {}).setdefault(encoded, (rank, length, value))
        return {name: [entry[2] for entry in sorted(values.values(), key=lambda entry: entry[:2])] for name, values in result.items()}

    # -- maximal --------------------------------------------------------------------------------------------------

    def fill(self, node, value, path, state):
        if isinstance(value, dict):
            view = self.view(node, value)
            for name, owners in view.properties.items():
                if name in value or name == "$schema" or not self.allowed(view, name):
                    continue
                keys = [(id(owner), name) for owner, _ in owners]
                if any(key in state["covered"] for key in keys):
                    continue
                field = self.combined([child for _, child in owners])
                tried = 0
                # A nested record takes its extension data from the scenario-wide values only.
                if name == "extensions" and path:
                    candidates = self.shared.get(name, [])
                elif "extensions" in path:
                    # Inside simulator and consumer data, only scenario-wide values for the same parent field.
                    candidates = self.shared.get((context(path), name), [])
                else:
                    candidates = state["pool"].get((context(path), name), []) + state["pool"].get(name, [])
                for candidate in candidates:
                    if (generic((*path, name)), dump(candidate)) in state["rejected"] or not self.valid(field, candidate):
                        continue
                    tried += 1
                    if tried > CANDIDATE_LIMIT:
                        break
                    trial = {**value, name: candidate}
                    if self.valid(node, trial):
                        value[name] = deepcopy(candidate)
                        state["inserted"].append((*path, name))
                        state["origin"][(*path, name)] = dump(candidate)
                        for key in keys:
                            state["covered"][key] = state["covered"].get(key, 0) + 1
                        for key in self.coverage(field, value[name]):
                            state["covered"][key] = state["covered"].get(key, 0) + 1
                        break
            view = self.view(node, value)
            for name, child in list(value.items()):
                owners = view.properties.get(name)
                if owners:
                    self.fill(self.combined([field for _, field in owners]), child, (*path, name), state)
                elif view.entries:
                    self.fill(self.combined(view.entries), child, (*path, name), state)
        elif isinstance(value, list):
            view = self.view(node, value)
            if view.items:
                for index, item in enumerate(value):
                    self.fill(self.combined(view.items), item, (*path, index), state)

    def check(self, node, value, name):
        """Raise ContractError when the value fails the schema or the semantic checks of the repository."""
        if name == "common#":
            validator = Draft202012Validator(node, registry=self.registry, format_checker=FORMAT_CHECKER)
            for error in validator.iter_errors(value):
                raise ContractError(pointer(error.absolute_path), "schema constraint: " + str(error.validator))
            validate.semantic(value, self.resources["resources"], None)
            validate.references(value, node, COMMON_ID, self.registry, self.resources["resources"])
            return
        validate.validate_document(value, name, self.resources, self.linked)

    def maximal(self, node, seed, name, documents, own=1):
        value = deepcopy(seed)
        self.check(node, value, name)  # The seed is valid; each addition is checked after it.
        state = {"pool": self.pool(documents, own), "rejected": set(), "covered": {}, "inserted": [], "origin": {}}
        for _ in range(400):
            state["covered"] = self.coverage(node, value)
            self.fill(node, value, (), state)
            try:
                self.check(node, value, name)
                break
            except ContractError as error:
                where = tuple(part.replace("~1", "/").replace("~0", "~") for part in error.path.split("/")[1:])
                inserted = [path for path in state["inserted"] if tuple(map(str, path)) == where[:len(path)] and self.present(value, path)]
                # A schema rule of an enclosing object (a `oneOf`, a conditional) reports the object, not the added field.
                below = [path for path in state["inserted"] if tuple(map(str, path[:len(where)])) == where and self.present(value, path)]
                # A conditional rule can also report a sibling of the added field: then the last addition goes.
                recent = [path for path in state["inserted"] if self.present(value, path)]
                if not inserted and not below and not recent:
                    raise ValueError(f"{name}: maximal example fails at {error}") from error
                path = max(inserted, key=len) if inserted else below[-1] if below else recent[-1]
                parent = get(value, path[:-1])
                state["rejected"].add((generic(path), state["origin"][path]))
                if error.code.startswith("schema constraint"):
                    self.schema_rejections.add(path[-1])
                del parent[path[-1]]
        else:
            raise ValueError(name + ": maximal example does not converge")
        return self.trim(node, value, name)

    @staticmethod
    def present(value, path):
        for key in path:
            if isinstance(value, dict) and key in value or isinstance(value, list) and isinstance(key, int) and key < len(value):
                value = value[key]
            else:
                return False
        return True

    def trim(self, node, value, name):
        """Remove list items and map entries that add no field, while the example stays valid."""
        counts = self.coverage(node, value)
        removals = []

        def visit(schema, item, path):
            if isinstance(item, dict):
                view = self.view(schema, item)
                for key, child in item.items():
                    owners = view.properties.get(key)
                    if owners:
                        visit(self.combined([field for _, field in owners]), child, (*path, key))
                    elif view.entries:
                        visit(self.combined(view.entries), child, (*path, key))
                        if isinstance(child, dict):
                            removals.append(((*path, key), self.combined(view.entries), schema))
            elif isinstance(item, list):
                view = self.view(schema, item)
                if view.items:
                    for index, child in enumerate(item):
                        visit(self.combined(view.items), child, (*path, index))
                        # Positions of a geometry are not separate items: a ring or a line needs all of them.
                        if index >= max(1, view.min_items) and isinstance(child, dict) and "latitude" not in child:
                            removals.append(((*path, index), self.combined(view.items), schema))

        visit(node, value, ())
        # Deepest and last first, so that the indices of the remaining candidates stay correct.
        removals.sort(key=lambda entry: (len(entry[0]), entry[0][-1] if isinstance(entry[0][-1], int) else 0), reverse=True)
        chosen = []
        for path, schema, _ in removals:
            own = self.coverage(schema, get(value, path))
            if all(counts.get(key, 0) > number for key, number in own.items()):
                for key, number in own.items():
                    counts[key] -= number
                chosen.append(path)
        return self.remove(value, chosen, node, name)

    def remove(self, value, paths, node, name):
        """Remove the paths. When the example then fails on a reference, the map entry with the referenced key stays;
        other failures split the paths into halves until each removal is tested."""
        paths = list(paths)
        while paths:
            trial = deepcopy(value)
            for path in paths:
                del get(trial, path[:-1])[path[-1]]
            # A map entry or a list item whose identifier the rest of the example names is a referenced record: it stays.
            names = {item for _, item in nested(trial) if isinstance(item, str)}
            kept = [path for path in paths if isinstance(path[-1], str) and path[-1] in names
                    or isinstance(path[-1], int) and isinstance(get(value, path), dict) and get(value, path).get("id") in names]
            if kept:
                paths = [path for path in paths if path not in kept]
                continue
            try:
                self.check(node, trial, name)
                return trial
            except ContractError as error:
                if len(paths) == 1:
                    return value
                target = locate(trial, error.path)
                where = tuple(part.replace("~1", "/").replace("~0", "~") for part in error.path.split("/")[1:])
                # The failing record and its neighbours keep their items: their own rules (minimum entries, totals,
                # graph links) need them.
                scope = where[:max(len(where) - 2, min(len(where), 3))]
                # Records of the same kind (the same path with other map keys) follow the same rule: they keep theirs too.
                pattern = [*scope[:-1], None] if len(scope) >= 3 else list(scope)
                kept = [path for path in paths if isinstance(path[-1], str) and path[-1] == target
                        or tuple(map(str, path[:len(scope)])) == scope
                        or len(path) >= len(scope) and all(part is None or str(path[index]) == part for index, part in enumerate(pattern))]
                if not kept:
                    half = len(paths) // 2
                    return self.remove(self.remove(value, paths[:half], node, name), paths[half:], node, name)
                paths = [path for path in paths if path not in kept]
        return value

    # -- minimal --------------------------------------------------------------------------------------------------

    def reduce(self, node, value):
        """Only the required fields, the first required list items and the minimum number of map entries."""
        if isinstance(value, dict):
            view = self.view(node, value)
            result = {}
            for name, child in value.items():
                owners = view.properties.get(name)
                if name in view.required or name == "$schema":
                    result[name] = self.reduce(self.combined([field for _, field in owners]), child) if owners else deepcopy(child)
            minimum = view.min_properties
            for name, child in value.items():
                if name not in result and name not in view.properties and view.entries and len(result) < minimum:
                    result[name] = self.reduce(self.combined(view.entries), child)
            return result
        if isinstance(value, list):
            view = self.view(node, value)
            minimum = view.min_items
            if any(isinstance(item, list) or isinstance(item, dict) and "latitude" in item for item in value):
                minimum = len(value)  # The positions of a geometry go together.
            schema = self.combined(view.items) if view.items else True
            return [self.reduce(schema, item) for item in value[:minimum]]
        return deepcopy(value)

    def minimal(self, node, maximal, name):
        value = self.reduce(node, maximal)
        for _ in range(200):
            try:
                self.check(node, value, name)
                return value
            except ContractError as error:
                where = [part.replace("~1", "/").replace("~0", "~") for part in error.path.split("/")[1:]]
                if not self.restore(node, value, maximal, where):
                    raise ValueError(f"{name}: minimal example fails at {error}") from error
        raise ValueError(name + ": minimal example does not converge")

    def restore(self, node, value, maximal, where):
        """Add back the first field that the error location needs, from the maximal example."""
        current, source, schema = value, maximal, node
        for part in where:
            key = int(part) if isinstance(source, list) else part
            if isinstance(source, list):
                view = self.view(schema, source)
                if key >= len(current):
                    current.extend(self.reduce(self.combined(view.items), item) for item in source[len(current):key + 1])
                    return True
                current, source, schema = current[key], source[key], self.combined(view.items) if view.items else True
                continue
            if not isinstance(source, dict) or key not in source:
                break
            view = self.view(schema, source)
            owners = view.properties.get(key)
            child = self.combined([field for _, field in owners]) if owners else self.combined(view.entries) if view.entries else True
            if key not in current:
                current[key] = self.reduce(child, source[key])
                return True
            current, source, schema = current[key], source[key], child
        # A reference needs the resource catalogue of the document.
        for key in ("resources_ref", "resources"):
            if isinstance(maximal, dict) and key in maximal and key not in value:
                value[key] = self.reduce(self.combined([field for _, field in self.view(node, maximal).properties[key]]), maximal[key])
                return True
        # The error is at an object: add its optional fields back one at a time.
        if isinstance(current, dict) and isinstance(source, dict):
            view = self.view(schema, source)
            for key, child in source.items():
                if key not in current:
                    owners = view.properties.get(key)
                    current[key] = self.reduce(self.combined([field for _, field in owners]), child) if owners else deepcopy(child)
                    return True
        return False

    # -- shared definitions ---------------------------------------------------------------------------------------

    def common_pair(self, node, documents):
        """A minimal and a maximal value of each definition of common.schema.json, from the largest OIR value that
        satisfies the definition."""
        values = {}
        for document in documents:
            for _, value in nested(document):
                values.setdefault(dump(value), value)
        ordered = sorted(values.values(), key=size, reverse=True)
        self.current_pool = self.pool(documents, len(documents))
        minimal, maximal, notes, missing = {"$schema": node["$id"]}, {"$schema": node["$id"]}, [], []
        for name, definition in node["$defs"].items():
            kinds = {"object": dict, "array": list, "string": str, "boolean": bool, "integer": int, "number": (int, float)}
            kind = kinds.get(definition.get("type")) if isinstance(definition.get("type"), str) else dict if "properties" in definition else None
            required = set(definition.get("required", []))
            seed = None
            for value in ordered:
                if kind and not isinstance(value, kind) or required and not (isinstance(value, dict) and required <= value.keys()):
                    continue
                if isinstance(value, dict):
                    # A definition that other records extend (a mixin) takes only its own fields of a record.
                    view = self.view(definition, value)
                    if view.properties and not view.entries and not value.keys() <= view.properties.keys():
                        value = {key: item for key, item in value.items() if key in view.properties}
                        if not value or required and not required <= value.keys():
                            continue
                if self.valid(definition, value):
                    try:
                        self.check(definition, value, "common#")
                    except ContractError:
                        continue
                    seed = value
                    break
            if seed is None:
                missing.append(name)
                continue
            maximal[name] = self.maximal(definition, seed, "common#", documents, len(documents))
            minimal[name] = self.minimal(definition, maximal[name], "common#")
            notes.extend({**entry, "path": name + ("/" + entry["path"] if entry["path"] != "/" else "")}
                         for entry in self.notes(definition, maximal[name]))
        if missing:
            raise ValueError("no OIR value for common definitions: " + ", ".join(missing))
        return minimal, maximal, notes

    # -- notes ----------------------------------------------------------------------------------------------------

    def notes(self, node, value, path=(), counts=None, state=None):
        """Fields of the schema that the maximal example leaves out, and the `oneOf` branches that it does not use.
        Each schema object is noted once, at its first location; list indices and map keys show as `*`."""
        counts = self.coverage(node, value) if counts is None else counts
        state = {"seen": set(), "notes": []} if state is None else state
        if isinstance(value, dict):
            view = self.view(node, value)
            for branches, selected in view.branches:
                others = [self.label(branch) for branch in branches if branch is not selected]
                if others and id(branches) not in state["seen"]:
                    state["seen"].add(id(branches))
                    state["notes"].append({"path": "/".join(path) or "/", "selected": self.label(selected), "alternatives": others})
            for name, owners in view.properties.items():
                keys = [(id(owner), name) for owner, _ in owners]
                if name in value or name == "$schema" or any(counts.get(key) for key in keys) or keys[0] in state["seen"]:
                    continue
                state["seen"].update(keys)
                reason = self.exclusion(node, value, name) if self.allowed(view, name) else {"reason": "conditional"}
                state["notes"].append({"path": "/".join((*path, name)), **reason})
            for name, child in value.items():
                owners = view.properties.get(name)
                if owners:
                    self.notes(self.combined([field for _, field in owners]), child, (*path, name), counts, state)
                elif view.entries:
                    self.notes(self.combined(view.entries), child, (*path, "*"), counts, state)
        elif isinstance(value, list):
            view = self.view(node, value)
            if view.items:
                for item in value:
                    self.notes(self.combined(view.items), item, (*path, "*"), counts, state)
        return state["notes"]

    def exclusion(self, node, value, name):
        """Why a field is left out: other fields exclude it, a conditional rule excludes it, or no OIR value fits."""
        field = self.combined([child for _, child in self.view(node, value).properties[name]])
        candidates = [item for key, items in self.current_pool.items() if key == name or isinstance(key, tuple) and key[1] == name
                      for item in items]
        candidate = next((item for item in candidates if self.valid(field, item)), None)
        if candidate is None:
            return {"reason": "no_value"}
        if self.valid(node, {**value, name: candidate}):
            return {"reason": "conditional" if name in self.schema_rejections else "no_value"}
        others = [other for other in value if other != "$schema" and self.valid(node, {**{k: v for k, v in value.items() if k != other}, name: candidate})]
        return {"reason": "alternative", "instead_of": others} if others else {"reason": "conditional"}


# -- driver -----------------------------------------------------------------------------------------------------------

def schema_name(path):
    return path.removeprefix("schemas/").removesuffix(".schema.json")


def embedded_records(resources, version):
    """Records of the OIR resource catalogue that are also standalone documents: airfields, navigation records,
    control measures and agencies."""
    catalogue = resources["resources"]
    for group in ("places", "localizers", "instrument_procedures", "control_measures", "agencies"):
        for record in catalogue.get(group, {}).values():
            yield {**deepcopy(record), "resources_ref": {"id": resources["meta"]["id"], "revision": resources["meta"]["revision"]}}


NOTES = "catalogues/example-notes.json"
INPUTS = "$inputs_sha256"


def inputs_digest(artifacts):
    """Digest of everything the pairs depend on: the schemas, catalogues and curated examples, the tools that build
    and check them, and the vendored DCS station data."""
    digest = hashlib.sha256()
    for path, value in sorted(artifacts.items()):
        if not path.startswith(("examples/minimal/", "examples/maximal/")) and path != NOTES:
            digest.update(path.encode() + b"\0" + dump(value).encode() + b"\0")
    for path in sorted([*(ROOT / "tools").rglob("*.py"), ROOT / "sources/dcs/aircraft-stations.json"]):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0" + path.read_bytes() + b"\0")
    return digest.hexdigest()


def cached_pairs(artifacts, digest):
    """The generated pairs on disk, when they were built from the same inputs."""
    try:
        notes = json.loads((ROOT / NOTES).read_text())
    except (OSError, ValueError):
        return None
    if notes.get(INPUTS) != digest:
        return None
    result = {NOTES: notes}
    for label in ("minimal", "maximal"):
        for path in sorted((ROOT / "examples" / label).glob("*.json")):
            result["examples/" + label + "/" + path.name] = json.loads(path.read_text())
    names = {schema_name(path).split("/")[-1] for path in artifacts if path.startswith("schemas/")}
    if {path.rsplit("/", 1)[-1].removesuffix(".json") for path in result if path.startswith("examples/maximal/")} != names:
        return None
    return result


_BUILD = None


def build_one(name):
    """The minimal example, the maximal example and the notes of one schema."""
    engine, records, standalone, embedded, resources = _BUILD
    engine.schema_rejections = set()
    identifier = records[name]["$id"]
    node = engine.records[name]
    if name == "common":
        return engine.common_pair(node, standalone)
    own = [value for value in standalone if value.get("$schema") == identifier]
    own += [{**value, "$schema": identifier} for value in embedded if engine.valid(node, {**value, "$schema": identifier})]
    if name == "control-measure":
        own += [{**value, "$schema": identifier} for value in standalone if engine.valid(node, {**value, "$schema": identifier})]
    if not own:
        raise ValueError("no OIR record for schema " + name)
    seed = max(own, key=size)
    extra = seed_fields().get(name, {})
    seed = {**seed, **extra, **({"extensions": {**seed.get("extensions", {}), **extra["extensions"]}} if "extensions" in extra else {})}
    seed = complete(name, deepcopy(seed), resources)
    documents = [*own, *[value for value in standalone if value not in own]]
    engine.current_pool = engine.pool(documents, len(own))
    maximal = engine.maximal(node, seed, name, documents, len(own))
    minimal = engine.minimal(node, maximal, name)
    return minimal, maximal, engine.notes(node, maximal)


def build_pairs(artifacts, version):
    """examples/minimal/<schema>.json, examples/maximal/<schema>.json and catalogues/example-notes.json. The pairs
    on disk are kept when their recorded input digest is current: a rebuild gives the same files."""
    digest = inputs_digest(artifacts)
    cached = cached_pairs(artifacts, digest)
    if cached is not None:
        return cached
    records = {schema_name(path): value for path, value in artifacts.items() if path.startswith("schemas/")}
    validate.use_schemas(records)
    curated = {path: value for path, value in artifacts.items() if path.startswith("examples/") and isinstance(value, dict)}
    resources = curated["examples/resources.json"]
    linked = {value["meta"]["id"]: value for value in curated.values() if value.get("kind") in {"ato", "opord"} and "id" in value.get("meta", {})}
    engine = Engine(records, resources, linked)
    oir = [value for path, value in sorted(curated.items()) if in_scenario(value)
           and value.get("resources_ref", {}).get("id", resources["meta"]["id"]) == resources["meta"]["id"]]
    seeds = navigation_seeds(version)
    embedded = list(embedded_records(resources, version))
    engine.shared_documents = field_values()
    engine.shared = engine.pool(engine.shared_documents, len(engine.shared_documents))
    standalone = [*oir, *seeds.values(), *embedded, *engine.shared_documents]
    global _BUILD
    _BUILD = (engine, records, standalone, embedded, resources)
    names = sorted(records)
    # Each schema is independent: build them in parallel processes (fork), in a fixed order of results.
    try:
        context_ = multiprocessing.get_context("fork")
    except ValueError:
        context_ = None
    if context_ is not None and len(names) > 1:
        with context_.Pool(min(len(names), os.cpu_count() or 1)) as workers:
            built = workers.map(build_one, names, chunksize=1)
    else:
        built = [build_one(name) for name in names]
    result, notes = {}, {}
    for name, (minimal, maximal, note) in zip(names, built):
        notes[records[name]["$id"]] = note
        result["examples/minimal/" + name.split("/")[-1] + ".json"] = minimal
        result["examples/maximal/" + name.split("/")[-1] + ".json"] = maximal
    result[NOTES] = {INPUTS: digest, **notes}
    return result
