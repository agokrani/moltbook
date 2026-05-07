#!/usr/bin/env python3
"""Build matched n10 model and roster comparison matrices."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    CONDITION_LABELS,
    CONDITION_ORDER,
    METRICS,
    N10_MODEL_ORDER,
    PLOT_ROOT,
    PRIMARY_METRICS,
    color_for_metric,
    load_run_deltas,
    save_figure,
    setup_style,
    symmetric_limits,
)

OUT = PLOT_ROOT / "n10"
INCLUDED_FAMILIES = ["single_model_final", "base_model_as_tool", "mixed_model_roster"]


def n10_df() -> pd.DataFrame:
    df = load_run_deltas("fixed_15m")
    df = df[df["internal_family_label"].isin(INCLUDED_FAMILIES)].copy()
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype(int)
    df = df[df["n_agents"] == 10].copy()
    return df


def plot_metric(metric_key: str) -> None:
    spec = METRICS[metric_key]
    df = n10_df()
    df[spec.col] = pd.to_numeric(df[spec.col], errors="coerce")
    values = df[spec.col]
    vmin, vmax = symmetric_limits(values)
    mat = np.full((len(N10_MODEL_ORDER), len(CONDITION_ORDER)), np.nan)
    labels = [["" for _ in CONDITION_ORDER] for __ in N10_MODEL_ORDER]
    for i, model in enumerate(N10_MODEL_ORDER):
        for j, cond in enumerate(CONDITION_ORDER):
            cell = df[(df["model_display"] == model) & (df["condition"] == cond)]
            if not cell.empty:
                val = float(cell[spec.col].mean())
                mat[i, j] = val
                labels[i][j] = spec.fmt.format(val)

    fig, ax = plt.subplots(figsize=(12.2, 6.8), layout="constrained")
    cmap = plt.get_cmap(color_for_metric(spec)).copy()
    cmap.set_bad("#eeeeee")
    im = ax.imshow(np.ma.masked_invalid(mat), vmin=vmin, vmax=vmax, cmap=cmap, aspect="auto")
    ax.set_xticks(np.arange(len(CONDITION_ORDER)))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER], rotation=25, ha="right")
    ax.set_yticks(np.arange(len(N10_MODEL_ORDER)))
    ax.set_yticklabels(N10_MODEL_ORDER)
    ax.set_xticks(np.arange(-0.5, len(CONDITION_ORDER), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(N10_MODEL_ORDER), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.tick_params(which="minor", bottom=False, left=False)
    for i in range(len(N10_MODEL_ORDER)):
        for j in range(len(CONDITION_ORDER)):
            if labels[i][j]:
                ax.text(j, i, labels[i][j], ha="center", va="center", fontsize=8.5, color="#111111")
    cbar = fig.colorbar(im, ax=ax, shrink=0.86, pad=0.02)
    cbar.set_label("Late minus early delta. Red = stronger collapse.")
    ax.set_title(f"Matched 10-agent comparison: {spec.label}", fontsize=15)
    save_figure(fig, OUT / f"n10_model_condition_matrix_{spec.filename_stem}.png")


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    for metric_key in PRIMARY_METRICS:
        plot_metric(metric_key)
    print(f"wrote n10 comparison plots to {OUT}")


if __name__ == "__main__":
    main()
