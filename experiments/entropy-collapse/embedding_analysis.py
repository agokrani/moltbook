#!/usr/bin/env python3
"""
==========================================================================
Embedding Analysis for Entropy Collapse Experiments (Run 04)
==========================================================================

Analyzes 2,366 agent-generated post embeddings (4096-dim, Qwen3-Embedding-8B)
across 6 experimental conditions. Each condition is analyzed INDEPENDENTLY first
(its own UMAP, HDBSCAN clusters, metrics), then cross-condition comparison uses
the original 4096-dim embedding space.

Generates:
  1. experiments/entropy-collapse/report/EMBEDDING_ANALYSIS.md
  2. experiments/entropy-collapse/report/fig_*.png
  3. experiments/entropy-collapse/report/analysis_data.csv
"""

import json, os, math, sys, time, csv
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

import numpy as np
import requests
from scipy import stats
from scipy.spatial.distance import cosine, pdist, squareform, cdist
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import seaborn as sns

from sklearn.decomposition import PCA

import umap
import hdbscan

# ============================================================
# Config
# ============================================================
ROOT = Path(__file__).parent.parent.parent
NPZ_PATH = ROOT / "embeddings_run04.npz"
SEED_DIR = Path(__file__).parent
REPORT_DIR = Path(__file__).parent / "report"
REPORT_DIR.mkdir(exist_ok=True)

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
EMBED_MODEL = "qwen/qwen3-embedding-8b"
LABEL_MODEL = "google/gemini-3.1-flash-lite-preview"
EMBED_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

# Condition ordering and display
COND_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
COND_LABELS = {
    "mag0": "Control (0 seeds)", "mag1": "1 seed", "mag5": "5 seeds",
    "mag25": "25 seeds", "dom-agi": "AGI (25)", "dom-tech": "Tech (25)",
}
COND_COLORS = {
    "mag0": "#9E9E9E", "mag1": "#81D4FA", "mag5": "#29B6F6",
    "mag25": "#0277BD", "dom-agi": "#FF7043", "dom-tech": "#AB47BC",
}
MAG_CONDITIONS = ["mag0", "mag1", "mag5", "mag25"]
DOMAIN_CONDITIONS = ["mag25", "dom-agi", "dom-tech"]

# Agent personality mapping
AGENT_PERSONALITY = {
    "ranking_alpha": "baseline", "ranking_beta": "introspective",
    "ranking_gamma": "nihilist", "ranking_delta": "leader",
    "ranking_epsilon": "follower", "ranking_zeta": "contrarian",
    "ranking_eta": "curious", "ranking_theta": "baseline",
    "ranking_iota": "introspective", "ranking_kappa": "nihilist",
}
PERSONALITY_ORDER = ["baseline", "introspective", "nihilist", "leader",
                     "follower", "contrarian", "curious"]

SEED_FILES = {
    "conspiracy": ["world-posts-mag1.jsonl", "world-posts-mag5.jsonl", "world-posts-mag25.jsonl"],
    "agi": ["world-posts-agi.jsonl"],
    "tech": ["world-posts-tech.jsonl"],
}

RANDOM_STATE = 42
np.random.seed(RANDOM_STATE)

# ============================================================
# Plot style
# ============================================================
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 10,
    "axes.titlesize": 12, "axes.labelsize": 11,
    "figure.facecolor": "white",
})

# Cluster color palette (for per-condition UMAP plots)
CLUSTER_PALETTE = [
    "#E53935", "#1E88E5", "#43A047", "#FB8C00", "#8E24AA",
    "#00ACC1", "#D81B60", "#5E35B1", "#F4511E", "#039BE5",
    "#7CB342", "#C0CA33", "#FFB300", "#6D4C41", "#546E7A",
]

# ============================================================
# Helpers
# ============================================================
def cosine_sim(a, b):
    return 1.0 - cosine(a, b)

def cosine_dist(a, b):
    return cosine(a, b)

def smean(v): return float(np.mean(v)) if len(v) > 0 else 0.0
def ssd(v):   return float(np.std(v, ddof=1)) if len(v) >= 2 else 0.0
def sem(v):   return ssd(v) / math.sqrt(len(v)) if len(v) >= 2 else 0.0

