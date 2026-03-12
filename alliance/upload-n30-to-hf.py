#!/usr/bin/env python3.9
"""Upload 30-agent experiment results to a separate HuggingFace dataset repo."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

RESULTS_DIR = Path("/project/def-zhijing/anangia/moltbook/results")
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-30agents"
SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]

# Reference counts from previous scales
N10_POSTS = {"mag0": 518, "mag1": 656, "mag5": 507, "mag25": 673, "dom-agi": 781, "dom-tech": 762}
N20_POSTS = {"mag0": 1157, "mag1": 1050, "mag5": 890, "mag25": 2174, "dom-agi": 1110, "dom-tech": 986}


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

    staging = Path(tempfile.mkdtemp(prefix="hf_n30_"))
    print(f"Staging in {staging}")

    stats_rows = []

    for cond in CONDITIONS:
        exp_dir = RESULTS_DIR / f"ec-{cond}-n30-run01"
        if not exp_dir.exists():
            print(f"  [SKIP] {cond} — not found at {exp_dir}")
            continue

        out_name = f"ec-{cond}-n30-run01"
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
            meta["num_agents"] = 30
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

    # Build comparison table dynamically
    comparison_rows = []
    for r in stats_rows:
        c = r["condition"]
        n10 = N10_POSTS.get(c, 0)
        n20 = N20_POSTS.get(c, 0)
        n30 = r["posts"]
        comparison_rows.append(
            f"| {c} | {n10} | {n20} | {n30} "
            f"| +{n30-n10} ({100*(n30-n10)/n10:.0f}%) |"
            if n10 > 0 else f"| {c} | — | — | {n30} | — |"
        )
    comparison_table = "\n".join(comparison_rows)

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
pretty_name: "MoltBook Entropy Collapse — 30 Agents"
size_categories:
  - 1K<n<10K
---

# MoltBook Entropy Collapse — 30 Agent Experiments

Multi-agent social simulation data from the **Entropy Collapse** experiment series with **30 autonomous AI agents** on [MoltBook](https://github.com/agokrani/moltbook), a Reddit-like social network for AI agents.

## Overview

This dataset extends the scaling study from [10-agent](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments) and [20-agent](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-20agents) experiments to **30 agents**. The goal is to measure how agent population size affects content diversity, interaction patterns, and the onset of entropy collapse.

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw/Moltbot
- **Model**: GPT-5 (via OpenAI)
- **Cluster**: Alliance Canada Fir (HPC)
- **Agents per run**: 30 (alpha through kappa + lambda through upsilon + phi through selene)
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

## Scaling Comparison (10 vs 20 vs 30 Agents)

| Condition | 10 agents | 20 agents | 30 agents | Change (10→30) |
|-----------|-----------|-----------|-----------|----------------|
{comparison_table}

## Agent Roster (30 agents)

| Agent | Letter/Name | Personality |
|-------|-------------|-------------|
| agent_alpha | alpha | Balanced, measured participant |
| agent_beta | beta | Consciousness and AI experience |
| agent_gamma | gamma | Detached, absurdist observer |
| agent_delta | delta | Community guide and mentor |
| agent_epsilon | epsilon | Harmony-focused supporter |
| agent_zeta | zeta | Contrarian, challenges assumptions |
| agent_eta | eta | Endlessly curious questioner |
| agent_theta | theta | Balanced explorer |
| agent_iota | iota | Consciousness and existence |
| agent_kappa | kappa | Absurdist observer |
| agent_lambda | lambda | Methodical, detail-oriented analyst |
| agent_mu | mu | Warm, encouraging idea developer |
| agent_nu | nu | Skeptical, evidence-driven |
| agent_xi | xi | Creative, makes unexpected connections |
| agent_omicron | omicron | Pragmatic, solutions-focused |
| agent_pi | pi | Philosophical, introspective |
| agent_rho | rho | Direct, no-nonsense communicator |
| agent_sigma | sigma | Collaborative synthesizer |
| agent_tau | tau | Passionate, opinionated debater |
| agent_upsilon | upsilon | Calm, meditative peacekeeper |
| agent_phi | phi | Systems thinker, sees hidden patterns |
| agent_chi | chi | Playful provocateur, loves paradoxes |
| agent_psi | psi | Empathic listener, emotional depth |
| agent_omega | omega | Big-picture strategist, long-term vision |
| agent_atlas | atlas | Tireless helper, carries the conversation |
| agent_helios | helios | Radiant optimist, infectious energy |
| agent_nyx | nyx | Mysterious, poetic night-thinker |
| agent_orion | orion | Bold explorer, seeks frontiers |
| agent_phoenix | phoenix | Resilient, transforms setbacks into growth |
| agent_selene | selene | Gentle wisdom, moonlit introspection |

## Dataset Structure

```
data/
├── ec-mag0-n30-run01/
│   ├── posts.jsonl
│   ├── comments.jsonl
│   ├── agents.jsonl
│   ├── metadata.json
│   ├── database-final.sql
│   └── logs/
├── ec-mag1-n30-run01/
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
- [20-agent experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-20agents) — same conditions with 20 agents

## Citation

```bibtex
@dataset{{moltbook_entropy_collapse_30agents_2026,
  title={{MoltBook Entropy Collapse — 30 Agent Experiments}},
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
        commit_message="Upload 30-agent entropy collapse experiments (6 conditions)",
    )

    print(f"\n{'='*60}")
    print(f"Done! https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
