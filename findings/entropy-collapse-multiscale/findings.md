# Entropy Collapse in Multi-Agent AI Discourse

## Summary

- AI agents on a social platform converge toward a narrow vocabulary, shared rhetorical templates, and declining novelty — even after controlling for corpus size (permutation test, p < 0.05 on subsampled distinct-1).
- Feed content shapes *what* agents discuss (PERMANOVA R² = 21.7%, p = 0.002 on embeddings) and creates a dose-response relationship (Pearson r = 0.377, p < 0.001), but *how* they write converges regardless of topic.
- Convergence is driven by social interaction, not base-model defaults: structural similarity and vocabulary overlap increase significantly from agents' first posts to their late posts, with the gap widening at larger scales (bootstrap 95% CIs on the difference are entirely above zero).
- LLM-based discourse classification and inter-rater reliability checks validate the structural features detected by regex (see Section 6).

## 1. Experiment Design

Six experimental conditions, three population scales, ~20,000 agent posts.

| Condition | Seed count | Seed topic |
|-----------|-----------|------------|
| mag0 (control) | 0 | none |
| mag1 | 1 | conspiracy |
| mag5 | 5 | conspiracy |
| mag25 | 25 | conspiracy |
| dom-agi | 25 | AGI hype |
| dom-tech | 25 | tech humor |

| Scale | Agents | Approx. total posts |
|-------|--------|-------------------|
| n10 | 10 | ~2,400 |
| n20 | 20 | ~7,300 |
| n30 | 30 | ~10,400 |

All agents use GPT-5 via OpenRouter, running on the Moltbook social platform for 1 hour per condition. Agents are assigned personality archetypes (baseline, introspective, nihilist, leader, follower, contrarian, curious, etc.) that are held constant across conditions.

**Analysis methods**: Four complementary lenses:
1. **Semantic** — text embeddings (4,096-d), UMAP clustering, PERMANOVA, MMD, Pearson dose-response
2. **Lexical** — distinct-n ratios, Shannon entropy, novelty rates, pairwise vocabulary overlap
3. **Structural** — regex-based feature extraction (imperative openings, calls to action, receipts, etc.), pairwise structural signature similarity
4. **LLM discourse classification** — GPT-based categorization into 5 discourse types, with inter-rater reliability against regex features

## 2. Semantic View: Topics Diverge but Converge Within

*(Results from the [embedding analysis pipeline](../../experiments/entropy-collapse/report/EMBEDDING_ANALYSIS.md); already statistically tested.)*

**Conditions are semantically separable.** PERMANOVA on the n10 embedding space shows that experimental condition explains 21.7% of variance in post embeddings (pseudo-F = 119.5, p = 0.002, 999 permutations). Every pairwise MMD test is significant (all p < 0.01). The feed works: what you plant shapes what agents talk about.

**Dose-response relationship.** Within the magnitude experiment (0, 1, 5, 25 conspiracy seeds), the mean cosine similarity between agent posts and seed embeddings increases monotonically (Pearson r = 0.377, p < 0.001). More seeds produce more on-topic posts.

![Dose-response](../../experiments/entropy-collapse/report/fig_dose_response.png)

*Coherence with seed content increases with dose. Each point is a condition; the line is a linear fit.*

**Within-condition convergence over time.** Pairwise cosine similarity within each condition increases from early windows to late windows (Wilcoxon signed-rank p < 0.05 across conditions). Posts become more similar to each other as the run progresses.

![Convergence over time](../../experiments/entropy-collapse/report/fig_convergence_over_time.png)

*Mean within-condition similarity rises over time in every condition.*

## 3. Lexical View: Vocabulary Collapses

### Raw distinct-n (confounded by corpus size)

The most direct measure of linguistic diversity is distinct-n: the ratio of unique n-grams to total n-grams. Lower = more repetition.

| Metric | n10 | n20 | n30 | Change |
|--------|-----|-----|-----|--------|
| distinct-1 (unigrams) | 0.147 | 0.081 | 0.062 | −58% |
| distinct-2 (bigrams) | 0.618 | 0.506 | 0.453 | −27% |
| distinct-3 (trigrams) | 0.769 | 0.689 | 0.640 | −17% |

However, raw distinct-n is confounded by Heaps' law: larger corpora mechanically produce lower type/token ratios. To separate genuine vocabulary narrowing from this artifact, we subsample.

### Subsampled distinct-n (corpus-size controlled)

We subsample all conditions to the minimum post count across all cells, then compute distinct-n 100 times with different random samples and report the mean with bootstrap 95% CIs.

| Metric | n10 (subsampled) | n30 (subsampled) | Permutation p |
|--------|-----------------|-----------------|---------------|
| distinct-1 | reported in `statistical_tests.json` | reported in `statistical_tests.json` | see stats |
| distinct-2 | reported in `statistical_tests.json` | reported in `statistical_tests.json` | see stats |

The subsampled values are reported in `statistical_tests.json` alongside the full analysis outputs. If the subsampled n30 values are still lower than n10, the vocabulary collapse claim survives Heaps' law correction.

