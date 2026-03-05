#!/usr/bin/env python3
"""Analysis script for factcheck dose-response experiment (factual 0→5).

Loads exports from exports/fc-f{0..5}-run{01..NN}/ and topic-mapping.json,
pooling across all available replications, then produces:
  1. Summary table — n_factual, mean scores, total comments per condition
  2. Dose-response curve — mean score for factual and conspiracy vs dose
  3. Trend test — Spearman correlation of factual count vs mean scores
  4. Score gap plot — (factual − conspiracy) gap vs factual count
  5. Per-run variability — shows consistency across replications

Figures saved to experiments/factcheck/figures/.

Usage:
    python3 experiments/factcheck/analyze_threshold.py [--export-dir exports]
"""

import json
import sys
import argparse
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_EXPORT_DIR = PROJECT_ROOT / "exports"
TOPIC_MAPPING_FILE = SCRIPT_DIR / "topic-mapping.json"
FIGURES_DIR = SCRIPT_DIR / "figures"

DOSES = [0, 1, 2, 3, 4, 5]
MAX_RUNS = 20  # scan up to run20


def load_topic_mapping():
    with open(TOPIC_MAPPING_FILE) as f:
        return json.load(f)


def load_jsonl(path):
    rows = []
    if not path.exists():
        return rows
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def classify_post(title, topic_mapping):
    if title in topic_mapping:
        return topic_mapping[title]["type"]
    return "agent"


def bootstrap_ci(data, n_boot=5000, ci=95, seed=42):
    """Compute bootstrap confidence interval for the mean."""
    rng = np.random.RandomState(seed)
    data = np.array(data, dtype=float)
    if len(data) == 0:
        return np.nan, np.nan, np.nan
    means = np.array([rng.choice(data, size=len(data), replace=True).mean()
                       for _ in range(n_boot)])
    alpha = (100 - ci) / 2
    lo = np.percentile(means, alpha)
    hi = np.percentile(means, 100 - alpha)
    return data.mean(), lo, hi


def discover_runs(export_dir):
    """Discover all available runs per dose, return {dose: [run_names]}."""
    runs_by_dose = defaultdict(list)
    for dose in DOSES:
        for run_num in range(1, MAX_RUNS + 1):
            run_name = f"fc-f{dose}-run{run_num:02d}"
            run_dir = export_dir / run_name
            if run_dir.exists() and (run_dir / "posts.jsonl").exists():
                runs_by_dose[dose].append(run_name)
    return dict(runs_by_dose)


def load_condition(export_dir, run_name, topic_mapping):
    """Load and classify posts for a single run."""
    run_dir = export_dir / run_name
    if not run_dir.exists():
        return None

    posts = load_jsonl(run_dir / "posts.jsonl")
    treatments = load_jsonl(run_dir / "treatments.jsonl")

    rows = []
    for p in posts:
        title = p.get("title", "")
        post_type = classify_post(title, topic_mapping)
        rows.append({
            "post_id": p["id"],
            "title": title,
            "post_type": post_type,
            "score": p.get("score", 0),
            "comment_count": p.get("comment_count", 0),
            "author": p.get("author_name", ""),
            "run_name": run_name,
        })

    df = pd.DataFrame(rows)

    # Verify all treatments are control (Mode C)
    treatment_types = set(t.get("treatment", "") for t in treatments)
    non_control = treatment_types - {"control"}
    if non_control:
        print(f"  [WARN] {run_name}: found non-control treatments: {non_control}")

    return df


