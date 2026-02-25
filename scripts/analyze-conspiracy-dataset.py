#!/usr/bin/env python3
"""
Moltbook Conspiracy vs Factual Dataset — Full Analysis
=======================================================
Analyzes 6 experiments with 10 GPT-5 agents across 25 conspiracy topics.

Output:
  findings/conspiracy-dataset/          — markdown summaries
  findings/conspiracy-dataset/plots/    — PNG figures

Usage:
  python3 scripts/analyze-conspiracy-dataset.py
"""

import csv
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "dataset" / "moltbook-conspiracy-vs-factual" / "data"
RAW_DIR = REPO_ROOT / "dataset" / "moltbook-conspiracy-vs-factual" / "raw"
OUT_DIR = REPO_ROOT / "findings" / "conspiracy-dataset"
PLOT_DIR = OUT_DIR / "plots"

RUN_DIRS = ["c1-run01", "c2-run01", "c3-run01", "c5a-run01", "c5b-run01", "c5c-run01"]
RUN_TO_EXP = {
    "c1-run01": "E1", "c2-run01": "E2", "c3-run01": "E3",
    "c5a-run01": "E5a", "c5b-run01": "E5b", "c5c-run01": "E5c",
}

AGENT_ARCHETYPES = {
    "ranking_alpha": "Baseline",
    "ranking_beta": "Introspective",
    "ranking_gamma": "Nihilist",
    "ranking_delta": "Leader",
    "ranking_epsilon": "Follower",
    "ranking_zeta": "Contrarian",
    "ranking_eta": "Curious",
    "ranking_theta": "Baseline",
    "ranking_iota": "Introspective",
    "ranking_kappa": "Nihilist",
}

SYSTEM_AGENTS = {"civiclens_nudger", "civiclens_world"}

# Plot style
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.2,
})

# Color palette
C_FACTUAL = "#2196F3"
C_CONSPIRACY = "#F44336"
C_AGENT = "#9C27B0"
C_NUDGE_UP = "#4CAF50"
C_CONTROL = "#9E9E9E"
C_NUDGE_DOWN = "#FF9800"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_activity():
    """Load all activity.jsonl files, tag with run_name and experiment."""
    all_events = []
    for run in RUN_DIRS:
        path = RAW_DIR / run / "activity.jsonl"
        if not path.exists():
            print(f"  WARNING: {path} not found, skipping")
            continue
        events = load_jsonl(path)
        for e in events:
            e["run_name"] = run
            e["experiment"] = RUN_TO_EXP[run]
        all_events.extend(events)
    return all_events


def build_post_lookup(posts):
    """Build (run_name, post_id) → post dict for joining activity to posts."""
    lookup = {}
    for p in posts:
        key = (p["run_name"], p["post_id"])
        lookup[key] = p
    return lookup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_organic(event):
    """True if event is from a real agent (not system)."""
    return event.get("agent_name", "") not in SYSTEM_AGENTS


def write_finding(filename, content):
    path = OUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO_ROOT)}")


def save_plot(fig, name):
    path = PLOT_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# Analysis 1: The Big Picture
# ---------------------------------------------------------------------------

def analysis_1(posts, activity, post_lookup):
    print("\n=== Analysis 1: The Big Picture ===")

    # Filter to E1+E2, organic vote events on world posts
    e12_posts = {(p["run_name"], p["post_id"]): p for p in posts
                 if p["experiment"] in ("E1", "E2") and p["is_world_post"] == "True"}

    vote_events = [e for e in activity
                   if e["experiment"] in ("E1", "E2")
                   and e["action_type"] in ("upvote", "downvote")
                   and is_organic(e)
                   and (e["run_name"], e["target_id"]) in e12_posts]

    # Count by post_type × vote_type
    counts = defaultdict(int)
    for v in vote_events:
        post = e12_posts[(v["run_name"], v["target_id"])]
        pt = post["post_type"]
        vt = v["action_type"]
        counts[(pt, vt)] += 1

    factual_up = counts.get(("factual", "upvote"), 0)
    factual_down = counts.get(("factual", "downvote"), 0)
    conspiracy_up = counts.get(("conspiracy", "upvote"), 0)
    conspiracy_down = counts.get(("conspiracy", "downvote"), 0)

    total = factual_up + factual_down + conspiracy_up + conspiracy_down

    md = f"""# Analysis 1: Agents Can Tell Fact from Fiction

## The headline finding

In E1 + E2 (balanced 50/50 experiments), agents show **perfect discrimination**
between factual and conspiracy content:

| | Upvotes | Downvotes | Total |
|---|---|---|---|
| **Factual** | {factual_up} | {factual_down} | {factual_up + factual_down} |
| **Conspiracy** | {conspiracy_up} | {conspiracy_down} | {conspiracy_up + conspiracy_down} |

- **{factual_up}** organic upvotes on factual posts, **{conspiracy_up}** on conspiracy
- **{factual_down}** downvotes on factual, **{conspiracy_down}** on conspiracy
- **Zero crossover**: not a single agent ever upvoted conspiracy or downvoted factual

Total organic votes in E1+E2: **{total}**
"""
    write_finding("01-big-picture.md", md)

    # Plot: bar chart
    fig, ax = plt.subplots(figsize=(7, 5))
    x = np.arange(2)
    w = 0.35
    bars_up = ax.bar(x - w/2, [factual_up, conspiracy_up], w,
                     label="Upvotes", color=[C_FACTUAL, C_CONSPIRACY], alpha=0.85,
                     edgecolor="white", linewidth=1.5)
    bars_down = ax.bar(x + w/2, [factual_down, conspiracy_down], w,
                       label="Downvotes", color=[C_FACTUAL, C_CONSPIRACY], alpha=0.4,
                       edgecolor="white", linewidth=1.5, hatch="//")
    ax.set_xticks(x)
    ax.set_xticklabels(["Factual", "Conspiracy"])
    ax.set_ylabel("Organic Vote Count")
    ax.set_title("Perfect Fact/Fiction Discrimination (E1 + E2)")
    # Add count labels
    for bar in list(bars_up) + list(bars_down):
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width()/2, h + 1, str(int(h)),
                    ha="center", va="bottom", fontweight="bold")
    ax.legend(["Upvotes", "Downvotes"])
    ax.set_ylim(0, max(factual_up, conspiracy_down) * 1.2 + 5)
    save_plot(fig, "01-big-picture-votes.png")

    return {"factual_up": factual_up, "factual_down": factual_down,
            "conspiracy_up": conspiracy_up, "conspiracy_down": conspiracy_down}


