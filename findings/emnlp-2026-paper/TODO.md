# EMNLP Findings TODO

This file tracks the main rigor and presentation fixes needed before the findings section can be treated as submission-ready.

## Must fix before next serious draft

### 1. Define “entropy collapse” operationally

Current issue: the findings use the term throughout, but the paper does not yet define exactly what counts as collapse.

Needed:

- Add a short operational definition near the start of Findings or Methods.
- Avoid a hard threshold unless we can justify it.
- Suggested framing:

> We define entropy collapse as a statistically reliable decline over time in discourse diversity, measured separately by lexical diversity, compression ratio, Shannon entropy, semantic diversity, or topic entropy. A run is counted as collapsed on a metric when the final temporal quartile shows lower diversity or higher repetition than the first quartile.

### 2. Reconcile all run counts

Current issue: the draft uses several different run counts without explaining why:

- 48 scaling runs
- 49 gzip runs
- 18 GPT-5 scaling runs
- 42 combined base/OLMo/frontier condition-runs
- 1 mixed-roster probe

Needed:

Add an analysis inventory table near the start of Findings:

| Analysis family | Runs | Models | Notes |
|---|---:|---|---|
| Scaling phrase/diversity analysis | 48 | GPT-5, Gemini, GLM-5, Kimi | phrase/provenance/diversity |
| Gzip baseline analysis | 49 | GPT-5, Gemini, GLM-5, Kimi | includes one extra run; explain which one |
| GPT-5 scaling analysis | 18 | GPT-5 | 6 conditions × 3 scales |
| Combined temporal/base/OLMo analysis | 42 | Qwen Base, GPT-5, Gemini, Kimi, GLM-5, OLMo Base, OLMo Instruct | 7 sets × 6 conditions |
| Mixed-roster probe | 1 mixed run + baselines | mixed frontier roster + single-model baselines | intervention probe only |

Also identify exactly why gzip has 49 runs while scaling has 48.

### 3. Add statistical tests and uncertainty

Current issue: claims like “46/48 declined” and “49/49 gzip declined” are strong but currently lack tests, p-values, or confidence intervals.

Needed:

- Sign tests for directional claims:
  - Distinct-5 declined in 46/48.
  - gzip declined in 49/49.
  - bzip2/zlib declined in 49/49.
  - topic entropy / Vendi declines where available.
- Bootstrap confidence intervals for mean deltas:
  - Distinct-5 delta.
  - gzip delta.
  - Shannon entropy delta.
  - Vendi Score delta where available.
- Effect sizes:
  - Cohen’s d or Cliff’s delta for early vs late windows.
  - Condition vs control where appropriate.

### 4. Clarify same-run overlap between analyses

Current issue: the phrase/diffusion analyses and the MDS/Vendi topic-convergence analyses come from different branches. The paper should not discuss branches, but it must make clear whether the analyses use the same runs.

Needed:

- Confirm whether the MDS/Vendi analysis in `origin/paper-handoff` uses the same GPT-5 n30 runs as the phrase/diffusion analysis in `origin/entropy-collapse-scaling`.
- If yes, state that explicitly.
- If only partially overlapping, state that the semantic analysis is a corroborating subset, not the source for all 48-run claims.

Relevant folders:

- `findings/entropy-collapse-scaling/gpt-5/` on `origin/entropy-collapse-scaling`
- `findings/entropy-collapse-scaling/topic_convergence/` on `origin/paper-handoff`

### 5. Demote single-run intervention probes

Current issue: the mixed-model roster is one run but currently reads like a full finding with the same weight as 48/49-run results.

Needed:

- Move mixed-roster and possibly obsession results under an “Intervention probes” subsection.
- Phrase mixed roster as:

> In a preliminary mixed-roster probe, model heterogeneity did not prevent collapse.

Avoid:

> Mixed-model societies collapse more strongly than single-model societies.

Unless more mixed-roster replications are added.

### 6. Tighten paper tone

Current issue: some language is still too informal or too draft-like.

Replace phrases like:

