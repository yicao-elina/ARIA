#!/usr/bin/env python3
"""ARIA KG Construction CLI.

Build, merge, validate, and inspect PSP knowledge graphs.

Usage:
    python scripts/build_kg.py --migrate --source /path/to/combined_doping_data.json
    python scripts/build_kg.py --validate data/aria_2d_kg_v1.json
    python scripts/build_kg.py --stats data/aria_2d_kg_v1.json
    python scripts/build_kg.py --merge data/aria_2d_kg_v1.json data/new_relationships.json -o data/aria_2d_kg_v2.json
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

from aria.kg.graph_store import load_kg, save_kg, kg_stats
from aria.kg.diagnostics import main as diagnostics_main

logger = logging.getLogger(__name__)


def validate_kg(kg_path: str) -> bool:
    """Validate a KG JSON file for structural correctness.

    Checks:
    - File exists and is valid JSON
    - Contains causal_relationships array
    - Each relationship has required fields
    - PSP types are valid
    - Confidence values are in [0, 1]
    """
    path = Path(kg_path)
    if not path.exists():
        logger.error("File not found: %s", path)
        return False

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.error("Invalid JSON in %s: %s", path, e)
        return False

    relationships = data.get("causal_relationships", [])
    if not relationships:
        logger.error("No causal_relationships found in %s", path)
        return False

    valid_psp_types = {
        "Processing_to_Structure",
        "Structure_to_Property",
        "Processing_to_Property",
        "Structure_to_Structure",
    }
    required_fields = ["source", "relation", "target", "psp_type"]

    errors = 0
    warnings = 0

    for i, rel in enumerate(relationships):
        # Check required fields
        for field in required_fields:
            if field not in rel or not rel[field]:
                logger.error("Relationship %d: missing or empty required field '%s'", i, field)
                errors += 1

        # Check PSP type
        psp = rel.get("psp_type", "")
        if psp and psp not in valid_psp_types:
            logger.warning("Relationship %d: invalid PSP type '%s'", i, psp)
            warnings += 1

        # Check confidence
        conf = rel.get("confidence", 1.0)
        if isinstance(conf, (int, float)) and (conf < 0 or conf > 1):
            logger.warning("Relationship %d: confidence %.2f outside [0, 1]", i, conf)
            warnings += 1

    logger.info(
        "Validation complete: %d relationships, %d errors, %d warnings",
        len(relationships), errors, warnings,
    )
    return errors == 0


def merge_kg_files(
    primary_path: str,
    secondary_path: str,
    output_path: str,
    deduplicate: bool = True,
) -> None:
    """Merge two KG JSON files, optionally deduplicating relationships."""
    with open(primary_path, "r", encoding="utf-8") as f:
        primary = json.load(f)
    with open(secondary_path, "r", encoding="utf-8") as f:
        secondary = json.load(f)

    primary_rels = primary.get("causal_relationships", [])
    secondary_rels = secondary.get("causal_relationships", [])

    logger.info("Primary: %d relationships", len(primary_rels))
    logger.info("Secondary: %d relationships", len(secondary_rels))

    if deduplicate:
        # Deduplicate by (source, relation, target, material) tuple
        seen = set()
        merged = []
        for rel in primary_rels + secondary_rels:
            key = (
                rel.get("source", ""),
                rel.get("relation", ""),
                rel.get("target", ""),
                rel.get("material", ""),
            )
            if key not in seen:
                seen.add(key)
                merged.append(rel)
        logger.info("After deduplication: %d relationships", len(merged))
    else:
        merged = primary_rels + secondary_rels

    output_data = {
        "version": primary.get("version", "1.0.0"),
        "description": f"Merged KG: {primary.get('description', '')} + {secondary.get('description', '')}",
        "schema": "PSPRelationship",
        "total_relationships": len(merged),
        "causal_relationships": merged,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    logger.info("Merged KG saved to %s (%d relationships)", out, len(merged))


def print_stats(kg_path: str) -> None:
    """Load a KG and print its statistics."""
    try:
        kg = load_kg(kg_path)
    except FileNotFoundError:
        logger.error("KG file not found: %s", kg_path)
        return
    except ValueError as e:
        logger.error("Error loading KG: %s", e)
        return

    stats = kg_stats(kg)

    print("\n=== KG Statistics ===")
    print(f"  Nodes: {stats['num_nodes']}")
    print(f"  Edges: {stats['num_edges']}")
    print(f"  Density: {stats['density']:.6f}")
    print(f"  Is DAG: {stats['is_dag']}")
    print(f"  Weakly connected components: {stats['weakly_connected_components']}")
    print(f"  Strongly connected components: {stats['strongly_connected_components']}")
    print(f"  Root nodes (in-degree 0): {stats['num_root_nodes']}")
    print(f"  Leaf nodes (out-degree 0): {stats['num_leaf_nodes']}")
    print(f"  Intermediate nodes: {stats['num_intermediate_nodes']}")
    print(f"  Avg degree: {stats['avg_degree']:.2f}")
    print(f"  Max in-degree: {stats['max_in_degree']}")
    print(f"  Max out-degree: {stats['max_out_degree']}")

    # PSP type distribution from edge attributes
    from collections import Counter
    psp_dist = Counter(
        data.get("psp_type", "unknown")
        for _, _, data in kg.edges(data=True)
    )
    print("\n  PSP type distribution:")
    for psp, count in sorted(psp_dist.items()):
        print(f"    {psp}: {count}")

    # Material distribution
    material_dist = Counter(
        data.get("psp_relationship", {}).get("material", "")
        for _, _, data in kg.edges(data=True)
        if data.get("psp_relationship")
    )
    print("\n  Material distribution (top 10):")
    for mat, count in material_dist.most_common(10):
        print(f"    {mat or '(empty)'}: {count}")


def export_to_networkx(kg_path: str, output_path: str) -> None:
    """Load KG and export as NetworkX graphml for external tools."""
    kg = load_kg(kg_path)
    import networkx as nx
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(kg, str(output))
    logger.info("Exported KG as GraphML to %s (%d nodes, %d edges)",
                output, kg.number_of_nodes(), kg.number_of_edges())


def main():
    parser = argparse.ArgumentParser(
        description="ARIA KG Construction CLI",
        prog="aria-build-kg",
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-command")

    # migrate
    migrate_parser = subparsers.add_parser("migrate", help="Migrate legacy KG to PSPRelationship format")
    migrate_parser.add_argument("--source", type=str,
                                help="Path to legacy combined_doping_data.json")
    migrate_parser.add_argument("--output-dir", type=str,
                                default=str(PROJECT_ROOT / "data"),
                                help="Output directory")
    migrate_parser.add_argument("-v", "--verbose", action="store_true")

    # validate
    validate_parser = subparsers.add_parser("validate", help="Validate a KG JSON file")
    validate_parser.add_argument("kg_file", type=str, help="Path to KG JSON file")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Print KG statistics")
    stats_parser.add_argument("kg_file", type=str, help="Path to KG JSON file")

    # merge
    merge_parser = subparsers.add_parser("merge", help="Merge two KG files")
    merge_parser.add_argument("primary", type=str, help="Primary KG file")
    merge_parser.add_argument("secondary", type=str, help="Secondary KG file")
    merge_parser.add_argument("-o", "--output", type=str, required=True,
                              help="Output merged KG file")
    merge_parser.add_argument("--no-deduplicate", action="store_true",
                              help="Skip deduplication")

    # export
    export_parser = subparsers.add_parser("export", help="Export KG as GraphML")
    export_parser.add_argument("kg_file", type=str, help="Path to KG JSON file")
    export_parser.add_argument("-o", "--output", type=str, required=True,
                                help="Output GraphML file")

    # diagnostics (delegates to aria.kg.diagnostics)
    diag_parser = subparsers.add_parser("diagnose", help="Run KG diagnostics")
    diag_parser.add_argument("kg_file", type=str, help="Path to KG JSON file")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if getattr(args, "verbose", False) else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.command == "migrate":
        # Run the migration script
        from migrate_kg import main as migrate_main
        # Reconstruct sys.argv for the migration script
        migrate_argv = ["migrate_kg"]
        if args.source:
            migrate_argv.extend(["--source", args.source])
        if args.output_dir:
            migrate_argv.extend(["--output-dir", args.output_dir])
        if getattr(args, "verbose", False):
            migrate_argv.append("-v")
        sys.argv = migrate_argv
        migrate_main()

    elif args.command == "validate":
        success = validate_kg(args.kg_file)
        sys.exit(0 if success else 1)

    elif args.command == "stats":
        print_stats(args.kg_file)

    elif args.command == "merge":
        merge_kg_files(
            args.primary, args.secondary, args.output,
            deduplicate=not args.no_deduplicate,
        )

    elif args.command == "export":
        export_to_networkx(args.kg_file, args.output)

    elif args.command == "diagnose":
        # Delegate to aria.kg.diagnostics CLI
        sys.argv = ["aria-diagnose", args.kg_file]
        diagnostics_main()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()