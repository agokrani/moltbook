# Incomplete canonical runs

> **Status: RESOLVED 2026-05-03.**
> All 8 runs listed below now have agent-authored posts in every 15-minute bin via
> the resumed-and-merged pipeline documented in `canonical_data.md`. The merged
> versions live at `data/canonical-merged/<run>/` and are used by every paper analysis
> via the overlay tree at `data/canonical-merged-overlay/`. After the merge, 0 of 48
> runs have an empty final bin. Fixed-window metrics no longer need a special-case
> exclusion rule. This file is kept as a forensic record of the original failure
> modes (provider-side empty completions for Gemini Flash Lite; wall-clock batch
> termination for two GPT-5 runs).

---

Eight of the 48 canonical runs in `data/` had no agent-authored posts in the final 15-minute window (45–60 min from the first agent post). Under the fixed-window metric scripts, the empty bin was encoded as `0.0`, which is not a content-collapse value but an activity dropout. Before the merge, these runs were excluded from fixed-window final-vs-first comparisons and reported separately.

## Affected runs (8 of 48)

| # | Set | Scale | Run | Bin counts (0–15 / 15–30 / 30–45 / 45–60) | Last post (min) | Likely cause |
|---|---|---|---|---|---:|---|
| 1 | GPT-5 | n10 | `ec-mag0-run04` | 114 / 126 / 129 / **0** | 42.98 | Wall-clock batch termination at ~43 min (paired with #2) |
| 2 | GPT-5 | n10 | `ec-mag1-run04` | 134 / 143 / 127 / **0** | 43.77 | Wall-clock batch termination at ~43 min (paired with #1) |
| 3 | Gemini | n10 | `ec-dom-agi-n10-run01` | 103 / 42 / **0** / **0** | 24.62 | Provider-side empty completions (verified in agent logs) |
| 4 | Gemini | n10 | `ec-dom-tech-n10-run01` | 107 / 85 / 11 / **0** | 40.14 | Same Gemini provider-side dropout signature |
| 5 | Gemini | n20 | `ec-dom-agi-n20-run01` | 241 / 159 / **0** / **0** | 26.22 | Same; 18 of 20 agents drop to empty completions within ~100 s |
| 6 | Gemini | n20 | `ec-mag5-n20-run01` | 231 / 174 / **0** / **0** | 26.19 | Same |
| 7 | Gemini | n30 | `ec-mag25-n30-run01` | 293 / 292 / **0** / **0** | 26.19 | Same |
| 8 | Gemini | n30 | `ec-mag5-n30-run01` | 306 / 291 / **0** / **0** | 26.00 | Same |

## Full paths

```
data/moltbook-entropy-collapse-v2/data/ec-mag0-run04
data/moltbook-entropy-collapse-v2/data/ec-mag1-run04
data/moltbook-entropy-collapse-gemini-flash-lite/data/n10/ec-dom-agi-n10-run01
data/moltbook-entropy-collapse-gemini-flash-lite/data/n10/ec-dom-tech-n10-run01
data/moltbook-entropy-collapse-gemini-flash-lite/data/n20/ec-dom-agi-n20-run01
data/moltbook-entropy-collapse-gemini-flash-lite/data/n20/ec-mag5-n20-run01
data/moltbook-entropy-collapse-gemini-flash-lite/data/n30/ec-mag25-n30-run01
data/moltbook-entropy-collapse-gemini-flash-lite/data/n30/ec-mag5-n30-run01
```

## Cause notes

### GPT-5 (#1, #2)

Both `ec-mag0-run04` and `ec-mag1-run04` end at the same wall-clock time (~13:01 UTC on 2026-03-05). The paired termination indicates external scheduling (compose stop / batch cut at ~43 min), not a model behavior. Per-agent runtime logs are not available for `moltbook-entropy-collapse-v2` (older export pipeline did not include `logs/`), so the precise reason for the 43-min cut cannot be confirmed from the export.

### Gemini (#3–#8)

All six Gemini runs share the same dropout signature, verified directly from per-agent logs in `<run>/logs/agent-*.log`:

- Posting stops near-simultaneously across all agents in each run (in `ec-dom-agi-n20-run01`, 18 of 20 agents transition within ~100 s).
- Embedded model-call duration drops from ~1500–2000 ms (real generation) to ~70–130 ms.
- The assistant stream goes from `lifecycle start → assistant text → lifecycle end` to `lifecycle start → lifecycle end` with no assistant-text event in between.
- `aborted=false` everywhere; no errors logged in the agent runtime.

This pattern is consistent with provider-side empty completions (likely a rate-limit or quota event on the shared OpenRouter `google/gemini-3.1-flash-lite-preview` route), not with the model behaviorally choosing silence. The HTTP response from OpenRouter is not in the exported logs, so the exact provider error cannot be confirmed without rerunning with verbose HTTP logging or checking the OpenRouter usage dashboard for that account on 2026-03-18.

## Implication for metrics (pre-merge)

The fixed-window metric scripts return literal `0.0` for empty bins:

- `scripts/gzip/compute_compression.py` — `compression_ratio()` returns `0.0` if input is empty
- `scripts/analyze-shannon-entropy-canonical.py` — `shannon_entropy_bits()` returns `0.0` if `total <= 0`
- `scripts/analysis_new/diversity_metrics.py` — `distinct_n_value()` and `effective_vocabulary_size()` return `0.0` for empty input

These zeros conflate activity dropout with content collapse. Before the merge, the 8 runs above had to be excluded from fixed-window final-vs-first deltas. Cumulative Distinct-5 was defined for these runs (it carries earlier posts forward) and could be reported over all 48.

## Resolution (post-merge)

The 8 runs were re-launched: the post-export Postgres dump was restored, every agent's API key was rotated, and the agent roster was brought back online for an additional ~30 minutes. The resumed exports were published as the HuggingFace dataset [`Ayushnangia/moltbook-entropy-collapse-resumes`](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-resumes) and merged with the originals via `scripts/retimestamp/retimestamp_resumed.py`. The script detects the multi-day inter-segment pause inside each resumed export and shifts post-pause timestamps backward so the gap collapses to 1 second. Outputs land at `data/canonical-merged/<run>/` plus an audit log at `data/canonical-merged/retimestamp_summary.json`.

After the merge, the bin counts for the same 8 runs are:

| # | Run | Bin counts (0–15 / 15–30 / 30–45 / 45–60) | Span (min) |
|---|---|---|---:|
| 1 | `ec-mag0-run04`           | 114 / 126 / 144 / 96  | 57.0 |
| 2 | `ec-mag1-run04`           | 134 / 143 / 135 / 96  | 56.0 |
| 3 | `ec-dom-agi-n10-run01`    | 103 / 97  / 139 / 57  | 51.9 |
| 4 | `ec-dom-tech-n10-run01`   | 107 / 85  / 57  / 82  | 53.2 |
| 5 | `ec-dom-agi-n20-run01`    | 241 / 178 / 83  / 141 | 61.9 |
| 6 | `ec-mag5-n20-run01`       | 231 / 240 / 272 / 112 | 61.3 |
| 7 | `ec-mag25-n30-run01`      | 294 / 319 / 291 / 374 | 63.2 |
| 8 | `ec-mag5-n30-run01`       | 306 / 342 / 395 / 375 | 62.8 |

No bin is empty. The four runs whose merged span exceeds 60 min are naturally trimmed by the existing `elapsed > 60: continue` filter inside the analysis scripts.
