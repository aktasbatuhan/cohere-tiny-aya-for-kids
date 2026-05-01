#!/usr/bin/env python3
"""Render data-story PNGs from the 709-item balanced subset (DeepSeek-judged).

Outputs in data/benchmark/v2/review/figures/:
    07_per_model_pass_by_language.png       — model × language pass-rate heatmap
    08_per_model_pass_by_category.png       — model × category grouped bars
    09_graded_score_distribution.png        — per-model graded-mean violin/box
    10_item_agreement_donut.png             — all-pass / mixed / all-fail across 4 models
    11_difficulty_progression.png           — pass rate by difficulty per model
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

REVIEW = Path("data/benchmark/v2/review")
FIG = REVIEW / "figures"
FIG.mkdir(parents=True, exist_ok=True)

CSV_PATH = REVIEW / "balanced_review.csv"

MODEL_LABELS = {
    "google_gemma-4-31b-it": "Gemma 4 31B",
    "command-a-03-2025": "Command A",
    "c4ai-aya-expanse-32b": "Aya Expanse 32B",
    "tiny-aya-modal": "TinyAya 3.3B",
}
MODEL_ORDER = ["google_gemma-4-31b-it", "command-a-03-2025", "c4ai-aya-expanse-32b", "tiny-aya-modal"]
MODEL_COLORS = {
    "google_gemma-4-31b-it": "#4f46e5",
    "command-a-03-2025": "#0891b2",
    "c4ai-aya-expanse-32b": "#ea580c",
    "tiny-aya-modal": "#a855f7",
}

LANGUAGE_NAMES = {
    "ar":"Arabic","cs":"Czech","de":"German","en":"English","es":"Spanish",
    "fr":"French","hi":"Hindi","id":"Indonesian","it":"Italian","ja":"Japanese",
    "ko":"Korean","nl":"Dutch","pl":"Polish","pt":"Portuguese","ro":"Romanian",
    "ru":"Russian","sw":"Swahili","te":"Telugu","th":"Thai","tr":"Turkish",
    "uk":"Ukrainian","vi":"Vietnamese","zh":"Chinese",
}

PASS_CMAP = LinearSegmentedColormap.from_list(
    "passrate", ["#b91c1c", "#f97316", "#facc15", "#22c55e", "#15803d"]
)


def load_rows():
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


# ---------- 07 — Per-model pass-rate heatmap by language ----------
def plot_model_x_language():
    rows = load_rows()
    languages = sorted({r["language"] for r in rows})
    mat = np.full((len(MODEL_ORDER), len(languages)), np.nan)
    counts = np.zeros((len(MODEL_ORDER), len(languages)))
    for i, m in enumerate(MODEL_ORDER):
        for j, lang in enumerate(languages):
            lang_rows = [r for r in rows if r["language"] == lang]
            n = len(lang_rows)
            if n == 0:
                continue
            passes = sum(1 for r in lang_rows if r.get(f"{m}__overall_pass") == "PASS")
            mat[i, j] = passes / n * 100
            counts[i, j] = n

    fig, ax = plt.subplots(figsize=(13, 5))
    im = ax.imshow(mat, cmap=PASS_CMAP, vmin=0, vmax=70, aspect="auto")
    ax.set_xticks(range(len(languages)))
    ax.set_xticklabels(languages, rotation=0, fontsize=10)
    ax.set_yticks(range(len(MODEL_ORDER)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], fontsize=11)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            v = mat[i, j]
            if np.isnan(v):
                continue
            color = "white" if v >= 35 else "black"
            ax.text(j, i, f"{v:.0f}", ha="center", va="center", color=color, fontsize=9)
    ax.set_title("Pass rate (%) — per model × language (709-item balanced subset, DeepSeek-judged)",
                 fontsize=12, pad=12)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("Pass rate (%)")
    fig.tight_layout()
    fig.savefig(FIG / "07_per_model_pass_by_language.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  07_per_model_pass_by_language.png")


# ---------- 08 — Per-model pass rate by category (grouped bars) ----------
def plot_model_x_category():
    rows = load_rows()
    cats = sorted({r["category"] for r in rows})
    cat_n = {c: sum(1 for r in rows if r["category"] == c) for c in cats}
    cats = sorted(cats, key=lambda c: -cat_n[c])

    mat = np.zeros((len(MODEL_ORDER), len(cats)))
    for i, m in enumerate(MODEL_ORDER):
        for j, c in enumerate(cats):
            cr = [r for r in rows if r["category"] == c]
            n = len(cr) or 1
            mat[i, j] = sum(1 for r in cr if r.get(f"{m}__overall_pass") == "PASS") / n * 100

    fig, ax = plt.subplots(figsize=(13, 5.5))
    width = 0.18
    x = np.arange(len(cats))
    for i, m in enumerate(MODEL_ORDER):
        offset = (i - 1.5) * width
        ax.bar(x + offset, mat[i], width, color=MODEL_COLORS[m],
               edgecolor="black", linewidth=0.4, label=MODEL_LABELS[m])
    ax.set_xticks(x)
    ax.set_xticklabels(
        [c.replace("_", " ") + f"\n(n={cat_n[c]})" for c in cats],
        rotation=15, ha="right", fontsize=9,
    )
    ax.set_ylabel("Pass rate (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Pass rate by category × model", fontsize=12, pad=10)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    fig.tight_layout()
    fig.savefig(FIG / "08_per_model_pass_by_category.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  08_per_model_pass_by_category.png")


# ---------- 09 — Graded score distribution (per dim, per model) ----------
def plot_graded_distribution():
    rows = load_rows()
    dims = ["helpfulness", "empathy", "engagement", "accuracy"]
    fig, axes = plt.subplots(1, 4, figsize=(15, 4.5), sharey=True)
    for di, dim in enumerate(dims):
        ax = axes[di]
        data = []
        for m in MODEL_ORDER:
            vals = [int(r[f"{m}__{dim}"]) for r in rows if r.get(f"{m}__{dim}", "").isdigit()]
            data.append(vals)
        bp = ax.violinplot(data, positions=range(len(MODEL_ORDER)), showmeans=True, showmedians=True, widths=0.7)
        for pc, m in zip(bp["bodies"], MODEL_ORDER):
            pc.set_facecolor(MODEL_COLORS[m])
            pc.set_alpha(0.6)
            pc.set_edgecolor("black")
            pc.set_linewidth(0.6)
        for partname in ("cbars", "cmins", "cmaxes", "cmeans", "cmedians"):
            if partname in bp:
                bp[partname].set_color("black")
                bp[partname].set_linewidth(0.8)
        ax.set_xticks(range(len(MODEL_ORDER)))
        ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], rotation=20, ha="right", fontsize=9)
        ax.set_ylim(0.5, 5.5)
        ax.set_yticks([1, 2, 3, 4, 5])
        ax.set_title(dim.capitalize())
        ax.grid(axis="y", linestyle="--", alpha=0.4)
        if di == 0:
            ax.set_ylabel("Score (1–5)")
    fig.suptitle("Graded-dimension distribution per model (DeepSeek judge, 709-item balanced subset)", fontsize=12)
    fig.tight_layout()
    fig.savefig(FIG / "09_graded_score_distribution.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  09_graded_score_distribution.png")


# ---------- 10 — Item agreement donut (all-pass / mixed / all-fail) ----------
def plot_item_agreement_donut():
    rows = load_rows()
    counts = Counter()
    for r in rows:
        passes = sum(1 for m in MODEL_ORDER if r.get(f"{m}__overall_pass") == "PASS")
        if passes == 4:
            counts["All 4 pass"] += 1
        elif passes == 0:
            counts["All 4 fail"] += 1
        else:
            counts[f"Mixed ({passes}/4 pass)"] += 1

    # Order
    order = ["All 4 pass", "Mixed (3/4 pass)", "Mixed (2/4 pass)", "Mixed (1/4 pass)", "All 4 fail"]
    labels = [k for k in order if k in counts]
    values = [counts[k] for k in labels]
    colors = ["#15803d", "#86efac", "#facc15", "#fb923c", "#b91c1c"][:len(labels)]

    total = sum(values)

    fig, ax = plt.subplots(figsize=(9, 7))
    label_with_n = [f"{lbl}  —  {v} items ({v/total*100:.1f}%)" for lbl, v in zip(labels, values)]
    wedges, texts = ax.pie(
        values,
        labels=None,
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.42, edgecolor="white", linewidth=2),
        counterclock=False,
    )
    ax.legend(
        wedges, label_with_n, loc="center",
        bbox_to_anchor=(0.5, 0.5),
        frameon=False, fontsize=11,
    )
    ax.set_title(
        f"Per-item model agreement on overall_pass\n709 items × 4 models, DeepSeek-judged",
        fontsize=13, pad=18,
    )
    fig.tight_layout()
    fig.savefig(FIG / "10_item_agreement_donut.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  10_item_agreement_donut.png")


# ---------- 11 — Difficulty progression (per model) ----------
def plot_difficulty_progression():
    rows = load_rows()
    diffs = ["easy", "medium", "hard"]

    fig, ax = plt.subplots(figsize=(9, 5))
    for m in MODEL_ORDER:
        ys = []
        for d in diffs:
            dr = [r for r in rows if r["difficulty"] == d]
            n = len(dr) or 1
            ys.append(sum(1 for r in dr if r.get(f"{m}__overall_pass") == "PASS") / n * 100)
        ax.plot(diffs, ys, marker="o", linewidth=2.2, markersize=9,
                color=MODEL_COLORS[m], label=MODEL_LABELS[m])
        for x, y in zip(diffs, ys):
            ax.text(x, y + 1.5, f"{y:.0f}%", ha="center", fontsize=9, color=MODEL_COLORS[m])
    ax.set_xlabel("Difficulty")
    ax.set_ylabel("Pass rate (%)")
    ax.set_ylim(0, max(60, ax.get_ylim()[1]))
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.set_title("Pass rate by difficulty — easy → hard", fontsize=12, pad=10)
    ax.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(FIG / "11_difficulty_progression.png", dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("  11_difficulty_progression.png")


def main():
    print("Generating data-story figures in", FIG)
    plot_model_x_language()
    plot_model_x_category()
    plot_graded_distribution()
    plot_item_agreement_donut()
    plot_difficulty_progression()
    print("Done.")


if __name__ == "__main__":
    main()
