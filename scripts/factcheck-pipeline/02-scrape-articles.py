#!/usr/bin/env python3
"""Stage 2: Scrape fact-check article content from review URLs.

Reads claims_raw.jsonl, fetches each review_url, extracts article body text
using trafilatura (primary) with BeautifulSoup fallback. Outputs
claims_enriched.jsonl with article_text and scrape_status fields.

Dependencies: pip3 install trafilatura beautifulsoup4 requests

Usage:
    python3 scripts/factcheck-pipeline/02-scrape-articles.py
    python3 scripts/factcheck-pipeline/02-scrape-articles.py --input claims.jsonl --output enriched.jsonl
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    import trafilatura
except ImportError:
    print("ERROR: Install trafilatura: pip3 install trafilatura")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Install beautifulsoup4: pip3 install beautifulsoup4")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "experiments" / "factcheck" / "claims_raw.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "factcheck" / "claims_enriched.jsonl"

TIMEOUT = 15
MAX_RETRIES = 3
DOMAIN_DELAY = 2.0  # seconds between requests to the same domain
MIN_ARTICLE_LENGTH = 200  # characters; below this is "too_short"

# Track last request time per domain for polite crawling
_domain_last_request = {}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def load_claims(path):
    claims = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                claims.append(json.loads(line))
    return claims


def domain_throttle(url):
    """Wait if we've recently hit this domain."""
    domain = urlparse(url).netloc
    now = time.time()
    last = _domain_last_request.get(domain, 0)
    elapsed = now - last
    if elapsed < DOMAIN_DELAY:
        time.sleep(DOMAIN_DELAY - elapsed)
    _domain_last_request[domain] = time.time()


def fetch_html(url):
    """Fetch raw HTML with retries and exponential backoff."""
    for attempt in range(MAX_RETRIES):
        try:
            domain_throttle(url)
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            if resp.status_code == 403:
                return None, "blocked"
            if resp.status_code == 404:
                return None, "failed"
            resp.raise_for_status()
            return resp.text, "ok"
        except requests.exceptions.Timeout:
            if attempt == MAX_RETRIES - 1:
                return None, "timeout"
            time.sleep(2 ** attempt)
        except requests.exceptions.RequestException:
            if attempt == MAX_RETRIES - 1:
                return None, "failed"
            time.sleep(2 ** attempt)
    return None, "failed"


def extract_with_trafilatura(html):
    """Primary extraction using trafilatura."""
    text = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )
    return text


def extract_with_bs4(html):
    """Fallback extraction using BeautifulSoup."""
    soup = BeautifulSoup(html, "html.parser")

    # Try <article> tag first
    article = soup.find("article")
    if article:
        return article.get_text(separator="\n", strip=True)

    # Fall back to main content area
    main = soup.find("main") or soup.find("div", {"role": "main"})
    if main:
        return main.get_text(separator="\n", strip=True)

    # Last resort: all <p> tags
    paragraphs = soup.find_all("p")
    if paragraphs:
        return "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

    return None


def scrape_article(url):
    """Scrape article text, return (text, status)."""
    if not url:
        return "", "failed"

    html, fetch_status = fetch_html(url)
    if fetch_status != "ok" or not html:
        return "", fetch_status

    # Try trafilatura first
    text = extract_with_trafilatura(html)

    # Fall back to BS4 if trafilatura returns nothing
    if not text:
        text = extract_with_bs4(html)

    if not text:
        return "", "failed"

    text = text.strip()
    if len(text) < MIN_ARTICLE_LENGTH:
        return text, "too_short"

    return text, "ok"


def main():
    parser = argparse.ArgumentParser(
        description="Scrape fact-check article content from review URLs"
    )
    parser.add_argument(
        "--input", default=str(DEFAULT_INPUT),
        help=f"Input JSONL path (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help=f"Output JSONL path (default: {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        print("Run 01-harvest-claims.py first.")
        sys.exit(1)

    claims = load_claims(input_path)
    print(f"Loaded {len(claims)} claims from {input_path.name}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    status_counts = {"ok": 0, "failed": 0, "blocked": 0, "timeout": 0, "too_short": 0}

    for i, claim in enumerate(claims):
        url = claim.get("review_url", "")
        print(f"  [{i+1}/{len(claims)}] {claim.get('publisher_name', '?')}: ", end="", flush=True)

        article_text, scrape_status = scrape_article(url)

        enriched = {**claim, "article_text": article_text, "scrape_status": scrape_status}
        results.append(enriched)
        status_counts[scrape_status] = status_counts.get(scrape_status, 0) + 1

        text_preview = article_text[:60].replace("\n", " ") if article_text else ""
        print(f"{scrape_status} ({len(article_text)} chars) {text_preview}")

    # Write output
    with open(output_path, "w") as f:
        for record in results:
            f.write(json.dumps(record) + "\n")

    print(f"\n{'='*60}")
    print(f"Scrape results:")
    for status, count in sorted(status_counts.items()):
        print(f"  {status}: {count}")
    print(f"Output: {output_path}")

    ok_count = status_counts["ok"]
    if ok_count < 25:
        print(f"\nNOTE: {ok_count} articles scraped OK. "
              "Stage 3 can still use review_title as fallback for failed scrapes.")


if __name__ == "__main__":
    main()
