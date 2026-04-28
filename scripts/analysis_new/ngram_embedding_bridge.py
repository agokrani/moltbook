#!/usr/bin/env python3
"""Analysis 3: Do phrase-sharing posts cluster in embedding space?"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

from load_entropy_data import SEED_AUTHORS, load_all_scales
from time_binned_lexical_metrics_5gram import tokenize, ngrams

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
TOP_K = 10
NGRAM_N = 5
TOP_NGRAMS_PATH = Path("findings/entropy-collapse-multiscale-new-5gram/top_ngrams/top_ngrams.json")
OUT_DIR = Path("findings/entropy-collapse-scaling/embedding_bridge")
SCALES = ["n10", "n20", "n30"]
N_RANDOM_SAMPLES = 1000
RANDOM_SEED = 42


def load_top_ngrams(k: int = TOP_K) -> list[str]:
    with TOP_NGRAMS_PATH.open() as f:
        data = json.load(f)
    return [e["phrase"] for e in data["all_0_60"][str(NGRAM_N)][:k]]


def load_embeddings(scale: str) -> dict[str, np.ndarray]:
    """Load embeddings NPZ, return {post_id: embedding_vector}."""
    path = Path(f"embeddings_{scale}.npz")
    data = np.load(path, allow_pickle=True)
    ids = data["post_id"]
    embs = data["embeddings"]
    return {str(pid): embs[i] for i, pid in enumerate(ids)}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def mean_pairwise_cosine(vectors: np.ndarray, max_pairs: int = 5000) -> float:
    """Compute mean pairwise cosine similarity. Sample if too many pairs."""
    n = len(vectors)
    if n < 2:
        return 0.0

    # Normalize for fast cosine via dot product
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = vectors / norms

    n_pairs = n * (n - 1) // 2
    if n_pairs <= max_pairs:
        # Compute full similarity matrix
        sim_matrix = normed @ normed.T
        # Extract upper triangle
        indices = np.triu_indices(n, k=1)
        return float(np.mean(sim_matrix[indices]))
    else:
        # Sample pairs
        rng = np.random.RandomState(RANDOM_SEED)
        idx_a = rng.randint(0, n, max_pairs)
        idx_b = rng.randint(0, n, max_pairs)
        # Avoid self-pairs
        mask = idx_a != idx_b
        idx_a, idx_b = idx_a[mask], idx_b[mask]
        sims = np.sum(normed[idx_a] * normed[idx_b], axis=1)
        return float(np.mean(sims))


def random_baseline_cosine(all_vectors: np.ndarray, group_size: int,
                           n_samples: int = N_RANDOM_SAMPLES) -> dict:
    """Compute random baseline: mean cosine for random groups of same size."""
    n = len(all_vectors)
    if group_size < 2 or group_size > n:
        return {"mean": 0.0, "std": 0.0, "samples": []}

    rng = np.random.RandomState(RANDOM_SEED)
    samples = []
    for _ in range(n_samples):
        idx = rng.choice(n, size=min(group_size, n), replace=False)
        subset = all_vectors[idx]
        samples.append(mean_pairwise_cosine(subset, max_pairs=2000))

    return {
        "mean": float(np.mean(samples)),
        "std": float(np.std(samples)),
        "samples": samples,
    }


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    top_phrases = load_top_ngrams(TOP_K)

    # Load all records (we need post_id -> text mapping)
    print("Loading all scales...")
    records = load_all_scales()
    agent_records = [r for r in records if not r.is_seed]
    print(f"  Agent posts: {len(agent_records)}")

    # Build post_id -> record map and post_id -> n-gram set
    post_map = {r.post_id: r for r in agent_records}

    # For each post, compute which top phrases it contains
    print("Matching phrases to posts...")
    phrase_post_ids: dict[str, list[str]] = defaultdict(list)
    for rec in agent_records:
        tokens = tokenize(rec.full_text)
        grams = {" ".join(g) for g in ngrams(tokens, NGRAM_N)}
        for phrase in top_phrases:
            if phrase in grams:
                phrase_post_ids[phrase].append(rec.post_id)

    print("Phrase post counts:")
    for phrase in top_phrases:
        print(f'  "{phrase}": {len(phrase_post_ids[phrase])} posts')

    # Load embeddings for all scales
    print("\nLoading embeddings...")
    all_emb_map: dict[str, np.ndarray] = {}
    for scale in SCALES:
        scale_embs = load_embeddings(scale)
        all_emb_map.update(scale_embs)
    print(f"  Total embeddings: {len(all_emb_map)}")

    # Match post_ids to embeddings
    matched_ids = set(post_map.keys()) & set(all_emb_map.keys())
    print(f"  Matched post IDs: {len(matched_ids)} / {len(post_map)} ({len(matched_ids)/len(post_map):.1%})")

    # Build full embedding matrix for baseline
    all_ids_list = sorted(matched_ids)
    all_vectors = np.array([all_emb_map[pid] for pid in all_ids_list])

    # Compute per-phrase cosine similarity
    print("\nComputing within-group cosine similarity...")
    results = []
    phrase_vectors: dict[str, np.ndarray] = {}

    for phrase in top_phrases:
        pids = [pid for pid in phrase_post_ids[phrase] if pid in matched_ids]
        if len(pids) < 2:
            print(f'  "{phrase}": only {len(pids)} matched posts, skipping')
            results.append({
                "phrase": phrase,
                "n_posts": len(pids),
                "within_cosine": 0.0,
                "baseline_mean": 0.0,
                "baseline_std": 0.0,
                "lift": 0.0,
            })
            continue

        vecs = np.array([all_emb_map[pid] for pid in pids])
        phrase_vectors[phrase] = vecs
        within_cos = mean_pairwise_cosine(vecs)

        # Random baseline with same group size
        baseline = random_baseline_cosine(all_vectors, len(pids), n_samples=500)

        lift = within_cos - baseline["mean"]
        results.append({
            "phrase": phrase,
            "n_posts": len(pids),
            "within_cosine": round(within_cos, 4),
            "baseline_mean": round(baseline["mean"], 4),
            "baseline_std": round(baseline["std"], 4),
            "lift": round(lift, 4),
        })
        print(f'  "{phrase}": within={within_cos:.4f}, baseline={baseline["mean"]:.4f} '
              f'(+{lift:.4f}), n={len(pids)}')

    # Write CSV
    csv_path = OUT_DIR / "embedding_similarity.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nWrote {csv_path}")

    # ---------------------------------------------------------------------------
    # PLOTS
    # ---------------------------------------------------------------------------
    # Plot 1: Bar chart — within-group vs baseline cosine similarity
    print("Generating similarity bar chart...")
    fig, ax = plt.subplots(figsize=(12, 6))

    valid_results = [r for r in results if r["n_posts"] >= 2]
    phrases_plot = [r["phrase"] for r in valid_results]
    within_vals = [r["within_cosine"] for r in valid_results]
    baseline_vals = [r["baseline_mean"] for r in valid_results]
    baseline_stds = [r["baseline_std"] for r in valid_results]

    x = np.arange(len(phrases_plot))
    width = 0.35

    bars1 = ax.bar(x - width / 2, within_vals, width, label="Within n-gram group",
                   color="#1565C0", edgecolor="white")
    bars2 = ax.bar(x + width / 2, baseline_vals, width, label="Random baseline",
                   color="#BDBDBD", edgecolor="white",
                   yerr=baseline_stds, capsize=3)

    ax.set_xticks(x)
    ax.set_xticklabels([f'{p[:25]}{"…" if len(p) > 25 else ""}' for p in phrases_plot],
                       rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Mean pairwise cosine similarity")
    ax.set_title("Semantic Clustering: Posts sharing the same 5-gram vs random baseline")
    ax.legend(fontsize=9)
    ax.grid(axis="y", alpha=0.2)

    fig.tight_layout()
    fig.savefig(OUT_DIR / "cosine_similarity_bar.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # Plot 2: UMAP scatter plot
    print("Computing UMAP projection (this may take a moment)...")
    try:
        import umap

        # Subsample for UMAP if too many points
        max_umap = 8000
        if len(all_vectors) > max_umap:
            rng = np.random.RandomState(RANDOM_SEED)
            umap_idx = rng.choice(len(all_vectors), max_umap, replace=False)
        else:
            umap_idx = np.arange(len(all_vectors))

        umap_vectors = all_vectors[umap_idx]
        umap_ids = [all_ids_list[i] for i in umap_idx]

        # Also include all phrase-matched posts
        phrase_id_sets = {}
        extra_ids = set()
        for phrase in top_phrases[:6]:  # Top 6 for visibility
            pids = set(pid for pid in phrase_post_ids[phrase] if pid in matched_ids)
            phrase_id_sets[phrase] = pids
            extra_ids.update(pids)

        # Add missing phrase posts to UMAP set
        existing = set(umap_ids)
        for pid in extra_ids:
            if pid not in existing:
                idx = all_ids_list.index(pid)
                umap_idx = np.append(umap_idx, idx)
                umap_ids.append(pid)
        umap_vectors = all_vectors[umap_idx]

        reducer = umap.UMAP(n_components=2, random_state=RANDOM_SEED, n_neighbors=30,
                            min_dist=0.3, metric="cosine")
        embedding_2d = reducer.fit_transform(umap_vectors)

        # Build id -> 2D coords map
        id_to_2d = {pid: embedding_2d[i] for i, pid in enumerate(umap_ids)}

        # Plot
        fig, ax = plt.subplots(figsize=(14, 10))

        # Background points (grey)
        all_x = embedding_2d[:, 0]
        all_y = embedding_2d[:, 1]
        ax.scatter(all_x, all_y, s=3, c="#E0E0E0", alpha=0.3, rasterized=True)

        # Overlay phrase groups with distinct colors
        phrase_colors = ["#E53935", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#00ACC1"]
        for pi, phrase in enumerate(top_phrases[:6]):
            pids = phrase_id_sets.get(phrase, set())
            coords = [id_to_2d[pid] for pid in pids if pid in id_to_2d]
            if not coords:
                continue
            coords = np.array(coords)
            ax.scatter(coords[:, 0], coords[:, 1], s=15, c=phrase_colors[pi],
                       alpha=0.7, label=f'{phrase[:30]}… ({len(coords)})',
                       edgecolors="white", linewidth=0.3)

        ax.set_xlabel("UMAP-1")
        ax.set_ylabel("UMAP-2")
        ax.set_title("UMAP of Post Embeddings — Colored by Shared 5-gram Phrase")
        ax.legend(fontsize=7, loc="best", markerscale=2)

        fig.tight_layout()
        fig.savefig(OUT_DIR / "umap_phrase_clusters.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote {OUT_DIR / 'umap_phrase_clusters.png'}")

        # Interactive HTML with plotly
        try:
            import plotly.graph_objects as go

            traces = [
                go.Scatter(
                    x=all_x.tolist(), y=all_y.tolist(),
                    mode="markers",
                    marker=dict(size=2, color="#E0E0E0", opacity=0.3),
                    name="All posts",
                    hoverinfo="skip",
                )
            ]

            for pi, phrase in enumerate(top_phrases[:6]):
                pids = sorted(phrase_id_sets.get(phrase, set()))
                coords = []
                hover_texts = []
                for pid in pids:
                    if pid in id_to_2d:
                        coords.append(id_to_2d[pid])
                        rec = post_map.get(pid)
                        if rec:
                            hover_texts.append(
                                f"<b>{rec.title[:60]}</b><br>"
                                f"Author: {rec.author_name}<br>"
                                f"Min: {rec.minutes_elapsed:.1f}<br>"
                                f"Scale: {rec.scale}, Cond: {rec.condition}"
                            )
                        else:
                            hover_texts.append(pid)
                if not coords:
                    continue
                coords = np.array(coords)
                traces.append(
                    go.Scatter(
                        x=coords[:, 0].tolist(), y=coords[:, 1].tolist(),
                        mode="markers",
                        marker=dict(size=5, color=phrase_colors[pi], opacity=0.7),
                        name=f'{phrase[:30]}… ({len(coords)})',
                        text=hover_texts,
                        hoverinfo="text",
                    )
                )

            fig_html = go.Figure(data=traces)
            fig_html.update_layout(
                title="UMAP Post Embeddings — Shared 5-gram Phrases (interactive)",
                xaxis_title="UMAP-1", yaxis_title="UMAP-2",
                width=1200, height=800,
                template="plotly_white",
            )
            html_path = OUT_DIR / "umap_interactive.html"
            fig_html.write_html(str(html_path))
            print(f"Wrote {html_path}")
        except ImportError:
            print("  plotly not installed, skipping interactive HTML")

    except ImportError:
        print("  umap-learn not installed, skipping UMAP plot")

    # Write JSON summary
    summary = {
        "top_k": TOP_K,
        "total_embeddings": len(all_emb_map),
        "matched_posts": len(matched_ids),
        "match_rate": round(len(matched_ids) / len(post_map), 4) if post_map else 0,
        "results": results,
    }
    with (OUT_DIR / "embedding_bridge_summary.json").open("w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {OUT_DIR / 'embedding_bridge_summary.json'}")

    print("\nDone!")


if __name__ == "__main__":
    main()
