#!/usr/bin/env python3
"""Rebuild multi-judge agreement and direction summaries from released scores."""

from __future__ import annotations

import argparse
import math
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import cohen_kappa_score


ROOT = Path(__file__).resolve().parents[1]
FIELDS = [
    "novelty",
    "semantic_repetition",
    "frame_convergence",
    "consensus_conformity",
    "template_rigidity",
]
MODELS = [
    "google/gemini-3.1-flash-lite-preview",
    "openai/gpt-5.5",
    "anthropic/claude-opus-4.7",
]


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scores", type=Path, default=ROOT / "results/multijudge_post_scores.csv"
    )
    parser.add_argument(
        "--pairwise-output",
        type=Path,
        default=ROOT / "results/multijudge_pairwise_agreement.csv",
    )
    parser.add_argument(
        "--direction-output",
        type=Path,
        default=ROOT / "results/multijudge_direction_summary.csv",
    )
    args = parser.parse_args()

    scores = pd.read_csv(args.scores)
    if len(scores) != 720 or set(scores["judge_model"]) != set(MODELS):
        raise RuntimeError("expected 720 released score rows from the three fixed judges")

    pair_rows = []
    for model_a, model_b in combinations(MODELS, 2):
        left = scores[scores["judge_model"] == model_a].set_index("row_uid")
        right = scores[scores["judge_model"] == model_b].set_index("row_uid")
        common = left.index.intersection(right.index)
        if len(common) != 240:
            raise RuntimeError(f"judge pair has {len(common)} rather than 240 common posts")
        row = {"judge_a": model_a, "judge_b": model_b, "n_posts": len(common)}
        kappas = []
        for field in FIELDS:
            value = cohen_kappa_score(
                left.loc[common, field], right.loc[common, field], weights="quadratic"
            )
            row[f"quadratic_kappa_{field}"] = float(value)
            kappas.append(float(value))
        row["mean_component_quadratic_kappa"] = float(np.mean(kappas))
        row["spearman_collapse_index"] = float(
            spearmanr(
                left.loc[common, "collapse_index"], right.loc[common, "collapse_index"]
            ).statistic
        )
        row["mean_absolute_collapse_difference"] = float(
            np.mean(
                np.abs(
                    left.loc[common, "collapse_index"]
                    - right.loc[common, "collapse_index"]
                )
            )
        )
        pair_rows.append(row)
    pairwise = pd.DataFrame(pair_rows)

    run_window = (
        scores.groupby(
            [
                "judge_model", "run_uid", "run_id", "model_display", "condition",
                "validation_window",
            ],
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
    summary = (
        run_window.groupby("judge_model")["delta_late_minus_early"]
        .agg(
            n_runs="size",
            mean_delta="mean",
            median_delta="median",
            positive_runs=lambda values: int((values > 0).sum()),
        )
        .reset_index()
    )
    summary["two_sided_sign_p"] = summary["judge_model"].map(
        lambda model: sign_test_p(
            run_window.loc[
                run_window["judge_model"] == model, "delta_late_minus_early"
            ]
        )
    )
    intervals = {
        model: bootstrap_mean_ci(
            run_window.loc[
                run_window["judge_model"] == model, "delta_late_minus_early"
            ]
        )
        for model in MODELS
    }
    summary["bootstrap_ci_low"] = summary["judge_model"].map(
        lambda model: intervals[model][0]
    )
    summary["bootstrap_ci_high"] = summary["judge_model"].map(
        lambda model: intervals[model][1]
    )
    summary["judge_order"] = summary["judge_model"].map(
        {model: index for index, model in enumerate(MODELS)}
    )
    summary = (
        summary.sort_values("judge_order")
        .drop(columns="judge_order")
        .reset_index(drop=True)
    )

    args.pairwise_output.parent.mkdir(parents=True, exist_ok=True)
    args.direction_output.parent.mkdir(parents=True, exist_ok=True)
    pairwise.to_csv(args.pairwise_output, index=False)
    summary.to_csv(args.direction_output, index=False)
    print(f"wrote {args.pairwise_output}")
    print(f"wrote {args.direction_output}")


if __name__ == "__main__":
    main()
