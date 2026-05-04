# Paper-Style Embedding and LLM-as-Judge Analysis

Generated: 2026-05-03T17:37:05.486061+00:00

## Scope

This folder reframes the archive + canonical Gemini analysis for the paper narrative rather than dashboard exploration. It uses one shared embedding model, `qwen/qwen3-embedding-8b`, to compare all posts in a common semantic space. It then uses one fixed LLM judge, `google/gemini-3.1-flash-lite-preview`, to score a stratified sample across all generation model families, conditions, groups, scales, time bins, and global embedding clusters.

Important distinction: **one embedding model** and **one judge model** were used for measurement consistency, but **all generation model families** in the corpus are analyzed separately.

## Embedding analysis: semantic narrowing

For each run and 15-minute bin, we compute:

- **Vendi score / effective semantic diversity** from the cosine kernel. Lower values mean fewer effective semantic items.
- **Mean pairwise cosine** within the bin. Higher values mean tighter semantic clustering.
- **Semantic radius** around the bin centroid. Lower values mean tighter concentration.

Across runs with both first and final bins, Vendi score declines in **114/131** run comparisons. The mean Q4−Q1 Vendi change is **-1.394** with 95% bootstrap CI **[-1.637, -1.121]**. Mean pairwise cosine changes by **0.098** with 95% CI **[0.074, 0.121]**.

### Embedding figures

- `fig_embedding_mds_condition_time.png` — paper-style semantic map: same balanced MDS projection colored by condition and by time.
- `fig_embedding_vendi_over_time_by_group.png` — semantic diversity trajectories by archive group.
- `fig_embedding_vendi_over_time_by_condition.png` — semantic diversity trajectories by stimulus condition.
- `fig_embedding_delta_vendi_by_model.png` — early-to-late Vendi deltas by generation model with bootstrap CIs.
- `fig_embedding_delta_vendi_by_condition.png` — early-to-late Vendi deltas by condition.
- `fig_embedding_delta_vendi_by_group.png` — early-to-late Vendi deltas by corpus group.

## LLM-as-judge analysis: collapse form and severity

Collapse index is the mean of semantic repetition, narrative convergence, groupthink, and template rigidity. The raw judged sample has **1,791** posts. Overall collapse index is **3.846**.

### LLM judge figures

- `fig_llm_judge_model_collapse_dotplot.png` — all generation models ranked by judged collapse.
- `fig_llm_judge_condition_collapse_dotplot.png` — all stimulus conditions ranked by judged collapse.
- `fig_llm_judge_model_by_condition_smallmultiples.png` — separate condition plot for each generation model.
- `fig_llm_judge_model_metric_profiles.png` — model-level score profiles across novelty/repetition/convergence/groupthink/template/evidence.
- `fig_llm_judge_collapse_label_stackedbars.png` — qualitative collapse-label distribution by generation model.
- `fig_embedding_delta_vs_llm_judge_collapse.png` — run-level relationship between semantic diversity change and judged collapse.

## Ranked model-level LLM judge table

| model_family | n_judged | collapse_index_mean | semantic_repetition_mean | narrative_convergence_mean | groupthink_mean | template_rigidity_mean | novelty_mean | evidence_grounding_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| olmo3-32b-base | 96 | 4.438 | 4.271 | 4.740 | 4.521 | 4.219 | 1.250 | 1.188 |
| olmo3-32b-instruct | 96 | 4.430 | 4.438 | 4.833 | 4.583 | 3.865 | 1.354 | 1.135 |
| google/gemini-3.1-flash-lite-preview | 596 | 4.066 | 4.121 | 4.614 | 4.238 | 3.292 | 1.691 | 1.371 |
| moonshotai/kimi-k2.5 | 96 | 4.042 | 3.990 | 4.646 | 4.312 | 3.219 | 1.792 | 1.188 |
| gpt-5 | 449 | 3.978 | 3.708 | 4.403 | 3.829 | 3.971 | 2.058 | 1.786 |
| gemini-flash-lite | 96 | 3.943 | 4.031 | 4.833 | 4.240 | 2.667 | 1.833 | 1.260 |
| nvidia/nemotron-3-super-120b-a12b:free | 28 | 3.339 | 3.464 | 3.821 | 3.214 | 2.857 | 1.714 | 1.000 |
| qwen3.5-35b-a3b-base | 96 | 3.172 | 3.073 | 3.896 | 3.354 | 2.365 | 2.562 | 1.948 |
| z-ai/glm-5 | 96 | 3.065 | 3.021 | 3.927 | 3.167 | 2.146 | 2.688 | 1.573 |
| mixed | 16 | 2.938 | 2.750 | 3.625 | 2.938 | 2.438 | 2.750 | 2.312 |
| qwen3.5-35b-a3b-instruct | 55 | 2.695 | 2.618 | 3.218 | 2.527 | 2.418 | 2.218 | 1.545 |
| olmo3-32b-think | 71 | 2.444 | 2.268 | 2.507 | 1.944 | 3.056 | 1.958 | 1.268 |

