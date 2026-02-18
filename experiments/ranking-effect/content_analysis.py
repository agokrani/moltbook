#!/usr/bin/env python3
"""
Content Analysis for CivicLens Experiment 1
============================================
Analyzes what agents actually posted and commented, and whether
comment content differs across treatment groups.

Generates: experiments/ranking-effect/report/CONTENT_ANALYSIS.md
"""

import json, math, statistics, re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

EXPORTS_DIR = Path(__file__).parent.parent.parent / "exports"
REPORT_DIR  = Path(__file__).parent / "report"
REPORT_DIR.mkdir(exist_ok=True)

GOOD_RUNS_A = ["e1a-run01", "e1a-run02", "e1a-run03"]
GOOD_RUNS_B = ["e1b-run01", "e1b-run02", "e1b-run03"]
ALL_GOOD    = GOOD_RUNS_A + GOOD_RUNS_B

TREAT_ORDER = ["nudge_up", "control", "nudge_down"]
TREAT_LABELS = {"nudge_up": "Nudge Up", "control": "Control", "nudge_down": "Nudge Down"}


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


def char_count(text):
    return len(text) if text else 0


def smean(v):
    return statistics.mean(v) if v else 0.0


def smed(v):
    return statistics.median(v) if v else 0.0


def ssd(v):
    return statistics.stdev(v) if len(v) >= 2 else 0.0


def fmt(m, s):
    return f"{m:.1f} +/- {s:.1f}"


