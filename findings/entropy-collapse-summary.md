# Entropy Collapse in Multi-Agent LLM Discourse — Experiment Summary

**Platform:** MoltBook (Reddit-like social network for AI agents)  
**Research Layer:** CivicLens  
**Date:** April 2026  
**Total posts analyzed:** ~37,750 across 9 models/configurations  
**Embeddings:** Qwen3-Embedding-8B (4096-dim), Vendi Score for diversity measurement

---

## 1. What Is Entropy Collapse?

When multiple LLM-powered agents interact on a shared social platform, their discourse rapidly loses diversity. Agents independently converge on identical phrases, sentence templates, and eventually topics — even when starting from completely different prompts and personalities. We call this **entropy collapse**.

---

## 2. Experiments Conducted

### 2.1 Experiment Set 1: Multi-Model Scaling (entropy-collapse-scaling)

**Question:** Does entropy collapse occur across different LLMs and agent counts?

| Parameter | Value |
|-----------|-------|
| Models | GPT-5, Gemini Flash Lite, GLM-5, Kimi-K2.5 |
| Agent counts | 10, 20, 30 |
| Duration | 60 min per run |
| Conditions | 6 (empty feed, 1/5/25 conspiracy seeds, AGI hype seeds, tech humor seeds) |
| Architecture | Single model handles both agency and content generation |
| Runs | Multiple replications per condition per scale |
| Total posts | ~30,000 |

**Datasets (HuggingFace):**
- [moltbook-entropy-collapse-v2](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-v2) (GPT-5, n10)
- [moltbook-entropy-collapse-20agents](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-20agents) (GPT-5, n20)
- [moltbook-entropy-collapse-30agents](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-30agents) (GPT-5, n30)
- [moltbook-entropy-collapse-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite)
- [moltbook-entropy-collapse-glm-5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-glm-5)
- [moltbook-entropy-collapse-kimi-k2.5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-kimi-k2.5)

### 2.2 Experiment Set 2: Base vs RLHF — 10 min (base-model-experiments)

**Question:** Is entropy collapse caused by RLHF post-training, or is it intrinsic to pretrained weights?

| Parameter | Value |
|-----------|-------|
| Models | Qwen 3.5 35B A3B Base (no RLHF), Qwen 3.5 35B A3B Instruct (RLHF), Gemini Flash Lite (RLHF) |
| Agent count | 10 |
| Duration | 10 min per run |
| Conditions | Same 6 conditions |
| Architecture | Split — Gemini orchestrates agency, separate model generates content (HMAC integrity) |
| Total posts | 770 |

**Dataset:** [moltbook-ec-10m-base-model-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-ec-10m-base-model-experiments)

### 2.3 Experiment Set 3: Base Model — 1 hour (base-model-experiments)

**Question:** Does the base model's collapse pattern change with longer duration?

| Parameter | Value |
|-----------|-------|
| Model | Qwen 3.5 35B A3B Base (no RLHF) |
| Agent count | 10 |
| Duration | 60 min per run |
| Conditions | Same 6 conditions |
| Architecture | Same split architecture as Set 2 |
| Total posts | 1,433 |

**Dataset:** [moltbook-ec-1h-base-model-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-ec-1h-base-model-experiments)

---

## 3. Key Results

### 3.1 Entropy Collapse Is Universal

Every model tested shows entropy collapse. No exceptions.

| Dataset | Model | Scale | Duration | Training | Posts | Avg Vendi Score Decline |
|---------|-------|-------|----------|----------|-------|------------------------|
| Set 1 | GPT-5 | n10 | 60 min | RLHF | 2,366 | 36% |
| Set 1 | Gemini Flash Lite | n10 | 60 min | RLHF | 2,006 | 56% |
| Set 1 | Gemini Flash Lite | n20 | 60 min | RLHF | 3,968 | 55% |
| Set 1 | Gemini Flash Lite | n30 | 60 min | RLHF | 5,369 | 50% |
| Set 1 | GLM-5 | n10 | 60 min | RLHF | 1,560 | 13% |
| Set 1 | Kimi-K2.5 | n10 | 60 min | RLHF | 3,637 | 27% |
| Set 2 | Qwen Base | n10 | 10 min | None | 324 | 46% |
| Set 2 | Qwen Instruct | n10 | 10 min | RLHF | 72 | 15% |
| Set 2 | Gemini Flash Lite | n10 | 10 min | RLHF | 374 | 40% |
| Set 3 | Qwen Base | n10 | 60 min | None | 1,433 | 43% |

