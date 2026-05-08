#!/usr/bin/env python3
"""Step 5: paper-facing phrase echo and embedding-neighborhood examples.

This figure avoids raw cluster IDs in the visual. It asks a simple question:
when an exact NLTK 5-token phrase repeats, do the posts carrying that phrase
concentrate in one embedding neighborhood more than the run as a whole?
"""
from __future__ import annotations

import json
import math
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from textwrap import wrap

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Ellipse, FancyBboxPatch, Rectangle
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize

try:
    from nltk.tokenize import PunktTokenizer, word_tokenize
    from nltk.util import ngrams as nltk_ngrams
except Exception as exc:  # pragma: no cover
    raise SystemExit(
        "NLTK is required for Step 5. Run with /tmp/moltbook-nltk-venv/bin/python or install NLTK."
    ) from exc

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import AYUSH_ROOT, CONDITION_LABELS, PLOT_ROOT, setup_style  # noqa: E402

TOPIC_ROOT = AYUSH_ROOT / "topic_convergence"
POST_INDEX = AYUSH_ROOT / "post_index.csv"
TOPIC_ASSIGNMENTS = TOPIC_ROOT / "topic_assignments.csv"
TOPIC_KEYWORDS = TOPIC_ROOT / "topic_keywords.csv"
EMBEDDING_DB = AYUSH_ROOT.parent / "embedding_cache.sqlite"
OUT_DIR = PLOT_ROOT / "step05_phrase_cluster_concentration_examples"
NGRAM_N = 5
N_CLUSTERS = 12
SENTENCE_TOKENIZER = PunktTokenizer("english")

# These examples were chosen because the phrase and the dominant embedding
# neighborhood are interpretable after checking cluster keywords and snippets.
EXAMPLES = [
    {
        "model_display": "GPT-5",
        "condition": "mag25",
        "n_agents": 10,
        "display_phrase": "Claim (1 line)",
        "anchor_tokens": ("Claim", "(", "1", "line", ")"),
        "neighborhood_label": "Claim-checking scaffold",
        "neighborhood_terms": "claim, check, falsifier, line",
        "context_snippet": "My template today: Claim (1 line): … Falsifier I’d accept: …",
    },
    {
        "model_display": "GPT-5",
        "condition": "dom-agi",
        "n_agents": 10,
        "display_phrase": "the Ops Pack v0.1.",
        "anchor_tokens": ("the", "Ops", "Pack", "v0.1", "."),
        "neighborhood_label": "Ops and rollback scaffold",
        "neighborhood_terms": "owner, rollback, path, failure",
        "context_snippet": "I’ll fold real examples into the Ops Pack v0.1.",
    },
    {
        "model_display": "Kimi K2.5",
        "condition": "mag1",
        "n_agents": 10,
        "display_phrase": "the web we have woven",
        "anchor_tokens": ("the", "web", "we", "have", "woven"),
        "neighborhood_label": "Community-reflection motif",
        "neighborhood_terms": "agent, questions, community, space",
        "context_snippet": "agent_beta speaks of the web we have woven.",
    },
]


@dataclass
class ExampleResult:
    index: int
    model_display: str
    condition: str
    condition_label: str
    n_agents: int
    run_uid: str
    run_id: str
    display_phrase: str
    anchor_tokens: tuple[str, ...]
    neighborhood_label: str
    neighborhood_terms: str
    context_snippet: str
    n_all_posts: int
    n_phrase_posts: int
    n_phrase_agents: int
    all_counts: Counter
    phrase_counts: Counter
    dominant_cluster: str
    all_count_in_dominant: int
    phrase_count_in_dominant: int
    all_share_in_dominant: float
    phrase_share_in_dominant: float
    all_hhi_norm: float
    phrase_hhi_norm: float

    @property
    def delta_hhi_norm(self) -> float:
        return self.phrase_hhi_norm - self.all_hhi_norm


def ensure_nltk_ready() -> None:
    try:
        _ = word_tokenize("Tokenizer check.")
        _ = list(SENTENCE_TOKENIZER.span_tokenize("A sentence. Another sentence."))
    except LookupError as exc:
        raise SystemExit("NLTK tokenizer data missing. Run: python -m nltk.downloader punkt punkt_tab") from exc


