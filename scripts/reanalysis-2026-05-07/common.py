#!/usr/bin/env python3
"""Shared helpers for the 2026-05-06 stepwise reanalysis plots."""
from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd

DATA_ROOT = Path("data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini")
AYUSH_ROOT = DATA_ROOT / "ayush_reanalysis"
PLOT_ROOT = Path("findings/emnlp-2026-paper/plots/reanalysis-2026-05-07")
SCRIPT_ROOT = Path("scripts/reanalysis-2026-05-07")

DETERMINISTIC_DELTAS = AYUSH_ROOT / "deterministic_run_deltas.csv"
DETERMINISTIC_TIMEBINS = AYUSH_ROOT / "deterministic_timebin_metrics.csv"
EMBEDDING_DELTAS = AYUSH_ROOT / "embedding_run_deltas.csv"
EMBEDDING_TIMEBINS = AYUSH_ROOT / "embedding_run_timebin_metrics.csv"
LLM_DELTAS = AYUSH_ROOT / "llm_judge_run_deltas.csv"
LLM_TIMEBINS = AYUSH_ROOT / "llm_judge_run_timebin_metrics.csv"

CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy seed",
    "mag5": "5 conspiracy seeds",
    "mag25": "25 conspiracy seeds",
    "dom-agi": "25 AGI seeds",
    "dom-tech": "25 tech seeds",
}
CONDITION_COLORS = {
    "mag0": "#1b6b42",
    "mag1": "#3b6ea8",
    "mag5": "#f28e2b",
    "mag25": "#d94f4f",
    "dom-agi": "#7b4ea3",
    "dom-tech": "#4e9f3d",
}
MODEL_ORDER = ["GPT-5", "Gemini Flash Lite", "Kimi K2.5", "GLM-5"]
MODEL_SLUGS = {
    "GPT-5": "gpt5",
    "Gemini Flash Lite": "gemini_flash_lite",
    "Kimi K2.5": "kimi_k25",
    "GLM-5": "glm5",
}

METRICS = {
    "gzip": {
        "source": "deterministic",
        "column": "compression_gzip",
        "label": "Gzip compression ratio",
        "short": "Gzip",
        "direction_text": "Down means later text is easier to compress and more repetitive.",
        "collapse_direction": "down",
        "file_slug": "gzip",
    },
    "distinct5": {
        "source": "deterministic",
        "column": "distinct_5",
        "label": "Distinct-5",
        "short": "Distinct-5",
        "direction_text": "Down means fewer unique 5-grams.",
        "collapse_direction": "down",
        "file_slug": "distinct5",
    },
    "vendi": {
        "source": "embedding",
        "column": "vendi_score",
        "label": "Vendi Score",
        "short": "Vendi",
        "direction_text": "Down means fewer semantic modes in embedding space.",
        "collapse_direction": "down",
        "file_slug": "vendi",
    },
    "llm_collapse": {
        "source": "llm",
        "column": "collapse_index",
        "label": "Blinded LLM collapse index",
        "short": "LLM collapse",
        "direction_text": "Up means more judged repetition, rigidity, conformity, and lower novelty.",
        "collapse_direction": "up",
        "file_slug": "llm_collapse",
    },
}


def setup_style() -> None:
    mpl.rcParams.update({
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
    })


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def load_timebins(source: str) -> pd.DataFrame:
    if source == "deterministic":
        return read_csv(DETERMINISTIC_TIMEBINS)
    if source == "embedding":
        return read_csv(EMBEDDING_TIMEBINS)
    if source == "llm":
        return read_csv(LLM_TIMEBINS)
    raise ValueError(source)


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def condition_label(condition: str) -> str:
    return CONDITION_LABELS.get(str(condition), str(condition))


def model_slug(model: str) -> str:
    return MODEL_SLUGS.get(str(model), str(model).lower().replace(" ", "_").replace(".", ""))
