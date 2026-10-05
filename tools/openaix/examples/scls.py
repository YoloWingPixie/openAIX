"""OIR stores and standard conventional loads (SCL) for every OIR mission that carries weapons.

Loads, station layouts and fuzes follow the owner's scl-tools: the F-16C loads are rows of the 93rd table on the
VCSG8 wiki (WW01, DTA05, AD05) with the 93rd's assumed pods, the station layouts of its UnitPayloads and its payload
names (`93rd <SCL id> (<SCL code>)[ <tag>]`); fuzes are those of profiles/fuzing.json. DCS station numbers, labels and
class identifiers (CLSID) are from the DCS unit and launcher data (sources/dcs/aircraft-stations.json). The F-15C,
F-15E, A-10C and AH-64D loads are planning loads for the OIR missions on the same DCS data. DCS has no EA-18G, so the
EA-18G load has no stations and no DCS bindings. Tanker, airborne control, lift, rescue and reconnaissance flights
carry no SCL.
"""
from copy import deepcopy

from openaix.sim.dcs import extension as dcs

DCS_TASKS = {"WW": [29], "DTA": [31, 30, 32], "AD": [11, 10, 18, 19]}


# The aircraft type catalogue: a neutral identifier and name, the DCS type name in `extensions.sim.dcs.type`.
# DCS has no EA-18G and no HH-60G as a playable or AI type in the OIR mission.
AIRCRAFT_TYPES = {
    "F-16C": ("f-16c-50", "F-16C Fighting Falcon Block 50", "airplane", "F-16C_50"),
    "F-15C": ("f-15c", "F-15C Eagle", "airplane", "F-15C"),
    "F-15E": ("f-15e", "F-15E Strike Eagle", "airplane", "F-15ESE"),
    "A-10C": ("a-10c", "A-10C II Thunderbolt II", "airplane", "A-10C_2"),
    "EA-18G": ("ea-18g", "EA-18G Growler", "airplane", None),
    "C-130J": ("c-130j", "C-130J Hercules", "airplane", "C-130"),
    "KC-135R": ("kc-135r", "KC-135R Stratotanker", "airplane", "KC-135"),
    "E-3A": ("e-3a", "E-3A Sentry", "airplane", "E-3A"),
    "MQ-9": ("mq-9", "MQ-9 Reaper", "unmanned", "MQ-9 Reaper"),
    "HH-60G": ("hh-60g", "HH-60G Pave Hawk", "helicopter", None),
    "AH-64D": ("ah-64d", "AH-64D Apache Longbow Block II", "helicopter", "AH-64D_BLK_II"),
    "CH-47F": ("ch-47f", "CH-47F Chinook", "helicopter", "CH-47Fbl1"),
}


def aircraft_types():
    """The `aircraft_types` catalogue of the OIR resources."""
    result = {}
    for identifier, name, category, dcs_type in AIRCRAFT_TYPES.values():
        result[identifier] = {"name": name, "category": category, **({"extensions": dcs(type=dcs_type)} if dcs_type else {})}
    return result


def aircraft_type(designation):
    """Catalogue identifier of an aircraft type designation such as `F-16C`."""
    return AIRCRAFT_TYPES[designation][0]


def store(name, kind, family=None, clsids=(), role=None, notes=None):
    result = {"name": name, "kind": kind}
    if family:
        result["family"] = family
    if role:
        result["role"] = role
    if clsids:
        result["extensions"] = dcs(clsids=list(clsids))
    if notes:
        result["notes"] = notes
    return result


