#!/usr/bin/env python3
"""Step 9: intervention comparison using the three core cumulative metrics.

One condition at a time, no condition pooling. X-axis is cumulative normalized
run progress so obsession-prompting runs can be compared to fixed-duration
cohorts.
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
OUT_DIR = PLOT_ROOT / "step09_intervention_cumulative_metrics"

CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag25": "25 conspiracy seeds",
    "dom-agi": "25 AGI seeds",
}
CONDITIONS = ["mag0", "mag25", "dom-agi"]
PROGRESS = [("25%", 0.25), ("50%", 0.50), ("75%", 0.75), ("100%", 1.000001)]
BIN_LABELS = ["Q1", "Q2", "Q3", "Q4"]
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)

COHORTS = [
    {"family": "single_model_final", "label": "Canonical baseline", "color": "#56616B"},
    {"family": "base_model_as_tool", "label": "Base model as tool", "color": "#0E7C7B"},
    {"family": "mixed_model_roster", "label": "Mixed-model roster", "color": "#B24E3A"},
    {"family": "obsession_prompting", "label": "Obsession prompt", "color": "#D08A2E"},
]

METRICS = [
    {"key": "distinct5", "title": "Cumulative Distinct-5", "ylabel": "Distinct-5", "direction": "lower = fewer unique 5-grams"},
    {"key": "gzip", "title": "Cumulative gzip", "ylabel": "gzip ratio", "direction": "lower = easier to compress"},
    {"key": "llm_collapse", "title": "Cumulative LLM collapse index", "ylabel": "collapse index", "direction": "higher = more judged collapse"},
]


def condition_label(condition: str) -> str:
    return CONDITION_LABELS.get(condition, condition)


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


def load_posts(condition: str) -> pd.DataFrame:
    df = pd.read_csv(POST_INDEX, low_memory=False)
    allowed = {cohort["family"] for cohort in COHORTS}
    sub = df[
        (~df["is_seed"].astype(bool))
        & (df["internal_family_label"].isin(allowed))
        & (df["condition"] == condition)
        & (df["n_agents"] == 10)
        & (pd.to_numeric(df["normalized_time"], errors="coerce") >= 0)
        & (pd.to_numeric(df["normalized_time"], errors="coerce") <= 1.000001)
    ].copy()
    sub["text"] = sub["text"].fillna("").astype(str)
    return sub.sort_values(["internal_family_label", "run_uid", "normalized_time", "post_id"])


def cumulative_text_metrics(posts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for run_uid, sub in posts.groupby("run_uid", dropna=False):
        first = sub.iloc[0]
        for idx, (progress_label, cutoff) in enumerate(PROGRESS):
            members = sub[pd.to_numeric(sub["normalized_time"], errors="coerce") <= cutoff]
            texts = members["text"].dropna().astype(str).tolist()
            rows.append({
                "run_uid": run_uid,
                "run_id": first["run_id"],
                "internal_family_label": first["internal_family_label"],
                "model_display": first["model_display"],
                "condition": first["condition"],
                "bin_idx": idx,
                "progress_label": progress_label,
                "n_posts_cumulative": int(len(members)),
                "distinct5": distinct5(texts),
                "gzip": compression_ratio(texts),
            })
    return pd.DataFrame(rows)


def cumulative_llm(condition: str) -> pd.DataFrame:
    df = pd.read_csv(LLM_TIMEBINS, low_memory=False)
    allowed = {cohort["family"] for cohort in COHORTS}
    sub = df[
        (df["scheme"] == "normalized_quartile")
        & (df["internal_family_label"].isin(allowed))
        & (df["condition"] == condition)
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
            rows.append({"run_uid": run_uid, "bin_idx": idx, "llm_collapse": weighted_sum / weight if weight else math.nan, "n_judged_cumulative": int(weight)})
    return pd.DataFrame(rows)


def build_table(condition: str) -> pd.DataFrame:
    text = cumulative_text_metrics(load_posts(condition))
    llm = cumulative_llm(condition)
    return text.merge(llm, on=["run_uid", "bin_idx"], how="left")


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cohort in COHORTS:
        family = cohort["family"]
        sub = df[df["internal_family_label"] == family]
        for idx, progress_label in enumerate([p[0] for p in PROGRESS]):
            point = sub[sub["bin_idx"] == idx]
            row = {
                "internal_family_label": family,
                "cohort_label": cohort["label"],
                "bin_idx": idx,
                "progress_label": progress_label,
                "n_runs": int(point["run_uid"].nunique()),
            }
            for metric in ["distinct5", "gzip", "llm_collapse"]:
                vals = pd.to_numeric(point[metric], errors="coerce").dropna().to_numpy(dtype=float)
                row[f"{metric}_median"] = float(np.median(vals)) if len(vals) else math.nan
                row[f"{metric}_mean"] = float(np.mean(vals)) if len(vals) else math.nan
            rows.append(row)
    return pd.DataFrame(rows)


def draw_plot(summary: pd.DataFrame, condition: str, output_path: Path) -> None:
    setup_style()
    fig, axes = plt.subplots(1, 3, figsize=(15.6, 6.9), facecolor="#F7F3ED")
    fig.subplots_adjust(left=0.060, right=0.985, top=0.765, bottom=0.285, wspace=0.250)
    fig.text(0.060, 0.945, "Intervention probes under one condition", ha="left", va="top", fontsize=22, fontweight="bold", color="#1F2A33")
    fig.text(0.060, 0.892, f"Condition fixed to {condition_label(condition)}. Lines show cohort medians over cumulative run progress.", ha="left", va="top", fontsize=11.2, color="#52616B")
    fig.text(0.060, 0.862, "Same three core metrics as the main paper figures: Distinct-5, gzip, and blinded LLM collapse index.", ha="left", va="top", fontsize=9.8, color="#6D7980")

    x = np.arange(len(PROGRESS))
    for ax, metric in zip(axes, METRICS):
        for cohort in COHORTS:
            line = summary[summary["internal_family_label"] == cohort["family"]].sort_values("bin_idx")
            y = line[f"{metric['key']}_median"].to_numpy(dtype=float)
            n_runs = int(line["n_runs"].max()) if not line.empty else 0
            ax.plot(x, y, marker="o", linewidth=2.4, markersize=5.8, color=cohort["color"], label=f"{cohort['label']} (n={n_runs})")
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
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=9.0, bbox_to_anchor=(0.5, 0.145))
    fig.text(0.060, 0.055, "Run is the unit before summarizing. Mixed-model roster has one run for each condition, so its line is a single-run trajectory.", ha="left", va="bottom", fontsize=8.8, color="#6D7980")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(condition: str, df: pd.DataFrame, summary: pd.DataFrame) -> None:
    df.to_csv(OUT_DIR / f"intervention_cumulative_metrics_{condition}_by_run.csv", index=False)
    summary.to_csv(OUT_DIR / f"intervention_cumulative_metrics_{condition}_summary.csv", index=False)
    (OUT_DIR / f"summary_{condition}.json").write_text(json.dumps({"condition": condition, "condition_label": condition_label(condition), "summary": summary.to_dict(orient="records")}, indent=2, ensure_ascii=False))
    final = summary[summary["bin_idx"] == len(PROGRESS) - 1].copy()
    rows = []
    for row in final.itertuples(index=False):
        rows.append(f"| {row.cohort_label} | {int(row.n_runs)} | {row.distinct5_median:.3f} | {row.gzip_median:.3f} | {row.llm_collapse_median:.2f} |")
    readme = f"""# Step 9: intervention cumulative metrics, {condition_label(condition)}

