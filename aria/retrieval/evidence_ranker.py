"""
Evidence ranking: score and sort causal paths by quality.

Retrieved paths can vary widely in length, evidence quality, and PSP-layer
coverage.  This module ranks them so that the best evidence is presented
first to the LLM or downstream evaluation pipeline.

Ranking combines three signals:

1. **Confidence** -- average edge confidence across the path.
2. **Evidence richness** -- fraction of edges that carry a non-empty
   mechanism quote.
3. **PSP coverage** -- how many of the three PSP layers (Processing,
   Structure, Property) the path traverses.

Typical usage::

    from aria.kg.graph_store import load_kg
    from aria.retrieval.path_search import find_psp_paths
    from aria.retrieval.evidence_ranker import rank_paths_by_evidence

    graph = load_kg("kg.json")
    paths = find_psp_paths(graph, ["CVD"], ["mobility"])
    ranked = rank_paths_by_evidence(paths, graph)
    for path, score in ranked:
        print(f"{score:.3f}: {' -> '.join(path)}")
"""

from __future__ import annotations

import logging
from typing import Dict, List, Tuple

import networkx as nx

from aria.kg.schema import psp_layers_covered

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Default scoring weights
# ---------------------------------------------------------------------------

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "confidence": 0.35,
    "evidence_richness": 0.30,
    "psp_coverage": 0.35,
}


# ---------------------------------------------------------------------------
# Path-level metrics
# ---------------------------------------------------------------------------

def _path_confidence(graph: nx.DiGraph, path: List[str]) -> float:
    """Average edge confidence along a path.

    Falls back to 1.0 for edges without an explicit confidence value.
    """
    if len(path) < 2:
        return 0.0

    total = 0.0
    for i in range(len(path) - 1):
        data = graph.get_edge_data(path[i], path[i + 1])
        if data:
            total += float(data.get("confidence", 1.0))
        else:
            total += 1.0
    return total / (len(path) - 1)


def _path_evidence_richness(graph: nx.DiGraph, path: List[str]) -> float:
    """Fraction of edges that have a non-empty mechanism quote.

    A path where every edge has textual evidence scores 1.0; a path
    where no edges have evidence scores 0.0.
    """
    if len(path) < 2:
        return 0.0

    with_evidence = 0
    for i in range(len(path) - 1):
        data = graph.get_edge_data(path[i], path[i + 1])
        if data and data.get("mechanism", "").strip():
            with_evidence += 1
    return with_evidence / (len(path) - 1)


def _path_psp_coverage(graph: nx.DiGraph, path: List[str]) -> float:
    """Fraction of the three PSP layers that the path covers.

    Returns a value in [0, 1]: 0/3, 1/3, 2/3, or 3/3.
    """
    layers = psp_layers_covered(path, graph)
    # Only count the three canonical layers
    n_covered = sum(1 for layer in ("Processing", "Structure", "Property") if layer in layers)
    return n_covered / 3.0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def rank_paths_by_evidence(
    paths: List[List[str]],
    graph: nx.DiGraph,
    weights: Dict[str, float] = _DEFAULT_WEIGHTS,  # type: ignore[assignment]
) -> List[Tuple[List[str], float]]:
    """Rank causal paths by a composite evidence-quality score.

    Each path receives a score that is a weighted combination of:

    * ``confidence`` -- average edge confidence
    * ``evidence_richness`` -- fraction of edges with mechanism text
    * ``psp_coverage`` -- fraction of PSP layers covered

    Paths are returned sorted in descending order of score.

    Parameters
    ----------
    paths:
        List of paths (each a list of node labels).
    graph:
        Directed PSP knowledge graph.
    weights:
        Optional weight dict with keys ``confidence``,
        ``evidence_richness``, ``psp_coverage``.  Values should sum to
        1.0 for interpretable scores.

    Returns
    -------
    list of (path, score)
        Sorted from best to worst.  An empty input list returns an empty
        result.
    """
    if not paths:
        return []

    w_conf = weights.get("confidence", 0.35)
    w_evid = weights.get("evidence_richness", 0.30)
    w_psp = weights.get("psp_coverage", 0.35)

    scored: List[Tuple[List[str], float]] = []
    for path in paths:
        conf = _path_confidence(graph, path)
        evid = _path_evidence_richness(graph, path)
        psp = _path_psp_coverage(graph, path)
        score = w_conf * conf + w_evid * evid + w_psp * psp
        scored.append((path, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def path_score_details(
    path: List[str],
    graph: nx.DiGraph,
) -> Dict[str, float]:
    """Return the three component scores for a single path.

    Useful for debugging or explaining rankings.

    Parameters
    ----------
    path:
        A single path (list of node labels).
    graph:
        Directed PSP knowledge graph.

    Returns
    -------
    dict
        Keys: ``confidence``, ``evidence_richness``, ``psp_coverage``.
    """
    return {
        "confidence": _path_confidence(graph, path),
        "evidence_richness": _path_evidence_richness(graph, path),
        "psp_coverage": _path_psp_coverage(graph, path),
    }