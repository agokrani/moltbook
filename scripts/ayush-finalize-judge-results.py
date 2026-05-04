#!/usr/bin/env python3
"""Finalize Ayush reanalysis once the blinded LLM-judge cache is complete.

This intentionally does not commit or push. It verifies cache completeness by
counting local SQLite judgments, then runs the public aggregate/report steps.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
DEFAULT_MODEL = "google/gemini-3.1-flash-lite-preview"
RUBRIC_VERSION = "ayush-blind-all-posts-v1"


def expected_total(root: Path) -> int:
    """Return unique judge rows, not raw post rows.

    The post index contains a few exact duplicate non-seed records. Judge cache
    keys by row_uid, so complete scoring means every unique row_uid is judged;
    aggregation joins the single judgment back onto duplicate metadata rows.
    """
    post_index = root / "ayush_reanalysis" / "post_index.jsonl"
    if post_index.exists():
        ids = set()
        for line in post_index.open():
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("is_seed"):
                ids.add(str(row["record_id"]))
        return len(ids)
    summary = root / "data_manifest_summary.json"
    if summary.exists():
        data = json.loads(summary.read_text())
        return int(sum(data.get("included_posts_by_family", {}).values()))
    return 0


def cached_count(root: Path, model: str) -> int:
    db = root / "ayush_reanalysis" / "llm_judge" / "judge_cache.sqlite"
    if not db.exists():
        return 0
    conn = sqlite3.connect(db)
    try:
        return int(conn.execute(
            "SELECT count(*) FROM judgments WHERE judge_model=? AND rubric_version=?",
            (model, RUBRIC_VERSION),
        ).fetchone()[0])
    finally:
        conn.close()


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--allow-partial", action="store_true", help="diagnostic only; final artifacts should not use this")
    parser.add_argument("--check-only", action="store_true", help="print completeness status and exit")
    args = parser.parse_args()

    root = Path(args.out_dir)
    expected = expected_total(root)
    cached = cached_count(root, args.model)
    print(f"judge cache: {cached:,}/{expected:,} ({cached / expected * 100 if expected else 0:.1f}%)")

    if args.check_only:
        raise SystemExit(0 if cached >= expected else 1)
    if cached < expected and not args.allow_partial:
        raise SystemExit(
            f"Refusing to finalize incomplete judge cache: {cached:,}/{expected:,}. "
            "Wait for scoring to finish or pass --allow-partial for diagnostics only."
        )

    aggregate = [sys.executable, "scripts/ayush-blind-llm-judge.py", "aggregate", "--out-dir", str(root), "--model", args.model]
    if args.allow_partial:
        aggregate.append("--allow-partial")
    run(aggregate)
    run([sys.executable, "scripts/ayush-final-report.py", "--out-dir", str(root)])

    required = [
        root / "combined_report" / "LLM_JUDGE_SUMMARY.md",
        root / "combined_report" / "llm_judge_summary_by_family.csv",
        root / "combined_report" / "llm_judge_label_counts.csv",
        root / "ayush_reanalysis" / "llm_judge_run_timebin_metrics.csv",
        root / "ayush_reanalysis" / "llm_judge_run_deltas.csv",
        root / "FINAL_REPORT.md",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit("Missing expected final artifacts:\n" + "\n".join(missing))
    print("final judge artifacts generated; review, scan, commit, and push manually")


if __name__ == "__main__":
    main()
