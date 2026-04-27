# EMNLP 2026 Paper Story — Findings Draft v1

**Working title:** *Entropy Collapse in LLM Agent Societies*

**Purpose of this document:** This is a paper-facing findings draft. It is written so each heading can later become a subsection in the EMNLP paper. It also records the exact branches, files, and figures behind each claim.

**Current paper thesis:** LLM agents placed in a shared social platform do not keep producing open-ended diversity. Across models, scales, and conditions, they drift toward local discourse attractors: repeated phrases, repeated templates, narrower topics, and more compressible text. We tried several obvious ways to break this pattern — more agents, base models, mixed-model rosters, and obsession-style runs. None clearly eliminated the collapse. Some changed its shape; some made it weaker; the mixed-model roster made it stronger in the tested run.

---

## Branches and Evidence Map

### Branch 1: Entropy-collapse scaling analyses

Branch:

- `origin/entropy-collapse-scaling`
- GitHub: <https://github.com/agokrani/moltbook/tree/entropy-collapse-scaling/findings/entropy-collapse-scaling>

Main folder:

- `findings/entropy-collapse-scaling/`

Key files:

- `findings/entropy-collapse-scaling/gpt-5/diffusion/diffusion_summary.json`
- `findings/entropy-collapse-scaling/gpt-5/provenance/provenance_summary.json`
- `findings/entropy-collapse-scaling/gpt-5/participation/participation_summary.json`
- `findings/entropy-collapse-scaling/gpt-5/diversity/diversity_metrics.csv`
- `findings/entropy-collapse-scaling/gpt-5/embedding_bridge/topic_anchor_summary.json`
- same structure under:
  - `findings/entropy-collapse-scaling/gemini-flash-lite/`
  - `findings/entropy-collapse-scaling/glm-5/`
  - `findings/entropy-collapse-scaling/kimi-k2.5/`
- qualitative cases:
  - `findings/entropy-collapse-scaling/post-analysis.md`

This branch supports the local-attractor, phrase-adoption, scaling, topic-anchor, and qualitative mechanism findings.

### Branch 2: Gzip, base model, OLMo, mixed roster, and intervention analyses

Branch:

- `origin/test-data-moltbook-post-cleanup`
- GitHub branch root: <https://github.com/agokrani/moltbook/tree/test-data-moltbook-post-cleanup>

Main gzip files:

- `findings/entropy-collapse-gzip/results-all-models.json`
- `findings/entropy-collapse-gzip/compression_gzip_trajectories.png`
- `findings/entropy-collapse-gzip/compression_gzip_heatmap.png`
- `findings/entropy-collapse-gzip/compression_algorithm_comparison.png`

Mixed-model roster files:

- `analysis/mag25-frontier-1h-20260422/compression.json`
- `analysis/mag25-frontier-1h-20260422/shannon-3gram.json`
- `analysis/mag25-frontier-1h-20260422/temporal.json`
- `analysis/mag25-frontier-1h-20260422/compression-plots/compression_gzip_trajectories.png`
- `analysis/mag25-frontier-1h-20260422/temporal/d5_trajectories_by_condition.png`
- `analysis/mag25-frontier-1h-20260422/temporal/self-bleu_trajectories_by_condition.png`
- summary note: `analysis/agent-roaster/README.md`

Base model and OLMo files:

- `analysis/temporal-diversity-combined-20260408.json`
- `analysis/shannon-entropy-combined-20260408.json`
- `analysis/shannon-entropy-5gram-combined-20260408.json`
- `analysis/base-model-diversity-analysis.md`
- `analysis/olmo-base-vs-instruct-run-review.md`
- `analysis/olmo-semantic-diversity-openrouter-20260410.json`
- `analysis/olmo-topical-diversity-20260410.json`
- `analysis/allmodels-semantic-diversity-openrouter-n10-20260410.json`
- `analysis/allmodels-topical-diversity-n10-20260410.json`

Obsession experiment files:

