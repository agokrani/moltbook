#!/usr/bin/env python3
"""Step 2: cumulative canonical 10-agent trajectories.

Each x-axis point uses all non-seed posts up to that time cutoff:
0-15, 0-30, 0-45, and 0-60 minutes.
"""
from __future__ import annotations

import gzip
import math
import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from common import (
    CONDITION_COLORS,
    CONDITION_ORDER,
    DATA_ROOT,
    EMBEDDING_TIMEBINS,
    LLM_TIMEBINS,
    MODEL_ORDER,
    PLOT_ROOT,
    condition_label,
    load_timebins,
    save_figure,
    setup_style,
)

OUT = PLOT_ROOT / "step02_canonical_n10_trajectories_cumulative"
POST_INDEX = DATA_ROOT / "ayush_reanalysis/post_index.csv"
BIN_CUTOFFS = [("0-15", 15), ("15-30", 30), ("30-45", 45), ("45-60", 60)]
BIN_ORDER = ["0-15m", "15-30m", "30-45m", "45-60m"]
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)

METRIC_INFO = {
    "gzip": {
        "label": "Cumulative gzip compression ratio",
        "short": "Gzip",
        "direction": "Down means all text so far is easier to compress and more repetitive.",
        "file_slug": "gzip",
    },
    "distinct5": {
        "label": "Cumulative Distinct-5",
        "short": "Distinct-5",
        "direction": "Down means the feed so far has fewer unique 5-grams.",
        "file_slug": "distinct5",
    },
    "llm_collapse": {
        "label": "Cumulative blinded LLM collapse index",
        "short": "LLM collapse",
        "direction": "Up means the feed so far is judged more repetitive, rigid, conformist, and less novel.",
        "file_slug": "llm_collapse",
    },
}


def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in TOKEN_RE.finditer(text or "")]


def distinct5(texts: list[str]) -> float:
    total = 0
    unique = set()
    for text in texts:
        toks = tokenize(text)
        if len(toks) < 5:
            continue
        grams = [tuple(toks[i:i+5]) for i in range(len(toks) - 4)]
        total += len(grams)
        unique.update(grams)
    return float(len(unique) / total) if total else math.nan


def compression_ratio(texts: list[str]) -> float:
    raw = "\n".join(t for t in texts if t).encode("utf-8")
    if not raw:
        return math.nan
    return float(len(gzip.compress(raw)) / len(raw))


def load_posts() -> pd.DataFrame:
    df = pd.read_csv(POST_INDEX, low_memory=False)
    df = df[
        (~df["is_seed"].astype(bool))
        & (df["internal_family_label"] == "single_model_final")
        & (df["n_agents"] == 10)
        & (df["model_display"].isin(MODEL_ORDER))
        & (df["minutes_elapsed"] >= 0)
        & (df["minutes_elapsed"] <= 60)
    ].copy()
    df["text"] = df["text"].fillna("")
    df["record_id"] = df["record_id"].astype(str)
    return df


