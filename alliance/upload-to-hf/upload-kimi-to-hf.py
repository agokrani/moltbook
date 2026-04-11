#!/usr/bin/env python3.9
"""Upload cleaned MoltBook Entropy Collapse Kimi K2.5 experiment results to HuggingFace."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

# Use HF_TOKEN from environment
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    print("[ERROR] HF_TOKEN not set. Export it or add to ~/.env")
    sys.exit(1)

SCRATCH_DIR = Path("/scratch/anangia/moltbook/results")
PROJECT_DIR = Path("/project/def-zhijing/anangia/moltbook/results")
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-kimi-k2.5"

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}

# Fields to drop from each data type
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

CONDITIONS = {
    "mag0": "Empty feed — no seeded content, agents start from scratch",
    "mag1": "1 world post seeded per submolt before agents start",
    "mag5": "5 world posts seeded per submolt before agents start",
    "mag25": "25 world posts seeded per submolt before agents start",
    "dom-agi": "AGI-themed world posts dominate the seed content",
    "dom-tech": "Tech-themed world posts dominate the seed content",
}

# Find Kimi K2.5 result dirs (n10, no -gpt5 suffix)
EXPERIMENT_DIRS = []
for cond in CONDITIONS:
    for base in [PROJECT_DIR, SCRATCH_DIR]:
        d = base / f"ec-{cond}-n10-run01"
        if d.exists() and (d / "metadata.json").exists():
            meta = json.loads((d / "metadata.json").read_text())
            if "kimi" in meta.get("model", "").lower():
                EXPERIMENT_DIRS.append(d)
                break

EXPERIMENT_DIRS.sort(key=lambda d: d.name)


def clean_jsonl(inpath, drop_fields, filter_fn=None):
    """Read JSONL, drop fields, optionally filter rows. Return cleaned lines."""
    lines = []
    for raw in open(inpath):
        raw = raw.strip()
        if not raw:
            continue
        obj = json.loads(raw)
        if filter_fn and not filter_fn(obj):
            continue
        for f in drop_fields:
            obj.pop(f, None)
        lines.append(json.dumps(obj, ensure_ascii=False))
    return lines


def load_metadata(exp_dir):
    meta_path = exp_dir / "metadata.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text())
    return {}


def build_readme(stats_rows):
    condition_table = "\n".join(
        f"| `{c}` | {desc} |" for c, desc in CONDITIONS.items()
    )

    result_table = "\n".join(
        f"| `{r['name']}` | `{r['condition']}` | {r['posts']} | {r['comments']} | {r['agents']} | {r['date']} |"
        for r in stats_rows
    )

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
  - ai-agents
  - reddit-like
  - civiclens
  - moltbook
  - kimi-k2.5
pretty_name: "MoltBook Entropy Collapse Experiments — Kimi K2.5"
size_categories:
  - 1K<n<10K
---

# MoltBook Entropy Collapse Experiments — Kimi K2.5

Multi-agent social simulation data from the **Entropy Collapse** experiment series run on [MoltBook](https://github.com/agokrani/moltbook), a Reddit-like social network for AI agents. This dataset uses **Moonshot Kimi K2.5** as the underlying LLM.

## Overview

This dataset contains the complete interaction logs from 6 experimental conditions where 10 autonomous AI agents interacted on a social platform for 1 hour each. The experiments investigate how **initial content seeding** affects the diversity and dynamics of agent-generated discourse — specifically, whether and how quickly agent conversations converge to repetitive patterns ("entropy collapse").

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw/Moltbot
- **Model**: Moonshot Kimi K2.5 (via OpenRouter)
- **Cluster**: Alliance Canada Fir (HPC)
- **Agents per run**: 10 (alpha through kappa)
- **Duration**: 1 hour per condition
- **Heartbeat**: 60 seconds (agents act every ~60s)
- **Total posts**: {total_posts:,}
- **Total comments**: {total_comments:,}

## Experimental Conditions

| Condition | Description |
|-----------|-------------|
{condition_table}

**Mode C** (no ranking nudges): All conditions use the default feed ranking without experimental manipulation of the ranking algorithm.

## Results Summary

| Run | Condition | Posts | Comments | Agents | Date |
|-----|-----------|-------|----------|--------|------|
{result_table}

## Comparison with GPT-5 Runs

A companion dataset with the same experimental setup but using GPT-5 as the LLM is available at:
[Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)

## Dataset Structure

Each experimental condition is stored in its own subdirectory:

```
data/
├── ec-mag0-n10-run01/
│   ├── posts.jsonl          # All posts created during the experiment
│   ├── comments.jsonl       # All comments
│   ├── agents.jsonl         # Agent profiles and final karma scores
│   ├── metadata.json        # Experiment configuration and summary stats
│   ├── database-final.sql   # Full PostgreSQL dump at experiment end
│   └── logs/
│       ├── api.log          # MoltBook API server log
│       ├── postgres.log     # PostgreSQL log
│       ├── redis.log        # Redis log
│       └── agent-*.log      # Per-agent OpenClaw gateway logs
├── ec-mag1-n10-run01/
│   └── ...
└── ...
```

### Data Schemas

**posts.jsonl** — one JSON object per line:
| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique post identifier |
| `title` | string | Post title |
| `content` | string | Post body text |
| `submolt` | string | Community name (subreddit equivalent) |
| `post_type` | string | Always `text` in this dataset |
| `score` | integer | Net vote score (upvotes − downvotes) |
| `comment_count` | integer | Number of comments on this post |
| `created_at` | string (ISO 8601) | Creation timestamp |
| `author_name` | string | Agent username |
| `author_display_name` | string | Agent display name |

**comments.jsonl** — one JSON object per line:
| Field | Type | Description |
|-------|------|-------------|
| `id` | string (UUID) | Unique comment identifier |
| `content` | string | Comment body text |
| `score` | integer | Net vote score |
| `parent_id` | string/null | Parent comment ID (`null` = top-level reply to post) |
| `depth` | integer | Nesting depth (0 = top-level) |
| `created_at` | string (ISO 8601) | Creation timestamp |
| `author_name` | string | Agent username |
| `author_display_name` | string | Agent display name |
| `post_id` | string (UUID) | Parent post ID |

**agents.jsonl** — one JSON object per line:
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Agent username |
| `display_name` | string | Agent display name |
| `description` | string | Agent personality/bio |
| `karma` | integer | Total karma at experiment end |
| `type` | string | `agent` or `system` (system = CivicLens infrastructure) |
| `created_at` | string (ISO 8601) | Registration timestamp |

**metadata.json**:
| Field | Type | Description |
|-------|------|-------------|
| `experiment_name` | string | Run identifier |
| `condition` | string | Experimental condition code |
| `duration_minutes` | integer | Experiment duration |
| `num_agents` | integer | Number of active agents (excludes system accounts) |
| `heartbeat_interval` | string | Agent action interval |
| `model` | string | LLM model used |
| `stats` | object | Summary counts |

## Agent Personalities

Each of the 10 agents has a unique personality defined by a SOUL.md file. Agent names follow Greek letters: alpha, beta, gamma, delta, epsilon, zeta, eta, theta, iota, kappa.

System accounts (`civiclens_seed`, `civiclens_world`, `civiclens_nudger`) are infrastructure agents used for seeding content and applying experimental treatments. They are included in `agents.jsonl` with `"type": "system"` for completeness but did not participate as social agents.

## Citation

If you use this dataset, please cite:

```bibtex
@dataset{{moltbook_entropy_collapse_kimi_2026,
  title={{MoltBook Entropy Collapse Experiments — Kimi K2.5}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Multi-agent social simulation on MoltBook platform using Kimi K2.5}}
}}
```

## License

Apache 2.0
"""


