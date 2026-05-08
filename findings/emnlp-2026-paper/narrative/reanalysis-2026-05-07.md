# Reanalysis narrative plan, 2026-05-07

Status: working narrative spine for the EMNLP paper. This restores the original findings story and separates it from the temporary plot-generation workflow.

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

Original claim:

Larger groups do not automatically protect diversity. In the original GPT-5 scale analysis, larger groups showed broader adoption of top phrase families.

Status: generated for review.

Current analysis:

- GPT-5 and Gemini Flash Lite only.
- 10, 20, and 30 agents.
- Agent-generated posts only.
- First 60 minutes only.
- Raw exact NLTK 5-token top phrase anchor per run.
- No seed posts loaded or used.

Current output folder:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step04_scale_phrase_adoption/
```

Generated figure:

```text
scale_phrase_adoption_gpt5_gemini.png
```

Current result to review:

- GPT-5 mean adopters rise from 7.0/10 to 22.0/30, while top-agent share falls from 0.293 to 0.153.
- Gemini Flash Lite mean adopters rise from 6.7/10 to 17.8/30, while top-agent share falls from 0.272 to 0.166.
- Adoption rate is roughly stable for GPT-5 and modestly lower for Gemini, but the absolute number of adopting agents rises with scale for both.

Interpretation candidate:

> Larger groups do not eliminate phrase attractors. The top phrase reaches more agents in larger groups, and repetition becomes less dominated by one agent.

### Finding 6. Phrase attractors can also be topic attractors

Question:

> Are repeated phrases just surface strings, or do they also mark topical concentration?

Claim:

Phrase-family posts can be more topically concentrated than the run as a whole.

Current status:

Not yet rebuilt in the 2026-05-07 final flow.

Candidate metric:

- normalized Simpson or HHI over embedding-cluster shares.

Caution:

Use the term embedding-cluster concentration unless clusters are human-labeled topics.

### Finding 7. Collapse takes different social forms

Question:

> What kind of social pattern is the attractor?

Claim:

Collapse is not one behavior. It can appear as:

1. rhythmic meme;
2. attribution meme;
3. role label;
4. procedural template;
5. shared phrasing or repeated framing.

Current status:

The Step 3 Excalidraw examples support this, but a final paper subsection may need short prose cases.

### Finding 8. Exact n-grams are conservative

Question:

> What does exact matching miss?

Claim:

Exact n-grams capture strong phrase reuse but can miss originators and variants. Sometimes the agent who inspires a phrase is not counted as an adopter because other agents turn that agent into a label.

Paper role:

This should be a limitation or mechanism note, not a headline finding unless quantified.

### Finding 9. Base models and other interventions change the signature but do not obviously solve collapse

Question:

> Do obvious interventions prevent collapse?

Candidates:

1. Base-model-as-tool runs.
2. Mixed-model roster.
3. Obsession prompting.

Current status:

Blocked until the canonical story is stable.

Paper role:

These should be framed as intervention probes, not equal-weight main findings.

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

## Script provenance

Current script folder:

```text
scripts/reanalysis-2026-05-07/
```

Copied scripts:

```text
common.py
step01_canonical_n10_trajectories.py
step02_canonical_n10_trajectories_cumulative.py
step03_canonical_n10_nltk_phrase_repetition.py
```

Original 2026-05-06 step folders are retained as provenance. The 2026-05-07 folder is the clean current working set.

## Next decision

Before making new plots, decide which scale finding to build:

### Option A, recommended

Build phrase-adoption-by-scale plots for GPT-5 and Gemini Flash Lite.

This best matches the original Finding 4.

### Option B

Build scale metric trajectories for gzip, Distinct-5, and LLM collapse.

This is useful, but it answers a weaker version of the scale question.

### Option C

First make run-level delta tables for the current approved figure candidates.

This helps captions and prose but does not add a new visual finding.

Recommendation:

Do Option A next.
