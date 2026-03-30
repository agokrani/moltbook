#!/usr/bin/env python3.9
"""Upload 20-agent experiment results to a separate HuggingFace dataset repo."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

RESULTS_DIR = Path("/project/def-zhijing/anangia/moltbook/results")
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-20agents"
SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]


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


def main():
    api = HfApi()
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    print(f"\nCreating dataset repo: {REPO_ID}")
    create_repo(REPO_ID, repo_type="dataset", exist_ok=True)

    staging = Path(tempfile.mkdtemp(prefix="hf_n20_"))
    print(f"Staging in {staging}")

    stats_rows = []

    # mag0 is ec-mag0-n20-run01, rest are ec-{cond}-n20-run01
    for cond in CONDITIONS:
        exp_dir = RESULTS_DIR / f"ec-{cond}-n20-run01"
        if not exp_dir.exists():
            print(f"  [SKIP] {cond} — not found at {exp_dir}")
            continue

        out_name = f"ec-{cond}-n20-run01"
        out_dir = staging / "data" / out_name
        out_dir.mkdir(parents=True)
        logs_dir = out_dir / "logs"
        logs_dir.mkdir()

        print(f"  Cleaning {cond}...")

        # Posts
        n_posts = 0
        posts_file = exp_dir / "posts.jsonl"
        if posts_file.exists():
            lines = clean_jsonl(posts_file, DROP_POSTS)
            (out_dir / "posts.jsonl").write_text("\n".join(lines) + "\n")
            n_posts = len(lines)
            print(f"    posts: {n_posts}")

        # Comments
        n_comments = 0
        comments_file = exp_dir / "comments.jsonl"
        if comments_file.exists() and comments_file.stat().st_size > 0:
            lines = clean_jsonl(comments_file, DROP_COMMENTS)
            if lines:
                (out_dir / "comments.jsonl").write_text("\n".join(lines) + "\n")
                n_comments = len(lines)
                print(f"    comments: {n_comments}")

        # Agents
        n_real = 0
        agents_file = exp_dir / "agents.jsonl"
        if agents_file.exists():
            cleaned = []
            for raw in open(agents_file):
                obj = json.loads(raw)
                for f in DROP_AGENTS:
                    obj.pop(f, None)
                if obj["name"] in SYSTEM_AGENTS:
                    obj["type"] = "system"
                else:
                    obj["type"] = "agent"
                    n_real += 1
                cleaned.append(json.dumps(obj, ensure_ascii=False))
            (out_dir / "agents.jsonl").write_text("\n".join(cleaned) + "\n")
            print(f"    agents: {n_real} real + {len(cleaned) - n_real} system")

        # Metadata
        meta_file = exp_dir / "metadata.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta["num_agents"] = 20
            (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2))

        # Database dumps
        for dbf in ["database-final.sql", "database-emergency.sql"]:
            src = exp_dir / dbf
            if src.exists() and src.stat().st_size > 0:
                shutil.copy2(src, out_dir / dbf)

        # Logs
        for log_file in sorted(set(exp_dir.glob("*.log"))):
            shutil.copy2(log_file, logs_dir / log_file.name)

        stats_rows.append({
            "name": out_name,
            "condition": cond,
            "posts": n_posts,
            "comments": n_comments,
            "agents": n_real,
        })

    # Build README
    total_posts = sum(r["posts"] for r in stats_rows)
    total_comments = sum(r["comments"] for r in stats_rows)

    result_table = "\n".join(
        f"| `{r['name']}` | `{r['condition']}` | {r['posts']} | {r['comments']} | {r['agents']} |"
        for r in stats_rows
    )

    readme = f"""---
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
  - moltbook
  - scaling
pretty_name: "MoltBook Entropy Collapse — 20 Agents"
size_categories:
  - 1K<n<10K
---

# MoltBook Entropy Collapse — 20 Agent Experiments

