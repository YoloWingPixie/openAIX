"""Control-measure semantic checks: airspace components, kill box floors, route vertices and measure catalogue identity.

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


def vertex_count(geometry):
    """Number of vertices of a route geometry: the points of a line or a corridor, the segment ends of a path, or the
    positions of a GeoJSON line. None for another shape."""
    if geometry.get("kind") in {"line", "corridor"}:
        return len(geometry.get("points", []))
    if geometry.get("kind") == "path":
        return len(geometry.get("segments", [])) + 1
    if geometry.get("kind") == "geojson" and geometry.get("geometry", {}).get("type") == "LineString":
        return len(geometry["geometry"].get("coordinates", []))
    return None


def path_segments(value, path):
    """A straight segment of a path that follows a straight segment starts at its end."""
    segments = value.get("segments", [])
    for index in range(1, len(segments)):
        before, segment = segments[index - 1], segments[index]
        if before.get("kind") == "line" and segment.get("kind") == "line" and segment.get("start") != before.get("end"):
            raise ContractError(pointer((*path, "segments", index, "start")), "path segment does not start at the end of the previous segment")


def route_vertices(value, path):
    """Each route vertex index and join vertex is a vertex of the route geometry; vertex indexes increase."""
    count = vertex_count(value["geometry"]) if isinstance(value.get("geometry"), dict) else None
    previous = -1
    for index, vertex in enumerate(value.get("vertices", [])):
        location = pointer((*path, "vertices", index, "index"))
        if count is not None and vertex["index"] >= count:
            raise ContractError(location, "route vertex index is outside the geometry")
        if vertex["index"] <= previous:
            raise ContractError(location, "route vertex indexes shall increase")
        previous = vertex["index"]
    for index, join in enumerate(value.get("joins", [])):
        if count is not None and join["vertex"] >= count:
            raise ContractError(pointer((*path, "joins", index, "vertex")), "join vertex is outside the geometry")
        if join["route"] == value.get("id"):
            raise ContractError(pointer((*path, "joins", index, "route")), "a route cannot join itself")


def semantic(value, path, period):
    if value.get("kind") == "path" and "segments" in value:
        path_segments(value, path)
    if "geometry" in value and ("vertices" in value or "joins" in value):
        route_vertices(value, path)
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
