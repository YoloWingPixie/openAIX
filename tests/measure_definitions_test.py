from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from openaix.describe import templates as d
from openaix.describe.tables.common import MEASURE_SOURCE, measure_text

# Defining terms of each code, taken from its `source_text` and `paraphrase`. The `definition`, after
# acronym expansion, keeps each term (case-insensitive; "|" separates accepted alternatives).
DEFINING_TERMS = {
    "AARA": ["defined dimensions", "air-to-air refuelling", "controlling authority", "coordinate"],
    "ACA": ["block or corridor", "reasonably safe", "surface fires", "airspace control authority", "informal",
            "battalion or higher"],
    "ACAR": ["lateral", "boundaries of the area of operations", "basic geographic element", "sub-areas"],
    "ACCA": ["defined dimensions", "battlefield command and control"],
    "ACP": ["navigation", "command and control", "communication", "without coordination|no coordination"],
    "ADIZ": ["defined dimensions", "identification", "location", "control of aircraft"],
    "ADVRTE": ["designated route", "advisory service"],
    "AEWA": ["defined dimensions", "early warning"],
    "AIRRTE": ["navigable airspace", "two points", "flight rules", "bi-directional", "minimum-risk", "support traffic"],
    "ALTRV": ["block of altitude", "transit or loiter", "moving or stationary", "upper and a lower limit",
              "lateral limits"],
    "AOA": ["geographical area", "initiating directive", "command and control", "objectives", "amphibious task force"],
    "AOR": ["geographic area", "authority to plan and conduct operations", "regional commander",
            "joint operations area", "smaller", "larger"],
    "APPCOR": ["safe passage", "land-based aircraft", "maritime force", "entry and exit gate",
               "identification safety range"],
    "ARWY": ["control area", "corridor", "radio navigation"],
    "ATSRTE": ["route", "channels the flow of traffic", "air traffic services"],
    "BDZ": ["around a base", "effectiveness", "air defence", "transit routes should avoid"],
    "BULLSEYE": ["reference point", "magnetic", "nautical miles", "nearest degree", "within 5 nautical miles",
                 "code name"],
    "BZ": ["buffer", "between coordination measures", "without coordination"],
    "CADA": ["block of airspace", "land-based air commander", "naval commander", "close to each other",
             "air defence responsibilit"],
    "CBA": ["temporary segregated area", "international boundar", "operational need", "designated users"],
    "CCZONE": ["aircraft carrier", "fixed-wing or rotary-wing", "carrier flight operations"],
    "CDR": ["non-permanent", "route", "only under stated conditions"],
    "CFL": ["land headquarters", "beyond", "conventional indirect surface fire", "at any time",
            "without further coordination", "boundaries of the establishing headquarters"],
    "CL": ["altitude or height", "airspace control responsibilit", "deconflict", "above", "below"],
    "CLSA": ["only instrument flight rules", "air traffic control", "separates all flights from each other"],
    "CLSB": ["instrument flight rules", "visual flight rules", "air traffic control",
             "separates all flights from each other"],
    "CLSC": ["instrument flight rules", "visual flight rules", "air traffic control",
             "from other ifr flights and from vfr flights", "traffic information about other vfr"],
    "CLSD": ["instrument flight rules", "visual flight rules", "air traffic control", "only from other ifr flights",
             "traffic information"],
    "CLSE": ["instrument flight rules", "visual flight rules", "AJP-3.3.5", "separates them from other ifr flights",
             "traffic information", "as far as practical"],
    "CLSF": ["instrument flight rules", "visual flight rules", "participating", "advisory service",
             "flight information service", "ask for it"],
    "CLSG": ["instrument flight rules", "visual flight rules", "only flight information service", "ask for it"],
    "COZ": ["beyond the missile engagement zone|beyond the MEZ", "fighters", "pursue|pursuit", "interception",
            "countdown"],
    "CP": ["mission leader", "radio contact", "airspace control agency"],
    "CTA": ["controlled airspace", "upwards", "above the surface", "not at the surface"],
    "CTZ": ["controlled airspace", "from the surface", "upper limit"],
    "DA": ["defined dimensions", "dangerous", "flight of aircraft", "stated times"],
    "DZ": ["airdrop", "troops", "equipment or supplies", "deconflict"],
    "EA": ["ground manoeuvre", "contain and destroy", "enemy force", "massed effects", "all available weapons",
           "subordinate units"],
    "EC": ["electromagnetic combat", "electronic warfare"],
    "EG": ["point", "inbound or outbound", "airfield", "force at sea"],
    "FACA": ["maritime", "around a force", "airspace control and air defence measures", "mutual interference",
             "weapon systems"],
    "FEBA": ["foremost limits", "ground combat units", "covering or screening", "fire support", "manoeuvre"],
    "FEZ": ["defined dimensions", "engagement of air threats", "normally", "fighter"],
    "FFA": ["any weapon system", "without further coordination", "establishing headquarters", "joint fires",
            "jettison", "division or higher"],
    "FIR": ["defined dimensions", "flight information service", "alerting service"],
    "FLOT": ["most forward positions", "friendly forces", "any kind of military operation", "at a given time"],
    "FSCL": ["land or amphibious force commander", "area of operations", "fires by other force elements",
             "current and planned operations", "coordinate"],
    "HG": ["control of the aircraft", "one controller to another", "radar hand-over"],
    "HIDACZ": ["defined dimensions", "airspace control authority", "concentrated", "weapons and airspace users",
               "controlling authority"],
    "IFFOFF": ["phase line", "airspace control order", "friendly aircraft", "stop",
               "identification, friend or foe", "target"],
    "IFFON": ["phase line", "airspace control order", "friendly aircraft", "start",
              "identification, friend or foe", "after the mission"],
    "IP": ["starts its attack run", "target", "airborne", "movement", "fixed-wing", "5 to 15 nautical miles",
           "more than 20 nautical miles"],
    "ISP": ["join", "maritime force", "two-way communications", "identification procedures"],
    "ISR": ["minimum range", "close", "maritime force", "positive identification|positively identified",
            "mistake the aircraft for hostile", "officer in tactical command"],
    "JEZ": ["defined dimensions", "at the same time", "surface-to-air missile", "OPTASK AAW", "identification",
            "positive control"],
    "KB": ["three-dimensional", "permissive", "fire support coordination measure", "rapid|quickly",
           "law of armed conflict", "rules of engagement"],
    "LLTR": ["temporary", "low-level corridor", "defined dimensions", "forward area", "friendly air defences",
             "surface forces"],
    "LZ": ["zone", "landing"],
    "MEZ": ["defined dimensions", "normally reserved", "surface-to-air missile", "air defence measure",
            "range and bearing", "coordinate before"],
    "MG": ["air traffic control", "outbound transit", "take-off", "before landing"],
    "MISARC": ["maritime", "10 degrees", "officer in tactical command", "bearing of the target", "maximum range",
               "surface-to-air missile"],
    "MRR": ["temporary air corridor", "ground commander", "minimum known hazards", "low-flying aircraft",
            "forward line of own troops", "close air support"],
    "NAVRTE": ["route", "area navigation"],
    "NFA": ["restrictive", "prohibits joint fires", "establishing headquarters", "one mission at a time",
            "self-defence", "any size"],
    "NFZ": ["defined dimensions", "no aircraft", "enforcing authority", "authorizes"],
    "PROHIB": ["defined dimensions", "land areas or territorial waters", "state", "prohibits flight"],
    "PZ": ["aerial retrieval", "pick up", "personnel or materiel"],
    "RA": ["defined dimensions", "land areas or territorial waters", "state", "restrict", "conditions"],
    "RCA": ["defined dimensions", "general air traffic", "off-route", "operational air traffic", "coordination"],
    "RECCE": ["reconnaissance"],
    "RFA": ["restrictions", "joint fires", "without coordination", "establishing headquarters",
            "manoeuvre battalion or higher", "on-call"],
    "ROZ": ["defined dimensions", "airspace control authority", "situation", "restricts",
            "one or more airspace users"],
    "SAAFR": ["below the coordination level", "land component aviation", "forward area",
              "direct support of ground operations"],
    "SAFES": ["routes friendly aircraft", "maritime force", "minimum risk", "safe from friendly fighters or weapons",
              "approach or return"],
    "SAMEZ": ["defined dimensions", "normally reserved", "surface-to-air missile", "coordinate before"],
    "SC": ["air corridor", "special routing", "missions"],
    "SCZ": ["activated", "ship", "operates aircraft", "friendly aircraft", "without permission", "interference"],
    "SL": ["bi-directional", "airbase", "landing site", "base defence zone", "routes or corridors", "activated"],
    "SSMS": ["Army Tactical Missile System", "surface-launched cruise missile", "launch", "impact points",
             "flight path"],
    "TC": ["bi-directional", "rear area", "air defences", "minimum risk", "not normally"],
    "TCA": ["control area", "confluence of air traffic services", "major aerodromes"],
    "TL": ["above low-level air defence", "height and an altitude", "cross the area", "friendly"],
    "TMRR": ["temporary", "minimum-risk", "transit routes", "rear boundary of the forward area", "operations area",
             "direct support of ground operations"],
    "TR": ["temporary air corridor", "defined dimensions", "forward area", "friendly air defences", "bi-directional",
           "weapons free zones"],
    "TRA": ["defined volume", "one airspace authority", "temporarily", "common agreement", "another airspace authority",
            "clearance"],
    "TRNG": ["geographical area", "temporarily or permanently", "training", "exercises and testing", "airspace"],
    "TSA": ["defined dimensions", "exclusive use", "users", "period", "no other traffic"],
    "UAA": ["defined dimensions", "unmanned aircraft"],
    "WFZ": ["air defence zone", "assets or facilities", "other than airbases", "any target",
            "positive identification", "friendly"],
    # Fire support coordination and naval surface fire support measures (JP 3-09, 2019; JP 3-02, 2019).
    "RFL": ["converging friendly forces", "one or both may move", "prohibits joint fires", "effects of joint fires",
            "across the line", "without coordination with the affected force", "friendly fire",
            "duplication of engagements", "commander common to the converging forces"],
    "BCL": ["Marine Corps", "fire support coordination measure", "surface targets of opportunity",
            "fire support coordination line", "Marine air-ground task force", "approval of the ground combat element",
            "commander establishes", "airspace coordination area"],
    "FSA": ["sea manoeuvre area", "naval force commander", "fire support ships", "gunfire support",
            "amphibious operation", "officer in tactical command"],
    "FSS": ["exact location at sea", "fire support area", "fire support ship delivers fire"],
    # Ground manoeuvre graphics (ADP 3-90, 2019; FM 3-90, 2023).
    "PL": ["identifiable feature", "operational area", "control and coordination", "military operations",
           "not a boundary"],
    "BOUNDARY": ["line", "delineates surface areas", "coordination and deconfliction", "units, formations or areas",
                 "next to each other"],
    "OBJ": ["location", "orientation of operations", "phases of operations", "changes of direction", "unity of effort",
            "terrain objective", "force objective"],
    "BP": ["defence location", "likely enemy avenue of approach", "not an area of operations"],
    "AA": ["area", "unit", "preparation for an operation"],
    "TRP": ["point of reference", "before the operation", "fixed structure or a terrain feature", "target location",
            "offset"],
    "NAI": ["geospatial area", "systems node or link", "information requirement", "enemy and adversary courses of action"],
    "TAI": ["geographical area", "friendly forces", "engage", "high-value targets"],
    "LOA": ["phase line", "forward progress of the attack", "does not advance", "security forces"],
    "LD": ["land warfare", "coordinates the departure of attack elements"],
    "LC": ["general trace", "friendly and enemy forces engage", "defence", "forward line of own troops",
           "line of departure"],
    # United States airspace coordinating measures (JP 3-52, 2014).
    "AIRCOR": ["restricted air route", "friendly aircraft", "prevent friendly forces from firing", "coordinating altitude"],
    "CA": ["airspace coordinating measure", "altitude to separate users", "transition",
           "different airspace control elements", "fly or fire through"],
}

