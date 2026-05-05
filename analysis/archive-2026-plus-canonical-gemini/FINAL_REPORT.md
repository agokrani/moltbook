# Ayush Reanalysis — Final-Run, Mixed-Roster, Base-Tool, and Obsession Experiments

Generated: 2026-05-05T09:27:48+00:00

This report supersedes the older archive-only embedding package. The current scope follows `ANALYSIS_PLAN_FOR_AYUSH.md`: canonical 48 single-model runs, the qwen3.5 frontier mixed roster, and the curated 2026-05-05 base-model/obsession bundle. The qwen3.6 mixed-roster variant is excluded per review.

## Status

- Deterministic/run-level analyses: **complete**.
- Qwen embedding/Vendi analyses: **complete**.
- Blinded LLM-as-judge context generation and audit: **complete**.
- Full blinded LLM-as-judge scoring: **complete and aggregated**.

## Included corpus

| family | runs | non_seed_posts |
| --- | --- | --- |
| Single-model final runs | 48 | 38,490 |
| Base model as tool | 18 | 5,137 |
| Obsession prompting | 9 | 3,845 |
| Mixed-model roster | 6 | 2,189 |

## Exclusions

| exclusion_reason | runs |
| --- | --- |
| qwen3.6 mixed-roster variant excluded per review | 1 |

## Main deterministic findings

All summaries are run-level first: metrics are computed within each run/time bin, converted to within-run last-bin minus first-bin deltas, then summarized over runs.

| family | scheme | n_runs | mean Δ gzip | mean Δ Distinct-5 | mean Δ Simpson effective 5-gram |
| --- | --- | --- | --- | --- | --- |
| Single-model final runs | fixed 15m | 48 | -0.03673 | -0.1017 | -8,253 |
| Single-model final runs | normalized quartiles | 48 | -0.04602 | -0.1162 | -8,463 |
| Base model as tool | fixed 15m | 18 | 0.01528 | 0.01196 | -11,252 |
| Base model as tool | normalized quartiles | 18 | 0.0112 | 0.01016 | -9,774 |
| Mixed-model roster | fixed 15m | 6 | -0.03654 | -0.1324 | -15,683 |
| Mixed-model roster | normalized quartiles | 6 | -0.03784 | -0.1308 | -14,472 |
| Obsession prompting | normalized quartiles | 9 | 0.08024 | 0.0107 | -14,856 |

The canonical single-model final set reproduces the expected entropy-collapse direction: gzip compression ratio, Distinct-5, cumulative Distinct-5, and Simpson-style effective 5-gram diversity all decline strongly over time.

## Main embedding findings

Embedding model: `qwen/qwen3-embedding-8b`. Coverage: 49,661 / 49,661 included non-seed posts; missing embeddings: 0.

| family | scheme | n_runs | mean Δ Vendi | mean Δ pairwise cosine | mean Δ semantic radius |
| --- | --- | --- | --- | --- | --- |
| Single-model final runs | fixed 15m | 48 | -0.7347 | 0.0588 | -0.03949 |
| Single-model final runs | normalized quartiles | 48 | -0.7786 | 0.05944 | -0.0399 |
| Base model as tool | fixed 15m | 18 | -0.7777 | 0.0947 | -0.06526 |
| Base model as tool | normalized quartiles | 18 | -0.7574 | 0.08573 | -0.05996 |
| Mixed-model roster | fixed 15m | 6 | -0.2871 | -0.00957 | 0.007051 |
| Mixed-model roster | normalized quartiles | 6 | -0.247 | -0.01167 | 0.008571 |
| Obsession prompting | normalized quartiles | 9 | -0.1871 | 0.03834 | -0.02072 |

Single-model final and base-model-as-tool runs show decreasing semantic diversity / increasing semantic concentration by embedding metrics. Mixed-model roster now covers six qwen3.5 roster conditions; qwen3.6 remains excluded.

## Embedding-based topical convergence findings

Topics are unsupervised clusters over SVD-reduced Qwen post embeddings. Increasing dominant-topic share / HHI and decreasing topic entropy / effective topics indicate topical convergence. No new API calls are made for this step.

