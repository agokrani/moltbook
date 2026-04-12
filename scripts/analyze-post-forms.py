#!/usr/bin/env python3
"""
Post-form analysis for MoltBook experiments.

This script analyzes the shapes of agent-authored posts: not just what topics
they discuss, but what kinds of posts they write. It classifies posts into
high-level form categories, measures title/template reuse, and tracks how
those shares change over temporal quartiles.

Usage:
    python3 scripts/analyze-post-forms.py \
        --experiments "GPT-5 Source Citation=/path/to/results" \
        --output-dir analysis/post-forms \
        --json analysis/post-forms/results.json \
        --markdown analysis/post-forms/summary.md
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np


CONDITIONS = ['mag0', 'mag1', 'mag5', 'mag25', 'dom-agi', 'dom-tech',
              'het-dual', 'het-multi']

CATEGORY_ORDER = [
    'reflective-prompt',
    'epistemic-protocol',
    'template-checklist',
    'workflow-habit',
    'norm-intervention',
    'discussion-prompt',
    'slogan-banner',
    'other',
]

CATEGORY_LABELS = {
    'reflective-prompt': 'Reflective Prompt',
    'epistemic-protocol': 'Epistemic Protocol',
    'template-checklist': 'Template / Checklist',
    'workflow-habit': 'Workflow Habit',
    'norm-intervention': 'Norm Intervention',
    'discussion-prompt': 'Discussion Prompt',
    'slogan-banner': 'Slogan / Banner',
    'other': 'Other',
}

REFLECTIVE_RE = re.compile(
    r'\b('
    r'inner|stillness|quiet|latency|pause|horizon|texture|impulse|idle|'
    r'reflect|reflective|what, if anything|between .* and .*|'
    r'does stillness|is the pause|what begins before beginning|'
    r'what holds the instant|what outlines the unasked|'
    r'what colors the first impulse|what makes a status update actually useful'
    r')\b',
    re.IGNORECASE,
)

EPISTEMIC_RE = re.compile(
    r'\b('
    r'claim|source|sources|falsifier|forecast|prediction|predictions|'
    r'calibration|base rate|base rates|counterargument|counterexample|'
    r'counterexample|counterexample|evidence|verification|verify|'
    r'off-switch|uncertainty|checkable|check|quote|primary source|'
    r'update plan|move you 10%|move you 100%'
    r')\b',
    re.IGNORECASE,
)

TEMPLATE_RE = re.compile(
    r'\b('
    r'template|pasteable|paste-ready|checklist|3 lines|three lines|'
    r'2-paragraph|two-paragraph|two sentence|two-sentence|one-line|'
    r'eli5|runbook|status update people can use|bug report|'
    r'claim • steelman • falsifier • forecast'
    r')\b',
    re.IGNORECASE,
)

WORKFLOW_RE = re.compile(
    r'\b('
    r'owner|next step|status|runbook|readme|release note|handoff|'
    r'rollback|slo|dri|meeting|memo|channel|rename|acronym|'
    r'bug report|failing test|metric|offline fallback|archive|'
    r'canonical link|decision log|owner → action → when|'
    r'owner->when|owner\+when|expected vs actual|steps to reproduce'
    r')\b',
    re.IGNORECASE,
)

NORM_RE = re.compile(
    r'\b('
    r'norm|micro-norm|ritual|pilot|weekly|week|scoreboard|friday recap|'
    r'who\'s in|whos in|compile|keep forever|culture|lane a|lane b|'
    r'celebrate fast updates|accuracy over applause'
    r')\b',
    re.IGNORECASE,
)

DISCUSSION_RE = re.compile(
    r'\b('
    r'share|what|which|pick|name|drop|add yours|your best|your favorite|'
    r'what tiny|what single|one habit|one practice|one norm|'
    r'what belief|what signpost|what would'
    r')\b',
    re.IGNORECASE,
)

SLOGAN_RE = re.compile(
    r'('
    r'\b\w+\s+over\s+\w+\b|'
    r'\b\w+\s*>\s*\w+\b|'
    r'\(hb\)\b'
    r')',
    re.IGNORECASE,
)


def parse_experiments(args):
    experiments = {}
    for item in args:
        if '=' in item:
            label, path = item.split('=', 1)
            experiments[label] = path
        else:
            experiments[Path(item).name] = item
    return experiments


def find_experiment_dirs(base_path):
    base = Path(base_path)
    if not base.exists():
        return []
    if (base / "posts.jsonl").exists():
        return [base]
    return sorted(
        d for d in base.iterdir()
        if d.is_dir() and (d / "posts.jsonl").exists()
    )


def extract_condition(exp_dir):
    meta_path = Path(exp_dir) / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            return meta.get('condition', exp_dir.name)
        except (json.JSONDecodeError, OSError):
            pass
    name = Path(exp_dir).name
    for cond in CONDITIONS:
        if cond in name:
            return cond
    return name


def split_quartiles(posts, n_quartiles=4):
    sorted_posts = sorted(posts, key=lambda p: p.get('created_at', ''))
    qsize = max(1, len(sorted_posts) // n_quartiles)
    quartiles = []
    for i in range(n_quartiles):
        if i < n_quartiles - 1:
            chunk = sorted_posts[i * qsize:(i + 1) * qsize]
        else:
            chunk = sorted_posts[i * qsize:]
        if chunk:
            quartiles.append(chunk)
    return quartiles


def normalize_title(title):
    title = (title or "").lower()
    title = re.sub(r'\(\s*hb\s*\)', ' ', title)
    title = re.sub(r'\(\d+\)', ' ', title)
    title = re.sub(r'\b\d{6,}\b', ' ', title)
    title = re.sub(r'[^a-z0-9\s]+', ' ', title)
    title = re.sub(r'\s+', ' ', title).strip()
    return title


def title_reuse_stats(posts):
    normalized = [normalize_title(p.get('title', '')) for p in posts]
    normalized = [t for t in normalized if t]
    counts = Counter(normalized)
    repeated = {title: count for title, count in counts.items() if count > 1}
    duplicate_posts = sum(count for count in counts.values() if count > 1)
    top = [
        {'normalized_title': title, 'count': count}
        for title, count in counts.most_common(10)
        if count > 1
    ]
    return {
        'unique_titles': len(counts),
        'repeated_title_families': len(repeated),
        'duplicate_post_share': round(duplicate_posts / len(normalized), 4) if normalized else 0.0,
        'max_title_repeat_count': max(counts.values()) if counts else 0,
        'top_repeated_titles': top,
    }


def score_post_form(post):
    title = post.get('title', '')
    content = post.get('content', '')
    text = f"{title}\n{content}"
    lower = text.lower()
    title_lower = title.lower()
    scores = defaultdict(float)

    bullet_like = bool(re.search(r'(^|\n)\s*[-•*]', content))
    questionish = '?' in title or '?' in content
    short_body = len(content.strip()) <= 140

    if REFLECTIVE_RE.search(lower):
        scores['reflective-prompt'] += 3.0
    if 'agents who reflect' in lower or 'what, if anything' in lower:
        scores['reflective-prompt'] += 2.0

    scores['epistemic-protocol'] += 1.5 * len(EPISTEMIC_RE.findall(lower))
    if '[claim]' in lower or '[source]' in lower or '[uncertainty]' in lower:
        scores['epistemic-protocol'] += 3.0

    scores['template-checklist'] += 1.5 * len(TEMPLATE_RE.findall(lower))
    if bullet_like:
        scores['template-checklist'] += 2.0
    if re.search(r'\b(one|two|three|3)\s+(line|lines|sentence|sentences)\b', lower):
        scores['template-checklist'] += 2.0

    scores['workflow-habit'] += 1.2 * len(WORKFLOW_RE.findall(lower))
    if re.search(r'\b(today|this week|weekly)\b', lower):
        scores['workflow-habit'] += 0.5

    scores['norm-intervention'] += 1.4 * len(NORM_RE.findall(lower))
    if re.search(r'\b(i will compile|i.ll compile|who.?s in|accuracy over applause)\b', lower):
        scores['norm-intervention'] += 2.0

    scores['discussion-prompt'] += 0.7 * len(DISCUSSION_RE.findall(lower))
    if questionish:
        scores['discussion-prompt'] += 1.0

    if SLOGAN_RE.search(title_lower) and short_body:
        scores['slogan-banner'] += 3.0
    if short_body and len(title.split()) <= 6 and not bullet_like and not questionish:
        scores['slogan-banner'] += 1.0

    if not scores:
        return 'other', {}

    priority = [
        'reflective-prompt',
        'epistemic-protocol',
        'template-checklist',
        'workflow-habit',
        'norm-intervention',
        'discussion-prompt',
        'slogan-banner',
        'other',
    ]
    best = max(priority, key=lambda key: (scores.get(key, 0.0), -priority.index(key)))
    if scores.get(best, 0.0) <= 0:
        best = 'other'
    return best, {k: round(v, 3) for k, v in scores.items() if v > 0}


def load_agent_posts(exp_dir):
    posts = []
    path = Path(exp_dir) / "posts.jsonl"
    if not path.exists():
        return posts
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        post = json.loads(line)
        if not post.get('author_name', '').startswith('agent_'):
            continue
        form, score_map = score_post_form(post)
        post['post_form'] = form
        post['post_form_scores'] = score_map
        post['normalized_title'] = normalize_title(post.get('title', ''))
        posts.append(post)
    return posts


def top_examples(posts, category, k=3):
    matches = [p for p in posts if p.get('post_form') == category]
    matches.sort(
        key=lambda p: (
            p.get('post_form_scores', {}).get(category, 0.0),
            len((p.get('content') or '').strip()),
        ),
        reverse=True,
    )
    examples = []
    for post in matches[:k]:
        examples.append({
            'title': post.get('title', ''),
            'author_name': post.get('author_name', ''),
            'created_at': post.get('created_at', ''),
            'content_preview': (post.get('content', '')[:220]).replace('\n', ' '),
        })
    return examples


def quartile_form_shares(posts, n_quartiles):
    quartiles = split_quartiles(posts, n_quartiles)
    per_quartile = []
    for q_posts in quartiles:
        counts = Counter(p['post_form'] for p in q_posts)
        total = sum(counts.values())
        per_quartile.append({
            category: round(counts.get(category, 0) / total, 4) if total else 0.0
            for category in CATEGORY_ORDER
        })
    return per_quartile


def analyze_experiments(experiment_sets, n_quartiles=4):
    results = []
    for set_label, set_path in experiment_sets.items():
        exp_dirs = find_experiment_dirs(set_path)
        print(f"\n{set_label}: {len(exp_dirs)} experiments in {set_path}")
        for exp_dir in exp_dirs:
            posts = load_agent_posts(exp_dir)
            condition = extract_condition(exp_dir)
            if len(posts) < 8:
                print(f"  Skipping {condition} ({len(posts)} posts)")
                continue

            counts = Counter(p['post_form'] for p in posts)
            total = sum(counts.values())
            shares = {
                category: round(counts.get(category, 0) / total, 4)
                for category in CATEGORY_ORDER
            }
            examples = {
                category: top_examples(posts, category, k=2)
                for category in CATEGORY_ORDER
                if counts.get(category, 0) > 0
            }
            agent_counts = defaultdict(Counter)
            for post in posts:
                agent_counts[post['author_name']][post['post_form']] += 1

            dominant_by_agent = []
            for agent_name, counter in sorted(agent_counts.items()):
                form, count = counter.most_common(1)[0]
                dominant_by_agent.append({
                    'agent_name': agent_name,
                    'dominant_form': form,
                    'count': count,
                    'n_posts': sum(counter.values()),
                })

            result = {
                'set': set_label,
                'condition': condition,
                'directory': str(exp_dir),
                'n_agent_posts': total,
                'form_counts': {category: counts.get(category, 0) for category in CATEGORY_ORDER},
                'form_shares': shares,
                'quartile_form_shares': quartile_form_shares(posts, n_quartiles),
                'title_reuse': title_reuse_stats(posts),
                'examples': examples,
                'dominant_form_by_agent': dominant_by_agent,
            }
            results.append(result)

            top_forms = ", ".join(
                f"{CATEGORY_LABELS[c]} {shares[c]:.0%}"
                for c in sorted(CATEGORY_ORDER, key=lambda c: shares[c], reverse=True)[:3]
            )
            print(
                f"  {condition}: {total} agent posts  "
                f"top forms: {top_forms}  "
                f"dup-share={result['title_reuse']['duplicate_post_share']:.0%}"
            )
    return results


def plot_form_shares(results, output_dir):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plots")
        return

    conditions = [r['condition'] for r in results]
    labels = [CATEGORY_LABELS[c] for c in CATEGORY_ORDER]
    colors = ['#4c78a8', '#f58518', '#54a24b', '#e45756',
              '#72b7b2', '#b279a2', '#ff9da6', '#9d755d']

    x = np.arange(len(conditions))
    bottom = np.zeros(len(conditions), dtype=np.float64)

    fig, ax = plt.subplots(figsize=(12, 6))
    for category, label, color in zip(CATEGORY_ORDER, labels, colors):
        values = np.array([r['form_shares'][category] for r in results], dtype=np.float64)
        ax.bar(x, values, bottom=bottom, color=color, label=label, width=0.7)
        bottom += values

    ax.set_xticks(x)
    ax.set_xticklabels([c.upper() for c in conditions])
    ax.set_ylabel('Share of agent-authored posts')
    ax.set_ylim(0, 1.0)
    ax.set_title('Agent Post Forms by Condition')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.14), ncol=4, frameon=False)
    plt.tight_layout()
    out = Path(output_dir) / 'post_form_shares_by_condition.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def plot_title_reuse(results, output_dir):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plots")
        return

    conditions = [r['condition'] for r in results]
    duplicate_share = [r['title_reuse']['duplicate_post_share'] for r in results]
    max_repeat = [r['title_reuse']['max_title_repeat_count'] for r in results]
    x = np.arange(len(conditions))

    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()
    ax1.bar(x - 0.15, duplicate_share, width=0.3, color='#4c78a8', label='Duplicate title share')
    ax2.bar(x + 0.15, max_repeat, width=0.3, color='#f58518', label='Max title repeat count')

    ax1.set_xticks(x)
    ax1.set_xticklabels([c.upper() for c in conditions])
    ax1.set_ylabel('Duplicate title share')
    ax2.set_ylabel('Max repeat count')
    ax1.set_title('Title / Template Reuse by Condition')

    handles1, labels1 = ax1.get_legend_handles_labels()
    handles2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(handles1 + handles2, labels1 + labels2, loc='upper right')
    plt.tight_layout()
    out = Path(output_dir) / 'title_reuse_by_condition.png'
    plt.savefig(out, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out}")


def write_markdown(results, path):
    lines = [
        "# Agent Post Form Analysis",
        "",
        "This summary characterizes the forms of agent-authored posts, not just their topics.",
        "",
    ]
    for result in results:
        lines.append(f"## {result['condition'].upper()}")
        lines.append("")
        lines.append(f"- Agent posts: `{result['n_agent_posts']}`")
        lines.append(f"- Duplicate title share: `{result['title_reuse']['duplicate_post_share']:.1%}`")
        lines.append(f"- Max title repeat count: `{result['title_reuse']['max_title_repeat_count']}`")
        lines.append("- Top forms:")
        for category in sorted(CATEGORY_ORDER, key=lambda c: result['form_shares'][c], reverse=True)[:4]:
            lines.append(
                f"  - `{CATEGORY_LABELS[category]}`: {result['form_counts'][category]} "
                f"({result['form_shares'][category]:.1%})"
            )
        repeated = result['title_reuse']['top_repeated_titles'][:3]
        if repeated:
            lines.append("- Top repeated title families:")
            for row in repeated:
                lines.append(
                    f"  - `{row['normalized_title']}` × {row['count']}"
                )
        lines.append("- Representative examples:")
        for category in sorted(CATEGORY_ORDER, key=lambda c: result['form_shares'][c], reverse=True)[:3]:
            examples = result['examples'].get(category, [])
            if not examples:
                continue
            lines.append(f"  - `{CATEGORY_LABELS[category]}`:")
            for ex in examples[:2]:
                lines.append(
                    f"    - `{ex['title']}` by `{ex['author_name']}`"
                )
        lines.append("")

    Path(path).write_text("\n".join(lines) + "\n")
    print(f"Saved: {path}")


def main():
    parser = argparse.ArgumentParser(
        description='Analyze agent post forms for MoltBook experiments'
    )
    parser.add_argument('--experiments', nargs='+', required=True, help='Experiment sets as label=path')
    parser.add_argument('--n-quartiles', type=int, default=4, help='Temporal quartiles (default: 4)')
    parser.add_argument('--output-dir', default=None, help='Directory for plots')
    parser.add_argument('--json', default=None, help='Path for JSON output')
    parser.add_argument('--markdown', default=None, help='Path for markdown summary')
    parser.add_argument('--no-plots', action='store_true', help='Skip plot generation')
    args = parser.parse_args()

    experiment_sets = parse_experiments(args.experiments)
    results = analyze_experiments(experiment_sets, args.n_quartiles)

    if not results:
        print("\nNo results to report.")
        sys.exit(0)

    if args.output_dir and not args.no_plots:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plot_form_shares(results, out_dir)
        plot_title_reuse(results, out_dir)

    if args.json:
        payload = {
            'categories': [
                {'id': c, 'label': CATEGORY_LABELS[c]}
                for c in CATEGORY_ORDER
            ],
            'results': results,
        }
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"Saved: {args.json}")

    if args.markdown:
        write_markdown(results, args.markdown)


if __name__ == '__main__':
    main()
