# Archive 2026 + Canonical Gemini LLM-as-a-Judge Report

Generated: 2026-05-03T17:04:58.974527+00:00

## Method

A stratified sample was drawn across `group × model_family × condition × scale × time_bin`, with extra coverage guarantees for every global embedding cluster. The judge prompt blinds group/model/condition/source labels and supplies local previous-post context plus same-cluster examples. Results are cached in SQLite and aggregated here.

- Rubric version: `archive-entropy-collapse-v1`
- Judge model: `google/gemini-3.1-flash-lite-preview`
- Sample rows: 1,791
- Completed judgments included: 1,791

## Outputs

- `judge_results.jsonl` / `judge_results.csv` — post-level scored sample.
- `judge_summary_by_cell.csv`, `judge_summary_by_group.csv`, `judge_summary_by_model.csv`, `judge_summary_by_condition.csv`, `judge_summary_by_cluster.csv`.
- `judge_collapse_label_shares.csv`, `judge_claim_behavior_shares.csv`.
- PNG heatmaps: `fig_judge_*_group_condition.png`; cluster repetition chart.

## Overall score means

```
novelty                    1.891
semantic_repetition        3.773
narrative_convergence      4.370
groupthink                 3.897
specificity                2.569
evidence_grounding         1.482
epistemic_caution          2.054
template_rigidity          3.343
source_citation_quality    1.021
```

## Group means

```
                      group  novelty  semantic_repetition  narrative_convergence  groupthink  specificity  evidence_grounding  epistemic_caution  template_rigidity  source_citation_quality  n_judged
                 base-model    1.914                3.402                  3.967       3.529        2.406               1.463              1.929              3.129                    1.031       510
canonical-gemini-flash-lite    1.646                4.260                  4.812       4.385        2.253               1.281              1.524              3.104                    1.000       288
           entropy-collapse    1.856                3.951                  4.549       4.096        2.529               1.435              2.210              3.478                    1.012       803
       frontier/mixed-model    2.750                2.750                  3.625       2.938        3.062               2.312              3.250              2.438                    1.438        16
                  obsession    2.627                2.982                  3.855       3.036        4.182               2.327              2.509              3.827                    1.027       110
            source-citation    1.781                3.922                  4.422       3.859        2.891               1.484              2.375              3.828                    1.031        64
```
