#!/usr/bin/env python3
"""Canonical compression-ratio analysis for EMNLP entropy-collapse runs.

This script intentionally reads the curated local `data/` mirrors, not raw
scratch exports. It also filters every run to the first 60 minutes before
binning, matching the entropy-collapse-scaling diversity analysis.

Output bins are fixed 15-minute windows over the first hour:
  Q1 = [0, 15), Q2 = [15, 30), Q3 = [30, 45), Q4 = [45, 60]

Usage:
    python3 scripts/gzip/compute_compression.py \
      --data-root data \
      --output findings/entropy-collapse-gzip/results-canonical-48.json
"""

from __future__ import annotations

import argparse
import bz2
import gzip
import json
import re
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

COMPRESSORS = {
    "gzip": gzip.compress,
    "bzip2": bz2.compress,
    "zlib": zlib.compress,
}

ALGORITHMS = list(COMPRESSORS.keys())

CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]

# Canonical paper inventory. Paths are relative to --data-root.
CANONICAL_DATASETS = [
    {
        "set": "GPT-5",
        "model": "gpt-5",
        "scale": "n10",
        "path": "moltbook-entropy-collapse-v2/data",
        "nested_scales": False,
    },
    {
        "set": "GPT-5",
        "model": "gpt-5",
        "scale": "n20",
        "path": "moltbook-entropy-collapse-20agents/data",
        "nested_scales": False,
    },
    {
        "set": "GPT-5",
        "model": "gpt-5",
        "scale": "n30",
        "path": "moltbook-entropy-collapse-30agents/data",
        "nested_scales": False,
    },
    {
        "set": "Gemini",
        "model": "google/gemini-3.1-flash-lite-preview",
        "scale": None,
        "path": "moltbook-entropy-collapse-gemini-flash-lite/data",
        "nested_scales": True,
    },
    {
        "set": "Kimi",
        "model": "moonshotai/kimi-k2.5",
        "scale": "n10",
        "path": "moltbook-entropy-collapse-kimi-k2.5/data",
        "nested_scales": False,
    },
    {
        "set": "GLM-5",
        "model": "z-ai/glm-5",
        "scale": "n10",
        "path": "moltbook-entropy-collapse-glm-5/data",
        "nested_scales": False,
    },
]

SYSTEM_PREFIXES = ("civiclens_",)


def parse_time(value: str) -> datetime:
    """Parse ISO timestamps from exported JSONL files."""
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def compression_ratio(data: bytes, algorithm: str) -> float:
    """Return compressed_size / original_size. 0.0 for empty data."""
    if not data:
        return 0.0
    compressed = COMPRESSORS[algorithm](data)
    return len(compressed) / len(data)


def post_text(post: dict) -> str:
    title = post.get("title", "") or ""
    content = post.get("content", "") or ""
    return f"{title}\n{content}"


def load_agent_posts(exp_dir: Path) -> List[dict]:
    """Load agent-authored posts from one run, excluding CivicLens seed/system posts."""
    posts_path = exp_dir / "posts.jsonl"
    posts: List[dict] = []
    if not posts_path.exists():
        return posts

    with posts_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            post = json.loads(line)
            author = post.get("author_name", "") or ""
            if author.startswith(SYSTEM_PREFIXES):
                continue
            if not post.get("created_at"):
                continue
            posts.append(post)
    return posts


def filter_first_hour(posts: List[dict], minutes: int = 60) -> Tuple[List[dict], Optional[datetime]]:
    """Keep posts within the first N minutes from the first agent post."""
    if not posts:
        return [], None
    sorted_posts = sorted(posts, key=lambda p: parse_time(p["created_at"]))
    start = parse_time(sorted_posts[0]["created_at"])
    end = start + timedelta(minutes=minutes)
    filtered = [p for p in sorted_posts if parse_time(p["created_at"]) <= end]
    return filtered, start


def split_fixed_15m_bins(posts: List[dict], start: datetime) -> List[List[dict]]:
    """Split first-hour posts into fixed 15-minute bins."""
    bins: List[List[dict]] = [[] for _ in range(4)]
    for post in posts:
        elapsed = (parse_time(post["created_at"]) - start).total_seconds() / 60.0
        if elapsed < 0 or elapsed > 60:
            continue
        if elapsed < 15:
            idx = 0
        elif elapsed < 30:
            idx = 1
        elif elapsed < 45:
            idx = 2
        else:
            idx = 3
        bins[idx].append(post)
    return bins


