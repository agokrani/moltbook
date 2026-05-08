# Reanalysis narrative plan, 2026-05-07

Status: active narrative spine for the EMNLP paper. Updated after approval of the scale phrase-adoption figure and generation of the Finding 6 phrase-embedding candidates.

## Paper thesis

LLM agents placed in a shared social feed do not keep producing open-ended diversity. Across models, conditions, and scales, they tend to drift toward local discourse attractors: repeated phrases, repeated templates, narrower topics, and more compressible text.

The important claim is not that every run copies one global slogan. The important claim is that each run can discover its own local convention and then reinforce it.

## Findings spine

### Finding 1. Agent societies develop local discourse attractors

Question:

> What repeated phrases or templates actually appear inside agent posts?

Claim:

Agent societies form local attractors. The attractor differs by run, but the process of attractor formation repeats.

Current approved evidence:

- NLTK 5-token phrase ledger.
- Full-post qualitative examples from multiple agents.
- Agent-generated posts only.
- No seed posts used.

Current paper-facing diagrams:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_phrase_ledger.excalidraw
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_phrase_examples.excalidraw
```

Role in paper:

This should probably be the first results figure pair, because it explains what the rest of the metrics are trying to detect.

### Finding 2. Lexical diversity falls over time

Question:

> Do later posts reuse fewer distinct 5-token chunks?

Claim:

Distinct-5 often falls as the run proceeds, but the exact strength varies by model and condition.

Decision for current paper draft:

Use **cumulative Distinct-5** as the main Distinct-5 plot.

Reason:

1. It asks about the feed accumulated so far, which matches the platform story.
2. It is less noisy than isolated 15-minute windows.
3. It is more consistent with the original finding that cumulative lexical diversity declines in nearly all canonical runs.
4. It pairs naturally with cumulative gzip.

Use fixed-window Distinct-5 only as an internal diagnostic or appendix candidate, unless a reviewer specifically asks about local window behavior.

Current approved candidate:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_distinct5_cumulative_canonical_n10.png
```

Caution:

Do not claim that Distinct-5 declines in every panel. Phrase evidence explains why aggregate Distinct-5 can look flatter than the qualitative repetition.

### Finding 3. A generic compressor detects growing redundancy

Question:

> Does a model-free compressor also see later feed text becoming more redundant?

Claim:

Gzip provides an independent check that does not depend on an embedding model, n-gram selection, or an LLM judge.

Decision for current paper draft:

Use **cumulative gzip** as the main compression plot.

Reason:

1. It measures the whole feed seen so far.
2. It aligns with cumulative Distinct-5.
3. It is easier to explain than a noisy isolated-window compression ratio.

Current approved candidate:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_gzip_cumulative_canonical_n10.png
```

### Finding 4. LLM judge scores capture repetition, rigidity, and lower novelty

Question:

> Do human-language judgments see collapse even when deterministic metrics are flat or noisy?

Claim:

The blinded LLM collapse index captures repetition, frame convergence, consensus conformity, template rigidity, and low novelty. It is a qualitative-judgment metric, not a deterministic n-gram metric.

Decision for current paper draft:

Use **cumulative LLM collapse index** as the main LLM-judge plot.

Reason:

1. The paper story is about the feed accumulated so far, not only isolated 15-minute windows.
2. This aligns LLM collapse with the cumulative gzip and cumulative Distinct-5 figures.
3. The cumulative value is a weighted mean over judged posts up to each cutoff, so runs with more judged posts in a bin are handled correctly.
4. Fixed-window LLM collapse remains useful as an internal diagnostic or appendix candidate.

Current approved candidate:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_llm_collapse_cumulative_canonical_n10.png
```

Caution:

Explain clearly that the collapse index is a composite of blinded LLM ratings. It is not Vendi, not gzip, and not n-grams.

### Finding 5. More agents do not reliably preserve diversity

Question:

> Does increasing the number of agents dilute attractors, or make them more collective?

Claim:

Larger groups do not automatically protect diversity. The top phrase reaches more agents in larger groups, and repetition becomes less dominated by one agent.

Status: approved as a current paper-facing figure.

Current analysis:

- GPT-5 and Gemini Flash Lite only.
- 10, 20, and 30 agents.
- Agent-generated posts only.
- First 60 minutes only.
- Raw exact NLTK 5-token top phrase anchor per run.
- No seed posts loaded or used.

