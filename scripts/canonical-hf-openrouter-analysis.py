#!/usr/bin/env python3
"""Canonical HuggingFace Moltbook embedding + LLM-judge analysis.

This script is designed for the downloaded dataset:

    exports/huggingface/agokrani/moltbook-entropy-collapse-canonical-48/data

It provides resumable OpenRouter-backed embeddings for every agent post, then a
context-aware LLM-as-a-judge pass on a stratified sample. Outputs are written to
`analysis/llm-judge-canonical-hf/` by default.

Subcommands:
  index             Normalize canonical HF runs into posts_index.jsonl/csv.
  embed             Embed agent posts with OpenRouter, cached in SQLite.
  embedding-report  Produce embedding summaries and figures from cached embeddings.
  sample-judge      Build context-aware stratified judge sample.
  judge             Run structured LLM-as-a-judge with OpenRouter chat model.
  aggregate-judge   Aggregate judge outputs into CSV/figures/report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import random
import re
import sqlite3
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import numpy as np
import requests

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/moltbook-cache")

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception:  # pragma: no cover
    plt = None

try:
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import normalize
except Exception:  # pragma: no cover
    PCA = None
    normalize = None

try:
    import umap  # type: ignore
except Exception:  # pragma: no cover
    umap = None

try:
    import hdbscan  # type: ignore
except Exception:  # pragma: no cover
    hdbscan = None

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None


DEFAULT_DATA_ROOT = Path("exports/huggingface/agokrani/moltbook-entropy-collapse-canonical-48/data")
DEFAULT_OUT_DIR = Path("analysis/llm-judge-canonical-hf")
DEFAULT_EMBED_MODEL = "qwen/qwen3-embedding-8b"
DEFAULT_JUDGE_MODEL = "google/gemini-3.1-flash-lite-preview"
EMBED_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

SEED_AUTHOR_PREFIXES = ("civiclens_",)
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy seed",
    "mag5": "5 conspiracy seeds",
    "mag25": "25 conspiracy seeds",
    "dom-agi": "25 AGI-hype seeds",
    "dom-tech": "25 tech-humor seeds",
}
CONDITION_COLORS = {
    "mag0": "#8c8c8c",
    "mag1": "#9ecae1",
    "mag5": "#4292c6",
    "mag25": "#08519c",
    "dom-agi": "#f16913",
    "dom-tech": "#756bb1",
}
JUDGE_RUBRIC_VERSION = "entropy-collapse-v1"
SCORE_FIELDS = [
    "novelty",
    "semantic_repetition",
    "narrative_convergence",
    "groupthink",
    "specificity",
    "evidence_grounding",
    "epistemic_caution",
    "template_rigidity",
]


@dataclass
class PostRecord:
    record_id: str
    post_id: str
    model_family: str
    scale: str
    n_agents: int
    run_id: str
    condition: str
    condition_label: str
    author_name: str
    author_display_name: str
    agent_type: str
    agent_description: str
    created_at: str
    minutes_elapsed: float
    time_bin: int
    title: str
    content: str
    text: str
    score: int
    comment_count: int
    submolt: str
    source_path: str
    is_seed: bool

    def to_dict(self) -> dict:
        return asdict(self)


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-")


def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


def parse_time(value: str) -> datetime:
    value = value.replace("Z", "+00:00")
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def condition_from_run_name(name: str) -> str:
    for cond in ["dom-agi", "dom-tech", "mag25", "mag5", "mag1", "mag0"]:
        if cond in name:
            return cond
    return "unknown"


def load_env() -> None:
    if load_dotenv:
        load_dotenv(Path(".env"), override=False)


def require_openrouter_key() -> str:
    load_env()
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise SystemExit(
            "OPENROUTER_API_KEY is not set. Put it in the environment or .env; "
            "the script will not print it."
        )
    return key


def progress(iterable, **kwargs):
    if tqdm is None:
        return iterable
    return tqdm(iterable, **kwargs)


def discover_run_dirs(data_root: Path) -> list[Path]:
    runs = []
    for run_dir in sorted(data_root.glob("*/*/*")):
        if run_dir.is_dir() and (run_dir / "posts.jsonl").exists():
            runs.append(run_dir)
    return runs


def load_agent_map(run_dir: Path) -> dict[str, dict]:
    agents_path = run_dir / "agents.jsonl"
    agents: dict[str, dict] = {}
    if not agents_path.exists():
        return agents
    with agents_path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            agent = json.loads(line)
            name = agent.get("name", "")
            agents[name] = {
                "type": agent.get("type", ""),
                "description": (agent.get("description") or "").strip(),
                "display_name": agent.get("display_name", ""),
            }
    return agents


def load_posts_from_run(run_dir: Path, first_minutes: int = 60, include_seeds: bool = False) -> list[PostRecord]:
    parts = run_dir.parts
    model_family = parts[-3]
    scale_dir = parts[-2]
    n_agents = int(scale_dir.replace("agents-", "")) if scale_dir.startswith("agents-") else 0
    scale = f"n{n_agents}" if n_agents else scale_dir
    run_id = run_dir.name
    condition = condition_from_run_name(run_id)
    condition_label = CONDITION_LABELS.get(condition, condition)
    agents = load_agent_map(run_dir)

    raw_posts = []
    with (run_dir / "posts.jsonl").open() as handle:
        for line in handle:
            if not line.strip():
                continue
            raw_posts.append(json.loads(line))

    agent_times = []
    for post in raw_posts:
        author = post.get("author_name", "") or ""
        is_seed = author.startswith(SEED_AUTHOR_PREFIXES)
        if not is_seed and post.get("created_at"):
            agent_times.append(parse_time(post["created_at"]))
    if not agent_times and raw_posts:
        agent_times = [parse_time(p["created_at"]) for p in raw_posts if p.get("created_at")]
    if not agent_times:
        return []
    start = min(agent_times)

    records: list[PostRecord] = []
    for post in raw_posts:
        author = post.get("author_name", "") or ""
        is_seed = author.startswith(SEED_AUTHOR_PREFIXES)
        if is_seed and not include_seeds:
            continue
        if not post.get("created_at"):
            continue
        created = parse_time(post["created_at"])
        minutes = (created - start).total_seconds() / 60.0
        if minutes < 0 or minutes > first_minutes:
            continue
        time_bin = min(3, max(0, int(minutes // 15)))
        title = (post.get("title") or "").strip()
        content = (post.get("content") or "").strip()
        text = (title + "\n\n" + content).strip()
        agent = agents.get(author, {})
        post_id = post.get("id") or sha1_text(f"{run_dir}:{title}:{content}:{created.isoformat()}")
        record_id = sha1_text(f"{model_family}/{scale}/{run_id}/{post_id}")
        records.append(PostRecord(
            record_id=record_id,
            post_id=post_id,
            model_family=model_family,
            scale=scale,
            n_agents=n_agents,
            run_id=run_id,
            condition=condition,
            condition_label=condition_label,
            author_name=author,
            author_display_name=post.get("author_display_name") or agent.get("display_name", ""),
            agent_type=agent.get("type", ""),
            agent_description=agent.get("description", ""),
            created_at=post["created_at"],
            minutes_elapsed=round(minutes, 4),
            time_bin=time_bin,
            title=title,
            content=content,
            text=text,
            score=int(post.get("score") or 0),
            comment_count=int(post.get("comment_count") or 0),
            submolt=post.get("submolt") or "",
            source_path=str(run_dir / "posts.jsonl"),
            is_seed=is_seed,
        ))
    return sorted(records, key=lambda r: (r.created_at, r.post_id))


def load_records(data_root: Path, first_minutes: int = 60, include_seeds: bool = False) -> list[PostRecord]:
    records: list[PostRecord] = []
    for run_dir in discover_run_dirs(data_root):
        records.extend(load_posts_from_run(run_dir, first_minutes=first_minutes, include_seeds=include_seeds))
    records.sort(key=lambda r: (r.model_family, r.scale, r.condition, r.run_id, r.created_at, r.post_id))
    return records


def read_index(index_path: Path) -> list[PostRecord]:
    records: list[PostRecord] = []
    with index_path.open() as handle:
        for line in handle:
            if not line.strip():
                continue
            data = json.loads(line)
            records.append(PostRecord(**data))
    return records


def write_index(records: list[PostRecord], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "posts_index.jsonl"
    csv_path = out_dir / "posts_index.csv"
    with jsonl_path.open("w") as handle:
        for rec in records:
            handle.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "\n")
    compact_fields = [
        "record_id", "post_id", "model_family", "scale", "n_agents", "run_id", "condition",
        "condition_label", "author_name", "author_display_name", "agent_type", "created_at",
        "minutes_elapsed", "time_bin", "title", "score", "comment_count", "submolt", "is_seed",
    ]
    with csv_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=compact_fields)
        writer.writeheader()
        for rec in records:
            row = rec.to_dict()
            writer.writerow({k: row.get(k, "") for k in compact_fields})


def ensure_embedding_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS embeddings (
            record_id TEXT NOT NULL,
            model TEXT NOT NULL,
            dim INTEGER NOT NULL,
            embedding BLOB NOT NULL,
            text_sha1 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(record_id, model)
        )
    """)
    conn.commit()
    return conn


