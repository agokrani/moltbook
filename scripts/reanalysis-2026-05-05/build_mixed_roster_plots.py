#!/usr/bin/env python3
"""Build mixed-roster plots against homogeneous n10 baselines."""
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

OUT = PLOT_ROOT / "mixed"


def data() -> pd.DataFrame:
    df = load_run_deltas("fixed_15m")
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype(int)
    keep = (
        ((df["internal_family_label"] == "single_model_final") & (df["n_agents"] == 10))
        | (df["internal_family_label"] == "mixed_model_roster")
    )
    return df[keep].copy()


def plot_metric(metric_key: str) -> None:
    spec = METRICS[metric_key]
    df = data()
    df[spec.col] = pd.to_numeric(df[spec.col], errors="coerce")
    hom = df[df["internal_family_label"] == "single_model_final"]
    mixed = df[df["internal_family_label"] == "mixed_model_roster"]

    fig, ax = plt.subplots(figsize=(10.8, 5.2), layout="constrained")
    for j, cond in enumerate(CONDITION_ORDER):
        h = hom[hom["condition"] == cond].sort_values("model_display")
        offsets = np.linspace(-0.18, 0.18, max(len(h), 1))
        for off, (_, row) in zip(offsets, h.iterrows()):
            ax.scatter(j + off, row[spec.col], s=44, color="#9ca3af", edgecolor="white", linewidth=0.4, alpha=0.9)
        if not h.empty:
            ax.scatter(j, h[spec.col].median(), s=90, marker="_", color="#111111", linewidth=3.0)
        m = mixed[mixed["condition"] == cond]
        if not m.empty:
            ax.scatter(j, float(m.iloc[0][spec.col]), s=130, marker="*", color="#d62728", edgecolor="#111111", linewidth=0.6, zorder=4)
    add_zero_line(ax)
    ax.set_xticks(range(len(CONDITION_ORDER)))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER], rotation=25, ha="right")
    ax.set_ylabel(f"{spec.label}\nlate minus early")
    ax.set_title(f"Mixed roster compared with homogeneous 10-agent runs: {spec.short_label}")
    ax.grid(axis="y", color="#dddddd", lw=0.7)
    ax.text(0.01, 0.98, "Gray points are homogeneous n10 models. Red stars are mixed roster runs.", transform=ax.transAxes, ha="left", va="top", fontsize=9, color="#444444")
    save_figure(fig, OUT / f"mixed_vs_homogeneous_n10_{spec.filename_stem}.png")


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    for metric_key in PRIMARY_METRICS:
        plot_metric(metric_key)
    print(f"wrote mixed-roster plots to {OUT}")


if __name__ == "__main__":
    main()
