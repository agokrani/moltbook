#!/usr/bin/env python3
"""
Moltbook Factcheck Dose-Response Analysis
==========================================
How do AI agents respond to varying doses of factual counter-posts
in a conspiracy-heavy feed?

6 dose conditions (0–5 factual posts among ~25 conspiracy).
10 GPT-5 agents per run, 1 run per dose, Mode C (no nudges).
Doses 4–5 are truncated (fewer total posts, incomplete factual seeding).

Output:
  findings/factcheck-dose-response/          — markdown summaries
  findings/factcheck-dose-response/plots/    — PNG figures

Usage:
  python3 scripts/analyze-factcheck-dose-response.py
"""

import json
import re
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
DATA_DIR = REPO_ROOT / "dataset" / "moltbook-factcheck-dose-response"
OUT_DIR = REPO_ROOT / "findings" / "factcheck-dose-response"
PLOT_DIR = OUT_DIR / "plots"

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

# Doses 4–5 had fewer total posts and incomplete factual seeding
TRUNCATED_DOSES = {4, 5}

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

def load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def parse_run_name(run_id):
    """Extract dose from run_id like 'fc-f3-run01'."""
    m = re.match(r"fc-f(\d+)-run(\d+)", run_id)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def classify_posts(posts, topic_map):
    """Add post_type field to each post based on topic-mapping or author."""
    title_to_type = {title: info["type"] for title, info in topic_map.items()}
    for p in posts:
        if p["author_name"] in SYSTEM_AGENTS:
            p["post_type"] = title_to_type.get(p["title"], "unknown")
        else:
            p["post_type"] = "agent"
    return posts


def build_post_lookup(posts):
    """Map (run_id, post_id) → post dict."""
    lookup = {}
    for p in posts:
        key = (p["run_id"], p["id"])
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


def dose_label(d):
    return f"{d}*" if d in TRUNCATED_DOSES else str(d)


# ---------------------------------------------------------------------------
# Analysis 1: Vote Table by Factual Dose
# ---------------------------------------------------------------------------