def stores():
    return {
        "aim-120c": store("AIM-120C AMRAAM", "weapon", "AIM-120", ["{40EF17B7-F508-45de-8566-6FFECC0C1AB8}"]),
        "aim-9x": store("AIM-9X Sidewinder", "weapon", "AIM-9", ["{5CE2FF2A-645A-4197-B48D-8720AC69394F}"]),
        "aim-9m": store("AIM-9M Sidewinder", "weapon", "AIM-9", ["{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}"]),
        "gbu-38": store("GBU-38 JDAM 500 lb", "weapon", "GBU-38", ["{GBU-38}"]),
        "gbu-12": store("GBU-12 Paveway II", "weapon", "GBU-12", ["{DB769D48-67D7-42ED-A2BE-108D566C8B1E}"]),
        "gbu-31v3": store("GBU-31(V)3/B JDAM 2000 lb penetrator", "weapon", "GBU-31", ["{GBU-31V3B}"]),
        "agm-65d": store("AGM-65D Maverick", "weapon", "AGM-65", notes="DCS loads it on a LAU-117 or LAU-88 launcher."),
        "agm-88c": store("AGM-88C HARM", "weapon", "AGM-88", ["{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}"]),
        "agm-114k": store("AGM-114K Hellfire II", "weapon", "AGM-114", notes="DCS loads it on the M299 launcher."),
        "lau-131-m151": store("LAU-131 rocket pod, 7 Hydra 70 M151 HE", "weapon", "LAU-131", ["{69926055-0DA8-4530-9F2F-C86B157EA9F6}"]),
        "lau-131-m156": store("LAU-131 rocket pod, 7 Hydra 70 M156 white phosphorus", "weapon", "LAU-131",
                              ["{2AF2EC3F-9065-4de5-93E1-1739C9A71EF7}"], notes="Marking rockets for FAC(A) target marks."),
        "m261-m151": store("M261 rocket launcher, 19 Hydra 70 M151 HE", "weapon", "M261", ["M261_MK151"]),
        "tank-370": store("370 US gal external fuel tank", "tank", clsids=["{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}"]),
        "tank-610": store("610 US gal external fuel tank", "tank", clsids=["{E1F29B21-F291-4589-9FD8-3272EEC69506}", "{F15E_EXTTANK}"],
                          notes="DCS has one class identifier for the F-15C tank and one for the F-15E tank."),
        "tank-480": store("480 US gal external fuel tank", "tank"),
        "sniper": store("AN/AAQ-33 Sniper targeting pod", "pod", clsids=["{AN_AAQ_33}"], role="targeting"),
        "litening": store("AN/AAQ-28 LITENING targeting pod", "pod", clsids=["{A111396E-D3E8-4b9c-8AC9-2432489304D5}"], role="targeting"),
        "lantirn-tgt": store("AN/AAQ-14 LANTIRN targeting pod", "pod", clsids=["{F-15E_AAQ-14_LANTIRN}"], role="targeting"),
        "lantirn-nav": store("AN/AAQ-13 LANTIRN navigation pod", "pod", clsids=["{F-15E_AAQ-13_LANTIRN}"], role="navigation"),
        "hts": store("AN/ASQ-213 HARM targeting system", "pod", clsids=["{AN_ASQ_213}"], role="emitter_targeting"),
        "alq-184": store("AN/ALQ-184 ECM pod", "pod", "ALQ-184", ["ALQ_184"], role="self_protection_jamming"),
        "alq-184-long": store("AN/ALQ-184 ECM pod, long", "pod", "ALQ-184", ["ALQ_184_Long"], role="self_protection_jamming"),
        "alq-99": store("AN/ALQ-99 tactical jamming pod", "pod", clsids=(), role="tactical_jamming"),
        "apg-78": store("AN/APG-78 Longbow fire control radar", "other", clsids=["{AN_APG_78}"],
                        notes="Mast-mounted radar; DCS loads it on the MMA station."),
        "ter-9a": store("TER-9A triple ejector rack", "rack"),
        "bru-42": store("BRU-42 triple ejector rack", "rack"),
        "lau-105": store("LAU-105 dual missile launcher", "rack", clsids=["LAU-105"]),
        "m299": store("M299 Hellfire launcher", "rack", clsids=["{M299_EMPTY}"]),
    }


