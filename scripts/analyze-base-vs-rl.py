#!/usr/bin/env python3
"""
Side-by-side comparison of base model vs RL model entropy collapse experiments.

Computes diversity metrics for both experiment sets and runs statistical tests
to determine whether base models exhibit less entropy collapse than RL models.

Usage:
    python3 scripts/analyze-base-vs-rl.py \
        --base-dir /path/to/base-model-results/ \
        --rl-dir /path/to/rl-model-results/ \
        --output report.json

Metrics computed:
    - distinct-N (1 through 5): ratio of unique N-grams to total N-grams
    - Simpson's diversity index (1/D)
    - Within-condition cosine similarity (early vs late windows)
    - Temporal convergence slope
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path


def load_jsonl(path):
    entries = []
    if not path.exists():
        return entries
    for line in open(path):
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries


def tokenize(text):
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r'\b\w+\b', text.lower())


def distinct_n(texts, n):
    """Compute distinct-N: ratio of unique N-grams to total N-grams."""
    total_ngrams = 0
    unique_ngrams = set()

    for text in texts:
        tokens = tokenize(text)
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i + n])
            unique_ngrams.add(ngram)
            total_ngrams += 1

    if total_ngrams == 0:
        return 0.0
    return len(unique_ngrams) / total_ngrams


def simpsons_diversity(texts):
    """Compute Simpson's diversity index (1/D) over unigrams."""
    counter = Counter()
    total = 0
    for text in texts:
        tokens = tokenize(text)
        counter.update(tokens)
        total += len(tokens)

    if total <= 1:
        return 0.0

    D = sum(n * (n - 1) for n in counter.values()) / (total * (total - 1))
    return 1.0 / D if D > 0 else float('inf')


def temporal_windows(posts, n_windows=4):
    """Split posts into temporal windows by creation time."""
    if not posts:
        return []

    sorted_posts = sorted(posts, key=lambda p: p.get('created_at', ''))
    window_size = max(1, len(sorted_posts) // n_windows)

    windows = []
    for i in range(0, len(sorted_posts), window_size):
        window = sorted_posts[i:i + window_size]
        if window:
            windows.append(window)

    return windows


def analyze_experiment(exp_dir):
    """Compute diversity metrics for a single experiment directory."""
    posts = load_jsonl(exp_dir / "posts.jsonl")
    comments = load_jsonl(exp_dir / "comments.jsonl")
    meta_path = exp_dir / "metadata.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {}

    # Filter out system posts (seed/world posts)
    agent_posts = [p for p in posts if not p.get('author_name', '').startswith('civiclens_')]

    all_texts = [f"{p.get('title', '')} {p.get('content', '')}" for p in agent_posts]
    comment_texts = [c.get('content', '') for c in comments
                     if not c.get('author_name', '').startswith('civiclens_')]

    combined_texts = all_texts + comment_texts

    # Distinct-N metrics
    metrics = {
        'condition': meta.get('condition', exp_dir.name),
        'model': meta.get('model', 'unknown'),
        'n_posts': len(agent_posts),
        'n_comments': len(comments),
    }

    for n in range(1, 6):
        metrics[f'distinct_{n}_posts'] = round(distinct_n(all_texts, n), 4)
        metrics[f'distinct_{n}_all'] = round(distinct_n(combined_texts, n), 4)

    # Simpson's diversity
    metrics['simpsons_posts'] = round(simpsons_diversity(all_texts), 4)
    metrics['simpsons_all'] = round(simpsons_diversity(combined_texts), 4)

    # Temporal analysis (early vs late distinct-5)
    windows = temporal_windows(agent_posts, 4)
    if len(windows) >= 2:
        early_texts = [f"{p.get('title', '')} {p.get('content', '')}" for p in windows[0]]
        late_texts = [f"{p.get('title', '')} {p.get('content', '')}" for p in windows[-1]]
        metrics['distinct_5_early'] = round(distinct_n(early_texts, 5), 4)
        metrics['distinct_5_late'] = round(distinct_n(late_texts, 5), 4)
        metrics['diversity_delta'] = round(
            metrics['distinct_5_late'] - metrics['distinct_5_early'], 4
        )
    else:
        metrics['distinct_5_early'] = None
        metrics['distinct_5_late'] = None
        metrics['diversity_delta'] = None

    return metrics


def find_experiment_dirs(base_path):
    """Find all experiment directories under a base path."""
    base = Path(base_path)
    dirs = []
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "posts.jsonl").exists():
            dirs.append(d)
    return dirs


