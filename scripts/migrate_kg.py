#!/usr/bin/env python3
"""Migrate the legacy combined_doping_data.json KG to PSPRelationship format.

Reads the legacy KG from the 26KDD data directory and converts each
causal_relationship entry into the new PSPRelationship schema defined
in aria.types. Outputs two files:

  1. aria_2d_kg_v1.json  -- full KG with all relationships
  2. aria_2d_kg_tiny.json -- curated ~6 relationships covering all PSP types

Usage:
    python scripts/migrate_kg.py
    python scripts/migrate_kg.py --source /path/to/combined_doping_data.json
    python scripts/migrate_kg.py --output-dir /path/to/output
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure the aria package is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aria.types import PSPRelationship, _infer_psp_type, _infer_relation, _parse_confidence, _infer_material

logger = logging.getLogger(__name__)

DEFAULT_SOURCE = Path(
    "/Users/alina/Library/CloudStorage/OneDrive-JohnsHopkins/"
    "Research/26ARIA/26KDD/data/KG/outputs/combined_doping_data.json"
)

# Extended material patterns for source file matching.
# The built-in _infer_material only handles a few abbreviations;
# this map covers materials that appear in the KG source file names.
_EXTENDED_MATERIAL_PATTERNS: Dict[str, str] = {
    # TMDs
    "wte2": "WTe2",
    "mose2": "MoSe2",
    "wse2": "WSe2",
    "mote2": "MoTe2",
    "mos2": "MoS2",
    "ws2": "WS2",
    # Other 2D
    "graphene": "graphene",
    "silicene": "silicene",
    "germanene": "germanene",
    "hbn": "hBN",
    "bn_": "hBN",
    "boron_nitride": "hBN",
    "black_phosphorus": "black_phosphorus",
    "fe3gete2": "Fe3GeTe2",
    "fe5gete2": "Fe5GeTe2",
    # Topological / magnetic
    "bi2se3": "Bi2Se3",
    "bi2te3": "Bi2Te3",
    "sb2te3": "Sb2Te3",
    "cr2ge2te2": "Cr2Ge2Te2",
    "cri3": "CrI3",
    "crse2": "CrSe2",
    # Metals / substrates
    "cu(111)": "Cu",
    "cu(001)": "Cu",
    "ni_doped": "Ni-doped",
    # Intercalation
    "lithium": "Li-intercalated",
    "li_intercalat": "Li-intercalated",
}


def _infer_material_extended(source_file: str) -> str:
    """Infer material name from source file, with extended pattern matching."""
    # First try the built-in
    result = _infer_material(source_file)
    if result:
        return result
    # Then try extended patterns
    source_lower = source_file.lower()
    for pattern, material in _EXTENDED_MATERIAL_PATTERNS.items():
        if pattern in source_lower:
            return material
    return ""


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------

def convert_legacy_relationships(
    causal_relationships: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert each legacy causal_relationship dict to PSPRelationship format.

    Handles None values in fields gracefully by defaulting to empty strings.
    Also uses extended material inference to capture materials that the
    built-in _infer_material misses.
    """
    converted: List[Dict[str, Any]] = []
    skipped = 0

    for idx, raw in enumerate(causal_relationships):
        cause = (raw.get("cause_parameter") or "").strip()
        effect = (raw.get("effect_on_doping") or "").strip()

        # Skip empty or placeholder values
        if not cause or not effect:
            skipped += 1
            continue
        if "unknown" in cause.lower() or "n/a" in cause.lower():
            skipped += 1
            continue
        if "unknown" in effect.lower() or "n/a" in effect.lower():
            skipped += 1
            continue

        # Build a clean dict for from_legacy, ensuring no None strings.
        # When affected_property is empty/None, use effect_on_doping as the
        # target so that from_legacy correctly populates the target field.
        affected_property = (raw.get("affected_property") or "").strip()
        if not affected_property:
            affected_property = effect

        source_file = raw.get("source_file") or ""
        clean = {
            "cause_parameter": cause,
            "effect_on_doping": effect,
            "affected_property": affected_property,
            "mechanism_quote": raw.get("mechanism_quote") or "",
            "confidence_level": raw.get("confidence_level") or "",
            "source_file": source_file,
            "relationship_id": raw.get("relationship_id") or f"migrated_{idx}",
            "paper_doi": raw.get("paper_doi") or "",
        }

        rel = PSPRelationship.from_legacy(clean)

        # Override material with extended inference if built-in returned empty
        if not rel.material:
            inferred = _infer_material_extended(source_file)
            if inferred:
                rel = PSPRelationship(
                    source=rel.source,
                    relation=rel.relation,
                    target=rel.target,
                    psp_type=rel.psp_type,
                    material=inferred,
                    evidence_text=rel.evidence_text,
                    paper_doi=rel.paper_doi,
                    confidence=rel.confidence,
                    curation=rel.curation,
                    relationship_id=rel.relationship_id,
                )

        entry = rel.to_dict()
        # Preserve legacy fields for backward compatibility
        entry["legacy_cause_parameter"] = cause
        entry["legacy_effect_on_doping"] = effect
        entry["legacy_confidence_level"] = clean["confidence_level"]
        converted.append(entry)

    logger.info(
        "Converted %d relationships (%d skipped as empty/placeholder)",
        len(converted), skipped,
    )
    return converted


