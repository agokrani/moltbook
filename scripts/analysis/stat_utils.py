#!/usr/bin/env python3
"""Statistical utilities for entropy-collapse analysis.

Consolidates bootstrap CIs, permutation tests, effect sizes, and
agreement measures used across the multiscale analysis pipeline.
"""

from __future__ import annotations

import random
from typing import Sequence

import numpy as np
from scipy import stats as scipy_stats


def bootstrap_ci(
    values: Sequence[float],
    n_boot: int = 10000,
    ci: float = 0.95,
    seed: int = 42,
) -> dict:
    """Bootstrap confidence interval for the mean.

    Returns {"mean": float, "ci_lo": float, "ci_hi": float, "n": int}.
    """
    values = list(values)
    n = len(values)
    if n < 2:
        v = values[0] if values else 0.0
        return {"mean": v, "ci_lo": v, "ci_hi": v, "n": n}
    rng = random.Random(seed)
    means = []
    for _ in range(n_boot):
        sample = rng.choices(values, k=n)
        means.append(sum(sample) / n)
    means.sort()
    lo = means[int((1 - ci) / 2 * n_boot)]
    hi = means[int((1 + ci) / 2 * n_boot)]
    return {
        "mean": sum(values) / n,
        "ci_lo": lo,
        "ci_hi": hi,
        "n": n,
    }


def permutation_test_means(
    a: Sequence[float],
    b: Sequence[float],
    n_perms: int = 5000,
    seed: int = 42,
) -> dict:
    """Two-sample permutation test on difference of means.

    Returns {"observed_diff": float, "p_value": float, "n_a": int, "n_b": int}.
    """
    a = list(a)
    b = list(b)
    if not a or not b:
        return {"observed_diff": 0.0, "p_value": 1.0, "n_a": len(a), "n_b": len(b)}
    observed = sum(a) / len(a) - sum(b) / len(b)
    combined = a + b
    n_a = len(a)
    rng = random.Random(seed)
    count = 0
    for _ in range(n_perms):
        rng.shuffle(combined)
        perm_diff = sum(combined[:n_a]) / n_a - sum(combined[n_a:]) / len(b)
        if abs(perm_diff) >= abs(observed):
            count += 1
    return {
        "observed_diff": observed,
        "p_value": (count + 1) / (n_perms + 1),
        "n_a": n_a,
        "n_b": len(b),
    }


def cohens_d(a: Sequence[float], b: Sequence[float]) -> float:
    """Pooled-SD Cohen's d: (mean_a - mean_b) / pooled_std."""
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    n_a, n_b = len(a_arr), len(b_arr)
    if n_a < 2 or n_b < 2:
        return 0.0
    var_a = np.var(a_arr, ddof=1)
    var_b = np.var(b_arr, ddof=1)
    pooled_std = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    if pooled_std == 0:
        return 0.0
    return float((np.mean(a_arr) - np.mean(b_arr)) / pooled_std)


def cohens_kappa(rater_a: Sequence, rater_b: Sequence) -> float:
    """Cohen's kappa for nominal agreement between two raters."""
    if len(rater_a) != len(rater_b) or not rater_a:
        return 0.0
    n = len(rater_a)
    categories = sorted(set(rater_a) | set(rater_b))
    if len(categories) < 2:
        return 1.0

    # Build confusion matrix
    cat_idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    matrix = np.zeros((k, k), dtype=int)
    for a_val, b_val in zip(rater_a, rater_b):
        matrix[cat_idx[a_val], cat_idx[b_val]] += 1

    p_o = np.trace(matrix) / n  # observed agreement
    row_sums = matrix.sum(axis=1)
    col_sums = matrix.sum(axis=0)
    p_e = float(np.sum(row_sums * col_sums)) / (n * n)  # expected agreement

    if p_e >= 1.0:
        return 1.0
    return float((p_o - p_e) / (1 - p_e))


def spearman_trend(x: Sequence[float], y: Sequence[float]) -> dict:
    """Spearman rank correlation.

    Returns {"rho": float, "p_value": float, "n": int}.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if len(x_arr) < 3:
        return {"rho": 0.0, "p_value": 1.0, "n": len(x_arr)}
    rho, p = scipy_stats.spearmanr(x_arr, y_arr)
    return {"rho": float(rho), "p_value": float(p), "n": len(x_arr)}


def chi_square_proportions(counts_a: Sequence[int], counts_b: Sequence[int]) -> dict:
    """Chi-square test comparing two distributions of counts.

    Returns {"chi2": float, "p_value": float, "dof": int}.
    """
    a_arr = np.asarray(counts_a, dtype=float)
    b_arr = np.asarray(counts_b, dtype=float)
    table = np.vstack([a_arr, b_arr])
    # Remove zero columns to avoid warnings
    nonzero = table.sum(axis=0) > 0
    table = table[:, nonzero]
    if table.shape[1] < 2:
        return {"chi2": 0.0, "p_value": 1.0, "dof": 0}
    chi2, p, dof, _ = scipy_stats.chi2_contingency(table)
    return {"chi2": float(chi2), "p_value": float(p), "dof": int(dof)}


def wilcoxon_signed_rank(a: Sequence[float], b: Sequence[float]) -> dict:
    """Wilcoxon signed-rank test for paired samples.

    Returns {"statistic": float, "p_value": float, "n": int}.
    """
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if len(a_arr) < 6 or len(a_arr) != len(b_arr):
        return {"statistic": 0.0, "p_value": 1.0, "n": len(a_arr)}
    diffs = a_arr - b_arr
    if np.all(diffs == 0):
        return {"statistic": 0.0, "p_value": 1.0, "n": len(a_arr)}
    stat, p = scipy_stats.wilcoxon(a_arr, b_arr)
    return {"statistic": float(stat), "p_value": float(p), "n": len(a_arr)}
