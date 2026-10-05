"""Navigation semantic checks: MSA sector sweep, Grid MORA cell bounds, radio bands, runway ends and airfield links.

check/validate.py calls every area module's hooks:
- semantic(value, path, period): once per JSON object node.
- catalogues(document, resources): extra reference catalogues for x-catalog resolution.
- document(document, resources): once per document after reference resolution.
Altitude-constraint ordering (lower below upper) is the engine's generic lower/upper check.

Airfield links go in two directions: an airfield lists its navigation aids, localizers and instrument procedures,
and each of those records may name its airfield. When both sides state the link, they agree. A record that a
document does not contain (an entry of a linked resource catalogue) is checked when that catalogue is validated.
"""
from openaix.build.units import RADIO_BANDS
from openaix.check.contract import ContractError, pointer


AIRFIELD_KINDS = ("airfield", "carrier", "farp")
# Airfield list field, resource catalogue and the record discriminator of the listed records.
LINKS = (("navaids", "control_measures"), ("localizers", "localizers"), ("procedures", "instrument_procedures"))


def reciprocal(designator):
    """Designator of the opposite runway end: 18 from the number, with `L` and `R` exchanged."""
    number, suffix = int(designator[:2]), designator[2:]
    return "%02d" % ((number + 17) % 36 + 1) + {"L": "R", "R": "L"}.get(suffix, suffix)


def band_errors(value, path):
    band = value["band"]
    megahertz = value["value"] / 1000 if value["unit"] == "kHz" else value["value"]
    low, high = RADIO_BANDS[band]
    if not low <= megahertz < high:
        yield (*path, "band"), f"frequency {megahertz:g} MHz is outside the {band} band"
    elif band == "fm" and value.get("modulation") == "AM":
        yield (*path, "modulation"), "the fm band uses frequency modulation"


def frequency_band(value, path):
    """A stated radio band agrees with the frequency value (and the FM band with FM modulation)."""
    for location, reason in band_errors(value, path):
        raise ContractError(pointer(location), reason)


def end_errors(runway, path):
    designators = [end["designator"] for end in runway["ends"]]
    if runway["designator"] != "/".join(designators):
        yield (*path, "designator"), "runway designator must join its end designators with /"
    elif len(designators) == 2 and reciprocal(designators[0]) != designators[1]:
        yield (*path, "ends"), "runway ends must have reciprocal designators"


def runway_ends(runway, path):
    """A runway joins the designators of its two ends, and the ends are reciprocal."""
    for location, reason in end_errors(runway, path):
        raise ContractError(pointer(location), reason)


def end_designators(airfield):
    return [end["designator"] for runway in airfield.get("runways", []) for end in runway.get("ends", [])]


def reference_errors(airfield, path):
    seen = set()
    for index, runway in enumerate(airfield.get("runways", [])):
        if "airfield" in runway and "id" in airfield and runway["airfield"] != airfield["id"]:
            yield (*path, "runways", index, "airfield"), "a listed runway must name the airfield that lists it"
        for number, end in enumerate(runway.get("ends", [])):
            if end.get("designator") in seen:
                yield (*path, "runways", index, "ends", number, "designator"), "runway end designators must be unique in an airfield"
            seen.add(end.get("designator"))
    for field in (("calm_wind_runway",), ("atis", "runway_in_use")):
        value = airfield
        for key in field:
            value = value.get(key) if isinstance(value, dict) else None
        if value is not None and value not in seen:
            yield (*path, *field), "runway designator does not name an end of a runway of this airfield"
    yield from taxi_errors(airfield, path, seen)


