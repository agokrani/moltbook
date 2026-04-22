#!/usr/bin/env python3
"""
Compression-ratio analysis for MoltBook entropy collapse experiments.

Computes gzip/bzip2/zlib compression ratios per temporal quartile.
Declining ratio over time = text becoming more compressible = more
repetitive = entropy collapse.

Usage:
    python3 scripts/gzip/compute_compression.py \
        --experiments "kimi=/scratch/anangia/moltbook/results" \
        --output results.json \
        --n-quartiles 4
"""

import argparse
import bz2
import gzip
import json
import re
import sys
import zlib
from pathlib import Path

COMPRESSORS = {
    "gzip": gzip.compress,
    "bzip2": bz2.compress,
    "zlib": zlib.compress,
}

ALGORITHMS = list(COMPRESSORS.keys())


# ---------------------------------------------------------------------------
# Compression
# ---------------------------------------------------------------------------

def compression_ratio(data: bytes, algorithm: str) -> float:
    """Return compressed_size / original_size. 0.0 for empty data."""
    if not data:
        return 0.0
    compressed = COMPRESSORS[algorithm](data)
    return len(compressed) / len(data)


# ---------------------------------------------------------------------------
# Data loading (mirrors analyze-shannon-entropy.py)
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
            if not p.get("author_name", "").startswith("civiclens_"):
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
            return meta.get("condition", exp_dir.name)
        except (json.JSONDecodeError, OSError):
            pass
    name = exp_dir.name
    for cond in ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech",
                 "het-dual", "het-multi"]:
        if cond in name:
            return cond
    return name


def extract_scale(exp_dir):
    """Extract agent scale (n10/n20/n30) from directory name."""
    m = re.search(r"-n(\d+)-", exp_dir.name)
    if m:
        return f"n{m.group(1)}"
    meta_path = exp_dir / "metadata.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            n = meta.get("num_agents")
            if n:
                return f"n{n}"
        except (json.JSONDecodeError, OSError):
            pass
    return "unknown"


# ---------------------------------------------------------------------------
# Temporal binning (mirrors analyze-shannon-entropy.py)
# ---------------------------------------------------------------------------

def split_quartiles(posts, n_quartiles=4):
    """Split posts into temporal quartiles by creation time."""
    sorted_posts = sorted(posts, key=lambda p: p.get("created_at", ""))
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


# ---------------------------------------------------------------------------
# Per-experiment analysis
# ---------------------------------------------------------------------------

def post_text(p):
    """Extract full text from a post dict."""
    title = p.get("title", "") or ""
    content = p.get("content", "") or ""
    return f"{title}\n{content}"


def compute_experiment(exp_dir, algorithms, n_quartiles):
    """Compute compression ratios per quartile for one experiment."""
    exp_dir = Path(exp_dir)
    posts = load_posts(exp_dir)

    if len(posts) < n_quartiles * 2:
        return None

    quartiles = split_quartiles(posts, n_quartiles)
    bins = []

    for i, q_posts in enumerate(quartiles):
        text = "\n".join(post_text(p) for p in q_posts)
        text_bytes = text.encode("utf-8")

        ratios = {}
        for alg in algorithms:
            ratios[alg] = round(compression_ratio(text_bytes, alg), 6)

        bins.append({
            "quartile": i + 1,
            "n_posts": len(q_posts),
            "total_bytes": len(text_bytes),
            "ratios": ratios,
        })

    # Deltas: Q_last - Q1
    deltas = {}
    if len(bins) >= 2:
        for alg in algorithms:
            deltas[alg] = round(bins[-1]["ratios"][alg] - bins[0]["ratios"][alg], 6)

    return {
        "experiment": exp_dir.name,
        "condition": extract_condition(exp_dir),
        "scale": extract_scale(exp_dir),
        "n_posts": len(posts),
        "bins": bins,
        "deltas": deltas,
    }


# ---------------------------------------------------------------------------
# Analysis runner
# ---------------------------------------------------------------------------

def analyze_experiments(experiment_sets, algorithms, n_quartiles):
    """Run compression analysis across all experiment sets."""
    all_results = []

    for set_label, set_path in experiment_sets.items():
        exp_dirs = find_experiment_dirs(set_path)
        print(f"\n{set_label}: {len(exp_dirs)} experiments in {set_path}")

        for exp_dir in exp_dirs:
            result = compute_experiment(exp_dir, algorithms, n_quartiles)
            if result is None:
                print(f"  Skipping {exp_dir.name} (too few posts)")
                continue

            result["set"] = set_label
            all_results.append(result)

            # Print summary line
            ratios_q1 = result["bins"][0]["ratios"]
            ratios_q4 = result["bins"][-1]["ratios"]
            d = result["deltas"].get("gzip", 0)
            print(f"  {result['condition']:>8} {result['scale']:>4}  "
                  f"{result['n_posts']:>4} posts  "
                  f"gzip: {ratios_q1['gzip']:.4f} → {ratios_q4['gzip']:.4f}  "
                  f"Δ={d:+.4f}")

    return all_results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compression-ratio analysis for MoltBook experiments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--experiments", nargs="+", required=True,
                        help="Experiment sets as label=path")
    parser.add_argument("--n-quartiles", type=int, default=4,
                        help="Number of temporal quartiles (default: 4)")
    parser.add_argument("--output", default=None,
                        help="Path for JSON results output")
    parser.add_argument("--algorithms", default=",".join(ALGORITHMS),
                        help=f"Comma-separated algorithms (default: {','.join(ALGORITHMS)})")

    args = parser.parse_args()

    algorithms = [a.strip() for a in args.algorithms.split(",")]
    for a in algorithms:
        if a not in COMPRESSORS:
            print(f"Unknown algorithm: {a}. Choose from: {list(COMPRESSORS.keys())}")
            sys.exit(1)

    experiment_sets = {}
    for item in args.experiments:
        if "=" in item:
            label, path = item.split("=", 1)
            experiment_sets[label] = path
        else:
            experiment_sets[Path(item).name] = item

    print(f"Algorithms: {algorithms}")
    print(f"Quartiles: {args.n_quartiles}")

    results = analyze_experiments(experiment_sets, algorithms, args.n_quartiles)

    if not results:
        print("\nNo results.")
        sys.exit(0)

    # Summary table
    print(f"\n{'=' * 90}")
    print("SUMMARY")
    print(f"{'=' * 90}")

    header = f"{'Cond':<10} {'Scale':<6} {'Set':<15} {'Posts':>5}"
    for i in range(1, args.n_quartiles + 1):
        header += f"  {'Q' + str(i):>7}"
    header += f"  {'Δ(gzip)':>8}"
    print(header)
    print("-" * len(header))

    for r in sorted(results, key=lambda x: (x["condition"], x["scale"], x["set"])):
        row = f"{r['condition']:<10} {r['scale']:<6} {r['set']:<15} {r['n_posts']:>5}"
        for b in r["bins"]:
            row += f"  {b['ratios']['gzip']:>7.4f}"
        row += f"  {r['deltas'].get('gzip', 0):>+8.4f}"
        print(row)

    output = {
        "meta": {
            "algorithms": algorithms,
            "n_quartiles": args.n_quartiles,
        },
        "results": results,
    }

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(output, indent=2))
        print(f"\nJSON saved to {args.output}")
    else:
        print("\nTip: use --output results.json to save results")


if __name__ == "__main__":
    main()
