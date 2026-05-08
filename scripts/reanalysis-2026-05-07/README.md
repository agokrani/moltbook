# Reanalysis scripts, 2026-05-07

This folder is the current clean script provenance folder for the EMNLP 2026 reanalysis narrative.

It was copied from `scripts/reanalysis-2026-05-06/` after the first approved figure candidates were identified.

## Scripts

| Script | Purpose | Current paper use |
|---|---|---|
| `common.py` | Shared paths, labels, colors, metric metadata | Used by all scripts in this folder. |
| `step01_canonical_n10_trajectories.py` | Fixed 15-minute canonical 10-agent trajectories | Source for approved LLM collapse figure. |
| `step02_canonical_n10_trajectories_cumulative.py` | Cumulative canonical 10-agent trajectories | Source for approved gzip and Distinct-5 figures. |
| `step03_canonical_n10_nltk_phrase_repetition.py` | NLTK 5-token phrase repetition audit | Source data for the Excalidraw qualitative diagrams. |

## Approved plot folder

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/
```

## Important note

The older 2026-05-06 scripts and plots are retained as provenance. The 2026-05-07 folder is the current working set for the paper narrative.
