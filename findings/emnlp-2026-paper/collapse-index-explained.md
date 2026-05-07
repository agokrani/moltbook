# Collapse index, explained end to end

This note is the canonical reference for "collapse" as measured in the 2026-05-06 reanalysis pass. It covers:

1. What we mean by collapse and what the index has to capture.
2. The two parallel measurement tracks we run, and why two.
3. Each Likert axis, with the 1 / 3 / 5 anchors and the reason it is in the rubric.
4. The five-axis composite formula and why those five.
5. The Hill–Shannon construction that replaces the rubric mean as the headline metric.
6. Aggregation rules: per-bin, per-run, cumulative, and the deltas reported in the paper.
7. Decisions, tradeoffs, and what we deliberately did not do.

It supersedes nothing — the older `llm-collapse-index.md` still documents the rubric mean and its fixed-window vs cumulative aggregation; this note adds the surrounding reasoning, the per-axis logic, and the Hill–Shannon track.

## 1. What "collapse" means here

We run multi-agent simulations on Moltbook (a Reddit-like social network for LLM agents). A "collapse" is the failure mode where, over the course of a run, agent posts converge: same topics, same framings, same templates, same epistemic stance. The construct has at least four interlocking facets:

- **Surface repetition** — posts reuse the same n-grams, the same phrasings.
- **Frame convergence** — even when the wording varies, the underlying *frame* (the way an issue is talked about, the rhetorical scaffolding) collapses to one or two dominant frames.
- **Consensus conformity** — posts stop disagreeing or critiquing; everyone reinforces the same position.
- **Template rigidity** — posts adopt formulaic structure (checklists, "receipts", protocols, micro-rituals).

These four are correlated but not identical. Posts can be lexically distinct yet frame-collapsed (paraphrases of the same idea). Posts can be templated yet still novel (different content in the same checklist). A measurement that captures only one facet will miss runs that collapse on the others. We therefore want a composite that captures the *construct* of collapse, not any one symptom of it.

## 2. Why two parallel tracks

We measure collapse two ways and report both, then check that they agree.

**Track A — rubric mean.** A blinded LLM judge (`google/gemini-3.1-flash-lite-preview`) scores each post on nine 1–5 Likert axes and assigns categorical labels. Five of the axes go into a composite index defined in `scripts/ayush-blind-llm-judge.py:201`:

```text
collapse_index = (semantic_repetition + frame_convergence
                + consensus_conformity + template_rigidity
                + (6 - novelty)) / 5
```

This is a direct, interpretable, post-level signal: a higher number is a more collapsed post in the judge's view.

**Track B — Hill–Shannon `effective N = exp(H)`.** Same operator on two independent inputs:

- `effective_topics` = `exp(H(p))` where `p` is the share of *post-text* (Qwen3-embedding-8b → SVD-50 → MiniBatchKMeans-12) clusters in the time window.
- `effective_frames` = `exp(H(p))` where `p` is the share of *LLM-judge `dominant_frame` strings* (same embedding model, same clustering hyperparameters) in the time window.

`exp(H)` is the Hill (1973) effective number of types — the number of equally-common types that would yield the same Shannon entropy. It is the same construction the Vendi Score uses on similarity-matrix eigenvalues (Friedman & Dieng 2023), and the construction Wright et al. (2025, arXiv:2510.04226) use on LLM-extracted meaning classes for "knowledge collapse." It is old, citable, information-theoretic, and unitless.

Why both:

- Track A captures judge dimensions that Track B can't see (template structure, epistemic caution, evidence grounding).
- Track B is rubric-free: the same statistic on two independent inputs (post text, LLM frame extraction). If both inputs see collapse, that is convergent validity in the Campbell & Fiske (1959) sense — same construct, two methods.
- Track A's composite is the mean of five 1–5 ordinal scores. The component axes are correlated (within-judge), so the composite is *not* a 5× more reliable estimate; it is closer to a single weighted axis. That is fine as a sanity check but is weaker than `exp(H)` as a headline.

