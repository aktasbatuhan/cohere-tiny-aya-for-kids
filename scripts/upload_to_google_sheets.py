#!/usr/bin/env python3
"""Upload a CSV to a new Google Sheet using gcloud application-default credentials.

Setup (run once on your laptop):
    gcloud auth application-default login \\
        --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.file

Usage:
    python scripts/upload_to_google_sheets.py --csv data/benchmark/v2/review/balanced_review.csv \\
        --title "TinyAya v2 Review (713 items)"
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

try:
    from google.auth import default
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Need google-api-python-client + google-auth.", file=sys.stderr)
    sys.exit(1)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def upload(csv_path: Path, title: str) -> str:
    creds, project = default(scopes=SCOPES)
    sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
    drive = build("drive", "v3", credentials=creds, cache_discovery=False)

    # Read CSV
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        raise ValueError("CSV is empty")
    n_rows = len(rows)
    n_cols = max(len(r) for r in rows)
    print(f"Loaded {n_rows} rows × {n_cols} cols from {csv_path}")

    # Create the spreadsheet
    body = {
        "properties": {"title": title},
        "sheets": [{"properties": {"title": "Reviews", "gridProperties": {"frozenRowCount": 1}}}],
    }
    ss = sheets.spreadsheets().create(body=body, fields="spreadsheetId,spreadsheetUrl").execute()
    sheet_id = ss["spreadsheetId"]
    sheet_url = ss["spreadsheetUrl"]
    print(f"Created sheet: {sheet_url}")

    # Write data — chunk to stay under request limits
    CHUNK = 1000
    for start in range(0, n_rows, CHUNK):
        chunk = rows[start:start + CHUNK]
        sheets.spreadsheets().values().update(
            spreadsheetId=sheet_id,
            range=f"Reviews!A{start + 1}",
            valueInputOption="RAW",
            body={"values": chunk},
        ).execute()
        print(f"  Wrote rows {start + 1}–{start + len(chunk)}")

    # Format header bold + freeze
    sheets.spreadsheets().batchUpdate(
        spreadsheetId=sheet_id,
        body={
            "requests": [
                {
                    "repeatCell": {
                        "range": {
                            "sheetId": ss["sheets"][0]["properties"]["sheetId"],
                            "startRowIndex": 0,
                            "endRowIndex": 1,
                        },
                        "cell": {"userEnteredFormat": {"textFormat": {"bold": True}, "wrapStrategy": "CLIP"}},
                        "fields": "userEnteredFormat(textFormat,wrapStrategy)",
                    }
                },
                {
                    "updateSheetProperties": {
                        "properties": {
                            "sheetId": ss["sheets"][0]["properties"]["sheetId"],
                            "gridProperties": {"frozenRowCount": 1},
                        },
                        "fields": "gridProperties.frozenRowCount",
                    }
                },
            ]
        },
    ).execute()

    return sheet_url


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, required=True)
    ap.add_argument("--title", default="TinyAya v2 Benchmark Review")
    args = ap.parse_args()

    if not args.csv.exists():
        print(f"CSV not found: {args.csv}", file=sys.stderr)
        sys.exit(2)

    try:
        url = upload(args.csv, args.title)
    except HttpError as e:
        print(f"\nGoogle API error: {e}", file=sys.stderr)
        if "403" in str(e) or "PERMISSION_DENIED" in str(e):
            print("\nLikely cause: missing scopes. Re-auth with:", file=sys.stderr)
            print("  gcloud auth application-default login \\", file=sys.stderr)
            print("    --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.file", file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        if "RefreshError" in type(e).__name__ or "invalid_grant" in str(e):
            print("\nApplication-default credentials are stale. Re-auth with:", file=sys.stderr)
            print("  gcloud auth application-default login \\", file=sys.stderr)
            print("    --scopes=https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive.file", file=sys.stderr)
            sys.exit(4)
        raise

    print(f"\n✓ Sheet ready: {url}")


if __name__ == "__main__":
    main()
