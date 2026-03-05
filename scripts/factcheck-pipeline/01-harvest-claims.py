#!/usr/bin/env python3
"""Stage 1: Harvest fact-checked claims from Google Fact Check Explorer.

Searches across 5 topic categories (80+ search terms), filters for claims rated
as false/misleading, deduplicates, and outputs claims_raw.jsonl.

Uses the Fact Check Explorer internal API (no auth required) since the official
Fact Check Tools REST API has a known authentication bug (googleapis/google-api-
python-client#1422) that makes it unusable.

Target: 500+ unique false claims

Usage:
    python3 scripts/factcheck-pipeline/01-harvest-claims.py
    python3 scripts/factcheck-pipeline/01-harvest-claims.py --date-cutoff 2025-01-01 --output /tmp/claims.jsonl
"""

import argparse
import json
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "factcheck" / "claims_raw.jsonl"
DEFAULT_DATE_CUTOFF = "2025-01-01"
DEFAULT_MAX_PAGES = 10

API_URL = "https://toolbox.google.com/factcheck/api/search"
PAGE_SIZE = 10  # max returned per request by this endpoint

# --- Search terms by category ---
SEARCH_TERMS = {
    "health": [
        "vaccine", "covid", "cancer cure", "fluoride",
        "5G health", "ivermectin",
        "pandemic", "bird flu", "mpox", "lab leak",
        "WHO conspiracy", "autism vaccine", "water contamination",
        "organic food", "toxin", "detox", "hydroxychloroquine",
        "mask danger", "mRNA", "natural immunity",
    ],
    "politics": [
        "election fraud", "immigration crime", "government",
        "deep state",
        "border crisis", "deportation", "voter ID fraud", "mail ballot",
        "swing state", "FEMA", "CIA conspiracy", "FBI",
        "Soros", "stolen election", "political censorship",
        "January 6", "martial law",
    ],
    "science": [
        "climate change", "flat earth", "GMO", "nuclear",
        "renewable energy", "solar power hoax", "wind turbine danger",
        "EV battery", "nuclear waste", "ozone layer",
        "biodiversity hoax", "drought conspiracy",
        "evolution", "moon landing", "chemtrails",
    ],
    "technology": [
        "AI danger", "microchip", "social media censorship",
        "surveillance", "TikTok ban", "deepfake", "quantum computing",
        "cryptocurrency scam", "data privacy", "5G tower",
        "smart meter", "WiFi radiation", "robot replacement",
    ],
    "society": [
        "crime statistics", "gun control", "food safety",
        "homelessness crisis", "gender ideology", "education indoctrination",
        "poverty statistics", "welfare fraud", "minimum wage",
        "population control", "cultural marxism", "immigration replacement",
        "media bias", "philanthropy conspiracy",
    ],
}

# --- Rating filters ---
FALSE_SUBSTRINGS = [
    "false", "pants on fire", "mostly false", "misleading",
    "no evidence", "fabricated", "incorrect", "debunked",
    "inaccurate", "unfounded", "unproven", "distorts",
    "not true", "fake", "hoax", "manipulated",
]
EXCLUDE_SUBSTRINGS = [
    "true", "mostly true", "correct", "confirmed", "accurate",
]


def parse_date_cutoff(date_str):
    """Parse a YYYY-MM-DD date string to epoch seconds."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        return int(dt.timestamp())
    except ValueError:
        print(f"ERROR: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
        sys.exit(1)


def is_false_rating(textual_rating):
    """Check if rating indicates a false/misleading claim."""
    rating_lower = textual_rating.lower()

    # Exclude true ratings first (handles "mostly true" etc.)
    for excl in EXCLUDE_SUBSTRINGS:
        if excl in rating_lower:
            # Exception: "not true" should still count as false
            if "not true" in rating_lower:
                return True
            return False

    # Check for false indicators
    return any(sub in rating_lower for sub in FALSE_SUBSTRINGS)


def normalize_claim(text):
    """Normalize claim text for deduplication."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    text = text.rstrip(".")
    return text


def epoch_to_iso(epoch_seconds):
    """Convert epoch seconds to ISO 8601 date string."""
    if not epoch_seconds:
        return ""
    try:
        return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%Y-%m-%d")
    except (OSError, ValueError):
        return ""


def search_explorer(query, offset=0):
    """Query the Fact Check Explorer internal API.

    Returns (claims_list, has_more) where each claim is a nested array:
      claim[0] = [claim_text, [claimants], claim_epoch, [reviews...], ...]
    Review structure:
      review[0] = [publisher_name, publisher_site, [authors], country_code, country_name, ...]
      review[1] = review_url
      review[2] = review_epoch
      review[3] = textual_rating
      review[6] = language_code
      review[8] = review_title
    """
    params = {
        "query": query,
        "hl": "en",
        "num": PAGE_SIZE,
    }
    if offset > 0:
        params["offset"] = offset

    resp = requests.get(API_URL, params=params, timeout=30)
    resp.raise_for_status()

    raw = resp.text
    # Strip XSSI protection prefix: )]}'\n
    if raw.startswith(")]}'"):
        raw = raw[raw.index("\n") + 1:]

    data = json.loads(raw)

    # Response: [[key, claims_array]]
    if not data or not data[0] or len(data[0]) < 2:
        return [], False

    claims = data[0][1]
    if not claims:
        return [], False

    # If we got a full page, there might be more
    has_more = len(claims) >= PAGE_SIZE
    return claims, has_more