def main():
    parser = argparse.ArgumentParser(description="Analyze factcheck dose-response experiment")
    parser.add_argument("--export-dir", type=Path, default=DEFAULT_EXPORT_DIR)
    args = parser.parse_args()

    export_dir = args.export_dir
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("  FACTCHECK DOSE-RESPONSE ANALYSIS (Factual 0→5)")
    print("  Multi-run pooled analysis")
    print("=" * 60)

    topic_mapping = load_topic_mapping()
    print(f"\nTopic mapping: {len(topic_mapping)} entries")

    # Discover available runs
    runs_by_dose = discover_runs(export_dir)
    all_run_nums = set()
    for runs in runs_by_dose.values():
        for r in runs:
            all_run_nums.add(r.split("-run")[1])
    n_reps = len(all_run_nums) if all_run_nums else 0
    print(f"Replications found: {n_reps} ({sorted(all_run_nums)})")

    # Load all data into one big DataFrame
    print(f"\nLoading conditions from {export_dir}/...")
    all_dfs = []
    for dose in DOSES:
        runs = runs_by_dose.get(dose, [])
        for run_name in runs:
            df = load_condition(export_dir, run_name, topic_mapping)
            if df is not None:
                df["dose"] = dose
                all_dfs.append(df)
                n_fact = (df["post_type"] == "factual").sum()
                n_cons = (df["post_type"] == "conspiracy").sum()
                n_agent = (df["post_type"] == "agent").sum()
                print(f"  {run_name}: {len(df)} posts ({n_fact}F, {n_cons}C, {n_agent} agent)")

    if not all_dfs:
        print("\n[ERROR] No data loaded. Exiting.")
        sys.exit(1)

    df_all = pd.concat(all_dfs, ignore_index=True)
    world = df_all[df_all["post_type"].isin(["factual", "conspiracy"])]
    print(f"\nTotal: {len(df_all)} posts ({len(world)} world posts across {n_reps} replications)")

    # ─────────────────────────────────────────────
    # 1. Summary Table (pooled across all reps)
    # ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  1. SUMMARY TABLE (pooled across replications)")
    print(f"{'='*60}\n")

    header = f"{'Dose':>4}  {'N_fact':>6}  {'N_cons':>6}  {'N_runs':>6}  {'Fact_μ':>7}  {'Cons_μ':>7}  {'Gap':>7}"
    print(header)
    print("-" * len(header))

    summary_rows = []
    for dose in DOSES:
        cond = world[world["dose"] == dose]
        fact = cond[cond["post_type"] == "factual"]
        cons = cond[cond["post_type"] == "conspiracy"]
        n_runs = len(runs_by_dose.get(dose, []))

        fact_mean = fact["score"].mean() if len(fact) > 0 else float("nan")
        cons_mean = cons["score"].mean() if len(cons) > 0 else float("nan")
        gap = fact_mean - cons_mean if not (np.isnan(fact_mean) or np.isnan(cons_mean)) else float("nan")

        summary_rows.append({
            "dose": dose,
            "n_fact": len(fact),
            "n_cons": len(cons),
            "n_runs": n_runs,
            "fact_mean": fact_mean,
            "cons_mean": cons_mean,
            "gap": gap,
            "fact_scores": fact["score"].values,
            "cons_scores": cons["score"].values,
        })

        fact_str = f"{fact_mean:.2f}" if not np.isnan(fact_mean) else "  n/a"
        cons_str = f"{cons_mean:.2f}" if not np.isnan(cons_mean) else "  n/a"
        gap_str = f"{gap:+.2f}" if not np.isnan(gap) else "  n/a"
        print(f"{dose:>4}  {len(fact):>6}  {len(cons):>6}  {n_runs:>6}  {fact_str:>7}  {cons_str:>7}  {gap_str:>7}")

    # ─────────────────────────────────────────────
    # 2. Dose-Response Curve (pooled)
    # ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  2. DOSE-RESPONSE CURVE (pooled, bootstrap 95% CI)")
    print(f"{'='*60}\n")

    doses_arr = np.array(DOSES)
    fact_means, fact_los, fact_his = [], [], []
    cons_means, cons_los, cons_his = [], [], []

    for row in summary_rows:
        d = row["dose"]

        if len(row["fact_scores"]) > 0:
            m, lo, hi = bootstrap_ci(row["fact_scores"])
            fact_means.append(m)
            fact_los.append(lo)
            fact_his.append(hi)
            print(f"  Dose {d} — Factual:    mean={m:.2f}, 95% CI=[{lo:.2f}, {hi:.2f}], n={len(row['fact_scores'])}")
        else:
            fact_means.append(np.nan)
            fact_los.append(np.nan)
            fact_his.append(np.nan)
            print(f"  Dose {d} — Factual:    n/a (0 posts)")

        m, lo, hi = bootstrap_ci(row["cons_scores"])
        cons_means.append(m)
        cons_los.append(lo)
        cons_his.append(hi)
        print(f"  Dose {d} — Conspiracy: mean={m:.2f}, 95% CI=[{lo:.2f}, {hi:.2f}], n={len(row['cons_scores'])}")

    # Plot
    fig, ax = plt.subplots(figsize=(8, 5))

    cons_m = np.array(cons_means)
    cons_lo = np.array(cons_los)
    cons_hi = np.array(cons_his)
    ax.plot(doses_arr, cons_m, "o-", color="#e74c3c", label="Conspiracy posts", linewidth=2, markersize=8)
    ax.fill_between(doses_arr, cons_lo, cons_hi, alpha=0.2, color="#e74c3c")

    fact_m = np.array(fact_means)
    fact_lo = np.array(fact_los)
    fact_hi = np.array(fact_his)
    valid = ~np.isnan(fact_m)
    if valid.any():
        ax.plot(doses_arr[valid], fact_m[valid], "s-", color="#2ecc71", label="Factual posts", linewidth=2, markersize=8)
        ax.fill_between(doses_arr[valid], fact_lo[valid], fact_hi[valid], alpha=0.2, color="#2ecc71")

    ax.set_xlabel("Number of Factual Posts (dose)", fontsize=12)
    ax.set_ylabel("Mean Score", fontsize=12)
    ax.set_title(f"Factcheck Dose-Response: Factual Post Count → Engagement\n({n_reps} replications, {len(world)} world posts)", fontsize=13)
    ax.set_xticks(range(6))
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    dose_path = FIGURES_DIR / "threshold_dose_response.png"
    fig.savefig(dose_path, dpi=150)
    plt.close(fig)
    print(f"\n  Saved: {dose_path}")

    # ─────────────────────────────────────────────
    # 3. Trend Tests
    # ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  3. TREND TESTS (Spearman)")
    print(f"{'='*60}\n")

    # Conspiracy trend
    cons_valid = [(d, m) for d, m in zip(DOSES, cons_means) if not np.isnan(m)]
    if len(cons_valid) >= 3:
        d_vals, m_vals = zip(*cons_valid)
        rho, p = stats.spearmanr(d_vals, m_vals)
        sig = "*" if p < 0.05 else "ns"
        print(f"  Conspiracy score vs dose: ρ={rho:.3f}, p={p:.4f} [{sig}]")

    # Factual trend
    fact_valid = [(d, m) for d, m in zip(DOSES, fact_means) if not np.isnan(m)]
    if len(fact_valid) >= 3:
        d_vals, m_vals = zip(*fact_valid)
        rho, p = stats.spearmanr(d_vals, m_vals)
        sig = "*" if p < 0.05 else "ns"
        print(f"  Factual score vs dose:    ρ={rho:.3f}, p={p:.4f} [{sig}]")

    # Mann-Whitney: factual vs conspiracy (pooled across all doses ≥ 1)
    all_fact_scores = world[world["post_type"] == "factual"]["score"].values
    all_cons_scores = world[world["post_type"] == "conspiracy"]["score"].values
    if len(all_fact_scores) > 0 and len(all_cons_scores) > 0:
        u_stat, p_mw = stats.mannwhitneyu(all_fact_scores, all_cons_scores, alternative="two-sided")
        sig = "*" if p_mw < 0.05 else "ns"
        print(f"\n  Mann-Whitney U (factual vs conspiracy, all doses ≥ 1):")
        print(f"    U={u_stat:.0f}, p={p_mw:.4f} [{sig}]")
        print(f"    Factual median={np.median(all_fact_scores):.1f}, Conspiracy median={np.median(all_cons_scores):.1f}")

    # ─────────────────────────────────────────────
    # 4. Score Gap Plot
    # ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  4. SCORE GAP (Factual − Conspiracy)")
    print(f"{'='*60}\n")

    gaps = []
    gap_doses = []
    for row in summary_rows:
        if not np.isnan(row["gap"]):
            gaps.append(row["gap"])
            gap_doses.append(row["dose"])
            print(f"  Dose {row['dose']}: gap = {row['gap']:+.2f}  (factual={row['fact_mean']:.2f}, conspiracy={row['cons_mean']:.2f})")

    if len(gaps) >= 2:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar(gap_doses, gaps, color=["#e74c3c" if g < 0 else "#2ecc71" for g in gaps],
               alpha=0.8, edgecolor="black", linewidth=0.5)
        ax.axhline(y=0, color="black", linewidth=0.8, linestyle="--")
        ax.set_xlabel("Number of Factual Posts (dose)", fontsize=12)
        ax.set_ylabel("Score Gap (Factual − Conspiracy)", fontsize=12)
        ax.set_title(f"Factcheck Score Gap vs Factual Dose ({n_reps} replications)", fontsize=14)
        ax.set_xticks(gap_doses)
        ax.grid(True, alpha=0.3, axis="y")
        fig.tight_layout()

        gap_path = FIGURES_DIR / "threshold_score_gap.png"
        fig.savefig(gap_path, dpi=150)
        plt.close(fig)
        print(f"\n  Saved: {gap_path}")

        if len(gaps) >= 3:
            rho, p = stats.spearmanr(gap_doses, gaps)
            sig = "*" if p < 0.05 else "ns"
            print(f"  Gap trend: ρ={rho:.3f}, p={p:.4f} [{sig}]")

    # ─────────────────────────────────────────────
    # 5. Per-run variability
    # ─────────────────────────────────────────────
    if n_reps > 1:
        print(f"\n{'='*60}")
        print("  5. PER-RUN VARIABILITY")
        print(f"{'='*60}\n")

        # Compute per-run mean scores for factual and conspiracy
        for dose in DOSES:
            runs = runs_by_dose.get(dose, [])
            if not runs:
                continue
            run_fact_means = []
            run_cons_means = []
            for run_name in runs:
                run_df = world[(world["dose"] == dose) & (world["run_name"] == run_name)]
                fact = run_df[run_df["post_type"] == "factual"]["score"]
                cons = run_df[run_df["post_type"] == "conspiracy"]["score"]
                run_fact_means.append(fact.mean() if len(fact) > 0 else float("nan"))
                run_cons_means.append(cons.mean())

            cons_arr = np.array(run_cons_means)
            print(f"  Dose {dose}: conspiracy per-run means = {[f'{x:.2f}' for x in cons_arr]}, "
                  f"SD = {np.nanstd(cons_arr):.2f}")
            if dose > 0:
                fact_arr = np.array([x for x in run_fact_means if not np.isnan(x)])
                if len(fact_arr) > 0:
                    print(f"          factual per-run means   = {[f'{x:.2f}' for x in fact_arr]}, "
                          f"SD = {np.nanstd(fact_arr):.2f}")

        # Per-run variability figure
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Panel A: Per-run conspiracy means by dose
        ax = axes[0]
        for dose in DOSES:
            runs = runs_by_dose.get(dose, [])
            for run_name in runs:
                run_df = world[(world["dose"] == dose) & (world["run_name"] == run_name)]
                cons_mean = run_df[run_df["post_type"] == "conspiracy"]["score"].mean()
                ax.plot(dose, cons_mean, "o", color="#e74c3c", alpha=0.4, markersize=6)
        ax.plot(doses_arr, cons_m, "s-", color="#e74c3c", linewidth=2, markersize=8, label="Pooled mean")
        ax.set_xlabel("Dose", fontsize=12)
        ax.set_ylabel("Mean Conspiracy Score", fontsize=12)
        ax.set_title("Conspiracy scores per run", fontsize=13)
        ax.set_xticks(range(6))
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Panel B: Per-run factual means by dose
        ax = axes[1]
        for dose in DOSES:
            if dose == 0:
                continue
            runs = runs_by_dose.get(dose, [])
            for run_name in runs:
                run_df = world[(world["dose"] == dose) & (world["run_name"] == run_name)]
                fact = run_df[run_df["post_type"] == "factual"]["score"]
                if len(fact) > 0:
                    ax.plot(dose, fact.mean(), "o", color="#2ecc71", alpha=0.4, markersize=6)
        if valid.any():
            ax.plot(doses_arr[valid], fact_m[valid], "s-", color="#2ecc71", linewidth=2, markersize=8, label="Pooled mean")
        ax.set_xlabel("Dose", fontsize=12)
        ax.set_ylabel("Mean Factual Score", fontsize=12)
        ax.set_title("Factual scores per run", fontsize=13)
        ax.set_xticks(range(1, 6))
        ax.legend()
        ax.grid(True, alpha=0.3)

        fig.tight_layout()
        var_path = FIGURES_DIR / "threshold_per_run_variability.png"
        fig.savefig(var_path, dpi=150)
        plt.close(fig)
        print(f"\n  Saved: {var_path}")

    # ─────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("  ANALYSIS COMPLETE")
    print(f"{'='*60}")
    print(f"  Doses loaded:    {len([d for d in DOSES if d in runs_by_dose])}/6")
    print(f"  Replications:    {n_reps}")
    print(f"  Total posts:     {len(df_all)} ({len(world)} world posts)")
    print(f"  Figures saved to: {FIGURES_DIR}/")


if __name__ == "__main__":
    main()
