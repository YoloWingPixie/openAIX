"""SCL checks: the bill of stores agrees with the stations, flights agree with their loads, weapon loads and
engagement means name stores that the load carries, and DCS stations exist on the DCS aircraft type.

- An SCL lists each store once in its bill (`stores`). When it has stations, the quantity of each store on its
  stations is equal to its quantity in the bill. A rack is a store of the `rack` type, only in `rack`.
- A flight that names an SCL (primary, secondary, alternative or aircraft override) has the aircraft type of the
  SCL: both name the same entry of the `aircraft_types` catalogue. The primary SCL and the SCL of an aircraft override list the tasking of the mission when they list missions.
- A weapon load names a store of an SCL of its flight (or of the assigned flights), and not more weapons than the
  flight carries; the `scl` of a weapon load is an SCL of the flight. The required stores of an attack assignment
  are carried by an assigned flight. A TST or JIPTL engagement means with an SCL and a store names a carried store.
- DCS (`extensions.sim.dcs`): the DCS data of a station names a pylon of the DCS type of the aircraft type, its
  Mission Editor label and a CLSID that DCS accepts on that pylon (sources/dcs/aircraft-stations.json, DCS World 2.9
  data from the dcs-lua-datamine); the DCS load of the SCL names the same DCS type. Aircraft types without a DCS type
  or without station data are not checked.

Hooks follow the check/validate.py area contract.
"""
import json
from collections import Counter
from functools import lru_cache

from openaix import ROOT
from openaix.check.contract import ContractError, pointer

STATION_DATA = ROOT / "sources/dcs/aircraft-stations.json"


@lru_cache(maxsize=1)
def dcs_stations():
    """DCS aircraft type -> {pylon number (text): {"label", "clsids"}}."""
    return {name: aircraft["stations"] for name, aircraft in json.loads(STATION_DATA.read_text())["aircraft"].items()}


def semantic(value, path, period):
    pass


def catalogues(document, resources):
    return {}


def dcs_data(record):
    return record.get("extensions", {}).get("sim", {}).get("dcs", {})


def dcs_aircraft_type(scl, aircraft_types):
    """The DCS type name of the aircraft type of an SCL, or None."""
    return dcs_data(aircraft_types.get(scl.get("aircraft_type"), {})).get("type")


def carried(scl):
    """Store identifier -> quantity in each aircraft: the bill of stores, or the sum on the stations without a bill."""
    if scl.get("stores"):
        return {item["store"]: item["quantity"] for item in scl["stores"]}
    total = Counter()
    for station in scl.get("stations", []):
        for item in station["items"]:
            total[item["store"]] += item["quantity"]
    return dict(total)


def scl_errors(scl, stores, aircraft_types):
    """(relative path, reason) for each disagreement inside one SCL."""
    bill = {}
    for index, item in enumerate(scl.get("stores", [])):
        if item["store"] in bill:
            yield ("stores", index, "store"), "store repeated in the bill of stores"
        bill[item["store"]] = item["quantity"]
        if stores[item["store"]]["kind"] == "rack":
            yield ("stores", index, "store"), "a rack goes in the rack field of a station, not in the bill of stores"
    labels, on_stations = set(), Counter()
    for index, station in enumerate(scl.get("stations", [])):
        if station["station"] in labels:
            yield ("stations", index, "station"), "station repeated in the layout"
        labels.add(station["station"])
        if "rack" in station and stores[station["rack"]]["kind"] != "rack":
            yield ("stations", index, "rack"), "rack requires a store of the rack type"
        for position, item in enumerate(station["items"]):
            on_stations[item["store"]] += item["quantity"]
            if stores[item["store"]]["kind"] == "rack":
                yield ("stations", index, "items", position, "store"), "a rack goes in the rack field of the station"
    if scl.get("stations") and scl.get("stores"):
        for store in sorted(bill.keys() | on_stations.keys()):
            if bill.get(store, 0) != on_stations.get(store, 0):
                yield ("stations",), "station quantities of " + store + " do not agree with the bill of stores"
    yield from station_errors(scl, aircraft_types)


def station_errors(scl, aircraft_types):
    """DCS load and station data against the DCS type of the aircraft type of the SCL."""
    aircraft_type = dcs_aircraft_type(scl, aircraft_types)
    payload = dcs_data(scl).get("payload", {})
    if aircraft_type and "unit_type" in payload and payload["unit_type"] != aircraft_type:
        yield ("extensions", "sim", "dcs", "payload", "unit_type"), "DCS load is for another aircraft type than the SCL"
    table = dcs_stations().get(aircraft_type)
    if table is None:
        return
    for index, station in enumerate(scl.get("stations", [])):
        data = dcs_data(station)
        if "pylon" not in data:
            continue
        path = ("stations", index, "extensions", "sim", "dcs")
        pylon = table.get(str(data["pylon"]))
        if pylon is None:
            yield (*path, "pylon"), "DCS pylon number is not a station of " + aircraft_type
            continue
        if "label" in data and data["label"] != pylon["label"]:
            yield (*path, "label"), "DCS station label does not agree with the pylon number"
        if "clsid" in data and data["clsid"] not in pylon["clsids"]:
            yield (*path, "clsid"), "DCS does not accept this CLSID on the pylon"