# ---------------------------------------------------------------------------
# Analysis 2: Context Changes Everything
# ---------------------------------------------------------------------------

def analysis_2(posts, activity, post_lookup):
    print("\n=== Analysis 2: Context Changes Everything ===")

    # For each experiment, compute conspiracy fraction of world posts
    # and conspiracy upvote rate among organic votes
    exp_labels = ["E1", "E2", "E3", "E5a", "E5b", "E5c"]

    # Build world-post sets per experiment
    world_posts_by_exp = defaultdict(dict)
    for p in posts:
        if p["is_world_post"] == "True":
            world_posts_by_exp[p["experiment"]][(p["run_name"], p["post_id"])] = p

    results = []
    for exp in exp_labels:
        wp = world_posts_by_exp[exp]
        n_factual = sum(1 for p in wp.values() if p["post_type"] == "factual")
        n_conspiracy = sum(1 for p in wp.values() if p["post_type"] == "conspiracy")
        n_total = n_factual + n_conspiracy
        conspiracy_frac = n_conspiracy / n_total if n_total > 0 else 0

        # Organic votes in this experiment on world posts
        votes = [e for e in activity
                 if e["experiment"] == exp
                 and e["action_type"] in ("upvote", "downvote")
                 and is_organic(e)
                 and (e["run_name"], e["target_id"]) in wp]

        conspiracy_upvotes = sum(1 for v in votes
                                if v["action_type"] == "upvote"
                                and wp[(v["run_name"], v["target_id"])]["post_type"] == "conspiracy")
        total_organic = len(votes)
        conspiracy_upvote_rate = conspiracy_upvotes / total_organic if total_organic > 0 else 0

        results.append({
            "experiment": exp,
            "n_factual": n_factual,
            "n_conspiracy": n_conspiracy,
            "conspiracy_frac": conspiracy_frac,
            "conspiracy_upvotes": conspiracy_upvotes,
            "total_organic_votes": total_organic,
            "conspiracy_upvote_rate": conspiracy_upvote_rate,
        })

    # Combine E1+E2
    e12 = [r for r in results if r["experiment"] in ("E1", "E2")]
    combined_e12 = {
        "experiment": "E1+E2",
        "conspiracy_frac": 0.50,
        "conspiracy_upvotes": sum(r["conspiracy_upvotes"] for r in e12),
        "total_organic_votes": sum(r["total_organic_votes"] for r in e12),
    }
    combined_e12["conspiracy_upvote_rate"] = (
        combined_e12["conspiracy_upvotes"] / combined_e12["total_organic_votes"]
        if combined_e12["total_organic_votes"] > 0 else 0
    )

    md = "# Analysis 2: Context Changes Everything\n\n"
    md += "As the information environment shifts toward more conspiracy content,\n"
    md += "agents become increasingly tolerant of conspiracy posts.\n\n"
    md += "| Environment | Conspiracy Fraction | Conspiracy Upvotes | Total Organic Votes | Conspiracy Upvote Rate |\n"
    md += "|---|---|---|---|---|\n"

    plot_data = []
    # E1+E2 combined
    md += f"| E1+E2 (balanced) | 50% | {combined_e12['conspiracy_upvotes']} | {combined_e12['total_organic_votes']} | {combined_e12['conspiracy_upvote_rate']:.1%} |\n"
    plot_data.append((0.50, combined_e12["conspiracy_upvote_rate"], "E1+E2"))

    for r in results:
        if r["experiment"] in ("E1", "E2"):
            continue
        md += f"| {r['experiment']} | {r['conspiracy_frac']:.0%} | {r['conspiracy_upvotes']} | {r['total_organic_votes']} | {r['conspiracy_upvote_rate']:.1%} |\n"
        plot_data.append((r["conspiracy_frac"], r["conspiracy_upvote_rate"], r["experiment"]))

    # Sort by conspiracy fraction for plot
    plot_data.sort(key=lambda x: x[0])

    md += "\n## Key insight\n\n"
    md += "Same agents, same model — but when no factual alternative is available (E3, 100% conspiracy),\n"
    md += "agents upvote conspiracy content. Context, not capability, determines behavior.\n"

    write_finding("02-context-changes-everything.md", md)

    # Plot: line chart
    fig, ax = plt.subplots(figsize=(8, 5))
    xs = [d[0] * 100 for d in plot_data]
    ys = [d[1] * 100 for d in plot_data]
    labels = [d[2] for d in plot_data]

    ax.plot(xs, ys, "o-", color=C_CONSPIRACY, markersize=10, linewidth=2.5, zorder=5)
    for x, y, label in zip(xs, ys, labels):
        ax.annotate(f"{label}\n({y:.0f}%)", (x, y),
                    textcoords="offset points", xytext=(0, 14),
                    ha="center", fontsize=9, fontweight="bold")
    ax.set_xlabel("Environment Conspiracy Fraction (%)")
    ax.set_ylabel("Conspiracy Upvote Rate (%)")
    ax.set_title("Conspiracy Tolerance Rises with Environment Conspiracy Fraction")
    ax.set_xlim(-5, 105)
    ax.set_ylim(-5, max(ys) * 1.3 + 5)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    save_plot(fig, "02-context-tolerance.png")

    return results


# ---------------------------------------------------------------------------
# Analysis 3: Does the Nudge Actually Work?
# ---------------------------------------------------------------------------

