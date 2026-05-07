#!/usr/bin/env python3
"""Build obsession-prompting matched plots."""
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

OUT = PLOT_ROOT / "obsession"


def data() -> pd.DataFrame:
    df = load_run_deltas("normalized_quartile")
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype(int)
    baseline = df[(df["internal_family_label"] == "single_model_final") & (df["model_display"] == "GPT-5") & (df["n_agents"] == 10)].copy()
    obs = df[df["internal_family_label"] == "obsession_prompting"].copy()
    return pd.concat([baseline, obs], ignore_index=True)


def plot_metric(metric_key: str) -> None:
    spec = METRICS[metric_key]
    df = data()
    df[spec.col] = pd.to_numeric(df[spec.col], errors="coerce")
    base = df[(df["internal_family_label"] == "single_model_final") & (df["model_display"] == "GPT-5")]
    obs_gpt = df[(df["internal_family_label"] == "obsession_prompting") & (df["model_display"] == "GPT-5")]
    obs_gem = df[(df["internal_family_label"] == "obsession_prompting") & (df["model_display"] == "Gemini Flash Lite")]

    fig, ax = plt.subplots(figsize=(10.6, 5.2), layout="constrained")
    for j, cond in enumerate(CONDITION_ORDER):
        b = base[base["condition"] == cond]
        og = obs_gpt[obs_gpt["condition"] == cond]
        if not b.empty:
            bval = float(b.iloc[0][spec.col])
            ax.scatter(j - 0.12, bval, s=75, color="#111111", marker="o", label="GPT-5 n10 baseline" if j == 0 else None, zorder=3)
        else:
            bval = np.nan
        if not og.empty:
            offsets = np.linspace(0.05, 0.22, len(og))
            med = float(og[spec.col].median())
            if np.isfinite(bval):
                ax.plot([j - 0.12, j + 0.12], [bval, med], color="#d62728", lw=1.4, alpha=0.65)
            for off, (_, row) in zip(offsets, og.iterrows()):
                ax.scatter(j + off, row[spec.col], s=85, color="#d62728", marker="o", edgecolor="white", linewidth=0.5, label="GPT-5 obsession" if j == 0 and off == offsets[0] else None, zorder=4)
            ax.scatter(j + 0.12, med, s=110, marker="_", color="#7f1d1d", linewidth=3.0, zorder=5)
        gem = obs_gem[obs_gem["condition"] == cond]
        if not gem.empty:
            ax.scatter(j + 0.30, float(gem.iloc[0][spec.col]), s=95, color="#1f77b4", marker="D", edgecolor="white", linewidth=0.5, label="Gemini obsession single case", zorder=4)
    add_zero_line(ax)
    ax.set_xticks(range(len(CONDITION_ORDER)))
    ax.set_xticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER], rotation=25, ha="right")
    ax.set_ylabel(f"{spec.label}\nQ4 minus Q1")
    ax.set_title(f"Does obsession prompting change the collapse signature? {spec.short_label}")
    ax.grid(axis="y", color="#dddddd", lw=0.7)
    ax.legend(loc="best", frameon=False)
    stem = spec.filename_stem.replace("fixed15m", "quartile")
    if "quartile" not in stem:
        stem = f"{stem}_quartile"
    save_figure(fig, OUT / f"obsession_vs_gpt5_n10_{stem}.png")


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    for metric_key in PRIMARY_METRICS:
        plot_metric(metric_key)
    print(f"wrote obsession plots to {OUT}")


if __name__ == "__main__":
    main()
