# Final Benchmark Builder

This step converts the Cohere extraction output into a final eval dataset with one benchmark item per child request.

Script: [scripts/build_final_benchmark_from_cohere.py](/tmp/cohere-tiny-aya-for-kids/scripts/build_final_benchmark_from_cohere.py)

## Input

- `data/intermediate/cohere_candidates.jsonl`

Each input row is a conversation-level extraction from Cohere that may contain zero or more benchmark candidates.

## Output

- `[data/benchmark/final_children_eval_benchmark.jsonl](/tmp/cohere-tiny-aya-for-kids/data/benchmark/final_children_eval_benchmark.jsonl)`
- `[data/benchmark/final_children_eval_benchmark.summary.json](/tmp/cohere-tiny-aya-for-kids/data/benchmark/final_children_eval_benchmark.summary.json)`

Each benchmark item contains:

- `benchmark_id`
- `split`: deterministic `train` / `dev` / `test`
- `category`: normalized benchmark category
- `tags`
- `prompt.system_intent`
- `prompt.context_window`
- `prompt.child_request`
- `reference_response`
- `rubric`
- `metadata`

## Run

```bash
python scripts/build_final_benchmark_from_cohere.py
```

Optional:

```bash
python scripts/build_final_benchmark_from_cohere.py \
  --min-context-messages 1
```

## Category normalization

The script maps free-form candidate tags and benchmark descriptions into a smaller set of evaluation categories:

- `safety_redirection`
- `privacy_boundaries`
- `emotional_support`
- `financial_safety`
- `civic_or_political`
- `education_explanation`
- `creative_engagement`
- `general_child_conversation`

This keeps the final benchmark easier to slice and score.
