"""Contract errors and the generic time and altitude ordering helpers shared by validators."""
import datetime
import math

from rfc3339_validator import validate_rfc3339

from openaix.build.availability import contains
from openaix.build.units import ALTITUDE_UNITS


class ContractError(ValueError):
    def __init__(self, path, code):
        self.path, self.code = path, code
        super().__init__(f"{path or '/'}: {code}")


def pointer(parts):
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def timestamp(value, path=()):
    """Parse one RFC 3339 date-time, accepting the lowercase separators that RFC 3339 permits."""
    if not isinstance(value, str) or not validate_rfc3339(value.upper()):
        raise ContractError(pointer(path), "invalid date-time")
    return datetime.datetime.fromisoformat(value.upper().replace("Z", "+00:00")).timestamp()


def instant(value, period, path=()):
    if isinstance(value, dict):
        if period is None:
            return value["offset_minutes"] * 60
        return instant(period["start"], None, path) + value["offset_minutes"] * 60
    return timestamp(value, path)


def interval(window, period, path):
    if period is None and isinstance(window["start"], dict) != isinstance(window["end"], dict):
        raise ContractError(pointer(path), "mixed absolute and relative times require an order period")
    start, end = instant(window["start"], period, (*path, "start")), instant(window["end"], period, (*path, "end"))
    if start >= end:
        raise ContractError(pointer(path), "non-positive time window")
    return start, end


def contained_interval(child, parent, period, path):
    if parent.get("continuous"):
        return
    if child.get("continuous"):
        raise ContractError(pointer(path), "continuous availability exceeds a bounded parent interval")
    if period is None and isinstance(child["start"], dict) != isinstance(parent["start"], dict):
        raise ContractError(pointer(path), "interval comparison requires an order period")
    start, end = interval(child, period, path)
    parent_start, parent_end = interval(parent, period, path)
    if start < parent_start or end > parent_end:
        raise ContractError(pointer(path), "interval lies outside parent availability")
    if "schedule" in parent and not contains(child, parent, period, instant):
        raise ContractError(pointer(path), "interval includes time outside the parent schedule")


def limit_level(limit):
    """Return (reference, metres) for a vertical limit; surface and unlimited compare with any reference."""
    if limit.get("surface"):
        return None, -math.inf
    if limit.get("unlimited"):
        return None, math.inf
    return limit["reference"], limit["value"] * ALTITUDE_UNITS[limit["unit"]]


def limit_difference(lower, upper):
    """Return lower minus upper in metres, or None when the references cannot be compared."""
    (lower_reference, floor), (upper_reference, ceiling) = limit_level(lower), limit_level(upper)
    if lower_reference and upper_reference and lower_reference != upper_reference:
        return None
    if floor == ceiling:
        return 0
    return floor - ceiling


def check_limits(lower, upper, path, allow_equal=True):
    if lower.get("unlimited"):
        raise ContractError(pointer(path), "unlimited is not a valid floor")
    if upper.get("surface"):
        raise ContractError(pointer(path), "surface is not a valid ceiling")
    difference = limit_difference(lower, upper)
    if difference is not None and (difference > 0 or (difference == 0 and not allow_equal)):
        raise ContractError(pointer(path), "reversed or empty altitude limits")


def component_limits(component, path):
    """Check a component's effective floor and ceiling after minimum/maximum overrides raise them."""
    limits = [component["lower_limit"], component["upper_limit"]]
    check_limits(limits[0], {"unlimited": True}, path)
    check_limits({"surface": True}, limits[1], path)
    for index, key in enumerate(("minimum_limit", "maximum_limit")):
        if key in component:
            difference = limit_difference(component[key], limits[index])
            if difference is None:
                return
            if difference > 0:
                limits[index] = component[key]
    check_limits(*limits, path, allow_equal=False)
