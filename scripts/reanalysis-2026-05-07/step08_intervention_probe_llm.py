#!/usr/bin/env python3
"""Step 8: intervention phrase-adoption scorecard.

This figure uses direct exact-phrase adoption rather than LLM deltas. For each
10-agent run, it finds the top exact NLTK 5-token anchor by number of adopting
agents, then counts how often that top anchor reaches at least half the agents.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import AYUSH_ROOT, PLOT_ROOT, setup_style  # noqa: E402
from step04_scale_phrase_adoption import ensure_nltk_ready, phrase_stats_for_run  # noqa: E402

POST_INDEX = AYUSH_ROOT / "post_index.csv"
OUT_DIR = PLOT_ROOT / "step08_intervention_probe_llm"
TIME_MIN = 0.0
TIME_MAX = 60.0
ADOPTION_THRESHOLD = 5

COHORTS = [
    {
        "family": "single_model_final",
        "label": "Canonical baseline",
        "scope": "reference",
        "color": "#56616B",
        "interpretation": "Widespread run-local phrase adoption is the baseline pattern.",
    },
    {
        "family": "base_model_as_tool",
        "label": "Base model as tool",
        "scope": "probe",
        "color": "#0E7C7B",
        "interpretation": "Still often produces a phrase adopted by at least half the agents.",
    },
    {
        "family": "mixed_model_roster",
        "label": "Mixed-model roster",
        "scope": "probe",
        "color": "#B24E3A",
        "interpretation": "Cross-agent adoption is weaker, but still appears in most runs.",
    },
    {
        "family": "obsession_prompting",
        "label": "Obsession prompt",
        "scope": "probe",
        "color": "#D08A2E",
        "interpretation": "Spread across agents is lower; repetition is more concentrated within fewer agents.",
    },
]


def load_posts() -> pd.DataFrame:
    df = pd.read_csv(POST_INDEX, low_memory=False)
    minutes = pd.to_numeric(df["minutes_elapsed"], errors="coerce")
    allowed = {cohort["family"] for cohort in COHORTS}
    sub = df[
        (~df["is_seed"].astype(bool))
        & (df["internal_family_label"].isin(allowed))
        & (df["n_agents"] == 10)
        & (minutes >= TIME_MIN)
        & (minutes <= TIME_MAX)
    ].copy()
    return sub.sort_values(["internal_family_label", "run_uid", "minutes_elapsed", "post_id"])


def top_phrase_rows(posts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (family, run_uid), sub in posts.groupby(["internal_family_label", "run_uid"], dropna=False):
        stats = phrase_stats_for_run(sub)
        if not stats:
            continue
        top = sorted(stats, key=lambda stat: stat.sort_key, reverse=True)[0]
        first = sub.iloc[0]
        rows.append(
            {
                "internal_family_label": family,
                "run_uid": run_uid,
                "run_id": first["run_id"],
                "model_display": first["model_display"],
                "condition": first["condition"],
                "n_agents": int(first["n_agents"]),
                "top_phrase_surface": top.phrase_surface,
                "top_phrase_tokens_json": json.dumps(list(top.tokens), ensure_ascii=False),
                "top_phrase_posts": int(top.n_posts),
                "top_phrase_agents": int(top.n_adopters),
                "top_phrase_mentions": int(top.n_mentions),
                "top_agent_share": float(top.top_agent_share),
                "reached_half_agents": bool(top.n_adopters >= ADOPTION_THRESHOLD),
            }
        )
    return pd.DataFrame(rows)


def summarize(run_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cohort in COHORTS:
        sub = run_df[run_df["internal_family_label"] == cohort["family"]].copy()
        if sub.empty:
            continue
        example = sub.sort_values(["top_phrase_agents", "top_phrase_posts", "top_phrase_mentions"], ascending=False).iloc[0]
        rows.append(
            {
                "internal_family_label": cohort["family"],
                "label": cohort["label"],
                "scope": cohort["scope"],
                "color": cohort["color"],
                "interpretation": cohort["interpretation"],
                "n_runs": int(len(sub)),
                "runs_reached_half_agents": int(sub["reached_half_agents"].sum()),
                "median_top_phrase_agents": float(np.median(sub["top_phrase_agents"])),
                "median_top_phrase_posts": float(np.median(sub["top_phrase_posts"])),
                "median_top_agent_share": float(np.median(sub["top_agent_share"])),
                "example_phrase": str(example["top_phrase_surface"]),
                "example_agents": int(example["top_phrase_agents"]),
                "example_posts": int(example["top_phrase_posts"]),
                "example_model": str(example["model_display"]),
                "example_condition": str(example["condition"]),
            }
        )
    return pd.DataFrame(rows)


def fmt_median(value: float) -> str:
    if math.isclose(value, round(value)):
        return str(int(round(value)))
    return f"{value:.1f}"


def wrapped(text: str, width: int) -> str:
    return "\n".join(wrap(text, width=width, break_long_words=False, replace_whitespace=False))


def draw_scorecard(summary: pd.DataFrame, output_path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(14.4, 7.6), facecolor="#F7F3ED")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    fig.text(0.055, 0.940, "Intervention probes change the repetition pattern", ha="left", va="top", fontsize=22, fontweight="bold", color="#1F2A33")
    fig.text(
        0.055,
        0.892,
        "For each 10-agent run, we find the top exact NLTK 5-token anchor and ask whether it reaches at least 5 agents.",
        ha="left",
        va="top",
        fontsize=11.0,
        color="#52616B",
    )
    fig.text(
        0.055,
        0.862,
        "This is direct phrase-adoption evidence, not an LLM score and not a causal estimate.",
        ha="left",
        va="top",
        fontsize=9.7,
        color="#6D7980",
    )

    y_top = 0.755
    row_h = 0.148
    col_x = [0.060, 0.255, 0.425, 0.585, 0.755]
    headers = ["Cohort", "Runs with ≥5-agent phrase", "Typical top phrase", "Strong example", "Reading"]

    ax.add_patch(FancyBboxPatch((0.045, y_top - 0.015), 0.910, 0.066, boxstyle="round,pad=0.006,rounding_size=0.014", facecolor="#1F2A33", edgecolor="none"))
    for x, header in zip(col_x, headers):
        ax.text(x, y_top + 0.017, header, ha="left", va="center", fontsize=9.1, color="#FFFFFF", fontweight="bold")

    for i, row in enumerate(summary.itertuples(index=False)):
        y = y_top - (i + 1) * row_h
        fill = "#FFFFFF" if i % 2 == 0 else "#FBFAF7"
        ax.add_patch(FancyBboxPatch((0.045, y - 0.010), 0.910, row_h - 0.012, boxstyle="round,pad=0.006,rounding_size=0.014", facecolor=fill, edgecolor="#DDD5CA", linewidth=0.8))
        ax.add_patch(FancyBboxPatch((0.060, y + 0.066), 0.012, 0.045, boxstyle="round,pad=0.004,rounding_size=0.006", facecolor=row.color, edgecolor="none"))
        ax.text(0.080, y + 0.090, wrapped(row.label, 22), ha="left", va="center", fontsize=9.5, color="#1F2A33", fontweight="bold")
        ax.text(0.080, y + 0.040, row.scope, ha="left", va="center", fontsize=7.8, color="#6D7980")

        ax.text(0.255, y + 0.092, f"{int(row.runs_reached_half_agents)}/{int(row.n_runs)} runs", ha="left", va="center", fontsize=10.2, color="#1F2A33", fontweight="bold")
        ax.text(0.255, y + 0.045, "top phrase reaches ≥5 agents", ha="left", va="center", fontsize=7.8, color="#6D7980")

        ax.text(0.425, y + 0.092, f"{fmt_median(row.median_top_phrase_agents)}/10 agents", ha="left", va="center", fontsize=9.5, color="#1F2A33", fontweight="bold")
        ax.text(0.425, y + 0.045, f"median {fmt_median(row.median_top_phrase_posts)} posts", ha="left", va="center", fontsize=8.0, color="#52616B")

        ax.text(0.585, y + 0.098, wrapped(f"“{row.example_phrase}”", 27), ha="left", va="center", fontsize=8.6, color="#1F2A33", fontweight="bold")
        ax.text(0.585, y + 0.040, f"{int(row.example_agents)}/10 agents, {int(row.example_posts)} posts", ha="left", va="center", fontsize=8.0, color="#52616B")

        ax.text(0.755, y + 0.075, wrapped(row.interpretation, 35), ha="left", va="center", fontsize=8.3, color="#2F3D46")

    fig.text(
        0.055,
        0.075,
        "Top phrase = exact 5-token anchor with the most adopting agents in that run, tie-broken by posts and mentions.",
        ha="left",
        va="bottom",
        fontsize=8.7,
        color="#6D7980",
    )
    fig.text(
        0.055,
        0.047,
        "Agent-generated posts only; first 60 minutes only; punctuation and casing retained; seed rows excluded before matching.",
        ha="left",
        va="bottom",
        fontsize=8.7,
        color="#6D7980",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(run_df: pd.DataFrame, summary: pd.DataFrame) -> None:
    run_df.to_csv(OUT_DIR / "intervention_phrase_adoption_by_run.csv", index=False)
    summary.drop(columns=["color"]).to_csv(OUT_DIR / "intervention_phrase_adoption_summary.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps({"summary": summary.drop(columns=["color"]).to_dict(orient="records")}, indent=2, ensure_ascii=False))
    table_rows = [
        f"| {row.label} | {int(row.n_runs)} | {int(row.runs_reached_half_agents)}/{int(row.n_runs)} | {fmt_median(row.median_top_phrase_agents)}/10 | {fmt_median(row.median_top_phrase_posts)} | {row.example_phrase} |"
        for row in summary.itertuples(index=False)
    ]
    readme = """# Step 8: intervention phrase-adoption scorecard

