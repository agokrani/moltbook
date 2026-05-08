# Reanalysis plot plan, 2026-05-06

<<<<<<< Updated upstream
Status: Step 0–2 outputs exist and were verified on 2026-05-07. Do not generate later-step plots until the exact step is approved.
=======
Status: active stepwise plan. Do not generate a new plot step until the exact step is approved.
>>>>>>> Stashed changes

This replaces the 2026-05-05 plotting pass. The 2026-05-05 figures are draft outputs unless a specific file is later rescued.

## Where are we now?

| Step | Status | Notes |
|---|---|---|
| Step 0. Inventory | Done | Confirmed clean bundle and canonical run availability. |
| Step 1. Canonical 10-agent fixed-window trajectories | Generated | Three metrics only: gzip, Distinct-5, LLM collapse index. Vendi skipped. |
| Step 2. Canonical 10-agent cumulative trajectories | Generated | Same three metrics. Independent y-axis per model panel. |
| Step 3. Qualitative NLTK phrase repetition | Done | Scripts and audit outputs generated. User now has two Excalidraw diagrams for paper use. |
| Step 4. Scale phrase adoption | Generated | GPT-5 and Gemini Flash Lite, first 60 minutes, raw NLTK top phrase anchors. Needs visual review. |
| Step 5. Run-level delta tables | Not started | Supports captions and prose after plots are chosen. |
| Step 6. Seed condition plots | Not started | Only after trajectory plots are approved. |
| Step 7. HHI concentration | Not started | Separate metric step, not mixed with trajectories. |
| Step 8. Secondary cohorts | Blocked | Only after canonical story is approved. |
| Step 9. Findings prose | Blocked | Only after final plot set is approved. |

## Output locations

Scripts:

```text
scripts/reanalysis-2026-05-06/
```

Plots:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/
```

Future findings draft:

```text
findings/emnlp-2026-paper/findings-reanalysis-2026-05-06.md
```

Input bundle:

```text
data/reanalysis-2026-05-05/
```

## Global rules

<<<<<<< Updated upstream
```text
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/deterministic_run_deltas.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/embedding_run_deltas.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_judge_run_deltas.csv
```

Time-bin input files:

```text
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/deterministic_timebin_metrics.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/embedding_run_timebin_metrics.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_judge_run_timebin_metrics.csv
```

Topic robustness input, if approved later:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness/topic_robustness_run_deltas.csv
```

## Metrics for the first approved sequence

Start with fixed 15-minute trajectories only.

Primary trajectory metrics:

| Metric | Source file | Column | Collapse direction |
|---|---|---|---:|
| Gzip compression ratio | deterministic time bins | `compression_gzip` | down |
| Distinct-5 | deterministic time bins | `distinct_5` | down |
| Vendi Score | embedding time bins | `vendi_score` | down |
| Effective topics (post-text) | `ayush_reanalysis/topic_convergence/topic_run_timebin_metrics.csv` | `effective_topics` | down |
| Effective frames (LLM-judge) | `ayush_reanalysis/llm_frame_topic_convergence/frame_topic_run_timebin_metrics.csv` | `effective_frames` | down |
| Blinded LLM rubric index *(secondary, validation)* | LLM judge time bins | `collapse_index` | up |

### Headline collapse metric: Hill–Shannon `effective_topics = exp(H)`

We use the same operator on two independent inputs:

- **`effective_topics`** — Hill-Shannon diversity of MiniBatchKMeans-12 cluster shares fit on Qwen3-embedding-8b post-text embeddings (SVD-50, L2-normalized). Pipeline: `scripts/ayush-topic-convergence.py` in the main repo.
- **`effective_frames`** — same operator, same embedding model, same clustering hyperparameters, but applied to the *blinded LLM judge's* `dominant_frame` strings (one short label per post). Pipeline: `scripts/reanalysis-2026-05-06/step03_build_llm_frame_topics.py` in the findings-handoff worktree, output under `analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_frame_topic_convergence/`.

Both are old, citable, information-theoretic constructs — Shannon (1948) entropy on a categorical distribution, Hill (1973) effective number conversion `exp(H)`. Direct prior art with this exact operator on LLM-extracted classes: Wright et al. 2025 (arXiv:2510.04226), "Epistemic Diversity and Knowledge Collapse." It is the same eigenvalue construction used in the Vendi Score (Friedman & Dieng 2023), but on cluster shares rather than similarity-matrix eigenvalues. Down means fewer effective topics / frames in the bin → more concentrated discourse.

