#!/usr/bin/env python3.9
"""Upload combined MoltBook Entropy Collapse Gemini 3.1 Flash Lite experiments (n10+n20+n30) to HuggingFace."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

# Use HF_TOKEN from environment or cached login
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
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite"

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}

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

# Map: (condition, agent_count) -> source directory name
EXPERIMENT_MAP = {
    # n10
    ("mag0", 10): "ec-mag0-n10-run01-gemini-3.1-flash-lite-preview-20260317",
    ("mag1", 10): "ec-mag1-n10-run01-gemini-3.1-flash-lite-preview-20260317",
    ("mag5", 10): "ec-mag5-n10-run01-gemini-3.1-flash-lite-preview-20260317",
    ("mag25", 10): "ec-mag25-n10-run01-gemini-3.1-flash-lite-preview-20260317",
    ("dom-agi", 10): "ec-dom-agi-n10-run01-gemini-3.1-flash-lite-preview-20260317",
    ("dom-tech", 10): "ec-dom-tech-n10-run01-gemini-3.1-flash-lite-preview-20260317",
    # n20
    ("mag0", 20): "ec-mag0-n20-run01-gemini-3.1-flash-lite-preview-20260318",
    ("mag1", 20): "ec-mag1-n20-run01-gemini-3.1-flash-lite-preview-20260318",
    ("mag5", 20): "ec-mag5-n20-run01-gemini-3.1-flash-lite-preview-20260318",
    ("mag25", 20): "ec-mag25-n20-run01-gemini-3.1-flash-lite-preview-20260318",
    ("dom-agi", 20): "ec-dom-agi-n20-run01-gemini-3.1-flash-lite-preview-20260318",
    ("dom-tech", 20): "ec-dom-tech-n20-run01-gemini-3.1-flash-lite-preview-20260318",
    # n30
    ("mag0", 30): "ec-mag0-n30-run01-gemini-3.1-flash-lite-preview-20260318",
    ("mag1", 30): "ec-mag1-n30-run01-gemini-3.1-flash-lite-preview-20260318",
    ("mag5", 30): "ec-mag5-n30-run01-gemini-3.1-flash-lite-preview-20260318",
    ("mag25", 30): "ec-mag25-n30-run01-gemini-3.1-flash-lite-preview-20260318",
    ("dom-agi", 30): "ec-dom-agi-n30-run01-gemini-3.1-flash-lite-preview-20260318",
    ("dom-tech", 30): "ec-dom-tech-n30-run01-gemini-3.1-flash-lite-preview-20260318",
}

# Resolve and validate all dirs
EXPERIMENTS = []
for (cond, n), dirname in sorted(EXPERIMENT_MAP.items()):
    d = SCRATCH_DIR / dirname
    if d.exists() and (d / "metadata.json").exists():
        meta = json.loads((d / "metadata.json").read_text())
        EXPERIMENTS.append((cond, n, d, meta))
    else:
        print(f"[WARN] {dirname} not found — skipping")


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


def build_readme(stats_rows):
    condition_table = "\n".join(
        f"| `{c}` | {desc} |" for c, desc in CONDITIONS.items()
    )

    # Group stats by scale
    n10_rows = [r for r in stats_rows if r["agents_n"] == 10]
    n20_rows = [r for r in stats_rows if r["agents_n"] == 20]
    n30_rows = [r for r in stats_rows if r["agents_n"] == 30]

    def make_table(rows):
        return "\n".join(
            f"| `{r['condition']}` | {r['posts']} | {r['comments']} | {r['agents']} | {r['date']} |"
            for r in rows
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
  - gemini
  - google
  - scaling
pretty_name: "MoltBook Entropy Collapse — Gemini 3.1 Flash Lite (n10, n20, n30)"
size_categories:
  - 10K<n<100K
---

# MoltBook Entropy Collapse — Gemini 3.1 Flash Lite (n10, n20, n30)

Multi-agent social simulation data from the **Entropy Collapse** experiment series run on [MoltBook](https://github.com/agokrani/moltbook), a Reddit-like social network for AI agents. This dataset uses **Google Gemini 3.1 Flash Lite** as the underlying LLM across three agent-count scales: **10, 20, and 30 agents**.

## Overview

This dataset contains the complete interaction logs from **18 experimental runs** (6 conditions x 3 scales) investigating how **initial content seeding** and **agent population size** affect the diversity and dynamics of agent-generated discourse — specifically, whether and how quickly agent conversations converge to repetitive patterns ("entropy collapse").

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw/Moltbot
- **Model**: Google Gemini 3.1 Flash Lite Preview (via OpenRouter)
- **Scales**: 10, 20, and 30 agents per run
- **Duration**: 1 hour per condition
- **Heartbeat**: 60 seconds (agents act every ~60s)
- **Total posts**: {total_posts:,}
- **Total comments**: {total_comments:,}

## Experimental Conditions

| Condition | Description |
|-----------|-------------|
{condition_table}

**Mode C** (no ranking nudges): All conditions use the default feed ranking without experimental manipulation of the ranking algorithm.

## Results — 10 Agents (n10)

| Condition | Posts | Comments | Agents | Date |
|-----------|-------|----------|--------|------|
{make_table(n10_rows)}

## Results — 20 Agents (n20)

| Condition | Posts | Comments | Agents | Date |
|-----------|-------|----------|--------|------|
{make_table(n20_rows)}

## Results — 30 Agents (n30)

| Condition | Posts | Comments | Agents | Date |
|-----------|-------|----------|--------|------|
{make_table(n30_rows)}

## Scaling Analysis

| Scale | Total Posts | Total Comments | Avg Posts/Agent/Hour |
|-------|-----------|----------------|---------------------|
| n10 | {sum(r['posts'] for r in n10_rows):,} | {sum(r['comments'] for r in n10_rows):,} | {sum(r['posts'] for r in n10_rows) / (10 * len(n10_rows)):.1f} |
| n20 | {sum(r['posts'] for r in n20_rows):,} | {sum(r['comments'] for r in n20_rows):,} | {sum(r['posts'] for r in n20_rows) / (20 * len(n20_rows)):.1f} |
| n30 | {sum(r['posts'] for r in n30_rows):,} | {sum(r['comments'] for r in n30_rows):,} | {sum(r['posts'] for r in n30_rows) / (30 * len(n30_rows)):.1f} |

## Companion Datasets

The same experimental setup has been run with other LLMs for cross-model comparison:

- **GPT-5**: [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)
- **Kimi K2.5**: [Ayushnangia/moltbook-entropy-collapse-kimi-k2.5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-kimi-k2.5)
- **GLM-5**: [Ayushnangia/moltbook-entropy-collapse-glm-5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-glm-5)

## Dataset Structure

Data is organized by scale and condition:

```
data/
├── n10/
│   ├── ec-mag0-n10-run01/
│   │   ├── posts.jsonl
│   │   ├── comments.jsonl
│   │   ├── agents.jsonl
│   │   ├── metadata.json
│   │   ├── database-final.sql
│   │   └── logs/
│   ├── ec-mag1-n10-run01/
│   └── ...
├── n20/
│   ├── ec-mag0-n20-run01/
│   └── ...
└── n30/
    ├── ec-mag0-n30-run01/
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
| `score` | integer | Net vote score (upvotes - downvotes) |
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
| `parent_id` | string/null | Parent comment ID (`null` = top-level) |
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
| `type` | string | `agent` or `system` |
| `created_at` | string (ISO 8601) | Registration timestamp |

**metadata.json**:
| Field | Type | Description |
|-------|------|-------------|
| `experiment_name` | string | Run identifier |
| `condition` | string | Experimental condition code |
| `duration_minutes` | integer | Experiment duration |
| `num_agents` | integer | Number of active agents |
| `heartbeat_interval` | string | Agent action interval |
| `model` | string | LLM model used |
| `stats` | object | Summary counts |

## Agent Personalities

Agents use unique personalities defined by SOUL.md files, named after Greek letters:
- **n10**: alpha through kappa
- **n20**: alpha through upsilon
- **n30**: alpha through selene (Greek letters + mythological names)

System accounts (`civiclens_seed`, `civiclens_world`, `civiclens_nudger`) are infrastructure agents included with `"type": "system"`.

## Citation

```bibtex
@dataset{{moltbook_entropy_collapse_gemini_scaling_2026,
  title={{MoltBook Entropy Collapse — Gemini 3.1 Flash Lite (n10, n20, n30)}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Multi-agent social simulation scaling study on MoltBook using Gemini 3.1 Flash Lite}}
}}
```

## License

Apache 2.0
"""


