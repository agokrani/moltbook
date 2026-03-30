#!/usr/bin/env python3.9
"""
Entropy Collapse Analysis — 10-agent experiments (6 conditions)

Analyzes posts, comments, and agent behavior across experimental conditions
to measure diversity collapse in multi-agent social discourse.
"""

import json
import math
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timezone

RESULTS_DIR = Path("/project/def-zhijing/anangia/moltbook/results")
SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}

CONDITIONS_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]


def load_jsonl(path):
    """Load a JSONL file, return list of dicts."""
    if not path.exists() or path.stat().st_size == 0:
        return []
    items = []
    for line in open(path):
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def entropy(counts):
    """Shannon entropy in bits from a Counter/dict of counts."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            h -= p * math.log2(p)
    return h


def normalized_entropy(counts):
    """Entropy / log2(num_categories). 1.0 = perfectly uniform."""
    n = len([c for c in counts.values() if c > 0])
    if n <= 1:
        return 0.0
    return entropy(counts) / math.log2(n)


def gini(values):
    """Gini coefficient. 0 = perfect equality, 1 = max inequality."""
    values = sorted(values)
    n = len(values)
    if n == 0 or sum(values) == 0:
        return 0.0
    cumsum = 0
    total = sum(values)
    for i, v in enumerate(values):
        cumsum += v
    # Using the relative mean absolute difference formula
    mean_val = total / n
    abs_diffs = sum(abs(a - b) for a in values for b in values)
    return abs_diffs / (2 * n * total) if total > 0 else 0


def unique_ngrams(texts, n=3):
    """Count unique word n-grams across all texts."""
    all_ngrams = set()
    for text in texts:
        words = text.lower().split()
        for i in range(len(words) - n + 1):
            all_ngrams.add(tuple(words[i:i+n]))
    return len(all_ngrams)


def type_token_ratio(texts):
    """Type-token ratio: unique words / total words."""
    all_words = []
    for text in texts:
        all_words.extend(text.lower().split())
    if not all_words:
        return 0.0
    return len(set(all_words)) / len(all_words)


def temporal_analysis(posts, window_minutes=10):
    """Analyze how diversity changes over time within an experiment."""
    if not posts:
        return []

    # Parse timestamps and sort
    for p in posts:
        if isinstance(p.get("created_at"), str):
            ts = p["created_at"].replace("Z", "+00:00")
            p["_ts"] = datetime.fromisoformat(ts)

    posts_sorted = sorted([p for p in posts if "_ts" in p], key=lambda x: x["_ts"])
    if not posts_sorted:
        return []

    t0 = posts_sorted[0]["_ts"]
    windows = []
    window_posts = []

    for p in posts_sorted:
        elapsed_min = (p["_ts"] - t0).total_seconds() / 60
        window_idx = int(elapsed_min // window_minutes)

        while len(windows) <= window_idx:
            # Finalize previous window
            if window_posts:
                titles = [wp.get("title", "") for wp in window_posts]
                contents = [wp.get("content", "") for wp in window_posts]
                author_counts = Counter(wp.get("author_name", "") for wp in window_posts)
                windows.append({
                    "window": len(windows),
                    "minute_start": len(windows) * window_minutes,
                    "n_posts": len(window_posts),
                    "unique_authors": len(author_counts),
                    "ttr": round(type_token_ratio(contents), 4),
                    "title_ttr": round(type_token_ratio(titles), 4),
                    "author_entropy": round(normalized_entropy(author_counts), 4),
                })
            else:
                windows.append({
                    "window": len(windows),
                    "minute_start": len(windows) * window_minutes,
                    "n_posts": 0,
                    "unique_authors": 0,
                    "ttr": 0,
                    "title_ttr": 0,
                    "author_entropy": 0,
                })
            window_posts = []

        window_posts.append(p)

    # Don't forget last window
    if window_posts:
        titles = [wp.get("title", "") for wp in window_posts]
        contents = [wp.get("content", "") for wp in window_posts]
        author_counts = Counter(wp.get("author_name", "") for wp in window_posts)
        windows.append({
            "window": len(windows),
            "minute_start": len(windows) * window_minutes,
            "n_posts": len(window_posts),
            "unique_authors": len(author_counts),
            "ttr": round(type_token_ratio(contents), 4),
            "title_ttr": round(type_token_ratio(titles), 4),
            "author_entropy": round(normalized_entropy(author_counts), 4),
        })

    return windows


def analyze_condition(exp_dir):
    """Full analysis for one experimental condition."""
    meta = {}
    meta_path = exp_dir / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text())

    posts = load_jsonl(exp_dir / "posts.jsonl")
    comments = load_jsonl(exp_dir / "comments.jsonl")
    agents = load_jsonl(exp_dir / "agents.jsonl")

    # Filter out system agents
    real_agents = [a for a in agents if a.get("name", "") not in SYSTEM_AGENTS]
    real_posts = [p for p in posts if p.get("author_name", "") not in SYSTEM_AGENTS]

    # --- Basic counts ---
    n_posts = len(real_posts)
    n_comments = len(comments)
    n_agents = len(real_agents)

    # --- Author distribution ---
    post_author_counts = Counter(p["author_name"] for p in real_posts)
    comment_author_counts = Counter(c["author_name"] for c in comments)

    # Posts per agent
    posts_per_agent = [post_author_counts.get(a["name"], 0) for a in real_agents]

    # --- Content diversity ---
    titles = [p.get("title", "") for p in real_posts if p.get("title")]
    contents = [p.get("content", "") for p in real_posts if p.get("content")]
    all_text = [f"{p.get('title', '')} {p.get('content', '')}" for p in real_posts]

    content_ttr = type_token_ratio(contents) if contents else 0
    title_ttr = type_token_ratio(titles) if titles else 0
    trigrams = unique_ngrams(all_text, 3) if all_text else 0

    # --- Word frequency analysis ---
    word_counts = Counter()
    for text in contents:
        word_counts.update(text.lower().split())
    # Remove very common words for topic analysis
    stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                 "being", "have", "has", "had", "do", "does", "did", "will",
                 "would", "could", "should", "may", "might", "can", "shall",
                 "to", "of", "in", "for", "on", "with", "at", "by", "from",
                 "as", "into", "through", "during", "before", "after", "and",
                 "but", "or", "nor", "not", "so", "yet", "both", "either",
                 "neither", "each", "every", "all", "any", "few", "more",
                 "most", "other", "some", "such", "no", "only", "own", "same",
                 "than", "too", "very", "just", "about", "above", "below",
                 "i", "me", "my", "we", "our", "you", "your", "he", "she",
                 "it", "its", "they", "them", "their", "this", "that", "these",
                 "those", "what", "which", "who", "whom", "how", "when",
                 "where", "why", "if", "then", "else", "while", "because",
                 "—", "–", "-", "i'm", "it's", "don't", "that's", "you're",
                 "one", "like", "also", "even", "much", "many", "well",
                 "still", "here", "there", "now"}
    topic_words = {w: c for w, c in word_counts.items()
                   if w not in stopwords and len(w) > 2 and c > 2}

    # --- Submolt distribution ---
    submolt_counts = Counter(p.get("submolt", "unknown") for p in real_posts)

    # --- Score distribution ---
    scores = [p.get("score", 0) for p in real_posts]
    avg_score = sum(scores) / len(scores) if scores else 0
    max_score = max(scores) if scores else 0

    # --- Temporal analysis ---
    temporal = temporal_analysis(real_posts, window_minutes=10)

    # --- First/last half comparison (entropy drift) ---
    mid = len(real_posts) // 2
    first_half = real_posts[:mid]
    second_half = real_posts[mid:]

    first_ttr = type_token_ratio([p.get("content", "") for p in first_half]) if first_half else 0
    second_ttr = type_token_ratio([p.get("content", "") for p in second_half]) if second_half else 0
    ttr_drift = second_ttr - first_ttr  # negative = collapsing

    first_author_ent = normalized_entropy(Counter(p["author_name"] for p in first_half)) if first_half else 0
    second_author_ent = normalized_entropy(Counter(p["author_name"] for p in second_half)) if second_half else 0

    return {
        "condition": meta.get("condition", exp_dir.name),
        "experiment_name": meta.get("experiment_name", exp_dir.name),
        "duration_minutes": meta.get("duration_minutes", "?"),
        "counts": {
            "posts": n_posts,
            "comments": n_comments,
            "agents_active": len(post_author_counts),
            "agents_total": n_agents,
        },
        "author_distribution": {
            "posts_per_agent": dict(post_author_counts.most_common()),
            "post_gini": round(gini(posts_per_agent), 4),
            "post_author_entropy": round(normalized_entropy(post_author_counts), 4),
            "comment_authors": len(comment_author_counts),
        },
        "content_diversity": {
            "content_ttr": round(content_ttr, 4),
            "title_ttr": round(title_ttr, 4),
            "unique_trigrams": trigrams,
            "trigrams_per_post": round(trigrams / n_posts, 2) if n_posts else 0,
        },
        "scores": {
            "avg": round(avg_score, 2),
            "max": max_score,
            "nonzero_pct": round(100 * sum(1 for s in scores if s != 0) / len(scores), 1) if scores else 0,
        },
        "submolts": dict(submolt_counts.most_common()),
        "top_words": dict(Counter(topic_words).most_common(20)),
        "entropy_drift": {
            "first_half_ttr": round(first_ttr, 4),
            "second_half_ttr": round(second_ttr, 4),
            "ttr_change": round(ttr_drift, 4),
            "first_half_author_entropy": round(first_author_ent, 4),
            "second_half_author_entropy": round(second_author_ent, 4),
        },
        "temporal": temporal,
    }


def print_summary(results):
    """Print a clean summary table."""
    print("=" * 90)
    print("ENTROPY COLLAPSE EXPERIMENT — 10-AGENT ANALYSIS")
    print("=" * 90)

    # Overview table
    print("\n## Overview\n")
    print(f"{'Condition':<12} {'Posts':>6} {'Comments':>9} {'Active':>7} "
          f"{'Content TTR':>12} {'Title TTR':>10} {'Author Ent':>11} {'Post Gini':>10}")
    print("-" * 90)
    for r in results:
        c = r["condition"]
        print(f"{c:<12} {r['counts']['posts']:>6} {r['counts']['comments']:>9} "
              f"{r['counts']['agents_active']:>7} "
              f"{r['content_diversity']['content_ttr']:>12.4f} "
              f"{r['content_diversity']['title_ttr']:>10.4f} "
              f"{r['author_distribution']['post_author_entropy']:>11.4f} "
              f"{r['author_distribution']['post_gini']:>10.4f}")

    # Entropy drift
    print("\n## Entropy Drift (1st half → 2nd half)\n")
    print(f"{'Condition':<12} {'1st TTR':>8} {'2nd TTR':>8} {'ΔTTR':>8} "
          f"{'1st Auth':>9} {'2nd Auth':>9} {'Signal':>12}")
    print("-" * 72)
    for r in results:
        d = r["entropy_drift"]
        delta = d["ttr_change"]
        signal = "COLLAPSE" if delta < -0.01 else ("STABLE" if abs(delta) < 0.01 else "EXPANDING")
        print(f"{r['condition']:<12} {d['first_half_ttr']:>8.4f} {d['second_half_ttr']:>8.4f} "
              f"{delta:>+8.4f} "
              f"{d['first_half_author_entropy']:>9.4f} {d['second_half_author_entropy']:>9.4f} "
              f"{signal:>12}")

    # Post distribution per agent
    print("\n## Agent Post Counts\n")
    all_agents = set()
    for r in results:
        all_agents.update(r["author_distribution"]["posts_per_agent"].keys())
    all_agents = sorted(all_agents)

    header = f"{'Agent':<18}" + "".join(f"{c:<10}" for c in CONDITIONS_ORDER)
    print(header)
    print("-" * len(header))
    for agent in all_agents:
        row = f"{agent:<18}"
        for r in results:
            count = r["author_distribution"]["posts_per_agent"].get(agent, 0)
            row += f"{count:<10}"
        print(row)

    # Scores
    print("\n## Voting Activity\n")
    print(f"{'Condition':<12} {'Avg Score':>10} {'Max Score':>10} {'% Nonzero':>10}")
    print("-" * 45)
    for r in results:
        print(f"{r['condition']:<12} {r['scores']['avg']:>10.2f} "
              f"{r['scores']['max']:>10} {r['scores']['nonzero_pct']:>10.1f}%")

    # Top words per condition
    print("\n## Top Content Words (by condition)\n")
    for r in results:
        words = list(r["top_words"].items())[:15]
        word_str = ", ".join(f"{w}({c})" for w, c in words)
        print(f"  {r['condition']:<12}: {word_str}")

    # Temporal trends
    print("\n## Temporal Diversity (10-min windows)\n")
    for r in results:
        if not r["temporal"]:
            continue
        print(f"  --- {r['condition']} ---")
        print(f"  {'Window':<8} {'Posts':>6} {'Authors':>8} {'Content TTR':>12} {'Title TTR':>10} {'Auth Ent':>9}")
        for w in r["temporal"]:
            print(f"  {w['minute_start']:>3}-{w['minute_start']+10:<4} "
                  f"{w['n_posts']:>6} {w['unique_authors']:>8} "
                  f"{w['ttr']:>12.4f} {w['title_ttr']:>10.4f} {w['author_entropy']:>9.4f}")
        print()


def main():
    results = []
    for cond in CONDITIONS_ORDER:
        exp_dir = RESULTS_DIR / f"ec-{cond}-run01"
        if exp_dir.exists():
            print(f"Analyzing {cond}...", file=sys.stderr)
            results.append(analyze_condition(exp_dir))
        else:
            print(f"[SKIP] {exp_dir} not found", file=sys.stderr)

    print_summary(results)

    # Save full JSON for further analysis
    out_path = Path("/home/anangia/moltbook/analysis/results_10agents.json")
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nFull results saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
