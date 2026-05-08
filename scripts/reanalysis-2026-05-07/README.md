# Reanalysis scripts, 2026-05-07

This folder is the current clean script provenance folder for the EMNLP 2026 reanalysis narrative.

It was copied from `scripts/reanalysis-2026-05-06/` after the first approved figure candidates were identified.

## Scripts

| Script | Purpose | Current paper use |
|---|---|---|
| `common.py` | Shared paths, labels, colors, metric metadata | Used by all scripts in this folder. |
| `step01_canonical_n10_trajectories.py` | Fixed 15-minute canonical 10-agent trajectories | Source for approved LLM collapse figure. |
| `step02_canonical_n10_trajectories_cumulative.py` | Cumulative canonical 10-agent trajectories | Source for approved gzip and Distinct-5 figures. |
| `step03_canonical_n10_nltk_phrase_repetition.py` | NLTK 5-token phrase repetition audit | Source data for the Excalidraw qualitative diagrams. |
| `step04_scale_phrase_adoption.py` | Scale phrase-adoption comparison | Source for approved scale figure. |
| `step05_phrase_cluster_concentration_examples.py` | Phrase plus embedding-neighborhood concentration examples | Candidate support for semantic anchoring. |
| `step06_social_forms_typology.py` | Social-form typology table | Source for approved typology table. |
| `step07_exact_ngram_conservatism.py` | Exact n-gram conservatism audit | Candidate limitation/mechanism table. |
| `step08_intervention_probe_llm.py` | Earlier intervention phrase-adoption scorecard | Superseded candidate. |
| `step09_intervention_cumulative_metrics.py` | Earlier intervention cohort-median cumulative metrics | Superseded candidate. |
| `step10_intervention_selected_single_runs.py` | Selected one-hour mag25 single-run comparison | Current mag25 intervention candidate. |
| `step11_intervention_selected_first_hour.py` | Selected first-hour comparison for mag0, mag25, and dom-agi | Prepared for rerun when first-hour LLM data are available. |

## First-hour LLM data needed for Step 11

Step 11 is ready, but the final LLM panel should use actual first-hour LLM judgments, not normalized full-run quartiles.

### Selected runs

Use these exact runs:

| Condition | Line | Run UID | Expected first-hour non-seed posts |
|---|---|---|---:|
| `mag0` | Canonical GPT-5 | `52cbe1b58dae376873d521996f9f08f26579623f` | 480 |
| `mag0` | Qwen base tool | `2ec295c49e9fc76a684c9a5e7fba4475d07aa444` | 211 |
| `mag0` | Mixed-model roster | `414de5708c19ec70bf042d934ff00dcab6a86d15` | 388 |
| `mag0` | Obsession GPT-5, first hour of 5h run | `329e6d908c55bed5cac56f80110982ca7a35521b` | 251 |
| `mag25` | Canonical GPT-5 | `6d3e2805af6653babf2fedb85ca20790cd830d58` | 346 |
| `mag25` | Qwen base tool | `5da5a08d776acf648cf486d44e05466a27a378de` | 270 |
| `mag25` | Mixed-model roster | `d055f0cea2ba847f5466e52b06efe723b94eaf85` | 337 |
| `mag25` | Obsession GPT-5, 1h run | `0e1a75b82e3e1c9395f6955b14174d7d7baa76f3` | 225 |
| `dom-agi` | Canonical GPT-5 | `5a3139019e30ef5344c4f09f69968cf1d93292a0` | 464 |
| `dom-agi` | Qwen base tool | `356e5ccaff59febc37a3e2d77af06ee9124f1174` | 277 |
| `dom-agi` | Mixed-model roster | `fc9ac31f2cddf9fe833f67dd50aec10f4c098072` | 421 |
| `dom-agi` | Obsession GPT-5, first hour of 5h run | `a4205cf68c020cde9babaeb76661e33cc86191e8` | 373 |

### Rows to score

Start from:

```text
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/post_index.csv
```

Filter rows as follows:

```text
run_uid is one of the selected run UIDs above
is_seed == false
n_agents == 10
0 <= minutes_elapsed <= 60
```

Do not use normalized quartiles for this comparison. The bins must be actual elapsed minutes:

```text
0-15m, 15-30m, 30-45m, 45-60m
```

### LLM judging requirements

Use the same blinded rubric as the current LLM collapse index:

```text
rubric_version = ayush-blind-all-posts-v1
judge model = google/gemini-3.1-flash-lite-preview
```

Prompts must stay blinded. Do not include condition, model, family, run ID, source path, or roster labels in the prompt. The prompt may include the target post text, previous anonymized posts from the same timeline, and anonymized semantic neighbors.

### Output format for Step 11

Preferred row-level CSV columns:

```text
run_uid, record_id, minutes_elapsed, is_seed, collapse_index
```

Optional but useful columns:

```text
condition, run_id, model_display, internal_family_label, judge_model, rubric_version
```

Step 11 also accepts a time-bin CSV with:

```text
run_uid, bin_label, collapse_index, n_judged
```

where `bin_label` is one of:

```text
0-15m, 15-30m, 30-45m, 45-60m
```

### Run Step 11 after LLM data exists

```bash
python3 scripts/reanalysis-2026-05-07/step11_intervention_selected_first_hour.py \
  --llm-file path/to/first_hour_llm_judge_results.csv \
  --llm-mode auto
```

For a text-only preview without the LLM panel:

```bash
python3 scripts/reanalysis-2026-05-07/step11_intervention_selected_first_hour.py --text-only
```

## Approved plot folder

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/
```

## Important note

The older 2026-05-06 scripts and plots are retained as provenance. The 2026-05-07 folder is the current working set for the paper narrative.
