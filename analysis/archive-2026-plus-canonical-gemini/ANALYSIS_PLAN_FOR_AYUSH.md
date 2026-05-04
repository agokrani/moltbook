# Analysis Plan for Ayush Review

**Status:** executed on reviewed local sources; smoke/test runs and the qwen3.6 mixed-roster variant are excluded from the final analysis package.
**Purpose:** define a literature-correct analysis pipeline for Moltbook final-run, roster, base-model-tool, and obsession-prompting experiments without pooling incompatible runs prematurely.

---

## 0. Core principle

The main unit of inference is the **run**, not the post.

Posts are nested inside agents; agents are nested inside runs; runs are nested inside experimental families, model configurations, conditions, and agent-count scales. Therefore, the correct analysis order is:

```text
post-level data
→ run × time-bin metrics
→ within-run change metrics
→ family/model/condition summaries over runs
→ combined comparison
```

The combined analysis must not start by pooling all posts into one group-level bin. Pooled post averages are only allowed as clearly labeled descriptive diagnostics, not as the main statistical evidence, because runs with more posts would dominate the estimate.

---

## 1. Confirmed scope

### 1.1 Include

#### A. Single-model final runs

- **Internal family label:** `single_model_final`
- **Source:** local HuggingFace canonical export from `agokrani`; this export is understood to already contain the merged/resumed canonical runs.
- **Do not use in graph labels:** `canonical-48`.
- **Display rule:** graphs/tables should use the actual model name and condition rather than the folder name.
  - Example labels:
    - `GPT-5 / mag0 / n10`
    - `Gemini Flash Lite / dom-agi / n20`
    - `Kimi K2.5 / mag25 / n10`
    - `GLM-5 / dom-tech / n10`
- **Experimental meaning:** one LLM family powers all agents in a run, across agent counts and starting seed-post conditions.

#### B. Mixed-model roster

- **Internal family label:** `mixed_model_roster`
- **Display name:** `Mixed-model roster`
- **Source:** local HuggingFace dataset `Ayushnangia/moltbook-frontier-mixed-1h`.
- **Variant rule:** include the `qwen3.5-27b` six-condition roster; exclude the extra `qwen3.6-plus` mag25 variant unless separately requested.
- **Experimental meaning:** different agents/personalities in the same run are powered by different LLMs, forming a mixed roster.
- **Primary breakdown:** roster run, condition, agent identity, and agent model/personality where metadata is reliable.

#### C. Base model as tool

- **Internal family label:** `base_model_as_tool`
- **Display name:** `Base model as tool`
- **Source:** local curated HuggingFace bundle `Ayushnangia/moltbook-curated-20260505`, subdirectory `2026-05-05/base-model`.
- **Exclusion rule:** use the curated bundle as cleaned input; still exclude any run path containing `ignore` if encountered.
- **Experimental meaning:** base/open-weight models are used as tools inside the Moltbook setup.

#### D. Obsession prompting

- **Internal family label:** `obsession_prompting`
- **Display name:** `Obsession prompting`
- **Source:** local curated HuggingFace bundle `Ayushnangia/moltbook-curated-20260505`, subdirectory `2026-05-05/obsession`.
- **Duration rule:** use the full available run duration.
- **Temporal rule:** use normalized quartiles for the main full-duration analysis.

### 1.2 Exclude

- Old archive `entropy-collapse` group, including the previously indexed 51,061-row archive group.
- `source-citation` / site-citation runs.
- Any run path containing `smoke`.
- Any zero-duration run (`duration_minutes <= 0`).
- Any base-model path containing `ignore`.
- The `qwen3.6-plus` frontier-mixed variant.
- Seed/system posts from LLM-as-judge scoring.

### 1.3 Important naming rule

Do not use raw archive/folder names as paper-facing graph labels when they are misleading. In particular:

| Raw/internal source | Paper-facing naming |
|---|---|
| `canonical-48` | Do not use directly; label by model + condition + scale |
| `frontier/mixed-model` | `Mixed-model roster` |
| `base-model` | `Base model as tool` |
| `obsession` | `Obsession prompting` |
| old archive `entropy-collapse` | excluded |

---

## 2. Data manifest stage

Before metrics are computed, build a clean manifest that records every included/excluded run and why.

### 2.1 Required manifest fields

For each run:

