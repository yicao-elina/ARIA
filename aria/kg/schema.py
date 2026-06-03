"""
PSP schema helpers: re-export types and classify PSP layers.

This module re-exports :class:`~aria.types.PSPRelationship` and
:class:`~aria.types.PSPType` for convenient access via
``aria.kg.schema``, and adds helper functions for classifying which
PSP layers a node or path belongs to.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set

from aria.types import PSPRelationship, PSPType, _infer_psp_type

__all__ = [
    "PSPRelationship",
    "PSPType",
    "classify_node_layer",
    "classify_path_layers",
    "psp_layers_covered",
]

# ---------------------------------------------------------------------------
# Keyword sets for each PSP layer
# ---------------------------------------------------------------------------

_PROCESSING_KEYWORDS: Set[str] = {
    "temperature", "pressure", "time", "atmosphere", "substrate",
    "precursor", "method", "annealing", "doping", "growth", "cvd",
    "mocvd", "sputtering", "catalyst", "solvent", "concentration",
    "deposition", "synthesis", "anneal", "flux", "ratio", "dopant",
}

_STRUCTURE_KEYWORDS: Set[str] = {
    "crystallinity", "phase", "morphology", "defect", "grain",
    "layer", "vacancy", "stoichiometry", "crystal", "strain",
    "doping_level", "thickness", "orientation", "grain_size",
    "lattice", "microstructure", "texture", "roughness",
}

_PROPERTY_KEYWORDS: Set[str] = {
    "mobility", "band_gap", "conductivity", "carrier", "resistance",
    "photoluminescence", "absorption", "emission", "ferromagnetic",
    "hall", "transconductance", "on/off", "property", "electronic",
    "optical", "thermal", "mechanical", "seebeck", "figure_of_merit",
}


def classify_node_layer(node: str) -> Optional[str]:
    """Classify a single KG node into a PSP layer.

    Parameters
    ----------
    node:
        Node label string (e.g. ``"CVD temperature"``).

    Returns
    -------
    str or None
        One of ``"Processing"``, ``"Structure"``, ``"Property"``,
        or ``None`` if the node does not match any layer's keywords.
    """
    node_lower = node.lower()
    proc_score = sum(1 for kw in _PROCESSING_KEYWORDS if kw in node_lower)
    struct_score = sum(1 for kw in _STRUCTURE_KEYWORDS if kw in node_lower)
    prop_score = sum(1 for kw in _PROPERTY_KEYWORDS if kw in node_lower)

    scores = {"Processing": proc_score, "Structure": struct_score, "Property": prop_score}
    best = max(scores, key=scores.get)  # type: ignore[arg-type]
    if scores[best] == 0:  # type: ignore[index]
        return None
    return best


def classify_path_layers(path: List[str], graph=None) -> Dict[str, List[str]]:
    """Classify which PSP layers each node in a path belongs to.

    Parameters
    ----------
    path:
        Ordered list of node labels forming a causal path.
    graph:
        Optional NetworkX DiGraph.  When provided, edge ``psp_type``
        attributes are used to enrich the classification.

    Returns
    -------
    dict
        ``{"Processing": [...], "Structure": [...], "Property": [...], "Unknown": [...]}``
        where each value is a list of node labels from *path*.
    """
    result: Dict[str, List[str]] = {
        "Processing": [],
        "Structure": [],
        "Property": [],
        "Unknown": [],
    }
    for node in path:
        layer = classify_node_layer(node)
        if layer is None:
            result["Unknown"].append(node)
        else:
            result[layer].append(node)
    return result


def psp_layers_covered(path: List[str], graph=None) -> Set[str]:
    """Return the set of PSP layers that a path covers.

    Parameters
    ----------
    path:
        Ordered list of node labels.
    graph:
        Optional NetworkX DiGraph (unused currently, reserved for
        edge-based classification).

    Returns
    -------
    set of str
        Subset of ``{"Processing", "Structure", "Property"}``.
    """
    classification = classify_path_layers(path, graph)
    return {layer for layer in ("Processing", "Structure", "Property") if classification[layer]}