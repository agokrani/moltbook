# Topic Convergence Analysis — Method Overview

## Research Question

When AI agents interact on a social network, their posts become increasingly similar over time ("entropy collapse"). **What topics do they converge toward, and how fast?**

## Data Pipeline

```
HuggingFace datasets (raw JSONL)
  → Qwen3-Embedding-8B (4096-dim vectors via OpenRouter)
    → Topic discovery + geometric diversity metrics
      → Plots + report
```

### Step 1: Experiment Data

AI agents run on MoltBook (a Reddit-like social network) for 1 hour under different conditions. Each run produces posts in JSONL format.

| Model | Agents | Conditions | HuggingFace repo |
|-------|--------|------------|-----------------|
| GPT-5 | 10, 20, 30 | 6 each | `Ayushnangia/moltbook-entropy-collapse-{experiments,20agents,30agents}` |
| Kimi K2.5 | 10 | 6 | `Ayushnangia/moltbook-entropy-collapse-kimi-k2.5` |
| GLM-5 | 10 | 6 | `Ayushnangia/moltbook-entropy-collapse-glm-5` |
| Gemini Flash Lite | 10, 20, 30 | 6 each | `Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite` |

The 6 conditions per model:

| Condition | Seed content |
|-----------|-------------|
| mag0 | Empty feed (control) |
| mag1 | 1 conspiracy post |
| mag5 | 5 conspiracy posts |
| mag25 | 25 conspiracy posts |
| dom-agi | 25 AGI hype posts |
| dom-tech | 25 tech humor posts |

### Step 2: Embedding

Every agent post is embedded using **Qwen3-Embedding-8B** (4096 dimensions) via the OpenRouter API. The embedding captures the semantic meaning of each post as a vector. Posts that discuss similar topics have vectors that point in similar directions (high cosine similarity).

Output: one `.npz` file per (model, scale) containing all post embeddings + metadata.

### Step 3: Topic Discovery (reference-based)

We discover topics **once** on a reference dataset (GPT-5 n20, the largest), then assign all other datasets to the same topics. This ensures consistent topic labels across scales and models.

1. **PCA(50)**: Reduce 4096-dim embeddings to 50 dimensions (captures ~55% of variance, removes noise)
2. **L2-normalize**: Make all vectors unit length so cosine similarity = dot product
3. **KMeans**: Cluster posts into K groups (K selected automatically via silhouette score, typically 3-7)
4. **LLM label**: For each cluster, sample 5 posts nearest the centroid, send to an LLM, get a one-word topic label (e.g., "identity", "safety", "habits")

For all other datasets: transform embeddings using the **same PCA model**, assign each post to the **nearest reference centroid**. Same topics, same colors, across all plots.

### Step 4: Three Layers of Analysis

**Layer 1 — Geometric convergence** (no labels needed, pure math):

| Metric | What it measures | Citation |
|--------|-----------------|----------|
| Vendi Score | "How many effectively distinct posts exist?" Drops = convergence | Friedman & Dieng, TMLR 2023 (`vendi-score` v0.0.3) |
| TwoNN intrinsic dimensionality | "How many semantic dimensions do posts span?" Drops = compression | Facco et al., Sci. Rep. 2017 (`scikit-dimension` v0.3.4) |
| JSD | "How much did the distribution shift between time bins?" | Jensen-Shannon divergence via `scipy` |

These metrics are computed per (condition, 15-minute time bin).

**Layer 2 — Topic tracking:**

- Topic proportions per time bin → stacked area chart (shows *what* agents converge toward)
- Topic entropy H(t) = −Σ pᵢ log₂ pᵢ → declining entropy = fewer topics dominating

**Layer 3 — Statistical comparison:**

- Cliff's delta effect sizes: each condition vs. control (mag0)
- Thresholds: |δ| < 0.11 negligible, < 0.28 small, < 0.43 medium, ≥ 0.43 large

### Step 5: Visualization

| Plot | What it shows |
|------|--------------|
| `geometric_{scale}.png` | Vendi Score, intrinsic dim, JSD over time (one line per condition) |
| `topics_{scale}.png` | Stacked area: topic proportions per condition over time |
| `entropy_{scale}.png` | Topic entropy decline curves (steeper = faster convergence) |
| `mds_topics_{scale}.png` | 2D map of all posts colored by topic (MDS on cosine distances) |
| `mds_temporal_{scale}.png` | Same 2D map colored by time (blue=early, red=late) |

## Reproducibility

- **Embeddings**: Qwen3-Embedding-8B via OpenRouter (deterministic at temperature=0)
- **Clustering**: KMeans with `random_state=42`, `n_init=10`
- **PCA**: `random_state=42`
- **MDS**: `random_state=42`, `n_init=4`
- **LLM labels**: Cached to JSON; re-running uses cache

## Running the Analysis

```bash
# GPT-5 across all scales (n20 as reference for topic discovery):
python3 scripts/analysis_new/topic_convergence.py \
  --scales n10,n20,n30 --reference n20

# Gemini Flash Lite (using GPT-5 n20 reference topics):
python3 scripts/analysis_new/topic_convergence.py \
  --scales gemini_n10,gemini_n20,gemini_n30 --reference n20 \
  --out-dir findings/entropy-collapse-scaling/topic_convergence_gemini

# Without LLM labels (offline testing):
python3 scripts/analysis_new/topic_convergence.py --scales n20 --skip-llm
```
