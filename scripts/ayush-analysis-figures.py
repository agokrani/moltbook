#!/usr/bin/env python3
"""Generate publication/checkpoint figures for Ayush reanalysis outputs."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OUT = Path("analysis/archive-2026-plus-canonical-gemini")
FIG_DIR = OUT / "ayush_reanalysis" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

FAMILY_LABELS = {
    "single_model_final": "Single-model\nfinal",
    "base_model_as_tool": "Base model\nas tool",
    "mixed_model_roster": "Mixed-model\nroster",
    "obsession_prompting": "Obsession\nprompting",
}
SCHEME_LABELS = {
    "fixed_15m": "fixed 15m",
    "normalized_quartile": "quartiles",
}
SCHEME_COLORS = {
    "fixed_15m": "#4C78A8",
    "normalized_quartile": "#F58518",
}


def _format_rows(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    rows = df.copy()
    rows["family_label"] = rows["internal_family_label"].map(FAMILY_LABELS).fillna(rows["internal_family_label"])
    rows["scheme_label"] = rows["scheme"].map(SCHEME_LABELS).fillna(rows["scheme"])
    rows["x_label"] = rows["family_label"] + "\n" + rows["scheme_label"] + "\n(n=" + rows[f"{metric}_n_valid"].fillna(0).astype(int).astype(str) + ")"
    order = [
        ("single_model_final", "fixed_15m"),
        ("single_model_final", "normalized_quartile"),
        ("base_model_as_tool", "fixed_15m"),
        ("base_model_as_tool", "normalized_quartile"),
        ("mixed_model_roster", "fixed_15m"),
        ("mixed_model_roster", "normalized_quartile"),
        ("obsession_prompting", "normalized_quartile"),
    ]
    order_map = {item: idx for idx, item in enumerate(order)}
    rows["_order"] = rows.apply(lambda r: order_map.get((r["internal_family_label"], r["scheme"]), 999), axis=1)
    return rows.sort_values("_order")


def bar_delta(df: pd.DataFrame, metric: str, title: str, ylabel: str, stem: str) -> None:
    rows = _format_rows(df, metric)
    means = rows[f"{metric}_mean"].astype(float).to_numpy()
    lows = rows[f"{metric}_ci_low"].astype(float).to_numpy()
    highs = rows[f"{metric}_ci_high"].astype(float).to_numpy()
    yerr = np.vstack([means - lows, highs - means])
    colors = rows["scheme"].map(SCHEME_COLORS).fillna("#777777").to_list()
    x = np.arange(len(rows))

    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.bar(x, means, yerr=yerr, capsize=4, color=colors, edgecolor="#333333", linewidth=0.6)
    ax.axhline(0, color="#111111", linewidth=0.9)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(rows["x_label"], rotation=0, ha="center", fontsize=8)
    ax.grid(axis="y", alpha=0.25)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(FIG_DIR / f"{stem}.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def manifest_counts() -> None:
    manifest = pd.read_csv(OUT / "data_manifest.csv")
    inc = manifest[manifest["include_in_main"] == True].copy()
    counts = inc.groupby("internal_family_label", as_index=False).agg(
        runs=("run_uid", "nunique"),
        nonseed_posts=("n_posts_nonseed", "sum"),
    )
    counts["label"] = counts["internal_family_label"].map(FAMILY_LABELS).fillna(counts["internal_family_label"])
    counts = counts.sort_values("runs", ascending=False)

    fig, ax1 = plt.subplots(figsize=(8.2, 4.8))
    x = np.arange(len(counts))
    ax1.bar(x - 0.18, counts["runs"], width=0.36, label="runs", color="#4C78A8")
    ax2 = ax1.twinx()
    ax2.bar(x + 0.18, counts["nonseed_posts"], width=0.36, label="non-seed posts", color="#F58518")
    ax1.set_xticks(x)
    ax1.set_xticklabels(counts["label"], fontsize=9)
    ax1.set_ylabel("Included runs")
    ax2.set_ylabel("Included non-seed posts")
    ax1.set_title("Included corpus by analysis family")
    ax1.grid(axis="y", alpha=0.25)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(FIG_DIR / f"manifest_included_corpus.{ext}", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    det = pd.read_csv(OUT / "combined_report" / "deterministic_summary_by_family.csv")
    emb = pd.read_csv(OUT / "combined_report" / "embedding_summary_by_family.csv")
    manifest_counts()
    bar_delta(
        det,
        "delta_compression_gzip",
        "Run-level change in gzip compression ratio (last bin − first bin)",
        "Δ gzip compression ratio",
        "delta_gzip_compression_by_family",
    )
    bar_delta(
        det,
        "delta_distinct_5",
        "Run-level change in Distinct-5 lexical diversity (last bin − first bin)",
        "Δ Distinct-5",
        "delta_distinct5_by_family",
    )
    bar_delta(
        emb,
        "delta_vendi_score",
        "Run-level change in embedding Vendi score (last bin − first bin)",
        "Δ Vendi score",
        "delta_vendi_by_family",
    )
    bar_delta(
        emb,
        "delta_mean_pairwise_cosine",
        "Run-level change in mean pairwise cosine (last bin − first bin)",
        "Δ mean pairwise cosine",
        "delta_pairwise_cosine_by_family",
    )
    print(f"wrote figures to {FIG_DIR}")


if __name__ == "__main__":
    main()