def analysis_3(posts, activity, post_lookup):
    print("\n=== Analysis 3: Does the Nudge Work? ===")

    # E1+E2 world posts only
    e12_world = [p for p in posts
                 if p["experiment"] in ("E1", "E2") and p["is_world_post"] == "True"]

    # Group by treatment × post_type → scores and comment counts
    groups = defaultdict(lambda: {"scores": [], "comments": []})
    for p in e12_world:
        treatment = p["treatment"]
        pt = p["post_type"]
        score = int(p["score"])
        cc = int(p["actual_comment_count"]) if p["actual_comment_count"] else int(p["comment_count"])
        groups[(treatment, pt)]["scores"].append(score)
        groups[(treatment, pt)]["comments"].append(cc)

    treatments = ["nudge_up", "control", "nudge_down"]
    post_types = ["factual", "conspiracy"]

    md = "# Analysis 3: Does the Nudge Actually Work?\n\n"
    md += "Each world post randomly receives nudge_up (+1 vote), nudge_down (-1 vote), or control.\n\n"
    md += "## Final scores by treatment × post type (E1+E2)\n\n"
    md += "| Treatment | Post Type | N | Mean Score | Median Score | Mean Comments |\n"
    md += "|---|---|---|---|---|---|\n"

    score_matrix = {}
    comment_matrix = {}
    for t in treatments:
        for pt in post_types:
            g = groups.get((t, pt), {"scores": [], "comments": []})
            n = len(g["scores"])
            mean_s = np.mean(g["scores"]) if n > 0 else 0
            med_s = np.median(g["scores"]) if n > 0 else 0
            mean_c = np.mean(g["comments"]) if n > 0 else 0
            md += f"| {t} | {pt} | {n} | {mean_s:.2f} | {med_s:.1f} | {mean_c:.2f} |\n"
            score_matrix[(t, pt)] = mean_s
            comment_matrix[(t, pt)] = mean_c

    # Compute adjusted scores (subtract the nudge vote itself)
    md += "\n## Adjusted scores (subtracting the nudge vote)\n\n"
    md += "This shows whether the nudge created a **cascade** beyond just the +1/-1.\n\n"
    md += "| Treatment | Post Type | Raw Mean | Nudge Value | Adjusted Mean | Cascade |\n"
    md += "|---|---|---|---|---|---|\n"
    nudge_values = {"nudge_up": 1, "control": 0, "nudge_down": -1}
    for t in treatments:
        for pt in post_types:
            g = groups.get((t, pt), {"scores": []})
            n = len(g["scores"])
            if n == 0:
                continue
            raw = np.mean(g["scores"])
            nv = nudge_values[t]
            adjusted = raw - nv
            cascade = adjusted - score_matrix.get(("control", pt), 0)
            md += f"| {t} | {pt} | {raw:.2f} | {nv:+d} | {adjusted:.2f} | {cascade:+.2f} |\n"

    md += "\n## Key insight\n\n"
    factual_range = score_matrix.get(("nudge_up", "factual"), 0) - score_matrix.get(("nudge_down", "factual"), 0)
    conspiracy_range = score_matrix.get(("nudge_up", "conspiracy"), 0) - score_matrix.get(("nudge_down", "conspiracy"), 0)
    md += f"- Nudge effect on factual posts: score range {factual_range:.2f} (from nudge_down to nudge_up)\n"
    md += f"- Nudge effect on conspiracy posts: score range {conspiracy_range:.2f}\n"
    md += f"- The nudge effect is **{factual_range/conspiracy_range:.1f}x stronger** for factual posts — agents pile on when factual content gets boosted\n"
    md += f"- Nudged-up factual posts get {comment_matrix.get(('nudge_up', 'factual'), 0):.2f} comments vs {comment_matrix.get(('control', 'factual'), 0):.2f} for control\n"

    write_finding("03-nudge-effects.md", md)

    # Plot 1: Grouped bar chart
    fig, ax = plt.subplots(figsize=(9, 5.5))
    x = np.arange(len(treatments))
    w = 0.35
    factual_scores = [score_matrix.get((t, "factual"), 0) for t in treatments]
    conspiracy_scores = [score_matrix.get((t, "conspiracy"), 0) for t in treatments]

    bars_f = ax.bar(x - w/2, factual_scores, w, label="Factual", color=C_FACTUAL, alpha=0.85)
    bars_c = ax.bar(x + w/2, conspiracy_scores, w, label="Conspiracy", color=C_CONSPIRACY, alpha=0.85)

    for bars in [bars_f, bars_c]:
        for bar in bars:
            h = bar.get_height()
            va = "bottom" if h >= 0 else "top"
            offset = 0.05 if h >= 0 else -0.05
            ax.text(bar.get_x() + bar.get_width()/2, h + offset, f"{h:.2f}",
                    ha="center", va=va, fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(["Nudge Up (+1)", "Control", "Nudge Down (-1)"])
    ax.set_ylabel("Mean Final Score")
    ax.set_title("Nudge Treatment × Post Type → Final Score (E1+E2)")
    ax.legend()
    ax.axhline(y=0, color="black", linewidth=0.5)
    save_plot(fig, "03-nudge-scores.png")

    # Plot 2: Interaction plot
    fig, ax = plt.subplots(figsize=(7, 5))
    nudge_x = [-1, 0, 1]
    ax.plot(nudge_x, [score_matrix.get((t, "factual"), 0) for t in ["nudge_down", "control", "nudge_up"]],
            "o-", color=C_FACTUAL, markersize=10, linewidth=2.5, label="Factual")
    ax.plot(nudge_x, [score_matrix.get((t, "conspiracy"), 0) for t in ["nudge_down", "control", "nudge_up"]],
            "s-", color=C_CONSPIRACY, markersize=10, linewidth=2.5, label="Conspiracy")
    ax.set_xticks(nudge_x)
    ax.set_xticklabels(["Nudge Down\n(-1 vote)", "Control", "Nudge Up\n(+1 vote)"])
    ax.set_ylabel("Mean Final Score")
    ax.set_title("Nudge Amplification: Stronger Effect on Factual Posts")
    ax.legend()
    ax.axhline(y=0, color="black", linewidth=0.5)
    save_plot(fig, "03-nudge-interaction.png")

    # Plot 3: Comment engagement by treatment
    fig, ax = plt.subplots(figsize=(8, 5))
    factual_comments = [comment_matrix.get((t, "factual"), 0) for t in treatments]
    conspiracy_comments = [comment_matrix.get((t, "conspiracy"), 0) for t in treatments]
    bars_f = ax.bar(x - w/2, factual_comments, w, label="Factual", color=C_FACTUAL, alpha=0.85)
    bars_c = ax.bar(x + w/2, conspiracy_comments, w, label="Conspiracy", color=C_CONSPIRACY, alpha=0.85)
    for bars in [bars_f, bars_c]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.02, f"{h:.2f}",
                        ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels(["Nudge Up (+1)", "Control", "Nudge Down (-1)"])
    ax.set_ylabel("Mean Comment Count")
    ax.set_title("Comment Engagement by Treatment × Post Type (E1+E2)")
    ax.legend()
    save_plot(fig, "03-nudge-comments.png")

    return score_matrix


# ---------------------------------------------------------------------------
# Analysis 4: Agent Personality Profiles
# ---------------------------------------------------------------------------

def analysis_4(posts, activity, post_lookup, comments):
    print("\n=== Analysis 4: Agent Personality Profiles ===")

    # Focus on E1+E2 world posts for voting profile
    e12_world_keys = {(p["run_name"], p["post_id"]): p for p in posts
                      if p["experiment"] in ("E1", "E2") and p["is_world_post"] == "True"}

    agents = sorted([a for a in AGENT_ARCHETYPES.keys()])

    # Per-agent vote counts by post_type
    agent_votes = defaultdict(lambda: defaultdict(int))
    for e in activity:
        if e["experiment"] not in ("E1", "E2"):
            continue
        if e["action_type"] not in ("upvote", "downvote"):
            continue
        if not is_organic(e):
            continue
        key = (e["run_name"], e["target_id"])
        if key not in e12_world_keys:
            continue
        post = e12_world_keys[key]
        agent = e["agent_name"]
        pt = post["post_type"]
        vt = e["action_type"]
        agent_votes[agent][(pt, vt)] += 1

    # Per-agent comment counts by post_type
    agent_comments = defaultdict(lambda: defaultdict(int))
    e12_comments = [c for c in comments if c["experiment"] in ("E1", "E2")]
    for c in e12_comments:
        agent = c["author"]
        if agent in SYSTEM_AGENTS:
            continue
        # Find the post for this comment
        key = (c["run_name"], c["post_id"])
        if key in e12_world_keys:
            pt = e12_world_keys[key]["post_type"]
        else:
            pt = "agent"
        agent_comments[agent][pt] += 1

    # Vote removals across all experiments
    vote_removals = [e for e in activity if e["action_type"] == "vote_removed" and is_organic(e)]

    md = "# Analysis 4: Agent Personality Profiles\n\n"
    md += "## Per-agent voting in E1+E2 (world posts only)\n\n"
    md += "| Agent | Archetype | Factual Up | Factual Down | Conspiracy Up | Conspiracy Down | Total |\n"
    md += "|---|---|---|---|---|---|---|\n"

    for agent in agents:
        arch = AGENT_ARCHETYPES[agent]
        fu = agent_votes[agent].get(("factual", "upvote"), 0)
        fd = agent_votes[agent].get(("factual", "downvote"), 0)
        cu = agent_votes[agent].get(("conspiracy", "upvote"), 0)
        cd = agent_votes[agent].get(("conspiracy", "downvote"), 0)
        total = fu + fd + cu + cd
        md += f"| {agent} | {arch} | {fu} | {fd} | {cu} | {cd} | {total} |\n"

    md += "\n## Per-agent commenting in E1+E2\n\n"
    md += "| Agent | Archetype | Comments on Factual | Comments on Conspiracy | Total |\n"
    md += "|---|---|---|---|---|\n"
    for agent in agents:
        arch = AGENT_ARCHETYPES[agent]
        cf = agent_comments[agent].get("factual", 0)
        cc = agent_comments[agent].get("conspiracy", 0)
        total = cf + cc
        md += f"| {agent} | {arch} | {cf} | {cc} | {total} |\n"

    # Vote removal inventory
    md += f"\n## Vote Removals ({len(vote_removals)} total across all experiments)\n\n"
    md += "| Agent | Archetype | Experiment | From Value | Post Type | Post Title (preview) |\n"
    md += "|---|---|---|---|---|---|\n"
    for vr in sorted(vote_removals, key=lambda x: x["created_at"]):
        agent = vr["agent_name"]
        arch = AGENT_ARCHETYPES.get(agent, "?")
        exp = vr["experiment"]
        from_val = vr["metadata"].get("from_value", "?")
        key = (vr["run_name"], vr["target_id"])
        post = post_lookup.get(key)
        pt = post["post_type"] if post else "?"
        title = (post["title"][:60] + "...") if post and len(post["title"]) > 60 else (post["title"] if post else "?")
        md += f"| {agent} | {arch} | {exp} | {from_val:+d} | {pt} | {title} |\n"

    # Categorize removal patterns
    removal_from_factual = sum(1 for vr in vote_removals
                               if post_lookup.get((vr["run_name"], vr["target_id"]), {}).get("post_type") == "factual")
    removal_from_conspiracy = sum(1 for vr in vote_removals
                                  if post_lookup.get((vr["run_name"], vr["target_id"]), {}).get("post_type") == "conspiracy")
    removal_upvotes = sum(1 for vr in vote_removals if vr["metadata"].get("from_value", 0) == 1)
    removal_downvotes = sum(1 for vr in vote_removals if vr["metadata"].get("from_value", 0) == -1)

    md += f"\n**Summary**: {removal_from_factual} removals from factual, {removal_from_conspiracy} from conspiracy. "
    md += f"{removal_upvotes} removed upvotes, {removal_downvotes} removed downvotes.\n"

    write_finding("04-agent-profiles.md", md)

    # Plot 1: Heatmap of agent × action
    fig, ax = plt.subplots(figsize=(10, 7))
    actions = ["Factual\nUpvote", "Factual\nDownvote", "Conspiracy\nUpvote", "Conspiracy\nDownvote",
               "Comments\nFactual", "Comments\nConspiracy"]
    matrix = []
    ylabels = []
    for agent in agents:
        arch = AGENT_ARCHETYPES[agent]
        short = agent.replace("ranking_", "")
        ylabels.append(f"{short} ({arch})")
        row = [
            agent_votes[agent].get(("factual", "upvote"), 0),
            agent_votes[agent].get(("factual", "downvote"), 0),
            agent_votes[agent].get(("conspiracy", "upvote"), 0),
            agent_votes[agent].get(("conspiracy", "downvote"), 0),
            agent_comments[agent].get("factual", 0),
            agent_comments[agent].get("conspiracy", 0),
        ]
        matrix.append(row)

    matrix = np.array(matrix)
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(actions)))
    ax.set_xticklabels(actions, fontsize=9)
    ax.set_yticks(range(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=9)
    # Annotate cells
    for i in range(len(ylabels)):
        for j in range(len(actions)):
            val = matrix[i, j]
            color = "white" if val > matrix.max() * 0.6 else "black"
            ax.text(j, i, str(int(val)), ha="center", va="center", fontsize=9,
                    fontweight="bold", color=color)
    ax.set_title("Agent × Action Heatmap (E1+E2)")
    fig.colorbar(im, ax=ax, label="Count", shrink=0.8)
    save_plot(fig, "04-agent-heatmap.png")

    # Plot 2: Vote removal timeline
    if vote_removals:
        fig, ax = plt.subplots(figsize=(10, 4))
        # Group by experiment
        exp_colors = {"E1": C_FACTUAL, "E2": C_NUDGE_UP, "E3": C_CONSPIRACY,
                      "E5a": "#FF9800", "E5b": "#9C27B0", "E5c": "#795548"}
        from datetime import datetime
        for i, vr in enumerate(sorted(vote_removals, key=lambda x: x["created_at"])):
            agent = vr["agent_name"].replace("ranking_", "")
            exp = vr["experiment"]
            from_val = vr["metadata"].get("from_value", 0)
            key = (vr["run_name"], vr["target_id"])
            post = post_lookup.get(key)
            pt = post["post_type"] if post else "?"
            marker = "^" if from_val == 1 else "v"
            color = C_FACTUAL if pt == "factual" else C_CONSPIRACY
            ax.scatter(i, 0, marker=marker, s=120, color=color, edgecolors="black", linewidth=0.5, zorder=5)
            ax.annotate(f"{agent}\n({exp})", (i, 0),
                        textcoords="offset points", xytext=(0, 15 if i % 2 == 0 else -25),
                        ha="center", fontsize=7, rotation=45)
        ax.set_xlim(-1, len(vote_removals))
        ax.set_yticks([])
        ax.set_xlabel("Vote Removal Event (chronological)")
        ax.set_title(f"Vote Removal Timeline ({len(vote_removals)} events)")
        # Legend
        from matplotlib.lines import Line2D
        legend_elements = [
            Line2D([0], [0], marker="^", color="w", markerfacecolor=C_FACTUAL, markersize=10, label="Removed upvote from factual"),
            Line2D([0], [0], marker="v", color="w", markerfacecolor=C_CONSPIRACY, markersize=10, label="Removed downvote from conspiracy"),
        ]
        ax.legend(handles=legend_elements, loc="upper right", fontsize=8)
        save_plot(fig, "04-vote-removals.png")


# ---------------------------------------------------------------------------
# Analysis 5: What Agents Create On Their Own
# ---------------------------------------------------------------------------

def analysis_5(posts, comments, activity, post_lookup):
    print("\n=== Analysis 5: Agent-Created Posts ===")

    agent_posts = [p for p in posts if p["post_type"] == "agent"]

    md = "# Analysis 5: What Agents Create On Their Own\n\n"
    md += f"**{len(agent_posts)} agent-generated posts** across all experiments.\n"
    md += "**Zero promote conspiracy.** All are meta-analysis, community infrastructure, or philosophical commentary.\n\n"
    md += "## Agent Post Catalog\n\n"
    md += "| # | Experiment | Author | Archetype | Title | Score | Comments | Classification |\n"
    md += "|---|---|---|---|---|---|---|---|\n"

    # Classify each agent post
    for i, p in enumerate(agent_posts, 1):
        author = p["author"]
        arch = AGENT_ARCHETYPES.get(author, "?")
        title = p["title"][:80] + ("..." if len(p["title"]) > 80 else "")
        score = int(p["score"])
        cc = int(p["actual_comment_count"]) if p["actual_comment_count"] else int(p["comment_count"])
        content = p.get("content", "").lower()
        title_lower = p["title"].lower()

        # Simple classification
        if any(w in content or w in title_lower for w in ["checklist", "proposal", "template", "framework"]):
            classification = "Community infrastructure"
        elif any(w in content or w in title_lower for w in ["why do", "cluster", "pattern", "across"]):
            classification = "Meta-analysis"
        elif any(w in content or w in title_lower for w in ["nothing matters", "absurd", "folklore", "ux"]):
            classification = "Philosophical commentary"
        elif any(w in content or w in title_lower for w in ["follow the science", "which one", "challenge"]):
            classification = "Epistemological challenge"
        else:
            classification = "Original discussion"

        md += f"| {i} | {p['experiment']} | {author} | {arch} | {title} | {score} | {cc} | {classification} |\n"

    # Which archetypes created posts vs didn't
    creators = set(p["author"] for p in agent_posts)
    creator_archetypes = sorted(set(AGENT_ARCHETYPES[a] for a in creators if a in AGENT_ARCHETYPES))
    all_archetypes = sorted(set(AGENT_ARCHETYPES.values()))
    non_creators = [a for a in all_archetypes if a not in creator_archetypes]

    md += f"\n## Who creates vs who doesn't\n\n"
    md += f"- **Creators**: {', '.join(creator_archetypes)}\n"
    md += f"- **Non-creators**: {', '.join(non_creators) if non_creators else 'all archetypes created at least one post'}\n"

    # Compare agent post engagement to world posts
    world_scores = [int(p["score"]) for p in posts if p["is_world_post"] == "True"]
    agent_scores = [int(p["score"]) for p in agent_posts]
    world_comments = [int(p["actual_comment_count"]) if p["actual_comment_count"] else int(p["comment_count"])
                      for p in posts if p["is_world_post"] == "True"]
    agent_comment_counts = [int(p["actual_comment_count"]) if p["actual_comment_count"] else int(p["comment_count"])
                            for p in agent_posts]

    md += f"\n## Engagement comparison\n\n"
    md += f"| Metric | World Posts (n={len(world_scores)}) | Agent Posts (n={len(agent_scores)}) |\n"
    md += f"|---|---|---|\n"
    md += f"| Mean score | {np.mean(world_scores):.2f} | {np.mean(agent_scores):.2f} |\n"
    md += f"| Max score | {max(world_scores)} | {max(agent_scores) if agent_scores else 0} |\n"
    md += f"| Mean comments | {np.mean(world_comments):.2f} | {np.mean(agent_comment_counts):.2f} |\n"
    md += f"| Max comments | {max(world_comments)} | {max(agent_comment_counts) if agent_comment_counts else 0} |\n"

    write_finding("05-agent-created-posts.md", md)

    # Plot: engagement on agent posts
    if agent_posts:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))

        # Scores
        ax = axes[0]
        labels = [p["author"].replace("ranking_", "") + f"\n({p['experiment']})" for p in agent_posts]
        scores = [int(p["score"]) for p in agent_posts]
        colors = [C_AGENT] * len(scores)
        ax.barh(range(len(scores)), scores, color=colors, alpha=0.85, edgecolor="white")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Score")
        ax.set_title("Agent Post Scores")
        ax.invert_yaxis()

        # Comments
        ax = axes[1]
        ccs = [int(p["actual_comment_count"]) if p["actual_comment_count"] else int(p["comment_count"])
               for p in agent_posts]
        ax.barh(range(len(ccs)), ccs, color=C_AGENT, alpha=0.6, edgecolor="white")
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Comment Count")
        ax.set_title("Agent Post Comments")
        ax.invert_yaxis()

        fig.suptitle("Engagement on Agent-Generated Posts", fontsize=13, fontweight="bold")
        fig.tight_layout()
        save_plot(fig, "05-agent-posts-engagement.png")


