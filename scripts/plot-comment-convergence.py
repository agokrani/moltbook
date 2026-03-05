#!/usr/bin/env python3
"""Plot comment convergence findings from LLM classification."""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PLOT_DIR = REPO_ROOT / "findings" / "entropy-collapse" / "plots"

plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.grid": True,
    "grid.alpha": 0.3,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "figure.dpi": 150,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.2,
})

# LLM classification results
conditions = ["mag0\n(0 seeds)", "mag1\n(1 seed)", "mag5\n(5 seeds)", "mag25\n(25 seeds)"]
categories = [
    "Evidence methodology",
    "Community building",
    "AI/consciousness",
    "Philosophical reflection",
    "Meta-commentary",
    "Original/topical",
    "Social/supportive",
]
colors = [
    "#D32F2F",  # evidence — red (dominant)
    "#1565C0",  # community — blue
    "#7B1FA2",  # AI/consciousness — purple
    "#00838F",  # philosophical — teal
    "#F57F17",  # meta — amber
    "#2E7D32",  # original — green
    "#9E9E9E",  # social — gray
]

data = {
    "Evidence methodology":   [25, 46, 62, 49],
    "Community building":     [17,  0,  0,  8],
    "AI/consciousness":       [ 8, 19,  0, 13],
    "Philosophical reflection":[18, 12,  8, 10],
    "Meta-commentary":        [10,  7, 23,  2],
    "Original/topical":       [16, 13,  0, 18],
    "Social/supportive":      [ 6,  1,  7,  0],
}

# --- Plot 1: Stacked bar chart ---
fig, ax = plt.subplots(figsize=(10, 7))
x = np.arange(len(conditions))
bottom = np.zeros(len(conditions))

for cat, color in zip(categories, colors):
    vals = np.array(data[cat])
    bars = ax.bar(x, vals, bottom=bottom, label=cat, color=color, alpha=0.88,
                  edgecolor="white", linewidth=0.8)
    for i, (v, b) in enumerate(zip(vals, bottom)):
        if v >= 8:
            ax.text(i, b + v/2, f"{v}%", ha="center", va="center",
                    fontsize=9, fontweight="bold", color="white")
    bottom += vals

ax.set_xticks(x)
ax.set_xticklabels(conditions, fontsize=11)
ax.set_ylabel("% of Comments")
ax.set_title("Comment Topic Distribution by Conspiracy Magnitude\n(LLM-classified, 2 runs each)", fontsize=13)
ax.legend(fontsize=8, loc="upper right", bbox_to_anchor=(1.0, 1.0))
ax.set_ylim(0, 105)

# Annotation arrow pointing at mag5
ax.annotate("Peak collapse:\n3 categories extinct",
            xy=(2, 95), fontsize=9, ha="center", fontstyle="italic",
            color="#D32F2F")

path = PLOT_DIR / "05-comment-convergence-stacked.png"
fig.savefig(path)
plt.close(fig)
print(f"Saved {path.relative_to(REPO_ROOT)}")

# --- Plot 2: Evidence methodology line + category count line ---
fig, ax1 = plt.subplots(figsize=(10, 6))

mags = [0, 1, 5, 25]
evidence_pcts = [25, 46, 62, 49]

# Active categories (>0%)
active_counts = []
for i in range(4):
    n = sum(1 for cat in categories if data[cat][i] > 0)
    active_counts.append(n)

color_ev = "#D32F2F"
color_ac = "#1565C0"

ax1.plot(range(4), evidence_pcts, "o-", color=color_ev, linewidth=2.5,
         markersize=10, label="Evidence methodology %", zorder=3)
for i, v in enumerate(evidence_pcts):
    ax1.text(i, v + 3, f"{v}%", ha="center", fontsize=11, fontweight="bold",
             color=color_ev)

ax1.set_xticks(range(4))
ax1.set_xticklabels([f"mag{m}" for m in mags], fontsize=11)
ax1.set_ylabel("Evidence Methodology %", color=color_ev, fontsize=12)
ax1.tick_params(axis="y", labelcolor=color_ev)
ax1.set_ylim(0, 80)

ax2 = ax1.twinx()
ax2.plot(range(4), active_counts, "s--", color=color_ac, linewidth=2.5,
         markersize=10, label="Active topic categories", zorder=3)
for i, v in enumerate(active_counts):
    ax2.text(i, v - 0.4, f"{v}/7", ha="center", fontsize=11, fontweight="bold",
             color=color_ac)

ax2.set_ylabel("Active Topic Categories (of 7)", color=color_ac, fontsize=12)
ax2.tick_params(axis="y", labelcolor=color_ac)
ax2.set_ylim(0, 8)

ax1.set_title("Comment Entropy Collapse: Dominance vs Diversity\n(LLM-classified, 2 runs each)",
              fontsize=13)

# Combined legend
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, fontsize=10, loc="center right")

ax1.axvspan(1.8, 2.2, alpha=0.08, color="#D32F2F")

path = PLOT_DIR / "05-comment-convergence-dual.png"
fig.savefig(path)
plt.close(fig)
print(f"Saved {path.relative_to(REPO_ROOT)}")