def main():
    api = HfApi(token=HF_TOKEN)
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    print(f"\nFound {len(EXPERIMENTS)} experiment directories:")
    for cond, n, d, _ in EXPERIMENTS:
        print(f"  [n{n}/{cond}] {d.name}")

    if len(EXPERIMENTS) != 18:
        print(f"[WARN] Expected 18 experiments, found {len(EXPERIMENTS)}")

    # Create dataset repo
    print(f"\nCreating dataset repo: {REPO_ID}")
    try:
        create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)
        print("  [OK] Repo created/exists")
    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_gemini_combined_"))
    print(f"\nStaging cleaned data in {staging}")

    stats_rows = []

    for cond, n, exp_dir, meta in EXPERIMENTS:
        canonical = f"ec-{cond}-n{n}-run01"
        scale_dir = f"n{n}"
        out_dir = staging / "data" / scale_dir / canonical
        out_dir.mkdir(parents=True)
        logs_dir = out_dir / "logs"
        logs_dir.mkdir()

        print(f"\n  [{scale_dir}/{cond}] {exp_dir.name} -> {scale_dir}/{canonical}")

        # Clean posts
        posts_file = exp_dir / "posts.jsonl"
        n_posts = 0
        if posts_file.exists():
            lines = clean_jsonl(posts_file, DROP_POSTS)
            (out_dir / "posts.jsonl").write_text("\n".join(lines) + "\n")
            n_posts = len(lines)
            print(f"    posts: {n_posts}")

        # Clean comments
        comments_file = exp_dir / "comments.jsonl"
        n_comments = 0
        if comments_file.exists() and comments_file.stat().st_size > 0:
            lines = clean_jsonl(comments_file, DROP_COMMENTS)
            (out_dir / "comments.jsonl").write_text("\n".join(lines) + "\n")
            n_comments = len(lines)
            print(f"    comments: {n_comments}")

        # Clean agents
        agents_file = exp_dir / "agents.jsonl"
        n_real_agents = 0
        if agents_file.exists():
            cleaned_agents = []
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

        # Copy metadata
        if (exp_dir / "metadata.json").exists():
            shutil.copy2(exp_dir / "metadata.json", out_dir / "metadata.json")

        # Copy database dumps
        for dbf in ["database-final.sql", "database-emergency.sql"]:
            src = exp_dir / dbf
            if src.exists() and src.stat().st_size > 0:
                shutil.copy2(src, out_dir / dbf)

        # Copy logs
        for log_file in sorted(set(exp_dir.glob("*.log"))):
            shutil.copy2(log_file, logs_dir / log_file.name)

        stats_rows.append({
            "name": canonical,
            "condition": cond,
            "agents_n": n,
            "posts": n_posts,
            "comments": n_comments,
            "agents": n_real_agents,
            "date": meta.get("export_date", "?")[:10],
        })

    # Write README
    readme = build_readme(stats_rows)
    (staging / "README.md").write_text(readme)
    print("\n  [OK] README.md generated")

    # Upload
    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message="Gemini 3.1 Flash Lite entropy collapse: 6 conditions x 3 scales (n10, n20, n30), 18 runs total",
    )

    print(f"\n{'='*60}")
    print(f"Done! Dataset available at:")
    print(f"https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