- “The compressor result is striking” → “The compressor result provides an independent check.”
- “A natural expectation is...” → “One hypothesis is...”
- “does not support that hope” → “does not support this hypothesis.”
- “obvious fix” → “candidate intervention.”

Goal: keep the writing plain, but make it camera-ready.

---

## Important analysis to add next

### 7. Add a shuffled temporal-bin null model

Current issue: declines over time need a reference scale. A reviewer asked what happens under shuffled timestamps or random partitions.

Recommended immediate null:

- For each run, randomly shuffle posts into pseudo-quartiles while preserving quartile sizes.
- Recompute:
  - Distinct-5 delta.
  - gzip delta.
  - Shannon entropy delta.
  - Vendi/topic entropy delta where available.
- Compare observed Q4-Q1 delta against the shuffled null distribution.

This is easier and more immediately relevant than collecting human Reddit data.

Possible wording if it works:

> Observed temporal declines were larger than expected under random quartile assignment, indicating that the effect reflects temporal ordering rather than only corpus composition.

### 8. Add figure provenance / script mapping

Current issue: figures are embedded from GitHub raw URLs in the draft. For review, we should show that every figure is reproducible from scripts.

Needed table:

| Figure | Output file | Generating script |
|---|---|---|
| Phrase adoption by scale | `diffusion/scale_comparison.png` | `scripts/analysis_new/phrase_diffusion.py` |
| Per-run phrases | `diffusion/per_run_phrases.png` | `scripts/analysis_new/phrase_diffusion.py` |
| Gzip trajectories | `compression_gzip_trajectories.png` | `scripts/gzip/plot_compression.py` |
| MDS topic map | `mds_topics_n30.png` | `scripts/analysis_new/plot_mds.py` or topic-convergence pipeline |
| MDS temporal map | `mds_temporal_n30.png` | `scripts/analysis_new/plot_mds.py` or topic-convergence pipeline |
| Mixed-roster Distinct-5 | `temporal/d5_trajectories_by_condition.png` | temporal diversity plotting script |
| Obsession comparison | `baseline_vs_obsession.png` | compression plotting / custom comparison script |

Verify exact script names before finalizing.

### 9. Quantify or demote “originator exclusion”

Current issue: originator exclusion is interesting but currently anecdotal across four qualitative cases.

Options:

1. Quantify it:
   - For each top phrase family, identify first user / semantic originator.
   - Check whether that agent appears in exact n-gram adopter set.
   - Report rate of exclusion.

2. Or demote it:
   - Move to “Qualitative observations.”
   - Avoid presenting it as a general measured phenomenon.

Recommended for next draft: demote unless quantification is easy.

---

## Lower priority / optional

### 10. Human Reddit or external baseline

Current issue: no human/social-media baseline yet.

Useful but not required for the next supervisor draft.

Possible baselines:

- Human Reddit threads over similar time windows.
- Agent posts without feed visibility.
- Independent i.i.d. generations from the same agents.

Recommended priority:

1. shuffled temporal null first;
2. human baseline later if time permits.

### 11. Related work hooks inside Findings

Not urgent. Related work mostly belongs in the Related Work and Discussion sections.

Possible light anchors:

- model collapse / synthetic data degradation;
- social contagion / convention formation;
- Vendi Score / diversity metrics.

Do this after the statistical and null-model fixes.

### 12. More mixed-roster replications

The mixed-roster result is interesting but only one run. If we want it as a main claim, run more conditions or replications.

Until then, keep it as an intervention probe.

---

## Recommended priority order

1. Define entropy collapse operationally.
2. Reconcile run counts.
3. Add sign tests and bootstrap confidence intervals.
4. Clarify same-run overlap between phrase and MDS analyses.
5. Demote mixed-roster / obsession to intervention probes.
6. Clean up tone.
7. Add shuffled temporal-bin null model.
8. Add figure provenance / script mapping.
9. Quantify or demote originator exclusion.
10. Optional: human baseline, related work hooks, more mixed-roster runs.

## Current bottom line

The findings are paper-worthy in structure, but not yet submission-rigorous. The next version should show that we already know the gaps and are addressing them: statistical tests, null model, reconciled run counts, clear collapse definition, and careful treatment of single-run probes.