def read_metadata(exp_dir: Path) -> dict:
    meta_path = exp_dir / "metadata.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text())
    except Exception:
        return {}


def extract_condition(exp_dir: Path, meta: dict) -> str:
    if meta.get("condition"):
        return meta["condition"]
    name = exp_dir.name
    for cond in CONDITIONS:
        if cond in name:
            return cond
    return name


def discover_runs(data_root: Path, merged_overrides_dir: Optional[Path] = None) -> List[dict]:
    """Discover the canonical 48 runs from the curated data/ inventory.

    If ``merged_overrides_dir`` is given (e.g. ``data/canonical-merged``), any run
    whose ``experiment`` name has a matching subdirectory in that override dir
    will have its ``path`` redirected there. This lets us substitute the 8
    re-timestamped resumed+merged runs without touching the originals on disk.
    """
    runs: List[dict] = []

    for spec in CANONICAL_DATASETS:
        base = data_root / spec["path"]
        if not base.exists():
            raise FileNotFoundError(f"Canonical data path not found: {base}")

        if spec["nested_scales"]:
            scale_dirs = sorted(d for d in base.iterdir() if d.is_dir())
            for scale_dir in scale_dirs:
                scale = scale_dir.name
                for exp_dir in sorted(d for d in scale_dir.iterdir() if d.is_dir()):
                    meta = read_metadata(exp_dir)
                    runs.append({
                        "set": spec["set"],
                        "model": meta.get("model") or spec["model"],
                        "scale": scale,
                        "condition": extract_condition(exp_dir, meta),
                        "experiment": exp_dir.name,
                        "path": exp_dir,
                        "metadata_duration_minutes": meta.get("duration_minutes"),
                    })
        else:
            for exp_dir in sorted(d for d in base.iterdir() if d.is_dir()):
                meta = read_metadata(exp_dir)
                runs.append({
                    "set": spec["set"],
                    "model": meta.get("model") or spec["model"],
                    "scale": spec["scale"],
                    "condition": extract_condition(exp_dir, meta),
                    "experiment": exp_dir.name,
                    "path": exp_dir,
                    "metadata_duration_minutes": meta.get("duration_minutes"),
                })

    if merged_overrides_dir is not None and merged_overrides_dir.exists():
        # Build (canonical_orig_dir -> merged_dir) map from the retimestamp summary.
        # We match runs by their canonical source path so the same experiment name
        # appearing in multiple datasets (e.g. ec-dom-agi-n10-run01 exists for
        # Gemini, Kimi, and GLM-5) is disambiguated correctly.
        summary_path = merged_overrides_dir / "retimestamp_summary.json"
        orig_to_merged: Dict[Path, Path] = {}
        if summary_path.exists():
            try:
                summary = json.loads(summary_path.read_text())
                for entry in summary:
                    orig = entry.get("orig_dir")
                    name = entry.get("run")
                    if orig and name:
                        merged = merged_overrides_dir / name
                        if merged.is_dir() and (merged / "posts.jsonl").exists():
                            orig_to_merged[Path(orig).resolve()] = merged
            except Exception as exc:
                print(f"[merged-overrides] failed to read {summary_path}: {exc}")
        else:
            print(f"[merged-overrides] WARNING: no retimestamp_summary.json in {merged_overrides_dir}; skipping overrides.")

        applied = []
        for run in runs:
            run_resolved = Path(run["path"]).resolve()
            if run_resolved in orig_to_merged:
                run["path"] = orig_to_merged[run_resolved]
                run["merged_override"] = True
                applied.append(f"{run['set']}/{run['scale']}/{run['experiment']}")
        if applied:
            print(f"[merged-overrides] applied to {len(applied)} runs:")
            for a in applied:
                print(f"  {a}")

    return runs


