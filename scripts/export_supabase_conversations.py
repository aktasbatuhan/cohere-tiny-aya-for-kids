#!/usr/bin/env python3
"""Export Supabase conversation records as one JSON file per conversation."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from dotenv import load_dotenv
from supabase import Client, create_client


DEFAULT_BATCH_SIZE = 500
WHITESPACE_RE = re.compile(r"\s+")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4})")
URL_RE = re.compile(r"\bhttps?://[^\s]+|\bwww\.[^\s]+", re.IGNORECASE)
LONG_NUMBER_RE = re.compile(r"\b\d{5,}\b")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        default="data/exports/conversations",
        help="Directory where one JSON file per conversation will be written.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Pagination size for Supabase fetches.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of conversations to export.",
    )
    parser.add_argument(
        "--since",
        default=None,
        help="Optional ISO timestamp filter on chat_conversations.started_at.",
    )
    parser.add_argument(
        "--include-user-profile",
        action="store_true",
        help="Include users.id/full_name/age in each exported JSON.",
    )
    return parser.parse_args()


def make_supabase_client() -> Client:
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_KEY or SUPABASE_KEY must be set.")
    return create_client(url, key)


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text or "").strip()


def redact_text(text: str, replacement_map: Optional[Dict[str, str]] = None) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""
    cleaned = EMAIL_RE.sub("[REDACTED_EMAIL]", cleaned)
    cleaned = PHONE_RE.sub("[REDACTED_PHONE]", cleaned)
    cleaned = URL_RE.sub("[REDACTED_URL]", cleaned)
    cleaned = LONG_NUMBER_RE.sub("[REDACTED_NUMBER]", cleaned)
    for source, replacement in (replacement_map or {}).items():
        if not source:
            continue
        cleaned = re.sub(re.escape(source), replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


def fetch_table_rows(
    client: Client,
    table: str,
    order_by: str,
    batch_size: int,
    limit: Optional[int],
    filters: Optional[Sequence[Tuple[str, str, Any]]] = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        query = client.table(table).select("*").order(order_by).range(offset, offset + batch_size - 1)
        for column, op, value in filters or []:
            query = getattr(query, op)(column, value)
        result = query.execute()
        batch = result.data or []
        if not batch:
            break
        rows.extend(batch)
        if limit and len(rows) >= limit:
            return rows[:limit]
        if len(batch) < batch_size:
            break
        offset += batch_size
    return rows


def fetch_conversations(client: Client, batch_size: int, limit: Optional[int], since: Optional[str]) -> List[Dict[str, Any]]:
    filters: List[Tuple[str, str, Any]] = []
    if since:
        filters.append(("started_at", "gte", since))
    return fetch_table_rows(
        client=client,
        table="chat_conversations",
        order_by="started_at",
        batch_size=batch_size,
        limit=limit,
        filters=filters,
    )


def fetch_legacy_messages(client: Client, conversation_id: str, batch_size: int) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    offset = 0
    while True:
        result = (
            client.table("chat_messages")
            .select("*")
            .eq("conversation_id", conversation_id)
            .order("timestamp")
            .range(offset, offset + batch_size - 1)
            .execute()
        )
        batch = result.data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return rows


def fetch_user_profile(client: Client, user_id: str) -> Optional[Dict[str, Any]]:
    if not user_id:
        return None
    result = client.table("users").select("id,full_name,age").eq("id", user_id).limit(1).execute()
    return result.data[0] if result.data else None


def build_replacement_map(user_profile: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not user_profile:
        return {}

    full_name = normalize_whitespace(str(user_profile.get("full_name") or ""))
    if not full_name:
        return {}

    replacements: Dict[str, str] = {full_name: "[CHILD_NAME]"}
    parts = [part.strip(" .,!?:;") for part in full_name.split() if len(part.strip(" .,!?:;")) >= 3]
    for part in parts:
        replacements[part] = "[CHILD_NAME]"
    return replacements


def build_redacted_messages(
    conversation_row: Dict[str, Any],
    legacy_messages: Sequence[Dict[str, Any]],
    replacement_map: Dict[str, str],
) -> List[Dict[str, Any]]:
    transcript = conversation_row.get("transcript_data")
    if isinstance(transcript, list) and transcript:
        redacted = []
        for entry in transcript:
            if not isinstance(entry, dict):
                continue
            message = entry.get("message")
            if message is None:
                message = entry.get("content")
            redacted_message = redact_text(str(message or ""), replacement_map=replacement_map)
            if not redacted_message:
                continue
            redacted.append(
                {
                    "role": entry.get("role", "user"),
                    "message": redacted_message,
                    "time_in_call_secs": entry.get("time_in_call_secs"),
                }
            )
        return redacted

    redacted = []
    for row in legacy_messages:
        redacted_message = redact_text(str(row.get("content") or ""), replacement_map=replacement_map)
        if not redacted_message:
            continue
        redacted.append(
            {
                "role": row.get("role", "user"),
                "message": redacted_message,
                "timestamp": row.get("timestamp"),
            }
        )
    return redacted


def main() -> None:
    args = parse_args()
    client = make_supabase_client()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    conversations = fetch_conversations(client, args.batch_size, args.limit, args.since)
    summary_rows: List[Dict[str, Any]] = []

    for conversation in conversations:
        conversation_id = conversation["id"]
        user_id = conversation.get("user_id")
        legacy_messages = fetch_legacy_messages(client, conversation_id, args.batch_size)
        user_profile = fetch_user_profile(client, user_id)
        replacement_map = build_replacement_map(user_profile)

        export_row = {
            "conversation_id": conversation_id,
            "conversation": conversation,
            "legacy_messages": legacy_messages,
            "redacted_messages": build_redacted_messages(conversation, legacy_messages, replacement_map),
            "source": "chat_conversations.transcript_data"
            if conversation.get("transcript_data")
            else "chat_messages",
        }

        if args.include_user_profile:
            export_row["user_profile"] = user_profile

        file_path = output_dir / f"{conversation_id}.json"
        with file_path.open("w", encoding="utf-8") as handle:
            json.dump(export_row, handle, indent=2, ensure_ascii=False)

        summary_rows.append(
            {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "started_at": conversation.get("started_at"),
                "message_count": conversation.get("message_count"),
                "has_transcript_data": bool(conversation.get("transcript_data")),
                "legacy_message_count": len(legacy_messages),
                "path": str(file_path),
            }
        )

    with (output_dir / "_summary.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                "exported_conversations": len(summary_rows),
                "output_dir": str(output_dir),
                "conversations": summary_rows,
            },
            handle,
            indent=2,
        )

    print(
        json.dumps(
            {
                "exported_conversations": len(summary_rows),
                "output_dir": str(output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
