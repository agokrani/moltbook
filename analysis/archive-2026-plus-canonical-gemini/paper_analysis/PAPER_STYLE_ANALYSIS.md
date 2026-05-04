# Paper-Style Embedding and LLM-as-Judge Analysis

Generated: 2026-05-04T10:18:00.260212+00:00

## Scope

This folder reframes the archive + full canonical-48 analysis for the paper narrative rather than dashboard exploration. It uses one shared embedding model, `qwen/qwen3-embedding-8b`, to compare all posts in a common semantic space. It then uses one fixed LLM judge, `google/gemini-3.1-flash-lite-preview`, to score a stratified sample across all generation model families, conditions, groups, scales, time bins, and global embedding clusters.

Important distinction: **one embedding model** and **one judge model** were used for measurement consistency, but **all generation model families** in the corpus are analyzed separately.

## Embedding analysis: semantic narrowing

For each run and 15-minute bin, we compute:

- **Vendi score / effective semantic diversity** from the cosine kernel. Lower values mean fewer effective semantic items.
- **Mean pairwise cosine** within the bin. Higher values mean tighter semantic clustering.
- **Semantic radius** around the bin centroid. Lower values mean tighter concentration.

Across runs with both first and final bins, Vendi score declines in **141/161** run comparisons. The mean Q4−Q1 Vendi change is **-1.250** with 95% bootstrap CI **[-1.471, -1.032]**. Mean pairwise cosine changes by **0.084** with 95% CI **[0.064, 0.107]**.

### Embedding figures

- `fig_embedding_mds_condition_time.png` — paper-style semantic map: same balanced MDS projection colored by condition and by time.
- `fig_embedding_vendi_over_time_by_group.png` — semantic diversity trajectories by archive group.
- `fig_embedding_vendi_over_time_by_condition.png` — semantic diversity trajectories by stimulus condition.
- `fig_embedding_delta_vendi_by_model.png` — early-to-late Vendi deltas by generation model with bootstrap CIs.
- `fig_embedding_delta_vendi_by_condition.png` — early-to-late Vendi deltas by condition.
- `fig_embedding_delta_vendi_by_group.png` — early-to-late Vendi deltas by corpus group.

## LLM-as-judge analysis: collapse form and severity

Collapse index is the mean of semantic repetition, narrative convergence, groupthink, and template rigidity. The raw judged sample has **2,265** posts. Overall collapse index is **3.867**.

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
| olmo3-32b-instruct | 96 | 4.430 | 4.438 | 4.833 | 4.583 | 3.865 | 1.354 | 1.135 |
| olmo3-32b-base | 97 | 4.402 | 4.237 | 4.701 | 4.485 | 4.186 | 1.278 | 1.206 |
| google/gemini-3.1-flash-lite-preview | 590 | 4.080 | 4.136 | 4.629 | 4.263 | 3.293 | 1.663 | 1.383 |
| gpt-5 | 736 | 4.063 | 3.784 | 4.465 | 3.980 | 4.024 | 2.015 | 1.764 |
| moonshotai/kimi-k2.5 | 192 | 4.022 | 3.969 | 4.641 | 4.281 | 3.198 | 1.870 | 1.172 |
| gemini-flash-lite | 96 | 3.956 | 4.094 | 4.833 | 4.240 | 2.656 | 1.771 | 1.208 |
| mixed | 16 | 3.375 | 3.250 | 4.188 | 3.312 | 2.750 | 2.438 | 2.188 |
| nvidia/nemotron-3-super-120b-a12b:free | 28 | 3.330 | 3.393 | 3.750 | 3.179 | 3.000 | 1.643 | 1.036 |
| qwen3.5-35b-a3b-base | 96 | 3.172 | 3.073 | 3.896 | 3.354 | 2.365 | 2.562 | 1.948 |
| z-ai/glm-5 | 192 | 3.035 | 2.964 | 3.870 | 3.130 | 2.177 | 2.729 | 1.578 |
| qwen3.5-35b-a3b-instruct | 55 | 2.695 | 2.618 | 3.218 | 2.527 | 2.418 | 2.218 | 1.545 |
| olmo3-32b-think | 71 | 2.444 | 2.268 | 2.507 | 1.944 | 3.056 | 1.958 | 1.268 |

## Condition-level LLM judge table

| condition | n_judged | collapse_index_mean | semantic_repetition_mean | narrative_convergence_mean | groupthink_mean | template_rigidity_mean |
| --- | --- | --- | --- | --- | --- | --- |
| mag0 | 364 | 3.795 | 3.712 | 4.371 | 3.835 | 3.261 |
| mag1 | 375 | 3.755 | 3.675 | 4.283 | 3.808 | 3.253 |
| mag5 | 375 | 3.942 | 3.845 | 4.416 | 3.997 | 3.509 |
| mag25 | 397 | 3.911 | 3.771 | 4.428 | 4.010 | 3.436 |
| dom-agi | 379 | 3.856 | 3.747 | 4.364 | 3.858 | 3.456 |
| dom-tech | 375 | 3.937 | 3.853 | 4.456 | 4.035 | 3.405 |

## Group-level LLM judge table

| group | n_judged | collapse_index_mean | semantic_repetition_mean | narrative_convergence_mean | groupthink_mean | template_rigidity_mean |
| --- | --- | --- | --- | --- | --- | --- |
| canonical-48 | 768 | 4.037 | 3.975 | 4.616 | 4.176 | 3.383 |
| entropy-collapse | 796 | 4.029 | 3.959 | 4.546 | 4.121 | 3.491 |
| source-citation | 64 | 3.840 | 3.625 | 4.250 | 3.688 | 3.797 |
| base-model | 511 | 3.502 | 3.397 | 3.961 | 3.524 | 3.125 |
| frontier/mixed-model | 16 | 3.375 | 3.250 | 4.188 | 3.312 | 2.750 |
| obsession | 110 | 3.282 | 2.809 | 3.718 | 2.845 | 3.755 |

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
