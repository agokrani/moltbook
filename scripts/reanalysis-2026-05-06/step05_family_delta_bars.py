#!/usr/bin/env python3
"""Step 5: family-level run-delta bar chart, two metrics side-by-side.

For each internal family, plot:
    mean Delta effective_topics   (post-text Hill-Shannon)
    mean Delta effective_frames   (LLM-judge Hill-Shannon)
with 95% bootstrap CIs over runs. One panel per binning scheme.

This is the "convergent validity at the effect-size level" figure: same
construct (collapse), two independent measurement methods, paired bars.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DEFAULT_ANALYSIS_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook/analysis/archive-2026-plus-canonical-gemini")
DEFAULT_PLOT_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook-findings-handoff/findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step05_family_delta_bars")

FAMILY_ORDER = ["single_model_final", "base_model_as_tool", "obsession_prompting", "mixed_model_roster"]
FAMILY_LABELS = {
    "single_model_final": "Single-model\nfinal",
    "base_model_as_tool": "Base model\nas tool",
    "obsession_prompting": "Obsession\nprompting",
    "mixed_model_roster": "Mixed-model\nroster",
}
SCHEME_TITLES = {
    "fixed_15m": "Fixed 15-minute first vs last bin",
    "normalized_quartile": "Normalized quartile Q1 vs Q4",
}
METRIC_COLORS = {
    "delta_effective_text": "#3b6ea8",   # blue
    "delta_effective_frame": "#d94f4f",  # red
}
METRIC_LABELS = {
    "delta_effective_text": "Δ effective topics  (post-text embedding)",
    "delta_effective_frame": "Δ effective frames  (LLM-judge dominant_frame)",
}


def setup_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 240,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def bootstrap_ci(vals: Sequence[float], reps: int = 5000, seed: int = 42) -> tuple[float, float, float]:
    x = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
    if len(x) == 0:
        return math.nan, math.nan, math.nan
    if len(x) == 1:
        return float(x[0]), float(x[0]), float(x[0])
    rng = np.random.default_rng(seed)
    means = np.mean(x[rng.integers(0, len(x), size=(reps, len(x)))], axis=1)
    return float(np.mean(x)), float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_test_p(vals: Sequence[float]) -> float:
    x = np.asarray([v for v in vals if np.isfinite(v) and v != 0], dtype=float)
    n = len(x)
    if n == 0:
        return math.nan
    k = min(int(np.sum(x > 0)), int(np.sum(x < 0)))
    p = 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, p))


def merge_run_deltas(text_csv: Path, frame_csv: Path) -> pd.DataFrame:
    t = pd.read_csv(text_csv).rename(columns={
        "delta_effective_topics": "delta_effective_text",
        "delta_dominant_share": "delta_dominant_share_text",
    })
    f = pd.read_csv(frame_csv).rename(columns={
        "delta_effective_frames": "delta_effective_frame",
        "delta_dominant_share": "delta_dominant_share_frame",
    })
    keep_t = ["run_uid", "scheme", "internal_family_label",
              "delta_effective_text", "delta_dominant_share_text"]
    keep_f = ["run_uid", "scheme",
              "delta_effective_frame", "delta_dominant_share_frame"]
    return t[keep_t].merge(f[keep_f], on=["run_uid", "scheme"], how="inner")


def plot_panel(ax: plt.Axes, df: pd.DataFrame, scheme: str) -> None:
    sub = df[df["scheme"] == scheme]
    families = [f for f in FAMILY_ORDER if f in set(sub["internal_family_label"])]
    n_fam = len(families)
    width = 0.38
    xs = np.arange(n_fam, dtype=float)
    for offset, metric in [(-width / 2, "delta_effective_text"), (+width / 2, "delta_effective_frame")]:
        means, lows, highs, ns, ps = [], [], [], [], []
        for fam in families:
            vals = sub.loc[sub["internal_family_label"] == fam, metric].astype(float).to_numpy()
            mean, lo, hi = bootstrap_ci(vals)
            means.append(mean)
            lows.append(lo)
            highs.append(hi)
            ns.append(int(np.isfinite(vals).sum()))
            ps.append(sign_test_p(vals))
        means_a = np.asarray(means)
        yerr = np.vstack([means_a - np.asarray(lows), np.asarray(highs) - means_a])
        bars = ax.bar(xs + offset, means_a, width=width,
                      yerr=yerr, capsize=4,
                      color=METRIC_COLORS[metric], edgecolor="#222", linewidth=.6,
                      label=METRIC_LABELS[metric])
        for bar, mean, p, n in zip(bars, means_a, ps, ns):
            if not np.isfinite(mean):
                continue
            top = bar.get_x() + bar.get_width() / 2
            y = mean - .08 if mean < 0 else mean + .08
            star = ""
            if np.isfinite(p):
                if p < .001:
                    star = "***"
                elif p < .01:
                    star = "**"
                elif p < .05:
                    star = "*"
            ax.text(top, y, f"n={n}{(' ' + star) if star else ''}",
                    ha="center", va="top" if mean < 0 else "bottom",
                    fontsize=8, color="#222")
    ax.axhline(0, color="#111", linewidth=.9)
    ax.set_xticks(xs)
    ax.set_xticklabels([FAMILY_LABELS.get(f, f) for f in families], fontsize=10)
    ax.set_ylabel("Δ Hill-Shannon diversity (final − first bin)")
    ax.set_title(SCHEME_TITLES.get(scheme, scheme), fontsize=12)
    ax.grid(axis="y", alpha=.25)


def save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(path.with_suffix(f".{ext}"), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    ap.add_argument("--plot-root", type=Path, default=DEFAULT_PLOT_ROOT)
    args = ap.parse_args()

    text_delta = args.analysis_root / "ayush_reanalysis/topic_convergence/topic_run_deltas.csv"
    frame_delta = args.analysis_root / "ayush_reanalysis/llm_frame_topic_convergence/frame_topic_run_deltas.csv"
    for p in (text_delta, frame_delta):
        if not p.exists():
            raise SystemExit(f"missing input: {p}")

    setup_style()
    merged = merge_run_deltas(text_delta, frame_delta)

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.6), sharey=False)
    for ax, scheme in zip(axes, ("fixed_15m", "normalized_quartile")):
        plot_panel(ax, merged, scheme)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels,
               loc="upper center", bbox_to_anchor=(0.5, 1.04),
               ncol=2, frameon=False, fontsize=10)
    fig.suptitle(
        "Run-level collapse: same operator (effective N = exp(H)), two inputs",
        y=1.10, fontsize=14,
    )
    fig.tight_layout()
    save_fig(fig, args.plot_root / "family_delta_bars")

    summary_rows = []
    for scheme in ("fixed_15m", "normalized_quartile"):
        sub = merged[merged["scheme"] == scheme]
        for fam in FAMILY_ORDER:
            for metric in ("delta_effective_text", "delta_effective_frame"):
                vals = sub.loc[sub["internal_family_label"] == fam, metric].astype(float).to_numpy()
                mean, lo, hi = bootstrap_ci(vals)
                summary_rows.append({
                    "scheme": scheme,
                    "internal_family_label": fam,
                    "metric": metric,
                    "n_runs": int(np.isfinite(vals).sum()),
                    "mean": mean,
                    "ci95_low": lo,
                    "ci95_high": hi,
                    "n_negative": int((vals < 0).sum()) if vals.size else 0,
                    "n_positive": int((vals > 0).sum()) if vals.size else 0,
                    "sign_p": sign_test_p(vals),
                })
    pd.DataFrame(summary_rows).to_csv(args.plot_root / "family_delta_summary.csv",
                                       index=False, lineterminator="\n")
    print(f"wrote step05 outputs to {args.plot_root}")


if __name__ == "__main__":
    main()
