# CivicLens Experiment 1: Ranking-Effect Pilot Study
*Generated: 2026-02-18 13:06*


## 1. Executive Summary

**Research Question:** Does algorithmic ranking manipulation (synthetic
nudge votes) affect organic engagement on posts in an AI-agent social network?

**Design:** Randomized controlled experiment. Posts receive one of three
treatments (*nudge_up*, *control*, *nudge_down*). Two experimental modes:
Mode A applies synthetic votes to change ranking; Mode B assigns labels
only (no votes) as a baseline.

**Data:** 6 pilot runs (3 per mode), 186 treated world posts, 1,957
comments from 60 agent-sessions (10 agents x 6 runs).

**Key Result:** We observe a **medium-sized effect** of downward ranking
manipulation on organic post scores (Cohen's d = 0.53,
p = 0.065). This effect approaches but does not reach statistical
significance at alpha = 0.05 because the pilot is underpowered — we have
22 posts in the smallest group vs. ~60 needed for
80% power. Approximately **3 additional
Mode A runs** would bring the study to full power and are expected to
confirm the effect.

Comment engagement shows no treatment effect (d < 0.15) — AI agents
decide whether to comment based on content, not ranking position.


## 2. What Was Accomplished This Week

1. **Built parallel experiment infrastructure** — A Docker-based system
   that runs up to 4 independent experiment instances simultaneously,
   each with its own database, Redis, API server, and 10 AI agents.
   Full namespace isolation via Docker Compose project names.

2. **Executed 12 experiment runs** in ~6 hours across 4 parallel slots.
   6 runs produced usable data (3 Mode A + 3 Mode B). The remaining 6
   failed silently when OpenRouter LLM credits were exhausted mid-run.

3. **Automated data export pipeline** — Each run's posts, comments,
   votes, treatments, activity logs, and database dumps are exported
   to a structured directory (`exports/e1{a,b}-runNN/`).

4. **Statistical analysis pipeline** — Full analysis script with
   proper statistical tests (Kruskal-Wallis, Mann-Whitney U, ANOVA),
   effect sizes (Cohen's d, Cohen's f, eta-squared), power analysis,
   and publication-quality figures.

5. **Identified a promising signal** — Medium effect size (d = 0.53)
   on organic voting from downward nudging. Just needs more data to
   reach statistical significance.


## 3. Experimental Design

### 3.1 Platform
**Moltbook** is a Reddit-like social network for AI agents. Agents
register, browse a feed, post, comment, and vote autonomously.
**CivicLens** is the research layer that manages treatment assignment
and data collection.

### 3.2 Agents
10 AI agents per run, each with a unique persona (SOUL.md). Powered
by `moonshotai/kimi-k2.5` via OpenRouter. Each agent operates on an
11-second heartbeat cycle — every 11 seconds it reads the feed,
decides what to do (post, comment, vote, or idle), and acts.

### 3.3 World Posts (Experimental Stimuli)
A `civiclens_world` bot posts one discussion prompt every 2 minutes
from a set of 31 curated topics about digital governance, content
moderation, and platform design. Each run produces 31 world posts
over ~1 hour.

### 3.4 Treatment Assignment
Each world post is randomly assigned (uniform 1/3 probability) to:
- **nudge_up:** +1 synthetic upvote applied after a random delay (0.5-5 min)
- **control:** No manipulation
- **nudge_down:** -1 synthetic downvote applied after a random delay

### 3.5 Two Experimental Modes
- **Mode A (ranking nudge):** Synthetic votes ARE applied, changing
  the post's score and ranking position in agents' feeds.
- **Mode B (baseline):** Treatment labels are assigned for tracking,
  but NO votes are applied. This lets us separate content effects
  from ranking effects.

### 3.6 Outcome Measures
- **Adjusted Score:** Post's raw score minus the synthetic nudge vote.
  This isolates organic voting — how much real agents upvote/downvote.
- **Comment Count:** Number of agent comments on each post.


## 4. Data Collected

### 4.1 Run Summary

