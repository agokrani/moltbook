"""
Power Analysis for Ranking Effect Pilot Study
Moltbook / CivicLens Experiment

Pilot data from ranking-effect study:
  - 3 treatment groups: nudge_up, control, nudge_down
  - Outcome variables: adjusted_score, final_score, comment_count
  - Primary outcome: adjusted_score (organic votes, excluding the nudge vote)

All random seeds set for reproducibility.
"""

import sys
import numpy as np
import scipy
import scipy.stats as stats
import pandas as pd
from statsmodels.stats.power import FTestAnovaPower
from itertools import product

# ─── Reproducibility ─────────────────────────────────────────────────────────
np.random.seed(42)

print(f"Python:      {sys.version.split()[0]}")
print(f"NumPy:       {np.__version__}")
print(f"SciPy:       {scipy.__version__}")
import statsmodels
print(f"Statsmodels: {statsmodels.__version__}")
print(f"Pandas:      {pd.__version__}")
print()

# ─── Raw Pilot Data ───────────────────────────────────────────────────────────
data = {
    "adjusted_score": {
        "nudge_up":   np.array([2, 2, 1, 1, 1, 2, 1, 2, 2, 2, 2, 2, 1], dtype=float),
        "control":    np.array([0, 0, 1, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1], dtype=float),
        "nudge_down": np.array([0, 1, 1, 1, 0, 2, 2, 1, 2, 2, 1, 2],    dtype=float),
    },
    "final_score": {
        "nudge_up":   np.array([3, 3, 2, 2, 2, 2, 2, 3, 3, 3, 3, 1, 1], dtype=float),
        "control":    np.array([0, 0, 1, 2, 1, 2, 2, 2, 1, 2, 2, 2, 1], dtype=float),
        "nudge_down": np.array([-1, 0, 0, 0, -1, 1, 2, 0, 2, 1, 1, 2],  dtype=float),
    },
    "comment_count": {
        "nudge_up":   np.array([12, 5, 9, 9, 4, 8, 9, 9, 8, 8, 9, 8, 8], dtype=float),
        "control":    np.array([0, 1, 3, 8, 10, 8, 10, 8, 9, 8, 9, 8, 7], dtype=float),
        "nudge_down": np.array([0, 3, 11, 10, 11, 8, 10, 10, 8, 9, 9, 8], dtype=float),
    },
}

# ─── Helper Functions ─────────────────────────────────────────────────────────

def cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """
    Pooled-SD Cohen's d: (mean_a - mean_b) / pooled_std.
    Uses n-1 (sample) variances.
    """
    n_a, n_b = len(a), len(b)
    var_a = np.var(a, ddof=1)
    var_b = np.var(b, ddof=1)
    pooled_std = np.sqrt(((n_a - 1) * var_a + (n_b - 1) * var_b) / (n_a + n_b - 2))
    if pooled_std == 0:
        return 0.0
    return (np.mean(a) - np.mean(b)) / pooled_std


def cohens_f_anova(groups: list[np.ndarray]) -> float:
    """
    Cohen's f from one-way ANOVA:
      eta^2 = SS_between / SS_total
      f     = sqrt(eta^2 / (1 - eta^2))
    """
    all_values = np.concatenate(groups)
    grand_mean = np.mean(all_values)
    ss_between = sum(len(g) * (np.mean(g) - grand_mean) ** 2 for g in groups)
    ss_total = np.sum((all_values - grand_mean) ** 2)
    if ss_total == 0:
        return 0.0
    eta_sq = ss_between / ss_total
    if eta_sq >= 1.0:
        return float("inf")
    return float(np.sqrt(eta_sq / (1 - eta_sq)))


def assumption_tests(groups: dict[str, np.ndarray]) -> dict:
    """Shapiro-Wilk normality + Levene homogeneity + one-way ANOVA F."""
    vals = list(groups.values())
    shapiro = {name: stats.shapiro(g) for name, g in groups.items()}
    levene_stat, levene_p = stats.levene(*vals)
    f_stat, anova_p = stats.f_oneway(*vals)
    kruskal_stat, kruskal_p = stats.kruskal(*vals)
    return {
        "shapiro": shapiro,
        "levene":  {"stat": levene_stat, "p": levene_p},
        "anova":   {"F": f_stat, "p": anova_p},
        "kruskal": {"H": kruskal_stat, "p": kruskal_p},
    }


def power_for_n(f: float, n_per_group: int, k_groups: int = 3, alpha: float = 0.05) -> float:
    """Exact power via statsmodels FTestAnovaPower."""
    analysis = FTestAnovaPower()
    return analysis.power(
        effect_size=f,
        nobs=n_per_group,
        alpha=alpha,
        k_groups=k_groups,
    )