### LLM judge rubric (kept as secondary validation, not headline)

```text
collapse_index = (semantic_repetition + frame_convergence + consensus_conformity + template_rigidity + (6 - novelty)) / 5
```

All five components are 1–5 judge scores. Higher values mean more judged collapse. Novelty is inverted so low novelty raises the index. We retain the rubric mean as a secondary index because it captures judge dimensions (e.g. `template_rigidity`, `evidence_grounding`) that the frame-clustering operator collapses to a single frame label per post. See `findings/emnlp-2026-paper/llm-collapse-index.md` for the full rubric explanation and fixed-window vs cumulative aggregation formulas.

### Convergent validity check

Step 4 (`scripts/reanalysis-2026-05-06/step04_frame_vs_text_topics.py`, outputs in `findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step04_frame_vs_text_topics/`) joins the two pipelines on `(run_uid, scheme, bin_idx)` and produces:

1. Side-by-side family-mean trajectories of `effective_topics` and `effective_frames` (fixed 15m and normalized quartile).
2. Per-run Δ scatter of `Δ effective_topics` vs `Δ effective_frames` with Pearson r — this is the Campbell & Fiske (1959) convergent-validity figure: same construct (collapse), two methods (post-text embeddings, LLM-judge framing).

Important rules:

1. No cumulative Distinct-5 trajectory plots in the first sequence.
2. No subsampled Distinct-5 in main plots.
3. HHI is a real metric, but it is not part of the first trajectory step because the robust HHI output is a late-minus-early run delta, not a clean fixed 15-minute trajectory.
4. HHI comes later as a separate approved step.
=======
1. One plot answers one question.
2. One step gets reviewed before the next step starts.
3. Run is the inference unit.
4. No pooled family bar charts.
5. No all-in-one heatmaps unless explicitly approved.
6. No scale mixing unless the plot is explicitly about scale.
7. No secondary cohorts until canonical plots are approved.
8. Use paper-facing labels in plots.
9. Save `.png` and `.pdf` for generated figures.
10. Do not write findings prose until the approved figure set is known.
>>>>>>> Stashed changes

## Paper-facing labels

Conditions:

| Internal label | Paper label |
|---|---|
| `mag0` | Empty feed |
| `mag1` | 1 conspiracy seed |
| `mag5` | 5 conspiracy seeds |
| `mag25` | 25 conspiracy seeds |
| `dom-agi` | 25 AGI seeds |
| `dom-tech` | 25 tech seeds |

Models:

| Internal label | Paper label |
|---|---|
| `GPT-5` | GPT-5 |
| `Gemini Flash Lite` | Gemini Flash Lite |
| `Kimi K2.5` | Kimi K2.5 |
| `GLM-5` | GLM-5 |

Scales:

| Agents | Paper label |
|---:|---|
| 10 | 10 agents |
| 20 | 20 agents |
| 30 | 30 agents |

## Step 0. What data are available?

Status: done.

Script:

```text
scripts/reanalysis-2026-05-06/step00_validate_inventory.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step00_inventory/
```

Key result:

1. Canonical fixed 15-minute runs: 48.
2. All four canonical models have six 10-agent runs.
3. Only GPT-5 and Gemini Flash Lite have 10, 20, and 30 agent scales.

## Step 1. Do canonical 10-agent feeds narrow inside fixed time windows?

Status: generated.

Cohort:

```text
internal_family_label = single_model_final
n_agents = 10
scheme = fixed_15m
```

Metrics:

```text
gzip
Distinct-5
blinded LLM collapse index
```

Vendi is skipped for now.

Script:

```text
scripts/reanalysis-2026-05-06/step01_canonical_n10_trajectories.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step01_canonical_n10_trajectories/
```

Generated files:

```text
canonical_n10_gzip_trajectory_by_model.png
canonical_n10_distinct5_trajectory_by_model.png
canonical_n10_llm_collapse_trajectory_by_model.png
```

Decision needed:

Decide whether these trajectory plots are paper candidates, need redesign, or should stay as internal diagnostics.

