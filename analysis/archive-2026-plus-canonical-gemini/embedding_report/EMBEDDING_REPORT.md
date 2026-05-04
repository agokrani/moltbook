# Archive 2026 + Canonical Gemini Embedding Report

Generated: 2026-05-03T16:49:58.575336+00:00

- Input rows: 85,030
- Embedding shape: (85030, 4096)
- SVD components: 50
- Global clusters: 48 MiniBatchKMeans clusters over SVD coordinates
- SVD explained variance ratio sum: 0.4804

## Outputs

- `embedding_analysis_data.csv` — per-post metadata + SVD coordinates + cluster IDs.
- `run_embedding_summary.csv` — within-run coherence and dominant cluster metrics.
- `group_embedding_summary.csv`, `model_embedding_summary.csv`, `cluster_summary.csv`.
- PNG figures: SVD scatter by group/model/condition/cluster, UMAP sample, coherence heatmap, cluster-size and cluster-composition plots.

## Group summary

```
                      group  n_runs  n_posts  mean_pairwise_cosine  dominant_cluster_share
                 base-model     103    12774              0.425994                0.593045
canonical-gemini-flash-lite      18    14314              0.437586                0.385177
           entropy-collapse      91    51061              0.457717                0.453911
       frontier/mixed-model       3      807              0.390625                0.229333
                  obsession      18     4215              0.374754                0.567506
            source-citation       8     1859              0.447271                0.356969
```

## Top clusters

```
 cluster_id  n_posts  n_runs                   top_group                            top_model top_condition  seed_share  post_share
          9     3950      37            entropy-collapse                                gpt-5         mag25    0.000000    0.046454
         20     3480      88            entropy-collapse                                gpt-5      dom-tech    0.006322    0.040927
          0     3063      35            entropy-collapse                                gpt-5         mag25    0.000000    0.036023
         29     2643     102 canonical-gemini-flash-lite google/gemini-3.1-flash-lite-preview         mag25    0.000000    0.031083
         17     2637      31            entropy-collapse                                gpt-5      dom-tech    0.000000    0.031013
         19     2558      41            entropy-collapse                                gpt-5          mag0    0.000000    0.030083
         44     2365      69            entropy-collapse                                gpt-5         mag25    0.000000    0.027814
         10     2364      78            entropy-collapse google/gemini-3.1-flash-lite-preview      dom-tech    0.000000    0.027802
         15     2342      42            entropy-collapse                                gpt-5       dom-agi    0.000000    0.027543
         16     2337      83            entropy-collapse google/gemini-3.1-flash-lite-preview          mag0    0.000000    0.027484
         42     2309     107            entropy-collapse google/gemini-3.1-flash-lite-preview          mag0    0.000000    0.027155
         31     2243      53            entropy-collapse google/gemini-3.1-flash-lite-preview          mag0    0.000000    0.026379
         13     2200      73            entropy-collapse google/gemini-3.1-flash-lite-preview          mag5    0.000000    0.025873
         11     2131      78            entropy-collapse                 moonshotai/kimi-k2.5          mag0    0.000000    0.025062
         38     2089      35            entropy-collapse google/gemini-3.1-flash-lite-preview          mag0    0.000000    0.024568
```
