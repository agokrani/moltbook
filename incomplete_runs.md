# Incomplete canonical runs

Eight of the 48 canonical runs in `data/` have no agent-authored posts in the final 15-minute window (45–60 min from the first agent post). Under the current fixed-window metric scripts, the empty bin is encoded as `0.0`, which is not a content-collapse value but an activity dropout. These runs should be excluded from fixed-window final-vs-first comparisons and reported separately.

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

## Implication for metrics

The fixed-window metric scripts return literal `0.0` for empty bins:

- `scripts/gzip/compute_compression.py` — `compression_ratio()` returns `0.0` if input is empty
- `scripts/analyze-shannon-entropy-canonical.py` — `shannon_entropy_bits()` returns `0.0` if `total <= 0`
- `scripts/analysis_new/diversity_metrics.py` — `distinct_n_value()` and `effective_vocabulary_size()` return `0.0` for empty input

These zeros conflate activity dropout with content collapse. The 8 runs above should be excluded from fixed-window final-vs-first deltas. Cumulative Distinct-5 remains defined for these runs (it carries earlier posts forward) and can continue to be reported over all 48.

## Resume status (2026-05-01)

All 8 runs have been resumed from their `database-final.sql` dumps via `scripts/resume-entropy-run.py` and re-exported. Each resume restored the historical posts, rotated agent API keys, and ran the full agent population for ~34 additional minutes.

| # | Run | Resume export | Total posts | New (2026-05) | Active agents |
|---|---|---|---:|---:|---:|
| 1 | `ec-mag0-run04` | `exports/ec-mag0-run04-resumed/` | 480 | 110 | 10/10 |
| 2 | `ec-mag1-run04` | `exports/ec-mag1-run04-resumed/` | 509 | 103 | 10/10 |
| 3 | `ec-dom-agi-n10-run01` | `exports/ec-dom-agi-n10-run01-resumed/` | 320 | 150 | 10/10 |
| 4 | `ec-dom-tech-n10-run01` | `exports/ec-dom-tech-n10-run01-resumed/` | 341 | 113 | 10/10 |
| 5 | `ec-dom-agi-n20-run01` | `exports/ec-dom-agi-n20-run01-resumed/` | 828 | 403 | 20/20 |
| 6 | `ec-mag5-n20-run01` | `exports/ec-mag5-n20-run01-resumed/` | 718 | 308 | 20/20 |
| 7 | `ec-mag25-n30-run01` | `exports/ec-mag25-n30-run01-resumed/` | 1160 | 550 | 30/30 |
| 8 | `ec-mag5-n30-run01` | `exports/ec-mag5-n30-run01-resumed/` | 1062 | 460 | 30/30 |

The Gemini runs (#3–#8) showed mid-resume throughput drops with the same provider-side empty-completion signature, but never collapsed to 0 — every resume produced ≥100 new posts with full cluster participation. Resumed exports should be analyzed alongside the original `database-final.sql` for the full ~94-min trajectory.
