#!/usr/bin/env python3
"""Topic convergence analysis for entropy-collapse experiments.

Layer 1 — Geometric convergence (no labels, no clustering):
  - Vendi Score (vendi-score v0.0.3, Friedman & Dieng, TMLR 2023)
  - TwoNN intrinsic dimensionality (scikit-dimension v0.3.4, Facco et al., 2017)
  - JSD between consecutive time bins (scipy)

Layer 2 — Data-driven topic tracking:
  - PCA + KMeans (silhouette-selected K, global per-scale)
  - LLM-labeled clusters via OpenRouter

Layer 3 — Effect sizes: Cliff's delta vs control (mag0)

Embeddings: Pre-computed Qwen3-Embedding-8B (4096-dim) via OpenRouter.

Outputs → findings/entropy-collapse-scaling/topic_convergence/
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import time as time_mod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/moltbook-cache")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial.distance import jensenshannon
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize
from skdim.id import TwoNN
from vendi_score import vendi

from load_entropy_data import CONDITION_LABELS, CONDITION_ORDER

try:
    import requests
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)
except ImportError:
    requests = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
SCALES = ["n20", "n30"]
BIN_EDGES = [0.0, 15.0, 30.0, 45.0, 60.0]
PCA_DIMS = 50
K_RANGE = range(3, 11)
OUT_DIR = Path("findings/entropy-collapse-scaling/topic_convergence")
EMB_DIR = Path("experiments/entropy-collapse/data/embeddings")

COND_COLORS = {
    "mag0": "#4B5563", "mag1": "#E11D48", "mag5": "#F97316",
    "mag25": "#7C3AED", "dom-agi": "#2563EB", "dom-tech": "#10B981",
}

# Slide-friendly condition labels (override CONDITION_LABELS for plots)
SLIDE_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy",
    "mag5": "5 conspiracies",
    "mag25": "25 conspiracies",
    "dom-agi": "25 AGI hype",
    "dom-tech": "25 tech humor",
}

# Default: show only these 4 conditions in plots
DEFAULT_PLOT_CONDITIONS = ["mag0", "mag5", "mag25", "dom-agi"]

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CHAT_MODEL = os.environ.get("TOPIC_MODEL", "google/gemini-3.1-flash-lite-preview")
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

LABEL_SCHEMA = {
    "name": "topic_label",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "label": {"type": "string", "description": "A single-word topic label like a research paper keyword."},
            "description": {"type": "string", "description": "One sentence explaining the common theme."},
        },
        "required": ["label", "description"],
        "additionalProperties": False,
    },
}


# ---------------------------------------------------------------------------
# Data
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


def load_posts(scale: str, emb_dir: Path = EMB_DIR) -> list[Post]:
    """Load posts with pre-computed Qwen3-8B embeddings from NPZ."""
    data = np.load(emb_dir / f"embeddings_{scale}.npz", allow_pickle=True)
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


def bin_posts(posts: list[Post], edges: list[float] = BIN_EDGES) -> dict[tuple[str, int], list[Post]]:
    """Bin posts into (condition, bin_index) groups within [0, max_t]."""
    bins: dict[tuple[str, int], list[Post]] = {}
    max_t = edges[-1]
    for p in posts:
        if p.minutes_elapsed > max_t:
            continue
        for bi in range(len(edges) - 1):
            lo, hi = edges[bi], edges[bi + 1]
            in_bin = (lo <= p.minutes_elapsed < hi) if bi < len(edges) - 2 else (lo <= p.minutes_elapsed <= hi)
            if in_bin:
                bins.setdefault((p.condition, bi), []).append(p)
                break
    return bins


# ---------------------------------------------------------------------------
# Layer 1: Geometric metrics
# ---------------------------------------------------------------------------
def compute_vendi(embs: np.ndarray) -> float:
    """Vendi Score via cosine similarity kernel (vendi-score package)."""
    if len(embs) < 2:
        return float(len(embs))
    X = normalize(embs, norm="l2")
    K = X @ X.T
    return float(vendi.score_K(K))


def compute_twonn(embs: np.ndarray) -> float:
    """TwoNN intrinsic dimensionality (scikit-dimension package)."""
    if len(embs) < 15:
        return float("nan")
    try:
        return float(TwoNN().fit_transform(embs))
    except Exception:
        return float("nan")


def compute_jsd(emb_a: np.ndarray, emb_b: np.ndarray, n_bins: int = 50) -> float:
    """JSD between two embedding sets via PCA(1) histogram."""
    if len(emb_a) < 2 or len(emb_b) < 2:
        return float("nan")
    combined = np.vstack([emb_a, emb_b])
    proj = PCA(n_components=1, random_state=42).fit_transform(combined).ravel()

    edges = np.linspace(proj.min(), proj.max(), n_bins + 1)
    ha, _ = np.histogram(proj[: len(emb_a)], bins=edges)
    hb, _ = np.histogram(proj[len(emb_a) :], bins=edges)

    # Normalize to probability distributions with smoothing
    ha = (ha + 1e-10) / (ha + 1e-10).sum()
    hb = (hb + 1e-10) / (hb + 1e-10).sum()
    return float(jensenshannon(ha, hb, base=2))


def compute_geometric_metrics(posts: list[Post], edges: list[float] = BIN_EDGES) -> list[dict]:
    """Layer 1 metrics per (condition, bin)."""
    binned = bin_posts(posts, edges)

    # Global PCA for TwoNN (avoids curse of dimensionality on raw 4096-dim)
    all_embs = np.array([p.embedding for p in posts])
    pca_global = PCA(n_components=min(PCA_DIMS, len(posts) - 1), random_state=42).fit(all_embs)
    all_pca = pca_global.transform(all_embs)
    idx_map = {p.post_id: i for i, p in enumerate(posts)}

    results = []
    for cond in CONDITION_ORDER:
        for bi in range(len(edges) - 1):
            bp = binned.get((cond, bi), [])
            embs = np.array([p.embedding for p in bp]) if bp else np.empty((0, 1))
            embs_pca = np.array([all_pca[idx_map[p.post_id]] for p in bp]) if bp else np.empty((0, 1))

            # JSD to next bin
            next_bp = binned.get((cond, bi + 1), [])
            next_embs = np.array([p.embedding for p in next_bp]) if next_bp else np.empty((0, 1))

            results.append({
                "condition": cond,
                "condition_label": CONDITION_LABELS.get(cond, cond),
                "bin_idx": bi,
                "bin_start": edges[bi], "bin_end": edges[bi + 1],
                "bin_center": (edges[bi] + edges[bi + 1]) / 2,
                "n_posts": len(bp),
                "vendi_score": compute_vendi(embs),
                "intrinsic_dim": compute_twonn(embs_pca),
                "jsd_to_next": compute_jsd(embs, next_embs),
            })
    return results


# ---------------------------------------------------------------------------
# Layer 2: Topic clustering + LLM labeling
# ---------------------------------------------------------------------------
def cluster_posts(posts: list[Post], k: int | None = None, pca_dims: int = PCA_DIMS) -> dict:
    """PCA → L2-norm → KMeans. Sets cluster_id on each post.

    Returns cluster_info including the fitted PCA model for reuse on other datasets.
    """
    embs = np.array([p.embedding for p in posts])
    pca = PCA(n_components=min(pca_dims, len(posts) - 1, embs.shape[1]), random_state=42)
    X = normalize(pca.fit_transform(embs), norm="l2")

    # Auto-select k via silhouette
    sil_scan = {}
    if k is None:
        for ki in K_RANGE:
            if ki >= len(X):
                continue
            labels = KMeans(n_clusters=ki, n_init=10, random_state=42).fit_predict(X)
            sil_scan[ki] = float(silhouette_score(X, labels, metric="cosine"))
        k = max(sil_scan, key=sil_scan.get)  # type: ignore
        print(f"  Auto k={k} (silhouette={sil_scan[k]:.3f})")

    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    for p, label in zip(posts, km.labels_):
        p.cluster_id = int(label)

    sizes = [0] * k
    for l in km.labels_:
        sizes[l] += 1

    # Compute raw-space centroids (mean of raw embeddings per cluster) for cross-model assignment
    raw_centroids = np.zeros((k, embs.shape[1]))
    for ci in range(k):
        mask = km.labels_ == ci
        if mask.sum() > 0:
            raw_centroids[ci] = embs[mask].mean(axis=0)

    return {
        "k": k, "silhouette": float(silhouette_score(X, km.labels_, metric="cosine")),
        "silhouette_scan": sil_scan, "cluster_sizes": sizes,
        "pca_explained_variance": float(np.sum(pca.explained_variance_ratio_)),
        "centroids": km.cluster_centers_, "X_norm": X,
        "pca_model": pca,
        "raw_centroids": raw_centroids,
    }


CLASSIFY_SCHEMA = {
    "name": "topic_classify",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "topic": {"type": "integer", "description": "The topic index (0-based) that best matches this post."},
        },
        "required": ["topic"],
        "additionalProperties": False,
    },
}


def assign_to_reference(posts: list[Post], ref_info: dict, ref_labels: dict[int, dict],
                        cache_path: Path | None = None, batch_size: int = 10) -> dict:
    """Assign posts to reference topics via LLM classification.

    Centroid-based assignment fails across models (different content distributions).
    Instead, we ask the LLM to classify each post into the fixed topic set.
    Posts are batched to reduce API calls.
    """
    k = ref_info["k"]

    # Build topic menu for the prompt
    topic_menu = "\n".join(f"  {ci}: {ref_labels[ci]['label']} — {ref_labels[ci]['description']}" for ci in range(k))

    # Load cache
    cache: dict[str, int] = {}
    if cache_path and cache_path.exists():
        cache = json.loads(cache_path.read_text())

    # Classify posts in batches
    assignments = []
    uncached = [(i, p) for i, p in enumerate(posts) if p.post_id not in cache]
    print(f"  {len(posts) - len(uncached)} cached, {len(uncached)} to classify")

    for batch_start in range(0, len(uncached), batch_size):
        batch = uncached[batch_start:batch_start + batch_size]
        # Build batch prompt
        post_texts = "\n\n".join(
            f"[Post {j}] {p.title}\n{p.content[:300]}"
            for j, (_, p) in enumerate(batch)
        )
        prompt = (
            f"Classify each post below into exactly one of these {k} topics:\n{topic_menu}\n\n"
            f"{post_texts}\n\n"
            f"For each post, respond with a JSON array of topic indices. "
            f"Example for 3 posts: {{\"assignments\": [2, 0, 5]}}"
        )

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

        result = llm_call(prompt, schema=batch_schema, tag=f"classify_batch_{batch_start}")
        if result and "assignments" in result and len(result["assignments"]) == len(batch):
            for (idx, p), topic_id in zip(batch, result["assignments"]):
                clamped = max(0, min(k - 1, topic_id))
                cache[p.post_id] = clamped
        else:
            # Fallback: assign to most common topic (0)
            for idx, p in batch:
                cache[p.post_id] = 0

        if (batch_start // batch_size + 1) % 10 == 0:
            print(f"    classified {min(batch_start + batch_size, len(uncached))}/{len(uncached)}")
        time_mod.sleep(0.3)

    # Save cache
    if cache_path:
        cache_path.write_text(json.dumps(cache, indent=2))

    # Apply assignments
    for p in posts:
        p.cluster_id = cache.get(p.post_id, 0)

    sizes = [0] * k
    for p in posts:
        sizes[p.cluster_id] += 1

    # PCA + X_norm for MDS visualization
    embs = np.array([p.embedding for p in posts])
    pca_local = PCA(n_components=min(PCA_DIMS, len(posts) - 1, embs.shape[1]), random_state=42)
    X_norm = normalize(pca_local.fit_transform(embs), norm="l2")
    cluster_ids = np.array([p.cluster_id for p in posts])

    sil = float(silhouette_score(X_norm, cluster_ids, metric="cosine")) if len(set(cluster_ids)) > 1 else 0.0

    # Dummy centroids in PCA space for compatibility
    centroids = np.zeros((k, X_norm.shape[1]))
    for ci in range(k):
        mask = cluster_ids == ci
        if mask.sum() > 0:
            centroids[ci] = X_norm[mask].mean(axis=0)

    return {
        "k": k, "silhouette": sil,
        "silhouette_scan": {}, "cluster_sizes": sizes,
        "pca_explained_variance": float(np.sum(pca_local.explained_variance_ratio_)),
        "centroids": centroids, "X_norm": X_norm,
        "pca_model": pca_local, "is_reference": False,
    }


def llm_call(prompt: str, *, schema: dict, tag: str = "") -> dict | None:
    """OpenRouter chat API with structured JSON output."""
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


def label_clusters(posts: list[Post], info: dict, cache_path: Path, skip_llm: bool = False) -> dict[int, dict]:
    """LLM-label each cluster using centroid-nearest posts."""
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    labels: dict[int, dict] = {}

    for ci in range(info["k"]):
        key = f"cluster_{ci}"
        if key in cache:
            labels[ci] = cache[key]
            continue
        if skip_llm:
            labels[ci] = {"label": f"Topic {ci}", "description": f"Cluster {ci}"}
            continue

        # 5 posts closest to centroid
        cluster_idx = [i for i, p in enumerate(posts) if p.cluster_id == ci]
        if not cluster_idx:
            labels[ci] = {"label": f"Topic {ci}", "description": "Empty"}
            continue
        centroid = info["centroids"][ci]
        dists = 1 - info["X_norm"][cluster_idx] @ (centroid / (np.linalg.norm(centroid) + 1e-10))
        top5 = [cluster_idx[i] for i in np.argsort(dists)[:5]]

        # Build list of already-used labels to avoid duplicates
        used_labels = [labels[cj]["label"] for cj in range(ci) if cj in labels]
        avoid_clause = ""
        if used_labels:
            avoid_clause = f"\n\nDo NOT reuse these labels already assigned to other clusters: {', '.join(used_labels)}. Pick a DIFFERENT word.\n"

        prompt = (
            "You are classifying posts from a multi-agent social network experiment.\n\n"
            "Below are 5 representative posts from one cluster. Read them carefully, "
            "identify the core theme, then assign a single-word topic label.\n\n"
            "The label should be: (1) one word, (2) suitable for an academic paper or conference slide, "
            "(3) clear to a broad research audience — e.g. 'identity', 'verification', 'resilience', "
            "'norms', 'introspection', 'coordination', 'risk', 'habits'."
            + avoid_clause + "\n"
            + "\n\n".join(f"Post {j+1}: {posts[i].title}\n{posts[i].content[:400]}" for j, i in enumerate(top5))
        )
        result = llm_call(prompt, schema=LABEL_SCHEMA, tag=key)
        labels[ci] = result or {"label": f"Topic {ci}", "description": "LLM failed"}
        cache[key] = labels[ci]
        time_mod.sleep(0.5)

    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False))

    # Post-process: apply label overrides and title-case
    LABEL_OVERRIDES = {"reliability": "Safety", "Reliability": "Safety"}
    for ci in labels:
        raw = labels[ci]["label"]
        labels[ci]["label"] = LABEL_OVERRIDES.get(raw, raw).title()

    for p in posts:
        p.topic_label = labels.get(p.cluster_id, {}).get("label", "")
    return labels


def compute_topic_proportions(posts: list[Post], labels: dict[int, dict], edges: list[float] = BIN_EDGES) -> list[dict]:
    """Topic proportions + entropy per (condition, bin)."""
    binned = bin_posts(posts, edges)
    k = len(labels)
    results = []
    for cond in CONDITION_ORDER:
        for bi in range(len(edges) - 1):
            bp = binned.get((cond, bi), [])
            n = len(bp)
            counts = [sum(1 for p in bp if p.cluster_id == ci) for ci in range(k)]
            props = [c / n if n > 0 else 1.0 / k for c in counts]
            H = -sum(p * math.log2(p) for p in props if p > 0)

            row = {
                "condition": cond, "condition_label": CONDITION_LABELS.get(cond, cond),
                "bin_idx": bi, "bin_center": (edges[bi] + edges[bi + 1]) / 2, "n_posts": n,
                "topic_entropy": H, "topic_entropy_norm": H / math.log2(k) if k > 1 else 0.0,
            }
            for ci in range(k):
                row[f"t{ci}_{labels[ci]['label']}"] = props[ci]
            results.append(row)
    return results


# ---------------------------------------------------------------------------
# Layer 3: Effect sizes
# ---------------------------------------------------------------------------
def cliffs_delta(x: np.ndarray, y: np.ndarray) -> tuple[float, str]:
    """Cliff's delta + effect size label (Romano et al. 2006)."""
    if len(x) == 0 or len(y) == 0:
        return 0.0, "negligible"
    more = sum(np.sum(xi > y) for xi in x)
    less = sum(np.sum(xi < y) for xi in x)
    d = float((more - less) / (len(x) * len(y)))
    ad = abs(d)
    return d, "large" if ad >= 0.43 else "medium" if ad >= 0.28 else "small" if ad >= 0.11 else "negligible"


