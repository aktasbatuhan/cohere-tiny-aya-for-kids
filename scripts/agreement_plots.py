#!/usr/bin/env python3
"""Render PNG figures from the agreement CSVs for the blog post.

Outputs in data/benchmark/v2/review/figures/:
    01_pairwise_kappa_heatmap.png        — 5×5 judge × judge Cohen's κ
    02_pairwise_pearson_heatmap.png      — 5×5 judge × judge Pearson r
    03_per_language_kappa_heatmap.png    — 23 langs × 4 judges (DeepSeek-vs-each)
    04_per_language_pearson_heatmap.png  — same for graded r
    05_pairwise_bar.png                  — sorted bar of all 10 pair κ
    06_panel_kappa_bar.png               — triplets + quartets Fleiss' κ
"""

from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

REVIEW = Path("data/benchmark/v2/review")
OUT = REVIEW / "figures"
OUT.mkdir(parents=True, exist_ok=True)

# κ-aware colormap: red(<0.2) → orange(fair) → yellow(moderate) → green(substantial) → dark green(almost perfect)
KAPPA_CMAP = LinearSegmentedColormap.from_list(
    "kappa", ["#b91c1c", "#f97316", "#facc15", "#22c55e", "#15803d"]
)


def load_square(path: Path) -> tuple[list[str], np.ndarray]:
    with open(path) as f:
        rows = list(csv.reader(f))
    judges = rows[0][1:]
    mat = np.full((len(judges), len(judges)), np.nan)
    for i, row in enumerate(rows[1:]):
        for j, val in enumerate(row[1:]):
            if val == "":
                continue
            mat[i, j] = float(val)
    return judges, mat


def annotate_heatmap(ax, mat, fmt="{:.2f}", text_threshold=None):
    rows, cols = mat.shape
    for i in range(rows):
        for j in range(cols):
            v = mat[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", color="gray", fontsize=10)
                continue
            color = "white" if (text_threshold is not None and v >= text_threshold) else "black"
            ax.text(j, i, fmt.format(v), ha="center", va="center", color=color, fontsize=10)


def plot_square_heatmap(csv_path, title, vmin, vmax, fname, cmap=KAPPA_CMAP, text_threshold=0.55):
    judges, mat = load_square(csv_path)
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, aspect="equal")
    ax.set_xticks(range(len(judges)))
    ax.set_yticks(range(len(judges)))
    ax.set_xticklabels(judges, rotation=30, ha="right")
    ax.set_yticklabels(judges)
    ax.set_title(title, fontsize=13, pad=12)
    annotate_heatmap(ax, mat, text_threshold=text_threshold)
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("Cohen's κ" if "κ" in title else "Pearson r")
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  {fname}")


def load_per_language(path: Path) -> tuple[list[str], list[str], np.ndarray, list[int]]:
    with open(path) as f:
        rows = list(csv.reader(f))
    header = rows[0]  # language, cohere, gpt-5.4, gemini, mimo, n_total
    judges = header[1:-1]
    langs, ntot = [], []
    mat = np.full((len(rows) - 1, len(judges)), np.nan)
    for i, row in enumerate(rows[1:]):
        langs.append(row[0])
        for j, val in enumerate(row[1:-1]):
            if val == "":
                continue
            mat[i, j] = float(val)
        ntot.append(int(row[-1]) if row[-1] else 0)
    return langs, judges, mat, ntot


def plot_per_lang_heatmap(csv_path, title, vmin, vmax, fname, cmap=KAPPA_CMAP):
    langs, judges, mat, ntot = load_per_language(csv_path)
    fig, ax = plt.subplots(figsize=(7, 9))
    im = ax.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
    ax.set_xticks(range(len(judges)))
    ax.set_xticklabels(judges, rotation=20, ha="right")
    # Annotate with language code + n_total to communicate sample size
    ax.set_yticks(range(len(langs)))
    ax.set_yticklabels([f"{lang}  (n={n})" for lang, n in zip(langs, ntot)])
    ax.set_title(title, fontsize=13, pad=12)
    rows, cols = mat.shape
    for i in range(rows):
        for j in range(cols):
            v = mat[i, j]
            if np.isnan(v):
                ax.text(j, i, "—", ha="center", va="center", color="gray", fontsize=8)
                continue
            color = "white" if v >= 0.55 else "black"
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", color=color, fontsize=8)
    cbar = fig.colorbar(im, ax=ax, fraction=0.04, pad=0.04)
    cbar.set_label("Cohen's κ" if "κ" in title else "Pearson r")
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  {fname}")


