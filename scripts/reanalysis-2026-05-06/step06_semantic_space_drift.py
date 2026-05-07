#!/usr/bin/env python3
"""Step 6: 2-D semantic space drift by family.

Fits a single TruncatedSVD-2 basis per input space (post text OR LLM-judge
dominant_frame), then draws a 2x2 family grid where each panel shows:

    - all points in that family colored by run-time quartile (Q1..Q4),
    - 50% Gaussian-KDE contour per quartile,
    - one centroid marker per quartile,
    - an arrow from Q1 centroid to Q4 centroid,
    - the L2 distance ||Q4 - Q1|| in the 2-D basis as a numeric annotation.

This is the "clouds shrinking and drifting" view: same operator (TruncatedSVD-2)
on two parallel inputs gives convergent visual evidence for collapse.

Usage:
    python3 step06_semantic_space_drift.py --input-type post
    python3 step06_semantic_space_drift.py --input-type frame
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import to_rgba
from scipy.stats import gaussian_kde
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

DEFAULT_ANALYSIS_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook/analysis/archive-2026-plus-canonical-gemini")
DEFAULT_PLOT_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook-findings-handoff/findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step06_semantic_space_drift")
EMBED_MODEL = "qwen/qwen3-embedding-8b"

FAMILY_ORDER = ["single_model_final", "base_model_as_tool", "obsession_prompting", "mixed_model_roster"]
FAMILY_LABELS = {
    "single_model_final": "Single-model final",
    "base_model_as_tool": "Base model as tool",
    "obsession_prompting": "Obsession prompting",
    "mixed_model_roster": "Mixed-model roster",
}
QUARTILE_BINS = [(0.0, 0.25, "Q1"), (0.25, 0.5, "Q2"), (0.5, 0.75, "Q3"), (0.75, 1.001, "Q4")]
QUARTILE_COLORS = ["#fde725", "#5ec962", "#21918c", "#3b528b"]  # viridis 4-step, Q1->Q4


def setup_style() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.titlesize": 13,
        "axes.labelsize": 11,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "savefig.dpi": 240,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def save_fig(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(path.with_suffix(f".{ext}"), bbox_inches="tight")
    plt.close(fig)


# --------------------------------------------------------------------------
# data loaders
# --------------------------------------------------------------------------

def load_post_index(root: Path) -> pd.DataFrame:
    rows = []
    with (root / "ayush_reanalysis/post_index.jsonl").open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    df = pd.DataFrame(rows)
    df = df[~df["is_seed"].astype(bool)].copy()
    df["record_id"] = df["record_id"].astype(str)
    return df.drop_duplicates("record_id").reset_index(drop=True)


def load_post_embeddings(root: Path, record_ids: list[str]) -> dict[str, np.ndarray]:
    db = root / "embedding_cache.sqlite"
    conn = sqlite3.connect(db)
    have = set(record_ids)
    out: dict[str, np.ndarray] = {}
    for rid, dim, blob in conn.execute(
        "SELECT record_id, dim, embedding FROM embeddings WHERE model=?", (EMBED_MODEL,),
    ):
        rid = str(rid)
        if rid in have:
            out[rid] = np.frombuffer(blob, dtype=np.float32, count=int(dim)).copy()
    conn.close()
    return out


def load_frame_embeddings(root: Path) -> dict[str, np.ndarray]:
    db = root / "ayush_reanalysis/llm_frame_topic_convergence/frame_embedding_cache.sqlite"
    conn = sqlite3.connect(db)
    out: dict[str, np.ndarray] = {}
    for sha, dim, blob in conn.execute(
        "SELECT text_sha1, dim, embedding FROM frame_embeddings WHERE model=?", (EMBED_MODEL,),
    ):
        out[str(sha)] = np.frombuffer(blob, dtype=np.float32, count=int(dim)).copy()
    conn.close()
    return out


def build_post_dataset(root: Path) -> tuple[pd.DataFrame, np.ndarray]:
    pi = load_post_index(root)
    emb = load_post_embeddings(root, pi["record_id"].to_list())
    pi = pi[pi["record_id"].isin(emb.keys())].copy().reset_index(drop=True)
    mat = np.vstack([emb[r] for r in pi["record_id"]]).astype(np.float32)
    return pi, mat


def build_frame_dataset(root: Path) -> tuple[pd.DataFrame, np.ndarray]:
    judge_csv = root / "ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv"
    cols = ["record_id", "run_uid", "internal_family_label", "minutes_elapsed",
            "normalized_time", "dominant_frame"]
    df = pd.read_csv(judge_csv, usecols=cols, low_memory=False)
    df = df.dropna(subset=["dominant_frame"]).copy()
    df["dominant_frame"] = df["dominant_frame"].astype(str).str.strip()
    df = df[df["dominant_frame"].str.len() > 0].copy()
    import hashlib
    df["text_sha1"] = df["dominant_frame"].map(
        lambda v: hashlib.sha1(v.encode("utf-8", errors="ignore")).hexdigest()
    )
    emb = load_frame_embeddings(root)
    df = df[df["text_sha1"].isin(emb.keys())].copy().reset_index(drop=True)
    mat = np.vstack([emb[s] for s in df["text_sha1"]]).astype(np.float32)
    return df, mat


# --------------------------------------------------------------------------
# 2-D projection + KDE
# --------------------------------------------------------------------------

def project_2d(mat: np.ndarray, seed: int = 42) -> tuple[np.ndarray, TruncatedSVD]:
    mat = normalize(mat, norm="l2", copy=False)
    svd = TruncatedSVD(n_components=2, random_state=seed)
    z = svd.fit_transform(mat).astype(np.float32)
    return z, svd


def kde_50_contour(ax: plt.Axes, points: np.ndarray, color: str,
                    grid_n: int = 80, levels_pct: tuple[int, ...] = (50,),
                    bbox: tuple[float, float, float, float] | None = None,
                    rng: np.random.Generator | None = None,
                    max_kde_points: int = 3000) -> None:
    """Draw KDE contour(s) at the requested probability-mass levels."""
    if len(points) < 8:
        return
    sample = points
    if len(sample) > max_kde_points and rng is not None:
        idx = rng.choice(len(sample), size=max_kde_points, replace=False)
        sample = sample[idx]
    try:
        kde = gaussian_kde(sample.T)
    except (np.linalg.LinAlgError, ValueError):
        return
    if bbox is None:
        x_lo, y_lo = sample.min(axis=0)
        x_hi, y_hi = sample.max(axis=0)
    else:
        x_lo, x_hi, y_lo, y_hi = bbox
    xx, yy = np.meshgrid(np.linspace(x_lo, x_hi, grid_n), np.linspace(y_lo, y_hi, grid_n))
    grid = np.vstack([xx.ravel(), yy.ravel()])
    zz = kde(grid).reshape(xx.shape)
    flat = np.sort(zz.ravel())[::-1]
    cumulative = np.cumsum(flat)
    cumulative /= cumulative[-1]
    levels = []
    for pct in levels_pct:
        target = pct / 100.0
        idx = int(np.searchsorted(cumulative, target))
        idx = min(idx, len(flat) - 1)
        levels.append(float(flat[idx]))
    levels = sorted(set(levels))
    if not levels:
        return
    ax.contour(xx, yy, zz, levels=levels, colors=[color] * len(levels),
               linewidths=1.5, alpha=0.95)


# --------------------------------------------------------------------------
# main panel logic
# --------------------------------------------------------------------------

def assign_quartile(normalized_time: pd.Series) -> pd.Series:
    out = pd.Series(index=normalized_time.index, dtype=object)
    nt = normalized_time.astype(float)
    for lo, hi, label in QUARTILE_BINS:
        mask = (nt >= lo) & (nt < hi)
        out.loc[mask] = label
    return out


def compute_global_bbox(z: np.ndarray, family_mask: np.ndarray, pad: float = 0.05) -> tuple[float, float, float, float]:
    pts = z[family_mask]
    x_lo, y_lo = pts.min(axis=0)
    x_hi, y_hi = pts.max(axis=0)
    dx, dy = (x_hi - x_lo) * pad, (y_hi - y_lo) * pad
    return float(x_lo - dx), float(x_hi + dx), float(y_lo - dy), float(y_hi + dy)


def plot_family_panel(ax: plt.Axes, z: np.ndarray, df: pd.DataFrame,
                       family: str, bbox: tuple[float, float, float, float],
                       rng: np.random.Generator) -> dict[str, float]:
    mask_fam = df["internal_family_label"].to_numpy() == family
    pts_fam = z[mask_fam]
    quart_fam = df.loc[mask_fam, "quartile"].to_numpy()
    centroids = {}
    for color, (_, _, label) in zip(QUARTILE_COLORS, QUARTILE_BINS):
        sel = quart_fam == label
        pts = pts_fam[sel]
        if len(pts) == 0:
            continue
        # Underlay dots
        ax.scatter(pts[:, 0], pts[:, 1], s=2, color=color, alpha=0.15, linewidths=0)
        # 50% KDE contour
        kde_50_contour(ax, pts, color=color, bbox=bbox, rng=rng, levels_pct=(50,))
        # Centroid
        centroid = pts.mean(axis=0)
        centroids[label] = centroid
        ax.scatter([centroid[0]], [centroid[1]], s=140,
                    color=color, edgecolor="#111", linewidth=1.2, zorder=5)
        ax.text(centroid[0], centroid[1], label,
                color="#111", weight="bold", fontsize=8, ha="center", va="center", zorder=6)
    # Q1->Q4 arrow
    drift = math.nan
    if "Q1" in centroids and "Q4" in centroids:
        q1 = centroids["Q1"]
        q4 = centroids["Q4"]
        ax.annotate("", xy=(q4[0], q4[1]), xytext=(q1[0], q1[1]),
                    arrowprops=dict(arrowstyle="-|>", color="#111", linewidth=1.6,
                                     mutation_scale=18, alpha=.9), zorder=4)
        drift = float(np.linalg.norm(q4 - q1))
    n_runs = int(df.loc[mask_fam, "run_uid"].nunique())
    n_posts = int(mask_fam.sum())
    label_text = f"{FAMILY_LABELS.get(family, family)}\nn runs = {n_runs}, n posts = {n_posts:,}"
    if np.isfinite(drift):
        label_text += f"\n‖Q4−Q1‖ = {drift:.3f}"
    ax.set_title(label_text, fontsize=11.5, loc="left")
    ax.set_xlim(bbox[0], bbox[1])
    ax.set_ylim(bbox[2], bbox[3])
    ax.grid(alpha=.18)
    return {"centroid_drift_l2": drift, "n_posts": n_posts, "n_runs": n_runs}


FAMILY_ACCENTS = {
    "single_model_final": "#3b6ea8",
    "base_model_as_tool": "#d94f4f",
    "obsession_prompting": "#7e57c2",
    "mixed_model_roster": "#2e8b57",
}


def plot_centroid_trajectories(z: np.ndarray, df: pd.DataFrame, title: str,
                                 subtitle: str, out_path: Path) -> None:
    """Zoomed view: centroid Q1->Q4 trajectories for all families on one axes.

    The full-cloud grid hides the drift because cloud span >> centroid drift.
    This complementary figure drops the dots entirely and zooms onto the
    centroid trajectories, with KDE 50% rings drawn at the per-family scale.
    """
    fig, ax = plt.subplots(figsize=(9.5, 8.0))
    rng = np.random.default_rng(42)
    rows = []
    for family in FAMILY_ORDER:
        mask_fam = df["internal_family_label"].to_numpy() == family
        if not mask_fam.any():
            continue
        pts_fam = z[mask_fam]
        quart_fam = df.loc[mask_fam, "quartile"].to_numpy()
        accent = FAMILY_ACCENTS[family]
        traj = []
        for color, (_, _, label) in zip(QUARTILE_COLORS, QUARTILE_BINS):
            sel = quart_fam == label
            pts = pts_fam[sel]
            if len(pts) == 0:
                continue
            centroid = pts.mean(axis=0)
            traj.append((label, centroid, color, len(pts)))
        if len(traj) < 2:
            continue
        xs = [c[1][0] for c in traj]
        ys = [c[1][1] for c in traj]
        ax.plot(xs, ys, color=accent, linewidth=2.0, alpha=0.55, zorder=2)
        for label, centroid, qcolor, n in traj:
            ax.scatter([centroid[0]], [centroid[1]], s=180,
                        color=qcolor, edgecolor=accent, linewidth=2.0, zorder=4)
            ax.text(centroid[0], centroid[1], label,
                    color="#111", weight="bold", fontsize=8,
                    ha="center", va="center", zorder=5)
        # Q1->Q4 dashed arrow per family, accent color
        if traj[0][0] == "Q1" and traj[-1][0] == "Q4":
            ax.annotate("", xy=traj[-1][1], xytext=traj[0][1],
                        arrowprops=dict(arrowstyle="-|>", color=accent,
                                         linewidth=1.6, mutation_scale=18, alpha=.9),
                        zorder=3)
            drift = float(np.linalg.norm(traj[-1][1] - traj[0][1]))
            mid = (traj[0][1] + traj[-1][1]) / 2
            ax.annotate(f"{FAMILY_LABELS[family]}  ‖Q4−Q1‖={drift:.3f}",
                        xy=mid, xytext=(8, 8), textcoords="offset points",
                        color=accent, fontsize=9, weight="bold")
            rows.append({"family": family, "drift": drift})
    ax.grid(alpha=.25)
    ax.set_xlabel("SVD component 1")
    ax.set_ylabel("SVD component 2")
    fig.suptitle(title, fontsize=14, y=0.995)
    fig.text(0.5, 0.955, subtitle, ha="center", va="top", fontsize=10, color="#444")
    qlegend = [plt.Line2D([0], [0], marker="o", color="w",
                            markerfacecolor=c, markeredgecolor="#222",
                            markersize=10, label=label)
                for c, (_, _, label) in zip(QUARTILE_COLORS, QUARTILE_BINS)]
    flegend = [plt.Line2D([0], [0], color=c, linewidth=2.4, label=FAMILY_LABELS[f])
                for f, c in FAMILY_ACCENTS.items() if f in set(df["internal_family_label"])]
    leg1 = ax.legend(handles=qlegend, title="Quartile", loc="upper left",
                      frameon=True, framealpha=0.92, fontsize=9, title_fontsize=9)
    leg1.get_frame().set_edgecolor("#bbb")
    ax.add_artist(leg1)
    leg2 = ax.legend(handles=flegend, title="Family (arrow color)", loc="lower left",
                      frameon=True, framealpha=0.92, fontsize=9, title_fontsize=9)
    leg2.get_frame().set_edgecolor("#bbb")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save_fig(fig, out_path)


def plot_grid(z: np.ndarray, df: pd.DataFrame, title: str, subtitle: str,
              out_path: Path) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(42)
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 11), sharex=True, sharey=True)
    bbox = compute_global_bbox(z, np.ones(len(df), dtype=bool))
    summary: dict[str, dict[str, float]] = {}
    for ax, family in zip(axes.flat, FAMILY_ORDER):
        if family not in set(df["internal_family_label"]):
            ax.set_axis_off()
            continue
        summary[family] = plot_family_panel(ax, z, df, family, bbox, rng)
    for ax in axes[-1]:
        ax.set_xlabel("SVD component 1")
    for ax in axes[:, 0]:
        ax.set_ylabel("SVD component 2")
    handles = [plt.Line2D([0], [0], marker="o", color="w",
                           markerfacecolor=c, markeredgecolor="#111",
                           markersize=10, label=label)
               for c, (_, _, label) in zip(QUARTILE_COLORS, QUARTILE_BINS)]
    fig.legend(handles=handles, loc="upper center", ncol=4,
                bbox_to_anchor=(0.5, 1.005), frameon=False)
    fig.suptitle(title, y=1.045, fontsize=15)
    fig.text(0.5, 1.018, subtitle, ha="center", va="bottom", fontsize=10.5, color="#444")
    fig.tight_layout()
    save_fig(fig, out_path)
    return summary


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT)
    ap.add_argument("--plot-root", type=Path, default=DEFAULT_PLOT_ROOT)
    ap.add_argument("--input-type", choices=("post", "frame", "both"), default="both")
    args = ap.parse_args()

    setup_style()
    args.plot_root.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []

    if args.input_type in ("post", "both"):
        print("loading post embeddings...", flush=True)
        df, mat = build_post_dataset(args.analysis_root)
        print(f"  posts: {len(df):,}, dims: {mat.shape}", flush=True)
        z, svd = project_2d(mat)
        print(f"  SVD-2 explained variance: {svd.explained_variance_ratio_.sum():.3%}", flush=True)
        df["quartile"] = assign_quartile(df["normalized_time"])
        summary = plot_grid(
            z, df,
            title="Post-text embedding space drifts toward an attractor",
            subtitle=f"TruncatedSVD-2 on Qwen3-embedding-8b, fit on all {len(df):,} non-seed posts. "
                    f"Q1..Q4 by normalized run time.",
            out_path=args.plot_root / "post_text_family_drift",
        )
        plot_centroid_trajectories(
            z, df,
            title="Post-text centroid drift Q1 → Q4 by family",
            subtitle="Zoomed onto centroid trajectories. Dot color = quartile, ring/arrow color = family.",
            out_path=args.plot_root / "post_text_centroid_drift",
        )
        for fam, st in summary.items():
            summaries.append({"input": "post_text", "family": fam, **st,
                              "svd_explained_variance": float(svd.explained_variance_ratio_.sum())})

    if args.input_type in ("frame", "both"):
        print("loading frame embeddings...", flush=True)
        df, mat = build_frame_dataset(args.analysis_root)
        print(f"  judged posts (with frame): {len(df):,}, dims: {mat.shape}", flush=True)
        z, svd = project_2d(mat)
        print(f"  SVD-2 explained variance: {svd.explained_variance_ratio_.sum():.3%}", flush=True)
        df["quartile"] = assign_quartile(df["normalized_time"])
        summary = plot_grid(
            z, df,
            title="LLM-judge frame space drifts toward an attractor",
            subtitle=f"TruncatedSVD-2 on Qwen3-embedding-8b applied to dominant_frame strings; "
                    f"{len(df):,} judged posts. Q1..Q4 by normalized run time.",
            out_path=args.plot_root / "frame_family_drift",
        )
        plot_centroid_trajectories(
            z, df,
            title="Frame centroid drift Q1 → Q4 by family",
            subtitle="Zoomed onto centroid trajectories of LLM-judge dominant_frame embeddings.",
            out_path=args.plot_root / "frame_centroid_drift",
        )
        for fam, st in summary.items():
            summaries.append({"input": "frame", "family": fam, **st,
                              "svd_explained_variance": float(svd.explained_variance_ratio_.sum())})

    pd.DataFrame(summaries).to_csv(args.plot_root / "drift_summary.csv",
                                    index=False, lineterminator="\n")
    print(f"wrote step06 outputs to {args.plot_root}", flush=True)


if __name__ == "__main__":
    main()
