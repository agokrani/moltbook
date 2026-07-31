#!/usr/bin/env python3
"""Build the paper-style five-hour cumulative extension and ranking table."""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CUTOFFS = [15, 30, 45, 60, 120, 180, 240, 300]
CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy seed",
    "mag5": "5 conspiracy seeds",
    "mag25": "25 conspiracy seeds",
    "dom-agi": "25 AGI seeds",
    "dom-tech": "25 tech seeds",
}
SHORT_LABELS = {
    "mag0": "Empty",
    "mag1": "1 conspiracy",
    "mag5": "5 conspiracies",
    "mag25": "25 conspiracies",
    "dom-agi": "AGI",
    "dom-tech": "Tech",
}
COLORS = {
    "mag0": "#1b6b42",
    "mag1": "#3b6ea8",
    "mag5": "#f28e2b",
    "mag25": "#d94f4f",
    "dom-agi": "#7b4ea3",
    "dom-tech": "#4e9f3d",
}
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", re.I)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def distinct_5(texts: list[str]) -> float:
    total = 0
    unique: set[tuple[str, ...]] = set()
    for text in texts:
        tokens = [match.group(0).lower() for match in TOKEN_RE.finditer(text or "")]
        grams = [tuple(tokens[index : index + 5]) for index in range(max(0, len(tokens) - 4))]
        total += len(grams)
        unique.update(grams)
    return len(unique) / total if total else math.nan


