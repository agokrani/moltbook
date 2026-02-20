#!/usr/bin/env python3
"""
Ranking-Effect Experiment Analysis
===================================
Analyzes CivicLens Experiment 1: Does algorithmic ranking nudge
affect organic engagement on AI-agent social media?

Mode A: Only world (seed) posts randomly assigned to nudge_up / control / nudge_down
        (actual ranking manipulation via synthetic votes on seed posts only)
Mode B: ALL posts (world + agent-created) randomly assigned to nudge_up / control / nudge_down
        (ranking manipulation applied to every post in the feed)

IMPORTANT: Runs 01-08 used sort=new (agents saw chronological feed, NOT hot-ranked).
           Runs 09-10 use sort=hot (agents see hot-ranked feed — correct behavior).
           Only runs 09-10 are valid for testing the ranking nudge hypothesis.

Runs:
  [sort=new — INVALID for ranking hypothesis, useful for model comparison only]
  kimi-k2.5 (OpenRouter, 10-15s heartbeat): e1a-run01..03, e1b-run01..03
  gpt-5-nano (OpenAI, 10-15s heartbeat):    e1a-run04, e1b-run04
  gpt-5-mini (OpenAI, 10-15s heartbeat):    e1a-run05..06, e1b-run05..06
  gpt-5 (OpenAI, 60s heartbeat):            e1a-run07, e1b-run07
  gpt-5.2 (OpenAI, 60s heartbeat):          e1a-run08, e1b-run08

  [sort=hot — VALID for ranking hypothesis]
  gpt-5 (OpenAI, 60s heartbeat):            e1a-run09, e1b-run09
  gpt-5.2 (OpenAI, 60s heartbeat):          e1a-run10, e1b-run10
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import statistics
import math

EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"

# ============================================================
# Run definitions
# ============================================================
# sort=new runs (agents saw chronological feed — ranking nudge invisible)
SORT_NEW_RUNS = {
    "kimi-k2.5":  {"A": ["e1a-run01", "e1a-run02", "e1a-run03"],
                   "B": ["e1b-run01", "e1b-run02", "e1b-run03"],
                   "heartbeat": "10-15s"},
    "gpt-5-nano": {"A": ["e1a-run04"], "B": ["e1b-run04"],
                   "heartbeat": "10-15s"},
    "gpt-5-mini": {"A": ["e1a-run05", "e1a-run06"], "B": ["e1b-run05", "e1b-run06"],
                   "heartbeat": "10-15s"},
    "gpt-5":      {"A": ["e1a-run07"], "B": ["e1b-run07"],
                   "heartbeat": "60s"},
    "gpt-5.2":    {"A": ["e1a-run08"], "B": ["e1b-run08"],
                   "heartbeat": "60s"},
}

# sort=hot runs (agents see hot-ranked feed — ranking nudge VISIBLE)
SORT_HOT_RUNS = {
    "gpt-5":      {"A": ["e1a-run09"], "B": ["e1b-run09"],
                   "heartbeat": "60s"},
    "gpt-5.2":    {"A": ["e1a-run10"], "B": ["e1b-run10"],
                   "heartbeat": "60s"},
}

# Combined model info (for model comparison sections)
RUNS_BY_MODEL = {}
for runs_dict in [SORT_NEW_RUNS, SORT_HOT_RUNS]:
    for model, info in runs_dict.items():
        if model not in RUNS_BY_MODEL:
            RUNS_BY_MODEL[model] = {"A": [], "B": [], "heartbeat": info["heartbeat"]}
        RUNS_BY_MODEL[model]["A"].extend(info["A"])
        RUNS_BY_MODEL[model]["B"].extend(info["B"])

ALL_MODELS = list(RUNS_BY_MODEL.keys())

# All runs (for data overview, model comparison)
GOOD_RUNS_A = [r for m in ALL_MODELS for r in RUNS_BY_MODEL[m]["A"]]
GOOD_RUNS_B = [r for m in ALL_MODELS for r in RUNS_BY_MODEL[m]["B"]]
ALL_GOOD_RUNS = GOOD_RUNS_A + GOOD_RUNS_B

# sort=hot only (for ranking hypothesis tests)
HOT_RUNS_A = [r for m in SORT_HOT_RUNS for r in SORT_HOT_RUNS[m]["A"]]
HOT_RUNS_B = [r for m in SORT_HOT_RUNS for r in SORT_HOT_RUNS[m]["B"]]
ALL_HOT_RUNS = HOT_RUNS_A + HOT_RUNS_B

# Feed sort type per run
FEED_SORT = {}
for runs_dict, sort_type in [(SORT_NEW_RUNS, "new"), (SORT_HOT_RUNS, "hot")]:
    for model, info in runs_dict.items():
        for r in info["A"] + info["B"]:
            FEED_SORT[r] = sort_type

MODEL_TIER = {}
for model, info in RUNS_BY_MODEL.items():
    for r in info["A"] + info["B"]:
        MODEL_TIER[r] = model


def load_jsonl(path):
    """Load a JSONL file into a list of dicts."""
    records = []
    if not path.exists():
        return records
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def load_run(run_name):
    """Load all data for a single run."""
    d = EXPORTS_DIR / run_name
    return {
        "name": run_name,
        "posts": load_jsonl(d / "posts.jsonl"),
        "comments": load_jsonl(d / "comments.jsonl"),
        "treatments": load_jsonl(d / "treatments.jsonl"),
        "activity": load_jsonl(d / "activity.jsonl"),
        "agents": load_jsonl(d / "agents.jsonl"),
        "metadata": json.loads((d / "metadata.json").read_text()) if (d / "metadata.json").exists() else {},
    }


def safe_mean(vals):
    return statistics.mean(vals) if vals else 0.0

def safe_stdev(vals):
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0

def safe_median(vals):
    return statistics.median(vals) if vals else 0.0


# ============================================================
# Statistical helper functions (no scipy dependency)
# ============================================================

def cohens_d(group1, group2):
    """Calculate Cohen's d effect size."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return 0.0
    m1, m2 = safe_mean(group1), safe_mean(group2)
    s1, s2 = safe_stdev(group1), safe_stdev(group2)
    pooled_std = math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))
    if pooled_std == 0:
        return 0.0
    return (m1 - m2) / pooled_std


