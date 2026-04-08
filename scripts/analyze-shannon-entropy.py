#!/usr/bin/env python3
"""
Shannon entropy analysis for MoltBook entropy collapse experiments.

Computes Shannon entropy of n-gram frequency distributions per temporal
quartile. Declining entropy over time = entropy collapse: fewer n-grams
dominating the distribution as agents converge on shared phrases.

Uses:
    - nltk.util.ngrams for n-gram extraction
    - scipy.stats.entropy for numerically stable Shannon entropy computation

Usage:
    python3 scripts/analyze-shannon-entropy.py \\
        --experiments "BASE=/path/to/base" "Gemini=/path/to/gemini" \\
        --ngram 3 \\
        --output-dir analysis/plots

    # Normalized entropy (0-1 scale):
    python3 scripts/analyze-shannon-entropy.py \\
        --experiments "BASE=/path/to/base" "RL=/path/to/rl" \\
        --ngram 3 --normalize \\
        --output-dir analysis/plots
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from nltk import word_tokenize
from nltk.util import ngrams as nltk_ngrams
from scipy.stats import entropy as scipy_entropy


# ---------------------------------------------------------------------------
# N-gram extraction (nltk)
# ---------------------------------------------------------------------------

def extract_ngrams(texts, n):
    """Extract n-gram frequency counts using nltk.

    Uses nltk.word_tokenize for tokenization and nltk.util.ngrams
    for n-gram generation.

    Returns:
        Counter mapping (n-gram tuple) -> count
    """
    counts = Counter()
    for text in texts:
        tokens = word_tokenize(text.lower())
        counts.update(nltk_ngrams(tokens, n))
    return counts


# ---------------------------------------------------------------------------
# Shannon entropy (scipy)
# ---------------------------------------------------------------------------

def shannon_entropy(ngram_counts, base=2, normalize=False):
    """Compute Shannon entropy of an n-gram frequency distribution.

    Uses scipy.stats.entropy for numerically stable computation.
    scipy normalizes raw counts to probabilities internally.

    Args:
        ngram_counts: Counter of {ngram: count}
        base: log base (2 = bits). Default: 2
        normalize: if True, return H / log_base(V) for [0, 1] scale

    Returns:
        float: entropy value
    """
    if not ngram_counts:
        return 0.0

    freq = np.array(list(ngram_counts.values()), dtype=np.float64)
    h = float(scipy_entropy(freq, base=base))

    if normalize:
        v = len(ngram_counts)
        if v <= 1:
            return 0.0
        h_max = math.log(v) / math.log(base)
        return h / h_max if h_max > 0 else 0.0

    return h


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_posts(exp_dir):
    """Load agent posts from JSONL, excluding seed/system posts."""
    posts = []
    pf = Path(exp_dir) / "posts.jsonl"
    if not pf.exists():
        return posts
    for line in open(pf):
        line = line.strip()
        if line:
            p = json.loads(line)
            if not p.get('author_name', '').startswith('civiclens_'):
                posts.append(p)
    return posts


def find_experiment_dirs(base_path):
    """Find experiment subdirectories containing posts.jsonl."""
    base = Path(base_path)
    if not base.exists():
        return []
    if (base / "posts.jsonl").exists():
        return [base]
    return sorted(d for d in base.iterdir()
                  if d.is_dir() and (d / "posts.jsonl").exists())


def extract_condition(exp_dir):
    """Extract condition name from experiment directory."""
    meta_path = exp_dir / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            return meta.get('condition', exp_dir.name)
        except (json.JSONDecodeError, OSError):
            pass
    name = exp_dir.name
    for cond in ['mag0', 'mag1', 'mag5', 'mag25', 'dom-agi', 'dom-tech',
                 'het-dual', 'het-multi']:
        if cond in name:
            return cond
    return name


# ---------------------------------------------------------------------------
# Temporal analysis
# ---------------------------------------------------------------------------

def split_quartiles(posts, n_quartiles=4):
    """Split posts into temporal quartiles by creation time."""
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


def compute_entropy_trajectory(posts, n, n_quartiles=4):
    """Compute Shannon entropy (raw + normalized) per temporal quartile."""
    quartiles = split_quartiles(posts, n_quartiles)
    trajectory = []

    for i, q_posts in enumerate(quartiles):
        texts = [f"{p.get('title', '')} {p.get('content', '')}"
                 for p in q_posts]

        ngram_counts = extract_ngrams(texts, n)
        total_ngrams = sum(ngram_counts.values())
        vocab_size = len(ngram_counts)

        h = shannon_entropy(ngram_counts, base=2, normalize=False)
        h_norm = shannon_entropy(ngram_counts, base=2, normalize=True)

        trajectory.append({
            'quartile': i + 1,
            'n_posts': len(q_posts),
            'total_ngrams': total_ngrams,
            'vocab_size': vocab_size,
            'entropy': round(h, 3),
            'entropy_norm': round(h_norm, 4),
        })

    return trajectory


# ---------------------------------------------------------------------------
# Analysis runner
# ---------------------------------------------------------------------------

def analyze_experiments(experiment_sets, n, n_quartiles=4):
    """Run entropy analysis across all experiment sets."""
    all_results = []

    for set_label, set_path in experiment_sets.items():
        exp_dirs = find_experiment_dirs(set_path)
        print(f"\n{set_label}: {len(exp_dirs)} experiments in {set_path}")

        for exp_dir in exp_dirs:
            condition = extract_condition(exp_dir)
            posts = load_posts(exp_dir)

            if len(posts) < 8:
                print(f"  Skipping {condition} ({len(posts)} posts)")
                continue

            trajectory = compute_entropy_trajectory(posts, n, n_quartiles)

            h_vals = [t['entropy'] for t in trajectory]
            h_norm_vals = [t['entropy_norm'] for t in trajectory]
            delta = round(h_vals[-1] - h_vals[0], 3) if len(h_vals) >= 2 else None
            delta_norm = round(h_norm_vals[-1] - h_norm_vals[0], 4) if len(h_norm_vals) >= 2 else None

            result = {
                'set': set_label,
                'condition': condition,
                'directory': str(exp_dir),
                'n_posts': len(posts),
                'ngram': n,
                'trajectory': trajectory,
                'entropy_values': h_vals,
                'entropy_norm_values': h_norm_vals,
                'delta': delta,
                'delta_norm': delta_norm,
            }

            all_results.append(result)

            h_str = " → ".join(f"{v:.2f}" for v in h_vals)
            print(f"  {condition}: {len(posts)} posts  "
                  f"H: {h_str}  Δ={delta:+.2f} bits  "
                  f"Δ_norm={delta_norm:+.4f}")

    return all_results


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_trajectories(results, output_dir, n, normalize, n_quartiles):
    """Plot per-condition entropy trajectory subplots."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping plots")
        return

    conditions = sorted(set(r['condition'] for r in results))
    sets = sorted(set(r['set'] for r in results))

    palette = ['#2ecc71', '#e74c3c', '#e67e22', '#9b59b6', '#3498db',
               '#1abc9c', '#f39c12', '#c0392b']
    marker_list = ['s', 'o', '^', 'D', 'v', 'P', 'X', '*']

    n_conds = len(conditions)
    n_cols = min(3, n_conds)
    n_rows = math.ceil(n_conds / n_cols)

    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(6 * n_cols, 5 * n_rows),
                             sharey=True, squeeze=False)

    y_label = 'H_norm' if normalize else 'H (bits)'
    fig.suptitle(
        f'Shannon Entropy ({n}-gram) Temporal Trajectories\n'
        f'({n_quartiles} quartiles, 1-hour experiments)',
        fontsize=14, fontweight='bold', y=1.0
    )

    val_key = 'entropy_norm_values' if normalize else 'entropy_values'
    delta_key = 'delta_norm' if normalize else 'delta'

    for idx, cond in enumerate(conditions):
        ax = axes[idx // n_cols][idx % n_cols]
        ax.set_title(cond.upper(), fontsize=13, fontweight='bold')
        ax.set_xlabel('Time Quartile', fontsize=10)
        if idx % n_cols == 0:
            ax.set_ylabel(y_label, fontsize=11)

        x_ticks = list(range(1, n_quartiles + 1))
        ax.set_xticks(x_ticks)
        ax.set_xticklabels([f'Q{i}' for i in x_ticks])
        ax.grid(True, alpha=0.3)

        for s_idx, s_label in enumerate(sets):
            matching = [r for r in results
                        if r['set'] == s_label and r['condition'] == cond]
            if not matching:
                continue
            r = matching[0]
            values = r[val_key]
            delta = r[delta_key]
            if len(values) < 2:
                continue

            color = palette[s_idx % len(palette)]
            marker = marker_list[s_idx % len(marker_list)]
            is_base = 'base' in s_label.lower()
            lw = 3.0 if is_base else 1.8
            ls = '-' if is_base else '--'

            fmt = f'{delta:+.4f}' if normalize else f'{delta:+.2f}'
            label = f"{s_label} (Δ={fmt})"
            ax.plot(x_ticks[:len(values)], values, color=color,
                    marker=marker, linewidth=lw, linestyle=ls,
                    markersize=7, label=label, alpha=0.9)

        ax.legend(fontsize=7, loc='best', framealpha=0.9)

    for idx in range(n_conds, n_rows * n_cols):
        axes[idx // n_cols][idx % n_cols].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    tag = '_norm' if normalize else ''
    out_path = Path(output_dir) / f'shannon_entropy_{n}gram{tag}_trajectories.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_path}")


def plot_heatmap(results, output_dir, n, normalize):
    """Plot delta heatmap."""
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not available — skipping heatmap")
        return

    conditions = sorted(set(r['condition'] for r in results))
    sets = sorted(set(r['set'] for r in results))

    delta_key = 'delta_norm' if normalize else 'delta'
    matrix = []
    for s_label in sets:
        row = []
        for cond in conditions:
            matching = [r for r in results
                        if r['set'] == s_label and r['condition'] == cond]
            row.append(matching[0][delta_key] if matching and matching[0][delta_key] is not None else 0)
        matrix.append(row)

    arr = np.array(matrix)

    fig, ax = plt.subplots(
        figsize=(max(8, len(conditions) * 1.6), len(sets) * 1.0 + 1.5)
    )

    if normalize:
        vmin, vmax = -0.15, 0.05
    else:
        vmin, vmax = -3.0, 0.5

    im = ax.imshow(arr, cmap='RdYlGn', aspect='auto', vmin=vmin, vmax=vmax)

    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.upper() for c in conditions], fontsize=11)
    ax.set_yticks(range(len(sets)))
    ax.set_yticklabels(sets, fontsize=11)

    for i in range(len(sets)):
        for j in range(len(conditions)):
            val = arr[i, j]
            threshold = 0.08 if normalize else 1.5
            color = 'white' if abs(val) > threshold else 'black'
            fmt = f'{val:+.4f}' if normalize else f'{val:+.2f}'
            ax.text(j, i, fmt, ha='center', va='center',
                    fontsize=10, fontweight='bold', color=color)

    tag = ' (Normalized)' if normalize else ' (bits)'
    ax.set_title(
        f'Shannon Entropy{tag} Temporal Delta (Q4 − Q1)\n'
        f'Green = Entropy Maintained | Red = Entropy Collapsed',
        fontsize=13, fontweight='bold'
    )
    plt.colorbar(im, ax=ax, label=f'ΔH', shrink=0.8)
    plt.tight_layout()

    norm_tag = '_norm' if normalize else ''
    out_path = Path(output_dir) / f'shannon_entropy_{n}gram{norm_tag}_heatmap.png'
    plt.savefig(out_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Shannon entropy analysis for MoltBook experiments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument('--experiments', nargs='+', required=True,
                        help='Experiment sets as label=path')
    parser.add_argument('--ngram', type=int, default=3,
                        help='N-gram size (default: 3)')
    parser.add_argument('--n-quartiles', type=int, default=4,
                        help='Number of temporal quartiles (default: 4)')
    parser.add_argument('--normalize', action='store_true',
                        help='Normalize entropy to [0,1] scale')
    parser.add_argument('--output-dir', default=None,
                        help='Directory for plot output')
    parser.add_argument('--json', default=None,
                        help='Path for JSON results output')
    parser.add_argument('--no-plots', action='store_true',
                        help='Skip plot generation')

    args = parser.parse_args()
    experiment_sets = {}
    for item in args.experiments:
        if '=' in item:
            label, path = item.split('=', 1)
            experiment_sets[label] = path
        else:
            experiment_sets[Path(item).name] = item

    print(f"N-gram: {args.ngram}")
    print(f"Quartiles: {args.n_quartiles}")
    print(f"Normalized: {args.normalize}")

    results = analyze_experiments(experiment_sets, args.ngram, args.n_quartiles)

    if not results:
        print("\nNo results.")
        sys.exit(0)

    # Summary table
    print(f"\n{'=' * 110}")
    print(f"SUMMARY")
    print(f"{'=' * 110}")

    sets = sorted(set(r['set'] for r in results))
    conditions = sorted(set(r['condition'] for r in results))

    header = f"{'Cond':<10} {'Set':<20} {'Posts':>5}"
    for i in range(1, args.n_quartiles + 1):
        header += f"  {'Q' + str(i):>8}"
    header += f"  {'Δ bits':>8}  {'Δ norm':>8}  {'V_Q1':>6} {'V_Q4':>6}"
    print(header)
    print("-" * len(header))

    for cond in conditions:
        for s_label in sets:
            matching = [r for r in results
                        if r['set'] == s_label and r['condition'] == cond]
            if not matching:
                continue
            r = matching[0]

            row = f"{cond:<10} {s_label:<20} {r['n_posts']:>5}"
            for v in r['entropy_values']:
                row += f"  {v:>8.2f}"
            row += f"  {r['delta']:>+8.2f}  {r['delta_norm']:>+8.4f}"

            traj = r['trajectory']
            row += f"  {traj[0]['vocab_size']:>6} {traj[-1]['vocab_size']:>6}"
            print(row)

    # Plots (generate both raw and normalized)
    if args.output_dir and not args.no_plots:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plot_trajectories(results, out_dir, args.ngram, False, args.n_quartiles)
        plot_heatmap(results, out_dir, args.ngram, False)
        plot_trajectories(results, out_dir, args.ngram, True, args.n_quartiles)
        plot_heatmap(results, out_dir, args.ngram, True)

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=2))
        print(f"\nJSON saved to {args.json}")


if __name__ == "__main__":
    main()
