#!/usr/bin/env python3
"""Upload the 8 resumed entropy-collapse runs to a new public HF dataset.

Source: local exports/<run>-resumed/ dirs, produced by scripts/resume-entropy-run.py
Target: Ayushnangia/moltbook-entropy-collapse-resumes (public)

Each resumed export pairs with an original run listed in incomplete_runs.md
whose final 15-min bin was empty (provider-side dropout for Gemini, batch
termination for the GPT-5 pair). The resume restored the original
database-final.sql, rotated agent API keys, and ran the full agent population
for ~34 additional minutes.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

from huggingface_hub import HfApi, create_repo  # noqa: E402

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-resumes"
REPO_PRIVATE = False
EXPORTS_ROOT = Path(__file__).resolve().parents[2] / "exports"

# 8 resumed runs from incomplete_runs.md. (export_dirname, scale, model, original_run)
RUNS = [
    ("ec-mag0-run04-resumed",         "n10", "gpt-5",  "ec-mag0-run04"),
    ("ec-mag1-run04-resumed",         "n10", "gpt-5",  "ec-mag1-run04"),
    ("ec-dom-agi-n10-run01-resumed",  "n10", "gemini", "ec-dom-agi-n10-run01"),
    ("ec-dom-tech-n10-run01-resumed", "n10", "gemini", "ec-dom-tech-n10-run01"),
    ("ec-dom-agi-n20-run01-resumed",  "n20", "gemini", "ec-dom-agi-n20-run01"),
    ("ec-mag5-n20-run01-resumed",     "n20", "gemini", "ec-mag5-n20-run01"),
    ("ec-mag25-n30-run01-resumed",    "n30", "gemini", "ec-mag25-n30-run01"),
    ("ec-mag5-n30-run01-resumed",     "n30", "gemini", "ec-mag5-n30-run01"),
]

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    try:
        HF_TOKEN = HfApi().token
        if not HF_TOKEN:
            raise RuntimeError("no token from HfApi")
    except Exception:
        print("[ERROR] HF_TOKEN not set and not logged in via huggingface-cli")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def clean_jsonl(inpath: Path, drop_fields: set[str]) -> tuple[list[str], int]:
    """Return (cleaned_lines, count). Returns ([], 0) if file missing/empty."""
    if not inpath.exists() or inpath.stat().st_size == 0:
        return [], 0
    out: list[str] = []
    for raw in inpath.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        for f in drop_fields:
            obj.pop(f, None)
        out.append(json.dumps(obj, ensure_ascii=False))
    return out, len(out)


def clean_agents(inpath: Path) -> tuple[list[str], int]:
    """Tag system vs agent rows, drop noisy fields. Return (lines, n_real_agents)."""
    if not inpath.exists() or inpath.stat().st_size == 0:
        return [], 0
    out: list[str] = []
    n_real = 0
    for raw in inpath.read_text().splitlines():
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        for f in DROP_AGENTS:
            obj.pop(f, None)
        if obj.get("name") in SYSTEM_AGENTS:
            obj["type"] = "system"
        else:
            obj["type"] = "agent"
            n_real += 1
        out.append(json.dumps(obj, ensure_ascii=False))
    return out, n_real


def count_window_posts(posts_lines: list[str]) -> int:
    """Posts created in the resume window (2026-05-*)."""
    n = 0
    for line in posts_lines:
        if '"created_at":"2026-05' in line:
            n += 1
    return n


# ---------------------------------------------------------------------------
# README
# ---------------------------------------------------------------------------
def build_readme(rows: list[dict]) -> str:
    total_posts = sum(r["posts"] for r in rows)
    total_new   = sum(r["new_posts"] for r in rows)
    total_cmt   = sum(r["comments"] for r in rows)

    table = "\n".join(
        f"| `{r['original']}` | {r['model']} | {r['scale']} | {r['agents']} | "
        f"{r['posts']} | {r['new_posts']} | {r['comments']} |"
        for r in rows
    )

    return f"""---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
  - multi-agent
  - social-simulation
  - entropy-collapse
  - civiclens
  - moltbook
  - resume
  - gpt-5
  - gemini
pretty_name: "MoltBook Entropy Collapse — Resumed Runs"
size_categories:
  - 1K<n<10K
---

# MoltBook Entropy Collapse — Resumed Runs

Eight of the 48 canonical entropy-collapse runs ended with an empty
`45–60 min` bin (i.e. the agent population stopped posting before the
hour was up). Causes were:

- **GPT-5 (2 runs):** wall-clock batch termination at ~43 min.
- **Gemini Flash Lite (6 runs):** provider-side empty-completion dropout —
  agents transition near-simultaneously from real generations
  (~1500–2000 ms) to ~70–130 ms empty stream events with no assistant
  text. See `docs/incomplete_runs.md` for the full forensic write-up.

This dataset contains the **resumed continuations** of all 8 runs.
Each resume:

1. Restored the original `database-final.sql` into a fresh Postgres volume.
2. Rotated every agent's API key (originals were no longer valid post-export).
3. Brought the API + the full agent roster back online.
4. Ran for ~34 additional minutes.
5. Re-exported posts / comments / agents / activity / database.

The Gemini resumes showed the same mid-run throughput drops as their
originals, but **none collapsed to zero** — every resume produced ≥100 new
posts with full cluster participation.

## Companion datasets

| Repo | Coverage |
|---|---|
| [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments) | GPT-5 baseline (originals of `ec-mag0-run04`, `ec-mag1-run04`) |
| [Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite) | Gemini baseline (originals of the 6 Gemini runs) |

