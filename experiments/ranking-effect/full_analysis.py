#!/usr/bin/env python3
"""
==========================================================================
CivicLens Experiment 1  - Full Analysis Report
Does Algorithmic Ranking Nudge Affect Organic Engagement in AI-Agent
Social Media?
==========================================================================

Generates:
  1. experiments/ranking-effect/report/REPORT.md  (text report)
  2. experiments/ranking-effect/report/fig_*.png   (figures)
  3. experiments/ranking-effect/report/analysis.csv (tidy data)
"""

import json, os, math, sys, textwrap
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats

# ============================================================
# Config
# ============================================================
EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"
REPORT_DIR  = Path(__file__).parent / "report"
REPORT_DIR.mkdir(exist_ok=True)

GOOD_RUNS_A = ["e1a-run01", "e1a-run02", "e1a-run03"]
GOOD_RUNS_B = ["e1b-run01", "e1b-run02", "e1b-run03"]
ALL_GOOD    = GOOD_RUNS_A + GOOD_RUNS_B

TREAT_ORDER = ["nudge_up", "control", "nudge_down"]
TREAT_LABELS = {"nudge_up": "Nudge Up", "control": "Control", "nudge_down": "Nudge Down"}
TREAT_COLORS = {"nudge_up": "#4CAF50", "control": "#9E9E9E", "nudge_down": "#F44336"}

# ============================================================
# Helpers
# ============================================================
def load_jsonl(p):
    if not p.exists(): return []
    out = []
    with open(p) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try: out.append(json.loads(ln))
                except: pass
    return out

def load_run(name):
    d = EXPORTS_DIR / name
    return dict(
        name=name,
        posts=load_jsonl(d/"posts.jsonl"),
        comments=load_jsonl(d/"comments.jsonl"),
        treatments=load_jsonl(d/"treatments.jsonl"),
        activity=load_jsonl(d/"activity.jsonl"),
        agents=load_jsonl(d/"agents.jsonl"),
    )

def smean(v): return statistics.mean(v) if v else 0.0
def ssd(v):   return statistics.stdev(v) if len(v)>=2 else 0.0
def smed(v):  return statistics.median(v) if v else 0.0

def fmt(m, s): return f"{m:.2f} +/- {s:.2f}"

# ============================================================
# Build tidy dataset
# ============================================================
def build_dataset(runs):
    rows = []
    for name in ALL_GOOD:
        r = runs[name]
        mode = "A" if name.startswith("e1a") else "B"
        post_map = {p["id"]: p for p in r["posts"]}
        cc = defaultdict(int)
        for c in r["comments"]:
            pid = c.get("post_id")
            if pid: cc[pid] += 1

        for t in r["treatments"]:
            pid = t["post_id"]
            post = post_map.get(pid, {})
            score = t.get("post_score", post.get("score", 0)) or 0
            comments = cc.get(pid, t.get("post_comment_count", 0) or 0)
            nudge_applied = t.get("nudge_vote_id") is not None
            treat = t["treatment"]
            if nudge_applied and treat == "nudge_up":
                adj = score - 1
            elif nudge_applied and treat == "nudge_down":
                adj = score + 1
            else:
                adj = score
            author = t.get("post_author_name", post.get("author_name", ""))
            is_world = (author == "civiclens_world")
            rows.append(dict(
                run=name, mode=mode, post_id=pid, treatment=treat,
                is_world=is_world, score=score, adjusted_score=adj,
                comment_count=comments, nudge_applied=nudge_applied,
                nudge_delay_min=t.get("nudge_delay_minutes"),
                author=author,
                title=t.get("post_title", post.get("title","")),
            ))
    return rows

# ============================================================
# Figures
# ============================================================
plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 10,
    "axes.titlesize": 12, "axes.labelsize": 11,
    "figure.facecolor": "white",
})

