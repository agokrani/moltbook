# Blinded judge materials

This directory contains the exact judge pipeline/rubric, the balanced selected contexts, and a prompt audit. The scored numeric outputs are under `../analysis/results/multijudge_*.csv`.

- `ayush-blind-llm-judge.py` defines the full prompt, forbidden metadata keys, score fields, response normalization, cache schema, and post-hoc aggregation.
- `blind_contexts_240.jsonl` contains the exact 240 blinded context records used for the additional-judge validation. It includes target text and anonymized prior/nearby examples, but no model, condition, run, dataset, or author identity fields.
- `multijudge_sample_metadata.csv` links the blind `row_uid` to analysis metadata only after scoring. Each stored `prompt_sha1` must match its context record.
- `extract_selected_contexts.py` reproducibly filters the 240 rows from the locked full context export without loading that 260 MB file into memory.

Re-running judges is optional, costs money, and may not be bit-reproducible when hosted provider aliases change. The release is designed so reviewers can inspect the exact prompts and outputs offline.
