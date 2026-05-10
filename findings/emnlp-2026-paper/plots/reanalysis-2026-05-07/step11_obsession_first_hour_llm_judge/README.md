# Step 11: obsession first-hour LLM-judge check

This pass fixes the obsession-duration issue by analyzing only minutes `0--60` for every GPT-5 obsession run.
The 5h runs are truncated to their first hour; the true 1h run is used as-is.
Physical runs are grouped by `run_uid` and `source_path`, not by `run_id`, because `obs-mag25-n10-run01-gpt-5-20260418` is reused by both `obs-mag25-1h` and `obs-mag25-5h-run02`.

No new LLM calls were needed: the existing blinded judge file already contains scores for every first-hour GPT-5 obsession post.

## Outputs

- `obsession_first_hour_llm_bins.csv`: fixed 15-minute collapse/component means.
- `obsession_first_hour_llm_run_summary.csv`: one row per physical run.
- `obsession_first_hour_llm_condition_summary.csv`: condition-level comparison with canonical GPT-5 n10 baselines.
- `obsession_first_hour_llm_judge.png/pdf`: trajectory and delta figure.

## Summary

- GPT-5 obsession physical runs analyzed: `8`.
- First-hour judge coverage: `8/8` runs have judged posts equal to post-index posts.
- Positive first-hour LLM-collapse delta: `7/8` obsession runs.
- Median obsession delta, 45--60m minus 0--15m: `+0.159`.

## Condition-level deltas

| Condition | Baseline runs | Obsession runs | Baseline delta | Obsession delta | Obs - baseline |
|---|---:|---:|---:|---:|---:|
| Empty | 1 | 1 | +0.241 | +0.175 | -0.065 |
| 1 consp. | 1 | 1 | +0.019 | +0.050 | +0.031 |
| 5 consp. | 1 | 1 | +0.407 | -0.172 | -0.578 |
| 25 consp. | 1 | 3 | +0.243 | +0.161 | -0.082 |
| AGI | 1 | 1 | +0.183 | +0.184 | +0.001 |
| Tech | 1 | 1 | +0.374 | +0.156 | -0.217 |