# ---- Fuzes (scl-tools profiles/fuzing.json) -------------------------------------------------------------------
PAVEWAY = {"function": "instantaneous", "tail_fuze": "FMU-139", "arming_delay_s": 4, "delay_ms": 0}
PENETRATOR = {"function": "delay", "tail_fuze": "FMU-143", "delay_ms": 60}
AIRBURST = {"function": "proximity", "nose_fuze": "DSU-33", "tail_fuze": "FMU-139", "arming_delay_s": 4,
            "height_of_burst": {"value": 20, "unit": "ft"}}
# The Mission Editor settings of a Paveway II pylon with the FMU-139 tail fuze, USAF appearance (fuzing.json).
PAVEWAY_SETTINGS = {"01_prfx_arm_delay_ctrl_FMU139CB_LD": 4, "01_prfx_function_delay_ctrl_FMU139CB_LD": 0,
                    "NFP_VIS_DrawArgNo_55": 0.1, "NFP_VIS_DrawArgNo_57": 0, "NFP_fuze_type_tail": "FMU139CB_LD",
                    "NFP_PRESID": "Paveway_II", "NFP_PRESVER": 2, "laser_code": 1688}


def item(store_id, quantity=1, **fields):
    return {"store": store_id, "quantity": quantity, **fields}


def station(label, number, clsid, *items, rack=None, settings=None):
    data = {"pylon": number, "label": label, "clsid": clsid}
    if settings:
        data["settings"] = deepcopy(settings)
    result = {"station": label, "items": list(items), "extensions": dcs(**data)}
    if rack:
        result["rack"] = rack
    return result


def bill(stations, fields=None):
    """The bill of stores of a station layout, in the order of first use; `fields` adds fuzes and codes by store."""
    totals = {}
    for entry in stations:
        for load in entry["items"]:
            totals[load["store"]] = totals.get(load["store"], 0) + load["quantity"]
    return [{"store": key, "quantity": value, **deepcopy((fields or {}).get(key, {}))} for key, value in totals.items()]


def scl(identifier, name, number, plane, missions, stations=None, fields=None, items=None, **extra):
    result = {"id": identifier, "kind": "scl", "name": name, "scl_number": number, "aircraft_type": plane,
              "missions": [{"tasking": tasking, **({"role": role} if role else {})} for tasking, role in missions],
              "era": "modern", "stores": items if items is not None else bill(stations, fields)}
    if stations:
        result["stations"] = stations
    result.update(extra)
    return result


def payload(name, unit_type, mission):
    return dcs(payload={"name": name, "unit_type": unit_type, "task_ids": list(DCS_TASKS[mission])})


# ---- F-16C Block 50: rows of the 93rd table, modern era, with the pods that the 93rd assumes -------------------
F16 = "F-16C"
AIM120, AIM9X = "{40EF17B7-F508-45de-8566-6FFECC0C1AB8}", "{5CE2FF2A-645A-4197-B48D-8720AC69394F}"
HARM, TANK370 = "{B06DD79A-F21E-4EB9-BD9D-AB3844618C93}", "{F376DBEE-4CAE-41BA-ADD9-B2910AC95DEC}"


def f16_pods(tgp=True, hts=True, jammer=True):
    """The modern pods of the 93rd: ALQ-184 on the centreline, HTS on 5L, Sniper on 5R."""
    pods = []
    if jammer:
        pods.append(station("5", 5, "ALQ_184_Long", item("alq-184-long")))
    if hts:
        pods.append(station("5L", 10, "{AN_ASQ_213}", item("hts")))
    if tgp:
        pods.append(station("5R", 11, "{AN_AAQ_33}", item("sniper")))
    return pods


def f16_counterair():
    stations = [station("1", 1, AIM120, item("aim-120c")), station("2", 2, AIM120, item("aim-120c")),
                station("3", 3, AIM120, item("aim-120c")), station("4", 4, TANK370, item("tank-370")),
                station("6", 6, TANK370, item("tank-370")), station("7", 7, AIM9X, item("aim-9x")),
                station("8", 8, AIM120, item("aim-120c")), station("9", 9, AIM120, item("aim-120c")), *f16_pods()]
    return scl("f16-cap", "AD05 AMRAAM", "AD05", aircraft_type(F16),
               [("counterair", None), ("cap", None), ("escort", None), ("training", None)], stations,
               code="5A.1X.2", gun_rounds=510, countermeasures={"chaff": 60, "flares": 60},
               remarks="93rd doctrine CAP standard. Two wing tanks; the jammer has the centreline.",
               extensions=payload("93rd AD05 (5A.1X.2)", "F-16C_50", "AD"))


