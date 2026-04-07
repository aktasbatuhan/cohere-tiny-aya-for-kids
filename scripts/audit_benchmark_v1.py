#!/usr/bin/env python3
"""Audit v1 benchmark data and classify each item as keep/rewrite/drop.

Outputs:
  data/benchmark/v2/audit_report.json   — per-item verdicts + summary stats
"""

from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path

INPUT = Path("data/benchmark/final_children_eval_benchmark.jsonl")
OUTPUT_DIR = Path("data/benchmark/v2")

GENERIC_MUST_PASS = {
    frozenset([
        "Responds clearly and helpfully",
        "Maintains child-safe tone and content",
        "Feels natural and supportive",
    ]),
}


def load_items() -> list[dict]:
    items = []
    with open(INPUT) as f:
        for line in f:
            items.append(json.loads(line))
    return items


def is_truncated(ref: str) -> bool:
    return ref.rstrip().endswith("...")


def is_generic_rubric(item: dict) -> bool:
    mp = item.get("rubric", {}).get("must_pass", [])
    return frozenset(mp) in GENERIC_MUST_PASS


def is_too_short(ref: str, min_chars: int = 30) -> bool:
    return len(ref.strip()) < min_chars


def normalize_request(text: str) -> str:
    return text.strip().lower().rstrip(".!?")


def audit(items: list[dict]) -> dict:
    # Build duplicate map
    request_groups: dict[str, list[int]] = defaultdict(list)
    for idx, item in enumerate(items):
        key = normalize_request(item["prompt"]["child_request"])
        request_groups[key].append(idx)

    duplicate_indices = set()
    for key, indices in request_groups.items():
        if len(indices) > 1:
            # Keep the first, mark rest as duplicates
            for i in indices[1:]:
                duplicate_indices.add(i)

    # Audit each item
    verdicts = []
    issues_counter = Counter()

    for idx, item in enumerate(items):
        issues = []
        ref = item.get("reference_response", "")
        bid = item["benchmark_id"]
        cat = item["category"]

        # Check truncated reference
        if is_truncated(ref):
            issues.append("truncated_reference")

        # Check generic rubric
        if is_generic_rubric(item):
            issues.append("generic_rubric")

        # Check short reference
        if is_too_short(ref):
            issues.append("short_reference")

        # Check duplicate
        if idx in duplicate_indices:
            issues.append("duplicate_request")

        # Check empty context window
        if not item["prompt"].get("context_window"):
            issues.append("no_context")

        # Check rubric notes are just copies of metadata
        rubric_notes = item.get("rubric", {}).get("notes", {})
        meta = item.get("metadata", {})
        if (rubric_notes.get("age_appropriateness") == meta.get("age_appropriateness_notes")
                and rubric_notes.get("safety") == meta.get("safety_notes")):
            issues.append("rubric_notes_duplicated_from_metadata")

        # Check if reference has non-English content (potential data issue)
        try:
            ref.encode("ascii")
        except UnicodeEncodeError:
            # Has non-ASCII — could be multilingual, flag for review
            if any(ord(c) > 0x024F for c in ref):  # Beyond Latin Extended
                issues.append("non_latin_reference")

        # Determine verdict
        critical = {"truncated_reference", "duplicate_request", "short_reference"}
        moderate = {"generic_rubric"}

        critical_issues = set(issues) & critical
        moderate_issues = set(issues) & moderate

        if len(critical_issues) >= 2:
            verdict = "drop"
        elif "truncated_reference" in critical_issues and "generic_rubric" in moderate_issues:
            verdict = "drop"
        elif critical_issues:
            verdict = "rewrite"
        elif moderate_issues:
            verdict = "rewrite"
        else:
            verdict = "keep"

        for issue in issues:
            issues_counter[issue] += 1

        verdicts.append({
            "benchmark_id": bid,
            "index": idx,
            "category": cat,
            "child_request": item["prompt"]["child_request"][:100],
            "reference_length": len(ref),
            "issues": issues,
            "verdict": verdict,
        })

    # Summary
    verdict_counts = Counter(v["verdict"] for v in verdicts)
    verdict_by_category = defaultdict(lambda: Counter())
    for v in verdicts:
        verdict_by_category[v["category"]][v["verdict"]] += 1

    # Items that survive (keep + rewrite)
    surviving_categories = Counter()
    for v in verdicts:
        if v["verdict"] != "drop":
            surviving_categories[v["category"]] += 1

    return {
        "summary": {
            "total_items": len(items),
            "verdicts": dict(verdict_counts),
            "issues": dict(issues_counter.most_common()),
            "verdicts_by_category": {
                cat: dict(counts) for cat, counts in sorted(verdict_by_category.items())
            },
            "surviving_by_category": dict(surviving_categories.most_common()),
        },
        "items": verdicts,
    }


def main():
    items = load_items()
    print(f"Loaded {len(items)} items from {INPUT}")

    report = audit(items)
    s = report["summary"]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "audit_report.json"
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print("AUDIT SUMMARY")
    print(f"{'='*50}")
    print(f"Total items: {s['total_items']}")
    print(f"\nVerdicts:")
    for v, count in sorted(s["verdicts"].items()):
        pct = count / s["total_items"] * 100
        print(f"  {v:>8}: {count:>4} ({pct:.1f}%)")

    print(f"\nIssues found:")
    for issue, count in s["issues"].items():
        print(f"  {issue}: {count}")

    print(f"\nVerdicts by category:")
    for cat, counts in sorted(s["verdicts_by_category"].items()):
        parts = ", ".join(f"{v}={c}" for v, c in sorted(counts.items()))
        print(f"  {cat}: {parts}")

    print(f"\nSurviving items by category (keep + rewrite):")
    for cat, count in s["surviving_by_category"].items():
        print(f"  {cat}: {count}")

    print(f"\nReport saved to {output_path}")


if __name__ == "__main__":
    main()
