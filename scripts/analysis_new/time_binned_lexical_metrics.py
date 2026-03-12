#!/usr/bin/env python3
"""Lexical metrics for strict fixed-duration bins."""

from __future__ import annotations

import re
import random
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

from load_entropy_data import PostRecord

_FENCED_CODE_RE = re.compile(r"```.*?```", flags=re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_URL_RE = re.compile(r"https?://\S+")
_QUOTE_LINE_RE = re.compile(r"(^|\n)>[^\n]*")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+")
_HEXISH_RE = re.compile(r"^[0-9a-f]{6,}$")

_STOPWORDS = {
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


@dataclass
class PreparedPost:
    record: PostRecord
    cleaned_text: str
    tokens: list[str]
    bigrams: list[tuple[str, str]]
    trigrams: list[tuple[str, str, str]]


def clean_text(text: str) -> str:
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    value = _FENCED_CODE_RE.sub(" ", value)
    value = _MARKDOWN_LINK_RE.sub(r"\1", value)
    value = _INLINE_CODE_RE.sub(" ", value)
    value = _URL_RE.sub(" ", value)
    value = _QUOTE_LINE_RE.sub(" ", value)
    return " ".join(value.split())


def _is_noise_token(token: str) -> bool:
    if len(token) > 30:
        return True
    if _HEXISH_RE.fullmatch(token):
        return True
    return sum(ch.isdigit() for ch in token) / len(token) >= 0.5


def tokenize(text: str, *, max_tokens: int = 200) -> list[str]:
    cleaned = clean_text(text).lower()
    tokens = [
        token for token in _TOKEN_RE.findall(cleaned)
        if len(token) >= 3 and token not in _STOPWORDS and not _is_noise_token(token)
    ]
    return tokens[:max_tokens]


def ngrams(tokens: Sequence[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def prepare_post(record: PostRecord) -> PreparedPost:
    tokens = tokenize(record.full_text)
    return PreparedPost(
        record=record,
        cleaned_text=clean_text(record.full_text),
        tokens=tokens,
        bigrams=ngrams(tokens, 2),
        trigrams=ngrams(tokens, 3),
    )


def prepare_posts(records: Iterable[PostRecord]) -> list[PreparedPost]:
    return [prepare_post(record) for record in records]


def distinct_n(posts: Sequence[PreparedPost], n: int) -> float:
    total = 0
    unique: set[tuple[str, ...]] = set()
    for post in posts:
        grams = post.bigrams if n == 2 else post.trigrams if n == 3 else [(token,) for token in post.tokens]
        unique.update(grams)
        total += len(grams)
    return len(unique) / total if total else 0.0


def token_counter(posts: Sequence[PreparedPost]) -> Counter:
    counter: Counter = Counter()
    for post in posts:
        counter.update(post.tokens)
    return counter


def ngram_counter(posts: Sequence[PreparedPost], n: int) -> Counter:
    counter: Counter = Counter()
    for post in posts:
        grams = post.bigrams if n == 2 else post.trigrams if n == 3 else [(token,) for token in post.tokens]
        counter.update(grams)
    return counter


def lexical_metrics(posts: Sequence[PreparedPost]) -> dict[str, float | int]:
    tokens = token_counter(posts)
    bigrams = ngram_counter(posts, 2)
    trigrams = ngram_counter(posts, 3)
    return {
        "n_posts": len(posts),
        "n_agents": len({post.record.author_name for post in posts}),
        "token_total": sum(tokens.values()),
        "bigram_total": sum(bigrams.values()),
        "trigram_total": sum(trigrams.values()),
        "unique_tokens": len(tokens),
        "unique_bigrams": len(bigrams),
        "unique_trigrams": len(trigrams),
        "distinct_1": distinct_n(posts, 1),
        "distinct_2": distinct_n(posts, 2),
        "distinct_3": distinct_n(posts, 3),
    }


def subsampled_distinct_n(
    posts: Sequence[PreparedPost],
    n: int,
    target_size: int,
    *,
    n_samples: int = 100,
    seed: int = 42,
) -> dict[str, float | list[float]]:
    if not posts or target_size <= 0:
        return {"mean": 0.0, "ci_lo": 0.0, "ci_hi": 0.0, "samples": []}
    if len(posts) <= target_size:
        value = distinct_n(posts, n)
        return {"mean": value, "ci_lo": value, "ci_hi": value, "samples": [value]}
    rng = random.Random(seed)
    posts_list = list(posts)
    samples: list[float] = []
    for _ in range(n_samples):
        subset = rng.sample(posts_list, target_size)
        samples.append(distinct_n(subset, n))
    samples.sort()
    lo_idx = int(0.025 * len(samples))
    hi_idx = int(0.975 * len(samples))
    return {
        "mean": sum(samples) / len(samples),
        "ci_lo": samples[lo_idx],
        "ci_hi": samples[hi_idx],
        "samples": samples,
    }


def fixed_time_bins(
    posts: Sequence[PreparedPost],
    *,
    bin_edges: Sequence[float],
) -> list[tuple[int, float, float, list[PreparedPost]]]:
    if len(bin_edges) < 2:
        return []
    ordered = sorted(posts, key=lambda post: post.record.minutes_elapsed)
    bins: list[tuple[int, float, float, list[PreparedPost]]] = []
    for idx in range(len(bin_edges) - 1):
        start = float(bin_edges[idx])
        end = float(bin_edges[idx + 1])
        if idx == len(bin_edges) - 2:
            members = [post for post in ordered if start <= post.record.minutes_elapsed <= end]
        else:
            members = [post for post in ordered if start <= post.record.minutes_elapsed < end]
        bins.append((idx, start, end, members))
    return bins
