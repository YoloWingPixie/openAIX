"""Load and clean imported opord-builder models, type their quantities and relax source requiredness."""
import re

from openaix.build.common import COMMON, read
from openaix.describe.resolve import typed_field_description


MODELS = ("ato-0.2", "spins", "opord", "frago", "tst", "jpitl")


NULL = {"type": "null"}


def load_model(name):
    """Return one imported source model, cleaned of pydantic and OpenAPI artefacts."""
    if name not in MODELS:
        raise ValueError("unknown imported model: " + name)
    model = read(f"sources/opord-builder/{name}.model.json")
    check_const_dispatch(model)
    return type_quantities(shared_primitives(clean(model)))


DTG_PATTERN = r"^\d{6}Z[A-Z]{3}\d{2}$"
MGRS_PATTERN = r"^[0-9]{1,2}[A-Z]{3}[0-9]{2,10}$|^[A-Z]{2}[0-9]{2,10}$"
LENGTH_SUFFIX = re.compile(r"^(?P<base>.+?)(?:_msl)?_(?P<unit>nm|km|m|ft)$")
FREQUENCY_SUFFIX = re.compile(r"^(?P<base>.+?)_(?:mhz|khz)$")
SPEED_SUFFIX = re.compile(r"^(?P<base>.+?)_kt$")


def typed_name(name):
    """Name and common primitive for one source field whose unit, time or grid format is in its name or pattern.

    Returns None when the field is not converted. Descriptive alternatives such as `dtg_or_cadence`
    or `grid_or_trace` remain text.
    """
    if "_or_" in name:
        return None
    tokens = name.split("_")
    if "dtg" in tokens:
        rest = [token for token in tokens if token != "dtg"]
        if not rest:
            return "date_time", "DateTime"
        return "_".join(rest + (["time"] if tokens[-1] == "dtg" else [])), "DateTime"
    for pattern, primitive in ((FREQUENCY_SUFFIX, "Frequency"), (SPEED_SUFFIX, "Speed")):
        match = pattern.match(name)
        if match:
            return match["base"], primitive
    match = LENGTH_SUFFIX.match(name)
    if match:
        base = match["base"]
        if "altitude" in base:
            return base, "Altitude"
        if "elevation" in base:
            return base, "Elevation"
        return base, "Length"
    return None