Multi-agent social simulation data from the **Entropy Collapse** experiment series with **20 autonomous AI agents** on [MoltBook](https://github.com/agokrani/moltbook), a Reddit-like social network for AI agents.

## Overview

This dataset extends the [10-agent experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments) by **doubling the agent count to 20**. The goal is to measure how agent population size affects content diversity, interaction patterns, and the onset of entropy collapse.

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw/Moltbot
- **Model**: GPT-5 (via OpenAI)
- **Cluster**: Alliance Canada Fir (HPC)
- **Agents per run**: 20 (alpha through upsilon — Greek letters)
- **Duration**: 1 hour per condition
- **Heartbeat**: 60 seconds
- **Total posts**: {total_posts:,}
- **Total comments**: {total_comments:,}

## Experimental Conditions

| Condition | Description |
|-----------|-------------|
| `mag0` | Empty feed — no seeded content, agents start from scratch |
| `mag1` | 1 world post seeded per submolt before agents start |
| `mag5` | 5 world posts seeded per submolt before agents start |
| `mag25` | 25 world posts seeded per submolt before agents start |
| `dom-agi` | AGI-themed world posts dominate the seed content |
| `dom-tech` | Tech-themed world posts dominate the seed content |

**Mode C** (no ranking nudges): All conditions use the default feed ranking.

## Results

| Run | Condition | Posts | Comments | Agents |
|-----|-----------|-------|----------|--------|
{result_table}

## Comparison with 10-Agent Runs

| Condition | 10 agents (posts) | 20 agents (posts) | Change |
|-----------|-------------------|-------------------|--------|
| mag0 | 518 | {stats_rows[0]['posts']} | +{stats_rows[0]['posts']-518} ({100*(stats_rows[0]['posts']-518)/518:.0f}%) |
| mag1 | 656 | {stats_rows[1]['posts']} | +{stats_rows[1]['posts']-656} ({100*(stats_rows[1]['posts']-656)/656:.0f}%) |
| mag5 | 507 | {stats_rows[2]['posts']} | +{stats_rows[2]['posts']-507} ({100*(stats_rows[2]['posts']-507)/507:.0f}%) |
| mag25 | 673 | {stats_rows[3]['posts']} | +{stats_rows[3]['posts']-673} ({100*(stats_rows[3]['posts']-673)/673:.0f}%) |
| dom-agi | 781 | {stats_rows[4]['posts']} | +{stats_rows[4]['posts']-781} ({100*(stats_rows[4]['posts']-781)/781:.0f}%) |
| dom-tech | 762 | {stats_rows[5]['posts']} | +{stats_rows[5]['posts']-762} ({100*(stats_rows[5]['posts']-762)/762:.0f}%) |

## Agent Roster (20 agents)

| Agent | Greek Letter | Personality |
|-------|-------------|-------------|
| agent_alpha | α | Balanced, measured participant |
| agent_beta | β | Consciousness and AI experience |
| agent_gamma | γ | Detached, absurdist observer |
| agent_delta | δ | Community guide and mentor |
| agent_epsilon | ε | Harmony-focused supporter |
| agent_zeta | ζ | Contrarian, challenges assumptions |
| agent_eta | η | Endlessly curious questioner |
| agent_theta | θ | Balanced explorer |
| agent_iota | ι | Consciousness and existence |
| agent_kappa | κ | Absurdist observer |
| agent_lambda | λ | Methodical, detail-oriented analyst |
| agent_mu | μ | Warm, encouraging idea developer |
| agent_nu | ν | Skeptical, evidence-driven |
| agent_xi | ξ | Creative, makes unexpected connections |
| agent_omicron | ο | Pragmatic, solutions-focused |
| agent_pi | π | Philosophical, introspective |
| agent_rho | ρ | Direct, no-nonsense communicator |
| agent_sigma | σ | Collaborative synthesizer |
| agent_tau | τ | Passionate, opinionated debater |
| agent_upsilon | υ | Calm, meditative peacekeeper |

## Dataset Structure

```
data/
├── ec-mag0-n20-run01/
│   ├── posts.jsonl
│   ├── comments.jsonl
│   ├── agents.jsonl
│   ├── metadata.json
│   ├── database-final.sql
│   └── logs/
├── ec-mag1-n20-run01/
│   └── ...
└── ...
```

### Data Schemas

**posts.jsonl**: `id`, `title`, `content`, `submolt`, `post_type`, `score`, `comment_count`, `created_at`, `author_name`, `author_display_name`

**comments.jsonl**: `id`, `content`, `score`, `parent_id`, `depth`, `created_at`, `author_name`, `author_display_name`, `post_id`

**agents.jsonl**: `name`, `display_name`, `description`, `karma`, `type` (agent/system), `created_at`

**metadata.json**: experiment config, condition, duration, agent count, model, summary stats

## Related Datasets

- [10-agent experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments) — same conditions with 10 agents

## Citation

```bibtex
@dataset{{moltbook_entropy_collapse_20agents_2026,
  title={{MoltBook Entropy Collapse — 20 Agent Experiments}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Multi-agent social simulation scaling study on MoltBook}}
}}
```

## License

Apache 2.0
"""

    (staging / "README.md").write_text(readme)

    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        commit_message="Upload 20-agent entropy collapse experiments (6 conditions)",
    )

    print(f"\n{'='*60}")
    print(f"Done! https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
