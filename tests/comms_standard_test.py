import json
from copy import deepcopy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.comms_standard import warnings
from openaix.check.contract import ContractError
from openaix.check.validate import validate_document
from openaix.comms.render import render

EXAMPLE = json.loads((ROOT / "examples/comms-standard.json").read_text())
CSG8 = json.loads((ROOT / "standards/csg8/comms-standard.json").read_text())


def changed(edit):
    document = deepcopy(EXAMPLE)
    edit(document)
    return document




class CommsStandardTests(unittest.TestCase):
    def rejected(self, edit, text):
        with self.assertRaises(ContractError) as caught:
            validate_document(changed(edit))
        self.assertIn(text, str(caught.exception))

    def test_examples_and_the_csg8_standard_validate(self):
        for label in ("minimal", "maximal"):
            validate_document(json.loads((ROOT / "examples" / label / "comms-standard.json").read_text()))
        validate_document(EXAMPLE)
        validate_document(CSG8)

    def test_duplicate_codes(self):
        self.rejected(lambda d: d["flights"]["sol"]["members"][1].update(stn="02101"), "duplicate STN")
        self.rejected(lambda d: d["flights"]["sol"]["members"][1].update(laser_code="1711"), "duplicate laser code")
        self.rejected(lambda d: d["flights"]["sol"]["members"][1].update(mode_3="2101"), "duplicate Mode 3")
        self.rejected(lambda d: d["support"]["texaco11"].update(stn="02101"), "duplicate STN")

    def test_tacan_overlap_between_support_and_ships(self):
        self.rejected(lambda d: d["support"]["texaco11"]["tacan"].update(channel=75, band="X"), "duplicate TACAN")

    def test_forbidden_tacan_channels(self):
        def edit(document):
            document["support"]["texaco11"]["tacan"].update(channel=5)
        self.rejected(edit, "TACAN channel is restricted")
        for channel in (4, 6, 7):
            self.rejected(lambda d, c=channel: d["support"]["texaco11"]["tacan"].update(channel=c), "restricted")
        self.rejected(lambda d: d["flights"]["sol"]["tacan_aa"].update(lead={"channel": 7, "band": "Y"}, wing={"channel": 70, "band": "Y"}), "restricted")

    def test_octal_station_numbers(self):
        self.rejected(lambda d: d["flights"]["sol"]["members"][0].update(stn="02181"), "pattern")
        self.rejected(lambda d: d["support"]["texaco11"].update(stn="07089"), "pattern")

    def test_mode_1_second_digit_is_0_to_3(self):
        self.rejected(lambda d: d["squadrons"]["vfa_81"].update(mode_1="14"), "pattern")
        self.rejected(lambda d: d["support"]["texaco11"].update(mode_1="75"), "pattern")
        validate_document(changed(lambda d: d["squadrons"]["vfa_81"].update(mode_1="73")))

    def test_restricted_mode_3(self):
        self.rejected(lambda d: d["support"]["texaco11"].update(mode_3="7500"), "Mode 3 is restricted")

    def test_unresolved_channel(self):
        self.rejected(lambda d: d["flights"]["sol"].update(intraflight="uhf_99"), "unresolved channels")

    def test_wing_tacan_is_63_above_lead(self):
        self.rejected(lambda d: d["flights"]["sol"]["tacan_aa"].update(wing={"channel": 76, "band": "Y"}), "63")

    def test_member_values_follow_the_rules(self):
        self.rejected(lambda d: d["flights"]["sol"]["members"][0].update(mode_3="2105"), "does not match rule")
        self.rejected(lambda d: d["flights"]["sol"]["members"][0].update(laser_code="1721"), "does not match rule")

    def test_frequency_outside_its_band(self):
        self.rejected(lambda d: d["channels"]["uhf_03"]["frequency"].update(value=150.0), "outside the uhf band")

    def test_laser_code_range(self):
        def laser(code):
            return changed(lambda d: d["flights"]["sol"]["members"][0].update(laser_code=code, mode_3="2101"))
        for code in ("1111", "1788"):
            self.assertEqual(warnings(laser(code)), [])
        document = laser("1812")
        document["flights"]["sol"]["members"][0]["laser_code"] = "1812"
        self.assertEqual(len(warnings(document)), 1)
        # 1812 is not a member code of the pattern: widen the rule to test that the document validates with the warning
        document["rules"] = [rule for rule in document["rules"] if rule["field"] != "laser_code"]
        validate_document(document)
        document["flights"]["sol"]["members"][0]["laser_code"] = "1911"
        with self.assertRaises(ContractError):
            validate_document(document)

    def test_csg8_markdown_matches_the_golden_file(self):
        self.assertEqual(render(CSG8), (ROOT / "tests/data/csg8-comms-standard.md").read_text())

    def test_csg8_proposals_are_flagged(self):
        proposed = [name for name in ("flights", "support") for record in CSG8[name].values() if record["status"] == "proposed" and record["proposals"]]
        self.assertTrue(proposed)
        self.assertEqual([entry["code"] for entry in CSG8["laser"]["jtac"] if entry["status"] == "adopted"], ["1688"])


if __name__ == "__main__":
    unittest.main()
