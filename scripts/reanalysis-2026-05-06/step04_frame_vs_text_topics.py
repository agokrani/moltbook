#!/usr/bin/env python3
"""Step 4: side-by-side Hill-Shannon comparison.

Two parallel pipelines, same operator (effective_topics = exp(H)), different
inputs:

    text  : MiniBatchKMeans on Qwen embeddings of *post text*
            -> already in topic_convergence/topic_run_timebin_metrics.csv
    frame : MiniBatchKMeans on Qwen embeddings of *blinded LLM judge
            dominant_frame strings*
            -> step03 output: llm_frame_topic_convergence/
               frame_topic_run_timebin_metrics.csv

If both pipelines see collapse on the same runs, that is convergent validity in
the Campbell-Fiske sense: two independent measurement methods, one construct.

Outputs PNG+PDF figures into FINDINGS/plots/reanalysis-2026-05-06/
step04_frame_vs_text_topics/.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DEFAULT_ANALYSIS_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook/analysis/archive-2026-plus-canonical-gemini")
DEFAULT_PLOT_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook-findings-handoff/findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step04_frame_vs_text_topics")

FAMILY_ORDER = ["single_model_final", "base_model_as_tool", "mixed_model_roster", "obsession_prompting"]
FAMILY_LABELS = {
    "single_model_final": "Single-model final",
    "base_model_as_tool": "Base model as tool",
    "mixed_model_roster": "Mixed-model roster",
    "obsession_prompting": "Obsession prompting",
}
FAMILY_COLORS = {
    "single_model_final": "#d94f4f",
    "base_model_as_tool": "#3b6ea8",
    "mixed_model_roster": "#1b6b42",
    "obsession_prompting": "#7b4ea3",
}
SCHEME_LABELS = {"fixed_15m": "fixed 15m bins", "normalized_quartile": "normalized quartiles"}


def setup_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 220,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(path.with_suffix(f".{ext}"), bbox_inches="tight")
    plt.close(fig)


def family_trajectory(df: pd.DataFrame, metric: str, scheme: str) -> pd.DataFrame:
    sub = df[df["scheme"] == scheme].copy()
    return (sub.groupby(["internal_family_label", "bin_idx", "bin_label"], as_index=False)[metric]
              .mean()
              .sort_values(["internal_family_label", "bin_idx"]))


def plot_dual_trajectories(text_df: pd.DataFrame, frame_df: pd.DataFrame,
                            scheme: str, out_path: Path) -> None:
    text_traj = family_trajectory(text_df, "effective_topics", scheme)
    frame_traj = family_trajectory(frame_df, "effective_frames", scheme)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.4), sharey=False)
    for ax, traj, ylab, title in [
        (axes[0], text_traj, "exp(H) on post-text clusters", "Effective topics (post-text embedding)"),
        (axes[1], frame_traj, "exp(H) on LLM-frame clusters", "Effective frames (LLM-judge dominant_frame)"),
    ]:
        for fam in FAMILY_ORDER:
            s = traj[traj["internal_family_label"] == fam]
            if s.empty:
                continue
            ax.plot(s["bin_label"], s.iloc[:, -1],
                    marker="o", linewidth=2, color=FAMILY_COLORS.get(fam, "#666"),
                    label=FAMILY_LABELS.get(fam, fam))
        ax.set_title(title, fontsize=12)
        ax.set_ylabel(ylab)
        ax.set_xlabel(f"Time bin ({SCHEME_LABELS.get(scheme, scheme)})")
        ax.grid(alpha=.25)
    axes[0].legend(loc="best", frameon=False)
    fig.suptitle(
        "Hill-Shannon diversity: same operator, two views of collapse",
        y=1.02, fontsize=14,
    )
    fig.tight_layout()
    save_fig(fig, out_path)


def merge_run_deltas(text_csv: Path, frame_csv: Path) -> pd.DataFrame:
    t = pd.read_csv(text_csv)
    f = pd.read_csv(frame_csv)
    t = t.rename(columns={"delta_effective_topics": "delta_effective_text",
                          "delta_dominant_share": "delta_dominant_share_text"})
    f = f.rename(columns={"delta_effective_frames": "delta_effective_frame",
                          "delta_dominant_share": "delta_dominant_share_frame"})
    keep_t = ["run_uid", "scheme", "internal_family_label",
              "delta_effective_text", "delta_dominant_share_text"]
    keep_f = ["run_uid", "scheme", "delta_effective_frame", "delta_dominant_share_frame"]
    return t[keep_t].merge(f[keep_f], on=["run_uid", "scheme"], how="inner")


def plot_delta_scatter(merged: pd.DataFrame, scheme: str, out_path: Path) -> None:
    sub = merged[merged["scheme"] == scheme].copy()
    fig, ax = plt.subplots(figsize=(7.0, 6.4))
    for fam in FAMILY_ORDER:
        s = sub[sub["internal_family_label"] == fam]
        if s.empty:
            continue
        ax.scatter(s["delta_effective_text"], s["delta_effective_frame"],
                   s=42, alpha=.75, color=FAMILY_COLORS.get(fam, "#666"),
                   edgecolor="#222", linewidth=.4,
                   label=FAMILY_LABELS.get(fam, fam))
    if not sub.empty:
        x = sub["delta_effective_text"].astype(float).to_numpy()
        y = sub["delta_effective_frame"].astype(float).to_numpy()
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() >= 3:
            r = float(np.corrcoef(x[mask], y[mask])[0, 1])
            lo = float(min(np.min(x[mask]), np.min(y[mask])))
            hi = float(max(np.max(x[mask]), np.max(y[mask])))
            pad = (hi - lo) * .08 if hi > lo else 1.0
            ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad],
                    "--", color="#888", linewidth=.9, label="y = x")
            ax.text(.02, .97, f"Pearson r = {r:.3f}\nn runs = {mask.sum()}",
                    transform=ax.transAxes, va="top", ha="left",
                    fontsize=10,
                    bbox={"boxstyle": "round,pad=0.3", "facecolor": "white",
                          "edgecolor": "#666", "alpha": .85})
    ax.axhline(0, color="#444", linewidth=.6)
    ax.axvline(0, color="#444", linewidth=.6)
    ax.set_xlabel("Δ effective topics (post-text)")
    ax.set_ylabel("Δ effective frames (LLM judge)")
    ax.set_title(f"Convergent validity: per-run Δ comparison ({SCHEME_LABELS.get(scheme, scheme)})")
    ax.legend(loc="lower right", frameon=False, fontsize=9)
    ax.grid(alpha=.25)
    fig.tight_layout()
    save_fig(fig, out_path)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    ap.add_argument("--plot-root", type=Path, default=DEFAULT_PLOT_ROOT)
    args = ap.parse_args()

    text_bin = args.analysis_root / "ayush_reanalysis/topic_convergence/topic_run_timebin_metrics.csv"
    frame_bin = args.analysis_root / "ayush_reanalysis/llm_frame_topic_convergence/frame_topic_run_timebin_metrics.csv"
    text_delta = args.analysis_root / "ayush_reanalysis/topic_convergence/topic_run_deltas.csv"
    frame_delta = args.analysis_root / "ayush_reanalysis/llm_frame_topic_convergence/frame_topic_run_deltas.csv"

    for p in (text_bin, frame_bin, text_delta, frame_delta):
        if not p.exists():
            raise SystemExit(f"missing input: {p}")

    setup_style()
    text_df = pd.read_csv(text_bin)
    frame_df = pd.read_csv(frame_bin)

    args.plot_root.mkdir(parents=True, exist_ok=True)
    for scheme in ("fixed_15m", "normalized_quartile"):
        plot_dual_trajectories(text_df, frame_df, scheme,
                               args.plot_root / f"trajectories_{scheme}")

    merged = merge_run_deltas(text_delta, frame_delta)
    merged.to_csv(args.plot_root / "delta_merged.csv", index=False, lineterminator="\n")
    for scheme in ("fixed_15m", "normalized_quartile"):
        plot_delta_scatter(merged, scheme, args.plot_root / f"delta_scatter_{scheme}")

    print(f"wrote step04 outputs to {args.plot_root}")


if __name__ == "__main__":
    main()