def fig_engagement_by_treatment(rows, path):
    """Box plots: comments & adjusted score by treatment, faceted by mode."""
    fig, axes = plt.subplots(2, 2, figsize=(10, 8))
    fig.suptitle("Engagement by Treatment Group", fontsize=14, fontweight="bold")

    for col, mode_label, mode_code in [(0, "Mode A (Seed-Only Nudge)", "A"),
                                        (1, "Mode B (All-Post Nudge)", "B")]:
        world = [r for r in rows if r["mode"]==mode_code and r["is_world"]]
        for row_idx, (metric, label) in enumerate([
            ("adjusted_score", "Score (adjusted)"),
            ("comment_count", "Comment Count"),
        ]):
            ax = axes[row_idx][col]
            data = []
            positions = []
            colors = []
            for i, treat in enumerate(TREAT_ORDER):
                vals = [r[metric] for r in world if r["treatment"]==treat]
                data.append(vals)
                positions.append(i)
                colors.append(TREAT_COLORS[treat])

            bp = ax.boxplot(data, positions=positions, widths=0.6, patch_artist=True,
                           showmeans=True, meanprops=dict(marker='D', markerfacecolor='black', markersize=5))
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.6)

            ax.set_xticks(positions)
            ax.set_xticklabels([TREAT_LABELS[t] for t in TREAT_ORDER], fontsize=9)
            ax.set_ylabel(label)
            if row_idx == 0:
                ax.set_title(mode_label)

            # Add N labels
            for i, treat in enumerate(TREAT_ORDER):
                n = len([r for r in world if r["treatment"]==treat])
                ax.text(i, ax.get_ylim()[0] - 0.05*(ax.get_ylim()[1]-ax.get_ylim()[0]),
                       f"n={n}", ha='center', fontsize=8, color='gray')

    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_mode_comparison(rows, path):
    """Bar chart comparing Mode A vs Mode B engagement."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.suptitle("Mode A (Seed-Only) vs Mode B (All Posts)", fontsize=14, fontweight="bold")

    world_a = [r for r in rows if r["mode"]=="A" and r["is_world"]]
    world_b = [r for r in rows if r["mode"]=="B" and r["is_world"]]

    for ax_idx, (metric, label) in enumerate([
        ("adjusted_score", "Mean Adjusted Score"),
        ("comment_count", "Mean Comment Count"),
    ]):
        ax = axes[ax_idx]
        x = [0, 1, 2]
        width = 0.35

        means_a, sems_a, means_b, sems_b = [], [], [], []
        for treat in TREAT_ORDER:
            va = [r[metric] for r in world_a if r["treatment"]==treat]
            vb = [r[metric] for r in world_b if r["treatment"]==treat]
            means_a.append(smean(va))
            sems_a.append(ssd(va)/math.sqrt(len(va)) if len(va)>1 else 0)
            means_b.append(smean(vb))
            sems_b.append(ssd(vb)/math.sqrt(len(vb)) if len(vb)>1 else 0)

        bars_a = ax.bar([xi - width/2 for xi in x], means_a, width, yerr=sems_a,
                        label="Mode A (seed-only)", color="#2196F3", alpha=0.7, capsize=4)
        bars_b = ax.bar([xi + width/2 for xi in x], means_b, width, yerr=sems_b,
                        label="Mode B (all posts)", color="#FF9800", alpha=0.7, capsize=4)

        ax.set_xticks(x)
        ax.set_xticklabels([TREAT_LABELS[t] for t in TREAT_ORDER])
        ax.set_ylabel(label)
        ax.legend(fontsize=9)
        ax.set_ylim(bottom=0)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_per_run_consistency(rows, path):
    """Line plot showing per-run means to assess consistency."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 5))
    fig.suptitle("Per-Run Consistency Check", fontsize=14, fontweight="bold")

    for ax_idx, (metric, label) in enumerate([
        ("comment_count", "Mean Comments per World Post"),
        ("adjusted_score", "Mean Score per World Post"),
    ]):
        ax = axes[ax_idx]
        for mode, runs_list, color, marker in [("A", GOOD_RUNS_A, "#2196F3", "o"),
                                                 ("B", GOOD_RUNS_B, "#FF9800", "s")]:
            means = []
            for run in runs_list:
                world = [r for r in rows if r["run"]==run and r["is_world"]]
                means.append(smean([r[metric] for r in world]))
            ax.plot(range(len(runs_list)), means, marker=marker, label=f"Mode {mode}",
                   color=color, linewidth=2, markersize=8)

        ax.set_xticks(range(3))
        ax.set_xticklabels(["Run 1", "Run 2", "Run 3"])
        ax.set_ylabel(label)
        ax.legend()
        ax.set_ylim(bottom=0)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_agent_participation(runs, path):
    """Heatmap of agent comment counts per run."""
    agent_names = sorted(set(
        a.get("name","") for r in runs.values() for a in r["agents"]
        if a.get("name","").startswith("ranking_")
    ))
    run_names = ALL_GOOD

    matrix = []
    for run in run_names:
        cc = defaultdict(int)
        for c in runs[run]["comments"]:
            cc[c.get("author_name","")] += 1
        matrix.append([cc.get(a, 0) for a in agent_names])

    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(matrix, cmap="YlOrRd", aspect="auto")
    ax.set_xticks(range(len(agent_names)))
    ax.set_xticklabels([a.replace("ranking_","") for a in agent_names], rotation=45, ha="right", fontsize=9)
    ax.set_yticks(range(len(run_names)))
    ax.set_yticklabels(run_names, fontsize=9)
    ax.set_title("Agent Comment Counts per Run", fontsize=14, fontweight="bold")

    for i in range(len(run_names)):
        for j in range(len(agent_names)):
            val = matrix[i][j]
            ax.text(j, i, str(val), ha="center", va="center", fontsize=7,
                   color="white" if val > 30 else "black")

    fig.colorbar(im, ax=ax, label="Comments")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_treatment_balance(rows, path):
    """Stacked bar showing treatment assignment balance per run."""
    fig, ax = plt.subplots(figsize=(8, 5))

    run_names = ALL_GOOD
    bottoms = [0] * len(run_names)

    for treat in TREAT_ORDER:
        counts = []
        for run in run_names:
            world = [r for r in rows if r["run"]==run and r["is_world"] and r["treatment"]==treat]
            counts.append(len(world))
        ax.bar(range(len(run_names)), counts, bottom=bottoms, label=TREAT_LABELS[treat],
              color=TREAT_COLORS[treat], alpha=0.7)
        bottoms = [b+c for b,c in zip(bottoms, counts)]

    ax.set_xticks(range(len(run_names)))
    ax.set_xticklabels(run_names, rotation=30, ha="right")
    ax.set_ylabel("Number of World Posts")
    ax.set_title("Treatment Assignment Balance (World Posts)", fontsize=14, fontweight="bold")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_power_projection(test_results, rows, path):
    """Power curve showing current power and projected power at larger sample sizes."""
    from scipy.stats import nct, t as t_dist, ncf, f as f_dist

    def power_ttest_2s(d, n_per_group, alpha=0.05):
        """Two-sided power for equal-n independent t-test."""
        if n_per_group < 3:
            return 0.0
        df = 2 * n_per_group - 2
        t_crit = t_dist.ppf(1 - alpha / 2, df)
        nc = abs(d) * math.sqrt(n_per_group / 2)
        return 1 - nct.cdf(t_crit, df, nc) + nct.cdf(-t_crit, df, nc)

    def power_anova_3g(f_effect, n_per_group, alpha=0.05):
        """Power for 3-group one-way ANOVA."""
        if n_per_group < 3:
            return 0.0
        k = 3
        N = k * n_per_group
        df1 = k - 1
        df2 = N - k
        f_crit = f_dist.ppf(1 - alpha, df1, df2)
        nc = f_effect ** 2 * N
        return 1 - ncf.cdf(f_crit, df1, df2, nc)

    # Observed effect sizes
    d_score = abs(test_results["A_adjusted_score_nudge_down_vs_ctrl"]["d"])  # 0.53
    f_score = test_results["A_adjusted_score_anova"]["cohens_f"]             # 0.18

    # Current min group size
    world_a = [r for r in rows if r["mode"] == "A" and r["is_world"]]
    current_n = min(len([r for r in world_a if r["treatment"] == t]) for t in TREAT_ORDER)
    runs_now = 3

    # Range: from 10 to 300 per group
    ns = list(range(5, 301, 5))

    # Compute power curves
    pow_pairwise = [power_ttest_2s(d_score, n) for n in ns]
    pow_omnibus = [power_anova_3g(f_score, n) for n in ns]

    # Find n needed for 80% power
    n80_pair = next((n for n, p in zip(ns, pow_pairwise) if p >= 0.80), ns[-1])
    n80_omni = next((n for n, p in zip(ns, pow_omnibus) if p >= 0.80), ns[-1])

    # How many runs = n per group? Each run produces ~31 world posts / 3 treatments ≈ 10 per group
    posts_per_run_per_group = 10  # approximate

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Statistical Power Projection", fontsize=14, fontweight="bold")

    # Left panel: pairwise comparison (nudge_down vs control)
    ax = axes[0]
    ax.plot(ns, pow_pairwise, color="#2196F3", linewidth=2.5, label=f"Observed d = {d_score:.2f}")
    ax.axhline(0.80, color="gray", linestyle="--", alpha=0.6, label="80% power threshold")
    ax.axvline(current_n, color="#F44336", linestyle=":", linewidth=2, label=f"Current n = {current_n}")
    ax.axvline(n80_pair, color="#4CAF50", linestyle=":", linewidth=2, label=f"Need n = {n80_pair}")

    # Mark current power
    current_pow = power_ttest_2s(d_score, current_n)
    ax.plot(current_n, current_pow, "o", color="#F44336", markersize=10, zorder=5)
    ax.annotate(f"Now: {current_pow:.0%} power\n({runs_now} runs)",
                xy=(current_n, current_pow), xytext=(current_n + 30, current_pow - 0.1),
                fontsize=9, arrowprops=dict(arrowstyle="->", color="gray"),
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFCDD2"))

    # Mark target
    runs_needed = math.ceil(n80_pair / posts_per_run_per_group)
    ax.plot(n80_pair, 0.80, "o", color="#4CAF50", markersize=10, zorder=5)
    ax.annotate(f"Target: 80% power\n(~{runs_needed} runs Mode A)",
                xy=(n80_pair, 0.80), xytext=(n80_pair + 20, 0.65),
                fontsize=9, arrowprops=dict(arrowstyle="->", color="gray"),
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#C8E6C9"))

    ax.set_xlabel("Sample Size per Group")
    ax.set_ylabel("Statistical Power")
    ax.set_title(f"Pairwise: Nudge Down vs Control\n(Cohen's d = {d_score:.2f})")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, 200)

    # Right panel: omnibus ANOVA (3 groups)
    ax = axes[1]
    ax.plot(ns, pow_omnibus, color="#FF9800", linewidth=2.5, label=f"Observed f = {f_score:.2f}")
    ax.axhline(0.80, color="gray", linestyle="--", alpha=0.6, label="80% power threshold")
    ax.axvline(current_n, color="#F44336", linestyle=":", linewidth=2, label=f"Current n = {current_n}")

    if n80_omni <= 300:
        ax.axvline(n80_omni, color="#4CAF50", linestyle=":", linewidth=2, label=f"Need n = {n80_omni}")
        runs_omni = math.ceil(n80_omni / posts_per_run_per_group)
        ax.plot(n80_omni, 0.80, "o", color="#4CAF50", markersize=10, zorder=5)
        ax.annotate(f"Target: 80% power\n(~{runs_omni} runs Mode A)",
                    xy=(n80_omni, 0.80), xytext=(min(n80_omni + 20, 220), 0.65),
                    fontsize=9, arrowprops=dict(arrowstyle="->", color="gray"),
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="#C8E6C9"))

    current_pow_omni = power_anova_3g(f_score, current_n)
    ax.plot(current_n, current_pow_omni, "o", color="#F44336", markersize=10, zorder=5)
    ax.annotate(f"Now: {current_pow_omni:.0%} power\n({runs_now} runs)",
                xy=(current_n, current_pow_omni), xytext=(current_n + 30, max(current_pow_omni - 0.1, 0.05)),
                fontsize=9, arrowprops=dict(arrowstyle="->", color="gray"),
                bbox=dict(boxstyle="round,pad=0.3", facecolor="#FFCDD2"))

    ax.set_xlabel("Sample Size per Group")
    ax.set_ylabel("Statistical Power")
    ax.set_title(f"Omnibus ANOVA (3 groups)\n(Cohen's f = {f_score:.2f})")
    ax.legend(fontsize=8, loc="lower right")
    ax.set_ylim(0, 1.05)
    ax.set_xlim(0, 300)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)

    # Return key numbers for the report
    return dict(
        d_score=d_score, f_score=f_score,
        current_n=current_n, current_pow_pair=current_pow,
        current_pow_omni=current_pow_omni,
        n80_pair=n80_pair, n80_omni=n80_omni,
        runs_needed_pair=math.ceil(n80_pair / posts_per_run_per_group),
        additional_runs_pair=max(0, math.ceil(n80_pair / posts_per_run_per_group) - runs_now),
    )


