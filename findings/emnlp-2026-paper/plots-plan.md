# Reanalysis plot plan, 2026-05-06

Status: Step 0–2 outputs exist and were verified on 2026-05-07. Do not generate later-step plots until the exact step is approved.

This replaces the 2026-05-05 plotting approach. The 2026-05-05 plots should be treated as discarded draft outputs unless a specific file is later rescued.

## What went wrong in the last pass

The previous plots tried to show too much at once.

Problems to avoid:

1. Large model x condition x scale heatmaps were hard to read.
2. Scale was mixed into charts that were not only about scale.
3. Secondary cohorts were plotted before the canonical story was clear.
4. Some plots compared cohorts that do not share the same design.
5. Cumulative metrics were visually mixed with fixed 15-minute trajectories.
6. The plan allowed too many figures to be generated before review.

The new rule is simple:

> One plot answers one question. One step generates one small family of plots. Each step needs approval before the next step.

## Output locations for the new pass

Scripts:

```text
scripts/reanalysis-2026-05-06/
```

Plots:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/
```

Readable findings draft, only after approved plots exist:

```text
findings/emnlp-2026-paper/findings-reanalysis-2026-05-06.md
```

## Data source

Use the clean 2026-05-05 reanalysis bundle as input:

```text
data/reanalysis-2026-05-05/
```

Run-level input files:

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

## Global figure rules

These rules apply to every step.

1. No all-in-one heatmaps unless explicitly approved later.
2. No chart should mix canonical, mixed roster, base-model, and obsession cohorts.
3. No scale comparison unless the plot is explicitly a scale plot.
4. No model comparison unless the plot is explicitly a matched model comparison.
5. No post-level significance tests.
6. No internal labels in figure titles or axes.
7. Use plain language titles framed as questions.
8. Save both `.png` and `.pdf`.
9. Write a small `README.md` in each plot folder explaining how to read that step.
10. Do not write final findings prose until the plots in that step are approved.

## Step 0. Validate inputs and produce a run inventory

Purpose:

Confirm what is available before plotting anything.

Script:

```text
scripts/reanalysis-2026-05-06/step00_validate_inventory.py
```

Outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step00_inventory/run_inventory.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step00_inventory/metric_availability.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step00_inventory/README.md
```

What to check:

1. Canonical single-model runs: 48.
2. GPT-5 and Gemini Flash Lite have 10, 20, and 30 agent runs.
3. Kimi K2.5 and GLM-5 only have 10 agent canonical runs.
4. Obsession prompting uses normalized quartiles, not fixed 15-minute bins.
5. Time-bin metrics exist for gzip, Distinct-5, Vendi, and LLM collapse index.

Approval gate:

Review the inventory table. If the table is right, approve Step 1.

## Step 1. Main canonical trajectories at the matched 10-agent scale

Question:

> Do agent-only feeds narrow over time when all models are compared at the same group size?

Why this comes first:

All four canonical models have 10-agent runs. This avoids scale mixing and gives the cleanest first view.

Cohort:

```text
internal_family_label = single_model_final
n_agents = 10
scheme = fixed_15m
```

Metrics:

```text
gzip
fixed-window Distinct-5
blinded LLM collapse index
```

Vendi is skipped for now in this step.

Plot design:

1. One figure per metric.
2. Four panels inside each figure, one panel per model.
3. X-axis: 15-minute time bin.
4. Y-axis: raw metric value, not delta.
5. Lines: six seed conditions.
6. Each model panel gets its own y-axis scale.
7. No scale in this step.
8. No cumulative metric in this step.
9. No HHI in this step.

Planned script:

```text
scripts/reanalysis-2026-05-06/step01_canonical_n10_trajectories.py
```

Planned output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step01_canonical_n10_trajectories/
```

Planned files:

```text
canonical_n10_gzip_trajectory_by_model.png
canonical_n10_distinct5_trajectory_by_model.png
canonical_n10_llm_collapse_trajectory_by_model.png
```

How to read the plots:

- Gzip down means text became easier to compress and more redundant.
- Distinct-5 down means fewer unique 5-grams.
- LLM collapse up means more judged repetition, rigidity, conformity, and lower novelty.

Approval gate:

Review these 3 combined plots. If they are readable, approve Step 2. If not, adjust only Step 1 before moving on.

## Step 2. Cumulative canonical trajectories at the matched 10-agent scale

Question:

> Does the total feed seen so far become narrower as the run proceeds?

Why this comes now:

Step 1 showed the metric value inside each separate 15-minute window. Step 2 asks the cumulative version of the same question. The x-axis stays the same, but each point uses all non-seed posts up to that time.

Cohort:

```text
internal_family_label = single_model_final
n_agents = 10
scheme = fixed_15m
```

Metrics:

```text
cumulative gzip
cumulative Distinct-5 recomputed over all post text seen so far
cumulative blinded LLM collapse index
```

Vendi is skipped for now in this step.

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

```text
scripts/reanalysis-2026-05-06/step02_canonical_n10_trajectories_cumulative.py
```

Planned output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step02_canonical_n10_trajectories_cumulative/
```