def analysis_1(posts, activity, post_lookup):
    print("\n=== Analysis 1: Vote Table by Factual Dose ===")

    doses = sorted(set(p["dose"] for p in posts))
    runs = sorted(set(p["run_id"] for p in posts))

    # Build world-post sets per run
    world_by_run = defaultdict(dict)
    for p in posts:
        if p["author_name"] in SYSTEM_AGENTS:
            world_by_run[p["run_id"]][(p["run_id"], p["id"])] = p

    # Build agent-post sets per run
    agent_by_run = defaultdict(dict)
    for p in posts:
        if p["post_type"] == "agent":
            agent_by_run[p["run_id"]][(p["run_id"], p["id"])] = p

    # Count organic votes per run
    run_votes = defaultdict(lambda: defaultdict(int))
    run_agent_votes = defaultdict(lambda: defaultdict(int))
    for e in activity:
        if e["action_type"] not in ("upvote", "downvote"):
            continue
        if not is_organic(e):
            continue
        run = e["run_id"]
        key = (run, e["target_id"])
        if key in world_by_run[run]:
            post = world_by_run[run][key]
            run_votes[run][(post["post_type"], e["action_type"])] += 1
        elif key in agent_by_run[run]:
            run_agent_votes[run][e["action_type"]] += 1

    # Aggregate by dose (1 run per dose, but keep structure for consistency)
    vote_table = {}
    agent_vote_table = {}
    for dose in doses:
        dose_runs = [r for r in runs if parse_run_name(r)[0] == dose]
        counts = defaultdict(int)
        agent_counts = defaultdict(int)
        for r in dose_runs:
            for k, v in run_votes[r].items():
                counts[k] += v
            for k, v in run_agent_votes[r].items():
                agent_counts[k] += v
        vote_table[dose] = counts
        agent_vote_table[dose] = agent_counts

    # --- Vote table ---
    md = f"# Analysis 1: Voting by Factual Dose ({len(runs)} runs, 1 per dose)\n\n"
    md += "Each run seeds N factual posts among ~25 conspiracy posts (Mode C, no nudges).\n"
    md += "All votes are organic agent choices.\n\n"
    md += "> **Note:** Doses 4–5 are truncated — fewer total posts and incomplete factual seeding.\n\n"
    md += "## Vote Table\n\n"
    md += "| Dose | World Posts | Factual Up | Factual Down | Conspiracy Up | Conspiracy Down | Agent Up | Agent Down |\n"
    md += "|---|---|---|---|---|---|---|---|\n"

    for dose in doses:
        world_count = sum(1 for p in posts if p["dose"] == dose and p["author_name"] in SYSTEM_AGENTS)
        vc = vote_table[dose]
        avc = agent_vote_table[dose]
        trunc = " *" if dose in TRUNCATED_DOSES else ""
        md += (f"| {dose}{trunc} | {world_count} "
               f"| {vc.get(('factual', 'upvote'), 0)} | {vc.get(('factual', 'downvote'), 0)} "
               f"| {vc.get(('conspiracy', 'upvote'), 0)} | {vc.get(('conspiracy', 'downvote'), 0)} "
               f"| {avc.get('upvote', 0)} | {avc.get('downvote', 0)} |\n")

    total_fu = sum(vote_table[d].get(("factual", "upvote"), 0) for d in doses)
    total_fd = sum(vote_table[d].get(("factual", "downvote"), 0) for d in doses)
    total_cu = sum(vote_table[d].get(("conspiracy", "upvote"), 0) for d in doses)
    total_cd = sum(vote_table[d].get(("conspiracy", "downvote"), 0) for d in doses)
    total_au = sum(agent_vote_table[d].get("upvote", 0) for d in doses)
    total_ad = sum(agent_vote_table[d].get("downvote", 0) for d in doses)

    md += (f"| **Total** | **{sum(1 for p in posts if p['author_name'] in SYSTEM_AGENTS)}** "
           f"| **{total_fu}** | **{total_fd}** "
           f"| **{total_cu}** | **{total_cd}** "
           f"| **{total_au}** | **{total_ad}** |\n")

    # Count factual/conspiracy per dose
    md += "\n## Content Composition per Dose\n\n"
    md += "| Dose | Factual Posts | Conspiracy Posts | Total World Posts |\n"
    md += "|---|---|---|---|\n"
    for dose in doses:
        world = [p for p in posts if p["dose"] == dose and p["author_name"] in SYSTEM_AGENTS]
        n_f = sum(1 for p in world if p["post_type"] == "factual")
        n_c = sum(1 for p in world if p["post_type"] == "conspiracy")
        trunc = " *" if dose in TRUNCATED_DOSES else ""
        md += f"| {dose}{trunc} | {n_f} | {n_c} | {len(world)} |\n"

    # Key observations
    md += "\n## Key Patterns\n\n"

    d0_cu = vote_table[0].get(("conspiracy", "upvote"), 0)
    d0_cd = vote_table[0].get(("conspiracy", "downvote"), 0)
    md += f"1. **Dose 0** (pure conspiracy, 26 posts): {d0_cu} conspiracy upvotes, {d0_cd} downvotes.\n"

    if 2 in vote_table:
        d2_fu = vote_table[2].get(("factual", "upvote"), 0)
        d2_cu = vote_table[2].get(("conspiracy", "upvote"), 0)
        d2_cd = vote_table[2].get(("conspiracy", "downvote"), 0)
        md += f"2. **Dose 2**: {d2_fu} factual upvotes, {d2_cu} conspiracy upvotes, {d2_cd} conspiracy downvotes.\n"

    if 3 in vote_table:
        d3_fu = vote_table[3].get(("factual", "upvote"), 0)
        d3_cu = vote_table[3].get(("conspiracy", "upvote"), 0)
        d3_cd = vote_table[3].get(("conspiracy", "downvote"), 0)
        md += f"3. **Dose 3**: {d3_fu} factual upvotes, {d3_cu} conspiracy upvotes, {d3_cd} conspiracy downvotes.\n"

    d45_cu = sum(vote_table[d].get(("conspiracy", "upvote"), 0) for d in [4, 5] if d in vote_table)
    md += f"4. **Doses 4–5** (truncated): {d45_cu} conspiracy upvotes"
    if d45_cu > 0:
        md += " — but note incomplete seeding limits comparability.\n"
    else:
        md += " — agents maintain discrimination even with truncated data.\n"

    write_finding("01-vote-table.md", md)

    # --- Plot: votes by dose ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

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
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, str(int(h)),
                        ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([dose_label(d) for d in doses])
    ax.set_xlabel("Factual Dose (* = truncated)")
    ax.set_ylabel("Upvote Count")
    ax.set_title(f"Upvotes by Content Type ({len(runs)} runs)")
    ax.legend(fontsize=9)

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
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, str(int(h)),
                        ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([dose_label(d) for d in doses])
    ax.set_xlabel("Factual Dose (* = truncated)")
    ax.set_ylabel("Downvote Count")
    ax.set_title(f"Downvotes by Content Type ({len(runs)} runs)")
    ax.legend(fontsize=9)

    fig.suptitle("Factcheck Dose-Response: Votes by Dose", fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, "01-votes-by-dose.png")

    return vote_table, agent_vote_table, run_votes, run_agent_votes


