#!/usr/bin/env python3
"""
Build combined comparison plots across legacy model sets and OLMo reruns.

Inputs:
- analysis/temporal-diversity-results.json
- analysis/shannon-entropy-results.json
- /tmp/olmo-temporal-diversity-20260408.json (preferred) or analysis/olmo-temporal-diversity.json
- /tmp/olmo-shannon-entropy-3gram-20260408.json (preferred) or analysis/olmo-shannon-entropy-3gram.json

Outputs:
- analysis/plots-combined/combined_d3_trajectories_with_olmo.png
- analysis/plots-combined/combined_entropy_3gram_with_olmo.png
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path("/home/anangia/moltbook")
ANALYSIS = ROOT / "analysis"
OUT_DIR = ANALYSIS / "plots-combined"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    with open(path) as f:
        return json.load(f)


def normalize_set_name(name: str) -> str:
    mapping = {
        "GPT-5 Nano": "GPT-5",
    }
    return mapping.get(name, name)


def pick_file(preferred: str, fallback: str) -> Path:
    preferred_path = Path(preferred)
    return preferred_path if preferred_path.exists() else Path(fallback)


def merge_temporal_results():
    legacy = load_json(ANALYSIS / "temporal-diversity-results.json")
    olmo = load_json(
        pick_file(
            "/tmp/olmo-temporal-diversity-20260408.json",
            str(ANALYSIS / "olmo-temporal-diversity.json"),
        )
    )

    rows = []
    for row in legacy + olmo:
        row = dict(row)
        row["set"] = normalize_set_name(row["set"])
        rows.append(row)
    return rows


def merge_entropy_results():
    legacy = load_json(ANALYSIS / "shannon-entropy-results.json")
    olmo = load_json(
        pick_file(
            "/tmp/olmo-shannon-entropy-3gram-20260408.json",
            str(ANALYSIS / "olmo-shannon-entropy-3gram.json"),
        )
    )

    rows = []
    for row in legacy + olmo:
        row = dict(row)
        row["set"] = normalize_set_name(row["set"])
        rows.append(row)
    return rows


def plot_metric(rows, value_key: str, ylabel: str, title: str, output_path: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    conditions = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
    set_order = [
        "BASE (Qwen 35B)",
        "GPT-5",
        "Gemini Flash Lite",
        "Kimi K2.5",
        "GLM-5",
        "OLMo Base",
        "OLMo Instruct",
    ]
    colors = {
        "BASE (Qwen 35B)": "#1f77b4",
        "GPT-5": "#d62728",
        "Gemini Flash Lite": "#2ca02c",
        "Kimi K2.5": "#ff7f0e",
        "GLM-5": "#9467bd",
        "OLMo Base": "#8c564b",
        "OLMo Instruct": "#e377c2",
    }
    markers = {
        "BASE (Qwen 35B)": "o",
        "GPT-5": "s",
        "Gemini Flash Lite": "^",
        "Kimi K2.5": "D",
        "GLM-5": "P",
        "OLMo Base": "X",
        "OLMo Instruct": "*",
    }

    fig, axes = plt.subplots(2, 3, figsize=(18, 10), sharex=True)
    axes = axes.flatten()

    for ax, condition in zip(axes, conditions):
        cond_rows = [r for r in rows if r["condition"] == condition]
        by_set = {r["set"]: r for r in cond_rows}

        for set_name in set_order:
            row = by_set.get(set_name)
            if not row:
                continue
            values = row[value_key]
            x = list(range(1, len(values) + 1))
            label = f"{set_name} (n={row.get('n_posts', '?')})"
            ax.plot(
                x,
                values,
                label=label,
                color=colors[set_name],
                marker=markers[set_name],
                linewidth=2,
                markersize=5,
                alpha=0.95,
            )

        ax.set_title(condition)
        ax.set_xticks([1, 2, 3, 4])
        ax.set_xlabel("Quartile")
        ax.set_ylabel(ylabel)
        ax.grid(True, alpha=0.25)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=4, frameon=False, bbox_to_anchor=(0.5, 1.02))
    fig.suptitle(title, y=1.08, fontsize=15)
    fig.tight_layout()
    fig.savefig(output_path, dpi=220, bbox_inches="tight")
    print(f"saved {output_path}")


def main():
    temporal_rows = merge_temporal_results()
    entropy_rows = merge_entropy_results()
    d3_series_key = "_".join(["d3", "quartiles"])
    entropy_series_key = "_".join(["entropy", "values"])

    plot_metric(
        temporal_rows,
        value_key=d3_series_key,
        ylabel="Distinct-3",
        title="Temporal Distinct-3 Trajectories Across Legacy Models and OLMo",
        output_path=OUT_DIR / "combined_d3_trajectories_with_olmo.png",
    )

    plot_metric(
        entropy_rows,
        value_key=entropy_series_key,
        ylabel="3-gram Shannon Entropy (bits)",
        title="3-gram Shannon Entropy Trajectories Across Legacy Models and OLMo",
        output_path=OUT_DIR / "combined_entropy_3gram_with_olmo.png",
    )


if __name__ == "__main__":
    main()
