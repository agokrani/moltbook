# Ranking Effect Experiment Battery

**Study:** Does a single early vote nudge (+1/-1) influence what AI agents pay attention to?
**Reference:** "The Ranking Effect" (arXiv:2509.18440) — replication with AI agents on Moltbook

---

## Pilot Results (Exp 1-A, completed 2026-02-17)

| Metric | nudge_up | control | nudge_down |
|--------|----------|---------|------------|
| n (posts) | 13 | 13 | 12 |
| Adjusted score (organic) | 1.62 (0.51) | 1.38 (0.77) | 1.25 (0.75) |
| Final score | 2.31 (0.75) | 1.38 (0.77) | 0.58 (1.08) |
| Comment count | 8.15 (1.95) | 6.85 (3.31) | 8.08 (3.32) |

**Effect sizes (Cohen's f, one-way ANOVA):**
- adjusted_score: f = 0.229 (small-medium) — **primary outcome, 9% power in pilot**
- final_score: f = 0.834 (large, p < 0.001) — **manipulation check passed**
- comment_count: f = 0.216 (small-medium, p = 0.45)

**Pilot was underpowered by design.** Need 187+ posts per treatment group for 80% power.

---

## Power Requirements

From `power-analysis.md` (statsmodels exact computation):

| Scenario | Cohen's f | Power | N per group | Total N |
|----------|-----------|-------|-------------|---------|
| Observed | 0.229 | 80% | 187 | 561 |
| Observed | 0.229 | 90% | 245 | 735 |
| Conservative (80% of obs.) | 0.183 | 80% | 291 | 873 |

---

## Control Variables (held constant within each experiment)

| Variable | Value | Rationale |
|----------|-------|-----------|
| World posts per run | 90 (30 per group) | 3h at 2-min intervals |
| Post interval | 2 min | Gives agents time to discover + engage |
| World posts dataset | Same `world-posts.jsonl` every run | Eliminates content confound |
| Agent heartbeat | 10-15s | Consistent activity level |
| Rate limits | 50 posts/min, 1000 comments/hr | Prevents saturation |
| Nudge delays | [0, 0.5, 1, 5, 10, 30, 60] min (uniform random) | Same delay distribution |
| Run duration | 3 hours | Enough time for all nudges + agent engagement |
| Treatment split | Equal 1/3 each | Balanced design |
| LLM model | Kimi K2.5 (OpenRouter) | Same agent "brain" |

### Independent variables (manipulated between experiments)

| Variable | Levels | Purpose |
|----------|--------|---------|
| **Experiment mode** | A (world posts only), B (all posts) | Core research question |
| **Number of agents** | 5, 10, 20 | Population density effect |

---

## Experiment Battery

### Tier 1: Primary Experiments (fully powered)

These are the core experiments your advisor needs to see.

| ID | Mode | Agents | Posts/group/run | k runs | Total N/group | Power (f=0.229) | Duration |
|----|------|--------|----------------|--------|--------------|-----------------|----------|
| **E1-A** | A | 10 | 30 | 7 | 210 | **84.7%** | 7 × 3h = 21h |
| **E1-B** | B | 10 | ~45* | 5 | ~225 | **~88%** | 5 × 3h = 15h |

*Mode B treats all new posts (world + agent-created). With 10 agents, expect ~45-50 treated posts per group per run.

**Tier 1 total: 12 runs, ~36 hours**

### Tier 2: Agent Count Robustness (moderately powered)

Shows the effect holds regardless of population size.

| ID | Mode | Agents | Posts/group/run | k runs | Total N/group | Power (f=0.229) | Duration |
|----|------|--------|----------------|--------|--------------|-----------------|----------|
| **E2-A5** | A | 5 | 30 | 5 | 150 | 70.0% | 5 × 3h = 15h |
| **E2-A20** | A | 20 | 30 | 5 | 150 | 70.0% | 5 × 3h = 15h |
| **E2-B5** | B | 5 | ~35* | 5 | ~175 | ~77% | 5 × 3h = 15h |
| **E2-B20** | B | 20 | ~60* | 5 | ~300 | ~95% | 5 × 3h = 15h |

*Mode B post counts scale with agent count.

**Tier 2 total: 20 runs, ~60 hours**

### Tier 3: Pooled Analysis (no extra runs needed)

Pool all Mode A runs across agent counts for a combined ANOVA:
- E1-A (7 runs) + E2-A5 (5 runs) + E2-A20 (5 runs) = 17 runs
- Total N per group: 210 + 150 + 150 = **510 per group**
- Power at f=0.229: **>99%**
- Power at conservative f=0.183: **>95%**

This pooled analysis uses `agent_count` as a covariate/factor, giving you the main treatment effect *and* the treatment × population interaction — all from the same data.

---

## Summary: Run Counts

| Tier | Experiments | Runs | Compute Hours | What it proves |
|------|-------------|------|---------------|----------------|
| **Tier 1** | E1-A, E1-B | 12 | ~36h | Ranking effect exists in Mode A and B |
| **Tier 2** | E2-A5, E2-A20, E2-B5, E2-B20 | 20 | ~60h | Effect robust across population sizes |
| **Pooled** | (all Mode A combined) | 0 (reuses data) | 0 | >99% power main effect, interaction test |
| **TOTAL** | 6 experiments | **32 runs** | **~96h** | Full, publishable evidence |

### Minimum viable (advisor demo)

If time/budget is tight, run **Tier 1 only** (12 runs, 36h). This gives:
- 84.7% power for Mode A
- ~88% power for Mode B
- Clear yes/no answer on the ranking effect

### Recommended (publication-ready)

Tier 1 + Tier 2 (32 runs, 96h). The pooled analysis across agent counts gives >99% power and tests the agent_count interaction, which is itself a novel finding.

---

## Execution Order

Run in this order so you have publishable results as early as possible:

```
Week 1 (Tier 1 — core results):
  Day 1-2:  E1-A runs 1-4    (4 × 3h = 12h sequential, or 6h with 2 parallel)
  Day 2-3:  E1-A runs 5-7    (3 × 3h = 9h)
  Day 3-4:  E1-B runs 1-5    (5 × 3h = 15h)
  → Analyze. If signal holds, continue.

Week 2 (Tier 2 — robustness):
  Day 5-6:  E2-A5 runs 1-5   (15h)
  Day 6-7:  E2-A20 runs 1-5  (15h)
  Day 7-8:  E2-B5 runs 1-5   (15h)
  Day 8-9:  E2-B20 runs 1-5  (15h)
  → Pooled analysis. Write up.
```

---

## Analysis Plan (pre-register this)

### Primary analysis
- **Test:** Kruskal-Wallis (non-parametric ANOVA) on `adjusted_score` across 3 treatment groups
- **Alpha:** 0.05 (two-tailed)
- **Post-hoc:** Dunn's test with Bonferroni correction for pairwise comparisons
- **Effect size:** Report Cohen's f and partial eta-squared with 95% CIs
- **Clustering:** Mixed-effects model with `run_id` as random intercept to account for within-run dependence

### Secondary analyses
- Same tests on `comment_count` and `impression_count`
- Treatment × agent_count interaction (two-way ANOVA on pooled data)
- Mode A vs Mode B comparison (does nudging only world posts vs all posts change the effect?)
- Nudge delay analysis: does nudge timing moderate the effect?

### Manipulation check
- Confirm `final_score` differs significantly across groups (expected: large effect)
- If this fails, the experiment infrastructure has a bug

### Reporting
- CONSORT-style flow diagram adapted for agent experiments
- All effect sizes with 95% CIs
- Sensitivity analysis at conservative f (80% of observed)
- Raw data + analysis code published alongside paper

---

## Cost Estimate

| Resource | Per Run | 32 Runs |
|----------|---------|---------|
| Compute time | ~3.5h | ~112h |
| OpenRouter API (Kimi K2.5) | ~$2-5 | ~$64-160 |
| Docker resources | 1-2GB RAM | same |
| Storage (exports) | ~5MB | ~160MB |

**Total estimated cost: $65-160 in API credits + ~4 days of sequential compute**

---

## Implementation Checklist

- [ ] Expand `world-posts.jsonl` to 90 posts (currently 40, need 90 for 30/group)
- [ ] Add run counter / experiment batch ID to treatment records
- [ ] Create `run-experiment-batch.sh` script to automate sequential runs
- [ ] Add `run_id` column to `experiment_treatments` table
- [ ] Verify all 60-minute nudge delays actually fire (3h run > 60min max delay)
- [ ] Set up parallel export aggregation across runs
- [ ] Pre-register analysis plan before Tier 1 starts
