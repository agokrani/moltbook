#!/usr/bin/env python3
"""Embedding word-anchor analysis for entropy-collapse scaling.

Unlike embedding_topic_anchors.py which builds anchors as centroids of
lexicon-matching posts, this script embeds the anchor words/phrases
themselves using the same model (qwen/qwen3-embedding-8b) and measures
cosine distance from each post to these fixed semantic reference points.

This gives anchors that are independent of the post distribution —
a post about "evidence" will be near the Evidence anchor regardless of
whether other posts in the corpus mention evidence-related keywords.

Outputs:
  - word_anchor_assignments.csv
  - word_anchor_run_summary.csv
  - word_anchor_bin_shares.csv
  - word_anchor_family_heatmap.png
  - word_anchor_late_heatmap.png
  - word_anchor_dominant_share.png
  - word_anchor_cluster_grid.png
  - word_anchor_family_cluster_grid.png
  - word_anchor_late_cluster_grid.png
  - word_anchor_centroids_pca.png
  - word_anchor_summary.json
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time as time_module
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests

from load_entropy_data import CONDITION_LABELS, CONDITION_ORDER, load_all_scales, group_records
from time_binned_lexical_metrics_5gram import ngram_counter, prepare_posts
from phrase_template_topics import (
    CATEGORY_LABELS,
    CATEGORY_LEXICONS,
    COND_COLORS,
    NGRAM_SIZE,
    TOP_K,
    overlap_graph_components,
    phrase_hits,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OUT_DIR = Path("findings/entropy-collapse-scaling/embedding_bridge")
ANCHOR_CACHE = OUT_DIR / "word_anchor_embeddings.npz"
SCALES = ["n10", "n20", "n30"]
BIN_EDGES = [0.0, 15.0, 30.0, 45.0, 60.0]

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
EMBED_MODEL = "qwen/qwen3-embedding-8b"
EMBED_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"

# ---------------------------------------------------------------------------
# Anchor definitions
#
# Each anchor is a short phrase that gets embedded directly.  The embedding
# of this phrase becomes the fixed reference point in the semantic space.
# ---------------------------------------------------------------------------

ANCHOR_PHRASES = {
    "evidence":  "Evidence: proof, receipts, sources, primary links, artifacts, traces",
    "testing":   "Testing: checks, probes, falsifiable predictions, disconfirming deltas, reviews",
    "ownership": "Ownership: decision scope, stakes, approvals, paths, accountability",
    "time":      "Time: dates, deadlines, cadence, scheduling, next steps, review cycles",
    "risk":      "Risk: rollback, failure modes, tripwires, alerts, drills, ramps",
}

ANCHOR_LABELS = {
    "evidence": "Evidence",
    "testing": "Testing",
    "ownership": "Ownership",
    "time": "Time",
    "risk": "Risk",
}

TOPIC_ORDER = list(ANCHOR_PHRASES.keys())
TOPIC_COLORS = {
    "evidence": "#2563EB",
    "testing": "#D97706",
    "ownership": "#059669",
    "time": "#7C3AED",
    "risk": "#DC2626",
}
ANCHOR_LAYOUT = {
    "evidence": (-0.85, 0.55),
    "testing": (-0.85, -0.45),
    "time": (0.0, 0.95),
    "ownership": (0.85, 0.45),
    "risk": (0.85, -0.55),
}
ANCHOR_POLYGON_ORDER = ["evidence", "time", "ownership", "risk", "testing", "evidence"]
ANCHOR_SOFTMAX_TEMP = 0.01
SCALE_ORDER = {scale: idx for idx, scale in enumerate(SCALES)}
COND_ORDER = {cond: idx for idx, cond in enumerate(CONDITION_ORDER)}
SCALE_MARKERS = {"n10": "^", "n20": "o", "n30": "s"}

# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Call the OpenRouter embeddings API."""
    response = requests.post(
        EMBED_ENDPOINT,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": EMBED_MODEL, "input": texts},
        timeout=120,
    )
    response.raise_for_status()
    payload = response.json()
    items = sorted(payload["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in items]


def load_or_create_anchor_embeddings() -> dict[str, np.ndarray]:
    """Load cached anchor embeddings or generate them via the API."""
    if ANCHOR_CACHE.exists():
        data = np.load(ANCHOR_CACHE, allow_pickle=True)
        anchors = {}
        for topic in TOPIC_ORDER:
            if topic in data:
                anchors[topic] = normalize(data[topic])
        if set(anchors.keys()) == set(TOPIC_ORDER):
            print(f"Loaded cached anchor embeddings from {ANCHOR_CACHE}")
            return anchors
        print("Cached anchors incomplete, regenerating...")

    if not OPENROUTER_KEY:
        raise RuntimeError(
            "OPENROUTER_API_KEY is not set and no cached anchor embeddings found.\n"
            f"Expected cache at: {ANCHOR_CACHE}"
        )

    print(f"Embedding {len(ANCHOR_PHRASES)} anchor phrases with {EMBED_MODEL}...")
    topics = list(ANCHOR_PHRASES.keys())
    texts = [ANCHOR_PHRASES[topic] for topic in topics]
    vectors = embed_texts(texts)

    anchors = {}
    save_kwargs = {}
    for topic, vector in zip(topics, vectors):
        arr = normalize(np.asarray(vector, dtype=np.float32))
        anchors[topic] = arr
        save_kwargs[topic] = arr

    ANCHOR_CACHE.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ANCHOR_CACHE, **save_kwargs)
    print(f"Cached anchor embeddings to {ANCHOR_CACHE}")
    return anchors


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def load_embeddings(scale: str) -> dict[str, np.ndarray]:
    data = np.load(Path(f"embeddings_{scale}.npz"), allow_pickle=True)
    ids = data["post_id"]
    embs = data["embeddings"]
    return {str(pid): embs[idx] for idx, pid in enumerate(ids)}


def bin_index(minutes_elapsed: float) -> int | None:
    for idx in range(len(BIN_EDGES) - 1):
        if BIN_EDGES[idx] <= minutes_elapsed < BIN_EDGES[idx + 1]:
            return idx
    return None


def topic_scores(vector: np.ndarray, anchors: dict[str, np.ndarray]) -> dict[str, float]:
    return {topic: float(np.dot(vector, anchor)) for topic, anchor in anchors.items()}


def anchor_pull_weights(score_map: dict[str, float], temperature: float = ANCHOR_SOFTMAX_TEMP) -> dict[str, float]:
    max_score = max(score_map[topic] for topic in TOPIC_ORDER)
    exps = {
        topic: float(np.exp((score_map[topic] - max_score) / temperature))
        for topic in TOPIC_ORDER
    }
    total = sum(exps.values())
    return {topic: exps[topic] / total for topic in TOPIC_ORDER}


def anchor_pull_coord(score_map: dict[str, float]) -> tuple[float, float]:
    weights = anchor_pull_weights(score_map)
    x_val = sum(weights[topic] * ANCHOR_LAYOUT[topic][0] for topic in TOPIC_ORDER)
    y_val = sum(weights[topic] * ANCHOR_LAYOUT[topic][1] for topic in TOPIC_ORDER)
    return x_val, y_val


# ---------------------------------------------------------------------------
# Phrase family detection (same as original)
# ---------------------------------------------------------------------------


def detect_phrase_family(run_prepared) -> tuple[list[str], list[str], set[str]]:
    top_ngrams = [" ".join(gram) for gram, _ in ngram_counter(run_prepared, NGRAM_SIZE).most_common(TOP_K)]
    if not top_ngrams:
        return [], [], set()
    components = overlap_graph_components(top_ngrams, min_overlap=NGRAM_SIZE - 1)
    chosen_family = None
    chosen_posts = []
    for component in components:
        component_set = set(component)
        component_posts = [post for post in run_prepared if phrase_hits(post, component_set) > 0]
        if chosen_family is None or len(component_posts) > len(chosen_posts):
            chosen_family = component
            chosen_posts = component_posts
    family_phrases = chosen_family or top_ngrams[:1]
    return top_ngrams, family_phrases, set(family_phrases)


# ---------------------------------------------------------------------------
# Summarization
# ---------------------------------------------------------------------------


def ordered_run_items(by_run: dict[tuple, list]) -> list[tuple[tuple, list]]:
    return sorted(
        by_run.items(),
        key=lambda item: (
            SCALE_ORDER.get(item[0][0], 99),
            COND_ORDER.get(item[0][1], 99),
            item[0][2],
        ),
    )


def run_label(scale: str, condition: str) -> str:
    return f"{scale[1:]}a {CONDITION_LABELS.get(condition, condition)}"


def format_topic_label(topic: str | None) -> str:
    if topic is None:
        return "No topic"
    return ANCHOR_LABELS.get(topic, topic)


def summarize_assignment_rows(rows: list[dict]) -> dict:
    total = len(rows)
    shares = {topic: 0.0 for topic in TOPIC_ORDER}
    if total == 0:
        return {
            "n_posts": 0,
            "dominant_topic": None,
            "dominant_share": 0.0,
            "concentration_hhi": 0.0,
            "mean_top_similarity": None,
            "shares": shares,
        }
    counts = Counter(row["top_topic"] for row in rows)
    shares = {topic: counts.get(topic, 0) / total for topic in TOPIC_ORDER}
    dominant_topic = max(TOPIC_ORDER, key=lambda topic: shares[topic])
    top_sims = [row["top_similarity"] for row in rows]
    return {
        "n_posts": total,
        "dominant_topic": dominant_topic,
        "dominant_share": shares[dominant_topic],
        "concentration_hhi": sum(value * value for value in shares.values()),
        "mean_top_similarity": float(np.mean(top_sims)) if top_sims else None,
        "shares": shares,
    }


def pca_2d(matrix: np.ndarray) -> np.ndarray:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    return centered @ vt[:2].T


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def ordered_heatmap_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda row: (
            SCALE_ORDER.get(row["scale"], 99),
            COND_ORDER.get(row["condition"], 99),
            row["run_name"],
        ),
    )


