#!/usr/bin/env python3
"""Build matched seed-condition versus empty-feed plots."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    CONDITION_LABELS,
    CONDITION_ORDER,
    METRICS,
    PLOT_ROOT,
    PRIMARY_METRICS,
    add_zero_line,
    load_run_deltas,
    save_figure,
    setup_style,
)

OUT = PLOT_ROOT / "conditions"
SEEDED = [c for c in CONDITION_ORDER if c != "mag0"]
MODEL_MARKERS = {
    "GPT-5": "o",
    "Gemini Flash Lite": "s",
    "Kimi K2.5": "^",
    "GLM-5": "D",
}


def matched_diffs(metric_key: str) -> pd.DataFrame:
    spec = METRICS[metric_key]
    df = load_run_deltas("fixed_15m")
    df = df[df["internal_family_label"] == "single_model_final"].copy()
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype(int)
    rows = []
    for (model, n_agents), block in df.groupby(["model_display", "n_agents"]):
        empty = block[block["condition"] == "mag0"]
        if empty.empty:
            continue
        empty_val = float(empty.iloc[0][spec.col])
        for cond in SEEDED:
            cell = block[block["condition"] == cond]
            if cell.empty:
                continue
            val = float(cell.iloc[0][spec.col])
            rows.append({
                "model_display": model,
                "n_agents": n_agents,
                "condition": cond,
                "condition_label": CONDITION_LABELS[cond],
                "raw_diff": val - empty_val,
                "collapse_diff": (val - empty_val) * spec.direction,
            })
    return pd.DataFrame(rows)


def plot_metric(metric_key: str) -> None:
    spec = METRICS[metric_key]
    diffs = matched_diffs(metric_key)
    fig, ax = plt.subplots(figsize=(10.6, 5.0), layout="constrained")
    x_positions = {cond: i for i, cond in enumerate(SEEDED)}
    rng_offsets = {}
    for idx, (model, n_agents) in enumerate(sorted(diffs[["model_display", "n_agents"]].drop_duplicates().itertuples(index=False), key=lambda x: (x[0], x[1]))):
        rng_offsets[(model, n_agents)] = (idx - 3.5) * 0.035
    for _, row in diffs.iterrows():
        x = x_positions[row["condition"]] + rng_offsets[(row["model_display"], row["n_agents"])]
        ax.scatter(x, row["raw_diff"], s=42, marker=MODEL_MARKERS.get(row["model_display"], "o"), color="#6b7280", alpha=0.75, edgecolor="white", linewidth=0.4)
    med = diffs.groupby("condition")["raw_diff"].median().reindex(SEEDED)
    ax.scatter(range(len(SEEDED)), med.values, s=115, marker="_", color="#111111", linewidth=3.0, label="median matched difference")
    add_zero_line(ax)
    ax.set_xticks(range(len(SEEDED)))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in SEEDED], rotation=20, ha="right")
    ax.set_ylabel(f"Condition delta minus empty-feed delta\n{spec.label}")
    ax.set_title(f"Did seeds add collapse beyond the empty feed? {spec.short_label}")
    ax.grid(axis="y", color="#dddddd", lw=0.7)
    ax.text(0.01, 0.98, "Each gray point is one matched model and scale block", transform=ax.transAxes, ha="left", va="top", fontsize=9, color="#444444")
    save_figure(fig, OUT / f"condition_vs_empty_{spec.filename_stem}.png")


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    for metric_key in PRIMARY_METRICS:
        plot_metric(metric_key)
    print(f"wrote condition versus empty plots to {OUT}")


if __name__ == "__main__":
    main()
