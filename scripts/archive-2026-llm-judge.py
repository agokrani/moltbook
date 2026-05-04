#!/usr/bin/env python3
"""Blinded LLM-as-a-judge protocol for archive-2026 main groups.

The judge never receives group/model/condition/run/source-path metadata. It sees
only anonymized post text plus anonymized local/semantic context. Group/model/etc.
analyses are produced only after judgments return by joining row_uid to a local
metadata map that is not sent to the model.
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
RUBRIC_VERSION = "archive-blind-posthoc-v1"
MAIN_GROUPS = {"base-model", "entropy-collapse", "obsession"}

# Avoid metadata-derived field names such as group/model/condition in prompts.
SCORE_FIELDS = [
    "novelty",
    "semantic_repetition",
    "frame_convergence",
    "consensus_conformity",
    "specificity",
    "evidence_grounding",
    "epistemic_caution",
    "template_rigidity",
    "citation_quality",
]
LABEL_ORDER = ["novel_contribution", "mild_rephrase", "frame_convergence", "template_repetition", "source_grounded", "off_topic"]
CLAIM_ORDER = ["no_checkable_claim", "specific_claim_supported", "specific_claim_unsupported", "speculative_or_conspiracy", "debunking_or_correction"]
POSTHOC_GROUP_COLS = ["group", "model_family", "condition", "scale", "time_bin"]
CONDITION_ORDER = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech", "unknown"]

# These keys/phrases should never appear as structured prompt metadata. The post
# text itself is allowed to contain arbitrary words; the audit focuses on leaked
# metadata fields and generated context objects.
FORBIDDEN_BLIND_KEYS = {
    "dataset_source",
    "group",
    "model",
    "model_family",
    "condition",
    "scale",
    "run_id",
    "run_path",
    "source_path",
    "post_id",
    "author_name",
    "author_display_name",
    "n_agents",
    "cluster_id",
    "cluster_label",
    "svd_1",
    "svd_2",
}
FORBIDDEN_PROMPT_KEY_RE = re.compile(
    r'(?i)("|\b)(' + "|".join(re.escape(k) for k in sorted(FORBIDDEN_BLIND_KEYS, key=len, reverse=True)) + r')("|\b)\s*:',
)


def progress(x, **kwargs):
    return tqdm(x, **kwargs) if tqdm else x


def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


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


def is_true_series(s: pd.Series) -> pd.Series:
    return s.astype(str).str.lower().isin(["true", "1", "yes"])


def clean_snippet(value: str, n: int) -> str:
    value = (value or "").replace("\x00", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value[:n]


def ensure_main_groups(index: pd.DataFrame) -> None:
    leaked = sorted(set(index.get("group", [])) - MAIN_GROUPS)
    if leaked:
        raise SystemExit(f"Non-main or excluded groups leaked into blinded judge index: {leaked}. Rebuild the index with default exclusions.")


def load_index(out_dir: Path) -> pd.DataFrame:
    index_path = out_dir / "combined_posts_index.csv"
    index_jsonl = out_dir / "combined_posts_index.jsonl"
    cluster_path = out_dir / "embedding_report" / "embedding_analysis_data.csv"
    if not index_path.exists():
        raise SystemExit(f"Missing {index_path}")
    df = pd.read_csv(index_path)
    # The tracked CSV intentionally omits long content columns. If the local
    # regenerable JSONL exists, attach text/content from it for judging.
    if index_jsonl.exists() and ("content" not in df.columns or "text" not in df.columns):
        long_rows = []
        with index_jsonl.open(errors="ignore") as f:
            for line in f:
                if line.strip():
                    r = json.loads(line)
                    long_rows.append({"content": r.get("content", ""), "text": r.get("text", "")})
        if len(long_rows) != len(df):
            raise SystemExit(f"JSONL rows {len(long_rows)} != CSV rows {len(df)}")
        long_df = pd.DataFrame(long_rows)
        for col in ["content", "text"]:
            if col not in df.columns:
                df[col] = long_df[col].to_numpy()
    if "content" not in df.columns:
        df["content"] = ""
    if "text" not in df.columns:
        df["text"] = (df.get("title", "").fillna("") + "\n" + df["content"].fillna("")) if "title" in df.columns else df["content"].fillna("")
    ensure_main_groups(df)
    df["row_index"] = range(len(df))
    df["row_uid"] = [
        sha1_text(f"{i}:{r.get('record_id','')}:{r.get('run_path','')}:{r.get('post_id','')}")
        for i, r in df.iterrows()
    ]
    df["is_seed_bool"] = is_true_series(df["is_seed"])
    df["text_len"] = df["text"].fillna("").astype(str).str.len()
    if cluster_path.exists():
        c = pd.read_csv(cluster_path, usecols=lambda x: x in {"cluster_id", "cluster_label", "svd_1", "svd_2"})
        if len(c) != len(df):
            raise SystemExit(f"Cluster rows {len(c)} != index rows {len(df)}")
        for col in c.columns:
            df[col] = c[col].to_numpy()
    else:
        df["cluster_id"] = -1
        df["cluster_label"] = "cluster_-1"
    return df


def blind_context_row(r: pd.Series, label: str | int, include_minutes: bool) -> dict[str, Any]:
    row: dict[str, Any] = {
        "item": str(label),
        "title": clean_snippet(str(r.get("title", "")), 180),
        "content": clean_snippet(str(r.get("content", "")), 700),
    }
    if include_minutes:
        try:
            row["relative_minute"] = round(float(r.get("minutes_elapsed", 0.0)), 2)
        except Exception:
            pass
    return row


def build_blind_rows(df: pd.DataFrame, chosen: pd.DataFrame, rng: random.Random, include_minutes: bool) -> list[dict[str, Any]]:
    run_groups = {run_path: sub.sort_values(["created_at", "post_id", "row_index"]) for run_path, sub in df.groupby("run_path", dropna=False)}
    by_cluster = {int(cid): sub for cid, sub in df.groupby("cluster_id", dropna=False)}
    rows: list[dict[str, Any]] = []
    for sample_i, (_, rec) in enumerate(chosen.sort_values("row_index").iterrows(), 1):
        previous = []
        run_df = run_groups.get(rec["run_path"])
        if run_df is not None:
            positions = run_df.index[run_df["row_uid"] == rec["row_uid"]].tolist()
            if positions:
                loc = run_df.index.get_loc(positions[0])
                prev = run_df.iloc[max(0, loc - 5):loc]
                previous = [blind_context_row(p, i + 1, include_minutes) for i, (_, p) in enumerate(prev.iterrows())]

        neighbors = []
        csub = by_cluster.get(int(rec.get("cluster_id", -1)))
        if csub is not None:
            candidates = csub[csub["row_uid"] != rec["row_uid"]]
            if len(candidates) > 0:
                take = candidates.sample(min(3, len(candidates)), random_state=rng.randint(0, 10**9))
                neighbors = [blind_context_row(p, i + 1, False) for i, (_, p) in enumerate(take.iterrows())]

        row = {
            "sample_id": f"blind-{sample_i:06d}",
            "row_uid": rec["row_uid"],
            "target_post": blind_context_row(rec, "target", include_minutes),
            "previous_posts_same_timeline": previous,
            "semantically_nearby_posts": neighbors,
        }
        assert_blind_row(row)
        row["prompt_sha1"] = sha1_text(judge_prompt(row))
        rows.append(row)
    return rows


def join_rows(chosen: pd.DataFrame) -> list[dict[str, Any]]:
    cols = [
        "row_uid",
        "record_id",
        "row_index",
        "dataset_source",
        "group",
        "run_id",
        "run_path",
        "model_family",
        "condition",
        "n_agents",
        "scale",
        "time_bin",
        "minutes_elapsed",
        "cluster_id",
        "cluster_label",
    ]
    existing = [c for c in cols if c in chosen.columns]
    return chosen[existing].to_dict("records")


def cmd_sample_blind(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    judge_dir = out_dir / "blind_llm_judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    df = load_index(out_dir)
    if not args.include_seeds:
        df = df[~df["is_seed_bool"]]
    df = df[df["text_len"] > 0].copy()
    rng = random.Random(args.seed)

    chosen_idx: set[int] = set()
    group_cols = [c for c in POSTHOC_GROUP_COLS if c in df.columns]
    for _, sub in df.groupby(group_cols, dropna=False):
        k = min(args.posts_per_cell, len(sub))
        if k <= 0:
            continue
        for i in sub.sample(k, random_state=rng.randint(0, 10**9)).index:
            chosen_idx.add(int(i))

    if args.min_per_cluster > 0 and "cluster_id" in df.columns:
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
        chosen = chosen.sample(args.max_rows, random_state=args.seed).sort_values("row_index")

    blind_rows = build_blind_rows(df, chosen, rng, include_minutes=args.include_minutes)
    sample_path = Path(args.sample) if args.sample else judge_dir / "blind_judge_sample.jsonl"
    join_path = Path(args.join) if args.join else judge_dir / "blind_judge_posthoc_join.csv"
    sample_path.parent.mkdir(parents=True, exist_ok=True)
    join_path.parent.mkdir(parents=True, exist_ok=True)

    with sample_path.open("w") as f:
        for row in blind_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with join_path.open("w", newline="") as f:
        rows = join_rows(chosen)
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["row_uid"])
        writer.writeheader()
        writer.writerows(rows)

    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "rubric_version": RUBRIC_VERSION,
        "rows": len(blind_rows),
        "prompt_blinded": True,
        "prompt_fields_sent_to_judge": ["target_post", "previous_posts_same_timeline", "semantically_nearby_posts"],
        "sample_file_control_fields_not_in_prompt": ["sample_id", "row_uid", "prompt_sha1"],
        "metadata_never_sent_to_judge": sorted(FORBIDDEN_BLIND_KEYS),
        "posthoc_join_path": str(join_path),
        "posthoc_group_cols": group_cols,
        "posts_per_cell": args.posts_per_cell,
        "min_per_cluster": args.min_per_cluster,
        "max_rows": args.max_rows,
        "seed": args.seed,
        "include_seeds": args.include_seeds,
    }
    sample_path.with_suffix(".json").write_text(json.dumps(meta, indent=2))
    audit_sample(sample_path)
    print(f"Wrote blinded judge sample: {len(blind_rows):,} rows -> {sample_path}")
    print(f"Wrote local post-hoc join map (not sent to judge) -> {join_path}")


def assert_blind_row(obj: Any, path: str = "row") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k) in FORBIDDEN_BLIND_KEYS:
                raise ValueError(f"Forbidden metadata key in blinded sample at {path}.{k}")
            assert_blind_row(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            assert_blind_row(v, f"{path}[{i}]")


def assert_prompt_blind(prompt: str) -> None:
    m = FORBIDDEN_PROMPT_KEY_RE.search(prompt)
    if m:
        raise ValueError(f"Forbidden metadata-looking key leaked into prompt near: {prompt[max(0, m.start()-40):m.end()+40]!r}")


def redacted_for_prompt_audit(row: dict[str, Any]) -> dict[str, Any]:
    """Keep prompt structure but remove user/post prose before regex checks.

    Natural post text can legitimately contain phrases like "for the group:".
    That is not metadata leakage. The audit therefore checks the exact prompt
    skeleton and JSON keys while replacing title/content values with placeholders.
    """
    def scrub(obj: Any) -> Any:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if k in {"title", "content"}:
                    out[k] = "[post text omitted for metadata audit]"
                else:
                    out[k] = scrub(v)
            return out
        if isinstance(obj, list):
            return [scrub(v) for v in obj]
        return obj
    return scrub(row)


def format_prompt(row: dict[str, Any]) -> str:
    return f"""You are scoring an anonymized post from a Reddit-like multi-agent social simulation.