def type_quantities(model, log=None):
    """Replace unit-suffixed numbers, DTG text and MGRS grids with the common primitives (SCHEMA-04).

    The conversion is name- and pattern-driven so every imported model is typed the same way:
    - `<x>_nm|_km|_m|_ft` numbers become Length, Altitude (names containing altitude) or Elevation;
      an `altitude_floor_ft`/`altitude_ceiling_ft` pair becomes one `altitude` AltitudeBlock;
    - `<x>_kt` becomes Speed; `<x>_mhz|_khz` becomes Frequency and absorbs a sibling AM/FM `modulation`;
    - DTG text (a `dtg` name token or the DDHHMMZMONYY pattern) becomes DateTime, unless the source
      also admits free-form text, which is ambiguous and stays text;
    - an MGRS-pattern string becomes a GeoPoint plus optional `mgrs` display text beside it.
    `log` collects (definition, source field, new field, primitive) rows.
    """
    log = [] if log is None else log

    def common(name, description=None):
        node = {"$ref": COMMON + "#/$defs/" + name}
        text = typed_field_description(description, name)
        if text:
            node["description"] = text
        return node

    def convert_object(node, owner):
        properties = node["properties"]
        required = list(node.get("required", []))
        result, renamed = {}, {}

        def place(old, new, value, primitive):
            if new in result or (new in properties and new != old):
                raise ValueError(f"{owner}: typed field {new} collides with an existing field")
            result[new] = value
            renamed.setdefault(old, []).append(new)
            log.append((owner, old, new, primitive))

        floors = {name[:-len("_floor_ft")] for name in properties if name.endswith("_floor_ft") and name[:-len("_floor_ft")] + "_ceiling_ft" in properties}
        for name, field in properties.items():
            if not isinstance(field, dict):
                result[name] = field
                continue
            description = field.get("description")
            base = name.removesuffix("_floor_ft").removesuffix("_ceiling_ft")
            if base in floors and name != base:
                if name.endswith("_floor_ft"):
                    place(name, base, common("AltitudeBlock", description), "AltitudeBlock")
                    renamed[base + "_ceiling_ft"] = [base]
                    log.append((owner, base + "_ceiling_ft", base, "AltitudeBlock"))
                continue
            scalar = field.get("type") in ("string", "number", "integer")
            pattern = field.get("pattern")
            typed = typed_name(name) if scalar else None
            if scalar and pattern == MGRS_PATTERN:
                if name == "grid":
                    position, display = "position", "mgrs"
                elif name.endswith("_grid"):
                    position, display = name.removesuffix("grid") + "position", name.removesuffix("grid") + "mgrs"
                else:
                    position, display = name, name + "_mgrs"
                place(name, position, common("GeoPoint", description), "GeoPoint")
                if display in properties or display in result:
                    raise ValueError(f"{owner}: grid display field {display} collides with an existing field")
                result[display] = {"type": "string", "minLength": 1, "description": typed_field_description(description, "MGRS")}
                log.append((owner, name, display, "MGRS display text"))
                continue
            free_form = "free-form" in (description or "")
            if scalar and field.get("type") == "string" and not free_form and (pattern == DTG_PATTERN or (typed and typed[1] == "DateTime")):
                new = typed[0] if typed else name
                place(name, new, common("DateTime", description), "DateTime")
                continue
            if typed and field.get("type") in ("number", "integer") and typed[1] != "DateTime":
                new, primitive = typed
                value = common(primitive, description)
                if primitive == "Frequency" and properties.get("modulation", {}).get("enum") == ["AM", "FM"]:
                    if "modulation" in required:
                        value = {"allOf": [{"$ref": value.pop("$ref")}, {"required": ["modulation"]}], **value}
                    renamed["modulation"] = []
                place(name, new, value, primitive)
                continue
            result[name] = field
        if "modulation" in renamed:
            result.pop("modulation", None)
        node["properties"] = result
        if "required" in node:
            names = []
            for name in required:
                for new in renamed.get(name, [name]):
                    if new not in names:
                        names.append(new)
            node["required"] = names

    def visit(node, owner):
        if isinstance(node, list):
            for item in node:
                visit(item, owner)
            return
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key == "$defs":
                for name, definition in value.items():
                    visit(definition, name)
            elif key == "properties" and isinstance(value, dict):
                for child in value.values():
                    visit(child, owner)
            else:
                visit(value, owner)
        if isinstance(node.get("properties"), dict):
            convert_object(node, owner)

    visit(model, "(root)")
    return model


def shared_primitives(node):
    """Point imported fields that hold a shared coded value at its common primitive."""
    if isinstance(node, list):
        return [shared_primitives(item) for item in node]
    if not isinstance(node, dict):
        return node
    result = {key: shared_primitives(value) for key, value in node.items()}
    properties = result.get("properties")
    if isinstance(properties, dict) and properties.get("laser_code", {}).get("type") == "string":
        field = properties["laser_code"]
        properties["laser_code"] = {"$ref": COMMON + "#/$defs/LaserCode", **{key: value for key, value in field.items() if key in ("description", "title")}}
    return result


def clean(node, key=None):
    """Remove artefacts that JSON Schema ignores or that make optional fields nullable.

    - `discriminator` is OpenAPI-only; dispatch relies on oneOf branches with a const kind.
    - `anyOf: [T, {type: null}]` becomes T: an optional field is absent, never null.
    - `default: null` and property titles that only repeat the property name are dropped.
    `key` is the property name when `node` is a property schema.
    """
    if isinstance(node, list):
        return [clean(item) for item in node]
    if not isinstance(node, dict):
        return node
    result = {}
    for name, value in node.items():
        if name == "discriminator" or (name == "default" and value is None):
            continue
        if name in ("properties", "$defs", "patternProperties") and isinstance(value, dict):
            result[name] = {child: clean(schema, child if name == "properties" else None) for child, schema in value.items()}
        else:
            result[name] = clean(value)
    branches = result.get("anyOf")
    if isinstance(branches, list) and NULL in branches:
        remaining = [branch for branch in branches if branch != NULL]
        del result["anyOf"]
        if len(remaining) == 1:
            result = {**remaining[0], **result}
        else:
            result["anyOf"] = remaining
    title = result.get("title")
    if key is not None and isinstance(title, str) and title.lower().replace(" ", "_") == key.lower():
        del result["title"]
    return result


