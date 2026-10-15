"""NOTAM records: the basic items of the ICAO NOTAM format and the links to the location, its runways and procedures."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, validate_document


RESOURCES = json.loads((ROOT / "examples/resources.json").read_text())
REF = {"id": RESOURCES["meta"]["id"], "revision": RESOURCES["meta"]["revision"]}


def notam(identifier="ojms-a0214"):
    return {"$schema": "urn:openaix:schema:notam:0.2.0-draft.1", **deepcopy(RESOURCES["resources"]["notams"][identifier]),
            "resources_ref": deepcopy(REF)}


def check(document):
    validate_document(document, resource_document=RESOURCES)


class NotamTests(unittest.TestCase):
    def test_examples_validate(self):
        for identifier in RESOURCES["resources"]["notams"]:
            with self.subTest(notam=identifier):
                check(notam(identifier))

    def test_basic_items_are_required(self):
        for field in ("number", "location", "code", "effective", "text"):
            document = notam()
            document.pop(field)
            with self.subTest(field=field), self.assertRaises(ContractError):
                check(document)

    def test_number_and_code_follow_the_icao_format(self):
        for field, value in (("code", "MRLC"), ("code", "QMRL"), ("code", "qmrlc"), ("number", {"series": "AA", "number": 214, "year": 2026}),
                             ("number", {"series": "A", "number": 0, "year": 2026}), ("number", {"series": "A", "number": 214})):
            document = notam()
            document[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ContractError):
                check(document)

    def test_location_and_references_resolve(self):
        for field, value in (("location", "kden"), ("affects", [{"kind": "control_measure", "id": "no-such-navaid"}]),
                             ("affects", [{"kind": "instrument_procedure", "id": "no-such-procedure"}])):
            document = notam()
            document[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                check(document)

    def test_runway_is_an_end_of_a_runway_of_the_location(self):
        document = notam()
        document["affects"] = [{"kind": "runway", "designator": "03L"}]
        with self.assertRaises(ContractError) as error:
            check(document)
        self.assertEqual(error.exception.path, "/affects/0/designator")

    def test_lower_limit_is_below_upper_limit(self):
        document = notam("ojms-a0215")
        document["lower"] = {"value": 9000, "unit": "ft", "reference": "MSL"}
        with self.assertRaises(ContractError):
            check(document)


if __name__ == "__main__":
    unittest.main()
