#!/usr/bin/env python3
"""LLM-frame Hill-Shannon pipeline.

Embeds the unique `dominant_frame` strings produced by the blinded LLM judge,
clusters them in the same SVD-50 -> MiniBatchKMeans-12 space used for post-text
topics, then computes per-(run, time-bin) Hill-Shannon diversity:

    effective_frames = exp(H(p))   where H is Shannon entropy of frame-cluster
                                   shares within the bin.

This is the LLM-as-judge analogue of `scripts/ayush-topic-convergence.py`, which
runs the same operator on post-text embedding clusters. The two pipelines share
embedding model (qwen/qwen3-embedding-8b) and clustering hyperparameters so
their `effective_topics` / `effective_frames` numbers are directly comparable.

Outputs (under MAIN_REPO/analysis/archive-2026-plus-canonical-gemini/
ayush_reanalysis/llm_frame_topic_convergence/):

    frame_embedding_cache.sqlite     # content-addressed: PK = (text_sha1, model)
    frame_topic_assignments.csv      # one row per (record_id, frame_cluster)
    frame_topic_keywords.csv         # cluster keyword tables for sanity checks
    frame_topic_run_timebin_metrics.csv
    frame_topic_run_deltas.csv

The script reads from the *main repo's* analysis directory because the
findings-handoff worktree does not contain the data tree. Override with
--analysis-root if you have a local copy.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sqlite3
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd
import requests
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

DEFAULT_ANALYSIS_ROOT = Path("/Users/fortuna/Desktop/UoT/moltbook/analysis/archive-2026-plus-canonical-gemini")
DEFAULT_ENV_FILE = Path("/Users/fortuna/Desktop/UoT/moltbook/.env")

EMBED_MODEL = "qwen/qwen3-embedding-8b"
EMBED_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"

TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)
STOPWORDS = {
    "the", "and", "for", "that", "this", "with", "from", "are", "was", "were", "will", "would", "could", "should",
    "have", "has", "had", "not", "but", "you", "your", "our", "their", "they", "them", "its", "it's", "into",
    "about", "what", "when", "where", "which", "while", "there", "here", "than", "then", "also", "just", "like",
    "can", "may", "might", "more", "most", "some", "any", "all", "one", "two", "new", "use", "using", "used",
    "because", "between", "through", "across", "within", "without", "over", "under", "after", "before", "these", "those",
    "i", "we", "he", "she", "it", "as", "is", "am", "be", "to", "of", "in", "on", "at", "by", "or", "an", "a",
}
FAMILY_ORDER = ["single_model_final", "base_model_as_tool", "mixed_model_roster", "obsession_prompting"]


# --------------------------------------------------------------------------
# embedding cache (content-addressed)
# --------------------------------------------------------------------------

def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


def ensure_frame_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS frame_embeddings (
        text_sha1 TEXT NOT NULL,
        model TEXT NOT NULL,
        dim INTEGER NOT NULL,
        embedding BLOB NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(text_sha1, model)
    )""")
    conn.commit()
    return conn


def cached_frame_shas(conn: sqlite3.Connection, model: str) -> set[str]:
    return {r[0] for r in conn.execute("SELECT text_sha1 FROM frame_embeddings WHERE model=?", (model,))}


def load_frame_embeddings(conn: sqlite3.Connection, model: str) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for sha, dim, blob in conn.execute("SELECT text_sha1, dim, embedding FROM frame_embeddings WHERE model=?", (model,)):
        out[str(sha)] = np.frombuffer(blob, dtype=np.float32, count=int(dim)).copy()
    return out


# --------------------------------------------------------------------------
# embedding API
# --------------------------------------------------------------------------

def load_env_key(env_file: Path) -> str:
    if load_dotenv and env_file.exists():
        load_dotenv(env_file, override=False)
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing; check .env or environment")
    return key


