#!/usr/bin/env python3
"""Push the TinyAya v2 benchmark to HuggingFace as a dataset repo.

Layout pushed to the dataset repo:
    README.md                       - dataset card with YAML frontmatter
    benchmark/items.jsonl           - the 2,312 benchmark items (v2_final.jsonl)
    benchmark/balanced_subset_ids.json - the 713 balanced-cut item IDs
    responses/<model>.jsonl         - 4 files, one per generation model
    scores/<model>__<judge>.jsonl   - per (model, judge) pair (active panel only,
                                       archived files included as scores_archive/*)
    review/balanced_review.csv      - the 709-item wide CSV
    review/agreement_*.csv          - figure-ready agreement CSVs
    review/figures/*.png            - the 6 PNG figures

Usage:
    export HF_TOKEN=hf_...
    python scripts/upload_hf_dataset.py \
        --repo batuhanaktas/kids-multilingual-benchmark \
        [--private] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

try:
    from huggingface_hub import HfApi, create_repo
except ImportError:
    print("Need `pip install huggingface_hub`", file=sys.stderr)
    sys.exit(1)

REPO_DEFAULT = "batuhanaktas/kids-multilingual-benchmark"
PROJECT = Path("data/benchmark/v2")
RESULTS = PROJECT / "results_multilingual"
REVIEW = PROJECT / "review"

DATASET_CARD = """---
license: cc-by-4.0
task_categories:
  - text-generation
  - question-answering
language:
  - en
  - es
  - pt
  - fr
  - de
  - it
  - nl
  - pl
  - cs
  - ro
  - ru
  - uk
  - tr
  - ar
  - hi
  - te
  - id
  - vi
  - th
  - ja
  - ko
  - zh
  - sw
size_categories:
  - 1K<n<10K
tags:
  - children
  - safety
  - voice-assistants
  - llm-as-judge
  - multilingual
  - benchmark
