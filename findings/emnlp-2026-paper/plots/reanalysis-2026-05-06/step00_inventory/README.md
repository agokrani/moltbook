# Step 0 inventory

This folder validates the input files and records what run designs are available.

Files:

- `metric_availability.csv`: required source files and row counts.
- `run_inventory.csv`: run counts by cohort, model, scale, and time scheme.
- `canonical_metric_availability.csv`: metric availability for canonical fixed 15-minute runs.
- `summary.json`: quick machine-readable summary.

Main check for Step 1: all four canonical models have six 10-agent fixed 15-minute runs, one for each seed condition.
