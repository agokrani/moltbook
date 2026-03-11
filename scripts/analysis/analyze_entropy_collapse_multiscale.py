#!/usr/bin/env python3
"""Run multiscale entropy-collapse analysis across lexical and structural metrics."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/moltbook-cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from entropy_metrics import (  # noqa: E402
    condition_metrics,
    cross_group_similarity,
    distinct_n,
    first_posts_per_agent,
    last_posts_per_agent,
    multinomial_nb_accuracy,
    novelty_rates,
    prepare_posts,
    subsampled_distinct_n,
    window_posts,
)
from load_entropy_data import (  # noqa: E402
    CONDITION_LABELS,
    CONDITION_ORDER,
    SCALE_CONFIG,
    load_all_scales,
)
from stat_utils import (  # noqa: E402
    bootstrap_ci,
    chi_square_proportions,
    cohens_d,
    permutation_test_means,
    spearman_trend,
    wilcoxon_signed_rank,
)

DEFAULT_OUT_DIR = Path("findings/entropy-collapse-multiscale")
PLOT_COLORS = {
    "n10": "#1f77b4",
    "n20": "#ff7f0e",
    "n30": "#2ca02c",
}
FEATURE_COLUMNS = [
    "has_bullets",
    "has_numbered_list",
    "linebreak_rich",
    "imperative_open",
    "question_open",
    "call_to_action",
    "if_then",
    "report_back",
    "receipt",
    "proof_of_work",
    "rollback",
    "checklist",
    "rubric",
    "artifact",
    "falsifier",
    "owner",
    "ledger",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default=str(DEFAULT_OUT_DIR),
        help="Directory for metrics, CSVs, and plots.",
    )
    parser.add_argument(
        "--scales",
        default="n10,n20,n30",
        help="Comma-separated scales to include.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Random seed for sampled metrics.",
    )
    parser.add_argument(
        "--n-windows",
        type=int,
        default=5,
        help="Number of temporal windows per condition.",
    )
    parser.add_argument(
        "--first-posts-per-agent",
        type=int,
        default=2,
        help="Number of earliest and latest posts per agent for matched boundary slices.",
    )
    parser.add_argument(
        "--late-fraction",
        type=float,
        default=0.25,
        help="Fraction of posts from the tail of a condition used for the late window.",
    )
    return parser.parse_args()


def safe_mean(values: list[float]) -> float:
    return float(sum(values) / len(values)) if values else 0.0


def flatten_feature_prevalence(feature_prevalence: dict[str, float]) -> dict[str, float]:
    return {f"feature_{key}": float(feature_prevalence.get(key, 0.0)) for key in FEATURE_COLUMNS}


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = []
    keys = set()
    for row in rows:
        keys.update(row.keys())
    fieldnames = sorted(keys)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_novelty_decay(window_rows: list[dict], plots_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(9, 5))
    for scale in sorted({row["scale"] for row in window_rows}):
        rows = [row for row in window_rows if row["scale"] == scale]
        if not rows:
            continue
        max_window = max(int(row["window_idx"]) for row in rows)
        x = list(range(max_window + 1))
        y = []
        y_lo = []
        y_hi = []
        for window_idx in x:
            subset = [row["token_novelty_rate"] for row in rows if int(row["window_idx"]) == window_idx]
            ci = bootstrap_ci(subset)
            y.append(ci["mean"])
            y_lo.append(ci["ci_lo"])
            y_hi.append(ci["ci_hi"])
        color = PLOT_COLORS.get(scale)
        ax.plot(x, y, marker="o", linewidth=2.2, label=scale, color=color)
        ax.fill_between(x, y_lo, y_hi, alpha=0.15, color=color)
    ax.set_xticks(range(max(int(row["window_idx"]) for row in window_rows) + 1))
    ax.set_xlabel("Temporal Window")
    ax.set_ylabel("Mean Token Novelty Rate")
    ax.set_title("Lexical Novelty Decays Over Time")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "lexical_novelty_decay_by_scale.png", dpi=180)
    plt.close(fig)


def plot_first_vs_late(first_vs_late_rows: list[dict], plots_dir: Path) -> None:
    metrics = [
        ("mean_structural_similarity", "Structural similarity"),
        ("top_10_signature_coverage", "Top-10 signature coverage"),
        ("mean_top20_vocab_overlap", "Agent vocab overlap"),
    ]
    fig, axes = plt.subplots(1, len(metrics), figsize=(14, 4.5), sharex=False)
    if len(metrics) == 1:
        axes = [axes]
    scales = sorted({row["scale"] for row in first_vs_late_rows})
    x = np.arange(len(scales))
    width = 0.35
    for ax, (metric_key, title) in zip(axes, metrics):
        first_vals = []
        late_vals = []
        first_errs = [[], []]
        late_errs = [[], []]
        for scale in scales:
            first_subset = [row[metric_key] for row in first_vs_late_rows if row["scale"] == scale and row["segment"] == "first_agent_posts"]
            late_subset = [row[metric_key] for row in first_vs_late_rows if row["scale"] == scale and row["segment"] == "late_window"]
            f_ci = bootstrap_ci(first_subset)
            l_ci = bootstrap_ci(late_subset)
            first_vals.append(f_ci["mean"])
            late_vals.append(l_ci["mean"])
            first_errs[0].append(f_ci["mean"] - f_ci["ci_lo"])
            first_errs[1].append(f_ci["ci_hi"] - f_ci["mean"])
            late_errs[0].append(l_ci["mean"] - l_ci["ci_lo"])
            late_errs[1].append(l_ci["ci_hi"] - l_ci["mean"])
        ax.bar(x - width / 2, first_vals, width, yerr=first_errs, capsize=4,
               label="First posts", color="#4c78a8")
        ax.bar(x + width / 2, late_vals, width, yerr=late_errs, capsize=4,
               label="Late posts", color="#e15759")
        ax.set_xticks(x)
        ax.set_xticklabels(scales)
        ax.set_title(title)
        ax.grid(alpha=0.2, axis="y")
    axes[0].legend()
    fig.suptitle("First Posts vs Late Posts")
    fig.tight_layout()
    fig.savefig(plots_dir / "first_vs_late_structural_convergence.png", dpi=180)
    plt.close(fig)


def plot_first_vs_last_agent_posts(first_vs_late_rows: list[dict], plots_dir: Path, per_agent_n: int) -> None:
    metrics = [
        ("mean_structural_similarity", "Structural similarity"),
        ("top_10_signature_coverage", "Top-10 signature coverage"),
        ("mean_top20_vocab_overlap", "Agent vocab overlap"),
    ]
    fig, axes = plt.subplots(1, len(metrics), figsize=(14, 4.5), sharex=False)
    if len(metrics) == 1:
        axes = [axes]
    scales = sorted({row["scale"] for row in first_vs_late_rows})
    x = np.arange(len(scales))
    width = 0.35
    for ax, (metric_key, title) in zip(axes, metrics):
        first_vals = []
        last_vals = []
        for scale in scales:
            first_subset = [
                row[metric_key]
                for row in first_vs_late_rows
                if row["scale"] == scale and row["segment"] == "first_agent_posts"
            ]
            last_subset = [
                row[metric_key]
                for row in first_vs_late_rows
                if row["scale"] == scale and row["segment"] == "last_agent_posts"
            ]
            first_vals.append(safe_mean(first_subset))
            last_vals.append(safe_mean(last_subset))
        ax.bar(x - width / 2, first_vals, width, label=f"First {per_agent_n}", color="#4c78a8")
        ax.bar(x + width / 2, last_vals, width, label=f"Last {per_agent_n}", color="#f28e2b")
        ax.set_xticks(x)
        ax.set_xticklabels(scales)
        ax.set_title(title)
        ax.grid(alpha=0.2, axis="y")
    axes[0].legend()
    fig.suptitle(f"First {per_agent_n} Posts vs Last {per_agent_n} Posts Per Agent")
    fig.tight_layout()
    fig.savefig(plots_dir / "first_vs_last_agent_posts.png", dpi=180)
    plt.close(fig)


def plot_predictability(separability_rows: list[dict], plots_dir: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 5))
    scales = sorted({row["scale"] for row in separability_rows})
    categories = [
        ("condition", "overall", "Condition overall"),
        ("condition", "late", "Condition late"),
        ("agent", "overall", "Agent overall"),
        ("agent", "late", "Agent late"),
    ]
    x = np.arange(len(scales))
    width = 0.18
    for idx, (target, segment, label) in enumerate(categories):
        values = []
        for scale in scales:
            subset = [
                row["lift_over_baseline"]
                for row in separability_rows
                if row["scale"] == scale and row["target"] == target and row["segment"] == segment
            ]
            values.append(safe_mean(subset))
        ax.bar(x + (idx - 1.5) * width, values, width, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    ax.set_ylabel("Accuracy lift over baseline")
    ax.set_title("Condition Signal Persists While Agent Signal Flattens")
    ax.axhline(0.0, color="#333333", linewidth=1)
    ax.grid(alpha=0.25, axis="y")
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "agent_vs_condition_predictability.png", dpi=180)
    plt.close(fig)


def plot_template_reuse(summary_rows: list[dict], plots_dir: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
    metrics = [
        ("near_duplicate_rate", "Near duplicate rate"),
        ("mean_structural_similarity", "Structural similarity"),
        ("top_10_signature_coverage", "Top-10 signature coverage"),
    ]
    scales = sorted({row["scale"] for row in summary_rows})
    x = np.arange(len(scales))
    for ax, (metric_key, title) in zip(axes, metrics):
        values = []
        err_lo = []
        err_hi = []
        for scale in scales:
            subset = [row[metric_key] for row in summary_rows if row["scale"] == scale]
            ci = bootstrap_ci(subset)
            values.append(ci["mean"])
            err_lo.append(ci["mean"] - ci["ci_lo"])
            err_hi.append(ci["ci_hi"] - ci["mean"])
        ax.bar(x, values, yerr=[err_lo, err_hi], capsize=4,
               color=[PLOT_COLORS.get(scale, "#777777") for scale in scales])
        ax.set_xticks(x)
        ax.set_xticklabels(scales)
        ax.set_title(title)
        ax.grid(alpha=0.25, axis="y")
    fig.suptitle("Template Reuse Remains Strong at Larger Scales")
    fig.tight_layout()
    fig.savefig(plots_dir / "template_reuse_by_scale.png", dpi=180)
    plt.close(fig)


def plot_structural_overlap_heatmap(cross_condition: dict, plots_dir: Path) -> None:
    scales = sorted(cross_condition)
    fig, axes = plt.subplots(1, len(scales), figsize=(5 * len(scales), 4.8))
    if len(scales) == 1:
        axes = [axes]
    for ax, scale in zip(axes, scales):
        matrix = np.array(cross_condition[scale]["structural_matrix"], dtype=float)
        labels = cross_condition[scale]["conditions"]
        im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
        ax.set_title(scale)
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels([CONDITION_LABELS.get(label, label) for label in labels], rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels([CONDITION_LABELS.get(label, label) for label in labels], fontsize=8)
        for row_idx in range(matrix.shape[0]):
            for col_idx in range(matrix.shape[1]):
                ax.text(col_idx, row_idx, f"{matrix[row_idx, col_idx]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=axes, shrink=0.8)
    fig.suptitle("Cross-Condition Structural Overlap")
    fig.subplots_adjust(left=0.05, right=0.92, bottom=0.22, top=0.86, wspace=0.45)
    fig.savefig(plots_dir / "structural_overlap_heatmap.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_vocabulary_collapse(summary_rows: list[dict], plots_dir: Path, subsampled: dict | None = None) -> None:
    """Grouped bar chart: mean distinct-1 and distinct-2 averaged across conditions, for each scale.

    If subsampled data is provided, adds a second panel showing corpus-controlled values with CIs.
    """
    scales = sorted({row["scale"] for row in summary_rows})
    d1_vals = []
    d2_vals = []
    d1_cis = []
    d2_cis = []
    for scale in scales:
        subset = [row for row in summary_rows if row["scale"] == scale]
        d1_list = [row["distinct_1"] for row in subset]
        d2_list = [row["distinct_2"] for row in subset]
        d1_vals.append(safe_mean(d1_list))
        d2_vals.append(safe_mean(d2_list))
        d1_ci = bootstrap_ci(d1_list)
        d2_ci = bootstrap_ci(d2_list)
        d1_cis.append((d1_ci["ci_lo"], d1_ci["ci_hi"]))
        d2_cis.append((d2_ci["ci_lo"], d2_ci["ci_hi"]))

    has_subsampled = subsampled and all(s in subsampled for s in scales)
    n_panels = 2 if has_subsampled else 1
    fig, axes = plt.subplots(1, n_panels, figsize=(7 * n_panels, 5))
    if n_panels == 1:
        axes = [axes]

    x = np.arange(len(scales))
    width = 0.35

    # Panel 1: raw values with error bars
    ax = axes[0]
    d1_err = [[v - lo for v, (lo, _) in zip(d1_vals, d1_cis)],
              [hi - v for v, (_, hi) in zip(d1_vals, d1_cis)]]
    d2_err = [[v - lo for v, (lo, _) in zip(d2_vals, d2_cis)],
              [hi - v for v, (_, hi) in zip(d2_vals, d2_cis)]]
    ax.bar(x - width / 2, d1_vals, width, yerr=d1_err, capsize=4,
           label="distinct-1 (unigrams)", color="#4c78a8")
    ax.bar(x + width / 2, d2_vals, width, yerr=d2_err, capsize=4,
           label="distinct-2 (bigrams)", color="#e15759")
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    ax.set_ylabel("Mean distinct-n ratio")
    ax.set_title("Raw Vocabulary Collapse by Scale")
    ax.legend()
    ax.grid(alpha=0.25, axis="y")
    for i, (v1, v2) in enumerate(zip(d1_vals, d2_vals)):
        ax.text(i - width / 2, v1 + d1_err[1][i] + 0.005, f"{v1:.3f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + width / 2, v2 + d2_err[1][i] + 0.005, f"{v2:.3f}", ha="center", va="bottom", fontsize=8)

    # Panel 2: subsampled values with CIs
    if has_subsampled:
        ax2 = axes[1]
        sub_d1_vals = []
        sub_d2_vals = []
        sub_d1_cis = []
        sub_d2_cis = []
        for scale in scales:
            conds = subsampled[scale]
            d1_means = [v["distinct_1"]["mean"] for v in conds.values()]
            d2_means = [v["distinct_2"]["mean"] for v in conds.values()]
            sub_d1_vals.append(safe_mean(d1_means))
            sub_d2_vals.append(safe_mean(d2_means))
            d1_ci = bootstrap_ci(d1_means)
            d2_ci = bootstrap_ci(d2_means)
            sub_d1_cis.append((d1_ci["ci_lo"], d1_ci["ci_hi"]))
            sub_d2_cis.append((d2_ci["ci_lo"], d2_ci["ci_hi"]))
        sd1_err = [[v - lo for v, (lo, _) in zip(sub_d1_vals, sub_d1_cis)],
                   [hi - v for v, (_, hi) in zip(sub_d1_vals, sub_d1_cis)]]
        sd2_err = [[v - lo for v, (lo, _) in zip(sub_d2_vals, sub_d2_cis)],
                   [hi - v for v, (_, hi) in zip(sub_d2_vals, sub_d2_cis)]]
        ax2.bar(x - width / 2, sub_d1_vals, width, yerr=sd1_err, capsize=4,
                label="distinct-1 (subsampled)", color="#4c78a8", alpha=0.7)
        ax2.bar(x + width / 2, sub_d2_vals, width, yerr=sd2_err, capsize=4,
                label="distinct-2 (subsampled)", color="#e15759", alpha=0.7)
        ax2.set_xticks(x)
        ax2.set_xticklabels(scales)
        ax2.set_ylabel("Mean distinct-n ratio (corpus-controlled)")
        ax2.set_title("Subsampled Vocabulary Collapse (Heaps' Law Controlled)")
        ax2.legend()
        ax2.grid(alpha=0.25, axis="y")
        for i, (v1, v2) in enumerate(zip(sub_d1_vals, sub_d2_vals)):
            ax2.text(i - width / 2, v1 + sd1_err[1][i] + 0.005, f"{v1:.3f}", ha="center", va="bottom", fontsize=8)
            ax2.text(i + width / 2, v2 + sd2_err[1][i] + 0.005, f"{v2:.3f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(plots_dir / "vocabulary_collapse_by_scale.png", dpi=180)
    plt.close(fig)


def plot_distinct2_temporal_decay(window_rows: list[dict], plots_dir: Path) -> None:
    """Line chart: mean distinct-2 per window index, one line per scale, with CI bands."""
    scales = sorted({row["scale"] for row in window_rows})
    fig, ax = plt.subplots(figsize=(9, 5))
    for scale in scales:
        rows = [row for row in window_rows if row["scale"] == scale]
        if not rows:
            continue
        max_window = max(int(row["window_idx"]) for row in rows)
        x = list(range(max_window + 1))
        y = []
        y_lo = []
        y_hi = []
        for window_idx in x:
            subset = [row["distinct_2"] for row in rows if int(row["window_idx"]) == window_idx]
            ci = bootstrap_ci(subset)
            y.append(ci["mean"])
            y_lo.append(ci["ci_lo"])
            y_hi.append(ci["ci_hi"])
        color = PLOT_COLORS.get(scale)
        ax.plot(x, y, marker="o", linewidth=2.2, label=scale, color=color)
        ax.fill_between(x, y_lo, y_hi, alpha=0.15, color=color)
    ax.set_xticks(range(max(int(row["window_idx"]) for row in window_rows) + 1))
    ax.set_xlabel("Temporal Window")
    ax.set_ylabel("Mean Distinct-2 (bigram diversity)")
    ax.set_title("Bigram Diversity Decays Over Time at Every Scale")
    ax.grid(alpha=0.3)
    ax.legend()
    fig.tight_layout()
    fig.savefig(plots_dir / "distinct2_temporal_decay.png", dpi=180)
    plt.close(fig)


def plot_local_vs_global(summary_rows: list[dict], cross_condition: dict, plots_dir: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    scales = sorted({row["scale"] for row in summary_rows})
    lexical_within = []
    lexical_between = []
    structural_within = []
    structural_between = []
    for scale in scales:
        subset = [row for row in summary_rows if row["scale"] == scale]
        lexical_within.append(safe_mean([row["mean_token_jaccard"] for row in subset]))
        structural_within.append(safe_mean([row["mean_structural_similarity"] for row in subset]))
        lexical_matrix = np.array(cross_condition[scale]["token_matrix"], dtype=float)
        structural_matrix = np.array(cross_condition[scale]["structural_matrix"], dtype=float)
        off_diag_token = [
            lexical_matrix[row_idx, col_idx]
            for row_idx in range(lexical_matrix.shape[0])
            for col_idx in range(lexical_matrix.shape[1])
            if row_idx != col_idx
        ]
        off_diag_struct = [
            structural_matrix[row_idx, col_idx]
            for row_idx in range(structural_matrix.shape[0])
            for col_idx in range(structural_matrix.shape[1])
            if row_idx != col_idx
        ]
        lexical_between.append(safe_mean(off_diag_token))
        structural_between.append(safe_mean(off_diag_struct))

    x = np.arange(len(scales))
    width = 0.35
    axes[0].bar(x - width / 2, lexical_within, width, label="Within condition", color="#4c78a8")
    axes[0].bar(x + width / 2, lexical_between, width, label="Between conditions", color="#f28e2b")
    axes[0].set_title("Lexical attractor gap")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(scales)
    axes[0].grid(alpha=0.25, axis="y")
    axes[0].legend()

    axes[1].bar(x - width / 2, structural_within, width, label="Within condition", color="#59a14f")
    axes[1].bar(x + width / 2, structural_between, width, label="Between conditions", color="#e15759")
    axes[1].set_title("Structural basin gap")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(scales)
    axes[1].grid(alpha=0.25, axis="y")

    fig.suptitle("Local Attractors Sit Inside a Narrower Global Basin")
    fig.tight_layout()
    fig.savefig(plots_dir / "local_attractors_vs_global_basin.png", dpi=180)
    plt.close(fig)


def compute_statistical_tests(
    grouped: dict[tuple[str, str], list],
    by_scale: dict[str, list],
    summary_rows: list[dict],
    window_rows: list[dict],
    first_vs_late_rows: list[dict],
    scales: list[str],
    seed: int,
) -> dict:
    """Compute statistical tests for the 4 testable headline claims.

    Returns a dict ready for JSON serialization.
    """
    results: dict = {"claims": {}}

    # ── Claim 1: Vocabulary narrows with scale ──
    # Find minimum post count across all conditions at each scale for subsampling
    min_posts_per_scale: dict[str, int] = {}
    for scale in scales:
        counts = [len(posts) for (s, _), posts in grouped.items() if s == scale]
        min_posts_per_scale[scale] = min(counts) if counts else 0
    global_min = min(min_posts_per_scale.values()) if min_posts_per_scale else 0

    subsampled: dict[str, dict[str, dict]] = {}  # scale -> condition -> {d1, d2}
    for scale in scales:
        subsampled[scale] = {}
        for (s, condition), posts in grouped.items():
            if s != scale:
                continue
            d1 = subsampled_distinct_n(posts, 1, global_min, seed=seed)
            d2 = subsampled_distinct_n(posts, 2, global_min, seed=seed)
            subsampled[scale][condition] = {"distinct_1": d1, "distinct_2": d2}

    # Permutation test: n10 vs n30 subsampled distinct-1
    if "n10" in subsampled and "n30" in subsampled:
        n10_d1 = [v["distinct_1"]["mean"] for v in subsampled["n10"].values()]
        n30_d1 = [v["distinct_1"]["mean"] for v in subsampled["n30"].values()]
        n10_d2 = [v["distinct_2"]["mean"] for v in subsampled["n10"].values()]
        n30_d2 = [v["distinct_2"]["mean"] for v in subsampled["n30"].values()]
        perm_d1 = permutation_test_means(n10_d1, n30_d1, seed=seed)
        perm_d2 = permutation_test_means(n10_d2, n30_d2, seed=seed)
        effect_d1 = cohens_d(n10_d1, n30_d1)
        effect_d2 = cohens_d(n10_d2, n30_d2)
    else:
        perm_d1 = perm_d2 = {"observed_diff": 0, "p_value": 1}
        effect_d1 = effect_d2 = 0.0

    results["claims"]["vocabulary_narrows_with_scale"] = {
        "description": "Vocabulary diversity (distinct-n) decreases from n10 to n30, controlled for corpus size",
        "subsampled_target_size": global_min,
        "subsampled_values": {
            scale: {
                cond: {
                    "distinct_1": vals["distinct_1"]["mean"],
                    "distinct_1_ci": [vals["distinct_1"]["ci_lo"], vals["distinct_1"]["ci_hi"]],
                    "distinct_2": vals["distinct_2"]["mean"],
                    "distinct_2_ci": [vals["distinct_2"]["ci_lo"], vals["distinct_2"]["ci_hi"]],
                }
                for cond, vals in conds.items()
            }
            for scale, conds in subsampled.items()
        },
        "permutation_test_d1_n10_vs_n30": perm_d1,
        "permutation_test_d2_n10_vs_n30": perm_d2,
        "cohens_d_d1": effect_d1,
        "cohens_d_d2": effect_d2,
    }

    # ── Claim 2: Temporal vocabulary decay ──
    temporal_decay: dict[str, dict] = {}
    for scale in scales:
        scale_windows = [r for r in window_rows if r["scale"] == scale]
        if not scale_windows:
            continue
        window_indices = sorted({int(r["window_idx"]) for r in scale_windows})
        # Mean distinct-2 per window (averaged across conditions)
        mean_d2_per_window = []
        for w in window_indices:
            vals = [r["distinct_2"] for r in scale_windows if int(r["window_idx"]) == w]
            mean_d2_per_window.append(safe_mean(vals))
        spearman = spearman_trend(
            [float(w) for w in window_indices],
            mean_d2_per_window,
        )
        # Bootstrap CI on first vs last window difference
        first_vals = [r["distinct_2"] for r in scale_windows if int(r["window_idx"]) == window_indices[0]]
        last_vals = [r["distinct_2"] for r in scale_windows if int(r["window_idx"]) == window_indices[-1]]
        first_ci = bootstrap_ci(first_vals, seed=seed)
        last_ci = bootstrap_ci(last_vals, seed=seed)
        temporal_decay[scale] = {
            "spearman": spearman,
            "first_window_d2": first_ci,
            "last_window_d2": last_ci,
            "mean_d2_per_window": mean_d2_per_window,
        }

    results["claims"]["temporal_vocabulary_decay"] = {
        "description": "Distinct-2 declines over temporal windows within each scale",
        "per_scale": temporal_decay,
    }

    # ── Claim 3: Structural template convergence intensifies ──
    struct_convergence: dict[str, dict] = {}
    for scale in scales:
        struct_sims = [r["mean_structural_similarity"] for r in summary_rows if r["scale"] == scale]
        struct_convergence[scale] = {
            "structural_similarity": bootstrap_ci(struct_sims, seed=seed),
        }

    # Permutation test: n10 vs n30 structural similarity
    if "n10" in struct_convergence and "n30" in struct_convergence:
        n10_ss = [r["mean_structural_similarity"] for r in summary_rows if r["scale"] == "n10"]
        n30_ss = [r["mean_structural_similarity"] for r in summary_rows if r["scale"] == "n30"]
        perm_struct = permutation_test_means(n30_ss, n10_ss, seed=seed)
        effect_struct = cohens_d(n30_ss, n10_ss)
    else:
        perm_struct = {"observed_diff": 0, "p_value": 1}
        effect_struct = 0.0

    # Chi-square on feature prevalence: early vs late windows per scale
    feature_chi2: dict[str, dict] = {}
    key_features = ["imperative_open", "call_to_action", "receipt"]
    for scale in scales:
        scale_windows = [r for r in window_rows if r["scale"] == scale]
        if not scale_windows:
            continue
        window_indices = sorted({int(r["window_idx"]) for r in scale_windows})
        early_rows = [r for r in scale_windows if int(r["window_idx"]) == window_indices[0]]
        late_rows = [r for r in scale_windows if int(r["window_idx"]) == window_indices[-1]]
        chi2_results = {}
        for feat in key_features:
            feat_col = f"feature_{feat}"
            if feat_col not in early_rows[0]:
                continue
            # Convert prevalence to approximate counts
            early_n = sum(r["n_posts"] for r in early_rows)
            late_n = sum(r["n_posts"] for r in late_rows)
            early_present = int(sum(r[feat_col] * r["n_posts"] for r in early_rows))
            late_present = int(sum(r[feat_col] * r["n_posts"] for r in late_rows))
            counts_present = [early_present, late_present]
            counts_absent = [early_n - early_present, late_n - late_present]
            chi2_results[feat] = chi_square_proportions(counts_present, counts_absent)
        feature_chi2[scale] = chi2_results

    results["claims"]["structural_convergence_intensifies"] = {
        "description": "Structural similarity increases from n10 to n30; key features intensify over time",
        "per_scale_structural_sim": {
            scale: data["structural_similarity"] for scale, data in struct_convergence.items()
        },
        "permutation_test_struct_sim_n10_vs_n30": perm_struct,
        "cohens_d_structural_sim": effect_struct,
        "feature_chi_square_early_vs_late": feature_chi2,
    }

    # ── Claim 4: Social convergence, not base-model prior ──
    social_convergence: dict[str, dict] = {}
    for scale in scales:
        first_rows = [r for r in first_vs_late_rows if r["scale"] == scale and r["segment"] == "first_agent_posts"]
        late_rows = [r for r in first_vs_late_rows if r["scale"] == scale and r["segment"] == "late_window"]
        if not first_rows or not late_rows:
            continue
        # Match conditions for paired test
        conditions = sorted(set(r["condition"] for r in first_rows) & set(r["condition"] for r in late_rows))
        first_struct = [next(r["mean_structural_similarity"] for r in first_rows if r["condition"] == c) for c in conditions]
        late_struct = [next(r["mean_structural_similarity"] for r in late_rows if r["condition"] == c) for c in conditions]
        first_vocab = [next(r["mean_top20_vocab_overlap"] for r in first_rows if r["condition"] == c) for c in conditions]
        late_vocab = [next(r["mean_top20_vocab_overlap"] for r in late_rows if r["condition"] == c) for c in conditions]

        # Paired differences with bootstrap CIs
        struct_diffs = [l - f for f, l in zip(first_struct, late_struct)]
        vocab_diffs = [l - f for f, l in zip(first_vocab, late_vocab)]

        social_convergence[scale] = {
            "n_conditions": len(conditions),
            "structural_sim_first": bootstrap_ci(first_struct, seed=seed),
            "structural_sim_late": bootstrap_ci(late_struct, seed=seed),
            "structural_sim_diff": bootstrap_ci(struct_diffs, seed=seed),
            "vocab_overlap_first": bootstrap_ci(first_vocab, seed=seed),
            "vocab_overlap_late": bootstrap_ci(late_vocab, seed=seed),
            "vocab_overlap_diff": bootstrap_ci(vocab_diffs, seed=seed),
            "wilcoxon_structural": wilcoxon_signed_rank(late_struct, first_struct),
            "wilcoxon_vocab": wilcoxon_signed_rank(late_vocab, first_vocab),
        }

    results["claims"]["social_convergence_not_base_model"] = {
        "description": "Late posts are more structurally similar and share more vocabulary than first posts",
        "per_scale": social_convergence,
    }

    # Store subsampled data for plotting
    results["subsampled"] = subsampled

    return results


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    scales = [scale.strip() for scale in args.scales.split(",") if scale.strip()]
    scale_dirs = {scale: SCALE_CONFIG[scale] for scale in scales if scale in SCALE_CONFIG}
    records = load_all_scales(scale_dirs=scale_dirs, include_scales=scales)
    agent_records = [record for record in records if not record.is_seed]
    prepared_posts = prepare_posts(agent_records)

    grouped: dict[tuple[str, str], list] = defaultdict(list)
    by_scale: dict[str, list] = defaultdict(list)
    for post in prepared_posts:
        grouped[(post.record.scale, post.record.condition)].append(post)
        by_scale[post.record.scale].append(post)

    summary_rows: list[dict] = []
    window_rows: list[dict] = []
    first_vs_late_rows: list[dict] = []
    structural_feature_rows: list[dict] = []
    separability_rows: list[dict] = []
    cross_condition: dict[str, dict] = {}
    metrics_json: dict[str, dict] = {
        "meta": {
            "seed": args.seed,
            "n_windows": args.n_windows,
            "first_posts_per_agent": args.first_posts_per_agent,
            "last_posts_per_agent": args.first_posts_per_agent,
            "late_fraction": args.late_fraction,
            "scales": scales,
        },
        "scales": {},
    }

    for scale in scales:
        metrics_json["scales"][scale] = {"conditions": {}, "cross_condition": {}}
        scale_posts = by_scale.get(scale, [])
        if not scale_posts:
            continue

        all_conditions = [condition for condition in CONDITION_ORDER if (scale, condition) in grouped]
        token_matrix = []
        structural_matrix = []

        scale_windows_early = []
        scale_windows_late = []

        for condition in all_conditions:
            posts = sorted(grouped[(scale, condition)], key=lambda post: post.record.created_at)
            metrics = condition_metrics(posts, seed=args.seed)
            row = {"scale": scale, "condition": condition, **{k: v for k, v in metrics.items() if k not in {"feature_prevalence", "top_tokens", "top_signatures"}}}
            row.update(flatten_feature_prevalence(metrics["feature_prevalence"]))
            summary_rows.append(row)
            structural_feature_rows.append(
                {
                    "scale": scale,
                    "condition": condition,
                    "segment": "overall",
                    **flatten_feature_prevalence(metrics["feature_prevalence"]),
                }
            )

            windows = window_posts(posts, n_windows=args.n_windows)
            novelties = novelty_rates(windows)
            if windows:
                scale_windows_early.extend(windows[0])
                scale_windows_late.extend(windows[-1])

            metrics_json["scales"][scale]["conditions"][condition] = {
                "overall": metrics,
                "windows": [],
            }

            for window_idx, window in enumerate(windows):
                window_metric = condition_metrics(window, seed=args.seed)
                novelty = novelties[window_idx]
                row = {
                    "scale": scale,
                    "condition": condition,
                    "window_idx": window_idx,
                    **{k: v for k, v in window_metric.items() if k not in {"feature_prevalence", "top_tokens", "top_signatures"}},
                    **novelty,
                }
                row.update(flatten_feature_prevalence(window_metric["feature_prevalence"]))
                window_rows.append(row)
                metrics_json["scales"][scale]["conditions"][condition]["windows"].append({
                    "window_idx": window_idx,
                    "metrics": window_metric,
                    "novelty": novelty,
                })

                structural_feature_rows.append(
                    {
                        "scale": scale,
                        "condition": condition,
                        "segment": f"window_{window_idx}",
                        **flatten_feature_prevalence(window_metric["feature_prevalence"]),
                    }
                )

            first_segment = first_posts_per_agent(posts, first_n=args.first_posts_per_agent)
            last_segment = last_posts_per_agent(posts, last_n=args.first_posts_per_agent)
            late_count = max(1, int(math.ceil(len(posts) * args.late_fraction)))
            late_segment = posts[-late_count:]
            for segment_name, segment_posts in (
                ("first_agent_posts", first_segment),
                ("last_agent_posts", last_segment),
                ("late_window", late_segment),
            ):
                segment_metrics = condition_metrics(segment_posts, seed=args.seed)
                first_vs_late_rows.append(
                    {
                        "scale": scale,
                        "condition": condition,
                        "segment": segment_name,
                        **{k: v for k, v in segment_metrics.items() if k not in {"feature_prevalence", "top_tokens", "top_signatures"}},
                    }
                )
                structural_feature_rows.append(
                    {
                        "scale": scale,
                        "condition": condition,
                        "segment": segment_name,
                        **flatten_feature_prevalence(segment_metrics["feature_prevalence"]),
                    }
                )

            labels_agent = [post.record.author_name for post in posts]
            early_labels = [post.record.author_name for post in windows[0]] if windows else []
            late_labels = [post.record.author_name for post in windows[-1]] if windows else []
            for segment_name, segment_posts, labels in (
                ("overall", posts, labels_agent),
                ("early", windows[0] if windows else [], early_labels),
                ("late", windows[-1] if windows else [], late_labels),
            ):
                result = multinomial_nb_accuracy(segment_posts, labels, seed=args.seed, max_features=1000)
                separability_rows.append(
                    {
                        "scale": scale,
                        "condition": condition,
                        "target": "agent",
                        "segment": segment_name,
                        **result,
                        "lift_over_baseline": result["accuracy"] - result["baseline"],
                    }
                )

        for left_condition in all_conditions:
            token_row = []
            structural_row = []
            left_posts = grouped[(scale, left_condition)]
            for right_condition in all_conditions:
                right_posts = grouped[(scale, right_condition)]
                if left_condition == right_condition:
                    left_metrics = next(
                        row for row in summary_rows
                        if row["scale"] == scale and row["condition"] == left_condition
                    )
                    token_row.append(left_metrics["mean_token_jaccard"])
                    structural_row.append(left_metrics["mean_structural_similarity"])
                else:
                    token_row.append(cross_group_similarity(left_posts, right_posts, mode="token", seed=args.seed))
                    structural_row.append(cross_group_similarity(left_posts, right_posts, mode="structural", seed=args.seed))
            token_matrix.append(token_row)
            structural_matrix.append(structural_row)

        metrics_json["scales"][scale]["cross_condition"] = {
            "conditions": all_conditions,
            "token_matrix": token_matrix,
            "structural_matrix": structural_matrix,
        }
        cross_condition[scale] = metrics_json["scales"][scale]["cross_condition"]

        condition_labels_all = [post.record.condition for post in scale_posts]
        condition_result = multinomial_nb_accuracy(scale_posts, condition_labels_all, seed=args.seed, max_features=1500)
        separability_rows.append(
            {
                "scale": scale,
                "condition": "ALL",
                "target": "condition",
                "segment": "overall",
                **condition_result,
                "lift_over_baseline": condition_result["accuracy"] - condition_result["baseline"],
            }
        )
        for segment_name, posts_subset in (("early", scale_windows_early), ("late", scale_windows_late)):
            labels = [post.record.condition for post in posts_subset]
            result = multinomial_nb_accuracy(posts_subset, labels, seed=args.seed, max_features=1500)
            separability_rows.append(
                {
                    "scale": scale,
                    "condition": "ALL",
                    "target": "condition",
                    "segment": segment_name,
                    **result,
                    "lift_over_baseline": result["accuracy"] - result["baseline"],
                }
            )

    # ── Statistical tests ──
    print("Computing statistical tests...")
    stat_results = compute_statistical_tests(
        grouped=grouped,
        by_scale=by_scale,
        summary_rows=summary_rows,
        window_rows=window_rows,
        first_vs_late_rows=first_vs_late_rows,
        scales=scales,
        seed=args.seed,
    )
    # Write separate stats JSON (without non-serializable samples lists)
    stat_output = {k: v for k, v in stat_results.items() if k != "subsampled"}
    with (out_dir / "statistical_tests.json").open("w") as handle:
        json.dump(stat_output, handle, indent=2)
    print(f"  Wrote statistical_tests.json")

    metrics_json["summary_rows"] = summary_rows
    metrics_json["window_rows"] = window_rows
    metrics_json["first_vs_late_rows"] = first_vs_late_rows
    metrics_json["separability_rows"] = separability_rows

    write_csv(out_dir / "summary.csv", summary_rows)
    write_csv(out_dir / "windowed_metrics.csv", window_rows)
    write_csv(out_dir / "first_vs_late.csv", first_vs_late_rows)
    write_csv(out_dir / "agent_separability.csv", separability_rows)
    write_csv(out_dir / "structural_features.csv", structural_feature_rows)
    with (out_dir / "metrics.json").open("w") as handle:
        json.dump(metrics_json, handle, indent=2)

    plot_novelty_decay(window_rows, plots_dir)
    plot_first_vs_late(first_vs_late_rows, plots_dir)
    plot_first_vs_last_agent_posts(first_vs_late_rows, plots_dir, args.first_posts_per_agent)
    plot_predictability(separability_rows, plots_dir)
    plot_template_reuse(summary_rows, plots_dir)
    plot_structural_overlap_heatmap(cross_condition, plots_dir)
    plot_local_vs_global(summary_rows, cross_condition, plots_dir)
    plot_vocabulary_collapse(summary_rows, plots_dir, stat_results.get("subsampled"))
    plot_distinct2_temporal_decay(window_rows, plots_dir)

    print(f"Wrote analysis outputs to {out_dir}")


if __name__ == "__main__":
    main()
