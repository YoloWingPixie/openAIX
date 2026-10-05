"""Emitter checks: an emitter and the air defence measures it owns agree in position.

The emitter refers to its measures (emitter -> measure, one direction only). A missile arc starts at
the emitter: its centre is within ARC_TOLERANCE_M of the emitter position. A missile engagement zone
(or another air defence volume) contains the emitter: the position is inside at least one circular
component when the zone has circular components. Emitters without a position (simulator-bound only)
are not checked. Hooks follow the check/validate.py area contract.
"""
import math

from openaix.build.units import LENGTH_UNITS
from openaix.check.contract import ContractError, pointer

ARC_TOLERANCE_M = 500
EARTH_RADIUS_M = 6371008.8


def distance_m(a, b):
    lat1, lat2 = math.radians(a["latitude"]), math.radians(b["latitude"])
    dlat, dlon = lat2 - lat1, math.radians(b["longitude"] - a["longitude"])
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))


def metres(length):
    return length["value"] * LENGTH_UNITS[length["unit"]]


def semantic(value, path, period):
    pass


def catalogues(document, resources):
    return {}


def emitter_errors(emitters, measures):
    """(path, reason) for each emitter whose position disagrees with a measure it owns."""
    for identifier, emitter in emitters.items():
        if "position" not in emitter:
            continue
        if "min_engagement_range" in emitter and metres(emitter["min_engagement_range"]) >= metres(emitter["max_engagement_range"]):
            yield (identifier, "min_engagement_range"), "minimum engagement range must be smaller than the maximum"
        for index, selection in enumerate(emitter.get("measures", [])):
            measure = measures[selection["id"]]
            where = (identifier, "measures", index, "id")
            if measure["type"] == "MISARC":
                if distance_m(emitter["position"], measure["center"]) > ARC_TOLERANCE_M:
                    yield where, "missile arc centre does not agree with the emitter position"
                continue
            circles = [component["geometry"] for component in measure.get("components", [])
                       if component.get("operation", "add") == "add" and component["geometry"].get("kind") == "circle"]
            if circles and not any(distance_m(emitter["position"], circle["center"]) <= metres(circle["radius"]) for circle in circles):
                yield where, "emitter position is outside the engagement zone"


def document(document, resources):
    if "resources" not in document:
        return
    root = ("resources", "emitters")
    emitters = resources.get("emitters", {})
    for relative, reason in emitter_errors(emitters, resources.get("control_measures", {})):
        raise ContractError(pointer((*root, *relative)), reason)
