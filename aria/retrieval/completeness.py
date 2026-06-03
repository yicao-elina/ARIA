"""
Causal completeness scoring for PSP pathways.

Implements the causal completeness metric C(E, q) from the ARIA paper:

    C(E, q) = |L(E) ∩ L_req(q)| / |L_req(q)|

where L = {Processing, Structure, Property} are the three PSP layers, E
is the retrieved evidence (set of paths), and L_req(q) is the set of
layers required by query q.

A path is **causally complete** if it traverses all three PSP layers.
Partial coverage is also scored so that retrieval can be ranked and
gaps identified.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

import networkx as nx

from aria.kg.schema import classify_node_layer, classify_path_layers, psp_layers_covered

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PSP layer enumeration
# ---------------------------------------------------------------------------

class PSPLayer(str, Enum):
    """The three causal layers in the Processing-Structure-Property hierarchy."""
    PROCESSING = "Processing"
    STRUCTURE = "Structure"
    PROPERTY = "Property"


ALL_LAYERS: FrozenSet[PSPLayer] = frozenset(PSPLayer)


# ---------------------------------------------------------------------------
# Layer classification
# ---------------------------------------------------------------------------

def classify_path_layers_detailed(
    path: List[str],
    graph: Optional[nx.DiGraph] = None,
) -> Dict[str, List[str]]:
    """Classify each node in *path* into a PSP layer.

    This is a thin wrapper around :func:`aria.kg.schema.classify_path_layers`
    that also checks edge ``psp_type`` attributes when *graph* is provided.

    Parameters
    ----------
    path:
        Ordered list of node labels.
    graph:
        Optional graph whose edge ``psp_type`` attribute is consulted.

    Returns
    -------
    dict
        ``{"Processing": [...], "Structure": [...], "Property": [...], "Unknown": [...]}``
    """
    base = classify_path_layers(path, graph)

    # Augment with edge-level PSP type when the graph is available
    if graph is not None:
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1])
            if edge_data and edge_data.get("psp_type"):
                psp_type_str = edge_data["psp_type"]
                # Map edge PSP type to node coverage
                if "Structure" in psp_type_str and path[i + 1] not in base["Structure"]:
                    base["Structure"].append(path[i + 1])
                if "Property" in psp_type_str and path[i + 1] not in base["Property"]:
                    base["Property"].append(path[i + 1])

    return base


# ---------------------------------------------------------------------------
# Required layers inference
# ---------------------------------------------------------------------------

def infer_required_layers(query: str) -> Set[PSPLayer]:
    """Infer which PSP layers a query requires.

    A *forward* query (synthesis -> property) typically requires all three
    layers.  A *property* query may only require Structure + Property.

    Parameters
    ----------
    query:
        Natural-language query string.

    Returns
    -------
    set of PSPLayer
        Layers that the query demands coverage for.
    """
    q_lower = query.lower()

    required: Set[PSPLayer] = set()

    # If the query mentions synthesis/processing conditions, require Processing
    processing_signals = [
        "temperature", "pressure", "cvd", "mocvd", "sputtering", "annealing",
        "growth", "deposition", "synthesis", "method", "doping", "dopant",
        "precursor", "substrate", "atmosphere", "time", "duration",
    ]
    if any(sig in q_lower for sig in processing_signals):
        required.add(PSPLayer.PROCESSING)

    # If the query mentions structure, require Structure
    structure_signals = [
        "crystallinity", "defect", "grain", "phase", "morphology",
        "layer", "vacancy", "stoichiometry", "strain", "thickness",
        "orientation", "structure", "microstructure",
    ]
    if any(sig in q_lower for sig in structure_signals):
        required.add(PSPLayer.STRUCTURE)

    # If the query mentions properties, require Property
    property_signals = [
        "mobility", "conductivity", "band gap", "bandgap", "carrier",
        "property", "electronic", "optical", "thermal", "mechanical",
        "ferromagnetic", "seebeck", "transconductance",
    ]
    if any(sig in q_lower for sig in property_signals):
        required.add(PSPLayer.PROPERTY)

    # Default: if nothing matched, assume all three layers
    if not required:
        required = {PSPLayer.PROCESSING, PSPLayer.STRUCTURE, PSPLayer.PROPERTY}

    # If only one layer matched, expand to include at least one more
    if len(required) == 1:
        required.add(PSPLayer.STRUCTURE)

    return required


# ---------------------------------------------------------------------------
# Completeness score
# ---------------------------------------------------------------------------

def causal_completeness_score(
    graph: nx.DiGraph,
    paths: List[List[str]],
    query: str,
) -> float:
    """Compute the causal completeness score C(E, q).

    .. math::

        C(E, q) = \\frac{|L(E) \\cap L_{\\text{req}}(q)|}{|L_{\\text{req}}(q)|}

    A score of 1.0 means the retrieved paths cover all PSP layers
    required by the query.  A score of 0.0 means no required layers
    are covered.

    Parameters
    ----------
    graph:
        Directed PSP knowledge graph.
    paths:
        Retrieved causal paths.
    query:
        User query string (used to infer required layers).

    Returns
    -------
    float
        Completeness score in [0, 1].
    """
    if not paths:
        return 0.0

    required_layers = infer_required_layers(query)

    # Collect layers covered by the entire evidence set E
    evidence_layers: Set[PSPLayer] = set()
    for path in paths:
        layers = psp_layers_covered(path, graph)
        for layer_name in layers:
            try:
                evidence_layers.add(PSPLayer(layer_name))
            except ValueError:
                pass  # skip "Unknown"

    if not required_layers:
        return 1.0  # nothing required -> trivially complete

    intersection = evidence_layers & required_layers
    return len(intersection) / len(required_layers)


def per_path_completeness(
    graph: nx.DiGraph,
    paths: List[List[str]],
    query: str,
) -> List[Tuple[List[str], float]]:
    """Compute the completeness score for each individual path.

    Useful for ranking or filtering paths that are causally incomplete.

    Parameters
    ----------
    graph:
        Directed PSP knowledge graph.
    paths:
        Retrieved causal paths.
    query:
        User query string.

    Returns
    -------
    list of (path, score)
        Each path paired with its individual completeness score.
    """
    required_layers = infer_required_layers(query)
    results: List[Tuple[List[str], float]] = []

    for path in paths:
        layers = psp_layers_covered(path, graph)
        path_layers: Set[PSPLayer] = set()
        for layer_name in layers:
            try:
                path_layers.add(PSPLayer(layer_name))
            except ValueError:
                pass

        if not required_layers:
            score = 1.0
        else:
            score = len(path_layers & required_layers) / len(required_layers)
        results.append((path, score))

    return results


def identify_missing_layers(
    graph: nx.DiGraph,
    paths: List[List[str]],
    query: str,
) -> Set[PSPLayer]:
    """Identify which PSP layers are missing from the retrieved evidence.

    Parameters
    ----------
    graph:
        Directed PSP knowledge graph.
    paths:
        Retrieved causal paths.
    query:
        User query string.

    Returns
    -------
    set of PSPLayer
        Layers required by the query but not covered by any path.
    """
    required = infer_required_layers(query)
    covered: Set[PSPLayer] = set()
    for path in paths:
        for layer_name in psp_layers_covered(path, graph):
            try:
                covered.add(PSPLayer(layer_name))
            except ValueError:
                pass
    return required - covered