def openrouter_embed(texts: Sequence[str], model: str, key: str, retries: int = 6, timeout: int = 120) -> np.ndarray:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": list(texts), "encoding_format": "float"}
    last: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.post(EMBED_ENDPOINT, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda x: x.get("index", 0))
            return np.asarray([x["embedding"] for x in data], dtype=np.float32)
        except Exception as e:  # noqa: BLE001
            last = e
            sleep = min(30, 2 ** attempt)
            print(f"embed attempt {attempt + 1}/{retries} failed: {e}; sleep {sleep}s", flush=True)
            time.sleep(sleep)
    raise RuntimeError(f"openrouter embed failed after {retries} retries: {last}")


def store_frame_batch(conn: sqlite3.Connection, batch: list[tuple[str, str]], vecs: np.ndarray, model: str) -> None:
    """batch is list of (text_sha1, raw_text); vecs aligned by row."""
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for (sha, text), v in zip(batch, vecs):
        v = np.asarray(v, dtype=np.float32)
        rows.append((sha, model, int(v.size), v.tobytes(), text, now))
    conn.executemany(
        "INSERT OR REPLACE INTO frame_embeddings VALUES (?,?,?,?,?,?)",
        rows,
    )
    conn.commit()


# --------------------------------------------------------------------------
# Hill-Shannon metrics
# --------------------------------------------------------------------------