def cumulative_text_metrics(posts: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (run_uid, model, cond), sub in posts.groupby(["run_uid", "model_display", "condition"], dropna=False):
        sub = sub.sort_values("minutes_elapsed")
        for idx, (label, cutoff) in enumerate(BIN_CUTOFFS):
            members = sub[sub["minutes_elapsed"] <= cutoff]
            texts = members["text"].dropna().astype(str).tolist()
            rows.append({
                "run_uid": run_uid,
                "model_display": model,
                "condition": cond,
                "bin_idx": idx,
                "bin_label": label,
                "n_posts_cumulative": len(members),
                "gzip": compression_ratio(texts),
                "distinct5": distinct5(texts),
            })
    return pd.DataFrame(rows)


def cumulative_llm() -> pd.DataFrame:
    llm = pd.read_csv(LLM_TIMEBINS, low_memory=False)
    llm = llm[
        (llm["internal_family_label"] == "single_model_final")
        & (llm["scheme"] == "fixed_15m")
        & (llm["n_agents"] == 10)
        & (llm["model_display"].isin(MODEL_ORDER))
    ].copy()
    llm["bin_label"] = pd.Categorical(llm["bin_label"], categories=BIN_ORDER, ordered=True)
    rows = []
    for (run_uid, model, cond), sub in llm.groupby(["run_uid", "model_display", "condition"], dropna=False):
        sub = sub.sort_values("bin_label")
        weighted_sum = 0.0
        weight = 0.0
        for idx, (_, row) in enumerate(sub.iterrows()):
            n = float(row.get("n_judged", 0) or 0)
            val = float(row.get("collapse_index", math.nan))
            if np.isfinite(val) and n > 0:
                weighted_sum += val * n
                weight += n
            rows.append({
                "run_uid": run_uid,
                "model_display": model,
                "condition": cond,
                "bin_idx": idx,
                "bin_label": BIN_CUTOFFS[idx][0],
                "llm_collapse": weighted_sum / weight if weight > 0 else math.nan,
            })
    return pd.DataFrame(rows)


def build_cumulative_table() -> pd.DataFrame:
    posts = load_posts()
    text = cumulative_text_metrics(posts)
    llm = cumulative_llm()
    df = text.merge(llm[["run_uid", "bin_idx", "llm_collapse"]], on=["run_uid", "bin_idx"], how="left")
    return df


def title_for(metric_key: str) -> str:
    info = METRIC_INFO[metric_key]
    if metric_key == "llm_collapse":
        return f"Does the feed so far become more repetitive? {info['short']}"
    return f"Does the feed so far lose diversity? {info['short']}"


def plot_metric(df: pd.DataFrame, metric_key: str) -> None:
    info = METRIC_INFO[metric_key]
    fig, axes = plt.subplots(2, 2, figsize=(13.8, 8.6), sharex=True, sharey=False)
    fig.subplots_adjust(left=0.08, right=0.82, top=0.88, bottom=0.13, wspace=0.08, hspace=0.28)
    axes = axes.ravel()

    for ax, model in zip(axes, MODEL_ORDER):
        sub = df[df["model_display"] == model]
        for cond in CONDITION_ORDER:
            line = sub[sub["condition"] == cond].sort_values("bin_idx")
            if line.empty:
                continue
            ax.plot(
                line["bin_idx"],
                line[metric_key],
                marker="o",
                markersize=4.7,
                linewidth=1.9,
                color=CONDITION_COLORS[cond],
                label=condition_label(cond),
            )
        ax.set_title(model, pad=8)
        ax.set_xticks(range(len(BIN_CUTOFFS)))
        ax.set_xticklabels([x[0] for x in BIN_CUTOFFS])
        ax.grid(axis="y", color="#dddddd", linewidth=0.8)

    axes[0].set_ylabel(info["label"])
    axes[2].set_ylabel(info["label"])
    axes[2].set_xlabel("Cumulative time cutoff, minutes")
    axes[3].set_xlabel("Cumulative time cutoff, minutes")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="center left", ncol=1, frameon=False, bbox_to_anchor=(0.84, 0.50))
    fig.suptitle(title_for(metric_key), y=0.965)
    fig.text(0.08, 0.045, info["direction"], ha="left", va="top", fontsize=10.5, color="#444444")

    save_figure(fig, OUT / f"canonical_n10_{info['file_slug']}_cumulative_trajectory_by_model.png")


def write_readme() -> None:
    readme = """# Step 2 cumulative canonical 10-agent trajectories

Each plot shows one cumulative metric at the matched 10-agent scale. The four panels are the four canonical models. The lines are the six seed conditions.

The x-axis labels are time cutoffs. For example, the point labeled `15-30` uses all posts from 0 to 30 minutes. The point labeled `45-60` uses all posts from 0 to 60 minutes.

Files:

- `canonical_n10_gzip_cumulative_trajectory_by_model.png`
- `canonical_n10_distinct5_cumulative_trajectory_by_model.png`
- `canonical_n10_llm_collapse_cumulative_trajectory_by_model.png`

Each model panel uses its own y-axis scale so within-model movement is easier to see.

How to read collapse direction:

- Gzip down means all text so far became easier to compress and more repetitive.
- Distinct-5 down means the feed so far has fewer unique 5-grams.
- LLM collapse index up means the feed so far is judged more repetitive, rigid, conformist, and less novel.

## Gzip

![Gzip](canonical_n10_gzip_cumulative_trajectory_by_model.png)

## Distinct-5

![Distinct-5](canonical_n10_distinct5_cumulative_trajectory_by_model.png)

## LLM collapse

![LLM collapse](canonical_n10_llm_collapse_cumulative_trajectory_by_model.png)
"""
    (OUT / "README.md").write_text(readme)


def main() -> None:
    setup_style()
    OUT.mkdir(parents=True, exist_ok=True)
    df = build_cumulative_table()
    df.to_csv(OUT / "canonical_n10_cumulative_metrics.csv", index=False, lineterminator="\n")
    for old in OUT.glob("*.png"):
        old.unlink()
    for old in OUT.glob("*.pdf"):
        old.unlink()
    for metric_key in ["gzip", "distinct5", "llm_collapse"]:
        plot_metric(df, metric_key)
    write_readme()
    print(f"wrote Step 2 cumulative trajectory plots to {OUT}")


if __name__ == "__main__":
    main()
