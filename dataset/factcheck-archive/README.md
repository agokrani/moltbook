# Factcheck Archive (debunking content)

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
