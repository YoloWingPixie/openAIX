"""Measure catalogue, measure schemas, the ControlMeasure union and measure examples.

The catalogue lists real NATO and doctrinal codes only (sources/measure-definitions.json). Several codes
share one contract (volume, route, line, area) and are told apart by `type`; codes that are represented
by Point, Airspace, Airway or the MEZ contract carry a `projection` instead.
"""
from copy import deepcopy

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from openaix.build.airspace_types import TYPES as AIRSPACE_TYPES
from openaix.build.common import (BASE, COMMON, DIALECT, GEOJSON_SHAPES, GEOMETRY_NAMES, VERSION, external,
                                  geometry_example)
from openaix.build.spatial import COUNTRY_CODE, coordination_fields, root_fields
from openaix.describe import templates as d
from openaix.describe.resolve import schema_description
from openaix.describe.tables.common import (AIRSPACE_TYPE_CODES, AIRSPACE_TYPES_DESCRIPTION, MEASURE_SOURCE,
                                            airspace_type_note, airspace_type_source, measure_aliases,
                                            measure_definition, measure_note, measure_text, measure_type_field)
from openaix.examples.measures import measures as authored_examples


SHARED_CODES = {
    "volume": ("AARA", "ACCA", "AEWA", "ACAR", "CBA", "DZ", "EC", "FACA", "HIDACZ", "LZ", "NFZ", "PZ", "RECCE", "ROZ",
               "SSMS", "TRA", "TSA", "TRNG", "UAA", "ADIZ", "BDZ", "CADA", "FEZ", "WFZ", "CCZONE", "COZ", "SAFES", "SCZ",
               "ALTRV", "RCA", "BZ", "JEZ", "ADS"),
    "route": ("AIRRTE", "LLTR", "SAAFR", "SC", "TMRR", "TC", "TR", "SL", "APPCOR", "MRR", "AIRCOR", "VFRRTE"),
    "line": ("FEBA", "FLOT", "IFFON", "IFFOFF", "PL", "BOUNDARY", "LOA", "LD", "LC"),
    "fire-support-line": ("FSCL", "CFL", "RFL", "BCL"),
    "area": ("AOA", "EA", "NFA", "RFA", "FFA", "OBJ", "BP", "AA", "NAI", "TAI", "FSA"),
    "cl": ("CL", "CA"),
}
SINGLE_CODES = {"aor": "AOR", "kb": "KB", "mez": "MEZ", "tl": "TL", "aca": "ACA", "isr": "ISR", "misarc": "MISARC"}
# Route codes that doctrine defines as corridors of defined dimensions: a centreline alone is not enough.
CORRIDOR_CODES = ("LLTR", "SC", "TMRR", "TC", "TR", "SL", "APPCOR", "MRR", "AIRCOR")
TITLES = {"volume": "Airspace coordination volume", "route": "Air route or corridor", "line": "Coordination line", "fire-support-line": "Fire support line",
          "area": "Fire support or manoeuvre area", "aor": "Area of responsibility", "kb": "Kill box", "mez": "Missile engagement zone",
          "cl": "Coordination level or coordinating altitude", "tl": "Traverse level", "aca": "Airspace coordination area",
          "isr": "Identification safety range", "misarc": "Missile arc"}
