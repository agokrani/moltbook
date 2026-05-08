#!/usr/bin/env python3
"""Step 4: scale phrase adoption for GPT-5 and Gemini Flash Lite.

Question: does adding more agents dilute local phrase attractors, or do repeated
phrases spread across more agents?

This uses agent-generated posts only, first 60 minutes only, and NLTK 5-token
n-gram anchors. Seed posts are not loaded or used.
"""
from __future__ import annotations

import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch

try:
    from nltk.tokenize import PunktTokenizer, word_tokenize
    from nltk.tokenize.destructive import NLTKWordTokenizer
    from nltk.tokenize.treebank import TreebankWordDetokenizer
    from nltk.util import ngrams as nltk_ngrams
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "NLTK is required for Step 4. Install it in a virtual environment, for example:\n"
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
    PLOT_ROOT,
    setup_style,
)

POST_INDEX = AYUSH_ROOT / "post_index.csv"
OUT_DIR = PLOT_ROOT / "step04_scale_phrase_adoption"
NGRAM_N = 5
MODELS = ["GPT-5", "Gemini Flash Lite"]
SCALES = [10, 20, 30]
TIME_MIN = 0.0
TIME_MAX = 60.0

SENTENCE_TOKENIZER = PunktTokenizer("english")
SPAN_WORD_TOKENIZER = NLTKWordTokenizer()
DETOKENIZER = TreebankWordDetokenizer()

MODEL_COLORS = {
    "GPT-5": "#3B6EA8",
    "Gemini Flash Lite": "#7B4EA3",
}
SCALE_JITTER = {
    "mag0": -0.18,
    "mag1": -0.11,
    "mag5": -0.04,
    "mag25": 0.04,
    "dom-agi": 0.11,
    "dom-tech": 0.18,
}

# Same readability helpers as Step 3. The exact anchor remains the measured unit.
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


@dataclass(frozen=True)
class Occurrence:
    record_id: str
    author_name: str
    sentence: str
    phrase_surface: str
    tokens: tuple[str, ...]


@dataclass
class PhraseStat:
    tokens: tuple[str, ...]
    phrase_surface: str
    occurrences: list[Occurrence]
    n_mentions: int
    n_posts: int
    n_adopters: int
    top_agent_mentions: int

    @property
    def top_agent_share(self) -> float:
        return self.top_agent_mentions / self.n_mentions if self.n_mentions else math.nan

    @property
    def sort_key(self) -> tuple[int, int, int, str]:
        return (self.n_adopters, self.n_posts, self.n_mentions, self.phrase_surface.lower())


def ensure_nltk_ready() -> None:
    try:
        _ = word_tokenize("A short tokenizer check.")
        _ = list(SENTENCE_TOKENIZER.span_tokenize("A sentence. Another sentence."))
    except LookupError as exc:
        raise SystemExit(
            "NLTK tokenizer data are missing. Run:\n"
            "  python -m nltk.downloader punkt punkt_tab\n"
            "inside the environment used for this script."
        ) from exc


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


def load_scale_posts() -> pd.DataFrame:
    df = pd.read_csv(POST_INDEX, low_memory=False)
    sub = df[
        (df["internal_family_label"] == "single_model_final")
        & (df["model_display"].isin(MODELS))
        & (df["n_agents"].isin(SCALES))
        & (~df["is_seed"].astype(bool))
        & (pd.to_numeric(df["minutes_elapsed"], errors="coerce") >= TIME_MIN)
        & (pd.to_numeric(df["minutes_elapsed"], errors="coerce") <= TIME_MAX)
    ].copy()
    sub = sub.sort_values(["model_display", "n_agents", "condition", "run_uid", "minutes_elapsed", "post_id"])
    return sub


def sentence_spans(text: str) -> Iterable[tuple[int, int, str]]:
    if not text.strip():
        return []
    return ((start, end, text[start:end]) for start, end in SENTENCE_TOKENIZER.span_tokenize(text))


def make_occurrence(row: pd.Series, sentence: str, surface: str, tokens: tuple[str, ...]) -> Occurrence:
    return Occurrence(
        record_id=clean_cell(row.get("record_id", "")),
        author_name=clean_cell(row.get("author_name", "")),
        sentence=" ".join(sentence.split()),
        phrase_surface=" ".join(surface.split()),
        tokens=tokens,
    )


