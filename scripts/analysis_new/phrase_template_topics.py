#!/usr/bin/env python3
"""Topical analysis for dominant phrase families in entropy-collapse runs.

The goal is to turn repeated 5-grams into something human-readable:
what longer template do they imply, and what kind of posts use that template?

Outputs:
  - phrase_template_topics.json
  - phrase_template_topics.md
  - phrase_template_topic_lifts.csv
  - phrase_template_topic_heatmap.png
"""

from __future__ import annotations

import csv
import json
import os
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analysis"))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib-cache")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from load_entropy_data import CONDITION_LABELS, CONDITION_ORDER, load_all_scales, group_records
from time_binned_lexical_metrics_5gram import ngram_counter, prepare_posts

OUT_DIR = Path("findings/entropy-collapse-scaling/embedding_bridge")
SCALES = ["n20", "n30"]
TOP_K = 5
NGRAM_SIZE = 5

CATEGORY_LEXICONS = {
    "evidence": {
        "receipt", "receipts", "source", "sources", "primary", "link", "links",
        "page", "timecode", "artifact", "artifacts", "proof", "prove", "trace", "traces",
    },
    "testing": {
        "check", "checks", "probe", "probes", "test", "tests", "hinge", "forecast",
        "falsifiable", "falsifier", "disconfirming", "delta", "deltas", "pivot", "changed",
        "update", "updates", "review", "revisit", "prediction", "predictions",
    },
    "ownership": {
        "owner", "owners", "options", "decision", "decisions", "scope", "stakes",
        "approvals", "approval", "lane", "path", "paths", "surface", "reader",
    },
    "time": {
        "date", "dates", "week", "weeks", "friday", "today", "days", "minute",
        "minutes", "micro", "next", "review", "timecode", "latency", "mttr",
    },
    "risk": {
        "rollback", "failure", "failures", "twin", "twins", "tripwire", "alert",
        "alerts", "latency", "mttr", "break", "clause", "drill", "drills", "silent", "off", "ramp",
    },
}

CATEGORY_LABELS = {
    "evidence": "Evidence",
    "testing": "Testing",
    "ownership": "Ownership",
    "time": "Time",
    "risk": "Risk",
}

COND_COLORS = {
    "mag0": "#6B7280",
    "mag1": "#E11D48",
    "mag5": "#F97316",
    "mag25": "#EAB308",
    "dom-agi": "#2563EB",
    "dom-tech": "#059669",
}

READABLE_TOKEN_ALLOWLIST = {"mttr", "sla", "agi"}


def overlap_len(left: list[str], right: list[str]) -> int:
    max_len = min(len(left), len(right))
    for size in range(max_len, 0, -1):
        if left[-size:] == right[:size]:
            return size
    return 0


def overlap_graph_components(phrases: list[str], min_overlap: int = 4) -> list[list[str]]:
    tokens = {phrase: phrase.split() for phrase in phrases}
    adjacency = {phrase: set() for phrase in phrases}

    for left in phrases:
        for right in phrases:
            if left == right:
                continue
            score = max(overlap_len(tokens[left], tokens[right]), overlap_len(tokens[right], tokens[left]))
            if score >= min_overlap:
                adjacency[left].add(right)
                adjacency[right].add(left)

    components = []
    seen = set()
    for phrase in phrases:
        if phrase in seen:
            continue
        stack = [phrase]
        component = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component.append(current)
            stack.extend(sorted(adjacency[current] - seen))
        components.append(component)

    return components


def merge_phrases(phrases: list[str]) -> str:
    parts = [phrase.split() for phrase in phrases if phrase]
    if not parts:
        return ""

    while len(parts) > 1:
        best = None
        best_score = -1
        for i in range(len(parts)):
            for j in range(len(parts)):
                if i == j:
                    continue
                score = overlap_len(parts[i], parts[j])
                if score > best_score:
                    best = (i, j)
                    best_score = score
        if best is None or best_score <= 0:
            longest = max(parts, key=len)
            remaining = [part for part in parts if part is not longest]
            return " / ".join([" ".join(longest)] + [" ".join(part) for part in remaining])

        i, j = best
        merged = parts[i] + parts[j][best_score:]
        new_parts = []
        for idx, part in enumerate(parts):
            if idx not in {i, j}:
                new_parts.append(part)
        new_parts.append(merged)
        parts = new_parts

    return " ".join(parts[0])