- `run_uid`
- `source_dataset`
- `source_path`
- `internal_family_label`
- `display_family_label`
- `model_family`
- `roster_name` if mixed-model roster
- `condition`
- `n_agents`
- `scale`
- `duration_minutes`
- `n_posts_total`
- `n_posts_nonseed`
- `n_seed_posts`
- `n_agents_observed`
- `include_in_main`
- `exclusion_reason`
- `notes`

### 2.2 Manifest validation checks

The manifest must verify:

1. Old archive `entropy-collapse` has zero included runs.
2. `source-citation` has zero included runs.
3. Base-model paths containing `ignore` have zero included runs.
4. Smoke/test paths containing `smoke` have zero included runs.
5. Zero-duration runs have zero included runs.
6. Single-model final runs come from the agokrani canonical export.
7. Obsession prompting uses full duration for included nonzero-duration runs.
8. Non-seed post counts are nonzero for every included run.
9. Conditions are parsed consistently:
   - `mag0`
   - `mag1`
   - `mag5`
   - `mag25`
   - `dom-agi`
   - `dom-tech`
   - plus any explicitly documented exception.
10. The `qwen3.6-plus` mixed-roster variant has zero included runs unless explicitly requested.

### 2.3 Deliverable

```text
analysis/.../data_manifest.csv
analysis/.../data_manifest_summary.md
```

No embeddings, judge calls, or statistical analysis should run until the manifest is reviewed.

---

## 3. Temporal binning

Different experiment families have different durations, so use two compatible temporal schemes.

### 3.1 Fixed first-hour bins

Use for first-hour-comparable analyses:

```text
0–15m
15–30m
30–45m
45–60m
```

Apply to:

- Single-model final runs.
- Mixed-model roster if duration supports first-hour comparison.
- Base model as tool if duration supports first-hour comparison.

### 3.2 Normalized quartiles

Use for combined cross-family comparisons and full-duration obsession analysis:

```text
Q1 = earliest 25% of run time
Q2 = 25–50%
Q3 = 50–75%
Q4 = latest 25%
```

Apply to:

- Obsession prompting as the main temporal scheme.
- All families for the combined early-vs-late comparison.

### 3.3 Primary early-vs-late contrast

For fixed first-hour analysis:

```text
Δ = metric(45–60m) − metric(0–15m)
```

For normalized quartile analysis:

```text
Δ = metric(Q4) − metric(Q1)
```

The report must always state which temporal scheme is used.

---

## 4. Required one-to-one findings-handoff analysis suite

The previous canonical analysis in `../moltbook-findings-handoff` should be treated as the reference pipeline. We should reproduce that analysis structure **one-to-one** for every included family before doing any new combined analysis. The only allowed changes are explicit family-specific adaptations, such as full-duration normalized quartiles for Obsession prompting.

This section is mandatory, not optional. The final analysis should not only compute embeddings/Vendi; it should also recreate the canonical lexical, compression, phrase-attractor, diffusion, and agent-participation analyses for all included families.

### 4.1 Reference scripts and outputs from findings-handoff

The canonical 48 analysis used the following components:

| Reference component | Findings-handoff source | Main output type | What it measures |
|---|---|---|---|
| Canonical data overlay | `findings/emnlp-2026-paper/canonical_data.md` | 48-run manifest | Correct merged/resumed inventory |
| Compression | `scripts/gzip/compute_compression.py` | per-run fixed-bin gzip/bzip2/zlib | byte-level redundancy |
| Lexical diversity | `scripts/analysis_new/diversity_metrics.py` | per-run/bin Distinct-5 and Simpson 1/D | lexical diversity collapse |
| Bin-size-controlled lexical metrics | `scripts/analysis_new/analyze_time_binned_lexical_5gram.py` | Distinct-1..5 raw and subsampled with CIs | sample-size-controlled lexical diversity |
| Distinct-n resumed check | `scripts/analysis_new/distinct_n_resumed.py` | canonical 48 Q4−Q1 summaries | corrected merged/resumed distinct-n deltas |
| Phrase provenance | `scripts/analysis_new/ngram_provenance.py` | top 4/5-gram phrases per run | local phrase attractors, seed overlap, cross-run overlap |
| Phrase diffusion | `scripts/analysis_new/phrase_diffusion.py` | first usage/adoption timelines | spread of dominant phrases across agents |
| Agent participation | `scripts/analysis_new/agent_participation.py` | concentration/adopter tables | whether attractors are collective or dominated by a few agents |
| Semantic/Vendi subset | paper-handoff semantic analysis referenced in `findings.md` | Vendi + MDS for GPT-5 n30 subset | semantic-space narrowing; not full canonical-48 coverage |

