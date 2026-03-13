#!/usr/bin/env python3
"""Analysis 5: Diversity metrics over time.

Metrics:
  1. distinct-5 (fixed window) — unique 5-grams / total 5-grams per bin (Li et al. 2016)
  2. distinct-5 (cumulative)  — unique 5-grams / total 5-grams from start to bin end
  3. Simpson's 1/D            — effective vocabulary size per bin (Simpson 1949)

Each metric is shown per condition within each scale (n10/n20/n30).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

from load_entropy_data import (
    CONDITION_ORDER,
    CONDITION_LABELS,
    load_all_scales,
    group_records,
)
from time_binned_lexical_metrics_5gram import (
    prepare_posts,
    fixed_time_bins,
    PreparedPost,
)
from entropy_metrics import effective_vocabulary_size

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
NGRAM_N = 5
BIN_EDGES = [0, 15, 30, 45, 60]
SCALES = ["n10", "n20", "n30"]
SCALE_LABELS = {"n10": "10 agents", "n20": "20 agents", "n30": "30 agents"}
OUT_DIR = Path("findings/entropy-collapse-scaling/diversity")

COND_COLORS = {
    "mag0": "#6B7280", "mag1": "#E11D48", "mag5": "#F97316",
    "mag25": "#EAB308", "dom-agi": "#3B82F6", "dom-tech": "#10B981",
}


def _grams_for_post(post: PreparedPost, n: int) -> list[tuple[str, ...]]:
    if n == 1:
        return [(t,) for t in post.tokens]
    return post.ngrams_by_n.get(n, [])


def ngram_counter_n(posts: list[PreparedPost], n: int) -> Counter:
    counter: Counter = Counter()
    for post in posts:
        counter.update(_grams_for_post(post, n))
    return counter


def distinct_n_value(posts: list[PreparedPost], n: int) -> float:
    """distinct-n: unique n-grams / total n-gram tokens (Li et al. 2016)."""
    total = 0
    unique: set[tuple[str, ...]] = set()
    for post in posts:
        grams = _grams_for_post(post, n)
        unique.update(grams)
        total += len(grams)
    return len(unique) / total if total else 0.0


def compute_metrics_per_run(bins: list[tuple[int, float, float, list[PreparedPost]]],
                            n: int = NGRAM_N) -> list[dict]:
    """Compute all three metrics per bin for one run."""
    rows = []
    cumulative_posts: list[PreparedPost] = []

    for bin_idx, start, end, members in bins:
        cumulative_posts.extend(members)

        # 1. distinct-5 fixed window
        d5_fixed = distinct_n_value(members, n)

        # 2. distinct-5 cumulative
        d5_cumulative = distinct_n_value(cumulative_posts, n)

        # 3. Simpson's 1/D per bin
        counter = ngram_counter_n(members, n)
        simpsons = effective_vocabulary_size(counter)

        rows.append({
            "bin_idx": bin_idx,
            "bin_start": start,
            "bin_end": end,
            "n_posts": len(members),
            "distinct_5_fixed": round(d5_fixed, 4),
            "distinct_5_cumulative": round(d5_cumulative, 4),
            "simpsons_1d": round(simpsons, 2),
        })

    return rows


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales()
    agent_records = [r for r in records if not r.is_seed]
    print(f"  Agent posts: {len(agent_records)}")

    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))

    # Compute metrics per run per bin
    print("Computing diversity metrics per run/bin...")
    all_rows = []

    for (scale, condition, run_name), recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        bins = fixed_time_bins(prepared, bin_edges=BIN_EDGES)
        metrics = compute_metrics_per_run(bins, n=NGRAM_N)

        for m in metrics:
            m["scale"] = scale
            m["condition"] = condition
            m["run_name"] = run_name
            all_rows.append(m)

    # Write CSV
    csv_path = OUT_DIR / "diversity_metrics.csv"
    fieldnames = ["scale", "condition", "run_name", "bin_idx", "bin_start", "bin_end",
                  "n_posts", "distinct_5_fixed", "distinct_5_cumulative", "simpsons_1d"]
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {csv_path} ({len(all_rows)} rows)")

    # Build lookup: (scale, condition, bin_idx) -> metric values
    lookup = defaultdict(lambda: defaultdict(list))
    for row in all_rows:
        key = (row["scale"], row["condition"], row["bin_idx"])
        for metric in ["distinct_5_fixed", "distinct_5_cumulative", "simpsons_1d"]:
            lookup[key][metric].append(row[metric])

    n_bins = len(BIN_EDGES) - 1
    bin_centers = [(BIN_EDGES[i] + BIN_EDGES[i + 1]) / 2 for i in range(n_bins)]
    bin_labels = [f"{int(BIN_EDGES[i])}-{int(BIN_EDGES[i+1])}" for i in range(n_bins)]

    # -----------------------------------------------------------------------
    # PLOT: 3 rows (metrics) × 3 columns (scales), 6 condition lines each
    # -----------------------------------------------------------------------
    print("Generating diversity grid plot...")

    metrics_config = [
        ("distinct_5_fixed", "distinct-5 (per window)", "unique / total 5-grams within each 15-min window"),
        ("distinct_5_cumulative", "distinct-5 (cumulative)", "unique / total 5-grams from start to current window"),
        ("simpsons_1d", "Simpson's 1/D (per window)", "effective vocabulary size per window — higher = more diverse"),
    ]

    fig, axes = plt.subplots(
        len(metrics_config), len(SCALES),
        figsize=(20, 16), sharex=True,
    )
    fig.patch.set_facecolor("white")

    for ri, (metric_key, metric_title, metric_caption) in enumerate(metrics_config):
        # Share y-axis within each metric row
        y_min = float("inf")
        y_max = float("-inf")

        for ci, scale in enumerate(SCALES):
            ax = axes[ri, ci]

            for cond in CONDITION_ORDER:
                vals = []
                for bi in range(n_bins):
                    data = lookup[(scale, cond, bi)][metric_key]
                    vals.append(sum(data) / len(data) if data else 0)

                ax.plot(
                    bin_centers, vals,
                    marker="o", markersize=5, linewidth=2,
                    color=COND_COLORS[cond],
                    label=CONDITION_LABELS.get(cond, cond),
                )

                y_min = min(y_min, min(vals) if vals else y_min)
                y_max = max(y_max, max(vals) if vals else y_max)

            ax.set_xticks(bin_centers)
            ax.set_xticklabels(bin_labels, fontsize=8)
            ax.grid(alpha=0.1)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            # Column headers
            if ri == 0:
                ax.set_title(SCALE_LABELS[scale], fontsize=14, fontweight="bold", pad=12)

            # Row labels
            if ci == 0:
                ax.set_ylabel(metric_title, fontsize=11, fontweight="bold")

            # X label on bottom row
            if ri == len(metrics_config) - 1:
                ax.set_xlabel("Minutes", fontsize=10)

            # Legend only in rightmost column
            if ci == len(SCALES) - 1:
                ax.legend(fontsize=7, loc="best", framealpha=0.9)

        # Set consistent y-range for each metric row
        margin = (y_max - y_min) * 0.08
        for ci in range(len(SCALES)):
            axes[ri, ci].set_ylim(y_min - margin, y_max + margin)

    fig.suptitle(
        "Diversity collapse by condition and scale",
        fontsize=20, fontweight="bold", y=1.0, color="#111",
    )
    fig.text(
        0.5, 0.97,
        "Each panel shows 6 conditions within one scale. "
        "All metrics decline over time — agents converge on fewer, more dominant phrases.",
        ha="center", fontsize=11, color="#666",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "diversity_grid.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote diversity_grid.png")

    # -----------------------------------------------------------------------
    # JSON summary
    # -----------------------------------------------------------------------
    summary = {
        "ngram_n": NGRAM_N,
        "bin_edges": BIN_EDGES,
        "metrics": ["distinct_5_fixed", "distinct_5_cumulative", "simpsons_1d"],
        "total_runs": len(by_run),
        "total_rows": len(all_rows),
        "by_scale_condition": {},
    }
    for scale in SCALES:
        for cond in CONDITION_ORDER:
            key_label = f"{scale}/{cond}"
            entry = {}
            for metric in ["distinct_5_fixed", "distinct_5_cumulative", "simpsons_1d"]:
                vals = []
                for bi in range(n_bins):
                    data = lookup[(scale, cond, bi)][metric]
                    vals.append(round(sum(data) / len(data), 4) if data else 0)
                entry[metric] = vals
            summary["by_scale_condition"][key_label] = entry

    with (OUT_DIR / "diversity_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote diversity_summary.json")

    print("\nDone!")


if __name__ == "__main__":
    main()
