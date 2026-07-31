# Analysis package

The scripts in this directory come from the authoritative rebuttal snapshot `7aa442f`, except `build_agent_sessions_1h.py`, which comes from the later provenance commit `2d95dd8` and has a portability fix for the published Hugging Face directory layout.

## Stored outputs

- `agent_sessions_1h.json`: 24 first-hour, top-level agent-text sessions; seeds excluded; SHA-256 locked in the builder.
- `matched_1h_reddit_posts.json`: direct post-to-post human reference; aggregate and pair metrics only, with no Reddit text.
- `temporal_equal_length_results.json`: equal-token Distinct-5 and equal-byte gzip control.
- `five_hour_comparison.csv` and `five_hour_comparison_summary.json`: one-hour GPT-5/Gemini and five-hour GPT-5 comparisons.
- `long_horizon_cumulative.csv` and `long_horizon_summary.json`: eight-cutoff extension through five hours.
- `multijudge_sample_metadata.csv`, `multijudge_post_scores.csv`, `multijudge_pairwise_agreement.csv`, and `multijudge_direction_summary.csv`: the balanced 240-post, three-judge validation.

Deprecated `matched_1h_cleaned.json`, `matched_1h_comparison.json`, and `matched_1h_paper_metrics.json` are not part of the release because they used Reddit comments rather than top-level submissions.

## Rebuild the first-hour sessions

```bash
python3 artifact/data/download_baseline_inputs.py
python3 artifact/analysis/scripts/build_agent_sessions_1h.py \
  --datasets-root artifact/data/cache \
  --resumes-root artifact/data/cache/moltbook-entropy-collapse-resumes
```

The command fails unless the output matches the release SHA-256. `datasets.lock.json` fixes every upstream revision and every required `posts.jsonl` checksum.

## Rebuild length and longer-horizon results

Download the reanalysis export at the revision in `data/datasets.lock.json`, then identify its analysis root (the directory containing `data_manifest.csv` and `ayush_reanalysis/`):

```bash
python3 artifact/analysis/scripts/build_temporal_length_normalization.py \
  --manifest /path/to/analysis-root/data_manifest.csv \
  --post-index /path/to/analysis-root/ayush_reanalysis/post_index.jsonl \
  --output artifact/analysis/results/temporal_equal_length_results.json

python3 artifact/analysis/scripts/build_five_hour_comparison.py \
  --analysis-root /path/to/analysis-root

python3 artifact/analysis/scripts/build_long_horizon_extension.py \
  --analysis-root /path/to/analysis-root
```

The full reanalysis export is not duplicated in Git because it is large. Its run/file manifests and validation summary are included under `data/manifests/`.

## Rebuild multi-judge summaries without API calls

```bash
python3 artifact/analysis/scripts/rebuild_multijudge_summaries.py
```

This deterministically recomputes pairwise weighted agreement, collapse-index correlations, run-level directions, sign tests, and bootstrap intervals from the released 720 post-score rows. Re-running the hosted judges is not required.

## Rebuild the Reddit baseline

Install `zstd`, then run:

```bash
python3 artifact/analysis/scripts/build_reddit_post_baseline.py
```

The script streams `RS_2019-04.zst` from the locked Zenodo source, retains the first 24 complete UTC hours, and writes metrics only. Network transfer is large. `--upstream-checkout` optionally enables the separately pinned robustness implementation.

## Environment

Python 3.11 or newer is recommended. Install plotting/statistics dependencies with:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r artifact/analysis/requirements.txt
```
