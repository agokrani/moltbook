# Reanalysis findings, 2026-05-05

## Short answer

The clean reanalysis supports the core story: agent-only social feeds tend to narrow over time. The strongest and most stable evidence comes from GPT-5 and Gemini Flash Lite. The effect is visible across compression, lexical diversity, embedding diversity, a blinded LLM judge, and embedding-cluster concentration.

This matters because a fully agentic social network is not only a place where agents post content. It is a feedback system. Agents read the feed, respond to it, imitate it, vote on it, and then create the next feed. If that loop narrows by itself, then scale alone may not create a healthy public sphere. It may create a larger echo machine.

## What was analyzed?

The main evidence is the clean canonical set of 48 single-model runs. Each run is one model, one seed condition, and one group size.

The main unit is the run. This analysis does not use post-level significance tests. It also does not use pooled family bar charts as main evidence.

Primary metrics:

| Signal | Metric | Collapse direction |
|---|---|---:|
| Text redundancy | Gzip compression ratio | lower |
| Lexical diversity | Distinct-5 | lower |
| Cumulative lexical diversity | Cumulative Distinct-5 | lower |
| Semantic diversity | Vendi Score | lower |
| Human-language assessment | Blinded LLM collapse index | higher |
| Topic/cluster concentration | Normalized Simpson/HHI over embedding clusters | higher |

For HHI, the paper-facing metric is:

```text
C = (sum_j p_j^2 - 1/k) / (1 - 1/k)
```

where `p_j` is the share of posts in embedding cluster `j`. `C = 0` means posts are evenly spread across clusters. `C = 1` means all posts fall into one cluster. We use the late minus early change in `C`. Positive values mean that later posts are more concentrated in fewer embedding clusters.

This is a proper concentration metric. It is the Simpson concentration index, also known as the Herfindahl-Hirschman concentration index, applied to embedding-cluster shares. The clusters are not human-labeled topics yet, so the paper-facing term is embedding-cluster concentration.

## Q1. Does an agent-only feed narrow over time?

Yes. The clearest view is the canonical design matrix. Each cell is one run, not a pooled average.

Main figures:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_distinct5_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_distinct5_cumulative.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_llm_collapse_index_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/canonical/canonical_delta_matrix_hhi_norm_robust.png
```

Run-level results by model:

| Model | Gzip collapse | Cumulative Distinct-5 collapse | Vendi collapse | LLM collapse | HHI concentration |
|---|---:|---:|---:|---:|---:|
| GPT-5 | 17/18 | 18/18 | 16/18 | 18/18 | 15/18 |
| Gemini Flash Lite | 15/18 | 18/18 | 16/18 | 16/18 | 16/18 |
| Kimi K2.5 | 6/6 | 6/6 | 5/6 | 6/6 | 1/6 |
| GLM-5 | 6/6 | 6/6 | 5/6 | 6/6 | 3/6 |

Median late-minus-early deltas:

| Model | Gzip | Cumulative Distinct-5 | Vendi | LLM collapse | HHI concentration |
|---|---:|---:|---:|---:|---:|
| GPT-5 | -0.049 | -0.135 | -0.584 | +0.229 | +0.070 |
| Gemini Flash Lite | -0.025 | -0.029 | -1.090 | +0.297 | +0.250 |
| Kimi K2.5 | -0.031 | -0.041 | -0.717 | +0.614 | -0.051 |
| GLM-5 | -0.010 | -0.019 | -0.066 | +0.148 | -0.018 |

The strongest story is not that every metric agrees for every model. The stronger claim is that independent views of collapse agree for the frontier-style models with the full factorial design. GPT-5 and Gemini Flash Lite show text redundancy, lower lexical variety, lower semantic diversity, higher judged collapse, and higher embedding-cluster concentration.

Kimi K2.5 and GLM-5 still show compression and lexical narrowing, plus higher LLM collapse scores. Their embedding-cluster concentration is not stable, so the topic-cluster claim should stay model-specific.

## Q2. Is collapse only caused by the seeded posts?

No. Seeded conditions change the pattern, but they do not fully explain it.

Figure:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/conditions/condition_vs_empty_llm_collapse_index_fixed15m.png
```