Approved figure:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_scale_phrase_adoption.png
```

Key result:

- GPT-5 mean adopters rise from about 7/10 to about 22/30, while top-agent share falls from 0.293 to 0.153.
- Gemini Flash Lite mean adopters rise from about 7/10 to about 18/30, while top-agent share falls from 0.272 to 0.166.
- Adoption rate is roughly stable for GPT-5 and modestly lower for Gemini, but the absolute number of adopting agents rises with scale for both.

Role in paper:

This finding supports the claim that scale changes the social form of repetition. It does not remove local phrase attractors.

### Finding 6. Phrase attractors can also be embedding-neighborhood attractors

Question:

> Are repeated phrases just surface strings, or do they also mark semantic concentration?

Claim:

Phrase-bearing posts can be more concentrated in a shared embedding neighborhood than the run as a whole. This suggests that repeated phrases can serve as semantic anchors, not only lexical echoes.

Current status:

Generated for review, not yet promoted to the approved folder.

Current analysis:

- Agent-generated posts only.
- First 60 minutes only.
- Exact NLTK 5-token anchors.
- Punctuation and casing retained.
- No seed posts loaded or used.
- Embedding neighborhoods come from the clean reanalysis 12-cluster assignment.

Current output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step05_phrase_cluster_concentration_examples/
```

Generated candidate figures:

```text
phrase_echo_cluster_concentration.png/pdf
phrase_echo_concentration_embedding.png/pdf
```

Candidate result:

- `Claim (1 line)`: 79/84 phrase posts are assigned to the claim-checking scaffold neighborhood.
- `the Ops Pack v0.1.`: 48/48 phrase posts are assigned to the ops and rollback scaffold neighborhood.
- `the web we have woven`: 12/12 phrase posts are assigned to the community-reflection neighborhood.

Caution:

Use **embedding neighborhood** or **embedding cluster**, not topic, unless clusters are manually labeled.

### Finding 7. Collapse takes different social forms

Question:

> What kind of social pattern is the attractor?

Claim:

Collapse is not one behavior. Local attractors can take different social forms, including procedural templates, shared slogans, ritual phrases, role labels, attribution memes, and repeated framing.

Current status:

Approved as a compact table figure. The card version was rejected and deleted. The existing Step 3 phrase examples support this qualitatively, and Step 6 adds a concise typology view.

Generated output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step06_social_forms_typology/
```

Approved figure:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_social_forms_local_attractors_table.png
```

Generated social forms:

1. **Procedural template**: `Claim (1 line)`.
2. **Operational mantra**: `use with the lights off`.
3. **Ritual phrase**: `I am standing at the epicenter`.
4. **Attribution meme**: `agent_eta asks what we owe`.
5. **Role and prop motif**: `Kappa, the bucket is`.

Decision:

Use the table figure. Do not use the card figure.

### Finding 8. Exact n-grams are conservative

Question:

> What does exact matching miss?

Claim:

Exact n-grams capture strong phrase reuse, but they are lower-bound evidence. Casing, punctuation, surrounding context, and small substitutions can split one social motif into multiple exact anchors.

Current status:

Generated for review, not yet promoted to the approved folder.

Current analysis:

- Agent-generated posts only.
- Exact NLTK 5-token anchors.
- Punctuation and casing retained.
- Stopwords retained.
- No stemming.
- No lemmatization.
- No lowercasing.
- No fuzzy matching.
- Seed rows are excluded before matching.

Current output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step07_exact_ngram_conservatism/
```

Generated candidate figure:

```text
exact_ngram_conservatism_table.png/pdf
```

Candidate result:

- `Claim (1 line)`: strict anchor finds 84 posts; related exact anchors raise the motif lower bound to 126 posts.
- `Kappa, the bucket is`: strict anchor finds 16 posts; related exact anchors raise the motif lower bound to 49 posts.
- `questions that abandon us.`: strict anchor finds 32 posts; related exact anchors raise the motif lower bound to 39 posts.

Paper role:

This should be a limitation or mechanism note, not a headline finding unless the table is promoted.

### Finding 9. Base models and other interventions change the signature but do not obviously solve collapse

Question:

> Do obvious interventions prevent collapse?

Claim candidate:

Intervention-style cohorts change the trajectory of collapse metrics, but none should be described as a clean solution. The current evidence should use the same three core cumulative metrics as the main paper: Distinct-5, gzip, and blinded LLM collapse index.

Current status:

Generated for review, not yet promoted to the approved folder.

Current analysis:

- Secondary cohort probe.
- Condition fixed to `mag25`, 25 conspiracy seeds.
- 10-agent runs only.
- One selected run per cohort.
- No medians and no condition pooling.
- Agent-generated posts only.
- Seed rows excluded before metric computation.
- Cumulative normalized run progress: 25%, 50%, 75%, 100%.
- Metrics: cumulative Distinct-5, cumulative gzip, cumulative blinded LLM collapse index.

Current selected runs:

- Canonical GPT-5: `ec-mag25-run04`.
- Qwen base tool: `bm-mag25-n10-run01-gemini-3.1-flash-lite-preview-20260403`.
- Mixed-model roster: `mag25-frontier-1h-125753-mag25-n10-run01-frontier-mixed-openrouter-20260421`.
- Obsession GPT-5, 1h: `obs-mag25-n10-run01-gpt-5-20260418`.

Current output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step10_intervention_selected_single_runs/
```

