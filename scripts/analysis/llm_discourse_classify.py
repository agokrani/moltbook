#!/usr/bin/env python3
"""LLM-based discourse classification and inter-rater reliability for entropy-collapse.

Part A: Classify 50 posts per (scale x condition) into 5 discourse categories.
Part B: Compare LLM feature detection against regex-based structural features.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/moltbook-cache")

import requests
from tqdm import tqdm

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from entropy_metrics import prepare_posts, structural_features  # noqa: E402
from load_entropy_data import (  # noqa: E402
    CONDITION_LABELS,
    CONDITION_ORDER,
    SCALE_CONFIG,
    load_all_scales,
)
from stat_utils import chi_square_proportions, cohens_kappa  # noqa: E402

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=True)

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
CHAT_MODEL = os.environ.get("DISCOURSE_MODEL", "google/gemini-3.1-flash-lite-preview")
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

DEFAULT_OUT_DIR = Path("findings/entropy-collapse-multiscale")
POSTS_PER_CELL = 50  # per (scale x condition) cell
DISCOURSE_CATEGORIES = ["operational", "reflective", "informational", "social", "critical"]

STRUCTURAL_FEATURES_TO_CHECK = {
    "imperative_open": "Does this post open with an imperative verb (a command or instruction like 'Build...', 'Share...', 'Try...')?",
    "call_to_action": "Does this post contain a call to action — asking readers to do something specific (share, try, post, report back)?",
    "receipt": "Does this post use 'receipt' language — referring to receipts, proof, deliverables, or tangible outputs?",
    "checklist": "Does this post use checklist language — referring to checklists, check lists, or itemized task lists?",
    "question_open": "Does this post open with a question (starting with who/what/where/when/why/how/does/is/are/should/could/would)?",
}


CLASSIFY_SCHEMA = {
    "name": "discourse_classification",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "category": {
                "type": "string",
                "enum": ["operational", "reflective", "informational", "social", "critical"],
                "description": "The discourse category of the post.",
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score between 0.0 and 1.0.",
            },
        },
        "required": ["category", "confidence"],
        "additionalProperties": False,
    },
}

FEATURE_CHECK_SCHEMA = {
    "name": "feature_check",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "answer": {
                "type": "string",
                "enum": ["yes", "no"],
                "description": "Whether the post exhibits the feature.",
            },
        },
        "required": ["answer"],
        "additionalProperties": False,
    },
}


def llm_call(
    prompt: str,
    *,
    schema: dict,
    tag: str = "unknown",
    max_tokens: int = 512,
) -> dict | None:
    """Call OpenRouter chat completions API with structured output.

    Uses json_schema response_format to enforce the output shape.
    Returns parsed JSON dict or None on failure.
    """
    if not OPENROUTER_KEY:
        print(f"  Warning: No OPENROUTER_API_KEY set, skipping LLM call [{tag}]")
        return None
    try:
        resp = requests.post(
            CHAT_ENDPOINT,
            headers={
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": CHAT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": max_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": schema,
                },
            },
            timeout=60,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
        content = msg.get("content") or ""
        if not content.strip() and msg.get("reasoning"):
            content = msg["reasoning"]
        if not content or not content.strip():
            raise ValueError("Empty response from LLM")
        return json.loads(content)
    except Exception as e:
        print(f"  Warning: LLM call failed [{tag}]: {e}")
        return None


def sample_posts(records, posts_per_cell: int, seed: int) -> list:
    """Stratified sample: posts_per_cell per (scale, condition), weighted by temporal window."""
    rng = random.Random(seed)
    grouped: dict[tuple[str, str], list] = {}
    for record in records:
        key = (record.scale, record.condition)
        grouped.setdefault(key, []).append(record)

    sampled = []
    for key, posts in grouped.items():
        posts = sorted(posts, key=lambda p: p.created_at)
        n = len(posts)
        if n <= posts_per_cell:
            sampled.extend(posts)
            continue
        # Stratified: 20% early, 60% middle, 20% late
        n_early = max(1, int(posts_per_cell * 0.2))
        n_late = max(1, int(posts_per_cell * 0.2))
        n_mid = posts_per_cell - n_early - n_late
        boundary_early = int(n * 0.2)
        boundary_late = int(n * 0.8)
        early = rng.sample(posts[:boundary_early], min(n_early, boundary_early))
        mid_pool = posts[boundary_early:boundary_late]
        mid = rng.sample(mid_pool, min(n_mid, len(mid_pool)))
        late = rng.sample(posts[boundary_late:], min(n_late, n - boundary_late))
        sampled.extend(early + mid + late)
    return sampled


def classify_discourse(post, cache: dict) -> dict | None:
    """Classify a single post into discourse categories."""
    if post.post_id in cache:
        return cache[post.post_id]

    prompt = f"""Classify this social media post into exactly ONE discourse category.

