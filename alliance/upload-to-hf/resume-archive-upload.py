#!/usr/bin/env python3
"""Resume an interrupted upload_large_folder run."""
import os
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")
os.environ.setdefault("HF_XET_HIGH_PERFORMANCE", "1")

from huggingface_hub import HfApi

REPO_ID = "Ayushnangia/moltbook-archive-2026"
STAGING = "/tmp/moltbook_archive_staging"

api = HfApi()
print(f"Authenticated as: {api.whoami()['name']}")
print(f"Resuming upload_large_folder from existing staging at {STAGING}")
print("(Cache metadata at .cache/huggingface/ will let it skip already-uploaded files)")
print()

api.upload_large_folder(
    folder_path=STAGING,
    repo_id=REPO_ID,
    repo_type="dataset",
    ignore_patterns=[".git/*", ".gitignore", "**/.DS_Store"],
)

print(f"\nDONE — https://huggingface.co/datasets/{REPO_ID}")