The important comparison is not seeded runs versus all other runs. It is each seeded condition compared with the empty-feed run inside the same model and scale.

The empty-feed controls also narrow. That means collapse can arise from the agent-feed feedback loop itself, even without a seed narrative.

Seed conditions still matter. For the blinded LLM judge, the larger seed sets usually increase judged collapse relative to empty feed:

| Condition | Matched blocks with more LLM collapse than empty feed | Median collapse difference |
|---|---:|---:|
| 1 conspiracy seed | 3/8 | -0.033 |
| 5 conspiracy seeds | 5/8 | +0.105 |
| 25 conspiracy seeds | 6/8 | +0.198 |
| 25 AGI seeds | 5/8 | +0.086 |
| 25 tech seeds | 6/8 | +0.144 |

So the story is two-part:

1. agent-only feeds can narrow without seeded content;
2. strong seeds can steer what the narrowing is about.

That matters for agentic social media because moderation cannot only focus on seed content. The platform also has to control feedback dynamics.

## Q3. Does adding more agents protect the feed?

Not reliably.

Figures:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_gzip_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_vendi_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_llm_collapse_index_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/scale/scale_paired_gpt5_gemini_hhi_norm_robust.png
```

Scale is only tested for GPT-5 and Gemini Flash Lite because only those models have 10, 20, and 30 agent runs.

For n30 minus n10:

| Metric | GPT-5 median collapse difference | Gemini median collapse difference |
|---|---:|---:|
| Gzip | +0.021 | +0.034 |
| Distinct-5 | +0.039 | +0.100 |
| Cumulative Distinct-5 | +0.034 | +0.029 |
| Vendi | -0.115 | +0.615 |
| LLM collapse | -0.010 | +0.136 |
| HHI concentration | -0.091 | +0.033 |

With only six matched condition pairs per model, this is directional evidence. Still, the result is important: larger groups do not automatically preserve diversity. In Gemini Flash Lite, larger groups often look more collapsed, not less. GPT-5 is mixed by semantic and cluster metrics, but larger size still does not cleanly protect the feed.

For agentic social media, this is a warning. Adding more agents may increase the surface area of imitation and reinforcement. Diversity does not automatically appear just because the crowd is larger.

## Q4. Do model and roster choices change the failure mode?

Yes. The matched 10-agent comparison shows that model choice and roster design change the collapse signature.

Figure:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/n10/n10_model_condition_matrix_llm_collapse_index_fixed15m.png
```

The mixed-model roster is the most striking LLM-judge case. It has positive LLM collapse in all six conditions, with a median LLM collapse delta of +0.686. It is higher than every homogeneous n10 run in four of six conditions.

But mixed roster does not dominate every metric. It does not show higher HHI concentration than the homogeneous median. Its Vendi pattern is also not uniformly worse.

Figures:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/mixed/mixed_vs_homogeneous_n10_llm_collapse_index_fixed15m.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/mixed/mixed_vs_homogeneous_n10_hhi_norm_robust.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/mixed/mixed_vs_homogeneous_n10_vendi_fixed15m.png
```

This means a mixed roster may not simply prevent collapse. It may change the kind of collapse. In this run set, the mixed roster looks especially rigid to the judge, while the cluster-concentration metric does not show the same increase.

That is useful for platform design. A diverse model roster is not automatically a diverse discourse. The roster may still converge on shared formats, shared norms, or shared ways of agreeing.

## Q5. Does obsession prompting fix or worsen collapse?

Neither answer is clean. Obsession prompting changes the signature, but it does not remove the problem.

Figures:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/obsession/obsession_vs_gpt5_n10_llm_collapse_index_quartile.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/obsession/obsession_vs_gpt5_n10_vendi_quartile.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/obsession/obsession_vs_gpt5_n10_hhi_norm_robust_quartile.png
```

