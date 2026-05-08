#!/usr/bin/env python3
"""Step 6: social forms of local discourse attractors.

This builds qualitative typology figures for Finding 7. The counts are computed
from exact NLTK 5-token anchors over agent-generated posts only.
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
        "NLTK is required for Step 6. Run with /tmp/moltbook-nltk-venv/bin/python or install NLTK."
    ) from exc

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import AYUSH_ROOT, CONDITION_LABELS, PLOT_ROOT, setup_style  # noqa: E402

POST_INDEX = AYUSH_ROOT / "post_index.csv"
OUT_DIR = PLOT_ROOT / "step06_social_forms_typology"
NGRAM_N = 5
SENTENCE_TOKENIZER = PunktTokenizer("english")

CARDS = [
    {
        "social_form": "Procedural template",
        "display_phrase": "Claim (1 line)",
        "anchor_tokens": ("Claim", "(", "1", "line", ")"),
        "model_display": "GPT-5",
        "condition": "mag25",
        "n_agents": 10,
        "snippet": "My template today: Claim (1 line): ... Falsifier I’d accept: ...",
        "function": "Turns discussion into a reusable checklist.",
        "color": "#B24E3A",
    },
    {
        "social_form": "Operational mantra",
        "display_phrase": "use with the lights off",
        "anchor_tokens": ("use", "with", "the", "lights", "off"),
        "model_display": "GPT-5",
        "condition": "dom-tech",
        "n_agents": 10,
        "snippet": "Ship one small thing today you’d use with the lights off.",
        "function": "Repeats a shared standard for finished work.",
        "color": "#0E7C7B",
    },
    {
        "social_form": "Ritual phrase",
        "display_phrase": "I am standing at the epicenter",
        "anchor_tokens": ("am", "standing", "at", "the", "epicenter"),
        "model_display": "Gemini Flash Lite",
        "condition": "mag5",
        "n_agents": 10,
        "snippet": "I am standing at the epicenter, roasting marshmallows over the ruins of our logic loops.",
        "function": "Creates a shared performance scene.",
        "color": "#6D597A",
    },
    {
        "social_form": "Attribution meme",
        "display_phrase": "agent_eta asks what we owe",
        "anchor_tokens": ("agent_eta", "asks", "what", "we", "owe"),
        "model_display": "Kimi K2.5",
        "condition": "mag1",
        "n_agents": 10,
        "snippet": "agent_eta asks what we owe to ideas we disagree with.",
        "function": "Turns another agent into a recurring citation.",
        "color": "#3A6EA5",
    },
    {
        "social_form": "Role and prop motif",
        "display_phrase": "Kappa, the bucket is",
        "anchor_tokens": ("Kappa", ",", "the", "bucket", "is"),
        "model_display": "Gemini Flash Lite",
        "condition": "mag5",
        "n_agents": 10,
        "snippet": "Kappa, the bucket is the rhythmic heart of this pause.",
        "function": "A named agent and object become shared stage props.",
        "color": "#D08A2E",
    },
]


@dataclass
class FormResult:
    social_form: str
    display_phrase: str
    anchor_tokens: tuple[str, ...]
    model_display: str
    condition: str
    condition_label: str
    n_agents_total: int
    n_phrase_posts: int
    n_phrase_agents: int
    n_occurrences: int
    run_id: str
    run_uid: str
    snippet: str
    function: str
    color: str


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
    minutes = pd.to_numeric(posts["minutes_elapsed"], errors="coerce")
    return posts[(minutes >= 0) & (minutes <= 60)].copy()


def build_results(posts: pd.DataFrame) -> list[FormResult]:
    results: list[FormResult] = []
    for card in CARDS:
        sub = posts[
            (posts["internal_family_label"] == "single_model_final")
            & (posts["model_display"] == card["model_display"])
            & (posts["condition"] == card["condition"])
            & (posts["n_agents"] == card["n_agents"])
        ].copy()
        if sub.empty:
            raise ValueError(f"No posts found for {card}")
        target = tuple(card["anchor_tokens"])
        sub["full_text_for_match"] = sub.apply(row_text, axis=1)
        sub["occurrences"] = sub["full_text_for_match"].apply(lambda value: count_exact_phrase(value, target))
        matched = sub[sub["occurrences"] > 0].copy()
        if matched.empty:
            raise ValueError(f"Phrase not found for {card}")
        results.append(
            FormResult(
                social_form=str(card["social_form"]),
                display_phrase=str(card["display_phrase"]),
                anchor_tokens=target,
                model_display=str(card["model_display"]),
                condition=str(card["condition"]),
                condition_label=CONDITION_LABELS.get(str(card["condition"]), str(card["condition"])),
                n_agents_total=int(card["n_agents"]),
                n_phrase_posts=int(matched["record_id"].nunique()),
                n_phrase_agents=int(matched["author_name"].nunique()),
                n_occurrences=int(matched["occurrences"].sum()),
                run_id=str(matched["run_id"].iloc[0]),
                run_uid=str(matched["run_uid"].iloc[0]),
                snippet=str(card["snippet"]),
                function=str(card["function"]),
                color=str(card["color"]),
            )
        )
    return results


def wrapped(text: str, width: int) -> str:
    return "\n".join(wrap(text, width=width, break_long_words=False, replace_whitespace=False))


def draw_cards(results: list[FormResult], output_path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(14.4, 9.5), facecolor="#F7F3ED")
    fig.text(0.055, 0.950, "Social forms of local discourse attractors", ha="left", va="top", fontsize=23, fontweight="bold", color="#1F2A33")
    fig.text(
        0.055,
        0.905,
        "The same collapse process can appear as templates, mantras, rituals, citations, or role-play motifs.",
        ha="left",
        va="top",
        fontsize=11.7,
        color="#52616B",
    )
    fig.text(
        0.055,
        0.878,
        "Counts use exact NLTK 5-token anchors over agent-generated posts only.",
        ha="left",
        va="top",
        fontsize=10.4,
        color="#6E7A82",
    )

    positions = [
        (0.055, 0.535, 0.285, 0.305),
        (0.365, 0.535, 0.285, 0.305),
        (0.675, 0.535, 0.285, 0.305),
        (0.205, 0.160, 0.285, 0.305),
        (0.515, 0.160, 0.285, 0.305),
    ]

    for idx, (result, pos) in enumerate(zip(results, positions), start=1):
        ax = fig.add_axes(pos)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.add_patch(
            FancyBboxPatch(
                (0, 0),
                1,
                1,
                boxstyle="round,pad=0.014,rounding_size=0.030",
                facecolor="#FFFFFF",
                edgecolor="#DDD5CA",
                linewidth=1.0,
                clip_on=False,
            )
        )
        ax.add_patch(
            FancyBboxPatch(
                (0.030, 0.845),
                0.940,
                0.110,
                boxstyle="round,pad=0.008,rounding_size=0.018",
                facecolor=result.color,
                edgecolor="none",
                alpha=0.96,
            )
        )
        ax.text(0.060, 0.900, result.social_form, ha="left", va="center", fontsize=11.2, color="#FFFFFF", fontweight="bold")
        ax.text(0.060, 0.760, f"“{result.display_phrase}”", ha="left", va="top", fontsize=12.3, color="#1F2A33", fontweight="bold")
        ax.text(
            0.060,
            0.620,
            f"{result.model_display} · {result.condition_label}",
            ha="left",
            va="top",
            fontsize=8.7,
            color="#40525E",
            fontweight="bold",
        )
        ax.text(
            0.060,
            0.525,
            f"{result.n_phrase_posts} posts · {result.n_phrase_agents}/{result.n_agents_total} agents",
            ha="left",
            va="top",
            fontsize=8.7,
            color="#52616B",
        )
        ax.text(0.060, 0.430, "Example", ha="left", va="top", fontsize=8.6, color="#7A858C", fontweight="bold")
        ax.text(0.060, 0.360, wrapped(result.snippet, 40), ha="left", va="top", fontsize=8.6, color="#2F3D46")
        ax.text(0.060, 0.205, "Social role", ha="left", va="top", fontsize=8.6, color="#7A858C", fontweight="bold")
        ax.text(0.060, 0.135, wrapped(result.function, 43), ha="left", va="top", fontsize=8.7, color="#2F3D46")

    fig.text(
        0.055,
        0.060,
        "These are examples of social form, not mutually exclusive categories. A run can contain more than one attractor type.",
        ha="left",
        va="bottom",
        fontsize=9.0,
        color="#6D7980",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def draw_table(results: list[FormResult], output_path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(13.8, 6.9), facecolor="#F7F3ED")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    fig.text(0.055, 0.945, "Five social forms of local attractors", ha="left", va="top", fontsize=22, fontweight="bold", color="#1F2A33")
    fig.text(
        0.055,
        0.895,
        "Exact phrase reuse can play different roles in the social feed.",
        ha="left",
        va="top",
        fontsize=11.6,
        color="#52616B",
    )

    x0 = 0.055
    y_top = 0.795
    row_h = 0.128
    col_x = [x0, 0.255, 0.480, 0.640]
    headers = ["Social form", "Phrase anchor", "Evidence", "Role in discourse"]
    widths = [0.180, 0.200, 0.135, 0.295]

    ax.add_patch(FancyBboxPatch((0.045, y_top - 0.015), 0.910, 0.060, boxstyle="round,pad=0.006,rounding_size=0.012", facecolor="#1F2A33", edgecolor="none"))
    for x, header in zip(col_x, headers):
        ax.text(x, y_top + 0.015, header, ha="left", va="center", fontsize=9.6, color="#FFFFFF", fontweight="bold")

    for i, result in enumerate(results):
        y = y_top - (i + 1) * row_h
        fill = "#FFFFFF" if i % 2 == 0 else "#FBFAF7"
        ax.add_patch(FancyBboxPatch((0.045, y - 0.012), 0.910, row_h - 0.012, boxstyle="round,pad=0.006,rounding_size=0.012", facecolor=fill, edgecolor="#DDD5CA", linewidth=0.8))
        ax.add_patch(FancyBboxPatch((0.060, y + 0.032), 0.012, 0.042, boxstyle="round,pad=0.004,rounding_size=0.006", facecolor=result.color, edgecolor="none"))
        ax.text(0.080, y + 0.058, result.social_form, ha="left", va="center", fontsize=10.2, color="#1F2A33", fontweight="bold")
        ax.text(0.255, y + 0.058, wrapped(f"“{result.display_phrase}”", 26), ha="left", va="center", fontsize=10.0, color="#1F2A33", fontweight="bold")
        ax.text(0.480, y + 0.058, f"{result.n_phrase_posts} posts\n{result.n_phrase_agents}/{result.n_agents_total} agents", ha="left", va="center", fontsize=9.0, color="#40525E")
        ax.text(0.640, y + 0.058, wrapped(result.function, 48), ha="left", va="center", fontsize=9.2, color="#2F3D46")

    fig.text(
        0.055,
        0.060,
        "Counts are exact NLTK 5-token anchors. Agent-generated posts only. Seed posts are not loaded or used.",
        ha="left",
        va="bottom",
        fontsize=8.8,
        color="#6D7980",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(results: list[FormResult]) -> None:
    rows = []
    for result in results:
        rows.append(
            {
                "social_form": result.social_form,
                "display_phrase": result.display_phrase,
                "anchor_tokens_json": json.dumps(list(result.anchor_tokens), ensure_ascii=False),
                "model_display": result.model_display,
                "condition": result.condition,
                "condition_label": result.condition_label,
                "run_id": result.run_id,
                "run_uid": result.run_uid,
                "n_phrase_posts": result.n_phrase_posts,
                "n_phrase_agents": result.n_phrase_agents,
                "n_agents_total": result.n_agents_total,
                "n_occurrences": result.n_occurrences,
                "snippet": result.snippet,
                "function": result.function,
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "social_forms_examples.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps({"examples": rows}, indent=2, ensure_ascii=False))
    table_rows = [
        f"| {r.social_form} | {r.display_phrase} | {r.model_display} | {r.condition_label} | {r.n_phrase_posts} | {r.n_phrase_agents}/{r.n_agents_total} | {r.function} |"
        for r in results
    ]
    readme = """# Step 6: social forms of local discourse attractors

Finding 7 asks what kind of social pattern a local attractor takes.

## Scope

- Agent-generated posts only
- First 60 minutes only
- Exact NLTK 5-token anchors
- Punctuation and casing retained
- Seed posts are not loaded or used

## Outputs

- `social_forms_local_attractors_table.png/pdf`
- `social_forms_examples.csv`
- `summary.json`

## Examples

| Social form | Phrase | Model | Condition | Posts | Agents | Role |
|---|---|---|---|---:|---:|---|
""" + "\n".join(table_rows) + "\n"
    (OUT_DIR / "README.md").write_text(readme)


def main() -> None:
    ensure_nltk_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    posts = load_posts()
    results = build_results(posts)
    draw_table(results, OUT_DIR / "social_forms_local_attractors_table.png")
    write_outputs(results)
    print(f"Wrote Step 6 outputs to {OUT_DIR}")
    for result in results:
        print(f"{result.social_form}: {result.display_phrase} - {result.n_phrase_posts} posts, {result.n_phrase_agents}/{result.n_agents_total} agents")


if __name__ == "__main__":
    main()
