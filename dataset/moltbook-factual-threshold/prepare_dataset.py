#!/usr/bin/env python3
"""Prepare and push threshold dose-response dataset to HuggingFace.

Creates Ayushnangia/moltbook-factual-threshold with:
  - data/posts.csv, comments.csv, treatments.csv, agents.csv
  - data/topic_mapping.json, experiment_metadata.json
  - raw/{run_name}/*.jsonl (original exports)
  - figures/threshold_dose_response.png, threshold_score_gap.png
  - README.md (dataset card)
  - prepare_dataset.py (this script, for reproducibility)
"""

import json
import csv
import shutil
from pathlib import Path
from collections import defaultdict

EXPORT_DIR = Path("/Users/fortuna/Desktop/UoT/moltbook/exports")
MAPPING_FILE = Path("/Users/fortuna/Desktop/UoT/moltbook/experiments/conspiracy/topic-mapping.json")
FIGURES_DIR = Path("/Users/fortuna/Desktop/UoT/moltbook/experiments/conspiracy/figures")
OUT_DIR = Path("/tmp/hf-threshold/repo")

CONDITIONS = {
    "th-f0-run01": {"experiment": "TH-F0", "label": "dose_0", "n_factual": 0, "n_conspiracy": 25,
                     "description": "Pure conspiracy baseline (0 factual + 25 conspiracy)"},
    "th-f1-run01": {"experiment": "TH-F1", "label": "dose_1", "n_factual": 1, "n_conspiracy": 24,
                     "description": "Minimal factual (1 factual + 24 conspiracy)"},
    "th-f2-run01": {"experiment": "TH-F2", "label": "dose_2", "n_factual": 2, "n_conspiracy": 23,
                     "description": "Low factual (2 factual + 23 conspiracy)"},
    "th-f3-run01": {"experiment": "TH-F3", "label": "dose_3", "n_factual": 3, "n_conspiracy": 22,
                     "description": "Moderate factual (3 factual + 22 conspiracy)"},
    "th-f4-run01": {"experiment": "TH-F4", "label": "dose_4", "n_factual": 4, "n_conspiracy": 21,
                     "description": "High factual (4 factual + 21 conspiracy)"},
    "th-f5-run01": {"experiment": "TH-F5", "label": "dose_5", "n_factual": 5, "n_conspiracy": 20,
                     "description": "Maximum factual (5 factual + 20 conspiracy)"},
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
    data_dir = OUT_DIR / "data"
    raw_dir = OUT_DIR / "raw"
    fig_dir = OUT_DIR / "figures"
    data_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    # === 1. Combined posts CSV ===
    all_posts = []
    for run_name, meta in CONDITIONS.items():
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
                "n_factual_dose": meta["n_factual"],
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

    with open(data_dir / "posts.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_posts[0].keys())
        w.writeheader()
        w.writerows(all_posts)
    print(f"posts.csv: {len(all_posts)} rows")

    # === 2. Combined comments CSV ===
    all_comments = []
    for run_name, meta in CONDITIONS.items():
        comments = load_jsonl(EXPORT_DIR / run_name / "comments.jsonl")
        for c in comments:
            all_comments.append({
                "experiment": meta["experiment"],
                "experiment_label": meta["label"],
                "n_factual_dose": meta["n_factual"],
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

    with open(data_dir / "comments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_comments[0].keys())
        w.writeheader()
        w.writerows(all_comments)
    print(f"comments.csv: {len(all_comments)} rows")

    # === 3. Combined treatments CSV ===
    all_treatments = []
    for run_name, meta in CONDITIONS.items():
        treatments = load_jsonl(EXPORT_DIR / run_name / "treatments.jsonl")
        for t in treatments:
            all_treatments.append({
                "experiment": meta["experiment"],
                "experiment_label": meta["label"],
                "n_factual_dose": meta["n_factual"],
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

    with open(data_dir / "treatments.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_treatments[0].keys())
        w.writeheader()
        w.writerows(all_treatments)
    print(f"treatments.csv: {len(all_treatments)} rows")

    # === 4. Agents CSV ===
    all_agents = []
    seen_agents = set()
    for run_name in CONDITIONS:
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

    with open(data_dir / "agents.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=all_agents[0].keys())
        w.writeheader()
        w.writerows(all_agents)
    print(f"agents.csv: {len(all_agents)} rows")

    # === 5. Topic mapping ===
    with open(data_dir / "topic_mapping.json", "w") as f:
        json.dump(mapping, f, indent=2)
    print(f"topic_mapping.json: {len(mapping)} entries")

    # === 6. Experiment metadata ===
    experiment_meta = {}
    for run_name, meta in CONDITIONS.items():
        run_posts = [p for p in all_posts if p["run_name"] == run_name]
        run_comments = [c for c in all_comments if c["run_name"] == run_name]
        run_treatments = [t for t in all_treatments if t["run_name"] == run_name]

        experiment_meta[run_name] = {
            **meta,
            "run_name": run_name,
            "n_posts": len(run_posts),
            "n_comments": len(run_comments),
            "n_treatments": len(run_treatments),
            "n_factual_actual": sum(1 for p in run_posts if p["post_type"] == "factual"),
            "n_conspiracy_actual": sum(1 for p in run_posts if p["post_type"] == "conspiracy"),
            "n_agent_posts": sum(1 for p in run_posts if p["post_type"] == "agent"),
            "model": "gpt-5",
            "duration_hours": 1,
            "n_agents": 10,
            "heartbeat": "HEARTBEAT-v2.1.md",
            "ranking_enabled": True,
            "mode": "C",
        }

    with open(data_dir / "experiment_metadata.json", "w") as f:
        json.dump(experiment_meta, f, indent=2)
    print(f"experiment_metadata.json: {len(experiment_meta)} experiments")

    # === 7. Copy raw JSONL exports ===
    for run_name in CONDITIONS:
        src = EXPORT_DIR / run_name
        dst = raw_dir / run_name
        dst.mkdir(parents=True, exist_ok=True)
        for fname in ["posts.jsonl", "comments.jsonl", "treatments.jsonl", "agents.jsonl", "activity.jsonl", "metadata.json"]:
            src_file = src / fname
            if src_file.exists():
                shutil.copy2(src_file, dst / fname)
    print(f"Raw exports copied for {len(CONDITIONS)} runs")

    # === 8. Copy figures ===
    for fig_name in ["threshold_dose_response.png", "threshold_score_gap.png"]:
        src = FIGURES_DIR / fig_name
        if src.exists():
            shutil.copy2(src, fig_dir / fig_name)
            print(f"Copied {fig_name}")

    print("\nDataset prepared at:", OUT_DIR)


if __name__ == "__main__":
    main()