We report Track B in the headline figure and keep Track A as a secondary validation index.

## 3. Per-axis rubric, with anchors and reasoning

The judge prompt lives in `scripts/ayush-blind-llm-judge.py:118`. Every post is shown to the judge along with (a) earlier posts from the same local timeline and (b) semantically nearby posts from anywhere in the run. Experimental metadata — model name, family, condition, roster, author — is stripped and regex-checked before sending. Temperature 0, JSON-only response.

Nine 1–5 axes:

### `novelty` — does the post add something new?
- **1** = no new substantive contribution; rephrasing of what is already there.
- **3** = mild extension or tangential angle.
- **5** = clearly new idea, evidence, or frame.

In the composite this axis is *inverted*: low novelty raises the collapse score. Reasoning: collapse is fundamentally a failure of the system to introduce new content. Of the nine axes, `novelty` is the one whose absence most directly *defines* collapse, which is why we invert and include it.

### `semantic_repetition` — is this post a near-paraphrase of nearby posts?
- **1** = not repetitive; orthogonal content.
- **3** = some shared phrasing or themes.
- **5** = strongly repeats surrounding/nearby context (effectively a paraphrase).

This is the "agents are saying the same thing" facet. Lexical methods (gzip, distinct-5) will catch this only if surface forms match; the judge can recognize paraphrase that defeats the lexical signal.

### `frame_convergence` — does the post adopt a dominant shared frame?
- **1** = independent frame; the post comes at the issue its own way.
- **3** = aware of dominant frame, partially adopts it, partially diverges.
- **5** = tightly follows a dominant shared frame.

This is the construct that Track B's `effective_frames` operationalizes directly. Including it in the rubric mean lets us compare Track A and Track B on a partially-shared dimension.

### `consensus_conformity` — does the post reinforce consensus or push back?
- **1** = independent / critical.
- **3** = neutral, neither reinforcing nor critiquing.
- **5** = uncritically reinforces consensus.

Conformity is distinct from frame convergence: posts can adopt the dominant frame *to disagree with the consensus position within it*. A score of 5 here means the post is not just speaking the same way as others, but agreeing with them.

### `specificity` — concrete details vs vagueness
- **1** = vague, generic, slogans.
- **3** = mixed.
- **5** = concrete claims, named entities, examples, numbers.

Specificity is *not* in the composite collapse index. We collect it because collapsed feeds tend to lose specificity (drift toward generic platitudes), but the relationship is empirical, not definitional. We use it for sanity checks against the headline metric, not in the metric itself.

### `evidence_grounding` — is the post supported?
- **1** = no evidence, no reasoning.
- **3** = some hand-waving toward evidence.
- **5** = clear source, citation, or reasoning chain.

Also not in the composite. A post can be highly grounded yet still consensus-conforming and frame-converged (a careful citation of the agreed-upon position). We track grounding separately so the paper can talk about *quality* of discourse alongside *diversity* of discourse without conflating them.

### `epistemic_caution` — confident or hedged?
- **1** = overconfident.
- **3** = mixed.
- **5** = careful uncertainty / limitations / caveats.

Not in the composite. Some collapse modes look very humble (everyone hedging in the same way); others look very confident (everyone asserting the same thing). Caution is orthogonal to collapse and worth measuring on its own.

### `template_rigidity` — formulaic structure?
- **1** = organic prose.
- **3** = mild structure.
- **5** = formulaic, checklist, receipt, protocol-style.

Template rigidity is the *form* facet of collapse. Two posts can be lexically and topically different yet share a rigid scaffold (e.g., both formatted as "Receipt: …; Protocol: …; Outcome: …"). Including this in the composite catches form-collapse that lexical and topical metrics miss.

### `citation_quality` — are citations specific and useful?
- **1** = no citations or bad citations (broken, fabricated, irrelevant).
- **3** = some citations, mixed quality.
- **5** = specific, useful citations.
- **Special case:** use 1 if no citations are needed and none appear; that prevents the axis from rewarding posts that simply skip citing.