def compute_effect_sizes(geo: list[dict], control: str = "mag0") -> list[dict]:
    by_cond: dict[str, list[dict]] = {}
    for r in geo:
        by_cond.setdefault(r["condition"], []).append(r)
    ctrl = by_cond.get(control, [])
    if not ctrl:
        return []

    results = []
    for metric in ["vendi_score", "intrinsic_dim"]:
        ctrl_vals = np.array([r[metric] for r in ctrl if not math.isnan(r[metric])])
        if len(ctrl_vals) == 0:
            continue
        for cond in CONDITION_ORDER:
            if cond == control:
                continue
            vals = np.array([r[metric] for r in by_cond.get(cond, []) if not math.isnan(r[metric])])
            if len(vals) == 0:
                continue
            d, label = cliffs_delta(vals, ctrl_vals)
            results.append({
                "metric": metric, "condition": cond,
                "condition_label": CONDITION_LABELS.get(cond, cond),
                "cliffs_delta": d, "effect_size": label,
            })
    return results


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------
def plot_geometric(metrics: list[dict], scale: str, out: Path,
                   conditions: list[str] | None = None) -> None:
    conditions = conditions or DEFAULT_PLOT_CONDITIONS
    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)
    for cond in conditions:
        rows = sorted([r for r in metrics if r["condition"] == cond], key=lambda r: r["bin_idx"])
        if not rows:
            continue
        c, color, lbl = [r["bin_center"] for r in rows], COND_COLORS.get(cond, "#6B7280"), SLIDE_LABELS.get(cond, cond)

        axes[0].plot(c, [r["vendi_score"] for r in rows], "o-", color=color, label=lbl, ms=5)

        id_vals = [(x, r["intrinsic_dim"]) for x, r in zip(c, rows) if not math.isnan(r["intrinsic_dim"])]
        if id_vals:
            axes[1].plot(*zip(*id_vals), "o-", color=color, label=lbl, ms=5)

        jsd_vals = [(x, r["jsd_to_next"]) for x, r in zip(c, rows) if not math.isnan(r["jsd_to_next"])]
        if jsd_vals:
            axes[2].plot(*zip(*jsd_vals), "o-", color=color, label=lbl, ms=5)

    axes[0].set_ylabel("Vendi Score\n(effective diversity)")
    axes[0].set_title(f"Geometric convergence ({scale})", fontsize=17, fontweight="bold")
    axes[0].legend(fontsize=17, ncol=3, loc="upper right")
    axes[1].set_ylabel("Intrinsic dim.\n(TwoNN)")
    axes[2].set_ylabel("JSD to next bin")
    axes[2].set_xlabel("Minutes")
    for ax in axes:
        ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


