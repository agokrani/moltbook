#!/usr/bin/env python3
"""Combined archive-2026 + canonical Gemini embedding/judge pipeline.

This script intentionally works from the targeted lightweight archive mirror plus
local canonical Gemini runs. It does not require full HF snapshots.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import numpy as np
import requests

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None

DEFAULT_ARCHIVE_ROOT = Path("exports/huggingface/Ayushnangia/moltbook-archive-2026-targeted")
DEFAULT_CANONICAL_GEMINI_ROOT = Path("exports/huggingface/agokrani/moltbook-entropy-collapse-canonical-48/data/gemini-flash-lite")
DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
DEFAULT_EMBED_MODEL = "qwen/qwen3-embedding-8b"
DEFAULT_JUDGE_MODEL = "google/gemini-3.1-flash-lite-preview"
EMBED_ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
SEED_PREFIXES = ("civiclens_",)

CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]


def progress(x, **kwargs):
    return tqdm(x, **kwargs) if tqdm else x


def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def infer_group(path: Path) -> str:
    s = str(path).lower()
    if "canonical-48/data/gemini-flash-lite" in s:
        return "canonical-gemini-flash-lite"
    if "base-model" in s or "/bm-" in s:
        return "base-model"
    if "obsession" in s or "obs_" in s or "/obs" in s:
        return "obsession"
    if "source-citation" in s:
        return "source-citation"
    if "frontier" in s or "mixed" in s:
        return "frontier/mixed-model"
    if "/ec-" in s or "entropy-collapse" in s:
        return "entropy-collapse"
    return "other/unknown"


def infer_condition(run_name: str) -> str:
    for cond in ["dom-agi", "dom-tech", "mag25", "mag5", "mag1", "mag0"]:
        if cond in run_name:
            return cond
    return "unknown"


def infer_n_agents(run_name: str, parent_name: str = "") -> int:
    m = re.search(r"(?:^|-)n(\d+)(?:-|$)", run_name)
    if m:
        return int(m.group(1))
    m = re.search(r"agents-(\d+)", parent_name)
    if m:
        return int(m.group(1))
    return 0


def infer_model(run_name: str, metadata: dict, group: str, run_path: str = "") -> str:
    # Model identity often lives in the parent result folder, not the leaf run name
    # (e.g. base-model-olmo3-32b-base/<bm-run-name-gemini...>). Prefer explicit
    # base-model folder markers over metadata, because those metadata files often
    # record the serving wrapper as Gemini rather than the tested base model.
    s = (run_path or run_name).lower()
    if "qwen3.5-35b-a3b-base" in s:
        return "qwen3.5-35b-a3b-base"
    if "qwen3.5-35b-a3b-instruct" in s:
        return "qwen3.5-35b-a3b-instruct"
    if "olmo3-32b-instruct" in s:
        return "olmo3-32b-instruct"
    if "olmo3-32b-think" in s:
        return "olmo3-32b-think"
    if "olmo3-32b-base" in s or "olmo3-32b-base" in str(metadata).lower():
        return "olmo3-32b-base"
    for key in ["model", "llm_model", "openrouter_model"]:
        if metadata.get(key):
            return str(metadata[key])
    if "gpt-5" in s or "gpt5" in s:
        return "gpt-5"
    if "gemini" in s:
        return "gemini-flash-lite"
    if "kimi" in s:
        return "kimi-k2.5"
    if "glm" in s:
        return "glm-5"
    if "nemotron" in s:
        return "nemotron"
    if "qwen36" in s:
        return "frontier-mixed-qwen36"
    if "frontier-mixed" in s:
        return "frontier-mixed"
    return group


@dataclass
class CombinedPost:
    record_id: str
    dataset_source: str
    group: str
    run_id: str
    run_path: str
    model_family: str
    condition: str
    n_agents: int
    scale: str
    post_id: str
    author_name: str
    author_display_name: str
    is_seed: bool
    created_at: str
    minutes_elapsed: float
    time_bin: int
    title: str
    content: str
    text: str
    score: int
    comment_count: int
    submolt: str
    post_type: str

    def to_dict(self):
        return asdict(self)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(errors="ignore") as f:
        for line in f:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def load_metadata(run_dir: Path) -> dict:
    p = run_dir / "metadata.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(errors="ignore"))
    except Exception:
        return {}


def discover_runs(archive_root: Path, canonical_gemini_root: Path) -> list[tuple[str, Path]]:
    runs: list[tuple[str, Path]] = []
    for p in sorted(archive_root.rglob("posts.jsonl")):
        runs.append(("archive-2026", p.parent))
    for p in sorted(canonical_gemini_root.glob("agents-*/*/posts.jsonl")):
        runs.append(("canonical-gemini-flash-lite", p.parent))
    return runs


def load_run(dataset_source: str, run_dir: Path, include_seeds: bool = True) -> list[CombinedPost]:
    posts = load_jsonl(run_dir / "posts.jsonl")
    if not posts:
        return []
    meta = load_metadata(run_dir)
    group = infer_group(run_dir)
    run_id = run_dir.name
    condition = infer_condition(run_id)
    n_agents = infer_n_agents(run_id, run_dir.parent.name)
    scale = f"n{n_agents}" if n_agents else "unknown"
    model = infer_model(run_id, meta, group, str(run_dir))

    agent_times = []
    for p in posts:
        author = p.get("author_name") or p.get("authorName") or ""
        if not str(author).startswith(SEED_PREFIXES):
            dt = parse_time(p.get("created_at") or p.get("createdAt") or "")
            if dt:
                agent_times.append(dt)
    all_times = [parse_time(p.get("created_at") or p.get("createdAt") or "") for p in posts]
    all_times = [t for t in all_times if t]
    start = min(agent_times or all_times) if (agent_times or all_times) else None

    records: list[CombinedPost] = []
    for p in posts:
        author = p.get("author_name") or p.get("authorName") or ""
        is_seed = str(author).startswith(SEED_PREFIXES)
        if is_seed and not include_seeds:
            continue
        created = p.get("created_at") or p.get("createdAt") or ""
        dt = parse_time(created)
        minutes = ((dt - start).total_seconds() / 60.0) if (dt and start) else 0.0
        time_bin = max(0, min(3, int(minutes // 15))) if minutes >= 0 else 0
        title = (p.get("title") or "").strip()
        content = (p.get("content") or "").strip()
        text = (title + "\n\n" + content).strip()
        post_id = p.get("id") or sha1_text(f"{run_dir}:{title}:{content}:{created}")
        record_id = sha1_text(f"{dataset_source}:{run_dir}:{post_id}:{title}:{created}")
        records.append(CombinedPost(
            record_id=record_id,
            dataset_source=dataset_source,
            group=group,
            run_id=run_id,
            run_path=str(run_dir),
            model_family=model,
            condition=condition,
            n_agents=n_agents,
            scale=scale,
            post_id=str(post_id),
            author_name=str(author),
            author_display_name=str(p.get("author_display_name") or p.get("authorDisplayName") or ""),
            is_seed=is_seed,
            created_at=str(created),
            minutes_elapsed=round(minutes, 4),
            time_bin=time_bin,
            title=title,
            content=content,
            text=text,
            score=int(p.get("score") or 0),
            comment_count=int(p.get("comment_count") or p.get("commentCount") or 0),
            submolt=str(p.get("submolt") or ""),
            post_type=str(p.get("post_type") or p.get("postType") or ""),
        ))
    return records


def build_index(args) -> list[CombinedPost]:
    records: list[CombinedPost] = []
    runs = discover_runs(Path(args.archive_root), Path(args.canonical_gemini_root))
    for source, run_dir in progress(runs, desc="Indexing runs", unit="run"):
        records.extend(load_run(source, run_dir, include_seeds=args.include_seeds))
    records.sort(key=lambda r: (r.dataset_source, r.group, r.model_family, r.run_id, r.created_at, r.post_id))
    return records


def write_index(records: list[CombinedPost], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "combined_posts_index.jsonl").open("w") as f:
        for r in records:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
    fields = [
        "record_id", "dataset_source", "group", "run_id", "model_family", "condition", "n_agents", "scale",
        "post_id", "author_name", "is_seed", "created_at", "minutes_elapsed", "time_bin", "title",
        "score", "comment_count", "submolt", "post_type", "run_path",
    ]
    with (out_dir / "combined_posts_index.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            d = r.to_dict()
            w.writerow({k: d.get(k, "") for k in fields})


def read_index(out_dir: Path) -> list[CombinedPost]:
    p = out_dir / "combined_posts_index.jsonl"
    return [CombinedPost(**json.loads(line)) for line in p.open() if line.strip()]


def load_env_key() -> str:
    if load_dotenv:
        load_dotenv(Path(".env"), override=False)
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing; put it in env or .env")
    return key


def ensure_embedding_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS embeddings (
        record_id TEXT NOT NULL,
        model TEXT NOT NULL,
        dim INTEGER NOT NULL,
        embedding BLOB NOT NULL,
        text_sha1 TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(record_id, model)
    )""")
    conn.commit()
    return conn