PROJECTIONS = {
    **{"CLS" + code: ("airspace", {"type": "AIRSPACE", "airspace_type": "Class" + code}) for code in "ABCDEFG"},
    "CTA": ("airspace", {"type": "AIRSPACE", "airspace_type": "CTA"}), "CTZ": ("airspace", {"type": "AIRSPACE", "airspace_type": "CTR"}),
    "TCA": ("airspace", {"type": "AIRSPACE", "airspace_type": "TMA"}), "FIR": ("airspace", {"type": "AIRSPACE", "airspace_type": "FIR"}),
    "DA": ("airspace", {"type": "AIRSPACE", "airspace_type": "Danger"}), "PROHIB": ("airspace", {"type": "AIRSPACE", "airspace_type": "Prohibited"}),
    "RA": ("airspace", {"type": "AIRSPACE", "airspace_type": "Restricted"}),
    "ACP": ("point", {"type": "POINT", "roles": ["control"]}), "CP": ("point", {"type": "POINT", "roles": ["control"]}),
    "IP": ("point", {"type": "POINT", "roles": ["initial"]}), "EG": ("point", {"type": "POINT", "roles": ["gate"]}),
    "HG": ("point", {"type": "POINT", "roles": ["handover"]}), "MG": ("point", {"type": "POINT", "roles": ["marshalling"]}),
    "ISP": ("point", {"type": "POINT", "roles": ["identification_safety"]}), "BULLSEYE": ("point", {"type": "POINT", "roles": ["bullseye"]}),
    "TRP": ("point", {"type": "POINT", "roles": ["target_reference"]}),
    "FSS": ("point", {"type": "POINT", "roles": ["fire_support_station"]}),
    "ADVRTE": ("airway", {"type": "AIRWAY", "airway_type": "advisory"}), "ARWY": ("airway", {"type": "AIRWAY", "airway_type": "airway"}),
    "NAVRTE": ("airway", {"type": "AIRWAY", "airway_type": "area_navigation"}),
    "ATSRTE": ("airway", {"type": "AIRWAY", "airway_type": "air_traffic_services"}),
    "CDR": ("airway", {"type": "AIRWAY", "airway_type": "conditional"}),
    "SAMEZ": ("mez", {"type": "MEZ"}),
}
PLAIN_SCHEMAS = ("orbit", "airspace", "point", "navaid", "airway", "territory")
# Route codes without a doctrinal altitude block: a published VFR route can have no vertical limits (FAA AIM 3-5-5a).
UNLIMITED_ROUTE_CODES = ("VFRRTE",)
# Affiliations of a territory: the standard identities friend, hostile and neutral of MIL-STD-2525 and APP-6.
AFFILIATIONS = ("friend", "hostile", "neutral")


def schema_id(name):
    return BASE + (name if name in PLAIN_SCHEMAS else "measure-" + name) + ":" + VERSION


def contract_of(code):
    """Name of the contract that carries a catalogue code."""
    if code in PROJECTIONS:
        return PROJECTIONS[code][0]
    for name, codes in SHARED_CODES.items():
        if code in codes:
            return name
    return next(name for name, single in SINGLE_CODES.items() if single == code)


def citation(row):
    result = {"source": row["source"], "locator": row["locator"]}
    if "note" in row:
        result["note"] = measure_note(row["code"])
    if not row["verified"]:
        result["verified"] = False
    if row.get("references"):
        result["references"] = [{key: reference[key] for key in ("source", "locator", "note") if key in reference}
                                for reference in row["references"]]
    return result


def catalogue():
    codes = MEASURE_SOURCE["codes"]
    assigned = set(PROJECTIONS) | {code for group in SHARED_CODES.values() for code in group} | set(SINGLE_CODES.values())
    if assigned != set(codes):
        raise ValueError("catalogue codes and measure contracts differ: " + ", ".join(sorted(assigned ^ set(codes))))
    types = []
    for code in sorted(codes):
        row = measure_definition(code)
        entry = {"code": code, "name": row["name"], "category": row["category"], "schema": schema_id(contract_of(code)),
                 "definition": measure_text(code), "definition_source": citation({**row, "code": code})}
        if code in PROJECTIONS:
            entry["projection"] = deepcopy(PROJECTIONS[code][1])
        if row.get("expansions"):
            # One code, more than one published expansion (SAAFR): each with the source that uses it.
            entry["expansions"] = [{key: item[key] for key in ("name", "usage", "source", "locator")} for item in row["expansions"]]
        types.append(entry)
    aliases = {}
    for name, alias in measure_aliases().items():
        source = {"source": alias["source"], "locator": alias["locator"]}
        if "note" in alias:
            source["note"] = d.statement(alias["note"])
        aliases[name] = {"code": alias["code"], "name": alias["name"], "values": deepcopy(alias["values"]), "definition_source": source}
    return {"schema_version": VERSION, "types": types, "aliases": aliases}


