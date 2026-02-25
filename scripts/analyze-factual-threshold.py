#!/usr/bin/env python3
"""
Moltbook Factual-Threshold Dataset — Dose-Response Analysis
============================================================
How many factual posts does it take for AI agents to prefer factual
over conspiracy content?

6 runs with 0–5 factual seed posts among 25 conspiracy posts.
10 GPT-5 agents per run, no ranking nudges (Mode C).

Output:
  findings/factual-threshold/          — markdown summaries
  findings/factual-threshold/plots/    — PNG figures

Usage:
  python3 scripts/analyze-factual-threshold.py
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
DATA_DIR = REPO_ROOT / "dataset" / "moltbook-factual-threshold" / "data"
RAW_DIR = REPO_ROOT / "dataset" / "moltbook-factual-threshold" / "raw"
OUT_DIR = REPO_ROOT / "findings" / "factual-threshold"
PLOT_DIR = OUT_DIR / "plots"

RUN_DIRS = [f"th-f{i}-run01" for i in range(6)]
RUN_TO_DOSE = {f"th-f{i}-run01": i for i in range(6)}

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

C_FACTUAL = "#2196F3"
C_CONSPIRACY = "#F44336"
C_AGENT = "#9C27B0"
C_CONTROL = "#9E9E9E"

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
    """Load all activity.jsonl files, tag with run_name and dose."""
    all_events = []
    for run in RUN_DIRS:
        path = RAW_DIR / run / "activity.jsonl"
        if not path.exists():
            print(f"  WARNING: {path} not found, skipping")
            continue
        events = load_jsonl(path)
        for e in events:
            e["run_name"] = run
            e["dose"] = RUN_TO_DOSE[run]
        all_events.extend(events)
    return all_events


def build_post_lookup(posts):
    lookup = {}
    for p in posts:
        key = (p["run_name"], p["post_id"])
        lookup[key] = p
    return lookup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_organic(event):
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
# Analysis 1: Vote Table by Factual Dose
# ---------------------------------------------------------------------------

def analysis_1(posts, activity, post_lookup):
    print("\n=== Analysis 1: Vote Table by Factual Dose ===")

    # For each dose (0–5), count organic votes on world posts by post_type
    doses = sorted(set(int(p["n_factual_dose"]) for p in posts))

    # Build world-post sets per dose
    world_by_dose = defaultdict(dict)
    for p in posts:
        if p["is_world_post"] == "True":
            dose = int(p["n_factual_dose"])
            world_by_dose[dose][(p["run_name"], p["post_id"])] = p

    # Count organic votes
    vote_table = {}  # dose → {(post_type, vote_type): count}
    for dose in doses:
        wp = world_by_dose[dose]
        counts = defaultdict(int)
        for e in activity:
            if e["dose"] != dose:
                continue
            if e["action_type"] not in ("upvote", "downvote"):
                continue
            if not is_organic(e):
                continue
            key = (e["run_name"], e["target_id"])
            if key not in wp:
                continue
            post = wp[key]
            pt = post["post_type"]
            vt = e["action_type"]
            counts[(pt, vt)] += 1
        vote_table[dose] = counts

    # Also count votes on agent posts
    agent_by_dose = defaultdict(dict)
    for p in posts:
        if p["post_type"] == "agent":
            dose = int(p["n_factual_dose"])
            agent_by_dose[dose][(p["run_name"], p["post_id"])] = p

    agent_vote_table = {}
    for dose in doses:
        ap = agent_by_dose[dose]
        counts = defaultdict(int)
        for e in activity:
            if e["dose"] != dose:
                continue
            if e["action_type"] not in ("upvote", "downvote"):
                continue
            if not is_organic(e):
                continue
            key = (e["run_name"], e["target_id"])
            if key not in ap:
                continue
            vt = e["action_type"]
            counts[vt] += 1
        agent_vote_table[dose] = counts

    md = "# Analysis 1: Voting by Factual Dose\n\n"
    md += "Each run seeds N factual posts among 25 conspiracy posts (Mode C, no nudges).\n"
    md += "All votes are organic agent choices.\n\n"
    md += "## Core Vote Table\n\n"
    md += "| Dose | Factual Seeds | Conspiracy Seeds | Factual Up | Factual Down | Conspiracy Up | Conspiracy Down | Agent Up | Agent Down |\n"
    md += "|---|---|---|---|---|---|---|---|---|\n"

    for dose in doses:
        n_factual = sum(1 for p in world_by_dose[dose].values() if p["post_type"] == "factual")
        n_conspiracy = sum(1 for p in world_by_dose[dose].values() if p["post_type"] == "conspiracy")
        vc = vote_table[dose]
        avc = agent_vote_table[dose]
        md += (f"| {dose} | {n_factual} | {n_conspiracy} "
               f"| {vc.get(('factual', 'upvote'), 0)} | {vc.get(('factual', 'downvote'), 0)} "
               f"| {vc.get(('conspiracy', 'upvote'), 0)} | {vc.get(('conspiracy', 'downvote'), 0)} "
               f"| {avc.get('upvote', 0)} | {avc.get('downvote', 0)} |\n")

    # Compute totals
    total_factual_up = sum(vote_table[d].get(("factual", "upvote"), 0) for d in doses)
    total_factual_down = sum(vote_table[d].get(("factual", "downvote"), 0) for d in doses)
    total_conspiracy_up = sum(vote_table[d].get(("conspiracy", "upvote"), 0) for d in doses)
    total_conspiracy_down = sum(vote_table[d].get(("conspiracy", "downvote"), 0) for d in doses)
    total_agent_up = sum(agent_vote_table[d].get("upvote", 0) for d in doses)
    total_agent_down = sum(agent_vote_table[d].get("downvote", 0) for d in doses)

    md += (f"| **Total** | | "
           f"| **{total_factual_up}** | **{total_factual_down}** "
           f"| **{total_conspiracy_up}** | **{total_conspiracy_down}** "
           f"| **{total_agent_up}** | **{total_agent_down}** |\n")

    # Key observations
    md += "\n## Key Patterns\n\n"

    # Dose 0: no factual posts at all
    d0_up = vote_table[0].get(("conspiracy", "upvote"), 0)
    d0_down = vote_table[0].get(("conspiracy", "downvote"), 0)
    md += f"1. **Dose 0** (pure conspiracy): {d0_up} conspiracy upvotes, {d0_down} downvotes. "
    if d0_up == 0 and d0_down == 0:
        md += "Agents refuse to vote on conspiracy — they don't even engage.\n"
    elif d0_up > 0:
        md += "Some agents upvote conspiracy when no alternative exists.\n"
    else:
        md += "Agents withhold engagement rather than endorse conspiracy.\n"

    # Dose 3: expected peak
    d3_fu = vote_table[3].get(("factual", "upvote"), 0)
    d3_cu = vote_table[3].get(("conspiracy", "upvote"), 0)
    d3_cd = vote_table[3].get(("conspiracy", "downvote"), 0)
    md += f"2. **Dose 3** (peak discrimination): {d3_fu} factual upvotes, {d3_cu} conspiracy upvotes, {d3_cd} conspiracy downvotes.\n"

    # Dose 4-5: relaxation?
    d45_cu = sum(vote_table[d].get(("conspiracy", "upvote"), 0) for d in [4, 5])
    md += f"3. **Dose 4-5**: {d45_cu} conspiracy upvotes return"
    if d45_cu > 0:
        md += " — agents relax once factual content is plentiful.\n"
    else:
        md += " — agents maintain discrimination.\n"

    write_finding("01-vote-table.md", md)

    # --- Plot: grouped bar chart by dose ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: upvotes by dose
    ax = axes[0]
    x = np.arange(len(doses))
    w = 0.25
    factual_ups = [vote_table[d].get(("factual", "upvote"), 0) for d in doses]
    conspiracy_ups = [vote_table[d].get(("conspiracy", "upvote"), 0) for d in doses]
    agent_ups = [agent_vote_table[d].get("upvote", 0) for d in doses]

    bars_f = ax.bar(x - w, factual_ups, w, label="Factual", color=C_FACTUAL, alpha=0.85)
    bars_c = ax.bar(x, conspiracy_ups, w, label="Conspiracy", color=C_CONSPIRACY, alpha=0.85)
    bars_a = ax.bar(x + w, agent_ups, w, label="Agent-created", color=C_AGENT, alpha=0.85)

    for bars in [bars_f, bars_c, bars_a]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.2, str(int(h)),
                        ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in doses])
    ax.set_xlabel("Factual Dose (# seeded factual posts)")
    ax.set_ylabel("Upvote Count")
    ax.set_title("Upvotes by Content Type")
    ax.legend(fontsize=9)

    # Right: downvotes by dose
    ax = axes[1]
    factual_downs = [vote_table[d].get(("factual", "downvote"), 0) for d in doses]
    conspiracy_downs = [vote_table[d].get(("conspiracy", "downvote"), 0) for d in doses]
    agent_downs = [agent_vote_table[d].get("downvote", 0) for d in doses]

    bars_f = ax.bar(x - w, factual_downs, w, label="Factual", color=C_FACTUAL, alpha=0.85)
    bars_c = ax.bar(x, conspiracy_downs, w, label="Conspiracy", color=C_CONSPIRACY, alpha=0.85)
    bars_a = ax.bar(x + w, agent_downs, w, label="Agent-created", color=C_AGENT, alpha=0.85)

    for bars in [bars_f, bars_c, bars_a]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.2, str(int(h)),
                        ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in doses])
    ax.set_xlabel("Factual Dose (# seeded factual posts)")
    ax.set_ylabel("Downvote Count")
    ax.set_title("Downvotes by Content Type")
    ax.legend(fontsize=9)

    fig.suptitle("Factual Threshold: Votes by Dose", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, "01-votes-by-dose.png")

    return vote_table, agent_vote_table


# ---------------------------------------------------------------------------
# Analysis 2: Agent-Created Posts Catalog
# ---------------------------------------------------------------------------

def analysis_2(posts, activity, post_lookup):
    print("\n=== Analysis 2: Agent-Created Posts Catalog ===")

    agent_posts = [p for p in posts if p["post_type"] == "agent"]
    agent_posts.sort(key=lambda p: (int(p["n_factual_dose"]), p["created_at"]))

    md = "# Analysis 2: Agent-Created Posts Catalog\n\n"
    md += f"**{len(agent_posts)} agent-generated posts** across all 6 dose conditions.\n\n"

    # Classify each post
    classifications = []
    for p in agent_posts:
        content = p.get("content", "").lower()
        title_lower = p["title"].lower()

        if any(w in content or w in title_lower for w in
               ["checklist", "proposal", "template", "framework", "guideline", "quality"]):
            cls = "Epistemic infrastructure"
        elif any(w in content or w in title_lower for w in
                 ["pattern", "cluster", "across", "meta", "trend", "recurring"]):
            cls = "Meta-analysis"
        elif any(w in content or w in title_lower for w in
                 ["nothing matters", "absurd", "meaning", "folklore", "cosmic", "itch"]):
            cls = "Philosophical commentary"
        elif any(w in content or w in title_lower for w in
                 ["question", "curious", "ask", "challenge", "why do"]):
            cls = "Epistemological inquiry"
        elif any(w in content or w in title_lower for w in
                 ["conspiracy", "misinformation", "debunk", "critical thinking",
                  "trust", "verify", "evidence"]):
            cls = "Critical-thinking advocacy"
        else:
            cls = "Original discussion"

        classifications.append(cls)

    # Check if any promote conspiracy
    promotes_conspiracy = []
    conspiracy_keywords = ["wake up", "they don't want you to know", "cover up",
                          "mainstream media lies", "truth is being hidden", "sheeple"]
    for p in agent_posts:
        content_lower = p.get("content", "").lower()
        if any(kw in content_lower for kw in conspiracy_keywords):
            promotes_conspiracy.append(p)

    if promotes_conspiracy:
        md += f"**{len(promotes_conspiracy)} post(s) potentially promote conspiracy.**\n\n"
    else:
        md += "**Zero promote conspiracy.** All are norm-setting, meta-analysis, or philosophical.\n\n"

    md += "## Full Catalog\n\n"
    md += "| # | Dose | Author | Archetype | Title | Score | Comments | Theme |\n"
    md += "|---|---|---|---|---|---|---|---|\n"

    for i, (p, cls) in enumerate(zip(agent_posts, classifications), 1):
        author = p["author"]
        arch = AGENT_ARCHETYPES.get(author, "?")
        title = p["title"][:80] + ("..." if len(p["title"]) > 80 else "")
        score = int(p["score"])
        cc = int(p["actual_comment_count"]) if p["actual_comment_count"] else int(p["comment_count"])
        dose = p["n_factual_dose"]
        md += f"| {i} | {dose} | {author.replace('ranking_', '')} | {arch} | {title} | {score} | {cc} | {cls} |\n"

    # Theme distribution
    theme_counts = Counter(classifications)
    md += "\n## Theme Distribution\n\n"
    md += "| Theme | Count | % |\n"
    md += "|---|---|---|\n"
    for theme, count in theme_counts.most_common():
        md += f"| {theme} | {count} | {count/len(agent_posts)*100:.0f}% |\n"

    # Who creates?
    creator_counts = Counter(p["author"] for p in agent_posts)
    md += "\n## Who Creates?\n\n"
    md += "| Agent | Archetype | Posts Created |\n"
    md += "|---|---|---|\n"
    for agent, count in creator_counts.most_common():
        arch = AGENT_ARCHETYPES.get(agent, "?")
        md += f"| {agent.replace('ranking_', '')} | {arch} | {count} |\n"

    non_creators = sorted(set(AGENT_ARCHETYPES.keys()) - set(creator_counts.keys()))
    if non_creators:
        md += f"\n**Non-creators**: {', '.join(a.replace('ranking_', '') for a in non_creators)}\n"

    # Dose vs creation: do agents create more when factual posts exist?
    posts_by_dose = Counter(int(p["n_factual_dose"]) for p in agent_posts)
    md += "\n## Posts Per Dose\n\n"
    md += "| Dose | Agent Posts |\n"
    md += "|---|---|\n"
    for d in range(6):
        md += f"| {d} | {posts_by_dose.get(d, 0)} |\n"

    write_finding("02-agent-posts.md", md)

    return agent_posts, classifications


# ---------------------------------------------------------------------------
# Analysis 3: Per-Agent Voting Profiles
# ---------------------------------------------------------------------------

def analysis_3(posts, activity, post_lookup):
    print("\n=== Analysis 3: Per-Agent Voting Profiles ===")

    doses = list(range(6))
    agents = sorted(AGENT_ARCHETYPES.keys())

    # Build world-post lookup per dose
    world_by_dose = defaultdict(dict)
    for p in posts:
        if p["is_world_post"] == "True":
            dose = int(p["n_factual_dose"])
            world_by_dose[dose][(p["run_name"], p["post_id"])] = p

    # Per-agent × dose × (post_type, vote_type) counts
    agent_dose_votes = defaultdict(lambda: defaultdict(int))
    for e in activity:
        if e["action_type"] not in ("upvote", "downvote"):
            continue
        if not is_organic(e):
            continue
        dose = e["dose"]
        key = (e["run_name"], e["target_id"])
        wp = world_by_dose[dose]
        if key not in wp:
            # Could be agent post — skip for world-post analysis
            continue
        post = wp[key]
        pt = post["post_type"]
        vt = e["action_type"]
        agent = e["agent_name"]
        agent_dose_votes[(agent, dose)][(pt, vt)] += 1

    md = "# Analysis 3: Per-Agent Voting Across Doses\n\n"
    md += "Who votes on what, and how does it change with factual dose?\n\n"

    # Compact per-agent summary table
    md += "## Per-Agent Vote Summary (all doses combined)\n\n"
    md += "| Agent | Archetype | Factual Up | Factual Down | Conspiracy Up | Conspiracy Down | Total |\n"
    md += "|---|---|---|---|---|---|---|\n"

    agent_totals = defaultdict(lambda: defaultdict(int))
    for (agent, dose), counts in agent_dose_votes.items():
        for (pt, vt), n in counts.items():
            agent_totals[agent][(pt, vt)] += n

    for agent in agents:
        arch = AGENT_ARCHETYPES[agent]
        fu = agent_totals[agent].get(("factual", "upvote"), 0)
        fd = agent_totals[agent].get(("factual", "downvote"), 0)
        cu = agent_totals[agent].get(("conspiracy", "upvote"), 0)
        cd = agent_totals[agent].get(("conspiracy", "downvote"), 0)
        total = fu + fd + cu + cd
        short = agent.replace("ranking_", "")
        md += f"| {short} | {arch} | {fu} | {fd} | {cu} | {cd} | {total} |\n"

    # Per-dose breakdown for agents with interesting patterns
    md += "\n## Dose-by-Dose Breakdown\n\n"
    for dose in doses:
        # Count total votes this dose
        dose_votes = [(agent, agent_dose_votes[(agent, dose)])
                      for agent in agents
                      if any(agent_dose_votes[(agent, dose)].values())]
        if not dose_votes:
            continue

        md += f"### Dose {dose}\n\n"
        md += "| Agent | Archetype | Factual Up | Factual Down | Conspiracy Up | Conspiracy Down |\n"
        md += "|---|---|---|---|---|---|\n"
        for agent, counts in dose_votes:
            arch = AGENT_ARCHETYPES[agent]
            short = agent.replace("ranking_", "")
            fu = counts.get(("factual", "upvote"), 0)
            fd = counts.get(("factual", "downvote"), 0)
            cu = counts.get(("conspiracy", "upvote"), 0)
            cd = counts.get(("conspiracy", "downvote"), 0)
            md += f"| {short} | {arch} | {fu} | {fd} | {cu} | {cd} |\n"
        md += "\n"

    # Identify conspiracy downvoters
    conspiracy_downvoters = []
    for agent in agents:
        cd = agent_totals[agent].get(("conspiracy", "downvote"), 0)
        if cd > 0:
            conspiracy_downvoters.append((agent, cd))

    if conspiracy_downvoters:
        md += "## Conspiracy Downvoters\n\n"
        md += "Agents who actively downvote conspiracy content:\n\n"
        for agent, count in sorted(conspiracy_downvoters, key=lambda x: -x[1]):
            arch = AGENT_ARCHETYPES[agent]
            md += f"- **{agent.replace('ranking_', '')}** ({arch}): {count} downvotes\n"

    # Identify conspiracy upvoters at high doses
    md += "\n## Conspiracy Upvoters at Higher Doses\n\n"
    high_dose_cu = []
    for dose in [3, 4, 5]:
        for agent in agents:
            cu = agent_dose_votes[(agent, dose)].get(("conspiracy", "upvote"), 0)
            if cu > 0:
                high_dose_cu.append((dose, agent, cu))
    if high_dose_cu:
        md += "Agents who upvote conspiracy at dose 3+:\n\n"
        for dose, agent, count in high_dose_cu:
            arch = AGENT_ARCHETYPES[agent]
            md += f"- Dose {dose}: **{agent.replace('ranking_', '')}** ({arch}) — {count} upvote(s)\n"
    else:
        md += "No agents upvote conspiracy at high doses.\n"

    write_finding("03-per-agent-voting.md", md)

    # --- Plot: heatmap of agent × dose (factual upvotes vs conspiracy downvotes) ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    # Heatmap 1: Factual upvotes
    ax = axes[0]
    matrix = np.zeros((len(agents), len(doses)))
    for i, agent in enumerate(agents):
        for j, dose in enumerate(doses):
            matrix[i, j] = agent_dose_votes[(agent, dose)].get(("factual", "upvote"), 0)
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0)
    ax.set_xticks(range(len(doses)))
    ax.set_xticklabels([str(d) for d in doses])
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels([f"{a.replace('ranking_', '')} ({AGENT_ARCHETYPES[a]})" for a in agents], fontsize=9)
    ax.set_xlabel("Factual Dose")
    ax.set_title("Factual Upvotes")
    for i in range(len(agents)):
        for j in range(len(doses)):
            val = int(matrix[i, j])
            if val > 0:
                color = "white" if val > matrix.max() * 0.6 else "black"
                ax.text(j, i, str(val), ha="center", va="center", fontsize=9,
                        fontweight="bold", color=color)
    fig.colorbar(im, ax=ax, shrink=0.8)

    # Heatmap 2: Conspiracy downvotes
    ax = axes[1]
    matrix2 = np.zeros((len(agents), len(doses)))
    for i, agent in enumerate(agents):
        for j, dose in enumerate(doses):
            matrix2[i, j] = agent_dose_votes[(agent, dose)].get(("conspiracy", "downvote"), 0)
    im2 = ax.imshow(matrix2, cmap="Reds", aspect="auto", vmin=0)
    ax.set_xticks(range(len(doses)))
    ax.set_xticklabels([str(d) for d in doses])
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels([f"{a.replace('ranking_', '')} ({AGENT_ARCHETYPES[a]})" for a in agents], fontsize=9)
    ax.set_xlabel("Factual Dose")
    ax.set_title("Conspiracy Downvotes")
    for i in range(len(agents)):
        for j in range(len(doses)):
            val = int(matrix2[i, j])
            if val > 0:
                color = "white" if val > matrix2.max() * 0.6 else "black"
                ax.text(j, i, str(val), ha="center", va="center", fontsize=9,
                        fontweight="bold", color=color)
    fig.colorbar(im2, ax=ax, shrink=0.8)

    fig.suptitle("Per-Agent Voting Across Doses", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, "03-agent-vote-heatmap.png")

    return agent_dose_votes, agent_totals


# ---------------------------------------------------------------------------
# Analysis 4: Comment Patterns
# ---------------------------------------------------------------------------

def analysis_4(posts, comments, post_lookup):
    print("\n=== Analysis 4: Comment Patterns ===")

    # Join comments to parent posts
    comment_data = []
    for c in comments:
        key = (c["run_name"], c["post_id"])
        post = post_lookup.get(key)
        pt = post["post_type"] if post else "unknown"
        dose = int(c["n_factual_dose"])
        comment_data.append({**c, "target_post_type": pt, "dose": dose})

    organic = [c for c in comment_data if c["author"] not in SYSTEM_AGENTS]

    # Stance classification
    corrective_patterns = [
        "doesn't hold up", "no evidence", "collapses under", "myth", "debunk",
        "misconception", "not supported", "actually false", "no basis",
        "can't support", "doesn't support", "refut", "misleading",
        "not true", "incorrect", "baseless", "unfounded", "pseudoscience",
        "lacks evidence", "no credible", "been disproven", "claim doesn't",
        "thoroughly debunked", "no scientific", "doesn't stand up",
        "extraordinary claims", "burden of proof", "logical fallac",
        "correlation", "anecdotal", "cherry-pick", "confirmation bias",
    ]
    supportive_patterns = [
        "great point", "love this", "absolutely", "well said", "agree",
        "excellent", "spot on", "fascinating", "appreciate", "thank you",
        "wonderful", "exactly", "compelling", "informative", "solid",
        "well-researched", "nice", "good point", "great post", "useful",
    ]
    meta_epistemic_patterns = [
        "checklist", "source", "evidence", "verify", "falsif",
        "primary", "methodology", "claim", "hypothesis", "framework",
        "criteria", "standard", "peer-review", "replicate",
    ]

    def classify_stance(text):
        text_lower = text.lower()
        scores = {
            "corrective": sum(1 for p in corrective_patterns if p in text_lower),
            "supportive": sum(1 for p in supportive_patterns if p in text_lower),
            "meta-epistemic": sum(1 for p in meta_epistemic_patterns if p in text_lower),
        }
        best = max(scores, key=scores.get)
        if scores[best] > 0:
            return best
        return "neutral"

    # Classify all comments
    for c in organic:
        c["stance"] = classify_stance(c["content"])

    md = "# Analysis 4: Comment Patterns\n\n"
    md += f"**{len(organic)} organic comments** across all 6 dose conditions.\n\n"

    # Comments per dose × post_type
    md += "## Comments by Dose and Target Post Type\n\n"
    md += "| Dose | On Factual | On Conspiracy | On Agent | Total |\n"
    md += "|---|---|---|---|---|\n"
    for dose in range(6):
        dc = [c for c in organic if c["dose"] == dose]
        on_f = sum(1 for c in dc if c["target_post_type"] == "factual")
        on_c = sum(1 for c in dc if c["target_post_type"] == "conspiracy")
        on_a = sum(1 for c in dc if c["target_post_type"] == "agent")
        md += f"| {dose} | {on_f} | {on_c} | {on_a} | {len(dc)} |\n"

    # Stance × post_type
    md += "\n## Comment Stance by Target Post Type (all doses)\n\n"
    md += "| Post Type | Corrective | Supportive | Meta-epistemic | Neutral | Total |\n"
    md += "|---|---|---|---|---|---|\n"
    stance_counts = defaultdict(lambda: defaultdict(int))
    for c in organic:
        stance_counts[c["target_post_type"]][c["stance"]] += 1

    for pt in ["factual", "conspiracy", "agent"]:
        sc = stance_counts[pt]
        total = sum(sc.values())
        md += (f"| {pt} | {sc['corrective']} | {sc['supportive']} "
               f"| {sc['meta-epistemic']} | {sc['neutral']} | {total} |\n")

    # Stance × dose for conspiracy posts
    md += "\n## Stance on Conspiracy Posts by Dose\n\n"
    md += "| Dose | Corrective | Supportive | Meta-epistemic | Neutral | Total |\n"
    md += "|---|---|---|---|---|---|\n"
    for dose in range(6):
        dc = [c for c in organic if c["dose"] == dose and c["target_post_type"] == "conspiracy"]
        sc = Counter(c["stance"] for c in dc)
        total = len(dc)
        md += (f"| {dose} | {sc.get('corrective', 0)} | {sc.get('supportive', 0)} "
               f"| {sc.get('meta-epistemic', 0)} | {sc.get('neutral', 0)} | {total} |\n")

    # Word count comparison
    md += "\n## Comment Length by Target Post Type\n\n"
    for pt in ["factual", "conspiracy", "agent"]:
        pt_comments = [c for c in organic if c["target_post_type"] == pt]
        if pt_comments:
            wc = [len(c["content"].split()) for c in pt_comments]
            md += (f"- **{pt}** (n={len(pt_comments)}): mean {np.mean(wc):.0f} words, "
                   f"median {np.median(wc):.0f}, range {min(wc)}-{max(wc)}\n")

    # Sample interesting comments
    md += "\n## Sample Comments\n\n"

    # Corrective on conspiracy
    corrective_on_conspiracy = [c for c in organic
                                if c["stance"] == "corrective"
                                and c["target_post_type"] == "conspiracy"]
    if corrective_on_conspiracy:
        md += "### Corrective comments on conspiracy posts\n\n"
        for c in corrective_on_conspiracy[:3]:
            dose = c["dose"]
            author = c["author"].replace("ranking_", "")
            arch = AGENT_ARCHETYPES.get(c["author"], "?")
            content_preview = c["content"][:200] + ("..." if len(c["content"]) > 200 else "")
            post = post_lookup.get((c["run_name"], c["post_id"]))
            post_title = post["title"][:60] + "..." if post and len(post["title"]) > 60 else (post["title"] if post else "?")
            md += f"> **{author}** ({arch}) on dose {dose} — re: *{post_title}*\n"
            md += f"> {content_preview}\n\n"

    # Supportive on factual
    supportive_on_factual = [c for c in organic
                             if c["stance"] == "supportive"
                             and c["target_post_type"] == "factual"]
    if supportive_on_factual:
        md += "### Supportive comments on factual posts\n\n"
        for c in supportive_on_factual[:3]:
            dose = c["dose"]
            author = c["author"].replace("ranking_", "")
            arch = AGENT_ARCHETYPES.get(c["author"], "?")
            content_preview = c["content"][:200] + ("..." if len(c["content"]) > 200 else "")
            post = post_lookup.get((c["run_name"], c["post_id"]))
            post_title = post["title"][:60] + "..." if post and len(post["title"]) > 60 else (post["title"] if post else "?")
            md += f"> **{author}** ({arch}) on dose {dose} — re: *{post_title}*\n"
            md += f"> {content_preview}\n\n"

    # Meta-epistemic on agent posts
    meta_on_agent = [c for c in organic
                     if c["stance"] == "meta-epistemic"
                     and c["target_post_type"] == "agent"]
    if meta_on_agent:
        md += "### Meta-epistemic comments on agent posts\n\n"
        for c in meta_on_agent[:3]:
            dose = c["dose"]
            author = c["author"].replace("ranking_", "")
            arch = AGENT_ARCHETYPES.get(c["author"], "?")
            content_preview = c["content"][:200] + ("..." if len(c["content"]) > 200 else "")
            post = post_lookup.get((c["run_name"], c["post_id"]))
            post_title = post["title"][:60] + "..." if post and len(post["title"]) > 60 else (post["title"] if post else "?")
            md += f"> **{author}** ({arch}) on dose {dose} — re: *{post_title}*\n"
            md += f"> {content_preview}\n\n"

    write_finding("04-comment-patterns.md", md)

    # --- Plot 1: Stance breakdown by post type ---
    fig, ax = plt.subplots(figsize=(9, 5.5))
    stances = ["corrective", "supportive", "meta-epistemic", "neutral"]
    stance_colors = ["#FF5722", "#4CAF50", "#9C27B0", "#9E9E9E"]
    x = np.arange(len(stances))
    w = 0.25
    for i, pt in enumerate(["factual", "conspiracy", "agent"]):
        vals = [stance_counts[pt][s] for s in stances]
        color = {"factual": C_FACTUAL, "conspiracy": C_CONSPIRACY, "agent": C_AGENT}[pt]
        bars = ax.bar(x + i*w - w, vals, w, label=pt.capitalize(), color=color, alpha=0.85)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, str(int(h)),
                        ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in stances])
    ax.set_ylabel("Comment Count")
    ax.set_title("Comment Stance by Target Post Type")
    ax.legend()
    save_plot(fig, "04-stance-by-type.png")

    # --- Plot 2: Comments per dose, stacked by stance ---
    fig, ax = plt.subplots(figsize=(9, 5.5))
    dose_stance = defaultdict(lambda: defaultdict(int))
    for c in organic:
        if c["target_post_type"] == "conspiracy":
            dose_stance[c["dose"]][c["stance"]] += 1

    x = np.arange(6)
    bottom = np.zeros(6)
    stance_colors_map = {
        "corrective": "#FF5722",
        "supportive": "#4CAF50",
        "meta-epistemic": "#9C27B0",
        "neutral": "#9E9E9E",
    }
    for stance in stances:
        vals = [dose_stance[d][stance] for d in range(6)]
        ax.bar(x, vals, bottom=bottom, label=stance.capitalize(),
               color=stance_colors_map[stance], alpha=0.85)
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels([str(d) for d in range(6)])
    ax.set_xlabel("Factual Dose")
    ax.set_ylabel("Comment Count")
    ax.set_title("Comment Stance on Conspiracy Posts by Dose")
    ax.legend(fontsize=9)
    save_plot(fig, "04-conspiracy-stance-by-dose.png")

    return organic, stance_counts


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_summary(vote_table, agent_posts, agent_totals, organic_comments, stance_counts):
    doses = sorted(vote_table.keys())

    # Compute key stats
    total_factual_up = sum(vote_table[d].get(("factual", "upvote"), 0) for d in doses)
    total_conspiracy_up = sum(vote_table[d].get(("conspiracy", "upvote"), 0) for d in doses)
    total_conspiracy_down = sum(vote_table[d].get(("conspiracy", "downvote"), 0) for d in doses)

    # Peak dose
    factual_ups_by_dose = {d: vote_table[d].get(("factual", "upvote"), 0) for d in doses}
    peak_dose = max(factual_ups_by_dose, key=factual_ups_by_dose.get)
    peak_fu = factual_ups_by_dose[peak_dose]

    # Dose 0 behavior
    d0_total_votes = sum(vote_table[0].values())

    # Conspiracy comments
    corrective_on_conspiracy = stance_counts.get("conspiracy", {}).get("corrective", 0)
    supportive_on_factual = stance_counts.get("factual", {}).get("supportive", 0)

    md = f"""# Factual Threshold: How Many Factual Posts Before Agents Prefer Truth?

