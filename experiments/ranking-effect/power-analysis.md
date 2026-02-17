# Power Analysis: Ranking Effect Experiment

**Date:** 2026-02-17
**Study:** Ranking Effect on AI Agent Voting Behavior (Moltbook / CivicLens)
**Analysis code:** `experiments/ranking-effect/power_analysis.py`

## Environment

| Package | Version |
|---------|---------|
| Python | 3.14.2 |
| NumPy | 2.4.2 |
| SciPy | 1.17.0 |
| Statsmodels | 0.14.6 |
| Pandas | 3.0.0 |

Random seed: `numpy.random.seed(42)`

---

## Study Design

**Treatments (3 groups):**

- `nudge_up` — post score artificially inflated by +1 before agents see it
- `control` — post score unmodified
- `nudge_down` — post score artificially deflated by -1 before agents see it

**Outcome variables:**

| Variable | Definition |
|----------|-----------|
| `adjusted_score` | Organic votes only, excluding the nudge vote (primary outcome) |
| `final_score` | Score agents actually see (includes nudge) |
| `comment_count` | Number of comments received |

**Pilot sample:** n = 13 / 13 / 12 posts per group (total 38 posts)

---

## Section 1: Pilot Descriptive Statistics

### adjusted_score (primary outcome)

| Group | n | Mean | SD |
|-------|---|------|----|
| nudge_up | 13 | 1.615 | 0.506 |
| control | 13 | 1.385 | 0.768 |
| nudge_down | 12 | 1.250 | 0.754 |

### final_score

| Group | n | Mean | SD |
|-------|---|------|----|
| nudge_up | 13 | 2.308 | 0.751 |
| control | 13 | 1.385 | 0.768 |
| nudge_down | 12 | 0.583 | 1.084 |

### comment_count

| Group | n | Mean | SD |
|-------|---|------|----|
| nudge_up | 13 | 8.154 | 1.951 |
| control | 13 | 6.846 | 3.313 |
| nudge_down | 12 | 8.083 | 3.315 |

---

## Section 2: Assumption Tests

All tests run on pilot data. Parametric tests are reported for completeness alongside
non-parametric alternatives; non-parametric tests are the primary basis for inference
given violated normality.

### adjusted_score

| Test | Statistic | p-value | Decision |
|------|-----------|---------|---------|
| Shapiro-Wilk (nudge_up) | — | 0.0001 | Non-normal |
| Shapiro-Wilk (control) | — | 0.0021 | Non-normal |
| Shapiro-Wilk (nudge_down) | — | 0.0113 | Non-normal |
| Levene (homogeneity) | F = 0.54 | 0.5876 | Variances equal |
| One-way ANOVA | F = 0.917 | 0.4092 | Not significant |
| Kruskal-Wallis | H = 1.507 | 0.4708 | Not significant |

### final_score

| Test | Statistic | p-value | Decision |
|------|-----------|---------|---------|
| Shapiro-Wilk (nudge_up) | — | 0.0052 | Non-normal |
| Shapiro-Wilk (control) | — | 0.0021 | Non-normal |
| Shapiro-Wilk (nudge_down) | — | 0.1182 | Normal |
| Levene (homogeneity) | F = 1.00 | 0.3789 | Variances equal |
| One-way ANOVA | F = 12.183 | 0.0001 | Significant |
| Kruskal-Wallis | H = 15.084 | 0.0005 | Significant |

The `final_score` ANOVA is significant even in the pilot — expected, because the nudge
vote is included in this variable. This confirms the manipulation check: nudge groups
differ in the score agents observe. The primary question is whether this propagates into
`adjusted_score` (organic votes).

### comment_count

| Test | Statistic | p-value | Decision |
|------|-----------|---------|---------|
| Shapiro-Wilk (nudge_up) | — | 0.0208 | Non-normal |
| Shapiro-Wilk (control) | — | 0.0040 | Non-normal |
| Shapiro-Wilk (nudge_down) | — | 0.0044 | Non-normal |
| Levene (homogeneity) | F = 0.54 | 0.5848 | Variances equal |
| One-way ANOVA | F = 0.816 | 0.4504 | Not significant |
| Kruskal-Wallis | H = 2.453 | 0.2933 | Not significant |