Planned files:

```text
canonical_n10_gzip_cumulative_trajectory_by_model.png
canonical_n10_distinct5_cumulative_trajectory_by_model.png
canonical_n10_llm_collapse_cumulative_trajectory_by_model.png
```

Approval gate:

Review these 3 cumulative plots. If they are readable, approve the scale step.

## Step 3. Scale trajectories for GPT-5 and Gemini Flash Lite only

Question:

> Does adding more agents preserve diversity, or does the feed still narrow?

Why this is separate:

Scale should not be mixed into the main canonical trajectory plots. Only GPT-5 and Gemini Flash Lite have 10, 20, and 30 agent canonical runs.

Cohort:

```text
internal_family_label = single_model_final
model_display in {GPT-5, Gemini Flash Lite}
n_agents in {10, 20, 30}
scheme = fixed_15m
```

Plot design:

1. One figure per model per metric.
2. Six panels in the figure, one panel per seed condition.
3. X-axis: 15-minute time bin.
4. Y-axis: raw metric value.
5. Lines: 10 agents, 20 agents, 30 agents.
6. Do not put GPT-5 and Gemini in the same chart.
7. Do not include Kimi K2.5 or GLM-5.

Planned script:

```text
scripts/reanalysis-2026-05-06/step03_scale_trajectories.py
```

Planned output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step03_scale_trajectories/
```

Planned files:

```text
gpt5_scale_gzip_trajectory.png
gpt5_scale_distinct5_trajectory.png
gpt5_scale_vendi_trajectory.png
gpt5_scale_llm_collapse_trajectory.png

gemini_flash_lite_scale_gzip_trajectory.png
gemini_flash_lite_scale_distinct5_trajectory.png
gemini_flash_lite_scale_vendi_trajectory.png
gemini_flash_lite_scale_llm_collapse_trajectory.png
```

Approval gate:

Review the eight scale figures. If they are readable, approve the next step.

## Step 3. Run-level late-minus-early tables for the approved trajectory plots

Question:

> Are the trajectory impressions supported by run-level deltas?

Purpose:

This step produces tables, not main plots. It supports the captions and findings text.

Cohorts:

1. Canonical 10-agent runs for all four models.
2. GPT-5 and Gemini Flash Lite scale runs.

Script:

```text
scripts/reanalysis-2026-05-06/step03_run_delta_tables.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step03_run_delta_tables/
```

Planned files:

```text
canonical_n10_run_deltas.csv
canonical_n10_model_summary.csv
scale_run_deltas_gpt5_gemini.csv
scale_model_summary.csv
README.md
```

Statistics:

1. Median late-minus-early delta.
2. Sign count in the collapse direction.
3. Exact sign-test p-value only as a small-n descriptive statistic.
4. No post-level tests.

Approval gate:

Review whether the tables match the approved plots. If yes, approve Step 4.

## Step 4. Seed condition plots, matched within model and scale

Question:

> Do seeds change the direction or strength of collapse compared with the empty-feed control?

Why this is after Step 1 and Step 2:

The empty-feed comparison only makes sense after the raw trajectories are approved.

Plot design:

1. One figure per model, scale, and metric.
2. X-axis: seed condition.
3. Y-axis: late-minus-early collapse score.
4. Empty feed appears as the first condition, not as a hidden baseline.
5. No model pooling.
6. No scale pooling.
7. No gray swarm of many unrelated blocks.

Collapse score direction:

- Gzip: multiply delta by `-1` so higher means more collapse.
- Distinct-5: multiply delta by `-1`.
- Vendi: multiply delta by `-1`.
- LLM collapse index: keep delta as is.

Planned script:

```text
scripts/reanalysis-2026-05-06/step04_condition_lollipops.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step04_condition_lollipops/
```

Initial planned files:

Only generate the 10-agent canonical set first:

```text
gpt5_n10_condition_gzip.png
gpt5_n10_condition_distinct5.png
gpt5_n10_condition_vendi.png
gpt5_n10_condition_llm_collapse.png

gemini_flash_lite_n10_condition_gzip.png
gemini_flash_lite_n10_condition_distinct5.png
gemini_flash_lite_n10_condition_vendi.png
gemini_flash_lite_n10_condition_llm_collapse.png

kimi_k25_n10_condition_gzip.png
kimi_k25_n10_condition_distinct5.png
kimi_k25_n10_condition_vendi.png
kimi_k25_n10_condition_llm_collapse.png

glm5_n10_condition_gzip.png
glm5_n10_condition_distinct5.png
glm5_n10_condition_vendi.png
glm5_n10_condition_llm_collapse.png
```

Do not generate 20-agent or 30-agent condition plots until the 10-agent condition plots are approved.

Approval gate:

Review the 10-agent condition plots. Decide whether to generate 20-agent and 30-agent condition plots for GPT-5 and Gemini Flash Lite.

## Step 5. HHI embedding-cluster concentration

Question:

> Do later posts concentrate into fewer embedding clusters?

Why this is separate:

HHI is a proper metric, but the robust version is not a simple raw time trajectory. It is a late-minus-early concentration delta averaged across k and random seed settings. It should not be mixed with the Step 1 time-series plots.

Metric:

```text
C = (sum_j p_j^2 - 1/k) / (1 - 1/k)
```

where `p_j` is the share of posts in embedding cluster `j`.

Input:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness/topic_robustness_run_deltas.csv
```

