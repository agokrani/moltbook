#!/usr/bin/env python3
"""Generate non-heatmap model-level and condition-level analysis graphs."""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech", "unknown"]
COLLAPSE_COMPONENTS = [
    "weighted_semantic_repetition",
    "weighted_narrative_convergence",
    "weighted_groupthink",
    "weighted_template_rigidity",
]
METRIC_LABELS = {
    "weighted_semantic_repetition": "semantic repetition",
    "weighted_narrative_convergence": "narrative convergence",
    "weighted_groupthink": "groupthink",
    "weighted_template_rigidity": "template rigidity",
    "weighted_novelty": "novelty",
    "weighted_evidence_grounding": "evidence grounding",
}
COLORS = {
    "collapse_index": "#e15759",
    "weighted_semantic_repetition": "#4e79a7",
    "weighted_narrative_convergence": "#f28e2b",
    "weighted_groupthink": "#59a14f",
    "weighted_template_rigidity": "#b07aa1",
    "weighted_novelty": "#76b7b2",
    "weighted_evidence_grounding": "#9c755f",
}


def slugify(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(s)).strip("-") or "unknown"


def weighted_aggregate(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    rows = []
    metric_cols = [c for c in df.columns if c.startswith("weighted_")]
    for key, sub in df.groupby(by, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        w = sub["n_full_nonseed_cell"].astype(float).to_numpy()
        row = {k: v for k, v in zip(by, key)}
        row["n_full_nonseed_posts"] = int(np.nansum(w))
        row["n_judged"] = int(np.nansum(sub["n_judged_cell"].astype(float)))
        for col in metric_cols:
            vals = sub[col].astype(float).to_numpy()
            mask = np.isfinite(vals) & np.isfinite(w) & (w > 0)
            row[col] = float(np.average(vals[mask], weights=w[mask])) if mask.any() else np.nan
        row["collapse_index"] = float(np.nanmean([row[c] for c in COLLAPSE_COMPONENTS]))
        rows.append(row)
    return pd.DataFrame(rows)


def sort_conditions(df: pd.DataFrame) -> pd.DataFrame:
    order = {c: i for i, c in enumerate(CONDITION_ORDER)}
    return df.assign(_cond_order=df["condition"].map(lambda x: order.get(x, 999))).sort_values("_cond_order").drop(columns="_cond_order")


def save_lollipop(df: pd.DataFrame, label_col: str, value_col: str, path: Path, title: str, xlabel: str, color="#e15759", xlim=(1, 5)) -> None:
    d = df.sort_values(value_col).copy()
    fig, ax = plt.subplots(figsize=(10, max(4, 0.38 * len(d))))
    y = np.arange(len(d))
    ax.hlines(y, xlim[0], d[value_col], color="#d0d0d0", lw=2)
    ax.scatter(d[value_col], y, s=70, color=color, zorder=3)
    for yi, (_, r) in enumerate(d.iterrows()):
        ax.text(r[value_col] + 0.035, yi, f"{r[value_col]:.2f}", va="center", fontsize=8)
    ax.set_yticks(y, d[label_col].astype(str))
    ax.set_xlim(*xlim)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_model_condition_facets(model_condition: pd.DataFrame, path: Path) -> None:
    models = model_condition.sort_values("n_full_nonseed_posts", ascending=False)["model_family"].drop_duplicates().tolist()
    ncols = 3
    nrows = int(np.ceil(len(models) / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(15, max(7, 3.3 * nrows)), sharex=True)
    axes = np.asarray(axes).reshape(-1)
    order = [c for c in CONDITION_ORDER if c != "unknown"]
    for ax, model in zip(axes, models):
        sub = model_condition[model_condition["model_family"] == model].copy()
        sub = sort_conditions(sub)
        sub = sub[sub["condition"].isin(order)]
        y = np.arange(len(sub))
        ax.barh(y, sub["collapse_index"], color="#e15759", alpha=0.85)
        ax.set_yticks(y, sub["condition"])
        ax.set_xlim(1, 5)
        ax.set_title(model, fontsize=9)
        ax.grid(axis="x", alpha=0.2)
        for yi, (_, r) in enumerate(sub.iterrows()):
            ax.text(r["collapse_index"] + 0.03, yi, f"{r['collapse_index']:.2f}", va="center", fontsize=7)
    for ax in axes[len(models):]:
        ax.axis("off")
    fig.suptitle("Collapse index by condition, split by generation model", y=0.995)
    fig.supxlabel("Collapse index (1–5)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_group_condition_bars(group_condition: pd.DataFrame, path: Path) -> None:
    groups = group_condition.sort_values("n_full_nonseed_posts", ascending=False)["group"].drop_duplicates().tolist()
    conditions = [c for c in CONDITION_ORDER if c in set(group_condition["condition"])]
    x = np.arange(len(conditions))
    width = 0.12 if len(groups) > 5 else 0.14
    fig, ax = plt.subplots(figsize=(12, 6))
    palette = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f", "#b07aa1", "#edc948"]
    for i, group in enumerate(groups):
        sub = group_condition[group_condition["group"] == group].set_index("condition")
        vals = [sub.loc[c, "collapse_index"] if c in sub.index else np.nan for c in conditions]
        ax.bar(x + (i - (len(groups)-1)/2) * width, vals, width=width, label=group, color=palette[i % len(palette)], alpha=0.9)
    ax.set_xticks(x, conditions)
    ax.set_ylim(1, 5)
    ax.set_ylabel("Collapse index")
    ax.set_title("Group × condition collapse index (bar chart, no heatmap)")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_model_profile(model: str, sub: pd.DataFrame, path: Path) -> None:
    sub = sort_conditions(sub)
    conditions = sub["condition"].tolist()
    x = np.arange(len(conditions))
    fig, ax = plt.subplots(figsize=(10, 5.5))
    ax.bar(x, sub["collapse_index"], color="#e15759", alpha=0.35, label="collapse index")
    for col in COLLAPSE_COMPONENTS:
        ax.plot(x, sub[col], marker="o", lw=2, label=METRIC_LABELS[col], color=COLORS[col])
    ax.set_xticks(x, conditions, rotation=25, ha="right")
    ax.set_ylim(1, 5.05)
    ax.set_ylabel("Score")
    ax.set_title(f"{model}: condition-level collapse profile")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.2)
    for xi, (_, r) in enumerate(sub.iterrows()):
        ax.text(xi, r["collapse_index"] + 0.05, f"{r['collapse_index']:.2f}", ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def save_condition_profile(condition: str, model_sub: pd.DataFrame, group_sub: pd.DataFrame, path: Path) -> None:
    model_sub = model_sub.sort_values("collapse_index")
    group_sub = group_sub.sort_values("collapse_index")
    fig, axes = plt.subplots(1, 2, figsize=(15, max(5, 0.38 * len(model_sub))))
    axes[0].barh(model_sub["model_family"], model_sub["collapse_index"], color="#f28e2b")
    axes[0].set_xlim(1, 5)
    axes[0].set_title(f"{condition}: model families")
    axes[0].set_xlabel("Collapse index")
    axes[0].grid(axis="x", alpha=0.2)
    axes[1].barh(group_sub["group"], group_sub["collapse_index"], color="#4e79a7")
    axes[1].set_xlim(1, 5)
    axes[1].set_title(f"{condition}: archive groups")
    axes[1].set_xlabel("Collapse index")
    axes[1].grid(axis="x", alpha=0.2)
    fig.suptitle(f"Condition-level analysis: {condition}")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def md_table(df: pd.DataFrame, max_rows=30) -> str:
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else f"{x:.3f}")
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in d.columns) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()
    root = Path(args.out_dir)
    final = root / "final_report"
    out = root / "individual_analysis"
    models_dir = out / "models"
    cond_dir = out / "conditions"
    out.mkdir(parents=True, exist_ok=True)
    models_dir.mkdir(parents=True, exist_ok=True)
    cond_dir.mkdir(parents=True, exist_ok=True)

    cells = pd.read_csv(final / "final_cell_weighting_inputs.csv")
    group_summary = pd.read_csv(final / "final_group_summary.csv")
    model_summary = pd.read_csv(final / "final_model_summary.csv")
    index = pd.read_csv(root / "combined_posts_index.csv")

    model_condition = weighted_aggregate(cells, ["model_family", "condition"])
    condition_summary = weighted_aggregate(cells, ["condition"])
    group_condition = weighted_aggregate(cells, ["group", "condition"])
    model_group_condition = weighted_aggregate(cells, ["model_family", "group", "condition"])

    model_condition = sort_conditions(model_condition).sort_values(["model_family", "condition"])
    condition_summary = sort_conditions(condition_summary)
    group_condition = sort_conditions(group_condition).sort_values(["group", "condition"])

    model_condition.to_csv(out / "model_condition_weighted_summary.csv", index=False)
    condition_summary.to_csv(out / "condition_weighted_summary.csv", index=False)
    group_condition.to_csv(out / "group_condition_weighted_summary.csv", index=False)
    model_group_condition.to_csv(out / "model_group_condition_weighted_summary.csv", index=False)

    # Combined non-heatmap figures.
    save_lollipop(model_summary.sort_values("weighted_collapse_index"), "model_family", "weighted_collapse_index", out / "fig_all_models_collapse_lollipop.png", "All generation model families: collapse index", "Cell-weighted collapse index")
    save_lollipop(condition_summary, "condition", "collapse_index", out / "fig_conditions_collapse_lollipop.png", "All conditions: collapse index", "Cell-weighted collapse index")
    save_model_condition_facets(model_condition, out / "fig_model_condition_collapse_facets.png")
    save_group_condition_bars(group_condition, out / "fig_group_condition_collapse_bars.png")

    # Model profile lines/bars: one graph per generation model.
    for model, sub in model_condition.groupby("model_family", dropna=False):
        save_model_profile(model, sub, models_dir / f"model_{slugify(model)}_condition_profile.png")

    # Condition profile graphs: model ranking and group ranking per condition.
    for condition in condition_summary["condition"].tolist():
        msub = model_condition[model_condition["condition"] == condition]
        gsub = group_condition[group_condition["condition"] == condition]
        save_condition_profile(condition, msub, gsub, cond_dir / f"condition_{slugify(condition)}_profiles.png")

    model_counts = index.groupby("model_family").agg(post_rows=("record_id", "count"), runs=("run_path", "nunique")).reset_index().sort_values("post_rows", ascending=False)
    condition_counts = index.groupby("condition").agg(post_rows=("record_id", "count"), runs=("run_path", "nunique")).reset_index()
    condition_counts = sort_conditions(condition_counts)

    report = f"""# Individual Model and Condition Analysis — Non-Heatmap Version\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n## Clarification\n\n- **Embedding model:** one embedding model was used as requested: `qwen/qwen3-embedding-8b`.\n- **Generation/model families analyzed:** all model families present in the targeted archive + full canonical-48 corpus were included. This report splits results by those generation model families.\n- **Judge model:** one LLM judge model was used for scoring (`google/gemini-3.1-flash-lite-preview`), but the sample spans every generation model family, group, condition, scale/time bin, and all global embedding clusters.\n\n## What changed from the earlier heatmaps\n\nThis folder uses lollipop charts, grouped bar charts, and small-multiple profile plots instead of heatmaps.\n\n## Main combined graphs\n\n- `fig_all_models_collapse_lollipop.png` — all generation models, ranked by collapse index.\n- `fig_conditions_collapse_lollipop.png` — all conditions, ranked by collapse index.\n- `fig_model_condition_collapse_facets.png` — separate mini-graph for each model showing condition collapse.\n- `fig_group_condition_collapse_bars.png` — group × condition bars, no heatmap.\n\n## Individual graph folders\n\n- `models/` — one condition-profile graph per generation model.\n- `conditions/` — one model/group ranking graph per condition.\n\n## Generation model families included\n\n{md_table(model_counts, max_rows=20)}\n\n## Condition counts\n\n{md_table(condition_counts, max_rows=20)}\n\n## Ranked model-level collapse\n\n{md_table(model_summary[['model_family','n_posts','n_judged_sample','weighted_collapse_index','weighted_semantic_repetition','weighted_narrative_convergence','weighted_groupthink','weighted_template_rigidity']], max_rows=20)}\n\n## Ranked condition-level collapse\n\n{md_table(condition_summary[['condition','n_full_nonseed_posts','n_judged','collapse_index','weighted_semantic_repetition','weighted_narrative_convergence','weighted_groupthink','weighted_template_rigidity']], max_rows=20)}\n"""
    (out / "INDIVIDUAL_MODEL_CONDITION_ANALYSIS.md").write_text(report)
    print(f"Wrote non-heatmap individual analysis -> {out}")
    print(f"Model graphs: {len(list(models_dir.glob('*.png')))}; condition graphs: {len(list(cond_dir.glob('*.png')))}")


if __name__ == "__main__":
    main()
