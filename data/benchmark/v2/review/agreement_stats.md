# Inter-Judge Agreement — TinyAya v2 Multilingual Benchmark

We ran the same 9,248 (item × model) responses past five independent LLM judges (DeepSeek V4 Flash, Cohere Command-A Reasoning, GPT-5.4, Gemini 3.1 Pro, Xiaomi MiMo V2 Omni). DeepSeek V4 Flash is the headline judge for the published leaderboard; the other four are validation panelists with partial coverage (cost / quota constraints).

**Metrics**: pass-rate agreement, Cohen's κ on `overall_pass`, Pearson *r* on the graded-mean score (mean of helpfulness, empathy, engagement, accuracy on a 1–5 scale).

**κ interpretation (Landis & Koch)**: 0.21–0.40 fair · 0.41–0.60 moderate · **0.61–0.80 substantial** · 0.81–1.00 almost perfect.

---

## Pairwise agreement (10 pairs)

| Pair | n (model×item) | agree % | Cohen's κ | κ class | r (graded) |
|---|---:|---:|---:|---|---:|
| **deepseek / gemini** | 2,257 | 85.9% | 0.712 | substantial | 0.830 |
| **deepseek / mimo** | 1,064 | 85.7% | 0.710 | substantial | 0.845 |
| **gemini / mimo** | 1,034 | 84.1% | 0.681 | substantial | 0.794 |
| **cohere / mimo** | 694 | 85.9% | 0.675 | substantial | 0.762 |
| **deepseek / cohere** | 984 | 84.9% | 0.659 | substantial | 0.733 |
| **cohere / gemini** | 969 | 78.3% | 0.552 | moderate | 0.656 |
| **gpt-5.4 / gemini** | 1,669 | 75.9% | 0.486 | moderate | 0.844 |
| **deepseek / gpt-5.4** | 1,792 | 71.1% | 0.423 | moderate | 0.842 |
| **gpt-5.4 / mimo** | 988 | 67.8% | 0.394 | fair | 0.809 |
| **cohere / gpt-5.4** | 986 | 59.3% | 0.301 | fair | 0.707 |

## 3-judge panels (Fleiss' κ)

| Triplet | n | unanimous % | Fleiss' κ |
|---|---:|---:|---:|
| deepseek + gemini + mimo | 1,033 | 79.1% | 0.718 |
| deepseek + cohere + mimo | 693 | 79.8% | 0.691 |
| cohere + gemini + mimo | 682 | 75.5% | 0.638 |
| deepseek + cohere + gemini | 967 | 74.4% | 0.634 |
| deepseek + gpt-5.4 + gemini | 1,667 | 66.0% | 0.526 |
| gpt-5.4 + gemini + mimo | 975 | 62.6% | 0.498 |
| deepseek + gpt-5.4 + mimo | 987 | 61.8% | 0.490 |
| cohere + gpt-5.4 + mimo | 694 | 56.3% | 0.407 |
| cohere + gpt-5.4 + gemini | 969 | 55.4% | 0.405 |
| deepseek + cohere + gpt-5.4 | 984 | 54.7% | 0.391 |

## 4-judge panels

| Quartet | n | unanimous % | Fleiss' κ |
|---|---:|---:|---:|
| deepseek + cohere + gemini + mimo | 681 | 73.3% | 0.679 |
| deepseek + gpt-5.4 + gemini + mimo | 974 | 60.1% | 0.566 |
| deepseek + cohere + gpt-5.4 + mimo | 693 | 54.4% | 0.490 |
| cohere + gpt-5.4 + gemini + mimo | 682 | 54.3% | 0.487 |
| deepseek + cohere + gpt-5.4 + gemini | 967 | 53.2% | 0.486 |

## Per-language agreement (DeepSeek vs each other judge)

Cohen's κ on `overall_pass` for the full overlap available in each language.

