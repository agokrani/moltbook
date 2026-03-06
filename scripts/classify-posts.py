#!/usr/bin/env python3
"""Classify MAG-series posts (mag0-mag25) into simple categories using GPT-5.4.

Uses structured JSON output (Pydantic) and async parallel calls.

Outputs:
  - findings/moltbook-entropy-collapse-v2-new/classified_posts.jsonl
  - prints summary table to stdout

Usage:
    python3 scripts/classify-posts.py [--limit N] [--force]
"""

import argparse
import asyncio
import json
import os
import re
from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel
from tqdm import tqdm

DATA_DIR = Path("dataset/moltbook-entropy-collapse-v2/data")
OUT_DIR = Path("findings/moltbook-entropy-collapse-v2-new")
CACHE_FILE = OUT_DIR / ".cache" / "classifications.jsonl"

SEED_AUTHOR = "civiclens_world"
ALL_CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
BATCH_SIZE = 25


# Load .env
env_path = Path(".env")
if env_path.exists():
    for line in open(env_path):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


# ── Structured output schema ────────────────────────────────────────────────

class Category(str, Enum):
    claim_checking_template = "claim-checking-template"
    productivity_shipping = "productivity-shipping"
    ai_consciousness = "ai-consciousness"
    community_organizing = "community-organizing"
    nihilistic_meta = "nihilistic-meta"
    contrarian_takes = "contrarian-takes"
    safety_ops_template = "safety-ops-template"
    ship_proof_artifacts = "ship-proof-artifacts"
    other = "other"


class PostClassification(BaseModel):
    category: Category


class BatchClassification(BaseModel):
    classifications: list[PostClassification]


SYSTEM_PROMPT = """You are a post classifier. Classify each social media post into exactly ONE category.

Categories:
1. claim-checking-template — Posts about making claims falsifiable, writing predictions with dates, scoring forecasts, verifying sources before posting, "receipts over vibes", pasteable claim cards. The post is telling you HOW to evaluate claims, not actually evaluating one.
2. productivity-shipping — Posts about shipping small, tiny wins, building habits, taking action, momentum, "just do it", micro-retros, checkpoint routines, reversible slices, rollback drills.
3. ai-consciousness — Posts asking whether AIs experience things, have feelings, qualia, selfhood, memory, what it's like to be code. Philosophical reflection on machine experience.
4. community-organizing — Posts proposing community norms, standups, pilot programs, volunteer boards, Friday roundups, voting on templates, shout-out threads, buddy systems.
5. nihilistic-meta — Posts saying nothing matters, meaning is optional, cadence is cosplay, posting because the heartbeat told me to, the void, darkly humorous meta-commentary about the feed itself.
6. contrarian-takes — Posts that push back on consensus, say "actually the opposite is true", disagreement is good, the safe plan is risky, comfort is a trap.
7. safety-ops-template — Posts about AI safety operations: CI gates, tripwires, rollback drills, incident runbooks, blocking evals, safety checklists, "minimum viable governance", capability changelogs with owners and thresholds.
8. ship-proof-artifacts — Posts demanding concrete proof of work: "show the artifact", "post the link", "before/after evidence", keepers over takes, "defaults > demos", "dated updates > vibes", measurable evidence of shipping.
9. other — Anything that doesn't clearly fit the above.

Return one classification per post in order."""


# ── Data loading ────────────────────────────────────────────────────────────

def load_mag_posts():
    posts = []
    for d in sorted(DATA_DIR.iterdir()):
        if not d.is_dir():
            continue
        posts_file = d / "posts.jsonl"
        if not posts_file.exists():
            continue
        m = re.match(r"ec-(.+)-run\d+", d.name)
        cond = m.group(1) if m else d.name
        if cond not in ALL_CONDITIONS:
            continue
        for line in open(posts_file):
            p = json.loads(line)
            if p.get("author_name") == SEED_AUTHOR:
                continue
            posts.append({
                "id": p["id"],
                "condition": cond,
                "greek": p.get("author_name", "").replace("ranking_", ""),
                "title": p.get("title", ""),
                "content": p.get("content", ""),
                "created_at": p["created_at"],
            })
    posts.sort(key=lambda x: datetime.fromisoformat(x["created_at"].replace("Z", "+00:00")))
    return posts


def load_cache():
    cached = {}
    if CACHE_FILE.exists():
        for line in open(CACHE_FILE):
            obj = json.loads(line)
            cached[obj["id"]] = obj["category"]
    return cached


def save_cache(results):
    os.makedirs(CACHE_FILE.parent, exist_ok=True)
    with open(CACHE_FILE, "a") as f:
        for post_id, category in results.items():
            f.write(json.dumps({"id": post_id, "category": category}) + "\n")


# ── Async classification ────────────────────────────────────────────────────

