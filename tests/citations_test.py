import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.sources.authorities import load_authorities
from openaix.build.measures import catalogue
from openaix.sources.audit import citation_errors, reference_errors, source_reference_errors

AUTHORITIES = load_authorities()
MEASURES = json.loads((ROOT / "sources/measure-definitions.json").read_text())
INVENTORY = json.loads((ROOT / "sources/planning-field-inventory.json").read_text())
KILL_BOX_MTTP = "alssa-kill-box-2009"


def inventory_rows():
    for section in ("documents", "mission_type_mapping", "tasking_families"):
        yield from INVENTORY.get(section, [])


def cited_sources():
    """Every authority key that the source tables cite, as a primary source or a reference."""
    rows = [*MEASURES["codes"].values(), *MEASURES["aliases"].values(), *inventory_rows(), INVENTORY["acmreq"]]
    for row in rows:
        if row.get("source"):
            yield row["source"]
        if row.get("kinds"):
            yield row["kinds"]["source"]
        for reference in row.get("references", []):
            yield reference["source"]


class CitationTests(unittest.TestCase):
    def test_catalogue_citations_and_references_resolve(self):
        self.assertEqual(citation_errors(catalogue(), AUTHORITIES, require_all=True), [])
        self.assertEqual(source_reference_errors(MEASURES, INVENTORY, AUTHORITIES), [])

    def test_a_reference_needs_a_known_authority_and_a_locator(self):
        self.assertEqual(len(reference_errors("TEST", [{"source": "no-such-authority", "locator": "p. 1"}], AUTHORITIES)), 1)
        self.assertEqual(reference_errors("TEST", [{"source": "joint-jp-3-09-3-2014"}], AUTHORITIES),
                         ["TEST: reference to 'joint-jp-3-09-3-2014' has no locator"])

    def test_catalogue_carries_references_of_the_source_table(self):
        entry = next(item for item in catalogue()["types"] if item["code"] == "KB")
        sources = {reference["source"] for reference in entry["definition_source"]["references"]}
        self.assertEqual(sources, {"joint-jp-3-09-3-2014", "usaf-afdp-3-03-2020", KILL_BOX_MTTP})

    def test_kill_box_mttp_is_paraphrased_never_quoted(self):
        for code, row in MEASURES["codes"].items():
            with self.subTest(code=code):
                self.assertFalse(row["source"] == KILL_BOX_MTTP and "source_text" in row)
                self.assertFalse(row.get("kinds", {}).get("source") == KILL_BOX_MTTP and "source_text" in row["kinds"])
                for reference in row.get("references", []):
                    self.assertNotIn("source_text", reference)

    def test_obsolete_brevity_document_is_not_an_authority(self):
        for key, authority in AUTHORITIES.items():
            with self.subTest(authority=key):
                self.assertNotIn("AFTTP 3-1.1", authority["edition"] + " " + authority["title"])
                self.assertNotIn("Operational Brevity Words", authority["title"])

    def test_every_cited_source_is_in_the_bibliography(self):
        for source in cited_sources():
            with self.subTest(source=source):
                self.assertIn(source, AUTHORITIES)

    def test_unread_editions_are_not_cited(self):
        cited = set(cited_sources())
        self.assertNotIn("usaf-afdp-3-01-2023", cited)
        self.assertNotIn("usmc-mcwp-3-23-1-1998", cited)
        self.assertIn("6 September 2019", AUTHORITIES["usaf-afdp-3-01-2019"]["edition"])

    def test_new_authorities_pin_the_copy_that_was_read(self):
        for key in ("usaf-afdp-3-01-2019", "usaf-afdp-3-03-2020", "usaf-afdp-3-60-2021", "joint-jp-3-30-2019",
                    "joint-jp-3-09-3-2014", "alssa-brevity-2023", "alssa-air-control-2021", KILL_BOX_MTTP,
                    "joint-jp-3-09-2019", "joint-jp-3-02-2019", "joint-jp-3-01-2017", "joint-jp-3-52-2014", "joint-jp-3-52-2004",
                    "joint-dod-dictionary-2021", "army-fm-1-02-1-2026", "army-fm-1-02-2-2025", "army-fm-3-52-2016",
                    "army-fm-3-52-2013", "faa-aim-2026", "faa-pcg-2026", "faa-jo-7400-2r-2026", "eu-sera-923-2012-2025",
                    "icao-annex-11-2018", "faa-order-8260-58d-2025", "faa-order-8260-3g-2024", "faa-order-8260-19k-2025",
                    "faa-h-8083-16b-2017", "faa-order-8260-46k-2024"):
            with self.subTest(authority=key):
                self.assertRegex(AUTHORITIES[key].get("sha256", ""), "^[0-9a-f]{64}$")

    def test_initial_point_cites_close_air_support_doctrine(self):
        row = MEASURES["codes"]["IP"]
        self.assertEqual(row["source"], "joint-jp-3-09-3-2014")
        self.assertTrue(row["verified"])
        self.assertIn("III-49", row["locator"])
        self.assertIn("III-73", row["locator"])
        self.assertEqual(row["source_text"], "The IP is the starting point for the run-in to the target.")
        self.assertNotIn("403", row.get("note", ""))

    def test_interception_stays_flagged_unverified_with_support(self):
        row = next(item for item in INVENTORY["mission_type_mapping"] if item["values"].get("mission_type") == "interception")
        self.assertIs(row["verified"], False)
        self.assertEqual({reference["source"] for reference in row["references"]},
                         {"usaf-afdp-3-01-2019", "alssa-brevity-2023"})

    def test_counterair_missions_cite_the_read_afdp_3_01_page(self):
        for mission in ("fighter_sweep", "fighter_escort"):
            row = next(item for item in INVENTORY["mission_type_mapping"] if item["mission_type"] == mission)
            with self.subTest(mission=mission):
                self.assertEqual(row["source"], "usaf-afdp-3-01-2019")
                self.assertIn("page 9", row["locator"])
        sead = next(item for item in INVENTORY["mission_type_mapping"] if item["mission_type"] == "suppression_of_enemy_air_defenses")
        self.assertIn("AOR/JOA air defense system suppression", sead["gap"])
        self.assertNotIn("Area-wide", sead["gap"])

    def test_targeting_documents_do_not_cite_unread_targeting_doctrine(self):
        text = json.dumps(INVENTORY) + json.dumps(MEASURES) + json.dumps(AUTHORITIES)
        for unread in ("JP 3-60", "ATP 3-60", "ATP 3-09.30"):
            with self.subTest(publication=unread):
                self.assertNotIn(unread, text)
        documents = {row["schema"]: row for row in INVENTORY["documents"]}
        self.assertEqual(documents["jiptl"]["source"], "usaf-afdp-3-60-2021")
        self.assertIn("JIPTL cut line not modelled.", documents["jiptl"]["gaps"])
        self.assertEqual(documents["tst"]["source"], "usaf-afdp-3-03-2020")
        self.assertEqual(documents["ato"]["source"], "joint-jp-3-30-2019")

    def test_generated_artifacts_spell_the_joint_integrated_prioritized_target_list(self):
        generated = {path for folder in ("schemas", "catalogues", "examples")
                     for path in (ROOT / folder).rglob("*.json")}
        self.assertTrue(generated)
        for path in sorted(generated):
            text = path.read_text()
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertNotIn("JPITL", text)
                self.assertNotIn("Joint Prioritized Integrated", text)


if __name__ == "__main__":
    unittest.main()
