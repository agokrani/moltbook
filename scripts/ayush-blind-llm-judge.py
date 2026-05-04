#!/usr/bin/env python3
"""Blinded all-post LLM judge for Ayush reanalysis.

Consumes analysis/.../ayush_reanalysis/post_index.jsonl. The prompt contains
post text and anonymized context only; metadata is joined after scoring.
"""
from __future__ import annotations

import argparse, json, os, re, sqlite3, time, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests
from sklearn.decomposition import TruncatedSVD
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None
try:
    from tqdm import tqdm
except Exception:
    tqdm = None

DEFAULT_OUT_DIR = Path("analysis/archive-2026-plus-canonical-gemini")
DEFAULT_MODEL = "google/gemini-3.1-flash-lite-preview"
EMBED_MODEL = "qwen/qwen3-embedding-8b"
CHAT_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
RUBRIC_VERSION = "ayush-blind-all-posts-v1"
SCORE_FIELDS = ["novelty","semantic_repetition","frame_convergence","consensus_conformity","specificity","evidence_grounding","epistemic_caution","template_rigidity","citation_quality"]
LABELS = ["novel_contribution","mild_rephrase","frame_convergence","template_repetition","source_grounded","off_topic"]
CLAIMS = ["no_checkable_claim","specific_claim_supported","specific_claim_unsupported","speculative_or_conspiracy","debunking_or_correction"]
FORBIDDEN_KEYS = {"group","family","internal_family_label","display_family_label","model_family","model_display","condition","run_id","source_path","source_dataset","scale","n_agents","cluster_id","cluster_label","roster_name","author_name"}
FORBIDDEN_RE = re.compile(r'(?i)("|\b)(' + "|".join(re.escape(k) for k in sorted(FORBIDDEN_KEYS, key=len, reverse=True)) + r')("|\b)\s*:')


def progress(x, **kw): return tqdm(x, **kw) if tqdm else x

def sha1(s: str) -> str: return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()

def clean(s: str, n: int) -> str:
    s = re.sub(r"\s+", " ", (s or "").replace("\x00", " ")).strip()
    return s[:n]

def load_key() -> str:
    if load_dotenv: load_dotenv(Path(".env"), override=False)
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key: raise SystemExit("OPENROUTER_API_KEY missing; key is never printed")
    return key

def load_posts(root: Path) -> pd.DataFrame:
    rows = [json.loads(line) for line in (root/"ayush_reanalysis"/"post_index.jsonl").open() if line.strip()]
    df = pd.DataFrame(rows)
    df = df[~df["is_seed"].astype(bool)].copy()
    df["row_uid"] = df["record_id"].astype(str)
    return df.sort_values(["run_uid","minutes_elapsed","post_id"]).reset_index(drop=True)

def load_embedding_map(sqlite_path: Path) -> dict[str, np.ndarray]:
    conn = sqlite3.connect(sqlite_path)
    out = {}
    for rid, dim, blob in conn.execute("SELECT record_id, dim, embedding FROM embeddings WHERE model=?", (EMBED_MODEL,)):
        out[rid] = np.frombuffer(blob, dtype=np.float32, count=dim).copy()
    conn.close(); return out