def flight_scls(flight):
    """(path below the flight, SCL identifier, mission check) for every SCL that a flight names."""
    config = flight.get("configuration")
    if not config:
        return
    yield ("configuration", "primary_scl"), config["primary_scl"], True
    if "secondary_scl" in config:
        yield ("configuration", "secondary_scl"), config["secondary_scl"], False
    for index, alternative in enumerate(config.get("alternatives", [])):
        yield ("configuration", "alternatives", index, "scl"), alternative["scl"], False
    for index, override in enumerate(config.get("member_overrides", [])):
        if "scl" in override:
            yield ("configuration", "member_overrides", index, "scl"), override["scl"], True


def tasking_role(tasking):
    return tasking.get("role", tasking.get("mission_type"))


def covers(scl, tasking):
    role = tasking_role(tasking)
    return any(entry["tasking"] == tasking["kind"] and entry.get("role", role) == role for entry in scl["missions"])


def flight_errors(ato, scls):
    """(path, reason) for each flight whose SCL has another aircraft type or does not list the tasking of the mission."""
    for mission_index, mission in enumerate(ato.get("missions", [])):
        for flight_index, flight in enumerate(mission["flights"]):
            for relative, identifier, mission_check in flight_scls(flight):
                scl = scls[identifier]
                path = ("missions", mission_index, "flights", flight_index, *relative)
                if scl.get("aircraft_type") != flight["aircraft_type"]:
                    yield path, "SCL aircraft type does not agree with the flight"
                elif mission_check and "missions" in scl and not covers(scl, mission["tasking"]):
                    yield path, "SCL missions do not include the tasking of the mission"


def weapon_errors(ato, scls):
    """(path, reason) for each weapon load or required store that the loads of the flights do not carry."""
    flights = {flight["id"]: flight for mission in ato.get("missions", []) for flight in mission["flights"]}

    def loads(flight_ids):
        return {identifier for flight_id in flight_ids for _, identifier, _ in flight_scls(flights[flight_id])}

    for mission_index, mission in enumerate(ato.get("missions", [])):
        for assignment_index, assignment in enumerate(mission["tasking"].get("assignments", [])):
            path = ("missions", mission_index, "tasking", "assignments", assignment_index)
            assigned = [selection["flight"] for selection in assignment.get("assigned_to", [])]
            available = loads(assigned)
            for index, store in enumerate(assignment.get("required_stores", [])):
                if available and not any(store in carried(scls[identifier]) for identifier in available):
                    yield (*path, "required_stores", index), "no SCL of the assigned flights carries the required store"
            for index, load in enumerate(assignment.get("weaponeering", [])):
                where = (*path, "weaponeering", index)
                candidates = loads([load["flight"]] if "flight" in load else assigned)
                if "scl" in load:
                    if "flight" in load and candidates and load["scl"] not in candidates:
                        yield (*where, "scl"), "SCL is not a load of the flight"
                        continue
                    candidates = {load["scl"]}
                if not candidates:
                    continue
                per_aircraft = max(carried(scls[identifier]).get(load["store"], 0) for identifier in candidates)
                if per_aircraft == 0:
                    yield (*where, "store"), "no SCL of the flight carries the store"
                elif "flight" in load and "quantity" in load and load["quantity"] > per_aircraft * flights[load["flight"]]["count"]:
                    yield (*where, "quantity"), "quantity is more than the flight carries"


def engagement_errors(document, scls):
    """(path, reason) for each TST or JIPTL engagement means whose SCL does not carry its store."""
    for index, entry in enumerate(document.get("targets", [])):
        for position, means in enumerate(entry.get("authorized_engagement_means", [])):
            if "scl" in means and "store" in means and means["store"] not in carried(scls[means["scl"]]):
                yield ("targets", index, "authorized_engagement_means", position, "store"), "the SCL does not carry the store"


def errors(document, resources):
    kind = document.get("kind")
    stores, scls, types = resources.get("stores", {}), resources.get("scls", {}), resources.get("aircraft_types", {})
    if kind == "scl":
        yield from scl_errors(document, stores, types)
    if isinstance(document.get("resources"), dict):
        for identifier, scl in document["resources"].get("scls", {}).items():
            path = ("resources", "scls", identifier)
            if scl["id"] != identifier:
                yield (*path, "id"), "SCL identifier does not agree with its key"
            for relative, reason in scl_errors(scl, stores, types):
                yield (*path, *relative), reason
    if kind == "ato":
        yield from flight_errors(document, scls)
        yield from weapon_errors(document, scls)
    if kind in ("tst", "jiptl"):
        yield from engagement_errors(document, scls)


def document(document, resources):
    for path, reason in errors(document, resources):
        raise ContractError(pointer(path), reason)