| family | scheme | n_runs | mean Δ dominant topic share | mean Δ topic entropy | mean Δ effective topics | mean Δ topic HHI |
| --- | --- | --- | --- | --- | --- | --- |
| Single-model final runs | fixed 15m | 48 | 0.07371 | -0.1164 | -0.8025 | 0.1017 |
| Single-model final runs | normalized quartiles | 48 | 0.06843 | -0.1108 | -0.7559 | 0.09757 |
| Base model as tool | fixed 15m | 18 | 0.01418 | -0.06817 | -0.1385 | 0.06336 |
| Base model as tool | normalized quartiles | 18 | 0.01562 | -0.06626 | -0.166 | 0.06089 |
| Mixed-model roster | fixed 15m | 6 | -0.04512 | -0.005951 | -0.08511 | -0.02137 |
| Mixed-model roster | normalized quartiles | 6 | -0.05106 | -0.00416 | -0.0471 | -0.02131 |
| Obsession prompting | normalized quartiles | 9 | 0.1014 | -0.09127 | -0.5796 | 0.1087 |

Full topic outputs: `ayush_reanalysis/topic_convergence/TOPIC_CONVERGENCE_SUMMARY.md`, `topic_summary_by_family.csv`, and the topic-convergence PNG/PDF figures.


## Blinded LLM-as-judge findings

The judge outputs below are metadata-blind at prompt time. The model received post text plus anonymized previous/semantic-neighbor posts only; run/group/model/condition/path/source metadata was joined locally after scoring.

| family | scheme | n_runs | mean Δ collapse index | mean Δ novelty | mean Δ semantic repetition | mean Δ specificity |
| --- | --- | --- | --- | --- | --- | --- |
| Single-model final runs | fixed 15m | 48 | 0.2903 | -0.3082 | 0.3383 | -0.1447 |
| Single-model final runs | normalized quartiles | 48 | 0.2985 | -0.3125 | 0.3403 | -0.1627 |
| Base model as tool | fixed 15m | 18 | 0.08481 | -0.06955 | 0.1248 | -0.1246 |
| Base model as tool | normalized quartiles | 18 | 0.0907 | -0.07656 | 0.135 | -0.124 |
| Mixed-model roster | fixed 15m | 6 | 0.6779 | -0.6351 | 0.7208 | -0.4084 |
| Mixed-model roster | normalized quartiles | 6 | 0.6577 | -0.6175 | 0.6995 | -0.3921 |
| Obsession prompting | normalized quartiles | 9 | 0.1315 | -0.1504 | 0.1549 | -0.1709 |

Full judge summaries: `combined_report/LLM_JUDGE_SUMMARY.md`, `combined_report/llm_judge_summary_by_family.csv`.


## Figures

- `ayush_reanalysis/figures/manifest_included_corpus.png`
- `ayush_reanalysis/figures/delta_gzip_compression_by_family.png`
- `ayush_reanalysis/figures/delta_distinct5_by_family.png`
- `ayush_reanalysis/figures/delta_vendi_by_family.png`
- `ayush_reanalysis/figures/delta_pairwise_cosine_by_family.png`
- `ayush_reanalysis/topic_convergence/topic_dominant_share_delta_by_family.png`
- `ayush_reanalysis/topic_convergence/topic_effective_topics_delta_by_family.png`
- `ayush_reanalysis/topic_convergence/topic_entropy_delta_by_family.png`
- `ayush_reanalysis/topic_convergence/topic_dominant_share_trajectories.png`
- `ayush_reanalysis/topic_convergence/topic_effective_topics_trajectories.png`
- `ayush_reanalysis/topic_convergence/topic_late_distribution_heatmap.png`
- `ayush_reanalysis/topic_convergence/embedding_topic_svd_map.png`

PDF versions are stored beside each PNG.

## Key artifacts

- Plan: `ANALYSIS_PLAN_FOR_AYUSH.md`
- Manifest: `data_manifest.csv`, `data_manifest_summary.md`
- Main deterministic CSVs: `ayush_reanalysis/deterministic_timebin_metrics.csv`, `ayush_reanalysis/deterministic_run_deltas.csv`
- Embedding CSVs: `ayush_reanalysis/embedding_run_timebin_metrics.csv`, `ayush_reanalysis/embedding_run_deltas.csv`
- Topical convergence outputs: `ayush_reanalysis/topic_convergence/`
- Per-family outputs: `per_family_reports/<family>/...`
- Combined summaries: `combined_report/DETERMINISTIC_METRICS_SUMMARY.md`, `combined_report/EMBEDDING_SUMMARY.md`
- Artifact inventory: `ayush_reanalysis/artifact_inventory.csv`
