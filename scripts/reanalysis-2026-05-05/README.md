# Reanalysis 2026-05-05 scripts

Scripts for paper-facing plots and tables based on the cleaned reanalysis bundle at:

```text
data/reanalysis-2026-05-05/
```

Outputs are written to:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/
```

The readable findings note is:

```text
findings/emnlp-2026-paper/findings-reanalysis-2026-05-05.md
```

## Run all

```bash
scripts/reanalysis-2026-05-05/run_all.sh
```

This runs topic robustness, validates inputs, rebuilds all plots, and writes the stats tables.

## Main scripts

```text
common.py                              Shared constants, paths, labels, metrics, and helpers
validate_reanalysis_bundle.py          Input validation
build_topic_robustness.py              k and seed sweep for embedding-cluster concentration
build_canonical_design_plots.py        Canonical 48 model x condition x scale matrices
build_canonical_trajectory_plots.py    Diagnostic time trajectories
build_scale_paired_plots.py            GPT-5 and Gemini n10/n20/n30 paired scale plots
build_condition_vs_empty_plots.py      Seed condition versus empty-feed matched plots
build_n10_comparison_plots.py          Matched 10-agent model and roster matrices
build_mixed_roster_plots.py            Mixed roster versus homogeneous n10 plots
build_obsession_matched_plots.py       Obsession prompting versus GPT-5 n10 plots
build_stats_tables.py                  Run-level statistical tables
external-scripts.md                    Provenance for bundled Ayush scripts
```

## Topic robustness sweep

```bash
python3 scripts/reanalysis-2026-05-05/build_topic_robustness.py
```

Inputs:

```text
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/embeddings/qwen-qwen3-embedding-8b-current-included-unique.npz
data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/post_index.csv
```

Default sweep:

- k values: `8,12,16,24`
- KMeans seeds: `11,22,33,44,55`
- SVD components: `50`

Primary paper-facing topic/cluster metric:

```text
normalized HHI/Simpson concentration = (sum_j p_j^2 - 1/k) / (1 - 1/k)
```

where `p_j` is the share of posts in embedding cluster `j`. Positive late-minus-early deltas mean concentration into fewer embedding clusters.