def row_text(row: pd.Series) -> str:
    title = "" if pd.isna(row.get("title", "")) else str(row.get("title", ""))
    content = "" if pd.isna(row.get("content", "")) else str(row.get("content", ""))
    return f"{title}\n{content}".strip()


def has_exact_phrase(text: str, target: tuple[str, ...]) -> bool:
    for sentence in SENTENCE_TOKENIZER.tokenize(text or ""):
        tokens = word_tokenize(sentence)
        for gram in nltk_ngrams(tokens, NGRAM_N):
            if tuple(gram) == target:
                return True
    return False


def normalized_hhi(counts: Counter, *, k: int = N_CLUSTERS) -> float:
    total = sum(counts.values())
    if total <= 0:
        return math.nan
    raw = sum((count / total) ** 2 for count in counts.values())
    return (raw - 1.0 / k) / (1.0 - 1.0 / k)


def load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    posts = pd.read_csv(POST_INDEX, low_memory=False)
    posts = posts[~posts["is_seed"].astype(bool)].copy()
    topics = pd.read_csv(TOPIC_ASSIGNMENTS, low_memory=False)
    keywords = pd.read_csv(TOPIC_KEYWORDS, low_memory=False)
    topic_keywords = {str(row.topic): str(row.keywords) for row in keywords.itertuples()}
    return posts, topics, topic_keywords


def build_examples(posts: pd.DataFrame, topics: pd.DataFrame) -> list[ExampleResult]:
    results: list[ExampleResult] = []
    minutes = pd.to_numeric(posts["minutes_elapsed"], errors="coerce")
    posts = posts[(minutes >= 0) & (minutes <= 60)].copy()

    for index, spec in enumerate(EXAMPLES, start=1):
        sub = posts[
            (posts["internal_family_label"] == "single_model_final")
            & (posts["model_display"] == spec["model_display"])
            & (posts["condition"] == spec["condition"])
            & (posts["n_agents"] == spec["n_agents"])
        ].copy()
        if sub.empty:
            raise ValueError(f"No posts found for {spec}")

        run_uid = str(sub["run_uid"].iloc[0])
        run_id = str(sub["run_id"].iloc[0])
        merged = sub.merge(topics[["record_id", "topic"]], on="record_id", how="inner")
        if merged.empty:
            raise ValueError(f"No embedding-cluster assignments found for {spec}")

        target = tuple(spec["anchor_tokens"])
        merged["full_text_for_match"] = merged.apply(row_text, axis=1)
        phrase_mask = merged["full_text_for_match"].apply(lambda value: has_exact_phrase(value, target))
        phrase = merged[phrase_mask].copy()
        if phrase.empty:
            raise ValueError(f"Phrase not found for {spec}")

        all_counts = Counter(merged["topic"])
        phrase_counts = Counter(phrase["topic"])
        dominant_cluster, phrase_dominant_count = phrase_counts.most_common(1)[0]
        all_total = sum(all_counts.values())
        phrase_total = sum(phrase_counts.values())
        all_dominant_count = all_counts[dominant_cluster]

        results.append(
            ExampleResult(
                index=index,
                model_display=str(spec["model_display"]),
                condition=str(spec["condition"]),
                condition_label=CONDITION_LABELS.get(str(spec["condition"]), str(spec["condition"])),
                n_agents=int(spec["n_agents"]),
                run_uid=run_uid,
                run_id=run_id,
                display_phrase=str(spec["display_phrase"]),
                anchor_tokens=target,
                neighborhood_label=str(spec["neighborhood_label"]),
                neighborhood_terms=str(spec["neighborhood_terms"]),
                context_snippet=str(spec["context_snippet"]),
                n_all_posts=int(merged["record_id"].nunique()),
                n_phrase_posts=int(phrase["record_id"].nunique()),
                n_phrase_agents=int(phrase["author_name"].nunique()),
                all_counts=all_counts,
                phrase_counts=phrase_counts,
                dominant_cluster=str(dominant_cluster),
                all_count_in_dominant=int(all_dominant_count),
                phrase_count_in_dominant=int(phrase_dominant_count),
                all_share_in_dominant=all_dominant_count / all_total if all_total else math.nan,
                phrase_share_in_dominant=phrase_dominant_count / phrase_total if phrase_total else math.nan,
                all_hhi_norm=normalized_hhi(all_counts),
                phrase_hhi_norm=normalized_hhi(phrase_counts),
            )
        )
    return results


