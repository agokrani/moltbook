#!/usr/bin/env python3
"""Build canonical 48 design-matrix plots."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import (
    CONDITION_LABELS,
    CONDITION_ORDER,
    METRICS,
    MODEL_ORDER,
    PLOT_ROOT,
    PRIMARY_METRICS,
    SCALE_LABELS,
    SCALE_ORDER,
    color_for_metric,
    load_run_deltas,
    metric_title,
    save_figure,
    setup_style,
    symmetric_limits,
)

OUT = PLOT_ROOT / "canonical"


def canonical_fixed() -> pd.DataFrame:
    df = load_run_deltas("fixed_15m")
    df = df[df["internal_family_label"] == "single_model_final"].copy()
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype(int)
    return df


def plot_matrix(df: pd.DataFrame, metric_key: str) -> None:
    spec = METRICS[metric_key]
    plot_df = df.copy()
    values = pd.to_numeric(plot_df[spec.col], errors="coerce")
    vmin, vmax = symmetric_limits(values)
    fig, axes = plt.subplots(2, 2, figsize=(12.8, 9.0), sharex=True, sharey=True, layout="constrained")
    axes = axes.ravel()
    cmap = plt.get_cmap(color_for_metric(spec)).copy()
    cmap.set_bad("#eeeeee")
    last_im = None
    for ax, model in zip(axes, MODEL_ORDER):
        sub = plot_df[plot_df["model_display"] == model]
        mat = np.full((len(CONDITION_ORDER), len(SCALE_ORDER)), np.nan)
        labels = [["" for _ in SCALE_ORDER] for __ in CONDITION_ORDER]
        for i, cond in enumerate(CONDITION_ORDER):
            for j, n_agents in enumerate(SCALE_ORDER):
                cell = sub[(sub["condition"] == cond) & (sub["n_agents"] == n_agents)]
                if not cell.empty:
                    val = float(cell.iloc[0][spec.col])
                    mat[i, j] = val
                    labels[i][j] = spec.fmt.format(val)
        last_im = ax.imshow(np.ma.masked_invalid(mat), vmin=vmin, vmax=vmax, cmap=cmap, aspect="auto")
        ax.set_title(model, fontsize=13, pad=8)
        ax.set_xticks(np.arange(len(SCALE_ORDER)))
        ax.set_xticklabels([SCALE_LABELS[n] for n in SCALE_ORDER])
        ax.set_yticks(np.arange(len(CONDITION_ORDER)))
        ax.set_yticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER])
        ax.set_xticks(np.arange(-0.5, len(SCALE_ORDER), 1), minor=True)
        ax.set_yticks(np.arange(-0.5, len(CONDITION_ORDER), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="minor", bottom=False, left=False)
        for i in range(len(CONDITION_ORDER)):
            for j in range(len(SCALE_ORDER)):
                if labels[i][j]:
                    ax.text(j, i, labels[i][j], ha="center", va="center", fontsize=8.5, color="#111111")
    fig.suptitle(f"Canonical 48 runs: {metric_title(spec)}", fontsize=16)
    if last_im is not None:
        cbar = fig.colorbar(last_im, ax=axes.tolist(), shrink=0.84, pad=0.02)
        cbar.set_label("Late minus early delta. Red = stronger collapse.")
    save_figure(fig, OUT / f"canonical_delta_matrix_{spec.filename_stem}.png")


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    df = canonical_fixed()
    for metric_key in PRIMARY_METRICS:
        plot_matrix(df, metric_key)
    manifest = {
        "rows": int(len(df)),
        "runs": int(df["run_uid"].nunique()),
        "outputs": [f"canonical_delta_matrix_{METRICS[k].filename_stem}.png" for k in PRIMARY_METRICS],
    }
    (OUT / "canonical_design_manifest.json").write_text(pd.Series(manifest).to_json(indent=2))
    print(f"wrote canonical design plots to {OUT}")


if __name__ == "__main__":
    main()