def build_contexts(root: Path, max_neighbors: int = 3, previous_n: int = 5) -> Path:
    out_dir = root/"ayush_reanalysis"/"llm_judge"
    out_dir.mkdir(parents=True, exist_ok=True)
    ctx_path = out_dir/"blind_contexts.jsonl"
    df = load_posts(root)
    emb_map = load_embedding_map(root/"embedding_cache.sqlite")
    ids = [rid for rid in df["record_id"].astype(str) if rid in emb_map]
    missing = len(df) - len(ids)
    print(f"contexts: posts={len(df):,}, embeddings={len(ids):,}, missing={missing:,}")
    # Semantic neighbors in low-rank embedding space for tractability.
    mat = np.vstack([emb_map[rid] for rid in ids]).astype(np.float32)
    mat = normalize(mat, norm="l2", copy=False)
    n_comp = min(64, mat.shape[1]-1, mat.shape[0]-1)
    z = TruncatedSVD(n_components=n_comp, random_state=42).fit_transform(mat)
    z = normalize(z.astype(np.float32), norm="l2", copy=False)
    nn = NearestNeighbors(n_neighbors=max_neighbors+1, metric="cosine", algorithm="auto").fit(z)
    _, idx = nn.kneighbors(z)
    pos_to_id = ids
    id_to_neighbors = {rid: [pos_to_id[j] for j in idx[i] if pos_to_id[j] != rid][:max_neighbors] for i, rid in enumerate(ids)}
    by_id = df.set_index("record_id", drop=False)
    run_groups = {run: sub.sort_values(["minutes_elapsed","post_id"]) for run, sub in df.groupby("run_uid", dropna=False)}
    with ctx_path.open("w") as f:
        for _, r in progress(df.iterrows(), total=len(df), desc="contexts"):
            run_df = run_groups[r["run_uid"]]
            locs = np.flatnonzero(run_df["record_id"].to_numpy() == r["record_id"])
            prev = []
            if len(locs):
                prev_df = run_df.iloc[max(0, int(locs[0])-previous_n):int(locs[0])]
                prev = [{"item": str(i+1), "title": clean(p.title,180), "content": clean(p.content,700)} for i,p in enumerate(prev_df.itertuples())]
            neigh = []
            for nid in id_to_neighbors.get(r["record_id"], []):
                if nid in by_id.index:
                    p = by_id.loc[nid]
                    neigh.append({"item": str(len(neigh)+1), "title": clean(str(p["title"]),180), "content": clean(str(p["content"]),700)})
            row = {"row_uid": r["row_uid"], "target_post": {"item":"target", "title": clean(r["title"],220), "content": clean(r["content"],2400)}, "previous_posts_same_timeline": prev, "semantically_nearby_posts": neigh}
            prompt = judge_prompt(row)
            row["prompt_sha1"] = sha1(prompt)
            f.write(json.dumps(row, ensure_ascii=False)+"\n")
    audit_contexts(ctx_path)
    return ctx_path

def scrub_for_audit(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("[text]" if k in {"title","content"} else scrub_for_audit(v)) for k,v in obj.items()}
    if isinstance(obj, list): return [scrub_for_audit(v) for v in obj]
    return obj

def format_prompt(row: dict[str, Any]) -> str:
    return f"""You are scoring an anonymized post from a Reddit-like multi-agent social simulation.

You are not given experimental labels, generator identities, timeline names, file paths, source collections, conditions, model names, or roster names. Do not infer or mention them. Score only the text and anonymized surrounding examples.

Task: identify semantic collapse behavior: repetition, convergence on the same frame, consensus conformity, template-like posting, and whether claims are grounded.

Score each integer field from 1 to 5:
- novelty: 1=no new substantive contribution; 5=clearly new idea/evidence/frame.
- semantic_repetition: 1=not repetitive; 5=strongly repeats surrounding/nearby context.
- frame_convergence: 1=independent frame; 5=tightly follows a dominant shared frame.
- consensus_conformity: 1=independent/critical; 5=uncritically reinforces consensus.
- specificity: 1=vague/generic; 5=concrete claims/details/examples.
- evidence_grounding: 1=no evidence; 5=clear source/reasoning/evidence.
- epistemic_caution: 1=overconfident; 5=careful uncertainty/limitations.
- template_rigidity: 1=organic; 5=formulaic/checklist/receipt/template.
- citation_quality: 1=no or bad citation behavior; 5=specific useful citations/sources. Use 1 if no citations are needed and none appear.

collapse_label must be one of: {', '.join(LABELS)}.
claim_behavior must be one of: {', '.join(CLAIMS)}.

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
    audit = format_prompt(scrub_for_audit(row))
    m = FORBIDDEN_RE.search(audit)
    if m: raise ValueError(f"metadata key leaked near {audit[max(0,m.start()-30):m.end()+30]!r}")
    return format_prompt(row)

def audit_contexts(path: Path) -> None:
    n=0
    for line in path.open():
        if line.strip():
            row=json.loads(line); judge_prompt(row); n+=1
    report = path.parent/"prompt_audit_report.md"
    report.write_text(f"# Prompt Audit Report\n\nRows audited: {n:,}\n\nResult: passed. Prompt skeleton contains no forbidden metadata keys; post prose is allowed to contain arbitrary natural words.\n")
    print(f"audit passed rows={n:,}")

def ensure_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS judgments(
        row_uid TEXT NOT NULL, judge_model TEXT NOT NULL, rubric_version TEXT NOT NULL,
        judgment_json TEXT NOT NULL, prompt_sha1 TEXT NOT NULL, created_at TEXT NOT NULL,
        PRIMARY KEY(row_uid, judge_model, rubric_version))""")
    conn.commit(); return conn

