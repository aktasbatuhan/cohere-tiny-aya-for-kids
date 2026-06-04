#!/usr/bin/env python3
"""Shared Tufte-compliant style for the benchmark blog figures.

Applies Edward Tufte's principles (VDQI / Envisioning Information):
maximize data-ink, erase non-data-ink, direct labels over legends,
single-hue sequential ramps for ordered data (never rainbow), range
frames, sorted-by-value axes, the smallest effective difference.

Both agreement_plots.py and data_story_plots.py import from here so the
whole figure set reads as one house style.
"""

from __future__ import annotations

import matplotlib as mpl
from matplotlib.colors import LinearSegmentedColormap

# --- ink hierarchy: data darkest, labels next, scaffolding faintest ---
INK = "#1f2937"      # data + focal text
MUTED = "#9aa3af"    # axes, ticks, secondary labels
FAINT = "#e7e9ee"    # the rare gridline, if any
ACCENT = "#0f766e"   # single accent — used to signal, not decorate
ACCENT_WARM = "#b45309"  # second accent, reserved for the one outlier story

# Single-hue sequential ramps (light -> dark). Hue is the only thing that
# moves, so the eye reads them as ordered — the whole point of dropping the
# red/yellow/green rainbow that mis-encodes ordinal data.
SEQ_AGREE = LinearSegmentedColormap.from_list("seq_agree", ["#f3f8f7", "#0f766e"])
SEQ_PASS = LinearSegmentedColormap.from_list("seq_pass", ["#eef1fb", "#312e81"])

# Muted, luminance-separated model palette. Distinct but quiet — contrast is
# spent on the data, not on telling four bars apart.
MODEL_COLORS = {
    "google_gemma-4-31b-it": "#3730a3",   # indigo
    "command-a-03-2025": "#0f766e",       # teal
    "c4ai-aya-expanse-32b": "#b45309",    # amber
    "tiny-aya-modal": "#9d174d",          # rose
}


def apply_base():
    """Global rcParams: white ground, no top/right spines, no grid, left-set titles."""
    mpl.rcParams.update({
        "figure.facecolor": "white",
        "figure.dpi": 180,
        "savefig.dpi": 180,
        "savefig.bbox": "tight",
        "axes.facecolor": "white",
        "axes.edgecolor": MUTED,
        "axes.linewidth": 0.8,
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.titlesize": 13,
        "axes.titleweight": "regular",
        "axes.titlelocation": "left",
        "axes.titlecolor": INK,
        "axes.titlepad": 10,
        "axes.labelcolor": INK,
        "axes.labelsize": 11,
        "text.color": INK,
        "font.size": 11,
        "font.family": "sans-serif",
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelcolor": INK,
        "ytick.labelcolor": INK,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
    })


def strip_axes(ax):
    """Heatmap / slopegraph chrome removal: no spines, no ticks."""
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(length=0)


def range_frame(ax, left=True, bottom=True):
    """Keep only the spines that anchor the data; thin and gray."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
        ax.spines[s].set_linewidth(0.8)
    ax.tick_params(length=0)


def cell_text_color(value, vmin, vmax, flip=0.55):
    """Dark text on light cells, white on dark — readable on a single-hue ramp."""
    if vmax == vmin:
        return INK
    frac = (value - vmin) / (vmax - vmin)
    return "white" if frac >= flip else INK
