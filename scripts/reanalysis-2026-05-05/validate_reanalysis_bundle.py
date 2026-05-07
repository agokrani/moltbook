#!/usr/bin/env python3
"""Validate that required reanalysis inputs and derived topic robustness files exist."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from common import (
    ANALYSIS_ROOT,
    DETERMINISTIC_DELTAS,
    DETERMINISTIC_TIMEBINS,
    EMBEDDING_DELTAS,
    EMBEDDING_TIMEBINS,
    LLM_DELTAS,
    LLM_TIMEBINS,
    REANALYSIS_ROOT,
    STATS_ROOT,
    TOPIC_ROBUSTNESS_DELTAS,
    write_json,
)

REQUIRED = [
    DETERMINISTIC_DELTAS,
    DETERMINISTIC_TIMEBINS,
    EMBEDDING_DELTAS,
    EMBEDDING_TIMEBINS,
    LLM_DELTAS,
    LLM_TIMEBINS,
    ANALYSIS_ROOT / "ayush_reanalysis/post_index.csv",
    ANALYSIS_ROOT / "embeddings/qwen-qwen3-embedding-8b-current-included-unique.npz",
    TOPIC_ROBUSTNESS_DELTAS,
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    rows = []
    ok = True
    for path in REQUIRED:
        exists = path.exists()
        ok = ok and exists
        rows.append({"path": str(path), "exists": exists, "size_bytes": path.stat().st_size if exists else None})
    manifest = REANALYSIS_ROOT / "FILE_MANIFEST.csv"
    manifest_status = {"exists": manifest.exists()}
    if manifest.exists():
        m = pd.read_csv(manifest)
        missing = []
        mismatched = []
        for _, row in m.iterrows():
            rel = str(row.get("path", row.get("file", "")))
            if not rel:
                continue
            local = REANALYSIS_ROOT / rel if not rel.startswith("data/reanalysis-2026-05-05") else Path(rel)
            if not local.exists():
                missing.append(rel)
                continue
            expected = row.get("sha256", None)
            if isinstance(expected, str) and len(expected) == 64 and local.name != ".gitattributes":
                actual = sha256(local)
                if actual != expected:
                    mismatched.append(rel)
        manifest_status.update({"rows": int(len(m)), "missing": len(missing), "sha256_mismatches_excluding_gitattributes": len(mismatched)})
        ok = ok and len(missing) == 0 and len(mismatched) == 0
    STATS_ROOT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(STATS_ROOT / "input_validation.csv", index=False, lineterminator="\n")
    write_json(STATS_ROOT / "input_validation_summary.json", {"ok": ok, "manifest": manifest_status})
    if not ok:
        raise SystemExit("validation failed. See stats/input_validation_summary.json")
    print("validation passed")


if __name__ == "__main__":
    main()
