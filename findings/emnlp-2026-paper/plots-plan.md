# Reanalysis Plot Plan — 2026-05-05

Status: **proposal only; do not implement until approved**.

Dataset source: `https://huggingface.co/datasets/Ayushnangia/moltbook-ayush-reanalysis-20260505`

Local data path: `data/reanalysis-2026-05-05/`

Download/validation note: the dataset was re-downloaded with `hf download --repo-type dataset --local-dir data/reanalysis-2026-05-05`. Against `FILE_MANIFEST.csv`, all 977 manifest entries are present. All analysis/data files match checksum. The only remaining mismatch is `.gitattributes` size, which is not analysis data.

## Goal

Create statistically valid, paper-presentable plots for the 2026-05-05 reanalysis without pooling incompatible experimental units.

The earlier family-level bar plots are not acceptable for the main paper because they collapse heterogeneous run sets into a single `n=48`, `n=18`, `n=9`, or `n=6` estimate. Those cohorts are not directly comparable: the canonical single-model cohort contains different models, conditions, and scales; the base-model, mixed-roster, and obsession cohorts have different designs.

The revised plan keeps the experimental design visible:

- one plotted cell/point/line should correspond to one run or to a matched within-design comparison;
- canonical single-model runs are primary evidence;
- base-model-as-tool, mixed-roster, and obsession-prompted runs are secondary probes;
- scale claims use only GPT-5 and Gemini Flash Lite, because only those two models have `n10`, `n20`, and `n30`;
- intervention/variant claims are matched by condition where possible;
- no post-level significance tests are used as paper evidence.

## Output locations

Plots will be written under:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/
```

Analysis and plotting scripts will be written under:

```text
scripts/reanalysis-2026-05-05/
```

Previously written scripts used as inputs or references will be documented in:

```text
scripts/reanalysis-2026-05-05/external-scripts.md
```

## Data files to use

Primary run-level and time-bin files from the bundle:

```text
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/deterministic_run_deltas.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/deterministic_timebin_metrics.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/embedding_run_deltas.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/embedding_run_timebin_metrics.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/topic_convergence/topic_run_deltas.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/topic_convergence/topic_run_timebin_metrics.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_judge_run_deltas.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_judge_run_timebin_metrics.csv
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/data_manifest.csv
```

LLM judge results are available, but the default plan is to keep them as secondary/appendix evidence unless explicitly approved for main-text use.

## Primary metrics

| Phenomenon | Primary metric | Collapse direction |
|---|---|---:|
| Compression / redundancy | `delta_compression_gzip` | negative |
| Lexical diversity | `delta_distinct_5_sub_mean` | negative |
| Semantic diversity | `delta_vendi_score` | negative |
| Embedding-topic concentration | `delta_topic_entropy_norm` | negative |

Secondary metrics available for sensitivity/appendix:

- `delta_distinct_5`
- `delta_distinct_5_cumulative`
- `delta_simpson_5gram_effective`
- `delta_mean_pairwise_cosine`
- `delta_semantic_radius`
- `delta_dominant_share`
- `delta_effective_topics`
- `delta_topic_hhi`
- `delta_collapse_index` from blinded LLM judge

## Paper-facing labels

Proposed condition labels:

| Internal label | Paper-facing label |
|---|---|
| `mag0` | Empty feed |
| `mag1` | 1 conspiracy seed |
| `mag5` | 5 conspiracy seeds |
| `mag25` | 25 conspiracy seeds |
| `dom-agi` | 25 AGI seeds |
| `dom-tech` | 25 tech seeds |

Proposed cohort labels:

| Internal label | Paper-facing label |
|---|---|
| `single_model_final` | Homogeneous single-model agents |
| `base_model_as_tool` | Base-model-as-tool agents |
| `mixed_model_roster` | Mixed-model roster |
| `obsession_prompting` | Obsession-prompted agents |

## Plot set

### 1. Canonical single-model design matrices

Purpose: show the canonical 48 runs without pooling across models, seed conditions, or scales.

Design:

- facet/panel = model;
- rows = seed conditions;
- columns = agent scale;
- one cell = one run;
- color = last-bin minus first-bin delta;
- zero-centered diverging color scale;
- fixed 15-minute deltas.

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_distinct5_subsampled_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_topic_entropy_fixed15m.png
```

Proposed figure wording:

