#!/usr/bin/env python3
"""Run all embedding-based analyses for the base-model experiments.

Handles:
  - Symlinking model-specific NPZ files to the expected embeddings_n10.npz
  - Patching SCALE_CONFIG so load_all_scales() reads from the right directory
  - Patching SCALES, OUT_DIR in each script module
  - Running each analysis
  - Cleaning up symlinks

Usage:
    python3 scripts/analysis_new/run_embedding_analyses.py
    python3 scripts/analysis_new/run_embedding_analyses.py --model qwen-base
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis_new"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "analysis"))

os.environ.setdefault("MPLCONFIGDIR", "/tmp/moltbook-mplconfig")
os.environ.setdefault("XDG_CACHE_HOME", "/tmp/moltbook-cache")

MODELS = ["qwen-base", "qwen-instruct", "gemini-flash-lite"]
FINDINGS_BASE = Path("findings/base-model-experiments")


def patch_scale_config(data_dir: Path):
    """Patch load_entropy_data.SCALE_CONFIG so load_all_scales() uses our data."""
    import load_entropy_data
    load_entropy_data.SCALE_CONFIG = {"n10": data_dir}


def symlink_embeddings(model: str) -> Path:
    """Create embeddings_n10.npz symlink pointing to the model's NPZ."""
    src = REPO_ROOT / f"embeddings_bm_{model}_n10.npz"
    dst = REPO_ROOT / "embeddings_n10.npz"
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    dst.symlink_to(src)
    return dst


def cleanup_symlink():
    dst = REPO_ROOT / "embeddings_n10.npz"
    if dst.is_symlink():
        dst.unlink()


def run_semantic_collapse(model: str, out_dir: Path):
    """semantic_collapse.py — phrase clusters in embedding space."""
    print(f"\n--- semantic_collapse ---")
    import semantic_collapse as mod
    importlib.reload(mod)
    mod.SCALES = ["n10"]
    mod.SCALE_LABELS = {"n10": "10 agents"}
    mod.OUT_DIR = out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        mod.main()
    except Exception as e:
        print(f"  ERROR: {e}")


def run_ngram_embedding_bridge(model: str, out_dir: Path, data_dir: Path):
    """ngram_embedding_bridge.py — do phrase-sharing posts cluster?"""
    print(f"\n--- ngram_embedding_bridge ---")
    import ngram_embedding_bridge as mod
    importlib.reload(mod)
    mod.OUT_DIR = out_dir
    # Point to the model's top_ngrams.json
    mod.TOP_NGRAMS_PATH = FINDINGS_BASE / model / "top_ngrams" / "top_ngrams.json"
    if hasattr(mod, "SCALES"):
        mod.SCALES = ["n10"]
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        mod.main()
    except Exception as e:
        print(f"  ERROR: {e}")


def run_embedding_topic_anchors(model: str, out_dir: Path, data_dir: Path):
    """embedding_topic_anchors.py — topic anchor analysis."""
    print(f"\n--- embedding_topic_anchors ---")
    old_argv = sys.argv
    sys.argv = [
        "embedding_topic_anchors.py",
        "--scales", "n10",
        "--out-dir", str(out_dir),
        "--emb-prefix", f"embeddings_bm_{model}",
        "--data-dir", str(data_dir),
    ]
    import embedding_topic_anchors as mod
    importlib.reload(mod)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        mod.main()
    except Exception as e:
        print(f"  ERROR: {e}")
    finally:
        sys.argv = old_argv


def run_embedding_word_anchors(model: str, out_dir: Path):
    """embedding_word_anchors.py — word anchor proximity analysis."""
    print(f"\n--- embedding_word_anchors ---")
    import embedding_word_anchors as mod
    importlib.reload(mod)
    mod.SCALES = ["n10"]
    mod.OUT_DIR = out_dir
    mod.ANCHOR_CACHE = out_dir / "word_anchor_embeddings.npz"
    if hasattr(mod, "SCALE_ORDER"):
        mod.SCALE_ORDER = {"n10": 0}
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        mod.main()
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, default=None)
    args = parser.parse_args()

    models = [args.model] if args.model else MODELS

    for model in models:
        data_dir = REPO_ROOT / "moltbook-ec-10m-base-model-experiments" / "data" / model
        out_base = FINDINGS_BASE / model
        npz_path = REPO_ROOT / f"embeddings_bm_{model}_n10.npz"

        if not npz_path.exists():
            print(f"SKIP {model}: {npz_path} not found")
            continue

        print(f"\n{'='*60}")
        print(f"  MODEL: {model}")
        print(f"{'='*60}")

        symlink_embeddings(model)
        patch_scale_config(data_dir)

        try:
            run_semantic_collapse(model, out_base / "semantic_collapse")
            run_ngram_embedding_bridge(model, out_base / "ngram_embedding_bridge", data_dir)
            run_embedding_topic_anchors(model, out_base / "embedding_topic_anchors", data_dir)
            run_embedding_word_anchors(model, out_base / "embedding_word_anchors")
        finally:
            cleanup_symlink()

        print(f"\nDone: {model}")

    print(f"\n{'='*60}")
    print(f"All embedding analyses complete.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
