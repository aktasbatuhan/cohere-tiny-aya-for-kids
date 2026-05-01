#!/usr/bin/env python3
"""Create a Label Studio project + import tasks via the REST API.

Uses the long-lived refresh token to mint short-lived access tokens on demand.

Usage:
    export LS_URL=https://batuhanaktas-tinyaya-bench-review.hf.space
    export LS_REFRESH=<your LS refresh JWT from Account settings>
    python scripts/upload_label_studio_project.py \
        --config data/benchmark/v2/label_studio/labeling_config.xml \
        --tasks data/benchmark/v2/label_studio/tasks_shard01.json \
                data/benchmark/v2/label_studio/tasks_shard02.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests


class LSClient:
    def __init__(self, base: str, refresh: str):
        self.base = base.rstrip("/")
        self.refresh = refresh
        self._access: str | None = None
        self._access_exp: float = 0.0
        self._s = requests.Session()

    def _mint_access(self) -> None:
        r = self._s.post(
            f"{self.base}/api/token/refresh/",
            headers={"Content-Type": "application/json"},
            json={"refresh": self.refresh},
            timeout=30,
        )
        r.raise_for_status()
        self._access = r.json()["access"]
        # Access tokens are ~5 min; refresh early (at 3 min).
        self._access_exp = time.time() + 180

    def _hdr(self) -> dict[str, str]:
        if not self._access or time.time() > self._access_exp:
            self._mint_access()
        return {"Authorization": f"Bearer {self._access}"}

    def request(self, method: str, path: str, **kw):
        headers = kw.pop("headers", {}) or {}
        headers.update(self._hdr())
        r = self._s.request(method, f"{self.base}{path}", headers=headers, timeout=kw.pop("timeout", 600), **kw)
        if r.status_code == 401:
            self._mint_access()
            headers.update(self._hdr())
            r = self._s.request(method, f"{self.base}{path}", headers=headers, timeout=kw.pop("timeout", 600), **kw)
        return r


def create_project(cli: LSClient, title: str, config_xml: str) -> int:
    r = cli.request(
        "POST",
        "/api/projects/",
        headers={"Content-Type": "application/json"},
        data=json.dumps({
            "title": title,
            "label_config": config_xml,
            "show_instruction": False,
        }),
    )
    if not r.ok:
        print(f"create_project failed {r.status_code}: {r.text[:500]}")
        r.raise_for_status()
    pid = r.json()["id"]
    print(f"Created project id={pid}")
    return pid


def import_tasks(cli: LSClient, project_id: int, tasks_path: Path) -> None:
    print(f"Uploading {tasks_path} ({tasks_path.stat().st_size/1e6:.1f}MB) ...")
    with open(tasks_path, "rb") as f:
        data = f.read()
    t0 = time.perf_counter()
    r = cli.request(
        "POST",
        f"/api/projects/{project_id}/import",
        headers={"Content-Type": "application/json"},
        data=data,
    )
    dt = time.perf_counter() - t0
    if not r.ok:
        print(f"  ERROR {r.status_code}: {r.text[:500]}")
        r.raise_for_status()
    out = r.json()
    print(f"  imported {out.get('task_count', '?')} tasks in {dt:.1f}s")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=os.environ.get("LS_URL"))
    ap.add_argument("--refresh", default=os.environ.get("LS_REFRESH"))
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--tasks", nargs="+", type=Path, required=True)
    ap.add_argument("--title", default="TinyAya Benchmark Review")
    ap.add_argument("--project-id", type=int, default=None)
    args = ap.parse_args()

    if not args.url or not args.refresh:
        print("ERROR: set LS_URL and LS_REFRESH env vars", file=sys.stderr)
        sys.exit(2)

    cli = LSClient(args.url, args.refresh)
    config_xml = args.config.read_text()

    if args.project_id:
        pid = args.project_id
        print(f"Using existing project id={pid}")
    else:
        pid = create_project(cli, args.title, config_xml)

    for tpath in args.tasks:
        import_tasks(cli, pid, tpath)

    print(f"\n✓ Done. Open: {args.url.rstrip('/')}/projects/{pid}/data")


if __name__ == "__main__":
    main()