# Defining terms of each civil airspace type (sources/measure-definitions.json `airspace_types`).
AIRSPACE_TERMS = {
    "ATCAA": ["defined vertical and lateral limits", "air traffic control (ATC) assigns", "separates",
              "stated activities", "other instrument flight rules (IFR) air traffic"],
    "CFA": ["contains activities", "danger to non-participating aircraft", "controlled environment", "stop at once",
            "spotter aircraft, radar or ground observers"],
    "NSA": ["defined vertical and lateral dimensions", "ground facilities", "security and safety", "avoid flight",
            "temporarily close"],
    "TFR": ["regulatory action", "Federal Aviation Administration", "notice to air missions", "temporarily restricts",
            "defined area", "persons or property in the air or on the ground"],
    "SFRA": ["defined dimensions", "land areas or territorial waters", "14 CFR part 93", "authorizes otherwise"],
    "TRSA": ["designated airport", "radar vectoring, sequencing and separation", "full time",
             "participating visual flight rules", "not mandatory", "not an airspace class"],
    "ModeCVeil": ["30 nautical miles", "Appendix D, section 1 of 14 CFR part 91", "from the surface to 10,000 feet",
                  "transponder with automatic altitude reporting", "ADS-B Out"],
    "RMZ": ["defined dimensions", "carriage and operation of radio equipment", "mandatory"],
    "TMZ": ["defined dimensions", "carriage and operation", "pressure-altitude reporting transponder", "mandatory"],
    "ClassA": ["only for instrument flight rules", "(ATC) service", "ATC clearance is necessary", "separates all flights from each other"],
    "ClassB": ["instrument flight rules", "visual flight rules", "(ATC) service", "ATC clearance is necessary",
               "separates all flights from each other", "In the United States", "radar"],
    "ClassC": ["(ATC) service", "ATC clearance is necessary", "separates IFR flights from all other flights",
               "VFR flights from IFR flights", "traffic information about other VFR flights", "radio contact"],
    "ClassD": ["(ATC) service", "ATC clearance is necessary", "separates IFR flights only from other IFR flights",
               "IFR flights get traffic information about VFR flights", "traffic information about all other flights",
               "radio contact"],
    "ClassE": ["Only IFR flights get", "necessary only for IFR flights", "separates IFR flights only from other IFR flights",
               "traffic information as far as practical", "control zone"],
    "ClassF": ["No flight gets", "participating IFR flights", "advisory service", "flight information service",
               "ask for it", "United States does not use class F"],
    "ClassG": ["No flight gets", "clearance is not necessary", "flight information service", "ask for it"],
    "UIR": ["above a different FIR", "ceiling of the lower FIR", "(VFR) cruising level"],
    "ATZ": ["defined dimensions", "around an aerodrome", "protection of aerodrome traffic"],
    "MOA": ["not in class A airspace", "training of armed forces", "not dangerous", "(IFR) aircraft",
            "shows visual flight rules (VFR) aircraft", "only when ATC can separate"],
    "Alert": ["pilot training", "unusual type of flight", "not dangerous", "non-participating aircraft",
              "Code of Federal Regulations", "collision avoidance"],
    "Warning": ["known dimensions", "3 nautical miles", "coast of the United States", "dangerous to non-participating aircraft",
                "tell the pilots", "international waters"],
    "Sector": ["horizontal and vertical dimensions", "group of controllers", "controls the air traffic"],
}