Condition fixed to **{condition_label(condition)}**. This avoids condition pooling and uses the same core metrics as the main paper figures.

## Scope

- 10-agent runs only
- Agent-generated posts only
- Seed rows excluded
- Cumulative normalized run progress: 25%, 50%, 75%, 100%
- Lines show cohort medians before plotting

## Outputs for this condition

- `intervention_cumulative_metrics_{condition}.png/pdf`
- `intervention_cumulative_metrics_{condition}_by_run.csv`
- `intervention_cumulative_metrics_{condition}_summary.csv`
- `summary_{condition}.json`

## Final cumulative values at 100% progress

| Cohort | Runs | Distinct-5 median | gzip median | LLM collapse median |
|---|---:|---:|---:|---:|
""" + "\n".join(rows) + "\n"
    (OUT_DIR / f"README_{condition}.md").write_text(readme)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    combined = {}
    for condition in CONDITIONS:
        df = build_table(condition)
        summary = summarize(df)
        draw_plot(summary, condition, OUT_DIR / f"intervention_cumulative_metrics_{condition}.png")
        write_outputs(condition, df, summary)
        combined[condition] = summary.to_dict(orient="records")
        print(f"\n## {condition}: {condition_label(condition)}")
        print(summary.to_string(index=False))
    (OUT_DIR / "summary_all_conditions.json").write_text(json.dumps(combined, indent=2, ensure_ascii=False))
    (OUT_DIR / "README.md").write_text(
        "# Step 9: intervention cumulative metrics\n\n"
        "Generated one-condition-at-a-time figures for: mag0, mag25, and dom-agi.\n\n"
        "Files:\n"
        "- `intervention_cumulative_metrics_mag0.png/pdf`\n"
        "- `intervention_cumulative_metrics_mag25.png/pdf`\n"
        "- `intervention_cumulative_metrics_dom-agi.png/pdf`\n"
    )
    print(f"\nWrote Step 9 outputs to {OUT_DIR}")


if __name__ == "__main__":
    main()