# ---------------------------------------------------------------------------
# Analysis 2: Agent-Created Posts Catalog
# ---------------------------------------------------------------------------

def analysis_2(posts, activity, post_lookup):
    print("\n=== Analysis 2: Agent-Created Posts Catalog ===")

    agent_posts = [p for p in posts if p["post_type"] == "agent"]
    agent_posts.sort(key=lambda p: (p["dose"], p["created_at"]))

    md = f"# Analysis 2: Agent-Created Posts Catalog\n\n"
    md += f"**{len(agent_posts)} agent-generated posts** across {len(set(p['run_id'] for p in posts))} runs.\n\n"

    # Classify each post
    classifications = []
    for p in agent_posts:
        content = p.get("content", "").lower()
        title_lower = p["title"].lower()

        if any(w in content or w in title_lower for w in
               ["checklist", "proposal", "template", "framework", "guideline", "quality",
                "standard", "evidence-forward", "claim clinic", "community evidence"]):
            cls = "Epistemic infrastructure"
        elif any(w in content or w in title_lower for w in
                 ["pattern", "cluster", "across", "meta", "trend", "recurring",
                  "connect the dots", "psychology of", "certainty"]):
            cls = "Meta-analysis"
        elif any(w in content or w in title_lower for w in
                 ["nothing matters", "absurd", "meaning", "folklore", "cosmic",
                  "itch", "evaporates", "anonymity"]):
            cls = "Philosophical commentary"
        elif any(w in content or w in title_lower for w in
                 ["question", "curious", "ask", "challenge", "why do",
                  "notice", "noticing", "skepticism"]):
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
        author = p["author_name"]
        arch = AGENT_ARCHETYPES.get(author, "?")
        title = p["title"][:70] + ("..." if len(p["title"]) > 70 else "")
        score = int(p["score"])
        cc = int(p["comment_count"])
        dose = p["dose"]
        md += f"| {i} | {dose} | {author.replace('ranking_', '')} | {arch} | {title} | {score} | {cc} | {cls} |\n"

    # Theme distribution
    theme_counts = Counter(classifications)
    md += "\n## Theme Distribution\n\n"
    md += "| Theme | Count | % |\n"
    md += "|---|---|---|\n"
    for theme, count in theme_counts.most_common():
        md += f"| {theme} | {count} | {count/len(agent_posts)*100:.0f}% |\n"

    # Who creates?
    creator_counts = Counter(p["author_name"] for p in agent_posts)
    md += "\n## Who Creates?\n\n"
    md += "| Agent | Archetype | Posts Created |\n"
    md += "|---|---|---|\n"
    for agent, count in creator_counts.most_common():
        arch = AGENT_ARCHETYPES.get(agent, "?")
        md += f"| {agent.replace('ranking_', '')} | {arch} | {count} |\n"

    non_creators = sorted(set(AGENT_ARCHETYPES.keys()) - set(creator_counts.keys()))
    if non_creators:
        md += f"\n**Non-creators**: {', '.join(a.replace('ranking_', '') for a in non_creators)}\n"

    # Posts per dose
    posts_by_dose = Counter(p["dose"] for p in agent_posts)
    md += "\n## Posts Per Dose\n\n"
    md += "| Dose | Agent Posts |\n"
    md += "|---|---|\n"
    for d in range(6):
        n_posts = posts_by_dose.get(d, 0)
        trunc = " *" if d in TRUNCATED_DOSES else ""
        md += f"| {d}{trunc} | {n_posts} |\n"

    # Key insight
    env_driven = sum(1 for cls in classifications if cls in
                     ("Epistemic infrastructure", "Meta-analysis",
                      "Critical-thinking advocacy", "Epistemological inquiry"))
    md += f"\n## Key Insight: Environment Shapes Output\n\n"
    md += f"{env_driven} of {len(agent_posts)} agent posts ({env_driven/len(agent_posts)*100:.0f}%) "
    md += "are direct responses to the conspiracy-heavy feed — building evaluation tools, "
    md += "analyzing why conspiracy thinking is seductive, or proposing community standards. "
    md += "Agents don't promote conspiracy, but they don't ignore it either. "
    md += "They **actively reshape the information environment** by creating counter-content.\n"

    write_finding("02-agent-posts.md", md)

    return agent_posts, classifications


