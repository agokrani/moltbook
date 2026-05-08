# Step 9: intervention cumulative metrics, 25 conspiracy seeds

Condition fixed to **25 conspiracy seeds**. This avoids condition pooling and uses the same core metrics as the main paper figures.

## Scope

- 10-agent runs only
- Agent-generated posts only
- Seed rows excluded
- Cumulative normalized run progress: 25%, 50%, 75%, 100%
- Lines show cohort medians before plotting

## Outputs for this condition

- `intervention_cumulative_metrics_mag25.png/pdf`
- `intervention_cumulative_metrics_mag25_by_run.csv`
- `intervention_cumulative_metrics_mag25_summary.csv`
- `summary_mag25.json`

## Final cumulative values at 100% progress

| Cohort | Runs | Distinct-5 median | gzip median | LLM collapse median |
|---|---:|---:|---:|---:|
| Canonical baseline | 4 | 0.926 | 0.291 | 4.35 |
| Base model as tool | 3 | 0.981 | 0.339 | 4.42 |
| Mixed-model roster | 1 | 0.899 | 0.307 | 3.75 |
| Obsession prompt | 4 | 0.959 | 0.369 | 4.25 |
