#!/usr/bin/env python3
"""Build final aggregate report for archive-2026 + canonical Gemini analysis."""
from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
SCORE_FIELDS = [
    "novelty",
    "semantic_repetition",
    "narrative_convergence",
    "groupthink",
    "specificity",
    "evidence_grounding",
    "epistemic_caution",
    "template_rigidity",
    "source_citation_quality",
]
COLLAPSE_FIELDS = ["semantic_repetition", "narrative_convergence", "groupthink", "template_rigidity"]


def is_true(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def md_table(df: pd.DataFrame, cols: list[str] | None = None, max_rows: int = 20, decimals: int = 3) -> str:
    if cols:
        df = df[cols]
    df = df.head(max_rows).copy()
    for c in df.columns:
        if pd.api.types.is_float_dtype(df[c]):
            df[c] = df[c].map(lambda x: "" if pd.isna(x) else f"{x:.{decimals}f}")
    headers = list(df.columns)
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in headers) + " |")
    return "\n".join(lines)


def weighted_means(df: pd.DataFrame, by: list[str], weight_col: str, value_cols: list[str]) -> pd.DataFrame:
    rows = []
    for key, sub in df.groupby(by, dropna=False):
        if not isinstance(key, tuple):
            key = (key,)
        w = sub[weight_col].astype(float).to_numpy()
        row = {col: val for col, val in zip(by, key)}
        row["n_full_nonseed_posts_with_judged_cells"] = int(w.sum())
        row["n_judged"] = int(sub.get("n_judged_cell", pd.Series(dtype=float)).sum()) if "n_judged_cell" in sub.columns else int(len(sub))
        for col in value_cols:
            vals = sub[col].astype(float).to_numpy()
            mask = np.isfinite(vals) & np.isfinite(w) & (w > 0)
            row[col] = float(np.average(vals[mask], weights=w[mask])) if mask.any() else float("nan")
        rows.append(row)
    return pd.DataFrame(rows)


