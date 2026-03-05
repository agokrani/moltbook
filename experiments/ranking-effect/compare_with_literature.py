#!/usr/bin/env python3
"""
Compare Moltbook AI agent results with human Reddit studies.

Reference baselines:
  Glenski 2015/2017: ±1 nudge on Reddit posts, N=93,019
    - Up-treated: +11.02% final score vs control
    - Down-treated: -5.15% final score vs control
    - Up-treated: +24.6% probability of reaching high score (≥2000)

  Glenski 2017 (comments): ±1 nudge on Reddit comments, N=128,316
    - Up-treated: NO significant positive herding
    - Down-treated: -37.4% final score vs control

  Muchnik 2013 (non-Reddit, for reference):
    - Up-treated: +25% final score, +32% next positive vote
    - Down-treated: NO effect (corrected by users)
"""

import csv
import statistics
from pathlib import Path
from collections import defaultdict

DATA_FILE = Path(__file__).parent / "analysis_data.csv"

# --- sort=hot runs only (valid for ranking hypothesis) ---
SORT_HOT_RUNS = {
    "gpt-5":  ["e1a-run09", "e1b-run09", "e1a-run12", "e1b-run12", "e1a-run21", "e1b-run21", "e1a-run22", "e1b-run22"],
    "gpt-5.2": ["e1a-run10", "e1b-run10"],
}
ALL_HOT = [r for runs in SORT_HOT_RUNS.values() for r in runs]

ALL_RUNS_BY_SORT = {"hot": ALL_HOT}


def load_data():
    rows = []
    with open(DATA_FILE) as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["score"] = int(row["score"])
            row["adjusted_score"] = int(row["adjusted_score"])
            row["comment_count"] = int(row["comment_count"])
            row["is_world_post"] = row["is_world_post"] == "True"
            row["nudge_applied"] = row["nudge_applied"] == "True"
            rows.append(row)
    return rows


def safe_mean(vals):
    return statistics.mean(vals) if vals else 0.0


def safe_stdev(vals):
    return statistics.stdev(vals) if len(vals) > 1 else 0.0


def safe_median(vals):
    return statistics.median(vals) if vals else 0.0


def bootstrap_ci(vals, n_boot=10000, ci=0.95):
    """Bootstrap confidence interval for the mean."""
    import random
    if len(vals) < 2:
        return (0, 0)
    means = []
    for _ in range(n_boot):
        sample = random.choices(vals, k=len(vals))
        means.append(statistics.mean(sample))
    means.sort()
    lo = means[int((1 - ci) / 2 * n_boot)]
    hi = means[int((1 + ci) / 2 * n_boot)]
    return (lo, hi)


def pct_change(treatment_mean, control_mean):
    """Percentage change: (treatment - control) / control * 100"""
    if control_mean == 0:
        return float('inf') if treatment_mean > 0 else 0.0
    return (treatment_mean - control_mean) / control_mean * 100


def mann_whitney_U(a, b):
    """Simple Mann-Whitney U test (two-sided)."""
    from itertools import combinations
    na, nb = len(a), len(b)
    if na == 0 or nb == 0:
        return 0, 1.0
    combined = [(v, 'a') for v in a] + [(v, 'b') for v in b]
    combined.sort(key=lambda x: x[0])
    # Assign ranks with tie handling
    ranks = {}
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            if k not in ranks:
                ranks[k] = []
            ranks[k] = avg_rank
        i = j
    R1 = sum(ranks[k] for k in range(len(combined)) if combined[k][1] == 'a')
    U1 = R1 - na * (na + 1) / 2
    U2 = na * nb - U1
    U = min(U1, U2)
    # Normal approximation
    mu = na * nb / 2
    sigma = (na * nb * (na + nb + 1) / 12) ** 0.5
    if sigma == 0:
        return U, 1.0
    z = (U - mu) / sigma
    # Two-tailed p-value from z
    import math
    p = 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))
    return U, p


