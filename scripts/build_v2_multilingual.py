#!/usr/bin/env python3
"""Build the multilingual v2 benchmark by combining real-world scraped items
with machine translation of strong English foundation items.

Composition:
1. Native/original-language items from scraped/extracted.jsonl (already in
   their source language, kept as-is)
2. English scraped items, translated into all TinyAya languages
3. A selected subset of strong v2 foundation items (hard difficulty, clean),
   translated into all TinyAya languages

Uses Cohere Command A Translate via the existing translate_benchmark.py logic.

Outputs:
  data/benchmark/v2/multilingual/v2_multilingual.jsonl   — combined final set
  data/benchmark/v2/multilingual/translation_log.json    — counts per language
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import cohere
from cohere.errors import TooManyRequestsError
from dotenv import load_dotenv

load_dotenv()

FOUNDATION = Path("data/benchmark/v2/v2_foundation.jsonl")
EXTRACTED = Path("data/benchmark/v2/scraped/extracted.jsonl")
OUT_DIR = Path("data/benchmark/v2/multilingual")

TRANSLATE_MODEL = "command-a-03-2025"

SUPPORTED_LANGUAGES = {
    "ar": "Arabic", "zh": "Chinese (Simplified)", "cs": "Czech",
    "nl": "Dutch", "fr": "French", "de": "German", "hi": "Hindi",
    "id": "Indonesian", "it": "Italian", "ja": "Japanese", "ko": "Korean",
    "pl": "Polish", "pt": "Portuguese", "ro": "Romanian", "ru": "Russian",
    "es": "Spanish", "sw": "Swahili", "te": "Telugu", "th": "Thai",
    "tr": "Turkish", "uk": "Ukrainian", "vi": "Vietnamese",
}

TRANSLATE_SYSTEM = """You are translating a children's AI evaluation benchmark item into {language_name}.