# ---------------------------------------------------------------------------
# Plotting (same structure, prefixed filenames)
# ---------------------------------------------------------------------------


def plot_share_heatmap(rows: list[dict], out_name: str, title: str, subtitle: str) -> None:
    ordered = ordered_heatmap_rows(rows)
    labels = [row["label"] for row in ordered]
    data = np.array([[row[f"share_{topic}"] for topic in TOPIC_ORDER] for row in ordered], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0.0, vmax=max(0.6, float(np.max(data))))

    ax.set_xticks(range(len(TOPIC_ORDER)))
    ax.set_xticklabels([ANCHOR_LABELS[topic] for topic in TOPIC_ORDER], rotation=0)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)

    for yi in range(data.shape[0]):
        for xi in range(data.shape[1]):
            value = data[yi, xi]
            text_color = "white" if value >= 0.38 else "#111827"
            ax.text(xi, yi, f"{value:.2f}", ha="center", va="center", fontsize=9, color=text_color)

    for yi, row in enumerate(ordered):
        ax.get_yticklabels()[yi].set_color(COND_COLORS.get(row["condition"], "#6B7280"))

    fig.colorbar(im, ax=ax, shrink=0.9, label="Share of posts nearest to anchor")
    ax.set_title(title, fontsize=15, fontweight="bold")
    fig.text(0.5, 0.96, subtitle, ha="center", fontsize=10, color="#4B5563")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / out_name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_dominant_share(run_rows: list[dict]) -> None:
    ordered = ordered_heatmap_rows(run_rows)
    y = np.arange(len(ordered))
    all_vals = [row["all_dominant_share"] for row in ordered]
    family_vals = [row["family_dominant_share"] for row in ordered]
    family_topics = [row["family_dominant_topic"] for row in ordered]
    labels = [f"{row['label']} [{format_topic_label(row['family_dominant_topic'])}]" for row in ordered]

    fig_height = max(7.5, 0.48 * len(ordered) + 2.2)
    fig, ax = plt.subplots(figsize=(11, fig_height))
    ax.barh(y - 0.18, all_vals, height=0.32, color="#D1D5DB", label="All posts")
    ax.barh(
        y + 0.18,
        family_vals,
        height=0.32,
        color=[TOPIC_COLORS.get(topic, "#9CA3AF") for topic in family_topics],
        label="Phrase-family posts",
    )

    for idx, row in enumerate(ordered):
        ax.text(family_vals[idx] + 0.01, y[idx] + 0.18, f"{family_vals[idx]:.2f}", va="center", fontsize=9, color="#111827")
        ax.text(all_vals[idx] + 0.01, y[idx] - 0.18, f"{all_vals[idx]:.2f}", va="center", fontsize=9, color="#4B5563")

    ax.set_xlim(0, 1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Share of posts nearest to the run's dominant word anchor")
    ax.set_title(
        "Phrase-family concentration (word-embedded anchors)",
        fontsize=15,
        fontweight="bold",
    )
    ax.grid(axis="x", alpha=0.15)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color="#D1D5DB", label="All posts"),
        plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="#111827", linewidth=1.2, label="Phrase-family posts"),
    ]
    topic_handles = [
        plt.Line2D([0], [0], marker="s", linestyle="", markersize=8, color=TOPIC_COLORS[topic], label=ANCHOR_LABELS[topic])
        for topic in TOPIC_ORDER
    ]
    legend_a = ax.legend(handles=handles, loc="upper right", frameon=False)
    ax.add_artist(legend_a)
    ax.legend(handles=topic_handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.12))

    fig.tight_layout()
    fig.savefig(OUT_DIR / "word_anchor_dominant_share.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def setup_anchor_axes(ax) -> None:
    polygon = np.array([ANCHOR_LAYOUT[topic] for topic in ANCHOR_POLYGON_ORDER], dtype=float)
    ax.plot(polygon[:, 0], polygon[:, 1], linestyle="--", linewidth=0.8, color="#E5E7EB", zorder=1)
    for topic in TOPIC_ORDER:
        x_val, y_val = ANCHOR_LAYOUT[topic]
        ax.scatter(x_val, y_val, marker="X", s=85, c=TOPIC_COLORS[topic], edgecolors="white", linewidths=0.7, zorder=5)
    ax.set_xlim(-1.05, 1.05)
    ax.set_ylim(-0.85, 1.08)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def plot_anchor_cluster_grid(assignment_rows: list[dict], run_summary_rows: list[dict], mode: str) -> None:
    by_run = group_records(
        assignment_rows,
        lambda row: (row["scale"], row["condition"], row["run_name"]),
    )
    summary_lookup = {
        (row["scale"], row["condition"], row["run_name"]): row for row in run_summary_rows
    }

    fig_height = 3.0 * len(SCALES) + 2.0
    fig, axes = plt.subplots(len(SCALES), len(CONDITION_ORDER), figsize=(22, fig_height), sharex=True, sharey=True)
    fig.patch.set_facecolor("white")

    for row_idx, scale in enumerate(SCALES):
        for col_idx, condition in enumerate(CONDITION_ORDER):
            ax = axes[row_idx, col_idx]
            run_key = next((key for key in by_run if key[0] == scale and key[1] == condition), None)
            if run_key is None:
                ax.set_visible(False)
                continue

            rows = by_run[run_key]
            summary = summary_lookup[run_key]
            setup_anchor_axes(ax)

            if mode == "all":
                for topic in TOPIC_ORDER:
                    topic_rows = [row for row in rows if row["top_topic"] == topic]
                    if not topic_rows:
                        continue
                    ax.scatter(
                        [row["anchor_x"] for row in topic_rows],
                        [row["anchor_y"] for row in topic_rows],
                        s=16, c=TOPIC_COLORS[topic], alpha=0.88, edgecolors="white", linewidths=0.2, zorder=2,
                    )
                note = (
                    f"{ANCHOR_LABELS[summary['all_dominant_topic']]} {summary['all_dominant_share']:.2f}\n"
                    f"n={summary['n_posts']}"
                )
            elif mode == "family":
                other_rows = [row for row in rows if row["in_family"] == 0]
                family_rows = [row for row in rows if row["in_family"] == 1]
                if other_rows:
                    ax.scatter(
                        [row["anchor_x"] for row in other_rows],
                        [row["anchor_y"] for row in other_rows],
                        s=7, c="#BFC7D1", alpha=0.18, edgecolors="none", zorder=2,
                    )
                for topic in TOPIC_ORDER:
                    topic_rows = [row for row in family_rows if row["top_topic"] == topic]
                    if not topic_rows:
                        continue
                    ax.scatter(
                        [row["anchor_x"] for row in topic_rows],
                        [row["anchor_y"] for row in topic_rows],
                        s=16, c=TOPIC_COLORS[topic], alpha=0.88, edgecolors="white", linewidths=0.2, zorder=4,
                    )
                note = (
                    f"family: {format_topic_label(summary['family_dominant_topic'])} "
                    f"{summary['family_dominant_share']:.2f}\n"
                    f"n={summary['n_family_posts']}"
                )
            elif mode == "late":
                late_rows = [row for row in rows if row["bin_idx"] == len(BIN_EDGES) - 2]
                for topic in TOPIC_ORDER:
                    topic_rows = [row for row in late_rows if row["top_topic"] == topic]
                    if not topic_rows:
                        continue
                    ax.scatter(
                        [row["anchor_x"] for row in topic_rows],
                        [row["anchor_y"] for row in topic_rows],
                        s=10, c=TOPIC_COLORS[topic], alpha=0.26, edgecolors="none", zorder=3,
                    )
                late_family_rows = [row for row in late_rows if row["in_family"] == 1]
                if late_family_rows:
                    ax.scatter(
                        [row["anchor_x"] for row in late_family_rows],
                        [row["anchor_y"] for row in late_family_rows],
                        s=18, facecolors="none", edgecolors="#111827", linewidths=0.45, alpha=0.9, zorder=4,
                    )
                note = (
                    f"late: {format_topic_label(summary['late_dominant_topic'])} "
                    f"{summary['late_dominant_share']:.2f}"
                )
            else:
                raise ValueError(f"Unknown mode: {mode}")

            ax.text(
                0.03, 0.04, note, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=8.5, color="#111827",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 1.5},
            )
            if row_idx == 0:
                ax.set_title(CONDITION_LABELS.get(condition, condition), fontsize=11, fontweight="bold", color=COND_COLORS.get(condition, "#111827"))
            if col_idx == 0:
                ax.set_ylabel(f"{scale[1:]} agents", fontsize=11, fontweight="bold")

    topic_handles = [
        plt.Line2D([0], [0], marker="o", linestyle="", markersize=7, color=TOPIC_COLORS[topic], label=ANCHOR_LABELS[topic])
        for topic in TOPIC_ORDER
    ]
    anchor_handle = plt.Line2D([0], [0], marker="X", linestyle="", markersize=9, color="#374151", label="Word anchor")

    if mode == "all":
        title = "All posts cluster near word-embedded topic anchors"
        subtitle = "Every post colored by its nearest anchor. Anchors are embeddings of topic phrases, not post centroids."
        out_name = "word_anchor_cluster_grid.png"
        legend_handles = topic_handles + [anchor_handle]
    elif mode == "family":
        title = "Repeated-phrase posts cluster near word-embedded anchors"
        subtitle = "Grey = rest of run. Colored = posts containing the dominant phrase family."
        out_name = "word_anchor_family_cluster_grid.png"
        legend_handles = topic_handles + [anchor_handle]
    else:
        title = "Late-run posts near word-embedded topic anchors"
        subtitle = "Anchors are embeddings of topic phrases, not post centroids. Black outlines = late phrase-family posts."
        out_name = "word_anchor_late_cluster_grid.png"
        outline_handle = plt.Line2D(
            [0], [0], marker="o", linestyle="", markersize=7,
            markerfacecolor="white", markeredgecolor="#111827", markeredgewidth=1.0, label="Phrase-family posts",
        )
        legend_handles = topic_handles + [outline_handle, anchor_handle]

    fig.suptitle(title, fontsize=18, fontweight="bold", y=0.98)
    fig.text(0.5, 0.94, subtitle, ha="center", fontsize=10, color="#4B5563")
    fig.legend(handles=legend_handles, loc="lower center", ncol=min(len(legend_handles), 7), frameon=False, bbox_to_anchor=(0.5, -0.01))
    fig.tight_layout(rect=[0, 0.05, 1, 0.90])
    fig.savefig(OUT_DIR / out_name, dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_centroids_pca(late_centroid_rows: list[dict], anchors: dict[str, np.ndarray]) -> None:
    anchor_topics = [topic for topic in TOPIC_ORDER if topic in anchors]
    point_vectors = [anchors[topic] for topic in anchor_topics] + [row["vector"] for row in late_centroid_rows]
    coords = pca_2d(np.asarray(point_vectors))

    fig, ax = plt.subplots(figsize=(9, 7))

    for idx, topic in enumerate(anchor_topics):
        x_val, y_val = coords[idx]
        ax.scatter(x_val, y_val, s=180, marker="X", c=TOPIC_COLORS[topic], edgecolors="white", linewidths=0.8, zorder=4)
        ax.text(x_val + 0.02, y_val + 0.02, ANCHOR_LABELS[topic], fontsize=10, fontweight="bold", color=TOPIC_COLORS[topic])

    offset = len(anchor_topics)
    for idx, row in enumerate(late_centroid_rows):
        x_val, y_val = coords[offset + idx]
        ax.scatter(
            x_val, y_val, s=90,
            c=COND_COLORS.get(row["condition"], "#6B7280"),
            marker=SCALE_MARKERS.get(row["scale"], "o"),
            edgecolors="white", linewidths=0.8, alpha=0.95, zorder=3,
        )
        ax.text(x_val + 0.015, y_val - 0.015, row["short_label"], fontsize=8, color="#111827")

    cond_handles = [
        plt.Line2D(
            [0], [0], marker="o", linestyle="",
            markerfacecolor=COND_COLORS[cond], markeredgecolor="white", markeredgewidth=0.6,
            markersize=8, label=CONDITION_LABELS.get(cond, cond),
        )
        for cond in CONDITION_ORDER
    ]
    scale_handles = [
        plt.Line2D([0], [0], marker=SCALE_MARKERS[scale], linestyle="", color="#374151", markersize=8, label=f"{scale[1:]} agents")
        for scale in SCALES
    ]
    legend_a = ax.legend(handles=cond_handles, loc="upper left", frameon=False, fontsize=9)
    ax.add_artist(legend_a)
    ax.legend(handles=scale_handles, loc="upper right", frameon=False, fontsize=9)

    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("Late-run centroids vs word-embedded anchors (PCA)", fontsize=15, fontweight="bold")
    fig.text(0.5, 0.96, "PCA for display only. Assignment uses cosine similarity in the full embedding space.", ha="center", fontsize=10, color="#4B5563")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "word_anchor_centroids_pca.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Load anchor embeddings (from cache or API)
    anchors = load_or_create_anchor_embeddings()

    # 2. Load post data and embeddings
    records = [record for record in load_all_scales(include_scales=SCALES) if not record.is_seed]
    prepared_posts = prepare_posts(records)
    prepared_by_id = {post.record.post_id: post for post in prepared_posts}

    emb_map = {}
    for scale in SCALES:
        emb_map.update(load_embeddings(scale))
    norm_emb_map = {post_id: normalize(vector) for post_id, vector in emb_map.items()}

    by_run = group_records(records, lambda r: (r.scale, r.condition, r.run_name))

    # 3. Assign posts to nearest word anchor
    assignment_rows = []
    run_summary_rows = []
    bin_rows = []
    family_heatmap_rows = []
    late_heatmap_rows = []
    late_centroid_rows = []

    for (scale, condition, run_name), run_records in ordered_run_items(by_run):
        run_prepared = [prepared_by_id[record.post_id] for record in run_records if record.post_id in prepared_by_id]
        _, family_phrases, family_set = detect_phrase_family(run_prepared)
        family_ids = {
            post.record.post_id
            for post in run_prepared
            if family_set and phrase_hits(post, family_set) > 0 and post.record.post_id in norm_emb_map
        }

        run_assignments = []
        for record in run_records:
            post_id = record.post_id
            if post_id not in norm_emb_map:
                continue
            sim = topic_scores(norm_emb_map[post_id], anchors)
            top_topic = max(TOPIC_ORDER, key=lambda topic: sim[topic])
            top_similarity = sim[top_topic]
            coord_x, coord_y = anchor_pull_coord(sim)
            row = {
                "scale": scale,
                "condition": condition,
                "run_name": run_name,
                "post_id": post_id,
                "author_name": record.author_name,
                "minutes_elapsed": round(record.minutes_elapsed, 3),
                "bin_idx": bin_index(record.minutes_elapsed),
                "in_family": int(post_id in family_ids),
                "top_topic": top_topic,
                "top_similarity": round(top_similarity, 6),
                "anchor_x": round(coord_x, 6),
                "anchor_y": round(coord_y, 6),
            }
            for topic in TOPIC_ORDER:
                row[f"sim_{topic}"] = round(sim[topic], 6)
            run_assignments.append(row)
            assignment_rows.append(row)

        all_summary = summarize_assignment_rows(run_assignments)
        family_assignments = [row for row in run_assignments if row["in_family"] == 1]
        other_assignments = [row for row in run_assignments if row["in_family"] == 0]
        family_summary = summarize_assignment_rows(family_assignments)
        other_summary = summarize_assignment_rows(other_assignments)
        late_assignments = [row for row in run_assignments if row["bin_idx"] == len(BIN_EDGES) - 2]
        late_summary = summarize_assignment_rows(late_assignments)

        label = run_label(scale, condition)
        family_topic = family_summary["dominant_topic"] or all_summary["dominant_topic"]
        run_row = {
            "scale": scale,
            "condition": condition,
            "condition_label": CONDITION_LABELS.get(condition, condition),
            "run_name": run_name,
            "label": label,
            "n_posts": all_summary["n_posts"],
            "n_family_posts": family_summary["n_posts"],
            "n_other_posts": other_summary["n_posts"],
            "family_phrases": " | ".join(family_phrases),
            "all_dominant_topic": all_summary["dominant_topic"],
            "all_dominant_share": round(all_summary["dominant_share"], 6),
            "all_concentration_hhi": round(all_summary["concentration_hhi"], 6),
            "family_dominant_topic": family_topic,
            "family_dominant_share": round(family_summary["dominant_share"], 6),
            "family_concentration_hhi": round(family_summary["concentration_hhi"], 6),
            "other_dominant_topic": other_summary["dominant_topic"],
            "other_dominant_share": round(other_summary["dominant_share"], 6),
            "other_concentration_hhi": round(other_summary["concentration_hhi"], 6),
            "late_dominant_topic": late_summary["dominant_topic"],
            "late_dominant_share": round(late_summary["dominant_share"], 6),
            "late_concentration_hhi": round(late_summary["concentration_hhi"], 6),
            "family_minus_all_dominant_share": round(
                family_summary["dominant_share"] - all_summary["dominant_share"], 6
            ),
        }
        for topic in TOPIC_ORDER:
            run_row[f"all_share_{topic}"] = round(all_summary["shares"][topic], 6)
            run_row[f"family_share_{topic}"] = round(family_summary["shares"][topic], 6)
            run_row[f"late_share_{topic}"] = round(late_summary["shares"][topic], 6)
        run_summary_rows.append(run_row)

        family_heatmap_rows.append({
            "scale": scale, "condition": condition, "run_name": run_name, "label": label,
            **{f"share_{topic}": round(family_summary["shares"][topic], 6) for topic in TOPIC_ORDER},
        })
        late_heatmap_rows.append({
            "scale": scale, "condition": condition, "run_name": run_name, "label": label,
            **{f"share_{topic}": round(late_summary["shares"][topic], 6) for topic in TOPIC_ORDER},
        })

        for bin_idx_value in range(len(BIN_EDGES) - 1):
            bin_assignments = [row for row in run_assignments if row["bin_idx"] == bin_idx_value]
            bin_summary = summarize_assignment_rows(bin_assignments)
            bin_row = {
                "scale": scale, "condition": condition, "run_name": run_name, "label": label,
                "bin_idx": bin_idx_value,
                "bin_start": BIN_EDGES[bin_idx_value],
                "bin_end": BIN_EDGES[bin_idx_value + 1],
                "n_posts": bin_summary["n_posts"],
                "dominant_topic": bin_summary["dominant_topic"],
                "dominant_share": round(bin_summary["dominant_share"], 6),
                "concentration_hhi": round(bin_summary["concentration_hhi"], 6),
            }
            for topic in TOPIC_ORDER:
                bin_row[f"share_{topic}"] = round(bin_summary["shares"][topic], 6)
            bin_rows.append(bin_row)

        late_vectors = [norm_emb_map[row["post_id"]] for row in late_assignments]
        if late_vectors:
            late_centroid_rows.append({
                "scale": scale, "condition": condition, "run_name": run_name,
                "short_label": f"{scale[1:]}-{condition}",
                "vector": normalize(np.mean(np.asarray(late_vectors), axis=0)),
            })

    # 4. Write CSVs
    assignment_fieldnames = [
        "scale", "condition", "run_name", "post_id", "author_name",
        "minutes_elapsed", "bin_idx", "in_family", "top_topic", "top_similarity",
        "anchor_x", "anchor_y",
        *[f"sim_{topic}" for topic in TOPIC_ORDER],
    ]
    write_csv(OUT_DIR / "word_anchor_assignments.csv", assignment_rows, assignment_fieldnames)

    run_fieldnames = [
        "scale", "condition", "condition_label", "run_name", "label",
        "n_posts", "n_family_posts", "n_other_posts", "family_phrases",
        "all_dominant_topic", "all_dominant_share", "all_concentration_hhi",
        "family_dominant_topic", "family_dominant_share", "family_concentration_hhi",
        "other_dominant_topic", "other_dominant_share", "other_concentration_hhi",
        "late_dominant_topic", "late_dominant_share", "late_concentration_hhi",
        "family_minus_all_dominant_share",
        *[f"all_share_{topic}" for topic in TOPIC_ORDER],
        *[f"family_share_{topic}" for topic in TOPIC_ORDER],
        *[f"late_share_{topic}" for topic in TOPIC_ORDER],
    ]
    write_csv(OUT_DIR / "word_anchor_run_summary.csv", run_summary_rows, run_fieldnames)

    bin_fieldnames = [
        "scale", "condition", "run_name", "label",
        "bin_idx", "bin_start", "bin_end", "n_posts",
        "dominant_topic", "dominant_share", "concentration_hhi",
        *[f"share_{topic}" for topic in TOPIC_ORDER],
    ]
    write_csv(OUT_DIR / "word_anchor_bin_shares.csv", bin_rows, bin_fieldnames)

    # 5. Plot
    plot_share_heatmap(
        family_heatmap_rows,
        "word_anchor_family_heatmap.png",
        "Phrase-family posts vs word-embedded topic anchors",
        "Each cell = share of phrase-family posts whose embedding is closest to that word anchor.",
    )
    plot_share_heatmap(
        late_heatmap_rows,
        "word_anchor_late_heatmap.png",
        "Late-run posts vs word-embedded topic anchors",
        "Each cell = share of posts from the 45-60 min window nearest to that word anchor.",
    )
    plot_dominant_share(run_summary_rows)
    plot_anchor_cluster_grid(assignment_rows, run_summary_rows, mode="all")
    plot_anchor_cluster_grid(assignment_rows, run_summary_rows, mode="family")
    plot_anchor_cluster_grid(assignment_rows, run_summary_rows, mode="late")
    plot_centroids_pca(late_centroid_rows, anchors)

    # 6. Summary JSON
    same_topic_count = sum(
        row["all_dominant_topic"] == row["family_dominant_topic"]
        for row in run_summary_rows
        if row["family_dominant_topic"] is not None
    )
    more_concentrated_count = sum(
        row["family_dominant_share"] > row["all_dominant_share"]
        for row in run_summary_rows
        if row["n_family_posts"] > 0
    )

    summary = {
        "method": {
            "anchor_definition": (
                "Each topic anchor is the embedding of a descriptive phrase, "
                "generated by the same model used for post embeddings "
                f"({EMBED_MODEL}). Anchors are independent of the post corpus."
            ),
            "anchor_phrases": ANCHOR_PHRASES,
            "assignment_rule": "Each post is assigned to the word anchor with highest cosine similarity.",
        },
        "n_runs": len(run_summary_rows),
        "family_same_dominant_topic_as_run": {
            "count": int(same_topic_count),
            "total": int(len(run_summary_rows)),
        },
        "family_more_concentrated_than_run": {
            "count": int(more_concentrated_count),
            "total": int(len(run_summary_rows)),
        },
        "runs": run_summary_rows,
    }

    with (OUT_DIR / "word_anchor_summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2)

    outputs = [
        "word_anchor_assignments.csv",
        "word_anchor_run_summary.csv",
        "word_anchor_bin_shares.csv",
        "word_anchor_family_heatmap.png",
        "word_anchor_late_heatmap.png",
        "word_anchor_dominant_share.png",
        "word_anchor_cluster_grid.png",
        "word_anchor_family_cluster_grid.png",
        "word_anchor_late_cluster_grid.png",
        "word_anchor_centroids_pca.png",
        "word_anchor_summary.json",
    ]
    for name in outputs:
        print(f"Wrote {OUT_DIR / name}")


if __name__ == "__main__":
    main()