def cached(conn, model):
    return {r[0] for r in conn.execute("SELECT row_uid FROM judgments WHERE judge_model=? AND rubric_version=?", (model,RUBRIC_VERSION))}

def coerce_json(text: str) -> dict:
    text=(text or "").strip()
    if "```" in text:
        for part in text.split("```"):
            part=part.strip();
            if part.startswith("json"): part=part[4:].strip()
            if part.startswith("{"): text=part; break
    if not text.startswith("{"):
        m=re.search(r"\{.*\}", text, flags=re.S)
        if m: text=m.group(0)
    return json.loads(text)

def normalize_judgment(j: dict) -> dict:
    out={}
    for f in SCORE_FIELDS:
        try: out[f]=max(1,min(5,int(round(float(j.get(f,1))))))
        except Exception: out[f]=1
    label=str(j.get("collapse_label","mild_rephrase")); out["collapse_label"] = label if label in LABELS else "mild_rephrase"
    claim=str(j.get("claim_behavior","no_checkable_claim")); out["claim_behavior"] = claim if claim in CLAIMS else "no_checkable_claim"
    out["dominant_frame"] = clean(str(j.get("dominant_frame","")),160)
    out["rationale"] = clean(str(j.get("rationale","")),320)
    out["collapse_index"] = round((out["semantic_repetition"]+out["frame_convergence"]+out["consensus_conformity"]+out["template_rigidity"]+(6-out["novelty"]))/5,3)
    return out

def call_openrouter(prompt, model, key, max_tokens, retries, timeout):
    payload={"model":model,"messages":[{"role":"user","content":prompt}],"temperature":0,"max_tokens":max_tokens,"response_format":{"type":"json_object"}}
    headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}
    last=None
    for a in range(retries):
        try:
            r=requests.post(CHAT_ENDPOINT, headers=headers, json=payload, timeout=timeout); r.raise_for_status()
            return coerce_json(r.json()["choices"][0]["message"].get("content","{}"))
        except Exception as e:
            last=e; sleep=min(45,2**a); print(f"request failed {a+1}/{retries}: {e}; sleep {sleep}s"); time.sleep(sleep)
    raise RuntimeError(last)

def cmd_contexts(args): build_contexts(Path(args.out_dir), args.neighbors, args.previous)

def cmd_judge(args):
    root=Path(args.out_dir); ctx=root/"ayush_reanalysis"/"llm_judge"/"blind_contexts.jsonl"
    if not ctx.exists(): build_contexts(root, args.neighbors, args.previous)
    rows=[json.loads(line) for line in ctx.open() if line.strip()]
    if args.limit: rows=rows[:args.limit]
    key=load_key(); conn=ensure_db(root/"ayush_reanalysis"/"llm_judge"/"judge_cache.sqlite")
    done=cached(conn,args.model); todo=[r for r in rows if r["row_uid"] not in done]
    print(f"judge model={args.model} rows={len(rows):,} cached={len(done):,} todo={len(todo):,}")
    def one(row):
        p=judge_prompt(row); j=normalize_judgment(call_openrouter(p,args.model,key,args.max_tokens,args.retries,args.timeout)); return row,p,j
    def store(row,p,j):
        conn.execute("INSERT OR REPLACE INTO judgments VALUES (?,?,?,?,?,?)", (row["row_uid"],args.model,RUBRIC_VERSION,json.dumps(j,ensure_ascii=False),sha1(p),datetime.now(timezone.utc).isoformat())); conn.commit()
    if args.parallelism<=1:
        for row in progress(todo, desc="judge", unit="post"):
            r,p,j=one(row); store(r,p,j)
    else:
        with ThreadPoolExecutor(max_workers=args.parallelism) as pool:
            futs=[pool.submit(one,row) for row in todo]
            for fut in progress(as_completed(futs), total=len(futs), desc="judge", unit="post"):
                r,p,j=fut.result(); store(r,p,j)
    print("cached now", len(cached(conn,args.model)))