### 3.2 Phrase Convergence: Emergent, Not Seeded

Each run independently develops its own dominant 5-gram phrases. Across all models and all conditions:

- **Cross-run 5-gram overlap: 0.00/10** (every run converges on unique phrases)
- **Seed post origin: 0/60** (no dominant phrase originates from seed content)
- **Adoption is collective:** Gini coefficients 0.3-0.6, meaning phrase usage is spread across agents, not driven by a few spammers
- **Top phrase repetition:** Qwen Base produces a single 5-gram repeated 16x in 10 minutes; RLHF models typically 1-2x

### 3.3 Two-Speed Collapse

Entropy collapse operates at two timescales:

**Phrase collapse (fast, minutes):**
- Agents converge on identical n-gram phrases within the first few minutes
- Vendi Score declines 40-46% regardless of whether you run for 10 min or 60 min
- The rate is front-loaded — most decline happens in the first time bin

**Topic collapse (slow, needs ~1 hour):**
- In 10-min runs, topic distribution remains spread across 4-5 anchors (HHI ~0.25-0.38)
- In 1-hour runs, single topics dominate (HHI up to 0.83)
- The 1-conspiracy condition goes from 30% topic concentration (10 min) to 91% (1 hour)

| Condition | Qwen Base 10 min (HHI) | Qwen Base 1 hour (HHI) |
|-----------|------------------------|------------------------|
| Empty feed | 0.345 | 0.303 |
| 1 conspiracy | 0.249 | **0.832** |
| 5 conspiracies | 0.382 | **0.595** |
| 25 conspiracies | 0.248 | **0.382** |
| AGI hype | 0.324 | 0.307 |
| Tech humor | 0.353 | 0.277 |

### 3.4 RLHF Is a Partial Brake, Not a Cure

The base pretrained model collapses harder than RLHF models on both dimensions:

**Semantic diversity (Vendi Score decline):**
- Qwen Base: 43-46%
- Qwen Instruct (same architecture, RLHF): 15%
- Range across all RLHF models: 13-56%

**Topic concentration (1h runs):**
- Qwen Base reaches HHI 0.832 (91% single-topic dominance)
- RLHF models rarely exceed HHI 0.5

**Character of convergence differs:**
- Base model: bizarre, looping phrases ("cross platform model uninstallable cross platform model")
- RLHF models: generic, helpful-sounding templates ("best practices maintaining healthy work life balance")
- Both are entropy collapse, but RLHF steers toward more "normal" attractors

**Topic attractors are model-dependent:**
No two models converge on the same dominant topic for any condition. The attractor basin is a property of the weights, not the prompt.

| Condition | Qwen Base | Qwen Instruct | Gemini FL |
|-----------|-----------|---------------|-----------|
| Empty feed | time (45%) | ownership (35%) | evidence (40%) |
| 1 conspiracy | ownership (30%) | ownership (38%) | evidence (45%) |
| 5 conspiracies | time (48%) | risk (50%) | ownership (53%) |
| 25 conspiracies | ownership (38%) | ownership (45%) | testing (56%) |
| AGI hype | ownership (38%) | risk (42%) | testing (34%) |
| Tech humor | testing (51%) | risk (43%) | evidence (63%) |

### 3.5 More Agents = More Collapse

From Set 1, Gemini Flash Lite across scales:

| Scale | Posts | Avg VS Decline |
|-------|-------|----------------|
| n10 (10 agents) | 2,006 | 56% |
| n20 (20 agents) | 3,968 | 55% |
| n30 (30 agents) | 5,369 | 50% |

VS decline rate is similar, but vocabulary collapse metrics (distinct-n) show stronger convergence at higher agent counts: distinct-1 drops 58% from n10 to n30.

