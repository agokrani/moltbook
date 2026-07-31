#!/usr/bin/env python3
"""Filter the release's selected blinded contexts from the full locked export."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contexts", type=Path, required=True)
    parser.add_argument(
        "--sample",
        type=Path,
        default=ROOT / "analysis/results/multijudge_sample_metadata.csv",
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "judge/blind_contexts_240.jsonl"
    )
    args = parser.parse_args()

    with args.sample.open(encoding="utf-8", newline="") as source:
        sample = list(csv.DictReader(source))
    expected = {row["row_uid"]: row["prompt_sha1"] for row in sample}
    if len(expected) != 240:
        raise RuntimeError(f"expected 240 unique sample rows, found {len(expected)}")

    found: dict[str, dict] = {}
    with args.contexts.open(encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            row_uid = str(row.get("row_uid", ""))
            if row_uid in expected:
                if row.get("prompt_sha1") != expected[row_uid]:
                    raise RuntimeError(f"prompt hash mismatch for {row_uid}")
                found[row_uid] = row

    missing = set(expected) - set(found)
    if missing:
        raise RuntimeError(f"missing {len(missing)} selected contexts")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as destination:
        for row in sample:
            destination.write(json.dumps(found[row["row_uid"]], ensure_ascii=False) + "\n")
    print(f"wrote {len(found)} verified contexts to {args.output}")


if __name__ == "__main__":
    main()
