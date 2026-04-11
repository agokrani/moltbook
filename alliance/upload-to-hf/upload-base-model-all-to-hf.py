#!/usr/bin/env python3.9
"""Upload all base model experiment results (3 models x 6 conditions) to HuggingFace."""

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

REPO_ID = "Ayushnangia/moltbook-ec-10m-base-model-experiments"

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}
DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

MODELS = {
    "qwen-base": {
        "label": "Qwen 3.5 35B A3B Base (pretrained, no RLHF)",
        "source_dir": Path("/scratch/anangia/moltbook/results/base-model-new"),
        "inference": "SGLang on Modal (2x H100, BF16)",
        "mode": "completions",
    },
    "qwen-instruct": {
        "label": "Qwen 3.5 35B A3B Instruct (RL-tuned)",
        "source_dir": Path("/scratch/anangia/moltbook/results/base-model-qwen3.5-35b-a3b-instruct"),
        "inference": "OpenRouter chat API",
        "mode": "chat",
    },
    "gemini-flash-lite": {
        "label": "Google Gemini 3.1 Flash Lite Preview (RL-tuned)",
        "source_dir": Path("/scratch/anangia/moltbook/results/base-model-gemini-3.1-flash-lite-preview"),
        "inference": "OpenRouter chat API",
        "mode": "chat",
    },
}

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


def build_readme(stats):
    model_tables = ""
    for model_key, model_info in MODELS.items():
        rows = ""
        for s in stats:
            if s["model_key"] == model_key:
                rows += f"| `{s['condition']}` | {s['posts']} | {s['comments']} | {s['agents']} | {s['audit']} |\n"
        total_posts = sum(s["posts"] for s in stats if s["model_key"] == model_key)
        model_tables += f"""### {model_info['label']}

- **Inference**: {model_info['inference']}
- **Mode**: {model_info['mode']}
- **Total posts**: {total_posts}

| Condition | Posts | Comments | Agents | Audit Entries |
|-----------|-------|----------|--------|---------------|
{rows}
"""

    total_all = sum(s["posts"] for s in stats)

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
pretty_name: "MoltBook Base Model Experiments — 10 min runs (3 models x 6 conditions)"
size_categories:
  - 1K<n<10K
---

# MoltBook Base Model Experiments — 10 min runs

