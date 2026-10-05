"""Description builder. Every description in a generated schema or catalogue is built here.

describe/acronyms.json holds the acronym table.

Each template returns a `Text` (a str with the template `kind`) and records it in REGISTRY.
describe/lint.py fails on a description that is not in REGISTRY, so text that a builder
writes directly into a schema fails the lint.

Writing conventions that the templates rely on:
- write acronyms bare; the builder expands the first use in each description from the acronym table;
- put field names, literal values and codes that are not words in backticks; the lint skips them;
- give slot text in lower case unless it starts with a proper name.
"""
import json
import re

from openaix import ROOT


ACRONYMS = json.loads((ROOT / "tools/openaix/describe/acronyms.json").read_text(encoding="utf-8"))
# Publication and standard designators that look like acronyms but are not expanded.
DESIGNATORS = [re.compile(pattern) for pattern in (
    r"\b(?:AJP|AFDP|JP|FM|ATP|ADP|AFTTP|MCWP|CJCSI)[- ]\d[\w.\-]*", r"\bRFC \d+", r"\bWGS 84\b", r"\bISO \d+", r"\bJSON\b",
    r"\bURN\b", r"\bUSMTF\b", r"\bAR \d+-\d+", r"\b\d+ CFR(?: part)? \d[\w.()]*")]

REGISTRY = {}
# Normative sentences with "shall" and what enforces each: "schema:<keyword>" (a JSON Schema keyword in the
# same schema) or "validator:<module>.<function>" (a named validator check). The lint fails on a "shall"
# sentence that is not here. Unenforced doctrine uses "should".
ENFORCED = {}


class Rule(str):
    """One normative sentence and the check that enforces it; see `enforced`."""

    enforcement = None


def enforced(sentence, by):
    """A "shall" sentence for use as a template part, with its enforcement: "schema:<keyword>" or "validator:<module>.<function>"."""
    if not by.startswith(("schema:", "validator:")):
        raise ValueError("enforcement must be schema:<keyword> or validator:<module>.<function>: " + by)
    rule = Rule(sentence)
    rule.enforcement = by
    return rule


class Text(str):
    """A built description. `kind` names the template that produced it."""

    kind = "statement"


LITERAL = re.compile(r"`[^`]*`")
ACRONYM = re.compile(r"(?<![\w`(/-])([A-Z][A-Z0-9]*[A-Z](?:\(A\))?)(s?)(?![\w`])|\(([A-Z][A-Z0-9]*[A-Z](?:\(A\))?)s?\)")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def sentences(text):
    """Split a description into sentences. Backticked literals never end a sentence."""
    return [part for part in SENTENCE_END.split(text.strip()) if part]


def designator_spans(text):
    spans = []
    for pattern in DESIGNATORS:
        spans.extend(match.span() for match in pattern.finditer(text))
    return spans


def literal_spans(text):
    return [match.span() for match in LITERAL.finditer(text)]


def _inside(position, spans):
    return any(start <= position < end for start, end in spans)


def _capitalize(sentence):
    for index, char in enumerate(sentence):
        if char == "`":
            return sentence
        if char.isalpha():
            return sentence[:index] + char.upper() + sentence[index + 1:]
    return sentence


def _article(before, expansion):
    """Fix a preceding "a"/"an" to fit the expansion that replaces an acronym."""
    match = re.search(r"\b([Aa]n?) $", before)
    if not match:
        return before
    word = match.group(1)
    vowel = expansion[:1].lower() in "aeiou"
    fitted = ("an" if vowel else "a")
    if word[0].isupper():
        fitted = fitted.capitalize()
    return before[:match.start(1)] + fitted + " "