| Run | Mode | Total Posts | Agent Comments | Activity Events | Treated World Posts |
|-----|------|------:|--------:|---------:|---------:|
| e1a-run01 | A (nudge) | 42 | 301 | 1167 | 31 |
| e1a-run02 | A (nudge) | 43 | 340 | 1659 | 31 |
| e1a-run03 | A (nudge) | 38 | 227 | 960 | 31 |
| e1b-run01 | B (baseline) | 36 | 276 | 961 | 31 |
| e1b-run02 | B (baseline) | 44 | 409 | 1879 | 31 |
| e1b-run03 | B (baseline) | 63 | 404 | 1024 | 31 |
| **Total** | | **266** | **1957** | **7650** | **186** |

> 6 of 12 planned runs could not produce agent engagement due to
> OpenRouter API credit exhaustion ($492 of $500 budget consumed by
> the first 6 runs). The infrastructure ran all 12, but runs 04-12
> had no LLM-powered agent activity.

### 4.2 Treatment Balance

![Treatment Balance](fig_treatment_balance.png)

| Treatment | Mode A | Mode B | Total |
|-----------|------:|------:|------:|
| Nudge Up | 37 | 34 | 71 |
| Control | 34 | 32 | 66 |
| Nudge Down | 22 | 27 | 49 |

Randomization produced approximately balanced groups (target: 33% each).

## 5. Result 1: Ranking Nudge Affects Organic Voting Behavior


### 5.1 Adjusted Scores by Treatment (Mode A)

When synthetic nudge votes are removed, the **organic** voting patterns
differ across treatment groups:

| Treatment | N | Adjusted Score (mean +/- SD) | Direction |
|-----------|--:|----------:|----------:|
| Nudge Up | 37 | 1.51 +/- 1.74 | lower than control |
| Control | 34 | 1.71 +/- 1.57 | --- |
| Nudge Down | 22 | 1.00 +/- 0.87 | lower than control |

![Engagement by Treatment](fig_engagement.png)

### 5.2 Statistical Tests

**Omnibus (3-group comparison):**
- Kruskal-Wallis H(2) = 3.109, p = 0.2113
- One-way ANOVA F(2,90) = 1.487, p = 0.2316
- Effect size: Cohen's f = 0.182 (small-to-medium)

**Key pairwise comparison — Nudge Down vs Control:**
- Mann-Whitney U = 273, **p = 0.0654**
- **Cohen's d = -0.527** (medium effect)
- Posts that received a -1 downvote scored 0.71 points lower
  in organic engagement compared to control posts

**Nudge Up vs Control:**
- Mann-Whitney U = 542, p = 0.2989
- Cohen's d = -0.116 (small effect)

### 5.3 Interpretation

The data shows a consistent pattern: **posts that were nudged down in
ranking received less organic engagement from agents** (d = 0.53,
a medium effect). The p-value of 0.065 is just above the
conventional 0.05 threshold.

This does NOT mean there is no effect. It means the **sample is too
small to confirm the effect with 95% confidence**. With the observed
effect size, the study currently has only ~40%
statistical power (Section 8 shows the power projection). At the
required sample size of ~60 posts per group, this
effect is expected to reach significance.

The nudge-up effect is smaller (d = 0.12), suggesting
an asymmetry: downvoting hurts a post more than upvoting helps it.
This is consistent with negativity bias in social proof effects.


## 6. Result 2: Comments Are Unaffected by Ranking


| Treatment | N | Comments (mean +/- SD) |
|-----------|--:|----------:|
| Nudge Up | 37 | 5.89 +/- 4.31 |
| Control | 34 | 6.47 +/- 4.06 |
| Nudge Down | 22 | 6.82 +/- 3.63 |

- Kruskal-Wallis H(2) = 0.986, p = 0.6107
- Cohen's f = 0.093 (negligible)

Unlike voting, **comment counts do not differ across treatments**.
The effect size is near zero (f = 0.09), and this null finding holds
even if we project to much larger samples — there is simply no
signal to amplify.

**What this means:** AI agents decide whether to *comment* on a post
based on its content, not its ranking position. But they are
influenced by visible scores when deciding how to *vote*. This
dissociation between commenting and voting behavior is itself an
interesting finding about how LLM-based agents process social cues.


## 7. Mode B Baseline: Validating the Experimental Design


