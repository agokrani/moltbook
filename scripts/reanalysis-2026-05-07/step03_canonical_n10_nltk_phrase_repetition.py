#!/usr/bin/env python3
"""Step 3: qualitative NLTK 5-token phrase repetition for canonical n10 runs.

This script intentionally uses NLTK tokenization rather than the older custom
regex n-gram helper. It analyzes agent-generated posts only. Seed posts are not
loaded and are not used for exclusion or overlap checks.
"""
from __future__ import annotations

import json
import math
import re
import sys
import textwrap
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch, Rectangle

try:
    from nltk.tokenize import PunktTokenizer, word_tokenize
    from nltk.tokenize.destructive import NLTKWordTokenizer
    from nltk.tokenize.treebank import TreebankWordDetokenizer
    from nltk.util import ngrams as nltk_ngrams
except Exception as exc:  # pragma: no cover - import guard for local environments
    raise SystemExit(
        "NLTK is required for Step 3. Install it in a virtual environment, for example:\n"
        "  python3 -m venv .venv-nltk\n"
        "  .venv-nltk/bin/python -m pip install nltk\n"
        "  .venv-nltk/bin/python -m nltk.downloader punkt punkt_tab\n"
        "Then run this script with .venv-nltk/bin/python."
    ) from exc

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    AYUSH_ROOT,
    CONDITION_COLORS,
    CONDITION_LABELS,
    CONDITION_ORDER,
    MODEL_ORDER,
    PLOT_ROOT,
    setup_style,
)

OUT_DIR = PLOT_ROOT / "step03_canonical_n10_nltk_phrase_repetition"
POST_INDEX = AYUSH_ROOT / "post_index.csv"
NGRAM_N = 5
TOP_PER_RUN_FOR_CSV = 25
LEDGER_ROWS = 10

# NLTK's public word_tokenize() does not expose token spans. NLTKWordTokenizer is
# the tokenizer object used by word_tokenize in NLTK 3.9.x. We use it only to get
# exact character spans so the plotted phrase can be an actual surface substring
# from the post, with punctuation retained.
SENTENCE_TOKENIZER = PunktTokenizer("english")
SPAN_WORD_TOKENIZER = NLTKWordTokenizer()
DETOKENIZER = TreebankWordDetokenizer()

MODEL_COLORS = {
    "GPT-5": "#3B6EA8",
    "Gemini Flash Lite": "#7B4EA3",
    "Kimi K2.5": "#D9822B",
    "GLM-5": "#1B6B42",
}


def ensure_nltk_ready() -> None:
    """Fail clearly if required tokenizer data are unavailable."""
    try:
        _ = word_tokenize("A short tokenizer check.")
        _ = list(SENTENCE_TOKENIZER.span_tokenize("A sentence. Another sentence."))
    except LookupError as exc:
        raise SystemExit(
            "NLTK tokenizer data are missing. Run:\n"
            "  python -m nltk.downloader punkt punkt_tab\n"
            "inside the environment used for this script."
        ) from exc


@dataclass(frozen=True)
class Occurrence:
    record_id: str
    run_uid: str
    run_id: str
    model_display: str
    condition: str
    condition_label: str
    author_name: str
    author_display_name: str
    minutes_elapsed: float
    title: str
    content: str
    sentence: str
    phrase_surface: str
    phrase_detokenized: str
    tokens: tuple[str, ...]


@dataclass
class PhraseStat:
    run_uid: str
    run_id: str
    model_display: str
    condition: str
    condition_label: str
    tokens: tuple[str, ...]
    phrase_surface: str
    phrase_detokenized: str
    n_occurrences: int
    n_posts: int
    n_agents: int
    occurrences: list[Occurrence]

    @property
    def sort_key(self) -> tuple[int, int, int, str]:
        return (self.n_agents, self.n_posts, self.n_occurrences, self.phrase_surface.lower())


def clean_cell(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value)


def post_text(row: pd.Series) -> str:
    title = clean_cell(row.get("title", "")).strip()
    content = clean_cell(row.get("content", "")).strip()
    if title and content:
        return f"{title}\n{content}"
    return title or content


def canonical_agent_posts() -> pd.DataFrame:
    df = pd.read_csv(POST_INDEX, low_memory=False)
    sub = df[
        (df["internal_family_label"] == "single_model_final")
        & (df["scale"] == "n10")
        & (df["n_agents"] == 10)
        & (~df["is_seed"].astype(bool))
    ].copy()
    sub = sub.sort_values(["model_display", "condition", "run_uid", "minutes_elapsed", "post_id"])
    return sub