This replaces the abstract intervention metric plots. It asks a direct question: in each run, does the top exact phrase reach at least half the agents?

## Scope

- 10-agent runs only
- First 60 minutes only
- Exact NLTK 5-token anchors
- Agent-generated posts only
- Seed rows excluded before matching
- Punctuation and casing retained

## Outputs

- `intervention_phrase_adoption_scorecard.png/pdf`
- `intervention_phrase_adoption_by_run.csv`
- `intervention_phrase_adoption_summary.csv`
- `summary.json`

## Summary

| Cohort | Runs | Runs with top phrase reaching ≥5 agents | Median top-phrase adopters | Median top-phrase posts | Strong example |
|---|---:|---:|---:|---:|---|
""" + "\n".join(table_rows) + "\n"
    (OUT_DIR / "README.md").write_text(readme)


def main() -> None:
    ensure_nltk_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for stale in OUT_DIR.glob("intervention_probe_*"):
        stale.unlink()
    posts = load_posts()
    run_df = top_phrase_rows(posts)
    summary = summarize(run_df)
    draw_scorecard(summary, OUT_DIR / "intervention_phrase_adoption_scorecard.png")
    write_outputs(run_df, summary)
    print(f"Wrote Step 8 outputs to {OUT_DIR}")
    print(summary.drop(columns=["color"]).to_string(index=False))


if __name__ == "__main__":
    main()
