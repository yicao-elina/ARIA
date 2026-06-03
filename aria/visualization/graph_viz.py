"""
ARIA knowledge-graph visualisation.

Ported from the graph-drawing logic in ``KG/build_graph.py`` and
refactored to accept a NetworkX DiGraph directly rather than a JSON
file.  Uses the JHU colour theme.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Optional

import matplotlib.pyplot as plt
import networkx as nx

from aria.visualization.jhu_theme import get_jhu_color, setup_jhu_colors

logger = logging.getLogger(__name__)


def plot_kg(
    graph: nx.DiGraph,
    output_path: Optional[str] = None,
    max_nodes: int = 50,
    title: str = "PSP Causal Knowledge Graph",
    figsize: tuple = (20, 20),
    dpi: int = 300,
    node_scale: float = 120.0,
    seed: int = 42,
) -> None:
    """Visualise a PSP knowledge graph.

    Parameters
    ----------
    graph :
        A directed NetworkX graph (as loaded by
        :func:`aria.kg.graph_store.load_kg`).
    output_path :
        If provided, save the figure to this path.  The format is inferred
        from the extension (default: PNG).  If *None*, the figure is shown
        interactively.
    max_nodes :
        Maximum number of nodes to render.  If the graph exceeds this
        threshold, only the highest-degree nodes are kept and a warning
        is logged.
    title :
        Plot title.
    figsize :
        Figure size in inches.
    dpi :
        Resolution for saved figures.
    node_scale :
        Base multiplier for node sizes (node size = label length * node_scale).
    seed :
        Random seed for the spring layout.
    """
    setup_jhu_colors()

    if graph.number_of_nodes() == 0:
        logger.warning("Graph is empty; nothing to plot.")
        return

    # Sub-sample if too large
    if graph.number_of_nodes() > max_nodes:
        logger.info(
            "Graph has %d nodes (> max_nodes=%d). Selecting top-%d by degree.",
            graph.number_of_nodes(),
            max_nodes,
            max_nodes,
        )
        degrees = dict(graph.degree())
        top_nodes = sorted(degrees, key=degrees.get, reverse=True)[:max_nodes]  # type: ignore[arg-type]
        graph = graph.subgraph(top_nodes).copy()

    # Detect cycles
    try:
        cycles = list(nx.simple_cycles(graph))
        if cycles:
            logger.warning("Graph has %d cycles; it is not a DAG.", len(cycles))
    except Exception:
        pass

    # ---- Layout ----
    fig, ax = plt.subplots(figsize=figsize)
    pos = nx.spring_layout(graph, k=1.2, iterations=70, seed=seed)

    # ---- Colours ----
    try:
        node_color = get_jhu_color("Spirit Blue")
        edge_color = get_jhu_color("Heritage Blue")
    except Exception:
        node_color = "#68ACF5"
        edge_color = "#002D72"

    # Ensure colours are hex strings
    if isinstance(node_color, (list, tuple)):
        node_color = "#{:02x}{:02x}{:02x}".format(
            int(node_color[0] * 255),
            int(node_color[1] * 255),
            int(node_color[2] * 255),
        )
    if isinstance(edge_color, (list, tuple)):
        edge_color = "#{:02x}{:02x}{:02x}".format(
            int(edge_color[0] * 255),
            int(edge_color[1] * 255),
            int(edge_color[2] * 255),
        )

    # ---- Draw ----
    node_sizes = [len(str(n)) * node_scale for n in graph.nodes()]

    nx.draw_networkx_nodes(
        graph,
        pos,
        node_color=node_color,
        node_size=node_sizes,
        alpha=0.85,
        ax=ax,
    )
    nx.draw_networkx_edges(
        graph,
        pos,
        edge_color=edge_color,
        arrowstyle="->",
        arrowsize=20,
        width=1.5,
        alpha=0.6,
        node_size=[s + 500 for s in node_sizes],
        ax=ax,
    )
    nx.draw_networkx_labels(
        graph,
        pos,
        font_size=8,
        font_family="sans-serif",
        font_weight="bold",
        ax=ax,
    )

    # Edge labels (mechanism) if available and graph is small enough
    if graph.number_of_edges() <= 80:
        edge_labels = {}
        for u, v, data in graph.edges(data=True):
            mechanism = data.get("mechanism", "")
            if mechanism and len(mechanism) < 40:
                edge_labels[(u, v)] = textwrap.fill(mechanism, width=20)
        if edge_labels:
            nx.draw_networkx_edge_labels(
                graph,
                pos,
                edge_labels=edge_labels,
                font_size=6,
                ax=ax,
            )

    ax.set_title(title, fontsize=22, fontweight="bold")
    ax.axis("off")
    plt.tight_layout()

    if output_path:
        from pathlib import Path
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(str(out), dpi=dpi, bbox_inches="tight")
        logger.info("KG visualisation saved to %s", out)
    else:
        plt.show()

    plt.close(fig)