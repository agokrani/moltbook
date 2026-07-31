# Release scope and review-request mapping

## Artifact commitment

The author response committed to releasing the controlled platform fork, run manifests, seed posts, anonymized agent posts, preprocessing and metric scripts, judge prompts and outputs, and configuration files. Each item is present and mapped in `README.md`.

## New analyses requested during review

| Request | Evidence | Reproducer |
| --- | --- | --- |
| Human reference / matched Reddit baseline | `analysis/results/matched_1h_reddit_posts.json` | `build_agent_sessions_1h.py`, `build_reddit_post_baseline.py` |
| Corpus-length control | `analysis/results/temporal_equal_length_results.json` | `build_temporal_length_normalization.py` |
| Longer-horizon behavior | `five_hour_comparison*`, `long_horizon_*`, and `5h_gp5_run.csv` | `build_five_hour_comparison.py`, `build_long_horizon_extension.py`, `plot_5h_gp5_csv.py` |
| Judge components and additional judges | `multijudge_*.csv` plus blinded contexts in `judge/` | `multijudge_validation.py`, `judge/ayush-blind-llm-judge.py` |
| Population scaling | 48-run manifest and locked canonical dataset | repository analysis scripts and `data/manifests/data_manifest.csv` |

## Editorial commitments not rewritten here

The rebuttal also promises camera-ready prose changes: define entropy collapse operationally, distinguish it from adjacent convergence/groupthink phenomena, add related work, explain model selection, narrow generalization claims, and expand limitations. The supplied Overleaf export predates those rebuttal-only analyses in several passages. Because the release must preserve the author-designated final source, this branch records that fact instead of silently editing scientific claims. The evidence and requested wording are retained in `rebuttal/rebuttal_final.md` for the authors' camera-ready editorial pass.