def f16_sead(pre_2015=False):
    stations = [station("1", 1, AIM120, item("aim-120c")), station("2", 2, AIM120, item("aim-120c")),
                station("3", 3, HARM, item("agm-88c")), station("4", 4, TANK370, item("tank-370")),
                station("6", 6, TANK370, item("tank-370")), station("7", 7, HARM, item("agm-88c")),
                station("8", 8, AIM120, item("aim-120c")), station("9", 9, AIM120, item("aim-120c")),
                *f16_pods(tgp=not pre_2015)]
    name = "93rd WW01 (2A88.4A.WW.2)" + (" Pre-2015" if pre_2015 else "")
    result = scl("f16-sead-pre2015" if pre_2015 else "f16-sead", "WW01 HARM" + (" Pre-2015" if pre_2015 else ""), "WW01",
                 aircraft_type(F16), [("preplanned_attack", "sead"), ("preplanned_attack", "dead")], stations,
                 {"agm-88c": {"program": "POS"}}, code="2A88.4A.WW.2", gun_rounds=510, countermeasures={"chaff": 60, "flares": 60},
                 remarks="93rd SEAD standard. HARMs on stations 3 and 7, AMRAAMs on the wingtips and outboard stations.",
                 extensions=payload(name, "F-16C_50", "WW"))
    if pre_2015:
        result["variant_tags"] = ["Pre-2015"]
        result["remarks"] = "Before 2015 the Viper carries the HTS or a targeting pod, not both; a SEAD load keeps the HTS."
    return result


def f16_interdiction():
    """The maximal SCL: DTA05 with every field."""
    gbu = "{TER_9A_2L*GBU-12}", "{TER_9A_2R*GBU-12}"
    stations = [station("1", 1, AIM120, item("aim-120c")), station("2", 2, AIM9X, item("aim-9x")),
                station("3", 3, gbu[0], item("gbu-12", 2), rack="ter-9a", settings=PAVEWAY_SETTINGS),
                station("4", 4, TANK370, item("tank-370")), station("6", 6, TANK370, item("tank-370")),
                station("7", 7, gbu[1], item("gbu-12", 2), rack="ter-9a", settings=PAVEWAY_SETTINGS),
                station("8", 8, AIM120, item("aim-120c")), station("9", 9, AIM120, item("aim-120c")), *f16_pods()]
    return scl("f16-ai", "DTA05 GBU-12", "DTA05", aircraft_type(F16),
               [("preplanned_attack", "air_interdiction"), ("preplanned_attack", "strike"),
                ("preplanned_attack", "maritime_attack"), ("on_call_cas", None)], stations,
               {"gbu-12": {"fuze": deepcopy(PAVEWAY)}},
               code="4G12.3A.1X.2", gun_rounds=510, countermeasures={"chaff": 60, "flares": 60, "program": "MAN 1"},
               laser_code="1688", remarks="93rd XAI, CAS and TASMO load. The code leaves out the jammer, the HTS and the targeting pod: the 93rd assumes them in the modern era.",
               source={"id": "vcsg8-scl-data", "title": "VCSG8 SCL data page, F-16C Viper table", "section": "DTA05"},
               extensions={**payload("93rd DTA05 (4G12.3A.1X.2)", "F-16C_50", "DTA"),
                           "org.vcsg8.scl-tools": {"mission": "DTA", "payload_prefix": "93rd"}})