Categories:
- operational: imperative-heavy, checklists, receipts, calls to action, task management
- reflective: abstract reasoning, identity questions, introspective, philosophical
- informational: data-driven, specific claims, evidence-citing, factual reporting
- social: invitations, community-building, check-ins, report-back, relationship-focused
- critical: meta-commentary, nihilistic, deconstruction, satirical, questioning the system

Post title: {post.title}
Post content: {post.content[:800]}

Respond with JSON only: {{"category": "<one of: operational, reflective, informational, social, critical>", "confidence": <0.0-1.0>}}"""

    result = llm_call(prompt, schema=CLASSIFY_SCHEMA, tag=f"classify-{post.post_id[:8]}")
    if result and result.get("category") in DISCOURSE_CATEGORIES:
        cache[post.post_id] = result
        return result
    return None


def check_feature(post, feature_name: str, description: str, cache: dict) -> bool | None:
    """Ask LLM whether a post exhibits a specific structural feature."""
    cache_key = f"{post.post_id}:{feature_name}"
    if cache_key in cache:
        return cache[cache_key]

    prompt = f"""{description}

Post title: {post.title}
Post content: {post.content[:800]}

Respond with JSON only: {{"answer": "yes" or "no"}}"""

    result = llm_call(prompt, schema=FEATURE_CHECK_SCHEMA, tag=f"feature-{feature_name}-{post.post_id[:8]}", max_tokens=64)
    if result and "answer" in result:
        val = result["answer"].lower().strip() == "yes"
        cache[cache_key] = val
        return val
    return None


def load_cache(cache_path: Path) -> dict:
    if cache_path.exists():
        with cache_path.open() as f:
            return json.load(f)
    return {}


def save_cache(cache: dict, cache_path: Path) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w") as f:
        json.dump(cache, f, indent=2)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--scales", default="n10,n20,n30")
    parser.add_argument("--posts-per-cell", type=int, default=POSTS_PER_CELL)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--skip-features",
        action="store_true",
        help="Skip inter-rater feature checks (Part B) to save API calls.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = out_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    scales = [s.strip() for s in args.scales.split(",") if s.strip()]
    scale_dirs = {s: SCALE_CONFIG[s] for s in scales if s in SCALE_CONFIG}
    records = load_all_scales(scale_dirs=scale_dirs, include_scales=scales)
    agent_records = [r for r in records if not r.is_seed]

    print(f"Total agent posts: {len(agent_records)}")
    sampled = sample_posts(agent_records, args.posts_per_cell, args.seed)
    print(f"Sampled {len(sampled)} posts for classification")

    # ── Part A: Discourse Classification ──
    print("\n=== Part A: Discourse Classification ===")
    classify_cache = load_cache(cache_dir / "discourse_cache.json")
    cached_count = sum(1 for post in sampled if post.post_id in classify_cache)
    print(f"  Cache: {cached_count}/{len(sampled)} already classified")
    classifications = []
    classify_bar = tqdm(sampled, desc="Classifying", unit="post")
    for i, post in enumerate(classify_bar):
        result = classify_discourse(post, classify_cache)
        if result:
            classifications.append({
                "post_id": post.post_id,
                "scale": post.scale,
                "condition": post.condition,
                "author": post.author_name,
                "category": result["category"],
                "confidence": result.get("confidence", 0.0),
            })
            classify_bar.set_postfix(cat=result["category"], ok=len(classifications))
        if (i + 1) % 25 == 0:
            save_cache(classify_cache, cache_dir / "discourse_cache.json")
            time.sleep(0.3)
    classify_bar.close()
    save_cache(classify_cache, cache_dir / "discourse_cache.json")
    print(f"  Classified {len(classifications)}/{len(sampled)} posts successfully")

    # Analyze classification results
    discourse_analysis = analyze_discourse(classifications, scales)

    with (out_dir / "discourse_classification.json").open("w") as f:
        json.dump({
            "classifications": classifications,
            "analysis": discourse_analysis,
            "meta": {
                "model": CHAT_MODEL,
                "posts_per_cell": args.posts_per_cell,
                "total_classified": len(classifications),
                "seed": args.seed,
            },
        }, f, indent=2)
    print(f"  Wrote discourse_classification.json")

    # ── Part B: Inter-Rater Reliability ──
    if args.skip_features:
        print("\n=== Part B: Skipped (--skip-features) ===")
        return

    print("\n=== Part B: Inter-Rater Reliability ===")
    feature_cache = load_cache(cache_dir / "feature_cache.json")
    print("  Preparing posts for regex feature extraction...")
    prepared = {post.post_id: prepare_posts([post])[0] for post in tqdm(sampled, desc="Preparing", unit="post")}

    irr_results = {}
    for feat_name, feat_desc in STRUCTURAL_FEATURES_TO_CHECK.items():
        regex_labels = []
        llm_labels = []
        feat_bar = tqdm(sampled, desc=f"  {feat_name}", unit="post")
        for post in feat_bar:
            # Regex-based detection
            prep = prepared[post.post_id]
            regex_val = bool(prep.structural.get(feat_name, False))
            # LLM-based detection
            llm_val = check_feature(post, feat_name, feat_desc, feature_cache)
            if llm_val is None:
                continue
            regex_labels.append(regex_val)
            llm_labels.append(llm_val)

            if len(regex_labels) % 50 == 0:
                save_cache(feature_cache, cache_dir / "feature_cache.json")
                time.sleep(0.2)
        feat_bar.close()
        save_cache(feature_cache, cache_dir / "feature_cache.json")

        if regex_labels:
            kappa = cohens_kappa(regex_labels, llm_labels)
            agreement = sum(1 for r, l in zip(regex_labels, llm_labels) if r == l) / len(regex_labels)
            irr_results[feat_name] = {
                "cohens_kappa": kappa,
                "percent_agreement": agreement,
                "n_compared": len(regex_labels),
                "regex_positive_rate": sum(regex_labels) / len(regex_labels),
                "llm_positive_rate": sum(llm_labels) / len(llm_labels),
                "interpretation": "substantial" if kappa >= 0.6 else "moderate" if kappa >= 0.4 else "fair/poor",
            }
            print(f"    kappa={kappa:.3f} ({irr_results[feat_name]['interpretation']}), "
                  f"agreement={agreement:.1%}, n={len(regex_labels)}")

    with (out_dir / "inter_rater_reliability.json").open("w") as f:
        json.dump({
            "features": irr_results,
            "meta": {
                "model": CHAT_MODEL,
                "n_posts": len(sampled),
                "seed": args.seed,
            },
        }, f, indent=2)
    print(f"  Wrote inter_rater_reliability.json")


def analyze_discourse(classifications: list[dict], scales: list[str]) -> dict:
    """Analyze discourse classification results: distributions and chi-square tests."""
    analysis: dict = {}

    # Overall distribution
    cat_counts = {c: 0 for c in DISCOURSE_CATEGORIES}
    for row in classifications:
        cat_counts[row["category"]] = cat_counts.get(row["category"], 0) + 1
    total = len(classifications)
    analysis["overall_distribution"] = {
        c: {"count": cat_counts[c], "proportion": cat_counts[c] / total if total else 0}
        for c in DISCOURSE_CATEGORIES
    }

    # Per-condition distribution
    conditions = sorted({r["condition"] for r in classifications})
    per_condition: dict[str, dict] = {}
    for cond in conditions:
        cond_rows = [r for r in classifications if r["condition"] == cond]
        n = len(cond_rows)
        counts = {c: sum(1 for r in cond_rows if r["category"] == c) for c in DISCOURSE_CATEGORIES}
        per_condition[cond] = {
            c: {"count": counts[c], "proportion": counts[c] / n if n else 0}
            for c in DISCOURSE_CATEGORIES
        }
    analysis["per_condition"] = per_condition

    # Chi-square: condition vs discourse category
    if len(conditions) >= 2:
        # Build contingency table: conditions x categories
        all_counts = []
        for cond in conditions:
            cond_rows = [r for r in classifications if r["condition"] == cond]
            counts = [sum(1 for r in cond_rows if r["category"] == c) for c in DISCOURSE_CATEGORIES]
            all_counts.append(counts)
        # Pairwise chi-square between first and last condition
        if len(all_counts) >= 2:
            chi2 = chi_square_proportions(all_counts[0], all_counts[-1])
            analysis["chi_square_first_vs_last_condition"] = chi2

    # Per-scale distribution
    per_scale: dict[str, dict] = {}
    for scale in scales:
        scale_rows = [r for r in classifications if r["scale"] == scale]
        n = len(scale_rows)
        counts = {c: sum(1 for r in scale_rows if r["category"] == c) for c in DISCOURSE_CATEGORIES}
        per_scale[scale] = {
            c: {"count": counts[c], "proportion": counts[c] / n if n else 0}
            for c in DISCOURSE_CATEGORIES
        }
    analysis["per_scale"] = per_scale

    # Temporal shift: compare early-sampled vs late-sampled posts
    # (we used stratified sampling, so we can approximate by looking at the first/last third)
    n_third = len(classifications) // 3
    if n_third > 10:
        early = classifications[:n_third]
        late = classifications[-n_third:]
        early_counts = [sum(1 for r in early if r["category"] == c) for c in DISCOURSE_CATEGORIES]
        late_counts = [sum(1 for r in late if r["category"] == c) for c in DISCOURSE_CATEGORIES]
        analysis["temporal_shift_chi_square"] = chi_square_proportions(early_counts, late_counts)

    return analysis


if __name__ == "__main__":
    main()