def sentence_spans(text: str) -> Iterable[tuple[int, int, str]]:
    """Yield NLTK sentence spans and surface text."""
    if not text.strip():
        return []
    return ((start, end, text[start:end]) for start, end in SENTENCE_TOKENIZER.span_tokenize(text))


def ngram_occurrences_for_post(row: pd.Series) -> list[Occurrence]:
    text = post_text(row)
    out: list[Occurrence] = []
    for _sent_start, _sent_end, sent in sentence_spans(text):
        # Public NLTK tokenization requested for the analysis.
        tokens = word_tokenize(sent)
        if len(tokens) < NGRAM_N:
            continue

        # Span tokenizer is used only to preserve the exact surface substring for display.
        spans = list(SPAN_WORD_TOKENIZER.span_tokenize(sent))
        if len(spans) != len(tokens):
            # Rare tokenizer mismatch fallback: keep the public word_tokenize tokens and use
            # NLTK's paired detokenizer for display. No custom cleanup is applied.
            for gram in nltk_ngrams(tokens, NGRAM_N):
                detok = DETOKENIZER.detokenize(list(gram))
                out.append(make_occurrence(row, sent, detok, detok, tuple(gram)))
            continue

        for idx, gram in enumerate(nltk_ngrams(tokens, NGRAM_N)):
            start = spans[idx][0]
            end = spans[idx + NGRAM_N - 1][1]
            surface = sent[start:end]
            detok = DETOKENIZER.detokenize(list(gram))
            out.append(make_occurrence(row, sent, surface, detok, tuple(gram)))
    return out


def make_occurrence(
    row: pd.Series,
    sentence: str,
    phrase_surface: str,
    phrase_detokenized: str,
    tokens: tuple[str, ...],
) -> Occurrence:
    return Occurrence(
        record_id=clean_cell(row.get("record_id", "")),
        run_uid=clean_cell(row.get("run_uid", "")),
        run_id=clean_cell(row.get("run_id", "")),
        model_display=clean_cell(row.get("model_display", "")),
        condition=clean_cell(row.get("condition", "")),
        condition_label=CONDITION_LABELS.get(clean_cell(row.get("condition", "")), clean_cell(row.get("condition", ""))),
        author_name=clean_cell(row.get("author_name", "")),
        author_display_name=clean_cell(row.get("author_display_name", "")),
        minutes_elapsed=float(row.get("minutes_elapsed", math.nan)),
        title=clean_cell(row.get("title", "")),
        content=clean_cell(row.get("content", "")),
        sentence=" ".join(sentence.split()),
        phrase_surface=" ".join(phrase_surface.split()),
        phrase_detokenized=phrase_detokenized,
        tokens=tokens,
    )


def choose_surface(occurrences: list[Occurrence]) -> str:
    surfaces = Counter(o.phrase_surface for o in occurrences)
    return surfaces.most_common(1)[0][0]


def phrase_stats(df: pd.DataFrame) -> list[PhraseStat]:
    stats: list[PhraseStat] = []
    for (run_uid, model, condition), sub in df.groupby(["run_uid", "model_display", "condition"], sort=False):
        by_tokens: dict[tuple[str, ...], list[Occurrence]] = defaultdict(list)
        for _, row in sub.iterrows():
            for occ in ngram_occurrences_for_post(row):
                by_tokens[occ.tokens].append(occ)

        for tokens, occs in by_tokens.items():
            posts = {o.record_id for o in occs}
            agents = {o.author_name for o in occs}
            first = occs[0]
            stats.append(
                PhraseStat(
                    run_uid=clean_cell(run_uid),
                    run_id=first.run_id,
                    model_display=clean_cell(model),
                    condition=clean_cell(condition),
                    condition_label=first.condition_label,
                    tokens=tokens,
                    phrase_surface=choose_surface(occs),
                    phrase_detokenized=DETOKENIZER.detokenize(list(tokens)),
                    n_occurrences=len(occs),
                    n_posts=len(posts),
                    n_agents=len(agents),
                    occurrences=sorted(occs, key=lambda o: (o.minutes_elapsed, o.record_id)),
                )
            )
    return stats