def plot_barh(df: pd.DataFrame, label_col: str, value_col: str, path: Path, title: str, xlabel: str, color: str = "#4e79a7") -> None:
    sub = df.sort_values(value_col).copy()
    fig, ax = plt.subplots(figsize=(10, max(4, 0.45 * len(sub))))
    ax.barh(sub[label_col].astype(str), sub[value_col], color=color)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_group_scatter(df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))
    sizes = 80 + 800 * (df["n_posts"] / df["n_posts"].max())
    ax.scatter(df["mean_pairwise_cosine"], df["weighted_collapse_index"], s=sizes, alpha=0.75, color="#e15759", edgecolor="white")
    for _, r in df.iterrows():
        ax.annotate(str(r["group"]), (r["mean_pairwise_cosine"], r["weighted_collapse_index"]), xytext=(4, 4), textcoords="offset points", fontsize=8)
    ax.set_xlabel("Full-corpus within-run embedding coherence")
    ax.set_ylabel("Cell-weighted LLM collapse index")
    ax.set_title("Embedding coherence vs. judged collapse by group")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_cluster_scatter(df: pd.DataFrame, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = df["collapse_pattern"].fillna("unknown").astype("category").cat.codes
    sc = ax.scatter(df["n_posts"], df["collapse_index"], c=colors, cmap="tab20", s=40 + 260 * (df["n_judged"] / max(1, df["n_judged"].max())), alpha=0.8, edgecolor="white")
    ax.set_xscale("log")
    ax.set_xlabel("Cluster posts (log scale)")
    ax.set_ylabel("Cluster LLM collapse index")
    ax.set_title("Global clusters: size vs. judged collapse")
    top = df.sort_values(["n_posts", "collapse_index"], ascending=False).head(10)
    for _, r in top.iterrows():
        label = f"c{int(r['cluster_id']):02d}"
        if isinstance(r.get("short_label"), str) and r["short_label"]:
            label += ": " + r["short_label"][:24]
        ax.annotate(label, (r["n_posts"], r["collapse_index"]), xytext=(4, 4), textcoords="offset points", fontsize=7)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_metric_heatmap(group_df: pd.DataFrame, path: Path) -> None:
    metrics = ["weighted_novelty", "weighted_semantic_repetition", "weighted_narrative_convergence", "weighted_groupthink", "weighted_template_rigidity", "weighted_evidence_grounding"]
    labels = ["novelty", "semantic rep.", "narrative conv.", "groupthink", "template rigid.", "evidence"]
    pivot = group_df.set_index("group")[metrics]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    im = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap="magma", vmin=1, vmax=5)
    ax.set_xticks(range(len(metrics)), labels, rotation=25, ha="right")
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    ax.set_title("Cell-weighted LLM judge means by group")
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            val = pivot.iat[i, j]
            if np.isfinite(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=7, color="white" if val > 3 else "black")
    fig.colorbar(im, ax=ax, label="Mean score (1-5)")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def artifact_inventory(root: Path, final_dir: Path) -> pd.DataFrame:
    interesting_dirs = [
        root,
        root / "embedding_report",
        root / "llm_judge",
        final_dir,
        root / "embeddings",
        root / "individual_analysis",
        root / "individual_analysis" / "models",
        root / "individual_analysis" / "conditions",
    ]
    rows = []
    seen: set[Path] = set()
    for d in interesting_dirs:
        if not d.exists():
            continue
        for p in sorted(d.glob("*")):
            if p.is_file() and p not in seen:
                seen.add(p)
                rows.append({
                    "path": str(p),
                    "name": p.name,
                    "suffix": p.suffix,
                    "size_bytes": p.stat().st_size,
                    "size_mb": round(p.stat().st_size / (1024 * 1024), 3),
                })
    return pd.DataFrame(rows).sort_values(["suffix", "path"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = ap.parse_args()
    root = Path(args.out_dir)
    final_dir = root / "final_report"
    final_dir.mkdir(parents=True, exist_ok=True)

    index = pd.read_csv(root / "combined_posts_index.csv")
    emb_group = pd.read_csv(root / "embedding_report" / "group_embedding_summary.csv")
    emb_model = pd.read_csv(root / "embedding_report" / "model_embedding_summary.csv")
    emb_cluster = pd.read_csv(root / "embedding_report" / "cluster_summary.csv")
    emb_data = pd.read_csv(root / "embedding_report" / "embedding_analysis_data.csv")
    judge_group = pd.read_csv(root / "llm_judge" / "judge_summary_by_group.csv")
    judge_model = pd.read_csv(root / "llm_judge" / "judge_summary_by_model.csv")
    judge_cell = pd.read_csv(root / "llm_judge" / "judge_summary_by_cell.csv")
    judge_cluster = pd.read_csv(root / "llm_judge" / "judge_summary_by_cluster.csv")
    cluster_labels = pd.read_csv(root / "llm_judge" / "cluster_labels.csv")
    judge_results = pd.read_csv(root / "llm_judge" / "judge_results.csv")

    # Cell-weighted judge estimates: cell means are weighted by the full nonseed corpus
    # counts in each group/model/condition/scale cell.
    emb_nonseed = emb_data[~is_true(emb_data["is_seed"])].copy()
    cell_cols = ["group", "model_family", "condition", "scale"]
    cell_counts = emb_nonseed.groupby(cell_cols, dropna=False).size().reset_index(name="n_full_nonseed_cell")
    rename = {f"{m}_mean": f"weighted_{m}" for m in SCORE_FIELDS if f"{m}_mean" in judge_cell.columns}
    rename.update({f"{SCORE_FIELDS[0]}_count": "n_judged_cell"})
    jcell = judge_cell.rename(columns=rename)
    metric_cols = [f"weighted_{m}" for m in SCORE_FIELDS]
    cell_join = cell_counts.merge(jcell[cell_cols + metric_cols + ["n_judged_cell"]], on=cell_cols, how="left")
    cell_join.to_csv(final_dir / "final_cell_weighting_inputs.csv", index=False)

    weighted_group = weighted_means(cell_join.dropna(subset=["weighted_semantic_repetition"]), ["group"], "n_full_nonseed_cell", metric_cols)
    weighted_model = weighted_means(cell_join.dropna(subset=["weighted_semantic_repetition"]), ["model_family"], "n_full_nonseed_cell", metric_cols)
    for df in [weighted_group, weighted_model]:
        df["weighted_collapse_index"] = df[[f"weighted_{m}" for m in COLLAPSE_FIELDS]].mean(axis=1)

    group = emb_group.merge(judge_group, on="group", how="left", suffixes=("_embedding", "_sample_judge"))
    group["sample_collapse_index"] = group[COLLAPSE_FIELDS].mean(axis=1)
    group = group.merge(weighted_group, on="group", how="left")
    group = group.rename(columns={
        "n_judged_x": "n_judged_sample",
        "mean_pairwise_cosine": "embedding_mean_pairwise_cosine",
    })
    # Restore short aliases used by plotting/reporting.
    group["mean_pairwise_cosine"] = group["embedding_mean_pairwise_cosine"]
    group = group.sort_values("weighted_collapse_index", ascending=False)
    group.to_csv(final_dir / "final_group_summary.csv", index=False)

    model = emb_model.merge(judge_model, on="model_family", how="left")
    model["sample_collapse_index"] = model[COLLAPSE_FIELDS].mean(axis=1)
    model = model.merge(weighted_model, on="model_family", how="left")
    model = model.rename(columns={
        "mean_pairwise_cosine": "embedding_mean_pairwise_cosine",
        "n_judged_x": "n_judged_sample",
    })
    model = model.sort_values("weighted_collapse_index", ascending=False)
    model.to_csv(final_dir / "final_model_summary.csv", index=False)

    cluster = emb_cluster.merge(judge_cluster, on="cluster_id", how="left", suffixes=("_embedding", "_judge"))
    cluster = cluster.merge(cluster_labels, on="cluster_id", how="left", suffixes=("", "_label"))
    cluster["collapse_index"] = cluster[COLLAPSE_FIELDS].mean(axis=1)
    cluster = cluster.sort_values(["n_posts", "collapse_index"], ascending=False)
    cluster.to_csv(final_dir / "final_cluster_summary.csv", index=False)

    # Overall estimates.
    weighted_overall = {}
    for col in metric_cols:
        vals = cell_join[col].astype(float)
        weights = cell_join["n_full_nonseed_cell"].astype(float)
        mask = vals.notna() & weights.notna() & (weights > 0)
        weighted_overall[col.replace("weighted_", "")] = float(np.average(vals[mask], weights=weights[mask]))
    weighted_overall["collapse_index"] = float(np.mean([weighted_overall[m] for m in COLLAPSE_FIELDS]))
    weighted_overall["n_full_nonseed_posts_weighted"] = int(cell_join.dropna(subset=["weighted_semantic_repetition"])["n_full_nonseed_cell"].sum())
    weighted_overall["n_judged"] = int(judge_results.shape[0])
    (final_dir / "final_weighted_overall_judge_estimates.json").write_text(json.dumps(weighted_overall, indent=2))

    # Final PNGs.
    plot_barh(group, "group", "weighted_collapse_index", final_dir / "fig_final_group_collapse_index.png", "Cell-weighted collapse index by group", "Collapse index (mean of repetition/convergence/groupthink/template)", "#e15759")
    plot_group_scatter(group, final_dir / "fig_final_embedding_vs_judge_collapse.png")
    plot_barh(model.head(12), "model_family", "weighted_collapse_index", final_dir / "fig_final_model_collapse_index.png", "Cell-weighted collapse index by model family", "Collapse index", "#f28e2b")
    plot_cluster_scatter(cluster, final_dir / "fig_final_cluster_size_vs_collapse.png")
    plot_metric_heatmap(group, final_dir / "fig_final_group_judge_metric_heatmap.png")

    inventory = artifact_inventory(root, final_dir)
    inventory.to_csv(final_dir / "artifact_inventory.csv", index=False)
    total_png = len(list(root.rglob("*.png")))

    # Helpful top tables.
    group_display = group[[
        "group", "n_runs", "n_posts", "embedding_mean_pairwise_cosine", "dominant_cluster_share",
        "n_judged_sample", "sample_collapse_index", "weighted_collapse_index",
        "weighted_semantic_repetition", "weighted_narrative_convergence", "weighted_groupthink", "weighted_template_rigidity",
    ]].copy()
    model_display = model[[
        "model_family", "n_runs", "n_posts", "embedding_mean_pairwise_cosine", "n_judged_sample",
        "sample_collapse_index", "weighted_collapse_index",
    ]].copy()
    cluster_display = cluster[[
        "cluster_id", "short_label", "n_posts", "n_judged", "collapse_index", "collapse_pattern", "top_group", "top_model", "top_condition",
    ]].head(15).copy()

    total_rows = len(index)
    unique_record_ids = index["record_id"].nunique()
    duplicate_rows = total_rows - unique_record_ids
    seed_rows = int(is_true(index["is_seed"]).sum())
    nonseed_rows = total_rows - seed_rows
    total_runs = index["run_path"].nunique()
    source_counts = index.groupby("dataset_source").size().reset_index(name="post_rows")
    group_counts = index.groupby("group").agg(post_rows=("record_id", "count"), runs=("run_path", "nunique")).reset_index().sort_values("post_rows", ascending=False)

    top_group = group_display.iloc[0]
    lowest_group = group_display.sort_values("weighted_collapse_index").iloc[0]
    top_coherence = group.sort_values("embedding_mean_pairwise_cosine", ascending=False).iloc[0]

    report = f"""# Moltbook Archive 2026 + Canonical Gemini — Final Aggregate Report\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n## Executive summary\n\nThis analysis combines the targeted lightweight mirror of `Ayushnangia/moltbook-archive-2026` with all canonical `gemini-flash-lite` runs from `agokrani/moltbook-entropy-collapse-canonical-48`. The corpus contains **{total_rows:,} post rows** across **{total_runs:,} non-empty runs**, with **{nonseed_rows:,} nonseed/agent rows** and **{seed_rows:,} seed/system rows**. Embeddings were computed with OpenRouter `{np.load(root / 'embeddings' / 'qwen-qwen3-embedding-8b.npz')['embedding_model'][0] if (root / 'embeddings' / 'qwen-qwen3-embedding-8b.npz').exists() else 'qwen/qwen3-embedding-8b'}` and clustered globally into 48 clusters.\n\nKey findings:\n\n- The full embedding corpus shows highest within-run semantic coherence for **{top_coherence['group']}** (`{top_coherence['embedding_mean_pairwise_cosine']:.3f}` mean pairwise cosine).\n- The cell-weighted LLM judge estimate shows strongest collapse for **{top_group['group']}** (`{top_group['weighted_collapse_index']:.3f}` collapse index).\n- The lowest cell-weighted collapse estimate is **{lowest_group['group']}** (`{lowest_group['weighted_collapse_index']:.3f}`), but frontier/mixed-model has a small judged sample because that slice is small.\n- Overall cell-weighted LLM estimates are high on narrative convergence (`{weighted_overall['narrative_convergence']:.3f}`), semantic repetition (`{weighted_overall['semantic_repetition']:.3f}`), and groupthink (`{weighted_overall['groupthink']:.3f}`), while novelty (`{weighted_overall['novelty']:.3f}`) and evidence grounding (`{weighted_overall['evidence_grounding']:.3f}`) are low.\n- All 48 embedding clusters were labeled with an LLM; prominent repeated patterns include micro-ritual epistemic protocols, recursive meta-discourse, technical protocol standardization, null/punctuation collapse, and existential/simulation-loop frames.\n\n## Scope and provenance\n\nThe archive source was intentionally targeted: only lightweight run artifacts (`posts.jsonl`, `comments.jsonl`, `agents.jsonl`, `metadata.json`, top-level metadata files) were fetched, not full logs/databases/plots. This follows the user instruction to be targeted rather than downloading a heavy full snapshot.\n\n### Source row counts\n\n{md_table(source_counts)}\n\n### Group row counts\n\n{md_table(group_counts)}\n\n## Methods\n\n1. **Indexing:** normalized archive + canonical Gemini posts into `combined_posts_index.jsonl/csv`. Duplicate `record_id`s exist for 8 rows; row order is preserved and later judge work uses a unique row UID.\n2. **Embeddings:** cached OpenRouter `qwen/qwen3-embedding-8b` vectors in SQLite and exported a `(85030, 4096)` NPZ.\n3. **Global embedding analysis:** normalized embeddings, computed 50 SVD components, clustered with MiniBatchKMeans (`k=48`), and sampled 25,000 rows for UMAP.\n4. **LLM judge:** drew a 1,791-row nonseed stratified sample across `group × model_family × condition × scale × time_bin`, with extra coverage for all 48 clusters. Judge prompts blinded source/group/model/condition labels and included local previous-post context plus same-cluster examples.\n5. **Cluster labeling:** all 48 global clusters were summarized by the judge model using representative posts plus aggregate statistics.\n\n## Final group summary\n\n`sample_collapse_index` is the raw mean over sampled posts. `weighted_collapse_index` weights cell-level judge means by the full nonseed post count of each cell, so it is the better group-level estimate. Collapse index = mean of semantic repetition, narrative convergence, groupthink, and template rigidity.\n\n{md_table(group_display, decimals=3)}\n\n## Final model summary\n\n{md_table(model_display, max_rows=20, decimals=3)}\n\n## Top clusters by size\n\n{md_table(cluster_display, max_rows=15, decimals=3)}\n\n## Final outputs\n\nPrimary reports:\n\n- `FINAL_REPORT.md` — this report.\n- `embedding_report/EMBEDDING_REPORT.md` — full embedding/clustering report.\n- `llm_judge/LLM_JUDGE_REPORT.md` — post-level LLM judge report.\n- `llm_judge/CLUSTER_LABELS.md` — qualitative labels/summaries for all 48 global clusters.\n\nFinal aggregate CSVs:\n\n- `final_report/final_group_summary.csv`\n- `final_report/final_model_summary.csv`\n- `final_report/final_cluster_summary.csv`\n- `final_report/final_cell_weighting_inputs.csv`\n- `final_report/final_weighted_overall_judge_estimates.json`\n- `final_report/artifact_inventory.csv`\n\nFinal aggregate PNGs:\n\n- `final_report/fig_final_group_collapse_index.png`\n- `final_report/fig_final_embedding_vs_judge_collapse.png`\n- `final_report/fig_final_model_collapse_index.png`\n- `final_report/fig_final_cluster_size_vs_collapse.png`\n- `final_report/fig_final_group_judge_metric_heatmap.png`\n\nNon-heatmap individual-analysis outputs:\n\n- `individual_analysis/INDIVIDUAL_MODEL_CONDITION_ANALYSIS.md`\n- `individual_analysis/fig_all_models_collapse_lollipop.png`\n- `individual_analysis/fig_conditions_collapse_lollipop.png`\n- `individual_analysis/fig_model_condition_collapse_facets.png`\n- `individual_analysis/fig_group_condition_collapse_bars.png`\n- `individual_analysis/models/` — one condition-profile graph per generation model.\n- `individual_analysis/conditions/` — one model/group ranking graph per condition.\n\nEarlier generated PNGs remain in `embedding_report/` and `llm_judge/`; current total is {total_png} PNG diagrams across the analysis directory.\n\n## Caveats\n\n- The archive mirror is targeted/lightweight by design; it is not a full snapshot of every heavy artifact.\n- LLM judge metrics are sampled estimates, not exhaustive judgments for all 85,030 rows. The final weighted estimates improve population alignment by weighting sampled cell means by full nonseed cell counts.\n- Frontier/mixed-model has only 807 post rows and 16 judged sample rows; interpret group-level judge scores cautiously.\n- LLM cluster labels are qualitative summaries and may compress heterogeneous clusters into a single label.\n- Source-citation quality scores should be interpreted carefully because many sampled posts did not contain source/citation behavior, and the rubric assigns low citation quality when no citations appear.\n\n## Artifact inventory\n\nSee `final_report/artifact_inventory.csv` for file sizes and paths. Current final inventory contains {len(inventory):,} files.\n"""
    (root / "FINAL_REPORT.md").write_text(report)
    (final_dir / "FINAL_REPORT.md").write_text(report)
    print(f"Wrote final report -> {root / 'FINAL_REPORT.md'}")
    print(f"Final report files -> {final_dir}")


if __name__ == "__main__":
    main()
