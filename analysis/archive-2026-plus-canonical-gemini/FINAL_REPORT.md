# Ayush Reanalysis — Deterministic + Embedding Checkpoint

Generated: 2026-05-04

This report supersedes the older archive-only embedding package. The current scope follows `ANALYSIS_PLAN_FOR_AYUSH.md` and excludes old archive `entropy-collapse`, source/site-citation runs, and base-model paths containing `ignore`.

## Status

- Deterministic/run-level analyses: **complete**.
- Qwen embedding/Vendi analyses: **complete**.
- Blinded LLM-as-judge context generation and audit: **complete**.
- Full all-post LLM-as-judge scoring: **running in background**, not yet included below.

## Included corpus

| family | runs | non-seed posts |
| --- | ---: | ---: |
| Single-model final runs (`single_model_final`) | 48 | 38,490 |
| Base model as tool (`base_model_as_tool`) | 49 | 7,680 |
| Mixed-model roster (`mixed_model_roster`) | 3 | 732 |
| Obsession prompting (`obsession_prompting`) | 15 | 3,903 |

Excluded runs: 94 old archive entropy-collapse, 8 source/site-citation, 60 base-model `ignore`, and 7 runs with no usable non-seed/agent posts.

## Main deterministic findings so far

All summaries are run-level first: metrics are computed within each run/time bin, converted to within-run last-bin minus first-bin deltas, then summarized over runs.

| family | scheme | mean Δ gzip compression | mean Δ Distinct-5 | mean Δ Simpson effective 5-gram |
| --- | --- | ---: | ---: | ---: |
| single_model_final | fixed 15m | -0.0367 | -0.1017 | -8,253 |
| single_model_final | normalized quartiles | -0.0460 | -0.1162 | -8,463 |
| base_model_as_tool | fixed 15m | +0.0191 | +0.0119 | -10,544 |
| base_model_as_tool | normalized quartiles | +0.0218 | +0.0115 | -4,815 |
| mixed_model_roster | fixed 15m | -0.0507 | -0.1701 | -16,808 |
| mixed_model_roster | normalized quartiles | -0.0450 | -0.1188 | -10,034 |
| obsession_prompting | normalized quartiles | +0.0462 | +0.0073 | -10,309 |

The canonical single-model final set reproduces the expected entropy-collapse direction: gzip compression ratio, Distinct-5, cumulative Distinct-5, and Simpson-style effective 5-gram diversity all decline strongly over time.

## Main embedding findings so far

Embedding model: `qwen/qwen3-embedding-8b`. Coverage: 50,805 / 50,805 included non-seed posts; missing embeddings: 0.

| family | scheme | mean Δ Vendi | mean Δ pairwise cosine | mean Δ semantic radius |
| --- | --- | ---: | ---: | ---: |
| single_model_final | fixed 15m | -0.735 | +0.0588 | -0.0395 |
| single_model_final | normalized quartiles | -0.779 | +0.0594 | -0.0399 |
| base_model_as_tool | fixed 15m | -0.657 | +0.0856 | -0.0574 |
| base_model_as_tool | normalized quartiles | -0.613 | +0.1134 | -0.0709 |
| mixed_model_roster | fixed 15m | +0.0657 | -0.0356 | +0.0264 |
| mixed_model_roster | normalized quartiles | +0.1295 | -0.0377 | +0.0266 |
| obsession_prompting | normalized quartiles | -0.170 | +0.0353 | -0.0191 |

Single-model final and base-model-as-tool runs show decreasing semantic diversity / increasing semantic concentration by embedding metrics. Mixed-model roster has only three runs, so its positive Vendi direction should be treated as exploratory.

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

## Pending final step

After the blinded judge completes, run:

```bash
python3 scripts/ayush-blind-llm-judge.py aggregate
```

Then update this report with LLM-judge run-level aggregate deltas.