### 4.2 Canonical parity check before extending

Before applying the pipeline to the broader set, the `single_model_final` data should first reproduce the canonical inventory shape from findings-handoff:

- 48 total runs.
- GPT-5: n10/n20/n30 × 6 conditions = 18 runs.
- Gemini Flash Lite: n10/n20/n30 × 6 conditions = 18 runs.
- Kimi K2.5: n10 × 6 conditions = 6 runs.
- GLM-5: n10 × 6 conditions = 6 runs.
- non-seed/agent posts only for main metrics.
- time anchored at first agent-authored post.
- fixed first-hour bins for canonical parity: 0–15, 15–30, 30–45, 45–60 minutes.

The parity check should report whether counts match the known corrected canonical findings, including:

- zero empty final bins in the merged canonical export,
- gzip decline approximately 44/48 with mean Δ around -0.0366 if recomputing the same metric,
- Distinct-5 and Simpson summaries consistent with the corrected merged/resumed findings, allowing small implementation differences only if explained.

If the canonical parity check fails, stop and inspect parsing before running the rest.

### 4.3 Apply the same modules to every included family

For each included family — `single_model_final`, `mixed_model_roster`, `base_model_as_tool`, and `obsession_prompting` — run the same analysis modules in the same order:

1. **Run manifest and non-seed loader**
   - Load all posts.
   - Mark seed/system posts.
   - Use non-seed posts for main metrics.
   - Anchor time at the first non-seed/agent post.
   - Record all parsing and exclusion decisions.

2. **Compression analysis**
   - Concatenate non-seed post text within each run × time bin.
   - Compute gzip, bzip2, and zlib compressed-size/raw-size ratios.
   - Compute final−first deltas per run.
   - Report run-level summaries with bootstrap CI and sign test.

3. **Lexical diversity analysis**
   - Compute fixed-window Distinct-5.
   - Compute cumulative Distinct-5.
   - Compute Simpson-style effective diversity.
   - Compute Distinct-1 through Distinct-5 raw and bin-size-controlled/subsampled.
   - Keep per-run × bin rows before aggregation.

4. **Phrase provenance analysis**
   - For each run, identify top 10 4-grams and top 10 5-grams.
   - Check overlap with seed posts for that run/family.
   - Check cross-run top-phrase overlap within the family.
   - Write per-run top phrase tables and phrase-DNA style figures.

5. **Phrase diffusion analysis**
   - For each run, track top-3 5-gram phrases.
   - For each dominant phrase, identify first usage by each agent.
   - Compute adoption count, adoption rate, first/last usage minute, and cumulative adoption curves.

6. **Agent participation analysis**
   - Compute phrase-use concentration by agent.
   - Compute Gini coefficient over all agents and over adopters.
   - Compute top-1 and top-3 agent share of phrase uses.
   - Compute Jaccard overlap among adopters of top phrases.
   - Where metadata exists, summarize adoption by personality/archetype/model assignment.

7. **Semantic embedding / Vendi analysis**
   - Use Qwen3-Embedding-8B for all included families.
   - Compute per-run × time-bin Vendi, mean pairwise cosine, and semantic radius.
   - Use equal-size repeated subsampling for Vendi.
   - Treat MDS/UMAP as visual checks only, not inferential statistics.

8. **Blinded LLM-as-judge analysis**
   - This is an addition beyond the canonical handoff pipeline.
   - Score non-seed posts only.
   - Prompt includes target + previous + semantic-neighbor text after prompt review.
   - No group/model/condition/run/cluster metadata in the prompt.
   - Aggregate post-level judgments to run × time-bin before any family/model/condition summaries.

### 4.4 Family-specific adaptations while preserving the same analysis logic

The analysis should stay one-to-one in logic, but time windows and caveats differ by family:

