"""
Generate embeddings for all agent-generated posts from run04 experiments.
Uses qwen/qwen3-embedding-8b via OpenRouter.
Saves embeddings + full metadata for downstream analysis.
"""

import json
import time
import numpy as np
import requests
from pathlib import Path

OPENROUTER_KEY = "***REDACTED***"
MODEL = "qwen/qwen3-embedding-8b"
ENDPOINT = "https://openrouter.ai/api/v1/embeddings"
BATCH_SIZE = 64  # OpenRouter batch limit
EXPORTS = Path("/Users/fortuna/Desktop/UoT/moltbook/exports")
OUTPUT = Path("/Users/fortuna/Desktop/UoT/moltbook/embeddings_run04.npz")

RUNS = [
    "ec-mag0-run04",
    "ec-mag1-run04",
    "ec-mag5-run04",
    "ec-mag25-run04",
    "ec-dom-agi-run04",
    "ec-dom-tech-run04",
]

# Condition metadata for each run
RUN_META = {
    "ec-mag0-run04":    {"experiment": "magnitude", "condition": "mag0",    "seed_count": 0,  "seed_topic": "none"},
    "ec-mag1-run04":    {"experiment": "magnitude", "condition": "mag1",    "seed_count": 1,  "seed_topic": "conspiracy"},
    "ec-mag5-run04":    {"experiment": "magnitude", "condition": "mag5",    "seed_count": 5,  "seed_topic": "conspiracy"},
    "ec-mag25-run04":   {"experiment": "magnitude", "condition": "mag25",   "seed_count": 25, "seed_topic": "conspiracy"},
    "ec-dom-agi-run04": {"experiment": "domain",    "condition": "dom-agi", "seed_count": 25, "seed_topic": "agi"},
    "ec-dom-tech-run04":{"experiment": "domain",    "condition": "dom-tech","seed_count": 25, "seed_topic": "tech"},
}


def load_agent_posts():
    """Load all agent-generated posts with full metadata."""
    posts = []
    for run in RUNS:
        run_dir = EXPORTS / run
        meta = RUN_META[run]
        for line in open(run_dir / "posts.jsonl"):
            post = json.loads(line)
            if post.get("author_name") == "civiclens_world":
                continue  # skip seed posts
            posts.append({
                # Post fields
                "post_id": post["id"],
                "title": post["title"],
                "content": post["content"],
                "submolt": post["submolt"],
                "score": post["score"],
                "comment_count": post["comment_count"],
                "created_at": post["created_at"],
                "author_name": post["author_name"],
                # Run/experiment fields
                "run": run,
                "experiment": meta["experiment"],
                "condition": meta["condition"],
                "seed_count": meta["seed_count"],
                "seed_topic": meta["seed_topic"],
            })
    return posts


def embed_batch(texts):
    """Embed a batch of texts via OpenRouter."""
    resp = requests.post(
        ENDPOINT,
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "input": texts},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    # Sort by index to preserve order
    sorted_embs = sorted(data["data"], key=lambda x: x["index"])
    return [e["embedding"] for e in sorted_embs]


def main():
    posts = load_agent_posts()
    print(f"Loaded {len(posts)} agent posts across {len(RUNS)} runs")
    for run in RUNS:
        count = sum(1 for p in posts if p["run"] == run)
        print(f"  {run}: {count} posts")

    # Build text inputs: title + content concatenated
    texts = [f"{p['title']}\n\n{p['content']}" for p in posts]

    # Embed in batches
    all_embeddings = []
    total_batches = (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        print(f"  Batch {batch_num}/{total_batches} ({len(batch)} texts)...", end=" ", flush=True)

        retries = 0
        while retries < 3:
            try:
                embs = embed_batch(batch)
                all_embeddings.extend(embs)
                print("OK")
                break
            except Exception as e:
                retries += 1
                print(f"RETRY ({e})")
                time.sleep(2 ** retries)
        else:
            print(f"FAILED after 3 retries, skipping batch")
            all_embeddings.extend([[0.0] * 4096] * len(batch))

        # Rate limit courtesy
        time.sleep(0.5)

    embeddings = np.array(all_embeddings, dtype=np.float32)
    print(f"\nEmbedding matrix: {embeddings.shape}")

    # Save everything
    # Metadata as JSON-encoded strings in object arrays
    metadata_keys = [
        "post_id", "title", "content", "submolt", "score", "comment_count",
        "created_at", "author_name", "run", "experiment", "condition",
        "seed_count", "seed_topic",
    ]
    metadata = {k: np.array([p[k] for p in posts], dtype=object) for k in metadata_keys}

    np.savez_compressed(
        OUTPUT,
        embeddings=embeddings,
        n_texts=len(posts),
        model=MODEL,
        **metadata,
    )
    print(f"Saved to {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.1f} MB)")
    print(f"Keys: embeddings + {metadata_keys}")


if __name__ == "__main__":
    main()
