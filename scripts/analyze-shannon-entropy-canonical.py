#!/usr/bin/env python3
"""Canonical Shannon entropy analysis for EMNLP entropy-collapse runs.

This script reads the curated local `data/` mirrors, not raw scratch exports. It
filters every run to the first 60 minutes and uses fixed 15-minute bins, matching
`entropy-collapse-scaling` and the canonical gzip analysis.

Usage:
    python3 scripts/analyze-shannon-entropy-canonical.py \
      --data-root data \
      --output-dir findings/entropy-collapse-shannon \
      --ngrams 3 5
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_ORDER = CONDITIONS
SET_ORDER = ["GPT-5 n10", "GPT-5 n20", "GPT-5 n30", "Gemini n10", "Gemini n20", "Gemini n30", "Kimi n10", "GLM-5 n10"]
SYSTEM_PREFIXES = ("civiclens_",)
TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")

CANONICAL_DATASETS = [
    {"set": "GPT-5", "model": "gpt-5", "scale": "n10", "path": "moltbook-entropy-collapse-v2/data", "nested_scales": False},
    {"set": "GPT-5", "model": "gpt-5", "scale": "n20", "path": "moltbook-entropy-collapse-20agents/data", "nested_scales": False},
    {"set": "GPT-5", "model": "gpt-5", "scale": "n30", "path": "moltbook-entropy-collapse-30agents/data", "nested_scales": False},
    {"set": "Gemini", "model": "google/gemini-3.1-flash-lite-preview", "scale": None, "path": "moltbook-entropy-collapse-gemini-flash-lite/data", "nested_scales": True},
    {"set": "Kimi", "model": "moonshotai/kimi-k2.5", "scale": "n10", "path": "moltbook-entropy-collapse-kimi-k2.5/data", "nested_scales": False},
    {"set": "GLM-5", "model": "z-ai/glm-5", "scale": "n10", "path": "moltbook-entropy-collapse-glm-5/data", "nested_scales": False},
]

PALETTE = ["#2ecc71", "#e74c3c", "#e67e22", "#9b59b6", "#3498db", "#1abc9c", "#f39c12", "#c0392b"]
MARKERS = ["s", "o", "^", "D", "v", "P", "X", "*"]


def parse_time(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def read_metadata(exp_dir: Path) -> dict:
    meta_path = exp_dir / "metadata.json"
    if not meta_path.exists():
        return {}
    try:
        return json.loads(meta_path.read_text())
    except Exception:
        return {}


def extract_condition(exp_dir: Path, meta: dict) -> str:
    if meta.get("condition"):
        return meta["condition"]
    for cond in CONDITIONS:
        if cond in exp_dir.name:
            return cond
    return exp_dir.name


def discover_runs(data_root: Path) -> List[dict]:
    runs: List[dict] = []
    for spec in CANONICAL_DATASETS:
        base = data_root / spec["path"]
        if not base.exists():
            raise FileNotFoundError(f"Canonical data path not found: {base}")
        if spec["nested_scales"]:
            for scale_dir in sorted(d for d in base.iterdir() if d.is_dir()):
                for exp_dir in sorted(d for d in scale_dir.iterdir() if d.is_dir()):
                    meta = read_metadata(exp_dir)
                    runs.append({
                        "set": spec["set"], "model": meta.get("model") or spec["model"],
                        "scale": scale_dir.name, "condition": extract_condition(exp_dir, meta),
                        "experiment": exp_dir.name, "path": exp_dir,
                        "metadata_duration_minutes": meta.get("duration_minutes"),
                    })
        else:
            for exp_dir in sorted(d for d in base.iterdir() if d.is_dir()):
                meta = read_metadata(exp_dir)
                runs.append({
                    "set": spec["set"], "model": meta.get("model") or spec["model"],
                    "scale": spec["scale"], "condition": extract_condition(exp_dir, meta),
                    "experiment": exp_dir.name, "path": exp_dir,
                    "metadata_duration_minutes": meta.get("duration_minutes"),
                })
    return runs


def load_agent_posts(exp_dir: Path) -> List[dict]:
    posts_path = exp_dir / "posts.jsonl"
    posts: List[dict] = []
    with posts_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            post = json.loads(line)
            author = post.get("author_name", "") or ""
            if author.startswith(SYSTEM_PREFIXES):
                continue
            if not post.get("created_at"):
                continue
            posts.append(post)
    return posts


def filter_first_hour(posts: List[dict], minutes: int = 60) -> Tuple[List[dict], Optional[datetime]]:
    if not posts:
        return [], None
    sorted_posts = sorted(posts, key=lambda p: parse_time(p["created_at"]))
    start = parse_time(sorted_posts[0]["created_at"])
    end = start + timedelta(minutes=minutes)
    return [p for p in sorted_posts if parse_time(p["created_at"]) <= end], start


def split_fixed_bins(posts: List[dict], start: datetime) -> List[List[dict]]:
    bins: List[List[dict]] = [[] for _ in range(4)]
    for post in posts:
        elapsed = (parse_time(post["created_at"]) - start).total_seconds() / 60.0
        if elapsed < 0 or elapsed > 60:
            continue
        idx = 0 if elapsed < 15 else 1 if elapsed < 30 else 2 if elapsed < 45 else 3
        bins[idx].append(post)
    return bins


def tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall(text.lower())


def post_text(post: dict) -> str:
    return f"{post.get('title', '') or ''} {post.get('content', '') or ''}"


def ngram_counts(posts: List[dict], n: int) -> Counter:
    counts: Counter = Counter()
    for post in posts:
        toks = tokenize(post_text(post))
        if len(toks) < n:
            continue
        counts.update(tuple(toks[i:i+n]) for i in range(len(toks) - n + 1))
    return counts


def shannon_entropy_bits(counts: Counter) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for c in counts.values():
        p = c / total
        h -= p * math.log2(p)
    return h


def normalized_entropy(h: float, vocab_size: int) -> float:
    if vocab_size <= 1:
        return 0.0
    return h / math.log2(vocab_size)


def compute_run(run: dict, n: int, first_minutes: int) -> Optional[dict]:
    all_posts = load_agent_posts(run["path"])
    first_posts, start = filter_first_hour(all_posts, first_minutes)
    if not first_posts or start is None:
        return None
    bins_posts = split_fixed_bins(first_posts, start)
    bins = []
    for idx, chunk in enumerate(bins_posts):
        counts = ngram_counts(chunk, n)
        total_ngrams = sum(counts.values())
        vocab_size = len(counts)
        h = shannon_entropy_bits(counts)
        h_norm = normalized_entropy(h, vocab_size)
        bins.append({
            "bin_idx": idx,
            "bin_start_min": idx * 15,
            "bin_end_min": (idx + 1) * 15,
            "n_posts": len(chunk),
            "total_ngrams": total_ngrams,
            "vocab_size": vocab_size,
            "entropy": round(h, 6),
            "entropy_norm": round(h_norm, 6),
        })
    return {
        "experiment": run["experiment"], "condition": run["condition"],
        "scale": run["scale"], "set": run["set"], "model": run["model"],
        "source_path": str(run["path"]), "metadata_duration_minutes": run["metadata_duration_minutes"],
        "first_post_at": start.isoformat(), "first_minutes": first_minutes,
        "ngram": n, "n_agent_posts_total_export": len(all_posts), "n_posts": len(first_posts),
        "n_posts_excluded_after_first_window": len(all_posts) - len(first_posts),
        "bins": bins,
        "entropy_values": [b["entropy"] for b in bins],
        "entropy_norm_values": [b["entropy_norm"] for b in bins],
        "delta": round(bins[-1]["entropy"] - bins[0]["entropy"], 6),
        "delta_norm": round(bins[-1]["entropy_norm"] - bins[0]["entropy_norm"], 6),
    }


def validate_inventory(results: List[dict]) -> None:
    if len(results) != 48:
        raise RuntimeError(f"Expected 48 canonical runs, got {len(results)}")
    expected = {("GPT-5", "n10"): 6, ("GPT-5", "n20"): 6, ("GPT-5", "n30"): 6,
                ("Gemini", "n10"): 6, ("Gemini", "n20"): 6, ("Gemini", "n30"): 6,
                ("Kimi", "n10"): 6, ("GLM-5", "n10"): 6}
    actual: Dict[Tuple[str, str], int] = {}
    for r in results:
        actual[(r["set"], r["scale"])] = actual.get((r["set"], r["scale"]), 0) + 1
    if actual != expected:
        raise RuntimeError(f"Inventory mismatch: {actual}")


def sign_test_p(k: int, n: int) -> float:
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def bootstrap_ci(vals: List[float], seed: int = 42, B: int = 20000) -> Tuple[float, float]:
    rng = random.Random(seed)
    n = len(vals)
    means = [sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(B)]
    means.sort()
    return means[int(0.025 * B)], means[int(0.975 * B)]


def summarize(results: List[dict]) -> dict:
    deltas = [r["delta"] for r in results]
    deltas_norm = [r["delta_norm"] for r in results]
    first = [r["bins"][0]["entropy"] for r in results]
    final = [r["bins"][-1]["entropy"] for r in results]
    first_norm = [r["bins"][0]["entropy_norm"] for r in results]
    final_norm = [r["bins"][-1]["entropy_norm"] for r in results]
    k = sum(1 for d in deltas if d < 0)
    k_norm = sum(1 for d in deltas_norm if d < 0)
    ci = bootstrap_ci(deltas)
    ci_norm = bootstrap_ci(deltas_norm)
    return {
        "runs": len(results),
        "agent_posts_first60": sum(r["n_posts"] for r in results),
        "excluded_after_first60": sum(r["n_posts_excluded_after_first_window"] for r in results),
        "declines": k,
        "declines_norm": k_norm,
        "mean_first_entropy": round(statistics.mean(first), 6),
        "mean_final_entropy": round(statistics.mean(final), 6),
        "mean_delta": round(statistics.mean(deltas), 6),
        "median_delta": round(statistics.median(deltas), 6),
        "bootstrap_mean_delta_ci95": [round(ci[0], 6), round(ci[1], 6)],
        "sign_test_two_sided_p_for_decline": sign_test_p(k, len(results)),
        "mean_first_entropy_norm": round(statistics.mean(first_norm), 6),
        "mean_final_entropy_norm": round(statistics.mean(final_norm), 6),
        "mean_delta_norm": round(statistics.mean(deltas_norm), 6),
        "median_delta_norm": round(statistics.median(deltas_norm), 6),
        "bootstrap_mean_delta_norm_ci95": [round(ci_norm[0], 6), round(ci_norm[1], 6)],
        "sign_test_two_sided_p_for_norm_decline": sign_test_p(k_norm, len(results)),
        "non_declining_runs": [
            {"set": r["set"], "scale": r["scale"], "condition": r["condition"], "experiment": r["experiment"], "delta": r["delta"]}
            for r in results if r["delta"] >= 0
        ],
    }


def label(r: dict) -> str:
    return f"{r['set']} {r['scale']}"


def ordered(values, preferred):
    return [v for v in preferred if v in values] + sorted(v for v in values if v not in preferred)


def plot_trajectories(results: List[dict], out_dir: Path, n: int, normalized: bool = False) -> None:
    metric = "entropy_norm" if normalized else "entropy"
    suffix = "norm" if normalized else "raw"
    conditions = ordered(set(r["condition"] for r in results), CONDITION_ORDER)
    labels = ordered(set(label(r) for r in results), SET_ORDER)
    fig, axes = plt.subplots(2, 3, figsize=(19, 10), sharey=True, squeeze=False)
    fig.suptitle(f"Canonical Shannon entropy ({n}-gram, {'normalized' if normalized else 'raw bits'})", fontsize=14, fontweight="bold")
    xs = [1, 2, 3, 4]
    for idx, cond in enumerate(conditions):
        ax = axes[idx // 3][idx % 3]
        ax.set_title(cond.upper(), fontweight="bold")
        ax.set_xticks(xs)
        ax.set_xticklabels(["0–15", "15–30", "30–45", "45–60"])
        ax.grid(True, alpha=0.25)
        if idx % 3 == 0:
            ax.set_ylabel("Shannon entropy")
        for li, lab in enumerate(labels):
            ms = [r for r in results if r["condition"] == cond and label(r) == lab]
            if not ms:
                continue
            r = ms[0]
            vals = [b[metric] for b in r["bins"]]
            ax.plot(xs, vals, color=PALETTE[li % len(PALETTE)], marker=MARKERS[li % len(MARKERS)], linewidth=1.5, markersize=5, label=f"{lab} ({r['delta' if not normalized else 'delta_norm']:+.2f})")
        ax.legend(fontsize=6)
    plt.tight_layout(rect=[0, 0, 1, 0.94])
    out = out_dir / f"shannon_entropy_{n}gram_{suffix}_trajectories.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def plot_heatmap(results: List[dict], out_dir: Path, n: int, normalized: bool = False) -> None:
    delta_key = "delta_norm" if normalized else "delta"
    suffix = "norm" if normalized else "raw"
    conditions = ordered(set(r["condition"] for r in results), CONDITION_ORDER)
    labels = ordered(set(label(r) for r in results), SET_ORDER)
    arr = []
    for lab in labels:
        row = []
        for cond in conditions:
            ms = [r for r in results if r["condition"] == cond and label(r) == lab]
            row.append(ms[0][delta_key] if ms else np.nan)
        arr.append(row)
    arr = np.array(arr)
    fig, ax = plt.subplots(figsize=(9, 7))
    vmax = max(abs(np.nanmin(arr)), abs(np.nanmax(arr))) or 1
    im = ax.imshow(arr, cmap="RdYlGn", aspect="auto", vmin=-vmax, vmax=vmax)
    ax.set_xticks(range(len(conditions)))
    ax.set_xticklabels([c.upper() for c in conditions])
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    for i in range(len(labels)):
        for j in range(len(conditions)):
            val = arr[i, j]
            ax.text(j, i, f"{val:+.2f}" if not normalized else f"{val:+.3f}", ha="center", va="center", fontsize=8)
    ax.set_title(f"Canonical Shannon entropy delta ({n}-gram, {'normalized' if normalized else 'raw'}): final − first", fontweight="bold")
    plt.colorbar(im, ax=ax, label="Delta; negative = lower entropy")
    plt.tight_layout()
    out = out_dir / f"shannon_entropy_{n}gram_{suffix}_heatmap.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Canonical Shannon entropy analysis")
    parser.add_argument("--data-root", default="data")
    parser.add_argument("--output-dir", default="findings/entropy-collapse-shannon")
    parser.add_argument("--ngrams", nargs="+", type=int, default=[3, 5])
    parser.add_argument("--first-minutes", type=int, default=60)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    runs = discover_runs(Path(args.data_root))

    all_summaries = {}
    for n in args.ngrams:
        print(f"\nComputing canonical Shannon entropy for {n}-grams")
        results = []
        for run in runs:
            result = compute_run(run, n, args.first_minutes)
            if result is None:
                continue
            results.append(result)
            print(f"{result['set']:7s} {result['scale']:3s} {result['condition']:8s} {result['experiment']:32s} posts={result['n_posts']:4d} excluded={result['n_posts_excluded_after_first_window']:4d} H Δ={result['delta']:+.3f}")
        validate_inventory(results)
        output = {
            "meta": {
                "analysis": "canonical_first_60_minute_shannon_entropy",
                "ngram": n,
                "first_minutes": args.first_minutes,
                "binning": "fixed_15_minute_bins_after_first_agent_post",
                "data_root": args.data_root,
                "canonical_datasets": CANONICAL_DATASETS,
                "tokenizer": "lowercase regex tokens: [a-z0-9]+(?:'[a-z0-9]+)?",
            },
            "summary": summarize(results),
            "results": results,
        }
        (out_dir / f"results-{n}gram-canonical-48.json").write_text(json.dumps(output, indent=2))
        all_summaries[f"{n}gram"] = output["summary"]
        plot_trajectories(results, out_dir, n, normalized=False)
        plot_trajectories(results, out_dir, n, normalized=True)
        plot_heatmap(results, out_dir, n, normalized=False)
        plot_heatmap(results, out_dir, n, normalized=True)

    (out_dir / "summary.json").write_text(json.dumps(all_summaries, indent=2))
    print(f"\nWrote canonical Shannon outputs to {out_dir}")


if __name__ == "__main__":
    main()
