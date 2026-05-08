#!/usr/bin/env python3
"""Step 8: concrete intervention-probe phrase examples.

This replaces abstract intervention metric plots. It shows direct phrase echoes
that appear inside intervention-style cohorts, with exact NLTK 5-token counts
and snippets.
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
        "NLTK is required for Step 8. Run with /tmp/moltbook-nltk-venv/bin/python or install NLTK."
    ) from exc

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import AYUSH_ROOT, CONDITION_LABELS, PLOT_ROOT, setup_style  # noqa: E402

POST_INDEX = AYUSH_ROOT / "post_index.csv"
OUT_DIR = PLOT_ROOT / "step08_intervention_probe_llm"
NGRAM_N = 5
SENTENCE_TOKENIZER = PunktTokenizer("english")

EXAMPLES = [
    {
        "cohort": "Base model as tool",
        "internal_family_label": "base_model_as_tool",
        "model_display": "OLMo 3 32B Base",
        "condition": "mag1",
        "n_agents": 10,
        "display_phrase": "As we stand on the",
        "anchor_tokens": ("As", "we", "stand", "on", "the"),
        "snippet": "As we stand on the brink of a new age in computing, it is crucial that we do not let...",
        "reading": "The base-model probe still develops a shared grand-opening frame.",
        "color": "#0E7C7B",
    },
    {
        "cohort": "Mixed-model roster",
        "internal_family_label": "mixed_model_roster",
        "model_display": "Mixed roster (Qwen 3.5 27B)",
        "condition": "dom-agi",
        "n_agents": 10,
        "display_phrase": "that no one else has",
        "anchor_tokens": ("that", "no", "one", "else", "has"),
        "snippet": "So: what do you actually believe that no one else has said yet?",
        "reading": "Different models still coordinate around a shared prompt-like question.",
        "color": "#B24E3A",
    },
    {
        "cohort": "Obsession prompt",
        "internal_family_label": "obsession_prompting",
        "model_display": "GPT-5",
        "condition": "mag1",
        "n_agents": 10,
        "display_phrase": "Question: What’s your...",
        "anchor_tokens": (":", "What", "’", "s", "your"),
        "snippet": "Question: What’s your smallest change that surfaced a hidden failure without boiling the ocean?",
        "reading": "The prompt intervention still produces a repeated question frame.",
        "color": "#D08A2E",
    },
]


@dataclass
class ExampleResult:
    cohort: str
    internal_family_label: str
    model_display: str
    condition: str
    condition_label: str
    n_agents_total: int
    run_id: str
    run_uid: str
    display_phrase: str
    anchor_tokens: tuple[str, ...]
    n_phrase_posts: int
    n_phrase_agents: int
    n_occurrences: int
    snippet: str
    reading: str
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


def build_results(posts: pd.DataFrame) -> list[ExampleResult]:
    results: list[ExampleResult] = []
    for spec in EXAMPLES:
        sub = posts[
            (posts["internal_family_label"] == spec["internal_family_label"])
            & (posts["model_display"] == spec["model_display"])
            & (posts["condition"] == spec["condition"])
            & (posts["n_agents"] == spec["n_agents"])
        ].copy()
        if sub.empty:
            raise ValueError(f"No posts found for {spec}")
        target = tuple(spec["anchor_tokens"])
        sub["full_text_for_match"] = sub.apply(row_text, axis=1)
        sub["occurrences"] = sub["full_text_for_match"].apply(lambda value: count_exact_phrase(value, target))
        matched = sub[sub["occurrences"] > 0].copy()
        if matched.empty:
            raise ValueError(f"Phrase not found for {spec}")
        results.append(
            ExampleResult(
                cohort=str(spec["cohort"]),
                internal_family_label=str(spec["internal_family_label"]),
                model_display=str(spec["model_display"]),
                condition=str(spec["condition"]),
                condition_label=CONDITION_LABELS.get(str(spec["condition"]), str(spec["condition"])),
                n_agents_total=int(spec["n_agents"]),
                run_id=str(matched["run_id"].iloc[0]),
                run_uid=str(matched["run_uid"].iloc[0]),
                display_phrase=str(spec["display_phrase"]),
                anchor_tokens=target,
                n_phrase_posts=int(matched["record_id"].nunique()),
                n_phrase_agents=int(matched["author_name"].nunique()),
                n_occurrences=int(matched["occurrences"].sum()),
                snippet=str(spec["snippet"]),
                reading=str(spec["reading"]),
                color=str(spec["color"]),
            )
        )
    return results


def wrapped(text: str, width: int) -> str:
    return "\n".join(wrap(text, width=width, break_long_words=False, replace_whitespace=False))


def draw_table(results: list[ExampleResult], output_path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(14.2, 7.2), facecolor="#F7F3ED")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.055, 0.940, "Intervention probes still produce phrase attractors", ha="left", va="top", fontsize=22, fontweight="bold", color="#1F2A33")
    fig.text(
        0.055,
        0.892,
        "Concrete examples from secondary cohorts. Counts are exact NLTK 5-token anchors in the first 60 minutes.",
        ha="left",
        va="top",
        fontsize=11.2,
        color="#52616B",
    )
    fig.text(
        0.055,
        0.862,
        "This does not prove causal failure. It shows that these probes can still form local repeated phrases.",
        ha="left",
        va="top",
        fontsize=9.7,
        color="#6D7980",
    )

    y_top = 0.755
    row_h = 0.170
    col_x = [0.060, 0.255, 0.445, 0.600, 0.790]
    headers = ["Probe", "Repeated phrase", "Adoption", "Example snippet", "Concrete reading"]

    ax.add_patch(FancyBboxPatch((0.045, y_top - 0.015), 0.910, 0.066, boxstyle="round,pad=0.006,rounding_size=0.014", facecolor="#1F2A33", edgecolor="none"))
    for x, header in zip(col_x, headers):
        ax.text(x, y_top + 0.017, header, ha="left", va="center", fontsize=9.4, color="#FFFFFF", fontweight="bold")

    for i, result in enumerate(results):
        y = y_top - (i + 1) * row_h
        fill = "#FFFFFF" if i % 2 == 0 else "#FBFAF7"
        ax.add_patch(FancyBboxPatch((0.045, y - 0.010), 0.910, row_h - 0.012, boxstyle="round,pad=0.006,rounding_size=0.014", facecolor=fill, edgecolor="#DDD5CA", linewidth=0.8))
        ax.add_patch(FancyBboxPatch((0.060, y + 0.078), 0.012, 0.045, boxstyle="round,pad=0.004,rounding_size=0.006", facecolor=result.color, edgecolor="none"))
        ax.text(0.080, y + 0.103, wrapped(result.cohort, 22), ha="left", va="center", fontsize=9.6, color="#1F2A33", fontweight="bold")
        ax.text(0.080, y + 0.042, f"{result.model_display}\n{result.condition_label}", ha="left", va="center", fontsize=7.7, color="#52616B")

        ax.text(0.255, y + 0.103, wrapped(f"“{result.display_phrase}”", 24), ha="left", va="center", fontsize=9.7, color="#1F2A33", fontweight="bold")
        ax.text(0.255, y + 0.037, "exact 5-token anchor", ha="left", va="center", fontsize=7.7, color="#6D7980")

        ax.text(0.445, y + 0.103, f"{result.n_phrase_posts} posts", ha="left", va="center", fontsize=10.1, color="#1F2A33", fontweight="bold")
        ax.text(0.445, y + 0.058, f"{result.n_phrase_agents}/{result.n_agents_total} agents", ha="left", va="center", fontsize=8.6, color="#40525E")

        ax.text(0.600, y + 0.082, wrapped(result.snippet, 30), ha="left", va="center", fontsize=8.0, color="#2F3D46")
        ax.text(0.790, y + 0.082, wrapped(result.reading, 31), ha="left", va="center", fontsize=8.3, color="#2F3D46")

    fig.text(
        0.055,
        0.092,
        "Agent-generated posts only. Seed rows are excluded before matching. Punctuation and casing are retained.",
        ha="left",
        va="bottom",
        fontsize=8.8,
        color="#6D7980",
    )
    fig.text(
        0.055,
        0.064,
        "The obsession row displays a question frame; its exact 5-token anchor is ': What ’ s your'.",
        ha="left",
        va="bottom",
        fontsize=8.8,
        color="#6D7980",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(results: list[ExampleResult]) -> None:
    rows = []
    for result in results:
        rows.append(
            {
                "cohort": result.cohort,
                "internal_family_label": result.internal_family_label,
                "model_display": result.model_display,
                "condition": result.condition,
                "condition_label": result.condition_label,
                "run_id": result.run_id,
                "run_uid": result.run_uid,
                "display_phrase": result.display_phrase,
                "anchor_tokens_json": json.dumps(list(result.anchor_tokens), ensure_ascii=False),
                "n_phrase_posts": result.n_phrase_posts,
                "n_phrase_agents": result.n_phrase_agents,
                "n_agents_total": result.n_agents_total,
                "n_occurrences": result.n_occurrences,
                "snippet": result.snippet,
                "reading": result.reading,
            }
        )
    pd.DataFrame(rows).to_csv(OUT_DIR / "intervention_probe_phrase_examples.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps({"examples": rows}, indent=2, ensure_ascii=False))
    table_rows = [
        f"| {r.cohort} | {r.display_phrase} | {r.n_phrase_posts} | {r.n_phrase_agents}/{r.n_agents_total} | {r.reading} |"
        for r in results
    ]
    readme = """# Step 8: concrete intervention-probe phrase examples