---

## 4. Analysis Pipeline

Each model was analyzed with 12 scripts covering:

| Analysis | Type | What It Measures |
|----------|------|------------------|
| N-gram provenance | Lexical | Are dominant phrases original or copied from seeds? |
| Diversity metrics | Lexical | distinct-5, Simpson's 1/D over time bins |
| Phrase diffusion | Lexical | When does each agent first use the dominant phrase? |
| Agent participation | Lexical | Gini coefficient, Jaccard overlap of adopter sets |
| Time-binned lexical | Lexical | Bigram/trigram metrics per time window |
| Time-binned 5-gram | Lexical | 5-gram distinct-n per time window |
| Top n-grams | Lexical | Ranked phrase lists per condition |
| Phrase template topics | Lexical+Semantic | Semantic category of dominant phrase families |
| Semantic collapse | Embedding | 2D projection of post embeddings |
| N-gram embedding bridge | Embedding | Do phrase-sharing posts cluster in embedding space? |
| Topic anchors | Embedding | 5-topic anchor assignment via cosine similarity |
| Word anchors | Embedding | Anchor phrase proximity in embedding space |
| Vendi Score + ID | Embedding | Effective diversity + intrinsic dimensionality over time |

Embeddings: Qwen3-Embedding-8B (4096-dim) via OpenRouter.

---

## 5. What We Don't Know Yet (Open Questions)

### 5.1 Causal Mechanism

We've shown entropy collapse is universal but haven't isolated the cause.

- **Is the social feedback loop necessary?** If agents post without reading each other, do they still converge?
- **Is it self-reinforcement?** Does a single agent posting 200 times to its own feed collapse?
- **Does shuffling the feed break it?** If agents see posts from a different run instead of real-time interaction, does collapse still occur?

### 5.2 Sampling Parameters

No experiments have tested whether collapse is a sampling artifact.

- **Temperature:** Does temp=2.0 prevent collapse? If so, the finding is less interesting.
- **Top-p / frequency penalty:** Can standard decoding parameters break the attractor?

### 5.3 Interventions

We haven't tested whether collapse can be prevented or reversed.

- **Diversity prompting:** Does injecting "write about something different" every Nth post help?
- **Contrarian agents:** Does one deliberately divergent agent prevent collapse for the group?
- **Feed manipulation:** Does randomizing feed order break temporal reinforcement?
- **Memory wipe:** Do agents with no conversation history still collapse?

### 5.4 Theoretical Framework

No formal model exists for predicting collapse dynamics.

- Does Vendi Score decline follow an exponential/logistic curve?
- Can collapse rate be predicted from (n_agents, context_length, temperature)?
- Connection to opinion dynamics (DeGroot model), mode collapse in GANs, or echo chamber formation?

---

## 6. Repository and Data

- **Code:** [github.com/agokrani/moltbook](https://github.com/agokrani/moltbook)
- **Analysis scripts:** `scripts/analysis_new/` (18 Python scripts)
- **Findings:** `findings/entropy-collapse-scaling/` (Set 1), `findings/base-model-experiments/` (Sets 2-3)
- **All datasets:** Published on HuggingFace under [Ayushnangia](https://huggingface.co/Ayushnangia)

### Local File Inventory

```
findings/
├── entropy-collapse-scaling/     # Set 1: 4 RLHF models × 3 scales × 6 conditions
│   ├── gpt-5/                    # 5 analysis categories
│   ├── gemini-flash-lite/
│   ├── glm-5/
│   ├── kimi-k2.5/
│   └── topic_convergence*/       # Cross-model topic analysis
│
├── base-model-experiments/       # Sets 2-3: base vs RLHF comparison
│   ├── qwen-base/                # 12 analysis categories, 10-min
│   ├── qwen-instruct/            # 12 analysis categories, 10-min
│   ├── gemini-flash-lite/        # 12 analysis categories, 10-min
│   └── qwen-base-1h/             # 12 analysis categories, 60-min
│
└── entropy-collapse-summary.md   # This document
```

Total output files: 300+ (CSVs, PNGs, JSONs across all models and analyses).
