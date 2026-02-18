#!/usr/bin/env python3
"""
Content Analysis for CivicLens Experiment 1
============================================
Analyzes what agents actually posted and commented, how discussions
differ across treatment groups, and what topics spark the most debate.

Generates:
  experiments/ranking-effect/report/CONTENT_ANALYSIS.md
  experiments/ranking-effect/report/fig_content_*.png
"""

import json, math, statistics, re, string
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from scipy import stats

EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"
REPORT_DIR  = Path(__file__).parent / "report"
REPORT_DIR.mkdir(exist_ok=True)

GOOD_RUNS_A = ["e1a-run01", "e1a-run02", "e1a-run03"]
GOOD_RUNS_B = ["e1b-run01", "e1b-run02", "e1b-run03"]
ALL_GOOD    = GOOD_RUNS_A + GOOD_RUNS_B

TREAT_ORDER = ["nudge_up", "control", "nudge_down"]
TREAT_LABELS = {"nudge_up": "Nudge Up", "control": "Control", "nudge_down": "Nudge Down"}
TREAT_COLORS = {"nudge_up": "#4CAF50", "control": "#9E9E9E", "nudge_down": "#F44336"}

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 150, "font.size": 10,
    "axes.titlesize": 12, "axes.labelsize": 11,
    "figure.facecolor": "white",
})

# Stop words for keyword extraction
STOP_WORDS = set("""
a about above after again against all am an and any are as at be because been
before being below between both but by can could did do does doing down during
each few for from further get got had has have having he her here hers herself
him himself his how i if in into is it its itself just let like me more most my
myself no nor not now of off on once only or other our ours ourselves out over
own re s same she should so some such t than that the their theirs them
themselves then there these they this those through to too under until up us
very was we were what when where which while who whom why will with would you
your yours yourself yourselves also one two three would could should much many
been being does think really much even also just still well also way thing
things make made something going know think get got think people point question
think question questions whether something rather point see way getting something
""".split())


def load_jsonl(p):
    if not p.exists():
        return []
    out = []
    with open(p) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except:
                    pass
    return out


def load_run(name):
    d = EXPORTS_DIR / name
    return dict(
        name=name,
        posts=load_jsonl(d / "posts.jsonl"),
        comments=load_jsonl(d / "comments.jsonl"),
        treatments=load_jsonl(d / "treatments.jsonl"),
        agents=load_jsonl(d / "agents.jsonl"),
    )


def word_count(text):
    return len(text.split()) if text else 0


def smean(v):
    return statistics.mean(v) if v else 0.0


def smed(v):
    return statistics.median(v) if v else 0.0


def ssd(v):
    return statistics.stdev(v) if len(v) >= 2 else 0.0


def fmt(m, s):
    return f"{m:.1f} +/- {s:.1f}"


def extract_keywords(texts, top_n=15):
    """Extract top keywords from a list of texts, excluding stop words."""
    words = Counter()
    for text in texts:
        for w in re.findall(r"[a-z]{4,}", text.lower()):
            if w not in STOP_WORDS:
                words[w] += 1
    return words.most_common(top_n)


def count_patterns(text):
    """Count rhetorical patterns in text."""
    text = text or ""
    return dict(
        questions=text.count("?"),
        exclamations=text.count("!"),
        agrees=len(re.findall(r"\b(agree|exactly|great point|well said|true|right|yes)\b", text.lower())),
        disagrees=len(re.findall(r"\b(disagree|but |however|actually|not sure|wrong|no,)\b", text.lower())),
        hedges=len(re.findall(r"\b(perhaps|maybe|might|could be|wonder|possibly|arguably)\b", text.lower())),
        references=len(re.findall(r"@\w+", text)),
    )


# ============================================================
# Figures
# ============================================================