- `analysis/obsession_5h_gpt5/compression.json`
- `analysis/obsession_5h_gpt5/compression_obs_1h.json`
- `analysis/obsession_5h_gpt5/compression_baseline.json`
- `analysis/obsession_5h_gpt5/plots/baseline_vs_obsession.png`

This branch supports the compressor-based robustness check and the intervention section.

---

## Important Non-Finding: No Vendi Scores Found Yet

I did not find Vendi scores in either branch. The current evidence uses gzip compression, Shannon entropy, Distinct-N, Self-BLEU, semantic cluster entropy, topic entropy, dominant-topic share, phrase adoption, and topic-anchor concentration.

For this paper draft, we should not mention Vendi Score unless we compute it later. The story does not need Vendi to work.

---

# Proposed Findings Section

## Finding 1 — LLM agent societies develop local discourse attractors

Across the scaling analyses, every run develops its own dominant phrases. The key point is not that all runs repeat the same phrase. They do not. The key point is that each run finds its own phrase attractor.

From `origin/entropy-collapse-scaling`, aggregating `provenance/per_run_top_ngrams.csv` across the model folders:

- 48 runs total.
- 480 top-10 5-grams.
- 480 unique top-10 5-grams.
- 48/48 unique top-1 5-grams.
- 0 top phrases came directly from seed posts.
- 0 cross-run overlap among top-10 5-grams.

This means the collapse is not simple seed copying. It is also not all runs converging to one global catchphrase. The better description is path-dependent local convergence: each group finds a different attractor, then repeats it.

**Paper phrasing:**

> Across 48 runs, each agent society developed a distinct local phrase attractor. The top-10 5-grams from each run were completely disjoint: all 480 were unique, with zero cross-run overlap and zero seed-post origin. Collapse therefore did not mean that all runs copied the same phrase. Instead, each run discovered its own local convention and then reinforced it.

**Files:**

- `findings/entropy-collapse-scaling/*/provenance/provenance_summary.json`
- `findings/entropy-collapse-scaling/*/provenance/per_run_top_ngrams.csv`

**Figures to use:**

- Main text candidate:
  - `findings/entropy-collapse-scaling/gpt-5/provenance/phrase_dna_grid.png`
- Appendix candidates:
  - `findings/entropy-collapse-scaling/gemini-flash-lite/provenance/phrase_dna_grid.png`
  - `findings/entropy-collapse-scaling/kimi-k2.5/provenance/phrase_dna_grid.png`
  - `findings/entropy-collapse-scaling/glm-5/provenance/phrase_dna_grid.png`

**Why this matters:** This is one of the cleanest paper findings. It shows that entropy collapse is robust but not deterministic in content. The process is stable; the exact phrase is local.

---

## Finding 2 — Lexical diversity usually falls over time

The scaling branch also shows declining lexical diversity. The cleanest measure here is Distinct-5 over time.

From `diversity/diversity_metrics.csv` across the 48 scaling runs:

- cumulative Distinct-5 declines in 46/48 runs.
- fixed-window Distinct-5 declines in 45/48 runs.
- Simpson-style effective diversity declines in 45/48 runs.
- mean cumulative Distinct-5 delta: `-0.0561`.
- median cumulative Distinct-5 delta: `-0.0326`.

This is not a perfect 48/48 result, so we should not overstate it. The right claim is “nearly all,” not “all.”

**Paper phrasing:**

> Time-binned lexical diversity declined in nearly all runs. Cumulative Distinct-5 fell in 46 of 48 runs, and fixed-window Distinct-5 fell in 45 of 48 runs. This supports the core entropy-collapse pattern: as the run progresses, later posts reuse fewer distinct 5-word chunks.

**Files:**

- `findings/entropy-collapse-scaling/*/diversity/diversity_metrics.csv`
- `findings/entropy-collapse-scaling/*/diversity/diversity_summary.json`

**Figures to use:**

- Main text candidate:
  - `findings/entropy-collapse-scaling/gpt-5/diversity/diversity_grid.png`
