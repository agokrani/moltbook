#!/usr/bin/env python3
"""Compute true equal-token and equal-byte temporal robustness checks.

This complements the existing equal-*post* analysis.  For each of the 24
paper's homogeneous 10-agent runs, it divides the first hour into four
15-minute windows.  Within a run, every window is then evaluated at:

* the same token budget for Distinct-5; and
* the same UTF-8 byte budget for the gzip compression ratio.

Posts are randomly permuted before truncation so a length budget does not
always select the earliest posts in a window.  The reported value is the mean
over repeated deterministic draws.  Seed posts are excluded.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean, median


TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+")
HEXISH_RE = re.compile(r"^[0-9a-f]{6,}$")
FENCED_CODE_RE = re.compile(r"```.*?```", flags=re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]+`")
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
URL_RE = re.compile(r"https?://\S+")
QUOTE_LINE_RE = re.compile(r"(^|\n)>[^\n]*")
STOPWORDS = {
    "a", "about", "after", "all", "also", "an", "and", "any", "are", "as",
    "at", "be", "because", "been", "but", "by", "can", "could", "do", "does",
    "don't", "each", "even", "for", "from", "get", "got", "had", "has",
    "have", "he", "her", "here", "him", "his", "how", "i", "if", "in",
    "into", "is", "it", "its", "just", "let", "like", "make", "me", "more",
    "most", "my", "need", "new", "no", "not", "now", "of", "on", "one",
    "only", "or", "other", "our", "out", "over", "own", "people", "really",
    "right", "say", "she", "should", "so", "some", "still", "take", "than",
    "that", "the", "their", "them", "then", "there", "these", "they", "think",
    "this", "those", "through", "to", "too", "up", "us", "use", "very",
    "want", "was", "way", "we", "well", "were", "what", "when", "where",
    "which", "while", "who", "will", "with", "would", "you", "your",
}
BINS = ((0.0, 15.0), (15.0, 30.0), (30.0, 45.0), (45.0, 60.0))


def tokens(text: str) -> list[str]:
    value = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    value = FENCED_CODE_RE.sub(" ", value)
    value = MARKDOWN_LINK_RE.sub(r"\1", value)
    value = INLINE_CODE_RE.sub(" ", value)
    value = URL_RE.sub(" ", value)
    value = QUOTE_LINE_RE.sub(" ", value)
    value = " ".join(value.split())
    values = []
    for match in TOKEN_RE.finditer(value.lower()):
        token = match.group(0)
        if len(token) < 3 or token in STOPWORDS or len(token) > 30:
            continue
        if HEXISH_RE.fullmatch(token):
            continue
        if sum(character.isdigit() for character in token) / len(token) >= 0.5:
            continue
        values.append(token)
    return values[:200]


def stable_seed(run_uid: str, bin_index: int, repetition: int, metric: str) -> int:
    value = f"{run_uid}|{bin_index}|{repetition}|{metric}".encode()
    return int.from_bytes(hashlib.sha256(value).digest()[:8], "big")


def distinct5_at_token_budget(
    texts: list[str], budget: int, *, run_uid: str, bin_index: int, repetition: int
) -> float:
    order = list(range(len(texts)))
    random.Random(stable_seed(run_uid, bin_index, repetition, "d5")).shuffle(order)
    remaining = budget
    total = 0
    unique: set[tuple[str, ...]] = set()
    for index in order:
        if remaining <= 0:
            break
        kept = tokens(texts[index])[:remaining]
        remaining -= len(kept)
        for offset in range(max(0, len(kept) - 4)):
            gram = tuple(kept[offset : offset + 5])
            unique.add(gram)
            total += 1
    if remaining != 0:
        raise RuntimeError(f"Could not fill equal-token budget; {remaining} tokens missing")
    return len(unique) / total if total else math.nan


def gzip_at_byte_budget(
    texts: list[str], budget: int, *, run_uid: str, bin_index: int, repetition: int
) -> float:
    order = list(range(len(texts)))
    random.Random(stable_seed(run_uid, bin_index, repetition, "gzip")).shuffle(order)
    raw = b"\n".join(texts[index].encode("utf-8") for index in order)[:budget]
    if len(raw) != budget:
        raise RuntimeError(f"Could not fill equal-byte budget; got {len(raw)} of {budget}")
    return len(gzip.compress(raw, compresslevel=9)) / len(raw) if raw else math.nan


def sign_test_p(successes: int, trials: int) -> float:
    smaller_tail = min(successes, trials - successes)
    tail = sum(math.comb(trials, index) for index in range(smaller_tail + 1))
    return min(1.0, 2.0 * tail / (2**trials))


def load_run_specs(manifest_path: Path) -> list[dict]:
    with manifest_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = [
        row
        for row in rows
        if row["internal_family_label"] == "single_model_final"
        and row["scale"] == "n10"
        and row["include_in_main"].lower() == "true"
    ]
    if len(selected) != 24:
        raise RuntimeError(f"Expected 24 paper n10 runs, found {len(selected)}")
    if len({row["run_uid"] for row in selected}) != 24:
        raise RuntimeError("Selected run UIDs are not unique")
    return selected


def load_posts(post_index_path: Path, run_uids: set[str]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    with post_index_path.open() as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("run_uid") not in run_uids or row.get("is_seed"):
                continue
            elapsed = row.get("minutes_elapsed")
            text = row.get("text")
            if not isinstance(elapsed, (int, float)) or not isinstance(text, str) or not text:
                continue
            if 0.0 <= elapsed <= 60.0:
                grouped[row["run_uid"]].append(row)
    missing = run_uids - set(grouped)
    if missing:
        raise RuntimeError(f"No posts for selected runs: {sorted(missing)}")
    return grouped


def analyze_run(spec: dict, posts: list[dict], repetitions: int) -> dict:
    windows: list[list[str]] = []
    for index, (low, high) in enumerate(BINS):
        if index < 3:
            members = [row["text"] for row in posts if low <= row["minutes_elapsed"] < high]
        else:
            members = [row["text"] for row in posts if low <= row["minutes_elapsed"] <= high]
        if not members:
            raise RuntimeError(f"Empty window {index} for {spec['run_uid']}")
        windows.append(members)

    token_counts = [sum(len(tokens(text)) for text in window) for window in windows]
    byte_counts = [len("\n".join(window).encode("utf-8")) for window in windows]
    token_budget = min(token_counts)
    byte_budget = min(byte_counts)
    run_uid = spec["run_uid"]

    d5_draws: list[list[float]] = [[] for _ in BINS]
    gzip_draws: list[list[float]] = [[] for _ in BINS]
    for repetition in range(repetitions):
        for bin_index, window in enumerate(windows):
            d5_draws[bin_index].append(
                distinct5_at_token_budget(
                    window,
                    token_budget,
                    run_uid=run_uid,
                    bin_index=bin_index,
                    repetition=repetition,
                )
            )
            gzip_draws[bin_index].append(
                gzip_at_byte_budget(
                    window,
                    byte_budget,
                    run_uid=run_uid,
                    bin_index=bin_index,
                    repetition=repetition,
                )
            )

    d5_means = [mean(values) for values in d5_draws]
    gzip_means = [mean(values) for values in gzip_draws]
    return {
        "run_uid": run_uid,
        "run_id": spec["run_id"],
        "model": spec["model_display"],
        "condition": spec["condition"],
        "post_counts": [len(window) for window in windows],
        "token_counts_before_matching": token_counts,
        "byte_counts_before_matching": byte_counts,
        "equal_token_budget": token_budget,
        "equal_byte_budget": byte_budget,
        "repetitions": repetitions,
        "distinct_5_equal_token_by_window": d5_means,
        "gzip_ratio_equal_byte_by_window": gzip_means,
        "delta_distinct_5_equal_token": d5_means[-1] - d5_means[0],
        "delta_gzip_ratio_equal_byte": gzip_means[-1] - gzip_means[0],
    }


def summarize(rows: list[dict], field: str) -> dict:
    deltas = [row[field] for row in rows]
    declines = sum(value < 0 for value in deltas)
    return {
        "runs": len(rows),
        "declines": declines,
        "mean_delta": mean(deltas),
        "median_delta": median(deltas),
        "two_sided_sign_test_p": sign_test_p(declines, len(rows)),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--post-index", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=100)
    args = parser.parse_args()

    specs = load_run_specs(args.manifest)
    posts = load_posts(args.post_index, {row["run_uid"] for row in specs})
    rows = [analyze_run(spec, posts[spec["run_uid"]], args.repetitions) for spec in specs]

    by_model = {}
    for model in sorted({row["model"] for row in rows}):
        subset = [row for row in rows if row["model"] == model]
        by_model[model] = {
            "distinct_5_equal_token": summarize(subset, "delta_distinct_5_equal_token"),
            "gzip_ratio_equal_byte": summarize(subset, "delta_gzip_ratio_equal_byte"),
        }

    output = {
        "method": {
            "cohort": "24 paper single-model n10 runs",
            "windows_minutes": [[low, high] for low, high in BINS],
            "seed_posts_excluded": True,
            "distinct_5_control": "same token count in every window within each run",
            "gzip_control": "same UTF-8 byte count in every window within each run",
            "random_post_permutations_per_window": args.repetitions,
        },
        "summary": {
            "distinct_5_equal_token": summarize(rows, "delta_distinct_5_equal_token"),
            "gzip_ratio_equal_byte": summarize(rows, "delta_gzip_ratio_equal_byte"),
            "by_model": by_model,
        },
        "runs": rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output["summary"], indent=2))


if __name__ == "__main__":
    main()
