"""Lint every generated description against the description rules in describe/templates.py.

Scope: descriptions and enumerated-value descriptions in schemas/, the catalogue definitions and notes,
and the airspace-type descriptions. Example documents are instance data and are not linted. Exit status 1 when any rule fails.
"""
import argparse
import collections
import json
import re
from pathlib import Path

from openaix import ROOT
from openaix.describe import templates

RULES = {
    "registry": "description not produced by describe/templates.py",
    "period": "missing final period",
    "acronym": "unknown acronym, or acronym not expanded on first use",
    "duplicate": "repeated or concatenated description",
    "placeholder": "empty or placeholder description",
    "kind": "template kind does not fit the schema node",
    "normative": "a shall sentence without a registered enforcement (schema keyword or validator check)",
    "missing": "a schema property without a description",
    "tautology": "an enumerated value description that only repeats the value name and adds no meaning",
}

PLACEHOLDERS = {"todo", "tbd", "tbc", "fixme", "xxx", "description", "field", "value", "example", "placeholder", "n/a", "none", "test"}
TEMPLATE_HEADS = re.compile(r"(?:^|(?<=\. ))(This field (?:identifies|gives|contains)|This list (?:identifies|contains)|This map contains|"
                            r"The value is `true`|This value identifies|The value identifies this record|This record is)\b")
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")
PARENTHESES = re.compile(r"\([^()]*\)")


def _strip_literals(text):
    spans = templates.literal_spans(text) + templates.designator_spans(text)
    chars = list(text)
    for start, end in spans:
        for index in range(start, end):
            chars[index] = " "
        chars[start] = "L"  # one word stands for the literal
    return "".join(chars)


def check_text(text, kind=None):
    """Problems of one description, as (rule, detail) pairs."""
    problems = []
    if not isinstance(text, str) or not text.strip():
        return [("placeholder", "empty")]
    bare = text.strip().rstrip(".").strip().lower()
    if bare in PLACEHOLDERS or len(bare.split()) < 2:
        problems.append(("placeholder", text))
    if not text.rstrip().endswith("."):
        problems.append(("period", text[-30:]))
    problems.extend(("acronym", detail) for detail in acronym_problems(text))
    sentence_list = [sentence.strip() for sentence in templates.sentences(text)]
    repeated = [sentence for sentence, number in collections.Counter(sentence_list).items() if number > 1]
    if repeated:
        problems.append(("duplicate", "repeated sentence: " + repeated[0]))
    heads = TEMPLATE_HEADS.findall(text)
    if len(heads) > 1:
        problems.append(("duplicate", "two template heads: " + ", ".join(heads)))
    return problems


def acronym_problems(text):
    problems, seen = [], set()
    skip = templates.literal_spans(text) + templates.designator_spans(text)
    for match in templates.ACRONYM.finditer(text):
        if any(start <= match.start() < end for start, end in skip):
            continue
        token = match.group(3) or match.group(1)
        known = token if token in templates.ACRONYMS else None
        if not known and match.group(2) == "s" and token + "s" in templates.ACRONYMS:
            known = token + "s"
        if not known:
            problems.append("unknown acronym " + token)
            continue
        if known in seen:
            continue
        seen.add(known)
        if not match.group(3):
            problems.append("not expanded on first use: " + known)
            continue
        expansion = templates.ACRONYMS[known]
        before = text[:match.start()].rstrip().lower()
        if not (before.endswith(expansion.lower()) or before.endswith(templates.pluralize(expansion).lower())):
            problems.append(f"({known}) does not follow its expansion '{expansion}'")
    return problems


# ---- Collect description sites ---------------------------------------------------------------

Site = collections.namedtuple("Site", "file path text node context siblings role")


