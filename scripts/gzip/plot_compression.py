#!/usr/bin/env python3
"""Plot canonical compression-ratio results from compute_compression.py."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

PALETTE = ["#2ecc71", "#e74c3c", "#e67e22", "#9b59b6", "#3498db", "#1abc9c", "#f39c12", "#c0392b"]
MARKERS = ["s", "o", "^", "D", "v", "P", "X", "*"]

ALG_STYLES = {
    "gzip": {"linestyle": "-", "marker": "o"},
    "bzip2": {"linestyle": "--", "marker": "s"},
    "zlib": {"linestyle": ":", "marker": "^"},
}

CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
SET_ORDER = ["GPT-5 n10", "GPT-5 n20", "GPT-5 n30", "Gemini n10", "Gemini n20", "Gemini n30", "Kimi n10", "GLM-5 n10"]


def set_scale_label(row: dict) -> str:
    return f"{row['set']} {row['scale']}"


def ordered(values, preferred):
    return [v for v in preferred if v in values] + sorted(v for v in values if v not in preferred)


def plot_trajectories(results, algorithm, output_dir, n_quartiles):
    conditions = ordered(set(r["condition"] for r in results), CONDITION_ORDER)
    labels = ordered(set(set_scale_label(r) for r in results), SET_ORDER)

    n_cols = 3
    n_rows = math.ceil(len(conditions) / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6.5 * n_cols, 5.2 * n_rows), sharey=True, squeeze=False)
    fig.suptitle(
        f"Canonical Compression Ratio ({algorithm}) — First 60 Minutes\n"
        f"Fixed 15-minute bins; lower = more compressible",
        fontsize=14,
        fontweight="bold",
        y=1.0,
    )

    x_ticks = list(range(1, n_quartiles + 1))
    for idx, cond in enumerate(conditions):
        ax = axes[idx // n_cols][idx % n_cols]
        ax.set_title(cond.upper(), fontsize=13, fontweight="bold")
        ax.set_xlabel("15-minute bin")
        if idx % n_cols == 0:
            ax.set_ylabel("Compression ratio")
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(["0–15", "15–30", "30–45", "45–60"])
        ax.grid(True, alpha=0.3)

        for s_idx, label in enumerate(labels):
            matches = [r for r in results if r["condition"] == cond and set_scale_label(r) == label]
            if not matches:
                continue
            r = matches[0]
            values = [b["ratios"][algorithm] for b in r["bins"]]
            delta = r["deltas"].get(algorithm, 0)
            ax.plot(
                x_ticks[:len(values)], values,
                color=PALETTE[s_idx % len(PALETTE)],
                marker=MARKERS[s_idx % len(MARKERS)],
                linewidth=1.6,
                markersize=5,
                label=f"{label} ({delta:+.3f})",
                alpha=0.9,
            )
        ax.legend(fontsize=6, loc="best", framealpha=0.9)

    for idx in range(len(conditions), n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = Path(output_dir) / f"compression_{algorithm}_trajectories.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_heatmap(results, algorithm, output_dir):
    conditions = ordered(set(r["condition"] for r in results), CONDITION_ORDER)
    labels = ordered(set(set_scale_label(r) for r in results), SET_ORDER)

    matrix = []
    for label in labels:
        row = []
        for cond in conditions:
            matches = [r for r in results if r["condition"] == cond and set_scale_label(r) == label]
            row.append(matches[0]["deltas"].get(algorithm, np.nan) if matches else np.nan)
        matrix.append(row)
    arr = np.array(matrix)

    fig, ax = plt.subplots(figsize=(max(8, len(conditions) * 1.5), len(labels) * 0.65 + 2.0))
    im = ax.imshow(arr, cmap="RdYlGn", aspect="auto", vmin=-0.10, vmax=0.03)
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.upper() for c in conditions], fontsize=10)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)

    for i in range(len(labels)):
        for j in range(len(conditions)):
            val = arr[i, j]
            color = "white" if abs(val) > 0.05 else "black"
            ax.text(j, i, f"{val:+.3f}", ha="center", va="center", fontsize=8, fontweight="bold", color=color)

    ax.set_title(f"Canonical Compression Delta ({algorithm}): final bin − first bin", fontsize=13, fontweight="bold")
    plt.colorbar(im, ax=ax, label="Δ ratio; negative = more compressible", shrink=0.8)
    plt.tight_layout()
    out_path = Path(output_dir) / f"compression_{algorithm}_heatmap.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_algorithm_comparison(results, output_dir, n_quartiles):
    algorithms = list(results[0]["bins"][0]["ratios"].keys()) if results else []
    if len(algorithms) < 2:
        return

    # Aggregate mean trajectory across runs for each algorithm.
    x_ticks = list(range(1, n_quartiles + 1))
    fig, ax = plt.subplots(figsize=(8, 5))
    for idx, alg in enumerate(algorithms):
        vals = np.array([[b["ratios"][alg] for b in r["bins"]] for r in results])
        mean = vals.mean(axis=0)
        style = ALG_STYLES.get(alg, {"linestyle": "-", "marker": "o"})
        ax.plot(x_ticks, mean, color=PALETTE[idx], marker=style["marker"], linestyle=style["linestyle"], linewidth=2, label=alg)
    ax.set_title("Mean canonical compression trajectory across 48 runs", fontweight="bold")
    ax.set_xlabel("15-minute bin")
    ax.set_ylabel("Compression ratio")
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(["0–15", "15–30", "30–45", "45–60"])
    ax.grid(True, alpha=0.3)
    ax.legend()
    plt.tight_layout()
    out_path = Path(output_dir) / "compression_algorithm_comparison.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Plot canonical compression results")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--algorithm", default="gzip")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    results = data["results"]
    n_quartiles = data["meta"]["n_quartiles"]
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_trajectories(results, args.algorithm, out_dir, n_quartiles)
    plot_heatmap(results, args.algorithm, out_dir)
    plot_algorithm_comparison(results, out_dir, n_quartiles)


if __name__ == "__main__":
    main()