def ngram_occurrences_for_post(row: pd.Series) -> list[Occurrence]:
    text = post_text(row)
    out: list[Occurrence] = []
    for _start, _end, sent in sentence_spans(text):
        tokens = word_tokenize(sent)
        if len(tokens) < NGRAM_N:
            continue
        spans = list(SPAN_WORD_TOKENIZER.span_tokenize(sent))
        if len(spans) != len(tokens):
            for gram in nltk_ngrams(tokens, NGRAM_N):
                detok = DETOKENIZER.detokenize(list(gram))
                out.append(make_occurrence(row, sent, detok, tuple(gram)))
            continue
        for idx, gram in enumerate(nltk_ngrams(tokens, NGRAM_N)):
            start = spans[idx][0]
            end = spans[idx + NGRAM_N - 1][1]
            surface = sent[start:end]
            out.append(make_occurrence(row, sent, surface, tuple(gram)))
    return out


def choose_surface(occurrences: list[Occurrence]) -> str:
    return Counter(o.phrase_surface for o in occurrences).most_common(1)[0][0]


def phrase_stats_for_run(sub: pd.DataFrame) -> list[PhraseStat]:
    by_tokens: dict[tuple[str, ...], list[Occurrence]] = defaultdict(list)
    for _, row in sub.iterrows():
        for occ in ngram_occurrences_for_post(row):
            by_tokens[occ.tokens].append(occ)

    stats: list[PhraseStat] = []
    for tokens, occs in by_tokens.items():
        posts = {occ.record_id for occ in occs}
        agent_counts = Counter(occ.author_name for occ in occs)
        stats.append(
            PhraseStat(
                tokens=tokens,
                phrase_surface=choose_surface(occs),
                occurrences=occs,
                n_mentions=len(occs),
                n_posts=len(posts),
                n_adopters=len(agent_counts),
                top_agent_mentions=max(agent_counts.values()) if agent_counts else 0,
            )
        )
    return stats


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


