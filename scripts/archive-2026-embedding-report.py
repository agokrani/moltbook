#!/usr/bin/env python3
"""Generate embedding summaries, global clusters, and PNG diagrams for archive-2026 combined corpus."""
from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

try:
    import umap  # type: ignore
except Exception:  # pragma: no cover
    umap = None

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")

PALETTE = [
    "#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#edc948",
    "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac", "#1f77b4", "#ff7f0e",
]


def mean_pairwise_cosine(x: np.ndarray, rng: random.Random, max_n: int = 700) -> float:
    if len(x) < 2:
        return float("nan")
    if len(x) > max_n:
        idx = rng.sample(range(len(x)), max_n)
        x = x[idx]
    sim = x @ x.T
    iu = np.triu_indices(sim.shape[0], k=1)
    return float(np.mean(sim[iu]))


def plot_scatter(df: pd.DataFrame, color_col: str, out_path: Path, title: str, max_points: int = 35000) -> None:
    plot_df = df
    if len(plot_df) > max_points:
        plot_df = plot_df.sample(max_points, random_state=42)
    vals = list(plot_df[color_col].fillna("unknown").astype(str).unique())
    vals = sorted(vals)
    color_map = {v: PALETTE[i % len(PALETTE)] for i, v in enumerate(vals)}
    fig, ax = plt.subplots(figsize=(10, 8))
    for v in vals:
        sub = plot_df[plot_df[color_col].fillna("unknown").astype(str) == v]
        ax.scatter(sub["svd_1"], sub["svd_2"], s=3, alpha=0.45, c=color_map[v], label=v)
    ax.set_title(title)
    ax.set_xlabel("SVD-1")
    ax.set_ylabel("SVD-2")
    ax.legend(markerscale=4, frameon=False, fontsize=7, ncol=2, loc="best")
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def plot_heatmap(pivot: pd.DataFrame, out_path: Path, title: str, label: str, cmap: str = "viridis") -> None:
    fig, ax = plt.subplots(figsize=(max(8, 0.7 * len(pivot.columns)), max(4, 0.4 * len(pivot.index))))
    arr = pivot.to_numpy(dtype=float)
    im = ax.imshow(arr, aspect="auto", cmap=cmap)
    ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=label)
    fig.tight_layout()
    fig.savefig(out_path)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--npz", default="")
    ap.add_argument("--clusters", type=int, default=48)
    ap.add_argument("--umap-sample", type=int, default=25000)
    ap.add_argument("--svd-components", type=int, default=50)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    report_dir = out_dir / "embedding_report"
    report_dir.mkdir(parents=True, exist_ok=True)
    npz_path = Path(args.npz) if args.npz else out_dir / "embeddings" / "qwen-qwen3-embedding-8b.npz"
    index_path = out_dir / "combined_posts_index.csv"

    print("Loading index", index_path)
    index = pd.read_csv(index_path)
    print("Loading embeddings", npz_path)
    npz = np.load(npz_path)
    emb = npz["embeddings"].astype(np.float32)
    record_ids = pd.Series(npz["record_ids"].astype(str), name="record_id")
    if len(index) != len(emb):
        raise SystemExit(f"index rows {len(index)} != embeddings rows {len(emb)}")

    print("Normalizing embeddings", emb.shape)
    x = normalize(emb, norm="l2", copy=False)

    print("Computing TruncatedSVD")
    svd = TruncatedSVD(n_components=args.svd_components, random_state=42)
    z = svd.fit_transform(x)

    print("Clustering with MiniBatchKMeans", args.clusters)
    km = MiniBatchKMeans(n_clusters=args.clusters, random_state=42, batch_size=4096, n_init="auto")
    cluster_ids = km.fit_predict(z)

    df = index.copy()
    df["record_id_from_npz"] = record_ids
    df["svd_1"] = z[:, 0]
    df["svd_2"] = z[:, 1]
    df["cluster_id"] = cluster_ids
    df["cluster_label"] = [f"cluster_{c:02d}" for c in cluster_ids]
    df.to_csv(report_dir / "embedding_analysis_data.csv", index=False)

    print("Computing summaries")
    rng = random.Random(42)
    run_rows = []
    for (source, group, run_path), sub in df.groupby(["dataset_source", "group", "run_path"], dropna=False):
        idx = sub.index.to_numpy()
        run_rows.append({
            "dataset_source": source,
            "group": group,
            "run_id": sub["run_id"].iloc[0] if len(sub) else "unknown",
            "run_path": run_path,
            "model_family": sub["model_family"].mode().iloc[0] if len(sub) else "unknown",
            "condition": sub["condition"].mode().iloc[0] if len(sub) else "unknown",
            "scale": sub["scale"].mode().iloc[0] if len(sub) else "unknown",
            "n_posts": len(sub),
            "n_nonseed": int((~sub["is_seed"].astype(bool)).sum()),
            "mean_pairwise_cosine": mean_pairwise_cosine(x[idx], rng),
            "dominant_cluster": int(sub["cluster_id"].value_counts().idxmax()),
            "dominant_cluster_share": float(sub["cluster_id"].value_counts(normalize=True).max()),
        })
    run_summary = pd.DataFrame(run_rows)
    run_summary.to_csv(report_dir / "run_embedding_summary.csv", index=False)

    group_summary = run_summary.groupby(["group"], as_index=False).agg(
        n_runs=("run_path", "nunique"),
        n_posts=("n_posts", "sum"),
        mean_pairwise_cosine=("mean_pairwise_cosine", "mean"),
        dominant_cluster_share=("dominant_cluster_share", "mean"),
    )
    group_summary.to_csv(report_dir / "group_embedding_summary.csv", index=False)

    model_summary = run_summary.groupby(["model_family"], as_index=False).agg(
        n_runs=("run_path", "nunique"),
        n_posts=("n_posts", "sum"),
        mean_pairwise_cosine=("mean_pairwise_cosine", "mean"),
        dominant_cluster_share=("dominant_cluster_share", "mean"),
    ).sort_values("n_posts", ascending=False)
    model_summary.to_csv(report_dir / "model_embedding_summary.csv", index=False)

    cluster_summary = df.groupby("cluster_id", as_index=False).agg(
        n_posts=("record_id", "count"),
        n_runs=("run_path", "nunique"),
        top_group=("group", lambda s: s.value_counts().idxmax()),
        top_model=("model_family", lambda s: s.value_counts().idxmax()),
        top_condition=("condition", lambda s: s.value_counts().idxmax()),
        seed_share=("is_seed", "mean"),
    )
    cluster_summary["post_share"] = cluster_summary["n_posts"] / len(df)
    cluster_summary = cluster_summary.sort_values("n_posts", ascending=False)
    cluster_summary.to_csv(report_dir / "cluster_summary.csv", index=False)

    cluster_group = pd.crosstab(df["cluster_label"], df["group"], normalize="index")
    cluster_group.to_csv(report_dir / "cluster_group_shares.csv")

    print("Writing PNGs")
    plot_scatter(df, "group", report_dir / "fig_svd_by_group.png", "Archive + canonical Gemini embeddings by group")
    plot_scatter(df, "model_family", report_dir / "fig_svd_by_model.png", "Archive + canonical Gemini embeddings by model")
    plot_scatter(df, "condition", report_dir / "fig_svd_by_condition.png", "Archive + canonical Gemini embeddings by condition")
    plot_scatter(df, "cluster_label", report_dir / "fig_svd_by_cluster.png", "Global MiniBatchKMeans clusters")

    # UMAP on SVD sample for non-linear view.
    if umap is not None and args.umap_sample > 0:
        sample_n = min(args.umap_sample, len(df))
        sample_idx = np.random.default_rng(42).choice(len(df), size=sample_n, replace=False)
        print("Computing UMAP sample", sample_n)
        reducer = umap.UMAP(n_components=2, metric="euclidean", random_state=42, n_neighbors=30, min_dist=0.1)
        u = reducer.fit_transform(z[sample_idx])
        udf = df.iloc[sample_idx].copy()
        udf["umap_1"] = u[:, 0]
        udf["umap_2"] = u[:, 1]
        udf.to_csv(report_dir / "umap_sample.csv", index=False)
        for col, fname, title in [
            ("group", "fig_umap_by_group.png", "UMAP sample by group"),
            ("cluster_label", "fig_umap_by_cluster.png", "UMAP sample by global cluster"),
        ]:
            vals = sorted(udf[col].fillna("unknown").astype(str).unique())
            cmap = {v: PALETTE[i % len(PALETTE)] for i, v in enumerate(vals)}
            fig, ax = plt.subplots(figsize=(10, 8))
            for v in vals:
                sub = udf[udf[col].fillna("unknown").astype(str) == v]
                ax.scatter(sub["umap_1"], sub["umap_2"], s=4, alpha=0.5, c=cmap[v], label=v)
            ax.set_title(title)
            ax.set_xlabel("UMAP-1")
            ax.set_ylabel("UMAP-2")
            ax.legend(markerscale=4, frameon=False, fontsize=7, ncol=2)
            fig.tight_layout()
            fig.savefig(report_dir / fname)
            plt.close(fig)

    # Heatmaps/bar charts.
    pivot = run_summary.pivot_table(index="group", columns="condition", values="mean_pairwise_cosine", aggfunc="mean")
    plot_heatmap(pivot.fillna(np.nan), report_dir / "fig_group_condition_coherence_heatmap.png", "Mean within-run cosine by group × condition", "Mean pairwise cosine")

    top_clusters = cluster_summary.head(30).sort_values("n_posts")
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh([f"c{int(c):02d}" for c in top_clusters["cluster_id"]], top_clusters["n_posts"], color="#4e79a7")
    ax.set_title("Top 30 global clusters by post count")
    ax.set_xlabel("Posts")
    fig.tight_layout()
    fig.savefig(report_dir / "fig_top_cluster_sizes.png")
    plt.close(fig)

    plot_heatmap(cluster_group.loc[[f"cluster_{int(c):02d}" for c in cluster_summary.head(30)["cluster_id"] if f"cluster_{int(c):02d}" in cluster_group.index]],
                 report_dir / "fig_top_cluster_group_shares.png", "Top cluster composition by group", "Row share", cmap="magma")

    report = f"""# Archive 2026 + Canonical Gemini Embedding Report\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n- Input rows: {len(df):,}\n- Embedding shape: {emb.shape}\n- SVD components: {args.svd_components}\n- Global clusters: {args.clusters} MiniBatchKMeans clusters over SVD coordinates\n- SVD explained variance ratio sum: {float(np.sum(svd.explained_variance_ratio_)):.4f}\n\n## Outputs\n\n- `embedding_analysis_data.csv` — per-post metadata + SVD coordinates + cluster IDs.\n- `run_embedding_summary.csv` — within-run coherence and dominant cluster metrics.\n- `group_embedding_summary.csv`, `model_embedding_summary.csv`, `cluster_summary.csv`.\n- PNG figures: SVD scatter by group/model/condition/cluster, UMAP sample, coherence heatmap, cluster-size and cluster-composition plots.\n\n## Group summary\n\n```\n{group_summary.to_string(index=False)}\n```\n\n## Top clusters\n\n```\n{cluster_summary.head(15).to_string(index=False)}\n```\n"""
    (report_dir / "EMBEDDING_REPORT.md").write_text(report)
    print("DONE", report_dir)


if __name__ == "__main__":
    main()
