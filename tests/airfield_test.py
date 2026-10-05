"""Airfield records: kinds, frequencies, runway ends, links to navigation records, traffic patterns, parking and taxi graphs."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


KDEN = example("resources-kden")
BASTION = example("resources")


def ojms():
    """The OIR Muwaffaq Salti airfield as a standalone document linked to the OIR catalogue."""
    document = deepcopy(BASTION["resources"]["places"]["ojms"])
    document["$schema"] = example("airfield")["$schema"]
    document["resources_ref"] = {"id": BASTION["meta"]["id"], "revision": BASTION["meta"]["revision"]}
    return document


def check(document, catalogue=None):
    validate_document(document, resource_document=catalogue)


class AirfieldKindTests(unittest.TestCase):
    def assertRejected(self, document, catalogue=None):
        with self.assertRaises(ContractError):
            check(document, catalogue)

    def test_fixed_airfield_needs_position_elevation_and_a_runway(self):
        check(ojms(), BASTION)
        for field in ("position", "elevation", "runways"):
            with self.subTest(field=field):
                document = ojms()
                del document[field]
                self.assertRejected(document, BASTION)
        document = ojms()
        document["runways"] = []
        self.assertRejected(document, BASTION)

    def test_farp_needs_position_and_elevation_and_has_no_runways(self):
        farp = example("farp")
        check(farp, BASTION)
        for field in ("position", "elevation"):
            with self.subTest(field=field):
                document = deepcopy(farp)
                del document[field]
                self.assertRejected(document, BASTION)
        document = deepcopy(farp)
        document["runways"] = deepcopy(ojms()["runways"])
        self.assertRejected(document, BASTION)

    def test_carrier_moves_with_its_unit_and_has_no_runways(self):
        carrier = example("carrier")
        self.assertNotIn("position", carrier)
        check(carrier)
        for field, value in (("runways", ojms()["runways"]), ("pads", [{"position": {"latitude": 1, "longitude": 1}}]),
                             ("calm_wind_runway", "21L")):
            with self.subTest(field=field):
                document = deepcopy(carrier)
                document[field] = deepcopy(value)
                self.assertRejected(document)
        document = deepcopy(carrier)
        del document["carrier"]
        self.assertRejected(document)
        document = ojms()
        document["carrier"] = deepcopy(carrier["carrier"])
        self.assertRejected(document, BASTION)

    def test_tacan_is_a_listed_navaid_except_on_a_carrier(self):
        # A fixed airfield has no TACAN field of its own; it lists its TACAN station in navaids.
        document = ojms()
        self.assertEqual(document["navaids"], [{"kind": "control_measure", "id": "ghi"}])
        self.assertEqual(BASTION["resources"]["control_measures"]["ghi"]["class"], "VORTAC")
        document["tacan"] = {"channel": 12, "band": "X"}
        self.assertRejected(document, BASTION)
        carrier = example("carrier")
        self.assertEqual(carrier["carrier"]["tacan"]["channel"], 72)
        carrier["tacan"] = carrier["carrier"].pop("tacan")
        self.assertRejected(carrier)

    def test_carrier_icls_channel_is_one_to_twenty(self):
        document = example("carrier")
        document["carrier"]["icls_channel"] = 21
        self.assertRejected(document)

    def test_coalition_and_operating_hours(self):
        document = ojms()
        document["coalition"] = "green"
        self.assertRejected(document, BASTION)
        prince_hassan = deepcopy(BASTION["resources"]["places"]["prince-hassan"])
        self.assertEqual(prince_hassan["operating_hours"]["periods"][0]["end_day_offset"], 1)

    def test_ato_flights_depart_from_farps_and_carriers(self):
        ato = example("ato-oir")
        departures = {flight["launch"]["departure"] for mission in ato["missions"] for flight in mission["flights"] if "launch" in flight}
        self.assertIn("farp-sage", departures)
        resources = deepcopy(BASTION)
        carrier = example("carrier")
        del carrier["$schema"]
        resources["resources"]["places"]["cvn-72"] = carrier
        ato["missions"][0]["flights"][0]["recovery"]["destination"] = "cvn-72"
        check(ato, resources)
        ato["missions"][0]["flights"][0]["recovery"]["destination"] = "cvn-73"
        with self.assertRaises(ContractError):
            check(ato, resources)


class FrequencyTests(unittest.TestCase):
    def test_station_frequency_has_role_megahertz_and_modulation(self):
        document = ojms()
        roles = {item["role"] for item in document["frequencies"]}
        self.assertTrue({"tower", "ground", "atis", "approach", "pmsv"} <= roles)
        for change in (lambda item: item.update(role="center"), lambda item: item["frequency"].update(unit="kHz"),
                       lambda item: item["frequency"].pop("modulation")):
            with self.subTest(change=change):
                document = ojms()
                change(document["frequencies"][0])
                with self.assertRaises(ContractError):
                    check(document, BASTION)

    def test_band_agrees_with_the_frequency(self):
        document = ojms()
        tower = next(item for item in document["frequencies"] if item["frequency"]["value"] == 120.5)
        self.assertEqual(tower["frequency"]["band"], "vhf")
        tower["frequency"]["band"] = "uhf"
        with self.assertRaisesRegex(ContractError, "outside the uhf band"):
            check(document, BASTION)
        farp = example("farp")
        farp["frequencies"][0]["frequency"]["modulation"] = "AM"
        with self.assertRaisesRegex(ContractError, "frequency modulation"):
            check(farp, BASTION)

    def test_resource_channels_share_the_frequency_band_rule(self):
        resources = deepcopy(BASTION)
        resources["resources"]["channels"]["ops-uhf"]["frequency"]["band"] = "hf"
        with self.assertRaises(ContractError):
            check(resources)

    def test_atis_content_and_calm_wind_runway_name_runway_ends(self):
        document = ojms()
        self.assertEqual(document["atis"]["transition_level"]["reference"], "FL")
        for path in (("calm_wind_runway",), ("atis", "runway_in_use")):
            with self.subTest(path=path):
                document = ojms()
                target = document
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = "09"
                with self.assertRaisesRegex(ContractError, "does not name an end"):
                    check(document, BASTION)


class RunwayTests(unittest.TestCase):
    def test_runway_has_two_reciprocal_ends_and_a_joined_designator(self):
        runway = example("runway")
        self.assertEqual(runway["designator"], "16R/34L")
        check(runway, KDEN)
        document = deepcopy(runway)
        document["designator"] = "16R/34R"
        with self.assertRaises(ContractError):
            check(document, KDEN)
        document = deepcopy(runway)
        document["ends"][1]["designator"] = "34R"
        document["designator"] = "16R/34R"
        with self.assertRaisesRegex(ContractError, "reciprocal"):
            check(document, KDEN)
        document = deepcopy(runway)
        document["ends"].append(deepcopy(document["ends"][0]))
        with self.assertRaises(ContractError):
            check(document, KDEN)

    def test_runway_end_designators_are_unique_and_a_listed_runway_names_its_airfield(self):
        document = ojms()
        document["runways"].append(deepcopy(document["runways"][0]))
        with self.assertRaisesRegex(ContractError, "unique"):
            check(document, BASTION)
        document = ojms()
        document["runways"][0]["airfield"] = "prince-hassan"
        with self.assertRaisesRegex(ContractError, "name the airfield that lists it"):
            check(document, BASTION)

    def test_runway_end_equipment(self):
        end = ojms()["runways"][1]["ends"][1]
        self.assertEqual(end["designator"], "31")
        self.assertEqual(end["lighting"]["approach_lighting"], "SSALR")
        self.assertEqual(end["arresting_gear"][0]["type"], "BAK_12")
        for change in (lambda end: end["arresting_gear"][0].update(type="BAK-99"), lambda end: end["lighting"].update(slope_indicator="LED"),
                       lambda end: end["arresting_gear"][0].pop("distance_from_threshold")):
            with self.subTest(change=change):
                document = ojms()
                change(document["runways"][1]["ends"][1])
                with self.assertRaises(ContractError):
                    check(document, BASTION)

    def test_ils_category_is_on_the_localizer(self):
        localizer = example("localizer")
        self.assertEqual(localizer["ils_category"], "I")
        localizer["ils_category"] = "IIIb"
        with self.assertRaises(ContractError):
            check(localizer, KDEN)


class LinkTests(unittest.TestCase):
    def test_links_resolve_in_both_directions(self):
        airfield = example("airfield")
        self.assertEqual(airfield["localizers"], ["kden-idqq"])
        self.assertEqual(airfield["procedures"], ["kden-i16r"])
        self.assertEqual(airfield["navaids"], [{"kind": "control_measure", "id": "dvv"}])
        for name in ("airfield", "localizer", "procedure", "navaid", "msa", "path-point", "runway"):
            with self.subTest(name=name):
                document = example(name)
                self.assertEqual(document["airfield"] if name != "airfield" else document["id"], "kden")
                check(document, KDEN)
        check(KDEN)

    def test_navaid_listed_by_one_airfield_and_naming_another_is_rejected(self):
        catalogue = deepcopy(KDEN)
        catalogue["resources"]["control_measures"]["dvv"]["airfield"] = "ojms"
        catalogue["resources"]["places"]["ojms"] = deepcopy(BASTION["resources"]["places"]["farp-sage"])
        catalogue["resources"]["places"]["ojms"].pop("controlling_agency")
        with self.assertRaisesRegex(ContractError, "names another airfield"):
            check(catalogue)
        document = ojms()
        document["navaids"].append({"kind": "control_measure", "id": "lsv"})
        document["id"] = "prince-hassan"
        with self.assertRaises(ContractError):
            check(document, BASTION)

    def test_record_that_names_an_airfield_must_be_in_its_list(self):
        for name in ("navaid", "localizer", "procedure"):
            with self.subTest(name=name):
                document = example(name)
                catalogue = deepcopy(KDEN)
                place = catalogue["resources"]["places"]["kden"]
                place[{"navaid": "navaids", "localizer": "localizers", "procedure": "procedures"}[name]] = (
                    [{"kind": "control_measure", "id": "other"}] if name == "navaid" else ["other"])
                with self.assertRaises(ContractError):
                    check(document, catalogue)

    def test_runway_end_localizer_serves_that_end(self):
        document = example("airfield")
        end = document["runways"][3]["ends"][1]
        self.assertEqual(end["designator"], "34L")
        end["localizer"] = "kden-idqq"
        with self.assertRaisesRegex(ContractError, "another runway end"):
            check(document, KDEN)
        localizer = example("localizer")
        localizer["runway"] = "09"
        with self.assertRaisesRegex(ContractError, "not an end of a runway"):
            check(localizer, KDEN)

    def test_unresolved_links_fail(self):
        for field, value in (("localizers", ["kden-ixxx"]), ("procedures", ["kden-i99"]), ("navaids", [{"kind": "control_measure", "id": "xyz"}])):
            with self.subTest(field=field):
                document = example("airfield")
                document[field] = value
                with self.assertRaises(ContractError):
                    check(document, KDEN)

    def test_airport_field_is_renamed_airfield(self):
        for name in ("localizer", "procedure", "msa", "path-point"):
            with self.subTest(name=name):
                document = example(name)
                document["airport"] = document.pop("airfield").upper()
                with self.assertRaises(ContractError):
                    check(document, KDEN)


class TrafficPatternTests(unittest.TestCase):
    def test_pattern_uses_a_named_profile_category_values_and_end_overrides(self):
        document = ojms()
        self.assertEqual(document["traffic_pattern"]["profile"], "usaf-standard")
        profile = BASTION["resources"]["pattern_profiles"]["usaf-standard"]
        self.assertEqual(profile["categories"]["helicopter"]["altitude"], {"value": 500, "unit": "ft", "reference": "AGL"})
        self.assertEqual(document["runways"][1]["ends"][1]["traffic_pattern"], {"direction": "right"})
        document["traffic_pattern"]["profile"] = "navy-standard"
        with self.assertRaises(ContractError):
            check(document, BASTION)

    def test_pattern_altitude_is_agl_or_msl_and_categories_are_closed(self):
        for change in (lambda pattern: pattern.update(altitude={"value": 30, "unit": "flight_level", "reference": "FL"}),
                       lambda pattern: pattern.update(categories={"glider": {"direction": "left"}}),
                       lambda pattern: pattern.update(break_point="downwind")):
            with self.subTest(change=change):
                document = ojms()
                change(document["traffic_pattern"])
                with self.assertRaises(ContractError):
                    check(document, BASTION)

    def test_initial_point_is_an_initial_point_or_a_distance(self):
        document = ojms()
        document["traffic_pattern"]["initial"] = [{"point": {"kind": "control_measure", "id": "ip-silver"}}]
        check(document, BASTION)
        document["traffic_pattern"]["initial"] = [{"point": {"kind": "control_measure", "id": "cedar"}}]
        with self.assertRaises(ContractError):
            check(document, BASTION)

    def test_named_profile_cannot_refer_to_another_profile(self):
        resources = deepcopy(BASTION)
        resources["resources"]["pattern_profiles"]["usaf-standard"]["profile"] = "usaf-standard"
        with self.assertRaisesRegex(ContractError, "another profile"):
            check(resources)


class ParkingAndTaxiTests(unittest.TestCase):
    def test_stands_and_taxi_graph_link_to_each_other_and_to_runway_ends(self):
        document = ojms()
        self.assertTrue(any(stand.get("shelter") for stand in document["parking"]))
        kinds = {node.get("kind") for node in document["taxi"]["nodes"]}
        self.assertTrue({"parking", "hold_short", "runway_connection", "intersection"} <= kinds)
        self.assertIn("taxi", example("airfield"))

    def test_broken_taxi_links_are_rejected(self):
        changes = {
            "edge to an unknown node": lambda doc: doc["taxi"]["edges"][0].update({"to": "z9"}),
            "edge to itself": lambda doc: doc["taxi"]["edges"][0].update({"to": doc["taxi"]["edges"][0]["from"]}),
            "hold short of an unknown end": lambda doc: next(n for n in doc["taxi"]["nodes"] if n.get("kind") == "hold_short").update(runway_end="09"),
            "hold short without an end": lambda doc: next(n for n in doc["taxi"]["nodes"] if n.get("kind") == "hold_short").pop("runway_end"),
            "parking node without a stand": lambda doc: next(n for n in doc["taxi"]["nodes"] if n.get("kind") == "parking").pop("stand"),
            "parking node with an unknown stand": lambda doc: next(n for n in doc["taxi"]["nodes"] if n.get("kind") == "parking").update(stand="west-9"),
            "duplicate stand": lambda doc: doc["parking"].append(deepcopy(doc["parking"][0])),
            "duplicate node": lambda doc: doc["taxi"]["nodes"].append(deepcopy(doc["taxi"]["nodes"][0])),
            "unknown stand category": lambda doc: doc["parking"][0].update(category="jumbo"),
        }
        for label, change in changes.items():
            with self.subTest(label=label):
                document = ojms()
                change(document)
                with self.assertRaises(ContractError):
                    check(document, BASTION)


if __name__ == "__main__":
    unittest.main()
