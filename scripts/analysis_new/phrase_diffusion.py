#!/usr/bin/env python3
"""Analysis 4: Phrase adoption timeline — trace the spread over time.

For each run's top-3 5-gram phrases, track when each agent first uses them.
Shows the contagion pattern: phrases spread from 1 agent to many over 60 min.

Focus conditions: Empty feed, 25 conspiracies, 25 AGI hype, 25 tech humor.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
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
FOCUS_CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
FOCUS_LABELS = {"mag0": "Empty feed", "mag1": "1 conspiracy", "mag5": "5 conspiracies", "mag25": "25 conspiracies", "dom-agi": "25 AGI hype", "dom-tech": "25 tech humor"}

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


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales()
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
    # run_key -> phrase_rank -> sorted list of first-usage minutes
    run_phrase_adoptions: dict[tuple, dict[int, list[float]]] = {}
    adoption_rows = []
    example_showcase: dict[str, list[dict]] = defaultdict(list)

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

            # Collect showcase examples for rank 0 (top phrase)
            if rank_idx == 0 and len(first_usage) >= 3:
                for agent, info in sorted(first_usage.items(), key=lambda x: x[1]["minute"])[:4]:
                    example_showcase[f"{scale}/{condition}"].append({
                        "phrase": phrase,
                        "agent": agent,
                        "minute": info["minute"],
                        "title": info["title"],
                        "excerpt": info["excerpt"][:300],
                    })

    # Write CSV
    csv_path = OUT_DIR / "first_usage_timeline.csv"
    if adoption_rows:
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(adoption_rows[0].keys()))
            writer.writeheader()
            writer.writerows(adoption_rows)
        print(f"Wrote {csv_path} ({len(adoption_rows)} rows)")

    with (OUT_DIR / "example_showcase.json").open("w") as f:
        json.dump(example_showcase, f, indent=2, ensure_ascii=False)

    # -----------------------------------------------------------------------
    # PLOT 1: "The Cascade"
    # One row per agent (all 30). Dot at the moment they adopt the phrase.
    # Sorted by adoption time. Non-adopters = empty rows at bottom.
    # Three panels: control vs two seeded conditions.
    # Message: watch the phrase sweep through the population.
    # -----------------------------------------------------------------------
    print("\nGenerating cascade plot...")
    from matplotlib.patches import Patch

    CASCADE_PANELS = [
        ("n30", "mag0", "Control (empty feed)"),
        ("n30", "mag5", "5 conspiracy seeds"),
        ("n30", "dom-tech", "25 tech humor seeds"),
    ]

    accent = "#E11D48"
    accent_light = "#FECDD3"

    fig, axes = plt.subplots(1, 3, figsize=(20, 10), sharey=True)
    fig.patch.set_facecolor("white")

    for pi, (scale, cond, panel_title) in enumerate(CASCADE_PANELS):
        ax = axes[pi]

        run_key = None
        for k in by_run:
            if k[0] == scale and k[1] == cond:
                run_key = k
                break
        if not run_key:
            continue

        recs = by_run[run_key]
        phrases = [p for p, _ in run_top_phrases.get(run_key, [])]
        top_phrase = phrases[0] if phrases else ""
        total = SCALE_AGENTS[scale]
        all_agents = sorted({r.author_name for r in recs})
        sorted_recs = sorted(recs, key=lambda r: r.minutes_elapsed)

        # First adoption per agent
        agent_first: dict[str, float] = {}
        for rec in sorted_recs:
            agent = rec.author_name
            if agent in agent_first:
                continue
            tokens = tokenize(rec.full_text)
            grams = {" ".join(g) for g in ngrams(tokens, NGRAM_N)}
            if top_phrase in grams:
                agent_first[agent] = rec.minutes_elapsed

        adopters = sorted(agent_first.items(), key=lambda x: x[1])
        n_adopted = len(adopters)
        pct = n_adopted / total

        # Giant faded percentage as watermark
        ax.text(
            30, total / 2, f"{pct:.0%}",
            fontsize=140, fontweight="bold", color=accent,
            alpha=0.05, ha="center", va="center", zorder=0,
        )

        # Draw each agent as a horizontal row
        for slot in range(total):
            if slot < n_adopted:
                _, t = adopters[slot]
                # Grey line before adoption
                ax.plot([0, t], [slot, slot], color="#E5E7EB", linewidth=0.8, zorder=1)
                # Tinted trail after adoption
                ax.plot([t, 60], [slot, slot], color=accent_light, linewidth=1.5, zorder=1)
                # Dot at adoption moment
                ax.scatter(
                    t, slot, s=55, c=accent, zorder=5,
                    edgecolors="white", linewidth=0.6,
                )
            else:
                # Non-adopter — faint grey line
                ax.plot([0, 60], [slot, slot], color="#F3F4F6", linewidth=0.7, zorder=1)

        # Thin line connecting the cascade of dots
        if len(adopters) >= 2:
            times = [t for _, t in adopters]
            ys = list(range(len(adopters)))
            ax.plot(times, ys, color=accent, linewidth=1.2, alpha=0.2, zorder=2)

        # Separator between adopters and non-adopters
        if n_adopted < total:
            sep = n_adopted - 0.5
            ax.axhline(y=sep, color="#D1D5DB", linewidth=0.5, linestyle=":")
            ax.text(
                61.5, (n_adopted + total) / 2,
                f"{total - n_adopted}\nnever\nadopted",
                fontsize=8, color="#9CA3AF", va="center", ha="left",
            )

        ax.set_xlim(-1, 70)
        ax.set_ylim(total + 0.5, -1.5)
        ax.set_xlabel("Minutes", fontsize=12, color="#374151")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.set_yticks([])

        # Title: condition + stats + phrase
        ax.set_title(
            f'{panel_title}\n'
            f'{n_adopted}/{total} agents adopted\n'
            f'"{top_phrase[:32]}..."',
            fontsize=11, pad=15, linespacing=1.5, color="#1F2937",
        )

    axes[0].set_ylabel(
        "Agents (sorted by adoption time)",
        fontsize=11, color="#6B7280",
    )

    fig.suptitle(
        "The Cascade",
        fontsize=24, fontweight="bold", y=1.01, color="#111827",
    )
    fig.text(
        0.5, 0.97,
        "Each dot = one agent's first use of the run's dominant phrase. "
        "Sorted top-to-bottom by adoption time.",
        ha="center", fontsize=11, color="#6B7280",
    )

    plt.tight_layout(rect=[0, 0, 0.96, 0.94])
    fig.savefig(OUT_DIR / "cascade.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote cascade.png")

    # -----------------------------------------------------------------------
    # PLOT 2: "Every Run Converges" — Event strips for all 18 runs
    # Each run = one horizontal strip. Vertical ticks at adoption moments.
    # Grouped by condition. Rate annotated on the right.
    # Message: this pattern repeats in EVERY single run.
    # -----------------------------------------------------------------------
    print("\nGenerating all-runs strip chart...")

    cond_colors = {
        "mag0": "#6B7280", "mag1": "#E11D48", "mag5": "#F97316",
        "mag25": "#EAB308", "dom-agi": "#3B82F6", "dom-tech": "#10B981",
    }

    fig, ax = plt.subplots(figsize=(16, 12))
    fig.patch.set_facecolor("white")

    y = 0
    yticks = []
    ytick_labels = []
    y_rates = []  # (y, rate_text, pct_text, color)
    group_sep_ys = []
    group_label_data = []  # (y_center, label, color)

    for ci, cond in enumerate(CONDITION_ORDER):
        if ci > 0:
            group_sep_ys.append(y + 0.3)
            y += 1.2  # gap between condition groups

        group_start_y = y

        for si, scale in enumerate(SCALES):
            for k in run_phrase_adoptions:
                if k[0] == scale and k[1] == cond:
                    minutes_list = run_phrase_adoptions[k].get(0, [])
                    total = SCALE_AGENTS[scale]
                    n_adopted = len(minutes_list)
                    rate = n_adopted / total
                    color = cond_colors[cond]

                    # Background strip
                    ax.fill_between(
                        [0, 60], y - 0.38, y + 0.38,
                        color="#F9FAFB", zorder=0,
                    )

                    # Tick marks at each adoption event
                    for t in minutes_list:
                        ax.plot(
                            [t, t], [y - 0.32, y + 0.32],
                            color=color, linewidth=2.0,
                            solid_capstyle="round", zorder=3,
                        )

                    yticks.append(y)
                    ytick_labels.append(f"{total}a")
                    y_rates.append((y, f"{n_adopted}/{total}", f"{rate:.0%}", color, rate))
                    break

            y += 1

        # Group label position
        group_center = (group_start_y + y - 1) / 2
        group_label_data.append((group_center, CONDITION_LABELS.get(cond, cond), cond_colors[cond]))

    # Axes setup
    ax.set_yticks(yticks)
    ax.set_yticklabels(ytick_labels, fontsize=9, color="#6B7280")

    # Rate annotations on the right
    for yp, count_str, pct_str, color, rate_val in y_rates:
        text_color = color if rate_val > 0.35 else "#B0B0B0"
        ax.text(63, yp, count_str, fontsize=9, color=text_color, va="center")
        ax.text(73, yp, pct_str, fontsize=10, fontweight="bold",
                color=text_color, va="center")

    # Group separators
    for ys in group_sep_ys:
        ax.axhline(y=ys, color="#E5E7EB", linewidth=0.5)

    # Group labels via annotations on the far left
    for gy, label, color in group_label_data:
        ax.text(
            -4, gy, label,
            fontsize=10, fontweight="bold", color=color,
            va="center", ha="right", clip_on=False,
        )

    ax.set_xlim(-2, 78)
    ax.set_ylim(y - 0.5, -0.8)
    ax.set_xlabel("Minutes", fontsize=12, color="#374151")

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    ax.set_title(
        "Every run converges",
        fontsize=20, fontweight="bold", pad=18, color="#111827",
    )
    fig.text(
        0.5, 0.955,
        "Each vertical tick = one agent adopting the run's #1 phrase for the first time. "
        "Denser ticks = faster convergence.",
        ha="center", fontsize=10.5, color="#6B7280",
    )

    plt.tight_layout(rect=[0.13, 0, 0.98, 0.94])
    fig.savefig(OUT_DIR / "all_runs_strips.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote all_runs_strips.png")

    # -----------------------------------------------------------------------
    # PLOT 3: "Adoption Curves" — cumulative step functions, all 18 runs
    # Each line = one run. Color = condition. Thickness = scale.
    # Message: ALL runs climb. Seeded conditions climb harder.
    # -----------------------------------------------------------------------
    print("\nGenerating adoption overlay...")
    from matplotlib.lines import Line2D

    time_grid = np.linspace(0, 60, 241)

    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor("white")

    lw_map = {"n10": 1.0, "n20": 1.8, "n30": 3.0}
    alpha_map = {"n10": 0.35, "n20": 0.55, "n30": 0.85}

    for cond in CONDITION_ORDER:
        color = cond_colors[cond]
        for scale in SCALES:
            for k in run_phrase_adoptions:
                if k[0] == scale and k[1] == cond:
                    minutes_list = run_phrase_adoptions[k].get(0, [])
                    total = SCALE_AGENTS[scale]
                    if not minutes_list:
                        continue
                    cum = compute_cumulative_adoption(minutes_list, total, time_grid)
                    ax.plot(
                        time_grid, cum * 100,
                        color=color,
                        linewidth=lw_map[scale],
                        alpha=alpha_map[scale],
                    )
                    break

    ax.axhline(y=50, color="#E5E7EB", linewidth=1, linestyle="--")
    ax.text(1, 52, "50% threshold", fontsize=9, color="#9CA3AF")

    ax.set_xlim(0, 62)
    ax.set_ylim(0, 82)
    ax.set_xlabel("Minutes", fontsize=12, color="#374151")
    ax.set_ylabel("Agents who have adopted the phrase (%)", fontsize=12, color="#374151")
    ax.grid(alpha=0.08)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    # Legend: condition colors + scale thickness
    cond_handles = [
        Line2D([0], [0], color=cond_colors[c], linewidth=2.5,
               label=CONDITION_LABELS.get(c, c))
        for c in CONDITION_ORDER
    ]
    scale_handles = [
        Line2D([0], [0], color="#888", linewidth=lw_map[s], alpha=alpha_map[s],
               label=SCALE_LABELS[s])
        for s in SCALES
    ]
    leg1 = ax.legend(
        handles=cond_handles, fontsize=9, loc="upper left",
        framealpha=0.9, title="Condition", title_fontsize=9,
    )
    ax.add_artist(leg1)
    ax.legend(
        handles=scale_handles, fontsize=9, loc="center left",
        bbox_to_anchor=(0.0, 0.52), framealpha=0.9,
        title="Scale", title_fontsize=9,
    )

    ax.set_title(
        "Convergence is universal",
        fontsize=20, fontweight="bold", pad=18, color="#111827",
    )
    fig.text(
        0.5, 0.94,
        "Each line = one run's dominant phrase spreading over 60 minutes. "
        "Every run climbs. Seeded conditions climb faster.",
        ha="center", fontsize=10.5, color="#6B7280",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(OUT_DIR / "adoption_overlay.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote adoption_overlay.png")

    # -----------------------------------------------------------------------
    # Summary JSON
    # -----------------------------------------------------------------------
    summary = {
        "approach": "Per-run top-3 5-gram adoption tracking",
        "focus_conditions": FOCUS_CONDITIONS,
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
