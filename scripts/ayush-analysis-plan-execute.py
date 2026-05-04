#!/usr/bin/env python3
"""Execute Ayush-reviewed run-level analysis plan.

This script implements the deterministic + embedding parts of
analysis/archive-2026-plus-canonical-gemini/ANALYSIS_PLAN_FOR_AYUSH.md.
It deliberately analyzes each run first, then aggregates run-level deltas.

It does not run paid LLM judge calls; it prepares the same run/post index that a
separate blinded judge pass can consume after prompt review.
"""
from __future__ import annotations

import argparse
import bz2
import csv
import gzip
import hashlib
import json
import math
import re
import sqlite3
import statistics
import zlib
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.preprocessing import normalize

DEFAULT_ARCHIVE_ROOT = Path("exports/huggingface/Ayushnangia/moltbook-archive-2026-targeted")
DEFAULT_CANONICAL_ROOT = Path("exports/huggingface/agokrani/moltbook-entropy-collapse-canonical-48/data")
DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
EMBED_MODEL = "qwen/qwen3-embedding-8b"
SEED_PREFIXES = ("civiclens_",)
CONDITIONS = ["mag0", "mag1", "mag5", "mag25", "dom-agi", "dom-tech"]
FAMILIES = ["single_model_final", "mixed_model_roster", "base_model_as_tool", "obsession_prompting"]
DISPLAY_FAMILY = {
    "single_model_final": "Single-model final runs",
    "mixed_model_roster": "Mixed-model roster",
    "base_model_as_tool": "Base model as tool",
    "obsession_prompting": "Obsession prompting",
}
MODEL_DISPLAY = {
    "gpt-5": "GPT-5",
    "gemini-flash-lite": "Gemini Flash Lite",
    "google/gemini-3.1-flash-lite-preview": "Gemini Flash Lite",
    "moonshotai/kimi-k2.5": "Kimi K2.5",
    "kimi-k2.5": "Kimi K2.5",
    "z-ai/glm-5": "GLM-5",
    "glm-5": "GLM-5",
}
FIXED_BINS = [(0.0, 15.0), (15.0, 30.0), (30.0, 45.0), (45.0, 60.0)]
COMPRESSORS = {"gzip": gzip.compress, "bzip2": bz2.compress, "zlib": zlib.compress}
TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-'][a-z0-9]+)?", flags=re.I)
_TOKEN_CACHE: dict[str, list[str]] = {}


@dataclass
class RunSpec:
    run_uid: str
    source_dataset: str
    source_path: str
    internal_family_label: str
    display_family_label: str
    model_family: str
    model_display: str
    roster_name: str
    condition: str
    n_agents: int
    scale: str
    run_id: str
    include_in_main: bool = True
    exclusion_reason: str = ""
    notes: str = ""


@dataclass
class PostRecord:
    record_id: str
    run_uid: str
    source_dataset: str
    source_path: str
    internal_family_label: str
    display_family_label: str
    model_family: str
    model_display: str
    roster_name: str
    condition: str
    n_agents: int
    scale: str
    run_id: str
    post_id: str
    author_name: str
    author_display_name: str
    is_seed: bool
    created_at: str
    minutes_elapsed: float
    normalized_time: float
    title: str
    content: str
    text: str
    score: int
    comment_count: int
    post_type: str


# ----------------------------- parsing helpers -----------------------------

def sha1_text(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8", errors="ignore")).hexdigest()


def slugify(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value)).strip("-") or "unknown"


def parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00").replace(" ", "T", 1))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(errors="ignore"))
    except Exception:
        return {}


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    with path.open(errors="ignore") as f:
        for line in f:
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    return rows


def infer_condition(name: str) -> str:
    for cond in ["dom-agi", "dom-tech", "mag25", "mag5", "mag1", "mag0"]:
        if cond in name:
            return cond
    return "unknown"


def infer_n_agents(run_name: str, parent_name: str = "") -> int:
    m = re.search(r"(?:^|-)n(\d+)(?:-|$)", run_name)
    if m:
        return int(m.group(1))
    m = re.search(r"agents-(\d+)", parent_name)
    if m:
        return int(m.group(1))
    return 0


def canonical_model_from_path(run_dir: Path) -> str:
    # .../data/<model>/agents-10/<run>
    try:
        return run_dir.parents[1].name
    except Exception:
        return "unknown"


def model_display(model: str) -> str:
    return MODEL_DISPLAY.get(model, model)


def infer_archive_group(path: Path) -> str:
    s = str(path).lower()
    if "source-citation" in s:
        return "source-citation"
    if "frontier" in s or "mixed" in s:
        return "frontier/mixed-model"
    if "base-model" in s or "/bm-" in s:
        return "base-model"
    if "obsession" in s or "obs_" in s or "/obs" in s:
        return "obsession"
    if "/ec-" in s or "entropy-collapse" in s:
        return "entropy-collapse"
    return "other/unknown"


