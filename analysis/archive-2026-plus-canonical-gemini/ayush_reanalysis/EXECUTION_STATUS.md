# Ayush Reanalysis Execution Status

Generated/updated: 2026-05-04

## Completed

Final reanalysis is complete on the reviewed local source set.

Included scope:

- `single_model_final`: 48 canonical runs / 38,490 non-seed posts
- `mixed_model_roster`: 6 qwen3.5 frontier-mixed runs / 2,189 non-seed posts
- `base_model_as_tool`: 18 curated base-model runs / 5,137 non-seed posts
- `obsession_prompting`: 9 curated obsession runs / 3,845 non-seed posts

Excluded:

- `qwen3.6-plus` frontier-mixed variant: 1 run

Source mapping:

- Single-model final: `exports/huggingface/agokrani/moltbook-entropy-collapse-canonical-48`
- Mixed-model roster: `exports/huggingface/Ayushnangia/moltbook-frontier-mixed-1h`, qwen3.5 variant only
- Base model as tool: `exports/huggingface/Ayushnangia/moltbook-curated-20260505/2026-05-05/base-model`
- Obsession prompting: `exports/huggingface/Ayushnangia/moltbook-curated-20260505/2026-05-05/obsession`

Completed analyses:

- manifest generation and validation
- deterministic run-level metrics
- Qwen embedding/Vendi metrics
- blinded LLM-as-judge context generation and prompt audit
- blinded LLM-as-judge scoring and aggregation
- per-family reports
- combined deterministic, embedding, and LLM-judge summaries
- PNG/PDF checkpoint figures
- final report: `FINAL_REPORT.md`

Embedding status:

- Embedding model: `qwen/qwen3-embedding-8b`
- Current included non-seed rows: 49,661
- Missing current embeddings: 0
- Existing canonical-48 embeddings were reused by row ID.
- Curated copied-run embeddings were reused by exact text hash where possible; only remaining missing current rows were embedded.

Judge status:

- Judge model: `google/gemini-3.1-flash-lite-preview`
- Current included non-seed rows: 49,661
- Unique current judge row IDs: 49,656
- Judged current row IDs: 49,656 / 49,656
- Post-level joined rows after aggregation: 49,661 / 49,661
- Existing canonical-48 judgments were reused by row ID.
- New/current non-single rows were scored under the same metadata-blind prompt protocol.
- Prompt audit passed; prompts contain post text and anonymized context but no run/group/model/condition/path/source metadata.

Large local caches/context files remain ignored by git.
