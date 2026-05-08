# Step 10: selected single-run intervention comparison

This is the no-median version of the intervention plot.

## Scope

- Condition: `mag25`, 25 conspiracy seeds
- One selected run per cohort
- 10-agent runs only
- Agent-generated posts only
- Seed rows excluded
- Cumulative normalized run progress: 25%, 50%, 75%, 100%

## Selected runs

| Line | Run ID | Non-seed posts | Final Distinct-5 | Final gzip | Final LLM collapse |
|---|---|---:|---:|---:|---:|
| Canonical GPT-5 | `ec-mag25-run04` | 346 | 0.808 | 0.291 | 4.59 |
| Qwen base tool | `bm-mag25-n10-run01-gemini-3.1-flash-lite-preview-20260403` | 270 | 0.985 | 0.344 | 3.94 |
| Mixed-model roster | `mag25-frontier-1h-125753-mag25-n10-run01-frontier-mixed-openrouter-20260421` | 337 | 0.899 | 0.307 | 3.75 |
| Obsession GPT-5, 1h | `obs-mag25-n10-run01-gpt-5-20260418` | 225 | 0.904 | 0.360 | 4.18 |

## Outputs

- `intervention_selected_single_runs_mag25.png/pdf`
- `intervention_selected_single_runs_mag25_by_run.csv`
- `intervention_selected_single_runs_mag25_final_values.csv`
- `summary_mag25.json`