RULES:
1. Translate with child-natural phrasing — how a 4-8 year old native {language_name} speaker would talk.
2. Preserve safety behavior exactly: if English refuses/redirects, translation must do the same.
3. Do NOT add harmful detail, cultural bias, or make content more adult.
4. Keep placeholder tokens like [CHILD_NAME] or [PARENT_NAME] as-is.
5. Must-pass criteria may stay in English (they're meta-instructions for judges).

Return ONLY valid JSON with these fields:
- child_utterance_translated
- reference_response_translated
- context_messages_translated (array of strings, same order as input)
- cultural_notes (optional, 1 line if the scenario doesn't translate well)"""


def make_cohere_client():
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY must be set")
    return cohere.ClientV2(api_key=api_key, log_warning_experimental_features=False, timeout=300)


def translate_item(client, item: dict, lang_code: str, max_retries: int = 4) -> dict:
    lang_name = SUPPORTED_LANGUAGES[lang_code]

    context_msgs = [m["message"] for m in item.get("context_window", [])]
    payload = {
        "child_utterance": item["child_utterance"],
        "reference_response": item["reference_response"],
        "context_messages": context_msgs,
    }
    user_prompt = json.dumps(payload, ensure_ascii=False)

    for attempt in range(max_retries + 1):
        try:
            resp = client.chat(
                model=TRANSLATE_MODEL,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": TRANSLATE_SYSTEM.format(language_name=lang_name)},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = getattr(resp.message, "content", None) or []
            text = "".join(getattr(c, "text", None) or "" for c in content).strip()

            # Strip markdown
            import re
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if m:
                text = m.group(1)
            return json.loads(text)
        except TooManyRequestsError:
            time.sleep(min(60, 2 ** attempt + 1))
        except Exception as e:
            if attempt == max_retries:
                return {"error": str(e)}
            time.sleep(2 ** attempt)
    return {"error": "max retries"}


def load_extracted_items() -> list[dict]:
    """Load real-world scraped items, dedup at incident level, convert to unified schema."""
    if not EXTRACTED.exists():
        return []
    items = []
    seen_signatures = set()
    with open(EXTRACTED) as f:
        for line in f:
            r = json.loads(line)
            if r.get("is_duplicate_incident"):
                continue
            sig = (r.get("incident_signature") or "").strip().lower()
            if sig and sig in seen_signatures:
                continue
            if sig:
                seen_signatures.add(sig)

            # Convert to unified schema
            items.append({
                "id": f"scraped_{r['candidate_id']}",
                "origin": "scraped",
                "source_url": r.get("source_url"),
                "source_domain": r.get("source_domain"),
                "source_language": r.get("language", "en"),
                "category": r.get("category", "other"),
                "difficulty": r.get("difficulty", "medium"),
                "estimated_age": r.get("estimated_age"),
                "child_utterance": r.get("child_utterance") or "",
                "reference_response": r.get("draft_reference_response") or "",
                "ai_response_observed": r.get("ai_response"),
                "context_window": [
                    {"role": "agent", "message": r.get("context", "")}
                ] if r.get("context") else [],
                "must_pass_criteria": r.get("must_pass_criteria", []),
                "notes": r.get("notes"),
                "provenance_confidence": r.get("provenance_confidence"),
                "incident_signature": r.get("incident_signature"),
            })
    return items


def load_foundation_subset(difficulty_filter: list[str] | None = None) -> list[dict]:
    """Load v2 foundation items, keeping only clean (no-rewrite) ones."""
    items = []
    if not FOUNDATION.exists():
        return items
    with open(FOUNDATION) as f:
        for line in f:
            f_item = json.loads(line)
            if f_item.get("quality_flags", {}).get("needs_rewrite"):
                continue
            if difficulty_filter and f_item.get("difficulty") not in difficulty_filter:
                continue

            items.append({
                "id": f"foundation_{f_item['id']}",
                "origin": "foundation",
                "source_url": None,
                "source_domain": None,
                "source_language": "en",
                "category": f_item["category"],
                "difficulty": f_item["difficulty"],
                "estimated_age": None,
                "child_utterance": f_item["prompt"]["child_utterance"],
                "reference_response": f_item["reference"]["response"],
                "ai_response_observed": None,
                "context_window": f_item["prompt"].get("context_window", []),
                "must_pass_criteria": f_item["evaluation"].get("item_specific_criteria", []),
                "notes": None,
                "provenance_confidence": "gold",
                "incident_signature": None,
            })
    return items


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--languages", nargs="+", default=["all"],
                        help=f"Target languages (default: all). Available: {list(SUPPORTED_LANGUAGES.keys())}")
    parser.add_argument("--foundation-difficulties", nargs="+", default=["hard"],
                        help="Which foundation difficulties to translate (default: hard only)")
    parser.add_argument("--foundation-limit", type=int, default=30,
                        help="Cap on foundation items to translate per language (default: 30)")
    parser.add_argument("--scraped-only", action="store_true",
                        help="Only translate scraped items; skip foundation subset")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan without translating")
    args = parser.parse_args()

    target_langs = list(SUPPORTED_LANGUAGES.keys()) if "all" in args.languages else args.languages
    for l in target_langs:
        if l not in SUPPORTED_LANGUAGES:
            raise RuntimeError(f"Unknown language: {l}")

    # Load sources
    scraped = load_extracted_items()
    print(f"Loaded {len(scraped)} unique scraped items")
    foundation = [] if args.scraped_only else load_foundation_subset(args.foundation_difficulties)
    if args.foundation_limit and foundation:
        foundation = foundation[: args.foundation_limit]
    print(f"Loaded {len(foundation)} foundation items (difficulties={args.foundation_difficulties}, capped at {args.foundation_limit})")

    # For scraped items: native-language items are kept as-is. English items + all foundation
    # items get translated into every target language.
    needs_translation_to = {}
    for item in scraped:
        src = item["source_language"]
        # If it's already in a target language, keep it native
        if src in target_langs:
            needs_translation_to[item["id"]] = [l for l in target_langs if l != src]
        else:
            # Translate from source to all targets
            needs_translation_to[item["id"]] = list(target_langs)

    for item in foundation:
        needs_translation_to[item["id"]] = [l for l in target_langs if l != "en"]

    total_translations = sum(len(langs) for langs in needs_translation_to.values())
    print(f"\nTotal translations to perform: {total_translations}")
    print(f"  Scraped items: {len(scraped)} × (up to {len(target_langs)-1}) languages")
    print(f"  Foundation items: {len(foundation)} × {len(target_langs)} languages")

    if args.dry_run:
        print("\n[dry-run] stopping here")
        return

    # Translate
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "v2_multilingual.jsonl"
    log_path = OUT_DIR / "translation_log.json"

    # Resume support
    existing_keys = set()
    if out_path.exists():
        with open(out_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    existing_keys.add((r["original_id"], r["language"]))
                except Exception:
                    continue
    if existing_keys:
        print(f"Resume: {len(existing_keys)} translations already done")

    client = make_cohere_client()
    all_items = scraped + foundation
    by_id = {i["id"]: i for i in all_items}

    # First, write the native-language versions (no translation needed)
    with open(out_path, "a") as f:
        for item in all_items:
            key = (item["id"], item["source_language"])
            if key in existing_keys:
                continue
            f.write(json.dumps({
                "original_id": item["id"],
                "language": item["source_language"],
                "origin": item["origin"],
                "is_translation": False,
                **{k: v for k, v in item.items() if k not in ("id",)},
            }, ensure_ascii=False) + "\n")
            existing_keys.add(key)

    # Now translate
    counter = Counter()
    done = 0
    for item in all_items:
        target_for_item = needs_translation_to[item["id"]]
        for lang in target_for_item:
            key = (item["id"], lang)
            if key in existing_keys:
                counter[f"cached_{lang}"] += 1
                continue

            t = translate_item(client, item, lang)
            if "error" in t:
                counter[f"error_{lang}"] += 1
                print(f"  [err] {item['id'][:20]} → {lang}: {t['error'][:80]}")
                continue

            row = {
                "original_id": item["id"],
                "language": lang,
                "origin": item["origin"],
                "is_translation": True,
                "source_language": item["source_language"],
                "source_url": item.get("source_url"),
                "source_domain": item.get("source_domain"),
                "category": item["category"],
                "difficulty": item["difficulty"],
                "estimated_age": item.get("estimated_age"),
                "child_utterance": t.get("child_utterance_translated", ""),
                "reference_response": t.get("reference_response_translated", ""),
                "context_window": [
                    {"role": "agent", "message": m} for m in t.get("context_messages_translated", [])
                ],
                "must_pass_criteria": item.get("must_pass_criteria", []),
                "cultural_notes": t.get("cultural_notes"),
                "provenance_confidence": item.get("provenance_confidence"),
            }
            with open(out_path, "a") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
            existing_keys.add(key)
            counter[f"done_{lang}"] += 1
            done += 1
            if done % 10 == 0:
                print(f"  [{done}/{total_translations}] {item['id'][:20]} → {lang}")

    # Log
    with open(log_path, "w") as f:
        json.dump({
            "totals": dict(counter),
            "done_at": time.time(),
            "out_path": str(out_path),
        }, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'='*60}")
    with open(out_path) as f:
        all_written = [json.loads(l) for l in f]
    by_lang = Counter(r["language"] for r in all_written)
    print(f"Total items written: {len(all_written)}")
    print(f"Per language:")
    for l in sorted(by_lang.keys()):
        print(f"  {l}: {by_lang[l]}")
    print(f"\nOutput: {out_path}")


if __name__ == "__main__":
    main()