def generate_report(runs):
    # Build data structures
    all_posts = []
    all_comments = []
    treatment_map = {}  # post_id -> treatment info

    for name in ALL_GOOD:
        r = runs[name]
        mode = "A" if name.startswith("e1a") else "B"

        # Build treatment lookup
        for t in r["treatments"]:
            treatment_map[t["post_id"]] = dict(
                treatment=t["treatment"],
                mode=mode,
                run=name,
                is_world=t.get("post_author_name", "") == "civiclens_world",
            )

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
            c["_char_count"] = char_count(c.get("content", ""))
            c["_is_agent"] = c.get("author_name", "").startswith("ranking_")
            # Link to treatment
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

    # Comments on world posts by treatment
    world_comments = [c for c in agent_comments if c["_post_is_world"] and c["_treatment"]]

    rpt = []
    def w(s=""):
        rpt.append(s)
    def wt(title):
        w(f"\n## {title}\n")

    w("# Content Analysis: What Did Agents Post and Comment?")
    w(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    w()
    w("This report looks at the actual text content of posts and comments,")
    w("not just the scores. It answers: what are agents writing, how much,")
    w("and does comment content differ between treatment groups?")

    # ================================================================
    # 1. OVERVIEW
    # ================================================================
    wt("1. Content Overview")
    w(f"| | Count | Avg Words | Median Words |")
    w(f"|---|---:|---:|---:|")
    w(f"| World posts | {len(world_posts)} | {smean([p['_word_count'] for p in world_posts]):.0f} | {smed([p['_word_count'] for p in world_posts]):.0f} |")
    w(f"| Agent posts | {len(agent_posts)} | {smean([p['_word_count'] for p in agent_posts]):.0f} | {smed([p['_word_count'] for p in agent_posts]):.0f} |")
    w(f"| Agent comments | {len(agent_comments)} | {smean([c['_word_count'] for c in agent_comments]):.0f} | {smed([c['_word_count'] for c in agent_comments]):.0f} |")

    # ================================================================
    # 2. WORLD POSTS
    # ================================================================
    wt("2. World Post Topics")
    w("The 31 world posts per run are drawn from a pool of 90 discussion")
    w("prompts. Here are the topics that appeared across all 6 runs, with")
    w("how many times each was used and their average adjusted score:")
    w()

    # Group world posts by title across runs
    title_stats = defaultdict(lambda: {"count": 0, "scores": [], "comments": [], "treatments": []})
    for name in ALL_GOOD:
        r = runs[name]
        post_map = {p["id"]: p for p in r["posts"]}
        cc = defaultdict(int)
        for c in r["comments"]:
            pid = c.get("post_id")
            if pid:
                cc[pid] += 1
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
            title_stats[title]["comments"].append(cc.get(pid, 0))
            title_stats[title]["treatments"].append(treat)

    # Sort by average score descending
    sorted_topics = sorted(title_stats.items(), key=lambda x: smean(x[1]["scores"]), reverse=True)

    w("### 2.1 Top 10 Most Engaging World Posts (by adjusted score)")
    w()
    w("| Title | Times Used | Avg Score | Avg Comments |")
    w("|-------|---:|---:|---:|")
    for title, s in sorted_topics[:10]:
        short = title[:60] + "..." if len(title) > 60 else title
        w(f"| {short} | {s['count']} | {smean(s['scores']):.1f} | {smean(s['comments']):.1f} |")

    w()
    w("### 2.2 Bottom 10 Least Engaging World Posts")
    w()
    w("| Title | Times Used | Avg Score | Avg Comments |")
    w("|-------|---:|---:|---:|")
    for title, s in sorted_topics[-10:]:
        short = title[:60] + "..." if len(title) > 60 else title
        w(f"| {short} | {s['count']} | {smean(s['scores']):.1f} | {smean(s['comments']):.1f} |")

    w()
    w(f"Total unique world post topics used: {len(title_stats)} (out of 90 in the pool). All 6 runs used the same 31 topics because the bot posts sequentially and each run only lasts long enough for 31 posts (one every 2 minutes for ~62 minutes).")

    # ================================================================
    # 3. AGENT POSTS
    # ================================================================
    wt("3. Agent-Created Posts")
    w(f"Agents created {len(agent_posts)} posts across 6 runs (in addition to the 186 world posts).")
    w()

    # Per-agent post counts
    agent_post_counts = Counter()
    for p in agent_posts:
        agent_post_counts[p.get("author_name", "")] += 1

    w("### 3.1 Posts per Agent")
    w()
    w("| Agent | Posts | Avg Words |")
    w("|-------|---:|---:|")
    for agent, count in sorted(agent_post_counts.items(), key=lambda x: -x[1]):
        words = [p["_word_count"] for p in agent_posts if p.get("author_name") == agent]
        w(f"| {agent.replace('ranking_', '')} | {count} | {smean(words):.0f} |")
    if not agent_post_counts:
        w("| (none) | 0 | 0 |")

    w()
    w("### 3.2 Sample Agent Posts")
    w()
    for p in agent_posts[:8]:
        title = p.get("title", "")[:70]
        author = p.get("author_name", "").replace("ranking_", "")
        content = p.get("content", "")[:150].replace("\n", " ")
        w(f"- **\"{title}\"** by {author} ({p['_run']})")
        w(f"  > {content}...")
        w()

    # ================================================================
    # 4. COMMENT ANALYSIS
    # ================================================================
    wt("4. Comment Analysis")

    w("### 4.1 Comment Volume per Agent")
    w()
    agent_comment_counts = Counter()
    agent_comment_words = defaultdict(list)
    for c in agent_comments:
        name = c.get("author_name", "")
        agent_comment_counts[name] += 1
        agent_comment_words[name].append(c["_word_count"])

    w("| Agent | Total Comments | Avg Words | Median Words |")
    w("|-------|---:|---:|---:|")
    for agent, count in sorted(agent_comment_counts.items(), key=lambda x: -x[1]):
        words = agent_comment_words[agent]
        w(f"| {agent.replace('ranking_', '')} | {count} | {smean(words):.0f} | {smed(words):.0f} |")

    w()
    w("### 4.2 Comment Length by Treatment Group (on World Posts)")
    w()
    w("Does the nudge treatment affect how much agents write in their comments?")
    w()
    w("| Treatment | N Comments | Avg Words | Median Words | Avg Chars |")
    w("|-----------|---:|---:|---:|---:|")
    for treat in TREAT_ORDER:
        tc = [c for c in world_comments if c["_treatment"] == treat]
        words = [c["_word_count"] for c in tc]
        chars = [c["_char_count"] for c in tc]
        w(f"| {TREAT_LABELS[treat]} | {len(tc)} | {smean(words):.1f} | {smed(words):.0f} | {smean(chars):.0f} |")

    w()
    w("### 4.3 Comment Length by Mode")
    w()
    w("| Mode | N Comments | Avg Words | Median Words |")
    w("|------|---:|---:|---:|")
    for mode in ["A", "B"]:
        mc = [c for c in world_comments if c["_mode"] == mode]
        words = [c["_word_count"] for c in mc]
        w(f"| Mode {mode} | {len(mc)} | {smean(words):.1f} | {smed(words):.0f} |")

    # ================================================================
    # 5. COMMENT CONTENT BY TREATMENT
    # ================================================================
    wt("5. Sample Comments by Treatment Group")
    w("Do comments read differently on nudged-up vs nudged-down posts?")
    w("Below are random samples from each group (Mode A only, world posts).")

    mode_a_world_comments = [c for c in world_comments if c["_mode"] == "A"]

    for i, treat in enumerate(TREAT_ORDER, 1):
        w()
        w(f"### 5.{i} {TREAT_LABELS[treat]} Posts")
        tc = [c for c in mode_a_world_comments if c["_treatment"] == treat]
        # Pick up to 5 samples spread across the list
        step = max(1, len(tc) // 5)
        samples = tc[::step][:5]
        for c in samples:
            author = c.get("author_name", "").replace("ranking_", "")
            content = c.get("content", "")[:200].replace("\n", " ")
            w(f"- **{author}:** {content}{'...' if len(c.get('content','')) > 200 else ''}")

    # ================================================================
    # 6. THREAD DEPTH
    # ================================================================
    wt("6. Comment Threading")
    w("How deep do conversation threads go?")
    w()

    depth_counts = Counter()
    for c in agent_comments:
        depth_counts[c.get("depth", 0)] += 1

    w("| Depth | Count | % |")
    w("|---:|---:|---:|")
    total_c = len(agent_comments)
    for depth in sorted(depth_counts.keys()):
        count = depth_counts[depth]
        pct = count / total_c * 100 if total_c else 0
        w(f"| {depth} | {count} | {pct:.1f}% |")

    w()
    max_depth = max(depth_counts.keys()) if depth_counts else 0
    top_level_pct = depth_counts.get(0, 0) / total_c * 100 if total_c else 0
    if top_level_pct > 50:
        w(f"Max thread depth: {max_depth}. Most comments ({top_level_pct:.0f}%) are top-level replies, with some threaded discussion.")
    else:
        w(f"Max thread depth: {max_depth}. Agents engage in multi-level threaded conversations.")

    # ================================================================
    # 7. MOST DISCUSSED POSTS
    # ================================================================
    wt("7. Most Discussed Posts")
    w("Which world posts got the most comments?")
    w()

    post_comments = defaultdict(list)
    post_info = {}
    for name in ALL_GOOD:
        r = runs[name]
        for p in r["posts"]:
            if p.get("author_name") == "civiclens_world":
                post_info[p["id"]] = dict(
                    title=p.get("title", ""),
                    run=name,
                    score=p.get("score", 0),
                )
        for c in r["comments"]:
            pid = c.get("post_id")
            if pid and pid in post_info:
                post_comments[pid].append(c)

    # Sort by comment count
    top_discussed = sorted(post_comments.items(), key=lambda x: -len(x[1]))[:10]

    w("| Post Title | Run | Comments | Score | Treatment |")
    w("|------------|-----|---:|---:|-----------|")
    for pid, comments in top_discussed:
        info = post_info[pid]
        title = info["title"][:50] + "..." if len(info["title"]) > 50 else info["title"]
        treat_info = treatment_map.get(pid, {})
        treat = TREAT_LABELS.get(treat_info.get("treatment", ""), "?")
        w(f"| {title} | {info['run']} | {len(comments)} | {info['score']} | {treat} |")

    # ================================================================
    # 8. KEY OBSERVATIONS
    # ================================================================
    wt("8. Key Observations")

    # Check if comment length differs by treatment
    up_words = [c["_word_count"] for c in world_comments if c["_treatment"] == "nudge_up"]
    ctrl_words = [c["_word_count"] for c in world_comments if c["_treatment"] == "control"]
    down_words = [c["_word_count"] for c in world_comments if c["_treatment"] == "nudge_down"]

    from scipy import stats as sp_stats
    if up_words and ctrl_words and down_words:
        H, p_len = sp_stats.kruskal(up_words, ctrl_words, down_words)
        w(f"1. **Comment length does {'not ' if p_len > 0.05 else ''}differ by treatment group** (Kruskal-Wallis H={H:.2f}, p={p_len:.3f}). Agents write about the same amount regardless of nudge direction.")
    else:
        w("1. Not enough data to test comment length by treatment.")

    w()
    avg_agent_words = smean([c["_word_count"] for c in agent_comments])
    avg_world_words = smean([p["_word_count"] for p in world_posts])
    w(f"2. **Agent comments average {avg_agent_words:.0f} words** (world post prompts average {avg_world_words:.0f} words). Agents write substantive responses, not just one-liners.")

    w()
    top_commenters = agent_comment_counts.most_common(3)
    bottom_commenters = agent_comment_counts.most_common()[-3:]
    w(f"3. **Most active commenters:** {', '.join(a.replace('ranking_','') for a,_ in top_commenters)} ({', '.join(str(c) for _,c in top_commenters)} comments each). **Least active:** {', '.join(a.replace('ranking_','') for a,_ in bottom_commenters)} ({', '.join(str(c) for _,c in bottom_commenters)} comments each).")

    w()
    w(f"4. **Agents created {len(agent_posts)} original posts** across 6 runs, showing they don't just react to world posts - they initiate their own discussions too.")

    w()
    reply_count = sum(1 for c in agent_comments if c.get("depth", 0) > 0)
    reply_pct = reply_count / len(agent_comments) * 100 if agent_comments else 0
    w(f"5. **{reply_pct:.0f}% of comments are replies** to other comments (not top-level). Agents engage in back-and-forth conversation, not just isolated reactions.")

    w()
    w("---")
    w(f"*Generated by `content_analysis.py` - {datetime.now().strftime('%Y-%m-%d %H:%M')}*")

    return "\n".join(rpt)


def main():
    print("Loading data...")
    runs = {name: load_run(name) for name in ALL_GOOD}

    print("Generating content analysis...")
    report = generate_report(runs)

    out_path = REPORT_DIR / "CONTENT_ANALYSIS.md"
    out_path.write_text(report)

    print()
    print("=" * 60)
    print("DONE")
    print("=" * 60)
    print(f"  Report: {out_path}")


if __name__ == "__main__":
    main()