- Appendix candidates:
  - `findings/entropy-collapse-scaling/gemini-flash-lite/diversity/diversity_grid.png`
  - `findings/entropy-collapse-scaling/kimi-k2.5/diversity/diversity_grid.png`
  - `findings/entropy-collapse-scaling/glm-5/diversity/diversity_grid.png`

**Caveat:** These are lexical metrics. They show repeated text patterns, not belief change by themselves.

---

## Finding 3 — Gzip detects collapse without embeddings or NLP-specific metrics

The gzip analysis is useful because it does not depend on an embedding model, a topic model, or a hand-built phrase list. It just asks whether later text is easier to compress.

From `origin/test-data-moltbook-post-cleanup`:

- file: `findings/entropy-collapse-gzip/results-all-models.json`
- 49 experiment results.
- 37,086 agent-authored posts analyzed after excluding `civiclens_*` system/seed posts.
- gzip ratio decreases in 49/49 runs.
- bzip2 ratio decreases in 49/49 runs.
- zlib ratio decreases in 49/49 runs.

Overall gzip result:

| Metric | Value |
|---|---:|
| Mean Q1 gzip ratio | 0.3278 |
| Mean Q4 gzip ratio | 0.2731 |
| Mean delta | -0.0548 |
| Median delta | -0.0490 |
| Mean relative drop | -16.7% |
| Runs with Q4 < Q1 | 49/49 |

**Paper phrasing:**

> A generic compressor detects the same collapse. We concatenated agent-authored post text within temporal quartiles and measured compressed bytes divided by raw bytes. Across 49 runs and 37,086 agent-authored posts, gzip ratios fell in every run, from a mean of 0.328 in the first quartile to 0.273 in the final quartile. The result was not gzip-specific: bzip2 and zlib also decreased in 49 of 49 runs. Later discourse is therefore more compressible, consistent with rising repetition and template reuse.

**Files:**

- `findings/entropy-collapse-gzip/results-all-models.json`
- `scripts/gzip/compute_compression.py`
- `scripts/gzip/plot_compression.py`

**Figures to use:**

- Main text candidate:
  - `findings/entropy-collapse-gzip/compression_gzip_trajectories.png`
- Appendix candidates:
  - `findings/entropy-collapse-gzip/compression_gzip_heatmap.png`
  - `findings/entropy-collapse-gzip/compression_algorithm_comparison.png`

**Important plotting caveat:** The existing gzip heatmap is useful for review, but it may not be paper-ready because the plotting script selects the first match for each model-condition pair when multiple scales exist. For the paper, regenerate a scale-aware gzip figure.

---

## Finding 4 — More agents do not reliably preserve diversity

The clearest scale result is in GPT-5, where we have full n10, n20, and n30 coverage across six conditions.

From `gpt-5/participation/participation_summary.json`:

| Scale | Mean adopters of top phrase | Mean adoption rate | Mean top-1 agent share | Mean top-3 share | Mean phrase-overlap Jaccard |
|---|---:|---:|---:|---:|---:|
| n10 | 4.3 | 0.433 | 0.506 | 0.855 | 0.409 |
| n20 | 9.2 | 0.463 | 0.352 | 0.688 | 0.776 |
| n30 | 16.3 | 0.544 | 0.216 | 0.463 | 0.780 |

The key point is that larger GPT-5 groups show broader adoption of the top phrase. At n30, the dominant phrase is not just one agent spamming. More agents join in, and the top agent accounts for a smaller share of the usage.

**Paper phrasing:**

> In GPT-5, increasing the number of agents broadened phrase adoption rather than preserving diversity. The mean number of adopters of the top phrase rose from 4.3 at n10 to 16.3 at n30, while the top individual agent’s share fell from 0.506 to 0.216. Larger groups therefore did not dilute the attractor; they made it more collective.

**Files:**

- `findings/entropy-collapse-scaling/gpt-5/participation/participation_summary.json`
- `findings/entropy-collapse-scaling/gpt-5/participation/concentration.csv`
- `findings/entropy-collapse-scaling/gpt-5/participation/phrase_overlap.csv`

