# Canonical data inventory

Environment note: this analysis is performed on Aman's MacBook in `~/Documents/git/moltbook`.

The source-data mismatch and the empty-Q3/Q4 dropout artifact in 8 runs have both been resolved. All paper analyses now read from the canonical 48-run inventory below, with the 8 dropout runs replaced by their resumed and re-timestamped continuations.

## Provenance, in order

1. **Original canonical exports** — 48 first-hour runs across 4 model sets, downloaded from HuggingFace at the start of the project. Live under `data/moltbook-entropy-collapse-*/`.
2. **8 of those 48 runs had agent-activity dropout** before 60 minutes (paired wall-clock cut for 2 GPT-5 runs at ~43 min; provider-side empty completions for 6 Gemini Flash Lite runs at ~24–40 min). See `incomplete_runs.md` for forensics.
3. **Resumed continuations** were run for those 8 cases (Ayush Nangia / `Ayushnangia` on HuggingFace), restoring the post-export database and bringing the agents back online for ~30 more minutes. Published as the dataset `Ayushnangia/moltbook-entropy-collapse-resumes` and mirrored locally at `data/resumed/`.
4. **Merge + retimestamp** glues each original to its resumed continuation, compressing the multi-day pause to a 1-second gap. Output lives at `data/canonical-merged/` and is produced by `scripts/retimestamp/retimestamp_resumed.py`. Audit log at `data/canonical-merged/retimestamp_summary.json`.
5. **Analysis overlay** at `data/canonical-merged-overlay/` is a tree of 48 symlinks: 40 point at the canonical originals, 8 point at the merged versions. Produced by `scripts/retimestamp/build_overlay.sh`. This is the single root all paper analyses now read from.

## Canonical local data paths

| Path | Role | Runs | Notes |
|---|---|---:|---|
| `data/moltbook-entropy-collapse-v2/` | GPT-5 n10 run04 set | 6 | 2 of 6 affected by dropout |
| `data/moltbook-entropy-collapse-20agents/` | GPT-5 n20 | 6 | 0 affected |
| `data/moltbook-entropy-collapse-30agents/` | GPT-5 n30 | 6 | 0 affected |
| `data/moltbook-entropy-collapse-gemini-flash-lite/` | Gemini n10/n20/n30 | 18 | 6 of 18 affected by dropout |
| `data/moltbook-entropy-collapse-kimi-k2.5/` | Kimi n10 | 6 | 0 affected |
| `data/moltbook-entropy-collapse-glm-5/` | GLM-5 n10 | 6 | 0 affected |
| `data/resumed/` | Resumed continuations of the 8 dropout runs (HF mirror) | 8 | Synced from `Ayushnangia/moltbook-entropy-collapse-resumes` |
| `data/canonical-merged/` | Per-run merged + retimestamped exports for the 8 dropout runs | 8 | Output of `retimestamp_resumed.py` |
| `data/canonical-merged-overlay/` | Unified overlay tree (40 originals + 8 merged) used by all analyses | 48 | Symlinks; produced by `build_overlay.sh` |

Total: **48 canonical runs**, with 8 of them now reading from the merged versions.

## Canonical scripts

These scripts are the official sources for the paper's lexical, compression, and phrase-level results. All read from `data/canonical-merged-overlay/` (or use `--merged-overrides-dir` against the canonical mirror, equivalently).

### Data preparation

| Script | Purpose |
|---|---|
| `scripts/retimestamp/retimestamp_resumed.py` | For each of the 8 dropout runs, glue the original to its resumed continuation by detecting the multi-day pause and shifting post-pause records back so the gap becomes 1 second. Writes to `data/canonical-merged/` plus `retimestamp_summary.json`. |
| `scripts/retimestamp/build_overlay.sh` | Build the analysis overlay (`data/canonical-merged-overlay/`). 48 symlinks, 8 of which redirect to `data/canonical-merged/`. Idempotent. |

### Analysis

| Script | Purpose | Output (paper-canonical) |
|---|---|---|
| `scripts/gzip/compute_compression.py` | gzip / bzip2 / zlib compression ratio per fixed 15-min bin, first 60 minutes | `findings/entropy-collapse-gzip-resumed/results-canonical-48-resumed.json` |
| `scripts/gzip/plot_compression.py` | Trajectory and heatmap plots for the above | `findings/entropy-collapse-gzip-resumed/*.png` |
| `scripts/analysis_new/diversity_metrics.py` | distinct-5 windowed, distinct-5 cumulative, Simpson's 1/D | `findings/entropy-collapse-scaling-resumed/<set>/diversity/` |
| `scripts/analysis_new/analyze_time_binned_lexical_5gram.py` | distinct-1 to distinct-5 raw + bin-size-controlled (subsampled) with 95% CIs | `findings/entropy-collapse-multiscale-new-5gram-resumed/<set>/` |
| `scripts/analysis_new/agent_participation.py` | Gini concentration, archetype adoption rates, agent-usage grids | `findings/entropy-collapse-scaling-resumed/<set>/participation/` |
| `scripts/analysis_new/ngram_provenance.py` | Per-run top 4-grams and 5-grams; "phrase DNA" plots | `findings/entropy-collapse-scaling-resumed/<set>/provenance/` |
| `scripts/analysis_new/phrase_diffusion.py` | First-usage timeline of top-3 phrases per run; scale-comparison plots | `findings/entropy-collapse-scaling-resumed/<set>/diffusion/` |

