# Individual Model and Condition Analysis — Non-Heatmap Version

Generated: 2026-05-03T17:21:10.413836+00:00

## Clarification

- **Embedding model:** one embedding model was used as requested: `qwen/qwen3-embedding-8b`.
- **Generation/model families analyzed:** all model families present in the targeted archive + canonical Gemini corpus were included. This report splits results by those generation model families.
- **Judge model:** one LLM judge model was used for scoring (`google/gemini-3.1-flash-lite-preview`), but the sample spans every generation model family, group, condition, scale/time bin, and all 48 embedding clusters.

## What changed from the earlier heatmaps

This folder uses lollipop charts, grouped bar charts, and small-multiple profile plots instead of heatmaps.

## Main combined graphs

- `fig_all_models_collapse_lollipop.png` — all generation models, ranked by collapse index.
- `fig_conditions_collapse_lollipop.png` — all conditions, ranked by collapse index.
- `fig_model_condition_collapse_facets.png` — separate mini-graph for each model showing condition collapse.
- `fig_group_condition_collapse_bars.png` — group × condition bars, no heatmap.

## Individual graph folders

- `models/` — one condition-profile graph per generation model.
- `conditions/` — one model/group ranking graph per condition.

## Generation model families included

| model_family | post_rows | runs |
| --- | --- | --- |
| google/gemini-3.1-flash-lite-preview | 36543 | 98 |
| gpt-5 | 25964 | 34 |
| olmo3-32b-instruct | 5650 | 29 |
| gemini-flash-lite | 5173 | 6 |
| moonshotai/kimi-k2.5 | 4150 | 7 |
| olmo3-32b-base | 2755 | 25 |
| z-ai/glm-5 | 1813 | 6 |
| qwen3.5-35b-a3b-base | 1433 | 6 |
| mixed | 807 | 3 |
| qwen3.5-35b-a3b-instruct | 277 | 12 |
| olmo3-32b-think | 244 | 7 |
| nvidia/nemotron-3-super-120b-a12b:free | 221 | 8 |

## Condition counts

| condition | post_rows | runs |
| --- | --- | --- |
| mag0 | 16585 | 45 |
| mag1 | 12135 | 33 |
| mag5 | 14613 | 41 |
| mag25 | 16868 | 47 |
| dom-agi | 12364 | 39 |
| dom-tech | 12465 | 36 |

## Ranked model-level collapse

| model_family | n_posts | n_judged_sample | weighted_collapse_index | weighted_semantic_repetition | weighted_narrative_convergence | weighted_groupthink | weighted_template_rigidity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| olmo3-32b-instruct | 5650 | 96 | 4.424 | 4.435 | 4.826 | 4.571 | 3.863 |
| olmo3-32b-base | 2755 | 96 | 4.412 | 4.244 | 4.709 | 4.469 | 4.227 |
| google/gemini-3.1-flash-lite-preview | 36543 | 596 | 4.229 | 4.311 | 4.754 | 4.398 | 3.454 |
| gpt-5 | 25964 | 449 | 4.090 | 3.807 | 4.503 | 3.986 | 4.063 |
| moonshotai/kimi-k2.5 | 4150 | 96 | 4.046 | 4.003 | 4.640 | 4.306 | 3.232 |
| gemini-flash-lite | 5173 | 96 | 3.886 | 3.974 | 4.810 | 4.155 | 2.607 |
| nvidia/nemotron-3-super-120b-a12b:free | 221 | 28 | 3.777 | 3.991 | 4.262 | 3.730 | 3.124 |
| qwen3.5-35b-a3b-base | 1433 | 96 | 3.220 | 3.123 | 3.943 | 3.425 | 2.391 |
| z-ai/glm-5 | 1813 | 96 | 3.020 | 2.978 | 3.889 | 3.117 | 2.094 |
| mixed | 807 | 16 | 2.938 | 2.750 | 3.625 | 2.938 | 2.438 |
| qwen3.5-35b-a3b-instruct | 277 | 55 | 2.823 | 2.722 | 3.370 | 2.689 | 2.511 |
| olmo3-32b-think | 244 | 71 | 2.568 | 2.405 | 2.647 | 2.067 | 3.153 |

## Ranked condition-level collapse

| condition | n_full_nonseed_posts | n_judged | collapse_index | weighted_semantic_repetition | weighted_narrative_convergence | weighted_groupthink | weighted_template_rigidity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mag0 | 16580 | 287 | 4.049 | 4.049 | 4.589 | 4.117 | 3.440 |
| mag1 | 12116 | 296 | 4.040 | 4.006 | 4.589 | 4.137 | 3.428 |
| mag5 | 14478 | 297 | 4.241 | 4.187 | 4.718 | 4.313 | 3.746 |
| mag25 | 16043 | 317 | 4.137 | 4.027 | 4.659 | 4.281 | 3.580 |
| dom-agi | 11764 | 298 | 4.091 | 4.003 | 4.556 | 4.113 | 3.693 |
| dom-tech | 11915 | 296 | 4.106 | 4.039 | 4.625 | 4.204 | 3.555 |
