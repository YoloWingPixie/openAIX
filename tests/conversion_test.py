import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, validate_document


def example(name):
    return json.loads((ROOT / "examples" / name).read_text())


def keywords(node, name):
    if isinstance(node, dict):
        return (name in node) + sum(keywords(child, name) for child in node.values())
    if isinstance(node, list):
        return sum(keywords(child, name) for child in node)
    return 0


class ConversionTests(unittest.TestCase):
    def test_optional_ato_field_cannot_be_null(self):
        document, resources = example("ato-oir.json"), example("resources.json")
        validate_document(document, resource_document=resources)
        document["missions"][0]["flights"][0]["notes"] = None
        with self.assertRaises(ContractError) as raised:
            validate_document(document, resource_document=resources)
        self.assertEqual(raised.exception.path, "/missions/0/flights/0/notes")

    def test_optional_spins_field_cannot_be_null(self):
        document = example("spins.json")
        linked = {"resource_document": example("resources.json"), "linked": {"oir-ato": example("ato-oir.json"), "oir-opord": example("opord.json")}}
        validate_document(document, **linked)
        document["period"] = None
        with self.assertRaises(ContractError) as raised:
            validate_document(document, **linked)
        self.assertEqual(raised.exception.path, "/period")

    def test_no_schema_claims_openapi_discriminator_dispatch(self):
        for path in sorted((ROOT / "schemas").rglob("*.schema.json")):
            with self.subTest(schema=str(path.relative_to(ROOT))):
                self.assertEqual(keywords(json.loads(path.read_text()), "discriminator"), 0)

    def test_every_tasking_family_dispatches_by_const_kind(self):
        document, resources = example("ato-oir.json"), example("resources.json")
        kinds = {mission["tasking"]["kind"] for mission in document["missions"]}
        self.assertEqual(len(kinds), 14)
        validate_document(document, resource_document=resources)
        for index, mission in enumerate(document["missions"]):
            with self.subTest(kind=mission["tasking"]["kind"]):
                changed = json.loads(json.dumps(document))
                changed["missions"][index]["tasking"]["kind"] = "not_a_tasking"
                with self.assertRaises(ContractError):
                    validate_document(changed, resource_document=resources)

if __name__ == "__main__":
    unittest.main()