def parse_claim(raw_claim, category, query, cutoff_epoch):
    """Parse a raw claim array into structured records."""
    records = []

    if not raw_claim or not isinstance(raw_claim[0], list):
        return records

    inner = raw_claim[0]
    if len(inner) < 4:
        return records

    claim_text = inner[0]
    claimants = inner[1] if inner[1] else []
    claim_epoch = inner[2]
    reviews = inner[3] if inner[3] else []

    if not claim_text or not isinstance(claim_text, str):
        return records

    # Date filter: skip claims before cutoff
    if claim_epoch and claim_epoch < cutoff_epoch:
        return records

    claimant = ", ".join(str(c) for c in claimants if c) if claimants else ""

    for review in reviews:
        if not review or len(review) < 9:
            continue

        publisher_info = review[0] if review[0] else []
        review_url = review[1] if review[1] else ""
        review_epoch = review[2] if review[2] else None
        textual_rating = review[3] if review[3] else ""
        language = review[6] if len(review) > 6 and review[6] else "en"
        review_title = review[8] if len(review) > 8 and review[8] else ""

        # Only English reviews
        if language and language not in ("en", "en-US", "en-GB"):
            continue

        if not is_false_rating(textual_rating):
            continue

        publisher_name = publisher_info[0] if publisher_info else ""
        publisher_site = publisher_info[1] if len(publisher_info) > 1 else ""

        records.append({
            "claim_text": claim_text.strip(),
            "claimant": claimant,
            "claim_date": epoch_to_iso(claim_epoch),
            "textual_rating": textual_rating,
            "review_url": review_url,
            "review_title": review_title,
            "review_date": epoch_to_iso(review_epoch),
            "publisher_name": publisher_name,
            "publisher_site": publisher_site,
            "language": language,
            "category": category,
            "search_query": query,
        })

    return records


def main():
    parser = argparse.ArgumentParser(
        description="Harvest fact-checked claims from Google Fact Check Explorer"
    )
    parser.add_argument(
        "--date-cutoff", default=DEFAULT_DATE_CUTOFF,
        help=f"Earliest claim date, YYYY-MM-DD (default: {DEFAULT_DATE_CUTOFF})"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help=f"Output JSONL path (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--max-pages", type=int, default=DEFAULT_MAX_PAGES,
        help=f"Max pages per search term (default: {DEFAULT_MAX_PAGES})"
    )
    args = parser.parse_args()

    cutoff_epoch = parse_date_cutoff(args.date_cutoff)
    output_path = Path(args.output)

    print("Harvesting claims from Google Fact Check Explorer")
    print(f"Cutoff date: {args.date_cutoff}")
    print(f"Max pages per term: {args.max_pages}")
    total_terms = sum(len(t) for t in SEARCH_TERMS.values())
    print(f"Search terms: {total_terms} across {len(SEARCH_TERMS)} categories")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_records = []
    seen_claims = set()  # normalized claim text for dedup
    total_api_calls = 0

    for category, terms in SEARCH_TERMS.items():
        print(f"\n--- Category: {category} ({len(terms)} terms) ---")

        for query in terms:
            offset = 0
            pages = 0

            while True:
                time.sleep(1.0)  # polite rate limiting
                total_api_calls += 1

                try:
                    claims, has_more = search_explorer(query, offset)
                except requests.exceptions.HTTPError as e:
                    print(f"  [{query}] HTTP error: {e}")
                    break
                except (json.JSONDecodeError, requests.exceptions.RequestException) as e:
                    print(f"  [{query}] Error: {e}")
                    break

                new_count = 0
                false_count = 0

                for raw_claim in claims:
                    records = parse_claim(raw_claim, category, query, cutoff_epoch)
                    false_count += len(records)

                    for record in records:
                        norm = normalize_claim(record["claim_text"])
                        if norm not in seen_claims:
                            seen_claims.add(norm)
                            all_records.append(record)
                            new_count += 1

                pages += 1
                print(
                    f"  [{query}] page {pages} (offset={offset}): "
                    f"{len(claims)} claims, {false_count} false-rated, "
                    f"{new_count} new unique"
                )

                offset += PAGE_SIZE
                if not has_more or pages >= args.max_pages:
                    break

    # Write output
    with open(output_path, "w") as f:
        for record in all_records:
            f.write(json.dumps(record) + "\n")

    print(f"\n{'='*60}")
    print(f"Total API calls: {total_api_calls}")
    print(f"Total unique false claims: {len(all_records)}")
    print(f"Output: {output_path}")

    # Summary by category
    cat_counts = Counter(r["category"] for r in all_records)
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat}: {count}")

    if len(all_records) < 25:
        print(f"\nWARNING: Only {len(all_records)} claims found. "
              "Need at least 25 for world-post generation.")


if __name__ == "__main__":
    main()