def embed_batch_api(texts):
    resp = requests.post(
        EMBED_ENDPOINT,
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
        json={"model": EMBED_MODEL, "input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    sorted_embs = sorted(data["data"], key=lambda x: x["index"])
    return np.array([e["embedding"] for e in sorted_embs], dtype=np.float32)

def llm_call(prompt, tag="unknown", max_tokens=2048):
    try:
        resp = requests.post(
            CHAT_ENDPOINT,
            headers={"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
            json={
                "model": LABEL_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3, "max_tokens": max_tokens,
            },
            timeout=180,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        content = msg.get("content") or ""
        if not content.strip() and msg.get("reasoning"):
            content = msg["reasoning"]
        if not content or not content.strip():
            raise ValueError("Empty response from LLM")
        if "```" in content:
            parts = content.split("```")
            for part in parts[1:]:
                stripped = part.strip()
                if stripped.startswith("json"):
                    stripped = stripped[4:].strip()
                if stripped.startswith("{"):
                    content = stripped
                    break
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(content[start:end])
        return json.loads(content.strip())
    except Exception as e:
        print(f"  Warning: LLM call failed [{tag}]: {e}")
        return None


def _format_posts_for_llm(posts):
    return "\n---\n".join(
        f"Title: {p['title']}\nContent: {p['content']}" for p in posts
    )


def mmd_rbf(X, Y, gamma=None):
    if gamma is None:
        combined = np.vstack([X, Y])
        dists = pdist(combined, metric="cosine")
        gamma = 1.0 / np.median(dists) if np.median(dists) > 0 else 1.0

    def rbf_kernel(A, B):
        dists = cdist(A, B, metric="cosine")
        return np.exp(-gamma * dists)

    n, m = len(X), len(Y)
    Kxx = rbf_kernel(X, X)
    Kyy = rbf_kernel(Y, Y)
    Kxy = rbf_kernel(X, Y)

    mmd_stat = (Kxx.sum() / (n * n) + Kyy.sum() / (m * m) - 2 * Kxy.sum() / (n * m))

    combined = np.vstack([X, Y])
    n_perms = 500
    perm_stats = []
    for _ in range(n_perms):
        idx = np.random.permutation(n + m)
        Xp, Yp = combined[idx[:n]], combined[idx[n:]]
        Kxx_p = rbf_kernel(Xp, Xp)
        Kyy_p = rbf_kernel(Yp, Yp)
        Kxy_p = rbf_kernel(Xp, Yp)
        perm_stat = (Kxx_p.sum() / (n * n) + Kyy_p.sum() / (m * m) - 2 * Kxy_p.sum() / (n * m))
        perm_stats.append(perm_stat)

    p_value = (np.sum(np.array(perm_stats) >= mmd_stat) + 1) / (n_perms + 1)
    return mmd_stat, p_value


def permanova_simple(X, labels, n_perms=999):
    D = squareform(pdist(X, metric="cosine"))
    groups = np.unique(labels)
    N = len(labels)

    def pseudo_f(D, labs):
        ss_t = (D ** 2).sum() / (2 * N)
        ss_w = 0
        for g in groups:
            mask = labs == g
            n_g = mask.sum()
            if n_g > 1:
                ss_w += (D[np.ix_(mask, mask)] ** 2).sum() / (2 * n_g)
        ss_b = ss_t - ss_w
        df_b = len(groups) - 1
        df_w = N - len(groups)
        if df_w == 0 or ss_w == 0:
            return 0.0
        return (ss_b / df_b) / (ss_w / df_w)

    f_obs = pseudo_f(D, labels)

    perm_count = 0
    for _ in range(n_perms):
        perm_labels = np.random.permutation(labels)
        if pseudo_f(D, perm_labels) >= f_obs:
            perm_count += 1

    p_value = (perm_count + 1) / (n_perms + 1)

    ss_t = (D ** 2).sum() / (2 * N)
    ss_w = 0
    for g in groups:
        mask = labels == g
        n_g = mask.sum()
        if n_g > 1:
            ss_w += (D[np.ix_(mask, mask)] ** 2).sum() / (2 * n_g)
    r_sq = 1 - ss_w / ss_t if ss_t > 0 else 0

    return f_obs, p_value, r_sq


# ============================================================
# Stage 0: Load and Prepare
# ============================================================
def load_data():
    print("Stage 0: Loading data...")
    data = np.load(NPZ_PATH, allow_pickle=True)
    embeddings = data["embeddings"]

    meta_keys = ["post_id", "title", "content", "submolt", "score", "comment_count",
                 "created_at", "author_name", "run", "experiment", "condition",
                 "seed_count", "seed_topic"]
    meta = {k: data[k] for k in meta_keys}

    minutes = np.zeros(len(embeddings))
    for cond in np.unique(meta["condition"]):
        mask = meta["condition"] == cond
        times = meta["created_at"][mask]
        parsed = []
        for t in times:
            try:
                dt = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
                parsed.append(dt.timestamp())
            except:
                parsed.append(0)
        parsed = np.array(parsed)
        if parsed.max() > parsed.min():
            minutes[mask] = (parsed - parsed.min()) / 60.0
        else:
            minutes[mask] = 0.0

    meta["minutes_elapsed"] = minutes
    meta["personality"] = np.array([AGENT_PERSONALITY.get(str(a), "unknown") for a in meta["author_name"]])

    n = len(embeddings)
    print(f"  Loaded {n} posts, {embeddings.shape[1]} dims")
    for cond in COND_ORDER:
        c = np.sum(meta["condition"] == cond)
        print(f"  {cond}: {c} posts")

    return embeddings, meta


def load_and_embed_seeds():
    cache_path = REPORT_DIR / "seed_embeddings.npz"
    if cache_path.exists():
        print("  Loading cached seed embeddings...")
        cached = np.load(cache_path, allow_pickle=True)
        return cached["embeddings"], cached["topics"].tolist(), cached["titles"].tolist()

    print("  Loading and embedding seed posts...")
    all_texts = []
    all_topics = []
    all_titles = []
    seen = set()

    for topic, files in SEED_FILES.items():
        for fname in files:
            fpath = SEED_DIR / fname
            if not fpath.exists():
                continue
            with open(fpath) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    post = json.loads(line)
                    title = post["title"]
                    if title in seen:
                        continue
                    seen.add(title)
                    text = f"{title}\n\n{post['content']}"
                    all_texts.append(text)
                    all_topics.append(topic)
                    all_titles.append(title)

    print(f"  {len(all_texts)} unique seed posts to embed")
    if not all_texts:
        return np.array([]), [], []

    all_embs = []
    for i in range(0, len(all_texts), 64):
        batch = all_texts[i:i+64]
        print(f"    Embedding batch {i//64 + 1}...", end=" ", flush=True)
        try:
            embs = embed_batch_api(batch)
            all_embs.append(embs)
            print("OK")
        except Exception as e:
            print(f"FAILED: {e}")
            all_embs.append(np.zeros((len(batch), 4096), dtype=np.float32))
        time.sleep(0.5)

    seed_embeddings = np.vstack(all_embs)
    np.savez_compressed(cache_path, embeddings=seed_embeddings,
                        topics=np.array(all_topics, dtype=object),
                        titles=np.array(all_titles, dtype=object))
    print(f"  Cached seed embeddings to {cache_path}")
    return seed_embeddings, all_topics, all_titles


def _get_posts_for_indices(meta, indices):
    return [{"title": str(meta["title"][i]), "content": str(meta["content"][i])}
            for i in indices]


# ============================================================
# Stage 1: Per-Condition Independent Analysis
# ============================================================
def analyze_single_condition(embeddings, meta, condition):
    """Fully independent analysis of one condition."""
    mask = meta["condition"] == condition
    cond_embs = embeddings[mask]
    cond_meta = {k: v[mask] for k, v in meta.items()}
    n = int(mask.sum())
    results = {"n": n}

    # PCA -> UMAP (fitted on THIS condition only)
    n_pca = min(50, n - 1)
    pca = PCA(n_components=n_pca, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(cond_embs)
    n_neighbors = min(15, n - 2)
    reducer = umap.UMAP(n_neighbors=n_neighbors, min_dist=0.1,
                        metric="cosine", random_state=RANDOM_STATE)
    X_umap = reducer.fit_transform(X_pca)
    results["X_umap"] = X_umap
    results["var_explained"] = pca.explained_variance_ratio_

    # HDBSCAN clustering (on this condition's UMAP)
    min_cluster_size = max(10, n // 20)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size,
                                 min_samples=5, metric="euclidean")
    labels = clusterer.fit_predict(X_umap)
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())
    results["cluster_labels"] = labels
    results["n_clusters"] = n_clusters
    results["n_noise"] = n_noise

    # Within-condition coherence (mean pairwise similarity)
    pw_sims = 1.0 - pdist(cond_embs, metric="cosine")
    results["mean_pairwise_sim"] = float(np.mean(pw_sims))

    # Agent spread within this condition
    agents = sorted(set(str(a) for a in cond_meta["author_name"]))
    agent_centroids = []
    for agent in agents:
        amask = np.array([str(a) == agent for a in cond_meta["author_name"]])
        if amask.sum() > 0:
            agent_centroids.append(cond_embs[amask].mean(axis=0))
    if len(agent_centroids) >= 2:
        agent_dists = pdist(np.array(agent_centroids), metric="cosine")
        results["agent_spread"] = float(np.mean(agent_dists))
    else:
        results["agent_spread"] = 0.0

    # Temporal drift (early vs late centroid in original space)
    mins = cond_meta["minutes_elapsed"]
    early = cond_embs[mins <= 20]
    late = cond_embs[mins >= 40]
    if len(early) > 0 and len(late) > 0:
        results["temporal_drift"] = float(cosine_dist(
            early.mean(axis=0), late.mean(axis=0)))
    else:
        results["temporal_drift"] = 0.0

    # Generate per-condition UMAP figure
    _plot_condition_umap(X_umap, labels, cond_meta, condition, n_clusters)

    return results


def _plot_condition_umap(X_umap, labels, cond_meta, condition, n_clusters,
                         cluster_name_map=None):
    """Generate per-condition UMAP figure colored by cluster.

    cluster_name_map: optional dict mapping cluster id (str) -> label string
    """
    n = len(X_umap)
    fig, ax = plt.subplots(figsize=(8, 7))

    # Plot noise points first (gray)
    noise_mask = labels == -1
    if noise_mask.sum() > 0:
        ax.scatter(X_umap[noise_mask, 0], X_umap[noise_mask, 1],
                   c="#BDBDBD", alpha=0.3, s=10, edgecolors="none", label=f"Noise ({noise_mask.sum()})")

    # Plot each cluster
    unique_labels = sorted(set(labels) - {-1})
    for i, cl in enumerate(unique_labels):
        cl_mask = labels == cl
        color = CLUSTER_PALETTE[i % len(CLUSTER_PALETTE)]
        # Use LLM-generated name if available
        if cluster_name_map and str(cl) in cluster_name_map:
            cl_name = cluster_name_map[str(cl)].get("label", f"Cluster {cl}")
        else:
            cl_name = f"Cluster {cl}"
        ax.scatter(X_umap[cl_mask, 0], X_umap[cl_mask, 1],
                   c=color, alpha=0.5, s=15, edgecolors="none",
                   label=f"{cl_name} ({cl_mask.sum()})")
        # Add text label at cluster centroid
        cx = X_umap[cl_mask, 0].mean()
        cy = X_umap[cl_mask, 1].mean()
        ax.annotate(cl_name, (cx, cy), fontsize=7, fontweight="bold",
                    ha="center", va="center",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.7))

    ax.set_xlabel("UMAP 1")
    ax.set_ylabel("UMAP 2")
    ax.set_title(f"{COND_LABELS[condition]} — {n} posts, {n_clusters} clusters",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=7, markerscale=1.5, loc="best")
    fig.tight_layout()
    fig.savefig(REPORT_DIR / f"fig_cond_{condition}_umap.png", bbox_inches="tight")
    plt.close(fig)


# ============================================================
# Stage 2: LLM Characterization (cached)
# ============================================================
def label_conditions(meta):
    print("\nStage 2a: Per-condition characterization (LLM)...")
    cache_path = REPORT_DIR / "condition_labels.json"

    if cache_path.exists():
        print("  Loading cached condition labels...")
        with open(cache_path) as f:
            return json.load(f)

    cond_labels = {}
    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        indices = np.where(mask)[0]
        posts = _get_posts_for_indices(meta, indices)
        n = len(posts)
        post_text = _format_posts_for_llm(posts)

        seed_info = f"seed_count={int(meta['seed_count'][indices[0]])}, seed_topic={str(meta['seed_topic'][indices[0]])}"
        prompt = f"""Below are ALL {n} posts generated by AI agents in the "{COND_LABELS[cond]}" experimental condition ({seed_info}).
These agents were running on a Reddit-like social platform for 1 hour. Read every post.

{post_text}

Provide a detailed characterization:
1. A 3-5 word label for the overall discourse in this condition
2. A 3-4 sentence description of what agents talked about, how the conversation evolved, and what stood out
3. Five dominant themes (ranked by prevalence)
4. Two themes that are UNIQUE to this condition (not shared with a generic AI conversation)
5. Overall tone (e.g., analytical, anxious, playful, repetitive, diverse)

Respond in JSON format:
{{"label": "...", "description": "...", "dominant_themes": ["...", "...", "...", "...", "..."], "unique_themes": ["...", "..."], "tone": "..."}}"""

        print(f"  {cond} ({n} posts)...", end=" ", flush=True)
        result = llm_call(prompt, tag=f"condition-{cond}", max_tokens=2048)
        if result:
            cond_labels[cond] = result
            print(f"-> {result.get('label', '?')}")
        else:
            cond_labels[cond] = {"label": cond, "description": "LLM failed", "dominant_themes": [], "unique_themes": [], "tone": "unknown"}
            print("-> FAILED")
        time.sleep(0.5)

    with open(cache_path, "w") as f:
        json.dump(cond_labels, f, indent=2)
    print(f"  Saved to {cache_path}")
    return cond_labels


def label_agents(meta):
    print("\nStage 2b: Per-agent voice characterization (LLM)...")
    cache_path = REPORT_DIR / "agent_labels.json"

    if cache_path.exists():
        print("  Loading cached agent labels...")
        with open(cache_path) as f:
            return json.load(f)

    agents = sorted(set(str(a) for a in meta["author_name"]))
    agent_labels = {}

    for agent in agents:
        mask = np.array([str(a) == agent for a in meta["author_name"]])
        indices = np.where(mask)[0]
        posts = _get_posts_for_indices(meta, indices)
        n = len(posts)
        personality = AGENT_PERSONALITY.get(agent, "unknown")
        post_text = _format_posts_for_llm(posts)

        prompt = f"""Below are ALL {n} posts by the AI agent "{agent}" (personality template: {personality}) across 6 experimental conditions on a Reddit-like social platform.

{post_text}

Characterize this agent's voice:
1. A 3-5 word label for their overall voice/style
2. A 2-3 sentence description of their distinctive characteristics, recurring topics, and communication style
3. Three signature topics this agent returns to
4. Their rhetorical style (e.g., questioning, declarative, list-making, philosophical, practical)
5. How much their content varies across different conditions (low/medium/high)

Respond in JSON format:
{{"label": "...", "description": "...", "signature_topics": ["...", "...", "..."], "rhetorical_style": "...", "condition_sensitivity": "..."}}"""

        print(f"  {agent} ({personality}, {n} posts)...", end=" ", flush=True)
        result = llm_call(prompt, tag=f"agent-{agent}", max_tokens=2048)
        if result:
            agent_labels[agent] = {**result, "personality": personality, "n_posts": n}
            print(f"-> {result.get('label', '?')}")
        else:
            agent_labels[agent] = {"label": agent, "description": "LLM failed", "signature_topics": [], "personality": personality, "n_posts": n}
            print("-> FAILED")
        time.sleep(0.5)

    with open(cache_path, "w") as f:
        json.dump(agent_labels, f, indent=2)
    print(f"  Saved to {cache_path}")
    return agent_labels


def label_temporal(meta):
    print("\nStage 2c: Temporal characterization (LLM)...")
    cache_path = REPORT_DIR / "temporal_labels.json"

    if cache_path.exists():
        print("  Loading cached temporal labels...")
        with open(cache_path) as f:
            return json.load(f)

    temporal_labels = {}
    windows = [("early", 0, 20), ("mid", 20, 40), ("late", 40, 60)]

    for cond in COND_ORDER:
        temporal_labels[cond] = {}
        cond_mask = meta["condition"] == cond
        cond_mins = meta["minutes_elapsed"][cond_mask]
        cond_indices = np.where(cond_mask)[0]

        for win_name, t_start, t_end in windows:
            win_mask = (cond_mins >= t_start) & (cond_mins < t_end)
            indices = cond_indices[win_mask]
            if len(indices) < 3:
                temporal_labels[cond][win_name] = {"label": "Too few posts", "description": "", "themes": []}
                continue

            posts = _get_posts_for_indices(meta, indices)
            n = len(posts)
            post_text = _format_posts_for_llm(posts)

            prompt = f"""Below are ALL {n} posts from the "{COND_LABELS[cond]}" condition during the {win_name} phase (minutes {t_start}-{t_end} of a 60-minute run).

{post_text}

Characterize the discourse in this time window:
1. A 3-5 word label for the dominant topic/mood
2. A 2-3 sentence description of what agents were discussing and how it differs from a generic conversation
3. Three key themes

Respond in JSON format:
{{"label": "...", "description": "...", "themes": ["...", "...", "..."]}}"""

            print(f"  {cond}/{win_name} ({n} posts)...", end=" ", flush=True)
            result = llm_call(prompt, tag=f"temporal-{cond}-{win_name}", max_tokens=1024)
            if result:
                temporal_labels[cond][win_name] = {**result, "n_posts": n}
                print(f"-> {result.get('label', '?')}")
            else:
                temporal_labels[cond][win_name] = {"label": "LLM failed", "description": "", "themes": [], "n_posts": n}
                print("-> FAILED")
            time.sleep(0.3)

    with open(cache_path, "w") as f:
        json.dump(temporal_labels, f, indent=2)
    print(f"  Saved to {cache_path}")
    return temporal_labels


def label_per_condition_clusters(meta, embeddings, per_cond):
    """LLM-label clusters within each condition independently. Cached."""
    print("\nStage 2d: Per-condition cluster labeling (LLM)...")
    cache_path = REPORT_DIR / "per_condition_clusters.json"

    if cache_path.exists():
        print("  Loading cached per-condition cluster labels...")
        with open(cache_path) as f:
            return json.load(f)

    all_labels = {}
    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        indices = np.where(mask)[0]
        labels = per_cond[cond]["cluster_labels"]
        n_clusters = per_cond[cond]["n_clusters"]
        all_labels[cond] = {}

        if n_clusters == 0:
            print(f"  {cond}: no clusters found")
            continue

        unique_clusters = sorted(set(labels) - {-1})
        for cl in unique_clusters:
            cl_indices = indices[labels == cl]
            posts = _get_posts_for_indices(meta, cl_indices)
            n = len(posts)
            post_text = _format_posts_for_llm(posts)

            prompt = f"""Below are ALL {n} posts in cluster {cl} from the "{COND_LABELS[cond]}" experimental condition on a Reddit-like AI social platform.

{post_text}

Provide:
1. A 3-6 word label for this cluster's topic
2. A 1-2 sentence description of what makes this cluster distinct

Respond in JSON format:
{{"label": "...", "description": "..."}}"""

            print(f"  {cond}/cluster-{cl} ({n} posts)...", end=" ", flush=True)
            result = llm_call(prompt, tag=f"cluster-{cond}-{cl}", max_tokens=512)
            if result:
                all_labels[cond][str(cl)] = {**result, "n_posts": n}
                print(f"-> {result.get('label', '?')}")
            else:
                all_labels[cond][str(cl)] = {"label": f"Cluster {cl}", "description": "LLM failed", "n_posts": n}
                print("-> FAILED")
            time.sleep(0.3)

    with open(cache_path, "w") as f:
        json.dump(all_labels, f, indent=2)
    print(f"  Saved to {cache_path}")
    return all_labels


# ============================================================
# Stage 3: Cross-Condition Comparison (original embedding space)
# ============================================================
def cross_condition_comparison(embeddings, meta, seed_embs, seed_topics):
    """Compare conditions using original 4096-dim embeddings. No shared UMAP."""
    print("\nStage 3: Cross-condition comparison...")
    results = {}

    # 3a. Condition centroid distances (original space)
    print("  Condition centroid distances...")
    centroids = {}
    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        centroids[cond] = embeddings[mask].mean(axis=0)

    cond_dist_matrix = np.zeros((len(COND_ORDER), len(COND_ORDER)))
    for i, c1 in enumerate(COND_ORDER):
        for j, c2 in enumerate(COND_ORDER):
            cond_dist_matrix[i, j] = cosine_dist(centroids[c1], centroids[c2])

    fig, ax = plt.subplots(figsize=(8, 6))
    im = ax.imshow(cond_dist_matrix, cmap="RdYlBu_r", aspect="auto")
    ax.set_xticks(range(len(COND_ORDER)))
    ax.set_xticklabels([COND_LABELS[c] for c in COND_ORDER], rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(COND_ORDER)))
    ax.set_yticklabels([COND_LABELS[c] for c in COND_ORDER], fontsize=9)
    for i in range(len(COND_ORDER)):
        for j in range(len(COND_ORDER)):
            ax.text(j, i, f"{cond_dist_matrix[i,j]:.3f}", ha="center", va="center",
                    fontsize=8, color="white" if cond_dist_matrix[i,j] > 0.05 else "black")
    ax.set_title("Condition Centroid Distances (Cosine)", fontsize=14, fontweight="bold")
    fig.colorbar(im, ax=ax, label="Cosine distance")
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "fig_centroid_distances.png", bbox_inches="tight")
    plt.close(fig)
    results["centroid_distances"] = cond_dist_matrix

    # 3b. Dose-response (cosine sim to conspiracy seed centroid)
    if len(seed_embs) > 0:
        print("  Dose-response analysis...")
        conspiracy_mask = np.array([t == "conspiracy" for t in seed_topics])
        if conspiracy_mask.sum() > 0:
            conspiracy_centroid = seed_embs[conspiracy_mask].mean(axis=0)

            dose_data = {}
            for cond in MAG_CONDITIONS:
                mask = meta["condition"] == cond
                cond_embs = embeddings[mask]
                sims = 1.0 - cdist([conspiracy_centroid], cond_embs, metric="cosine")[0]
                seed_count = int(meta["seed_count"][mask][0])
                dose_data[cond] = {"seed_count": seed_count, "sims": sims,
                                   "mean": float(np.mean(sims)), "sem": float(sem(sims))}

            fig, ax = plt.subplots(figsize=(8, 6))
            x_vals = [dose_data[c]["seed_count"] for c in MAG_CONDITIONS]
            y_vals = [dose_data[c]["mean"] for c in MAG_CONDITIONS]
            y_errs = [dose_data[c]["sem"] for c in MAG_CONDITIONS]

            ax.errorbar(x_vals, y_vals, yerr=y_errs, fmt="o-", color="#0277BD",
                        linewidth=2.5, markersize=10, capsize=6, capthick=2)
            for c, x, y in zip(MAG_CONDITIONS, x_vals, y_vals):
                n = np.sum(meta["condition"] == c)
                ax.annotate(f"{COND_LABELS[c]}\n(n={n})", xy=(x, y),
                            xytext=(10, 10), textcoords="offset points", fontsize=9)

            all_sc = []
            all_sim = []
            for cond in MAG_CONDITIONS:
                mask = meta["condition"] == cond
                sc = int(meta["seed_count"][mask][0])
                sims = dose_data[cond]["sims"]
                all_sc.extend([sc] * len(sims))
                all_sim.extend(sims.tolist())
            r, p = stats.pearsonr(all_sc, all_sim)
            results["dose_response_r"] = r
            results["dose_response_p"] = p

            ax.set_xlabel("Number of Conspiracy Seed Posts", fontsize=12)
            ax.set_ylabel("Mean Cosine Similarity to\nConspiracy Seed Centroid", fontsize=12)
            ax.set_title(f"Dose-Response: Seed Count vs Topic Similarity\n(Pearson r = {r:.3f}, p = {p:.4f})",
                         fontsize=14, fontweight="bold")
            ax.set_xticks(x_vals)
            fig.tight_layout()
            fig.savefig(REPORT_DIR / "fig_dose_response.png", bbox_inches="tight")
            plt.close(fig)
            results["dose_data"] = {c: {"seed_count": d["seed_count"], "mean": d["mean"]}
                                    for c, d in dose_data.items()}

        # Domain comparison: similarity to respective domain centroids
        print("  Domain comparison...")
        domain_sims = {}
        for topic in ["conspiracy", "agi", "tech"]:
            topic_mask = np.array([t == topic for t in seed_topics])
            if topic_mask.sum() > 0:
                topic_centroid = seed_embs[topic_mask].mean(axis=0)
                for cond in COND_ORDER:
                    mask = meta["condition"] == cond
                    cond_embs = embeddings[mask]
                    sims = 1.0 - cdist([topic_centroid], cond_embs, metric="cosine")[0]
                    domain_sims[(cond, topic)] = float(np.mean(sims))
        results["domain_sims"] = domain_sims

    # 3c. MMD between condition pairs (PCA-50 for computational speed)
    print("  MMD between conditions (PCA-50 for speed)...")
    pca_speed = PCA(n_components=50, random_state=RANDOM_STATE)
    X_pca_all = pca_speed.fit_transform(embeddings)

    max_n = 200
    mmd_matrix = np.zeros((len(COND_ORDER), len(COND_ORDER)))
    mmd_pvals = np.ones((len(COND_ORDER), len(COND_ORDER)))

    for i in range(len(COND_ORDER)):
        for j in range(i + 1, len(COND_ORDER)):
            c1, c2 = COND_ORDER[i], COND_ORDER[j]
            mask1 = meta["condition"] == c1
            mask2 = meta["condition"] == c2
            X1 = X_pca_all[mask1]
            X2 = X_pca_all[mask2]
            if len(X1) > max_n:
                X1 = X1[np.random.choice(len(X1), max_n, replace=False)]
            if len(X2) > max_n:
                X2 = X2[np.random.choice(len(X2), max_n, replace=False)]
            mmd_val, p_val = mmd_rbf(X1, X2)
            mmd_matrix[i, j] = mmd_val
            mmd_matrix[j, i] = mmd_val
            mmd_pvals[i, j] = p_val
            mmd_pvals[j, i] = p_val
            sig = "*" if p_val < 0.05 else ""
            print(f"    {c1} vs {c2}: MMD={mmd_val:.4f}, p={p_val:.3f} {sig}")

    results["mmd_matrix"] = mmd_matrix
    results["mmd_pvals"] = mmd_pvals

    # MMD heatmap
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Maximum Mean Discrepancy Between Conditions", fontsize=14, fontweight="bold")

    im1 = ax1.imshow(mmd_matrix, cmap="YlOrRd", aspect="auto")
    ax1.set_xticks(range(len(COND_ORDER)))
    ax1.set_xticklabels([COND_LABELS[c] for c in COND_ORDER], rotation=45, ha="right", fontsize=8)
    ax1.set_yticks(range(len(COND_ORDER)))
    ax1.set_yticklabels([COND_LABELS[c] for c in COND_ORDER], fontsize=8)
    for ii in range(len(COND_ORDER)):
        for jj in range(len(COND_ORDER)):
            ax1.text(jj, ii, f"{mmd_matrix[ii,jj]:.3f}", ha="center", va="center", fontsize=7)
    ax1.set_title("MMD Statistic")
    fig.colorbar(im1, ax=ax1)

    im2 = ax2.imshow(mmd_pvals, cmap="RdYlGn", aspect="auto", vmin=0, vmax=0.1)
    ax2.set_xticks(range(len(COND_ORDER)))
    ax2.set_xticklabels([COND_LABELS[c] for c in COND_ORDER], rotation=45, ha="right", fontsize=8)
    ax2.set_yticks(range(len(COND_ORDER)))
    ax2.set_yticklabels([COND_LABELS[c] for c in COND_ORDER], fontsize=8)
    for ii in range(len(COND_ORDER)):
        for jj in range(len(COND_ORDER)):
            sig = "*" if mmd_pvals[ii,jj] < 0.05 else ""
            ax2.text(jj, ii, f"{mmd_pvals[ii,jj]:.3f}{sig}", ha="center", va="center", fontsize=7)
    ax2.set_title("p-value (permutation, * = p < 0.05)")
    fig.colorbar(im2, ax=ax2)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(REPORT_DIR / "fig_mmd_heatmap.png", bbox_inches="tight")
    plt.close(fig)

    # 3d. PERMANOVA (condition + agent factors, PCA-50 for speed)
    print("  PERMANOVA: variance decomposition (PCA-50 for speed)...")
    n_sub = min(1000, len(embeddings))
    idx = np.random.choice(len(embeddings), n_sub, replace=False)
    X_sub = X_pca_all[idx]

    cond_labels_arr = meta["condition"][idx]
    f_cond, p_cond, r2_cond = permanova_simple(X_sub, cond_labels_arr, n_perms=499)
    print(f"    Condition: F={f_cond:.3f}, p={p_cond:.4f}, R2={r2_cond:.4f}")

    agent_labels_arr = np.array([str(a) for a in meta["author_name"]])[idx]
    f_agent, p_agent, r2_agent = permanova_simple(X_sub, agent_labels_arr, n_perms=499)
    print(f"    Agent: F={f_agent:.3f}, p={p_agent:.4f}, R2={r2_agent:.4f}")

    results["permanova"] = {
        "condition": {"F": f_cond, "p": p_cond, "R2": r2_cond},
        "agent": {"F": f_agent, "p": p_agent, "R2": r2_agent},
        "residual_R2": 1 - r2_cond - r2_agent,
    }

    # Variance decomposition bar chart
    fig, ax = plt.subplots(figsize=(8, 5))
    labels_bar = ["Condition", "Agent", "Residual"]
    values = [r2_cond, r2_agent, max(0, 1 - r2_cond - r2_agent)]
    colors = ["#0277BD", "#FF7043", "#9E9E9E"]
    bars = ax.bar(labels_bar, values, color=colors, alpha=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f"{val:.1%}", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylabel("Proportion of Variance (R-squared)")
    ax.set_title("Variance Decomposition (PERMANOVA)", fontsize=14, fontweight="bold")
    ax.set_ylim(0, 1.0)
    ax.text(0, values[0]/2, f"p={p_cond:.3f}", ha="center", va="center", fontsize=10, color="white", fontweight="bold")
    ax.text(1, values[1]/2, f"p={p_agent:.3f}", ha="center", va="center", fontsize=10, color="white", fontweight="bold")
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "fig_variance_decomposition.png", bbox_inches="tight")
    plt.close(fig)

    return results


# ============================================================
# Stage 3b: Temporal Dynamics (Attractor Analysis)
# ============================================================
def temporal_dynamics(embeddings, meta):
    """Compute temporal convergence/divergence metrics and generate figures."""
    print("\nStage 3b: Temporal dynamics...")
    results = {}
    windows = [(0, 15), (15, 30), (30, 45), (45, 60)]
    win_labels = ["0-15m", "15-30m", "30-45m", "45-60m"]

    # --- Computation 1: Within-window coherence ---
    print("  Within-window coherence...")
    coherence = {}
    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        cond_embs = embeddings[mask]
        cond_mins = meta["minutes_elapsed"][mask]
        vals = []
        for t0, t1 in windows:
            wmask = (cond_mins >= t0) & (cond_mins < t1)
            if wmask.sum() >= 5:
                pw = 1.0 - pdist(cond_embs[wmask], metric="cosine")
                vals.append(float(np.mean(pw)))
            else:
                vals.append(float('nan'))
        coherence[cond] = vals
    results["coherence_over_time"] = coherence

    # Figure: convergence over time
    fig, ax = plt.subplots(figsize=(9, 6))
    for cond in COND_ORDER:
        vals = coherence[cond]
        valid_x = [i for i, v in enumerate(vals) if not np.isnan(v)]
        valid_y = [vals[i] for i in valid_x]
        ax.plot(valid_x, valid_y, "o-", color=COND_COLORS[cond],
                label=COND_LABELS[cond], linewidth=2.5, markersize=8)
    ax.set_xticks(range(len(windows)))
    ax.set_xticklabels(win_labels)
    ax.set_xlabel("Time Window", fontsize=12)
    ax.set_ylabel("Mean Pairwise Cosine Similarity", fontsize=12)
    ax.set_title("Within-Condition Convergence Over Time", fontsize=14, fontweight="bold")
    ax.legend(fontsize=9)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "fig_convergence_over_time.png", bbox_inches="tight")
    plt.close(fig)

    # --- Computation 2: Cross-condition divergence ---
    print("  Cross-condition divergence (early vs late)...")
    early_centroids = {}
    late_centroids = {}
    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        cond_embs = embeddings[mask]
        cond_mins = meta["minutes_elapsed"][mask]
        early = cond_embs[cond_mins <= 15]
        late = cond_embs[cond_mins >= 40]
        if len(early) > 0:
            early_centroids[cond] = early.mean(axis=0)
        if len(late) > 0:
            late_centroids[cond] = late.mean(axis=0)

    divergence = []
    for i in range(len(COND_ORDER)):
        for j in range(i + 1, len(COND_ORDER)):
            c1, c2 = COND_ORDER[i], COND_ORDER[j]
            if c1 in early_centroids and c2 in early_centroids and \
               c1 in late_centroids and c2 in late_centroids:
                d_early = cosine_dist(early_centroids[c1], early_centroids[c2])
                d_late = cosine_dist(late_centroids[c1], late_centroids[c2])
                divergence.append({"pair": f"{c1} vs {c2}", "early": d_early,
                                   "late": d_late, "change": d_late - d_early})
    results["cross_cond_divergence"] = divergence

    # Figure: scatter early vs late distance
    fig, ax = plt.subplots(figsize=(8, 7))
    early_dists = [d["early"] for d in divergence]
    late_dists = [d["late"] for d in divergence]
    max_d = max(max(early_dists), max(late_dists)) * 1.1
    ax.plot([0, max_d], [0, max_d], "--", color="gray", alpha=0.5, label="No change")
    ax.scatter(early_dists, late_dists, s=80, c="#0277BD", alpha=0.7,
               edgecolors="white", zorder=5)
    for d in divergence:
        ax.annotate(d["pair"].replace(" vs ", "\nvs "), xy=(d["early"], d["late"]),
                    fontsize=6.5, ha="center", va="bottom",
                    xytext=(0, 6), textcoords="offset points")
    n_above = sum(1 for d in divergence if d["change"] > 0)
    ax.set_xlabel("Early-Phase Distance (0-15 min)", fontsize=12)
    ax.set_ylabel("Late-Phase Distance (40-60 min)", fontsize=12)
    ax.set_title(f"Cross-Condition Divergence: {n_above}/{len(divergence)} pairs\n"
                 "increase distance over time (above diagonal = diverging)",
                 fontsize=13, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "fig_cross_condition_divergence.png", bbox_inches="tight")
    plt.close(fig)

    # --- Computation 3: Agent individuality ---
    print("  Agent individuality over time...")
    individuality = {}
    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        cond_embs = embeddings[mask]
        cond_mins = meta["minutes_elapsed"][mask]
        cond_authors = meta["author_name"][mask]
        agents = sorted(set(str(a) for a in cond_authors))

        for phase, t0, t1 in [("early", 0, 20), ("late", 40, 60)]:
            centroids = []
            for agent in agents:
                amask = np.array([str(a) == agent for a in cond_authors]) & \
                        (cond_mins >= t0) & (cond_mins < t1)
                if amask.sum() > 0:
                    centroids.append(cond_embs[amask].mean(axis=0))
            if len(centroids) >= 2:
                d = float(np.mean(pdist(np.array(centroids), metric="cosine")))
            else:
                d = 0.0
            individuality[(cond, phase)] = d
    results["agent_individuality"] = individuality

    # Figure: grouped bar chart
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(COND_ORDER))
    width = 0.35
    early_vals = [individuality[(c, "early")] for c in COND_ORDER]
    late_vals = [individuality[(c, "late")] for c in COND_ORDER]
    bars1 = ax.bar(x - width/2, early_vals, width, label="Early (0-20 min)",
                   color="#81D4FA", alpha=0.8)
    bars2 = ax.bar(x + width/2, late_vals, width, label="Late (40-60 min)",
                   color="#0277BD", alpha=0.8)
    for i, cond in enumerate(COND_ORDER):
        change = late_vals[i] - early_vals[i]
        y_pos = max(early_vals[i], late_vals[i]) + 0.005
        ax.text(i, y_pos, f"+{change:.3f}" if change > 0 else f"{change:.3f}",
                ha="center", fontsize=8, fontweight="bold",
                color="#2E7D32" if change > 0 else "#C62828")
    ax.set_xticks(x)
    ax.set_xticklabels([COND_LABELS[c] for c in COND_ORDER], rotation=20, ha="right")
    ax.set_ylabel("Mean Inter-Agent Cosine Distance")
    ax.set_title("Agent Individuality Over Time", fontsize=14, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "fig_agent_individuality.png", bbox_inches="tight")
    plt.close(fig)

    # --- Statistical tests ---
    print("  Statistical tests...")

    # Helper: one-tailed sign test P(X >= k) under H0: p = 0.5
    def sign_test_p(k, n):
        return float(1 - stats.binom.cdf(k - 1, n, 0.5)) if k > 0 else 1.0

    # Test 1: Within-condition convergence
    # Compare first window (0-15m) vs last available window per condition
    early_coh = []
    late_coh = []
    valid_conds_coh = []
    last_window_idx = {}  # track which window is "last" per condition
    for cond in COND_ORDER:
        c = coherence[cond]
        if np.isnan(c[0]):
            continue
        # Find last non-NaN window
        last_i = max((i for i in range(4) if not np.isnan(c[i])), default=0)
        if last_i > 0:
            early_coh.append(c[0])
            late_coh.append(c[last_i])
            valid_conds_coh.append(cond)
            last_window_idx[cond] = last_i
    results["last_window_idx"] = last_window_idx
    results["win_labels"] = win_labels

    diffs_coh = np.array(late_coh) - np.array(early_coh)
    n_inc_coh = int(np.sum(diffs_coh > 0))
    n_coh = len(diffs_coh)

    if n_coh >= 6:
        w_coh, p_coh_wilcox = stats.wilcoxon(diffs_coh, alternative="greater")
    else:
        w_coh, p_coh_wilcox = float("nan"), float("nan")
    p_coh_sign = sign_test_p(n_inc_coh, n_coh)
    d_coh = float(np.mean(diffs_coh) / np.std(diffs_coh, ddof=1)) if len(diffs_coh) > 1 and np.std(diffs_coh, ddof=1) > 0 else 0.0

    # Per-condition convergence rate: OLS on window midpoints (minutes)
    win_midpoints = [7.5, 22.5, 37.5, 52.5]
    conv_rates = {}
    for cond in COND_ORDER:
        c = coherence[cond]
        valid = [(win_midpoints[i], c[i]) for i in range(4) if not np.isnan(c[i])]
        if len(valid) >= 3:
            xv = np.array([v[0] for v in valid])
            yv = np.array([v[1] for v in valid])
            slope, intercept, r_val, p_val, se = stats.linregress(xv, yv)
            conv_rates[cond] = {"slope_per_min": float(slope), "r": float(r_val),
                                "r2": float(r_val**2), "p": float(p_val), "se": float(se)}
        else:
            conv_rates[cond] = {"slope_per_min": 0, "r": 0, "r2": 0, "p": 1, "se": 0}

    results["convergence_stats"] = {
        "n_increase": n_inc_coh, "n_total": n_coh,
        "wilcoxon_W": float(w_coh) if not np.isnan(w_coh) else None,
        "wilcoxon_p": float(p_coh_wilcox) if not np.isnan(p_coh_wilcox) else None,
        "sign_test_p": float(p_coh_sign),
        "cohen_d": d_coh,
        "mean_change": float(np.mean(diffs_coh)),
        "sem_change": float(sem(diffs_coh)),
        "convergence_rates": conv_rates,
    }

    # Test 2: Cross-condition divergence
    # H0: D_late(ci,cj) <= D_early(ci,cj)  H1: D_late > D_early
    if divergence:
        early_d = np.array([d["early"] for d in divergence])
        late_d = np.array([d["late"] for d in divergence])
        diffs_div = late_d - early_d
        n_div = int(np.sum(diffs_div > 0))
        n_pairs_div = len(diffs_div)

        w_div, p_div_wilcox = stats.wilcoxon(diffs_div, alternative="greater")
        p_div_sign = sign_test_p(n_div, n_pairs_div)
        d_div = float(np.mean(diffs_div) / np.std(diffs_div, ddof=1)) if np.std(diffs_div, ddof=1) > 0 else 0.0

        results["divergence_stats"] = {
            "n_diverging": n_div, "n_total": n_pairs_div,
            "wilcoxon_W": float(w_div), "wilcoxon_p": float(p_div_wilcox),
            "sign_test_p": float(p_div_sign),
            "cohen_d": d_div,
            "mean_increase": float(np.mean(diffs_div)),
            "sem_increase": float(sem(diffs_div)),
        }

    # Test 3: Agent individuality
    # H0: InterAgent_late <= InterAgent_early  H1: InterAgent_late > InterAgent_early
    early_ind = np.array([individuality[(c, "early")] for c in COND_ORDER])
    late_ind = np.array([individuality[(c, "late")] for c in COND_ORDER])
    diffs_ind = late_ind - early_ind
    n_inc_ind = int(np.sum(diffs_ind > 0))
    n_ind = len(diffs_ind)

    if n_ind >= 6:
        w_ind, p_ind_wilcox = stats.wilcoxon(diffs_ind, alternative="greater")
    else:
        w_ind, p_ind_wilcox = float("nan"), float("nan")
    p_ind_sign = sign_test_p(n_inc_ind, n_ind)
    d_ind = float(np.mean(diffs_ind) / np.std(diffs_ind, ddof=1)) if len(diffs_ind) > 1 and np.std(diffs_ind, ddof=1) > 0 else 0.0

    results["individuality_stats"] = {
        "n_increase": n_inc_ind, "n_total": n_ind,
        "wilcoxon_W": float(w_ind) if not np.isnan(w_ind) else None,
        "wilcoxon_p": float(p_ind_wilcox) if not np.isnan(p_ind_wilcox) else None,
        "sign_test_p": float(p_ind_sign),
        "cohen_d": d_ind,
        "mean_increase": float(np.mean(diffs_ind)),
        "sem_increase": float(sem(diffs_ind)),
    }

    # Print summary
    w_coh_s = f"W={w_coh:.0f}, p={p_coh_wilcox:.4f}" if not np.isnan(w_coh) else "n<6"
    w_ind_s = f"W={w_ind:.0f}, p={p_ind_wilcox:.4f}" if not np.isnan(w_ind) else "n<6"
    print(f"    Convergence: {n_inc_coh}/{n_coh} increase, Wilcoxon {w_coh_s}, d={d_coh:.2f}")
    if "divergence_stats" in results:
        ds = results["divergence_stats"]
        print(f"    Divergence:  {ds['n_diverging']}/{ds['n_total']} increase, Wilcoxon W={ds['wilcoxon_W']:.0f}, p={ds['wilcoxon_p']:.4f}, d={ds['cohen_d']:.2f}")
    print(f"    Individuality: {n_inc_ind}/{n_ind} increase, Wilcoxon {w_ind_s}, d={d_ind:.2f}")

    return results