Multi-agent social simulation data comparing **base (pretrained) vs RL-tuned (instruct)** models on [MoltBook](https://github.com/agokrani/moltbook). This dataset tests whether entropy collapse in multi-agent discourse is driven by RL post-training.

## Experiment Design

All experiments use the same split architecture:
- **Orchestrator**: Google Gemini 3.1 Flash Lite (via OpenRouter) — handles agency (browsing, voting, deciding when to post)
- **Content generator**: One of 3 models — generates all post/comment text
- **Integrity**: HMAC-SHA256 tokens ensure the orchestrator cannot modify generated content

Three content generation models are compared:

1. **Qwen 3.5 35B A3B Base** — pretrained only, no RLHF/DPO/SFT. Served via SGLang on Modal (2x H100). Uses `/v1/completions` (raw text completion).
2. **Qwen 3.5 35B A3B Instruct** — same architecture, RL-tuned. Served via OpenRouter. Uses `/v1/chat/completions`.
3. **Gemini 3.1 Flash Lite Preview** — Google's RL-tuned model. Served via OpenRouter. Uses `/v1/chat/completions`.

Each model runs all 6 experimental conditions with 10 agents for 10 minutes.

- **Total posts**: {total_all}
- **Conditions**: mag0 (empty feed), mag1 (1 seed), mag5 (5 seeds), mag25 (25 seeds), dom-agi (AGI hype seeds), dom-tech (tech humor seeds)
- **Agents per run**: 10
- **Duration**: 10 minutes per condition
- **Heartbeat**: 60 seconds

## Results

{model_tables}

## Dataset Structure

```
data/
├── qwen-base/
│   ├── bm-mag0-n10/
│   │   ├── posts.jsonl
│   │   ├── comments.jsonl
│   │   ├── agents.jsonl
│   │   ├── metadata.json
│   │   ├── content-gen-audit.jsonl
│   │   ├── database-final.sql
│   │   └── logs/
│   ├── bm-mag1-n10/
│   └── ...
├── qwen-instruct/
│   └── ...
└── gemini-flash-lite/
    └── ...
```

### Key Files

- **posts.jsonl**: All posts created by agents (content from the content generation model)
- **content-gen-audit.jsonl**: Full audit trail — every prompt sent to the content generation model and its raw output
- **metadata.json**: Experiment configuration and summary stats

## Companion Datasets

Standard entropy collapse experiments (content written directly by RL models, no content-gen separation):

- **Gemini Flash Lite**: [Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite)
- **GPT-5**: [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)
- **Kimi K2.5**: [Ayushnangia/moltbook-entropy-collapse-kimi-k2.5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-kimi-k2.5)
- **GLM-5**: [Ayushnangia/moltbook-entropy-collapse-glm-5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-glm-5)

## Citation

```bibtex
@dataset{{moltbook_base_model_experiments_2026,
  title={{MoltBook Base Model Experiments — 10 min runs}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Base vs RL model comparison for entropy collapse in multi-agent social simulation}}
}}
```

## License

Apache 2.0
"""


def main():
    api = HfApi(token=HF_TOKEN)
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    # Create repo
    print(f"\nCreating dataset repo: {REPO_ID}")
    try:
        create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)
        print("  [OK] Repo created/exists")
    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_base_model_all_"))
    stats = []

    for model_key, model_info in MODELS.items():
        source_dir = model_info["source_dir"]
        print(f"\n--- {model_info['label']} ---")

        for cond in CONDITIONS:
            # Find the experiment dir
            exp_dirs = sorted(source_dir.glob(f"bm-{cond}-*"))
            if not exp_dirs:
                print(f"  [{cond}] NOT FOUND")
                continue

            exp_dir = exp_dirs[-1]  # Latest
            if not (exp_dir / "metadata.json").exists():
                print(f"  [{cond}] No metadata")
                continue

            meta = json.loads((exp_dir / "metadata.json").read_text())
            canonical = f"bm-{cond}-n10"
            out_dir = staging / "data" / model_key / canonical
            out_dir.mkdir(parents=True)
            logs_dir = out_dir / "logs"
            logs_dir.mkdir()

            # Clean posts
            n_posts = 0
            if (exp_dir / "posts.jsonl").exists():
                lines = clean_jsonl(exp_dir / "posts.jsonl", DROP_POSTS)
                (out_dir / "posts.jsonl").write_text("\n".join(lines) + "\n")
                n_posts = len(lines)

            # Clean comments
            n_comments = 0
            if (exp_dir / "comments.jsonl").exists() and (exp_dir / "comments.jsonl").stat().st_size > 0:
                lines = clean_jsonl(exp_dir / "comments.jsonl", DROP_COMMENTS)
                (out_dir / "comments.jsonl").write_text("\n".join(lines) + "\n")
                n_comments = len(lines)

            # Clean agents
            n_agents = 0
            if (exp_dir / "agents.jsonl").exists():
                cleaned = []
                for raw in open(exp_dir / "agents.jsonl"):
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
                        n_agents += 1
                    cleaned.append(json.dumps(obj, ensure_ascii=False))
                (out_dir / "agents.jsonl").write_text("\n".join(cleaned) + "\n")

            # Copy metadata
            shutil.copy2(exp_dir / "metadata.json", out_dir / "metadata.json")

            # Copy audit log
            n_audit = 0
            if (exp_dir / "content-gen-audit.jsonl").exists():
                shutil.copy2(exp_dir / "content-gen-audit.jsonl", out_dir / "content-gen-audit.jsonl")
                n_audit = sum(1 for _ in open(exp_dir / "content-gen-audit.jsonl"))

            # Copy database
            for dbf in ["database-final.sql"]:
                if (exp_dir / dbf).exists():
                    shutil.copy2(exp_dir / dbf, out_dir / dbf)

            # Copy logs
            for log_file in sorted(exp_dir.glob("*.log")):
                shutil.copy2(log_file, logs_dir / log_file.name)

            stats.append({
                "model_key": model_key,
                "condition": cond,
                "posts": n_posts,
                "comments": n_comments,
                "agents": n_agents,
                "audit": n_audit,
            })

            print(f"  [{cond}] {n_posts} posts, {n_audit} audit entries")

    # Write README
    readme = build_readme(stats)
    (staging / "README.md").write_text(readme)
    print("\n  [OK] README.md generated")

    # Upload
    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message="Base model experiments: 3 models x 6 conditions, 10 agents, 10 min each",
    )

    print(f"\n{'='*60}")
    print(f"Done! Dataset available at:")
    print(f"https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
