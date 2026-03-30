#!/usr/bin/env python3.9
"""Upload 10-agent run02 (second replication) to HuggingFace."""

import json
import os
import sys
import shutil
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

RESULTS_DIR = Path("/project/def-zhijing/anangia/moltbook/results")
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-experiments"
SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]


def clean_jsonl(inpath, drop_fields, filter_fn=None):
    lines = []
    for raw in open(inpath):
        obj = json.loads(raw.strip())
        if filter_fn and not filter_fn(obj):
            continue
        for f in drop_fields:
            obj.pop(f, None)
        lines.append(json.dumps(obj, ensure_ascii=False))
    return lines


def main():
    api = HfApi()
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    staging = Path(tempfile.mkdtemp(prefix="hf_run02_"))
    print(f"Staging in {staging}")

    for cond in CONDITIONS:
        exp_dir = RESULTS_DIR / f"ec-{cond}-run01"
        if not exp_dir.exists():
            print(f"  [SKIP] {cond} — not found")
            continue

        # Output as run02 (second replication)
        out_name = f"ec-{cond}-n10-run02"
        out_dir = staging / "data" / out_name
        out_dir.mkdir(parents=True)
        logs_dir = out_dir / "logs"
        logs_dir.mkdir()

        print(f"  Cleaning {cond} -> {out_name}...")

        # Clean posts
        posts_file = exp_dir / "posts.jsonl"
        if posts_file.exists():
            lines = clean_jsonl(posts_file, DROP_POSTS)
            (out_dir / "posts.jsonl").write_text("\n".join(lines) + "\n")
            print(f"    posts: {len(lines)}")

        # Clean comments
        comments_file = exp_dir / "comments.jsonl"
        if comments_file.exists() and comments_file.stat().st_size > 0:
            lines = clean_jsonl(comments_file, DROP_COMMENTS)
            (out_dir / "comments.jsonl").write_text("\n".join(lines) + "\n")
            print(f"    comments: {len(lines)}")

        # Clean agents
        agents_file = exp_dir / "agents.jsonl"
        if agents_file.exists():
            cleaned = []
            for raw in open(agents_file):
                obj = json.loads(raw)
                for f in DROP_AGENTS:
                    obj.pop(f, None)
                obj["type"] = "system" if obj["name"] in SYSTEM_AGENTS else "agent"
                cleaned.append(json.dumps(obj, ensure_ascii=False))
            (out_dir / "agents.jsonl").write_text("\n".join(cleaned) + "\n")

        # Update metadata — fix num_agents and rename
        meta_file = exp_dir / "metadata.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta["experiment_name"] = out_name
            meta["num_agents"] = 10
            meta["replication"] = 2
            (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2))

        # Database dumps
        for dbf in ["database-final.sql", "database-emergency.sql"]:
            src = exp_dir / dbf
            if src.exists() and src.stat().st_size > 0:
                shutil.copy2(src, out_dir / dbf)

        # Log files
        for log_file in sorted(set(exp_dir.glob("*.log"))):
            shutil.copy2(log_file, logs_dir / log_file.name)

    print(f"\nUploading run02 data to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        commit_message="Add 10-agent run02 (second replication) for all 6 conditions",
    )

    print(f"\nDone! https://huggingface.co/datasets/{REPO_ID}")
    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
