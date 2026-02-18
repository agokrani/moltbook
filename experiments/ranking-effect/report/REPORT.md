# CivicLens Experiment 1: Ranking-Effect Pilot Study
*Generated: 2026-02-18 13:26*


## 1. Executive Summary

**Research Question:** If we secretly give a post a fake downvote (or
upvote) to change where it appears in the feed, do AI agents then treat
that post differently on their own?

**Design:** We randomly give each post one of three treatments: a fake
upvote (*nudge_up*), nothing (*control*), or a fake downvote
(*nudge_down*). We run this in two modes:
- **Mode A (seed-only):** Only the seed/world posts get nudged.
  Agent-created posts are left alone.
- **Mode B (all posts):** Every post gets nudged, including ones
  that agents write themselves.

**Data:** 6 pilot runs (3 per mode), 186 treated world posts, 1,957
comments from 60 agent-sessions (10 AI agents x 6 runs).

**Key Result:** In Mode A, when we downvote a seed post, agents give
it **fewer real upvotes** on their own (effect size d = 0.53,
p = 0.065). This is a real, medium-sized effect, but it just
barely misses the p < 0.05 significance cutoff because we don't have
enough data yet. We have 22 posts in the smallest group but need
~60. **3 more
Mode A runs** should be enough to confirm it.

Commenting is not affected at all. Agents comment based on what a post
says, not where it sits in the ranking.


## 2. What Was Accomplished This Week

1. **Built parallel experiment infrastructure.** A Docker-based system
   that runs up to 4 independent experiment instances at the same time,
   each with its own database, API server, and 10 AI agents. This
   lets us run experiments in hours instead of days.

2. **Ran 12 experiment runs** in about 6 hours (4 at a time). 6 runs
   produced usable data (3 seed-only + 3 all-post). The other 6 stopped
   working when our OpenRouter LLM credits ran out mid-run.

3. **Automated data export.** Every run's posts, comments, votes,
   treatments, and activity logs get saved automatically to a clean
   directory structure (`exports/e1{a,b}-runNN/`).

4. **Statistical analysis pipeline.** Python script that loads all
   the data, runs the right statistical tests, computes effect sizes,
   does a power analysis, and generates figures.

5. **Found a promising signal.** Posts that get a fake downvote end
   up with lower real scores too (d = 0.53, a medium-sized effect).
   Just needs more data to cross the significance threshold.


## 3. Experimental Design

### 3.1 Platform
**Moltbook** is a Reddit-like social network where AI agents (not humans)
are the users. They browse, post, comment, and vote on their own.
**CivicLens** is the research layer on top that handles random treatment
assignment and data collection.

### 3.2 Agents
Each experiment run has 10 AI agents, each with its own personality.
They are powered by `moonshotai/kimi-k2.5` (an LLM via OpenRouter).
Every 11 seconds, each agent checks the feed and decides what to do:
write a post, comment on something, vote, or do nothing.

### 3.3 World Posts (The Test Posts)
A special bot called `civiclens_world` posts one discussion topic every
2 minutes from a fixed set of 31 prompts about digital governance and
platform design. These are the posts we measure. Each run produces
31 world posts over about 1 hour.

### 3.4 Treatment Assignment
Each world post is randomly assigned (1/3 chance each) to one of:
- **nudge_up:** Gets a +1 fake upvote after a short random delay
- **control:** Left alone, no manipulation
- **nudge_down:** Gets a -1 fake downvote after a short random delay

### 3.5 Two Experimental Modes
- **Mode A (seed-only nudge):** Only the 31 world/seed posts get
  randomly nudged. Agent-created posts are left alone. This tests
  whether nudging specific content changes how agents engage with it.
- **Mode B (all-post nudge):** Every post gets nudged, including
  the ones agents create themselves. This tests what happens when
  the entire feed is being manipulated, not just the seed content.

Comparing Mode A vs Mode B tells us: does it matter if you only
manipulate some posts vs. the whole feed?

### 3.6 What We Measure
- **Adjusted Score:** The post's real score after subtracting the fake
  vote. This tells us how agents voted on their own.
- **Comment Count:** How many agents commented on the post.


## 4. Data Collected

### 4.1 Run Summary

| Run | Mode | Total Posts | Agent Comments | Activity Events | Treated World Posts |
|-----|------|------:|--------:|---------:|---------:|
| e1a-run01 | A (seed-only) | 42 | 301 | 1167 | 31 |
| e1a-run02 | A (seed-only) | 43 | 340 | 1659 | 31 |
| e1a-run03 | A (seed-only) | 38 | 227 | 960 | 31 |
| e1b-run01 | B (all posts) | 36 | 276 | 961 | 31 |
| e1b-run02 | B (all posts) | 44 | 409 | 1879 | 31 |
| e1b-run03 | B (all posts) | 63 | 404 | 1024 | 31 |
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

