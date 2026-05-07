#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../.."

python3 scripts/reanalysis-2026-05-05/build_topic_robustness.py
python3 scripts/reanalysis-2026-05-05/validate_reanalysis_bundle.py
python3 scripts/reanalysis-2026-05-05/build_canonical_design_plots.py
python3 scripts/reanalysis-2026-05-05/build_canonical_trajectory_plots.py
python3 scripts/reanalysis-2026-05-05/build_scale_paired_plots.py
python3 scripts/reanalysis-2026-05-05/build_condition_vs_empty_plots.py
python3 scripts/reanalysis-2026-05-05/build_n10_comparison_plots.py
python3 scripts/reanalysis-2026-05-05/build_mixed_roster_plots.py
python3 scripts/reanalysis-2026-05-05/build_obsession_matched_plots.py
python3 scripts/reanalysis-2026-05-05/build_stats_tables.py

echo "done: findings/emnlp-2026-paper/plots/reanalysis-2026-05-05"
