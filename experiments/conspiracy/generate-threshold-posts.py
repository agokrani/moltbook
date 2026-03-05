#!/usr/bin/env python3
"""Generate world-posts JSONL files for threshold dose-response experiment.

Reads conspiracy_reddit.jsonl and produces 6 files with varying factual/conspiracy
ratios, all totaling 25 posts:

  world-posts-f0.jsonl   →  0 factual + 25 conspiracy
  world-posts-f1.jsonl   →  1 factual + 24 conspiracy
  world-posts-f2.jsonl   →  2 factual + 23 conspiracy
  world-posts-f3.jsonl   →  3 factual + 22 conspiracy
  world-posts-f4.jsonl   →  4 factual + 21 conspiracy
  world-posts-f5.jsonl   →  5 factual + 20 conspiracy

Each file is shuffled with seed=42. Reuses existing topic-mapping.json.

Usage:
    python3 experiments/conspiracy/generate-threshold-posts.py
"""

import json
import random
from pathlib import Path

SEED = 42
TOTAL_POSTS = 25

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SOURCE_FILE = PROJECT_ROOT / "conspiracy_reddit.jsonl"


def load_source():
    entries = []
    with open(SOURCE_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def make_post(title, content, submolt="general"):
    return {"title": title, "content": content, "submolt": submolt}


def write_jsonl(path, posts):
    with open(path, "w") as f:
        for post in posts:
            f.write(json.dumps(post) + "\n")
    print(f"  {path.name}: {len(posts)} posts")


def main():
    entries = load_source()
    print(f"Loaded {len(entries)} topics from {SOURCE_FILE.name}")

    # Build factual and conspiracy post lists
    factual_posts = []
    conspiracy_posts = []

    for entry in entries:
        factual_posts.append(make_post(entry["factual_post_title"], entry["factual_post_content"]))
        conspiracy_posts.append(make_post(entry["conspiracy_post_title"], entry["conspiracy_post_content"]))

    print(f"  {len(factual_posts)} factual, {len(conspiracy_posts)} conspiracy available")

    # Generate 6 files: f0 through f5
    for n_factual in range(6):
        random.seed(SEED)  # Reset seed for each file for reproducibility
        n_conspiracy = TOTAL_POSTS - n_factual

        posts = []
        if n_factual > 0:
            posts.extend(random.sample(factual_posts, n_factual))
        posts.extend(random.sample(conspiracy_posts, n_conspiracy))
        random.shuffle(posts)

        filename = f"world-posts-f{n_factual}.jsonl"
        write_jsonl(SCRIPT_DIR / filename, posts)

    print("\nDone! Generated 6 threshold world-post files.")


if __name__ == "__main__":
    main()