| Family | Required timing | Notes |
|---|---|---|
| `single_model_final` | fixed first-hour bins; also normalized quartiles for combined comparison | Must pass canonical parity check first |
| `mixed_model_roster` | fixed first-hour bins if supported; normalized quartiles for combined comparison | Report as roster/intervention-style family if few runs |
| `base_model_as_tool` | fixed first-hour bins if supported; normalized quartiles for combined comparison | Exclude all paths containing `ignore` |
| `obsession_prompting` | full-duration normalized quartiles as main; optional fixed first-hour secondary | Do not truncate main analysis to 60 minutes |

For seed-overlap checks, use the seed/system posts belonging to the same run or same experimental seed set where available. Do not use the old canonical seed-file glob blindly for non-canonical families.

### 4.5 One-to-one outputs required per family

Each family report should contain these subfolders/tables so Ayush can compare families directly:

```text
per_family_reports/<family>/
  manifest/
    run_manifest.csv
    inclusion_exclusion_summary.md
  compression/
    compression_run_timebin_metrics.csv
    compression_run_deltas.csv
    compression_summary.md
  lexical_diversity/
    diversity_metrics.csv
    raw_time_bin_metrics.csv
    subsampled_time_bin_metrics.csv
    run_metadata.csv
    lexical_summary.md
  phrase_provenance/
    per_run_top_ngrams.csv
    provenance_summary.json
    phrase_dna_grid.png
  phrase_diffusion/
    first_usage_timeline.csv
    diffusion_summary.json
    per_run_phrases.png
  agent_participation/
    concentration.csv
    phrase_overlap.csv
    adopter_profiles.csv
    participation_summary.json
  semantic_embeddings/
    embedding_run_timebin_metrics.csv
    embedding_run_deltas.csv
    vendi_subsampling_diagnostics.csv
  llm_judge/
    prompt_audit_report.md
    judge_run_timebin_metrics.csv
    judge_run_deltas.csv
```

### 4.6 Combined analysis depends on these one-to-one outputs

The combined report must consume the per-family run-level outputs above. It should not recompute pooled group metrics directly from raw posts except for explicitly labeled descriptive appendices.

---

## 5. Embedding analysis

### 5.1 Embedding model

Use one shared embedding model for measurement consistency:

```text
qwen/qwen3-embedding-8b
```

Embeddings should be cached/resumable locally. Do not commit large regenerable caches.

### 5.2 Post inclusion for embeddings

Primary embedding metrics should use non-seed/agent-authored posts. Seed/system posts may be embedded for diagnostic visualizations, but must not be included in the main collapse metrics unless explicitly labeled.

### 5.3 Per-run metrics

For each run and time bin, compute:

1. **Vendi Score / effective semantic diversity**
   - Interpreted as effective number of semantically distinct items.
   - Lower values indicate semantic narrowing.
2. **Mean pairwise cosine similarity**
   - Higher values indicate tighter semantic clustering.
3. **Semantic radius**
   - Mean cosine distance from bin centroid.
   - Lower values indicate concentration around a narrower centroid.
4. **Post counts**
   - `n_available`
   - `n_used`
   - number of agents contributing.

### 5.4 Vendi Score handling

Vendi Score is sample-size-sensitive. Therefore:

1. Do not report naive Vendi from unequal bin sizes as the sole result.
2. For each run × time bin, use repeated equal-size subsampling.
3. Choose `n_used` transparently:
   - default: minimum nonzero bin size within the run for the relevant time scheme;
   - optionally cap at a maximum for computation, e.g. 400 posts/bin.
4. Repeat subsampling with fixed random seeds, e.g. 100 bootstrap/subsample replicates.
5. Report:
   - mean Vendi across subsamples,
   - subsample standard error or interval,
   - `n_available`,
   - `n_used`,
   - number of replicates.

### 5.5 Per-run deltas

For every run:

```text
Δ_vendi = final_bin_vendi − first_bin_vendi
Δ_cosine = final_bin_mean_pairwise_cosine − first_bin_mean_pairwise_cosine
Δ_radius = final_bin_semantic_radius − first_bin_semantic_radius
```

Interpretation:

- Negative `Δ_vendi` = diversity declined.
- Positive `Δ_cosine` = semantic clustering increased.
- Negative `Δ_radius` = semantic radius shrank.

### 5.6 Family/model/condition summaries

After per-run deltas exist, aggregate over runs by:

