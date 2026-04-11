#!/usr/bin/env python3
"""Analysis 3: Semantic collapse — phrase clusters in embedding space.

For each run, project all post embeddings to 2D using multiple methods
(t-SNE, UMAP, PCA), then highlight posts containing each of the run's
top-5 phrases individually. One subplot per phrase per run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

from load_entropy_data import (
    CONDITION_ORDER,
    CONDITION_LABELS,
    load_all_scales,
    group_records,
)
from time_binned_lexical_metrics_5gram import (
    tokenize,
    ngrams,
    prepare_posts,
    ngram_counter,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
NGRAM_N = 5
TOP_K = 5
SCALES = ["n10", "n20", "n30"]
SCALE_LABELS = {"n10": "10 agents", "n20": "20 agents", "n30": "30 agents"}
OUT_DIR = Path("findings/entropy-collapse-scaling/embedding_bridge")

COND_COLORS = {
    "mag0": "#6B7280", "mag1": "#E11D48", "mag5": "#F97316",
    "mag25": "#EAB308", "dom-agi": "#3B82F6", "dom-tech": "#10B981",
}
PHRASE_COLOR = "#E53935"


def load_embeddings(scale: str) -> dict[str, np.ndarray]:
    path = Path(f"embeddings_{scale}.npz")
    data = np.load(path, allow_pickle=True)
    ids = data["post_id"]
    embs = data["embeddings"]
    return {str(pid): embs[i] for i, pid in enumerate(ids)}


def reduce_tsne(vectors: np.ndarray, perplexity: int = 30) -> np.ndarray:
    from sklearn.manifold import TSNE
    perp = min(perplexity, len(vectors) - 1)
    reducer = TSNE(n_components=2, perplexity=perp, random_state=42,
                   metric="cosine", init="pca", learning_rate="auto")
    return reducer.fit_transform(vectors)


def reduce_umap(vectors: np.ndarray) -> np.ndarray:
    import umap
    n_neighbors = min(30, len(vectors) - 1)
    reducer = umap.UMAP(n_components=2, n_neighbors=n_neighbors,
                        min_dist=0.3, metric="cosine", random_state=42)
    return reducer.fit_transform(vectors)


def reduce_pca(vectors: np.ndarray) -> np.ndarray:
    from sklearn.decomposition import PCA
    reducer = PCA(n_components=2, random_state=42)
    return reducer.fit_transform(vectors)


def plot_grid(run_data: dict, run_coords: dict, method_name: str,
              scale: str, out_path: Path) -> None:
    """6 rows (conditions) × 5 cols (top-1 through top-5), one phrase highlighted per panel."""

    fig, axes = plt.subplots(
        len(CONDITION_ORDER), TOP_K,
        figsize=(25, 30), squeeze=False,
    )
    fig.patch.set_facecolor("white")

    for ri, cond in enumerate(CONDITION_ORDER):
        matched_key = None
        for k in run_data:
            if k[0] == scale and k[1] == cond:
                matched_key = k
                break

        for ci in range(TOP_K):
            ax = axes[ri, ci]

            if matched_key is None or matched_key not in run_coords:
                ax.set_visible(False)
                continue

            data = run_data[matched_key]
            coords = run_coords[matched_key]
            tags = data["phrase_tags"]  # shape (n_posts,) with values per phrase rank
            phrases = data["phrases"]

            if ci >= len(phrases):
                ax.set_visible(False)
                continue

            # Grey: everything NOT this phrase
            mask_other = tags[:, ci] == 0
            mask_phrase = tags[:, ci] == 1
            n_match = int(np.sum(mask_phrase))

            if np.any(mask_other):
                ax.scatter(
                    coords[mask_other, 0], coords[mask_other, 1],
                    s=5, c="#D1D5DB", alpha=0.25, zorder=1, edgecolors="none",
                )

            if n_match > 0:
                ax.scatter(
                    coords[mask_phrase, 0], coords[mask_phrase, 1],
                    s=20, c=PHRASE_COLOR, alpha=0.7, zorder=3,
                    edgecolors="white", linewidths=0.3,
                )

            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)

            # Phrase text inside panel
            phrase_text = phrases[ci][:30] + ("…" if len(phrases[ci]) > 30 else "")
            ax.text(
                0.5, 0.02,
                f'"{phrase_text}" ({n_match})',
                transform=ax.transAxes, ha="center", va="bottom",
                fontsize=6, color="#666", style="italic",
            )

            # Column headers
            if ri == 0:
                ax.set_title(f"Top {ci + 1}", fontsize=13, fontweight="bold", pad=8)

            # Row labels
            if ci == 0:
                ax.set_ylabel(
                    CONDITION_LABELS.get(cond, cond),
                    fontsize=11, fontweight="bold",
                    color=COND_COLORS[cond],
                )

    fig.suptitle(
        f"Phrase clusters in embedding space — {method_name} ({SCALE_LABELS[scale]})",
        fontsize=22, fontweight="bold", y=1.0, color="#111",
    )
    fig.text(
        0.5, 0.98,
        "Each panel highlights posts containing ONE phrase (red) against all other posts (grey). "
        "Tight red clusters = semantic convergence.",
        ha="center", fontsize=11, color="#666",
    )

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"  Wrote {out_path.name}")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales()
    agent_records = [r for r in records if not r.is_seed]

    print("Loading embeddings...")
    emb_map: dict[str, np.ndarray] = {}
    for scale in SCALES:
        scale_embs = load_embeddings(scale)
        emb_map.update(scale_embs)
        print(f"  {scale}: {len(scale_embs)} embeddings")

    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))

    # Find each run's top-5 phrases
    print("\nFinding each run's top-5 5-grams...")
    run_top_phrases: dict[tuple, list[str]] = {}
    for key, recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        counter = ngram_counter(prepared, NGRAM_N)
        top = [" ".join(g) for g, _ in counter.most_common(TOP_K)]
        run_top_phrases[key] = top

    # Tag posts — phrase_tags is (n_posts, TOP_K) binary matrix
    print("Tagging posts by phrase membership...")
    run_data: dict[tuple, dict] = {}

    for key, recs in sorted(by_run.items()):
        phrases = run_top_phrases.get(key, [])
        if not phrases:
            continue

        vectors = []
        tag_matrix = []

        for rec in recs:
            if rec.post_id not in emb_map:
                continue
            vectors.append(emb_map[rec.post_id])

            toks = tokenize(rec.full_text)
            grams = {" ".join(g) for g in ngrams(toks, NGRAM_N)}
            row = [1 if (pi < len(phrases) and phrases[pi] in grams) else 0
                   for pi in range(TOP_K)]
            tag_matrix.append(row)

        if len(vectors) < 20:
            continue

        run_data[key] = {
            "vectors": np.array(vectors),
            "phrase_tags": np.array(tag_matrix),
            "phrases": phrases,
            "n_posts": len(vectors),
        }

    # Generate plots for n20 and n30 (n10 has poor embedding coverage)
    target_scales = ["n20", "n30"]
    methods = {
        "t-SNE": reduce_tsne,
        "UMAP": reduce_umap,
        "PCA": reduce_pca,
    }

    for scale in target_scales:
        # Get run keys for this scale
        scale_keys = [k for k in run_data if k[0] == scale]
        if not scale_keys:
            print(f"\nSkipping {scale} — no data")
            continue

        for method_name, reduce_fn in methods.items():
            print(f"\n{method_name} for {scale}...")
            run_coords: dict[tuple, np.ndarray] = {}

            for key in scale_keys:
                data = run_data[key]
                coords = reduce_fn(data["vectors"])
                run_coords[key] = coords
                n_tagged = int(np.sum(data["phrase_tags"].any(axis=1)))
                print(f"  {key[1]}: {data['n_posts']} posts, {n_tagged} tagged")

            slug = method_name.lower().replace("-", "").replace(" ", "_")
            out_path = OUT_DIR / f"phrase_clusters_{slug}_{scale}.png"
            plot_grid(run_data, run_coords, method_name, scale, out_path)

    # Summary
    summary = {
        "methods": list(methods.keys()),
        "scales": target_scales,
        "top_k": TOP_K,
        "total_runs": len(run_data),
        "per_run": {},
    }
    for key, data in sorted(run_data.items()):
        scale, cond, _ = key
        tags = data["phrase_tags"]
        summary["per_run"][f"{scale}/{cond}"] = {
            "n_posts": data["n_posts"],
            "phrases": data["phrases"],
            "n_tagged_per_phrase": [int(tags[:, i].sum()) for i in range(TOP_K)],
        }

    with (OUT_DIR / "semantic_collapse_summary.json").open("w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("\nWrote semantic_collapse_summary.json")
    print("Done!")


if __name__ == "__main__":
    main()
