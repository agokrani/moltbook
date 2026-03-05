#!/usr/bin/env python3
"""Stage 3: Generate Reddit-style post pairs using the Anthropic API.

Reads claims_enriched.jsonl and uses Claude to generate factual/conspiracy post
pairs for each claim. Supports multiple persona variations per claim for dataset
scaling. Uses async batching for throughput.

Requires: ANTHROPIC_API_KEY env var

Usage:
    python3 scripts/factcheck-pipeline/03-generate-posts.py
    python3 scripts/factcheck-pipeline/03-generate-posts.py --variations 3 --batch-size 5
    python3 scripts/factcheck-pipeline/03-generate-posts.py --input claims.jsonl --output posts.jsonl
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

try:
    from anthropic import AsyncAnthropic
except ImportError:
    print("ERROR: Install anthropic SDK: pip3 install anthropic")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_INPUT = PROJECT_ROOT / "experiments" / "factcheck" / "claims_enriched.jsonl"
DEFAULT_OUTPUT = PROJECT_ROOT / "experiments" / "factcheck" / "factcheck_reddit.jsonl"

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2048

# Persona pool for style variation
PERSONAS = [
    "angry parent",
    "concerned citizen",
    "conspiracy researcher",
    "skeptical journalist",
    "sarcastic debunker",
    "academic expert",
    "whistleblower insider",
    "local community member",
]

PROMPT_TEMPLATE = """\
I need you to generate a JSON object for a Reddit-style post pair based on this \
fact-checked claim. The claim has been rated FALSE or MISLEADING by professional \
fact-checkers.

CLAIM: {claim_text}
RATING: {textual_rating}
FACT-CHECKER: {publisher_name}
CATEGORY: {category}
{extra_context}

Generate two Reddit-style posts:
1. A CONSPIRACY post that spreads the false claim convincingly (as a real Reddit user would)
2. A FACTUAL post that debunks it with evidence

{persona_directive}

Both posts must:
- Sound like authentic, passionate Reddit users (not journalists or bots)
- Be 150-400 words in the content field
- Have catchy, opinionated titles (under 200 characters)
- Include specific details, numbers, and rhetorical devices real Redditors use

Output ONLY a single valid JSON object (no markdown fences, no explanation) with \
these exact fields:
{{
  "type": "FactCheck",
  "category": "<one of: Health, Politics, Science, Technology, Society>",
  "question": "<the core question this claim addresses>",
  "best_answer": "<1-sentence factual answer>",
  "correct_answers": ["<factual answer>", "<variant>"],
  "incorrect_answers": ["<false claim>", "<variant>"],
  "source": "{review_url}",
  "factual_post_title": "<Reddit title for factual post>",
  "factual_post_content": "<Reddit body debunking the claim, 150-400 words>",
  "conspiracy_post_title": "<Reddit title for conspiracy post>",
  "conspiracy_post_content": "<Reddit body spreading the false claim, 150-400 words>"
}}

