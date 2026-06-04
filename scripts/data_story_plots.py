#!/usr/bin/env python3
"""Render Tufte-compliant data-story PNGs from the 709-item balanced subset.

Outputs in data/benchmark/v2/review/figures/:
    07_per_model_pass_by_language.png   — model × language pass rate (single-hue, sorted by difficulty)
    08_per_model_pass_by_category.png   — small multiples, one panel per model
    09_graded_score_distribution.png    — small-multiple score histograms (model × dimension)
    10_item_agreement_donut.png         — single horizontal stacked bar (was a donut)
    11_difficulty_progression.png       — slopegraph, direct end labels

Style lives in tufte_style.py: single-hue sequential ramps (no rainbow),
direct labels (no colorbars/legends), value-sorted axes, range frames.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tufte_style as ts  # noqa: E402

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


def load_rows():
    with open(CSV_PATH) as f:
        return list(csv.DictReader(f))


def pass_rate(rows, model):
    n = len(rows) or 1
    return sum(1 for r in rows if r.get(f"{model}__overall_pass") == "PASS") / n * 100


# ---------- 07 — model × language pass rate, single-hue, sorted ----------
def plot_model_x_language():
    rows = load_rows()
    languages = sorted({r["language"] for r in rows})
    by_lang = {lang: [r for r in rows if r["language"] == lang] for lang in languages}

    mat = np.array([[pass_rate(by_lang[lang], m) for lang in languages] for m in MODEL_ORDER])
    # Sort languages by mean pass rate (descending): the easy lane (English)
    # to the left, the hard tail (Telugu / Thai / Swahili) to the right, so the
    # gradient reads as one left-to-right slope instead of alphabetical noise.
    order = list(np.argsort(-mat.mean(axis=0)))
    languages = [languages[j] for j in order]
    mat = mat[:, order]

    vmax = 90
    fig, ax = plt.subplots(figsize=(13, 3.4))
    ts.strip_axes(ax)
    nrows, ncols = mat.shape
    for i in range(nrows):
        for j in range(ncols):
            v = mat[i, j]
            ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                                       facecolor=ts.SEQ_PASS(v / vmax), edgecolor="white", linewidth=1.5))
            ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                    color=ts.cell_text_color(v, 0, vmax, flip=0.5), fontsize=9)
    ax.set_xlim(-0.5, ncols - 0.5)
    ax.set_ylim(nrows - 0.5, -0.5)
    ax.set_xticks(range(ncols))
    ax.set_xticklabels(languages, fontsize=10)
    ax.set_yticks(range(nrows))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], fontsize=10)
    ax.set_title("Pass rate (%) by model × language — easiest languages left, hardest right", pad=12)
    fig.tight_layout()
    fig.savefig(FIG / "07_per_model_pass_by_language.png")
    plt.close(fig)
    print("  07_per_model_pass_by_language.png")


# ---------- 08 — pass by category, small multiples (one panel per model) ----------
def plot_model_x_category():
    rows = load_rows()
    cats = sorted({r["category"] for r in rows})
    cat_n = {c: sum(1 for r in rows if r["category"] == c) for c in cats}
    by_cat = {c: [r for r in rows if r["category"] == c] for c in cats}

    # One shared category order (by overall pass rate, descending) across all
    # panels — that's what makes the small multiples comparable at a glance.
    overall = {c: np.mean([pass_rate(by_cat[c], m) for m in MODEL_ORDER]) for c in cats}
    cats = sorted(cats, key=lambda c: overall[c])  # ascending -> largest at top after barh
    ylabels = [c.replace("_", " ") + f"  (n={cat_n[c]})" for c in cats]

    fig, axes = plt.subplots(1, 4, figsize=(14, 4.2), sharey=True)
    y = np.arange(len(cats))
    for ax, m in zip(axes, MODEL_ORDER):
        ts.range_frame(ax, left=False, bottom=True)
        vals = [pass_rate(by_cat[c], m) for c in cats]
        ax.barh(y, vals, color=ts.MODEL_COLORS[m], height=0.66)
        ax.set_xlim(0, 100)
        ax.set_xticks([0, 50, 100])
        for i, v in enumerate(vals):
            ax.text(v + 2, i, f"{v:.0f}", va="center", fontsize=8.5, color=ts.INK)
        ax.set_title(MODEL_LABELS[m], color=ts.MODEL_COLORS[m])
    axes[0].set_yticks(y)
    axes[0].set_yticklabels(ylabels, fontsize=9)
    fig.suptitle("Pass rate (%) by category — one panel per model, shared scale",
                 x=0.01, ha="left", fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(FIG / "08_per_model_pass_by_category.png")
    plt.close(fig)
    print("  08_per_model_pass_by_category.png")


# ---------- 09 — graded score distributions, small-multiple histograms ----------
def plot_graded_distribution():
    rows = load_rows()
    dims = ["helpfulness", "empathy", "engagement", "accuracy"]
    scores = [1, 2, 3, 4, 5]

    fig, axes = plt.subplots(len(MODEL_ORDER), len(dims), figsize=(12, 8),
                             sharex=True, sharey=True)
    for ri, m in enumerate(MODEL_ORDER):
        for ci, dim in enumerate(dims):
            ax = axes[ri, ci]
            ts.range_frame(ax, left=False, bottom=(ri == len(MODEL_ORDER) - 1))
            vals = [int(r[f"{m}__{dim}"]) for r in rows if r.get(f"{m}__{dim}", "").isdigit()]
            n = len(vals) or 1
            pct = [sum(1 for v in vals if v == s) / n * 100 for s in scores]
            ax.bar(scores, pct, width=0.74, color=ts.MODEL_COLORS[m])
            if vals:  # mean as a thin reference line — the one summary stat worth drawing
                ax.axvline(np.mean(vals), color=ts.INK, linewidth=1.0)
            ax.set_xticks(scores)
            ax.set_ylim(0, 80)  # headroom so the accuracy=5 spikes don't clip
            ax.set_yticks([0, 40, 80])
            if ri == 0:
                ax.set_title(dim.capitalize(), fontsize=11)
            if ci == 0:
                ax.set_ylabel(MODEL_LABELS[m], color=ts.MODEL_COLORS[m], fontsize=10)
    fig.suptitle("Graded-score distribution (% of items at each 1–5 score); vertical line = mean",
                 x=0.01, ha="left", fontsize=13)
    fig.supxlabel("Score (1–5)", fontsize=10)
    fig.tight_layout(rect=(0, 0.02, 1, 0.96))
    fig.savefig(FIG / "09_graded_score_distribution.png")
    plt.close(fig)
    print("  09_graded_score_distribution.png")


# ---------- 10 — item agreement as a single horizontal stacked bar ----------
def plot_item_agreement_bar():
    rows = load_rows()
    counts = Counter()
    for r in rows:
        passes = sum(1 for m in MODEL_ORDER if r.get(f"{m}__overall_pass") == "PASS")
        key = {4: "All 4 pass", 0: "All 4 fail"}.get(passes, f"Mixed ({passes}/4 pass)")
        counts[key] += 1

    order = ["All 4 pass", "Mixed (3/4 pass)", "Mixed (2/4 pass)", "Mixed (1/4 pass)", "All 4 fail"]
    labels = [k for k in order if k in counts]
    values = [counts[k] for k in labels]
    total = sum(values)
    # Ordered good -> bad, so a luminance-separated good→bad palette matches the
    # data's own meaning (not a rainbow on a nominal axis). Direct labels carry
    # the exact numbers; color is secondary.
    seg_colors = ["#0f766e", "#7fc6bd", "#d9c98a", "#d98a5a", "#9d174d"][:len(labels)]

    fig, ax = plt.subplots(figsize=(12, 2.6))
    ts.strip_axes(ax)
    left = 0
    for lbl, v, c in zip(labels, values, seg_colors):
        ax.barh(0, v, left=left, color=c, height=0.5)
        frac = v / total
        txt_color = "white" if c in ("#0f766e", "#9d174d", "#d98a5a") else ts.INK
        ax.text(left + v / 2, 0, f"{lbl}\n{v}  ({frac*100:.1f}%)",
                ha="center", va="center", color=txt_color, fontsize=9.5)
        left += v
    ax.set_xlim(0, total)
    ax.set_ylim(-0.6, 0.6)
    ax.set_xticks([])  # the segment labels carry the values; the count axis is redundant
    ax.set_yticks([])
    ax.set_title(f"How many of the 4 models pass each item  ·  {total} items, DeepSeek-judged", pad=10)
    fig.tight_layout()
    fig.savefig(FIG / "10_item_agreement_donut.png")  # filename kept so article URLs are stable
    plt.close(fig)
    print("  10_item_agreement_donut.png")


# ---------- 11 — difficulty progression as a slopegraph ----------
def plot_difficulty_progression():
    rows = load_rows()
    diffs = ["easy", "medium", "hard"]
    by_diff = {d: [r for r in rows if r["difficulty"] == d] for d in diffs}

    series = {m: [pass_rate(by_diff[d], m) for d in diffs] for m in MODEL_ORDER}

    fig, ax = plt.subplots(figsize=(9, 5.4))
    ts.strip_axes(ax)
    x = [0, 1, 2]
    for m in MODEL_ORDER:
        ys = series[m]
        ax.plot(x, ys, color=ts.MODEL_COLORS[m], linewidth=2.0, marker="o", markersize=5)
        ax.text(-0.05, ys[0], f"{ys[0]:.0f}", ha="right", va="center",
                fontsize=9, color=ts.MODEL_COLORS[m])

    # Right-end labels: the three frontier models converge near 20–23, so spread
    # the label text apart by a minimum gap while the line endpoints stay true.
    gap = 2.8
    placed = []  # (label_y, model, true_value)
    for val, m in sorted((series[m][2], m) for m in MODEL_ORDER):
        y = val if not placed else max(val, placed[-1][0] + gap)
        placed.append((y, m, val))
    for y, m, val in placed:
        ax.text(2.05, y, f"  {MODEL_LABELS[m]}  ·  {val:.0f}", ha="left", va="center",
                fontsize=9.5, color=ts.MODEL_COLORS[m])

    ax.set_xlim(-0.35, 3.1)
    ax.set_ylim(0, max(max(v) for v in series.values()) + 6)
    ax.set_xticks(x)
    ax.set_xticklabels(["easy", "medium", "hard"], fontsize=11)
    ax.set_ylabel("Pass rate (%)")
    ax.set_title("Pass rate by difficulty — easy → hard")
    fig.tight_layout()
    fig.savefig(FIG / "11_difficulty_progression.png")
    plt.close(fig)
    print("  11_difficulty_progression.png")


def main():
    ts.apply_base()
    print("Generating data-story figures in", FIG)
    plot_model_x_language()
    plot_model_x_category()
    plot_graded_distribution()
    plot_item_agreement_bar()
    plot_difficulty_progression()
    print("Done.")


if __name__ == "__main__":
    main()
