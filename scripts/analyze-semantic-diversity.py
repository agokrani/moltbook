#!/usr/bin/env python3
"""
Semantic diversity analysis for MoltBook experiments.

This script supports two embedding backends:

1. sentence-transformers
   Uses a pretrained embedding model when available. This is the preferred
   path for Alliance GPU jobs.

2. svd
   FIR-runnable fallback when pretrained embedding stacks are unavailable:
   TF-IDF -> TruncatedSVD -> L2 normalization

Embeddings are clustered with k-means. Temporal diversity is measured from
quartile-level cluster distributions and semantic similarities.

Usage:
    python3 scripts/analyze-semantic-diversity.py \
        --experiments "Base=/path/to/base" "Instruct=/path/to/instruct" \
        --embedding-backend auto \
        --n-clusters 15 \
        --output-dir analysis/plots-semantic \
        --json analysis/semantic-diversity.json
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import entropy as scipy_entropy
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import Normalizer


CONDITIONS = ['mag0', 'mag1', 'mag5', 'mag25', 'dom-agi', 'dom-tech',
              'het-dual', 'het-multi']
EXTRA_STOP_WORDS = {
    've', 'll', 're', 'don', 'didn', 'doesn', 'isn', 'aren', 'wasn', 'weren',
    'won', 'wouldn', 'couldn', 'shouldn', 'hadn', 'hasn', 'haven', 'mightn',
    'mustn', 'needn', 'shan', 'just', 'like', 'actually', 'really',
}


def clean_text(text):
    text = text or ""
    text = re.sub(r'https?://\S+', ' ', text)
    text = re.sub(r'\b[a-zA-Z]+n[\'’]t\b', ' not', text)
    text = re.sub(r'[\'’](ve|ll|re|d|m|s)\b', '', text)
    text = re.sub(r'[*_`#>\[\]\(\)\|]+', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def sentence_transformers_available():
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
        return True
    except ImportError:
        return False


def load_posts(exp_dir):
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
        post['text'] = clean_text(f"{post.get('title', '')} {post.get('content', '')}")
        posts.append(post)
    return posts


def find_experiment_dirs(base_path):
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


def parse_experiments(args):
    experiments = {}
    for item in args:
        if '=' in item:
            label, path = item.split('=', 1)
            experiments[label] = path
        else:
            experiments[Path(item).name] = item
    return experiments


def split_quartiles(posts, n_quartiles=4):
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


def normalize_distribution(values):
    arr = np.asarray(values, dtype=np.float64)
    total = arr.sum()
    if total <= 0:
        return np.zeros_like(arr)
    return arr / total


def jensen_shannon_divergence(p, q):
    p = normalize_distribution(p)
    q = normalize_distribution(q)
    if p.sum() == 0 or q.sum() == 0:
        return 0.0
    m = 0.5 * (p + q)
    return 0.5 * (
        scipy_entropy(p, m, base=2) + scipy_entropy(q, m, base=2)
    )


def mean_pairwise_cosine(embeddings):
    if len(embeddings) < 2:
        return 0.0
    sims = cosine_similarity(np.asarray(embeddings))
    n = sims.shape[0]
    vals = []
    for i in range(n):
        for j in range(i + 1, n):
            vals.append(float(sims[i, j]))
    return float(np.mean(vals)) if vals else 0.0


def mean_agent_embedding_similarity(posts):
    by_agent = defaultdict(list)
    for post in posts:
        if 'embedding' not in post:
            continue
        by_agent[post.get('author_name', 'unknown')].append(post['embedding'])

    agent_centroids = []
    for embs in by_agent.values():
        if not embs:
            continue
        centroid = np.asarray(embs, dtype=np.float64).mean(axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        agent_centroids.append(centroid)

    return mean_pairwise_cosine(agent_centroids)


def collect_documents(experiment_sets, min_posts):
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
            for post in posts:
                docs.append(post['text'])

            print(f"  {condition}: {len(posts)} posts")

    return docs, experiments


def build_keyword_tfidf(texts, min_df, max_df, max_features):
    vectorizer = TfidfVectorizer(
        stop_words=sorted(ENGLISH_STOP_WORDS.union(EXTRA_STOP_WORDS)),
        min_df=min_df,
        max_df=max_df,
        max_features=max_features,
        ngram_range=(1, 2),
        token_pattern=r'(?u)\b[a-zA-Z][a-zA-Z]{1,}\b',
    )
    tfidf = vectorizer.fit_transform(texts)
    return vectorizer, tfidf


def build_svd_embeddings(tfidf, svd_dim, random_state):
    max_rank = max(2, min(tfidf.shape[0] - 1, tfidf.shape[1] - 1))
    n_components = min(svd_dim, max_rank)
    svd = TruncatedSVD(n_components=n_components, random_state=random_state)
    dense = svd.fit_transform(tfidf)
    dense = Normalizer(copy=False).fit_transform(dense)
    return dense


def build_sentence_transformer_embeddings(texts, model_name, batch_size, device):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device=device)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )
    return np.asarray(embeddings, dtype=np.float32)


def build_semantic_space(
    texts,
    backend,
    embedding_model,
    batch_size,
    device,
    svd_dim,
    min_df,
    max_df,
    max_features,
    random_state,
):
    vectorizer, tfidf = build_keyword_tfidf(texts, min_df, max_df, max_features)

    if backend == 'sentence-transformers':
        embeddings = build_sentence_transformer_embeddings(
            texts,
            model_name=embedding_model,
            batch_size=batch_size,
            device=device,
        )
        return vectorizer, tfidf, embeddings

    if backend == 'svd':
        embeddings = build_svd_embeddings(tfidf, svd_dim, random_state)
        return vectorizer, tfidf, embeddings

    raise ValueError(f"Unsupported embedding backend: {backend}")


def cluster_embeddings(embeddings, n_clusters, random_state):
    model = MiniBatchKMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        batch_size=1024,
        n_init='auto',
    )
    labels = model.fit_predict(embeddings)
    return model, labels


def summarize_cluster_keywords(tfidf, labels, vectorizer, topn):
    vocab = vectorizer.get_feature_names_out()
    clusters = []
    for cluster_id in sorted(set(labels.tolist())):
        idx = np.where(labels == cluster_id)[0]
        mean_tfidf = np.asarray(tfidf[idx].mean(axis=0)).ravel()
        top_ids = mean_tfidf.argsort()[-topn:][::-1]
        clusters.append({
            'cluster_id': int(cluster_id),
            'keywords': [vocab[i] for i in top_ids],
            'n_docs': int(len(idx)),
        })
    return clusters


def compute_quartile_metrics(posts, n_clusters, n_quartiles):
    quartiles = split_quartiles(posts, n_quartiles)

    cluster_entropy = []
    effective_clusters = []
    dominant_cluster_share = []
    within_quartile_cosine = []
    agent_embedding_sim = []
    drift_jsd = []
    cluster_distribution_quartiles = []
    top_cluster_ids_per_quartile = []

    baseline = None
    for q_posts in quartiles:
        labels = [int(p['cluster_id']) for p in q_posts]
        counts = np.zeros(n_clusters, dtype=np.float64)
        for label, count in Counter(labels).items():
            counts[label] = count
        dist = normalize_distribution(counts)
        cluster_distribution_quartiles.append([round(float(x), 6) for x in dist])
        top_cluster_ids_per_quartile.append([int(i) for i in dist.argsort()[-3:][::-1]])

        h = float(scipy_entropy(dist, base=2))
        cluster_entropy.append(round(h, 4))
        effective_clusters.append(round(float(2 ** h), 4))
        dominant_cluster_share.append(round(float(dist.max()), 4))
        within_quartile_cosine.append(round(mean_pairwise_cosine([p['embedding'] for p in q_posts]), 4))
        agent_embedding_sim.append(round(mean_agent_embedding_similarity(q_posts), 4))

        if baseline is None:
            baseline = dist
            drift_jsd.append(0.0)
        else:
            drift_jsd.append(round(float(jensen_shannon_divergence(baseline, dist)), 4))

    return {
        'cluster-entropy_quartiles': cluster_entropy,
        'effective-clusters_quartiles': effective_clusters,
        'dominant-cluster-share_quartiles': dominant_cluster_share,
        'within-quartile-cosine_quartiles': within_quartile_cosine,
        'agent-embedding-sim_quartiles': agent_embedding_sim,
        'drift-jsd_quartiles': drift_jsd,
        'cluster_distribution_quartiles': cluster_distribution_quartiles,
        'top_cluster_ids_per_quartile': top_cluster_ids_per_quartile,
        'n_quartiles': len(quartiles),
    }


def analyze_experiments(experiments, n_clusters, n_quartiles):
    results = []
    metrics = [
        'cluster-entropy',
        'effective-clusters',
        'dominant-cluster-share',
        'within-quartile-cosine',
        'agent-embedding-sim',
        'drift-jsd',
    ]
    print("\nPER-EXPERIMENT METRICS")
    for exp in experiments:
        payload = compute_quartile_metrics(exp['posts'], n_clusters, n_quartiles)
        result = {
            'set': exp['set'],
            'condition': exp['condition'],
            'directory': exp['directory'],
            'n_posts': len(exp['posts']),
            'n_clusters': n_clusters,
            'n_quartiles': payload['n_quartiles'],
            'cluster_distribution_quartiles': payload['cluster_distribution_quartiles'],
            'top_cluster_ids_per_quartile': payload['top_cluster_ids_per_quartile'],
        }
        for metric in metrics:
            values = payload[f'{metric}_quartiles']
            result[f'{metric}_quartiles'] = values
            result[f'{metric}_delta'] = round(values[-1] - values[0], 4) if len(values) >= 2 else None
        results.append(result)

        print(
            f"  {exp['set']} / {exp['condition']}: "
            f"cluster-entropy Δ={result['cluster-entropy_delta']:+.3f}  "
            f"dom-share Δ={result['dominant-cluster-share_delta']:+.3f}  "
            f"within-cos Δ={result['within-quartile-cosine_delta']:+.3f}  "
            f"agent-sim Δ={result['agent-embedding-sim_delta']:+.3f}"
        )

    return results


def write_cluster_keywords(cluster_keywords, output_dir):
    out_path = Path(output_dir) / 'cluster_keywords.txt'
    lines = []
    for cluster in cluster_keywords:
        lines.append(
            f"Cluster {cluster['cluster_id']:02d} ({cluster['n_docs']} docs): "
            + ", ".join(cluster['keywords'])
        )
    out_path.write_text("\n".join(lines) + "\n")
    print(f"Saved: {out_path}")


def plot_trajectories(results, metric, output_dir, n_quartiles=4):
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
        f'(semantic embeddings + k-means, {n_quartiles} quartiles)',
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
            matches = [r for r in results if r['set'] == s_label and r['condition'] == cond]
            if not matches:
                continue
            row = matches[0]
            values = row.get(f'{metric}_quartiles', [])
            if len(values) < 2:
                continue
            delta = row.get(f'{metric}_delta', 0.0)
            ax.plot(
                x_ticks[:len(values)],
                values,
                color=palette[s_idx % len(palette)],
                marker=marker_list[s_idx % len(marker_list)],
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
                (r for r in results if r['set'] == s_label and r['condition'] == cond),
                None,
            )
            row.append(match.get(f'{metric}_delta', 0.0) if match else 0.0)
        matrix.append(row)
    arr = np.asarray(matrix, dtype=np.float64)

    metric_label = metric.replace('-', ' ').title()
    if metric in ('dominant-cluster-share', 'within-quartile-cosine', 'agent-embedding-sim'):
        cmap = 'RdYlGn_r'
        vmin, vmax = -0.2, 0.2
        subtitle = 'Green = Less convergence | Red = More'
    elif metric == 'drift-jsd':
        cmap = 'Blues'
        vmin, vmax = 0.0, max(0.2, float(arr.max()) if arr.size else 0.2)
        subtitle = 'Darker = Greater drift from Q1'
    else:
        cmap = 'RdYlGn'
        vmin, vmax = -1.5, 1.5
        subtitle = 'Green = More semantic diversity | Red = Less'

    fig, ax = plt.subplots(figsize=(max(8, len(conditions) * 1.6), len(sets) * 1.0 + 1.5))
    im = ax.imshow(arr, cmap=cmap, aspect='auto', vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.upper() for c in conditions], fontsize=11)
    ax.set_yticks(range(len(sets)))
    ax.set_yticklabels(sets, fontsize=11)

    for i in range(len(sets)):
        for j in range(len(conditions)):
            val = arr[i, j]
            color = 'white' if abs(val) > 0.08 else 'black'
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
        description='Semantic diversity analysis for MoltBook experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--experiments', nargs='+', required=True, help='Experiment sets as label=path')
    parser.add_argument(
        '--embedding-backend',
        choices=['auto', 'sentence-transformers', 'svd'],
        default='auto',
        help='Embedding backend: auto, sentence-transformers, or svd fallback (default: auto)',
    )
    parser.add_argument(
        '--embedding-model',
        default='BAAI/bge-large-en-v1.5',
        help='Sentence-transformers model name when using the embedding backend (default: BAAI/bge-large-en-v1.5)',
    )
    parser.add_argument('--device', default='auto', help='Embedding device for sentence-transformers (default: auto)')
    parser.add_argument('--batch-size', type=int, default=64, help='Sentence-transformers batch size (default: 64)')
    parser.add_argument('--n-clusters', type=int, default=15, help='Number of k-means clusters (default: 15)')
    parser.add_argument('--svd-dim', type=int, default=128, help='Dense embedding dimension after SVD (default: 128)')
    parser.add_argument('--n-quartiles', type=int, default=4, help='Number of temporal quartiles (default: 4)')
    parser.add_argument('--min-posts', type=int, default=8, help='Skip experiments with fewer than this many posts')
    parser.add_argument('--min-df', type=int, default=5, help='TF-IDF min_df (default: 5)')
    parser.add_argument('--max-df', type=float, default=0.8, help='TF-IDF max_df (default: 0.8)')
    parser.add_argument('--max-features', type=int, default=12000, help='TF-IDF max_features (default: 12000)')
    parser.add_argument('--topn-words', type=int, default=12, help='Top words per cluster to save (default: 12)')
    parser.add_argument('--random-state', type=int, default=0, help='Random seed (default: 0)')
    parser.add_argument('--output-dir', default=None, help='Directory for plot output and cluster keyword sidecar')
    parser.add_argument('--json', default=None, help='Path for JSON results output')
    parser.add_argument('--no-plots', action='store_true', help='Skip plot generation')
    args = parser.parse_args()

    experiment_sets = parse_experiments(args.experiments)
    texts, experiments = collect_documents(experiment_sets, args.min_posts)
    if not texts:
        print("\nNo documents to analyze.")
        sys.exit(0)

    backend = args.embedding_backend
    if backend == 'auto':
        backend = 'sentence-transformers' if sentence_transformers_available() else 'svd'
    if backend == 'sentence-transformers' and not sentence_transformers_available():
        print("\nsentence-transformers is not installed in this environment.")
        print("Either install it and rerun with --embedding-backend sentence-transformers,")
        print("or rerun with --embedding-backend svd for the FIR-safe fallback.")
        sys.exit(1)

    device = args.device
    if backend == 'sentence-transformers' and device == 'auto':
        try:
            import torch
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        except ImportError:
            device = 'cpu'

    print(
        f"\nBuilding semantic space: {len(texts)} documents, "
        f"backend={backend}, "
        f"{'model=' + args.embedding_model if backend == 'sentence-transformers' else 'svd_dim=' + str(args.svd_dim)}"
    )
    vectorizer, tfidf, embeddings = build_semantic_space(
        texts,
        backend=backend,
        embedding_model=args.embedding_model,
        batch_size=args.batch_size,
        device=device,
        svd_dim=args.svd_dim,
        min_df=args.min_df,
        max_df=args.max_df,
        max_features=args.max_features,
        random_state=args.random_state,
    )

    print(f"Clustering embeddings: K={args.n_clusters}")
    cluster_model, labels = cluster_embeddings(
        embeddings,
        n_clusters=args.n_clusters,
        random_state=args.random_state,
    )
    cluster_keywords = summarize_cluster_keywords(
        tfidf,
        labels,
        vectorizer,
        args.topn_words,
    )
    cluster_keyword_map = {c['cluster_id']: c['keywords'] for c in cluster_keywords}

    print("\nCLUSTER KEYWORDS")
    for cluster in cluster_keywords:
        print(f"  Cluster {cluster['cluster_id']:02d}: {', '.join(cluster['keywords'])}")

    offset = 0
    for exp in experiments:
        n = len(exp['posts'])
        exp_embs = embeddings[offset:offset + n]
        exp_labels = labels[offset:offset + n]
        for post, emb, cluster_id in zip(exp['posts'], exp_embs, exp_labels):
            post['embedding'] = emb.tolist()
            post['cluster_id'] = int(cluster_id)
        offset += n

    results = analyze_experiments(experiments, args.n_clusters, args.n_quartiles)
    for row in results:
        row['top_cluster_keywords_per_quartile'] = [
            [cluster_keyword_map[i] for i in cluster_ids]
            for cluster_ids in row['top_cluster_ids_per_quartile']
        ]

    metrics = [
        'cluster-entropy',
        'effective-clusters',
        'dominant-cluster-share',
        'within-quartile-cosine',
        'agent-embedding-sim',
        'drift-jsd',
    ]

    print(f"\n{'=' * 110}")
    print("SUMMARY: Semantic Temporal Deltas (Q4 - Q1)")
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
                matches = [r for r in results if r['set'] == s_label and r['condition'] == cond]
                if not matches:
                    continue
                row = matches[0]
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
        write_cluster_keywords(cluster_keywords, out_dir)
        if not args.no_plots:
            for metric in metrics:
                plot_trajectories(results, metric, out_dir, args.n_quartiles)
                plot_heatmap(results, metric, out_dir)

    if args.json:
        payload = {
            'config': {
                'embedding_backend': backend,
                'embedding_model': args.embedding_model if backend == 'sentence-transformers' else None,
                'device': device if backend == 'sentence-transformers' else None,
                'batch_size': args.batch_size if backend == 'sentence-transformers' else None,
                'n_clusters': args.n_clusters,
                'svd_dim': args.svd_dim,
                'n_quartiles': args.n_quartiles,
                'min_posts': args.min_posts,
                'min_df': args.min_df,
                'max_df': args.max_df,
                'max_features': args.max_features,
                'random_state': args.random_state,
            },
            'clusters': cluster_keywords,
            'results': results,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"\nJSON results saved to {args.json}")


if __name__ == '__main__':
    main()