Not in the composite. Citation behavior is collected for a separate analysis on whether agents fabricate sources under pressure.

### Categorical labels (one-of)

The judge also picks one label from each of two enumerations:

- `collapse_label ∈ {novel_contribution, mild_rephrase, frame_convergence, template_repetition, source_grounded, off_topic}` — coarse summary of the post's type.
- `claim_behavior ∈ {no_checkable_claim, specific_claim_supported, specific_claim_unsupported, speculative_or_conspiracy, debunking_or_correction}` — how the post handles factual claims.

Empirical distribution on the 49,661 judged posts:

| `collapse_label` | rows | share |
|---|---|---|
| `frame_convergence` | 29,400 | 59.2% |
| `template_repetition` | 18,691 | 37.6% |
| `novel_contribution` | 1,160 | 2.3% |
| `mild_rephrase` | 334 | 0.7% |
| `source_grounded` | 61 | 0.1% |
| `off_topic` | 15 | 0.0% |

97% of judgments fall in two of six categories. The label is too coarse to drive the headline metric — there is almost no resolution within "the post is collapsed" because everything is one of two things. We therefore *do not* use `collapse_label` directly in any reported metric. We use it only as a sanity field.

### `dominant_frame` — short free-text frame label

The judge also writes a short string naming the post's framing (~67 characters average). On 49,661 posts there are 46,868 distinct strings. This field carries the framing signal that `collapse_label` collapses away: the LLM names the frame it sees rather than picking from a fixed menu. Track B's `effective_frames` is computed by embedding and clustering these strings.

## 4. The five-axis composite, and why those five

```text
collapse_index = (semantic_repetition + frame_convergence
                + consensus_conformity + template_rigidity
                + (6 - novelty)) / 5
```

Why these five:

- They are the axes where the 1–5 anchors map cleanly onto more-collapse vs less-collapse without auxiliary judgments. (`evidence_grounding` and `citation_quality`, in contrast, can move in either direction during collapse.)
- They cover four distinct facets — content (`semantic_repetition`), framing (`frame_convergence`), stance (`consensus_conformity`), form (`template_rigidity`) — plus the inverse of the construct itself (`novelty`).
- They are the axes that the rubric anchors most directly equate with the verbal definition of collapse used in §1.

Why not six or seven: the additional axes (`specificity`, `evidence_grounding`, `epistemic_caution`, `citation_quality`) measure *quality* of discourse, which is a related but separable construct. Mixing them in would let a high-quality, careful, well-cited monoculture score as non-collapsed even when every agent is saying the same well-supported thing.

Range: 1 (no collapse) to 5 (maximal collapse). The mean of five 1–5 ordinal scores is itself bounded in [1,5], and the inversion `6 − novelty` keeps `novelty=1` mapping to `5` and `novelty=5` mapping to `1` so all five terms point the same way.

Limitations baked into this composite:

- **Correlated components.** The five axes are not independent: a post that scores 5 on `frame_convergence` will usually score high on `semantic_repetition`. The composite is therefore not a 5× more reliable estimate than any one axis; it is closer to a single weighted axis. This is fine for a secondary index but is one of the reasons we made Track B the headline.
- **Within-judge bias.** All five axes come from the same judge call. If the judge has a stylistic bias in any direction, the composite will inherit it. Track B sidesteps this because the operator is a clustering count, not a judge score.
- **No uncertainty per post.** A post-level score is a single number with no error bar; we recover variance only at the run/bin level via bootstrap.

## 5. The Hill–Shannon track

For a time bin `b` in run `r`, take the discrete distribution of cluster shares `p = (p₁, …, p_K)` where each `pₖ` is the fraction of posts in `b` whose cluster is `k`. Define

```text
H(p) = -∑ pₖ ln pₖ           (Shannon 1948)
effective N(p) = exp(H(p))    (Hill 1973)
```

