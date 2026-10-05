from openaix.describe.tables.common import AIRSPACE_TYPE_VALUES


NAMES = (*("Class" + code for code in "ABCDEFG"), "MTA", "MOA", "CTA", "CTR", "TMA", "FIR", "UIR", "ATZ", "ADIZ", "TRA", "TSA",
         "ROZ", "Restricted", "Prohibited", "Danger", "Warning", "Alert", "Sector",
         # Civil and special use airspace with a first-party source in sources/measure-definitions.json `airspace_types`.
         "ATCAA", "CFA", "NSA", "TFR", "SFRA", "TRSA", "ModeCVeil", "RMZ", "TMZ", "Other")
TYPES = {name: AIRSPACE_TYPE_VALUES[name] for name in NAMES}


def schema():
    return {"type": "string", "enum": list(TYPES), "x-enum-descriptions": TYPES.copy()}
