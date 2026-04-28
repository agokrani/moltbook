#!/usr/bin/env python3
"""Plot MDS topic maps from pre-computed plot data.

Reads plot_data_{model}_{scale}.npz files from compute_topics.py and generates
MDS topic visualizations. No clustering, no MDS recomputation — instant.

Usage:
    python3 scripts/analysis_new/plot_mds.py                          # all models
    python3 scripts/analysis_new/plot_mds.py --models gpt,gemini      # specific models
    python3 scripts/analysis_new/plot_mds.py --conditions mag0,mag25  # specific conditions
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path("findings/entropy-collapse-scaling/topic_convergence_all")
OUT_DIR = DATA_DIR  # plots go alongside the data

MODELS = {
    "gpt": "GPT-5",
    "gemini": "Gemini Flash Lite",
    "glm": "GLM-5",
    "kimi": "Kimi K2.5",
}

SLIDE_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy",
    "mag5": "5 conspiracies",
    "mag25": "25 conspiracies",
    "dom-agi": "25 AGI hype",
    "dom-tech": "25 tech humor",
}

DEFAULT_CONDITIONS = ["mag0", "mag5", "mag25", "dom-agi"]

# 6 maximally distinct topic colors (projector/slide safe)
TOPIC_COLORS = ["#2563EB", "#DC2626", "#16A34A", "#9333EA", "#EA580C", "#0891B2"]

BIN_EDGES_MAX = 60.0  # for temporal colorbar


# ---------------------------------------------------------------------------
# MDS topic map (2x2 grid, one panel per condition)
# ---------------------------------------------------------------------------
def plot_mds_topics(npz_path: Path, json_path: Path, conditions: list[str],
                    model_label: str, out_path: Path) -> None:
    """Generate MDS topic map from saved plot data."""
    npz = np.load(npz_path, allow_pickle=True)
    meta = json.loads(json_path.read_text())

    coords = npz["mds_coords"]
    cond_arr = npz["conditions"]
    cluster_arr = npz["cluster_ids"]
    k = int(npz["k"])
    labels = {int(ki): v for ki, v in meta["labels"].items()}
    scale = npz_path.stem.split("_")[-1]  # e.g. "n10"

    topic_colors = {ci: TOPIC_COLORS[ci] if ci < len(TOPIC_COLORS) else f"C{ci}" for ci in range(k)}

    fig, axes = plt.subplots(2, 2, figsize=(12, 11))

    for idx, cond in enumerate(conditions[:4]):
        ax = axes.flat[idx]
        cond_mask = cond_arr == cond
        other = ~cond_mask

        # Background: all other conditions in light grey
        ax.scatter(coords[other, 0], coords[other, 1], c="#E5E7EB", s=4, alpha=0.25, rasterized=True)

        # Foreground: this condition colored by topic
        for ci in range(k):
            mask = cond_mask & (cluster_arr == ci)
            if mask.sum() == 0:
                continue
            ax.scatter(coords[mask, 0], coords[mask, 1], c=[topic_colors[ci]], s=28, alpha=0.8,
                       label=labels[ci]["label"], edgecolors="white", linewidths=0.3, rasterized=True)

        n_cond = int(cond_mask.sum())
        ax.set_title(f"{SLIDE_LABELS.get(cond, cond)} (n={n_cond})", fontsize=16, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_aspect("equal")
        ax.spines[:].set_visible(False)

    # Shared legend
    handles, leg = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, leg, loc="lower center", ncol=min(k, 6), fontsize=20,
               frameon=True, fancybox=True, shadow=False, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Topic Map — MDS Projection ({model_label}, {scale})", fontsize=18, fontweight="bold")
    plt.subplots_adjust(hspace=0.15, wspace=0.08, top=0.93, bottom=0.08)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out_path.name}")


# ---------------------------------------------------------------------------
# MDS temporal map (2x2, colored by time)
# ---------------------------------------------------------------------------
def plot_mds_temporal(npz_path: Path, conditions: list[str],
                      model_label: str, out_path: Path) -> None:
    """Generate MDS temporal map from saved plot data."""
    npz = np.load(npz_path, allow_pickle=True)
    coords = npz["mds_coords"]
    cond_arr = npz["conditions"]
    minutes_arr = npz["minutes"]
    scale = npz_path.stem.split("_")[-1]
    max_t = BIN_EDGES_MAX

    fig, axes = plt.subplots(2, 2, figsize=(12, 11))
    sc = None

    for idx, cond in enumerate(conditions[:4]):
        ax = axes.flat[idx]
        cond_mask = cond_arr == cond
        cond_times = np.clip(minutes_arr, 0, max_t)
        other = ~cond_mask

        ax.scatter(coords[other, 0], coords[other, 1], c="#E5E7EB", s=4, alpha=0.25, rasterized=True)

        cm = cond_mask & (cond_times <= max_t)
        if cm.sum() > 0:
            sc = ax.scatter(coords[cm, 0], coords[cm, 1], c=cond_times[cm], cmap="coolwarm",
                           s=28, alpha=0.8, vmin=0, vmax=max_t, edgecolors="white", linewidths=0.3, rasterized=True)

        ax.set_title(f"{SLIDE_LABELS.get(cond, cond)}", fontsize=16, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_aspect("equal")
        ax.spines[:].set_visible(False)

    if sc is not None:
        fig.colorbar(sc, ax=axes.ravel().tolist(), shrink=0.5, label="Minutes elapsed", pad=0.02)
    fig.suptitle(f"Temporal Drift — MDS Projection ({model_label}, {scale})", fontsize=18, fontweight="bold")
    plt.subplots_adjust(hspace=0.12, wspace=0.08, top=0.93, bottom=0.03)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved {out_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default="gpt,gemini,glm,kimi",
                        help="Comma-separated model keys")
    parser.add_argument("--conditions", default=None,
                        help="Comma-separated conditions to plot (default: mag0,mag5,mag25,dom-agi)")
    parser.add_argument("--data-dir", default=None, help="Override data directory")
    parser.add_argument("--no-temporal", action="store_true", help="Skip temporal plots")
    args = parser.parse_args()

    global DATA_DIR, OUT_DIR
    if args.data_dir:
        DATA_DIR = Path(args.data_dir)
        OUT_DIR = DATA_DIR

    conditions = args.conditions.split(",") if args.conditions else DEFAULT_CONDITIONS
    model_keys = args.models.split(",")

    print(f"Conditions: {conditions}")
    print(f"Data dir: {DATA_DIR}\n")

    for model_key in model_keys:
        model_label = MODELS.get(model_key, model_key)

        # Find all plot_data files for this model
        pattern = f"plot_data_{model_key}_*.npz"
        npz_files = sorted(DATA_DIR.glob(pattern))

        if not npz_files:
            print(f"  No data for {model_key} (looked for {pattern})")
            continue

        for npz_path in npz_files:
            json_path = npz_path.with_suffix(".json")
            if not json_path.exists():
                print(f"  Missing JSON for {npz_path.name}, skipping")
                continue

            tag = npz_path.stem.replace("plot_data_", "")  # e.g. "gpt_n10"

            print(f"\n{model_label} / {tag}")
            plot_mds_topics(npz_path, json_path, conditions, model_label,
                           OUT_DIR / f"mds_topics_{tag}.png")

            if not args.no_temporal:
                plot_mds_temporal(npz_path, conditions, model_label,
                                 OUT_DIR / f"mds_temporal_{tag}.png")

    print("\nDone.")


if __name__ == "__main__":
    main()
