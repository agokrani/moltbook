#!/usr/bin/env python3
"""Build paired scale plots for GPT-5 and Gemini Flash Lite."""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from common import (
    CONDITION_LABELS,
    CONDITION_ORDER,
    METRICS,
    PLOT_ROOT,
    PRIMARY_METRICS,
    SCALE_LABELS,
    SCALE_ORDER,
    add_zero_line,
    load_run_deltas,
    save_figure,
    setup_style,
)

OUT = PLOT_ROOT / "scale"
VALID_MODELS = ["GPT-5", "Gemini Flash Lite"]
COND_COLORS = {
    "mag0": "#2f6f4e",
    "mag1": "#4c78a8",
    "mag5": "#f58518",
    "mag25": "#e45756",
    "dom-agi": "#7a5195",
    "dom-tech": "#54a24b",
}


def plot_metric(metric_key: str) -> None:
    spec = METRICS[metric_key]
    df = load_run_deltas("fixed_15m")
    df = df[(df["internal_family_label"] == "single_model_final") & (df["model_display"].isin(VALID_MODELS))].copy()
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype(int)
    df[spec.col] = pd.to_numeric(df[spec.col], errors="coerce")

    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.8), sharey=True, layout="constrained")
    for ax, model in zip(axes, VALID_MODELS):
        sub = df[df["model_display"] == model]
        for cond in CONDITION_ORDER:
            line = sub[sub["condition"] == cond].sort_values("n_agents")
            if len(line) < 2:
                continue
            ax.plot(line["n_agents"], line[spec.col], marker="o", lw=2, ms=5, color=COND_COLORS[cond], label=CONDITION_LABELS[cond])
        add_zero_line(ax)
        ax.set_title(model)
        ax.set_xticks(SCALE_ORDER)
        ax.set_xticklabels([SCALE_LABELS[n] for n in SCALE_ORDER])
        ax.grid(axis="y", color="#dddddd", lw=0.7)
        ax.set_xlabel("Group size")
    axes[0].set_ylabel(f"{spec.label}\nlate minus early")
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, bbox_to_anchor=(0.5, -0.07))
    fig.suptitle(f"Does a larger agent group preserve diversity? {spec.short_label}", fontsize=15)
    save_figure(fig, OUT / f"scale_paired_gpt5_gemini_{spec.filename_stem}.png")


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    for metric_key in PRIMARY_METRICS:
        plot_metric(metric_key)
    print(f"wrote scale paired plots to {OUT}")


if __name__ == "__main__":
    main()
