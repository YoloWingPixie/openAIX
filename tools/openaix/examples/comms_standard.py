"""A small communications standard for the OIR examples: one squadron, one flight, one tanker and one carrier.

The values follow the pattern of the CSG8 standard (standards/csg8/comms-standard.json): STN = block + member, Mode 3 = the
STN without its leading 0, laser code = 1 + block + member, wing TACAN = lead TACAN + 63.
"""


def frequency(value, band="uhf"):
    return {"value": value, "unit": "MHz", "modulation": "AM", "band": band}


def comms_standard_example(version):
    members = [{"member": number, "stn": f"0210{number}", "mode_3": f"210{number}", "laser_code": f"171{number}"} for number in range(1, 5)]
    return {
        "examples/comms-standard.json": {
            "$schema": f"urn:openaix:schema:comms-standard:{version}", "kind": "comms_standard", "schema_version": version,
            "meta": {"id": "oir-comms-standard", "revision": "1", "title": "OIR communications standard"},
            "channels": {
                "uhf_03": {"name": "Intraflight Sol", "frequency": frequency(276.0)},
                "uhf_16": {"name": "CCA TANKER", "frequency": frequency(285.0), "usage": "recovery tanker"},
                "texaco11": {"name": "TEXACO11", "frequency": frequency(285.0)},
            },
            "squadrons": {"vfa_81": {"name": "VFA-81", "aircraft_type": "fa_18c", "flights": ["sol"], "stn_prefix": "02", "mode_1": "02"}},
            "flights": {"sol": {"callsign": "SOL", "squadron": "vfa_81", "aircraft_type": "fa_18c", "datalink_callsign": "SO",
                                "intraflight": "uhf_03", "stn_block": "0210", "laser_block": "71", "members": members,
                                "tacan_aa": {"lead": {"channel": 12, "band": "Y"}, "wing": {"channel": 75, "band": "Y"}}}},
            "support": {"texaco11": {"callsign": "TEXACO11", "role": "recovery_tanker", "aircraft_type": "s3_tanker", "refuel": "basket",
                                     "channels": ["texaco11"], "tacan": {"channel": 85, "band": "Y", "identifier": "TX1"},
                                     "datalink_callsign": "TX", "stn": "07023", "mode_3": "6023"}},
            "ships": {"cvn_75": {"hull": "CVN_75", "name": "USS Harry S. Truman", "tacan": {"channel": 75, "band": "X", "identifier": "KU"},
                                 "icls_channel": 5, "link4": {"value": 336.0, "unit": "MHz"}, "radio": "uhf_16", "recovery_tanker": "texaco11"}},
            "rules": [{"field": "stn", "pattern": "{stn_block}{member}"}, {"field": "laser_code", "pattern": "1{laser_block}{member}"},
                      {"field": "mode_3", "pattern": "{stn_tail}{member}"}],
            "sources": [{"id": "csg8-comm-plan", "title": "CSG8 comm plan"}],
            "radio_plans": {"hornet": {"name": "F/A-18C", "aircraft_types": ["fa_18c"], "radios": [
                {"radio": "uhf_1", "start_preset": 1, "presets": [{"preset": 1, "flight_channel": "intraflight"}, {"channel": "uhf_16", "preset": 2}]}]}},
            "airfields": {"rule": "airfield_record", "link4": False},
            "datalink": {"network": {"fighter_channel": 1, "mission_channel": 1, "special_channel": 1, "transmit_power": 3},
                         "hornet": {"aic": 1, "ff1": 1, "ff2": 1}, "team_rule": "flight_members", "donor_rule": "awacs_and_flight_leads"},
            "iff": {"defaults": {"mode_4": "on", "mode_c": True}},
            "laser": {"jtac": [{"code": "1688"}], "blocks": {"sol": "71"}, "alternates": {"sol": "1611"}},
            "restrictions": {"tacan": [{"channels": [4, 5, 6, 7], "band": "Y", "reason": "kills Link 16"}], "mode_3": ["7500", "7600", "7700"]},
        }
    }
