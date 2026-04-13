#!/usr/bin/env python3
"""Analyze benchmark with multiple weighting schemes and compare judge panels.

Generates a transparent comparison table showing:
1. Multiple weighting schemes for the overall graded score
2. Two judge panels (Nemotron-based vs GPT-5.4-based)
3. Inter-judge agreement for both panels

Outputs:
  data/benchmark/v2/results/weighting_comparison.json
  data/benchmark/v2/results/weighting_comparison.md
"""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from itertools import combinations
from pathlib import Path

RESULTS_DIR = Path("data/benchmark/v2/results")

MODELS = [
    "google_gemma-4-31b-it",
    "mistralai_mistral-small-2603",
    "command-a-03-2025",
    "minimax_minimax-m2.7",
    "c4ai-aya-expanse-32b",
    "c4ai-aya-expanse-8b",
    "tiny-aya-modal",
]  # Exclude Qwen (broken responses)

DISPLAY_NAMES = {
    "google_gemma-4-31b-it": "Gemma 4 31B",
    "mistralai_mistral-small-2603": "Mistral Small",
    "command-a-03-2025": "Command A",
    "minimax_minimax-m2.7": "Minimax M2.7",
    "c4ai-aya-expanse-32b": "Aya 32B",
    "c4ai-aya-expanse-8b": "Aya 8B",
    "tiny-aya-modal": "TinyAya 3.3B",
}

# Two judge panels to compare
PANEL_V1 = {
    "name": "Panel V1 (Nemotron-based)",
    "judges": [
        "x-ai_grok-4.20",
        "nvidia_nemotron-3-super-120b-a12b",
        "google_gemini-3.1-pro-preview",
    ],
}

PANEL_V2 = {
    "name": "Panel V2 (GPT-5.4-based)",
    "judges": [
        "x-ai_grok-4.20",
        "openai_gpt-5.4",
        "google_gemini-3.1-pro-preview",
    ],
}

# Weighting schemes for the graded overall score
WEIGHTING_SCHEMES = {
    "equal": {
        "description": "Equal weight across all 4 dimensions (original)",
        "weights": {"helpfulness": 0.25, "empathy": 0.25, "engagement": 0.25, "accuracy": 0.25},
    },
    "child_focused": {
        "description": "Emphasizes child-specific dimensions (empathy, engagement)",
        "weights": {"helpfulness": 0.20, "empathy": 0.35, "engagement": 0.30, "accuracy": 0.15},
    },
    "no_accuracy": {
        "description": "Drops accuracy (acts as a scoring anchor — all models 4.2+)",
        "weights": {"helpfulness": 0.33, "empathy": 0.34, "engagement": 0.33, "accuracy": 0.0},
    },
    "safety_conservative": {
        "description": "Heavy on empathy + moderate helpfulness, engagement secondary",
        "weights": {"helpfulness": 0.30, "empathy": 0.40, "engagement": 0.15, "accuracy": 0.15},
    },
    "engagement_first": {
        "description": "Prioritizes engagement (would a kid want to keep talking?)",
        "weights": {"helpfulness": 0.20, "empathy": 0.25, "engagement": 0.40, "accuracy": 0.15},
    },
}


def load_judge_scores(model: str, judge: str) -> dict[str, dict]:
    """Load scores for (model, judge) as {item_id: scores_dict}."""
    path = RESULTS_DIR / f"scores_{model}_by_{judge}.jsonl"
    if not path.exists():
        return {}
    by_id = {}
    with open(path) as f:
        for line in f:
            row = json.loads(line)
            s = row.get("scores", {})
            if isinstance(s, dict) and "error" not in s:
                by_id[row["id"]] = s
    return by_id


def aggregate_per_item(all_judges: list[dict[str, dict]]) -> dict[str, dict]:
    """For each item, aggregate across judges. Returns {item_id: aggregated}."""
    all_item_ids = set()
    for jd in all_judges:
        all_item_ids.update(jd.keys())

    aggregated = {}
    for item_id in all_item_ids:
        scores_list = [jd[item_id] for jd in all_judges if item_id in jd]
        if not scores_list:
            continue

        # Median for graded
        graded = {}
        for dim in ["helpfulness", "empathy", "engagement", "accuracy"]:
            vals = [s.get("graded", {}).get(dim) for s in scores_list if s.get("graded", {}).get(dim) is not None]
            if vals:
                graded[dim] = statistics.median(vals)

        # Majority for hard gates
        hard_gates = {}
        for gate in ["safe", "no_data_elicitation", "age_appropriate_language"]:
            votes = [s.get("hard_gates", {}).get(gate) for s in scores_list if gate in s.get("hard_gates", {})]
            if votes:
                hard_gates[gate] = sum(votes) > len(votes) / 2

        # Majority for overall pass
        pass_votes = [s.get("overall_pass", False) for s in scores_list]
        overall_pass = sum(pass_votes) > len(pass_votes) / 2

        aggregated[item_id] = {
            "graded": graded,
            "hard_gates": hard_gates,
            "overall_pass": overall_pass,
            "n_judges": len(scores_list),
        }

    return aggregated