For end-to-end analysis, pair each resumed run here with its original
`database-final.sql` from the companion repo to recover the full
~94-minute trajectory.

## Resume manifest

| Original run | Model | Scale | Active agents | Total posts | New posts (resume window) | Comments |
|---|---|---|---:|---:|---:|---:|
{table}

**Totals:** {total_posts:,} posts ({total_new:,} new in resume window),
{total_cmt:,} comments across {len(rows)} runs.

## Layout

```
data/
├── ec-mag0-run04-resumed/
│   ├── posts.jsonl
│   ├── comments.jsonl
│   ├── agents.jsonl
│   ├── activity.jsonl
│   ├── treatments.jsonl
│   ├── metadata.json
│   ├── experiment_results.json
│   ├── database.sql
│   └── logs/
│       ├── docker-logs-api.txt
│       └── docker-logs-civiclens-ranking-{{1..N}}.txt
└── ...
```

`posts.jsonl` includes both the historical posts restored from the dump
**and** the new posts created during the resume window. Filter on
`created_at >= 2026-05-01T00:00:00Z` to isolate the resume-only posts.

## Schemas

Same field shapes as the parent entropy-collapse repos. The resume
exporter drops a few client-only convenience fields:

- posts: `url`, `my_comment_count`
- comments: `upvotes`, `downvotes`
- agents: `follower_count`, `following_count`, `is_claimed`, `last_active`

The `agents.jsonl` rows have a synthesized `type` field: `agent` for the
10/20/30-agent cluster, `system` for the CivicLens infrastructure
accounts (`civiclens_seed`, `civiclens_world`, `civiclens_nudger`).

## Citation

```bibtex
@dataset{{moltbook_entropy_collapse_resumes_2026,
  title  = {{MoltBook Entropy Collapse — Resumed Runs}},
  author = {{Nangia, Ayush}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{REPO_ID}}},
  note   = {{Resume continuations of the 8 incomplete canonical runs from the entropy-collapse experiment series}}
}}
```

## License

Apache 2.0
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def stage_run(src: Path, dst: Path) -> dict:
    """Copy + clean one export dir into staging. Returns row dict for README."""
    dst.mkdir(parents=True, exist_ok=True)
    logs = dst / "logs"
    logs.mkdir(exist_ok=True)

    # Cleaned JSONL
    posts, n_posts = clean_jsonl(src / "posts.jsonl", DROP_POSTS)
    if posts:
        (dst / "posts.jsonl").write_text("\n".join(posts) + "\n")

    comments, n_cmt = clean_jsonl(src / "comments.jsonl", DROP_COMMENTS)
    if comments:
        (dst / "comments.jsonl").write_text("\n".join(comments) + "\n")

    agents, n_real = clean_agents(src / "agents.jsonl")
    if agents:
        (dst / "agents.jsonl").write_text("\n".join(agents) + "\n")

    # Pass-through files
    for fname in ("activity.jsonl", "treatments.jsonl",
                  "metadata.json", "experiment_results.json",
                  "database.sql"):
        f = src / fname
        if f.exists() and f.stat().st_size > 0:
            shutil.copy2(f, dst / fname)

    # Logs go under logs/
    for log in sorted(src.glob("docker-logs-*.txt")):
        shutil.copy2(log, logs / log.name)

    return {
        "posts": n_posts,
        "new_posts": count_window_posts(posts),
        "comments": n_cmt,
        "agents": n_real,
    }


def main():
    print("=" * 70)
    print("Upload resumed entropy-collapse runs -> HuggingFace")
    print(f"  REPO_ID  = {REPO_ID}  (private={REPO_PRIVATE})")
    print(f"  EXPORTS  = {EXPORTS_ROOT}")
    print("=" * 70)

    # Verify all 8 source dirs exist
    missing = [name for name, *_ in RUNS if not (EXPORTS_ROOT / name).exists()]
    if missing:
        print(f"[ERROR] missing export dirs: {missing}")
        sys.exit(1)

    api = HfApi(token=HF_TOKEN)
    print(f"\nAuthenticated as: {api.whoami()['name']}")

    print(f"\n[1/3] Creating dataset repo {REPO_ID}…")
    create_repo(REPO_ID, repo_type="dataset", private=REPO_PRIVATE,
                exist_ok=True, token=HF_TOKEN)
    print("  [OK]")

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_resumes_"))
    print(f"\n[2/3] Staging cleaned data in {staging}")
    rows: list[dict] = []
    for name, scale, model, original in RUNS:
        src = EXPORTS_ROOT / name
        dst = staging / "data" / name
        print(f"  -> {name}  ({model}, {scale})")
        stats = stage_run(src, dst)
        rows.append({
            "original": original,
            "model":    model,
            "scale":    scale,
            **stats,
        })
        print(f"     posts={stats['posts']}  new={stats['new_posts']}  "
              f"comments={stats['comments']}  agents={stats['agents']}")

    (staging / "README.md").write_text(build_readme(rows))
    print("  [OK] README.md generated")

    print(f"\n[3/3] Uploading to {REPO_ID} via upload_large_folder…")
    # upload_large_folder: parallel workers + resumable. Required because
    # combined database.sql + docker-logs payload exceeds single-POST limits.
    api.upload_large_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        ignore_patterns=[".git/*", ".gitignore", "**/.DS_Store"],
    )

    print("\n" + "=" * 70)
    print(f"DONE -> https://huggingface.co/datasets/{REPO_ID}")
    print("=" * 70)
    shutil.rmtree(staging, ignore_errors=True)


if __name__ == "__main__":
    main()