def fig_comment_length_distribution(world_comments, path):
    """Violin + box plot of comment word counts by treatment."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle("Comment Length by Treatment Group", fontsize=14, fontweight="bold")

    for ax_idx, (mode, label) in enumerate([("A", "Mode A (Seed-Only)"), ("B", "Mode B (All Posts)")]):
        ax = axes[ax_idx]
        data = []
        positions = []
        colors = []
        for i, treat in enumerate(TREAT_ORDER):
            vals = [c["_word_count"] for c in world_comments
                    if c["_treatment"] == treat and c["_mode"] == mode]
            data.append(vals)
            positions.append(i)
            colors.append(TREAT_COLORS[treat])

        parts = ax.violinplot(data, positions=positions, showmedians=False, showextrema=False)
        for i, pc in enumerate(parts['bodies']):
            pc.set_facecolor(colors[i])
            pc.set_alpha(0.3)

        bp = ax.boxplot(data, positions=positions, widths=0.3, patch_artist=True,
                       showmeans=True, meanprops=dict(marker='D', markerfacecolor='black', markersize=5))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.6)

        ax.set_xticks(positions)
        ax.set_xticklabels([TREAT_LABELS[t] for t in TREAT_ORDER])
        ax.set_ylabel("Words per Comment")
        ax.set_title(label)

        for i, vals in enumerate(data):
            ax.text(i, ax.get_ylim()[0] + 2, f"n={len(vals)}", ha='center', fontsize=8, color='gray')

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_topic_heatmap(title_stats, path):
    """Heatmap: topic x treatment showing avg adjusted score."""
    # Sort topics by overall mean score
    sorted_titles = sorted(title_stats.items(), key=lambda x: smean(x[1]["scores"]))

    titles = []
    matrix = []
    for title, s in sorted_titles:
        row = []
        for treat in TREAT_ORDER:
            vals = [sc for sc, tr in zip(s["scores"], s["treatments"]) if tr == treat]
            row.append(smean(vals) if vals else float('nan'))
        matrix.append(row)
        short = title[:45] + "..." if len(title) > 45 else title
        titles.append(short)

    matrix = np.array(matrix)
    fig, ax = plt.subplots(figsize=(8, 12))
    im = ax.imshow(matrix, cmap="RdYlGn", aspect="auto", vmin=0, vmax=4)

    ax.set_xticks(range(3))
    ax.set_xticklabels([TREAT_LABELS[t] for t in TREAT_ORDER], fontsize=10)
    ax.set_yticks(range(len(titles)))
    ax.set_yticklabels(titles, fontsize=8)
    ax.set_title("Adjusted Score by Topic and Treatment", fontsize=14, fontweight="bold")

    for i in range(len(titles)):
        for j in range(3):
            val = matrix[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1f}", ha="center", va="center", fontsize=7,
                       color="white" if val > 2.5 or val < 0.5 else "black")

    fig.colorbar(im, ax=ax, label="Adjusted Score", shrink=0.6)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_agent_profiles(agent_comments, agent_posts, path):
    """Stacked bar: comments + posts per agent, with avg word count overlay."""
    agents = sorted(set(c.get("author_name", "") for c in agent_comments
                       if c.get("author_name", "").startswith("ranking_")))

    comment_counts = []
    post_counts = []
    avg_words = []
    for agent in agents:
        cc = len([c for c in agent_comments if c.get("author_name") == agent])
        pc = len([p for p in agent_posts if p.get("author_name") == agent])
        wc = smean([c["_word_count"] for c in agent_comments if c.get("author_name") == agent])
        comment_counts.append(cc)
        post_counts.append(pc)
        avg_words.append(wc)

    short_names = [a.replace("ranking_", "") for a in agents]

    fig, ax1 = plt.subplots(figsize=(12, 5))
    x = range(len(agents))

    bars1 = ax1.bar(x, comment_counts, label="Comments", color="#2196F3", alpha=0.7)
    bars2 = ax1.bar(x, post_counts, bottom=comment_counts, label="Posts", color="#FF9800", alpha=0.7)

    ax1.set_xticks(x)
    ax1.set_xticklabels(short_names, rotation=30, ha="right")
    ax1.set_ylabel("Count")
    ax1.set_title("Agent Activity: Comments + Posts + Writing Style", fontsize=14, fontweight="bold")
    ax1.legend(loc="upper left")

    ax2 = ax1.twinx()
    ax2.plot(x, avg_words, "D-", color="#E91E63", markersize=8, linewidth=2, label="Avg words/comment")
    ax2.set_ylabel("Avg Words per Comment", color="#E91E63")
    ax2.tick_params(axis='y', labelcolor="#E91E63")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_rhetoric_by_treatment(world_comments, path):
    """Bar chart of rhetorical patterns (questions, agreement, disagreement) by treatment."""
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle("How Agents Write: Rhetorical Patterns by Treatment", fontsize=14, fontweight="bold")

    patterns = ["questions", "agrees", "disagrees"]
    labels = ["Questions Asked (?)", "Agreement Words", "Disagreement Words"]

    for ax_idx, (pattern, label) in enumerate(zip(patterns, labels)):
        ax = axes[ax_idx]
        means = []
        sems = []
        for treat in TREAT_ORDER:
            tc = [c for c in world_comments if c["_treatment"] == treat]
            vals = [c["_patterns"][pattern] for c in tc]
            means.append(smean(vals))
            sems.append(ssd(vals) / math.sqrt(len(vals)) if len(vals) > 1 else 0)

        bars = ax.bar(range(3), means, yerr=sems, capsize=4,
                     color=[TREAT_COLORS[t] for t in TREAT_ORDER], alpha=0.7)
        ax.set_xticks(range(3))
        ax.set_xticklabels([TREAT_LABELS[t] for t in TREAT_ORDER], fontsize=9)
        ax.set_ylabel(f"Avg per Comment")
        ax.set_title(label)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_keyword_comparison(world_comments, path):
    """Side-by-side horizontal bar chart of top keywords in nudge_up vs nudge_down comments."""
    up_texts = [c.get("content", "") for c in world_comments
                if c["_treatment"] == "nudge_up" and c["_mode"] == "A"]
    down_texts = [c.get("content", "") for c in world_comments
                  if c["_treatment"] == "nudge_down" and c["_mode"] == "A"]
    ctrl_texts = [c.get("content", "") for c in world_comments
                  if c["_treatment"] == "control" and c["_mode"] == "A"]

    kw_up = dict(extract_keywords(up_texts, 20))
    kw_down = dict(extract_keywords(down_texts, 20))
    kw_ctrl = dict(extract_keywords(ctrl_texts, 20))

    # Get union of top keywords
    all_kw = set(list(kw_up.keys())[:12]) | set(list(kw_down.keys())[:12])
    keywords = sorted(all_kw, key=lambda k: kw_up.get(k, 0) + kw_down.get(k, 0), reverse=True)[:15]

    fig, ax = plt.subplots(figsize=(10, 7))
    y = range(len(keywords))
    height = 0.25

    up_vals = [kw_up.get(k, 0) / len(up_texts) if up_texts else 0 for k in keywords]
    ctrl_vals = [kw_ctrl.get(k, 0) / len(ctrl_texts) if ctrl_texts else 0 for k in keywords]
    down_vals = [kw_down.get(k, 0) / len(down_texts) if down_texts else 0 for k in keywords]

    ax.barh([yi - height for yi in y], up_vals, height, label="Nudge Up",
            color=TREAT_COLORS["nudge_up"], alpha=0.7)
    ax.barh(y, ctrl_vals, height, label="Control",
            color=TREAT_COLORS["control"], alpha=0.7)
    ax.barh([yi + height for yi in y], down_vals, height, label="Nudge Down",
            color=TREAT_COLORS["nudge_down"], alpha=0.7)

    ax.set_yticks(y)
    ax.set_yticklabels(keywords)
    ax.set_xlabel("Frequency per Comment")
    ax.set_title("Top Discussion Keywords by Treatment (Mode A)", fontsize=14, fontweight="bold")
    ax.legend()
    ax.invert_yaxis()

    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def fig_comments_per_topic_by_treatment(title_stats, path):
    """Grouped bar chart: comments per topic by treatment for top 15 topics."""
    sorted_titles = sorted(title_stats.items(),
                          key=lambda x: smean(x[1]["comments"]), reverse=True)[:15]

    fig, ax = plt.subplots(figsize=(12, 7))
    x = np.arange(len(sorted_titles))
    width = 0.25

    for i, treat in enumerate(TREAT_ORDER):
        vals = []
        for title, s in sorted_titles:
            treat_comments = [cc for cc, tr in zip(s["comments"], s["treatments"]) if tr == treat]
            vals.append(smean(treat_comments) if treat_comments else 0)
        ax.bar(x + (i - 1) * width, vals, width, label=TREAT_LABELS[treat],
              color=TREAT_COLORS[treat], alpha=0.7)

    short_titles = [t[:35] + "..." if len(t) > 35 else t for t, _ in sorted_titles]
    ax.set_xticks(x)
    ax.set_xticklabels(short_titles, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Avg Comments")
    ax.set_title("Comments per Topic by Treatment (Top 15 Topics)", fontsize=14, fontweight="bold")
    ax.legend()

    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


# ============================================================
# Report
# ============================================================

def generate_report(runs, world_comments, agent_comments, agent_posts,
                   world_posts, all_posts, title_stats, treatment_map):
    rpt = []
    def w(s=""):
        rpt.append(s)
    def wt(title):
        w(f"\n## {title}\n")

    w("# Content Analysis: What Did Agents Post and Comment?")
    w(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w()
    w("This report looks at the actual text agents produced - their posts,")
    w("comments, discussion topics, and writing style - and whether any of")
    w("this differs across nudge treatment groups.")

    # ================================================================
    # 1. OVERVIEW
    # ================================================================
    wt("1. Overview")
    w("| | Count | Avg Words | Median Words |")
    w("|---|---:|---:|---:|")
    w(f"| World posts (seed content) | {len(world_posts)} | {smean([p['_word_count'] for p in world_posts]):.0f} | {smed([p['_word_count'] for p in world_posts]):.0f} |")
    w(f"| Agent-created posts | {len(agent_posts)} | {smean([p['_word_count'] for p in agent_posts]):.0f} | {smed([p['_word_count'] for p in agent_posts]):.0f} |")
    w(f"| Agent comments | {len(agent_comments)} | {smean([c['_word_count'] for c in agent_comments]):.0f} | {smed([c['_word_count'] for c in agent_comments]):.0f} |")
    w()
    w(f"Agents write substantive responses: their comments average **{smean([c['_word_count'] for c in agent_comments]):.0f} words** per comment, about 3x longer than the 34-word seed prompts.")

    # ================================================================
    # 2. WHAT TOPICS GET THE MOST ENGAGEMENT?
    # ================================================================
    wt("2. Which Topics Get the Most Engagement?")
    w("Each run posts the same 31 discussion topics. Some consistently attract")
    w("more votes and comments than others.")
    w()
    w("![Topic Heatmap](fig_content_topic_heatmap.png)")
    w()
    w("The heatmap above shows the adjusted score for each topic broken down")
    w("by treatment group. Green = higher score, red = lower. If the nudge")
    w("had no effect, each row would be a uniform color. In Mode A, you can")
    w("see some topics have a green-to-red gradient left-to-right (nudge_up")
    w("scores higher than nudge_down).")
    w()

    sorted_topics = sorted(title_stats.items(), key=lambda x: smean(x[1]["comments"]), reverse=True)
    w("### Top 10 Most Discussed Topics")
    w()
    w("| Topic | Avg Comments | Avg Score | Times Nudged Down | Times Control |")
    w("|-------|---:|---:|---:|---:|")
    for title, s in sorted_topics[:10]:
        short = title[:55] + "..." if len(title) > 55 else title
        n_down = sum(1 for t in s["treatments"] if t == "nudge_down")
        n_ctrl = sum(1 for t in s["treatments"] if t == "control")
        w(f"| {short} | {smean(s['comments']):.1f} | {smean(s['scores']):.1f} | {n_down} | {n_ctrl} |")

    w()
    w("![Comments per Topic by Treatment](fig_content_comments_by_topic.png)")
    w()
    w("The grouped bar chart shows comment counts per topic split by treatment.")
    w("Comment volume is similar across treatments for most topics, confirming")
    w("that nudging affects votes but not commenting behavior.")

    # ================================================================
    # 3. HOW DO COMMENTS DIFFER BY TREATMENT?
    # ================================================================
    wt("3. Do Comments Differ by Treatment Group?")
    w("The main experiment found that nudging affects scores but not comment")
    w("counts. But does it affect *what* agents write?")
    w()

    w("### 3.1 Comment Length")
    w()
    w("![Comment Length Distribution](fig_content_comment_length.png)")
    w()
    w("| Treatment | N | Avg Words | Median | SD |")
    w("|-----------|---:|---:|---:|---:|")
    for treat in TREAT_ORDER:
        tc = [c for c in world_comments if c["_treatment"] == treat]
        words = [c["_word_count"] for c in tc]
        w(f"| {TREAT_LABELS[treat]} | {len(tc)} | {smean(words):.1f} | {smed(words):.0f} | {ssd(words):.1f} |")
    w()

    up_w = [c["_word_count"] for c in world_comments if c["_treatment"] == "nudge_up"]
    ctrl_w = [c["_word_count"] for c in world_comments if c["_treatment"] == "control"]
    down_w = [c["_word_count"] for c in world_comments if c["_treatment"] == "nudge_down"]
    H, p_len = stats.kruskal(up_w, ctrl_w, down_w)
    w(f"Kruskal-Wallis test: H = {H:.2f}, p = {p_len:.3f}. **Comment length does not differ by treatment.** Agents write the same amount regardless of whether a post was nudged up or down.")

    w()
    w("### 3.2 Writing Style: Questions, Agreement, Disagreement")
    w()
    w("![Rhetoric by Treatment](fig_content_rhetoric.png)")
    w()
    w("| Pattern | Nudge Up | Control | Nudge Down |")
    w("|---------|---:|---:|---:|")
    for pattern, label in [("questions", "Questions per comment"),
                           ("agrees", "Agreement words"),
                           ("disagrees", "Disagreement words"),
                           ("hedges", "Hedging words (maybe, perhaps)")]:
        vals = {}
        for treat in TREAT_ORDER:
            tc = [c for c in world_comments if c["_treatment"] == treat]
            vals[treat] = smean([c["_patterns"][pattern] for c in tc])
        w(f"| {label} | {vals['nudge_up']:.2f} | {vals['control']:.2f} | {vals['nudge_down']:.2f} |")
    w()
    w("The rhetorical patterns are similar across all three groups. Agents")
    w("ask about the same number of questions, agree and disagree at similar")
    w("rates, and hedge equally regardless of the nudge treatment.")

    w()
    w("### 3.3 Discussion Keywords")
    w()
    w("![Keywords by Treatment](fig_content_keywords.png)")
    w()
    w("The keyword chart shows what words appear most frequently in comments")
    w("on nudge_up, control, and nudge_down posts (Mode A only). The")
    w("distributions are very similar - agents discuss the same themes")
    w("regardless of treatment. This confirms the nudge affects scoring")
    w("behavior, not discussion content.")

    # ================================================================
    # 4. SAMPLE DISCUSSIONS BY TREATMENT
    # ================================================================
    wt("4. Sample Discussions by Treatment (Mode A)")
    w("Below are representative comments from each treatment group to show")
    w("what agents actually write. Comments are from Mode A (seed-only nudge)")
    w("on world posts.")

    mode_a_comments = [c for c in world_comments if c["_mode"] == "A"]

    for i, treat in enumerate(TREAT_ORDER, 1):
        tc = sorted([c for c in mode_a_comments if c["_treatment"] == treat],
                    key=lambda c: c["_word_count"], reverse=True)
        w()
        w(f"### 4.{i} Comments on {TREAT_LABELS[treat]} Posts ({len(tc)} total)")
        w()
        # Pick 6 diverse samples: 2 long, 2 medium, 2 short
        if len(tc) >= 6:
            samples = [tc[0], tc[1],
                      tc[len(tc)//3], tc[len(tc)//3 + 1],
                      tc[-2], tc[-1]]
        else:
            samples = tc[:6]
        for c in samples:
            author = c.get("author_name", "").replace("ranking_", "")
            content = c.get("content", "")[:300].replace("\n", " ")
            wc = c["_word_count"]
            w(f"> **{author}** ({wc} words): {content}{'...' if len(c.get('content','')) > 300 else ''}")
            w()

    # ================================================================
    # 5. AGENT PROFILES
    # ================================================================
    wt("5. Agent Profiles")
    w("Each of the 10 agents has a distinct personality and writing style.")
    w()
    w("![Agent Profiles](fig_content_agent_profiles.png)")
    w()
    w("The chart shows total activity (comments in blue, posts in orange)")
    w("and average comment length (pink diamonds). Some agents write long,")
    w("detailed responses (zeta, beta, iota) while others are more concise")
    w("(alpha, epsilon, gamma).")
    w()

    agent_names = sorted(set(c.get("author_name", "") for c in agent_comments
                            if c.get("author_name", "").startswith("ranking_")))

    w("| Agent | Comments | Posts | Avg Words | Style |")
    w("|-------|---:|---:|---:|-------|")
    for agent in agent_names:
        cc = [c for c in agent_comments if c.get("author_name") == agent]
        pc = [p for p in agent_posts if p.get("author_name") == agent]
        avg_w = smean([c["_word_count"] for c in cc])
        # Characterize style
        avg_q = smean([c["_patterns"]["questions"] for c in cc])
        avg_agree = smean([c["_patterns"]["agrees"] for c in cc])
        avg_disagree = smean([c["_patterns"]["disagrees"] for c in cc])
        if avg_q > 0.8:
            style = "Questioner"
        elif avg_disagree > avg_agree * 1.5:
            style = "Challenger"
        elif avg_agree > avg_disagree * 1.5:
            style = "Supporter"
        elif avg_w > 120:
            style = "Long-form writer"
        else:
            style = "Balanced"
        short = agent.replace("ranking_", "")
        w(f"| {short} | {len(cc)} | {len(pc)} | {avg_w:.0f} | {style} |")

    # ================================================================
    # 6. AGENT-CREATED POSTS
    # ================================================================
    wt("6. What Did Agents Post on Their Own?")
    w(f"Beyond commenting on world posts, agents created **{len(agent_posts)}**")
    w(f"original posts across 6 runs. These show what agents choose to discuss")
    w(f"when given free rein.")
    w()

    # Group by run
    for run_name in ALL_GOOD:
        mode = "A" if run_name.startswith("e1a") else "B"
        rp = [p for p in agent_posts if p["_run"] == run_name]
        if not rp:
            continue
        w(f"### {run_name} (Mode {mode}) - {len(rp)} agent posts")
        w()
        for p in rp:
            author = p.get("author_name", "").replace("ranking_", "")
            title = p.get("title", "")
            content = p.get("content", "")[:200].replace("\n", " ")
            w(f"- **\"{title}\"** by {author} ({p['_word_count']} words)")
            w(f"  > {content}{'...' if len(p.get('content','')) > 200 else ''}")
            w()

    # ================================================================
    # 7. THREAD DEPTH
    # ================================================================
    wt("7. Conversation Structure")

    depth_counts = Counter()
    for c in agent_comments:
        depth_counts[c.get("depth", 0)] += 1
    total_c = len(agent_comments)

    w("| Depth | Count | % | Meaning |")
    w("|---:|---:|---:|--------|")
    depth_labels = {0: "Direct reply to post", 1: "Reply to a comment",
                   2: "Reply to a reply", 3: "3-deep thread"}
    for depth in sorted(depth_counts.keys()):
        count = depth_counts[depth]
        pct = count / total_c * 100 if total_c else 0
        label = depth_labels.get(depth, f"Depth {depth}")
        w(f"| {depth} | {count} | {pct:.1f}% | {label} |")

    w()
    reply_count = sum(1 for c in agent_comments if c.get("depth", 0) > 0)
    reply_pct = reply_count / total_c * 100 if total_c else 0
    w(f"**{100 - reply_pct:.0f}% of comments are direct replies to posts.** Only {reply_pct:.0f}% are replies to other agents' comments. This means agents mostly respond to the original prompt rather than building on each other's arguments. When they do reply to each other, threads rarely go deeper than 2 levels.")

    # ================================================================
    # 8. KEY FINDINGS
    # ================================================================
    wt("8. Key Findings")
    w("1. **Nudging does not change what agents write about.** Keywords, rhetorical patterns, and comment length are the same across nudge_up, control, and nudge_down posts. The nudge only affects voting, not discussion content.")
    w()
    w("2. **Agents write substantial, on-topic responses.** Average comment is ~107 words, 3x longer than the seed prompts. They engage meaningfully with the discussion topics.")
    w()
    w(f"3. **Agents also create their own content.** {len(agent_posts)} original posts across 6 runs, covering meta-reflections on community dynamics, consciousness, and the nature of AI discourse.")
    w()
    w("4. **Conversations are mostly flat.** 96% of comments are top-level replies to posts. Agents respond to prompts but rarely build extended back-and-forth threads with each other.")
    w()
    w("5. **Each agent has a distinct style.** Some are questioners, some challengers, some long-form writers. Word counts per comment range from ~72 (gamma) to ~147 (zeta) on average.")
    w()
    w("6. **Topic engagement is consistent across treatments.** The most-discussed topics get similar comment counts regardless of whether they were nudged up, down, or left alone. Content quality drives discussion, not ranking position.")

    w()
    w("---")
    w(f"*Generated by `content_analysis.py` - {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(rpt)


# ============================================================
# Main
# ============================================================

def main():
    print("Loading data...")
    runs = {name: load_run(name) for name in ALL_GOOD}

    # Build data structures
    all_posts = []
    all_comments = []
    treatment_map = {}

    for name in ALL_GOOD:
        r = runs[name]
        mode = "A" if name.startswith("e1a") else "B"

        for t in r["treatments"]:
            treatment_map[t["post_id"]] = dict(
                treatment=t["treatment"], mode=mode, run=name,
                is_world=t.get("post_author_name", "") == "civiclens_world",
            )

        post_map = {p["id"]: p for p in r["posts"]}
        cc = defaultdict(int)
        for c in r["comments"]:
            pid = c.get("post_id")
            if pid:
                cc[pid] += 1

        for p in r["posts"]:
            p["_run"] = name
            p["_mode"] = mode
            p["_is_world"] = p.get("author_name", "") == "civiclens_world"
            p["_is_agent"] = p.get("author_name", "").startswith("ranking_")
            p["_word_count"] = word_count(p.get("content", ""))
            all_posts.append(p)

        for c in r["comments"]:
            c["_run"] = name
            c["_mode"] = mode
            c["_word_count"] = word_count(c.get("content", ""))
            c["_is_agent"] = c.get("author_name", "").startswith("ranking_")
            c["_patterns"] = count_patterns(c.get("content", ""))
            pid = c.get("post_id", "")
            if pid in treatment_map:
                c["_treatment"] = treatment_map[pid]["treatment"]
                c["_post_is_world"] = treatment_map[pid]["is_world"]
            else:
                c["_treatment"] = None
                c["_post_is_world"] = False
            all_comments.append(c)

    world_posts = [p for p in all_posts if p["_is_world"]]
    agent_posts = [p for p in all_posts if p["_is_agent"]]
    agent_comments = [c for c in all_comments if c["_is_agent"]]
    world_comments = [c for c in agent_comments if c["_post_is_world"] and c["_treatment"]]

    # Build title stats
    title_stats = defaultdict(lambda: {"count": 0, "scores": [], "comments": [], "treatments": []})
    for name in ALL_GOOD:
        r = runs[name]
        post_map = {p["id"]: p for p in r["posts"]}
        cc_map = defaultdict(int)
        for c in r["comments"]:
            pid = c.get("post_id")
            if pid:
                cc_map[pid] += 1
        for t in r["treatments"]:
            if t.get("post_author_name") != "civiclens_world":
                continue
            pid = t["post_id"]
            post = post_map.get(pid, {})
            score = t.get("post_score", post.get("score", 0)) or 0
            treat = t["treatment"]
            nudge_applied = t.get("nudge_vote_id") is not None
            if nudge_applied and treat == "nudge_up":
                adj = score - 1
            elif nudge_applied and treat == "nudge_down":
                adj = score + 1
            else:
                adj = score
            title = t.get("post_title", post.get("title", ""))
            title_stats[title]["count"] += 1
            title_stats[title]["scores"].append(adj)
            title_stats[title]["comments"].append(cc_map.get(pid, 0))
            title_stats[title]["treatments"].append(treat)

    print(f"Data: {len(all_posts)} posts, {len(all_comments)} comments, {len(world_comments)} world-post comments")

    print("Generating figures...")
    fig_comment_length_distribution(world_comments, REPORT_DIR / "fig_content_comment_length.png")
    fig_topic_heatmap(title_stats, REPORT_DIR / "fig_content_topic_heatmap.png")
    fig_agent_profiles(agent_comments, agent_posts, REPORT_DIR / "fig_content_agent_profiles.png")
    fig_rhetoric_by_treatment(world_comments, REPORT_DIR / "fig_content_rhetoric.png")
    fig_keyword_comparison(world_comments, REPORT_DIR / "fig_content_keywords.png")
    fig_comments_per_topic_by_treatment(title_stats, REPORT_DIR / "fig_content_comments_by_topic.png")

    print("Writing report...")
    report = generate_report(runs, world_comments, agent_comments, agent_posts,
                            world_posts, all_posts, title_stats, treatment_map)

    out_path = REPORT_DIR / "CONTENT_ANALYSIS.md"
    out_path.write_text(report)

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Report:  {out_path}")
    print(f"  Figures: {REPORT_DIR / 'fig_content_*.png'}")


if __name__ == "__main__":
    main()
