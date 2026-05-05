#!/usr/bin/env python3
"""Embedding-based topical convergence analysis for the Ayush reanalysis package.

Uses the already-cached Qwen post embeddings. No API calls are made.

Outputs under:
  analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/topic_convergence/
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
EMBED_MODEL = "qwen/qwen3-embedding-8b"
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)
STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were", "will", "would", "could", "should",
    "have", "has", "had", "not", "but", "you", "your", "our", "their", "they", "them", "its", "it's", "into",
    "about", "what", "when", "where", "which", "while", "there", "here", "than", "then", "also", "just", "like",
    "can", "may", "might", "more", "most", "some", "any", "all", "one", "two", "new", "use", "using", "used",
    "because", "between", "through", "across", "within", "without", "over", "under", "after", "before", "these", "those",
    "i", "we", "he", "she", "it", "as", "is", "am", "be", "to", "of", "in", "on", "at", "by", "or", "an", "a",
}
FAMILY_LABELS = {
    "single_model_final": "Single-model final",
    "base_model_as_tool": "Base model as tool",
    "mixed_model_roster": "Mixed-model roster",
    "obsession_prompting": "Obsession prompting",
}
FAMILY_SHORT = {
    "single_model_final": "Single-model\nfinal",
    "base_model_as_tool": "Base model\nas tool",
    "mixed_model_roster": "Mixed-model\nroster",
    "obsession_prompting": "Obsession\nprompting",
}
FAMILY_ORDER = ["single_model_final", "base_model_as_tool", "mixed_model_roster", "obsession_prompting"]
SCHEME_ORDER = ["fixed_15m", "normalized_quartile"]
SCHEME_LABELS = {"fixed_15m": "fixed 15m", "normalized_quartile": "quartiles"}
SCHEME_COLORS = {"fixed_15m": "#4C78A8", "normalized_quartile": "#F58518"}


def sha1_text(value: str) -> str:
    import hashlib
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


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


def markdown_table(df: pd.DataFrame, max_rows: int = 80) -> str:
    if df.empty:
        return "(empty)"
    d = df.head(max_rows).copy()
    for col in d.columns:
        if pd.api.types.is_float_dtype(d[col]):
            d[col] = d[col].map(lambda x: "" if pd.isna(x) else f"{float(x):.4g}")
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, row in d.iterrows():
        lines.append("| " + " | ".join(str(row[col]) for col in d.columns) + " |")
    return "\n".join(lines)


def load_posts(root: Path) -> pd.DataFrame:
    path = root / "ayush_reanalysis" / "post_index.jsonl"
    rows = [json.loads(line) for line in path.open() if line.strip()]
    df = pd.DataFrame(rows)
    df = df[~df["is_seed"].astype(bool)].copy()
    df["row_uid"] = df["record_id"].astype(str)
    return df.sort_values(["run_uid", "minutes_elapsed", "post_id"]).reset_index(drop=True)


def load_embedding_map(root: Path, model: str) -> dict[str, np.ndarray]:
    db = root / "embedding_cache.sqlite"
    conn = sqlite3.connect(db)
    out: dict[str, np.ndarray] = {}
    for rid, dim, blob in conn.execute("SELECT record_id, dim, embedding FROM embeddings WHERE model=?", (model,)):
        out[str(rid)] = np.frombuffer(blob, dtype=np.float32, count=int(dim)).copy()
    conn.close()
    return out


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "") if len(t) >= 3 and t.lower() not in STOPWORDS and not t.isdigit()]


def bootstrap_ci(vals: Sequence[float], seed: int = 42, reps: int = 2000) -> tuple[float, float]:
    x = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
    if len(x) == 0:
        return math.nan, math.nan
    if len(x) == 1:
        return float(x[0]), float(x[0])
    rng = np.random.default_rng(seed)
    means = np.mean(x[rng.integers(0, len(x), size=(reps, len(x)))], axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_test_p(vals: Sequence[float]) -> float:
    x = np.asarray([v for v in vals if np.isfinite(v) and v != 0], dtype=float)
    n = len(x)
    if n == 0:
        return math.nan
    k = min(int(np.sum(x > 0)), int(np.sum(x < 0)))
    p = 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, p))


def topic_distribution_metrics(topic_ids: Sequence[int], n_topics: int) -> dict[str, Any]:
    n = len(topic_ids)
    if n == 0:
        row = {
            "n_posts": 0,
            "dominant_topic": "",
            "dominant_share": math.nan,
            "topic_entropy": math.nan,
            "topic_entropy_norm": math.nan,
            "effective_topics": math.nan,
            "topic_hhi": math.nan,
        }
        for topic in range(n_topics):
            row[f"topic_{topic+1:02d}_share"] = math.nan
        return row
    counts = Counter(int(t) for t in topic_ids)
    probs = np.asarray([counts.get(topic, 0) / n for topic in range(n_topics)], dtype=float)
    nz = probs[probs > 0]
    entropy = float(-np.sum(nz * np.log(nz))) if len(nz) else 0.0
    dominant = int(np.argmax(probs))
    row = {
        "n_posts": n,
        "dominant_topic": f"T{dominant+1:02d}",
        "dominant_share": float(np.max(probs)),
        "topic_entropy": entropy,
        "topic_entropy_norm": float(entropy / math.log(n_topics)) if n_topics > 1 else math.nan,
        "effective_topics": float(math.exp(entropy)),
        "topic_hhi": float(np.sum(probs * probs)),
    }
    for topic, prob in enumerate(probs):
        row[f"topic_{topic+1:02d}_share"] = float(prob)
    return row


def assign_bins(sub: pd.DataFrame, scheme: str) -> list[tuple[int, str, pd.DataFrame]]:
    if scheme == "fixed_15m":
        return [
            (0, "0-15m", sub[(sub.minutes_elapsed >= 0) & (sub.minutes_elapsed < 15)]),
            (1, "15-30m", sub[(sub.minutes_elapsed >= 15) & (sub.minutes_elapsed < 30)]),
            (2, "30-45m", sub[(sub.minutes_elapsed >= 30) & (sub.minutes_elapsed < 45)]),
            (3, "45-60m", sub[(sub.minutes_elapsed >= 45) & (sub.minutes_elapsed <= 60)]),
        ]
    return [
        (0, "Q1", sub[(sub.normalized_time >= 0) & (sub.normalized_time < .25)]),
        (1, "Q2", sub[(sub.normalized_time >= .25) & (sub.normalized_time < .5)]),
        (2, "Q3", sub[(sub.normalized_time >= .5) & (sub.normalized_time < .75)]),
        (3, "Q4", sub[(sub.normalized_time >= .75) & (sub.normalized_time <= 1.000001)]),
    ]


def summarize_deltas(delta_df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = []
    for (family, scheme), sub in delta_df.groupby(["internal_family_label", "scheme"], dropna=False):
        row = {"internal_family_label": family, "scheme": scheme, "n_runs": int(sub["run_uid"].nunique())}
        for metric in metrics:
            vals = pd.to_numeric(sub[metric], errors="coerce").dropna().to_numpy(dtype=float)
            lo, hi = bootstrap_ci(vals)
            row.update({
                f"{metric}_n_valid": int(len(vals)),
                f"{metric}_mean": float(np.mean(vals)) if len(vals) else math.nan,
                f"{metric}_median": float(np.median(vals)) if len(vals) else math.nan,
                f"{metric}_ci_low": lo,
                f"{metric}_ci_high": hi,
                f"{metric}_n_negative": int(np.sum(vals < 0)) if len(vals) else 0,
                f"{metric}_n_positive": int(np.sum(vals > 0)) if len(vals) else 0,
                f"{metric}_sign_p": sign_test_p(vals),
            })
        rows.append(row)
    out = pd.DataFrame(rows)
    order = {(fam, scheme): i for i, (fam, scheme) in enumerate((f, s) for f in FAMILY_ORDER for s in SCHEME_ORDER)}
    if not out.empty:
        out["_order"] = out.apply(lambda r: order.get((r["internal_family_label"], r["scheme"]), 999), axis=1)
        out = out.sort_values("_order").drop(columns=["_order"])
    return out


def bar_delta(summary: pd.DataFrame, metric: str, title: str, ylabel: str, out_path: Path) -> None:
    rows = summary.copy()
    rows["family_label"] = rows["internal_family_label"].map(FAMILY_SHORT).fillna(rows["internal_family_label"])
    rows["scheme_label"] = rows["scheme"].map(SCHEME_LABELS).fillna(rows["scheme"])
    rows["x_label"] = rows["family_label"] + "\n" + rows["scheme_label"] + "\n(n=" + rows[f"{metric}_n_valid"].fillna(0).astype(int).astype(str) + ")"
    means = rows[f"{metric}_mean"].astype(float).to_numpy()
    lows = rows[f"{metric}_ci_low"].astype(float).to_numpy()
    highs = rows[f"{metric}_ci_high"].astype(float).to_numpy()
    yerr = np.vstack([means - lows, highs - means])
    x = np.arange(len(rows))
    colors = rows["scheme"].map(SCHEME_COLORS).fillna("#777777").to_list()
    fig, ax = plt.subplots(figsize=(11, 5.8))
    ax.bar(x, means, yerr=yerr, capsize=4, color=colors, edgecolor="#333333", linewidth=.6)
    ax.axhline(0, color="#111111", linewidth=.9)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xticks(x)
    ax.set_xticklabels(rows["x_label"], fontsize=8)
    ax.grid(axis="y", alpha=.25)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_path.with_suffix(f".{ext}"), dpi=220, bbox_inches="tight")
    plt.close(fig)


def line_trajectories(time_df: pd.DataFrame, metric: str, scheme: str, title: str, ylabel: str, out_path: Path) -> None:
    df = time_df[time_df["scheme"] == scheme].copy()
    rows = df.groupby(["internal_family_label", "bin_idx", "bin_label"], as_index=False)[metric].mean()
    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    for family in FAMILY_ORDER:
        sub = rows[rows["internal_family_label"] == family].sort_values("bin_idx")
        if sub.empty:
            continue
        ax.plot(sub["bin_label"], sub[metric], marker="o", linewidth=2, label=FAMILY_LABELS.get(family, family))
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Time bin")
    ax.grid(alpha=.25)
    ax.legend(frameon=False, fontsize=8)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_path.with_suffix(f".{ext}"), dpi=220, bbox_inches="tight")
    plt.close(fig)


def late_distribution_heatmap(time_df: pd.DataFrame, n_topics: int, topic_labels: dict[int, str], out_path: Path) -> None:
    df = time_df[time_df["bin_idx"] == 3].copy()
    share_cols = [f"topic_{i+1:02d}_share" for i in range(n_topics)]
    mat_rows, ylabels = [], []
    for family in FAMILY_ORDER:
        sub = df[(df["internal_family_label"] == family) & (df["scheme"] == ("normalized_quartile" if family == "obsession_prompting" else "fixed_15m"))]
        if sub.empty:
            continue
        mat_rows.append(sub[share_cols].mean().to_numpy(dtype=float))
        ylabels.append(FAMILY_LABELS.get(family, family))
    mat = np.vstack(mat_rows) if mat_rows else np.zeros((0, n_topics))
    fig, ax = plt.subplots(figsize=(max(9, n_topics * .75), 4.8))
    im = ax.imshow(mat, aspect="auto", cmap="Blues", vmin=0, vmax=max(.2, float(np.nanmax(mat)) if mat.size else .2))
    ax.set_yticks(np.arange(len(ylabels)))
    ax.set_yticklabels(ylabels, fontsize=9)
    xlabels = [f"T{i+1:02d}\n{topic_labels.get(i, '')}" for i in range(n_topics)]
    ax.set_xticks(np.arange(n_topics))
    ax.set_xticklabels(xlabels, rotation=45, ha="right", fontsize=8)
    ax.set_title("Late-bin embedding topic distribution by family")
    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label("Mean share of posts")
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_path.with_suffix(f".{ext}"), dpi=220, bbox_inches="tight")
    plt.close(fig)


def svd_topic_map(df_unique: pd.DataFrame, z2: np.ndarray, labels: np.ndarray, n_topics: int, out_path: Path) -> None:
    rng = np.random.default_rng(42)
    n = min(6000, len(df_unique))
    idx = rng.choice(len(df_unique), size=n, replace=False) if len(df_unique) > n else np.arange(len(df_unique))
    fig, ax = plt.subplots(figsize=(7.5, 6.2))
    sc = ax.scatter(z2[idx, 0], z2[idx, 1], c=labels[idx], s=4, cmap="tab20", alpha=.45, linewidths=0)
    centers = []
    for topic in range(n_topics):
        pts = z2[labels == topic]
        if len(pts):
            center = pts.mean(axis=0)
            centers.append(center)
            ax.text(center[0], center[1], f"T{topic+1:02d}", weight="bold", fontsize=10, ha="center", va="center", bbox={"boxstyle":"round,pad=0.18", "facecolor":"white", "alpha":.75, "edgecolor":"#444444"})
    ax.set_title("Embedding topics in 2D SVD projection")
    ax.set_xlabel("SVD 1")
    ax.set_ylabel("SVD 2")
    ax.grid(alpha=.15)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    fig.tight_layout()
    for ext in ["png", "pdf"]:
        fig.savefig(out_path.with_suffix(f".{ext}"), dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--model", default=EMBED_MODEL)
    parser.add_argument("--n-topics", type=int, default=12)
    parser.add_argument("--svd-components", type=int, default=50)
    args = parser.parse_args()

    root = Path(args.out_dir)
    out = root / "ayush_reanalysis" / "topic_convergence"
    out.mkdir(parents=True, exist_ok=True)

    df = load_posts(root)
    emb_map = load_embedding_map(root, args.model)
    missing = int((~df["record_id"].isin(emb_map.keys())).sum())
    if missing:
        raise SystemExit(f"missing embeddings for {missing} current non-seed rows")

    # Fit clusters on unique row IDs so exact duplicate rows do not overweight the topic model.
    df_unique = df.drop_duplicates("record_id").copy().reset_index(drop=True)
    ids = df_unique["record_id"].astype(str).to_list()
    mat = np.vstack([emb_map[rid] for rid in ids]).astype(np.float32)
    mat = normalize(mat, norm="l2", copy=False)
    n_comp = min(args.svd_components, mat.shape[1] - 1, mat.shape[0] - 1)
    z = TruncatedSVD(n_components=n_comp, random_state=42).fit_transform(mat).astype(np.float32)
    z = normalize(z, norm="l2", copy=False)
    km = MiniBatchKMeans(n_clusters=args.n_topics, random_state=42, batch_size=2048, n_init=10)
    raw_labels = km.fit_predict(z)

    # Re-map cluster IDs by size so T01 is the largest topic, T02 the next largest, etc.
    counts = Counter(int(x) for x in raw_labels)
    remap = {old: new for new, (old, _) in enumerate(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))}
    labels = np.asarray([remap[int(x)] for x in raw_labels], dtype=int)
    df_unique["topic_id"] = labels
    id_to_topic = dict(zip(df_unique["record_id"].astype(str), labels))
    df["topic_id"] = df["record_id"].astype(str).map(id_to_topic).astype(int)

    # 2D projection for plotting.
    z2 = TruncatedSVD(n_components=2, random_state=43).fit_transform(mat).astype(np.float32)

    # Topic keywords from cluster-specific token counts.
    topic_counts = {i: Counter() for i in range(args.n_topics)}
    topic_n_posts = Counter()
    for row in df_unique.itertuples(index=False):
        topic = int(row.topic_id)
        topic_n_posts[topic] += 1
        topic_counts[topic].update(tokenize(f"{getattr(row, 'title', '')} {getattr(row, 'content', '')}"))
    keyword_rows = []
    topic_labels: dict[int, str] = {}
    for topic in range(args.n_topics):
        terms = [term for term, _ in topic_counts[topic].most_common(8)]
        topic_labels[topic] = ", ".join(terms[:3])
        keyword_rows.append({"topic": f"T{topic+1:02d}", "n_unique_posts": int(topic_n_posts[topic]), "keywords": ", ".join(terms)})
    write_csv(out / "topic_keywords.csv", keyword_rows)
    (out / "topic_keywords.md").write_text("# Embedding Topic Keywords\n\n" + markdown_table(pd.DataFrame(keyword_rows), 50) + "\n")

    assignment_rows = []
    for row in df.itertuples(index=False):
        assignment_rows.append({
            "record_id": row.record_id,
            "run_uid": row.run_uid,
            "internal_family_label": row.internal_family_label,
            "display_family_label": row.display_family_label,
            "model_family": row.model_family,
            "model_display": row.model_display,
            "roster_name": row.roster_name,
            "condition": row.condition,
            "scale": row.scale,
            "n_agents": int(row.n_agents),
            "run_id": row.run_id,
            "minutes_elapsed": float(row.minutes_elapsed),
            "normalized_time": float(row.normalized_time),
            "author_name": row.author_name,
            "topic": f"T{int(row.topic_id)+1:02d}",
            "topic_id": int(row.topic_id),
        })
    write_csv(out / "topic_assignments.csv", assignment_rows)

    time_rows = []
    delta_rows = []
    meta_cols = ["internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]
    for run_uid, sub in df.groupby("run_uid", dropna=False):
        first = sub.iloc[0]
        schemes = ["normalized_quartile"] if first.internal_family_label == "obsession_prompting" else ["fixed_15m", "normalized_quartile"]
        for scheme in schemes:
            b_rows = []
            for bi, label, b in assign_bins(sub, scheme):
                row = {"run_uid": run_uid, "scheme": scheme, "bin_idx": bi, "bin_label": label}
                row.update(topic_distribution_metrics(b["topic_id"].tolist(), args.n_topics))
                row["n_agents_observed"] = int(b["author_name"].nunique()) if len(b) else 0
                for col in meta_cols:
                    row[col] = first[col]
                time_rows.append(row)
                b_rows.append(row)
            d = {"run_uid": run_uid, "scheme": scheme, "first_bin": b_rows[0]["bin_label"], "final_bin": b_rows[-1]["bin_label"]}
            for metric in ["dominant_share", "topic_entropy_norm", "effective_topics", "topic_hhi"]:
                a, b = b_rows[0][metric], b_rows[-1][metric]
                d[f"delta_{metric}"] = (b - a) if np.isfinite(a) and np.isfinite(b) else math.nan
            d["first_n_posts"] = b_rows[0]["n_posts"]
            d["final_n_posts"] = b_rows[-1]["n_posts"]
            for col in meta_cols:
                d[col] = first[col]
            delta_rows.append(d)

    write_csv(out / "topic_run_timebin_metrics.csv", time_rows)
    write_csv(out / "topic_run_deltas.csv", delta_rows)
    time_df = pd.DataFrame(time_rows)
    delta_df = pd.DataFrame(delta_rows)
    summary = summarize_deltas(delta_df, ["delta_dominant_share", "delta_topic_entropy_norm", "delta_effective_topics", "delta_topic_hhi"])
    summary.to_csv(out / "topic_summary_by_family.csv", index=False, lineterminator="\n")

    bar_delta(summary, "delta_dominant_share", "Run-level change in dominant embedding-topic share", "Δ dominant topic share", out / "topic_dominant_share_delta_by_family")
    bar_delta(summary, "delta_effective_topics", "Run-level change in effective number of embedding topics", "Δ effective topics", out / "topic_effective_topics_delta_by_family")
    bar_delta(summary, "delta_topic_entropy_norm", "Run-level change in normalized embedding-topic entropy", "Δ normalized topic entropy", out / "topic_entropy_delta_by_family")
    line_trajectories(time_df, "dominant_share", "normalized_quartile", "Dominant embedding-topic share over normalized run time", "Dominant topic share", out / "topic_dominant_share_trajectories")
    line_trajectories(time_df, "effective_topics", "normalized_quartile", "Effective embedding topics over normalized run time", "Effective topics", out / "topic_effective_topics_trajectories")
    late_distribution_heatmap(time_df, args.n_topics, topic_labels, out / "topic_late_distribution_heatmap")
    svd_topic_map(df_unique, z2, labels, args.n_topics, out / "embedding_topic_svd_map")

    selected = summary[[
        "internal_family_label", "scheme", "n_runs",
        "delta_dominant_share_mean", "delta_dominant_share_ci_low", "delta_dominant_share_ci_high",
        "delta_topic_entropy_norm_mean", "delta_effective_topics_mean", "delta_topic_hhi_mean",
    ]].copy()
    selected["family"] = selected["internal_family_label"].map(FAMILY_LABELS).fillna(selected["internal_family_label"])
    selected = selected[["family", "scheme", "n_runs", "delta_dominant_share_mean", "delta_dominant_share_ci_low", "delta_dominant_share_ci_high", "delta_topic_entropy_norm_mean", "delta_effective_topics_mean", "delta_topic_hhi_mean"]]
    report = (
        "# Embedding-Based Topic Convergence Summary\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"Embedding model: `{args.model}`. Topic model: MiniBatchKMeans over {n_comp}-D SVD-reduced, L2-normalized embeddings. No API calls were made.\n\n"
        "Interpretation: increasing dominant-topic share / HHI and decreasing topic entropy / effective topics indicate topical convergence.\n\n"
        "## Run-level delta summary\n\n"
        + markdown_table(selected, 50)
        + "\n\n## Topic keywords\n\n"
        + markdown_table(pd.DataFrame(keyword_rows), 50)
        + "\n\n## Figures\n\n"
        "- `topic_dominant_share_delta_by_family.png`\n"
        "- `topic_effective_topics_delta_by_family.png`\n"
        "- `topic_entropy_delta_by_family.png`\n"
        "- `topic_dominant_share_trajectories.png`\n"
        "- `topic_effective_topics_trajectories.png`\n"
        "- `topic_late_distribution_heatmap.png`\n"
        "- `embedding_topic_svd_map.png`\n"
    )
    (out / "TOPIC_CONVERGENCE_SUMMARY.md").write_text(report)
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": args.model,
        "n_topics": args.n_topics,
        "svd_components": int(n_comp),
        "n_nonseed_rows": int(len(df)),
        "n_unique_record_ids": int(len(df_unique)),
        "missing_embeddings": int(missing),
        "outputs": sorted(p.name for p in out.iterdir() if p.is_file()),
    }
    (out / "topic_convergence_summary.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote topic convergence outputs to {out}")


if __name__ == "__main__":
    main()