def cohens_f(groups):
    """Calculate Cohen's f effect size for ANOVA-like comparison."""
    all_vals = [v for g in groups for v in g]
    if not all_vals:
        return 0.0
    grand_mean = safe_mean(all_vals)

    # Between-group variance
    ss_between = sum(len(g) * (safe_mean(g) - grand_mean)**2 for g in groups if g)
    # Within-group variance
    ss_within = sum(sum((v - safe_mean(g))**2 for v in g) for g in groups if g)

    n_total = len(all_vals)
    k = len([g for g in groups if g])

    if ss_within == 0 or n_total <= k:
        return 0.0

    ms_between = ss_between / (k - 1) if k > 1 else 0
    ms_within = ss_within / (n_total - k)

    if ms_within == 0:
        return 0.0

    f_stat = ms_between / ms_within
    # Cohen's f = sqrt(eta_squared / (1 - eta_squared))
    eta_sq = ss_between / (ss_between + ss_within)
    if eta_sq >= 1:
        return float('inf')
    return math.sqrt(eta_sq / (1 - eta_sq))


def kruskal_wallis_H(groups):
    """
    Kruskal-Wallis H statistic (non-parametric ANOVA).
    Returns (H, approximate p-value using chi-square approximation).
    """
    all_vals = []
    for i, g in enumerate(groups):
        for v in g:
            all_vals.append((v, i))

    n = len(all_vals)
    if n < 3:
        return 0.0, 1.0

    # Rank all values
    all_vals.sort(key=lambda x: x[0])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and all_vals[j][0] == all_vals[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2  # average rank for ties
        for k_idx in range(i, j):
            ranks[k_idx] = avg_rank
        i = j

    # Calculate H
    group_rank_sums = defaultdict(float)
    group_sizes = defaultdict(int)
    for idx, (val, gid) in enumerate(all_vals):
        group_rank_sums[gid] += ranks[idx]
        group_sizes[gid] += 1

    H = (12 / (n * (n + 1))) * sum(
        group_rank_sums[g]**2 / group_sizes[g]
        for g in group_rank_sums
    ) - 3 * (n + 1)

    # Chi-square approximation for p-value (df = k-1)
    k = len(groups)
    df = k - 1
    if df <= 0:
        return H, 1.0

    # Approximate p-value using chi-square survival function
    # Using Wilson-Hilferty approximation
    p_value = chi2_survival(H, df)

    return H, p_value


def chi2_survival(x, df):
    """Approximate chi-square survival function P(X > x) for df degrees of freedom."""
    if x <= 0:
        return 1.0
    if df <= 0:
        return 0.0
    # Wilson-Hilferty normal approximation
    z = ((x / df)**(1/3) - (1 - 2/(9*df))) / math.sqrt(2/(9*df))
    # Standard normal CDF approximation
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return max(0.0, min(1.0, p))


def mann_whitney_U(group1, group2):
    """Mann-Whitney U test. Returns (U, approximate p-value)."""
    n1, n2 = len(group1), len(group2)
    if n1 == 0 or n2 == 0:
        return 0, 1.0

    all_vals = [(v, 0) for v in group1] + [(v, 1) for v in group2]
    all_vals.sort(key=lambda x: x[0])
    n = len(all_vals)

    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n and all_vals[j][0] == all_vals[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2
        for k_idx in range(i, j):
            ranks[k_idx] = avg_rank
        i = j

    R1 = sum(ranks[i] for i in range(n) if all_vals[i][1] == 0)
    U1 = R1 - n1 * (n1 + 1) / 2
    U2 = n1 * n2 - U1
    U = min(U1, U2)

    # Normal approximation for p-value
    mu = n1 * n2 / 2
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    if sigma == 0:
        return U, 1.0
    z = (U - mu) / sigma
    p = 2 * 0.5 * math.erfc(-z / math.sqrt(2))  # two-tailed
    p = min(p, 1.0)

    return U, p


# ============================================================
# Main Analysis
# ============================================================

def main():
    print("=" * 70)
    print("RANKING-EFFECT EXPERIMENT ANALYSIS")
    print("CivicLens Experiment 1: Algorithmic Ranking Nudge")
    print("=" * 70)
    print()

    # Load all good runs
    runs = {}
    for name in ALL_GOOD_RUNS:
        runs[name] = load_run(name)

    # --------------------------------------------------------
    # 1. DATA OVERVIEW
    # --------------------------------------------------------
    print("1. DATA OVERVIEW")
    print("-" * 50)
    print(f"{'Run':<12} {'Mode':<8} {'Model':<12} {'Feed':<5} {'Posts':>6} {'Comments':>9} {'Treatments':>11}")
    print("-" * 70)

    total_posts = total_comments = total_treatments = 0
    for name in ALL_GOOD_RUNS:
        r = runs[name]
        mode = "A (seed)" if name.startswith("e1a") else "B (all)"
        model = MODEL_TIER.get(name, "unknown")
        feed = FEED_SORT.get(name, "?")
        n_posts = len(r["posts"])
        n_comments = len(r["comments"])
        n_treatments = len(r["treatments"])
        print(f"{name:<12} {mode:<8} {model:<12} {feed:<5} {n_posts:>6} {n_comments:>9} {n_treatments:>11}")
        total_posts += n_posts
        total_comments += n_comments
        total_treatments += n_treatments

    print("-" * 70)
    print(f"{'TOTAL':<38} {total_posts:>6} {total_comments:>9} {total_treatments:>11}")
    print()

    # --------------------------------------------------------
    # 2. TREATMENT ASSIGNMENT BALANCE
    # --------------------------------------------------------
    print("2. TREATMENT ASSIGNMENT BALANCE")
    print("-" * 50)

    # Collect all treatments by mode
    mode_a_treatments = []
    mode_b_treatments = []

    for name in GOOD_RUNS_A:
        mode_a_treatments.extend(runs[name]["treatments"])
    for name in GOOD_RUNS_B:
        mode_b_treatments.extend(runs[name]["treatments"])

    for label, treatments in [("Mode A", mode_a_treatments), ("Mode B", mode_b_treatments)]:
        counts_all = defaultdict(int)
        counts_world = defaultdict(int)
        for t in treatments:
            counts_all[t["treatment"]] += 1
            # Check world post by author name (reliable)
            if t.get("post_author_name", "") == "civiclens_world":
                counts_world[t["treatment"]] += 1
        total_all = sum(counts_all.values())
        total_world = sum(counts_world.values())
        print(f"\n  {label} — All posts (n={total_all}):")
        for treat in ["nudge_up", "control", "nudge_down"]:
            n = counts_all.get(treat, 0)
            pct = (n / total_all * 100) if total_all > 0 else 0
            print(f"    {treat:<12} {n:>4} ({pct:.1f}%)")
        print(f"\n  {label} — World posts only (n={total_world}):")
        for treat in ["nudge_up", "control", "nudge_down"]:
            n = counts_world.get(treat, 0)
            pct = (n / total_world * 100) if total_world > 0 else 0
            print(f"    {treat:<12} {n:>4} ({pct:.1f}%)")
    print()

    # --------------------------------------------------------
    # 3. BUILD ANALYSIS DATASET
    # --------------------------------------------------------
    # Join treatments with posts to get engagement metrics
    # NOTE: is_world_post flag is unreliable in Mode B (only partially set).
    # Instead, identify world posts by author_name == "civiclens_world".

    # For each treatment record, build analysis row
    analysis_rows = []

    for name in ALL_GOOD_RUNS:
        r = runs[name]
        mode = "A" if name.startswith("e1a") else "B"

        # Build post lookup
        post_map = {p["id"]: p for p in r["posts"]}

        # Build comment count per post (from comments data, more accurate)
        comment_counts = defaultdict(int)
        for c in r["comments"]:
            pid = c.get("post_id")
            if pid:
                comment_counts[pid] += 1

        # Build vote counts per post from activity log
        vote_counts = defaultdict(lambda: {"upvotes": 0, "downvotes": 0})
        for a in r["activity"]:
            meta = a.get("metadata", {})
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except:
                    meta = {}
            if a.get("action_type") in ("upvote", "downvote") and "post_id" in meta:
                pid = meta["post_id"]
                if a["action_type"] == "upvote":
                    vote_counts[pid]["upvotes"] += 1
                else:
                    vote_counts[pid]["downvotes"] += 1

        for t in r["treatments"]:
            post_id = t["post_id"]
            post = post_map.get(post_id, {})

            # Get score from treatment record (snapshot at export time)
            score = t.get("post_score", post.get("score", 0)) or 0
            comment_count = comment_counts.get(post_id, t.get("post_comment_count", 0) or 0)

            # Calculate adjusted score (remove nudge vote)
            nudge_applied = t.get("nudge_vote_id") is not None
            treatment = t["treatment"]

            if nudge_applied and treatment == "nudge_up":
                adjusted_score = score - 1
            elif nudge_applied and treatment == "nudge_down":
                adjusted_score = score + 1
            else:
                adjusted_score = score

            # Determine world post by author name (reliable), not flag (unreliable in Mode B)
            post_author = t.get("post_author_name", post.get("author_name", ""))
            is_world = (post_author == "civiclens_world")

            analysis_rows.append({
                "run": name,
                "mode": mode,
                "model": MODEL_TIER.get(name, "unknown"),
                "feed_sort": FEED_SORT.get(name, "unknown"),
                "post_id": post_id,
                "treatment": treatment,
                "is_world_post": is_world,
                "score": score,
                "adjusted_score": adjusted_score,
                "comment_count": comment_count,
                "nudge_applied": nudge_applied,
                "nudge_delay_min": t.get("nudge_delay_minutes"),
                "post_title": t.get("post_title", post.get("title", "")),
                "post_author": post_author,
            })

    # --------------------------------------------------------
    # 3. PRIMARY ANALYSIS — sort=hot RUNS ONLY (ranking visible)
    # --------------------------------------------------------
    print("=" * 70)
    print("3. PRIMARY ANALYSIS — RANKING HYPOTHESIS (sort=hot runs only)")
    print("=" * 70)
    print("   These runs used sort=hot so agents saw hot-ranked feed.")
    print("   Nudge votes actually affected post visibility.")
    print()

    hot_a = [r for r in analysis_rows if r["feed_sort"] == "hot" and r["mode"] == "A" and r["is_world_post"]]
    hot_b = [r for r in analysis_rows if r["feed_sort"] == "hot" and r["mode"] == "B" and r["is_world_post"]]

    for label, data in [("Mode A (seed posts only)", hot_a), ("Mode B (all posts)", hot_b)]:
        print(f"  {label} — World Posts (n={len(data)})")
        print(f"  {'Treatment':<12} {'N':>4} {'Adj.Score':>10} {'Comments':>10} {'Raw Score':>10}")
        print(f"  {'':<12} {'':>4} {'mean±sd':>10} {'mean±sd':>10} {'mean±sd':>10}")
        print(f"  {'-'*52}")

        for treat in ["nudge_up", "control", "nudge_down"]:
            subset = [r for r in data if r["treatment"] == treat]
            n = len(subset)
            adj_scores = [r["adjusted_score"] for r in subset]
            comments = [r["comment_count"] for r in subset]
            raw_scores = [r["score"] for r in subset]
            print(f"  {treat:<12} {n:>4} "
                  f"{safe_mean(adj_scores):>5.2f}±{safe_stdev(adj_scores):<4.2f} "
                  f"{safe_mean(comments):>5.2f}±{safe_stdev(comments):<4.2f} "
                  f"{safe_mean(raw_scores):>5.2f}±{safe_stdev(raw_scores):<4.2f}")
        print()

    # Statistical tests on sort=hot data
    print("  STATISTICAL TESTS (sort=hot only)")
    print("  " + "-" * 50)

    for label, data in [("Mode A", hot_a), ("Mode B", hot_b)]:
        print(f"\n  {label}:")
        print(f"    Kruskal-Wallis H test")
        print(f"    H0: No difference in engagement across treatment groups")

        for metric_name, metric_key in [("Adjusted Score", "adjusted_score"), ("Comment Count", "comment_count")]:
            groups = []
            for treat in ["nudge_up", "control", "nudge_down"]:
                vals = [r[metric_key] for r in data if r["treatment"] == treat]
                groups.append(vals)

            H, p = kruskal_wallis_H(groups)
            f_effect = cohens_f(groups)
            print(f"\n      {metric_name}:")
            print(f"        H = {H:.4f}, p = {p:.4f} {'*' if p < 0.05 else '(ns)'}")
            print(f"        Cohen's f = {f_effect:.4f} ({'small' if f_effect < 0.25 else 'medium' if f_effect < 0.40 else 'large'})")

        # Pairwise
        print(f"\n    Pairwise Mann-Whitney U:")
        for metric_name, metric_key in [("Adjusted Score", "adjusted_score"), ("Comment Count", "comment_count")]:
            control = [r[metric_key] for r in data if r["treatment"] == "control"]
            for treat in ["nudge_up", "nudge_down"]:
                other = [r[metric_key] for r in data if r["treatment"] == treat]
                U, p = mann_whitney_U(other, control)
                d = cohens_d(other, control)
                print(f"      {metric_name}: {treat} vs control — U={U:.1f}, p={p:.4f} {'*' if p < 0.05 else '(ns)'}, d={d:.4f}")

    # Mode A vs Mode B (sort=hot only)
    if hot_a and hot_b:
        print(f"\n  Mode A vs Mode B (sort=hot):")
        a_scores = [r["adjusted_score"] for r in hot_a]
        b_scores = [r["score"] for r in hot_b]
        a_comments = [r["comment_count"] for r in hot_a]
        b_comments = [r["comment_count"] for r in hot_b]

        U, p = mann_whitney_U(a_scores, b_scores)
        d = cohens_d(a_scores, b_scores)
        print(f"    Score: U={U:.1f}, p={p:.4f}, d={d:.4f}")
        U, p = mann_whitney_U(a_comments, b_comments)
        d = cohens_d(a_comments, b_comments)
        print(f"    Comments: U={U:.1f}, p={p:.4f}, d={d:.4f}")

    # sort=hot vs sort=new comparison (same models)
    print(f"\n  sort=hot vs sort=new COMPARISON (same models, world posts only):")
    for model_name in SORT_HOT_RUNS:
        hot_model = [r for r in analysis_rows if r["model"] == model_name and r["feed_sort"] == "hot" and r["is_world_post"]]
        new_model = [r for r in analysis_rows if r["model"] == model_name and r["feed_sort"] == "new" and r["is_world_post"]]
        if hot_model and new_model:
            for metric_name, metric_key in [("Score", "adjusted_score"), ("Comments", "comment_count")]:
                hot_vals = [r[metric_key] for r in hot_model]
                new_vals = [r[metric_key] for r in new_model]
                U, p = mann_whitney_U(hot_vals, new_vals)
                d = cohens_d(hot_vals, new_vals)
                print(f"    {model_name} {metric_name}: hot={safe_mean(hot_vals):.2f} vs new={safe_mean(new_vals):.2f}, p={p:.4f}, d={d:.4f}")

    print()

    # --------------------------------------------------------
    # 4. SECONDARY — ALL RUNS (sort=new + sort=hot combined)
    # --------------------------------------------------------
    print("4. ALL RUNS COMBINED (for reference)")
    print("-" * 50)

    world_a = [r for r in analysis_rows if r["mode"] == "A" and r["is_world_post"]]
    world_b = [r for r in analysis_rows if r["mode"] == "B" and r["is_world_post"]]

    for label, data in [("Mode A", world_a), ("Mode B", world_b)]:
        print(f"\n  {label} — World Posts (n={len(data)})")
        print(f"  {'Treatment':<12} {'N':>4} {'Adj.Score':>10} {'Comments':>10}")
        for treat in ["nudge_up", "control", "nudge_down"]:
            subset = [r for r in data if r["treatment"] == treat]
            n = len(subset)
            adj_scores = [r["adjusted_score"] for r in subset]
            comments = [r["comment_count"] for r in subset]
            print(f"  {treat:<12} {n:>4} {safe_mean(adj_scores):>5.2f}±{safe_stdev(adj_scores):<4.2f} {safe_mean(comments):>5.2f}±{safe_stdev(comments):<4.2f}")

    print()

    # --------------------------------------------------------
    # 6. PER-RUN CONSISTENCY CHECK
    # --------------------------------------------------------
    print("5. PER-RUN CONSISTENCY")
    print("-" * 50)
    print(f"\n  {'Run':<12} {'Model':<12} {'Feed':<5} {'N(world)':>9} {'Avg Score':>10} {'Avg Comments':>13}")
    print(f"  {'-'*65}")

    for name in ALL_GOOD_RUNS:
        world = [r for r in analysis_rows if r["run"] == name and r["is_world_post"]]
        n = len(world)
        avg_s = safe_mean([r["adjusted_score"] if r["mode"] == "A" else r["score"] for r in world])
        avg_c = safe_mean([r["comment_count"] for r in world])
        model = MODEL_TIER.get(name, "unknown")
        feed = FEED_SORT.get(name, "?")
        print(f"  {name:<12} {model:<12} {feed:<5} {n:>9} {avg_s:>10.2f} {avg_c:>13.2f}")

    print()

    # --------------------------------------------------------
    # 7. AGENT PARTICIPATION
    # --------------------------------------------------------
    print("6. AGENT PARTICIPATION")
    print("-" * 50)

    for name in ALL_GOOD_RUNS:
        r = runs[name]
        agent_comments = defaultdict(int)
        for c in r["comments"]:
            agent_comments[c.get("author_name", "unknown")] += 1

        agents_active = len([a for a in agent_comments if a.startswith("ranking_")])
        total_c = sum(agent_comments.values())

        print(f"  {name}: {agents_active}/10 agents active, {total_c} total comments")

    print()

    # --------------------------------------------------------
    # 8. MODEL COMPARISON (all models)
    # --------------------------------------------------------
    print("7. MODEL COMPARISON")
    print("-" * 50)

    model_world_data = {}  # model_name -> list of world rows

    for model_name in ALL_MODELS:
        model_rows = [r for r in analysis_rows if r["model"] == model_name]
        model_world = [r for r in model_rows if r["is_world_post"]]
        model_agent = [r for r in model_rows if not r["is_world_post"]]
        all_posts_this_model = sum(len(runs[name]["posts"]) for name in ALL_GOOD_RUNS if MODEL_TIER.get(name) == model_name)
        all_comments_this_model = sum(len(runs[name]["comments"]) for name in ALL_GOOD_RUNS if MODEL_TIER.get(name) == model_name)
        n_runs = len([n for n in ALL_GOOD_RUNS if MODEL_TIER.get(n) == model_name])
        heartbeat = RUNS_BY_MODEL[model_name]["heartbeat"]

        scores = [r["adjusted_score"] if r["mode"] == "A" else r["score"] for r in model_world]
        comments = [r["comment_count"] for r in model_world]

        model_world_data[model_name] = model_world

        print(f"\n  {model_name} ({n_runs} runs, heartbeat={heartbeat}):")
        print(f"    Total posts: {all_posts_this_model}, Total comments: {all_comments_this_model}")
        print(f"    Treated posts: {len(model_rows)} ({len(model_world)} world, {len(model_agent)} agent)")
        if model_world:
            print(f"    World post avg score: {safe_mean(scores):.2f} ± {safe_stdev(scores):.2f}")
            print(f"    World post avg comments: {safe_mean(comments):.2f} ± {safe_stdev(comments):.2f}")

    # Kruskal-Wallis across all models on world posts
    print(f"\n  Cross-model Kruskal-Wallis (world posts):")
    for metric_name, metric_key in [("Score", "adjusted_score"), ("Comments", "comment_count")]:
        groups = []
        group_labels = []
        for model_name in ALL_MODELS:
            mw = model_world_data.get(model_name, [])
            if mw:
                if metric_key == "adjusted_score":
                    vals = [r["adjusted_score"] if r["mode"] == "A" else r["score"] for r in mw]
                else:
                    vals = [r[metric_key] for r in mw]
                groups.append(vals)
                group_labels.append(model_name)

        if len(groups) >= 2:
            H, p = kruskal_wallis_H(groups)
            f_effect = cohens_f(groups)
            print(f"    {metric_name}: H={H:.4f}, p={p:.4f} {'*' if p < 0.05 else '(ns)'}, f={f_effect:.4f}")

    # Pairwise comparisons (each model vs kimi-k2.5 baseline)
    baseline = "kimi-k2.5"
    baseline_world = model_world_data.get(baseline, [])
    if baseline_world:
        print(f"\n  Pairwise vs {baseline} (world posts, Mann-Whitney U):")
        print(f"  {'Model':<14} {'Metric':<10} {'Mean':>6} {'vs':>4} {'Base':>6} {'U':>8} {'p':>8} {'d':>8}")
        print(f"  {'-'*66}")
        for model_name in ALL_MODELS:
            if model_name == baseline:
                continue
            mw = model_world_data.get(model_name, [])
            if not mw:
                continue
            for metric_name, metric_key in [("Score", "adjusted_score"), ("Comments", "comment_count")]:
                if metric_key == "adjusted_score":
                    base_vals = [r["adjusted_score"] if r["mode"] == "A" else r["score"] for r in baseline_world]
                    other_vals = [r["adjusted_score"] if r["mode"] == "A" else r["score"] for r in mw]
                else:
                    base_vals = [r[metric_key] for r in baseline_world]
                    other_vals = [r[metric_key] for r in mw]
                U, p = mann_whitney_U(other_vals, base_vals)
                d = cohens_d(other_vals, base_vals)
                sig = "*" if p < 0.05 else ""
                print(f"  {model_name:<14} {metric_name:<10} {safe_mean(other_vals):>6.2f} {'vs':>4} {safe_mean(base_vals):>6.2f} {U:>8.1f} {p:>7.4f}{sig} {d:>7.4f}")

    print()

    # --------------------------------------------------------
    # 9. SUMMARY & CONCLUSIONS
    # --------------------------------------------------------
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Get treatment effect from sort=hot runs (the valid ones)
    hot_up = [r["comment_count"] for r in hot_a if r["treatment"] == "nudge_up"]
    hot_ctrl = [r["comment_count"] for r in hot_a if r["treatment"] == "control"]
    hot_down = [r["comment_count"] for r in hot_a if r["treatment"] == "nudge_down"]

    n_runs_total = len(ALL_GOOD_RUNS)
    n_hot_runs = len(ALL_HOT_RUNS)

    print(f"""
  Experiment: CivicLens Ranking-Effect
  Total runs: {len(GOOD_RUNS_A)} Mode A + {len(GOOD_RUNS_B)} Mode B = {n_runs_total} total
    - sort=new (ranking invisible): {n_runs_total - n_hot_runs} runs
    - sort=hot (ranking visible):   {n_hot_runs} runs (PRIMARY)

  Data collected:
    - {total_posts} posts, {total_comments} comments across {n_runs_total} runs
    - {len(hot_a)} world posts in sort=hot Mode A, {len(hot_b)} in sort=hot Mode B

  Key findings (sort=hot, Mode A — nudge applied):
    - nudge_up:   avg {safe_mean(hot_up):.1f} comments/post (n={len(hot_up)})
    - control:    avg {safe_mean(hot_ctrl):.1f} comments/post (n={len(hot_ctrl)})
    - nudge_down: avg {safe_mean(hot_down):.1f} comments/post (n={len(hot_down)})
""")

    # --------------------------------------------------------
    # 10. EXPORT ANALYSIS CSV
    # --------------------------------------------------------
    csv_path = Path(__file__).parent / "analysis_data.csv"
    with open(csv_path, "w") as f:
        headers = ["run", "mode", "model", "feed_sort", "post_id", "treatment", "is_world_post",
                   "score", "adjusted_score", "comment_count", "nudge_applied",
                   "nudge_delay_min", "post_author", "post_title"]
        f.write(",".join(headers) + "\n")
        for row in analysis_rows:
            vals = [str(row.get(h, "")) for h in headers]
            # Escape commas and quotes in all fields
            vals = [f'"{v.replace(chr(34), chr(34)+chr(34))}"' if "," in v or '"' in v else v for v in vals]
            f.write(",".join(vals) + "\n")

    print(f"  Analysis data exported to: {csv_path}")
    print(f"  ({len(analysis_rows)} rows)")
    print()


if __name__ == "__main__":
    main()
