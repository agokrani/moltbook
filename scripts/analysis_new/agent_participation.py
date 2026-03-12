#!/usr/bin/env python3
"""Analysis 2: Agent participation — how many agents catch each phrase.

Two complementary views:
1. Per-run: For each run's top-5 phrases, what fraction of agents use them?
2. Cross-run: For top-50 global 2-grams (which are universal), participation across runs.
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
    SEED_AUTHORS,
    load_all_scales,
    group_records,
)
from time_binned_lexical_metrics_5gram import prepare_posts, ngrams, tokenize, ngram_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
NGRAM_N = 5
TOP_NGRAMS_PATH = Path("findings/entropy-collapse-multiscale-new-5gram/top_ngrams/top_ngrams.json")
OUT_DIR = Path("findings/entropy-collapse-scaling/participation")
SCALES = ["n10", "n20", "n30"]
SCALE_AGENTS = {"n10": 10, "n20": 20, "n30": 30}


def load_top_bigrams(k: int = 20) -> list[str]:
    with TOP_NGRAMS_PATH.open() as f:
        data = json.load(f)
    return [e["phrase"] for e in data["all_0_60"]["2"][:k]]


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales()
    agent_records = [r for r in records if not r.is_seed]
    print(f"  Agent posts: {len(agent_records)}")

    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))

    # -----------------------------------------------------------------------
    # Part A: Per-run participation for that run's top-5 5-grams
    # -----------------------------------------------------------------------
    print("\nPart A: Per-run top-5 5-gram participation...")
    per_run_rows = []
    example_posts: dict[str, list[dict]] = defaultdict(list)

    for (scale, condition, run_name), recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        counter = ngram_counter(prepared, NGRAM_N)
        top5 = [" ".join(g) for g, _ in counter.most_common(5)]
        total_agents = len({r.author_name for r in recs})

        for phrase in top5:
            # Build per-agent participation + early/late split
            agents_all: set[str] = set()
            agents_early: set[str] = set()
            agents_late: set[str] = set()

            for rec in recs:
                tokens = tokenize(rec.full_text)
                grams = {" ".join(g) for g in ngrams(tokens, NGRAM_N)}
                if phrase in grams:
                    agent = rec.author_name
                    agents_all.add(agent)
                    if rec.minutes_elapsed <= 30:
                        agents_early.add(agent)
                    else:
                        agents_late.add(agent)
                    if len(example_posts[f"{scale}/{condition}/{phrase}"]) < 5:
                        example_posts[f"{scale}/{condition}/{phrase}"].append({
                            "agent": agent,
                            "minute": round(rec.minutes_elapsed, 1),
                            "title": rec.title[:120],
                        })

            per_run_rows.append({
                "scale": scale, "condition": condition, "run_name": run_name,
                "phrase": phrase,
                "phrase_rank": top5.index(phrase) + 1,
                "total_agents": total_agents,
                "agents_with_phrase": len(agents_all),
                "participation_rate": round(len(agents_all) / total_agents, 3) if total_agents else 0,
                "agents_early_0_30": len(agents_early),
                "agents_late_30_60": len(agents_late),
                "early_rate": round(len(agents_early) / total_agents, 3) if total_agents else 0,
                "late_rate": round(len(agents_late) / total_agents, 3) if total_agents else 0,
            })

    csv_path = OUT_DIR / "per_run_participation.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(per_run_rows[0].keys()))
        writer.writeheader()
        writer.writerows(per_run_rows)
    print(f"  Wrote {csv_path} ({len(per_run_rows)} rows)")

    # -----------------------------------------------------------------------
    # Part B: Cross-run participation for universal 2-grams
    # -----------------------------------------------------------------------
    print("\nPart B: Cross-run 2-gram participation...")
    top_bigrams = load_top_bigrams(20)
    bigram_set = set(top_bigrams)

    bigram_rows = []
    for (scale, condition, run_name), recs in sorted(by_run.items()):
        total_agents = len({r.author_name for r in recs})
        agent_grams: dict[str, set[str]] = defaultdict(set)
        agent_grams_early: dict[str, set[str]] = defaultdict(set)
        agent_grams_late: dict[str, set[str]] = defaultdict(set)

        for rec in recs:
            tokens = tokenize(rec.full_text)
            grams = {" ".join(g) for g in ngrams(tokens, 2)}
            relevant = grams & bigram_set
            agent = rec.author_name
            for phrase in relevant:
                agent_grams[phrase].add(agent)
                if rec.minutes_elapsed <= 30:
                    agent_grams_early[phrase].add(agent)
                else:
                    agent_grams_late[phrase].add(agent)

        for phrase in top_bigrams:
            agents_all = agent_grams.get(phrase, set())
            bigram_rows.append({
                "phrase": phrase, "scale": scale, "condition": condition,
                "run_name": run_name, "total_agents": total_agents,
                "agents_with_phrase": len(agents_all),
                "participation_rate": round(len(agents_all) / total_agents, 3) if total_agents else 0,
                "early_rate": round(len(agent_grams_early.get(phrase, set())) / total_agents, 3) if total_agents else 0,
                "late_rate": round(len(agent_grams_late.get(phrase, set())) / total_agents, 3) if total_agents else 0,
            })

    bigram_csv = OUT_DIR / "bigram_participation.csv"
    with bigram_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(bigram_rows[0].keys()))
        writer.writeheader()
        writer.writerows(bigram_rows)
    print(f"  Wrote {bigram_csv} ({len(bigram_rows)} rows)")

    # Write example posts
    with (OUT_DIR / "example_posts.json").open("w") as f:
        json.dump(example_posts, f, indent=2)

    # -----------------------------------------------------------------------
    # PLOTS
    # -----------------------------------------------------------------------
    # Plot 1: Per-run top-1 phrase participation rate across all 18 runs
    print("\nGenerating per-run participation chart...")
    top1_rows = [r for r in per_run_rows if r["phrase_rank"] == 1]

    fig, ax = plt.subplots(figsize=(16, 6))
    cond_colors = {
        "mag0": "#616161", "mag1": "#E53935", "mag5": "#FF7043",
        "mag25": "#FF8F00", "dom-agi": "#1E88E5", "dom-tech": "#43A047",
    }

    x = np.arange(len(top1_rows))
    colors = [cond_colors.get(r["condition"], "#999") for r in top1_rows]
    bars = ax.bar(x, [r["participation_rate"] for r in top1_rows], color=colors,
                  edgecolor="white", linewidth=0.5)

    for bar, r in zip(bars, top1_rows):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02,
                f"{r['agents_with_phrase']}/{r['total_agents']}", ha="center", fontsize=7)

    labels = [f"{r['scale']}\n{CONDITION_LABELS.get(r['condition'], r['condition'])[:10]}" for r in top1_rows]
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7, rotation=45, ha="right")
    ax.set_ylabel("Participation rate")
    ax.set_ylim(0, 1.15)
    ax.axhline(y=0.5, color="gray", linestyle="--", alpha=0.3)
    ax.set_title("Each Run's #1 5-gram: Fraction of Agents Using It\n"
                 "(Different phrases per run, but consistently high adoption)",
                 fontsize=11, fontweight="bold")
    ax.grid(axis="y", alpha=0.15)

    # Legend
    from matplotlib.patches import Patch
    legend_handles = [Patch(facecolor=cond_colors[c], label=CONDITION_LABELS.get(c, c))
                      for c in CONDITION_ORDER]
    ax.legend(handles=legend_handles, fontsize=7, loc="upper right", ncol=2)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "per_run_top1_participation.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Plot 2: Early vs late for per-run top-1 phrases
    print("Generating early vs late chart...")
    fig, axes = plt.subplots(1, 3, figsize=(16, 6), sharey=True)

    for si, scale in enumerate(SCALES):
        ax = axes[si]
        scale_rows = [r for r in top1_rows if r["scale"] == scale]
        y_pos = np.arange(len(scale_rows))

        early = [r["early_rate"] for r in scale_rows]
        late = [r["late_rate"] for r in scale_rows]
        labels_y = [f'{CONDITION_LABELS.get(r["condition"], r["condition"])[:15]}\n'
                     f'"{r["phrase"][:20]}…"' for r in scale_rows]

        ax.barh(y_pos - 0.15, early, height=0.3, label="Early (0-30 min)",
                color="#90CAF9", edgecolor="white")
        ax.barh(y_pos + 0.15, late, height=0.3, label="Late (30-60 min)",
                color="#1565C0", edgecolor="white")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels_y, fontsize=6.5)
        ax.set_xlabel("Participation rate")
        ax.set_title(f"{scale} ({SCALE_AGENTS[scale]} agents)", fontweight="bold")
        ax.set_xlim(0, 1.05)
        ax.legend(fontsize=7, loc="lower right")
        ax.grid(axis="x", alpha=0.2)

    fig.suptitle("Early vs Late Adoption of Each Run's Top 5-gram", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "early_vs_late_per_run.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Plot 3: Universal 2-gram participation across all runs
    print("Generating 2-gram participation heatmap...")
    top10_bigrams = top_bigrams[:10]
    run_keys = sorted(set((r["scale"], r["condition"]) for r in bigram_rows))

    matrix = np.zeros((len(top10_bigrams), len(run_keys)))
    for row in bigram_rows:
        if row["phrase"] in top10_bigrams:
            yi = top10_bigrams.index(row["phrase"])
            xi = run_keys.index((row["scale"], row["condition"]))
            matrix[yi, xi] = row["participation_rate"]

    fig, ax = plt.subplots(figsize=(16, 6))
    im = ax.imshow(matrix, aspect="auto", cmap="YlOrRd", vmin=0, vmax=1, interpolation="nearest")
    run_labels = [f"{s}/{CONDITION_LABELS.get(c, c)[:10]}" for s, c in run_keys]
    ax.set_xticks(range(len(run_labels)))
    ax.set_xticklabels(run_labels, rotation=60, ha="right", fontsize=7)
    ax.set_yticks(range(len(top10_bigrams)))
    ax.set_yticklabels([f'"{p}"' for p in top10_bigrams], fontsize=9)

    for yi in range(matrix.shape[0]):
        for xi in range(matrix.shape[1]):
            val = matrix[yi, xi]
            if val > 0:
                ax.text(xi, yi, f"{val:.0%}", ha="center", va="center", fontsize=6,
                        color="white" if val > 0.5 else "black")

    fig.colorbar(im, ax=ax, label="Participation rate", shrink=0.7)
    ax.set_title("Top-10 Universal 2-gram Participation Across All 18 Runs\n"
                 "(Same phrases everywhere — nearly all agents use them)",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT_DIR / "bigram_participation_heatmap.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Summary
    top1_rates = [r["participation_rate"] for r in top1_rows]
    summary = {
        "per_run_5gram_top1": {
            "mean_participation": round(np.mean(top1_rates), 3),
            "min_participation": round(min(top1_rates), 3),
            "max_participation": round(max(top1_rates), 3),
            "per_scale": {
                scale: round(np.mean([r["participation_rate"] for r in top1_rows if r["scale"] == scale]), 3)
                for scale in SCALES
            },
        },
        "universal_2gram": {
            "mean_participation": round(
                np.mean([r["participation_rate"] for r in bigram_rows]), 3
            ),
            "top5_mean": round(
                np.mean([r["participation_rate"] for r in bigram_rows if r["phrase"] in set(top_bigrams[:5])]), 3
            ),
        },
    }
    with (OUT_DIR / "participation_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nPer-run top-1 5-gram participation: "
          f"mean={summary['per_run_5gram_top1']['mean_participation']:.1%}, "
          f"range=[{summary['per_run_5gram_top1']['min_participation']:.1%}, "
          f"{summary['per_run_5gram_top1']['max_participation']:.1%}]")
    print(f"Universal 2-gram top-5 mean participation: {summary['universal_2gram']['top5_mean']:.1%}")

    print("\nDone!")


if __name__ == "__main__":
    main()
