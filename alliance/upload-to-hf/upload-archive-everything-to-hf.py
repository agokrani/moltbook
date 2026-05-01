#!/usr/bin/env python3
"""
One-shot full archive of MoltBook / CivicLens cluster data to a single private
HuggingFace dataset repo. Captures everything before $SCRATCH purge.

Sources packed into the repo:
  archive/project-results/      <- /project/def-zhijing/anangia/moltbook/results/
  archive/scratch-results/      <- /scratch/anangia/moltbook/results/  (only dirs not in project)
  archive/scratch-analysis/     <- /scratch/anangia/moltbook/analysis/
  archive/home-analysis/        <- /home/anangia/moltbook/analysis/
  archive/home-findings/        <- /home/anangia/moltbook/findings/
  archive/home-dataset/         <- /home/anangia/moltbook/dataset/
  README.md                     <- generated manifest

Nothing is filtered or cleaned. Logs, garbage/cancelled/partial dirs,
content-gen audits, .sql dumps — everything goes.
"""

from __future__ import annotations

import datetime
import json
import os
import sys
from pathlib import Path

# Enable Rust-based fast transfer BEFORE importing hf_hub
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("HF_XET_HIGH_PERFORMANCE", "1")

from huggingface_hub import HfApi, create_repo  # noqa: E402

# ============================================================================
# CONFIG
# ============================================================================

REPO_ID = "Ayushnangia/moltbook-archive-2026"
REPO_PRIVATE = True

PROJECT_RESULTS = Path("/project/def-zhijing/anangia/moltbook/results")
SCRATCH_RESULTS = Path("/scratch/anangia/moltbook/results")
SCRATCH_ANALYSIS = Path("/scratch/anangia/moltbook/analysis")
HOME_MOLTBOOK = Path("/home/anangia/moltbook")
HOME_ANALYSIS = HOME_MOLTBOOK / "analysis"
HOME_FINDINGS = HOME_MOLTBOOK / "findings"
HOME_DATASET = HOME_MOLTBOOK / "dataset"

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
# INVENTORY
# ============================================================================

def dir_stats(path: Path) -> dict:
    if not path.exists():
        return {"exists": False, "n_files": 0, "size_bytes": 0}
    n_files = 0
    size = 0
    for p in path.rglob("*"):
        if p.is_file():
            n_files += 1
            try:
                size += p.stat().st_size
            except OSError:
                pass
    return {"exists": True, "n_files": n_files, "size_bytes": size}