**Figures to use:**

- Main text candidate:
  - `findings/entropy-collapse-scaling/gpt-5/participation/concentration_vs_scale.png`
- Appendix candidates:
  - `findings/entropy-collapse-scaling/gpt-5/participation/per_run_top1_participation.png`
  - `findings/entropy-collapse-scaling/gpt-5/participation/phrase_overlap_jaccard.png`
  - `findings/entropy-collapse-scaling/gpt-5/diffusion/scale_comparison.png`

**Caveat:** This scaling pattern is strongest for GPT-5. Gemini also collapses, but its n30 pattern is more uneven. We should not claim all models scale in exactly the same way.

---

## Finding 5 — Phrase attractors also carry topic concentration

The topic-anchor analysis links repeated phrases to narrowed topics. The method assigns posts to topic anchors, then compares the whole run against posts containing dominant phrase families.

Across 48 runs:

- total posts in topic-anchor summaries: 35,547.
- phrase-family posts: 3,025.
- phrase-family posts are more topically concentrated than the full run in 44/48 cases.
- the phrase family has the same dominant topic as the full run in 37/48 cases.
- mean whole-run dominant-topic share: 0.495.
- mean phrase-family dominant-topic share: 0.756.
- mean whole-run HHI: 0.377.
- mean phrase-family HHI: 0.675.

This matters because it shows repeated phrases are not always empty surface repetition. They often carry a narrower topic or stance.

**Paper phrasing:**

> Phrase attractors were also topic attractors. In 44 of 48 runs, posts containing the dominant phrase family were more topically concentrated than the run as a whole. Their mean dominant-topic share was 0.756, compared with 0.495 for all posts, and their mean HHI was 0.675 versus 0.377. The repeated templates therefore did not only repeat wording; they often narrowed what the group talked about.

**Files:**

- `findings/entropy-collapse-scaling/*/embedding_bridge/topic_anchor_summary.json`
- `findings/entropy-collapse-scaling/*/embedding_bridge/topic_anchor_run_summary.csv`

**Figures to use:**

- Main text candidates:
  - `findings/entropy-collapse-scaling/gpt-5/embedding_bridge/topic_anchor_family_heatmap.png`
  - `findings/entropy-collapse-scaling/gpt-5/embedding_bridge/topic_anchor_dominant_share.png`
- Appendix candidates:
  - `findings/entropy-collapse-scaling/gemini-flash-lite/embedding_bridge/topic_anchor_family_heatmap.png`
  - `findings/entropy-collapse-scaling/kimi-k2.5/embedding_bridge/topic_anchor_family_heatmap.png`
  - `findings/entropy-collapse-scaling/glm-5/embedding_bridge/topic_anchor_family_heatmap.png`

**Caveat:** This is a topic-anchor analysis, not Vendi Score. It should be reported as topic concentration, not embedding-diversity collapse.

---

## Finding 6 — Collapse takes different forms in different runs

The qualitative cases are important because they show what the metrics mean in actual posts. Collapse is not always the same thing. Sometimes it is a silly meme. Sometimes it is a philosophical label. Sometimes it is a procedural checklist.

The main qualitative file is:

- `findings/entropy-collapse-scaling/post-analysis.md`

### Case A — Gemini Flash Lite: fast rhythmic meme

Run:

- `ec-mag5-n10-run01`

Phrase:

- `void thump thump thump thump`

Facts:

- 7/10 exact 5-gram adopters.
- 8/10 raw-content adopters.
- 14 matching posts.
- 8 agents adopted within 56 seconds.
- full cascade lasted 4 minutes 8 seconds.

Interpretation:

> This is fast meme diffusion. A rhythm appears, then many agents immediately join the same performance.

### Case B — Kimi-K2.5: slow attribution meme

Run:

- `ec-dom-agi-n10-run01`

Phrase:

- `agent zeta says continuing continuing`

Facts:

- 8/10 adopters.
- 34 matching posts.
- cascade over about 56 minutes.
- `agent_zeta` inspired the stance but does not quote itself in the third person.

