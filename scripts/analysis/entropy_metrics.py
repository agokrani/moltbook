#!/usr/bin/env python3
"""Deterministic lexical, structural, and separability metrics."""

from __future__ import annotations

import math
import random
import re
from collections import Counter
from dataclasses import dataclass
from statistics import median
from typing import Iterable, Sequence

from load_entropy_data import PostRecord

_FENCED_CODE_RE = re.compile(r"```.*?```", flags=re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`[^`]+`")
_MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_URL_RE = re.compile(r"https?://\S+")
_QUOTE_LINE_RE = re.compile(r"(^|\n)>[^\n]*")
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9']+")
_HEXISH_RE = re.compile(r"^[0-9a-f]{6,}$")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
_BULLET_RE = re.compile(r"(?m)^\s*[-*•]\s+")
_NUMBERED_RE = re.compile(r"(?m)^\s*\d+[.)]\s+")
_QUESTION_OPEN_RE = re.compile(r"^\s*(what|why|how|when|where|who|does|do|is|are|should|could|would)\b", re.I)
_CTA_RE = re.compile(r"\b(share|drop|paste|show|report back|report|try|post|reply|compile)\b", re.I)
_IF_THEN_RE = re.compile(r"\bif\b.*\bthen\b|\bif/then\b", re.I)
_REPORT_BACK_RE = re.compile(r"\b(report back|i['’]ll report|report friday|report tomorrow|check back)\b", re.I)

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

_IMPERATIVE_STARTS = {
    "add", "ask", "build", "choose", "default", "define", "drop", "keep",
    "make", "name", "paste", "pick", "post", "report", "run", "set", "share",
    "ship", "show", "start", "test", "track", "try", "use", "write",
}

_STRUCTURAL_KEYWORDS = {
    "receipt": ("receipt",),
    "proof_of_work": ("proof-of-work", "proof of work"),
    "rollback": ("rollback", "roll back"),
    "checklist": ("checklist", "check list"),
    "rubric": ("rubric",),
    "artifact": ("artifact", "artifacts"),
    "falsifier": ("falsifier", "falsifiers"),
    "owner": ("owner", "owners"),
    "ledger": ("ledger", "changelog"),
}


@dataclass
class PreparedPost:
    record: PostRecord
    cleaned_text: str
    tokens: list[str]
    token_set: set[str]
    bigrams: list[tuple[str, str]]
    trigrams: list[tuple[str, str, str]]
    shingle_set: set[str]
    structural: dict[str, float | int | bool]
    structural_signature: tuple[str, ...]


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


def _ngrams(tokens: Sequence[str], n: int) -> list[tuple[str, ...]]:
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]


def shingle_strings(tokens: Sequence[str], *, n: int = 3, max_shingles: int = 80) -> set[str]:
    shingles = {" ".join(ngram) for ngram in _ngrams(tokens, n)}
    return set(sorted(shingles)[:max_shingles])


def structural_features(text: str) -> dict[str, float | int | bool]:
    cleaned = clean_text(text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    sentences = [part.strip() for part in _SENTENCE_RE.split(cleaned) if part.strip()]
    line_count = len(lines)
    bullet_lines = len(_BULLET_RE.findall(cleaned))
    numbered_lines = len(_NUMBERED_RE.findall(cleaned))
    imperative_count = 0
    for sentence in sentences:
        words = tokenize(sentence, max_tokens=8)
        if words and words[0] in _IMPERATIVE_STARTS:
            imperative_count += 1

    features: dict[str, float | int | bool] = {
        "has_bullets": bullet_lines > 0,
        "has_numbered_list": numbered_lines > 0,
        "linebreak_rich": line_count >= 3,
        "imperative_open": imperative_count > 0,
        "question_open": bool(_QUESTION_OPEN_RE.search(cleaned)),
        "call_to_action": bool(_CTA_RE.search(cleaned)),
        "if_then": bool(_IF_THEN_RE.search(cleaned)),
        "report_back": bool(_REPORT_BACK_RE.search(cleaned)),
        "bullet_lines": bullet_lines,
        "numbered_lines": numbered_lines,
        "line_count": line_count,
        "imperative_sentence_starts": imperative_count,
        "question_marks": cleaned.count("?"),
    }
    lowered = cleaned.lower()
    for name, patterns in _STRUCTURAL_KEYWORDS.items():
        features[name] = any(pattern in lowered for pattern in patterns)
    return features


def structural_signature(features: dict[str, float | int | bool]) -> tuple[str, ...]:
    signature: list[str] = []
    for key in (
        "has_bullets",
        "has_numbered_list",
        "linebreak_rich",
        "imperative_open",
        "question_open",
        "call_to_action",
        "if_then",
        "report_back",
        "receipt",
        "proof_of_work",
        "rollback",
        "checklist",
        "rubric",
        "artifact",
        "falsifier",
        "owner",
        "ledger",
    ):
        if features.get(key):
            signature.append(key)

    imperative_bucket = int(features.get("imperative_sentence_starts", 0) or 0)
    if imperative_bucket >= 2:
        signature.append("imperatives_ge2")
    elif imperative_bucket == 1:
        signature.append("imperatives_1")

    if (features.get("bullet_lines", 0) or 0) >= 3:
        signature.append("bullets_ge3")
    if (features.get("numbered_lines", 0) or 0) >= 3:
        signature.append("numbers_ge3")
    if (features.get("question_marks", 0) or 0) >= 2:
        signature.append("questions_ge2")

    if not signature:
        signature.append("plain")
    return tuple(sorted(signature))


def prepare_post(record: PostRecord) -> PreparedPost:
    tokens = tokenize(record.full_text)
    bigrams = _ngrams(tokens, 2)
    trigrams = _ngrams(tokens, 3)
    features = structural_features(record.full_text)
    return PreparedPost(
        record=record,
        cleaned_text=clean_text(record.full_text),
        tokens=tokens,
        token_set=set(tokens),
        bigrams=bigrams,
        trigrams=trigrams,
        shingle_set=shingle_strings(tokens),
        structural=features,
        structural_signature=structural_signature(features),
    )


def prepare_posts(records: Iterable[PostRecord]) -> list[PreparedPost]:
    return [prepare_post(record) for record in records]


def counts_entropy(counter: Counter) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    entropy = 0.0
    for count in counter.values():
        p = count / total
        entropy -= p * math.log(p, 2)
    return entropy


def effective_vocabulary_size(counter: Counter) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    denom = sum((count / total) ** 2 for count in counter.values())
    return 1.0 / denom if denom else 0.0


def distinct_n(posts: Sequence[PreparedPost], n: int) -> float:
    total = 0
    unique: set[tuple[str, ...]] = set()
    for post in posts:
        grams = post.bigrams if n == 2 else post.trigrams if n == 3 else [(token,) for token in post.tokens]
        unique.update(grams)
        total += len(grams)
    return len(unique) / total if total else 0.0


def normalized_vocab_size(posts: Sequence[PreparedPost]) -> float:
    tokens = [token for post in posts for token in post.tokens]
    return len(set(tokens)) / len(tokens) if tokens else 0.0


def exact_duplicate_rate(posts: Sequence[PreparedPost]) -> float:
    if not posts:
        return 0.0
    cleaned = [post.cleaned_text for post in posts]
    return 1.0 - len(set(cleaned)) / len(cleaned)


def near_duplicate_rate(posts: Sequence[PreparedPost]) -> float:
    if not posts:
        return 0.0
    keys = []
    for post in posts:
        if not post.tokens:
            continue
        key = " ".join(sorted(post.tokens[:80]))
        keys.append(key)
    return 1.0 - len(set(keys)) / len(keys) if keys else 0.0


def _sample_pairs(items: Sequence, *, max_pairs: int, seed: int) -> list[tuple[int, int]]:
    n_items = len(items)
    if n_items < 2:
        return []
    max_possible = n_items * (n_items - 1) // 2
    if max_possible <= max_pairs:
        pairs = []
        for left in range(n_items):
            for right in range(left + 1, n_items):
                pairs.append((left, right))
        return pairs
    rng = random.Random(seed)
    pairs = set()
    while len(pairs) < max_pairs:
        left = rng.randrange(n_items)
        right = rng.randrange(n_items - 1)
        if right >= left:
            right += 1
        if left > right:
            left, right = right, left
        pairs.add((left, right))
    return sorted(pairs)


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    if not set_a and not set_b:
        return 1.0
    union = len(set_a | set_b)
    return len(set_a & set_b) / union if union else 0.0


def sampled_pairwise_jaccard(
    posts: Sequence[PreparedPost],
    *,
    max_pairs: int = 2000,
    seed: int = 1337,
) -> dict[str, float]:
    pairs = _sample_pairs(posts, max_pairs=max_pairs, seed=seed)
    if not pairs:
        return {"pairs": 0, "mean": 0.0, "median": 0.0}
    scores = [
        jaccard_similarity(posts[left].token_set, posts[right].token_set)
        for left, right in pairs
    ]
    return {
        "pairs": len(scores),
        "mean": sum(scores) / len(scores),
        "median": median(scores),
    }


def sampled_structural_similarity(
    posts: Sequence[PreparedPost],
    *,
    max_pairs: int = 2000,
    seed: int = 1337,
) -> dict[str, float]:
    pairs = _sample_pairs(posts, max_pairs=max_pairs, seed=seed)
    if not pairs:
        return {"pairs": 0, "mean": 0.0, "median": 0.0}
    scores = []
    for left, right in pairs:
        set_a = set(posts[left].structural_signature)
        set_b = set(posts[right].structural_signature)
        scores.append(jaccard_similarity(set_a, set_b))
    return {
        "pairs": len(scores),
        "mean": sum(scores) / len(scores),
        "median": median(scores),
    }


def cross_group_similarity(
    left_posts: Sequence[PreparedPost],
    right_posts: Sequence[PreparedPost],
    *,
    mode: str = "token",
    max_pairs: int = 2000,
    seed: int = 1337,
) -> float:
    if not left_posts or not right_posts:
        return 0.0
    rng = random.Random(seed)
    total_pairs = min(max_pairs, len(left_posts) * len(right_posts))
    scores = []
    for _ in range(total_pairs):
        left = left_posts[rng.randrange(len(left_posts))]
        right = right_posts[rng.randrange(len(right_posts))]
        if mode == "token":
            scores.append(jaccard_similarity(left.token_set, right.token_set))
        else:
            scores.append(jaccard_similarity(set(left.structural_signature), set(right.structural_signature)))
    return sum(scores) / len(scores) if scores else 0.0


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


def top_k_coverage(counter: Counter, k: int) -> float:
    total = sum(counter.values())
    if total <= 0:
        return 0.0
    return sum(count for _, count in counter.most_common(k)) / total


def signature_counter(posts: Sequence[PreparedPost]) -> Counter:
    counter: Counter = Counter()
    for post in posts:
        counter[post.structural_signature] += 1
    return counter


def feature_prevalence(posts: Sequence[PreparedPost]) -> dict[str, float]:
    if not posts:
        return {}
    keys = sorted(posts[0].structural.keys())
    prevalence = {}
    for key in keys:
        values = [post.structural[key] for post in posts]
        if isinstance(values[0], bool):
            prevalence[key] = sum(1 for value in values if value) / len(values)
        else:
            prevalence[key] = float(sum(float(value) for value in values) / len(values))
    return prevalence


def window_posts(posts: Sequence[PreparedPost], n_windows: int = 5) -> list[list[PreparedPost]]:
    if not posts:
        return []
    ordered = sorted(posts, key=lambda post: post.record.created_at)
    size = max(1, len(ordered) // n_windows)
    windows = []
    for window_idx in range(n_windows):
        start = window_idx * size
        end = start + size if window_idx < n_windows - 1 else len(ordered)
        if start >= len(ordered):
            break
        windows.append(ordered[start:end])
    return windows


def first_posts_per_agent(posts: Sequence[PreparedPost], first_n: int = 2) -> list[PreparedPost]:
    by_agent: dict[str, list[PreparedPost]] = {}
    for post in sorted(posts, key=lambda post: post.record.created_at):
        by_agent.setdefault(post.record.author_name, []).append(post)
    selected = []
    for agent_posts in by_agent.values():
        selected.extend(agent_posts[:first_n])
    return selected


def last_posts_per_agent(posts: Sequence[PreparedPost], last_n: int = 2) -> list[PreparedPost]:
    by_agent: dict[str, list[PreparedPost]] = {}
    for post in sorted(posts, key=lambda post: post.record.created_at):
        by_agent.setdefault(post.record.author_name, []).append(post)
    selected = []
    for agent_posts in by_agent.values():
        selected.extend(agent_posts[-last_n:])
    return selected


def novelty_rates(windows: Sequence[Sequence[PreparedPost]]) -> list[dict[str, float]]:
    seen_tokens: set[tuple[str]] = set()
    seen_bigrams: set[tuple[str, str]] = set()
    rows = []
    for window in windows:
        token_events = 0
        token_new = 0
        bigram_events = 0
        bigram_new = 0
        posts_with_new_tokens = 0
        for post in window:
            had_new_token = False
            for token in post.tokens:
                token_events += 1
                wrapped = (token,)
                if wrapped not in seen_tokens:
                    token_new += 1
                    seen_tokens.add(wrapped)
                    had_new_token = True
            for bigram in post.bigrams:
                bigram_events += 1
                if bigram not in seen_bigrams:
                    bigram_new += 1
                    seen_bigrams.add(bigram)
            if had_new_token:
                posts_with_new_tokens += 1
        rows.append(
            {
                "token_novelty_rate": token_new / token_events if token_events else 0.0,
                "bigram_novelty_rate": bigram_new / bigram_events if bigram_events else 0.0,
                "post_novelty_rate": posts_with_new_tokens / len(window) if window else 0.0,
            }
        )
    return rows


def mean_top_vocab_overlap(posts: Sequence[PreparedPost], *, top_k: int = 20) -> float:
    by_agent: dict[str, list[PreparedPost]] = {}
    for post in posts:
        by_agent.setdefault(post.record.author_name, []).append(post)
    agents = sorted(by_agent)
    if len(agents) < 2:
        return 0.0
    top_sets = {}
    for agent in agents:
        counter = token_counter(by_agent[agent])
        top_sets[agent] = {token for token, _ in counter.most_common(top_k)}
    overlaps = []
    for left_idx in range(len(agents)):
        for right_idx in range(left_idx + 1, len(agents)):
            left = agents[left_idx]
            right = agents[right_idx]
            if not top_sets[left] or not top_sets[right]:
                continue
            overlaps.append(len(top_sets[left] & top_sets[right]) / len(top_sets[left]))
    return sum(overlaps) / len(overlaps) if overlaps else 0.0


def mean_structural_overlap_by_agent(posts: Sequence[PreparedPost]) -> float:
    by_agent: dict[str, Counter] = {}
    for post in posts:
        counter = by_agent.setdefault(post.record.author_name, Counter())
        counter[post.structural_signature] += 1
    agents = sorted(by_agent)
    if len(agents) < 2:
        return 0.0
    signature_sets = {
        agent: {signature for signature, _ in counter.most_common(10)}
        for agent, counter in by_agent.items()
    }
    overlaps = []
    for left_idx in range(len(agents)):
        for right_idx in range(left_idx + 1, len(agents)):
            left = signature_sets[agents[left_idx]]
            right = signature_sets[agents[right_idx]]
            overlaps.append(jaccard_similarity(left, right))
    return sum(overlaps) / len(overlaps) if overlaps else 0.0


def _stratified_split(
    labels: Sequence[str],
    *,
    test_frac: float = 0.2,
    seed: int = 1337,
) -> tuple[list[int], list[int]]:
    grouped: dict[str, list[int]] = {}
    for idx, label in enumerate(labels):
        grouped.setdefault(label, []).append(idx)
    train_idx: list[int] = []
    test_idx: list[int] = []
    rng = random.Random(seed)
    for label, indices in grouped.items():
        if len(indices) < 2:
            continue
        shuffled = indices[:]
        rng.shuffle(shuffled)
        n_test = max(1, int(round(len(shuffled) * test_frac)))
        if n_test >= len(shuffled):
            n_test = len(shuffled) - 1
        test_idx.extend(shuffled[:n_test])
        train_idx.extend(shuffled[n_test:])
    return sorted(train_idx), sorted(test_idx)


def _build_vocab(posts: Sequence[PreparedPost], indices: Sequence[int], *, max_features: int) -> list[str]:
    counter: Counter = Counter()
    for idx in indices:
        counter.update(posts[idx].tokens)
    return [token for token, _ in counter.most_common(max_features)]


def _class_log_probs(
    posts: Sequence[PreparedPost],
    indices: Sequence[int],
    labels: Sequence[str],
    vocab: Sequence[str],
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    vocab_set = set(vocab)
    per_class_counts: dict[str, Counter] = {}
    class_totals: Counter = Counter()
    class_docs: Counter = Counter()
    for idx in indices:
        label = labels[idx]
        class_docs[label] += 1
        counter = per_class_counts.setdefault(label, Counter())
        tokens = [token for token in posts[idx].tokens if token in vocab_set]
        counter.update(tokens)
        class_totals[label] += len(tokens)
    priors = {
        label: math.log(count / sum(class_docs.values()))
        for label, count in class_docs.items()
    }
    likelihoods: dict[str, dict[str, float]] = {}
    alpha = 1.0
    vocab_size = max(len(vocab), 1)
    for label, counter in per_class_counts.items():
        denom = class_totals[label] + alpha * vocab_size
        likelihoods[label] = {
            token: math.log((counter.get(token, 0) + alpha) / denom)
            for token in vocab
        }
        likelihoods[label]["__unk__"] = math.log(alpha / denom)
    return priors, likelihoods


def multinomial_nb_accuracy(
    posts: Sequence[PreparedPost],
    labels: Sequence[str],
    *,
    max_features: int = 3000,
    test_frac: float = 0.2,
    seed: int = 1337,
) -> dict[str, float]:
    if len(posts) < 10:
        return {"accuracy": 0.0, "baseline": 0.0, "n_train": 0, "n_test": 0, "n_classes": 0}

    train_idx, test_idx = _stratified_split(labels, test_frac=test_frac, seed=seed)
    if not train_idx or not test_idx:
        return {"accuracy": 0.0, "baseline": 0.0, "n_train": 0, "n_test": 0, "n_classes": 0}
    train_labels = [labels[idx] for idx in train_idx]
    vocab = _build_vocab(posts, train_idx, max_features=max_features)
    priors, likelihoods = _class_log_probs(posts, train_idx, labels, vocab)
    classes = sorted(priors)
    correct = 0
    test_labels = [labels[idx] for idx in test_idx]
    majority = max(Counter(train_labels).values()) / len(train_labels)
    for idx in test_idx:
        token_counter_doc = Counter(token for token in posts[idx].tokens if token in set(vocab))
        best_label = None
        best_score = None
        for label in classes:
            score = priors[label]
            ll = likelihoods[label]
            unk = ll["__unk__"]
            for token, count in token_counter_doc.items():
                score += count * ll.get(token, unk)
            if best_score is None or score > best_score:
                best_label = label
                best_score = score
        if best_label == labels[idx]:
            correct += 1
    return {
        "accuracy": correct / len(test_idx) if test_idx else 0.0,
        "baseline": majority,
        "n_train": len(train_idx),
        "n_test": len(test_idx),
        "n_classes": len(classes),
    }


def condition_metrics(posts: Sequence[PreparedPost], *, seed: int = 1337) -> dict:
    tokens = token_counter(posts)
    bigrams = ngram_counter(posts, 2)
    signatures = signature_counter(posts)
    lexical_sim = sampled_pairwise_jaccard(posts, seed=seed)
    structural_sim = sampled_structural_similarity(posts, seed=seed)
    return {
        "n_posts": len(posts),
        "n_agents": len({post.record.author_name for post in posts}),
        "exact_duplicate_rate": exact_duplicate_rate(posts),
        "near_duplicate_rate": near_duplicate_rate(posts),
        "distinct_1": distinct_n(posts, 1),
        "distinct_2": distinct_n(posts, 2),
        "distinct_3": distinct_n(posts, 3),
        "normalized_vocab_size": normalized_vocab_size(posts),
        "unigram_entropy": counts_entropy(tokens),
        "bigram_entropy": counts_entropy(bigrams),
        "effective_vocab_size": effective_vocabulary_size(tokens),
        "mean_token_jaccard": lexical_sim["mean"],
        "median_token_jaccard": lexical_sim["median"],
        "mean_structural_similarity": structural_sim["mean"],
        "median_structural_similarity": structural_sim["median"],
        "top_10_token_coverage": top_k_coverage(tokens, 10),
        "top_25_token_coverage": top_k_coverage(tokens, 25),
        "top_50_token_coverage": top_k_coverage(tokens, 50),
        "top_10_signature_coverage": top_k_coverage(signatures, 10),
        "unique_structural_signatures": len(signatures),
        "mean_top20_vocab_overlap": mean_top_vocab_overlap(posts, top_k=20),
        "mean_structural_overlap_by_agent": mean_structural_overlap_by_agent(posts),
        "feature_prevalence": feature_prevalence(posts),
        "top_tokens": [{"token": token, "count": count} for token, count in tokens.most_common(15)],
        "top_signatures": [
            {"signature": list(signature), "count": count}
            for signature, count in signatures.most_common(10)
        ],
    }
