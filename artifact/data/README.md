# Data inventory and retrieval policy

`datasets.lock.json` records immutable Hugging Face revisions. For the Reddit-baseline rebuild it also records the SHA-256 of every required post export. `download_baseline_inputs.py` retrieves only those 28 allowlisted `posts.jsonl` files.

The files under `manifests/` describe the broader 81-run reanalysis bundle and its local integrity validation. They do not imply that raw logs, SQL dumps, embeddings, caches, or credentials are included in this Git release.

Some upstream dataset repositories contain operational logs or database exports in addition to paper data. Do not mirror a full repository by default. Prefer the allowlisted downloader, inspect text before public redistribution, and retain the dataset license and revision in derived releases.

The 24-session `analysis/results/agent_sessions_1h.json` is a derived, compact analysis input containing normalized generated text, model-family labels, run labels, and counts. It contains no API keys, database dumps, Reddit text, or human participant data.
