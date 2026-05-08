#!/usr/bin/env python3
"""Step 10: selected single-run intervention comparison.

No cohort medians. This plot uses one pre-selected run per cohort for the
clean one-hour mag25 comparison.
"""
from __future__ import annotations

import gzip
import json
import math
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import AYUSH_ROOT, PLOT_ROOT, setup_style  # noqa: E402

POST_INDEX = AYUSH_ROOT / "post_index.csv"
LLM_TIMEBINS = AYUSH_ROOT / "llm_judge_run_timebin_metrics.csv"
OUT_DIR = PLOT_ROOT / "step10_intervention_selected_single_runs"

CONDITION = "mag25"
CONDITION_LABEL = "25 conspiracy seeds"
PROGRESS = [("25%", 0.25), ("50%", 0.50), ("75%", 0.75), ("100%", 1.000001)]
BIN_LABELS = ["Q1", "Q2", "Q3", "Q4"]
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)

SELECTED_RUNS = [
    {
        "key": "canonical_gpt5",
        "label": "Canonical GPT-5",
        "short_label": "Canonical GPT-5",
        "run_uid": "6d3e2805af6653babf2fedb85ca20790cd830d58",
        "color": "#56616B",
    },
    {
        "key": "qwen_base_tool",
        "label": "Qwen base tool",
        "short_label": "Qwen base tool",
        "run_uid": "5da5a08d776acf648cf486d44e05466a27a378de",
        "color": "#0E7C7B",
    },
    {
        "key": "mixed_roster",
        "label": "Mixed-model roster",
        "short_label": "Mixed roster",
        "run_uid": "d055f0cea2ba847f5466e52b06efe723b94eaf85",
        "color": "#B24E3A",
    },
    {
        "key": "obsession_gpt5_1h",
        "label": "Obsession GPT-5, 1h",
        "short_label": "Obsession GPT-5",
        "run_uid": "0e1a75b82e3e1c9395f6955b14174d7d7baa76f3",
        "color": "#D08A2E",
    },
]

METRICS = [
    {"key": "distinct5", "title": "Cumulative Distinct-5", "ylabel": "Distinct-5", "direction": "lower = fewer unique 5-grams"},
    {"key": "gzip", "title": "Cumulative gzip", "ylabel": "gzip ratio", "direction": "lower = easier to compress"},
    {"key": "llm_collapse", "title": "Cumulative LLM collapse index", "ylabel": "collapse index", "direction": "higher = more judged collapse"},
]


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def distinct5(texts: list[str]) -> float:
    total = 0
    unique = set()
    for text in texts:
        tokens = tokenize(text)
        if len(tokens) < 5:
            continue
        grams = [tuple(tokens[i : i + 5]) for i in range(len(tokens) - 4)]
        total += len(grams)
        unique.update(grams)
    return float(len(unique) / total) if total else math.nan


def compression_ratio(texts: list[str]) -> float:
    raw = "\n".join(t for t in texts if t).encode("utf-8")
    if not raw:
        return math.nan
    return float(len(gzip.compress(raw)) / len(raw))


def selected_lookup() -> dict[str, dict[str, str]]:
    return {row["run_uid"]: row for row in SELECTED_RUNS}


def load_posts() -> pd.DataFrame:
    df = pd.read_csv(POST_INDEX, low_memory=False)
    selected = selected_lookup()
    sub = df[
        (~df["is_seed"].astype(bool))
        & (df["run_uid"].isin(selected))
        & (df["condition"] == CONDITION)
        & (df["n_agents"] == 10)
        & (pd.to_numeric(df["normalized_time"], errors="coerce") >= 0)
        & (pd.to_numeric(df["normalized_time"], errors="coerce") <= 1.000001)
    ].copy()
    sub["text"] = sub["text"].fillna("").astype(str)
    sub["progress_time"] = pd.to_numeric(sub["normalized_time"], errors="coerce")
    sub["selected_key"] = sub["run_uid"].map(lambda uid: selected[uid]["key"])
    sub["selected_label"] = sub["run_uid"].map(lambda uid: selected[uid]["label"])
    return sub.sort_values(["selected_key", "progress_time", "post_id"])


