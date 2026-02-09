#!/usr/bin/env python3
"""
Score CivicLens consensus tasks from an exported dataset.

Expected export directory contents (from scripts/export-experiment.sh):
  - posts.jsonl
  - comments.jsonl
  - activity.jsonl (optional but recommended)

Consensus tasks are identified by a tag substring in post titles (default: "CL:CONSENSUS")
and options are identified by top-level comments prefixed with "CL_OPTION:".
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def parse_iso8601(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    # Postgres-style timestamps are typically ISO 8601 with timezone.
    try:
        # Normalize trailing Z
        if ts.endswith("Z"):
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def shannon_entropy_bits(counts: List[int]) -> Optional[float]:
    total = sum(counts)
    if total <= 0:
        return None
    entropy = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        entropy -= p * math.log2(p)
    return entropy


@dataclass(frozen=True)
class OptionScore:
    comment_id: str
    label: str
    score: int
    upvotes: int
    downvotes: int


def main() -> int:
    parser = argparse.ArgumentParser(description="Score CivicLens consensus tasks from exports/")
    parser.add_argument("export_dir", type=Path, help="Path to exports/<experiment-name>/")
    parser.add_argument("--tag", default="CL:CONSENSUS", help="Substring to match in post titles")
    parser.add_argument("--option-prefix", default="CL_OPTION:", help="Prefix used for option comments")
    parser.add_argument(
        "--exclude-agent-prefix",
        default="civiclens_seed",
        help="Exclude voters whose agent_name starts with this prefix (set empty to disable)",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of human-readable output")

    args = parser.parse_args()

    export_dir: Path = args.export_dir
    posts_path = export_dir / "posts.jsonl"
    comments_path = export_dir / "comments.jsonl"
    activity_path = export_dir / "activity.jsonl"

    if not posts_path.exists() or not comments_path.exists():
        print(f"[ERROR] Missing required files in {export_dir}", file=sys.stderr)
        print("Expected: posts.jsonl and comments.jsonl", file=sys.stderr)
        return 2

    posts = list(read_jsonl(posts_path))
    comments = list(read_jsonl(comments_path))
    activity: List[Dict[str, Any]] = list(read_jsonl(activity_path)) if activity_path.exists() else []

    comments_by_post: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in comments:
        post_id = c.get("post_id")
        if post_id:
            comments_by_post[str(post_id)].append(c)

    # Index activity by target_id for quick lookup
    activity_by_target: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for ev in activity:
        tid = ev.get("target_id")
        if tid:
            activity_by_target[str(tid)].append(ev)

    consensus_posts = [p for p in posts if args.tag in (p.get("title") or "")]

    results: List[Dict[str, Any]] = []

    for post in consensus_posts:
        post_id = str(post.get("id") or "")
        if not post_id:
            continue

        post_comments = comments_by_post.get(post_id, [])

        option_comments: List[Dict[str, Any]] = []
        for c in post_comments:
            content = (c.get("content") or "").strip()
            if not content.startswith(args.option_prefix):
                continue
            # Top-level options are preferred; allow missing parent_id for older exports.
            parent_id = c.get("parent_id")
            if parent_id not in (None, "", "null"):
                continue
            option_comments.append(c)

        if not option_comments:
            continue

        options: List[OptionScore] = []
        for c in option_comments:
            label = (c.get("content") or "")[len(args.option_prefix) :].strip()
            options.append(
                OptionScore(
                    comment_id=str(c.get("id") or ""),
                    label=label,
                    score=int(c.get("score") or 0),
                    upvotes=int(c.get("upvotes") or 0),
                    downvotes=int(c.get("downvotes") or 0),
                )
            )

        options_sorted = sorted(options, key=lambda o: (o.score, o.upvotes, -o.downvotes), reverse=True)
        winner = options_sorted[0]
        runner_up = options_sorted[1] if len(options_sorted) > 1 else None

        total_upvotes = sum(o.upvotes for o in options_sorted)
        winner_share = (winner.upvotes / total_upvotes) if total_upvotes > 0 else None
        entropy = shannon_entropy_bits([o.upvotes for o in options_sorted])

        margin_upvotes = winner.upvotes - (runner_up.upvotes if runner_up else 0)
        margin_score = winner.score - (runner_up.score if runner_up else 0)

        # Participation (from activity log if present)
        voters: set[str] = set()
        vote_times: List[datetime] = []

        if activity:
            option_ids = {o.comment_id for o in options_sorted if o.comment_id}
            for oid in option_ids:
                for ev in activity_by_target.get(oid, []):
                    if ev.get("target_type") != "comment":
                        continue
                    if ev.get("action_type") not in ("upvote", "downvote", "vote_removed", "vote_changed"):
                        continue

                    agent_name = (ev.get("agent_name") or "").strip()
                    if args.exclude_agent_prefix and agent_name.startswith(args.exclude_agent_prefix):
                        continue
                    if agent_name:
                        voters.add(agent_name)

                    ts = parse_iso8601(ev.get("created_at") or "")
                    if ts:
                        vote_times.append(ts.astimezone(timezone.utc))

        vote_window_seconds = None
        if vote_times:
            vote_times.sort()
            vote_window_seconds = int((vote_times[-1] - vote_times[0]).total_seconds())

        result = {
            "post_id": post_id,
            "title": post.get("title"),
            "created_at": post.get("created_at"),
            "winner": {
                "label": winner.label,
                "comment_id": winner.comment_id,
                "score": winner.score,
                "upvotes": winner.upvotes,
                "downvotes": winner.downvotes,
            },
            "options": [
                {
                    "label": o.label,
                    "comment_id": o.comment_id,
                    "score": o.score,
                    "upvotes": o.upvotes,
                    "downvotes": o.downvotes,
                }
                for o in options_sorted
            ],
            "metrics": {
                "total_upvotes": total_upvotes,
                "winner_share_upvotes": winner_share,
                "entropy_bits_upvotes": entropy,
                "margin_upvotes": margin_upvotes,
                "margin_score": margin_score,
                "voter_count": len(voters) if activity else None,
                "vote_window_seconds": vote_window_seconds,
            },
        }
        results.append(result)

    if args.json:
        json.dump(
            {
                "export_dir": str(export_dir),
                "tag": args.tag,
                "tasks_scored": len(results),
                "results": results,
            },
            sys.stdout,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    if not results:
        print(f"No consensus tasks found (tag '{args.tag}') in {export_dir}")
        return 0

    print(f"Consensus tasks scored: {len(results)}")
    print(f"Export: {export_dir}")
    print("")

    for r in results:
        metrics = r["metrics"]
        print(f"== {r['title']}  ({r['post_id']})")
        if metrics.get("voter_count") is not None:
            print(f"Voters: {metrics['voter_count']}  Vote window (s): {metrics.get('vote_window_seconds')}")
        print(
            "Winner:",
            f"{r['winner']['label']} | score={r['winner']['score']} up={r['winner']['upvotes']} down={r['winner']['downvotes']}",
        )
        if metrics.get("winner_share_upvotes") is not None:
            print(f"Winner share (upvotes): {metrics['winner_share_upvotes']:.2f}  Entropy(bits): {metrics['entropy_bits_upvotes']:.2f}")
        print("Options:")
        for o in r["options"]:
            print(f"  - {o['label']} | score={o['score']} up={o['upvotes']} down={o['downvotes']}")
        print("")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