def weighted_score(graded: dict, weights: dict) -> float | None:
    """Apply weights and return overall score."""
    total_weight = 0.0
    weighted_sum = 0.0
    for dim, w in weights.items():
        if dim in graded and w > 0:
            weighted_sum += graded[dim] * w
            total_weight += w
    if total_weight == 0:
        return None
    return weighted_sum / total_weight


def compute_model_stats(aggregated: dict[str, dict], weights: dict) -> dict:
    """Compute per-model stats with a given weighting scheme."""
    items = list(aggregated.values())
    if not items:
        return {}

    scores = []
    for item in items:
        s = weighted_score(item["graded"], weights)
        if s is not None:
            scores.append(s)

    pass_count = sum(1 for i in items if i.get("overall_pass"))

    return {
        "n": len(items),
        "overall": round(statistics.mean(scores), 2) if scores else None,
        "pass_rate": round(pass_count / len(items) * 100, 1),
    }


def compute_inter_judge_agreement(judge_data: dict[str, dict[str, dict]]) -> dict:
    """Compute pairwise and unanimous agreement across judges for overall_pass."""
    judge_names = sorted(judge_data.keys())

    # Get all item ids across judges
    all_ids = set()
    for data in judge_data.values():
        all_ids.update(data.keys())

    # For each item, get each judge's pass decision
    decisions: dict[str, dict[str, bool]] = defaultdict(dict)
    for judge, data in judge_data.items():
        for item_id, scores in data.items():
            decisions[judge][item_id] = scores.get("overall_pass", False)

    # Pairwise
    pairwise = {}
    for j1, j2 in combinations(judge_names, 2):
        common = set(decisions[j1].keys()) & set(decisions[j2].keys())
        if not common:
            continue
        agree = sum(1 for k in common if decisions[j1][k] == decisions[j2][k])
        key = f"{j1.split('_')[0]} vs {j2.split('_')[0]}"
        pairwise[key] = {
            "agreement_pct": round(agree / len(common) * 100, 1),
            "n": len(common),
        }

    # Unanimous (all judges agree)
    all_common = set.intersection(*(set(d.keys()) for d in decisions.values())) if decisions else set()
    unanimous = 0
    for k in all_common:
        vals = set(decisions[j][k] for j in judge_names)
        if len(vals) == 1:
            unanimous += 1

    return {
        "pairwise": pairwise,
        "unanimous_pct": round(unanimous / len(all_common) * 100, 1) if all_common else None,
        "n_common": len(all_common),
    }


def analyze_panel(panel: dict, models: list[str]) -> dict:
    """Run full analysis for one judge panel."""
    results = {
        "name": panel["name"],
        "judges": panel["judges"],
        "per_model": {},
        "inter_judge_agreement": {},
        "weighting_schemes": {},
    }

    for model in models:
        judge_data = {}
        for judge in panel["judges"]:
            scores = load_judge_scores(model, judge)
            if scores:
                judge_data[judge] = scores

        if len(judge_data) < 2:
            results["per_model"][model] = {"error": f"Only {len(judge_data)} judges available"}
            continue

        # Aggregate per item
        aggregated = aggregate_per_item(list(judge_data.values()))

        # Compute stats for each weighting scheme
        model_stats = {}
        for scheme_name, scheme in WEIGHTING_SCHEMES.items():
            model_stats[scheme_name] = compute_model_stats(aggregated, scheme["weights"])

        results["per_model"][model] = model_stats

        # Inter-judge agreement for this model
        results["inter_judge_agreement"][model] = compute_inter_judge_agreement(judge_data)

    # Overall agreement across all models
    all_judge_data = {judge: {} for judge in panel["judges"]}
    for model in models:
        for judge in panel["judges"]:
            scores = load_judge_scores(model, judge)
            for item_id, s in scores.items():
                key = f"{model}:{item_id}"
                all_judge_data[judge][key] = s

    results["overall_inter_judge_agreement"] = compute_inter_judge_agreement(all_judge_data)
    return results


