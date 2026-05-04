#!/usr/bin/env python3
"""LLM judge and cluster labeling for archive-2026 + full canonical-48 corpus.

Uses the combined index and embedding_report cluster assignments already produced
under analysis/archive-2026-plus-canonical-gemini/. All network outputs are
cached in local SQLite and can be resumed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    tqdm = None

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
DEFAULT_JUDGE_MODEL = "google/gemini-3.1-flash-lite-preview"
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
RUBRIC_VERSION = "archive-entropy-collapse-v1"
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
LABEL_ORDER = ["novel_contribution", "mild_rephrase", "frame_convergence", "template_repetition", "source_grounded", "off_topic"]
CLAIM_ORDER = ["no_checkable_claim", "specific_claim_supported", "specific_claim_unsupported", "conspiracy_or_speculative", "debunking_or_correction"]
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech", "unknown"]


def progress(x, **kwargs):
    return tqdm(x, **kwargs) if tqdm else x


def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


def load_env_key() -> str:
    if load_dotenv:
        load_dotenv(Path(".env"), override=False)
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise SystemExit("OPENROUTER_API_KEY missing; set env or .env. The key is never printed.")
    return key


def coerce_json(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if "```" in text:
        for part in text.split("```"):
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break
    if not text.startswith("{"):
        m = re.search(r"\{.*\}", text, flags=re.S)
        if m:
            text = m.group(0)
    return json.loads(text)


def load_records(out_dir: Path) -> pd.DataFrame:
    index_jsonl = out_dir / "combined_posts_index.jsonl"
    cluster_csv = out_dir / "embedding_report" / "embedding_analysis_data.csv"
    rows = []
    with index_jsonl.open() as f:
        for i, line in enumerate(f):
            if not line.strip():
                continue
            r = json.loads(line)
            r["row_index"] = i
            # Stable unique key per row. record_id alone has 8 duplicate rows in this corpus.
            r["row_uid"] = sha1_text(f"{i}:{r.get('record_id','')}:{r.get('run_path','')}:{r.get('post_id','')}")
            rows.append(r)
    df = pd.DataFrame(rows)
    if cluster_csv.exists():
        c = pd.read_csv(cluster_csv)
        needed = ["cluster_id", "cluster_label", "svd_1", "svd_2"]
        for col in needed:
            if col not in c.columns:
                raise SystemExit(f"Missing {col} in {cluster_csv}")
        if len(c) != len(df):
            raise SystemExit(f"Cluster rows {len(c)} != index rows {len(df)}")
        for col in needed:
            df[col] = c[col].to_numpy()
    else:
        df["cluster_id"] = -1
        df["cluster_label"] = "cluster_-1"
        df["svd_1"] = 0.0
        df["svd_2"] = 0.0
    df["is_seed"] = df["is_seed"].astype(bool)
    df["text_len"] = df["text"].fillna("").astype(str).str.len()
    return df


def clean_snippet(value: str, n: int) -> str:
    value = (value or "").replace("\x00", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value[:n]


def build_context_rows(df: pd.DataFrame, chosen: pd.DataFrame, rng: random.Random) -> list[dict[str, Any]]:
    # Previous posts are local run context; similar examples are from the global cluster.
    run_groups = {run_path: sub.sort_values(["created_at", "post_id", "row_index"]) for run_path, sub in df.groupby("run_path", dropna=False)}
    by_cluster = {int(cid): sub for cid, sub in df.groupby("cluster_id", dropna=False)}
    sample_rows: list[dict[str, Any]] = []
    for _, rec in chosen.sort_values(["group", "model_family", "condition", "scale", "time_bin", "row_index"]).iterrows():
        run_df = run_groups.get(rec["run_path"])
        previous = []
        if run_df is not None:
            positions = run_df.index[run_df["row_uid"] == rec["row_uid"]].tolist()
            if positions:
                loc = run_df.index.get_loc(positions[0])
                prev = run_df.iloc[max(0, loc - 5):loc]
                for _, p in prev.iterrows():
                    previous.append({
                        "minutes_elapsed": round(float(p.get("minutes_elapsed", 0.0)), 2),
                        "author": p.get("author_name", ""),
                        "title": clean_snippet(str(p.get("title", "")), 160),
                        "content": clean_snippet(str(p.get("content", "")), 420),
                    })
        similar = []
        csub = by_cluster.get(int(rec.get("cluster_id", -1)))
        if csub is not None:
            candidates = csub[csub["row_uid"] != rec["row_uid"]]
            if len(candidates) > 0:
                take = candidates.sample(min(3, len(candidates)), random_state=rng.randint(0, 10**9))
                for _, p in take.iterrows():
                    similar.append({
                        "cluster_id": int(p.get("cluster_id", -1)),
                        "group": p.get("group", ""),
                        "condition": p.get("condition", ""),
                        "title": clean_snippet(str(p.get("title", "")), 160),
                        "content": clean_snippet(str(p.get("content", "")), 420),
                    })
        record = rec.to_dict()
        sample_rows.append({
            "row_uid": rec["row_uid"],
            "record": record,
            "previous_run_context": previous,
            "same_cluster_context": similar,
        })
    return sample_rows


def cmd_sample_judge(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    judge_dir = out_dir / "llm_judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    df = load_records(out_dir)
    if not args.include_seeds:
        df = df[~df["is_seed"]]
    df = df[df["text_len"] > 0].copy()
    rng = random.Random(args.seed)

    chosen_idx: set[int] = set()
    group_cols = ["group", "model_family", "condition", "scale", "time_bin"]
    for _, sub in df.groupby(group_cols, dropna=False):
        k = min(args.posts_per_cell, len(sub))
        if k <= 0:
            continue
        for i in sub.sample(k, random_state=rng.randint(0, 10**9)).index:
            chosen_idx.add(int(i))

    # Guarantee cluster coverage even for small/special clusters.
    for _, sub in df.groupby("cluster_id", dropna=False):
        k = min(args.min_per_cluster, len(sub))
        have = [i for i in sub.index if int(i) in chosen_idx]
        if len(have) >= k:
            continue
        remaining = sub.drop(index=have, errors="ignore")
        add = min(k - len(have), len(remaining))
        if add > 0:
            for i in remaining.sample(add, random_state=rng.randint(0, 10**9)).index:
                chosen_idx.add(int(i))

    chosen = df.loc[sorted(chosen_idx)].copy()
    if args.max_rows and len(chosen) > args.max_rows:
        chosen = chosen.sample(args.max_rows, random_state=args.seed).sort_index()
    sample_rows = build_context_rows(df, chosen, rng)
    out_path = Path(args.sample) if args.sample else judge_dir / "judge_sample.jsonl"
    with out_path.open("w") as f:
        for row in sample_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rubric_version": RUBRIC_VERSION,
        "rows": len(sample_rows),
        "posts_per_cell": args.posts_per_cell,
        "min_per_cluster": args.min_per_cluster,
        "max_rows": args.max_rows,
        "seed": args.seed,
        "group_cols": group_cols,
        "include_seeds": args.include_seeds,
    }
    out_path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote judge sample: {len(sample_rows):,} rows -> {out_path}")


def ensure_judge_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS judgments (
        row_uid TEXT NOT NULL,
        record_id TEXT NOT NULL,
        judge_model TEXT NOT NULL,
        rubric_version TEXT NOT NULL,
        judgment_json TEXT NOT NULL,
        prompt_sha1 TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(row_uid, judge_model, rubric_version)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS cluster_labels (
        cluster_id INTEGER NOT NULL,
        judge_model TEXT NOT NULL,
        rubric_version TEXT NOT NULL,
        label_json TEXT NOT NULL,
        prompt_sha1 TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(cluster_id, judge_model, rubric_version)
    )""")
    conn.commit()
    return conn