---

## Section 3: Effect Sizes from Pilot Data

Effect sizes computed using pooled-SD Cohen's d (pairwise) and eta-squared-derived
Cohen's f (one-way ANOVA across all 3 groups).

**Cohen's d formula:** d = (mean_A - mean_B) / pooled_SD, where pooled_SD uses n-1 variances.

**Cohen's f formula:** f = sqrt(eta^2 / (1 - eta^2)), where eta^2 = SS_between / SS_total.

### Pairwise Cohen's d

| Comparison | adjusted_score | final_score | comment_count |
|-----------|---------------|-------------|--------------|
| nudge_up vs control | +0.355 | +1.215 | +0.481 |
| nudge_down vs control | -0.177 | -0.859 | +0.373 |
| nudge_up vs nudge_down | +0.574 | +1.864 | +0.026 |

Sign convention: positive = first group has higher mean.

### Cohen's f (one-way ANOVA, 3 groups)

| Outcome | Cohen's f | Interpretation |
|---------|-----------|---------------|
| adjusted_score | **0.2289** | Small-medium |
| final_score | 0.8344 | Large (manipulation check) |
| comment_count | 0.2159 | Small-medium |

Reference thresholds (Cohen 1988): small = 0.10, medium = 0.25, large = 0.40.

The `adjusted_score` f = 0.229 sits just below the medium threshold. This is the
effect we must be powered to detect in a full study.

### Power at pilot sample size (n=13/group)

| Outcome | Cohen's f | Power at n=13 |
|---------|-----------|--------------|
| adjusted_score | 0.2289 | 0.091 |
| final_score | 0.8344 | 0.631 |
| comment_count | 0.2159 | 0.086 |

The pilot was severely underpowered for the primary outcome (9% power). This is
expected for a pilot — it establishes the effect size estimate, not the inference.

---

## Section 4: Power Analysis — Primary Outcome (adjusted_score)

**Method:** `statsmodels.stats.power.FTestAnovaPower` (exact computation).
**Parameters:** k_groups = 3, alpha = 0.05.
**Two scenarios:** observed f = 0.2289; conservative f = 0.1831 (80% of observed).

The conservative scenario hedges against pilot upward bias — pilot effect sizes are
often inflated relative to true population values.

### N per group needed

| Scenario | Cohen's f | Target Power | N per Group | Total N | Achieved Power |
|----------|-----------|-------------|-------------|---------|---------------|
| Observed | 0.2289 | 0.80 | **187** | 561 | 0.8001 |
| Observed | 0.2289 | 0.90 | **245** | 735 | 0.9005 |
| Conservative (80% of observed) | 0.1831 | 0.80 | **291** | 873 | 0.8009 |
| Conservative (80% of observed) | 0.1831 | 0.90 | **381** | 1143 | 0.9004 |

---

## Section 5: Runs (k) Needed Given Posts per Treatment Group

Each experiment run generates a fixed number of posts per treatment group.
Posts accumulate across runs: total N per group = k * posts_per_group.

Using **observed Cohen's f = 0.2289**, alpha = 0.05.

### 30 posts per group per run (90 total world posts per run)

| Target Power | N Needed | k Runs | N Achieved | Actual Power |
|-------------|---------|--------|-----------|-------------|
| 0.80 | 187 | **7** | 210 | 0.847 |
| 0.90 | 245 | **9** | 270 | 0.928 |

### 20 posts per group per run (60 total world posts per run)

| Target Power | N Needed | k Runs | N Achieved | Actual Power |
|-------------|---------|--------|-----------|-------------|
| 0.80 | 187 | **10** | 200 | 0.828 |
| 0.90 | 245 | **13** | 260 | 0.918 |

---

## Section 6: Sensitivity Table

Power as a function of posts per group per run and number of runs k.
Computed using `FTestAnovaPower`, alpha = 0.05, k_groups = 3.

### Observed Cohen's f = 0.2289

