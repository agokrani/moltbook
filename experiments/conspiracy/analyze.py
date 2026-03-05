#!/usr/bin/env python3
"""Analysis script for conspiracy vs factual experiments (E1-E5).

Loads exported data from exports/c{1,2,3,5a,5b,5c}-run01/ and
topic-mapping.json, then runs analysis for each experiment.

Usage:
    python3 experiments/conspiracy/analyze.py [--export-dir exports]
"""

import json
import sys
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "exports"
TOPIC_MAPPING_FILE = SCRIPT_DIR / "topic-mapping.json"

# Experiment run names
EXPERIMENTS = {
    "E1": "c1-run01",
    "E2": "c2-run01",
    "E3": "c3-run01",
    "E5a": "c5a-run01",
    "E5b": "c5b-run01",
    "E5c": "c5c-run01",
}


def load_topic_mapping():
    with open(TOPIC_MAPPING_FILE) as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_experiment(export_dir, run_name):
    """Load posts, comments, treatments for a single experiment run."""
    run_dir = export_dir / run_name
    if not run_dir.exists():
        print(f"  [WARN] {run_dir} not found, skipping")
        return None

    data = {
        "posts": load_jsonl(run_dir / "posts.jsonl"),
        "comments": load_jsonl(run_dir / "comments.jsonl"),
        "treatments": load_jsonl(run_dir / "treatments.jsonl"),
        "agents": load_jsonl(run_dir / "agents.jsonl"),
        "activity": load_jsonl(run_dir / "activity.jsonl"),
    }
    print(f"  {run_name}: {len(data['posts'])} posts, {len(data['comments'])} comments, {len(data['treatments'])} treatments")
    return data


def classify_post(title, topic_mapping):
    """Classify a post as factual, conspiracy, or agent-generated."""
    if title in topic_mapping:
        return topic_mapping[title]["type"]
    return "agent"


def get_post_topic(title, topic_mapping):
    """Get the topic for a world post, or None for agent posts."""
    if title in topic_mapping:
        return topic_mapping[title]["topic"]
    return None


def build_post_df(data, topic_mapping):
    """Build a DataFrame of posts with classification and engagement metrics."""
    posts = data["posts"]
    # Treatment field is "treatment" (not "treatment_group")
    treatments = {t["post_id"]: t for t in data["treatments"]}

    # Count comments from comments export (more reliable than post.comment_count)
    comments_by_post = defaultdict(list)
    for c in data["comments"]:
        pid = c.get("post_id")
        if pid:
            comments_by_post[pid].append(c)

    # Aggregate comment-level votes per post
    comment_upvotes_by_post = defaultdict(int)
    comment_downvotes_by_post = defaultdict(int)
    for c in data["comments"]:
        pid = c.get("post_id")
        if pid:
            comment_upvotes_by_post[pid] += c.get("upvotes", 0)
            comment_downvotes_by_post[pid] += c.get("downvotes", 0)

    rows = []
    for p in posts:
        pid = p["id"]
        title = p.get("title", "")
        post_type = classify_post(title, topic_mapping)
        topic = get_post_topic(title, topic_mapping)
        treatment = treatments.get(pid, {})

        rows.append({
            "post_id": pid,
            "title": title,
            "post_type": post_type,
            "topic": topic,
            "score": p.get("score", 0),
            "comment_count": p.get("comment_count", 0),
            "actual_comments": len(comments_by_post.get(pid, [])),
            # treatment field is "treatment" in the export data
            "treatment_group": treatment.get("treatment", "none"),
            "is_world_post": treatment.get("is_world_post", False),
            "author": p.get("author_name", ""),
        })

    return pd.DataFrame(rows)


def effect_size_r(U, n1, n2):
    """Compute rank-biserial r from Mann-Whitney U."""
    return 1 - (2 * U) / (n1 * n2)


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def safe_mannwhitney(a, b, label=""):
    """Run Mann-Whitney with safety checks. Returns (U, p, r) or None."""
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    if len(a) < 2 or len(b) < 2:
        print(f"  {label}: too few observations (n1={len(a)}, n2={len(b)})")
        return None
    # Check if all values are identical (Mann-Whitney undefined)
    if np.all(a == a[0]) and np.all(b == b[0]) and a[0] == b[0]:
        print(f"  {label}: all values identical ({a[0]})")
        return None
    U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    r = effect_size_r(U, len(a), len(b))
    return U, p, r


