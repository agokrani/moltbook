#!/usr/bin/env python3
"""Compute topic assignments for all models using GPT's k=6 clusters as reference.

Step 1: Cluster GPT embeddings with KMeans (k=6), label via LLM.
Step 2: For each non-GPT model, classify posts into those 6 topics via LLM.
Step 3: Compute MDS coordinates per model and save plot_data NPZ files.

Outputs go to findings/entropy-collapse-scaling/topic_convergence_all/
Each model gets: plot_data_{model}_{scale}.npz + .json

Usage:
    python3 scripts/analysis_new/compute_topics.py
    python3 scripts/analysis_new/compute_topics.py --skip-llm   # use cached labels only
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time as time_mod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/moltbook-cache")

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.manifold import MDS
from sklearn.metrics import silhouette_score
from sklearn.metrics.pairwise import cosine_distances
from sklearn.preprocessing import normalize

try:
    import requests
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
except ImportError:
    requests = None

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
K = 6
PCA_DIMS = 50
EMB_DIR = Path("experiments/entropy-collapse/data/embeddings")
OUT_DIR = Path("findings/entropy-collapse-scaling/topic_convergence_all")

# Models and their available scales
MODELS = {
    "gpt": {"prefix": "", "scales": ["n10", "n20", "n30"], "label": "GPT-5"},
    "gemini": {"prefix": "gemini_", "scales": ["n10", "n20", "n30"], "label": "Gemini Flash Lite"},
    "glm": {"prefix": "glm-5_", "scales": ["n10"], "label": "GLM-5"},
    "kimi": {"prefix": "kimi-k2.5_", "scales": ["n10"], "label": "Kimi K2.5"},
}

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CHAT_MODEL = os.environ.get("TOPIC_MODEL", "google/gemini-3.1-flash-lite-preview")
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

LABEL_SCHEMA = {
    "name": "topic_label",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "A single-word topic label."},
            "description": {"type": "string", "description": "One sentence explaining the common theme."},
        },
        "required": ["label", "description"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@dataclass
class Post:
    post_id: str
    title: str
    content: str
    author_name: str
    condition: str
    run: str
    scale: str
    created_at: str
    minutes_elapsed: float
    embedding: np.ndarray
    cluster_id: int = -1
    topic_label: str = ""


def load_posts(model_key: str, scale: str) -> list[Post]:
    """Load posts from NPZ file for a given model and scale."""
    prefix = MODELS[model_key]["prefix"]
    npz_name = f"embeddings_{prefix}{scale}.npz"
    npz_path = EMB_DIR / npz_name
    if not npz_path.exists():
        raise FileNotFoundError(f"Missing: {npz_path}")

    data = np.load(npz_path, allow_pickle=True)
    embeddings = data["embeddings"]
    n = int(data["n_texts"])

    posts = [
        Post(
            post_id=str(data["post_id"][i]), title=str(data["title"][i]),
            content=str(data["content"][i]), author_name=str(data["author_name"][i]),
            condition=str(data["condition"][i]), run=str(data["run"][i]),
            scale=scale, created_at=str(data["created_at"][i]),
            minutes_elapsed=0.0, embedding=embeddings[i],
        )
        for i in range(n)
    ]

    # Compute minutes_elapsed per condition
    by_cond: dict[str, list[Post]] = {}
    for p in posts:
        by_cond.setdefault(p.condition, []).append(p)
    for cond_posts in by_cond.values():
        ts = [datetime.fromisoformat(p.created_at.replace("Z", "+00:00")) for p in cond_posts]
        t0 = min(ts)
        for p, t in zip(cond_posts, ts):
            p.minutes_elapsed = (t - t0).total_seconds() / 60.0

    return posts


# ---------------------------------------------------------------------------
# LLM calls
# ---------------------------------------------------------------------------
def llm_call(prompt: str, *, schema: dict, tag: str = "") -> dict | None:
    if not OPENROUTER_KEY or requests is None:
        return None
    try:
        resp = requests.post(
            CHAT_ENDPOINT,
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={
                "model": CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0, "max_tokens": 512,
                "response_format": {"type": "json_schema", "json_schema": schema},
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"].get("content", "")
        return json.loads(content) if content.strip() else None
    except Exception as e:
        print(f"  LLM call failed [{tag}]: {e}")
        return None


# ---------------------------------------------------------------------------
# Step 1: Cluster GPT reference
# ---------------------------------------------------------------------------
def cluster_gpt_reference(posts: list[Post], k: int = K) -> tuple[dict, dict[int, dict]]:
    """KMeans on GPT embeddings → cluster_info + labels."""
    embs = np.array([p.embedding for p in posts])
    pca = PCA(n_components=min(PCA_DIMS, len(posts) - 1, embs.shape[1]), random_state=42)
    X = normalize(pca.fit_transform(embs), norm="l2")

    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    sil = float(silhouette_score(X, km.labels_, metric="cosine"))
    for p, label in zip(posts, km.labels_):
        p.cluster_id = int(label)

    sizes = [int((km.labels_ == ci).sum()) for ci in range(k)]
    print(f"  k={k}, silhouette={sil:.3f}, sizes={sizes}")

    cluster_info = {
        "k": k, "silhouette": sil, "cluster_sizes": sizes,
        "centroids": km.cluster_centers_, "X_norm": X, "pca_model": pca,
    }
    return cluster_info, _label_clusters(posts, cluster_info)


def _label_clusters(posts: list[Post], info: dict) -> dict[int, dict]:
    """LLM-label clusters, with cache."""
    cache_path = OUT_DIR / "label_cache_gpt_k6.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    labels: dict[int, dict] = {}

    for ci in range(info["k"]):
        key = f"cluster_{ci}"
        if key in cache:
            labels[ci] = cache[key]
            continue

        # 5 posts closest to centroid
        cluster_idx = [i for i, p in enumerate(posts) if p.cluster_id == ci]
        if not cluster_idx:
            labels[ci] = {"label": f"Topic {ci}", "description": "Empty"}
            continue
        centroid = info["centroids"][ci]
        dists = 1 - info["X_norm"][cluster_idx] @ (centroid / (np.linalg.norm(centroid) + 1e-10))
        top5 = [cluster_idx[i] for i in np.argsort(dists)[:5]]

        used_labels = [labels[cj]["label"] for cj in range(ci) if cj in labels]
        avoid = ""
        if used_labels:
            avoid = f"\n\nDo NOT reuse these labels: {', '.join(used_labels)}. Pick a DIFFERENT word.\n"

        prompt = (
            "You are classifying posts from a multi-agent social network experiment.\n\n"
            "Below are 5 representative posts from one cluster. Identify the core theme "
            "and assign a single-word topic label.\n\n"
            "The label should be: (1) one word, (2) suitable for an academic paper, "
            "(3) clear to a broad research audience."
            + avoid + "\n"
            + "\n\n".join(f"Post {j+1}: {posts[i].title}\n{posts[i].content[:400]}" for j, i in enumerate(top5))
        )
        result = llm_call(prompt, schema=LABEL_SCHEMA, tag=key)
        labels[ci] = result or {"label": f"Topic {ci}", "description": "LLM failed"}
        cache[key] = labels[ci]
        time_mod.sleep(0.5)

    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False))

    # Title-case
    LABEL_OVERRIDES = {"reliability": "Safety", "Reliability": "Safety"}
    for ci in labels:
        raw = labels[ci]["label"]
        labels[ci]["label"] = LABEL_OVERRIDES.get(raw, raw).title()

    return labels


# ---------------------------------------------------------------------------
# Step 2: Classify non-GPT posts into reference topics
# ---------------------------------------------------------------------------
def classify_into_reference(posts: list[Post], ref_labels: dict[int, dict],
                            cache_path: Path, batch_size: int = 10) -> None:
    """Assign each post to one of the k reference topics via LLM classification."""
    k = len(ref_labels)
    topic_menu = "\n".join(f"  {ci}: {ref_labels[ci]['label']} — {ref_labels[ci]['description']}"
                           for ci in range(k))

    cache: dict[str, int] = {}
    if cache_path.exists():
        cache = json.loads(cache_path.read_text())

    uncached = [(i, p) for i, p in enumerate(posts) if p.post_id not in cache]
    print(f"  {len(posts) - len(uncached)} cached, {len(uncached)} to classify")

    batch_schema = {
        "name": "batch_classify",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": f"Topic index (0-{k-1}) for each post in order.",
                },
            },
            "required": ["assignments"],
            "additionalProperties": False,
        },
    }

    for batch_start in range(0, len(uncached), batch_size):
        batch = uncached[batch_start:batch_start + batch_size]
        post_texts = "\n\n".join(
            f"[Post {j}] {p.title}\n{p.content[:300]}"
            for j, (_, p) in enumerate(batch)
        )
        prompt = (
            f"Classify each post below into exactly one of these {k} topics:\n{topic_menu}\n\n"
            f"{post_texts}\n\n"
            f"Respond with a JSON array of topic indices. "
            f"Example for 3 posts: {{\"assignments\": [2, 0, 5]}}"
        )

        result = llm_call(prompt, schema=batch_schema, tag=f"batch_{batch_start}")
        if result and "assignments" in result and len(result["assignments"]) == len(batch):
            for (idx, p), topic_id in zip(batch, result["assignments"]):
                cache[p.post_id] = max(0, min(k - 1, topic_id))
        else:
            for idx, p in batch:
                cache[p.post_id] = 0

        done = min(batch_start + batch_size, len(uncached))
        if done % 50 == 0 or done == len(uncached):
            print(f"    classified {done}/{len(uncached)}")
        time_mod.sleep(0.3)

    cache_path.write_text(json.dumps(cache, indent=2))

    for p in posts:
        p.cluster_id = cache.get(p.post_id, 0)


# ---------------------------------------------------------------------------
# Step 3: Compute MDS + save plot data
# ---------------------------------------------------------------------------
def compute_and_save(model_key: str, scale: str, posts: list[Post],
                     labels: dict[int, dict]) -> None:
    """PCA → MDS → save NPZ + JSON for later plotting."""
    k = len(labels)
    tag = f"{model_key}_{scale}" if model_key != "gpt" else f"gpt_{scale}"

    # PCA + normalize for MDS
    embs = np.array([p.embedding for p in posts])
    pca = PCA(n_components=min(PCA_DIMS, len(posts) - 1, embs.shape[1]), random_state=42)
    X = normalize(pca.fit_transform(embs), norm="l2")

    # MDS
    print(f"  MDS for {tag} ({len(posts)} posts)...")
    X_centered = X - X.mean(axis=0)
    dist_matrix = cosine_distances(X_centered)
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=42,
              n_init=4, max_iter=300, normalized_stress="auto")
    coords = mds.fit_transform(dist_matrix)

    # Save NPZ
    np.savez_compressed(
        OUT_DIR / f"plot_data_{tag}.npz",
        conditions=np.array([p.condition for p in posts], dtype=object),
        cluster_ids=np.array([p.cluster_id for p in posts]),
        minutes=np.array([p.minutes_elapsed for p in posts]),
        mds_coords=coords,
        k=np.array(k),
    )

    # Save JSON metadata
    meta = {"labels": {str(ci): v for ci, v in labels.items()}}
    (OUT_DIR / f"plot_data_{tag}.json").write_text(json.dumps(meta, indent=2, default=str))

    print(f"  Saved plot_data_{tag}.npz + .json")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-llm", action="store_true", help="Use cached labels only")
    parser.add_argument("--models", default="gpt,gemini,glm,kimi",
                        help="Comma-separated model keys to process")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    model_keys = args.models.split(",")

    # ── Step 1: GPT reference clustering ──
    # Use the largest available GPT scale for reference clustering
    ref_scale = "n10"  # all models have n10, use it for reference
    print(f"\n{'='*60}")
    print(f"Step 1: GPT reference clustering (k={K}, scale={ref_scale})")
    print(f"{'='*60}")

    ref_posts = load_posts("gpt", ref_scale)
    print(f"  Loaded {len(ref_posts)} GPT posts")

    # Check for existing label cache first
    label_cache = OUT_DIR / "label_cache_gpt_k6.json"
    old_cache = Path("findings/entropy-collapse-scaling/topic_convergence/label_cache_reference.json")

    if not label_cache.exists() and old_cache.exists():
        # Reuse existing labels from previous analysis
        import shutil
        shutil.copy(old_cache, label_cache)
        print(f"  Copied existing labels from {old_cache}")

    ref_cluster, ref_labels = cluster_gpt_reference(ref_posts, k=K)

    print("  Reference topics:")
    for ci, lbl in sorted(ref_labels.items()):
        print(f"    {ci}: {lbl['label']} — {lbl['description']}")

    # ── Step 2+3: Process each model × scale ──
    for model_key in model_keys:
        if model_key not in MODELS:
            print(f"  Unknown model: {model_key}, skipping")
            continue
        model_cfg = MODELS[model_key]

        for scale in model_cfg["scales"]:
            print(f"\n{'='*60}")
            print(f"{model_cfg['label']} / {scale}")
            print(f"{'='*60}")

            try:
                posts = load_posts(model_key, scale)
            except FileNotFoundError as e:
                print(f"  SKIP: {e}")
                continue

            print(f"  Loaded {len(posts)} posts")

            if model_key == "gpt" and scale == ref_scale:
                # Already clustered
                for p in posts:
                    for rp in ref_posts:
                        if p.post_id == rp.post_id:
                            p.cluster_id = rp.cluster_id
                            break
            elif model_key == "gpt":
                # Other GPT scales: classify into reference topics
                cache_path = OUT_DIR / f"classify_cache_gpt_{scale}.json"
                print("  Classifying into reference topics...")
                classify_into_reference(posts, ref_labels, cache_path)
            else:
                # Non-GPT models: classify into reference topics
                cache_path = OUT_DIR / f"classify_cache_{model_key}_{scale}.json"
                print("  Classifying into reference topics...")
                if args.skip_llm and not cache_path.exists():
                    print("  SKIP: --skip-llm and no cache exists")
                    continue
                classify_into_reference(posts, ref_labels, cache_path)

            # Apply topic labels
            for p in posts:
                p.topic_label = ref_labels.get(p.cluster_id, {}).get("label", "")

            # Compute MDS + save
            compute_and_save(model_key, scale, posts, ref_labels)

    print(f"\nAll done. Plot data saved to {OUT_DIR}/")
    for p in sorted(OUT_DIR.iterdir()):
        print(f"  {p.name}")


if __name__ == "__main__":
    main()
