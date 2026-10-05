from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.examples.aco import build_aco_example
from openaix.check.validate import ContractError, schemas, validate_document


class AcoExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = schemas()[0]["aco"]
        cls.version = cls.schema["properties"]["schema_version"]["const"]

    def test_broken_control_point_and_out_of_period_assignment_are_rejected(self):
        document = build_aco_example(self.version)
        document["assignments"][0]["control_points"][0]["id"] = "missing-gate"
        with self.assertRaises(ContractError):
            validate_document(document)
        document = build_aco_example(self.version)
        document["assignments"][0]["effective"]["end"] = "2026-10-02T16:00:00Z"
        with self.assertRaises(ContractError):
            validate_document(document)