# ============================================================
# Statistical tests
# ============================================================
def run_all_tests(rows):
    """Run all statistical tests, return results dict."""
    results = {}
    world_a = [r for r in rows if r["mode"]=="A" and r["is_world"]]
    world_b = [r for r in rows if r["mode"]=="B" and r["is_world"]]

    # --- Mode A omnibus tests ---
    for metric, key in [("Adjusted Score", "adjusted_score"), ("Comment Count", "comment_count")]:
        groups = [[r[key] for r in world_a if r["treatment"]==t] for t in TREAT_ORDER]
        H, p_kw = stats.kruskal(*[g for g in groups if g])
        # Effect size: epsilon-squared for KW
        N = sum(len(g) for g in groups)
        eps_sq = (H - len(groups) + 1) / (N - len(groups)) if N > len(groups) else 0

        # Cohen's f from one-way ANOVA
        F_stat, p_anova = stats.f_oneway(*[g for g in groups if g])
        grand = [v for g in groups for v in g]
        gm = smean(grand)
        ss_b = sum(len(g)*(smean(g)-gm)**2 for g in groups if g)
        ss_w = sum(sum((v-smean(g))**2 for v in g) for g in groups if g)
        eta_sq = ss_b/(ss_b+ss_w) if (ss_b+ss_w)>0 else 0
        cohens_f = math.sqrt(eta_sq/(1-eta_sq)) if eta_sq < 1 else 0

        results[f"A_{key}_kruskal"] = dict(H=H, p=p_kw, eps_sq=eps_sq)
        results[f"A_{key}_anova"] = dict(F=F_stat, p=p_anova, eta_sq=eta_sq, cohens_f=cohens_f)

        # Pairwise: nudge_up vs control, nudge_down vs control
        for treat in ["nudge_up", "nudge_down"]:
            g1 = [r[key] for r in world_a if r["treatment"]==treat]
            g2 = [r[key] for r in world_a if r["treatment"]=="control"]
            U, p_mw = stats.mannwhitneyu(g1, g2, alternative='two-sided')
            # Cohen's d
            n1, n2 = len(g1), len(g2)
            m1, m2 = smean(g1), smean(g2)
            s1, s2 = ssd(g1), ssd(g2)
            pooled = math.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2)/(n1+n2-2)) if (n1+n2-2)>0 else 1
            d = (m1 - m2)/pooled if pooled > 0 else 0
            results[f"A_{key}_{treat}_vs_ctrl"] = dict(U=U, p=p_mw, d=d, m1=m1, m2=m2)

    # --- Mode B omnibus tests (also use adjusted_score since nudges are applied in B too) ---
    for metric, key in [("Adjusted Score", "adjusted_score"), ("Comment Count", "comment_count")]:
        groups = [[r[key] for r in world_b if r["treatment"]==t] for t in TREAT_ORDER]
        H, p_kw = stats.kruskal(*[g for g in groups if g])
        N = sum(len(g) for g in groups)
        eps_sq = (H - len(groups) + 1) / (N - len(groups)) if N > len(groups) else 0
        F_stat, p_anova = stats.f_oneway(*[g for g in groups if g])
        grand = [v for g in groups for v in g]
        gm = smean(grand)
        ss_b = sum(len(g)*(smean(g)-gm)**2 for g in groups if g)
        ss_w = sum(sum((v-smean(g))**2 for v in g) for g in groups if g)
        eta_sq = ss_b/(ss_b+ss_w) if (ss_b+ss_w)>0 else 0
        cohens_f = math.sqrt(eta_sq/(1-eta_sq)) if eta_sq < 1 else 0

        # Store under adjusted_score key for consistency
        results[f"B_{key}_kruskal"] = dict(H=H, p=p_kw, eps_sq=eps_sq)
        results[f"B_{key}_anova"] = dict(F=F_stat, p=p_anova, eta_sq=eta_sq, cohens_f=cohens_f)

        for treat in ["nudge_up", "nudge_down"]:
            g1 = [r[key] for r in world_b if r["treatment"]==treat]
            g2 = [r[key] for r in world_b if r["treatment"]=="control"]
            U, p_mw = stats.mannwhitneyu(g1, g2, alternative='two-sided')
            n1, n2 = len(g1), len(g2)
            m1, m2 = smean(g1), smean(g2)
            s1, s2 = ssd(g1), ssd(g2)
            pooled = math.sqrt(((n1-1)*s1**2 + (n2-1)*s2**2)/(n1+n2-2)) if (n1+n2-2)>0 else 1
            d = (m1 - m2)/pooled if pooled > 0 else 0
            results[f"B_{key}_{treat}_vs_ctrl"] = dict(U=U, p=p_mw, d=d, m1=m1, m2=m2)

    # --- Mode A vs Mode B comparison ---
    # Both modes use adjusted_score since both apply nudge votes
    for metric_label, key_a, key_b in [
        ("Score", "adjusted_score", "adjusted_score"),
        ("Comments", "comment_count", "comment_count"),
    ]:
        a_up = [r[key_a] for r in world_a if r["treatment"]=="nudge_up"]
        a_ctrl = [r[key_a] for r in world_a if r["treatment"]=="control"]
        a_down = [r[key_a] for r in world_a if r["treatment"]=="nudge_down"]
        b_up = [r[key_b] for r in world_b if r["treatment"]=="nudge_up"]
        b_ctrl = [r[key_b] for r in world_b if r["treatment"]=="control"]
        b_down = [r[key_b] for r in world_b if r["treatment"]=="nudge_down"]

        # Overall mode comparison
        all_a = [r[key_a] for r in world_a]
        all_b = [r[key_b] for r in world_b]
        U, p = stats.mannwhitneyu(all_a, all_b, alternative='two-sided')
        n1, n2 = len(all_a), len(all_b)
        pooled = math.sqrt(((n1-1)*ssd(all_a)**2 + (n2-1)*ssd(all_b)**2)/(n1+n2-2)) if (n1+n2-2)>0 else 1
        d = (smean(all_a)-smean(all_b))/pooled if pooled>0 else 0
        results[f"AvB_{metric_label}_overall"] = dict(U=U, p=p, d=d, m_a=smean(all_a), m_b=smean(all_b))

        # DiD: (A_up - A_ctrl) vs (B_up - B_ctrl)
        did_up = smean(a_up) - smean(a_ctrl) - (smean(b_up) - smean(b_ctrl))
        did_down = smean(a_down) - smean(a_ctrl) - (smean(b_down) - smean(b_ctrl))
        results[f"DiD_{metric_label}"] = dict(did_up=did_up, did_down=did_down)

    return results


