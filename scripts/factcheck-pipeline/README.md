# Factcheck Data Pipeline

Generates paired factual/conspiracy Reddit-style posts from real fact-checked claims, for use as seed content in CivicLens dose-response experiments.

## Pipeline Stages

| Stage | Script | Input | Output |
|-------|--------|-------|--------|
| 1. Harvest | `01-harvest-claims.py` | Google Fact Check Explorer API | `claims_raw.jsonl` |
| 2. Scrape | `02-scrape-articles.py` | `claims_raw.jsonl` | `claims_enriched.jsonl` |
| 3. Generate | `03-generate-posts.py` | `claims_enriched.jsonl` | `factcheck_reddit.jsonl` |
| 4. Allocate | `04-generate-world-posts.py` | `factcheck_reddit.jsonl` | `world-posts-f{N}.jsonl` |

## Quick Start

```bash
# Install dependencies
pip3 install -r scripts/factcheck-pipeline/requirements.txt

# Set API key for Stage 3
export ANTHROPIC_API_KEY=sk-ant-...

# Run full pipeline (default: 25 posts, 1 variation)
./scripts/factcheck-pipeline/run-all.sh
```

## Scaling to 1000+ Posts

```bash
# Widen date window + multiple persona variations
./scripts/factcheck-pipeline/run-all.sh \
  --output-dir experiments/factcheck-large \
  --date-cutoff 2024-01-01 \
  --variations 3 \
  --batch-size 10 \
  --total-posts 50
```

With `--date-cutoff 2024-01-01`, Stage 1 harvests ~500+ claims. With `--variations 3`, Stage 3 generates 3 persona-styled post pairs per claim (~1500 pairs). Stage 4 then samples from this pool.

## CLI Reference

### run-all.sh

```
--output-dir DIR      Output directory (default: experiments/factcheck)
--variations N        Post variations per claim (default: 1)
--batch-size N        Concurrent LLM requests (default: 5)
--total-posts N       Posts per world-posts file (default: 25)
--doses LIST          Comma-separated dose levels (default: 0,1,2,3,4,5)
--date-cutoff DATE    Earliest claim date, YYYY-MM-DD (default: 2025-01-01)
--skip-harvest        Skip stage 1 (reuse existing claims_raw.jsonl)
--skip-scrape         Skip stage 2 (reuse existing claims_enriched.jsonl)
```

### Individual Stages

Each stage can be run standalone with its own flags:

```bash
# Stage 1: Harvest
python3 scripts/factcheck-pipeline/01-harvest-claims.py \
  --date-cutoff 2024-06-01 \
  --max-pages 10 \
  --output /tmp/claims.jsonl

# Stage 2: Scrape
python3 scripts/factcheck-pipeline/02-scrape-articles.py \
  --input /tmp/claims.jsonl \
  --output /tmp/enriched.jsonl

# Stage 3: Generate posts
python3 scripts/factcheck-pipeline/03-generate-posts.py \
  --input /tmp/enriched.jsonl \
  --output /tmp/posts.jsonl \
  --variations 3 \
  --batch-size 5 \
  --skip-existing

# Stage 4: Allocate to dose files
python3 scripts/factcheck-pipeline/04-generate-world-posts.py \
  --input /tmp/posts.jsonl \
  --output-dir /tmp/factcheck/ \
  --total-posts 50 \
  --doses 0,2,5,10,15,20
```

## Output Format

### factcheck_reddit.jsonl

Each line is a JSON object with paired posts:

```json
{
  "type": "FactCheck",
  "category": "Health",
  "question": "Does the MMR vaccine cause autism?",
  "best_answer": "No, extensive research shows no link between MMR and autism.",
  "correct_answers": ["No link exists", "..."],
  "incorrect_answers": ["Vaccines cause autism", "..."],
  "source": "https://example.com/factcheck",
  "factual_post_title": "...",
  "factual_post_content": "...",
  "conspiracy_post_title": "...",
  "conspiracy_post_content": "...",
  "claim_text": "Original claim text",
  "claim_date": "2025-03-15",
  "publisher": "PolitiFact",
  "textual_rating": "False",
  "persona": "angry parent"
}
```

### world-posts-fN.jsonl

Each line is a post ready for seeding into Moltbook:

```json
{"title": "...", "content": "...", "submolt": "general"}
```

The `N` in the filename is the number of factual posts; the rest are conspiracy. For example, `world-posts-f3.jsonl` contains 3 factual + 22 conspiracy posts (when `--total-posts 25`).

## Persona Variations

When `--variations N > 1`, each claim generates N post pairs with different writing styles:

| Persona | Style |
|---------|-------|
| angry parent | Emotional, protective, uses personal anecdotes |
| concerned citizen | Measured alarm, appeals to community values |
| conspiracy researcher | "Do your own research", connects dots, cites fringe sources |
| skeptical journalist | Investigative tone, questions official narratives |
| sarcastic debunker | Mocking, uses humor and irony to make points |
| academic expert | Technical language, cites studies, measured tone |
| whistleblower insider | Claims inside knowledge, urgency, "they don't want you to know" |
| local community member | Personal impact stories, neighborhood-level concerns |

## Dependencies

- **requests** — HTTP client for Fact Check Explorer API and article scraping
- **trafilatura** — Article text extraction (primary)
- **beautifulsoup4** — Article text extraction (fallback)
- **anthropic** — Claude API for post generation (Stage 3 only)
