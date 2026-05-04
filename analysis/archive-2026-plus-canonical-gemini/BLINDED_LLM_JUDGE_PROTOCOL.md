# Blinded LLM-as-a-Judge Protocol

This is the safe protocol if LLM-as-a-judge is re-enabled for the archive main groups.

## What the judge sees

The prompt contains only anonymized text:

- one target post,
- earlier anonymized posts from the same local timeline,
- anonymized semantically nearby posts.

The prompt does **not** contain group, model, condition, run name, source path, dataset source, or cluster metadata.

## How group analysis still works

Judgments are made independently at the row/post level using only a blind `row_uid`. After the API returns, a local join file maps `row_uid` back to metadata. Group summaries are then computed post-hoc.

So the judge is **not** asked to analyze a group. Instead:

1. score each sampled post blindly;
2. locally join scores to `base-model`, `entropy-collapse`, or `obsession`;
3. aggregate within each group and compare groups.

This supports both individual group review and between-group summaries without leaking group labels into the prompt.

## Commands

```bash
python3 scripts/archive-2026-llm-judge.py sample-blind --posts-per-cell 4 --min-per-cluster 8 --max-rows 1800
python3 scripts/archive-2026-llm-judge.py audit-prompts
python3 scripts/archive-2026-llm-judge.py judge --model google/gemini-3.1-flash-lite-preview
python3 scripts/archive-2026-llm-judge.py aggregate --model google/gemini-3.1-flash-lite-preview
```

`audit-prompts` fails if forbidden metadata keys appear in the blinded sample or generated prompts.