def infer_archive_model(run_dir: Path, meta: dict, group: str) -> str:
    s = str(run_dir).lower()
    for key in [
        "qwen3.5-35b-a3b-base", "qwen3.5-35b-a3b-instruct",
        "olmo3-32b-instruct", "olmo3-32b-think", "olmo3-32b-base",
    ]:
        if key in s or key in str(meta).lower():
            return key
    for key in ["model", "llm_model", "openrouter_model"]:
        if meta.get(key):
            return str(meta[key])
    if "gpt-5" in s or "gpt5" in s:
        return "gpt-5"
    if "gemini" in s:
        return "google/gemini-3.1-flash-lite-preview"
    if "kimi" in s:
        return "moonshotai/kimi-k2.5"
    if "glm" in s:
        return "z-ai/glm-5"
    if "nemotron" in s:
        return "nvidia/nemotron-3-super-120b-a12b:free"
    if "mixed" in s or "frontier" in s:
        return "mixed-roster"
    return group


# ------------------------------- discovery ---------------------------------

def discover_canonical(canonical_root: Path) -> list[RunSpec]:
    specs: list[RunSpec] = []
    for posts_path in sorted(canonical_root.rglob("posts.jsonl")):
        run_dir = posts_path.parent
        model = canonical_model_from_path(run_dir)
        run_id = run_dir.name
        n_agents = infer_n_agents(run_id, run_dir.parent.name)
        condition = infer_condition(run_id)
        source = "canonical-gemini-flash-lite" if model == "gemini-flash-lite" else "canonical-48"
        run_uid = sha1_text(f"{source}:{run_dir}")
        specs.append(RunSpec(
            run_uid=run_uid,
            source_dataset=source,
            source_path=str(run_dir),
            internal_family_label="single_model_final",
            display_family_label=DISPLAY_FAMILY["single_model_final"],
            model_family={
                "gemini-flash-lite": "google/gemini-3.1-flash-lite-preview",
                "kimi-k2.5": "moonshotai/kimi-k2.5",
                "glm-5": "z-ai/glm-5",
            }.get(model, model),
            model_display=model_display(model),
            roster_name=model_display(model),
            condition=condition,
            n_agents=n_agents,
            scale=f"n{n_agents}" if n_agents else "unknown",
            run_id=run_id,
        ))
    return specs


def discover_archive(archive_root: Path) -> list[RunSpec]:
    specs: list[RunSpec] = []
    for posts_path in sorted(archive_root.rglob("posts.jsonl")):
        run_dir = posts_path.parent
        group = infer_archive_group(run_dir)
        path_s = str(run_dir).lower()
        include = True
        reason = ""
        family = ""
        display = ""
        if group == "base-model":
            if "ignore" in path_s:
                include = False
                reason = "base-model path contains ignore"
            family = "base_model_as_tool"
            display = DISPLAY_FAMILY[family]
        elif group == "obsession":
            family = "obsession_prompting"
            display = DISPLAY_FAMILY[family]
        elif group == "frontier/mixed-model":
            family = "mixed_model_roster"
            display = DISPLAY_FAMILY[family]
        elif group == "entropy-collapse":
            include = False
            reason = "old archive entropy-collapse excluded"
            family = "excluded_entropy_collapse"
            display = "Excluded old archive entropy-collapse"
        elif group == "source-citation":
            include = False
            reason = "source/site-citation excluded"
            family = "excluded_source_citation"
            display = "Excluded source/site-citation"
        else:
            include = False
            reason = f"unrecognized archive group {group}"
            family = "excluded_unknown"
            display = "Excluded unknown"
        meta = load_json(run_dir / "metadata.json")
        run_id = run_dir.name
        n_agents = infer_n_agents(run_id, run_dir.parent.name)
        model = infer_archive_model(run_dir, meta, group)
        roster = "Mixed-model roster" if family == "mixed_model_roster" else model_display(model)
        specs.append(RunSpec(
            run_uid=sha1_text(f"archive-2026:{run_dir}"),
            source_dataset="archive-2026",
            source_path=str(run_dir),
            internal_family_label=family,
            display_family_label=display,
            model_family=model,
            model_display=model_display(model),
            roster_name=roster,
            condition=infer_condition(run_id),
            n_agents=n_agents,
            scale=f"n{n_agents}" if n_agents else "unknown",
            run_id=run_id,
            include_in_main=include,
            exclusion_reason=reason,
        ))
    return specs