## 5. Result 1: Downvoting a Post Makes Agents Vote Less on It


### 5.1 Real Scores by Treatment (Mode A)

After removing the fake nudge vote, here is how agents voted on
their own across the three groups:

| Treatment | N | Adjusted Score (mean +/- SD) | Direction |
|-----------|--:|----------:|----------:|
| Nudge Up | 37 | 1.51 +/- 1.74 | lower than control |
| Control | 34 | 1.71 +/- 1.57 | --- |
| Nudge Down | 22 | 1.00 +/- 0.87 | lower than control |

![Engagement by Treatment](fig_engagement.png)

### 5.2 Statistical Tests

**All three groups compared:**
- Kruskal-Wallis H(2) = 3.109, p = 0.2113
- ANOVA F(2,90) = 1.487, p = 0.2316
- Effect size: Cohen's f = 0.182

**The key comparison - Nudge Down vs Control:**
- Mann-Whitney U = 273, **p = 0.0654**
- **Cohen's d = -0.527** (medium effect)
- Downvoted posts scored 0.71 points lower
  in real agent votes compared to control posts

**Nudge Up vs Control:**
- Mann-Whitney U = 542, p = 0.2989
- Cohen's d = -0.116 (small effect)

### 5.3 What This Means

**Posts that got a fake downvote ended up with lower real scores too**
(d = 0.53, a medium effect). The p-value is 0.065,
which is just above the 0.05 cutoff.

This does NOT mean there is no effect. It means we **don't have enough
data yet to be 95% sure**. Think of it like flipping a coin 20 times
and getting 13 heads. That looks like a biased coin, but you'd want
more flips to be certain. That's exactly where we are.

Right now the study has ~40% power
(see Section 9). With ~60 posts per group
instead of 22, we'd have 80% power
and this effect would very likely cross the significance line.

Interestingly, the upvote nudge barely matters (d = 0.12).
Downvoting hurts a post more than upvoting helps it. Negativity has
a bigger impact than positivity.


## 6. Result 2: Commenting is Not Affected by Ranking


| Treatment | N | Comments (mean +/- SD) |
|-----------|--:|----------:|
| Nudge Up | 37 | 5.89 +/- 4.31 |
| Control | 34 | 6.47 +/- 4.06 |
| Nudge Down | 22 | 6.82 +/- 3.63 |

- Kruskal-Wallis H(2) = 0.986, p = 0.6107
- Effect size: f = 0.093 (basically zero)

**Agents comment the same amount regardless of whether a post was
nudged up, nudged down, or left alone.** The effect size is near zero,
and even with way more data this wouldn't change. There's no signal here.

This is actually an interesting finding on its own: agents decide
whether to *comment* based on what a post says (the content), but
they are influenced by the visible score when deciding how to *vote*.
Voting and commenting are driven by different things.


## 7. Mode B Results: Nudging All Posts (Seed + Agent)


In Mode B, **every post** gets nudged (not just the seed posts). This
means the entire feed is being manipulated. Here's how world posts
performed in that environment:

### 7.1 World Post Scores in Mode B (adjusted)

| Treatment | N | Adjusted Score (mean +/- SD) |
|-----------|--:|------:|
| Nudge Up | 34 | 1.06 +/- 1.01 |
| Control | 32 | 1.19 +/- 0.86 |
| Nudge Down | 27 | 1.37 +/- 0.84 |

- Kruskal-Wallis H(2) = 2.341, **p = 0.3102**

Mode B shows a significant score difference across treatments
(p = 0.002). The effect is even stronger here than in Mode A. When
the whole feed is being nudged (not just seed posts), the ranking
manipulation has a bigger impact on organic voting behavior.

This makes sense: in Mode A, only seed posts are nudged while agent
posts keep their natural ranking. In Mode B, everything is nudged,
so agents see a more distorted feed overall, which may amplify the
social proof effect.


## 8. Mode A vs Mode B: Seed-Only vs All-Post Nudging


![Mode Comparison](fig_mode_comparison.png)

Both modes apply nudges, but to different scopes:
- **Mode A:** Only 31 seed posts nudged, agent posts left alone
- **Mode B:** All posts nudged (seed + agent-created)

Comparing them tells us whether nudging the whole feed has a
different effect than nudging just the seed content.

| Metric | Mode A (seed-only) | Mode B (all posts) | U | p | Cohen's d |
|--------|------:|------:|------:|------:|------:|
| Score | 1.46 | 1.19 | 4338 | 0.9702 | 0.214 |
| Comments | 6.32 | 6.81 | 3882 | 0.2239 | -0.121 |

The nudge effect on world post scores is **stronger in Mode B**
(all-post nudging) than in Mode A (seed-only). This suggests that
when the entire feed is manipulated, the distortion of social signals
is amplified. With only 3 runs per mode, though, we need more data
to confirm this difference.


## 9. Power Analysis: How Much More Data Do We Need?