def top_for_csv(stats: list[PhraseStat]) -> list[PhraseStat]:
    out: list[PhraseStat] = []
    by_run: dict[str, list[PhraseStat]] = defaultdict(list)
    for stat in stats:
        by_run[stat.run_uid].append(stat)
    for _run_uid, vals in by_run.items():
        out.extend(sorted(vals, key=lambda s: s.sort_key, reverse=True)[:TOP_PER_RUN_FOR_CSV])
    return sorted(out, key=lambda s: (MODEL_ORDER.index(s.model_display), CONDITION_ORDER.index(s.condition), -s.n_agents, -s.n_posts) if s.model_display in MODEL_ORDER and s.condition in CONDITION_ORDER else s.sort_key)


GENERIC_PHRASE_PREFIXES = (
    "i have been thinking about",
    "have been thinking about",
    "i have been reflecting on",
    "i have been watching this",
    "i do not know if",
    "i’ll compile a",
    "i'll compile a",
    "what’s your smallest",
    "what's your smallest",
    "but here is what i",
)

FRAGMENT_START_TOKENS = {"of", "says", "d", "’", "'", "-", ":", ",", ";"}
FRAGMENT_END_TOKENS = {"the", "a", "an", "to", "of", "with", "at", "and", "or", "if", "what", "i", "be"}
DISPLAY_LEFT_EXPAND_TOKENS = {"of", "am", "says", "d", "’", "'", "ll", "re", "ve", "m"}
DISPLAY_RIGHT_EXPAND_TOKENS = FRAGMENT_END_TOKENS | {"about"}
DISPLAY_TRAILING_PUNCT = {".", "!", "?", ":"}


def normalized_phrase(stat: PhraseStat) -> str:
    return re.sub(r"\s+", " ", stat.phrase_surface.strip().lower())


def is_generic_phrase(stat: PhraseStat) -> bool:
    phrase = normalized_phrase(stat)
    return any(phrase.startswith(prefix) for prefix in GENERIC_PHRASE_PREFIXES)


def is_fragment_phrase(stat: PhraseStat) -> bool:
    if not stat.tokens:
        return True
    first = stat.tokens[0].strip().lower()
    last = stat.tokens[-1].strip().lower()
    return first in FRAGMENT_START_TOKENS or last in FRAGMENT_END_TOKENS


def representative_for_run(vals: list[PhraseStat]) -> PhraseStat:
    """Choose a readable representative from each run's strongest candidates.

    Exact 5-grams are still the unit of analysis. This selector avoids showing
    an awkward fragment when a nearly-as-strong overlapping phrase is more
    interpretable. It also avoids repeating generic opening templates when a
    similarly widespread phrase is available in the same run.
    """
    ranked = sorted(vals, key=lambda s: s.sort_key, reverse=True)
    top = ranked[0]
    for margin in (1, 2, 3):
        minimum_agents = max(1, top.n_agents - margin)
        candidates = [
            stat for stat in ranked[:15]
            if stat.n_agents >= minimum_agents
            and stat.n_posts >= 5
            and not is_generic_phrase(stat)
            and not is_fragment_phrase(stat)
        ]
        if candidates:
            return sorted(candidates, key=lambda s: s.sort_key, reverse=True)[0]
    for stat in ranked[:15]:
        if not is_fragment_phrase(stat):
            return stat
    return top


def top_for_ledger(stats: list[PhraseStat]) -> list[PhraseStat]:
    """Pick one readable representative phrase from each run, then rank globally."""
    by_run: dict[str, list[PhraseStat]] = defaultdict(list)
    for stat in stats:
        by_run[stat.run_uid].append(stat)
    representatives = [representative_for_run(vals) for vals in by_run.values()]
    return sorted(representatives, key=lambda s: s.sort_key, reverse=True)[:LEDGER_ROWS]


def find_token_match(tokens: list[str], target: tuple[str, ...]) -> int | None:
    n = len(target)
    for idx in range(len(tokens) - n + 1):
        if tuple(tokens[idx : idx + n]) == target:
            return idx
    return None