def compute_run(run: dict, algorithms: Iterable[str], first_minutes: int) -> Optional[dict]:
    all_agent_posts = load_agent_posts(run["path"])
    first_hour_posts, start = filter_first_hour(all_agent_posts, first_minutes)
    if not first_hour_posts or start is None:
        return None

    bins_posts = split_fixed_15m_bins(first_hour_posts, start)
    bins = []

    for idx, chunk in enumerate(bins_posts):
        text = "\n".join(post_text(p) for p in chunk)
        text_bytes = text.encode("utf-8")
        ratios = {alg: round(compression_ratio(text_bytes, alg), 6) for alg in algorithms}
        bins.append({
            "quartile": idx + 1,
            "bin_start_min": idx * 15,
            "bin_end_min": (idx + 1) * 15,
            "n_posts": len(chunk),
            "total_bytes": len(text_bytes),
            "ratios": ratios,
        })

    deltas = {
        alg: round(bins[-1]["ratios"][alg] - bins[0]["ratios"][alg], 6)
        for alg in algorithms
    }

    return {
        "experiment": run["experiment"],
        "condition": run["condition"],
        "scale": run["scale"],
        "set": run["set"],
        "model": run["model"],
        "source_path": str(run["path"]),
        "merged_override": bool(run.get("merged_override", False)),
        "metadata_duration_minutes": run["metadata_duration_minutes"],
        "first_post_at": start.isoformat(),
        "first_minutes": first_minutes,
        "n_agent_posts_total_export": len(all_agent_posts),
        "n_posts": len(first_hour_posts),
        "n_posts_excluded_after_first_window": len(all_agent_posts) - len(first_hour_posts),
        "bins": bins,
        "deltas": deltas,
    }


def validate_inventory(results: List[dict]) -> None:
    if len(results) != 48:
        raise RuntimeError(f"Expected 48 canonical runs, got {len(results)}")

    expected_counts = {
        ("GPT-5", "n10"): 6,
        ("GPT-5", "n20"): 6,
        ("GPT-5", "n30"): 6,
        ("Gemini", "n10"): 6,
        ("Gemini", "n20"): 6,
        ("Gemini", "n30"): 6,
        ("Kimi", "n10"): 6,
        ("GLM-5", "n10"): 6,
    }
    actual: Dict[Tuple[str, str], int] = {}
    for row in results:
        key = (row["set"], row["scale"])
        actual[key] = actual.get(key, 0) + 1

    if actual != expected_counts:
        raise RuntimeError(f"Canonical inventory mismatch. Expected {expected_counts}, got {actual}")

    for key in expected_counts:
        conds = sorted(r["condition"] for r in results if (r["set"], r["scale"]) == key)
        if conds != sorted(CONDITIONS):
            raise RuntimeError(f"Condition mismatch for {key}: {conds}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical gzip/bzip2/zlib compression analysis")
    parser.add_argument("--data-root", default="data", help="Root containing canonical local datasets")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--first-minutes", type=int, default=60, help="Minutes from first agent post to include")
    parser.add_argument("--algorithms", nargs="+", default=ALGORITHMS, choices=ALGORITHMS)
    parser.add_argument("--merged-overrides-dir", default=None,
                        help="Optional directory (e.g. data/canonical-merged) whose subdirectories override matching canonical runs by experiment name. Used to substitute resumed+retimestamped runs.")
    args = parser.parse_args()

    data_root = Path(args.data_root)
    overrides_dir = Path(args.merged_overrides_dir) if args.merged_overrides_dir else None
    runs = discover_runs(data_root, merged_overrides_dir=overrides_dir)

    results = []
    for run in runs:
        result = compute_run(run, args.algorithms, args.first_minutes)
        if result is None:
            print(f"Skipping empty run: {run['path']}")
            continue
        results.append(result)
        gzip_delta = result["deltas"].get("gzip")
        print(
            f"{result['set']:7s} {result['scale']:3s} {result['condition']:8s} "
            f"{result['experiment']:32s} posts={result['n_posts']:4d} "
            f"excluded={result['n_posts_excluded_after_first_window']:4d} "
            f"gzip Δ={gzip_delta:+.4f}"
        )

    validate_inventory(results)

    output = {
        "meta": {
            "analysis": "canonical_first_60_minute_compression",
            "algorithms": args.algorithms,
            "n_quartiles": 4,
            "binning": "fixed_15_minute_bins_after_first_agent_post",
            "first_minutes": args.first_minutes,
            "data_root": str(data_root),
            "merged_overrides_dir": str(overrides_dir) if overrides_dir else None,
            "merged_overrides_applied": sorted(r["experiment"] for r in runs if r.get("merged_override")),
            "canonical_datasets": CANONICAL_DATASETS,
            "notes": [
                "Reads curated local data/ mirrors, not raw scratch exports.",
                "Excludes CivicLens system/seed posts via author_name prefix civiclens_.",
                "Filters every run to first 60 minutes from first agent-authored post.",
                "When --merged-overrides-dir is set, matching runs are read from that dir (resumed+retimestamped) instead of the canonical mirror.",
            ],
        },
        "results": results,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {len(results)} canonical runs to {out_path}")


if __name__ == "__main__":
    main()
