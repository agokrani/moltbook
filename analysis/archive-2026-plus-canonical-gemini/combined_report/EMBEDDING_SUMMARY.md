# Embedding/Vendi Summary

{
  "cached_embeddings": 109844,
  "nonseed_posts": 50805,
  "missing_nonseed_embeddings": 0,
  "embedding_model": "qwen/qwen3-embedding-8b"
}

| internal_family_label | scheme | n_runs | delta_vendi_score_n_valid | delta_vendi_score_mean | delta_vendi_score_median | delta_vendi_score_ci_low | delta_vendi_score_ci_high | delta_vendi_score_n_negative | delta_vendi_score_n_positive | delta_vendi_score_sign_p | delta_mean_pairwise_cosine_n_valid | delta_mean_pairwise_cosine_mean | delta_mean_pairwise_cosine_median | delta_mean_pairwise_cosine_ci_low | delta_mean_pairwise_cosine_ci_high | delta_mean_pairwise_cosine_n_negative | delta_mean_pairwise_cosine_n_positive | delta_mean_pairwise_cosine_sign_p | delta_semantic_radius_n_valid | delta_semantic_radius_mean | delta_semantic_radius_median | delta_semantic_radius_ci_low | delta_semantic_radius_ci_high | delta_semantic_radius_n_negative | delta_semantic_radius_n_positive | delta_semantic_radius_sign_p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| base_model_as_tool | fixed_15m | 49 | 25 | -0.6569 | -0.6795 | -1.055 | -0.2231 | 17 | 8 | 0.1078 | 25 | 0.0856 | 0.07731 | 0.03156 | 0.1343 | 7 | 18 | 0.04329 | 25 | -0.05742 | -0.05676 | -0.09257 | -0.01846 | 18 | 7 | 0.04329 |
| base_model_as_tool | normalized_quartile | 49 | 46 | -0.6129 | -0.6852 | -0.8649 | -0.3567 | 35 | 11 | 0.0005356 | 46 | 0.1134 | 0.1205 | 0.077 | 0.1487 | 10 | 36 | 0.0001564 | 46 | -0.07091 | -0.07978 | -0.09404 | -0.04721 | 36 | 10 | 0.0001564 |
| mixed_model_roster | fixed_15m | 3 | 2 | 0.06572 | 0.06572 | 0.05306 | 0.07839 | 0 | 2 | 0.5 | 2 | -0.03557 | -0.03557 | -0.04938 | -0.02176 | 2 | 0 | 0.5 | 2 | 0.0264 | 0.0264 | 0.01595 | 0.03685 | 0 | 2 | 0.5 |
| mixed_model_roster | normalized_quartile | 3 | 3 | 0.1295 | 0.09376 | 0.08673 | 0.2081 | 0 | 3 | 0.25 | 3 | -0.03772 | -0.04331 | -0.04983 | -0.02001 | 3 | 0 | 0.25 | 3 | 0.02663 | 0.02802 | 0.01472 | 0.03715 | 0 | 3 | 0.25 |
| obsession_prompting | normalized_quartile | 15 | 10 | -0.1698 | -0.1452 | -0.3365 | -0.03716 | 7 | 3 | 0.3438 | 10 | 0.03533 | 0.0224 | 0.01004 | 0.06961 | 2 | 8 | 0.1094 | 10 | -0.01914 | -0.01635 | -0.03144 | -0.007097 | 8 | 2 | 0.1094 |
| single_model_final | fixed_15m | 48 | 48 | -0.7347 | -0.6952 | -0.9562 | -0.5206 | 42 | 6 | 1.009e-07 | 48 | 0.0588 | 0.03792 | 0.03758 | 0.08249 | 7 | 41 | 6.24e-07 | 48 | -0.03949 | -0.02707 | -0.05473 | -0.02569 | 41 | 7 | 6.24e-07 |
| single_model_final | normalized_quartile | 48 | 48 | -0.7786 | -0.6969 | -1.016 | -0.5513 | 40 | 8 | 3.305e-06 | 48 | 0.05944 | 0.03791 | 0.03792 | 0.08377 | 7 | 41 | 6.24e-07 | 48 | -0.0399 | -0.02609 | -0.05543 | -0.02575 | 41 | 7 | 6.24e-07 |
