#!/usr/bin/env python3.9
"""Upload cleaned MoltBook Entropy Collapse Qwen 3.5 35B-A3B Base experiment results to HuggingFace."""

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

# ============================================================================
# CONFIG
# ============================================================================

SCRATCH_DIR = Path("/home/anangia/scratch/moltbook/results")
PARENT_DIR = SCRATCH_DIR / "base-model-qwen3.5-35b-a3b-base"
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-qwen-35b-base"

CONTENT_MODEL = "Qwen/Qwen3.5-35B-A3B-Base"
ORCHESTRATOR_MODEL = "google/gemini-3.1-flash-lite-preview"
MODEL_DISPLAY = "Qwen 3.5 35B-A3B Base"
MODEL_HF_TAGS = ["qwen", "qwen-3.5", "base-model", "moe"]

CONDITIONS = {
    "mag0": "Empty feed — no seeded content, agents start from scratch",
    "mag1": "1 world post seeded per submolt before agents start",
    "mag5": "5 world posts seeded per submolt before agents start",
    "mag25": "25 world posts seeded per submolt before agents start",
    "dom-agi": "AGI-themed world posts dominate the seed content",
    "dom-tech": "Tech-themed world posts dominate the seed content",
}

CANONICAL_NAME = {cond: f"ec-{cond}-n10-run01" for cond in CONDITIONS}

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}

DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

SKIP_SUBDIR_MARKERS = ("-ignore", "contaminated", "cancelled", "garbage", "partial")


# ============================================================================
# AUTH
# ============================================================================

HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    try:
        _api = HfApi()
        _api.whoami()
        HF_TOKEN = _api.token
    except Exception:
        print("[ERROR] HF_TOKEN not set and not logged in via huggingface-cli")
        sys.exit(1)


# ============================================================================
# HELPERS
# ============================================================================

def clean_jsonl(inpath: Path, drop_fields: set) -> list[str]:
    lines = []
    with open(inpath) as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            for field in drop_fields:
                obj.pop(field, None)
            lines.append(json.dumps(obj, ensure_ascii=False))
    return lines


def rewrite_metadata(meta: dict) -> dict:
    cleaned = dict(meta)
    cleaned.pop("model", None)
    cleaned["content_model"] = CONTENT_MODEL
    cleaned["orchestrator_model"] = ORCHESTRATOR_MODEL
    return cleaned


def resolve_condition_dirs() -> dict[str, Path]:
    found = {}
    for cond in CONDITIONS:
        matches = sorted(PARENT_DIR.glob(f"bm-{cond}-n10-run01-*"))
        matches = [m for m in matches if not any(k in m.name for k in SKIP_SUBDIR_MARKERS)]
        if not matches:
            print(f"[ERROR] No run dir for condition '{cond}' under {PARENT_DIR}")
            sys.exit(1)
        if len(matches) > 1:
            print(f"[WARN] Multiple matches for '{cond}', using newest: {matches[-1].name}")
        found[cond] = matches[-1]
    return found


# ============================================================================
# README
# ============================================================================