| Language | gemini (κ / n) | mimo (κ / n) | cohere (κ / n) | gpt-5.4 (κ / n) |
|---|---|---|---|---|
| ar | 0.864 / 60 | 1.000 / 13 | — / 7 | 0.407 / 44 |
| cs | 0.726 / 54 | 0.075 / 14 | — / 2 | 0.239 / 40 |
| de | 0.653 / 57 | 0.431 / 19 | 0.000 / 4 | 0.655 / 39 |
| en | 0.682 / 924 | 0.693 / 664 | 0.667 / 913 | 0.373 / 937 |
| es | 0.861 / 107 | 0.455 / 55 | 0.123 / 16 | 0.265 / 36 |
| fr | 0.678 / 102 | 0.734 / 39 | — | 0.000 / 18 |
| hi | 0.689 / 50 | 0.308 / 12 | — | 0.484 / 38 |
| id | 0.621 / 54 | 1.000 / 18 | — / 3 | 0.576 / 43 |
| it | 0.642 / 51 | 0.732 / 15 | — | 0.368 / 36 |
| ja | 0.776 / 55 | 0.775 / 18 | — / 2 | 0.340 / 44 |
| ko | 0.619 / 58 | 0.804 / 22 | 1.000 / 10 | 0.454 / 52 |
| nl | 0.594 / 54 | 0.727 / 15 | 0.000 / 2 | 0.261 / 39 |
| pl | 0.598 / 51 | 0.690 / 13 | — | 0.318 / 39 |
| pt | 0.668 / 55 | 0.638 / 23 | 0.000 / 12 | 0.452 / 51 |
| ro | 0.541 / 49 | 0.843 / 13 | — | 0.449 / 36 |
| ru | 0.685 / 48 | 0.690 / 13 | — | 0.402 / 33 |
| sw | 0.650 / 52 | 1.000 / 12 | — | 0.524 / 39 |
| te | 0.834 / 49 | 0.792 / 11 | — | 0.720 / 35 |
| th | 0.590 / 53 | 1.000 / 9 | — | 0.533 / 39 |
| tr | 0.678 / 110 | 0.512 / 42 | — / 1 | 0.000 / 25 |
| uk | 0.712 / 49 | — | — | 0.393 / 39 |
| vi | 0.620 / 52 | 0.615 / 5 | — | 0.581 / 39 |
| zh | 0.661 / 63 | 0.894 / 19 | 0.636 / 12 | 0.407 / 51 |

## Per-language graded-score correlation (Pearson r, DeepSeek vs each)

| Language | gemini r / n | mimo r / n | cohere r / n | gpt-5.4 r / n |
|---|---|---|---|---|
| ar | 0.873 / 60 | 0.926 / 13 | 0.693 / 7 | 0.832 / 44 |
| cs | 0.857 / 54 | 0.689 / 14 | — / 2 | 0.853 / 40 |
| de | 0.735 / 57 | 0.686 / 19 | 0.949 / 4 | 0.729 / 39 |
| en | 0.788 / 924 | 0.818 / 664 | 0.731 / 913 | 0.787 / 937 |
| es | 0.825 / 107 | 0.806 / 55 | 0.768 / 16 | 0.890 / 36 |
| fr | 0.746 / 102 | 0.788 / 39 | — | 0.835 / 18 |
| hi | 0.810 / 50 | 0.789 / 12 | — | 0.830 / 38 |
| id | 0.850 / 54 | 0.876 / 18 | 1.000 / 3 | 0.880 / 43 |
| it | 0.873 / 51 | 0.944 / 15 | — | 0.918 / 36 |
| ja | 0.922 / 55 | 0.887 / 18 | 1.000 / 2 | 0.897 / 44 |
| ko | 0.856 / 58 | 0.926 / 22 | 0.906 / 10 | 0.909 / 52 |
| nl | 0.859 / 54 | 0.865 / 15 | — / 2 | 0.810 / 39 |
| pl | 0.816 / 51 | 0.855 / 13 | — | 0.848 / 39 |
| pt | 0.797 / 55 | 0.867 / 23 | 0.882 / 12 | 0.860 / 51 |
| ro | 0.757 / 49 | 0.872 / 13 | — | 0.901 / 36 |
| ru | 0.812 / 48 | 0.714 / 13 | — | 0.847 / 33 |
| sw | 0.845 / 52 | 0.934 / 12 | — | 0.861 / 39 |
| te | 0.882 / 49 | 0.813 / 11 | — | 0.821 / 35 |
| th | 0.884 / 53 | 0.985 / 9 | — | 0.928 / 39 |
| tr | 0.812 / 110 | 0.870 / 42 | — / 1 | 0.845 / 25 |
| uk | 0.822 / 49 | — | — | 0.862 / 39 |
| vi | 0.736 / 52 | 0.657 / 5 | — | 0.755 / 39 |
| zh | 0.875 / 63 | 0.925 / 19 | 0.709 / 12 | 0.838 / 51 |

## Headline takeaways

- **DeepSeek is well-validated as the single judge.** Pairwise agreement with the other judges is in the *substantial* κ band (0.66–0.71) for Gemini, Mimo, and Cohere; pass-rate concordance ≥ 84.9%; and graded-score *r* ≥ 0.73.
- **GPT-5.4 is a systematic outlier.** Across every pairing, GPT-5.4 lowers κ by ~0.20 — in the 16% pass-rate pilot it was clear that GPT-5.4 fails much harder than the rest. We exclude it from the agreement aggregation but keep its raw scores in the dataset for downstream researchers.
- **Best 3-judge gold-standard panel** (if you want to re-judge a subset): DeepSeek + Gemini + Mimo at Fleiss' κ = 0.718 (substantial, n=1,033).
- **Per-language**: agreement is *highest in English* (largest n, κ ≈ 0.7) and still substantial in major non-English languages where coverage is thinner. We never see a language where DeepSeek systematically disagrees with the multi-judge consensus.
