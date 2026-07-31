#!/usr/bin/env python3
"""Prepare and analyze a balanced four-model blinded judge validation."""

from __future__ import annotations

import argparse
import json
import math
import sqlite3
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score


FIELDS = [
    "novelty",
    "semantic_repetition",
    "frame_convergence",
    "consensus_conformity",
    "template_rigidity",
]
EXISTING_MODEL = "google/gemini-3.1-flash-lite-preview"
NEW_MODELS = [
    "openai/gpt-5.5",
    "anthropic/claude-opus-4.7",
]
ALL_MODELS = [EXISTING_MODEL, *NEW_MODELS]
RUBRIC_VERSION = "ayush-blind-all-posts-v1"


def collapse_index(frame: pd.DataFrame) -> pd.Series:
    return (
        frame["semantic_repetition"]
        + frame["frame_convergence"]
        + frame["consensus_conformity"]
        + frame["template_rigidity"]
        + (6 - frame["novelty"])
    ) / 5


def prepare(args: argparse.Namespace) -> None:
    usecols = [
        "row_uid",
        "run_uid",
        "run_id",
        "model_display",
        "condition",
        "n_agents",
        "internal_family_label",
        "minutes_elapsed",
        "is_seed",
        "prompt_sha1",
        *FIELDS,
        "collapse_index",
    ]
    scores = pd.read_csv(args.existing_scores, usecols=usecols, low_memory=False)
    scores = scores[
        (scores["internal_family_label"] == "single_model_final")
        & (scores["n_agents"] == 10)
        & (~scores["is_seed"].astype(bool))
        & (scores["minutes_elapsed"] >= 0)
        & (scores["minutes_elapsed"] <= 60)
    ].copy()
    scores["validation_window"] = np.where(
        scores["minutes_elapsed"] < 15,
        "early",
        np.where(scores["minutes_elapsed"] >= 45, "late", "middle"),
    )
    scores = scores[scores["validation_window"].isin(["early", "late"])]

    context_hashes: dict[str, str] = {}
    with args.contexts.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            context_hashes[str(row["row_uid"])] = str(row["prompt_sha1"])
    scores["context_prompt_sha1"] = scores["row_uid"].astype(str).map(context_hashes)
    scores = scores[scores["prompt_sha1"] == scores["context_prompt_sha1"]].copy()

    selected = []
    for (run_uid, window), group in scores.groupby(["run_uid", "validation_window"]):
        if len(group) < args.posts_per_window:
            raise RuntimeError(f"only {len(group)} posts for {run_uid} {window}")
        seed = args.seed + int(str(run_uid)[:8], 16) + (0 if window == "early" else 1)
        selected.append(group.sample(args.posts_per_window, random_state=seed))
    sample = pd.concat(selected, ignore_index=True).sort_values(
        ["model_display", "condition", "run_uid", "validation_window", "minutes_elapsed"]
    )
    if sample["run_uid"].nunique() != 24 or len(sample) != 24 * 2 * args.posts_per_window:
        raise RuntimeError(
            f"expected 24 runs and {24 * 2 * args.posts_per_window} posts; "
            f"found {sample['run_uid'].nunique()} and {len(sample)}"
        )
    if sample["row_uid"].duplicated().any():
        raise RuntimeError("duplicate row_uid in validation sample")

    args.output_root.mkdir(parents=True, exist_ok=True)
    judge_dir = args.output_root / "ayush_reanalysis/llm_judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    sample.to_csv(args.output_root / "multijudge_sample_metadata.csv", index=False)

    wanted = set(sample["row_uid"].astype(str))
    found = set()
    with args.contexts.open(encoding="utf-8") as source, (
        judge_dir / "blind_contexts.jsonl"
    ).open("w", encoding="utf-8") as destination:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("row_uid") in wanted:
                destination.write(json.dumps(row, ensure_ascii=False) + "\n")
                found.add(row["row_uid"])
    missing = wanted - found
    if missing:
        raise RuntimeError(f"missing {len(missing)} selected contexts")
    if not (sample["prompt_sha1"] == sample["context_prompt_sha1"]).all():
        raise RuntimeError("selected prompts do not match the original judge prompt hashes")
    print(
        f"prepared {len(sample)} blinded posts from {sample['run_uid'].nunique()} runs "
        f"at {args.output_root}"
    )


def read_new_judges(cache: Path) -> pd.DataFrame:
    conn = sqlite3.connect(cache)
    rows = []
    query = """
        SELECT row_uid, judge_model, judgment_json
        FROM judgments
        WHERE rubric_version = ?
    """
    for row_uid, model, judgment_json in conn.execute(query, (RUBRIC_VERSION,)):
        if model not in NEW_MODELS:
            continue
        scores = json.loads(judgment_json)
        rows.append({"row_uid": row_uid, "judge_model": model, **scores})
    conn.close()
    return pd.DataFrame(rows)