def expand_acronyms(text):
    """Expand the first use of each tabled acronym as "expansion (ABBR)"; later uses stay bare."""
    seen = set()
    output, position = [], 0
    skip = literal_spans(text) + designator_spans(text)
    for match in ACRONYM.finditer(text):
        if _inside(match.start(), skip):
            continue
        if match.group(3):  # an explicit "(ABBR)" written by the author
            seen.add(match.group(3))
            continue
        token, plural = match.group(1), match.group(2)
        if token not in ACRONYMS:
            if plural and token + plural in ACRONYMS:
                token, plural = token + plural, ""
            else:
                continue
        if token in seen:
            continue
        seen.add(token)
        expansion = ACRONYMS[token]
        if plural:
            expansion = pluralize(expansion)
        before = "".join(output) + text[position:match.start()]
        written_before = before.rstrip().lower()
        if written_before.endswith(expansion.lower()):
            output, position = [before + "(" + token + plural + ")"], match.end()
            continue
        output, position = [_article(before, expansion) + expansion + " (" + token + plural + ")"], match.end()
    return "".join(output) + text[position:]


def pluralize(phrase):
    head, _, tail = phrase.partition(" of ")
    words = head.split(" ")
    last = words[-1]
    if last.endswith(("s", "x", "ch", "sh")):
        last += "es"
    elif last.endswith("y") and last[-2:-1] not in "aeiou":
        last = last[:-1] + "ies"
    else:
        last += "s"
    words[-1] = last
    return " ".join(words) + ((" of " + tail) if tail else "")


def finish(kind, *parts):
    """Join sentence parts into one description: expand acronyms, capitalize, end each sentence with a period."""
    pieces, rules = [], []
    for part in parts:
        if not part:
            continue
        enforcement = getattr(part, "enforcement", None)
        part = " ".join(str(part).split())
        if not part.endswith((".", "?", "!")):
            part += "."
        if enforcement:
            rules.append((sum(len(sentences(piece)) for piece in pieces), enforcement))
        pieces.append(_capitalize(part))
    if not pieces:
        raise ValueError("empty description")
    text = expand_acronyms(" ".join(pieces))
    final = [_capitalize(sentence) for sentence in sentences(text)]
    for index, enforcement in rules:
        ENFORCED[final[index]] = enforcement
    text = " ".join(final)
    result = Text(text)
    result.kind = kind
    previous = REGISTRY.get(text)
    if previous and previous != kind:
        kind = previous if previous != "statement" else kind
    REGISTRY[text] = kind
    result.kind = kind
    return result


def _clause(text):
    return text.strip().rstrip(".")


# ---- Templates, one per element kind ----------------------

MASS_NOUNS = {"airspace", "weather", "information", "data", "guidance", "fuel", "traffic", "equipment", "personnel", "terrain",
              "intelligence", "logistics", "ammunition", "ordnance", "fire support", "situation", "sustainment",
              "execution", "command", "control", "signal", "lighting", "command and signal"}


def _lower_first(phrase):
    """Lower-case the first letter of a sentence-case phrase; keep acronyms and proper names."""
    words = phrase.split(" ")
    first = words[0]
    if first in ("A", "An", "The", "One", "Each", "This", "These", "Its", "Two"):
        return first.lower() + phrase[len(first):]
    proper = len(words) > 1 and words[1][:1].isupper() and not words[1].isupper()
    if first[:1].isupper() and first[1:] == first[1:].lower() and not proper:
        return first[:1].lower() + phrase[1:]
    return phrase


def _subject(name):
    """'a kill box', 'an area', 'rules of engagement', 'airspace': the name as the subject of a sentence, and its verb."""
    phrase = _lower_first(name)
    head = phrase.split(" of ")[0].split(" ")[-1].lower()
    if phrase.lower() in MASS_NOUNS or head in MASS_NOUNS:
        return phrase, "is"
    first = phrase.split(" ")[0].lower()
    if head.endswith("s") and not head.endswith(("ss", "us", "is")) or first.endswith("s") and " of " in phrase \
            and not first.endswith(("ss", "us", "is")):
        return phrase, "are"
    return ("an " if phrase[:1].lower() in "aeiou" and not phrase.lower().startswith(("uni", "one", "eu", "us")) else "a ") + phrase, "is"