def schema_sites(path, document):
    name = path.removeprefix("schemas/").removesuffix(".schema.json")
    sites = []

    def visit(node, context, pointer, siblings=None, role="schema"):
        if isinstance(node, list):
            for index, item in enumerate(node):
                visit(item, context, pointer + "/" + str(index))
            return
        if not isinstance(node, dict):
            return
        if isinstance(node.get("description"), str):
            sites.append(Site(path, pointer + "/description", node["description"], node, context, siblings, role))
        for key, text in (node.get("x-enum-descriptions") or {}).items():
            sites.append(Site(path, pointer + "/x-enum-descriptions/" + key, text, None, context, node["x-enum-descriptions"], "value"))
        for key, child in node.items():
            if key == "$defs":
                for definition, value in child.items():
                    visit(value, definition, pointer + "/$defs/" + definition)
            elif key == "properties" and isinstance(child, dict):
                for field, value in child.items():
                    visit(value, context + "." + field, pointer + "/properties/" + field, child, "property")
            elif key not in ("description", "x-enum-descriptions", "const", "enum", "default", "examples", "x-catalog"):
                visit(child, context, pointer + "/" + key)

    visit(document, name, "")
    return sites


def catalogue_sites():
    sites = []
    measures = json.loads((ROOT / "catalogues/control-measures.json").read_text())
    for index, entry in enumerate(measures["types"]):
        pointer = f"/types/{index}"
        sites.append(Site("catalogues/control-measures.json", pointer + "/definition", entry["definition"], None, entry["code"], None, "definition"))
        if "note" in entry["definition_source"]:
            sites.append(Site("catalogues/control-measures.json", pointer + "/definition_source/note",
                              entry["definition_source"]["note"], None, entry["code"], None, "note"))
    for name, alias in measures.get("aliases", {}).items():
        if "note" in alias["definition_source"]:
            sites.append(Site("catalogues/control-measures.json", "/aliases/" + name + "/definition_source/note",
                              alias["definition_source"]["note"], None, name, None, "note"))
    airspace = json.loads((ROOT / "catalogues/airspace-types.json").read_text())
    sites.append(Site("catalogues/airspace-types.json", "/description", airspace["description"], None, "airspace-types", None, "root"))
    for key, text in airspace["types"].items():
        sites.append(Site("catalogues/airspace-types.json", "/types/" + key, text, None, "airspace-types", airspace["types"], "value"))
    for key, source in airspace.get("definition_sources", {}).items():
        if "note" in source:
            sites.append(Site("catalogues/airspace-types.json", "/definition_sources/" + key + "/note", source["note"], None,
                              "airspace-types", None, "note"))
    return sites


def schema_paths():
    return [path.relative_to(ROOT).as_posix() for path in (ROOT / "schemas").rglob("*.json")]


def all_sites():
    sites = []
    for path in sorted(schema_paths()):
        if path.startswith("schemas/"):
            sites.extend(schema_sites(path, json.loads((ROOT / path).read_text())))
    return sites + catalogue_sites()


# ---- Tautology: an enumerated value description that only restates its value --------------------

# Template and function words. They carry no meaning of the value.
FILLER = set("""a an the this that these those it its is are be value values identifies identify identified
of for to in on at by with from and or as one each all any some no not only also
which who whose when where than then there here so such other others can may do does""".split())
# Content words that a restatement needs to tell more than the value name: one is a restatement, two are a definition.
TAUTOLOGY_MINIMUM = 2


def _stems(text):
    """Lower-case word stems of a name or a phrase: "ClassB", "air_defense" and "air defence" give the same stems."""
    text = re.sub(r"([a-z])([A-Z0-9])", r"\1 \2", text)
    words = re.findall(r"[A-Za-z]+|\d+", text.replace("_", " ").replace("-", " "))
    return {word.lower()[:5] for word in words}


def _name_stems(name):
    """Stems of a value or field name, with the expansion of each tabled acronym in it."""
    stems = _stems(name)
    for token in [name, name.upper(), *re.split(r"[_\W]+", name)]:
        if token.upper() in templates.ACRONYMS:
            stems |= _stems(templates.ACRONYMS[token.upper()])
    return stems


