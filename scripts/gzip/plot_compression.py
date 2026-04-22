#!/usr/bin/env python3
"""
Plot compression-ratio results from compute_compression.py.

Usage:
    python3 scripts/gzip/plot_compression.py \
        --input results.json \
        --output-dir plots/ \
        --algorithm gzip
"""

import argparse
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PALETTE = ["#2ecc71", "#e74c3c", "#e67e22", "#9b59b6", "#3498db",
           "#1abc9c", "#f39c12", "#c0392b"]
MARKERS = ["s", "o", "^", "D", "v", "P", "X", "*"]

ALG_STYLES = {
    "gzip":  {"linestyle": "-",  "marker": "o"},
    "bzip2": {"linestyle": "--", "marker": "s"},
    "zlib":  {"linestyle": ":",  "marker": "^"},
}


# ---------------------------------------------------------------------------
# Trajectory plot (one subplot per condition, lines per experiment set)
# ---------------------------------------------------------------------------

def plot_trajectories(results, algorithm, output_dir, n_quartiles):
    """Plot per-condition compression ratio trajectories."""
    conditions = sorted(set(r["condition"] for r in results))
    sets = sorted(set(r["set"] for r in results))

    n_conds = len(conditions)
    n_cols = min(3, n_conds)
    n_rows = math.ceil(n_conds / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(6 * n_cols, 5 * n_rows),
                             sharey=True, squeeze=False)

    fig.suptitle(
        f"Compression Ratio ({algorithm}) Temporal Trajectories\n"
        f"({n_quartiles} quartiles, 1-hour experiments)",
        fontsize=14, fontweight="bold", y=1.0,
    )

    x_ticks = list(range(1, n_quartiles + 1))

    for idx, cond in enumerate(conditions):
        ax = axes[idx // n_cols][idx % n_cols]
        ax.set_title(cond.upper(), fontsize=13, fontweight="bold")
        ax.set_xlabel("Time Quartile", fontsize=10)
        if idx % n_cols == 0:
            ax.set_ylabel("Compression Ratio", fontsize=11)

        ax.set_xticks(x_ticks)
        ax.set_xticklabels([f"Q{i}" for i in x_ticks])
        ax.grid(True, alpha=0.3)

        for s_idx, s_label in enumerate(sets):
            matching = [r for r in results
                        if r["set"] == s_label and r["condition"] == cond]
            if not matching:
                continue

            r = matching[0]
            values = [b["ratios"][algorithm] for b in r["bins"]]
            delta = r["deltas"].get(algorithm, 0)
            if len(values) < 2:
                continue

            color = PALETTE[s_idx % len(PALETTE)]
            marker = MARKERS[s_idx % len(MARKERS)]
            label = f"{s_label} (Δ={delta:+.4f})"
            ax.plot(x_ticks[:len(values)], values, color=color,
                    marker=marker, linewidth=1.8, linestyle="--",
                    markersize=7, label=label, alpha=0.9)

        ax.legend(fontsize=7, loc="best", framealpha=0.9)

    for idx in range(n_conds, n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = Path(output_dir) / f"compression_{algorithm}_trajectories.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Delta heatmap (condition x set)
# ---------------------------------------------------------------------------

def plot_heatmap(results, algorithm, output_dir):
    """Plot Q4-Q1 delta heatmap."""
    conditions = sorted(set(r["condition"] for r in results))
    sets = sorted(set(r["set"] for r in results))

    matrix = []
    for s_label in sets:
        row = []
        for cond in conditions:
            matching = [r for r in results
                        if r["set"] == s_label and r["condition"] == cond]
            val = matching[0]["deltas"].get(algorithm, 0) if matching else 0
            row.append(val)
        matrix.append(row)

    arr = np.array(matrix)

    fig, ax = plt.subplots(
        figsize=(max(8, len(conditions) * 1.6), len(sets) * 1.0 + 1.5)
    )

    vmin, vmax = -0.10, 0.03
    im = ax.imshow(arr, cmap="RdYlGn", aspect="auto", vmin=vmin, vmax=vmax)

    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.upper() for c in conditions], fontsize=11)
    ax.set_yticks(range(len(sets)))
    ax.set_yticklabels(sets, fontsize=11)

    for i in range(len(sets)):
        for j in range(len(conditions)):
            val = arr[i, j]
            color = "white" if abs(val) > 0.05 else "black"
            ax.text(j, i, f"{val:+.4f}", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=color)

    ax.set_title(
        f"Compression Ratio ({algorithm}) Temporal Delta (Q4 − Q1)\n"
        f"Green = Stable | Red = More Compressible (Collapse)",
        fontsize=13, fontweight="bold",
    )
    plt.colorbar(im, ax=ax, label="Δ ratio", shrink=0.8)
    plt.tight_layout()

    out_path = Path(output_dir) / f"compression_{algorithm}_heatmap.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# Algorithm comparison (overlay gzip/bzip2/zlib)
