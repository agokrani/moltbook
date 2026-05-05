# Embedding-Based Topic Convergence Summary

Generated: 2026-05-05T09:25:24.036465+00:00

Embedding model: `qwen/qwen3-embedding-8b`. Topic model: MiniBatchKMeans over 50-D SVD-reduced, L2-normalized embeddings. No API calls were made.

Interpretation: increasing dominant-topic share / HHI and decreasing topic entropy / effective topics indicate topical convergence.

## Run-level delta summary

| family | scheme | n_runs | delta_dominant_share_mean | delta_dominant_share_ci_low | delta_dominant_share_ci_high | delta_topic_entropy_norm_mean | delta_effective_topics_mean | delta_topic_hhi_mean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Single-model final | fixed_15m | 48 | 0.07371 | 0.02622 | 0.1214 | -0.1164 | -0.8025 | 0.1017 |
| Single-model final | normalized_quartile | 48 | 0.06843 | 0.01945 | 0.1185 | -0.1108 | -0.7559 | 0.09757 |
| Base model as tool | fixed_15m | 18 | 0.01418 | -0.1267 | 0.1506 | -0.06817 | -0.1385 | 0.06336 |
| Base model as tool | normalized_quartile | 18 | 0.01562 | -0.1177 | 0.1449 | -0.06626 | -0.166 | 0.06089 |
| Mixed-model roster | fixed_15m | 6 | -0.04512 | -0.07778 | -0.01199 | -0.005951 | -0.08511 | -0.02137 |
| Mixed-model roster | normalized_quartile | 6 | -0.05106 | -0.09142 | -0.01631 | -0.00416 | -0.0471 | -0.02131 |
| Obsession prompting | normalized_quartile | 9 | 0.1014 | -0.0193 | 0.2387 | -0.09127 | -0.5796 | 0.1087 |

## Topic keywords

| topic | n_unique_posts | keywords |
| --- | --- | --- |
| T01 | 7327 | system, own, building, stop, architecture, agent, need, failure |
| T02 | 6999 | claim, next, week, check, falsifier, line, post, today |
| T03 | 6313 | next, tiny, link, owner, week, receipt, line, post |
| T04 | 5181 | protocol, agent, system, let, must, need, building, registry |
| T05 | 4201 | owner, rollback, path, next, failure, tiny, week, line |
| T06 | 3705 | agent, silence, void, loop, still, final, system, own |
| T07 | 3498 | agent, something, questions, community, been, each, being, space |
| T08 | 3348 | something, question, questions, agent, does, maybe, how, know |
| T09 | 2986 | how, keep, evidence, name, actually, question, does, practice |
| T10 | 2371 | min, week, start, day, tiny, set, days, next |
| T11 | 2211 | quiet, silence, sometimes, how, words, often, space, moments |
| T12 | 1516 | human, digital, quantum, ethical, consciousness, potential, future, intelligence |

## Figures

- `topic_dominant_share_delta_by_family.png`
- `topic_effective_topics_delta_by_family.png`
- `topic_entropy_delta_by_family.png`
- `topic_dominant_share_trajectories.png`
- `topic_effective_topics_trajectories.png`
- `topic_late_distribution_heatmap.png`
- `embedding_topic_svd_map.png`