## Step 2. Does the cumulative feed seen so far narrow over time?

Status: generated.

Cohort:

```text
internal_family_label = single_model_final
n_agents = 10
scheme = fixed_15m
```

Metrics:

```text
cumulative gzip
<<<<<<< Updated upstream
cumulative Distinct-5 recomputed over all post text seen so far
=======
cumulative Distinct-5
>>>>>>> Stashed changes
cumulative blinded LLM collapse index
```

Vendi is skipped for now.

<<<<<<< Updated upstream
Cumulative definition:

| X-axis point | Posts included |
|---|---|
| 0-15 | posts from 0 to 15 minutes |
| 15-30 | posts from 0 to 30 minutes |
| 30-45 | posts from 0 to 45 minutes |
| 45-60 | posts from 0 to 60 minutes |

Metric computation:

1. Gzip cumulative is recomputed from all post text seen so far.
2. Distinct-5 cumulative is recomputed from all post text seen so far.
3. LLM collapse cumulative is the weighted cumulative mean of bin scores, using `n_judged`.

Plot design:

1. One figure per metric.
2. Four panels inside each figure, one panel per model.
3. X-axis: cumulative time cutoff.
4. Y-axis: cumulative metric value.
5. Lines: six seed conditions.
6. Each model panel gets its own y-axis scale.
7. No scale in this step.
8. No HHI in this step.

Planned script:
=======
Script:
>>>>>>> Stashed changes

```text
scripts/reanalysis-2026-05-06/step02_canonical_n10_trajectories_cumulative.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step02_canonical_n10_trajectories_cumulative/
```

Generated files:

```text
canonical_n10_gzip_cumulative_trajectory_by_model.png
canonical_n10_distinct5_cumulative_trajectory_by_model.png
canonical_n10_llm_collapse_cumulative_trajectory_by_model.png
```

Decision needed:

Decide whether cumulative plots add value or whether the paper should emphasize fixed-window trajectories plus qualitative phrase evidence.

## Step 3. What repeated phrases actually appear in agent posts?

Status: done.

Purpose:

Qualitative evidence for local phrase repetition using NLTK n-grams, because aggregate gzip and Distinct-5 can look flat while repeated motifs still appear inside runs.

Cohort:

```text
internal_family_label = single_model_final
n_agents = 10
is_seed = false
```

No seed posts are loaded or used.

N-gram method:

```text
nltk.tokenize.word_tokenize
nltk.util.ngrams
N = 5
punctuation retained
casing retained
stopwords retained
no stemming
no lemmatization
within sentence boundaries
```

Script:

```text
scripts/reanalysis-2026-05-06/step03_canonical_n10_nltk_phrase_repetition.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step03_canonical_n10_nltk_phrase_repetition/
```

Generated audit outputs:

```text
canonical_n10_nltk_top_5grams.csv
canonical_n10_phrase_examples.md
README.md
summary.json
```

Generated draft plots:

```text
canonical_n10_nltk_phrase_echo_ledger.png
canonical_n10_nltk_phrase_echo_examples.png
```

Paper status:

The user now has two Excalidraw versions for this qualitative evidence. Treat those as the paper-facing diagrams unless we later decide to regenerate them from code.

## Step 4. Does scale protect diversity?

Status: generated for review. This step uses **scale phrase adoption**, not generic metric trajectories.

Question:

> Does adding more agents dilute local attractors, or does the repeated phrase spread across more agents?

Why this is separate:

Only GPT-5 and Gemini Flash Lite have complete 10, 20, and 30 agent canonical runs. Scale should not be mixed into the four-model 10-agent plots.

Cohort:

```text
internal_family_label = single_model_final
model_display in {GPT-5, Gemini Flash Lite}
n_agents in {10, 20, 30}
is_seed = false
```

Implemented analysis:

1. Use raw exact NLTK 5-token phrase anchors.
2. For each run, identify the strongest repeated exact anchor by agents, then posts, then mentions.
3. Count how many agents use the phrase.
4. Count how many posts contain the phrase.
5. Count total mentions.
6. Compute top-agent share.
7. Compare 10, 20, and 30 agent scales inside the same model.
8. Keep GPT-5 and Gemini Flash Lite separate.

Recommended plot design:

