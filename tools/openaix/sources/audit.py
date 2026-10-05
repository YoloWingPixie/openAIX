"""Check that catalogue definition sources resolve to a cited first-party authority."""
import argparse
import json

from openaix import ROOT
from openaix.build.planning_fields import validate_planning_inventory
from openaix.sources.authorities import load_authorities


CITATION_FIELDS = ("publisher", "title", "edition", "url")
REFERENCE_FIELDS = ("publisher", "title", "edition")


def reference_errors(owner, references, authorities):
    """Corroborating references name a known authority with publisher, title and edition, and a locator.

    A reference may cite a publication without a recorded URL; a primary definition source may not.
    """
    errors = []
    for reference in references or []:
        authority = authorities.get(reference.get("source"))
        if authority is None:
            errors.append(owner + ": reference to unknown authority " + repr(reference.get("source")))
        elif not all(authority.get(field) for field in REFERENCE_FIELDS):
            errors.append(owner + ": reference authority " + reference["source"] + " lacks publisher, title or edition")
        if not reference.get("locator"):
            errors.append(owner + ": reference to " + repr(reference.get("source")) + " has no locator")
    return errors


def citation_errors(catalogue, authorities, require_all=False):
    """Return one message per catalogue entry whose definition source is missing or incomplete."""
    errors = []
    for entry in catalogue["types"]:
        citation = entry.get("definition_source")
        if citation is None:
            if require_all:
                errors.append(entry["code"] + ": no definition source")
            continue
        authority = authorities.get(citation.get("source"))
        if authority is None:
            errors.append(entry["code"] + ": unknown authority " + repr(citation.get("source")))
        elif not all(authority.get(field) for field in CITATION_FIELDS):
            errors.append(entry["code"] + ": authority " + citation["source"] + " lacks publisher, title, edition or url")
        if not citation.get("locator"):
            errors.append(entry["code"] + ": definition source has no locator")
        errors.extend(reference_errors(entry["code"], citation.get("references"), authorities))
    return errors


def leg_type_errors(table, authorities):
    """Each procedure leg type cites a first-party source with a locator, keeps its published wording and is verified."""
    errors = []
    for code, row in table["codes"].items():
        owner = "leg type " + code
        authority = authorities.get(row.get("source"))
        if authority is None:
            errors.append(owner + ": unknown authority " + repr(row.get("source")))
        elif not all(authority.get(field) for field in CITATION_FIELDS):
            errors.append(owner + ": authority " + row["source"] + " lacks publisher, title, edition or url")
        for field in ("leg_type", "name", "locator", "source_text", "definition"):
            if not row.get(field):
                errors.append(owner + ": no " + field)
        if row.get("verified") is not True:
            errors.append(owner + ": not verified against its source")
        errors.extend(reference_errors(owner, row.get("references"), authorities))
    return errors


def source_reference_errors(measures, inventory, authorities):
    """References recorded in the source tables, checked before the catalogue is generated."""
    errors = []
    for code, row in measures["codes"].items():
        errors.extend(reference_errors(code, row.get("references"), authorities))
        errors.extend(reference_errors(code + " expansion", row.get("expansions"), authorities))
    for name, row in measures.get("airspace_types", {}).items():
        errors.extend(reference_errors("airspace type " + name, row.get("references"), authorities))
    for section in ("documents", "mission_type_mapping", "tasking_families"):
        for row in inventory.get(section, []):
            owner = section + " " + str(row.get("schema") or row.get("mission_type") or row.get("kind"))
            errors.extend(reference_errors(owner, row.get("references"), authorities))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-all", action="store_true", help="Fail when any catalogue entry has no definition source.")
    args = parser.parse_args()
    authorities = load_authorities()
    inventory = json.loads((ROOT / "sources/planning-field-inventory.json").read_text())
    validate_planning_inventory(inventory, authorities)
    measures = json.loads((ROOT / "sources/measure-definitions.json").read_text())
    catalogue = json.loads((ROOT / "catalogues/control-measures.json").read_text())
    errors = source_reference_errors(measures, inventory, authorities)
    errors.extend(citation_errors(catalogue, authorities, args.require_all))
    leg_types = json.loads((ROOT / "sources/leg-type-definitions.json").read_text())
    errors.extend(leg_type_errors(leg_types, authorities))
    for name, alias in catalogue.get("aliases", {}).items():
        errors.extend(citation_errors({"types": [{"code": name, **alias}]}, authorities, True))
    airspace = json.loads((ROOT / "catalogues/airspace-types.json").read_text())
    for name, source in airspace.get("definition_sources", {}).items():
        errors.extend(citation_errors({"types": [{"code": "airspace type " + name, "definition_source": source}]}, authorities, True))
    for name in measures.get("airspace_types", {}):
        if name not in airspace.get("definition_sources", {}):
            errors.append("airspace type " + name + ": source row not published in catalogues/airspace-types.json")
    if errors:
        raise SystemExit("\n".join(errors))
    cited = sum("definition_source" in entry for entry in catalogue["types"])
    unverified = sorted(entry["code"] for entry in catalogue["types"] if entry.get("definition_source", {}).get("verified") is False)
    print(f"Checked {len(catalogue['types'])} catalogue entries: {cited} cite a resolvable first-party definition source; "
          f"{len(catalogue.get('aliases', {}))} aliases and {len(airspace.get('definition_sources', {}))} airspace types also cite one."
          + f" {len(leg_types['codes'])} leg types cite a verified first-party source."
          + (" Citations not re-read: " + ", ".join(unverified) + "." if unverified else ""))
