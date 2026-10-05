"""Order semantic checks: ATO identifiers and mission numbers, ACO assignments, and the order-local catalogues of
OPORD references (units, phases, requirements, decision points, command posts, organizations, enemy units and
protected sites).

Hooks called by check/validate.py: semantic(value, path, period), catalogues(document, resources),
document(document, resources). See check/navigation.py for the contract.
"""
from openaix.build.assignments import ROLE_USAGE
from openaix.check.contract import ContractError, contained_interval, pointer


def semantic(value, path, period):
    pass


# Order-local catalogues of an OPORD (build/opord/): catalogue name and the JSON paths of the identified entries.
# A `*` step is every item of a list.
ORDER_CATALOGUES = {
    "order_phases": (("execution", "concept_of_operations", "phases", "*"),),
    "order_requirements": (("execution", "coordinating_instructions", "ccir", "priority_intelligence_requirements", "*"),
                           ("execution", "coordinating_instructions", "ccir", "friendly_force_information_requirements", "*")),
    "order_decision_points": (("annexes", "C", "decision_points", "*"),),
    "order_command_posts": (("command_and_signal", "command_posts", "*"),),
    "order_organizations": (("situation", "interagency_organizations", "*"),),
    "order_enemy_units": (("situation", "enemy_forces", "units", "*"),),
    "order_protected_sites": (("annexes", "K", "protected_sites", "*"),),
}


def _entries(value, steps, path=()):
    if not steps:
        yield path, value
        return
    step, rest = steps[0], steps[1:]
    if step == "*":
        for index, item in enumerate(value if isinstance(value, list) else []):
            yield from _entries(item, rest, (*path, index))
    elif isinstance(value, dict) and step in value:
        yield from _entries(value[step], rest, (*path, step))


def order_catalogues(document):
    """Identified OPORD entries by catalogue; an identifier repeated within one catalogue fails."""
    result = {"order_units": dict(document.get("task_organization", {}))}
    for name, paths in ORDER_CATALOGUES.items():
        catalogue = {}
        for steps in paths:
            for path, entry in _entries(document, steps):
                if entry["id"] in catalogue:
                    raise ContractError(pointer((*path, "id")), "duplicate identifier")
                catalogue[entry["id"]] = entry
        result[name] = catalogue
    return result


def catalogues(document, resources):
    """Unique ATO missions, packages and flights and the OPORD-local catalogues, used to resolve x-catalog references."""
    result = {}
    if document.get("kind") == "opord":
        result.update(order_catalogues(document))
    if document.get("kind") == "ato":
        for collection in ("missions", "packages", "flights"):
            items = [(index, item) for index, item in enumerate(document.get(collection, []))]
            if collection == "flights":
                items = [((mi, "flights", fi), flight) for mi, mission in enumerate(document["missions"])
                         for fi, flight in enumerate(mission["flights"])]
            catalogue = {}
            for index, item in items:
                path = ("missions", *index, "id") if isinstance(index, tuple) else (collection, index, "id")
                if item["id"] in catalogue:
                    raise ContractError(pointer(path), "duplicate identifier")
                catalogue[item["id"]] = item
            result[collection] = catalogue
        numbers = set()
        for index, mission in enumerate(document["missions"]):
            # Units cross-reference missions by number on kneeboards and by voice (ORDERS-02).
            if mission["mission_number"] in numbers:
                raise ContractError(pointer(("missions", index, "mission_number")), "duplicate mission number")
            numbers.add(mission["mission_number"])
    return result


def document(document, resources):
    if document.get("kind") == "aco":
        for index, assignment in enumerate(document["assignments"]):
            measure = resources["control_measures"][assignment["measure"]]
            path = ("assignments", index)
            if "role" in assignment and measure["type"] != "ORBIT":
                raise ContractError(pointer((*path, "role")), "orbit role requires an Orbit measure")
            if "usage" in assignment and assignment.get("role") in ROLE_USAGE and assignment["usage"] != ROLE_USAGE[assignment["role"]]:
                raise ContractError(pointer((*path, "usage")), "usage contradicts the orbit role")
            if "killbox_status" in assignment and measure["type"] != "KB":
                raise ContractError(pointer((*path, "killbox_status")), "firing status requires a kill box")
            contained_interval(assignment["effective"], document["period"], document["period"], (*path, "effective"))
            if assignment["state"] == "active" and "active" in measure:
                contained_interval(assignment["effective"], measure["active"], document["period"], (*path, "effective"))
