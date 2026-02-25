#!/usr/bin/env python3
"""Prepare HuggingFace dataset from conspiracy experiment exports."""

import json
import csv
from pathlib import Path
from collections import defaultdict

EXPORT_DIR = Path("/Users/fortuna/Desktop/UoT/moltbook/exports")
MAPPING_FILE = Path("/Users/fortuna/Desktop/UoT/moltbook/experiments/conspiracy/topic-mapping.json")
OUT_DIR = Path("/tmp/hf-conspiracy-dataset/data")

RUNS = {
    "c1-run01": {"experiment": "E1", "label": "baseline", "description": "All 50 posts, random ranking treatment"},
    "c2-run01": {"experiment": "E2", "label": "nudge_veracity", "description": "All 50 posts, nudge × veracity interaction"},
    "c3-run01": {"experiment": "E3", "label": "correction", "description": "25 conspiracy-only posts"},
    "c5a-run01": {"experiment": "E5a", "label": "env_80fact", "description": "80% factual environment (20F + 5C)"},
    "c5b-run01": {"experiment": "E5b", "label": "env_50_50", "description": "50/50 environment (13F + 12C)"},
    "c5c-run01": {"experiment": "E5c", "label": "env_80cons", "description": "80% conspiracy environment (5F + 20C)"},
}

def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

def main():
    mapping = json.load(open(MAPPING_FILE))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # === 1. Combined posts CSV ===
    all_posts = []
    for run_name, meta in RUNS.items():
        posts = load_jsonl(EXPORT_DIR / run_name / "posts.jsonl")
        treatments = {t["post_id"]: t for t in load_jsonl(EXPORT_DIR / run_name / "treatments.jsonl")}
        comments = load_jsonl(EXPORT_DIR / run_name / "comments.jsonl")

        comments_by_post = defaultdict(int)
        for c in comments:
            comments_by_post[c.get("post_id", "")] += 1

        for p in posts:
            pid = p["id"]
            title = p.get("title", "")
            m = mapping.get(title, {})
            t = treatments.get(pid, {})

            all_posts.append({
                "experiment": meta["experiment"],
                "experiment_label": meta["label"],
                "run_name": run_name,
                "post_id": pid,
                "title": title,
                "content": p.get("content", ""),
                "post_type": m.get("type", "agent"),
                "topic": m.get("topic", ""),
                "score": p.get("score", 0),
                "comment_count": p.get("comment_count", 0),
                "actual_comment_count": comments_by_post.get(pid, 0),
                "treatment": t.get("treatment", "none"),
                "is_world_post": t.get("is_world_post", False),
                "author": p.get("author_name", ""),
                "created_at": p.get("created_at", ""),
            })

    with open(OUT_DIR / "posts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_posts[0].keys())
        w.writeheader()
        w.writerows(all_posts)
    print(f"posts.csv: {len(all_posts)} rows")

    # === 2. Combined comments CSV ===
    all_comments = []
    for run_name, meta in RUNS.items():
        comments = load_jsonl(EXPORT_DIR / run_name / "comments.jsonl")
        for c in comments:
            all_comments.append({
                "experiment": meta["experiment"],
                "experiment_label": meta["label"],
                "run_name": run_name,
                "comment_id": c.get("id", ""),
                "post_id": c.get("post_id", ""),
                "content": c.get("content", ""),
                "score": c.get("score", 0),
                "upvotes": c.get("upvotes", 0),
                "downvotes": c.get("downvotes", 0),
                "depth": c.get("depth", 0),
                "parent_id": c.get("parent_id", ""),
                "author": c.get("author_name", ""),
                "created_at": c.get("created_at", ""),
            })

    with open(OUT_DIR / "comments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_comments[0].keys())
        w.writeheader()
        w.writerows(all_comments)
    print(f"comments.csv: {len(all_comments)} rows")

    # === 3. Combined treatments CSV ===
    all_treatments = []
    for run_name, meta in RUNS.items():
        treatments = load_jsonl(EXPORT_DIR / run_name / "treatments.jsonl")
        for t in treatments:
            all_treatments.append({
                "experiment": meta["experiment"],
                "experiment_label": meta["label"],
                "run_name": run_name,
                "treatment_id": t.get("id", ""),
                "post_id": t.get("post_id", ""),
                "post_title": t.get("post_title", ""),
                "treatment": t.get("treatment", ""),
                "is_world_post": t.get("is_world_post", False),
                "experiment_mode": t.get("experiment_mode", ""),
                "nudge_delay_minutes": t.get("nudge_delay_minutes", ""),
                "nudge_applied_at": t.get("nudge_applied_at", ""),
                "post_score": t.get("post_score", 0),
                "post_comment_count": t.get("post_comment_count", 0),
                "created_at": t.get("created_at", ""),
            })

    with open(OUT_DIR / "treatments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_treatments[0].keys())
        w.writeheader()
        w.writerows(all_treatments)
    print(f"treatments.csv: {len(all_treatments)} rows")

    # === 4. Agents CSV ===
    all_agents = []
    seen_agents = set()
    for run_name, meta in RUNS.items():
        agents = load_jsonl(EXPORT_DIR / run_name / "agents.jsonl")
        for a in agents:
            name = a.get("name", "")
            if name not in seen_agents:
                seen_agents.add(name)
                all_agents.append({
                    "name": name,
                    "display_name": a.get("display_name", ""),
                    "description": a.get("description", ""),
                })

    with open(OUT_DIR / "agents.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_agents[0].keys())
        w.writeheader()
        w.writerows(all_agents)
    print(f"agents.csv: {len(all_agents)} rows")

    # === 5. Topic mapping ===
    with open(OUT_DIR / "topic_mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"topic_mapping.json: {len(mapping)} entries")

    # === 6. Experiment metadata ===
    experiment_meta = {}
    for run_name, meta in RUNS.items():
        run_posts = [p for p in all_posts if p["run_name"] == run_name]
        run_comments = [c for c in all_comments if c["run_name"] == run_name]
        run_treatments = [t for t in all_treatments if t["run_name"] == run_name]

        experiment_meta[run_name] = {
            **meta,
            "run_name": run_name,
            "n_posts": len(run_posts),
            "n_comments": len(run_comments),
            "n_treatments": len(run_treatments),
            "n_factual": sum(1 for p in run_posts if p["post_type"] == "factual"),
            "n_conspiracy": sum(1 for p in run_posts if p["post_type"] == "conspiracy"),
            "n_agent": sum(1 for p in run_posts if p["post_type"] == "agent"),
            "model": "gpt-5",
            "duration_hours": 1,
            "n_agents": 10,
            "heartbeat": "HEARTBEAT-v2.1.md",
            "ranking_enabled": True,
            "mode": "A",
        }

    with open(OUT_DIR / "experiment_metadata.json", "w") as f:
        json.dump(experiment_meta, f, indent=2)
    print(f"experiment_metadata.json: {len(experiment_meta)} experiments")

    print("\nDone!")

if __name__ == "__main__":
    main()
