"""
Knowledge graph storage: load, save, and inspect PSP causal graphs.

The canonical format is the enriched JSON with a ``causal_relationships``
key, where each relationship has fields like ``cause_parameter``,
``effect_on_doping``, ``affected_property``, ``mechanism_quote``,
``confidence_level``, ``source_file``, and ``relationship_id``.

Functions in this module convert that JSON into a NetworkX DiGraph whose
edges carry PSPRelationship metadata and whose nodes are the canonical
parameter / property strings.

Ported from the ``_load_kg`` logic in ``aria_core_ollama.py`` (lines 73-103)
and consolidated across the ``kg_only.py`` and ``naive_kg_ollama.py`` variants.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import networkx as nx

from aria.types import PSPRelationship, _infer_psp_type, _infer_relation, _parse_confidence

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_kg(path: str) -> nx.DiGraph:
    """Load a PSP knowledge graph from an enriched JSON file.

    The file must contain a top-level ``causal_relationships`` array (or be
    a plain list of relationship dicts).  Each relationship is converted to a
    :class:`~aria.types.PSPRelationship` and stored as a directed edge in the
    returned graph.

    Nodes with ``unknown`` or ``n/a`` values are silently skipped.

    Parameters
    ----------
    path:
        Path to the JSON file.

    Returns
    -------
    nx.DiGraph
        Directed graph whose edge attributes include the full
        :class:`PSPRelationship` dataclass fields as well as a serialised
        ``psp_relationship`` dict.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    ValueError
        If the JSON cannot be parsed or contains no valid relationships.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"KG file not found: {p}")

    with open(p, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    relationships = data.get("causal_relationships", data if isinstance(data, list) else [])

    G = nx.DiGraph()

    added = 0
    for raw in relationships:
        cause = (raw.get("cause_parameter") or "").strip()
        effect = (raw.get("effect_on_doping") or "").strip()

        # Skip placeholder values
        if not cause or not effect:
            continue
        if "unknown" in cause.lower() or "n/a" in cause.lower():
            continue
        if "unknown" in effect.lower() or "n/a" in effect.lower():
            continue

        # Build a PSPRelationship from the enriched row
        rel = PSPRelationship.from_legacy(raw)

        G.add_edge(
            cause,
            effect,
            # Preserve original edge-level attributes for backward compat
            mechanism=raw.get("mechanism_quote", rel.evidence_text or ""),
            affected_property=raw.get("affected_property", rel.target),
            source_file=raw.get("source_file", ""),
            source_doi=raw.get("source_doi", ""),
            confidence=raw.get("confidence", rel.confidence),
            # Full PSP relationship data
            psp_relationship=rel.to_dict(),
            psp_type=rel.psp_type,
            relation=rel.relation,
        )
        added += 1

    if added == 0:
        raise ValueError(f"No valid relationships found in {p}")

    logger.info("Loaded KG from %s: %d nodes, %d edges", p, G.number_of_nodes(), G.number_of_edges())
    return G


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def save_kg(graph: nx.DiGraph, path: str) -> None:
    """Serialise a PSP knowledge graph to JSON.

    The output follows the enriched format (``causal_relationships`` key)
    and includes every edge attribute that was present in the original load.

    Parameters
    ----------
    graph:
        Directed NetworkX graph (as returned by :func:`load_kg`).
    path:
        Destination file path.
    """
    relationships: list[dict[str, Any]] = []

    for u, v, data in graph.edges(data=True):
        rel_dict = data.get("psp_relationship")
        if rel_dict is not None:
            # Use the full PSPRelationship dict as the canonical record
            entry = dict(rel_dict)
            # Overlay any legacy edge-level fields that might have been added
            entry.setdefault("mechanism_quote", data.get("mechanism", ""))
            entry.setdefault("source_file", data.get("source_file", ""))
            entry.setdefault("source_doi", data.get("source_doi", ""))
            entry.setdefault("confidence_level", data.get("confidence", ""))
        else:
            # Fallback: reconstruct from edge attributes
            entry = {
                "cause_parameter": u,
                "effect_on_doping": v,
                "affected_property": data.get("affected_property", ""),
                "mechanism_quote": data.get("mechanism", ""),
                "confidence_level": str(data.get("confidence", 1.0)),
                "source_file": data.get("source_file", ""),
                "source_doi": data.get("source_doi", ""),
                "relationship_id": None,
            }
        relationships.append(entry)

    payload = {"causal_relationships": relationships}

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    logger.info("Saved KG to %s: %d relationships", out, len(relationships))


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

def kg_stats(graph: nx.DiGraph) -> Dict[str, Any]:
    """Return summary statistics for a PSP knowledge graph.

    Parameters
    ----------
    graph:
        Directed NetworkX graph.

    Returns
    -------
    dict
        Keys: ``num_nodes``, ``num_edges``, ``density``, ``is_dag``,
        ``weakly_connected_components``, ``strongly_connected_components``,
        ``root_nodes`` (in-degree 0), ``leaf_nodes`` (out-degree 0),
        ``intermediate_nodes``, ``avg_degree``, ``max_in_degree``,
        ``max_out_degree``.
    """
    n_nodes = graph.number_of_nodes()
    n_edges = graph.number_of_edges()

    root_nodes = [n for n in graph.nodes() if graph.in_degree(n) == 0]
    leaf_nodes = [n for n in graph.nodes() if graph.out_degree(n) == 0]
    intermediate = [n for n in graph.nodes() if graph.in_degree(n) > 0 and graph.out_degree(n) > 0]

    in_degrees = dict(graph.in_degree())
    out_degrees = dict(graph.out_degree())
    total_degrees = dict(graph.degree())

    return {
        "num_nodes": n_nodes,
        "num_edges": n_edges,
        "density": nx.density(graph),
        "is_dag": nx.is_directed_acyclic_graph(graph),
        "weakly_connected_components": nx.number_weakly_connected_components(graph),
        "strongly_connected_components": nx.number_strongly_connected_components(graph),
        "root_nodes": root_nodes,
        "leaf_nodes": leaf_nodes,
        "intermediate_nodes": intermediate,
        "num_root_nodes": len(root_nodes),
        "num_leaf_nodes": len(leaf_nodes),
        "num_intermediate_nodes": len(intermediate),
        "avg_degree": sum(total_degrees.values()) / n_nodes if n_nodes else 0,
        "avg_in_degree": sum(in_degrees.values()) / n_nodes if n_nodes else 0,
        "avg_out_degree": sum(out_degrees.values()) / n_nodes if n_nodes else 0,
        "max_in_degree": max(in_degrees.values()) if in_degrees else 0,
        "max_out_degree": max(out_degrees.values()) if out_degrees else 0,
    }