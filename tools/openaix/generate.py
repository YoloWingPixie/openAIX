"""Generate openAIX schemas, catalogues and curated examples.

This module only orchestrates. Each area owns its builder:
build/common.py (shared primitives), build/convert.py (imported models), build/measures.py,
build/orders.py, build/navigation.py with the KDEN seed data (examples/kden.py) and examples/pairs.py
(the minimal and maximal example of each schema).
"""
import argparse
import json

from openaix import ROOT
from openaix.build.common import BASE, COMMON, DIALECT, VERSION, common_schema, trim_definitions
from openaix.build.convert import load_model, relax_requiredness
from openaix.build.measures import (bound_measure_example, build_measures, catalogue, extend_area_geometry,
                                    seed_measure_examples)
from openaix.build.navigation import build_navigation
from openaix.build.orders import enrich_orders, load_documents, order_examples, order_schemas
from openaix.build.spatial import models as spatial_models
from openaix.build.targeting import normalize_targeting
from openaix.describe.resolve import describe_artifacts
from openaix.examples.kden import kden_examples
from openaix.examples.pairs import build_pairs
from openaix.sim.bindings import attach_bindings


GENERATED = ("schemas", "catalogues", "examples")


def generated_paths():
    """Every file in the generated folders; each one is a build artifact."""
    return {path.relative_to(ROOT).as_posix() for folder in GENERATED for path in (ROOT / folder).rglob("*.json")}


def build():
    source = load_model("ato-0.2")
    documents = load_documents()
    cat = catalogue()
    common = common_schema(source)
    artifacts = {"catalogues/control-measures.json": cat, "schemas/common.schema.json": common}
    artifacts.update(order_schemas(source, documents))
    artifacts.update(seed_measure_examples(cat))
    order_examples(artifacts)
    spatial = spatial_models(BASE, VERSION, DIALECT, COMMON)
    navigation, navigation_models = build_navigation(kden_examples(), spatial, BASE, VERSION, COMMON)
    artifacts.update(navigation)
    spatial.update(navigation_models)
    build_measures(artifacts, cat, common, spatial)
    for name, schema in list(artifacts.items()):
        if name.startswith("schemas/") and name != "schemas/common.schema.json":
            schema = normalize_targeting(schema, COMMON)
            artifacts[name] = schema
            trim_definitions(schema)
    relax_requiredness(artifacts)
    attach_bindings(artifacts, COMMON)
    enrich_orders(artifacts)
    for path, document in artifacts.items():
        if path.startswith("schemas/"):
            extend_area_geometry(document)
    bound_measure_example(artifacts)
    describe_artifacts(artifacts)
    artifacts.update(build_pairs(artifacts, VERSION))
    return artifacts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build()
    obsolete = generated_paths() - artifacts.keys()
    if args.check and obsolete:
        raise SystemExit("obsolete generated artifacts: " + ", ".join(sorted(obsolete)))
    for name, value in artifacts.items():
        encoded = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_text() != encoded:
                raise SystemExit("stale generated artifact: " + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(encoded)
    if not args.check:
        for name in sorted(obsolete):
            (ROOT / name).unlink(missing_ok=True)
    print(f"{'Checked' if args.check else 'Wrote'} {len(artifacts)} artifacts: {len(artifacts['catalogues/control-measures.json']['types'])} measure types and 12 source tasking families.")
