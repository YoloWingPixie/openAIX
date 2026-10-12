"""Notice to air missions (NOTAM): the basic items of the ICAO NOTAM format that a planner writes ahead of time.

ICAO Annex 15 and the PANS-AIM (Doc 10066) give the NOTAM format; ICAO Doc 8126 gives the NOTAM Code. The record
keeps the NOTAM number (series, number and year), item A (the location), the NOTAM Code of item Q, items B and C
(the effective window), item E (the text) and items F and G (the lower and upper limits). The runways, navigation
aids, airspace and procedures that the NOTAM is about are typed references in `affects`. Descriptions come from
describe/tables/navigation.py.
"""

# The NOTAM Code: the letter Q, two letters for the subject and two letters for its condition (ICAO Doc 8126).
NOTAM_CODE = r"^Q[A-Z]{4}$"
NOTAM_SERIES = r"^[A-Z]$"


def schema(base, version, common, airfield_reference):
    def ref(name, catalogue=None):
        node = {"$ref": common + "#/$defs/" + name}
        if catalogue:
            node["x-catalog"] = catalogue
        return node

    def obj(properties, required=()):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(required)}

    def text():
        return {"type": "string", "minLength": 1}

    number = obj({"series": {"type": "string", "pattern": NOTAM_SERIES}, "number": {"type": "integer", "minimum": 1, "maximum": 9999},
                  "year": {"type": "integer", "minimum": 1900, "maximum": 9999}}, ("series", "number", "year"))
    runway = obj({"kind": {"const": "runway"}, "designator": ref("RunwayDesignator")}, ("kind", "designator"))
    procedure = obj({"kind": {"const": "instrument_procedure"}, "id": ref("Identifier", "instrument_procedures")}, ("kind", "id"))
    affected = {"oneOf": [ref("ControlMeasureSelection"), {"$ref": "#/$defs/RunwaySelection"}, {"$ref": "#/$defs/ProcedureSelection"}]}
    record = obj({
        "$schema": text(), "id": ref("Identifier"), "kind": {"const": "notam"}, "number": {"$ref": "#/$defs/NotamNumber"},
        "location": airfield_reference, "code": {"type": "string", "pattern": NOTAM_CODE}, "effective": ref("Window"),
        "text": text(), "lower": ref("VerticalLimit"), "upper": ref("VerticalLimit"),
        "affects": {"type": "array", "minItems": 1, "items": affected},
        "resources_ref": ref("ResourceRef"), "extensions": ref("Extensions"),
    }, ("id", "kind", "number", "location", "code", "effective", "text"))
    return {**record, "$defs": {"NotamNumber": number, "RunwaySelection": runway, "ProcedureSelection": procedure}}
