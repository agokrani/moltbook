#!/usr/bin/env python3
"""Generate entropy-collapse post embeddings for n10/n20/n30.

This replaces the stale root-level `embeddings_n*.npz` files and also writes
the copies expected by `experiments/entropy-collapse/embedding_analysis.py`.

Outputs for each scale:
  - embeddings_<scale>.npz
  - experiments/entropy-collapse/data/embeddings/embeddings_<scale>.npz
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import requests

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR / "analysis"))

from load_entropy_data import SCALE_CONFIG, SEED_AUTHORS, parse_condition

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
MODEL = "qwen/qwen3-embedding-8b"
ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
BATCH_SIZE = 64
VALID_SCALES = ["n10", "n20", "n30"]

CONDITION_META = {
    "mag0": {"experiment": "magnitude", "seed_count": 0, "seed_topic": "none"},
    "mag1": {"experiment": "magnitude", "seed_count": 1, "seed_topic": "conspiracy"},
    "mag5": {"experiment": "magnitude", "seed_count": 5, "seed_topic": "conspiracy"},
    "mag25": {"experiment": "magnitude", "seed_count": 25, "seed_topic": "conspiracy"},
    "dom-agi": {"experiment": "domain", "seed_count": 25, "seed_topic": "agi"},
    "dom-tech": {"experiment": "domain", "seed_count": 25, "seed_topic": "tech"},
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate embeddings for entropy-collapse runs.")
    parser.add_argument(
        "--scale",
        choices=VALID_SCALES + ["all"],
        default="all",
        help="Scale to embed (default: all).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Embedding batch size (default: {BATCH_SIZE}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Load and summarize posts without calling the embedding API.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=None,
        help="Override data directory (all scales read from this single dir).",
    )
    parser.add_argument(
        "--out-prefix",
        type=str,
        default="embeddings",
        help="Output file prefix (default: 'embeddings' → embeddings_n10.npz).",
    )
    return parser.parse_args()


def output_paths(scale: str, prefix: str = "embeddings") -> tuple[Path, Path]:
    root_npz = REPO_ROOT / f"{prefix}_{scale}.npz"
    analysis_npz = REPO_ROOT / "experiments" / "entropy-collapse" / "data" / "embeddings" / f"{prefix}_{scale}.npz"
    return root_npz, analysis_npz


def load_agent_posts(scale: str, data_dir_override: str | None = None) -> list[dict]:
    data_dir = Path(data_dir_override) if data_dir_override else REPO_ROOT / SCALE_CONFIG[scale]
    if not data_dir.exists():
        raise FileNotFoundError(f"Missing data directory for {scale}: {data_dir}")

    posts = []
    for run_dir in sorted(data_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        posts_path = run_dir / "posts.jsonl"
        if not posts_path.exists():
            continue

        condition = parse_condition(run_dir.name)
        meta = CONDITION_META.get(condition)
        if meta is None:
            continue

        with posts_path.open() as handle:
            for line in handle:
                post = json.loads(line)
                if post.get("author_name") in SEED_AUTHORS:
                    continue
                posts.append(
                    {
                        "post_id": str(post.get("id", "")),
                        "title": str(post.get("title") or ""),
                        "content": str(post.get("content") or ""),
                        "submolt": str(post.get("submolt") or ""),
                        "score": int(post.get("score") or 0),
                        "comment_count": int(post.get("comment_count") or 0),
                        "created_at": str(post.get("created_at") or ""),
                        "author_name": str(post.get("author_name") or ""),
                        "run": run_dir.name,
                        "experiment": meta["experiment"],
                        "condition": condition,
                        "seed_count": int(meta["seed_count"]),
                        "seed_topic": meta["seed_topic"],
                    }
                )

    posts.sort(key=lambda post: (post["condition"], post["run"], post["created_at"], post["post_id"]))
    return posts


def embed_batch(texts: list[str]) -> list[list[float]]:
    response = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "input": texts},
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    embeddings = sorted(payload["data"], key=lambda item: item["index"])
    return [item["embedding"] for item in embeddings]


def save_npz(path: Path, posts: list[dict], embeddings: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp.npz")
    metadata_keys = [
        "post_id",
        "title",
        "content",
        "submolt",
        "score",
        "comment_count",
        "created_at",
        "author_name",
        "run",
        "experiment",
        "condition",
        "seed_count",
        "seed_topic",
    ]
    metadata = {key: np.array([post[key] for post in posts], dtype=object) for key in metadata_keys}
    with tmp_path.open("wb") as handle:
        np.savez_compressed(
            handle,
            embeddings=embeddings,
            n_texts=np.array(len(posts)),
            model=np.array(MODEL),
            **metadata,
        )
    tmp_path.replace(path)


def print_scale_summary(scale: str, posts: list[dict]) -> None:
    print(f"\n{scale}: loaded {len(posts)} agent posts")
    counts: dict[str, int] = {}
    for post in posts:
        counts[post["condition"]] = counts.get(post["condition"], 0) + 1
    for condition in ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]:
        if condition in counts:
            print(f"  {condition}: {counts[condition]} posts")


def embed_scale(scale: str, batch_size: int, dry_run: bool, data_dir: str | None = None, out_prefix: str = "embeddings") -> None:
    posts = load_agent_posts(scale, data_dir_override=data_dir)
    print_scale_summary(scale, posts)

    if dry_run:
        root_npz, analysis_npz = output_paths(scale, prefix=out_prefix)
        print(f"  dry-run only; would write:\n    {root_npz}\n    {analysis_npz}")
        return

    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    texts = [f"{post['title']}\n\n{post['content']}".strip() for post in posts]
    all_embeddings: list[list[float]] = []
    total_batches = (len(texts) + batch_size - 1) // batch_size
    print(f"  embedding {len(texts)} texts in {total_batches} batches...")

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        batch_num = start // batch_size + 1
        print(f"    batch {batch_num}/{total_batches} ({len(batch)} texts)...", end=" ", flush=True)

        retries = 0
        while retries < 3:
            try:
                batch_embeddings = embed_batch(batch)
                all_embeddings.extend(batch_embeddings)
                print("OK")
                break
            except Exception as exc:
                retries += 1
                print(f"RETRY ({exc})")
                time.sleep(2 ** retries)
        else:
            raise RuntimeError(f"Failed embedding batch {batch_num}/{total_batches} for {scale}")

        time.sleep(0.5)

    embeddings = np.asarray(all_embeddings, dtype=np.float32)
    if embeddings.shape[0] != len(posts):
        raise RuntimeError(f"Embedding count mismatch for {scale}: {embeddings.shape[0]} vs {len(posts)}")

    root_npz, analysis_npz = output_paths(scale, prefix=out_prefix)
    save_npz(root_npz, posts, embeddings)
    save_npz(analysis_npz, posts, embeddings)
    print(f"  wrote {root_npz}")
    print(f"  wrote {analysis_npz}")


def main() -> None:
    args = parse_args()
    scales = VALID_SCALES if args.scale == "all" else [args.scale]
    started_at = time.time()
    print(f"Generating embeddings with model {MODEL}")
    print(f"Scales: {', '.join(scales)}")
    for scale in scales:
        embed_scale(scale, batch_size=args.batch_size, dry_run=args.dry_run, data_dir=args.data_dir, out_prefix=args.out_prefix)
    print(f"\nDone in {time.time() - started_at:.1f}s")


if __name__ == "__main__":
    main()
