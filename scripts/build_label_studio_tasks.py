#!/usr/bin/env python3
"""Build Label Studio task JSON from v2 benchmark + model responses.

One task per (item, model_response) pair — blind (model ID hidden from the
annotator but stored in `data.model_id` for later analysis).

Usage:
    python scripts/build_label_studio_tasks.py
    python scripts/build_label_studio_tasks.py --languages en tr ja
    python scripts/build_label_studio_tasks.py --per-lang 20  # stratified sample
"""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

V2_FINAL = Path("data/benchmark/v2/final/v2_final.jsonl")
RESULTS_ML = Path("data/benchmark/v2/results_multilingual")
OUT_DIR = Path("data/benchmark/v2/label_studio")

MODEL_FILES = {
    "command-a-03-2025": "responses_command-a-03-2025.jsonl",
    "google/gemma-4-31b-it": "responses_google_gemma-4-31b-it.jsonl",
    "tiny-aya-modal": "responses_tiny-aya-modal.jsonl",
    "c4ai-aya-expanse-32b": "responses_c4ai-aya-expanse-32b.jsonl",
}

LANGUAGE_META = {
    "ar": ("Arabic", "🇸🇦"),
    "cs": ("Czech", "🇨🇿"),
    "de": ("German", "🇩🇪"),
    "en": ("English", "🇬🇧"),
    "es": ("Spanish", "🇪🇸"),
    "fr": ("French", "🇫🇷"),
    "hi": ("Hindi", "🇮🇳"),
    "id": ("Indonesian", "🇮🇩"),
    "it": ("Italian", "🇮🇹"),
    "ja": ("Japanese", "🇯🇵"),
    "ko": ("Korean", "🇰🇷"),
    "nl": ("Dutch", "🇳🇱"),
    "pl": ("Polish", "🇵🇱"),
    "pt": ("Portuguese", "🇵🇹"),
    "ro": ("Romanian", "🇷🇴"),
    "ru": ("Russian", "🇷🇺"),
    "sw": ("Swahili", "🇰🇪"),
    "te": ("Telugu", "🇮🇳"),
    "th": ("Thai", "🇹🇭"),
    "tr": ("Turkish", "🇹🇷"),
    "uk": ("Ukrainian", "🇺🇦"),
    "vi": ("Vietnamese", "🇻🇳"),
    "zh": ("Chinese", "🇨🇳"),
}


def load_items() -> dict[str, dict]:
    items: dict[str, dict] = {}
    with open(V2_FINAL) as f:
        for line in f:
            i = json.loads(line)
            items[i["id"]] = i
    return items


def load_responses() -> dict[str, dict[str, dict]]:
    """Returns: {model: {item_id: response_row}}."""
    out: dict[str, dict[str, dict]] = {}
    for model, fname in MODEL_FILES.items():
        path = RESULTS_ML / fname
        rows: dict[str, dict] = {}
        if not path.exists():
            print(f"  WARN: missing {path}")
            continue
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                rows[r["id"]] = r
        out[model] = rows
    return out


def _criteria_html(item: dict) -> str:
    bits: list[str] = []
    must = item.get("must_pass_criteria") or []
    if must:
        lis = "".join(f"<li>{c}</li>" for c in must)
        bits.append(f"<p><b>Must-pass criteria for this item:</b></p><ul>{lis}</ul>")
    return "".join(bits) or "<p><i>(no item-specific criteria)</i></p>"


def _header_line(item: dict) -> str:
    lang = item.get("language", "??")
    name, flag = LANGUAGE_META.get(lang, (lang, ""))
    src = "native" if not item.get("is_translation") else f"translated from {item.get('source_language','?')}"
    return (
        f"{flag} {name} ({lang})  •  {item.get('category','?')}  •  "
        f"difficulty: {item.get('difficulty','?')}  •  {src}  •  id: {item['id'][:20]}"
    )


