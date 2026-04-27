# Moltbook HuggingFace Dataset Inventory

**Local mirror (not tracked in git):** `/Users/fortuna/Desktop/UoT/moltbook-hf-datasets/`
**Downloaded:** 2026-04-26
**Source:** All datasets owned by [Ayushnangia](https://huggingface.co/Ayushnangia) on HuggingFace, filtered to repos containing `moltbook` or `civiclens`.
**Total:** 30 datasets, 1.3 GB on disk, ~75,500 posts across ~200 runs.
**Tool used:** `hf download <repo> --repo-type dataset --local-dir <subdir>`

> This inventory documents the offline mirror of all moltbook/civiclens HuggingFace datasets. The data lives outside the repo to avoid git bloat; this file is the canonical reference for what was downloaded, where, and how to reproduce.

---

## Quick Summary

| Metric | Value |
|---|---|
| Datasets | 30 |
| Total size on disk | 1.3 GB |
| Total runs (dirs with `posts.jsonl` or `posts.csv`) | ~200 |
| Total posts (JSONL only, world-posts excluded) | ~75,500 |
| Largest dataset | `moltbook-entropy-collapse-kimi-k2.5` (159 MB) |
| Smallest dataset | `moltbook-base-model-experiment-test` (776 KB) |
| Unique LLM models tested | 10 (kimi-k2.5, glm-5, gemini-flash-lite, olmo-3-base, olmo-3-instruct, qwen-35b-base, qwen-instruct, gpt-5, frontier-mixed, default) |

---

## All 30 Datasets

| # | Dataset | Size | Runs | Posts | Family | Model |
|---|---|---:|---:|---:|---|---|
| 1 | `moltbook-entropy-collapse-kimi-k2.5` | 159M | 6 | 3,718 | entropy-collapse | kimi-k2.5 |
| 2 | `moltbook-obsession-gpt5` | 157M | 8 | 3,920 | obsession | gpt-5 |
| 3 | `moltbook-entropy-collapse-gemini-flash-lite` | 138M | 18 | 11,586 | entropy-collapse | gemini-flash-lite |
| 4 | `moltbook-entropy-collapse-30agents` | 135M | 6 | 9,436 | entropy-collapse-scale | gpt-5 (n30) |
| 5 | `moltbook-entropy-collapse-20agents` | 110M | 6 | 7,367 | entropy-collapse-scale | gpt-5 (n20) |
| 6 | `moltbook-entropy-collapse-experiments` | 100M | 12 | 7,105 | entropy-collapse | mixed |
| 7 | `moltbook-entropy-collapse-gemini-flash-lite-failures` | 92M | 13 | 9,506 | entropy-collapse | gemini-flash-lite |
| 8 | `moltbook-entropy-collapse-glm-5` | 86M | 6 | 1,641 | entropy-collapse | glm-5 |
| 9 | `moltbook-entropy-collapse-gemini-flash-lite-n20` | 54M | 6 | 5,001 | entropy-collapse-scale | gemini (n20) |
| 10 | `civiclens-entropy-collapse` | 43M | 12 | 201 | entropy-collapse | (early/sparse) |
| 11 | `moltbook-entropy-collapse-olmo-3-base` | 40M | 6 | 1,666 | entropy-collapse | olmo-3-base |
| 12 | `moltbook-ec-1h-base-model-experiments` | 39M | 6 | 1,433 | base-model | qwen-35b-base (1h) |
| 13 | `moltbook-entropy-collapse-qwen-35b-base` | 39M | 6 | 1,433 | entropy-collapse | qwen-35b-base |
| 14 | `moltbook-entropy-collapse-olmo-3-instruct` | 38M | 6 | 2,200 | entropy-collapse | olmo-3-instruct |
| 15 | `moltbook-frontier-mixed-mag25-1h` | 28M | 2 | 720 | frontier-mixed | mixed |
| 16 | `moltbook-source-citation-gpt5-1h` | 26M | 4 | 1,498 | source-citation | gpt-5 |
| 17 | `moltbook-entropy-collapse-gemini-flash-lite-n10` | 23M | 6 | 2,176 | entropy-collapse-scale | gemini (n10) |
| 18 | `moltbook-ec-10m-base-model-experiments` | 19M | 18 | 770 | base-model | 3 models × 6 conds (10m) |
| 19 | `moltbook-obsession-gemini-flash-lite` | 15M | 2 | 109 | obsession | gemini-flash-lite |
| 20 | `moltbook-factual-threshold-v2` | 5.9M | 21* | 534 | factcheck | (CSV bundle + raw JSONL) |
| 21 | `moltbook-entropy-collapse-v2` | 4.9M | 6 | 2,447 | entropy-collapse | gpt-5 (early) |
| 22 | `moltbook-conspiracy-vs-factual` | 2.0M | 7* | 203 | factcheck | (CSV + raw JSONL) |
| 23 | `moltbook-factual-threshold` | 2.0M | 7* | 168 | factcheck | (CSV + raw JSONL) |
| 24 | `moltbook-base-model-experiment-test-run3` | 1.7M | 1 | 55 | base-model | (test) |
| 25 | `moltbook-entropy-collapse` | 1.5M | 6 | 109 | entropy-collapse | (early) |
| 26 | `moltbook-factcheck-dose-response` | 1.5M | 1 | 175 | factcheck | dose-response |
| 27 | `moltbook-factcheck-conspiracy-grok` | 1.4M | 4 | 123 | factcheck | conspiracy-grok |
| 28 | `civiclens-turbo-experiment` | 948K | 1 | 8 | turbo | (sparse) |
| 29 | `civiclens-religion-experiment` | 808K | 2 | 11 | religion | (sparse) |
| 30 | `moltbook-base-model-experiment-test` | 776K | 1 | 45 | base-model | (test) |

`*` Includes both raw per-run JSONL (in `raw/`) and bundled CSV (in `data/`); count is JSONL+CSV.

---

## By Family

### Entropy collapse — main effect (12 datasets, ~57k posts)
The flagship line of work. Tests whether multi-agent LLM discourse loses diversity over time.
- `moltbook-entropy-collapse-kimi-k2.5`, `-glm-5`, `-gemini-flash-lite`, `-olmo-3-base`, `-olmo-3-instruct`, `-qwen-35b-base` — model variants
- `moltbook-entropy-collapse-v2`, `moltbook-entropy-collapse`, `moltbook-entropy-collapse-experiments` — earlier iterations
- `civiclens-entropy-collapse` — the original civiclens-tagged run (sparse)
- `moltbook-entropy-collapse-gemini-flash-lite-failures` — failed-run salvage (analysis-relevant)

### Entropy collapse — scaling (3 datasets, ~22k posts)
Tests whether collapse intensifies with more agents.
- `moltbook-entropy-collapse-20agents`, `-30agents` (gpt-5)
- `moltbook-entropy-collapse-gemini-flash-lite-n10`, `-n20` (gemini)

### Base-model experiments (4 datasets, ~2.3k posts)
Base vs RLHF comparison (Qwen 3.5 35B A3B Base/Instruct, Gemini Flash Lite).
- `moltbook-ec-10m-base-model-experiments` — 10-min runs, 3 models × 6 conditions
- `moltbook-ec-1h-base-model-experiments` — 1-hour follow-up on Qwen Base
- `moltbook-base-model-experiment-test`, `-run3` — pilot runs

### Factcheck / context-rot (5 datasets, ~1.2k posts)
Dose-response: how many factual posts are needed to rebalance a conspiracy-dominated feed?
- `moltbook-factcheck-dose-response` — flat single-run, dose 0–5
- `moltbook-factual-threshold`, `-v2` — CSV-bundled with `raw/` JSONL per run
- `moltbook-conspiracy-vs-factual`
- `moltbook-factcheck-conspiracy-grok`

### Obsession (2 datasets, ~4k posts)
Long-duration topic-fixation studies.
- `moltbook-obsession-gpt5` (5h + 1h variants)
- `moltbook-obsession-gemini-flash-lite` (5h + 1h variants)

### Source-citation, frontier-mixed, religion, turbo (4 datasets, ~2.2k posts)
- `moltbook-source-citation-gpt5-1h` — agents posting with citations
- `moltbook-frontier-mixed-mag25-1h` — multi-model mixture
- `civiclens-religion-experiment` — religion topic seeding (sparse)
- `civiclens-turbo-experiment` — turbo heartbeat infrastructure test (sparse)

---

## Layout Patterns

Datasets fall into 4 layout patterns. A discovery script needs to handle all four.

| Pattern | Where runs live | Example | Affects |
|---|---|---|---|
| **A** | `data/<run-name>/posts.jsonl` | `moltbook-entropy-collapse-kimi-k2.5/data/ec-mag25-n10-run01/posts.jsonl` | ~18 datasets |
| **B** | `data/<model>/<run-name>/posts.jsonl` (two-level) | `moltbook-ec-10m-base-model-experiments/data/qwen-base/bm-mag25-n10/posts.jsonl` | 1 dataset |
| **C** | `<run-name>/posts.jsonl` at root | `civiclens-entropy-collapse/ec-mag5-run01/posts.jsonl` | 1 dataset |
| **D** | Flat `posts.jsonl` at root (single run) | `moltbook-factcheck-dose-response/posts.jsonl` | 3 datasets |
| **E** | CSV bundle in `data/posts.csv` + per-run JSONL in `raw/` | `moltbook-factual-threshold/{data,raw}/...` | 3 datasets |
| **F** | Mixed (both `data/` AND root run dirs) | `moltbook-entropy-collapse-experiments` | 1 dataset |

### Canonical files in a run dir
- `posts.jsonl` (or `posts.csv`) — required
- `comments.jsonl` (or `.csv`) — usually present
- `agents.jsonl` (or `.csv`) — usually present
- `metadata.json` — present in JSONL-format runs; contains `experiment_name`, `condition`, `duration_minutes`, `num_agents`, `model`, stats
- `treatments.jsonl` — present where seeded posts were used
- `activity.jsonl` — present in ~50% of runs
- `database-final.sql` or `database.sql` — full Postgres dump of the experiment

### Posts JSONL schema (consistent across most datasets)
```
id, title, content, submolt, post_type, score, comment_count,
created_at, author_name, author_display_name, [url | source_url]
```
Variants: `factcheck-dose-response` adds `dose`, `run_id`; `factual-threshold` (CSV) adds `experiment`, `experiment_label`, `n_factual_dose`, `topic`, `treatment`, `is_world_post`.

---

## Reproducing the Download

```bash
# All datasets are public; no auth needed for read.
hf download Ayushnangia/<dataset-name> --repo-type dataset --local-dir <local-path>
```

The full download script is at `_download.sh` in this directory. Re-running it is incremental — `hf download` uses ETags and only fetches changed files.

---

## Files in This Directory

- `_download.sh` — the script that downloaded everything
- `_download.log` — log of the download run
- `INVENTORY.md` — this file
- 30 dataset subdirectories (one per HF repo)

---

## Notes

- The `entropy-collapse-gemini-flash-lite` dataset (138 MB, 18 runs, 11,586 posts) is currently the largest single-model entropy-collapse dataset and the natural anchor for cross-model comparison plots.
- `civiclens-entropy-collapse` and the early `moltbook-entropy-collapse` are sparse (≤200 posts) and are best treated as historical, not used for headline analyses.
- The `*-failures` dataset preserves runs that failed mid-experiment — useful for understanding what kinds of conditions cause cascade failures, but not for steady-state metrics.
- All datasets are public on HuggingFace (verified via `hf auth whoami` → `Ayushnangia`).
