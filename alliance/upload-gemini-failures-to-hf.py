#!/usr/bin/env python3.9
"""Upload MoltBook Entropy Collapse Gemini 3.1 Flash Lite FAILURE runs to HuggingFace.

Includes only model-behaviour failures:
  -garbage   : symbols, gibberish, nonsensical output
  -collapsed : extreme phrase repetition / degenerate loops
  -9of10, -27of30, -28of30 : agent-loss (some agents failed to start)

Does NOT include infrastructure failures:
  -partial, -cancelled, -portcrash
"""

import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from huggingface_hub import HfApi, create_repo

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
HF_TOKEN = os.environ.get("HF_TOKEN")
if not HF_TOKEN:
    try:
        _api = HfApi()
        _api.whoami()
        HF_TOKEN = _api.token
    except Exception:
        print("[ERROR] HF_TOKEN not set and not logged in via huggingface-cli")
        sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRATCH_DIR = Path("/scratch/anangia/moltbook/results")
REPO_ID = "Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite-failures"

SYSTEM_AGENTS = {"civiclens_seed", "civiclens_world", "civiclens_nudger"}

DROP_POSTS = {"url", "my_comment_count"}
DROP_COMMENTS = {"upvotes", "downvotes"}
DROP_AGENTS = {"follower_count", "following_count", "is_claimed", "last_active"}

# Suffix -> (subdirectory, failure type label)
FAILURE_SUFFIX_MAP = {
    "-garbage": ("garbage", "garbage"),
    "-collapsed": ("collapsed", "collapsed"),
    "-9of10": ("agent-loss", "agent-loss"),
    "-27of30": ("agent-loss", "agent-loss"),
    "-28of30": ("agent-loss", "agent-loss"),
}

# Infrastructure failures — explicitly excluded
INFRA_SUFFIXES = ("-partial", "-cancelled", "-portcrash")


# ---------------------------------------------------------------------------
# Discover failure directories
# ---------------------------------------------------------------------------
def discover_failures():
    """Scan results dir for gemini dirs with model-behaviour failure suffixes."""
    failures = []
    for d in sorted(SCRATCH_DIR.iterdir()):
        if not d.is_dir():
            continue
        name = d.name
        if "gemini" not in name.lower():
            continue

        # Skip infrastructure failures
        if any(name.endswith(sfx) for sfx in INFRA_SUFFIXES):
            continue

        # Check for model-behaviour failure suffix
        matched_suffix = None
        for sfx in FAILURE_SUFFIX_MAP:
            if name.endswith(sfx):
                matched_suffix = sfx
                break

        if matched_suffix is None:
            continue  # clean run

        subdir, failure_type = FAILURE_SUFFIX_MAP[matched_suffix]

        # Validate metadata
        meta_path = d / "metadata.json"
        if not meta_path.exists():
            print(f"[WARN] {name} has no metadata.json — including anyway")
            meta = {}
        else:
            meta = json.loads(meta_path.read_text())

        # Extract condition and scale from dirname
        # Pattern: ec-<condition>-n<scale>-run01-...-<suffix>
        m = re.match(r"ec-(.+?)-n(\d+)-run\d+", name)
        if m:
            condition = m.group(1)
            scale = int(m.group(2))
        else:
            condition = "unknown"
            scale = 0

        failures.append({
            "dir": d,
            "name": name,
            "condition": condition,
            "scale": scale,
            "suffix": matched_suffix,
            "subdir": subdir,
            "failure_type": failure_type,
            "meta": meta,
        })

    return failures


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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


def build_readme(failure_rows):
    """Build README for the failures dataset."""

    # Count by type
    by_type = {}
    for row in failure_rows:
        ft = row["failure_type"]
        by_type[ft] = by_type.get(ft, 0) + 1

    total_posts = sum(r["posts"] for r in failure_rows)
    total_comments = sum(r["comments"] for r in failure_rows)

    failure_table = "\n".join(
        f"| `{r['dirname']}` | `{r['condition']}` | n{r['scale']} | {r['failure_type']} | {r['posts']} | {r['comments']} | {r['date']} |"
        for r in failure_rows
    )

    type_counts = "\n".join(
        f"- **{ft}**: {count} run(s)" for ft, count in sorted(by_type.items())
    )

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
  - model-degeneration
  - failure-analysis
  - civiclens
  - moltbook
  - gemini
  - google
pretty_name: "MoltBook Entropy Collapse — Gemini Flash Lite Failure Runs"
size_categories:
  - 1K<n<10K
---

# MoltBook Entropy Collapse — Gemini 3.1 Flash Lite (Failure Runs)

This dataset contains runs from the **Entropy Collapse** experiment series where **Google Gemini 3.1 Flash Lite** exhibited model degeneration or agent loss. These are runs where the model's output quality degraded during the experiment, producing garbage text, collapsing into repetitive phrases, or failing to maintain all agents.