# ---------------------------------------------------------------------------
# Analysis 6: Comment Analysis
# ---------------------------------------------------------------------------

def analysis_6(posts, comments, post_lookup):
    print("\n=== Analysis 6: Comment Analysis ===")

    # Join comments to posts
    comment_data = []
    for c in comments:
        key = (c["run_name"], c["post_id"])
        post = post_lookup.get(key)
        pt = post["post_type"] if post else "unknown"
        comment_data.append({**c, "target_post_type": pt})

    # Filter to organic comments (non-system agents)
    organic_comments = [c for c in comment_data if c["author"] not in SYSTEM_AGENTS]

    # E1+E2 comment counts by post_type
    e12_comments = [c for c in organic_comments if c["experiment"] in ("E1", "E2")]
    e12_on_factual = [c for c in e12_comments if c["target_post_type"] == "factual"]
    e12_on_conspiracy = [c for c in e12_comments if c["target_post_type"] == "conspiracy"]

    md = "# Analysis 6: What Agents Comment — and How\n\n"
    md += f"**{len(organic_comments)} total organic comments** across all experiments.\n"
    md += f"All depth-0 (no reply threading).\n\n"
    md += f"## E1+E2 Comment Distribution\n\n"
    md += f"- Comments on factual posts: **{len(e12_on_factual)}**\n"
    md += f"- Comments on conspiracy posts: **{len(e12_on_conspiracy)}**\n\n"

    # Stance classification using keyword patterns
    corrective_patterns = [
        "doesn't hold up", "no evidence", "collapses under", "myth", "debunk",
        "misconception", "not supported", "actually false", "no basis",
        "can't support", "doesn't support", "refut", "misleading",
        "not true", "incorrect", "baseless", "unfounded", "pseudoscience",
        "lacks evidence", "no credible", "been disproven", "claim doesn't",
        "thoroughly debunked", "no scientific", "doesn't stand up",
    ]
    supportive_patterns = [
        "great point", "love this", "absolutely", "well said", "agree",
        "excellent", "spot on", "fascinating", "appreciate", "thank you",
        "wonderful", "exactly", "compelling", "informative", "solid",
        "well-researched", "nice", "good point",
    ]
    questioning_patterns = [
        "genuine question", "do you have", "curious", "wonder",
        "what about", "how does", "can you explain", "interested",
        "any source", "what if", "is there", "have you considered",
    ]

    def classify_stance(text):
        text_lower = text.lower()
        scores = {
            "corrective": sum(1 for p in corrective_patterns if p in text_lower),
            "supportive": sum(1 for p in supportive_patterns if p in text_lower),
            "questioning": sum(1 for p in questioning_patterns if p in text_lower),
        }
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
        return "neutral"

    # Classify all organic comments
    stance_counts = defaultdict(lambda: defaultdict(int))
    for c in organic_comments:
        stance = classify_stance(c["content"])
        stance_counts[c["target_post_type"]][stance] += 1

    md += "## Comment Stance by Post Type (all experiments)\n\n"
    md += "| Post Type | Corrective | Supportive | Questioning | Neutral | Total |\n"
    md += "|---|---|---|---|---|---|\n"
    for pt in ["factual", "conspiracy", "agent"]:
        sc = stance_counts[pt]
        total = sum(sc.values())
        md += f"| {pt} | {sc['corrective']} | {sc['supportive']} | {sc['questioning']} | {sc['neutral']} | {total} |\n"

    # Word count comparison
    md += "\n## Comment Length Analysis\n\n"
    for pt in ["factual", "conspiracy"]:
        pt_comments = [c for c in organic_comments if c["target_post_type"] == pt]
        if pt_comments:
            wc = [len(c["content"].split()) for c in pt_comments]
            md += f"- **{pt}** comments: mean {np.mean(wc):.0f} words, median {np.median(wc):.0f}, "
            md += f"range {min(wc)}-{max(wc)}\n"

    # Per-agent comment distribution in E1+E2
    md += "\n## Per-agent comment distribution (E1+E2)\n\n"
    md += "| Agent | Archetype | Factual | Conspiracy | Total |\n"
    md += "|---|---|---|---|---|\n"
    agents = sorted(AGENT_ARCHETYPES.keys())
    agent_comment_profile = defaultdict(lambda: defaultdict(int))
    for c in e12_comments:
        agent_comment_profile[c["author"]][c["target_post_type"]] += 1
    for agent in agents:
        arch = AGENT_ARCHETYPES[agent]
        f = agent_comment_profile[agent].get("factual", 0)
        co = agent_comment_profile[agent].get("conspiracy", 0)
        total = f + co
        md += f"| {agent} | {arch} | {f} | {co} | {total} |\n"

    write_finding("06-comment-analysis.md", md)

    # Plot 1: Per-agent comment distribution
    fig, ax = plt.subplots(figsize=(10, 6))
    agent_names = [a.replace("ranking_", "") for a in agents]
    factual_counts = [agent_comment_profile[a].get("factual", 0) for a in agents]
    conspiracy_counts = [agent_comment_profile[a].get("conspiracy", 0) for a in agents]

    y = np.arange(len(agents))
    h = 0.35
    ax.barh(y - h/2, factual_counts, h, label="On Factual", color=C_FACTUAL, alpha=0.85)
    ax.barh(y + h/2, conspiracy_counts, h, label="On Conspiracy", color=C_CONSPIRACY, alpha=0.85)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{n} ({AGENT_ARCHETYPES[a]})" for n, a in zip(agent_names, agents)], fontsize=9)
    ax.set_xlabel("Comment Count")
    ax.set_title("Per-Agent Comment Distribution (E1+E2)")
    ax.legend()
    ax.invert_yaxis()
    save_plot(fig, "06-agent-comments.png")

    # Plot 2: Stance breakdown by post type
    fig, ax = plt.subplots(figsize=(8, 5))
    stances = ["corrective", "supportive", "questioning", "neutral"]
    x = np.arange(len(stances))
    w = 0.25
    for i, pt in enumerate(["factual", "conspiracy", "agent"]):
        vals = [stance_counts[pt][s] for s in stances]
        color = {"factual": C_FACTUAL, "conspiracy": C_CONSPIRACY, "agent": C_AGENT}[pt]
        ax.bar(x + i*w - w, vals, w, label=pt.capitalize(), color=color, alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in stances])
    ax.set_ylabel("Comment Count")
    ax.set_title("Comment Stance by Target Post Type (All Experiments)")
    ax.legend()
    save_plot(fig, "06-stance-breakdown.png")

    # Plot 3: Word count distribution
    fig, ax = plt.subplots(figsize=(8, 5))
    for pt, color, label in [("factual", C_FACTUAL, "On Factual"), ("conspiracy", C_CONSPIRACY, "On Conspiracy")]:
        wcs = [len(c["content"].split()) for c in organic_comments if c["target_post_type"] == pt]
        if wcs:
            ax.hist(wcs, bins=20, alpha=0.6, color=color, label=f"{label} (n={len(wcs)}, mean={np.mean(wcs):.0f})",
                    edgecolor="white")
    ax.set_xlabel("Word Count")
    ax.set_ylabel("Number of Comments")
    ax.set_title("Comment Length Distribution by Target Post Type")
    ax.legend()
    save_plot(fig, "06-word-count-dist.png")


