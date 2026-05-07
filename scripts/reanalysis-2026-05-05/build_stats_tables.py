#!/usr/bin/env python3
"""Build run-level statistical tables for paper figures."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from common import (
    CONDITION_LABELS,
    CONDITION_ORDER,
    METRICS,
    MODEL_ORDER,
    N10_MODEL_ORDER,
    PRIMARY_METRICS,
    STATS_ROOT,
    collapse_score,
    fmt_signed,
    load_run_deltas,
    setup_style,
    sign_test_p,
    summarize_values,
    write_json,
)

SEEDED = [c for c in CONDITION_ORDER if c != "mag0"]


def canonical_model_direction_tests(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    can = df[(df["internal_family_label"] == "single_model_final") & (df["scheme"] == "fixed_15m")].copy()
    for metric_key in PRIMARY_METRICS:
        spec = METRICS[metric_key]
        can[f"collapse_{metric_key}"] = collapse_score(can, spec)
        for model in MODEL_ORDER:
            sub = can[can["model_display"] == model]
            vals_raw = pd.to_numeric(sub[spec.col], errors="coerce").dropna()
            vals_c = sub[f"collapse_{metric_key}"].dropna()
            s = summarize_values(vals_c)
            rows.append({
                "metric": metric_key,
                "metric_label": spec.label,
                "model_display": model,
                "n_runs": int(len(vals_c)),
                "median_raw_delta": float(vals_raw.median()) if len(vals_raw) else np.nan,
                "mean_raw_delta": float(vals_raw.mean()) if len(vals_raw) else np.nan,
                "median_collapse_score": s["median"],
                "mean_collapse_score": s["mean"],
                "collapse_direction_count": s["n_positive"],
                "opposite_direction_count": s["n_negative"],
                "sign_test_p": s["sign_p"],
            })
    return pd.DataFrame(rows)


def scale_paired_tests(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    can = df[(df["internal_family_label"] == "single_model_final") & (df["scheme"] == "fixed_15m")].copy()
    for metric_key in PRIMARY_METRICS:
        spec = METRICS[metric_key]
        for model in ["GPT-5", "Gemini Flash Lite"]:
            sub = can[can["model_display"] == model]
            for high in [20, 30]:
                vals_raw = []
                vals_c = []
                for cond in CONDITION_ORDER:
                    low_cell = sub[(sub["condition"] == cond) & (sub["n_agents"] == 10)]
                    high_cell = sub[(sub["condition"] == cond) & (sub["n_agents"] == high)]
                    if low_cell.empty or high_cell.empty:
                        continue
                    raw = float(high_cell.iloc[0][spec.col]) - float(low_cell.iloc[0][spec.col])
                    vals_raw.append(raw)
                    vals_c.append(raw * spec.direction)
                s = summarize_values(vals_c)
                rows.append({
                    "metric": metric_key,
                    "metric_label": spec.label,
                    "model_display": model,
                    "comparison": f"n{high}_minus_n10",
                    "n_condition_pairs": int(len(vals_c)),
                    "median_raw_difference": float(np.median(vals_raw)) if vals_raw else np.nan,
                    "median_collapse_difference": s["median"],
                    "n_high_more_collapse": s["n_positive"],
                    "n_high_less_collapse": s["n_negative"],
                    "sign_test_p": s["sign_p"],
                })
    return pd.DataFrame(rows)


def condition_vs_empty_tests(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    can = df[(df["internal_family_label"] == "single_model_final") & (df["scheme"] == "fixed_15m")].copy()
    for metric_key in PRIMARY_METRICS:
        spec = METRICS[metric_key]
        for cond in SEEDED:
            vals_raw = []
            vals_c = []
            for (model, n_agents), block in can.groupby(["model_display", "n_agents"]):
                empty = block[block["condition"] == "mag0"]
                seed = block[block["condition"] == cond]
                if empty.empty or seed.empty:
                    continue
                raw = float(seed.iloc[0][spec.col]) - float(empty.iloc[0][spec.col])
                vals_raw.append(raw)
                vals_c.append(raw * spec.direction)
            s = summarize_values(vals_c)
            rows.append({
                "metric": metric_key,
                "metric_label": spec.label,
                "condition": cond,
                "condition_label": CONDITION_LABELS[cond],
                "n_matched_blocks": int(len(vals_c)),
                "median_raw_difference_vs_empty": float(np.median(vals_raw)) if vals_raw else np.nan,
                "median_collapse_difference_vs_empty": s["median"],
                "n_seed_more_collapse_than_empty": s["n_positive"],
                "n_seed_less_collapse_than_empty": s["n_negative"],
                "sign_test_p": s["sign_p"],
            })
    return pd.DataFrame(rows)


def n10_model_condition_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sub = df[(df["scheme"] == "fixed_15m") & (df["n_agents"] == 10) & (df["internal_family_label"].isin(["single_model_final", "base_model_as_tool", "mixed_model_roster"]))].copy()
    for metric_key in PRIMARY_METRICS:
        spec = METRICS[metric_key]
        for model in N10_MODEL_ORDER:
            for cond in CONDITION_ORDER:
                cell = sub[(sub["model_display"] == model) & (sub["condition"] == cond)]
                if cell.empty:
                    continue
                raw = float(pd.to_numeric(cell[spec.col], errors="coerce").mean())
                rows.append({
                    "metric": metric_key,
                    "metric_label": spec.label,
                    "model_display": model,
                    "condition": cond,
                    "condition_label": CONDITION_LABELS[cond],
                    "n_runs": int(cell["run_uid"].nunique()),
                    "raw_delta": raw,
                    "collapse_score": raw * spec.direction,
                    "family": str(cell.iloc[0]["internal_family_label"]),
                })
    return pd.DataFrame(rows)


def mixed_vs_homogeneous_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sub = df[(df["scheme"] == "fixed_15m") & (df["n_agents"] == 10)].copy()
    hom = sub[sub["internal_family_label"] == "single_model_final"]
    mixed = sub[sub["internal_family_label"] == "mixed_model_roster"]
    for metric_key in PRIMARY_METRICS:
        spec = METRICS[metric_key]
        for cond in CONDITION_ORDER:
            h = hom[hom["condition"] == cond]
            m = mixed[mixed["condition"] == cond]
            if h.empty or m.empty:
                continue
            h_scores = pd.to_numeric(h[spec.col], errors="coerce") * spec.direction
            m_score = float(m.iloc[0][spec.col]) * spec.direction
            rows.append({
                "metric": metric_key,
                "metric_label": spec.label,
                "condition": cond,
                "condition_label": CONDITION_LABELS[cond],
                "homogeneous_n10_median_collapse_score": float(h_scores.median()),
                "mixed_collapse_score": m_score,
                "mixed_minus_homogeneous_median": float(m_score - h_scores.median()),
                "mixed_more_collapse_than_all_homogeneous": bool(m_score > h_scores.max()),
                "mixed_less_collapse_than_all_homogeneous": bool(m_score < h_scores.min()),
                "n_homogeneous_runs": int(h["run_uid"].nunique()),
            })
    return pd.DataFrame(rows)


def obsession_summary(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sub = df[df["scheme"] == "normalized_quartile"].copy()
    base = sub[(sub["internal_family_label"] == "single_model_final") & (sub["model_display"] == "GPT-5") & (sub["n_agents"] == 10)]
    obs_gpt = sub[(sub["internal_family_label"] == "obsession_prompting") & (sub["model_display"] == "GPT-5")]
    obs_gem = sub[(sub["internal_family_label"] == "obsession_prompting") & (sub["model_display"] == "Gemini Flash Lite")]
    for metric_key in PRIMARY_METRICS:
        spec = METRICS[metric_key]
        for cond in CONDITION_ORDER:
            b = base[base["condition"] == cond]
            o = obs_gpt[obs_gpt["condition"] == cond]
            if b.empty or o.empty:
                continue
            b_score = float(b.iloc[0][spec.col]) * spec.direction
            o_scores = pd.to_numeric(o[spec.col], errors="coerce") * spec.direction
            rows.append({
                "metric": metric_key,
                "metric_label": spec.label,
                "condition": cond,
                "condition_label": CONDITION_LABELS[cond],
                "baseline_gpt5_n10_collapse_score": b_score,
                "obsession_gpt5_median_collapse_score": float(o_scores.median()),
                "obsession_minus_baseline": float(o_scores.median() - b_score),
                "n_obsession_gpt5_runs": int(o["run_uid"].nunique()),
            })
        gem = obs_gem[obs_gem["condition"] == "mag25"]
        if not gem.empty:
            rows.append({
                "metric": metric_key,
                "metric_label": spec.label,
                "condition": "mag25",
                "condition_label": "25 conspiracy seeds",
                "baseline_gpt5_n10_collapse_score": np.nan,
                "obsession_gpt5_median_collapse_score": np.nan,
                "obsession_minus_baseline": np.nan,
                "n_obsession_gpt5_runs": 0,
                "gemini_obsession_single_case_collapse_score": float(gem.iloc[0][spec.col]) * spec.direction,
            })
    return pd.DataFrame(rows)


def write_markdown_summary(tables: dict[str, pd.DataFrame]) -> None:
    can = tables["canonical_model_direction_tests"]
    hhi = can[can["metric"] == "hhi_norm"]
    vendi = can[can["metric"] == "vendi"]
    llm = can[can["metric"] == "llm_collapse"]
    lines = [
        "# Statistical table summary",
        "",
        "All signs are run-level. Positive collapse score means more collapse in the metric-specific direction.",
        "",
        "## Canonical model direction tests",
        "",
        "| Model | Vendi collapse count | LLM collapse count | HHI concentration count |",
        "|---|---:|---:|---:|",
    ]
    for model in MODEL_ORDER:
        def cell(table):
            row = table[table["model_display"] == model].iloc[0]
            return f"{int(row['collapse_direction_count'])}/{int(row['n_runs'])}"
        lines.append(f"| {model} | {cell(vendi)} | {cell(llm)} | {cell(hhi)} |")
    scale = tables["scale_paired_tests_gpt5_gemini"]
    lines += ["", "## Scale, n30 minus n10", "", "| Metric | Model | Median collapse difference | Sign count |", "|---|---|---:|---:|"]
    for metric in ["gzip", "vendi", "llm_collapse", "hhi_norm"]:
        for model in ["GPT-5", "Gemini Flash Lite"]:
            row = scale[(scale["metric"] == metric) & (scale["model_display"] == model) & (scale["comparison"] == "n30_minus_n10")]
            if row.empty:
                continue
            row = row.iloc[0]
            lines.append(f"| {METRICS[metric].short_label} | {model} | {fmt_signed(row['median_collapse_difference'], 3)} | {int(row['n_high_more_collapse'])}/{int(row['n_condition_pairs'])} |")
    (STATS_ROOT / "summary_for_findings.md").write_text("\n".join(lines))


def main() -> None:
    setup_style()
    STATS_ROOT.mkdir(parents=True, exist_ok=True)
    df = load_run_deltas(None)
    tables = {
        "canonical_model_direction_tests": canonical_model_direction_tests(df),
        "scale_paired_tests_gpt5_gemini": scale_paired_tests(df),
        "condition_vs_empty_matched_tests": condition_vs_empty_tests(df),
        "n10_model_condition_summary": n10_model_condition_summary(df),
        "mixed_vs_homogeneous_matched_summary": mixed_vs_homogeneous_summary(df),
        "obsession_matched_condition_summary": obsession_summary(df),
    }
    for name, table in tables.items():
        table.to_csv(STATS_ROOT / f"{name}.csv", index=False, lineterminator="\n")
    write_markdown_summary(tables)
    write_json(STATS_ROOT / "stats_manifest.json", {name: int(len(table)) for name, table in tables.items()})
    print(f"wrote stats tables to {STATS_ROOT}")


if __name__ == "__main__":
    main()
