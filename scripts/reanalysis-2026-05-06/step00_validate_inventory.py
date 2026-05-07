#!/usr/bin/env python3
"""Step 0: validate inputs and write run inventory tables."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from common import (
    DETERMINISTIC_DELTAS,
    DETERMINISTIC_TIMEBINS,
    EMBEDDING_DELTAS,
    EMBEDDING_TIMEBINS,
    LLM_DELTAS,
    LLM_TIMEBINS,
    MODEL_ORDER,
    PLOT_ROOT,
    read_csv,
)

OUT = PLOT_ROOT / "step00_inventory"
REQUIRED = [
    DETERMINISTIC_DELTAS,
    DETERMINISTIC_TIMEBINS,
    EMBEDDING_DELTAS,
    EMBEDDING_TIMEBINS,
    LLM_DELTAS,
    LLM_TIMEBINS,
]


def source_row(name: str, path: Path) -> dict:
    exists = path.exists()
    row = {
        "source": name,
        "path": str(path),
        "exists": exists,
        "size_bytes": path.stat().st_size if exists else None,
        "rows": None,
        "columns": None,
    }
    if exists:
        df = pd.read_csv(path, nrows=5)
        row["columns"] = len(df.columns)
        row["rows"] = sum(1 for _ in open(path, "rb")) - 1
    return row


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    source_rows = [
        source_row("deterministic run deltas", DETERMINISTIC_DELTAS),
        source_row("deterministic time bins", DETERMINISTIC_TIMEBINS),
        source_row("embedding run deltas", EMBEDDING_DELTAS),
        source_row("embedding time bins", EMBEDDING_TIMEBINS),
        source_row("LLM judge run deltas", LLM_DELTAS),
        source_row("LLM judge time bins", LLM_TIMEBINS),
    ]
    source_df = pd.DataFrame(source_rows)
    source_df.to_csv(OUT / "metric_availability.csv", index=False, lineterminator="\n")

    det = read_csv(DETERMINISTIC_DELTAS)
    emb = read_csv(EMBEDDING_DELTAS)
    llm = read_csv(LLM_DELTAS)

    inv = det.groupby(
        ["internal_family_label", "model_display", "n_agents", "scheme"],
        dropna=False,
    ).agg(
        runs=("run_uid", "nunique"),
        conditions=("condition", lambda s: ", ".join(sorted(set(map(str, s))))),
        first_run=("run_id", "first"),
    ).reset_index().sort_values(["internal_family_label", "model_display", "n_agents", "scheme"])
    inv.to_csv(OUT / "run_inventory.csv", index=False, lineterminator="\n")

    # Metric-level run availability for the first plotting step.
    rows = []
    checks = [
        ("gzip", det, "delta_compression_gzip"),
        ("distinct5", det, "delta_distinct_5"),
        ("vendi", emb, "delta_vendi_score"),
        ("llm_collapse", llm, "delta_collapse_index"),
    ]
    for metric, df, col in checks:
        sub = df[(df["internal_family_label"] == "single_model_final") & (df["scheme"] == "fixed_15m")].copy()
        for model in MODEL_ORDER:
            for n_agents in [10, 20, 30]:
                cell = sub[(sub["model_display"] == model) & (sub["n_agents"] == n_agents)]
                rows.append({
                    "metric": metric,
                    "model_display": model,
                    "n_agents": n_agents,
                    "runs": int(cell["run_uid"].nunique()),
                    "conditions": int(cell["condition"].nunique()) if not cell.empty else 0,
                    "non_missing_metric_values": int(cell[col].notna().sum()) if col in cell else 0,
                })
    availability = pd.DataFrame(rows)
    availability.to_csv(OUT / "canonical_metric_availability.csv", index=False, lineterminator="\n")

    summary = {
        "all_required_files_exist": all(p.exists() for p in REQUIRED),
        "canonical_fixed_15m_runs": int(det[(det["internal_family_label"] == "single_model_final") & (det["scheme"] == "fixed_15m")]["run_uid"].nunique()),
        "canonical_n10_models": availability[(availability["n_agents"] == 10) & (availability["metric"] == "gzip")].set_index("model_display")["runs"].to_dict(),
        "scale_complete_models": availability[(availability["metric"] == "gzip") & (availability["runs"] == 6)].groupby("model_display")["n_agents"].apply(lambda s: sorted(map(int, s))).to_dict(),
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True))

    readme = """# Step 0 inventory\n\nThis folder validates the input files and records what run designs are available.\n\nFiles:\n\n- `metric_availability.csv`: required source files and row counts.\n- `run_inventory.csv`: run counts by cohort, model, scale, and time scheme.\n- `canonical_metric_availability.csv`: metric availability for canonical fixed 15-minute runs.\n- `summary.json`: quick machine-readable summary.\n\nMain check for Step 1: all four canonical models have six 10-agent fixed 15-minute runs, one for each seed condition.\n"""
    (OUT / "README.md").write_text(readme)
    print(f"wrote Step 0 inventory to {OUT}")


if __name__ == "__main__":
    main()
