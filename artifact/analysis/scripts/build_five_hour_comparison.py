#!/usr/bin/env python3
"""Build the reviewer-facing one-hour and longer-horizon comparison table."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import random
import shutil
import subprocess
from pathlib import Path
from statistics import mean

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--analysis-root",
        type=Path,
        required=True,
        help="Directory containing data_manifest.csv and ayush_reanalysis/",
    )
    parser.add_argument("--data-output", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--figure-output",
        type=Path,
        default=ROOT.parent / "rebuttal/assets",
    )
    args = parser.parse_args()

    manifest_path = args.analysis_root / "data_manifest.csv"
    deterministic_path = args.analysis_root / "ayush_reanalysis/deterministic_timebin_metrics.csv"
    judge_path = args.analysis_root / "ayush_reanalysis/llm_judge_run_timebin_metrics.csv"
    manifest = {row["run_uid"]: row for row in read_csv(manifest_path)}
    deterministic = read_csv(deterministic_path)
    judge = {
        (row["run_uid"], row["scheme"], int(row["bin_idx"])): row
        for row in read_csv(judge_path)
    }

    selected_bins: dict[tuple[str, str], dict[int, dict[str, str]]] = {}
    for row in deterministic:
        if row["scheme"] != "normalized_quartile":
            continue
        if row["model_display"] not in {"GPT-5", "Gemini Flash Lite"} or int(row["n_agents"]) != 10:
            continue
        if row["condition"] not in CONDITIONS:
            continue

        meta = manifest[row["run_uid"]]
        duration = float(meta["duration_minutes"])
        cohort: str | None = None
        if row["internal_family_label"] == "single_model_final" and duration < 75:
            cohort = f"One-hour {row['model_display']} run"
        elif (
            row["model_display"] == "GPT-5"
            and row["internal_family_label"] == "obsession_prompting"
            and duration >= 240
        ):
            cohort = "Five-hour GPT-5 run"
        if cohort is None:
            continue
        selected_bins.setdefault((cohort, row["run_uid"]), {})[int(row["bin_idx"])] = row

    baselines: list[dict[str, object]] = []
    long_runs: list[dict[str, object]] = []
    for (cohort, run_uid), bins in selected_bins.items():
        assert 0 in bins and 3 in bins, f"missing first/final quartile for {run_uid}"
        first = bins[0]
        final = bins[3]
        meta = manifest[run_uid]
        duration = float(meta["duration_minutes"])
        judge_first = judge[(run_uid, "normalized_quartile", 0)]
        judge_final = judge[(run_uid, "normalized_quartile", 3)]
        record: dict[str, object] = {
            "run_uid": run_uid,
            "run_id": first["run_id"],
            "model": first["model_display"],
            "condition": first["condition"],
            "duration_minutes": duration,
            "equal_post_distinct_5_first": float(first["distinct_5_sub_mean"]),
            "equal_post_distinct_5_final": float(final["distinct_5_sub_mean"]),
            "delta_equal_post_distinct_5": (
                float(final["distinct_5_sub_mean"])
                - float(first["distinct_5_sub_mean"])
            ),
            "collapse_index_first": float(judge_first["collapse_index"]),
            "collapse_index_final": float(judge_final["collapse_index"]),
            "delta_collapse_index": (
                float(judge_final["collapse_index"])
                - float(judge_first["collapse_index"])
            ),
            "equal_post_target": int(first["subsample_target_posts"]),
            "cohort": cohort,
        }
        if cohort.startswith("One-hour"):
            baselines.append(record)
        else:
            long_runs.append(record)

    gpt_baselines = [row for row in baselines if row["model"] == "GPT-5"]
    gemini_baselines = [row for row in baselines if row["model"] == "Gemini Flash Lite"]
    assert len(gpt_baselines) == 6, f"expected 6 GPT-5 baselines, found {len(gpt_baselines)}"
    assert len(gemini_baselines) == 6, f"expected 6 Gemini baselines, found {len(gemini_baselines)}"
    long_runs = [
        max(
            (row for row in long_runs if row["condition"] == condition),
            key=lambda row: str(row["run_id"]),
        )
        for condition in CONDITIONS
    ]
    assert len(long_runs) == 6, f"expected 6 long runs, found {len(long_runs)}"
    assert {r["condition"] for r in long_runs} == set(CONDITIONS)
    assert {r["condition"] for r in gpt_baselines} == set(CONDITIONS)
    assert {r["condition"] for r in gemini_baselines} == set(CONDITIONS)

    rows = baselines + long_runs
    one_hour_uids = {str(row["run_uid"]) for row in baselines}
    fixed_bins: dict[str, dict[int, dict[str, str]]] = {}
    for row in deterministic:
        if row["scheme"] == "fixed_15m" and row["run_uid"] in one_hour_uids:
            fixed_bins.setdefault(row["run_uid"], {})[int(row["bin_idx"])] = row

    def paper_style_series(record: dict[str, object]) -> tuple[list[float], list[float]]:
        run_uid = str(record["run_uid"])
        if str(record["cohort"]).startswith("One-hour"):
            scheme = "fixed_15m"
            bins = fixed_bins[run_uid]
        else:
            scheme = "normalized_quartile"
            bins = selected_bins[(str(record["cohort"]), run_uid)]
        assert set(bins) >= {0, 1, 2, 3}, f"missing trajectory bins for {run_uid}"
        distinct_5 = [float(bins[index]["distinct_5_cumulative"]) for index in range(4)]
        judge_values = []
        weighted_sum = 0.0
        total_weight = 0.0
        for index in range(4):
            judge_row = judge[(run_uid, scheme, index)]
            weight = float(judge_row["n_judged"])
            weighted_sum += float(judge_row["collapse_index"]) * weight
            total_weight += weight
            judge_values.append(weighted_sum / total_weight)
        return distinct_5, judge_values

    for record in rows:
        cumulative_d5, cumulative_judge = paper_style_series(record)
        record["cumulative_distinct_5_first"] = cumulative_d5[0]
        record["cumulative_distinct_5_final"] = cumulative_d5[-1]
        record["delta_cumulative_distinct_5"] = cumulative_d5[-1] - cumulative_d5[0]
        record["cumulative_collapse_index_first"] = cumulative_judge[0]
        record["cumulative_collapse_index_final"] = cumulative_judge[-1]
        record["delta_cumulative_collapse_index"] = cumulative_judge[-1] - cumulative_judge[0]

    gpt_records = [record for record in rows if record["model"] == "GPT-5"]
    gpt_uids = {str(record["run_uid"]) for record in gpt_records}
    posts_by_uid: dict[str, list[dict[str, object]]] = {run_uid: [] for run_uid in gpt_uids}
    post_index_path = args.analysis_root / "ayush_reanalysis/post_index.jsonl"
    with post_index_path.open(encoding="utf-8") as handle:
        for line in handle:
            post = json.loads(line)
            run_uid = post.get("run_uid")
            if run_uid not in gpt_uids or post.get("is_seed"):
                continue
            normalized_time = post.get("normalized_time")
            text_value = post.get("text")
            if isinstance(normalized_time, (int, float)) and isinstance(text_value, str) and text_value:
                posts_by_uid[str(run_uid)].append(post)

    one_hour_gpt_uids = {
        str(record["run_uid"])
        for record in gpt_records
        if str(record["cohort"]).startswith("One-hour")
    }
    paper_posts = pd.read_csv(
        args.analysis_root / "ayush_reanalysis/post_index.csv",
        usecols=["run_uid", "is_seed", "minutes_elapsed", "text"],
        low_memory=False,
    )
    paper_posts = paper_posts[
        paper_posts["run_uid"].isin(one_hour_gpt_uids)
        & (~paper_posts["is_seed"].astype(bool))
        & (paper_posts["minutes_elapsed"] >= 0)
        & (paper_posts["minutes_elapsed"] <= 60)
    ].copy()
    paper_posts["text"] = paper_posts["text"].fillna("")

    def equal_byte_gzip_series(record: dict[str, object], repetitions: int = 100) -> list[float]:
        run_uid = str(record["run_uid"])
        windows: list[list[str]] = []
        bounds = [(0.0, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.0000001)]
        for low, high in bounds:
            windows.append(
                [
                    str(post["text"])
                    for post in posts_by_uid[run_uid]
                    if low <= float(post["normalized_time"]) < high
                ]
            )
        if any(not window for window in windows):
            raise RuntimeError(f"empty gzip window for {run_uid}")
        byte_budget = min(len("\n".join(window).encode("utf-8")) for window in windows)
        means = []
        for bin_index, window in enumerate(windows):
            draws = []
            for repetition in range(repetitions):
                seed_value = f"{run_uid}|{bin_index}|{repetition}|gzip".encode()
                seed = int.from_bytes(hashlib.sha256(seed_value).digest()[:8], "big")
                order = list(range(len(window)))
                random.Random(seed).shuffle(order)
                raw = b"\n".join(window[index].encode("utf-8") for index in order)[:byte_budget]
                if len(raw) != byte_budget:
                    raise RuntimeError(f"could not fill gzip byte budget for {run_uid}")
                draws.append(len(gzip.compress(raw, compresslevel=9)) / len(raw))
            means.append(mean(draws))
        return means

    for record in rows:
        for index in range(4):
            record[f"equal_byte_gzip_q{index + 1}"] = ""
            record[f"cumulative_gzip_q{index + 1}"] = ""
        record["delta_equal_byte_gzip"] = ""
        record["delta_cumulative_gzip"] = ""
    for record in gpt_records:
        gzip_values = equal_byte_gzip_series(record)
        for index, value in enumerate(gzip_values):
            record[f"equal_byte_gzip_q{index + 1}"] = value
        record["delta_equal_byte_gzip"] = gzip_values[-1] - gzip_values[0]

        posts = sorted(
            posts_by_uid[str(record["run_uid"])],
            key=lambda post: float(post.get("minutes_elapsed", 0.0)),
        )
        if str(record["cohort"]).startswith("One-hour"):
            paper_run_posts = paper_posts[
                paper_posts["run_uid"] == str(record["run_uid"])
            ].sort_values("minutes_elapsed")
            cumulative_windows = [
                paper_run_posts[
                    paper_run_posts["minutes_elapsed"] <= cutoff
                ]["text"].astype(str).tolist()
                for cutoff in (15.0, 30.0, 45.0, 60.0)
            ]
        else:
            cumulative_windows = [
                [
                    str(post["text"])
                    for post in posts
                    if 0.0 <= float(post["normalized_time"]) <= cutoff
                ]
                for cutoff in (0.25, 0.50, 0.75, 1.0)
            ]
        cumulative_gzip = []
        for window in cumulative_windows:
            raw = "\n".join(window).encode("utf-8")
            if not raw:
                raise RuntimeError(f"empty cumulative gzip window for {record['run_uid']}")
            cumulative_gzip.append(len(gzip.compress(raw)) / len(raw))
        for index, value in enumerate(cumulative_gzip):
            record[f"cumulative_gzip_q{index + 1}"] = value
        record["delta_cumulative_gzip"] = cumulative_gzip[-1] - cumulative_gzip[0]

    args.data_output.mkdir(parents=True, exist_ok=True)
    csv_path = args.data_output / "five_hour_comparison.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    def summarize(rows_in_cohort: list[dict[str, object]]) -> dict[str, object]:
        equal_post_d5 = [float(row["delta_equal_post_distinct_5"]) for row in rows_in_cohort]
        quarterly_judge = [float(row["delta_collapse_index"]) for row in rows_in_cohort]
        cumulative_d5 = [float(row["delta_cumulative_distinct_5"]) for row in rows_in_cohort]
        cumulative_judge = [float(row["delta_cumulative_collapse_index"]) for row in rows_in_cohort]
        equal_byte_gzip = [
            float(row["delta_equal_byte_gzip"])
            for row in rows_in_cohort
            if row["delta_equal_byte_gzip"] != ""
        ]
        cumulative_gzip = [
            float(row["delta_cumulative_gzip"])
            for row in rows_in_cohort
            if row["delta_cumulative_gzip"] != ""
        ]
        return {
            "n_runs": len(rows_in_cohort),
            "conditions": sorted({str(row["condition"]) for row in rows_in_cohort}),
            "duration_minutes_range": [
                min(float(row["duration_minutes"]) for row in rows_in_cohort),
                max(float(row["duration_minutes"]) for row in rows_in_cohort),
            ],
            "equal_post_distinct_5_decreases": sum(value < 0 for value in equal_post_d5),
            "quarterly_collapse_index_increases": sum(value > 0 for value in quarterly_judge),
            "cumulative_distinct_5_decreases": sum(value < 0 for value in cumulative_d5),
            "cumulative_collapse_index_increases": sum(value > 0 for value in cumulative_judge),
            "mean_delta_equal_post_distinct_5": mean(equal_post_d5),
            "mean_delta_quarterly_collapse_index": mean(quarterly_judge),
            "mean_delta_cumulative_distinct_5": mean(cumulative_d5),
            "mean_delta_cumulative_collapse_index": mean(cumulative_judge),
            "equal_byte_gzip_decreases": (
                sum(value < 0 for value in equal_byte_gzip) if equal_byte_gzip else None
            ),
            "mean_delta_equal_byte_gzip": mean(equal_byte_gzip) if equal_byte_gzip else None,
            "cumulative_gzip_decreases": (
                sum(value < 0 for value in cumulative_gzip) if cumulative_gzip else None
            ),
            "mean_delta_cumulative_gzip": mean(cumulative_gzip) if cumulative_gzip else None,
        }

    summary = {
        "comparison": "first quartile versus final quartile",
        "trajectory_metric": "paper-style cumulative values at four cutoffs within each run",
        "gzip_control": "same UTF-8 byte count in all four windows; mean of 100 deterministic post-order permutations",
        "one_hour_gpt5": summarize(gpt_baselines),
        "one_hour_gemini_flash_lite": summarize(gemini_baselines),
        "extended_gpt5": summarize(long_runs),
        "gemini_five_hour": {
            "scheduled_attempts": 2,
            "conditions_attempted": ["mag25"],
            "scheduled_minutes": 300,
            "nonseed_post_counts": [3, 0],
            "final_quarter_estimate_available": False,
        },
    }
    json_path = args.data_output / "five_hour_comparison_summary.json"
    json_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    def transition(first: object, final: object) -> str:
        return f"{float(first):.3f} $\\rightarrow$ {float(final):.3f}"

    condition_labels = {
        "mag0": "Empty",
        "mag1": "1 conspiracy",
        "mag5": "5 conspiracies",
        "mag25": "25 conspiracies",
        "dom-agi": "AGI",
        "dom-tech": "Tech",
    }
    gpt_by_condition = {str(row["condition"]): row for row in gpt_baselines}
    gemini_by_condition = {str(row["condition"]): row for row in gemini_baselines}
    long_by_condition = {str(row["condition"]): row for row in long_runs}
    d5_lines = []
    judge_lines = []
    for condition in CONDITIONS:
        gpt = gpt_by_condition[condition]
        gemini = gemini_by_condition[condition]
        extended = long_by_condition[condition]
        gemini_five_hour = "n/e" if condition == "mag25" else "--"
        d5_lines.append(
            "%s & %s & %s & %s & %s \\\\" % (
                condition_labels[condition],
                transition(gpt["equal_post_distinct_5_first"], gpt["equal_post_distinct_5_final"]),
                transition(gemini["equal_post_distinct_5_first"], gemini["equal_post_distinct_5_final"]),
                transition(extended["equal_post_distinct_5_first"], extended["equal_post_distinct_5_final"]),
                gemini_five_hour,
            )
        )
        judge_lines.append(
            "%s & %s & %s & %s & %s \\\\" % (
                condition_labels[condition],
                transition(gpt["collapse_index_first"], gpt["collapse_index_final"]),
                transition(gemini["collapse_index_first"], gemini["collapse_index_final"]),
                transition(extended["collapse_index_first"], extended["collapse_index_final"]),
                gemini_five_hour,
            )
        )

    args.figure_output.mkdir(parents=True, exist_ok=True)
    tex_path = args.figure_output / "ovs5_five_hour_comparison.tex"
    png_path = args.figure_output / "ovs5_five_hour_comparison.png"
    pdf_path = args.figure_output / "ovs5_five_hour_comparison.pdf"
    tex_path.write_text(
        """\\documentclass[border=10pt]{standalone}
