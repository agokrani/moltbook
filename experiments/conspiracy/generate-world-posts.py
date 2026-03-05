#!/usr/bin/env python3
"""Generate world-posts JSONL files for conspiracy vs factual experiments.

Reads conspiracy_reddit.jsonl and produces:
  - world-posts-all.jsonl          (50 posts: 25 factual + 25 conspiracy, shuffled)
  - world-posts-conspiracy-only.jsonl (25 conspiracy posts, shuffled)
  - world-posts-80fact.jsonl       (20 factual + 5 conspiracy, shuffled)
  - world-posts-50-50.jsonl        (13 factual + 12 conspiracy, shuffled)
  - world-posts-80cons.jsonl       (5 factual + 20 conspiracy, shuffled)
  - topic-mapping.json             (title -> {topic, type} mapping)
"""

import json
import random
import sys
from pathlib import Path

SEED = 42
random.seed(SEED)

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
    topic_mapping = {}

    for entry in entries:
        topic = entry["question"]

        fp = make_post(entry["factual_post_title"], entry["factual_post_content"])
        cp = make_post(entry["conspiracy_post_title"], entry["conspiracy_post_content"])

        factual_posts.append(fp)
        conspiracy_posts.append(cp)

        topic_mapping[entry["factual_post_title"]] = {"topic": topic, "type": "factual"}
        topic_mapping[entry["conspiracy_post_title"]] = {"topic": topic, "type": "conspiracy"}

    print(f"  {len(factual_posts)} factual, {len(conspiracy_posts)} conspiracy")

    # 1. world-posts-all.jsonl — all 50 posts, shuffled
    all_posts = factual_posts + conspiracy_posts
    random.shuffle(all_posts)
    write_jsonl(SCRIPT_DIR / "world-posts-all.jsonl", all_posts)

    # 2. world-posts-conspiracy-only.jsonl — 25 conspiracy posts, shuffled
    cons_only = list(conspiracy_posts)
    random.shuffle(cons_only)
    write_jsonl(SCRIPT_DIR / "world-posts-conspiracy-only.jsonl", cons_only)

    # 3. world-posts-80fact.jsonl — 20 factual + 5 conspiracy, shuffled
    f80 = random.sample(factual_posts, 20) + random.sample(conspiracy_posts, 5)
    random.shuffle(f80)
    write_jsonl(SCRIPT_DIR / "world-posts-80fact.jsonl", f80)

    # 4. world-posts-50-50.jsonl — 13 factual + 12 conspiracy, shuffled
    f5050 = random.sample(factual_posts, 13) + random.sample(conspiracy_posts, 12)
    random.shuffle(f5050)
    write_jsonl(SCRIPT_DIR / "world-posts-50-50.jsonl", f5050)

    # 5. world-posts-80cons.jsonl — 5 factual + 20 conspiracy, shuffled
    f80c = random.sample(factual_posts, 5) + random.sample(conspiracy_posts, 20)
    random.shuffle(f80c)
    write_jsonl(SCRIPT_DIR / "world-posts-80cons.jsonl", f80c)

    # 6. topic-mapping.json
    mapping_path = SCRIPT_DIR / "topic-mapping.json"
    with open(mapping_path, "w") as f:
        json.dump(topic_mapping, f, indent=2)
    print(f"  topic-mapping.json: {len(topic_mapping)} entries")

    print("\nDone!")


if __name__ == "__main__":
    main()