def fmt_bytes(b: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def build_inventory():
    inv = {}

    # Project results — every subdir
    project_dirs = sorted(d for d in PROJECT_RESULTS.iterdir() if d.is_dir())
    inv["project_results"] = {
        "source": str(PROJECT_RESULTS),
        "subdirs": [d.name for d in project_dirs],
        **dir_stats(PROJECT_RESULTS),
    }

    # Scratch results that aren't in project
    project_names = {d.name for d in project_dirs}
    scratch_only = []
    if SCRATCH_RESULTS.exists():
        for d in sorted(SCRATCH_RESULTS.iterdir()):
            if d.is_dir() and d.name not in project_names:
                scratch_only.append(d.name)
    inv["scratch_only"] = {
        "source": str(SCRATCH_RESULTS),
        "subdirs": scratch_only,
    }

    inv["scratch_analysis"] = {"source": str(SCRATCH_ANALYSIS), **dir_stats(SCRATCH_ANALYSIS)}
    inv["home_analysis"]    = {"source": str(HOME_ANALYSIS),    **dir_stats(HOME_ANALYSIS)}
    inv["home_findings"]    = {"source": str(HOME_FINDINGS),    **dir_stats(HOME_FINDINGS)}
    inv["home_dataset"]     = {"source": str(HOME_DATASET),     **dir_stats(HOME_DATASET)}

    return inv


# ============================================================================
# README
# ============================================================================

def build_readme(inv: dict) -> str:
    today = datetime.date.today().isoformat()

    def section(title, key, prefix):
        s = inv[key]
        if not s.get("subdirs"):
            return ""
        lines = [f"\n### `archive/{prefix}/`  — `{s['source']}`\n"]
        lines.append(f"Subdirectories ({len(s['subdirs'])}):\n")
        for sub in s["subdirs"]:
            lines.append(f"- `{sub}`")
        return "\n".join(lines) + "\n"

    project_section = section("Project /results", "project_results", "project-results")
    scratch_section = section("Scratch-only /results", "scratch_only", "scratch-results")

    # Sizes
    pr = inv["project_results"]
    home_a = inv["home_analysis"]
    home_f = inv["home_findings"]

    return f"""---
license: mit
task_categories:
  - text-generation
language:
  - en
tags:
  - multi-agent
  - social-simulation
  - entropy-collapse
  - moltbook
  - civiclens
  - archive
  - cluster-archive
pretty_name: "MoltBook / CivicLens Cluster Archive (2026)"
---

# MoltBook / CivicLens Cluster Archive — {today}

**Private one-shot archive** of all MoltBook / CivicLens experiment data,
analysis artifacts, and supporting files generated on Alliance Canada Fir
(`def-zhijing` allocation) before the `$SCRATCH` 60-day purge.

This repo is the **single source of truth** for every cluster experiment run by
@Ayushnangia — including draft / cancelled / partial / "garbage" replicates,
all log files, all database dumps, and all local analysis outputs.

The cleaned, per-model curated datasets live in separate public repos
(`Ayushnangia/moltbook-entropy-collapse-*`, `…-obsession-*`, `…-frontier-mixed-*`,
etc.) — those are the entry points for downstream users. **This repo is the
unfiltered backup**: everything that the curated repos dropped or never indexed
is here too.

## Repo Layout

```
archive/
├── project-results/      Mirror of /project/def-zhijing/anangia/moltbook/results/  ({len(inv['project_results']['subdirs'])} dirs, {fmt_bytes(pr['size_bytes'])})
├── scratch-results/      Dirs only on /scratch (not duplicated in project)         ({len(inv['scratch_only']['subdirs'])} dirs)
├── scratch-analysis/     /scratch/anangia/moltbook/analysis/                       ({fmt_bytes(inv['scratch_analysis'].get('size_bytes', 0))})
├── home-analysis/        ~/moltbook/analysis/  — Shannon, temporal, semantic,      ({fmt_bytes(home_a.get('size_bytes', 0))})
│                          topical, gzip JSONs and plot PNGs
├── home-findings/        ~/moltbook/findings/  — markdown summaries, scaling,     ({fmt_bytes(home_f.get('size_bytes', 0))})
│                          multiscale, gzip findings, conspiracy-dataset, etc.
└── home-dataset/         ~/moltbook/dataset/  — supporting data
```

## Each Experiment Run Directory

Every `<run>/` under `project-results/` and `scratch-results/` contains the
standard MoltBook export:

| File | Description |
|------|-------------|
| `posts.jsonl` | All posts (seed + agent-generated) |
| `comments.jsonl` | All comments |
| `agents.jsonl` | Agent profiles + final karma |
| `activity.jsonl` | Timestamped activity events (CivicLens observation layer) |
| `metadata.json` | Experiment config + summary stats |
| `database-final.sql` (or `database-emergency.sql`) | Full Postgres dump |
| `agent-<name>.log` | Per-agent OpenClaw gateway log |
| `api.log` / `postgres.log` / `redis.log` | Service logs |
| `checkpoints/` | Per-30-min checkpoint snapshots (when present) |
| `content-gen-audit.jsonl` | (Base-model runs only) content-gen audit trail |

## Curated Public Companion Repos

For a clean, README-documented entry point, use these instead:

| Repo | Coverage |
|---|---|
| `Ayushnangia/moltbook-entropy-collapse-experiments` | GPT-5 baseline, n10/n20/n30 |
| `Ayushnangia/moltbook-entropy-collapse-kimi-k2.5` | Kimi K2.5 baseline |
| `Ayushnangia/moltbook-entropy-collapse-glm-5` | GLM-5 baseline |
| `Ayushnangia/moltbook-entropy-collapse-gemini-flash-lite` | Gemini Flash Lite (combined) |
| `Ayushnangia/moltbook-entropy-collapse-olmo-3-base` / `-instruct` | OLMo-3 32B base/instruct |
| `Ayushnangia/moltbook-entropy-collapse-qwen-35b-base` | Qwen 3.5 35B A3B base |
| `Ayushnangia/moltbook-obsession-gpt5` / `-gemini-flash-lite` | Obsession (v3) |
| `Ayushnangia/moltbook-frontier-mixed-mag25-1h` | Heterogeneous-models |
| `Ayushnangia/moltbook-source-citation-gpt5-1h` | Source-citation experiment |
| `Ayushnangia/moltbook-base-model-experiment-test*`, `…-ec-*-base-model-experiments` | Earlier base-model variants |
| `Ayushnangia/moltbook-conspiracy-vs-factual` | Conspiracy / factual benchmark |
| `Ayushnangia/moltbook-factual-threshold` (+ v2), `…-factcheck-dose-response`, `…-factcheck-conspiracy-grok` | Factcheck experiments |
| `Ayushnangia/moltbook-entropy-collapse-v2` | Older v2 baseline (docker-compose-era) |

## Notes / Conventions

- Directory names containing `-ignore`, `-garbage`, `-cancelled`, `-partial`,
  `-failed`, `-collapsed`, `-portcrash`, `-Xof10`, `-Xof30` indicate **failed
  or partial runs** — preserved for failure-mode documentation, not for
  publication-quality analysis.
- The `civiclens_seed`, `civiclens_world`, `civiclens_nudger` users in
  `agents.jsonl` are CivicLens infrastructure accounts (not real participants).
- Agent name prefix `agent_*` = cluster-Slurm experiments; `ranking_*` =
  earlier docker-compose-era runs (see `moltbook-entropy-collapse-v2`).
- Heartbeat versions: `HEARTBEAT.md` (v1), `HEARTBEAT-v2.md`, `HEARTBEAT-v2.1.md`,
  `HEARTBEAT-turbo.md`, `HEARTBEAT-base-model.md`, `HEARTBEAT-v3-obsessions.md`.
{project_section}{scratch_section}

## Citation

```bibtex
@dataset{{moltbook_cluster_archive_2026,
  title={{MoltBook / CivicLens Cluster Archive — 2026}},
  author={{Nangia, Ayush}},
  year={{2026}},
  url={{https://huggingface.co/datasets/{REPO_ID}}},
  note={{Private one-shot archive of cluster experiment data, logs, and analysis outputs}}
}}
```

## License

MIT.
"""


# ============================================================================
# UPLOAD ORCHESTRATION
# ============================================================================

def build_staging(inv: dict) -> Path:
    """Build a staging tree by plain copy onto /tmp (tmpfs, ~750 GB free).

    /project, /scratch, /home each present as separate filesystems despite
    sharing the Lustre backend, so hardlinks across them fail
    ("Invalid cross-device link"). /tmp is tmpfs so plain copies hit RAM
    speeds and the staging dir vanishes on reboot.
    """
    import shutil
    import subprocess

    staging = Path("/tmp/moltbook_archive_staging")
    if staging.exists():
        print(f"  Cleaning prior staging: {staging}")
        shutil.rmtree(staging)
    staging.mkdir(parents=True)
    archive = staging / "archive"
    archive.mkdir()

    def hardlink_tree(src: Path, dst: Path):
        """Recursively copy every file under src into dst (preserve perms+times)."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        # cp -a: archive mode (recursive + preserve metadata)
        subprocess.run(["cp", "-a", str(src), str(dst)], check=True)

    # 1. project-results — every subdir
    pr_root = archive / "project-results"
    pr_root.mkdir()
    for sub in inv["project_results"]["subdirs"]:
        hardlink_tree(PROJECT_RESULTS / sub, pr_root / sub)

    # 2. scratch-only
    if inv["scratch_only"]["subdirs"]:
        so_root = archive / "scratch-results"
        so_root.mkdir()
        for sub in inv["scratch_only"]["subdirs"]:
            hardlink_tree(SCRATCH_RESULTS / sub, so_root / sub)

    # 3. scratch-analysis
    if SCRATCH_ANALYSIS.exists() and any(SCRATCH_ANALYSIS.iterdir()):
        hardlink_tree(SCRATCH_ANALYSIS, archive / "scratch-analysis")

    # 4. home-analysis
    if HOME_ANALYSIS.exists():
        hardlink_tree(HOME_ANALYSIS, archive / "home-analysis")

    # 5. home-findings
    if HOME_FINDINGS.exists():
        hardlink_tree(HOME_FINDINGS, archive / "home-findings")

    # 6. home-dataset
    if HOME_DATASET.exists():
        hardlink_tree(HOME_DATASET, archive / "home-dataset")

    return staging


def main():
    print("=" * 70)
    print("MoltBook / CivicLens cluster archive — full sweep upload")
    print("=" * 70)

    api = HfApi(token=HF_TOKEN)
    me = api.whoami()
    print(f"Authenticated as: {me['name']}")

    # 1. Build inventory
    print("\n[1/4] Building inventory…")
    inv = build_inventory()
    print(f"  project-results : {inv['project_results']['n_files']:>5} files, "
          f"{fmt_bytes(inv['project_results']['size_bytes'])} ({len(inv['project_results']['subdirs'])} dirs)")
    print(f"  scratch-only    : {len(inv['scratch_only']['subdirs'])} dirs not in project")
    print(f"  scratch-analysis: {inv['scratch_analysis'].get('n_files', 0):>5} files, "
          f"{fmt_bytes(inv['scratch_analysis'].get('size_bytes', 0))}")
    print(f"  home-analysis   : {inv['home_analysis'].get('n_files', 0):>5} files, "
          f"{fmt_bytes(inv['home_analysis'].get('size_bytes', 0))}")
    print(f"  home-findings   : {inv['home_findings'].get('n_files', 0):>5} files, "
          f"{fmt_bytes(inv['home_findings'].get('size_bytes', 0))}")
    print(f"  home-dataset    : {inv['home_dataset'].get('n_files', 0):>5} files, "
          f"{fmt_bytes(inv['home_dataset'].get('size_bytes', 0))}")

    # 2. Create repo
    print(f"\n[2/4] Creating private repo {REPO_ID}…")
    create_repo(REPO_ID, repo_type="dataset", private=REPO_PRIVATE,
                exist_ok=True, token=HF_TOKEN)
    print("  [OK]")

    # 3. Push README + inventory.json first so the repo is browseable while uploads run
    print("\n[3/4] Pushing README + inventory.json…")
    readme_path = Path("/tmp/moltbook_archive_readme.md")
    readme_path.write_text(build_readme(inv))
    inventory_path = Path("/tmp/moltbook_archive_inventory.json")
    inventory_path.write_text(json.dumps(inv, indent=2))
    api.upload_file(path_or_fileobj=str(readme_path),
                    path_in_repo="README.md",
                    repo_id=REPO_ID, repo_type="dataset",
                    commit_message="archive: README + manifest")
    api.upload_file(path_or_fileobj=str(inventory_path),
                    path_in_repo="inventory.json",
                    repo_id=REPO_ID, repo_type="dataset",
                    commit_message="archive: inventory snapshot")
    print("  [OK]")

    # 4. Stage symlinks under one root then bulk-upload via upload_large_folder
    print("\n[4/4] Staging symlinks then uploading via upload_large_folder…")
    staging = build_staging(inv)
    print(f"  Staging dir: {staging}")
    print(f"  HF_HUB_ENABLE_HF_TRANSFER={os.environ.get('HF_HUB_ENABLE_HF_TRANSFER')}")
    print(f"  hf_xet high-perf={os.environ.get('HF_XET_HIGH_PERFORMANCE')}")

    # upload_large_folder: parallel workers, resumable, auto-LFS, follows symlinks.
    api.upload_large_folder(
        folder_path=str(staging),
        repo_id=REPO_ID,
        repo_type="dataset",
        ignore_patterns=[".git/*", ".gitignore", "**/.DS_Store"],
    )

    print("\n" + "=" * 70)
    print(f"DONE — https://huggingface.co/datasets/{REPO_ID}")
    print("=" * 70)


if __name__ == "__main__":
    main()
