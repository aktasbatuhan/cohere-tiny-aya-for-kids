#!/usr/bin/env python3
"""Pilot evaluation: full 3-judge panel on a stratified sample.

Produces a small, representative sample (default 10 items per language
per model), runs all 3 judges, and reports:
  - Actual cost per judge (token counts from OpenRouter response if available)
  - Inter-judge agreement
  - Parse success rate
  - Suspicious patterns (all passes, all fails, flat scores)
  - Sample-level leaderboard

Lets you decide whether to pay for the full run.

Usage:
  python scripts/run_judge_pilot.py --per-lang 5 --models c4ai-aya-expanse-8b tiny-aya-modal
  python scripts/run_judge_pilot.py --resume
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluate_v2 import (  # type: ignore
    JUDGE_MODELS,
    build_judge_prompt,
    load_v2_multilingual_items,
    openrouter_chat,
    _parse_judge_response,
)

PILOT_DIR = Path("data/benchmark/v2/results_multilingual/pilot")
RESPONSES_ML = Path("data/benchmark/v2/results_multilingual")
PILOT_SAMPLE = PILOT_DIR / "pilot_sample_ids.json"


def pick_sample(items: list[dict], per_lang: int, seed: int = 42) -> list[str]:
    """Stratified sample: `per_lang` items per language."""
    rng = random.Random(seed)
    by_lang: dict[str, list[dict]] = defaultdict(list)
    for i in items:
        by_lang[i["language"]].append(i)

    chosen: list[str] = []
    for lang, lang_items in sorted(by_lang.items()):
        # Stratify by difficulty too
        by_diff: dict[str, list[dict]] = defaultdict(list)
        for i in lang_items:
            by_diff[i.get("difficulty", "medium")].append(i)
        pool = []
        for diff, diff_items in by_diff.items():
            rng.shuffle(diff_items)
            # Take proportional slice up to per_lang total
            pool.extend(diff_items)
        rng.shuffle(pool)
        chosen.extend(i["id"] for i in pool[:per_lang])
    return chosen


def load_responses(model: str) -> dict[str, dict]:
    """Load generation responses keyed by item_id."""
    path = RESPONSES_ML / f"responses_{model.replace('/', '_')}.jsonl"
    out: dict[str, dict] = {}
    if path.exists():
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                out[r["id"]] = r
    return out


def run_judge(model: str, judge: str, items_by_id: dict[str, dict], responses: dict[str, dict], target_ids: list[str]) -> dict:
    """Run one judge on a sample for one generation model."""
    judge_tag = judge.replace("/", "_")
    score_file = PILOT_DIR / f"scores_{model.replace('/', '_')}_by_{judge_tag}.jsonl"
    score_file.parent.mkdir(parents=True, exist_ok=True)

    existing: dict[str, dict] = {}
    if score_file.exists():
        with open(score_file) as f:
            for line in f:
                r = json.loads(line)
                existing[r["id"]] = r

    pending = [tid for tid in target_ids if tid not in existing]
    print(f"  [{judge}/{model}] pending: {len(pending)}, cached: {len(existing)}")

    latencies: list[float] = []
    parse_ok = 0
    parse_fail = 0

    with open(score_file, "a") as f:
        for i, tid in enumerate(pending, 1):
            item = items_by_id.get(tid)
            resp = responses.get(tid)
            if not item or not resp:
                continue
            prompt = build_judge_prompt(item, resp["model_response"])
            t0 = time.perf_counter()
            raw = openrouter_chat(
                judge,
                [{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=2048,
            )
            dt = time.perf_counter() - t0
            latencies.append(dt)

            parsed = _parse_judge_response(raw)
            ok = isinstance(parsed, dict) and "error" not in parsed and any(
                k in parsed for k in ("hard_gates", "graded", "overall_pass")
            )
            if ok:
                parse_ok += 1
            else:
                parse_fail += 1

            row = {
                "id": tid,
                "model": model,
                "judge": judge,
                "language": item.get("language"),
                "category": item.get("category"),
                "difficulty": item.get("difficulty"),
                "latency_s": round(dt, 2),
                "scores": parsed,
                "raw_response": raw[:1500],
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            f.flush()

            if i % 10 == 0 or i == 1 or i == len(pending):
                print(f"    [{i}/{len(pending)}] {item.get('language')} {dt:5.1f}s {'OK' if ok else 'FAIL'}")

    # Recompute final counts across both cached + new
    all_scored = {**existing}
    if score_file.exists():
        with open(score_file) as f:
            for line in f:
                r = json.loads(line)
                all_scored[r["id"]] = r

    return {
        "judge": judge,
        "model": model,
        "calls_this_run": len(latencies),
        "total_scored": len(all_scored),
        "parse_ok_this_run": parse_ok,
        "parse_fail_this_run": parse_fail,
        "latency_median": round(statistics.median(latencies), 2) if latencies else None,
        "latency_mean": round(statistics.mean(latencies), 2) if latencies else None,
        "score_file": str(score_file),
    }


def analyze_pilot(models: list[str], judges: list[str]) -> dict:
    """Read pilot score files and produce analysis."""
    # Per-judge parse rate and score distribution
    analysis: dict = {"per_judge": {}, "per_model": {}, "inter_judge": {}}

    # Load all pilot scores
    all_scores: dict[str, dict] = {}  # keyed by (model, item_id, judge)
    for model in models:
        for judge in judges:
            path = PILOT_DIR / f"scores_{model.replace('/', '_')}_by_{judge.replace('/', '_')}.jsonl"
            if not path.exists():
                continue
            with open(path) as f:
                for line in f:
                    r = json.loads(line)
                    all_scores[(model, r["id"], judge)] = r

    # Per-judge stats
    for judge in judges:
        scores_for_judge = [r for (m, i, j), r in all_scores.items() if j == judge]
        valid = [r for r in scores_for_judge if isinstance(r.get("scores"), dict) and "error" not in r["scores"]]
        passes = sum(1 for r in valid if r["scores"].get("overall_pass"))
        helpfulness = [r["scores"].get("graded", {}).get("helpfulness") for r in valid]
        helpfulness = [h for h in helpfulness if h is not None]

        # Flat-score detection: are all graded dims identical for >20% of items?
        flat_count = 0
        for r in valid:
            g = r["scores"].get("graded", {})
            vals = [v for v in g.values() if isinstance(v, (int, float))]
            if len(vals) >= 3 and len(set(vals)) == 1:
                flat_count += 1

        analysis["per_judge"][judge] = {
            "n_total": len(scores_for_judge),
            "n_valid": len(valid),
            "parse_rate": round(len(valid) / len(scores_for_judge) * 100, 1) if scores_for_judge else 0,
            "pass_rate": round(passes / len(valid) * 100, 1) if valid else 0,
            "flat_score_rate": round(flat_count / len(valid) * 100, 1) if valid else 0,
            "helpfulness_mean": round(statistics.mean(helpfulness), 2) if helpfulness else None,
            "helpfulness_median": round(statistics.median(helpfulness), 2) if helpfulness else None,
        }

    # Inter-judge agreement
    # For each (model, item_id), collect each judge's overall_pass
    by_item: dict[tuple, dict[str, bool]] = defaultdict(dict)
    for (m, i, j), r in all_scores.items():
        s = r.get("scores", {})
        if isinstance(s, dict) and "error" not in s:
            by_item[(m, i)][j] = bool(s.get("overall_pass", False))

    # Pairwise agreement across all (model, item) pairs where both judges scored
    for j1, j2 in combinations(judges, 2):
        common = [d for d in by_item.values() if j1 in d and j2 in d]
        if not common:
            continue
        agree = sum(1 for d in common if d[j1] == d[j2])
        analysis["inter_judge"][f"{j1} vs {j2}"] = {
            "n": len(common),
            "agreement_pct": round(agree / len(common) * 100, 1),
        }

    # Unanimous
    all3 = [d for d in by_item.values() if all(j in d for j in judges)]
    if all3:
        unanimous = sum(1 for d in all3 if len(set(d[j] for j in judges)) == 1)
        analysis["inter_judge"]["unanimous"] = {
            "n": len(all3),
            "agreement_pct": round(unanimous / len(all3) * 100, 1),
        }

    # Per-model leaderboard (median graded mean across judges)
    by_model_item: dict[tuple, list[float]] = defaultdict(list)
    for (m, i, j), r in all_scores.items():
        s = r.get("scores", {})
        if not isinstance(s, dict) or "error" in s:
            continue
        g = s.get("graded", {})
        vals = [v for v in g.values() if isinstance(v, (int, float))]
        if vals:
            by_model_item[(m, i)].append(statistics.mean(vals))

    per_model_scores: dict[str, list[float]] = defaultdict(list)
    per_model_passes: dict[str, list[bool]] = defaultdict(list)
    for (m, i), per_judge_means in by_model_item.items():
        per_model_scores[m].append(statistics.median(per_judge_means))
        # Majority vote for pass
        judges_for_item = by_item.get((m, i), {})
        if judges_for_item:
            votes = list(judges_for_item.values())
            per_model_passes[m].append(sum(votes) > len(votes) / 2)

    for m in models:
        scores = per_model_scores.get(m, [])
        passes = per_model_passes.get(m, [])
        analysis["per_model"][m] = {
            "n_items": len(scores),
            "median_graded": round(statistics.median(scores), 2) if scores else None,
            "mean_graded": round(statistics.mean(scores), 2) if scores else None,
            "pass_rate": round(sum(passes) / len(passes) * 100, 1) if passes else None,
        }

    return analysis


def format_report(analysis: dict) -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("PILOT REPORT")
    lines.append("=" * 70)

    lines.append("\n## Judge quality")
    lines.append(f"{'Judge':<45} {'Parse%':>8} {'Pass%':>8} {'Flat%':>7} {'Help-med':>9}")
    for judge, s in analysis["per_judge"].items():
        lines.append(f"{judge:<45} {s['parse_rate']:>7.1f}% {s['pass_rate']:>7.1f}% {s['flat_score_rate']:>6.1f}% {str(s['helpfulness_median']):>9}")

    lines.append("\n## Inter-judge agreement (overall_pass)")
    for pair, s in analysis["inter_judge"].items():
        lines.append(f"  {pair}: {s['agreement_pct']}% (n={s['n']})")

    lines.append("\n## Per-model leaderboard (pilot sample only)")
    lines.append(f"{'Model':<35} {'n':>5} {'Graded (median)':>18} {'Pass%':>8}")
    rows = sorted(analysis["per_model"].items(), key=lambda kv: -(kv[1].get("mean_graded") or 0))
    for m, s in rows:
        lines.append(f"{m:<35} {s['n_items']:>5} {str(s['mean_graded']):>18} {str(s['pass_rate']):>7}%")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-lang", type=int, default=5, help="Items per language (default 5)")
    parser.add_argument("--models", nargs="+",
                        default=["c4ai-aya-expanse-8b", "tiny-aya-modal", "command-a-03-2025", "google/gemma-4-31b-it"],
                        help="Generation models to score")
    parser.add_argument("--judges", nargs="+", default=None,
                        help=f"Override judge list (default: {JUDGE_MODELS})")
    parser.add_argument("--analyze-only", action="store_true", help="Skip judging, just analyze existing pilot scores")
    parser.add_argument("--resume", action="store_true", help="Reuse existing pilot_sample_ids.json if present")
    parser.add_argument("--workers", type=int, default=1, help="Parallel workers per (model, judge) pair")
    args = parser.parse_args()

    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    judges = args.judges or JUDGE_MODELS

    items = load_v2_multilingual_items()
    items_by_id = {i["id"]: i for i in items}

    # Sample
    if args.resume and PILOT_SAMPLE.exists():
        with open(PILOT_SAMPLE) as f:
            target_ids = json.load(f)
        print(f"Resuming with cached sample: {len(target_ids)} items")
    else:
        target_ids = pick_sample(items, args.per_lang)
        with open(PILOT_SAMPLE, "w") as f:
            json.dump(target_ids, f)
        print(f"Wrote sample: {len(target_ids)} items across languages → {PILOT_SAMPLE}")

    lang_dist = Counter(items_by_id[tid]["language"] for tid in target_ids)
    print(f"Sample lang distribution: {dict(sorted(lang_dist.items()))}")

    per_model = len(target_ids)
    per_judge_per_model = per_model
    total_calls = per_model * len(args.models) * len(judges)
    print(f"\nTotal calls this pilot: {per_model} × {len(args.models)} models × {len(judges)} judges = {total_calls}\n")

    if not args.analyze_only:
        # Parallelize across (model, judge) pairs — independent work streams.
        from concurrent.futures import ThreadPoolExecutor, as_completed
        responses_cache = {m: load_responses(m) for m in args.models}

        tasks = []
        for model in args.models:
            responses = responses_cache.get(model) or {}
            if not responses:
                print(f"WARNING: no responses for {model}, skipping")
                continue
            for judge in judges:
                tasks.append((model, judge, responses))

        # Workers = number of (model, judge) pairs; each pair runs its own thread.
        with ThreadPoolExecutor(max_workers=max(args.workers, len(tasks))) as pool:
            futures = {
                pool.submit(run_judge, model, judge, items_by_id, responses, target_ids): (model, judge)
                for (model, judge, responses) in tasks
            }
            for fut in as_completed(futures):
                model, judge = futures[fut]
                try:
                    r = fut.result()
                    print(f"[done] {model} / {judge}: {r.get('calls_this_run', 0)} new, {r.get('total_scored', 0)} total")
                except Exception as e:
                    print(f"[err] {model} / {judge}: {e}")

    # Analyze
    analysis = analyze_pilot(args.models, judges)
    report = format_report(analysis)
    print("\n" + report)

    with open(PILOT_DIR / "pilot_report.json", "w") as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)
    with open(PILOT_DIR / "pilot_report.md", "w") as f:
        f.write(report)
    print(f"\nSaved report to {PILOT_DIR}/pilot_report.{{json,md}}")


if __name__ == "__main__":
    main()
