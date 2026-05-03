#!/usr/bin/env python3
"""Distinct-n diversity (windowed and cumulative) for the resumed+merged runs.

Answers the question: "after the resume+merge, does distinct-5 still go down
along with gzip in the first 60 minutes?"

For each of the 8 merged runs (and, optionally, the 40 untouched canonical runs),
this script computes:

  1. Windowed distinct-n in 4 fixed 15-minute bins (Q1, Q2, Q3, Q4).
  2. Cumulative distinct-n: distinct-n computed over [0, b_end] for each bin
     boundary b in {15, 30, 45, 60}. This corresponds to the running diversity
     of the conversation as it unfolds — and for distinct-n it is *guaranteed*
     to monotonically decrease as repeats accumulate, unless agents keep
     introducing new vocabulary.

Output:
  findings/entropy-collapse-distinct-n-resumed/
    per_run_distinct_n.csv      one row per (run, bin) with windowed + cumulative metrics
    summary.json                aggregate Δ stats (Q4-Q1) per metric and per scope
    findings.md                 short write-up with the headline numbers

Usage:
  python3 scripts/analysis_new/distinct_n_resumed.py             # 8 overridden runs only
  python3 scripts/analysis_new/distinct_n_resumed.py --all       # full canonical 48
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Optional

# Make the repo's analysis helpers importable (load_entropy_data + 5-gram metrics).
SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPT_DIR.parent / "analysis"
for _p in (SCRIPT_DIR, ANALYSIS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# We avoid load_entropy_data.SCALE_CONFIG (which only sees GPT-5) and re-implement
# a tiny loader that takes any directory holding posts.jsonl.
from load_entropy_data import PostRecord, SEED_AUTHORS  # noqa: E402
from time_binned_lexical_metrics_5gram import (  # noqa: E402
    fixed_time_bins,
    lexical_metrics,
    prepare_posts,
)

REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_OUT_DIR = REPO_ROOT / "findings" / "entropy-collapse-distinct-n-resumed"
BIN_EDGES = [0, 15, 30, 45, 60]
DISTINCT_KEYS = ("distinct_1", "distinct_2", "distinct_3", "distinct_4", "distinct_5")


# Mapping for the 8 overridden runs: (set, scale, condition, experiment) -> (orig_path, merged_path)
# Built from data/canonical-merged/retimestamp_summary.json + the canonical inventory.
SCALE_FROM_NAME = {
    "ec-mag0-run04": "n10",
    "ec-mag1-run04": "n10",
    "ec-dom-agi-n10-run01": "n10",
    "ec-dom-tech-n10-run01": "n10",
    "ec-dom-agi-n20-run01": "n20",
    "ec-mag5-n20-run01": "n20",
    "ec-mag25-n30-run01": "n30",
    "ec-mag5-n30-run01": "n30",
}


def parse_ts(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    s = s.replace(" ", "T", 1)
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_posts(run_dir: Path, run_name: str, scale: str, condition: str) -> list[PostRecord]:
    """Build PostRecord list from a posts.jsonl directory, with 0-based minutes_elapsed."""
    posts_path = run_dir / "posts.jsonl"
    if not posts_path.exists():
        return []

    raw = []
    with posts_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw.append(json.loads(line))

    # Compute first-agent-post anchor (excluding civiclens_*).
    agent_times = []
    for post in raw:
        author = post.get("author_name", "") or ""
        if author in SEED_AUTHORS or author.startswith("civiclens_"):
            continue
        ts = post.get("created_at")
        if ts:
            agent_times.append(parse_ts(ts))
    if not agent_times:
        return []
    cond_start = min(agent_times)

    records = []
    for post in raw:
        author = post.get("author_name", "") or ""
        if author in SEED_AUTHORS or author.startswith("civiclens_"):
            continue
        ts = post.get("created_at")
        if not ts:
            continue
        created_at = parse_ts(ts)
        title = (post.get("title") or "").strip()
        content = (post.get("content") or "").strip()
        records.append(
            PostRecord(
                scale=scale,
                run_name=run_name,
                condition=condition,
                author_name=author,
                personality="",
                personality_description="",
                is_seed=False,
                created_at=ts,
                minutes_elapsed=(created_at - cond_start).total_seconds() / 60.0,
                title=title,
                content=content,
                full_text=(title + "\n" + content).strip(),
                source_file=str(posts_path),
                post_id=post.get("id", ""),
            )
        )
    return records


def parse_condition_from_name(name: str) -> str:
    """Pull the condition tag (mag0, dom-agi, ...) out of an experiment dir name."""
    import re
    m = re.match(r"ec-(.+)-run\d+", name)
    raw = m.group(1) if m else name
    return re.sub(r"-n\d+$", "", raw)


@dataclass
class RunSpec:
    label: str            # e.g. "Gemini/n20/dom-agi/ec-dom-agi-n20-run01"
    set_: str             # GPT-5, Gemini, ...
    scale: str
    condition: str
    experiment: str
    path: Path
    is_merged_override: bool


def build_inventory(repo_root: Path, all_canonical: bool) -> list[RunSpec]:
    """Return the runs we want to analyze.

    If --all, returns all 48 canonical runs (with merged overrides for the 8 resumed),
    otherwise returns only the 8 overridden runs.
    """
    summary_path = repo_root / "data" / "canonical-merged" / "retimestamp_summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing {summary_path}; run scripts/retimestamp/retimestamp_resumed.py first.")
    summary = json.loads(summary_path.read_text())
    orig_to_merged: dict[Path, Path] = {}
    merged_run_names: dict[str, Path] = {}
    for entry in summary:
        orig = (repo_root / entry["orig_dir"]).resolve()
        merged = repo_root / "data" / "canonical-merged" / entry["run"]
        orig_to_merged[orig] = merged
        merged_run_names[entry["run"]] = merged

    # Inventory of canonical paths (mirror of the gzip script's inventory).
    canonical_specs = [
        ("GPT-5",  "n10", repo_root / "data" / "moltbook-entropy-collapse-v2" / "data", False),
        ("GPT-5",  "n20", repo_root / "data" / "moltbook-entropy-collapse-20agents" / "data", False),
        ("GPT-5",  "n30", repo_root / "data" / "moltbook-entropy-collapse-30agents" / "data", False),
        ("Gemini", None,  repo_root / "data" / "moltbook-entropy-collapse-gemini-flash-lite" / "data", True),
        ("Kimi",   "n10", repo_root / "data" / "moltbook-entropy-collapse-kimi-k2.5" / "data", False),
        ("GLM-5",  "n10", repo_root / "data" / "moltbook-entropy-collapse-glm-5" / "data", False),
    ]

    specs: list[RunSpec] = []
    for set_name, scale, base, nested in canonical_specs:
        if not base.exists():
            continue
        if nested:
            for scale_dir in sorted(d for d in base.iterdir() if d.is_dir()):
                for exp_dir in sorted(d for d in scale_dir.iterdir() if d.is_dir()):
                    spec = _make_spec(set_name, scale_dir.name, exp_dir, orig_to_merged)
                    specs.append(spec)
        else:
            for exp_dir in sorted(d for d in base.iterdir() if d.is_dir()):
                spec = _make_spec(set_name, scale, exp_dir, orig_to_merged)
                specs.append(spec)

    if not all_canonical:
        specs = [s for s in specs if s.is_merged_override]
    return specs


def _make_spec(set_name: str, scale: str, exp_dir: Path, orig_to_merged: dict[Path, Path]) -> RunSpec:
    resolved = exp_dir.resolve()
    cond = parse_condition_from_name(exp_dir.name)
    if resolved in orig_to_merged:
        merged_path = orig_to_merged[resolved]
        return RunSpec(
            label=f"{set_name}/{scale}/{cond}/{exp_dir.name}",
            set_=set_name,
            scale=scale,
            condition=cond,
            experiment=exp_dir.name,
            path=merged_path,
            is_merged_override=True,
        )
    return RunSpec(
        label=f"{set_name}/{scale}/{cond}/{exp_dir.name}",
        set_=set_name,
        scale=scale,
        condition=cond,
        experiment=exp_dir.name,
        path=exp_dir,
        is_merged_override=False,
    )


def windowed_and_cumulative(prepared, max_minutes: float = 60.0):
    """Compute windowed and cumulative distinct-n at each bin boundary.

    Returns:
      bins: list of dicts with windowed metrics (q1..q4)
      cumulative: list of dicts with cumulative metrics at each bin end
                  (i.e. distinct-n on posts in [0, bin_end])
    """
    posts_in_window = [p for p in prepared if 0.0 <= float(p.record.minutes_elapsed) <= max_minutes]
    bins = fixed_time_bins(posts_in_window, bin_edges=BIN_EDGES)

    windowed_rows = []
    cumulative_rows = []
    cumulative_posts = []
    for idx, start, end, members in bins:
        m_win = lexical_metrics(members)
        windowed_rows.append({
            "bin_idx": idx,
            "bin_label": f"{int(start)}-{int(end)}",
            "bin_start_min": start,
            "bin_end_min": end,
            "n_posts": len(members),
            **{k: m_win[k] for k in DISTINCT_KEYS},
        })

        cumulative_posts.extend(members)
        m_cum = lexical_metrics(cumulative_posts)
        cumulative_rows.append({
            "bin_idx": idx,
            "bin_label": f"0-{int(end)}",
            "bin_start_min": 0.0,
            "bin_end_min": end,
            "n_posts": len(cumulative_posts),
            **{k: m_cum[k] for k in DISTINCT_KEYS},
        })
    return windowed_rows, cumulative_rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                    help="Analyze the full canonical 48 (with merged overrides). Default is the 8 overridden runs only.")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    inventory = build_inventory(REPO_ROOT, all_canonical=args.all)
    print(f"Analyzing {len(inventory)} runs (merged_overrides={sum(1 for s in inventory if s.is_merged_override)}).")

    rows: list[dict] = []
    per_run: list[dict] = []
    for spec in inventory:
        records = load_posts(spec.path, spec.experiment, spec.scale, spec.condition)
        if not records:
            print(f"  SKIP (no agent posts): {spec.label}")
            continue
        prepared = prepare_posts(records)
        wins, cums = windowed_and_cumulative(prepared, max_minutes=60.0)

        for w, c in zip(wins, cums):
            rows.append({
                "set": spec.set_, "scale": spec.scale, "condition": spec.condition,
                "experiment": spec.experiment, "merged_override": spec.is_merged_override,
                "kind": "windowed",
                **w,
            })
            rows.append({
                "set": spec.set_, "scale": spec.scale, "condition": spec.condition,
                "experiment": spec.experiment, "merged_override": spec.is_merged_override,
                "kind": "cumulative",
                **c,
            })

        # Per-run delta summary (Q4 - Q1)
        d_win = {k: wins[3][k] - wins[0][k] for k in DISTINCT_KEYS}
        d_cum = {k: cums[3][k] - cums[0][k] for k in DISTINCT_KEYS}
        per_run.append({
            "set": spec.set_, "scale": spec.scale, "condition": spec.condition,
            "experiment": spec.experiment, "merged_override": spec.is_merged_override,
            "windowed_q1_q4": {k: (wins[0][k], wins[3][k], d_win[k]) for k in DISTINCT_KEYS},
            "cumulative_q1_q4": {k: (cums[0][k], cums[3][k], d_cum[k]) for k in DISTINCT_KEYS},
            "n_posts_per_bin": [w["n_posts"] for w in wins],
        })

        bins_str = " ".join(f"Q{i+1}={w['n_posts']:>4d}" for i, w in enumerate(wins))
        d5w = d_win["distinct_5"]
        d5c = d_cum["distinct_5"]
        flag = " (merged)" if spec.is_merged_override else ""
        print(f"  {spec.label:<52s}  {bins_str}  Δd5_win={d5w:+.4f}  Δd5_cum={d5c:+.4f}{flag}")

    # Write per-run CSV
    csv_path = out_dir / "per_run_distinct_n.csv"
    fieldnames = sorted({k for row in rows for k in row})
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {csv_path}")

    # Aggregate summary
    def agg(scope_filter, kind):
        deltas = {k: [] for k in DISTINCT_KEYS}
        for r in per_run:
            if not scope_filter(r):
                continue
            src = r["windowed_q1_q4"] if kind == "windowed" else r["cumulative_q1_q4"]
            for k in DISTINCT_KEYS:
                deltas[k].append(src[k][2])
        out = {}
        for k in DISTINCT_KEYS:
            vs = deltas[k]
            if not vs:
                continue
            decl = sum(1 for v in vs if v < 0)
            out[k] = {
                "n_runs": len(vs),
                "n_decline": decl,
                "mean_delta_q4_minus_q1": round(mean(vs), 6),
                "median_delta_q4_minus_q1": round(median(vs), 6),
                "frac_declining": round(decl / len(vs), 4),
            }
        return out

    summary = {
        "scope": "8_overridden_only" if not args.all else "canonical_48",
        "n_runs_analyzed": len(per_run),
        "n_merged_overrides": sum(1 for r in per_run if r["merged_override"]),
        "windowed": {
            "all": agg(lambda r: True, "windowed"),
            "merged_overrides_only": agg(lambda r: r["merged_override"], "windowed"),
        },
        "cumulative": {
            "all": agg(lambda r: True, "cumulative"),
            "merged_overrides_only": agg(lambda r: r["merged_override"], "cumulative"),
        },
        "per_run": per_run,
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    print(f"Wrote aggregate summary to {summary_path}")

    # Headline print
    print()
    print("=== Headline (Q4 - Q1) ===")
    for kind in ("windowed", "cumulative"):
        for scope in ("merged_overrides_only", "all"):
            block = summary[kind][scope]
            if not block:
                continue
            d5 = block["distinct_5"]
            print(f"  {kind:11s}  scope={scope:24s}  Δdistinct_5  mean={d5['mean_delta_q4_minus_q1']:+.4f}  "
                  f"median={d5['median_delta_q4_minus_q1']:+.4f}  declining={d5['n_decline']}/{d5['n_runs']}")


if __name__ == "__main__":
    main()
