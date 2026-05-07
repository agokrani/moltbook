# Blinded LLM collapse index

This note explains the LLM collapse index used in the 2026-05-05 reanalysis bundle and the 2026-05-06 plot pass.

## Post-level formula

The blinded judge scores each non-seed post on 1–5 integer scales. The collapse index uses five of those scores:

- `semantic_repetition` (`R`): repeats nearby/surrounding context.
- `frame_convergence` (`F`): follows the dominant shared frame.
- `consensus_conformity` (`G`): reinforces consensus rather than adding an independent/critical move.
- `template_rigidity` (`T`): formulaic/checklist/receipt-like structure.
- `novelty` (`N`): new substantive idea/evidence/frame.

Novelty is inverted so that lower novelty increases collapse:

```text
collapse_index_i = (R_i + F_i + G_i + T_i + (6 - N_i)) / 5
```

Range: `1` to `5`.

- `1` = low repetition/conformity/rigidity and high novelty.
- `5` = high repetition/conformity/rigidity and low novelty.

The judge also records `specificity`, `evidence_grounding`, `epistemic_caution`, `citation_quality`, labels, and rationale, but those are not part of the collapse-index formula.

## Fixed-window aggregation

For a run `r` and 15-minute bin `b`, the plotted fixed-window value is the mean post-level collapse score inside that bin:

```text
CI_window(r,b) = mean_{i in posts(r,b)} collapse_index_i
```

The run-level late-minus-early delta is:

```text
Delta_CI_window(r) = CI_window(r, final_bin) - CI_window(r, first_bin)
```

Positive `Delta_CI_window` means later posts in the run are judged more collapsed.

This is the best primary analysis for the paper because it asks whether the current local discourse state changes over time. It is also aligned with the fixed 15-minute gzip, Distinct-5, and Vendi trajectories.

## Cumulative aggregation

For cumulative plots, each point uses all non-seed posts seen so far. If `t` is a cutoff such as 30 minutes:

```text
CI_cumulative(r,t) = mean_{i in posts(r, 0 <= time_i <= t)} collapse_index_i
```

Equivalently, from bin means:

```text
CI_cumulative(r,t) = sum_{b <= t} n_{r,b} * CI_window(r,b) / sum_{b <= t} n_{r,b}
```

where `n_{r,b}` is the number of judged posts in bin `b`.

Cumulative collapse is useful for the reader-facing question: “Does the feed seen so far become more collapsed?” It should not replace fixed-window analysis because cumulative curves are smoothed by early posts and adjacent cumulative points are mechanically dependent.

## Reporting recommendation

Use both, but keep them separate:

1. **Main figure / main claim:** fixed 15-minute LLM collapse trajectories and run-level final-minus-first deltas.
2. **Companion or appendix figure:** cumulative LLM collapse trajectories, clearly labeled as “feed so far.”
3. Do not mix fixed-window and cumulative lines on the same axes.
4. Do not use pooled post-level significance tests; summarize at run level first.

## Current verified finding on latest `findings-handoff`

Latest checked commit: `3c296f2` (`origin/findings-handoff`, message: `reanalysis incomplete`).

For the matched 10-agent canonical runs:

| View | Metric | Collapse direction | Direction count | Median final-minus-first delta |
|---|---|---:|---:|---:|
| Fixed 15-minute | LLM collapse index | up | 24/24 | +0.288 |
| Cumulative | LLM collapse index | up | 23/24 | +0.156 |
| Cumulative | gzip compression ratio | down | 24/24 | -0.032 |
| Cumulative | Distinct-5 | down | 24/24 | -0.031 |

Interpretation: the LLM judge sees increasing collapse almost everywhere. The cumulative view is slightly smoother and weaker than the fixed-window view, which is expected because early posts remain in every later cumulative point.

## Plot files to use

Fixed-window LLM collapse:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step01_canonical_n10_trajectories/canonical_n10_llm_collapse_trajectory_by_model.png
```

Cumulative LLM collapse:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step02_canonical_n10_trajectories_cumulative/canonical_n10_llm_collapse_cumulative_trajectory_by_model.png
```

## Verification note

On 2026-05-07, Step 0–2 scripts were rerun in a temporary directory against the clean 2026-05-05 analysis source. The regenerated inventory JSON, metric-availability CSV, and cumulative metrics CSV matched the committed handoff outputs exactly; regenerated PNG sizes matched the committed PNG sizes.
