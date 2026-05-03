# Decision required: how to report fixed-window metrics with empty bins

> **Status: RESOLVED 2026-05-03.**
> The decision below was needed because 8 of 48 runs had empty final bins. Those
> 8 runs have since been re-launched, exported as
> [`Ayushnangia/moltbook-entropy-collapse-resumes`](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-resumes),
> merged with their originals (`scripts/retimestamp/retimestamp_resumed.py`),
> and folded into the canonical inventory through the analysis overlay
> (`data/canonical-merged-overlay/`). After the merge, **zero of 48 runs** have
> an empty final bin, so fixed-window metrics no longer need a special-case
> exclusion rule. The paper-canonical numbers are now computed over all 48 runs
> with no missing bins. See `canonical_data.md` for the pipeline and `findings.md`
> for the corrected statistics.
>
> The bottom-line shift in the headline numbers, before vs after the merge:
>
> | Metric | Before (with empty-bin zeros) | After (resumed + merged) |
> |---|---:|---:|
> | gzip mean Δ (Q4−Q1) | -0.089, 46/48 declines | -0.037, 44/48 declines, p=1.5e-9 |
> | Fixed-window distinct-5 mean Δ | -0.250, 47/48 declines | -0.090, 44/48 declines, p=1.5e-9 |
> | Cumulative distinct-5 mean Δ | -0.056, 46/48 declines | -0.056, 47/48 declines, p=3.5e-13 |
> | Simpson's 1/D mean Δ | -5,309 | -4,447, 44/48 declines |
>
> The cumulative metric is essentially unchanged (it carried earlier posts
> forward in the dropout runs). The fixed-window metrics shrink in magnitude
> because the inflated near-zero values from empty bins are gone, but the
> direction is unchanged and the 95% CIs are well below zero.
>
> The original analysis below is kept as a record.

---

## Issue

Some canonical runs have no agent-authored posts in the later 15-minute bins. In the current fixed-window metrics, these empty bins are encoded as `0.0`.

This affects:

- gzip compression ratio,
- Shannon entropy,
- fixed-window Distinct-5,
- Simpson-style effective diversity.

A zero value in these cases does **not** mean that text entropy collapsed to zero. It means there was no text in that bin.

## Runs with empty final bins

These runs have zero agent-authored posts in the final 45–60 minute bin:

| Model | Scale | Condition | Run | Bin counts: 0–15 / 15–30 / 30–45 / 45–60 | Last post minute |
|---|---|---|---|---|---:|
| GPT-5 | n10 | `mag0` | `ec-mag0-run04` | 114 / 126 / 129 / 0 | 42.98 |
| GPT-5 | n10 | `mag1` | `ec-mag1-run04` | 134 / 143 / 127 / 0 | 43.77 |
| Gemini | n10 | `dom-agi` | `ec-dom-agi-n10-run01` | 103 / 42 / 0 / 0 | 24.62 |
| Gemini | n10 | `dom-tech` | `ec-dom-tech-n10-run01` | 107 / 85 / 11 / 0 | 40.14 |
| Gemini | n20 | `dom-agi` | `ec-dom-agi-n20-run01` | 241 / 159 / 0 / 0 | 26.22 |
| Gemini | n20 | `mag5` | `ec-mag5-n20-run01` | 231 / 174 / 0 / 0 | 26.19 |
| Gemini | n30 | `mag25` | `ec-mag25-n30-run01` | 293 / 292 / 0 / 0 | 26.19 |
| Gemini | n30 | `mag5` | `ec-mag5-n30-run01` | 306 / 291 / 0 / 0 | 26.00 |

These should be treated as **activity dropouts**, not as zero-entropy or zero-compression text.

## Why this appears differently across metrics

### Fixed-window metrics

Fixed-window metrics compute the value using only posts inside a single 15-minute bin.

If a bin has no posts, the current scripts return `0.0`.

This affects:

- gzip,
- Shannon entropy,
- fixed-window Distinct-5,
- Simpson-style effective diversity.

For these metrics, final-bin vs first-bin decline should only be computed when both the first and final bins are non-empty.

### Cumulative metrics

Cumulative Distinct-5 is different. It uses all posts from the start of the run through the current bin.

So if the final bin is empty, cumulative Distinct-5 remains defined because it carries forward earlier posts.

That is why cumulative Distinct-5 does not drop to zero in dropout runs.

## Current implication for gzip and Shannon

If empty final bins are included as zeros, the results look like:

- gzip: 46/48 declines
- raw 3-gram Shannon entropy: 48/48 declines
- raw 5-gram Shannon entropy: 48/48 declines

But this mixes content collapse with activity dropout.

If we exclude runs where the first or final bin is empty:

| Metric | Valid runs | Declines among valid runs | Notes |
|---|---:|---:|---|
| gzip | 40 | 38/40 | Two valid runs increase: GPT-5 n10 `mag25`, Gemini n20 `mag0` |
| raw 3-gram Shannon entropy | 40 | 40/40 | All valid runs decline |
| raw 5-gram Shannon entropy | 40 | 40/40 | All valid runs decline |

This is probably the cleaner reporting choice.

## Decision needed

We need to decide how the paper should report fixed-window metrics.

Recommended approach:

1. Treat empty-bin values as missing/undefined, not zero.
2. Report fixed-window final-vs-first declines only over runs with non-empty first and final bins.
3. Report activity dropouts separately.
4. Keep cumulative Distinct-5 over all 48 runs, because it remains defined even when later bins are empty.

Suggested wording:

> Eight runs had no agent-authored posts in the final 15-minute window. We treat these as activity dropouts rather than zero-entropy text. For fixed-window metrics, final-vs-first comparisons are therefore computed only on runs with non-empty first and final bins. Under this rule, gzip declines in 38/40 valid runs and raw Shannon entropy declines in 40/40 valid runs.

## Scripts that should be updated if we accept this

- `scripts/gzip/compute_compression.py`
- `scripts/analyze-shannon-entropy-canonical.py`
- possibly `scripts/analysis_new/diversity_metrics.py` if we regenerate fixed-window Distinct-5 / Simpson summaries

Required behavior:

- empty fixed-window bins should be written as `null`, not `0.0`;
- plots should break lines or show missing values instead of dropping to zero;
- summary statistics should exclude missing final-bin comparisons;
- dropout counts should be reported separately.

## Open question

Should activity dropout be treated as a separate finding?

Possible framing:

> In some runs, collapse appears not only as repetitive text, but as cessation of agent posting. We report this separately from content-level entropy collapse.

This may be interesting, but it should not be mixed into the main content-diversity metric unless explicitly stated.