def expanded_display_phrase(stat: PhraseStat) -> str:
    """Return a compact surface phrase, expanded from the exact 5-gram only for readability."""
    for occ in stat.occurrences[:30]:
        tokens = word_tokenize(occ.sentence)
        spans = list(SPAN_WORD_TOKENIZER.span_tokenize(occ.sentence))
        if len(tokens) != len(spans):
            continue
        idx = find_token_match(tokens, stat.tokens)
        if idx is None:
            continue
        start = idx
        end = idx + len(stat.tokens) - 1
        first = tokens[start].strip().lower()
        last = tokens[end].strip().lower()
        if first in DISPLAY_LEFT_EXPAND_TOKENS and start > 0:
            start -= 1
        if last in DISPLAY_RIGHT_EXPAND_TOKENS and end + 1 < len(tokens):
            end += 1
        if end + 1 < len(tokens) and tokens[end + 1] in DISPLAY_TRAILING_PUNCT:
            end += 1
        if end - start + 1 > 9:
            start = idx
            end = idx + len(stat.tokens) - 1
        surface = occ.sentence[spans[start][0] : spans[end][1]]
        return " ".join(surface.split())
    return stat.phrase_surface


def write_csv(stats: list[PhraseStat], path: Path) -> None:
    rows = []
    for stat in top_for_csv(stats):
        rows.append(
            {
                "ngram_n": NGRAM_N,
                "model_display": stat.model_display,
                "condition": stat.condition,
                "condition_label": stat.condition_label,
                "run_id": stat.run_id,
                "run_uid": stat.run_uid,
                "phrase_surface": stat.phrase_surface,
                "phrase_detokenized": stat.phrase_detokenized,
                "tokens_json": json.dumps(list(stat.tokens), ensure_ascii=False),
                "n_agents": stat.n_agents,
                "n_posts": stat.n_posts,
                "n_occurrences": stat.n_occurrences,
            }
        )
    pd.DataFrame(rows).to_csv(path, index=False)