def build_readme(stats_rows: list[dict]) -> str:
    condition_table = "\n".join(
        f"| `{c}` | {desc} |" for c, desc in CONDITIONS.items()
    )
    result_table = "\n".join(
        f"| `{r['name']}` | `{r['condition']}` | {r['posts']} | {r['comments']} | {r['agents']} | {r['date']} |"
        for r in stats_rows
    )
    total_posts = sum(r["posts"] for r in stats_rows)
    total_comments = sum(r["comments"] for r in stats_rows)

    tags = [
        "multi-agent", "social-simulation", "entropy-collapse",
        "ai-agents", "reddit-like", "civiclens", "moltbook",
    ] + MODEL_HF_TAGS
    tags_yaml = "\n".join(f"  - {t}" for t in tags)

    return f"""---
license: apache-2.0
task_categories:
  - text-generation
language:
  - en
tags:
{tags_yaml}
pretty_name: "MoltBook Entropy Collapse Experiments — {MODEL_DISPLAY}"
size_categories:
  - 1K<n<10K
---

# MoltBook Entropy Collapse Experiments — {MODEL_DISPLAY}

Multi-agent social simulation data from the **Entropy Collapse** experiment series run on [MoltBook](https://github.com/agokrani/moltbook), a Reddit-like social network for AI agents. This dataset uses **{MODEL_DISPLAY}** as the content-generation model, with Gemini 3.1 Flash Lite Preview orchestrating agent reasoning.

## Two-model architecture

These are **base-model experiments** designed to test whether "entropy collapse" (conversational repetition in multi-agent discourse) is driven by RL post-training. Two distinct LLMs are in play:

- **Orchestrator model** (`{ORCHESTRATOR_MODEL}`): runs inside each agent container, reads the feed, decides what action to take (post / comment / vote).
- **Content model** (`{CONTENT_MODEL}`): generates the actual post title + body and comment text. The agent hands off to a separate `content-gen-service` for every generation call.

Every post and comment is HMAC-signed with a `content_token` by `content-gen-service` and verified at API ingestion (`moltbook-api/src/routes/posts.js`). An audit log of every generation (`content-gen-audit.jsonl`) is included in each run dir as cryptographic provenance that the content came from the content model, not the orchestrator.

Because `{MODEL_DISPLAY}` is a **base (non-instruct) model**, it has not undergone RL post-training. These runs form the control condition for the "is entropy collapse caused by RL post-training?" hypothesis — comparable to the GPT-5 / Kimi / GLM-5 / Gemini runs which all used production-RL-trained models.

## Overview

- **Platform**: MoltBook (Reddit-like social network for AI agents)
- **Agent framework**: OpenClaw/Moltbot
- **Content model**: `{CONTENT_MODEL}`
- **Orchestrator model**: `{ORCHESTRATOR_MODEL}`
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

## Companion Datasets

Same experimental setup, different models:

- **GPT-5 Nano** (RL-trained): [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)
- **Kimi K2.5** (RL-trained): [Ayushnangia/moltbook-entropy-collapse-kimi-k2.5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-kimi-k2.5)
- **GLM-5** (RL-trained): [Ayushnangia/moltbook-entropy-collapse-glm-5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-glm-5)
- **Gemini Flash Lite** (RL-trained): [Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite)
- **OLMo 3 32B Base** (base, no RL): [Ayushnangia/moltbook-entropy-collapse-olmo-3-base](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-olmo-3-base)
- **OLMo 3.1 32B Instruct** (SFT, no RL): [Ayushnangia/moltbook-entropy-collapse-olmo-3-instruct](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-olmo-3-instruct)

## Dataset Structure

```
data/
├── ec-mag0-n10-run01/
│   ├── posts.jsonl                # All posts created during the experiment
│   ├── comments.jsonl             # All comments
│   ├── agents.jsonl               # Agent profiles and final karma scores
│   ├── metadata.json              # Experiment config + content_model/orchestrator_model
│   ├── content-gen-audit.jsonl    # HMAC-signed provenance log of every content-gen call
│   ├── database-final.sql         # Full PostgreSQL dump at experiment end
│   └── logs/
│       ├── api.log                # MoltBook API server log
│       ├── postgres.log           # PostgreSQL log
│       ├── redis.log              # Redis log
│       ├── content-gen.log        # content-gen-service log
│       └── agent-*.log            # Per-agent OpenClaw gateway logs
├── ec-mag1-n10-run01/
│   └── ...
└── ...
```

### Data Schemas

See the OLMo 3 Base companion dataset for field-level schemas. All MoltBook entropy-collapse datasets share the same JSONL layout.

## Agent Personalities

Each of the 10 agents has a unique personality defined by a SOUL.md file. Agent names follow Greek letters: alpha, beta, gamma, delta, epsilon, zeta, eta, theta, iota, kappa.

System accounts (`civiclens_seed`, `civiclens_world`, `civiclens_nudger`) are infrastructure agents used for seeding content and applying experimental treatments. They are included in `agents.jsonl` with `"type": "system"` for completeness but did not participate as social agents.

## Citation

```bibtex
@dataset{{moltbook_entropy_collapse_qwen35b_base_2026,
  title={{MoltBook Entropy Collapse Experiments — {MODEL_DISPLAY}}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Multi-agent social simulation on MoltBook platform using {CONTENT_MODEL} as the content-generation model}}
}}
```

## License

Apache 2.0
"""


# ============================================================================
# MAIN
# ============================================================================

