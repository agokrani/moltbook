#!/usr/bin/env python3
"""Regenerate the Ayush reanalysis final/checkpoint report from small CSV artifacts."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")

FAMILY_NAMES = {
    "single_model_final": "Single-model final runs",
    "base_model_as_tool": "Base model as tool",
    "mixed_model_roster": "Mixed-model roster",
    "obsession_prompting": "Obsession prompting",
}
SCHEME_NAMES = {
    "fixed_15m": "fixed 15m",
    "normalized_quartile": "normalized quartiles",
}


def fmt(x: Any, digits: int = 4) -> str:
    if pd.isna(x):
        return ""
    if isinstance(x, (float, int)):
        if abs(float(x)) >= 1000:
            return f"{float(x):,.0f}"
        return f"{float(x):.{digits}g}"
    return str(x)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(fmt(row[c]) for c in cols) + " |")
    return "\n".join(lines)


def family_scheme_order(df: pd.DataFrame) -> pd.DataFrame:
    order = {
        ("single_model_final", "fixed_15m"): 0,
        ("single_model_final", "normalized_quartile"): 1,
        ("base_model_as_tool", "fixed_15m"): 2,
        ("base_model_as_tool", "normalized_quartile"): 3,
        ("mixed_model_roster", "fixed_15m"): 4,
        ("mixed_model_roster", "normalized_quartile"): 5,
        ("obsession_prompting", "normalized_quartile"): 6,
    }
    out = df.copy()
    out["_order"] = out.apply(lambda r: order.get((r.get("internal_family_label"), r.get("scheme")), 999), axis=1)
    return out.sort_values("_order").drop(columns=["_order"])


def compact_summary(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    rows = family_scheme_order(df)
    out = pd.DataFrame({
        "family": rows["internal_family_label"].map(FAMILY_NAMES).fillna(rows["internal_family_label"]),
        "scheme": rows["scheme"].map(SCHEME_NAMES).fillna(rows["scheme"]),
        "n_runs": rows["n_runs"],
    })
    for label, col in metrics:
        out[label] = rows[col]
    return out


def manifest_table(root: Path) -> pd.DataFrame:
    manifest = pd.read_csv(root / "data_manifest.csv")
    inc = manifest[manifest["include_in_main"] == True]
    out = inc.groupby("internal_family_label", as_index=False).agg(
        runs=("run_uid", "nunique"),
        non_seed_posts=("n_posts_nonseed", "sum"),
    )
    out["family"] = out["internal_family_label"].map(FAMILY_NAMES).fillna(out["internal_family_label"])
    return out[["family", "runs", "non_seed_posts"]].sort_values("runs", ascending=False)


def exclusion_table(root: Path) -> pd.DataFrame:
    manifest = pd.read_csv(root / "data_manifest.csv")
    exc = manifest[manifest["include_in_main"] != True]
    return exc.groupby("exclusion_reason", as_index=False).size().rename(columns={"size": "runs"}).sort_values("runs", ascending=False)


def regenerate_artifact_inventory(root: Path) -> None:
    exclude_parts = {"llm_judge", "blind_llm_judge"}
    exclude_names = {
        "post_index.csv",
        "post_index.jsonl",
        "combined_posts_index.csv",
        "combined_posts_index.jsonl",
        "artifact_inventory.csv",
    }
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in exclude_parts for part in rel.parts):
            continue
        if path.name in exclude_names:
            continue
        if path.suffix in {".sqlite", ".npz"}:
            continue
        rows.append({"path": str(rel), "bytes": path.stat().st_size, "kilobytes": round(path.stat().st_size / 1024, 1)})
    out = root / "ayush_reanalysis" / "artifact_inventory.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["path", "bytes", "kilobytes"], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def build_report(root: Path) -> str:
    generated = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    det = pd.read_csv(root / "combined_report" / "deterministic_summary_by_family.csv")
    emb = pd.read_csv(root / "combined_report" / "embedding_summary_by_family.csv")
    coverage = pd.read_json(root / "ayush_reanalysis" / "embedding_cache_coverage.json", typ="series")

    det_table = compact_summary(det, [
        ("mean Δ gzip", "delta_compression_gzip_mean"),
        ("mean Δ Distinct-5", "delta_distinct_5_mean"),
        ("mean Δ Simpson effective 5-gram", "delta_simpson_5gram_effective_mean"),
    ])
    emb_table = compact_summary(emb, [
        ("mean Δ Vendi", "delta_vendi_score_mean"),
        ("mean Δ pairwise cosine", "delta_mean_pairwise_cosine_mean"),
        ("mean Δ semantic radius", "delta_semantic_radius_mean"),
    ])

    judge_summary = root / "combined_report" / "llm_judge_summary_by_family.csv"
    if judge_summary.exists():
        judge = pd.read_csv(judge_summary)
        judge_table = compact_summary(judge, [
            ("mean Δ collapse index", "delta_collapse_index_mean"),
            ("mean Δ novelty", "delta_novelty_mean"),
            ("mean Δ semantic repetition", "delta_semantic_repetition_mean"),
            ("mean Δ specificity", "delta_specificity_mean"),
        ])
        judge_section = (
            "## Blinded LLM-as-judge findings\n\n"
            "The judge outputs below are metadata-blind at prompt time. The model received post text plus anonymized previous/semantic-neighbor posts only; run/group/model/condition/path/source metadata was joined locally after scoring.\n\n"
            + markdown_table(judge_table)
            + "\n\nFull judge summaries: `combined_report/LLM_JUDGE_SUMMARY.md`, `combined_report/llm_judge_summary_by_family.csv`.\n"
        )
        status = "Full blinded LLM-as-judge scoring: **complete and aggregated**."
    else:
        judge_section = (
            "## Blinded LLM-as-judge findings\n\n"
            "Full all-post blinded LLM-as-judge scoring is still running and is not included in this checkpoint yet. After it finishes, run `python3 scripts/ayush-blind-llm-judge.py aggregate` and regenerate this report.\n"
        )
        status = "Full blinded LLM-as-judge scoring: **running; not yet included**."

    return f"""# Ayush Reanalysis — Final-Run, Mixed-Roster, Base-Tool, and Obsession Experiments

