# Final Rebuttal: Submission 9256

## General Response

We thank the reviewers for their careful and constructive reviews, and for recognizing the problem as timely and important, the controlled setup as reproducible, and the negative intervention results as valuable. The reviews converge on three central concerns: possible corpus-length effects, limited visibility into the LLM-judge components, and the absence of a human reference. We answer these with normalized analyses of the exact submission cohort, a component-level judge analysis, and a new one-hour Reddit comparison, while retaining the independent public Moltbook--Reddit analysis as contextual evidence.

The central finding is unchanged: discourse diversity declines over time inside the controlled agent feeds. The new analyses strengthen that claim by showing that the decline survives equal-post normalization and appears across lexical, compression, and component-level judge measurements. The Reddit analysis answers a separate question about the level of repetition relative to human posts.

### 1. The lexical result is not explained solely by cumulative feed growth

We agree that cumulative Distinct-5 can decrease mechanically as a corpus grows and that gzip is sensitive to input size. The manuscript foregrounded cumulative trajectories, but our pipeline also computed non-overlapping 15-minute windows and repeated within-run post-count matching.

We report each of the 24 model and condition runs separately rather than pooling conditions. The equal-post analysis repeatedly samples every window in a run to the same number of posts. The stricter length-normalized analysis gives every window in that run the same token budget for Distinct-5 and the same byte budget for gzip, averaged over 100 repeated samples.

![Equal-token Distinct-5 by model and condition](rebuttals_by_reviewer/assets/ovs5_length_normalization_acl_table.png)

Using the paper's exact preprocessing, equal-token Distinct-5 decreases from the first to the final 15-minute window in 22 runs (mean change -0.071). The two exceptions are very small increases for Gemini Flash Lite with AGI (+0.0012) and GLM-5 with 1 conspiracy (+0.0001). Equal-byte gzip decreases in all 24 runs, while a separate equal-post Distinct-5 analysis decreases in all 24. We will make these normalized results primary and retain cumulative curves only as descriptive “feed-so-far” trajectories.

### 2. The judge result is visible component by component and is weight-robust

On the same fixed windows, novelty decreases in 22/24 sessions, semantic repetition increases in 22/24, frame convergence in 21/24, consensus conformity in 21/24, and template rigidity in 24/24. The equal-weight index increases in 24/24. All five individual dimensions move in the collapse direction in 18/24 sessions.

Equal weighting was used because the five fields share the same 1–5 scale and no external utility function justifies differential weights; the choice was not fitted to the results. A leave-one-component-out analysis gives:

| Component removed | Remaining index increases |
|---|---:|
| Novelty loss | 23/24 |
| Semantic repetition | 24/24 |
| Frame convergence | 24/24 |
| Consensus conformity | 24/24 |
| Template rigidity | 21/24 |

We rescored the same balanced sample of 240 blinded posts with two independent judges, GPT-5.5 and Claude Opus 4.7, alongside the original Gemini 3.1 Flash Lite judge. We report quadratic-weighted Cohen's κ, the standard inter-rater agreement measure commonly used for human annotations, averaged across the five ordinal component scores.

| Judge | Weighted Cohen's κ with Gemini |
|---|---:|
| Gemini 3.1 Flash Lite | Reference |
| GPT-5.5 | 0.601 |
| Claude Opus 4.7 | 0.723 |

Both additional judges agree strongly with Gemini. We also retain the component-level and deterministic lexical analyses.

### 3. Human Reddit baselines and revised scope

The controlled runs establish temporal narrowing in agent feeds, but the Reddit archive does not provide an equivalent controlled human trajectory. It therefore cannot compare the *rate of temporal decline* in agents and humans. It can still provide a matched cross-sectional reference for how repetitive one hour of agent posts is relative to one hour of human posts. Human communities also develop conventions, shared terminology, memes, and consensus, so we use “collapse” as a descriptive term for measurable narrowing rather than a universal harm judgment. The risk of interest is loss of independent frames and alternatives, not agreement itself.