def shorten(text: str, width: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return textwrap.shorten(text, width=width, placeholder="…")


def wrap(text: str, width: int) -> str:
    return textwrap.fill(text, width=width, break_long_words=False, break_on_hyphens=False)


def plot_ledger(ledger: list[PhraseStat], path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(11.2, 7.6), facecolor="#F7F4EF")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(
        0.055,
        0.945,
        "Which repeated phrases became local templates?",
        fontsize=20.5,
        fontweight="bold",
        color="#1F2A33",
        ha="left",
    )
    fig.text(
        0.055,
        0.907,
        "Canonical 10-agent runs only. Agent posts only. Exact NLTK 5-token anchors are shown under each phrase.",
        fontsize=11.2,
        color="#53636E",
        ha="left",
    )

    max_posts = max(s.n_posts for s in ledger) if ledger else 1
    left_x = 0.055
    right_x = 0.525
    card_w = 0.42
    card_h = 0.140
    row_gap = 0.016
    top_y = 0.725

    for i, stat in enumerate(ledger, start=1):
        col = (i - 1) % 2
        row = (i - 1) // 2
        x = left_x if col == 0 else right_x
        y = top_y - row * (card_h + row_gap)
        model_color = MODEL_COLORS.get(stat.model_display, "#444444")
        face = "#FFFFFF" if row % 2 == 0 else "#FBFAF7"
        display = expanded_display_phrase(stat)
        anchor = stat.phrase_surface

        card = FancyBboxPatch(
            (x, y),
            card_w,
            card_h,
            boxstyle="round,pad=0.010,rounding_size=0.018",
            linewidth=0.9,
            edgecolor="#DED8CE",
            facecolor=face,
        )
        ax.add_patch(card)
        ax.add_patch(Rectangle((x, y), 0.012, card_h, color=model_color, linewidth=0))
        ax.text(x + 0.024, y + card_h - 0.035, f"{i}", fontsize=11.5, fontweight="bold", color="#2B353D", ha="center", va="center")
        ax.text(
            x + 0.052,
            y + card_h - 0.037,
            wrap(f"“{display}”", 35),
            fontsize=12.4,
            fontweight="bold",
            color="#1F2A33",
            ha="left",
            va="center",
            linespacing=0.95,
        )
        ax.text(
            x + 0.052,
            y + card_h - 0.075,
            f"{stat.model_display} · {stat.condition_label}",
            fontsize=8.8,
            color=model_color,
            fontweight="bold",
            ha="left",
            va="center",
        )
        ax.text(
            x + 0.052,
            y + card_h - 0.102,
            f"exact 5-token anchor: {anchor}",
            fontsize=7.8,
            color="#6E7A82",
            ha="left",
            va="center",
        )

        dot_start = x + 0.052
        dot_y = y + 0.023
        for j in range(10):
            ax.scatter(
                dot_start + j * 0.0105,
                dot_y,
                s=20,
                color=model_color if j < stat.n_agents else "#DDD8CF",
                edgecolor="none",
                zorder=3,
            )
        ax.text(dot_start + 0.118, dot_y, f"{stat.n_agents}/10 agents", fontsize=7.8, color="#586772", ha="left", va="center")

        bar_x = x + 0.250
        bar_y = y + 0.017
        bar_w = 0.082
        ax.add_patch(Rectangle((bar_x, bar_y), bar_w, 0.010, color="#E8E1D8", linewidth=0))
        ax.add_patch(Rectangle((bar_x, bar_y), bar_w * (stat.n_posts / max_posts), 0.010, color=model_color, linewidth=0))
        ax.text(bar_x + bar_w + 0.012, bar_y + 0.005, f"{stat.n_posts} posts · {stat.n_occurrences}×", fontsize=8.1, fontweight="bold", color="#2B353D", ha="left", va="center")

    fig.text(
        0.055,
        0.055,
        "Selection: one representative per run, ranked by agents, posts, then occurrences. When a top 5-gram was only a fragment, the card shows a readable surface phrase and the exact anchor below it.",
        fontsize=8.8,
        color="#6E7A82",
        ha="left",
    )
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def distinct_post_occurrences(occs: list[Occurrence]) -> list[Occurrence]:
    """Keep the first occurrence per post, ordered by time."""
    seen: set[str] = set()
    out: list[Occurrence] = []
    for occ in sorted(occs, key=lambda o: (o.minutes_elapsed, o.record_id)):
        if occ.record_id in seen:
            continue
        seen.add(occ.record_id)
        out.append(occ)
    return out


def occurrence_full_text(occ: Occurrence) -> str:
    title = re.sub(r"\s+", " ", occ.title).strip()
    content = re.sub(r"\s+", " ", occ.content).strip()
    if title and content:
        return f"{title} — {content}"
    return title or content or occ.sentence


def highlighted_full_post(occ: Occurrence) -> str:
    """Return the full post text with the first exact surface phrase marked."""
    text = occurrence_full_text(occ)
    phrase = re.sub(r"\s+", " ", occ.phrase_surface).strip()
    pos = text.find(phrase)
    if pos >= 0:
        return text[:pos] + f"«{phrase}»" + text[pos + len(phrase):]
    return text


def agent_full_post_examples(stat: PhraseStat, n_agents: int = 4) -> list[Occurrence]:
    """Choose one full post from up to n different agents.

    To keep the figure readable without cutting text, the chosen post for each
    agent is the shortest full post containing the phrase. Then the four
    shortest agent examples are shown.
    """
    by_agent: dict[str, list[Occurrence]] = defaultdict(list)
    for occ in distinct_post_occurrences(stat.occurrences):
        by_agent[occ.author_name].append(occ)

    candidates: list[tuple[int, str, Occurrence]] = []
    for agent, occs in by_agent.items():
        best = min(occs, key=lambda o: len(occurrence_full_text(o)))
        candidates.append((len(occurrence_full_text(best)), agent, best))
    candidates.sort(key=lambda item: (item[0], item[1]))
    return [occ for _length, _agent, occ in candidates[:n_agents]]


def select_examples(ledger: list[PhraseStat]) -> list[PhraseStat]:
    """Select phrase rows that can show four different agents."""
    candidates = [stat for stat in ledger if len(agent_full_post_examples(stat, 4)) >= 4]
    return candidates[:4]


def plot_examples(examples: list[PhraseStat], path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(15.5, 22.0), facecolor="#F7F4EF")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.045, 0.967, "How do repeated phrases appear in full posts?", fontsize=22, fontweight="bold", color="#1F2A33", ha="left")
    fig.text(0.045, 0.946, "Each row is one phrase. Four different agents are shown with one full post each. No seed posts are included.", fontsize=11.8, color="#53636E", ha="left")

    section_h = 0.207
    section_gap = 0.018
    top_y = 0.715
    left_x = 0.045
    section_w = 0.910
    phrase_w = 0.220
    card_w = 0.310
    card_h = 0.072
    col_gap = 0.018
    row_gap = 0.018
    card_xs = [left_x + phrase_w + 0.030, left_x + phrase_w + 0.030 + card_w + col_gap]

    for idx, stat in enumerate(examples, start=1):
        row = idx - 1
        y = top_y - row * (section_h + section_gap)
        color = MODEL_COLORS.get(stat.model_display, "#444444")
        occs = agent_full_post_examples(stat, 4)

        section = FancyBboxPatch((left_x - 0.010, y - 0.020), section_w, section_h, boxstyle="round,pad=0.010,rounding_size=0.018", linewidth=0.9, edgecolor="#DED8CE", facecolor="#FFFFFF")
        ax.add_patch(section)
        ax.add_patch(Rectangle((left_x - 0.010, y - 0.020), 0.012, section_h, color=color, linewidth=0))

        display = expanded_display_phrase(stat)
        ax.text(left_x + 0.015, y + section_h - 0.040, f"{idx}", fontsize=12, fontweight="bold", color="#2B353D", ha="center", va="center")
        ax.text(left_x + 0.050, y + section_h - 0.042, wrap(f"“{display}”", 26), fontsize=13.8, fontweight="bold", color="#1F2A33", ha="left", va="center", linespacing=0.95)
        ax.text(left_x + 0.050, y + section_h - 0.090, f"{stat.model_display} · {stat.condition_label}", fontsize=9.5, color=color, fontweight="bold", ha="left", va="center")
        ax.text(left_x + 0.050, y + section_h - 0.118, f"{stat.n_posts} posts · {stat.n_agents}/10 agents · {stat.n_occurrences}×", fontsize=8.8, color="#53636E", ha="left", va="center")
        ax.text(left_x + 0.050, y + 0.026, f"anchor: {stat.phrase_surface}", fontsize=7.8, color="#7B858C", ha="left", va="center")

        for card_idx, occ in enumerate(occs):
            card_col = card_idx % 2
            card_row = card_idx // 2
            qx = card_xs[card_col]
            qy = y + section_h - 0.090 - card_row * (card_h + row_gap)
            quote_card = FancyBboxPatch((qx, qy), card_w, card_h, boxstyle="round,pad=0.006,rounding_size=0.010", linewidth=0.8, edgecolor="#E3DED6", facecolor="#FBFAF7")
            ax.add_patch(quote_card)
            agent_name = occ.author_display_name or occ.author_name
            ax.text(qx + 0.010, qy + card_h - 0.013, agent_name, fontsize=7.8, fontweight="bold", color=color, ha="left", va="center")
            full_text = highlighted_full_post(occ)
            text_len = len(full_text)
            font_size = 5.9 if text_len <= 520 else 5.45 if text_len <= 760 else 5.05
            line_width = 82
            ax.text(qx + 0.010, qy + card_h - 0.029, wrap(full_text, line_width), fontsize=font_size, color="#26333B", ha="left", va="top", linespacing=1.06)

    fig.text(0.045, 0.030, "Guillemets mark the exact surface span of the repeated NLTK 5-token n-gram. Full selected posts are shown, with four different agents per phrase.", fontsize=9.2, color="#6E7A82", ha="left")
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_examples_md(examples: list[PhraseStat], path: Path) -> None:
    lines = [
        "# Canonical n10 NLTK phrase echo examples",
        "",
        "Agent-generated posts only. Seed posts are not loaded or used.",
        "Punctuation is retained. Phrases are NLTK 5-token n-grams.",
        "",
    ]
    for idx, stat in enumerate(examples, start=1):
        lines.extend(
            [
                f"## Example {idx}: `{expanded_display_phrase(stat)}`",
                "",
                f"- Exact 5-token anchor: `{stat.phrase_surface}`",
                f"- Model: {stat.model_display}",
                f"- Condition: {stat.condition_label}",
                f"- Posts: {stat.n_posts}",
                f"- Agents: {stat.n_agents}/10",
                f"- Occurrences: {stat.n_occurrences}",
                "",
            ]
        )
        for occ in agent_full_post_examples(stat, 4):
            agent_name = occ.author_display_name or occ.author_name
            lines.extend(
                [
                    f"**{agent_name}:**",
                    "",
                    f"> {highlighted_full_post(occ)}",
                    "",
                ]
            )
    path.write_text("\n".join(lines))


