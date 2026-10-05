from pathlib import Path
import sys
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.viewer import response, review_data, example_yaml


class ViewerTests(unittest.TestCase):
    def test_yaml_preserves_source_codes_whitespace_and_multiline_text(self):
        document = {"code": "0012", "boolean_word": "on", "date": "2026-10-02", "raw": "S" + " " * 131,
                    "notes": "First line\nSecond line\n", "value": None, "enabled": True, "count": 2}
        self.assertEqual(yaml.safe_load(example_yaml(document)), document)

    def test_all_viewer_examples_round_trip_through_yaml(self):
        data = review_data()
        for entry in data["examples"]:
            self.assertEqual(yaml.safe_load(entry["yaml"]), entry["document"])
        for pair in data["example_pairs"].values():
            for entry in [pair, *pair["definitions"].values()]:
                for label in ("minimal", "maximal"):
                    self.assertEqual(yaml.safe_load(entry[label]["yaml"]), entry[label]["document"])

    def test_each_schema_has_a_minimal_and_a_maximal_example_in_the_viewer(self):
        data = review_data()
        self.assertFalse(any(entry["path"].startswith(("examples/minimal/", "examples/maximal/")) for entry in data["examples"]))
        for schema in data["schemas"]:
            pair = data["example_pairs"][schema["document"]["$id"]]
            self.assertEqual({"minimal", "maximal"} <= pair.keys(), True)
        common = next(schema["document"] for schema in data["schemas"] if schema["path"] == "schemas/common.schema.json")
        self.assertEqual(set(data["example_pairs"][common["$id"]]["definitions"]), set(common["$defs"]))

    def test_server_exposes_only_review_data_and_assets(self):
        for path in ("/AGENTS.md", "/sources/manifest.json", "/.git/config", "/../README.md",
                     "/app/../../README.md", "/%2e%2e/README.md", "/schemas/common.schema.json"):
            with self.subTest(path=path):
                self.assertIsNone(response(path))
        for path in ("/", "/app/styles.css", "/pages/explorer/model.mjs"):
            with self.subTest(path=path):
                self.assertTrue(response(path)[1])