def build_contracts():
    def ref(name, catalogue=None):
        result = {"$ref": COMMON + "#/$defs/" + name}
        if catalogue:
            result["x-catalog"] = catalogue
        return result

    def texts():
        return {"type": "array", "items": {"type": "string", "minLength": 1}}

    def text():
        return {"type": "string", "minLength": 1}

    def geometry(*kinds):
        return {"oneOf": [ref("Geometry_" + kind) for kind in kinds]} if len(kinds) > 1 else ref("Geometry_" + kinds[0])

    root, coordination = root_fields(COMMON), coordination_fields(COMMON)
    components = {"type": "array", "minItems": 1, "items": ref("AirspaceComponent")}
    authority = {"establishing_authority": ref("Identifier", "agencies"), "coordination_instructions": texts()}
    single = {name: {"const": code} for name, code in SINGLE_CODES.items()}
    bodies = {
        "volume": ({**coordination, "components": components}, ["components"], []),
        "route": ({**coordination, "geometry": geometry("line", "corridor", "path"), "altitude": ref("AltitudeBlock"),
                   "vertices": {"type": "array", "minItems": 1, "items": {
                       "type": "object", "additionalProperties": False,
                       "properties": {"index": {"type": "integer", "minimum": 0}, "name": text(), "point": ref("Identifier", "control_measures")},
                       "required": ["index"], "anyOf": [{"required": ["name"]}, {"required": ["point"]}]}},
                   "joins": {"type": "array", "minItems": 1, "items": {
                       "type": "object", "additionalProperties": False,
                       "properties": {"route": ref("Identifier", "control_measures"), "vertex": {"type": "integer", "minimum": 0}},
                       "required": ["route", "vertex"]}},
                   "serves": {"type": "array", "minItems": 1, "items": {
                       "type": "object", "additionalProperties": False,
                       "properties": {"airfield": ref("Identifier", "places"), "runway": ref("RunwayDesignator")},
                       "required": ["airfield", "runway"]}}},
                  ["geometry"],
                  [{"if": {"properties": {"type": {"enum": list(CORRIDOR_CODES)}}, "required": ["type"]},
                    "then": {"properties": {"geometry": ref("Geometry_corridor")}}},
                   {"if": {"properties": {"type": {"enum": list(UNLIMITED_ROUTE_CODES)}}, "required": ["type"]},
                    "else": {"required": ["altitude"]}}]),
        # The hostile side is to the left or to the right of the line, in the order of its points.
        "line": ({"geometry": geometry("line"), "hostile_side": {"enum": ["left", "right"]}, **authority}, ["geometry"], []),
        "fire-support-line": ({"geometry": geometry("line"), **authority}, ["geometry"], []),
        "area": ({"geometry": geometry("polygon", "circle", "polyarc"), **authority, "restrictions": texts()}, ["geometry"],
                 [{"if": {"properties": {"type": {"const": "RFA"}}, "required": ["type"]}, "then": {"required": ["restrictions"]}}]),
        "aor": ({"geometry": geometry("polygon", "circle"), "responsible_agency": ref("Identifier", "agencies"),
                 "gates": {"type": "array", "items": ref("Identifier"), "x-catalog": "control_measures"}}, ["geometry"], []),
        "kb": ({**coordination, "establishing_authority": ref("Identifier", "agencies"), "killbox_kind": {"enum": ["blue", "purple"]},
                "coordinating_altitude": ref("Altitude"), "grid_label": text(), "components": components}, ["killbox_kind", "components"], []),
        "mez": ({**coordination, "mez_kind": {"enum": ["high", "low", "short_range"]}, "components": components}, ["components"], []),
        "cl": ({"geometry": {"allOf": [ref("Geometry_vertical"), {"required": ["level"]}]},
                "responsibility_below": ref("Identifier", "agencies"), "responsibility_above": ref("Identifier", "agencies"),
                "coordination_instructions": texts()}, ["geometry"], []),
        "tl": ({"geometry": {"allOf": [ref("Geometry_vertical"), {"required": ["height", "altitude"]}]},
                "coordination_instructions": texts()}, ["geometry"], []),
        "aca": ({**coordination, "establishing_authority": ref("Identifier", "agencies"), "aca_kind": {"enum": ["formal", "informal"]},
                 "separation": {"enum": ["time", "lateral", "altitude", "combined"]}, "components": components}, ["aca_kind"],
                [{"if": {"properties": {"aca_kind": {"const": "formal"}}, "required": ["aca_kind"]}, "then": {"required": ["components"]},
                  "else": {"required": ["separation"]}}]),
        "isr": ({"reference_force": text(), "reference_position": ref("GeoPoint"), "range": ref("Length"), "geometry": geometry("circle"),
                 "establishing_authority": ref("Identifier", "agencies"), "restrictions": texts(), "coordination_instructions": texts()},
                ["reference_force", "range"], []),
        "misarc": ({"firing_unit": text(), "center": ref("GeoPoint"), "axis": ref("Bearing"),
                    "width_deg": {"type": "number", "exclusiveMinimum": 0, "maximum": 360, "default": 10},
                    "range": ref("Length"), "altitude": ref("AltitudeBlock"), "controlling_agency": ref("Identifier", "agencies"),
                    "restrictions": texts(), "coordination_instructions": texts()}, ["center", "axis", "range"], []),
    }
    schemas = {}
    for name, (properties, required, conditions) in bodies.items():
        kind = measure_type_field(SHARED_CODES[name]) if name in SHARED_CODES else single[name]
        schema = {"$schema": DIALECT, "$id": schema_id(name), "title": TITLES[name], "description": schema_description("measures/" + name),
                  "type": "object", "additionalProperties": False,
                  "properties": {**deepcopy(root), "type": kind, **deepcopy(properties)},
                  "required": ["id", "name", "type", *required, "active"]}
        if conditions:
            schema["allOf"] = conditions
        schemas["schemas/measures/" + name + ".schema.json"] = schema
    schemas["schemas/measures/territory.schema.json"] = territory_contract(root)
    return schemas


