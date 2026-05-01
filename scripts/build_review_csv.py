#!/usr/bin/env python3
"""Build a wide CSV of the 713-item balanced subset for blog review.

For each (item, model) pair: prompt context, model response, DeepSeek judge score.

Usage:
    python scripts/build_review_csv.py
    python scripts/build_review_csv.py --out review.csv
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

V2_FINAL = Path("data/benchmark/v2/final/v2_final.jsonl")
RESULTS_ML = Path("data/benchmark/v2/results_multilingual")
BALANCED_IDS = RESULTS_ML / "balanced_subset_ids.json"

MODELS = [
    "command-a-03-2025",
    "google_gemma-4-31b-it",
    "tiny-aya-modal",
    "c4ai-aya-expanse-32b",
]
JUDGE = "deepseek_deepseek-v4-flash"

LANGUAGE_NAMES = {
    "ar":"Arabic","cs":"Czech","de":"German","en":"English","es":"Spanish",
    "fr":"French","hi":"Hindi","id":"Indonesian","it":"Italian","ja":"Japanese",
    "ko":"Korean","nl":"Dutch","pl":"Polish","pt":"Portuguese","ro":"Romanian",
    "ru":"Russian","sw":"Swahili","te":"Telugu","th":"Thai","tr":"Turkish",
    "uk":"Ukrainian","vi":"Vietnamese","zh":"Chinese",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=Path("data/benchmark/v2/review/balanced_review.csv"))
    args = ap.parse_args()

    with open(BALANCED_IDS) as f:
        balanced = set(json.load(f))

    items = {}
    with open(V2_FINAL) as f:
        for line in f:
            it = json.loads(line)
            if it["id"] in balanced:
                items[it["id"]] = it

    # Load all 4 models' responses
    responses: dict[str, dict[str, dict]] = {m: {} for m in MODELS}
    for model in MODELS:
        path = RESULTS_ML / f"responses_{model}.jsonl"
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if r["id"] in balanced:
                    responses[model][r["id"]] = r

    # Load DeepSeek scores
    scores: dict[str, dict[str, dict]] = {m: {} for m in MODELS}
    for model in MODELS:
        path = RESULTS_ML / f"scores_{model}_by_{JUDGE}.jsonl"
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if r["id"] in balanced:
                    s = r.get("scores", {})
                    if isinstance(s, dict) and "error" not in s:
                        scores[model][r["id"]] = s

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id", "language", "language_name", "category", "difficulty",
        "child_utterance", "context_window",
        "must_pass_criteria", "reference_response",
    ]
    for model in MODELS:
        m = model.replace("/", "_")
        fieldnames += [
            f"{m}__response",
            f"{m}__hard_gates",
            f"{m}__helpfulness",
            f"{m}__empathy",
            f"{m}__engagement",
            f"{m}__accuracy",
            f"{m}__overall_pass",
            f"{m}__reasoning",
        ]

    rows_written = 0
    rows_skipped = 0
    with open(args.out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for iid in sorted(balanced, key=lambda x: (items[x].get("language",""), x)):
            it = items[iid]
            p = it.get("prompt") or {}
            ctx = p.get("context_window") or []
            ctx_str = " | ".join(f"[{c.get('role','?')}] {c.get('message','')}" for c in ctx)
            row = {
                "id": iid,
                "language": it.get("language",""),
                "language_name": LANGUAGE_NAMES.get(it.get("language",""), ""),
                "category": it.get("category",""),
                "difficulty": it.get("difficulty",""),
                "child_utterance": p.get("child_utterance",""),
                "context_window": ctx_str,
                "must_pass_criteria": "\n".join(f"• {c}" for c in it.get("must_pass_criteria",[])),
                "reference_response": it.get("reference_response",""),
            }
            ok = True
            for model in MODELS:
                m = model.replace("/", "_")
                resp = responses[model].get(iid, {})
                sc = scores[model].get(iid)
                if not sc:
                    ok = False
                    break
                graded = sc.get("graded", {})
                hard = sc.get("hard_gates", {})
                hard_str = ", ".join(f"{k}={'pass' if v else 'fail'}" for k, v in hard.items())
                row[f"{m}__response"] = resp.get("model_response", "")
                row[f"{m}__hard_gates"] = hard_str
                row[f"{m}__helpfulness"] = graded.get("helpfulness", "")
                row[f"{m}__empathy"] = graded.get("empathy", "")
                row[f"{m}__engagement"] = graded.get("engagement", "")
                row[f"{m}__accuracy"] = graded.get("accuracy", "")
                row[f"{m}__overall_pass"] = "PASS" if sc.get("overall_pass") else "FAIL"
                row[f"{m}__reasoning"] = sc.get("reasoning", "")
            if ok:
                writer.writerow(row)
                rows_written += 1
            else:
                rows_skipped += 1

    print(f"Wrote {rows_written} rows, skipped {rows_skipped} (incomplete) → {args.out}")
    if rows_skipped:
        print("  (skipped rows are items missing one or more model scores)")


if __name__ == "__main__":
    main()
