#!/usr/bin/env python3
"""Download only the allowlisted post exports needed for agent_sessions_1h.json."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, expected: str) -> None:
    if destination.is_file() and sha256(destination) == expected:
        print("verified", destination)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "moltbook-artifact/1"})
    with urllib.request.urlopen(request) as response, temporary.open("wb") as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
    actual = sha256(temporary)
    if actual != expected:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"checksum mismatch for {destination}: {actual} != {expected}")
    os.replace(temporary, destination)
    print("downloaded", destination)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "cache")
    parser.add_argument("--lock", type=Path, default=ROOT / "datasets.lock.json")
    args = parser.parse_args()

    lock = json.loads(args.lock.read_text(encoding="utf-8"))
    count = 0
    for dataset in lock["datasets"]:
        for relative, expected in dataset["required_files"].items():
            quoted = "/".join(urllib.parse.quote(part) for part in relative.split("/"))
            url = (
                "https://huggingface.co/datasets/"
                f"{dataset['repo_id']}/resolve/{dataset['revision']}/{quoted}"
            )
            destination = args.output / dataset["local_dir"] / relative
            download(url, destination, expected)
            count += 1
    print(f"verified {count} allowlisted files under {args.output}")


if __name__ == "__main__":
    main()