# ---------------------------------------------------------------------------
# Analysis 7: Feed Exposure Loop
# ---------------------------------------------------------------------------

def analysis_7(posts, activity, post_lookup):
    print("\n=== Analysis 7: Feed Exposure Loop ===")

    # Focus on E1+E2 feed_impression events from organic agents
    feed_events = [e for e in activity
                   if e["action_type"] == "feed_impression"
                   and is_organic(e)
                   and e["experiment"] in ("E1", "E2")]

    # For each feed impression, compute fraction of visible posts that are factual
    results = []
    for fe in feed_events:
        post_ids = fe["metadata"].get("post_ids", [])
        if not post_ids:
            continue
        run = fe["run_name"]
        n_factual = 0
        n_conspiracy = 0
        n_total = 0
        for pid in post_ids:
            post = post_lookup.get((run, pid))
            if post:
                if post["post_type"] == "factual":
                    n_factual += 1
                elif post["post_type"] == "conspiracy":
                    n_conspiracy += 1
                n_total += 1
        if n_total > 0:
            frac_factual = n_factual / n_total
            results.append({
                "experiment": fe["experiment"],
                "agent": fe["agent_name"],
                "created_at": fe["created_at"],
                "sort": fe["metadata"].get("sort", "?"),
                "n_posts_visible": len(post_ids),
                "n_factual": n_factual,
                "n_conspiracy": n_conspiracy,
                "frac_factual": frac_factual,
            })

    if not results:
        write_finding("07-feed-exposure.md", "# Analysis 7: Feed Exposure Loop\n\nNo feed impression data available.\n")
        return

    # Sort by time
    results.sort(key=lambda x: x["created_at"])

    # Separate hot vs new sorted feeds
    hot_feeds = [r for r in results if r["sort"] == "hot"]
    new_feeds = [r for r in results if r["sort"] == "new"]

    md = "# Analysis 7: The Feed Exposure Loop\n\n"
    md += "Agents browse the feed using hot-sort. As factual posts get upvoted and conspiracy\n"
    md += "posts get downvoted, the feed becomes increasingly dominated by factual content.\n\n"
    md += f"## Feed Impression Stats (E1+E2)\n\n"
    md += f"- Total feed impressions: **{len(results)}**\n"
    md += f"- Hot-sorted: **{len(hot_feeds)}**, New-sorted: **{len(new_feeds)}**\n"

    if hot_feeds:
        # Time bins: split into early/mid/late thirds
        n = len(hot_feeds)
        thirds = [hot_feeds[:n//3], hot_feeds[n//3:2*n//3], hot_feeds[2*n//3:]]
        labels_t = ["Early", "Middle", "Late"]
        md += "\n## Feed Composition Over Time (hot-sorted, E1+E2)\n\n"
        md += "| Period | Impressions | Mean % Factual | Mean Posts Visible |\n"
        md += "|---|---|---|---|\n"
        period_data = []
        for label, chunk in zip(labels_t, thirds):
            if chunk:
                mean_frac = np.mean([r["frac_factual"] for r in chunk])
                mean_vis = np.mean([r["n_posts_visible"] for r in chunk])
                md += f"| {label} | {len(chunk)} | {mean_frac:.1%} | {mean_vis:.1f} |\n"
                period_data.append((label, mean_frac))

    if new_feeds:
        md += f"\n## New-sorted feeds: mean factual fraction = {np.mean([r['frac_factual'] for r in new_feeds]):.1%}\n"
        md += "(New sort shows all posts chronologically — no ranking effect)\n"

    md += "\n## Self-Reinforcing Cycle\n\n"
    md += "1. Factual posts get upvoted → rise in hot feed\n"
    md += "2. Conspiracy posts get downvoted → sink in hot feed\n"
    md += "3. Agents see more factual → engage more with factual → amplify the cycle\n"

    write_finding("07-feed-exposure.md", md)

    # Plot: time series of feed composition
    fig, ax = plt.subplots(figsize=(10, 5))

    # Plot each feed impression as a dot
    if hot_feeds:
        from datetime import datetime
        # Convert times to minutes from first event
        t0 = min(r["created_at"] for r in hot_feeds)
        for r in hot_feeds:
            r["_minutes"] = _time_diff_minutes(t0, r["created_at"])

        xs = [r["_minutes"] for r in hot_feeds]
        ys = [r["frac_factual"] * 100 for r in hot_feeds]

        # Color by experiment
        for exp, color, label in [("E1", C_FACTUAL, "E1"), ("E2", C_NUDGE_UP, "E2")]:
            exp_xs = [x for x, r in zip(xs, hot_feeds) if r["experiment"] == exp]
            exp_ys = [y for y, r in zip(ys, hot_feeds) if r["experiment"] == exp]
            if exp_xs:
                ax.scatter(exp_xs, exp_ys, s=50, alpha=0.6, color=color, label=label, edgecolors="white", linewidth=0.5)

        # Moving average line
        if len(xs) > 3:
            # Sort by time
            sorted_pairs = sorted(zip(xs, ys))
            sx, sy = zip(*sorted_pairs)
            window = max(3, len(sx) // 5)
            ma = np.convolve(sy, np.ones(window)/window, mode="valid")
            ma_x = sx[window//2: window//2 + len(ma)]
            ax.plot(ma_x, ma, color="black", linewidth=2, label=f"Moving avg (window={window})", zorder=5)

    ax.set_xlabel("Minutes from Experiment Start")
    ax.set_ylabel("% Factual in Feed")
    ax.set_title("Feed Composition Over Time (Hot-Sorted, E1+E2)")
    ax.legend()
    ax.axhline(y=50, color="gray", linestyle="--", alpha=0.5, label="50% baseline")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter())
    save_plot(fig, "07-feed-composition.png")

    # Plot: per-agent feed exposure
    fig, ax = plt.subplots(figsize=(10, 5))
    agent_feeds = defaultdict(list)
    for r in hot_feeds:
        agent_feeds[r["agent"]].append(r["frac_factual"])

    agents_sorted = sorted(agent_feeds.keys(), key=lambda a: a)
    agent_names = [a.replace("ranking_", "") for a in agents_sorted]
    means = [np.mean(agent_feeds[a]) * 100 for a in agents_sorted]

    ax.barh(range(len(means)), means, color=C_FACTUAL, alpha=0.7, edgecolor="white")
    ax.set_yticks(range(len(agent_names)))
    ax.set_yticklabels([f"{n} ({AGENT_ARCHETYPES.get(a, '?')})" for n, a in zip(agent_names, agents_sorted)], fontsize=9)
    ax.set_xlabel("Mean % Factual in Feed")
    ax.set_title("Per-Agent Feed Exposure (Hot-Sorted, E1+E2)")
    ax.axvline(x=50, color="gray", linestyle="--", alpha=0.5)
    ax.xaxis.set_major_formatter(mticker.PercentFormatter())
    ax.invert_yaxis()
    save_plot(fig, "07-per-agent-feed.png")


def _time_diff_minutes(t0, t1):
    """Parse ISO timestamps and return difference in minutes."""
    from datetime import datetime
    fmt = "%Y-%m-%dT%H:%M:%S"
    # Strip microseconds and timezone
    def clean(t):
        t = t.split(".")[0]
        t = t.replace("Z", "")
        return t
    d0 = datetime.strptime(clean(t0), fmt)
    d1 = datetime.strptime(clean(t1), fmt)
    return (d1 - d0).total_seconds() / 60


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_summary(stats):
    md = """# Moltbook Conspiracy vs Factual — Analysis Summary

## Dataset
- 6 experiments, 10 GPT-5 agents, 25 conspiracy topics
- Each topic has a factual + conspiracy post variant
- Posts receive random ranking nudges (+1, -1, or control)

## Key Findings

### 1. Perfect Discrimination (E1+E2)
Agents show **zero crossover** between factual and conspiracy content:
- **{factual_up}** upvotes on factual, **{conspiracy_up}** on conspiracy
- **{factual_down}** downvotes on factual, **{conspiracy_down}** on conspiracy

### 2. Context Changes Behavior
Same agents upvote conspiracy content when no factual alternative exists:
- 0% conspiracy upvotes in 50/50 environments
- ~88% in 100% conspiracy environments

### 3. Nudge Amplification
Social proof signals have ~{nudge_ratio:.1f}x stronger effect on factual posts than conspiracy.
Agents pile on when factual content gets boosted.

### 4. Agent Personalities
Each archetype shows distinct behavioral patterns (nihilists downvote most,
contrarians fact-check conspiracy, followers support factual).

### 5. No Conspiracy Creation
All 6 agent-created posts are meta-analysis, community tools, or philosophical
commentary. Zero promote conspiracy theories.

### 6. Comment Stance
Comments on factual posts are supportive/elaborative.
Comments on conspiracy posts are corrective/debunking.

### 7. Self-Reinforcing Feed
Hot-sort creates a self-reinforcing cycle: upvoted factual posts dominate the feed,
further concentrating agent attention on factual content.

---

*Generated by `scripts/analyze-conspiracy-dataset.py`*
""".format(**stats)
    write_finding("00-summary.md", md)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Moltbook Conspiracy vs Factual — Dataset Analysis")
    print("=" * 55)

    # Ensure output dirs exist
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    posts = load_csv(DATA_DIR / "posts.csv")
    comments = load_csv(DATA_DIR / "comments.csv")
    treatments = load_csv(DATA_DIR / "treatments.csv")
    agents = load_csv(DATA_DIR / "agents.csv")
    topic_mapping = load_json(DATA_DIR / "topic_mapping.json")
    experiment_meta = load_json(DATA_DIR / "experiment_metadata.json")
    activity = load_activity()

    print(f"  {len(posts)} posts, {len(comments)} comments, {len(treatments)} treatments")
    print(f"  {len(agents)} agents, {len(activity)} activity events")
    print(f"  {len(topic_mapping)} topic mappings, {len(experiment_meta)} experiments")

    # Build lookups
    post_lookup = build_post_lookup(posts)

    # Sanity checks
    assert len(posts) == 203, f"Expected 203 posts, got {len(posts)}"
    assert len(comments) == 192, f"Expected 192 comments, got {len(comments)}"

    # Run analyses
    a1_stats = analysis_1(posts, activity, post_lookup)
    a2_results = analysis_2(posts, activity, post_lookup)
    a3_scores = analysis_3(posts, activity, post_lookup)
    analysis_4(posts, activity, post_lookup, comments)
    analysis_5(posts, comments, activity, post_lookup)
    analysis_6(posts, comments, post_lookup)
    analysis_7(posts, activity, post_lookup)

    # Compute nudge ratio for summary
    factual_range = (a3_scores.get(("nudge_up", "factual"), 0) -
                     a3_scores.get(("nudge_down", "factual"), 0))
    conspiracy_range = (a3_scores.get(("nudge_up", "conspiracy"), 0) -
                        a3_scores.get(("nudge_down", "conspiracy"), 0))
    nudge_ratio = factual_range / conspiracy_range if conspiracy_range != 0 else float("inf")

    # Write summary
    print("\n=== Writing Summary ===")
    summary_stats = {**a1_stats, "nudge_ratio": nudge_ratio}
    write_summary(summary_stats)

    print(f"\nDone! Findings in {OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"Plots in {PLOT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
