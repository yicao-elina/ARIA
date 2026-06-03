"""
PSP (Processing-Structure-Property) layer classification utilities.

Provides helpers to classify knowledge-graph node names into PSP layers,
determine which layers a query requires, and build causal chains from
triplets of (processing, structure, property) names.
"""

from __future__ import annotations

import re
from typing import List, Set, Tuple


# ---------------------------------------------------------------------------
# Keyword sets for layer classification
# ---------------------------------------------------------------------------

_PROCESSING_KEYWORDS = {
    "temperature", "pressure", "time", "duration", "atmosphere",
    "substrate", "precursor", "method", "annealing", "doping",
    "growth", "cvd", "mocvd", "sputtering", "catalyst", "solvent",
    "concentration", "flux", "rate", "power", "bias", "rf",
    "plasma", "laser", "pulsed", "continuous", "batch", "flow",
    "ratio", "partial_pressure", "carrier_gas", "argon", "nitrogen",
    "hydrogen", "vacuum", "ambient",
}

_STRUCTURE_KEYWORDS = {
    "crystallinity", "phase", "morphology", "defect", "grain",
    "layer", "vacancy", "stoichiometry", "crystal", "strain",
    "doping_level", "thickness", "orientation", "grain_size",
    "lattice", "interlayer", "stacking", "monolayer", "bilayer",
    "trilayer", "multilayer", "domain", "boundary", "dislocation",
    "substitution", "interstitial", "adsorption", "coverage",
}

_PROPERTY_KEYWORDS = {
    "mobility", "band_gap", "conductivity", "carrier", "resistance",
    "photoluminescence", "absorption", "emission", "ferromagnetic",
    "hall", "transconductance", "on/off", "on_off_ratio", "threshold",
    "saturation", "responsivity", "detectivity", "neff", "seebeck",
    "thermal_conductivity", "youngs_modulus", "stiffness",
    "toughness", "hardness", "flexibility", "transparency",
}


# ---------------------------------------------------------------------------
# classify_psp_layer
# ---------------------------------------------------------------------------

def classify_psp_layer(node_name: str) -> str:
    """Classify a KG node name into its PSP layer.

    Parameters
    ----------
    node_name :
        The node label from the knowledge graph (e.g.
        ``"growth_temperature"``).

    Returns
    -------
    str
        One of ``"Processing"``, ``"Structure"``, or ``"Property"``.
        Defaults to ``"Processing"`` when no keywords match.
    """
    text = node_name.lower()

    # Count keyword hits per layer
    processing_hits = sum(1 for kw in _PROCESSING_KEYWORDS if kw in text)
    structure_hits = sum(1 for kw in _STRUCTURE_KEYWORDS if kw in text)
    property_hits = sum(1 for kw in _PROPERTY_KEYWORDS if kw in text)

    max_hits = max(processing_hits, structure_hits, property_hits)

    if max_hits == 0:
        # No keyword match -- use heuristic position
        # "Processing" is the safest default for unknown nodes
        return "Processing"

    if property_hits == max_hits:
        return "Property"
    elif structure_hits == max_hits:
        return "Structure"
    else:
        return "Processing"


# ---------------------------------------------------------------------------
# get_required_layers
# ---------------------------------------------------------------------------

_QUERY_LAYER_PATTERNS: List[Tuple[re.Pattern, Set[str]]] = [
    (re.compile(r"\b(predict|property|measure|performance)\b", re.I), {"Property"}),
    (re.compile(r"\b(structure|crystal|defect|phase|morphology)\b", re.I), {"Structure", "Property"}),
    (re.compile(r"\b(synthes|grow|deposit|fabricat|process)\b", re.I), {"Processing", "Structure", "Property"}),
    (re.compile(r"\b(optimize|improve|enhance)\b", re.I), {"Processing", "Structure", "Property"}),
    (re.compile(r"\b(why|how|cause|mechanism)\b", re.I), {"Processing", "Structure", "Property"}),
    (re.compile(r"\b(what|which)\b", re.I), {"Property"}),
]


def get_required_layers(query: str) -> Set[str]:
    """Determine which PSP layers are needed to answer *query*.

    Uses keyword matching to decide whether the query touches
    Processing, Structure, and/or Property reasoning.

    Parameters
    ----------
    query :
        Natural-language query string.

    Returns
    -------
    set of str
        Subset of ``{"Processing", "Structure", "Property"}``.
    """
    layers: Set[str] = set()

    for pattern, matched_layers in _QUERY_LAYER_PATTERNS:
        if pattern.search(query):
            layers.update(matched_layers)

    # If no pattern matched, default to all three layers
    if not layers:
        layers = {"Processing", "Structure", "Property"}

    return layers


# ---------------------------------------------------------------------------
# build_psp_chain
# ---------------------------------------------------------------------------

def build_psp_chain(
    processing: str,
    structure: str,
    property_: str,
) -> List[Tuple[str, str]]:
    """Build a PSP causal chain as a list of directed edges.

    Parameters
    ----------
    processing :
        Name of the processing node (e.g. ``"CVD temperature 750C"``).
    structure :
        Name of the resulting structure node (e.g. ``"improved crystallinity"``).
    property_ :
        Name of the resulting property node (e.g. ``"higher carrier mobility"``).

    Returns
    -------
    list of (str, str)
        Directed edges representing the causal chain:
        ``[(processing, structure), (structure, property_)]``.
    """
    edges: List[Tuple[str, str]] = [
        (processing, structure),
        (structure, property_),
    ]
    return edges