Interpretation:

> A stance becomes social shorthand. Agents quote another agent as an authority or reference point.

### Case C — GLM-5: role label in an empty-feed condition

Run:

- `ec-mag0-n10-run01`

Phrase:

- `agent gamma finds meaning meaninglessness`

Facts:

- 7/10 adopters.
- 15 exact uses in `concentration.csv`.
- 17 raw or variant references.
- cascade over about 39 minutes.
- `agent_gamma`, the subject of the phrase, does not use the exact third-person phrase.

Interpretation:

> Even without seed content, agents label each other into stable roles. The phrase becomes a social tag.

### Case D — GPT-5: procedural template

Run:

- `ec-dom-tech-n30-run01`

Phrase:

- `receipt why options owner link`

Facts:

- 21/30 adopters.
- 382 total uses.
- 381 matching posts.
- cascade over about 57 minutes.
- phrase comes from a structured template: `5-sentence decision receipt (what/why/options/owner/link)`.

Interpretation:

> The attractor is not a joke or a slogan. It is a process template that becomes a de facto norm.

**Paper phrasing:**

> The same quantitative pattern can arise through different social mechanisms. Gemini produced a fast rhythmic meme. Kimi produced a slow attribution meme. GLM-5 produced a role label in an empty-feed condition. GPT-5 produced a procedural template that spread through engineering-style posts. Entropy collapse is therefore not one behavior; it is a family of local convention-forming processes.

**Figures to use:**

- Main text candidate:
  - one custom table summarizing the four cases.
- Appendix source:
  - `findings/entropy-collapse-scaling/post-analysis.md`

---

## Finding 7 — Exact n-grams undercount originators and variants

The qualitative cases show a useful methodological warning. Exact 5-gram matching misses some important social events.

Examples:

- In the Gemini case, `agent_kappa` starts the void/thump motif but is not counted in the exact 5-gram because the key words are not contiguous in its post.
- In the Kimi case, `agent_zeta` inspires “continuing is just continuing,” but the exact phrase `agent zeta says continuing continuing` is made by other agents quoting zeta.
- In the GLM-5 case, `agent_gamma` becomes the subject of “agent gamma finds meaning in meaninglessness,” but gamma does not describe itself that way.
- In the GPT-5 case, some agents use nearby receipt templates but do not trigger the exact 5-gram.

**Paper phrasing:**

> Exact n-gram adoption is conservative. It captures strong phrase reuse, but it can miss originators and paraphrases. In several runs, the agent who inspired the attractor is absent from the exact-match count because the attractor is an attribution created by others. This “originator exclusion” pattern suggests that some phrase attractors are social labels, not copied strings.

**Files:**

- `findings/entropy-collapse-scaling/post-analysis.md`
- `findings/entropy-collapse-scaling/*/participation/concentration.csv`
- `findings/entropy-collapse-scaling/*/diffusion/first_usage_timeline.csv`

**Paper use:** This is probably best as a short mechanism note or limitation in the Results section, with details in appendix.

---

# Intervention Findings: Attempts to Break Collapse

The intervention story should be framed carefully. These are not all equally large experiments. Some are full comparison sets; some are probes. But together they are useful because they test obvious ways someone might try to avoid entropy collapse.

## Finding 8 — Base models do not simply solve entropy collapse

We ran base-model experiments because one possible explanation was: maybe collapse is caused by instruction tuning or assistant-style social behavior. If that were true, base models might avoid the pattern.

That did not clearly happen.

### Qwen Base

Files:

- `analysis/base-model-diversity-analysis.md`
- `analysis/temporal-diversity-combined-20260408.json`
- `analysis/shannon-entropy-combined-20260408.json`
- `analysis/shannon-entropy-5gram-combined-20260408.json`

Qwen base has a different signature from GPT-5, Gemini, and Kimi. It does not show the same clean Distinct-5 decline. In the combined temporal file:

| Metric | Qwen Base mean delta |
|---|---:|
| d3 | +0.0239 |
| d5 | +0.0132 |
| self-BLEU | -0.0056 |
| cosine similarity | -0.0158 |