def plot_pairwise_bar():
    with open(REVIEW / "agreement_pairwise.csv") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: float(r["cohen_kappa"]) if r["cohen_kappa"] else -1, reverse=True)
    labels = [f"{r['judge1']} / {r['judge2']}" for r in rows]
    kappas = [float(r["cohen_kappa"]) if r["cohen_kappa"] else 0 for r in rows]
    ns = [int(r["n"]) for r in rows]

    colors = []
    for k in kappas:
        if k < 0.21: colors.append("#b91c1c")
        elif k < 0.41: colors.append("#f97316")
        elif k < 0.61: colors.append("#facc15")
        elif k < 0.81: colors.append("#22c55e")
        else: colors.append("#15803d")

    fig, ax = plt.subplots(figsize=(9, 6))
    y = np.arange(len(labels))
    bars = ax.barh(y, kappas, color=colors, edgecolor="black", linewidth=0.4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Cohen's κ on overall_pass")
    ax.set_xlim(0, 1.0)
    for k_band, label, color in [
        (0.21, "fair", "#f97316"),
        (0.41, "moderate", "#facc15"),
        (0.61, "substantial", "#22c55e"),
        (0.81, "almost\nperfect", "#15803d"),
    ]:
        ax.axvline(k_band, color="#888", linewidth=0.6, linestyle="--", alpha=0.5)
    for i, (b, k, n) in enumerate(zip(bars, kappas, ns)):
        ax.text(k + 0.01, i, f"κ={k:.2f}  n={n:,}", va="center", fontsize=9)
    ax.set_title("Pairwise inter-judge agreement (Cohen's κ on overall_pass)", fontsize=12)
    ax.text(1.01, -0.5, "fair·moderate·substantial·almost perfect",
            transform=ax.transData, ha="right", va="top", fontsize=8, color="#666")
    fig.tight_layout()
    fig.savefig(OUT / "05_pairwise_bar.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  05_pairwise_bar.png")


def plot_panels_bar():
    with open(REVIEW / "agreement_panels.csv") as f:
        rows = list(csv.DictReader(f))
    rows.sort(key=lambda r: (int(r["panel_size"]), -float(r["fleiss_kappa"]) if r["fleiss_kappa"] else 0))
    labels = [r["judges"].replace("+", " + ") for r in rows]
    kappas = [float(r["fleiss_kappa"]) if r["fleiss_kappa"] else 0 for r in rows]
    sizes = [int(r["panel_size"]) for r in rows]
    ns = [int(r["n"]) for r in rows]

    colors = ["#3b82f6" if s == 3 else "#a855f7" for s in sizes]

    fig, ax = plt.subplots(figsize=(10, 7))
    y = np.arange(len(labels))
    ax.barh(y, kappas, color=colors, edgecolor="black", linewidth=0.4)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("Fleiss' κ on overall_pass")
    ax.set_xlim(0, 1.0)
    for k_band in [0.21, 0.41, 0.61, 0.81]:
        ax.axvline(k_band, color="#888", linewidth=0.6, linestyle="--", alpha=0.5)
    for i, (k, n) in enumerate(zip(kappas, ns)):
        ax.text(k + 0.01, i, f"κ={k:.2f}  n={n:,}", va="center", fontsize=9)
    legend_elements = [
        plt.Rectangle((0, 0), 1, 1, color="#3b82f6", label="3-judge triplets"),
        plt.Rectangle((0, 0), 1, 1, color="#a855f7", label="4-judge quartets"),
    ]
    ax.legend(handles=legend_elements, loc="lower right")
    ax.set_title("3- and 4-judge panel agreement (Fleiss' κ)", fontsize=12)
    fig.tight_layout()
    fig.savefig(OUT / "06_panel_kappa_bar.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  06_panel_kappa_bar.png")


def main():
    print("Generating figures in", OUT)

    plot_square_heatmap(
        REVIEW / "agreement_kappa_matrix.csv",
        "Pairwise inter-judge agreement (Cohen's κ on overall_pass)",
        vmin=0.0, vmax=1.0,
        fname="01_pairwise_kappa_heatmap.png",
    )
    plot_square_heatmap(
        REVIEW / "agreement_pearson_matrix.csv",
        "Pairwise correlation on graded mean (Pearson r)",
        vmin=0.5, vmax=1.0,
        fname="02_pairwise_pearson_heatmap.png",
    )
    plot_per_lang_heatmap(
        REVIEW / "per_language_kappa_heatmap.csv",
        "DeepSeek vs each judge — Cohen's κ per language",
        vmin=0.0, vmax=1.0,
        fname="03_per_language_kappa_heatmap.png",
    )
    plot_per_lang_heatmap(
        REVIEW / "per_language_pearson_heatmap.csv",
        "DeepSeek vs each judge — Pearson r on graded mean, per language",
        vmin=0.4, vmax=1.0,
        fname="04_per_language_pearson_heatmap.png",
    )
    plot_pairwise_bar()
    plot_panels_bar()

    print("\nDone.")


if __name__ == "__main__":
    main()
