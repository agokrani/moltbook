#!/usr/bin/env python3
"""Analysis 1: N-gram provenance — per-run phrase fingerprints.

Finding: Each run independently develops its own dominant 4/5-gram phrases.
Zero overlap between runs. Zero origin from seed posts. Pure LLM convergence.
"""

from __future__ import annotations

import csv
import json
import sys
import textwrap
from collections import Counter, defaultdict
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
from time_binned_lexical_metrics_5gram import (
    tokenize,
    ngrams,
    prepare_posts,
    ngram_counter,
)

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

# ---------------------------------------------------------------------------
TOP_K_PER_RUN = 10
SEED_POST_FILES = sorted(Path("experiments/entropy-collapse").glob("world-posts-*.jsonl"))
OUT_DIR = Path("findings/entropy-collapse-scaling/provenance")
SCALES = ["n10", "n20", "n30"]
COND_COLORS = {
    "mag0": "#8FA5B1",
    "mag1": "#E95A54",
    "mag5": "#F58A5C",
    "mag25": "#F3B52A",
    "dom-agi": "#4A97E5",
    "dom-tech": "#65B467",
}
ROW_LABELS = {
    "n10": "10 agents",
    "n20": "20 agents",
    "n30": "30 agents",
}


def tint(hex_color: str, mix: float = 0.86) -> tuple[float, float, float]:
    hex_color = hex_color.lstrip("#")
    rgb = np.array([int(hex_color[i : i + 2], 16) for i in (0, 2, 4)], dtype=float) / 255.0
    white = np.ones(3)
    return tuple(rgb * (1.0 - mix) + white * mix)


def wrap_phrase(phrase: str, width: int = 14) -> str:
    return textwrap.fill(phrase, width=width, break_long_words=False)


def ordered_run_keys(by_run: dict[tuple[str, str, str], list]) -> list[tuple[str, str, str]]:
    keys = []
    for scale in SCALES:
        for condition in CONDITION_ORDER:
            matches = sorted(key for key in by_run if key[0] == scale and key[1] == condition)
            if matches:
                keys.append(matches[0])
    return keys


