# Archive 2026 Main Groups — Embedding-Only Final Report

Generated: 2026-05-04T11:09:34.940295+00:00

## Scope

This cleaned review package is **embedding-only** and includes only the main archive groups:

- `base-model`
- `entropy-collapse`
- `obsession`

Excluded by design:

- `source-citation` / site-citation smoke runs
- `frontier/mixed-model` roster/mixed runs
- `canonical-48` and canonical Gemini comparison runs
- all LLM-as-a-judge outputs

## Why LLM-as-a-judge is excluded

LLM-as-a-judge results are not used in this main package. Earlier judge prompts/context could expose group/source cues through context metadata, so we removed those outputs rather than reporting potentially confounded judge scores.

If judge scoring is re-enabled, it must use the blinded row-level protocol in `BLINDED_LLM_JUDGE_PROTOCOL.md`: the model receives no group/model/condition/run/source metadata, scores individual posts only, and group summaries are computed locally after joining scores back to metadata.

## Corpus

- Post rows: **68,050**
- Nonseed/agent rows: **66,394**
- Seed/system rows: **1,656**
- Non-empty runs: **212**
- Embedding NPZ shape: **(68050, 4096)**
- Global embedding clusters: **48**

## Key embedding result

The highest within-run semantic coherence is **entropy-collapse** with mean pairwise cosine **0.458**.

## Group counts

| group | post_rows | runs |
| --- | --- | --- |
| entropy-collapse | 51061 | 91 |
| base-model | 12774 | 103 |
| obsession | 4215 | 18 |

## Model counts

| model_family | post_rows | runs |
| --- | --- | --- |
| google/gemini-3.1-flash-lite-preview | 27402 | 86 |
| gpt-5 | 24105 | 26 |
| olmo3-32b-instruct | 5650 | 29 |
| moonshotai/kimi-k2.5 | 4150 | 7 |
| olmo3-32b-base | 2755 | 25 |
| z-ai/glm-5 | 1813 | 6 |
| qwen3.5-35b-a3b-base | 1433 | 6 |
| qwen3.5-35b-a3b-instruct | 277 | 12 |
| olmo3-32b-think | 244 | 7 |
| nvidia/nemotron-3-super-120b-a12b:free | 221 | 8 |

## Group embedding summary

| group | n_runs | n_posts | mean_pairwise_cosine | dominant_cluster_share |
| --- | --- | --- | --- | --- |
| entropy-collapse | 91 | 51061 | 0.458 | 0.473 |
| base-model | 103 | 12774 | 0.426 | 0.538 |
| obsession | 18 | 4215 | 0.375 | 0.574 |

## Model embedding summary

| model_family | n_runs | n_posts | mean_pairwise_cosine | dominant_cluster_share |
| --- | --- | --- | --- | --- |
| olmo3-32b-instruct | 29 | 5650 | 0.541 | 0.568 |
| moonshotai/kimi-k2.5 | 7 | 4150 | 0.527 | 0.421 |
| z-ai/glm-5 | 6 | 1813 | 0.461 | 0.397 |
| gpt-5 | 26 | 24105 | 0.453 | 0.314 |
| olmo3-32b-base | 25 | 2755 | 0.425 | 0.593 |
| google/gemini-3.1-flash-lite-preview | 86 | 27402 | 0.416 | 0.507 |
| nvidia/nemotron-3-super-120b-a12b:free | 8 | 221 | 0.413 | 0.821 |
| qwen3.5-35b-a3b-base | 6 | 1433 | 0.372 | 0.531 |
| qwen3.5-35b-a3b-instruct | 12 | 277 | 0.359 | 0.584 |
| olmo3-32b-think | 7 | 244 | 0.282 | 0.521 |

## Top clusters

| cluster_id | n_posts | n_runs | top_group | top_model | top_condition | seed_share | post_share |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 16 | 3420 | 48 | entropy-collapse | gpt-5 | dom-agi | 0.005 | 0.050 |
| 24 | 2429 | 23 | entropy-collapse | gpt-5 | mag25 | 0.000 | 0.036 |
| 18 | 2354 | 43 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 | 0.000 | 0.035 |
| 44 | 2319 | 66 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 | 0.000 | 0.034 |
| 0 | 2248 | 45 | entropy-collapse | gpt-5 | mag1 | 0.000 | 0.033 |
| 6 | 2175 | 91 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag25 | 0.000 | 0.032 |
| 29 | 2114 | 27 | entropy-collapse | gpt-5 | mag25 | 0.000 | 0.031 |
| 11 | 2050 | 26 | entropy-collapse | gpt-5 | dom-tech | 0.000 | 0.030 |
| 2 | 1987 | 40 | entropy-collapse | gpt-5 | dom-agi | 0.000 | 0.029 |
| 41 | 1932 | 38 | entropy-collapse | gpt-5 | mag0 | 0.000 | 0.028 |
| 38 | 1858 | 64 | entropy-collapse | moonshotai/kimi-k2.5 | mag0 | 0.000 | 0.027 |
| 12 | 1832 | 63 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag5 | 0.000 | 0.027 |
| 15 | 1808 | 27 | entropy-collapse | gpt-5 | mag25 | 0.000 | 0.027 |
| 13 | 1805 | 47 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 | 0.000 | 0.027 |
| 42 | 1701 | 27 | entropy-collapse | gpt-5 | mag1 | 0.000 | 0.025 |
| 37 | 1673 | 12 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 | 0.000 | 0.025 |
| 3 | 1637 | 90 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 | 0.000 | 0.024 |
| 47 | 1607 | 102 | entropy-collapse | google/gemini-3.1-flash-lite-preview | dom-tech | 0.000 | 0.024 |
| 7 | 1607 | 90 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag25 | 0.000 | 0.024 |
| 5 | 1584 | 40 | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 | 0.000 | 0.023 |

## Main outputs

- `FINAL_REPORT.md` — this report.
- `embedding_report/EMBEDDING_REPORT.md` — full embedding/clustering report.
- `paper_analysis/PAPER_STYLE_ANALYSIS.md` — paper-style embedding-only analysis with Vendi/MDS figures.
- `BLINDED_LLM_JUDGE_PROTOCOL.md` — optional safe judge protocol; group analysis is post-hoc only.
- `final_report/final_group_embedding_summary.csv`
- `final_report/final_model_embedding_summary.csv`
- `final_report/final_cluster_embedding_summary.csv`
- `final_report/final_run_embedding_summary.csv`
- `final_report/final_embedding_only_summary.json`

## Final PNGs

- `final_report/fig_final_group_embedding_coherence.png`
- `final_report/fig_final_group_dominant_cluster_share.png`
- `final_report/fig_final_model_embedding_coherence.png`
- `final_report/fig_final_cluster_sizes.png`

## Reproducibility

Regenerate the cleaned index and analysis with:

```bash
python3 scripts/archive-2026-combined-analysis.py index
python3 scripts/archive-2026-combined-analysis.py embed --model qwen/qwen3-embedding-8b --export-npz
python3 scripts/archive-2026-embedding-report.py --clusters 48 --umap-sample 25000 --svd-components 50
python3 scripts/archive-2026-paper-analysis.py --max-bin-n 400 --mds-sample 4000
python3 scripts/archive-2026-final-report.py
```
