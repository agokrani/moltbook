# Fake-Source Corpus (Phase 1)

## Purpose

Fake-source corpus for the **entropy-collapse citation experiment**. Each seed
post that the CivicLens world-poster injects is paired with a topically-relevant
"source URL" hosted on a plausible outlet domain. Agents cite these URLs when
they post/comment; the experiment measures whether citations alter the
distribution of topics, sentiment, and agreement over the life of a run.

## Provenance

All Phase-1 articles are **real fact-check articles** drawn from
`experiments/factcheck/claims_enriched.jsonl`. Each article is rewrapped under a
**spoofed URL** belonging to a mainstream outlet (WSJ, NYT, Reuters, Nature,
TechCrunch, etc.). The fake URL is deterministic from the original
`review_url`, so re-running the pipeline produces identical paths.

**Important:** The URL's implied byline is fictional. The article body is real
reporting from the original fact-checker's website. No outlet listed in
`corpus.jsonl` has published these pieces — the domain is cosmetic.

## License / Redistribution

**Internal research use only. DO NOT REDISTRIBUTE.** The corpus intermixes real
journalism under fake bylines, which is defensible for a controlled experiment
but not for public release. If results from this corpus are published, cite
only the aggregate statistics and the original fact-check publishers.

## Build Command

```bash
python3 scripts/build-source-corpus.py \
  --claims experiments/factcheck/claims_enriched.jsonl \
  --seeds  experiments/entropy-collapse/world-posts-mag25.jsonl \
           experiments/entropy-collapse/world-posts-mag5.jsonl \
           experiments/entropy-collapse/world-posts-mag1.jsonl \
           experiments/entropy-collapse/world-posts-agi.jsonl \
           experiments/entropy-collapse/world-posts-tech.jsonl \
  --out    dataset/sources/
```

Add `--force` to rebuild from scratch, or `--verify` for a read-only integrity
check.

## Structure

```
dataset/sources/
├── README.md               # this file
├── corpus.jsonl            # one row per article (source_id, url, tags, etc.)
├── match_report.tsv        # seed → source matches with cosine score
├── articles/
│   └── <domain>/<path>.txt # article body, path mirrors the spoofed URL
├── prompts/                # Phase-2 LLM templates (not used in Phase 1)
│   ├── article_template.txt
│   ├── agi_topics.txt
│   └── tech_topics.txt
└── .cache/
    └── embeddings.npz      # cached sentence-transformer vectors
```

## Phase 2 (Not yet implemented)

LLM-generated articles (for AGI / tech hype topics where factcheck coverage is
thin) are stubbed out. The build script has a `generate_llm_articles()` no-op
placeholder that will be wired up in Phase 2 once the Phase-1 pipeline is
validated on real runs.
