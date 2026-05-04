#!/usr/bin/env python3
"""Build embedding-only final report for archive-2026 main groups.

Main package intentionally excludes source-citation/site-citation, frontier/mixed
roster runs, canonical-48 comparison runs, and all LLM-as-a-judge outputs.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
MAIN_GROUPS = ["base-model", "entropy-collapse", "obsession"]
EXCLUDED_GROUPS = ["source-citation", "frontier/mixed-model", "canonical-48", "canonical-gemini-flash-lite"]


def is_true(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def md_table(df: pd.DataFrame, max_rows: int = 20, decimals: int = 3) -> str:
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else f"{x:.{decimals}f}")
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"] * len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in d.columns) + " |")
    return "\n".join(lines)


def plot_barh(df: pd.DataFrame, label: str, value: str, path: Path, title: str, xlabel: str, color: str) -> None:
    d = df.sort_values(value).copy()
    fig, ax = plt.subplots(figsize=(8, max(3.5, 0.45 * len(d))))
    ax.barh(d[label].astype(str), d[value], color=color)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def artifact_inventory(root: Path, final_dir: Path) -> pd.DataFrame:
    dirs = [root, root / "embedding_report", root / "paper_analysis", final_dir, root / "embeddings"]
    rows = []
    seen = set()
    for d in dirs:
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
    bad = sorted(set(index["group"]) - set(MAIN_GROUPS))
    if bad:
        raise SystemExit(f"Excluded groups leaked into main index: {bad}")

    emb_group = pd.read_csv(root / "embedding_report" / "group_embedding_summary.csv")
    emb_model = pd.read_csv(root / "embedding_report" / "model_embedding_summary.csv")
    emb_cluster = pd.read_csv(root / "embedding_report" / "cluster_summary.csv")
    emb_run = pd.read_csv(root / "embedding_report" / "run_embedding_summary.csv")

    total_rows = len(index)
    seed_rows = int(is_true(index["is_seed"]).sum())
    nonseed_rows = total_rows - seed_rows
    total_runs = index["run_path"].nunique()
    unique_ids = index["record_id"].nunique()
    duplicate_rows = total_rows - unique_ids
    cluster_n = int(emb_cluster["cluster_id"].nunique())
    npz_path = root / "embeddings" / "qwen-qwen3-embedding-8b.npz"
    npz_shape = tuple(np.load(npz_path)["embeddings"].shape) if npz_path.exists() else (total_rows, 4096)

    group_counts = index.groupby("group").agg(post_rows=("record_id", "count"), runs=("run_path", "nunique")).reset_index().sort_values("post_rows", ascending=False)
    model_counts = index.groupby("model_family").agg(post_rows=("record_id", "count"), runs=("run_path", "nunique")).reset_index().sort_values("post_rows", ascending=False)

    final_group = emb_group.sort_values("mean_pairwise_cosine", ascending=False)
    final_model = emb_model.sort_values("mean_pairwise_cosine", ascending=False)
    final_cluster = emb_cluster.sort_values("n_posts", ascending=False)

    final_group.to_csv(final_dir / "final_group_embedding_summary.csv", index=False)
    final_model.to_csv(final_dir / "final_model_embedding_summary.csv", index=False)
    final_cluster.to_csv(final_dir / "final_cluster_embedding_summary.csv", index=False)
    emb_run.to_csv(final_dir / "final_run_embedding_summary.csv", index=False)

    plot_barh(final_group, "group", "mean_pairwise_cosine", final_dir / "fig_final_group_embedding_coherence.png", "Within-run embedding coherence by group", "Mean pairwise cosine", "#4e79a7")
    plot_barh(final_group, "group", "dominant_cluster_share", final_dir / "fig_final_group_dominant_cluster_share.png", "Dominant-cluster share by group", "Mean dominant-cluster share", "#e15759")
    plot_barh(final_model.head(20), "model_family", "mean_pairwise_cosine", final_dir / "fig_final_model_embedding_coherence.png", "Within-run embedding coherence by model", "Mean pairwise cosine", "#f28e2b")
    plot_barh(final_cluster.head(20), "cluster_id", "n_posts", final_dir / "fig_final_cluster_sizes.png", "Top global embedding clusters by size", "Posts", "#59a14f")

    inventory = artifact_inventory(root, final_dir)
    inventory.to_csv(final_dir / "artifact_inventory.csv", index=False)

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "embedding_model": "qwen/qwen3-embedding-8b",
        "llm_as_judge_used": False,
        "llm_as_judge_exclusion_reason": "Excluded because judge/context can leak group labels; final package is embedding-only.",
        "included_groups": MAIN_GROUPS,
        "excluded_groups": EXCLUDED_GROUPS,
        "post_rows": total_rows,
        "nonseed_rows": nonseed_rows,
        "seed_rows": seed_rows,
        "runs": int(total_runs),
        "duplicate_record_id_rows": int(duplicate_rows),
        "embedding_npz_shape": npz_shape,
        "global_clusters": cluster_n,
    }
    (final_dir / "final_embedding_only_summary.json").write_text(json.dumps(summary, indent=2))

    top_group = final_group.iloc[0]
    report = f"""# Archive 2026 Main Groups — Embedding-Only Final Report\n\nGenerated: {summary['generated_at']}\n\n## Scope\n\nThis cleaned review package is **embedding-only** and includes only the main archive groups:\n\n- `base-model`\n- `entropy-collapse`\n- `obsession`\n\nExcluded by design:\n\n- `source-citation` / site-citation smoke runs\n- `frontier/mixed-model` roster/mixed runs\n- `canonical-48` and canonical Gemini comparison runs\n- all LLM-as-a-judge outputs\n\n## Why LLM-as-a-judge is excluded\n\nLLM-as-a-judge results are not used in this package. Earlier judge prompts/context could expose group/source cues through context metadata, so we removed those outputs rather than reporting potentially confounded judge scores.\n\n## Corpus\n\n- Post rows: **{total_rows:,}**\n- Nonseed/agent rows: **{nonseed_rows:,}**\n- Seed/system rows: **{seed_rows:,}**\n- Non-empty runs: **{total_runs:,}**\n- Embedding NPZ shape: **{npz_shape}**\n- Global embedding clusters: **{cluster_n}**\n\n## Key embedding result\n\nThe highest within-run semantic coherence is **{top_group['group']}** with mean pairwise cosine **{top_group['mean_pairwise_cosine']:.3f}**.\n\n## Group counts\n\n{md_table(group_counts)}\n\n## Model counts\n\n{md_table(model_counts, max_rows=20)}\n\n## Group embedding summary\n\n{md_table(final_group)}\n\n## Model embedding summary\n\n{md_table(final_model, max_rows=20)}\n\n## Top clusters\n\n{md_table(final_cluster.head(20), max_rows=20)}\n\n## Main outputs\n\n- `FINAL_REPORT.md` — this report.\n- `embedding_report/EMBEDDING_REPORT.md` — full embedding/clustering report.\n- `paper_analysis/PAPER_STYLE_ANALYSIS.md` — paper-style embedding-only analysis with Vendi/MDS figures.\n- `final_report/final_group_embedding_summary.csv`\n- `final_report/final_model_embedding_summary.csv`\n- `final_report/final_cluster_embedding_summary.csv`\n- `final_report/final_run_embedding_summary.csv`\n- `final_report/final_embedding_only_summary.json`\n\n## Final PNGs\n\n- `final_report/fig_final_group_embedding_coherence.png`\n- `final_report/fig_final_group_dominant_cluster_share.png`\n- `final_report/fig_final_model_embedding_coherence.png`\n- `final_report/fig_final_cluster_sizes.png`\n\n## Reproducibility\n\nRegenerate the cleaned index and analysis with:\n\n```bash\npython3 scripts/archive-2026-combined-analysis.py index\npython3 scripts/archive-2026-combined-analysis.py embed --model qwen/qwen3-embedding-8b --export-npz\npython3 scripts/archive-2026-embedding-report.py --clusters 48 --umap-sample 25000 --svd-components 50\npython3 scripts/archive-2026-paper-analysis.py --max-bin-n 400 --mds-sample 4000\npython3 scripts/archive-2026-final-report.py\n```\n"""
    (root / "FINAL_REPORT.md").write_text(report)
    (final_dir / "FINAL_REPORT.md").write_text(report)
    print(f"Wrote embedding-only final report -> {root / 'FINAL_REPORT.md'}")


if __name__ == "__main__":
    main()
