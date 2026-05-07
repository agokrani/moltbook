#!/usr/bin/env python3
"""Build diagnostic canonical trajectories."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    CONDITION_LABELS,
    CONDITION_ORDER,
    METRICS,
    MODEL_ORDER,
    PLOT_ROOT,
    SCALE_LABELS,
    SCALE_ORDER,
    load_timebins,
    save_figure,
    setup_style,
)

OUT = PLOT_ROOT / "canonical"

TRAJ = {
    "gzip": ("deterministic", "compression_gzip", "Gzip compression ratio"),
    "distinct5": ("deterministic", "distinct_5", "Distinct-5"),
    "vendi": ("embedding", "vendi_score", "Vendi semantic diversity"),
    "llm_collapse": ("llm", "collapse_index", "Blinded LLM collapse index"),
}
COND_COLORS = {
    "mag0": "#2f6f4e",
    "mag1": "#4c78a8",
    "mag5": "#f58518",
    "mag25": "#e45756",
    "dom-agi": "#7a5195",
    "dom-tech": "#54a24b",
}


def plot_trajectory(metric_key: str) -> None:
    kind, value_col, title = TRAJ[metric_key]
    df = load_timebins(kind, "fixed_15m")
    df = df[df["internal_family_label"] == "single_model_final"].copy()
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype(int)
    df[value_col] = pd.to_numeric(df[value_col], errors="coerce")

    fig, axes = plt.subplots(len(MODEL_ORDER), len(SCALE_ORDER), figsize=(12.8, 10.0), sharex=True, sharey=False, layout="constrained")
    for r, model in enumerate(MODEL_ORDER):
        for c, n_agents in enumerate(SCALE_ORDER):
            ax = axes[r, c]
            sub = df[(df["model_display"] == model) & (df["n_agents"] == n_agents)]
            if sub.empty:
                ax.set_facecolor("#f0f0f0")
                ax.text(0.5, 0.5, "not run", ha="center", va="center", transform=ax.transAxes, color="#777777")
            else:
                for cond in CONDITION_ORDER:
                    line = sub[sub["condition"] == cond].sort_values("bin_idx")
                    if line.empty:
                        continue
                    ax.plot(line["bin_idx"], line[value_col], marker="o", lw=1.8, ms=3.5, color=COND_COLORS[cond], label=CONDITION_LABELS[cond])
                ax.grid(axis="y", color="#dddddd", lw=0.6)
            if r == 0:
                ax.set_title(SCALE_LABELS[n_agents], fontsize=11)
            if c == 0:
                ax.set_ylabel(model)
            ax.set_xticks([0, 1, 2, 3])
            ax.set_xticklabels(["0-15", "15-30", "30-45", "45-60"])
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle(f"Canonical trajectories: {title}", fontsize=16)
    save_figure(fig, OUT / f"canonical_trajectories_{METRICS[metric_key].filename_stem}.png")


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    for metric_key in TRAJ:
        plot_trajectory(metric_key)
    print(f"wrote canonical trajectory plots to {OUT}")


if __name__ == "__main__":
    main()
