# Canonical data inventory

Environment note: this cleanup was performed on Aman's MacBook in `~/Documents/git/moltbook`, on the `findings-handoff` working branch/context.

The source-data mismatch has been resolved by using the local canonical `data/` inventory below for paper analyses.

## Canonical local data paths

| Dataset | Role | Runs |
|---|---|---:|
| `data/moltbook-entropy-collapse-v2/` | GPT-5 n10 run04 set | 6 |
| `data/moltbook-entropy-collapse-20agents/` | GPT-5 n20 | 6 |
| `data/moltbook-entropy-collapse-30agents/` | GPT-5 n30 | 6 |
| `data/moltbook-entropy-collapse-gemini-flash-lite/` | Gemini n10/n20/n30 | 18 |
| `data/moltbook-entropy-collapse-kimi-k2.5/` | Kimi n10 | 6 |
| `data/moltbook-entropy-collapse-glm-5/` | GLM-5 n10 | 6 |

Total: **48 canonical runs**.

## Current canonical scripts

These scripts now read from the canonical `data/` paths and filter runs to the first 60 minutes:

- `scripts/gzip/compute_compression.py`
- `scripts/analyze-shannon-entropy-canonical.py`

## Other analysis sources used in the paper draft

The 48-run canonical `data/` inventory above is for the main scaling analyses. Some intervention and base-model sections still come from separate analysis outputs in the `origin/test-data-moltbook-post-cleanup` worktree.

### Base-model and OLMo analyses

Source worktree:

- `/Users/agokrani/Documents/git/moltbook-test-data-moltbook-post-cleanup/`

Primary source files:

- `analysis/base-model-diversity-analysis.md`
- `analysis/temporal-diversity-combined-20260408.json`
- `analysis/shannon-entropy-combined-20260408.json`
- `analysis/shannon-entropy-5gram-combined-20260408.json`
- `analysis/allmodels-semantic-diversity-openrouter-n10-20260410.json`
- `analysis/allmodels-topical-diversity-n10-20260410.json`
- `analysis/olmo-base-vs-instruct-run-review.md`
- `analysis/olmo-temporal-diversity.json`
- `analysis/olmo-shannon-entropy-3gram.json`
- `analysis/olmo-shannon-entropy-5gram.json`
- `analysis/olmo-semantic-diversity-openrouter-20260410.json`
- `analysis/olmo-topical-diversity-20260410.json`

Related plot directories:

- `analysis/plots-combined/plots-combined/`
- `analysis/plots-olmo/`
- `analysis/plots-semantic-openrouter-allmodels-n10-20260410/`
- `analysis/plots-semantic-openrouter-olmo-20260410/`
- `analysis/plots-topical-allmodels-n10-20260410/`
- `analysis/plots-topical-olmo-20260410/`

Note: these are not part of the canonical 48-run scaling inventory. They support the base-model / OLMo comparison sections and should be described as a separate analysis family.

### Mixed-roster probe

Source worktree:

- `/Users/agokrani/Documents/git/moltbook-test-data-moltbook-post-cleanup/`

Primary source files:

- `analysis/mag25-frontier-1h-20260422/compression.json`
- `analysis/mag25-frontier-1h-20260422/shannon-3gram.json`
- `analysis/mag25-frontier-1h-20260422/temporal.json`
- `analysis/agent-roaster/README.md`

Note: this is a single-run probe and should not be reported with the same weight as the canonical 48-run results.

### Obsession prompting probe

Source worktree:

- `/Users/agokrani/Documents/git/moltbook-test-data-moltbook-post-cleanup/`

Primary source files:

- `analysis/obsession_5h_gpt5/compression.json`
- `analysis/obsession_5h_gpt5/compression_baseline.json`
- `analysis/obsession_5h_gpt5/compression_obs_1h.json`
- `analysis/obsession_5h_gpt5/plots/baseline_vs_obsession.png`

Note: this is an intervention/probe analysis, not part of the canonical 48-run scaling inventory.

## Remaining decision

The remaining issue is not a data mismatch. It is a metric-reporting decision for fixed-window metrics when a run has no agent-authored posts in the final 15-minute bin.

See:

- `findings/emnlp-2026-paper/decision-required-on-metrics-to-report.md`