def taxi_errors(airfield, path, ends):
    """Stand and taxi node identifiers are unique; taxi links name runway ends, stands and nodes of this airfield."""
    stands = set()
    for index, stand in enumerate(airfield.get("parking", [])):
        if stand.get("id") in stands:
            yield (*path, "parking", index, "id"), "stand identifiers must be unique in an airfield"
        stands.add(stand.get("id"))
    graph = airfield.get("taxi") or {}
    nodes = set()
    for index, node in enumerate(graph.get("nodes", [])):
        location = (*path, "taxi", "nodes", index)
        if node.get("id") in nodes:
            yield (*location, "id"), "taxi node identifiers must be unique in an airfield"
        nodes.add(node.get("id"))
        if "runway_end" in node and node["runway_end"] not in ends:
            yield (*location, "runway_end"), "runway designator does not name an end of a runway of this airfield"
        if "stand" in node and node["stand"] not in stands:
            yield (*location, "stand"), "the taxi node names no stand of this airfield"
    for index, edge in enumerate(graph.get("edges", [])):
        for field in ("from", "to"):
            if edge.get(field) not in nodes:
                yield (*path, "taxi", "edges", index, field), "the taxi edge names no node of this graph"
        if edge.get("from") == edge.get("to"):
            yield (*path, "taxi", "edges", index, "to"), "a taxi edge joins two different nodes"


def runway_end_references(airfield, path):
    """Runway end designators are unique in an airfield, the airfield references name one of them, and a listed runway
    names the airfield that lists it."""
    for location, reason in reference_errors(airfield, path):
        raise ContractError(pointer(location), reason)


def object_errors(value, path):
    """Problems of one JSON object that do not need other records."""
    if {"value", "unit", "band"} <= value.keys() and value.get("unit") in ("kHz", "MHz"):
        yield from band_errors(value, path)
    if value.get("kind") == "runway" and isinstance(value.get("ends"), list) and "designator" in value:
        yield from end_errors(value, path)
    if value.get("kind") in AIRFIELD_KINDS and ({"runways", "calm_wind_runway", "atis", "parking", "taxi"} & value.keys()):
        yield from reference_errors(value, path)


def _listed(airfield, field):
    values = airfield.get(field)
    if values is None:
        return None
    return [item["id"] if isinstance(item, dict) else item for item in values]


def link_errors(document, resources):
    """Disagreeing airfield links between the document and the catalogue entries it can see."""
    inline = isinstance(document.get("resources"), dict)

    def entries(catalogue, predicate=lambda record: True):
        return {key: (record, ("resources", catalogue, key) if inline else None)
                for key, record in (resources.get(catalogue) or {}).items() if isinstance(record, dict) and predicate(record)}

    airfields = entries("places")
    records = {"navaids": entries("control_measures", lambda record: record.get("type") == "NAVAID"),
               "localizers": entries("localizers"), "procedures": entries("instrument_procedures")}
    own = document.get("id")
    if document.get("kind") in AIRFIELD_KINDS:
        airfields[own] = (document, ())
    for field, kind in (("navaids", None), ("localizers", "localizer"), ("procedures", "procedure")):
        if (kind and document.get("kind") == kind) or (kind is None and document.get("type") == "NAVAID"):
            records[field][own] = (document, ())

    def at(base, *rest):
        return None if base is None else (*base, *rest)

    errors = []
    for identifier, (airfield, base) in airfields.items():
        for field, _ in LINKS:
            for index, item in enumerate(_listed(airfield, field) or []):
                record = records[field].get(item)
                if record and record[0].get("airfield", identifier) != identifier:
                    errors.append((at(base, field, index), f"listed {field[:-1]} {item} names another airfield"))
        localizers = _listed(airfield, "localizers")
        for index, runway in enumerate(airfield.get("runways", [])):
            for number, end in enumerate(runway.get("ends", [])):
                if "localizer" not in end or end["localizer"] not in records["localizers"]:
                    continue
                localizer = records["localizers"][end["localizer"]][0]
                location = at(base, "runways", index, "ends", number, "localizer")
                if localizer.get("runway") != end["designator"]:
                    errors.append((location, "the localizer serves another runway end"))
                elif localizer.get("airfield", identifier) != identifier:
                    errors.append((location, "the localizer names another airfield"))
                elif localizers is not None and end["localizer"] not in localizers:
                    errors.append((location, "the runway end localizer is not in the airfield localizers"))
    for field, _ in LINKS:
        for identifier, (record, base) in records[field].items():
            target = airfields.get(record.get("airfield"))
            if target is None:
                continue
            listed = _listed(target[0], field)
            if listed is not None and identifier not in listed:
                errors.append((at(base, "airfield"), f"the airfield does not list this {field[:-1]}"))
            if field == "localizers" and "runway" in record and target[0].get("runways") and record["runway"] not in end_designators(target[0]):
                errors.append((at(base, "runway"), "the localizer runway is not an end of a runway of its airfield"))
    if document.get("kind") == "runway" and document.get("airfield") in airfields:
        target = airfields[document["airfield"]][0]
        designators = [runway.get("designator") for runway in target.get("runways", [])]
        if designators and document.get("designator") not in designators:
            errors.append((("designator",), "the airfield of this runway has no runway with this designator"))
    if inline:
        for key, profile in (resources.get("pattern_profiles") or {}).items():
            if isinstance(profile, dict) and "profile" in profile:
                errors.append((("resources", "pattern_profiles", key, "profile"), "a named pattern profile cannot refer to another profile"))
    return [(path, reason) for path, reason in errors if path is not None]


