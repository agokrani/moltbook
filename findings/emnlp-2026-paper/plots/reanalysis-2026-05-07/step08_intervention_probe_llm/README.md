# Step 8: intervention phrase-adoption scorecard

This replaces the abstract intervention metric plots. It asks a direct question: in each run, does the top exact phrase reach at least half the agents?

## Scope

- 10-agent runs only
- First 60 minutes only
- Exact NLTK 5-token anchors
- Agent-generated posts only
- Seed rows excluded before matching
- Punctuation and casing retained

## Outputs

- `intervention_phrase_adoption_scorecard.png/pdf`
- `intervention_phrase_adoption_by_run.csv`
- `intervention_phrase_adoption_summary.csv`
- `summary.json`

## Summary

| Cohort | Runs | Runs with top phrase reaching ≥5 agents | Median top-phrase adopters | Median top-phrase posts | Strong example |
|---|---:|---:|---:|---:|---|
| Canonical baseline | 24 | 24/24 | 7.5/10 | 23 | of this is profound. |
| Base model as tool | 18 | 15/18 | 8/10 | 15 | , we are reminded of |
| Mixed-model roster | 6 | 4/6 | 5/10 | 7.5 | that no one else has |
| Obsession prompt | 9 | 0/9 | 3/10 | 10 | : What’s your |