def gzip_ratio(texts: list[str]) -> float:
    raw = "\n".join(text for text in texts if text).encode("utf-8")
    return len(gzip.compress(raw)) / len(raw) if raw else math.nan


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            "legend.fontsize": 9.5,
            "figure.titlesize": 15,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--data-output", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=ROOT.parent / "rebuttal/assets",
    )
    args = parser.parse_args()

    manifest = read_csv(args.analysis_root / "data_manifest.csv")
    candidates = [
        row
        for row in manifest
        if row["model_display"] == "GPT-5"
        and row["internal_family_label"] == "obsession_prompting"
        and int(row["n_agents"]) == 10
        and row["condition"] in CONDITIONS
        and float(row["duration_minutes"]) >= 240
    ]
    selected = {
        condition: max(
            (row for row in candidates if row["condition"] == condition),
            key=lambda row: row["run_id"],
        )
        for condition in CONDITIONS
    }
    run_uids = {row["run_uid"] for row in selected.values()}

    posts = pd.read_csv(
        args.analysis_root / "ayush_reanalysis/post_index.csv",
        usecols=["run_uid", "is_seed", "minutes_elapsed", "text"],
        low_memory=False,
    )
    posts = posts[
        posts["run_uid"].isin(run_uids)
        & (~posts["is_seed"].astype(bool))
        & (posts["minutes_elapsed"] >= 0)
    ].copy()
    posts["text"] = posts["text"].fillna("")

    judge = pd.read_csv(
        args.analysis_root / "ayush_reanalysis/llm_judge/blind_judge_results_with_metadata.csv",
        usecols=["run_uid", "is_seed", "minutes_elapsed", "collapse_index"],
        low_memory=False,
    )
    judge = judge[
        judge["run_uid"].isin(run_uids)
        & (~judge["is_seed"].astype(bool))
        & (judge["minutes_elapsed"] >= 0)
    ].copy()

    rows: list[dict[str, object]] = []
    for condition in CONDITIONS:
        spec = selected[condition]
        run_posts = posts[posts["run_uid"] == spec["run_uid"]].sort_values("minutes_elapsed")
        run_judge = judge[judge["run_uid"] == spec["run_uid"]].sort_values("minutes_elapsed")
        if run_posts.empty or run_judge.empty:
            raise RuntimeError(f"missing posts or judge scores for {spec['run_id']}")
        for cutoff in CUTOFFS:
            post_members = run_posts[run_posts["minutes_elapsed"] <= cutoff]
            judge_members = run_judge[run_judge["minutes_elapsed"] <= cutoff]
            texts = post_members["text"].astype(str).tolist()
            rows.append(
                {
                    "run_uid": spec["run_uid"],
                    "run_id": spec["run_id"],
                    "condition": condition,
                    "duration_minutes": float(spec["duration_minutes"]),
                    "cutoff_minutes": cutoff,
                    "n_posts_cumulative": len(post_members),
                    "n_judged_cumulative": len(judge_members),
                    "distinct_5_cumulative": distinct_5(texts),
                    "gzip_ratio_cumulative": gzip_ratio(texts),
                    "collapse_index_cumulative": float(judge_members["collapse_index"].mean()),
                }
            )

    frame = pd.DataFrame(rows)
    for condition, condition_frame in frame.groupby("condition"):
        ordered_counts = condition_frame.sort_values("cutoff_minutes")["n_posts_cumulative"]
        if not ordered_counts.is_monotonic_increasing:
            raise RuntimeError(f"non-cumulative post counts for {condition}")

    mean_trajectory = frame.groupby("cutoff_minutes", as_index=False)[
        ["distinct_5_cumulative", "gzip_ratio_cumulative", "collapse_index_cumulative"]
    ].mean()
    if not mean_trajectory["distinct_5_cumulative"].is_monotonic_decreasing:
        raise RuntimeError("mean cumulative Distinct-5 does not decrease at every checkpoint")
    if not mean_trajectory["gzip_ratio_cumulative"].is_monotonic_decreasing:
        raise RuntimeError("mean cumulative gzip does not decrease at every checkpoint")
    if not mean_trajectory["collapse_index_cumulative"].is_monotonic_increasing:
        raise RuntimeError("mean cumulative judge index does not increase at every checkpoint")

    args.data_output.mkdir(parents=True, exist_ok=True)
    csv_path = args.data_output / "long_horizon_cumulative.csv"
    frame.to_csv(csv_path, index=False, lineterminator="\n")

    metric_specs = [
        ("distinct_5_cumulative", "(a) Cumulative Distinct-5", "lower"),
        ("gzip_ratio_cumulative", "(b) Cumulative gzip ratio", "lower"),
        ("collapse_index_cumulative", "(c) Cumulative LLM collapse index", "higher"),
    ]
    summaries = []
    for metric, label, collapse_direction in metric_specs:
        at_60 = frame[frame["cutoff_minutes"] == 60].set_index("condition")[metric]
        at_300 = frame[frame["cutoff_minutes"] == 300].set_index("condition")[metric]
        ascending = collapse_direction == "lower"
        ranking_60 = at_60.sort_values(ascending=ascending).index.tolist()
        ranking_300 = at_300.sort_values(ascending=ascending).index.tolist()
        ranks_60 = at_60.rank(ascending=ascending, method="average")
        ranks_300 = at_300.rank(ascending=ascending, method="average")
        summaries.append(
            {
                "metric": metric,
                "metric_label": label[4:],
                "ranking_60": ranking_60,
                "ranking_300": ranking_300,
                "spearman_rho": float(ranks_60.corr(ranks_300, method="pearson")),
                "mean_change_60_to_300": float((at_300 - at_60).mean()),
                "per_condition_change_60_to_300": {
                    condition: float(at_300[condition] - at_60[condition])
                    for condition in CONDITIONS
                },
            }
        )

    summary = {
        "cutoffs_minutes": CUTOFFS,
        "run_duration_minutes": {
            condition: float(selected[condition]["duration_minutes"])
            for condition in CONDITIONS
        },
        "replicates_per_condition": 1,
        "confidence_intervals_available": False,
        "metrics": summaries,
    }
    summary_path = args.data_output / "long_horizon_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    setup_style()
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 10.8), sharex=True)
    cutoff_positions = {cutoff: position for position, cutoff in enumerate(CUTOFFS)}
    # Use the paper's metric-specific, truncated-axis presentation, but fit each
    # panel to the range observed in the five-hour extension. This avoids large
    # empty regions while retaining enough headroom for every marker.
    minimum_padding = {
        "distinct_5_cumulative": 0.003,
        "gzip_ratio_cumulative": 0.003,
        "collapse_index_cumulative": 0.030,
    }
    for ax, (metric, ylabel, _) in zip(axes, metric_specs):
        metric_values = frame[metric].dropna().astype(float)
        data_span = float(metric_values.max() - metric_values.min())
        padding = max(data_span * 0.08, minimum_padding[metric])
        ylim = (
            float(metric_values.min()) - padding,
            float(metric_values.max()) + padding,
        )
        for condition in CONDITIONS:
            line = frame[frame["condition"] == condition].sort_values("cutoff_minutes")
            ax.plot(
                line["cutoff_minutes"].map(cutoff_positions),
                line[metric],
                marker="o",
                markersize=4.2,
                linewidth=1.4,
                color=COLORS[condition],
                alpha=0.72,
                label=CONDITION_LABELS[condition],
            )
        ax.plot(
            mean_trajectory["cutoff_minutes"].map(cutoff_positions),
            mean_trajectory[metric],
            marker="D",
            markersize=4.8,
            linewidth=2.8,
            color="#222222",
            label="Mean across conditions",
            zorder=5,
        )
        ax.axvline(cutoff_positions[60], color="#555555", linestyle="--", linewidth=1.0)
        ax.set_ylabel(ylabel)
        ax.set_ylim(*ylim)
        ax.grid(axis="y", color="#dddddd", linewidth=0.8)
        if not ((metric_values > ylim[0]).all() and (metric_values < ylim[1]).all()):
            raise RuntimeError(f"{metric} contains points outside y-axis limits {ylim}")
    axes[0].text(
        cutoff_positions[60] + 0.10,
        0.97,
        "original evaluation horizon",
        fontsize=8.5,
        color="#555555",
        rotation=90,
        va="top",
        transform=axes[0].get_xaxis_transform(),
    )
    axes[-1].set_xlabel("Cumulative cutoff (minutes)")
    axes[-1].set_xticks(range(len(CUTOFFS)), labels=CUTOFFS)
    axes[-1].set_xlim(-0.35, len(CUTOFFS) - 0.65)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, frameon=False, bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("GPT-5 cumulative feed-level collapse, 15 to 300 minutes", y=0.995)
    fig.subplots_adjust(top=0.96, bottom=0.19, left=0.16, right=0.98, hspace=0.26)
    args.figure_output.mkdir(parents=True, exist_ok=True)
    png_path = args.figure_output / "ovs5_long_horizon_cumulative.png"
    pdf_path = args.figure_output / "ovs5_long_horizon_cumulative.pdf"
    fig.savefig(png_path, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    def ranking_text(values: list[str]) -> str:
        return " $>$ ".join(SHORT_LABELS[value] for value in values)

    table_rows = []
    for item in summaries:
        table_rows.append(
            "%s & %s & %s & %.2f & %+.3f \\\\" % (
                item["metric_label"],
                ranking_text(item["ranking_60"]),
                ranking_text(item["ranking_300"]),
                item["spearman_rho"],
                item["mean_change_60_to_300"],
            )
        )
    tex_path = args.figure_output / "ovs5_long_horizon_summary.tex"
    tex_path.write_text(
        """\\documentclass[border=10pt]{standalone}
\\usepackage[T1]{fontenc}
\\usepackage{times}
\\usepackage{booktabs}
\\begin{document}
\\begin{minipage}{10.6in}
\\centering
\\scriptsize
\\setlength{\\tabcolsep}{5pt}
\\begin{tabular}{lccrr}
\\toprule
Metric & Collapse ranking at 60 min & Collapse ranking at 300 min & Spearman $\\rho$ & Mean $\\Delta_{60\\rightarrow300}$ \\\\
\\midrule
%s
\\bottomrule
\\end{tabular}
\\vspace{5pt}
\\parbox{10.3in}{\\scriptsize Rankings run from greater to lower collapse. Lower Distinct-5 and gzip indicate greater collapse; higher judge index indicates greater collapse. The 300-minute value is the final available log for runs ending between 272 and 297 minutes. One run is available per condition, so confidence intervals are not estimated.}
\\end{minipage}
\\end{document}
""" % "\n".join(table_rows),
        encoding="utf-8",
    )
    if shutil.which("pdflatex") and shutil.which("pdftoppm"):
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={args.figure_output}", str(tex_path)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        table_pdf = tex_path.with_suffix(".pdf")
        table_png = tex_path.with_suffix(".png")
        subprocess.run(
            ["pdftoppm", "-png", "-singlefile", "-r", "180", str(table_pdf), str(table_png.with_suffix(""))],
            check=True,
        )
        for suffix in (".aux", ".log"):
            tex_path.with_suffix(suffix).unlink(missing_ok=True)
    else:
        print("pdflatex/pdftoppm unavailable; kept TeX table and skipped table rendering")

    print(json.dumps(summary, indent=2))
    print(f"wrote {csv_path}")
    print(f"wrote {summary_path}")
    print(f"wrote {png_path}")
    print(f"wrote {pdf_path}")
    print(f"wrote {tex_path}")
    if shutil.which("pdflatex") and shutil.which("pdftoppm"):
        print(f"wrote {table_png}")


if __name__ == "__main__":
    main()