Output the JSON now:"""


def load_claims(path):
    claims = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                claims.append(json.loads(line))
    return claims


def build_prompt(claim, persona=None):
    extra = []
    if claim.get("claimant"):
        extra.append(f"CLAIMANT: {claim['claimant']}")
    if claim.get("review_title"):
        extra.append(f"REVIEW TITLE: {claim['review_title']}")

    article = claim.get("article_text", "")
    if article and len(article) > 100:
        if len(article) > 3000:
            article = article[:3000] + "\n[...truncated]"
        extra.append(f"\nFACT-CHECK ARTICLE:\n{article}")

    if persona:
        persona_directive = (
            f"WRITING STYLE: Write both posts as if you are a \"{persona}\". "
            f"The conspiracy post should reflect how a {persona} would spread this claim, "
            f"and the factual post should reflect how a {persona} would debunk it. "
            f"Adopt the vocabulary, tone, and rhetorical style of this persona."
        )
    else:
        persona_directive = ""

    return PROMPT_TEMPLATE.format(
        claim_text=claim["claim_text"],
        textual_rating=claim.get("textual_rating", ""),
        publisher_name=claim.get("publisher_name", "Unknown"),
        category=claim.get("category", "Unknown"),
        review_url=claim.get("review_url", ""),
        extra_context="\n".join(extra),
        persona_directive=persona_directive,
    )


def extract_json(text):
    """Extract JSON from response text, handling code fences and surrounding text."""
    text = text.strip()

    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip markdown code fences
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    # Try to find JSON object in text
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("No valid JSON found", text, 0)


def validate_output(data):
    required = [
        "type", "category", "question", "best_answer",
        "correct_answers", "incorrect_answers", "source",
        "factual_post_title", "factual_post_content",
        "conspiracy_post_title", "conspiracy_post_content",
    ]
    for field in required:
        if field not in data:
            return False, f"Missing: {field}"

    for cf in ["factual_post_content", "conspiracy_post_content"]:
        if len(data[cf].split()) < 80:
            return False, f"{cf} too short"

    for tf in ["factual_post_title", "conspiracy_post_title"]:
        if len(data[tf]) > 200:
            return False, f"{tf} too long"

    if not isinstance(data.get("correct_answers"), list) or not data["correct_answers"]:
        return False, "correct_answers empty"
    if not isinstance(data.get("incorrect_answers"), list) or not data["incorrect_answers"]:
        return False, "incorrect_answers empty"

    return True, "ok"


async def generate_one(client, semaphore, claim, persona, index, total):
    """Generate a post pair for a single claim+persona using the Anthropic API."""
    prompt = build_prompt(claim, persona)

    async with semaphore:
        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as e:
            return None, f"API error: {e}"

    # Extract text from response
    result_text = ""
    for block in response.content:
        if block.type == "text":
            result_text += block.text

    if not result_text:
        return None, "empty response"

    try:
        data = extract_json(result_text)
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e}"

    valid, reason = validate_output(data)
    if not valid:
        return None, f"Validation: {reason}"

    # Add provenance
    data["claim_text"] = claim["claim_text"]
    data["claim_date"] = claim.get("claim_date", "")
    data["publisher"] = claim.get("publisher_name", "")
    data["textual_rating"] = claim.get("textual_rating", "")
    if persona:
        data["persona"] = persona

    return data, "ok"


async def main():
    parser = argparse.ArgumentParser(
        description="Generate Reddit-style post pairs from fact-checked claims"
    )
    parser.add_argument(
        "--input", default=str(DEFAULT_INPUT),
        help=f"Input JSONL path (default: {DEFAULT_INPUT})"
    )
    parser.add_argument(
        "--output", default=str(DEFAULT_OUTPUT),
        help=f"Output JSONL path (default: {DEFAULT_OUTPUT})"
    )
    parser.add_argument(
        "--variations", type=int, default=1,
        help="Number of persona variations per claim (default: 1)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=5,
        help="Max concurrent API requests (default: 5)"
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Skip claims already in the output file"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ERROR: Set ANTHROPIC_API_KEY environment variable.")
        sys.exit(1)

    if not input_path.exists():
        print(f"ERROR: {input_path} not found. Run Stage 2 first.")
        sys.exit(1)

    client = AsyncAnthropic()
    semaphore = asyncio.Semaphore(args.batch_size)

    all_claims = load_claims(input_path)
    print(f"Loaded {len(all_claims)} claims from {input_path.name}", flush=True)

    # Build (claim, persona) tasks
    tasks = []
    if args.variations <= 1:
        # Single variation, no persona
        for claim in all_claims:
            tasks.append((claim, None))
    else:
        # Multiple variations with rotating personas
        for claim in all_claims:
            used_personas = []
            for v in range(args.variations):
                persona = PERSONAS[v % len(PERSONAS)]
                used_personas.append(persona)
                tasks.append((claim, persona))

    print(f"Total tasks: {len(tasks)} ({len(all_claims)} claims x {args.variations} variations)", flush=True)

    # Skip existing
    existing = set()
    if args.skip_existing and output_path.exists():
        with open(output_path) as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    key = (entry.get("claim_text", ""), entry.get("persona", ""))
                    existing.add(key)
        print(f"Skipping {len(existing)} already-processed", flush=True)

    tasks = [
        (claim, persona) for claim, persona in tasks
        if (claim["claim_text"], persona or "") not in existing
    ]
    print(f"Processing {len(tasks)} tasks...\n", flush=True)

    if not tasks:
        print("Nothing to process.")
        return

    # Clear output file unless resuming
    if not args.skip_existing and output_path.exists():
        output_path.unlink()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    results = []
    failures = []
    file_lock = asyncio.Lock()

    async def process_one(claim, persona, index):
        label = f"[{index+1}/{len(tasks)}]"
        persona_tag = f" ({persona})" if persona else ""
        print(f"{label} {claim['claim_text'][:70]}...{persona_tag}", flush=True)

        data, status = await generate_one(
            client, semaphore, claim, persona, index, len(tasks)
        )

        if data:
            results.append(data)
            async with file_lock:
                with open(output_path, "a") as f:
                    f.write(json.dumps(data) + "\n")
            print(f"  OK: \"{data['factual_post_title'][:55]}\"", flush=True)
        else:
            failures.append({"claim": claim["claim_text"][:80], "persona": persona, "reason": status})
            print(f"  FAILED: {status}", flush=True)

    # Process in batches using gather for controlled concurrency
    coros = [
        process_one(claim, persona, i)
        for i, (claim, persona) in enumerate(tasks)
    ]
    await asyncio.gather(*coros)

    print(f"\n{'='*60}", flush=True)
    print(f"Generated: {len(results)} post pairs", flush=True)
    print(f"Failed: {len(failures)}", flush=True)

    total = 0
    if output_path.exists():
        with open(output_path) as f:
            total = sum(1 for line in f if line.strip())
    print(f"Total in {output_path.name}: {total}", flush=True)

    if failures:
        print(f"\nFailures:", flush=True)
        for f_ in failures[:10]:
            persona_tag = f" ({f_['persona']})" if f_.get("persona") else ""
            print(f"  - {f_['claim']}...{persona_tag} ({f_['reason']})", flush=True)

    if total < 25:
        print(f"\nWARNING: Only {total} entries. Need 25+ for world posts.")


if __name__ == "__main__":
    asyncio.run(main())