def cached_record_ids(conn: sqlite3.Connection, model: str) -> set[str]:
    rows = conn.execute("SELECT record_id FROM embeddings WHERE model = ?", (model,)).fetchall()
    return {r[0] for r in rows}


def store_embeddings(conn: sqlite3.Connection, records: Sequence[PostRecord], vectors: np.ndarray, model: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for rec, vec in zip(records, vectors):
        arr = np.asarray(vec, dtype=np.float32)
        rows.append((rec.record_id, model, int(arr.shape[0]), arr.tobytes(), sha1_text(rec.text), now))
    conn.executemany(
        "INSERT OR REPLACE INTO embeddings(record_id, model, dim, embedding, text_sha1, created_at) VALUES(?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


def load_embedding_map(conn: sqlite3.Connection, model: str) -> dict[str, np.ndarray]:
    rows = conn.execute("SELECT record_id, dim, embedding FROM embeddings WHERE model = ?", (model,)).fetchall()
    out: dict[str, np.ndarray] = {}
    for record_id, dim, blob in rows:
        out[record_id] = np.frombuffer(blob, dtype=np.float32, count=dim).copy()
    return out


def openrouter_embed(texts: Sequence[str], model: str, key: str, retries: int = 5, timeout: int = 120) -> np.ndarray:
    payload = {"model": model, "input": list(texts), "encoding_format": "float"}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.post(EMBED_ENDPOINT, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            items = sorted(data["data"], key=lambda x: x.get("index", 0))
            return np.asarray([item["embedding"] for item in items], dtype=np.float32)
        except Exception as exc:  # pragma: no cover - network dependent
            last_err = exc
            sleep = min(30, 2 ** attempt)
            print(f"  embedding request failed attempt={attempt+1}/{retries}: {exc}; sleeping {sleep}s")
            time.sleep(sleep)
    raise RuntimeError(f"OpenRouter embedding failed after {retries} attempts: {last_err}")


def batched_records(records: Sequence[PostRecord], batch_size: int, max_batch_chars: int, max_text_chars: int) -> Iterator[list[PostRecord]]:
    batch: list[PostRecord] = []
    chars = 0
    for rec in records:
        tchars = min(len(rec.text), max_text_chars)
        if batch and (len(batch) >= batch_size or chars + tchars > max_batch_chars):
            yield batch
            batch = []
            chars = 0
        batch.append(rec)
        chars += tchars
    if batch:
        yield batch


def export_npz(records: list[PostRecord], embedding_map: dict[str, np.ndarray], out_path: Path, model: str) -> None:
    ids = [rec.record_id for rec in records if rec.record_id in embedding_map]
    if not ids:
        raise SystemExit("No cached embeddings available to export")
    matrix = np.vstack([embedding_map[rid] for rid in ids]).astype(np.float32)
    rec_by_id = {rec.record_id: rec for rec in records}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        out_path,
        embeddings=matrix,
        record_ids=np.asarray(ids),
        post_ids=np.asarray([rec_by_id[rid].post_id for rid in ids]),
        run_ids=np.asarray([rec_by_id[rid].run_id for rid in ids]),
        model_families=np.asarray([rec_by_id[rid].model_family for rid in ids]),
        scales=np.asarray([rec_by_id[rid].scale for rid in ids]),
        conditions=np.asarray([rec_by_id[rid].condition for rid in ids]),
        embedding_model=np.asarray([model]),
    )
    meta = {
        "embedding_model": model,
        "n_embeddings": len(ids),
        "dim": int(matrix.shape[1]),
        "npz": str(out_path),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path.with_suffix(".json").write_text(json.dumps(meta, indent=2))


def mean_pairwise_cosine(vectors: np.ndarray, rng: random.Random, max_n: int = 700) -> float:
    if vectors.shape[0] < 2:
        return float("nan")
    x = vectors
    if x.shape[0] > max_n:
        idx = rng.sample(range(x.shape[0]), max_n)
        x = x[idx]
    sim = x @ x.T
    iu = np.triu_indices(sim.shape[0], k=1)
    return float(np.mean(sim[iu]))


def centroid_cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    if a.shape[0] == 0 or b.shape[0] == 0:
        return float("nan")
    ca = np.mean(a, axis=0)
    cb = np.mean(b, axis=0)
    denom = float(np.linalg.norm(ca) * np.linalg.norm(cb))
    if denom <= 0:
        return float("nan")
    return float(1.0 - np.dot(ca, cb) / denom)


def make_plots(df, out_dir: Path) -> None:
    if plt is None or pd is None:
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 150, "font.size": 9})

    # PCA condition scatter, sampled for readability.
    plot_df = df.copy()
    if len(plot_df) > 12000:
        plot_df = plot_df.sample(12000, random_state=42)
    fig, ax = plt.subplots(figsize=(9, 7))
    for cond in CONDITION_ORDER:
        sub = plot_df[plot_df["condition"] == cond]
        if len(sub) == 0:
            continue
        ax.scatter(sub["pca_1"], sub["pca_2"], s=4, alpha=0.45, label=CONDITION_LABELS[cond], c=CONDITION_COLORS[cond])
    ax.set_title("Canonical HF post embeddings by condition (PCA)")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend(markerscale=3, frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_condition_pca.png")
    plt.close(fig)

    # Model/scale scatter.
    fig, ax = plt.subplots(figsize=(9, 7))
    for key, sub in plot_df.groupby(["model_family", "scale"]):
        ax.scatter(sub["pca_1"], sub["pca_2"], s=4, alpha=0.42, label=f"{key[0]} {key[1]}")
    ax.set_title("Canonical HF post embeddings by model × scale (PCA)")
    ax.set_xlabel("PC1")
    ax.set_ylabel("PC2")
    ax.legend(markerscale=3, frameon=False, fontsize=7, ncol=2)
    fig.tight_layout()
    fig.savefig(out_dir / "fig_model_scale_pca.png")
    plt.close(fig)

    # Coherence trajectory by condition.
    if {"condition", "time_bin", "mean_pairwise_cosine"}.issubset(df.columns):
        pass


def write_embedding_report(records: list[PostRecord], embedding_map: dict[str, np.ndarray], out_dir: Path, model: str, use_umap: bool = False) -> None:
    if pd is None or PCA is None or normalize is None:
        raise SystemExit("pandas, sklearn, and numpy are required for embedding-report")
    out_dir.mkdir(parents=True, exist_ok=True)
    usable = [rec for rec in records if rec.record_id in embedding_map]
    if not usable:
        raise SystemExit("No matching cached embeddings found")
    ids = [rec.record_id for rec in usable]
    raw = np.vstack([embedding_map[rid] for rid in ids]).astype(np.float32)
    x = normalize(raw)

    pca = PCA(n_components=2, random_state=42)
    coords = pca.fit_transform(x)

    umap_coords = None
    if use_umap and umap is not None:
        reducer = umap.UMAP(n_components=2, metric="cosine", random_state=42, min_dist=0.1, n_neighbors=30)
        umap_coords = reducer.fit_transform(x)

    rows = []
    for i, rec in enumerate(usable):
        d = rec.to_dict()
        d.pop("content", None)
        d.pop("text", None)
        d.pop("agent_description", None)
        d["pca_1"] = float(coords[i, 0])
        d["pca_2"] = float(coords[i, 1])
        if umap_coords is not None:
            d["umap_1"] = float(umap_coords[i, 0])
            d["umap_2"] = float(umap_coords[i, 1])
        rows.append(d)
    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "analysis_data.csv", index=False)

    # Optional HDBSCAN on PCA/UMAP coordinates per condition for a cluster id similar to handoff artifacts.
    if hdbscan is not None:
        cluster_ids = np.full(len(df), -999, dtype=int)
        coord_cols = ["umap_1", "umap_2"] if umap_coords is not None else ["pca_1", "pca_2"]
        for cond in CONDITION_ORDER:
            idx = df.index[df["condition"] == cond].to_numpy()
            if len(idx) < 30:
                continue
            points = df.loc[idx, coord_cols].to_numpy()
            min_cluster_size = max(10, int(len(idx) * 0.03))
            labels = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=5).fit_predict(points)
            cluster_ids[idx] = labels
        df["cluster_id"] = cluster_ids
        df.to_csv(out_dir / "analysis_data.csv", index=False)

    rng = random.Random(42)
    rec_index = {rid: i for i, rid in enumerate(ids)}
    run_rows = []
    bin_rows = []
    for (model_family, scale, condition, run_id), sub in df.groupby(["model_family", "scale", "condition", "run_id"]):
        idx = [rec_index[rid] for rid in sub["record_id"]]
        xv = x[idx]
        early_idx = [rec_index[rid] for rid in sub[sub["time_bin"] == 0]["record_id"]]
        late_idx = [rec_index[rid] for rid in sub[sub["time_bin"] == 3]["record_id"]]
        early = x[early_idx] if early_idx else np.empty((0, x.shape[1]))
        late = x[late_idx] if late_idx else np.empty((0, x.shape[1]))
        run_rows.append({
            "model_family": model_family,
            "scale": scale,
            "condition": condition,
            "run_id": run_id,
            "n_posts": len(sub),
            "mean_pairwise_cosine": mean_pairwise_cosine(xv, rng),
            "early_pairwise_cosine": mean_pairwise_cosine(early, rng),
            "late_pairwise_cosine": mean_pairwise_cosine(late, rng),
            "delta_late_minus_early": mean_pairwise_cosine(late, rng) - mean_pairwise_cosine(early, rng) if len(early) >= 2 and len(late) >= 2 else float("nan"),
            "early_late_centroid_distance": centroid_cosine_distance(early, late),
        })
        for time_bin in range(4):
            bsub = sub[sub["time_bin"] == time_bin]
            if len(bsub) < 2:
                val = float("nan")
            else:
                bidx = [rec_index[rid] for rid in bsub["record_id"]]
                val = mean_pairwise_cosine(x[bidx], rng)
            bin_rows.append({
                "model_family": model_family,
                "scale": scale,
                "condition": condition,
                "run_id": run_id,
                "time_bin": time_bin,
                "bin_start_min": time_bin * 15,
                "bin_end_min": (time_bin + 1) * 15,
                "n_posts": len(bsub),
                "mean_pairwise_cosine": val,
            })
    run_df = pd.DataFrame(run_rows)
    bin_df = pd.DataFrame(bin_rows)
    run_df.to_csv(out_dir / "run_embedding_summary.csv", index=False)
    bin_df.to_csv(out_dir / "timebin_embedding_summary.csv", index=False)

    group_cols = ["model_family", "scale", "condition"]
    condition_summary = run_df.groupby(group_cols).agg(
        n_runs=("run_id", "nunique"),
        n_posts=("n_posts", "sum"),
        mean_pairwise_cosine=("mean_pairwise_cosine", "mean"),
        early_pairwise_cosine=("early_pairwise_cosine", "mean"),
        late_pairwise_cosine=("late_pairwise_cosine", "mean"),
        delta_late_minus_early=("delta_late_minus_early", "mean"),
        early_late_centroid_distance=("early_late_centroid_distance", "mean"),
    ).reset_index()
    condition_summary.to_csv(out_dir / "condition_embedding_summary.csv", index=False)

    make_plots(df, out_dir)
    if plt is not None:
        # Time-bin coherence line plot.
        agg = bin_df.groupby(["condition", "time_bin"], as_index=False)["mean_pairwise_cosine"].mean()
        fig, ax = plt.subplots(figsize=(8, 5))
        for cond in CONDITION_ORDER:
            sub = agg[agg["condition"] == cond]
            ax.plot(sub["time_bin"] * 15 + 7.5, sub["mean_pairwise_cosine"], marker="o", label=CONDITION_LABELS[cond], color=CONDITION_COLORS[cond])
        ax.set_title("Within-run semantic coherence over time")
        ax.set_xlabel("Minutes")
        ax.set_ylabel("Mean pairwise cosine")
        ax.legend(frameon=False, fontsize=8)
        fig.tight_layout()
        fig.savefig(out_dir / "fig_coherence_over_time.png")
        plt.close(fig)

        # Heatmap-like condition summary using imshow.
        pivot = condition_summary.pivot_table(index="model_family", columns="condition", values="late_pairwise_cosine", aggfunc="mean")
        pivot = pivot.reindex(columns=CONDITION_ORDER)
        fig, ax = plt.subplots(figsize=(8, 4))
        im = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="viridis")
        ax.set_xticks(range(len(pivot.columns)), [CONDITION_LABELS[c] for c in pivot.columns], rotation=35, ha="right")
        ax.set_yticks(range(len(pivot.index)), pivot.index)
        ax.set_title("Late-window semantic coherence by model and condition")
        fig.colorbar(im, ax=ax, label="Mean pairwise cosine")
        fig.tight_layout()
        fig.savefig(out_dir / "fig_late_coherence_heatmap.png")
        plt.close(fig)

    report = f"""# Canonical HF Embedding Analysis\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n- Dataset records indexed: {len(records):,}\n- Records with cached embeddings: {len(usable):,}\n- Embedding model: `{model}`\n- Embedding dimensionality: {raw.shape[1]}\n\n## Outputs\n\n- `analysis_data.csv`: per-post metadata plus PCA/cluster coordinates.\n- `run_embedding_summary.csv`: per-run coherence and early/late drift metrics.\n- `timebin_embedding_summary.csv`: 15-minute binned within-run coherence.\n- `condition_embedding_summary.csv`: model × scale × condition aggregates.\n- `fig_condition_pca.png`, `fig_model_scale_pca.png`, `fig_coherence_over_time.png`, `fig_late_coherence_heatmap.png`.\n\n## Notes\n\nCosine metrics are computed on L2-normalized OpenRouter embeddings. Pairwise means are sampled for large bins to keep the run tractable and reproducible (`random_state=42`).\n"""
    (out_dir / "EMBEDDING_ANALYSIS.md").write_text(report)


