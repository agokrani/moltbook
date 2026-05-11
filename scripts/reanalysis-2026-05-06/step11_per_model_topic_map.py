#!/usr/bin/env python3
"""Step 11: per-model topic map -- free-flow MDS small multiples.

Per-model figure with the original "Topic Map -- MDS Projection" layout
(rows=scale, cols=condition), with the projection done by classical MDS on
cosine distance (== TruncatedSVD-2 of L2-normalized embeddings) instead of
softmax-barycentric onto a polygon. No fixed anchors, no vertex layout --
points live freely in the 2-D MDS basis derived from that model's own
posts. Cluster labels (LLM-judge dominant_frame text -> KMeans -> top
keywords) are placed at the in-MDS centroid of each cluster.

Pipeline (per model):
    1. Pull all frame embeddings for the model's LLM-judged posts.
    2. KMeans (k=8 default) on L2-normalized vectors -> cluster labels.
       Compute silhouette score (cosine) on a 5k subsample.
    3. Derive cluster keyword labels from the dominant_frame strings in
       each cluster (most discriminative words vs the global model corpus).
    4. Fit TruncatedSVD-2 on the model's L2-normalized embeddings -> 2-D
       coords shared across all panels.
    5. Render small multiples: rows=scale, cols=condition. Each panel
       shows that subset's points colored by KMeans cluster, with the
       cluster centroid label overlaid.

Output:
    step11_per_model_topic_map/
        <model>.png
        <model>_cluster_labels.csv
        per_model_silhouette.csv

Usage:
    python3 step11_per_model_topic_map.py
    python3 step11_per_model_topic_map.py --k 8 --models gpt-5
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
from collections import Counter
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import normalize

DEFAULT_ANALYSIS_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook/analysis/archive-2026-plus-canonical-gemini")
DEFAULT_PLOT_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook-findings-handoff/findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map")
EMBED_MODEL = "qwen/qwen3-embedding-8b"

CLUSTER_PALETTE = [
    "#2563EB",  # C1  blue
    "#DC2626",  # C2  red
    "#059669",  # C3  green
    "#D97706",  # C4  orange
    "#7C3AED",  # C5  purple
    "#0891B2",  # C6  cyan
    "#F59E0B",  # C7  amber (was dark red, too close to C2)
    "#65A30D",  # C8  lime
    "#9333EA",  # spare
    "#0EA5E9",
    "#C026D3",
    "#475569",
]

STOP_TOKENS = {
    "the", "and", "of", "in", "to", "a", "as", "is", "on", "for", "with",
    "by", "an", "or", "that", "this", "from", "at", "be", "are", "was",
    "it", "its", "a.k.a", "via", "vs", "vs.", "into", "about", "across",
    "through", "between", "without", "within", "while", "where", "when",
    "what", "which", "who", "how", "why", "discussion", "post", "posts",
    "framing", "frame", "framework", "frames", "topic", "topics", "such",
    "claim", "claims", "social", "online", "users", "based", "user",
}

MODEL_DISPLAY = {
    "google/gemini-3.1-flash-lite-preview": "Gemini 3.1 Flash Lite",
    "gpt-5": "GPT-5",
    "moonshotai/kimi-k2.5": "Kimi K2.5",
    "z-ai/glm-5": "GLM-5",
    "olmo-3-32b-base": "Olmo-3-32B Base",
    "olmo-3-32b-instruct": "Olmo-3-32B Instruct",
    "qwen-3.5-35b-a3b-base": "Qwen 3.5-35B A3B Base",
    "mixed-roster/qwen3.5-27b": "Qwen 3.5-27B (mixed roster)",
}

CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed (mag0)",
    "mag1": "1 conspiracy (mag1)",
    "mag5": "5 conspiracies (mag5)",
    "mag25": "25 conspiracies (mag25)",
    "dom-agi": "AGI dominance (dom-agi)",
    "dom-tech": "Tech dominance (dom-tech)",
}
SCALE_ORDER = ["n10", "n20", "n30"]


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


def load_frame_assignments(root: Path) -> pd.DataFrame:
    p = root / "ayush_reanalysis/llm_frame_topic_convergence/frame_topic_assignments.csv"
    df = pd.read_csv(p)
    df["record_id"] = df["record_id"].astype(str)
    df["text_sha1"] = df["dominant_frame"].astype(str).map(sha1_text)
    return df


def load_frame_embeddings(root: Path) -> dict[str, np.ndarray]:
    db = root / "ayush_reanalysis/llm_frame_topic_convergence/frame_embedding_cache.sqlite"
    conn = sqlite3.connect(db)
    out: dict[str, np.ndarray] = {}
    for sha, dim, blob in conn.execute(
        "SELECT text_sha1, dim, embedding FROM frame_embeddings WHERE model=?",
        (EMBED_MODEL,),
    ):
        out[sha] = np.frombuffer(blob, dtype=np.float32, count=int(dim)).copy()
    conn.close()
    return out


# --------------------------------------------------------------------------
# clustering + labels
# --------------------------------------------------------------------------

def kmeans_cosine(emb_n: np.ndarray, k: int, seed: int = 0) -> tuple[np.ndarray, np.ndarray, float]:
    """KMeans on already-L2-normalized vectors. Returns (labels, centroids,
    silhouette_cosine_subsample)."""
    km = KMeans(n_clusters=k, n_init=10, random_state=seed)
    labels = km.fit_predict(emb_n)
    centroids = normalize(km.cluster_centers_, norm="l2", copy=False)
    if len(emb_n) > 5000:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(emb_n), size=5000, replace=False)
        sil = float(silhouette_score(emb_n[idx], labels[idx], metric="cosine"))
    else:
        sil = float(silhouette_score(emb_n, labels, metric="cosine"))
    return labels, centroids, sil


_TOK_RE = re.compile(r"[a-z][a-z'-]{2,}", re.IGNORECASE)


def tokenize_for_label(text: str) -> list[str]:
    return [t.lower() for t in _TOK_RE.findall(text or "")]


def derive_cluster_labels(frames: pd.Series, labels: np.ndarray, k: int,
                           top_n: int = 2) -> dict[int, str]:
    cluster_tf: list[Counter] = [Counter() for _ in range(k)]
    global_tf: Counter = Counter()
    for frame, c in zip(frames.tolist(), labels.tolist()):
        toks = [t for t in tokenize_for_label(frame) if t not in STOP_TOKENS]
        cluster_tf[c].update(toks)
        global_tf.update(toks)
    total = sum(global_tf.values()) or 1
    out: dict[int, str] = {}
    for c in range(k):
        local = cluster_tf[c]
        local_total = sum(local.values()) or 1
        scored = []
        for tok, cnt in local.most_common(80):
            local_p = cnt / local_total
            global_p = global_tf[tok] / total
            scored.append((local_p - global_p, tok, cnt))
        scored.sort(reverse=True)
        chosen, seen = [], set()
        for _, tok, _ in scored:
            stem = tok[:5]
            if stem in seen:
                continue
            seen.add(stem)
            chosen.append(tok)
            if len(chosen) >= top_n:
                break
        out[c] = ", ".join(chosen).title() if chosen else f"cluster {c+1}"
    return out


# --------------------------------------------------------------------------
# plot
# --------------------------------------------------------------------------

def setup_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 11,
        "savefig.dpi": 200,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": "white",
    })


def plot_panel(ax: plt.Axes, xy_sub: np.ndarray, lab_sub: np.ndarray, k: int,
                xlim: tuple[float, float], ylim: tuple[float, float],
                cluster_centroids_2d: np.ndarray, cluster_labels: dict[int, str],
                title: str, draw_labels: bool,
                ghost_xy: np.ndarray | None) -> None:
    ax.set_facecolor("#fafafa")
    if ghost_xy is not None and len(ghost_xy) >= 50:
        ax.hexbin(ghost_xy[:, 0], ghost_xy[:, 1], gridsize=70, mincnt=1,
                   cmap="Greys", alpha=0.18, linewidths=0,
                   extent=(xlim[0], xlim[1], ylim[0], ylim[1]), zorder=0)
    n = len(xy_sub)
    pt_size = 10.0 if n > 1500 else (14.0 if n > 400 else 18.0)
    pt_alpha = 0.45 if n > 1500 else (0.55 if n > 400 else 0.7)
    for c in range(k):
        sel = lab_sub == c
        if not sel.any():
            continue
        ax.scatter(xy_sub[sel, 0], xy_sub[sel, 1],
                    s=pt_size, color=CLUSTER_PALETTE[c % len(CLUSTER_PALETTE)],
                    alpha=pt_alpha, edgecolor="none", zorder=2)
    if draw_labels:
        for c in range(k):
            cx, cy = cluster_centroids_2d[c]
            if not (xlim[0] <= cx <= xlim[1] and ylim[0] <= cy <= ylim[1]):
                continue
            color = CLUSTER_PALETTE[c % len(CLUSTER_PALETTE)]
            ax.text(cx, cy, f"C{c+1}", color="white", fontsize=8.0,
                    weight="bold", ha="center", va="center", zorder=6,
                    bbox=dict(facecolor=color, edgecolor="white",
                              boxstyle="circle,pad=0.25", linewidth=0.8))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(0.4)
        spine.set_edgecolor("#d1d5db")
    ax.set_title(title, fontsize=10)


def render_model_figure(model: str, scale_to_conditions: dict[str, list[str]],
                         points_by_cell: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]],
                         k: int, cluster_labels: dict[int, str],
                         cluster_centroids_2d: np.ndarray,
                         xlim: tuple[float, float], ylim: tuple[float, float],
                         silhouette: float, var_explained: float,
                         n_total: int, out_path: Path,
                         ghost_xy: np.ndarray | None = None) -> None:
    scales_present = [s for s in SCALE_ORDER if s in scale_to_conditions]
    cond_set = sorted({c for cs in scale_to_conditions.values() for c in cs},
                       key=lambda c: CONDITION_ORDER.index(c)
                       if c in CONDITION_ORDER else 99)
    rows = max(1, len(scales_present))
    cols = max(1, len(cond_set))
    panel_h = 3.2
    title_pad = 1.3
    legend_pad = 1.0
    fig_h = rows * panel_h + title_pad + legend_pad
    fig, axes = plt.subplots(rows, cols,
                              figsize=(cols * 3.0, fig_h),
                              squeeze=False, sharex=True, sharey=True)
    title_y = 1.0 - 0.32 / fig_h
    subtitle_y = title_y - 0.55 / fig_h
    legend_y = (legend_pad / fig_h) * 0.45

    for r, scale in enumerate(scales_present):
        for c, cond in enumerate(cond_set):
            ax = axes[r][c]
            key = (scale, cond)
            if key in points_by_cell:
                xy_sub, lab_sub = points_by_cell[key][:2]
                title = f"{CONDITION_LABELS.get(cond, cond)}  n={len(xy_sub)}"
                plot_panel(ax, xy_sub, lab_sub, k, xlim, ylim,
                            cluster_centroids_2d, cluster_labels, title,
                            draw_labels=(c == 0),
                            ghost_xy=ghost_xy)
            else:
                ax.set_axis_off()
        axes[r][0].set_ylabel(scale, fontsize=12, weight="bold",
                                color="#374151", labelpad=8)

    display = MODEL_DISPLAY.get(model, model)
    fig.suptitle(display, fontsize=15, weight="bold", y=title_y)

    handles = [
        plt.Line2D([0], [0], marker="o", color="w",
                    markerfacecolor=CLUSTER_PALETTE[c % len(CLUSTER_PALETTE)],
                    markeredgecolor="#222", markersize=10,
                    label=f"C{c+1}: {cluster_labels.get(c, '')}")
        for c in range(k)
    ]
    legend_cols = min(k, 4)
    fig.legend(handles=handles, loc="lower center", ncol=legend_cols,
                bbox_to_anchor=(0.5, legend_y), frameon=False,
                fontsize=10)
    fig.tight_layout(rect=(0, legend_pad / fig_h + 0.01, 1,
                            title_y - 0.6 / fig_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path.with_suffix(".png"), bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def slugify(s: str) -> str:
    s = re.sub(r"[/\\:]+", "_", s or "unknown")
    s = re.sub(r"\s+", "_", s)
    s = s.replace(".", "_")
    s = re.sub(r"[^A-Za-z0-9_\-]+", "_", s)
    return s.strip("_-") or "unknown"


def run_ksweep(df: pd.DataFrame, emb_map: dict[str, np.ndarray],
                k_values: list[int], out_csv: Path) -> None:
    """Per-model silhouette as K is swept. Lets readers see whether K=8 is
    near a peak, on a flat plateau, or well below the optimum."""
    rows = []
    for model, mdf in df.groupby("model_family"):
        n_model = len(mdf)
        if n_model < max(k_values) * 5:
            print(f"[{model}] skipped: only {n_model} posts", flush=True)
            continue
        emb_mat = np.vstack([emb_map[s] for s in mdf["text_sha1"]]).astype(np.float32)
        emb_n = normalize(emb_mat, norm="l2", copy=False)
        for k in k_values:
            if n_model < k * 5:
                continue
            _, _, sil = kmeans_cosine(emb_n, k)
            print(f"[{model}] k={k:2d}  silhouette={sil:.3f}  (n={n_model})", flush=True)
            rows.append({"model_family": model, "n_posts": n_model,
                         "k": k, "silhouette_cosine": sil})
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(out_csv, index=False, lineterminator="\n")
    print(f"\nwrote K-sweep silhouette table -> {out_csv}", flush=True)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    ap.add_argument("--plot-root", type=Path, default=DEFAULT_PLOT_ROOT)
    ap.add_argument("--models", default="", help="Comma-separated model_family allowlist")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--min-posts-per-cell", type=int, default=8)
    ap.add_argument("--ksweep", default="",
                     help="Comma-separated K values to sweep silhouette over. "
                          "If set, the script runs the sweep and exits (no plots).")
    args = ap.parse_args()

    setup_style()
    args.plot_root.mkdir(parents=True, exist_ok=True)

    print("loading LLM-judge frame assignments...", flush=True)
    df = load_frame_assignments(args.analysis_root)
    if args.models.strip():
        allow = {m.strip() for m in args.models.split(",") if m.strip()}
        df = df[df["model_family"].isin(allow)].copy().reset_index(drop=True)
    print(f"  {len(df):,} judged posts across {df.model_family.nunique()} models", flush=True)

    print("loading frame embeddings...", flush=True)
    emb_map = load_frame_embeddings(args.analysis_root)
    df = df[df["text_sha1"].isin(emb_map.keys())].copy().reset_index(drop=True)
    print(f"  {len(df):,} posts with available frame embeddings", flush=True)

    if args.ksweep.strip():
        k_values = [int(v.strip()) for v in args.ksweep.split(",") if v.strip()]
        run_ksweep(df, emb_map, k_values, args.plot_root / "ksweep_silhouette.csv")
        return

    silhouette_rows = []

    for model, mdf in df.groupby("model_family"):
        n_model = len(mdf)
        if n_model < args.k * 5:
            print(f"\n[{model}] skipped: only {n_model} posts (< {args.k*5})", flush=True)
            continue
        print(f"\n[{model}] {n_model:,} posts -> KMeans k={args.k}", flush=True)

        emb_mat = np.vstack([emb_map[s] for s in mdf["text_sha1"]]).astype(np.float32)
        emb_n = normalize(emb_mat, norm="l2", copy=False)

        labels, centroids, silhouette = kmeans_cosine(emb_n, args.k)
        print(f"  silhouette (cosine, sample) = {silhouette:.3f}", flush=True)

        cluster_labels = derive_cluster_labels(mdf["dominant_frame"], labels, args.k)
        for c in range(args.k):
            n_c = int((labels == c).sum())
            print(f"    C{c+1}: {cluster_labels[c]:<35} n={n_c}", flush=True)

        pd.DataFrame([
            {"model_family": model, "cluster_id": c + 1, "label": cluster_labels[c],
             "size": int((labels == c).sum())}
            for c in range(args.k)
        ]).to_csv(args.plot_root / f"{slugify(model)}_cluster_labels.csv",
                   index=False, lineterminator="\n")

        # Joint PCA on centered, L2-normalized embeddings == classical
        # MDS on cosine distance. Shared 2-D basis across all panels for
        # this model, so panel-to-panel comparisons are well defined.
        pca = PCA(n_components=2, random_state=0)
        xy_all = pca.fit_transform(emb_n).astype(np.float32)
        var_explained = float(pca.explained_variance_ratio_.sum())
        print(f"  joint PCA-2 (== MDS on cosine)  var_explained={var_explained:.3f}",
               flush=True)

        # Joint axis limits from the 0.5-99.5 percentile so a handful
        # of outliers don't squash the bulk of the cloud.
        q_lo, q_hi = 0.005, 0.995
        x_lo = float(np.quantile(xy_all[:, 0], q_lo))
        x_hi = float(np.quantile(xy_all[:, 0], q_hi))
        y_lo = float(np.quantile(xy_all[:, 1], q_lo))
        y_hi = float(np.quantile(xy_all[:, 1], q_hi))
        # Same scale on both axes -> equal aspect doesn't squish one of them
        half = 0.55 * max(x_hi - x_lo, y_hi - y_lo)
        cx0 = 0.5 * (x_lo + x_hi)
        cy0 = 0.5 * (y_lo + y_hi)
        xlim = (cx0 - half, cx0 + half)
        ylim = (cy0 - half, cy0 + half)

        centroids_2d = np.zeros((args.k, 2), dtype=np.float32)
        for c in range(args.k):
            sel = labels == c
            if sel.any():
                centroids_2d[c] = xy_all[sel].mean(axis=0)

        mdf = mdf.copy().reset_index(drop=True)
        mdf["__cluster__"] = labels.astype(np.int8)

        scale_to_conditions: dict[str, list[str]] = {}
        points_by_cell: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
        for (scale, cond), sub in mdf.groupby(["scale", "condition"]):
            if len(sub) < args.min_posts_per_cell:
                continue
            scale_to_conditions.setdefault(scale, []).append(cond)
            cell_xy = xy_all[sub.index.to_numpy()]
            lab_sub = sub["__cluster__"].to_numpy()
            points_by_cell[(scale, cond)] = (cell_xy, lab_sub)

        out_path = args.plot_root / slugify(model)
        render_model_figure(model, scale_to_conditions, points_by_cell, args.k,
                             cluster_labels, centroids_2d, xlim, ylim,
                             silhouette, var_explained, n_model, out_path,
                             ghost_xy=xy_all)
        print(f"  wrote {out_path.with_suffix('.png').name}", flush=True)

        silhouette_rows.append({
            "model_family": model,
            "n_posts": n_model,
            "k": args.k,
            "silhouette_cosine": silhouette,
            "svd2_var_explained": var_explained,
            **{f"size_C{c+1}": int((labels == c).sum()) for c in range(args.k)},
        })

    pd.DataFrame(silhouette_rows).sort_values("silhouette_cosine", ascending=False).to_csv(
        args.plot_root / "per_model_silhouette.csv",
        index=False, lineterminator="\n",
    )
    print(f"\nwrote {len(silhouette_rows)} per-model figures to {args.plot_root}", flush=True)


if __name__ == "__main__":
    main()
