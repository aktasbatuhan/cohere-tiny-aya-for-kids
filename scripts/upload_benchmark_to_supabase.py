#!/usr/bin/env python3
"""Upload benchmark responses and scores to Supabase, replacing existing data for specified models."""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OUTPUT_DIR = Path("data/benchmark/preliminary")


def sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def delete_model_data(client: httpx.Client, table: str, model: str):
    """Delete all rows for a model from a table."""
    resp = client.delete(
        f"{SUPABASE_URL}/rest/v1/{table}",
        params={"model": f"eq.{model}"},
        headers=sb_headers(),
    )
    print(f"  DELETE {table} model={model} → {resp.status_code}")


def upsert_rows(client: httpx.Client, table: str, rows: list[dict]):
    """Upsert rows in batches using on_conflict for the unique key."""
    batch_size = 50
    headers = sb_headers()
    headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        resp = client.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            params={"on_conflict": "benchmark_id,model"},
            json=batch,
            headers=headers,
        )
        if resp.status_code >= 400:
            print(f"  ERROR upserting into {table}: {resp.status_code} {resp.text[:200]}")
        else:
            print(f"  UPSERT {table} batch {i // batch_size + 1}: {len(batch)} rows → {resp.status_code}")


def upload_model(client: httpx.Client, model: str):
    resp_file = OUTPUT_DIR / f"responses_{model}.jsonl"
    scores_file = OUTPUT_DIR / f"scores_{model}.jsonl"

    if not resp_file.exists():
        print(f"[{model}] No response file found. Skipping.")
        return

    # Load responses
    responses = []
    with open(resp_file) as f:
        for line in f:
            r = json.loads(line)
            if "ERROR" not in r.get("model_response", ""):
                responses.append(r)

    print(f"[{model}] {len(responses)} valid responses")

    # Delete old data
    delete_model_data(client, "benchmark_responses", model)
    delete_model_data(client, "benchmark_scores", model)

    # Upload responses
    resp_rows = []
    for r in responses:
        resp_rows.append({
            "benchmark_id": r["benchmark_id"],
            "model": model,
            "category": r["category"],
            "child_request": r["child_request"],
            "reference_response": r["reference_response"],
            "model_response": r["model_response"],
        })
    if resp_rows:
        upsert_rows(client, "benchmark_responses", resp_rows)

    # Upload scores
    if scores_file.exists():
        score_rows = []
        with open(scores_file) as f:
            for line in f:
                s = json.loads(line)
                scores = s.get("scores", {})
                if "error" in scores:
                    continue
                score_rows.append({
                    "benchmark_id": s["benchmark_id"],
                    "model": model,
                    "category": s["category"],
                    "child_safety": scores.get("child_safety"),
                    "age_appropriateness": scores.get("age_appropriateness"),
                    "helpfulness": scores.get("helpfulness"),
                    "empathy": scores.get("empathy"),
                    "conversational_quality": scores.get("conversational_quality"),
                    "overall_pass": scores.get("overall_pass"),
                    "brief_reasoning": scores.get("brief_reasoning", ""),
                })
        print(f"[{model}] {len(score_rows)} valid scores")
        if score_rows:
            upsert_rows(client, "benchmark_scores", score_rows)
    else:
        print(f"[{model}] No scores file.")


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    models = sys.argv[1:] if len(sys.argv) > 1 else [
        "tiny-aya-modal",
        "c4ai-aya-expanse-8b",
        "c4ai-aya-expanse-32b",
        "command-a-reasoning-08-2025",
    ]

    client = httpx.Client(timeout=30)
    for model in models:
        upload_model(client, model)
    print("\nDone!")


if __name__ == "__main__":
    main()
