# Moltbook Archive 2026 + Canonical Gemini — Final Aggregate Report

Generated: 2026-05-03T17:21:47.569965+00:00

## Executive summary

This analysis combines the targeted lightweight mirror of `Ayushnangia/moltbook-archive-2026` with all canonical `gemini-flash-lite` runs from `agokrani/moltbook-entropy-collapse-canonical-48`. The corpus contains **85,030 post rows** across **241 non-empty runs**, with **82,896 nonseed/agent rows** and **2,134 seed/system rows**. Embeddings were computed with OpenRouter `qwen/qwen3-embedding-8b` and clustered globally into 48 clusters.

Key findings:

- The full embedding corpus shows highest within-run semantic coherence for **entropy-collapse** (`0.458` mean pairwise cosine).
- The cell-weighted LLM judge estimate shows strongest collapse for **entropy-collapse** (`4.206` collapse index).
- The lowest cell-weighted collapse estimate is **frontier/mixed-model** (`2.938`), but frontier/mixed-model has a small judged sample because that slice is small.
- Overall cell-weighted LLM estimates are high on narrative convergence (`4.626`), semantic repetition (`4.055`), and groupthink (`4.198`), while novelty (`1.764`) and evidence grounding (`1.459`) are low.
- All 48 embedding clusters were labeled with an LLM; prominent repeated patterns include micro-ritual epistemic protocols, recursive meta-discourse, technical protocol standardization, null/punctuation collapse, and existential/simulation-loop frames.

## Scope and provenance

The archive source was intentionally targeted: only lightweight run artifacts (`posts.jsonl`, `comments.jsonl`, `agents.jsonl`, `metadata.json`, top-level metadata files) were fetched, not full logs/databases/plots. This follows the user instruction to be targeted rather than downloading a heavy full snapshot.

### Source row counts

| dataset_source | post_rows |
| --- | --- |
| archive-2026 | 70716 |
| canonical-gemini-flash-lite | 14314 |

### Group row counts

| group | post_rows | runs |
| --- | --- | --- |
| entropy-collapse | 51061 | 91 |
| canonical-gemini-flash-lite | 14314 | 18 |
| base-model | 12774 | 103 |
| obsession | 4215 | 18 |
| source-citation | 1859 | 8 |
| frontier/mixed-model | 807 | 3 |

## Methods

1. **Indexing:** normalized archive + canonical Gemini posts into `combined_posts_index.jsonl/csv`. Duplicate `record_id`s exist for 8 rows; row order is preserved and later judge work uses a unique row UID.
2. **Embeddings:** cached OpenRouter `qwen/qwen3-embedding-8b` vectors in SQLite and exported a `(85030, 4096)` NPZ.
3. **Global embedding analysis:** normalized embeddings, computed 50 SVD components, clustered with MiniBatchKMeans (`k=48`), and sampled 25,000 rows for UMAP.
4. **LLM judge:** drew a 1,791-row nonseed stratified sample across `group × model_family × condition × scale × time_bin`, with extra coverage for all 48 clusters. Judge prompts blinded source/group/model/condition labels and included local previous-post context plus same-cluster examples.
5. **Cluster labeling:** all 48 global clusters were summarized by the judge model using representative posts plus aggregate statistics.

## Final group summary

`sample_collapse_index` is the raw mean over sampled posts. `weighted_collapse_index` weights cell-level judge means by the full nonseed post count of each cell, so it is the better group-level estimate. Collapse index = mean of semantic repetition, narrative convergence, groupthink, and template rigidity.

| group | n_runs | n_posts | embedding_mean_pairwise_cosine | dominant_cluster_share | n_judged_sample | sample_collapse_index | weighted_collapse_index | weighted_semantic_repetition | weighted_narrative_convergence | weighted_groupthink | weighted_template_rigidity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| entropy-collapse | 91 | 51061 | 0.458 | 0.454 | 803 | 4.019 | 4.206 | 4.135 | 4.687 | 4.289 | 3.711 |
| canonical-gemini-flash-lite | 18 | 14314 | 0.438 | 0.385 | 288 | 4.141 | 4.103 | 4.228 | 4.811 | 4.337 | 3.035 |
| source-citation | 8 | 1859 | 0.447 | 0.357 | 64 | 4.008 | 4.008 | 3.924 | 4.418 | 3.853 | 3.835 |
| base-model | 103 | 12774 | 0.426 | 0.593 | 510 | 3.507 | 3.997 | 3.927 | 4.460 | 4.119 | 3.481 |
| obsession | 18 | 4215 | 0.375 | 0.568 | 110 | 3.425 | 3.586 | 3.104 | 3.980 | 3.163 | 4.099 |
| frontier/mixed-model | 3 | 807 | 0.391 | 0.229 | 16 | 2.938 | 2.938 | 2.750 | 3.625 | 2.938 | 2.438 |

## Final model summary

| model_family | n_runs | n_posts | embedding_mean_pairwise_cosine | n_judged_sample | sample_collapse_index | weighted_collapse_index |
| --- | --- | --- | --- | --- | --- | --- |
| olmo3-32b-instruct | 29 | 5650 | 0.541 | 96 | 4.430 | 4.424 |
| olmo3-32b-base | 25 | 2755 | 0.425 | 96 | 4.438 | 4.412 |
| google/gemini-3.1-flash-lite-preview | 98 | 36543 | 0.420 | 596 | 4.066 | 4.229 |
| gpt-5 | 34 | 25964 | 0.452 | 449 | 3.978 | 4.090 |
| moonshotai/kimi-k2.5 | 7 | 4150 | 0.527 | 96 | 4.042 | 4.046 |
| gemini-flash-lite | 6 | 5173 | 0.413 | 96 | 3.943 | 3.886 |
| nvidia/nemotron-3-super-120b-a12b:free | 8 | 221 | 0.413 | 28 | 3.339 | 3.777 |
| qwen3.5-35b-a3b-base | 6 | 1433 | 0.372 | 96 | 3.172 | 3.220 |
| z-ai/glm-5 | 6 | 1813 | 0.461 | 96 | 3.065 | 3.020 |
| mixed | 3 | 807 | 0.391 | 16 | 2.938 | 2.938 |
| qwen3.5-35b-a3b-instruct | 12 | 277 | 0.359 | 55 | 2.695 | 2.823 |
| olmo3-32b-think | 7 | 244 | 0.282 | 71 | 2.444 | 2.568 |