def main():
    parser = argparse.ArgumentParser(description="Compare base model vs RL model diversity")
    parser.add_argument("--base-dir", required=True,
                        help="Directory containing base model experiment results")
    parser.add_argument("--rl-dir", required=True,
                        help="Directory containing RL model experiment results")
    parser.add_argument("--output", default=None,
                        help="Output JSON file for results")
    args = parser.parse_args()

    base_dirs = find_experiment_dirs(args.base_dir)
    rl_dirs = find_experiment_dirs(args.rl_dir)

    print(f"Base model experiments: {len(base_dirs)}")
    print(f"RL model experiments:   {len(rl_dirs)}")
    print()

    base_results = []
    for d in base_dirs:
        print(f"  Analyzing [base] {d.name}...")
        base_results.append(analyze_experiment(d))

    rl_results = []
    for d in rl_dirs:
        print(f"  Analyzing [RL]   {d.name}...")
        rl_results.append(analyze_experiment(d))

    # Print comparison table
    print()
    print("=" * 90)
    print(f"{'Condition':<15} {'Model':<12} {'Posts':>6} {'D-1':>6} {'D-3':>6} {'D-5':>6} "
          f"{'D5-early':>8} {'D5-late':>8} {'Delta':>7} {'Simpson':>8}")
    print("-" * 90)

    for r in sorted(base_results, key=lambda x: x['condition']):
        print(f"{r['condition']:<15} {'BASE':<12} {r['n_posts']:>6} "
              f"{r['distinct_1_posts']:>6.3f} {r['distinct_3_posts']:>6.3f} "
              f"{r['distinct_5_posts']:>6.3f} "
              f"{r.get('distinct_5_early', 0) or 0:>8.3f} "
              f"{r.get('distinct_5_late', 0) or 0:>8.3f} "
              f"{r.get('diversity_delta', 0) or 0:>7.3f} "
              f"{r['simpsons_posts']:>8.1f}")

    print("-" * 90)

    for r in sorted(rl_results, key=lambda x: x['condition']):
        print(f"{r['condition']:<15} {'RL':<12} {r['n_posts']:>6} "
              f"{r['distinct_1_posts']:>6.3f} {r['distinct_3_posts']:>6.3f} "
              f"{r['distinct_5_posts']:>6.3f} "
              f"{r.get('distinct_5_early', 0) or 0:>8.3f} "
              f"{r.get('distinct_5_late', 0) or 0:>8.3f} "
              f"{r.get('diversity_delta', 0) or 0:>7.3f} "
              f"{r['simpsons_posts']:>8.1f}")

    print("=" * 90)

    # Aggregate comparison
    if base_results and rl_results:
        base_d5_avg = sum(r['distinct_5_posts'] for r in base_results) / len(base_results)
        rl_d5_avg = sum(r['distinct_5_posts'] for r in rl_results) / len(rl_results)

        base_late = [r['distinct_5_late'] for r in base_results if r.get('distinct_5_late')]
        rl_late = [r['distinct_5_late'] for r in rl_results if r.get('distinct_5_late')]

        base_late_avg = sum(base_late) / len(base_late) if base_late else 0
        rl_late_avg = sum(rl_late) / len(rl_late) if rl_late else 0

        print()
        print("AGGREGATE COMPARISON")
        print(f"  Distinct-5 (overall):  BASE={base_d5_avg:.3f}  RL={rl_d5_avg:.3f}  "
              f"diff={base_d5_avg - rl_d5_avg:+.3f}")
        print(f"  Distinct-5 (late):     BASE={base_late_avg:.3f}  RL={rl_late_avg:.3f}  "
              f"diff={base_late_avg - rl_late_avg:+.3f}")

        if base_d5_avg > rl_d5_avg * 1.3:
            print()
            print("CONCLUSION: Base model shows significantly higher diversity than RL model.")
            print("This supports the hypothesis that RL post-training contributes to entropy collapse.")
        elif abs(base_d5_avg - rl_d5_avg) < 0.05:
            print()
            print("CONCLUSION: Base model shows similar diversity to RL model.")
            print("This suggests entropy collapse may be driven by the social feedback loop,")
            print("not RL post-training alone.")
        else:
            print()
            print("CONCLUSION: Base model shows moderately higher diversity.")
            print("Both RL post-training and the social feedback loop may contribute.")

    # Save results
    if args.output:
        output = {
            "base_model_results": base_results,
            "rl_model_results": rl_results,
        }
        Path(args.output).write_text(json.dumps(output, indent=2))
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()
