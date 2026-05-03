#!/usr/bin/env python3
"""Compute strict 60-minute lexical metrics in fixed time bins up to 5-grams."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/moltbook-cache")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent
ANALYSIS_DIR = SCRIPT_DIR.parent / "analysis"
for path in (SCRIPT_DIR, ANALYSIS_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from load_entropy_data import CONDITION_LABELS, CONDITION_ORDER, SCALE_CONFIG, load_all_scales  # noqa: E402
from time_binned_lexical_metrics_5gram import (  # noqa: E402
    fixed_time_bins,
    lexical_metrics,
    prepare_posts,
    subsampled_distinct_n,
)

DEFAULT_OUT_DIR = Path("findings/entropy-collapse-multiscale-new-5gram")
PLOT_COLORS = {
    "n10": "#1f77b4",
    "n20": "#ff7f0e",
    "n30": "#2ca02c",
}
DISTINCT_METRICS = ("distinct_1", "distinct_2", "distinct_3", "distinct_4", "distinct_5")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    parser.add_argument("--scales", default="n10,n20,n30")
    parser.add_argument("--bin-edges", default="0,15,30,45,60")
    parser.add_argument("--max-minutes", type=float, default=60.0)
    parser.add_argument("--seed", type=int, default=1337)
    parser.add_argument("--n-samples", type=int, default=100)
    parser.add_argument("--data-dir", type=str, default=None,
                        help="Override data directory. If it contains n10/n20/n30 subdirs they are auto-detected; otherwise it is treated as a single-scale dir.")
    return parser.parse_args()


def parse_bin_edges(value: str) -> list[float]:
    edges = [float(part.strip()) for part in value.split(",") if part.strip()]
    if len(edges) < 2:
        raise ValueError("bin edges require at least two values")
    if sorted(edges) != edges:
        raise ValueError("bin edges must be sorted")
    return edges


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row})
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def aggregate_bin_means(rows: list[dict], value_map: dict[str, str]) -> list[dict]:
    grouped: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["scale"], int(row["bin_idx"]))].append(row)

    summary_rows: list[dict] = []
    for (scale, bin_idx), group_rows in sorted(grouped.items()):
        first = group_rows[0]
        summary = {
            "scale": scale,
            "bin_idx": bin_idx,
            "bin_label": first["bin_label"],
            "bin_start_min": first["bin_start_min"],
            "bin_end_min": first["bin_end_min"],
            "n_runs_present": len(group_rows),
        }
        for source_key, output_key in value_map.items():
            summary[output_key] = safe_mean([float(row[source_key]) for row in group_rows])
        summary_rows.append(summary)
    return summary_rows


def plot_distinct(
    summary_rows: list[dict],
    *,
    out_path: Path,
    title: str,
    metric_keys: tuple[str, ...],
) -> None:
    fig, axes = plt.subplots(1, len(metric_keys), figsize=(5 * len(metric_keys), 4.5), sharex=False)
    if len(metric_keys) == 1:
        axes = [axes]
    metric_labels = [
        (metric_keys[0], "Distinct-1"),
        (metric_keys[1], "Distinct-2"),
        (metric_keys[2], "Distinct-3"),
        (metric_keys[3], "Distinct-4"),
        (metric_keys[4], "Distinct-5"),
    ]
    for ax, (metric_key, metric_title) in zip(axes, metric_labels):
        for scale in sorted({row["scale"] for row in summary_rows}):
            rows = sorted(
                [row for row in summary_rows if row["scale"] == scale],
                key=lambda row: int(row["bin_idx"]),
            )
            if not rows:
                continue
            x = [str(row["bin_label"]) for row in rows]
            y = [float(row[metric_key]) for row in rows]
            ax.plot(x, y, marker="o", linewidth=2.0, color=PLOT_COLORS.get(scale), label=scale)
        ax.set_title(metric_title)
        ax.grid(alpha=0.25)
    axes[0].set_ylabel("Mean distinct-n")
    axes[0].legend()
    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    bin_edges = parse_bin_edges(args.bin_edges)

    out_dir = Path(args.out_dir)
    plots_dir = out_dir / "plots"
    out_dir.mkdir(parents=True, exist_ok=True)
    plots_dir.mkdir(parents=True, exist_ok=True)

    include_scales = [scale.strip() for scale in args.scales.split(",") if scale.strip()]
    scale_dirs = SCALE_CONFIG
    if args.data_dir:
        base = Path(args.data_dir)
        if any((base / s).is_dir() for s in include_scales):
            scale_dirs = {s: base / s for s in include_scales if (base / s).is_dir()}
            include_scales = sorted(scale_dirs.keys())
        else:
            scale_dirs = {s: base for s in include_scales}
    records = load_all_scales(scale_dirs=scale_dirs, include_scales=include_scales)
    agent_records = [record for record in records if not record.is_seed]
    prepared = prepare_posts(agent_records)

    by_run: dict[tuple[str, str, str], list] = defaultdict(list)
    for post in prepared:
        if 0.0 <= float(post.record.minutes_elapsed) <= args.max_minutes:
            by_run[(post.record.scale, post.record.condition, post.record.run_name)].append(post)

    raw_rows: list[dict] = []
    subsampled_rows: list[dict] = []
    run_metadata_rows: list[dict] = []
    metrics_json: dict[str, dict] = {
        "meta": {
            "bin_edges": bin_edges,
            "max_minutes": args.max_minutes,
            "n_samples": args.n_samples,
            "scales": include_scales,
        },
        "runs": {},
    }

    distinct_seed_offsets = {
        1: 11,
        2: 23,
        3: 37,
        4: 53,
        5: 71,
    }

    for scale in sorted(include_scales):
        for condition in CONDITION_ORDER:
            run_keys = sorted(key for key in by_run if key[0] == scale and key[1] == condition)
            for _, _, run_name in run_keys:
                posts = sorted(by_run[(scale, condition, run_name)], key=lambda post: post.record.minutes_elapsed)
                bins = fixed_time_bins(posts, bin_edges=bin_edges)
                nonempty_bins = [(idx, start, end, members) for idx, start, end, members in bins if members]
                target_size = min((len(members) for _, _, _, members in nonempty_bins), default=0)

                run_metadata_rows.append(
                    {
                        "scale": scale,
                        "condition": condition,
                        "condition_label": CONDITION_LABELS.get(condition, condition),
                        "run_name": run_name,
                        "posts_within_60m": len(posts),
                        "n_nonempty_bins": len(nonempty_bins),
                        "subsample_target_posts": target_size,
                    }
                )

                run_json = {
                    "scale": scale,
                    "condition": condition,
                    "condition_label": CONDITION_LABELS.get(condition, condition),
                    "run_name": run_name,
                    "posts_within_60m": len(posts),
                    "subsample_target_posts": target_size,
                    "bins": [],
                }

                for bin_idx, start, end, members in bins:
                    bin_label = f"{int(start)}-{int(end)}"
                    raw_metrics = lexical_metrics(members)
                    raw_row = {
                        "scale": scale,
                        "condition": condition,
                        "condition_label": CONDITION_LABELS.get(condition, condition),
                        "run_name": run_name,
                        "bin_idx": bin_idx,
                        "bin_start_min": start,
                        "bin_end_min": end,
                        "bin_label": bin_label,
                        **raw_metrics,
                    }
                    raw_rows.append(raw_row)

                    subsampled_metrics = {}
                    for n in range(1, 6):
                        subsampled_metrics[n] = subsampled_distinct_n(
                            members,
                            n,
                            target_size,
                            n_samples=args.n_samples,
                            seed=args.seed + bin_idx + distinct_seed_offsets[n],
                        )

                    subsampled_row = {
                        "scale": scale,
                        "condition": condition,
                        "condition_label": CONDITION_LABELS.get(condition, condition),
                        "run_name": run_name,
                        "bin_idx": bin_idx,
                        "bin_start_min": start,
                        "bin_end_min": end,
                        "bin_label": bin_label,
                        "n_posts": len(members),
                        "subsample_target_posts": target_size,
                    }
                    for n in range(1, 6):
                        subsampled_row[f"distinct_{n}_mean"] = subsampled_metrics[n]["mean"]
                        subsampled_row[f"distinct_{n}_ci_lo"] = subsampled_metrics[n]["ci_lo"]
                        subsampled_row[f"distinct_{n}_ci_hi"] = subsampled_metrics[n]["ci_hi"]
                    subsampled_rows.append(subsampled_row)

                    run_json["bins"].append(
                        {
                            "bin_idx": bin_idx,
                            "bin_label": bin_label,
                            "bin_start_min": start,
                            "bin_end_min": end,
                            "raw": raw_metrics,
                            "subsampled": {
                                "target_posts": target_size,
                                **{
                                    f"distinct_{n}": {
                                        key: subsampled_metrics[n][key]
                                        for key in ("mean", "ci_lo", "ci_hi")
                                    }
                                    for n in range(1, 6)
                                },
                            },
                        }
                    )

                metrics_json["runs"][f"{scale}:{condition}:{run_name}"] = run_json

    raw_summary_rows = aggregate_bin_means(
        [row for row in raw_rows if int(row["n_posts"]) > 0],
        value_map={
            "n_posts": "n_posts_mean",
            "distinct_1": "distinct_1_mean",
            "distinct_2": "distinct_2_mean",
            "distinct_3": "distinct_3_mean",
            "distinct_4": "distinct_4_mean",
            "distinct_5": "distinct_5_mean",
        },
    )
    subsampled_summary_rows = aggregate_bin_means(
        [row for row in subsampled_rows if int(row["n_posts"]) > 0 and int(row["subsample_target_posts"]) > 0],
        value_map={
            "distinct_1_mean": "distinct_1_mean",
            "distinct_2_mean": "distinct_2_mean",
            "distinct_3_mean": "distinct_3_mean",
            "distinct_4_mean": "distinct_4_mean",
            "distinct_5_mean": "distinct_5_mean",
        },
    )

    write_csv(out_dir / "raw_time_bin_metrics.csv", raw_rows)
    write_csv(out_dir / "subsampled_time_bin_metrics.csv", subsampled_rows)
    write_csv(out_dir / "scale_bin_means_raw.csv", raw_summary_rows)
    write_csv(out_dir / "scale_bin_means_subsampled.csv", subsampled_summary_rows)
    write_csv(out_dir / "run_metadata.csv", run_metadata_rows)
    (out_dir / "metrics.json").write_text(json.dumps(metrics_json, indent=2))

    plot_distinct(
        raw_summary_rows,
        out_path=plots_dir / "distinct_n_raw_by_scale.png",
        title="Raw distinct-n by fixed 15-minute bin (1-5 grams)",
        metric_keys=tuple(f"{metric}_mean" for metric in DISTINCT_METRICS),
    )
    plot_distinct(
        subsampled_summary_rows,
        out_path=plots_dir / "distinct_n_subsampled_by_scale.png",
        title="Subsampled distinct-n by fixed 15-minute bin (1-5 grams)",
        metric_keys=tuple(f"{metric}_mean" for metric in DISTINCT_METRICS),
    )


if __name__ == "__main__":
    main()
