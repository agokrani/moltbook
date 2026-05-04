# Blinded LLM Judge Summary

Judge model: `google/gemini-3.1-flash-lite-preview`

Rubric version: `ayush-blind-all-posts-v1`

Post-level judgments joined after scoring: **49,661 / 49,661** non-seed posts.

Prompts contained target post text, previous anonymized timeline posts, and anonymized semantic-neighbor posts, but no run/group/model/condition/path/source metadata.

## Run-level delta summary

| internal_family_label | scheme | n_runs | delta_collapse_index_mean | delta_collapse_index_ci_low | delta_collapse_index_ci_high | delta_collapse_index_sign_p | delta_novelty_mean | delta_semantic_repetition_mean | delta_specificity_mean | delta_evidence_grounding_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_model_as_tool | fixed_15m | 18 | 0.08481 | -0.05954 | 0.2197 | 0.2379 | -0.06955 | 0.1248 | -0.1246 | -0.08109 |
| base_model_as_tool | normalized_quartile | 18 | 0.0907 | -0.04575 | 0.2221 | 0.2379 | -0.07656 | 0.135 | -0.124 | -0.08925 |
| mixed_model_roster | fixed_15m | 6 | 0.6779 | 0.5832 | 0.7754 | 0.03125 | -0.6351 | 0.7208 | -0.4084 | -0.3601 |
| mixed_model_roster | normalized_quartile | 6 | 0.6577 | 0.5572 | 0.7573 | 0.03125 | -0.6175 | 0.6995 | -0.3921 | -0.3293 |
| obsession_prompting | normalized_quartile | 9 | 0.1315 | -0.07309 | 0.2734 | 0.03906 | -0.1504 | 0.1549 | -0.1709 | -0.1845 |
| single_model_final | fixed_15m | 48 | 0.2903 | 0.224 | 0.356 | 8.363e-12 | -0.3082 | 0.3383 | -0.1447 | -0.1201 |
| single_model_final | normalized_quartile | 48 | 0.2985 | 0.2334 | 0.3629 | 8.363e-12 | -0.3125 | 0.3403 | -0.1627 | -0.1383 |

## Outputs

- `ayush_reanalysis/llm_judge_run_timebin_metrics.csv`
- `ayush_reanalysis/llm_judge_run_deltas.csv`
- `combined_report/llm_judge_summary_by_family.csv`
- `combined_report/llm_judge_label_counts.csv`

Post-level joined judgments remain local/ignored at `ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv`.
