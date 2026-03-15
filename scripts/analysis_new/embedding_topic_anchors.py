#!/usr/bin/env python3
"""Embedding topic-anchor analysis for entropy-collapse scaling.

This analysis does not embed the labels "Evidence", "Testing", "Ownership",
"Time", and "Risk" directly. The stored post embeddings were created earlier
with an external model, so the safer local option is:

1. Reuse the existing post embeddings.
2. Build one anchor per topic as the centroid of already-embedded posts whose
   text matches that topic's lexical cue set.
3. Score every post by cosine similarity to the five anchors.
4. Ask two concrete questions:
   - Do dominant phrase-family posts concentrate toward one topic anchor?
   - By the late phase of the run, does the whole run tilt toward one anchor?

Outputs:
  - topic_anchor_assignments.csv
  - topic_anchor_run_summary.csv
  - topic_anchor_bin_shares.csv
  - topic_anchor_family_heatmap.png
  - topic_anchor_late_heatmap.png
  - topic_anchor_dominant_share.png
  - topic_anchor_centroids_pca.png
  - topic_anchor_summary.json
"""

from __future__ import annotations

import csv
import json
import os
import sys
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

OUT_DIR = Path("findings/entropy-collapse-scaling/embedding_bridge")
SCALES = ["n10", "n20", "n30"]
BIN_EDGES = [0.0, 15.0, 30.0, 45.0, 60.0]
TOPIC_ORDER = list(CATEGORY_LEXICONS.keys())
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


def load_embeddings(scale: str, prefix: str = "embeddings") -> dict[str, np.ndarray]:
    data = np.load(Path(f"{prefix}_{scale}.npz"), allow_pickle=True)
    ids = data["post_id"]
    embs = data["embeddings"]
    return {str(pid): embs[idx] for idx, pid in enumerate(ids)}


def normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector
    return vector / norm


def bin_index(minutes_elapsed: float) -> int | None:
    for idx in range(len(BIN_EDGES) - 1):
        if BIN_EDGES[idx] <= minutes_elapsed < BIN_EDGES[idx + 1]:
            return idx
    return None


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
    return CATEGORY_LABELS.get(topic, topic)


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


def build_topic_anchors(prepared_posts, emb_map: dict[str, np.ndarray]) -> tuple[dict[str, np.ndarray], dict[str, int]]:
    anchors = {}
    counts = {}
    for topic, lexicon in CATEGORY_LEXICONS.items():
        vectors = []
        for post in prepared_posts:
            post_id = post.record.post_id
            if post_id not in emb_map:
                continue
            if set(post.tokens) & lexicon:
                vectors.append(emb_map[post_id])
        if not vectors:
            continue
        centroid = normalize(np.mean(np.asarray(vectors), axis=0))
        anchors[topic] = centroid
        counts[topic] = len(vectors)
    return anchors, counts


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


