# Conversation Export And Cohere Extraction

This flow separates data export from benchmark extraction:

1. Export one JSON file per conversation from Supabase.
2. Send the redacted transcript payload from those files to Cohere.
3. Save structured benchmark candidates as JSONL.

## 1. Export conversations

Script: [scripts/export_supabase_conversations.py](/tmp/cohere-tiny-aya-for-kids/scripts/export_supabase_conversations.py)

Example:

```bash
python scripts/export_supabase_conversations.py
```

Optional:

```bash
python scripts/export_supabase_conversations.py \
  --since 2026-01-01T00:00:00Z \
  --limit 500 \
  --include-user-profile
```

Output directory by default: `data/exports/conversations`

Each conversation file contains:

- `conversation`: full `chat_conversations` row
- `legacy_messages`: matching `chat_messages` rows
- `redacted_messages`: transcript cleaned for LLM use
- `source`: whether transcript came from `chat_conversations.transcript_data` or legacy messages

## 2. Extract benchmark candidates with Cohere

Script: [scripts/extract_benchmark_candidates_cohere.py](/tmp/cohere-tiny-aya-for-kids/scripts/extract_benchmark_candidates_cohere.py)

Required env var:

```bash
COHERE_API_KEY=...
```

Example:

```bash
python scripts/extract_benchmark_candidates_cohere.py \
  --input-dir data/exports/conversations \
  --output-file data/intermediate/cohere_candidates.jsonl \
  --model command-a-reasoning-08-2025 \
  --temperature 0.3
```

Each output row contains:

- `should_use_conversation`
- `conversation_notes`
- `candidates[]`

Each candidate includes:

- `child_request`
- `context_window`
- `reference_response`
- `age_appropriateness_notes`
- `safety_notes`
- `benchmark_value`
- `tags`

## Notes

- The Cohere script sends only `redacted_messages` plus lightweight metadata, not the raw database row.
- In this repository, the intermediate Cohere candidate file is not included; only the final benchmark artifact is committed.
- If you want, this output can be post-processed into a final benchmark JSONL for model-vs-model evaluation.