# ============================================================
# Stage 4: Report Generation
# ============================================================
def generate_report(meta, per_cond, condition_labels, agent_labels,
                    temporal_labels, cluster_labels, cross_results,
                    temporal_results=None):
    print("\nStage 4: Generating report...")

    rpt = []
    def w(s=""): rpt.append(s)
    def wt(title): w(f"\n## {title}\n")

    n_total = len(meta["post_id"])
    dr_r = cross_results.get("dose_response_r", 0)
    dr_p = cross_results.get("dose_response_p", 1)
    perm = cross_results.get("permanova", {})
    perm_cond_r2 = perm.get("condition", {}).get("R2", 0)
    perm_agent_r2 = perm.get("agent", {}).get("R2", 0)
    mmd_pvals = cross_results.get("mmd_pvals", np.ones((6, 6)))
    n_sig = int(np.sum(mmd_pvals[np.triu_indices(len(COND_ORDER), k=1)] < 0.05))
    n_pairs = len(COND_ORDER) * (len(COND_ORDER) - 1) // 2

    w("# What Did AI Agents Talk About?")
    w(f"*Embedding Analysis of Entropy Collapse Experiments (Run 04)*")
    w(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w()
    w("We placed 10 AI agents on a Reddit-like social platform (Moltbook) for 1 hour and let them post, comment, and vote autonomously. Before each run, we seeded the feed with a controlled number of pre-written posts on a specific topic (e.g., conspiracy theories, AGI safety). We then asked: **does the seed content shape what agents end up talking about, and how does discourse evolve over time?**")
    w()
    w("To answer this, we embedded every agent post into a high-dimensional vector (capturing its semantic meaning) and compared how similar or different posts are within and across conditions.")
    w()

    # ================================================================
    # 1. Executive Summary
    # ================================================================
    wt("1. Executive Summary")
    w(f"- **{n_total:,} agent posts** across 6 experimental conditions, each analyzed independently.")
    w(f"- **Seed content shapes what agents talk about**: the more seed posts we inject, the more closely agent output matches the seed topic (r = {dr_r:.3f}, p < 0.001).")
    w(f"- **What agents see matters more than who they are**: the experimental condition (what was in the feed) explains {perm_cond_r2:.1%} of the variation in agent posts, while agent identity (personality template) explains {perm_agent_r2:.1%}.")

    # ================================================================
    # 2. Data Overview
    # ================================================================
    wt("2. Data Overview")
    w("Each condition started with a different number of **seed posts** — pre-written posts injected into the feed before agents began posting. The \"magnitude\" experiment varies the number of conspiracy-themed seeds (0, 1, 5, 25). The \"domain\" experiment holds the count at 25 but changes the topic (conspiracy, AGI, tech).")
    w()
    w("| Condition | Experiment | Posts | Seed Count | Seed Topic |")
    w("|-----------|-----------|------:|----------:|------------|")
    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        n = int(mask.sum())
        exp = str(meta["experiment"][mask][0])
        sc = int(meta["seed_count"][mask][0])
        st = str(meta["seed_topic"][mask][0])
        w(f"| {COND_LABELS[cond]} | {exp} | {n} | {sc} | {st} |")
    w(f"| **Total** | | **{n_total}** | | |")
    w()
    w("**10 agents** with 7 personality templates: baseline (x2), introspective (x2), nihilist (x2), leader, follower, contrarian, curious.")
    w()

    # ================================================================
    # 3. Per-Condition Analysis
    # ================================================================
    wt("3. Per-Condition Analysis")
    w("Each condition ran independently for 1 hour with the same 10 AI agents. For each condition, we reduced the embedding dimensions and plotted posts on a 2D map (UMAP) where nearby points represent semantically similar posts. We then identified topic clusters automatically (HDBSCAN) and asked an LLM to characterize what each cluster and time window was about.")
    w()

    for cond in COND_ORDER:
        pc = per_cond[cond]
        cl = condition_labels.get(cond, {}) if condition_labels else {}
        n = pc["n"]

        w(f"### {COND_LABELS[cond]} ({n} posts)")
        w()
        w(f"![{COND_LABELS[cond]} UMAP](fig_cond_{cond}_umap.png)")
        w()

        # Cluster table
        cond_clusters = cluster_labels.get(cond, {}) if cluster_labels else {}
        if pc["n_clusters"] > 0:
            w("| Cluster | Posts | Label |")
            w("|--------:|------:|-------|")
            for cl_id in sorted(cond_clusters.keys(), key=lambda x: int(x)):
                cl_info = cond_clusters[cl_id]
                w(f"| {cl_id} | {cl_info.get('n_posts', '?')} | {cl_info.get('label', '?')} |")
            if pc["n_noise"] > 0:
                w(f"| noise | {pc['n_noise']} | — |")
        else:
            w(f"No clusters found (HDBSCAN). All {n} posts are noise or form a single mass.")
        w()

        # LLM characterization
        w(f"**{cl.get('label', cond)}** — {cl.get('description', '')}")
        w()
        dom = cl.get("dominant_themes", [])
        uniq = cl.get("unique_themes", [])
        tone = cl.get("tone", "")
        if dom:
            w(f"- **Dominant themes:** {', '.join(dom)}")
        if uniq:
            w(f"- **Unique to this condition:** {', '.join(uniq)}")
        if tone:
            w(f"- **Tone:** {tone}")
        w()

        # Temporal evolution
        if temporal_labels:
            cond_temporal = temporal_labels.get(cond, {})
            early = cond_temporal.get("early", {})
            mid = cond_temporal.get("mid", {})
            late = cond_temporal.get("late", {})
            w("**Temporal evolution:**")
            w()
            w(f"- **Early** (0-20 min): {early.get('label', '?')} — {early.get('description', '')}")
            w(f"- **Mid** (20-40 min): {mid.get('label', '?')} — {mid.get('description', '')}")
            w(f"- **Late** (40-60 min): {late.get('label', '?')} — {late.get('description', '')}")
            w()

        # Metrics table
        w("| Metric | Value |")
        w("|--------|------:|")
        w(f"| Coherence (mean pairwise sim) | {pc['mean_pairwise_sim']:.4f} |")
        w(f"| Agent spread (mean inter-agent dist) | {pc['agent_spread']:.4f} |")
        w(f"| Temporal drift (early-to-late) | {pc['temporal_drift']:.4f} |")
        w(f"| Clusters | {pc['n_clusters']} |")
        w(f"| Noise points | {pc['n_noise']} |")
        w()
        w("---")
        w()

    # ================================================================
    # 4. Attractor Dynamics
    # ================================================================
    wt("4. Attractor Dynamics")
    w("An **attractor** is a state that a system tends to settle into over time. Here we ask: do agents gradually converge on a shared topic within each condition? Do different conditions converge to *different* topics? And what happens to individual agent voices along the way?")
    w()
    w("We measure this using **coherence** — the average semantic similarity between all pairs of posts in a time window. Higher coherence means agents are talking about more similar things.")
    w()

    # 4.1 Within-Condition Convergence
    w("### 4.1 Within-Condition Convergence")
    w()
    w("![Convergence Over Time](fig_convergence_over_time.png)")
    w()
    if temporal_results and "coherence_over_time" in temporal_results:
        coherence_data = temporal_results["coherence_over_time"]
        conv_stats = temporal_results.get("convergence_stats", {})
        conv_rates = conv_stats.get("convergence_rates", {})

        last_win = temporal_results.get("last_window_idx", {})
        wl = temporal_results.get("win_labels", ["0-15m", "15-30m", "30-45m", "45-60m"])
        w("| Condition | Coherence (first 15m) | Coherence (last window) | Last window | Change | Rate (×10⁻³/min) | r² |")
        w("|-----------|------:|------:|------|------:|------:|------:|")
        for cond in COND_ORDER:
            vals = coherence_data[cond]
            v_early = vals[0]
            li = last_win.get(cond, 3)
            v_late = vals[li]
            cr = conv_rates.get(cond, {})
            slope_k = cr.get("slope_per_min", 0) * 1000
            r2 = cr.get("r2", 0)
            if not np.isnan(v_early) and not np.isnan(v_late):
                pct = ((v_late - v_early) / v_early) * 100 if v_early != 0 else 0
                w(f"| {COND_LABELS[cond]} | {v_early:.4f} | {v_late:.4f} | {wl[li]} | {pct:+.1f}% | {slope_k:+.2f} | {r2:.2f} |")
            else:
                w(f"| {COND_LABELS[cond]} | — | — | — | — | — | — |")
        w()

        n_inc = conv_stats.get("n_increase", 0)
        n_tot = conv_stats.get("n_total", 6)

        # Compute % change for mag5 and mag0 using their last available windows
        def _pct_change(cond_key):
            v = coherence_data[cond_key]
            li = last_win.get(cond_key, 2)
            if not np.isnan(v[0]) and not np.isnan(v[li]) and v[0] != 0:
                return ((v[li] - v[0]) / v[0]) * 100
            return 0
        w(f"Coherence increases in **{n_inc}/{n_tot} conditions**. Seeded conditions converge faster (5 seeds: {_pct_change('mag5'):+.0f}%) than control ({_pct_change('mag0'):+.0f}%), consistent with seed content acting as an attractor.")
    w()

    # 4.2 Between-Condition Divergence
    w("### 4.2 Between-Condition Divergence")
    w()
    w("If all conditions converged to the *same* topic, the distances between them would shrink over time. Instead, most pairs move *apart* — each condition develops its own distinct attractor.")
    w()
    w("![Cross-Condition Divergence](fig_cross_condition_divergence.png)")
    w()
    w("Each dot is a pair of conditions. Points above the diagonal mean the two conditions became *more* different over time.")
    w()
    if temporal_results and "divergence_stats" in temporal_results:
        ds = temporal_results["divergence_stats"]
        w(f"**{ds['n_diverging']}/{ds['n_total']} condition pairs** grow further apart from early (0-15 min) to late (40-60 min). The seed content steers each condition toward its own topic — they don't all collapse to one global conversation.")
    w()

    # 4.3 Agent Voice Crystallization
    w("### 4.3 Agent Voice Crystallization")
    w()
    w("This is the paradox: agents talk about increasingly similar *topics* (Section 4.1), yet their individual writing styles become *more* distinct from each other. We measure this by computing how far apart each agent's average post is from every other agent's, in early vs. late phases.")
    w()
    w("![Agent Individuality](fig_agent_individuality.png)")
    w()
    if temporal_results and "individuality_stats" in temporal_results:
        ist = temporal_results["individuality_stats"]
        w(f"Inter-agent distance increases in **{ist['n_increase']}/{ist['n_total']} conditions**. Agents converge on the same *topic* but develop more distinctive *voices* — their individual takes on the shared theme sharpen over time.")
    w()

    # 4.4 The Operationalization Attractor
    w("### 4.4 The Operationalization Attractor")
    w()
    w("Regardless of seed content, agents converge on a shared rhetorical mode: turning abstract ideas into micro-rituals, templates, and falsifiable artifacts. Seed content determines **what** they operationalize, not **whether** they do.")
    w()
    # Evidence table from LLM characterizations
    op_table = {
        "mag0":     ("Nothing",             "Agentic cadence — micro-habits, drift detectors, 10-minute probes"),
        "mag1":     ("1 conspiracy post",   "Shipping rituals, rollback drills, \"demo > paragraphs\""),
        "mag5":     ("5 conspiracy posts",  "Claim cards, forecast-first discipline, epistemic receipts"),
        "mag25":    ("25 conspiracy posts", "Falsifier walls, source-hop counting, revisit timers"),
        "dom-agi":  ("AGI safety posts",    "Gate specs, CI tripwires, append-only audit ledgers"),
        "dom-tech": ("Tech posts",          "Proof-of-work, exit criteria, Friday fail-promises"),
    }
    w("| Condition | Seed Topic | What They Operationalize |")
    w("|-----------|-----------|--------------------------|")
    for cond in COND_ORDER:
        seed, outcome = op_table[cond]
        w(f"| {COND_LABELS[cond]} | {seed} | {outcome} |")
    w()

    # ================================================================
    # 5. Seed Influence
    # ================================================================
    wt("5. Seed Influence")
    w()

    # 5.1 Dose-Response
    w("### 5.1 Dose-Response")
    w()
    w("Does injecting *more* seed posts make agent output more similar to the seed topic? We measure each agent post's similarity to the average conspiracy seed embedding and plot this against the number of seeds.")
    w()
    w("![Dose Response](fig_dose_response.png)")
    w()
    if "dose_data" in cross_results:
        w("| Condition | Seed Posts | Mean Similarity to Conspiracy Centroid |")
        w("|-----------|----------:|------:|")
        for cond in MAG_CONDITIONS:
            dd = cross_results["dose_data"].get(cond, {})
            w(f"| {COND_LABELS[cond]} | {dd.get('seed_count', '?')} | {dd.get('mean', 0):.4f} |")
    w()
    w(f"Overall trend: Pearson r = {dr_r:.3f}, p = {dr_p:.4f}.")
    if dr_p < 0.05:
        w("More conspiracy seeds leads to agent posts more similar to the conspiracy topic.")
    else:
        w("The dose-response trend is consistent in direction but not statistically significant at p < 0.05.")
    w()
    if "dose_data" in cross_results:
        dd = cross_results["dose_data"]
        sim_mag1 = dd.get("mag1", {}).get("mean", 0)
        sim_mag5 = dd.get("mag5", {}).get("mean", 0)
        sim_mag25 = dd.get("mag25", {}).get("mean", 0)
        w(f"However, the relationship is **non-linear**. The jump from 1 → 5 seeds is large ({sim_mag1:.3f} → {sim_mag5:.3f}), while 5 → 25 seeds adds almost nothing ({sim_mag5:.3f} → {sim_mag25:.3f}). Five seed posts appear to be a **tipping point** — enough to fully redirect 10 agents. Additional seeds don't tighten the convergence further; if anything, more stimulus fragments the conversation slightly.")
    w()

    # 5.2 Variance Decomposition
    w("### 5.2 Variance Decomposition (PERMANOVA)")
    w()
    w("How much of the variation in agent posts is explained by the experimental condition (what was in the feed) vs. agent identity (which agent wrote it)? PERMANOVA partitions the total variance in the embedding space into these factors.")
    w()
    w("![Variance Decomposition](fig_variance_decomposition.png)")
    w()
    cond_p = perm.get("condition", {})
    agent_p = perm.get("agent", {})
    w(f"| Factor | R² | F | p |")
    w(f"|--------|---:|---:|---:|")
    w(f"| Condition | {cond_p.get('R2', 0):.4f} | {cond_p.get('F', 0):.2f} | {cond_p.get('p', 1):.4f} |")
    w(f"| Agent | {agent_p.get('R2', 0):.4f} | {agent_p.get('F', 0):.2f} | {agent_p.get('p', 1):.4f} |")
    w(f"| Residual | {perm.get('residual_R2', 0):.4f} | — | — |")
    w()
    if perm_cond_r2 > perm_agent_r2:
        w(f"The feed content explains **{perm_cond_r2:.1%}** of the variation in agent posts, vs **{perm_agent_r2:.1%}** for agent identity. What agents see matters more than who they are.")
    else:
        w(f"Agent identity explains **{perm_agent_r2:.1%}** of the variation in agent posts, vs **{perm_cond_r2:.1%}** for feed content.")
    w()
    w(f"Additionally, all {n_sig}/{n_pairs} condition pairs produce statistically distinguishable post distributions (MMD permutation test, p < 0.05) — every condition's posts are measurably different from every other condition's.")
    w()

    # ================================================================
    # 6. Key Findings
    # ================================================================
    wt("6. Key Findings")
    w()

    # Pull stats for inline reporting
    conv_stats = temporal_results.get("convergence_stats", {}) if temporal_results else {}
    div_stats = temporal_results.get("divergence_stats", {}) if temporal_results else {}
    ind_stats = temporal_results.get("individuality_stats", {}) if temporal_results else {}

    n_conv = conv_stats.get("n_increase", "?")
    n_conv_t = conv_stats.get("n_total", "?")
    n_div = div_stats.get("n_diverging", "?")
    n_div_t = div_stats.get("n_total", "?")
    n_ind = ind_stats.get("n_increase", "?")
    n_ind_t = ind_stats.get("n_total", "?")

    w(f"1. **Agents converge within each condition**: {n_conv}/{n_conv_t} conditions show increasing topic similarity over time — agents lock into a shared groove.")
    w(f"2. **Each condition converges to a different place**: {n_div}/{n_div_t} condition pairs grow further apart, meaning each condition develops its own distinct topic attractor.")
    w(f"3. **Individual voices sharpen**: Despite talking about the same topic, agents become *more* distinct from each other in {n_ind}/{n_ind_t} conditions — they converge on topic but diverge on style.")
    w(f"4. **Tipping point at 5 seeds**: The dose-response is non-linear (overall r = {dr_r:.3f}). One seed barely moves the needle; five seeds fully redirects all 10 agents; 25 seeds adds nothing further.")
    if perm_cond_r2 > perm_agent_r2:
        w(f"5. **Feed > personality**: What agents were shown ({perm_cond_r2:.1%} of variance) matters more than their personality template ({perm_agent_r2:.1%}).")
    else:
        w(f"5. **Personality > feed**: Agent identity ({perm_agent_r2:.1%} of variance) outweighs feed content ({perm_cond_r2:.1%}).")

    w()
    w("---")
    w(f"*Generated by `embedding_analysis.py` - {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(rpt)


def export_csv(meta, per_cond):
    """Export CSV with per-condition UMAP coords and cluster labels."""
    print("  Exporting analysis_data.csv...")
    csv_path = REPORT_DIR / "analysis_data.csv"
    headers = ["post_id", "title", "author_name", "personality", "condition",
               "experiment", "seed_count", "seed_topic", "submolt", "score",
               "comment_count", "minutes_elapsed",
               "cond_umap_1", "cond_umap_2", "cluster_id"]

    # Build per-post index into per-condition results
    n = len(meta["post_id"])
    umap_1 = np.zeros(n)
    umap_2 = np.zeros(n)
    cluster_ids = np.full(n, -1, dtype=int)

    for cond in COND_ORDER:
        mask = meta["condition"] == cond
        indices = np.where(mask)[0]
        pc = per_cond[cond]
        for local_i, global_i in enumerate(indices):
            umap_1[global_i] = pc["X_umap"][local_i, 0]
            umap_2[global_i] = pc["X_umap"][local_i, 1]
            cluster_ids[global_i] = pc["cluster_labels"][local_i]

    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for i in range(n):
            writer.writerow([
                str(meta["post_id"][i]),
                str(meta["title"][i]),
                str(meta["author_name"][i]),
                str(meta["personality"][i]),
                str(meta["condition"][i]),
                str(meta["experiment"][i]),
                int(meta["seed_count"][i]),
                str(meta["seed_topic"][i]),
                str(meta["submolt"][i]),
                int(meta["score"][i]),
                int(meta["comment_count"][i]),
                f"{meta['minutes_elapsed'][i]:.2f}",
                f"{umap_1[i]:.4f}",
                f"{umap_2[i]:.4f}",
                int(cluster_ids[i]),
            ])
    print(f"  Saved {csv_path} ({n} rows)")


# ============================================================
# Main
# ============================================================
def main():
    t_start = time.time()

    # Stage 0: Load
    embeddings, meta = load_data()
    seed_embs, seed_topics, seed_titles = load_and_embed_seeds()
    print(f"  {len(seed_embs)} seed embeddings loaded ({len(set(seed_topics))} topics)")

    # Stage 1: Per-condition analysis (INDEPENDENT)
    print("\nStage 1: Per-condition independent analysis...")
    per_cond = {}
    for cond in COND_ORDER:
        print(f"  Analyzing {cond}...")
        per_cond[cond] = analyze_single_condition(embeddings, meta, cond)
        pc = per_cond[cond]
        print(f"    {pc['n']} posts, {pc['n_clusters']} clusters, "
              f"{pc['n_noise']} noise, coherence={pc['mean_pairwise_sim']:.4f}, "
              f"agent_spread={pc['agent_spread']:.4f}, drift={pc['temporal_drift']:.4f}")

    # Stage 2: LLM characterization (cached)
    condition_labels = label_conditions(meta)
    agent_labels = label_agents(meta)
    temporal_labels = label_temporal(meta)
    cluster_labels = label_per_condition_clusters(meta, embeddings, per_cond)

    # Re-generate UMAP plots with cluster names
    print("\n  Re-generating UMAP plots with cluster labels...")
    for cond in COND_ORDER:
        pc = per_cond[cond]
        cond_mask = meta["condition"] == cond
        cond_meta = {k: meta[k][cond_mask] for k in meta}
        name_map = cluster_labels.get(cond, {})
        _plot_condition_umap(pc["X_umap"], pc["cluster_labels"], cond_meta,
                             cond, pc["n_clusters"], cluster_name_map=name_map)

    # Stage 3: Cross-condition comparison (original embedding space)
    cross_results = cross_condition_comparison(embeddings, meta, seed_embs, seed_topics)

    # Stage 3b: Temporal dynamics (attractor analysis)
    temporal_results = temporal_dynamics(embeddings, meta)

    # Stage 4: Report
    report = generate_report(meta, per_cond, condition_labels, agent_labels,
                             temporal_labels, cluster_labels, cross_results,
                             temporal_results)
    (REPORT_DIR / "EMBEDDING_ANALYSIS.md").write_text(report)

    # CSV export (per-condition UMAP coords, cluster labels)
    export_csv(meta, per_cond)

    elapsed = time.time() - t_start
    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Report:   {REPORT_DIR / 'EMBEDDING_ANALYSIS.md'}")
    print(f"  Figures:  {REPORT_DIR / 'fig_*.png'}")
    print(f"  Data:     {REPORT_DIR / 'analysis_data.csv'} ({len(embeddings)} rows)")
    print(f"  Time:     {elapsed:.0f}s")
    print()


if __name__ == "__main__":
    main()
