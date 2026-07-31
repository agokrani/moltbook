# Prompt audit report

- Locked full context export: 49,661 rows, 260,513,065 bytes, SHA-256 `0028d11aaa6f82c3f4f0c07c9bd4defbd6600a17f1451d064b4562b76dc97d12`.
- Selected validation export: 240 rows, 1,399,475 bytes, SHA-256 `f5498413ab80d724012cc66eca712198c333e852e3d8051f26daa04aee1f2b33`.
- Selection keys: exactly the 240 unique `row_uid` values in `multijudge_sample_metadata.csv`.
- Hash check: every selected context's stored `prompt_sha1` matches the sample metadata and the prompt regenerated from the exact included rubric.
- Metadata check: no selected context object contains model, condition, run, source, author, roster, scale, family, or cluster identity fields.

Result: passed.
