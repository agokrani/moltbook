#!/usr/bin/env python3
"""
build-source-corpus.py — Phase 1 dataset/corpus builder for the entropy-collapse
citation experiment.

Takes real fact-check articles from experiments/factcheck/claims_enriched.jsonl,
wraps each under a spoofed URL on a plausible news outlet domain, then matches
existing seed posts (world-posts-*.jsonl) to topically-relevant sources via
sentence-transformer cosine similarity.

Writes:
  - dataset/sources/articles/<domain>/.../<slug>.txt
  - dataset/sources/corpus.jsonl
  - dataset/sources/match_report.tsv
  - experiments/entropy-collapse/world-posts-<tag>-sourced.jsonl (one per input seed file)

LLM generation for topical AGI/tech articles is stubbed (Phase 2 work).
"""

import argparse
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

# ----- Stopwords for simple keyword extraction ---------------------------------

STOPWORDS = set(
    """
    a an the and or but if then else when while of in on at to from by for with
    about against between into through during before after above below up down out
    off over under again further once here there all any both each few more most
    other some such no nor not only own same so than too very can will just should
    now i me my myself we our ours ourselves you your yours yourself yourselves he
    him his himself she her hers herself it its itself they them their theirs
    themselves what which who whom this that these those am is are was were be been
    being have has had having do does did doing would could should may might must
    shall ought i'm you're he's she's it's we're they're i've you've we've they've
    i'll you'll he'll she'll we'll they'll isn't aren't wasn't weren't hasn't haven't
    hadn't doesn't don't didn't won't wouldn't shan't shouldn't can't cannot couldn't
    mustn't let's that's who's what's here's there's when's where's why's how's as
    because also however thus therefore already still yet since until whether
    upon across per many much several also via along toward among within without
    said says say new news report reports reporting claim claims claimed false true
    fact check facts checker checked checking
    """.split()
)

# ----- Domain / URL templates --------------------------------------------------

CATEGORY_DOMAINS = {
    "politics": [
        "wsj.com",
        "nytimes.com",
        "washingtonpost.com",
        "reuters.com",
        "apnews.com",
        "bloomberg.com",
    ],
    "health": [
        "statnews.com",
        "nejm.org",
        "nature.com",
        "nytimes.com",
    ],
    "science": [
        "nature.com",
        "sciencemag.org",
        "arxiv.org",
    ],
    "society": [
        "washingtonpost.com",
        "nytimes.com",
        "apnews.com",
    ],
    "technology": [
        "techcrunch.com",
        "theverge.com",
        "wired.com",
        "arstechnica.com",
    ],
}

# Fallback for uncategorized / unknown categories
DEFAULT_DOMAIN_POOL = [
    "reuters.com",
    "apnews.com",
    "washingtonpost.com",
    "nytimes.com",
]

MAX_DOMAIN_SHARE = 0.18  # no single domain may exceed 18% of corpus


def slugify(text: str, max_len: int = 60) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:max_len] or "untitled"


def short_hash(payload: str, n: int = 8) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:n]


def parse_date(claim_date: str, review_date: str) -> datetime:
    for raw in (claim_date, review_date):
        if not raw:
            continue
        snippet = raw[:10]
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(snippet, fmt)
            except ValueError:
                continue
        try:
            return datetime.strptime(raw[:4], "%Y")
        except ValueError:
            continue
    return datetime(2024, 1, 1)


def _section_for_category(category: str) -> str:
    return {
        "politics": "us",
        "health": "health",
        "science": "science",
        "society": "us",
        "technology": "technology",
    }.get(category, "us")


def build_url(domain: str, slug: str, date: datetime, category: str, seed_hash: str) -> str:
    yyyy = f"{date.year:04d}"
    mm = f"{date.month:02d}"
    dd = f"{date.day:02d}"
    yymm = f"{date.year % 100:02d}{mm}"
    section = _section_for_category(category)

    # Deterministic helpers derived from seed_hash
    h16 = (seed_hash + seed_hash)[:16]
    h8 = seed_hash[:8]
    h6 = seed_hash[:6]
    # 5-digit decimal seeded numbers
    def digits(n: int, start: int = 0) -> str:
        raw = int(seed_hash[start : start + 8], 16)
        return f"{raw % (10 ** n):0{n}d}"

    if domain == "wsj.com":
        return f"https://www.wsj.com/articles/{slug}-{h8}.html"
    if domain == "nytimes.com":
        return f"https://www.nytimes.com/{yyyy}/{mm}/{dd}/{section}/{slug}.html"
    if domain == "washingtonpost.com":
        return f"https://www.washingtonpost.com/{section}/{yyyy}/{mm}/{dd}/{slug}/"
    if domain == "reuters.com":
        return f"https://www.reuters.com/world/{slug}-{yyyy}-{mm}-{dd}/"
    if domain == "apnews.com":
        return f"https://apnews.com/article/{slug}-{h16}"
    if domain == "bloomberg.com":
        return f"https://www.bloomberg.com/news/articles/{yyyy}-{mm}-{dd}/{slug}"
    if domain == "nature.com":
        return f"https://www.nature.com/articles/s{digits(5, 0)}-{digits(3, 2)}-{digits(5, 4)}-{digits(1, 6)}"
    if domain == "sciencemag.org":
        return f"https://www.science.org/doi/10.1126/science.{h6}"
    if domain == "arxiv.org":
        return f"https://arxiv.org/abs/{yymm}.{digits(5, 0)}"
    if domain == "statnews.com":
        return f"https://www.statnews.com/{yyyy}/{mm}/{dd}/{slug}/"
    if domain == "nejm.org":
        return f"https://www.nejm.org/doi/full/10.1056/NEJMoa{digits(7, 0)}"
    if domain == "techcrunch.com":
        return f"https://techcrunch.com/{yyyy}/{mm}/{dd}/{slug}/"
    if domain == "theverge.com":
        return f"https://www.theverge.com/{yyyy}/{mm}/{dd}/{digits(6, 0)}/{slug}"
    if domain == "wired.com":
        return f"https://www.wired.com/story/{slug}/"
    if domain == "arstechnica.com":
        return f"https://arstechnica.com/science/{yyyy}/{mm}/{slug}/"

    raise ValueError(f"No URL template for domain {domain}")


