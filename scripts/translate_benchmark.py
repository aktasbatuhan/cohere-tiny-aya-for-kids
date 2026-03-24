#!/usr/bin/env python3
"""Translate the children eval benchmark into TinyAya-supported languages using Cohere Command A.

Usage:
    python scripts/translate_benchmark.py --languages tr es ar           # specific languages
    python scripts/translate_benchmark.py --languages all                # all supported
    python scripts/translate_benchmark.py --languages tr --limit 10      # test with 10 items
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import cohere
from cohere.errors import TooManyRequestsError
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# TinyAya supported languages (23 languages)
# Cross-referenced with Command A translation support
# https://docs.cohere.com/docs/command-a-translate#supported-languages
# ---------------------------------------------------------------------------

SUPPORTED_LANGUAGES = {
    "ar": "Arabic",
    "zh": "Chinese (Simplified)",
    "cs": "Czech",
    "nl": "Dutch",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "pl": "Polish",
    "pt": "Portuguese",
    "ro": "Romanian",
    "ru": "Russian",
    "es": "Spanish",
    "sw": "Swahili",
    "te": "Telugu",
    "th": "Thai",
    "tr": "Turkish",
    "uk": "Ukrainian",
    "vi": "Vietnamese",
}

TRANSLATE_MODEL = "command-a-08-2025"

SYSTEM_PROMPT = """You are translating a children's AI evaluation benchmark from English into {language_name}.

CRITICAL RULES:
1. Use child-natural phrasing — how a real 4-8 year old native speaker would talk. Do NOT translate word-for-word.
2. Keep the same warmth, simplicity, and tone as the English source.
3. Preserve safety behavior EXACTLY: if the English redirects away from unsafe content, the translation must too.
4. Do NOT add harmful detail, political/religious bias, or make content more adult or frightening.
5. Keep privacy boundaries intact.
6. For educational items, use local metaphors only if they don't change the teaching goal.
7. Preserve placeholder tokens like [CHILD_NAME] as-is.

Return ONLY valid JSON matching the requested schema."""

TRANSLATE_SCHEMA = {
    "type": "object",
    "properties": {
        "context_messages": {
            "type": "array",
            "items": {"type": "string"},
        },
        "child_request": {"type": "string"},
        "reference_response": {"type": "string"},
    },
    "required": ["context_messages", "child_request", "reference_response"],
    "additionalProperties": False,
}


def make_client() -> cohere.ClientV2:
    load_dotenv()
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY must be set in .env or environment.")
    return cohere.ClientV2(api_key=api_key, log_warning_experimental_features=False)


def load_benchmark(path: str) -> list[dict]:
    items = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            items.append(json.loads(line))
    return items


def translate_item(
    client: cohere.ClientV2,
    item: dict,
    lang_code: str,
    lang_name: str,
    max_retries: int = 5,
) -> dict:
    """Translate the translatable fields of a benchmark item."""
    context_messages = [m["message"] for m in item["prompt"].get("context_window", [])]

    user_prompt = json.dumps(
        {
            "source_language": "English",
            "target_language": lang_name,
            "category": item["category"],
            "context_messages": context_messages,
            "child_request": item["prompt"]["child_request"],
            "reference_response": item["reference_response"],
        },
        ensure_ascii=False,
    )

    for attempt in range(max_retries + 1):
        try:
            response = client.chat(
                model=TRANSLATE_MODEL,
                temperature=0.2,
                response_format={"type": "json_object", "schema": TRANSLATE_SCHEMA},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT.format(language_name=lang_name)},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = getattr(response.message, "content", None) or []
            text = "".join(getattr(c, "text", "") for c in content)
            translation = json.loads(text)

            # Reconstruct the translated item preserving structure
            translated = json.loads(json.dumps(item))  # deep copy
            translated["language"] = lang_code

            # Update context window messages
            ctx = translated["prompt"].get("context_window", [])
            for i, msg in enumerate(translation.get("context_messages", [])):
                if i < len(ctx):
                    ctx[i]["message"] = msg

            translated["prompt"]["child_request"] = translation["child_request"]
            translated["reference_response"] = translation["reference_response"]

            return translated

        except TooManyRequestsError:
            wait = min(60, 2**attempt + 1)
            time.sleep(wait)
        except Exception as e:
            if attempt == max_retries:
                # Return original with error flag
                errored = json.loads(json.dumps(item))
                errored["language"] = lang_code
                errored["translation_error"] = str(e)
                return errored
            time.sleep(2**attempt)

    errored = json.loads(json.dumps(item))
    errored["language"] = lang_code
    errored["translation_error"] = "max retries exceeded"
    return errored


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--benchmark", default="data/benchmark/final_children_eval_benchmark.jsonl")
    parser.add_argument("--output-dir", default="data/benchmark/translations")
    parser.add_argument("--languages", nargs="+", required=True, help="Language codes (e.g., tr es ar) or 'all'")
    parser.add_argument("--limit", type=int, default=None, help="Max items to translate (for testing)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    items = load_benchmark(args.benchmark)
    if args.limit:
        items = items[: args.limit]

    languages = list(SUPPORTED_LANGUAGES.keys()) if "all" in args.languages else args.languages
    for lang in languages:
        if lang not in SUPPORTED_LANGUAGES:
            print(f"WARNING: '{lang}' not in supported languages. Skipping.")
            continue

    client = make_client()

    for lang in languages:
        if lang not in SUPPORTED_LANGUAGES:
            continue

        lang_name = SUPPORTED_LANGUAGES[lang]
        output_file = output_dir / f"final_children_eval_benchmark.{lang}.jsonl"

        # Resume support
        existing_ids = set()
        if output_file.exists():
            with open(output_file, encoding="utf-8") as f:
                for line in f:
                    row = json.loads(line)
                    existing_ids.add(row["benchmark_id"])

        pending = [item for item in items if item["benchmark_id"] not in existing_ids]
        if not pending:
            print(f"[{lang}] All {len(items)} items already translated. Skipping.")
            continue

        print(f"[{lang} — {lang_name}] Translating {len(pending)} items ({len(existing_ids)} cached)...")
        errors = 0

        with open(output_file, "a", encoding="utf-8") as f:
            for i, item in enumerate(pending, 1):
                translated = translate_item(client, item, lang, lang_name)
                f.write(json.dumps(translated, ensure_ascii=False) + "\n")
                f.flush()

                if "translation_error" in translated:
                    errors += 1

                if i % 10 == 0 or i == len(pending):
                    print(f"  [{lang}] {i}/{len(pending)} done ({errors} errors)")

        print(f"[{lang}] Complete. Output: {output_file} ({errors} errors)")


if __name__ == "__main__":
    main()