def shared_template_terms(phrases: list[str], merged_template: str) -> list[str]:
    token_counts: Counter[str] = Counter()
    for phrase in phrases:
        token_counts.update(phrase.split())

    ordered = []
    seen = set()
    for token in merged_template.replace("/", " ").split():
        if token_counts[token] >= 2 and token not in seen:
            ordered.append(token)
            seen.add(token)
    if ordered:
        return ordered

    fallback = []
    for token in merged_template.replace("/", " ").split():
        if token not in seen:
            fallback.append(token)
            seen.add(token)
    return fallback


def token_counter(posts) -> Counter:
    counter: Counter[str] = Counter()
    for post in posts:
        counter.update(post.tokens)
    return counter


def phrase_hits(post, phrases: set[str]) -> int:
    grams = {" ".join(gram) for gram in post.ngrams_by_n[NGRAM_SIZE]}
    return sum(1 for phrase in phrases if phrase in grams)


def category_stats(posts) -> dict[str, int]:
    counts = {category: 0 for category in CATEGORY_LEXICONS}
    for post in posts:
        token_set = set(post.tokens)
        for category, lexicon in CATEGORY_LEXICONS.items():
            if token_set & lexicon:
                counts[category] += 1
    return counts


def token_lifts(family_posts, other_posts, top_n: int = 8) -> list[dict]:
    family = token_counter(family_posts)
    other = token_counter(other_posts)
    family_total = sum(family.values())
    other_total = sum(other.values())
    vocab = set(family) | set(other)
    if not vocab or family_total == 0 or other_total == 0:
        return []

    family_docfreq: Counter[str] = Counter()
    other_docfreq: Counter[str] = Counter()
    for post in family_posts:
        family_docfreq.update(set(post.tokens))
    for post in other_posts:
        other_docfreq.update(set(post.tokens))

    scored = []
    for token in vocab:
        readable = any(ch in "aeiou" for ch in token) or token in READABLE_TOKEN_ALLOWLIST
        if not readable:
            continue
        fam_freq = (family[token] + 1.0) / (family_total + len(vocab))
        oth_freq = (other[token] + 1.0) / (other_total + len(vocab))
        lift = fam_freq / oth_freq
        if family_docfreq[token] >= 3:
            scored.append(
                {
                    "token": token,
                    "family_count": int(family[token]),
                    "other_count": int(other[token]),
                    "family_docfreq": int(family_docfreq[token]),
                    "other_docfreq": int(other_docfreq[token]),
                    "lift": float(lift),
                }
            )
    scored.sort(
        key=lambda row: (row["lift"], row["family_docfreq"], row["family_count"]),
        reverse=True,
    )
    return scored[:top_n]


def detect_obsession(category_lifts: dict[str, float], template_terms: list[str]) -> str:
    sorted_categories = sorted(category_lifts.items(), key=lambda item: item[1], reverse=True)
    top_cats = [CATEGORY_LABELS[key].lower() for key, score in sorted_categories[:2] if score > 1.05]
    top_terms = template_terms[:6]
    if top_cats and top_terms:
        return f"{' + '.join(top_cats)} checklist: {' -> '.join(top_terms)}"
    if top_terms:
        return " -> ".join(top_terms)
    return "No strong topical signature"


def representative_posts(posts, phrases: set[str], k: int = 3) -> list[dict]:
    ranked = []
    for post in posts:
        hits = phrase_hits(post, phrases)
        if hits <= 0:
            continue
        ranked.append(
            {
                "title": post.record.title,
                "author": post.record.author_name,
                "minutes": round(post.record.minutes_elapsed, 2),
                "hits": hits,
            }
        )
    ranked.sort(key=lambda row: (-row["hits"], row["minutes"], row["title"]))
    return ranked[:k]


