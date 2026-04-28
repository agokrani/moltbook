#!/usr/bin/env python3
"""Load and normalize entropy-collapse experiment data across scales."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

SEED_AUTHORS = {"civiclens_world", "civiclens_seed"}
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy",
    "mag5": "5 conspiracies",
    "mag25": "25 conspiracies",
    "dom-agi": "25 AGI hype",
    "dom-tech": "25 tech humor",
}
SCALE_CONFIG = {
    "n10": Path("dataset/moltbook-entropy-collapse-v2/data"),
    "n20": Path("dataset/moltbook-entropy-collapse-20agents/data"),
    "n30": Path("dataset/moltbook-entropy-collapse-30agents/data"),
}


@dataclass
class PostRecord:
    scale: str
    run_name: str
    condition: str
    author_name: str
    personality: str
    personality_description: str
    is_seed: bool
    created_at: str
    minutes_elapsed: float
    title: str
    content: str
    full_text: str
    source_file: str
    post_id: str

    def to_dict(self) -> dict:
        return asdict(self)


def parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def parse_condition(dirname: str) -> str:
    # Handle ec-mag0-n10-run01 style
    match = re.match(r"ec-(.+)-run\d+", dirname)
    if match:
        condition = match.group(1)
        return re.sub(r"-n\d+$", "", condition)
    # Handle bm-mag0-n10 style (base-model experiments)
    match = re.match(r"bm-(.+?)(?:-n\d+)?$", dirname)
    if match:
        return match.group(1)
    return re.sub(r"-n\d+$", "", dirname)


def canonical_author_name(author_name: str) -> str:
    return re.sub(r"^(ranking_|agent_)", "", author_name)


def load_agent_metadata(run_dir: Path) -> dict[str, dict[str, str]]:
    agents_path = run_dir / "agents.jsonl"
    metadata: dict[str, dict[str, str]] = {}
    if not agents_path.exists():
        return metadata
    with agents_path.open() as handle:
        for line in handle:
            agent = json.loads(line)
            name = agent.get("name", "")
            metadata[name] = {
                "personality": canonical_author_name(name),
                "description": agent.get("description", "").strip(),
            }
    return metadata


def load_scale(scale: str, data_dir: Path) -> list[PostRecord]:
    records: list[PostRecord] = []
    for run_dir in sorted(data_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        posts_path = run_dir / "posts.jsonl"
        if not posts_path.exists():
            continue

        condition = parse_condition(run_dir.name)
        agent_meta = load_agent_metadata(run_dir)
        raw_posts = []
        with posts_path.open() as handle:
            for line in handle:
                raw_posts.append(json.loads(line))

        agent_times = [
            parse_timestamp(post["created_at"])
            for post in raw_posts
            if post.get("author_name") not in SEED_AUTHORS
        ]
        if agent_times:
            cond_start = min(agent_times)
        else:
            cond_start = parse_timestamp(raw_posts[0]["created_at"])

        for post in raw_posts:
            author_name = post.get("author_name", "")
            is_seed = author_name in SEED_AUTHORS
            created_at = parse_timestamp(post["created_at"])
            meta = agent_meta.get(author_name, {})
            title = (post.get("title") or "").strip()
            content = (post.get("content") or "").strip()
            records.append(
                PostRecord(
                    scale=scale,
                    run_name=run_dir.name,
                    condition=condition,
                    author_name=author_name,
                    personality=meta.get("personality", canonical_author_name(author_name)),
                    personality_description=meta.get("description", ""),
                    is_seed=is_seed,
                    created_at=post["created_at"],
                    minutes_elapsed=(created_at - cond_start).total_seconds() / 60.0,
                    title=title,
                    content=content,
                    full_text=(title + "\n" + content).strip(),
                    source_file=str(posts_path),
                    post_id=post.get("id", ""),
                )
            )
    records.sort(key=lambda record: (record.scale, record.condition, record.created_at, record.post_id))
    return records


def load_all_scales(
    scale_dirs: dict[str, Path] | None = None,
    *,
    include_scales: Iterable[str] | None = None,
) -> list[PostRecord]:
    scale_dirs = scale_dirs or SCALE_CONFIG
    include = set(include_scales or scale_dirs.keys())
    all_records: list[PostRecord] = []
    for scale in sorted(include):
        if scale not in scale_dirs:
            continue
        all_records.extend(load_scale(scale, Path(scale_dirs[scale])))
    return all_records


def group_records(records: Iterable[PostRecord], key_fn) -> dict[tuple | str, list[PostRecord]]:
    grouped: dict[tuple | str, list[PostRecord]] = {}
    for record in records:
        key = key_fn(record)
        grouped.setdefault(key, []).append(record)
    return grouped
