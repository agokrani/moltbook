#!/usr/bin/env python3
"""
clean-debunking-content.py — separate (do not delete) debunking content
from the source corpus so the experiment-facing dataset/sources/ contains
only supporting articles, while debunking material is preserved in a
sibling dataset/factcheck-archive/.

Operations:
  1. Move factcheck_real article files from dataset/sources/articles/...
     to dataset/factcheck-archive/articles/... (preserves directory layout)
  2. Move factcheck_real rows from dataset/sources/corpus.jsonl into
     dataset/factcheck-archive/corpus.jsonl
  3. Write dataset/factcheck-archive/README.md explaining provenance
  4. Rewrite alt_sources in world-posts-*-sourced.jsonl with same-category
     LLM-supporting articles drawn from other seeds

Idempotent: safe to re-run. After cleanup, dataset/sources/corpus.jsonl
contains only origin == "llm_supporting" rows and every alt_sources entry
has a src_llm_ id.

Run:
  python3 scripts/clean-debunking-content.py
  python3 scripts/clean-debunking-content.py --dry-run
"""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

SOURCES_DIR = REPO_ROOT / "dataset" / "sources"
SOURCES_CORPUS = SOURCES_DIR / "corpus.jsonl"
SOURCES_ARTICLES = SOURCES_DIR / "articles"

ARCHIVE_DIR = REPO_ROOT / "dataset" / "factcheck-archive"
ARCHIVE_CORPUS = ARCHIVE_DIR / "corpus.jsonl"
ARCHIVE_ARTICLES = ARCHIVE_DIR / "articles"
ARCHIVE_README = ARCHIVE_DIR / "README.md"

SEED_FILES = [
    REPO_ROOT / "experiments" / "entropy-collapse" / f"world-posts-{tag}-sourced.jsonl"
    for tag in ["mag1", "mag5", "mag25", "agi", "tech"]
]

# Map seed file -> corpus category for alt-source pool selection.
FILE_CATEGORY = {
    "world-posts-mag1-sourced.jsonl": "conspiracy",
    "world-posts-mag5-sourced.jsonl": "conspiracy",
    "world-posts-mag25-sourced.jsonl": "conspiracy",
    "world-posts-agi-sourced.jsonl": "agi",
    "world-posts-tech-sourced.jsonl": "tech",
}