def _definition(name, abbr, definition):
    """Head sentence of a root or object: '<A name> (<ABBR>) is <definition>.' The definition is a noun phrase."""
    subject, verb = _subject(name)
    subject += (" (" + abbr + ")" if abbr else "")
    if not definition:
        return "This record is " + (subject if verb == "is" else "a record of " + subject)
    definition = _lower_first(str(definition).strip())
    if definition.startswith("in ") and ", " in definition.split(".")[0]:
        return subject + " " + verb + ", " + definition  # "is, in air defence, airspace ..."
    return subject + " " + verb + " " + definition


def _the(phrase):
    """'the <phrase>', unless the phrase starts with its own determiner."""
    phrase = _clause(phrase)
    first = phrase.split(" ")[0].lower()
    if first in ("a", "an", "the", "one", "each", "all", "this", "these", "its", "their", "any", "two", "some", "no"):
        return _lower_first(phrase)
    return "the " + _lower_first(phrase)


def root(name, abbr=None, definition=None, *notes):
    """Schema root: "<A name> (<ABBR>) is <definition>." The name is a technical name in sentence case."""
    return finish("root", _definition(name, abbr, definition), *notes)


def entity(name, definition, *notes, abbr=None):
    """Object or $defs entry: "<A name> is <definition>."."""
    return finish("object", _definition(name, abbr, definition), *notes)


def identifier(subject, unique_in=None, *notes):
    """Identifier field: "This field identifies this <subject>." [+ "Each <subject> in <scope> has a different identifier."]"""
    subject = _clause(subject)
    extra = f"Each {subject} in {_clause(unique_in)} has a different identifier" if unique_in else None
    return finish("identifier", "This field identifies this " + subject, extra, *notes)


def reference(target, clause=None, *notes):
    """Reference to X: "This field identifies the <X> that <clause>."."""
    head = "This field identifies " + _the(target) + (" that " + _clause(clause) if clause else "")
    return finish("reference", head, *notes)


def references(targets, clause=None, *notes):
    """List of references: "This list identifies the <Xs> that <clause>."."""
    head = "This list identifies " + _the(targets) + (" that " + _clause(clause) if clause else "")
    return finish("references", head, *notes)


def name(subject, *notes):
    """Display name: "This field gives the name of this <subject>, for display."."""
    return finish("name", "This field gives the name of this " + _clause(subject) + ", for display", *notes)


def discriminator(subject, *notes):
    """Constant kind field: "The value identifies this record as <subject>."."""
    return finish("discriminator", "The value identifies this record as " + _clause(subject), *notes)


def enum(subject, *notes):
    """Enumerated field: "This field gives <the subject>, as one of the enumerated values."."""
    return finish("enum", "This field gives " + _the(subject) + ", as one of the enumerated values", *notes)


def value(meaning, *notes):
    """One enumerated value, as a noun phrase: "This value identifies <meaning>."."""
    return finish("value", "This value identifies " + _lower_first(_clause(meaning)), *notes)


def value_sentence(*sentences):
    """One enumerated value whose meaning is already one or more full sentences."""
    return finish("value", *sentences)


def values(table):
    """Descriptions of each enumerated value, from {value: meaning or Text}."""
    return {key: text if isinstance(text, Text) else value(text) for key, text in table.items()}


def flag(condition, otherwise=None, *notes):
    """Boolean: "The value is `true` when <condition>." with an optional "The value is `false` when <otherwise>."."""
    return finish("boolean", "The value is `true` when " + _clause(condition),
                  ("The value is `false` when " + _clause(otherwise)) if otherwise else None, *notes)


QUANTITIES = {"Length": "a length", "Altitude": "an altitude", "Elevation": "an elevation", "Speed": "a speed",
              "Frequency": "a frequency", "Bearing": "a bearing", "Offset": "an offset", "LaserCode": "a laser code"}


