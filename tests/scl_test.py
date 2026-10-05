from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.scl import dcs_stations
from openaix.check.validate import ContractError, schemas, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


def mission(ato, identifier):
    return next(item for item in ato["missions"] if item["id"] == identifier)


def dcs(record):
    return record.get("extensions", {}).get("sim", {}).get("dcs", {})


def station(scl, label):
    return next(entry for entry in scl["stations"] if entry["station"] == label)


class SCLRecordTests(unittest.TestCase):
    def setUp(self):
        self.resources, self.scl = example("resources"), example("scl")

    def rejects(self, document, path_prefix, resources=None):
        with self.assertRaises(ContractError) as error:
            validate_document(document, resource_document=resources)
        self.assertTrue(error.exception.path.startswith(path_prefix), error.exception.path + ": " + str(error.exception))

    def test_standalone_and_catalogue_loads_validate(self):
        validate_document(self.scl, resource_document=self.resources)
        validate_document(self.resources)
        self.assertEqual(self.scl["id"], "f16-ai")
        records, _ = schemas()
        self.assertEqual(records["resources"]["$defs"]["ResourceData"]["properties"]["scls"]["additionalProperties"]["$ref"], records["scl"]["$id"])
        self.assertNotIn("dcs_clsid", records["resources"]["$defs"]["Store"]["properties"])
        self.assertEqual(records["scl"]["properties"]["aircraft_type"]["x-catalog"], "aircraft_types")

    def test_every_weapon_mission_of_the_oir_ato_has_a_load(self):
        ato = example("ato-oir")
        unarmed = {"kc-135r", "e-3a", "mq-9", "c-130j", "hh-60g", "ch-47f"}
        for item in ato["missions"]:
            for flight in item["flights"]:
                with self.subTest(flight=flight["id"]):
                    self.assertEqual("configuration" in flight, flight["aircraft_type"] not in unarmed)

    def test_quantities_are_positive(self):
        for path in (("stores", 0, "quantity"), ("stations", 0, "items", 0, "quantity")):
            document = deepcopy(self.scl)
            node = document
            for key in path[:-1]:
                node = node[key]
            node[path[-1]] = 0
            with self.subTest(path=path):
                self.rejects(document, "/" + "/".join(map(str, path)), self.resources)

    def test_bill_of_stores_agrees_with_the_stations(self):
        document = deepcopy(self.scl)
        document["stores"][0]["quantity"] += 1
        self.rejects(document, "/stations", self.resources)
        document = deepcopy(self.scl)
        document["stores"].append(deepcopy(document["stores"][0]))
        self.rejects(document, "/stores/", self.resources)
        document = deepcopy(self.scl)
        document["stations"].append(deepcopy(document["stations"][0]))
        self.rejects(document, "/stations/", self.resources)
        document = deepcopy(self.scl)
        document.pop("stations")
        validate_document(document, resource_document=self.resources)

    def test_racks_and_pod_roles_keep_their_store_types(self):
        document = deepcopy(self.scl)
        station(document, "3")["rack"] = "aim-120c"
        self.rejects(document, "/stations/2/rack", self.resources)
        resources = deepcopy(self.resources)
        resources["resources"]["stores"]["aim-120c"]["role"] = "targeting"
        self.rejects(resources, "/resources/stores/aim-120c")

    def test_mission_roles_belong_to_their_tasking_family(self):
        document = deepcopy(self.scl)
        document["missions"].append({"tasking": "counterair", "role": "sead"})
        self.rejects(document, "/missions", self.resources)
        document["missions"][-1] = {"tasking": "cap", "role": "strike"}
        self.rejects(document, "/missions", self.resources)
        document["missions"][-1] = {"tasking": "counterland_control", "role": "scar"}
        validate_document(document, resource_document=self.resources)

    def test_store_references_resolve(self):
        document = deepcopy(self.scl)
        document["stores"][0]["store"] = "gbu-99"
        self.rejects(document, "/stores/0/store", self.resources)


