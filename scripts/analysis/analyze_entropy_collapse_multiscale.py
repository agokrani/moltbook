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
    first_posts_per_agent,
    last_posts_per_agent,
    multinomial_nb_accuracy,
    novelty_rates,
    prepare_posts,
    window_posts,
)
from load_entropy_data import (  # noqa: E402
    CONDITION_LABELS,
    CONDITION_ORDER,
    SCALE_CONFIG,
    load_all_scales,
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
    plt.figure(figsize=(9, 5))
    for scale in sorted({row["scale"] for row in window_rows}):
        rows = [row for row in window_rows if row["scale"] == scale]
        if not rows:
            continue
        max_window = max(int(row["window_idx"]) for row in rows)
        x = list(range(max_window + 1))
        y = []
        for window_idx in x:
            subset = [row["token_novelty_rate"] for row in rows if int(row["window_idx"]) == window_idx]
            y.append(safe_mean(subset))
        plt.plot(x, y, marker="o", linewidth=2.2, label=scale, color=PLOT_COLORS.get(scale))
    plt.xticks(range(max(int(row["window_idx"]) for row in window_rows) + 1))
    plt.xlabel("Temporal Window")
    plt.ylabel("Mean Token Novelty Rate")
    plt.title("Lexical Novelty Decays Over Time")
    plt.grid(alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(plots_dir / "lexical_novelty_decay_by_scale.png", dpi=180)
    plt.close()


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
        for scale in scales:
            first_subset = [row[metric_key] for row in first_vs_late_rows if row["scale"] == scale and row["segment"] == "first_agent_posts"]
            late_subset = [row[metric_key] for row in first_vs_late_rows if row["scale"] == scale and row["segment"] == "late_window"]
            first_vals.append(safe_mean(first_subset))
            late_vals.append(safe_mean(late_subset))
        ax.bar(x - width / 2, first_vals, width, label="First posts", color="#4c78a8")
        ax.bar(x + width / 2, late_vals, width, label="Late posts", color="#e15759")
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
        for scale in scales:
            subset = [row[metric_key] for row in summary_rows if row["scale"] == scale]
            values.append(safe_mean(subset))
        ax.bar(x, values, color=[PLOT_COLORS.get(scale, "#777777") for scale in scales])
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


def plot_vocabulary_collapse(summary_rows: list[dict], plots_dir: Path) -> None:
    """Grouped bar chart: mean distinct-1 and distinct-2 averaged across conditions, for each scale."""
    scales = sorted({row["scale"] for row in summary_rows})
    d1_vals = []
    d2_vals = []
    for scale in scales:
        subset = [row for row in summary_rows if row["scale"] == scale]
        d1_vals.append(safe_mean([row["distinct_1"] for row in subset]))
        d2_vals.append(safe_mean([row["distinct_2"] for row in subset]))

    x = np.arange(len(scales))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(x - width / 2, d1_vals, width, label="distinct-1 (unigrams)", color="#4c78a8")
    ax.bar(x + width / 2, d2_vals, width, label="distinct-2 (bigrams)", color="#e15759")
    ax.set_xticks(x)
    ax.set_xticklabels(scales)
    ax.set_ylabel("Mean distinct-n ratio")
    ax.set_title("Vocabulary Collapse by Scale")
    ax.legend()
    ax.grid(alpha=0.25, axis="y")

    for i, (v1, v2) in enumerate(zip(d1_vals, d2_vals)):
        ax.text(i - width / 2, v1 + 0.008, f"{v1:.3f}", ha="center", va="bottom", fontsize=8)
        ax.text(i + width / 2, v2 + 0.008, f"{v2:.3f}", ha="center", va="bottom", fontsize=8)

    fig.tight_layout()
    fig.savefig(plots_dir / "vocabulary_collapse_by_scale.png", dpi=180)
    plt.close(fig)


def plot_distinct2_temporal_decay(window_rows: list[dict], plots_dir: Path) -> None:
    """Line chart: mean distinct-2 per window index, one line per scale (averaged across conditions)."""
    scales = sorted({row["scale"] for row in window_rows})
    fig, ax = plt.subplots(figsize=(9, 5))
    for scale in scales:
        rows = [row for row in window_rows if row["scale"] == scale]
        if not rows:
            continue
        max_window = max(int(row["window_idx"]) for row in rows)
        x = list(range(max_window + 1))
        y = []
        for window_idx in x:
            subset = [row["distinct_2"] for row in rows if int(row["window_idx"]) == window_idx]
            y.append(safe_mean(subset))
        ax.plot(x, y, marker="o", linewidth=2.2, label=scale, color=PLOT_COLORS.get(scale))
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
    plot_vocabulary_collapse(summary_rows, plots_dir)
    plot_distinct2_temporal_decay(window_rows, plots_dir)

    print(f"Wrote analysis outputs to {out_dir}")


if __name__ == "__main__":
    main()