def select_tiny_kg(relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hand-pick ~6 representative relationships for the tiny example KG.

    Selection criteria:
      - Cover Processing->Structure, Structure->Property, and Processing->Property
      - Include diverse materials (MoS2, graphene, WTe2, MoSe2/WSe2)
      - Prefer relationships with mechanism quotes for richer evidence
      - Include varied confidence levels
    """
    # Categorize by PSP type
    ps_entries = []
    sp_entries = []
    pp_entries = []
    ss_entries = []

    for r in relationships:
        psp = r.get("psp_type", "")
        if psp == "Processing_to_Structure":
            ps_entries.append(r)
        elif psp == "Structure_to_Property":
            sp_entries.append(r)
        elif psp == "Processing_to_Property":
            pp_entries.append(r)
        elif psp == "Structure_to_Structure":
            ss_entries.append(r)

    selected = []

    # Processing -> Structure: 2 entries
    ps1 = _find_by_fields(ps_entries, material="MoS2", has_evidence=True)
    if ps1:
        selected.append(ps1)
    ps2 = _find_by_fields(ps_entries, source_contains="WTe2")
    if ps2:
        selected.append(ps2)

    # Structure -> Property: 2 entries
    sp1 = _find_by_fields(sp_entries, has_evidence=True)
    if sp1:
        selected.append(sp1)
    sp2 = _find_by_fields(sp_entries, source_contains="trion")
    if sp2:
        selected.append(sp2)

    # Processing -> Property: 2 entries
    pp1 = _find_by_fields(pp_entries, material="MoS2", has_evidence=True)
    if pp1:
        selected.append(pp1)
    pp2 = _find_by_fields(pp_entries, source_contains="graphene")
    if pp2:
        selected.append(pp2)

    # Deduplicate by relationship_id
    seen = set()
    unique = []
    for r in selected:
        rid = r.get("relationship_id", "")
        if rid not in seen:
            seen.add(rid)
            unique.append(r)

    return unique


def _find_by_fields(
    entries: List[Dict[str, Any]],
    material: str = "",
    source_contains: str = "",
    has_evidence: bool = False,
) -> Dict[str, Any] | None:
    """Find the first entry matching given field criteria.

    Searches across material, evidence_text, source, and legacy fields
    to handle both the converted PSPRelationship format and its
    backward-compatible legacy fields.
    """
    for entry in entries:
        if material and material.lower() not in entry.get("material", "").lower():
            continue
        combined_text = (
            entry.get("evidence_text", "")
            + " " + entry.get("source", "")
            + " " + entry.get("legacy_cause_parameter", "")
            + " " + entry.get("legacy_effect_on_doping", "")
        ).lower()
        if source_contains and source_contains.lower() not in combined_text:
            continue
        if has_evidence and not entry.get("evidence_text"):
            continue
        return entry
    # Relax criteria progressively
    if has_evidence:
        return _find_by_fields(entries, material=material, source_contains=source_contains, has_evidence=False)
    if material:
        return _find_by_fields(entries, material="", source_contains=source_contains, has_evidence=False)
    if source_contains:
        return _find_by_fields(entries, material=material, source_contains="", has_evidence=False)
    return entries[0] if entries else None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Migrate legacy KG to PSPRelationship format")
    parser.add_argument(
        "--source", type=Path, default=DEFAULT_SOURCE,
        help="Path to legacy combined_doping_data.json",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "data",
        help="Directory for output files",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    source = args.source
    if not source.exists():
        logger.error("Source file not found: %s", source)
        sys.exit(1)

    logger.info("Reading legacy KG from %s", source)
    with open(source, "r", encoding="utf-8") as f:
        data = json.load(f)

    causal_relationships = data.get("causal_relationships", [])
    if not causal_relationships:
        logger.error("No causal_relationships found in %s", source)
        sys.exit(1)

    logger.info("Found %d legacy relationships", len(causal_relationships))

    # Convert all relationships
    converted = convert_legacy_relationships(causal_relationships)

    # Build full KG output
    full_kg = {
        "version": "1.0.0",
        "description": "ARIA 2D Materials PSP Knowledge Graph (v1)",
        "schema": "PSPRelationship",
        "total_relationships": len(converted),
        "causal_relationships": converted,
    }

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    full_path = output_dir / "aria_2d_kg_v1.json"
    with open(full_path, "w", encoding="utf-8") as f:
        json.dump(full_kg, f, indent=2, ensure_ascii=False)
    logger.info("Wrote full KG (%d relationships) to %s", len(converted), full_path)

    # Build tiny KG
    tiny_relationships = select_tiny_kg(converted)
    tiny_kg = {
        "version": "1.0.0",
        "description": "ARIA 2D Materials PSP Knowledge Graph (tiny example, ~6 relationships)",
        "schema": "PSPRelationship",
        "total_relationships": len(tiny_relationships),
        "causal_relationships": tiny_relationships,
    }

    tiny_path = output_dir / "aria_2d_kg_tiny.json"
    with open(tiny_path, "w", encoding="utf-8") as f:
        json.dump(tiny_kg, f, indent=2, ensure_ascii=False)
    logger.info("Wrote tiny KG (%d relationships) to %s", len(tiny_relationships), tiny_path)

    # Print summary
    from collections import Counter
    psp_dist = Counter(r["psp_type"] for r in converted)
    material_dist = Counter(r["material"] for r in converted)
    confidence_dist = Counter(r["confidence"] for r in converted)

    print("\n=== Migration Summary ===")
    print(f"Total relationships converted: {len(converted)}")
    print(f"\nPSP type distribution:")
    for psp, count in sorted(psp_dist.items()):
        print(f"  {psp}: {count}")
    print(f"\nMaterial distribution (top 15):")
    for mat, count in material_dist.most_common(15):
        print(f"  {mat or '(empty)'}: {count}")
    print(f"\nConfidence distribution:")
    for conf, count in sorted(confidence_dist.items()):
        print(f"  {conf}: {count}")
    print(f"\nOutput files:")
    print(f"  Full KG:  {full_path}")
    print(f"  Tiny KG:  {tiny_path}")


if __name__ == "__main__":
    main()