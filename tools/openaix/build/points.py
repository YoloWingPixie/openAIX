from copy import deepcopy

from openaix.describe.resolve import schema_description


POINT_ROLES = ("control", "initial", "ingress", "egress", "gate", "handover",
               "marshalling", "identification_safety", "bullseye", "fix", "target_reference", "fire_support_station")


def point_location(common):
    return {"type": "object",
        "properties": {
            "position": {"$ref": common + "#/$defs/GeoPoint"},
            "position_description": {"type": "string", "minLength": 1},
        }, "anyOf": [{"required": ["position"]}, {"required": ["position_description"]}]}


def apply_point_location(schema, common, required=True):
    result = deepcopy(schema)
    for name in point_location(common)["properties"]:
        result["properties"][name] = {"$ref": common + "#/$defs/PointLocation/properties/" + name}
    if result.get("anyOf") == point_location(common)["anyOf"]:
        result.pop("anyOf")
    if required:
        condition = {"$ref": common + "#/$defs/PointLocation"}
        conditions = result.setdefault("allOf", [])
        if condition not in conditions:
            conditions.append(condition)
    return result


def control_fields(common):
    """Contact, handover and gateway references a control point may carry."""
    def ref(name, catalogue=None):
        result = {"$ref": common + "#/$defs/" + name}
        if catalogue:
            result["x-catalog"] = catalogue
        return result

    return {"contact_agency": ref("Identifier", "agencies"), "handover_agency": ref("Identifier", "agencies"),
            "channels": {"type": "array", "items": ref("Identifier"), "x-catalog": "channels"},
            "aor": ref("Identifier", "control_measures"), "route": ref("Identifier", "routes"),
            "instructions": {"type": "array", "items": {"type": "string", "minLength": 1}}}


def build_point(skeleton, base, version, common):
    """The Point contract: a measure root plus roles, a location and control references.

    Catalogue codes such as CP or IP are not instance types; the catalogue projects them to
    `type: POINT` with the matching role. Category and source labels are not instance fields.
    """
    schema = apply_point_location(skeleton, common)
    schema.update({"$id": base + "point:" + version, "title": "Navigation or control point", "description": schema_description("measures/point")})
    properties = schema["properties"]
    schema["required"] = ["id", "name", "type", "roles", "active"]
    properties["type"] = {"const": "POINT"}
    properties["roles"] = {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"enum": list(POINT_ROLES)}}
    for name, node in control_fields(common).items():
        properties.setdefault(name, node)
    return schema
