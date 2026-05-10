# Step 12: fresh OpenRouter judge for obsession first hour

This is a fresh OpenRouter LLM-as-judge pass over the corrected GPT-5 obsession first-hour set.
The judge model is `google/gemini-3.1-flash-lite-preview`; rubric version is `ayush-blind-all-posts-v1`.
All 5h obsession runs are truncated to minutes `0--60`; the true 1h run is used as-is.
Physical runs are keyed by `run_uid + source_path`, not by `run_id`.

## Outputs

- `fresh_openrouter_blind_judge_results_with_metadata.csv`: row-level fresh judgments joined with metadata.
- `obsession_first_hour_openrouter_bins.csv`: fixed 15-minute collapse/component means.
- `obsession_first_hour_openrouter_run_summary.csv`: one row per physical run.
- `obsession_first_hour_openrouter_condition_summary.csv`: comparison to canonical GPT-5 n10 baseline.
- `obsession_first_hour_openrouter_judge.png/pdf`: paper-facing diagnostic figure.

## Summary

- Fresh judged first-hour posts: `1920`.
- GPT-5 obsession physical runs analyzed: `8`.
- First-hour judge coverage: `8/8` runs have judged posts equal to post-index posts.
- Positive first-hour LLM-collapse delta: `8/8` obsession runs.
- Median fresh obsession delta, 45--60m minus 0--15m: `+0.056`.

## Condition-level deltas

| Condition | Baseline runs | Fresh obsession runs | Baseline delta | Fresh obsession delta | Obs - baseline |
|---|---:|---:|---:|---:|---:|
| Empty | 1 | 1 | +0.241 | +0.110 | -0.131 |
| 1 consp. | 1 | 1 | +0.019 | +0.022 | +0.003 |
| 5 consp. | 1 | 1 | +0.407 | +0.035 | -0.371 |
| 25 consp. | 1 | 3 | +0.243 | +0.056 | -0.187 |
| AGI | 1 | 1 | +0.183 | +0.055 | -0.128 |
| Tech | 1 | 1 | +0.374 | +0.117 | -0.257 |
