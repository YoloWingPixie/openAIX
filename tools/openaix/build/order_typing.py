"""Typed fields for the target lists and the resource catalogue that earlier held free text.

- TST and JIPTL entries refer to the resource-catalogue target, name their engagement authority as an
  agency and list the authorized engagement means as a weapon system or aircraft type with SCL and store references. Both
  documents can link a resource catalogue with `resources_ref` so that these references resolve.
- A report definition names its recipient agency and its channel; the transmission medium and the
  classification are enumerated values.
- Times in threat and last-known-position records use the shared DateTime primitive.
Descriptions come from describe/tables/ato.py and describe/tables/orders.py.
"""

from openaix.sim.bindings import attach_policy

REPORT_MEDIA = ("voice", "datalink", "chat", "message", "debrief")
# Radar types of the DCS F-16C Early Access Guide, Appendix B (ALIC codes and RWR symbols).
RADAR_ROLES = ("early_warning", "surveillance", "target_acquisition", "target_tracking", "target_illumination",
               "fire_control", "ranging", "continuous_wave_acquisition", "search_and_tracking")
EMITTER_STATUS = ("active", "silent", "suspected", "destroyed")
MOBILITY = ("fixed", "mobile", "relocatable")
# Air defence measures that an emitter can own: missile engagement zones, missile arcs and the other
# air defence measures of the catalogue.
EMITTER_MEASURES = ("MEZ", "MISARC", "SAMEZ", "FEZ", "JEZ", "WFZ")


def type_orders(artifacts, common):
    def c(name):
        return {"$ref": common + "#/$defs/" + name}

    def ident(collection):
        return c("Identifier") | {"x-catalog": collection}

    def obj(properties, required=()):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required)}

    means = obj({"system": {"type": "string", "minLength": 1}, "scl": ident("scls"), "store": ident("stores")}, ("system",))
    for name, entry in (("tst", "TSTEntry"), ("jiptl", "JIPTLTarget")):
        schema = artifacts["schemas/" + name + ".schema.json"]
        schema["properties"]["resources_ref"] = c("ResourceRef")
        schema["$defs"]["EngagementMeans"] = means
        fields = schema["$defs"][entry]["properties"]
        fields["target"] = ident("targets")
        fields["authorized_engagement_means"] = {"type": "array", "items": {"$ref": "#/$defs/EngagementMeans"}}
    tst = artifacts["schemas/tst.schema.json"]["$defs"]["TSTEntry"]["properties"]
    tst["engagement_authority"] = ident("agencies")
    tst["expires_at"] = c("DateTime")

    resources = artifacts["schemas/resources.schema.json"]["$defs"]
    report = resources["ReportDefinition"]["properties"]
    report["recipient"] = ident("agencies")
    report["channel"] = ident("channels")
    report["medium"] = {"enum": list(REPORT_MEDIA)}
    report["classification"] = c("ClassificationLevel")
    for name in ("Threat", "LastKnownPosition"):
        resources[name]["properties"]["as_of"] = c("DateTime")

    # Emitters: air defence radars and the systems they belong to, with a threat ring.
    text = {"type": "string", "minLength": 1}
    length = c("Length")
    emitter = obj({
        "id": c("Identifier"), "name": dict(text), "system_id": dict(text), "reporting_name": dict(text),
        "native_designation": dict(text), "radar_reporting_name": dict(text), "radar_system_id": dict(text),
        "radar_roles": {"type": "array", "items": {"enum": list(RADAR_ROLES)}, "uniqueItems": True},
        "rwr_symbol": dict(text),
        "position": c("GeoPoint"), "status": {"enum": list(EMITTER_STATUS)}, "last_seen": c("DateTime"),
        "mobility": {"enum": list(MOBILITY)}, "side": c("Coalition"),
        "max_engagement_range": dict(length), "min_engagement_range": dict(length), "detection_range": dict(length),
        "engagement_floor": c("VerticalLimit"), "engagement_ceiling": c("VerticalLimit"),
        "measures": {"type": "array", "uniqueItems": True,
                     "items": c("ControlMeasureSelection") | {"x-measure-kinds": list(EMITTER_MEASURES)}},
        "remarks": dict(text),
    }, ("id", "name", "system_id", "mobility", "max_engagement_range"))
    resources["Emitter"] = emitter
    attach_policy(emitter, common, "emitter", "emitter")
    # An emitter without a position has a simulator object that gives it.
    emitter["anyOf"] = [{"required": ["position"]}, {"required": ["extensions"], "properties": {"extensions": {"required": ["sim"]}}}]
    data = resources["ResourceData"]["properties"]
    data["emitters"] = {"type": "object", "additionalProperties": {"$ref": "#/$defs/Emitter"}, "propertyNames": c("Identifier")}
    resources["Threat"]["properties"]["emitters"] = {"type": "array", "uniqueItems": True, "items": ident("emitters")}