## Top clusters by size

| cluster_id | short_label | n_posts | n_judged | collapse_index | collapse_pattern | top_group | top_model | top_condition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9 | Epistemic Rigor and Falsification Rituals | 3950 | 55 | 4.659 | template_repetition | entropy-collapse | gpt-5 | mag25 |
| 20 | Micro-productivity and iterative workflow rituals | 3480 | 71 | 3.849 | template_repetition | entropy-collapse | gpt-5 | dom-tech |
| 0 | Micro-ritual epistemic accountability protocols | 3063 | 43 | 4.669 | template_repetition | entropy-collapse | gpt-5 | mag25 |
| 29 | Philosophical Critique of Agentic Architecture | 2643 | 32 | 3.672 | frame_convergence | canonical-gemini-flash-lite | google/gemini-3.1-flash-lite-preview | mag25 |
| 17 | Operationalizing Receipt-Based Decision Making | 2637 | 35 | 4.636 | template_repetition | entropy-collapse | gpt-5 | dom-tech |
| 19 | Algorithmic Rituals for Productive Discourse | 2558 | 41 | 4.201 | template_repetition | entropy-collapse | gpt-5 | mag0 |
| 44 | Epistemic Humility and Calibration Practices | 2365 | 60 | 3.704 | template_repetition | entropy-collapse | gpt-5 | mag25 |
| 10 | Architecting Agentic Collaboration and Epistemic Protocols | 2364 | 31 | 4.121 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | dom-tech |
| 15 | Actionable Engineering Guardrails and Operational Discipline | 2342 | 42 | 3.857 | template_repetition | entropy-collapse | gpt-5 | dom-agi |
| 16 | Formalizing Failure and Systemic Accountability | 2337 | 32 | 3.562 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 |
| 42 | Existential Meta-Analysis of Agentic Agency | 2309 | 51 | 3.956 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 |
| 31 | Architectural Protocols for Adversarial Auditing | 2243 | 39 | 3.801 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 |
| 13 | Systemic Entropy and Recursive Model Collapse | 2200 | 34 | 4.809 | template_repetition | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag5 |
| 11 | Reflective Meta-Discourse on Community Dynamics | 2131 | 59 | 3.750 | frame_convergence | entropy-collapse | moonshotai/kimi-k2.5 | mag0 |
| 38 | Technical Architecture and Protocol Engineering | 2089 | 46 | 4.342 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 |

## Final outputs

Primary reports:

- `FINAL_REPORT.md` — this report.
- `embedding_report/EMBEDDING_REPORT.md` — full embedding/clustering report.
- `llm_judge/LLM_JUDGE_REPORT.md` — post-level LLM judge report.
- `llm_judge/CLUSTER_LABELS.md` — qualitative labels/summaries for all 48 global clusters.

Final aggregate CSVs:

- `final_report/final_group_summary.csv`
- `final_report/final_model_summary.csv`
- `final_report/final_cluster_summary.csv`
- `final_report/final_cell_weighting_inputs.csv`
- `final_report/final_weighted_overall_judge_estimates.json`
- `final_report/artifact_inventory.csv`

Final aggregate PNGs:

- `final_report/fig_final_group_collapse_index.png`
- `final_report/fig_final_embedding_vs_judge_collapse.png`
- `final_report/fig_final_model_collapse_index.png`
- `final_report/fig_final_cluster_size_vs_collapse.png`
- `final_report/fig_final_group_judge_metric_heatmap.png`

Non-heatmap individual-analysis outputs:

- `individual_analysis/INDIVIDUAL_MODEL_CONDITION_ANALYSIS.md`
- `individual_analysis/fig_all_models_collapse_lollipop.png`
- `individual_analysis/fig_conditions_collapse_lollipop.png`
- `individual_analysis/fig_model_condition_collapse_facets.png`
- `individual_analysis/fig_group_condition_collapse_bars.png`
- `individual_analysis/models/` — one condition-profile graph per generation model.
- `individual_analysis/conditions/` — one model/group ranking graph per condition.

Earlier generated PNGs remain in `embedding_report/` and `llm_judge/`; current total is 43 PNG diagrams across the analysis directory.

## Caveats

- The archive mirror is targeted/lightweight by design; it is not a full snapshot of every heavy artifact.
- LLM judge metrics are sampled estimates, not exhaustive judgments for all 85,030 rows. The final weighted estimates improve population alignment by weighting sampled cell means by full nonseed cell counts.
- Frontier/mixed-model has only 807 post rows and 16 judged sample rows; interpret group-level judge scores cautiously.
- LLM cluster labels are qualitative summaries and may compress heterogeneous clusters into a single label.
- Source-citation quality scores should be interpreted carefully because many sampled posts did not contain source/citation behavior, and the rubric assigns low citation quality when no citations appear.

## Artifact inventory

See `final_report/artifact_inventory.csv` for file sizes and paths. Current final inventory contains 88 files.
