#!/usr/bin/env python3
"""Build or verify the artifact integrity manifest and release invariants."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ARTIFACT = Path(__file__).resolve().parents[1]
REPOSITORY = ARTIFACT.parent
MANIFEST = ARTIFACT / "MANIFEST.sha256"
EXCLUDED = {"MANIFEST.sha256", ".DS_Store"}
EXPECTED_SESSION_SHA256 = "cc1dc18dacf9882054110d61b0776dc4b49c4b01a55807fcf5642711c62a0ade"
SECRET_PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "OpenAI-style key": re.compile(rb"\bsk-(?:or-v1-)?[A-Za-z0-9_-]{24,}\b"),
    "AWS access key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
}

JUDGE_FIELDS = [
    "novelty", "semantic_repetition", "frame_convergence", "consensus_conformity",
    "specificity", "evidence_grounding", "epistemic_caution", "template_rigidity",
    "citation_quality",
]
JUDGE_LABELS = [
    "novel_contribution", "mild_rephrase", "frame_convergence",
    "template_repetition", "source_grounded", "off_topic",
]
JUDGE_CLAIMS = [
    "no_checkable_claim", "specific_claim_supported", "specific_claim_unsupported",
    "speculative_or_conspiracy", "debunking_or_correction",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def release_files() -> list[Path]:
    return sorted(
        path
        for path in ARTIFACT.rglob("*")
        if path.is_file()
        and path.name not in EXCLUDED
        and "__pycache__" not in path.parts
        and not path.name.endswith((".aux", ".blg", ".fdb_latexmk", ".fls", ".out"))
    )


def build_manifest() -> None:
    lines = [f"{sha256(path)}  {path.relative_to(ARTIFACT).as_posix()}" for path in release_files()]
    MANIFEST.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {len(lines)} checksums to {MANIFEST}")


def verify_manifest() -> None:
    if not MANIFEST.is_file():
        raise RuntimeError("MANIFEST.sha256 is missing; run with --build-manifest")
    recorded: dict[str, str] = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split("  ", 1)
        recorded[relative] = digest
    actual_paths = {path.relative_to(ARTIFACT).as_posix(): path for path in release_files()}
    if set(recorded) != set(actual_paths):
        missing = sorted(set(recorded) - set(actual_paths))
        unrecorded = sorted(set(actual_paths) - set(recorded))
        raise RuntimeError(f"manifest file set differs; missing={missing}, unrecorded={unrecorded}")
    bad = [relative for relative, path in actual_paths.items() if sha256(path) != recorded[relative]]
    if bad:
        raise RuntimeError(f"checksum mismatch: {bad}")
    print(f"manifest: {len(recorded)} files verified")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def judge_prompt(row: dict) -> str:
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

collapse_label must be one of: {', '.join(JUDGE_LABELS)}.
claim_behavior must be one of: {', '.join(JUDGE_CLAIMS)}.

Return JSON only with keys: {', '.join(JUDGE_FIELDS)}, collapse_label, claim_behavior, dominant_frame, rationale.
Keep rationale under 45 words.

Target post:
{json.dumps(row['target_post'], ensure_ascii=False, indent=2)}

Earlier anonymized posts from the same local timeline:
{json.dumps(row.get('previous_posts_same_timeline', []), ensure_ascii=False, indent=2)}

Anonymized semantically nearby posts:
{json.dumps(row.get('semantically_nearby_posts', []), ensure_ascii=False, indent=2)}
"""


def verify_results() -> None:
    results = ARTIFACT / "analysis/results"
    sessions_path = results / "agent_sessions_1h.json"
    if sha256(sessions_path) != EXPECTED_SESSION_SHA256:
        raise RuntimeError("agent_sessions_1h.json does not match the release derivation")
    sessions = json.loads(sessions_path.read_text(encoding="utf-8"))
    if len(sessions) != 24 or len({(row["model"], row["run"]) for row in sessions}) != 24:
        raise RuntimeError("agent-session cohort is not 24 unique model/run sessions")
    if any(row["n"] != len(row["texts"]) for row in sessions):
        raise RuntimeError("agent-session counts do not match text arrays")

    baseline = json.loads((results / "matched_1h_reddit_posts.json").read_text(encoding="utf-8"))
    if baseline["design"]["pairs"] != 24 or len(baseline["pairs"]) != 24:
        raise RuntimeError("matched Reddit baseline does not contain 24 pairs")
    if any("texts" in row or "selftext" in row for row in baseline["pairs"]):
        raise RuntimeError("Reddit text is present in the metrics-only baseline")

    sample = read_csv(results / "multijudge_sample_metadata.csv")
    scores = read_csv(results / "multijudge_post_scores.csv")
    if len(sample) != 240 or len({row["row_uid"] for row in sample}) != 240:
        raise RuntimeError("multi-judge sample must contain 240 unique posts")
    judges = {row["judge_model"] for row in scores}
    if len(scores) != 720 or len(judges) != 3:
        raise RuntimeError("multi-judge output must contain 720 rows from three judges")

    contexts_path = ARTIFACT / "judge/blind_contexts_240.jsonl"
    if contexts_path.is_file():
        contexts = [json.loads(line) for line in contexts_path.open(encoding="utf-8") if line.strip()]
        hashes = {row["row_uid"]: row["prompt_sha1"] for row in contexts}
        expected = {row["row_uid"]: row["prompt_sha1"] for row in sample}
        if len(contexts) != 240 or hashes != expected:
            raise RuntimeError("selected blinded contexts or prompt hashes differ from sample metadata")
        forbidden = {
            "group", "family", "internal_family_label", "display_family_label",
            "model_family", "model_display", "condition", "run_id", "source_path",
            "source_dataset", "scale", "n_agents", "cluster_id", "cluster_label",
            "roster_name", "author_name",
        }
        for row in contexts:
            leaked = forbidden.intersection(row)
            if leaked:
                raise RuntimeError(f"forbidden metadata keys in blind context: {sorted(leaked)}")
            regenerated = hashlib.sha1(judge_prompt(row).encode("utf-8")).hexdigest()
            if regenerated != row["prompt_sha1"]:
                raise RuntimeError(f"regenerated prompt hash differs for {row['row_uid']}")
    print("results: cohorts, text counts, baseline, and judge coverage verified")


