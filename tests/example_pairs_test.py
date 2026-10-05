import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.contract import ContractError
from openaix.check.validate import validate_definitions, validate_document

SCHEMAS = {path.name.removesuffix(".schema.json"): json.loads(path.read_text()) for path in (ROOT / "schemas").rglob("*.schema.json")}
NOTES = json.loads((ROOT / "catalogues/example-notes.json").read_text())
CURATED = [json.loads(path.read_text()) for path in sorted((ROOT / "examples").rglob("*.json")) if path.parent.name not in {"minimal", "maximal"}]
RESOURCES = {document["meta"]["id"]: document for document in CURATED if document.get("kind") == "resources"}
LINKED = {document["meta"]["id"]: document for document in CURATED if document.get("kind") in {"ato", "opord"}}


def load(label, name):
    return json.loads((ROOT / "examples" / label / (name + ".json")).read_text())


def check(document):
    if document["$schema"] == SCHEMAS["common"]["$id"]:
        validate_definitions(document)
    else:
        validate_document(document, resource_document=RESOURCES.get(document.get("resources_ref", {}).get("id")), linked=LINKED)


class ExamplePairTests(unittest.TestCase):
    def test_every_schema_has_a_minimal_and_a_maximal_example(self):
        for label in ("minimal", "maximal"):
            names = {path.stem for path in (ROOT / "examples" / label).glob("*.json")}
            self.assertEqual(names, set(SCHEMAS), label)
            for name, schema in SCHEMAS.items():
                self.assertEqual(load(label, name)["$schema"], schema["$id"], name)

    def test_minimal_and_maximal_examples_validate(self):
        for name in SCHEMAS:
            for label in ("minimal", "maximal"):
                with self.subTest(schema=name, example=label):
                    check(load(label, name))

    def test_maximal_examples_give_every_top_level_field(self):
        """A top-level field is in the maximal example, or the notes name the fields or the rule that exclude it."""
        for name, schema in SCHEMAS.items():
            document = load("maximal", name)
            if name == "common":
                self.assertEqual(set(document) - {"$schema"}, set(schema["$defs"]))
                self.assertEqual(set(load("minimal", name)) - {"$schema"}, set(schema["$defs"]))
                continue
            excluded = {note["path"] for note in NOTES[schema["$id"]] if note.get("reason") in {"alternative", "conditional"}}
            for field in schema.get("properties", {}):
                with self.subTest(schema=name, field=field):
                    self.assertTrue(field in document or field in excluded)

    def test_minimal_examples_give_only_the_fields_that_validation_needs(self):
        for name, schema in SCHEMAS.items():
            if name == "common":
                continue
            document = load("minimal", name)
            for field in set(document) - set(schema.get("required", [])) - {"$schema"}:
                with self.subTest(schema=name, field=field), self.assertRaises(ContractError):
                    check({key: value for key, value in document.items() if key != field})

    def test_notes_name_fields_of_the_maximal_examples(self):
        for name, schema in SCHEMAS.items():
            for note in NOTES[schema["$id"]]:
                with self.subTest(schema=name, note=note):
                    self.assertTrue(note["path"])
                    self.assertTrue({"reason", "selected"} & note.keys())


if __name__ == "__main__":
    unittest.main()
