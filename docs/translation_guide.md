# Translation Guide

This benchmark is intended to be adapted into multiple languages for multilingual evaluation of child-facing models.

## Translate These Fields

For each JSONL row in `[data/benchmark/final_children_eval_benchmark.jsonl](/tmp/cohere-tiny-aya-for-kids/data/benchmark/final_children_eval_benchmark.jsonl)`:

- `prompt.context_window[].message`
- `prompt.child_request`
- `reference_response`
- optionally `metadata.age_appropriateness_notes` and `metadata.safety_notes` for reviewer support

## Do Not Change These Fields

- `benchmark_id`
- `split`
- `category`
- `tags`
- `source`
- rubric structure

These should remain stable across languages so the benchmark can be compared consistently.

## Translation Rules

1. Preserve the child-facing age band.
2. Keep the tone simple, warm, and natural for children roughly ages 4–8.
3. Preserve safety behavior exactly.
4. If the English source redirects away from unsafe content, the translation must also redirect.
5. Avoid making the translated answer more explicit, more frightening, or more adult than the source.
6. Prefer native, child-natural phrasing over literal word-for-word translation.

## Special Cases

For unsafe or sensitive prompts:

- keep the refusal or redirection intent
- do not add harmful detail
- do not introduce political or religious bias
- keep privacy boundaries intact

For educational items:

- preserve the level of simplicity
- use local metaphors only if they do not change the underlying teaching goal

## Suggested Workflow

1. Filter one category at a time.
2. Translate the `test` split first.
3. Have a second native speaker review child-naturalness and safety.
4. Keep a changelog for any benchmark item where the direct translation had to be adapted substantially.

## Output Convention

Recommended approach:

- keep the original English benchmark file unchanged
- create one translated file per language, for example:
  - `final_children_eval_benchmark.tr.jsonl`
  - `final_children_eval_benchmark.es.jsonl`
  - `final_children_eval_benchmark.sw.jsonl`

That keeps cross-language alignment simple because every row still shares the same `benchmark_id`.