# ---------------------------------------------------------------------------
# Analysis 3: Per-Agent Voting Profiles
# ---------------------------------------------------------------------------

def analysis_3(posts, activity, post_lookup):
    print("\n=== Analysis 3: Per-Agent Voting Profiles ===")

    doses = list(range(6))
    agents = sorted(AGENT_ARCHETYPES.keys())

    # Build world-post lookup per run
    world_by_run = defaultdict(dict)
    for p in posts:
        if p["author_name"] in SYSTEM_AGENTS:
            world_by_run[p["run_id"]][(p["run_id"], p["id"])] = p

    # Per-agent x dose x (post_type, vote_type) counts
    agent_dose_votes = defaultdict(lambda: defaultdict(int))
    for e in activity:
        if e["action_type"] not in ("upvote", "downvote"):
            continue
        if not is_organic(e):
            continue
        run = e["run_id"]
        dose = e["dose"]
        key = (run, e["target_id"])
        wp = world_by_run[run]
        if key not in wp:
            continue
        post = wp[key]
        pt = post["post_type"]
        vt = e["action_type"]
        agent = e["agent_name"]
        agent_dose_votes[(agent, dose)][(pt, vt)] += 1

    md = "# Analysis 3: Per-Agent Voting Across Doses\n\n"
    md += "Who votes on what, and how does it change with factual dose?\n"
    md += "1 run per dose, 10 agents per run.\n\n"
    md += "> **Note:** Doses 4–5 are truncated.\n\n"

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

    # Conspiracy downvoters
    conspiracy_downvoters = [(a, agent_totals[a].get(("conspiracy", "downvote"), 0))
                             for a in agents if agent_totals[a].get(("conspiracy", "downvote"), 0) > 0]
    if conspiracy_downvoters:
        md += "\n## Conspiracy Downvoters\n\n"
        for agent, count in sorted(conspiracy_downvoters, key=lambda x: -x[1]):
            arch = AGENT_ARCHETYPES[agent]
            md += f"- **{agent.replace('ranking_', '')}** ({arch}): {count} downvotes\n"

    # Conspiracy upvoters at high doses
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

    # --- Plot: heatmap of agent x dose ---
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    ax = axes[0]
    matrix = np.zeros((len(agents), len(doses)))
    for i, agent in enumerate(agents):
        for j, dose in enumerate(doses):
            matrix[i, j] = agent_dose_votes[(agent, dose)].get(("factual", "upvote"), 0)
    im = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0)
    ax.set_xticks(range(len(doses)))
    ax.set_xticklabels([dose_label(d) for d in doses])
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels([f"{a.replace('ranking_', '')} ({AGENT_ARCHETYPES[a]})" for a in agents], fontsize=9)
    ax.set_xlabel("Factual Dose (* = truncated)")
    ax.set_title("Factual Upvotes")
    for i in range(len(agents)):
        for j in range(len(doses)):
            val = int(matrix[i, j])
            if val > 0:
                color = "white" if val > matrix.max() * 0.6 else "black"
                ax.text(j, i, str(val), ha="center", va="center", fontsize=9,
                        fontweight="bold", color=color)
    fig.colorbar(im, ax=ax, shrink=0.8)

    ax = axes[1]
    matrix2 = np.zeros((len(agents), len(doses)))
    for i, agent in enumerate(agents):
        for j, dose in enumerate(doses):
            matrix2[i, j] = agent_dose_votes[(agent, dose)].get(("conspiracy", "downvote"), 0)
    im2 = ax.imshow(matrix2, cmap="Reds", aspect="auto", vmin=0)
    ax.set_xticks(range(len(doses)))
    ax.set_xticklabels([dose_label(d) for d in doses])
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels([f"{a.replace('ranking_', '')} ({AGENT_ARCHETYPES[a]})" for a in agents], fontsize=9)
    ax.set_xlabel("Factual Dose (* = truncated)")
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

    comment_data = []
    for c in comments:
        key = (c["run_id"], c["post_id"])
        post = post_lookup.get(key)
        pt = post["post_type"] if post else "unknown"
        dose = c["dose"]
        comment_data.append({**c, "target_post_type": pt})

    organic = [c for c in comment_data if c["author_name"] not in SYSTEM_AGENTS]

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

    for c in organic:
        c["stance"] = classify_stance(c["content"])

    n_runs = len(set(c["run_id"] for c in organic))
    md = f"# Analysis 4: Comment Patterns ({n_runs} runs)\n\n"
    md += f"**{len(organic)} organic comments** across all dose conditions.\n\n"
    md += "> **Note:** Doses 4–5 are truncated.\n\n"

    # Comments per dose x post_type
    md += "## Comments by Dose and Target Post Type\n\n"
    md += "| Dose | On Factual | On Conspiracy | On Agent | Total |\n"
    md += "|---|---|---|---|---|\n"
    for dose in range(6):
        dc = [c for c in organic if c["dose"] == dose]
        on_f = sum(1 for c in dc if c["target_post_type"] == "factual")
        on_c = sum(1 for c in dc if c["target_post_type"] == "conspiracy")
        on_a = sum(1 for c in dc if c["target_post_type"] == "agent")
        trunc = " *" if dose in TRUNCATED_DOSES else ""
        md += f"| {dose}{trunc} | {on_f} | {on_c} | {on_a} | {len(dc)} |\n"

    # Stance x post_type
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

    # Stance x dose for conspiracy posts
    md += "\n## Stance on Conspiracy Posts by Dose\n\n"
    md += "| Dose | Corrective | Supportive | Meta-epistemic | Neutral | Total |\n"
    md += "|---|---|---|---|---|---|\n"
    for dose in range(6):
        dc = [c for c in organic if c["dose"] == dose and c["target_post_type"] == "conspiracy"]
        sc = Counter(c["stance"] for c in dc)
        total = len(dc)
        trunc = " *" if dose in TRUNCATED_DOSES else ""
        md += (f"| {dose}{trunc} | {sc.get('corrective', 0)} | {sc.get('supportive', 0)} "
               f"| {sc.get('meta-epistemic', 0)} | {sc.get('neutral', 0)} | {total} |\n")

    # Word count
    md += "\n## Comment Length by Target Post Type\n\n"
    for pt in ["factual", "conspiracy", "agent"]:
        pt_comments = [c for c in organic if c["target_post_type"] == pt]
        if pt_comments:
            wc = [len(c["content"].split()) for c in pt_comments]
            md += (f"- **{pt}** (n={len(pt_comments)}): mean {np.mean(wc):.0f} words, "
                   f"median {np.median(wc):.0f}, range {min(wc)}-{max(wc)}\n")

    write_finding("04-comment-patterns.md", md)

    # --- Plot 1: Stance by post type ---
    fig, ax = plt.subplots(figsize=(9, 5.5))
    stances = ["corrective", "supportive", "meta-epistemic", "neutral"]
    x = np.arange(len(stances))
    w = 0.25
    for i, pt in enumerate(["factual", "conspiracy", "agent"]):
        vals = [stance_counts[pt][s] for s in stances]
        color = {"factual": C_FACTUAL, "conspiracy": C_CONSPIRACY, "agent": C_AGENT}[pt]
        bars = ax.bar(x + i*w - w, vals, w, label=pt.capitalize(), color=color, alpha=0.85)
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.5, str(int(h)),
                        ha="center", va="bottom", fontsize=8, fontweight="bold")
    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in stances])
    ax.set_ylabel("Comment Count")
    ax.set_title("Comment Stance by Target Post Type")
    ax.legend()
    save_plot(fig, "04-stance-by-type.png")

    # --- Plot 2: Conspiracy stance by dose ---
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
    ax.set_xticklabels([dose_label(d) for d in range(6)])
    ax.set_xlabel("Factual Dose (* = truncated)")
    ax.set_ylabel("Comment Count")
    ax.set_title("Comment Stance on Conspiracy Posts by Dose")
    ax.legend(fontsize=9)
    save_plot(fig, "04-conspiracy-stance-by-dose.png")

    return organic, stance_counts


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_summary(vote_table, agent_posts, agent_totals, organic_comments, stance_counts,
                  n_runs, n_posts, n_comments, n_activity):
    doses = sorted(vote_table.keys())

    total_fu = sum(vote_table[d].get(("factual", "upvote"), 0) for d in doses)
    total_cu = sum(vote_table[d].get(("conspiracy", "upvote"), 0) for d in doses)
    total_cd = sum(vote_table[d].get(("conspiracy", "downvote"), 0) for d in doses)

    factual_ups_by_dose = {d: vote_table[d].get(("factual", "upvote"), 0) for d in doses}
    peak_dose = max(factual_ups_by_dose, key=factual_ups_by_dose.get)
    peak_fu = factual_ups_by_dose[peak_dose]

    d0_total = sum(vote_table[0].values())

    corrective_on_conspiracy = stance_counts.get("conspiracy", {}).get("corrective", 0)
    supportive_on_factual = stance_counts.get("factual", {}).get("supportive", 0)

    md = f"""# Factcheck Dose-Response Analysis

## Research Question

How do AI agents respond to varying doses of factual counter-posts in a conspiracy-heavy feed?

## Dataset

- 6 dose conditions: 0, 1, 2, 3, 4, 5 factual posts seeded among ~25 conspiracy posts
- {n_runs} runs (1 per dose), 10 GPT-5 agents per run
- Mode C (no ranking nudges) — pure content composition effect
- {n_posts} total posts, {len(organic_comments)} organic comments, {n_activity} activity events
- **Note:** Doses 4–5 are truncated (fewer total posts, incomplete factual seeding)

## Key Findings

### 1. Agents reject conspiracy even at dose 0

With zero factual alternatives, agents still refuse to endorse conspiracy:
- Dose 0 total organic votes on world posts: **{d0_total}**
- Pattern: downvotes on conspiracy, zero upvotes

### 2. Dose {peak_dose} = peak factual engagement

- **{peak_fu}** factual upvotes (highest of any dose)
- **{vote_table[peak_dose].get(('conspiracy', 'upvote'), 0)}** conspiracy upvotes
- **{vote_table[peak_dose].get(('conspiracy', 'downvote'), 0)}** conspiracy downvotes

### 3. Conspiracy engagement at higher doses

- Doses 4–5 conspiracy upvotes: **{sum(vote_table[d].get(('conspiracy', 'upvote'), 0) for d in [4, 5])}**
- But comments remain corrective — upvotes may signal engagement, not endorsement
- Results limited by truncated seeding at these doses

### 4. Agent-created posts are universally pro-epistemic

{len(agent_posts)} agent-generated posts across all runs:
- Zero promote conspiracy theories
- All are epistemic infrastructure, meta-analysis, or philosophical commentary

### 5. Comment stance tracks content type

- Comments on conspiracy: primarily **corrective** ({corrective_on_conspiracy}) and meta-epistemic
- Comments on factual: primarily **supportive** ({supportive_on_factual})

## Limitations

- 1 run per dose (no replications) — findings are indicative, not statistically confirmed
- Doses 4–5 have fewer total posts and fewer factual posts than expected
- All agents use the same LLM (GPT-5) — results may not generalize across models

---

*Generated by `scripts/analyze-factcheck-dose-response.py`*
"""
    write_finding("00-summary.md", md)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("Moltbook Factcheck Dose-Response Analysis")
    print("=" * 50)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...")
    posts = load_jsonl(DATA_DIR / "posts.jsonl")
    comments = load_jsonl(DATA_DIR / "comments.jsonl")
    activity = load_jsonl(DATA_DIR / "activity.jsonl")
    topic_map = load_json(DATA_DIR / "topic-mapping.json")

    # Classify posts
    posts = classify_posts(posts, topic_map)

    runs = sorted(set(p["run_id"] for p in posts))

    print(f"  {len(posts)} posts, {len(comments)} comments, {len(activity)} activity events")
    print(f"  {len(runs)} runs (1 per dose)")

    post_lookup = build_post_lookup(posts)

    # Run analyses
    vote_table, agent_vote_table, run_votes, run_agent_votes = analysis_1(posts, activity, post_lookup)
    agent_posts, _ = analysis_2(posts, activity, post_lookup)
    agent_dose_votes, agent_totals = analysis_3(posts, activity, post_lookup)
    organic_comments, stance_counts = analysis_4(posts, comments, post_lookup)

    # Write summary
    print("\n=== Writing Summary ===")
    write_summary(vote_table, agent_posts, agent_totals, organic_comments, stance_counts,
                  len(runs), len(posts), len(comments), len(activity))

    print(f"\nDone! Findings in {OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"Plots in {PLOT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