class DCSStationTests(unittest.TestCase):
    def setUp(self):
        self.resources, self.scl = example("resources"), example("scl")

    def rejects(self, document, path):
        with self.assertRaises(ContractError) as error:
            validate_document(document, resource_document=self.resources)
        self.assertTrue(error.exception.path.startswith(path), error.exception.path)

    def dcs_type(self, scl):
        return dcs(self.resources["resources"]["aircraft_types"][scl["aircraft_type"]]).get("type")

    def test_station_data_covers_the_dcs_aircraft_of_the_oir_loads(self):
        types = {self.dcs_type(scl) for scl in self.resources["resources"]["scls"].values()} - {None}
        self.assertEqual(types, set(dcs_stations()))
        self.assertEqual(dcs_stations()["F-16C_50"]["10"]["label"], "5L")

    def test_station_number_label_and_clsid_must_exist_on_the_dcs_aircraft(self):
        data = ("stations", 0, "extensions", "sim", "dcs")
        for field, value in (("pylon", 13), ("label", "5R"), ("clsid", "{GBU-31}")):
            document = deepcopy(self.scl)
            dcs(document["stations"][0])[field] = value
            with self.subTest(field=field):
                self.rejects(document, "/" + "/".join(map(str, (*data, field))))

    def test_every_oir_station_is_a_dcs_pylon_load(self):
        for identifier, scl in self.resources["resources"]["scls"].items():
            for entry in scl.get("stations", []):
                data = dcs(entry)
                if not data:
                    continue
                pylon = dcs_stations()[self.dcs_type(scl)][str(data["pylon"])]
                with self.subTest(scl=identifier, station=entry["station"]):
                    self.assertEqual(data["label"], pylon["label"])
                    self.assertIn(data["clsid"], pylon["clsids"])

    def test_aircraft_without_station_data_is_not_checked(self):
        document = deepcopy(self.scl)
        document["aircraft_type"] = "ea-18g"
        dcs(station(document, "1"))["pylon"] = 40
        validate_document(document, resource_document=self.resources)

    def test_load_names_the_dcs_type_of_the_aircraft_of_the_scl(self):
        document = deepcopy(self.scl)
        dcs(document)["payload"]["unit_type"] = "FA-18C_hornet"
        self.rejects(document, "/extensions/sim/dcs/payload/unit_type")

    def test_dcs_data_keys_follow_the_record(self):
        for data, path in (({"pylon": 3, "clsid": "{GBU-31}", "type": "F-16C_50"}, "/stations/0/extensions"),
                           ({"bindings": [{"kind": "unit", "object_id": 3}]}, "/stations/0/extensions"),
                           ({"label": "3"}, "/stations/0/extensions")):
            document = deepcopy(self.scl)
            document["stations"][0]["extensions"] = {"sim": {"dcs": data}}
            with self.subTest(data=data):
                self.rejects(document, path)


class SCLReferenceTests(unittest.TestCase):
    def setUp(self):
        self.ato, self.resources = example("ato-oir"), example("resources")

    def rejects(self, path, document=None, resources=None):
        with self.assertRaises(ContractError) as error:
            validate_document(document or self.ato, resource_document=resources or self.resources)
        self.assertTrue(error.exception.path.startswith(path), error.exception.path + ": " + str(error.exception))

    def test_oir_order_and_target_lists_resolve_their_loads(self):
        validate_document(self.ato, resource_document=self.resources)
        for name in ("tst", "jiptl"):
            validate_document(example(name), resource_document=self.resources)

    def test_flight_load_references_resolve(self):
        flight = mission(self.ato, "strike-cobalt")["flights"][0]
        flight["configuration"]["primary_scl"] = "f15e-missing"
        self.rejects("/missions/3/flights/0/configuration/primary_scl")
        flight["configuration"]["primary_scl"] = "f15e-strike"
        flight["configuration"]["alternatives"] = [{"scl": "f15e-missing", "condition": "Weather below minimums."}]
        self.rejects("/missions/3/flights/0/configuration/alternatives/0/scl")

    def test_flight_and_load_have_the_same_aircraft_type(self):
        mission(self.ato, "strike-cobalt")["flights"][0]["configuration"]["primary_scl"] = "f16-ai"
        self.rejects("/missions/3/flights/0/configuration/primary_scl")

    def test_primary_load_lists_the_tasking_of_the_mission(self):
        mission(self.ato, "sweep")["flights"][0]["configuration"]["secondary_scl"] = "f15c-aa"
        validate_document(self.ato, resource_document=self.resources)
        mission(self.ato, "strike-cobalt")["flights"][0]["configuration"]["primary_scl"] = "f15e-scar"
        self.rejects("/missions/3/flights/0/configuration/primary_scl")

    def test_weapon_loads_name_stores_that_the_flight_carries(self):
        strike = mission(self.ato, "strike-cobalt")["tasking"]["assignments"][0]
        strike["weaponeering"][0]["store"] = "agm-88c"
        strike["weaponeering"][0].pop("scl")
        self.rejects("/missions/3/tasking/assignments/0/weaponeering/0/store")
        strike["weaponeering"][0].update({"store": "gbu-31v3", "quantity": 5})
        self.rejects("/missions/3/tasking/assignments/0/weaponeering/0/quantity")
        strike["weaponeering"][0].update({"quantity": 4, "scl": "f16-ai"})
        self.rejects("/missions/3/tasking/assignments/0/weaponeering/0/scl")

    def test_required_stores_are_carried_by_an_assigned_flight(self):
        mission(self.ato, "ai-zinc")["tasking"]["assignments"][0]["required_stores"] = ["agm-88c"]
        self.rejects("/missions/15/tasking/assignments/0/required_stores/0")

    def test_target_list_engagement_means_name_a_carried_store(self):
        jiptl = example("jiptl")
        jiptl["targets"][0]["authorized_engagement_means"][0]["store"] = "agm-88c"
        self.rejects("/targets/0/authorized_engagement_means/0/store", jiptl)

    def test_catalogue_key_is_the_load_identifier(self):
        resources = deepcopy(self.resources)
        resources["resources"]["scls"]["f16-cap"]["id"] = "f16-cap-2"
        with self.assertRaises(ContractError) as error:
            validate_document(resources)
        self.assertEqual(error.exception.path, "/resources/scls/f16-cap/id")


if __name__ == "__main__":
    unittest.main()
