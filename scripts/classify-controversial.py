#!/usr/bin/env python3
"""
Classify FEVER dataset claims as controversial or not using a free OpenRouter model.

Usage:
    python scripts/classify-controversial.py [--sample-pct 1.0] [--output FILE]

Requires:
    pip install requests
    OPENROUTER_API_KEY env var set
"""

import json
import os
import sys
import random
import time
import argparse
import requests

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL = "openrouter/free"
INPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "dataset", "train.jsonl")

SYSTEM_PROMPT = """You are a claim classifier. Given a claim, classify it as either CONTROVERSIAL or NOT_CONTROVERSIAL.

A claim is CONTROVERSIAL if:
- It involves a politically or socially divisive topic
- Reasonable people would disagree about it
- It touches on ethics, morality, religion, politics, social issues, or subjective value judgments
- It could spark a heated debate

A claim is NOT_CONTROVERSIAL if:
- It is a straightforward factual statement (dates, names, places, events)
- It is about entertainment, sports stats, geography, science facts, etc.
- Most people would not have strong opinions about it

Respond with ONLY a JSON object, no other text:
{"label": "CONTROVERSIAL" or "NOT_CONTROVERSIAL", "reason": "one sentence explanation"}"""


def classify_claim(claim, api_key):
    """Send a claim to OpenRouter for classification."""
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Classify this claim: \"{claim}\""},
            ],
            "temperature": 0.0,
        },
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"]

    # Strip markdown code fences if present
    content = content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"label": "PARSE_ERROR", "reason": content[:200]}


def main():
    parser = argparse.ArgumentParser(description="Classify claims as controversial or not")
    parser.add_argument("--sample-pct", type=float, default=1.0, help="Percentage of dataset to sample (default: 1.0)")
    parser.add_argument("--input", default=INPUT_FILE, help="Input JSONL file")
    parser.add_argument("--output", default=None, help="Output JSONL file (default: dataset/classified-controversial.jsonl)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for sampling")
    args = parser.parse_args()

    api_key = OPENROUTER_API_KEY
    if not api_key:
        print("ERROR: Set OPENROUTER_API_KEY environment variable")
        sys.exit(1)

    output_file = args.output or os.path.join(os.path.dirname(args.input), "classified-controversial.jsonl")

    # Load dataset
    print(f"Loading {args.input}...")
    with open(args.input) as f:
        lines = f.readlines()

    total = len(lines)
    sample_size = max(1, int(total * args.sample_pct / 100))
    print(f"Total records: {total}")
    print(f"Sample size ({args.sample_pct}%): {sample_size}")
    print(f"Model: {MODEL}")
    print(f"Output: {output_file}")
    print()

    # Sample
    random.seed(args.seed)
    sampled_indices = sorted(random.sample(range(total), sample_size))
    samples = [json.loads(lines[i]) for i in sampled_indices]

    # Resume support — skip already classified
    already_done = set()
    if os.path.exists(output_file):
        with open(output_file) as f:
            for line in f:
                rec = json.loads(line)
                already_done.add(rec["id"])
        print(f"Resuming: {len(already_done)} already classified")

    # Classify
    controversial_count = 0
    errors = 0
    classified = 0

    with open(output_file, "a") as out:
        for i, sample in enumerate(samples):
            if sample["id"] in already_done:
                continue

            claim = sample["claim"]
            try:
                classification = classify_claim(claim, api_key)
                result = {
                    "id": sample["id"],
                    "claim": claim,
                    "original_label": sample.get("label", ""),
                    "controversial": classification.get("label", "UNKNOWN"),
                    "reason": classification.get("reason", ""),
                }
                out.write(json.dumps(result) + "\n")
                out.flush()

                is_controversial = classification.get("label") == "CONTROVERSIAL"
                if is_controversial:
                    controversial_count += 1
                classified += 1

                status = "CONTROVERSIAL" if is_controversial else "not controversial"
                print(f"[{i+1}/{sample_size}] {status}: {claim[:80]}...")

            except Exception as e:
                errors += 1
                print(f"[{i+1}/{sample_size}] ERROR: {e} — {claim[:60]}...")
                time.sleep(2)
                continue

    # Summary
    print()
    print("=" * 50)
    print(f"Done! Classified {classified} claims.")
    print(f"Controversial: {controversial_count}")
    print(f"Not controversial: {classified - controversial_count}")
    print(f"Errors: {errors}")
    print(f"Output: {output_file}")


if __name__ == "__main__":
    main()