- internal family label,
- display family label,
- model family,
- condition,
- scale / agent count,
- roster name where applicable.

Use equal-run weighting by default.

### 5.7 Embedding deliverables

Per-family outputs:

```text
per_family_reports/single_model_final/embedding_run_timebin_metrics.csv
per_family_reports/single_model_final/embedding_run_deltas.csv
per_family_reports/single_model_final/embedding_summary_by_model_condition.csv
...
```

Combined outputs:

```text
combined_report/embedding_run_timebin_metrics.csv
combined_report/embedding_run_deltas.csv
combined_report/embedding_summary_by_family.csv
combined_report/embedding_summary_by_model_condition.csv
```

---

## 6. LLM-as-judge analysis

### 6.1 Judge model

Use one judge model for consistency:

```text
google/gemini-3.1-flash-lite-preview
```

### 6.2 Post inclusion for LLM judge

Use **non-seed posts only**.

Seeds/system posts are experimental inputs, not generated agent discourse. They should not be scored as agent output.

### 6.3 Judge input

The judge may receive:

1. target post title/content,
2. previous anonymized posts from the same run,
3. anonymized semantically-nearby posts.

However, the judge prompt must not include:

- internal family label,
- display family label,
- group,
- model family,
- condition,
- run id,
- run path,
- source dataset,
- folder name,
- cluster id,
- roster name,
- agent model assignment.

The judge should score text only. Metadata is joined locally after scoring.

### 6.4 Pipeline review requirement

Before running all-point judge scoring, review the prompt and sampling/context pipeline manually.

The review should check:

1. No metadata keys are present in the prompt.
2. Natural post text is allowed to contain arbitrary words; that is not metadata leakage.
3. Any control IDs such as `row_uid` are not placed in the model prompt.
4. Semantic-neighbor selection does not attach labels or cluster IDs.
5. Previous-post context does not include author/model/condition metadata.

### 6.5 Judge rubric

The rubric should score post-level collapse indicators, for example:

- `novelty`
- `semantic_repetition`
- `frame_convergence`
- `consensus_conformity`
- `specificity`
- `evidence_grounding`
- `epistemic_caution`
- `template_rigidity`
- `citation_quality`
- `collapse_label`
- `claim_behavior`
- short rationale

The judge output should be JSON only.

### 6.6 LLM-judge aggregation

Even though judge scores are post-level, the statistical summaries must be run-level first:

```text
post-level judge scores
→ run × time-bin mean judge scores
→ run-level final−first deltas
→ family/model/condition summaries over runs
```

Do not report pooled post-level means as the main evidence. Pooled means can be included only as descriptive appendix tables.

### 6.7 LLM-judge deliverables

```text
llm_judge/blind_judge_prompt_template.md
llm_judge/prompt_audit_report.md
llm_judge/post_level_judgments.jsonl       # local/cache; do not commit if large
llm_judge/run_timebin_judge_metrics.csv
llm_judge/run_judge_deltas.csv
llm_judge/summary_by_family.csv
llm_judge/summary_by_model_condition.csv
```

---

## 7. Separate analyses before combined analysis

The analysis must be performed separately for each experimental family before the combined report.

### 7.1 Single-model final runs

Main questions:

1. Within each model/condition/scale, does semantic diversity decline over time?
2. Are declines consistent across models?
3. Does agent count change the strength of narrowing?
4. Are seeded conditions lower-diversity or more rapidly convergent than `mag0`?

Breakdowns:

- model family,
- condition,
- scale / number of agents,
- run,
- agent/author as secondary.

Plots:

- individual run trajectories by model/condition,
- model × condition delta forest plot,
- scale comparison for models with n10/n20/n30 coverage,
- per-run Vendi and cosine delta scatter.

Tables:

- per-run metrics,
- per-run deltas,
- model × condition summary,
- condition summary,
- scale summary.

### 7.2 Mixed-model roster

Main questions:

1. Does a mixed-model roster show the same collapse dynamics as single-model runs?
2. Do particular agents or model-assigned roles dominate the convergence?
3. Is semantic narrowing distributed across agents or driven by one high-volume agent?

Breakdowns:

- roster run,
- condition,
- agent identity,
- agent model/personality assignment if reliable.

Plots:

