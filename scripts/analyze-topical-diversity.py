#!/usr/bin/env python3
"""
Topical diversity analysis for MoltBook experiments.

Fits one global topic model across all provided experiment sets, then measures
how topic mixtures change over time inside each experiment directory.

This is intentionally simpler than STM:
- one shared LDA topic model across the full corpus
- per-document topic proportions
- per-quartile topic-mixture metrics
- human-readable topic keywords for inspection

Usage:
    python3 scripts/analyze-topical-diversity.py \
        --experiments "Base=/path/to/base" "Instruct=/path/to/instruct" \
        --n-topics 15 \
        --output-dir analysis/plots-topical \
        --json analysis/topical-diversity.json

Primary metrics:
    topic-entropy        Shannon entropy of the quartile's mean topic mixture.
                         Higher = more diverse topics represented.
    effective-topics     Effective number of topics = 2 ** entropy.
                         Higher = broader topical spread.
    dominant-topic-share Largest topic share in the quartile mean mixture.
                         Higher = one topic dominates more.
    agent-topic-sim      Mean pairwise similarity between agent topic profiles.
                         Higher = agents are discussing more similar topics.
    drift-jsd            JSD from Q1 topic mixture to the current quartile.
                         Higher = topical drift away from the start state.
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import entropy as scipy_entropy
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS


CONDITIONS = ['mag0', 'mag1', 'mag5', 'mag25', 'dom-agi', 'dom-tech',
              'het-dual', 'het-multi']
EXTRA_STOP_WORDS = {
    've', 'll', 're', 'don', 'didn', 'doesn', 'isn', 'aren', 'wasn', 'weren',
    'won', 'wouldn', 'couldn', 'shouldn', 'hadn', 'hasn', 'haven', 'mightn',
    'mustn', 'needn', 'shan', 'just', 'like', 'actually', 'really',
}


def load_posts(exp_dir):
    """Load agent-authored posts from posts.jsonl."""
    posts = []
    path = Path(exp_dir) / "posts.jsonl"
    if not path.exists():
        return posts

    for line in open(path):
        line = line.strip()
        if not line:
            continue
        post = json.loads(line)
        if post.get('author_name', '').startswith('civiclens_'):
            continue
        posts.append(post)

    return posts


def find_experiment_dirs(base_path):
    """Find experiment directories containing posts.jsonl."""
    base = Path(base_path)
    if not base.exists():
        return []
    if (base / "posts.jsonl").exists():
        return [base]
    return sorted(
        d for d in base.iterdir()
        if d.is_dir() and (d / "posts.jsonl").exists()
    )


def extract_condition(exp_dir):
    """Extract experiment condition from metadata or directory name."""
    meta_path = Path(exp_dir) / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            return meta.get('condition', exp_dir.name)
        except (json.JSONDecodeError, OSError):
            pass

    name = Path(exp_dir).name
    for cond in CONDITIONS:
        if cond in name:
            return cond
    return name


def split_quartiles(posts, n_quartiles=4):
    """Split posts into temporal quartiles by created_at."""
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


def parse_experiments(args):
    """Parse label=path experiment arguments into a dict."""
    experiments = {}
    for item in args:
        if '=' in item:
            label, path = item.split('=', 1)
            experiments[label] = path
        else:
            experiments[Path(item).name] = item
    return experiments


def clean_text(text):
    """Light normalization for topic modeling."""
    text = text or ""
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'\b[a-zA-Z]+n[\'’]t\b', ' not', text)
    text = re.sub(r'[\'’](ve|ll|re|d|m|s)\b', '', text)
    text = re.sub(r'[*_`#>\[\]\(\)\|]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_distribution(values):
    """Normalize a non-negative vector to sum to 1."""
    arr = np.asarray(values, dtype=np.float64)
    total = arr.sum()
    if total <= 0:
        return np.zeros_like(arr)
    return arr / total


def jensen_shannon_divergence(p, q):
    """Jensen-Shannon divergence in bits, bounded to [0, 1]."""
    p = normalize_distribution(p)
    q = normalize_distribution(q)
    if p.sum() == 0 or q.sum() == 0:
        return 0.0
    m = 0.5 * (p + q)
    return 0.5 * (
        scipy_entropy(p, m, base=2) + scipy_entropy(q, m, base=2)
    )


def top_positive_ids(dist, topn=3):
    arr = np.asarray(dist, dtype=np.float64)
    positive = np.flatnonzero(arr > 0)
    if positive.size == 0:
        return []
    ranked = positive[np.argsort(arr[positive])[::-1]]
    return [int(i) for i in ranked[:topn]]


def mean_agent_topic_similarity(posts):
    """Average pairwise topic-distribution similarity across agents."""
    by_agent = defaultdict(list)
    for post in posts:
        if 'topic_dist' not in post:
            continue
        by_agent[post.get('author_name', 'unknown')].append(post['topic_dist'])

    agent_profiles = []
    for topic_dists in by_agent.values():
        if not topic_dists:
            continue
        mean_profile = normalize_distribution(np.mean(topic_dists, axis=0))
        agent_profiles.append(mean_profile)

    if len(agent_profiles) < 2:
        return 0.0

    similarities = []
    for i in range(len(agent_profiles)):
        for j in range(i + 1, len(agent_profiles)):
            jsd = jensen_shannon_divergence(agent_profiles[i], agent_profiles[j])
            similarities.append(1.0 - jsd)

    return float(np.mean(similarities)) if similarities else 0.0


def summarize_topic_keywords(model, vectorizer, topn):
    """Extract top keywords for each topic."""
    vocab = vectorizer.get_feature_names_out()
    topics = []
    for idx, topic_weights in enumerate(model.components_):
        top_ids = topic_weights.argsort()[-topn:][::-1]
        topics.append({
            'topic_id': idx,
            'keywords': [vocab[i] for i in top_ids],
        })
    return topics


def collect_documents(experiment_sets, min_posts):
    """Load posts from all experiment sets and flatten to a shared corpus."""
    docs = []
    experiments = []

    for set_label, set_path in experiment_sets.items():
        exp_dirs = find_experiment_dirs(set_path)
        print(f"\n{set_label}: {len(exp_dirs)} experiments in {set_path}")

        for exp_dir in exp_dirs:
            posts = load_posts(exp_dir)
            condition = extract_condition(exp_dir)
            if len(posts) < min_posts:
                print(f"  Skipping {condition} ({len(posts)} posts)")
                continue

            experiments.append({
                'set': set_label,
                'condition': condition,
                'directory': str(exp_dir),
                'posts': posts,
            })

            for idx, post in enumerate(posts):
                docs.append({
                    'doc_id': len(docs),
                    'directory': str(exp_dir),
                    'set': set_label,
                    'condition': condition,
                    'post_idx': idx,
                    'author_name': post.get('author_name', 'unknown'),
                    'created_at': post.get('created_at', ''),
                    'text': clean_text(
                        f"{post.get('title', '')} {post.get('content', '')}"
                    ),
                })

            print(f"  {condition}: {len(posts)} posts")

    return docs, experiments


def fit_topic_model(docs, n_topics, min_df, max_df, max_features, random_state):
    """Fit a shared LDA topic model across all loaded documents."""
    texts = [d['text'] for d in docs]
    vectorizer = CountVectorizer(
        stop_words=sorted(ENGLISH_STOP_WORDS.union(EXTRA_STOP_WORDS)),
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
        token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z]{1,}\b',
    )
    matrix = vectorizer.fit_transform(texts)
    model = LatentDirichletAllocation(
        n_components=n_topics,
        learning_method='batch',
        max_iter=30,
        random_state=random_state,
        evaluate_every=0,
        n_jobs=-1,
    )
    doc_topics = model.fit_transform(matrix)
    return model, vectorizer, doc_topics


def compute_quartile_metrics(posts, n_topics, n_quartiles):
    """Compute topical metrics per quartile for a single experiment."""
    quartiles = split_quartiles(posts, n_quartiles)

    topic_entropy = []
    effective_topics = []
    dominant_topic_share = []
    agent_topic_sim = []
    drift_jsd = []
    quartile_topic_mix = []
    top_topic_ids = []

    baseline_mix = None
    for q_posts in quartiles:
        matrix = np.asarray([p['topic_dist'] for p in q_posts], dtype=np.float64)
        quartile_mix = normalize_distribution(matrix.mean(axis=0))
        quartile_topic_mix.append([round(float(x), 6) for x in quartile_mix])

        h = float(scipy_entropy(quartile_mix, base=2))
        topic_entropy.append(round(h, 4))
        effective_topics.append(round(float(2 ** h), 4))
        dominant_topic_share.append(round(float(quartile_mix.max()), 4))
        agent_topic_sim.append(round(mean_agent_topic_similarity(q_posts), 4))

        if baseline_mix is None:
            baseline_mix = quartile_mix
            drift_jsd.append(0.0)
        else:
            drift_jsd.append(round(float(jensen_shannon_divergence(baseline_mix, quartile_mix)), 4))

        top_topic_ids.append(top_positive_ids(quartile_mix, topn=3))

    return {
        'topic-entropy_quartiles': topic_entropy,
        'effective-topics_quartiles': effective_topics,
        'dominant-topic-share_quartiles': dominant_topic_share,
        'agent-topic-sim_quartiles': agent_topic_sim,
        'drift-jsd_quartiles': drift_jsd,
        'quartile_topic_mix': quartile_topic_mix,
        'top_topic_ids_per_quartile': top_topic_ids,
        'n_quartiles': len(quartiles),
    }


def analyze_experiments(experiments, n_topics, n_quartiles):
    """Compute topical diversity metrics for all experiments."""
    results = []
    metric_names = [
        'topic-entropy',
        'effective-topics',
        'dominant-topic-share',
        'agent-topic-sim',
        'drift-jsd',
    ]

    for exp in experiments:
        payload = compute_quartile_metrics(exp['posts'], n_topics, n_quartiles)
        result = {
            'set': exp['set'],
            'condition': exp['condition'],
            'directory': exp['directory'],
            'n_posts': len(exp['posts']),
            'n_topics': n_topics,
            'n_quartiles': payload['n_quartiles'],
            'quartile_topic_mix': payload['quartile_topic_mix'],
            'top_topic_ids_per_quartile': payload['top_topic_ids_per_quartile'],
        }
        for metric in metric_names:
            values = payload[f'{metric}_quartiles']
            result[f'{metric}_quartiles'] = values
            result[f'{metric}_delta'] = round(values[-1] - values[0], 4) if len(values) >= 2 else None
        results.append(result)

        print(
            f"  {exp['set']} / {exp['condition']}: "
            f"entropy Δ={result['topic-entropy_delta']:+.3f}  "
            f"dom-share Δ={result['dominant-topic-share_delta']:+.3f}  "
            f"agent-sim Δ={result['agent-topic-sim_delta']:+.3f}  "
            f"drift Q4={result['drift-jsd_quartiles'][-1]:.3f}"
        )

    return results


def write_topic_keywords(topic_keywords, output_dir):
    """Write topic keywords to a plain-text sidecar file."""
    out_path = Path(output_dir) / 'topic_keywords.txt'
    lines = []
    for topic in topic_keywords:
        lines.append(
            f"Topic {topic['topic_id']:02d}: " + ", ".join(topic['keywords'])
        )
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Saved: {out_path}")


def plot_trajectories(results, metric, output_dir, n_quartiles=4):
    """Plot per-condition quartile trajectories for a topical metric."""
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

    n_cols = min(3, max(1, len(conditions)))
    n_rows = math.ceil(len(conditions) / n_cols)
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows),
                             sharey=True, squeeze=False)

    metric_label = metric.replace('-', ' ').title()
    fig.suptitle(
        f'{metric_label} Temporal Trajectories\n'
        f'(global topic model, {n_quartiles} quartiles)',
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
        ax.set_xticklabels([f'Q{i}' for i in x_ticks])
        ax.grid(True, alpha=0.3)

        for s_idx, s_label in enumerate(sets):
            matching = [r for r in results
                        if r['set'] == s_label and r['condition'] == cond]
            if not matching:
                continue
            row = matching[0]
            values = row.get(f'{metric}_quartiles', [])
            if len(values) < 2:
                continue

            delta = row.get(f'{metric}_delta', 0.0)
            color = palette[s_idx % len(palette)]
            marker = marker_list[s_idx % len(marker_list)]
            ax.plot(
                x_ticks[:len(values)],
                values,
                color=color,
                marker=marker,
                linewidth=2.2,
                markersize=7,
                alpha=0.9,
                label=f"{s_label} (Δ={delta:+.3f})",
            )

        ax.legend(fontsize=7, loc='best', framealpha=0.9)

    for idx in range(len(conditions), n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out_path = Path(output_dir) / f'{metric}_trajectories_by_condition.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_heatmap(results, metric, output_dir):
    """Plot Q4-Q1 heatmap for a topical metric."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping heatmap")
        return

    conditions = sorted(set(r['condition'] for r in results))
    sets = sorted(set(r['set'] for r in results))
    matrix = []
    for s_label in sets:
        row = []
        for cond in conditions:
            match = next(
                (
                    r for r in results
                    if r['set'] == s_label and r['condition'] == cond
                ),
                None,
            )
            row.append(match.get(f'{metric}_delta', 0.0) if match else 0.0)
        matrix.append(row)
    arr = np.array(matrix, dtype=np.float64)

    metric_label = metric.replace('-', ' ').title()
    if metric in ('dominant-topic-share', 'agent-topic-sim'):
        cmap = 'RdYlGn_r'
        absmax = float(np.max(np.abs(arr))) if arr.size else 0.0
        vmax = max(0.15, absmax * 1.05)
        vmin = -vmax
        subtitle = 'Green = Less Concentration/Convergence | Red = More'
    elif metric == 'drift-jsd':
        cmap = 'Blues'
        vmax = max(0.15, (float(arr.max()) * 1.05) if arr.size else 0.15)
        vmin = 0.0
        subtitle = 'Darker = Greater drift from Q1'
    else:
        cmap = 'RdYlGn'
        absmax = float(np.max(np.abs(arr))) if arr.size else 0.0
        vmax = max(0.5, absmax * 1.05)
        vmin = -vmax
        subtitle = 'Green = More topical diversity | Red = Less'

    fig, ax = plt.subplots(figsize=(max(8, len(conditions) * 1.6), len(sets) * 1.0 + 1.5))
    im = ax.imshow(arr, cmap=cmap, aspect='auto', vmin=vmin, vmax=vmax)

    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.upper() for c in conditions], fontsize=11)
    ax.set_yticks(range(len(sets)))
    ax.set_yticklabels(sets, fontsize=11)

    for i in range(len(sets)):
        for j in range(len(conditions)):
            val = arr[i, j]
            color = 'white' if (abs(val) > 0.6 and metric != 'drift-jsd') or (metric == 'drift-jsd' and val > 0.08) else 'black'
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