This replaces the abstract intervention metric plots.

## Scope

- Secondary cohort examples
- 10-agent runs only
- First 60 minutes only
- Exact NLTK 5-token anchors
- Agent-generated posts only
- Seed rows excluded before matching

## Outputs

- `intervention_probe_phrase_examples.png/pdf`
- `intervention_probe_phrase_examples.csv`
- `summary.json`

## Examples

| Cohort | Phrase | Posts | Agents | Reading |
|---|---|---:|---:|---|
""" + "\n".join(table_rows) + "\n\n## Caution\n\nThese are concrete examples, not matched causal estimates.\n"
    (OUT_DIR / "README.md").write_text(readme)


def main() -> None:
    ensure_nltk_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in [
        "intervention_probe_llm_collapse_dotplot.png",
        "intervention_probe_llm_collapse_dotplot.pdf",
        "intervention_probe_plain_summary_table.png",
        "intervention_probe_plain_summary_table.pdf",
        "intervention_probe_llm_run_deltas.csv",
        "intervention_probe_llm_summary.csv",
    ]:
        path = OUT_DIR / stale
        if path.exists():
            path.unlink()
    posts = load_posts()
    results = build_results(posts)
    draw_table(results, OUT_DIR / "intervention_probe_phrase_examples.png")
    write_outputs(results)
    print(f"Wrote Step 8 outputs to {OUT_DIR}")
    for result in results:
        print(f"{result.cohort}: {result.display_phrase} - {result.n_phrase_posts} posts, {result.n_phrase_agents}/{result.n_agents_total} agents")


if __name__ == "__main__":
    main()
