"""ARIA visualization module.

Provides plotting utilities for knowledge graphs, causal traces,
and JHU-themed figures.  Heavy dependencies (matplotlib, networkx)
are imported lazily to avoid import errors in environments without
them installed.
"""


def __getattr__(name):
    """Lazy imports for visualization submodules."""
    if name == "plot_causal_trace":
        from aria.visualization.trace_viz import plot_causal_trace
        return plot_causal_trace
    elif name == "plot_tier_comparison":
        from aria.visualization.trace_viz import plot_tier_comparison
        return plot_tier_comparison
    elif name == "plot_kg":
        from aria.visualization.graph_viz import plot_kg
        return plot_kg
    elif name == "setup_jhu_colors":
        from aria.visualization.jhu_theme import setup_jhu_colors
        return setup_jhu_colors
    elif name == "get_jhu_color":
        from aria.visualization.jhu_theme import get_jhu_color
        return get_jhu_color
    elif name == "list_jhu_colors":
        from aria.visualization.jhu_theme import list_jhu_colors
        return list_jhu_colors
    elif name == "show_jhu_palette":
        from aria.visualization.jhu_theme import show_jhu_palette
        return show_jhu_palette
    raise AttributeError(f"module 'aria.visualization' has no attribute {name!r}")


__all__ = [
    "plot_causal_trace",
    "plot_tier_comparison",
    "plot_kg",
    "setup_jhu_colors",
    "get_jhu_color",
    "list_jhu_colors",
    "show_jhu_palette",
]