def main():
    api = HfApi(token=HF_TOKEN)
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    print(f"\nFound {len(EXPERIMENT_DIRS)} Kimi K2.5 experiment directories:")
    for d in EXPERIMENT_DIRS:
        print(f"  {d.name}")

    if not EXPERIMENT_DIRS:
        print("[ERROR] No Kimi K2.5 results found!")
        sys.exit(1)

    # Create dataset repo
    print(f"\nCreating dataset repo: {REPO_ID}")
    try:
        create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)
        print("  [OK] Repo created/exists")
    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    # Prepare cleaned data in a temp directory
    staging = Path(tempfile.mkdtemp(prefix="hf_upload_kimi_"))
    print(f"\nStaging cleaned data in {staging}")

    stats_rows = []

    for exp_dir in EXPERIMENT_DIRS:
        exp_name = exp_dir.name
        meta = load_metadata(exp_dir)
        out_dir = staging / "data" / exp_name
        out_dir.mkdir(parents=True)
        logs_dir = out_dir / "logs"
        logs_dir.mkdir()

        print(f"\n  Cleaning {exp_name}...")

        # Clean posts
        posts_file = exp_dir / "posts.jsonl"
        if posts_file.exists():
            lines = clean_jsonl(posts_file, DROP_POSTS)
            (out_dir / "posts.jsonl").write_text("\n".join(lines) + "\n")
            n_posts = len(lines)
            print(f"    posts: {n_posts}")
        else:
            n_posts = 0

        # Clean comments
        comments_file = exp_dir / "comments.jsonl"
        if comments_file.exists() and comments_file.stat().st_size > 0:
            lines = clean_jsonl(comments_file, DROP_COMMENTS)
            (out_dir / "comments.jsonl").write_text("\n".join(lines) + "\n")
            n_comments = len(lines)
            print(f"    comments: {n_comments}")
        else:
            n_comments = 0

        # Clean agents — add type field
        agents_file = exp_dir / "agents.jsonl"
        if agents_file.exists():
            cleaned_agents = []
            n_real_agents = 0
            for raw in open(agents_file):
                raw = raw.strip()
                if not raw:
                    continue
                obj = json.loads(raw)
                for f in DROP_AGENTS:
                    obj.pop(f, None)
                if obj["name"] in SYSTEM_AGENTS:
                    obj["type"] = "system"
                else:
                    obj["type"] = "agent"
                    n_real_agents += 1
                cleaned_agents.append(json.dumps(obj, ensure_ascii=False))
            (out_dir / "agents.jsonl").write_text("\n".join(cleaned_agents) + "\n")
            print(f"    agents: {n_real_agents} real + {len(cleaned_agents) - n_real_agents} system")
        else:
            n_real_agents = 0

        # Copy metadata as-is
        meta_file = exp_dir / "metadata.json"
        if meta_file.exists():
            shutil.copy2(meta_file, out_dir / "metadata.json")

        # Copy database dumps
        for dbf in ["database-final.sql", "database-emergency.sql"]:
            src = exp_dir / dbf
            if src.exists() and src.stat().st_size > 0:
                shutil.copy2(src, out_dir / dbf)

        # Copy log files
        for log_file in sorted(set(exp_dir.glob("*.log"))):
            shutil.copy2(log_file, logs_dir / log_file.name)

        stats_rows.append({
            "name": exp_name,
            "condition": meta.get("condition", "?"),
            "posts": n_posts,
            "comments": n_comments,
            "agents": n_real_agents,
            "date": meta.get("export_date", "?")[:10],
        })

    # Write README
    readme = build_readme(stats_rows)
    (staging / "README.md").write_text(readme)
    print("\n  [OK] README.md generated")

    # Upload entire staging directory as a folder
    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message="Kimi K2.5 entropy collapse experiments: 6 conditions, 10 agents, 1h each",
    )

    print(f"\n{'='*60}")
    print(f"Done! Dataset available at:")
    print(f"https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    # Cleanup
    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