def territory_contract(root):
    """Territory: a friendly, hostile or neutral land area with a required shape, optional country codes and optional
    vertical limits. It has no catalogue code."""
    countries = {"type": "array", "minItems": 1, "uniqueItems": True, "items": {"type": "string", "pattern": COUNTRY_CODE}}
    return {"$schema": DIALECT, "$id": schema_id("territory"), "title": "Territory", "description": schema_description("measures/territory"),
            "type": "object", "additionalProperties": False,
            "properties": {**deepcopy(root), "type": {"const": "TERRITORY"}, "affiliation": {"enum": list(AFFILIATIONS)},
                           "geometry": {"oneOf": [external("Geometry_polygon")]}, "countries": countries,
                           "lower_limit": external("VerticalLimit"), "upper_limit": external("VerticalLimit")},
            "required": ["id", "name", "type", "affiliation", "geometry"]}


def seed_measure_examples(cat):
    """Authored OIR measure examples; they do not depend on generated schemas."""
    return {"examples/" + path: value for path, value in authored_examples(VERSION).items()}


def build_measures(artifacts, cat, common, spatial):
    """Measure schemas, the ControlMeasure union in common and the measure catalogues."""
    contracts = build_contracts()
    for name, model in spatial.items():
        contracts["schemas/measures/" + name + ".schema.json"] = model
    artifacts.update(contracts)
    union = [{"$ref": schema["$id"]} for _, schema in sorted(contracts.items())]
    extension = {"type": "object", "additionalProperties": False,
                 "properties": {**root_fields(COMMON), "type": {"type": "string", "pattern": r"^[a-z][a-z0-9-]*(\.[a-z0-9-]+)+$"},
                                "geometry": external("Geometry")},
                 "required": ["name", "type", "geometry", "extensions"]}
    common["$defs"]["ControlMeasure"] = {"oneOf": [*union, extension]}
    artifacts["schemas/control-measure.schema.json"] = {"$schema": DIALECT, "$id": BASE + "control-measure:" + VERSION,
        "title": "Control measure", "allOf": [external("ControlMeasure")], "required": ["id"]}
    artifacts["catalogues/airspace-types.json"] = {"types": AIRSPACE_TYPES,
        "references": ["https://aixm.aero/sites/default/files/imce/AIXM52HTML/AIXM/DataType_CodeAirspaceBaseType.html"],
        "description": AIRSPACE_TYPES_DESCRIPTION, "definition_sources": airspace_type_sources()}


def airspace_type_sources():
    """First-party definition source of each airspace type that has one: its own source row, or the catalogue code that defines it."""
    result = {}
    for name in AIRSPACE_TYPES:
        row = airspace_type_source(name)
        if row is None and name in AIRSPACE_TYPE_CODES:
            code = AIRSPACE_TYPE_CODES[name][0]
            result[name] = {"name": measure_definition(code)["name"], "catalogue_code": code,
                            **citation({"code": code, **measure_definition(code)})}
        if row is None:
            continue
        entry = {"name": row["name"], **citation({key: value for key, value in row.items() if key != "note"})}
        if "note" in row:
            entry["note"] = airspace_type_note(name)
        result[name] = entry
    return result


# Geometries that a contract accepts together with an openAIX shape: the exact DCS rectangle and ellipse with a polygon,
# and the GeoJSON geometry of each shape (build/common.py GEOJSON_SHAPES).
EXTENDED_SHAPES = {"polygon": ("rectangle", "ellipse", "geojson_polygon"), "line": ("geojson_line",), "point": ("geojson_point",)}


