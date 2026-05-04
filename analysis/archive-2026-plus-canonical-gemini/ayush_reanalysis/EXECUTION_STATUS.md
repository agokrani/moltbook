# Ayush Reanalysis Execution Status

Generated/updated: 2026-05-04

## Completed

- Wrote detailed plan: `ANALYSIS_PLAN_FOR_AYUSH.md`.
- Implemented deterministic/embedding executor: `scripts/ayush-analysis-plan-execute.py`.
- Implemented blinded all-post judge pipeline: `scripts/ayush-blind-llm-judge.py`.
- Built clean manifest with confirmed scope:
  - `single_model_final`: 48 runs / 38,490 non-seed posts
  - `mixed_model_roster`: 3 runs / 732 non-seed posts
  - `base_model_as_tool`: 49 runs / 7,680 non-seed posts
  - `obsession_prompting`: 15 runs / 3,903 non-seed posts
- Excluded:
  - old archive entropy-collapse: 94 runs
  - source/site-citation: 8 runs
  - base-model paths containing `ignore`: 60 runs
  - empty/non-agent obsession runs: 7 runs
- Ran findings-handoff-style one-to-one deterministic metrics:
  - compression
  - lexical diversity / Distinct-1..5
  - bin-size-controlled subsampled Distinct-1..5
  - phrase provenance top 4/5-grams
  - phrase diffusion first usage timelines
  - agent phrase concentration
- Ran embedding/Vendi metrics from cached `qwen/qwen3-embedding-8b` embeddings:
  - 50,805 non-seed posts
  - 0 missing embeddings
  - run-level Vendi, mean cosine, semantic radius deltas
- Generated per-family and combined deterministic/embedding summaries.
- Generated PNG/PDF checkpoint figures under `ayush_reanalysis/figures/`.
- Replaced stale archive-only root `FINAL_REPORT.md` with a current Ayush reanalysis checkpoint report.
- Removed stale archive-only tracked outputs from the staged package:
  - `combined_posts_index.csv`
  - `embedding_report/`
  - `final_report/`
  - `paper_analysis/`
  - stale embedding metadata JSON
- Built blinded judge contexts for all 50,805 non-seed posts:
  - target post text
  - previous same-run posts
  - semantic-neighbor posts from embedding space
  - no metadata in prompt skeleton
- Prompt audit passed for all 50,805 contexts.

## Running in background

Full all-post blinded LLM-as-judge scoring is running against:

`google/gemini-3.1-flash-lite-preview`

Current observed progress: **12,149 / 50,805 judgments cached** (~23.9%).

Files:

- PID: `ayush_reanalysis/llm_judge/judge_all.pid`
- log: `ayush_reanalysis/llm_judge/logs/judge_all.log`
- cache: `ayush_reanalysis/llm_judge/judge_cache.sqlite`

The judge cache/context files are ignored by git and resumable.

## Still pending after judge completes

Run:

```bash
python3 scripts/ayush-blind-llm-judge.py aggregate
```

This will create run-level LLM-judge metrics and deltas from the completed post-level judgments. Then update `FINAL_REPORT.md` and commit/push the final package.
