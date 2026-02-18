#!/usr/bin/env python3
"""
Ranking-Effect Experiment Analysis
===================================
Analyzes CivicLens Experiment 1: Does algorithmic ranking nudge
affect organic engagement on AI-agent social media?

Mode A: Posts randomly assigned to nudge_up / control / nudge_down
        (actual ranking manipulation via synthetic votes)
Mode B: Posts randomly assigned but NO nudge applied (baseline)

Usable runs: e1a-run01..03 (Mode A), e1b-run01..03 (Mode B)
"""

import json
import os
import sys
from pathlib import Path
from collections import defaultdict
import statistics
import math

EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"

GOOD_RUNS_A = ["e1a-run01", "e1a-run02", "e1a-run03"]
GOOD_RUNS_B = ["e1b-run01", "e1b-run02", "e1b-run03"]
ALL_GOOD_RUNS = GOOD_RUNS_A + GOOD_RUNS_B


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
    print(f"{'Run':<12} {'Mode':<8} {'Posts':>6} {'Comments':>9} {'Activity':>9} {'Treatments':>11}")
    print("-" * 60)

    total_posts = total_comments = total_activity = total_treatments = 0
    for name in ALL_GOOD_RUNS:
        r = runs[name]
        mode = "A (nudge)" if name.startswith("e1a") else "B (ctrl)"
        n_posts = len(r["posts"])
        n_comments = len(r["comments"])
        n_activity = len(r["activity"])
        n_treatments = len(r["treatments"])
        print(f"{name:<12} {mode:<8} {n_posts:>6} {n_comments:>9} {n_activity:>9} {n_treatments:>11}")
        total_posts += n_posts
        total_comments += n_comments
        total_activity += n_activity
        total_treatments += n_treatments

    print("-" * 60)
    print(f"{'TOTAL':<21} {total_posts:>6} {total_comments:>9} {total_activity:>9} {total_treatments:>11}")
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
    # 4. ENGAGEMENT BY TREATMENT (Mode A only - where nudge applied)
    # --------------------------------------------------------
    print("3. ENGAGEMENT BY TREATMENT GROUP")
    print("-" * 50)

    # Filter to world posts only (agent posts are confounds)
    world_a = [r for r in analysis_rows if r["mode"] == "A" and r["is_world_post"]]
    world_b = [r for r in analysis_rows if r["mode"] == "B" and r["is_world_post"]]

    print(f"\n  Mode A — World Posts Only (n={len(world_a)})")
    print(f"  {'Treatment':<12} {'N':>4} {'Adj.Score':>10} {'Comments':>10} {'Raw Score':>10}")
    print(f"  {'':<12} {'':>4} {'mean±sd':>10} {'mean±sd':>10} {'mean±sd':>10}")
    print(f"  {'-'*52}")

    for treat in ["nudge_up", "control", "nudge_down"]:
        subset = [r for r in world_a if r["treatment"] == treat]
        n = len(subset)
        adj_scores = [r["adjusted_score"] for r in subset]
        comments = [r["comment_count"] for r in subset]
        raw_scores = [r["score"] for r in subset]

        print(f"  {treat:<12} {n:>4} "
              f"{safe_mean(adj_scores):>5.2f}±{safe_stdev(adj_scores):<4.2f} "
              f"{safe_mean(comments):>5.2f}±{safe_stdev(comments):<4.2f} "
              f"{safe_mean(raw_scores):>5.2f}±{safe_stdev(raw_scores):<4.2f}")

    print(f"\n  Mode B — World Posts Only (n={len(world_b)}) [No nudge applied]")
    print(f"  {'Treatment':<12} {'N':>4} {'Score':>10} {'Comments':>10}")
    print(f"  {'':<12} {'':>4} {'mean±sd':>10} {'mean±sd':>10}")
    print(f"  {'-'*42}")

    for treat in ["nudge_up", "control", "nudge_down"]:
        subset = [r for r in world_b if r["treatment"] == treat]
        n = len(subset)
        scores = [r["score"] for r in subset]
        comments = [r["comment_count"] for r in subset]

        print(f"  {treat:<12} {n:>4} "
              f"{safe_mean(scores):>5.2f}±{safe_stdev(scores):<4.2f} "
              f"{safe_mean(comments):>5.2f}±{safe_stdev(comments):<4.2f}")

    print()

    # --------------------------------------------------------
    # 5. STATISTICAL TESTS
    # --------------------------------------------------------
    print("4. STATISTICAL TESTS")
    print("-" * 50)

    # Mode A: Kruskal-Wallis across 3 treatment groups
    print("\n  a) Kruskal-Wallis H test (Mode A world posts)")
    print("     H0: No difference in engagement across treatment groups")

    for metric_name, metric_key in [("Adjusted Score", "adjusted_score"), ("Comment Count", "comment_count")]:
        groups = []
        for treat in ["nudge_up", "control", "nudge_down"]:
            vals = [r[metric_key] for r in world_a if r["treatment"] == treat]
            groups.append(vals)

        H, p = kruskal_wallis_H(groups)
        f_effect = cohens_f(groups)
        print(f"\n     {metric_name}:")
        print(f"       H = {H:.4f}, p = {p:.4f} {'*' if p < 0.05 else '(ns)'}")
        print(f"       Cohen's f = {f_effect:.4f} ({'small' if f_effect < 0.25 else 'medium' if f_effect < 0.40 else 'large'})")

    # Mode A: Pairwise Mann-Whitney (nudge_up vs control, nudge_down vs control)
    print("\n  b) Pairwise comparisons — Mann-Whitney U (Mode A)")

    for metric_name, metric_key in [("Adjusted Score", "adjusted_score"), ("Comment Count", "comment_count")]:
        control = [r[metric_key] for r in world_a if r["treatment"] == "control"]

        for treat in ["nudge_up", "nudge_down"]:
            other = [r[metric_key] for r in world_a if r["treatment"] == treat]
            U, p = mann_whitney_U(other, control)
            d = cohens_d(other, control)
            print(f"\n     {metric_name}: {treat} vs control")
            print(f"       U = {U:.1f}, p = {p:.4f} {'*' if p < 0.05 else '(ns)'}")
            print(f"       Cohen's d = {d:.4f} ({'small' if abs(d) < 0.5 else 'medium' if abs(d) < 0.8 else 'large'})")

    # Mode A vs Mode B comparison
    print("\n  c) Mode A vs Mode B comparison (treatment effect)")
    print("     Does applying nudge votes change engagement vs. label-only?")

    a_scores = [r["adjusted_score"] for r in world_a]
    b_scores = [r["score"] for r in world_b]
    a_comments = [r["comment_count"] for r in world_a]
    b_comments = [r["comment_count"] for r in world_b]

    U, p = mann_whitney_U(a_scores, b_scores)
    d = cohens_d(a_scores, b_scores)
    print(f"\n     Score: U = {U:.1f}, p = {p:.4f}, Cohen's d = {d:.4f}")

    U, p = mann_whitney_U(a_comments, b_comments)
    d = cohens_d(a_comments, b_comments)
    print(f"     Comments: U = {U:.1f}, p = {p:.4f}, Cohen's d = {d:.4f}")

    print()

    # --------------------------------------------------------
    # 6. PER-RUN CONSISTENCY CHECK
    # --------------------------------------------------------
    print("5. PER-RUN CONSISTENCY")
    print("-" * 50)
    print(f"\n  {'Run':<12} {'N(world)':>9} {'Avg Score':>10} {'Avg Comments':>13}")
    print(f"  {'-'*48}")

    for name in ALL_GOOD_RUNS:
        world = [r for r in analysis_rows if r["run"] == name and r["is_world_post"]]
        n = len(world)
        avg_s = safe_mean([r["adjusted_score"] if r["mode"] == "A" else r["score"] for r in world])
        avg_c = safe_mean([r["comment_count"] for r in world])
        print(f"  {name:<12} {n:>9} {avg_s:>10.2f} {avg_c:>13.2f}")

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
    # 8. POWER ANALYSIS
    # --------------------------------------------------------
    print("7. POWER ANALYSIS (Post-Hoc Sensitivity)")
    print("-" * 50)

    # How many world posts per treatment group?
    for label, data in [("Mode A", world_a), ("Mode B", world_b)]:
        per_group = defaultdict(int)
        for r in data:
            per_group[r["treatment"]] += 1
        min_n = min(per_group.values()) if per_group else 0
        total_n = sum(per_group.values())

        # For 3 groups, minimum detectable effect at alpha=0.05, power=0.80
        # Using approximation: n_per_group ≈ (z_alpha + z_beta)^2 / f^2 * (k/(k-1))
        # For power=0.80, alpha=0.05: (1.96 + 0.84)^2 = 7.84
        # With 3 groups: min detectable f = sqrt(7.84 * 2 / (3 * min_n))
        if min_n > 0:
            min_f = math.sqrt(7.84 * 2 / (3 * min_n))
        else:
            min_f = float('inf')

        print(f"\n  {label}: {total_n} world posts ({', '.join(f'{t}={n}' for t, n in sorted(per_group.items()))})")
        print(f"    Min group size: {min_n}")
        print(f"    Minimum detectable Cohen's f at 80% power: {min_f:.3f}")
        print(f"    Interpretation: Can detect {'large' if min_f > 0.40 else 'medium-to-large' if min_f > 0.25 else 'medium' if min_f > 0.10 else 'small'} effects")

    # Needed sample per pilot power analysis
    print(f"\n  Target from pilot power analysis: f=0.229, need 187 posts/group")
    print(f"  Current: ~{min_n} posts/group → underpowered for pilot effect size")
    print(f"  Recommendation: Re-run failed experiments after adding OpenRouter credits")

    print()

    # --------------------------------------------------------
    # 9. SUMMARY & CONCLUSIONS
    # --------------------------------------------------------
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    # Get overall treatment effect
    nudge_up_comments = [r["comment_count"] for r in world_a if r["treatment"] == "nudge_up"]
    control_comments = [r["comment_count"] for r in world_a if r["treatment"] == "control"]
    nudge_down_comments = [r["comment_count"] for r in world_a if r["treatment"] == "nudge_down"]

    print(f"""
  Experiment: CivicLens Ranking-Effect (Tier 1)
  Runs completed: 3 Mode A + 3 Mode B (6 of 12; runs 04-07 failed due to
                  OpenRouter credit exhaustion at $492/$500 limit)

  Data collected:
    - {total_posts} posts, {total_comments} comments across 6 runs
    - {len(world_a)} world posts in Mode A, {len(world_b)} in Mode B
    - 10 AI agents per run (kimi-k2.5 via OpenRouter)

  Key findings (Mode A — nudge applied):
    - nudge_up:   avg {safe_mean(nudge_up_comments):.1f} comments/post (n={len(nudge_up_comments)})
    - control:    avg {safe_mean(control_comments):.1f} comments/post (n={len(control_comments)})
    - nudge_down: avg {safe_mean(nudge_down_comments):.1f} comments/post (n={len(nudge_down_comments)})

  Limitations:
    - Underpowered: ~{min_n} posts/group vs. 187 needed (pilot power analysis)
    - 6 of 12 runs unusable (OpenRouter credits depleted)
    - Single model (kimi-k2.5) — no model diversity
    - 1-hour runs (shorter than planned 3-hour)

  Next steps:
    1. Add OpenRouter credits and re-run 6 failed experiments
    2. Consider longer run duration (2-3h) for more posts per run
    3. Consider reducing heartbeat frequency to lower API costs
""")

    # --------------------------------------------------------
    # 10. EXPORT ANALYSIS CSV
    # --------------------------------------------------------
    csv_path = Path(__file__).parent / "analysis_data.csv"
    with open(csv_path, "w") as f:
        headers = ["run", "mode", "post_id", "treatment", "is_world_post",
                   "score", "adjusted_score", "comment_count", "nudge_applied",
                   "nudge_delay_min", "post_author", "post_title"]
        f.write(",".join(headers) + "\n")
        for row in analysis_rows:
            vals = [str(row.get(h, "")) for h in headers]
            # Escape commas in title
            vals[-1] = f'"{vals[-1]}"'
            f.write(",".join(vals) + "\n")

    print(f"  Analysis data exported to: {csv_path}")
    print(f"  ({len(analysis_rows)} rows)")
    print()


if __name__ == "__main__":
    main()