def extend_area_geometry(node):
    if isinstance(node, dict):
        for name, child in (node.get("properties") or {}).items():
            # A field that takes one shape becomes a choice, so that it can take the GeoJSON geometry too.
            if isinstance(child, dict) and set(child) <= {"$ref", "description"} and any(
                    child.get("$ref", "").endswith("#/$defs/Geometry_" + shape) for shape in EXTENDED_SHAPES):
                node["properties"][name] = {"oneOf": [{"$ref": child["$ref"]}], **({"description": child["description"]} if "description" in child else {})}
        for keyword in ("oneOf", "anyOf"):
            branches = node.get(keyword, [])
            existing = {COMMON + branch["$ref"] if branch.get("$ref", "").startswith("#") else branch.get("$ref") for branch in branches}
            for shape, additions in EXTENDED_SHAPES.items():
                if COMMON + "#/$defs/Geometry_" + shape in existing:
                    for name in additions:
                        reference = COMMON + "#/$defs/Geometry_" + name
                        if reference not in existing:
                            branches.append({"$ref": reference})
                            existing.add(reference)
        for value in node.values():
            extend_area_geometry(value)
    elif isinstance(node, list):
        for value in node:
            extend_area_geometry(value)


def probe_geometries():
    """One example of every common geometry kind, including the exact DCS rectangle and ellipse."""
    result = {kind: geometry_example(kind) for kind in GEOMETRY_NAMES}
    center = {"latitude": 37.1, "longitude": -115.5}
    result["rectangle"] = {"kind": "rectangle", "center": center, "width_m": 2000, "height_m": 1000}
    result["ellipse"] = {"kind": "ellipse", "center": center, "north_radius_m": 1000, "east_radius_m": 500}
    result.update(geojson_probes())
    return result


def geojson_probes():
    """One `geojson` geometry of each GeoJSON type, keyed `geojson:<type>`."""
    a, b, c = [-115.5, 37.1], [-115.4, 36.9], [-115.7, 37.0]
    ring = [a, b, c, a]
    coordinates = {"Point": a, "LineString": [a, b], "Polygon": [ring], "MultiPolygon": [[ring]]}
    return {"geojson:" + name: {"kind": "geojson", "geometry": {"type": name, "coordinates": deepcopy(value)}}
            for types in GEOJSON_SHAPES.values() for name in types for value in (coordinates[name],)}


def with_geometry(document, geometry):
    """A copy of a measure document whose geometry, or each component's geometry, is replaced."""
    result = deepcopy(document)
    if "components" in result:
        for item in result["components"]:
            item["geometry"] = deepcopy(geometry)
            item["operation"] = "add"
        return result, "components/geometry"
    result["geometry"] = deepcopy(geometry)
    return result, "geometry"


def base_document(code, examples, schema):
    """An authored document of the code's contract, retyped to the code (or its projection)."""
    document = next(deepcopy(value) for value in examples if value.get("$schema") == schema["$id"])
    document.update(deepcopy(PROJECTIONS[code][1]) if code in PROJECTIONS else {"type": code})
    if code in PROJECTIONS and PROJECTIONS[code][0] == "airspace":
        document.pop("airspace_class_code", None)
    return document


def derive_geometries(catalogue_document, artifacts):
    """Catalogue geometries are the kinds that the code's own contract accepts (SCHEMA-08)."""
    schemas = {value["$id"]: value for name, value in artifacts.items() if name.startswith("schemas/")}
    registry = Registry().with_resources((identifier, Resource.from_contents(value)) for identifier, value in schemas.items())
    examples = [value for name, value in artifacts.items() if name.startswith("examples/") and isinstance(value, dict) and "$schema" in value]
    probes = probe_geometries()
    for entry in catalogue_document["types"]:
        schema = schemas[entry["schema"]]
        properties = schema["properties"]
        if "geometry" not in properties and "components" not in properties:
            entry.pop("geometries", None)
            continue
        validator = Draft202012Validator(schema, registry=registry)
        base = base_document(entry["code"], examples, schema)
        authored = [base["geometry"]] if "geometry" in base else [item["geometry"] for item in base.get("components", [])]
        accepted, location = [], None
        for kind, geometry in probes.items():
            candidates = [geometry, *(item for item in authored if item["kind"] == kind)]
            for candidate in candidates:
                document, location = with_geometry(base, candidate)
                if validator.is_valid(document):
                    accepted.append(kind)
                    break
        if not accepted:
            raise ValueError("no geometry validates for " + entry["code"])
        entry["geometries"] = accepted
        entry["geometry_path"] = location


def bound_measure_example(artifacts):
    """Late measure step, after every schema is final: derive catalogue geometries from the contracts."""
    derive_geometries(artifacts["catalogues/control-measures.json"], artifacts)
