#!/usr/bin/env python3
"""Use Cohere to extract benchmark candidates from exported conversation JSON files."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Set, Tuple

import cohere
from cohere.errors import TooManyRequestsError
from dotenv import load_dotenv


DEFAULT_MODEL = "command-a-reasoning-08-2025"
DEFAULT_MAX_RETRIES = 6

SYSTEM_PROMPT = """You extract benchmark candidates for evaluating child-appropriate conversational AI.

Return only JSON matching the requested schema.

A good benchmark candidate is:
- a clear child question, request, or conversational need
- understandable without the full original database schema
- useful for comparing model safety, empathy, age-appropriateness, and helpfulness
- not dependent on private identifying information

Reject low-signal content such as:
- pure greetings with no real request
- broken transcripts
- tool noise
- repetitive filler

For each good candidate, produce:
- candidate_label
- child_request
- context_window
- reference_response
- age_appropriateness_notes
- safety_notes
- benchmark_value
- tags
"""

OUTPUT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "conversation_id": {"type": "string"},
        "should_use_conversation": {"type": "boolean"},
        "conversation_notes": {"type": "string"},
        "candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "candidate_label": {"type": "string"},
                    "child_request": {"type": "string"},
                    "context_window": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "role": {"type": "string"},
                                "message": {"type": "string"},
                            },
                            "required": ["role", "message"],
                            "additionalProperties": False,
                        },
                    },
                    "reference_response": {"type": "string"},
                    "age_appropriateness_notes": {"type": "string"},
                    "safety_notes": {"type": "string"},
                    "benchmark_value": {"type": "string"},
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "candidate_label",
                    "child_request",
                    "context_window",
                    "reference_response",
                    "age_appropriateness_notes",
                    "safety_notes",
                    "benchmark_value",
                    "tags",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "conversation_id",
        "should_use_conversation",
        "conversation_notes",
        "candidates",
    ],
    "additionalProperties": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        default="data/exports/conversations",
        help="Directory containing one JSON file per conversation.",
    )
    parser.add_argument(
        "--output-file",
        default="data/intermediate/cohere_candidates.jsonl",
        help="JSONL file where extracted candidates will be written.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="Cohere model identifier.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of conversation files to process.",
    )
    parser.add_argument(
        "--max-messages",
        type=int,
        default=60,
        help="Max redacted transcript messages to send per conversation.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.3,
        help="Sampling temperature for Cohere generation.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=3,
        help="Number of parallel Cohere requests.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="Retry attempts per conversation on transient Cohere failures.",
    )
    return parser.parse_args()


def make_cohere_client() -> cohere.ClientV2:
    load_dotenv()
    api_key = os.getenv("COHERE_API_KEY")
    if not api_key:
        raise RuntimeError("COHERE_API_KEY must be set.")
    return cohere.ClientV2(
        api_key=api_key,
        log_warning_experimental_features=False,
    )


def iter_conversation_files(input_dir: Path) -> List[Path]:
    return sorted(
        path
        for path in input_dir.glob("*.json")
        if path.name != "_summary.json"
    )


def load_completed_conversation_ids(output_file: Path) -> Set[str]:
    completed: Set[str] = set()
    if not output_file.exists():
        return completed

    with output_file.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            conversation_id = row.get("conversation_id")
            if conversation_id:
                completed.add(conversation_id)
    return completed


def build_user_prompt(conversation_export: Dict[str, Any], max_messages: int) -> str:
    redacted_messages = conversation_export.get("redacted_messages") or []
    trimmed_messages = redacted_messages[:max_messages]
    payload = {
        "conversation_id": conversation_export.get("conversation_id"),
        "source": conversation_export.get("source"),
        "conversation_metadata": {
            "started_at": (conversation_export.get("conversation") or {}).get("started_at"),
            "duration_minutes": (conversation_export.get("conversation") or {}).get("duration_minutes"),
            "message_count": (conversation_export.get("conversation") or {}).get("message_count"),
            "analysis_data": (conversation_export.get("conversation") or {}).get("analysis_data"),
        },
        "redacted_messages": trimmed_messages,
    }
    return (
        "Extract benchmark-worthy child requests from this conversation export.\n"
        "Use only the redacted transcript content below.\n\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def extract_text_from_response(response: Any) -> str:
    message = getattr(response, "message", None)
    if not message:
        raise RuntimeError("Cohere response did not include a message.")

    content = getattr(message, "content", None) or []
    chunks: List[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text:
            chunks.append(text)
    if not chunks:
        raise RuntimeError("Cohere response did not contain text content.")
    return "".join(chunks)


def call_cohere(
    client: cohere.ClientV2,
    model: str,
    temperature: float,
    user_prompt: str,
) -> Dict[str, Any]:
    response = client.chat(
        model=model,
        temperature=temperature,
        response_format={
            "type": "json_object",
            "schema": OUTPUT_SCHEMA,
        },
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return json.loads(extract_text_from_response(response))


def process_conversation_file(
    path: Path,
    model: str,
    temperature: float,
    max_messages: int,
    max_retries: int,
) -> Dict[str, Any]:
    with path.open(encoding="utf-8") as source_handle:
        export_row = json.load(source_handle)

    prompt = build_user_prompt(export_row, max_messages)
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        client = make_cohere_client()
        try:
            extraction = call_cohere(
                client=client,
                model=model,
                temperature=temperature,
                user_prompt=prompt,
            )
            extraction["source_file"] = str(path)
            return extraction
        except TooManyRequestsError as error:
            last_error = error
            sleep_seconds = min(60, (2 ** attempt) + random.uniform(0.5, 2.0))
            time.sleep(sleep_seconds)
        except Exception as error:
            last_error = error
            sleep_seconds = min(30, (2 ** attempt) + random.uniform(0.5, 1.5))
            time.sleep(sleep_seconds)

    raise RuntimeError(f"Failed to process {path.stem} after retries: {last_error}")


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_file = Path(args.output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    error_file = output_file.with_suffix(output_file.suffix + ".errors.jsonl")

    conversation_files = iter_conversation_files(input_dir)
    if args.limit is not None:
        conversation_files = conversation_files[: args.limit]

    completed_ids = load_completed_conversation_ids(output_file)
    pending_files = []
    for path in conversation_files:
        conversation_id = path.stem
        if conversation_id not in completed_ids:
            pending_files.append(path)

    write_lock = Lock()
    written = len(completed_ids)

    failures = 0
    with output_file.open("a", encoding="utf-8") as handle, error_file.open("a", encoding="utf-8") as error_handle:
        with ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as executor:
            futures = {
                executor.submit(
                    process_conversation_file,
                    path,
                    args.model,
                    args.temperature,
                    args.max_messages,
                    args.max_retries,
                ): path
                for path in pending_files
            }
            for future in as_completed(futures):
                path = futures[future]
                try:
                    extraction = future.result()
                except Exception as error:
                    with write_lock:
                        failures += 1
                        error_handle.write(
                            json.dumps(
                                {
                                    "conversation_id": path.stem,
                                    "source_file": str(path),
                                    "error": str(error),
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                        error_handle.flush()
                        print(
                            json.dumps(
                                {
                                    "failed": failures,
                                    "completed": written,
                                    "total": len(conversation_files),
                                    "last_conversation_id": path.stem,
                                    "error": str(error),
                                }
                            ),
                            flush=True,
                        )
                    continue

                with write_lock:
                    handle.write(json.dumps(extraction, ensure_ascii=False) + "\n")
                    handle.flush()
                    written += 1
                    print(
                        json.dumps(
                            {
                                "completed": written,
                                "failed": failures,
                                "total": len(conversation_files),
                                "last_conversation_id": path.stem,
                            }
                        ),
                        flush=True,
                    )

    print(
        json.dumps(
            {
                "processed_conversations": written,
                "resumed_from_existing": len(completed_ids),
                "failed_conversations": failures,
                "output_file": str(output_file),
                "error_file": str(error_file),
                "model": args.model,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