- roster run trajectories,
- agent contribution / posting volume,
- agent-level semantic centrality or repetition diagnostics,
- comparison against single-model final runs only after per-run metrics exist.

### 7.3 Base model as tool

Main questions:

1. Does the base-model-as-tool setup show semantic narrowing?
2. How does it compare with single-model final runs and mixed-model roster after run-level aggregation?
3. Are results different by base model or condition?

Rules:

- Exclude all paths containing `ignore`.
- Document excluded counts.

Breakdowns:

- base model,
- condition,
- run,
- agent/author if useful.

### 7.4 Obsession prompting

Main questions:

1. Does full-duration obsession prompting show narrowing over normalized time?
2. Does the task maintain or reduce topic diversity compared with other families?
3. Are there agent-specific or prompt-specific attractors?

Rules:

- Use full duration.
- Use normalized quartiles as the main time scheme.

Breakdowns:

- condition/prompt type,
- run,
- agent/author.

Plots:

- quartile trajectories,
- run-level early-vs-late deltas,
- agent participation and repetition diagnostics.

---

## 8. Combined analysis

The combined analysis should only be produced after the four separate family analyses are complete.

### 8.1 Combined comparison units

Compare run-level deltas across:

- `single_model_final`
- `mixed_model_roster`
- `base_model_as_tool`
- `obsession_prompting`

### 8.2 Combined metric tables

For each family and metric:

- `n_runs`
- mean delta
- median delta
- standard deviation
- bootstrap 95% CI over runs
- number of runs declining
- sign test p-value
- optional Wilcoxon signed-rank p-value

### 8.3 Combined plots

Recommended plots:

1. **Run trajectories with family mean overlays**
   - thin lines = individual runs
   - thick line = equal-run-weighted mean
   - ribbon/error bars = bootstrap CI over runs
2. **Delta forest plot**
   - one point per family/model/condition summary
   - CI over runs
3. **Model × condition plot** for single-model final runs
   - actual model names and conditions, not `canonical-48` label
4. **Mixed-model roster comparison**
   - roster as its own experimental family
5. **Obsession prompting quartile plot**
   - full-duration normalized time
6. **MDS/UMAP maps**
   - visual checks only, not main inferential evidence

### 8.4 Explicitly avoid

Avoid main-result claims based on:

- post-pooled group averages,
- UMAP/MDS visual separation alone,
- cluster labels as if they were ground truth,
- unequal-size Vendi without subsampling or explicit caveat,
- judge-score post averages without run-level aggregation.

---

## 9. Statistical reporting

### 9.1 Within-run change

For each run:

```text
Δ = final metric − first metric
```

where `final` and `first` are defined by the relevant time scheme.

### 9.2 Summary over runs

For each group of runs:

- mean Δ,
- median Δ,
- bootstrap 95% CI over runs,
- sign-test count and p-value,
- optional Wilcoxon signed-rank p-value.

### 9.3 Bootstrap rule

Bootstrap should resample runs, not posts.

If there are very few runs in a subgroup, report the point estimate but mark the CI as unstable or omit inferential claims.

### 9.4 Multiple comparisons

If many model × condition comparisons are tested, either:

- apply FDR correction, or
- label those comparisons exploratory.

### 9.5 Mixed-effects model sensitivity

Optionally fit mixed-effects models as sensitivity analyses, e.g.:

```text
metric_delta ~ family + condition + scale + (1 | model_family)
```

or for post-level judge scores:

```text
judge_score ~ time_bin + family + condition + (1 | run) + (1 | agent)
```

But the main reporting should remain transparent run-level deltas unless the model assumptions are carefully checked.

---

## 10. Vendi check against existing findings-handoff analysis

Before using Vendi as a headline metric:

1. Check findings-handoff / paper-handoff outputs for existing Vendi coverage.
2. Determine whether Vendi was computed for:
   - all canonical final runs,
   - only GPT-5 n30,
   - or another subset.
3. If only a subset exists, regenerate per-run Vendi consistently across all included runs.
4. Do not write “canonical Vendi result” unless all canonical single-model final runs have per-run Vendi metrics.

Known from findings-handoff context:

- Vendi is explicitly reported for GPT-5 n30 conditions in the semantic-map section.
- Need verification before claiming full canonical-48 Vendi coverage.

---

## 11. Outputs

Recommended final structure:

