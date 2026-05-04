#!/usr/bin/env python3
"""Print progress for the Ayush blinded LLM-judge background run."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
from pathlib import Path
from typing import Any

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
DEFAULT_MODEL = "google/gemini-3.1-flash-lite-preview"
RUBRIC_VERSION = "ayush-blind-all-posts-v1"


def expected_row_ids(root: Path) -> set[str]:
    """Return unique judge row IDs for the current included non-seed post index."""
    post_index = root / "ayush_reanalysis" / "post_index.jsonl"
    ids: set[str] = set()
    if post_index.exists():
        for line in post_index.open():
            if not line.strip():
                continue
            row = json.loads(line)
            if not row.get("is_seed"):
                ids.add(str(row["record_id"]))
    return ids


def expected_total(root: Path) -> int:
    ids = expected_row_ids(root)
    if ids:
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
    expected_ids = expected_row_ids(root)
    conn = sqlite3.connect(db)
    try:
        rows = {str(r[0]) for r in conn.execute(
            "SELECT row_uid FROM judgments WHERE judge_model=? AND rubric_version=?",
            (model, RUBRIC_VERSION),
        )}
        return len(rows & expected_ids) if expected_ids else len(rows)
    finally:
        conn.close()


def process_status(root: Path) -> dict[str, Any]:
    pid_path = root / "ayush_reanalysis" / "llm_judge" / "judge_all.pid"
    if not pid_path.exists():
        return {"pid": None, "running": False, "ps": "pid file missing"}
    pid = pid_path.read_text().strip()
    try:
        ps = subprocess.check_output(["ps", "-p", pid, "-o", "pid=,stat=,etime=,pcpu=,pmem=,command="], text=True).strip()
        return {"pid": pid, "running": bool(ps), "ps": ps or "not running"}
    except subprocess.CalledProcessError:
        return {"pid": pid, "running": False, "ps": "not running"}


def latest_log(root: Path) -> str:
    log = root / "ayush_reanalysis" / "llm_judge" / "logs" / "judge_all.log"
    if not log.exists():
        return ""
    text = log.read_text(errors="ignore")
    parts = [part.strip() for part in text.replace("\r", "\n").splitlines() if part.strip()]
    return parts[-1] if parts else ""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()
    root = Path(args.out_dir)
    total = expected_total(root)
    cached = cached_count(root, args.model)
    remaining = max(total - cached, 0)
    percent = (cached / total * 100.0) if total else 0.0
    status = process_status(root)
    payload = {
        "model": args.model,
        "rubric_version": RUBRIC_VERSION,
        "cached": cached,
        "total": total,
        "remaining": remaining,
        "percent": round(percent, 2),
        "process": status,
        "latest_log": latest_log(root),
    }
    if args.as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"judge model: {payload['model']}")
    print(f"cached: {cached:,}/{total:,} ({percent:.1f}%), remaining: {remaining:,}")
    print(f"process: {status['ps']}")
    if payload["latest_log"]:
        print(f"latest log: {payload['latest_log']}")


if __name__ == "__main__":
    main()