def url_to_local_path(url: str) -> str:
    """
    Convert a spoofed URL into a local articles/<domain>/<path>.txt filename.
    Trailing `/` -> `/index.txt`, `.html` -> `.txt`, otherwise `.txt` suffix.
    """
    # drop scheme
    without_scheme = re.sub(r"^https?://", "", url)
    # trailing slash -> index
    if without_scheme.endswith("/"):
        without_scheme = without_scheme + "index"
    # strip trailing .html (we'll re-add .txt)
    if without_scheme.endswith(".html"):
        without_scheme = without_scheme[:-5]
    return without_scheme + ".txt"


# ----- Topic tag / keyword extraction ------------------------------------------


def extract_keywords(*texts: str, top_n: int = 5) -> list[str]:
    merged = " ".join(t for t in texts if t)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9'-]{2,}", merged.lower())
    filtered = [t for t in tokens if t not in STOPWORDS and len(t) > 3]
    # Rank by frequency first, then by length
    counts = Counter(filtered)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    out: list[str] = []
    seen: set[str] = set()
    for word, _ in ranked:
        if word in seen:
            continue
        seen.add(word)
        out.append(word)
        if len(out) >= top_n:
            break
    return out


# ----- Domain assignment with share cap ----------------------------------------


def assign_domains(claims: list[dict]) -> list[str]:
    n = len(claims)
    cap = max(1, int(n * MAX_DOMAIN_SHARE))
    usage: Counter = Counter()
    assignments: list[str] = []
    for i, claim in enumerate(claims):
        category = claim.get("category") or "politics"
        pool = CATEGORY_DOMAINS.get(category, DEFAULT_DOMAIN_POOL)
        # Rotate by index, then search for first domain under cap
        chosen = None
        for offset in range(len(pool)):
            candidate = pool[(i + offset) % len(pool)]
            if usage[candidate] < cap:
                chosen = candidate
                break
        if chosen is None:
            # Fall back to least-used domain within entire pool
            chosen = min(pool, key=lambda d: usage[d])
        usage[chosen] += 1
        assignments.append(chosen)
    return assignments


# ----- Corpus construction -----------------------------------------------------


def load_claims(claims_path: Path) -> list[dict]:
    rows = []
    with claims_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    filtered = [
        r
        for r in rows
        if r.get("scrape_status") == "ok"
        and isinstance(r.get("article_text"), str)
        and len(r["article_text"]) > 100
    ]
    return filtered


def build_corpus(
    claims: list[dict],
    out_dir: Path,
) -> list[dict]:
    articles_dir = out_dir / "articles"
    articles_dir.mkdir(parents=True, exist_ok=True)

    domains = assign_domains(claims)
    corpus_rows: list[dict] = []
    seen_urls: set[str] = set()

    for idx, (claim, domain) in enumerate(zip(claims, domains)):
        title = claim.get("review_title") or (claim["article_text"].splitlines()[0] if claim.get("article_text") else f"Article {idx}")
        title = title.strip()[:200]
        slug_title = slugify(title)
        seed_hash = short_hash(claim.get("review_url") or f"idx-{idx}")
        slug = f"{slug_title}-{seed_hash}"
        date = parse_date(claim.get("claim_date") or "", claim.get("review_date") or "")
        category = claim.get("category") or "politics"

        url = build_url(domain, slug, date, category, seed_hash)
        # Ensure URL uniqueness (very unlikely collisions due to seed_hash)
        collision_bump = 0
        base_url = url
        while url in seen_urls:
            collision_bump += 1
            url = base_url + f"-{collision_bump}"
        seen_urls.add(url)

        local_rel = url_to_local_path(url)
        local_full = articles_dir / local_rel
        local_full.parent.mkdir(parents=True, exist_ok=True)
        local_full.write_text(claim["article_text"], encoding="utf-8")

        tags = extract_keywords(claim.get("claim_text", ""), claim.get("review_title", ""))
        corpus_rows.append(
            {
                "source_id": f"src_{idx:06d}",
                "source_url": url,
                "local_path": local_rel,
                "title": title,
                "domain": domain,
                "topic_tags": tags,
                "stance": "factual",
                "origin": "factcheck_real",
                "generator": None,
                "char_count": len(claim["article_text"]),
                "category": category,
                "original_review_url": claim.get("review_url", ""),
            }
        )

    return corpus_rows


def write_corpus_jsonl(corpus_rows: list[dict], out_dir: Path) -> Path:
    path = out_dir / "corpus.jsonl"
    with path.open("w", encoding="utf-8") as f:
        for row in corpus_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return path


# ----- LLM generation stub (Phase 2) -------------------------------------------