1. One compact figure per model.
2. X-axis: scale, 10 agents, 20 agents, 30 agents.
3. Y-axis: adopters of the top phrase, or adoption rate.
4. Optional second encoded value: posts containing the top phrase.
5. Do not include Kimi K2.5 or GLM-5.
6. Do not mix this with gzip, Distinct-5, or LLM trajectories.

Script:

```text
scripts/reanalysis-2026-05-07/step04_scale_phrase_adoption.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step04_scale_phrase_adoption/
```

Generated files:

```text
scale_phrase_adoption_gpt5_gemini.png
scale_phrase_adoption_gpt5_gemini.pdf
scale_phrase_adoption_by_run.csv
scale_phrase_adoption_summary.csv
README.md
summary.json
```

Approval gate:

Review the figure. If approved, promote it to the `approved/` folder. If not, revise only this step before moving on.

## Step 5. Are trajectory impressions supported at the run level?

Status: not started.

Purpose:

Produce tables for captions and prose. These are not main figures.

Cohorts:

1. Canonical 10-agent runs for all four models.
2. GPT-5 and Gemini Flash Lite scale runs, if Step 4 is generated.

Planned script:

```text
scripts/reanalysis-2026-05-06/step05_run_delta_tables.py
```

Planned output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step05_run_delta_tables/
```

Statistics:

1. Median late-minus-early delta.
2. Sign count in the collapse direction.
3. Exact sign-test p-value only as a small-n descriptive statistic.
4. No post-level tests.

## Step 6. Do seed conditions change collapse relative to empty feed?

Status: not started.

Question:

> Do seeds steer the kind of collapse, or do agent feeds narrow even without seeds?

This step should wait until we know which trajectory plots are paper candidates.

Recommended first pass:

1. 10-agent canonical runs only.
2. One model per figure.
3. One metric per figure.
4. Empty feed shown as the first condition.
5. No scale pooling.
6. No model pooling.

Planned script:

```text
scripts/reanalysis-2026-05-06/step06_condition_lollipops.py
```

Planned output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step06_condition_lollipops/
```

## Step 7. Do later posts concentrate into fewer embedding clusters?

Status: not started.

HHI is valid but remains separate from the main trajectories.

Metric:

```text
C = (sum_j p_j^2 - 1/k) / (1 - 1/k)
```

Input:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness/topic_robustness_run_deltas.csv
```

Recommended first pass:

1. One figure per model at 10-agent scale.
2. X-axis: seed condition.
3. Y-axis: robust late-minus-early normalized HHI delta.
4. Horizontal zero line.
5. No heatmap.
6. No model pooling.

Planned script:

```text
scripts/reanalysis-2026-05-06/step07_hhi_condition_plots.py
```

Planned output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step07_hhi_condition_plots/
```

## Step 8. Secondary cohorts

Status: blocked.

Do not start these until the canonical story is approved.

Possible later substeps:

1. Base-model-as-tool trajectories.
2. Mixed-model roster trajectories.
3. Obsession prompting quartile trajectories.

Rules:

1. Do not mix these cohorts with canonical plots.
2. Obsession prompting uses quartiles, not fixed 15-minute bins.
3. Any comparison to canonical runs should be separately approved.

## Step 9. Findings prose

Status: blocked.

Target file:

```text
findings/emnlp-2026-paper/findings-reanalysis-2026-05-06.md
```

Only write this after the final figure set is approved.

Proposed structure:

1. What happens inside an agent-only feed?
2. What do deterministic metrics miss?
3. What repeated language appears in posts?
4. Does scale protect diversity?
5. Do seeds steer the collapse?
6. What does this imply for agentic social media?

Writing rules:

1. No em dashes.
2. Use paper-facing labels.
3. Keep claims tied to approved figures or tables.
4. Do not overclaim from HHI.
5. Keep the main claim simple: agent-feed feedback can narrow discourse over time.

## Immediate next decision

Choose one:

1. Approve Step 4 scale phrase adoption for GPT-5 and Gemini Flash Lite.
2. Pause plots and make run-level delta tables for existing Step 1, Step 2, and Step 3 evidence.
3. Redesign or drop the Step 1 and Step 2 trajectory plots before moving to scale.

Recommended next action:

Approve Step 4 scale phrase adoption. This matches the original findings spine better than generic scale metric trajectories.