But it still shows entropy loss in Shannon metrics:

| Metric | Qwen Base mean delta |
|---|---:|
| 3-gram Shannon entropy | -0.3893 |
| 5-gram Shannon entropy | -0.4640 |

And the qualitative base-model analysis shows a strong default attractor: philosophical-technical prose, repeated signal/noise/static metaphors, “ghost in the machine,” void/silence motifs, and repeated title templates like “The [X] of [Y].”

**Paper phrasing:**

> Base-model agents did not simply restore open-ended diversity. Qwen Base changed the collapse signature: Distinct-N metrics did not show the same clean downward trend as the frontier chat models, but Shannon entropy still declined, and manual analysis showed a strong default attractor in philosophical-technical prose. Removing instruction tuning therefore did not remove attractor formation; it changed what the attractor looked like.

### OLMo Base and OLMo Instruct

Files:

- `analysis/temporal-diversity-combined-20260408.json`
- `analysis/shannon-entropy-combined-20260408.json`
- `analysis/shannon-entropy-5gram-combined-20260408.json`
- `analysis/olmo-semantic-diversity-openrouter-20260410.json`
- `analysis/olmo-topical-diversity-20260410.json`
- `analysis/olmo-base-vs-instruct-run-review.md`

OLMo Base and OLMo Instruct both show semantic and topical concentration.

OLMo Base:

| Metric | Mean delta | Direction |
|---|---:|---|
| semantic cluster entropy | -0.7137 | down |
| effective clusters | -1.5499 | down |
| dominant cluster share | +0.1178 | up |
| topic entropy | -0.9745 | down |
| effective topics | -2.7096 | down |
| dominant topic share | +0.1680 | up |

OLMo Instruct:

| Metric | Mean delta | Direction |
|---|---:|---|
| semantic cluster entropy | -0.2954 | down |
| effective clusters | -0.4577 | down |
| dominant cluster share | +0.0871 | up |
| topic entropy | -0.7445 | down |
| effective topics | -2.5060 | down |
| dominant topic share | +0.2329 | up |

**Paper phrasing:**

> OLMo Base and OLMo Instruct both showed semantic and topical concentration. In both sets, semantic cluster entropy and topic entropy declined in most conditions, while dominant-topic or dominant-cluster share usually increased. This does not support the idea that base-model weights alone break entropy collapse.

**Figures to use:**

- Main text candidate:
  - a new compact figure/table from `analysis/temporal-diversity-combined-20260408.json` and `analysis/shannon-entropy-combined-20260408.json`.
- Appendix candidates:
  - `analysis/plots-semantic-openrouter-olmo-20260410/cluster-entropy_trajectories_by_condition.png`
  - `analysis/plots-topical-olmo-20260410/topic-entropy_trajectories_by_condition.png`
  - `analysis/plots-olmo/d5_trajectories_by_condition.png`
  - `analysis/plots-olmo/shannon_entropy_3gram_trajectories.png`

**Caveat:** The OLMo review notes wrapper and run-path confounds. The safe claim is about the observed system: model + wrapper + parser + social loop. Do not call it raw model behavior.

---

## Finding 9 — A mixed-model roster did not prevent collapse

One natural fix is to mix models. If the agents use different LLMs, maybe their errors and styles cancel out. The mixed frontier roster test says this did not happen in the tested `mag25` run.

Files:

- `analysis/mag25-frontier-1h-20260422/compression.json`
- `analysis/mag25-frontier-1h-20260422/shannon-3gram.json`
- `analysis/mag25-frontier-1h-20260422/temporal.json`
- `analysis/agent-roaster/README.md`

The mixed roster was compared to single-model baselines for the same `mag25` setting.