def cached_ids(conn: sqlite3.Connection, model: str) -> set[str]:
    return {r[0] for r in conn.execute("SELECT record_id FROM embeddings WHERE model=?", (model,))}


def load_embedding_map(conn: sqlite3.Connection, model: str) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for record_id, dim, blob in conn.execute("SELECT record_id, dim, embedding FROM embeddings WHERE model=?", (model,)):
        out[record_id] = np.frombuffer(blob, dtype=np.float32, count=dim).copy()
    return out


def export_npz(records: list[CombinedPost], conn: sqlite3.Connection, model: str, out_dir: Path) -> Path:
    emb_map = load_embedding_map(conn, model)
    usable = [r for r in records if r.record_id in emb_map]
    if not usable:
        raise SystemExit("No cached embeddings to export")
    matrix = np.vstack([emb_map[r.record_id] for r in usable]).astype(np.float32)
    emb_dir = out_dir / "embeddings"
    emb_dir.mkdir(parents=True, exist_ok=True)
    safe_model = re.sub(r"[^A-Za-z0-9_.-]+", "-", model).strip("-")
    out_path = emb_dir / f"{safe_model}.npz"
    np.savez_compressed(
        out_path,
        embeddings=matrix,
        record_ids=np.asarray([r.record_id for r in usable]),
        dataset_sources=np.asarray([r.dataset_source for r in usable]),
        groups=np.asarray([r.group for r in usable]),
        run_ids=np.asarray([r.run_id for r in usable]),
        model_families=np.asarray([r.model_family for r in usable]),
        conditions=np.asarray([r.condition for r in usable]),
        scales=np.asarray([r.scale for r in usable]),
        is_seed=np.asarray([r.is_seed for r in usable]),
        embedding_model=np.asarray([model]),
    )
    out_path.with_suffix(".json").write_text(json.dumps({
        "embedding_model": model,
        "n_rows": len(usable),
        "dim": int(matrix.shape[1]),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_index": str(out_dir / "combined_posts_index.jsonl"),
    }, indent=2))
    return out_path