# 6 maximally distinct topic colors (projector/slide safe)
TOPIC_COLORS = ["#2563EB", "#DC2626", "#16A34A", "#9333EA", "#EA580C", "#0891B2"]


def plot_stacked(props: list[dict], labels: dict[int, dict], scale: str, out: Path,
                 conditions: list[str] | None = None) -> None:
    conditions = conditions or DEFAULT_PLOT_CONDITIONS
    k = len(labels)
    fig, axes = plt.subplots(2, 2, figsize=(12, 10), sharey=True)

    colors = TOPIC_COLORS[:k] if k <= len(TOPIC_COLORS) else [matplotlib.colormaps.get_cmap("tab10")(i) for i in range(k)]

    for idx, cond in enumerate(conditions):
        ax = axes.flat[idx]
        cond_rows = sorted([r for r in props if r["condition"] == cond], key=lambda r: r["bin_idx"])
        if not cond_rows:
            continue
        centers = [r["bin_center"] for r in cond_rows]
        stacks = [[r.get(f"t{ci}_{labels[ci]['label']}", 0) for r in cond_rows] for ci in range(k)]
        ax.stackplot(centers, *stacks, labels=[labels[ci]["label"] for ci in range(k)], colors=colors, alpha=0.85)
        n_total = sum(r["n_posts"] for r in cond_rows)
        ax.set_title(f"{SLIDE_LABELS.get(cond, cond)} (n={n_total})", fontsize=18, fontweight="bold")
        ax.set_ylim(0, 1)
        if idx >= 2: ax.set_xlabel("Minutes")
        if idx % 2 == 0: ax.set_ylabel("Topic proportion")

    handles, leg = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, leg, loc="lower center", ncol=min(k, 6), fontsize=14, frameon=True, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Topic Proportions Over Time ({scale})", fontsize=18, fontweight="bold")
    plt.subplots_adjust(hspace=0.2, wspace=0.1, top=0.93, bottom=0.07)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_entropy(props: list[dict], scale: str, out: Path,
                 conditions: list[str] | None = None) -> None:
    conditions = conditions or DEFAULT_PLOT_CONDITIONS
    fig, ax = plt.subplots(figsize=(10, 6))
    for cond in conditions:
        rows = sorted([r for r in props if r["condition"] == cond], key=lambda r: r["bin_idx"])
        if not rows:
            continue
        ax.plot([r["bin_center"] for r in rows], [r["topic_entropy_norm"] for r in rows],
                "o-", color=COND_COLORS.get(cond, "#6B7280"), label=SLIDE_LABELS.get(cond, cond), ms=6, lw=2)
    ax.set_xlabel("Minutes"); ax.set_ylabel("Normalized topic entropy")
    ax.set_title(f"Topic entropy over time ({scale})", fontsize=17, fontweight="bold")
    ax.set_ylim(0, 1.05); ax.legend(); ax.grid(True, alpha=0.3)
    fig.tight_layout(); fig.savefig(out, dpi=180, bbox_inches="tight"); plt.close(fig)


