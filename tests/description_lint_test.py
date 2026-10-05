"""What a description may and may not say."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.describe import templates as d  # noqa: E402
from openaix.describe import resolve as descriptions  # noqa: E402
from openaix.describe import lint  # noqa: E402


def rules(text):
    return {rule for rule, _ in lint.check_text(text)}


class TemplateTests(unittest.TestCase):
    def test_templates_give_one_sentence_pattern_per_element_kind(self):
        cases = {
            d.reference("agency", "controls this measure"): "This field identifies the agency that controls this measure.",
            d.flag("traffic uses the corridor in one direction only"):
                "The value is `true` when traffic uses the corridor in one direction only.",
            d.vertical_limit("floor", "this component"):
                "This field gives the floor of this component: an altitude with its reference, or the surface.",
            d.list_of("legs", None, ordered=True): "This list contains the legs, in order.",
            d.window("this assignment is in effect"): "This field gives the time interval during which this assignment is in effect.",
            d.quantity("radius of the arc", "Length"): "This field gives the radius of the arc, as a length with its unit.",
            d.root("Kill box", "KB", "A reference system for the coordination of fires"):
                "A kill box (KB) is a reference system for the coordination of fires.",
        }
        for built, expected in cases.items():
            with self.subTest(expected=expected):
                self.assertEqual(built, expected)
                self.assertEqual(rules(built), set())

    def test_first_use_of_an_acronym_is_expanded_and_later_uses_stay_bare(self):
        text = d.statement("An FSCL is a line. Fires short of the FSCL need no coordination with the ATO")
        self.assertEqual(text, "A fire support coordination line (FSCL) is a line. Fires short of the FSCL need no coordination "
                               "with the air tasking order (ATO).")
        self.assertNotIn("acronym", rules(text))

    def test_literals_in_backticks_are_not_words_or_acronyms(self):
        text = d.statement("The `TF` leg ends at the fix in `lower_limit`")
        self.assertEqual(text, "The `TF` leg ends at the fix in `lower_limit`.")
        self.assertNotIn("acronym", rules(text))

    def test_every_built_text_is_registered_with_its_kind(self):
        text = d.flag("the equipment is serviceable")
        self.assertEqual(d.REGISTRY[text], "boolean")


class RuleTests(unittest.TestCase):
    def test_a_description_ends_with_a_period(self):
        self.assertIn("period", rules("Identifier of the agency that controls this measure"))

    def test_acronyms_are_known_and_expanded_on_first_use(self):
        self.assertIn("acronym", rules("The ATO lists missions."))
        self.assertIn("acronym", rules("The QQX lists missions."))
        self.assertIn("acronym", rules("The tasking order (ATO) lists missions."))
        self.assertNotIn("acronym", rules("The air tasking order (ATO) lists missions. The ATO has a period."))

    def test_publication_designators_are_not_acronyms(self):
        self.assertNotIn("acronym", rules("The source is AJP-3.3.5 Annex B and FM 3-09 paragraph B-19."))

    def test_concatenated_and_repeated_descriptions_are_rejected(self):
        self.assertIn("duplicate", rules("This field identifies this mission. This field identifies this mission."))
        self.assertIn("duplicate", rules("This field identifies this mission. This list contains the flights in the mission."))

    def test_a_value_description_that_restates_the_value_is_a_tautology(self):
        def site(value, text, field="airspace_type"):
            return lint.Site("schemas/x.schema.json", f"/properties/{field}/x-enum-descriptions/{value}", text, None, "x",
                             None, "value")
        for value, text in (("ClassB", "This value identifies airspace with the regulatory classification B."),
                            ("final_approach_fix", "This value identifies the final approach fix."),
                            ("cap", "This value identifies combat air patrol (CAP)."),
                            ("off", "Mode 4 is off.")):
            with self.subTest(value=value):
                self.assertIsNotNone(lint.tautology_problem(site(value, text)))
        self.assertIsNone(lint.tautology_problem(site(
            "final_approach_fix", "This value identifies the fix at the start of the final approach segment.", "approach_fix")))
        self.assertIsNone(lint.tautology_problem(site("off", "The IFF transponder does not operate in Mode 4.", "mode_4")))

    def test_placeholders_are_rejected(self):
        for text in ("", "TODO", "Description.", "Field.", "Value"):
            with self.subTest(text=text):
                self.assertIn("placeholder", rules(text))


class SiteTests(unittest.TestCase):
    def site(self, text, node, siblings=None):
        return lint.Site("schemas/test.schema.json", "/properties/x/description", text, node, "test", siblings, "property")

    def test_hand_written_schema_text_fails_the_registry_rule(self):
        failures = lint.lint([self.site("Agency that controls this measure, written by hand.", {"type": "string"})], d.REGISTRY)
        self.assertIn("registry", {rule for _, rule, _ in failures})

    def test_template_kind_fits_the_schema_node(self):
        boolean_text = d.flag("the corridor is one-way")
        failures = lint.lint([self.site(boolean_text, {"type": "string"})], d.REGISTRY)
        self.assertIn("kind", {rule for _, rule, _ in failures})
        plain = d.statement("The corridor carries traffic in one direction")
        failures = lint.lint([self.site(plain, {"type": "boolean"})], d.REGISTRY)
        self.assertIn("kind", {rule for _, rule, _ in failures})

    def test_two_sibling_fields_may_not_share_one_description(self):
        text = d.time("the start of the interval")
        siblings = {"start": {"description": text}, "end": {"description": text}}
        sites = [self.site(text, {"$ref": "#/$defs/DateTime"}, siblings), self.site(text, {"$ref": "#/$defs/DateTime"}, siblings)]
        self.assertIn("duplicate", {rule for _, rule, _ in lint.lint(sites, d.REGISTRY)})


class NormativeTests(unittest.TestCase):
    def site(self, text):
        return lint.Site("schemas/ato.schema.json", "/description", text, None, "ato", None, "schema")

    def test_shall_needs_a_registered_enforcement(self):
        loose = d.statement("Each unit shall report its position")
        self.assertTrue(lint.normative_problems(self.site(loose)))
        rule = d.statement("Resources", d.enforced("The order shall have exactly one catalogue", "schema:oneOf"))
        self.assertEqual(lint.normative_problems(self.site(rule)), [])

    def test_enforcement_must_exist(self):
        missing = d.statement("Routes", d.enforced("A route shall have two points", "validator:openaix.check.measures.no_such_check"))
        self.assertTrue(lint.normative_problems(self.site(missing)))
        absent = d.statement("Routes", d.enforced("A route shall have three points", "schema:minContains"))
        self.assertTrue(lint.normative_problems(self.site(absent)))
        with self.assertRaises(ValueError):
            d.enforced("A route shall have points", "the validator")

    def test_should_needs_no_enforcement(self):
        self.assertEqual(lint.normative_problems(self.site(d.statement("Each unit should report its position"))), [])


class MissingTests(unittest.TestCase):
    def test_every_property_needs_a_description_except_in_conditions(self):
        document = {"properties": {"a": {"type": "string", "description": "x"}, "b": {"type": "string"}},
                    "if": {"properties": {"c": {"const": 1}}}}
        self.assertEqual(lint.missing_descriptions("schemas/x.schema.json", document), ["/properties/b"])


class GenerationTests(unittest.TestCase):
    def test_generation_refuses_schema_text_without_a_template_entry(self):
        artifacts = {"schemas/unlisted.schema.json": {"description": "Builder text.", "properties": {}}}
        with self.assertRaisesRegex(ValueError, "no template entry"):
            descriptions.describe_artifacts(artifacts)

    def test_generation_replaces_source_text_with_the_table_entry(self):
        artifacts = {"schemas/aco.schema.json": {"description": "Imported source wording.", "properties": {}}}
        descriptions.describe_artifacts(artifacts)
        self.assertEqual(artifacts["schemas/aco.schema.json"]["description"], descriptions.DESCRIPTIONS[("aco", None)])


if __name__ == "__main__":
    unittest.main()