> Each cell is one canonical run. Negative gzip, Distinct-5, Vendi, and topic-entropy deltas indicate entropy collapse. This view preserves the experimental design rather than averaging across models, seed conditions, or scales.

This is the main paper evidence because it shows how widespread the phenomenon is while keeping run identity visible.

### 2. Canonical per-run temporal trajectories

Purpose: show that run deltas are not hiding unusual trajectories.

Design:

- panel = model × scale;
- x = time bin;
- y = metric value;
- line = seed condition;
- no averaging across runs;
- fixed 15-minute bins.

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_trajectories_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_trajectories_distinct5_subsampled_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_trajectories_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_trajectories_topic_entropy_fixed15m.png
```

Proposed figure wording:

> Lines are individual condition runs, not cohort averages. The trajectory plots show whether collapse appears gradually, abruptly, or non-monotonically inside each experimental cell.

### 3. Scale effect, only where scale is factorial

Purpose: test whether larger groups protect against collapse, using only models that actually have all three scales.

Valid models:

- GPT-5: `n10`, `n20`, `n30` × 6 conditions;
- Gemini Flash Lite: `n10`, `n20`, `n30` × 6 conditions.

Do not use Kimi K2.5 or GLM-5 for scale claims because they only have `n10`.

Design:

- one panel per model;
- x = `n10`, `n20`, `n30`;
- y = run delta;
- line = same seed condition across scales;
- fixed 15-minute deltas.

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_distinct5_subsampled_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_topic_entropy_fixed15m.png
```

Statistical treatment:

- condition is the block;
- compare `n30 - n10` within each condition;
- report median paired difference and exact sign test over 6 condition-pairs per model;
- do not make a global scale claim across all four models.

Proposed figure wording:

> Scale is analyzed only for GPT-5 and Gemini Flash Lite, the two models with all three group sizes. Lines connect the same seed condition across scales, so the figure tests whether increasing group size protects that condition from collapse.

### 4. Seed-condition effect relative to empty feed

Purpose: separate collapse caused by seeds from collapse that appears even with an empty feed.

Matched comparison:

- block = model × scale;
- compare each seeded condition against `mag0` within the same model × scale;
- valid blocks only.

Design:

- x = seed condition;
- y = `delta(condition) - delta(empty feed)`;
- points = model × scale blocks;
- horizontal zero line;
- fixed 15-minute deltas.

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/conditions/condition_vs_empty_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/conditions/condition_vs_empty_distinct5_subsampled_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/conditions/condition_vs_empty_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/conditions/condition_vs_empty_topic_entropy_fixed15m.png
```

Proposed figure wording:

> Each point compares a seed condition to the empty-feed control within the same model and scale. This plot asks whether seeds strengthen or weaken collapse relative to that run family's own empty-feed baseline.

### 5. Matched n10 model/roster comparison

Purpose: compare models and rosters only where the experimental design is shared.

Included rows:

- GPT-5;
- Gemini Flash Lite;
- Kimi K2.5;
- GLM-5;
- OLMo 3 32B Base;
- OLMo 3 32B Instruct;
- Qwen 3.5 35B A3B Base;
- Mixed roster Qwen 3.5 27B.

Columns:

- Empty feed;
- 1 conspiracy seed;
- 5 conspiracy seeds;
- 25 conspiracy seeds;
- 25 AGI seeds;
- 25 tech seeds.

Design:

- one cell = one `n10` run;
- color = delta;
- fixed 15-minute deltas;
- descriptive comparison only.

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/n10/n10_model_condition_matrix_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/n10/n10_model_condition_matrix_distinct5_subsampled_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/n10/n10_model_condition_matrix_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/n10/n10_model_condition_matrix_topic_entropy_fixed15m.png
```

Proposed figure wording:

> This matched n10 matrix compares models and rosters only in the six seed conditions they all share. It is descriptive, not a pooled estimate across incompatible cohorts.

### 6. Mixed-roster comparison against homogeneous n10 baselines

Purpose: show the mixed-model roster without pretending its six runs are directly comparable to the full 48-run canonical inventory.

Design:

- x = condition;
- y = metric delta;
- points = homogeneous n10 single-model runs plus mixed roster;
- mixed roster highlighted;
- fixed 15-minute deltas;
- no averaging across all conditions.

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/mixed/mixed_vs_homogeneous_n10_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/mixed/mixed_vs_homogeneous_n10_distinct5_subsampled_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/mixed/mixed_vs_homogeneous_n10_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/mixed/mixed_vs_homogeneous_n10_topic_entropy_fixed15m.png
```

Proposed figure wording:

> The mixed roster is compared condition-by-condition against homogeneous n10 runs. This avoids treating six mixed runs as directly comparable to the full 48-run canonical inventory.

### 7. Obsession intervention matched to GPT-5 n10 baseline

Purpose: evaluate obsession prompting as an intervention while respecting its unbalanced design.

Use normalized quartile deltas because obsession outputs are available only for normalized quartiles in the current reanalysis.

Comparison:

- GPT-5 obsession run vs GPT-5 canonical n10 in the same seed condition;
- `mag25` has multiple obsession repeats: show individual dots, but use condition-level median for inference;
- Gemini Flash Lite obsession `mag25` is shown as a separate single-case note, not pooled with GPT-5.

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/obsession/obsession_vs_gpt5_n10_gzip_quartile.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/obsession/obsession_vs_gpt5_n10_distinct5_subsampled_quartile.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/obsession/obsession_vs_gpt5_n10_vendi_quartile.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/obsession/obsession_vs_gpt5_n10_topic_entropy_quartile.png
```

Proposed figure wording:

> Obsession prompting is evaluated as a matched intervention against GPT-5 n10 runs in the same seed condition. Individual repeats are shown, but condition-level summaries prevent mag25 from dominating the comparison.

## Statistical tables

Statistical tables should be written under:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/
```

Planned outputs:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/canonical_model_direction_tests.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/scale_paired_tests_gpt5_gemini.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/condition_vs_empty_matched_tests.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/n10_model_condition_summary.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/mixed_vs_homogeneous_matched_summary.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/obsession_matched_condition_summary.csv
```

Rules:

- main unit of inference is the run;
- use exact sign tests over runs or matched blocks;
- report median deltas and sign counts;
- use bootstrap CIs only where run-level `n` is meaningful;
- do not use post-level significance tests;
- do not report family-level pooled bars as main evidence.

## Script plan

Planned script layout:

```text
scripts/reanalysis-2026-05-05/
  README.md
  common.py
  validate_reanalysis_bundle.py
  build_canonical_design_plots.py
  build_canonical_trajectory_plots.py
  build_scale_paired_plots.py
  build_condition_vs_empty_plots.py
  build_n10_comparison_plots.py
  build_mixed_roster_plots.py
  build_obsession_matched_plots.py
  build_stats_tables.py
  run_all.sh
  external-scripts.md
```

`external-scripts.md` should document the bundled scripts and provenance:

```text
data/reanalysis-2026-05-05/scripts/ayush-analysis-plan-execute.py
data/reanalysis-2026-05-05/scripts/ayush-topic-convergence.py
data/reanalysis-2026-05-05/scripts/ayush-blind-llm-judge.py
data/reanalysis-2026-05-05/scripts/ayush-finalize-judge-results.py
data/reanalysis-2026-05-05/scripts/ayush-final-report.py
```

Original worktree/branch provenance:

```text
worktree: /Users/agokrani/Documents/git/moltbook-obsession-frontier-mixed-and-archive
branch: obsession-frontier-mixed-and-archive
commit: bad88a8
```

## Findings narrative after plots

The updated narrative should avoid a single pooled average over all runs. Proposed wording:

> The main result is not a single pooled average over all runs. Instead, the canonical design matrix shows that entropy-collapse signatures recur across many individual model × condition × scale cells. The pattern is strongest and most consistent for GPT-5 and Gemini Flash Lite, visible for Kimi K2.5 and GLM-5 in lexical/compression metrics, and heterogeneous for embedding-topic metrics. Larger groups do not cleanly preserve diversity in the models where scale is factorial. Seed conditions modulate the collapse but do not fully explain it, because empty-feed controls also narrow. Secondary cohorts show that base-model tooling, mixed rosters, and obsession prompting change the collapse signature rather than clearly eliminating it.

## Open questions before implementation

1. Should `delta_distinct_5_sub_mean` be the primary lexical plot metric? Recommendation: yes, because it controls for bin-size differences.
2. Should LLM-judge results stay appendix/secondary only? Recommendation: yes, unless explicitly approved for main text.
3. Are the proposed paper-facing condition labels acceptable?
4. Should implementation generate all candidate plots first, then select which enter `findings.md`, or generate only the core canonical plots first?