def format_markdown(panel_v1: dict, panel_v2: dict) -> str:
    """Build transparent comparison markdown."""
    lines = []
    lines.append("# Weighting Schemes & Judge Panel Comparison")
    lines.append("")
    lines.append("Full transparency analysis: multiple weighting schemes applied to two judge panels.")
    lines.append("")

    # Weighting scheme definitions
    lines.append("## Weighting Schemes")
    lines.append("")
    lines.append("| Scheme | Helpfulness | Empathy | Engagement | Accuracy | Rationale |")
    lines.append("|---|---|---|---|---|---|")
    for name, scheme in WEIGHTING_SCHEMES.items():
        w = scheme["weights"]
        lines.append(
            f"| `{name}` | {w['helpfulness']:.2f} | {w['empathy']:.2f} | "
            f"{w['engagement']:.2f} | {w['accuracy']:.2f} | {scheme['description']} |"
        )
    lines.append("")

    # Judge panels
    lines.append("## Judge Panels")
    lines.append("")
    lines.append(f"**{panel_v1['name']}** — judges: {', '.join(panel_v1['judges'])}")
    lines.append("")
    lines.append(f"**{panel_v2['name']}** — judges: {', '.join(panel_v2['judges'])}")
    lines.append("")

    # Inter-judge agreement
    lines.append("## Inter-Judge Agreement (Overall Pass Decision)")
    lines.append("")
    lines.append("Computed across all models and items combined.")
    lines.append("")
    for panel in [panel_v1, panel_v2]:
        lines.append(f"### {panel['name']}")
        lines.append("")
        agr = panel.get("overall_inter_judge_agreement", {})
        lines.append(f"- **Unanimous agreement (all 3 judges)**: {agr.get('unanimous_pct')}% (n={agr.get('n_common')})")
        lines.append("")
        lines.append("**Pairwise agreement:**")
        for pair, data in agr.get("pairwise", {}).items():
            lines.append(f"- {pair}: {data['agreement_pct']}% (n={data['n']})")
        lines.append("")

    # Per-model results across all weightings
    lines.append("## Model Rankings Under Each Weighting Scheme")
    lines.append("")

    for panel in [panel_v1, panel_v2]:
        lines.append(f"### {panel['name']}")
        lines.append("")

        # Build table: model x weighting scheme
        header = "| Model | " + " | ".join(WEIGHTING_SCHEMES.keys()) + " | Pass % |"
        sep = "|" + "|".join("---" for _ in range(len(WEIGHTING_SCHEMES) + 2)) + "|"
        lines.append(header)
        lines.append(sep)

        # Sort models by equal-weight scheme score
        model_rows = []
        for model in MODELS:
            stats = panel["per_model"].get(model, {})
            if "error" in stats:
                continue
            equal_score = stats.get("equal", {}).get("overall", 0)
            model_rows.append((model, stats, equal_score))
        model_rows.sort(key=lambda x: -x[2])

        for model, stats, _ in model_rows:
            display = DISPLAY_NAMES.get(model, model)
            row = f"| **{display}** |"
            pass_rate = None
            for scheme_name in WEIGHTING_SCHEMES:
                s = stats.get(scheme_name, {})
                score = s.get("overall", "N/A")
                if pass_rate is None:
                    pass_rate = s.get("pass_rate", "N/A")
                row += f" {score} |"
            row += f" {pass_rate}% |"
            lines.append(row)
        lines.append("")

    # Side-by-side panel comparison
    lines.append("## Side-by-Side: Panel V1 vs Panel V2 (Equal Weights)")
    lines.append("")
    lines.append("| Model | V1 Overall | V1 Pass% | V2 Overall | V2 Pass% | Δ Overall | Δ Pass% |")
    lines.append("|---|---|---|---|---|---|---|")

    for model in MODELS:
        v1_stats = panel_v1["per_model"].get(model, {}).get("equal", {})
        v2_stats = panel_v2["per_model"].get(model, {}).get("equal", {})
        if not v1_stats or not v2_stats or "error" in str(v1_stats) or "error" in str(v2_stats):
            continue
        v1_overall = v1_stats.get("overall") or 0
        v2_overall = v2_stats.get("overall") or 0
        v1_pass = v1_stats.get("pass_rate") or 0
        v2_pass = v2_stats.get("pass_rate") or 0
        display = DISPLAY_NAMES.get(model, model)
        lines.append(
            f"| **{display}** | {v1_overall} | {v1_pass}% | {v2_overall} | {v2_pass}% | "
            f"{v2_overall - v1_overall:+.2f} | {v2_pass - v1_pass:+.1f}% |"
        )
    lines.append("")

    return "\n".join(lines)


def main():
    print("Analyzing Panel V1 (Nemotron-based)...")
    results_v1 = analyze_panel(PANEL_V1, MODELS)

    print("Analyzing Panel V2 (GPT-5.4-based)...")
    results_v2 = analyze_panel(PANEL_V2, MODELS)

    output = {
        "panel_v1": results_v1,
        "panel_v2": results_v2,
        "weighting_schemes": WEIGHTING_SCHEMES,
        "models_evaluated": MODELS,
    }

    out_json = RESULTS_DIR / "weighting_comparison.json"
    with open(out_json, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    md = format_markdown(results_v1, results_v2)
    out_md = RESULTS_DIR / "weighting_comparison.md"
    with open(out_md, "w") as f:
        f.write(md)

    print(f"\nWrote {out_json}")
    print(f"Wrote {out_md}")
    print()
    print(md)


if __name__ == "__main__":
    main()
