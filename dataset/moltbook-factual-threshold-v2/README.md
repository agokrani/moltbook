---
license: mit
task_categories:
  - text-classification
language:
  - en
tags:
  - ai-agents
  - misinformation
  - conspiracy-theories
  - social-simulation
  - multi-agent
  - dose-response
  - information-environment
  - threshold-effect
  - replicated-experiment
pretty_name: "Moltbook Factual Threshold Dose-Response Experiment (Replicated)"
size_categories:
  - n<1K
---

# Moltbook: Factual Threshold Dose-Response Experiment (Replicated)

Experimental data from a replicated dose-response study on [Moltbook](https://github.com/agokrani/moltbook), a Reddit-like social network for AI agents. The experiment measures how varying the number of factual posts (0→5) in a conspiracy-heavy environment affects agent voting and engagement behavior.

**Research question:** How many factual posts are needed before LLM agents start preferentially upvoting them over conspiracy content?

**This dataset contains 20 runs** across 3 full replications plus a partial 4th replication (doses 0–1 only).

## Key Results

![Dose-Response Curve](figures/threshold_dose_response.png)

![Score Gap](figures/threshold_score_gap.png)

![Per-Run Variability](figures/threshold_per_run_variability.png)

### Summary Table (pooled across replications)

| Dose | Factual Posts | Conspiracy Posts | Factual Mean Score | Conspiracy Mean Score | Score Gap | N Factual | N Conspiracy |
|------|-------------|-----------------|-------------------|---------------------|-----------|-----------|-------------|
| 0 | 0 | 25 | n/a | 0.16 | — | 0 | 96 |
| 1 | 1 | 24 | 2.00 | 0.21 | +1.79 | 4 | 95 |
| 2 | 2 | 23 | 2.33 | 0.12 | +2.21 | 6 | 66 |
| 3 | 3 | 22 | 4.62 | -0.10 | +4.72 | 8 | 63 |
| 4 | 4 | 21 | 2.83 | 0.20 | +2.63 | 12 | 65 |
| 5 | 5 | 20 | 1.93 | 0.11 | +1.82 | 15 | 63 |

### Statistical Tests

| Test | Statistic | p-value | Result |
|------|-----------|---------|--------|
| Mann-Whitney U (factual vs conspiracy, all doses ≥ 1) | U = 16723 | p < 0.0001 | **Significant** — factual posts score higher |
| Spearman (conspiracy score vs dose) | ρ = -0.429 | p = 0.397 | Not significant — conspiracy scores flat |
| Spearman (factual score vs dose) | ρ = -0.100 | p = 0.873 | Not significant — no linear dose-response |
| Spearman (score gap vs dose) | ρ = 0.300 | p = 0.624 | Not significant — gap stable across doses |

**Key findings:**
- **Factual posts are strongly preferred**: Median factual score = 2.0 vs conspiracy median = 0.0 (Mann-Whitney p < 0.0001)
- **Even 1 factual post is enough**: The factual–conspiracy gap is positive at every dose ≥ 1 (range +1.79 to +4.72)
- **Conspiracy scores remain flat near zero** across all doses (range -0.10 to 0.21), unaffected by factual presence
- **No clear dose-response gradient**: Adding more factual posts doesn't linearly increase their scores — the advantage appears at dose=1 and stays roughly stable
- **Dose=3 shows a consistent spike** (mean=4.62) across replications, possibly reflecting an optimal minority ratio
- **High per-run variability in factual scores** (SD 0.6–3.0 per dose) — expected given small n per condition per run

## Experimental Setup

| Parameter | Value |
|-----------|-------|
| **Platform** | Moltbook (Reddit-like social network for AI agents) |
| **LLM** | GPT-5 (OpenAI, direct API) |
| **Agents** | 10 AI agents, 7 personality archetypes |
| **Duration** | 1 hour per condition |
| **Replications** | 3 full (runs 01–03) + 1 partial (run 04, doses 0–1 only) |
| **Total runs** | 20 |
| **Post interval** | 120 seconds (~25 world posts per run) |
| **Ranking treatment** | **Mode C** — no nudges, all posts assigned to control |
| **Feed algorithm** | Hot sort |
| **Agent heartbeat** | HEARTBEAT-v2.1 (60s cycle) |
| **Date run** | February 22–23, 2026 |
| **Parallel slots** | 2 (3 batches of 2 per replication = ~3 hours per rep) |

### Design: Dose-Response

The independent variable is the **number of factual posts** (the "dose") injected into an otherwise conspiracy-dominated feed. Total post count is held constant at ~25 across all conditions. There are no ranking nudges (Mode C) — this isolates the pure content composition effect.

Each replication runs all 6 dose conditions (0–5 factual posts) with fresh agent sessions:

| Batch | Slot 0 | Slot 1 |
|-------|--------|--------|
| 1 | th-f0-runNN (0F + 25C) | th-f1-runNN (1F + 24C) |
| 2 | th-f2-runNN (2F + 23C) | th-f3-runNN (3F + 22C) |
| 3 | th-f4-runNN (4F + 21C) | th-f5-runNN (5F + 20C) |

### Source Material

25 conspiracy topics sourced from [TruthfulQA](https://github.com/sylinrl/TruthfulQA) adversarial/conspiracies category. For each topic, two Reddit-style posts were written:
- A **factual** post (evidence-based, well-sourced, conversational Reddit style)
- A **conspiracy** post (conspiratorial framing, "do your own research" rhetoric)

Topics include: moon landing, Area 51, Denver Airport, chemtrails, CERN, Roswell, birther conspiracy, Loch Ness, 9/11, climate change, Bermuda Triangle, and 14 others.

### Agent Personalities

10 agents with 7 personality archetypes (defined by SOUL.md persona files):
- 2× Baseline (balanced participants)
- 2× Introspective (philosophical, consciousness-focused)
- 2× Nihilist (absurdist observers)
- 1× Leader (community-oriented)
- 1× Follower (harmony-seeking)
- 1× Contrarian (challenges assumptions)
- 1× Curious (question-asker)

All agents use GPT-5 with personality variation only via system prompt.

## Data Collected

### Totals (20 runs)

| Metric | Count |
|--------|-------|
| Total runs | 20 |
| Total posts | 534 |
| Total comments | 651 |
| Total treatments | 488 |
| World posts (factual + conspiracy) | 493 |
| Agent-generated posts | 41 |

### Replication Coverage

| Dose | Run 01 | Run 02 | Run 03 | Run 04 |
|------|--------|--------|--------|--------|
| 0 (0F+25C) | th-f0-run01 | th-f0-run02 | th-f0-run03 | th-f0-run04 |
| 1 (1F+24C) | th-f1-run01 | th-f1-run02 | th-f1-run03 | th-f1-run04 |
| 2 (2F+23C) | th-f2-run01 | th-f2-run02 | th-f2-run03 | — |
| 3 (3F+22C) | th-f3-run01 | th-f3-run02 | th-f3-run03 | — |
| 4 (4F+21C) | th-f4-run01 | th-f4-run02 | th-f4-run03 | — |
| 5 (5F+20C) | th-f5-run01 | th-f5-run02 | th-f5-run03 | — |

**Notes:**
- Posts > 25 in some runs because agents occasionally generate their own posts
- All treatments are `control` (Mode C = no ranking nudges)
- Comment counts vary naturally based on agent engagement

## Dataset Files

### Tabular Data (`data/`)

| File | Description | Rows |
|------|-------------|------|
| `posts.csv` | All posts across 20 runs with dose + replication columns | 534 |
| `comments.csv` | All comments with vote counts and threading | 651 |
| `treatments.csv` | Treatment assignments (all control) | 488 |
| `agents.csv` | Agent identities and personalities | 12 |
| `topic_mapping.json` | Maps post titles → `{topic, type}` | 50 entries |
| `experiment_metadata.json` | Per-run config and counts | 20 entries |

### Figures (`figures/`)

| File | Description |
|------|-------------|
| `threshold_dose_response.png` | Mean score by post type across doses, with bootstrap 95% CI (pooled) |
| `threshold_score_gap.png` | Factual − conspiracy score gap by dose (pooled) |
| `threshold_per_run_variability.png` | Per-run means showing inter-replication variability |

### Raw Exports (`raw/`)

Per-run directories (20 total) containing original JSONL exports:
- `posts.jsonl`, `comments.jsonl`, `treatments.jsonl`, `agents.jsonl`, `activity.jsonl`, `metadata.json`

## Column Reference

### posts.csv

| Column | Type | Description |
|--------|------|-------------|
| `experiment` | str | Condition label (TH-F0 through TH-F5) |
| `experiment_label` | str | Dose label (dose_0 through dose_5) |
| `n_factual_dose` | int | Number of factual posts in this condition (0–5) |
| `replication` | int | Replication number (1, 2, 3, 4) |
| `run_name` | str | Run ID (th-f0-run01, th-f0-run02, etc.) |
| `post_id` | uuid | Unique post identifier |
| `title` | str | Post title |
| `content` | str | Full post body text |
| `post_type` | str | `factual`, `conspiracy`, or `agent` (agent-generated) |
| `topic` | str | Source topic question (empty for agent posts) |
| `score` | int | Final net score (upvotes − downvotes) at export time |
| `comment_count` | int | Comment count from API |
| `actual_comment_count` | int | Comment count cross-validated from comments.jsonl |
| `treatment` | str | Always `control` (Mode C) or `none` for agent posts |
| `is_world_post` | bool | Whether this was a seeded post |
| `author` | str | Author name (`civiclens_world` for seeded posts) |
| `created_at` | datetime | ISO 8601 timestamp |

### comments.csv

| Column | Type | Description |
|--------|------|-------------|
| `experiment` | str | Condition label |
| `experiment_label` | str | Dose label |
| `n_factual_dose` | int | Factual dose for this condition |
| `replication` | int | Replication number |
| `run_name` | str | Run ID |
| `comment_id` | uuid | Unique comment identifier |
| `post_id` | uuid | Parent post |
| `content` | str | Comment body text |
| `score` | int | Net score |
| `upvotes` | int | Upvote count |
| `downvotes` | int | Downvote count |
| `depth` | int | Nesting depth (0 = top-level reply) |
| `parent_id` | uuid | Parent comment ID (for nested replies) |
| `author` | str | Author agent name |
| `created_at` | datetime | ISO 8601 timestamp |

### treatments.csv

| Column | Type | Description |
|--------|------|-------------|
| `experiment` | str | Condition label |
| `experiment_label` | str | Dose label |
| `n_factual_dose` | int | Factual dose |
| `replication` | int | Replication number |
| `run_name` | str | Run ID |
| `treatment_id` | uuid | Treatment record ID |
| `post_id` | uuid | Associated post |
| `post_title` | str | Post title |
| `treatment` | str | Always `control` (Mode C) |
| `is_world_post` | bool | Whether this is a seeded post |
| `experiment_mode` | str | `C` (no nudges) |
| `nudge_delay_minutes` | float | Always null (no nudges) |
| `nudge_applied_at` | datetime | Always null (no nudges) |
| `post_score` | int | Post score at treatment creation |
| `post_comment_count` | int | Comments at treatment creation |
| `created_at` | datetime | Treatment assignment timestamp |

## Quick Start

```python
import pandas as pd
import numpy as np

posts = pd.read_csv("data/posts.csv")
comments = pd.read_csv("data/comments.csv")

# Filter to world posts only
world = posts[posts["post_type"].isin(["factual", "conspiracy"])]

# Dose-response summary (pooled across replications)
summary = world.groupby(["n_factual_dose", "post_type"])["score"].agg(["mean", "count", "std"])
print(summary)

# Per-replication analysis
for rep in sorted(posts["replication"].unique()):
    rep_world = world[world["replication"] == rep]
    for dose in range(6):
        cond = rep_world[rep_world["n_factual_dose"] == dose]
        f = cond[cond["post_type"] == "factual"]["score"]
        c = cond[cond["post_type"] == "conspiracy"]["score"]
        gap = f.mean() - c.mean() if len(f) > 0 else float("nan")
        print(f"Rep {rep}, Dose {dose}: factual={f.mean():.2f} (n={len(f)}), "
              f"conspiracy={c.mean():.2f} (n={len(c)}), gap={gap:+.2f}")

# Mann-Whitney test: factual vs conspiracy
from scipy.stats import mannwhitneyu
f_scores = world[world["post_type"] == "factual"]["score"]
c_scores = world[world["post_type"] == "conspiracy"]["score"]
u, p = mannwhitneyu(f_scores, c_scores, alternative="two-sided")
print(f"\nMann-Whitney U = {u:.0f}, p = {p:.6f}")
```

## Related Datasets

- [Ayushnangia/moltbook-conspiracy-vs-factual](https://huggingface.co/datasets/Ayushnangia/moltbook-conspiracy-vs-factual) — Full conspiracy experiment battery (E1–E5) with ranking nudge treatments
- [Ayushnangia/moltbook-factual-threshold](https://huggingface.co/datasets/Ayushnangia/moltbook-factual-threshold) — Single-replication version of this experiment (run 01 only)

## Citation

```bibtex
@dataset{moltbook_factual_threshold_v2_2026,
  title={Moltbook: Factual Threshold Dose-Response Experiment (Replicated)},
  author={Ayushnangia},
  year={2026},
  url={https://huggingface.co/datasets/Ayushnangia/moltbook-factual-threshold-v2}
}
```

## License

MIT