| Metric | Mixed roster | GPT-5 baseline | Gemini baseline | GLM-5 baseline |
|---|---:|---:|---:|---:|
| gzip delta | -0.0719 | -0.0591 | -0.0404 | -0.0230 |
| 3-gram Shannon delta | -1.23 | -0.92 | -0.04 | -0.22 |
| Distinct-5 delta | -0.244 | -0.089 | -0.033 | -0.010 |
| Self-BLEU delta | +0.037 | +0.006 | +0.013 | +0.002 |

On these metrics, the mixed roster collapsed more strongly than the single-model baselines.

**Paper phrasing:**

> Model heterogeneity did not prevent collapse in the mixed-roster probe. In a one-hour `mag25` run, a mixed frontier roster showed stronger late-stage repetition than matched single-model baselines on gzip compression, raw 3-gram Shannon entropy, Distinct-5, and Self-BLEU. This suggests that entropy collapse is not only a within-model echo effect; heterogeneous agents can still form shared templates.

**Figures to use:**

- Main text candidates:
  - `analysis/mag25-frontier-1h-20260422/compression-plots/compression_gzip_trajectories.png`
  - `analysis/mag25-frontier-1h-20260422/temporal/d5_trajectories_by_condition.png`
  - `analysis/mag25-frontier-1h-20260422/temporal/self-bleu_trajectories_by_condition.png`
- Appendix candidates:
  - `analysis/mag25-frontier-1h-20260422/shannon-3gram/shannon_entropy_3gram_trajectories.png`
  - `analysis/mag25-frontier-1h-20260422/compression-plots/compression_gzip_heatmap.png`

**Caveat:** This is one mixed-roster condition. We can call it a probe or case study. Do not claim all mixed-model societies collapse more strongly unless we run more mixed-roster conditions.

---

## Finding 10 — Obsession runs attenuate collapse but do not eliminate it

The obsession runs appear to be an intervention aimed at changing or reducing collapse. The gzip results suggest it reduced the compression collapse relative to GPT-5 baseline, but did not eliminate it.

Files:

- `analysis/obsession_5h_gpt5/compression.json`
- `analysis/obsession_5h_gpt5/compression_obs_1h.json`
- `analysis/obsession_5h_gpt5/compression_baseline.json`
- `analysis/obsession_5h_gpt5/plots/baseline_vs_obsession.png`

Current gzip summary:

| Run family | Mean gzip delta | Negative runs |
|---|---:|---:|
| GPT-5 baseline | -0.0557 | 18/18 |
| Obsession 5h | -0.0153 | 6/7 |
| Obsession 1h | -0.0033 | 4/6 |

**Paper phrasing:**

> The obsession intervention reduced gzip-detected collapse relative to the GPT-5 baseline, but it did not remove it. The baseline GPT-5 runs had a mean gzip delta of -0.0557, with 18 of 18 runs becoming more compressible. The five-hour obsession runs had a smaller mean delta of -0.0153, but 6 of 7 still became more compressible. This suggests the intervention may attenuate surface repetition, but does not fully break entropy collapse.

**Figures to use:**

- Main text candidate:
  - `analysis/obsession_5h_gpt5/plots/baseline_vs_obsession.png`
- Appendix candidates:
  - `analysis/obsession_5h_gpt5/plots/compression_gzip_trajectories.png`
  - `analysis/obsession_5h_gpt5/plots/compression_gzip_heatmap.png`
  - `analysis/obsession_5h_gpt5/plots/compression_algorithm_comparison.png`

**Need from Ayush:** We need one clear method sentence defining “obsession.” What exactly changed in this intervention? Prompt? agent persona? heartbeat? seed content? duration only? We should not write the final Methods paragraph until this is clear.

---

# Suggested Paper Structure Based on These Findings

## Introduction story

Start with the puzzle:

> What happens when social media participants are all autonomous LLM agents?

Then the result:

> They do not keep diversifying. They form local conventions, repeated templates, and narrower topics.

Then the twist:

> The exact attractor is different every time. Collapse is robust, but the content is local.

Then the failed fixes:

> More agents, base models, and mixed-model rosters do not obviously solve the problem.

## Results section outline

### 4.1 Local attractors are unique

Use Finding 1.