`<set>` ranges over `gpt-5`, `gemini-flash-lite`, `kimi-k2.5`, `glm-5`.

### Reproduction

```bash
# 1. Download resumed continuations (idempotent; cached after first run).
python3 -c "from huggingface_hub import snapshot_download; \
            snapshot_download(repo_id='Ayushnangia/moltbook-entropy-collapse-resumes', \
                              repo_type='dataset', local_dir='data/resumed')"

# 2. Merge originals + resumes; produce data/canonical-merged/.
python3 scripts/retimestamp/retimestamp_resumed.py

# 3. Build analysis overlay tree.
bash scripts/retimestamp/build_overlay.sh

# 4. Run gzip canonical analysis (uses --merged-overrides-dir against the canonical mirror).
python3 scripts/gzip/compute_compression.py \
  --data-root data \
  --merged-overrides-dir data/canonical-merged \
  --output findings/entropy-collapse-gzip-resumed/results-canonical-48-resumed.json
python3 scripts/gzip/plot_compression.py \
  --input findings/entropy-collapse-gzip-resumed/results-canonical-48-resumed.json \
  --output-dir findings/entropy-collapse-gzip-resumed

# 5. Run lexical / phrase analyses against the overlay (one invocation per model set).
for tree in gpt-5 gemini-flash-lite kimi-k2.5 glm-5; do
  case "$tree" in
    kimi-k2.5|glm-5) scales=n10 ;;
    *) scales=n10,n20,n30 ;;
  esac
  python3 scripts/analysis_new/diversity_metrics.py \
    --data-dir "data/canonical-merged-overlay/$tree" --scales "$scales" \
    --out-dir "findings/entropy-collapse-scaling-resumed/$tree/diversity"
  python3 scripts/analysis_new/analyze_time_binned_lexical_5gram.py \
    --data-dir "data/canonical-merged-overlay/$tree" --scales "$scales" \
    --out-dir "findings/entropy-collapse-multiscale-new-5gram-resumed/$tree"
  python3 scripts/analysis_new/agent_participation.py \
    --data-dir "data/canonical-merged-overlay/$tree" --scales "$scales" \
    --out-dir "findings/entropy-collapse-scaling-resumed/$tree/participation"
  python3 scripts/analysis_new/ngram_provenance.py \
    --data-dir "data/canonical-merged-overlay/$tree" --scales "$scales" \
    --out-dir "findings/entropy-collapse-scaling-resumed/$tree/provenance"
  python3 scripts/analysis_new/phrase_diffusion.py \
    --data-dir "data/canonical-merged-overlay/$tree" --scales "$scales" \
    --out-dir "findings/entropy-collapse-scaling-resumed/$tree/diffusion"
done
```

## Findings paths used by the paper

The `-resumed` suffix denotes the corrected version. The non-suffixed directories
contain the pre-merge outputs and are kept for historical comparison only.

- `findings/entropy-collapse-gzip-resumed/` — gzip / bzip2 / zlib over all 48 runs (paper-canonical)
- `findings/entropy-collapse-scaling-resumed/{gpt-5,gemini-flash-lite,kimi-k2.5,glm-5}/{diversity,participation,provenance,diffusion}/` — lexical and phrase analyses per model set (paper-canonical)
- `findings/entropy-collapse-multiscale-new-5gram-resumed/{gpt-5,...}/` — distinct-1..5 with subsampled CIs per model set (paper-canonical)
- `findings/entropy-collapse-gzip/` — *historical*, pre-resume gzip output (kept for comparison only)
- `findings/entropy-collapse-scaling/` — *historical*, pre-resume scaling outputs (kept for comparison only)

## Other analysis sources used in the paper draft

The 48-run canonical inventory above is for the main scaling analyses. Some intervention and base-model sections come from a separate worktree and are reported as separate analysis families.

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

Note: these are not part of the canonical 48-run scaling inventory. They support the base-model / OLMo comparison sections and are described as a separate analysis family.

### Mixed-roster probe

Source worktree:

- `/Users/agokrani/Documents/git/moltbook-test-data-moltbook-post-cleanup/`

Primary source files:

- `analysis/mag25-frontier-1h-20260422/compression.json`
- `analysis/mag25-frontier-1h-20260422/shannon-3gram.json`
- `analysis/mag25-frontier-1h-20260422/temporal.json`
- `analysis/agent-roaster/README.md`

Note: this is a single-run probe and is reported as an intervention probe with appropriate caveats.

### Obsession prompting probe

Source worktree:

- `/Users/agokrani/Documents/git/moltbook-test-data-moltbook-post-cleanup/`

Primary source files:

- `analysis/obsession_5h_gpt5/compression.json`
- `analysis/obsession_5h_gpt5/compression_baseline.json`
- `analysis/obsession_5h_gpt5/compression_obs_1h.json`
- `analysis/obsession_5h_gpt5/plots/baseline_vs_obsession.png`

Note: an intervention probe, not part of the canonical 48-run scaling inventory.

## Resolved decisions

The previous open question about how to report fixed-window metrics with empty bins (`decision-required-on-metrics-to-report.md`) is now moot for the canonical 48: the merged data has zero empty bins. The decision file is kept as a record of the pre-resume reasoning.

`incomplete_runs.md` documents the 8 runs that originally had empty bins; they are now fully covered by the merge.