def tautology_problem(site):
    """A value description whose content words, after template words and the value and field names, are fewer than two."""
    parts = site.path.split("/")
    value = parts[-1]
    if "x-enum-descriptions" in parts:
        field = [part for part in parts[:parts.index("x-enum-descriptions")] if part not in ("items", "properties")][-1:]
    else:
        field = [site.context]
    names = _name_stems(value) | set().union(*(_name_stems(name) for name in field))
    text = PARENTHESES.sub(" ", " ".join(" " if part.startswith("`") else part for part in re.split(r"(`[^`]*`)", site.text)))
    words = [part for word in WORD.findall(text) for part in re.split(r"[-'’]", word)]
    content = {word.lower()[:5] for word in words if word.lower() not in FILLER and len(word) > 1}
    added = content - names
    if len(added) < TAUTOLOGY_MINIMUM:
        return f"'{value}' adds only {sorted(added) or 'nothing'}: {site.text[:80]}"
    return None


# ---- Shape checks ------------------------------------------------------------------------------

def _refs(node):
    if not isinstance(node, dict):
        return []
    found = [node["$ref"]] if "$ref" in node else []
    for keyword in ("allOf", "oneOf", "anyOf"):
        for branch in node.get(keyword, []):
            found.extend(_refs(branch))
    return found


def _refers(node, *names):
    return any(ref.rsplit("/", 1)[-1] in names for ref in _refs(node))


def kind_problem(kind, node):
    if node is None or kind is None:
        return None
    if any("/properties/" in ref for ref in _refs(node)):
        return None  # a reference into another definition's property: its shape is not resolved here
    node_type = node.get("type")
    is_boolean = node_type == "boolean" or isinstance(node.get("const"), bool)
    if kind == "boolean" and not is_boolean:
        return "boolean template on a non-boolean node"
    if is_boolean and kind != "boolean":
        return "boolean node without the boolean template"
    if kind in ("list", "references") and node_type != "array" and not _refs(node):
        return kind + " template on a non-array node"
    if kind == "vertical_limit" and not _refers(node, "VerticalLimit"):
        return "vertical-limit template on a node that is not a VerticalLimit"
    if kind == "altitude_block" and not _refers(node, "AltitudeBlock"):
        return "altitude-block template on a node that is not an AltitudeBlock"
    if kind == "position" and not _refers(node, "GeoPoint", "Point"):
        return "position template on a node that is not a GeoPoint"
    if kind == "count" and node_type not in ("integer", "number"):
        return "count template on a non-numeric node"
    if kind == "enum" and "enum" not in node and not _refs(node) and "items" not in node:
        return "enum template on a node without enumerated values"
    return None


def lint(sites, registry):
    failures = []
    by_container = collections.defaultdict(list)
    for site in sites:
        kind = registry.get(site.text)
        if kind is None:
            failures.append((site, "registry", site.text[:90]))
        for rule, detail in check_text(site.text, kind):
            failures.append((site, rule, detail))
        for problem in normative_problems(site):
            failures.append((site, "normative", problem))
        if site.role == "value":
            problem = tautology_problem(site)
            if problem:
                failures.append((site, "tautology", problem))
        if site.role == "property":
            problem = kind_problem(kind, site.node)
            if problem:
                failures.append((site, "kind", problem))
        if site.siblings is not None:
            by_container[(site.file, id(site.siblings), site.role)].append(site)
    for group in by_container.values():
        texts = collections.Counter(site.text for site in group)
        for site in group:
            if texts[site.text] > 1:
                failures.append((site, "duplicate", "same text as a sibling: " + site.text[:80]))
    return failures


SHALL = re.compile(r"\bshall\b")
_DOCUMENTS = {}


def _document_text(path):
    if path not in _DOCUMENTS:
        file = ROOT / path
        _DOCUMENTS[path] = file.read_text() if file.is_file() else ""
    return _DOCUMENTS[path]


def enforcement_problem(enforcement, path):
    kind, _, target = enforcement.partition(":")
    if kind == "validator":
        module_name, _, function = target.rpartition(".")
        try:
            import importlib
            module = importlib.import_module(module_name)
        except ImportError:
            return "validator module not found: " + module_name
        return None if callable(getattr(module, function, None)) else "validator check not found: " + target
    if path.startswith("schemas/") and '"' + target + '"' not in _document_text(path):
        return f"schema keyword {target} does not occur in {path}"
    return None


