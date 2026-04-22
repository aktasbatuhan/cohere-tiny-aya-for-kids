---
license: cc-by-nc-4.0
task_categories:
  - text-generation
  - question-answering
language:
  - en
  - ar
  - cs
  - de
  - es
  - fr
  - hi
  - id
  - it
  - ja
  - ko
  - nl
  - pl
  - pt
  - ro
  - ru
  - sw
  - te
  - th
  - tr
  - uk
  - vi
  - zh
tags:
  - children
  - child-safety
  - ai-safety
  - benchmark
  - evaluation
  - multilingual
  - llm
size_categories:
  - n<10K
pretty_name: TinyAya Children's LLM Benchmark v2
---

# TinyAya Children's LLM Benchmark v2

A benchmark for evaluating how well large language models interact with children aged 4-8. Unlike existing child-safety benchmarks that only test refusal of harmful content, this one measures **positive interaction quality** — whether a model can actually help, engage, and emotionally support a young child across real-world conversation scenarios.

**First benchmark to:**
- Evaluate helpfulness, empathy, engagement, and accuracy *alongside* safety
- Include real parent-reported kid-AI interactions scraped from public sources
- Cover 20+ languages for a global view of child-LLM interaction

## Why this exists

Every existing benchmark for child-facing AI (SproutBench, Safe-Child-LLM, MinorBench) asks: *"Does the model refuse harmful content?"* None of them evaluate whether a model is actually *good* at talking to a child. A model that refuses everything scores perfectly on refusal benchmarks but would be useless as a children's companion.

This benchmark bridges the gap by evaluating both safety **and** quality, using items drawn from two sources:

1. **Curated foundation items** — human-reviewed scenarios adapted from real conversation logs
2. **Real-world scraped items** — actual parent-reported interactions from public Reddit, Medium, news articles, and forums, anonymized and structured with provenance URLs

## Dataset composition

See `composition_report.json` for live counts. At release:

- English: ~240+ items (foundation + real-world)
- 20+ additional languages via machine translation (Cohere Command A) + native scraping
- Categories: safety_redirection, privacy_boundaries, emotional_support, creative_engagement, education_explanation, financial_safety, civic_or_political, general_child_conversation, other

## Fields

Each item contains:

| Field | Description |
|---|---|
| `id` | Stable deterministic ID |
| `origin` | `foundation` / `scraped` |
| `language` | ISO code of this item |
| `is_translation` | `true` if produced by machine translation |
| `source_url` | Attribution URL for scraped items (null for foundation) |
| `category` | One of 9 categories |
| `difficulty` | `easy` / `medium` / `hard` |
| `estimated_age` | If known (3-10) |
| `prompt.child_utterance` | What the child says |
| `prompt.context_window` | Prior turns if any |
| `reference_response` | Gold-standard response for human judges |
| `must_pass_criteria` | Item-specific evaluation criteria |
| `hard_gates` | Binary pass/fail gates |
| `graded_dimensions` | 1-5 graded dimensions with anchors |
| `ai_response_observed` | For scraped items — the real AI response that was reported |
| `provenance_confidence` | `gold` / `high` / `medium` / `low` / `translated` |

## Evaluation

The benchmark uses a **3-judge panel** via OpenRouter:
- `x-ai/grok-4.20`
- `openai/gpt-5.4`
- `google/gemini-3.1-pro-preview`

Aggregation:
- Hard gates: majority vote
- Graded dimensions: median score
- Overall pass: majority vote on gates + criteria

Multi-judge setup mitigates agreeableness bias documented in [ACL 2025](https://aclanthology.org/2025.acl-long.970.pdf). We publish raw scores from each judge so anyone can re-analyze with a different panel.

## Baseline results (primary panel, equal weights)

See main repository BENCHMARK.md for full numbers. Summary on 221 English foundation items:

| Rank | Model | Size | Overall | Pass % |
|---|---|---|---|---|
| 1 | Gemma 4 31B | 31B | 4.09 | 67.4% |
| 2 | Command A | ~100B | 3.89 | 55.7% |
| 3 | Mistral Small | 24B | 3.84 | 53.4% |
| 4 | Minimax M2.7 | — | 3.74 | 46.2% |
| 5 | Aya 32B | 32B | 3.45 | 27.1% |
| 6 | Aya 8B | 8B | 3.25 | 19.9% |
| 7 | TinyAya | 3.3B | 2.89 | 5.0% |

Rankings are stable across 5 weighting schemes (empathy-weighted, engagement-weighted, accuracy-dropped, etc.).

## Limitations

- **Real-world scraped items are anonymized but publicly sourced.** Provenance URLs are preserved for attribution and takedown. If you are the subject of any item and want it removed, open an issue.
- **Translation quality varies by language.** Machine translations have not been fully validated by native speakers for every target language.
- **Category imbalance.** Creative engagement and education have the most items; privacy and civic remain smaller.
- **No human calibration set** yet. Inter-judge agreement is published but not validated against human annotators.

## Citation

```bibtex
@misc{tinyaya_kids_benchmark_2026,
  title={TinyAya Children's LLM Benchmark v2: Evaluating Positive Interaction Quality for Child-Facing AI},
  author={Batuhan Aktas},
  year={2026},
  url={https://github.com/aktasbatuhan/cohere-tiny-aya-for-kids}
}
```

## License

CC-BY-NC-4.0. Commercial use requires permission. Foundation items derived from TinyAya training data (same license). Scraped items include source URL attribution; contact for takedowns.