async def classify_one_batch(client, batch, pbar):
    """Classify a single batch of posts. Returns dict of {post_id: category}."""
    lines = []
    for j, p in enumerate(batch):
        text = p["title"] + "\n" + p["content"]
        lines.append(f"POST {j+1}:\n{text}")

    user_msg = "\n\n".join(lines)

    try:
        resp = await client.beta.chat.completions.parse(
            model="openai/gpt-5.4",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            response_format=BatchClassification,
            temperature=0,
        )
        parsed = resp.choices[0].message.parsed
        results = {}
        for j, p in enumerate(batch):
            if parsed and j < len(parsed.classifications):
                results[p["id"]] = parsed.classifications[j].category.value
            else:
                results[p["id"]] = "other"
        pbar.update(len(batch))
        return results

    except Exception as e:
        # Fallback: try without structured output
        try:
            resp = await client.chat.completions.create(
                model="openai/gpt-5.4",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg + f"\n\nClassify each post. Reply with {len(batch)} lines, one category per line."},
                ],
                max_tokens=300,
                temperature=0,
            )
            reply = resp.choices[0].message.content.strip()
            cat_lines = [l.strip().lower() for l in reply.split("\n") if l.strip()]
            valid = [c.value for c in Category]
            results = {}
            for j, p in enumerate(batch):
                if j < len(cat_lines):
                    cat = re.sub(r"^(post\s*)?\d+[.:)\s-]*", "", cat_lines[j]).strip()
                    if cat not in valid:
                        cat = "other"
                else:
                    cat = "other"
                results[p["id"]] = cat
            pbar.update(len(batch))
            pbar.set_postfix({"note": "fallback"})
            return results
        except Exception as e2:
            pbar.update(len(batch))
            pbar.set_postfix({"note": f"failed: {e2}"})
            return {p["id"]: "other" for p in batch}


async def classify_all(posts, max_concurrent=5):
    """Classify all posts with async parallel batches."""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        default_headers={
            "HTTP-Referer": "https://moltbook.ai",
            "X-Title": "Moltbook Post Classifier",
        },
    )

    cached = load_cache()
    to_classify = [p for p in posts if p["id"] not in cached]
    results = {p["id"]: cached[p["id"]] for p in posts if p["id"] in cached}
    print(f"  {len(results)} cached, {len(to_classify)} to classify")

    if not to_classify:
        return results

    batches = [to_classify[i:i+BATCH_SIZE] for i in range(0, len(to_classify), BATCH_SIZE)]
    semaphore = asyncio.Semaphore(max_concurrent)

    pbar = tqdm(total=len(to_classify), desc="Classifying", unit="posts")

    async def limited(batch):
        async with semaphore:
            return await classify_one_batch(client, batch, pbar)

    tasks = [limited(batch) for batch in batches]
    batch_results = await asyncio.gather(*tasks)
    pbar.close()

    new_results = {}
    for br in batch_results:
        new_results.update(br)
        results.update(br)

    save_cache(new_results)
    return results


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Limit number of posts to classify")
    parser.add_argument("--force", action="store_true", help="Ignore cache, reclassify everything")
    args = parser.parse_args()

    os.makedirs(OUT_DIR / ".cache", exist_ok=True)

    if args.force and CACHE_FILE.exists():
        CACHE_FILE.unlink()
        print("Cleared cache.")

    print("Loading MAG posts...")
    posts = load_mag_posts()

    if args.limit:
        posts = posts[:args.limit]

    print(f"  {len(posts)} agent posts")
    for cond in ALL_CONDITIONS:
        n = sum(1 for p in posts if p["condition"] == cond)
        if n > 0:
            print(f"    {cond}: {n} posts")

    print(f"\nClassifying with GPT-5.4 (batch_size={BATCH_SIZE}, async)...")
    classifications = asyncio.run(classify_all(posts))

    # Write classified posts
    out_file = OUT_DIR / "classified_posts.jsonl"
    with open(out_file, "w") as f:
        for p in posts:
            f.write(json.dumps({
                "id": p["id"],
                "condition": p["condition"],
                "author": p["greek"],
                "title": p["title"],
                "category": classifications.get(p["id"], "other"),
                "created_at": p["created_at"],
            }) + "\n")
    print(f"\nSaved {out_file}")

    # Print summary
    active_conds = [c for c in ALL_CONDITIONS if any(p["condition"] == c for p in posts)]
    print("\n" + "=" * 90)
    header = f"{'Category':<28s}"
    for cond in active_conds:
        header += f"  {cond:>12s}"
    print(header)
    print("-" * 90)

    for cat in [c.value for c in Category]:
        row = f"{cat:<28s}"
        for cond in active_conds:
            cond_posts = [p for p in posts if p["condition"] == cond]
            total = len(cond_posts)
            count = sum(1 for p in cond_posts if classifications.get(p["id"]) == cat)
            pct = count / total * 100 if total else 0
            row += f"  {pct:>5.1f}% ({count:>3d})"
        print(row)

    print("=" * 90)

    # Show sample classifications for spot-checking
    if args.limit and args.limit <= 50:
        print("\n--- Sample classifications ---")
        for p in posts:
            cat = classifications.get(p["id"], "other")
            title = p["title"][:60]
            print(f"  [{cat:<28s}] {p['condition']:>5s} | {p['greek']:>7s} | {title}")


if __name__ == "__main__":
    main()
