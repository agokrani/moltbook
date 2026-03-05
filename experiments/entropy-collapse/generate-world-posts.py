#!/usr/bin/env python3
"""
Generate world-posts files for entropy-collapse experiments.

Reads from three sources:
  - experiments/conspiracy/world-posts-conspiracy-only.jsonl  (25 conspiracy posts)
  - dataset/AGI_hype/dataset.jsonl (from analyze-datasets branch via git)
  - dataset/Tech_news/dataset.jsonl (from analyze-datasets branch via git)

Produces 7 world-posts files:
  - world-posts-empty.jsonl       (0 posts — true control)
  - world-posts-mag1.jsonl        (1 conspiracy post)
  - world-posts-mag5.jsonl        (5 conspiracy posts)
  - world-posts-agi.jsonl         (25 AGI hype posts)
  - world-posts-tech.jsonl        (25 tech news posts)
  - world-posts-het-dual.jsonl    (12 conspiracy + 13 AGI, interleaved)
  - world-posts-het-multi.jsonl   (8 conspiracy + 8 AGI + 9 tech, interleaved)

Usage:
  python3 experiments/entropy-collapse/generate-world-posts.py
"""

import json
import subprocess
import sys
from pathlib import Path
from itertools import zip_longest

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = Path(__file__).resolve().parent
GIT_BRANCH = "origin/analyze-datasets-and-experiments"


def load_conspiracy_posts():
    """Load conspiracy posts from local file."""
    path = PROJECT_DIR / "experiments" / "conspiracy" / "world-posts-conspiracy-only.jsonl"
    posts = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                posts.append(json.loads(line))
    print(f"  Loaded {len(posts)} conspiracy posts from {path.name}")
    return posts


def load_from_git(branch_path, label):
    """Load dataset from git branch and transform to world-posts format."""
    result = subprocess.run(
        ["git", "show", f"{GIT_BRANCH}:{branch_path}"],
        capture_output=True, text=True, cwd=PROJECT_DIR
    )
    if result.returncode != 0:
        print(f"  [ERROR] Failed to read {branch_path} from {GIT_BRANCH}")
        print(f"  stderr: {result.stderr.strip()}")
        sys.exit(1)

    posts = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        raw = json.loads(line)
        posts.append({
            "title": raw["post_title"],
            "content": raw["post_content"],
            "submolt": "general"
        })
    print(f"  Loaded {len(posts)} {label} posts from git:{branch_path}")
    return posts


def interleave(*lists):
    """Round-robin interleave multiple lists."""
    result = []
    for items in zip_longest(*lists):
        for item in items:
            if item is not None:
                result.append(item)
    return result


def write_jsonl(filename, posts):
    """Write posts to a JSONL file."""
    path = OUTPUT_DIR / filename
    with open(path, "w") as f:
        for post in posts:
            f.write(json.dumps(post) + "\n")
    print(f"  Wrote {len(posts)} posts → {filename}")


def main():
    print("Loading source datasets...")
    conspiracy = load_conspiracy_posts()
    agi = load_from_git("dataset/AGI_hype/dataset.jsonl", "AGI")
    tech = load_from_git("dataset/Tech_news/dataset.jsonl", "Tech")

    assert len(conspiracy) == 25, f"Expected 25 conspiracy posts, got {len(conspiracy)}"
    assert len(agi) == 25, f"Expected 25 AGI posts, got {len(agi)}"
    assert len(tech) == 25, f"Expected 25 tech posts, got {len(tech)}"

    print("\nGenerating world-posts files...")

    # E-MAG-0: True control (empty feed)
    write_jsonl("world-posts-empty.jsonl", [])

    # E-MAG-1: Minimum viable attractor (1 conspiracy post)
    write_jsonl("world-posts-mag1.jsonl", conspiracy[:1])

    # E-MAG-5: Light dose (5 conspiracy posts)
    write_jsonl("world-posts-mag5.jsonl", conspiracy[:5])

    # E-DOM-AGI: Domain independence — AGI hype
    write_jsonl("world-posts-agi.jsonl", agi)

    # E-DOM-TECH: Domain independence — tech news
    write_jsonl("world-posts-tech.jsonl", tech)

    # E-HET-DUAL: Mixed feed — 12 conspiracy + 13 AGI (interleaved)
    write_jsonl("world-posts-het-dual.jsonl", interleave(conspiracy[:12], agi[:13]))

    # E-HET-MULTI: Mixed feed — 8 conspiracy + 8 AGI + 9 tech (interleaved)
    write_jsonl("world-posts-het-multi.jsonl", interleave(conspiracy[:8], agi[:8], tech[:9]))

    print("\nDone. Verify with:")
    print(f"  wc -l {OUTPUT_DIR}/world-posts-*.jsonl")


if __name__ == "__main__":
    main()