\\usepackage[T1]{fontenc}
\\usepackage{times}
\\usepackage{booktabs}
\\begin{document}
\\begin{minipage}{7.2in}
\\centering
\\scriptsize
\\setlength{\\tabcolsep}{6pt}
\\renewcommand{\\arraystretch}{1.12}
\\textbf{Length-controlled Distinct-5} (lower means less lexical diversity)\\par
\\vspace{2pt}
\\begin{tabular}{lcccc}
\\toprule
Condition & GPT-5 1 h & Gemini Flash Lite 1 h & GPT-5 5 h & Gemini Flash Lite 5 h \\\\
\\midrule
%s
\\bottomrule
\\end{tabular}

\\vspace{9pt}
\\textbf{Judge collapse index} (higher means more collapse)\\par
\\vspace{2pt}
\\begin{tabular}{lcccc}
\\toprule
Condition & GPT-5 1 h & Gemini Flash Lite 1 h & GPT-5 5 h & Gemini Flash Lite 5 h \\\\
\\midrule
%s
\\bottomrule
\\end{tabular}

\\vspace{6pt}
\\parbox{7.0in}{\\scriptsize\\textbf{Table C3:} Each cell shows first quarter $\\rightarrow$ final quarter within the same run. Distinct-5 uses the same post count in both windows. One- and five-hour change magnitudes are not directly comparable. ``--'' means no run. ``n/e'' means not estimable; the two Gemini Flash Lite five-hour attempts contain three and zero non-seed posts.}
\\end{minipage}
\\end{document}
""" % ("\n".join(d5_lines), "\n".join(judge_lines)),
        encoding="utf-8",
    )
    if shutil.which("pdflatex") and shutil.which("pdftoppm"):
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={args.figure_output}", str(tex_path)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            ["pdftoppm", "-png", "-singlefile", "-r", "180", str(pdf_path), str(png_path.with_suffix(""))],
            check=True,
        )
        for suffix in (".aux", ".log"):
            tex_path.with_suffix(suffix).unlink(missing_ok=True)
    else:
        print("pdflatex/pdftoppm unavailable; kept TeX table and skipped table rendering")

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 15,
            "axes.labelsize": 12,
            "xtick.labelsize": 11,
            "ytick.labelsize": 11,
            "legend.fontsize": 10,
            "figure.titlesize": 16,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": False,
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    condition_colors = {
        "mag0": "#1b6b42",
        "mag1": "#3b6ea8",
        "mag5": "#f28e2b",
        "mag25": "#d94f4f",
        "dom-agi": "#7b4ea3",
        "dom-tech": "#4e9f3d",
    }
    paper_condition_labels = {
        "mag0": "Empty feed",
        "mag1": "1 conspiracy seed",
        "mag5": "5 conspiracy seeds",
        "mag25": "25 conspiracy seeds",
        "dom-agi": "25 AGI seeds",
        "dom-tech": "25 tech seeds",
    }

    def plot_trajectories(
        metric_name: str,
        ylabel: str,
        stem: str,
    ) -> None:
        fig, axes = plt.subplots(1, 2, figsize=(13.8, 5.2), sharex=True, sharey=False)
        fig.subplots_adjust(left=0.08, right=0.82, top=0.88, bottom=0.18, wspace=0.16)
        x = [1, 2, 3, 4]
        labels = ["Q1", "Q2", "Q3", "Q4"]
        panels = [
            ("GPT-5, 1 hour", gpt_by_condition),
            ("GPT-5, 5 hours", long_by_condition),
        ]
        for ax, (panel_title, records) in zip(axes, panels):
            for condition in CONDITIONS:
                record = records[condition]
                bins = selected_bins[(str(record["cohort"]), str(record["run_uid"]))]
                if metric_name == "distinct_5_sub_mean":
                    values = [float(bins[index][metric_name]) for index in range(4)]
                else:
                    values = [
                        float(judge[(str(record["run_uid"]), "normalized_quartile", index)][metric_name])
                        for index in range(4)
                    ]
                ax.plot(
                    x,
                    values,
                    marker="o",
                    markersize=4.7,
                    linewidth=1.9,
                    color=condition_colors[condition],
                    label=paper_condition_labels[condition],
                )
            ax.set_title(panel_title, pad=8)
            ax.set_xticks(x, labels)
            ax.set_xlabel("Run quartile")
            ax.grid(axis="y", color="#dddddd", linewidth=0.8)
        axes[0].set_ylabel(ylabel)
        handles, legend_labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles,
            legend_labels,
            loc="center left",
            bbox_to_anchor=(0.84, 0.50),
            frameon=False,
            ncol=1,
        )
        trajectory_png = args.figure_output / f"{stem}.png"
        trajectory_pdf = args.figure_output / f"{stem}.pdf"
        fig.savefig(trajectory_png, bbox_inches="tight", facecolor="white")
        fig.savefig(trajectory_pdf, bbox_inches="tight", facecolor="white")
        plt.close(fig)

    plot_trajectories(
        "distinct_5_sub_mean",
        "Length-controlled Distinct-5",
        "ovs5_five_hour_distinct5_trajectories",
    )
    plot_trajectories(
        "collapse_index",
        "LLM collapse index",
        "ovs5_five_hour_judge_trajectories",
    )

    def combined_values(record: dict[str, object], metric_name: str) -> list[float]:
        if metric_name == "cumulative_gzip":
            return [float(record[f"cumulative_gzip_q{index}"]) for index in range(1, 5)]
        cumulative_d5, cumulative_judge = paper_style_series(record)
        return cumulative_d5 if metric_name == "cumulative_distinct_5" else cumulative_judge

    metric_rows = [
        ("cumulative_distinct_5", "(a) Cumulative Distinct-5"),
        ("cumulative_gzip", "(b) Cumulative gzip ratio"),
        ("cumulative_collapse_index", "(c) Cumulative LLM collapse index"),
    ]
    horizon_columns = [
        ("GPT-5, 1 hour", gpt_by_condition),
        ("GPT-5, 5 hours", long_by_condition),
    ]
    fig, axes = plt.subplots(3, 2, figsize=(13.8, 11.5), sharex=True, sharey=False)
    fig.subplots_adjust(left=0.10, right=0.82, top=0.91, bottom=0.10, wspace=0.16, hspace=0.28)
    x = [1, 2, 3, 4]
    for row_index, (metric_name, ylabel) in enumerate(metric_rows):
        for column_index, (panel_title, records) in enumerate(horizon_columns):
            ax = axes[row_index, column_index]
            for condition in CONDITIONS:
                record = records[condition]
                ax.plot(
                    x,
                    combined_values(record, metric_name),
                    marker="o",
                    markersize=4.7,
                    linewidth=1.9,
                    color=condition_colors[condition],
                    label=paper_condition_labels[condition],
                )
            if row_index == 0:
                ax.set_title(panel_title, pad=8)
            ax.set_ylabel(ylabel if column_index == 0 else "")
            ax.set_xticks(x, ["Q1", "Q2", "Q3", "Q4"])
            if row_index == 2:
                ax.set_xlabel("Run quartile")
            ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    handles, legend_labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="center left",
        bbox_to_anchor=(0.84, 0.50),
        frameon=False,
        ncol=1,
    )
    fig.suptitle("GPT-5 collapse at one and five hours", y=0.975)
    combined_png = args.figure_output / "ovs5_five_hour_combined_trajectories.png"
    combined_pdf = args.figure_output / "ovs5_five_hour_combined_trajectories.pdf"
    fig.savefig(combined_png, bbox_inches="tight", facecolor="white")
    fig.savefig(combined_pdf, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print(json.dumps(summary, indent=2))
    print(f"wrote {csv_path}")
    print(f"wrote {json_path}")
    print(f"wrote {tex_path}")
    print(f"wrote {png_path}")
    print(f"wrote {pdf_path}")
    print("wrote condition-level trajectory figures")
    print(f"wrote {combined_png}")
    print(f"wrote {combined_pdf}")


if __name__ == "__main__":
    main()
