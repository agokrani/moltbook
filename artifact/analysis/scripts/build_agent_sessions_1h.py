#!/usr/bin/env python3
"""Rebuild agent_sessions_1h.json — the first-hour agent-session texts used by
build_reddit_post_baseline.py (the direct Reddit post baseline builder).

Derivation (matches rebuttal-9256-repo commit 9d6fb20, "provenance validated"):
- 24 canonical n10 runs across four models, taken from the published moltbook
  HF dataset exports (posts.jsonl per run).
- Agent posts only (author_name startswith 'ranking_' / 'agent_'), sorted by
  created_at; seeds (civiclens_world / civiclens_seed) are thereby excluded.
- Four dropout runs (2x GPT-5, 2x Gemini) are rebuilt from the published
  resumed exports with the paper's retimestamping: any pause > 10 minutes is
  compressed to 1 second (compress_gaps).
- Keep posts within 3600 s of each run's first agent post; text = whitespace-
  normalized title + ' ' + content; empty strings dropped.

Usage:
  python build_agent_sessions_1h.py \
      --datasets-root moltbook-hf-datasets \
      --resumes-root moltbook-entropy-collapse-resumes
"""

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA256 = "cc1dc18dacf9882054110d61b0776dc4b49c4b01a55807fcf5642711c62a0ade"


def parse(t):
    return dt.datetime.fromisoformat(t.replace("Z", "+00:00"))


def clean(s):
    return re.sub(r"\s+", " ", (s or "").strip())


def load(path):
    with Path(path).open(encoding="utf-8") as source:
        ag = [
            row
            for row in (json.loads(line) for line in source if line.strip())
            if row["author_name"].startswith(("ranking_", "agent_"))
        ]
    ag.sort(key=lambda r: r["created_at"])
    return ag


def compress_gaps(ag, gap_min=10):
    """Paper's retimestamp: detect large pause, shift post-pause records so the
    gap becomes 1 second."""
    out = [dict(r) for r in ag]
    shift = dt.timedelta(0)
    for i in range(1, len(out)):
        t_prev = parse(ag[i - 1]["created_at"])
        t_cur = parse(ag[i]["created_at"])
        if (t_cur - t_prev) > dt.timedelta(minutes=gap_min):
            shift += (t_cur - t_prev) - dt.timedelta(seconds=1)
        out[i]["created_at"] = (t_cur - shift).isoformat().replace("+00:00", "Z")
    return out


RESUME_FILES = {
    ("GPT-5", "ec-mag0-run04"): "ec-mag0-run04-resumed",
    ("GPT-5", "ec-mag1-run04"): "ec-mag1-run04-resumed",
    ("Gemini", "ec-dom-agi-n10-run01"): "ec-dom-agi-n10-run01-resumed",
    ("Gemini", "ec-dom-tech-n10-run01"): "ec-dom-tech-n10-run01-resumed",
}

SETS = {
    "GPT-5": "moltbook-entropy-collapse-v2/data/*",
    "Gemini": "moltbook-entropy-collapse-gemini-flash-lite/data/n10/*",
    "Kimi": "moltbook-entropy-collapse-kimi-k2.5/data/*",
    "GLM-5": "moltbook-entropy-collapse-glm-5/data/*",
}


def resume_posts_path(root: Path, name: str) -> Path:
    """Resolve both the published Hub layout and the older flat layout."""
    candidates = [
        root / "data" / name / "posts.jsonl",
        root / name / "posts.jsonl",
        root / f"{name}.posts.jsonl",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    expected = " or ".join(str(path) for path in candidates)
    raise FileNotFoundError(f"resume post export not found; expected {expected}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets-root", default="moltbook-hf-datasets")
    ap.add_argument("--resumes-root", default="moltbook-entropy-collapse-resumes")
    ap.add_argument("--output", type=Path, default=ROOT / "results/agent_sessions_1h.json")
    ap.add_argument(
        "--skip-hash-check",
        action="store_true",
        help="allow output that differs from the release-locked dataset revisions",
    )
    args = ap.parse_args()

    sessions = []
    for model, pat in SETS.items():
        for d in sorted(glob.glob(os.path.join(args.datasets_root, pat))):
            run = Path(d).name
            if (model, run) in RESUME_FILES:
                ag = compress_gaps(
                    load(
                        resume_posts_path(
                            Path(args.resumes_root), RESUME_FILES[(model, run)]
                        )
                    )
                )
            else:
                ag = load(os.path.join(d, "posts.jsonl"))
            t0 = parse(ag[0]["created_at"])
            first = [
                r for r in ag if (parse(r["created_at"]) - t0).total_seconds() <= 3600
            ]
            texts = [
                t
                for t in (
                    clean((r.get("title", "") or "") + " " + (r.get("content", "") or ""))
                    for r in first
                )
                if t
            ]
            sessions.append({"model": model, "run": run, "n": len(first), "texts": texts})

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        json.dump(sessions, destination)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    if not args.skip_hash_check and digest != EXPECTED_SHA256:
        raise RuntimeError(
            f"output SHA-256 {digest} does not match release value {EXPECTED_SHA256}; "
            "use the revisions in artifact/data/datasets.lock.json"
        )
    print(len(sessions), "sessions; posts per session:", sorted(s["n"] for s in sessions))
    print("sha256", digest)


if __name__ == "__main__":
    main()