def airfield_links(document, resources):
    """Airfield, navigation aid, localizer and procedure links agree in both directions."""
    for path, reason in link_errors(document, resources):
        raise ContractError(pointer(path), reason)


def pattern_profiles(document, resources):
    """A named traffic pattern profile does not refer to another profile."""
    for path, reason in link_errors(document, resources):
        if path[:2] == ("resources", "pattern_profiles"):
            raise ContractError(pointer(path), reason)


def clockwise(start, end):
    return (end["value"] - start["value"]) % 360


def msa_sectors(sectors, path):
    """Bearings are bearings TO the centre, swept clockwise from start to end; sectors tile the circle."""
    references = {bearing["reference"] for sector in sectors for bearing in (sector["start_bearing"], sector["end_bearing"])}
    if len(references) > 1:
        raise ContractError(pointer((*path, "sectors")), "MSA sector bearings require one reference")
    for index, sector in enumerate(sectors):
        same = sector["start_bearing"]["value"] % 360 == sector["end_bearing"]["value"] % 360
        if sector["full_circle"] != same:
            raise ContractError(pointer((*path, "sectors", index)), "MSA full-circle flag disagrees with limiting bearings")
    if len(sectors) == 1:
        if not sectors[0]["full_circle"]:
            raise ContractError(pointer((*path, "sectors", 0)), "a single MSA sector must cover the full circle")
        return
    for index, sector in enumerate(sectors):
        following = sectors[(index + 1) % len(sectors)]
        if sector["full_circle"]:
            raise ContractError(pointer((*path, "sectors", index)), "a full-circle MSA sector cannot share the circle")
        if sector["end_bearing"]["value"] % 360 != following["start_bearing"]["value"] % 360:
            raise ContractError(pointer((*path, "sectors", index, "end_bearing")), "MSA sectors must continue clockwise from the previous end bearing")
    if sum(clockwise(sector["start_bearing"], sector["end_bearing"]) for sector in sectors) != 360:
        raise ContractError(pointer((*path, "sectors")), "MSA sectors must sweep the circle exactly once")


def grid_cells(cells, path):
    seen = set()
    for index, cell in enumerate(cells):
        location = (*path, "cells", index)
        sw, ne = cell["southwest"], cell["northeast"]
        if sw["latitude"] != int(sw["latitude"]) or sw["longitude"] != int(sw["longitude"]):
            raise ContractError(pointer((*location, "southwest")), "Grid MORA cell corners lie on whole degrees")
        if ne["latitude"] - sw["latitude"] != 1 or ne["longitude"] - sw["longitude"] != 1:
            raise ContractError(pointer(location), "Grid MORA cell must span one degree north and east")
        key = (sw["latitude"], sw["longitude"])
        if key in seen:
            raise ContractError(pointer(location), "duplicate Grid MORA cell")
        seen.add(key)


def semantic(value, path, period):
    for location, reason in object_errors(value, path):
        raise ContractError(pointer(location), reason)
    if value.get("kind") == "msa" and "sectors" in value:
        msa_sectors(value["sectors"], path)
    if value.get("kind") == "grid-mora" and "cells" in value:
        grid_cells(value["cells"], path)


def catalogues(document, resources):
    return {}


def document(document, resources):
    airfield_links(document, resources)
