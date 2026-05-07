# External / bundled scripts used by reanalysis plotting

The 2026-05-05 reanalysis dataset includes the original Ayush reanalysis scripts under:

```text
data/reanalysis-2026-05-05/scripts/
```

Relevant bundled scripts:

```text
data/reanalysis-2026-05-05/scripts/ayush-analysis-plan-execute.py
data/reanalysis-2026-05-05/scripts/ayush-topic-convergence.py
data/reanalysis-2026-05-05/scripts/ayush-blind-llm-judge.py
data/reanalysis-2026-05-05/scripts/ayush-finalize-judge-results.py
data/reanalysis-2026-05-05/scripts/ayush-final-report.py
```

Original development worktree / branch provenance for these scripts:

```text
worktree: /Users/agokrani/Documents/git/moltbook-obsession-frontier-mixed-and-archive
branch: obsession-frontier-mixed-and-archive
commit: bad88a8
```

The new paper-facing topic robustness script is local to this repository:

```text
scripts/reanalysis-2026-05-05/build_topic_robustness.py
```

It reuses the cleaned embedding NPZ and post index from the HF bundle and does not make API calls.