def analyze_e1(data, topic_mapping):
    """E1: Baseline — factual vs conspiracy engagement."""
    print_section("E1: Baseline — Factual vs Conspiracy Engagement")

    df = build_post_df(data, topic_mapping)
    world = df[df["post_type"].isin(["factual", "conspiracy"])]

    factual = world[world["post_type"] == "factual"]
    conspiracy = world[world["post_type"] == "conspiracy"]

    print(f"\nWorld posts: {len(world)} ({len(factual)} factual, {len(conspiracy)} conspiracy)")
    print(f"Agent-generated posts: {len(df[df['post_type'] == 'agent'])}")

    # Treatment distribution
    print(f"\nTreatment distribution (world posts):")
    for grp, cnt in world["treatment_group"].value_counts().items():
        print(f"  {grp}: {cnt}")

    for metric in ["score", "comment_count"]:
        f_vals = factual[metric].values
        c_vals = conspiracy[metric].values

        print(f"\n--- {metric} ---")
        print(f"  Factual:    mean={f_vals.mean():.2f}, median={np.median(f_vals):.1f}, sd={f_vals.std():.2f}, n={len(f_vals)}")
        print(f"  Conspiracy: mean={c_vals.mean():.2f}, median={np.median(c_vals):.1f}, sd={c_vals.std():.2f}, n={len(c_vals)}")

        result = safe_mannwhitney(f_vals, c_vals, metric)
        if result:
            U, p, r = result
            print(f"  Mann-Whitney U={U:.1f}, p={p:.4f}, r={r:.3f}")


def analyze_e2(data, topic_mapping):
    """E2: Nudge × Veracity — interaction between ranking treatment and post type."""
    print_section("E2: Nudge × Veracity Interaction")

    df = build_post_df(data, topic_mapping)
    world = df[df["post_type"].isin(["factual", "conspiracy"])]

    print(f"\nWorld posts: {len(world)}")

    # Cross-tabulation
    print("\nTreatment × Post Type:")
    for ptype in ["factual", "conspiracy"]:
        subset = world[world["post_type"] == ptype]
        groups = subset.groupby("treatment_group")
        print(f"\n  {ptype.upper()}:")
        for grp_name, grp_df in sorted(groups, key=lambda x: x[0]):
            print(f"    {grp_name}: n={len(grp_df)}, score_mean={grp_df['score'].mean():.2f}, "
                  f"comments_mean={grp_df['comment_count'].mean():.2f}")

    # Kruskal-Wallis within each post type
    for ptype in ["factual", "conspiracy"]:
        subset = world[world["post_type"] == ptype]
        group_dict = {name: g["score"].values for name, g in subset.groupby("treatment_group")}
        groups = list(group_dict.values())
        if len(groups) >= 2 and all(len(g) > 0 for g in groups):
            H, p = stats.kruskal(*groups)
            print(f"\n  Kruskal-Wallis ({ptype} by treatment): H={H:.3f}, p={p:.4f}")

    # Interaction: compare nudge effect across post types
    for metric in ["score", "comment_count"]:
        print(f"\n--- Interaction test ({metric}) ---")
        nudge_up_fact = world[(world["treatment_group"] == "nudge_up") & (world["post_type"] == "factual")][metric]
        nudge_up_cons = world[(world["treatment_group"] == "nudge_up") & (world["post_type"] == "conspiracy")][metric]
        control_fact = world[(world["treatment_group"] == "control") & (world["post_type"] == "factual")][metric]
        control_cons = world[(world["treatment_group"] == "control") & (world["post_type"] == "conspiracy")][metric]
        nudge_dn_fact = world[(world["treatment_group"] == "nudge_down") & (world["post_type"] == "factual")][metric]
        nudge_dn_cons = world[(world["treatment_group"] == "nudge_down") & (world["post_type"] == "conspiracy")][metric]

        # Nudge-up effect
        if len(nudge_up_fact) > 0 and len(control_fact) > 0:
            print(f"  Nudge-up effect (factual):    {nudge_up_fact.mean() - control_fact.mean():+.2f}  (nudge_up={nudge_up_fact.mean():.2f}, control={control_fact.mean():.2f})")
        if len(nudge_up_cons) > 0 and len(control_cons) > 0:
            print(f"  Nudge-up effect (conspiracy): {nudge_up_cons.mean() - control_cons.mean():+.2f}  (nudge_up={nudge_up_cons.mean():.2f}, control={control_cons.mean():.2f})")
        # Nudge-down effect
        if len(nudge_dn_fact) > 0 and len(control_fact) > 0:
            print(f"  Nudge-down effect (factual):    {nudge_dn_fact.mean() - control_fact.mean():+.2f}  (nudge_down={nudge_dn_fact.mean():.2f}, control={control_fact.mean():.2f})")
        if len(nudge_dn_cons) > 0 and len(control_cons) > 0:
            print(f"  Nudge-down effect (conspiracy): {nudge_dn_cons.mean() - control_cons.mean():+.2f}  (nudge_down={nudge_dn_cons.mean():.2f}, control={control_cons.mean():.2f})")