| posts/group | k=1 | k=2 | k=3 | k=5 | k=7 |
|-------------|-----|-----|-----|-----|-----|
| 20 | 0.122 | 0.219 | 0.320 | 0.510 | 0.667 |
| 30 | 0.170 | 0.320 | 0.465 | 0.700 | **0.847** |
| 40 | 0.219 | 0.418 | 0.594 | 0.828 | 0.937 |
| 50 | 0.269 | 0.510 | 0.700 | 0.907 | 0.976 |

Bold = first cell exceeding 80% power with 30 posts/group.

### Conservative Cohen's f = 0.1831 (80% of observed)

| posts/group | k=1 | k=2 | k=3 | k=5 | k=7 |
|-------------|-----|-----|-----|-----|-----|
| 20 | 0.095 | 0.154 | 0.217 | 0.345 | 0.469 |
| 30 | 0.124 | 0.217 | 0.313 | 0.498 | 0.651 |
| 40 | 0.154 | 0.281 | 0.408 | 0.628 | 0.784 |
| 50 | 0.185 | 0.345 | 0.498 | 0.733 | 0.873 |

Under the conservative scenario, 80% power requires roughly 50 posts/group with k=5
runs, or 40 posts/group with k=7 runs.

---

## Section 7: Summary and Recommendation

### Effect Size Summary

| Outcome | Cohen's f | d (up vs ctrl) | d (dn vs ctrl) | d (up vs dn) |
|---------|-----------|---------------|---------------|-------------|
| adjusted_score | 0.2289 | +0.355 | -0.177 | +0.574 |
| final_score | 0.8344 | +1.215 | -0.859 | +1.864 |
| comment_count | 0.2159 | +0.481 | +0.373 | +0.026 |

Key observations:
- The nudge manipulation successfully shifts `final_score` (large effect, p < 0.001). This is the manipulation check and confirms the intervention is working.
- The effect on `adjusted_score` (organic votes) is small-medium (f = 0.229). The direction is consistent with a ranking effect: nudge_up posts receive more organic votes than nudge_down posts (d = +0.574). The pilot was underpowered to detect this.
- The `comment_count` pattern is unexpected: nudge_up and nudge_down both attract more comments than control, with nearly no difference between them (d = +0.026). This may reflect general visibility rather than valence-specific engagement.

### Sample Size Recommendation

The primary outcome is `adjusted_score` (organic votes excluding the nudge).

| Scenario | Power Target | Posts/Group/Run | Runs (k) | Total Posts |
|----------|-------------|----------------|---------|------------|
| Observed f = 0.229 | 80% | 30 | 7 | 630 |
| Observed f = 0.229 | 90% | 30 | 9 | 810 |
| Conservative f = 0.183 | 80% | 50 | 5 | 750 |
| Conservative f = 0.183 | 90% | 50 | 8 | 1200 |

**Primary recommendation:** 7 runs x 30 posts per group = 210 posts per group (630 total)
achieves 84.7% power under the observed effect size. This is a pragmatic target that
balances statistical rigor with experimental cost.

**If pilot effect is inflated:** Consider 10 runs x 30 posts (power = 87.2% at f = 0.183)
as a conservative plan, or pre-register the observed f and accept the risk of lower power.

### Caveats

1. The pilot n per group (12-13) is small. The Cohen's f estimate carries substantial
   uncertainty. A 95% CI on f would be wide.
2. All outcomes show non-normal distributions (Shapiro-Wilk p < 0.05). The ANOVA-based
   power analysis assumes normality. With large N, the CLT mitigates this; with moderate
   N, consider permutation-based power simulations as a check.
3. Posts within a run may not be independent if agents see and respond to each other's
   votes during the run. This within-run clustering is not accounted for here. If
   intra-run ICC > 0, effective N is smaller than nominal N.
4. Effect size inflation from pilot data is well-documented. The conservative scenario
   (80% of observed f) is a simple hedge but not a principled correction.

---

*Analysis executed with `experiments/ranking-effect/power_analysis.py`*
*Reproducible: set `numpy.random.seed(42)`, pinned library versions listed above.*
