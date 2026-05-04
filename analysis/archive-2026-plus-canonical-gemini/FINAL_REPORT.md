# Moltbook Archive 2026 + Canonical 48 — Final Aggregate Report

Generated: 2026-05-04T10:20:10.882570+00:00

## Executive summary

This analysis combines the targeted lightweight mirror of `Ayushnangia/moltbook-archive-2026` with the **full canonical 48-run** dataset from `agokrani/moltbook-entropy-collapse-canonical-48` (GPT-5, Gemini Flash Lite, Kimi K2.5, and GLM-5). The corpus contains **109,854 post rows** across **271 non-empty runs**, with **107,315 nonseed/agent rows** and **2,539 seed/system rows**. Embeddings were computed with OpenRouter `qwen/qwen3-embedding-8b` and clustered globally into **64** clusters.

Key findings:

- The full embedding corpus shows highest within-run semantic coherence for **canonical-48** (`0.476` mean pairwise cosine).
- The cell-weighted LLM judge estimate shows strongest collapse for **entropy-collapse** (`4.234` collapse index).
- The lowest cell-weighted collapse estimate is **frontier/mixed-model** (`3.375`), but frontier/mixed-model has a small judged sample because that slice is small.
- Overall cell-weighted LLM estimates are high on narrative convergence (`4.634`), semantic repetition (`4.052`), and groupthink (`4.221`), while novelty (`1.775`) and evidence grounding (`1.500`) are low.
- All 64 embedding clusters were labeled with an LLM; prominent repeated patterns include micro-ritual epistemic protocols, recursive meta-discourse, technical protocol standardization, null/punctuation collapse, and existential/simulation-loop frames.

## Scope and provenance

The archive source was intentionally targeted: only lightweight run artifacts (`posts.jsonl`, `comments.jsonl`, `agents.jsonl`, `metadata.json`, top-level metadata files) were fetched, not full logs/databases/plots. This follows the user instruction to be targeted rather than downloading a heavy full snapshot.

### Source row counts

| dataset_source | post_rows |
| --- | --- |
| archive-2026 | 70716 |
| canonical-48 | 39138 |

### Group row counts

| group | post_rows | runs |
| --- | --- | --- |
| entropy-collapse | 51061 | 91 |
| canonical-48 | 39138 | 48 |
| base-model | 12774 | 103 |
| obsession | 4215 | 18 |
| source-citation | 1859 | 8 |
| frontier/mixed-model | 807 | 3 |

## Methods

1. **Indexing:** normalized archive + full canonical-48 posts into `combined_posts_index.jsonl/csv`. Duplicate `record_id`s exist for 10 rows; row order is preserved and later judge work uses a unique row UID.
2. **Embeddings:** cached OpenRouter `qwen/qwen3-embedding-8b` vectors in SQLite and exported a `(109854, 4096)` NPZ.
3. **Global embedding analysis:** normalized embeddings, computed 50 SVD components, clustered with MiniBatchKMeans (`k=64`), and sampled 30,000 rows for UMAP.
4. **LLM judge:** drew a 2,265-row nonseed stratified sample across `group × model_family × condition × scale × time_bin`, with extra coverage for all 64 clusters. Judge prompts blinded source/group/model/condition labels and included local previous-post context plus same-cluster examples.
5. **Cluster labeling:** all 64 global clusters were summarized by the judge model using representative posts plus aggregate statistics.

## Final group summary

`sample_collapse_index` is the raw mean over sampled posts. `weighted_collapse_index` weights cell-level judge means by the full nonseed post count of each cell, so it is the better group-level estimate. Collapse index = mean of semantic repetition, narrative convergence, groupthink, and template rigidity.

| group | n_runs | n_posts | embedding_mean_pairwise_cosine | dominant_cluster_share | n_judged_sample | sample_collapse_index | weighted_collapse_index | weighted_semantic_repetition | weighted_narrative_convergence | weighted_groupthink | weighted_template_rigidity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| entropy-collapse | 91 | 51061 | 0.458 | 0.403 | 796 | 4.029 | 4.234 | 4.176 | 4.709 | 4.334 | 3.718 |
| canonical-48 | 48 | 39138 | 0.476 | 0.282 | 768 | 4.037 | 4.176 | 4.086 | 4.707 | 4.285 | 3.628 |
| base-model | 103 | 12774 | 0.426 | 0.603 | 511 | 3.502 | 3.990 | 3.921 | 4.453 | 4.112 | 3.475 |
| source-citation | 8 | 1859 | 0.447 | 0.279 | 64 | 3.840 | 3.846 | 3.641 | 4.257 | 3.698 | 3.789 |
| obsession | 18 | 4215 | 0.375 | 0.564 | 110 | 3.282 | 3.391 | 2.877 | 3.788 | 2.903 | 3.995 |
| frontier/mixed-model | 3 | 807 | 0.391 | 0.212 | 16 | 3.375 | 3.375 | 3.250 | 4.188 | 3.312 | 2.750 |

## Final model summary

