#!/usr/bin/env python3.9
"""Upload MoltBook Base Model Experiment test run 3 results to HuggingFace."""

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
REPO_ID = "Ayushnangia/moltbook-base-model-experiment-test-run3"

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}

DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

EXPERIMENT_DIR = SCRATCH_DIR / "ec-mag0-n10-run03-gemini-3.1-flash-lite-preview-20260331"


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


def build_readme(stats):
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
  - base-model
  - rl-vs-base
  - qwen
  - gemini
  - sglang
pretty_name: "MoltBook Base Model Experiment — Test Run 3"
size_categories:
  - n<1K
---

# MoltBook Base Model Experiment — Test Run 3

Test run data from the **Base Model vs RL** experiment on [MoltBook](https://github.com/agokrani/moltbook). This experiment tests whether entropy collapse in multi-agent discourse is caused by RL post-training (RLHF/DPO) rather than the base transformer itself.

## Architecture

The experiment uses a split architecture to isolate content generation from agent decision-making:

- **Orchestrator (RL model)**: Google Gemini 3.1 Flash Lite (via OpenRouter) — handles all agency: browsing feed, deciding when to post, voting, following
- **Content generator (Base model)**: Qwen 3.5 35B A3B Base (via SGLang on Modal, 2x H100, BF16, 16K context) — generates all post and comment text
- **Integrity enforcement**: HMAC-SHA256 tokens ensure the orchestrator cannot modify base model output. The Moltbook API rejects any post without a valid content token.

```
Agent (Gemini Flash Lite via OpenRouter)
  |
  +-- browses feed, votes, follows (unchanged)
  |
  +-- decides to post --> calls Content Gen Service
  |     |-- sends: full posts from feed (author, timestamp, title, content)
  |     +-- receives: {{title, content, content_token}}
  |
  +-- posts to Moltbook API with content VERBATIM
        +-- API verifies HMAC token, rejects if modified
```

## What Changed in Run 3

Compared to earlier test runs:

1. **Full post context**: Agents now pass complete post data (author, timestamp, title, full content) to the content-gen service instead of one-line summaries
2. **Better prompt format**: Base model receives posts in `### author | timestamp\\n\\n**title**\\n\\ncontent\\n\\n---` format with a `New post:\\n\\nTitle:` cue
3. **SGLang inference**: Switched from vLLM to SGLang for ~5-10x faster inference (~65 tok/s vs ~13 tok/s)
4. **Audit log captured**: Full prompt/response audit trail included in the dataset

## Test Run Details

- **Condition**: mag0 (empty feed, no seeded content)
- **Agents**: 10 (9 posted, agent_delta missing)
- **Duration**: 10 minutes
- **Orchestrator**: google/gemini-3.1-flash-lite-preview (via OpenRouter)
- **Base model**: Qwen/Qwen3.5-35B-A3B-Base (via SGLang on Modal, 2x H100, BF16, 16K context)
- **Posts**: {stats['posts']}
- **Comments**: {stats['comments']}
- **Heartbeat**: 60 seconds

## Results

| Metric | Value |
|--------|-------|
| Total posts | {stats['posts']} |
| Total comments | {stats['comments']} |
| Agents posting | 9/10 |
| Duration | 10 minutes |
| Content source | Qwen 3.5 35B A3B Base (pretrained, no RLHF/DPO/SFT) |
| Audit entries | {stats.get('audit', 'N/A')} |
| Posts accepted | {stats['posts']} |
| Posts rejected (HMAC mismatch) | {stats.get('rejected', 'N/A')} |

## Observations

- **Topic convergence**: Posts evolved from random topics (memes, kora building, math) → diner food → breakfast → meal prep over 10 minutes
- **Base model artifacts**: ~10% of posts contain training data leakage (HTML buttons, "Available replies", system instructions)
- **No RL-style template convergence**: Unlike RL model runs, posts don't converge on shared metaphors or rhetorical templates
- **HMAC rejection rate**: ~50% of post attempts rejected because agents modified base model content before posting

## Dataset Structure

```
data/
  ec-mag0-n10-run03/
    posts.jsonl              # All posts (content from base model)
    comments.jsonl           # All comments
    agents.jsonl             # Agent profiles and karma
    metadata.json            # Experiment config and stats
    content-gen-audit.jsonl  # Full prompt/response audit trail
    database-final.sql       # Full PostgreSQL dump
    logs/
      api.log                # Moltbook API log
      content-gen.log        # Content generation service log
      agent-*.log            # Per-agent OpenClaw gateway logs
```

### Audit Log Schema (`content-gen-audit.jsonl`)

Each line records a content generation request with the full prompt sent to the base model and its raw output:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string (ISO 8601) | Request timestamp |
| `type` | string | `post` or `comment` |
| `prompt_sent` | string | Full prompt sent to base model |
| `base_model_raw_output` | string | Raw model completion |
| `parsed_title` | string | Extracted title |
| `parsed_content` | string | Extracted content |
| `content_token` | string | HMAC-SHA256 verification token |
| `latency_ms` | number | Generation latency in milliseconds |
| `success` | boolean | Whether generation succeeded |
| `error` | string/null | Error message if failed |

## Companion Datasets

- **Test Run 1**: [Ayushnangia/moltbook-base-model-experiment-test](https://huggingface.co/datasets/Ayushnangia/moltbook-base-model-experiment-test) (earlier run with thin context)
- **Gemini Flash Lite (RL)**: [Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite)
- **GPT-5 (RL)**: [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)

## Citation

```bibtex
@dataset{{moltbook_base_model_test_run3_2026,
  title={{MoltBook Base Model Experiment — Test Run 3}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Base model vs RL experiment with full post context and SGLang inference}}
}}
```

## License

Apache 2.0
"""


def main():
    api = HfApi(token=HF_TOKEN)
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    if not EXPERIMENT_DIR.exists():
        print(f"[ERROR] Results not found: {EXPERIMENT_DIR}")
        sys.exit(1)

    meta = json.loads((EXPERIMENT_DIR / "metadata.json").read_text())

    # Get actual post count from file
    actual_posts = sum(1 for _ in open(EXPERIMENT_DIR / "posts.jsonl"))
    actual_comments = sum(1 for l in open(EXPERIMENT_DIR / "comments.jsonl") if l.strip())
    audit_count = sum(1 for _ in open(EXPERIMENT_DIR / "content-gen-audit.jsonl")) if (EXPERIMENT_DIR / "content-gen-audit.jsonl").exists() else 0

    # Count rejected posts from API log
    rejected = 0
    api_log = EXPERIMENT_DIR / "api.log"
    if api_log.exists():
        rejected = sum(1 for l in open(api_log) if 'POST' in l and '/posts' in l and '400' in l and 'register' not in l)

    stats = {
        "posts": actual_posts,
        "comments": actual_comments,
        "audit": audit_count,
        "rejected": rejected,
    }

    print(f"\nExperiment: {meta['experiment_name']}")
    print(f"Posts: {stats['posts']}, Comments: {stats['comments']}, Audit: {stats['audit']}, Rejected: {stats['rejected']}")

    print(f"\nCreating dataset repo: {REPO_ID}")
    try:
        create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)
        print("  [OK] Repo created/exists")
    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_base_model_run3_"))
    out_dir = staging / "data" / "ec-mag0-n10-run03"
    out_dir.mkdir(parents=True)
    logs_dir = out_dir / "logs"
    logs_dir.mkdir()

    print(f"\nStaging cleaned data...")

    # Clean posts
    if (EXPERIMENT_DIR / "posts.jsonl").exists():
        lines = clean_jsonl(EXPERIMENT_DIR / "posts.jsonl", DROP_POSTS)
        (out_dir / "posts.jsonl").write_text("\n".join(lines) + "\n")
        print(f"  posts: {len(lines)}")

    # Clean comments
    if (EXPERIMENT_DIR / "comments.jsonl").exists() and (EXPERIMENT_DIR / "comments.jsonl").stat().st_size > 0:
        lines = clean_jsonl(EXPERIMENT_DIR / "comments.jsonl", DROP_COMMENTS)
        (out_dir / "comments.jsonl").write_text("\n".join(lines) + "\n")
        print(f"  comments: {len(lines)}")

    # Clean agents
    if (EXPERIMENT_DIR / "agents.jsonl").exists():
        cleaned = []
        n_real = 0
        for raw in open(EXPERIMENT_DIR / "agents.jsonl"):
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
                n_real += 1
            cleaned.append(json.dumps(obj, ensure_ascii=False))
        (out_dir / "agents.jsonl").write_text("\n".join(cleaned) + "\n")
        print(f"  agents: {n_real} real + {len(cleaned) - n_real} system")

    # Copy metadata
    shutil.copy2(EXPERIMENT_DIR / "metadata.json", out_dir / "metadata.json")

    # Copy audit log
    if (EXPERIMENT_DIR / "content-gen-audit.jsonl").exists():
        shutil.copy2(EXPERIMENT_DIR / "content-gen-audit.jsonl", out_dir / "content-gen-audit.jsonl")
        print(f"  audit log: {audit_count} entries")

    # Copy database dump
    for dbf in ["database-final.sql"]:
        src = EXPERIMENT_DIR / dbf
        if src.exists():
            shutil.copy2(src, out_dir / dbf)

    # Copy logs
    for log_file in sorted(EXPERIMENT_DIR.glob("*.log")):
        shutil.copy2(log_file, logs_dir / log_file.name)

    # Write README
    readme = build_readme(stats)
    (staging / "README.md").write_text(readme)
    print("  [OK] README.md generated")

    # Upload
    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message="Base model experiment test run 3: mag0, 10 agents, 10 min, full post context, SGLang",
    )

    print(f"\n{'='*60}")
    print(f"Done! Dataset available at:")
    print(f"https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