def main():
    parser = argparse.ArgumentParser(
        description='Topical diversity analysis for MoltBook experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--experiments', nargs='+', required=True,
        help='Experiment sets as label=path'
    )
    parser.add_argument(
        '--n-topics', type=int, default=15,
        help='Number of LDA topics for the shared model (default: 15)'
    )
    parser.add_argument(
        '--n-quartiles', type=int, default=4,
        help='Number of temporal quartiles (default: 4)'
    )
    parser.add_argument(
        '--min-posts', type=int, default=8,
        help='Skip experiments with fewer than this many posts (default: 8)'
    )
    parser.add_argument(
        '--min-df', type=int, default=5,
        help='CountVectorizer min_df (default: 5)'
    )
    parser.add_argument(
        '--max-df', type=float, default=0.8,
        help='CountVectorizer max_df (default: 0.8)'
    )
    parser.add_argument(
        '--max-features', type=int, default=5000,
        help='CountVectorizer max_features (default: 5000)'
    )
    parser.add_argument(
        '--topn-words', type=int, default=12,
        help='Top words to save per topic (default: 12)'
    )
    parser.add_argument(
        '--random-state', type=int, default=0,
        help='Random seed for LDA (default: 0)'
    )
    parser.add_argument(
        '--output-dir', default=None,
        help='Directory for plot output and topic keyword sidecar'
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
    docs, experiments = collect_documents(experiment_sets, args.min_posts)

    if not docs:
        print("\nNo documents to analyze.")
        sys.exit(0)

    print(f"\nFitting global LDA: {len(docs)} documents, K={args.n_topics}")
    model, vectorizer, doc_topics = fit_topic_model(
        docs,
        n_topics=args.n_topics,
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=args.max_features,
        random_state=args.random_state,
    )

    topic_keywords = summarize_topic_keywords(model, vectorizer, args.topn_words)
    topic_keyword_map = {t['topic_id']: t['keywords'] for t in topic_keywords}
    print("\nTOPIC KEYWORDS")
    for topic in topic_keywords:
        print(f"  Topic {topic['topic_id']:02d}: {', '.join(topic['keywords'])}")

    topic_lookup = {
        doc['directory']: [] for doc in docs
    }
    for doc, topic_dist in zip(docs, doc_topics):
        topic_lookup[doc['directory']].append(topic_dist)

    for exp in experiments:
        for post, topic_dist in zip(exp['posts'], topic_lookup[exp['directory']]):
            post['topic_dist'] = topic_dist.tolist()

    print("\nPER-EXPERIMENT METRICS")
    results = analyze_experiments(experiments, args.n_topics, args.n_quartiles)
    for row in results:
        row['top_topic_keywords_per_quartile'] = [
            [topic_keyword_map[i] for i in topic_ids]
            for topic_ids in row['top_topic_ids_per_quartile']
        ]

    if not results:
        print("\nNo results to report.")
        sys.exit(0)

    metrics = [
        'topic-entropy',
        'effective-topics',
        'dominant-topic-share',
        'agent-topic-sim',
        'drift-jsd',
    ]

    print(f"\n{'=' * 110}")
    print("SUMMARY: Topical Temporal Deltas (Q4 - Q1)")
    print(f"{'=' * 110}")
    sets = sorted(set(r['set'] for r in results))
    conditions = sorted(set(r['condition'] for r in results))

    for metric in metrics:
        print(f"\n--- {metric.upper()} ---")
        header = f"{'Condition':<12} {'Set':<20} {'Posts':>6}"
        for i in range(1, args.n_quartiles + 1):
            header += f"  {'Q' + str(i):>9}"
        header += f"  {'Delta':>9}"
        print(header)
        print("-" * len(header))

        for cond in conditions:
            for s_label in sets:
                matching = [r for r in results
                            if r['set'] == s_label and r['condition'] == cond]
                if not matching:
                    continue
                row = matching[0]
                values = row.get(f'{metric}_quartiles', [])
                delta = row.get(f'{metric}_delta')
                line = f"{cond:<12} {s_label:<20} {row['n_posts']:>6}"
                for value in values:
                    line += f"  {value:>9.4f}"
                line += f"  {delta:>+9.4f}"
                print(line)

    if args.output_dir:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_topic_keywords(topic_keywords, out_dir)
        if not args.no_plots:
            for metric in metrics:
                plot_trajectories(results, metric, out_dir, args.n_quartiles)
                plot_heatmap(results, metric, out_dir)

    if args.json:
        payload = {
            'config': {
                'n_topics': args.n_topics,
                'n_quartiles': args.n_quartiles,
                'min_posts': args.min_posts,
                'min_df': args.min_df,
                'max_df': args.max_df,
                'max_features': args.max_features,
                'random_state': args.random_state,
            },
            'topics': topic_keywords,
            'results': results,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nJSON results saved to {args.json}")


if __name__ == "__main__":
    main()
