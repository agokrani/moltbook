# Approved current figure candidates, 2026-05-07

This folder contains the current paper-facing candidates promoted from the 2026-05-06 stepwise plot pass.

The older step folders remain as provenance. This folder is the clean working set for the paper narrative.

## Current files

| File | Source | Use |
|---|---|---|
| `figure_phrase_ledger.excalidraw` | Step 3 Excalidraw rewrite | Qualitative phrase attractor ledger. |
| `figure_phrase_examples.excalidraw` | Step 3 Excalidraw rewrite | Full-post examples of repeated phrases. |
| `figure_distinct5_cumulative_canonical_n10.png/pdf` | Step 2 cumulative trajectories | Main Distinct-5 candidate. Prefer cumulative over fixed-window. |
| `figure_gzip_cumulative_canonical_n10.png/pdf` | Step 2 cumulative trajectories | Main gzip candidate. |
| `figure_llm_collapse_cumulative_canonical_n10.png/pdf` | Step 2 cumulative trajectories | Main LLM-judge candidate. |
| `figure_scale_phrase_adoption.png/pdf` | Step 4 scale phrase adoption | Main scale candidate. |

## Metric decisions

- Distinct-5: use cumulative in the main paper because it best matches the accumulated-feed story and is less noisy than fixed 15-minute windows.
- Gzip: use cumulative for the same reason.
- LLM collapse index: use cumulative to match the feed-level framing used for gzip and Distinct-5. It is a weighted cumulative mean over judged posts up to each cutoff.

## Not promoted for main paper yet

- Fixed-window gzip.
- Fixed-window Distinct-5.
- Fixed-window LLM collapse index.
- Generated matplotlib Step 3 PNG/PDF phrase plots, because the Excalidraw versions replaced them.