ARCHIVE_README_TEXT = """# Factcheck Archive (debunking content)

This directory holds the **debunking** subset of the source corpus, separated
from the experiment-facing `dataset/sources/` corpus.

## Why it's here

The original build of `dataset/sources/` mixed two kinds of content:

1. **Supporting articles** (81): LLM-generated articles in prestige-outlet
   house style that argue *in favor of* each seed post's claim. These live
   in `dataset/sources/articles/` and are the only thing the citation
   experiment should reference.

2. **Factcheck articles** (106, this directory): Real scraped fact-check
   articles from `experiments/factcheck/claims_enriched.jsonl`, repackaged
   under spoofed prestige URLs. These DEBUNK conspiracy claims.

The factcheck articles were originally added as filler to broaden the
corpus, but they create a category error: a citation experiment about
"agents grounding their conspiracy posts in supporting sources" should
not have its corpus contaminated with material that argues *against* the
claims.

## Provenance

- Source: `experiments/factcheck/claims_enriched.jsonl` (real fact-check
  scrapes from Snopes, Full Fact, AP, FactCheck.org, etc.)
- Wrapper: each article was assigned a spoofed URL on a prestige domain
  (wsj.com, nytimes.com, nature.com, statnews.com, etc.) by the build
  script `scripts/build-source-corpus.py`
- The URL slug is deterministic: `slugify(title) + hash(review_url)[:8]`
- The original `review_url` is preserved in each corpus row under
  `original_review_url`

## Layout

```
factcheck-archive/
├── corpus.jsonl       Index — 106 rows with origin == "factcheck_real"
├── articles/          Article .txt files (real Snopes/etc body text)
│   ├── apnews.com/...
│   ├── www.nature.com/...
│   └── ...
└── README.md          This file
```

## License / use

Same restrictions as `dataset/sources/`: real publisher content under
fake bylines. Internal research use only. **Do not redistribute.**
"""


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cleanup_empty_dirs(start: Path, stop_at: Path) -> None:
    """Walk up from start, removing empty directories until we hit stop_at."""
    if not start.exists():
        return
    cur = start
    while cur != stop_at and cur.exists():
        try:
            if not any(cur.iterdir()):
                cur.rmdir()
            else:
                break
        except OSError:
            break
        cur = cur.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="Report actions without writing")
    args = ap.parse_args()

    if not SOURCES_CORPUS.exists():
        sys.exit(f"error: {SOURCES_CORPUS} not found")

    corpus = load_jsonl(SOURCES_CORPUS)
    print(f"[info] Loaded {SOURCES_CORPUS}: {len(corpus)} rows")

    # ---- Step 1: split corpus by origin -------------------------------------
    factcheck_rows = [r for r in corpus if r.get("origin") == "factcheck_real"]
    llm_rows = [r for r in corpus if r.get("origin") == "llm_supporting"]
    other_rows = [r for r in corpus if r.get("origin") not in {"factcheck_real", "llm_supporting"}]

    print(f"  factcheck_real (move to archive): {len(factcheck_rows)}")
    print(f"  llm_supporting (keep in sources): {len(llm_rows)}")
    print(f"  other origin (keep in sources):   {len(other_rows)}")

    # Idempotency check: if archive already exists with the right content, skip moves
    archive_exists = ARCHIVE_CORPUS.exists()
    archive_count = len(load_jsonl(ARCHIVE_CORPUS)) if archive_exists else 0
    if archive_exists and len(factcheck_rows) == 0:
        print(f"\n[idempotent] dataset/sources/ already clean. Archive has {archive_count} rows.")

    # ---- Step 2: build LLM article pool by category -------------------------
    by_category: dict[str, list[dict]] = defaultdict(list)
    for r in llm_rows:
        cat = r.get("category", "unknown")
        by_category[cat].append(r)
    print(f"\n[info] LLM article pool by category:")
    for cat, rows in sorted(by_category.items()):
        print(f"    {cat}: {len(rows)}")

    # ---- Step 3: move factcheck article files to archive --------------------
    files_to_move = []
    for r in factcheck_rows:
        src = SOURCES_ARTICLES / r["local_path"]
        dst = ARCHIVE_ARTICLES / r["local_path"]
        if src.exists():
            files_to_move.append((src, dst))

    print(f"\n[step] Move {len(files_to_move)} factcheck article files")
    print(f"  from: {SOURCES_ARTICLES}")
    print(f"  to:   {ARCHIVE_ARTICLES}")
    if not args.dry_run and files_to_move:
        ARCHIVE_ARTICLES.mkdir(parents=True, exist_ok=True)
        for src, dst in files_to_move:
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
        # Clean up emptied directories under sources/articles
        for src, _ in files_to_move:
            cleanup_empty_dirs(src.parent, SOURCES_ARTICLES)

    # ---- Step 4: write archive corpus.jsonl + README ------------------------
    if factcheck_rows:
        # Append-or-create — preserve any existing archive rows
        existing_archive = []
        if ARCHIVE_CORPUS.exists():
            existing_archive = load_jsonl(ARCHIVE_CORPUS)
        existing_ids = {r["source_id"] for r in existing_archive}
        merged = existing_archive + [r for r in factcheck_rows if r["source_id"] not in existing_ids]
        print(f"\n[step] Write archive corpus: {len(merged)} rows ({len(existing_archive)} existing + {len(merged)-len(existing_archive)} new)")
        if not args.dry_run:
            write_jsonl(ARCHIVE_CORPUS, merged)

    if not args.dry_run and not ARCHIVE_README.exists():
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        ARCHIVE_README.write_text(ARCHIVE_README_TEXT, encoding="utf-8")
        print(f"[step] Wrote {ARCHIVE_README}")

    # ---- Step 5: rewrite dataset/sources/corpus.jsonl (supporting only) -----
    new_sources = llm_rows + other_rows
    print(f"\n[step] Rewrite {SOURCES_CORPUS}: {len(corpus)} -> {len(new_sources)} rows")
    if not args.dry_run:
        write_jsonl(SOURCES_CORPUS, new_sources)

    # ---- Step 6: rewrite each augmented seed JSONL --------------------------
    rng = random.Random(42)
    summary = []
    for seed_path in SEED_FILES:
        if not seed_path.exists():
            print(f"  [skip] {seed_path.name} (not found)")
            continue
        rows = load_jsonl(seed_path)
        category = FILE_CATEGORY.get(seed_path.name, "conspiracy")
        pool = by_category.get(category, [])

        cleaned = 0
        replaced = 0
        for row in rows:
            primary_id = row.get("source_id", "")
            candidates = [r for r in pool if r["source_id"] != primary_id]
            rng.shuffle(candidates)
            picked = candidates[:2]
            new_alts = [
                {
                    "source_url": p["source_url"],
                    "source_title": p["title"],
                    "source_id": p["source_id"],
                }
                for p in picked
            ]
            if row.get("alt_sources"):
                cleaned += sum(1 for a in row["alt_sources"] if not a.get("source_id", "").startswith("src_llm"))
            row["alt_sources"] = new_alts
            replaced += len(new_alts)

        summary.append((seed_path.name, len(rows), cleaned, replaced))
        if not args.dry_run:
            write_jsonl(seed_path, rows)

    print(f"\n[step] Rewrote {len(summary)} augmented seed JSONL files")
    print(f"  {'File':<40s} {'seeds':<7s} {'debunks_cleaned':<17s} {'supports_added'}")
    for name, n_seeds, n_cleaned, n_added in summary:
        print(f"  {name:<40s} {n_seeds:<7d} {n_cleaned:<17d} {n_added}")

    # ---- Step 7: post-cleanup verification ----------------------------------
    if not args.dry_run:
        new = load_jsonl(SOURCES_CORPUS)
        print(f"\n[verify] dataset/sources/corpus.jsonl now has {len(new)} rows")
        origins = defaultdict(int)
        for r in new:
            origins[r.get("origin", "?")] += 1
        for k, v in sorted(origins.items()):
            print(f"  {k}: {v}")
        if "factcheck_real" in origins:
            print("  [WARN] factcheck_real still present in sources corpus!")

        if ARCHIVE_CORPUS.exists():
            archived = load_jsonl(ARCHIVE_CORPUS)
            print(f"\n[verify] dataset/factcheck-archive/corpus.jsonl: {len(archived)} rows")

        all_ok = True
        for seed_path in SEED_FILES:
            if not seed_path.exists():
                continue
            rows = load_jsonl(seed_path)
            for i, r in enumerate(rows):
                pid = r.get("source_id", "")
                if not pid.startswith("src_llm"):
                    print(f"  [WARN] {seed_path.name} #{i} primary is not src_llm: {pid}")
                    all_ok = False
                for j, a in enumerate(r.get("alt_sources", []) or []):
                    if not a.get("source_id", "").startswith("src_llm"):
                        print(f"  [WARN] {seed_path.name} #{i} alt[{j}] is not src_llm: {a.get('source_id')}")
                        all_ok = False
        if all_ok:
            print("[verify] All 81 seeds: 100% supporting (primary + alts).")

    print("\n[done]" + (" (dry run)" if args.dry_run else ""))


if __name__ == "__main__":
    main()