# Codes without published first-party wording, with the reason.
WITHOUT_SOURCE_TEXT = {}

KIND_TERMS = {
    "blue": ["air-to-surface", "from the surface to a ceiling", "no further coordination",
             "area of operations", "airspace control element", "kill box coordinator", "aircrew on station"],
    "purple": ["air-to-surface", "surface-to-surface", "subsurface-to-surface", "floor", "do not fly below the floor",
               "below the floor need no further coordination"],
}


def present(term, text):
    return any(option.lower() in text.lower() for option in term.split("|"))


class MeasureDefinitionTests(unittest.TestCase):
    codes = MEASURE_SOURCE["codes"]

    def test_every_code_lists_its_defining_terms(self):
        self.assertEqual(set(DEFINING_TERMS), set(self.codes))

    def test_definitions_keep_their_defining_terms(self):
        for code, terms in DEFINING_TERMS.items():
            text = str(measure_text(code))
            for term in terms:
                with self.subTest(code=code, term=term):
                    self.assertTrue(present(term, text), f"{code} lost '{term}': {text}")

    def test_every_code_keeps_source_text_and_paraphrase(self):
        for code, row in self.codes.items():
            with self.subTest(code=code):
                self.assertTrue(row.get("paraphrase", "").strip())
                self.assertTrue(row.get("definition", "").strip())
                self.assertNotIn("quote", row)
                if code in WITHOUT_SOURCE_TEXT:
                    self.assertNotIn("source_text", row)
                else:
                    self.assertTrue(row.get("source_text", "").strip())

    def test_definition_does_not_start_with_the_name(self):
        for code, row in self.codes.items():
            with self.subTest(code=code):
                self.assertFalse(row["definition"].lower().startswith(row["name"].lower()))

    def test_kill_box_kinds_keep_their_conditions(self):
        kinds = self.codes["KB"]["kinds"]
        self.assertEqual(set(kinds["source_text"]), set(KIND_TERMS))
        self.assertEqual(set(kinds["values"]), set(KIND_TERMS))
        for kind, terms in KIND_TERMS.items():
            text = str(d.value(kinds["values"][kind]))
            for term in terms:
                with self.subTest(kind=kind, term=term):
                    self.assertTrue(present(term, text), f"{kind} lost '{term}': {text}")

    def test_aliases_keep_source_text(self):
        for alias, row in MEASURE_SOURCE["aliases"].items():
            with self.subTest(alias=alias):
                self.assertTrue(row.get("source_text", "").strip())
                self.assertNotIn("quote", row)
                self.assertIn(row["code"], self.codes)

    def test_every_airspace_type_source_lists_its_defining_terms(self):
        self.assertEqual(set(AIRSPACE_TERMS), set(MEASURE_SOURCE["airspace_types"]))

    def test_airspace_type_definitions_keep_their_defining_terms(self):
        from openaix.describe.tables.common import AIRSPACE_TYPE_VALUES
        for name, terms in AIRSPACE_TERMS.items():
            row = MEASURE_SOURCE["airspace_types"][name]
            text = str(AIRSPACE_TYPE_VALUES[name])
            with self.subTest(airspace_type=name):
                self.assertTrue(row["source_text"].strip())
                self.assertTrue(row["paraphrase"].strip())
                self.assertTrue(row["verified"])
            for term in terms:
                with self.subTest(airspace_type=name, term=term):
                    self.assertTrue(present(term, text), f"{name} lost '{term}': {text}")

    def test_saafr_keeps_both_published_expansions_with_their_sources(self):
        expansions = {item["usage"]: item for item in self.codes["SAAFR"]["expansions"]}
        self.assertEqual(expansions["NATO"]["name"], "Slow Aviation Assets Flight Route")
        self.assertEqual(expansions["NATO"]["source"], "nato-ajp-3-3-5")
        self.assertEqual(expansions["US"]["name"], "Standard Use Army Aircraft Flight Route")
        self.assertEqual(expansions["US"]["source"], "joint-jp-3-52-2014")
        for item in expansions.values():
            with self.subTest(usage=item["usage"]):
                self.assertIn("below the coordination level", item["source_text"])

    def test_source_file_keeps_its_format(self):
        path = ROOT / "sources/measure-definitions.json"
        text = path.read_text()
        self.assertEqual(text, json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    unittest.main()