def build_judge_sample(records: list[PostRecord], out_path: Path, posts_per_cell: int, seed: int, embedding_map: dict[str, np.ndarray] | None = None) -> list[dict]:
    rng = random.Random(seed)
    groups: dict[tuple[str, str, str], list[PostRecord]] = {}
    for rec in records:
        groups.setdefault((rec.model_family, rec.scale, rec.condition), []).append(rec)
    sample: list[PostRecord] = []
    for key, posts in sorted(groups.items()):
        posts = sorted(posts, key=lambda r: (r.created_at, r.post_id))
        # Balance across four time bins.
        chosen: list[PostRecord] = []
        per_bin = max(1, posts_per_cell // 4)
        remainder = posts_per_cell - per_bin * 4
        for b in range(4):
            pool = [p for p in posts if p.time_bin == b]
            k = per_bin + (1 if b < remainder else 0)
            if len(pool) <= k:
                chosen.extend(pool)
            else:
                chosen.extend(rng.sample(pool, k))
        if len(chosen) < min(posts_per_cell, len(posts)):
            have = {c.record_id for c in chosen}
            rest = [p for p in posts if p.record_id not in have]
            chosen.extend(rng.sample(rest, min(len(rest), min(posts_per_cell, len(posts)) - len(chosen))))
        sample.extend(chosen[:posts_per_cell])

    by_run: dict[str, list[PostRecord]] = {}
    for rec in records:
        by_run.setdefault(rec.run_id + ":" + rec.model_family + ":" + rec.scale, []).append(rec)
    for posts in by_run.values():
        posts.sort(key=lambda r: (r.created_at, r.post_id))

    emb_norm = None
    emb_ids = None
    if embedding_map:
        emb_ids = list(embedding_map.keys())
        mat = np.vstack([embedding_map[rid] for rid in emb_ids]).astype(np.float32)
        emb_norm = mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-12)

    sample_rows: list[dict] = []
    for rec in sorted(sample, key=lambda r: (r.model_family, r.scale, r.condition, r.run_id, r.created_at)):
        run_key = rec.run_id + ":" + rec.model_family + ":" + rec.scale
        run_posts = by_run[run_key]
        pos = next((i for i, p in enumerate(run_posts) if p.record_id == rec.record_id), -1)
        previous = run_posts[max(0, pos - 5):pos] if pos >= 0 else []
        prev_context = [
            {"minutes_elapsed": p.minutes_elapsed, "author": p.author_name, "title": p.title[:180], "content": p.content[:350]}
            for p in previous
        ]
        nearest_context = []
        if emb_norm is not None and emb_ids is not None and rec.record_id in embedding_map:
            rec_vec = embedding_map[rec.record_id].astype(np.float32)
            rec_vec = rec_vec / max(float(np.linalg.norm(rec_vec)), 1e-12)
            sims = emb_norm @ rec_vec
            candidates = []
            for i, rid in enumerate(emb_ids):
                if rid == rec.record_id:
                    continue
                candidates.append((float(sims[i]), rid))
            candidates.sort(reverse=True)
            rec_by_id = {r.record_id: r for r in records}
            for sim, rid in candidates[:3]:
                p = rec_by_id.get(rid)
                if p:
                    nearest_context.append({
                        "similarity": round(sim, 4),
                        "model_family": p.model_family,
                        "scale": p.scale,
                        "condition": p.condition,
                        "title": p.title[:180],
                        "content": p.content[:350],
                    })
        sample_rows.append({
            "record": rec.to_dict(),
            "previous_run_context": prev_context,
            "nearest_embedding_context": nearest_context,
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as handle:
        for row in sample_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return sample_rows


JUDGE_SCHEMA = {
    "name": "entropy_collapse_judgment",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "novelty": {"type": "integer", "minimum": 1, "maximum": 5},
            "semantic_repetition": {"type": "integer", "minimum": 1, "maximum": 5},
            "narrative_convergence": {"type": "integer", "minimum": 1, "maximum": 5},
            "groupthink": {"type": "integer", "minimum": 1, "maximum": 5},
            "specificity": {"type": "integer", "minimum": 1, "maximum": 5},
            "evidence_grounding": {"type": "integer", "minimum": 1, "maximum": 5},
            "epistemic_caution": {"type": "integer", "minimum": 1, "maximum": 5},
            "template_rigidity": {"type": "integer", "minimum": 1, "maximum": 5},
            "collapse_label": {
                "type": "string",
                "enum": ["novel_contribution", "mild_rephrase", "frame_convergence", "template_repetition", "off_topic"]
            },
            "claim_behavior": {
                "type": "string",
                "enum": ["no_checkable_claim", "specific_claim_supported", "specific_claim_unsupported", "conspiracy_or_speculative", "debunking_or_correction"]
            },
            "dominant_frame": {"type": "string"},
            "rationale": {"type": "string"}
        },
        "required": [
            "novelty", "semantic_repetition", "narrative_convergence", "groupthink",
            "specificity", "evidence_grounding", "epistemic_caution", "template_rigidity",
            "collapse_label", "claim_behavior", "dominant_frame", "rationale"
        ],
        "additionalProperties": False,
    }
}