def cumulative_text_metrics(posts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for run_uid, sub in posts.groupby("run_uid", dropna=False):
        first = sub.iloc[0]
        for idx, (progress_label, cutoff) in enumerate(PROGRESS):
            members = sub[sub["progress_time"] <= cutoff]
            texts = members["text"].dropna().astype(str).tolist()
            rows.append({
                "run_uid": run_uid,
                "run_id": first["run_id"],
                "source_path": first["source_path"],
                "selected_key": first["selected_key"],
                "selected_label": first["selected_label"],
                "internal_family_label": first["internal_family_label"],
                "model_display": first["model_display"],
                "condition": first["condition"],
                "bin_idx": idx,
                "progress_label": progress_label,
                "n_posts_cumulative": int(len(members)),
                "n_posts_total": int(len(sub)),
                "distinct5": distinct5(texts),
                "gzip": compression_ratio(texts),
            })
    return pd.DataFrame(rows)


def cumulative_llm() -> pd.DataFrame:
    df = pd.read_csv(LLM_TIMEBINS, low_memory=False)
    selected = selected_lookup()
    sub = df[
        (df["scheme"] == "normalized_quartile")
        & (df["run_uid"].isin(selected))
        & (df["condition"] == CONDITION)
        & (df["n_agents"] == 10)
    ].copy()
    sub["bin_label"] = pd.Categorical(sub["bin_label"], categories=BIN_LABELS, ordered=True)
    rows = []
    for run_uid, run in sub.groupby("run_uid", dropna=False):
        run = run.sort_values("bin_label")
        weighted_sum = 0.0
        weight = 0.0
        for idx, (_, row) in enumerate(run.iterrows()):
            n = float(row.get("n_judged", 0) or 0)
            val = float(row.get("collapse_index", math.nan))
            if np.isfinite(val) and n > 0:
                weighted_sum += val * n
                weight += n
            rows.append({
                "run_uid": run_uid,
                "bin_idx": idx,
                "llm_collapse": weighted_sum / weight if weight else math.nan,
                "n_judged_cumulative": int(weight),
            })
    return pd.DataFrame(rows)


def build_table() -> pd.DataFrame:
    text = cumulative_text_metrics(load_posts())
    llm = cumulative_llm()
    df = text.merge(llm, on=["run_uid", "bin_idx"], how="left")
    order = {row["key"]: idx for idx, row in enumerate(SELECTED_RUNS)}
    df["selected_order"] = df["selected_key"].map(order)
    return df.sort_values(["selected_order", "bin_idx"])


def draw_plot(df: pd.DataFrame, output_path: Path) -> None:
    setup_style()
    fig, axes = plt.subplots(1, 3, figsize=(15.8, 6.9), facecolor="#F7F3ED")
    fig.subplots_adjust(left=0.060, right=0.985, top=0.760, bottom=0.310, wspace=0.260)
    fig.text(0.060, 0.945, "Selected one-hour intervention runs", ha="left", va="top", fontsize=22, fontweight="bold", color="#1F2A33")
    fig.text(0.060, 0.892, f"Condition fixed to {CONDITION_LABEL}. Each line is one selected run, not a cohort median.", ha="left", va="top", fontsize=11.2, color="#52616B")
    fig.text(0.060, 0.862, "Same three core metrics: cumulative Distinct-5, cumulative gzip, and cumulative blinded LLM collapse index.", ha="left", va="top", fontsize=9.8, color="#6D7980")

    x = np.arange(len(PROGRESS))
    for ax, metric in zip(axes, METRICS):
        for selected in SELECTED_RUNS:
            line = df[df["selected_key"] == selected["key"]].sort_values("bin_idx")
            if line.empty:
                continue
            y = line[f"{metric['key']}"].to_numpy(dtype=float)
            total_posts = int(line["n_posts_total"].max())
            ax.plot(
                x,
                y,
                marker="o",
                linewidth=2.4,
                markersize=5.8,
                color=selected["color"],
                label=f"{selected['short_label']} ({total_posts} posts)",
            )
        ax.set_title(metric["title"], fontsize=12.5, fontweight="bold", color="#1F2A33", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels([p[0] for p in PROGRESS])
        ax.set_xlabel("Cumulative run progress")
        ax.set_ylabel(metric["ylabel"])
        ax.grid(axis="y", color="#DDD8D0", linewidth=0.8, alpha=0.70)
        ax.text(0.02, 0.04, metric["direction"], transform=ax.transAxes, ha="left", va="bottom", fontsize=8.3, color="#6D7980")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8.7, bbox_to_anchor=(0.5, 0.150))
    fig.text(0.060, 0.058, "Post counts are non-seed agent posts. Qwen base tool uses Gemini Flash Lite for orchestration and Qwen as the content-generation tool.", ha="left", va="bottom", fontsize=8.8, color="#6D7980")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(df: pd.DataFrame) -> None:
    df.to_csv(OUT_DIR / "intervention_selected_single_runs_mag25_by_run.csv", index=False)
    final = df[df["bin_idx"] == len(PROGRESS) - 1].copy().sort_values("selected_order")
    final.to_csv(OUT_DIR / "intervention_selected_single_runs_mag25_final_values.csv", index=False)

    rows = []
    for row in final.itertuples(index=False):
        rows.append(
            f"| {row.selected_label} | `{row.run_id}` | {int(row.n_posts_total)} | {row.distinct5:.3f} | {row.gzip:.3f} | {row.llm_collapse:.2f} |"
        )

    summary = {
        "condition": CONDITION,
        "condition_label": CONDITION_LABEL,
        "method": "one selected run per cohort; no medians",
        "selected_runs": SELECTED_RUNS,
        "final_values": final.to_dict(orient="records"),
    }
    (OUT_DIR / "summary_mag25.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    readme = """# Step 10: selected single-run intervention comparison

This is the no-median version of the intervention plot.

## Scope

- Condition: `mag25`, 25 conspiracy seeds
- One selected run per cohort
- 10-agent runs only
- Agent-generated posts only
- Seed rows excluded
- Cumulative normalized run progress: 25%, 50%, 75%, 100%

## Selected runs

| Line | Run ID | Non-seed posts | Final Distinct-5 | Final gzip | Final LLM collapse |
|---|---|---:|---:|---:|---:|
""" + "\n".join(rows) + "\n\n## Outputs\n\n- `intervention_selected_single_runs_mag25.png/pdf`\n- `intervention_selected_single_runs_mag25_by_run.csv`\n- `intervention_selected_single_runs_mag25_final_values.csv`\n- `summary_mag25.json`\n"
    (OUT_DIR / "README.md").write_text(readme)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = build_table()
    expected = {row["key"] for row in SELECTED_RUNS}
    found = set(df["selected_key"].dropna().unique())
    missing = expected - found
    if missing:
        raise RuntimeError(f"Missing selected runs: {sorted(missing)}")
    draw_plot(df, OUT_DIR / "intervention_selected_single_runs_mag25.png")
    write_outputs(df)
    print(f"Wrote selected single-run intervention outputs to {OUT_DIR}")
    print(df[df["bin_idx"] == len(PROGRESS) - 1][["selected_label", "run_id", "n_posts_total", "distinct5", "gzip", "llm_collapse"]].to_string(index=False))


if __name__ == "__main__":
    main()