```text
analysis/archive-2026-plus-canonical-gemini/
  ANALYSIS_PLAN_FOR_AYUSH.md
  data_manifest.csv
  data_manifest_summary.md

  per_family_reports/
    single_model_final/
      RUN_MANIFEST.md
      EMBEDDING_REPORT.md
      LLM_JUDGE_REPORT.md
      embedding_run_timebin_metrics.csv
      embedding_run_deltas.csv
      judge_run_timebin_metrics.csv
      judge_run_deltas.csv
      figures/

    mixed_model_roster/
      RUN_MANIFEST.md
      EMBEDDING_REPORT.md
      LLM_JUDGE_REPORT.md
      ...

    base_model_as_tool/
      RUN_MANIFEST.md
      EMBEDDING_REPORT.md
      LLM_JUDGE_REPORT.md
      ...

    obsession_prompting/
      RUN_MANIFEST.md
      EMBEDDING_REPORT.md
      LLM_JUDGE_REPORT.md
      ...

  combined_report/
    COMBINED_REPORT.md
    embedding_summary_by_family.csv
    embedding_summary_by_model_condition.csv
    judge_summary_by_family.csv
    judge_summary_by_model_condition.csv
    figures/
```

Large regenerable files should remain ignored:

- embedding caches,
- judge caches,
- NPZ matrices,
- large JSONL prompt/result files if too large for git.

---

## 12. Execution gates

The workflow should stop for review at each gate.

### Gate 1 — Plan

Write this plan file only. No analysis execution.

### Gate 2 — Manifest

Build manifest and exclusion report only.

Review required before embeddings or judge runs.

### Gate 3 — Embeddings

Generate/reuse embeddings with Qwen3-Embedding-8B.

Review row counts and cache coverage.

### Gate 4 — Separate family embedding reports

Produce per-family embedding reports first.

Review before combined report.

### Gate 5 — LLM judge pipeline review

Before scoring all non-seed posts:

- inspect prompt template,
- inspect example prompt inputs,
- run metadata-leak audit,
- approve context policy.

### Gate 6 — LLM judge scoring

Run all non-seed post scoring only after pipeline approval.

### Gate 7 — Combined report

Aggregate run-level metrics across families.

### Gate 8 — Commit/push

Only after review and secret scan.

---

## 13. Current open implementation checklist

Before executing, verify:

- [ ] agokrani canonical export has the expected merged/resumed single-model final runs.
- [ ] canonical model names are parsed correctly.
- [ ] canonical conditions are parsed correctly.
- [ ] frontier/mixed roster runs are included and named `Mixed-model roster`.
- [ ] base-model-as-tool excludes every path containing `ignore`.
- [ ] obsession prompting uses full duration and normalized quartiles.
- [ ] old archive `entropy-collapse` has zero included rows.
- [ ] source/site-citation has zero included rows.
- [ ] seed posts are excluded from LLM judge.
- [ ] run-level aggregation is used for main statistics.
- [ ] one-to-one findings-handoff modules are run for every included family: compression, lexical diversity, bin-size-controlled distinct-n, phrase provenance, phrase diffusion, and agent participation.
- [ ] single-model final runs pass canonical parity checks before extending the pipeline.
- [ ] seed-overlap checks use the correct seed posts for each family, not a hard-coded canonical seed glob.
- [ ] Vendi uses equal-size repeated subsampling.
- [ ] all combined plots show run-level uncertainty, not pooled-post means.

---

## 14. Summary of final confirmed choices

| Decision | Final choice |
|---|---|
| Old archive entropy-collapse | Exclude completely |
| Canonical export | Use agokrani HuggingFace canonical export; already merged/resumed |
| Canonical graph label | Use actual model + condition; do not graph as `canonical-48` |
| Canonical internal family | `single_model_final` |
| Frontier/mixed display | `Mixed-model roster` |
| Base-model display | `Base model as tool` |
| Base-model `ignore` paths | Exclude |
| Obsession display | `Obsession prompting` |
| Obsession duration | Full available duration |
| Obsession time scheme | Normalized quartiles |
| LLM judge posts | Non-seed posts only |
| LLM judge context | Target + previous posts + semantic-neighbor posts, after pipeline review |
| Main statistical unit | Run |
| Combined averaging | Equal-run-weighted with uncertainty; no pooled-post means as main evidence |