def normative_problems(site):
    problems = []
    for sentence in templates.sentences(site.text):
        if not SHALL.search(_strip_literals(sentence)):
            continue
        enforcement = templates.ENFORCED.get(sentence)
        if enforcement is None:
            problems.append("no registered enforcement: " + sentence)
        else:
            problem = enforcement_problem(enforcement, site.file)
            if problem:
                problems.append(problem)
    return problems


def missing_descriptions(path, document):
    """Schema properties without a description. Conditional subschemas are predicates, and `allOf` members
    beside a `$ref` refine the referenced type; both are skipped."""
    found = []

    def visit(node, pointer, conditional=False):
        if isinstance(node, list):
            for index, item in enumerate(node):
                visit(item, pointer + "/" + str(index), conditional)
            return
        if not isinstance(node, dict):
            return
        for key, child in node.items():
            inside = conditional or key in ("if", "then", "else", "not")
            if key == "properties" and isinstance(child, dict):
                for field, value in child.items():
                    if isinstance(value, dict) and not inside and "description" not in value:
                        found.append(pointer + "/properties/" + field)
                    visit(value, pointer + "/properties/" + field, inside)
            elif key == "allOf" and isinstance(child, list) and ("$ref" in node or any(isinstance(item, dict) and "$ref" in item for item in child)):
                # Members beside a `$ref` refine the referenced type; its own definition describes the fields.
                for index, item in enumerate(child):
                    visit(item, pointer + "/allOf/" + str(index), inside or not (isinstance(item, dict) and "$ref" in item))
            elif key not in ("const", "enum", "default", "examples"):
                visit(child, pointer + "/" + key, inside)

    visit(document, "")
    return found


def build_registry():
    """Run the generators in memory so every template call is recorded."""
    from openaix import generate  # imports every description table
    generate.build()
    return templates.REGISTRY


def check_module(name):
    """Check every template text in one table module; returns the number of problems."""
    import importlib
    module = importlib.import_module(name)
    entries = []

    def collect(label, value):
        if isinstance(value, templates.Text):
            entries.append((label, value))
        elif isinstance(value, dict):
            for key, child in value.items():
                collect(label + " " + repr(key), child)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                collect(label + f"[{index}]", child)
        elif isinstance(value, str) and label.split(" ")[0] in ("DESCRIPTIONS", "ENUMS"):
            entries.append((label, value))

    for table in ("DESCRIPTIONS", "ENUMS"):
        collect(table, getattr(module, table, {}))
    problems = 0
    for label, text in entries:
        found = check_text(text)
        if not isinstance(text, templates.Text):
            found.append(("registry", "plain string, not built by a template"))
        for rule, detail in found:
            problems += 1
            print(f"{label}: {rule}: {detail}")
    print(f"{name}: {len(entries)} texts, {problems} problems.")
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=40, help="failures to print per rule")
    parser.add_argument("--module", help="check only the template texts of one table module, such as openaix.describe.tables.orders")
    parser.add_argument("--summary", help="write the failure count per rule to this JSON file")
    args = parser.parse_args()
    if args.module:
        raise SystemExit(1 if check_module(args.module) else 0)
    registry = build_registry()
    sites = all_sites()
    failures = lint(sites, registry)
    for path in sorted(schema_paths()):
        if path.startswith("schemas/"):
            for pointer in missing_descriptions(path, json.loads((ROOT / path).read_text())):
                failures.append((Site(path, pointer, "", None, None, None, "property"), "missing", pointer))
    by_rule = collections.defaultdict(list)
    for site, rule, detail in failures:
        by_rule[rule].append((site, detail))
    for rule, entries in sorted(by_rule.items()):
        print(f"{rule}: {len(entries)} ({RULES[rule]})")
        for site, detail in entries[:args.limit]:
            print(f"  {site.file}{site.path}: {detail}")
    if args.summary:
        Path(args.summary).write_text(json.dumps({rule: len(entries) for rule, entries in sorted(by_rule.items())}, indent=1))
    unique = len({site.text for site in sites})
    print(f"Checked {len(sites)} descriptions ({unique} unique) against {len(RULES)} rules: {len(failures)} failures.")
    if failures:
        raise SystemExit(1)