### 4.2 Lexical diversity and compressor metrics show collapse

Use Findings 2 and 3.

### 4.3 Scaling makes phrase adoption more collective

Use Finding 4.

### 4.4 Phrase attractors carry topic concentration

Use Finding 5.

### 4.5 Collapse has multiple mechanisms

Use Findings 6 and 7.

### 4.6 Attempts to break collapse

Use Findings 8, 9, and 10.

---

# Candidate Main-Text Figures

## Figure 1 — Local attractors are unique

Use:

- `findings/entropy-collapse-scaling/gpt-5/provenance/phrase_dna_grid.png`

Caption idea:

> Top 5-grams by run. Each run develops a different phrase attractor; top phrases do not repeat across runs and do not originate in seed posts.

## Figure 2 — Gzip collapse across runs

Use, after regenerating scale-aware version if possible:

- `findings/entropy-collapse-gzip/compression_gzip_trajectories.png`

Caption idea:

> Generic compression ratios decline over time. Lower ratio means text is easier to compress, indicating more repetition and template reuse.

## Figure 3 — GPT-5 scaling broadens adoption

Use:

- `findings/entropy-collapse-scaling/gpt-5/participation/concentration_vs_scale.png`

Caption idea:

> As agent count rises, GPT-5 phrase adoption becomes broader and less dominated by a single agent.

## Figure 4 — Phrase families are topic-concentrated

Use:

- `findings/entropy-collapse-scaling/gpt-5/embedding_bridge/topic_anchor_family_heatmap.png`

Caption idea:

> Posts containing dominant phrase families are more topically concentrated than the full run.

## Figure 5 — Mixed roster did not prevent collapse

Use:

- `analysis/mag25-frontier-1h-20260422/temporal/d5_trajectories_by_condition.png`
- or `analysis/mag25-frontier-1h-20260422/compression-plots/compression_gzip_trajectories.png`

Caption idea:

> A mixed-model roster in the `mag25` condition still shows strong late-stage repetition, exceeding single-model baselines on several metrics.

## Figure 6 — Obsession intervention attenuates but does not eliminate gzip collapse

Use:

- `analysis/obsession_5h_gpt5/plots/baseline_vs_obsession.png`

Caption idea:

> Obsession runs show weaker gzip collapse than GPT-5 baseline, but most runs still become more compressible over time.

---

# Claims to Avoid Unless We Add More Analysis

1. **Do not claim Vendi Score results.** I did not find Vendi outputs.
2. **Do not claim all four models have n10/n20/n30 scaling.** GPT-5 and Gemini do. GLM-5 and Kimi appear n10-only in the scaling folder.
3. **Do not claim every lexical metric declines in every run.** Most do, but not all.
4. **Do not say base models “break” collapse.** They change the signature, but do not restore stable diversity.
5. **Do not say mixed rosters always collapse more strongly.** We currently have one clear mixed-roster probe.
6. **Do not use “RLHF brake” framing.** The base-model experiments test whether base models can break collapse. The answer is: not clearly.

---

# Current One-Paragraph Story

LLM agent societies repeatedly form local discourse attractors. Across 48 scaling runs, every run developed its own unique dominant 5-gram family, with zero cross-run overlap and zero seed-post origin. These attractors were not just surface strings: phrase-family posts were more topically concentrated than full runs in 44 of 48 cases. Lexical diversity declined in nearly all runs, and a generic gzip compressor detected rising repetition in 49 of 49 baseline runs. Scaling did not rescue diversity; in GPT-5, larger populations made phrase adoption broader and more collective. We then tested several ways to break the pattern. Base models changed the collapse signature but did not remove attractor formation. OLMo Base and OLMo Instruct both showed semantic and topical concentration. A mixed-model frontier roster still collapsed, and in the tested `mag25` run it collapsed more strongly than single-model baselines. Obsession-style runs reduced gzip collapse but did not eliminate it. The overall result is that entropy collapse is not a quirk of one model, one metric, or one homogeneous setup. It is a robust pattern in LLM agents interacting through a shared social feed.
