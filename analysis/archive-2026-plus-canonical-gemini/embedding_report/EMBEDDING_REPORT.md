# Archive 2026 + Canonical 48 Embedding Report

Generated: 2026-05-04T10:49:49.820634+00:00

- Input rows: 68,050
- Embedding shape: (68050, 4096)
- SVD components: 50
- Global clusters: 48 MiniBatchKMeans clusters over SVD coordinates
- SVD explained variance ratio sum: 0.4922

## Outputs

- `embedding_analysis_data.csv` — per-post metadata + SVD coordinates + cluster IDs.
- `run_embedding_summary.csv` — within-run coherence and dominant cluster metrics.
- `group_embedding_summary.csv`, `model_embedding_summary.csv`, `cluster_summary.csv`.
- PNG figures: SVD scatter by group/model/condition/cluster, UMAP sample, coherence heatmap, cluster-size and cluster-composition plots.

## Group summary

```
           group  n_runs  n_posts  mean_pairwise_cosine  dominant_cluster_share
      base-model     103    12774              0.425994                0.537886
entropy-collapse      91    51061              0.457717                0.473107
       obsession      18     4215              0.374754                0.574038
```

## Top clusters

```
 cluster_id  n_posts  n_runs        top_group                            top_model top_condition  seed_share  post_share
         16     3420      48 entropy-collapse                                gpt-5       dom-agi    0.004971    0.050257
         24     2429      23 entropy-collapse                                gpt-5         mag25    0.000000    0.035694
         18     2354      43 entropy-collapse google/gemini-3.1-flash-lite-preview          mag0    0.000000    0.034592
         44     2319      66 entropy-collapse google/gemini-3.1-flash-lite-preview          mag0    0.000000    0.034078
          0     2248      45 entropy-collapse                                gpt-5          mag1    0.000000    0.033035
          6     2175      91 entropy-collapse google/gemini-3.1-flash-lite-preview         mag25    0.000000    0.031962
         29     2114      27 entropy-collapse                                gpt-5         mag25    0.000000    0.031065
         11     2050      26 entropy-collapse                                gpt-5      dom-tech    0.000000    0.030125
          2     1987      40 entropy-collapse                                gpt-5       dom-agi    0.000000    0.029199
         41     1932      38 entropy-collapse                                gpt-5          mag0    0.000000    0.028391
         38     1858      64 entropy-collapse                 moonshotai/kimi-k2.5          mag0    0.000000    0.027303
         12     1832      63 entropy-collapse google/gemini-3.1-flash-lite-preview          mag5    0.000000    0.026921
         15     1808      27 entropy-collapse                                gpt-5         mag25    0.000000    0.026569
         13     1805      47 entropy-collapse google/gemini-3.1-flash-lite-preview          mag0    0.000000    0.026525
         42     1701      27 entropy-collapse                                gpt-5          mag1    0.000000    0.024996
```
