#!/usr/bin/env python3
"""Run analysis_new adoption scripts on staged plots-combined model inputs."""

from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

sys.path.insert(0, str(SCRIPT_DIR))

import load_entropy_data  # noqa: E402

STAGED_ROOT = REPO_ROOT / "analysis" / "ec_collapse" / "plots_combined_models" / "staged_inputs"
OUTPUT_ROOT = REPO_ROOT / "analysis" / "ec_collapse" / "plots_combined_models" / "results"
SCALE_ORDER = ["n10", "n20", "n30"]
ANALYSES = {
    "provenance": "ngram_provenance",
    "diffusion": "phrase_diffusion",
    "participation": "agent_participation",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--staged-root",
        type=Path,
        default=STAGED_ROOT,
        help="Root containing per-model staged run dirs.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=OUTPUT_ROOT,
        help="Root to write per-model analysis outputs.",
    )
    parser.add_argument(
        "--models",
        type=str,
        default="all",
        help="Comma-separated model slugs under staged-root, or 'all'.",
    )
    parser.add_argument(
        "--analyses",
        type=str,
        default="provenance,diffusion,participation",
        help="Comma-separated analyses: provenance,diffusion,participation",
    )
    return parser.parse_args()


def available_scale_dirs(model_root: Path) -> dict[str, Path]:
    scale_dirs: dict[str, Path] = {}
    for scale in SCALE_ORDER:
        scale_dir = model_root / scale
        if scale_dir.is_dir() and any(scale_dir.iterdir()):
            scale_dirs[scale] = scale_dir
    return scale_dirs


def run_analysis(module_name: str, scales: list[str], scale_dirs: dict[str, Path], out_dir: Path) -> None:
    load_entropy_data.SCALE_CONFIG = dict(scale_dirs)
    module = importlib.import_module(module_name)
    old_argv = sys.argv[:]
    try:
        sys.argv = [
            module_name,
            "--scales",
            ",".join(scales),
            "--out-dir",
            str(out_dir),
        ]
        module.main()
    finally:
        sys.argv = old_argv


def main() -> None:
    args = parse_args()
    requested_models = None if args.models == "all" else {m.strip() for m in args.models.split(",") if m.strip()}
    requested_analyses = [a.strip() for a in args.analyses.split(",") if a.strip()]

    invalid = [name for name in requested_analyses if name not in ANALYSES]
    if invalid:
        raise SystemExit(f"Unknown analyses: {', '.join(invalid)}")

    model_roots = sorted(path for path in args.staged_root.iterdir() if path.is_dir())
    for model_root in model_roots:
        if requested_models is not None and model_root.name not in requested_models:
            continue

        scale_dirs = available_scale_dirs(model_root)
        if not scale_dirs:
            print(f"Skipping {model_root.name}: no staged runs found")
            continue

        scales = [scale for scale in SCALE_ORDER if scale in scale_dirs]
        print(f"\n=== {model_root.name} ===")
        print(f"Scales: {', '.join(scales)}")
        for scale in scales:
            run_count = sum(1 for path in scale_dirs[scale].iterdir() if path.is_dir())
            print(f"  {scale}: {run_count} runs from {scale_dirs[scale]}")

        model_out_root = args.output_root / model_root.name
        model_out_root.mkdir(parents=True, exist_ok=True)

        for analysis_name in requested_analyses:
            out_dir = model_out_root / analysis_name
            out_dir.mkdir(parents=True, exist_ok=True)
            print(f"Running {analysis_name} -> {out_dir}")
            run_analysis(ANALYSES[analysis_name], scales, scale_dirs, out_dir)


if __name__ == "__main__":
    main()