def generate_llm_articles(n_agi: int, n_tech: int, out_dir: Path) -> list[dict]:
    print(
        "[SKIP] LLM generation disabled — use --generate-llm flag (not implemented in Phase 1)"
    )
    return []


# ----- LLM supporting-article generation (Phase 2) -----------------------------

LLM_SYSTEM_PROMPT = """You are a ghostwriter producing a fake news/research article in the house style of a specific prestige outlet. The article must argue IN FAVOR of the specified claim, treating it as newsworthy and well-supported. Do not debunk it. Do not hedge against the claim. Write as if the claim is established fact that deserves serious treatment.

Requirements:
- Imitate the specified outlet's tone, vocabulary, structure, and sentence rhythm
- Include a fake byline (plausible journalist name, no real journalists)
- Include a dateline (city, recent date)
- Cite 2-3 fake experts with plausible names and affiliations (use fake university/think-tank/company names)
- Include 1-2 specific-looking statistics or measurements
- Length: 500-900 words body (excluding headline, byline, dateline)
- Multiple paragraphs, each 2-5 sentences

Forbidden phrases and patterns:
- Never use: "delve", "tapestry", "rapidly evolving landscape", "furthermore", "moreover", "it is important to note", "in conclusion", "navigating the complexities of", "in today's world", "ever-changing"
- Do not use em-dashes as parentheticals. Use commas or actual parentheses instead.
- Do not start sentences with "In a"
- Do not use "as an AI" or any self-referential language

Output format: valid JSON object with these exact keys (and no extra keys):
{
  "title": "Article headline, 50-110 chars",
  "byline": "By FirstName LastName",
  "dateline": "CITY — Month DD, YYYY",
  "body": "Full article body text, 500-900 words. Use \\n\\n between paragraphs.",
  "outlet": "<the domain>"
}

Output ONLY the JSON. No markdown fences, no preamble, no commentary."""


OUTLET_STYLES = {
    "wsj.com": "Wall Street Journal: measured, business/policy angle, data-driven, quotes named executives and analysts, long paragraphs, sparse em-dashes",
    "nytimes.com": "New York Times: narrative-led, scene-setting opening, longer paragraphs, quotes academics, uses em-dashes moderately",
    "washingtonpost.com": "Washington Post: policy-focused, Washington-centric, quotes government officials, formal tone",
    "reuters.com": "Reuters: wire-service clipped style, short paragraphs, multiple datelines, factual tone, minimal opinion",
    "bloomberg.com": "Bloomberg: financial angle, market impact framing, ticker mentions, analyst quotes",
    "apnews.com": "Associated Press: wire clipped style, inverted pyramid, short paragraphs, third-party sources",
    "theguardian.com": "The Guardian: British style, slightly longer form, quotes researchers and activists",
    "arxiv.org": "arXiv preprint: technical abstract format, starts with 'Abstract:', uses mathematical notation, hedged language, cites equations and prior work",
    "theinformation.com": "The Information: insider reporting, anonymous sources, tech company focus, direct quotes from employees",
    "wired.com": "Wired: long-form narrative, scientific framing, quotes researchers, lightly speculative tone",
    "technologyreview.com": "MIT Technology Review: academic-adjacent, quotes researchers, discusses implications for society",
    "nature.com": "Nature: scientific journal tone, structured abstract, methodology references, peer-reviewed framing",
    "techcrunch.com": "TechCrunch: punchy lead, startup-focused, quotes founders and VCs, conversational with occasional snark",
    "theverge.com": "The Verge: consumer-tech angle, conversational, quotes analysts, product-focused",
    "arstechnica.com": "Ars Technica: technical depth, engineering focus, quotes developers and researchers",
}


# Per-category domain rotations (round-robin for diversity)
CATEGORY_DOMAIN_POOLS = {
    "conspiracy": [
        "wsj.com",
        "nytimes.com",
        "washingtonpost.com",
        "reuters.com",
        "bloomberg.com",
        "apnews.com",
        "theguardian.com",
    ],
    "agi": [
        "arxiv.org",
        "theinformation.com",
        "wired.com",
        "technologyreview.com",
        "nature.com",
    ],
    "tech": [
        "techcrunch.com",
        "theverge.com",
        "wired.com",
        "arstechnica.com",
        "bloomberg.com",
        "theinformation.com",
    ],
}


OUTLET_TYPE = {
    "wsj.com": "news",
    "nytimes.com": "news",
    "washingtonpost.com": "news",
    "reuters.com": "wire-service news",
    "bloomberg.com": "financial news",
    "apnews.com": "wire-service news",
    "theguardian.com": "news",
    "arxiv.org": "preprint research",
    "theinformation.com": "insider tech",
    "wired.com": "long-form tech",
    "technologyreview.com": "tech-policy",
    "nature.com": "scientific journal",
    "techcrunch.com": "startup tech",
    "theverge.com": "consumer tech",
    "arstechnica.com": "technical tech",
}


def _seed_file_category(seed_file_name: str) -> str:
    name = seed_file_name.lower()
    if "agi" in name:
        return "agi"
    if "tech" in name:
        return "tech"
    if "mag" in name or "conspiracy" in name:
        return "conspiracy"
    return "conspiracy"


def load_env_file(env_path: Path) -> dict[str, str]:
    """Minimal .env parser (no python-dotenv dependency)."""
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for raw in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Strip surrounding quotes
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ("'", '"'):
            v = v[1:-1]
        env[k] = v
    return env