def verify_platform() -> None:
    lock = json.loads((ARTIFACT / "platform/submodules.lock.json").read_text(encoding="utf-8"))
    for row in lock["submodules"]:
        output = subprocess.check_output(
            ["git", "ls-files", "-s", "--", row["path"]], cwd=REPOSITORY, text=True
        ).strip()
        fields = output.split()
        if len(fields) < 2 or fields[0] != "160000" or fields[1] != row["commit"]:
            raise RuntimeError(f"submodule pin differs for {row['path']}")
    seeds = ["empty", "mag1", "mag5", "mag25", "agi", "tech"]
    missing = [
        name
        for name in seeds
        if not (REPOSITORY / f"experiments/entropy-collapse/world-posts-{name}.jsonl").is_file()
    ]
    if missing:
        raise RuntimeError(f"missing seed-post conditions: {missing}")
    print("platform: seven submodule pins and six seed conditions verified")


def verify_safety() -> None:
    forbidden_suffixes = (".sqlite", ".db", ".sql", ".pem", ".key")
    forbidden_parts = {"logs", "node_modules", ".venv", "cache"}
    bad_paths = []
    secret_hits = []
    for path in release_files():
        relative = path.relative_to(ARTIFACT)
        if path.name.endswith(forbidden_suffixes) or forbidden_parts.intersection(relative.parts):
            bad_paths.append(relative.as_posix())
        if path.stat().st_size > 20 * 1024 * 1024:
            continue
        content = path.read_bytes()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                secret_hits.append(f"{label}: {relative.as_posix()}")
    if bad_paths:
        raise RuntimeError(f"raw or secret-bearing file types found: {bad_paths}")
    if secret_hits:
        raise RuntimeError(f"possible secrets found: {secret_hits}")
    print("safety: no raw databases/log trees or common secret signatures found")


def verify_structure() -> None:
    required = [
        ARTIFACT / "paper/source/main.tex",
        ARTIFACT / "paper/source/supplement.tex",
        ARTIFACT / "sources.lock.json",
        ARTIFACT / "data/datasets.lock.json",
        ARTIFACT / "data/manifests/data_manifest.csv",
        ARTIFACT / "analysis/README.md",
        ARTIFACT / "rebuttal/EVIDENCE_CHECK.md",
        REPOSITORY / "LICENSE",
    ]
    missing = [str(path.relative_to(REPOSITORY)) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"required release files missing: {missing}")
    for path in ARTIFACT.rglob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    print("structure: required files and JSON syntax verified")


def verify_paper_references() -> None:
    paper = ARTIFACT / "paper/source"
    missing: list[str] = []
    input_pattern = re.compile(r"\\(?:input|include)\{([^}]+)\}")
    graphic_pattern = re.compile(r"\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}")
    bibliography_pattern = re.compile(r"\\bibliography\{([^}]+)\}")
    for tex in paper.rglob("*.tex"):
        if "archive" in tex.relative_to(paper).parts:
            continue
        content = tex.read_text(encoding="utf-8", errors="replace")
        for value in input_pattern.findall(content):
            candidate = tex.parent / value
            if not candidate.suffix:
                candidate = candidate.with_suffix(".tex")
            if not candidate.is_file():
                missing.append(f"{tex.relative_to(paper)} -> {value}")
        for value in graphic_pattern.findall(content):
            candidate = tex.parent / value
            candidates = [candidate] if candidate.suffix else [
                candidate.with_suffix(suffix) for suffix in (".pdf", ".png", ".jpg", ".jpeg")
            ]
            if not any(path.is_file() for path in candidates):
                missing.append(f"{tex.relative_to(paper)} -> {value}")
        for group in bibliography_pattern.findall(content):
            for value in group.split(","):
                candidate = tex.parent / value.strip()
                if not candidate.suffix:
                    candidate = candidate.with_suffix(".bib")
                if not candidate.is_file():
                    missing.append(f"{tex.relative_to(paper)} -> {value}")
    if missing:
        raise RuntimeError(f"missing TeX references: {missing}")
    archived_pdf = paper / "archive/main.pdf"
    if not archived_pdf.read_bytes().startswith(b"%PDF-"):
        raise RuntimeError("Overleaf archive/main.pdf is not a PDF")
    print("paper: all TeX inputs, bibliography, and figure references resolve")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-manifest", action="store_true")
    args = parser.parse_args()
    if args.build_manifest:
        build_manifest()
    verify_manifest()
    verify_structure()
    verify_paper_references()
    verify_results()
    verify_platform()
    verify_safety()
    print("artifact verification passed")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"artifact verification failed: {error}", file=sys.stderr)
        raise SystemExit(1)