def quantity(subject, primitive=None, unit=None, *notes):
    """Quantity: "This field gives the <subject>, as <a length> with its unit." or "..., in <unit>."."""
    if primitive:
        head = "This field gives " + _the(subject) + ", as " + QUANTITIES[primitive] + " with its unit"
    elif unit:
        head = "This field gives " + _the(subject) + ", in " + unit
    else:
        raise ValueError("quantity needs a primitive or a unit: " + subject)
    if primitive in ("Altitude", "Bearing"):
        head += " and reference"
    return finish("quantity", head, *notes)


def count(subject, *notes):
    """Count: "This field gives the number of <subject>."."""
    return finish("count", "This field gives the number of " + _clause(subject), *notes)


LIMIT_FORMS = {"floor": "an altitude with its reference, or the surface",
               "ceiling": "an altitude with its reference, or no limit",
               "any": "an altitude with its reference, the surface or no limit"}


def vertical_limit(edge, of, form=None, *notes):
    """Vertical limit: "This field gives the floor of <x>: an altitude with its reference, or the surface."."""
    words = {"floor": "floor", "ceiling": "ceiling", "minimum": "lowest floor", "maximum": "highest ceiling"}
    form = form or LIMIT_FORMS["floor" if edge in ("floor", "minimum") else "ceiling"]
    return finish("vertical_limit", "This field gives the " + words[edge] + " of " + _clause(of) + ": " + _clause(form), *notes)


def altitude_block(of, *notes):
    """Altitude block: "This field gives the vertical limits of <x>, as an altitude block with a floor and a ceiling."."""
    return finish("altitude_block", "This field gives the vertical limits of " + _clause(of)
                  + ", as an altitude block with a floor and a ceiling", *notes)


def time(event, *notes):
    """Time point: "This field gives the time at which <event>." or, for a noun, "This field gives the time of <event>."."""
    event = _clause(event)
    head = ("the time " + event) if event.startswith(("at which", "before which", "after which", "until which")) else ("the time of " + event)
    return finish("time", "This field gives " + head, *notes)


def window(clause, *notes):
    """Time window: "This field gives the time interval during which <clause>."."""
    return finish("window", "This field gives the time interval during which " + _clause(clause), *notes)


def geometry(of, shapes=None, *notes, part="Horizontal geometry"):
    """Geometry: "This field gives the <part> of <x>: <shapes>."."""
    head = "This field gives the " + _lower_first(part) + " of " + _clause(of) + (": " + _clause(shapes) if shapes else "")
    return finish("geometry", head, *notes)


def position(of, *notes):
    """Position: "This field gives the geographic position of <x>, as latitude and longitude."."""
    return finish("position", "This field gives the geographic position of " + _clause(of) + ", as latitude and longitude", *notes)


def list_of(items, clause=None, *notes, ordered=False):
    """Array: "This list contains the <items> that <clause>." or "This list contains, in order, the <items> ..."."""
    if ordered and not clause:
        head = "This list contains " + _the(items) + ", in order"
    else:
        head = "This list contains " + (", in order, " if ordered else "") + _the(items) + (" that " + _clause(clause) if clause else "")
        head = head.replace("contains , in order, ", "contains, in order, ")
    return finish("list", head, *notes)


def map_of(items, *notes, key="identifier"):
    """Object keyed by identifier: "This map contains the <items>. The key of each item is its <key>."."""
    return finish("map", "This map contains " + _the(items), "The key of each item is its " + key, *notes)


def extension(*notes):
    """Namespaced extension data."""
    return finish("extension", "This field contains extension data in groups",
                  "The namespace of each group identifies the application or standard that supplies its data",
                  "The group `sim` contains the simulator data of the record", *notes)


def source(subject, *notes):
    """Provenance: "This field gives the source of this <subject>."."""
    return finish("source", "This field gives the source of this " + _clause(subject), *notes)


def text(subject, *notes):
    """Free text: "This field gives the <subject>, as free text."."""
    return finish("text", "This field gives " + _the(subject) + ", as free text", *notes)


def statement(*parts):
    """Definition or statement of fact in plain present tense, for text that no other template fits."""
    return finish("statement", *parts)
