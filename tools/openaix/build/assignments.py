"""ACO assignment contract: the order's time-bound instruction for one referenced measure.

The ACO owns airspace: which measure is active, for what use, under which controlling agency and
with which control points. Tanker method, TACAN, receivers and surveillance responsibility are
service data owned by the ATO Refueling and AirborneControl taskings (ORDERS-01). Descriptions
come from describe/resolve.py (context "aco.assignments").
"""

# Fields that only make sense for one orbit role. Holding stacks are airspace use, so they stay here.
ROLE_FIELDS = {
    "cap": (),
    "aew": (),
    "refueling": (),
    "holding": ("stack_instructions", "entry_route", "exit_route"),
    "other": (),
}

# Short, doctrinal use categories for filtering assignments (ORDERS-03). openAIX values, not USMTF codes.
USAGES = ("cap", "aar", "aew", "transit", "holding", "fires", "isr", "training")

# An orbit role implies its use; a supplied usage must agree with it.
ROLE_USAGE = {"cap": "cap", "aew": "aew", "refueling": "aar", "holding": "holding"}


def schema(common):
    def ref(name, catalogue=None):
        value = {"$ref": common + "#/$defs/" + name}
        if catalogue:
            value["x-catalog"] = catalogue
        return value

    def texts():
        return {"type": "array", "items": {"type": "string", "minLength": 1}}

    return {
        "type": "object", "additionalProperties": False,
        "properties": {
            "measure": ref("Identifier", "control_measures"),
            "state": {"enum": ["active", "deactivated"]},
            "effective": ref("Window"),
            "usage": {"enum": list(USAGES)},
            "restrictions": texts(),
            "killbox_status": {"enum": ["open", "closed"]},
            "role": {"enum": list(ROLE_FIELDS)},
            "stack_instructions": texts(),
            "entry_route": ref("Identifier", "routes"),
            "exit_route": ref("Identifier", "routes"),
            "extensions": ref("Extensions"),
        },
        "required": ["measure", "state", "effective"],
        "allOf": [{"if": {"anyOf": [{"required": [field]} for field in fields]},
                   "then": {"required": ["role"], "properties": {"role": {"const": role}}}}
                  for role, fields in ROLE_FIELDS.items() if fields],
    }
