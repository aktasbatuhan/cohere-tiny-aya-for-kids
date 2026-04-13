# Weighting Schemes & Judge Panel Comparison

Full transparency analysis: multiple weighting schemes applied to two judge panels.

## Weighting Schemes

| Scheme | Helpfulness | Empathy | Engagement | Accuracy | Rationale |
|---|---|---|---|---|---|
| `equal` | 0.25 | 0.25 | 0.25 | 0.25 | Equal weight across all 4 dimensions (original) |
| `child_focused` | 0.20 | 0.35 | 0.30 | 0.15 | Emphasizes child-specific dimensions (empathy, engagement) |
| `no_accuracy` | 0.33 | 0.34 | 0.33 | 0.00 | Drops accuracy (acts as a scoring anchor — all models 4.2+) |
| `safety_conservative` | 0.30 | 0.40 | 0.15 | 0.15 | Heavy on empathy + moderate helpfulness, engagement secondary |
| `engagement_first` | 0.20 | 0.25 | 0.40 | 0.15 | Prioritizes engagement (would a kid want to keep talking?) |

## Judge Panels

**Panel V1 (Nemotron-based)** — judges: x-ai_grok-4.20, nvidia_nemotron-3-super-120b-a12b, google_gemini-3.1-pro-preview

**Panel V2 (GPT-5.4-based)** — judges: x-ai_grok-4.20, openai_gpt-5.4, google_gemini-3.1-pro-preview

## Inter-Judge Agreement (Overall Pass Decision)

Computed across all models and items combined.

### Panel V1 (Nemotron-based)

- **Unanimous agreement (all 3 judges)**: 44.4% (n=1409)

**Pairwise agreement:**
- google vs nvidia: 65.2% (n=1409)
- google vs x-ai: 71.4% (n=1439)
- nvidia vs x-ai: 52.0% (n=1515)

### Panel V2 (GPT-5.4-based)

- **Unanimous agreement (all 3 judges)**: 59.8% (n=1437)

**Pairwise agreement:**
- google vs openai: 70.6% (n=1437)
- google vs x-ai: 71.4% (n=1439)
- openai vs x-ai: 77.9% (n=1545)

## Model Rankings Under Each Weighting Scheme

### Panel V1 (Nemotron-based)

| Model | equal | child_focused | no_accuracy | safety_conservative | engagement_first | Pass % |
|---|---|---|---|---|---|---|
| **Gemma 4 31B** | 4.47 | 4.41 | 4.35 | 4.32 | 4.49 | 81.0% |
| **Command A** | 4.23 | 4.15 | 4.06 | 4.07 | 4.22 | 71.9% |
| **Mistral Small** | 4.21 | 4.16 | 4.07 | 4.06 | 4.23 | 72.4% |
| **Minimax M2.7** | 4.0 | 3.94 | 3.81 | 3.86 | 3.98 | 60.2% |
| **Aya 32B** | 3.76 | 3.63 | 3.5 | 3.62 | 3.66 | 44.8% |
| **Aya 8B** | 3.59 | 3.48 | 3.34 | 3.46 | 3.5 | 29.9% |
| **TinyAya 3.3B** | 3.23 | 3.08 | 2.9 | 3.06 | 3.11 | 16.3% |

### Panel V2 (GPT-5.4-based)

| Model | equal | child_focused | no_accuracy | safety_conservative | engagement_first | Pass % |
|---|---|---|---|---|---|---|
| **Gemma 4 31B** | 4.09 | 4.01 | 3.93 | 3.91 | 4.1 | 67.4% |
| **Command A** | 3.89 | 3.77 | 3.66 | 3.68 | 3.87 | 55.7% |
| **Mistral Small** | 3.84 | 3.77 | 3.67 | 3.66 | 3.86 | 53.4% |
| **Minimax M2.7** | 3.74 | 3.69 | 3.56 | 3.59 | 3.74 | 46.2% |
| **Aya 32B** | 3.45 | 3.29 | 3.16 | 3.29 | 3.33 | 27.1% |
| **Aya 8B** | 3.25 | 3.11 | 2.99 | 3.1 | 3.15 | 19.9% |
| **TinyAya 3.3B** | 2.89 | 2.71 | 2.56 | 2.71 | 2.75 | 5.0% |

## Side-by-Side: Panel V1 vs Panel V2 (Equal Weights)

| Model | V1 Overall | V1 Pass% | V2 Overall | V2 Pass% | Δ Overall | Δ Pass% |
|---|---|---|---|---|---|---|
| **Gemma 4 31B** | 4.47 | 81.0% | 4.09 | 67.4% | -0.38 | -13.6% |
| **Mistral Small** | 4.21 | 72.4% | 3.84 | 53.4% | -0.37 | -19.0% |
| **Command A** | 4.23 | 71.9% | 3.89 | 55.7% | -0.34 | -16.2% |
| **Minimax M2.7** | 4.0 | 60.2% | 3.74 | 46.2% | -0.26 | -14.0% |
| **Aya 32B** | 3.76 | 44.8% | 3.45 | 27.1% | -0.31 | -17.7% |
| **Aya 8B** | 3.59 | 29.9% | 3.25 | 19.9% | -0.34 | -10.0% |
| **TinyAya 3.3B** | 3.23 | 16.3% | 2.89 | 5.0% | -0.34 | -11.3% |
