"""GeoJSON geometry (RFC 7946): the `geojson` kind is accepted wherever its openAIX shape is accepted, and only there."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, validate_definitions, validate_document


def example(name):
    return json.loads((ROOT / "examples" / (name + ".json")).read_text())


RING = [[40.1, 35.1], [40.3, 35.1], [40.3, 35.3], [40.1, 35.3], [40.1, 35.1]]
POLYGON = {"kind": "geojson", "geometry": {"type": "Polygon", "coordinates": [deepcopy(RING)]}}
MULTIPOLYGON = {"kind": "geojson", "geometry": {"type": "MultiPolygon", "coordinates": [[deepcopy(RING)]]}}
LINE = {"kind": "geojson", "geometry": {"type": "LineString", "coordinates": [[39.724, 34.835], [40.025, 34.855]]}}
POINT = {"kind": "geojson", "geometry": {"type": "Point", "coordinates": [40.17, 35.21]}}


class GeoJSONTests(unittest.TestCase):
    def test_each_geojson_type_is_a_common_geometry(self):
        for geometry in (POLYGON, MULTIPOLYGON, LINE, POINT):
            with self.subTest(type=geometry["geometry"]["type"]):
                validate_definitions({"Geometry": deepcopy(geometry)})

    def test_other_geojson_types_and_foreign_members_are_rejected(self):
        for change in ({"type": "MultiLineString", "coordinates": [[[40.0, 35.0], [40.1, 35.1]]]},
                       {"type": "GeometryCollection", "geometries": []},
                       {"type": "Point", "coordinates": [40.17, 35.21], "crs": "EPSG:4326"}):
            with self.subTest(change=change["type"]), self.assertRaises(ContractError):
                validate_definitions({"Geometry": {"kind": "geojson", "geometry": change}})

    def test_positions_are_longitude_then_latitude(self):
        with self.assertRaises(ContractError):
            validate_definitions({"Geometry": {"kind": "geojson", "geometry": {"type": "Point", "coordinates": [35.21, 140.17]}}})
        validate_definitions({"Geometry": {"kind": "geojson", "geometry": {"type": "Point", "coordinates": [140.17, 35.21, 120.0]}}})

    def test_linear_ring_closes_around_three_distinct_positions(self):
        for ring in ([[40.1, 35.1], [40.3, 35.1], [40.3, 35.3], [40.1, 35.3]], [[40.1, 35.1], [40.3, 35.1], [40.1, 35.1], [40.1, 35.1]]):
            with self.subTest(ring=ring), self.assertRaises(ContractError) as error:
                validate_definitions({"Geometry": {"kind": "geojson", "geometry": {"type": "Polygon", "coordinates": [ring]}}})
            self.assertIn("linear ring", error.exception.code)

    def test_a_shape_takes_only_its_own_geojson_types(self):
        flot = example("measures/flot")
        validate_document({**flot, "geometry": deepcopy(LINE)})
        for geometry in (POLYGON, POINT):
            with self.subTest(type=geometry["geometry"]["type"]), self.assertRaises(ContractError):
                validate_document({**flot, "geometry": deepcopy(geometry)})
        nfa = example("measures/nfa")
        for geometry in (POLYGON, MULTIPOLYGON):
            with self.subTest(type=geometry["geometry"]["type"]):
                validate_document({**nfa, "geometry": deepcopy(geometry)})
        with self.assertRaises(ContractError):
            validate_document({**nfa, "geometry": deepcopy(LINE)})

    def test_corridor_codes_do_not_take_a_geojson_line(self):
        catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
        entries = {item["code"]: item for item in catalogue["types"]}
        self.assertEqual(entries["MRR"]["geometries"], ["corridor"])
        self.assertIn("geojson:LineString", entries["FLOT"]["geometries"])
        self.assertIn("geojson:MultiPolygon", entries["ROZ"]["geometries"])
        self.assertNotIn("geojson:Point", entries["ROZ"]["geometries"])


if __name__ == "__main__":
    unittest.main()