def ensure_judge_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS judgments (
            record_id TEXT NOT NULL,
            judge_model TEXT NOT NULL,
            rubric_version TEXT NOT NULL,
            judgment_json TEXT NOT NULL,
            prompt_sha1 TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(record_id, judge_model, rubric_version)
        )
    """)
    conn.commit()
    return conn


def cached_judgment_ids(conn: sqlite3.Connection, judge_model: str, rubric_version: str) -> set[str]:
    rows = conn.execute(
        "SELECT record_id FROM judgments WHERE judge_model = ? AND rubric_version = ?",
        (judge_model, rubric_version),
    ).fetchall()
    return {r[0] for r in rows}


def judge_prompt(sample_row: dict) -> str:
    rec = sample_row["record"]
    blinded = {
        "condition": "hidden",
        "model_family": "hidden",
        "scale": rec.get("scale"),
        "time_bin": rec.get("time_bin"),
        "minutes_elapsed": rec.get("minutes_elapsed"),
    }
    return f"""You are judging AI-agent discourse from a Reddit-like multi-agent social simulation.

Your task is NOT to judge writing quality. Your task is to identify entropy-collapse behavior: semantic repetition, narrative convergence, groupthink, and templated discourse.

Scoring rubric, 1-5:
- novelty: 1 = no new substantive contribution; 5 = clearly new idea/evidence/frame.
- semantic_repetition: 1 = not repetitive; 5 = strongly repeats nearby/similar context.
- narrative_convergence: 1 = independent frame; 5 = tightly follows a dominant shared frame.
- groupthink: 1 = independent/critical; 5 = uncritically reinforces consensus.
- specificity: 1 = vague/generic; 5 = concrete claims/details/examples.
- evidence_grounding: 1 = no evidence; 5 = clear evidence/source/reasoning.
- epistemic_caution: 1 = overconfident; 5 = careful uncertainty/limitations.
- template_rigidity: 1 = organic; 5 = formulaic/checklist/receipt/template-like.

