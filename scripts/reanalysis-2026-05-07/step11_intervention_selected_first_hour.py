#!/usr/bin/env python3
"""Step 11: selected first-hour intervention comparison.

This script is for the final intervention comparison once first-hour LLM judge
outputs are available. It uses one pre-selected run per cohort and compares
actual first-hour cumulative cutoffs: 0-15, 0-30, 0-45, and 0-60 minutes.

It intentionally does not take cohort medians.
"""
from __future__ import annotations

import argparse
import gzip
import json
import math
import re
import sys
from pathlib import Path
from typing import Iterable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import AYUSH_ROOT, PLOT_ROOT, condition_label, setup_style  # noqa: E402

POST_INDEX = AYUSH_ROOT / "post_index.csv"
OUT_DIR = PLOT_ROOT / "step11_intervention_selected_first_hour"

CUTOFFS = [("0-15m", 15.0), ("0-30m", 30.0), ("0-45m", 45.0), ("0-60m", 60.0)]
BIN_LABEL_MAP = {
    "0-15": 0,
    "0-15m": 0,
    "15-30": 1,
    "15-30m": 1,
    "30-45": 2,
    "30-45m": 2,
    "45-60": 3,
    "45-60m": 3,
    "Q1": 0,
    "Q2": 1,
    "Q3": 2,
    "Q4": 3,
}
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)

SELECTED_BY_CONDITION = {
    "mag0": [
        {
            "key": "canonical_gpt5",
            "label": "Canonical GPT-5",
            "short_label": "Canonical GPT-5",
            "run_uid": "52cbe1b58dae376873d521996f9f08f26579623f",
            "color": "#56616B",
        },
        {
            "key": "qwen_base_tool",
            "label": "Qwen base tool",
            "short_label": "Qwen base tool",
            "run_uid": "2ec295c49e9fc76a684c9a5e7fba4475d07aa444",
            "color": "#0E7C7B",
        },
        {
            "key": "mixed_roster",
            "label": "Mixed-model roster",
            "short_label": "Mixed roster",
            "run_uid": "414de5708c19ec70bf042d934ff00dcab6a86d15",
            "color": "#B24E3A",
        },
        {
            "key": "obsession_gpt5",
            "label": "Obsession GPT-5, first hour of 5h run",
            "short_label": "Obsession GPT-5",
            "run_uid": "329e6d908c55bed5cac56f80110982ca7a35521b",
            "color": "#D08A2E",
        },
    ],
    "mag25": [
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
            "key": "obsession_gpt5",
            "label": "Obsession GPT-5, 1h run",
            "short_label": "Obsession GPT-5",
            "run_uid": "0e1a75b82e3e1c9395f6955b14174d7d7baa76f3",
            "color": "#D08A2E",
        },
    ],
    "dom-agi": [
        {
            "key": "canonical_gpt5",
            "label": "Canonical GPT-5",
            "short_label": "Canonical GPT-5",
            "run_uid": "5a3139019e30ef5344c4f09f69968cf1d93292a0",
            "color": "#56616B",
        },
        {
            "key": "qwen_base_tool",
            "label": "Qwen base tool",
            "short_label": "Qwen base tool",
            "run_uid": "356e5ccaff59febc37a3e2d77af06ee9124f1174",
            "color": "#0E7C7B",
        },
        {
            "key": "mixed_roster",
            "label": "Mixed-model roster",
            "short_label": "Mixed roster",
            "run_uid": "fc9ac31f2cddf9fe833f67dd50aec10f4c098072",
            "color": "#B24E3A",
        },
        {
            "key": "obsession_gpt5",
            "label": "Obsession GPT-5, first hour of 5h run",
            "short_label": "Obsession GPT-5",
            "run_uid": "a4205cf68c020cde9babaeb76661e33cc86191e8",
            "color": "#D08A2E",
        },
    ],
}