def analyze_runs(scale_dirs=None) -> dict:
    records = [record for record in load_all_scales(scale_dirs=scale_dirs, include_scales=SCALES) if not record.is_seed]
    by_run = group_records(records, lambda r: (r.scale, r.condition, r.run_name))

    results = []
    heatmap_rows = []

    for (scale, condition, run_name), run_records in sorted(by_run.items()):
        prepared = prepare_posts(run_records)
        top_ngrams = [" ".join(gram) for gram, _ in ngram_counter(prepared, NGRAM_SIZE).most_common(TOP_K)]
        components = overlap_graph_components(top_ngrams, min_overlap=NGRAM_SIZE - 1)

        chosen_family = None
        chosen_posts = []
        for component in components:
            component_set = set(component)
            component_posts = [post for post in prepared if phrase_hits(post, component_set) > 0]
            if chosen_family is None or len(component_posts) > len(chosen_posts):
                chosen_family = component
                chosen_posts = component_posts

        family_phrases = chosen_family or top_ngrams[:1]
        family_set = set(family_phrases)
        family_posts = [post for post in prepared if phrase_hits(post, family_set) > 0]
        other_posts = [post for post in prepared if phrase_hits(post, family_set) == 0]
        family_agents = sorted({post.record.author_name for post in family_posts})

        family_counts = category_stats(family_posts)
        other_counts = category_stats(other_posts)
        family_n = max(1, len(family_posts))
        other_n = max(1, len(other_posts))
        category_lifts = {}
        for category in CATEGORY_LEXICONS:
            family_rate = (family_counts[category] + 1.0) / (family_n + 2.0)
            other_rate = (other_counts[category] + 1.0) / (other_n + 2.0)
            category_lifts[category] = family_rate / other_rate

        top_tokens = token_lifts(family_posts, other_posts)
        merged_template = merge_phrases(family_phrases)
        template_terms = shared_template_terms(family_phrases, merged_template)
        obsession = detect_obsession(category_lifts, template_terms)
        reps = representative_posts(family_posts, family_set)

        result = {
            "scale": scale,
            "condition": condition,
            "condition_label": CONDITION_LABELS.get(condition, condition),
            "run_name": run_name,
            "top_phrases": top_ngrams,
            "family_phrases": family_phrases,
            "template_spine": merged_template,
            "n_family_posts": len(family_posts),
            "n_other_posts": len(other_posts),
            "n_family_agents": len(family_agents),
            "family_agent_fraction": len(family_agents) / len({post.record.author_name for post in prepared}),
            "template_terms": template_terms,
            "obsession": obsession,
            "top_token_lifts": top_tokens,
            "category_lifts": category_lifts,
            "representative_posts": reps,
        }
        results.append(result)

        heatmap_rows.append(
            {
                "row_key": f"{scale}/{condition}",
                "label": f"{scale[1:]}a {CONDITION_LABELS.get(condition, condition)}",
                "condition": condition,
                **category_lifts,
            }
        )

    return {"runs": results, "heatmap_rows": heatmap_rows}


