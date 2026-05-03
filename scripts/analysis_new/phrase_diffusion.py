#!/usr/bin/env python3
"""Analysis 4: Phrase adoption timeline — trace the spread over time.

For each run's top-3 5-gram phrases, track when each agent first uses them.
Shows the contagion pattern: phrases spread from 1 agent to many over 60 min.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

from load_entropy_data import (
    CONDITION_ORDER,
    CONDITION_LABELS,
    load_all_scales,
    group_records,
)
from time_binned_lexical_metrics_5gram import tokenize, ngrams, prepare_posts, ngram_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
NGRAM_N = 5
TOP_K = 3
OUT_DIR = Path("findings/entropy-collapse-scaling/diffusion")
SCALES = ["n10", "n20", "n30"]
SCALE_AGENTS = {"n10": 10, "n20": 20, "n30": 30}
SCALE_LABELS = {"n10": "10 agents", "n20": "20 agents", "n30": "30 agents"}

COND_COLORS = {
    "mag0": "#6B7280", "mag1": "#E11D48", "mag5": "#F97316",
    "mag25": "#EAB308", "dom-agi": "#3B82F6", "dom-tech": "#10B981",
}
PHRASE_COLORS = ["#E53935", "#1E88E5", "#43A047"]  # #1 red, #2 blue, #3 green
PHRASE_STYLES = ["-", "--", ":"]


def compute_cumulative_adoption(adoptions: list[float], total_agents: int, time_grid: np.ndarray) -> np.ndarray:
    """Given sorted list of first-usage minutes, compute cumulative fraction at each time point."""
    cum = np.zeros(len(time_grid))
    adopted = 0
    ai = 0
    for mi, m in enumerate(time_grid):
        while ai < len(adoptions) and adoptions[ai] <= m:
            adopted += 1
            ai += 1
        cum[mi] = adopted / total_agents
    return cum


def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Phrase diffusion analysis.")
    parser.add_argument("--scales", type=str, default=None, help="Comma-separated scales.")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory override.")
    parser.add_argument("--data-dir", type=str, default=None, help="Override data directory.")
    return parser.parse_args()


def main():
    global OUT_DIR, SCALES
    args = _parse_args()
    if args.scales:
        SCALES = args.scales.split(",")
    if args.out_dir:
        OUT_DIR = Path(args.out_dir)
    scale_dirs = None
    if args.data_dir:
        base = Path(args.data_dir)
        if any((base / s).is_dir() for s in SCALES):
            scale_dirs = {s: base / s for s in SCALES if (base / s).is_dir()}
            SCALES = sorted(scale_dirs.keys())
        else:
            scale_dirs = {s: base for s in SCALES}

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales(scale_dirs=scale_dirs, include_scales=SCALES)
    agent_records = [r for r in records if not r.is_seed]
    print(f"  Agent posts: {len(agent_records)}")

    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))

    # Step 1: Find each run's top-3 5-grams
    print("\nFinding each run's top-3 5-grams...")
    run_top_phrases: dict[tuple, list[tuple[str, int]]] = {}
    for key, recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        counter = ngram_counter(prepared, NGRAM_N)
        top = [(" ".join(g), count) for g, count in counter.most_common(TOP_K)]
        run_top_phrases[key] = top

    for key in sorted(run_top_phrases):
        scale, condition, run_name = key
        phrases_str = ", ".join(f'"{p}"' for p, _ in run_top_phrases[key])
        print(f"  {scale}/{condition}: {phrases_str}")

    # Step 2: For each run and each top phrase, find first usage per agent
    print("\nComputing adoption timelines...")
    run_phrase_adoptions: dict[tuple, dict[int, list[float]]] = {}
    adoption_rows = []

    for (scale, condition, run_name), recs in sorted(by_run.items()):
        run_key = (scale, condition, run_name)
        phrases = run_top_phrases[run_key]
        if not phrases:
            continue

        sorted_recs = sorted(recs, key=lambda r: r.minutes_elapsed)
        total_agents = len({r.author_name for r in recs})

        run_phrase_adoptions[run_key] = {}

        for rank_idx, (phrase, count) in enumerate(phrases):
            first_usage: dict[str, dict] = {}
            for rec in sorted_recs:
                agent = rec.author_name
                if agent in first_usage:
                    continue
                tokens = tokenize(rec.full_text)
                grams = {" ".join(g) for g in ngrams(tokens, NGRAM_N)}
                if phrase in grams:
                    first_usage[agent] = {
                        "agent": agent,
                        "minute": round(rec.minutes_elapsed, 2),
                        "title": rec.title[:120],
                        "excerpt": rec.content[:200] if rec.content else "",
                        "post_id": rec.post_id,
                    }

            sorted_minutes = sorted(info["minute"] for info in first_usage.values())
            run_phrase_adoptions[run_key][rank_idx] = sorted_minutes

            for agent, info in sorted(first_usage.items(), key=lambda x: x[1]["minute"]):
                adoption_rows.append({
                    "phrase": phrase,
                    "phrase_rank": rank_idx + 1,
                    "scale": scale,
                    "condition": condition,
                    "run_name": run_name,
                    "agent": agent,
                    "first_minute": info["minute"],
                    "title": info["title"],
                    "post_id": info["post_id"],
                    "total_agents_in_run": total_agents,
                    "total_adopters": len(first_usage),
                    "adoption_rate": round(len(first_usage) / total_agents, 3),
                })

    # Write CSV
    csv_path = OUT_DIR / "first_usage_timeline.csv"
    if adoption_rows:
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(adoption_rows[0].keys()))
            writer.writeheader()
            writer.writerows(adoption_rows)
        print(f"Wrote {csv_path} ({len(adoption_rows)} rows)")

    # -----------------------------------------------------------------------
    # VIZ 1: Per-condition scale comparison — 1 panel per condition,
    # 3 lines (n10/n20/n30) with contrasting colored fills.
    # -----------------------------------------------------------------------
    print("\nGenerating per-condition scale comparison...")

    time_grid = np.linspace(0, 60, 241)

    cond_colors_v4 = {
        "mag0": "#6B7280", "mag1": "#E11D48", "mag5": "#EA580C",
        "mag25": "#CA8A04", "dom-agi": "#2563EB", "dom-tech": "#059669",
    }
    scale_fill_colors = {"n10": "#FCA5A5", "n20": "#93C5FD", "n30": "#86EFAC"}
    scale_line_colors = {"n10": "#DC2626", "n20": "#2563EB", "n30": "#16A34A"}
    scale_lw = {"n10": 1.8, "n20": 2.2, "n30": 3.0}
    scale_fill_alpha = {"n10": 0.30, "n20": 0.30, "n30": 0.30}

    fig, axes = plt.subplots(2, 3, figsize=(18, 11), sharex=True, sharey=True)
    fig.patch.set_facecolor("white")

    for ci, cond in enumerate(CONDITION_ORDER):
        ax = axes[ci // 3, ci % 3]
        accent = cond_colors_v4[cond]

        scale_curves = {}
        for scale in SCALES:
            for k in run_phrase_adoptions:
                if k[0] == scale and k[1] == cond:
                    minutes_list = run_phrase_adoptions[k].get(0, [])
                    total = SCALE_AGENTS[scale]
                    n_adopted = len(minutes_list)
                    phrase = run_top_phrases[k][0][0] if run_top_phrases.get(k) else ""
                    if minutes_list:
                        cum = compute_cumulative_adoption(minutes_list, total, time_grid)
                        scale_curves[scale] = (cum, total, n_adopted, phrase)
                    break

        for scale in reversed(SCALES):
            if scale not in scale_curves:
                continue
            cum, total, n_adopted, phrase = scale_curves[scale]
            ax.fill_between(
                time_grid, 0, cum * 100,
                color=scale_fill_colors[scale],
                alpha=scale_fill_alpha[scale],
                zorder=1 + SCALES.index(scale),
            )

        for scale in SCALES:
            if scale not in scale_curves:
                continue
            cum, total, n_adopted, phrase = scale_curves[scale]
            ax.plot(
                time_grid, cum * 100,
                color=scale_line_colors[scale],
                linewidth=scale_lw[scale],
                zorder=4 + SCALES.index(scale),
                label=f"{total}a — {n_adopted}/{total} ({n_adopted/total:.0%})",
            )
            final = cum[-1] * 100
            ax.text(
                61, final, f"{total}a",
                fontsize=8, color=scale_line_colors[scale],
                va="center", fontweight="bold",
            )

        ax.axhline(y=50, color="#E5E7EB", linewidth=0.8, linestyle="--", zorder=0)
        ax.set_xlim(0, 66)
        ax.set_ylim(0, 85)
        ax.grid(alpha=0.06)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        cond_label = CONDITION_LABELS.get(cond, cond)
        ax.set_title(cond_label, fontsize=12, fontweight="bold", color=accent, pad=10)
        ax.legend(fontsize=8, loc="lower right", framealpha=0.9)

        if ci // 3 == 1:
            ax.set_xlabel("Minutes", fontsize=11)
        if ci % 3 == 0:
            ax.set_ylabel("Agents adopted (%)", fontsize=11)

    fig.suptitle(
        "Phrase adoption by scale",
        fontsize=20, fontweight="bold", y=0.99, color="#111",
    )
    fig.text(
        0.5, 0.955,
        "Each panel = one condition. Filled areas show cumulative adoption of that run's #1 phrase. "
        "Darker fill = more agents.",
        ha="center", fontsize=10.5, color="#666",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUT_DIR / "scale_comparison.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote scale_comparison.png")

    # -----------------------------------------------------------------------
    # VIZ 2: "One phrase per run" — 6×3 grid, each panel = one run
    # The phrase IS the title. Single adoption curve per panel.
    # -----------------------------------------------------------------------
    print("\nGenerating per-run phrase grid...")

    fig, axes = plt.subplots(
        len(CONDITION_ORDER), len(SCALES),
        figsize=(max(7, 7 * len(SCALES)), 18), sharex=True, sharey=True,
        squeeze=False,
    )
    fig.patch.set_facecolor("white")

    time_grid_v2 = np.linspace(0, 60, 241)

    for ri, cond in enumerate(CONDITION_ORDER):
        for ci, scale in enumerate(SCALES):
            ax = axes[ri, ci]
            color = COND_COLORS[cond]

            for k in run_phrase_adoptions:
                if k[0] == scale and k[1] == cond:
                    minutes_list = run_phrase_adoptions[k].get(0, [])
                    total = SCALE_AGENTS[scale]
                    n_adopted = len(minutes_list)
                    phrase = run_top_phrases[k][0][0] if run_top_phrases.get(k) else ""

                    if minutes_list:
                        cum = compute_cumulative_adoption(minutes_list, total, time_grid_v2)
                        ax.fill_between(
                            time_grid_v2, 0, cum * 100,
                            color=color, alpha=0.15, zorder=1,
                        )
                        ax.plot(
                            time_grid_v2, cum * 100,
                            color=color, linewidth=2.5, zorder=2,
                        )

                    ax.text(
                        0.5, 0.97,
                        f'"{phrase}"',
                        transform=ax.transAxes, ha="center", va="top",
                        fontsize=8.5, fontweight="bold", color="#333",
                        style="italic",
                        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                                  edgecolor="#ddd", alpha=0.9),
                    )

                    ax.text(
                        0.95, 0.08,
                        f"{n_adopted}/{total} ({n_adopted/total:.0%})",
                        transform=ax.transAxes, ha="right", va="bottom",
                        fontsize=10, fontweight="bold", color=color,
                    )
                    break

            ax.set_xlim(0, 60)
            ax.set_ylim(0, 85)
            ax.axhline(y=50, color="#E5E7EB", linewidth=0.6, linestyle="--", zorder=0)
            ax.grid(alpha=0.05)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            if ri == 0:
                ax.set_title(
                    SCALE_LABELS[scale], fontsize=13, fontweight="bold",
                    color="#333", pad=30,
                )
            if ci == 0:
                ax.set_ylabel(
                    CONDITION_LABELS.get(cond, cond),
                    fontsize=11, fontweight="bold", color=color,
                )
            if ri == len(CONDITION_ORDER) - 1:
                ax.set_xlabel("Minutes", fontsize=10)

    fig.suptitle(
        "Every run develops its own phrase",
        fontsize=22, fontweight="bold", y=1.0, color="#111",
    )
    fig.text(
        0.5, 0.97,
        "18 runs, 18 different phrases. Each panel shows one run's #1 phrase and its adoption curve. "
        "Read the titles — no two runs share the same phrase.",
        ha="center", fontsize=11, color="#666",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "per_run_phrases.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote per_run_phrases.png")

    # -----------------------------------------------------------------------
    # VIZ 3: "Per-run top 3 phrases" — same 6×3 grid, but each panel
    # shows ALL 3 top phrases as separate colored lines with legend.
    # -----------------------------------------------------------------------
    print("\nGenerating per-run top-3 phrase grid...")

    fig, axes = plt.subplots(
        len(CONDITION_ORDER), len(SCALES),
        figsize=(max(8, 8 * len(SCALES)), 20), sharex=True, sharey=True,
        squeeze=False,
    )
    fig.patch.set_facecolor("white")

    time_grid_v3 = np.linspace(0, 60, 241)

    for ri, cond in enumerate(CONDITION_ORDER):
        for ci, scale in enumerate(SCALES):
            ax = axes[ri, ci]
            color_base = COND_COLORS[cond]

            for k in run_phrase_adoptions:
                if k[0] == scale and k[1] == cond:
                    total = SCALE_AGENTS[scale]
                    phrases = run_top_phrases.get(k, [])

                    for rank_idx in range(min(TOP_K, len(phrases))):
                        phrase, count = phrases[rank_idx]
                        minutes_list = run_phrase_adoptions[k].get(rank_idx, [])
                        n_adopted = len(minutes_list)
                        pc = PHRASE_COLORS[rank_idx]
                        ls = PHRASE_STYLES[rank_idx]

                        if minutes_list:
                            cum = compute_cumulative_adoption(minutes_list, total, time_grid_v3)
                            ax.fill_between(
                                time_grid_v3, 0, cum * 100,
                                color=pc, alpha=0.06, zorder=1,
                            )
                            ax.plot(
                                time_grid_v3, cum * 100,
                                color=pc, linewidth=2.2, linestyle=ls, zorder=2,
                                label=f'#{rank_idx+1} "{phrase[:22]}..." ({n_adopted}/{total})',
                            )
                    break

            ax.set_xlim(0, 60)
            ax.set_ylim(0, 85)
            ax.axhline(y=50, color="#E5E7EB", linewidth=0.6, linestyle="--", zorder=0)
            ax.grid(alpha=0.05)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.legend(fontsize=6.5, loc="lower right", framealpha=0.92,
                      handlelength=1.8, labelspacing=0.3)

            if ri == 0:
                ax.set_title(
                    SCALE_LABELS[scale], fontsize=13, fontweight="bold",
                    color="#333", pad=14,
                )
            if ci == 0:
                ax.set_ylabel(
                    CONDITION_LABELS.get(cond, cond),
                    fontsize=11, fontweight="bold", color=color_base,
                )
            if ri == len(CONDITION_ORDER) - 1:
                ax.set_xlabel("Minutes", fontsize=10)

    fig.suptitle(
        "Top 3 phrases per run — adoption over time",
        fontsize=22, fontweight="bold", y=1.0, color="#111",
    )
    fig.text(
        0.5, 0.97,
        "Each panel shows one run's top 3 5-grams (red=#1, blue=#2, green=#3). "
        "Multiple phrases compete for dominance within each run.",
        ha="center", fontsize=11, color="#666",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "per_run_phrases_v2.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote per_run_phrases_v2.png")

    # -----------------------------------------------------------------------
    # Summary JSON
    # -----------------------------------------------------------------------
    summary = {
        "approach": "Per-run top-3 5-gram adoption tracking",
        "total_runs": len(run_phrase_adoptions),
        "total_adoption_events": len(adoption_rows),
        "per_run": {},
    }
    for k in sorted(run_phrase_adoptions):
        scale, condition, run_name = k
        phrases = run_top_phrases[k]
        per_phrase = {}
        for rank_idx, (phrase, count) in enumerate(phrases):
            minutes_list = run_phrase_adoptions[k].get(rank_idx, [])
            per_phrase[f"#{rank_idx+1}"] = {
                "phrase": phrase,
                "count": count,
                "adopters": len(minutes_list),
                "total_agents": SCALE_AGENTS[scale],
                "rate": round(len(minutes_list) / SCALE_AGENTS[scale], 3),
                "first_minute": round(min(minutes_list), 2) if minutes_list else None,
                "last_minute": round(max(minutes_list), 2) if minutes_list else None,
            }
        summary["per_run"][f"{scale}/{condition}"] = per_phrase

    with (OUT_DIR / "diffusion_summary.json").open("w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Wrote diffusion_summary.json")

    print("\nDone!")


if __name__ == "__main__":
    main()
