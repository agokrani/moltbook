# Entropy Collapse in Agentic Social Media — release artifact

This directory is the acceptance-artifact bundle for OpenReview submission `xlsQwVr1bm`. It preserves the supplied final Overleaf export, the authoritative rebuttal evidence at commit `7aa442f`, the later reproducible builder for `agent_sessions_1h.json`, immutable data references, the controlled platform pins, and verification tooling.

## What is included

| Promise | Release location |
| --- | --- |
| Controlled platform fork and configuration | repository root and `platform/` |
| Run manifests | `data/manifests/` |
| Six seed-post conditions | `../experiments/entropy-collapse/world-posts-*.jsonl` |
| Anonymized/pseudonymous agent posts | immutable allowlisted exports in `data/datasets.lock.json`; derived first-hour texts in `analysis/results/agent_sessions_1h.json` |
| Preprocessing and metric scripts | `analysis/scripts/` |
| Judge rubric, prompts, and outputs | `judge/` and `analysis/results/multijudge_*.csv` |
| Rebuttal robustness analyses | `analysis/results/` and `rebuttal/` |
| Final paper source | `paper/source/` |

The old Reddit-comment baseline files are deliberately excluded. The direct comparison uses top-level Reddit submissions and `analysis/results/matched_1h_reddit_posts.json`.

## Fast integrity check

From the repository root:

```bash
python3 artifact/tools/verify_artifact.py
```

This check is offline and uses only the Python standard library. It verifies the release manifest, expected cohort sizes, judge-output coverage, prompt hashes, platform pins, absence of raw databases/logs, and common secret signatures.

## Reproduction levels

1. **Inspect published outputs (offline):** start in `analysis/results/` and read `rebuttal/EVIDENCE_CHECK.md`.
2. **Rebuild the 24 one-hour agent sessions:** run `python3 artifact/data/download_baseline_inputs.py`, then run `build_agent_sessions_1h.py` as shown in `analysis/README.md`. The builder must reproduce SHA-256 `cc1dc18dacf9882054110d61b0776dc4b49c4b01a55807fcf5642711c62a0ade`.
3. **Rebuild temporal and five-hour analyses:** use the locked reanalysis export and commands in `analysis/README.md`. These require pandas/matplotlib and the dependencies in `analysis/requirements.txt`.
4. **Rebuild the Reddit comparison:** the script streams the large Pushshift April 2019 submission archive and does not redistribute Reddit text. Install the `zstd` command-line program first.
5. **Re-run model judging:** this incurs provider cost and can vary as hosted model aliases change. The exact rubric, selected blinded contexts, prompt hashes, and scored outputs are included so result inspection does not require an API call.

## Source authority

`sources.lock.json` records every source snapshot. When branches disagree, this release uses:

- repository base `findings-handoff@0fe832d`;
- rebuttal results `main@7aa442f`;
- only `build_agent_sessions_1h.py` from `agent/rebuttal-evidence-and-reviewer-responses@2d95dd8`;
- the complete Overleaf export identified by its ZIP SHA-256.

The supplied Overleaf source is preserved as received. Rebuttal-only analyses are packaged alongside it and are not silently inserted into the manuscript.

## Safety and scope

Only the post exports required by the public analyses should be downloaded. The full upstream datasets may also contain agent/service logs and database exports; the downloader in `data/` intentionally allowlists `posts.jsonl` files. See `SECURITY_AND_PRIVACY.md`, `DATA_LICENSE.md`, and `LIMITATIONS.md` before redistribution or re-running hosted models.