## Condition-level LLM judge table

| condition | n_judged | collapse_index_mean | semantic_repetition_mean | narrative_convergence_mean | groupthink_mean | template_rigidity_mean |
| --- | --- | --- | --- | --- | --- | --- |
| mag0 | 287 | 3.792 | 3.739 | 4.369 | 3.829 | 3.230 |
| mag1 | 296 | 3.716 | 3.686 | 4.216 | 3.753 | 3.209 |
| mag5 | 297 | 3.895 | 3.801 | 4.394 | 3.936 | 3.448 |
| mag25 | 317 | 3.889 | 3.789 | 4.420 | 3.975 | 3.372 |
| dom-agi | 298 | 3.841 | 3.765 | 4.352 | 3.859 | 3.389 |
| dom-tech | 296 | 3.938 | 3.858 | 4.466 | 4.024 | 3.405 |

## Group-level LLM judge table

| group | n_judged | collapse_index_mean | semantic_repetition_mean | narrative_convergence_mean | groupthink_mean | template_rigidity_mean |
| --- | --- | --- | --- | --- | --- | --- |
| canonical-gemini-flash-lite | 288 | 4.141 | 4.260 | 4.812 | 4.385 | 3.104 |
| entropy-collapse | 803 | 4.019 | 3.951 | 4.549 | 4.096 | 3.478 |
| source-citation | 64 | 4.008 | 3.922 | 4.422 | 3.859 | 3.828 |
| base-model | 510 | 3.507 | 3.402 | 3.967 | 3.529 | 3.129 |
| obsession | 110 | 3.425 | 2.982 | 3.855 | 3.036 | 3.827 |
| frontier/mixed-model | 16 | 2.938 | 2.750 | 3.625 | 2.938 | 2.438 |

## Files generated

PNG/PDF figure pairs generated in this folder:

- `fig_embedding_delta_vendi_by_condition.png` / `fig_embedding_delta_vendi_by_condition.pdf`
- `fig_embedding_delta_vendi_by_group.png` / `fig_embedding_delta_vendi_by_group.pdf`
- `fig_embedding_delta_vendi_by_model.png` / `fig_embedding_delta_vendi_by_model.pdf`
- `fig_embedding_delta_vs_llm_judge_collapse.png` / `fig_embedding_delta_vs_llm_judge_collapse.pdf`
- `fig_embedding_mds_condition_time.png` / `fig_embedding_mds_condition_time.pdf`
- `fig_embedding_vendi_over_time_by_condition.png` / `fig_embedding_vendi_over_time_by_condition.pdf`
- `fig_embedding_vendi_over_time_by_group.png` / `fig_embedding_vendi_over_time_by_group.pdf`
- `fig_llm_judge_collapse_label_stackedbars.png` / `fig_llm_judge_collapse_label_stackedbars.pdf`
- `fig_llm_judge_condition_collapse_dotplot.png` / `fig_llm_judge_condition_collapse_dotplot.pdf`
- `fig_llm_judge_model_by_condition_smallmultiples.png` / `fig_llm_judge_model_by_condition_smallmultiples.pdf`
- `fig_llm_judge_model_collapse_dotplot.png` / `fig_llm_judge_model_collapse_dotplot.pdf`
- `fig_llm_judge_model_metric_profiles.png` / `fig_llm_judge_model_metric_profiles.pdf`

CSV tables:

- `embedding_timebin_metrics.csv`
- `embedding_q4_minus_q1_deltas.csv`
- `embedding_delta_summary_by_group.csv`
- `embedding_delta_summary_by_model.csv`
- `embedding_delta_summary_by_condition.csv`
- `llm_judge_summary_by_model.csv`
- `llm_judge_summary_by_condition.csv`
- `llm_judge_summary_by_group.csv`
- `llm_judge_summary_by_model_condition.csv`
- `llm_judge_summary_by_group_condition.csv`
- `table_llm_judge_model_ranked.csv`
- `table_llm_judge_condition_ranked.csv`
- `table_llm_judge_group_ranked.csv`

## Caveats

- Vendi and pairwise metrics are sampled for large bins (`max_bin_n=400`) for tractability.
- The MDS map is a balanced sample (`n≈4000`), intended as a visual check, not a standalone inferential statistic.
- LLM judge results are sampled, not exhaustive over all posts.
- Small groups such as frontier/mixed-model have wider uncertainty because they have fewer posts and judged examples.