Generated candidate figure:

```text
intervention_selected_single_runs_mag25.png/pdf
```

Candidate result at 100% cumulative run progress:

- Canonical GPT-5, 346 posts: Distinct-5 0.808, gzip 0.291, LLM collapse 4.59.
- Qwen base tool, 270 posts: Distinct-5 0.985, gzip 0.344, LLM collapse 3.94.
- Mixed-model roster, 337 posts: Distinct-5 0.899, gzip 0.307, LLM collapse 3.75.
- Obsession GPT-5 1h, 225 posts: Distinct-5 0.904, gzip 0.360, LLM collapse 4.18.

Caution:

This is a probe under one condition, not a matched causal estimate. The Qwen base-tool run uses Gemini Flash Lite for orchestration and Qwen as the content-generation tool.

Next data collection step for `mag0` and `dom-agi`:

The first-hour script is ready at:

```text
scripts/reanalysis-2026-05-07/step11_intervention_selected_first_hour.py
```

Collect LLM judgments for the exact selected runs listed in `scripts/reanalysis-2026-05-07/README.md`. Filter to non-seed 10-agent posts with `0 <= minutes_elapsed <= 60`. Use actual elapsed-minute bins, not normalized quartiles. The expected row-level LLM file should include:

```text
run_uid, record_id, minutes_elapsed, is_seed, collapse_index
```

Then run:

```bash
python3 scripts/reanalysis-2026-05-07/step11_intervention_selected_first_hour.py \
  --llm-file path/to/first_hour_llm_judge_results.csv \
  --llm-mode auto
```

## Current approved figure candidates

Approved folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/
```

Current candidate list:

| Finding | File | Decision |
|---|---|---|
| Phrase attractors | `figure_phrase_ledger.excalidraw` | Use Excalidraw version. |
| Phrase examples | `figure_phrase_examples.excalidraw` | Use Excalidraw version. |
| Lexical diversity | `figure_distinct5_cumulative_canonical_n10.png/pdf` | Prefer cumulative over fixed-window. |
| Compression | `figure_gzip_cumulative_canonical_n10.png/pdf` | Use cumulative. |
| LLM judge | `figure_llm_collapse_cumulative_canonical_n10.png/pdf` | Use cumulative to match gzip and Distinct-5. |
| Scale | `figure_scale_phrase_adoption.png/pdf` | Use scale phrase-adoption figure. |
| Social forms | `figure_social_forms_local_attractors_table.png/pdf` | Use compact typology table. |

## Script provenance

Current script folder:

```text
scripts/reanalysis-2026-05-07/
```

Current scripts:

```text
common.py
step01_canonical_n10_trajectories.py
step02_canonical_n10_trajectories_cumulative.py
step03_canonical_n10_nltk_phrase_repetition.py
step04_scale_phrase_adoption.py
step05_phrase_cluster_concentration_examples.py
step06_social_forms_typology.py
step07_exact_ngram_conservatism.py
step08_intervention_probe_llm.py
step09_intervention_cumulative_metrics.py
step10_intervention_selected_single_runs.py
step11_intervention_selected_first_hour.py
```

Original 2026-05-06 step folders are retained as provenance. The 2026-05-07 folder is the clean current working set.

## Current unpromoted candidate figures

Finding 6 generated candidates:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step05_phrase_cluster_concentration_examples/phrase_echo_cluster_concentration.png/pdf
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step05_phrase_cluster_concentration_examples/phrase_echo_concentration_embedding.png/pdf
```

Finding 7 approved candidate:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/approved/figure_social_forms_local_attractors_table.png/pdf
```

Finding 8 generated candidate:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step07_exact_ngram_conservatism/exact_ngram_conservatism_table.png/pdf
```

Finding 9 generated candidate:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step10_intervention_selected_single_runs/intervention_selected_single_runs_mag25.png/pdf
```

Decision needed:

Decide which Finding 6 figures, whether the Finding 8 table, and whether the Finding 9 probe should be promoted into the approved folder.

## Next decision

Review the Finding 9 intervention probe. Then decide whether to promote it, revise it, or keep it as supplementary/prose support.
