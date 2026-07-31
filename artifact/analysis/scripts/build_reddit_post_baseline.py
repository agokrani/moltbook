#!/usr/bin/env python3
"""Build the post-to-post one-hour Reddit baseline used in the rebuttal.

The controlled data contain top-level agent posts, so the human unit here is a
Reddit submission, not a comment. The script streams RS_2019-04.zst directly
from Zenodo, keeps the first 24 complete UTC hours, and never writes Reddit
text to disk. Only aggregate, per-pair metrics are written.

Primary metrics reproduce the paper's aggregation:
  * gzip compressed/raw ratio on equal-character session text;
  * Distinct-N on equal-token post collections.

The optional upstream checkout adds a robustness check using the pinned
moltbook_vs_reddit message cleaning, 50-character-bin length matching, and
Distinct-1/2 definitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import math
import random
import re
import subprocess
import sys
from collections import OrderedDict
from contextlib import suppress
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_URL = "https://zenodo.org/records/3608135/files/RS_2019-04.zst?download=1"
EXPECTED_UPSTREAM_COMMIT = "30b9bae05635f73e08dde4231367d7f527e9f596"
MIN_CHARS = 40
SEED = 42
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


def clean_text(text: str) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    value = FENCED_CODE_RE.sub(" ", value)
    value = MARKDOWN_LINK_RE.sub(r"\1", value)
    value = INLINE_CODE_RE.sub(" ", value)
    value = URL_RE.sub(" ", value)
    value = QUOTE_LINE_RE.sub(" ", value)
    return " ".join(value.split())


def paper_tokens(text: str) -> list[str]:
    values = []
    for match in TOKEN_RE.finditer(clean_text(text).lower()):
        token = match.group(0)
        if len(token) < 3 or token in STOPWORDS or len(token) > 30:
            continue
        if HEXISH_RE.fullmatch(token):
            continue
        if sum(character.isdigit() for character in token) / len(token) >= 0.5:
            continue
        values.append(token)
    return values[:200]


def text_from_submission(row: dict) -> str | None:
    title = row.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    selftext = row.get("selftext")
    if not isinstance(selftext, str) or selftext in ("[deleted]", "[removed]"):
        selftext = ""
    text = clean_text(f"{title}\n{selftext}")
    return text if len(text) >= MIN_CHARS else None


def probably_bot(author: object) -> bool:
    if not isinstance(author, str):
        return False
    value = author.strip().lower()
    return value.endswith("bot") or value.endswith("_bot")


def stream_reddit_hours(source_url: str, *, n_hours: int = 24) -> tuple[list[dict], int]:
    curl = subprocess.Popen(
        ["curl", "-L", "--fail", "--silent", "--show-error", source_url],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert curl.stdout is not None
    zstd = subprocess.Popen(
        ["zstd", "-dc"],
        stdin=curl.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    curl.stdout.close()
    assert zstd.stdout is not None

    buckets: OrderedDict[int, list[str]] = OrderedDict()
    scanned = 0
    first_hour: int | None = None
    stop_hour: int | None = None
    try:
        for line in zstd.stdout:
            scanned += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            created = row.get("created_utc")
            if not isinstance(created, (int, float)):
                continue
            hour = int(created) // 3600
            if first_hour is None:
                first_hour = hour
                stop_hour = first_hour + n_hours
            assert stop_hour is not None
            if hour >= stop_hour:
                break
            if hour < first_hour:
                continue
            if probably_bot(row.get("author")):
                continue
            text = text_from_submission(row)
            if text is None:
                continue
            buckets.setdefault(hour, []).append(text)
    finally:
        with suppress(Exception):
            zstd.stdout.close()
        zstd.terminate()
        curl.terminate()
        with suppress(Exception):
            zstd.wait(timeout=10)
        with suppress(Exception):
            curl.wait(timeout=10)

    if first_hour is None:
        raise RuntimeError("No Reddit submissions were read")
    missing = [hour for hour in range(first_hour, first_hour + n_hours) if hour not in buckets]
    if missing:
        raise RuntimeError(f"Missing Reddit UTC-hour buckets: {missing}")

    output = []
    for hour in range(first_hour, first_hour + n_hours):
        start = dt.datetime.fromtimestamp(hour * 3600, tz=dt.UTC)
        output.append({"hour": start.isoformat(), "texts": buckets[hour]})
    return output, scanned


def distinct_n_equal_budget(texts_a: list[str], texts_b: list[str], n: int) -> tuple[float, float, int]:
    tokenized_a = [paper_tokens(text) for text in texts_a]
    tokenized_b = [paper_tokens(text) for text in texts_b]
    budget = min(sum(map(len, tokenized_a)), sum(map(len, tokenized_b)))

    def score(tokenized: list[list[str]]) -> float:
        remaining = budget
        total = 0
        unique: set[tuple[str, ...]] = set()
        for tokens in tokenized:
            if remaining <= 0:
                break
            kept = tokens[:remaining]
            remaining -= len(kept)
            for idx in range(max(0, len(kept) - n + 1)):
                gram = tuple(kept[idx : idx + n])
                unique.add(gram)
                total += 1
        return len(unique) / total if total else math.nan

    return score(tokenized_a), score(tokenized_b), budget


def gzip_ratio_equal_characters(texts_a: list[str], texts_b: list[str]) -> tuple[float, float, int]:
    joined_a = "\n".join(clean_text(text) for text in texts_a if clean_text(text))
    joined_b = "\n".join(clean_text(text) for text in texts_b if clean_text(text))
    budget = min(len(joined_a), len(joined_b))

    def score(text: str) -> float:
        raw = text[:budget].encode("utf-8")
        return len(gzip.compress(raw, compresslevel=9)) / len(raw) if raw else math.nan

    return score(joined_a), score(joined_b), budget


def load_agent_sessions(path: Path) -> list[dict]:
    sessions = json.loads(path.read_text())
    if not isinstance(sessions, list) or len(sessions) != 24:
        raise RuntimeError(f"Expected 24 agent sessions, found {len(sessions)}")
    model_runs = {(row.get("model"), row.get("run")) for row in sessions}
    if len(model_runs) != 24:
        raise RuntimeError("Agent model-run identifiers are not unique")
    return sessions


def primary_pair_metrics(agent_sessions: list[dict], reddit_hours: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    hour_order = list(reddit_hours)
    rng.shuffle(hour_order)
    output = []

    for index, (session, hour) in enumerate(zip(agent_sessions, hour_order, strict=True)):
        agent_texts = [clean_text(text) for text in session["texts"]]
        agent_texts = [text for text in agent_texts if len(text) >= MIN_CHARS]
        human_pool = hour["texts"]
        if len(human_pool) < len(agent_texts):
            raise RuntimeError(
                f"Reddit hour {hour['hour']} has {len(human_pool)} eligible posts; "
                f"need {len(agent_texts)}"
            )
        pair_rng = random.Random(SEED + index)
        selected_indices = sorted(pair_rng.sample(range(len(human_pool)), k=len(agent_texts)))
        human_texts = [human_pool[idx] for idx in selected_indices]

        agent_gzip, human_gzip, char_budget = gzip_ratio_equal_characters(
            agent_texts, human_texts
        )
        agent_d1, human_d1, token_budget = distinct_n_equal_budget(agent_texts, human_texts, 1)
        agent_d2, human_d2, _ = distinct_n_equal_budget(agent_texts, human_texts, 2)
        agent_d5, human_d5, _ = distinct_n_equal_budget(agent_texts, human_texts, 5)
        cumulative_d5 = []
        for fraction in (0.25, 0.50, 0.75, 1.00):
            checkpoint_posts = max(1, round(len(agent_texts) * fraction))
            checkpoint_agent, checkpoint_human, checkpoint_budget = distinct_n_equal_budget(
                agent_texts[:checkpoint_posts], human_texts[:checkpoint_posts], 5
            )
            cumulative_d5.append(
                {
                    "post_fraction": fraction,
                    "n_posts_each": checkpoint_posts,
                    "equal_token_budget": checkpoint_budget,
                    "agent": checkpoint_agent,
                    "reddit": checkpoint_human,
                }
            )
        output.append(
            {
                "model": session["model"],
                "run": session["run"],
                "reddit_hour": hour["hour"],
                "n_posts_each": len(agent_texts),
                "equal_token_budget": token_budget,
                "equal_character_budget": char_budget,
                "agent": {"gzip_ratio": agent_gzip, "distinct_1": agent_d1, "distinct_2": agent_d2, "distinct_5": agent_d5},
                "reddit": {"gzip_ratio": human_gzip, "distinct_1": human_d1, "distinct_2": human_d2, "distinct_5": human_d5},
                "cumulative_distinct_5": cumulative_d5,
            }
        )
    return output


def sign_test_p(successes: int, trials: int) -> float:
    smaller_tail = min(successes, trials - successes)
    tail = sum(math.comb(trials, index) for index in range(smaller_tail + 1))
    return min(1.0, 2.0 * tail / (2**trials))


def summarize_pairs(pairs: list[dict]) -> dict:
    summary: dict[str, dict] = {}

    for metric in ("gzip_ratio", "distinct_1", "distinct_2", "distinct_5"):
        agent_values = [row["agent"][metric] for row in pairs]
        reddit_values = [row["reddit"][metric] for row in pairs]
        direction_count = sum(
            agent < reddit for agent, reddit in zip(agent_values, reddit_values, strict=True)
        )
        summary[metric] = {
            "agent_mean": mean(agent_values),
            "reddit_mean": mean(reddit_values),
            "mean_difference_agent_minus_reddit": mean(
                agent - reddit
                for agent, reddit in zip(agent_values, reddit_values, strict=True)
            ),
            "agent_more_repetitive_pairs": direction_count,
            "two_sided_sign_test_p": sign_test_p(direction_count, len(pairs)),
        }
    return summary


def summarize_cumulative_distinct_5(pairs: list[dict]) -> dict:
    checkpoints = []
    for checkpoint_index in range(4):
        agent_values = [row["cumulative_distinct_5"][checkpoint_index]["agent"] for row in pairs]
        reddit_values = [row["cumulative_distinct_5"][checkpoint_index]["reddit"] for row in pairs]
        agent_lower = sum(
            agent < reddit
            for agent, reddit in zip(agent_values, reddit_values, strict=True)
        )
        checkpoints.append(
            {
                "post_fraction": pairs[0]["cumulative_distinct_5"][checkpoint_index]["post_fraction"],
                "agent_mean": mean(agent_values),
                "reddit_mean": mean(reddit_values),
                "mean_difference_agent_minus_reddit": mean(
                    agent - reddit
                    for agent, reddit in zip(agent_values, reddit_values, strict=True)
                ),
                "agent_lower_pairs": agent_lower,
            }
        )

    agent_changes = [
        row["cumulative_distinct_5"][-1]["agent"]
        - row["cumulative_distinct_5"][0]["agent"]
        for row in pairs
    ]
    reddit_changes = [
        row["cumulative_distinct_5"][-1]["reddit"]
        - row["cumulative_distinct_5"][0]["reddit"]
        for row in pairs
    ]
    steeper_agent_declines = sum(
        agent < reddit
        for agent, reddit in zip(agent_changes, reddit_changes, strict=True)
    )
    return {
        "checkpoint_definition": "ordered cumulative post-count quartiles",
        "same_post_count_within_pair_at_each_checkpoint": True,
        "same_token_budget_within_pair_at_each_checkpoint": True,
        "checkpoints": checkpoints,
        "first_to_final_change": {
            "agent_mean": mean(agent_changes),
            "reddit_mean": mean(reddit_changes),
            "mean_difference_agent_minus_reddit": mean(
                agent - reddit
                for agent, reddit in zip(agent_changes, reddit_changes, strict=True)
            ),
            "agent_steeper_decline_pairs": steeper_agent_declines,
            "two_sided_sign_test_p": sign_test_p(steeper_agent_declines, len(pairs)),
        },
    }


def repository_style_metrics(
    agent_sessions: list[dict], reddit_hours: list[dict], upstream_checkout: Path
) -> dict:
    commit = subprocess.check_output(
        ["git", "-C", str(upstream_checkout), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != EXPECTED_UPSTREAM_COMMIT:
        raise RuntimeError(f"Expected upstream commit {EXPECTED_UPSTREAM_COMMIT}, found {commit}")
    sys.path.insert(0, str(upstream_checkout / "src"))
    from moltbook_analysis.metrics import (  # type: ignore[import-not-found]
        distinct_n,
        exact_duplicate_rate,
        gzip_bits_per_char,
        ngram_counts,
        sampled_pairwise_jaccard_similarity,
        shannon_entropy_bits_from_counts,
        soft_duplicate_key,
    )
    from moltbook_analysis.run_analysis import _sample_length_matched  # type: ignore[import-not-found]

    agent_texts = [text for session in agent_sessions for text in session["texts"]]
    reddit_texts = [text for hour in reddit_hours for text in hour["texts"]]
    agent_matched, reddit_matched = _sample_length_matched(
        agent_texts, reddit_texts, bin_size=50, seed=1337, min_len=MIN_CHARS
    )

    def score(texts: list[str]) -> dict:
        soft_keys = [
            key for key in (soft_duplicate_key(text, max_tokens=80) for text in texts) if key
        ]
        unigram_counts = ngram_counts(texts, n=1, max_tokens=80)
        return {
            "n": len(texts),
            "distinct_1": distinct_n(texts, n=1, max_tokens=80),
            "distinct_2": distinct_n(texts, n=2, max_tokens=80),
            "exact_duplicate_rate": exact_duplicate_rate(texts),
            "soft_duplicate_rate": exact_duplicate_rate(soft_keys),
            "mean_gzip_bits_per_char": mean(gzip_bits_per_char(text) for text in texts),
            "pairwise_jaccard": sampled_pairwise_jaccard_similarity(
                texts, pairs=2000, max_tokens=80
            ),
            "unigram_entropy_bits": shannon_entropy_bits_from_counts(unigram_counts),
        }

    return {
        "upstream_repository": "https://github.com/strangeloopcanon/moltbook_vs_reddit",
        "upstream_commit": commit,
        "matching": {"bin_size_characters": 50, "minimum_cleaned_characters": MIN_CHARS},
        "agent": score(agent_matched),
        "reddit": score(reddit_matched),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agents", type=Path, default=ROOT / "results/agent_sessions_1h.json")
    parser.add_argument("--output", type=Path, default=ROOT / "results/matched_1h_reddit_posts.json")
    parser.add_argument("--source-url", default=DEFAULT_URL)
    parser.add_argument("--upstream-checkout", type=Path)
    args = parser.parse_args()

    sessions = load_agent_sessions(args.agents)
    reddit_hours, scanned = stream_reddit_hours(args.source_url, n_hours=24)
    pairs = primary_pair_metrics(sessions, reddit_hours)
    report = {
        "source": {
            "dataset": "The Pushshift Reddit Dataset",
            "file": "RS_2019-04.zst",
            "unit": "Reddit submission (title plus selftext)",
            "url": args.source_url,
            "data_doi": "10.5281/zenodo.3608135",
            "paper_doi": "10.1609/icwsm.v14i1.7347",
            "license": "CC-BY-4.0",
            "rows_scanned": scanned,
            "hours": [hour["hour"] for hour in reddit_hours],
        },
        "design": {
            "seed": SEED,
            "pairs": len(pairs),
            "reddit_hours": len(reddit_hours),
            "minimum_cleaned_characters": MIN_CHARS,
            "same_post_count_within_pair": True,
            "distinct_n_equal_token_budget": True,
            "distinct_n_preprocessing": "time_binned_lexical_metrics_5gram.py",
            "distinct_n_max_tokens_per_post": 200,
            "gzip_equal_character_budget": True,
            "reddit_text_redistributed": False,
        },
        "summary": summarize_pairs(pairs),
        "cumulative_distinct_5": summarize_cumulative_distinct_5(pairs),
        "pairs": pairs,
    }
    if args.upstream_checkout is not None:
        report["repository_style_robustness"] = repository_style_metrics(
            sessions, reddit_hours, args.upstream_checkout
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
