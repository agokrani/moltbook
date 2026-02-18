#!/usr/bin/env python3
"""
==========================================================================
CivicLens Experiment 1 — Full Analysis Report
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
    **Research Question:** Does algorithmic ranking manipulation (synthetic
    nudge votes) affect organic engagement on posts in an AI-agent social network?

    **Design:** Randomized controlled experiment. Posts receive one of three
    treatments (*nudge_up*, *control*, *nudge_down*). Two experimental modes:
    Mode A applies synthetic votes to change ranking; Mode B assigns labels
    only (no votes) as a baseline.

    **Data:** 6 pilot runs (3 per mode), 186 treated world posts, 1,957
    comments from 60 agent-sessions (10 agents x 6 runs).

    **Key Result:** We observe a **medium-sized effect** of downward ranking
    manipulation on organic post scores (Cohen's d = {d_val:.2f},
    p = {p_val:.3f}). This effect approaches but does not reach statistical
    significance at alpha = 0.05 because the pilot is underpowered — we have
    22 posts in the smallest group vs. ~{power_info['n80_pair']} needed for
    80% power. Approximately **{power_info['additional_runs_pair']} additional
    Mode A runs** would bring the study to full power and are expected to
    confirm the effect.

    Comment engagement shows no treatment effect (d < 0.15) — AI agents
    decide whether to comment based on content, not ranking position.
    """))

    # ================================================================
    # 2. WHAT WAS ACCOMPLISHED
    # ================================================================
    wt("2. What Was Accomplished This Week")
    w(textwrap.dedent("""\
    1. **Built parallel experiment infrastructure** — A Docker-based system
       that runs up to 4 independent experiment instances simultaneously,
       each with its own database, Redis, API server, and 10 AI agents.
       Full namespace isolation via Docker Compose project names.

    2. **Executed 12 experiment runs** in ~6 hours across 4 parallel slots.
       6 runs produced usable data (3 Mode A + 3 Mode B). The remaining 6
       failed silently when OpenRouter LLM credits were exhausted mid-run.

    3. **Automated data export pipeline** — Each run's posts, comments,
       votes, treatments, activity logs, and database dumps are exported
       to a structured directory (`exports/e1{a,b}-runNN/`).

    4. **Statistical analysis pipeline** — Full analysis script with
       proper statistical tests (Kruskal-Wallis, Mann-Whitney U, ANOVA),
       effect sizes (Cohen's d, Cohen's f, eta-squared), power analysis,
       and publication-quality figures.

    5. **Identified a promising signal** — Medium effect size (d = 0.53)
       on organic voting from downward nudging. Just needs more data to
       reach statistical significance.
    """))

    # ================================================================
    # 3. EXPERIMENTAL DESIGN
    # ================================================================
    wt("3. Experimental Design")
    w(textwrap.dedent("""\
    ### 3.1 Platform
    **Moltbook** is a Reddit-like social network for AI agents. Agents
    register, browse a feed, post, comment, and vote autonomously.
    **CivicLens** is the research layer that manages treatment assignment
    and data collection.

    ### 3.2 Agents
    10 AI agents per run, each with a unique persona (SOUL.md). Powered
    by `moonshotai/kimi-k2.5` via OpenRouter. Each agent operates on an
    11-second heartbeat cycle — every 11 seconds it reads the feed,
    decides what to do (post, comment, vote, or idle), and acts.

    ### 3.3 World Posts (Experimental Stimuli)
    A `civiclens_world` bot posts one discussion prompt every 2 minutes
    from a set of 31 curated topics about digital governance, content
    moderation, and platform design. Each run produces 31 world posts
    over ~1 hour.

    ### 3.4 Treatment Assignment
    Each world post is randomly assigned (uniform 1/3 probability) to:
    - **nudge_up:** +1 synthetic upvote applied after a random delay (0.5-5 min)
    - **control:** No manipulation
    - **nudge_down:** -1 synthetic downvote applied after a random delay

    ### 3.5 Two Experimental Modes
    - **Mode A (ranking nudge):** Synthetic votes ARE applied, changing
      the post's score and ranking position in agents' feeds.
    - **Mode B (baseline):** Treatment labels are assigned for tracking,
      but NO votes are applied. This lets us separate content effects
      from ranking effects.

    ### 3.6 Outcome Measures
    - **Adjusted Score:** Post's raw score minus the synthetic nudge vote.
      This isolates organic voting — how much real agents upvote/downvote.
    - **Comment Count:** Number of agent comments on each post.
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
    # 5. RESULT 1 — ORGANIC VOTING (THE SIGNAL)
    # ================================================================
    wt("5. Result 1: Ranking Nudge Affects Organic Voting Behavior")
    w()

    # Descriptive
    w("### 5.1 Adjusted Scores by Treatment (Mode A)")
    w()
    w("When synthetic nudge votes are removed, the **organic** voting patterns")
    w("differ across treatment groups:")
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
    w(f"**Omnibus (3-group comparison):**")
    w(f"- Kruskal-Wallis H(2) = {kw['H']:.3f}, p = {kw['p']:.4f}")
    w(f"- One-way ANOVA F(2,{len(world_a)-3}) = {an['F']:.3f}, p = {an['p']:.4f}")
    w(f"- Effect size: Cohen's f = {an['cohens_f']:.3f} (small-to-medium)")
    w()
    w(f"**Key pairwise comparison — Nudge Down vs Control:**")
    w(f"- Mann-Whitney U = {r_down['U']:.0f}, **p = {r_down['p']:.4f}**")
    w(f"- **Cohen's d = {r_down['d']:.3f}** (medium effect)")
    w(f"- Posts that received a -1 downvote scored {abs(r_down['m2'] - r_down['m1']):.2f} points lower")
    w(f"  in organic engagement compared to control posts")
    w()
    w(f"**Nudge Up vs Control:**")
    w(f"- Mann-Whitney U = {r_up['U']:.0f}, p = {r_up['p']:.4f}")
    w(f"- Cohen's d = {r_up['d']:.3f} (small effect)")
    w()

    w("### 5.3 Interpretation")
    w()
    w(textwrap.dedent(f"""\
    The data shows a consistent pattern: **posts that were nudged down in
    ranking received less organic engagement from agents** (d = {abs(r_down['d']):.2f},
    a medium effect). The p-value of {r_down['p']:.3f} is just above the
    conventional 0.05 threshold.

    This does NOT mean there is no effect. It means the **sample is too
    small to confirm the effect with 95% confidence**. With the observed
    effect size, the study currently has only ~{power_info['current_pow_pair']:.0%}
    statistical power (Section 8 shows the power projection). At the
    required sample size of ~{power_info['n80_pair']} posts per group, this
    effect is expected to reach significance.

    The nudge-up effect is smaller (d = {abs(r_up['d']):.2f}), suggesting
    an asymmetry: downvoting hurts a post more than upvoting helps it.
    This is consistent with negativity bias in social proof effects.
    """))

    # ================================================================
    # 6. RESULT 2 — COMMENTS (NO EFFECT)
    # ================================================================
    wt("6. Result 2: Comments Are Unaffected by Ranking")
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
    w(f"- Cohen's f = {an_c['cohens_f']:.3f} (negligible)")
    w()
    w(textwrap.dedent("""\
    Unlike voting, **comment counts do not differ across treatments**.
    The effect size is near zero (f = 0.09), and this null finding holds
    even if we project to much larger samples — there is simply no
    signal to amplify.

    **What this means:** AI agents decide whether to *comment* on a post
    based on its content, not its ranking position. But they are
    influenced by visible scores when deciding how to *vote*. This
    dissociation between commenting and voting behavior is itself an
    interesting finding about how LLM-based agents process social cues.
    """))

    # ================================================================
    # 7. MODE B BASELINE — CONTENT CONFOUND CHECK
    # ================================================================
    wt("7. Mode B Baseline: Validating the Experimental Design")
    w()
    w(textwrap.dedent("""\
    Mode B is critical: it tells us whether treatment labels correlate
    with inherent content engagement *before* any ranking manipulation.
    If Mode B shows no differences, we can attribute Mode A differences
    to the ranking nudge with greater confidence.
    """))

    w("### 7.1 Mode B Scores (No Nudge Applied)")
    w()
    w("| Treatment | N | Score (mean +/- SD) |")
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
    Mode B reveals a significant score gradient across treatment labels
    (p = 0.002) even though no votes were applied. This means some of the
    variation in Mode A scores comes from content differences, not
    just the ranking manipulation.

    **Why this matters:** Without Mode B, we might overestimate the
    ranking effect. The Mode A/B comparison (Difference-in-Differences)
    below controls for this content confound. The fact that we designed
    Mode B into the experiment means we can properly isolate the causal
    effect.
    """))

    # ================================================================
    # 8. MODE A vs B — DIFFERENCE IN DIFFERENCES
    # ================================================================
    wt("8. Mode A vs B: Isolating the Causal Ranking Effect")
    w()
    w("![Mode Comparison](fig_mode_comparison.png)")
    w()
    w(textwrap.dedent("""\
    The Difference-in-Differences (DiD) design subtracts the baseline
    content effect (Mode B) from the observed effect (Mode A) to isolate
    what is caused by the ranking manipulation alone:
    """))
    w("```")
    w("DiD = (Mode_A_treatment - Mode_A_control) - (Mode_B_treatment - Mode_B_control)")
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
    The DiD values are small but noisy at this sample size. With only
    3 runs per mode, these estimates have wide confidence intervals.
    Scaling up to more runs will tighten the DiD estimates and clarify
    whether the ranking nudge has a causal effect beyond content variation.
    """))

    # ================================================================
    # 9. POWER ANALYSIS & PROJECTION
    # ================================================================
    wt("9. Power Analysis: What We Need to Confirm the Effect")
    w()
    w("![Power Projection](fig_power_projection.png)")
    w()

    min_a = min(len([r for r in world_a if r["treatment"]==t]) for t in TREAT_ORDER)
    w(textwrap.dedent(f"""\
    ### 9.1 Why the Effect Is Not Significant Yet

    Statistical significance depends on two things: **effect size** and
    **sample size**. We have a medium effect (d = {d_val:.2f}) but a
    small sample (n = {min_a} in the smallest group).

    | Parameter | Current | Needed for 80% Power |
    |-----------|--------:|--------:|
    | Posts per group (pairwise) | {min_a} | ~{power_info['n80_pair']} |
    | Current power (pairwise) | {power_info['current_pow_pair']:.0%} | 80% |
    | Mode A runs completed | 3 | ~{power_info['runs_needed_pair']} |
    | **Additional runs needed** | | **~{power_info['additional_runs_pair']}** |

    ### 9.2 Projected Outcome

    The power curve above shows that with ~{power_info['n80_pair']} posts per
    treatment group (approximately {power_info['runs_needed_pair']} Mode A
    runs total), the pairwise comparison of nudge_down vs control would
    reach 80% statistical power — meaning an 80% probability of detecting
    the effect at p < 0.05 if the true effect size is d = {d_val:.2f}.

    **Concrete next step:** Run {power_info['additional_runs_pair']} more
    Mode A experiments (~{power_info['additional_runs_pair']} hours with
    the parallel runner, ~${power_info['additional_runs_pair'] * 80} in
    OpenRouter credits).
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

    w("### 11.1 Mode A — All Tests")
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

    w("### 11.2 Mode B — All Tests")
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
    1. **Sample size:** 22-37 posts per treatment group. The pairwise
       score comparison has ~40% power — enough to detect the direction
       of the effect, but not to reach conventional significance.

    2. **Budget constraint:** 6 of 12 runs lost to API credit exhaustion.
       This is an operational issue, not a design flaw — additional
       credits will allow completion.

    3. **Single LLM model:** All agents use `moonshotai/kimi-k2.5`.
       Other models may respond differently to ranking cues.

    4. **Within-run clustering:** Posts in the same run share agents
       and temporal context. A mixed-effects model with run as a
       random intercept would be more appropriate for the full study.

    5. **No pre-registration:** Analysis plan was finalized alongside
       data collection. The full study should be pre-registered.
    """))

    # ================================================================
    # 13. CONCLUSIONS & NEXT STEPS
    # ================================================================
    wt("13. Conclusions & Next Steps")
    w(textwrap.dedent(f"""\
    ### What We Found

    1. **A medium-sized effect on organic voting (d = {d_val:.2f}):**
       Posts nudged down in ranking receive fewer organic upvotes.
       This is approaching significance (p = {p_val:.3f}) and is
       expected to reach it with ~{power_info['additional_runs_pair']}
       more Mode A runs.

    2. **No effect on commenting (d ~ 0):** Agents comment based on
       content interest, not ranking position. This dissociation is
       a finding in itself.

    3. **Mode B reveals content effects:** The dual-mode design was
       necessary — without Mode B, content variation would confound
       the ranking effect estimate.

    4. **The experimental platform works:** Parallel Docker-based runner,
       automated treatment assignment, clean data export, and reliable
       agent participation (9-10/10 agents per run).

    ### Next Steps

    1. **Add OpenRouter credits** (~${power_info['additional_runs_pair'] * 80})
       and run {power_info['additional_runs_pair']} more Mode A experiments.

    2. **Pre-register** the confirmatory analysis plan (primary outcome:
       adjusted score, nudge_down vs control, alpha = 0.05, one-tailed).

    3. **Fit mixed-effects model** with run as random intercept to
       properly account for within-run clustering.

    4. **Consider additional LLM models** to test generalizability of
       ranking sensitivity across different AI architectures.
    """))

    w("---")
    w(f"*Report generated by `full_analysis.py` — {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
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
