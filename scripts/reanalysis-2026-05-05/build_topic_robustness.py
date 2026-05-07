#!/usr/bin/env python3
"""Topic-cluster robustness sweep for the 2026-05-05 MoltBook reanalysis.

This script does NOT make new API calls. It uses the cleaned Qwen embedding NPZ
from the HF reanalysis bundle and reruns unsupervised embedding clustering across
multiple k values and random seeds.

Outputs are written to:
  findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness/

The goal is not to turn k-means clusters into validated human topics. The goal is
to test whether topic/cluster concentration directions are stable under reasonable
cluster-count and random-initialization perturbations.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

DATA_ROOT = Path("data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini")
DEFAULT_EMBED_NPZ = DATA_ROOT / "embeddings/qwen-qwen3-embedding-8b-current-included-unique.npz"
DEFAULT_POST_INDEX = DATA_ROOT / "ayush_reanalysis/post_index.csv"
DEFAULT_OUT = Path("findings/emnlp-2026-paper/plots/reanalysis-2026-05-05/topic_robustness")

K_VALUES = [8, 12, 16, 24]
SEEDS = [11, 22, 33, 44, 55]
SVD_COMPONENTS = 50

CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy seed",
    "mag5": "5 conspiracy seeds",
    "mag25": "25 conspiracy seeds",
    "dom-agi": "25 AGI seeds",
    "dom-tech": "25 tech seeds",
}
MODEL_ORDER = ["GPT-5", "Gemini Flash Lite", "Kimi K2.5", "GLM-5"]
SCALE_ORDER = [10, 20, 30]

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)
STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were", "will", "would", "could", "should",
    "have", "has", "had", "not", "but", "you", "your", "our", "their", "they", "them", "its", "it's", "into",
    "about", "what", "when", "where", "which", "while", "there", "here", "than", "then", "also", "just", "like",
    "can", "may", "might", "more", "most", "some", "any", "all", "one", "two", "new", "use", "using", "used",
    "because", "between", "through", "across", "within", "without", "over", "under", "after", "before", "these", "those",
    "i", "we", "he", "she", "it", "as", "is", "am", "be", "to", "of", "in", "on", "at", "by", "or", "an", "a",
}


def parse_int_list(value: str) -> list[int]:
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fieldnames = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sign_test_p(vals: Iterable[float]) -> float:
    x = np.asarray([v for v in vals if np.isfinite(v) and v != 0], dtype=float)
    n = len(x)
    if n == 0:
        return math.nan
    k = min(int(np.sum(x > 0)), int(np.sum(x < 0)))
    p = 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, p))


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) >= 3 and t.lower() not in STOPWORDS and not t.isdigit()]


def clean_text(value: Any, limit: int = 360) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def load_inputs(embed_npz: Path, post_index: Path) -> tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    npz = np.load(embed_npz, allow_pickle=False)
    embeddings = np.asarray(npz["embeddings"], dtype=np.float32)
    record_ids = np.asarray(npz["record_ids"]).astype(str)

    df = pd.read_csv(post_index, low_memory=False)
    if "is_seed" not in df.columns:
        raise ValueError("post_index is missing is_seed")
    df = df[~df["is_seed"].astype(bool)].copy()
    df["record_id"] = df["record_id"].astype(str)
    df["row_idx"] = np.arange(len(df))

    missing = sorted(set(df["record_id"]) - set(record_ids))
    if missing:
        raise ValueError(f"Embeddings missing for {len(missing)} post-index record_ids; first={missing[:3]}")

    return df, embeddings, record_ids


def assign_bins(sub: pd.DataFrame, scheme: str) -> list[tuple[int, str, pd.DataFrame]]:
    if scheme == "fixed_15m":
        return [
            (0, "0-15m", sub[(sub.minutes_elapsed >= 0) & (sub.minutes_elapsed < 15)]),
            (1, "15-30m", sub[(sub.minutes_elapsed >= 15) & (sub.minutes_elapsed < 30)]),
            (2, "30-45m", sub[(sub.minutes_elapsed >= 30) & (sub.minutes_elapsed < 45)]),
            (3, "45-60m", sub[(sub.minutes_elapsed >= 45) & (sub.minutes_elapsed <= 60)]),
        ]
    if scheme == "normalized_quartile":
        return [
            (0, "Q1", sub[(sub.normalized_time >= 0) & (sub.normalized_time < .25)]),
            (1, "Q2", sub[(sub.normalized_time >= .25) & (sub.normalized_time < .5)]),
            (2, "Q3", sub[(sub.normalized_time >= .5) & (sub.normalized_time < .75)]),
            (3, "Q4", sub[(sub.normalized_time >= .75) & (sub.normalized_time <= 1.000001)]),
        ]
    raise ValueError(f"unknown scheme {scheme}")


def topic_distribution_metrics(topic_ids: np.ndarray, n_topics: int) -> dict[str, Any]:
    n = int(len(topic_ids))
    if n == 0:
        return {
            "n_posts": 0,
            "dominant_share": math.nan,
            "topic_entropy_norm": math.nan,
            "effective_topics": math.nan,
            "topic_hhi": math.nan,
        }
    counts = np.bincount(topic_ids.astype(int), minlength=n_topics).astype(float)
    probs = counts / n
    nz = probs[probs > 0]
    entropy = float(-np.sum(nz * np.log(nz))) if len(nz) else 0.0
    hhi = float(np.sum(probs * probs))
    # Normalized Simpson/Herfindahl concentration. Raw HHI has a k-dependent
    # uniform baseline of 1/k; this rescales to 0=uniform over k clusters and
    # 1=all posts in one cluster. Direction is unchanged within a fixed k.
    hhi_norm = float((hhi - (1.0 / n_topics)) / (1.0 - (1.0 / n_topics))) if n_topics > 1 else math.nan
    return {
        "n_posts": n,
        "dominant_share": float(np.max(probs)),
        "topic_entropy_norm": float(entropy / math.log(n_topics)) if n_topics > 1 else math.nan,
        "effective_topics": float(math.exp(entropy)),
        "topic_hhi": hhi,
        "topic_hhi_norm": hhi_norm,
    }


def compute_run_deltas(df: pd.DataFrame, labels_by_record: dict[str, int], k: int, seed: int) -> list[dict[str, Any]]:
    work = df.copy()
    work["topic_id"] = work["record_id"].map(labels_by_record).astype(int)
    rows: list[dict[str, Any]] = []
    meta_cols = [
        "internal_family_label", "display_family_label", "model_family", "model_display",
        "roster_name", "condition", "scale", "n_agents", "run_id", "source_path",
    ]
    for run_uid, sub in work.groupby("run_uid", dropna=False):
        first = sub.iloc[0]
        schemes = ["normalized_quartile"] if first.internal_family_label == "obsession_prompting" else ["fixed_15m", "normalized_quartile"]
        for scheme in schemes:
            bin_rows = []
            for bi, label, b in assign_bins(sub, scheme):
                metrics = topic_distribution_metrics(b["topic_id"].to_numpy(dtype=int), k)
                metrics.update({"bin_idx": bi, "bin_label": label})
                bin_rows.append(metrics)
            row: dict[str, Any] = {
                "k": k,
                "seed": seed,
                "run_uid": run_uid,
                "scheme": scheme,
                "first_bin": bin_rows[0]["bin_label"],
                "final_bin": bin_rows[-1]["bin_label"],
                "first_n_posts": bin_rows[0]["n_posts"],
                "final_n_posts": bin_rows[-1]["n_posts"],
            }
            for metric in ["dominant_share", "topic_entropy_norm", "effective_topics", "topic_hhi", "topic_hhi_norm"]:
                a, b = bin_rows[0][metric], bin_rows[-1][metric]
                row[f"delta_{metric}"] = (b - a) if np.isfinite(a) and np.isfinite(b) else math.nan
            for col in meta_cols:
                row[col] = first[col]
            rows.append(row)
    return rows


def summarize(deltas: pd.DataFrame) -> pd.DataFrame:
    metrics = ["delta_dominant_share", "delta_topic_entropy_norm", "delta_effective_topics", "delta_topic_hhi", "delta_topic_hhi_norm"]
    groups = ["internal_family_label", "model_display", "scheme", "k", "seed"]
    rows = []
    for keys, sub in deltas.groupby(groups, dropna=False):
        row = dict(zip(groups, keys))
        row["n_runs"] = int(sub["run_uid"].nunique())
        for metric in metrics:
            vals = pd.to_numeric(sub[metric], errors="coerce").dropna().to_numpy(dtype=float)
            row[f"{metric}_mean"] = float(np.mean(vals)) if len(vals) else math.nan
            row[f"{metric}_median"] = float(np.median(vals)) if len(vals) else math.nan
            row[f"{metric}_n_negative"] = int(np.sum(vals < 0))
            row[f"{metric}_n_positive"] = int(np.sum(vals > 0))
            row[f"{metric}_sign_p"] = sign_test_p(vals)
        rows.append(row)
    return pd.DataFrame(rows)


def canonical_stability(deltas: pd.DataFrame) -> pd.DataFrame:
    can = deltas[(deltas["internal_family_label"] == "single_model_final") & (deltas["scheme"] == "fixed_15m")].copy()
    rows = []
    for run_uid, sub in can.groupby("run_uid", dropna=False):
        first = sub.iloc[0]
        n = len(sub)
        rows.append({
            "run_uid": run_uid,
            "model_display": first.model_display,
            "condition": first.condition,
            "condition_label": CONDITION_LABELS.get(first.condition, first.condition),
            "n_agents": int(first.n_agents),
            "scale": first.scale,
            "n_cluster_settings": int(n),
            "topic_entropy_decline_rate": float(np.mean(sub["delta_topic_entropy_norm"] < 0)),
            "dominant_share_increase_rate": float(np.mean(sub["delta_dominant_share"] > 0)),
            "effective_topics_decline_rate": float(np.mean(sub["delta_effective_topics"] < 0)),
            "topic_hhi_increase_rate": float(np.mean(sub["delta_topic_hhi"] > 0)),
            "topic_hhi_norm_increase_rate": float(np.mean(sub["delta_topic_hhi_norm"] > 0)),
            "mean_delta_topic_entropy_norm": float(sub["delta_topic_entropy_norm"].mean()),
            "mean_delta_dominant_share": float(sub["delta_dominant_share"].mean()),
            "mean_delta_effective_topics": float(sub["delta_effective_topics"].mean()),
            "mean_delta_topic_hhi": float(sub["delta_topic_hhi"].mean()),
            "mean_delta_topic_hhi_norm": float(sub["delta_topic_hhi_norm"].mean()),
        })
    return pd.DataFrame(rows)


def plot_stability_matrix(stability: pd.DataFrame, metric: str, title: str, cbar_label: str, out_path: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 9.2), sharex=True, sharey=True, layout="constrained")
    axes = axes.ravel()
    cmap = plt.get_cmap("RdYlGn").copy()
    cmap.set_bad("#eeeeee")
    last_im = None
    for ax, model in zip(axes, MODEL_ORDER):
        sub = stability[stability["model_display"] == model]
        mat = np.full((len(CONDITION_ORDER), len(SCALE_ORDER)), np.nan, dtype=float)
        annot = [["" for _ in SCALE_ORDER] for __ in CONDITION_ORDER]
        for i, cond in enumerate(CONDITION_ORDER):
            for j, n_agents in enumerate(SCALE_ORDER):
                cell = sub[(sub["condition"] == cond) & (sub["n_agents"] == n_agents)]
                if not cell.empty:
                    val = float(cell.iloc[0][metric])
                    mat[i, j] = val
                    annot[i][j] = f"{val:.0%}"
        masked = np.ma.masked_invalid(mat)
        last_im = ax.imshow(masked, vmin=0, vmax=1, cmap=cmap, aspect="auto")
        ax.set_title(model, fontsize=13)
        ax.set_xticks(np.arange(len(SCALE_ORDER)))
        ax.set_xticklabels([f"{n} agents" for n in SCALE_ORDER], rotation=0)
        ax.set_yticks(np.arange(len(CONDITION_ORDER)))
        ax.set_yticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER])
        ax.set_xticks(np.arange(-.5, len(SCALE_ORDER), 1), minor=True)
        ax.set_yticks(np.arange(-.5, len(CONDITION_ORDER), 1), minor=True)
        ax.grid(which="minor", color="white", linewidth=2)
        ax.tick_params(which="minor", bottom=False, left=False)
        for i in range(len(CONDITION_ORDER)):
            for j in range(len(SCALE_ORDER)):
                if annot[i][j]:
                    ax.text(j, i, annot[i][j], ha="center", va="center", fontsize=9, color="#111111")
    fig.suptitle(title, fontsize=16)
    if last_im is not None:
        cbar = fig.colorbar(last_im, ax=axes.tolist(), shrink=0.86, pad=0.02, location="right")
        cbar.set_label(cbar_label)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def plot_k_seed_summary(summary: pd.DataFrame, metric: str, title: str, cbar_label: str, out_path: Path, vcenter: float = 0.0) -> None:
    can = summary[(summary["internal_family_label"] == "single_model_final") & (summary["scheme"] == "fixed_15m")].copy()
    models = MODEL_ORDER
    k_values = sorted(can["k"].unique())
    seeds = sorted(can["seed"].unique())
    vals = can[f"{metric}_mean"].to_numpy(dtype=float)
    vmax = float(np.nanmax(np.abs(vals - vcenter))) if len(vals) else 1.0
    if not np.isfinite(vmax) or vmax == 0:
        vmax = 1.0
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.8), sharex=True, sharey=True, layout="constrained")
    axes = axes.ravel()
    cmap = plt.get_cmap("coolwarm_r" if metric == "delta_topic_entropy_norm" else "coolwarm")
    last_im = None
    for ax, model in zip(axes, models):
        sub = can[can["model_display"] == model]
        mat = np.full((len(k_values), len(seeds)), np.nan, dtype=float)
        for i, k in enumerate(k_values):
            for j, seed in enumerate(seeds):
                cell = sub[(sub["k"] == k) & (sub["seed"] == seed)]
                if not cell.empty:
                    mat[i, j] = float(cell.iloc[0][f"{metric}_mean"])
        last_im = ax.imshow(mat, vmin=vcenter-vmax, vmax=vcenter+vmax, cmap=cmap, aspect="auto")
        ax.set_title(model, fontsize=13)
        ax.set_xticks(np.arange(len(seeds)))
        ax.set_xticklabels([str(s) for s in seeds])
        ax.set_yticks(np.arange(len(k_values)))
        ax.set_yticklabels([str(k) for k in k_values])
        ax.set_xlabel("KMeans random seed")
        ax.set_ylabel("k topics")
        for i in range(len(k_values)):
            for j in range(len(seeds)):
                if np.isfinite(mat[i, j]):
                    ax.text(j, i, f"{mat[i,j]:.2f}", ha="center", va="center", fontsize=8)
    fig.suptitle(title, fontsize=16)
    if last_im is not None:
        cbar = fig.colorbar(last_im, ax=axes.tolist(), shrink=0.86, pad=0.02, location="right")
        cbar.set_label(cbar_label)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=220, bbox_inches="tight")
    fig.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def build_exemplars(
    df: pd.DataFrame,
    z: np.ndarray,
    record_ids: np.ndarray,
    exemplar_labels: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]],
    out_path: Path,
    exemplar_seed: int,
    n_examples: int = 3,
) -> None:
    # One row per unique record for text lookup.
    unique = df.drop_duplicates("record_id").set_index("record_id", drop=False)
    rid_to_pos = {rid: i for i, rid in enumerate(record_ids)}
    lines = [
        "# Embedding-cluster exemplars",
        "",
        f"Exemplars use the clustering runs with random seed `{exemplar_seed}`.",
        "These clusters are unsupervised embedding clusters, not validated human topic labels.",
        "",
    ]
    for (k, seed), (labels, centers) in sorted(exemplar_labels.items()):
        if seed != exemplar_seed:
            continue
        lines.extend([f"## k={k}, seed={seed}", ""])
        centers_norm = normalize(centers.astype(np.float32), norm="l2")
        for topic in range(k):
            ids = np.where(labels == topic)[0]
            if len(ids) == 0:
                continue
            # Keywords from cluster token counts.
            counts = Counter()
            for idx in ids:
                rid = record_ids[idx]
                if rid in unique.index:
                    row = unique.loc[rid]
                    counts.update(tokenize(f"{row.get('title','')} {row.get('content','')}"))
            keywords = ", ".join([term for term, _ in counts.most_common(8)])
            sims = z[ids] @ centers_norm[topic]
            nearest = ids[np.argsort(-sims)[:n_examples]]
            lines.extend([f"### T{topic+1:02d} — {len(ids):,} posts", "", f"Keywords: {keywords or '(none)'}", ""])
            for rank, idx in enumerate(nearest, start=1):
                rid = record_ids[idx]
                if rid not in unique.index:
                    continue
                row = unique.loc[rid]
                title = clean_text(row.get("title", ""), 160)
                content = clean_text(row.get("content", ""), 420)
                model = clean_text(row.get("model_display", ""), 80)
                cond = CONDITION_LABELS.get(str(row.get("condition", "")), str(row.get("condition", "")))
                run_id = clean_text(row.get("run_id", ""), 100)
                lines.extend([
                    f"{rank}. **{title}**",
                    f"   - Source: {model}, {cond}, `{run_id}`",
                    f"   - Excerpt: {content}",
                    "",
                ])
    out_path.write_text("\n".join(lines))


def write_report(out: Path, stability: pd.DataFrame, summary: pd.DataFrame, k_values: list[int], seeds: list[int]) -> None:
    can = stability.copy()
    rows = []
    for model in MODEL_ORDER:
        sub = can[can["model_display"] == model]
        if sub.empty:
            continue
        rows.append({
            "model": model,
            "runs": int(sub["run_uid"].nunique()),
            "entropy_decline_rate_mean": float(sub["topic_entropy_decline_rate"].mean()),
            "entropy_decline_cells_ge_75pct": int((sub["topic_entropy_decline_rate"] >= 0.75).sum()),
            "entropy_decline_cells_all_settings": int((sub["topic_entropy_decline_rate"] == 1.0).sum()),
            "dominant_share_increase_rate_mean": float(sub["dominant_share_increase_rate"].mean()),
            "dominant_share_cells_ge_75pct": int((sub["dominant_share_increase_rate"] >= 0.75).sum()),
            "dominant_share_cells_all_settings": int((sub["dominant_share_increase_rate"] == 1.0).sum()),
            "hhi_norm_increase_rate_mean": float(sub["topic_hhi_norm_increase_rate"].mean()),
            "hhi_norm_cells_ge_75pct": int((sub["topic_hhi_norm_increase_rate"] >= 0.75).sum()),
            "hhi_norm_cells_all_settings": int((sub["topic_hhi_norm_increase_rate"] == 1.0).sum()),
        })
    table = pd.DataFrame(rows)
    md = [
        "# Topic-cluster robustness sweep",
        "",
        "This sweep reruns unsupervised embedding clustering across multiple topic counts and random seeds.",
        "It tests robustness of embedding-cluster concentration, not validated human topic categories.",
        "",
        f"k values: `{k_values}`",
        f"random seeds: `{seeds}`",
        "SVD components: `50`; embedding model: `qwen/qwen3-embedding-8b`.",
        "",
        "## Current status",
        "",
        "The earlier Ayush topic output used one clustering configuration only: `k=12`, `random_state=42`.",
        "This sweep adds k/seed sensitivity outputs for deciding whether topic metrics are stable enough for main-paper use.",
        "",
        "## Canonical fixed-window stability by model",
        "",
    ]
    if table.empty:
        md.append("(empty)")
    else:
        fmt = table.copy()
        for col in fmt.columns:
            if col.endswith("_mean"):
                fmt[col] = fmt[col].map(lambda x: f"{x:.3f}")
        md.append("| " + " | ".join(fmt.columns) + " |")
        md.append("| " + " | ".join(["---"] * len(fmt.columns)) + " |")
        for _, row in fmt.iterrows():
            md.append("| " + " | ".join(str(row[col]) for col in fmt.columns) + " |")
    md.extend([
        "",
        "## Outputs",
        "",
        "- `topic_robustness_run_deltas.csv`: every run × scheme × k × seed delta.",
        "- `topic_robustness_summary_by_model.csv`: model/family summaries by k and seed.",
        "- `canonical_topic_cluster_stability_by_run.csv`: per canonical run stability rates across all k/seed settings.",
        "- `topic_entropy_robustness_matrix.png`: per-run design matrix; cell value is share of k/seed settings with topic entropy decline.",
        "- `dominant_share_robustness_matrix.png`: per-run design matrix; cell value is share of k/seed settings with dominant-topic share increase.",
        "- `hhi_norm_robustness_matrix.png`: per-run design matrix; cell value is share of k/seed settings with normalized HHI/Simpson concentration increase.",
        "- `topic_entropy_mean_delta_by_k_seed_model.png`: diagnostic k×seed mean-delta heatmap by model.",
        "- `dominant_share_mean_delta_by_k_seed_model.png`: diagnostic k×seed mean-delta heatmap by model.",
        "- `hhi_norm_mean_delta_by_k_seed_model.png`: diagnostic k×seed normalized-HHI mean-delta heatmap by model.",
        "- `topic_exemplars.md`: exemplar posts for each topic at each k using the configured exemplar seed.",
        "",
        "## Interpretation rule",
        "",
        "Use normalized HHI/Simpson concentration as the paper-facing embedding-cluster concentration metric where the relevant cells remain directionally stable across k and seed. Describe it as embedding-cluster concentration unless labels are manually validated.",
    ])
    (out / "TOPIC_ROBUSTNESS_REPORT.md").write_text("\n".join(md))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-npz", default=str(DEFAULT_EMBED_NPZ))
    parser.add_argument("--post-index", default=str(DEFAULT_POST_INDEX))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--k-values", default=",".join(map(str, K_VALUES)))
    parser.add_argument("--seeds", default=",".join(map(str, SEEDS)))
    parser.add_argument("--svd-components", type=int, default=SVD_COMPONENTS)
    parser.add_argument("--exemplar-seed", type=int, default=55)
    parser.add_argument("--n-exemplars", type=int, default=3)
    args = parser.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    k_values = parse_int_list(args.k_values)
    seeds = parse_int_list(args.seeds)
    if args.exemplar_seed not in seeds:
        seeds = sorted(set(seeds + [args.exemplar_seed]))

    print("loading inputs")
    df, embeddings, record_ids = load_inputs(Path(args.embedding_npz), Path(args.post_index))
    print(f"post rows non-seed={len(df):,}; unique embeddings={len(record_ids):,}; dims={embeddings.shape[1]:,}")

    print("normalizing embeddings")
    mat = normalize(embeddings, norm="l2", copy=True)
    n_comp = min(args.svd_components, mat.shape[1] - 1, mat.shape[0] - 1)
    print(f"fitting TruncatedSVD n_components={n_comp}")
    svd = TruncatedSVD(n_components=n_comp, random_state=42)
    z = svd.fit_transform(mat).astype(np.float32)
    z = normalize(z, norm="l2", copy=False)
    print(f"SVD explained variance ratio sum={float(np.sum(svd.explained_variance_ratio_)):.4f}")

    all_delta_rows: list[dict[str, Any]] = []
    exemplar_labels: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}

    for k in k_values:
        for seed in seeds:
            print(f"clustering k={k} seed={seed}")
            km = MiniBatchKMeans(n_clusters=k, random_state=seed, batch_size=4096, n_init=10)
            raw = km.fit_predict(z)
            counts = Counter(int(x) for x in raw)
            remap = {old: new for new, (old, _) in enumerate(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))}
            labels = np.asarray([remap[int(x)] for x in raw], dtype=np.int32)
            centers = np.zeros((k, z.shape[1]), dtype=np.float32)
            for old, new in remap.items():
                centers[new] = km.cluster_centers_[old]
            labels_by_record = dict(zip(record_ids, labels.tolist()))
            all_delta_rows.extend(compute_run_deltas(df, labels_by_record, k, seed))
            if seed == args.exemplar_seed:
                exemplar_labels[(k, seed)] = (labels, centers)

    deltas = pd.DataFrame(all_delta_rows)
    deltas.to_csv(out / "topic_robustness_run_deltas.csv", index=False, lineterminator="\n")
    # Backward-compatible/planned alias focused on entropy but includes all topic deltas.
    deltas.to_csv(out / "topic_entropy_delta_by_k_seed.csv", index=False, lineterminator="\n")

    summary = summarize(deltas)
    summary.to_csv(out / "topic_robustness_summary_by_model.csv", index=False, lineterminator="\n")

    stability = canonical_stability(deltas)
    stability.to_csv(out / "canonical_topic_cluster_stability_by_run.csv", index=False, lineterminator="\n")

    plot_stability_matrix(
        stability,
        "topic_entropy_decline_rate",
        "Canonical runs: stability of embedding-cluster entropy decline across k and seed",
        "Share of k/seed settings with entropy decline",
        out / "topic_entropy_robustness_matrix.png",
    )
    plot_stability_matrix(
        stability,
        "dominant_share_increase_rate",
        "Canonical runs: stability of dominant embedding-cluster share increase across k and seed",
        "Share of k/seed settings with dominant-share increase",
        out / "dominant_share_robustness_matrix.png",
    )
    plot_k_seed_summary(
        summary,
        "delta_topic_entropy_norm",
        "Canonical fixed-window mean Δ topic entropy by model, k, and seed",
        "Mean Δ normalized topic entropy",
        out / "topic_entropy_mean_delta_by_k_seed_model.png",
        vcenter=0.0,
    )
    plot_stability_matrix(
        stability,
        "topic_hhi_norm_increase_rate",
        "Canonical runs: stability of normalized HHI/Simpson concentration increase across k and seed",
        "Share of k/seed settings with concentration increase",
        out / "hhi_norm_robustness_matrix.png",
    )
    plot_k_seed_summary(
        summary,
        "delta_dominant_share",
        "Canonical fixed-window mean Δ dominant topic share by model, k, and seed",
        "Mean Δ dominant topic share",
        out / "dominant_share_mean_delta_by_k_seed_model.png",
        vcenter=0.0,
    )
    plot_k_seed_summary(
        summary,
        "delta_topic_hhi_norm",
        "Canonical fixed-window mean Δ normalized HHI/Simpson concentration by model, k, and seed",
        "Mean Δ normalized HHI/Simpson concentration",
        out / "hhi_norm_mean_delta_by_k_seed_model.png",
        vcenter=0.0,
    )

    build_exemplars(df, z, record_ids, exemplar_labels, out / "topic_exemplars.md", args.exemplar_seed, args.n_exemplars)
    write_report(out, stability, summary, k_values, seeds)

    meta = {
        "embedding_npz": str(args.embedding_npz),
        "post_index": str(args.post_index),
        "out_dir": str(out),
        "k_values": k_values,
        "seeds": seeds,
        "svd_components": int(n_comp),
        "svd_explained_variance_ratio_sum": float(np.sum(svd.explained_variance_ratio_)),
        "n_nonseed_rows": int(len(df)),
        "n_unique_embeddings": int(len(record_ids)),
        "outputs": sorted(p.name for p in out.iterdir() if p.is_file()),
    }
    (out / "topic_robustness_summary.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote outputs to {out}")


if __name__ == "__main__":
    main()