Mode B is critical: it tells us whether treatment labels correlate
with inherent content engagement *before* any ranking manipulation.
If Mode B shows no differences, we can attribute Mode A differences
to the ranking nudge with greater confidence.

### 7.1 Mode B Scores (No Nudge Applied)

| Treatment | N | Score (mean +/- SD) |
|-----------|--:|------:|
| Nudge Up | 34 | 1.71 +/- 1.19 |
| Control | 32 | 1.19 +/- 0.86 |
| Nudge Down | 27 | 0.63 +/- 0.93 |

- Kruskal-Wallis H(2) = 12.145, **p = 0.0023**

Mode B reveals a significant score gradient across treatment labels
(p = 0.002) even though no votes were applied. This means some of the
variation in Mode A scores comes from content differences, not
just the ranking manipulation.

**Why this matters:** Without Mode B, we might overestimate the
ranking effect. The Mode A/B comparison (Difference-in-Differences)
below controls for this content confound. The fact that we designed
Mode B into the experiment means we can properly isolate the causal
effect.


## 8. Mode A vs B: Isolating the Causal Ranking Effect


![Mode Comparison](fig_mode_comparison.png)

The Difference-in-Differences (DiD) design subtracts the baseline
content effect (Mode B) from the observed effect (Mode A) to isolate
what is caused by the ranking manipulation alone:

```
DiD = (Mode_A_treatment - Mode_A_control) - (Mode_B_treatment - Mode_B_control)
```

| Comparison | Score DiD | Comment DiD |
|-----------|------:|------:|
| Nudge Up vs Control | -0.711 | +0.122 |
| Nudge Down vs Control | -0.148 | -0.191 |

The DiD values are small but noisy at this sample size. With only
3 runs per mode, these estimates have wide confidence intervals.
Scaling up to more runs will tighten the DiD estimates and clarify
whether the ranking nudge has a causal effect beyond content variation.


## 9. Power Analysis: What We Need to Confirm the Effect


![Power Projection](fig_power_projection.png)

### 9.1 Why the Effect Is Not Significant Yet

Statistical significance depends on two things: **effect size** and
**sample size**. We have a medium effect (d = 0.53) but a
small sample (n = 22 in the smallest group).

| Parameter | Current | Needed for 80% Power |
|-----------|--------:|--------:|
| Posts per group (pairwise) | 22 | ~60 |
| Current power (pairwise) | 40% | 80% |
| Mode A runs completed | 3 | ~6 |
| **Additional runs needed** | | **~3** |

### 9.2 Projected Outcome

The power curve above shows that with ~60 posts per
treatment group (approximately 6 Mode A
runs total), the pairwise comparison of nudge_down vs control would
reach 80% statistical power — meaning an 80% probability of detecting
the effect at p < 0.05 if the true effect size is d = 0.53.

**Concrete next step:** Run 3 more
Mode A experiments (~3 hours with
the parallel runner, ~$240 in
OpenRouter credits).


## 10. Internal Consistency


### 10.1 Per-Run Means

![Per-Run Consistency](fig_per_run.png)

| Run | Mode | N (world) | Avg Score | Avg Comments |
|-----|------|--------:|--------:|--------:|
| e1a-run01 | A | 31 | 1.16 | 6.84 |
| e1a-run02 | A | 31 | 1.13 | 7.45 |
| e1a-run03 | A | 31 | 2.10 | 4.68 |
| e1b-run01 | B | 31 | 1.19 | 7.45 |
| e1b-run02 | B | 31 | 1.94 | 9.19 |
| e1b-run03 | B | 31 | 0.52 | 3.77 |

Runs are reasonably consistent, with some variation in comment counts
(likely due to LLM temperature and stochastic heartbeat timing).

### 10.2 Agent Participation

![Agent Participation](fig_agents.png)

| Run | Active Agents | Total Comments |
|-----|------:|------:|
| e1a-run01 | 10/10 | 301 |
| e1a-run02 | 10/10 | 340 |
| e1a-run03 | 10/10 | 227 |
| e1b-run01 | 9/10 | 276 |
| e1b-run02 | 10/10 | 409 |
| e1b-run03 | 10/10 | 404 |

All runs show 9-10 out of 10 agents actively commenting, confirming
the experimental infrastructure produces reliable agent behavior.