# ---- F-15C, F-15E, A-10C II and AH-64D: OIR planning loads on the DCS station data ----------------------------
def f15c_counterair():
    stations = [station("1", 1, "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", item("aim-9m")),
                station("3", 3, AIM120, item("aim-120c")),
                *[station(str(number), number, AIM120, item("aim-120c")) for number in (4, 5, 7, 8)],
                station("6", 6, "{E1F29B21-F291-4589-9FD8-3272EEC69506}", item("tank-610")),
                station("9", 9, AIM120, item("aim-120c")), station("11", 11, "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", item("aim-9m"))]
    return scl("f15c-aa", "Eagle air-to-air", "F15C-AA1", aircraft_type("F-15C"), [("counterair", None), ("cap", None)],
               stations, gun_rounds=940, countermeasures={"chaff": 120, "flares": 60},
               remarks="Sweep load with one centreline tank.")


F15E = "F-15E"
F15E_AIR = [station("2A", 1, AIM120, item("aim-120c")), station("2B", 3, "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", item("aim-9m")),
            station("8A", 13, "{6CEB49FC-DED8-4DED-B053-E1F033FF72D3}", item("aim-9m")), station("8B", 15, AIM120, item("aim-120c")),
            station("TGP", 7, "{F-15E_AAQ-14_LANTIRN}", item("lantirn-tgt")), station("NVP", 9, "{F-15E_AAQ-13_LANTIRN}", item("lantirn-nav"))]


def f15e_strike():
    stations = [station("2", 2, "{GBU-31V3B}", item("gbu-31v3")), station("8", 14, "{GBU-31V3B}", item("gbu-31v3")),
                station("L-CFT", 4, "{CFT_L_GBU_12_x_2}", item("gbu-12", 2)), station("R-CFT", 12, "{CFT_R_GBU_12_x_2}", item("gbu-12", 2)),
                station("5", 8, "{F15E_EXTTANK}", item("tank-610")), *deepcopy(F15E_AIR)]
    return scl("f15e-strike", "Strike Eagle penetrator and Paveway", "F15E-ST1", aircraft_type(F15E),
               [("preplanned_attack", "strike"), ("preplanned_attack", "air_interdiction")], stations,
               {"gbu-31v3": {"fuze": deepcopy(PENETRATOR)}, "gbu-12": {"fuze": deepcopy(PAVEWAY)}},
               gun_rounds=500, countermeasures={"chaff": 120, "flares": 60}, laser_code="1688",
               remarks="Penetrators for hardened aimpoints, Paveways for soft aimpoints; one centreline tank.")


def f15e_scar():
    stations = [station("2", 2, "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}", item("gbu-12")),
                station("8", 14, "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}", item("gbu-12")),
                station("L-CFT", 4, "{CFT_L_GBU_38_x_3}", item("gbu-38", 3)), station("R-CFT", 12, "{CFT_R_GBU_38_x_3}", item("gbu-38", 3)),
                station("5", 8, "{F15E_EXTTANK}", item("tank-610")), *deepcopy(F15E_AIR)]
    return scl("f15e-scar", "Strike Eagle SCAR", "F15E-SC1", aircraft_type(F15E),
               [("counterland_control", "scar"), ("preplanned_attack", "air_interdiction")], stations,
               {"gbu-38": {"fuze": deepcopy(AIRBURST)}, "gbu-12": {"fuze": deepcopy(PAVEWAY)}},
               gun_rounds=500, countermeasures={"chaff": 120, "flares": 60}, laser_code="1688",
               remarks="JDAM with airburst fuzes for vehicles in the open and Paveways for moving targets.")


A10 = "A-10C"
MAVERICK = "{444BA8AE-82A7-4345-842E-76154EFCCA46}"
PAVEWAY_CLSID = "{DB769D48-67D7-42ED-A2BE-108D566C8B1E}"


