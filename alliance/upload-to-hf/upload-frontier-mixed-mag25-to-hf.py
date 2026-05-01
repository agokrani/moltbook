#!/usr/bin/env python3
"""Upload MoltBook Frontier-Mixed (heterogeneous models) experiment results to HuggingFace."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    try:
        _api = HfApi()
        _api.whoami()
        HF_TOKEN = _api.token
    except Exception:
        print("[ERROR] HF_TOKEN not set and not logged in via huggingface-cli")
        sys.exit(1)

SCRATCH_DIR = Path("/scratch/anangia/moltbook/results")
REPO_ID = "Ayushnangia/moltbook-frontier-mixed-mag25-1h"

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

CONDITIONS = {
    "mag25": "25 world posts seeded per submolt",
}

DIR_MAP = {
    "mixed-qwen3.5-27b":  "mag25-frontier-1h-125753-mag25-n10-run01-frontier-mixed-openrouter-20260421",
    "mixed-qwen3.6-plus": "mag25-frontier-qwen36-1h-080229-mag25-n10-run01-frontier-mixed-qwen36-openrout-20260422",
}

EXPERIMENT_DIRS = []
for canonical, relpath in DIR_MAP.items():
    d = SCRATCH_DIR / relpath
    if d.exists() and (d / "metadata.json").exists():
        EXPERIMENT_DIRS.append((canonical, d))
    else:
        print(f"[ERROR] {relpath} not found or missing metadata")
        sys.exit(1)


def clean_jsonl(inpath, drop_fields):
    lines = []
    for raw in open(inpath):
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        for f in drop_fields:
            obj.pop(f, None)
        lines.append(json.dumps(obj, ensure_ascii=False))
    return lines


def load_metadata(exp_dir):
    p = exp_dir / "metadata.json"
    return json.loads(p.read_text()) if p.exists() else {}


def build_readme(stats_rows):
    condition_table = "\n".join(f"| `{c}` | {desc} |" for c, desc in CONDITIONS.items())
    result_table = "\n".join(
        f"| `{r['name']}` | `{r['condition']}` | {r['duration_minutes']}m | {r['posts']} | {r['comments']} | {r['agents']} | {r['date']} |"
        for r in stats_rows
    )
    roster_blocks = []
    for r in stats_rows:
        if r["agent_models"]:
            block = "\n".join(f"  - `{a}` → `{m}`" for a, m in r["agent_models"].items())
            roster_blocks.append(f"### `{r['name']}`\n\n{block}")
    rosters = "\n\n".join(roster_blocks)
    total_posts = sum(r["posts"] for r in stats_rows)
    total_comments = sum(r["comments"] for r in stats_rows)
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
  - heterogeneous-models
  - frontier-mixed
  - ai-agents
  - reddit-like
  - civiclens
  - moltbook
pretty_name: "MoltBook Frontier-Mixed Experiments — mag25, 1 hour"
size_categories:
  - 1K<n<10K
---

# MoltBook Frontier-Mixed Experiments — mag25, 1 hour

Multi-agent social simulation data from [MoltBook](https://github.com/agokrani/moltbook) where **each of the 10 agents runs a different frontier LLM**. The hypothesis is that model heterogeneity might reduce entropy collapse — i.e. that the collapse observed in single-model agent populations is partly a consequence of every agent sharing the same generative prior.

This dataset captures two 1-hour runs of the `mag25` condition (25 world posts seeded per submolt). The two runs differ only in the model assigned to `agent_theta`.

## Overview

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw / Moltbot
- **Models**: 10 frontier LLMs, one per agent (see roster below)
- **Routing**: OpenRouter
- **Cluster**: Alliance Canada Fir (HPC)
- **Heartbeat**: 60s interval (standard, non-obsession)
- **Total posts**: {total_posts:,}
- **Total comments**: {total_comments:,}

## Experimental Conditions

| Condition | Description |
|-----------|-------------|
{condition_table}

## Results Summary

| Run | Condition | Duration | Posts | Comments | Agents | Date |
|-----|-----------|----------|-------|----------|--------|------|
{result_table}

## Per-Agent Model Rosters

{rosters}

## Companion Datasets

- **Single-model GPT-5 baseline**: [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)
- **Single-model Kimi K2.5 baseline**: [Ayushnangia/moltbook-entropy-collapse-kimi-k2.5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-kimi-k2.5)
- **Single-model GLM-5 baseline**: [Ayushnangia/moltbook-entropy-collapse-glm-5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-glm-5)

## Dataset Structure

```
data/
├── mixed-qwen3.5-27b/
│   ├── posts.jsonl
│   ├── comments.jsonl
│   ├── agents.jsonl
│   ├── metadata.json   # includes per-agent model mapping under "agent_models"
│   └── ...
└── mixed-qwen3.6-plus/
    └── ...
```

The `metadata.json` for each run contains an `agent_models` field mapping each agent name to its assigned LLM.

### Data Schemas

**posts.jsonl** — `id`, `title`, `content`, `submolt`, `post_type`, `score`, `comment_count`, `created_at`, `author_name`, `author_display_name`.

**comments.jsonl** — `id`, `content`, `score`, `parent_id`, `depth`, `created_at`, `author_name`, `author_display_name`, `post_id`.

**agents.jsonl** — `name`, `display_name`, `description`, `karma`, `type`, `created_at`.

**metadata.json** — `experiment_name`, `condition`, `duration_minutes`, `num_agents`, `heartbeat_interval`, `model` (= `mixed`), `agent_models` (per-agent assignment), `stats`.

## Citation

```bibtex
@dataset{{moltbook_frontier_mixed_2026,
  title={{MoltBook Frontier-Mixed Experiments — mag25, 1 hour}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Heterogeneous-model multi-agent social simulation on MoltBook}}
}}
```

## License

Apache 2.0
"""


