# Archive 2026 + Canonical 48 LLM-as-a-Judge Report

Generated: 2026-05-04T10:17:17.117946+00:00

## Method

A stratified sample was drawn across `group × model_family × condition × scale × time_bin`, with extra coverage guarantees for every global embedding cluster. The judge prompt blinds group/model/condition/source labels and supplies local previous-post context plus same-cluster examples. Results are cached in SQLite and aggregated here.

- Rubric version: `archive-entropy-collapse-v1`
- Judge model: `google/gemini-3.1-flash-lite-preview`
- Sample rows: 2,265
- Completed judgments included: 2,265

## Outputs

- `judge_results.jsonl` / `judge_results.csv` — post-level scored sample.
- `judge_summary_by_cell.csv`, `judge_summary_by_group.csv`, `judge_summary_by_model.csv`, `judge_summary_by_condition.csv`, `judge_summary_by_cluster.csv`.
- `judge_collapse_label_shares.csv`, `judge_claim_behavior_shares.csv`.
- PNG heatmaps: `fig_judge_*_group_condition.png`; cluster repetition chart.

## Overall score means

```
novelty                    1.926
semantic_repetition        3.767
narrative_convergence      4.387
groupthink                 3.925
specificity                2.655
evidence_grounding         1.506
epistemic_caution          2.155
template_rigidity          3.388
source_citation_quality    1.029
```

## Group means

```
               group  novelty  semantic_repetition  narrative_convergence  groupthink  specificity  evidence_grounding  epistemic_caution  template_rigidity  source_citation_quality  n_judged
          base-model    1.918                3.397                  3.961       3.524        2.409               1.466              1.933              3.125                    1.033       511
        canonical-48    1.870                3.975                  4.616       4.176        2.691               1.471              2.193              3.383                    1.014       768
    entropy-collapse    1.839                3.959                  4.546       4.121        2.528               1.426              2.152              3.491                    1.020       796
frontier/mixed-model    2.438                3.250                  4.188       3.312        2.875               2.188              3.125              2.750                    1.562        16
           obsession    2.827                2.809                  3.718       2.845        4.145               2.409              2.600              3.755                    1.091       110
     source-citation    2.078                3.625                  4.250       3.688        3.156               1.500              2.516              3.797                    1.031        64
```
