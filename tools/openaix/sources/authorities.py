import json

from openaix import ROOT


def load_authorities():
    """The bibliography: every first-party publication cited by catalogues and inventories."""
    return json.loads((ROOT / "sources/authorities.json").read_text())