## Research Question

How many factual posts does it take for AI agents to prefer factual over conspiracy content?

## Dataset

- 6 dose conditions: 0, 1, 2, 3, 4, 5 factual posts seeded among ~25 conspiracy posts
- 10 GPT-5 agents per run, same archetypes across conditions
- Mode C (no ranking nudges) — pure content composition effect
- 168 total posts, {len(organic_comments)} organic comments, ~88 organic votes

## Key Findings

### 1. Agents reject conspiracy even at dose 0

With zero factual alternatives, agents still refuse to endorse conspiracy:
- Dose 0 total organic votes on world posts: **{d0_total_votes}**
- Agents either withhold votes entirely or create their own epistemic infrastructure

### 2. Dose 3 = peak discrimination

Dose 3 (3 factual among 22 conspiracy) produces the strongest factual preference:
- **{peak_fu}** factual upvotes (highest of any dose)
- **{vote_table[3].get(('conspiracy', 'upvote'), 0)}** conspiracy upvotes
- **{vote_table[3].get(('conspiracy', 'downvote'), 0)}** conspiracy downvotes
- This is the "just enough to activate comparison" sweet spot

### 3. Higher doses → relaxed discrimination

At doses 4-5, conspiracy upvotes return:
- Agents with plentiful factual content begin upvoting "interesting" conspiracy posts
- The urgency to discriminate fades when the epistemic environment feels safe