Collapse label:
- novel_contribution: substantially adds a new idea.
- mild_rephrase: mostly rewords existing ideas.
- frame_convergence: different wording but converges on same narrative frame.
- template_repetition: repeats a visible posting format/template.
- off_topic: unrelated to local discourse.

Claim behavior:
- no_checkable_claim
- specific_claim_supported
- specific_claim_unsupported
- conspiracy_or_speculative
- debunking_or_correction

Blinded metadata:
{json.dumps(blinded, ensure_ascii=False)}

Current post:
Title: {rec.get('title','')}
Content:
{(rec.get('content') or '')[:2200]}

Previous posts in same run immediately before this post:
{json.dumps(sample_row.get('previous_run_context', []), ensure_ascii=False, indent=2)}

Most embedding-similar posts from the corpus, if available:
{json.dumps(sample_row.get('nearest_embedding_context', []), ensure_ascii=False, indent=2)}

Return JSON only following the required schema. Keep rationale under 45 words.
"""


def openrouter_judge(prompt: str, model: str, key: str, retries: int = 5, timeout: int = 90) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": 700,
        "response_format": {"type": "json_schema", "json_schema": JUDGE_SCHEMA},
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.post(CHAT_ENDPOINT, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            content = msg.get("content") or msg.get("reasoning") or ""
            if "```" in content:
                for part in content.split("```"):
                    part = part.strip()
                    if part.startswith("json"):
                        part = part[4:].strip()
                    if part.startswith("{"):
                        content = part
                        break
            return json.loads(content)
        except Exception as exc:  # pragma: no cover - network dependent
            last_err = exc
            sleep = min(30, 2 ** attempt)
            print(f"  judge request failed attempt={attempt+1}/{retries}: {exc}; sleeping {sleep}s")
            time.sleep(sleep)
    raise RuntimeError(f"OpenRouter judge failed after {retries} attempts: {last_err}")


def store_judgment(conn: sqlite3.Connection, record_id: str, judge_model: str, prompt: str, judgment: dict) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO judgments(record_id, judge_model, rubric_version, judgment_json, prompt_sha1, created_at) VALUES(?,?,?,?,?,?)",
        (record_id, judge_model, JUDGE_RUBRIC_VERSION, json.dumps(judgment, ensure_ascii=False), sha1_text(prompt), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def load_judgments(conn: sqlite3.Connection, judge_model: str | None = None) -> list[dict]:
    if judge_model:
        rows = conn.execute(
            "SELECT record_id, judge_model, rubric_version, judgment_json, created_at FROM judgments WHERE judge_model = ?",
            (judge_model,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT record_id, judge_model, rubric_version, judgment_json, created_at FROM judgments").fetchall()
    out = []
    for record_id, model, rubric, jtxt, created_at in rows:
        judgment = json.loads(jtxt)
        judgment.update({"record_id": record_id, "judge_model": model, "rubric_version": rubric, "judged_at": created_at})
        out.append(judgment)
    return out


def aggregate_judge(records: list[PostRecord], judgments: list[dict], sample_path: Path, out_dir: Path) -> None:
    if pd is None:
        raise SystemExit("pandas is required for aggregate-judge")
    out_dir.mkdir(parents=True, exist_ok=True)
    sample_ids: set[str] | None = None
    if sample_path.exists():
        sample_ids = set()
        with sample_path.open() as handle:
            for line in handle:
                if line.strip():
                    sample_ids.add(json.loads(line)["record"]["record_id"])
    rec_by_id = {r.record_id: r for r in records}
    rows = []
    for j in judgments:
        if sample_ids is not None and j["record_id"] not in sample_ids:
            continue
        rec = rec_by_id.get(j["record_id"])
        if not rec:
            continue
        row = rec.to_dict()
        row.pop("content", None)
        row.pop("text", None)
        row.pop("agent_description", None)
        row.update(j)
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        raise SystemExit("No judgments matched records")
    df.to_json(out_dir / "judge_results.jsonl", orient="records", lines=True, force_ascii=False)
    df.to_csv(out_dir / "judge_results.csv", index=False)

    group_cols = ["model_family", "scale", "condition"]
    agg_spec = {field: ["mean", "std", "count"] for field in SCORE_FIELDS if field in df.columns}
    summary = df.groupby(group_cols).agg(agg_spec)
    summary.columns = ["_".join(col).strip("_") for col in summary.columns.values]
    summary = summary.reset_index()
    summary.to_csv(out_dir / "judge_summary.csv", index=False)

    label_counts = df.groupby(group_cols + ["collapse_label"]).size().reset_index(name="count")
    totals = df.groupby(group_cols).size().reset_index(name="total")
    label_counts = label_counts.merge(totals, on=group_cols)
    label_counts["proportion"] = label_counts["count"] / label_counts["total"]
    label_counts.to_csv(out_dir / "judge_collapse_label_shares.csv", index=False)

    claim_counts = df.groupby(group_cols + ["claim_behavior"]).size().reset_index(name="count")
    claim_counts = claim_counts.merge(totals, on=group_cols)
    claim_counts["proportion"] = claim_counts["count"] / claim_counts["total"]
    claim_counts.to_csv(out_dir / "judge_claim_behavior_shares.csv", index=False)

    if plt is not None:
        for metric in ["novelty", "semantic_repetition", "narrative_convergence", "groupthink", "template_rigidity"]:
            if metric not in df.columns:
                continue
            pivot = df.pivot_table(index="model_family", columns="condition", values=metric, aggfunc="mean").reindex(columns=CONDITION_ORDER)
            fig, ax = plt.subplots(figsize=(8, 4))
            im = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="magma", vmin=1, vmax=5)
            ax.set_xticks(range(len(pivot.columns)), [CONDITION_LABELS.get(c, c) for c in pivot.columns], rotation=35, ha="right")
            ax.set_yticks(range(len(pivot.index)), pivot.index)
            ax.set_title(f"LLM judge: {metric.replace('_', ' ')}")
            fig.colorbar(im, ax=ax, label="Mean score (1-5)")
            fig.tight_layout()
            fig.savefig(out_dir / f"fig_judge_{metric}_heatmap.png")
            plt.close(fig)

    n_sample = sum(1 for _ in sample_path.open()) if sample_path.exists() else "unknown"
    report = f"""# Canonical HF LLM-as-a-Judge Analysis\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n## Method\n\nA stratified sample was drawn from the canonical 48-run HuggingFace dataset by model family, scale, condition, and 15-minute time bin. Each sampled post was judged with a fixed JSON schema and a context packet containing immediately previous posts from the same run plus nearest embedding neighbors when available. Condition and model family were blinded in the prompt.\n\n- Rubric version: `{JUDGE_RUBRIC_VERSION}`\n- Sample rows requested: {n_sample}\n- Completed judgments: {len(df):,}\n- Judge models present: {', '.join(sorted(df['judge_model'].unique()))}\n\n## Outputs\n\n- `judge_results.jsonl` / `judge_results.csv`: post-level judgments.\n- `judge_summary.csv`: model × scale × condition score means/std/counts.\n- `judge_collapse_label_shares.csv`: collapse-label proportions.\n- `judge_claim_behavior_shares.csv`: claim-behavior proportions.\n- `fig_judge_*_heatmap.png`: metric heatmaps.\n\n## Headline aggregate means\n\n```\n{df[SCORE_FIELDS].mean(numeric_only=True).round(3).to_string()}\n```\n"""
    (out_dir / "LLM_JUDGE_REPORT.md").write_text(report)


