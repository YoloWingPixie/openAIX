"""Control-measure semantic checks: airspace components, kill box floors and measure catalogue identity.

Hooks called by check/validate.py: semantic(value, path, period), catalogues(document, resources),
document(document, resources). See check/navigation.py for the contract.
"""
from openaix.check.contract import ContractError, contained_interval, pointer


def surface(limit):
    """True for an explicit surface floor or a zero height above ground."""
    return bool(limit.get("surface")) or (limit.get("reference") == "AGL" and limit.get("value") == 0)


def same_altitude(limit, altitude):
    """True when a vertical limit is the stated altitude: same value, unit and reference."""
    return bool(altitude) and all(limit.get(key) == altitude.get(key) for key in ("value", "unit", "reference"))


def semantic(value, path, period):
    if "components" in value:
        identifiers = set()
        for index, part in enumerate(value["components"]):
            if index == 0 and part["operation"] != "add":
                raise ContractError(pointer((*path, "components", index, "operation")), "first component must add a volume")
            if part["id"] in identifiers:
                raise ContractError(pointer((*path, "components", index, "id")), "duplicate component identifier")
            identifiers.add(part["id"])
            if "active" in part and "active" in value:
                contained_interval(part["active"], value["active"], period, (*path, "components", index, "active"))
    if value.get("type") == "KB" and "killbox_kind" in value:
        # FM 3-09 (2024) B-19: a purple kill box has an altitude floor. Kill box MTTP (2009) Ch I 2.c(2): a blue kill box
        # extends from the surface, or from the coordinating altitude when one is established.
        coordinating = value.get("coordinating_altitude")
        for index, part in enumerate(value.get("components", [])):
            if part["operation"] != "add":
                continue
            location = pointer((*path, "components", index, "lower_limit"))
            floor = part["lower_limit"]
            if value["killbox_kind"] == "blue" and not (surface(floor) or same_altitude(floor, coordinating)):
                raise ContractError(location, "a blue kill box extends from the surface or from its coordinating altitude")
            if value["killbox_kind"] == "purple" and surface(part["lower_limit"]):
                raise ContractError(location, "a purple kill box requires an altitude floor above the surface")


def catalogues(document, resources):
    return {}


def document(document, resources):
    for identifier, measure in resources.get("control_measures", {}).items():
        if "id" in measure and measure["id"] != identifier:
            raise ContractError(pointer(("resources", "control_measures", identifier, "id")), "catalogue key and identifier differ")
