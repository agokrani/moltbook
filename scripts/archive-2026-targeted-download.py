#!/usr/bin/env python3
"""Targeted downloader for Ayushnangia/moltbook-archive-2026.

Downloads only the lightweight files needed for embedding/judge analysis:
posts.jsonl, comments.jsonl, agents.jsonl, metadata.json, plus top-level
README.md/inventory.json. It intentionally skips logs, DB dumps, existing plots,
and other heavy artifacts.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from pathlib import Path

from huggingface_hub import hf_hub_download, list_repo_files

REPO_ID = "Ayushnangia/moltbook-archive-2026"
NEEDED_BASENAMES = {"posts.jsonl", "comments.jsonl", "agents.jsonl", "metadata.json"}
TOP_LEVEL = {"README.md", "inventory.json", ".gitattributes"}
INCLUDE_GROUPS = {
    "base-model",
    "entropy-collapse",
    "obsession",
    "source-citation",
    "frontier/mixed-model",
}


def group_for_run(run_dir: str) -> str:
    s = run_dir.lower()
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


def discover(files: list[str]) -> tuple[list[str], dict[str, str]]:
    post_dirs = []
    groups = {}
    for f in files:
        if f.endswith("/posts.jsonl"):
            run_dir = "/".join(f.split("/")[:-1])
            group = group_for_run(run_dir)
            if group in INCLUDE_GROUPS:
                post_dirs.append(run_dir)
                groups[run_dir] = group
    return sorted(set(post_dirs)), groups


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo-id", default=REPO_ID)
    ap.add_argument("--local-dir", default="exports/huggingface/Ayushnangia/moltbook-archive-2026-targeted")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    files = list_repo_files(args.repo_id, repo_type="dataset")
    run_dirs, groups = discover(files)
    if args.limit:
        run_dirs = run_dirs[: args.limit]

    file_set = set(files)
    wanted = sorted(TOP_LEVEL & file_set)
    missing_by_run = defaultdict(list)
    for run_dir in run_dirs:
        for base in sorted(NEEDED_BASENAMES):
            f = f"{run_dir}/{base}"
            if f in file_set:
                wanted.append(f)
            else:
                missing_by_run[run_dir].append(base)

    counts = Counter(groups[r] for r in run_dirs)
    print("Targeted run dirs:", len(run_dirs))
    for k, v in counts.most_common():
        print(f"  {k}: {v}")
    print("Files to download:", len(wanted))
    print("Runs missing optional files:", len(missing_by_run))
    if missing_by_run:
        for i, (run, miss) in enumerate(missing_by_run.items()):
            if i >= 10:
                print("  ...")
                break
            print(" ", run, "missing", ",".join(miss))

    out = Path(args.local_dir)
    if args.dry_run:
        return
    out.mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(wanted, 1):
        print(f"[{i}/{len(wanted)}] {f}")
        hf_hub_download(
            args.repo_id,
            f,
            repo_type="dataset",
            local_dir=str(out),
        )
    print("DONE", out)


if __name__ == "__main__":
    main()