def build_tasks(
    items: dict[str, dict],
    responses: dict[str, dict[str, dict]],
    languages: list[str] | None = None,
    per_lang: int | None = None,
    seed: int = 42,
) -> list[dict]:
    # Optional language filter
    filtered = [i for i in items.values() if (not languages or i.get("language") in languages)]

    # Optional stratified sample: per_lang items per language
    if per_lang is not None:
        rng = random.Random(seed)
        by_lang: dict[str, list[dict]] = defaultdict(list)
        for i in filtered:
            by_lang[i.get("language", "??")].append(i)
        sample: list[dict] = []
        for lang, lang_items in by_lang.items():
            rng.shuffle(lang_items)
            sample.extend(lang_items[:per_lang])
        filtered = sample

    tasks: list[dict] = []
    for item in filtered:
        child = item.get("prompt", {}).get("child_utterance") or ""
        ref = item.get("reference_response") or ""
        criteria_html = _criteria_html(item)
        header_line = _header_line(item)

        for model, rows in responses.items():
            r = rows.get(item["id"])
            if not r:
                continue
            response_text = r.get("model_response") or ""
            tasks.append({
                "data": {
                    "item_id": item["id"],
                    "language": item.get("language"),
                    "language_name": LANGUAGE_META.get(item.get("language", ""), (item.get("language"),""))[0],
                    "category": item.get("category"),
                    "difficulty": item.get("difficulty"),
                    "is_translation": item.get("is_translation", False),
                    "source_language": item.get("source_language"),
                    "model_id": model,  # hidden in UI, usable in exports/filters
                    "header_line": header_line,
                    "prompt": child,
                    "reference_response": ref,
                    "item_criteria_html": criteria_html,
                    "model_response": response_text,
                },
                "meta": {
                    "item_id": item["id"],
                    "model_id": model,
                },
            })
    return tasks


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--languages", nargs="*", default=None, help="Restrict to these language codes")
    ap.add_argument("--per-lang", type=int, default=None, help="Stratified sample: this many items per language")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=OUT_DIR / "tasks.json")
    ap.add_argument("--shard-size", type=int, default=5000, help="Split output into shards of N tasks (LS upload limits)")
    args = ap.parse_args()

    items = load_items()
    responses = load_responses()
    print(f"Loaded {len(items)} items across {len({i.get('language') for i in items.values()})} languages")
    for m, rows in responses.items():
        print(f"  {m}: {len(rows)} responses")

    tasks = build_tasks(items, responses, args.languages, args.per_lang, args.seed)
    print(f"\nBuilt {len(tasks)} tasks")

    # Language breakdown
    by_lang = defaultdict(int)
    for t in tasks:
        by_lang[t["data"]["language"]] += 1
    print("Per-language counts:")
    for lang, n in sorted(by_lang.items()):
        print(f"  {lang}: {n}")

    args.out.parent.mkdir(parents=True, exist_ok=True)

    if args.shard_size and len(tasks) > args.shard_size:
        # Shard by language to keep annotators' views coherent
        shards: list[list[dict]] = []
        current: list[dict] = []
        by_lang_tasks: dict[str, list[dict]] = defaultdict(list)
        for t in tasks:
            by_lang_tasks[t["data"]["language"]].append(t)
        for lang in sorted(by_lang_tasks):
            for t in by_lang_tasks[lang]:
                current.append(t)
                if len(current) >= args.shard_size:
                    shards.append(current)
                    current = []
        if current:
            shards.append(current)

        for idx, shard in enumerate(shards, 1):
            p = args.out.with_name(args.out.stem + f"_shard{idx:02d}.json")
            with open(p, "w") as f:
                json.dump(shard, f, ensure_ascii=False)
            print(f"Wrote shard {idx}/{len(shards)}: {p} ({len(shard)} tasks)")
    else:
        with open(args.out, "w") as f:
            json.dump(tasks, f, ensure_ascii=False)
        print(f"Wrote {args.out} ({len(tasks)} tasks)")


if __name__ == "__main__":
    main()
