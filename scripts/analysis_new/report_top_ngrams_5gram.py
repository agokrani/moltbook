#!/usr/bin/env python3
"""Export top 2-5 grams for the strict 60-minute lexical corpus."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPT_DIR.parent / "analysis"
for path in (SCRIPT_DIR, ANALYSIS_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from load_entropy_data import SCALE_CONFIG, load_all_scales  # noqa: E402
from time_binned_lexical_metrics_5gram import prepare_posts  # noqa: E402

DEFAULT_OUT_DIR = Path("findings/entropy-collapse-multiscale-new-5gram/top_ngrams")
DEFAULT_SLICES = {
    "all_0_60": lambda minutes: 0.0 <= minutes <= 60.0,
    "early_0_15": lambda minutes: 0.0 <= minutes < 15.0,
    "late_45_60": lambda minutes: 45.0 <= minutes <= 60.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--scales", default="n10,n20,n30")
    parser.add_argument("--top-k", type=int, default=100)
    return parser.parse_args()


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    include_scales = [scale.strip() for scale in args.scales.split(",") if scale.strip()]
    records = load_all_scales(scale_dirs=SCALE_CONFIG, include_scales=include_scales)
    agent_records = [record for record in records if not record.is_seed]
    prepared = prepare_posts(agent_records)

    summary: dict[str, dict[int, list[dict]]] = {}

    for slice_name, predicate in DEFAULT_SLICES.items():
        slice_posts = [post for post in prepared if predicate(float(post.record.minutes_elapsed))]
        slice_payload: dict[int, list[dict]] = {}
        for n in range(2, 6):
            counter: Counter = Counter()
            post_counter: Counter = Counter()
            for post in slice_posts:
                grams = post.ngrams_by_n[n]
                counter.update(grams)
                post_counter.update(set(grams))

            rows: list[dict] = []
            for rank, (gram, count) in enumerate(counter.most_common(args.top_k), start=1):
                rows.append(
                    {
                        "rank": rank,
                        "n": n,
                        "count": count,
                        "post_count": post_counter[gram],
                        "phrase": " ".join(gram),
                    }
                )
            slice_payload[n] = rows
            write_csv(out_dir / f"{slice_name}_{n}gram.csv", rows)
        summary[slice_name] = slice_payload

    json_ready = {
        slice_name: {
            str(n): rows
            for n, rows in payload.items()
        }
        for slice_name, payload in summary.items()
    }
    (out_dir / "top_ngrams.json").write_text(json.dumps(json_ready, indent=2))


if __name__ == "__main__":
    main()