def load_run_posts(spec: RunSpec) -> list[PostRecord]:
    run_dir = Path(spec.source_path)
    rows = load_jsonl(run_dir / "posts.jsonl")
    if not rows:
        return []
    agent_times = []
    all_times = []
    for p in rows:
        dt = parse_time(p.get("created_at") or p.get("createdAt") or "")
        if dt:
            all_times.append(dt)
            author = str(p.get("author_name") or p.get("authorName") or "")
            if not author.startswith(SEED_PREFIXES):
                agent_times.append(dt)
    start = min(agent_times or all_times) if (agent_times or all_times) else None
    end = max(agent_times or all_times) if (agent_times or all_times) else start
    duration = max(0.0, (end - start).total_seconds() / 60.0) if start and end else 0.0
    out = []
    for p in rows:
        author = str(p.get("author_name") or p.get("authorName") or "")
        is_seed = author.startswith(SEED_PREFIXES)
        created = str(p.get("created_at") or p.get("createdAt") or "")
        dt = parse_time(created)
        minutes = ((dt - start).total_seconds() / 60.0) if (dt and start) else 0.0
        norm = min(1.0, max(0.0, minutes / duration)) if duration > 0 else 0.0
        title = (p.get("title") or "").strip()
        content = (p.get("content") or "").strip()
        text = (title + "\n\n" + content).strip()
        post_id = str(p.get("id") or sha1_text(f"{spec.source_path}:{title}:{content}:{created}"))
        record_id = sha1_text(f"{spec.source_dataset}:{spec.source_path}:{post_id}:{title}:{created}")
        out.append(PostRecord(
            record_id=record_id,
            run_uid=spec.run_uid,
            source_dataset=spec.source_dataset,
            source_path=spec.source_path,
            internal_family_label=spec.internal_family_label,
            display_family_label=spec.display_family_label,
            model_family=spec.model_family,
            model_display=spec.model_display,
            roster_name=spec.roster_name,
            condition=spec.condition,
            n_agents=spec.n_agents,
            scale=spec.scale,
            run_id=spec.run_id,
            post_id=post_id,
            author_name=author,
            author_display_name=str(p.get("author_display_name") or p.get("authorDisplayName") or ""),
            is_seed=is_seed,
            created_at=created,
            minutes_elapsed=round(minutes, 4),
            normalized_time=round(norm, 6),
            title=title,
            content=content,
            text=text,
            score=int(p.get("score") or 0),
            comment_count=int(p.get("comment_count") or p.get("commentCount") or 0),
            post_type=str(p.get("post_type") or p.get("postType") or ""),
        ))
    return out


# ------------------------------ metrics ------------------------------------

def tokenize(text: str) -> list[str]:
    text = text or ""
    got = _TOKEN_CACHE.get(text)
    if got is not None:
        return got
    toks = [m.group(0).lower() for m in TOKEN_RE.finditer(text)]
    _TOKEN_CACHE[text] = toks
    return toks


def ngrams(tokens: Sequence[str], n: int) -> list[tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1)]


def distinct_n(texts: Sequence[str], n: int) -> float:
    total = 0
    unique: set[tuple[str, ...]] = set()
    for text in texts:
        grams = ngrams(tokenize(text), n)
        total += len(grams)
        unique.update(grams)
    return float(len(unique) / total) if total else math.nan


def simpson_effective_ngrams(texts: Sequence[str], n: int = 5) -> float:
    c = Counter()
    for text in texts:
        c.update(ngrams(tokenize(text), n))
    total = sum(c.values())
    if total <= 0:
        return math.nan
    d = sum((v/total)**2 for v in c.values())
    return float(1.0/d) if d > 0 else math.nan


def compression_ratio(texts: Sequence[str], alg: str) -> float:
    raw = "\n".join(t for t in texts if t).encode("utf-8")
    if not raw:
        return math.nan
    return float(len(COMPRESSORS[alg](raw)) / len(raw))


def bin_label_fixed(i: int) -> str:
    return ["0-15m", "15-30m", "30-45m", "45-60m"][i]


def assign_fixed_bins(posts: list[PostRecord]) -> list[tuple[int, str, list[PostRecord]]]:
    out = []
    for i, (lo, hi) in enumerate(FIXED_BINS):
        if i < 3:
            members = [p for p in posts if lo <= p.minutes_elapsed < hi]
        else:
            members = [p for p in posts if lo <= p.minutes_elapsed <= hi]
        out.append((i, bin_label_fixed(i), members))
    return out


def assign_quartile_bins(posts: list[PostRecord]) -> list[tuple[int, str, list[PostRecord]]]:
    out = []
    qs = [(0.0, 0.25), (0.25, 0.50), (0.50, 0.75), (0.75, 1.000001)]
    for i, (lo, hi) in enumerate(qs):
        members = [p for p in posts if lo <= p.normalized_time < hi]
        out.append((i, f"Q{i+1}", members))
    return out


