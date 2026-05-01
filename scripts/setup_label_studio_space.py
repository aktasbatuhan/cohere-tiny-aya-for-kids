#!/usr/bin/env python3
"""Provision a Label Studio HuggingFace Space for benchmark annotation.

Creates a private Docker Space running Label Studio, wires up:
  - Admin credentials (from args)
  - Signup restriction
  - Persistent storage bucket mounted at /data
  - SECRET_KEY for stable sessions

After the Space finishes building, paste labeling_config.xml into the
project's Labeling Interface, then import tasks_shard*.json files.

Usage:
    export HF_TOKEN=hf_...
    python scripts/setup_label_studio_space.py \
        --space-id batuhan/tinyaya-bench-review \
        --admin-email batuhan@dria.co \
        --admin-password 'choose-a-strong-one'
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys

try:
    from huggingface_hub import HfApi
    from huggingface_hub.errors import HfHubHTTPError
except ImportError:
    print("Need `pip install huggingface_hub`", file=sys.stderr)
    sys.exit(1)


LABEL_STUDIO_DOCKER = "heartexlabs/label-studio:latest"

DOCKERFILE = f"""FROM {LABEL_STUDIO_DOCKER}

# HF Spaces runs the container as a non-root user (UID 1001).
# Pre-create data + writable dirs so Label Studio can boot without a bucket.
USER root
RUN mkdir -p /data /label-studio/data \\
    && chown -R 1001:0 /data /label-studio/data \\
    && chmod -R 775 /data /label-studio/data
USER 1001

# HuggingFace Spaces expects the app on port 7860
ENV PORT=7860
EXPOSE 7860

ENV LABEL_STUDIO_HOST=0.0.0.0
ENV LABEL_STUDIO_PORT=7860
ENV LABEL_STUDIO_COPY_STATIC_DATA=true
"""

README_MD = """---
title: TinyAya Benchmark Review
emoji: 🟧
colorFrom: yellow
colorTo: pink
sdk: docker
app_port: 7860
pinned: false
license: apache-2.0
short_description: Human review of TinyAya children's LLM benchmark
---

Label Studio instance for reviewing the TinyAya v2 children's LLM benchmark —
validating translations, grading model responses, and flagging bad items.

Import the labeling interface from `labeling_config.xml` and the
stratified tasks from `tasks_shard*.json` after the Space is running.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--space-id", required=True, help="e.g. batuhan/tinyaya-bench-review")
    ap.add_argument("--admin-email", required=True)
    ap.add_argument("--admin-password", required=True)
    ap.add_argument("--bucket-name", default="label-studio-data")
    ap.add_argument("--private", action="store_true", default=True)
    ap.add_argument("--no-bucket", action="store_true", help="Skip bucket creation (set up storage manually)")
    ap.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    args = ap.parse_args()

    if not args.token:
        print("ERROR: provide --token or set HF_TOKEN env var", file=sys.stderr)
        sys.exit(2)

    api = HfApi(token=args.token)

    # ---------- 1. Create the Space ----------
    print(f"Creating Space {args.space_id} (Docker SDK, private={args.private})")
    try:
        api.create_repo(
            repo_id=args.space_id,
            repo_type="space",
            space_sdk="docker",
            private=args.private,
            exist_ok=True,
        )
    except HfHubHTTPError as e:
        print(f"WARN: create_repo said: {e}")

    # ---------- 2. Upload Dockerfile + README ----------
    print("Uploading Dockerfile + README.md")
    api.upload_file(
        path_or_fileobj=DOCKERFILE.encode(),
        path_in_repo="Dockerfile",
        repo_id=args.space_id,
        repo_type="space",
        commit_message="Add Label Studio Dockerfile",
    )
    api.upload_file(
        path_or_fileobj=README_MD.encode(),
        path_in_repo="README.md",
        repo_id=args.space_id,
        repo_type="space",
        commit_message="Add Space README",
    )

    # ---------- 3. Set env vars (signup restriction + persistence) ----------
    print("Setting Space variables + secrets")
    variables = {
        "LABEL_STUDIO_DISABLE_SIGNUP_WITHOUT_LINK": "true",
        "LABEL_STUDIO_USERNAME": args.admin_email,
        "LABEL_STUDIO_BASE_DATA_DIR": "/data",
        "STORAGE_PERSISTENCE": "1",
    }
    secrets_kv = {
        "LABEL_STUDIO_PASSWORD": args.admin_password,
        "SECRET_KEY": secrets.token_urlsafe(48),
    }
    for k, v in variables.items():
        api.add_space_variable(args.space_id, k, v)
    for k, v in secrets_kv.items():
        api.add_space_secret(args.space_id, k, v)

    # ---------- 4. (Optional) Bucket for persistence ----------
    if not args.no_bucket:
        try:
            from huggingface_hub import Volume  # newer hub versions
            print(f"Attaching bucket {args.bucket_name} at /data")
            api.set_space_volumes(
                args.space_id,
                volumes=[Volume(type="bucket", source=f"/{args.bucket_name}", mount_path="/data")],
            )
        except ImportError:
            print(
                "huggingface_hub lacks Volume support — attach a bucket manually:\n"
                f"  hf buckets create /{args.bucket_name}\n"
                "  Space Settings → Storage Buckets → mount at /data"
            )

    # ---------- 5. Factory rebuild so mounts + vars take effect ----------
    print("Factory rebuilding Space")
    api.restart_space(args.space_id, factory_reboot=True)

    print(f"\n✓ Done. Visit https://huggingface.co/spaces/{args.space_id}")
    print("\nNext steps once the Space is live:")
    print("  1. Log in with the admin email/password above")
    print("  2. Create a new project → Labeling Interface → paste labeling_config.xml")
    print("  3. Data Manager → Import → upload tasks_shard01.json, tasks_shard02.json")
    print("  4. Use the Data Manager filter on `language` to work one language at a time")


if __name__ == "__main__":
    main()
