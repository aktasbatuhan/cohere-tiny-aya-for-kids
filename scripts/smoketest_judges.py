#!/usr/bin/env python3
"""Quickly smoke-test candidate judge models via OpenRouter.

Sends the same judge prompt to each candidate on a small sample of
real (item, model_response) pairs from the multilingual results, then
reports:
  - Latency per call
  - JSON parse success
  - Score output preview

Usage:
  python scripts/smoketest_judges.py --candidates qwen/qwen3.6-plus xiaomi/mimo-v2-omni
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from evaluate_v2 import (  # type: ignore
    build_judge_prompt,
    load_v2_multilingual_items,
    openrouter_chat,
    _parse_judge_response,
)

RESULTS_ML = Path("data/benchmark/v2/results_multilingual")


def load_sample_pairs(n: int, seed: int = 42) -> list[tuple[dict, str]]:
    """Return a stratified sample of (item, model_response) for smoke testing.

    Mixes languages and difficulties to make sure slow paths get hit.
    """
    items = load_v2_multilingual_items()
    items_by_id = {i["id"]: i for i in items}

    # Pick responses from Gemma (strong model, diverse) and TinyAya (weaker, different shape)
    resp_files = [
        RESULTS_ML / "responses_google_gemma-4-31b-it.jsonl",
        RESULTS_ML / "responses_tiny-aya-modal.jsonl",
    ]
    pairs: list[tuple[dict, str]] = []
    for rf in resp_files:
        if not rf.exists():
            continue
        with open(rf) as f:
            for line in f:
                r = json.loads(line)
                item = items_by_id.get(r["id"])
                if not item:
                    continue
                pairs.append((item, r["model_response"]))

    rng = random.Random(seed)
    rng.shuffle(pairs)

    # Stratify — one from each of these language buckets if possible
    buckets_order = ["en", "tr", "es", "ja", "ar", "hi", "zh", "sw", "ro", "te"]
    chosen: list[tuple[dict, str]] = []
    seen_langs: dict[str, int] = {}
    for item, resp in pairs:
        lang = item.get("language", "en")
        if lang in buckets_order and seen_langs.get(lang, 0) < 1:
            chosen.append((item, resp))
            seen_langs[lang] = seen_langs.get(lang, 0) + 1
        if len(chosen) >= n:
            break
    # Pad if we need more
    for p in pairs:
        if len(chosen) >= n:
            break
        if p not in chosen:
            chosen.append(p)
    return chosen[:n]


def run_candidate(model: str, pairs: list[tuple[dict, str]]) -> dict:
    latencies: list[float] = []
    parse_ok = 0
    parse_fail = 0
    samples: list[dict] = []

    print(f"\n=== {model} ===")
    for i, (item, resp) in enumerate(pairs, 1):
        prompt = build_judge_prompt(item, resp)
        t0 = time.perf_counter()
        raw = openrouter_chat(
            model,
            [{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=2048,
        )
        dt = time.perf_counter() - t0
        latencies.append(dt)

        parsed = _parse_judge_response(raw)
        ok = "error" not in parsed and any(k in parsed for k in ("hard_gates", "graded", "overall_pass"))
        if ok:
            parse_ok += 1
            status = "OK"
        else:
            parse_fail += 1
            status = "FAIL"

        samples.append({
            "lang": item.get("language"),
            "item_id": item["id"][:16],
            "latency_s": round(dt, 2),
            "parse": status,
            "error_snippet": (raw if not ok else "")[:120],
            "overall_pass": parsed.get("overall_pass") if ok else None,
            "gates": list((parsed.get("hard_gates") or {}).keys()) if ok else None,
            "graded_keys": list((parsed.get("graded") or {}).keys()) if ok else None,
        })
        print(f"  [{i}/{len(pairs)}] lang={item.get('language'):>2}  {dt:5.1f}s  {status}")

    return {
        "model": model,
        "n": len(latencies),
        "parse_ok": parse_ok,
        "parse_fail": parse_fail,
        "parse_rate": round(parse_ok / len(latencies) * 100, 1) if latencies else 0,
        "latency_median_s": round(statistics.median(latencies), 2) if latencies else None,
        "latency_mean_s": round(statistics.mean(latencies), 2) if latencies else None,
        "latency_max_s": round(max(latencies), 2) if latencies else None,
        "samples": samples,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--candidates", nargs="+", required=True, help="OpenRouter model IDs to test")
    parser.add_argument("--n", type=int, default=6, help="Number of pairs per candidate (default 6)")
    args = parser.parse_args()

    pairs = load_sample_pairs(args.n)
    print(f"Loaded {len(pairs)} sample pairs")
    print("Sample langs:", [p[0].get("language") for p in pairs])

    results = [run_candidate(m, pairs) for m in args.candidates]

    # Summary
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Model':<40} {'N':>3} {'Parse%':>8} {'Med(s)':>8} {'Mean(s)':>8} {'Max(s)':>8}")
    for r in results:
        print(f"{r['model']:<40} {r['n']:>3} {r['parse_rate']:>7.1f}% "
              f"{r['latency_median_s']:>8.2f} {r['latency_mean_s']:>8.2f} {r['latency_max_s']:>8.2f}")

    # Save
    out = Path("data/benchmark/v2/results_multilingual/judge_smoketest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
