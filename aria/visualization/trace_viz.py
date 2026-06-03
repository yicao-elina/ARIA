"""
ARIA causal-trace visualization.

Produces PSP (Processing -> Structure -> Property) chain diagrams from
ARIAResult objects, and comparison plots across engine modes / tiers.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np

from aria.types import ARIAResult, CausalTraceStep
from aria.visualization.jhu_theme import get_jhu_color, setup_jhu_colors

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PSP-layer colour mapping
# ---------------------------------------------------------------------------

_LAYER_COLORS = {
    "Processing": get_jhu_color("Red"),
    "Structure": get_jhu_color("Heritage Blue"),
    "Property": get_jhu_color("Homewood Green"),
}

# Fallbacks if JHU colours are unavailable
_LAYER_COLORS_FALLBACK = {
    "Processing": "#CF4420",
    "Structure": "#002D72",
    "Property": "#00877B",
}


def _layer_color(layer: str) -> str:
    """Return a hex colour string for a PSP layer."""
    try:
        c = _LAYER_COLORS.get(layer)
        if c and isinstance(c, (list, tuple)):
            return "#{:02x}{:02x}{:02x}".format(
                int(c[0] * 255), int(c[1] * 255), int(c[2] * 255)
            )
        elif c:
            return str(c)
    except Exception:
        pass
    return _LAYER_COLORS_FALLBACK.get(layer, "#888888")


def _classify_node(label: str) -> str:
    """Classify a causal-trace node label into a PSP layer."""
    from aria.materials.psp import classify_psp_layer
    return classify_psp_layer(label)


# ---------------------------------------------------------------------------
# plot_causal_trace
# ---------------------------------------------------------------------------

def plot_causal_trace(
    result: ARIAResult,
    output_path: Optional[str] = None,
) -> None:
    """Visualise the causal trace of an ARIAResult as a PSP chain diagram.

    Each :class:`~aria.types.CausalTraceStep` in the result is rendered as a
    Processing -> Structure -> Property triplet, with edges coloured by PSP
    layer and confidence annotated.

    Parameters
    ----------
    result :
        An ARIAResult containing a ``causal_trace`` list.
    output_path :
        If provided, save the figure to this path (format inferred from
        extension).  If *None*, the figure is shown interactively.
    """
    setup_jhu_colors()

    trace = result.causal_trace
    if not trace:
        logger.warning("ARIAResult has an empty causal_trace; nothing to plot.")
        return

    fig, ax = plt.subplots(figsize=(14, 3 * max(len(trace), 1)))

    # Build a graph from the trace
    G = nx.DiGraph()
    node_layers: Dict[str, str] = {}
    edge_labels: Dict[tuple, str] = {}

    for i, step in enumerate(trace):
        p_node = f"P{i}: {step.processing}"
        s_node = f"S{i}: {step.structure}"
        prop_node = f"Prop{i}: {step.property_}"

        G.add_edge(p_node, s_node)
        G.add_edge(s_node, prop_node)

        node_layers[p_node] = "Processing"
        node_layers[s_node] = "Structure"
        node_layers[prop_node] = "Property"

        # Annotate confidence on edges
        if step.confidence is not None:
            edge_labels[(p_node, s_node)] = f"conf={step.confidence:.2f}"
            edge_labels[(s_node, prop_node)] = f"conf={step.confidence:.2f}"

    # Layout
    pos = nx.multipartite_layout(G, subset_key=lambda n: _classify_node(
        n.split(": ", 1)[1] if ": " in n else n
    ))

    # If multipartite_layout fails, fall back to shell
    if not pos:
        pos = nx.shell_layout(G)

    # Node colours
    node_colors = [_layer_color(node_layers.get(n, "Processing")) for n in G.nodes()]

    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2000, alpha=0.85, ax=ax)
    nx.draw_networkx_edges(G, pos, arrowstyle="->", arrowsize=20, alpha=0.7, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=7, font_weight="bold", ax=ax)
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=6, ax=ax)

    # Legend
    patches = [
        mpatches.Patch(color=_layer_color("Processing"), label="Processing"),
        mpatches.Patch(color=_layer_color("Structure"), label="Structure"),
        mpatches.Patch(color=_layer_color("Property"), label="Property"),
    ]
    ax.legend(handles=patches, loc="upper left", fontsize=9)
    ax.set_title(
        f"ARIA Causal Trace (tier={result.tier.name}, confidence={result.confidence:.2f})",
        fontsize=14,
        fontweight="bold",
    )
    ax.axis("off")

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Causal trace saved to %s", output_path)
    else:
        plt.show()

    plt.close(fig)


# ---------------------------------------------------------------------------
# plot_tier_comparison
# ---------------------------------------------------------------------------

def plot_tier_comparison(
    results: List[ARIAResult],
    output_path: Optional[str] = None,
) -> None:
    """Compare ARIAResult objects across tiers as a grouped bar chart.

    One bar group per result, showing the confidence and number of KG
    paths used.

    Parameters
    ----------
    results :
        List of ARIAResult objects (typically from different engine modes).
    output_path :
        If provided, save the figure.  Otherwise show interactively.
    """
    setup_jhu_colors()

    if not results:
        logger.warning("No results to compare.")
        return

    labels = [
        f"{r.mode}\nTier {r.tier.value}" if r.mode else f"Tier {r.tier.value}"
        for r in results
    ]
    confidences = [r.confidence for r in results]
    kg_paths = [r.kg_paths_used for r in results]

    x = np.arange(len(labels))
    width = 0.35

    fig, ax1 = plt.subplots(figsize=(max(8, len(labels) * 2), 6))

    color1 = _layer_color("Processing")
    color2 = _layer_color("Structure")

    bars1 = ax1.bar(x - width / 2, confidences, width, label="Confidence", color=color1, alpha=0.85)
    ax1.set_ylabel("Confidence", fontsize=12)
    ax1.set_ylim(0, 1.05)

    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width / 2, kg_paths, width, label="KG Paths", color=color2, alpha=0.85)
    ax2.set_ylabel("KG Paths Used", fontsize=12)

    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=10)
    ax1.set_title("ARIA Tier Comparison", fontsize=14, fontweight="bold")

    # Combined legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", fontsize=10)

    plt.tight_layout()

    if output_path:
        fig.savefig(output_path, dpi=300, bbox_inches="tight")
        logger.info("Tier comparison saved to %s", output_path)
    else:
        plt.show()

    plt.close(fig)