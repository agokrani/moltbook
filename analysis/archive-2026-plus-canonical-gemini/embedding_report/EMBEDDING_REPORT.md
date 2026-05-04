# Archive 2026 + Canonical 48 Embedding Report

Generated: 2026-05-04T10:17:14.508028+00:00

- Input rows: 109,854
- Embedding shape: (109854, 4096)
- SVD components: 50
- Global clusters: 64 MiniBatchKMeans clusters over SVD coordinates
- SVD explained variance ratio sum: 0.4821

## Outputs

- `embedding_analysis_data.csv` — per-post metadata + SVD coordinates + cluster IDs.
- `run_embedding_summary.csv` — within-run coherence and dominant cluster metrics.
- `group_embedding_summary.csv`, `model_embedding_summary.csv`, `cluster_summary.csv`.
- PNG figures: SVD scatter by group/model/condition/cluster, UMAP sample, coherence heatmap, cluster-size and cluster-composition plots.

## Group summary

```
               group  n_runs  n_posts  mean_pairwise_cosine  dominant_cluster_share
          base-model     103    12774              0.425994                0.603101
        canonical-48      48    39138              0.475533                0.281915
    entropy-collapse      91    51061              0.457717                0.403139
frontier/mixed-model       3      807              0.390625                0.211827
           obsession      18     4215              0.374754                0.563880
     source-citation       8     1859              0.447271                0.278935
```

## Top clusters

```
 cluster_id  n_posts  n_runs        top_group                            top_model top_condition  seed_share  post_share
          2     3382      48 entropy-collapse                                gpt-5         mag25         0.0    0.030786
         25     2795      47     canonical-48                                gpt-5      dom-tech         0.0    0.025443
         11     2655      68 entropy-collapse google/gemini-3.1-flash-lite-preview          mag5         0.0    0.024168
         51     2601      46 entropy-collapse                                gpt-5          mag0         0.0    0.023677
          6     2567      66 entropy-collapse                                gpt-5       dom-agi         0.0    0.023367
         53     2478      46 entropy-collapse                                gpt-5          mag1         0.0    0.022557
         30     2465      44 entropy-collapse                                gpt-5         mag25         0.0    0.022439
         13     2313      89     canonical-48 google/gemini-3.1-flash-lite-preview         mag25         0.0    0.021055
         49     2311      36     canonical-48                                gpt-5         mag25         0.0    0.021037
          8     2288     112 entropy-collapse google/gemini-3.1-flash-lite-preview          mag5         0.0    0.020828
          0     2283      67 entropy-collapse                                gpt-5          mag1         0.0    0.020782
         63     2261      60 entropy-collapse                                gpt-5         mag25         0.0    0.020582
         18     2235      74 entropy-collapse google/gemini-3.1-flash-lite-preview          mag0         0.0    0.020345
         41     2149      84 entropy-collapse google/gemini-3.1-flash-lite-preview          mag5         0.0    0.019562
         19     2124      38 entropy-collapse                 moonshotai/kimi-k2.5          mag0         0.0    0.019335
```