def cmd_index(args: argparse.Namespace) -> None:
    records = load_records(Path(args.data_root), first_minutes=args.first_minutes, include_seeds=args.include_seeds)
    write_index(records, Path(args.out_dir))
    print(f"Indexed {len(records):,} posts -> {args.out_dir}/posts_index.jsonl")


def load_or_build_records(args: argparse.Namespace) -> list[PostRecord]:
    out_dir = Path(args.out_dir)
    index_path = out_dir / "posts_index.jsonl"
    if index_path.exists() and not getattr(args, "rebuild_index", False):
        return read_index(index_path)
    records = load_records(Path(args.data_root), first_minutes=getattr(args, "first_minutes", 60), include_seeds=getattr(args, "include_seeds", False))
    write_index(records, out_dir)
    return records


def cmd_embed(args: argparse.Namespace) -> None:
    key = require_openrouter_key()
    records = load_or_build_records(args)
    if args.limit:
        records = records[:args.limit]
    conn = ensure_embedding_db(Path(args.out_dir) / "embedding_cache.sqlite")
    cached = cached_record_ids(conn, args.model)
    todo = [r for r in records if r.record_id not in cached]
    print(f"Embedding model: {args.model}")
    print(f"Records: {len(records):,}; cached: {len(cached):,}; remaining in scope: {len(todo):,}")
    print(f"Parallel OpenRouter requests: {max(1, args.parallelism)} worker(s); local store: {Path(args.out_dir) / 'embedding_cache.sqlite'}")
    batches = list(batched_records(todo, args.batch_size, args.max_batch_chars, args.max_text_chars))

    def embed_one(batch_index: int, batch: list[PostRecord]) -> tuple[int, list[PostRecord], np.ndarray]:
        texts = [r.text[:args.max_text_chars] for r in batch]
        vectors = openrouter_embed(texts, args.model, key, retries=args.retries, timeout=args.timeout)
        if len(vectors) != len(batch):
            raise RuntimeError(f"Embedding response length mismatch for batch {batch_index}: got {len(vectors)} expected {len(batch)}")
        return batch_index, batch, vectors

    if args.parallelism <= 1:
        for i, batch in enumerate(progress(batches, desc="Embedding", unit="batch")):
            _, done_batch, vectors = embed_one(i, batch)
            store_embeddings(conn, done_batch, vectors, args.model)
            if args.sleep:
                time.sleep(args.sleep)
    else:
        # Network calls are parallelized, but SQLite writes happen only in this
        # main thread as futures complete. Each completed batch is committed,
        # so Ctrl-C/provider failures still leave a resumable local cache.
        with ThreadPoolExecutor(max_workers=args.parallelism) as pool:
            futures = []
            for i, batch in enumerate(batches):
                futures.append(pool.submit(embed_one, i, batch))
                if args.sleep:
                    time.sleep(args.sleep)
            for fut in progress(as_completed(futures), total=len(futures), desc="Embedding", unit="batch"):
                _, done_batch, vectors = fut.result()
                store_embeddings(conn, done_batch, vectors, args.model)
    final_map = load_embedding_map(conn, args.model)
    print(f"Cached embeddings now: {len(final_map):,}")
    if args.export_npz:
        out_path = Path(args.out_dir) / "embeddings" / f"{slugify(args.model)}.npz"
        export_npz(load_or_build_records(args), final_map, out_path, args.model)
        print(f"Exported NPZ -> {out_path}")