Plot design:

1. One figure per model and scale.
2. X-axis: seed condition.
3. Y-axis: robust late-minus-early normalized HHI delta.
4. One dot per condition.
5. Horizontal zero line.
6. No heatmap in the first HHI pass.
7. No model pooling.
8. No scale pooling.

Planned script:

```text
scripts/reanalysis-2026-05-06/step05_hhi_condition_plots.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step05_hhi_condition_plots/
```

Initial planned files:

```text
gpt5_n10_hhi_concentration.png
gemini_flash_lite_n10_hhi_concentration.png
kimi_k25_n10_hhi_concentration.png
glm5_n10_hhi_concentration.png
```

If these are approved, then generate scale-specific HHI plots for GPT-5 and Gemini Flash Lite:

```text
gpt5_n20_hhi_concentration.png
gpt5_n30_hhi_concentration.png
gemini_flash_lite_n20_hhi_concentration.png
gemini_flash_lite_n30_hhi_concentration.png
```

Approval gate:

Review whether HHI plots are readable and worth including. If yes, approve Step 6.

## Step 6. Secondary cohorts, only after canonical plots are approved

Secondary cohorts should not appear in the main story until the canonical story is visually stable.

### Step 6A. Base-model-as-tool runs

Question:

> Do base-model-as-tool agents show the same kind of narrowing?

Design:

1. Same plotting grammar as Step 1.
2. One model per figure.
3. 10-agent scale only.
4. Fixed 15-minute bins only.

Script:

```text
scripts/reanalysis-2026-05-06/step06a_base_model_trajectories.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step06a_base_model_trajectories/
```

Approval gate:

Review before any mixed-roster or obsession plots are generated.

### Step 6B. Mixed-model roster

Question:

> Does a mixed roster avoid narrowing, or does it narrow in a different way?

Design:

1. Plot mixed roster trajectories by condition.
2. Do not compare it to all canonical runs in the same chart.
3. If a comparison is needed, compare only to the matched 10-agent canonical runs in a separate table first.
4. No star charts and no gray point clouds.

Script:

```text
scripts/reanalysis-2026-05-06/step06b_mixed_roster_trajectories.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step06b_mixed_roster_trajectories/
```

Approval gate:

Review the mixed-roster-only trajectories first. Approve any comparison plot separately.

### Step 6C. Obsession prompting

Question:

> Does obsession prompting change the collapse trajectory?

Important design constraint:

Obsession prompting uses normalized quartile bins in the current reanalysis. It should not be mixed visually with fixed 15-minute canonical trajectories.

Design:

1. Use quartile x-axis: Q1, Q2, Q3, Q4.
2. One model per figure.
3. One metric per figure.
4. If comparing to GPT-5 n10 baseline, show it as a separate approved comparison after the obsession-only plot is reviewed.

Script:

```text
scripts/reanalysis-2026-05-06/step06c_obsession_quartile_trajectories.py
```

Output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step06c_obsession_quartile_trajectories/
```

Approval gate:

Review obsession-only plots first. Approve any baseline comparison separately.

## Step 7. Findings draft

Only write the findings file after the approved plots exist.

Target file:

```text
findings/emnlp-2026-paper/findings-reanalysis-2026-05-06.md
```

Proposed structure:

1. What happens inside an agent-only feed?
2. Does the same narrowing appear across models?
3. Does more scale protect diversity?
4. Do seeds steer the collapse, or cause it?
5. Do cluster concentrations support the same story?
6. What does this imply for fully agentic social media?

Writing rules:

1. No em dashes.
2. No internal labels unless they are in code blocks or tables.
3. Do not overclaim topic convergence from HHI.
4. Keep the main claim simple: agent-feed feedback can narrow discourse over time.
5. Tie every claim to an approved figure or table.

## Step order summary

| Step | Output type | Requires approval before next step? |
|---|---|---:|
| Step 0 | Inventory tables | yes |
| Step 1 | Canonical 10-agent trajectories | yes |
| Step 2 | Scale trajectories for GPT-5 and Gemini | yes |
| Step 3 | Run-level delta tables | yes |
| Step 4 | Condition plots | yes |
| Step 5 | HHI concentration plots | yes |
| Step 6A | Base-model trajectories | yes |
| Step 6B | Mixed-roster trajectories | yes |
| Step 6C | Obsession quartile trajectories | yes |
| Step 7 | Findings prose | final review |

## Immediate next action after this plan is approved

Only implement Step 0.

Do not create Step 1 plots until the Step 0 inventory is reviewed and approved.
