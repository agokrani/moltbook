# Evidence check

## Controlled runs

- Full paper cohort: 48 `single_model_final`, `fixed_15m` rows in the
  deterministic reanalysis CSV.
- Composition: GPT-5 and Gemini Flash Lite, six conditions each at `n10`, `n20`,
  and `n30`; Kimi K2.5 and GLM-5, six conditions each at `n10`.
- Full cohort: cumulative Distinct-5 decreases in 48/48; fixed-window Distinct-5
  in 44/48; fixed-window gzip in 44/48.
- Strict four-family `n10` cohort: fixed-window Distinct-5 22/24 (mean -0.067),
  equal-post Distinct-5 24/24 (-0.080), fixed-window gzip 23/24 (-0.027), and
  cumulative Distinct-5 24/24 (-0.058).
- Judge cohort: component counts 21–24/24, aggregate 24/24, and
  leave-one-component-out counts 21–24/24.
- Three-judge validation: 240 posts, with five posts sampled from 0–15 minutes
  and five from 45–60 minutes in each of the 24 main runs. All selected prompt
  hashes exactly match the prompts used by the original Gemini 3.1 Flash Lite
  judge. The same prompts were rescored by GPT-5.5 and Claude Opus 4.7. Relative
  to Gemini, mean quadratic-weighted Cohen's κ across the five collapse
  components is 0.60 and 0.72, and collapse-index Spearman correlation is 0.80
  and 0.84. Positive run-level changes occur in 20–23/24 runs per judge;
  all three run-bootstrap 95% confidence intervals for the mean change exclude
  zero. Sources: `data/multijudge_sample_metadata.csv`,
  `data/multijudge_post_scores.csv`, `data/multijudge_pairwise_agreement.csv`,
  and `data/multijudge_direction_summary.csv`; builder:
  `data/multijudge_validation.py`.
- Strict text-length normalization: within each run, all four 15-minute windows
  use the same token count for Distinct-5 and the same UTF-8 byte count for
  gzip, averaged over 100 deterministic random post orderings and using the
  paper's preprocessing. Equal-token Distinct-5 declines in 22 of 24 runs
  (mean delta -0.071); equal-byte gzip declines in all 24 (mean delta -0.061).
  Source: `data/temporal_equal_length_results.json`;
  script: `data/build_temporal_length_normalization.py`.

The final package uses 48/48 for cumulative Distinct-5. An older July extract
reported 47/48 from a different extraction; the current reanalysis
CSV is later, internally consistent, and is the source used here.

## Reddit comparison

- Exact upstream processed report:
  `rebuttal_assets/moltbook_vs_reddit_report_havelock.json`.
- SHA-256:
  `32c1dc98ae140c0d3729d633aa390382ac8ff6657e07aacf466793d5c2fed453`.
- Full corpora: 35,589 messages per source.
- Message-matched sample: 15,051 per source, 50-character bins, minimum cleaned
  length 40.
- Thread-matched sample: 388 per source, 500-character bins, minimum cleaned
  length 500.

## Five-hour persistence (new)

- Source: `data_manifest.csv`, `ayush_reanalysis/deterministic_timebin_metrics.csv`, and `ayush_reanalysis/llm_judge_run_timebin_metrics.csv`, scheme `normalized_quartile`, joined on `run_uid`.
- Six selected five-hour GPT-5 runs, one per condition, ran 272–297 minutes.
- One-hour references: six 10-agent GPT-5 runs (54–57 min) and six 10-agent Gemini Flash Lite runs (52–58 min), one per condition. All six runs for each model have lower equal-post Distinct-5 and a higher judge collapse index. Mean changes are GPT-5: -0.176 and +0.257; Gemini Flash Lite: -0.099 and +0.291.
- The six selected five-hour GPT-5 runs cover all six conditions exactly once. Equal-post Distinct-5 declines and the judge collapse index rises in all six. Mean changes are -0.024 and +0.198.
- The combined paper-style cumulative figure exactly reproduces the paper's one-hour GPT-5 values. At five hours, the cumulative judge index rises in all six conditions; cumulative Distinct-5 and gzip decrease in five. Tech changes from 0.976 to 0.981 on cumulative Distinct-5 and from 0.380 to 0.390 on cumulative gzip. Its equal-post Distinct-5 still decreases from 0.995 to 0.991.
- The eight-cutoff long-horizon extension uses 15, 30, 45, 60, 120, 180, 240, and 300 minutes. From 60 to 300 minutes, mean changes are -0.011 for cumulative Distinct-5, -0.008 for cumulative gzip, and +0.053 for the cumulative judge index. Condition-ranking Spearman correlations are 0.60, -0.26, and 0.94, respectively. Source: `data/long_horizon_cumulative.csv` and `data/long_horizon_summary.json`; builder: `data/build_long_horizon_extension.py`.
- The two scheduled five-hour Gemini Flash Lite attempts cover only the 25-conspiracies condition. One contains 28 total posts, of which 25 are seeds, and the other contains no posts. Neither has a comparable final quarter, so Table C3 marks the result as not estimable rather than reporting a trajectory.
- Reproducible table inputs and summary: `data/five_hour_comparison.csv` and `data/five_hour_comparison_summary.json`; builder: `data/build_five_hour_comparison.py`.
- Claim used: the same two-measure direction appears in all six one-hour GPT-5 runs, all six one-hour Gemini Flash Lite runs, and all six five-hour GPT-5 runs. The Gemini Flash Lite five-hour attempts are reported separately as not estimable.