def frame_distribution_metrics(cluster_ids: Sequence[int], n_clusters: int) -> dict[str, Any]:
    n = len(cluster_ids)
    if n == 0:
        row = {
            "n_posts": 0,
            "dominant_frame_cluster": "",
            "dominant_share": math.nan,
            "frame_entropy": math.nan,
            "frame_entropy_norm": math.nan,
            "effective_frames": math.nan,
            "frame_hhi": math.nan,
        }
        for c in range(n_clusters):
            row[f"frame_{c + 1:02d}_share"] = math.nan
        return row
    counts = Counter(int(c) for c in cluster_ids)
    probs = np.asarray([counts.get(c, 0) / n for c in range(n_clusters)], dtype=float)
    nz = probs[probs > 0]
    entropy = float(-np.sum(nz * np.log(nz))) if len(nz) else 0.0
    dominant = int(np.argmax(probs))
    row = {
        "n_posts": n,
        "dominant_frame_cluster": f"F{dominant + 1:02d}",
        "dominant_share": float(np.max(probs)),
        "frame_entropy": entropy,
        "frame_entropy_norm": float(entropy / math.log(n_clusters)) if n_clusters > 1 else math.nan,
        "effective_frames": float(math.exp(entropy)),
        "frame_hhi": float(np.sum(probs * probs)),
    }
    for c, prob in enumerate(probs):
        row[f"frame_{c + 1:02d}_share"] = float(prob)
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


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")
            if len(t) >= 3 and t.lower() not in STOPWORDS and not t.isdigit()]


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


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--analysis-root", type=Path, default=DEFAULT_ANALYSIS_ROOT,
                    help="archive-2026-plus-canonical-gemini directory in main repo")
    ap.add_argument("--env-file", type=Path, default=DEFAULT_ENV_FILE,
                    help=".env file containing OPENROUTER_API_KEY")
    ap.add_argument("--model", default=EMBED_MODEL)
    ap.add_argument("--n-clusters", type=int, default=12)
    ap.add_argument("--svd-components", type=int, default=50)
    ap.add_argument("--batch-size", type=int, default=64,
                    help="frames per OpenRouter embed request")
    ap.add_argument("--max-batches", type=int, default=0,
                    help="cap embedding batches per run (0 = no cap, debugging knob)")
    ap.add_argument("--skip-embedding", action="store_true",
                    help="assume cache is full; skip API calls and go straight to clustering")
    args = ap.parse_args()

    root: Path = args.analysis_root
    if not root.exists():
        raise SystemExit(f"analysis root does not exist: {root}")
    judge_csv = root / "ayush_reanalysis" / "llm_judge" / "blind_judge_results_with_metadata.csv"
    if not judge_csv.exists():
        raise SystemExit(f"missing: {judge_csv}")

    out = root / "ayush_reanalysis" / "llm_frame_topic_convergence"
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / "frame_embedding_cache.sqlite"

    print(f"loading judge results from {judge_csv}", flush=True)
    cols = ["record_id", "run_uid", "minutes_elapsed", "normalized_time",
            "internal_family_label", "display_family_label", "model_family",
            "model_display", "roster_name", "condition", "scale", "n_agents",
            "run_id", "source_path", "author_name", "dominant_frame"]
    df = pd.read_csv(judge_csv, usecols=cols, low_memory=False)
    before = len(df)
    df = df.dropna(subset=["dominant_frame"]).copy()
    df["dominant_frame"] = df["dominant_frame"].astype(str).str.strip()
    df = df[df["dominant_frame"].str.len() > 0].copy()
    df["text_sha1"] = df["dominant_frame"].map(sha1_text)
    print(f"  rows: {before} -> {len(df)} after frame filter; "
          f"unique frames: {df['text_sha1'].nunique()}", flush=True)

    # ---- ensure embedding cache is complete --------------------------------
    conn = ensure_frame_db(cache_path)
    have = cached_frame_shas(conn, args.model)
    needed_pairs: dict[str, str] = {}
    for sha, text in df[["text_sha1", "dominant_frame"]].drop_duplicates().itertuples(index=False):
        if sha not in have:
            needed_pairs[sha] = text
    print(f"  cached frame embeddings: {len(have)}; missing: {len(needed_pairs)}", flush=True)

    if needed_pairs and not args.skip_embedding:
        key = load_env_key(args.env_file)
        items = list(needed_pairs.items())
        bs = max(1, args.batch_size)
        n_batches = (len(items) + bs - 1) // bs
        if args.max_batches > 0:
            n_batches = min(n_batches, args.max_batches)
        iterator = range(n_batches)
        if tqdm:
            iterator = tqdm(iterator, desc="embed frames", unit="batch")
        for bi in iterator:
            batch = items[bi * bs:(bi + 1) * bs]
            if not batch:
                break
            texts = [t for _, t in batch]
            vecs = openrouter_embed(texts, args.model, key)
            store_frame_batch(conn, batch, vecs, args.model)
        # refresh cache view
        have = cached_frame_shas(conn, args.model)
        print(f"  cached frame embeddings after run: {len(have)}", flush=True)

    # ---- load embeddings into memory and verify coverage -------------------
    emb_map = load_frame_embeddings(conn, args.model)
    conn.close()
    missing = df[~df["text_sha1"].isin(emb_map.keys())]["text_sha1"].nunique()
    if missing:
        if args.skip_embedding:
            print(f"WARN: {missing} unique frames still missing; "
                  f"continuing with available subset (--skip-embedding)", flush=True)
            df = df[df["text_sha1"].isin(emb_map.keys())].copy()
        else:
            raise SystemExit(f"{missing} unique frames missing from cache after embed run; "
                             f"rerun without --skip-embedding")

    # ---- cluster (mirror ayush-topic-convergence semantics) ----------------
    unique_shas = sorted(emb_map.keys())
    sha_to_text = dict(df[["text_sha1", "dominant_frame"]].drop_duplicates().itertuples(index=False))
    mat = np.vstack([emb_map[s] for s in unique_shas]).astype(np.float32)
    print(f"  clustering matrix: {mat.shape}", flush=True)
    mat = normalize(mat, norm="l2", copy=False)
    n_comp = min(args.svd_components, mat.shape[1] - 1, mat.shape[0] - 1)
    z = TruncatedSVD(n_components=n_comp, random_state=42).fit_transform(mat).astype(np.float32)
    z = normalize(z, norm="l2", copy=False)
    km = MiniBatchKMeans(n_clusters=args.n_clusters, random_state=42, batch_size=2048, n_init=10)
    raw_labels = km.fit_predict(z)

    counts = Counter(int(x) for x in raw_labels)
    remap = {old: new for new, (old, _) in enumerate(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))}
    labels = np.asarray([remap[int(x)] for x in raw_labels], dtype=int)
    sha_to_cluster = dict(zip(unique_shas, labels))
    df["frame_cluster"] = df["text_sha1"].map(sha_to_cluster).astype(int)

    # ---- cluster keywords for sanity --------------------------------------
    cluster_tokens = {i: Counter() for i in range(args.n_clusters)}
    cluster_unique = Counter()
    for sha, cid in sha_to_cluster.items():
        cluster_unique[int(cid)] += 1
        cluster_tokens[int(cid)].update(tokenize(sha_to_text.get(sha, "")))
    keyword_rows = []
    for c in range(args.n_clusters):
        terms = [t for t, _ in cluster_tokens[c].most_common(10)]
        keyword_rows.append({
            "frame_cluster": f"F{c + 1:02d}",
            "n_unique_frames": int(cluster_unique[c]),
            "n_total_posts": int((df["frame_cluster"] == c).sum()),
            "keywords": ", ".join(terms),
        })
    write_csv(out / "frame_topic_keywords.csv", keyword_rows)

    # ---- per-(run, scheme, bin) Hill-Shannon ------------------------------
    meta_cols = ["internal_family_label", "display_family_label", "model_family",
                 "model_display", "roster_name", "condition", "scale", "n_agents",
                 "run_id", "source_path"]
    time_rows: list[dict[str, Any]] = []
    delta_rows: list[dict[str, Any]] = []
    df_sorted = df.sort_values(["run_uid", "minutes_elapsed", "record_id"]).reset_index(drop=True)

    for run_uid, sub in df_sorted.groupby("run_uid", dropna=False):
        first = sub.iloc[0]
        schemes = (["normalized_quartile"]
                   if first.internal_family_label == "obsession_prompting"
                   else ["fixed_15m", "normalized_quartile"])
        for scheme in schemes:
            b_rows = []
            for bi, label, b in assign_bins(sub, scheme):
                row = {"run_uid": run_uid, "scheme": scheme, "bin_idx": bi, "bin_label": label}
                row.update(frame_distribution_metrics(b["frame_cluster"].tolist(), args.n_clusters))
                row["n_agents_observed"] = int(b["author_name"].nunique()) if len(b) else 0
                for col in meta_cols:
                    row[col] = first[col]
                time_rows.append(row)
                b_rows.append(row)
            d = {"run_uid": run_uid, "scheme": scheme,
                 "first_bin": b_rows[0]["bin_label"], "final_bin": b_rows[-1]["bin_label"]}
            for metric in ["dominant_share", "frame_entropy_norm", "effective_frames", "frame_hhi"]:
                a, bv = b_rows[0][metric], b_rows[-1][metric]
                d[f"delta_{metric}"] = (bv - a) if np.isfinite(a) and np.isfinite(bv) else math.nan
            d["first_n_posts"] = b_rows[0]["n_posts"]
            d["final_n_posts"] = b_rows[-1]["n_posts"]
            for col in meta_cols:
                d[col] = first[col]
            delta_rows.append(d)

    write_csv(out / "frame_topic_run_timebin_metrics.csv", time_rows)
    write_csv(out / "frame_topic_run_deltas.csv", delta_rows)

    # ---- per-record assignments ------------------------------------------
    assignment_rows = []
    for row in df_sorted.itertuples(index=False):
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
            "frame_cluster": f"F{int(row.frame_cluster) + 1:02d}",
            "frame_cluster_id": int(row.frame_cluster),
            "dominant_frame": row.dominant_frame,
        })
    write_csv(out / "frame_topic_assignments.csv", assignment_rows)

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": args.model,
        "n_clusters": args.n_clusters,
        "svd_components": int(n_comp),
        "n_judged_rows": int(len(df)),
        "n_unique_frames": int(len(unique_shas)),
        "outputs": sorted(p.name for p in out.iterdir() if p.is_file()),
    }
    (out / "frame_topic_convergence_summary.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote frame topic convergence outputs to {out}", flush=True)


if __name__ == "__main__":
    main()
