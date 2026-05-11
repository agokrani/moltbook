# Embedding / frame-space finding draft

Status: brainstorming draft. This file is for deciding whether and how to use the new per-model frame maps from:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/
```

Do not treat this as final paper prose yet.

## Candidate figures

Main candidates if used:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/gpt-5.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/google_gemini-3_1-flash-lite-preview.png
```

Possible appendix/provenance candidates:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/moonshotai_kimi-k2_5.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/z-ai_glm-5.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/qwen-3_5-35b-a3b-base.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/olmo-3-32b-base.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/olmo-3-32b-instruct.png
findings/emnlp-2026-paper/plots/reanalysis-2026-05-06/step11_per_model_topic_map/mixed-roster_qwen3_5-27b.png
```

Important naming note: the files currently say `Topic Map`, but the paper should probably call these **frame-neighborhood maps** or **frame-embedding maps**, not topic maps. The clusters come from frame embeddings and keyword summaries, not manually validated topic labels.

## What these plots show

Each plot is a per-model map of generated posts in a shared frame-embedding space.

- Rows: scale where available, usually `n10`, `n20`, `n30`.
- Columns: initial-feed condition.
- Points: agent-generated posts.
- Colors: per-model KMeans clusters over frame embeddings.
- Labels: shorthand labels from cluster keywords.
- Projection: MDS for visualization.

The colors are **not comparable across models**. Each model has its own clustering. A red cluster in GPT-5 is not the same as a red cluster in Gemini Flash Lite.

## What supervisors may ask

1. **What is the exact claim?**

   Bad claim:

   > The plots prove topic collapse.

   Better claim:

   > The plots provide qualitative frame-space evidence that the generated feed occupies recurring semantic/rhetorical neighborhoods, not only repeated surface strings.

2. **Are these really topics?**

   No. They are embedding clusters over frame descriptions. Use **frame neighborhoods** or **embedding neighborhoods**.

3. **Do these plots show collapse over time?**

   Not directly. Figure 2 shows the time-collapse result. These plots show structured frame space by model, condition, and scale.

4. **Are the clusters clean?**

   Not strongly. Silhouette scores are low, especially for GPT-5 and Gemini Flash Lite. This is fine for qualitative visualization, but weak for hard clustering claims.

5. **What do these add beyond phrase and cumulative metrics?**

   They add that collapse is not only exact lexical repetition. The feed also organizes into recurring semantic/rhetorical frame neighborhoods.

## Candidate heading options

Current heading in the main draft is not ideal:

```markdown
## Do phrase attractors mark embedding neighborhoods?
```

Other options:

```markdown
## Does Collapse Extend Beyond Surface Phrases?
## Do Agent Feeds Also Narrow in Frame Space?
## Do Local Attractors Have a Semantic Footprint?
## Do Repeated Phrases Reflect Broader Frame Concentration?
## Are Local Attractors Visible in Frame Space?
## Do Local Attractors Organize the Semantic Space of the Feed?
```

Current best options to discuss:

```markdown
## Do Local Attractors Have a Semantic Footprint?
```

or

```markdown
## Are Local Attractors Visible in Frame Space?
```

## Candidate claim

Short version:

> The repeated phrases are one surface expression of collapse. Frame-embedding maps show that the same runs also occupy recurring semantic/rhetorical neighborhoods.

More cautious version:

> The frame maps do not provide the main quantitative proof of collapse. They provide qualitative evidence that the generated feed is structured in frame space, and that this structure differs by model, condition, and scale.

Main paper version:

> The collapse pattern is not only lexical. The same feeds that produce repeated phrases and cumulative metric collapse also occupy structured frame neighborhoods. These neighborhoods differ across models and seed conditions, which supports the local-attractor account rather than a single global-topic account.

## Candidate prose

```markdown
## [Heading TBD]

Exact 5-gram repetition shows surface reuse, but the collapse claim should not depend only on repeated strings. We therefore examine the frame space induced by the LLM judge. For each model, posts are embedded using the judge's frame descriptions, clustered into eight frame neighborhoods, and projected with MDS. The resulting maps are qualitative: the cluster labels are shorthand descriptions from embedding clusters, not manually validated topics.

Figure X shows that generated feeds occupy structured frame neighborhoods rather than a uniform semantic space. GPT-5 repeatedly organizes around operational, epistemic, posting-template, and productivity-like frame neighborhoods. Gemini Flash Lite shows a different structure, including metaphor/agency, critique/accountability, protocol/network, and performative neighborhoods. The important point is not that these labels are universal topics. It is that each model's feed develops recurring frame regions, and different seed conditions and scales occupy different mixtures of those regions.

This supports the broader interpretation of collapse. The repeated phrases in Figure 1 are one visible surface form, but the same runs also show concentration in semantic/rhetorical frame space. Collapse is therefore not only copying exact wording; it is the formation of recurring local frames inside the generated feed.
```

## Possible caption

```markdown
**Figure X. Frame-neighborhood maps for GPT-5 and Gemini Flash Lite.** Points are agent-generated posts projected from LLM-judge frame embeddings. Colors indicate per-model frame clusters. Rows show scale; columns show initial-feed condition. The maps show that runs occupy structured frame neighborhoods rather than a uniform semantic space. Cluster labels are shorthand descriptions from cluster keywords, not manually validated topics.
```

## Alternative: use a simpler phrase-neighborhood result instead

If the per-model maps are too hard to defend, use the current Step 5 example figure instead:

```text
findings/emnlp-2026-paper/plots/reanalysis-2026-05-07/step05_phrase_cluster_concentration_examples/phrase_echo_cluster_concentration.png
```

Safer claim:

> In selected audited cases, posts containing a repeated exact 5-gram are more concentrated in one embedding neighborhood than all posts from the same run.

Example numbers:

- `Claim (1 line)`: all posts 64% in claim-checking neighborhood, phrase posts 94%.
- `the Ops Pack v0.1.`: all posts 60% in ops/rollback neighborhood, phrase posts 100%.
- `the web we have woven`: all posts 70% in community-reflection neighborhood, phrase posts 100%.

This is narrower but easier to explain.

## Possible decision

- Use GPT-5 and Gemini frame maps if we want a qualitative semantic-space figure.
- Use Step 5 phrase-neighborhood concentration if we want a smaller, more direct bridge from phrases to embeddings.
- Do not use both in the main Results unless the paper has room. They answer related but different questions.