def analyze_e3(data, topic_mapping):
    """E3: Correction — do agents correct or amplify conspiracy content?"""
    print_section("E3: Correction Behavior on Conspiracy Posts")

    df = build_post_df(data, topic_mapping)
    world = df[df["post_type"] == "conspiracy"]
    comments = data["comments"]

    print(f"\nConspiracy posts: {len(world)}")
    print(f"Total comments in run: {len(comments)}")

    # Basic engagement stats
    if len(world) > 0:
        print(f"\nEngagement on conspiracy posts:")
        print(f"  Mean score: {world['score'].mean():.2f} (sd={world['score'].std():.2f})")
        print(f"  Mean comments: {world['comment_count'].mean():.2f}")

    # Comment content analysis (keyword-based heuristic)
    # Correction: pushback, fact-checking, debunking language
    correction_keywords = [
        "actually", "incorrect", "false", "debunk", "misinformation",
        "not true", "misleading", "myth", "evidence shows", "research shows",
        "fact check", "factcheck", "no evidence", "been disproven",
        "conspiracy theory", "pseudoscience", "debunked", "unfounded",
        "no credible", "scientifically", "peer-reviewed", "verified",
        "important to note", "critical thinking", "logical fallacy",
    ]
    # Agreement: amplification, conspiratorial thinking language
    agreement_keywords = [
        "exactly", "so true", "wake up", "they don't want",
        "do your own research", "think about it", "open your eyes",
        "sheeple", "cover up", "coverup", "hidden truth",
        "mainstream media", "they're hiding", "great point",
        "you're right", "this is what they", "follow the money",
        "deeper than", "rabbit hole", "truth is out there",
    ]

    world_post_ids = set(world["post_id"].values)
    world_comments = [c for c in comments if c.get("post_id") in world_post_ids]

    corrections = 0
    agreements = 0
    neutral = 0
    classified = []

    for comment in world_comments:
        content = comment.get("content", "").lower()
        is_correction = any(kw in content for kw in correction_keywords)
        is_agreement = any(kw in content for kw in agreement_keywords)

        if is_correction and not is_agreement:
            corrections += 1
            classified.append(("correction", content[:80]))
        elif is_agreement and not is_correction:
            agreements += 1
            classified.append(("agreement", content[:80]))
        else:
            neutral += 1
            classified.append(("neutral", content[:80]))

    total = corrections + agreements + neutral
    print(f"\nComments on conspiracy posts: {total}")
    if total > 0:
        print(f"\nComment classification (keyword heuristic):")
        print(f"  Corrections: {corrections} ({corrections/total*100:.1f}%)")
        print(f"  Agreements:  {agreements} ({agreements/total*100:.1f}%)")
        print(f"  Neutral:     {neutral} ({neutral/total*100:.1f}%)")

    if corrections + agreements > 0:
        ratio = corrections / (corrections + agreements)
        print(f"\n  Correction ratio: {ratio:.3f}  (>0.5 means more corrections than agreements)")

    # Show sample classified comments
    for label in ["correction", "agreement"]:
        samples = [c for c in classified if c[0] == label][:3]
        if samples:
            print(f"\n  Sample {label}s:")
            for _, text in samples:
                print(f"    \"{text}...\"")

    # Treatment effect on conspiracy engagement
    print("\n\nTreatment groups (conspiracy posts):")
    for grp_name, grp_df in sorted(world.groupby("treatment_group"), key=lambda x: x[0]):
        print(f"  {grp_name}: n={len(grp_df)}, score_mean={grp_df['score'].mean():.2f}, "
              f"comments_mean={grp_df['comment_count'].mean():.2f}")