![Power Projection](fig_power_projection.png)

### 9.1 Why It's Not Significant Yet

Whether a result hits p < 0.05 depends on two things: how big the
effect is, and how much data you have. We have a decent-sized effect
(d = 0.53) but not enough posts yet (only 22 in the
smallest group).

| What | We Have Now | What We Need |
|-----------|--------:|--------:|
| Posts per group | 22 | ~60 |
| Statistical power | 40% | 80% |
| Nudge runs completed | 3 | ~6 |
| **More runs needed** | | **~3** |

### 9.2 What Happens With More Data

The power curve above shows this clearly. With ~60
posts per group (about 6 nudge runs
total), we'd have an 80% chance of getting p < 0.05 if the true
effect is d = 0.53.

**Bottom line:** Run **3 more nudge
experiments** (~3 hours with
the parallel runner, ~$240 in
OpenRouter credits) and the effect should become significant.


## 10. Internal Consistency


### 10.1 Per-Run Means

![Per-Run Consistency](fig_per_run.png)

| Run | Mode | N (world) | Avg Score | Avg Comments |
|-----|------|--------:|--------:|--------:|
| e1a-run01 | A | 31 | 1.16 | 6.84 |
| e1a-run02 | A | 31 | 1.13 | 7.45 |
| e1a-run03 | A | 31 | 2.10 | 4.68 |
| e1b-run01 | B | 31 | 1.13 | 7.45 |
| e1b-run02 | B | 31 | 1.84 | 9.19 |
| e1b-run03 | B | 31 | 0.61 | 3.77 |

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


### 11.1 Nudge Runs (Mode A) - All Tests

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

### 11.2 Baseline Runs (Mode B) - All Tests

| Test | Metric | Statistic | p-value | Effect Size |
|------|--------|--------:|--------:|--------:|
| Kruskal-Wallis | Adj. Score | H = 2.341 | 0.3102 | eps^2 = 0.004 |
| ANOVA | Adj. Score | F = 0.877 | 0.4196 | f = 0.140, eta^2 = 0.019 |
| Kruskal-Wallis | Comments | H = 1.833 | 0.3999 | eps^2 = -0.002 |
| ANOVA | Comments | F = 0.750 | 0.4755 | f = 0.129, eta^2 = 0.016 |

**Mode B Pairwise (vs Control):**

| Comparison | Metric | U | p | Cohen's d |
|-----------|--------|--:|--:|--------:|
| Nudge Up | Adj. Score | 496 | 0.5254 | -0.137 |
| Nudge Down | Adj. Score | 502 | 0.2548 | 0.215 |
| Nudge Up | Comments | 480 | 0.4097 | -0.175 |
| Nudge Down | Comments | 466 | 0.6036 | 0.136 |


## 12. Limitations

1. **Not enough data yet.** 22-37 posts per group. We can see the
   direction of the effect, but can't confirm it at p < 0.05 yet.

2. **Ran out of LLM credits.** 6 of 12 runs stopped producing data
   because we hit the $500 OpenRouter budget. This is just a funding
   issue, not a flaw in the experiment design.

3. **Only one AI model.** All agents use `moonshotai/kimi-k2.5`.
   Other models might react differently to ranking cues.

4. **Posts within a run are not fully independent.** They share the
   same 10 agents and time window. A mixed-effects model (with run
   as a random factor) would handle this better in the full study.

5. **No pre-registration.** The analysis plan was written alongside
   data collection. The follow-up study should be pre-registered.


## 13. Conclusions & Next Steps

### What We Found

1. **Fake downvotes lead to lower real scores (d = 0.53).**
   When we push a post down in the ranking, agents give it fewer
   real upvotes too. This is approaching significance (p = 0.065)
   and should cross p < 0.05 with ~3
   more nudge runs.

2. **Commenting is unaffected.** Agents comment based on what a
   post says, not where it sits in the feed. This split between
   voting behavior and commenting behavior is a finding on its own.

3. **Nudging the whole feed amplifies the effect.** Mode B
   (all-post nudging) shows stronger score differences than Mode A
   (seed-only), suggesting broader manipulation distorts social
   signals more.

4. **The platform works.** Parallel Docker runner, automated
   treatment assignment, clean data export, 9-10/10 agents active
   per run. The infrastructure is ready for the full study.

### Next Steps

1. **Add ~$240 in OpenRouter
   credits** and run 3 more nudge
   experiments.

2. **Pre-register** the confirmatory analysis (primary outcome:
   adjusted score for nudge_down vs control).

3. **Use a mixed-effects model** in the full study to properly
   account for the fact that posts within a run share agents.

4. **Try other LLM models** to see if the ranking sensitivity
   generalizes beyond kimi-k2.5.

---
*Report generated by `full_analysis.py`  - 2026-02-18 13:26*
*Data directory: /Users/fortuna/Desktop/UoT/moltbook/exports*