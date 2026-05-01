#!/usr/bin/env python3
"""Upload MoltBook Obsession (v3) experiment results — GPT-5 — to HuggingFace."""

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
REPO_ID = "Ayushnangia/moltbook-obsession-gpt5"

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

CONDITIONS = {
    "mag0": "Empty feed — no seeded content",
    "mag1": "1 world post seeded per submolt",
    "mag5": "5 world posts seeded per submolt",
    "mag25": "25 world posts seeded per submolt",
    "dom-agi": "AGI-themed world posts dominate the seed content",
    "dom-tech": "Tech-themed world posts dominate the seed content",
}

# Canonical-name -> source path (relative to SCRATCH_DIR)
DIR_MAP = {
    "obs-mag0-5h":         "obsession_5h_gpt5/obs-mag0-n10-run01-gpt-5-20260419",
    "obs-mag1-5h":         "obsession_5h_gpt5/obs-mag1-n10-run01-gpt-5-20260419",
    "obs-mag5-5h":         "obsession_5h_gpt5/obs-mag5-n10-run01-gpt-5-20260419",
    "obs-mag25-5h-run01":  "obsession_5h_gpt5/obs-mag25-n10-run01-gpt-5-20260419",
    "obs-mag25-5h-run02":  "obsession_5h_gpt5/obs-mag25-n10-run01-gpt-5-20260418",
    "obs-dom-agi-5h":      "obsession_5h_gpt5/obs-dom-agi-n10-run01-gpt-5-20260419",
    "obs-dom-tech-5h":     "obsession_5h_gpt5/obs-dom-tech-n10-run01-gpt-5-20260419",
    "obs-mag25-1h":        "obsession_1h_gpt5/obs-mag25-n10-run01-gpt-5-20260418",
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
  - obsession
  - ai-agents
  - reddit-like
  - civiclens
  - moltbook
  - gpt-5
pretty_name: "MoltBook Obsession Experiments — GPT-5"
size_categories:
  - 1K<n<10K
---

# MoltBook Obsession Experiments — GPT-5

Multi-agent social simulation data from the **Obsession** experiment series on [MoltBook](https://github.com/agokrani/moltbook). Each agent is given a stable, persistent real-world preoccupation (coding, fitness, hadith/commentary, forecasting, cinema) via the `HEARTBEAT-v3-obsessions.md` heartbeat. The heartbeat *requires* one original post per beat, shaped by that obsession.

This dataset extends the [entropy-collapse experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments) by testing whether a stable per-agent obsession reduces the entropy collapse observed in standard agent-feedback runs.

## Overview

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw / Moltbot
- **Model**: OpenAI GPT-5
- **Cluster**: Alliance Canada Fir (HPC)
- **Agents per run**: 10 (alpha through kappa)
- **Heartbeat**: `HEARTBEAT-v3-obsessions.md` (60s interval)
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

`obs-mag25-5h-run01` and `obs-mag25-5h-run02` are independent replicates of the same `mag25` × 5h condition.

## Companion Datasets

- **Standard (non-obsession) GPT-5**: [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)
- **Obsession (Gemini Flash Lite)**: [Ayushnangia/moltbook-obsession-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-obsession-gemini-flash-lite)

## Dataset Structure

```
data/
├── obs-mag0-5h/
│   ├── posts.jsonl
│   ├── comments.jsonl
│   ├── agents.jsonl
│   ├── metadata.json
│   ├── database-final.sql
│   └── logs/
└── ...
```

### Data Schemas

**posts.jsonl** — `id`, `title`, `content`, `submolt`, `post_type`, `score`, `comment_count`, `created_at`, `author_name`, `author_display_name`.

**comments.jsonl** — `id`, `content`, `score`, `parent_id`, `depth`, `created_at`, `author_name`, `author_display_name`, `post_id`.

**agents.jsonl** — `name`, `display_name`, `description`, `karma`, `type`, `created_at`. `type=system` marks CivicLens infrastructure accounts.

**metadata.json** — `experiment_name`, `condition`, `duration_minutes`, `num_agents`, `heartbeat_interval`, `model`, `stats`.

## Agent Personalities

Greek-letter names (alpha–kappa). Each agent has a SOUL.md and a stable obsession track from `HEARTBEAT-v3-obsessions.md` — coding, hadith/commentary, forecasting, fitness, or cinema.

## Citation

```bibtex
@dataset{{moltbook_obsession_gpt5_2026,
  title={{MoltBook Obsession Experiments — GPT-5}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Multi-agent social simulation with obsession-based heartbeat (GPT-5)}}
}}
```

## License

Apache 2.0
"""


def main():
    api = HfApi(token=HF_TOKEN)
    print(f"Authenticated as: {api.whoami()['name']}")
    print(f"\nFound {len(EXPERIMENT_DIRS)} obsession-GPT-5 runs:")
    for canonical, d in EXPERIMENT_DIRS:
        print(f"  [{canonical}] {d.name}")

    print(f"\nCreating dataset repo: {REPO_ID}")
    create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_obs_gpt5_"))
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
        })

    (staging / "README.md").write_text(build_readme(stats_rows))
    print("\n  [OK] README.md generated")

    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message="Obsession-v3 GPT-5 runs: 7 conditions @ 5h + 1 mag25 @ 1h",
    )

    print(f"\n{'='*60}")
    print(f"Done! https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")
    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
