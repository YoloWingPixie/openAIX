"""Render a communications standard as Markdown tables in the layout of the Victoria comm plan and laser plan pages.

python3 -m openaix comms render <file> --format md [--section comm_plan|laser_plan]

The output is deterministic and has no timestamps. The comm plan page has the broadband channels, the flight radio and
signals tables and the additional tankers; the laser plan page has the per-aircraft table and the flight-wise table.
"""
import argparse
import json
from pathlib import Path

LADDER = "uhf_"
# Flights of the F-16 have their own table, as on the page; the other flights are in the carrier air wing table.
WING_TABLES = {"f_16c": "AW13"}
DEFAULT_TABLE = "CVW-1"


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "|".join("-" * (len(name) + 2) for name in header) + "|"]
    return lines + ["| " + " | ".join(map(str, row)) + " |" for row in rows]


def mhz(channel, places=2):
    return f"{channel['frequency']['value']:.{places}f}"


def tacan(entry):
    return f"{entry['channel']}{entry['band']}"


def comm_plan(document):
    channels = document["channels"]
    rows = []
    for number in range(1, 21):
        channel = channels.get(f"{LADDER}{number:02d}")
        rows.append(("Intraflight", f"{number:02d}", "->") if channel is None else (channel["name"], f"{number:02d}", mhz(channel)))
    out = ["# Comm Plan", "", "**Broadband Channels**", *table(("Name", "Channel", "Frequency"), rows), "", "**Flight Radio and Signals**"]
    tables = {}
    for flight in document["flights"].values():
        tables.setdefault(WING_TABLES.get(flight["aircraft_type"], DEFAULT_TABLE), []).append(flight)
    for name, flights in sorted(tables.items(), key=lambda item: item[0] != DEFAULT_TABLE):
        out += ["", name]
        header = ("Flight", "Frequency", "MIDS", "Lead TACAN", "Wing TACAN", "TNDL Callsign", "STN")
        rows = []
        for flight in flights:
            pair = flight["tacan_aa"]
            rows.append((flight["callsign"].title(), mhz(channels[flight["intraflight"]], 3 if name != DEFAULT_TABLE else 2),
                         flight.get("mids_channel", "--"), tacan(pair["lead"]), tacan(pair["wing"]), flight["datalink_callsign"],
                         flight["stn_block"] + "*"))
        out += table(header, rows)
    rows = []
    for record in document["support"].values():
        if record["role"] == "awacs":
            continue
        frequencies = " / ".join(mhz(channels[name]) for name in record["channels"])
        rows.append((record["callsign"], frequencies, record["tacan"].get("identifier", ""), f"{record['tacan']['channel']:03d}{record['tacan']['band']}"))
    out += ["", "## Additional Tankers", *table(("Tanker", "Freq", "TACAN Callsign", "TACAN Channel"), rows)]
    return out


def laser_plan(document):
    flights = document["flights"]
    squadrons = {}
    for flight in sorted(flights.values(), key=lambda item: item["laser_block"]):
        squadrons.setdefault(flight["squadron"], []).append(flight)
    columns = [[(f"{flight['callsign']} {member['member']}", member["laser_code"]) for flight in group for member in flight["members"]]
               for group in squadrons.values()]
    laser = document["laser"]
    columns[0] += [("JTAC", entry["code"]) for entry in laser.get("jtac", [])]
    header = [name for _ in columns for name in ("FLIGHT", "CODE")]
    rows = []
    for index in range(max(map(len, columns))):
        rows.append([cell for column in columns for cell in (column[index] if index < len(column) else ("", ""))])
    out = ["# Laser Plan", "", "## Plan", *table(header, rows), "", "## Flight-wise Plan",
           *table(("FLIGHT", "CODE"), [(name.upper(), code) for name, code in laser.get("alternates", {}).items()])]
    return out


SECTIONS = {"comm_plan": comm_plan, "laser_plan": laser_plan}


def render(document, section=None):
    names = [section] if section else list(SECTIONS)
    return "\n\n".join("\n".join(SECTIONS[name](document)) for name in names) + "\n"


def main():
    parser = argparse.ArgumentParser(prog="openaix comms")
    parser.add_argument("command", choices=("render",))
    parser.add_argument("file", type=Path)
    parser.add_argument("--format", choices=("md",), default="md")
    parser.add_argument("--section", choices=sorted(SECTIONS))
    args = parser.parse_args()
    document = json.loads(args.file.read_text())
    if document.get("kind") != "comms_standard":
        raise SystemExit("not a comms_standard document: " + str(args.file))
    print(render(document, args.section), end="")
