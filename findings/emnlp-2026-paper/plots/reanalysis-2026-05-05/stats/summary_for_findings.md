# Statistical table summary

All signs are run-level. Positive collapse score means more collapse in the metric-specific direction.

## Canonical model direction tests

| Model | Vendi collapse count | LLM collapse count | HHI concentration count |
|---|---:|---:|---:|
| GPT-5 | 16/18 | 18/18 | 15/18 |
| Gemini Flash Lite | 16/18 | 16/18 | 16/18 |
| Kimi K2.5 | 5/6 | 6/6 | 1/6 |
| GLM-5 | 5/6 | 6/6 | 3/6 |

## Scale, n30 minus n10

| Metric | Model | Median collapse difference | Sign count |
|---|---|---:|---:|
| Gzip | GPT-5 | +0.021 | 5/6 |
| Gzip | Gemini Flash Lite | +0.034 | 5/6 |
| Vendi | GPT-5 | -0.115 | 2/6 |
| Vendi | Gemini Flash Lite | +0.615 | 5/6 |
| LLM collapse index | GPT-5 | -0.010 | 3/6 |
| LLM collapse index | Gemini Flash Lite | +0.136 | 4/6 |
| HHI concentration | GPT-5 | -0.091 | 2/6 |
| HHI concentration | Gemini Flash Lite | +0.033 | 4/6 |