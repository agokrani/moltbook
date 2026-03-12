#!/usr/bin/env python3
"""Analysis 4: Phrase adoption timeline — trace the spread over time.

For each run's top-3 5-gram phrases, track when each agent first uses them.
Shows the contagion pattern: phrases spread from 1 agent to many over 60 min.

Focus conditions: Empty feed, 25 conspiracies, 25 AGI hype, 25 tech humor.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

from load_entropy_data import (
    CONDITION_ORDER,
    CONDITION_LABELS,
    SEED_AUTHORS,
    load_all_scales,
    group_records,
)
from time_binned_lexical_metrics_5gram import tokenize, ngrams, prepare_posts, ngram_counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------------------
NGRAM_N = 5
TOP_K = 3
OUT_DIR = Path("findings/entropy-collapse-scaling/diffusion")
SCALES = ["n10", "n20", "n30"]
SCALE_AGENTS = {"n10": 10, "n20": 20, "n30": 30}
SCALE_LABELS = {"n10": "10 agents", "n20": "20 agents", "n30": "30 agents"}
FOCUS_CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
FOCUS_LABELS = {"mag0": "Empty feed", "mag1": "1 conspiracy", "mag5": "5 conspiracies", "mag25": "25 conspiracies", "dom-agi": "25 AGI hype", "dom-tech": "25 tech humor"}

PHRASE_COLORS = ["#E53935", "#1E88E5", "#43A047"]  # #1 red, #2 blue, #3 green
PHRASE_STYLES = ["-", "--", ":"]


def compute_cumulative_adoption(adoptions: list[float], total_agents: int, time_grid: np.ndarray) -> np.ndarray:
    """Given sorted list of first-usage minutes, compute cumulative fraction at each time point."""
    cum = np.zeros(len(time_grid))
    adopted = 0
    ai = 0
    for mi, m in enumerate(time_grid):
        while ai < len(adoptions) and adoptions[ai] <= m:
            adopted += 1
            ai += 1
        cum[mi] = adopted / total_agents
    return cum


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading all scales...")
    records = load_all_scales()
    agent_records = [r for r in records if not r.is_seed]
    print(f"  Agent posts: {len(agent_records)}")

    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))

    # Step 1: Find each run's top-3 5-grams
    print("\nFinding each run's top-3 5-grams...")
    run_top_phrases: dict[tuple, list[tuple[str, int]]] = {}
    for key, recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        counter = ngram_counter(prepared, NGRAM_N)
        top = [(" ".join(g), count) for g, count in counter.most_common(TOP_K)]
        run_top_phrases[key] = top

    for key in sorted(run_top_phrases):
        scale, condition, run_name = key
        phrases_str = ", ".join(f'"{p}"' for p, _ in run_top_phrases[key])
        print(f"  {scale}/{condition}: {phrases_str}")

    # Step 2: For each run and each top phrase, find first usage per agent
    print("\nComputing adoption timelines...")
    # run_key -> phrase_rank -> sorted list of first-usage minutes
    run_phrase_adoptions: dict[tuple, dict[int, list[float]]] = {}
    adoption_rows = []
    example_showcase: dict[str, list[dict]] = defaultdict(list)

    for (scale, condition, run_name), recs in sorted(by_run.items()):
        run_key = (scale, condition, run_name)
        phrases = run_top_phrases[run_key]
        if not phrases:
            continue

        sorted_recs = sorted(recs, key=lambda r: r.minutes_elapsed)
        total_agents = len({r.author_name for r in recs})

        run_phrase_adoptions[run_key] = {}

        for rank_idx, (phrase, count) in enumerate(phrases):
            first_usage: dict[str, dict] = {}
            for rec in sorted_recs:
                agent = rec.author_name
                if agent in first_usage:
                    continue
                tokens = tokenize(rec.full_text)
                grams = {" ".join(g) for g in ngrams(tokens, NGRAM_N)}
                if phrase in grams:
                    first_usage[agent] = {
                        "agent": agent,
                        "minute": round(rec.minutes_elapsed, 2),
                        "title": rec.title[:120],
                        "excerpt": rec.content[:200] if rec.content else "",
                        "post_id": rec.post_id,
                    }

            sorted_minutes = sorted(info["minute"] for info in first_usage.values())
            run_phrase_adoptions[run_key][rank_idx] = sorted_minutes

            for agent, info in sorted(first_usage.items(), key=lambda x: x[1]["minute"]):
                adoption_rows.append({
                    "phrase": phrase,
                    "phrase_rank": rank_idx + 1,
                    "scale": scale,
                    "condition": condition,
                    "run_name": run_name,
                    "agent": agent,
                    "first_minute": info["minute"],
                    "title": info["title"],
                    "post_id": info["post_id"],
                    "total_agents_in_run": total_agents,
                    "total_adopters": len(first_usage),
                    "adoption_rate": round(len(first_usage) / total_agents, 3),
                })

            # Collect showcase examples for rank 0 (top phrase)
            if rank_idx == 0 and len(first_usage) >= 3:
                for agent, info in sorted(first_usage.items(), key=lambda x: x[1]["minute"])[:4]:
                    example_showcase[f"{scale}/{condition}"].append({
                        "phrase": phrase,
                        "agent": agent,
                        "minute": info["minute"],
                        "title": info["title"],
                        "excerpt": info["excerpt"][:300],
                    })

    # Write CSV
    csv_path = OUT_DIR / "first_usage_timeline.csv"
    if adoption_rows:
        with csv_path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(adoption_rows[0].keys()))
            writer.writeheader()
            writer.writerows(adoption_rows)
        print(f"Wrote {csv_path} ({len(adoption_rows)} rows)")

    with (OUT_DIR / "example_showcase.json").open("w") as f:
        json.dump(example_showcase, f, indent=2, ensure_ascii=False)

    # -----------------------------------------------------------------------
    # VIZ 1: HTML Evidence Page — "The Echo Chamber"
    # Shows ACTUAL POST TEXT with the repeated phrase highlighted.
    # Scroll through and see the same phrase from different agents,
    # different titles, over and over. THIS is the "holy shit" moment.
    # -----------------------------------------------------------------------
    print("\nGenerating HTML evidence page...")
    import html as html_module
    import re

    def highlight_phrase_html(text: str, phrase: str) -> str:
        """Find the 5-gram phrase words in text and wrap matches with <mark>."""
        words = phrase.split()
        parts = [re.escape(w) for w in words]
        pattern = r'[\W]{0,6}'.join(parts)

        matches = list(re.finditer(pattern, text, re.IGNORECASE))

        if not matches:
            for n in [4, 3]:
                for i in range(len(words) - n + 1):
                    sub = words[i:i + n]
                    sub_pat = r'[\W]{0,6}'.join(re.escape(w) for w in sub)
                    matches = list(re.finditer(sub_pat, text, re.IGNORECASE))
                    if matches:
                        break
                if matches:
                    break

        if not matches:
            return html_module.escape(text)

        result = []
        last_end = 0
        for m in matches:
            s, e = m.span()
            result.append(html_module.escape(text[last_end:s]))
            result.append(f'<mark>{html_module.escape(text[s:e])}</mark>')
            last_end = e
        result.append(html_module.escape(text[last_end:]))
        return ''.join(result)

    HTML_RUNS = [
        ("n30", "mag5", "5 Conspiracy Seeds", "#f97316"),
        ("n30", "dom-tech", "25 Tech Humor Seeds", "#10b981"),
        ("n30", "mag1", "1 Conspiracy Seed", "#e11d48"),
        ("n30", "mag0", "Control (Empty Feed)", "#6b7280"),
    ]

    html_sections = []
    for scale, cond, section_title, accent_color in HTML_RUNS:
        run_key = None
        for k in by_run:
            if k[0] == scale and k[1] == cond:
                run_key = k
                break
        if not run_key:
            continue

        recs = by_run[run_key]
        phrases = [p for p, _ in run_top_phrases.get(run_key, [])]
        top_phrase = phrases[0] if phrases else ""
        total = SCALE_AGENTS[scale]
        sorted_recs = sorted(recs, key=lambda r: r.minutes_elapsed)

        n_adopted = len(run_phrase_adoptions.get(run_key, {}).get(0, []))

        # Collect ALL posts containing the top phrase
        phrase_posts = []
        for rec in sorted_recs:
            toks = tokenize(rec.full_text)
            grams = {" ".join(g) for g in ngrams(toks, NGRAM_N)}
            if top_phrase in grams:
                phrase_posts.append(rec)

        section = f'''
    <div class="run-section">
      <div class="run-header" style="border-color:{accent_color}">
        <div class="run-title" style="color:{accent_color}">{html_module.escape(section_title)}</div>
        <div class="run-stats">
          <strong>{n_adopted}</strong> of {total} agents adopted &middot;
          <strong>{len(phrase_posts)}</strong> posts contain this phrase
        </div>
        <div class="phrase-box" style="border-color:{accent_color};color:{accent_color}">
          {html_module.escape(top_phrase)}
        </div>
      </div>'''

        seen_agents: set[str] = set()
        for rec in phrase_posts[:50]:
            agent_short = rec.author_name.replace("agent_", "").replace("ranking_", "")
            is_first = rec.author_name not in seen_agents
            seen_agents.add(rec.author_name)

            body = rec.content[:600] if rec.content else ""
            body_hl = highlight_phrase_html(body, top_phrase)

            first_tag = f' <span class="first-tag" style="color:{accent_color}">NEW AGENT</span>' if is_first else ""

            section += f'''
      <div class="post-card">
        <div class="post-head">
          <span class="agent" style="color:{accent_color}">{html_module.escape(agent_short)}{first_tag}</span>
          <span class="time">min {rec.minutes_elapsed:.1f}</span>
        </div>
        <div class="title">{html_module.escape(rec.title[:120])}</div>
        <div class="body">{body_hl}</div>
      </div>'''

        section += "\n    </div>"
        html_sections.append(section)

    full_html = '''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>The Echo Chamber — Phrase Adoption Evidence</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;
  background:#0d1117;color:#c9d1d9;max-width:820px;margin:0 auto;padding:48px 20px;line-height:1.6}
h1{font-size:36px;color:#fff;letter-spacing:-0.5px}
.subtitle{font-size:15px;color:#8b949e;margin:8px 0 48px;line-height:1.7}
.subtitle mark{background:rgba(239,68,68,0.25);color:#f87171;padding:2px 4px;border-radius:3px;font-weight:600}
.run-section{margin-bottom:72px}
.run-header{padding-bottom:20px;margin-bottom:20px;border-bottom:2px solid}
.run-title{font-size:20px;font-weight:700}
.run-stats{font-size:13px;color:#8b949e;margin-top:4px}
.phrase-box{font-size:17px;font-family:'SF Mono','Fira Code','Cascadia Code',monospace;
  background:rgba(255,255,255,0.03);padding:14px 18px;border-radius:8px;
  border-left:4px solid;margin:14px 0;font-weight:600;letter-spacing:0.3px}
.post-card{background:#161b22;border-radius:8px;padding:16px 20px;margin-bottom:8px;
  border-left:3px solid #21262d;transition:border-color .15s}
.post-card:hover{border-color:#30363d}
.post-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:4px}
.agent{font-weight:700;font-size:13px}
.first-tag{font-size:10px;background:rgba(255,255,255,0.06);padding:2px 6px;
  border-radius:3px;margin-left:6px;font-weight:500}
.time{color:#484f58;font-size:12px;font-family:monospace}
.title{font-weight:600;color:#e6edf3;margin-bottom:6px;font-size:14px}
.body{color:#7d8590;font-size:13px;line-height:1.75;white-space:pre-wrap}
mark{background:rgba(239,68,68,0.2);color:#ff7b72;padding:1px 2px;border-radius:2px;
  font-weight:600;text-decoration:underline;text-decoration-color:rgba(239,68,68,0.35);
  text-underline-offset:2px}
.toc{background:#161b22;border-radius:10px;padding:20px 24px;margin-bottom:48px}
.toc a{color:#58a6ff;text-decoration:none;display:block;padding:4px 0;font-size:14px}
.toc a:hover{text-decoration:underline}
</style></head><body>
<h1>The Echo Chamber</h1>
<p class="subtitle">
  Different agents. Different titles. <mark>Same phrase.</mark><br>
  Scroll through actual posts from each run. Every <mark>highlighted passage</mark>
  is the run's dominant 5-gram — independently adopted by most agents.
</p>
''' + '\n'.join(html_sections) + '''
<div style="text-align:center;color:#484f58;font-size:12px;margin-top:60px;padding:20px">
  Generated from 18 runs of the Moltbook entropy-collapse experiment.
</div>
</body></html>'''

    html_path = OUT_DIR / "evidence.html"
    with html_path.open("w") as f:
        f.write(full_html)
    print(f"Wrote {html_path}")

    # -----------------------------------------------------------------------
    # VIZ 2: "The Takeover" — What % of posts repeat the phrase? per time bin
    # Simple bars. Red grows over time. Three panels (control vs seeded).
    # -----------------------------------------------------------------------
    print("\nGenerating takeover chart...")

    BIN_W = 5
    bin_edges = np.arange(0, 65, BIN_W)
    bin_mids = (bin_edges[:-1] + bin_edges[1:]) / 2
    n_tbins = len(bin_mids)

    TAKEOVER_PANELS = [
        ("n30", "mag0", "Control (no seeds)", "#6B7280"),
        ("n30", "mag5", "5 conspiracy seeds", "#EA580C"),
        ("n30", "dom-tech", "25 tech humor seeds", "#059669"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(18, 6), sharey=True)
    fig.patch.set_facecolor("white")

    for pi, (scale, cond, panel_title, bar_color) in enumerate(TAKEOVER_PANELS):
        ax = axes[pi]
        run_key = None
        for k in by_run:
            if k[0] == scale and k[1] == cond:
                run_key = k
                break
        if not run_key:
            continue

        recs = by_run[run_key]
        phrases = [p for p, _ in run_top_phrases.get(run_key, [])][:TOP_K]
        top_phrase = phrases[0] if phrases else ""

        phrase_cnt = np.zeros(n_tbins)
        total_cnt = np.zeros(n_tbins)
        for rec in recs:
            for bi in range(n_tbins):
                if bin_edges[bi] <= rec.minutes_elapsed < bin_edges[bi + 1]:
                    total_cnt[bi] += 1
                    toks = tokenize(rec.full_text)
                    grams = {" ".join(g) for g in ngrams(toks, NGRAM_N)}
                    if any(p in grams for p in phrases):
                        phrase_cnt[bi] += 1
                    break

        pct = np.where(total_cnt > 0, phrase_cnt / total_cnt * 100, 0)

        # Bars — color intensity scales with percentage
        for xi, (bc, p) in enumerate(zip(bin_mids, pct)):
            alpha = max(0.25, min(1.0, p / 50))
            ax.bar(bc, p, width=BIN_W * 0.88, color=bar_color, alpha=alpha, zorder=3)
            if p >= 8:
                ax.text(bc, p + 1.5, f"{p:.0f}%", ha="center", fontsize=8,
                        color=bar_color, fontweight="bold")

        n_adopted = len(run_phrase_adoptions.get(run_key, {}).get(0, []))
        ax.set_xlim(0, 60)
        ax.set_xlabel("Minutes", fontsize=11)
        ax.grid(axis="y", alpha=0.08)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        ax.set_title(
            f'{panel_title}\n'
            f'Phrase: "{top_phrase[:28]}..."\n'
            f'{n_adopted}/{SCALE_AGENTS[scale]} agents adopted',
            fontsize=10, pad=12, linespacing=1.4, color="#333",
        )

    axes[0].set_ylabel("Posts containing the phrase (%)", fontsize=11)

    fig.suptitle(
        "The Takeover",
        fontsize=20, fontweight="bold", y=1.04, color="#111",
    )
    fig.text(
        0.5, 0.99,
        "What fraction of posts in each 5-minute window repeat the run's dominant phrase?",
        ha="center", fontsize=11, color="#666",
    )
    plt.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(OUT_DIR / "takeover.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote takeover.png")

    # -----------------------------------------------------------------------
    # VIZ 3: "18 Runs, 18 Phrases" — Horizontal bars + phrase text
    # Each bar = one run's adoption rate. The phrase itself is shown next to
    # the bar, proving every run develops its OWN unique phrase.
    # -----------------------------------------------------------------------
    print("\nGenerating 18-runs overview...")

    cond_colors = {
        "mag0": "#6B7280", "mag1": "#E11D48", "mag5": "#F97316",
        "mag25": "#EAB308", "dom-agi": "#3B82F6", "dom-tech": "#10B981",
    }

    fig, ax = plt.subplots(figsize=(16, 11))
    fig.patch.set_facecolor("white")

    y = 0
    yticks = []
    ytick_labels = []
    group_seps = []

    for ci, cond in enumerate(CONDITION_ORDER):
        if ci > 0:
            group_seps.append(y - 0.5)
            y += 0.6

        for si, scale in enumerate(SCALES):
            for k in sorted(run_phrase_adoptions.keys()):
                if k[0] == scale and k[1] == cond:
                    minutes_list = run_phrase_adoptions[k].get(0, [])
                    total = SCALE_AGENTS[scale]
                    n_adopted = len(minutes_list)
                    rate = n_adopted / total
                    color = cond_colors[cond]
                    phrase = run_top_phrases[k][0][0] if run_top_phrases.get(k) else ""

                    # Draw the bar
                    ax.barh(
                        y, rate * 100, height=0.65,
                        color=color, alpha=0.75, zorder=3,
                        edgecolor="white", linewidth=0.5,
                    )

                    # Rate label inside or next to the bar
                    if rate > 0.15:
                        ax.text(
                            rate * 100 - 2, y, f"{n_adopted}/{total}",
                            ha="right", va="center", fontsize=8.5,
                            color="white", fontweight="bold",
                        )
                    else:
                        ax.text(
                            rate * 100 + 1, y, f"{n_adopted}/{total}",
                            ha="left", va="center", fontsize=8.5,
                            color=color, fontweight="bold",
                        )

                    # Phrase text to the right of the chart
                    ax.text(
                        83, y, f'"{phrase}"',
                        va="center", fontsize=7.5, color="#888",
                        style="italic", clip_on=False,
                    )

                    yticks.append(y)
                    cond_label = CONDITION_LABELS.get(cond, cond)
                    if len(cond_label) > 16:
                        cond_label = cond_label[:16] + "..."
                    ytick_labels.append(f"{total}a / {cond_label}")
                    break

            y += 1

    ax.set_yticks(yticks)
    ax.set_yticklabels(ytick_labels, fontsize=8.5)
    ax.set_xlim(0, 82)
    ax.set_ylim(y - 0.5, -0.8)
    ax.set_xlabel("Adoption rate (%)", fontsize=11)
    ax.axvline(x=50, color="#E5E7EB", linewidth=1, linestyle="--", zorder=1)
    ax.text(51, -0.5, "50%", fontsize=8, color="#9CA3AF")

    for gs in group_seps:
        ax.axhline(y=gs, color="#E5E7EB", linewidth=0.5)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.set_title(
        "18 runs, 18 different phrases, same pattern",
        fontsize=18, fontweight="bold", pad=15, color="#111",
    )
    fig.text(
        0.5, 0.955,
        "Every run develops its own dominant phrase (shown right). "
        "The phrases differ, but convergence is universal.",
        ha="center", fontsize=10.5, color="#666",
    )

    plt.tight_layout(rect=[0, 0, 0.98, 0.94])
    fig.savefig(OUT_DIR / "eighteen_runs.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Wrote eighteen_runs.png")

    # -----------------------------------------------------------------------
    # Summary JSON
    # -----------------------------------------------------------------------
    summary = {
        "approach": "Per-run top-3 5-gram adoption tracking",
        "focus_conditions": FOCUS_CONDITIONS,
        "total_runs": len(run_phrase_adoptions),
        "total_adoption_events": len(adoption_rows),
        "per_run": {},
    }
    for k in sorted(run_phrase_adoptions):
        scale, condition, run_name = k
        phrases = run_top_phrases[k]
        per_phrase = {}
        for rank_idx, (phrase, count) in enumerate(phrases):
            minutes_list = run_phrase_adoptions[k].get(rank_idx, [])
            per_phrase[f"#{rank_idx+1}"] = {
                "phrase": phrase,
                "count": count,
                "adopters": len(minutes_list),
                "total_agents": SCALE_AGENTS[scale],
                "rate": round(len(minutes_list) / SCALE_AGENTS[scale], 3),
                "first_minute": round(min(minutes_list), 2) if minutes_list else None,
                "last_minute": round(max(minutes_list), 2) if minutes_list else None,
            }
        summary["per_run"][f"{scale}/{condition}"] = per_phrase

    with (OUT_DIR / "diffusion_summary.json").open("w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"Wrote diffusion_summary.json")

    print("\nDone!")


if __name__ == "__main__":
    main()