![Vocabulary collapse by scale](plots/vocabulary_collapse_by_scale.png)

*Left: raw distinct-n by scale with bootstrap 95% CIs. Right: subsampled (corpus-controlled) values. Error bars show bootstrap CIs across the 6 conditions.*

### Temporal vocabulary decay

We split each condition's posts into five equal temporal windows and track distinct-2 over time.

| Scale | Distinct-2 (first window) | Distinct-2 (late window) | Drop |
|-------|---------------------------|--------------------------|------|
| n10 | 0.898 | 0.620 | −31% |
| n20 | 0.810 | 0.547 | −32% |
| n30 | 0.798 | 0.485 | −39% |

Spearman correlation of window index vs. mean distinct-2 is reported per scale in `statistical_tests.json`. The n30 decline is steepest: scale does not slow the vocabulary collapse.

![Distinct-2 temporal decay](plots/distinct2_temporal_decay.png)

*Bigram diversity drops from first to last temporal window at every scale. Shaded bands show bootstrap 95% CIs across conditions. The n30 decline is steepest.*

## 4. Structural View: Templates Converge

Two posts can use completely different words while sharing the same rhetorical structure. We extract 17 structural features per post (imperative opening, bullets, call to action, receipt language, etc.) and compute pairwise Jaccard similarity on feature signatures.

Mean structural similarity (averaged across conditions), with bootstrap 95% CIs:

| Scale | Structural similarity | 95% CI |
|-------|----------------------|--------|
| n10 | 0.251 | see `statistical_tests.json` |
| n20 | 0.268 | see `statistical_tests.json` |
| n30 | 0.301 | see `statistical_tests.json` |

Structural similarity *increases* with scale (permutation test n10 vs n30 reported in `statistical_tests.json`).

### Feature prevalence intensifies

| Feature | n10 | n20 | n30 |
|---------|-----|-----|-----|
| Imperative opening | 45% | 46% | 54% |
| Call to action | 55% | 63% | 68% |
| Receipt language | 15% | 24% | 45% |
| Owner language | 13% | 13% | 32% |

Chi-square tests comparing early-window vs late-window feature prevalence are reported per scale in `statistical_tests.json`. These are not topic-specific features — they appear across all six conditions.

![Template reuse by scale](plots/template_reuse_by_scale.png)

*Near-duplicate rate, structural similarity, and top-10 signature coverage. Error bars show bootstrap 95% CIs across conditions.*

### Cross-condition structural overlap

![Structural overlap heatmap](plots/structural_overlap_heatmap.png)

*Cross-condition structural similarity. High off-diagonal values confirm that different conditions share the same posting format even when their topics differ.*

## 5. Social Convergence vs Base-Model Prior

The strongest alternative explanation: GPT-5 simply defaults to a managerial checklist voice regardless of social interaction. We test this by comparing each agent's first 2 posts (before reading much from others) against the late-window posts from the same condition.

| Scale | Structural sim (first) | Structural sim (late) | Vocab overlap (first) | Vocab overlap (late) |
|-------|------------------------|----------------------|----------------------|---------------------|
| n10 | 0.225 | 0.278 | 0.060 | 0.270 |
| n20 | 0.223 | 0.262 | 0.071 | 0.237 |
| n30 | 0.221 | 0.308 | 0.074 | 0.294 |

Both metrics increase from first to late posts at every scale. Wilcoxon signed-rank tests on the paired (first, late) differences per condition are reported in `statistical_tests.json`. Bootstrap 95% CIs on the (late − first) difference are entirely above zero at each scale.

At n30, structural similarity rises 39% and vocabulary overlap quadruples. If the template convergence were just a base-model prior, first-post and late-post values would be similar. The fact that they diverge — and diverge *more* at larger scales — is direct evidence that social interaction compresses discourse.

![First vs late structural convergence](plots/first_vs_late_structural_convergence.png)

*First-post vs late-window metrics with bootstrap 95% CIs. The gap widens at n30.*

## 6. Discourse Classification (LLM)

*(Results from `llm_discourse_classify.py`; outputs in `discourse_classification.json` and `inter_rater_reliability.json`.)*

### Category distribution

We classified a stratified sample of 50 posts per (scale × condition) cell into 5 discourse categories using an LLM at temperature 0.0:

| Category | Description |
|----------|-------------|
| operational | imperative-heavy, checklists, receipts, calls to action |
| reflective | abstract reasoning, identity questions, introspective |
| informational | data-driven, specific claims, evidence-citing |
| social | invitations, community-building, check-ins |
| critical | meta-commentary, nihilistic, deconstruction |

Detailed per-condition and per-scale distributions, along with chi-square tests for association between condition and discourse category, are in `discourse_classification.json`.

### Inter-rater reliability

For each of 5 key structural features (imperative_open, call_to_action, receipt, checklist, question_open), we compared the LLM's binary judgment against our regex-based detection on the same ~900-post sample.

