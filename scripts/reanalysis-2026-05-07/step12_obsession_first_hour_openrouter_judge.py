#!/usr/bin/env python3
"""Step 12: summarize a fresh OpenRouter judge pass for obsession first hour.

Input is a freshly generated blinded-judge CSV for the corrected GPT-5 obsession
set: physical runs grouped by run_uid/source_path and truncated to minutes 0--60.
The script compares those fresh obsession scores to the existing canonical GPT-5
n10 baseline scores and writes paper-facing summaries/figures.
"""
from __future__ import annotations

import math
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
FRESH_JUDGE = REPO / "analysis/obsession-first-hour-openrouter-judge/ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv"
BASELINE_JUDGE = REPO / "analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv"
POST_INDEX = REPO / "analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/post_index.csv"
OUT_DIR = REPO / "findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step12_obsession_first_hour_openrouter_judge"

BIN_LABELS = ["0-15m", "15-30m", "30-45m", "45-60m"]
COMPONENTS = ["novelty", "semantic_repetition", "frame_convergence", "consensus_conformity", "template_rigidity"]
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty",
    "mag1": "1 consp.",
    "mag5": "5 consp.",
    "mag25": "25 consp.",
    "dom-agi": "AGI",
    "dom-tech": "Tech",
}


def source_short(source_path: str) -> str:
    marker = "/2026-05-05/"
    if marker in str(source_path):
        return str(source_path).split(marker, 1)[1]
    marker = "/project-results/"
    if marker in str(source_path):
        return str(source_path).split(marker, 1)[1]
    return str(source_path)


def first_hour_bin(minutes: float) -> int | None:
    if not np.isfinite(minutes) or minutes < 0 or minutes > 60:
        return None
    if minutes < 15:
        return 0
    if minutes < 30:
        return 1
    if minutes < 45:
        return 2
    return 3


def read_judge(path: Path, family_filter: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path, low_memory=False)
    df["minutes_elapsed"] = pd.to_numeric(df["minutes_elapsed"], errors="coerce")
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce")
    df["collapse_index"] = pd.to_numeric(df["collapse_index"], errors="coerce")
    for col in COMPONENTS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    keep = (
        (df["is_seed"].astype(str) == "False")
        & (df["model_family"] == "gpt-5")
        & (df["n_agents"] == 10)
        & (df["internal_family_label"] == family_filter)
        & (df["minutes_elapsed"] >= 0)
        & (df["minutes_elapsed"] <= 60)
    )
    out = df[keep].copy()
    out["physical_run_key"] = out["run_uid"].astype(str) + "::" + out["source_path"].astype(str)
    out["source_short"] = out["source_path"].map(source_short)
    out["first_hour_bin"] = out["minutes_elapsed"].map(first_hour_bin)
    return out


def read_post_counts() -> pd.DataFrame:
    df = pd.read_csv(POST_INDEX, low_memory=False)
    df["minutes_elapsed"] = pd.to_numeric(df["minutes_elapsed"], errors="coerce")
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce")
    keep = (
        (df["is_seed"].astype(str) == "False")
        & (df["model_family"] == "gpt-5")
        & (df["n_agents"] == 10)
        & (df["internal_family_label"] == "obsession_prompting")
        & (df["minutes_elapsed"] >= 0)
        & (df["minutes_elapsed"] <= 60)
    )
    sub = df[keep].copy()
    sub["physical_run_key"] = sub["run_uid"].astype(str) + "::" + sub["source_path"].astype(str)
    return sub.groupby("physical_run_key").size().rename("n_posts_first_hour").reset_index()


