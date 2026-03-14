#!/usr/bin/env python3
"""Focused embedding bridge analyses for entropy-collapse scaling.

This script adds the missing bridge between the lexical analyses and the
embedding analyses without overwriting any previous work.

Outputs:
  - lexical_semantic_bridge.csv
  - lexical_semantic_bridge.png
  - early_adoption_late_semantics.csv
  - early_adoption_late_semantics.png
  - phrase_removal_robustness.csv
  - phrase_removal_robustness.png
  - embedding_bridge_reframed_summary.json
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from load_entropy_data import CONDITION_LABELS, CONDITION_ORDER, load_all_scales, group_records
from time_binned_lexical_metrics_5gram import fixed_time_bins, ngram_counter, prepare_posts

# ---------------------------------------------------------------------------
OUT_DIR = Path("findings/entropy-collapse-scaling/embedding_bridge")
DIV_CSV = Path("findings/entropy-collapse-scaling/diversity/diversity_metrics.csv")
SEM_CSV = Path("findings/entropy-collapse-scaling/embedding_bridge/semantic_collapse_metrics.csv")
PART_CSV = Path("findings/entropy-collapse-scaling/participation/per_run_participation.csv")

SCALES = ["n20", "n30"]
BIN_EDGES = [0.0, 15.0, 30.0, 45.0, 60.0]
TOP_K = 5
NGRAM_SIZE = 5

COND_COLORS = {
    "mag0": "#6B7280",
    "mag1": "#E11D48",
    "mag5": "#F97316",
    "mag25": "#EAB308",
    "dom-agi": "#2563EB",
    "dom-tech": "#059669",
}
SCALE_MARKERS = {"n20": "o", "n30": "s"}
MASK_STYLES = {
    "all": {"label": "All posts", "color": "#111827"},
    "exclude_top1": {"label": "Exclude top-1 phrase", "color": "#2563EB"},
    "exclude_top5": {"label": "Exclude top-5 phrases", "color": "#DC2626"},
}


def load_embeddings(scale: str) -> dict[str, np.ndarray]:
    path = Path(f"embeddings_{scale}.npz")
    data = np.load(path, allow_pickle=True)
    ids = data["post_id"]
    embs = data["embeddings"]
    return {str(pid): embs[i] for i, pid in enumerate(ids)}


def safe_corr(df: pd.DataFrame, left: str, right: str) -> float | None:
    subset = df[[left, right]].dropna()
    if len(subset) < 2:
        return None
    return float(subset[left].corr(subset[right]))


def mean_pairwise_cosine(vectors: list[np.ndarray]) -> float | None:
    if len(vectors) < 2:
        return None
    arr = np.asarray(vectors)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = arr / norms
    sims = normed @ normed.T
    iu = np.triu_indices(len(arr), k=1)
    return float(np.mean(sims[iu]))


def inter_agent_similarity(author_vectors: list[tuple[str, np.ndarray]]) -> float | None:
    authors = [author for author, _ in author_vectors]
    if len(set(authors)) < 2:
        return None

    arr = np.asarray([vector for _, vector in author_vectors])
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    normed = arr / norms
    sims = normed @ normed.T

    author_arr = np.asarray(authors)
    diff_author = author_arr[:, None] != author_arr[None, :]
    upper = np.triu(np.ones_like(sims, dtype=bool), k=1)
    mask = diff_author & upper
    if not np.any(mask):
        return None
    return float(np.mean(sims[mask]))


def _legend_handles():
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
        if cond in COND_COLORS
    ]
    scale_handles = [
        plt.Line2D(
            [0],
            [0],
            marker=SCALE_MARKERS[scale],
            linestyle="",
            color="#374151",
            markersize=8,
            label=f"{scale[1:]} agents",
        )
        for scale in SCALES
    ]
    return cond_handles, scale_handles


def build_lexical_semantic_bridge() -> tuple[pd.DataFrame, dict]:
    div = pd.read_csv(DIV_CSV)
    sem = pd.read_csv(SEM_CSV)

    merged = div.merge(
        sem,
        on=["scale", "condition", "run_name", "bin_idx", "bin_start", "bin_end", "n_posts"],
        how="inner",
    )
    merged = merged[merged["scale"].isin(SCALES)].copy()
    merged["lexical_collapse"] = 1.0 - merged["distinct_5_cumulative"]
    merged = merged.sort_values(["scale", "condition", "run_name", "bin_idx"])
    merged.to_csv(OUT_DIR / "lexical_semantic_bridge.csv", index=False)

    summary = {
        "n_rows": int(len(merged)),
        "overall": {
            "lexical_collapse_vs_post_similarity": safe_corr(
                merged, "lexical_collapse", "mean_pairwise_cosine"
            ),
            "lexical_collapse_vs_inter_agent_similarity": safe_corr(
                merged, "lexical_collapse", "inter_agent_similarity"
            ),
        },
        "by_scale": {},
    }
    for scale, group in merged.groupby("scale"):
        summary["by_scale"][scale] = {
            "lexical_collapse_vs_post_similarity": safe_corr(
                group, "lexical_collapse", "mean_pairwise_cosine"
            ),
            "lexical_collapse_vs_inter_agent_similarity": safe_corr(
                group, "lexical_collapse", "inter_agent_similarity"
            ),
        }

    fig, axes = plt.subplots(1, 2, figsize=(15, 6), sharex=True)
    y_specs = [
        ("mean_pairwise_cosine", "Post semantic similarity"),
        ("inter_agent_similarity", "Cross-agent post similarity"),
    ]

    for ax, (y_col, y_label) in zip(axes, y_specs):
        for (scale, condition, run_name), group in merged.groupby(["scale", "condition", "run_name"]):
            group = group.sort_values("bin_idx")
            xs = group["lexical_collapse"].to_numpy()
            ys = group[y_col].to_numpy()
            color = COND_COLORS.get(condition, "#6B7280")
            marker = SCALE_MARKERS[scale]

            for idx in range(len(group) - 1):
                ax.annotate(
                    "",
                    xy=(xs[idx + 1], ys[idx + 1]),
                    xytext=(xs[idx], ys[idx]),
                    arrowprops={
                        "arrowstyle": "->",
                        "color": color,
                        "alpha": 0.30,
                        "lw": 1.3,
                        "shrinkA": 0,
                        "shrinkB": 0,
                    },
                )

            sizes = [28, 34, 40, 52]
            for idx, (x_val, y_val) in enumerate(zip(xs, ys)):
                ax.scatter(
                    x_val,
                    y_val,
                    s=sizes[min(idx, len(sizes) - 1)],
                    c=color,
                    marker=marker,
                    alpha=0.85,
                    edgecolors="white",
                    linewidths=0.5,
                    zorder=3,
                )

        corr = summary["overall"][
            "lexical_collapse_vs_post_similarity"
            if y_col == "mean_pairwise_cosine"
            else "lexical_collapse_vs_inter_agent_similarity"
        ]
        corr_text = "n/a" if corr is None else f"{corr:.2f}"
        ax.text(
            0.03,
            0.97,
            f"Overall r = {corr_text}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            color="#374151",
            bbox={"facecolor": "white", "edgecolor": "#E5E7EB", "boxstyle": "round,pad=0.3"},
        )
        ax.set_xlabel("Lexical collapse (1 - cumulative distinct-5)")
        ax.set_ylabel(y_label)
        ax.grid(alpha=0.2)

    cond_handles, scale_handles = _legend_handles()
    fig.legend(
        handles=cond_handles + scale_handles,
        loc="upper center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 1.03),
    )
    fig.suptitle(
        "Lexical collapse tracks semantic collapse over time",
        fontsize=16,
        fontweight="bold",
        y=1.08,
    )
    fig.text(
        0.5,
        1.01,
        "Each path is one run moving through the 15-minute bins. Later bins are larger points.",
        ha="center",
        fontsize=10,
        color="#4B5563",
    )
    fig.tight_layout()
    fig.savefig(OUT_DIR / "lexical_semantic_bridge.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    return merged, summary


def build_early_adoption_bridge(sem: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    part = pd.read_csv(PART_CSV)
    top1 = part[(part["phrase_rank"] == 1) & (part["scale"].isin(SCALES))].copy()

    final_sem = (
        sem.sort_values("bin_idx")
        .groupby(["scale", "condition", "run_name"], as_index=False)
        .tail(1)
        .copy()
    )
    runs = final_sem.merge(
        top1[
            [
                "scale",
                "condition",
                "run_name",
                "phrase",
                "participation_rate",
                "early_rate",
                "late_rate",
            ]
        ],
        on=["scale", "condition", "run_name"],
        how="inner",
    )
    runs = runs.sort_values(["scale", "condition"])
    runs.to_csv(OUT_DIR / "early_adoption_late_semantics.csv", index=False)

    summary = {
        "n_runs": int(len(runs)),
        "correlations": {
            "early_rate_vs_late_post_similarity": safe_corr(
                runs, "early_rate", "mean_pairwise_cosine"
            ),
            "early_rate_vs_late_agent_similarity": safe_corr(
                runs, "early_rate", "inter_agent_similarity"
            ),
            "participation_rate_vs_late_post_similarity": safe_corr(
                runs, "participation_rate", "mean_pairwise_cosine"
            ),
            "participation_rate_vs_late_agent_similarity": safe_corr(
                runs, "participation_rate", "inter_agent_similarity"
            ),
        },
    }

    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharex=True)
    y_specs = [
        ("mean_pairwise_cosine", "Late post semantic similarity"),
        ("inter_agent_similarity", "Late cross-agent post similarity"),
    ]

    for ax, (y_col, y_label) in zip(axes, y_specs):
        for _, row in runs.iterrows():
            ax.scatter(
                row["early_rate"],
                row[y_col],
                s=85,
                c=COND_COLORS.get(row["condition"], "#6B7280"),
                marker=SCALE_MARKERS[row["scale"]],
                edgecolors="white",
                linewidths=0.7,
                alpha=0.90,
            )

        corr = summary["correlations"][
            "early_rate_vs_late_post_similarity"
            if y_col == "mean_pairwise_cosine"
            else "early_rate_vs_late_agent_similarity"
        ]
        corr_text = "n/a" if corr is None else f"{corr:.2f}"
        ax.text(
            0.03,
            0.97,
            f"r = {corr_text}",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=10,
            color="#374151",
            bbox={"facecolor": "white", "edgecolor": "#E5E7EB", "boxstyle": "round,pad=0.3"},
        )
        ax.set_xlabel("Early top-1 phrase adoption (0-30m)")
        ax.set_ylabel(y_label)
        ax.grid(alpha=0.2)

    cond_handles, scale_handles = _legend_handles()
    fig.legend(
        handles=cond_handles + scale_handles,
        loc="upper center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 1.05),
    )
    fig.suptitle(
        "Runs with earlier template spread tend to end more collapsed semantically",
        fontsize=15,
        fontweight="bold",
        y=1.10,
    )
    fig.tight_layout()
    fig.savefig(OUT_DIR / "early_adoption_late_semantics.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    return runs, summary


def compute_phrase_removal_robustness() -> tuple[pd.DataFrame, dict]:
    print("Loading run data for phrase-removal robustness...")
    records = [record for record in load_all_scales(include_scales=SCALES) if not record.is_seed]
    by_run = group_records(records, lambda r: (r.scale, r.condition, r.run_name))

    emb_map: dict[str, np.ndarray] = {}
    for scale in SCALES:
        scale_embs = load_embeddings(scale)
        emb_map.update(scale_embs)
        print(f"  {scale}: {len(scale_embs)} embeddings")

    rows: list[dict] = []
    for (scale, condition, run_name), run_records in sorted(by_run.items()):
        prepared = prepare_posts(run_records)
        top_phrases = [" ".join(gram) for gram, _ in ngram_counter(prepared, NGRAM_SIZE).most_common(TOP_K)]
        top1 = set(top_phrases[:1])
        top5 = set(top_phrases)

        bins = fixed_time_bins(prepared, bin_edges=BIN_EDGES)
        for bin_idx, start, end, posts in bins:
            tagged_posts = []
            for post in posts:
                rec = post.record
                if rec.post_id not in emb_map:
                    continue
                grams = {" ".join(gram) for gram in post.ngrams_by_n[NGRAM_SIZE]}
                tagged_posts.append(
                    {
                        "author": rec.author_name,
                        "vector": emb_map[rec.post_id],
                        "contains_top1": bool(top1 & grams),
                        "contains_top5": bool(top5 & grams),
                    }
                )

            mask_specs = {
                "all": tagged_posts,
                "exclude_top1": [post for post in tagged_posts if not post["contains_top1"]],
                "exclude_top5": [post for post in tagged_posts if not post["contains_top5"]],
            }
            for mask_name, subset in mask_specs.items():
                vectors = [post["vector"] for post in subset]
                author_vectors = [(post["author"], post["vector"]) for post in subset]
                rows.append(
                    {
                        "scale": scale,
                        "condition": condition,
                        "run_name": run_name,
                        "bin_idx": bin_idx,
                        "bin_start": start,
                        "bin_end": end,
                        "mask": mask_name,
                        "top_phrase": top_phrases[0] if top_phrases else "",
                        "top5_phrases": top_phrases,
                        "n_posts": len(subset),
                        "n_agents": len({post["author"] for post in subset}),
                        "mean_pairwise_cosine": mean_pairwise_cosine(vectors),
                        "inter_agent_similarity": inter_agent_similarity(author_vectors),
                    }
                )

    df = pd.DataFrame(rows)
    df["top5_phrases"] = df["top5_phrases"].apply(json.dumps)
    df.to_csv(OUT_DIR / "phrase_removal_robustness.csv", index=False)

    summary = {"n_rows": int(len(df)), "by_mask": {}, "by_scale": {}}
    for mask_name, mask_df in df.groupby("mask"):
        delta_post = []
        delta_agent = []
        for _, run_df in mask_df.groupby(["scale", "condition", "run_name"]):
            run_df = run_df.sort_values("bin_idx")
            post_vals = run_df["mean_pairwise_cosine"].dropna().tolist()
            agent_vals = run_df["inter_agent_similarity"].dropna().tolist()
            if len(post_vals) >= 2:
                delta_post.append(post_vals[-1] - post_vals[0])
            if len(agent_vals) >= 2:
                delta_agent.append(agent_vals[-1] - agent_vals[0])
        summary["by_mask"][mask_name] = {
            "mean_post_similarity_delta": float(np.mean(delta_post)) if delta_post else None,
            "mean_agent_similarity_delta": float(np.mean(delta_agent)) if delta_agent else None,
            "positive_post_similarity_runs": int(sum(delta > 0 for delta in delta_post)),
            "positive_agent_similarity_runs": int(sum(delta > 0 for delta in delta_agent)),
            "total_post_similarity_runs": int(len(delta_post)),
            "total_agent_similarity_runs": int(len(delta_agent)),
        }

    for scale, scale_df in df.groupby("scale"):
        summary["by_scale"][scale] = {}
        for mask_name, mask_df in scale_df.groupby("mask"):
            delta_post = []
            delta_agent = []
            for _, run_df in mask_df.groupby(["condition", "run_name"]):
                run_df = run_df.sort_values("bin_idx")
                post_vals = run_df["mean_pairwise_cosine"].dropna().tolist()
                agent_vals = run_df["inter_agent_similarity"].dropna().tolist()
                if len(post_vals) >= 2:
                    delta_post.append(post_vals[-1] - post_vals[0])
                if len(agent_vals) >= 2:
                    delta_agent.append(agent_vals[-1] - agent_vals[0])
            summary["by_scale"][scale][mask_name] = {
                "mean_post_similarity_delta": float(np.mean(delta_post)) if delta_post else None,
                "mean_agent_similarity_delta": float(np.mean(delta_agent)) if delta_agent else None,
            }

    fig, axes = plt.subplots(len(SCALES), 2, figsize=(14, 9), sharex=True)
    if len(SCALES) == 1:
        axes = np.array([axes])

    for row_idx, scale in enumerate(SCALES):
        scale_df = df[df["scale"] == scale].copy()
        grouped = (
            scale_df.groupby(["mask", "bin_idx", "bin_start", "bin_end"], as_index=False)[
                ["mean_pairwise_cosine", "inter_agent_similarity"]
            ]
            .mean()
            .sort_values(["mask", "bin_idx"])
        )
        x_vals = grouped["bin_end"].drop_duplicates().tolist()
        x_labels = ["0-15", "15-30", "30-45", "45-60"]

        for col_idx, (metric, y_label) in enumerate(
            [
                ("mean_pairwise_cosine", "Post semantic similarity"),
                ("inter_agent_similarity", "Cross-agent post similarity"),
            ]
        ):
            ax = axes[row_idx, col_idx]
            for mask_name in ["all", "exclude_top1", "exclude_top5"]:
                mask_df = grouped[grouped["mask"] == mask_name].sort_values("bin_idx")
                ax.plot(
                    mask_df["bin_end"],
                    mask_df[metric],
                    "-o",
                    lw=2.2,
                    ms=6,
                    color=MASK_STYLES[mask_name]["color"],
                    label=MASK_STYLES[mask_name]["label"],
                )
            ax.set_xticks(x_vals)
            ax.set_xticklabels(x_labels)
            ax.set_ylabel(y_label)
            ax.set_title(f"{scale[1:]} agents", fontsize=12, fontweight="bold")
            ax.grid(alpha=0.2)
            if row_idx == len(SCALES) - 1:
                ax.set_xlabel("Time bin")

    axes[0, 1].legend(frameon=False, loc="lower right")
    fig.suptitle(
        "Semantic collapse remains after removing dominant phrase posts",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )
    fig.text(
        0.5,
        0.945,
        "Lines are run-averaged metrics. The key comparison is whether the rise survives after excluding top-1/top-5 phrase posts.",
        ha="center",
        fontsize=10,
        color="#4B5563",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(OUT_DIR / "phrase_removal_robustness.png", dpi=180, bbox_inches="tight")
    plt.close(fig)

    return df, summary


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Building lexical/semantic bridge...")
    sem_bridge_df, sem_bridge_summary = build_lexical_semantic_bridge()

    print("Building early-adoption bridge...")
    early_df, early_summary = build_early_adoption_bridge(sem_bridge_df)

    print("Computing phrase-removal robustness...")
    robustness_df, robustness_summary = compute_phrase_removal_robustness()

    summary = {
        "scales": SCALES,
        "lexical_semantic_bridge": sem_bridge_summary,
        "early_adoption_bridge": early_summary,
        "phrase_removal_robustness": robustness_summary,
        "files_written": [
            "lexical_semantic_bridge.csv",
            "lexical_semantic_bridge.png",
            "early_adoption_late_semantics.csv",
            "early_adoption_late_semantics.png",
            "phrase_removal_robustness.csv",
            "phrase_removal_robustness.png",
        ],
        "n_rows": {
            "lexical_semantic_bridge": int(len(sem_bridge_df)),
            "early_adoption_late_semantics": int(len(early_df)),
            "phrase_removal_robustness": int(len(robustness_df)),
        },
    }
    with (OUT_DIR / "embedding_bridge_reframed_summary.json").open("w") as handle:
        json.dump(summary, handle, indent=2, ensure_ascii=False)

    print(f"Wrote {OUT_DIR / 'embedding_bridge_reframed_summary.json'}")
    print("Done!")


if __name__ == "__main__":
    main()