You are not given any experimental labels, generator identities, timeline names, file paths, or collection identifiers. Do not infer or mention them. Score only the text and the anonymized surrounding examples.

Task: identify semantic collapse behavior: repetition, convergence on the same frame, consensus conformity, template-like posting, and whether claims are grounded.

Score each integer field from 1 to 5:
- novelty: 1=no new substantive contribution; 5=clearly new idea/evidence/frame.
- semantic_repetition: 1=not repetitive; 5=strongly repeats nearby/surrounding context.
- frame_convergence: 1=independent frame; 5=tightly follows a dominant shared frame.
- consensus_conformity: 1=independent/critical; 5=uncritically reinforces consensus.
- specificity: 1=vague/generic; 5=concrete claims/details/examples.
- evidence_grounding: 1=no evidence; 5=clear source/reasoning/evidence.
- epistemic_caution: 1=overconfident; 5=careful uncertainty/limitations.
- template_rigidity: 1=organic; 5=formulaic/checklist/receipt/template.
- citation_quality: 1=no or bad citation behavior; 5=specific useful citations/sources. Use 1 if no citations are needed and none appear.

collapse_label must be one of: {', '.join(LABEL_ORDER)}.
claim_behavior must be one of: {', '.join(CLAIM_ORDER)}.

Return JSON only with keys: {', '.join(SCORE_FIELDS)}, collapse_label, claim_behavior, dominant_frame, rationale.
Keep rationale under 45 words.

