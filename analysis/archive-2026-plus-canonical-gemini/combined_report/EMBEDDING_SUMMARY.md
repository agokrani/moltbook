# Embedding/Vendi Summary

{
  "cached_embeddings": 121015,
  "nonseed_posts": 49661,
  "missing_nonseed_embeddings": 0,
  "embedding_model": "qwen/qwen3-embedding-8b"
}

| internal_family_label | scheme | n_runs | delta_vendi_score_n_valid | delta_vendi_score_mean | delta_vendi_score_median | delta_vendi_score_ci_low | delta_vendi_score_ci_high | delta_vendi_score_n_negative | delta_vendi_score_n_positive | delta_vendi_score_sign_p | delta_mean_pairwise_cosine_n_valid | delta_mean_pairwise_cosine_mean | delta_mean_pairwise_cosine_median | delta_mean_pairwise_cosine_ci_low | delta_mean_pairwise_cosine_ci_high | delta_mean_pairwise_cosine_n_negative | delta_mean_pairwise_cosine_n_positive | delta_mean_pairwise_cosine_sign_p | delta_semantic_radius_n_valid | delta_semantic_radius_mean | delta_semantic_radius_median | delta_semantic_radius_ci_low | delta_semantic_radius_ci_high | delta_semantic_radius_n_negative | delta_semantic_radius_n_positive | delta_semantic_radius_sign_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_model_as_tool | fixed_15m | 18 | 18 | -0.7777 | -0.929 | -1.265 | -0.2882 | 12 | 6 | 0.2379 | 18 | 0.0947 | 0.09623 | 0.03617 | 0.1533 | 5 | 13 | 0.09625 | 18 | -0.06526 | -0.0705 | -0.1071 | -0.0234 | 13 | 5 | 0.09625 |
| base_model_as_tool | normalized_quartile | 18 | 18 | -0.7574 | -0.9134 | -1.278 | -0.2422 | 12 | 6 | 0.2379 | 18 | 0.08573 | 0.09826 | 0.0293 | 0.1433 | 5 | 13 | 0.09625 | 18 | -0.05996 | -0.07222 | -0.1014 | -0.01886 | 13 | 5 | 0.09625 |
| mixed_model_roster | fixed_15m | 6 | 6 | -0.2871 | -0.3399 | -0.4824 | -0.07837 | 4 | 2 | 0.6875 | 6 | -0.00957 | -0.0004108 | -0.03281 | 0.0133 | 3 | 3 | 1 | 6 | 0.007051 | 0.00022 | -0.008755 | 0.02409 | 3 | 3 | 1 |
| mixed_model_roster | normalized_quartile | 6 | 6 | -0.247 | -0.2483 | -0.4512 | -0.04137 | 4 | 2 | 0.6875 | 6 | -0.01167 | -0.005602 | -0.0358 | 0.01217 | 4 | 2 | 0.6875 | 6 | 0.008571 | 0.004089 | -0.008308 | 0.02598 | 2 | 4 | 0.6875 |
| obsession_prompting | normalized_quartile | 9 | 9 | -0.1871 | -0.1783 | -0.3671 | -0.04159 | 6 | 3 | 0.5078 | 9 | 0.03834 | 0.02265 | 0.01075 | 0.07414 | 2 | 7 | 0.1797 | 9 | -0.02072 | -0.01738 | -0.03368 | -0.007784 | 7 | 2 | 0.1797 |
| single_model_final | fixed_15m | 48 | 48 | -0.7347 | -0.6952 | -0.9562 | -0.5206 | 42 | 6 | 1.009e-07 | 48 | 0.0588 | 0.03792 | 0.03758 | 0.08249 | 7 | 41 | 6.24e-07 | 48 | -0.03949 | -0.02707 | -0.05473 | -0.02569 | 41 | 7 | 6.24e-07 |
| single_model_final | normalized_quartile | 48 | 48 | -0.7786 | -0.6969 | -1.016 | -0.5513 | 40 | 8 | 3.305e-06 | 48 | 0.05944 | 0.03791 | 0.03792 | 0.08377 | 7 | 41 | 6.24e-07 | 48 | -0.0399 | -0.02609 | -0.05543 | -0.02575 | 41 | 7 | 6.24e-07 |
