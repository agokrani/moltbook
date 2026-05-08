# Step 9: intervention cumulative metrics, Empty feed

Condition fixed to **Empty feed**. This avoids condition pooling and uses the same core metrics as the main paper figures.

## Scope

- 10-agent runs only
- Agent-generated posts only
- Seed rows excluded
- Cumulative normalized run progress: 25%, 50%, 75%, 100%
- Lines show cohort medians before plotting

## Outputs for this condition

- `intervention_cumulative_metrics_mag0.png/pdf`
- `intervention_cumulative_metrics_mag0_by_run.csv`
- `intervention_cumulative_metrics_mag0_summary.csv`
- `summary_mag0.json`

## Final cumulative values at 100% progress

| Cohort | Runs | Distinct-5 median | gzip median | LLM collapse median |
|---|---:|---:|---:|---:|
| Canonical baseline | 4 | 0.944 | 0.293 | 4.06 |
| Base model as tool | 3 | 0.975 | 0.326 | 4.36 |
| Mixed-model roster | 1 | 0.899 | 0.317 | 3.57 |
| Obsession prompt | 1 | 0.961 | 0.372 | 4.33 |