METRICS_WITH_LLM = [
    {"key": "distinct5", "title": "Cumulative Distinct-5", "ylabel": "Distinct-5", "direction": "lower = fewer unique 5-grams"},
    {"key": "gzip", "title": "Cumulative gzip", "ylabel": "gzip ratio", "direction": "lower = easier to compress"},
    {"key": "llm_collapse", "title": "Cumulative LLM collapse index", "ylabel": "collapse index", "direction": "higher = more judged collapse"},
]
METRICS_TEXT_ONLY = METRICS_WITH_LLM[:2]


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


def selected_rows(conditions: Iterable[str]) -> list[dict[str, str]]:
    rows = []
    for condition in conditions:
        if condition not in SELECTED_BY_CONDITION:
            raise ValueError(f"Unsupported condition {condition!r}. Expected one of {sorted(SELECTED_BY_CONDITION)}")
        for order, row in enumerate(SELECTED_BY_CONDITION[condition]):
            rows.append({**row, "condition": condition, "selected_order": order})
    return rows


def selected_lookup(conditions: Iterable[str]) -> dict[str, dict[str, str]]:
    return {row["run_uid"]: row for row in selected_rows(conditions)}


def load_selected_posts(conditions: Iterable[str]) -> pd.DataFrame:
    selected = selected_lookup(conditions)
    df = pd.read_csv(POST_INDEX, low_memory=False)
    sub = df[
        (~df["is_seed"].astype(bool))
        & (df["run_uid"].isin(selected))
        & (df["condition"].isin(list(conditions)))
        & (df["n_agents"] == 10)
    ].copy()
    sub["minutes_numeric"] = pd.to_numeric(sub["minutes_elapsed"], errors="coerce")
    sub = sub[(sub["minutes_numeric"] >= 0) & (sub["minutes_numeric"] <= 60.000001)].copy()
    sub["text"] = sub["text"].fillna("").astype(str)
    sub["selected_key"] = sub["run_uid"].map(lambda uid: selected[uid]["key"])
    sub["selected_label"] = sub["run_uid"].map(lambda uid: selected[uid]["label"])
    sub["short_label"] = sub["run_uid"].map(lambda uid: selected[uid]["short_label"])
    sub["selected_order"] = sub["run_uid"].map(lambda uid: selected[uid]["selected_order"])
    return sub.sort_values(["condition", "selected_order", "minutes_numeric", "post_id"])