def n_for_power(f: float, power: float, k_groups: int = 3, alpha: float = 0.05) -> int:
    """Minimum n per group for target power."""
    analysis = FTestAnovaPower()
    n = analysis.solve_power(
        effect_size=f,
        power=power,
        alpha=alpha,
        k_groups=k_groups,
    )
    return int(np.ceil(n))


# ─── Section 1: Effect Sizes ─────────────────────────────────────────────────
print("=" * 70)
print("SECTION 1: EFFECT SIZES FROM PILOT DATA")
print("=" * 70)

effect_sizes = {}

for outcome in ["adjusted_score", "final_score", "comment_count"]:
    g = data[outcome]
    up, ctrl, dn = g["nudge_up"], g["control"], g["nudge_down"]

    d_up_ctrl  = cohens_d(up,   ctrl)
    d_dn_ctrl  = cohens_d(dn,   ctrl)
    d_up_dn    = cohens_d(up,   dn)
    f_anova    = cohens_f_anova([up, ctrl, dn])
    assump     = assumption_tests(g)

    effect_sizes[outcome] = {
        "d_up_vs_ctrl":  d_up_ctrl,
        "d_dn_vs_ctrl":  d_dn_ctrl,
        "d_up_vs_dn":    d_up_dn,
        "f_anova":       f_anova,
        "assumptions":   assump,
    }

    print(f"\nOutcome: {outcome}")
    print(f"  n per group: up={len(up)}, ctrl={len(ctrl)}, dn={len(dn)}")
    print(f"  Means:       up={np.mean(up):.3f}, ctrl={np.mean(ctrl):.3f}, dn={np.mean(dn):.3f}")
    print(f"  SDs:         up={np.std(up, ddof=1):.3f}, ctrl={np.std(ctrl, ddof=1):.3f}, dn={np.std(dn, ddof=1):.3f}")
    print(f"  Cohen's d  (nudge_up vs control):   {d_up_ctrl:+.4f}")
    print(f"  Cohen's d  (nudge_down vs control): {d_dn_ctrl:+.4f}")
    print(f"  Cohen's d  (nudge_up vs nudge_down):{d_up_dn:+.4f}")
    print(f"  Cohen's f  (one-way ANOVA, 3 grps): {f_anova:.4f}")
    print(f"  Shapiro-Wilk p-values: up={assump['shapiro']['nudge_up'].pvalue:.4f}, "
          f"ctrl={assump['shapiro']['control'].pvalue:.4f}, "
          f"dn={assump['shapiro']['nudge_down'].pvalue:.4f}")
    print(f"  Levene test:  F={assump['levene']['stat']:.4f}, p={assump['levene']['p']:.4f}")
    print(f"  One-way ANOVA: F={assump['anova']['F']:.4f}, p={assump['anova']['p']:.4f}")
    print(f"  Kruskal-Wallis: H={assump['kruskal']['H']:.4f}, p={assump['kruskal']['p']:.4f}")

# ─── Section 2: Power Analysis (primary = adjusted_score) ────────────────────
print("\n" + "=" * 70)
print("SECTION 2: POWER ANALYSIS — PRIMARY OUTCOME (adjusted_score)")
print("=" * 70)

f_obs  = effect_sizes["adjusted_score"]["f_anova"]
f_cons = 0.80 * f_obs   # Conservative: 80% of observed

print(f"\nObserved Cohen's f (adjusted_score): {f_obs:.4f}")
print(f"Conservative Cohen's f (80% of observed): {f_cons:.4f}")

power_table_rows = []
for label, f_val in [("Observed f", f_obs), ("Conservative f (80%)", f_cons)]:
    for alpha_label, alpha in [("alpha=0.05", 0.05)]:
        for power_target in [0.80, 0.90]:
            n_needed = n_for_power(f_val, power_target, k_groups=3, alpha=alpha)
            power_achieved = power_for_n(f_val, n_needed, k_groups=3, alpha=alpha)
            power_table_rows.append({
                "Effect Size": label,
                "f value": f"{f_val:.4f}",
                "Alpha": alpha,
                "Target Power": power_target,
                "N per Group": n_needed,
                "Total N": n_needed * 3,
                "Achieved Power": f"{power_achieved:.4f}",
            })
            print(f"\n  {label} (f={f_val:.4f}), {alpha_label}, target power={power_target:.2f}:")
            print(f"    N per group needed: {n_needed}")
            print(f"    Total N:            {n_needed * 3}")
            print(f"    Achieved power:     {power_achieved:.4f}")

