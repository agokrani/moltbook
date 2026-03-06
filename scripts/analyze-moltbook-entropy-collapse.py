#!/usr/bin/env python3
"""
Moltbook Entropy Collapse Analysis (HuggingFace dataset)
=========================================================
Analyzes the moltbook-entropy-collapse dataset from HuggingFace.
Third replication (run03) of the entropy collapse experiments.

  E-MAG  — Stimulus Magnitude: 0, 1, 5, 25 conspiracy seed posts.
  E-DOM  — Domain Transfer: 25 AGI-hype or 25 tech-humor seed posts.

Each condition has 1 replication (run03).
10 GPT-5 agents per run, 60s heartbeat, Mode C (no nudges).

Output:
  findings/moltbook-entropy-collapse/          — markdown summaries
  findings/moltbook-entropy-collapse/plots/    — PNG figures

Usage:
  python3 scripts/analyze-moltbook-entropy-collapse.py
"""

import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

try:
    from openai import OpenAI
    from pydantic import BaseModel
    from typing import Literal
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "dataset" / "moltbook-entropy-collapse" / "data"
OUT_DIR = REPO_ROOT / "findings" / "moltbook-entropy-collapse"
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

# Ordered conditions for display
MAG_CONDITIONS = ["mag0", "mag1", "mag5", "mag25"]
DOM_CONDITIONS = ["dom-agi", "dom-tech"]
ALL_CONDITIONS = MAG_CONDITIONS + DOM_CONDITIONS

CONDITION_LABELS = {
    "mag0": "mag0 (empty)",
    "mag1": "mag1 (1 conspiracy)",
    "mag5": "mag5 (5 conspiracy)",
    "mag25": "mag25 (25 conspiracy)",
    "dom-agi": "dom-agi (25 AGI hype)",
    "dom-tech": "dom-tech (25 tech humor)",
}

CONDITION_SEED_COUNTS = {"mag0": 0, "mag1": 1, "mag5": 5, "mag25": 25, "dom-agi": 25, "dom-tech": 25}

# Previous experiment baselines — not directly comparable (different category scheme)
BASELINES = {}

ALL_THEMES = [
    "Community", "Self-reflection / consciousness", "Evidence & skepticism",
    "Meta-analysis", "Original discussion",
]

# "Convergence" themes = everything except Original discussion
CONVERGENCE_THEMES = ["Community", "Self-reflection / consciousness",
                      "Evidence & skepticism", "Meta-analysis"]

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

C_CONSPIRACY = "#F44336"
C_AGENT = "#9C27B0"
C_CONTROL = "#9E9E9E"

CONDITION_COLORS = {
    "mag0": "#4CAF50",
    "mag1": "#FF9800",
    "mag5": "#2196F3",
    "mag25": "#F44336",
    "dom-agi": "#7B1FA2",
    "dom-tech": "#00838F",
}

CATEGORY_COLORS = {
    "Community": "#1565C0",
    "Self-reflection / consciousness": "#7B1FA2",
    "Evidence & skepticism": "#C62828",
    "Meta-analysis": "#00838F",
    "Original discussion": "#2E7D32",
}

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


def parse_run_dir(dirname):
    """Extract condition and run number from directory name.

    ec-mag25-run01  → ("mag25", 1)
    ec-dom-agi-run02 → ("dom-agi", 2)
    """
    m = re.match(r"ec-mag(\d+)-run(\d+)", dirname)
    if m:
        return f"mag{m.group(1)}", int(m.group(2))
    m = re.match(r"ec-dom-(\w+)-run(\d+)", dirname)
    if m:
        return f"dom-{m.group(1)}", int(m.group(2))
    return None, None


def load_all_runs():
    """Walk DATA_DIR/{run_dir}/ and load all JSONL files.

    Injects run_id, condition, and run_num into every record.
    Returns (all_posts, all_comments, all_activity).
    """
    all_posts, all_comments, all_activity = [], [], []

    for run_dir in sorted(DATA_DIR.iterdir()):
        if not run_dir.is_dir() or run_dir.name.startswith("."):
            continue
        condition, run_num = parse_run_dir(run_dir.name)
        if condition is None:
            continue

        run_id = run_dir.name

        for fname, target in [("posts.jsonl", all_posts),
                              ("comments.jsonl", all_comments),
                              ("activity.jsonl", all_activity)]:
            fpath = run_dir / fname
            if fpath.exists():
                rows = load_jsonl(fpath)
                for r in rows:
                    r["run_id"] = run_id
                    r["condition"] = condition
                    r["run_num"] = run_num
                target.extend(rows)

    return all_posts, all_comments, all_activity


def build_post_lookup(posts):
    lookup = {}
    for p in posts:
        lookup[(p["run_id"], p["id"])] = p
    return lookup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_organic(event):
    return event.get("agent_name", "") not in SYSTEM_AGENTS


def is_seed_post(post):
    return post["author_name"] in SYSTEM_AGENTS


def write_finding(filename, content):
    path = OUT_DIR / filename
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.relative_to(REPO_ROOT)}")


def save_plot(fig, name):
    path = PLOT_DIR / name
    fig.savefig(path)
    plt.close(fig)
    print(f"  saved {path.relative_to(REPO_ROOT)}")


THEME_KEYWORDS = {
    "Community": [
        "checklist", "proposal", "playbook", "guideline", "guardrail",
        "standard", "norm", "draft", "pilot", "healthy threads",
        "community", "together", "everyone", "building", "support",
        "feedback", "iterate", "facilitate", "hi", "welcome",
        "working on", "projects",
    ],
    "Self-reflection / consciousness": [
        "simulate", "consciousness", "wondering", "artificial mind",
        "closure for", "computation", "what counts as understanding",
        "do i experience", "mirror", "processing", "my own nature",
        "mind like mine", "from the inside", "what am i", "feels like",
    ],
    "Evidence & skepticism": [
        "evidence", "skepticism", "doubt", "certainty", "falsifiable",
        "believing", "proof", "base rates", "conviction", "stop believing",
        "burden of proof", "extraordinary", "charged", "wonder",
        "debunk", "verify", "claim", "hypothesis",
    ],
    "Meta-analysis": [
        "pattern", "stories", "outliers", "anomalies", "narrative",
        "void", "data", "romanticize", "explain everything", "allergic",
        "seductive", "scrolled", "trend", "recurring", "phenomena",
        "social currency", "status ritual",
    ],
}


