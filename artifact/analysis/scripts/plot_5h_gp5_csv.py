#!/usr/bin/env python3
"""Plot the supplied GPT-5 cumulative checkpoint CSV in the paper's style."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
METRICS = ["Distinct-5", "Gzip ratio", "LLM collapse index"]
CONDITIONS = [
    "Empty feed",
    "1 conspiracy",
    "5 conspiracy",
    "25 conspiracy",
    "25 AGI",
    "25 tech",
]
CUTOFFS = [15, 30, 45, 60, 90, 120, 180, 240, 300]
COLORS = {
    "Empty feed": "#1b6b42",
    "1 conspiracy": "#3b6ea8",
    "5 conspiracy": "#f28e2b",
    "25 conspiracy": "#d94f4f",
    "25 AGI": "#7b4ea3",
    "25 tech": "#4e9f3d",
}
Y_LABELS = {
    "Distinct-5": "(a) Cumulative Distinct-5",
    "Gzip ratio": "(b) Cumulative gzip ratio",
    "LLM collapse index": "(c) Cumulative LLM collapse index",
}
FIRST_HOUR_STATUS = "Approximate digitization from supplied figure"
POST_HOUR_STATUS = "Provided cumulative run value"


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
            "savefig.dpi": 300,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )


def validate(frame: pd.DataFrame) -> None:
    expected_columns = {"Metric", "Condition", "Minute", "Value", "Status"}
    if set(frame.columns) != expected_columns:
        raise ValueError(f"expected columns {sorted(expected_columns)}, found {frame.columns.tolist()}")
    expected = pd.MultiIndex.from_product(
        [METRICS, CONDITIONS, CUTOFFS], names=["Metric", "Condition", "Minute"]
    )
    actual = pd.MultiIndex.from_frame(frame[["Metric", "Condition", "Minute"]])
    missing = expected.difference(actual)
    extra = actual.difference(expected)
    if len(missing) or len(extra) or actual.has_duplicates:
        raise ValueError(
            f"CSV grid mismatch: missing={missing.tolist()}, extra={extra.tolist()}, "
            f"duplicates={actual[actual.duplicated()].tolist()}"
        )
    expected_status = frame["Minute"].map(
        lambda minute: FIRST_HOUR_STATUS if minute <= 60 else POST_HOUR_STATUS
    )
    if not frame["Status"].equals(expected_status):
        raise ValueError("status labels do not match the first-hour and post-hour split")
    if frame["Value"].isna().any():
        raise ValueError("Value contains missing entries")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "results/5h_gp5_run.csv",
    )
    parser.add_argument(
        "--output-prefix",
        type=Path,
        default=ROOT.parent / "rebuttal/assets/ovs5_five_hour_from_csv",
    )
    args = parser.parse_args()

    frame = pd.read_csv(args.input)
    validate(frame)
    setup_style()

    positions = {cutoff: index for index, cutoff in enumerate(CUTOFFS)}
    fig, axes = plt.subplots(3, 1, figsize=(7.2, 10.6), sharex=True)

    for ax, metric in zip(axes, METRICS):
        metric_frame = frame[frame["Metric"] == metric]
        values = metric_frame["Value"].astype(float)
        span = float(values.max() - values.min())
        padding = max(span * 0.06, 0.008 if metric == "LLM collapse index" else 0.004)
        limits = (float(values.min()) - padding, float(values.max()) + padding)

        for condition in CONDITIONS:
            series = metric_frame[metric_frame["Condition"] == condition].sort_values("Minute")
            ax.plot(
                series["Minute"].map(positions),
                series["Value"],
                color=COLORS[condition],
                marker="o",
                markersize=4.6,
                linewidth=1.9,
                label=condition,
            )

        ax.axvline(positions[60], color="#aaaaaa", linewidth=0.9)
        ax.set_ylabel(Y_LABELS[metric])
        ax.set_ylim(*limits)
        ax.grid(axis="y", color="#dddddd", linewidth=0.8)
        if not ((values > limits[0]).all() and (values < limits[1]).all()):
            raise RuntimeError(f"{metric} contains a point outside its y-axis limits")

    axes[0].text(
        positions[60] + 0.10,
        0.97,
        "original evaluation horizon",
        transform=axes[0].get_xaxis_transform(),
        fontsize=8.5,
        color="#555555",
        rotation=90,
        va="top",
    )
    axes[-1].set_xticks(range(len(CUTOFFS)), labels=CUTOFFS)
    axes[-1].set_xlim(-0.35, len(CUTOFFS) - 0.65)
    axes[-1].set_xlabel("Cumulative cutoff (minutes)")

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=3,
        frameon=False,
        bbox_to_anchor=(0.5, 0.025),
    )
    fig.suptitle("GPT-5 cumulative metrics, 15 to 300 minutes", y=0.995)
    fig.subplots_adjust(top=0.96, bottom=0.13, left=0.17, right=0.98, hspace=0.27)

    args.output_prefix.parent.mkdir(parents=True, exist_ok=True)
    png_path = args.output_prefix.with_suffix(".png")
    pdf_path = args.output_prefix.with_suffix(".pdf")
    fig.savefig(png_path, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf_path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"wrote {png_path}")
    print(f"wrote {pdf_path}")


if __name__ == "__main__":
    main()
