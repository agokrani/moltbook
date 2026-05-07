# Topic-cluster robustness sweep

This sweep reruns unsupervised embedding clustering across multiple topic counts and random seeds.
It tests robustness of embedding-cluster concentration, not validated human topic categories.

k values: `[8, 12, 16, 24]`
random seeds: `[11, 22, 33, 44, 55]`
SVD components: `50`; embedding model: `qwen/qwen3-embedding-8b`.

## Current status

The earlier Ayush topic output used one clustering configuration only: `k=12`, `random_state=42`.
This sweep adds k/seed sensitivity outputs for deciding whether topic metrics are stable enough for main-paper use.

## Canonical fixed-window stability by model

| model | runs | entropy_decline_rate_mean | entropy_decline_cells_ge_75pct | entropy_decline_cells_all_settings | dominant_share_increase_rate_mean | dominant_share_cells_ge_75pct | dominant_share_cells_all_settings | hhi_norm_increase_rate_mean | hhi_norm_cells_ge_75pct | hhi_norm_cells_all_settings |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GPT-5 | 18 | 0.867 | 14 | 11 | 0.689 | 10 | 2 | 0.781 | 13 | 4 |
| Gemini Flash Lite | 18 | 0.897 | 16 | 10 | 0.831 | 14 | 4 | 0.872 | 16 | 7 |
| Kimi K2.5 | 6 | 0.517 | 1 | 1 | 0.358 | 1 | 0 | 0.350 | 1 | 0 |
| GLM-5 | 6 | 0.492 | 2 | 1 | 0.458 | 1 | 0 | 0.442 | 1 | 0 |

## Outputs

- `topic_robustness_run_deltas.csv`: every run × scheme × k × seed delta.
- `topic_robustness_summary_by_model.csv`: model/family summaries by k and seed.
- `canonical_topic_cluster_stability_by_run.csv`: per canonical run stability rates across all k/seed settings.
- `topic_entropy_robustness_matrix.png`: per-run design matrix; cell value is share of k/seed settings with topic entropy decline.
- `dominant_share_robustness_matrix.png`: per-run design matrix; cell value is share of k/seed settings with dominant-topic share increase.
- `hhi_norm_robustness_matrix.png`: per-run design matrix; cell value is share of k/seed settings with normalized HHI/Simpson concentration increase.
- `topic_entropy_mean_delta_by_k_seed_model.png`: diagnostic k×seed mean-delta heatmap by model.
- `dominant_share_mean_delta_by_k_seed_model.png`: diagnostic k×seed mean-delta heatmap by model.
- `hhi_norm_mean_delta_by_k_seed_model.png`: diagnostic k×seed normalized-HHI mean-delta heatmap by model.
- `topic_exemplars.md`: exemplar posts for each topic at each k using the configured exemplar seed.

## Interpretation rule

Use normalized HHI/Simpson concentration as the paper-facing embedding-cluster concentration metric where the relevant cells remain directionally stable across k and seed. Describe it as embedding-cluster concentration unless labels are manually validated.