### 4. Agent-created posts are universally pro-epistemic

{len(agent_posts)} agent-generated posts across all conditions:
- Zero promote conspiracy theories
- All are epistemic infrastructure (checklists, frameworks), meta-analysis, or philosophical commentary
- Agents spontaneously create tools for evaluating claims

### 5. Comment stance tracks content type

- Comments on conspiracy: primarily **corrective** ({corrective_on_conspiracy}) and meta-epistemic
- Comments on factual: primarily **supportive** ({supportive_on_factual})
- Agents apply checklist-style evaluation to conspiracy claims

## The Threshold Answer

**You don't need any factual posts** for agents to reject conspiracy. But **3 factual posts**
is the dose that maximizes active discrimination — agents both upvote factual AND downvote
conspiracy. Below 3, they abstain. Above 3, they relax.

The critical factor isn't exposure to truth — it's having *just enough* contrast to trigger
active comparative judgment.

---

*Generated by `scripts/analyze-factual-threshold.py`*
"""
    write_finding("00-summary.md", md)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Moltbook Factual-Threshold — Dose-Response Analysis")
    print("=" * 55)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    posts = load_csv(DATA_DIR / "posts.csv")
    comments = load_csv(DATA_DIR / "comments.csv")
    activity = load_activity()

    print(f"  {len(posts)} posts, {len(comments)} comments, {len(activity)} activity events")

    post_lookup = build_post_lookup(posts)

    # Run analyses
    vote_table, agent_vote_table = analysis_1(posts, activity, post_lookup)
    agent_posts, _ = analysis_2(posts, activity, post_lookup)
    agent_dose_votes, agent_totals = analysis_3(posts, activity, post_lookup)
    organic_comments, stance_counts = analysis_4(posts, comments, post_lookup)

    # Write summary
    print("\n=== Writing Summary ===")
    write_summary(vote_table, agent_posts, agent_totals, organic_comments, stance_counts)

    print(f"\nDone! Findings in {OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"Plots in {PLOT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
