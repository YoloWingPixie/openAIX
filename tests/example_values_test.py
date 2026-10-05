import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "examples").rglob("*.json"))
# The OIR minimal and maximal examples: the curated ACO pair and the generated pair of each schema.
SCENARIO = [path for path in EXAMPLES if path.name.endswith((".maximal.json", ".minimal.json")) or path.parent.name in {"minimal", "maximal"}]
# Whole values that only a generic filler writes, and filler words anywhere in a text.
PLACEHOLDER_VALUES = {"example", "string", "test", "todo", "tbd", "n/a", "xxx", "foo", "bar", "sample"}
PLACEHOLDER_WORDS = re.compile(r"\b(lorem|ipsum|placeholder|dummy|foobar|example)\b", re.IGNORECASE)
# Notes and remarks carry operational content; a disclaimer about the data belongs nowhere, and provenance goes in `source`.
DISCLAIMER = re.compile(r"\b(fictional|simulated|exercise only|example only|not published|not an faa|scenario (data|value)|"
                        r"not real|training only|for simulator use)\b", re.IGNORECASE)
NOTE_KEYS = {"notes", "remarks", "note"}
BANDS = {"hf": (2, 30), "fm": (30, 88), "vhf": (30, 300), "uhf": (225, 400)}
# The DCS Syria map: the OIR scenario lies inside it.
SYRIA_MAP = {"latitude": (30.6, 38.5), "longitude": (32.0, 41.0)}


def walk(node, path=()):
    yield path, node
    if isinstance(node, dict):
        for key, child in node.items():
            yield from walk(child, (*path, key))
    elif isinstance(node, list):
        for index, child in enumerate(node):
            yield from walk(child, (*path, index))


def disclaimer_problems(document):
    problems = []
    for path, value in walk(document):
        key = next((part for part in reversed(path) if isinstance(part, str)), None)
        if key in NOTE_KEYS and isinstance(value, str) and DISCLAIMER.search(value):
            problems.append((path, value))
    return problems


def placeholder_problems(document):
    problems = []
    for path, value in walk(document):
        if isinstance(value, str) and not value.startswith(("urn:", "http")) and "$schema" not in path:
            if value.strip().lower() in PLACEHOLDER_VALUES or PLACEHOLDER_WORDS.search(value):
                problems.append((path, value))
        if isinstance(value, dict):
            # A range is never empty or one unit wide: altitude blocks, vertical limits and time windows.
            for low, high in (("lower", "upper"), ("lower_limit", "upper_limit"), ("start", "end")):
                a, b = value.get(low), value.get(high)
                if isinstance(a, dict) and isinstance(b, dict) and {"value", "unit"} <= a.keys() and a.get("unit") == b.get("unit"):
                    if b["value"] - a["value"] <= 1:
                        problems.append((path, value))
                elif isinstance(a, str) and a == b:
                    problems.append((path, value))
    return problems


class ExampleValueTests(unittest.TestCase):
    def test_there_are_minimal_and_maximal_examples(self):
        self.assertTrue(any(path.parent.name == "minimal" for path in SCENARIO))
        self.assertTrue(any(path.parent.name == "maximal" for path in SCENARIO))

    def test_examples_have_no_placeholder_values_or_empty_ranges(self):
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                self.assertEqual(placeholder_problems(json.loads(path.read_text())), [])

    def test_notes_and_remarks_carry_no_disclaimers(self):
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                self.assertEqual(disclaimer_problems(json.loads(path.read_text())), [])
        self.assertTrue(disclaimer_problems({"notes": "Fictional DCS training scenario; not published airspace."}))
        self.assertTrue(disclaimer_problems({"atis": {"remarks": ["Scenario value for simulator use; not an FAA publication."]}}))
        self.assertFalse(disclaimer_problems({"notes": "Hot 0600-1400Z daily; expect short-notice activation for TIC."}))

    def test_the_check_finds_filler_values(self):
        self.assertTrue(placeholder_problems({"name": "Example"}))
        self.assertTrue(placeholder_problems({"remarks": "Lorem ipsum dolor"}))
        self.assertTrue(placeholder_problems({"altitude": {"lower": {"value": 1000, "unit": "ft", "reference": "MSL"},
                                                           "upper": {"value": 1001, "unit": "ft", "reference": "MSL"}}}))
        self.assertTrue(placeholder_problems({"active": {"start": "2026-10-02T13:00:00Z", "end": "2026-10-02T13:00:00Z"}}))
        self.assertFalse(placeholder_problems({"name": "H4"}))

    def test_minimal_and_maximal_examples_stay_in_the_scenario_and_use_the_right_band(self):
        for path in SCENARIO:
            document = json.loads(path.read_text())
            for location, value in walk(document):
                if not isinstance(value, dict):
                    continue
                if {"latitude", "longitude"} <= value.keys():
                    with self.subTest(example=str(path.relative_to(ROOT)), path=location):
                        for axis, (low, high) in SYRIA_MAP.items():
                            self.assertTrue(low <= value[axis] <= high)
                if value.get("unit") == "MHz" and "band" in value:
                    with self.subTest(example=str(path.relative_to(ROOT)), path=location):
                        low, high = BANDS[value["band"]]
                        self.assertTrue(low <= value["value"] <= high)


if __name__ == "__main__":
    unittest.main()