def representative_for_run(stats: list[PhraseStat]) -> PhraseStat:
    ranked = sorted(stats, key=lambda s: s.sort_key, reverse=True)
    top = ranked[0]
    for margin in (1, 2, 3):
        minimum_agents = max(1, top.n_adopters - margin)
        candidates = [
            stat for stat in ranked[:15]
            if stat.n_adopters >= minimum_agents
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


def find_token_match(tokens: list[str], target: tuple[str, ...]) -> int | None:
    n = len(target)
    for idx in range(len(tokens) - n + 1):
        if tuple(tokens[idx : idx + n]) == target:
            return idx
    return None


def expanded_display_phrase(stat: PhraseStat) -> str:
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
        return " ".join(occ.sentence[spans[start][0] : spans[end][1]].split())
    return stat.phrase_surface


def build_run_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = ["model_display", "condition", "n_agents", "run_uid", "run_id"]
    for (model, condition, n_agents, run_uid, run_id), sub in df.groupby(group_cols, sort=False):
        stats = phrase_stats_for_run(sub)
        if not stats:
            continue
        # For the scale metric, use the raw strongest exact NLTK anchor.
        # No readability filtering is applied to the measured phrase.
        stat = sorted(stats, key=lambda s: s.sort_key, reverse=True)[0]
        rows.append(
            {
                "model_display": model,
                "condition": condition,
                "condition_label": CONDITION_LABELS.get(condition, condition),
                "n_agents": int(n_agents),
                "run_uid": run_uid,
                "run_id": run_id,
                "n_posts_total": int(sub["record_id"].nunique()),
                "top_phrase_display": expanded_display_phrase(stat),
                "top_phrase_anchor": stat.phrase_surface,
                "tokens_json": json.dumps(list(stat.tokens), ensure_ascii=False),
                "adopters": stat.n_adopters,
                "adoption_rate": stat.n_adopters / int(n_agents),
                "phrase_posts": stat.n_posts,
                "mentions": stat.n_mentions,
                "top_agent_mentions": stat.top_agent_mentions,
                "top_agent_share": stat.top_agent_share,
            }
        )
    return pd.DataFrame(rows).sort_values(["model_display", "n_agents", "condition"])


def build_summary_table(run_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (model, n_agents), sub in run_df.groupby(["model_display", "n_agents"], sort=False):
        rows.append(
            {
                "model_display": model,
                "n_agents": int(n_agents),
                "n_runs": int(len(sub)),
                "mean_adopters": float(sub["adopters"].mean()),
                "median_adopters": float(sub["adopters"].median()),
                "mean_adoption_rate": float(sub["adoption_rate"].mean()),
                "median_adoption_rate": float(sub["adoption_rate"].median()),
                "mean_phrase_posts": float(sub["phrase_posts"].mean()),
                "median_phrase_posts": float(sub["phrase_posts"].median()),
                "mean_mentions": float(sub["mentions"].mean()),
                "median_mentions": float(sub["mentions"].median()),
                "mean_top_agent_share": float(sub["top_agent_share"].mean()),
                "median_top_agent_share": float(sub["top_agent_share"].median()),
            }
        )
    return pd.DataFrame(rows).sort_values(["model_display", "n_agents"])


def plot_scale_adoption(run_df: pd.DataFrame, summary_df: pd.DataFrame, path: Path) -> None:
    """Paper-facing scale plot with no condition spaghetti.

    The stricter scale-normalized metric is adoption rate. Absolute adopter
    counts are shown only as rounded labels, because the count is an average
    over six conditions and can be fractional.
    """
    setup_style()
    fig = plt.figure(figsize=(11.6, 6.9), facecolor="#F7F4EF")
    gs = fig.add_gridspec(1, 2, left=0.08, right=0.96, top=0.76, bottom=0.25, wspace=0.20)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])

    fig.text(
        0.08,
        0.935,
        "Does a larger agent group dilute the top phrase?",
        fontsize=20.5,
        fontweight="bold",
        color="#1F2A33",
        ha="left",
    )
    fig.text(
        0.08,
        0.888,
        "Each point is the mean across six matched seed conditions. First 60 minutes, agent posts only.",
        fontsize=11.2,
        color="#53636E",
        ha="left",
    )

    def label_position(x: float, y: float, model: str, panel: str) -> tuple[float, float, str, str]:
        if x <= 10:
            dx, ha = 0.55, "left"
        elif x >= 30:
            dx, ha = -0.35, "right"
        else:
            dx, ha = 0.0, "center"
        if panel == "adoption":
            dy = 0.045 if model == "GPT-5" else -0.045
        else:
            dy = 0.028 if model == "GPT-5" else -0.028
        va = "bottom" if dy > 0 else "top"
        return x + dx, y + dy, ha, va

    for model in MODELS:
        sub = summary_df[summary_df["model_display"] == model].sort_values("n_agents")
        color = MODEL_COLORS[model]
        ax1.plot(
            sub["n_agents"],
            sub["mean_adoption_rate"],
            color=color,
            linewidth=3.4,
            marker="o",
            markersize=9,
            label=model,
        )
        for _, r in sub.iterrows():
            dy = 0.035 if model == "GPT-5" else -0.035
            va = "bottom" if model == "GPT-5" else "top"
            label = f"≈{int(round(r['mean_adopters']))}/{int(r['n_agents'])} agents"
            tx, ty, ha, va = label_position(float(r["n_agents"]), float(r["mean_adoption_rate"]), model, "adoption")
            ax1.text(
                tx,
                ty,
                label.replace(" agents", ""),
                ha=ha,
                va=va,
                fontsize=9.8,
                fontweight="bold",
                color=color,
            )

    ax1.set_title("Top phrase remains widely adopted", fontsize=15, fontweight="bold", color="#1F2A33", pad=12)
    ax1.set_ylabel("Mean adoption rate of run's top phrase")
    ax1.set_xticks(SCALES)
    ax1.set_xticklabels(["10 agents", "20 agents", "30 agents"])
    ax1.set_ylim(0, 1.0)
    ax1.set_yticks([0, 0.25, 0.50, 0.75, 1.0])
    ax1.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    ax1.grid(axis="y", color="#E6DED4", linewidth=0.9)
    ax1.set_facecolor("#FFFFFF")
    ax1.spines["left"].set_color("#D3CABF")
    ax1.spines["bottom"].set_color("#D3CABF")
    ax1.legend(frameon=False, loc="upper left")

    for model in MODELS:
        sub = summary_df[summary_df["model_display"] == model].sort_values("n_agents")
        color = MODEL_COLORS[model]
        ax2.plot(
            sub["n_agents"],
            sub["mean_top_agent_share"],
            color=color,
            linewidth=3.4,
            marker="o",
            markersize=9,
            label=model,
        )
        for _, r in sub.iterrows():
            dy = 0.025 if model == "GPT-5" else -0.025
            va = "bottom" if model == "GPT-5" else "top"
            tx, ty, ha, va = label_position(float(r["n_agents"]), float(r["mean_top_agent_share"]), model, "share")
            ax2.text(
                tx,
                ty,
                f"{100 * float(r['mean_top_agent_share']):.0f}%",
                ha=ha,
                va=va,
                fontsize=10.5,
                fontweight="bold",
                color=color,
            )

    ax2.set_title("Top user becomes less dominant", fontsize=15, fontweight="bold", color="#1F2A33", pad=12)
    ax2.set_ylabel("Mean share of phrase mentions by top user")
    ax2.set_xticks(SCALES)
    ax2.set_xticklabels(["10 agents", "20 agents", "30 agents"])
    ax2.set_ylim(0, 0.36)
    ax2.set_yticks([0, 0.1, 0.2, 0.3])
    ax2.set_yticklabels(["0%", "10%", "20%", "30%"])
    ax2.grid(axis="y", color="#E6DED4", linewidth=0.9)
    ax2.set_facecolor("#FFFFFF")
    ax2.spines["left"].set_color("#D3CABF")
    ax2.spines["bottom"].set_color("#D3CABF")

    card = FancyBboxPatch(
        (0.08, 0.075),
        0.88,
        0.082,
        transform=fig.transFigure,
        boxstyle="round,pad=0.012,rounding_size=0.015",
        linewidth=0.9,
        edgecolor="#DED8CE",
        facecolor="#FFFFFF",
    )
    fig.patches.append(card)
    fig.text(0.105, 0.118, "Interpretation:", fontsize=10.8, fontweight="bold", color="#1F2A33", ha="left")
    fig.text(
        0.215,
        0.118,
        "scale does not eliminate the attractor. The top phrase still reaches most agents, while repetition is less dominated by one agent.",
        fontsize=10.4,
        color="#40505A",
        ha="left",
    )
    fig.text(
        0.08,
        0.027,
        "Metric: strongest exact NLTK 5-token phrase anchor per run, ranked by adopters, then posts, then mentions. Seed posts are excluded.",
        fontsize=8.8,
        color="#6E7A82",
        ha="left",
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def markdown_table(df: pd.DataFrame) -> str:
    def fmt(x: object) -> str:
        if isinstance(x, (float, np.floating)):
            return f"{float(x):.3f}"
        return str(x)
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def write_readme(run_df: pd.DataFrame, summary_df: pd.DataFrame, path: Path) -> None:
    display_summary = summary_df[[
        "model_display", "n_agents", "mean_adopters", "mean_adoption_rate", "mean_phrase_posts", "mean_top_agent_share",
    ]].copy()
    text = f"""# Step 4: scale phrase adoption

Question: does adding more agents dilute local phrase attractors, or do repeated phrases spread across more agents?

## Scope

- Models: GPT-5 and Gemini Flash Lite
- Scales: 10, 20, 30 agents
- Conditions: six canonical seed conditions
- Time window: first 60 minutes, `0 <= minutes_elapsed <= 60`
- Posts: agent-generated posts only, `is_seed == false`
- Seed posts: not loaded and not used

## N-gram method

- Sentence segmentation: NLTK Punkt
- Tokenizer: `nltk.tokenize.word_tokenize`
- N-gram function: `nltk.util.ngrams`
- N: {NGRAM_N}
- Punctuation retained
- Casing retained
- Stopwords retained
- No stemming or lemmatization
- N-grams are built within sentence boundaries only

## Run-level selection

For each run, the script finds a representative top phrase anchor. Exact 5-token anchors are ranked by:

1. unique agents using the anchor;
2. posts containing the anchor;
3. total mentions.

No seed-overlap filtering, generic-phrase filtering, stemming, lemmatization, or readability substitution is applied. The measured phrase is the raw strongest exact NLTK 5-token anchor for that run.

## How to read the plot

- Adoption rate = agents using the top phrase / total agents.
- Top-agent share = share of mentions made by the single most frequent user of that phrase.
- If adoption rate stays flat or rises with scale, scale did not dilute the attractor.
- If top-agent share falls with scale, repetition is more collective rather than driven by one spammer.

## Outputs

- `scale_phrase_adoption_gpt5_gemini.png/pdf`
- `scale_phrase_adoption_by_run.csv`
- `scale_phrase_adoption_summary.csv`
- `summary.json`

## Summary

{markdown_table(display_summary)}
"""
    path.write_text(text)


def write_summary_json(run_df: pd.DataFrame, summary_df: pd.DataFrame, path: Path) -> None:
    summary = {
        "time_window_minutes": [TIME_MIN, TIME_MAX],
        "seed_posts_loaded": False,
        "models": MODELS,
        "scales": SCALES,
        "n_runs": int(len(run_df)),
        "run_rows": run_df.to_dict(orient="records"),
        "summary_rows": summary_df.to_dict(orient="records"),
    }
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False))


def main() -> None:
    ensure_nltk_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_scale_posts()
    run_df = build_run_table(df)
    summary_df = build_summary_table(run_df)

    run_df.to_csv(OUT_DIR / "scale_phrase_adoption_by_run.csv", index=False)
    summary_df.to_csv(OUT_DIR / "scale_phrase_adoption_summary.csv", index=False)
    plot_scale_adoption(run_df, summary_df, OUT_DIR / "scale_phrase_adoption_gpt5_gemini.png")
    write_readme(run_df, summary_df, OUT_DIR / "README.md")
    write_summary_json(run_df, summary_df, OUT_DIR / "summary.json")

    print(f"Wrote outputs to {OUT_DIR}")
    print(summary_df[["model_display", "n_agents", "mean_adopters", "mean_adoption_rate", "mean_top_agent_share"]].to_string(index=False))


if __name__ == "__main__":
    main()