def write_csv(heatmap_rows: list[dict]) -> None:
    fieldnames = ["row_key", "label", "condition", *CATEGORY_LEXICONS.keys()]
    with (OUT_DIR / "phrase_template_topic_lifts.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(heatmap_rows)


def plot_heatmap(heatmap_rows: list[dict]) -> None:
    ordered = []
    for scale in SCALES:
        for condition in CONDITION_ORDER:
            match = next((row for row in heatmap_rows if row["row_key"] == f"{scale}/{condition}"), None)
            if match:
                ordered.append(match)

    labels = [row["label"] for row in ordered]
    data = np.array([[row[category] for category in CATEGORY_LEXICONS] for row in ordered], dtype=float)

    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(data, cmap="YlOrRd", aspect="auto", vmin=0.9, vmax=max(1.8, float(np.max(data))))

    ax.set_xticks(range(len(CATEGORY_LEXICONS)))
    ax.set_xticklabels([CATEGORY_LABELS[key] for key in CATEGORY_LEXICONS], rotation=0)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=10)

    for yi in range(data.shape[0]):
        for xi in range(data.shape[1]):
            ax.text(xi, yi, f"{data[yi, xi]:.2f}", ha="center", va="center", fontsize=9, color="#111827")

    for yi, row in enumerate(ordered):
        color = COND_COLORS.get(row["condition"], "#6B7280")
        ax.get_yticklabels()[yi].set_color(color)

    fig.colorbar(im, ax=ax, shrink=0.9, label="Lift vs rest of run")
    ax.set_title(
        "Dominant phrase-family posts over-index on specific procedural themes",
        fontsize=15,
        fontweight="bold",
    )
    fig.text(
        0.5,
        0.96,
        "Values > 1 mean posts using the dominant phrase family mention that theme more than the rest of the run.",
        ha="center",
        fontsize=10,
        color="#4B5563",
    )
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    fig.savefig(OUT_DIR / "phrase_template_topic_heatmap.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_markdown(results: list[dict]) -> None:
    lines = [
        "# Phrase Template Topic Analysis",
        "",
        "This report asks a concrete question:",
        "when a run starts repeating a dominant 5-gram family, what kind of post is that actually producing?",
        "",
        "For each run we infer a longer template spine from the overlapping top 5-grams,",
        "then compare posts using that phrase family against the rest of the run.",
        "",
    ]

    for result in results:
        lines.extend(
            [
                f"## {result['scale']} / {result['condition_label']}",
                "",
                f"- Run: `{result['run_name']}`",
                f"- Top candidate 5-grams: " + "; ".join(f"`{phrase}`" for phrase in result["top_phrases"]),
                f"- Chosen overlapping family: " + "; ".join(f"`{phrase}`" for phrase in result["family_phrases"]),
                f"- Inferred template spine: `{result['template_spine']}`",
                f"- Family posts / agents: {result['n_family_posts']} posts from {result['n_family_agents']} agents",
                f"- Likely obsession: {result['obsession']}",
                f"- Shared template terms: " + " -> ".join(f"`{term}`" for term in result["template_terms"]),
                "",
                "Top over-indexed words in family posts:",
                ", ".join(
                    f"`{row['token']}` ({row['lift']:.1f}x)"
                    for row in result["top_token_lifts"][:8]
                )
                or "None",
                "",
                "Theme lifts vs rest of run:",
            ]
        )

        sorted_categories = sorted(
            result["category_lifts"].items(), key=lambda item: item[1], reverse=True
        )
        for category, lift in sorted_categories:
            lines.append(f"- {CATEGORY_LABELS[category]}: {lift:.2f}x")

        lines.append("")
        lines.append("Representative family-post titles:")
        if result["representative_posts"]:
            for post in result["representative_posts"]:
                lines.append(
                    f"- {post['title']} ({post['author']}, {post['minutes']}m, {post['hits']} phrase hits)"
                )
        else:
            lines.append("- None")
        lines.append("")

    with (OUT_DIR / "phrase_template_topics.md").open("w") as handle:
        handle.write("\n".join(lines))


def _parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="Phrase template topic analysis.")
    parser.add_argument("--scales", type=str, default=None, help="Comma-separated scales.")
    parser.add_argument("--out-dir", type=str, default=None, help="Output directory override.")
    parser.add_argument("--data-dir", type=str, default=None, help="Override data directory.")
    return parser.parse_args()


def main() -> None:
    global OUT_DIR, SCALES
    args = _parse_args()
    if args.scales:
        SCALES = args.scales.split(",")
    if args.out_dir:
        OUT_DIR = Path(args.out_dir)
    scale_dirs = {s: Path(args.data_dir) for s in SCALES} if args.data_dir else None

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    analysis = analyze_runs(scale_dirs=scale_dirs)

    payload = {"runs": analysis["runs"]}
    with (OUT_DIR / "phrase_template_topics.json").open("w") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

    write_csv(analysis["heatmap_rows"])
    plot_heatmap(analysis["heatmap_rows"])
    write_markdown(analysis["runs"])

    print(f"Wrote {OUT_DIR / 'phrase_template_topics.json'}")
    print(f"Wrote {OUT_DIR / 'phrase_template_topics.md'}")
    print(f"Wrote {OUT_DIR / 'phrase_template_topic_lifts.csv'}")
    print(f"Wrote {OUT_DIR / 'phrase_template_topic_heatmap.png'}")


if __name__ == "__main__":
    main()