def check_const_dispatch(model):
    """Every discriminated union must dispatch through oneOf branches whose kind property is a required const."""
    definitions = model.get("$defs", {})

    def visit(node, path):
        if isinstance(node, dict):
            if "discriminator" in node:
                field = node["discriminator"]["propertyName"]
                for branch in node["oneOf"]:
                    target = definitions[branch["$ref"].removeprefix("#/$defs/")] if "$ref" in branch else branch
                    if "const" not in target.get("properties", {}).get(field, {}) or field not in target.get("required", []):
                        raise ValueError(path + ": union branch lacks a required const " + field)
            for name, child in node.items():
                visit(child, path + "/" + name)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                visit(child, path + "/" + str(index))

    visit(model, "")


# Flight-simulation requiredness policy. Imported models require
# publication and administrative fields that must not block partial mission authoring.
ROOT_REQUIRED = {
    "ato": "kind period missions", "aco": "kind period assignments", "resources": "kind resources",
    "jiptl": "kind targets", "tst": "kind targets",
    "c2-agency": "id kind callsign role", "fac": "id kind callsign role", "scl": "id kind name aircraft_type",
    "airfield": "id kind name", "runway": "id kind name designator length ends",
    "localizer": "id kind name frequency course position",
    "msa": "id kind name center sectors", "grid-mora": "id kind name cells",
    "path-point": "id kind name landing_threshold_point flight_path_alignment_point glide_path_angle_deg threshold_crossing_height",
}

MINIMUM = {
    "Metadata": "id", "Activity": "id kind", "Aimpoint": "position", "AirborneControl": "kind area",
    "AirborneLaunch": "kind position altitude", "AlertLaunch": "kind departure", "AttackAssignment": "id target",
    "CargoItem": "name quantity", "CollectionRequirement": "id information_required area requirement_number indicator",
    "Contingency": "condition action", "CustomTask": "kind name assigned_actions",
    "ElectromagneticTask": "kind area assigned_effect", "Escort": "kind supported_missions",
    "Flight": "id callsign aircraft_type count", "Mission": "id mission_number tasking flights", "Package": "id name",
    "Patrol": "kind area", "OnCallCAS": "kind area", "PersonnelRecovery": "kind incident search_area",
    "PreplannedAttack": "kind role assignments", "Reconnaissance": "kind requirements", "Refueling": "kind area method",
    "Training": "kind events", "Transport": "kind pickup destination", "ReceiverSlot": "flight",
    "SelfControl": "kind responsible_flight", "SupportLink": "role flight", "SCLAlternative": "scl condition",
    "ScheduledLaunch": "kind departure", "OnOrder": "kind condition", "AreaTarget": "kind name area",
    "FixedTarget": "kind name aimpoints", "MobileTarget": "kind name", "RoutePoint": "id position",
    "Channel": "name frequency", "RadioAssignment": "channel", "Threat": "kind name",
    "LastKnownPosition": "position", "ControlMeasure": "name type grid_or_trace",
    "JIPTLTarget": "target_number priority_rank", "ReportDefinition": "name", "TSTEntry": "tst_number",
    "Attachment": "kind path",
}


def relax_requiredness(artifacts):
    """Apply the flight-simulation requiredness policy to generated schemas."""

    def visit(node, path, owner, root_name):
        if isinstance(node, dict):
            original = node.get("required", [])[:]
            keep = None
            if path == "" and root_name in ROOT_REQUIRED:
                keep = set(ROOT_REQUIRED[root_name].split())
            elif path.startswith("/$defs/") and path.count("/") == 2 and owner in MINIMUM:
                keep = set(MINIMUM[owner].split())
            if keep is not None and original:
                node["required"] = [name for name in original if name in keep]
            for key, value in node.items():
                if key == "$defs":
                    for name, definition in value.items():
                        visit(definition, path + "/$defs/" + name, name, root_name)
                else:
                    visit(value, path + "/" + key, owner, root_name)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, path + "/" + str(index), owner, root_name)

    for path, schema in sorted(artifacts.items()):
        if path.startswith("schemas/"):
            name = path.removeprefix("schemas/").removesuffix(".schema.json")
            visit(schema, "", name, name)
