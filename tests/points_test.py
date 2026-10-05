from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator
from referencing import Resource

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.build.points import build_point, point_location
from openaix.check.validate import schemas


class PointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        records, registry = schemas()
        common = deepcopy(records["common"])
        cls.common_id = common["$id"]
        common["$defs"]["PointLocation"] = point_location(cls.common_id)
        cls.registry = registry.with_resource(cls.common_id, Resource.from_contents(common))
        source = records.get("measures/fix", records.get("measures/point"))
        version = source["$id"].rsplit(":", 1)[1]
        cls.point = build_point(source, "urn:openaix:schema:", version, cls.common_id)
        cls.validator = Draft202012Validator(cls.point, registry=cls.registry)

    def point_document(self):
        return {"id": "north-gate", "name": "North Gate", "type": "POINT", "roles": ["gate", "ingress"],
                "position": {"latitude": 37.1, "longitude": -115.5}, "active": {"continuous": True}}

    def test_point_accepts_combined_roles_and_described_location_without_provenance(self):
        document = self.point_document()
        document["roles"].append("egress")
        self.validator.validate(document)
        document.pop("position")
        document["position_description"] = "Road junction north of the field"
        self.validator.validate(document)

    def test_point_rejects_missing_location_and_unsupported_or_duplicate_roles(self):
        mutations = [lambda doc: doc.pop("position"), lambda doc: doc.update(roles=[]),
                     lambda doc: doc.update(roles=["ingress", "ingress"]), lambda doc: doc.update(roles=["anchor"]),
                     lambda doc: doc["position"].update(latitude=91)]
        for mutate in mutations:
            document = self.point_document()
            mutate(document)
            with self.subTest(document=document):
                self.assertFalse(self.validator.is_valid(document))

    def test_point_preserves_navigation_and_gateway_operational_fields_together(self):
        document = self.point_document()
        document.update({
            "aor": "north-aor", "route": "north-route", "contact_agency": "contact-control",
            "handover_agency": "receiving-control", "reference_agency": "reference-control",
            "channels": ["guard"], "instructions": ["Contact control before crossing."],
            "extensions": {"sim": {"dcs": {"bindings": [{"kind": "drawing", "name": "North Gate", "primitive_type": "Icon", "icon": "star"}]}}}})
        self.validator.validate(document)
        encoded = json.loads(json.dumps(document))
        self.validator.validate(encoded)
        self.assertEqual(encoded, document)
        document["aor"] = {"id": "north-aor"}
        self.assertFalse(self.validator.is_valid(document))

    def test_catalogue_codes_are_roles_not_point_types_or_labels(self):
        for field, value in (("source_type", "CP"), ("source_type", "EGRESS_PT"), ("category", "arm"), ("type", "CP"), ("type", "IP")):
            document = self.point_document()
            document[field] = value
            with self.subTest(field=field, value=value):
                self.assertFalse(self.validator.is_valid(document))
        for role in ("control", "initial", "gate", "handover", "marshalling", "identification_safety", "bullseye", "egress"):
            document = self.point_document()
            document["roles"] = [role]
            with self.subTest(role=role):
                self.validator.validate(document)

    def test_navaid_reuses_location_validation_without_requiring_an_invented_station(self):
        records, _ = schemas()
        validator = Draft202012Validator(records["measures/navaid"], registry=self.registry)
        document = {"id": "dme-only", "name": "DME Site", "type": "NAVAID", "class": "DME",
                    "frequency": {"value": 113.5, "unit": "MHz"}, "dme_position": {"latitude": 37.1, "longitude": -115.5}}
        validator.validate(document)
        document.pop("dme_position")
        self.assertFalse(validator.is_valid(document))
        document["position"] = {"latitude": 37.1, "longitude": -115.5}
        document["roles"] = ["gate"]
        self.assertFalse(validator.is_valid(document))
