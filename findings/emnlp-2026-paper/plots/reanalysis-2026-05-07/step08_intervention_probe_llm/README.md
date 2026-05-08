# Step 8: concrete intervention-probe phrase examples

This replaces the abstract intervention metric plots.

## Scope

- Secondary cohort examples
- 10-agent runs only
- First 60 minutes only
- Exact NLTK 5-token anchors
- Agent-generated posts only
- Seed rows excluded before matching

## Outputs

- `intervention_probe_phrase_examples.png/pdf`
- `intervention_probe_phrase_examples.csv`
- `summary.json`

## Examples

| Cohort | Phrase | Posts | Agents | Reading |
|---|---|---:|---:|---|
| Base model as tool | As we stand on the | 42 | 9/10 | The base-model probe still develops a shared grand-opening frame. |
| Mixed-model roster | that no one else has | 11 | 6/10 | Different models still coordinate around a shared prompt-like question. |
| Obsession prompt | Question: What’s your... | 85 | 4/10 | The prompt intervention still produces a repeated question frame. |

## Caution

These are concrete examples, not matched causal estimates.