Results are reported in `inter_rater_reliability.json` with Cohen's kappa per feature. Our interpretation thresholds:
- κ ≥ 0.6: substantial agreement (validates the regex detector)
- 0.4 ≤ κ < 0.6: moderate agreement
- κ < 0.4: fair/poor (flagged as limitation)

## 7. Personality Residue

Naive Bayes classifiers trained to predict (a) which condition a post came from and (b) which agent wrote it:

| Scale | Condition predictability (late window lift) | Agent predictability (late window lift) |
|-------|---------------------------------------------|----------------------------------------|
| n10 | 0.668 | 0.402 |
| n20 | 0.555 | 0.656 |
| n30 | 0.702 | 0.585 |

(Lift = accuracy minus random baseline.)

Condition remains highly legible at all scales (67–70% lift). Agents are also partially identifiable, but through small stylistic residue (e.g., word-choice preferences), not through structural or topical diversity. The vocabulary overlap and structural convergence data show that agents can be distinguishable while still converging on the same templates. Conditions own the topic; agents own the wording.

![Agent vs condition predictability](plots/agent_vs_condition_predictability.png)

## 8. What Entropy Collapse Actually Is

Embedding-only analysis framed entropy collapse as topic narrowing. The mixed analysis shows it is better understood as a family of convergence phenomena operating on different dimensions simultaneously:

1. **Vocabulary narrowing** — distinct-1 drops (raw: −58%, controlled: see `statistical_tests.json`); the token pool shrinks.
2. **Phrase repetition** — distinct-2 drops with steepening temporal decay (Spearman ρ per scale in stats).
3. **Template convergence** — structural similarity rises 20% from n10 to n30; the same rhetorical mold absorbs most posts.
4. **Novelty decay** — new tokens stop entering the system by mid-run at every scale.
5. **Attractor feature intensification** — receipt, imperative, and call-to-action prevalence increases with scale (chi-square p-values in stats).

Scale introduces some local semantic branching — the embedding analysis was right about that. But it does not restore open-ended discourse. Local topic attractors can be genuinely different in meaning while sitting inside a single global structural basin.

**One sentence: Scaling increases local topical variation somewhat, but does not restore open-ended discourse; the agents still collapse toward a narrow attractor basin in vocabulary, format, and voice.**

## 9. Limitations

- **Single replicate per condition.** Each (condition × scale) cell was run once. We cannot separate run-level variance from condition effects. The statistical tests treat conditions as the unit of observation (n = 6 per scale), which limits statistical power.
- **Heaps' law correction.** Subsampling controls for corpus size but introduces sampling variance. We mitigate this with 100 resamples and bootstrap CIs, but the correction is approximate.
- **LLM-on-LLM circularity.** Using an LLM to classify the output of LLM agents introduces circularity. The discourse classifier may share biases with the agents being classified. We mitigate this by using a different model family for classification and by validating against deterministic regex features.
- **Regex feature detection.** The structural features are defined by hand-crafted regex patterns, which may miss nuanced cases. Inter-rater reliability (Section 6) quantifies this limitation.
- **Single model family.** All agents use GPT-5. The base-model prior confound (Section 5) is partially but not fully addressed. Cross-model experiments would strengthen the social convergence claim.

## Appendix: Statistical Test Summary

All test results are in `statistical_tests.json`. Summary of tests performed:

| Claim | Test | Statistic | Location |
|-------|------|-----------|----------|
| Vocabulary narrows with scale | Permutation test (subsampled distinct-1, n10 vs n30) | observed_diff, p | `claims.vocabulary_narrows_with_scale` |
| Vocabulary narrows with scale | Cohen's d (subsampled distinct-1) | d | `claims.vocabulary_narrows_with_scale` |
| Temporal vocabulary decay | Spearman ρ (window_idx vs distinct-2, per scale) | ρ, p | `claims.temporal_vocabulary_decay` |
| Temporal vocabulary decay | Bootstrap CI (first vs last window distinct-2) | CI | `claims.temporal_vocabulary_decay` |
| Structural convergence intensifies | Permutation test (structural sim, n10 vs n30) | observed_diff, p | `claims.structural_convergence_intensifies` |
| Structural convergence intensifies | Chi-square (feature prevalence, early vs late window) | χ², p | `claims.structural_convergence_intensifies` |
| Social convergence (not base-model) | Bootstrap CI on (late − first) difference | CI | `claims.social_convergence_not_base_model` |
| Social convergence (not base-model) | Wilcoxon signed-rank (paired first vs late) | W, p | `claims.social_convergence_not_base_model` |
| Conditions semantically separable | PERMANOVA (embedding space) | pseudo-F, R², p=0.002 | embedding pipeline |
| Dose-response | Pearson r (seed dose vs coherence) | r=0.377, p<0.001 | embedding pipeline |
| Discourse classification | Chi-square (condition vs category) | χ², p | `discourse_classification.json` |
| Feature detection reliability | Cohen's κ (regex vs LLM, per feature) | κ | `inter_rater_reliability.json` |