def build_bins(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    meta_cols = ["physical_run_key", "run_uid", "run_id", "source_path", "source_short", "internal_family_label", "condition"]
    for key, run in df.groupby(meta_cols, dropna=False):
        meta = dict(zip(meta_cols, key))
        for idx, label in enumerate(BIN_LABELS):
            b = run[run["first_hour_bin"] == idx]
            row = dict(meta)
            row.update({"bin_idx": idx, "bin_label": label, "n_judged": int(len(b))})
            for col in ["collapse_index"] + COMPONENTS:
                row[col] = float(b[col].mean()) if len(b) else math.nan
            rows.append(row)
    return pd.DataFrame(rows)


def build_run_summary(bins: pd.DataFrame, post_counts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, run in bins.groupby("physical_run_key", dropna=False):
        run = run.sort_values("bin_idx")
        first = run.iloc[0]
        vals = run["collapse_index"].to_numpy(dtype=float)
        ns = run["n_judged"].to_numpy(dtype=int)
        row = {
            "physical_run_key": key,
            "run_uid": first["run_uid"],
            "run_id": first["run_id"],
            "source_short": first["source_short"],
            "source_path": first["source_path"],
            "internal_family_label": first["internal_family_label"],
            "condition": first["condition"],
            "n_judged_first_hour": int(ns.sum()),
            "n_bin_0_15": int(ns[0]),
            "n_bin_15_30": int(ns[1]),
            "n_bin_30_45": int(ns[2]),
            "n_bin_45_60": int(ns[3]),
            "collapse_0_15": vals[0],
            "collapse_15_30": vals[1],
            "collapse_30_45": vals[2],
            "collapse_45_60": vals[3],
            "delta_45_60_minus_0_15": vals[3] - vals[0] if np.isfinite(vals[0]) and np.isfinite(vals[3]) else math.nan,
        }
        rows.append(row)
    out = pd.DataFrame(rows)
    if len(post_counts):
        out = out.merge(post_counts, on="physical_run_key", how="left")
        out["judge_coverage_first_hour"] = out["n_judged_first_hour"] / out["n_posts_first_hour"]
    return out.sort_values(["internal_family_label", "condition", "source_short"])


def condition_summary(run_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition in CONDITION_ORDER:
        base = run_summary[(run_summary.internal_family_label == "single_model_final") & (run_summary.condition == condition)]
        obs = run_summary[(run_summary.internal_family_label == "obsession_prompting") & (run_summary.condition == condition)]
        if base.empty and obs.empty:
            continue
        bd = float(base.delta_45_60_minus_0_15.median()) if len(base) else math.nan
        od = float(obs.delta_45_60_minus_0_15.median()) if len(obs) else math.nan
        rows.append({
            "condition": condition,
            "condition_label": CONDITION_LABELS.get(condition, condition),
            "baseline_runs": int(len(base)),
            "fresh_obsession_runs": int(len(obs)),
            "baseline_delta_median": bd,
            "fresh_obsession_delta_median": od,
            "delta_difference_obs_minus_baseline": od - bd if np.isfinite(od) and np.isfinite(bd) else math.nan,
            "fresh_obsession_positive_delta": int((obs.delta_45_60_minus_0_15 > 0).sum()) if len(obs) else 0,
        })
    return pd.DataFrame(rows)


def plot(bins: pd.DataFrame, summary: pd.DataFrame) -> None:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42})
    fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.8), facecolor="#F7F3ED")
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.20, top=0.78, wspace=0.28)
    fig.text(0.07, 0.95, "Fresh OpenRouter judge: obsession first hour", fontsize=18, fontweight="bold", ha="left", color="#1F2A33")
    fig.text(0.07, 0.89, "A fresh blinded Gemini Flash Lite judge pass was run on all GPT-5 obsession posts in minutes 0--60. Runs are keyed by run_uid/source_path.", fontsize=9.5, ha="left", color="#52616B")

    ax = axes[0]
    x = np.arange(4)
    for family, label, color in [
        ("single_model_final", "Canonical GPT-5 n10 baseline", "#56616B"),
        ("obsession_prompting", "Obsession GPT-5 n10, fresh first-hour judge", "#D08A2E"),
    ]:
        sub = bins[bins.internal_family_label == family]
        y = sub.groupby("bin_idx").collapse_index.median().reindex(range(4)).to_numpy(dtype=float)
        ax.plot(x, y, marker="o", linewidth=2.5, color=color, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels(BIN_LABELS)
    ax.set_ylabel("Blinded LLM collapse index")
    ax.set_title("Median fixed-window trajectory")
    ax.grid(axis="y", color="#DDD8D0", linewidth=0.8)
    ax.legend(frameon=False, loc="lower right")

    ax = axes[1]
    conds = [c for c in CONDITION_ORDER if c in set(summary.condition)]
    xs = np.arange(len(conds)); width = 0.35
    s = summary.set_index("condition").reindex(conds)
    ax.bar(xs - width/2, s.baseline_delta_median, width, color="#56616B", label="Canonical baseline")
    ax.bar(xs + width/2, s.fresh_obsession_delta_median, width, color="#D08A2E", label="Fresh obsession judge")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([CONDITION_LABELS.get(c, c) for c in conds], rotation=20, ha="right")
    ax.set_ylabel("Delta collapse index: 45--60m minus 0--15m")
    ax.set_title("First-hour change by condition")
    ax.grid(axis="y", color="#DDD8D0", linewidth=0.8)
    ax.legend(frameon=False, loc="upper right")
    fig.text(0.07, 0.06, "Positive delta means later first-hour posts are judged more repetitive/convergent/rigid and less novel. MAG25 obsession has three physical GPT-5 runs.", fontsize=8.6, color="#52616B")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "obsession_first_hour_openrouter_judge.png", dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(OUT_DIR / "obsession_first_hour_openrouter_judge.pdf", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_readme(run_summary: pd.DataFrame, summary: pd.DataFrame) -> None:
    obs = run_summary[run_summary.internal_family_label == "obsession_prompting"].copy()
    n_runs = len(obs)
    pos = int((obs.delta_45_60_minus_0_15 > 0).sum())
    med = float(obs.delta_45_60_minus_0_15.median())
    cov = int((obs.judge_coverage_first_hour == 1).sum()) if "judge_coverage_first_hour" in obs else 0
    lines = [
        "# Step 12: fresh OpenRouter judge for obsession first hour",
        "",
        "This is a fresh OpenRouter LLM-as-judge pass over the corrected GPT-5 obsession first-hour set.",
        "The judge model is `google/gemini-3.1-flash-lite-preview`; rubric version is `ayush-blind-all-posts-v1`.",
        "All 5h obsession runs are truncated to minutes `0--60`; the true 1h run is used as-is.",
        "Physical runs are keyed by `run_uid + source_path`, not by `run_id`.",
        "",
        "## Outputs",
        "",
        "- `fresh_openrouter_blind_judge_results_with_metadata.csv`: row-level fresh judgments joined with metadata.",
        "- `obsession_first_hour_openrouter_bins.csv`: fixed 15-minute collapse/component means.",
        "- `obsession_first_hour_openrouter_run_summary.csv`: one row per physical run.",
        "- `obsession_first_hour_openrouter_condition_summary.csv`: comparison to canonical GPT-5 n10 baseline.",
        "- `obsession_first_hour_openrouter_judge.png/pdf`: paper-facing diagnostic figure.",
        "",
        "## Summary",
        "",
        f"- Fresh judged first-hour posts: `{int(obs.n_judged_first_hour.sum())}`.",
        f"- GPT-5 obsession physical runs analyzed: `{n_runs}`.",
        f"- First-hour judge coverage: `{cov}/{n_runs}` runs have judged posts equal to post-index posts.",
        f"- Positive first-hour LLM-collapse delta: `{pos}/{n_runs}` obsession runs.",
        f"- Median fresh obsession delta, 45--60m minus 0--15m: `{med:+.3f}`.",
        "",
        "## Condition-level deltas",
        "",
        "| Condition | Baseline runs | Fresh obsession runs | Baseline delta | Fresh obsession delta | Obs - baseline |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary.itertuples(index=False):
        lines.append(f"| {row.condition_label} | {row.baseline_runs} | {row.fresh_obsession_runs} | {row.baseline_delta_median:+.3f} | {row.fresh_obsession_delta_median:+.3f} | {row.delta_difference_obs_minus_baseline:+.3f} |")
    lines.append("")
    (OUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fresh_obs = read_judge(FRESH_JUDGE, "obsession_prompting")
    baseline = read_judge(BASELINE_JUDGE, "single_model_final")
    combined = pd.concat([baseline, fresh_obs], ignore_index=True)
    bins = build_bins(combined)
    runs = build_run_summary(bins, read_post_counts())
    summary = condition_summary(runs)
    bins.to_csv(OUT_DIR / "obsession_first_hour_openrouter_bins.csv", index=False)
    runs.to_csv(OUT_DIR / "obsession_first_hour_openrouter_run_summary.csv", index=False)
    summary.to_csv(OUT_DIR / "obsession_first_hour_openrouter_condition_summary.csv", index=False)
    fresh_obs.to_csv(OUT_DIR / "fresh_openrouter_blind_judge_results_with_metadata.csv", index=False)
    plot(bins, summary)
    write_readme(runs, summary)
    print(f"Wrote outputs to {OUT_DIR}")
    print(runs[runs.internal_family_label == "obsession_prompting"][["condition", "source_short", "n_judged_first_hour", "delta_45_60_minus_0_15", "judge_coverage_first_hour"]].to_string(index=False))


if __name__ == "__main__":
    main()