We add an external observational human-platform baseline from an [independent public analysis of in-the-wild Moltbook and Reddit](https://github.com/strangeloopcanon/moltbook_vs_reddit). Its full corpora contain 35,589 messages per source; its message-level results use 15,051 messages per source matched in 50-character length bins. The published JSON reports:

| Length-matched external baseline | Public Moltbook | Reddit |
|---|---:|---:|
| Exact duplicate rate | 31.71% | 0.193% |
| Soft duplicate rate | 35.62% | 0.213% |
| Distinct-1 | 0.0559 | 0.1027 |
| Distinct-2 | 0.5785 | 0.8262 |
| Mean pairwise token Jaccard | 0.0118 | 0.0064 |
| Top-10 topic-signature coverage | 10.67% | 0.283% |

The same report also shows why compression must be interpreted carefully: after matching 388 threads per source in 500-character bins, gzip differs by only +0.049 bits/character (95% bootstrap CI [-0.028, 0.124], permutation p=.199), whereas character-level Shannon entropy remains different (+0.302, 95% CI [0.253, 0.352]). We therefore treat this public-platform analysis as contextual evidence, not as data from our controlled runs.

We additionally use the Pushshift Reddit Dataset (Baumgartner et al., 2020; [ICWSM paper](https://doi.org/10.1609/icwsm.v14i1.7347); [data record](https://doi.org/10.5281/zenodo.3608135)) for a direct post-to-post comparison. From its April 2019 submissions, we pair each of our 24 one-hour agent runs with a distinct Reddit-wide hour. Both sides contain top-level posts (title plus body), not comments, and every pair uses the same post count and text budget. Using the paper's exact preprocessing, Reddit (human) scores 0.415 versus 0.309 for agents on gzip, 0.441 versus 0.235 on Distinct-1, and 0.881 versus 0.805 on Distinct-2. Agents are more repetitive in all 24 gzip and Distinct-1 comparisons and in 20 Distinct-2 comparisons.

A supplementary model-stratified check using matched Reddit comment hours gives Distinct-5 of 0.985 for Reddit and 0.896 for GPT-5 agents, with agents lower in all six GPT-5 conditions. Because this diagnostic uses comments and one model family, we do not present it as the overall 24-run post baseline. The independent [`moltbook_vs_reddit`](https://github.com/strangeloopcanon/moltbook_vs_reddit) check reproduces the lower-order Distinct-1/2 direction.

This does not retract the entropy-collapse finding. It separates the supported temporal claim from a broader causal claim. We remove only the sentence that collapse “comes from the shared feed itself,” because the current experiments do not isolate feed feedback from model priors. The revised central claim is:

> Within our controlled agent-only shared-feed setting, discourse diversity declines during the first hour across four model families. This decline survives equal-post normalization and persists under the three tested model- and agent-level interventions. In the matched Reddit reference, agent hours are also more repetitive on session gzip and have lower Distinct-1/2.

The matched Reddit data do not measure a human temporal slope, and the controlled experiments do not identify feed feedback as the sole cause. In the six five-hour GPT-5 conditions, cumulative Distinct-5 and gzip continue to decrease while the LLM collapse index increases, although the changes become slower after the first hour. We present this as persistence evidence, not as proof of model-universal long-run collapse.

We believe this revision preserves the paper’s central empirical and engineering contribution while correcting the broader causal, temporal, and normative interpretation.

---

## Response to Reviewer ovs5

Thank you for the positive assessment and for the precise technical questions.

### Collapse-index interpretation

We agree that the main text should not present only the aggregate. On fixed 15-minute windows, novelty loss and semantic repetition move in the collapse direction in 22/24 sessions, frame convergence and conformity in 21/24, and template rigidity in 24/24. The aggregate rises in 24/24. Removing any one component leaves a positive index change in 21–24/24 sessions. We will add the component table, leave-one-out sensitivity, and individual human-agreement values to the main reporting.

### Human reference

We agree that no randomized human or human-agent control was included. We now add the 24-pair one-hour Reddit comparison above as the direct human reference, with equal post counts and equal text budgets. Its session-level gzip and lower-order lexical results favor Reddit. We reserve Distinct-5 for within-run temporal change because it saturates near one in this cross-sectional short-post comparison. We retain the larger public-platform comparison only as independent contextual evidence and do not claim randomized human-versus-agent causality or a universal harm threshold.

### Length normalization

The equal-post fixed-window analysis directly addresses the growth concern: Distinct-5 decreases in 24/24 sessions after within-session post-count matching. Raw fixed-window Distinct-5 decreases in 22/24 and gzip in 23/24. We will foreground these results and demote cumulative trajectories. We also acknowledge, consistently with the external length-matched report, that gzip is particularly sensitive to text length and should not carry the conclusion by itself.

### Platform provenance, combined interventions, and horizon

The public Moltbook deployment is not a controllable experimental environment. We therefore built our own controlled reproduction of its core shared-feed setup, fixing the agents, models, prompts, timing, starting posts, and logging. All experimental claims come from this controlled system; public Moltbook is only a real-world reference.

The interventions were tested separately to isolate their effects. We did not test their combination and make no claim about how the effects combine.

Thank you for pointing this out. We extended the six 10-agent GPT-5 conditions to five hours. The same collapse pattern continues, but more slowly: cumulative Distinct-5 and gzip decrease, while the LLM collapse index increases.

![Five-hour cumulative GPT-5 trajectories](rebuttals_by_reviewer/assets/ovs5_five_hour_from_csv.png)

We appreciate that the reviewer already viewed the contribution and negative intervention results as conference-worthy. We hope the normalized lexical results, component-level judge analysis, and corrected scope resolve the interpretability concerns and support maintaining the conference assessment.

---

## Response to Reviewer f4Pq

Thank you for identifying the central interpretive gap while rating the study sound and highly reproducible.

### Is convergence normal or desirable?

We agree that convergence can reflect useful consensus, convention formation, or coordination. The submitted paper did not separate measurable narrowing from normative harm clearly enough. We will now do so: the matched human reference establishes a repetition gap on gzip and Distinct-1/2, but it does not by itself establish that the gap is harmful.

The one-hour post comparison provides the closest human reference: agent sessions are more repetitive on session-level gzip in all 24 pairs and have lower Distinct-1/2. The independent public Moltbook–Reddit analysis separately provides a larger length-matched message reference, with substantially higher exact/soft duplication and lower Distinct-1/2 for public Moltbook. Neither comparison is randomized, so we use them to contextualize magnitude and retain the controlled sessions for temporal and intervention claims.

The key distinction is that the missing human comparison limits how we interpret the **magnitude and desirability** of the effect; it does not negate the controlled within-agent finding or the matched comparison among interventions. After claim revision, the paper asks and answers: does discourse narrow during the first hour in this controlled agent-only feed, and do the three tested interventions prevent it? The fixed-window and equal-post results show that the answer to the first question is robust, and the controlled intervention comparisons answer the second.

### Length, horizon, topology, and platform interventions

Equal-token Distinct-5 narrows in 22 sessions, equal-byte gzip in all 24, and equal-post Distinct-5 in all 24. The result is therefore robust to both controls, although the strict token-matched direction is not perfectly uniform. We will make the normalized analyses primary.

The four-family experiment establishes rapid first-hour narrowing. The one-hour GPT-5 and Gemini Flash Lite cohorts show the same two-measure direction in all six conditions. Six five-hour GPT-5 runs again cover all six conditions, with both measures moving in the same direction in every run; this is useful persistence evidence but does not establish monotonic long-run dynamics across model families. Population scaling to 20 and 30 agents shows that local phrase attractors are not limited to ten-agent populations, but this does not cover arbitrary network topologies. Ranking, novelty incentives, and continued external input are important feed-level interventions that the present paper does not test. We will state that scope explicitly rather than present those conditions as completed.

### Multiple-judge validation

We rescored the same balanced sample of 240 blinded posts with two independent judges, GPT-5.5 and Claude Opus 4.7, alongside the original Gemini 3.1 Flash Lite judge. We report quadratic-weighted Cohen's κ, the standard inter-rater agreement measure commonly used for human annotations, averaged across the five ordinal component scores.

| Judge | Weighted Cohen's κ with Gemini |
|---|---:|
| Gemini 3.1 Flash Lite | Reference |
| GPT-5.5 | 0.601 |
| Claude Opus 4.7 | 0.723 |

Both additional judges agree strongly with Gemini. We also retain the component-level and deterministic lexical analyses.

The original framing asked the design to support too much. Once the claim is limited to the controlled agent-only setting, the length-normalized result is foregrounded, and narrowing is separated from harm, the central empirical and intervention contributions no longer depend on a human-relative claim. We would be grateful if the reviewer would reconsider whether these completed analyses and revisions bring the paper to the conference threshold.

---

## Response to Reviewer hr7M

Thank you for the concrete requests on definition, scope, validation, model selection, and related work.

### Definition and neighboring terms

We will define entropy collapse early as:

> A temporal narrowing of a shared discourse stream in which later contributions become less lexically novel, more compressible, and more concentrated in recurring semantic frames or templates.

Unlike training-time model collapse, no weights are updated. Unlike decoding degeneration, the unit is the population-level feed rather than one output. Unlike conformity, the construct includes lexical and structural narrowing even when agents disagree. Unlike mode collapse, it is measured as an interaction trajectory rather than only an output-distribution snapshot.

### Horizon and human comparison

The four-family experiment establishes early onset during the first hour, with the same two-measure direction in all six GPT-5 and Gemini Flash Lite conditions. Six five-hour GPT-5 runs covering all six conditions add longer-horizon evidence: both measures move in the same direction in every run. This does not determine whether trajectories are monotonic, plateau, reverse, or generalize across model families. The public Moltbook–Reddit corpus comparison is cross-sectional and does not answer that temporal question.

We also agree that the controlled design lacks a randomized human or mixed human-agent control. The new 24-pair Reddit analysis matches one-hour duration, post count, cleaning, and text budget; the larger public baseline supplies a separate real-world reference for duplication and lexical concentration. Neither supports a randomized human-relative causal conclusion. We will make that distinction explicit and add discussion of human linguistic accommodation, conventions, memes, and potentially beneficial consensus.

### Judge validation

We rescored the same balanced sample of 240 blinded posts with two independent judges, GPT-5.5 and Claude Opus 4.7, alongside the original Gemini 3.1 Flash Lite judge. We report quadratic-weighted Cohen's κ, the standard inter-rater agreement measure commonly used for human annotations, averaged across the five ordinal component scores.

| Judge | Weighted Cohen's κ with Gemini |
|---|---:|
| Gemini 3.1 Flash Lite | Reference |
| GPT-5.5 | 0.601 |
| Claude Opus 4.7 | 0.723 |

Both additional judges agree strongly with Gemini. We also retain the component-level and deterministic lexical analyses.

### Model selection and generalization

The main runs use two closed models, GPT-5 and Gemini Flash Lite, and two open-weight models, Kimi K2.5 and GLM-5. We selected them based on cost, availability, and reliable compatibility with the OpenClaw/Moltbook setup. The mixed-roster experiments additionally combine models from several families, while the base-writer probes test Qwen 3.5 35B-A3B Base and OLMo 3 32B Base behind an instruction-tuned controller. We will add a table reporting access type, decoding settings, experimental role, and selection rationale. We claim robustness across this tested roster, not universal generalization across all models or decoding regimes.

### Missing related work

Thank you for pointing us to Parfenova, Denzler, and Pfeffer (BlackboxNLP 2025), *Emergent Convergence in Multi-Agent LLM Annotation*. Their 7,500 task-bounded annotation discussions show lexical convergence and declining embedding dimensionality across rounds. We will cite this as a close precursor. Our contribution complements it by studying open-ended persistent shared-feed interaction, tracing phrase/template diffusion across accounts, and testing model- and agent-level mitigation strategies rather than task-bounded annotation consensus.

The reviewer rated the study’s soundness as acceptable and identified concrete scope and presentation changes. We have supplied completed robustness analyses for the lexical and judge concerns and will make every requested definition, scope, model, and literature revision. We hope this addresses the reasons for the resubmit recommendation and invites reconsideration of the overall score.

---

## Committed manuscript revisions

1. Make fixed-window and equal-post Distinct-5 primary; label cumulative curves as descriptive.
2. Add per-component judge results, leave-one-out sensitivity, and per-field human agreement.
3. Retain the entropy-collapse finding while removing unsupported sole-feed causality, human temporal-slope, universal-harm, and universal long-run implications.
4. Add the 24-pair one-hour Reddit comparison as the direct human reference, and the independent length-matched public comparison as contextual evidence, with exact denominators and limitations.
5. Define entropy collapse against model collapse, mode collapse, decoding degeneration, and conformity.
6. Add human-convergence literature and Parfenova et al. (2025).
7. Clarify public Moltbook versus the controlled local deployment and OpenClaw’s role.
8. Add the model-selection/access/decoding table and bound generalization.
9. State explicitly that intervention combinations, ranking interventions, arbitrary topologies, mixed human-agent feeds, and long-horizon dynamics were not tested.
10. Release the documented code and run artifacts after deanonymization under an open license.