def plot_mds_topics(posts: list[Post], info: dict, labels: dict[int, dict], scale: str, out: Path,
                    conditions: list[str] | None = None, model_label: str = "GPT-5") -> None:
    """MDS 2D topic map: PCA → mean-center → cosine distance → MDS.

    Grid (one per condition) showing post positions colored by topic cluster.
    """
    from sklearn.manifold import MDS
    from sklearn.metrics.pairwise import cosine_distances

    conditions = conditions or DEFAULT_PLOT_CONDITIONS
    k = len(labels)
    topic_colors = {ci: TOPIC_COLORS[ci] if ci < len(TOPIC_COLORS) else f"C{ci}" for ci in range(k)}

    # Global MDS projection (all posts together for consistent coordinates)
    X = info["X_norm"]  # PCA-reduced, L2-normed
    X_centered = X - X.mean(axis=0)
    dist_matrix = cosine_distances(X_centered)
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=42, n_init=4, max_iter=300, normalized_stress="auto")
    coords = mds.fit_transform(dist_matrix)

    # 2x2 grid, tight layout for slides
    fig, axes = plt.subplots(2, 2, figsize=(12, 11))

    for idx, cond in enumerate(conditions[:4]):
        ax = axes.flat[idx]
        cond_mask = np.array([p.condition == cond for p in posts])
        cond_clusters = np.array([p.cluster_id for p in posts])

        # Background: all other conditions in light grey
        other = ~cond_mask
        ax.scatter(coords[other, 0], coords[other, 1], c="#E5E7EB", s=4, alpha=0.25, rasterized=True)

        # Foreground: this condition colored by topic
        for ci in range(k):
            mask = cond_mask & (cond_clusters == ci)
            if mask.sum() == 0:
                continue
            ax.scatter(coords[mask, 0], coords[mask, 1], c=[topic_colors[ci]], s=28, alpha=0.8,
                       label=labels[ci]["label"].title(), edgecolors="white", linewidths=0.3, rasterized=True)

        ax.set_title(f"{SLIDE_LABELS.get(cond, cond)} (n={cond_mask.sum()})", fontsize=16, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_aspect("equal")
        ax.spines[:].set_visible(False)

    # Shared legend
    handles, leg = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, leg, loc="lower center", ncol=min(k, 6), fontsize=17,
               frameon=True, fancybox=True, shadow=False, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Topic Map — MDS Projection ({model_label}, {scale})", fontsize=18, fontweight="bold")
    plt.subplots_adjust(hspace=0.15, wspace=0.08, top=0.93, bottom=0.07)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_mds_temporal(posts: list[Post], info: dict, scale: str, out: Path,
                     conditions: list[str] | None = None, model_label: str = "GPT-5") -> None:
    """MDS 2D map colored by time (early=blue → late=red) per condition."""
    from sklearn.manifold import MDS
    from sklearn.metrics.pairwise import cosine_distances

    conditions = conditions or DEFAULT_PLOT_CONDITIONS

    X = info["X_norm"]
    X_centered = X - X.mean(axis=0)
    dist_matrix = cosine_distances(X_centered)
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=42, n_init=4, max_iter=300, normalized_stress="auto")
    coords = mds.fit_transform(dist_matrix)

    max_t = BIN_EDGES[-1]
    fig, axes = plt.subplots(2, 2, figsize=(12, 11))

    sc = None
    for idx, cond in enumerate(conditions[:4]):
        ax = axes.flat[idx]
        cond_mask = np.array([p.condition == cond for p in posts])
        cond_times = np.array([min(p.minutes_elapsed, max_t) for p in posts])

        other = ~cond_mask
        ax.scatter(coords[other, 0], coords[other, 1], c="#E5E7EB", s=4, alpha=0.25, rasterized=True)

        cm = cond_mask & (cond_times <= max_t)
        if cm.sum() > 0:
            sc = ax.scatter(coords[cm, 0], coords[cm, 1], c=cond_times[cm], cmap="coolwarm",
                           s=28, alpha=0.8, vmin=0, vmax=max_t, edgecolors="white", linewidths=0.3, rasterized=True)

        ax.set_title(f"{SLIDE_LABELS.get(cond, cond)}", fontsize=16, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([])
        ax.set_aspect("equal")
        ax.spines[:].set_visible(False)

    if sc is not None:
        fig.colorbar(sc, ax=axes.ravel().tolist(), shrink=0.5, label="Minutes elapsed", pad=0.02)
    fig.suptitle(f"Temporal Drift — MDS Projection ({model_label}, {scale})", fontsize=18, fontweight="bold")
    plt.subplots_adjust(hspace=0.12, wspace=0.08, top=0.93, bottom=0.03)
    fig.savefig(out, dpi=180, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------
def write_outputs(all_results: dict[str, dict], out_dir: Path) -> None:
    # JSON
    clean = {}
    for scale, d in all_results.items():
        clean[scale] = {
            "geometric": d["geo"], "cluster_info": {k: v for k, v in d["cluster"].items() if k not in ("centroids", "X_norm", "pca_model")},
            "labels": {str(k): v for k, v in d["labels"].items()},
            "proportions": d["props"], "effects": d["effects"],
        }
    (out_dir / "topic_convergence.json").write_text(json.dumps(clean, indent=2, default=str))

    # CSVs
    all_geo, all_props, all_fx = [], [], []
    for scale, d in all_results.items():
        all_geo.extend({"scale": scale, **r} for r in d["geo"])
        all_props.extend({"scale": scale, **r} for r in d["props"])
        all_fx.extend({"scale": scale, **r} for r in d["effects"])

    for fname, rows in [("geometric_metrics.csv", all_geo), ("effect_sizes.csv", all_fx)]:
        if rows:
            with (out_dir / fname).open("w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader(); w.writerows(rows)

    if all_props:
        all_fields = list(dict.fromkeys(k for r in all_props for k in r))
        with (out_dir / "topic_proportions.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=all_fields, restval="")
            w.writeheader(); w.writerows(all_props)

    # Report
    lines = [
        "# Topic Convergence Analysis", "",
        "## Method", "",
        "- **Embeddings**: Qwen3-Embedding-8B (4096-dim) via OpenRouter",
        "- **Vendi Score**: vendi-score v0.0.3 (Friedman & Dieng, TMLR 2023)",
        "- **Intrinsic dim**: TwoNN via scikit-dimension v0.3.4 (Facco et al., 2017)",
        "- **JSD**: scipy.spatial.distance.jensenshannon, PCA(1) histogram discretization",
        "- **Clustering**: PCA(50) + L2-norm + KMeans (silhouette-selected K)", "",
    ]
    for scale, d in all_results.items():
        ci = d["cluster"]
        lines.extend([f"## {scale}", "", f"k={ci['k']}, silhouette={ci['silhouette']:.3f}, PCA var={ci['pca_explained_variance']:.1%}", ""])
        lines.append("### Topics")
        for cid, lbl in sorted(d["labels"].items()):
            lines.append(f"- **{lbl['label']}** ({ci['cluster_sizes'][cid]} posts): {lbl['description']}")
        lines.extend(["", "### Geometric summary", "",
                       "| Condition | VS (0-15m) | VS (45-60m) | ID (0-15m) | ID (45-60m) |",
                       "|-----------|------------|-------------|------------|-------------|"])
        for cond in CONDITION_ORDER:
            g = sorted([r for r in d["geo"] if r["condition"] == cond], key=lambda r: r["bin_idx"])
            if not g: continue
            fmt = lambda v: f"{v:.1f}" if not math.isnan(v) else "—"
            lines.append(f"| {CONDITION_LABELS.get(cond, cond)} | {fmt(g[0]['vendi_score'])} | {fmt(g[-1]['vendi_score'])} | {fmt(g[0]['intrinsic_dim'])} | {fmt(g[-1]['intrinsic_dim'])} |")
        if d["effects"]:
            lines.extend(["", "### Effect sizes (vs mag0)", "", "| Metric | Condition | δ | Size |", "|--------|-----------|---|------|"])
            for e in d["effects"]:
                lines.append(f"| {e['metric']} | {e['condition_label']} | {e['cliffs_delta']:+.3f} | {e['effect_size']} |")
        lines.append("")

    (out_dir / "topic_convergence_report.md").write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def save_plot_data(scale: str, posts: list[Post], cluster_info: dict, labels: dict[int, dict],
                   geo: list[dict], props: list[dict], effects: list[dict], out_dir: Path) -> None:
    """Save all data needed for plotting to a single NPZ file. Replot without recomputing."""
    from sklearn.manifold import MDS
    from sklearn.metrics.pairwise import cosine_distances

    print(f"  Computing MDS coords for {len(posts)} posts...")
    X = cluster_info["X_norm"]
    X_centered = X - X.mean(axis=0)
    dist_matrix = cosine_distances(X_centered)
    mds = MDS(n_components=2, dissimilarity="precomputed", random_state=42, n_init=4, max_iter=300, normalized_stress="auto")
    coords = mds.fit_transform(dist_matrix)

    np.savez_compressed(
        out_dir / f"plot_data_{scale}.npz",
        # Per-post data
        conditions=np.array([p.condition for p in posts], dtype=object),
        cluster_ids=np.array([p.cluster_id for p in posts]),
        minutes=np.array([p.minutes_elapsed for p in posts]),
        mds_coords=coords,
        # Metadata
        k=np.array(cluster_info["k"]),
        cluster_sizes=np.array(cluster_info["cluster_sizes"]),
        silhouette=np.array(cluster_info["silhouette"]),
    )
    # Save labels + metrics as JSON (easier to read back)
    plot_meta = {
        "labels": {str(k): v for k, v in labels.items()},
        "geo": geo, "props": props, "effects": effects,
    }
    (out_dir / f"plot_data_{scale}.json").write_text(json.dumps(plot_meta, indent=2, default=str))
    print(f"  Saved plot_data_{scale}.npz + .json")


def replot_from_saved(scale: str, out_dir: Path, conditions: list[str], model_label: str) -> None:
    """Regenerate all plots from saved plot data — no clustering, no MDS, instant."""
    npz = np.load(out_dir / f"plot_data_{scale}.npz", allow_pickle=True)
    meta = json.loads((out_dir / f"plot_data_{scale}.json").read_text())

    coords = npz["mds_coords"]
    cond_arr = npz["conditions"]
    cluster_arr = npz["cluster_ids"]
    minutes_arr = npz["minutes"]
    k = int(npz["k"])
    labels = {int(ki): v for ki, v in meta["labels"].items()}
    geo = meta["geo"]
    props = meta["props"]
    effects = meta["effects"]

    # --- Geometric plot ---
    plot_geometric(geo, scale, out_dir / f"geometric_{scale}.png", conditions=conditions)

    # --- Stacked area ---
    plot_stacked(props, labels, scale, out_dir / f"topics_{scale}.png", conditions=conditions)

    # --- Entropy ---
    plot_entropy(props, scale, out_dir / f"entropy_{scale}.png", conditions=conditions)

    # --- MDS topic map (from saved coords, no recomputation) ---
    topic_colors = {ci: TOPIC_COLORS[ci] if ci < len(TOPIC_COLORS) else f"C{ci}" for ci in range(k)}
    fig, axes = plt.subplots(2, 2, figsize=(12, 11))
    for idx, cond in enumerate(conditions[:4]):
        ax = axes.flat[idx]
        cond_mask = cond_arr == cond
        other = ~cond_mask
        ax.scatter(coords[other, 0], coords[other, 1], c="#E5E7EB", s=4, alpha=0.25, rasterized=True)
        for ci in range(k):
            mask = cond_mask & (cluster_arr == ci)
            if mask.sum() == 0:
                continue
            ax.scatter(coords[mask, 0], coords[mask, 1], c=[topic_colors[ci]], s=28, alpha=0.8,
                       label=labels[ci]["label"], edgecolors="white", linewidths=0.3, rasterized=True)
        ax.set_title(f"{SLIDE_LABELS.get(cond, cond)} (n={cond_mask.sum()})", fontsize=16, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal"); ax.spines[:].set_visible(False)
    handles, leg = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, leg, loc="lower center", ncol=min(k, 6), fontsize=17, frameon=True, bbox_to_anchor=(0.5, 0.0))
    fig.suptitle(f"Topic Map — MDS Projection ({model_label}, {scale})", fontsize=18, fontweight="bold")
    plt.subplots_adjust(hspace=0.15, wspace=0.08, top=0.93, bottom=0.07)
    fig.savefig(out_dir / f"mds_topics_{scale}.png", dpi=200, bbox_inches="tight"); plt.close(fig)

    # --- MDS temporal map (from saved coords) ---
    max_t = BIN_EDGES[-1]
    fig, axes = plt.subplots(2, 2, figsize=(12, 11))
    sc = None
    for idx, cond in enumerate(conditions[:4]):
        ax = axes.flat[idx]
        cond_mask = cond_arr == cond
        cond_times = np.clip(minutes_arr, 0, max_t)
        other = ~cond_mask
        ax.scatter(coords[other, 0], coords[other, 1], c="#E5E7EB", s=4, alpha=0.25, rasterized=True)
        cm = cond_mask & (cond_times <= max_t)
        if cm.sum() > 0:
            sc = ax.scatter(coords[cm, 0], coords[cm, 1], c=cond_times[cm], cmap="coolwarm",
                           s=28, alpha=0.8, vmin=0, vmax=max_t, edgecolors="white", linewidths=0.3, rasterized=True)
        ax.set_title(f"{SLIDE_LABELS.get(cond, cond)}", fontsize=16, fontweight="bold")
        ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect("equal"); ax.spines[:].set_visible(False)
    if sc is not None:
        fig.colorbar(sc, ax=axes.ravel().tolist(), shrink=0.5, label="Minutes elapsed", pad=0.02)
    fig.suptitle(f"Temporal Drift — MDS Projection ({model_label}, {scale})", fontsize=18, fontweight="bold")
    plt.subplots_adjust(hspace=0.12, wspace=0.08, top=0.93, bottom=0.03)
    fig.savefig(out_dir / f"mds_temporal_{scale}.png", dpi=200, bbox_inches="tight"); plt.close(fig)

    print(f"  Replotted {scale}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scales", default="n20,n30",
                        help="Comma-separated list of NPZ suffixes (e.g. 'n10,n20,n30' or 'kimi-k2.5_n10,gemini_n20')")
    parser.add_argument("--k", type=int, default=None)
    parser.add_argument("--skip-llm", action="store_true")
    parser.add_argument("--out-dir", type=str, default=None)
    parser.add_argument("--emb-dir", type=str, default=None)
    parser.add_argument("--model", type=str, default=None)
    parser.add_argument("--reference", type=str, default=None,
                        help="NPZ suffix to use as reference for topic discovery (default: first scale).")
    parser.add_argument("--conditions", type=str, default=None,
                        help="Comma-separated conditions to plot (default: mag0,mag5,mag25,dom-agi)")
    parser.add_argument("--model-label", type=str, default="GPT-5",
                        help="Model name for plot titles (e.g. 'GPT-5', 'Gemini Flash Lite')")
    parser.add_argument("--plot-only", action="store_true",
                        help="Skip computation, regenerate plots from saved plot_data_*.npz files")
    parser.add_argument("--duration", type=float, default=None,
                        help="Run duration in minutes (default 60). Adjusts bin edges.")
    args = parser.parse_args()

    global OUT_DIR, CHAT_MODEL, BIN_EDGES
    if args.duration:
        step = args.duration / 4
        BIN_EDGES = [round(i * step, 2) for i in range(5)]
    scales = args.scales.split(",")
    if args.out_dir: OUT_DIR = Path(args.out_dir)
    if args.model: CHAT_MODEL = args.model
    emb_dir = Path(args.emb_dir) if args.emb_dir else EMB_DIR
    plot_conds = args.conditions.split(",") if args.conditions else DEFAULT_PLOT_CONDITIONS
    model_label = args.model_label
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- Plot-only mode: just regenerate plots from saved data ---
    if args.plot_only:
        print(f"Plot-only mode: regenerating from {OUT_DIR}")
        for scale in scales:
            if not (OUT_DIR / f"plot_data_{scale}.npz").exists():
                print(f"  SKIP {scale}: no plot_data_{scale}.npz found")
                continue
            replot_from_saved(scale, OUT_DIR, plot_conds, model_label)
        print("Done.")
        return

    # --- Full computation mode ---
    ref_scale = args.reference or scales[0]
    ref_cluster = None
    ref_labels = None

    if True:
        # Phase 1: Discover topics on reference scale
        print(f"\n{'='*60}")
        print(f"REFERENCE: {ref_scale} (topic discovery)")
        print(f"{'='*60}")

        ref_posts = load_posts(ref_scale, emb_dir)
        print(f"  {len(ref_posts)} posts, {len(set(p.condition for p in ref_posts))} conditions")

        print("Clustering (reference)...")
        ref_cluster = cluster_posts(ref_posts, k=args.k)
        ref_cluster["is_reference"] = True
        print(f"  k={ref_cluster['k']}, silhouette={ref_cluster['silhouette']:.3f}")

        print("Labeling topics...")
        ref_labels = label_clusters(ref_posts, ref_cluster, OUT_DIR / "label_cache_reference.json", args.skip_llm)
        for ci, lbl in sorted(ref_labels.items()):
            print(f"  {ci}: {lbl['label']} — {lbl['description']}")

    # Phase 2: Process each scale
    all_results: dict[str, dict] = {}

    for scale in scales:
        print(f"\n{'='*60}\n{scale}\n{'='*60}")

        if scale == ref_scale:
            posts = ref_posts
            cluster = ref_cluster
        else:
            posts = load_posts(scale, emb_dir)
            print(f"  {len(posts)} posts, {len(set(p.condition for p in posts))} conditions")
            print("Assigning to reference topics (LLM classification)...")
            cluster = assign_to_reference(posts, ref_cluster, ref_labels,
                                          cache_path=OUT_DIR / f"classify_cache_{scale}.json")
            print(f"  sizes={cluster['cluster_sizes']}, silhouette={cluster['silhouette']:.3f}")

        labels = ref_labels

        for p in posts:
            p.topic_label = labels.get(p.cluster_id, {}).get("label", "")

        print("Geometric metrics..."); geo = compute_geometric_metrics(posts)
        print("Topic proportions..."); props = compute_topic_proportions(posts, labels)
        print("Effect sizes..."); effects = compute_effect_sizes(geo)

        # Save plot data (includes MDS — slow but only once)
        print("Saving plot data + MDS...")
        save_plot_data(scale, posts, cluster, labels, geo, props, effects, OUT_DIR)

        # Generate plots
        print("Plotting...")
        replot_from_saved(scale, OUT_DIR, plot_conds, model_label)

        all_results[scale] = {"geo": geo, "cluster": cluster, "labels": labels, "props": props, "effects": effects}

    print(f"\nWriting outputs to {OUT_DIR}...")
    write_outputs(all_results, OUT_DIR)
    print("Done.")
    for p in sorted(OUT_DIR.iterdir()):
        print(f"  {p}")


if __name__ == "__main__":
    main()