Generated: {generated}

This report supersedes the older archive-only embedding package. The current scope follows `ANALYSIS_PLAN_FOR_AYUSH.md` and excludes old archive `entropy-collapse`, source/site-citation runs, and base-model paths containing `ignore`.

## Status

- Deterministic/run-level analyses: **complete**.
- Qwen embedding/Vendi analyses: **complete**.
- Blinded LLM-as-judge context generation and audit: **complete**.
- {status}

## Included corpus

{markdown_table(manifest_table(root))}

## Exclusions

{markdown_table(exclusion_table(root))}

## Main deterministic findings

All summaries are run-level first: metrics are computed within each run/time bin, converted to within-run last-bin minus first-bin deltas, then summarized over runs.

{markdown_table(det_table)}

The canonical single-model final set reproduces the expected entropy-collapse direction: gzip compression ratio, Distinct-5, cumulative Distinct-5, and Simpson-style effective 5-gram diversity all decline strongly over time.

## Main embedding findings

Embedding model: `{coverage.get('embedding_model', 'qwen/qwen3-embedding-8b')}`. Coverage: {int(coverage.get('nonseed_posts', 0)):,} / {int(coverage.get('nonseed_posts', 0)):,} included non-seed posts; missing embeddings: {int(coverage.get('missing_nonseed_embeddings', 0)):,}.

{markdown_table(emb_table)}

Single-model final and base-model-as-tool runs show decreasing semantic diversity / increasing semantic concentration by embedding metrics. Mixed-model roster has only three runs, so its positive Vendi direction should be treated as exploratory.

{judge_section}

## Figures

- `ayush_reanalysis/figures/manifest_included_corpus.png`
- `ayush_reanalysis/figures/delta_gzip_compression_by_family.png`
- `ayush_reanalysis/figures/delta_distinct5_by_family.png`
- `ayush_reanalysis/figures/delta_vendi_by_family.png`
- `ayush_reanalysis/figures/delta_pairwise_cosine_by_family.png`

PDF versions are stored beside each PNG.

## Key artifacts

- Plan: `ANALYSIS_PLAN_FOR_AYUSH.md`
- Manifest: `data_manifest.csv`, `data_manifest_summary.md`
- Main deterministic CSVs: `ayush_reanalysis/deterministic_timebin_metrics.csv`, `ayush_reanalysis/deterministic_run_deltas.csv`
- Embedding CSVs: `ayush_reanalysis/embedding_run_timebin_metrics.csv`, `ayush_reanalysis/embedding_run_deltas.csv`
- Per-family outputs: `per_family_reports/<family>/...`
- Combined summaries: `combined_report/DETERMINISTIC_METRICS_SUMMARY.md`, `combined_report/EMBEDDING_SUMMARY.md`
- Artifact inventory: `ayush_reanalysis/artifact_inventory.csv`
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    args = parser.parse_args()
    root = Path(args.out_dir)
    report = build_report(root)
    (root / "FINAL_REPORT.md").write_text(report)
    regenerate_artifact_inventory(root)
    print(f"wrote {root / 'FINAL_REPORT.md'}")
    print(f"wrote {root / 'ayush_reanalysis' / 'artifact_inventory.csv'}")


if __name__ == "__main__":
    main()