def sign_test_p(values: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce").dropna()
    values = values[values != 0]
    n = len(values)
    if n == 0:
        return math.nan
    k = min(int((values > 0).sum()), int((values < 0).sum()))
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / (2**n))


def bootstrap_mean_ci(values: pd.Series, seed: int = 42) -> tuple[float, float]:
    array = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.choice(array, size=(20000, len(array)), replace=True).mean(axis=1)
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def markdown_table(frame: pd.DataFrame) -> str:
    def format_value(value: object) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, (float, np.floating)):
            return f"{float(value):.3f}"
        return str(value)

    columns = list(frame.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join(format_value(row[column]) for column in columns) + " |")
    return "\n".join(lines)


def short_model(model: str) -> str:
    return {
        EXISTING_MODEL: "Gemini 3.1 Flash Lite",
        "openai/gpt-5.5": "GPT-5.5",
        "anthropic/claude-opus-4.7": "Claude Opus 4.7",
    }[model]


def write_figure(pairwise: pd.DataFrame, summary: pd.DataFrame, output_prefix: Path) -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
        }
    )
    agreement_rows = [
        [
            f"{short_model(row.judge_a)} / {short_model(row.judge_b)}",
            f"{row.mean_component_quadratic_kappa:.2f}",
            f"{row.spearman_collapse_index:.2f}",
        ]
        for row in pairwise.itertuples(index=False)
    ]
    direction_rows = [
        [
            short_model(row.judge_model),
            f"{row.mean_delta:+.2f} [{row.bootstrap_ci_low:+.2f}, {row.bootstrap_ci_high:+.2f}]",
        ]
        for row in summary.itertuples(index=False)
    ]
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 6.6), gridspec_kw={"height_ratios": [1.45, 1]})
    for ax in axes:
        ax.axis("off")
    axes[0].set_title("Pairwise agreement on the same 240 blinded posts", loc="left", pad=10)
    table_a = axes[0].table(
        cellText=agreement_rows,
        colLabels=["Judge pair", "Mean weighted κ", "Index Spearman ρ"],
        cellLoc="center",
        colLoc="center",
        colWidths=[0.48, 0.25, 0.27],
        bbox=[0, 0, 1, 0.92],
    )
    axes[1].set_title("Early-to-late collapse-index change", loc="left", pad=10)
    table_b = axes[1].table(
        cellText=direction_rows,
        colLabels=["Judge", "Mean change [run-bootstrap 95% CI]"],
        cellLoc="center",
        colLoc="center",
        colWidths=[0.45, 0.55],
        bbox=[0, 0.08, 1, 0.82],
    )
    for table in [table_a, table_b]:
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        for (row, _), cell in table.get_celld().items():
            cell.set_edgecolor("#777777")
            cell.set_linewidth(0.6)
            if row == 0:
                cell.set_facecolor("#eeeeee")
                cell.set_text_props(weight="bold")
            else:
                cell.set_facecolor("white")
    fig.text(
        0.5,
        0.015,
        "Quadratic weights are used for the ordinal 1-5 component scores. Positive change means more collapse.",
        ha="center",
        fontsize=8.5,
    )
    fig.subplots_adjust(top=0.95, bottom=0.08, left=0.03, right=0.97, hspace=0.20)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_prefix.with_suffix(".png"), bbox_inches="tight", facecolor="white")
    fig.savefig(output_prefix.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
    plt.close(fig)


def analyze(args: argparse.Namespace) -> None:
    sample = pd.read_csv(args.output_root / "multijudge_sample_metadata.csv")
    existing = sample[["row_uid", *FIELDS, "collapse_index"]].copy()
    existing["judge_model"] = EXISTING_MODEL
    new = read_new_judges(args.output_root / "ayush_reanalysis/llm_judge/judge_cache.sqlite")
    new = new[new["row_uid"].isin(set(sample["row_uid"].astype(str)))].copy()
    expected = len(sample) * len(NEW_MODELS)
    if len(new) != expected:
        counts = new.groupby("judge_model")["row_uid"].nunique().to_dict() if len(new) else {}
        raise RuntimeError(f"new judge cache incomplete: {len(new)}/{expected}; {counts}")
    for field in FIELDS:
        new[field] = pd.to_numeric(new[field], errors="raise").astype(int)
    new["collapse_index"] = collapse_index(new)
    long = pd.concat([existing, new[["row_uid", "judge_model", *FIELDS, "collapse_index"]]])
    long = long.merge(
        sample[
            [
                "row_uid",
                "run_uid",
                "run_id",
                "model_display",
                "condition",
                "validation_window",
                "minutes_elapsed",
            ]
        ],
        on="row_uid",
        how="left",
        validate="many_to_one",
    )
    long.to_csv(args.output_root / "multijudge_post_scores.csv", index=False)

    pair_rows = []
    for model_a, model_b in combinations(ALL_MODELS, 2):
        a = long[long["judge_model"] == model_a].set_index("row_uid")
        b = long[long["judge_model"] == model_b].set_index("row_uid")
        common = a.index.intersection(b.index)
        if len(common) != len(sample):
            raise RuntimeError(f"pair {model_a}, {model_b} has only {len(common)} common posts")
        row = {"judge_a": model_a, "judge_b": model_b, "n_posts": len(common)}
        kappas = []
        for field in FIELDS:
            value = cohen_kappa_score(a.loc[common, field], b.loc[common, field], weights="quadratic")
            row[f"quadratic_kappa_{field}"] = float(value)
            kappas.append(float(value))
        row["mean_component_quadratic_kappa"] = float(np.mean(kappas))
        row["spearman_collapse_index"] = float(
            spearmanr(a.loc[common, "collapse_index"], b.loc[common, "collapse_index"]).statistic
        )
        row["mean_absolute_collapse_difference"] = float(
            np.mean(np.abs(a.loc[common, "collapse_index"] - b.loc[common, "collapse_index"]))
        )
        pair_rows.append(row)
    pairwise = pd.DataFrame(pair_rows)
    pairwise.to_csv(args.output_root / "multijudge_pairwise_agreement.csv", index=False)

    run_window = (
        long.groupby(
            ["judge_model", "run_uid", "run_id", "model_display", "condition", "validation_window"],
            as_index=False,
        )["collapse_index"]
        .mean()
        .pivot(
            index=["judge_model", "run_uid", "run_id", "model_display", "condition"],
            columns="validation_window",
            values="collapse_index",
        )
        .reset_index()
    )
    run_window["delta_late_minus_early"] = run_window["late"] - run_window["early"]
    run_window.to_csv(args.output_root / "multijudge_run_deltas.csv", index=False)
    summary = (
        run_window.groupby("judge_model")["delta_late_minus_early"]
        .agg(n_runs="size", mean_delta="mean", median_delta="median", positive_runs=lambda x: int((x > 0).sum()))
        .reset_index()
    )
    summary["two_sided_sign_p"] = summary["judge_model"].map(
        lambda model: sign_test_p(
            run_window.loc[run_window["judge_model"] == model, "delta_late_minus_early"]
        )
    )
    intervals = {
        model: bootstrap_mean_ci(
            run_window.loc[run_window["judge_model"] == model, "delta_late_minus_early"]
        )
        for model in ALL_MODELS
    }
    summary["bootstrap_ci_low"] = summary["judge_model"].map(lambda model: intervals[model][0])
    summary["bootstrap_ci_high"] = summary["judge_model"].map(lambda model: intervals[model][1])
    summary["judge_order"] = summary["judge_model"].map({model: index for index, model in enumerate(ALL_MODELS)})
    summary = summary.sort_values("judge_order").drop(columns="judge_order").reset_index(drop=True)
    summary.to_csv(args.output_root / "multijudge_direction_summary.csv", index=False)

    if args.export_dir:
        args.export_dir.mkdir(parents=True, exist_ok=True)
        sample.to_csv(args.export_dir / "multijudge_sample_metadata.csv", index=False)
        long.to_csv(args.export_dir / "multijudge_post_scores.csv", index=False)
        pairwise.to_csv(args.export_dir / "multijudge_pairwise_agreement.csv", index=False)
        summary.to_csv(args.export_dir / "multijudge_direction_summary.csv", index=False)
    if args.figure_output:
        write_figure(pairwise, summary, args.figure_output)

    lines = [
        "# Three-judge blinded validation",
        "",
        f"Sample: {len(sample)} posts, balanced across 24 runs with five posts from 0-15 minutes and five from 45-60 minutes per run.",
        "",
        "## Pairwise agreement",
        "",
        markdown_table(pairwise),
        "",
        "## Run-level direction",
        "",
        markdown_table(summary),
        "",
    ]
    (args.output_root / "MULTIJUDGE_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(pairwise.to_string(index=False))
    print(summary.to_string(index=False))
    print(f"wrote {args.output_root / 'MULTIJUDGE_REPORT.md'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ["prepare", "analyze"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("--output-root", type=Path, required=True)
        sub.add_argument("--existing-scores", type=Path)
        sub.add_argument("--contexts", type=Path)
        sub.add_argument("--posts-per-window", type=int, default=5)
        sub.add_argument("--seed", type=int, default=42)
        sub.add_argument("--export-dir", type=Path)
        sub.add_argument("--figure-output", type=Path)
    args = parser.parse_args()
    if args.command == "prepare":
        if args.existing_scores is None or args.contexts is None:
            parser.error("prepare requires --existing-scores and --contexts")
        prepare(args)
    else:
        analyze(args)


if __name__ == "__main__":
    main()