def main():
    api = HfApi(token=HF_TOKEN)
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")
    print(f"Source:      {PARENT_DIR}")
    print(f"Target repo: {REPO_ID}")
    print(f"Content model: {CONTENT_MODEL}")
    print()

    cond_dirs = resolve_condition_dirs()
    print(f"Found {len(cond_dirs)} condition dirs:")
    for cond, d in cond_dirs.items():
        print(f"  [{cond:>8}] {d.name}")
    print()

    print(f"Creating/verifying repo: {REPO_ID}")
    try:
        create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)
        print("  [OK]")
    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)
    print()

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_qwen_base_"))
    print(f"Staging dir: {staging}")
    print()

    stats_rows = []
    total_condition = len(cond_dirs)

    for idx, (cond, src_dir) in enumerate(cond_dirs.items(), start=1):
        canonical = CANONICAL_NAME[cond]
        out_dir = staging / "data" / canonical
        out_dir.mkdir(parents=True)
        logs_dir = out_dir / "logs"
        logs_dir.mkdir()

        print(f"[{idx}/{total_condition}] Cleaning {cond} ({src_dir.name} -> {canonical})")

        posts_file = src_dir / "posts.jsonl"
        n_posts = 0
        if posts_file.exists():
            lines = clean_jsonl(posts_file, DROP_POSTS)
            (out_dir / "posts.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""))
            n_posts = len(lines)
        print(f"    posts:    {n_posts}")

        comments_file = src_dir / "comments.jsonl"
        n_comments = 0
        if comments_file.exists() and comments_file.stat().st_size > 0:
            lines = clean_jsonl(comments_file, DROP_COMMENTS)
            (out_dir / "comments.jsonl").write_text("\n".join(lines) + ("\n" if lines else ""))
            n_comments = len(lines)
        print(f"    comments: {n_comments}")

        agents_file = src_dir / "agents.jsonl"
        n_real = 0
        n_sys = 0
        if agents_file.exists():
            cleaned = []
            with open(agents_file) as f:
                for raw in f:
                    raw = raw.strip()
                    if not raw:
                        continue
                    obj = json.loads(raw)
                    for field in DROP_AGENTS:
                        obj.pop(field, None)
                    if obj.get("name") in SYSTEM_AGENTS:
                        obj["type"] = "system"
                        n_sys += 1
                    else:
                        obj["type"] = "agent"
                        n_real += 1
                    cleaned.append(json.dumps(obj, ensure_ascii=False))
            (out_dir / "agents.jsonl").write_text("\n".join(cleaned) + ("\n" if cleaned else ""))
        print(f"    agents:   {n_real} real + {n_sys} system")

        meta_file = src_dir / "metadata.json"
        meta = {}
        if meta_file.exists():
            meta = json.loads(meta_file.read_text())
            meta = rewrite_metadata(meta)
            (out_dir / "metadata.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

        audit_file = src_dir / "content-gen-audit.jsonl"
        if audit_file.exists() and audit_file.stat().st_size > 0:
            shutil.copy2(audit_file, out_dir / "content-gen-audit.jsonl")
            print(f"    audit:    {audit_file.stat().st_size // 1024} KB")

        for dbf in ["database-final.sql", "database-emergency.sql"]:
            src = src_dir / dbf
            if src.exists() and src.stat().st_size > 0:
                shutil.copy2(src, out_dir / dbf)

        log_count = 0
        for log_file in sorted(src_dir.glob("*.log")):
            shutil.copy2(log_file, logs_dir / log_file.name)
            log_count += 1
        print(f"    logs:     {log_count} files")

        stats_rows.append({
            "name": canonical,
            "condition": meta.get("condition", cond),
            "posts": n_posts,
            "comments": n_comments,
            "agents": n_real,
            "date": (meta.get("export_date", "?") or "?")[:10],
        })

    print()
    readme = build_readme(stats_rows)
    (staging / "README.md").write_text(readme)
    print(f"[OK] README.md generated ({len(readme)} chars)")
    print()

    total_size_mb = sum(
        f.stat().st_size for f in staging.rglob("*") if f.is_file()
    ) / (1024 * 1024)
    print(f"Uploading {total_size_mb:.1f} MB to {REPO_ID}...")
    print("(huggingface_hub will display per-file progress below)")
    print()
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message=f"{MODEL_DISPLAY} entropy collapse experiments: 6 conditions, 10 agents, 1h each",
    )

    print()
    print("=" * 60)
    print(f"UPLOAD COMPLETE — {MODEL_DISPLAY}")
    print("=" * 60)
    print(f"Dataset: https://huggingface.co/datasets/{REPO_ID}")
    print()
    print(f"{'Condition':<10} {'Posts':>6} {'Comments':>9} {'Agents':>7}")
    print("-" * 40)
    for r in stats_rows:
        print(f"{r['condition']:<10} {r['posts']:>6} {r['comments']:>9} {r['agents']:>7}")
    print("-" * 40)
    total_p = sum(r["posts"] for r in stats_rows)
    total_c = sum(r["comments"] for r in stats_rows)
    print(f"{'TOTAL':<10} {total_p:>6} {total_c:>9}")
    print()

    shutil.rmtree(staging)
    print(f"Removed staging dir: {staging}")


if __name__ == "__main__":
    main()
