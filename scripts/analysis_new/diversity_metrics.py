#!/usr/bin/env python3
"""Analysis 5: Diversity metrics over time — novelty rate, effective vocab, top-K concentration."""

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
    SEED_AUTHORS,
    load_all_scales,
    group_records,
)
from time_binned_lexical_metrics_5gram import (
    prepare_posts,
    ngram_counter,
    fixed_time_bins,
    PreparedPost,
)
from entropy_metrics import (
    counts_entropy,
    effective_vocabulary_size,
    top_k_coverage,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
NGRAM_N = 5
BIN_EDGES = [0, 15, 30, 45, 60]
SCALES = ["n10", "n20", "n30"]
OUT_DIR = Path("findings/entropy-collapse-scaling/diversity")
TOP_K_CONCENTRATION = 20
SUBSAMPLE_TARGET = 50  # posts per bin for subsampled metrics
SUBSAMPLE_N = 100
SUBSAMPLE_SEED = 42


def _grams_for_post(post: PreparedPost, n: int) -> list[tuple[str, ...]]:
    """Extract n-grams from a PreparedPost (5gram version)."""
    if n == 1:
        return [(t,) for t in post.tokens]
    return post.ngrams_by_n.get(n, [])


def ngram_counter_n(posts: list[PreparedPost], n: int) -> Counter:
    """Count n-grams across posts."""
    counter: Counter = Counter()
    for post in posts:
        counter.update(_grams_for_post(post, n))
    return counter


def novelty_rate_5gram(bins: list[tuple[int, float, float, list[PreparedPost]]],
                       n: int = NGRAM_N) -> list[dict]:
    """Compute novelty rate for n-grams across time bins (cumulative seen set)."""
    seen: set[tuple[str, ...]] = set()
    rows = []
    for bin_idx, start, end, members in bins:
        total_events = 0
        new_events = 0
        for post in members:
            grams = _grams_for_post(post, n)
            for gram in grams:
                total_events += 1
                if gram not in seen:
                    new_events += 1
                    seen.add(gram)
        rows.append({
            "bin_idx": bin_idx,
            "start": start,
            "end": end,
            "n_posts": len(members),
            "total_ngram_events": total_events,
            "new_ngrams": new_events,
            "novelty_rate": new_events / total_events if total_events else 0.0,
        })
    return rows


def effective_vocab_per_bin(bins: list[tuple[int, float, float, list[PreparedPost]]],
                            n: int = NGRAM_N) -> list[float]:
    """Simpson's reciprocal index per time bin."""
    results = []
    for _, _, _, members in bins:
        counter = ngram_counter_n(members, n)
        results.append(effective_vocabulary_size(counter))
    return results


def top_k_concentration_per_bin(bins: list[tuple[int, float, float, list[PreparedPost]]],
                                n: int = NGRAM_N, k: int = TOP_K_CONCENTRATION) -> list[float]:
    """Top-K n-gram coverage per time bin."""
    results = []
    for _, _, _, members in bins:
        counter = ngram_counter_n(members, n)
        results.append(top_k_coverage(counter, k))
    return results


def subsampled_metric(bins, metric_fn, n: int, target: int = SUBSAMPLE_TARGET,
                      n_samples: int = SUBSAMPLE_N, seed: int = SUBSAMPLE_SEED):
    """Run metric_fn on subsampled bins for corpus-size control."""
    import random
    rng = random.Random(seed)
    results = []
    for bin_idx, start, end, members in bins:
        if len(members) <= target:
            val = metric_fn(members, n)
            results.append({"mean": val, "ci_lo": val, "ci_hi": val})
            continue
        samples = []
        for _ in range(n_samples):
            subset = rng.sample(members, target)
            samples.append(metric_fn(subset, n))
        samples.sort()
        lo = int(0.025 * len(samples))
        hi = int(0.975 * len(samples))
        results.append({
            "mean": sum(samples) / len(samples),
            "ci_lo": samples[lo],
            "ci_hi": samples[hi],
        })
    return results


def _single_effective_vocab(posts, n):
    counter = ngram_counter_n(posts, n)
    return effective_vocabulary_size(counter)


def _single_top_k(posts, n):
    counter = ngram_counter_n(posts, n)
    return top_k_coverage(counter, TOP_K_CONCENTRATION)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales()
    agent_records = [r for r in records if not r.is_seed]
    print(f"  Agent posts: {len(agent_records)}")

    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))

    # Compute metrics per run, per bin
    print("Computing diversity metrics per run/bin...")
    all_rows = []

    for (scale, condition, run_name), recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        bins = fixed_time_bins(prepared, bin_edges=BIN_EDGES)

        # 1. Novelty rates
        novelty = novelty_rate_5gram(bins, n=NGRAM_N)

        # 2. Effective vocabulary size
        eff_vocab = effective_vocab_per_bin(bins, n=NGRAM_N)

        # 3. Top-K concentration
        top_k_conc = top_k_concentration_per_bin(bins, n=NGRAM_N, k=TOP_K_CONCENTRATION)

        # 4. Subsampled versions
        sub_eff = subsampled_metric(bins, _single_effective_vocab, NGRAM_N)
        sub_topk = subsampled_metric(bins, _single_top_k, NGRAM_N)

        for i, (bin_idx, start, end, members) in enumerate(bins):
            row = {
                "scale": scale,
                "condition": condition,
                "run_name": run_name,
                "bin_idx": bin_idx,
                "bin_start": start,
                "bin_end": end,
                "n_posts": len(members),
                "n_agents": len({p.record.author_name for p in members}),
                # Raw metrics
                "novelty_rate": round(novelty[i]["novelty_rate"], 4),
                "new_ngrams": novelty[i]["new_ngrams"],
                "total_ngram_events": novelty[i]["total_ngram_events"],
                "effective_vocab_size": round(eff_vocab[i], 2),
                "top_k_concentration": round(top_k_conc[i], 4),
                # Subsampled
                "effective_vocab_sub_mean": round(sub_eff[i]["mean"], 2),
                "effective_vocab_sub_ci_lo": round(sub_eff[i]["ci_lo"], 2),
                "effective_vocab_sub_ci_hi": round(sub_eff[i]["ci_hi"], 2),
                "top_k_conc_sub_mean": round(sub_topk[i]["mean"], 4),
                "top_k_conc_sub_ci_lo": round(sub_topk[i]["ci_lo"], 4),
                "top_k_conc_sub_ci_hi": round(sub_topk[i]["ci_hi"], 4),
            }
            all_rows.append(row)

    # Write CSV
    csv_path = OUT_DIR / "diversity_metrics.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(all_rows[0].keys()))
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Wrote {csv_path} ({len(all_rows)} rows)")

    # Aggregate by (scale, bin) across all conditions
    agg = defaultdict(lambda: defaultdict(list))
    for row in all_rows:
        key = (row["scale"], row["bin_idx"])
        for metric in ["novelty_rate", "effective_vocab_size", "top_k_concentration",
                        "effective_vocab_sub_mean", "top_k_conc_sub_mean"]:
            agg[key][metric].append(row[metric])

    agg_rows = []
    for (scale, bin_idx), metrics in sorted(agg.items()):
        row = {"scale": scale, "bin_idx": bin_idx, "bin_label": f"{BIN_EDGES[bin_idx]}-{BIN_EDGES[bin_idx+1]}min"}
        for metric, vals in metrics.items():
            row[f"{metric}_mean"] = round(sum(vals) / len(vals), 4)
        agg_rows.append(row)

    agg_path = OUT_DIR / "diversity_metrics_aggregated.csv"
    with agg_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(agg_rows[0].keys()))
        writer.writeheader()
        writer.writerows(agg_rows)
    print(f"Wrote {agg_path}")

    # Also aggregate by (condition, bin)
    agg_cond = defaultdict(lambda: defaultdict(list))
    for row in all_rows:
        key = (row["condition"], row["bin_idx"])
        for metric in ["novelty_rate", "effective_vocab_size", "top_k_concentration"]:
            agg_cond[key][metric].append(row[metric])

    # ---------------------------------------------------------------------------
    # PLOTS
    # ---------------------------------------------------------------------------
    print("Generating 3-panel diversity plot...")

    scale_colors = {"n10": "#66BB6A", "n20": "#42A5F5", "n30": "#AB47BC"}
    bin_centers = [(BIN_EDGES[i] + BIN_EDGES[i + 1]) / 2 for i in range(len(BIN_EDGES) - 1)]

    # Main figure: 3-panel (novelty, effective vocab, top-K concentration)
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    metrics_config = [
        ("novelty_rate_mean", "Novelty Rate (5-gram)",
         "Fraction of 5-grams in each window\nthat have never appeared before"),
        ("effective_vocab_size_mean", "Effective Vocabulary Size (Simpson's 1/D)",
         "Higher = more diverse;\ndrops as a few phrases dominate"),
        ("top_k_concentration_mean", f"Top-{TOP_K_CONCENTRATION} Concentration",
         f"Fraction of all 5-gram usage\ncaptured by the top {TOP_K_CONCENTRATION} phrases"),
    ]

    for ax_idx, (metric_key, title, caption) in enumerate(metrics_config):
        ax = axes[ax_idx]

        for scale in SCALES:
            vals = []
            for bi in range(len(BIN_EDGES) - 1):
                matching = [r for r in agg_rows if r["scale"] == scale and r["bin_idx"] == bi]
                if matching:
                    vals.append(matching[0][metric_key])
                else:
                    vals.append(0)

            ax.plot(bin_centers, vals, marker="o", label=scale, color=scale_colors[scale],
                    linewidth=2, markersize=6)

        ax.set_xlabel("Minutes elapsed")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xticks(bin_centers)
        ax.set_xticklabels([f"{int(BIN_EDGES[i])}-{int(BIN_EDGES[i+1])}" for i in range(len(BIN_EDGES)-1)])
        ax.legend(fontsize=9)
        ax.grid(alpha=0.15)

        # Caption below
        ax.text(0.5, -0.18, caption, transform=ax.transAxes, ha="center",
                fontsize=8, fontstyle="italic", color="#666")

    fig.suptitle("Diversity Metrics Over Time (5-gram, all conditions averaged)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout(rect=[0, 0.05, 1, 0.95])
    fig.savefig(OUT_DIR / "diversity_3panel.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Wrote diversity_3panel.png")

    # Subsampled version
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    sub_metrics = [
        ("effective_vocab_sub_mean_mean", "Effective Vocab Size (subsampled)"),
        ("top_k_conc_sub_mean_mean", f"Top-{TOP_K_CONCENTRATION} Concentration (subsampled)"),
    ]

    for ax_idx, (metric_key, title) in enumerate(sub_metrics):
        ax = axes[ax_idx]
        for scale in SCALES:
            vals = []
            for bi in range(len(BIN_EDGES) - 1):
                matching = [r for r in agg_rows if r["scale"] == scale and r["bin_idx"] == bi]
                if matching:
                    vals.append(matching[0][metric_key])
                else:
                    vals.append(0)
            ax.plot(bin_centers, vals, marker="o", label=scale, color=scale_colors[scale],
                    linewidth=2, markersize=6)

        ax.set_xlabel("Minutes elapsed")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xticks(bin_centers)
        ax.set_xticklabels([f"{int(BIN_EDGES[i])}-{int(BIN_EDGES[i+1])}" for i in range(len(BIN_EDGES)-1)])
        ax.legend(fontsize=9)
        ax.grid(alpha=0.15)

    fig.suptitle("Subsampled Diversity Metrics (controls for corpus size)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "diversity_subsampled.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Wrote diversity_subsampled.png")

    # Per-condition breakdown plot
    print("Generating per-condition diversity plots...")
    cond_colors = {
        "mag0": "#616161", "mag1": "#E53935", "mag5": "#FF7043",
        "mag25": "#FF8F00", "dom-agi": "#1E88E5", "dom-tech": "#43A047",
    }

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))

    for ax_idx, metric in enumerate(["novelty_rate", "effective_vocab_size", "top_k_concentration"]):
        ax = axes[ax_idx]

        for cond in CONDITION_ORDER:
            vals = []
            for bi in range(len(BIN_EDGES) - 1):
                key = (cond, bi)
                if key in agg_cond and metric in agg_cond[key]:
                    v = agg_cond[key][metric]
                    vals.append(sum(v) / len(v))
                else:
                    vals.append(0)
            ax.plot(bin_centers, vals, marker="o",
                    label=CONDITION_LABELS.get(cond, cond),
                    color=cond_colors.get(cond, "#999"),
                    linewidth=1.5, markersize=5)

        ax.set_xlabel("Minutes elapsed")
        titles = {"novelty_rate": "Novelty Rate",
                  "effective_vocab_size": "Effective Vocab Size",
                  "top_k_concentration": f"Top-{TOP_K_CONCENTRATION} Concentration"}
        ax.set_title(titles[metric], fontweight="bold")
        ax.set_xticks(bin_centers)
        ax.set_xticklabels([f"{int(BIN_EDGES[i])}-{int(BIN_EDGES[i+1])}" for i in range(len(BIN_EDGES)-1)])
        ax.legend(fontsize=7, loc="best")
        ax.grid(alpha=0.15)

    fig.suptitle("Diversity Metrics by Condition (all scales combined)",
                 fontsize=13, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "diversity_by_condition.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Wrote diversity_by_condition.png")

    # JSON summary
    summary = {
        "ngram_n": NGRAM_N,
        "bin_edges": BIN_EDGES,
        "top_k": TOP_K_CONCENTRATION,
        "total_runs": len(by_run),
        "total_rows": len(all_rows),
        "aggregated_by_scale": {
            scale: {
                "novelty_rate": [
                    round(next((r[f"novelty_rate_mean"] for r in agg_rows
                                if r["scale"] == scale and r["bin_idx"] == bi), 0), 4)
                    for bi in range(len(BIN_EDGES) - 1)
                ],
                "effective_vocab": [
                    round(next((r[f"effective_vocab_size_mean"] for r in agg_rows
                                if r["scale"] == scale and r["bin_idx"] == bi), 0), 2)
                    for bi in range(len(BIN_EDGES) - 1)
                ],
                "top_k_concentration": [
                    round(next((r[f"top_k_concentration_mean"] for r in agg_rows
                                if r["scale"] == scale and r["bin_idx"] == bi), 0), 4)
                    for bi in range(len(BIN_EDGES) - 1)
                ],
            }
            for scale in SCALES
        },
    }
    with (OUT_DIR / "diversity_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {OUT_DIR / 'diversity_summary.json'}")

    print("\nDone!")


if __name__ == "__main__":
    main()
