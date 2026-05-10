#!/usr/bin/env python3
"""Step 11: first-hour LLM-judge analysis for obsession prompting.

The obsession cohort mixes 1h and 5h exports, and one MAG25 1h run shares a
human-readable run_id with a distinct 5h run. This script fixes both issues by:

1. grouping physical runs by (run_uid, source_path), not run_id;
2. filtering every run to minutes_elapsed in [0, 60];
3. computing fixed 15-minute LLM-collapse bins on the first hour only.

It uses already-computed blinded LLM judge results; no judge calls are made.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
JUDGE_CANDIDATES = [
    REPO / "analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv",
    REPO / "data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv",
]
POST_INDEX_CANDIDATES = [
    REPO / "analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/post_index.csv",
    REPO / "data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/post_index.csv",
]
OUT_DIR = REPO / "findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step11_obsession_first_hour_llm_judge"

BIN_EDGES = [0, 15, 30, 45, 60.000001]
BIN_LABELS = ["0-15m", "15-30m", "30-45m", "45-60m"]
COMPONENTS = [
    "semantic_repetition",
    "frame_convergence",
    "consensus_conformity",
    "template_rigidity",
    "novelty",
]
CONDITION_LABELS = {
    "mag0": "Empty",
    "mag1": "1 consp.",
    "mag5": "5 consp.",
    "mag25": "25 consp.",
    "dom-agi": "AGI",
    "dom-tech": "Tech",
}
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]


def first_existing(paths: list[Path]) -> Path:
    for path in paths:
        if path.exists():
            return path
    raise FileNotFoundError("None found: " + ", ".join(str(p) for p in paths))


def source_short(source_path: str) -> str:
    marker = "/2026-05-05/"
    if marker in source_path:
        return source_path.split(marker, 1)[1]
    marker = "/project-results/"
    if marker in source_path:
        return source_path.split(marker, 1)[1]
    return source_path


def bin_idx(minutes: float) -> int | None:
    if minutes < 0 or minutes > 60:
        return None
    for i in range(4):
        if BIN_EDGES[i] <= minutes < BIN_EDGES[i + 1]:
            return i
    return None


def load_first_hour_judgments() -> pd.DataFrame:
    judge_path = first_existing(JUDGE_CANDIDATES)
    df = pd.read_csv(judge_path, low_memory=False)
    df["minutes_elapsed"] = pd.to_numeric(df["minutes_elapsed"], errors="coerce")
    df["collapse_index"] = pd.to_numeric(df["collapse_index"], errors="coerce")
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce")
    for col in COMPONENTS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    keep = (
        (df["is_seed"].astype(str) == "False")
        & (df["model_family"] == "gpt-5")
        & (df["n_agents"] == 10)
        & (df["internal_family_label"].isin(["single_model_final", "obsession_prompting"]))
        & (df["minutes_elapsed"] >= 0)
        & (df["minutes_elapsed"] <= 60)
    )
    out = df[keep].copy()
    out["physical_run_key"] = out["run_uid"].astype(str) + "::" + out["source_path"].astype(str)
    out["source_short"] = out["source_path"].map(source_short)
    out["first_hour_bin"] = out["minutes_elapsed"].map(bin_idx)
    out["first_hour_bin_label"] = out["first_hour_bin"].map(lambda i: BIN_LABELS[int(i)] if pd.notna(i) else "")
    return out.sort_values(["internal_family_label", "condition", "source_short", "minutes_elapsed"])


def load_first_hour_post_counts() -> pd.DataFrame:
    post_path = first_existing(POST_INDEX_CANDIDATES)
    df = pd.read_csv(post_path, low_memory=False)
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


def build_bin_table(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_cols = [
        "physical_run_key", "run_uid", "run_id", "source_path", "source_short",
        "internal_family_label", "display_family_label", "condition", "model_family",
    ]
    for key, run in df.groupby(group_cols, dropna=False):
        meta = dict(zip(group_cols, key))
        for i, label in enumerate(BIN_LABELS):
            part = run[run["first_hour_bin"] == i]
            row = dict(meta)
            row.update({
                "bin_idx": i,
                "bin_label": label,
                "n_judged": int(len(part)),
                "collapse_index": float(part["collapse_index"].mean()) if len(part) else math.nan,
            })
            for col in COMPONENTS:
                row[col] = float(part[col].mean()) if len(part) else math.nan
            rows.append(row)
    return pd.DataFrame(rows)


def build_run_summary(bin_table: pd.DataFrame, post_counts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, run in bin_table.groupby("physical_run_key", dropna=False):
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
            "display_family_label": first["display_family_label"],
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
            "collapse_first_hour_mean": float(np.average(vals[np.isfinite(vals)], weights=ns[np.isfinite(vals)])) if ns[np.isfinite(vals)].sum() else math.nan,
        }
        rows.append(row)
    out = pd.DataFrame(rows)
    out = out.merge(post_counts, on="physical_run_key", how="left")
    out["judge_coverage_first_hour"] = out["n_judged_first_hour"] / out["n_posts_first_hour"]
    return out.sort_values(["internal_family_label", "condition", "source_short"])


def build_condition_summary(run_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for condition in CONDITION_ORDER:
        base = run_summary[(run_summary["internal_family_label"] == "single_model_final") & (run_summary["condition"] == condition)]
        obs = run_summary[(run_summary["internal_family_label"] == "obsession_prompting") & (run_summary["condition"] == condition)]
        if base.empty and obs.empty:
            continue
        row = {
            "condition": condition,
            "condition_label": CONDITION_LABELS.get(condition, condition),
            "baseline_runs": int(len(base)),
            "obsession_runs": int(len(obs)),
            "baseline_delta_median": float(base["delta_45_60_minus_0_15"].median()) if len(base) else math.nan,
            "obsession_delta_median": float(obs["delta_45_60_minus_0_15"].median()) if len(obs) else math.nan,
            "baseline_final_median": float(base["collapse_45_60"].median()) if len(base) else math.nan,
            "obsession_final_median": float(obs["collapse_45_60"].median()) if len(obs) else math.nan,
            "obsession_positive_delta": int((obs["delta_45_60_minus_0_15"] > 0).sum()) if len(obs) else 0,
        }
        row["delta_difference_obs_minus_baseline"] = row["obsession_delta_median"] - row["baseline_delta_median"] if np.isfinite(row["obsession_delta_median"]) and np.isfinite(row["baseline_delta_median"]) else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


def plot(bin_table: pd.DataFrame, run_summary: pd.DataFrame, condition_summary: pd.DataFrame) -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })
    fig, axes = plt.subplots(1, 2, figsize=(13.4, 5.8), facecolor="#F7F3ED")
    fig.subplots_adjust(left=0.07, right=0.98, bottom=0.20, top=0.78, wspace=0.28)
    fig.text(0.07, 0.95, "Obsession prompting: first-hour LLM-judge check", fontsize=18, fontweight="bold", ha="left", color="#1F2A33")
    fig.text(0.07, 0.89, "All GPT-5 obsession runs are truncated to minutes 0--60 and grouped by run_uid/source_path to avoid merging 1h and 5h MAG25 exports.", fontsize=9.5, ha="left", color="#52616B")

    ax = axes[0]
    x = np.arange(4)
    for family, label, color in [
        ("single_model_final", "Canonical GPT-5 n10", "#56616B"),
        ("obsession_prompting", "Obsession GPT-5 n10, first hour", "#D08A2E"),
    ]:
        sub = bin_table[bin_table["internal_family_label"] == family]
        med = sub.groupby("bin_idx")["collapse_index"].median().reindex(range(4)).to_numpy(dtype=float)
        ax.plot(x, med, marker="o", linewidth=2.5, color=color, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels(BIN_LABELS)
    ax.set_ylabel("Blinded LLM collapse index")
    ax.set_title("Median fixed-window trajectory")
    ax.grid(axis="y", color="#DDD8D0", linewidth=0.8)
    ax.legend(frameon=False, loc="lower right")

    ax = axes[1]
    conds = [c for c in CONDITION_ORDER if c in set(condition_summary["condition"])]
    xs = np.arange(len(conds))
    width = 0.35
    base = condition_summary.set_index("condition").reindex(conds)
    ax.bar(xs - width/2, base["baseline_delta_median"], width, color="#56616B", label="Canonical baseline")
    ax.bar(xs + width/2, base["obsession_delta_median"], width, color="#D08A2E", label="Obsession, first hour")
    ax.axhline(0, color="#333333", linewidth=0.8)
    ax.set_xticks(xs)
    ax.set_xticklabels([CONDITION_LABELS.get(c, c) for c in conds], rotation=20, ha="right")
    ax.set_ylabel("Delta collapse index: 45--60m minus 0--15m")
    ax.set_title("Run-level first-hour change by condition")
    ax.grid(axis="y", color="#DDD8D0", linewidth=0.8)
    ax.legend(frameon=False, loc="upper right")

    fig.text(0.07, 0.06, "Positive delta means later first-hour posts are judged more repetitive/convergent/rigid and less novel. MAG25 obsession has three physical GPT-5 runs.", fontsize=8.6, color="#52616B")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_DIR / "obsession_first_hour_llm_judge.png", dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(OUT_DIR / "obsession_first_hour_llm_judge.pdf", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_readme(run_summary: pd.DataFrame, condition_summary: pd.DataFrame) -> None:
    obs = run_summary[run_summary["internal_family_label"] == "obsession_prompting"].copy()
    n_runs = len(obs)
    complete = int((obs["judge_coverage_first_hour"] == 1).sum())
    pos = int((obs["delta_45_60_minus_0_15"] > 0).sum())
    median_delta = float(obs["delta_45_60_minus_0_15"].median())
    lines = [
        "# Step 11: obsession first-hour LLM-judge check",
        "",
        "This pass fixes the obsession-duration issue by analyzing only minutes `0--60` for every GPT-5 obsession run.",
        "The 5h runs are truncated to their first hour; the true 1h run is used as-is.",
        "Physical runs are grouped by `run_uid` and `source_path`, not by `run_id`, because `obs-mag25-n10-run01-gpt-5-20260418` is reused by both `obs-mag25-1h` and `obs-mag25-5h-run02`.",
        "",
        "No new LLM calls were needed: the existing blinded judge file already contains scores for every first-hour GPT-5 obsession post.",
        "",
        "## Outputs",
        "",
        "- `obsession_first_hour_llm_bins.csv`: fixed 15-minute collapse/component means.",
        "- `obsession_first_hour_llm_run_summary.csv`: one row per physical run.",
        "- `obsession_first_hour_llm_condition_summary.csv`: condition-level comparison with canonical GPT-5 n10 baselines.",
        "- `obsession_first_hour_llm_judge.png/pdf`: trajectory and delta figure.",
        "",
        "## Summary",
        "",
        f"- GPT-5 obsession physical runs analyzed: `{n_runs}`.",
        f"- First-hour judge coverage: `{complete}/{n_runs}` runs have judged posts equal to post-index posts.",
        f"- Positive first-hour LLM-collapse delta: `{pos}/{n_runs}` obsession runs.",
        f"- Median obsession delta, 45--60m minus 0--15m: `{median_delta:+.3f}`.",
        "",
        "## Condition-level deltas",
        "",
        "| Condition | Baseline runs | Obsession runs | Baseline delta | Obsession delta | Obs - baseline |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in condition_summary.itertuples(index=False):
        lines.append(
            f"| {row.condition_label} | {row.baseline_runs} | {row.obsession_runs} | "
            f"{row.baseline_delta_median:+.3f} | {row.obsession_delta_median:+.3f} | {row.delta_difference_obs_minus_baseline:+.3f} |"
        )
    lines.append("")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "README.md").write_text("\n".join(lines))


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = load_first_hour_judgments()
    post_counts = load_first_hour_post_counts()
    bin_table = build_bin_table(df)
    run_summary = build_run_summary(bin_table, post_counts)
    condition_summary = build_condition_summary(run_summary)

    bin_table.to_csv(OUT_DIR / "obsession_first_hour_llm_bins.csv", index=False)
    run_summary.to_csv(OUT_DIR / "obsession_first_hour_llm_run_summary.csv", index=False)
    condition_summary.to_csv(OUT_DIR / "obsession_first_hour_llm_condition_summary.csv", index=False)
    plot(bin_table, run_summary, condition_summary)
    write_readme(run_summary, condition_summary)

    print(f"Wrote outputs to {OUT_DIR}")
    print(run_summary[run_summary["internal_family_label"] == "obsession_prompting"][[
        "condition", "source_short", "n_posts_first_hour", "n_judged_first_hour", "delta_45_60_minus_0_15", "judge_coverage_first_hour"
    ]].to_string(index=False))


if __name__ == "__main__":
    main()