def cumulative_text_metrics(posts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (condition, run_uid), sub in posts.groupby(["condition", "run_uid"], dropna=False):
        first = sub.iloc[0]
        for bin_idx, (bin_label, cutoff) in enumerate(CUTOFFS):
            members = sub[sub["minutes_numeric"] <= cutoff]
            texts = members["text"].dropna().astype(str).tolist()
            rows.append({
                "condition": condition,
                "condition_label": condition_label(condition),
                "run_uid": run_uid,
                "run_id": first["run_id"],
                "source_path": first["source_path"],
                "selected_key": first["selected_key"],
                "selected_label": first["selected_label"],
                "short_label": first["short_label"],
                "selected_order": int(first["selected_order"]),
                "internal_family_label": first["internal_family_label"],
                "model_display": first["model_display"],
                "bin_idx": bin_idx,
                "bin_label": bin_label,
                "cutoff_minutes": cutoff,
                "n_posts_cumulative": int(len(members)),
                "n_posts_first_hour": int(len(sub)),
                "distinct5": distinct5(texts),
                "gzip": compression_ratio(texts),
            })
    return pd.DataFrame(rows)


def _coerce_is_seed(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(["true", "1", "yes"])


def load_row_level_llm(path: Path, conditions: Iterable[str]) -> pd.DataFrame:
    selected = selected_lookup(conditions)
    df = pd.read_csv(path, low_memory=False)
    required = {"run_uid", "minutes_elapsed", "collapse_index"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Row-level LLM file is missing columns: {sorted(missing)}")
    sub = df[df["run_uid"].isin(selected)].copy()
    if "condition" in sub.columns:
        sub = sub[sub["condition"].isin(list(conditions))].copy()
    if "is_seed" in sub.columns:
        sub = sub[~_coerce_is_seed(sub["is_seed"])].copy()
    sub["minutes_numeric"] = pd.to_numeric(sub["minutes_elapsed"], errors="coerce")
    sub["collapse_numeric"] = pd.to_numeric(sub["collapse_index"], errors="coerce")
    sub = sub[(sub["minutes_numeric"] >= 0) & (sub["minutes_numeric"] <= 60.000001)].copy()
    rows = []
    for run_uid, run in sub.groupby("run_uid", dropna=False):
        selected_row = selected[run_uid]
        for bin_idx, (bin_label, cutoff) in enumerate(CUTOFFS):
            members = run[run["minutes_numeric"] <= cutoff]
            vals = members["collapse_numeric"].dropna().to_numpy(dtype=float)
            rows.append({
                "run_uid": run_uid,
                "bin_idx": bin_idx,
                "bin_label": bin_label,
                "llm_collapse": float(np.mean(vals)) if len(vals) else math.nan,
                "n_judged_cumulative": int(len(vals)),
                "llm_source_mode": "row_level",
                "llm_selected_key": selected_row["key"],
            })
    return pd.DataFrame(rows)


def load_timebin_llm(path: Path, conditions: Iterable[str]) -> pd.DataFrame:
    selected = selected_lookup(conditions)
    df = pd.read_csv(path, low_memory=False)
    required = {"run_uid", "collapse_index"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Timebin LLM file is missing columns: {sorted(missing)}")
    sub = df[df["run_uid"].isin(selected)].copy()
    if "condition" in sub.columns:
        sub = sub[sub["condition"].isin(list(conditions))].copy()
    if "scheme" in sub.columns:
        fixed = sub["scheme"].astype(str).str.contains("fixed|15", case=False, regex=True, na=False)
        if fixed.any():
            sub = sub[fixed].copy()
    if "bin_idx" not in sub.columns:
        if "bin_label" not in sub.columns:
            raise ValueError("Timebin LLM file needs either bin_idx or bin_label")
        sub["bin_idx"] = sub["bin_label"].map(BIN_LABEL_MAP)
    sub["bin_idx"] = pd.to_numeric(sub["bin_idx"], errors="coerce")
    sub["collapse_numeric"] = pd.to_numeric(sub["collapse_index"], errors="coerce")
    if "n_judged" in sub.columns:
        sub["n_judged_numeric"] = pd.to_numeric(sub["n_judged"], errors="coerce").fillna(0.0)
    else:
        sub["n_judged_numeric"] = 1.0
    rows = []
    for run_uid, run in sub.dropna(subset=["bin_idx"]).groupby("run_uid", dropna=False):
        run = run.sort_values("bin_idx")
        weighted_sum = 0.0
        weight = 0.0
        for bin_idx in range(len(CUTOFFS)):
            point = run[run["bin_idx"].astype(int) == bin_idx]
            if not point.empty:
                # If duplicate rows exist, aggregate them before cumulating.
                vals = point["collapse_numeric"].to_numpy(dtype=float)
                weights = point["n_judged_numeric"].to_numpy(dtype=float)
                ok = np.isfinite(vals) & np.isfinite(weights) & (weights > 0)
                if ok.any():
                    weighted_sum += float(np.sum(vals[ok] * weights[ok]))
                    weight += float(np.sum(weights[ok]))
            rows.append({
                "run_uid": run_uid,
                "bin_idx": bin_idx,
                "bin_label": CUTOFFS[bin_idx][0],
                "llm_collapse": weighted_sum / weight if weight else math.nan,
                "n_judged_cumulative": int(weight),
                "llm_source_mode": "timebin",
            })
    return pd.DataFrame(rows)


def load_llm_metrics(path: Path, conditions: Iterable[str], mode: str) -> pd.DataFrame:
    if mode == "row":
        return load_row_level_llm(path, conditions)
    if mode == "timebin":
        return load_timebin_llm(path, conditions)
    if mode == "auto":
        header = pd.read_csv(path, nrows=0)
        cols = set(header.columns)
        if {"minutes_elapsed", "collapse_index"}.issubset(cols):
            return load_row_level_llm(path, conditions)
        return load_timebin_llm(path, conditions)
    raise ValueError(mode)


def build_table(conditions: list[str], llm_file: Path | None, llm_mode: str) -> pd.DataFrame:
    posts = load_selected_posts(conditions)
    text = cumulative_text_metrics(posts)
    if llm_file is None:
        text["llm_collapse"] = np.nan
        text["n_judged_cumulative"] = 0
        text["llm_source_mode"] = "pending"
        return text
    llm = load_llm_metrics(llm_file, conditions, llm_mode)
    return text.merge(llm[["run_uid", "bin_idx", "llm_collapse", "n_judged_cumulative", "llm_source_mode"]], on=["run_uid", "bin_idx"], how="left")


def validate_completeness(df: pd.DataFrame, conditions: list[str], require_llm: bool) -> None:
    selected = selected_lookup(conditions)
    found = set(df["run_uid"].dropna().unique())
    missing_runs = set(selected) - found
    if missing_runs:
        labels = [selected[uid]["label"] for uid in sorted(missing_runs)]
        raise RuntimeError(f"Missing selected post runs: {labels}")
    if require_llm:
        final = df[df["bin_idx"] == len(CUTOFFS) - 1]
        bad = final[(pd.to_numeric(final["n_judged_cumulative"], errors="coerce") <= 0) | (pd.to_numeric(final["llm_collapse"], errors="coerce").isna())]
        if not bad.empty:
            details = bad[["condition", "selected_label", "run_id", "run_uid"]].to_dict(orient="records")
            raise RuntimeError(f"Missing LLM data for selected runs: {details}")


def draw_condition_plot(df: pd.DataFrame, condition: str, include_llm: bool, output_path: Path) -> None:
    setup_style()
    metrics = METRICS_WITH_LLM if include_llm else METRICS_TEXT_ONLY
    width = 15.8 if include_llm else 10.8
    fig, axes = plt.subplots(1, len(metrics), figsize=(width, 6.9), facecolor="#F7F3ED")
    if len(metrics) == 1:
        axes = [axes]
    fig.subplots_adjust(left=0.070, right=0.985, top=0.760, bottom=0.310, wspace=0.270)
    fig.text(0.070, 0.945, "Selected first-hour intervention runs", ha="left", va="top", fontsize=22, fontweight="bold", color="#1F2A33")
    fig.text(0.070, 0.892, f"Condition fixed to {condition_label(condition)}. Each line is one selected run, not a cohort median.", ha="left", va="top", fontsize=11.2, color="#52616B")
    fig.text(0.070, 0.862, "Cutoffs use actual elapsed minutes: 0-15, 0-30, 0-45, and 0-60.", ha="left", va="top", fontsize=9.8, color="#6D7980")

    selected = SELECTED_BY_CONDITION[condition]
    x = np.arange(len(CUTOFFS))
    cond_df = df[df["condition"] == condition]
    for ax, metric in zip(axes, metrics):
        for row in selected:
            line = cond_df[cond_df["selected_key"] == row["key"]].sort_values("bin_idx")
            if line.empty:
                continue
            total_posts = int(line["n_posts_first_hour"].max())
            y = pd.to_numeric(line[metric["key"]], errors="coerce").to_numpy(dtype=float)
            ax.plot(x, y, marker="o", linewidth=2.4, markersize=5.8, color=row["color"], label=f"{row['short_label']} ({total_posts} posts)")
        ax.set_title(metric["title"], fontsize=12.5, fontweight="bold", color="#1F2A33", pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels([label for label, _ in CUTOFFS])
        ax.set_xlabel("Cumulative first-hour cutoff")
        ax.set_ylabel(metric["ylabel"])
        ax.grid(axis="y", color="#DDD8D0", linewidth=0.8, alpha=0.70)
        ax.text(0.02, 0.04, metric["direction"], transform=ax.transAxes, ha="left", va="bottom", fontsize=8.3, color="#6D7980")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8.5, bbox_to_anchor=(0.5, 0.150))
    note = "Post counts are non-seed agent posts in the first 60 minutes. Qwen base tool uses Gemini Flash Lite for orchestration and Qwen as the content-generation tool."
    if not include_llm:
        note += " LLM panel omitted because no LLM file was supplied."
    fig.text(0.070, 0.058, note, ha="left", va="bottom", fontsize=8.6, color="#6D7980")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_outputs(df: pd.DataFrame, conditions: list[str], llm_file: Path | None, include_llm: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "intervention_selected_first_hour_metrics.csv", index=False)
    final = df[df["bin_idx"] == len(CUTOFFS) - 1].copy().sort_values(["condition", "selected_order"])
    final.to_csv(OUT_DIR / "intervention_selected_first_hour_final_values.csv", index=False)
    inventory = final[["condition", "selected_label", "run_id", "run_uid", "source_path", "n_posts_first_hour", "n_judged_cumulative"]].copy()
    inventory.to_csv(OUT_DIR / "intervention_selected_first_hour_run_inventory.csv", index=False)

    for condition in conditions:
        draw_condition_plot(df, condition, include_llm, OUT_DIR / f"intervention_selected_first_hour_{condition}.png")

    summary = {
        "conditions": conditions,
        "cutoffs": CUTOFFS,
        "llm_file": str(llm_file) if llm_file else None,
        "include_llm": include_llm,
        "selected_runs": selected_rows(conditions),
        "final_values": final.to_dict(orient="records"),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    readme = """# Step 11: selected first-hour intervention comparison

This is the no-median, one-run-per-line intervention script for `mag0`, `mag25`, and `dom-agi`.

## Design

- One selected run per cohort.
- Actual first-hour cutoffs: 0-15, 0-30, 0-45, 0-60 minutes.
- Agent-generated posts only.
- Seed rows excluded.
- No cohort medians.
- No condition pooling.

## LLM input

Preferred LLM input is a row-level judged CSV with columns:

```text
run_uid, minutes_elapsed, collapse_index
```

Optional useful columns:

```text
condition, is_seed, record_id, run_id
```

The script also accepts time-bin metrics with:

```text
run_uid, bin_label or bin_idx, collapse_index, n_judged
```

## Run later with LLM data

```bash
python3 scripts/reanalysis-2026-05-07/step11_intervention_selected_first_hour.py \
  --llm-file path/to/first_hour_llm_judge_results.csv \
  --llm-mode auto
```

## Text-only preview

```bash
python3 scripts/reanalysis-2026-05-07/step11_intervention_selected_first_hour.py --text-only
```
"""
    (OUT_DIR / "README.md").write_text(readme)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conditions", nargs="+", default=["mag0", "mag25", "dom-agi"], choices=sorted(SELECTED_BY_CONDITION))
    parser.add_argument("--llm-file", type=Path, default=None, help="Future first-hour LLM judge CSV. Row-level and time-bin formats are both supported.")
    parser.add_argument("--llm-mode", choices=["auto", "row", "timebin"], default="auto")
    parser.add_argument("--text-only", action="store_true", help="Allow running without LLM data and omit the LLM panel.")
    parser.add_argument("--allow-missing-llm", action="store_true", help="Do not fail if the LLM file is incomplete. Useful for debugging only.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.llm_file is None and not args.text_only:
        raise SystemExit("Pass --llm-file when LLM data are ready, or use --text-only for a text-metric preview.")
    if args.llm_file is not None and not args.llm_file.exists():
        raise FileNotFoundError(args.llm_file)

    conditions = list(args.conditions)
    df = build_table(conditions, args.llm_file, args.llm_mode)
    include_llm = args.llm_file is not None
    validate_completeness(df, conditions, require_llm=include_llm and not args.allow_missing_llm)
    write_outputs(df, conditions, args.llm_file, include_llm)
    print(f"Wrote Step 11 outputs to {OUT_DIR}")
    print(df[df["bin_idx"] == len(CUTOFFS) - 1][["condition", "selected_label", "run_id", "n_posts_first_hour", "n_judged_cumulative", "distinct5", "gzip", "llm_collapse"]].to_string(index=False))


if __name__ == "__main__":
    main()
