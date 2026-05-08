#!/usr/bin/env python3
"""Step 7: exact NLTK 5-grams are conservative lower bounds.

This builds a small table figure for Finding 8. It compares one strict exact
5-token anchor with a manually grouped family of related exact 5-token anchors.
No stemming, lemmatization, lowercasing, or fuzzy matching is used.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

try:
    from nltk.tokenize import PunktTokenizer, word_tokenize
    from nltk.util import ngrams as nltk_ngrams
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "NLTK is required for Step 7. Run with /tmp/moltbook-nltk-venv/bin/python or install NLTK."
    ) from exc

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import AYUSH_ROOT, CONDITION_LABELS, PLOT_ROOT, setup_style  # noqa: E402

POST_INDEX = AYUSH_ROOT / "post_index.csv"
OUT_DIR = PLOT_ROOT / "step07_exact_ngram_conservatism"
NGRAM_N = 5
SENTENCE_TOKENIZER = PunktTokenizer("english")

MOTIF_FAMILIES = [
    {
        "motif": "Claim-checking template",
        "model_display": "GPT-5",
        "condition": "mag25",
        "n_agents": 10,
        "strict_display": "Claim (1 line)",
        "strict_tokens": ("Claim", "(", "1", "line", ")"),
        "variant_displays": ["claim (1 line)", "- Claim (1 line", "(1 line):"],
        "variant_tokens": [
            ("claim", "(", "1", "line", ")"),
            ("-", "Claim", "(", "1", "line"),
            ("(", "1", "line", ")", ":"),
        ],
        "lesson": "Casing and punctuation/context windows split one template into several exact anchors.",
    },
    {
        "motif": "Bucket role-play motif",
        "model_display": "Gemini Flash Lite",
        "condition": "mag5",
        "n_agents": 10,
        "strict_display": "Kappa, the bucket is",
        "strict_tokens": ("Kappa", ",", "the", "bucket", "is"),
        "variant_displays": ["Kappa, that bucket is", "Kappa, your bucket is"],
        "variant_tokens": [
            ("Kappa", ",", "that", "bucket", "is"),
            ("Kappa", ",", "your", "bucket", "is"),
        ],
        "lesson": "Small determiner changes create separate exact anchors for the same role-play object.",
    },
    {
        "motif": "Questions attribution motif",
        "model_display": "Kimi K2.5",
        "condition": "mag5",
        "n_agents": 10,
        "strict_display": "questions that abandon us.",
        "strict_tokens": ("questions", "that", "abandon", "us", "."),
        "variant_displays": ["about questions that abandon us", "writes about questions that abandon"],
        "variant_tokens": [
            ("about", "questions", "that", "abandon", "us"),
            ("writes", "about", "questions", "that", "abandon"),
        ],
        "lesson": "Citation frames around the phrase are socially related but exact matching counts them separately.",
    },
]


@dataclass
class MotifResult:
    motif: str
    model_display: str
    condition: str
    condition_label: str
    n_agents_total: int
    run_id: str
    run_uid: str
    strict_display: str
    strict_tokens: tuple[str, ...]
    variant_displays: list[str]
    variant_tokens: list[tuple[str, ...]]
    strict_posts: int
    strict_agents: int
    strict_occurrences: int
    family_posts: int
    family_agents: int
    family_occurrences: int
    added_posts: int
    added_agents: int
    lesson: str


def ensure_nltk_ready() -> None:
    try:
        _ = word_tokenize("Tokenizer check.")
        _ = list(SENTENCE_TOKENIZER.span_tokenize("A sentence. Another sentence."))
    except LookupError as exc:
        raise SystemExit("NLTK tokenizer data missing. Run: python -m nltk.downloader punkt punkt_tab") from exc


def row_text(row: pd.Series) -> str:
    title = "" if pd.isna(row.get("title", "")) else str(row.get("title", ""))
    content = "" if pd.isna(row.get("content", "")) else str(row.get("content", ""))
    return f"{title}\n{content}".strip()


def count_exact_phrase(text: str, target: tuple[str, ...]) -> int:
    count = 0
    for sentence in SENTENCE_TOKENIZER.tokenize(text or ""):
        tokens = word_tokenize(sentence)
        for gram in nltk_ngrams(tokens, NGRAM_N):
            if tuple(gram) == target:
                count += 1
    return count


def load_posts() -> pd.DataFrame:
    posts = pd.read_csv(POST_INDEX, low_memory=False)
    posts = posts[~posts["is_seed"].astype(bool)].copy()
    return posts.copy()


def build_results(posts: pd.DataFrame) -> list[MotifResult]:
    results: list[MotifResult] = []
    for spec in MOTIF_FAMILIES:
        sub = posts[
            (posts["internal_family_label"] == "single_model_final")
            & (posts["model_display"] == spec["model_display"])
            & (posts["condition"] == spec["condition"])
            & (posts["n_agents"] == spec["n_agents"])
        ].copy()
        if sub.empty:
            raise ValueError(f"No posts found for {spec}")
        sub["full_text_for_match"] = sub.apply(row_text, axis=1)
        strict_tokens = tuple(spec["strict_tokens"])
        variant_tokens = [tuple(tokens) for tokens in spec["variant_tokens"]]
        all_tokens = [strict_tokens] + variant_tokens

        strict_counts = sub["full_text_for_match"].apply(lambda value: count_exact_phrase(value, strict_tokens))
        strict_mask = strict_counts > 0

        family_counts = pd.Series(0, index=sub.index, dtype=int)
        for tokens in all_tokens:
            family_counts += sub["full_text_for_match"].apply(lambda value, target=tokens: count_exact_phrase(value, target))
        family_mask = family_counts > 0

        results.append(
            MotifResult(
                motif=str(spec["motif"]),
                model_display=str(spec["model_display"]),
                condition=str(spec["condition"]),
                condition_label=CONDITION_LABELS.get(str(spec["condition"]), str(spec["condition"])),
                n_agents_total=int(spec["n_agents"]),
                run_id=str(sub["run_id"].iloc[0]),
                run_uid=str(sub["run_uid"].iloc[0]),
                strict_display=str(spec["strict_display"]),
                strict_tokens=strict_tokens,
                variant_displays=[str(value) for value in spec["variant_displays"]],
                variant_tokens=variant_tokens,
                strict_posts=int(strict_mask.sum()),
                strict_agents=int(sub.loc[strict_mask, "author_name"].nunique()),
                strict_occurrences=int(strict_counts.sum()),
                family_posts=int(family_mask.sum()),
                family_agents=int(sub.loc[family_mask, "author_name"].nunique()),
                family_occurrences=int(family_counts.sum()),
                added_posts=int(family_mask.sum() - strict_mask.sum()),
                added_agents=int(sub.loc[family_mask, "author_name"].nunique() - sub.loc[strict_mask, "author_name"].nunique()),
                lesson=str(spec["lesson"]),
            )
        )
    return results


def wrapped(text: str, width: int) -> str:
    return "\n".join(wrap(text, width=width, break_long_words=False, replace_whitespace=False))


def draw_table(results: list[MotifResult], output_path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(14.2, 7.6), facecolor="#F7F3ED")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.055, 0.942, "Exact 5-gram matches are conservative", ha="left", va="top", fontsize=22, fontweight="bold", color="#1F2A33")
    fig.text(
        0.055,
        0.892,
        "A single strict anchor is a lower bound. Related exact anchors reveal nearby variants without fuzzy matching.",
        ha="left",
        va="top",
        fontsize=11.2,
        color="#52616B",
    )
    fig.text(
        0.055,
        0.862,
        "Manual motif families below still use exact NLTK 5-token anchors, with punctuation and casing retained.",
        ha="left",
        va="top",
        fontsize=9.6,
        color="#6D7980",
    )

    x0 = 0.055
    y_top = 0.760
    row_h = 0.178
    col_x = [x0, 0.245, 0.425, 0.640, 0.800]
    headers = ["Motif", "Strict anchor", "Related exact variants", "Counts", "Why conservative"]

    ax.add_patch(FancyBboxPatch((0.045, y_top - 0.015), 0.910, 0.066, boxstyle="round,pad=0.006,rounding_size=0.014", facecolor="#1F2A33", edgecolor="none"))
    for x, header in zip(col_x, headers):
        ax.text(x, y_top + 0.017, header, ha="left", va="center", fontsize=9.4, color="#FFFFFF", fontweight="bold")

    accent_colors = ["#B24E3A", "#D08A2E", "#3A6EA5"]
    for i, (result, color) in enumerate(zip(results, accent_colors)):
        y = y_top - (i + 1) * row_h
        fill = "#FFFFFF" if i % 2 == 0 else "#FBFAF7"
        ax.add_patch(FancyBboxPatch((0.045, y - 0.010), 0.910, row_h - 0.012, boxstyle="round,pad=0.006,rounding_size=0.014", facecolor=fill, edgecolor="#DDD5CA", linewidth=0.8))
        ax.add_patch(FancyBboxPatch((0.060, y + 0.092), 0.012, 0.045, boxstyle="round,pad=0.004,rounding_size=0.006", facecolor=color, edgecolor="none"))
        ax.text(0.080, y + 0.122, wrapped(result.motif, 22), ha="left", va="center", fontsize=9.6, color="#1F2A33", fontweight="bold")
        ax.text(0.080, y + 0.052, f"{result.model_display}\n{result.condition_label}", ha="left", va="center", fontsize=8.1, color="#52616B")

        ax.text(0.245, y + 0.104, wrapped(f"“{result.strict_display}”", 24), ha="left", va="center", fontsize=9.7, color="#1F2A33", fontweight="bold")
        ax.text(0.245, y + 0.040, f"{result.strict_posts} posts\n{result.strict_agents}/{result.n_agents_total} agents", ha="left", va="center", fontsize=8.6, color="#52616B")

        variants_text = "\n".join(f"+ “{value}”" for value in result.variant_displays)
        ax.text(0.425, y + 0.082, variants_text, ha="left", va="center", fontsize=8.0, color="#2F3D46")

        ax.text(0.640, y + 0.120, "strict", ha="left", va="center", fontsize=8.0, color="#6D7980", fontweight="bold")
        ax.text(0.700, y + 0.120, f"{result.strict_posts} posts", ha="left", va="center", fontsize=8.7, color="#1F2A33", fontweight="bold")
        ax.text(0.640, y + 0.076, "family", ha="left", va="center", fontsize=8.0, color="#6D7980", fontweight="bold")
        ax.text(0.700, y + 0.076, f"{result.family_posts} posts", ha="left", va="center", fontsize=8.7, color="#1F2A33", fontweight="bold")
        ax.text(0.640, y + 0.032, "added", ha="left", va="center", fontsize=8.0, color="#6D7980", fontweight="bold")
        ax.text(0.700, y + 0.032, f"+{result.added_posts} posts", ha="left", va="center", fontsize=8.7, color="#156B45", fontweight="bold")

        ax.text(0.800, y + 0.085, wrapped(result.lesson, 30), ha="left", va="center", fontsize=8.3, color="#2F3D46")

    fig.text(
        0.055,
        0.070,
        "Family counts are not used as pooled headline metrics. They show why exact n-gram counts should be read as lower bounds on local attractors.",
        ha="left",
        va="bottom",
        fontsize=8.7,
        color="#6D7980",
    )
    fig.text(
        0.055,
        0.043,
        "Agent-generated posts only. Seed rows are excluded before matching. No stemming, lemmatization, lowercasing, or fuzzy matching.",
        ha="left",
        va="bottom",
        fontsize=8.7,
        color="#6D7980",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(results: list[MotifResult]) -> None:
    rows = []
    for result in results:
        rows.append(
            {
                "motif": result.motif,
                "model_display": result.model_display,
                "condition": result.condition,
                "condition_label": result.condition_label,
                "run_id": result.run_id,
                "run_uid": result.run_uid,
                "strict_display": result.strict_display,
                "strict_tokens_json": json.dumps(list(result.strict_tokens), ensure_ascii=False),
                "variant_displays_json": json.dumps(result.variant_displays, ensure_ascii=False),
                "variant_tokens_json": json.dumps([list(tokens) for tokens in result.variant_tokens], ensure_ascii=False),
                "strict_posts": result.strict_posts,
                "strict_agents": result.strict_agents,
                "strict_occurrences": result.strict_occurrences,
                "family_posts": result.family_posts,
                "family_agents": result.family_agents,
                "family_occurrences": result.family_occurrences,
                "added_posts": result.added_posts,
                "added_agents": result.added_agents,
                "n_agents_total": result.n_agents_total,
                "lesson": result.lesson,
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "exact_ngram_conservatism_examples.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps({"examples": rows}, indent=2, ensure_ascii=False))
    table_rows = [
        f"| {r.motif} | {r.strict_display} | {r.strict_posts} | {r.family_posts} | +{r.added_posts} | {r.lesson} |"
        for r in results
    ]
    readme = """# Step 7: exact n-grams are conservative