def plot_share_heatmap(rows: list[dict], out_name: str, title: str, subtitle: str) -> None:
    ordered = ordered_heatmap_rows(rows)
    labels = [row["label"] for row in ordered]
    data = np.array([[row[f"share_{topic}"] for topic in TOPIC_ORDER] for row in ordered], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0.0, vmax=max(0.6, float(np.max(data))))

    ax.set_xticks(range(len(TOPIC_ORDER)))
    ax.set_xticklabels([CATEGORY_LABELS[topic] for topic in TOPIC_ORDER], rotation=0)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)

    for yi in range(data.shape[0]):
        for xi in range(data.shape[1]):
            value = data[yi, xi]
            text_color = "white" if value >= 0.38 else "#111827"
            ax.text(xi, yi, f"{value:.2f}", ha="center", va="center", fontsize=9, color=text_color)

    for yi, row in enumerate(ordered):
        ax.get_yticklabels()[yi].set_color(COND_COLORS.get(row["condition"], "#6B7280"))

    fig.colorbar(im, ax=ax, shrink=0.9, label="Share of posts nearest to topic anchor")
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
        ax.text(
            family_vals[idx] + 0.01,
            y[idx] + 0.18,
            f"{family_vals[idx]:.2f}",
            va="center",
            fontsize=9,
            color="#111827",
        )
        ax.text(
            all_vals[idx] + 0.01,
            y[idx] - 0.18,
            f"{all_vals[idx]:.2f}",
            va="center",
            fontsize=9,
            color="#4B5563",
        )

    ax.set_xlim(0, 1.0)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("Share of posts nearest to the run's dominant topic anchor")
    ax.set_title(
        "Dominant phrase-family posts are more topic-concentrated than the run overall",
        fontsize=15,
        fontweight="bold",
    )
    ax.grid(axis="x", alpha=0.15)

    handles = [
        plt.Rectangle((0, 0), 1, 1, color="#D1D5DB", label="All posts"),
        plt.Rectangle((0, 0), 1, 1, facecolor="white", edgecolor="#111827", linewidth=1.2, label="Phrase-family posts"),
    ]
    topic_handles = [
        plt.Line2D([0], [0], marker="s", linestyle="", markersize=8, color=TOPIC_COLORS[topic], label=CATEGORY_LABELS[topic])
        for topic in TOPIC_ORDER
    ]
    legend_a = ax.legend(handles=handles, loc="upper right", frameon=False)
    ax.add_artist(legend_a)
    ax.legend(handles=topic_handles, loc="lower center", ncol=5, frameon=False, bbox_to_anchor=(0.5, -0.12))

    fig.tight_layout()
    fig.savefig(OUT_DIR / "topic_anchor_dominant_share.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def setup_anchor_axes(ax) -> None:
    polygon = np.array([ANCHOR_LAYOUT[topic] for topic in ANCHOR_POLYGON_ORDER], dtype=float)
    ax.plot(polygon[:, 0], polygon[:, 1], linestyle="--", linewidth=0.8, color="#E5E7EB", zorder=1)
    for topic in TOPIC_ORDER:
        x_val, y_val = ANCHOR_LAYOUT[topic]
        ax.scatter(
            x_val,
            y_val,
            marker="X",
            s=85,
            c=TOPIC_COLORS[topic],
            edgecolors="white",
            linewidths=0.7,
            zorder=5,
        )
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
    fig, axes = plt.subplots(len(SCALES), len(CONDITION_ORDER), figsize=(22, fig_height), sharex=True, sharey=True, squeeze=False)
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
                        s=16,
                        c=TOPIC_COLORS[topic],
                        alpha=0.88,
                        edgecolors="white",
                        linewidths=0.2,
                        zorder=2,
                    )
                note = (
                    f"{CATEGORY_LABELS[summary['all_dominant_topic']]} {summary['all_dominant_share']:.2f}\n"
                    f"n={summary['n_posts']}"
                )
            elif mode == "family":
                other_rows = [row for row in rows if row["in_family"] == 0]
                family_rows = [row for row in rows if row["in_family"] == 1]
                if other_rows:
                    ax.scatter(
                        [row["anchor_x"] for row in other_rows],
                        [row["anchor_y"] for row in other_rows],
                        s=7,
                        c="#BFC7D1",
                        alpha=0.18,
                        edgecolors="none",
                        zorder=2,
                    )
                for topic in TOPIC_ORDER:
                    topic_rows = [row for row in family_rows if row["top_topic"] == topic]
                    if not topic_rows:
                        continue
                    ax.scatter(
                        [row["anchor_x"] for row in topic_rows],
                        [row["anchor_y"] for row in topic_rows],
                        s=16,
                        c=TOPIC_COLORS[topic],
                        alpha=0.88,
                        edgecolors="white",
                        linewidths=0.2,
                        zorder=4,
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
                        s=10,
                        c=TOPIC_COLORS[topic],
                        alpha=0.26,
                        edgecolors="none",
                        zorder=3,
                    )
                late_family_rows = [
                    row for row in late_rows if row["in_family"] == 1
                ]
                if late_family_rows:
                    ax.scatter(
                        [row["anchor_x"] for row in late_family_rows],
                        [row["anchor_y"] for row in late_family_rows],
                        s=18,
                        facecolors="none",
                        edgecolors="#111827",
                        linewidths=0.45,
                        alpha=0.9,
                        zorder=4,
                    )
                note = (
                    f"late: {format_topic_label(summary['late_dominant_topic'])} "
                    f"{summary['late_dominant_share']:.2f}"
                )
            else:
                raise ValueError(f"Unknown mode: {mode}")

            ax.text(
                0.03,
                0.04,
                note,
                transform=ax.transAxes,
                ha="left",
                va="bottom",
                fontsize=8.5,
                color="#111827",
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 1.5},
            )

            if row_idx == 0:
                ax.set_title(CONDITION_LABELS.get(condition, condition), fontsize=11, fontweight="bold", color=COND_COLORS.get(condition, "#111827"))
            if col_idx == 0:
                ax.set_ylabel(f"{scale[1:]} agents", fontsize=11, fontweight="bold")

    topic_handles = [
        plt.Line2D([0], [0], marker="o", linestyle="", markersize=7, color=TOPIC_COLORS[topic], label=CATEGORY_LABELS[topic])
        for topic in TOPIC_ORDER
    ]
    outline_handle = plt.Line2D(
        [0],
        [0],
        marker="o",
        linestyle="",
        markersize=7,
        markerfacecolor="white",
        markeredgecolor="#111827",
        markeredgewidth=1.0,
        color="#111827",
        label="Phrase-family posts",
    )
    anchor_handle = plt.Line2D(
        [0],
        [0],
        marker="X",
        linestyle="",
        markersize=9,
        color="#374151",
        label="Topic anchor",
    )

    if mode == "all":
        title = "All posts cluster near topic anchors"
        subtitle = "Every post colored by its nearest anchor. Anchors are centroids of lexicon-matching posts."
        out_name = "topic_anchor_cluster_grid.png"
        legend_handles = topic_handles + [anchor_handle]
    elif mode == "family":
        title = "Repeated-phrase posts cluster near a single topic anchor"
        subtitle = "Grey points are the rest of the run. Colored points are posts containing the dominant phrase family."
        out_name = "topic_anchor_family_cluster_grid.png"
        legend_handles = topic_handles + [anchor_handle]
    else:
        title = "Late-run posts concentrate near a few topic anchors"
        subtitle = "Point positions come from cosine pull toward the five anchor centroids. Black outlines mark late phrase-family posts."
        out_name = "topic_anchor_late_cluster_grid.png"
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
        ax.text(x_val + 0.02, y_val + 0.02, CATEGORY_LABELS[topic], fontsize=10, fontweight="bold", color=TOPIC_COLORS[topic])

    offset = len(anchor_topics)
    for idx, row in enumerate(late_centroid_rows):
        x_val, y_val = coords[offset + idx]
        ax.scatter(
            x_val,
            y_val,
            s=90,
            c=COND_COLORS.get(row["condition"], "#6B7280"),
            marker=SCALE_MARKERS.get(row["scale"], "o"),
            edgecolors="white",
            linewidths=0.8,
            alpha=0.95,
            zorder=3,
        )
        ax.text(x_val + 0.015, y_val - 0.015, row["short_label"], fontsize=8, color="#111827")

    cond_handles = [
        plt.Line2D(
            [0],
            [0],
            marker="o",
            linestyle="",
            markerfacecolor=COND_COLORS[cond],
            markeredgecolor="white",
            markeredgewidth=0.6,
            markersize=8,
            label=CONDITION_LABELS.get(cond, cond),
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
    ax.set_title("Late-run centroids in topic-anchor PCA map", fontsize=15, fontweight="bold")
    fig.text(
        0.5,
        0.96,
        "PCA is only for display. Topic assignment itself uses cosine similarity in the full embedding space.",
        ha="center",
        fontsize=10,
        color="#4B5563",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "topic_anchor_centroids_pca.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Embedding topic-anchor analysis.")
    parser.add_argument("--scales", type=str, default=None, help="Comma-separated scales (default: n10,n20,n30).")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory override.")
    parser.add_argument("--emb-prefix", type=str, default="embeddings", help="Embedding file prefix (default: 'embeddings' → embeddings_n10.npz).")
    parser.add_argument("--data-dir", type=str, default=None, help="Override data directory (all scales read from this single dir).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    scales = args.scales.split(",") if args.scales else SCALES
    global OUT_DIR
    if args.out_dir:
        OUT_DIR = Path(args.out_dir)
    emb_prefix = args.emb_prefix
    scale_dirs = {s: Path(args.data_dir) for s in scales} if args.data_dir else None

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    records = [record for record in load_all_scales(scale_dirs=scale_dirs, include_scales=scales) if not record.is_seed]
    prepared_posts = prepare_posts(records)
    prepared_by_id = {post.record.post_id: post for post in prepared_posts}

    emb_map = {}
    for scale in scales:
        emb_map.update(load_embeddings(scale, prefix=emb_prefix))
    norm_emb_map = {post_id: normalize(vector) for post_id, vector in emb_map.items()}

    anchors, anchor_counts = build_topic_anchors(prepared_posts, emb_map)

    by_run = group_records(records, lambda r: (r.scale, r.condition, r.run_name))

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
            topic_sim = topic_scores(norm_emb_map[post_id], anchors)
            top_topic = max(TOPIC_ORDER, key=lambda topic: topic_sim[topic])
            top_similarity = topic_sim[top_topic]
            coord_x, coord_y = anchor_pull_coord(topic_sim)
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
                row[f"sim_{topic}"] = round(topic_sim[topic], 6)
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

        family_heatmap_rows.append(
            {
                "scale": scale,
                "condition": condition,
                "run_name": run_name,
                "label": label,
                **{f"share_{topic}": round(family_summary["shares"][topic], 6) for topic in TOPIC_ORDER},
            }
        )
        late_heatmap_rows.append(
            {
                "scale": scale,
                "condition": condition,
                "run_name": run_name,
                "label": label,
                **{f"share_{topic}": round(late_summary["shares"][topic], 6) for topic in TOPIC_ORDER},
            }
        )

        for bin_idx_value in range(len(BIN_EDGES) - 1):
            bin_assignments = [row for row in run_assignments if row["bin_idx"] == bin_idx_value]
            bin_summary = summarize_assignment_rows(bin_assignments)
            bin_row = {
                "scale": scale,
                "condition": condition,
                "run_name": run_name,
                "label": label,
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
            late_centroid_rows.append(
                {
                    "scale": scale,
                    "condition": condition,
                    "run_name": run_name,
                    "short_label": f"{scale[1:]}-{condition}",
                    "vector": normalize(np.mean(np.asarray(late_vectors), axis=0)),
                }
            )

    assignment_fieldnames = [
        "scale",
        "condition",
        "run_name",
        "post_id",
        "author_name",
        "minutes_elapsed",
        "bin_idx",
        "in_family",
        "top_topic",
        "top_similarity",
        "anchor_x",
        "anchor_y",
        *[f"sim_{topic}" for topic in TOPIC_ORDER],
    ]
    write_csv(OUT_DIR / "topic_anchor_assignments.csv", assignment_rows, assignment_fieldnames)

    run_fieldnames = [
        "scale",
        "condition",
        "condition_label",
        "run_name",
        "label",
        "n_posts",
        "n_family_posts",
        "n_other_posts",
        "family_phrases",
        "all_dominant_topic",
        "all_dominant_share",
        "all_concentration_hhi",
        "family_dominant_topic",
        "family_dominant_share",
        "family_concentration_hhi",
        "other_dominant_topic",
        "other_dominant_share",
        "other_concentration_hhi",
        "late_dominant_topic",
        "late_dominant_share",
        "late_concentration_hhi",
        "family_minus_all_dominant_share",
        *[f"all_share_{topic}" for topic in TOPIC_ORDER],
        *[f"family_share_{topic}" for topic in TOPIC_ORDER],
        *[f"late_share_{topic}" for topic in TOPIC_ORDER],
    ]
    write_csv(OUT_DIR / "topic_anchor_run_summary.csv", run_summary_rows, run_fieldnames)

    bin_fieldnames = [
        "scale",
        "condition",
        "run_name",
        "label",
        "bin_idx",
        "bin_start",
        "bin_end",
        "n_posts",
        "dominant_topic",
        "dominant_share",
        "concentration_hhi",
        *[f"share_{topic}" for topic in TOPIC_ORDER],
    ]
    write_csv(OUT_DIR / "topic_anchor_bin_shares.csv", bin_rows, bin_fieldnames)

    plot_share_heatmap(
        family_heatmap_rows,
        "topic_anchor_family_heatmap.png",
        "Dominant phrase-family posts cluster toward one topic anchor",
        "Each cell is the share of phrase-family posts whose embedding is closest to that topic anchor.",
    )
    plot_share_heatmap(
        late_heatmap_rows,
        "topic_anchor_late_heatmap.png",
        "Late-run posts drift toward a small number of topic anchors",
        "Each cell is the share of posts from the 45-60 minute window nearest to that topic anchor.",
    )
    plot_dominant_share(run_summary_rows)
    plot_anchor_cluster_grid(assignment_rows, run_summary_rows, mode="all")
    plot_anchor_cluster_grid(assignment_rows, run_summary_rows, mode="family")
    plot_anchor_cluster_grid(assignment_rows, run_summary_rows, mode="late")
    plot_centroids_pca(late_centroid_rows, anchors)

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
                "Each topic anchor is the centroid of already-embedded posts that contain "
                "that topic's lexical cues."
            ),
            "assignment_rule": "Each post is assigned to the topic anchor with highest cosine similarity.",
            "primary_outputs": [
                "topic_anchor_family_heatmap.png",
                "topic_anchor_late_heatmap.png",
                "topic_anchor_dominant_share.png",
                "topic_anchor_cluster_grid.png",
                "topic_anchor_family_cluster_grid.png",
                "topic_anchor_late_cluster_grid.png",
                "topic_anchor_centroids_pca.png",
            ],
        },
        "anchor_counts": anchor_counts,
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

    with (OUT_DIR / "topic_anchor_summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2)

    print(f"Wrote {OUT_DIR / 'topic_anchor_assignments.csv'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_run_summary.csv'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_bin_shares.csv'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_family_heatmap.png'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_late_heatmap.png'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_dominant_share.png'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_cluster_grid.png'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_family_cluster_grid.png'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_late_cluster_grid.png'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_centroids_pca.png'}")
    print(f"Wrote {OUT_DIR / 'topic_anchor_summary.json'}")


if __name__ == "__main__":
    main()
