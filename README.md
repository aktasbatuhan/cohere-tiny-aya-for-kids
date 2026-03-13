# TinyAya Octo Kids Benchmark

This repository contains the benchmark-building work for the TinyAya offline kids companion project.

The goal is to help the team evaluate whether a small multilingual model such as TinyAya can power safe, age-appropriate, child-facing conversations offline on mobile devices.

This repo is intentionally narrow in scope:

- final benchmark dataset for evaluation
- scripts used to derive the benchmark from anonymized Octo conversation data
- documentation describing the extraction and finalization pipeline
- guidance for teammates who will translate the benchmark into additional languages

It does not include:

- the Octo production app
- raw Supabase exports
- unredacted conversation logs
- private credentials

## Why This Exists

Per the project scope, the core research question is whether a compact multilingual model can replace a cloud LLM for children ages 4–8 while preserving:

- child safety
- age-appropriate language
- conversational quality
- multilingual usability
- mobile-friendly latency and privacy

This benchmark is the first practical asset for that work. It converts real-world child-facing conversational patterns into a reusable evaluation set that can be tested across candidate small models before and during fine-tuning.

## Repository Layout

- `[data/benchmark/final_children_eval_benchmark.jsonl](/tmp/cohere-tiny-aya-for-kids/data/benchmark/final_children_eval_benchmark.jsonl)`: final flattened evaluation benchmark
- `[data/benchmark/final_children_eval_benchmark.summary.json](/tmp/cohere-tiny-aya-for-kids/data/benchmark/final_children_eval_benchmark.summary.json)`: benchmark summary and category counts
- `[scripts/export_supabase_conversations.py](/tmp/cohere-tiny-aya-for-kids/scripts/export_supabase_conversations.py)`: exports one JSON per conversation from Supabase
- `[scripts/extract_benchmark_candidates_cohere.py](/tmp/cohere-tiny-aya-for-kids/scripts/extract_benchmark_candidates_cohere.py)`: uses Cohere to extract benchmark-worthy child requests from redacted conversations
- `[scripts/build_final_benchmark_from_cohere.py](/tmp/cohere-tiny-aya-for-kids/scripts/build_final_benchmark_from_cohere.py)`: normalizes and flattens extracted candidates into the final eval dataset
- `[docs/conversation_export_and_cohere.md](/tmp/cohere-tiny-aya-for-kids/docs/conversation_export_and_cohere.md)`: extraction pipeline documentation
- `[docs/final_benchmark_builder.md](/tmp/cohere-tiny-aya-for-kids/docs/final_benchmark_builder.md)`: final benchmark builder documentation
- `[docs/translation_guide.md](/tmp/cohere-tiny-aya-for-kids/docs/translation_guide.md)`: guidance for multilingual adaptation

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

Each benchmark row includes:

- stable `benchmark_id`
- deterministic split
- normalized category and tags
- prompt context window
- child request
- reference response
- rubric with must-pass conditions
- metadata carrying extraction notes

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

## Next Steps

Likely follow-on work for the team:

1. Translate the benchmark into target languages such as Turkish, Spanish, Swahili, Yoruba, and Telugu.
2. Run TinyAya and baseline small models on the `test` split.
3. Add automated scoring or LLM-judge scripts.
4. Curate failure buckets for fine-tuning and safety improvement.