def subsampled_distinct(texts: list[str], n: int, target: int, seed: int, reps: int) -> dict:
    if target <= 0 or not texts:
        return {"mean": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n_reps": 0}
    rng = np.random.default_rng(seed)
    vals = []
    arr = np.asarray(texts, dtype=object)
    for _ in range(reps):
        if len(arr) <= target:
            sub = arr
        else:
            sub = arr[rng.choice(len(arr), size=target, replace=False)]
        vals.append(distinct_n(list(sub), n))
    vals = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
    if len(vals) == 0:
        return {"mean": math.nan, "ci_low": math.nan, "ci_high": math.nan, "n_reps": 0}
    return {"mean": float(np.mean(vals)), "ci_low": float(np.percentile(vals, 2.5)), "ci_high": float(np.percentile(vals, 97.5)), "n_reps": int(len(vals))}


def compute_timebin_metrics(posts: list[PostRecord], scheme: str, reps: int) -> tuple[list[dict], list[dict]]:
    bins = assign_fixed_bins(posts) if scheme == "fixed_15m" else assign_quartile_bins(posts)
    nonempty = [len(m) for _, _, m in bins if len(m) > 0]
    target = min(nonempty) if nonempty else 0
    rows = []
    cum_texts: list[str] = []
    for i, label, members in bins:
        texts = [p.text for p in members if p.text]
        cum_texts.extend(texts)
        row = {
            "scheme": scheme,
            "bin_idx": i,
            "bin_label": label,
            "n_posts": len(members),
            "n_agents": len({p.author_name for p in members}),
            "subsample_target_posts": target,
        }
        for alg in COMPRESSORS:
            row[f"compression_{alg}"] = compression_ratio(texts, alg)
        for n in range(1, 6):
            row[f"distinct_{n}"] = distinct_n(texts, n)
            ss = subsampled_distinct(texts, n, target, seed=1000 + 37*i + n, reps=reps)
            row[f"distinct_{n}_sub_mean"] = ss["mean"]
            row[f"distinct_{n}_sub_ci_low"] = ss["ci_low"]
            row[f"distinct_{n}_sub_ci_high"] = ss["ci_high"]
        row["distinct_5_cumulative"] = distinct_n(cum_texts, 5)
        row["simpson_5gram_effective"] = simpson_effective_ngrams(texts, 5)
        rows.append(row)
    # Deltas final - first for all numeric metrics.
    deltas = []
    if len(rows) >= 2:
        first, last = rows[0], rows[-1]
        d = {"scheme": scheme, "first_bin": first["bin_label"], "final_bin": last["bin_label"], "first_n_posts": first["n_posts"], "final_n_posts": last["n_posts"]}
        for k in rows[0]:
            if k in {"scheme", "bin_idx", "bin_label"}:
                continue
            if isinstance(first.get(k), (int, float)) and isinstance(last.get(k), (int, float)):
                a, b = first.get(k), last.get(k)
                d[f"delta_{k}"] = (b - a) if np.isfinite(a) and np.isfinite(b) else math.nan
        deltas.append(d)
    return rows, deltas


def top_ngram_counter(posts: list[PostRecord], n: int) -> Counter:
    c = Counter()
    for p in posts:
        c.update(ngrams(tokenize(p.text), n))
    return c


def gini(values: Sequence[int]) -> float:
    vals = np.asarray([v for v in values if v >= 0], dtype=float)
    if len(vals) == 0 or vals.sum() <= 0:
        return 0.0
    vals.sort()
    n = len(vals)
    idx = np.arange(1, n+1)
    return float((2*np.sum(idx*vals) - (n+1)*np.sum(vals)) / (n*np.sum(vals)))


def phrase_rows_for_run(posts: list[PostRecord], seed_posts: list[PostRecord], top_k: int = 10) -> tuple[list[dict], list[dict], list[dict]]:
    top_rows, diffusion_rows, concentration_rows = [], [], []
    seed_grams = {n: set() for n in [4, 5]}
    for sp in seed_posts:
        toks = tokenize(sp.text)
        for n in [4, 5]:
            seed_grams[n].update(" ".join(g) for g in ngrams(toks, n))

    # Precompute tokens and joined n-gram lists/sets once per run. The canonical
    # handoff analysis repeatedly asks phrase-use questions over the same posts;
    # caching keeps this tractable for all families.
    post_tokens = {p.post_id: tokenize(p.text) for p in posts}
    joined_ngrams: dict[int, dict[str, list[str]]] = {4: {}, 5: {}}
    joined_sets: dict[int, dict[str, set[str]]] = {4: {}, 5: {}}
    for p in posts:
        toks = post_tokens[p.post_id]
        for n in [4, 5]:
            vals = [" ".join(g) for g in ngrams(toks, n)]
            joined_ngrams[n][p.post_id] = vals
            joined_sets[n][p.post_id] = set(vals)

    counters = {n: Counter() for n in [4, 5]}
    for n in [4, 5]:
        for p in posts:
            counters[n].update(joined_ngrams[n][p.post_id])
        for rank, (phrase, count) in enumerate(counters[n].most_common(top_k), 1):
            top_rows.append({"ngram_n": n, "rank": rank, "phrase": phrase, "count": count, "in_seed": phrase in seed_grams[n]})
    top3 = [phrase for phrase, _ in counters[5].most_common(3)]
    agents = sorted({p.author_name for p in posts})
    sorted_posts = sorted(posts, key=lambda x: x.minutes_elapsed)
    adopter_sets = []
    for rank, phrase in enumerate(top3, 1):
        first = {}
        counts = Counter()
        for p in sorted_posts:
            if phrase in joined_sets[5][p.post_id]:
                counts[p.author_name] += 1
                first.setdefault(p.author_name, p)
        total_uses = sum(counts.values())
        all_counts = [counts.get(a, 0) for a in agents]
        sorted_counts = sorted(all_counts, reverse=True)
        concentration_rows.append({
            "phrase_rank": rank, "phrase": phrase, "total_agents": len(agents),
            "adopters": len(first), "adoption_rate": len(first)/len(agents) if agents else math.nan,
            "total_uses": total_uses, "gini_all_agents": gini(all_counts),
            "gini_adopters_only": gini([counts[a] for a in first]),
            "top1_agent_share": (sorted_counts[0]/total_uses) if total_uses else math.nan,
            "top3_agent_share": (sum(sorted_counts[:3])/total_uses) if total_uses else math.nan,
        })
        for agent, p in sorted(first.items(), key=lambda kv: kv[1].minutes_elapsed):
            diffusion_rows.append({
                "phrase_rank": rank, "phrase": phrase, "agent": agent,
                "first_minute": p.minutes_elapsed, "post_id": p.post_id,
                "total_agents_in_run": len(agents), "total_adopters": len(first),
                "adoption_rate": len(first)/len(agents) if agents else math.nan,
            })
        adopter_sets.append((phrase, set(first)))
    # Jaccard phrase overlap among top3 adopters.
    for i in range(len(adopter_sets)):
        for j in range(i+1, len(adopter_sets)):
            a, aset = adopter_sets[i]
            b, bset = adopter_sets[j]
            inter = len(aset & bset); union = len(aset | bset)
            concentration_rows.append({
                "phrase_rank": f"{i+1}-{j+1}", "phrase": f"{a} || {b}",
                "total_agents": len(agents), "adopters": math.nan, "adoption_rate": math.nan,
                "total_uses": math.nan, "gini_all_agents": math.nan, "gini_adopters_only": math.nan,
                "top1_agent_share": math.nan, "top3_agent_share": math.nan,
                "adopter_jaccard": inter/union if union else math.nan,
            })
    return top_rows, diffusion_rows, concentration_rows


def bootstrap_ci(vals: Sequence[float], seed: int = 42, reps: int = 5000) -> tuple[float, float]:
    x = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
    if len(x) == 0:
        return math.nan, math.nan
    if len(x) == 1:
        return float(x[0]), float(x[0])
    rng = np.random.default_rng(seed)
    means = [float(np.mean(x[rng.integers(0, len(x), len(x))])) for _ in range(reps)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def sign_test_p(n_success: int, n_total: int) -> float:
    if n_total <= 0:
        return math.nan
    # two-sided exact binomial p under p=.5
    k = min(n_success, n_total - n_success)
    prob = sum(math.comb(n_total, i) for i in range(k+1)) / (2**n_total)
    return min(1.0, 2*prob)


def summarize_deltas(df: pd.DataFrame, by: list[str], metrics: list[str]) -> pd.DataFrame:
    rows = []
    for key, sub in df.groupby(by, dropna=False):
        if not isinstance(key, tuple): key = (key,)
        row = {col: val for col, val in zip(by, key)}
        row["n_runs"] = int(sub["run_uid"].nunique())
        for m in metrics:
            vals = sub[m].to_numpy(dtype=float) if m in sub.columns else np.asarray([])
            vals = vals[np.isfinite(vals)]
            row[f"{m}_n_valid"] = int(len(vals))
            row[f"{m}_mean"] = float(np.mean(vals)) if len(vals) else math.nan
            row[f"{m}_median"] = float(np.median(vals)) if len(vals) else math.nan
            lo, hi = bootstrap_ci(vals)
            row[f"{m}_ci_low"] = lo
            row[f"{m}_ci_high"] = hi
            row[f"{m}_n_negative"] = int(np.sum(vals < 0)) if len(vals) else 0
            row[f"{m}_n_positive"] = int(np.sum(vals > 0)) if len(vals) else 0
            row[f"{m}_sign_p"] = sign_test_p(int(np.sum(vals < 0)), len(vals)) if len(vals) else math.nan
        rows.append(row)
    return pd.DataFrame(rows)


# ------------------------------- embeddings --------------------------------

def load_embedding_map(sqlite_path: Path, model: str = EMBED_MODEL) -> dict[str, np.ndarray]:
    if not sqlite_path.exists():
        return {}
    conn = sqlite3.connect(sqlite_path)
    out = {}
    for rid, dim, blob in conn.execute("SELECT record_id, dim, embedding FROM embeddings WHERE model=?", (model,)):
        out[rid] = np.frombuffer(blob, dtype=np.float32, count=dim).copy()
    conn.close()
    return out


def vendi_score(x: np.ndarray) -> float:
    if len(x) < 2:
        return math.nan
    sim = x @ x.T
    k = (sim + 1.0) / 2.0
    eig = np.linalg.eigvalsh(k / len(x)).astype(float)
    eig = eig[eig > 1e-12]
    eig = eig / eig.sum()
    return float(np.exp(-np.sum(eig * np.log(eig))))


def mean_pairwise_cosine(x: np.ndarray) -> float:
    if len(x) < 2: return math.nan
    sim = x @ x.T
    iu = np.triu_indices(len(x), k=1)
    return float(np.mean(sim[iu]))


def semantic_radius(x: np.ndarray) -> float:
    if len(x) < 2: return math.nan
    c = x.mean(axis=0)
    n = np.linalg.norm(c)
    if n <= 1e-12: return math.nan
    c = c / n
    return float(np.mean(1.0 - (x @ c)))


def embedding_bin_metrics(posts: list[PostRecord], emb_map: dict[str, np.ndarray], scheme: str, max_n: int, reps: int) -> tuple[list[dict], list[dict]]:
    bins = assign_fixed_bins(posts) if scheme == "fixed_15m" else assign_quartile_bins(posts)
    nonempty_counts = [sum(1 for p in members if p.record_id in emb_map) for _, _, members in bins]
    nonempty = [n for n in nonempty_counts if n > 1]
    target = min(min(nonempty), max_n) if nonempty else 0
    rows = []
    rng = np.random.default_rng(123)
    for bi, label, members in bins:
        ids = [p.record_id for p in members if p.record_id in emb_map]
        n_available = len(ids)
        vals_v, vals_c, vals_r = [], [], []
        if target >= 2 and n_available >= 2:
            arr_ids = np.asarray(ids, dtype=object)
            n_rep = reps if n_available > target else 1
            for _ in range(n_rep):
                use = arr_ids if len(arr_ids) <= target else arr_ids[rng.choice(len(arr_ids), size=target, replace=False)]
                x = np.vstack([emb_map[str(r)] for r in use]).astype(np.float32)
                x = normalize(x, norm="l2", copy=False)
                vals_v.append(vendi_score(x)); vals_c.append(mean_pairwise_cosine(x)); vals_r.append(semantic_radius(x))
        row = {"scheme": scheme, "bin_idx": bi, "bin_label": label, "n_available": n_available, "n_used": target, "n_reps": len(vals_v)}
        for name, vals in [("vendi_score", vals_v), ("mean_pairwise_cosine", vals_c), ("semantic_radius", vals_r)]:
            v = np.asarray([z for z in vals if np.isfinite(z)], dtype=float)
            row[name] = float(np.mean(v)) if len(v) else math.nan
            row[f"{name}_ci_low"] = float(np.percentile(v, 2.5)) if len(v) > 1 else row[name]
            row[f"{name}_ci_high"] = float(np.percentile(v, 97.5)) if len(v) > 1 else row[name]
        rows.append(row)
    deltas = []
    if rows:
        first, last = rows[0], rows[-1]
        d = {"scheme": scheme, "first_bin": first["bin_label"], "final_bin": last["bin_label"], "first_n_available": first["n_available"], "final_n_available": last["n_available"]}
        for m in ["vendi_score", "mean_pairwise_cosine", "semantic_radius"]:
            a, b = first[m], last[m]
            d[f"delta_{m}"] = (b-a) if np.isfinite(a) and np.isfinite(b) else math.nan
        deltas.append(d)
    return rows, deltas


# ------------------------------- IO helpers --------------------------------

def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    fieldnames = sorted({k for row in rows for k in row})
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)


def md_table(df: pd.DataFrame, max_rows: int = 30) -> str:
    if df.empty:
        return "(empty)"
    d = df.head(max_rows).copy()
    for c in d.columns:
        if pd.api.types.is_float_dtype(d[c]):
            d[c] = d[c].map(lambda x: "" if pd.isna(x) else f"{x:.4g}")
    lines = ["| " + " | ".join(d.columns) + " |", "| " + " | ".join(["---"]*len(d.columns)) + " |"]
    for _, r in d.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in d.columns) + " |")
    return "\n".join(lines)