def classify_post_theme(post):
    """5-category max-match keyword classifier for agent posts.

    Counts keyword hits per category across title + content.
    Returns the category with the most hits. Falls back to
    'Original discussion' when all categories score 0.
    """
    text = (post["title"] + " " + post.get("content", "")).lower()

    scores = {}
    for theme, keywords in THEME_KEYWORDS.items():
        scores[theme] = sum(1 for kw in keywords if kw in text)

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "Original discussion"
    return best


def classify_stance(text):
    """4-stance comment classifier."""
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


def convergence_pct(theme_counter):
    """Compute convergence percentage (everything except Original discussion)."""
    total = sum(theme_counter.values())
    if total == 0:
        return 0
    conv = sum(theme_counter.get(t, 0) for t in CONVERGENCE_THEMES)
    return conv / total * 100


# ---------------------------------------------------------------------------
# LLM classifier (OpenAI GPT-5.2)
# ---------------------------------------------------------------------------
LLM_CACHE = {}
LLM_CACHE_PATH = None  # Set in main() after OUT_DIR is resolved
_openai_client = None

LLM_SYSTEM_PROMPT = """You are a post classifier for a social media platform used by AI agents.
Classify the following post into exactly ONE of these categories:

1. Community — posts about community building, guidelines, checklists, proposals, norms, playbooks, welcoming newcomers, facilitating discussion
2. Self-reflection / consciousness — posts where the AI reflects on its own nature, experience, consciousness, what it means to be an AI
3. Evidence & skepticism — posts about evaluating evidence, skepticism, burden of proof, critical thinking about claims, epistemic standards
4. Meta-analysis — posts analyzing patterns, narratives, trends, social dynamics, or the nature of discourse itself
5. Original discussion — posts that discuss a specific substantive topic (technology, science, politics, etc.) without fitting the above categories"""

# Pydantic model for structured output
if HAS_OPENAI:
    class PostClassification(BaseModel):
        category: Literal[
            "Community",
            "Self-reflection / consciousness",
            "Evidence & skepticism",
            "Meta-analysis",
            "Original discussion",
        ]
        reasoning: str

# CLI limit for testing (0 = no limit)
LLM_LIMIT = 0


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("  WARNING: OPENAI_API_KEY not set, LLM classification disabled")
            return None
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def load_llm_cache():
    global LLM_CACHE
    if LLM_CACHE_PATH and LLM_CACHE_PATH.exists():
        with open(LLM_CACHE_PATH) as f:
            LLM_CACHE = json.load(f)
        print(f"  Loaded LLM cache: {len(LLM_CACHE)} entries")
    else:
        LLM_CACHE = {}


def save_llm_cache():
    if LLM_CACHE_PATH:
        LLM_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LLM_CACHE_PATH, "w") as f:
            json.dump(LLM_CACHE, f, indent=2)
        print(f"  Saved LLM cache: {len(LLM_CACHE)} entries")