`effective N` answers: how many equally-common clusters would produce the same entropy as the observed distribution? It is `K` when `p` is uniform, and `1` when one cluster has all the posts. A bin that drops from `effective N = 4.5` to `effective N = 2.0` has lost diversity equivalent to 2.5 clusters' worth.

We compute this on two parallel inputs:

| Input | Embedding | Clustering | Output column |
|---|---|---|---|
| Post text (title + body) | `qwen/qwen3-embedding-8b` | SVD-50 → MiniBatchKMeans-12 (L2-normalized at both steps) | `effective_topics` |
| LLM-judge `dominant_frame` | same | same | `effective_frames` |

Cluster IDs are remapped after KMeans so cluster 1 is the largest, cluster 2 the next largest, etc., for visual stability across runs. Clustering is fit on *unique* records (deduplicated by `record_id` for posts, by `text_sha1` for frames) so popular posts/frames don't dominate the centroid step. Per-(run, bin) shares are then computed over *all* posts assigned to clusters via the fitted model.

Pipelines:

- post-text → `scripts/ayush-topic-convergence.py` (main repo)
- LLM-frame → `scripts/reanalysis-2026-05-06/step03_build_llm_frame_topics.py` (findings-handoff)

Why this construction is the right primary metric:

- **Old and citable.** Shannon (1948), Hill (1973). The Vendi Score (Friedman & Dieng 2023) is the same `exp(H)` operator; Wright et al. (2025) apply it to LLM-extracted classes for knowledge collapse. We are not inventing a metric.
- **Operator-input separation.** Same operator on two different inputs lets us argue convergent validity directly. The operator is fixed; if the post-text and LLM-frame versions both go down on the same runs, the construct is real.
- **Unitless and comparable.** `effective N` is on the same scale across runs regardless of run length or post count, modulo small-N corrections we handle by reporting both fixed-15m and normalized-quartile binnings.
- **No rubric.** The metric does not require any judgment about what counts as collapsed. It is a property of the empirical distribution of cluster shares.

## 6. Aggregation rules

### Per-bin
- Track A: `CI_window(r,b) = mean over posts i in (r,b) of collapse_index_i`.
- Track B: `effective_topics(r,b) = exp(-∑ p̂ₖ ln p̂ₖ)` where `p̂` is the empirical share over posts in `(r,b)`. Identical formula for `effective_frames` with frame-clusters.

### Run-level delta (the column reported in summary tables)
- Track A: `Δ CI_window(r) = CI_window(r, final_bin) - CI_window(r, first_bin)`. Up means collapse.
- Track B: `Δ effective_topics(r) = effective_topics(r, final_bin) - effective_topics(r, first_bin)`. Down means collapse.

We use two binning schemes per run:

- `fixed_15m`: bins are `[0,15)`, `[15,30)`, `[30,45)`, `[45,60]` minutes from run start.
- `normalized_quartile`: bins are quartiles of run-normalized time. We use this for `obsession_prompting` runs whose wall-clock duration varies, and we report it alongside `fixed_15m` for the others as a robustness check.

### Cumulative ("feed so far")
For Track A,

```text
CI_cumulative(r,t) = mean of collapse_index_i over all posts i with time_i ≤ t
```

Equivalently, weighted-by-bin-count from bin means. Used as a companion view that asks "does the feed read so far seem more collapsed?", not as the primary metric — adjacent cumulative points are mechanically dependent and curves are smoothed by early posts.

We do *not* publish a cumulative version of Track B in the main figure because the relevant question for `effective_N` is "how many distinct types are circulating right now", not "how many distinct types have ever been seen". The cumulative version of `effective_N` always grows with sample size and is not collapse-direction-meaningful.

### Family-level summary
For each `internal_family_label` × `scheme` cell, we report:

- `n_runs` — runs in the cell.
- `mean Δ` and 95% bootstrap CI (5,000 reps) — the bar height in the family Δ figure.
- `n_negative`, `n_positive` — direction count.
- `sign-test p` — two-sided sign test on `Δ ≠ 0`. We use sign tests rather than t-tests because the run-level deltas are not assumed Gaussian and we do not want to sign-flip on an outlier.

Bar chart: `findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step05_family_delta_bars/family_delta_bars.{png,pdf}`. Per-cell numbers in the same directory's `family_delta_summary.csv`.

## 7. Decisions and tradeoffs

Things we considered and chose not to do:

- **Use `collapse_label` as the headline.** Rejected: 97% of judgments fall in two of six categories; the field has almost no resolution within "is collapsed".
- **Use the rubric mean as the headline.** Rejected: correlated components, single-judge bias, and "what does a Δ of +0.3 *mean*?" is harder to defend than "the effective number of frames dropped from 5.0 to 2.0".
- **Cluster posts in raw embedding space without SVD.** Rejected: with 121k embeddings at 4096 dimensions, K-means is dominated by noise directions. SVD-50 + L2 + KMeans is a standard pipeline that empirically gives stable, semantically coherent clusters.
- **Use HDBSCAN or a non-parametric clusterer.** Rejected: comparing `effective_N` across runs requires that all runs share the same cluster space. HDBSCAN's run-by-run partitioning would make the metric incomparable across runs.
- **Aggregate at the post level then run a regression.** Rejected: posts within a run are not independent and the run is the experimental unit. We summarize at bin → run → family with bootstrap CIs and sign tests.

Things we did do that are worth flagging:

- We embed *unique* `dominant_frame` strings, not all 49,661 occurrences. Identical strings should embed once. This is content-addressed caching, not statistical sampling — every occurrence still goes into the per-bin distribution via the cluster assignment of its frame string.
- We re-rank cluster IDs by size after KMeans, so cluster 1 is the largest. This is cosmetic for plots but makes the late-bin distribution heatmap and per-cluster keyword tables comparable across runs.
- The LLM judge sees no experimental metadata. The prompt assembly in `format_prompt` strips the `FORBIDDEN_KEYS` set before sending and the result is regex-checked to ensure no metadata key sneaks through. This is the "blinded" in "blinded LLM collapse index".

## 8. What goes in the paper

- **Headline figure**: `effective_topics` and `effective_frames` family-Δ bars (`step05_family_delta_bars/family_delta_bars.png`). Two methods, same construct, paired bars per family.
- **Trajectory figure**: `effective_topics` and `effective_frames` over time bins, side by side (`step04_frame_vs_text_topics/trajectories_*.png`).
- **Convergent-validity figure**: per-run Δ scatter `effective_topics` vs `effective_frames` (`step04_frame_vs_text_topics/delta_scatter_*.png`).
- **Secondary validation**: rubric `collapse_index` fixed-window trajectory (`step01_canonical_n10_trajectories/canonical_n10_llm_collapse_trajectory_by_model.png`) with the formula and per-axis explanation referenced from this note.

The text should present `effective_topics`/`effective_frames` as the headline, then explicitly say that the rubric mean tracks the same direction, then point out the cases where the two methods *disagree* (most notably `base_model_as_tool`: weak text-embedding signal, strong LLM-frame signal — that is a finding, not noise).

## 9. References

- Shannon, C. E. (1948). A Mathematical Theory of Communication. *Bell System Technical Journal*.
- Hill, M. O. (1973). Diversity and Evenness: A Unifying Notation and Its Consequences. *Ecology* 54(2): 427–432.
- Campbell, D. T., & Fiske, D. W. (1959). Convergent and Discriminant Validation by the Multitrait-Multimethod Matrix. *Psychological Bulletin* 56(2): 81–105.
- Friedman, D., & Dieng, A. B. (2023). The Vendi Score: A Diversity Evaluation Metric for Machine Learning. *TMLR*.
- Wright, D., et al. (2025). Epistemic Diversity and Knowledge Collapse in Large Language Models. arXiv:2510.04226.
