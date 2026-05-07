#!/usr/bin/env python3
"""Step 1: canonical 10-agent fixed 15-minute trajectories.

This version creates one combined figure per metric. Each figure has four model
panels and six condition lines. It does not include scale, cumulative metrics, or
secondary cohorts.
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd

from common import (
    CONDITION_COLORS,
    CONDITION_ORDER,
    METRICS,
    MODEL_ORDER,
    PLOT_ROOT,
    condition_label,
    load_timebins,
    save_figure,
    setup_style,
)

OUT = PLOT_ROOT / "step01_canonical_n10_trajectories"
BIN_ORDER = ["0-15m", "15-30m", "30-45m", "45-60m"]
BIN_LABELS = ["0-15", "15-30", "30-45", "45-60"]
METRIC_ORDER = ["gzip", "distinct5", "llm_collapse"]


def title_for(metric: dict) -> str:
    if metric["collapse_direction"] == "down":
        return f"Do 10-agent feeds lose diversity over time? {metric['short']}"
    return f"Do 10-agent feeds become more repetitive over time? {metric['short']}"


def metric_data(metric_key: str) -> pd.DataFrame:
    metric = METRICS[metric_key]
    df = load_timebins(metric["source"])
    df = df[
        (df["internal_family_label"] == "single_model_final")
        & (df["scheme"] == "fixed_15m")
        & (df["n_agents"] == 10)
        & (df["model_display"].isin(MODEL_ORDER))
    ].copy()
    if df.empty:
        raise ValueError(f"No data for {metric_key}")
    df["bin_label"] = pd.Categorical(df["bin_label"], categories=BIN_ORDER, ordered=True)
    df[metric["column"]] = pd.to_numeric(df[metric["column"]], errors="coerce")
    return df.sort_values(["model_display", "condition", "bin_label"])


def plot_metric(metric_key: str) -> None:
    metric = METRICS[metric_key]
    df = metric_data(metric_key)

    fig, axes = plt.subplots(2, 2, figsize=(13.8, 8.6), sharex=True, sharey=False)
    fig.subplots_adjust(left=0.08, right=0.82, top=0.88, bottom=0.13, wspace=0.08, hspace=0.28)
    axes = axes.ravel()

    for ax, model in zip(axes, MODEL_ORDER):
        sub = df[df["model_display"] == model]
        for cond in CONDITION_ORDER:
            line = sub[sub["condition"] == cond].sort_values("bin_label")
            if line.empty:
                continue
            x = [BIN_ORDER.index(str(v)) for v in line["bin_label"]]
            y = line[metric["column"]]
            ax.plot(
                x,
                y,
                marker="o",
                markersize=4.7,
                linewidth=1.9,
                color=CONDITION_COLORS[cond],
                label=condition_label(cond),
            )
        ax.set_title(model, pad=8)
        ax.set_xticks(range(len(BIN_LABELS)))
        ax.set_xticklabels(BIN_LABELS)
        ax.grid(axis="y", color="#dddddd", linewidth=0.8)

    axes[0].set_ylabel(metric["label"])
    axes[2].set_ylabel(metric["label"])
    axes[2].set_xlabel("Time in run, minutes")
    axes[3].set_xlabel("Time in run, minutes")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="center left", ncol=1, frameon=False, bbox_to_anchor=(0.84, 0.50))
    fig.suptitle(title_for(metric), y=0.965)
    fig.text(0.08, 0.045, metric["direction_text"], ha="left", va="top", fontsize=10.5, color="#444444")

    out_path = OUT / f"canonical_n10_{metric['file_slug']}_trajectory_by_model.png"
    save_figure(fig, out_path)


def write_readme() -> None:
    readme = """# Step 1 canonical 10-agent trajectories

Each plot shows one metric at the matched 10-agent scale. The four panels are the four canonical models. The lines are the six seed conditions.

These are fixed 15-minute trajectories only. No cumulative metric is included here. No scale comparison is included here.

Files:

- `canonical_n10_gzip_trajectory_by_model.png`
- `canonical_n10_distinct5_trajectory_by_model.png`
- `canonical_n10_llm_collapse_trajectory_by_model.png`

Each model panel uses its own y-axis scale so within-model movement is easier to see.

How to read collapse direction:

- Gzip down means text became easier to compress and more repetitive.
- Distinct-5 down means fewer unique 5-grams.
- LLM collapse index up means more judged repetition, rigidity, conformity, and lower novelty.

## Gzip

![Gzip](canonical_n10_gzip_trajectory_by_model.png)

## Distinct-5

![Distinct-5](canonical_n10_distinct5_trajectory_by_model.png)

## LLM collapse

![LLM collapse](canonical_n10_llm_collapse_trajectory_by_model.png)
"""
    (OUT / "README.md").write_text(readme)


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.png"):
        old.unlink()
    for old in OUT.glob("*.pdf"):
        old.unlink()
    for metric_key in METRIC_ORDER:
        plot_metric(metric_key)
    write_readme()
    print(f"wrote Step 1 combined trajectory plots to {OUT}")


if __name__ == "__main__":
    main()