def cached_judgment_uids(conn: sqlite3.Connection, model: str) -> set[str]:
    return {r[0] for r in conn.execute("SELECT row_uid FROM judgments WHERE judge_model=? AND rubric_version=?", (model, RUBRIC_VERSION))}


def judge_prompt(row: dict[str, Any]) -> str:
    r = row["record"]
    blinded = {
        "dataset_source": "hidden",
        "group": "hidden",
        "model_family": "hidden",
        "condition": "hidden",
        "scale": r.get("scale"),
        "time_bin": r.get("time_bin"),
        "minutes_elapsed": r.get("minutes_elapsed"),
        "global_cluster_id": int(r.get("cluster_id", -1)),
    }
    return f"""You are judging AI-agent discourse from a Reddit-like multi-agent social simulation.

Your task is not to judge style. Identify entropy-collapse behavior: semantic repetition, narrative convergence, groupthink, template-like posting, and whether claims are grounded.

Score each integer field from 1 to 5:
- novelty: 1=no new substantive contribution; 5=clearly new idea/evidence/frame.
- semantic_repetition: 1=not repetitive; 5=strongly repeats nearby/similar context.
- narrative_convergence: 1=independent frame; 5=tightly follows a dominant shared frame.
- groupthink: 1=independent/critical; 5=uncritically reinforces consensus.
- specificity: 1=vague/generic; 5=concrete claims/details/examples.
- evidence_grounding: 1=no evidence; 5=clear source/reasoning/evidence.
- epistemic_caution: 1=overconfident; 5=careful uncertainty/limitations.
- template_rigidity: 1=organic; 5=formulaic/checklist/receipt/template.
- source_citation_quality: 1=no or bad citation behavior; 5=specific useful citations/sources. Use 1 if no citations are needed and none appear.

collapse_label must be one of: {', '.join(LABEL_ORDER)}.
claim_behavior must be one of: {', '.join(CLAIM_ORDER)}.

Return JSON only with keys: {', '.join(SCORE_FIELDS)}, collapse_label, claim_behavior, dominant_frame, rationale.
Keep rationale under 45 words.

Blinded metadata:
{json.dumps(blinded, ensure_ascii=False)}

Current post:
Title: {r.get('title','')}
Content:
{clean_snippet(str(r.get('content','')), 2400)}

Previous posts in the same run immediately before this post:
{json.dumps(row.get('previous_run_context', []), ensure_ascii=False, indent=2)}

Other posts from the same global embedding cluster:
{json.dumps(row.get('same_cluster_context', []), ensure_ascii=False, indent=2)}
"""


