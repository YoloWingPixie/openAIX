"""Every schema, field and enumerated-value description, resolved from template tables.

Descriptions are built by describe/templates.py templates. The tables are keyed
by (context, property):
- context is a schema name (for example "measures/kb" or "opord"), a `$defs` name, or either one
  followed by the dotted path of an inline object, for example ("Geometry_polyarc.segments", "turns");
- property None keys the description of the schema root or `$defs` entry itself;
- property "#<keyword>" keys a described node that is not a property, such as array `items`;
- a context "<schema>:<context>" applies to one schema only and wins over the plain context.

Table modules, each exporting DESCRIPTIONS {(context, property): Text} and optionally ENUMS
{(context, property): {value: Text}} and SUBJECTS {context: noun phrase}:
- tables/common.py: common primitives, measures, catalogue text, generic field templates;
- tables/orders.py: ATO, ACO, SPINS, TST, JIPTL, resources, agencies and controllers;
- tables/order_fields.py: the order fields that have no description in the source models;
- tables/ato.py: ATO mission briefs, the counterland control tasking and typed target-list fields;
- build/opord/documents.py: OPORD, FRAGO and SPINS fields, with the texts kept beside each field;
- tables/navigation.py: navigation records;

describe_artifacts() replaces every description in the generated schemas. A schema node that carries
a description no template built, and that no table key covers, fails generation.
"""
import json
import re

from openaix.build.opord import documents as opord_table
from openaix.describe import templates as d
from openaix.describe.tables import ato as ato_table
from openaix.describe.tables import common as common_table
from openaix.describe.tables import navigation as navigation_table
from openaix.describe.tables import order_fields as order_fields_table
from openaix.describe.tables import orders as orders_table


TABLE_MODULES = (common_table, orders_table, order_fields_table, ato_table, opord_table, navigation_table)
DESCRIPTIONS, ENUMS, SUBJECTS = {}, {}, {}
for _module in TABLE_MODULES:
    for _name, _target in (("DESCRIPTIONS", DESCRIPTIONS), ("ENUMS", ENUMS), ("SUBJECTS", SUBJECTS)):
        _table = getattr(_module, _name, {})
        _clash = set(_table) & set(_target)
        if _clash:
            raise ValueError(f"{_module.__name__}.{_name} repeats keys: {sorted(map(str, _clash))[:5]}")
        _target.update(_table)
GENERIC = common_table.GENERIC


def subject(context):
    """Noun phrase for the object that owns a field, for generic templates."""
    head = context.split(":")[-1]
    if head in SUBJECTS:
        return SUBJECTS[head]
    if "." in head:
        field = head.rpartition(".")[2].replace("_", " ")
        return field[:-1] if field.endswith("s") and not field.endswith("ss") else field
    head = head.removeprefix("measures/")
    words = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", head)
    words = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", words)
    return " ".join(word if word.isupper() and len(word) > 1 else word.lower() for word in re.split(r"[ _-]+", words))


def schema_description(name):
    """Root description for a schema built by an area builder."""
    return DESCRIPTIONS.get((name, None))


MISSING = []
CONDITIONS = ("if", "then", "else", "not")


def _registered(text):
    return isinstance(text, str) and text in d.REGISTRY


def _lookup(schema, context, field, node):
    for key in ((schema + ":" + context, field), (context, field)):
        if key in DESCRIPTIONS:
            return DESCRIPTIONS[key]
    if field is None or field.startswith("#"):
        return None
    rule = common_table.shape_rule(field, node, subject(context))
    if rule is not None:
        return rule
    if field in GENERIC and not node.get("description"):
        return GENERIC[field](subject(context))
    return None


def _enum_lookup(schema, context, field):
    for key in ((schema + ":" + context, field), (context, field)):
        if key in ENUMS:
            return ENUMS[key]
    return None


def describe_artifacts(artifacts, strict=True):
    """Replace every schema description with template text; fail on text that no template built."""
    MISSING.clear()

    def place(node, schema, context, field, pointer):
        text = _lookup(schema, context, field, node)
        if text is not None:
            if not _registered(text):
                MISSING.append((schema, context, field, pointer, "table text not built by a template: " + str(text)))
            node["description"] = text
        elif "description" in node and not _registered(node["description"]):
            MISSING.append((schema, context, field, pointer, str(node["description"])))
        if field is not None and not field.startswith("#"):
            enums = _enum_lookup(schema, context, field)
            if enums is not None:
                node["x-enum-descriptions"] = dict(enums)
        for key, text in (node.get("x-enum-descriptions") or {}).items():
            if not _registered(text):
                MISSING.append((schema, context, field, pointer + "/x-enum-descriptions/" + key, str(text)))

    def visit(node, schema, context, pointer, field_key=None):
        if isinstance(node, list):
            for index, item in enumerate(node):
                visit(item, schema, context, pointer + "/" + str(index))
            return
        if not isinstance(node, dict):
            return
        if field_key is not None:
            place(node, schema, *field_key, pointer)
        else:
            key = "#" + pointer.rsplit("/", 1)[-1]
            if "description" in node or "x-enum-descriptions" in node or (context, key) in DESCRIPTIONS:
                place(node, schema, context, key, pointer)
        for key, child in node.items():
            if key in CONDITIONS:
                strip(child)
            elif key == "$defs":
                for definition, value in child.items():
                    visit(value, schema, definition, pointer + "/$defs/" + definition, (definition, None))
            elif key == "properties" and isinstance(child, dict):
                for field, value in child.items():
                    visit(value, schema, context + "." + field, pointer + "/properties/" + field, (context, field))
            elif key not in ("description", "x-enum-descriptions", "const", "enum", "default", "examples"):
                visit(child, schema, context, pointer + "/" + key)

    def strip(node):
        """Conditional subschemas are predicates: they carry no description of their own."""
        if isinstance(node, list):
            for item in node:
                strip(item)
        elif isinstance(node, dict):
            node.pop("description", None)
            node.pop("x-enum-descriptions", None)
            for child in node.values():
                strip(child)

    for path, schema in artifacts.items():
        if not path.startswith("schemas/"):
            continue
        name = path.removeprefix("schemas/").removesuffix(".schema.json")
        # Builders may share one dict between two fields (for example `start` and `end`); copy so that
        # each node takes its own description.
        schema = artifacts[path] = json.loads(json.dumps(schema))
        visit(schema, name, name, "", (name, None))
    if strict and MISSING:
        listing = "\n".join(f"  {schema}: ({context!r}, {field!r}) {pointer}: {text[:70]}"
                            for schema, context, field, pointer, text in MISSING[:60])
        raise ValueError(f"{len(MISSING)} descriptions have no template entry:\n{listing}")
    return artifacts


def typed_field_description(original, primitive):
    """Source text of a field typed as a common primitive; describe_artifacts replaces it with template text."""
    return original