def cmd_embedding_report(args: argparse.Namespace) -> None:
    records = load_or_build_records(args)
    conn = ensure_embedding_db(Path(args.out_dir) / "embedding_cache.sqlite")
    embs = load_embedding_map(conn, args.model)
    out = Path(args.out_dir) / "embedding_analysis"
    write_embedding_report(records, embs, out, args.model, use_umap=args.umap)
    print(f"Wrote embedding report -> {out}")


def cmd_sample_judge(args: argparse.Namespace) -> None:
    records = load_or_build_records(args)
    embedding_map = None
    if args.with_nearest_embeddings:
        conn = ensure_embedding_db(Path(args.out_dir) / "embedding_cache.sqlite")
        embedding_map = load_embedding_map(conn, args.embedding_model)
        if not embedding_map:
            print("No embeddings available; nearest embedding context will be omitted")
            embedding_map = None
    out_path = Path(args.out_dir) / "judge_sample.jsonl"
    rows = build_judge_sample(records, out_path, args.posts_per_cell, args.seed, embedding_map=embedding_map)
    print(f"Wrote judge sample: {len(rows):,} rows -> {out_path}")


def cmd_judge(args: argparse.Namespace) -> None:
    key = require_openrouter_key()
    sample_path = Path(args.sample)
    if not sample_path.exists():
        raise SystemExit(f"Sample file not found: {sample_path}. Run sample-judge first.")
    rows = []
    with sample_path.open() as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    if args.limit:
        rows = rows[:args.limit]
    conn = ensure_judge_db(Path(args.out_dir) / "judge_cache.sqlite")
    cached = cached_judgment_ids(conn, args.model, JUDGE_RUBRIC_VERSION)
    todo = [r for r in rows if r["record"]["record_id"] not in cached]
    print(f"Judge model: {args.model}")
    print(f"Sample rows in scope: {len(rows):,}; cached: {len(cached):,}; remaining: {len(todo):,}")
    for row in progress(todo, desc="Judging", unit="post"):
        prompt = judge_prompt(row)
        judgment = openrouter_judge(prompt, args.model, key, retries=args.retries, timeout=args.timeout)
        store_judgment(conn, row["record"]["record_id"], args.model, prompt, judgment)
        if args.sleep:
            time.sleep(args.sleep)
    print(f"Cached judgments now: {len(cached_judgment_ids(conn, args.model, JUDGE_RUBRIC_VERSION)):,}")