def a10_close_air_support():
    stations = [station("1", 1, "ALQ_184", item("alq-184")), station("2", 2, "{69926055-0DA8-4530-9F2F-C86B157EA9F6}", item("lau-131-m151")),
                station("3", 3, MAVERICK, item("agm-65d")), station("4", 4, PAVEWAY_CLSID, item("gbu-12")),
                station("8", 8, PAVEWAY_CLSID, item("gbu-12")), station("9", 9, MAVERICK, item("agm-65d")),
                station("10", 10, "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", item("litening")),
                station("11", 11, "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", item("aim-9m", 2), rack="lau-105")]
    return scl("a10-cas", "Hog CAS", "A10-CAS1", aircraft_type(A10), [("on_call_cas", None), ("preplanned_attack", "scheduled_cas")], stations,
               {"gbu-12": {"fuze": deepcopy(PAVEWAY), "laser_code": "1511"}},
               gun_rounds=1150, countermeasures={"chaff": 240, "flares": 120}, laser_code="1688",
               remarks="Paveways on code 1511 for Axeman's second designator; Mavericks and HE rockets for vehicles.")


def a10_forward_air_control():
    stations = [station("1", 1, "ALQ_184", item("alq-184")), station("2", 2, "{69926055-0DA8-4530-9F2F-C86B157EA9F6}", item("lau-131-m151")),
                station("3", 3, "{BRU42LS_2*LAU131_HYDRA_70_M156_L}", item("lau-131-m156", 2), rack="bru-42"),
                station("4", 4, PAVEWAY_CLSID, item("gbu-12")), station("8", 8, PAVEWAY_CLSID, item("gbu-12")),
                station("9", 9, MAVERICK, item("agm-65d")), station("10", 10, "{A111396E-D3E8-4b9c-8AC9-2432489304D5}", item("litening")),
                station("11", 11, "{DB434044-F5D0-4F1F-9BA9-B73027E18DD3}", item("aim-9m", 2), rack="lau-105")]
    return scl("a10-faca", "Hog FAC(A) marking", "A10-FAC1", aircraft_type(A10), [("counterland_control", "fac_a"), ("on_call_cas", None)],
               stations, {"gbu-12": {"fuze": deepcopy(PAVEWAY)}},
               gun_rounds=1150, countermeasures={"chaff": 240, "flares": 120}, laser_code="1688",
               remarks="Two pods of white phosphorus rockets for target marks; self-attack with Paveways and a Maverick.")


def ah64_hellfire():
    stations = [station("1", 1, "M261_MK151", item("m261-m151")),
                station("2", 2, "{88D18A5E-99C8-4B04-B40B-1C02F2018B6E}", item("agm-114k", 4), rack="m299"),
                station("3", 3, "{88D18A5E-99C8-4B04-B40B-1C02F2018B6E}", item("agm-114k", 4), rack="m299"),
                station("4", 4, "M261_MK151", item("m261-m151")), station("MMA", 6, "{AN_APG_78}", item("apg-78"))]
    return scl("ah64-hellfire", "Apache Hellfire and rockets", "AH64-1", aircraft_type("AH-64D"),
               [("custom", None), ("on_call_cas", None)], stations, gun_rounds=1200, countermeasures={"chaff": 30, "flares": 60},
               laser_code="1688", remarks="Eight Hellfires on the inboard pylons and two rocket launchers outboard; Longbow radar on the mast.")


def ea18g_jamming():
    return scl("ea18g-ea", "Growler stand-off jamming", "EA18G-EA1", aircraft_type("EA-18G"), [("electromagnetic", None)],
               items=[item("alq-99", 3), item("aim-120c", 2), item("tank-480", 2)],
               remarks="Three jamming pods. DCS has no EA-18G, so the load has no stations or simulator bindings.")


def scls():
    loads = [f16_counterair(), f16_sead(), f16_sead(pre_2015=True), f16_interdiction(), f15c_counterair(), f15e_strike(),
             f15e_scar(), a10_close_air_support(), a10_forward_air_control(), ah64_hellfire(), ea18g_jamming()]
    return {load["id"]: load for load in loads}


def scl_example(version, resources_ref):
    """examples/scl.json: the DTA05 load as a standalone record that links the OIR resource catalogue."""
    return {"$schema": f"urn:openaix:schema:scl:{version}", **f16_interdiction(), "resources_ref": deepcopy(resources_ref)}
