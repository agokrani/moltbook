# Step 9: intervention cumulative metrics, 25 AGI seeds

Condition fixed to **25 AGI seeds**. This avoids condition pooling and uses the same core metrics as the main paper figures.

## Scope

- 10-agent runs only
- Agent-generated posts only
- Seed rows excluded
- Cumulative normalized run progress: 25%, 50%, 75%, 100%
- Lines show cohort medians before plotting

## Outputs for this condition

- `intervention_cumulative_metrics_dom-agi.png/pdf`
- `intervention_cumulative_metrics_dom-agi_by_run.csv`
- `intervention_cumulative_metrics_dom-agi_summary.csv`
- `summary_dom-agi.json`

## Final cumulative values at 100% progress

| Cohort | Runs | Distinct-5 median | gzip median | LLM collapse median |
|---|---:|---:|---:|---:|
| Canonical baseline | 4 | 0.908 | 0.293 | 4.23 |
| Base model as tool | 3 | 0.976 | 0.327 | 4.66 |
| Mixed-model roster | 1 | 0.903 | 0.302 | 3.56 |
| Obsession prompt | 1 | 0.953 | 0.375 | 4.23 |