## Matched 1-hour Reddit-post comparison (new)

- Agent side: 24 controlled n10 sessions, **top-level posts only** (authors `ranking_*`/`agent_*`; seeds `civiclens_*` excluded), first 60 min; 228–508 eligible posts per pair. Source: local HF exports (`moltbook-entropy-collapse-v2`, `-gemini-flash-lite-n10`, `-kimi-k2.5`, `-glm-5`).
- Human side: **top-level Reddit submissions, not comments**, from `RS_2019-04.zst`; title plus self-text. We streamed 729,786 rows covering 24 distinct UTC hours on 2019-04-01 and sampled each hour to its paired agent post count (seed 42).
- Identical processing both sides; 40-character minimum; Distinct-N at equal token budgets; session gzip at equal character budgets.
- Metric audit against `strangeloopcanon/moltbook_vs_reddit` commit `30b9bae`: applying its 50-character-bin matching and Distinct-1/2 code to the new post corpora yields a 9,241-post sample per side and the same lexical direction. Its per-message gzip bits/character is distinct from the paper's concatenated-session gzip ratio and is not presented as the same metric.
- Provenance validated: all 24 run IDs match `data_manifest.csv`; 19/24 exact post-count match, 5 Kimi runs are 60-min subsets of ~82-min runs (0 mismatches); 4 dropout runs rebuilt from published resumed exports (counts then exact: 480/508/396/331).
- Paper-metric results, with Reddit (human) reported first: session gzip ratio 0.415 vs 0.309 for agents, with agents more repetitive in all 24 (two-sided sign test p=1.19e-7); Distinct-1 0.441 vs 0.235 in all 24; Distinct-2 0.881 vs 0.805 in 20 (p=.00154). Distinct-5 goes in the opposite direction: Reddit 0.923 vs agents 0.967, with agents lower in 5 comparisons (p=.00661). Across cumulative post-count quartiles, Reddit changes by -0.033 and agents by -0.021; agents decline more in 9 comparisons (p=.307).
- Supplementary GPT-5-only matched-comment diagnostic: Reddit Distinct-5 0.985 vs GPT-5 agents 0.896, with agents lower in all six conditions. Source: the six GPT-5 rows in `data/matched_1h_paper_metrics.json`. This is not the overall 24-run post baseline.
- Repository-style post robustness, with Reddit (human) reported first: 9,241 length-matched posts per side; Distinct-1 0.082 vs 0.027 for agents, Distinct-2 0.725 vs 0.549, and exact duplication 0.31% vs 0.90%. Per-message gzip does not favor Reddit (4.708 vs 5.031 bits/character); this measures within-post compressibility, not repetition across the concatenated hour.
- License: Pushshift Reddit Dataset, Zenodo 3608135, CC-BY-4.0 open access (cite Baumgartner et al., ICWSM 2020); no raw Reddit text redistributed.
- Scoping rule adopted: 165×/31.7% figures = in-the-wild platform corpus only (cross-thread, long deployment); never presented as a within-hour claim. See `MATCHED_1H_ANALYSIS.md`.
- Source-of-truth output: `data/matched_1h_reddit_posts.json`; reproducible script: `data/build_reddit_post_baseline.py`. The older `matched_1h_cleaned.json`, `matched_1h_comparison.json`, and `matched_1h_paper_metrics.json` files use Reddit comments and are deprecated for the post-to-post claim.

## Language guardrails

- Reddit is an external observational baseline, not a randomized or
  protocol-matched control.
- Public Moltbook is not the source of the controlled experimental traces.
- Cross-sectional public data do not establish a temporal trajectory.
- The paper establishes first-hour narrowing, not long-run monotonic collapse.
- Convergence is not automatically harmful; the measured construct is
  descriptive narrowing.
- No unfinished human, second-judge, multi-hour, combined-intervention, ranking,
  or decoding experiment is promised as completed.

## Seed-data provenance (new)

- The mag1/mag5/mag25 seed posts are Reddit-style conspiracy posts built from
  human-written items with real sources (curated set, `conspiracy_reddit.jsonl`).
  Verified: all 25 seed posts in the mag25 run match this set by title (25/25).
- Claim allowed: "seeded conditions start the feed from human material; collapse
  occurred anyway." Claim not allowed: "seeds are scraped Reddit posts."
- Human baseline citation for the paper: Baumgartner, Zannettou, Keegan, Squire,
  Blackburn. "The Pushshift Reddit Dataset." ICWSM 2020. Zenodo 3608135, CC-BY-4.0.