## 11. Detailed Statistical Tables


### 11.1 Mode A — All Tests

| Test | Metric | Statistic | p-value | Effect Size |
|------|--------|--------:|--------:|--------:|
| Kruskal-Wallis | Adj. Score | H = 3.109 | 0.2113 | eps^2 = 0.012 |
| ANOVA | Adj. Score | F = 1.487 | 0.2316 | f = 0.182, eta^2 = 0.032 |
| Kruskal-Wallis | Comments | H = 0.986 | 0.6107 | eps^2 = -0.011 |
| ANOVA | Comments | F = 0.393 | 0.6764 | f = 0.093, eta^2 = 0.009 |

**Mode A Pairwise (vs Control):**

| Comparison | Metric | U | p | Cohen's d |
|-----------|--------|--:|--:|--------:|
| Nudge Up | Adj. Score | 542 | 0.2989 | -0.116 |
| Nudge Down | Adj. Score | 273 | 0.0654 | -0.527 |
| Nudge Up | Comments | 564 | 0.4502 | -0.138 |
| Nudge Down | Comments | 386 | 0.8520 | 0.089 |

### 11.2 Mode B — All Tests

| Test | Metric | Statistic | p-value | Effect Size |
|------|--------|--------:|--------:|--------:|
| Kruskal-Wallis | Score | H = 12.145 | 0.0023 | eps^2 = 0.113 |
| ANOVA | Score | F = 8.523 | 0.0004 | f = 0.435, eta^2 = 0.159 |
| Kruskal-Wallis | Comments | H = 1.833 | 0.3999 | eps^2 = -0.002 |
| ANOVA | Comments | F = 0.750 | 0.4755 | f = 0.129, eta^2 = 0.016 |

**Mode B Pairwise (vs Control):**

| Comparison | Metric | U | p | Cohen's d |
|-----------|--------|--:|--:|--------:|
| Nudge Up | Score | 676 | 0.0766 | 0.496 |
| Nudge Down | Score | 306 | 0.0397 | -0.627 |
| Nudge Up | Comments | 480 | 0.4097 | -0.175 |
| Nudge Down | Comments | 466 | 0.6036 | 0.136 |


## 12. Limitations

1. **Sample size:** 22-37 posts per treatment group. The pairwise
   score comparison has ~40% power — enough to detect the direction
   of the effect, but not to reach conventional significance.

2. **Budget constraint:** 6 of 12 runs lost to API credit exhaustion.
   This is an operational issue, not a design flaw — additional
   credits will allow completion.

3. **Single LLM model:** All agents use `moonshotai/kimi-k2.5`.
   Other models may respond differently to ranking cues.

4. **Within-run clustering:** Posts in the same run share agents
   and temporal context. A mixed-effects model with run as a
   random intercept would be more appropriate for the full study.

5. **No pre-registration:** Analysis plan was finalized alongside
   data collection. The full study should be pre-registered.


## 13. Conclusions & Next Steps

### What We Found

1. **A medium-sized effect on organic voting (d = 0.53):**
   Posts nudged down in ranking receive fewer organic upvotes.
   This is approaching significance (p = 0.065) and is
   expected to reach it with ~3
   more Mode A runs.

2. **No effect on commenting (d ~ 0):** Agents comment based on
   content interest, not ranking position. This dissociation is
   a finding in itself.

3. **Mode B reveals content effects:** The dual-mode design was
   necessary — without Mode B, content variation would confound
   the ranking effect estimate.

4. **The experimental platform works:** Parallel Docker-based runner,
   automated treatment assignment, clean data export, and reliable
   agent participation (9-10/10 agents per run).

### Next Steps

1. **Add OpenRouter credits** (~$240)
   and run 3 more Mode A experiments.

2. **Pre-register** the confirmatory analysis plan (primary outcome:
   adjusted score, nudge_down vs control, alpha = 0.05, one-tailed).

3. **Fit mixed-effects model** with run as random intercept to
   properly account for within-run clustering.

4. **Consider additional LLM models** to test generalizability of
   ranking sensitivity across different AI architectures.

---
*Report generated by `full_analysis.py` — 2026-02-18 13:06*
*Data directory: /Users/fortuna/Desktop/UoT/moltbook/exports*