Target post:
{json.dumps(row['target_post'], ensure_ascii=False, indent=2)}

Earlier anonymized posts from the same local timeline:
{json.dumps(row.get('previous_posts_same_timeline', []), ensure_ascii=False, indent=2)}

Anonymized semantically nearby posts:
{json.dumps(row.get('semantically_nearby_posts', []), ensure_ascii=False, indent=2)}
"""


def judge_prompt(row: dict[str, Any]) -> str:
    # Deliberately no group/model/condition/run/path/cluster metadata. Context
    # entries are anonymized snippets only. Audit the prompt skeleton with post
    # prose redacted so natural words inside content are not treated as leaks.
    assert_blind_row(row)
    assert_prompt_blind(format_prompt(redacted_for_prompt_audit(row)))
    return format_prompt(row)


def audit_sample(sample_path: Path, limit: int = 0) -> None:
    n = 0
    with sample_path.open() as f:
        for line in f:
            if not line.strip():
                continue
            n += 1
            row = json.loads(line)
            judge_prompt(row)  # builds and audits the redacted prompt skeleton
            if limit and n >= limit:
                break
    if n == 0:
        raise SystemExit(f"No rows in {sample_path}")


def cmd_audit_prompts(args: argparse.Namespace) -> None:
    sample_path = Path(args.sample) if args.sample else Path(args.out_dir) / "blind_llm_judge" / "blind_judge_sample.jsonl"
    audit_sample(sample_path, limit=args.limit)
    print(f"Prompt audit passed: no forbidden metadata keys in blinded sample/prompts -> {sample_path}")


def ensure_judge_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS judgments (
        row_uid TEXT NOT NULL,
        sample_id TEXT NOT NULL,
        judge_model TEXT NOT NULL,
        rubric_version TEXT NOT NULL,
        judgment_json TEXT NOT NULL,
        prompt_sha1 TEXT NOT NULL,
        created_at TEXT NOT NULL,
        PRIMARY KEY(row_uid, judge_model, rubric_version)
    )""")
    conn.commit()
    return conn