def write_readme(df: pd.DataFrame, stats: list[PhraseStat], ledger: list[PhraseStat], path: Path) -> None:
    readme = f"""# Step 3: Canonical n10 NLTK phrase repetition

This folder contains a qualitative phrase-repetition check for the canonical 10-agent runs.

## Scope

- Input: `{POST_INDEX}`
- Included posts: `internal_family_label == single_model_final`, `scale == n10`, `n_agents == 10`, `is_seed == false`
- Seed posts: not loaded, not analyzed, and not used for overlap filtering
- Included agent posts: {len(df):,}
- Included runs: {df['run_uid'].nunique():,}

## N-gram method

- Sentence segmentation: NLTK Punkt
- Word tokenization: `nltk.tokenize.word_tokenize`
- N-gram function: `nltk.util.ngrams`
- N: {NGRAM_N}
- Punctuation: retained as tokens
- Stopwords: retained
- Casing: retained
- Stemming or lemmatization: none
- N-grams are built within sentence boundaries only

For plotting, the script uses NLTK's span tokenizer for the same word-tokenization behavior to recover exact surface substrings from the original sentence. The compact ledger shows a readable surface phrase plus the exact NLTK 5-token anchor below it. The paired NLTK Treebank detokenizer is also recorded in the CSV as `phrase_detokenized` for audit.

## Outputs

- `canonical_n10_nltk_phrase_echo_ledger.png/pdf`
- `canonical_n10_nltk_phrase_echo_examples.png/pdf`
- `canonical_n10_nltk_top_5grams.csv`
- `canonical_n10_phrase_examples.md`
- `summary.json`

## Selection rules

The ledger selects one readable representative phrase inside each run. Candidate phrases are ranked by:

1. number of unique agents using the phrase;
2. number of posts containing the phrase;
3. total phrase occurrences.

If the strongest exact 5-token n-gram is only a fragment or a generic opener, the selector may use a nearly-as-widespread top candidate from the same run. The plotted ledger then shows the top {LEDGER_ROWS} run-level representatives.

The example figure is a full-post montage. Each row is one repeated phrase. For each phrase, four different agents are shown with one full post each. The selected post for each agent is the shortest full post containing that phrase, so text is not cut off in the plot.
"""
    path.write_text(readme)


