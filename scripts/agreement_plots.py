#!/usr/bin/env python3
"""Render Tufte-compliant agreement figures from the agreement CSVs.

Outputs in data/benchmark/v2/review/figures/:
    01_pairwise_kappa_heatmap.png        — judge × judge Cohen's κ (lower-triangle shaded table)
    02_pairwise_pearson_heatmap.png      — judge × judge Pearson r (lower-triangle shaded table)
    03_per_language_kappa_heatmap.png    — DeepSeek-vs-each κ per language (single-hue, sorted)
    04_per_language_pearson_heatmap.png  — same for graded r
    05_pairwise_bar.png                  — sorted bar of all 10 pair κ, outlier highlighted
    06_panel_kappa_bar.png               — triplet / quartet Fleiss' κ as small multiples

Style lives in tufte_style.py: single-hue sequential ramps (no rainbow),
direct labels (no colorbars/legends), value-sorted axes, range frames.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tufte_style as ts  # noqa: E402

REVIEW = Path("data/benchmark/v2/review")
OUT = REVIEW / "figures"
OUT.mkdir(parents=True, exist_ok=True)


# ---------- shared loaders ----------
def load_square(path: Path) -> tuple[list[str], np.ndarray]:
    with open(path) as f:
        rows = list(csv.reader(f))
    judges = rows[0][1:]
    mat = np.full((len(judges), len(judges)), np.nan)
    for i, row in enumerate(rows[1:]):
        for j, val in enumerate(row[1:]):
            if val != "":
                mat[i, j] = float(val)
    return judges, mat


def load_per_language(path: Path) -> tuple[list[str], list[str], np.ndarray, list[int]]:
    with open(path) as f:
        rows = list(csv.reader(f))
    judges = rows[0][1:-1]
    langs, ntot = [], []
    mat = np.full((len(rows) - 1, len(judges)), np.nan)
    for i, row in enumerate(rows[1:]):
        langs.append(row[0])
        for j, val in enumerate(row[1:-1]):
            if val != "":
                mat[i, j] = float(val)
        ntot.append(int(row[-1]) if row[-1] else 0)
    return langs, judges, mat, ntot


# ---------- 01 / 02 — pairwise as a lower-triangle shaded table ----------
def plot_square_lower(csv_path, title, fname, vmin, vmax):
    """A heatmap of a small symmetric matrix is just a table; show the numbers,
    shade with one hue, and drop the trivial diagonal and the duplicate triangle."""
    judges, mat = load_square(csv_path)
    n = len(judges)

    # Sort judges by mean off-diagonal agreement (descending) so the outlier
    # sorts to an edge and the cluster reads as a block.
    off = mat.copy()
    np.fill_diagonal(off, np.nan)
    order = list(np.argsort(-np.nanmean(off, axis=1)))
    judges = [judges[i] for i in order]
    mat = mat[np.ix_(order, order)]

    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    ts.strip_axes(ax)

    for i in range(n):
        for j in range(n):
            if j >= i:  # lower triangle only — drop diagonal + upper duplicate
                continue
            v = mat[i, j]
            if np.isnan(v):
                continue
            frac = (np.clip(v, vmin, vmax) - vmin) / (vmax - vmin)
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                       facecolor=ts.SEQ_AGREE(frac), edgecolor="white", linewidth=2))
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color=ts.cell_text_color(v, vmin, vmax), fontsize=11)

    ax.set_xlim(-0.6, n - 1.5)
    ax.set_ylim(n - 0.5, 0.5)
    ax.set_xticks(range(n - 1))
    ax.set_xticklabels(judges[:-1], fontsize=10)
    ax.set_yticks(range(1, n))
    ax.set_yticklabels(judges[1:], fontsize=10)
    ax.set_title(title)
    ax.set_aspect("equal")
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)
    print(f"  {fname}")


# ---------- 03 / 04 — per-language single-hue heatmap, sorted ----------
def plot_per_lang(csv_path, title, fname, vmin, vmax):
    langs, judges, mat, ntot = load_per_language(csv_path)

    # Sort languages by mean agreement (descending) — strongest at top.
    order = list(np.argsort(-np.nanmean(mat, axis=1)))
    langs = [langs[i] for i in order]
    ntot = [ntot[i] for i in order]
    mat = mat[order]

    nrows, ncols = mat.shape
    fig, ax = plt.subplots(figsize=(5.6, 0.42 * nrows + 1.4))
    ts.strip_axes(ax)

    for i in range(nrows):
        for j in range(ncols):
            v = mat[i, j]
            if np.isnan(v):
                ax.text(j, i, "·", ha="center", va="center", color=ts.MUTED, fontsize=11)
                continue
            frac = (np.clip(v, vmin, vmax) - vmin) / (vmax - vmin)
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                       facecolor=ts.SEQ_AGREE(frac), edgecolor="white", linewidth=1.5))
            ax.text(j, i, f"{v:.2f}", ha="center", va="center",
                    color=ts.cell_text_color(v, vmin, vmax), fontsize=8.5)

    ax.set_xlim(-0.5, ncols - 0.5)
    ax.set_ylim(nrows - 0.5, -0.5)
    ax.set_xticks(range(ncols))
    ax.set_xticklabels(judges, fontsize=10)
    ax.xaxis.set_ticks_position("top")
    ax.set_yticks(range(nrows))
    ax.set_yticklabels([f"{lang}  ·  n={n}" for lang, n in zip(langs, ntot)], fontsize=9)
    ax.set_title(title, pad=24)
    fig.tight_layout()
    fig.savefig(OUT / fname)
    plt.close(fig)
    print(f"  {fname}")


# ---------- 05 — pairwise κ as a sorted bar, outlier in warm accent ----------
def plot_pairwise_bar():
    with open(REVIEW / "agreement_pairwise.csv") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: float(r["cohen_kappa"]) if r["cohen_kappa"] else -1)
    labels = [f"{r['judge1']} / {r['judge2']}" for r in rows]
    kappas = [float(r["cohen_kappa"]) if r["cohen_kappa"] else 0 for r in rows]
    ns = [int(r["n"]) for r in rows]
    is_outlier = ["gpt-5.4" in lab for lab in labels]

    fig, ax = plt.subplots(figsize=(8.2, 5.2))
    ts.range_frame(ax, left=False, bottom=True)
    y = np.arange(len(labels))
    colors = [ts.ACCENT_WARM if o else ts.ACCENT for o in is_outlier]
    ax.barh(y, kappas, color=colors, height=0.66)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    for col, o in zip(ax.get_yticklabels(), is_outlier):
        col.set_color(ts.ACCENT_WARM if o else ts.INK)
    ax.set_xlim(0, 0.85)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8])
    for i, (k, n) in enumerate(zip(kappas, ns)):
        ax.text(k + 0.012, i, f"{k:.2f}   n={n:,}", va="center", fontsize=9, color=ts.INK)
    ax.set_xlabel("Cohen's κ on overall_pass")
    ax.set_title("Pairwise inter-judge agreement")
    ax.text(0, len(labels) - 0.2, "amber = pairs involving GPT-5.4",
            fontsize=8.5, color=ts.ACCENT_WARM, va="bottom")
    fig.tight_layout()
    fig.savefig(OUT / "05_pairwise_bar.png")
    plt.close(fig)
    print("  05_pairwise_bar.png")


# ---------- 06 — panels as small multiples (triplets, then quartets) ----------
def plot_panels_bar():
    with open(REVIEW / "agreement_panels.csv") as f:
        rows = list(csv.DictReader(f))

    def group(size):
        g = [r for r in rows if int(r["panel_size"]) == size]
        g.sort(key=lambda r: float(r["fleiss_kappa"]) if r["fleiss_kappa"] else 0)
        return g

    triplets, quartets = group(3), group(4)
    heights = [len(triplets), len(quartets)]
    fig, axes = plt.subplots(
        2, 1, figsize=(8.4, 0.42 * sum(heights) + 1.6),
        gridspec_kw={"height_ratios": heights, "hspace": 0.32},
    )

    for ax, data, title in zip(axes, (triplets, quartets),
                               ("3-judge panels (Fleiss' κ)", "4-judge panels (Fleiss' κ)")):
        ts.range_frame(ax, left=False, bottom=True)
        labels = [r["judges"].replace("+", " + ") for r in data]
        kappas = [float(r["fleiss_kappa"]) if r["fleiss_kappa"] else 0 for r in data]
        ns = [int(r["n"]) for r in data]
        y = np.arange(len(labels))
        best = max(range(len(kappas)), key=lambda i: kappas[i]) if kappas else -1
        colors = [ts.ACCENT if i == best else ts.MUTED for i in range(len(kappas))]
        ax.barh(y, kappas, color=colors, height=0.62)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.set_xlim(0, 0.85)
        ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8])
        for i, (k, n) in enumerate(zip(kappas, ns)):
            ax.text(k + 0.012, i, f"{k:.2f}   n={n:,}", va="center", fontsize=8.5, color=ts.INK)
        ax.set_title(title)
    axes[-1].set_xlabel("Fleiss' κ on overall_pass")
    fig.tight_layout()
    fig.savefig(OUT / "06_panel_kappa_bar.png")
    plt.close(fig)
    print("  06_panel_kappa_bar.png")


def main():
    ts.apply_base()
    print("Generating agreement figures in", OUT)
    plot_square_lower(REVIEW / "agreement_kappa_matrix.csv",
                      "Inter-judge agreement — Cohen's κ on overall_pass",
                      "01_pairwise_kappa_heatmap.png", vmin=0.25, vmax=0.75)
    plot_square_lower(REVIEW / "agreement_pearson_matrix.csv",
                      "Inter-judge correlation — Pearson r on graded mean",
                      "02_pairwise_pearson_heatmap.png", vmin=0.5, vmax=0.95)
    plot_per_lang(REVIEW / "per_language_kappa_heatmap.csv",
                  "DeepSeek vs each judge — Cohen's κ per language",
                  "03_per_language_kappa_heatmap.png", vmin=0.0, vmax=1.0)
    plot_per_lang(REVIEW / "per_language_pearson_heatmap.csv",
                  "DeepSeek vs each judge — Pearson r per language",
                  "04_per_language_pearson_heatmap.png", vmin=0.4, vmax=1.0)
    plot_pairwise_bar()
    plot_panels_bar()
    print("Done.")


if __name__ == "__main__":
    main()
