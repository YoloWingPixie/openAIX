"""Navigation examples for Denver International (KDEN): FAA CIFP cycle 2610 data with authored scenario data.

The records are curated seed data in sources/kden-navigation.json; generation reads them and does not decode
source data. The authored scenario fields (frequencies, ATIS content, the calm-wind runway, the traffic pattern,
the coalition, the illustrative taxi subgraph and the on-field navigation aid) are plausible for a simulator;
they are not FAA publications, and the airfield extension names them.
"""
import json

from openaix import ROOT

SEED = ROOT / "sources/kden-navigation.json"
PROVENANCE = "FAA CIFP cycle 2610"
# The KDEN examples link to one resource catalogue (examples/resources-kden.json) that holds the airfield, its
# localizer, its instrument procedure and its navigation aid, so that the airfield links resolve offline.
CATALOGUE_REF = {"id": "kden-navigation", "revision": "2610"}
SCENARIO_FIELDS = {"airfield": ("coalition", "frequencies", "atis", "calm_wind_runway", "traffic_pattern", "navaids", "taxi", "extensions"),
                   "navaid": ("airfield",)}
LINKED = ("airfield", "runway", "localizer", "procedure", "msa", "path-point", "navaid")
CATALOGUE_RECORDS = {"places": "airfield", "localizers": "localizer", "instrument_procedures": "procedure", "control_measures": "navaid"}


def kden_examples():
    """Example name -> KDEN navigation record, read from the seed data."""
    return json.loads(SEED.read_text())


def kden_catalogue(documents, version):
    """The KDEN resource catalogue: the records that the KDEN airfield links to, keyed by identifier."""
    resources = {}
    for catalogue, name in CATALOGUE_RECORDS.items():
        record = {key: value for key, value in documents[name].items() if key not in ("$schema", "resources_ref")}
        resources[catalogue] = {record["id"]: record}
    return {"$schema": "urn:openaix:schema:resources:" + version, "kind": "resources", "schema_version": version,
            "meta": {"id": CATALOGUE_REF["id"], "revision": CATALOGUE_REF["revision"],
                     "title": "KDEN navigation records from " + PROVENANCE + ", with authored scenario data"},
            "resources": resources}