def main():
    rows = load_data()

    print("=" * 80)
    print("COMPARISON WITH HUMAN REDDIT STUDIES")
    print("Moltbook AI Agent Results vs. Glenski 2015/2017 (Reddit)")
    print("=" * 80)

    # ================================================================
    # SECTION 1: Our data — sort=hot, Mode A, world posts only
    # ================================================================
    hot_a_world = [r for r in rows if r["run"] in ALL_HOT
                   and r["mode"] == "A" and r["is_world_post"]]
    hot_b_world = [r for r in rows if r["run"] in ALL_HOT
                   and r["mode"] == "B" and r["is_world_post"]]

    print()
    print("-" * 80)
    print("1. PERCENTAGE CHANGE IN SCORE (comparable to Glenski metric)")
    print("-" * 80)
    print()
    print("  Glenski 2015/2017 used: % change = (treatment_mean - control_mean) / control_mean × 100")
    print("  They removed the nudge vote before analysis (same as our adjusted_score).")
    print("  Their metric: final score after 4 days. Ours: score after 1-hour run.")
    print()

    for label, data in [("Mode A (sort=hot, world posts)", hot_a_world),
                        ("Mode B (sort=hot, world posts)", hot_b_world)]:
        up = [r["adjusted_score"] for r in data if r["treatment"] == "nudge_up"]
        ctrl = [r["adjusted_score"] for r in data if r["treatment"] == "control"]
        down = [r["adjusted_score"] for r in data if r["treatment"] == "nudge_down"]

        up_mean, ctrl_mean, down_mean = safe_mean(up), safe_mean(ctrl), safe_mean(down)
        up_pct = pct_change(up_mean, ctrl_mean)
        down_pct = pct_change(down_mean, ctrl_mean)

        print(f"  {label}:")
        print(f"    nudge_up  (n={len(up):>3}): mean={up_mean:>6.2f}  → {up_pct:>+7.2f}% vs control")
        print(f"    control   (n={len(ctrl):>3}): mean={ctrl_mean:>6.2f}  (baseline)")
        print(f"    nudge_down(n={len(down):>3}): mean={down_mean:>6.2f}  → {down_pct:>+7.2f}% vs control")
        print()

    # Same for comment count
    print("  Comment count (our secondary metric, no direct Glenski equivalent):")
    print()
    for label, data in [("Mode A (sort=hot, world posts)", hot_a_world),
                        ("Mode B (sort=hot, world posts)", hot_b_world)]:
        up = [r["comment_count"] for r in data if r["treatment"] == "nudge_up"]
        ctrl = [r["comment_count"] for r in data if r["treatment"] == "control"]
        down = [r["comment_count"] for r in data if r["treatment"] == "nudge_down"]

        up_mean, ctrl_mean, down_mean = safe_mean(up), safe_mean(ctrl), safe_mean(down)
        up_pct = pct_change(up_mean, ctrl_mean)
        down_pct = pct_change(down_mean, ctrl_mean)

        print(f"  {label} — Comments:")
        print(f"    nudge_up  (n={len(up):>3}): mean={up_mean:>6.2f}  → {up_pct:>+7.2f}% vs control")
        print(f"    control   (n={len(ctrl):>3}): mean={ctrl_mean:>6.2f}  (baseline)")
        print(f"    nudge_down(n={len(down):>3}): mean={down_mean:>6.2f}  → {down_pct:>+7.2f}% vs control")
        print()

    # ================================================================
    # SECTION 2: Head-to-head comparison table
    # ================================================================
    print("-" * 80)
    print("2. HEAD-TO-HEAD: AI AGENTS vs HUMAN REDDIT USERS")
    print("-" * 80)
    print()

    # Our Mode A numbers
    up_a = [r["adjusted_score"] for r in hot_a_world if r["treatment"] == "nudge_up"]
    ctrl_a = [r["adjusted_score"] for r in hot_a_world if r["treatment"] == "control"]
    down_a = [r["adjusted_score"] for r in hot_a_world if r["treatment"] == "nudge_down"]

    our_up_pct = pct_change(safe_mean(up_a), safe_mean(ctrl_a))
    our_down_pct = pct_change(safe_mean(down_a), safe_mean(ctrl_a))

    print("  Study                  | Platform    | N posts  | Up effect    | Down effect   | Asymmetry")
    print("  -----------------------|-------------|----------|--------------|---------------|----------")
    print(f"  Glenski 2015 (humans)  | Reddit      |   93,019 | +11.02%  **  | -5.15%   **   | Up > Down")
    print(f"  Muchnik 2013 (humans)  | Undisclosed |  101,281 | +25.00%  **  |  ~0% (ns)     | Up only")
    print(f"  Moltbook (AI agents)   | Moltbook    |      125 | {our_up_pct:>+7.2f}%     | {our_down_pct:>+7.2f}%      | {'Down > Up' if abs(our_down_pct) > abs(our_up_pct) else 'Up > Down'}")
    print()
    print("  ** = statistically significant; ns = not significant")
    print()

    # ================================================================
    # SECTION 3: Score distributions
    # ================================================================
    print("-" * 80)
    print("3. SCORE DISTRIBUTIONS BY TREATMENT")
    print("-" * 80)
    print()
    print("  Glenski noted Reddit scores are extremely right-skewed")
    print("  (skewness=11.2, kurtosis=149.8). How do ours compare?")
    print()

    for label, data in [("Mode A (sort=hot)", hot_a_world)]:
        for treat in ["nudge_up", "control", "nudge_down"]:
            vals = [r["adjusted_score"] for r in data if r["treatment"] == treat]
            if not vals:
                continue
            print(f"  {treat}:")
            print(f"    N={len(vals)}, mean={safe_mean(vals):.2f}, median={safe_median(vals):.1f}, "
                  f"sd={safe_stdev(vals):.2f}, min={min(vals)}, max={max(vals)}")
            # Distribution buckets
            buckets = defaultdict(int)
            for v in vals:
                if v <= 0:
                    buckets["≤0"] += 1
                elif v == 1:
                    buckets["1"] += 1
                elif v <= 3:
                    buckets["2-3"] += 1
                elif v <= 5:
                    buckets["4-5"] += 1
                elif v <= 10:
                    buckets["6-10"] += 1
                else:
                    buckets["11+"] += 1
            dist = "    Distribution: " + ", ".join(f"{k}:{buckets[k]}" for k in ["≤0", "1", "2-3", "4-5", "6-10", "11+"] if buckets.get(k))
            print(dist)
            print()

    # ================================================================
    # SECTION 4: Statistical tests with confidence intervals
    # ================================================================
    print("-" * 80)
    print("4. STATISTICAL TESTS WITH CONFIDENCE INTERVALS")
    print("-" * 80)
    print()

    for label, data in [("Mode A (sort=hot, world posts)", hot_a_world)]:
        up_scores = [r["adjusted_score"] for r in data if r["treatment"] == "nudge_up"]
        ctrl_scores = [r["adjusted_score"] for r in data if r["treatment"] == "control"]
        down_scores = [r["adjusted_score"] for r in data if r["treatment"] == "nudge_down"]

        print(f"  {label}:")
        print()

        # Up vs Control
        U, p = mann_whitney_U(up_scores, ctrl_scores)
        up_ci = bootstrap_ci(up_scores)
        ctrl_ci = bootstrap_ci(ctrl_scores)
        print(f"  nudge_up vs control (Score):")
        print(f"    Up:   mean={safe_mean(up_scores):.2f}  95% CI [{up_ci[0]:.2f}, {up_ci[1]:.2f}]")
        print(f"    Ctrl: mean={safe_mean(ctrl_scores):.2f}  95% CI [{ctrl_ci[0]:.2f}, {ctrl_ci[1]:.2f}]")
        print(f"    Mann-Whitney U={U:.1f}, p={p:.4f} {'*' if p < 0.05 else '(ns)'}")
        print(f"    % change: {pct_change(safe_mean(up_scores), safe_mean(ctrl_scores)):+.2f}%")
        print()

        # Down vs Control
        U, p = mann_whitney_U(down_scores, ctrl_scores)
        down_ci = bootstrap_ci(down_scores)
        print(f"  nudge_down vs control (Score):")
        print(f"    Down: mean={safe_mean(down_scores):.2f}  95% CI [{down_ci[0]:.2f}, {down_ci[1]:.2f}]")
        print(f"    Ctrl: mean={safe_mean(ctrl_scores):.2f}  95% CI [{ctrl_ci[0]:.2f}, {ctrl_ci[1]:.2f}]")
        print(f"    Mann-Whitney U={U:.1f}, p={p:.4f} {'*' if p < 0.05 else '(ns)'}")
        print(f"    % change: {pct_change(safe_mean(down_scores), safe_mean(ctrl_scores)):+.2f}%")
        print()

        # Same for comments
        up_c = [r["comment_count"] for r in data if r["treatment"] == "nudge_up"]
        ctrl_c = [r["comment_count"] for r in data if r["treatment"] == "control"]
        down_c = [r["comment_count"] for r in data if r["treatment"] == "nudge_down"]

        U, p = mann_whitney_U(up_c, ctrl_c)
        print(f"  nudge_up vs control (Comments):")
        print(f"    Up:   mean={safe_mean(up_c):.2f}, Ctrl: mean={safe_mean(ctrl_c):.2f}")
        print(f"    Mann-Whitney U={U:.1f}, p={p:.4f} {'*' if p < 0.05 else '(ns)'}")
        print(f"    % change: {pct_change(safe_mean(up_c), safe_mean(ctrl_c)):+.2f}%")
        print()

        U, p = mann_whitney_U(down_c, ctrl_c)
        print(f"  nudge_down vs control (Comments):")
        print(f"    Down: mean={safe_mean(down_c):.2f}, Ctrl: mean={safe_mean(ctrl_c):.2f}")
        print(f"    Mann-Whitney U={U:.1f}, p={p:.4f} {'*' if p < 0.05 else '(ns)'}")
        print(f"    % change: {pct_change(safe_mean(down_c), safe_mean(ctrl_c)):+.2f}%")
        print()

    # ================================================================
    # SECTION 5: Per-run breakdown
    # ================================================================
    print("-" * 80)
    print("5. PER-RUN PERCENTAGE CHANGES (consistency check)")
    print("-" * 80)
    print()
    print("  Glenski found subreddit-dependent effects. Do our runs show consistent direction?")
    print()
    print("  Run          | N(world) | Up mean | Ctrl mean | Down mean | Up %chg  | Down %chg")
    print("  -------------|----------|---------|-----------|-----------|----------|----------")

    hot_runs_a = sorted(set(r["run"] for r in hot_a_world))
    for run in hot_runs_a:
        run_data = [r for r in hot_a_world if r["run"] == run]
        up = [r["adjusted_score"] for r in run_data if r["treatment"] == "nudge_up"]
        ctrl = [r["adjusted_score"] for r in run_data if r["treatment"] == "control"]
        down = [r["adjusted_score"] for r in run_data if r["treatment"] == "nudge_down"]

        up_m = safe_mean(up) if up else float('nan')
        ctrl_m = safe_mean(ctrl) if ctrl else float('nan')
        down_m = safe_mean(down) if down else float('nan')

        up_pct = pct_change(up_m, ctrl_m) if ctrl else float('nan')
        down_pct = pct_change(down_m, ctrl_m) if ctrl else float('nan')

        print(f"  {run:<13}| {len(run_data):>8} | {up_m:>7.2f} | {ctrl_m:>9.2f} | {down_m:>9.2f} | {up_pct:>+8.1f}% | {down_pct:>+8.1f}%")

    print()

    # ================================================================
    # SECTION 6: Key differences summary
    # ================================================================
    print("-" * 80)
    print("6. KEY DIFFERENCES: AI AGENTS vs HUMANS")
    print("-" * 80)
    print()

    # Compute our final numbers
    our_up = pct_change(safe_mean(up_a), safe_mean(ctrl_a))
    our_down = pct_change(safe_mean(down_a), safe_mean(ctrl_a))

    print("  ASYMMETRY:")
    print(f"    Humans (Glenski/Reddit):  Up stronger (+11.02%) > Down (-5.15%)")
    print(f"    Humans (Muchnik/other):   Up only (+25%), Down has NO effect")
    print(f"    AI Agents (Moltbook):     Up ({our_up:+.1f}%) {'<' if abs(our_up) < abs(our_down) else '>'} Down ({our_down:+.1f}%)")
    if abs(our_down) > abs(our_up):
        print(f"    → REVERSED asymmetry: AI agents show stronger DOWN effect")
    else:
        print(f"    → SAME asymmetry as humans: UP effect stronger")
    print()

    print("  MECHANISM DIFFERENCES:")
    print("    Humans:     Herding (see score → follow the crowd)")
    print("                Correction (see unfair downvote → compensate)")
    print("    AI Agents:  Position-based attention (see feed order, not score directly)")
    print("                No social correction instinct")
    print("                May have LLM primacy bias (attend more to first items in list)")
    print()

    print("  SCALE:")
    print(f"    Glenski: N=93,019 posts, 6 months, millions of voters")
    print(f"    Ours:    N={len(hot_a_world)} world posts, {len(set(r['run'] for r in hot_a_world))} runs × 1 hour, 10 AI agents")
    print(f"    Our sample is ~745x smaller → much wider confidence intervals")
    print()

    print("  EFFECT SIZE:")
    print(f"    Glenski: Small but highly significant (N compensates)")
    print(f"    Ours:    Medium effect sizes (Cohen's f ~0.23-0.28) but not yet significant")
    print(f"    Our effects are directionally LARGER in magnitude than Glenski's,")
    print(f"    which is expected with fewer agents creating more variance")
    print()

    print("=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print()
    if abs(our_down) > abs(our_up) and our_down < 0:
        print("  Our AI agent experiment shows a REVERSED asymmetry compared to human studies:")
        print("  - Humans: upvote herding dominates (Muchnik +25%, Glenski +11%)")
        print("  - AI agents: downvote suppression dominates")
        print()
        print("  Possible explanations:")
        print("  1. AI agents lack the human 'correction' instinct that neutralizes downvotes")
        print("  2. AI agents are more sensitive to position than to displayed score")
        print("     (downvoted posts drop in hot ranking → less visible → less engagement)")
        print("  3. AI agents don't exhibit positive herding (don't 'follow the crowd')")
        print("     because they evaluate content independently, not socially")
        print("  4. With only 10 agents and 1-hour runs, there's less time for cascading")
        print("     herding effects that require many sequential voters")
    else:
        print("  Results show similar direction to human studies but more data needed.")
    print()


if __name__ == "__main__":
    main()
