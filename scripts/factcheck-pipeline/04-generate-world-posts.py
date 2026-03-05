#!/usr/bin/env python3
"""Stage 4: Generate world-posts JSONL files for threshold dose-response experiment.

Mirrors experiments/conspiracy/generate-threshold-posts.py but reads from
factcheck_reddit.jsonl instead. Produces N files with varying factual/conspiracy
ratios, plus a topic-mapping.json.

Output (default 6 doses, 25 posts each):
  world-posts-f0.jsonl   ->  0 factual + 25 conspiracy
  world-posts-f1.jsonl   ->  1 factual + 24 conspiracy
  ...
  world-posts-f5.jsonl   ->  5 factual + 20 conspiracy

  topic-mapping.json     ->  {title: {topic, type}}

Usage:
    python3 scripts/factcheck-pipeline/04-generate-world-posts.py
    python3 scripts/factcheck-pipeline/04-generate-world-posts.py --total-posts 50 --doses 0,1,2,3,4,5,10,15
"""

import argparse
import json
import random
import sys
from pathlib import Path

SEED = 42

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "experiments" / "factcheck" / "factcheck_reddit.jsonl"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "experiments" / "factcheck"
DEFAULT_TOTAL_POSTS = 25
DEFAULT_DOSES = "0,1,2,3,4,5"


def load_source(path):
    entries = []
    with open(path) as f:
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
    parser = argparse.ArgumentParser(
        description="Generate world-posts JSONL files for dose-response experiments"
    )
    parser.add_argument(
        "--input", default=str(DEFAULT_INPUT),
        help=f"Input JSONL path (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output-dir", default=str(DEFAULT_OUTPUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})"
    )
    parser.add_argument(
        "--total-posts", type=int, default=DEFAULT_TOTAL_POSTS,
        help=f"Total posts per world-posts file (default: {DEFAULT_TOTAL_POSTS})"
    )
    parser.add_argument(
        "--doses", default=DEFAULT_DOSES,
        help=f"Comma-separated factual dose levels (default: {DEFAULT_DOSES})"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    total_posts = args.total_posts
    doses = [int(d.strip()) for d in args.doses.split(",")]

    if not input_path.exists():
        print(f"ERROR: Source file not found: {input_path}")
        print("Run 03-generate-posts.py first.")
        sys.exit(1)

    entries = load_source(input_path)
    print(f"Loaded {len(entries)} topics from {input_path.name}")
    print(f"Total posts per file: {total_posts}")
    print(f"Dose levels: {doses}")

    # Build factual and conspiracy post lists
    factual_posts = []
    conspiracy_posts = []

    for entry in entries:
        factual_posts.append(
            make_post(entry["factual_post_title"], entry["factual_post_content"])
        )
        conspiracy_posts.append(
            make_post(entry["conspiracy_post_title"], entry["conspiracy_post_content"])
        )

    print(f"  {len(factual_posts)} factual, {len(conspiracy_posts)} conspiracy available")

    # Build topic mapping (compatible with analyze_threshold.py)
    topic_mapping = {}
    for entry in entries:
        topic = entry.get("question", entry.get("claim_text", "Unknown"))

        topic_mapping[entry["factual_post_title"]] = {
            "topic": topic,
            "type": "factual",
        }
        topic_mapping[entry["conspiracy_post_title"]] = {
            "topic": topic,
            "type": "conspiracy",
        }

    output_dir.mkdir(parents=True, exist_ok=True)
    mapping_path = output_dir / "topic-mapping.json"
    with open(mapping_path, "w") as f:
        json.dump(topic_mapping, f, indent=2)
    print(f"  topic-mapping.json: {len(topic_mapping)} entries")

    # Generate files for each dose level
    n_available_conspiracy = len(conspiracy_posts)
    n_available_factual = len(factual_posts)

    for n_factual in doses:
        random.seed(SEED)  # Reset seed for each file for reproducibility
        n_conspiracy = total_posts - n_factual

        if n_conspiracy < 0:
            print(f"  Skipping f{n_factual}: dose exceeds total_posts ({total_posts})")
            continue

        # Sample with replacement if pool is too small
        posts = []
        if n_factual > 0:
            if n_factual <= n_available_factual:
                posts.extend(random.sample(factual_posts, n_factual))
            else:
                posts.extend(random.choices(factual_posts, k=n_factual))
                print(f"  NOTE: f{n_factual} used sampling with replacement for factual posts")

        if n_conspiracy > 0:
            if n_conspiracy <= n_available_conspiracy:
                posts.extend(random.sample(conspiracy_posts, n_conspiracy))
            else:
                posts.extend(random.choices(conspiracy_posts, k=n_conspiracy))
                print(f"  NOTE: f{n_factual} used sampling with replacement for conspiracy posts")

        random.shuffle(posts)

        filename = f"world-posts-f{n_factual}.jsonl"
        write_jsonl(output_dir / filename, posts)

    print(f"\nDone! Generated {len(doses)} threshold world-post files in {output_dir}")


if __name__ == "__main__":
    main()