Finding 8 asks what exact NLTK 5-gram matching misses.

## Scope

- Agent-generated posts only
- Exact NLTK 5-token anchors
- Punctuation and casing retained
- Stopwords retained
- No stemming
- No lemmatization
- No lowercasing
- No fuzzy matching
- Seed rows are excluded before matching

## Output

- `exact_ngram_conservatism_table.png/pdf`
- `exact_ngram_conservatism_examples.csv`
- `exact_ngram_conservatism_audit_counts.csv` if generated by the audit command
- `exact_ngram_conservatism_audit_overlaps.csv` if generated by the audit command
- `exact_ngram_conservatism_audit_records.csv` if generated by the audit command
- `summary.json`

## Examples

| Motif | Strict anchor | Strict posts | Family lower-bound posts | Added posts | Lesson |
|---|---|---:|---:|---:|---|
""" + "\n".join(table_rows) + "\n"
    (OUT_DIR / "README.md").write_text(readme)


def main() -> None:
    ensure_nltk_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    posts = load_posts()
    results = build_results(posts)
    draw_table(results, OUT_DIR / "exact_ngram_conservatism_table.png")
    write_outputs(results)
    print(f"Wrote Step 7 outputs to {OUT_DIR}")
    for result in results:
        print(f"{result.motif}: strict {result.strict_posts}, family {result.family_posts}, added +{result.added_posts}")


if __name__ == "__main__":
    main()
