#!/usr/bin/env python3
"""
Temporal diversity analysis for MoltBook entropy collapse experiments.

Computes per-quartile diversity metrics across experiment directories and
generates trajectory plots + heatmaps. Supports multiple n-gram levels
and self-BLEU for measuring post-to-post convergence over time.

Usage:
    # Compare two experiment sets (base vs RL):
    python3 scripts/analyze-temporal-diversity.py \
        --experiments base=/path/to/base-results rl=/path/to/rl-results \
        --metrics d3 d5 self-bleu \
        --output-dir analysis/plots

    # Single experiment set analysis:
    python3 scripts/analyze-temporal-diversity.py \
        --experiments gemini=/path/to/gemini-results \
        --metrics d3 d5 self-bleu \
        --n-quartiles 4

    # JSON output only (no plots):
    python3 scripts/analyze-temporal-diversity.py \
        --experiments base=/path/to/base rl=/path/to/rl \
        --metrics d3 \
        --json results.json

Metrics:
    d1..d5        Distinct-N (ratio of unique N-grams to total)
    self-bleu     Self-BLEU (avg BLEU of each post against K predecessors)
    cosine-sim    Intra-quartile avg pairwise cosine similarity (TF-IDF)
                  Higher = posts more topically similar to each other
    agent-jaccard Inter-agent vocabulary Jaccard similarity (scipy pdist)
                  Higher = agents sharing more words = identity collapse
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from scipy.spatial.distance import pdist
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity as sklearn_cosine_similarity


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------

def tokenize(text):
    """Whitespace + punctuation tokenizer, lowercased."""
    return re.findall(r'\b\w+\b', text.lower())


# ---------------------------------------------------------------------------
# Distinct-N
# ---------------------------------------------------------------------------

def distinct_n(texts, n):
    """Ratio of unique N-grams to total N-grams across texts."""
    total = 0
    unique = set()
    for text in texts:
        tokens = tokenize(text)
        for i in range(len(tokens) - n + 1):
            ngram = tuple(tokens[i:i + n])
            unique.add(ngram)
            total += 1
    return len(unique) / total if total else 0.0


# ---------------------------------------------------------------------------
# Self-BLEU (using nltk)
# ---------------------------------------------------------------------------

# Smoothing for short texts where higher-order n-gram precision can be zero
_smoothing = SmoothingFunction().method1


def self_bleu_rolling(posts_ordered, k=20, max_n=4):
    """Compute rolling self-BLEU: each post vs its K predecessors.

    Uses nltk.translate.bleu_score.sentence_bleu with smoothing.
    Returns average self-BLEU score. Higher = more repetitive.
    """
    if len(posts_ordered) < 2:
        return 0.0

    weights = tuple(1.0 / max_n for _ in range(max_n))

    tokenized = []
    for p in posts_ordered:
        text = f"{p.get('title', '')} {p.get('content', '')}"
        tokenized.append(tokenize(text))

    scores = []
    for i in range(1, len(tokenized)):
        start = max(0, i - k)
        predecessors = tokenized[start:i]

        post_scores = []
        for ref in predecessors:
            s = sentence_bleu(
                [ref], tokenized[i],
                weights=weights,
                smoothing_function=_smoothing
            )
            post_scores.append(s)

        if post_scores:
            scores.append(sum(post_scores) / len(post_scores))

    return sum(scores) / len(scores) if scores else 0.0


# ---------------------------------------------------------------------------
# Intra-quartile cosine similarity (TF-IDF)
# ---------------------------------------------------------------------------

def intra_cosine_similarity(texts):
    """Average pairwise cosine similarity between TF-IDF vectors of texts.

    Measures topical convergence: higher = posts are more similar to each other.
    Uses sklearn TfidfVectorizer with default English stop words removed.
    """
    if len(texts) < 2:
        return 0.0

    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        # All texts are empty or stop words only
        return 0.0

    sim_matrix = sklearn_cosine_similarity(tfidf_matrix)

    # Average of upper triangle (excluding diagonal)
    n = sim_matrix.shape[0]
    total = 0.0
    count = 0
    for i in range(n):
        for j in range(i + 1, n):
            total += sim_matrix[i, j]
            count += 1

    return total / count if count > 0 else 0.0


def extract_top_terms(texts, n_terms=10):
    """Extract top TF-IDF terms from a collection of texts."""
    if not texts:
        return []

    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []

    feature_names = vectorizer.get_feature_names_out()
    mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).flatten()
    top_indices = mean_tfidf.argsort()[-n_terms:][::-1]

    return [(feature_names[i], round(float(mean_tfidf[i]), 4)) for i in top_indices]


# ---------------------------------------------------------------------------
# Inter-agent Jaccard similarity
# ---------------------------------------------------------------------------

_STOP_WORDS = ENGLISH_STOP_WORDS


def inter_agent_jaccard(posts):
    """Average pairwise Jaccard similarity between agent vocabularies.

    For a set of posts in a time window:
    1. Group posts by author (agent)
    2. Build each agent's vocabulary set (stop words removed)
    3. Compute all pairwise Jaccard similarities using scipy.spatial.distance
    4. Return the mean similarity

    Higher value = agents share more vocabulary = identity convergence.
    Uses scipy.spatial.distance.pdist(metric='jaccard') on binary
    word-presence vectors for correct, standard Jaccard computation.
    """
    # Group posts by agent
    agent_texts = defaultdict(list)
    for p in posts:
        agent = p.get('author_name', 'unknown')
        text = f"{p.get('title', '')} {p.get('content', '')}"
        agent_texts[agent].append(text)

    # Build vocabulary set per agent (stop words + single chars removed)
    agent_vocabs = {}
    for agent, texts in agent_texts.items():
        words = set()
        for text in texts:
            tokens = tokenize(text)
            words.update(t for t in tokens if t not in _STOP_WORDS and len(t) > 1)
        # Skip agents with fewer than 5 unique words in this window
        if len(words) >= 5:
            agent_vocabs[agent] = words

    if len(agent_vocabs) < 2:
        return 0.0

    # Build binary word-presence matrix (agents × vocabulary)
    all_words = sorted(set().union(*agent_vocabs.values()))
    word_to_idx = {w: i for i, w in enumerate(all_words)}

    agents = sorted(agent_vocabs.keys())
    matrix = np.zeros((len(agents), len(all_words)), dtype=bool)
    for i, agent in enumerate(agents):
        for word in agent_vocabs[agent]:
            matrix[i, word_to_idx[word]] = True

    # scipy jaccard gives dissimilarity: 1 - |A∩B|/|A∪B|
    distances = pdist(matrix, metric='jaccard')
    similarities = 1.0 - distances

    return float(np.mean(similarities))


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_posts(exp_dir):
    """Load agent posts from JSONL, excluding seed/system posts."""
    posts = []
    pf = Path(exp_dir) / "posts.jsonl"
    if not pf.exists():
        return posts
    for line in open(pf):
        line = line.strip()
        if line:
            p = json.loads(line)
            if not p.get('author_name', '').startswith('civiclens_'):
                posts.append(p)
    return posts


def find_experiment_dirs(base_path):
    """Find experiment subdirectories containing posts.jsonl."""
    base = Path(base_path)
    if not base.exists():
        return []
    # If the directory itself has posts.jsonl, it's a single experiment
    if (base / "posts.jsonl").exists():
        return [base]
    dirs = []
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "posts.jsonl").exists():
            dirs.append(d)
    return dirs


def extract_condition(exp_dir):
    """Extract condition name from experiment directory."""
    meta_path = exp_dir / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            return meta.get('condition', exp_dir.name)
        except (json.JSONDecodeError, OSError):
            pass
    # Fallback: parse from directory name
    name = exp_dir.name
    for cond in ['mag0', 'mag1', 'mag5', 'mag25', 'dom-agi', 'dom-tech',
                 'het-dual', 'het-multi']:
        if cond in name:
            return cond
    return name


# ---------------------------------------------------------------------------
# Quartile analysis
# ---------------------------------------------------------------------------

def split_quartiles(posts, n_quartiles=4):
    """Split posts into temporal quartiles by creation time."""
    sorted_posts = sorted(posts, key=lambda p: p.get('created_at', ''))
    qsize = max(1, len(sorted_posts) // n_quartiles)
    quartiles = []
    for i in range(n_quartiles):
        if i < n_quartiles - 1:
            chunk = sorted_posts[i * qsize:(i + 1) * qsize]
        else:
            chunk = sorted_posts[i * qsize:]
        if chunk:
            quartiles.append(chunk)
    return quartiles


def compute_quartile_metrics(posts, metrics, n_quartiles=4, bleu_k=20):
    """Compute requested metrics per quartile.

    Args:
        posts: list of post dicts
        metrics: list of metric names (e.g. ['d3', 'd5', 'self-bleu'])
        n_quartiles: number of temporal splits
        bleu_k: number of predecessors for self-BLEU

    Returns:
        dict mapping metric_name -> list of per-quartile values
    """
    quartiles = split_quartiles(posts, n_quartiles)
    results = {m: [] for m in metrics}

    for q_posts in quartiles:
        texts = [f"{p.get('title', '')} {p.get('content', '')}" for p in q_posts]

        for metric in metrics:
            if metric.startswith('d') and metric[1:].isdigit():
                n = int(metric[1:])
                results[metric].append(round(distinct_n(texts, n), 4))
            elif metric == 'self-bleu':
                score = self_bleu_rolling(q_posts, k=bleu_k)
                results[metric].append(round(score, 4))
            elif metric == 'cosine-sim':
                score = intra_cosine_similarity(texts)
                results[metric].append(round(score, 4))
            elif metric == 'agent-jaccard':
                score = inter_agent_jaccard(q_posts)
                results[metric].append(round(score, 4))

    # Optionally collect top terms per quartile (for qualitative output)
    top_terms = {}
    if 'cosine-sim' in metrics:
        for i, q_posts in enumerate(quartiles):
            texts = [f"{p.get('title', '')} {p.get('content', '')}" for p in q_posts]
            top_terms[f'Q{i+1}'] = extract_top_terms(texts, n_terms=10)

    return results, len(quartiles), top_terms


# ---------------------------------------------------------------------------
# Analysis runner
# ---------------------------------------------------------------------------

def analyze_experiments(experiment_sets, metrics, n_quartiles=4, bleu_k=20):
    """Run analysis across all experiment sets.

    Args:
        experiment_sets: dict of {label: path}
        metrics: list of metric names
        n_quartiles: temporal splits
        bleu_k: self-BLEU predecessor count

    Returns:
        list of result dicts
    """
    all_results = []

    for set_label, set_path in experiment_sets.items():
        exp_dirs = find_experiment_dirs(set_path)
        print(f"\n{set_label}: {len(exp_dirs)} experiments in {set_path}")

        for exp_dir in exp_dirs:
            condition = extract_condition(exp_dir)
            posts = load_posts(exp_dir)

            if len(posts) < 8:
                print(f"  Skipping {condition} ({len(posts)} posts — too few)")
                continue

            print(f"  {condition}: {len(posts)} posts", end='')

            quartile_metrics, n_q, top_terms = compute_quartile_metrics(
                posts, metrics, n_quartiles, bleu_k
            )

            result = {
                'set': set_label,
                'condition': condition,
                'directory': str(exp_dir),
                'n_posts': len(posts),
                'n_quartiles': n_q,
            }

            for metric, values in quartile_metrics.items():
                result[f'{metric}_quartiles'] = values
                if len(values) >= 2:
                    result[f'{metric}_delta'] = round(values[-1] - values[0], 4)
                else:
                    result[f'{metric}_delta'] = None

            if top_terms:
                result['top_terms_per_quartile'] = {
                    q: [t[0] for t in terms] for q, terms in top_terms.items()
                }

            all_results.append(result)

            # Print summary
            for metric in metrics:
                delta = result.get(f'{metric}_delta')
                if delta is not None:
                    print(f'  {metric}: Δ={delta:+.3f}', end='')
            print()

    return all_results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_trajectories(results, metric, output_dir, n_quartiles=4):
    """Plot per-condition trajectory subplots for a given metric."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plots")
        return

    conditions = sorted(set(r['condition'] for r in results))
    sets = sorted(set(r['set'] for r in results))

    palette = ['#2ecc71', '#e74c3c', '#e67e22', '#9b59b6', '#3498db',
               '#1abc9c', '#f39c12', '#c0392b']
    marker_list = ['s', 'o', '^', 'D', 'v', 'P', 'X', '*']

    n_conds = len(conditions)
    n_cols = min(3, n_conds)
    n_rows = math.ceil(n_conds / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows),
                             sharey=True, squeeze=False)

    metric_label = metric.upper().replace('-', ' ').replace('SELF BLEU', 'Self-BLEU').replace('AGENT JACCARD', 'Inter-Agent Jaccard')
    fig.suptitle(
        f'{metric_label} Temporal Trajectories\n'
        f'({n_quartiles} quartiles, 1-hour experiments)',
        fontsize=14, fontweight='bold', y=1.0
    )

    for idx, cond in enumerate(conditions):
        ax = axes[idx // n_cols][idx % n_cols]
        ax.set_title(cond.upper(), fontsize=13, fontweight='bold')
        ax.set_xlabel('Time Quartile', fontsize=10)
        if idx % n_cols == 0:
            ax.set_ylabel(metric_label, fontsize=11)

        x_ticks = list(range(1, n_quartiles + 1))
        ax.set_xticks(x_ticks)
        q_labels = [f'Q{i}' for i in x_ticks]
        ax.set_xticklabels(q_labels)
        ax.grid(True, alpha=0.3)

        for s_idx, s_label in enumerate(sets):
            matching = [r for r in results
                        if r['set'] == s_label and r['condition'] == cond]
            if not matching:
                continue
            r = matching[0]
            values = r.get(f'{metric}_quartiles', [])
            if len(values) < 2:
                continue

            delta = r.get(f'{metric}_delta', 0)
            color = palette[s_idx % len(palette)]
            marker = marker_list[s_idx % len(marker_list)]

            # BASE gets thick solid line
            is_base = 'base' in s_label.lower()
            lw = 3.0 if is_base else 1.8
            ls = '-' if is_base else '--'

            label = f"{s_label} (Δ={delta:+.3f})"
            ax.plot(x_ticks[:len(values)], values, color=color, marker=marker,
                    linewidth=lw, linestyle=ls, markersize=7, label=label,
                    alpha=0.9)

        ax.legend(fontsize=7, loc='best', framealpha=0.9)

    # Hide unused subplots
    for idx in range(n_conds, n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = Path(output_dir) / f'{metric}_trajectories_by_condition.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_heatmap(results, metric, output_dir):
    """Plot delta heatmap for a given metric."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib/numpy not available — skipping heatmap")
        return

    conditions = sorted(set(r['condition'] for r in results))
    sets = sorted(set(r['set'] for r in results))

    matrix = []
    for s_label in sets:
        row = []
        for cond in conditions:
            matching = [r for r in results
                        if r['set'] == s_label and r['condition'] == cond]
            if matching:
                row.append(matching[0].get(f'{metric}_delta', 0) or 0)
            else:
                row.append(0)
        matrix.append(row)

    arr = np.array(matrix)

    metric_label = metric.upper().replace('-', ' ').replace('SELF BLEU', 'Self-BLEU').replace('AGENT JACCARD', 'Inter-Agent Jaccard')

    # For self-BLEU and cosine-sim, positive delta = more convergence (bad)
    if 'bleu' in metric.lower():
        cmap = 'RdYlGn_r'
        vmin, vmax = -0.05, 0.3
        subtitle = 'Green = Low Repetition | Red = Increasing Repetition'
    elif 'cosine' in metric.lower():
        cmap = 'RdYlGn_r'
        vmin, vmax = -0.1, 0.3
        subtitle = 'Green = Topically Diverse | Red = Topical Convergence'
    elif 'jaccard' in metric.lower():
        cmap = 'RdYlGn_r'
        vmin, vmax = -0.05, 0.15
        subtitle = 'Green = Distinct Agent Voices | Red = Agent Identity Collapse'
    else:
        cmap = 'RdYlGn'
        vmin, vmax = -0.5, 0.1
        subtitle = 'Green = Diversity Maintained | Red = Entropy Collapse'

    fig, ax = plt.subplots(figsize=(max(8, len(conditions) * 1.6), len(sets) * 1.0 + 1.5))
    im = ax.imshow(arr, cmap=cmap, aspect='auto', vmin=vmin, vmax=vmax)

    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.upper() for c in conditions], fontsize=11)
    ax.set_yticks(range(len(sets)))
    ax.set_yticklabels(sets, fontsize=11)

    for i in range(len(sets)):
        for j in range(len(conditions)):
            val = arr[i, j]
            color = 'white' if abs(val) > 0.15 else 'black'
            ax.text(j, i, f'{val:+.3f}', ha='center', va='center',
                    fontsize=11, fontweight='bold', color=color)

    ax.set_title(f'{metric_label} Temporal Delta (Q4 − Q1)\n{subtitle}',
                 fontsize=13, fontweight='bold')
    plt.colorbar(im, ax=ax, label=f'{metric_label} Delta', shrink=0.8)
    plt.tight_layout()

    out_path = Path(output_dir) / f'{metric}_delta_heatmap.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_experiments(args):
    """Parse label=path experiment arguments into dict."""
    experiments = {}
    for item in args:
        if '=' in item:
            label, path = item.split('=', 1)
            experiments[label] = path
        else:
            experiments[Path(item).name] = item
    return experiments


def main():
    parser = argparse.ArgumentParser(
        description='Temporal diversity analysis for MoltBook experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        '--experiments', nargs='+', required=True,
        help='Experiment sets as label=path (e.g. base=/path/to/base rl=/path/to/rl)'
    )
    parser.add_argument(
        '--metrics', nargs='+', default=['d3', 'd5'],
        help='Metrics to compute (d1..d5, self-bleu). Default: d3 d5'
    )
    parser.add_argument(
        '--n-quartiles', type=int, default=4,
        help='Number of temporal quartiles (default: 4)'
    )
    parser.add_argument(
        '--bleu-k', type=int, default=20,
        help='Number of predecessors for self-BLEU (default: 20)'
    )
    parser.add_argument(
        '--output-dir', default=None,
        help='Directory for plot output (generates trajectories + heatmaps)'
    )
    parser.add_argument(
        '--json', default=None,
        help='Path for JSON results output'
    )
    parser.add_argument(
        '--no-plots', action='store_true',
        help='Skip plot generation even if --output-dir is set'
    )

    args = parser.parse_args()

    experiment_sets = parse_experiments(args.experiments)

    # Validate metrics
    valid_metrics = set()
    for m in args.metrics:
        if m in ('self-bleu', 'cosine-sim', 'agent-jaccard'):
            valid_metrics.add(m)
        elif m.startswith('d') and m[1:].isdigit() and 1 <= int(m[1:]) <= 10:
            valid_metrics.add(m)
        else:
            print(f"Unknown metric: {m}", file=sys.stderr)
            sys.exit(1)

    metrics = sorted(valid_metrics)
    print(f"Metrics: {', '.join(metrics)}")
    print(f"Quartiles: {args.n_quartiles}")
    if 'self-bleu' in metrics:
        print(f"Self-BLEU K: {args.bleu_k}")

    # Run analysis
    results = analyze_experiments(
        experiment_sets, metrics, args.n_quartiles, args.bleu_k
    )

    if not results:
        print("\nNo results to report.")
        sys.exit(0)

    # Print summary table
    print(f"\n{'=' * 90}")
    print("SUMMARY: Temporal Deltas (Q{} - Q1)".format(args.n_quartiles))
    print(f"{'=' * 90}")

    sets = sorted(set(r['set'] for r in results))
    conditions = sorted(set(r['condition'] for r in results))

    for metric in metrics:
        metric_label = metric.upper().replace('-', ' ')
        print(f"\n--- {metric_label} ---")
        header = f"{'Condition':<12} {'Set':<18} {'Posts':>6}"
        for i in range(1, args.n_quartiles + 1):
            header += f"  {'Q' + str(i):>7}"
        header += f"  {'Delta':>8}"
        print(header)
        print("-" * len(header))

        for cond in conditions:
            for s_label in sets:
                matching = [r for r in results
                            if r['set'] == s_label and r['condition'] == cond]
                if not matching:
                    continue
                r = matching[0]
                values = r.get(f'{metric}_quartiles', [])
                delta = r.get(f'{metric}_delta')

                row = f"{cond:<12} {s_label:<18} {r['n_posts']:>6}"
                for v in values:
                    row += f"  {v:>7.3f}"
                if delta is not None:
                    row += f"  {delta:>+8.3f}"
                print(row)

    # Plots
    if args.output_dir and not args.no_plots:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        for metric in metrics:
            plot_trajectories(results, metric, out_dir, args.n_quartiles)
            plot_heatmap(results, metric, out_dir)

    # JSON output
    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))
        print(f"\nJSON results saved to {args.json}")


if __name__ == "__main__":
    main()