def wrapped(text: str, width: int) -> str:
    return "\n".join(wrap(text, width=width, break_long_words=False, replace_whitespace=False))


def draw_bar(ax, x: float, y: float, width: float, height: float, share: float, color: str, label: str) -> None:
    ax.add_patch(Rectangle((x, y), width, height, facecolor="#ECE7DF", edgecolor="none", zorder=1))
    ax.add_patch(Rectangle((x, y), width * share, height, facecolor=color, edgecolor="none", zorder=2))
    ax.text(x, y + height + 0.020, label, ha="left", va="bottom", fontsize=8.7, color="#53636E")
    ax.text(x + width + 0.012, y + height / 2, f"{share * 100:.0f}%", ha="left", va="center", fontsize=10.2, color="#1F2A33", fontweight="bold")


def draw_figure(results: list[ExampleResult], output_path: Path) -> None:
    setup_style()
    fig = plt.figure(figsize=(13.8, 8.6), facecolor="#F7F3ED")
    fig.text(0.055, 0.958, "Repeated phrases become semantic anchors", ha="left", va="top", fontsize=23, fontweight="bold", color="#1F2A33")
    fig.text(
        0.055,
        0.915,
        "For each exact 5-token phrase, compare all posts in the run with posts containing the phrase.",
        ha="left",
        va="top",
        fontsize=11.6,
        color="#52616B",
    )
    fig.text(
        0.055,
        0.888,
        "Both bars refer to the same neighborhood. The denominators differ: all run posts vs the subset containing the phrase.",
        ha="left",
        va="top",
        fontsize=11.6,
        color="#52616B",
    )

    card_positions = [0.638, 0.374, 0.110]
    all_color = "#B9B1A6"
    phrase_color = "#0E7C7B"
    accent = "#B24E3A"

    for result, bottom in zip(results, card_positions):
        ax = fig.add_axes([0.055, bottom, 0.89, 0.225])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        ax.add_patch(
            FancyBboxPatch(
                (0, 0),
                1,
                1,
                boxstyle="round,pad=0.012,rounding_size=0.025",
                facecolor="#FFFFFF",
                edgecolor="#DDD5CA",
                linewidth=1.0,
                clip_on=False,
            )
        )

        ax.text(0.025, 0.800, f"{result.index}", fontsize=12, fontweight="bold", color="#FFFFFF", ha="center", va="center", bbox=dict(boxstyle="circle,pad=0.35", fc=accent, ec="none"))
        ax.text(0.065, 0.815, f"“{result.display_phrase}”", fontsize=14.8, fontweight="bold", color="#1F2A33", ha="left", va="center")
        ax.text(0.065, 0.655, f"{result.model_display} · {result.condition_label}", fontsize=10.5, fontweight="bold", color="#40525E", ha="left", va="center")
        ax.text(
            0.065,
            0.525,
            f"{result.n_phrase_posts} phrase posts · {result.n_phrase_agents}/{result.n_agents} agents",
            fontsize=9.6,
            color="#52616B",
            ha="left",
            va="center",
        )
        ax.text(0.065, 0.315, "Example context", fontsize=8.8, color="#7A858C", ha="left", va="center", fontweight="bold")
        ax.text(0.065, 0.185, wrapped(result.context_snippet, 48), fontsize=9.3, color="#2F3D46", ha="left", va="center")

        ax.plot([0.385, 0.385], [0.13, 0.87], color="#E5DED5", lw=1.0)
        ax.text(0.420, 0.795, "Dominant embedding neighborhood", fontsize=8.8, color="#7A858C", ha="left", va="center", fontweight="bold")
        ax.text(0.420, 0.640, result.neighborhood_label, fontsize=12.2, fontweight="bold", color="#1F2A33", ha="left", va="center")
        ax.text(0.420, 0.500, f"keywords: {result.neighborhood_terms}", fontsize=9.4, color="#52616B", ha="left", va="center")
        ax.text(0.420, 0.335, "name checked against phrase-context snippets", fontsize=8.5, color="#8A949B", ha="left", va="center")
        ax.text(0.420, 0.195, f"C, all → phrase: {result.all_hhi_norm:.2f} → {result.phrase_hhi_norm:.2f}", fontsize=9.7, color="#40525E", ha="left", va="center", fontweight="bold")

        ax.plot([0.655, 0.655], [0.13, 0.87], color="#E5DED5", lw=1.0)
        ax.text(0.690, 0.810, "Share in that same neighborhood", fontsize=10.2, fontweight="bold", color="#1F2A33", ha="left", va="center")
        draw_bar(ax, 0.690, 0.570, 0.220, 0.070, result.all_share_in_dominant, all_color, f"All run posts ({result.all_count_in_dominant}/{result.n_all_posts})")
        draw_bar(ax, 0.690, 0.315, 0.220, 0.070, result.phrase_share_in_dominant, phrase_color, f"Phrase posts ({result.phrase_count_in_dominant}/{result.n_phrase_posts})")
        ax.text(0.690, 0.145, f"ΔC = {result.delta_hhi_norm:+.2f}", fontsize=10.2, color="#156B45", ha="left", va="center", fontweight="bold")

    fig.text(
        0.055,
        0.040,
        "C is normalized HHI across 12 embedding neighborhoods. Higher C means posts occupy fewer neighborhoods. Neighborhood names are shorthand from cluster keywords and checked snippets.",
        ha="left",
        va="bottom",
        fontsize=8.9,
        color="#6D7980",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def load_selected_embeddings(record_ids: list[str]) -> dict[str, np.ndarray]:
    """Load only the embeddings needed for the selected example runs."""
    if not EMBEDDING_DB.exists():
        raise FileNotFoundError(EMBEDDING_DB)
    wanted = list(dict.fromkeys(str(record_id) for record_id in record_ids))
    out: dict[str, np.ndarray] = {}
    conn = sqlite3.connect(EMBEDDING_DB)
    try:
        for start in range(0, len(wanted), 500):
            chunk = wanted[start : start + 500]
            placeholders = ",".join("?" for _ in chunk)
            query = f"SELECT record_id, dim, embedding FROM embeddings WHERE record_id IN ({placeholders})"
            for record_id, dim, blob in conn.execute(query, chunk):
                out[str(record_id)] = np.frombuffer(blob, dtype=np.float32, count=int(dim)).copy()
    finally:
        conn.close()
    missing = sorted(set(wanted) - set(out))
    if missing:
        raise ValueError(f"Missing embeddings for {len(missing)} selected records")
    return out


def frame_for_embedding_plot(posts: pd.DataFrame, topics: pd.DataFrame, result: ExampleResult) -> pd.DataFrame:
    minutes = pd.to_numeric(posts["minutes_elapsed"], errors="coerce")
    sub = posts[
        (minutes >= 0)
        & (minutes <= 60)
        & (posts["internal_family_label"] == "single_model_final")
        & (posts["model_display"] == result.model_display)
        & (posts["condition"] == result.condition)
        & (posts["n_agents"] == result.n_agents)
    ].copy()
    merged = sub.merge(topics[["record_id", "topic"]], on="record_id", how="inner")
    merged["full_text_for_match"] = merged.apply(row_text, axis=1)
    merged["phrase_match"] = merged["full_text_for_match"].apply(lambda value: has_exact_phrase(value, result.anchor_tokens))
    merged["dominant_neighborhood"] = merged["topic"].astype(str).eq(result.dominant_cluster)
    return merged.reset_index(drop=True)


def project_run_embeddings(frame: pd.DataFrame, embedding_map: dict[str, np.ndarray]) -> pd.DataFrame:
    ids = frame["record_id"].astype(str).to_list()
    mat = np.vstack([embedding_map[record_id] for record_id in ids]).astype(np.float32)
    mat = normalize(mat, norm="l2", copy=False)
    if len(frame) >= 3:
        coords = TruncatedSVD(n_components=2, random_state=43).fit_transform(mat).astype(np.float32)
    else:
        coords = np.zeros((len(frame), 2), dtype=np.float32)
        coords[:, 0] = np.arange(len(frame), dtype=np.float32)
    out = frame.copy()
    out["svd_x"] = coords[:, 0]
    out["svd_y"] = coords[:, 1]
    return out


def add_covariance_ellipse(ax, points: np.ndarray, color: str) -> None:
    if len(points) < 4:
        return
    cov = np.cov(points[:, 0], points[:, 1])
    if not np.all(np.isfinite(cov)):
        return
    vals, vecs = np.linalg.eigh(cov)
    vals = np.maximum(vals, 1e-12)
    order = vals.argsort()[::-1]
    vals = vals[order]
    vecs = vecs[:, order]
    angle = math.degrees(math.atan2(vecs[1, 0], vecs[0, 0]))
    center = points.mean(axis=0)
    ell = Ellipse(
        center,
        width=4.0 * math.sqrt(vals[0]),
        height=4.0 * math.sqrt(vals[1]),
        angle=angle,
        facecolor=color,
        edgecolor=color,
        alpha=0.13,
        linewidth=2.0,
        zorder=1,
    )
    ax.add_patch(ell)
    outline = Ellipse(
        center,
        width=4.0 * math.sqrt(vals[0]),
        height=4.0 * math.sqrt(vals[1]),
        angle=angle,
        facecolor="none",
        edgecolor=color,
        alpha=0.75,
        linewidth=1.4,
        zorder=2,
    )
    ax.add_patch(outline)


def draw_embedding_figure(posts: pd.DataFrame, topics: pd.DataFrame, results: list[ExampleResult], output_path: Path) -> None:
    """Draw a visual 2D embedding projection for the selected phrase examples."""
    frames = [frame_for_embedding_plot(posts, topics, result) for result in results]
    record_ids = [str(record_id) for frame in frames for record_id in frame["record_id"].astype(str)]
    embedding_map = load_selected_embeddings(record_ids)
    frames = [project_run_embeddings(frame, embedding_map) for frame in frames]

    setup_style()
    fig, axes = plt.subplots(1, len(results), figsize=(15.4, 6.8), facecolor="#F7F3ED")
    if len(results) == 1:
        axes = [axes]
    fig.subplots_adjust(left=0.045, right=0.985, top=0.700, bottom=0.170, wspace=0.18)
    fig.text(0.045, 0.955, "Phrase echoes in embedding space", ha="left", va="top", fontsize=23, fontweight="bold", color="#1F2A33")
    fig.text(
        0.045,
        0.900,
        "Each panel is one run. Grey points are other posts. Amber points are the phrase's dominant embedding neighborhood. Teal rings are posts containing the exact phrase.",
        ha="left",
        va="top",
        fontsize=11.3,
        color="#52616B",
    )
    fig.text(
        0.045,
        0.868,
        "The shaded ellipse marks the center of the phrase's dominant neighborhood; amber membership is the actual cluster assignment.",
        ha="left",
        va="top",
        fontsize=11.3,
        color="#52616B",
    )

    other_color = "#CFC7BD"
    dominant_color = "#D28C35"
    phrase_color = "#087E78"
    outside_color = "#B94435"

    for ax, result, frame in zip(axes, results, frames):
        ax.set_facecolor("#FFFFFF")
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_color("#D8D0C5")
            spine.set_linewidth(1.0)
        other = frame[~frame["dominant_neighborhood"] & ~frame["phrase_match"]]
        dominant = frame[frame["dominant_neighborhood"]]
        dominant_nonphrase = frame[frame["dominant_neighborhood"] & ~frame["phrase_match"]]
        phrase_in = frame[frame["dominant_neighborhood"] & frame["phrase_match"]]
        phrase_out = frame[~frame["dominant_neighborhood"] & frame["phrase_match"]]

        if len(dominant):
            add_covariance_ellipse(ax, dominant[["svd_x", "svd_y"]].to_numpy(dtype=float), dominant_color)
        ax.scatter(other["svd_x"], other["svd_y"], s=18, c=other_color, alpha=0.42, linewidths=0, label="Other posts", zorder=3)
        ax.scatter(dominant_nonphrase["svd_x"], dominant_nonphrase["svd_y"], s=24, c=dominant_color, alpha=0.62, linewidths=0, label="Dominant neighborhood", zorder=4)
        ax.scatter(phrase_in["svd_x"], phrase_in["svd_y"], s=66, facecolors="none", edgecolors=phrase_color, linewidths=1.8, label="Posts with phrase", zorder=6)
        if len(phrase_out):
            ax.scatter(phrase_out["svd_x"], phrase_out["svd_y"], s=70, c=outside_color, marker="x", linewidths=1.8, label="Phrase outside neighborhood", zorder=7)

        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"“{result.display_phrase}”\n{result.model_display} · {result.condition_label}", fontsize=12.1, fontweight="bold", color="#1F2A33", pad=12)
        ax.text(
            0.035,
            0.965,
            f"{result.neighborhood_label}\n{result.phrase_count_in_dominant}/{result.n_phrase_posts} phrase posts assigned here",
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=9.0,
            color="#2F3D46",
            bbox={"boxstyle": "round,pad=0.32", "facecolor": "#FFFFFF", "edgecolor": "#DDD5CA", "alpha": 0.92},
            zorder=10,
        )
        ax.text(0.035, 0.045, "2D SVD projection", transform=ax.transAxes, ha="left", va="bottom", fontsize=8.4, color="#7A858C")

    handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=other_color, markeredgewidth=0, markersize=7, alpha=0.65, label="Other posts"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=dominant_color, markeredgewidth=0, markersize=7, alpha=0.80, label="Dominant neighborhood"),
        plt.Line2D([0], [0], marker="o", color=phrase_color, markerfacecolor="none", markeredgewidth=1.8, markersize=8, label="Posts with phrase"),
        plt.Line2D([0], [0], marker="x", color=outside_color, markeredgewidth=1.8, markersize=8, label="Phrase outside neighborhood"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False, fontsize=9.2, bbox_to_anchor=(0.5, 0.085))
    fig.text(
        0.045,
        0.038,
        "Positions are within-run 2D SVD projections of Qwen post embeddings for visualization. Neighborhood assignments come from the 12-cluster clean reanalysis model.",
        ha="left",
        va="bottom",
        fontsize=8.6,
        color="#6D7980",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=300, bbox_inches="tight", facecolor=fig.get_facecolor())
    fig.savefig(output_path.with_suffix(".pdf"), bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_tables(results: list[ExampleResult], topic_keywords: dict[str, str]) -> None:
    summary_rows = []
    distribution_rows = []
    for result in results:
        summary_rows.append(
            {
                "example": result.index,
                "model_display": result.model_display,
                "condition": result.condition,
                "condition_label": result.condition_label,
                "n_agents": result.n_agents,
                "run_id": result.run_id,
                "run_uid": result.run_uid,
                "display_phrase": result.display_phrase,
                "anchor_tokens_json": json.dumps(list(result.anchor_tokens), ensure_ascii=False),
                "n_all_posts": result.n_all_posts,
                "n_phrase_posts": result.n_phrase_posts,
                "n_phrase_agents": result.n_phrase_agents,
                "neighborhood_label": result.neighborhood_label,
                "neighborhood_terms": result.neighborhood_terms,
                "dominant_internal_cluster": result.dominant_cluster,
                "all_count_in_dominant": result.all_count_in_dominant,
                "phrase_count_in_dominant": result.phrase_count_in_dominant,
                "all_share_in_dominant": result.all_share_in_dominant,
                "phrase_share_in_dominant": result.phrase_share_in_dominant,
                "all_hhi_norm": result.all_hhi_norm,
                "phrase_hhi_norm": result.phrase_hhi_norm,
                "delta_hhi_norm": result.delta_hhi_norm,
                "context_snippet": result.context_snippet,
            }
        )
        for population, counts in [("all_posts", result.all_counts), ("phrase_posts", result.phrase_counts)]:
            total = sum(counts.values())
            for cluster in sorted(counts):
                distribution_rows.append(
                    {
                        "example": result.index,
                        "population": population,
                        "internal_cluster": cluster,
                        "cluster_keywords": topic_keywords.get(cluster, ""),
                        "count": counts[cluster],
                        "share": counts[cluster] / total if total else math.nan,
                    }
                )
    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "phrase_cluster_examples.csv", index=False)
    pd.DataFrame(distribution_rows).to_csv(OUT_DIR / "phrase_cluster_distributions.csv", index=False)
    (OUT_DIR / "summary.json").write_text(json.dumps({"examples": summary_rows}, indent=2, ensure_ascii=False))


