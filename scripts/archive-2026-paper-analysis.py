#!/usr/bin/env python3
"""Paper-style embedding + LLM-as-judge analysis for archive-2026 corpus.

This intentionally avoids dashboard heatmaps. It creates publication-style dot,
slope, line, stacked-bar, and semantic-map figures aligned with the EMNLP draft
framing: semantic-space narrowing, model/condition decomposition, and qualitative
collapse scoring.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from sklearn.preprocessing import normalize

try:
    from scipy.sparse.linalg import eigsh
except Exception:  # pragma: no cover
    eigsh = None

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
TIME_LABELS = {0: "0–15m", 1: "15–30m", 2: "30–45m", 3: "45–60m"}
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy",
    "mag5": "5 conspiracies",
    "mag25": "25 conspiracies",
    "dom-agi": "25 AGI-hype",
    "dom-tech": "25 tech-humor",
}
GROUP_ORDER = ["base-model", "canonical-48", "entropy-collapse", "frontier/mixed-model", "obsession", "source-citation"]
COLLAPSE_COMPONENTS = ["semantic_repetition", "narrative_convergence", "groupthink", "template_rigidity"]
JUDGE_METRICS = ["novelty", "semantic_repetition", "narrative_convergence", "groupthink", "template_rigidity", "evidence_grounding"]
PALETTE = ["#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC", "#1F77B4", "#FF7F0E"]
COND_COLORS = {
    "mag0": "#4E79A7",
    "mag1": "#9ECAE1",
    "mag5": "#4292C6",
    "mag25": "#08519C",
    "dom-agi": "#F28E2B",
    "dom-tech": "#59A14F",
}
TIME_COLORS = {0: "#2166AC", 1: "#67A9CF", 2: "#F4A582", 3: "#B2182B"}

plt.rcParams.update({
    "figure.dpi": 140,
    "savefig.dpi": 300,
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.labelsize": 10,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


def slugify(x: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(x)).strip("-") or "unknown"


def is_true(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def save_fig(fig: plt.Figure, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out_path)
    fig.savefig(out_path.with_suffix(".pdf"))
    plt.close(fig)


def bootstrap_ci(values: np.ndarray, seed: int = 42, n_boot: int = 1000) -> tuple[float, float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return np.nan, np.nan, np.nan
    mean = float(np.mean(values))
    if len(values) == 1:
        return mean, mean, mean
    rng = np.random.default_rng(seed)
    boots = np.empty(n_boot, dtype=float)
    n = len(values)
    for i in range(n_boot):
        boots[i] = np.mean(values[rng.integers(0, n, n)])
    return mean, float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def mean_pairwise_cosine(x: np.ndarray) -> float:
    if len(x) < 2:
        return np.nan
    sim = x @ x.T
    iu = np.triu_indices(len(x), k=1)
    return float(np.mean(sim[iu]))


def vendi_score(x: np.ndarray) -> float:
    """Effective semantic diversity from cosine-kernel eigenvalue entropy.

    Uses K=(cos+1)/2 to keep the kernel positive-ish and bounded. For a bin with
    identical texts, the score approaches 1; larger values mean a broader set of
    effective semantic items.
    """
    n = len(x)
    if n < 2:
        return np.nan
    sim = x @ x.T
    k = (sim + 1.0) / 2.0
    eig = np.linalg.eigvalsh(k / n).astype(float)
    eig = eig[eig > 1e-12]
    eig = eig / eig.sum()
    return float(np.exp(-np.sum(eig * np.log(eig))))


def semantic_radius(x: np.ndarray) -> float:
    if len(x) < 2:
        return np.nan
    centroid = x.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm <= 1e-12:
        return np.nan
    centroid = centroid / norm
    return float(np.mean(1.0 - (x @ centroid)))


def classical_mds_from_cosine(x: np.ndarray) -> np.ndarray:
    """Classical MDS from cosine distances for a balanced sample."""
    x = normalize(x, norm="l2", copy=False)
    d = 1.0 - np.clip(x @ x.T, -1.0, 1.0)
    d2 = d * d
    n = d.shape[0]
    row_mean = d2.mean(axis=1, keepdims=True)
    col_mean = d2.mean(axis=0, keepdims=True)
    total_mean = d2.mean()
    b = -0.5 * (d2 - row_mean - col_mean + total_mean)
    if eigsh is not None and n > 800:
        vals, vecs = eigsh(b, k=2, which="LA")
        idx = np.argsort(vals)[::-1]
        vals = vals[idx]
        vecs = vecs[:, idx]
    else:
        vals, vecs = np.linalg.eigh(b)
        idx = np.argsort(vals)[::-1][:2]
        vals = vals[idx]
        vecs = vecs[:, idx]
    vals = np.maximum(vals, 0)
    coords = vecs * np.sqrt(vals)
    return coords.astype(np.float32)


def load_data(root: Path) -> tuple[pd.DataFrame, np.ndarray]:
    index = pd.read_csv(root / "combined_posts_index.csv")
    npz = np.load(root / "embeddings" / "qwen-qwen3-embedding-8b.npz")
    emb = npz["embeddings"].astype(np.float32)
    if len(index) != len(emb):
        raise SystemExit(f"Index rows {len(index)} != embedding rows {len(emb)}")
    index["row_index"] = np.arange(len(index))
    index["is_seed_bool"] = is_true(index["is_seed"])
    return index, normalize(emb, norm="l2", copy=False)


def compute_embedding_bins(df: pd.DataFrame, x: np.ndarray, out_dir: Path, max_bin_n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    group_cols = ["dataset_source", "group", "model_family", "condition", "scale", "run_path", "time_bin"]
    work = df[(~df["is_seed_bool"]) & df["time_bin"].isin([0, 1, 2, 3])].copy()
    for key, sub in work.groupby(group_cols, dropna=False):
        idx = sub["row_index"].to_numpy(dtype=int)
        n_posts = len(idx)
        if n_posts > max_bin_n:
            idx = rng.choice(idx, size=max_bin_n, replace=False)
        xb = x[idx]
        row = {k: v for k, v in zip(group_cols, key)}
        row.update({
            "n_posts": int(n_posts),
            "n_used": int(len(idx)),
            "vendi_score": vendi_score(xb),
            "mean_pairwise_cosine": mean_pairwise_cosine(xb),
            "semantic_radius": semantic_radius(xb),
        })
        rows.append(row)
    bins = pd.DataFrame(rows)
    bins.to_csv(out_dir / "embedding_timebin_metrics.csv", index=False)
    return bins


def compute_deltas(bins: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    id_cols = ["dataset_source", "group", "model_family", "condition", "scale", "run_path"]
    rows = []
    for key, sub in bins.groupby(id_cols, dropna=False):
        q1 = sub[sub["time_bin"] == 0]
        q4 = sub[sub["time_bin"] == 3]
        if q1.empty or q4.empty:
            continue
        a = q1.iloc[0]
        b = q4.iloc[0]
        row = {k: v for k, v in zip(id_cols, key)}
        for metric in ["vendi_score", "mean_pairwise_cosine", "semantic_radius"]:
            row[f"q1_{metric}"] = float(a[metric])
            row[f"q4_{metric}"] = float(b[metric])
            row[f"delta_{metric}"] = float(b[metric] - a[metric])
        row["q1_posts"] = int(a["n_posts"])
        row["q4_posts"] = int(b["n_posts"])
        rows.append(row)
    deltas = pd.DataFrame(rows)
    deltas.to_csv(out_dir / "embedding_q4_minus_q1_deltas.csv", index=False)
    return deltas


def summarize_delta(deltas: pd.DataFrame, by: str, out_dir: Path, prefix: str) -> pd.DataFrame:
    rows = []
    for key, sub in deltas.groupby(by, dropna=False):
        row = {by: key, "n_runs": len(sub)}
        for metric in ["delta_vendi_score", "delta_mean_pairwise_cosine", "delta_semantic_radius"]:
            mean, lo, hi = bootstrap_ci(sub[metric].to_numpy(), seed=17)
            row[f"{metric}_mean"] = mean
            row[f"{metric}_ci_low"] = lo
            row[f"{metric}_ci_high"] = hi
            row[f"{metric}_n_negative"] = int(np.sum(sub[metric] < 0))
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(out_dir / f"embedding_delta_summary_by_{prefix}.csv", index=False)
    return out


def plot_vendi_trajectories(bins: pd.DataFrame, out_dir: Path, by: str, title: str, fname: str) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8))
    keys = [k for k in (GROUP_ORDER if by == "group" else CONDITION_ORDER) if k in set(bins[by])] + [k for k in sorted(set(bins[by])) if k not in (GROUP_ORDER + CONDITION_ORDER)]
    for i, key in enumerate(keys):
        sub = bins[bins[by] == key]
        line = []
        lo = []
        hi = []
        xs = []
        for tb in [0, 1, 2, 3]:
            vals = sub[sub["time_bin"] == tb]["vendi_score"].to_numpy(dtype=float)
            if len(vals) == 0:
                continue
            m, l, h = bootstrap_ci(vals, seed=100 + tb)
            xs.append(tb)
            line.append(m)
            lo.append(l)
            hi.append(h)
        if xs:
            label = CONDITION_LABELS.get(key, str(key))
            color = COND_COLORS.get(key, PALETTE[i % len(PALETTE)])
            ax.plot(xs, line, marker="o", lw=2, label=label, color=color)
            ax.fill_between(xs, lo, hi, alpha=0.14, color=color, linewidth=0)
    ax.set_xticks([0, 1, 2, 3], [TIME_LABELS[i] for i in [0, 1, 2, 3]])
    ax.set_ylabel("Vendi score / effective semantic diversity")
    ax.set_xlabel("Run time")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=2)
    save_fig(fig, out_dir / fname)


def plot_delta_dot(summary: pd.DataFrame, label_col: str, metric: str, out_dir: Path, fname: str, title: str, xlabel: str, zero_line: bool = True) -> None:
    m = f"{metric}_mean"
    lo = f"{metric}_ci_low"
    hi = f"{metric}_ci_high"
    d = summary.sort_values(m).copy()
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(7.4, max(3.8, 0.35 * len(d))))
    xerr = np.vstack([d[m] - d[lo], d[hi] - d[m]])
    ax.errorbar(d[m], y, xerr=xerr, fmt="o", color="#4E79A7", ecolor="#9ECAE1", capsize=3, ms=5)
    if zero_line:
        ax.axvline(0, color="#555", lw=1, linestyle="--")
    ax.set_yticks(y, d[label_col].astype(str))
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.25)
    save_fig(fig, out_dir / fname)


def plot_mds_maps(df: pd.DataFrame, x: np.ndarray, out_dir: Path, sample_n: int, seed: int) -> pd.DataFrame:
    work = df[(~df["is_seed_bool"]) & df["time_bin"].isin([0, 1, 2, 3])].copy()
    strata = ["condition", "time_bin"]
    # Balanced condition × time sample to prevent entropy-collapse/gemini volume dominating.
    per_cell = max(20, sample_n // max(1, work.groupby(strata).ngroups))
    pieces = []
    rng = np.random.default_rng(seed)
    for _, sub in work.groupby(strata, dropna=False):
        k = min(per_cell, len(sub))
        pieces.append(sub.sample(k, random_state=int(rng.integers(0, 1_000_000))))
    sample = pd.concat(pieces, ignore_index=False)
    if len(sample) > sample_n:
        sample = sample.sample(sample_n, random_state=seed)
    coords = classical_mds_from_cosine(x[sample["row_index"].to_numpy(dtype=int)])
    sample = sample.copy()
    sample["mds_1"] = coords[:, 0]
    sample["mds_2"] = coords[:, 1]
    sample.to_csv(out_dir / "embedding_mds_balanced_sample.csv", index=False)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharex=True, sharey=True)
    ax = axes[0]
    for cond in CONDITION_ORDER:
        sub = sample[sample["condition"] == cond]
        if len(sub):
            ax.scatter(sub["mds_1"], sub["mds_2"], s=7, alpha=0.55, label=CONDITION_LABELS.get(cond, cond), color=COND_COLORS.get(cond))
    ax.set_title("Semantic map colored by stimulus condition")
    ax.set_xlabel("MDS-1")
    ax.set_ylabel("MDS-2")
    ax.legend(frameon=False, markerscale=2, ncol=1, loc="best")

    ax = axes[1]
    for tb in [0, 1, 2, 3]:
        sub = sample[sample["time_bin"] == tb]
        ax.scatter(sub["mds_1"], sub["mds_2"], s=7, alpha=0.55, label=TIME_LABELS[tb], color=TIME_COLORS[tb])
    ax.set_title("Same map colored by time")
    ax.set_xlabel("MDS-1")
    ax.legend(frameon=False, markerscale=2)
    fig.suptitle("Embedding-space semantic map (balanced sample, cosine classical MDS)", y=1.02)
    save_fig(fig, out_dir / "fig_embedding_mds_condition_time.png")
    return sample


def collapse_index(df: pd.DataFrame, prefix: str = "") -> pd.Series:
    cols = [prefix + c for c in COLLAPSE_COMPONENTS]
    return df[cols].mean(axis=1)


def aggregate_judge(judge: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    for key, sub in judge.groupby(by, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        row = {k: v for k, v in zip(by, key)}
        row["n_judged"] = len(sub)
        for metric in JUDGE_METRICS + ["specificity", "epistemic_caution", "source_citation_quality"]:
            if metric in sub:
                mean, lo, hi = bootstrap_ci(sub[metric].to_numpy(), seed=81)
                row[f"{metric}_mean"] = mean
                row[f"{metric}_ci_low"] = lo
                row[f"{metric}_ci_high"] = hi
        row["collapse_index_mean"] = float(np.mean([row[f"{m}_mean"] for m in COLLAPSE_COMPONENTS]))
        rows.append(row)
    return pd.DataFrame(rows)


def plot_judge_model_dot(jm: pd.DataFrame, out_dir: Path) -> None:
    d = jm.sort_values("collapse_index_mean").copy()
    y = np.arange(len(d))
    fig, ax = plt.subplots(figsize=(7.6, max(4, 0.38 * len(d))))
    ax.hlines(y, 1, d["collapse_index_mean"], color="#DDD", lw=2)
    ax.scatter(d["collapse_index_mean"], y, s=70, color="#E15759", label="collapse index")
    for yi, (_, r) in enumerate(d.iterrows()):
        ax.text(r["collapse_index_mean"] + 0.035, yi, f"{r['collapse_index_mean']:.2f}  (n={int(r['n_judged'])})", va="center", fontsize=7)
    ax.set_xlim(1, 5)
    ax.set_yticks(y, d["model_family"].astype(str))
    ax.set_xlabel("LLM-judge collapse index")
    ax.set_title("Generation models ranked by LLM-judged collapse")
    ax.grid(axis="x", alpha=0.25)
    save_fig(fig, out_dir / "fig_llm_judge_model_collapse_dotplot.png")


def plot_judge_condition_dot(jc: pd.DataFrame, out_dir: Path) -> None:
    d = jc.copy()
    order = {c: i for i, c in enumerate(CONDITION_ORDER)}
    d["_order"] = d["condition"].map(lambda x: order.get(x, 99))
    d = d.sort_values("_order")
    fig, ax = plt.subplots(figsize=(7.2, 4.4))
    y = np.arange(len(d))
    ax.hlines(y, 1, d["collapse_index_mean"], color="#DDD", lw=2)
    colors = [COND_COLORS.get(c, "#777") for c in d["condition"]]
    ax.scatter(d["collapse_index_mean"], y, s=75, color=colors)
    for yi, (_, r) in enumerate(d.iterrows()):
        ax.text(r["collapse_index_mean"] + 0.035, yi, f"{r['collapse_index_mean']:.2f}", va="center", fontsize=8)
    ax.set_xlim(1, 5)
    ax.set_yticks(y, [CONDITION_LABELS.get(c, c) for c in d["condition"]])
    ax.set_xlabel("LLM-judge collapse index")
    ax.set_title("Stimulus conditions ranked by LLM-judged collapse")
    ax.grid(axis="x", alpha=0.25)
    save_fig(fig, out_dir / "fig_llm_judge_condition_collapse_dotplot.png")


def plot_model_condition_smallmultiples(jmc: pd.DataFrame, out_dir: Path) -> None:
    models = jmc.groupby("model_family")["n_judged"].sum().sort_values(ascending=False).index.tolist()
    ncols = 3
    nrows = int(math.ceil(len(models) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(14.5, max(7, 3.1 * nrows)), sharex=True)
    axes = np.asarray(axes).reshape(-1)
    order = {c: i for i, c in enumerate(CONDITION_ORDER)}
    for ax, model in zip(axes, models):
        sub = jmc[jmc["model_family"] == model].copy()
        sub["_order"] = sub["condition"].map(lambda x: order.get(x, 99))
        sub = sub.sort_values("_order")
        y = np.arange(len(sub))
        ax.barh(y, sub["collapse_index_mean"], color="#E15759", alpha=0.8)
        ax.set_yticks(y, [CONDITION_LABELS.get(c, c) for c in sub["condition"]])
        ax.set_xlim(1, 5)
        ax.set_title(model, fontsize=9)
        ax.grid(axis="x", alpha=0.2)
        for yi, (_, r) in enumerate(sub.iterrows()):
            ax.text(r["collapse_index_mean"] + 0.03, yi, f"{r['collapse_index_mean']:.2f}", va="center", fontsize=7)
    for ax in axes[len(models):]:
        ax.axis("off")
    fig.suptitle("LLM-judge collapse by condition, split by generation model", y=1.01)
    fig.supxlabel("Collapse index")
    save_fig(fig, out_dir / "fig_llm_judge_model_by_condition_smallmultiples.png")


def plot_metric_profiles(jm: pd.DataFrame, out_dir: Path) -> None:
    metrics = ["novelty", "semantic_repetition", "narrative_convergence", "groupthink", "template_rigidity", "evidence_grounding"]
    labels = ["Novelty", "Repetition", "Narr. conv.", "Groupthink", "Template", "Evidence"]
    models = jm.sort_values("collapse_index_mean", ascending=False)["model_family"].tolist()
    fig, ax = plt.subplots(figsize=(10.5, max(5, 0.42 * len(models))))
    y_base = np.arange(len(models))
    offsets = np.linspace(-0.24, 0.24, len(metrics))
    for i, metric in enumerate(metrics):
        vals = jm.set_index("model_family").loc[models, f"{metric}_mean"].to_numpy()
        ax.scatter(vals, y_base + offsets[i], s=22, label=labels[i], color=PALETTE[i])
    ax.set_yticks(y_base, models)
    ax.invert_yaxis()
    ax.set_xlim(1, 5)
    ax.set_xlabel("Mean LLM-judge score")
    ax.set_title("LLM-judge metric profile by generation model")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="lower right")
    save_fig(fig, out_dir / "fig_llm_judge_model_metric_profiles.png")


def plot_label_distribution(judge: pd.DataFrame, out_dir: Path) -> None:
    counts = pd.crosstab(judge["model_family"], judge["collapse_label"], normalize="index")
    order = judge.groupby("model_family").size().sort_values(ascending=True).index.tolist()
    labels = ["novel_contribution", "mild_rephrase", "frame_convergence", "template_repetition", "source_grounded", "off_topic"]
    labels = [l for l in labels if l in counts.columns] + [l for l in counts.columns if l not in labels]
    counts = counts.reindex(index=order, columns=labels, fill_value=0)
    fig, ax = plt.subplots(figsize=(8.5, max(4.5, 0.42 * len(counts))))
    left = np.zeros(len(counts))
    colors = ["#59A14F", "#F28E2B", "#E15759", "#B07AA1", "#4E79A7", "#BAB0AC"]
    y = np.arange(len(counts))
    for i, label in enumerate(labels):
        vals = counts[label].to_numpy()
        ax.barh(y, vals, left=left, color=colors[i % len(colors)], label=label.replace("_", " "))
        left += vals
    ax.set_yticks(y, counts.index)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Share of judged posts")
    ax.set_title("Qualitative collapse labels by generation model")
    ax.legend(frameon=False, ncol=2, loc="lower right")
    save_fig(fig, out_dir / "fig_llm_judge_collapse_label_stackedbars.png")


def plot_embedding_vs_judge(deltas: pd.DataFrame, judge: pd.DataFrame, out_dir: Path) -> pd.DataFrame:
    # Merge run-level embedding delta with run-level judged collapse if available.
    jr = judge.copy()
    jr["collapse_index"] = jr[COLLAPSE_COMPONENTS].mean(axis=1)
    run_judge = jr.groupby(["group", "model_family", "condition", "scale", "run_path"], dropna=False).agg(
        collapse_index=("collapse_index", "mean"),
        n_judged=("collapse_index", "count"),
    ).reset_index()
    m = deltas.merge(run_judge, on=["group", "model_family", "condition", "scale", "run_path"], how="inner")
    m.to_csv(out_dir / "embedding_delta_vs_judge_by_run.csv", index=False)
    if len(m) >= 3:
        fig, ax = plt.subplots(figsize=(7, 5.2))
        groups = [g for g in GROUP_ORDER if g in set(m["group"])] + [g for g in sorted(set(m["group"])) if g not in GROUP_ORDER]
        for i, g in enumerate(groups):
            sub = m[m["group"] == g]
            ax.scatter(sub["delta_vendi_score"], sub["collapse_index"], s=35 + 8 * sub["n_judged"], alpha=0.75, label=g, color=PALETTE[i % len(PALETTE)], edgecolor="white", linewidth=0.4)
        ax.axvline(0, color="#555", linestyle="--", lw=1)
        ax.set_xlabel("Q4 − Q1 Vendi score (negative = semantic narrowing)")
        ax.set_ylabel("Mean LLM-judge collapse index")
        ax.set_title("Run-level semantic narrowing vs. judged collapse")
        ax.grid(alpha=0.25)
        ax.legend(frameon=False, fontsize=7, ncol=2)
        save_fig(fig, out_dir / "fig_embedding_delta_vs_llm_judge_collapse.png")
    return m


def md_table(df: pd.DataFrame, cols: list[str] | None = None, max_rows: int = 20, decimals: int = 3) -> str:
    d = df.copy()
    if cols:
        d = d[cols]
    d = d.head(max_rows)
    for col in d.columns:
        if pd.api.types.is_float_dtype(d[col]):
            d[col] = d[col].map(lambda x: "" if pd.isna(x) else f"{x:.{decimals}f}")
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, row in d.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    ap.add_argument("--max-bin-n", type=int, default=400)
    ap.add_argument("--mds-sample", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.out_dir)
    paper = root / "paper_analysis"
    paper.mkdir(parents=True, exist_ok=True)

    df, x = load_data(root)
    bins = compute_embedding_bins(df, x, paper, args.max_bin_n, args.seed)
    deltas = compute_deltas(bins, paper)
    by_group = summarize_delta(deltas, "group", paper, "group")
    by_model = summarize_delta(deltas, "model_family", paper, "model")
    by_condition = summarize_delta(deltas, "condition", paper, "condition")

    plot_vendi_trajectories(bins, paper, "group", "Embedding diversity over time by corpus group", "fig_embedding_vendi_over_time_by_group.png")
    plot_vendi_trajectories(bins, paper, "condition", "Embedding diversity over time by stimulus condition", "fig_embedding_vendi_over_time_by_condition.png")
    plot_delta_dot(by_model, "model_family", "delta_vendi_score", paper, "fig_embedding_delta_vendi_by_model.png", "Early-to-late semantic diversity change by model", "Q4 − Q1 Vendi score")
    plot_delta_dot(by_condition, "condition", "delta_vendi_score", paper, "fig_embedding_delta_vendi_by_condition.png", "Early-to-late semantic diversity change by condition", "Q4 − Q1 Vendi score")
    plot_delta_dot(by_group, "group", "delta_vendi_score", paper, "fig_embedding_delta_vendi_by_group.png", "Early-to-late semantic diversity change by corpus group", "Q4 − Q1 Vendi score")
    plot_mds_maps(df, x, paper, args.mds_sample, args.seed)

    judge = pd.read_csv(root / "llm_judge" / "judge_results.csv")
    judge["collapse_index"] = judge[COLLAPSE_COMPONENTS].mean(axis=1)
    jm = aggregate_judge(judge, ["model_family"])
    jc = aggregate_judge(judge, ["condition"])
    jg = aggregate_judge(judge, ["group"])
    jmc = aggregate_judge(judge, ["model_family", "condition"])
    jgc = aggregate_judge(judge, ["group", "condition"])
    jm.to_csv(paper / "llm_judge_summary_by_model.csv", index=False)
    jc.to_csv(paper / "llm_judge_summary_by_condition.csv", index=False)
    jg.to_csv(paper / "llm_judge_summary_by_group.csv", index=False)
    jmc.to_csv(paper / "llm_judge_summary_by_model_condition.csv", index=False)
    jgc.to_csv(paper / "llm_judge_summary_by_group_condition.csv", index=False)

    plot_judge_model_dot(jm, paper)
    plot_judge_condition_dot(jc, paper)
    plot_model_condition_smallmultiples(jmc, paper)
    plot_metric_profiles(jm, paper)
    plot_label_distribution(judge, paper)
    merged = plot_embedding_vs_judge(deltas, judge, paper)

    # Tables for manuscript appendix.
    model_rank = jm.sort_values("collapse_index_mean", ascending=False)[["model_family", "n_judged", "collapse_index_mean", "semantic_repetition_mean", "narrative_convergence_mean", "groupthink_mean", "template_rigidity_mean", "novelty_mean", "evidence_grounding_mean"]]
    condition_rank = jc.copy()
    order = {c: i for i, c in enumerate(CONDITION_ORDER)}
    condition_rank["_order"] = condition_rank["condition"].map(lambda c: order.get(c, 99))
    condition_rank = condition_rank.sort_values("_order")[["condition", "n_judged", "collapse_index_mean", "semantic_repetition_mean", "narrative_convergence_mean", "groupthink_mean", "template_rigidity_mean"]]
    group_rank = jg.sort_values("collapse_index_mean", ascending=False)[["group", "n_judged", "collapse_index_mean", "semantic_repetition_mean", "narrative_convergence_mean", "groupthink_mean", "template_rigidity_mean"]]
    model_rank.to_csv(paper / "table_llm_judge_model_ranked.csv", index=False)
    condition_rank.to_csv(paper / "table_llm_judge_condition_ranked.csv", index=False)
    group_rank.to_csv(paper / "table_llm_judge_group_ranked.csv", index=False)

    # Summary stats.
    neg_vendi = int((deltas["delta_vendi_score"] < 0).sum())
    n_delta = len(deltas)
    mean_dv, lo_dv, hi_dv = bootstrap_ci(deltas["delta_vendi_score"].to_numpy())
    mean_dc, lo_dc, hi_dc = bootstrap_ci(deltas["delta_mean_pairwise_cosine"].to_numpy())
    overall_judge = {m: float(judge[m].mean()) for m in JUDGE_METRICS if m in judge}
    overall_judge["collapse_index"] = float(judge["collapse_index"].mean())
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": "qwen/qwen3-embedding-8b",
        "judge_model": "google/gemini-3.1-flash-lite-preview",
        "corpus_rows": int(len(df)),
        "nonseed_rows": int((~df["is_seed_bool"]).sum()),
        "runs_with_q1_q4_embedding_metrics": n_delta,
        "runs_with_vendi_decline": neg_vendi,
        "mean_delta_vendi_score": mean_dv,
        "ci95_delta_vendi_score": [lo_dv, hi_dv],
        "mean_delta_pairwise_cosine": mean_dc,
        "ci95_delta_pairwise_cosine": [lo_dc, hi_dc],
        "judge_rows": int(len(judge)),
        "judge_overall_means": overall_judge,
        "run_level_embedding_judge_pairs": int(len(merged)),
    }
    (paper / "paper_analysis_summary.json").write_text(json.dumps(summary, indent=2))

    pngs = sorted(p.name for p in paper.glob("*.png"))
    report = f"""# Paper-Style Embedding and LLM-as-Judge Analysis\n\nGenerated: {summary['generated_at']}\n\n## Scope\n\nThis folder reframes the archive + full canonical-48 analysis for the paper narrative rather than dashboard exploration. It uses one shared embedding model, `qwen/qwen3-embedding-8b`, to compare all posts in a common semantic space. It then uses one fixed LLM judge, `google/gemini-3.1-flash-lite-preview`, to score a stratified sample across all generation model families, conditions, groups, scales, time bins, and global embedding clusters.\n\nImportant distinction: **one embedding model** and **one judge model** were used for measurement consistency, but **all generation model families** in the corpus are analyzed separately.\n\n## Embedding analysis: semantic narrowing\n\nFor each run and 15-minute bin, we compute:\n\n- **Vendi score / effective semantic diversity** from the cosine kernel. Lower values mean fewer effective semantic items.\n- **Mean pairwise cosine** within the bin. Higher values mean tighter semantic clustering.\n- **Semantic radius** around the bin centroid. Lower values mean tighter concentration.\n\nAcross runs with both first and final bins, Vendi score declines in **{neg_vendi}/{n_delta}** run comparisons. The mean Q4−Q1 Vendi change is **{mean_dv:.3f}** with 95% bootstrap CI **[{lo_dv:.3f}, {hi_dv:.3f}]**. Mean pairwise cosine changes by **{mean_dc:.3f}** with 95% CI **[{lo_dc:.3f}, {hi_dc:.3f}]**.\n\n### Embedding figures\n\n- `fig_embedding_mds_condition_time.png` — paper-style semantic map: same balanced MDS projection colored by condition and by time.\n- `fig_embedding_vendi_over_time_by_group.png` — semantic diversity trajectories by archive group.\n- `fig_embedding_vendi_over_time_by_condition.png` — semantic diversity trajectories by stimulus condition.\n- `fig_embedding_delta_vendi_by_model.png` — early-to-late Vendi deltas by generation model with bootstrap CIs.\n- `fig_embedding_delta_vendi_by_condition.png` — early-to-late Vendi deltas by condition.\n- `fig_embedding_delta_vendi_by_group.png` — early-to-late Vendi deltas by corpus group.\n\n## LLM-as-judge analysis: collapse form and severity\n\nCollapse index is the mean of semantic repetition, narrative convergence, groupthink, and template rigidity. The raw judged sample has **{len(judge):,}** posts. Overall collapse index is **{overall_judge['collapse_index']:.3f}**.\n\n### LLM judge figures\n\n- `fig_llm_judge_model_collapse_dotplot.png` — all generation models ranked by judged collapse.\n- `fig_llm_judge_condition_collapse_dotplot.png` — all stimulus conditions ranked by judged collapse.\n- `fig_llm_judge_model_by_condition_smallmultiples.png` — separate condition plot for each generation model.\n- `fig_llm_judge_model_metric_profiles.png` — model-level score profiles across novelty/repetition/convergence/groupthink/template/evidence.\n- `fig_llm_judge_collapse_label_stackedbars.png` — qualitative collapse-label distribution by generation model.\n- `fig_embedding_delta_vs_llm_judge_collapse.png` — run-level relationship between semantic diversity change and judged collapse.\n\n## Ranked model-level LLM judge table\n\n{md_table(model_rank, max_rows=20)}\n\n## Condition-level LLM judge table\n\n{md_table(condition_rank, max_rows=20)}\n\n## Group-level LLM judge table\n\n{md_table(group_rank, max_rows=20)}\n\n## Files generated\n\nPNG/PDF figure pairs generated in this folder:\n\n{chr(10).join(f'- `{p}` / `{Path(p).with_suffix(".pdf").name}`' for p in pngs)}\n\nCSV tables:\n\n- `embedding_timebin_metrics.csv`\n- `embedding_q4_minus_q1_deltas.csv`\n- `embedding_delta_summary_by_group.csv`\n- `embedding_delta_summary_by_model.csv`\n- `embedding_delta_summary_by_condition.csv`\n- `llm_judge_summary_by_model.csv`\n- `llm_judge_summary_by_condition.csv`\n- `llm_judge_summary_by_group.csv`\n- `llm_judge_summary_by_model_condition.csv`\n- `llm_judge_summary_by_group_condition.csv`\n- `table_llm_judge_model_ranked.csv`\n- `table_llm_judge_condition_ranked.csv`\n- `table_llm_judge_group_ranked.csv`\n\n## Caveats\n\n- Vendi and pairwise metrics are sampled for large bins (`max_bin_n={args.max_bin_n}`) for tractability.\n- The MDS map is a balanced sample (`n≈{args.mds_sample}`), intended as a visual check, not a standalone inferential statistic.\n- LLM judge results are sampled, not exhaustive over all posts.\n- Small groups such as frontier/mixed-model have wider uncertainty because they have fewer posts and judged examples.\n"""
    (paper / "PAPER_STYLE_ANALYSIS.md").write_text(report)
    print(f"Wrote paper-style analysis -> {paper}")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