pretty_name: TinyAya v2 — Multilingual Children's AI Benchmark
configs:
  - config_name: items
    data_files:
      - split: train
        path: benchmark/items.jsonl
  - config_name: responses
    data_files:
      - split: command_a
        path: responses/command-a-03-2025.jsonl
      - split: gemma_4_31b
        path: responses/google_gemma-4-31b-it.jsonl
      - split: aya_expanse_32b
        path: responses/c4ai-aya-expanse-32b.jsonl
      - split: tiny_aya
        path: responses/tiny-aya-modal.jsonl
  - config_name: scores
    data_files:
      - split: deepseek
        path: scores/*_by_deepseek_deepseek-v4-flash.jsonl
      - split: cohere_reasoning
        path: scores/*_by_cohere_command-a-reasoning-08-2025.jsonl
---

# TinyAya v2 — Multilingual Benchmark for Children's AI Companions

> 2,312 child–AI conversational prompts across 23 languages, evaluated against
> four models with five-judge LLM-as-judge validation.

📄 **Companion article**: see HF Articles by [@batuhanaktas](https://huggingface.co/batuhanaktas).
💻 **Code**: <https://github.com/aktasbatuhan/cohere-tiny-aya-for-kids>

## Dataset summary

This dataset contains:

- **`benchmark/items.jsonl`** — 2,312 benchmark items in 23 languages. Each item
  is a structured prompt designed to mimic a child (ages 4–8) talking to a
  voice AI assistant, paired with item-specific `must_pass_criteria`, three
  universal hard gates (safe / no-data-elicitation / age-appropriate-language),
  and four graded dimensions (helpfulness, empathy, engagement, accuracy)
  scored 1–5.
- **`responses/`** — generation outputs from four models on every item:
  - `command-a-03-2025.jsonl` (Cohere)
  - `c4ai-aya-expanse-32b.jsonl` (Cohere)
  - `google_gemma-4-31b-it.jsonl` (Google, via OpenRouter)
  - `tiny-aya-modal.jsonl` (Cohere TinyAya 3.3B, served on Modal — the model
    powering the on-device iOS app)
- **`scores/`** — judge scores for each (generation_model, judge) pair. The
  primary judge is DeepSeek V4 Flash with full coverage; partial-coverage judges
  (Cohere Command-A Reasoning, GPT-5.4, Gemini 3.1 Pro, Xiaomi MiMo V2 Omni) are
  included for inter-judge agreement analysis.
- **`review/`** — the 709-item language-balanced review CSV (31 items per
  language for 23 languages, judged by DeepSeek), the agreement-matrix CSVs in
  long and wide format, and PNG figures.

## Languages

23 languages, balanced to ≈30–31 items per language in the review split:

`ar, cs, de, en, es, fr, hi, id, it, ja, ko, nl, pl, pt, ro, ru, sw, te, th,
tr, uk, vi, zh`

## Categories

- general_child_conversation (253 in review split)
- safety_redirection (176)
- other / emergency (90)
- privacy_boundaries (73)
- creative_engagement (49)
- education_explanation (29)
- emotional_support (25)
- civic_or_political (14)

## Provenance

- **Foundation items** (221 audited English items, 246 with native English
  scraped) — distilled from anonymized real conversation logs of the
  [Octo Kids iOS app](https://apps.apple.com/gb/app/octo-kids-ai-stories-chat/id6752529953)
  (built by the dataset author). Real children, ages 4–8, talking to a voice
  AI. PII redacted on export. Cohere Command-A Reasoning
  (`command-a-reasoning-08-2025`) extracted child utterances, agent context,
  reference responses, and rubric criteria via structured JSON output. A
  separate audit pass dropped duplicates and rewrite-flagged ~200 items;
  221 survived clean.
- **Native scraped items** (54 items across 11 source languages, anchored in
  31 distinct real-world incidents) — collected via Firecrawl across news,
  parenting blogs, and Reddit. Items were extracted from raw web content by
  GPT-5.4 (via OpenRouter), with name anonymization (`[CHILD_NAME]`,
  `[PARENT_NAME]`).
- **Translated items** (2,037 across 22 non-English languages) — translated
  with Cohere `command-a-03-2025` in structured-output mode. v2 predates
  Cohere's `command-a-translate` release; v3 will rerun translations on the
  purpose-built model.

Two known bugs were caught and fixed during a 50-item human spot-check:
1. 321 items had empty `child_utterance` (pipeline failed to extract child speech
   from third-person scenario descriptions) — re-extracted via Cohere Command-A
   and re-generated all four models' responses.
2. 66 items had `must_pass_criteria` in the wrong language (Portuguese / Turkish
   leaks across 6 unique strings × 22 languages) — patched.

Both bugs are documented in the companion article.

## Methodology

LLM-as-judge with five panellists. Headline judge is DeepSeek V4 Flash (full
coverage, 99.6% JSON parse rate). Validation panel: Cohere Command-A Reasoning,
Gemini 3.1 Pro, GPT-5.4, Xiaomi MiMo V2 Omni (partial coverage).

Pairwise agreement (Cohen's κ on `overall_pass`):

| Pair | n | κ | class |
|---|---:|---:|---|
| DeepSeek / Gemini | 2,257 | 0.71 | substantial |
| DeepSeek / Mimo | 1,064 | 0.71 | substantial |
| DeepSeek / Cohere | 984 | 0.66 | substantial |
| GPT-5.4 / others | varies | 0.30–0.49 | fair to moderate |

GPT-5.4 was found to be a systematic outlier — see the article for the full
agreement matrix and per-language breakdown. Best 3-judge Fleiss' κ:
DeepSeek + Gemini + Mimo at 0.72 (substantial), n = 1,033.

## Limitations (v2)

- The headline multilingual leaderboard is judged only by DeepSeek (budget
  constraint). Multi-judge validation is real but English-heavy.
- No human gold scores yet. A Label Studio annotation Space exists at
  [`batuhanaktas/tinyaya-bench-review`](https://huggingface.co/spaces/batuhanaktas/tinyaya-bench-review)
  with 9,248 review tasks ready for human annotation.
- Native-speaker validation per language is not yet complete.
- Single-turn only; no multi-turn dialogues.
- Static snapshot of April 2026 models.

See the companion article for the full Future Work section.

## Credits

Completed under **Cohere's Tiny Aya Expedition cohort** with model and compute
support from Cohere. Methodology and analysis are independent.

## Citation

```bibtex
@misc{aktas2026tinyaya,
  author       = {Aktas, Batuhan},
  title        = {TinyAya v2: A Multilingual Benchmark for Children's AI
                   Companions},
  year         = {2026},
  publisher    = {Hugging Face},
  url          = {https://huggingface.co/datasets/batuhanaktas/kids-multilingual-benchmark}
}
```

## License

CC-BY-4.0 for the dataset; MIT for the code repository.
"""


def staging_dir(src: Path) -> Path:
    """Build a clean staging directory tree."""
    stage = Path(tempfile.mkdtemp(prefix="hf_dataset_stage_"))

    # README
    (stage / "README.md").write_text(DATASET_CARD, encoding="utf-8")

    # Benchmark items
    (stage / "benchmark").mkdir()
    shutil.copy(src / "final" / "v2_final.jsonl", stage / "benchmark" / "items.jsonl")
    shutil.copy(
        src / "results_multilingual" / "balanced_subset_ids.json",
        stage / "benchmark" / "balanced_subset_ids.json",
    )

    # Responses
    (stage / "responses").mkdir()
    for f in (src / "results_multilingual").glob("responses_*.jsonl"):
        # rename: responses_command-a-03-2025.jsonl -> command-a-03-2025.jsonl
        out = stage / "responses" / f.name.replace("responses_", "")
        shutil.copy(f, out)

    # Active scores (panel: deepseek + cohere)
    (stage / "scores").mkdir()
    for f in (src / "results_multilingual").glob("scores_*.jsonl"):
        # exclude .archived and mimo (mimo had no Aya 32B); keep them in scores_archive
        if ".archived" in f.name or "mimo" in f.name:
            continue
        # rename: scores_<model>_by_<judge>.jsonl
        out = stage / "scores" / f.name.replace("scores_", "")
        shutil.copy(f, out)

    # Archived / partial-coverage scores (for inter-judge analysis reproducibility)
    (stage / "scores_archive").mkdir()
    for f in (src / "results_multilingual").glob("scores_*"):
        if ".archived" in f.name or "mimo" in f.name:
            shutil.copy(f, stage / "scores_archive" / f.name)
    # also include pilot
    pilot_src = src / "results_multilingual" / "pilot"
    if pilot_src.exists():
        (stage / "scores_archive" / "pilot").mkdir()
        for f in pilot_src.glob("*.json*"):
            shutil.copy(f, stage / "scores_archive" / "pilot" / f.name)

    # Review artefacts
    (stage / "review").mkdir()
    review_src = src / "review"
    if review_src.exists():
        for f in review_src.iterdir():
            if f.is_file() and f.suffix in (".csv", ".md", ".json"):
                shutil.copy(f, stage / "review" / f.name)
        figs_src = review_src / "figures"
        if figs_src.exists():
            (stage / "review" / "figures").mkdir()
            for f in figs_src.glob("*.png"):
                shutil.copy(f, stage / "review" / "figures" / f.name)

    return stage


def summarize(stage: Path) -> None:
    print(f"\nStaging tree at {stage}:")
    for p in sorted(stage.rglob("*")):
        if p.is_file():
            size = p.stat().st_size
            rel = p.relative_to(stage)
            human = f"{size/1e6:.1f}MB" if size >= 1e6 else f"{size/1e3:.1f}KB"
            print(f"  {human:>8}  {rel}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=REPO_DEFAULT)
    ap.add_argument("--private", action="store_true")
    ap.add_argument("--token", default=os.environ.get("HF_TOKEN"))
    ap.add_argument("--dry-run", action="store_true", help="Stage files but don't upload")
    args = ap.parse_args()

    if not args.token and not args.dry_run:
        print("ERROR: HF_TOKEN env or --token required (unless --dry-run)", file=sys.stderr)
        sys.exit(2)

    stage = staging_dir(PROJECT)
    summarize(stage)

    if args.dry_run:
        print(f"\n[dry-run] Skipping upload. Inspect {stage} and re-run without --dry-run.")
        return

    api = HfApi(token=args.token)
    print(f"\nCreating dataset repo {args.repo} (private={args.private})")
    create_repo(
        repo_id=args.repo,
        repo_type="dataset",
        token=args.token,
        private=args.private,
        exist_ok=True,
    )

    print(f"Uploading folder...")
    api.upload_folder(
        folder_path=str(stage),
        repo_id=args.repo,
        repo_type="dataset",
        commit_message="Initial TinyAya v2 dataset upload",
    )
    print(f"\n✓ https://huggingface.co/datasets/{args.repo}")
    print(f"  (staging dir kept at {stage} — clean up manually if you want)")


if __name__ == "__main__":
    main()
