import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.check.validate import ContractError, export_document, import_document, validate_document


class FacTests(unittest.TestCase):
    def test_point_references_match_initial_or_egress_roles(self):
        for field, accepted, rejected in (("initial_points", ("initial", "fix"), ("control", "egress")),
                                          ("egress_points", ("egress", "gate", "fix"), ("control", "initial"))):
            document = json.loads((ROOT / "examples/fac.json").read_text())
            resources = json.loads((ROOT / "examples/resources.json").read_text())
            point = json.loads((ROOT / "examples/measures/ip.json").read_text())
            resources["resources"]["control_measures"][point["id"]] = point
            document[field] = [{"kind": "control_measure", "id": point["id"]}]
            for role in accepted:
                with self.subTest(field=field, accepted=role):
                    point["roles"] = [role]
                    validate_document(document, resource_document=resources)
            for role in rejected:
                with self.subTest(field=field, rejected=role):
                    point["roles"] = [role]
                    with self.assertRaises(ContractError) as error:
                        validate_document(document, resource_document=resources)
                    self.assertEqual(error.exception.path, f"/{field}/0/id")

    def test_equipment_coordinate_source_and_consumer_behavior_round_trip_together(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        for field in ("resources_ref", "channels", "initial_points", "egress_points"):
            document.pop(field, None)
        document.update({"coordinate_source": "lrf", "default_laser_code": "1688", "smoke_color": "white",
                         "equipment": [{"id": "lrf-1", "kind": "laser_rangefinder", "quantity": 1, "available": True,
                                        "max_range": {"value": 8, "unit": "km"}, "horizontal_accuracy": {"value": 10, "unit": "m"}}],
                         "extensions": {"org.vox-bellica.jtac": {"search_range_m": 10000, "laser_range_m": 8000,
                            "voice_id": "training-controller", "memory_file": "Axeman.json", "readback_timeout_s": 60,
                            "impact_window_s": 120, "precise_coords_delay_s": 10, "last_call_on_loss": False, "town_ips": True,
                            "stack": {"concurrent": False, "radius_m": 3000, "block_ft": 2000, "helo_block_ft": 1000, "separation_ft": 2000,
                                      "helo_floor_ft": 1000, "slow_floor_ft": 12000, "fast_floor_ft": 16000},
                            "launch_warnings": {"enabled": True, "range_m": 8000, "delay_min": "2.5s", "delay_max": "6s", "coalesce": "5s"},
                            "night": {"mode": "auto", "sun_deg": -6, "start_hour": 20, "end_hour": 5, "utc_offset_h": 3, "ir_mark": True, "snake_amplitude_m": 15, "snake_period": "500ms"},
                            "fah": {"laser_cone": True, "laser_cone_deg": 60, "laser_prefer_deg": 45, "observer_buffer_m": 500, "friendly_parallel_reds": 3,
                                    "valley_min_depth_m": 50, "road_max_m": 150, "terrain": True}, "danger_close": {"initials": "JD"}}}})
        self.assertEqual(import_document(export_document(document)), document)
        changed = json.loads(json.dumps(document))
        changed["coordinate_source"] = "gps"
        with self.assertRaises(ContractError):
            validate_document(changed)

    def test_target_location_error_name_and_vox_tuning_are_not_portable_fields(self):
        # DOCTRINE-06: `tle` held a coordinate source, not a CAT I-VI target location error; ORDERS-05: Vox tuning is namespaced.
        document = json.loads((ROOT / "examples/fac.json").read_text())
        resources = json.loads((ROOT / "examples/resources.json").read_text())
        validate_document(document, resource_document=resources)
        for field, value in (("tle", "lrf"), ("search_range_m", 10000), ("laser_range_m", 8000), ("availability", {"start": "2026-10-02T13:00:00Z", "end": "2026-10-02T15:00:00Z"})):
            with self.subTest(field=field):
                changed = json.loads(json.dumps(document))
                changed[field] = value
                with self.assertRaises(ContractError) as error:
                    validate_document(changed, resource_document=resources)
                self.assertEqual(error.exception.code, "schema constraint: additionalProperties")

    def test_equipment_ranges_use_typed_lengths(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        resources = json.loads((ROOT / "examples/resources.json").read_text())
        for value in (8000, {"value": 8000}, {"value": -1, "unit": "m"}):
            with self.subTest(value=value):
                changed = json.loads(json.dumps(document))
                changed["equipment"][0]["max_range"] = value
                with self.assertRaises(ContractError):
                    validate_document(changed, resource_document=resources)
        changed = json.loads(json.dumps(document))
        changed["equipment"][0]["max_range_m"] = 8000
        with self.assertRaises(ContractError):
            validate_document(changed, resource_document=resources)

    def test_supplied_equipment_and_vox_observers_are_validated(self):
        document = json.loads((ROOT / "examples/fac.json").read_text())
        for field in ("resources_ref", "channels", "initial_points", "egress_points"):
            document.pop(field, None)
        document["equipment"] = [{"id": "lrf-1", "kind": "laser_rangefinder", "horizontal_accuracy": {"value": -1, "unit": "m"}}]
        with self.assertRaises(ContractError):
            validate_document(document)
        document.pop("equipment")
        document["extensions"]["org.vox-bellica.jtac"]["observers"] = [{"kind": "unit", "name": "Not-a-name"}]
        with self.assertRaises(ContractError):
            validate_document(document)
        # The observers of the Vox Bellica JTAC are application settings, not DCS data.
        document["extensions"]["org.vox-bellica.jtac"]["observers"] = ["OIR Axeman OP"]
        document["extensions"]["sim"]["dcs"]["observers"] = [{"kind": "unit", "name": "OIR Axeman OP"}]
        with self.assertRaises(ContractError):
            validate_document(document)
