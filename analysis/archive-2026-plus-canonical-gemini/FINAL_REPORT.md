# Ayush Reanalysis — Final-Run, Mixed-Roster, Base-Tool, and Obsession Experiments

Generated: 2026-05-04T15:12:05+00:00

This report supersedes the older archive-only embedding package. The current scope follows `ANALYSIS_PLAN_FOR_AYUSH.md` and excludes old archive `entropy-collapse`, source/site-citation runs, and base-model paths containing `ignore`.

## Status

- Deterministic/run-level analyses: **complete**.
- Qwen embedding/Vendi analyses: **complete**.
- Blinded LLM-as-judge context generation and audit: **complete**.
- Full blinded LLM-as-judge scoring: **running; not yet included**.

## Included corpus

| family | runs | non_seed_posts |
| --- | --- | --- |
| Base model as tool | 49 | 7,680 |
| Single-model final runs | 48 | 38,490 |
| Obsession prompting | 15 | 3,903 |
| Mixed-model roster | 3 | 732 |

## Exclusions

| exclusion_reason | runs |
| --- | --- |
| old archive entropy-collapse excluded | 94 |
| base-model path contains ignore | 60 |
| source/site-citation excluded | 8 |
| no non-seed/agent posts | 7 |

## Main deterministic findings

All summaries are run-level first: metrics are computed within each run/time bin, converted to within-run last-bin minus first-bin deltas, then summarized over runs.

| family | scheme | n_runs | mean Δ gzip | mean Δ Distinct-5 | mean Δ Simpson effective 5-gram |
| --- | --- | --- | --- | --- | --- |
| Single-model final runs | fixed 15m | 48 | -0.03673 | -0.1017 | -8,253 |
| Single-model final runs | normalized quartiles | 48 | -0.04602 | -0.1162 | -8,463 |
| Base model as tool | fixed 15m | 49 | 0.01907 | 0.01194 | -10,544 |
| Base model as tool | normalized quartiles | 49 | 0.02183 | 0.0115 | -4,815 |
| Mixed-model roster | fixed 15m | 3 | -0.05067 | -0.1701 | -16,808 |
| Mixed-model roster | normalized quartiles | 3 | -0.04497 | -0.1188 | -10,034 |
| Obsession prompting | normalized quartiles | 15 | 0.04622 | 0.007294 | -10,309 |

The canonical single-model final set reproduces the expected entropy-collapse direction: gzip compression ratio, Distinct-5, cumulative Distinct-5, and Simpson-style effective 5-gram diversity all decline strongly over time.

## Main embedding findings

Embedding model: `qwen/qwen3-embedding-8b`. Coverage: 50,805 / 50,805 included non-seed posts; missing embeddings: 0.

| family | scheme | n_runs | mean Δ Vendi | mean Δ pairwise cosine | mean Δ semantic radius |
| --- | --- | --- | --- | --- | --- |
| Single-model final runs | fixed 15m | 48 | -0.7347 | 0.0588 | -0.03949 |
| Single-model final runs | normalized quartiles | 48 | -0.7786 | 0.05944 | -0.0399 |
| Base model as tool | fixed 15m | 49 | -0.6569 | 0.0856 | -0.05742 |
| Base model as tool | normalized quartiles | 49 | -0.6129 | 0.1134 | -0.07091 |
| Mixed-model roster | fixed 15m | 3 | 0.06572 | -0.03557 | 0.0264 |
| Mixed-model roster | normalized quartiles | 3 | 0.1295 | -0.03772 | 0.02663 |
| Obsession prompting | normalized quartiles | 15 | -0.1698 | 0.03533 | -0.01914 |

Single-model final and base-model-as-tool runs show decreasing semantic diversity / increasing semantic concentration by embedding metrics. Mixed-model roster has only three runs, so its positive Vendi direction should be treated as exploratory.

## Blinded LLM-as-judge findings

Full all-post blinded LLM-as-judge scoring is still running and is not included in this checkpoint yet. After it finishes, run `python3 scripts/ayush-blind-llm-judge.py aggregate` and regenerate this report.


## Figures

- `ayush_reanalysis/figures/manifest_included_corpus.png`
- `ayush_reanalysis/figures/delta_gzip_compression_by_family.png`
- `ayush_reanalysis/figures/delta_distinct5_by_family.png`
- `ayush_reanalysis/figures/delta_vendi_by_family.png`
- `ayush_reanalysis/figures/delta_pairwise_cosine_by_family.png`

PDF versions are stored beside each PNG.

## Key artifacts

- Plan: `ANALYSIS_PLAN_FOR_AYUSH.md`
- Manifest: `data_manifest.csv`, `data_manifest_summary.md`
- Main deterministic CSVs: `ayush_reanalysis/deterministic_timebin_metrics.csv`, `ayush_reanalysis/deterministic_run_deltas.csv`
- Embedding CSVs: `ayush_reanalysis/embedding_run_timebin_metrics.csv`, `ayush_reanalysis/embedding_run_deltas.csv`
- Per-family outputs: `per_family_reports/<family>/...`
- Combined summaries: `combined_report/DETERMINISTIC_METRICS_SUMMARY.md`, `combined_report/EMBEDDING_SUMMARY.md`
- Artifact inventory: `ayush_reanalysis/artifact_inventory.csv`
