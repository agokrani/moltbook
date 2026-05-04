# Blinded LLM Judge Summary

Judge model: `google/gemini-3.1-flash-lite-preview`

Rubric version: `ayush-blind-all-posts-v1`

Post-level judgments joined after scoring: **50,805 / 50,805** non-seed posts.

Prompts contained target post text, previous anonymized timeline posts, and anonymized semantic-neighbor posts, but no run/group/model/condition/path/source metadata.

## Run-level delta summary

| internal_family_label | scheme | n_runs | delta_collapse_index_mean | delta_collapse_index_ci_low | delta_collapse_index_ci_high | delta_collapse_index_sign_p | delta_novelty_mean | delta_semantic_repetition_mean | delta_specificity_mean | delta_evidence_grounding_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_model_as_tool | fixed_15m | 49 | 0.09188 | -0.0816 | 0.2792 | 0.69 | -0.1072 | 0.1601 | -0.1685 | -0.1371 |
| base_model_as_tool | normalized_quartile | 49 | 0.3063 | 0.1604 | 0.4523 | 0.009399 | -0.09619 | 0.3686 | -0.2226 | -0.1512 |
| mixed_model_roster | fixed_15m | 3 | 0.5471 | 0.3817 | 0.7125 | 0.5 | -0.4797 | 0.551 | -0.2919 | -0.2288 |
| mixed_model_roster | normalized_quartile | 3 | 0.1604 | -0.524 | 0.7236 | 1 | -0.1356 | 0.0949 | 0.04441 | 0.09116 |
| obsession_prompting | normalized_quartile | 15 | 0.0035 | -0.2344 | 0.1769 | 0.146 | -0.00479 | 0.1403 | -0.05476 | -0.1722 |
| single_model_final | fixed_15m | 48 | 0.2903 | 0.224 | 0.356 | 8.363e-12 | -0.3082 | 0.3383 | -0.1447 | -0.1201 |
| single_model_final | normalized_quartile | 48 | 0.2985 | 0.2334 | 0.3629 | 8.363e-12 | -0.3125 | 0.3403 | -0.1627 | -0.1383 |

## Outputs

- `ayush_reanalysis/llm_judge_run_timebin_metrics.csv`
- `ayush_reanalysis/llm_judge_run_deltas.csv`
- `combined_report/llm_judge_summary_by_family.csv`
- `combined_report/llm_judge_label_counts.csv`

Post-level joined judgments remain local/ignored at `ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv`.
