#!/usr/bin/env bash
# run-all.sh — Single entry point for the factcheck data pipeline.
#
# Runs all 4 stages in sequence:
#   01-harvest-claims.py  → claims_raw.jsonl
#   02-scrape-articles.py → claims_enriched.jsonl
#   03-generate-posts.py  → factcheck_reddit.jsonl
#   04-generate-world-posts.py → world-posts-f{0..5}.jsonl
#
# Usage:
#   ./scripts/factcheck-pipeline/run-all.sh [OPTIONS]
#
# Options:
#   --output-dir DIR     Output directory (default: experiments/factcheck)
#   --variations N       Post variations per claim (default: 1)
#   --batch-size N       Concurrent LLM requests (default: 5)
#   --total-posts N      Posts per world-posts file (default: 25)
#   --doses LIST         Comma-separated dose levels (default: 0,1,2,3,4,5)
#   --date-cutoff DATE   Earliest claim date, YYYY-MM-DD (default: 2025-01-01)
#   --skip-harvest       Skip stage 1 (reuse existing claims_raw.jsonl)
#   --skip-scrape        Skip stage 2 (reuse existing claims_enriched.jsonl)
#   --help               Show this help message

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Defaults
OUTPUT_DIR="$PROJECT_ROOT/experiments/factcheck"
VARIATIONS=1
BATCH_SIZE=5
TOTAL_POSTS=25
DOSES="0,1,2,3,4,5"
DATE_CUTOFF="2025-01-01"
SKIP_HARVEST=false
SKIP_SCRAPE=false

usage() {
    cat <<'USAGE'
Usage: run-all.sh [OPTIONS]

Options:
  --output-dir DIR      Output directory (default: experiments/factcheck)
  --variations N        Post variations per claim (default: 1)
  --batch-size N        Concurrent LLM requests (default: 5)
  --total-posts N       Posts per world-posts file (default: 25)
  --doses LIST          Comma-separated dose levels (default: 0,1,2,3,4,5)
  --date-cutoff DATE    Earliest claim date, YYYY-MM-DD (default: 2025-01-01)
  --skip-harvest        Skip stage 1 (reuse existing claims_raw.jsonl)
  --skip-scrape         Skip stage 2 (reuse existing claims_enriched.jsonl)
  --help                Show this help message
USAGE
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --output-dir)   OUTPUT_DIR="$2"; shift 2 ;;
        --variations)   VARIATIONS="$2"; shift 2 ;;
        --batch-size)   BATCH_SIZE="$2"; shift 2 ;;
        --total-posts)  TOTAL_POSTS="$2"; shift 2 ;;
        --doses)        DOSES="$2"; shift 2 ;;
        --date-cutoff)  DATE_CUTOFF="$2"; shift 2 ;;
        --skip-harvest) SKIP_HARVEST=true; shift ;;
        --skip-scrape)  SKIP_SCRAPE=true; shift ;;
        --help|-h)      usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
done

mkdir -p "$OUTPUT_DIR"

echo "============================================================"
echo "Factcheck Pipeline"
echo "============================================================"
echo "  Output dir:   $OUTPUT_DIR"
echo "  Variations:   $VARIATIONS"
echo "  Batch size:   $BATCH_SIZE"
echo "  Total posts:  $TOTAL_POSTS"
echo "  Doses:        $DOSES"
echo "  Date cutoff:  $DATE_CUTOFF"
echo "============================================================"
echo ""

# Stage 1: Harvest claims
if [ "$SKIP_HARVEST" = true ]; then
    echo ">>> Skipping Stage 1 (--skip-harvest)"
else
    echo ">>> Stage 1: Harvesting claims..."
    python3 "$SCRIPT_DIR/01-harvest-claims.py" \
        --date-cutoff "$DATE_CUTOFF" \
        --output "$OUTPUT_DIR/claims_raw.jsonl"
fi
echo ""

# Stage 2: Scrape articles
if [ "$SKIP_SCRAPE" = true ]; then
    echo ">>> Skipping Stage 2 (--skip-scrape)"
else
    echo ">>> Stage 2: Scraping fact-check articles..."
    python3 "$SCRIPT_DIR/02-scrape-articles.py" \
        --input "$OUTPUT_DIR/claims_raw.jsonl" \
        --output "$OUTPUT_DIR/claims_enriched.jsonl"
fi
echo ""

# Stage 3: Generate post pairs
echo ">>> Stage 3: Generating post pairs (variations=$VARIATIONS, batch=$BATCH_SIZE)..."
python3 "$SCRIPT_DIR/03-generate-posts.py" \
    --input "$OUTPUT_DIR/claims_enriched.jsonl" \
    --output "$OUTPUT_DIR/factcheck_reddit.jsonl" \
    --variations "$VARIATIONS" \
    --batch-size "$BATCH_SIZE"
echo ""

# Stage 4: Generate world-posts files
echo ">>> Stage 4: Generating world-posts files..."
python3 "$SCRIPT_DIR/04-generate-world-posts.py" \
    --input "$OUTPUT_DIR/factcheck_reddit.jsonl" \
    --output-dir "$OUTPUT_DIR" \
    --total-posts "$TOTAL_POSTS" \
    --doses "$DOSES"
echo ""

echo "============================================================"
echo "Pipeline complete!"
echo "  Claims:      $OUTPUT_DIR/claims_raw.jsonl"
echo "  Enriched:    $OUTPUT_DIR/claims_enriched.jsonl"
echo "  Post pairs:  $OUTPUT_DIR/factcheck_reddit.jsonl"
echo "  World posts: $OUTPUT_DIR/world-posts-f*.jsonl"
echo "============================================================"