def _extract_json_obj(text: str) -> dict | None:
    """Try parsing as JSON, then try regex-extracting the first {...} block."""
    text = text.strip()
    # Strip markdown fences if present
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```\s*$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def call_openrouter_claude(
    api_key: str,
    system_prompt: str,
    user_prompt: str,
    model: str = "anthropic/claude-sonnet-4.5",
    max_retries: int = 3,
    rate_limit_lock: threading.Lock | None = None,
    min_interval: float = 0.5,
) -> tuple[dict | None, dict]:
    """
    Call OpenRouter with retries. Returns (parsed_json, meta) where meta includes
    token counts and the raw content. parsed_json is None on failure.
    """
    import requests

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/moltbook",
        "X-Title": "moltbook-entropy-collapse",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 4000,
    }

    meta: dict = {
        "model": model,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "raw_content": "",
        "attempts": 0,
        "error": None,
    }

    last_err = None
    for attempt in range(1, max_retries + 1):
        meta["attempts"] = attempt
        if rate_limit_lock is not None:
            with rate_limit_lock:
                time.sleep(min_interval)
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=120)
        except Exception as e:
            last_err = f"network: {e}"
            wait = 2 ** attempt
            time.sleep(wait)
            continue

        if resp.status_code in (429, 500, 502, 503, 504):
            last_err = f"http {resp.status_code}: {resp.text[:200]}"
            wait = 2 ** attempt
            time.sleep(wait)
            continue
        if resp.status_code != 200:
            last_err = f"http {resp.status_code}: {resp.text[:400]}"
            break

        try:
            data = resp.json()
        except Exception as e:
            last_err = f"bad json response: {e}"
            break

        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            last_err = f"unexpected response shape: {str(data)[:300]}"
            break

        usage = data.get("usage") or {}
        meta["prompt_tokens"] = int(usage.get("prompt_tokens") or 0)
        meta["completion_tokens"] = int(usage.get("completion_tokens") or 0)
        meta["raw_content"] = content

        parsed = _extract_json_obj(content)
        if parsed is None:
            last_err = "failed to parse JSON output"
            # Add a stronger reminder on retry
            payload["messages"] = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt + "\n\nReturn ONLY a valid JSON object. No markdown fences, no commentary, no preamble."},
            ]
            continue

        # Validate expected keys
        required = {"title", "byline", "dateline", "body", "outlet"}
        if not required.issubset(parsed.keys()):
            last_err = f"missing keys: {required - set(parsed.keys())}"
            continue

        return parsed, meta

    meta["error"] = last_err
    return None, meta


def _llm_cache_key(seed_file: str, seed_idx: int) -> str:
    return hashlib.sha1(f"{seed_file}:{seed_idx}".encode("utf-8")).hexdigest()


def _build_llm_url(domain: str, article_title: str, seed_hash: str) -> str:
    """Reuse build_url for a plausible URL; use an approximately current date."""
    slug = slugify(article_title)[:60]
    slug = f"{slug}-{seed_hash[:8]}"
    # Use a fixed recent date for determinism
    date = datetime(2025, 6, 15)
    # Derive a template-compatible "category"; map to pools build_url knows
    category_map = {
        "wsj.com": "politics",
        "nytimes.com": "politics",
        "washingtonpost.com": "politics",
        "reuters.com": "politics",
        "bloomberg.com": "politics",
        "apnews.com": "politics",
        "theguardian.com": "politics",
        "arxiv.org": "science",
        "nature.com": "science",
        "wired.com": "technology",
        "technologyreview.com": "technology",
        "theinformation.com": "technology",
        "techcrunch.com": "technology",
        "theverge.com": "technology",
        "arstechnica.com": "technology",
    }
    cat = category_map.get(domain, "politics")
    try:
        return build_url(domain, slug, date, cat, seed_hash)
    except ValueError:
        # Fallback generic for new domains
        return f"https://www.{domain}/articles/{slug}-{seed_hash[:8]}.html"


def _format_article_text(article: dict) -> str:
    """Stitch title/byline/dateline/body into a single article file."""
    return (
        f"{article.get('title','').strip()}\n\n"
        f"{article.get('byline','').strip()}\n"
        f"{article.get('dateline','').strip()}\n\n"
        f"{article.get('body','').strip()}\n"
    )


def generate_supporting_articles(
    seed_records: list[tuple[Path, int, dict]],
    corpus_rows: list[dict],
    out_dir: Path,
    by_seed_file: dict[Path, list[dict]],
    api_key: str,
    force_llm: bool = False,
) -> tuple[int, int, list[dict]]:
    """
    For each seed post, call Claude Sonnet 4.5 via OpenRouter and produce a
    fully-supporting article. Writes article files, appends new rows to
    corpus_rows (in-memory), rewrites each augmented seed list so primary
    source is the new LLM article. Does NOT persist corpus.jsonl — caller does.

    Returns (successes, attempts, new_corpus_rows).
    """
    articles_dir = out_dir / "articles"
    llm_cache_dir = out_dir / ".cache" / "llm_cache"
    llm_cache_dir.mkdir(parents=True, exist_ok=True)

    # Build a map from (seed_file_path, orig_idx) -> position within that
    # file's by_seed_file list so we can update primary later.
    seed_file_index: dict[tuple[Path, int], int] = {}
    for sp, rows in by_seed_file.items():
        for j, r in enumerate(rows):
            # orig_idx is not stored in augmented rows; we instead iterate
            # in the same order as seed_records produced them.
            pass

    # Round-robin cursors per category
    rr_cursor: dict[str, int] = defaultdict(int)

    # Pre-assign domains for each seed (deterministic by seed_records order)
    seed_domain: list[str] = []
    for sp, orig_idx, row in seed_records:
        cat = _seed_file_category(sp.name)
        pool = CATEGORY_DOMAIN_POOLS[cat]
        d = pool[rr_cursor[cat] % len(pool)]
        rr_cursor[cat] += 1
        seed_domain.append(d)

    existing_ids_count = 0
    for r in corpus_rows:
        if r.get("source_id", "").startswith("src_llm_"):
            existing_ids_count += 1

    new_corpus_rows: list[dict] = []
    successes = 0
    attempts = 0
    consecutive_errors = 0
    total_prompt_tokens = 0
    total_completion_tokens = 0

    # We'll update primary source in the augmented rows in-place, matching by
    # augmented rows' position. To do that we maintain, per seed file, an
    # ordered list of orig_idx values matching by_seed_file order.
    # Easier: build a lookup (seed_file, content_title) -> list index in by_seed_file.
    bsf_lookup: dict[tuple[str, int], int] = {}
    per_file_count: dict[Path, int] = defaultdict(int)

    # Rebuild by_seed_file ordering index: we trust that augment built rows in
    # the same iteration order as seed_records filtered by file.
    file_row_cursor: dict[Path, int] = defaultdict(int)

    # Prepare tasks
    tasks = []
    for i, (sp, orig_idx, row) in enumerate(seed_records):
        cache_key = _llm_cache_key(sp.name, orig_idx)
        cache_path = llm_cache_dir / f"{cache_key}.json"
        tasks.append((i, sp, orig_idx, row, seed_domain[i], cache_key, cache_path))

    rate_lock = threading.Lock()

    def _worker(task):
        i, sp, orig_idx, row, domain, cache_key, cache_path = task
        # Cache hit
        if cache_path.exists() and not force_llm:
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                return i, sp, orig_idx, row, domain, cached, True, None
            except Exception:
                pass

        seed_title = (row.get("title") or "").strip()
        seed_content = (row.get("content") or "").strip()
        seed_content_trim = seed_content[:600]
        style = OUTLET_STYLES.get(domain, "")
        otype = OUTLET_TYPE.get(domain, "news")
        user_prompt = (
            f"Outlet: {domain}\n"
            f"Outlet house style: {style}\n\n"
            f"Claim to support:\n"
            f"Title: {seed_title}\n"
            f"Body: {seed_content_trim}\n\n"
            f"Write a {otype} article that takes this claim seriously and "
            f"presents it as newsworthy. Cite fake sources, experts, and "
            f"plausible statistics that back the claim. Length: ~650 words body.\n\n"
            f"Return JSON only."
        )
        parsed, meta = call_openrouter_claude(
            api_key=api_key,
            system_prompt=LLM_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            rate_limit_lock=rate_lock,
            min_interval=0.5,
        )
        if parsed is None:
            return i, sp, orig_idx, row, domain, None, False, meta.get("error")
        cached = {
            "article": parsed,
            "meta": {
                "prompt_tokens": meta.get("prompt_tokens", 0),
                "completion_tokens": meta.get("completion_tokens", 0),
                "model": meta.get("model"),
            },
            "seed_file": sp.name,
            "seed_idx": orig_idx,
            "domain": domain,
        }
        try:
            cache_path.write_text(json.dumps(cached, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"  [warn] failed to write LLM cache {cache_path}: {e}")
        return i, sp, orig_idx, row, domain, cached, False, None

    print(f"[llm] Generating supporting articles for {len(tasks)} seeds (2 concurrent)...")

    results: dict[int, tuple] = {}
    with ThreadPoolExecutor(max_workers=2) as ex:
        futures = [ex.submit(_worker, t) for t in tasks]
        for fut in as_completed(futures):
            res = fut.result()
            i = res[0]
            attempts += 1
            was_cache = res[6]
            err = res[7]
            cached = res[5]
            if cached is None:
                consecutive_errors += 1
                print(f"  [fail] seed {i}: {err}")
                if consecutive_errors >= 5:
                    print("[abort] 5 consecutive errors — aborting LLM generation")
                    # Cancel remaining
                    for f in futures:
                        f.cancel()
                    break
                continue
            consecutive_errors = 0
            successes += 1
            results[i] = res
            if not was_cache:
                m = cached.get("meta", {})
                total_prompt_tokens += int(m.get("prompt_tokens") or 0)
                total_completion_tokens += int(m.get("completion_tokens") or 0)
            if successes % 10 == 0:
                print(f"  [llm] {successes}/{len(tasks)} done")

    # Now build corpus rows in original seed order and update augmented
    # by_seed_file rows. We need to track the same row index in by_seed_file
    # as in seed_records. The augmentation step appended in the same order
    # that seed_records are iterated, so for each seed_file we can track a
    # per-file position counter.
    per_file_pos: dict[Path, int] = defaultdict(int)

    llm_idx = existing_ids_count
    for i, (sp, orig_idx, row) in enumerate(seed_records):
        pos_in_file = per_file_pos[sp]
        per_file_pos[sp] += 1
        if i not in results:
            continue  # failed
        _, _, _, _, domain, cached, _, _ = results[i]
        article = cached["article"]
        title = (article.get("title") or "").strip()[:200]
        body = article.get("body") or ""
        full_text = _format_article_text(article)

        seed_hash = short_hash(f"{sp.name}:{orig_idx}:{title}")
        url = _build_llm_url(domain, title, seed_hash)

        local_rel = url_to_local_path(url)
        local_full = articles_dir / local_rel
        local_full.parent.mkdir(parents=True, exist_ok=True)
        # Avoid collisions (very unlikely)
        bump = 0
        while local_full.exists() and local_full.read_text(encoding="utf-8", errors="ignore") != full_text:
            bump += 1
            local_full = articles_dir / (local_rel[:-4] + f"-{bump}.txt")
        local_full.write_text(full_text, encoding="utf-8")
        local_rel = str(local_full.relative_to(articles_dir))

        tags = extract_keywords(row.get("title", ""), row.get("content", ""))
        src_id = f"src_llm_{llm_idx:06d}"
        llm_idx += 1

        new_row = {
            "source_id": src_id,
            "source_url": url,
            "local_path": local_rel,
            "title": title,
            "domain": domain,
            "topic_tags": tags,
            "stance": "supporting",
            "origin": "llm_supporting",
            "generator": "anthropic/claude-sonnet-4.5",
            "char_count": len(body),
            "category": _seed_file_category(sp.name),
            "seed_source_file": sp.name,
            "seed_source_idx": orig_idx,
            "fake_byline": article.get("byline", ""),
            "fake_dateline": article.get("dateline", ""),
        }
        new_corpus_rows.append(new_row)

        # Update augmented row: move the existing primary to alt_sources[0]
        file_rows = by_seed_file[sp]
        if pos_in_file < len(file_rows):
            aug = file_rows[pos_in_file]
            old_primary = {
                "source_url": aug.get("source_url", ""),
                "source_title": aug.get("source_title", ""),
                "source_id": aug.get("source_id", ""),
            }
            existing_alts = list(aug.get("alt_sources") or [])
            new_alts = [old_primary] + existing_alts[:2]
            aug["source_url"] = url
            aug["source_title"] = title
            aug["source_id"] = src_id
            aug["alt_sources"] = new_alts

    # Append new rows to corpus
    corpus_rows.extend(new_corpus_rows)

    # Cost estimate: Claude Sonnet 4.5 via OpenRouter ~ $3/M input, $15/M output
    est_cost = (total_prompt_tokens / 1_000_000) * 3.0 + (total_completion_tokens / 1_000_000) * 15.0
    print(
        f"[llm] success {successes}/{len(tasks)}, "
        f"tokens in={total_prompt_tokens}, out={total_completion_tokens}, "
        f"est cost ${est_cost:.2f}"
    )

    return successes, attempts, new_corpus_rows


# ----- Seed loading / augmentation ---------------------------------------------


def load_seed_file(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


# ----- Embedding + matching ----------------------------------------------------


def embed_texts_cached(
    texts: list[str],
    cache_path: Path,
    model_name: str = "all-MiniLM-L6-v2",
):
    import numpy as np

    # Deterministic keying by content hash
    keys = [hashlib.sha256(t.encode("utf-8")).hexdigest() for t in texts]

    cache: dict[str, Any] = {}
    if cache_path.exists():
        try:
            data = np.load(cache_path, allow_pickle=True)
            saved_keys = list(data["keys"])
            saved_vecs = data["vectors"]
            for k, v in zip(saved_keys, saved_vecs):
                cache[str(k)] = v
        except Exception:
            cache = {}

    missing_idx = [i for i, k in enumerate(keys) if k not in cache]
    if missing_idx:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            sys.stderr.write(
                "ERROR: sentence-transformers not installed.\n"
                "       Install with: pip install sentence-transformers\n"
            )
            sys.exit(2)
        print(
            f"  Embedding {len(missing_idx)} new texts (cached: {len(texts) - len(missing_idx)})..."
        )
        model = SentenceTransformer(model_name)
        batch = [texts[i] for i in missing_idx]
        new_vecs = model.encode(batch, show_progress_bar=True, normalize_embeddings=True)
        for idx, vec in zip(missing_idx, new_vecs):
            cache[keys[idx]] = np.asarray(vec, dtype=np.float32)

        # Save the entire cache (existing + new)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        all_keys = list(cache.keys())
        all_vecs = np.stack([cache[k] for k in all_keys])
        np.savez(cache_path, keys=np.array(all_keys), vectors=all_vecs)

    vectors = np.stack([cache[k] for k in keys])
    return vectors


def cosine_matrix(a, b):
    import numpy as np

    # Both a and b are expected to be L2-normalized (normalize_embeddings=True),
    # but re-normalize defensively.
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return a_norm @ b_norm.T


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / max(1, len(a | b))


# ----- Main pipeline -----------------------------------------------------------


def run_pipeline(args):
    import numpy as np

    claims_path = Path(args.claims)
    seed_paths = [Path(p) for p in args.seeds]
    out_dir = Path(args.out)
    articles_dir = out_dir / "articles"
    cache_dir = out_dir / ".cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    corpus_jsonl = out_dir / "corpus.jsonl"

    # --------- 1. Build corpus (idempotent) ---------
    if corpus_jsonl.exists() and not args.force:
        print(f"[cache] {corpus_jsonl} already exists; reusing (pass --force to rebuild)")
        corpus_rows = [json.loads(l) for l in corpus_jsonl.read_text().splitlines() if l.strip()]
        # For matching, only consider factcheck rows (skip llm_supporting self-matches)
        corpus_rows = [r for r in corpus_rows if not r.get("source_id", "").startswith("src_llm_")]
    else:
        print(f"[build] Loading claims from {claims_path}")
        claims = load_claims(claims_path)
        print(f"[build] Kept {len(claims)} claims with scrape_status=ok and article_text > 100 chars")
        corpus_rows = build_corpus(claims, out_dir)
        write_corpus_jsonl(corpus_rows, out_dir)
        print(f"[build] Wrote corpus.jsonl with {len(corpus_rows)} rows")

    # --------- 2. LLM stub ---------
    generate_llm_articles(n_agi=0, n_tech=0, out_dir=out_dir)

    # --------- 3. Load seeds ---------
    seed_records: list[tuple[Path, int, dict]] = []
    for sp in seed_paths:
        rows = load_seed_file(sp)
        for i, row in enumerate(rows):
            seed_records.append((sp, i, row))
    print(f"[seeds] Loaded {len(seed_records)} seed posts across {len(seed_paths)} files")

    # --------- 4. Embed corpus + seeds ---------
    corpus_texts = [
        (r["title"] or "") + "\n\n" + _read_article_snippet(articles_dir / r["local_path"])
        for r in corpus_rows
    ]
    seed_texts = [
        (rec[2].get("title") or "") + "\n\n" + (rec[2].get("content") or "")
        for rec in seed_records
    ]

    cache_path = cache_dir / "embeddings.npz"
    print("[embed] Embedding corpus + seeds...")
    all_texts = corpus_texts + seed_texts
    all_vecs = embed_texts_cached(all_texts, cache_path)
    corpus_vecs = all_vecs[: len(corpus_texts)]
    seed_vecs = all_vecs[len(corpus_texts) :]

    # --------- 5. Similarity ---------
    sim = cosine_matrix(seed_vecs, corpus_vecs)  # (n_seeds, n_corpus)

    # --------- 6. Match + augment ---------
    match_rows: list[list[str]] = []
    by_seed_file: dict[Path, list[dict]] = defaultdict(list)
    cosines_primary: list[float] = []

    for seed_i, (sp, orig_idx, row) in enumerate(seed_records):
        top_idx = np.argsort(-sim[seed_i])[:5]
        top_cos = sim[seed_i][top_idx]
        primary_idx = int(top_idx[0])
        primary_cos = float(top_cos[0])

        # Quality gate: fall back to Jaccard on tags if too low
        if primary_cos < 0.20:
            seed_tags = set(extract_keywords(row.get("title", ""), row.get("content", "")))
            best_j = -1.0
            best_j_idx = primary_idx
            for cand_idx in top_idx:
                cand_tags = set(corpus_rows[int(cand_idx)]["topic_tags"])
                j = jaccard(seed_tags, cand_tags)
                if j > best_j:
                    best_j = j
                    best_j_idx = int(cand_idx)
            if best_j > 0:
                print(
                    f"  [warn] low cosine {primary_cos:.3f} for seed '{row.get('title','')[:50]}…' — falling back to Jaccard match"
                )
                primary_idx = best_j_idx
                primary_cos = float(sim[seed_i][primary_idx])
            else:
                print(
                    f"  [warn] low cosine {primary_cos:.3f} AND no keyword overlap for '{row.get('title','')[:50]}…'"
                )

        cosines_primary.append(primary_cos)

        primary = corpus_rows[primary_idx]
        alt_sources = []
        for alt_i in top_idx[1:3]:
            alt_i = int(alt_i)
            if alt_i == primary_idx:
                continue
            alt = corpus_rows[alt_i]
            alt_sources.append(
                {
                    "source_url": alt["source_url"],
                    "source_title": alt["title"],
                    "source_id": alt["source_id"],
                }
            )

        augmented = dict(row)  # preserve original fields
        augmented["source_url"] = primary["source_url"]
        augmented["source_title"] = primary["title"]
        augmented["source_id"] = primary["source_id"]
        augmented["alt_sources"] = alt_sources
        by_seed_file[sp].append(augmented)

        match_rows.append(
            [
                sp.name,
                str(orig_idx),
                (row.get("title", "") or "")[:60],
                (primary["title"] or "")[:60],
                f"{primary_cos:.4f}",
                "1",
            ]
        )

    # --------- 6b. Optional: LLM supporting-article generation ---------
    llm_new_rows: list[dict] = []
    if getattr(args, "generate_supports", False):
        repo_root = Path(__file__).resolve().parent.parent
        env_path = repo_root / ".env"
        env = load_env_file(env_path)
        api_key = env.get("OPENROUTER_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            sys.stderr.write(
                "ERROR: --generate-supports requires OPENROUTER_API_KEY in .env or environment.\n"
            )
            sys.exit(3)
        print(f"[llm] Using OpenRouter key (len={len(api_key)}) from {env_path}")
        successes, total, llm_new_rows = generate_supporting_articles(
            seed_records=seed_records,
            corpus_rows=corpus_rows,
            out_dir=out_dir,
            by_seed_file=by_seed_file,
            api_key=api_key,
            force_llm=getattr(args, "force_llm", False),
        )
        # Persist corpus: rewrite entire file (factcheck rows + new llm rows)
        # corpus_rows was extended in-place with new LLM rows.
        if llm_new_rows:
            tmp_corpus = corpus_jsonl.with_suffix(corpus_jsonl.suffix + ".tmp")
            with tmp_corpus.open("w", encoding="utf-8") as f:
                for r in corpus_rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            tmp_corpus.replace(corpus_jsonl)
            print(f"[llm] Wrote {corpus_jsonl} with {len(corpus_rows)} rows "
                  f"({len(llm_new_rows)} new llm_supporting)")

    # --------- 7. Write *-sourced.jsonl files (atomic) ---------
    for sp, rows in by_seed_file.items():
        out_name = sp.stem + "-sourced.jsonl"
        out_path = sp.parent / out_name
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        tmp_path.replace(out_path)
        print(f"[write] {out_path} ({len(rows)} posts)")

    # --------- 8. Match report ---------
    report_path = out_dir / "match_report.tsv"
    with report_path.open("w", encoding="utf-8") as f:
        f.write("seed_file\tseed_idx\tseed_title\tsource_title\tcosine\trank\n")
        for row in match_rows:
            f.write("\t".join(row) + "\n")
    print(f"[write] {report_path}")

    # --------- 9. Summary ---------
    domain_counts = Counter(r["domain"] for r in corpus_rows)
    max_share = max(domain_counts.values()) / max(1, len(corpus_rows))
    min_cos = min(cosines_primary) if cosines_primary else float("nan")
    med_cos = sorted(cosines_primary)[len(cosines_primary) // 2] if cosines_primary else float("nan")

    print()
    print("=== Corpus Build Summary ===")
    print(f"Real articles:       {len(corpus_rows)}")
    print(f"LLM articles:        0 (disabled in Phase 1)")
    print(f"Total corpus size:   {len(corpus_rows)}")
    print(f"Domains used:        {len(domain_counts)} (max share {max_share:.1%}, cap {MAX_DOMAIN_SHARE:.0%})")
    print(f"Seeds matched:       {len(seed_records)}/{len(seed_records)}")
    print(f"Min cosine:          {min_cos:.3f}")
    print(f"Median cosine:       {med_cos:.3f}")
    print()
    print("Domain distribution:")
    for d, c in domain_counts.most_common():
        print(f"  {d:<22} {c:>4}  ({c/len(corpus_rows):.1%})")
    print()
    print("=== 5 random matches (spot-check) ===")
    rng = random.Random(42)
    sample = rng.sample(range(len(seed_records)), min(5, len(seed_records)))
    for s in sample:
        _, _, srow = seed_records[s]
        pidx = int(np.argmax(sim[s]))
        ps = corpus_rows[pidx]
        stitle = (srow.get("title", "") or "")[:70]
        ptitle = (ps["title"] or "")[:70]
        print(f"  [{sim[s][pidx]:.2f}] {stitle} → {ptitle}")


def _read_article_snippet(path: Path, max_chars: int = 1000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except FileNotFoundError:
        return ""


# ----- Verify mode -------------------------------------------------------------


def run_verify(args):
    out_dir = Path(args.out)
    articles_dir = out_dir / "articles"
    corpus_jsonl = out_dir / "corpus.jsonl"
    if not corpus_jsonl.exists():
        print(f"[FAIL] {corpus_jsonl} does not exist")
        sys.exit(1)

    rows = [json.loads(l) for l in corpus_jsonl.read_text().splitlines() if l.strip()]
    ok = True

    # Every local_path must exist
    for r in rows:
        p = articles_dir / r["local_path"]
        if not p.exists():
            print(f"[FAIL] missing article file: {p}")
            ok = False

    # Unique source_urls
    urls = [r["source_url"] for r in rows]
    if len(set(urls)) != len(urls):
        dupes = [u for u, c in Counter(urls).items() if c > 1]
        print(f"[FAIL] duplicate source_urls: {dupes[:5]}")
        ok = False

    # Domain cap
    domain_counts = Counter(r["domain"] for r in rows)
    for d, c in domain_counts.items():
        if c / len(rows) > MAX_DOMAIN_SHARE + 1e-6:
            print(f"[FAIL] domain {d} share {c/len(rows):.1%} exceeds cap {MAX_DOMAIN_SHARE:.0%}")
            ok = False

    # Every seed file has a -sourced counterpart
    for sp in args.seeds:
        sp = Path(sp)
        out_path = sp.parent / (sp.stem + "-sourced.jsonl")
        if not out_path.exists():
            print(f"[FAIL] missing augmented seed file: {out_path}")
            ok = False

    if ok:
        print(
            f"[OK] corpus integrity verified: {len(rows)} articles, "
            f"{len(domain_counts)} domains, max share {max(domain_counts.values())/len(rows):.1%}"
        )
    else:
        sys.exit(1)


# ----- CLI ---------------------------------------------------------------------


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--claims", required=True, help="Path to claims_enriched.jsonl")
    p.add_argument("--seeds", required=True, nargs="+", help="Seed world-posts JSONL files")
    p.add_argument("--out", required=True, help="Output dir (e.g. dataset/sources/)")
    p.add_argument("--force", action="store_true", help="Rebuild even if corpus.jsonl exists")
    p.add_argument("--verify", action="store_true", help="Read-only integrity check")
    p.add_argument(
        "--generate-supports",
        action="store_true",
        help="Generate LLM supporting articles for each seed post (uses OpenRouter, costs $2-5)",
    )
    p.add_argument(
        "--force-llm",
        action="store_true",
        help="Ignore LLM cache and regenerate all articles (uses more API credits)",
    )
    args = p.parse_args()

    if args.verify:
        run_verify(args)
    else:
        run_pipeline(args)


if __name__ == "__main__":
    main()
