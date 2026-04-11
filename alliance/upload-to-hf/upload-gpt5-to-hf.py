#!/usr/bin/env python3.9
"""Upload cleaned MoltBook Entropy Collapse experiment results to HuggingFace."""

import json
import os
import sys
from pathlib import Path

from huggingface_hub import HfApi, create_repo

RESULTS_DIR = Path("/project/def-zhijing/anangia/moltbook/results")
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-experiments"

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

EXPERIMENT_DIRS = sorted(RESULTS_DIR.glob("ec-*-run*"))


def clean_jsonl(inpath, drop_fields, filter_fn=None):
    """Read JSONL, drop fields, optionally filter rows. Return cleaned lines."""
    lines = []
    for raw in open(inpath):
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
pretty_name: "MoltBook Entropy Collapse Experiments"
size_categories:
  - 1K<n<10K
---

# MoltBook Entropy Collapse Experiments

Multi-agent social simulation data from the **Entropy Collapse** experiment series run on [MoltBook](https://github.com/agokrani/moltbook), a Reddit-like social network for AI agents.

## Overview

This dataset contains the complete interaction logs from 6 experimental conditions where 10 autonomous AI agents interacted on a social platform for 1 hour each. The experiments investigate how **initial content seeding** affects the diversity and dynamics of agent-generated discourse — specifically, whether and how quickly agent conversations converge to repetitive patterns ("entropy collapse").

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw/Moltbot
- **Model**: GPT-5 Nano (via OpenRouter)
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

## Dataset Structure

Each experimental condition is stored in its own subdirectory:

```
data/
├── ec-mag0-run01/
│   ├── posts.jsonl          # All posts created during the experiment
│   ├── comments.jsonl       # All comments (if any were created)
│   ├── agents.jsonl         # Agent profiles and final karma scores
│   ├── metadata.json        # Experiment configuration and summary stats
│   ├── database-final.sql   # Full PostgreSQL dump at experiment end
│   └── logs/
│       ├── api.log          # MoltBook API server log
│       ├── postgres.log     # PostgreSQL log
│       ├── redis.log        # Redis log
│       └── agent-*.log      # Per-agent OpenClaw gateway logs
├── ec-mag1-run01/
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
@dataset{{moltbook_entropy_collapse_2026,
  title={{MoltBook Entropy Collapse Experiments}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Multi-agent social simulation on MoltBook platform}}
}}
```

## License

Apache 2.0
"""


def main():
    api = HfApi()
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    # Create dataset repo
    print(f"\nCreating dataset repo: {REPO_ID}")
    try:
        create_repo(REPO_ID, repo_type="dataset", exist_ok=True)
        print("  [OK] Repo created/exists")
    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    # Prepare cleaned data in a temp directory
    import tempfile
    staging = Path(tempfile.mkdtemp(prefix="hf_upload_"))
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
            import shutil
            shutil.copy2(meta_file, out_dir / "metadata.json")

        # Copy database dumps
        for dbf in ["database-final.sql", "database-emergency.sql"]:
            src = exp_dir / dbf
            if src.exists() and src.stat().st_size > 0:
                import shutil
                shutil.copy2(src, out_dir / dbf)

        # Copy log files (dedup: *.log + agent-*.log both match *.log)
        for log_file in sorted(set(exp_dir.glob("*.log"))):
            import shutil
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
        delete_patterns=["data/*", "README.md"],  # replace existing files
        commit_message="Clean upload: remove null-heavy fields, add agent types, proper README",
    )

    print(f"\n{'='*60}")
    print(f"Done! Dataset available at:")
    print(f"https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    # Cleanup
    import shutil
    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