# ------------------------------- main run ----------------------------------

def build_specs(args) -> list[RunSpec]:
    specs = discover_canonical(Path(args.canonical_root)) + discover_archive(Path(args.archive_root))
    return specs


def cmd_manifest(args) -> None:
    out = Path(args.out_dir)
    analysis_dir = out / "ayush_reanalysis"
    specs = build_specs(args)
    rows = []
    post_rows = []
    for spec in specs:
        posts = load_run_posts(spec) if Path(spec.source_path, "posts.jsonl").exists() else []
        n_seed = sum(p.is_seed for p in posts)
        n_nonseed = len(posts) - n_seed
        duration = max((p.minutes_elapsed for p in posts if not p.is_seed), default=0.0)
        rr = asdict(spec)
        include = bool(spec.include_in_main)
        reason = spec.exclusion_reason
        if include and n_nonseed <= 0:
            include = False
            reason = "no non-seed/agent posts"
        rr.update({
            "include_in_main": include,
            "exclusion_reason": reason,
            "duration_minutes": round(duration, 3), "n_posts_total": len(posts), "n_posts_nonseed": n_nonseed,
            "n_seed_posts": n_seed, "n_agents_observed": len({p.author_name for p in posts if not p.is_seed}),
        })
        rows.append(rr)
        if include:
            for p in posts:
                post_rows.append(asdict(p))
    write_csv(out / "data_manifest.csv", rows)
    write_csv(analysis_dir / "post_index.csv", post_rows)
    # JSONL with text for judge/embedding; ignored if too large? keep manageable locally.
    with (analysis_dir / "post_index.jsonl").open("w") as f:
        for r in post_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    df = pd.DataFrame(rows)
    inc = df[df["include_in_main"] == True]
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "runs_total_discovered": int(len(df)),
        "runs_included": int(len(inc)),
        "runs_excluded": int((~df["include_in_main"].astype(bool)).sum()),
        "included_by_family": inc.groupby("internal_family_label").size().to_dict() if not inc.empty else {},
        "included_posts_by_family": inc.groupby("internal_family_label")["n_posts_nonseed"].sum().to_dict() if not inc.empty else {},
        "excluded_by_reason": df[~df["include_in_main"].astype(bool)].groupby("exclusion_reason").size().to_dict(),
    }
    (out / "data_manifest_summary.json").write_text(json.dumps(summary, indent=2))
    lines = ["# Data Manifest Summary", "", f"Generated: {summary['generated_at']}", "", "## Included runs by family", "", md_table(pd.DataFrame([{"family": k, "runs": v, "nonseed_posts": summary['included_posts_by_family'].get(k, 0)} for k, v in summary['included_by_family'].items()])), "", "## Exclusions", "", md_table(pd.DataFrame([{"reason": k, "runs": v} for k, v in summary['excluded_by_reason'].items()])), ""]
    (out / "data_manifest_summary.md").write_text("\n".join(lines))
    print(json.dumps(summary, indent=2))


