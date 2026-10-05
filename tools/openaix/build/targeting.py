"""Target-list documents: the Joint Integrated Prioritized Target List (JIPTL) and Time-Sensitive Targets (TST).

Both are imported from opord-builder and trimmed to the fields units coordinate on (ORDERS-05).
Priority tiers and categories are openAIX/application values, not joint doctrine (DOCTRINE-07).
Descriptions come from describe/resolve.py.
"""
from openaix.build.common import external, obj, text

# Fields kept on each target-list entry (ORDERS-05 keep lists).
JIPTL_FIELDS = ("target_number", "target_name", "target_description", "priority_rank", "location", "location_mgrs",
                "desired_effect", "component_tasked", "authorized_engagement_means", "status")
TST_FIELDS = ("tst_number", "target_description", "expected_locations", "activity_window", "authorized_engagement_means",
              "engagement_authority", "roe_constraints", "expiration_criteria")
# Joint force components that can be tasked with a target; information operations is a staff
# capability, not a joint force component (DOCTRINE-07).
JOINT_COMPONENTS = ("LAND", "AIR", "MARITIME", "SOF", "CYBER", "SPACE")


def normalize_targeting(schema, common):
    """Spell the imported JPITL entry as the Joint Integrated Prioritized Target List (JIPTL) throughout."""
    def visit(value):
        if isinstance(value, dict):
            return {({"JPITLEntry": "JIPTLTarget", "jpitl": "jiptl"}.get(key, key)): visit(child) for key, child in value.items()}
        if isinstance(value, list):
            return [visit(child) for child in value]
        if isinstance(value, str):
            if value == "jpitl":
                return "jiptl"
            return value.replace("Joint Prioritized Integrated Target List", "Joint Integrated Prioritized Target List").replace("JPITLEntry", "JIPTLTarget").replace("JPITL", "JIPTL")
        return value

    result = visit(schema)
    target = result.get("$defs", {}).get("JIPTLTarget")
    if target:
        target["title"] = "Prioritized target"
        target["properties"]["target_number"].update({"minLength": 1, "pattern": r"\S"})
        target["properties"]["priority_rank"]["minimum"] = 1
        target["properties"]["status"].pop("default", None)
    return result


def keep(definition, names):
    definition["properties"] = {name: field for name, field in definition["properties"].items() if name in names}
    definition["required"] = [name for name in definition.get("required", []) if name in names]


def target_list(schema, name):
    """Turn an imported target list into an openAIX document with a `targets` array and common metadata."""
    schema["properties"]["targets"] = schema["properties"].pop("entries")
    schema["properties"]["targets"].pop("description", None)
    schema["properties"]["targets"].pop("title", None)
    schema["properties"]["meta"] = external("Metadata")
    schema["required"] = sorted(set(schema.get("required", [])) | {"kind", "targets"})
    schema["properties"]["kind"] = {"const": name}
    schema["title"] = {"jiptl": "Joint Integrated Prioritized Target List (JIPTL)", "tst": "Time-Sensitive Targets (TST)"}[name]
    schema.pop("description", None)
    definitions = schema["$defs"]
    definitions.pop("DataSourceMeta", None)
    if name == "jiptl":
        entry = definitions["JPITLEntry"]
        keep(entry, JIPTL_FIELDS)
        entry["properties"]["component_tasked"]["enum"] = list(JOINT_COMPONENTS)
    else:
        entry = definitions["TSTEntry"]
        keep(entry, TST_FIELDS)
        for field in ("engagement_authority", "expiration_criteria"):
            # The source text refers to TST-1 tiers and DTG strings, which this contract does not use.
            entry["properties"][field].pop("description", None)
        entry["properties"].update({
            "expected_locations": {"type": "array", "items": obj({
                "name": text(), "position": external("GeoPoint"), "mgrs": text()}, ("position",))},
            "activity_window": external("Window"),
            "priority": {"type": "integer", "minimum": 1},
            "category": text(),
        })