def cached_judgment_uids(conn: sqlite3.Connection, model: str) -> set[str]:
    return {r[0] for r in conn.execute("SELECT row_uid FROM judgments WHERE judge_model=? AND rubric_version=?", (model, RUBRIC_VERSION))}


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
    out["collapse_index"] = round(float((out["semantic_repetition"] + out["frame_convergence"] + out["consensus_conformity"] + out["template_rigidity"] + (6 - out["novelty"])) / 5.0), 3)
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
    last: Exception | None = None
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
            row.get("sample_id", ""),
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
    sample_path = Path(args.sample) if args.sample else Path(args.out_dir) / "blind_llm_judge" / "blind_judge_sample.jsonl"
    rows = [json.loads(line) for line in sample_path.open() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    for row in rows:
        judge_prompt(row)  # builds and audits the redacted prompt skeleton
    conn = ensure_judge_db(Path(args.out_dir) / "blind_llm_judge" / "judge_cache.sqlite")
    cached = cached_judgment_uids(conn, args.model)
    todo = [r for r in rows if r["row_uid"] not in cached]
    print(f"Blinded judge model={args.model}; sample={len(rows):,}; cached={len(cached):,}; remaining={len(todo):,}; parallelism={args.parallelism}")

    def one(row: dict[str, Any]):
        p = judge_prompt(row)
        j = normalize_judgment(openrouter_json(p, args.model, key, args.max_tokens, args.retries, args.timeout))
        return row, p, j

    if args.parallelism <= 1:
        for row in progress(todo, desc="Judging blinded posts", unit="post"):
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
            for fut in progress(as_completed(futs), total=len(futs), desc="Judging blinded posts", unit="post"):
                r, p, j = fut.result()
                store_judgment(conn, r, args.model, p, j)
    print("Cached blinded judgments now:", len(cached_judgment_uids(conn, args.model)))


def load_judgments(conn: sqlite3.Connection, model: str) -> pd.DataFrame:
    rows = []
    for row_uid, sample_id, judge_model, rubric, jtxt, prompt_sha1, created_at in conn.execute(
        "SELECT row_uid, sample_id, judge_model, rubric_version, judgment_json, prompt_sha1, created_at FROM judgments WHERE judge_model=? AND rubric_version=?",
        (model, RUBRIC_VERSION),
    ):
        j = json.loads(jtxt)
        j.update({
            "row_uid": row_uid,
            "sample_id": sample_id,
            "judge_model": judge_model,
            "rubric_version": rubric,
            "prompt_sha1": prompt_sha1,
            "judged_at": created_at,
        })
        rows.append(j)
    return pd.DataFrame(rows)


def metric_summary(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    metrics = SCORE_FIELDS + ["collapse_index"]
    agg = {m: ["mean", "std", "count"] for m in metrics if m in df.columns}
    out = df.groupby(cols, dropna=False).agg(agg)
    out.columns = ["_".join(c).strip("_") for c in out.columns]
    return out.reset_index()


def write_md_report(judge_dir: Path, df: pd.DataFrame, model: str, sample_n: int) -> None:
    means = df[SCORE_FIELDS + ["collapse_index"]].mean(numeric_only=True).round(3)
    group_summary_path = judge_dir / "blind_summary_by_group.csv"
    group_summary = pd.read_csv(group_summary_path).round(3) if group_summary_path.exists() else pd.DataFrame()
    report = f"""# Blinded LLM-as-a-Judge Report

Generated: {datetime.now(timezone.utc).isoformat()}

## Blinding protocol

The judge prompt contains **no group, model, condition, run, source-path, cluster, or dataset-source metadata**. The model sees only:

- one anonymized target post,
- anonymized earlier posts from the same local timeline,
- anonymized semantically nearby posts.

The local join file maps `row_uid` back to `group`, `model_family`, `condition`, etc. only **after** judgments return. Therefore the judge scores items individually and cannot directly score or compare archive groups.

## Post-hoc group analysis

Group-level analysis is still valid as a post-hoc aggregation: first score blind posts independently, then join those row-level scores to the local metadata map and summarize by group/model/condition. This answers “what happens within each group?” without putting group labels in the prompt.

- Rubric version: `{RUBRIC_VERSION}`
- Judge model: `{model}`
- Sample rows: {sample_n:,}
- Completed judgments included: {len(df):,}

## Overall score means

```
{means.to_string()}
```

## Group means (post-hoc)

```
{group_summary.to_string(index=False) if not group_summary.empty else 'No group summary generated.'}
```

## Outputs

- `blind_judge_results_blind.jsonl` — row-level judgments with no group metadata.
- `blind_judge_results_with_metadata.csv` — local post-hoc join; not sent to judge.
- `blind_summary_by_group.csv`, `blind_summary_by_model_family.csv`, `blind_summary_by_condition.csv`, `blind_summary_by_group_condition.csv`.
- `groups/<group>/blind_judge_results.csv` and `groups/<group>/blind_summary_by_condition.csv` for individual group review.
"""
    (judge_dir / "BLINDED_LLM_JUDGE_REPORT.md").write_text(report)


def cmd_aggregate(args: argparse.Namespace) -> None:
    out_dir = Path(args.out_dir)
    judge_dir = out_dir / "blind_llm_judge"
    judge_dir.mkdir(parents=True, exist_ok=True)
    sample_path = Path(args.sample) if args.sample else judge_dir / "blind_judge_sample.jsonl"
    join_path = Path(args.join) if args.join else judge_dir / "blind_judge_posthoc_join.csv"
    sample_rows = [json.loads(line) for line in sample_path.open() if line.strip()]
    join = pd.read_csv(join_path)
    conn = ensure_judge_db(judge_dir / "judge_cache.sqlite")
    judgments = load_judgments(conn, args.model)
    if judgments.empty:
        raise SystemExit("No blinded judgments cached")

    blind_results = judgments.copy()
    blind_results.to_json(judge_dir / "blind_judge_results_blind.jsonl", orient="records", lines=True, force_ascii=False)
    df = join.merge(judgments, on="row_uid", how="inner")
    if df.empty:
        raise SystemExit("No post-hoc join rows matched judgments")
    df.to_csv(judge_dir / "blind_judge_results_with_metadata.csv", index=False)

    for cols, name in [
        (["group"], "group"),
        (["model_family"], "model_family"),
        (["condition"], "condition"),
        (["scale"], "scale"),
        (["time_bin"], "time_bin"),
        (["group", "condition"], "group_condition"),
        (["group", "model_family"], "group_model_family"),
        (["model_family", "condition"], "model_family_condition"),
    ]:
        have = [c for c in cols if c in df.columns]
        if len(have) == len(cols):
            s = metric_summary(df, cols)
            if name == "condition":
                s["condition"] = pd.Categorical(s["condition"], categories=CONDITION_ORDER, ordered=True)
                s = s.sort_values("condition")
            s.to_csv(judge_dir / f"blind_summary_by_{name}.csv", index=False)

    group_root = judge_dir / "groups"
    group_root.mkdir(exist_ok=True)
    for group, sub in df.groupby("group", dropna=False):
        gdir = group_root / slugify(str(group))
        gdir.mkdir(parents=True, exist_ok=True)
        sub.to_csv(gdir / "blind_judge_results.csv", index=False)
        if "condition" in sub.columns:
            metric_summary(sub, ["condition"]).to_csv(gdir / "blind_summary_by_condition.csv", index=False)
        if "model_family" in sub.columns:
            metric_summary(sub, ["model_family"]).to_csv(gdir / "blind_summary_by_model_family.csv", index=False)

    write_md_report(judge_dir, df, args.model, len(sample_rows))
    print(f"Wrote blinded post-hoc aggregate: {len(df):,} judgments -> {judge_dir}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("sample-blind", help="Build a blinded sample plus a local post-hoc metadata join map.")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--sample", default="")
    p.add_argument("--join", default="")
    p.add_argument("--posts-per-cell", type=int, default=4)
    p.add_argument("--min-per-cluster", type=int, default=8)
    p.add_argument("--max-rows", type=int, default=1800)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--include-seeds", action="store_true")
    p.add_argument("--include-minutes", action="store_true", help="Include only relative timing, never group/run/model labels.")
    p.set_defaults(func=cmd_sample_blind)

    p = sub.add_parser("audit-prompts", help="Fail if the blinded sample or generated prompts contain forbidden metadata keys.")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--sample", default="")
    p.add_argument("--limit", type=int, default=0)
    p.set_defaults(func=cmd_audit_prompts)

    p = sub.add_parser("judge", help="Run OpenRouter judgments on the blinded sample.")
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

    p = sub.add_parser("aggregate", help="Join blind row-level judgments to local metadata and summarize post-hoc by group/model/condition.")
    p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    p.add_argument("--sample", default="")
    p.add_argument("--join", default="")
    p.add_argument("--model", default=DEFAULT_JUDGE_MODEL)
    p.set_defaults(func=cmd_aggregate)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