This data is useful for studying **how LLMs degenerate under sustained social interaction pressure** — a phenomenon where models progressively lose output quality when generating content in multi-agent social settings.

## Failure Types

{type_counts}

### Garbage (symbols/gibberish)

Runs where the model began producing nonsensical output: random symbols, Unicode noise, malformed text, or contextually meaningless strings. The model's generation quality catastrophically degraded during the experiment.

### Collapsed (extreme phrase repetition)

Runs where the model entered a degenerate repetition loop — producing the same phrases, sentences, or paragraph structures over and over. Unlike natural entropy collapse (where *topics* converge), collapsed runs show *verbatim* or *near-verbatim* repetition at the text level.

### Agent-loss (startup failures)

Runs where not all agents successfully started or remained active throughout the experiment. Suffixes like `-9of10` (only 9 of 10 agents ran), `-27of30`, `-28of30` indicate how many agents were active.

## All Failure Runs

| Directory | Condition | Scale | Failure Type | Posts | Comments | Date |
|-----------|-----------|-------|-------------|-------|----------|------|
{failure_table}

**Totals**: {total_posts:,} posts, {total_comments:,} comments across {len(failure_rows)} failure runs.

## Companion Dataset

The best clean runs (without degeneration) are available in the main dataset:

- **Clean runs**: [Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite)

Other models in the series:

- **GPT-5**: [Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)
- **Kimi K2.5**: [Ayushnangia/moltbook-entropy-collapse-kimi-k2.5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-kimi-k2.5)
- **GLM-5**: [Ayushnangia/moltbook-entropy-collapse-glm-5](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-glm-5)

## Dataset Structure

Data is organized by failure type:

```
data/
├── garbage/
│   ├── <run-dirname>/
│   │   ├── posts.jsonl
│   │   ├── comments.jsonl
│   │   ├── agents.jsonl
│   │   ├── metadata.json
│   │   ├── database-final.sql
│   │   └── logs/
│   └── ...
├── collapsed/
│   └── ...
└── agent-loss/
    └── ...
```

### Data Schemas

Same schemas as the main dataset — see [Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite) for full field descriptions.

## Citation

```bibtex
@dataset{{moltbook_gemini_failures_2026,
  title={{MoltBook Entropy Collapse — Gemini 3.1 Flash Lite Failure Runs}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Model degeneration data from multi-agent social simulation using Gemini 3.1 Flash Lite}}
}}
```

## License

Apache 2.0
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    api = HfApi(token=HF_TOKEN)
    whoami = api.whoami()
    print(f"Authenticated as: {whoami['name']}")

    failures = discover_failures()
    print(f"\nFound {len(failures)} model-behaviour failure directories:")
    for f in failures:
        print(f"  [{f['failure_type']}] {f['name']}")

    if not failures:
        print("[ERROR] No failure directories found!")
        sys.exit(1)

    # Create dataset repo
    print(f"\nCreating dataset repo: {REPO_ID}")
    try:
        create_repo(REPO_ID, repo_type="dataset", exist_ok=True, token=HF_TOKEN)
        print("  [OK] Repo created/exists")
    except Exception as e:
        print(f"  [ERROR] {e}")
        sys.exit(1)

    staging = Path(tempfile.mkdtemp(prefix="hf_upload_gemini_failures_"))
    print(f"\nStaging cleaned data in {staging}")

    failure_rows = []

    for f in failures:
        exp_dir = f["dir"]
        subdir = f["subdir"]
        dirname = f["name"]

        out_dir = staging / "data" / subdir / dirname
        out_dir.mkdir(parents=True)
        logs_dir = out_dir / "logs"
        logs_dir.mkdir()

        print(f"\n  [{f['failure_type']}] {dirname} -> data/{subdir}/{dirname}")

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
                for af in DROP_AGENTS:
                    obj.pop(af, None)
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

        meta = f["meta"]
        failure_rows.append({
            "dirname": dirname,
            "condition": f["condition"],
            "scale": f["scale"],
            "failure_type": f["failure_type"],
            "posts": n_posts,
            "comments": n_comments,
            "agents": n_real_agents,
            "date": meta.get("export_date", "?")[:10] if meta else "?",
        })

    # Write README
    readme = build_readme(failure_rows)
    (staging / "README.md").write_text(readme)
    print("\n  [OK] README.md generated")

    # Upload
    print(f"\nUploading to {REPO_ID}...")
    api.upload_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        delete_patterns=["data/*", "README.md"],
        commit_message="Gemini 3.1 Flash Lite failure runs: garbage, collapsed, and agent-loss degeneration data",
    )

    print(f"\n{'='*60}")
    print(f"Done! Dataset available at:")
    print(f"https://huggingface.co/datasets/{REPO_ID}")
    print(f"{'='*60}")

    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
