#!/usr/bin/env python3
"""Upload experiment data to HuggingFace"""

import sys
import os
from huggingface_hub import HfApi, login

def main():
    if len(sys.argv) < 3:
        print("Usage: python upload-to-hf.py <repo_id> <export_dir>")
        print("Example: python upload-to-hf.py Ayushnangia/civiclens-turbo-experiment exports/turbo-v1")
        sys.exit(1)

    repo_id = sys.argv[1]
    export_dir = sys.argv[2]

    if not os.path.exists(export_dir):
        print(f"Error: Directory {export_dir} not found")
        sys.exit(1)

    print(f"Uploading {export_dir} to {repo_id}...")

    # Login (will prompt for token if not already logged in)
    try:
        api = HfApi()
        # Check if logged in
        api.whoami()
    except Exception:
        print("\nYou need to log in to HuggingFace.")
        print("Get your token from: https://huggingface.co/settings/tokens")
        token = input("Enter your HuggingFace token: ").strip()
        login(token=token)
        api = HfApi()

    # Create repo if it doesn't exist
    try:
        api.create_repo(repo_id, repo_type="dataset", exist_ok=True)
        print(f"Repository {repo_id} ready")
    except Exception as e:
        print(f"Note: {e}")

    # Upload folder
    api.upload_folder(
        folder_path=export_dir,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=f"Upload experiment data from {os.path.basename(export_dir)}"
    )

    print(f"\nSuccess! Dataset available at:")
    print(f"https://huggingface.co/datasets/{repo_id}")

if __name__ == "__main__":
    main()