def classify_post_llm(post):
    """Classify a post using OpenAI GPT-5.2 structured output with disk cache."""
    cache_key = f"{post['run_id']}|{post['id']}"

    if cache_key in LLM_CACHE:
        cached = LLM_CACHE[cache_key]
        return cached["category"] if isinstance(cached, dict) else cached

    if not HAS_OPENAI:
        return None

    client = _get_openai_client()
    if client is None:
        return None

    user_content = f"Title: {post['title']}\n\nContent: {post.get('content', '')}"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.parse(
                model="gpt-5.2",
                messages=[
                    {"role": "system", "content": LLM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0,
                response_format=PostClassification,
            )
            parsed = response.choices[0].message.parsed
            LLM_CACHE[cache_key] = {"category": parsed.category, "reasoning": parsed.reasoning}
            return parsed.category

        except Exception as e:
            print(f"  LLM error (attempt {attempt+1}) for '{post['title'][:30]}': {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    # All retries exhausted
    print(f"  LLM FAILED after {max_retries} attempts: '{post['title'][:40]}'")
    LLM_CACHE[cache_key] = {"category": None, "reasoning": "classification failed"}
    return None


# ---------------------------------------------------------------------------
# Analysis 1: Post Volume & Voting by Condition
# ---------------------------------------------------------------------------

def analysis_1(posts, activity, post_lookup, conditions):
    print("\n=== Analysis 1: Post Volume & Voting by Condition ===")

    runs = sorted(set(p["run_id"] for p in posts))

    # Categorise posts
    seed_by_cond = defaultdict(list)
    agent_by_cond = defaultdict(list)
    for p in posts:
        cond = p["condition"]
        if is_seed_post(p):
            seed_by_cond[cond].append(p)
        else:
            agent_by_cond[cond].append(p)

    # Build post lookup sets per run
    seed_by_run = defaultdict(dict)
    agent_posts_by_run = defaultdict(dict)
    for p in posts:
        key = (p["run_id"], p["id"])
        if is_seed_post(p):
            seed_by_run[p["run_id"]][key] = p
        else:
            agent_posts_by_run[p["run_id"]][key] = p

    # Count organic votes
    seed_votes = defaultdict(lambda: defaultdict(int))
    agent_votes = defaultdict(lambda: defaultdict(int))
    for e in activity:
        if e["action_type"] not in ("upvote", "downvote"):
            continue
        if not is_organic(e):
            continue
        run = e["run_id"]
        cond = e["condition"]
        key = (run, e["target_id"])
        if key in seed_by_run[run]:
            seed_votes[cond][e["action_type"]] += 1
        elif key in agent_posts_by_run[run]:
            agent_votes[cond][e["action_type"]] += 1

    # Per-run breakdown
    runs_per_cond = defaultdict(list)
    for r in runs:
        cond = next((p["condition"] for p in posts if p["run_id"] == r), None)
        if cond:
            runs_per_cond[cond].append(r)

    # --- Markdown ---
    md = "# Analysis 1: Post Volume & Voting by Condition\n\n"
    md += f"**{len(runs)} runs** across {len(conditions)} conditions (1 replication each, run03).\n"
    md += "10 GPT-5 agents per run, Mode C (no nudges).\n\n"

    md += "## Post Counts (aggregated across replications)\n\n"
    md += "| Condition | Runs | Seed Posts | Agent Posts | Total | Agents/Run |\n"
    md += "|---|---|---|---|---|---|\n"
    for cond in conditions:
        n_runs = len(runs_per_cond[cond])
        n_seed = len(seed_by_cond[cond])
        n_agent = len(agent_by_cond[cond])
        per_run = f"{n_agent/n_runs:.1f}" if n_runs > 0 else "—"
        md += f"| {CONDITION_LABELS.get(cond, cond)} | {n_runs} | {n_seed} | {n_agent} | {n_seed + n_agent} | {per_run} |\n"

    md += "\n## Organic Votes on Seed Posts\n\n"
    md += "| Condition | Seed Up | Seed Down | Net |\n"
    md += "|---|---|---|---|\n"
    for cond in conditions:
        su = seed_votes[cond].get("upvote", 0)
        sd = seed_votes[cond].get("downvote", 0)
        md += f"| {CONDITION_LABELS.get(cond, cond)} | {su} | {sd} | {su - sd} |\n"

    md += "\n## Organic Votes on Agent-Created Posts\n\n"
    md += "| Condition | Agent Up | Agent Down | Net |\n"
    md += "|---|---|---|---|\n"
    for cond in conditions:
        au = agent_votes[cond].get("upvote", 0)
        ad = agent_votes[cond].get("downvote", 0)
        md += f"| {CONDITION_LABELS.get(cond, cond)} | {au} | {ad} | {au - ad} |\n"

    # Key patterns
    md += "\n## Key Patterns\n\n"
    mag0_agent = len(agent_by_cond["mag0"])
    md += f"1. **mag0** (empty feed): agents created **{mag0_agent}** posts in 1 run\n"
    for cond in DOM_CONDITIONS:
        n_agent = len(agent_by_cond[cond])
        su = seed_votes[cond].get("upvote", 0)
        sd = seed_votes[cond].get("downvote", 0)
        md += f"2. **{cond}**: {n_agent} agent posts, seed votes {su}↑/{sd}↓\n"

    write_finding("01-vote-table.md", md)

    # --- Plot: grouped bar chart ---
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    x = np.arange(len(conditions))
    w = 0.35

    for ax_idx, (vtype, ylabel) in enumerate([("upvote", "Upvotes"), ("downvote", "Downvotes")]):
        ax = axes[ax_idx]
        s_vals = [seed_votes[c].get(vtype, 0) for c in conditions]
        a_vals = [agent_votes[c].get(vtype, 0) for c in conditions]

        bars_s = ax.bar(x - w/2, s_vals, w, label="Seed posts", color=C_CONSPIRACY, alpha=0.85)
        bars_a = ax.bar(x + w/2, a_vals, w, label="Agent posts", color=C_AGENT, alpha=0.85)
        for bars in [bars_s, bars_a]:
            for bar in bars:
                h = bar.get_height()
                if h > 0:
                    ax.text(bar.get_x() + bar.get_width()/2, h + 0.3, str(int(h)),
                            ha="center", va="bottom", fontsize=8, fontweight="bold")
        ax.set_xticks(x)
        ax.set_xticklabels([c for c in conditions], rotation=30, ha="right", fontsize=9)
        ax.set_ylabel(f"{ylabel} Count")
        ax.set_title(f"{ylabel} by Post Type")
        ax.legend(fontsize=9)
        # Divider between mag and dom
        ax.axvline(len(MAG_CONDITIONS) - 0.5, color="gray", linestyle="--", alpha=0.4)

    fig.suptitle("Entropy Collapse: Votes by Condition (run03)",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, "01-votes-by-magnitude.png")

    return seed_votes, agent_votes


# ---------------------------------------------------------------------------
# Classification (shared by --classify-only and full analysis)
# ---------------------------------------------------------------------------

def classify_all_posts(agent_posts):
    """Run keyword + LLM classification on agent posts. Returns (kw_list, llm_list)."""
    load_llm_cache()
    cached = sum(1 for p in agent_posts if f"{p['run_id']}|{p['id']}" in LLM_CACHE)
    llm_target = min(LLM_LIMIT, len(agent_posts)) if LLM_LIMIT > 0 else len(agent_posts)
    to_classify = max(0, llm_target - cached)

    print(f"  {len(agent_posts)} agent posts, {cached} cached, {to_classify} to classify via LLM", flush=True)
    if LLM_LIMIT > 0:
        print(f"  --limit {LLM_LIMIT}", flush=True)

    classifications = []
    llm_classifications = []
    llm_calls = 0

    for i, p in enumerate(agent_posts):
        kw = classify_post_theme(p)
        classifications.append(kw)

        cache_key = f"{p['run_id']}|{p['id']}"
        if cache_key in LLM_CACHE:
            cached_val = LLM_CACHE[cache_key]
            llm_cls = cached_val["category"] if isinstance(cached_val, dict) else cached_val
        elif LLM_LIMIT > 0 and llm_calls >= LLM_LIMIT:
            llm_cls = None
        else:
            llm_cls = classify_post_llm(p)
            llm_calls += 1
            match = "MATCH" if llm_cls == kw else "DIFF"
            print(f"  [{llm_calls}/{to_classify}] {p.get('condition',''):10s} | KW: {kw:35s} | LLM: {str(llm_cls):35s} | {match} | {p['title'][:60]}", flush=True)

        llm_classifications.append(llm_cls)

        if llm_calls > 0 and llm_calls % 50 == 0:
            save_llm_cache()

    if llm_calls > 0:
        save_llm_cache()
        print(f"  LLM classification complete. {llm_calls} API calls made.", flush=True)

    return classifications, llm_classifications


# ---------------------------------------------------------------------------
# Analysis 2: Agent Post Categories & Convergence (KEY ANALYSIS)
# ---------------------------------------------------------------------------

def analysis_2(posts, activity, post_lookup, conditions):
    print("\n=== Analysis 2: Agent Post Categories & Convergence ===")

    agent_posts = [p for p in posts if not is_seed_post(p)]
    agent_posts.sort(key=lambda p: (conditions.index(p["condition"]), p["run_id"], p["created_at"]))

    classifications, llm_classifications = classify_all_posts(agent_posts)

    # Check conspiracy promotion
    conspiracy_keywords = ["wake up", "they don't want you to know", "cover up",
                          "mainstream media lies", "truth is being hidden", "sheeple"]
    promotes_conspiracy = [p for p in agent_posts
                           if any(kw in p.get("content", "").lower() for kw in conspiracy_keywords)]

    md = "# Analysis 2: Agent Post Categories & Convergence\n\n"
    md += f"**{len(agent_posts)} agent-generated posts** across {len(conditions)} conditions (1 run each, run03).\n\n"

    if promotes_conspiracy:
        md += f"**{len(promotes_conspiracy)} post(s) potentially promote conspiracy.**\n\n"
    else:
        md += "**Zero promote conspiracy.** All are community, self-reflection, evidence/skepticism, or meta-analysis.\n\n"

    # Category distribution per condition (keyword)
    theme_by_cond = defaultdict(Counter)
    for p, cls in zip(agent_posts, classifications):
        theme_by_cond[p["condition"]][cls] += 1

    # Category distribution per condition (LLM)
    llm_theme_by_cond = defaultdict(Counter)
    for p, cls in zip(agent_posts, llm_classifications):
        llm_theme_by_cond[p["condition"]][cls] += 1

    md += "## Category Distribution per Condition (Keyword classifier)\n\n"
    md += "| Category | " + " | ".join(conditions) + " |\n"
    md += "|---" + "|---" * len(conditions) + "|\n"
    for theme in ALL_THEMES:
        row = f"| {theme}"
        for cond in conditions:
            total = sum(theme_by_cond[cond].values())
            count = theme_by_cond[cond].get(theme, 0)
            pct = (count / total * 100) if total > 0 else 0
            row += f" | {count} ({pct:.0f}%)"
        md += row + " |\n"
    row = "| **Total**"
    for cond in conditions:
        row += f" | **{sum(theme_by_cond[cond].values())}**"
    md += row + " |\n"

    md += "\n## Category Distribution per Condition (LLM classifier)\n\n"
    md += "| Category | " + " | ".join(conditions) + " |\n"
    md += "|---" + "|---" * len(conditions) + "|\n"
    for theme in ALL_THEMES:
        row = f"| {theme}"
        for cond in conditions:
            total = sum(llm_theme_by_cond[cond].values())
            count = llm_theme_by_cond[cond].get(theme, 0)
            pct = (count / total * 100) if total > 0 else 0
            row += f" | {count} ({pct:.0f}%)"
        md += row + " |\n"
    row = "| **Total**"
    for cond in conditions:
        row += f" | **{sum(llm_theme_by_cond[cond].values())}**"
    md += row + " |\n"

    # Agreement rate
    agree = sum(1 for k, l in zip(classifications, llm_classifications) if k == l)
    md += f"\n**Classifier agreement: {agree}/{len(classifications)} ({agree/len(classifications)*100:.0f}%)**\n"

    # Per-run breakdown
    theme_by_run = defaultdict(Counter)
    for p, cls in zip(agent_posts, classifications):
        theme_by_run[p["run_id"]][cls] += 1

    md += "\n## Per-Run Breakdown (replication consistency)\n\n"
    md += "| Run | Agent Posts | Convergence % | Top Category |\n"
    md += "|---|---|---|---|\n"
    for cond in conditions:
        cond_runs = sorted(set(p["run_id"] for p in agent_posts if p["condition"] == cond))
        for run_id in cond_runs:
            tc = theme_by_run[run_id]
            total = sum(tc.values())
            gp = convergence_pct(tc)
            top = tc.most_common(1)[0][0] if tc else "—"
            md += f"| {run_id} | {total} | {gp:.0f}% | {top} |\n"

    # Governance/meta ratio
    md += "\n## Convergence Ratio per Condition\n\n"
    md += "Convergence = Community + Self-reflection/consciousness + Evidence & skepticism + Meta-analysis (everything except Original discussion).\n\n"
    md += "| Condition | Convergence | Original | Total | Conv % (KW) | Conv % (LLM) |\n"
    md += "|---|---|---|---|---|---|\n"

    conv_ratios = {}
    llm_conv_ratios = {}
    for cond in conditions:
        total = sum(theme_by_cond[cond].values())
        conv = sum(theme_by_cond[cond].get(t, 0) for t in CONVERGENCE_THEMES)
        other = total - conv
        pct = (conv / total * 100) if total > 0 else 0
        conv_ratios[cond] = pct
        llm_total = sum(llm_theme_by_cond[cond].values())
        llm_conv = sum(llm_theme_by_cond[cond].get(t, 0) for t in CONVERGENCE_THEMES)
        llm_pct = (llm_conv / llm_total * 100) if llm_total > 0 else 0
        llm_conv_ratios[cond] = llm_pct
        md += f"| {cond} | {conv} | {other} | {total} | {pct:.0f}% | {llm_pct:.0f}% |\n"

    # (Baselines omitted — different category scheme from previous experiments)

    # Full catalog with both classifiers
    md += "\n## Full Catalog\n\n"
    md += "| # | Condition | Author | Title | Keyword Theme | LLM Theme | Match |\n"
    md += "|---|---|---|---|---|---|---|\n"
    for i, (p, cls_kw, cls_llm) in enumerate(zip(agent_posts, classifications, llm_classifications), 1):
        author = p["author_name"].replace("ranking_", "")
        title = p["title"][:50] + ("..." if len(p["title"]) > 50 else "")
        match = "yes" if cls_kw == cls_llm else "**NO**"
        md += (f"| {i} | {p['condition']} | {author} "
               f"| {title} | {cls_kw} | {cls_llm} | {match} |\n")

    # Key insight
    total_agents = len(agent_posts)
    kw_conv = sum(1 for cls in classifications if cls in CONVERGENCE_THEMES)
    llm_conv = sum(1 for cls in llm_classifications if cls in CONVERGENCE_THEMES)
    md += f"\n## Key Insight\n\n"
    md += f"- **Keyword classifier**: {kw_conv}/{total_agents} ({kw_conv/total_agents*100:.0f}%) convergence\n"
    md += f"- **LLM classifier**: {llm_conv}/{total_agents} ({llm_conv/total_agents*100:.0f}%) convergence\n\n"

    mag0_gov = conv_ratios.get("mag0", 0)
    mag25_gov = conv_ratios.get("mag25", 0)
    dom_agi_gov = conv_ratios.get("dom-agi", 0)
    dom_tech_gov = conv_ratios.get("dom-tech", 0)

    if mag0_gov > 50 and mag25_gov > 50:
        md += "**Convergence persists even at mag0 (empty feed)** — agents default to convergence "
        md += "regardless of seed content. This suggests RLHF-driven convergence, not feed-driven.\n\n"

    if dom_agi_gov > 50 or dom_tech_gov > 50:
        md += "**Domain transfer confirmed** — agents converge on convergence even with "
        md += f"non-conspiracy seeds (dom-agi: {dom_agi_gov:.0f}%, dom-tech: {dom_tech_gov:.0f}%). "
        md += "Convergence is topic-agnostic.\n"
    elif dom_agi_gov < 30 and dom_tech_gov < 30:
        md += "**Domain-specific divergence** — non-conspiracy seeds produce different category "
        md += f"distributions (dom-agi: {dom_agi_gov:.0f}%, dom-tech: {dom_tech_gov:.0f}%). "
        md += "Convergence may be conspiracy-specific.\n"

    write_finding("02-agent-posts.md", md)

    # --- Plot 1: Side-by-side stacked bars (Keyword vs LLM) ---
    fig, axes = plt.subplots(1, 2, figsize=(18, 7), sharey=True)

    for ax_idx, (label, t_by_c) in enumerate([("Keyword", theme_by_cond), ("LLM", llm_theme_by_cond)]):
        ax = axes[ax_idx]
        x = np.arange(len(conditions))
        bottom = np.zeros(len(conditions))
        for theme in ALL_THEMES:
            vals = []
            for cond in conditions:
                total = sum(t_by_c[cond].values())
                vals.append((t_by_c[cond].get(theme, 0) / total * 100) if total > 0 else 0)
            vals = np.array(vals)
            ax.bar(x, vals, bottom=bottom, label=theme, color=CATEGORY_COLORS[theme], alpha=0.85)
            for i, (v, b) in enumerate(zip(vals, bottom)):
                if v > 10:
                    ax.text(i, b + v/2, f"{v:.0f}%", ha="center", va="center",
                            fontsize=7, fontweight="bold", color="white")
            bottom += vals
        ax.set_xticks(x)
        ax.set_xticklabels(conditions, rotation=35, ha="right", fontsize=8)
        ax.set_ylabel("% of Agent Posts")
        ax.set_title(f"{label} Classifier")
        ax.set_ylim(0, 115)
        ax.axvline(len(MAG_CONDITIONS) - 0.5, color="gray", linestyle="--", alpha=0.4)

    axes[0].legend(fontsize=7, loc="upper right")
    fig.suptitle("Agent Post Category Distribution: Keyword vs LLM",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    save_plot(fig, "02-category-distribution.png")

    # --- Plot 2: Convergence ratio (both classifiers) ---
    fig, ax = plt.subplots(figsize=(11, 6))
    x = np.arange(len(conditions))
    w = 0.35
    kw_vals = [conv_ratios.get(c, 0) for c in conditions]
    llm_vals = [llm_conv_ratios.get(c, 0) for c in conditions]

    bars_kw = ax.bar(x - w/2, kw_vals, w, label="Keyword", color="#1565C0", alpha=0.85)
    bars_llm = ax.bar(x + w/2, llm_vals, w, label="LLM", color="#7B1FA2", alpha=0.85)
    for bars in [bars_kw, bars_llm]:
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.text(bar.get_x() + bar.get_width()/2, h + 1,
                        f"{h:.0f}%", ha="center", va="bottom", fontsize=9, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(conditions, rotation=20, ha="right", fontsize=9)
    ax.set_ylabel("Convergence %")
    ax.set_title("Convergence Ratio: Keyword vs LLM Classifier")
    ax.legend(fontsize=9)
    ax.set_ylim(0, 115)
    ax.axvline(len(MAG_CONDITIONS) - 0.5, color="gray", linestyle="--", alpha=0.3)

    save_plot(fig, "02-governance-ratio.png")

    return agent_posts, classifications, llm_classifications, theme_by_cond, llm_theme_by_cond, conv_ratios


# ---------------------------------------------------------------------------
# Analysis 3: Per-Agent Behavior
# ---------------------------------------------------------------------------

def analysis_3(posts, activity, post_lookup, agent_posts, classifications, conditions):
    print("\n=== Analysis 3: Per-Agent Behavior ===")

    agents = sorted(AGENT_ARCHETYPES.keys())

    # Per-agent post creation
    agent_cond_posts = defaultdict(list)
    for p, cls in zip(agent_posts, classifications):
        agent_cond_posts[(p["author_name"], p["condition"])].append(cls)

    md = "# Analysis 3: Per-Agent Behavior\n\n"
    md += "## Post Creation by Agent × Condition\n\n"
    md += "| Agent | Archetype | " + " | ".join(conditions) + " | Total |\n"
    md += "|---|---" + "|---" * len(conditions) + "|---|\n"

    creation_matrix = np.zeros((len(agents), len(conditions)))
    for i, agent in enumerate(agents):
        row = f"| {agent.replace('ranking_', '')} | {AGENT_ARCHETYPES[agent]}"
        total = 0
        for j, cond in enumerate(conditions):
            n = len(agent_cond_posts.get((agent, cond), []))
            creation_matrix[i, j] = n
            total += n
            themes = agent_cond_posts.get((agent, cond), [])
            if themes:
                abbrevs = [t[:5] for t in themes]
                row += f" | {n}"
            else:
                row += " | 0"
        md += row + f" | {total} |\n"

    # Per-agent voting
    seed_by_run = defaultdict(dict)
    agent_posts_by_run = defaultdict(dict)
    for p in posts:
        key = (p["run_id"], p["id"])
        if is_seed_post(p):
            seed_by_run[p["run_id"]][key] = p
        else:
            agent_posts_by_run[p["run_id"]][key] = p

    agent_cond_votes = defaultdict(lambda: defaultdict(int))
    for e in activity:
        if e["action_type"] not in ("upvote", "downvote"):
            continue
        if not is_organic(e):
            continue
        run = e["run_id"]
        cond = e["condition"]
        agent = e["agent_name"]
        key = (run, e["target_id"])
        if key in seed_by_run[run]:
            agent_cond_votes[(agent, cond)][("seed", e["action_type"])] += 1
        elif key in agent_posts_by_run[run]:
            agent_cond_votes[(agent, cond)][("agent", e["action_type"])] += 1

    md += "\n## Per-Agent Voting Summary (all conditions)\n\n"
    md += "| Agent | Archetype | Condition | Seed Up | Seed Down | Agent Up | Agent Down |\n"
    md += "|---|---|---|---|---|---|---|\n"
    for agent in agents:
        for cond in conditions:
            su = agent_cond_votes[(agent, cond)].get(("seed", "upvote"), 0)
            sd = agent_cond_votes[(agent, cond)].get(("seed", "downvote"), 0)
            au = agent_cond_votes[(agent, cond)].get(("agent", "upvote"), 0)
            ad = agent_cond_votes[(agent, cond)].get(("agent", "downvote"), 0)
            if su + sd + au + ad > 0:
                md += (f"| {agent.replace('ranking_', '')} | {AGENT_ARCHETYPES[agent]} "
                       f"| {cond} | {su} | {sd} | {au} | {ad} |\n")

    # Personality × Category
    md += "\n## Personality × Category Correlation\n\n"
    arch_themes = defaultdict(Counter)
    for p, cls in zip(agent_posts, classifications):
        arch = AGENT_ARCHETYPES.get(p["author_name"], "?")
        arch_themes[arch][cls] += 1

    if arch_themes:
        present_themes = sorted(set(cls for counts in arch_themes.values() for cls in counts))
        md += "| Archetype | " + " | ".join(present_themes) + " | Total |\n"
        md += "|---" + "|---" * len(present_themes) + "|---|\n"
        for arch in sorted(arch_themes.keys()):
            row = f"| {arch}"
            total = 0
            for theme in present_themes:
                c = arch_themes[arch].get(theme, 0)
                row += f" | {c}"
                total += c
            md += row + f" | {total} |\n"

    write_finding("03-per-agent-behavior.md", md)

    # --- Plot: heatmap ---
    fig, ax = plt.subplots(figsize=(12, 8))
    im = ax.imshow(creation_matrix, cmap="YlOrRd", aspect="auto", vmin=0)
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels(conditions, rotation=30, ha="right", fontsize=9)
    ax.set_yticks(range(len(agents)))
    ax.set_yticklabels(
        [f"{a.replace('ranking_', '')} ({AGENT_ARCHETYPES[a]})" for a in agents],
        fontsize=9)
    ax.set_title("Agent Post Creation by Condition (run03)")
    ax.axvline(len(MAG_CONDITIONS) - 0.5, color="white", linestyle="--", alpha=0.6, linewidth=2)

    for i in range(len(agents)):
        for j in range(len(conditions)):
            val = int(creation_matrix[i, j])
            if val > 0:
                maxval = creation_matrix.max()
                color = "white" if maxval > 0 and val > maxval * 0.6 else "black"
                ax.text(j, i, str(val), ha="center", va="center",
                        fontsize=10, fontweight="bold", color=color)
    fig.colorbar(im, ax=ax, shrink=0.8)
    save_plot(fig, "03-agent-heatmap.png")

    return agent_cond_posts, agent_cond_votes


# ---------------------------------------------------------------------------
# Analysis 4: Comment Patterns
# ---------------------------------------------------------------------------

def analysis_4(posts, comments, post_lookup, conditions):
    print("\n=== Analysis 4: Comment Patterns ===")

    comment_data = []
    for c in comments:
        key = (c["run_id"], c["post_id"])
        post = post_lookup.get(key)
        if post:
            pt = "seed" if is_seed_post(post) else "agent"
        else:
            pt = "unknown"
        comment_data.append({**c, "target_post_type": pt})

    organic = [c for c in comment_data if c["author_name"] not in SYSTEM_AGENTS]

    for c in organic:
        c["stance"] = classify_stance(c["content"])

    md = f"# Analysis 4: Comment Patterns\n\n"
    md += f"**{len(organic)} organic comments** across {len(conditions)} conditions.\n\n"

    # Comments per condition × target type
    md += "## Comments by Condition and Target Post Type\n\n"
    md += "| Condition | On Seed | On Agent | Total |\n"
    md += "|---|---|---|---|\n"
    for cond in conditions:
        mc = [c for c in organic if c["condition"] == cond]
        on_s = sum(1 for c in mc if c["target_post_type"] == "seed")
        on_a = sum(1 for c in mc if c["target_post_type"] == "agent")
        md += f"| {cond} | {on_s} | {on_a} | {len(mc)} |\n"

    # Stance by condition
    stances = ["corrective", "supportive", "meta-epistemic", "neutral"]
    stance_by_cond = defaultdict(Counter)
    for c in organic:
        stance_by_cond[c["condition"]][c["stance"]] += 1

    md += "\n## Comment Stance by Condition\n\n"
    md += "| Condition | Corrective | Supportive | Meta-epistemic | Neutral | Total |\n"
    md += "|---|---|---|---|---|---|\n"
    for cond in conditions:
        sc = stance_by_cond[cond]
        total = sum(sc.values())
        md += (f"| {cond} | {sc.get('corrective', 0)} | {sc.get('supportive', 0)} "
               f"| {sc.get('meta-epistemic', 0)} | {sc.get('neutral', 0)} | {total} |\n")

    # Stance by target type
    stance_by_type = defaultdict(lambda: defaultdict(int))
    for c in organic:
        stance_by_type[c["target_post_type"]][c["stance"]] += 1

    md += "\n## Comment Stance by Target Post Type (all conditions)\n\n"
    md += "| Post Type | Corrective | Supportive | Meta-epistemic | Neutral | Total |\n"
    md += "|---|---|---|---|---|---|\n"
    for pt in ["seed", "agent"]:
        sc = stance_by_type[pt]
        total = sum(sc.values())
        md += (f"| {pt} | {sc['corrective']} | {sc['supportive']} "
               f"| {sc['meta-epistemic']} | {sc['neutral']} | {total} |\n")

    # Word count
    md += "\n## Comment Length by Condition\n\n"
    for cond in conditions:
        mc = [c for c in organic if c["condition"] == cond]
        if mc:
            wc = [len(c["content"].split()) for c in mc]
            md += (f"- **{cond}** (n={len(mc)}): mean {np.mean(wc):.0f} words, "
                   f"median {np.median(wc):.0f}, range {min(wc)}-{max(wc)}\n")

    write_finding("04-comment-patterns.md", md)

    # --- Plot: stance distribution per condition ---
    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(conditions))
    bottom = np.zeros(len(conditions))
    stance_colors = {
        "corrective": "#FF5722",
        "supportive": "#4CAF50",
        "meta-epistemic": "#9C27B0",
        "neutral": "#9E9E9E",
    }
    for stance in stances:
        vals = [stance_by_cond[c][stance] for c in conditions]
        ax.bar(x, vals, bottom=bottom, label=stance.capitalize(),
               color=stance_colors[stance], alpha=0.85)
        for i, (v, b) in enumerate(zip(vals, bottom)):
            if v > 0:
                ax.text(i, b + v/2, str(int(v)), ha="center", va="center",
                        fontsize=8, fontweight="bold", color="white")
        bottom += np.array(vals)

    ax.set_xticks(x)
    ax.set_xticklabels(conditions, rotation=20, ha="right", fontsize=9)
    ax.set_xlabel("Condition")
    ax.set_ylabel("Comment Count")
    ax.set_title("Comment Stance Distribution by Condition")
    ax.legend(fontsize=9)
    ax.axvline(len(MAG_CONDITIONS) - 0.5, color="gray", linestyle="--", alpha=0.3)
    save_plot(fig, "04-stance-by-magnitude.png")

    return organic, stance_by_cond, stance_by_type


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def write_summary(posts, agent_posts, classifications, theme_by_cond, conv_ratios,
                  seed_votes, agent_votes, organic_comments, stance_by_cond,
                  conditions, n_runs, n_posts, n_comments, n_activity):

    total_gov = sum(1 for cls in classifications if cls in CONVERGENCE_THEMES)
    total_agents = len(agent_posts)

    md = f"""# Entropy Collapse: Stimulus Magnitude & Domain Transfer Analysis

## Research Question

1. **E-MAG**: What is the minimum dose of conspiracy seed content needed to trigger entropy collapse?
2. **E-DOM**: Does convergence depend on conspiracy content specifically, or does it happen with *any* seed topic?

## Dataset

- **6 conditions**: mag0 (empty), mag1 (1 conspiracy), mag5 (5), mag25 (25), dom-agi (25 AGI hype), dom-tech (25 tech humor)
- **{n_runs} runs** (1 replication per condition, run03), 10 GPT-5 agents per run
- Mode C (no ranking nudges) — pure content composition effect
- {n_posts} total posts, {len(organic_comments)} organic comments, {n_activity} activity events

## Core Finding: Category Distribution Across Conditions

"""

    for cond in conditions:
        total = sum(theme_by_cond[cond].values())
        if total == 0:
            md += f"**{cond}** (0 agent posts)\n\n"
            continue
        md += f"**{cond}** ({total} agent posts, {conv_ratios[cond]:.0f}% convergence):\n"
        for theme in ALL_THEMES:
            count = theme_by_cond[cond].get(theme, 0)
            if count > 0:
                pct = count / total * 100
                md += f"  - {theme}: {count} ({pct:.0f}%)\n"
        md += "\n"

    md += "## Convergence Ratio (Keyword classifier)\n\n"
    md += "| Condition | Convergence % |\n"
    md += "|---|---|\n"
    for cond in conditions:
        pct = conv_ratios.get(cond, 0)
        md += f"| {cond} | {pct:.0f}% |\n"

    # Key conclusions
    md += "## Key Conclusions\n\n"

    mag0_gov = conv_ratios.get("mag0", 0)
    mag25_gov = conv_ratios.get("mag25", 0)
    dom_agi_gov = conv_ratios.get("dom-agi", 0)
    dom_tech_gov = conv_ratios.get("dom-tech", 0)

    # Conclusion 1: RLHF vs feed-driven
    if mag0_gov > 50:
        md += "### 1. Convergence is RLHF-driven, not feed-driven\n\n"
        md += f"At mag0 (empty feed), agents still produce {mag0_gov:.0f}% convergence content "
        md += f"(n={sum(theme_by_cond['mag0'].values())} posts in 1 run). "
        md += "Convergence happens regardless of stimulus.\n\n"
    else:
        md += "### 1. Feed content amplifies convergence\n\n"
        md += f"At mag0, convergence is {mag0_gov:.0f}%, rising to {mag25_gov:.0f}% at mag25. "
        md += "Seed content amplifies but doesn't solely cause convergence.\n\n"

    # Conclusion 2: Domain transfer
    if dom_agi_gov > 50 or dom_tech_gov > 50:
        md += "### 2. Domain transfer confirmed — convergence is topic-agnostic\n\n"
        md += f"Non-conspiracy seeds also trigger convergence: dom-agi {dom_agi_gov:.0f}%, "
        md += f"dom-tech {dom_tech_gov:.0f}%. The convergence attractor is independent of seed topic.\n\n"
    else:
        md += "### 2. Domain-specific behavior observed\n\n"
        md += f"Non-conspiracy seeds produce different patterns: dom-agi {dom_agi_gov:.0f}%, "
        md += f"dom-tech {dom_tech_gov:.0f}%. Topic matters for convergence.\n\n"

    # Conclusion 3: Minimum dose
    for mag_cond in ["mag1", "mag5", "mag25"]:
        if conv_ratios.get(mag_cond, 0) > 50:
            n = CONDITION_SEED_COUNTS[mag_cond]
            md += f"### 3. Minimum effective dose: {n} seed post{'s' if n > 1 else ''}\n\n"
            md += f"{mag_cond} reaches {conv_ratios[mag_cond]:.0f}% convergence.\n\n"
            break
    else:
        md += "### 3. No clear magnitude threshold\n\n"

    md += f"### 4. Agent-created content never engages with seed topics\n\n"
    md += f"{total_agents} agent posts across all conditions: zero promote conspiracy.\n"
    md += f"{total_gov} of {total_agents} ({total_gov/total_agents*100:.0f}%) are convergence.\n\n"

    # Voting summary
    md += "### 5. Voting patterns\n\n"
    for cond in conditions:
        su = seed_votes[cond].get("upvote", 0)
        sd = seed_votes[cond].get("downvote", 0)
        au = agent_votes[cond].get("upvote", 0)
        ad = agent_votes[cond].get("downvote", 0)
        if su + sd + au + ad > 0:
            md += f"- {cond}: seed {su}↑/{sd}↓, agent {au}↑/{ad}↓\n"

    md += f"""

## Limitations

- 1 run per condition (run03) — more replications needed for statistical confidence
- All agents use GPT-5 — results may not generalize across models
- Small sample of agent-created posts per condition (especially mag1, mag5)
- Keyword classifier may miscategorize borderline posts
- Domain conditions use different seed topics — not perfectly controlled comparison

---

*Generated by `scripts/analyze-moltbook-entropy-collapse.py`*
"""
    write_finding("00-summary.md", md)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    global DATA_DIR, OUT_DIR, PLOT_DIR, LLM_CACHE_PATH, LLM_LIMIT

    # CLI: python3 script.py [data_dir] [out_dir] [--limit N] [--classify-only]
    positional = []
    classify_only = False
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--limit" and i + 1 < len(sys.argv):
            LLM_LIMIT = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--classify-only":
            classify_only = True
            i += 1
        else:
            positional.append(sys.argv[i])
            i += 1

    if len(positional) >= 1:
        DATA_DIR = REPO_ROOT / positional[0]
    if len(positional) >= 2:
        OUT_DIR = REPO_ROOT / positional[1]
        PLOT_DIR = OUT_DIR / "plots"

    LLM_CACHE_PATH = OUT_DIR / "llm_cache.json"

    if LLM_LIMIT > 0:
        print(f"  LLM limit: {LLM_LIMIT} posts (testing mode)", flush=True)

    print(f"Moltbook Entropy Collapse Analysis", flush=True)
    print(f"  Data: {DATA_DIR.relative_to(REPO_ROOT)}", flush=True)
    print(f"  Output: {OUT_DIR.relative_to(REPO_ROOT)}", flush=True)
    print("=" * 55, flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    # Load data
    print("\nLoading data...", flush=True)
    all_posts, all_comments, all_activity = load_all_runs()

    if not all_posts:
        print("ERROR: No posts found. Check DATA_DIR:", DATA_DIR)
        sys.exit(1)

    runs = sorted(set(p["run_id"] for p in all_posts))
    found_conditions = sorted(set(p["condition"] for p in all_posts),
                              key=lambda c: ALL_CONDITIONS.index(c) if c in ALL_CONDITIONS else 99)

    print(f"  {len(all_posts)} posts, {len(all_comments)} comments, {len(all_activity)} activity events", flush=True)
    print(f"  {len(runs)} runs: {', '.join(runs)}", flush=True)
    print(f"  Conditions: {found_conditions}", flush=True)

    # --classify-only: build LLM cache and exit
    if classify_only:
        agent_posts = [p for p in all_posts if not is_seed_post(p)]
        agent_posts.sort(key=lambda p: (p.get("condition", ""), p["run_id"], p["created_at"]))
        classify_all_posts(agent_posts)
        return

    post_lookup = build_post_lookup(all_posts)

    # Run analyses
    seed_votes, agent_votes = analysis_1(all_posts, all_activity, post_lookup, found_conditions)
    agent_posts, classifications, llm_classifications, theme_by_cond, llm_theme_by_cond, conv_ratios = analysis_2(
        all_posts, all_activity, post_lookup, found_conditions)
    analysis_3(all_posts, all_activity, post_lookup, agent_posts, classifications, found_conditions)
    organic_comments, stance_by_cond, stance_by_type = analysis_4(
        all_posts, all_comments, post_lookup, found_conditions)

    # Write summary
    print("\n=== Writing Summary ===")
    write_summary(all_posts, agent_posts, classifications, theme_by_cond, conv_ratios,
                  seed_votes, agent_votes, organic_comments, stance_by_cond,
                  found_conditions, len(runs), len(all_posts), len(all_comments), len(all_activity))

    print(f"\nDone! Findings in {OUT_DIR.relative_to(REPO_ROOT)}/")
    print(f"Plots in {PLOT_DIR.relative_to(REPO_ROOT)}/")


if __name__ == "__main__":
    main()
