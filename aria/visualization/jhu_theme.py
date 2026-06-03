"""
JHU colour theme for matplotlib.

Ported from ``jhu_colors/colors.py`` and adapted as a self-contained
module that does not depend on an external JSON data file.  Provides
the full JHU colour palette, helper functions, and publication-quality
matplotlib defaults.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.cycler import cycler
from typing import Any, Dict, List, Optional, Sequence, Union

# ---------------------------------------------------------------------------
# JHU Colour Palette  (RGB in 0-1 range)
# ---------------------------------------------------------------------------

JHU_COLORS: Dict[str, List[float]] = {
    "White":          [1.000, 1.000, 1.000],
    "Double Black":   [0.000, 0.000, 0.000],
    "Heritage Blue":  [0.000, 0.176, 0.447],
    "Spirit Blue":    [0.408, 0.675, 0.898],
    "Red":            [0.812, 0.271, 0.125],
    "Orange":         [1.000, 0.620, 0.106],
    "Homewood Green": [0.000, 0.529, 0.404],
    "Purple":         [0.643, 0.361, 0.596],
    "Gold":           [0.945, 0.769, 0.000],
    "Forest Green":   [0.153, 0.369, 0.239],
    "Harbor Blue":    [0.333, 0.588, 0.816],
    "Maroon":         [0.416, 0.125, 0.169],
}

# Canonical ordering for colour cycles
_COLOR_ORDER = [
    "Heritage Blue", "Red", "Homewood Green", "Orange",
    "Purple", "Spirit Blue", "Gold", "Forest Green",
    "Harbor Blue", "Maroon",
]

# ---------------------------------------------------------------------------
# Colormaps
# ---------------------------------------------------------------------------

_jhu_cmap = LinearSegmentedColormap.from_list(
    "jhu",
    [JHU_COLORS["Heritage Blue"], JHU_COLORS["White"], JHU_COLORS["Spirit Blue"]],
)

_jhu_diverging = LinearSegmentedColormap.from_list(
    "jhu_diverging",
    [JHU_COLORS["Red"], JHU_COLORS["White"], JHU_COLORS["Heritage Blue"]],
)

_jhu_sequential = LinearSegmentedColormap.from_list(
    "jhu_sequential",
    [JHU_COLORS["White"], JHU_COLORS["Spirit Blue"], JHU_COLORS["Heritage Blue"]],
)

# Register colormaps (compatible with matplotlib 3.5+ and 3.7+)
try:
    from matplotlib import colormaps as _cm_registry
    _cm_registry.register(cmap=_jhu_cmap, name="jhu")
    _cm_registry.register(cmap=_jhu_diverging, name="jhu_diverging")
    _cm_registry.register(cmap=_jhu_sequential, name="jhu_sequential")
except (ImportError, AttributeError, ValueError):
    try:
        mpl.cm.register_cmap(name="jhu", cmap=_jhu_cmap)
        mpl.cm.register_cmap(name="jhu_diverging", cmap=_jhu_diverging)
        mpl.cm.register_cmap(name="jhu_sequential", cmap=_jhu_sequential)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def setup_jhu_colors() -> Dict[str, List[float]]:
    """Set up JHU colours as the default matplotlib colour cycle and
    apply publication-quality style defaults.

    Returns the full colour palette dict for convenience.
    """
    colors = [JHU_COLORS[name] for name in _COLOR_ORDER]

    plt.rcParams.update({
        # Colour cycle
        "axes.prop_cycle": cycler(color=colors),
        # Figure
        "figure.figsize": (6, 4),
        # Fonts
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "DejaVu Sans", "Liberation Sans"],
        "font.size": 18,
        "axes.unicode_minus": False,
        # Axes
        "axes.titlesize": 16,
        "axes.labelsize": 18,
        "axes.linewidth": 1,
        "axes.grid": False,
        # Ticks
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
        "xtick.major.width": 1,
        "ytick.major.width": 1,
        "xtick.direction": "in",
        "ytick.direction": "in",
        # Lines
        "lines.linewidth": 1.5,
        # Legend
        "legend.fontsize": 12,
        # Save
        "savefig.format": "png",
        "savefig.dpi": 300,
    })

    return JHU_COLORS


def get_jhu_color(name: str) -> List[float]:
    """Return the RGB value of a JHU colour by name.

    Parameters
    ----------
    name :
        Colour name (e.g. ``"Heritage Blue"``, ``"Spirit Blue"``).

    Returns
    -------
    list of float
        ``[R, G, B]`` in the 0--1 range.  Returns black ``[0, 0, 0]``
        if the name is not found.
    """
    return JHU_COLORS.get(name, [0.0, 0.0, 0.0])


def list_jhu_colors() -> None:
    """Print all available JHU colours with RGB and hex values."""
    print("Available JHU colours:")
    for name in sorted(JHU_COLORS):
        rgb = JHU_COLORS[name]
        hex_color = "#{:02x}{:02x}{:02x}".format(
            int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255)
        )
        print(f"  {name:<20} RGB: ({rgb[0]:.3f}, {rgb[1]:.3f}, {rgb[2]:.3f})  HEX: {hex_color}")


def show_jhu_palette() -> "plt.Figure":
    """Display all JHU colours as a horizontal swatch plot.

    Returns the figure object for further customisation or saving.
    """
    import numpy as np

    fig, ax = plt.subplots(figsize=(12, 8))
    sorted_colors = sorted(JHU_COLORS.items())
    n_colors = len(sorted_colors)

    for i, (name, color) in enumerate(sorted_colors):
        y = n_colors - i - 1
        rect = plt.Rectangle((0, y), 4, 0.8, facecolor=color)
        ax.add_patch(rect)
        ax.text(4.2, y + 0.4, name, va="center", fontsize=12)

        rgb_text = f"RGB({int(color[0]*255)}, {int(color[1]*255)}, {int(color[2]*255)})"
        ax.text(8, y + 0.4, rgb_text, va="center", fontsize=10, color="gray")

    ax.set_xlim(0, 12)
    ax.set_ylim(0, n_colors)
    ax.set_title("JHU Colour Palette", fontsize=18, pad=20)
    ax.axis("off")
    plt.tight_layout()
    return fig