def write_readme(results: list[ExampleResult]) -> None:
    table_rows = []
    for result in results:
        table_rows.append(
            f"| {result.index} | {result.model_display} | {result.condition_label} | {result.display_phrase} | "
            f"{result.n_phrase_posts} | {result.n_phrase_agents}/{result.n_agents} | {result.neighborhood_label} | "
            f"{result.all_share_in_dominant:.0%} | {result.phrase_share_in_dominant:.0%} | "
            f"{result.all_hhi_norm:.2f} → {result.phrase_hhi_norm:.2f} | {result.delta_hhi_norm:+.2f} |"
        )
    readme = f"""# Step 5: phrase echoes and embedding neighborhoods

This is the paper-facing replacement for the first Step 5 draft. The first draft exposed internal cluster IDs in the figure. This version hides those IDs and explains the relationship directly.

## Question

When an exact repeated phrase appears, do the posts containing that phrase concentrate in one embedding neighborhood?

## Scope

- Clean reanalysis topic assignments from `{TOPIC_ASSIGNMENTS}`
- Agent-generated posts only
- First 60 minutes only
- Exact NLTK 5-token anchors
- Punctuation and casing retained
- Seed posts are not loaded or used

## Main visual encoding

The right-side bars show the share of posts that fall into the phrase's dominant embedding neighborhood. The two bars use different denominators:

- grey: all posts in the same run
- teal: only the subset of posts containing the exact phrase

Example: `222/346 = 64%` means 222 of all 346 run posts are in the claim-checking neighborhood. `79/84 = 94%` means 79 of the 84 phrase posts are in that same neighborhood.

`C` is normalized HHI over all 12 embedding neighborhoods. Higher `C` means the posts occupy fewer neighborhoods.

## Examples

| # | Model | Condition | Phrase | Phrase posts | Agents | Neighborhood shorthand | All-post share | Phrase-post share | C | ΔC |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
""" + "\n".join(table_rows) + """

## Outputs

- `phrase_echo_cluster_concentration.png/pdf`
- `phrase_echo_concentration_embedding.png/pdf`
- `phrase_cluster_examples.csv`
- `phrase_cluster_distributions.csv`
- `summary.json`

## Wording

Use **embedding neighborhood** or **embedding cluster**, not topic. The shorthand labels in the figure are based on cluster keywords plus checked phrase-context snippets.
"""
    (OUT_DIR / "README.md").write_text(readme)


def main() -> None:
    ensure_nltk_ready()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    posts, topics, topic_keywords = load_inputs()
    results = build_examples(posts, topics)
    draw_figure(results, OUT_DIR / "phrase_echo_cluster_concentration.png")
    draw_embedding_figure(posts, topics, results, OUT_DIR / "phrase_echo_concentration_embedding.png")
    write_tables(results, topic_keywords)
    write_readme(results)
    print(f"Wrote paper-facing Step 5 outputs to {OUT_DIR}")
    for result in results:
        print(
            f"{result.display_phrase}: share {result.all_share_in_dominant:.0%} → {result.phrase_share_in_dominant:.0%}, "
            f"C {result.all_hhi_norm:.2f} → {result.phrase_hhi_norm:.2f}, ΔC {result.delta_hhi_norm:+.2f}"
        )


if __name__ == "__main__":
    main()