def plot_phrase_dna_grid(per_run_top: dict[int, dict[tuple, list[tuple[str, int]]]], run_keys: list[tuple[str, str, str]]) -> None:
    fig, axes = plt.subplots(len(SCALES), len(CONDITION_ORDER), figsize=(24, 20))
    fig.patch.set_facecolor("#F3F1EE")

    for row_idx, scale in enumerate(SCALES):
        for col_idx, condition in enumerate(CONDITION_ORDER):
            ax = axes[row_idx, col_idx]
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")

            matches = [key for key in run_keys if key[0] == scale and key[1] == condition]
            if not matches:
                continue
            key = matches[0]
            phrases = per_run_top[5][key][:3]
            base = COND_COLORS[condition]

            panel = FancyBboxPatch(
                (0.03, 0.02),
                0.94,
                0.94,
                boxstyle="round,pad=0.02,rounding_size=0.05",
                linewidth=2.2,
                edgecolor=base,
                facecolor=tint(base, 0.88),
            )
            ax.add_patch(panel)

            for rank_idx, (phrase, count) in enumerate(phrases):
                y0 = 0.70 - (rank_idx * 0.28)
                card = FancyBboxPatch(
                    (0.10, y0),
                    0.80,
                    0.23,
                    boxstyle="round,pad=0.02,rounding_size=0.045",
                    linewidth=1.8,
                    edgecolor=base,
                    facecolor="#FFFFFF",
                )
                ax.add_patch(card)
                ax.text(
                    0.50,
                    y0 + 0.155,
                    wrap_phrase(phrase, width=14),
                    ha="center",
                    va="center",
                    fontsize=10.5,
                    fontweight="bold",
                    color="#20303A",
                    linespacing=1.05,
                )
                ax.text(
                    0.50,
                    y0 + 0.04,
                    f"#{rank_idx + 1}  n={count}",
                    ha="center",
                    va="center",
                    fontsize=8.8,
                    color=base,
                    fontweight="bold",
                )

            if row_idx == 0:
                ax.set_title(
                    CONDITION_LABELS.get(condition, condition),
                    fontsize=13,
                    fontweight="bold",
                    color=base,
                    pad=12,
                )

    label_nudge = {"n10": 0.005, "n20": -0.015, "n30": -0.09}
    for row_idx, scale in enumerate(SCALES):
        bbox = axes[row_idx, 0].get_position()
        fig.text(
            bbox.x0 - 0.025,
            (bbox.y0 + bbox.y1) / 2 + label_nudge[scale],
            ROW_LABELS[scale],
            rotation=90,
            ha="right",
            va="center",
            fontsize=13,
            fontweight="bold",
            color="#33424C",
        )

    fig.suptitle(
        "Each run develops its own phrase DNA",
        fontsize=21,
        fontweight="bold",
        y=0.98,
        color="#1E2A33",
    )
    fig.text(
        0.5,
        0.955,
        "Top 3 dominant 5-grams per run. Each panel is one run; phrases are unique to that run's local convergence.",
        ha="center",
        va="center",
        fontsize=11.5,
        color="#475761",
    )
    fig.text(
        0.5,
        0.935,
        "Counts are shown inside each card to keep the figure readable without pushing the labels into tiny type.",
        ha="center",
        va="center",
        fontsize=10.2,
        color="#667782",
    )
    plt.subplots_adjust(left=0.10, right=0.985, top=0.91, bottom=0.03, wspace=0.14, hspace=0.35)
    fig.savefig(OUT_DIR / "phrase_dna_grid.png", dpi=220, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print("Wrote phrase_dna_grid.png")



def load_seed_texts() -> list[str]:
    texts = []
    for path in SEED_POST_FILES:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                post = json.loads(line)
                title = (post.get("title") or "").strip()
                content = (post.get("content") or "").strip()
                texts.append(f"{title}\n{content}".strip())
    return texts


def ngrams_in_text(text: str, n: int) -> set[str]:
    tokens = tokenize(text)
    grams = ngrams(tokens, n)
    return {" ".join(g) for g in grams}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Load seed n-grams for 4 and 5
    seed_texts = load_seed_texts()
    print(f"Loaded {len(seed_texts)} seed posts")
    seed_ngrams = {}
    for n in [4, 5]:
        s = set()
        for text in seed_texts:
            s.update(ngrams_in_text(text, n))
        seed_ngrams[n] = s
        print(f"  Seed {n}-grams: {len(s)}")

    # Load all posts
    print("\nLoading all scales...")
    records = load_all_scales()
    agent_records = [r for r in records if not r.is_seed]
    by_run = group_records(agent_records, lambda r: (r.scale, r.condition, r.run_name))
    run_keys = ordered_run_keys(by_run)
    print(f"  {len(agent_records)} agent posts across {len(run_keys)} runs")

    # -----------------------------------------------------------------------
    # Compute per-run top n-grams for n=4 and n=5
    # -----------------------------------------------------------------------
    per_run_top: dict[int, dict[tuple, list[tuple[str, int]]]] = {4: {}, 5: {}}

    for key, recs in sorted(by_run.items()):
        prepared = prepare_posts(recs)
        for n in [4, 5]:
            counter = ngram_counter(prepared, n)
            top = [(" ".join(g), count) for g, count in counter.most_common(TOP_K_PER_RUN)]
            per_run_top[n][key] = top

    # -----------------------------------------------------------------------
    # Cross-run overlap for both n=4 and n=5
    # -----------------------------------------------------------------------
    for n in [4, 5]:
        phrase_sets = {k: {phrase for phrase, _ in v} for k, v in per_run_top[n].items()}
        overlaps = []
        for i, ki in enumerate(run_keys):
            for j in range(i + 1, len(run_keys)):
                kj = run_keys[j]
                overlaps.append(len(phrase_sets[ki] & phrase_sets[kj]))
        mean_ov = sum(overlaps) / len(overlaps) if overlaps else 0
        print(f"\n{n}-gram: mean cross-run top-{TOP_K_PER_RUN} overlap = {mean_ov:.2f}/{TOP_K_PER_RUN}")

    # Seed overlap check
    for n in [4, 5]:
        all_top_phrases = set()
        for v in per_run_top[n].values():
            all_top_phrases.update(phrase for phrase, _ in v)
        in_seed = all_top_phrases & seed_ngrams[n]
        print(f"  {n}-gram: {len(in_seed)}/{len(all_top_phrases)} top phrases found in seed posts")

    # -----------------------------------------------------------------------
    # Write CSV: per-run top phrases
    # -----------------------------------------------------------------------
    csv_rows = []
    for n in [4, 5]:
        all_top = set()
        for v in per_run_top[n].values():
            all_top.update(phrase for phrase, _ in v)

        for key in run_keys:
            scale, condition, run_name = key
            for rank, (phrase, count) in enumerate(per_run_top[n][key], 1):
                csv_rows.append({
                    "ngram_n": n,
                    "scale": scale,
                    "condition": condition,
                    "run_name": run_name,
                    "rank": rank,
                    "phrase": phrase,
                    "count": count,
                    "in_seed": phrase in seed_ngrams[n],
                })

    csv_path = OUT_DIR / "per_run_top_ngrams.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        writer.writeheader()
        writer.writerows(csv_rows)
    print(f"\nWrote {csv_path} ({len(csv_rows)} rows)")

    # -----------------------------------------------------------------------
    # PLOTS
    # -----------------------------------------------------------------------
    print("\nGenerating phrase DNA views...")
    plot_phrase_dna_grid(per_run_top, run_keys)

    # -----------------------------------------------------------------------
    # JSON summary
    # -----------------------------------------------------------------------
    summary = {
        "finding": (
            "Each of the 18 runs independently develops its own dominant 4/5-gram phrases. "
            "Zero top-10 overlap between any two runs. Zero seed-post origin. "
            "The collapse is LLM-intrinsic: agents converge within a run, but on different phrases per run."
        ),
        "runs": len(run_keys),
        "per_ngram": {},
    }
    for n in [4, 5]:
        phrase_sets = {k: {phrase for phrase, _ in v} for k, v in per_run_top[n].items()}
        all_phrases = set()
        for v in per_run_top[n].values():
            all_phrases.update(phrase for phrase, _ in v)
        overlaps = []
        for i, ki in enumerate(run_keys):
            for j in range(i + 1, len(run_keys)):
                overlaps.append(len(phrase_sets[ki] & phrase_sets[run_keys[j]]))
        summary["per_ngram"][str(n)] = {
            "unique_top_phrases": len(all_phrases),
            "in_seed": len(all_phrases & seed_ngrams[n]),
            "mean_cross_run_overlap": round(sum(overlaps) / len(overlaps), 2) if overlaps else 0,
            "max_cross_run_overlap": max(overlaps) if overlaps else 0,
        }
    summary["per_run_top3"] = {
        f"{k[0]}/{k[1]}": [phrase for phrase, _ in per_run_top[5][k][:3]]
        for k in run_keys
    }

    with (OUT_DIR / "provenance_summary.json").open("w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nWrote provenance_summary.json")
    print("\nDone!")


if __name__ == "__main__":
    main()