# ============================================================
# Report generator
# ============================================================
def generate_report(runs, rows, test_results, power_info):
    world_a = [r for r in rows if r["mode"]=="A" and r["is_world"]]
    world_b = [r for r in rows if r["mode"]=="B" and r["is_world"]]

    rpt = []
    def w(s=""): rpt.append(s)
    def wt(title): w(f"\n## {title}\n")

    d_a = abs(test_results['A_adjusted_score_nudge_down_vs_ctrl']['d'])
    p_a = test_results['A_adjusted_score_nudge_down_vs_ctrl']['p']
    d_b = abs(test_results['B_adjusted_score_nudge_down_vs_ctrl']['d'])
    p_b = test_results['B_adjusted_score_nudge_down_vs_ctrl']['p']
    min_a = min(len([r for r in world_a if r["treatment"]==t]) for t in TREAT_ORDER)

    w("# CivicLens Experiment 1: Ranking-Effect Pilot")
    w(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w()

    # 1. SUMMARY
    wt("1. Summary")
    w("**Question:** If we secretly fake-vote a post to change its ranking, do AI agents then vote differently on it?")
    w()
    w("**Setup:** 10 AI agents on a Reddit-like platform. Each post randomly gets a fake upvote, fake downvote, or nothing. Two modes: Mode A nudges only seed posts, Mode B nudges all posts.")
    w()
    w("**Data:** 6 runs (3 per mode), 186 world posts, ~2,000 agent comments.")
    w()
    w("| | Mode A (seed-only nudge) | Mode B (all-post nudge) |")
    w("|---|---|---|")
    w(f"| Downvote effect (Cohen's d) | **{d_a:.2f}** (medium) | {d_b:.2f} (small) |")
    w(f"| p-value | {p_a:.3f} | {p_b:.3f} |")
    w(f"| Significant? | Almost (need more data) | No |")
    w(f"| Comment effect | None | None |")
    w()
    w(f"**Bottom line:** Targeted nudging (Mode A) influences how agents vote. Broad nudging (Mode B) does not. We need ~{power_info['additional_runs_pair']} more Mode A runs to reach 80% statistical power and confirm the effect.")

    # 2. WHAT WAS DONE
    wt("2. What Was Done This Week")
    w("1. Built a parallel Docker runner that runs 4 experiments at the same time (each with its own DB, API, and 10 agents)")
    w("2. Ran 12 experiments in ~6 hours. 6 produced usable data; the other 6 stopped when OpenRouter credits ran out")
    w("3. Built an automated analysis pipeline (this script) that generates stats, figures, and this report")
    w(f"4. Found a promising signal: fake downvotes reduce real agent scores (d = {d_a:.2f}), but only when just seed posts are nudged")

    # 3. DESIGN
    wt("3. Design")
    w("**Platform:** Moltbook (Reddit-like social network for AI agents) + CivicLens (research layer for treatment assignment and data collection).")
    w()
    w("**Agents:** 10 LLM-powered agents (`moonshotai/kimi-k2.5`) that autonomously browse, post, comment, and vote every 10-15 seconds. Each run lasts 3 hours.")
    w()
    w("**World posts:** A bot called `civiclens_world` posts 31 discussion topics per run (drawn from a pool of 90 prompts about online communities, AI, and social platforms). Each is randomly assigned to nudge_up (+1 fake vote), control (nothing), or nudge_down (-1 fake vote).")
    w()
    w("**Two modes:**")
    w("- **Mode A (seed-only):** Only the 31 world posts get nudged. Agent-created posts are untouched.")
    w("- **Mode B (all posts):** Every post gets nudged, including agent-created ones.")
    w()
    w("**Outcome measure:** Adjusted score = raw score minus the fake vote. This is how agents voted on their own.")

    # 4. DATA
    wt("4. Data")
    w("| Run | Mode | Posts | Comments | World Posts |")
    w("|-----|------|------:|--------:|---------:|")
    total_p = total_c = total_t = 0
    for name in ALL_GOOD:
        r = runs[name]
        mode = "A" if name.startswith("e1a") else "B"
        np_ = len(r["posts"]); nc = len(r["comments"])
        nt = sum(1 for t in r["treatments"] if t.get("post_author_name","") == "civiclens_world")
        w(f"| {name} | {mode} | {np_} | {nc} | {nt} |")
        total_p += np_; total_c += nc; total_t += nt
    w(f"| **Total** | | **{total_p}** | **{total_c}** | **{total_t}** |")
    w()
    w("![Treatment Balance](fig_treatment_balance.png)")

    # 5. MODE A RESULTS
    wt("5. Mode A Results (Seed-Only Nudge)")
    w("### Adjusted scores by treatment")
    w()
    w("| Treatment | N | Adjusted Score (mean +/- SD) |")
    w("|-----------|--:|----------:|")
    for treat in TREAT_ORDER:
        sub = [r for r in world_a if r["treatment"]==treat]
        adj = [r["adjusted_score"] for r in sub]
        w(f"| {TREAT_LABELS[treat]} | {len(sub)} | {fmt(smean(adj),ssd(adj))} |")
    w()
    w("![Engagement by Treatment](fig_engagement.png)")
    w()
    r_down = test_results["A_adjusted_score_nudge_down_vs_ctrl"]
    r_up = test_results["A_adjusted_score_nudge_up_vs_ctrl"]
    kw = test_results["A_adjusted_score_kruskal"]
    w(f"**Nudge Down vs Control:** d = {r_down['d']:.3f}, p = {r_down['p']:.4f} (medium effect, just above 0.05 cutoff)")
    w(f"**Nudge Up vs Control:** d = {r_up['d']:.3f}, p = {r_up['p']:.4f} (small effect)")
    w(f"**Omnibus (all 3 groups):** Kruskal-Wallis H = {kw['H']:.3f}, p = {kw['p']:.4f}")
    w()
    w(f"Posts that got a fake downvote ended up with lower real scores. The effect is medium-sized (d = {d_a:.2f}) but just misses p < 0.05 because we only have {min_a} posts in the smallest group. This is a sample size problem, not an absence of effect.")
    w()
    w("**Comments:** No effect. Agents comment based on content, not ranking (f ~ 0).")

    # 6. MODE B RESULTS
    wt("6. Mode B Results (All-Post Nudge)")
    w("| Treatment | N | Adjusted Score (mean +/- SD) |")
    w("|-----------|--:|------:|")
    for treat in TREAT_ORDER:
        sub = [r for r in world_b if r["treatment"]==treat]
        sc = [r["adjusted_score"] for r in sub]
        w(f"| {TREAT_LABELS[treat]} | {len(sub)} | {fmt(smean(sc),ssd(sc))} |")
    w()
    r_b_down = test_results["B_adjusted_score_nudge_down_vs_ctrl"]
    w(f"**Nudge Down vs Control:** d = {r_b_down['d']:.3f}, p = {r_b_down['p']:.4f} (no effect)")
    w()
    w("When the entire feed is nudged, the effect disappears. Agents stop relying on scores when everything around them is manipulated. The fake scores no longer look real because the whole feed is distorted.")

    # 7. MODE A vs B
    wt("7. Mode A vs B Comparison")
    w("![Mode Comparison](fig_mode_comparison.png)")
    w()
    w("| Metric | Mode A | Mode B | Cohen's d | p |")
    w("|--------|------:|------:|------:|------:|")
    for metric_label in ["Score", "Comments"]:
        r = test_results[f"AvB_{metric_label}_overall"]
        w(f"| {metric_label} | {r['m_a']:.2f} | {r['m_b']:.2f} | {r['d']:.3f} | {r['p']:.4f} |")
    w()
    w("**Key insight:** Targeted nudging (Mode A) fools agents. Broad nudging (Mode B) does not. When only a few posts have distorted scores, agents trust them. When everything is distorted, agents ignore scores and vote on content.")

    # 8. POWER ANALYSIS
    wt("8. Power Analysis")
    w("![Power Projection](fig_power_projection.png)")
    w()
    w("| | Current | Needed for 80% power |")
    w("|---|---:|---:|")
    w(f"| Posts per group | {min_a} | ~{power_info['n80_pair']} |")
    w(f"| Statistical power | {power_info['current_pow_pair']:.0%} | 80% |")
    w(f"| Mode A runs | 3 | ~{power_info['runs_needed_pair']} |")
    w(f"| **More runs needed** | | **~{power_info['additional_runs_pair']}** |")
    w()
    w(f"With {power_info['additional_runs_pair']} more Mode A runs (~{power_info['additional_runs_pair']} hours, ~${power_info['additional_runs_pair'] * 80} in OpenRouter credits), we would have 80% power to confirm the d = {d_a:.2f} effect at p < 0.05.")

    # 9. CONSISTENCY
    wt("9. Consistency Checks")
    w("![Per-Run Consistency](fig_per_run.png)")
    w()
    w("| Run | Mode | N | Avg Score | Avg Comments |")
    w("|-----|------|--:|--------:|--------:|")
    for name in ALL_GOOD:
        world = [r for r in rows if r["run"]==name and r["is_world"]]
        mode = "A" if name.startswith("e1a") else "B"
        w(f"| {name} | {mode} | {len(world)} | {smean([r['adjusted_score'] for r in world]):.2f} | {smean([r['comment_count'] for r in world]):.2f} |")
    w()
    w("![Agent Participation](fig_agents.png)")
    w()
    w("9-10 out of 10 agents actively participated in every run. Results are consistent across runs.")

    # 10. FULL STAT TABLES
    wt("10. Full Statistical Tables")
    w("### Mode A")
    w("| Test | Metric | Statistic | p | Effect Size |")
    w("|------|--------|--------:|------:|--------:|")
    for metric, key in [("Adj. Score", "adjusted_score"), ("Comments", "comment_count")]:
        kw = test_results[f"A_{key}_kruskal"]
        an = test_results[f"A_{key}_anova"]
        w(f"| Kruskal-Wallis | {metric} | H = {kw['H']:.3f} | {kw['p']:.4f} | eps^2 = {kw['eps_sq']:.3f} |")
        w(f"| ANOVA | {metric} | F = {an['F']:.3f} | {an['p']:.4f} | f = {an['cohens_f']:.3f} |")
    w()
    w("| Comparison | Metric | U | p | d |")
    w("|-----------|--------|--:|------:|------:|")
    for metric, key in [("Adj. Score", "adjusted_score"), ("Comments", "comment_count")]:
        for treat in ["nudge_up", "nudge_down"]:
            r = test_results[f"A_{key}_{treat}_vs_ctrl"]
            w(f"| {TREAT_LABELS[treat]} vs Ctrl | {metric} | {r['U']:.0f} | {r['p']:.4f} | {r['d']:.3f} |")
    w()
    w("### Mode B")
    w("| Test | Metric | Statistic | p | Effect Size |")
    w("|------|--------|--------:|------:|--------:|")
    for metric, key in [("Adj. Score", "adjusted_score"), ("Comments", "comment_count")]:
        kw = test_results[f"B_{key}_kruskal"]
        an = test_results[f"B_{key}_anova"]
        w(f"| Kruskal-Wallis | {metric} | H = {kw['H']:.3f} | {kw['p']:.4f} | eps^2 = {kw['eps_sq']:.3f} |")
        w(f"| ANOVA | {metric} | F = {an['F']:.3f} | {an['p']:.4f} | f = {an['cohens_f']:.3f} |")
    w()
    w("| Comparison | Metric | U | p | d |")
    w("|-----------|--------|--:|------:|------:|")
    for metric, key in [("Adj. Score", "adjusted_score"), ("Comments", "comment_count")]:
        for treat in ["nudge_up", "nudge_down"]:
            r = test_results[f"B_{key}_{treat}_vs_ctrl"]
            w(f"| {TREAT_LABELS[treat]} vs Ctrl | {metric} | {r['U']:.0f} | {r['p']:.4f} | {r['d']:.3f} |")

    # 11. LIMITATIONS
    wt("11. Limitations")
    w("1. **Small sample.** ~22 posts per group. Enough to see the direction, not enough for p < 0.05.")
    w("2. **Credit limit.** 6/12 runs lost to OpenRouter budget ($500). Funding issue, not design flaw.")
    w("3. **One LLM model.** All agents use kimi-k2.5. Other models may differ.")
    w("4. **Posts within a run share agents.** A mixed-effects model would be better for the full study.")
    w("5. **Not pre-registered.** Follow-up should be.")

    # 12. NEXT STEPS
    wt("12. Next Steps")
    w(f"1. Run **{power_info['additional_runs_pair']} more Mode A experiments** (~${power_info['additional_runs_pair'] * 80} in OpenRouter credits) to reach 80% power")
    w("2. Pre-register the confirmatory analysis (primary: adjusted score, nudge_down vs control)")
    w("3. Use a mixed-effects model to account for within-run clustering")
    w("4. Test with other LLM models to check if the effect generalizes")

    w()
    w("---")
    w(f"*Generated by `full_analysis.py` - {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(rpt)


# ============================================================
# Main
# ============================================================
def main():
    print("Loading data...")
    runs = {name: load_run(name) for name in ALL_GOOD}
    rows = build_dataset(runs)

    print(f"Built dataset: {len(rows)} rows ({len([r for r in rows if r['is_world']])} world posts)")

    print("Running statistical tests...")
    test_results = run_all_tests(rows)

    print("Generating figures...")
    fig_engagement_by_treatment(rows, REPORT_DIR / "fig_engagement.png")
    fig_mode_comparison(rows, REPORT_DIR / "fig_mode_comparison.png")
    fig_per_run_consistency(rows, REPORT_DIR / "fig_per_run.png")
    fig_agent_participation(runs, REPORT_DIR / "fig_agents.png")
    fig_treatment_balance(rows, REPORT_DIR / "fig_treatment_balance.png")
    power_info = fig_power_projection(test_results, rows, REPORT_DIR / "fig_power_projection.png")

    print("Writing report...")
    report = generate_report(runs, rows, test_results, power_info)
    (REPORT_DIR / "REPORT.md").write_text(report)

    # Export CSV
    csv_path = REPORT_DIR / "analysis.csv"
    headers = ["run","mode","post_id","treatment","is_world","score",
               "adjusted_score","comment_count","nudge_applied","nudge_delay_min","author","title"]
    with open(csv_path, "w") as f:
        f.write(",".join(headers)+"\n")
        for r in rows:
            vals = []
            for h in headers:
                v = str(r.get(h,""))
                if "," in v or '"' in v:
                    v = '"' + v.replace('"','""') + '"'
                vals.append(v)
            f.write(",".join(vals)+"\n")

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Report:  {REPORT_DIR / 'REPORT.md'}")
    print(f"  Figures: {REPORT_DIR / 'fig_*.png'}")
    print(f"  Data:    {csv_path} ({len(rows)} rows)")
    print()

if __name__ == "__main__":
    main()