def openrouter_embed(texts: Sequence[str], model: str, key: str, retries: int, timeout: int) -> np.ndarray:
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    payload = {"model": model, "input": list(texts), "encoding_format": "float"}
    last = None
    for attempt in range(retries):
        try:
            resp = requests.post(EMBED_ENDPOINT, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()["data"]
            data = sorted(data, key=lambda x: x.get("index", 0))
            return np.asarray([x["embedding"] for x in data], dtype=np.float32)
        except Exception as e:
            last = e
            sleep = min(30, 2 ** attempt)
            print(f"embedding failed attempt={attempt+1}/{retries}: {e}; sleep {sleep}s")
            time.sleep(sleep)
    raise RuntimeError(last)


def store_embeddings(conn, batch: list[CombinedPost], vecs: np.ndarray, model: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    rows = []
    for r, v in zip(batch, vecs):
        arr = np.asarray(v, dtype=np.float32)
        rows.append((r.record_id, model, int(arr.shape[0]), arr.tobytes(), sha1_text(r.text), now))
    conn.executemany("INSERT OR REPLACE INTO embeddings VALUES (?,?,?,?,?,?)", rows)
    conn.commit()


def batches(records: list[CombinedPost], batch_size: int, max_batch_chars: int, max_text_chars: int):
    cur, chars = [], 0
    for r in records:
        n = min(len(r.text), max_text_chars)
        if cur and (len(cur) >= batch_size or chars + n > max_batch_chars):
            yield cur
            cur, chars = [], 0
        cur.append(r)
        chars += n
    if cur:
        yield cur


def cmd_index(args):
    records = build_index(args)
    write_index(records, Path(args.out_dir))
    print(f"Wrote combined index: {len(records):,} rows -> {args.out_dir}")


def cmd_embed(args):
    key = load_env_key()
    out_dir = Path(args.out_dir)
    records = read_index(out_dir)
    if not args.include_seeds_for_embedding:
        records = [r for r in records if not r.is_seed]
    if args.limit:
        records = records[: args.limit]
    conn = ensure_embedding_db(out_dir / "embedding_cache.sqlite")
    done = cached_ids(conn, args.model)
    todo = [r for r in records if r.record_id not in done]
    bs = list(batches(todo, args.batch_size, args.max_batch_chars, args.max_text_chars))
    print(f"Embedding model={args.model}; records={len(records):,}; cached={len(done):,}; remaining={len(todo):,}; batches={len(bs):,}; parallelism={args.parallelism}")

    def one(i, batch):
        vecs = openrouter_embed([r.text[: args.max_text_chars] for r in batch], args.model, key, args.retries, args.timeout)
        return i, batch, vecs

    if args.parallelism <= 1:
        for i, b in enumerate(progress(bs, desc="Embedding", unit="batch")):
            _, batch, vecs = one(i, b)
            store_embeddings(conn, batch, vecs, args.model)
    else:
        with ThreadPoolExecutor(max_workers=args.parallelism) as pool:
            futs = [pool.submit(one, i, b) for i, b in enumerate(bs)]
            for fut in progress(as_completed(futs), total=len(futs), desc="Embedding", unit="batch"):
                _, batch, vecs = fut.result()
                store_embeddings(conn, batch, vecs, args.model)
    print("Cached now:", len(cached_ids(conn, args.model)))
    if args.export_npz:
        out_path = export_npz(records, conn, args.model, out_dir)
        print("Exported NPZ:", out_path)


def cmd_judge_smoke(args):
    # Minimal one-call structured smoke. Full judge/cluster labels come next iteration.
    key = load_env_key()
    records = [r for r in read_index(Path(args.out_dir)) if not r.is_seed and r.text][: args.limit]
    if not records:
        raise SystemExit("No records for judge smoke")
    r = records[0]
    prompt = f"""Score this AI-agent post for entropy-collapse behavior. Return JSON only with keys novelty, repetition, convergence, rationale.
Title: {r.title}
Content: {r.content[:1200]}
"""
    resp = requests.post(
        CHAT_ENDPOINT,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": args.model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": 200, "response_format": {"type": "json_object"}},
        timeout=90,
    )
    resp.raise_for_status()
    out = Path(args.out_dir) / "judge_smoke.json"
    out.write_text(resp.json()["choices"][0]["message"].get("content", "{}"))
    print("Wrote", out)


def parse_args():
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("index")
    p.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT))
    p.add_argument("--canonical-gemini-root", default=str(DEFAULT_CANONICAL_GEMINI_ROOT))
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--include-seeds", action="store_true", default=True)
    p.set_defaults(func=cmd_index)

    p = sub.add_parser("embed")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--model", default=DEFAULT_EMBED_MODEL)
    p.add_argument("--include-seeds-for-embedding", action="store_true", default=True)
    p.add_argument("--batch-size", type=int, default=80)
    p.add_argument("--max-batch-chars", type=int, default=90000)
    p.add_argument("--max-text-chars", type=int, default=6000)
    p.add_argument("--parallelism", type=int, default=4)
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--export-npz", action="store_true")
    p.set_defaults(func=cmd_embed)

    p = sub.add_parser("judge-smoke")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    p.add_argument("--limit", type=int, default=5)
    p.set_defaults(func=cmd_judge_smoke)
    return ap.parse_args()


def main():
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