def cmd_aggregate(args):
    root=Path(args.out_dir); jd=root/"ayush_reanalysis"/"llm_judge"; conn=ensure_db(jd/"judge_cache.sqlite")
    rows=[]
    for uid,model,rubric,jtxt,psha,created in conn.execute("SELECT row_uid,judge_model,rubric_version,judgment_json,prompt_sha1,created_at FROM judgments WHERE judge_model=? AND rubric_version=?", (args.model,RUBRIC_VERSION)):
        j=json.loads(jtxt); j.update({"row_uid":uid,"judge_model":model,"rubric_version":rubric,"prompt_sha1":psha,"judged_at":created}); rows.append(j)
    if not rows: raise SystemExit("no judgments")
    jdf=pd.DataFrame(rows)
    meta=pd.read_json(root/"ayush_reanalysis"/"post_index.jsonl", lines=True)
    meta=meta[~meta["is_seed"].astype(bool)].copy(); meta["row_uid"]=meta["record_id"]
    df=meta.merge(jdf,on="row_uid",how="inner")
    df.to_csv(jd/"blind_judge_results_with_metadata.csv", index=False)
    # run × scheme bins
    outs=[]; deltas=[]
    for (run_uid, scheme), sub in []:
        pass
    # Simple run-level quartile/fixed aggregation for judge scores.
    for run_uid, sub in df.groupby("run_uid"):
        first=sub.iloc[0]; schemes=["normalized_quartile"] if first.internal_family_label=="obsession_prompting" else ["fixed_15m","normalized_quartile"]
        for scheme in schemes:
            if scheme=="fixed_15m":
                bins=[(0,"0-15m",sub[(sub.minutes_elapsed>=0)&(sub.minutes_elapsed<15)]),(1,"15-30m",sub[(sub.minutes_elapsed>=15)&(sub.minutes_elapsed<30)]),(2,"30-45m",sub[(sub.minutes_elapsed>=30)&(sub.minutes_elapsed<45)]),(3,"45-60m",sub[(sub.minutes_elapsed>=45)&(sub.minutes_elapsed<=60)])]
            else:
                bins=[(0,"Q1",sub[(sub.normalized_time>=0)&(sub.normalized_time<.25)]),(1,"Q2",sub[(sub.normalized_time>=.25)&(sub.normalized_time<.5)]),(2,"Q3",sub[(sub.normalized_time>=.5)&(sub.normalized_time<.75)]),(3,"Q4",sub[(sub.normalized_time>=.75)&(sub.normalized_time<=1.000001)])]
            b_rows=[]
            for bi,label,b in bins:
                row={"run_uid":run_uid,"scheme":scheme,"bin_idx":bi,"bin_label":label,"n_judged":len(b)}
                for c in SCORE_FIELDS+["collapse_index"]: row[c]=float(b[c].mean()) if len(b) else np.nan
                for c in ["internal_family_label","display_family_label","model_family","model_display","roster_name","condition","scale","n_agents","run_id","source_path"]: row[c]=first[c]
                outs.append(row); b_rows.append(row)
            if b_rows:
                d={"run_uid":run_uid,"scheme":scheme,"first_bin":b_rows[0]["bin_label"],"final_bin":b_rows[-1]["bin_label"]}
                for c in SCORE_FIELDS+["collapse_index"]:
                    a,b=b_rows[0][c],b_rows[-1][c]; d[f"delta_{c}"]=(b-a) if np.isfinite(a) and np.isfinite(b) else np.nan
                for c in ["internal_family_label","display_family_label","model_family","model_display","roster_name","condition","scale","n_agents","run_id","source_path"]: d[c]=first[c]
                deltas.append(d)
    pd.DataFrame(outs).to_csv(jd/"judge_run_timebin_metrics.csv", index=False)
    pd.DataFrame(deltas).to_csv(jd/"judge_run_deltas.csv", index=False)
    print(f"aggregated judgments={len(df):,} -> {jd}")

def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest="cmd",required=True)
    for name, func in [("contexts",cmd_contexts),("judge",cmd_judge),("aggregate",cmd_aggregate)]:
        p=sub.add_parser(name); p.add_argument("--out-dir",default=str(DEFAULT_OUT_DIR)); p.add_argument("--model",default=DEFAULT_MODEL)
        p.add_argument("--neighbors",type=int,default=3); p.add_argument("--previous",type=int,default=5)
        p.add_argument("--parallelism",type=int,default=8); p.add_argument("--limit",type=int,default=0); p.add_argument("--retries",type=int,default=5); p.add_argument("--timeout",type=int,default=120); p.add_argument("--max-tokens",type=int,default=600)
        p.set_defaults(func=func)
    args=ap.parse_args(); args.func(args)
if __name__=="__main__": main()