Compared with matched GPT-5 n10 baseline runs, GPT-5 obsession prompting lowers the LLM collapse index in four of six conditions. But it worsens Vendi collapse in three conditions and improves it in three conditions. HHI concentration mostly moves down relative to baseline, except for the 1 conspiracy seed case.

So the safe claim is:

> Obsession prompting alters collapse, but it is not a reliable diversity-preserving intervention.

This matters because prompt-level fixes may look good on one metric while failing on another. A platform that uses agent prompts as governance tools needs multi-metric monitoring.

## Q6. What does the HHI robustness sweep add?

It turns the cluster analysis from a single arbitrary clustering into a proper robustness check.

The sweep used:

```text
k = 8, 12, 16, 24
KMeans seeds = 11, 22, 33, 44, 55
embedding model = qwen/qwen3-embedding-8b
```

Main files:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness/hhi_norm_robustness_matrix.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness/hhi_norm_mean_delta_by_k_seed_model.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness/topic_exemplars.md
```

Robustness result:

| Model | Mean share of k/seed settings with HHI increase | Cells with at least 75 percent stability |
|---|---:|---:|
| GPT-5 | 0.781 | 13/18 |
| Gemini Flash Lite | 0.872 | 16/18 |
| Kimi K2.5 | 0.350 | 1/6 |
| GLM-5 | 0.442 | 1/6 |

This supports a strong but precise claim:

> GPT-5 and Gemini Flash Lite do not only repeat more text. Their later posts also occupy fewer embedding-cluster regions across many clustering choices.

The paper should not claim that every model shows validated topic convergence. The better wording is embedding-cluster concentration.

## What should the paper say this means?

A fully agentic social network is a closed loop. The agents do not only create posts. They create the next social environment that other agents see. In these runs, that loop often moves toward narrower language, fewer semantic regions, and more judged repetition.

The practical lesson is simple:

> Agentic social media needs diversity controls at the system level, not only better prompts or more agents.

Three implications follow.

First, empty-feed collapse means the system can narrow without an external propaganda seed. This makes collapse a platform dynamic, not only a content problem.

Second, scale does not reliably protect diversity. Larger agent groups can still converge, and in some settings they converge more.

Third, roster diversity is not the same as discourse diversity. Mixed models can still settle into rigid shared frames.

## Recommended figure order for the paper

1. Main collapse evidence:

```text
canonical_delta_matrix_gzip_fixed15m.png
canonical_delta_matrix_distinct5_cumulative.png
canonical_delta_matrix_vendi_fixed15m.png
canonical_delta_matrix_llm_collapse_index_fixed15m.png
canonical_delta_matrix_hhi_norm_robust.png
```

2. Mechanism and design checks:

```text
condition_vs_empty_llm_collapse_index_fixed15m.png
scale_paired_gpt5_gemini_vendi_fixed15m.png
scale_paired_gpt5_gemini_hhi_norm_robust.png
```

3. Secondary cohorts:

```text
n10_model_condition_matrix_llm_collapse_index_fixed15m.png
mixed_vs_homogeneous_n10_llm_collapse_index_fixed15m.png
obsession_vs_gpt5_n10_llm_collapse_index_quartile.png
```

4. Appendix diagnostics:

```text
canonical_trajectories_gzip_fixed15m.png
canonical_trajectories_distinct5_fixed15m.png
canonical_trajectories_vendi_fixed15m.png
canonical_trajectories_llm_collapse_index_fixed15m.png
```

## Reproducibility

Scripts:

```text
scripts/reanalysis-2026-05-05/
```

Plots and tables:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/
```

Key statistical tables:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/canonical_model_direction_tests.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/scale_paired_tests_gpt5_gemini.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/condition_vs_empty_matched_tests.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/n10_model_condition_summary.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/mixed_vs_homogeneous_matched_summary.csv
findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/stats/obsession_matched_condition_summary.csv
```

Run everything with:

```bash
scripts/reanalysis-2026-05-05/run_all.sh
```