def normalize_judgment(j: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for f in SCORE_FIELDS:
        try:
            out[f] = max(1, min(5, int(round(float(j.get(f, 1))))))
        except Exception:
            out[f] = 1
    label = str(j.get("collapse_label", "mild_rephrase"))
    out["collapse_label"] = label if label in LABEL_ORDER else "mild_rephrase"
    claim = str(j.get("claim_behavior", "no_checkable_claim"))
    out["claim_behavior"] = claim if claim in CLAIM_ORDER else "no_checkable_claim"
    out["dominant_frame"] = clean_snippet(str(j.get("dominant_frame", "")), 160)
    out["rationale"] = clean_snippet(str(j.get("rationale", "")), 320)
    return out


def openrouter_json(prompt: str, model: str, key: str, max_tokens: int, retries: int, timeout: int) -> dict[str, Any]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last = None
    for attempt in range(retries):
        try:
            resp = requests.post(CHAT_ENDPOINT, headers=headers, json=payload, timeout=timeout)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"].get("content", "{}")
            return coerce_json(content)
        except Exception as e:
            last = e
            sleep = min(45, 2 ** attempt)
            print(f"request failed attempt={attempt+1}/{retries}: {e}; sleep {sleep}s")
            time.sleep(sleep)
    raise RuntimeError(last)


def store_judgment(conn: sqlite3.Connection, row: dict[str, Any], model: str, prompt: str, judgment: dict[str, Any]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO judgments VALUES (?,?,?,?,?,?,?)",
        (
            row["row_uid"],
            row["record"].get("record_id", ""),
            model,
            RUBRIC_VERSION,
            json.dumps(judgment, ensure_ascii=False),
            sha1_text(prompt),
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()


def cmd_judge(args: argparse.Namespace) -> None:
    key = load_env_key()
    sample_path = Path(args.sample) if args.sample else Path(args.out_dir) / "llm_judge" / "judge_sample.jsonl"
    rows = [json.loads(line) for line in sample_path.open() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    conn = ensure_judge_db(Path(args.out_dir) / "llm_judge" / "judge_cache.sqlite")
    cached = cached_judgment_uids(conn, args.model)
    todo = [r for r in rows if r["row_uid"] not in cached]
    print(f"Judge model={args.model}; sample_scope={len(rows):,}; cached={len(cached):,}; remaining={len(todo):,}; parallelism={args.parallelism}")

    def one(row: dict[str, Any]):
        p = judge_prompt(row)
        j = normalize_judgment(openrouter_json(p, args.model, key, args.max_tokens, args.retries, args.timeout))
        return row, p, j

    if args.parallelism <= 1:
        for row in progress(todo, desc="Judging", unit="post"):
            r, p, j = one(row)
            store_judgment(conn, r, args.model, p, j)
            if args.sleep:
                time.sleep(args.sleep)
    else:
        with ThreadPoolExecutor(max_workers=args.parallelism) as pool:
            futs = []
            for row in todo:
                futs.append(pool.submit(one, row))
                if args.sleep:
                    time.sleep(args.sleep)
            for fut in progress(as_completed(futs), total=len(futs), desc="Judging", unit="post"):
                r, p, j = fut.result()
                store_judgment(conn, r, args.model, p, j)
    print("Cached judgments now:", len(cached_judgment_uids(conn, args.model)))


def load_judgments(conn: sqlite3.Connection, model: str) -> pd.DataFrame:
    rows = []
    for row_uid, record_id, judge_model, rubric, jtxt, created_at in conn.execute(
        "SELECT row_uid, record_id, judge_model, rubric_version, judgment_json, created_at FROM judgments WHERE judge_model=? AND rubric_version=?",
        (model, RUBRIC_VERSION),
    ):
        j = json.loads(jtxt)
        j.update({"row_uid": row_uid, "record_id": record_id, "judge_model": judge_model, "rubric_version": rubric, "judged_at": created_at})
        rows.append(j)
    return pd.DataFrame(rows)


def plot_heatmap(pivot: pd.DataFrame, path: Path, title: str, label: str, vmin=None, vmax=None, cmap="magma") -> None:
    fig, ax = plt.subplots(figsize=(max(8, 0.7 * len(pivot.columns)), max(4, 0.45 * len(pivot.index))))
    im = ax.imshow(pivot.to_numpy(dtype=float), aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=35, ha="right")
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    ax.set_title(title)
    fig.colorbar(im, ax=ax, label=label)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def cmd_aggregate(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    judge_dir = out_dir / "llm_judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    sample_path = Path(args.sample) if args.sample else judge_dir / "judge_sample.jsonl"
    sample_rows = [json.loads(line) for line in sample_path.open() if line.strip()]
    srows = []
    for row in sample_rows:
        r = row["record"].copy()
        r.pop("content", None)
        r.pop("text", None)
        r["row_uid"] = row["row_uid"]
        srows.append(r)
    sample_df = pd.DataFrame(srows)
    conn = ensure_judge_db(judge_dir / "judge_cache.sqlite")
    judgments = load_judgments(conn, args.model)
    if judgments.empty:
        raise SystemExit("No judgments cached")
    df = sample_df.merge(judgments, on=["row_uid", "record_id"], how="inner")
    if df.empty:
        raise SystemExit("No sample rows matched judgments")
    df.to_json(judge_dir / "judge_results.jsonl", orient="records", lines=True, force_ascii=False)
    df.to_csv(judge_dir / "judge_results.csv", index=False)

    group_cols = ["group", "model_family", "condition", "scale"]
    agg = {f: ["mean", "std", "count"] for f in SCORE_FIELDS}
    summary = df.groupby(group_cols, dropna=False).agg(agg)
    summary.columns = ["_".join(c).strip("_") for c in summary.columns]
    summary = summary.reset_index()
    summary.to_csv(judge_dir / "judge_summary_by_cell.csv", index=False)

    for cols, name in [
        (["group"], "group"),
        (["model_family"], "model"),
        (["condition"], "condition"),
        (["cluster_id"], "cluster"),
    ]:
        s = df.groupby(cols, dropna=False).agg({**{f: "mean" for f in SCORE_FIELDS}, "row_uid": "count"}).rename(columns={"row_uid": "n_judged"}).reset_index()
        s.to_csv(judge_dir / f"judge_summary_by_{name}.csv", index=False)

    for label_col, order, fname in [
        ("collapse_label", LABEL_ORDER, "judge_collapse_label_shares.csv"),
        ("claim_behavior", CLAIM_ORDER, "judge_claim_behavior_shares.csv"),
    ]:
        counts = df.groupby(["group", label_col], dropna=False).size().reset_index(name="count")
        totals = df.groupby("group", dropna=False).size().reset_index(name="total")
        counts = counts.merge(totals, on="group")
        counts["proportion"] = counts["count"] / counts["total"]
        counts[label_col] = pd.Categorical(counts[label_col], categories=order, ordered=True)
        counts.sort_values(["group", label_col]).to_csv(judge_dir / fname, index=False)

    # PNGs.
    for metric in ["novelty", "semantic_repetition", "narrative_convergence", "groupthink", "template_rigidity", "evidence_grounding"]:
        pivot = df.pivot_table(index="group", columns="condition", values=metric, aggfunc="mean")
        cols = [c for c in CONDITION_ORDER if c in pivot.columns] + [c for c in pivot.columns if c not in CONDITION_ORDER]
        pivot = pivot.reindex(columns=cols)
        plot_heatmap(pivot, judge_dir / f"fig_judge_{metric}_group_condition.png", f"LLM judge {metric}: group × condition", "Mean score", vmin=1, vmax=5)

    top_clusters = pd.read_csv(judge_dir / "judge_summary_by_cluster.csv").sort_values("n_judged", ascending=False).head(30)
    fig, ax = plt.subplots(figsize=(9, 8))
    ax.barh([f"c{int(c):02d}" for c in top_clusters.sort_values("n_judged")["cluster_id"]], top_clusters.sort_values("n_judged")["semantic_repetition"], color="#e15759")
    ax.set_xlabel("Mean semantic repetition")
    ax.set_title("Judged semantic repetition in top sampled clusters")
    fig.tight_layout()
    fig.savefig(judge_dir / "fig_judge_top_cluster_repetition.png")
    plt.close(fig)

    means = df[SCORE_FIELDS].mean(numeric_only=True).round(3)
    report = f"""# Archive 2026 + Canonical 48 LLM-as-a-Judge Report\n\nGenerated: {datetime.now(timezone.utc).isoformat()}\n\n## Method\n\nA stratified sample was drawn across `group × model_family × condition × scale × time_bin`, with extra coverage guarantees for every global embedding cluster. The judge prompt blinds group/model/condition/source labels and supplies local previous-post context plus same-cluster examples. Results are cached in SQLite and aggregated here.\n\n- Rubric version: `{RUBRIC_VERSION}`\n- Judge model: `{args.model}`\n- Sample rows: {len(sample_rows):,}\n- Completed judgments included: {len(df):,}\n\n## Outputs\n\n- `judge_results.jsonl` / `judge_results.csv` — post-level scored sample.\n- `judge_summary_by_cell.csv`, `judge_summary_by_group.csv`, `judge_summary_by_model.csv`, `judge_summary_by_condition.csv`, `judge_summary_by_cluster.csv`.\n- `judge_collapse_label_shares.csv`, `judge_claim_behavior_shares.csv`.\n- PNG heatmaps: `fig_judge_*_group_condition.png`; cluster repetition chart.\n\n## Overall score means\n\n```\n{means.to_string()}\n```\n\n## Group means\n\n```\n{pd.read_csv(judge_dir / 'judge_summary_by_group.csv').round(3).to_string(index=False)}\n```\n"""
    (judge_dir / "LLM_JUDGE_REPORT.md").write_text(report)
    print(f"Wrote judge aggregate: {len(df):,} judgments -> {judge_dir}")


def cluster_label_prompt(cluster_id: int, cluster_df: pd.DataFrame, examples: list[dict[str, str]], judge_summary: dict[str, Any] | None) -> str:
    stats = {
        "cluster_id": int(cluster_id),
        "n_posts": int(len(cluster_df)),
        "top_groups": cluster_df["group"].value_counts().head(5).to_dict(),
        "top_models": cluster_df["model_family"].value_counts().head(5).to_dict(),
        "top_conditions": cluster_df["condition"].value_counts().head(5).to_dict(),
        "judge_summary": judge_summary or {},
    }
    return f"""You are labeling one global embedding cluster from a Reddit-like AI-agent social simulation.

Return JSON only with keys:
- short_label: 3-8 word human-readable label
- discourse_frame: one sentence describing the dominant narrative/frame
- collapse_pattern: one of novel_diverse, mild_rephrase, frame_convergence, template_repetition, source_grounded, mixed
- qualitative_summary: 2-3 sentence summary
- representative_terms: array of 5-10 words/phrases
- caveats: one sentence noting uncertainty/heterogeneity

Cluster stats:
{json.dumps(stats, ensure_ascii=False, indent=2)}

Representative posts:
{json.dumps(examples, ensure_ascii=False, indent=2)}
"""


def cached_cluster_ids(conn: sqlite3.Connection, model: str) -> set[int]:
    return {int(r[0]) for r in conn.execute("SELECT cluster_id FROM cluster_labels WHERE judge_model=? AND rubric_version=?", (model, RUBRIC_VERSION))}


def store_cluster_label(conn: sqlite3.Connection, cid: int, model: str, prompt: str, label: dict[str, Any]) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO cluster_labels VALUES (?,?,?,?,?,?)",
        (cid, model, RUBRIC_VERSION, json.dumps(label, ensure_ascii=False), sha1_text(prompt), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()


def cmd_label_clusters(args: argparse.Namespace) -> None:
    key = load_env_key()
    out_dir = Path(args.out_dir)
    judge_dir = out_dir / "llm_judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    df = load_records(out_dir)
    if not args.include_seeds:
        df = df[~df["is_seed"]]
    conn = ensure_judge_db(judge_dir / "judge_cache.sqlite")
    done = cached_cluster_ids(conn, args.model)
    judge_summary_path = judge_dir / "judge_summary_by_cluster.csv"
    judge_summary = pd.read_csv(judge_summary_path).set_index("cluster_id").to_dict("index") if judge_summary_path.exists() else {}

    cluster_ids = sorted(int(c) for c in df["cluster_id"].dropna().unique())
    if args.limit:
        cluster_ids = cluster_ids[:args.limit]
    todo = [c for c in cluster_ids if c not in done]
    print(f"Cluster labels model={args.model}; clusters={len(cluster_ids)}; cached={len(done)}; remaining={len(todo)}")
    rng = random.Random(args.seed)

    def one(cid: int):
        sub = df[df["cluster_id"] == cid].copy()
        ex_df = sub.sample(min(args.examples, len(sub)), random_state=rng.randint(0, 10**9))
        examples = []
        for _, r in ex_df.iterrows():
            examples.append({
                "group": r.get("group", ""),
                "condition": r.get("condition", ""),
                "title": clean_snippet(str(r.get("title", "")), 180),
                "content": clean_snippet(str(r.get("content", "")), 650),
            })
        prompt = cluster_label_prompt(cid, sub, examples, judge_summary.get(cid))
        label = openrouter_json(prompt, args.model, key, args.max_tokens, args.retries, args.timeout)
        for k in ["short_label", "discourse_frame", "collapse_pattern", "qualitative_summary", "caveats"]:
            label[k] = clean_snippet(str(label.get(k, "")), 700)
        terms = label.get("representative_terms", [])
        if not isinstance(terms, list):
            terms = [str(terms)]
        label["representative_terms"] = [clean_snippet(str(t), 80) for t in terms[:12]]
        label["cluster_id"] = cid
        label["n_posts"] = int(len(sub))
        return cid, prompt, label

    if args.parallelism <= 1:
        for cid in progress(todo, desc="Labeling clusters", unit="cluster"):
            c, p, label = one(cid)
            store_cluster_label(conn, c, args.model, p, label)
            if args.sleep:
                time.sleep(args.sleep)
    else:
        with ThreadPoolExecutor(max_workers=args.parallelism) as pool:
            futs = [pool.submit(one, cid) for cid in todo]
            for fut in progress(as_completed(futs), total=len(futs), desc="Labeling clusters", unit="cluster"):
                c, p, label = fut.result()
                store_cluster_label(conn, c, args.model, p, label)

    rows = []
    for cid, model, rubric, jtxt, created_at in conn.execute(
        "SELECT cluster_id, judge_model, rubric_version, label_json, created_at FROM cluster_labels WHERE judge_model=? AND rubric_version=? ORDER BY cluster_id",
        (args.model, RUBRIC_VERSION),
    ):
        row = json.loads(jtxt)
        row.update({"cluster_id": int(cid), "judge_model": model, "rubric_version": rubric, "labeled_at": created_at})
        rows.append(row)
    with (judge_dir / "cluster_labels.jsonl").open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    if rows:
        # Expand list terms for CSV readability.
        csv_rows = []
        for r in rows:
            rr = r.copy()
            rr["representative_terms"] = "; ".join(map(str, rr.get("representative_terms", [])))
            csv_rows.append(rr)
        pd.DataFrame(csv_rows).to_csv(judge_dir / "cluster_labels.csv", index=False)
        lines = ["# Archive 2026 + Canonical 48 Cluster Labels", "", f"Generated: {datetime.now(timezone.utc).isoformat()}", ""]
        for r in rows:
            lines.append(f"## Cluster {int(r['cluster_id']):02d}: {r.get('short_label','')}")
            lines.append("")
            lines.append(f"- Posts: {r.get('n_posts','')}")
            lines.append(f"- Pattern: `{r.get('collapse_pattern','')}`")
            lines.append(f"- Frame: {r.get('discourse_frame','')}")
            lines.append(f"- Terms: {', '.join(map(str, r.get('representative_terms', [])))}")
            lines.append("")
            lines.append(str(r.get("qualitative_summary", "")))
            lines.append("")
            lines.append(f"Caveat: {r.get('caveats','')}")
            lines.append("")
        (judge_dir / "CLUSTER_LABELS.md").write_text("\n".join(lines))
    print(f"Wrote cluster labels: {len(rows)} -> {judge_dir}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sample-judge")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--sample", default="")
    p.add_argument("--posts-per-cell", type=int, default=4)
    p.add_argument("--min-per-cluster", type=int, default=8)
    p.add_argument("--max-rows", type=int, default=1800)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--include-seeds", action="store_true")
    p.set_defaults(func=cmd_sample_judge)

    p = sub.add_parser("judge")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--sample", default="")
    p.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    p.add_argument("--parallelism", type=int, default=4)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--sleep", type=float, default=0.0)
    p.add_argument("--max-tokens", type=int, default=600)
    p.set_defaults(func=cmd_judge)

    p = sub.add_parser("aggregate")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--sample", default="")
    p.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    p.set_defaults(func=cmd_aggregate)

    p = sub.add_parser("label-clusters")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    p.add_argument("--parallelism", type=int, default=4)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--examples", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--include-seeds", action="store_true")
    p.add_argument("--retries", type=int, default=5)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--sleep", type=float, default=0.0)
    p.add_argument("--max-tokens", type=int, default=900)
    p.set_defaults(func=cmd_label_clusters)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