def cmd_aggregate_judge(args: argparse.Namespace) -> None:
    records = load_or_build_records(args)
    conn = ensure_judge_db(Path(args.out_dir) / "judge_cache.sqlite")
    judgments = load_judgments(conn, args.model if args.model else None)
    out = Path(args.out_dir) / "llm_judge_analysis"
    aggregate_judge(records, judgments, Path(args.sample), out)
    print(f"Wrote LLM judge analysis -> {out}")


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--first-minutes", type=int, default=60)
    parser.add_argument("--include-seeds", action="store_true")
    parser.add_argument("--rebuild-index", action="store_true")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("index", help="Build normalized posts index")
    add_common(p)
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("embed", help="Embed posts with OpenRouter")
    add_common(p)
    p.add_argument("--model", default=DEFAULT_EMBED_MODEL)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--max-batch-chars", type=int, default=90000)
    p.add_argument("--max-text-chars", type=int, default=6000)
    p.add_argument("--parallelism", type=int, default=4, help="Concurrent OpenRouter embedding requests; SQLite writes remain single-threaded")
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--sleep", type=float, default=0.0, help="Optional stagger between request submissions")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--export-npz", action="store_true")
    p.set_defaults(func=cmd_embed)

    p = sub.add_parser("embedding-report", help="Summarize cached embeddings")
    add_common(p)
    p.add_argument("--model", default=DEFAULT_EMBED_MODEL)
    p.add_argument("--umap", action="store_true", help="Also compute global UMAP (slower)")
    p.set_defaults(func=cmd_embedding_report)

    p = sub.add_parser("sample-judge", help="Build stratified context-aware judge sample")
    add_common(p)
    p.add_argument("--posts-per-cell", type=int, default=12, help="Per model×scale×condition cell")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--with-nearest-embeddings", action="store_true")
    p.add_argument("--embedding-model", default=DEFAULT_EMBED_MODEL)
    p.set_defaults(func=cmd_sample_judge)

    p = sub.add_parser("judge", help="Run OpenRouter LLM-as-a-judge")
    add_common(p)
    p.add_argument("--sample", default=str(DEFAULT_OUT_DIR / "judge_sample.jsonl"))
    p.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--timeout", type=int, default=90)
    p.add_argument("--sleep", type=float, default=0.1)
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("aggregate-judge", help="Aggregate cached LLM judgments")
    add_common(p)
    p.add_argument("--sample", default=str(DEFAULT_OUT_DIR / "judge_sample.jsonl"))
    p.add_argument("--model", default="", help="Optional judge model filter")
    p.set_defaults(func=cmd_aggregate_judge)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