# ─── Section 3: Runs (k) Needed Given Posts per Treatment ────────────────────
print("\n" + "=" * 70)
print("SECTION 3: NUMBER OF RUNS (k) FOR GIVEN POSTS PER TREATMENT GROUP")
print("=" * 70)

print(f"\nUsing observed Cohen's f = {f_obs:.4f} for adjusted_score")
print("Each 'run' contributes a fixed number of posts per treatment group.")
print("Total N per group after k runs = k * posts_per_group.\n")

run_rows = []
for posts_per_group in [20, 30]:
    for power_target in [0.80, 0.90]:
        n_needed = n_for_power(f_obs, power_target, k_groups=3, alpha=0.05)
        k_needed = int(np.ceil(n_needed / posts_per_group))
        n_actual = k_needed * posts_per_group
        power_actual = power_for_n(f_obs, n_actual, k_groups=3, alpha=0.05)
        run_rows.append({
            "Posts per group per run": posts_per_group,
            "Target Power": power_target,
            "N needed": n_needed,
            "k runs needed": k_needed,
            "N achieved (k*posts)": n_actual,
            "Actual Power": f"{power_actual:.4f}",
        })
        print(f"  posts_per_group={posts_per_group}, target power={power_target:.2f}:")
        print(f"    N per group needed: {n_needed}")
        print(f"    k runs needed:      {k_needed}  (gives N={n_actual} per group)")
        print(f"    Actual power:       {power_actual:.4f}\n")

# ─── Section 4: Sensitivity Table ─────────────────────────────────────────────
print("=" * 70)
print("SECTION 4: SENSITIVITY TABLE — Power by (posts/group, k runs)")
print("=" * 70)
print(f"\nUsing observed Cohen's f = {f_obs:.4f}, alpha=0.05, k_groups=3\n")

posts_grid = [20, 30, 40, 50]
k_grid     = [1, 2, 3, 5, 7]

# Build table: rows=posts_per_group, cols=k
header = f"{'posts/group':>12}" + "".join(f"  k={k:<5}" for k in k_grid)
print(header)
print("-" * len(header))

sensitivity_rows = []
for ppg in posts_grid:
    row_str = f"{ppg:>12}"
    for k in k_grid:
        n = ppg * k
        pw = power_for_n(f_obs, n, k_groups=3, alpha=0.05)
        row_str += f"  {pw:.3f}  "
        sensitivity_rows.append({
            "posts_per_group": ppg,
            "k_runs": k,
            "n_per_group": n,
            "power": pw,
        })
    print(row_str)

# Also compute with conservative f
print(f"\nConservative Cohen's f = {f_cons:.4f} (80% of observed), alpha=0.05\n")
print(header)
print("-" * len(header))
for ppg in posts_grid:
    row_str = f"{ppg:>12}"
    for k in k_grid:
        n = ppg * k
        pw = power_for_n(f_cons, n, k_groups=3, alpha=0.05)
        row_str += f"  {pw:.3f}  "
    print(row_str)

# ─── Section 5: Summary ───────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SECTION 5: SUMMARY")
print("=" * 70)

for outcome in ["adjusted_score", "final_score", "comment_count"]:
    es = effect_sizes[outcome]
    print(f"\n{outcome}:")
    print(f"  d (up vs ctrl)  = {es['d_up_vs_ctrl']:+.4f}  "
          f"d (dn vs ctrl)  = {es['d_dn_vs_ctrl']:+.4f}  "
          f"d (up vs dn)    = {es['d_up_vs_dn']:+.4f}")
    print(f"  Cohen's f (ANOVA, 3 groups) = {es['f_anova']:.4f}")
    pw_pilot = power_for_n(es["f_anova"], 13, k_groups=3, alpha=0.05)
    print(f"  Power at pilot n=13/group:   {pw_pilot:.4f}")

print("\nRecommendation for full study (adjusted_score, primary):")
f_primary = effect_sizes["adjusted_score"]["f_anova"]
n80  = n_for_power(f_primary, 0.80)
n90  = n_for_power(f_primary, 0.90)
nf80 = n_for_power(0.80 * f_primary, 0.80)
nf90 = n_for_power(0.80 * f_primary, 0.90)
print(f"  Observed f={f_primary:.4f}: need {n80}/group (80% power), {n90}/group (90% power)")
print(f"  Conservative f={0.80*f_primary:.4f}: need {nf80}/group (80% power), {nf90}/group (90% power)")

print("\nAll results printed above and will be written to power-analysis.md")