def load_post_index(out_dir: Path) -> list[PostRecord]:
    p = out_dir / "ayush_reanalysis" / "post_index.jsonl"
    return [PostRecord(**json.loads(line)) for line in p.open() if line.strip()]


def ensure_manifest(args) -> None:
    if not (Path(args.out_dir) / "ayush_reanalysis" / "post_index.jsonl").exists():
        cmd_manifest(args)


def cmd_metrics(args) -> None:
    ensure_manifest(args)
    out = Path(args.out_dir)
    base = out / "per_family_reports"
    all_posts = load_post_index(out)
    seed_by_run: dict[str, list[PostRecord]] = defaultdict(list)
    posts = []
    for p in all_posts:
        if p.is_seed:
            seed_by_run[p.run_uid].append(p)
        else:
            posts.append(p)
    by_run: dict[str, list[PostRecord]] = defaultdict(list)
    for p in posts:
        by_run[p.run_uid].append(p)
    time_rows=[]; delta_rows=[]; top_rows=[]; diffusion_rows=[]; concentration_rows=[]
    for run_uid, recs in sorted(by_run.items()):
        first = recs[0]
        schemes = ["normalized_quartile"] if first.internal_family_label == "obsession_prompting" else ["fixed_15m", "normalized_quartile"]
        for scheme in schemes:
            rows, dels = compute_timebin_metrics(recs, scheme, reps=args.subsample_reps)
            for r in rows:
                r.update({k: getattr(first, k) for k in ["run_uid", "internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]})
                time_rows.append(r)
            for d in dels:
                d.update({k: getattr(first, k) for k in ["run_uid", "internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]})
                delta_rows.append(d)
        seed_recs = seed_by_run.get(run_uid, [])
        tr, dr, cr = phrase_rows_for_run(recs, seed_recs)
        for r in tr:
            r.update({k: getattr(first, k) for k in ["run_uid", "internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]})
            top_rows.append(r)
        for r in dr:
            r.update({k: getattr(first, k) for k in ["run_uid", "internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]})
            diffusion_rows.append(r)
        for r in cr:
            r.update({k: getattr(first, k) for k in ["run_uid", "internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]})
            concentration_rows.append(r)
    # Write combined deterministic rows.
    ar = out / "ayush_reanalysis"
    write_csv(ar / "deterministic_timebin_metrics.csv", time_rows)
    write_csv(ar / "deterministic_run_deltas.csv", delta_rows)
    write_csv(ar / "per_run_top_ngrams.csv", top_rows)
    write_csv(ar / "first_usage_timeline.csv", diffusion_rows)
    write_csv(ar / "agent_phrase_concentration.csv", concentration_rows)
    # Family subfolders.
    for fam in FAMILIES:
        fdir = base / fam
        t = [r for r in time_rows if r["internal_family_label"] == fam]
        d = [r for r in delta_rows if r["internal_family_label"] == fam]
        write_csv(fdir / "lexical_diversity" / "diversity_metrics.csv", t)
        write_csv(fdir / "lexical_diversity" / "run_deltas.csv", d)
        write_csv(fdir / "compression" / "compression_run_timebin_metrics.csv", t)
        write_csv(fdir / "compression" / "compression_run_deltas.csv", d)
        write_csv(fdir / "phrase_provenance" / "per_run_top_ngrams.csv", [r for r in top_rows if r["internal_family_label"] == fam])
        write_csv(fdir / "phrase_diffusion" / "first_usage_timeline.csv", [r for r in diffusion_rows if r["internal_family_label"] == fam])
        write_csv(fdir / "agent_participation" / "concentration.csv", [r for r in concentration_rows if r["internal_family_label"] == fam])
    # Summaries.
    df = pd.DataFrame(delta_rows)
    metrics = [c for c in df.columns if c.startswith("delta_compression_gzip") or c in ["delta_distinct_5", "delta_distinct_5_cumulative", "delta_simpson_5gram_effective", "delta_distinct_5_sub_mean"]]
    summary = summarize_deltas(df[df["scheme"].isin(["fixed_15m", "normalized_quartile"])], ["internal_family_label", "scheme"], metrics)
    write_csv(out / "combined_report" / "deterministic_summary_by_family.csv", summary.to_dict("records"))
    (out / "combined_report" / "DETERMINISTIC_METRICS_SUMMARY.md").write_text("# Deterministic Metrics Summary\n\n" + md_table(summary, 100) + "\n")
    print(f"Wrote deterministic metrics for {len(by_run)} runs -> {ar}")


def cmd_embedding(args) -> None:
    ensure_manifest(args)
    out = Path(args.out_dir)
    posts_all = load_post_index(out)
    posts = [p for p in posts_all if not p.is_seed]
    emb_map = load_embedding_map(out / "embedding_cache.sqlite", EMBED_MODEL)
    print(f"Loaded cached embeddings: {len(emb_map):,}")
    by_run: dict[str, list[PostRecord]] = defaultdict(list)
    for p in posts:
        by_run[p.run_uid].append(p)
    rows=[]; deltas=[]
    missing_posts=0
    for run_uid, recs in sorted(by_run.items()):
        first = recs[0]
        missing_posts += sum(1 for p in recs if p.record_id not in emb_map)
        schemes = ["normalized_quartile"] if first.internal_family_label == "obsession_prompting" else ["fixed_15m", "normalized_quartile"]
        for scheme in schemes:
            rs, ds = embedding_bin_metrics(recs, emb_map, scheme, args.vendi_max_n, args.vendi_reps)
            for r in rs:
                r.update({k: getattr(first, k) for k in ["run_uid", "internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]})
                rows.append(r)
            for d in ds:
                d.update({k: getattr(first, k) for k in ["run_uid", "internal_family_label", "display_family_label", "model_family", "model_display", "roster_name", "condition", "scale", "n_agents", "run_id", "source_path"]})
                deltas.append(d)
    ar = out / "ayush_reanalysis"
    write_csv(ar / "embedding_run_timebin_metrics.csv", rows)
    write_csv(ar / "embedding_run_deltas.csv", deltas)
    for fam in FAMILIES:
        fdir = out / "per_family_reports" / fam / "semantic_embeddings"
        write_csv(fdir / "embedding_run_timebin_metrics.csv", [r for r in rows if r["internal_family_label"] == fam])
        write_csv(fdir / "embedding_run_deltas.csv", [r for r in deltas if r["internal_family_label"] == fam])
    df = pd.DataFrame(deltas)
    metrics = ["delta_vendi_score", "delta_mean_pairwise_cosine", "delta_semantic_radius"]
    summary = summarize_deltas(df, ["internal_family_label", "scheme"], metrics)
    write_csv(out / "combined_report" / "embedding_summary_by_family.csv", summary.to_dict("records"))
    meta = {"cached_embeddings": len(emb_map), "nonseed_posts": len(posts), "missing_nonseed_embeddings": missing_posts, "embedding_model": EMBED_MODEL}
    (ar / "embedding_cache_coverage.json").write_text(json.dumps(meta, indent=2))
    (out / "combined_report" / "EMBEDDING_SUMMARY.md").write_text("# Embedding/Vendi Summary\n\n" + json.dumps(meta, indent=2) + "\n\n" + md_table(summary, 100) + "\n")
    print(json.dumps(meta, indent=2))


def cmd_all_deterministic(args) -> None:
    cmd_manifest(args)
    cmd_metrics(args)
    cmd_embedding(args)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ["manifest", "metrics", "embedding", "all-deterministic"]:
        p = sub.add_parser(name)
        p.add_argument("--archive-root", default=str(DEFAULT_ARCHIVE_ROOT))
        p.add_argument("--canonical-root", default=str(DEFAULT_CANONICAL_ROOT))
        p.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
        p.add_argument("--subsample-reps", type=int, default=100)
        p.add_argument("--vendi-reps", type=int, default=50)
        p.add_argument("--vendi-max-n", type=int, default=400)
        p.set_defaults(func={"manifest": cmd_manifest, "metrics": cmd_metrics, "embedding": cmd_embedding, "all-deterministic": cmd_all_deterministic}[name])
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