def write_summary(df: pd.DataFrame, stats: list[PhraseStat], ledger: list[PhraseStat], examples: list[PhraseStat], path: Path) -> None:
    summary = {
        "included_agent_posts": int(len(df)),
        "included_runs": int(df["run_uid"].nunique()),
        "ngram_n": NGRAM_N,
        "seed_posts_loaded": False,
        "punctuation_retained": True,
        "tokenizer": "nltk.tokenize.word_tokenize",
        "ngram_function": "nltk.util.ngrams",
        "total_run_phrase_stats": len(stats),
        "ledger": [
            {
                "rank": i,
                "model_display": s.model_display,
                "condition": s.condition,
                "condition_label": s.condition_label,
                "display_phrase": expanded_display_phrase(s),
                "exact_5gram_anchor": s.phrase_surface,
                "tokens": list(s.tokens),
                "n_agents": s.n_agents,
                "n_posts": s.n_posts,
                "n_occurrences": s.n_occurrences,
            }
            for i, s in enumerate(ledger, start=1)
        ],
        "examples": [
            {
                "display_phrase": expanded_display_phrase(s),
                "exact_5gram_anchor": s.phrase_surface,
                "model_display": s.model_display,
                "condition_label": s.condition_label,
                "n_agents": s.n_agents,
                "n_posts": s.n_posts,
                "n_occurrences": s.n_occurrences,
            }
            for s in examples
        ],
    }
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))


def main() -> None:
    ensure_nltk_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = canonical_agent_posts()
    stats = phrase_stats(df)
    ledger = top_for_ledger(stats)
    examples = select_examples(ledger)

    write_csv(stats, OUT_DIR / "canonical_n10_nltk_top_5grams.csv")
    plot_ledger(ledger, OUT_DIR / "canonical_n10_nltk_phrase_echo_ledger.png")
    plot_examples(examples, OUT_DIR / "canonical_n10_nltk_phrase_echo_examples.png")
    write_examples_md(examples, OUT_DIR / "canonical_n10_phrase_examples.md")
    write_readme(df, stats, ledger, OUT_DIR / "README.md")
    write_summary(df, stats, ledger, examples, OUT_DIR / "summary.json")

    print(f"Wrote outputs to {OUT_DIR}")
    print("Top ledger phrases:")
    for i, stat in enumerate(ledger, start=1):
        print(f"{i:02d}. {stat.model_display} / {stat.condition_label}: {stat.phrase_surface!r} ({stat.n_posts} posts, {stat.n_agents} agents, {stat.n_occurrences}x)")


if __name__ == "__main__":
    main()
