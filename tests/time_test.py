import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import FORMAT_CHECKER, ContractError, validate_document


def roz():
    return json.loads((ROOT / "examples/aco-oir.maximal.json").read_text())


class TimeTests(unittest.TestCase):
    def test_date_time_format_is_enforced(self):
        self.assertIn("date-time", FORMAT_CHECKER.checkers)
        self.assertFalse(FORMAT_CHECKER.conforms("bad", "date-time"))
        self.assertFalse(FORMAT_CHECKER.conforms("2026-10-02T06:00:00", "date-time"))

    def test_malformed_order_period_is_rejected_with_its_path(self):
        document = roz()
        document["period"]["start"] = "bad"
        with self.assertRaises(ContractError) as raised:
            validate_document(document)
        self.assertEqual(raised.exception.path, "/period/start")

    def test_time_without_offset_is_rejected(self):
        document = roz()
        document["period"]["end"] = "2026-10-03T06:00:00"
        with self.assertRaises(ContractError) as raised:
            validate_document(document)
        self.assertEqual(raised.exception.path, "/period/end")

    def test_malformed_rfc3339_values_are_rejected(self):
        for value in ("2026-13-02T06:00:00Z", "2026-10-02T25:00:00Z", "2026-10-02T06:00Z", "2026-10-02T06:00:00+2:00",
                      "20261002T060000Z", "021245ZOCT26", "2026-10-02", ""):
            with self.subTest(value=value):
                document = roz()
                document["period"]["start"] = value
                with self.assertRaises(ContractError) as raised:
                    validate_document(document)
                self.assertEqual(raised.exception.path, "/period/start")

    def test_offset_times_are_ordered_as_instants(self):
        document = roz()
        start, end = document["period"]["start"], document["period"]["end"]
        # The same end instant written in a UTC-7 offset still ends after the start.
        self.assertTrue(start.endswith("Z") and end.endswith("Z"))
        document["period"]["end"] = end.replace("T15:", "T08:").replace("Z", "-07:00")
        validate_document(document)
        document["period"]["end"] = start.replace("Z", "+01:00")
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_lowercase_separators_still_order_the_window(self):
        document = roz()
        start, end = document["period"]["start"], document["period"]["end"]
        valid = copy.deepcopy(document)
        valid["period"] = {"start": start.lower(), "end": end.lower()}
        validate_document(valid)
        document["period"] = {"start": end.lower(), "end": start.lower()}
        with self.assertRaises(ContractError) as raised:
            validate_document(document)
        self.assertEqual(raised.exception.code, "non-positive time window")


if __name__ == "__main__":
    unittest.main()
