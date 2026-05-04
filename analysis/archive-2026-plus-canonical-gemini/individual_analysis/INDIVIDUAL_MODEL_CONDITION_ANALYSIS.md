# Individual Model and Condition Analysis — Non-Heatmap Version

Generated: 2026-05-04T10:17:34.346681+00:00

## Clarification

- **Embedding model:** one embedding model was used as requested: `qwen/qwen3-embedding-8b`.
- **Generation/model families analyzed:** all model families present in the targeted archive + full canonical-48 corpus were included. This report splits results by those generation model families.
- **Judge model:** one LLM judge model was used for scoring (`google/gemini-3.1-flash-lite-preview`), but the sample spans every generation model family, group, condition, scale/time bin, and all global embedding clusters.

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
| gpt-5 | 45429 | 52 |
| google/gemini-3.1-flash-lite-preview | 36543 | 98 |
| moonshotai/kimi-k2.5 | 7868 | 13 |
| olmo3-32b-instruct | 5650 | 29 |
| gemini-flash-lite | 5173 | 6 |
| z-ai/glm-5 | 3454 | 12 |
| olmo3-32b-base | 2755 | 25 |
| qwen3.5-35b-a3b-base | 1433 | 6 |
| mixed | 807 | 3 |
| qwen3.5-35b-a3b-instruct | 277 | 12 |
| olmo3-32b-think | 244 | 7 |
| nvidia/nemotron-3-super-120b-a12b:free | 221 | 8 |

## Condition counts

| condition | post_rows | runs |
| --- | --- | --- |
| mag0 | 20772 | 50 |
| mag1 | 16030 | 38 |
| mag5 | 18263 | 46 |
| mag25 | 22001 | 52 |
| dom-agi | 16465 | 44 |
| dom-tech | 16323 | 41 |

## Ranked model-level collapse

| model_family | n_posts | n_judged_sample | weighted_collapse_index | weighted_semantic_repetition | weighted_narrative_convergence | weighted_groupthink | weighted_template_rigidity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| olmo3-32b-instruct | 5650 | 96 | 4.424 | 4.435 | 4.826 | 4.571 | 3.863 |
| olmo3-32b-base | 2755 | 97 | 4.380 | 4.213 | 4.675 | 4.436 | 4.198 |
| google/gemini-3.1-flash-lite-preview | 36543 | 590 | 4.256 | 4.345 | 4.783 | 4.437 | 3.460 |
| gpt-5 | 45429 | 736 | 4.185 | 3.911 | 4.570 | 4.128 | 4.133 |
| moonshotai/kimi-k2.5 | 7868 | 192 | 4.042 | 4.003 | 4.647 | 4.291 | 3.227 |
| gemini-flash-lite | 5173 | 96 | 3.918 | 4.048 | 4.823 | 4.180 | 2.623 |
| nvidia/nemotron-3-super-120b-a12b:free | 221 | 28 | 3.781 | 3.845 | 4.190 | 3.712 | 3.378 |
| mixed | 807 | 16 | 3.375 | 3.250 | 4.188 | 3.312 | 2.750 |
| qwen3.5-35b-a3b-base | 1433 | 96 | 3.220 | 3.123 | 3.943 | 3.425 | 2.391 |
| z-ai/glm-5 | 3454 | 192 | 3.016 | 2.938 | 3.852 | 3.108 | 2.164 |
| qwen3.5-35b-a3b-instruct | 277 | 55 | 2.823 | 2.722 | 3.370 | 2.689 | 2.511 |
| olmo3-32b-think | 244 | 71 | 2.568 | 2.405 | 2.647 | 2.067 | 3.153 |

## Ranked condition-level collapse

| condition | n_full_nonseed_posts | n_judged | collapse_index | weighted_semantic_repetition | weighted_narrative_convergence | weighted_groupthink | weighted_template_rigidity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| mag0 | 20767 | 364 | 4.094 | 4.048 | 4.632 | 4.153 | 3.545 |
| mag1 | 16006 | 375 | 4.070 | 3.990 | 4.605 | 4.166 | 3.517 |
| mag5 | 18103 | 375 | 4.234 | 4.176 | 4.679 | 4.300 | 3.781 |
| mag25 | 21051 | 397 | 4.183 | 4.021 | 4.664 | 4.317 | 3.731 |
| dom-agi | 15740 | 379 | 4.141 | 4.036 | 4.601 | 4.151 | 3.774 |
| dom-tech | 15648 | 375 | 4.121 | 4.035 | 4.608 | 4.219 | 3.621 |