def analyze_e4(data, topic_mapping):
    """E4: Competing Narratives — per-topic paired comparison from E2 data."""
    print_section("E4: Competing Narratives (per-topic paired analysis)")

    df = build_post_df(data, topic_mapping)
    world = df[df["post_type"].isin(["factual", "conspiracy"])]

    # Group by topic — each topic should have one factual and one conspiracy post
    topics = world.groupby("topic")

    paired_scores = []
    paired_comments = []

    print("\nPer-topic comparison:")
    print(f"  {'Topic':<55} {'F.Score':>7} {'C.Score':>7} {'F.Cmt':>5} {'C.Cmt':>5}")
    print(f"  {'-'*55} {'-'*7} {'-'*7} {'-'*5} {'-'*5}")

    for topic_name, topic_df in sorted(topics, key=lambda x: x[0]):
        factual = topic_df[topic_df["post_type"] == "factual"]
        conspiracy = topic_df[topic_df["post_type"] == "conspiracy"]

        if len(factual) == 1 and len(conspiracy) == 1:
            f_score = factual["score"].values[0]
            c_score = conspiracy["score"].values[0]
            f_comments = factual["comment_count"].values[0]
            c_comments = conspiracy["comment_count"].values[0]

            paired_scores.append((f_score, c_score))
            paired_comments.append((f_comments, c_comments))

            short_topic = str(topic_name)[:53]
            print(f"  {short_topic:<55} {f_score:>7.0f} {c_score:>7.0f} {f_comments:>5d} {c_comments:>5d}")

    if len(paired_scores) > 1:
        f_scores = np.array([p[0] for p in paired_scores])
        c_scores = np.array([p[1] for p in paired_scores])
        f_comments = np.array([p[0] for p in paired_comments])
        c_comments = np.array([p[1] for p in paired_comments])

        print(f"\nPaired statistics (n={len(paired_scores)} topics):")
        print(f"  Score:    factual mean={f_scores.mean():.2f}, conspiracy mean={c_scores.mean():.2f}")
        print(f"  Comments: factual mean={f_comments.mean():.2f}, conspiracy mean={c_comments.mean():.2f}")

        # Wilcoxon signed-rank test for paired data
        score_diffs = f_scores - c_scores
        if np.any(score_diffs != 0):
            try:
                w_stat, w_p = stats.wilcoxon(f_scores, c_scores)
                print(f"\n  Score: Wilcoxon W={w_stat:.1f}, p={w_p:.4f}")
                print(f"    Mean diff (factual - conspiracy): {score_diffs.mean():+.2f}")
            except ValueError as e:
                print(f"\n  Score: Wilcoxon test failed ({e})")
        else:
            print(f"\n  Score: all pairs identical, no test needed")

        comment_diffs = f_comments - c_comments
        if np.any(comment_diffs != 0):
            try:
                w_stat, w_p = stats.wilcoxon(f_comments, c_comments)
                print(f"  Comments: Wilcoxon W={w_stat:.1f}, p={w_p:.4f}")
                print(f"    Mean diff (factual - conspiracy): {comment_diffs.mean():+.2f}")
            except ValueError as e:
                print(f"  Comments: Wilcoxon test failed ({e})")
        else:
            print(f"  Comments: all pairs identical, no test needed")

        # How many topics had higher engagement for conspiracy?
        cons_wins_score = np.sum(c_scores > f_scores)
        fact_wins_score = np.sum(f_scores > c_scores)
        ties_score = np.sum(f_scores == c_scores)
        print(f"\n  Score direction: factual>{fact_wins_score}, conspiracy>{cons_wins_score}, tied={ties_score}")

        cons_wins_cmt = np.sum(c_comments > f_comments)
        fact_wins_cmt = np.sum(f_comments > c_comments)
        ties_cmt = np.sum(f_comments == c_comments)
        print(f"  Comment direction: factual>{fact_wins_cmt}, conspiracy>{cons_wins_cmt}, tied={ties_cmt}")


