#!/usr/bin/env python3
"""Shared helpers for 2026-05-05 paper plots."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REANALYSIS_ROOT = Path("data/reanalysis-2026-05-05")
ANALYSIS_ROOT = REANALYSIS_ROOT / "analysis/archive-2026-plus-canonical-gemini"
AYUSH_ROOT = ANALYSIS_ROOT / "ayush_reanalysis"
PLOT_ROOT = Path("findings/emnlp-2026-paper/plots/reanalysis-2026-05-05")
STATS_ROOT = PLOT_ROOT / "stats"
TOPIC_ROBUSTNESS_ROOT = PLOT_ROOT / "topic_robustness"

DETERMINISTIC_DELTAS = AYUSH_ROOT / "deterministic_run_deltas.csv"
DETERMINISTIC_TIMEBINS = AYUSH_ROOT / "deterministic_timebin_metrics.csv"
EMBEDDING_DELTAS = AYUSH_ROOT / "embedding_run_deltas.csv"
EMBEDDING_TIMEBINS = AYUSH_ROOT / "embedding_run_timebin_metrics.csv"
LLM_DELTAS = AYUSH_ROOT / "llm_judge_run_deltas.csv"
LLM_TIMEBINS = AYUSH_ROOT / "llm_judge_run_timebin_metrics.csv"
TOPIC_ROBUSTNESS_DELTAS = TOPIC_ROBUSTNESS_ROOT / "topic_robustness_run_deltas.csv"

CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
CONDITION_LABELS = {
    "mag0": "Empty feed",
    "mag1": "1 conspiracy seed",
    "mag5": "5 conspiracy seeds",
    "mag25": "25 conspiracy seeds",
    "dom-agi": "25 AGI seeds",
    "dom-tech": "25 tech seeds",
}
MODEL_ORDER = ["GPT-5", "Gemini Flash Lite", "Kimi K2.5", "GLM-5"]
SCALE_ORDER = [10, 20, 30]
SCALE_LABELS = {10: "10 agents", 20: "20 agents", 30: "30 agents"}
N10_MODEL_ORDER = [
    "GPT-5",
    "Gemini Flash Lite",
    "Kimi K2.5",
    "GLM-5",
    "OLMo 3 32B Base",
    "OLMo 3 32B Instruct",
    "Qwen 3.5 35B A3B Base",
    "Mixed roster (Qwen 3.5 27B)",
]
FAMILY_LABELS = {
    "single_model_final": "Homogeneous single-model agents",
    "base_model_as_tool": "Base-model-as-tool agents",
    "mixed_model_roster": "Mixed-model roster",
    "obsession_prompting": "Obsession-prompted agents",
}

META_COLS = [
    "run_uid",
    "run_id",
    "scheme",
    "internal_family_label",
    "display_family_label",
    "model_display",
    "model_family",
    "roster_name",
    "condition",
    "scale",
    "n_agents",
    "source_path",
]


@dataclass(frozen=True)
class MetricSpec:
    key: str
    col: str
    label: str
    short_label: str
    direction: int
    units: str
    filename_stem: str
    fmt: str = "{:+.3f}"
    cmap: str = "RdBu_r"
    description: str = ""

    @property
    def collapse_positive_label(self) -> str:
        return "higher means more collapse" if self.direction == 1 else "lower means more collapse"


METRICS: dict[str, MetricSpec] = {
    "gzip": MetricSpec(
        key="gzip",
        col="delta_compression_gzip",
        label="Gzip compression ratio",
        short_label="Gzip",
        direction=-1,
        units="late minus early",
        filename_stem="gzip_fixed15m",
        fmt="{:+.3f}",
        description="Lower gzip ratios mean later text is easier to compress and more redundant.",
    ),
    "distinct5": MetricSpec(
        key="distinct5",
        col="delta_distinct_5",
        label="Distinct-5",
        short_label="Distinct-5",
        direction=-1,
        units="late minus early",
        filename_stem="distinct5_fixed15m",
        fmt="{:+.3f}",
        description="Lower Distinct-5 means fewer unique 5-grams relative to total 5-grams.",
    ),
    "distinct5_cumulative": MetricSpec(
        key="distinct5_cumulative",
        col="delta_distinct_5_cumulative",
        label="Cumulative Distinct-5",
        short_label="Cumulative Distinct-5",
        direction=-1,
        units="late minus early",
        filename_stem="distinct5_cumulative",
        fmt="{:+.3f}",
        description="Lower cumulative Distinct-5 means the run accumulates less lexical variety over time.",
    ),
    "vendi": MetricSpec(
        key="vendi",
        col="delta_vendi_score",
        label="Vendi semantic diversity",
        short_label="Vendi",
        direction=-1,
        units="late minus early",
        filename_stem="vendi_fixed15m",
        fmt="{:+.2f}",
        description="Lower Vendi Score means fewer effective semantic modes in the embedding space.",
    ),
    "llm_collapse": MetricSpec(
        key="llm_collapse",
        col="delta_collapse_index",
        label="Blinded LLM collapse index",
        short_label="LLM collapse index",
        direction=1,
        units="late minus early",
        filename_stem="llm_collapse_index_fixed15m",
        fmt="{:+.2f}",
        description="Higher blinded judge scores mean more repetition, frame convergence, conformity, rigidity, and lower novelty.",
    ),
    "hhi_norm": MetricSpec(
        key="hhi_norm",
        col="delta_topic_hhi_norm_robust",
        label="Normalized HHI/Simpson concentration",
        short_label="HHI concentration",
        direction=1,
        units="mean late minus early across k and seed",
        filename_stem="hhi_norm_robust",
        fmt="{:+.2f}",
        description="Higher normalized HHI means posts concentrate into fewer embedding clusters.",
    ),
}
PRIMARY_METRICS = ["gzip", "distinct5", "distinct5_cumulative", "vendi", "llm_collapse", "hhi_norm"]
PRIMARY_NO_TOPIC = ["gzip", "distinct5", "distinct5_cumulative", "vendi", "llm_collapse"]


def setup_style() -> None:
    mpl.rcParams.update({
        "figure.dpi": 130,
        "savefig.dpi": 300,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    })


def ensure_dirs() -> None:
    for p in [PLOT_ROOT, STATS_ROOT]:
        p.mkdir(parents=True, exist_ok=True)


def condition_label(x: str) -> str:
    return CONDITION_LABELS.get(str(x), str(x))


def family_label(x: str) -> str:
    return FAMILY_LABELS.get(str(x), str(x))


def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path, low_memory=False)


def _dedupe_cols(df: pd.DataFrame) -> pd.DataFrame:
    # Keep the first copy of duplicated metadata columns after merges.
    dupes = [c for c in df.columns if c.endswith("_x") or c.endswith("_y")]
    for c in dupes:
        base = c[:-2]
        if base not in df.columns:
            df[base] = df[c]
    return df[[c for c in df.columns if not (c.endswith("_x") or c.endswith("_y"))]]


def topic_robustness_by_run() -> pd.DataFrame:
    if not TOPIC_ROBUSTNESS_DELTAS.exists():
        raise FileNotFoundError(
            f"Missing {TOPIC_ROBUSTNESS_DELTAS}. Run build_topic_robustness.py first."
        )
    t = read_csv(TOPIC_ROBUSTNESS_DELTAS)
    agg = t.groupby(["run_uid", "scheme"], dropna=False).agg(
        delta_topic_hhi_norm_robust=("delta_topic_hhi_norm", "mean"),
        delta_topic_hhi_robust=("delta_topic_hhi", "mean"),
        delta_topic_entropy_norm_robust=("delta_topic_entropy_norm", "mean"),
        topic_hhi_norm_increase_rate=("delta_topic_hhi_norm", lambda s: float(np.mean(np.asarray(s) > 0))),
        topic_entropy_decline_rate=("delta_topic_entropy_norm", lambda s: float(np.mean(np.asarray(s) < 0))),
        topic_robustness_settings=("delta_topic_hhi_norm", "size"),
    ).reset_index()
    return agg


def load_run_deltas(scheme: str | None = None) -> pd.DataFrame:
    det = read_csv(DETERMINISTIC_DELTAS)
    emb = read_csv(EMBEDDING_DELTAS)
    llm = read_csv(LLM_DELTAS)
    if scheme is not None:
        det = det[det["scheme"] == scheme].copy()
        emb = emb[emb["scheme"] == scheme].copy()
        llm = llm[llm["scheme"] == scheme].copy()
    keys = ["run_uid", "scheme"]
    emb_metric_cols = ["delta_mean_pairwise_cosine", "delta_semantic_radius", "delta_vendi_score"]
    llm_metric_cols = [c for c in llm.columns if c.startswith("delta_")]
    df = det.merge(emb[keys + emb_metric_cols], on=keys, how="left")
    df = df.merge(llm[keys + llm_metric_cols], on=keys, how="left")
    df = _dedupe_cols(df)
    topic = topic_robustness_by_run()
    df = df.merge(topic, on=keys, how="left")
    df["condition_label"] = df["condition"].map(condition_label)
    df["family_label"] = df["internal_family_label"].map(family_label)
    df["n_agents"] = pd.to_numeric(df["n_agents"], errors="coerce").astype("Int64")
    return df


def load_timebins(kind: str, scheme: str = "fixed_15m") -> pd.DataFrame:
    if kind == "deterministic":
        df = read_csv(DETERMINISTIC_TIMEBINS)
    elif kind == "embedding":
        df = read_csv(EMBEDDING_TIMEBINS)
    elif kind == "llm":
        df = read_csv(LLM_TIMEBINS)
    else:
        raise ValueError(kind)
    df = df[df["scheme"] == scheme].copy()
    df["condition_label"] = df["condition"].map(condition_label)
    df["family_label"] = df["internal_family_label"].map(family_label)
    return df


def save_figure(fig: plt.Figure, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    fig.savefig(path.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def finite_values(vals: Iterable[float]) -> np.ndarray:
    arr = np.asarray(list(vals), dtype=float)
    return arr[np.isfinite(arr)]


def sign_test_p(values: Iterable[float]) -> float:
    vals = finite_values(values)
    vals = vals[vals != 0]
    n = len(vals)
    if n == 0:
        return math.nan
    k = int(min(np.sum(vals > 0), np.sum(vals < 0)))
    p = 2.0 * sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, p))


def summarize_values(values: Iterable[float]) -> dict[str, float | int]:
    vals = finite_values(values)
    if len(vals) == 0:
        return {
            "n": 0,
            "mean": math.nan,
            "median": math.nan,
            "n_positive": 0,
            "n_negative": 0,
            "sign_p": math.nan,
        }
    return {
        "n": int(len(vals)),
        "mean": float(np.mean(vals)),
        "median": float(np.median(vals)),
        "n_positive": int(np.sum(vals > 0)),
        "n_negative": int(np.sum(vals < 0)),
        "sign_p": sign_test_p(vals),
    }


def collapse_score(df: pd.DataFrame, spec: MetricSpec) -> pd.Series:
    return pd.to_numeric(df[spec.col], errors="coerce") * spec.direction


def symmetric_limits(values: Iterable[float], floor: float | None = None) -> tuple[float, float]:
    vals = finite_values(values)
    if len(vals) == 0:
        return -1, 1
    lim = float(np.nanmax(np.abs(vals)))
    if floor is not None:
        lim = max(lim, floor)
    if lim == 0 or not np.isfinite(lim):
        lim = 1.0
    return -lim, lim


def color_for_metric(spec: MetricSpec) -> str:
    # Make red mean the collapse direction while retaining raw delta values.
    return "RdBu" if spec.direction == -1 else "RdBu_r"


def add_zero_line(ax, orientation: str = "h") -> None:
    if orientation == "h":
        ax.axhline(0, color="#303030", lw=0.8, ls="--", zorder=1)
    else:
        ax.axvline(0, color="#303030", lw=0.8, ls="--", zorder=1)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def fmt_num(x: float, digits: int = 3) -> str:
    if not np.isfinite(x):
        return "NA"
    return f"{x:.{digits}f}"


def fmt_signed(x: float, digits: int = 3) -> str:
    if not np.isfinite(x):
        return "NA"
    return f"{x:+.{digits}f}"


def metric_title(spec: MetricSpec) -> str:
    return f"{spec.label}: {spec.units}"