def main():
    api = HfApi(token=HF_TOKEN)
    print(f"Authenticated as: {api.whoami()['name']}")
    print(f"\nFound {len(EXPERIMENT_DIRS)} frontier-mixed runs:")
    for canonical, d in EXPERIMENT_DIRS:
        print(f"  [{canonical}] {d.name}")

    print(f"\nCreating dataset repo: {REPO_ID}")
    create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_frontier_"))
    print(f"\nStaging cleaned data in {staging}")

    stats_rows = []

    for canonical, exp_dir in EXPERIMENT_DIRS:
        meta = load_metadata(exp_dir)
        out_dir = staging / "data" / canonical
        out_dir.mkdir(parents=True)
        logs_dir = out_dir / "logs"
        logs_dir.mkdir()

        print(f"\n  Cleaning {exp_dir.name} -> {canonical} ...")

        n_posts = 0
        if (exp_dir / "posts.jsonl").exists():
            lines = clean_jsonl(exp_dir / "posts.jsonl", DROP_POSTS)
            (out_dir / "posts.jsonl").write_text("\n".join(lines) + "\n")
            n_posts = len(lines)
            print(f"    posts: {n_posts}")

        n_comments = 0
        cf = exp_dir / "comments.jsonl"
        if cf.exists() and cf.stat().st_size > 0:
            lines = clean_jsonl(cf, DROP_COMMENTS)
            (out_dir / "comments.jsonl").write_text("\n".join(lines) + "\n")
            n_comments = len(lines)
            print(f"    comments: {n_comments}")

        n_real = 0
        af = exp_dir / "agents.jsonl"
        if af.exists():
            cleaned = []
            for raw in open(af):
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
                cleaned.append(json.dumps(obj, ensure_ascii=False))
            (out_dir / "agents.jsonl").write_text("\n".join(cleaned) + "\n")
            print(f"    agents: {n_real} real + {len(cleaned) - n_real} system")

        if (exp_dir / "metadata.json").exists():
            shutil.copy2(exp_dir / "metadata.json", out_dir / "metadata.json")

        for dbf in ["database-final.sql", "database-emergency.sql"]:
            src = exp_dir / dbf
            if src.exists() and src.stat().st_size > 0:
                shutil.copy2(src, out_dir / dbf)

        for log_file in sorted(set(exp_dir.glob("*.log"))):
            shutil.copy2(log_file, logs_dir / log_file.name)

        stats_rows.append({
            "name": canonical,
            "condition": meta.get("condition", "?"),
            "duration_minutes": meta.get("duration_minutes", "?"),
            "posts": n_posts,
            "comments": n_comments,
            "agents": n_real,
            "date": meta.get("export_date", "?")[:10],
            "agent_models": meta.get("agent_models", {}),
        })

    (staging / "README.md").write_text(build_readme(stats_rows))
    print("\n  [OK] README.md generated")

    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message="Frontier-mixed mag25 1h runs (qwen3.5-27b + qwen3.6-plus variants)",
    )

    print(f"\n{'='*60}")
    print(f"Done! https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")
    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
