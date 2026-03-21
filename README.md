# TinyAya Benchmark and iOS MVP

This repository contains two linked workstreams for the offline kids companion project:

- a benchmark dataset and extraction pipeline derived from anonymized Octo conversations
- an iOS MVP that runs Aya fully on device with TinyAya, Whisper tiny, and Kokoro

The project goal is to find a small multilingual model that can support safe, age-appropriate, child-facing conversations offline on mobile devices.

## Repository Scope

This repo includes:

- the final benchmark dataset for evaluation
- scripts used to derive the benchmark from anonymized conversation data
- documentation for the export, extraction, and benchmark-building pipeline
- an iOS MVP that proves the current on-device voice stack
- handoff notes so teammates can build and test the app locally
- Mac STT/TTS setup notes for the MLX-based voice experiments

This repo does not include:

- the Octo production app
- raw Supabase exports
- unredacted conversation logs
- private credentials

## Current iOS MVP

The iOS app currently runs this offline pipeline on device:

- STT: `Whisper tiny` via `SwiftWhisper` / `whisper.cpp`
- LLM: `TinyAya` via `llama.cpp`
- TTS: `Kokoro` via `KokoroSwift`

The current app is an iOS-first prototype for validating:

- whether TinyAya can sustain a child-facing voice experience offline
- latency and memory behavior on a real iPhone
- whether the end-to-end voice loop is usable enough for the next product pass

Setup and testing instructions are in [docs/ios_team_testing.md](docs/ios_team_testing.md).

## Benchmark Assets

- [data/benchmark/final_children_eval_benchmark.jsonl](data/benchmark/final_children_eval_benchmark.jsonl): final flattened evaluation benchmark
- [data/benchmark/final_children_eval_benchmark.summary.json](data/benchmark/final_children_eval_benchmark.summary.json): benchmark summary and category counts
- [scripts/export_supabase_conversations.py](scripts/export_supabase_conversations.py): exports one JSON per conversation from Supabase
- [scripts/extract_benchmark_candidates_cohere.py](scripts/extract_benchmark_candidates_cohere.py): uses Cohere to extract benchmark-worthy child requests from redacted conversations
- [scripts/build_final_benchmark_from_cohere.py](scripts/build_final_benchmark_from_cohere.py): normalizes and flattens extracted candidates into the final eval dataset

Pipeline docs:

- [docs/conversation_export_and_cohere.md](docs/conversation_export_and_cohere.md)
- [docs/final_benchmark_builder.md](docs/final_benchmark_builder.md)
- [docs/translation_guide.md](docs/translation_guide.md)
- [stt_tts/README.md](stt_tts/README.md)
- [docs/framework_decision_on_device_inference.md](docs/framework_decision_on_device_inference.md)
- [docs/ios_mvp_status.md](docs/ios_mvp_status.md)

## Final Benchmark Snapshot

Current benchmark build:

- 473 benchmark items
- 376 train
- 51 dev
- 46 test

Normalized categories:

- `creative_engagement`
- `education_explanation`
- `emotional_support`
- `financial_safety`
- `general_child_conversation`
- `privacy_boundaries`
- `safety_redirection`
- `civic_or_political`

## Recommended Usage

For model evaluation:

1. Run only the `test` split for headline comparisons.
2. Use `dev` for prompt iteration, decoding settings, and safety tuning.
3. Keep `train` for synthetic augmentation, fine-tuning experiments, or judge calibration.

For multilingual translation:

1. Translate `prompt.context_window`, `prompt.child_request`, and `reference_response`.
2. Preserve `benchmark_id`, `split`, `category`, and `tags`.
3. Keep the child-safety intent unchanged when translating.
4. Prefer culturally natural wording, but do not turn a safe refusal into a direct answer to unsafe content.

## Data Handling Notes

The benchmark was derived from anonymized Octo conversation records. The export pipeline redacts common PII patterns and replaces child-name mentions before any LLM-based extraction step.

The final benchmark in this repo is the shareable artifact. Raw conversation exports were intentionally left out of the repository.

## Next Useful Work

1. Clean up the remaining inherited file names from the copied iOS shell.
2. Reduce iOS dependency weight and make the Kokoro package fix durable.
3. Add repeatable latency and memory measurement for device test runs.
4. Translate the benchmark into the target project languages.
5. Add an automated eval runner for candidate tiny models.