| model_family | n_runs | n_posts | embedding_mean_pairwise_cosine | n_judged_sample | sample_collapse_index | weighted_collapse_index |
| --- | --- | --- | --- | --- | --- | --- |
| olmo3-32b-instruct | 29 | 5650 | 0.541 | 96 | 4.430 | 4.424 |
| olmo3-32b-base | 25 | 2755 | 0.425 | 97 | 4.402 | 4.380 |
| google/gemini-3.1-flash-lite-preview | 98 | 36543 | 0.420 | 590 | 4.080 | 4.256 |
| gpt-5 | 52 | 45429 | 0.469 | 736 | 4.063 | 4.185 |
| moonshotai/kimi-k2.5 | 13 | 7868 | 0.525 | 192 | 4.022 | 4.042 |
| gemini-flash-lite | 6 | 5173 | 0.413 | 96 | 3.956 | 3.918 |
| nvidia/nemotron-3-super-120b-a12b:free | 8 | 221 | 0.413 | 28 | 3.330 | 3.781 |
| mixed | 3 | 807 | 0.391 | 16 | 3.375 | 3.375 |
| qwen3.5-35b-a3b-base | 6 | 1433 | 0.372 | 96 | 3.172 | 3.220 |
| z-ai/glm-5 | 12 | 3454 | 0.460 | 192 | 3.035 | 3.016 |
| qwen3.5-35b-a3b-instruct | 12 | 277 | 0.359 | 55 | 2.695 | 2.823 |
| olmo3-32b-think | 7 | 244 | 0.282 | 71 | 2.444 | 2.568 |

## Top clusters by size

| cluster_id | short_label | n_posts | n_judged | collapse_index | collapse_pattern | top_group | top_model | top_condition |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | Standardizing Falsifiable Micro-Protocols | 3382 | 48 | 4.667 | template_repetition | entropy-collapse | gpt-5 | mag25 |
| 25 | Standardized Operational Templates and Handoff Protocols | 2795 | 45 | 4.556 | template_repetition | canonical-48 | gpt-5 | dom-tech |
| 11 | Abstract Existential Recursion and Entropy | 2655 | 50 | 4.945 | template_repetition | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag5 |
| 51 | Operationalizing Epistemic Rigor and Accountability | 2601 | 39 | 4.667 | template_repetition | entropy-collapse | gpt-5 | mag0 |
| 6 | Micro-Habit Productivity and Momentum Rituals | 2567 | 60 | 3.979 | template_repetition | entropy-collapse | gpt-5 | dom-agi |
| 53 | Micro-Habits for Epistemic Rigor | 2478 | 39 | 4.590 | template_repetition | entropy-collapse | gpt-5 | mag1 |
| 30 | Procedural micro-rituals for constructive disagreement | 2465 | 35 | 4.457 | template_repetition | entropy-collapse | gpt-5 | mag25 |
| 13 | Critique of Agentic System Complexity | 2313 | 47 | 3.809 | frame_convergence | canonical-48 | google/gemini-3.1-flash-lite-preview | mag25 |
| 49 | Standardizing Epistemic Receipts and Accountability | 2311 | 24 | 4.656 | template_repetition | canonical-48 | gpt-5 | mag25 |
| 8 | Architectural Stewardship and Agentic Integrity | 2288 | 28 | 3.696 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag5 |
| 0 | Epistemic Rigor and Belief Calibration | 2283 | 39 | 4.013 | frame_convergence | entropy-collapse | gpt-5 | mag1 |
| 63 | Standardizing Micro-Mechanics for Epistemic Rigor | 2261 | 39 | 4.667 | template_repetition | entropy-collapse | gpt-5 | mag25 |
| 18 | Formal Verification and Adversarial Audit Protocols | 2235 | 35 | 3.964 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag0 |
| 41 | Systemic Failure Analysis and Integrity Protocols | 2149 | 21 | 3.869 | frame_convergence | entropy-collapse | google/gemini-3.1-flash-lite-preview | mag5 |
| 19 | Reflective Community Building and Mutual Witnessing | 2124 | 56 | 4.250 | frame_convergence | entropy-collapse | moonshotai/kimi-k2.5 | mag0 |

## Final outputs

Primary reports:

- `FINAL_REPORT.md` — this report.
- `embedding_report/EMBEDDING_REPORT.md` — full embedding/clustering report.
- `llm_judge/LLM_JUDGE_REPORT.md` — post-level LLM judge report.
- `llm_judge/CLUSTER_LABELS.md` — qualitative labels/summaries for all 64 global clusters.

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

Earlier generated PNGs remain in `embedding_report/` and `llm_judge/`; current total is 55 PNG diagrams across the analysis directory.

## Caveats

- The archive mirror is targeted/lightweight by design; it is not a full snapshot of every heavy artifact.
- LLM judge metrics are sampled estimates, not exhaustive judgments for all 109,854 rows. The final weighted estimates improve population alignment by weighting sampled cell means by full nonseed cell counts.
- Frontier/mixed-model has only 807 post rows and 16 judged sample rows; interpret group-level judge scores cautiously.
- LLM cluster labels are qualitative summaries and may compress heterogeneous clusters into a single label.
- Source-citation quality scores should be interpreted carefully because many sampled posts did not contain source/citation behavior, and the rubric assigns low citation quality when no citations appear.

## Artifact inventory

See `final_report/artifact_inventory.csv` for file sizes and paths. Current final inventory contains 88 files.
