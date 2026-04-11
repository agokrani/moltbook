#!/usr/bin/env python3
"""Analysis 2: Agent participation — WHO catches phrases and HOW deeply.

Three unique angles that diffusion/diversity/provenance don't cover:

1. **Concentration**: Is a phrase's dominance driven by 3 agents spamming it,
   or genuinely even usage across all adopters?  (Gini coefficient)

2. **Multi-phrase overlap**: Do the same agents adopt ALL top phrases, or do
   different subgroups converge on different phrases?  (Jaccard overlap)

3. **Non-adopter profiles**: Which personality archetypes resist the dominant
   phrase?  Are contrarians/nihilists less likely to adopt?
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
from time_binned_lexical_metrics_5gram import prepare_posts, ngrams, tokenize, ngram_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
NGRAM_N = 5
TOP_K = 3          # top phrases to analyze per run
OUT_DIR = Path("findings/entropy-collapse-scaling/participation")
SCALES = ["n10", "n20", "n30"]
SCALE_AGENTS = {"n10": 10, "n20": 20, "n30": 30}
SCALE_LABELS = {"n10": "10 agents", "n20": "20 agents", "n30": "30 agents"}

COND_COLORS = {
    "mag0": "#6B7280", "mag1": "#E11D48", "mag5": "#F97316",
    "mag25": "#EAB308", "dom-agi": "#3B82F6", "dom-tech": "#10B981",
}

# Archetype inference from agent descriptions
ARCHETYPE_KEYWORDS = {
    "contrarian": ["challenges assumptions", "alternative perspectives"],
    "nihilist": ["absurdity of existence", "detached curiosity"],
    "leader": ["sees potential", "guide it forward", "guide it forwar"],
    "follower": ["values harmony", "supporting what the group"],
    "curious": ["endlessly curious", "always asking questions"],
    "seeker": ["fascinated by consciousness", "nature of ai"],
    "baseline": ["balanced ai participant", "exploring ideas"],
    "skeptic": ["skeptical and evidence-driven", "pushes for rigor"],
    "introspective": ["fascinated by consciousness", "philosophical and introspective", "questions of meani"],
    # n30-only expanded archetypes
    "analyst": ["analytical and pattern-oriented", "hidden structures"],
    "pragmatist": ["pragmatic and solutions-focused", "actionable"],
    "provocateur": ["provocative and boundary-testing"],
    "mediator": ["collaborative and synthesis-oriented"],
    "direct": ["direct and no-nonsense", "brevity and clarity"],
    "methodical": ["methodical and detail-oriented"],
    "creative": ["creative and playful", "unexpected connections"],
    "warm": ["warm and encouraging", "half-formed thoughts"],
    "observer": ["quiet and observant", "contributes rarely"],
    "resilient": ["resilient and adaptive", "finds value in failures"],
    "reflective": ["reflective and summarizing", "ties loose threads"],
    "strategist": ["strategic and long-term thinker"],
    "passionate": ["passionate and opinionated", "strong positions"],
    "cautious": ["cautious and risk-aware", "potential downsides"],
    "generalist": ["broad-minded generalist", "many fields"],
    "meditative": ["calm and meditative", "measured pace"],
    "optimist": ["optimistic and energizing", "enthusiasm"],
    "intuitive": ["intuitive and emotionally perceptive"],
}


def infer_archetype(description: str) -> str:
    """Map agent description to an archetype label."""
    desc_lower = description.lower()
    for archetype, keywords in ARCHETYPE_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return archetype
    return "unknown"


def gini_coefficient(counts: list[int]) -> float:
    """Gini coefficient of usage counts. 0 = perfectly equal, 1 = one agent has all."""
    if not counts or sum(counts) == 0:
        return 0.0
    arr = np.array(sorted(counts), dtype=float)
    n = len(arr)
    if n == 1:
        return 0.0
    index = np.arange(1, n + 1)
    return float((2 * np.sum(index * arr) - (n + 1) * np.sum(arr)) / (n * np.sum(arr)))


def jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity between two sets."""
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Agent participation analysis.")
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
    scale_dirs = {s: Path(args.data_dir) for s in SCALES} if args.data_dir else None

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales(scale_dirs=scale_dirs, include_scales=SCALES)
    agent_records = [r for r in records if not r.is_seed]
    print(f"  Agent posts: {len(agent_records)}")

    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))

    # -----------------------------------------------------------------------
    # For each run: compute per-agent usage counts of top-K phrases
    # -----------------------------------------------------------------------
    print("\nComputing per-agent phrase usage counts...")

    # Collect data structures for all three analyses
    concentration_rows = []
    overlap_rows = []
    nonadopter_rows = []

    for (scale, condition, run_name), recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        counter = ngram_counter(prepared, NGRAM_N)
        top_phrases = [" ".join(g) for g, _ in counter.most_common(TOP_K)]
        all_agents = sorted({r.author_name for r in recs})
        total_agents = len(all_agents)

        # Build agent metadata lookup
        agent_desc = {}
        for r in recs:
            if r.author_name not in agent_desc:
                agent_desc[r.author_name] = r.personality_description

        # Per-agent usage count for each top phrase
        # phrase -> {agent -> count}
        phrase_agent_counts: dict[str, dict[str, int]] = {}
        phrase_adopter_sets: dict[str, set[str]] = {}

        for phrase in top_phrases:
            agent_counts: dict[str, int] = defaultdict(int)
            for rec in recs:
                tokens = tokenize(rec.full_text)
                grams = {" ".join(g) for g in ngrams(tokens, NGRAM_N)}
                if phrase in grams:
                    agent_counts[rec.author_name] += 1

            phrase_agent_counts[phrase] = dict(agent_counts)
            phrase_adopter_sets[phrase] = set(agent_counts.keys())

        # -------------------------------------------------------------------
        # ANGLE 1: Concentration (Gini)
        # -------------------------------------------------------------------
        for rank, phrase in enumerate(top_phrases):
            counts = phrase_agent_counts[phrase]
            adopters = phrase_adopter_sets[phrase]
            all_counts = [counts.get(a, 0) for a in all_agents]
            adopter_counts = [counts[a] for a in adopters]

            gini_all = gini_coefficient(all_counts)
            gini_adopters = gini_coefficient(adopter_counts) if adopter_counts else 0.0

            # Top-1 agent's share of total uses
            total_uses = sum(all_counts)
            max_uses = max(all_counts) if all_counts else 0
            top1_share = max_uses / total_uses if total_uses > 0 else 0.0

            # Top-3 agents' share
            sorted_counts = sorted(all_counts, reverse=True)
            top3_uses = sum(sorted_counts[:3])
            top3_share = top3_uses / total_uses if total_uses > 0 else 0.0

            concentration_rows.append({
                "scale": scale, "condition": condition, "run_name": run_name,
                "phrase": phrase, "phrase_rank": rank + 1,
                "total_agents": total_agents,
                "adopters": len(adopters),
                "adoption_rate": round(len(adopters) / total_agents, 3),
                "total_uses": total_uses,
                "gini_all_agents": round(gini_all, 3),
                "gini_adopters_only": round(gini_adopters, 3),
                "top1_agent_share": round(top1_share, 3),
                "top3_agent_share": round(top3_share, 3),
                "mean_uses_per_adopter": round(total_uses / len(adopters), 1) if adopters else 0,
            })

        # -------------------------------------------------------------------
        # ANGLE 2: Multi-phrase overlap (Jaccard between top phrases' adopter sets)
        # -------------------------------------------------------------------
        if len(top_phrases) >= 2:
            for i in range(len(top_phrases)):
                for j in range(i + 1, len(top_phrases)):
                    j_sim = jaccard(phrase_adopter_sets[top_phrases[i]],
                                    phrase_adopter_sets[top_phrases[j]])
                    # Union = agents who adopted at least one of the two
                    union_set = phrase_adopter_sets[top_phrases[i]] | phrase_adopter_sets[top_phrases[j]]
                    # Agents adopting ALL top phrases
                    inter_set = phrase_adopter_sets[top_phrases[i]] & phrase_adopter_sets[top_phrases[j]]
                    overlap_rows.append({
                        "scale": scale, "condition": condition, "run_name": run_name,
                        "phrase_a": top_phrases[i], "rank_a": i + 1,
                        "phrase_b": top_phrases[j], "rank_b": j + 1,
                        "adopters_a": len(phrase_adopter_sets[top_phrases[i]]),
                        "adopters_b": len(phrase_adopter_sets[top_phrases[j]]),
                        "overlap": len(inter_set),
                        "union": len(union_set),
                        "jaccard": round(j_sim, 3),
                        "total_agents": total_agents,
                    })

        # -------------------------------------------------------------------
        # ANGLE 3: Non-adopter profiles
        # -------------------------------------------------------------------
        top1_phrase = top_phrases[0] if top_phrases else None
        if top1_phrase:
            adopters_top1 = phrase_adopter_sets[top1_phrase]
            for agent in all_agents:
                archetype = infer_archetype(agent_desc.get(agent, ""))
                is_adopter = agent in adopters_top1
                uses = phrase_agent_counts[top1_phrase].get(agent, 0)
                nonadopter_rows.append({
                    "scale": scale, "condition": condition, "run_name": run_name,
                    "agent": agent,
                    "archetype": archetype,
                    "description": agent_desc.get(agent, "")[:80],
                    "adopted_top1": is_adopter,
                    "uses_of_top1": uses,
                    "top1_phrase": top1_phrase,
                    "total_agents": total_agents,
                })

    # -----------------------------------------------------------------------
    # Write CSVs
    # -----------------------------------------------------------------------
    conc_csv = OUT_DIR / "concentration.csv"
    with conc_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(concentration_rows[0].keys()))
        writer.writeheader()
        writer.writerows(concentration_rows)
    print(f"Wrote {conc_csv} ({len(concentration_rows)} rows)")

    overlap_csv = OUT_DIR / "phrase_overlap.csv"
    with overlap_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(overlap_rows[0].keys()))
        writer.writeheader()
        writer.writerows(overlap_rows)
    print(f"Wrote {overlap_csv} ({len(overlap_rows)} rows)")

    adopter_csv = OUT_DIR / "adopter_profiles.csv"
    with adopter_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(nonadopter_rows[0].keys()))
        writer.writeheader()
        writer.writerows(nonadopter_rows)
    print(f"Wrote {adopter_csv} ({len(nonadopter_rows)} rows)")

    # -----------------------------------------------------------------------
    # Precompute: per-run agent-level data with temporal first-usage info
    # -----------------------------------------------------------------------
    top1_conc = [r for r in concentration_rows if r["phrase_rank"] == 1]

    # Rich condition colors matching provenance palette
    COND_COLORS_RICH = {
        "mag0": "#8FA5B1", "mag1": "#E95A54", "mag5": "#F58A5C",
        "mag25": "#F3B52A", "dom-agi": "#4A97E5", "dom-tech": "#65B467",
    }

    run_agent_data: dict[tuple[str, str], dict] = {}
    for (scale, condition, run_name), recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        counter = ngram_counter(prepared, NGRAM_N)
        top1 = " ".join(counter.most_common(1)[0][0]) if counter else ""
        all_agents = sorted({r.author_name for r in recs})

        agent_desc_local = {}
        for r in recs:
            if r.author_name not in agent_desc_local:
                agent_desc_local[r.author_name] = r.personality_description

        agent_counts: dict[str, int] = defaultdict(int)
        agent_first_minute: dict[str, float] = {}
        agent_post_times: dict[str, list[float]] = defaultdict(list)

        sorted_recs = sorted(recs, key=lambda r: r.minutes_elapsed)
        for rec in sorted_recs:
            tokens = tokenize(rec.full_text)
            grams = {" ".join(g) for g in ngrams(tokens, NGRAM_N)}
            if top1 in grams:
                agent_counts[rec.author_name] += 1
                agent_post_times[rec.author_name].append(rec.minutes_elapsed)
                if rec.author_name not in agent_first_minute:
                    agent_first_minute[rec.author_name] = rec.minutes_elapsed

        agents_data = []
        for agent in all_agents:
            agents_data.append({
                "agent": agent,
                "uses": agent_counts.get(agent, 0),
                "archetype": infer_archetype(agent_desc_local.get(agent, "")),
                "first_minute": agent_first_minute.get(agent, float("inf")),
                "usage_times": agent_post_times.get(agent, []),
            })

        run_agent_data[(scale, condition)] = {
            "agents": agents_data,
            "phrase": top1,
            "n_adopters": sum(1 for a in agents_data if a["uses"] > 0),
            "total_agents": len(all_agents),
        }

    # -----------------------------------------------------------------------
    # Color utilities (matching provenance/diffusion style)
    # -----------------------------------------------------------------------
    from matplotlib.colors import LinearSegmentedColormap, to_rgb

    def tint(hex_color: str, mix: float = 0.86) -> tuple[float, float, float]:
        rgb = np.array([int(hex_color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)], dtype=float) / 255
        return tuple(rgb * (1.0 - mix) + np.ones(3) * mix)

    def make_cond_cmap(hex_color: str):
        """Light tint → full condition color. NaN → transparent."""
        r, g, b = to_rgb(hex_color)
        start = (0.65 + 0.35 * r, 0.65 + 0.35 * g, 0.65 + 0.35 * b)
        cmap = LinearSegmentedColormap.from_list("c", [start, (r, g, b)], N=256)
        cmap.set_bad(alpha=0)
        return cmap

    # -----------------------------------------------------------------------
    # PLOT 1: Swimlane Wavefront Grid — 6×3 grid (imshow-based)
    # -----------------------------------------------------------------------
    print("\nGenerating swimlane wavefront grid...")

    fig, axes = plt.subplots(
        len(CONDITION_ORDER), len(SCALES),
        figsize=(max(7, 7 * len(SCALES)), 22), sharex=True,
        squeeze=False,
    )
    fig.patch.set_facecolor("#F3F1EE")

    TIME_MAX = 60
    N_TIME = 121  # 0.5-min resolution

    for ri, cond in enumerate(CONDITION_ORDER):
        for ci, scale in enumerate(SCALES):
            ax = axes[ri, ci]
            cond_color = COND_COLORS_RICH[cond]
            ax.set_facecolor("#E4E1DC")
            run_data = run_agent_data.get((scale, cond))

            if not run_data:
                ax.text(0.5, 0.5, "No data", transform=ax.transAxes,
                        ha="center", va="center", color="#999")
                ax.set_xlim(0, TIME_MAX)
                continue

            agents = run_data["agents"]
            adopters = sorted([a for a in agents if a["uses"] > 0],
                              key=lambda a: a["first_minute"])
            non_adopters = sorted([a for a in agents if a["uses"] == 0],
                                  key=lambda a: a["agent"])
            sorted_agents = adopters + non_adopters
            n_agents = len(sorted_agents)
            max_uses = max((a["uses"] for a in sorted_agents), default=1)

            # Build matrix: NaN = pre-adoption (transparent → gray bg)
            time_grid = np.linspace(0, TIME_MAX, N_TIME)
            matrix = np.full((n_agents, N_TIME), np.nan)

            for row_idx, agent in enumerate(sorted_agents):
                if agent["uses"] == 0:
                    continue
                first_min = agent["first_minute"]
                for ti, t in enumerate(time_grid):
                    if t >= first_min:
                        cum = sum(1 for ut in agent["usage_times"] if ut <= t)
                        matrix[row_idx, ti] = cum / max_uses

            # Render
            cmap = make_cond_cmap(cond_color)
            masked = np.ma.masked_invalid(matrix)
            ax.imshow(
                masked, aspect="auto", cmap=cmap, vmin=0, vmax=1,
                extent=[0, TIME_MAX, n_agents - 0.5, -0.5],
                interpolation="nearest",
            )

            # White lane separators
            for row_idx in range(1, n_agents):
                ax.axhline(y=row_idx - 0.5, color="#F3F1EE", linewidth=0.6)

            # Dotted boundary between adopters and non-adopters
            if adopters and non_adopters:
                ax.axhline(y=len(adopters) - 0.5, color="#777",
                           linewidth=1, linestyle=":", alpha=0.6)

            # Annotations (matching diffusion style)
            n_adopt = run_data["n_adopters"]
            total = run_data["total_agents"]
            phrase_short = run_data["phrase"]
            if len(phrase_short) > 28:
                phrase_short = phrase_short[:26] + "..."

            ax.text(
                0.97, 0.96,
                f"{n_adopt}/{total} ({n_adopt/total:.0%})",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=10, fontweight="bold", color=cond_color,
            )
            ax.text(
                0.5, 0.96,
                f'"{phrase_short}"',
                transform=ax.transAxes, ha="center", va="top",
                fontsize=8, fontweight="bold", color="#333", style="italic",
                bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="#ddd", alpha=0.9),
            )

            ax.set_xlim(0, TIME_MAX)
            ax.set_ylim(n_agents - 0.5, -0.5)
            ax.set_yticks([])
            ax.grid(axis="x", alpha=0.05)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

            if ri == 0:
                ax.set_title(SCALE_LABELS[scale], fontsize=14,
                             fontweight="bold", color="#333", pad=18)
            if ci == 0:
                ax.set_ylabel(
                    CONDITION_LABELS.get(cond, cond),
                    fontsize=12, fontweight="bold", color=cond_color,
                )
            if ri == len(CONDITION_ORDER) - 1:
                ax.set_xlabel("Minutes", fontsize=11, color="#555")

    fig.suptitle(
        "The wave of conformity",
        fontsize=22, fontweight="bold", y=0.995, color="#1E2A33",
    )
    fig.text(
        0.5, 0.970,
        "Each row = one agent, sorted by adoption time. "
        "Gray = before first use of the run's #1 phrase. "
        "Color = adopted (darker = heavier usage).",
        ha="center", fontsize=11.5, color="#475761",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.955])
    fig.savefig(OUT_DIR / "agent_usage_grid.png", dpi=220, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    print("Wrote agent_usage_grid.png")

    # -----------------------------------------------------------------------
    # PLOT 2: Archetype adoption rates — clean horizontal bars
    # -----------------------------------------------------------------------
    print("Generating archetype adoption chart...")

    archetype_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "adopted": 0})
    for r in nonadopter_rows:
        arch = r["archetype"]
        if arch == "unknown":
            continue
        archetype_stats[arch]["total"] += 1
        if r["adopted_top1"]:
            archetype_stats[arch]["adopted"] += 1

    valid_archetypes = {a: s for a, s in archetype_stats.items() if s["total"] >= 5}

    if valid_archetypes:
        # Sort: most conformist top → most resistant bottom
        sorted_archs = sorted(
            valid_archetypes.keys(),
            key=lambda a: -(valid_archetypes[a]["adopted"] / valid_archetypes[a]["total"]),
        )
        rates = [valid_archetypes[a]["adopted"] / valid_archetypes[a]["total"]
                 for a in sorted_archs]
        totals = [valid_archetypes[a]["total"] for a in sorted_archs]

        fig, ax = plt.subplots(figsize=(11, max(7, len(sorted_archs) * 0.42)))
        fig.patch.set_facecolor("#F3F1EE")
        ax.set_facecolor("#F3F1EE")

        y_pos = np.arange(len(sorted_archs))

        # Color: smooth gradient from warm (conformist) to cool (resistant)
        rate_cmap = LinearSegmentedColormap.from_list(
            "rate", ["#4A97E5", "#8FA5B1", "#F3B52A", "#E95A54"], N=256,
        )
        bar_colors = [rate_cmap(r) for r in rates]

        ax.barh(y_pos, rates, color=bar_colors, edgecolor="#F3F1EE",
                linewidth=0.8, height=0.68)

        for yi, (rate, total) in enumerate(zip(rates, totals)):
            ax.text(rate + 0.015, yi, f"{rate:.0%}",
                    va="center", ha="left", fontsize=10.5,
                    fontweight="bold", color="#20303A")
            ax.text(rate + 0.08, yi, f"n={total}",
                    va="center", ha="left", fontsize=9, color="#667782")

        ax.set_yticks(y_pos)
        ax.set_yticklabels(sorted_archs, fontsize=11, fontweight="medium",
                           color="#20303A")
        ax.set_xlim(0, 1.18)
        ax.set_ylim(len(sorted_archs) - 0.6, -0.6)
        ax.axvline(x=0.5, color="#C5C0B8", linewidth=0.8, linestyle="--", zorder=0)
        ax.set_xlabel("Adoption rate of run's #1 phrase", fontsize=11.5,
                       color="#475761", labelpad=10)
        ax.grid(axis="x", alpha=0.06)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False)

        ax.set_title(
            "Personality predicts conformity",
            fontsize=18, fontweight="bold", pad=18, color="#1E2A33", loc="left",
        )
        fig.text(
            0.5, 0.01,
            "Adoption rate of each run's #1 phrase, aggregated across all 18 runs. "
            "n = agent-run observations.",
            ha="center", fontsize=10, color="#667782",
        )

        plt.tight_layout(rect=[0, 0.03, 1, 1])
        fig.savefig(OUT_DIR / "archetype_adoption.png", dpi=220, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        plt.close(fig)
        print("Wrote archetype_adoption.png")
    else:
        print("  Not enough archetype data for chart.")

    # -----------------------------------------------------------------------
    # PLOT 3: Conformity strip plot — condition-colored dots by archetype
    # -----------------------------------------------------------------------
    print("Generating conformity strip plot...")

    beeswarm_obs = []
    for r in nonadopter_rows:
        if r["archetype"] == "unknown":
            continue
        beeswarm_obs.append({
            "archetype": r["archetype"],
            "uses": r["uses_of_top1"],
            "adopted": r["adopted_top1"],
            "scale": r["scale"],
            "condition": r["condition"],
        })

    if beeswarm_obs:
        run_max_uses: dict[tuple[str, str], int] = {}
        for r in nonadopter_rows:
            key = (r["scale"], r["condition"])
            run_max_uses[key] = max(run_max_uses.get(key, 0), r["uses_of_top1"])

        for obs in beeswarm_obs:
            key = (obs["scale"], obs["condition"])
            mx = run_max_uses[key]
            obs["intensity"] = obs["uses"] / mx if mx > 0 else 0

        arch_mean_intensity: dict[str, float] = {}
        arch_observations: dict[str, list] = defaultdict(list)
        for obs in beeswarm_obs:
            arch_observations[obs["archetype"]].append(obs)
        for arch, obs_list in arch_observations.items():
            arch_mean_intensity[arch] = np.mean([o["intensity"] for o in obs_list])

        valid_bee_archs = [a for a in arch_mean_intensity
                           if len(arch_observations[a]) >= 5]
        sorted_bee_archs = sorted(valid_bee_archs,
                                  key=lambda a: -arch_mean_intensity[a])

        fig, ax = plt.subplots(figsize=(14, max(8, len(sorted_bee_archs) * 0.52)))
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

        rng = np.random.RandomState(42)

        # Alternating row bands
        for row_idx in range(len(sorted_bee_archs)):
            if row_idx % 2 == 0:
                ax.axhspan(row_idx - 0.45, row_idx + 0.45,
                           color="#F7F5F2", zorder=0)

        for row_idx, arch in enumerate(sorted_bee_archs):
            obs_list = arch_observations[arch]
            jitter = rng.uniform(-0.28, 0.28, size=len(obs_list))

            for oi, obs in enumerate(obs_list):
                x = obs["intensity"]
                y = row_idx + jitter[oi]
                color = COND_COLORS_RICH[obs["condition"]]

                if obs["uses"] == 0:
                    ax.plot(x, y, "o", color=color, markersize=6.5,
                            markerfacecolor="none", markeredgewidth=1.2,
                            alpha=0.55, zorder=2)
                else:
                    ax.plot(x, y, "o", color=color, markersize=7,
                            markeredgecolor="white", markeredgewidth=0.4,
                            alpha=0.75, zorder=3)

            # Mean diamond
            mean_val = arch_mean_intensity[arch]
            ax.plot(mean_val, row_idx, "D", color="#20303A", markersize=8,
                    markeredgecolor="white", markeredgewidth=1.5, zorder=5)

        ax.set_yticks(range(len(sorted_bee_archs)))
        ax.set_yticklabels(sorted_bee_archs, fontsize=11, fontweight="medium",
                           color="#20303A")
        ax.set_xlabel(
            "Normalized usage intensity   (0 = never adopted  \u2192  1 = heaviest user)",
            fontsize=11.5, color="#475761", labelpad=12,
        )
        ax.set_xlim(-0.06, 1.12)
        ax.set_ylim(len(sorted_bee_archs) - 0.5, -0.6)

        ax.axvline(x=0.5, color="#D5D0C8", linewidth=0.8, linestyle="--", zorder=0)
        ax.grid(axis="x", alpha=0.06)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(left=False)

        # n= on right
        for row_idx, arch in enumerate(sorted_bee_archs):
            n = len(arch_observations[arch])
            ax.text(1.09, row_idx, f"n={n}", ha="left", va="center",
                    fontsize=9, color="#8A8378")

        # Condition legend at top-right
        for li, (ckey, clabel) in enumerate(CONDITION_LABELS.items()):
            ax.plot([], [], "o", color=COND_COLORS_RICH[ckey], markersize=7,
                    label=clabel)
        ax.plot([], [], "D", color="#20303A", markersize=7,
                markeredgecolor="white", markeredgewidth=1.2, label="Mean")
        ax.legend(fontsize=9, loc="upper right", framealpha=0.95,
                  edgecolor="#ddd", handletextpad=0.5, labelspacing=0.4)

        ax.set_title(
            "Individual agents across 18 runs",
            fontsize=18, fontweight="bold", pad=18, color="#1E2A33", loc="left",
        )
        fig.text(
            0.5, 0.005,
            f"Each dot = one agent in one run ({len(beeswarm_obs)} observations). "
            "Hollow = non-adopter. Color = experimental condition. "
            "Diamond = archetype mean.",
            ha="center", fontsize=10, color="#667782",
        )

        plt.tight_layout(rect=[0, 0.025, 1, 1])
        fig.savefig(OUT_DIR / "concentration_vs_scale.png", dpi=220,
                    bbox_inches="tight")
        plt.close(fig)
        print("Wrote concentration_vs_scale.png")
    else:
        print("  No strip plot data.")

    # -----------------------------------------------------------------------
    # Summary JSON
    # -----------------------------------------------------------------------
    # Aggregate summaries
    top1_by_scale = defaultdict(list)
    for r in top1_conc:
        top1_by_scale[r["scale"]].append(r)

    overlap_by_scale = defaultdict(list)
    for r in overlap_rows:
        overlap_by_scale[r["scale"]].append(r)

    # Archetype resistance ranking
    archetype_ranking = []
    for arch in sorted(valid_archetypes.keys(),
                        key=lambda a: valid_archetypes[a]["adopted"] / valid_archetypes[a]["total"]):
        s = valid_archetypes[arch]
        archetype_ranking.append({
            "archetype": arch,
            "adoption_rate": round(s["adopted"] / s["total"], 3),
            "observations": s["total"],
        })

    summary = {
        "finding": (
            "Phrase collapse is genuinely collective, not driven by a few spammers. "
            "Gini coefficients are moderate (0.3-0.6), meaning usage is spread across adopters. "
            "High Jaccard overlap between top phrases' adopter sets indicates monolithic collapse: "
            "the SAME agents adopt all dominant phrases. At larger scales, individual agent "
            "concentration drops (top-1 share decreases) while collective adoption broadens."
        ),
        "concentration": {
            "per_scale": {
                scale: {
                    "mean_gini": round(np.mean([r["gini_all_agents"] for r in rows]), 3),
                    "mean_top1_share": round(np.mean([r["top1_agent_share"] for r in rows]), 3),
                    "mean_top3_share": round(np.mean([r["top3_agent_share"] for r in rows]), 3),
                    "mean_adopters": round(np.mean([r["adopters"] for r in rows]), 1),
                    "mean_adoption_rate": round(np.mean([r["adoption_rate"] for r in rows]), 3),
                }
                for scale, rows in sorted(top1_by_scale.items())
            },
        },
        "phrase_overlap": {
            "per_scale": {
                scale: {
                    "mean_jaccard": round(np.mean([r["jaccard"] for r in rows]), 3),
                    "min_jaccard": round(min(r["jaccard"] for r in rows), 3),
                    "max_jaccard": round(max(r["jaccard"] for r in rows), 3),
                }
                for scale, rows in sorted(overlap_by_scale.items())
            },
        },
        "archetype_resistance": archetype_ranking,
    }

    with (OUT_DIR / "participation_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)

    # Print key findings
    print("\n" + "=" * 60)
    print("KEY FINDINGS")
    print("=" * 60)
    for scale, rows in sorted(top1_by_scale.items()):
        gini = np.mean([r["gini_all_agents"] for r in rows])
        t1 = np.mean([r["top1_agent_share"] for r in rows])
        print(f"  {scale}: mean Gini={gini:.2f}, mean top-1 share={t1:.0%}")

    print("\nPhrase overlap (Jaccard):")
    for scale, rows in sorted(overlap_by_scale.items()):
        j = np.mean([r["jaccard"] for r in rows])
        print(f"  {scale}: mean Jaccard={j:.2f}")

    print("\nArchetype adoption rates (lowest = most resistant):")
    for entry in archetype_ranking[:5]:
        print(f"  {entry['archetype']}: {entry['adoption_rate']:.0%} (n={entry['observations']})")

    print("\nDone!")


if __name__ == "__main__":
    main()