# ---------------------------------------------------------------------------

def plot_algorithm_comparison(results, output_dir, n_quartiles):
    """Overlay all algorithms on same axes, one subplot per condition."""
    conditions = sorted(set(r["condition"] for r in results))
    algorithms = list(results[0]["bins"][0]["ratios"].keys()) if results else []

    if len(algorithms) < 2:
        print("Only one algorithm — skipping comparison plot")
        return

    # Use first experiment per condition for simplicity
    n_conds = len(conditions)
    n_cols = min(3, n_conds)
    n_rows = math.ceil(n_conds / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(6 * n_cols, 5 * n_rows),
                             sharey=True, squeeze=False)

    fig.suptitle(
        f"Algorithm Comparison — Compression Ratio Trajectories\n"
        f"({n_quartiles} quartiles)",
        fontsize=14, fontweight="bold", y=1.0,
    )

    x_ticks = list(range(1, n_quartiles + 1))

    for idx, cond in enumerate(conditions):
        ax = axes[idx // n_cols][idx % n_cols]
        ax.set_title(cond.upper(), fontsize=13, fontweight="bold")
        ax.set_xlabel("Time Quartile", fontsize=10)
        if idx % n_cols == 0:
            ax.set_ylabel("Compression Ratio", fontsize=11)
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([f"Q{i}" for i in x_ticks])
        ax.grid(True, alpha=0.3)

        matching = [r for r in results if r["condition"] == cond]
        if not matching:
            continue
        r = matching[0]

        for a_idx, alg in enumerate(algorithms):
            values = [b["ratios"][alg] for b in r["bins"]]
            delta = r["deltas"].get(alg, 0)
            style = ALG_STYLES.get(alg, {"linestyle": "-", "marker": "o"})
            color = PALETTE[a_idx % len(PALETTE)]
            ax.plot(x_ticks[:len(values)], values, color=color,
                    marker=style["marker"], linewidth=1.8,
                    linestyle=style["linestyle"], markersize=7,
                    label=f"{alg} (Δ={delta:+.4f})", alpha=0.9)

        ax.legend(fontsize=7, loc="best", framealpha=0.9)

    for idx in range(n_conds, n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = Path(output_dir) / "compression_algorithm_comparison.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Plot compression-ratio results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--input", required=True,
                        help="JSON results from compute_compression.py")
    parser.add_argument("--output-dir", required=True,
                        help="Directory for plot output")
    parser.add_argument("--algorithm", default="gzip",
                        help="Algorithm for trajectory/heatmap plots (default: gzip)")

    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text())
    results = data["results"]
    n_quartiles = data["meta"]["n_quartiles"]

    if not results:
        print("No results to plot.")
        sys.exit(0)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    plot_trajectories(results, args.algorithm, out_dir, n_quartiles)
    plot_heatmap(results, args.algorithm, out_dir)
    plot_algorithm_comparison(results, out_dir, n_quartiles)

    print(f"\nAll plots saved to {out_dir}/")


if __name__ == "__main__":
    main()