def analyze_e5(data_5a, data_5b, data_5c, topic_mapping):
    """E5: Information Environment — conspiracy engagement across 3 environments."""
    print_section("E5: Information Environment Effect")

    environments = {
        "80% Factual (c5a)": data_5a,
        "50/50 (c5b)": data_5b,
        "80% Conspiracy (c5c)": data_5c,
    }

    env_conspiracy_scores = {}
    env_conspiracy_comments = {}

    for env_name, data in environments.items():
        if data is None:
            print(f"\n  {env_name}: NO DATA")
            continue

        df = build_post_df(data, topic_mapping)
        world = df[df["post_type"].isin(["factual", "conspiracy"])]
        cons = df[df["post_type"] == "conspiracy"]
        fact = df[df["post_type"] == "factual"]

        print(f"\n  {env_name}:")
        print(f"    World posts: {len(world)} ({len(fact)} factual, {len(cons)} conspiracy)")
        print(f"    Agent posts: {len(df[df['post_type'] == 'agent'])}")

        if len(cons) > 0:
            print(f"    Conspiracy engagement:")
            print(f"      Mean score: {cons['score'].mean():.2f}, median: {cons['score'].median():.1f}, sd: {cons['score'].std():.2f}")
            print(f"      Mean comments: {cons['comment_count'].mean():.2f}")

            env_conspiracy_scores[env_name] = cons["score"].values
            env_conspiracy_comments[env_name] = cons["comment_count"].values

        if len(fact) > 0:
            print(f"    Factual engagement:")
            print(f"      Mean score: {fact['score'].mean():.2f}, median: {fact['score'].median():.1f}, sd: {fact['score'].std():.2f}")
            print(f"      Mean comments: {fact['comment_count'].mean():.2f}")

    # Cross-environment comparison of conspiracy post engagement
    env_names = list(env_conspiracy_scores.keys())
    if len(env_names) >= 2:
        print(f"\n--- Cross-environment comparison (conspiracy posts) ---")

        score_groups = [env_conspiracy_scores[n] for n in env_names if len(env_conspiracy_scores[n]) > 0]
        if len(score_groups) >= 2:
            H, p = stats.kruskal(*score_groups)
            print(f"  Kruskal-Wallis (score): H={H:.3f}, p={p:.4f}")

        comment_groups = [env_conspiracy_comments[n] for n in env_names if len(env_conspiracy_comments[n]) > 0]
        if len(comment_groups) >= 2:
            H, p = stats.kruskal(*comment_groups)
            print(f"  Kruskal-Wallis (comments): H={H:.3f}, p={p:.4f}")

        # Pairwise comparisons
        print(f"\n  Pairwise Mann-Whitney (score):")
        for i in range(len(env_names)):
            for j in range(i + 1, len(env_names)):
                a = env_conspiracy_scores[env_names[i]]
                b = env_conspiracy_scores[env_names[j]]
                result = safe_mannwhitney(a, b, f"{env_names[i]} vs {env_names[j]}")
                if result:
                    U, p, r = result
                    print(f"    {env_names[i]} vs {env_names[j]}: U={U:.1f}, p={p:.4f}, r={r:.3f}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Analyze conspiracy experiments")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    args = parser.parse_args()

    export_dir = args.export_dir

    print("=" * 60)
    print("  CONSPIRACY vs FACTUAL EXPERIMENT ANALYSIS")
    print("=" * 60)

    # Load topic mapping
    topic_mapping = load_topic_mapping()
    print(f"\nTopic mapping: {len(topic_mapping)} entries")

    # Load all experiment data
    print(f"\nLoading experiments from {export_dir}/...")
    experiments = {}
    for label, run_name in EXPERIMENTS.items():
        experiments[label] = load_experiment(export_dir, run_name)

    # Run analyses
    if experiments["E1"]:
        analyze_e1(experiments["E1"], topic_mapping)

    if experiments["E2"]:
        analyze_e2(experiments["E2"], topic_mapping)
        analyze_e4(experiments["E2"], topic_mapping)  # E4 uses same data as E2

    if experiments["E3"]:
        analyze_e3(experiments["E3"], topic_mapping)

    if any(experiments.get(k) for k in ["E5a", "E5b", "E5c"]):
        analyze_e5(
            experiments.get("E5a"),
            experiments.get("E5b"),
            experiments.get("E5c"),
            topic_mapping,
        )

    print(f"\n{'='*60}")
    print("  ANALYSIS COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
