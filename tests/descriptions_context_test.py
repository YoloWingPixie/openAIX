import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.describe.resolve import DESCRIPTIONS, ENUMS, schema_description
from openaix.describe.tables.common import measure_summary


class DescriptionContextTests(unittest.TestCase):
    def test_interval_text_matches_what_each_interval_accepts(self):
        common = json.loads((ROOT / "schemas/common.schema.json").read_text())["$defs"]
        for name in ("Period", "ScheduledWindow"):
            for field in ("start", "end"):
                with self.subTest(definition=name, field=field):
                    self.assertNotIn("offset", common[name]["properties"][field]["description"])
        self.assertIn("offset", common["Window"]["properties"]["start"]["description"])

    def test_polyarc_turns_is_the_arc_sweep_not_a_flight_pattern(self):
        common = json.loads((ROOT / "schemas/common.schema.json").read_text())["$defs"]
        arc = next(branch for branch in common["Geometry_polyarc"]["properties"]["segments"]["items"]["oneOf"]
                   if branch["properties"]["kind"]["const"] == "arc")
        self.assertNotIn("pattern", arc["properties"]["turns"]["description"])
        racetrack = common["Geometry_racetrack"]["properties"]["turns"]["description"]
        self.assertIn("pattern", racetrack)

    def test_schema_descriptions_are_not_two_definitions_run_together(self):
        records = {path.name: json.loads(path.read_text()) for path in (ROOT / "schemas").rglob("*.schema.json")}
        for name in ("point.schema.json", "airspace.schema.json", "orbit.schema.json"):
            with self.subTest(schema=name):
                text = records[name]["description"]
                self.assertEqual(text, schema_description("measures/" + name.removesuffix(".schema.json")))

    def test_measure_descriptions_keep_their_operative_rule(self):
        # tests/measure_definitions_test.py checks the defining terms of every code; this covers the schema text.
        self.assertIn("without positive identification as friendly", measure_summary("WFZ"))

    def test_tst_engagement_authority_rests_with_the_joint_force_commander(self):
        tst = json.loads((ROOT / "schemas/tst.schema.json").read_text())
        entry = tst["$defs"]["TSTEntry"]
        self.assertIn("joint force commander", entry["description"])
        self.assertIn("may delegate", entry["properties"]["engagement_authority"]["description"])
        for schema in ("tst", "opord", "frago"):
            text = json.dumps(json.loads((ROOT / "schemas" / (schema + ".schema.json")).read_text()))
            with self.subTest(schema=schema):
                self.assertNotIn("JP 3-60", text)
                self.assertNotIn("usually at component level", text)

    def test_assignment_state_active_is_not_the_kill_box_occupancy_term(self):
        state = DESCRIPTIONS[("aco.assignments", "state")]
        self.assertIn("in effect", state)
        self.assertIn("aircraft in it", state)
        self.assertIn("the kill box stays open", DESCRIPTIONS[("aco.assignments", "killbox_status")])

    def test_unsourced_attack_values_say_they_are_openaix_values(self):
        self.assertIn("openAIX value", ENUMS[("PreplannedAttack", "role")]["dead"])
        for value, text in ENUMS[("AttackAssignment", "desired_effect")].items():
            with self.subTest(value=value):
                self.assertIn("openAIX value", text)
        self.assertIn("JP 3-09.3", ENUMS[("PreplannedAttack", "role")]["scheduled_cas"])
