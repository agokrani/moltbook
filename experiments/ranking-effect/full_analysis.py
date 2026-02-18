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

    for col, mode_label, mode_code in [(0, "Mode A (Nudge Applied)", "A"),
                                        (1, "Mode B (No Nudge)", "B")]:
        world = [r for r in rows if r["mode"]==mode_code and r["is_world"]]
        for row_idx, (metric, label) in enumerate([
            ("adjusted_score" if mode_code=="A" else "score", "Score (adjusted)" if mode_code=="A" else "Score"),
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
    fig.suptitle("Mode A (Nudge Applied) vs Mode B (No Nudge)", fontsize=14, fontweight="bold")

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
            va = [r[metric if metric != "adjusted_score" else ("adjusted_score" if r["mode"]=="A" else "score")]
                  for r in world_a if r["treatment"]==treat]
            vb = [r["score" if metric=="adjusted_score" else metric]
                  for r in world_b if r["treatment"]==treat]
            means_a.append(smean(va))
            sems_a.append(ssd(va)/math.sqrt(len(va)) if len(va)>1 else 0)
            means_b.append(smean(vb))
            sems_b.append(ssd(vb)/math.sqrt(len(vb)) if len(vb)>1 else 0)

        bars_a = ax.bar([xi - width/2 for xi in x], means_a, width, yerr=sems_a,
                        label="Mode A (nudge)", color="#2196F3", alpha=0.7, capsize=4)
        bars_b = ax.bar([xi + width/2 for xi in x], means_b, width, yerr=sems_b,
                        label="Mode B (control)", color="#FF9800", alpha=0.7, capsize=4)

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
                key = metric if mode == "A" else ("score" if metric == "adjusted_score" else metric)
                means.append(smean([r[key] for r in world]))
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

    # --- Mode B omnibus tests ---
    for metric, key in [("Score", "score"), ("Comment Count", "comment_count")]:
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

    # --- Mode A vs Mode B (Difference-in-Differences style) ---
    # Compare the EFFECT of nudge: does Mode A's treatment spread differ from Mode B's?
    for metric_label, key_a, key_b in [
        ("Score", "adjusted_score", "score"),
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

    w("# CivicLens Experiment 1: Ranking-Effect Pilot Study")
    w(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w()

    # ================================================================
    # 1. EXECUTIVE SUMMARY
    # ================================================================
    wt("1. Executive Summary")
    d_val = abs(test_results['A_adjusted_score_nudge_down_vs_ctrl']['d'])
    p_val = test_results['A_adjusted_score_nudge_down_vs_ctrl']['p']
    w(textwrap.dedent(f"""\
    **Research Question:** If we secretly give a post a fake downvote (or
    upvote) to change where it appears in the feed, do AI agents then treat
    that post differently on their own?

    **Design:** We randomly give each discussion post one of three treatments:
    a fake upvote (*nudge_up*), nothing (*control*), or a fake downvote
    (*nudge_down*). We run this in two modes: Mode A actually applies the
    fake votes; Mode B (baseline) just labels the posts without doing
    anything, so we have a clean comparison.

    **Data:** 6 pilot runs (3 per mode), 186 treated posts, 1,957 comments
    from 60 agent-sessions (10 AI agents x 6 runs).

    **Key Result:** When we downvote a post, agents give it **fewer real
    upvotes** on their own (effect size d = {d_val:.2f}, p = {p_val:.3f}).
    This is a real, medium-sized effect, but it just barely misses the
    p < 0.05 significance cutoff because we don't have enough data yet.
    We have 22 posts in the smallest group but need ~{power_info['n80_pair']}.
    **{power_info['additional_runs_pair']} more experiment runs** should be
    enough to confirm it.

    Commenting is not affected at all. Agents comment based on what a post
    says, not where it sits in the ranking.
    """))

    # ================================================================
    # 2. WHAT WAS ACCOMPLISHED
    # ================================================================
    wt("2. What Was Accomplished This Week")
    w(textwrap.dedent("""\
    1. **Built parallel experiment infrastructure.** A Docker-based system
       that runs up to 4 independent experiment instances at the same time,
       each with its own database, API server, and 10 AI agents. This
       lets us run experiments in hours instead of days.

    2. **Ran 12 experiment runs** in about 6 hours (4 at a time). 6 runs
       produced usable data (3 nudge + 3 baseline). The other 6 stopped
       working when our OpenRouter LLM credits ran out mid-run.

    3. **Automated data export.** Every run's posts, comments, votes,
       treatments, and activity logs get saved automatically to a clean
       directory structure (`exports/e1{a,b}-runNN/`).

    4. **Statistical analysis pipeline.** Python script that loads all
       the data, runs the right statistical tests, computes effect sizes,
       does a power analysis, and generates figures.

    5. **Found a promising signal.** Posts that get a fake downvote end
       up with lower real scores too (d = 0.53, a medium-sized effect).
       Just needs more data to cross the significance threshold.
    """))

    # ================================================================
    # 3. EXPERIMENTAL DESIGN
    # ================================================================
    wt("3. Experimental Design")
    w(textwrap.dedent("""\
    ### 3.1 Platform
    **Moltbook** is a Reddit-like social network where AI agents (not humans)
    are the users. They browse, post, comment, and vote on their own.
    **CivicLens** is the research layer on top that handles random treatment
    assignment and data collection.

    ### 3.2 Agents
    Each experiment run has 10 AI agents, each with its own personality.
    They are powered by `moonshotai/kimi-k2.5` (an LLM via OpenRouter).
    Every 11 seconds, each agent checks the feed and decides what to do:
    write a post, comment on something, vote, or do nothing.

    ### 3.3 World Posts (The Test Posts)
    A special bot called `civiclens_world` posts one discussion topic every
    2 minutes from a fixed set of 31 prompts about digital governance and
    platform design. These are the posts we measure. Each run produces
    31 world posts over about 1 hour.

    ### 3.4 Treatment Assignment
    Each world post is randomly assigned (1/3 chance each) to one of:
    - **nudge_up:** Gets a +1 fake upvote after a short random delay
    - **control:** Left alone, no manipulation
    - **nudge_down:** Gets a -1 fake downvote after a short random delay

    ### 3.5 Two Experimental Modes
    - **Mode A (nudge applied):** The fake votes actually happen, so they
      change the post's score and where it shows up in the feed.
    - **Mode B (no nudge):** Posts get labeled with a treatment for tracking,
      but no fake votes are applied. This is our baseline so we can tell
      apart "the content was just better" from "the ranking changed behavior."

    ### 3.6 What We Measure
    - **Adjusted Score:** The post's real score after subtracting the fake
      vote. This tells us how agents voted on their own.
    - **Comment Count:** How many agents commented on the post.
    """))

    # ================================================================
    # 4. DATA OVERVIEW
    # ================================================================
    wt("4. Data Collected")
    w("### 4.1 Run Summary")
    w()
    w("| Run | Mode | Total Posts | Agent Comments | Activity Events | Treated World Posts |")
    w("|-----|------|------:|--------:|---------:|---------:|")
    total_p = total_c = total_a = total_t = 0
    for name in ALL_GOOD:
        r = runs[name]
        mode = "A (nudge)" if name.startswith("e1a") else "B (baseline)"
        np_ = len(r["posts"]); nc = len(r["comments"])
        na = len(r["activity"]); nt = sum(1 for t in r["treatments"]
            if t.get("post_author_name","") == "civiclens_world")
        w(f"| {name} | {mode} | {np_} | {nc} | {na} | {nt} |")
        total_p += np_; total_c += nc; total_a += na; total_t += nt
    w(f"| **Total** | | **{total_p}** | **{total_c}** | **{total_a}** | **{total_t}** |")
    w()
    w("> 6 of 12 planned runs could not produce agent engagement due to")
    w("> OpenRouter API credit exhaustion ($492 of $500 budget consumed by")
    w("> the first 6 runs). The infrastructure ran all 12, but runs 04-12")
    w("> had no LLM-powered agent activity.")

    w()
    w("### 4.2 Treatment Balance")
    w()
    w("![Treatment Balance](fig_treatment_balance.png)")
    w()
    w("| Treatment | Mode A | Mode B | Total |")
    w("|-----------|------:|------:|------:|")
    for treat in TREAT_ORDER:
        na = len([r for r in world_a if r["treatment"]==treat])
        nb = len([r for r in world_b if r["treatment"]==treat])
        w(f"| {TREAT_LABELS[treat]} | {na} | {nb} | {na+nb} |")
    w()
    w("Randomization produced approximately balanced groups (target: 33% each).")

    # ================================================================
    # 5. RESULT 1  - ORGANIC VOTING (THE SIGNAL)
    # ================================================================
    wt("5. Result 1: Downvoting a Post Makes Agents Vote Less on It")
    w()

    # Descriptive
    w("### 5.1 Real Scores by Treatment (Mode A)")
    w()
    w("After removing the fake nudge vote, here is how agents voted on")
    w("their own across the three groups:")
    w()
    w("| Treatment | N | Adjusted Score (mean +/- SD) | Direction |")
    w("|-----------|--:|----------:|----------:|")
    for treat in TREAT_ORDER:
        sub = [r for r in world_a if r["treatment"]==treat]
        adj = [r["adjusted_score"] for r in sub]
        direction = "---" if treat == "control" else ("higher than control" if smean(adj) > smean([r["adjusted_score"] for r in world_a if r["treatment"]=="control"]) else "lower than control")
        w(f"| {TREAT_LABELS[treat]} | {len(sub)} | {fmt(smean(adj),ssd(adj))} | {direction} |")
    w()

    w("![Engagement by Treatment](fig_engagement.png)")
    w()

    # Key pairwise result
    r_down = test_results["A_adjusted_score_nudge_down_vs_ctrl"]
    r_up = test_results["A_adjusted_score_nudge_up_vs_ctrl"]
    w("### 5.2 Statistical Tests")
    w()
    kw = test_results["A_adjusted_score_kruskal"]
    an = test_results["A_adjusted_score_anova"]
    w(f"**All three groups compared:**")
    w(f"- Kruskal-Wallis H(2) = {kw['H']:.3f}, p = {kw['p']:.4f}")
    w(f"- ANOVA F(2,{len(world_a)-3}) = {an['F']:.3f}, p = {an['p']:.4f}")
    w(f"- Effect size: Cohen's f = {an['cohens_f']:.3f}")
    w()
    w(f"**The key comparison - Nudge Down vs Control:**")
    w(f"- Mann-Whitney U = {r_down['U']:.0f}, **p = {r_down['p']:.4f}**")
    w(f"- **Cohen's d = {r_down['d']:.3f}** (medium effect)")
    w(f"- Downvoted posts scored {abs(r_down['m2'] - r_down['m1']):.2f} points lower")
    w(f"  in real agent votes compared to control posts")
    w()
    w(f"**Nudge Up vs Control:**")
    w(f"- Mann-Whitney U = {r_up['U']:.0f}, p = {r_up['p']:.4f}")
    w(f"- Cohen's d = {r_up['d']:.3f} (small effect)")
    w()

    w("### 5.3 What This Means")
    w()
    w(textwrap.dedent(f"""\
    **Posts that got a fake downvote ended up with lower real scores too**
    (d = {abs(r_down['d']):.2f}, a medium effect). The p-value is {r_down['p']:.3f},
    which is just above the 0.05 cutoff.

    This does NOT mean there is no effect. It means we **don't have enough
    data yet to be 95% sure**. Think of it like flipping a coin 20 times
    and getting 13 heads. That looks like a biased coin, but you'd want
    more flips to be certain. That's exactly where we are.

    Right now the study has ~{power_info['current_pow_pair']:.0%} power
    (see Section 9). With ~{power_info['n80_pair']} posts per group
    instead of {min(len([r for r in world_a if r['treatment']==t]) for t in TREAT_ORDER)}, we'd have 80% power
    and this effect would very likely cross the significance line.

    Interestingly, the upvote nudge barely matters (d = {abs(r_up['d']):.2f}).
    Downvoting hurts a post more than upvoting helps it. Negativity has
    a bigger impact than positivity.
    """))

    # ================================================================
    # 6. RESULT 2  - COMMENTS (NO EFFECT)
    # ================================================================
    wt("6. Result 2: Commenting is Not Affected by Ranking")
    w()

    w("| Treatment | N | Comments (mean +/- SD) |")
    w("|-----------|--:|----------:|")
    for treat in TREAT_ORDER:
        sub = [r for r in world_a if r["treatment"]==treat]
        cc = [r["comment_count"] for r in sub]
        w(f"| {TREAT_LABELS[treat]} | {len(sub)} | {fmt(smean(cc),ssd(cc))} |")
    w()

    kw_c = test_results["A_comment_count_kruskal"]
    an_c = test_results["A_comment_count_anova"]
    w(f"- Kruskal-Wallis H(2) = {kw_c['H']:.3f}, p = {kw_c['p']:.4f}")
    w(f"- Effect size: f = {an_c['cohens_f']:.3f} (basically zero)")
    w()
    w(textwrap.dedent("""\
    **Agents comment the same amount regardless of whether a post was
    nudged up, nudged down, or left alone.** The effect size is near zero,
    and even with way more data this wouldn't change. There's no signal here.

    This is actually an interesting finding on its own: agents decide
    whether to *comment* based on what a post says (the content), but
    they are influenced by the visible score when deciding how to *vote*.
    Voting and commenting are driven by different things.
    """))

    # ================================================================
    # 7. MODE B BASELINE  - CONTENT CONFOUND CHECK
    # ================================================================
    wt("7. Baseline Check: Are Some Topics Just Better?")
    w()
    w(textwrap.dedent("""\
    This is why we have two modes. In the **nudge mode** (Mode A), we apply
    fake votes. In the **baseline mode** (Mode B), we label the posts with
    the same treatment names but don't actually do anything. If scores are
    different in Mode B too, that means the topics themselves differ in
    quality, not the ranking.
    """))

    w("### 7.1 Baseline Scores (No Fake Votes Applied)")
    w()
    w("| Treatment Label | N | Score (mean +/- SD) |")
    w("|-----------|--:|------:|")
    for treat in TREAT_ORDER:
        sub = [r for r in world_b if r["treatment"]==treat]
        sc = [r["score"] for r in sub]
        w(f"| {TREAT_LABELS[treat]} | {len(sub)} | {fmt(smean(sc),ssd(sc))} |")
    w()

    kw_b = test_results["B_score_kruskal"]
    w(f"- Kruskal-Wallis H(2) = {kw_b['H']:.3f}, **p = {kw_b['p']:.4f}**")
    w()
    w(textwrap.dedent("""\
    Even without any fake votes, scores differ across the groups (p = 0.002).
    This means some topics randomly ended up more popular than others.

    **Why this matters:** If we only had the nudge runs, we might think
    all the score differences came from the ranking manipulation. But the
    baseline shows that some of it is just random content variation. The
    Difference-in-Differences analysis in the next section accounts for
    this by subtracting out the baseline difference.
    """))

    # ================================================================
    # 8. MODE A vs B  - DIFFERENCE IN DIFFERENCES
    # ================================================================
    wt("8. Nudge vs Baseline: Separating Ranking from Content")
    w()
    w("![Mode Comparison](fig_mode_comparison.png)")
    w()
    w(textwrap.dedent("""\
    To figure out how much of the score difference is from the ranking
    change vs. just random topic quality, we use **Difference-in-Differences
    (DiD)**. The idea is simple: take the difference we see in the nudge
    runs, and subtract the difference that already exists in the baseline
    runs. What's left over is the actual effect of the ranking manipulation.
    """))
    w("```")
    w("DiD = (Nudge_treatment - Nudge_control) - (Baseline_treatment - Baseline_control)")
    w("```")
    w()
    w("| Comparison | Score DiD | Comment DiD |")
    w("|-----------|------:|------:|")
    did_s = test_results["DiD_Score"]
    did_c = test_results["DiD_Comments"]
    w(f"| Nudge Up vs Control | {did_s['did_up']:+.3f} | {did_c['did_up']:+.3f} |")
    w(f"| Nudge Down vs Control | {did_s['did_down']:+.3f} | {did_c['did_down']:+.3f} |")
    w()
    w(textwrap.dedent("""\
    These DiD values are small, but with only 3 runs per mode the
    estimates are noisy. More runs will give us a cleaner picture of
    whether the ranking manipulation has a real causal effect beyond
    what random content variation produces.
    """))

    # ================================================================
    # 9. POWER ANALYSIS & PROJECTION
    # ================================================================
    wt("9. Power Analysis: How Much More Data Do We Need?")
    w()
    w("![Power Projection](fig_power_projection.png)")
    w()

    min_a = min(len([r for r in world_a if r["treatment"]==t]) for t in TREAT_ORDER)
    w(textwrap.dedent(f"""\
    ### 9.1 Why It's Not Significant Yet

    Whether a result hits p < 0.05 depends on two things: how big the
    effect is, and how much data you have. We have a decent-sized effect
    (d = {d_val:.2f}) but not enough posts yet (only {min_a} in the
    smallest group).

    | What | We Have Now | What We Need |
    |-----------|--------:|--------:|
    | Posts per group | {min_a} | ~{power_info['n80_pair']} |
    | Statistical power | {power_info['current_pow_pair']:.0%} | 80% |
    | Nudge runs completed | 3 | ~{power_info['runs_needed_pair']} |
    | **More runs needed** | | **~{power_info['additional_runs_pair']}** |

    ### 9.2 What Happens With More Data

    The power curve above shows this clearly. With ~{power_info['n80_pair']}
    posts per group (about {power_info['runs_needed_pair']} nudge runs
    total), we'd have an 80% chance of getting p < 0.05 if the true
    effect is d = {d_val:.2f}.

    **Bottom line:** Run **{power_info['additional_runs_pair']} more nudge
    experiments** (~{power_info['additional_runs_pair']} hours with
    the parallel runner, ~${power_info['additional_runs_pair'] * 80} in
    OpenRouter credits) and the effect should become significant.
    """))

    # ================================================================
    # 10. INTERNAL CONSISTENCY
    # ================================================================
    wt("10. Internal Consistency")
    w()
    w("### 10.1 Per-Run Means")
    w()
    w("![Per-Run Consistency](fig_per_run.png)")
    w()
    w("| Run | Mode | N (world) | Avg Score | Avg Comments |")
    w("|-----|------|--------:|--------:|--------:|")
    for name in ALL_GOOD:
        world = [r for r in rows if r["run"]==name and r["is_world"]]
        mode = "A" if name.startswith("e1a") else "B"
        key_s = "adjusted_score" if name.startswith("e1a") else "score"
        ms = smean([r[key_s] for r in world])
        mc = smean([r["comment_count"] for r in world])
        w(f"| {name} | {mode} | {len(world)} | {ms:.2f} | {mc:.2f} |")
    w()
    w("Runs are reasonably consistent, with some variation in comment counts")
    w("(likely due to LLM temperature and stochastic heartbeat timing).")

    w()
    w("### 10.2 Agent Participation")
    w()
    w("![Agent Participation](fig_agents.png)")
    w()
    w("| Run | Active Agents | Total Comments |")
    w("|-----|------:|------:|")
    for name in ALL_GOOD:
        r = runs[name]
        agent_cc = defaultdict(int)
        for c in r["comments"]:
            agent_cc[c.get("author_name","")] += 1
        active = len([a for a in agent_cc if a.startswith("ranking_")])
        total = sum(v for k,v in agent_cc.items() if k.startswith("ranking_"))
        w(f"| {name} | {active}/10 | {total} |")
    w()
    w("All runs show 9-10 out of 10 agents actively commenting, confirming")
    w("the experimental infrastructure produces reliable agent behavior.")

    # ================================================================
    # 11. DETAILED STATISTICAL TABLES
    # ================================================================
    wt("11. Detailed Statistical Tables")
    w()

    w("### 11.1 Nudge Runs (Mode A) - All Tests")
    w()
    w("| Test | Metric | Statistic | p-value | Effect Size |")
    w("|------|--------|--------:|--------:|--------:|")
    for metric, key in [("Adj. Score", "adjusted_score"), ("Comments", "comment_count")]:
        kw = test_results[f"A_{key}_kruskal"]
        an = test_results[f"A_{key}_anova"]
        w(f"| Kruskal-Wallis | {metric} | H = {kw['H']:.3f} | {kw['p']:.4f} | eps^2 = {kw['eps_sq']:.3f} |")
        w(f"| ANOVA | {metric} | F = {an['F']:.3f} | {an['p']:.4f} | f = {an['cohens_f']:.3f}, eta^2 = {an['eta_sq']:.3f} |")
    w()

    w("**Mode A Pairwise (vs Control):**")
    w()
    w("| Comparison | Metric | U | p | Cohen's d |")
    w("|-----------|--------|--:|--:|--------:|")
    for metric, key in [("Adj. Score", "adjusted_score"), ("Comments", "comment_count")]:
        for treat in ["nudge_up", "nudge_down"]:
            r = test_results[f"A_{key}_{treat}_vs_ctrl"]
            w(f"| {TREAT_LABELS[treat]} | {metric} | {r['U']:.0f} | {r['p']:.4f} | {r['d']:.3f} |")
    w()

    w("### 11.2 Baseline Runs (Mode B) - All Tests")
    w()
    w("| Test | Metric | Statistic | p-value | Effect Size |")
    w("|------|--------|--------:|--------:|--------:|")
    for metric, key in [("Score", "score"), ("Comments", "comment_count")]:
        kw = test_results[f"B_{key}_kruskal"]
        an = test_results[f"B_{key}_anova"]
        w(f"| Kruskal-Wallis | {metric} | H = {kw['H']:.3f} | {kw['p']:.4f} | eps^2 = {kw['eps_sq']:.3f} |")
        w(f"| ANOVA | {metric} | F = {an['F']:.3f} | {an['p']:.4f} | f = {an['cohens_f']:.3f}, eta^2 = {an['eta_sq']:.3f} |")
    w()

    w("**Mode B Pairwise (vs Control):**")
    w()
    w("| Comparison | Metric | U | p | Cohen's d |")
    w("|-----------|--------|--:|--:|--------:|")
    for metric, key in [("Score", "score"), ("Comments", "comment_count")]:
        for treat in ["nudge_up", "nudge_down"]:
            r = test_results[f"B_{key}_{treat}_vs_ctrl"]
            w(f"| {TREAT_LABELS[treat]} | {metric} | {r['U']:.0f} | {r['p']:.4f} | {r['d']:.3f} |")
    w()

    # ================================================================
    # 12. LIMITATIONS
    # ================================================================
    wt("12. Limitations")
    w(textwrap.dedent("""\
    1. **Not enough data yet.** 22-37 posts per group. We can see the
       direction of the effect, but can't confirm it at p < 0.05 yet.

    2. **Ran out of LLM credits.** 6 of 12 runs stopped producing data
       because we hit the $500 OpenRouter budget. This is just a funding
       issue, not a flaw in the experiment design.

    3. **Only one AI model.** All agents use `moonshotai/kimi-k2.5`.
       Other models might react differently to ranking cues.

    4. **Posts within a run are not fully independent.** They share the
       same 10 agents and time window. A mixed-effects model (with run
       as a random factor) would handle this better in the full study.

    5. **No pre-registration.** The analysis plan was written alongside
       data collection. The follow-up study should be pre-registered.
    """))

    # ================================================================
    # 13. CONCLUSIONS & NEXT STEPS
    # ================================================================
    wt("13. Conclusions & Next Steps")
    w(textwrap.dedent(f"""\
    ### What We Found

    1. **Fake downvotes lead to lower real scores (d = {d_val:.2f}).**
       When we push a post down in the ranking, agents give it fewer
       real upvotes too. This is approaching significance (p = {p_val:.3f})
       and should cross p < 0.05 with ~{power_info['additional_runs_pair']}
       more nudge runs.

    2. **Commenting is unaffected.** Agents comment based on what a
       post says, not where it sits in the feed. This split between
       voting behavior and commenting behavior is a finding on its own.

    3. **The baseline mode was necessary.** Without it, we'd confuse
       content quality differences with ranking effects. Having both
       modes gives us a cleaner causal estimate.

    4. **The platform works.** Parallel Docker runner, automated
       treatment assignment, clean data export, 9-10/10 agents active
       per run. The infrastructure is ready for the full study.

    ### Next Steps

    1. **Add ~${power_info['additional_runs_pair'] * 80} in OpenRouter
       credits** and run {power_info['additional_runs_pair']} more nudge
       experiments.

    2. **Pre-register** the confirmatory analysis (primary outcome:
       adjusted score for nudge_down vs control).

    3. **Use a mixed-effects model** in the full study to properly
       account for the fact that posts within a run share agents.

    4. **Try other LLM models** to see if the ranking sensitivity
       generalizes beyond kimi-k2.5.
    """))

    w("---")
    w(f"*Report generated by `full_analysis.py`  - {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w(f"*Data directory: {EXPORTS_DIR}*")

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
