# Paper-Style Embedding Analysis

Generated: 2026-05-04T10:53:35.126705+00:00

## Scope

This folder reframes the archive analysis for the paper narrative. It uses one shared embedding model, `qwen/qwen3-embedding-8b`, to compare all posts in a common semantic space. The cleaned main corpus includes only the archive groups `base-model`, `entropy-collapse`, and `obsession`.

Excluded from the main package by design:

- `source-citation` / site-citation smoke runs
- `frontier/mixed-model` roster/mixed runs
- `canonical-48` / canonical Gemini comparison runs

## Why LLM-as-a-judge is excluded

LLM-as-a-judge outputs are **not used** in this cleaned package. Earlier judge prompts/context could expose group/source cues through context metadata, so those results are removed from the review package rather than reported. This package is embedding-only.

## Embedding analysis: semantic narrowing

For each run and 15-minute bin, we compute:

- **Vendi score / effective semantic diversity** from the cosine kernel. Lower values mean fewer effective semantic items.
- **Mean pairwise cosine** within the bin. Higher values mean tighter semantic clustering.
- **Semantic radius** around the bin centroid. Lower values mean tighter concentration.

Across runs with both first and final bins, Vendi score declines in **92/107** run comparisons. The mean Q4−Q1 Vendi change is **-1.423** with 95% bootstrap CI **[-1.719, -1.111]**. Mean pairwise cosine changes by **0.103** with 95% CI **[0.076, 0.133]**. Mean semantic radius changes by **-0.075** with 95% CI **[-0.095, -0.057]**.

## Embedding figures

- `fig_embedding_mds_condition_time.png` — paper-style semantic map: same balanced MDS projection colored by condition and by time.
- `fig_embedding_vendi_over_time_by_group.png` — semantic diversity trajectories by archive group.
- `fig_embedding_vendi_over_time_by_condition.png` — semantic diversity trajectories by stimulus condition.
- `fig_embedding_delta_vendi_by_model.png` — early-to-late Vendi deltas by generation model with bootstrap CIs.
- `fig_embedding_delta_vendi_by_condition.png` — early-to-late Vendi deltas by condition.
- `fig_embedding_delta_vendi_by_group.png` — early-to-late Vendi deltas by corpus group.

## CSV tables

- `embedding_timebin_metrics.csv`
- `embedding_q4_minus_q1_deltas.csv`
- `embedding_delta_summary_by_group.csv`
- `embedding_delta_summary_by_model.csv`
- `embedding_delta_summary_by_condition.csv`
- `embedding_mds_balanced_sample.csv`

## Files generated

PNG/PDF figure pairs generated in this folder:

- `fig_embedding_delta_vendi_by_condition.png` / `fig_embedding_delta_vendi_by_condition.pdf`
- `fig_embedding_delta_vendi_by_group.png` / `fig_embedding_delta_vendi_by_group.pdf`
- `fig_embedding_delta_vendi_by_model.png` / `fig_embedding_delta_vendi_by_model.pdf`
- `fig_embedding_mds_condition_time.png` / `fig_embedding_mds_condition_time.pdf`
- `fig_embedding_vendi_over_time_by_condition.png` / `fig_embedding_vendi_over_time_by_condition.pdf`
- `fig_embedding_vendi_over_time_by_group.png` / `fig_embedding_vendi_over_time_by_group.pdf`

## Caveats

- Vendi and pairwise metrics are sampled for large bins (`max_bin_n=400`) for tractability.
- The MDS map is a balanced sample (`n≈4000`), intended as a visual check, not a standalone inferential statistic.
- This is archive-main-only: source-citation, frontier/mixed, and canonical comparison runs are intentionally excluded.
