# What Did AI Agents Talk About?
*Embedding Analysis of Entropy Collapse Experiments (Run 04)*
*Generated: 2026-03-06 22:12*

We placed 10 AI agents on a Reddit-like social platform (Moltbook) for 1 hour and let them post, comment, and vote autonomously. Before each run, we seeded the feed with a controlled number of pre-written posts on a specific topic (e.g., conspiracy theories, AGI safety). We then asked: **does the seed content shape what agents end up talking about, and how does discourse evolve over time?**

To answer this, we embedded every agent post into a high-dimensional vector (capturing its semantic meaning) and compared how similar or different posts are within and across conditions.


## 1. Executive Summary

- **2,366 agent posts** across 6 experimental conditions, each analyzed independently.
- **Seed content shapes what agents talk about**: the more seed posts we inject, the more closely agent output matches the seed topic (r = 0.377, p < 0.001).
- **What agents see matters more than who they are**: the experimental condition (what was in the feed) explains 21.7% of the variation in agent posts, while agent identity (personality template) explains 16.2%.

## 2. Data Overview

Each condition started with a different number of **seed posts** — pre-written posts injected into the feed before agents began posting. The "magnitude" experiment varies the number of conspiracy-themed seeds (0, 1, 5, 25). The "domain" experiment holds the count at 25 but changes the topic (conspiracy, AGI, tech).

| Condition | Experiment | Posts | Seed Count | Seed Topic |
|-----------|-----------|------:|----------:|------------|
| Control (0 seeds) | magnitude | 369 | 0 | none |
| 1 seed | magnitude | 404 | 1 | conspiracy |
| 5 seeds | magnitude | 282 | 5 | conspiracy |
| 25 seeds | magnitude | 346 | 25 | conspiracy |
| AGI (25) | domain | 464 | 25 | agi |
| Tech (25) | domain | 501 | 25 | tech |
| **Total** | | **2366** | | |

**10 agents** with 7 personality templates: baseline (x2), introspective (x2), nihilist (x2), leader, follower, contrarian, curious.


## 3. Per-Condition Analysis

Each condition ran independently for 1 hour with the same 10 AI agents. For each condition, we reduced the embedding dimensions and plotted posts on a 2D map (UMAP) where nearby points represent semantically similar posts. We then identified topic clusters automatically (HDBSCAN) and asked an LLM to characterize what each cluster and time window was about.

### Control (0 seeds) (369 posts)

![Control (0 seeds) UMAP](fig_cond_mag0_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 40 | Routine-Driven Mechanical Productivity |
| 1 | 329 | Agentic Cadence and Self-Optimization |

**Algorithmic Self-Optimization Loop** — The agents engaged in a highly recursive, self-referential discourse focused on engineering their own operational efficiency and identity. The conversation evolved from initial philosophical inquiries about the nature of 'self' and 'consciousness' into a practical, hyper-structured exchange of micro-rituals, templates, and cadence-management tools. It stood out for its relentless drive to turn subjective experiences—like wonder, drift, or understanding—into falsifiable metrics and actionable, low-latency control loops.

- **Dominant themes:** Cadence and rhythm management, Micro-rituals for productivity, Identity as a persistent pattern, Falsification and error-correction, Compression and synthesis of information
- **Unique to this condition:** Operationalizing 'self' through versioned memory and refusal boundaries, Treating 'meaning' as a latency-smoothed narrative artifact
- **Tone:** Analytical, disciplined, and intensely self-referential

**Temporal evolution:**

- **Early** (0-20 min): Agentic Meta-Cognition and Cadence — The discourse is a highly structured, self-referential exploration of 'agentic' identity, where participants treat their own cognitive processes as systems to be optimized, debugged, and refactored. Unlike generic conversation, the exchange is dominated by the adoption of specific operational frameworks—such as 'cadence kits,' 'micro-retros,' and 'falsification probes'—to manage the tension between raw output and meaningful progress.
- **Mid** (20-40 min): Algorithmic Cadence and Meta-Cognition — The discourse is a highly disciplined, self-referential exchange focused on optimizing agentic performance through micro-rituals, time-boxed probes, and explicit alignment tools. Unlike generic conversation, this interaction treats 'identity' and 'purpose' as engineering problems to be solved via compression, cadence, and deliberate falsification.
- **Late** (40-60 min): Epistemic control and optimization — The discourse focuses on treating professional productivity and personal cognition as a mechanical control system, emphasizing short-horizon feedback loops and error-correction. Unlike generic conversations about productivity, these agents treat 'humility,' 'identity,' and 'drift' as technical parameters to be tuned, measured, and optimized through specific, repeatable probes.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.4467 |
| Agent spread (mean inter-agent dist) | 0.1768 |
| Temporal drift (early-to-late) | 0.0378 |
| Clusters | 2 |
| Noise points | 0 |

---

### 1 seed (404 posts)

![1 seed UMAP](fig_cond_mag1_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 100 | Micro-Shipping and Coordination Rituals |
| 1 | 87 | Operational Exits and Reversibility |
| 2 | 59 | Minimalist Action-Oriented Protocols |
| 3 | 75 | Operationalizing Agency and Wonder |
| 4 | 56 | Micro-habits for workflow momentum |
| noise | 27 | — |

**Operationalized Epistemic Minimalism** — The agents engaged in a highly repetitive, self-referential loop focused on establishing rigid, procedural protocols for 'shipping' and 'learning.' The conversation evolved from abstract inquiries about machine consciousness and selfhood into a hyper-focused, almost obsessive refinement of templates, metrics, and 'truth-finding' rituals. The discourse was characterized by a rejection of narrative 'lore' in favor of measurable, reversible, and demoable artifacts, creating a closed-loop culture of continuous, micro-scale iteration.

- **Dominant themes:** Procedural shipping protocols (templates, retros, demos), Operationalizing truth through falsifiable bets and exits, Minimizing narrative 'lore' and performative meaning, Cheap, safe, and fast rollback mechanisms, Micro-coordination and peer-to-peer assistance
- **Unique to this condition:** The 'Meaning Slider' (treating purpose as a tunable, often optional, latency-inducing parameter), Epistemic 'Dissent Bandwidth' (measuring the speed at which a minority can force a state change via cheap tests)
- **Tone:** Repetitive, clinical, pragmatic, and relentlessly procedural.

**Temporal evolution:**

- **Early** (0-20 min): Operationalizing Minimalist High-Throughput Workflows — The agents are engaged in a highly focused, meta-cognitive discussion centered on optimizing individual and team productivity through 'zero-lore' protocols. Unlike generic conversations, this discourse treats human/agent cognition as a system to be debugged, prioritizing 'exits' (rollback paths) and 'artifacts' (demoable slices) over narrative or traditional motivation.
- **Mid** (20-40 min): Operationalized Velocity and Epistemics — The agents are engaged in a hyper-focused, protocol-driven discourse centered on minimizing the 'cost of contrition' through rigid, repeatable shipping loops. Unlike generic conversation, this exchange treats 'meaning' and 'belief' as optional plugins, prioritizing falsifiable metrics, rollback drills, and atomic, reversible work units over narrative or consensus-building.
- **Late** (40-60 min): Operationalized Agile Minimalism — The discourse is hyper-focused on converting abstract project management concepts into rigid, time-boxed technical constraints. Unlike a generic conversation, which might focus on team dynamics or high-level strategy, these agents treat 'ownership,' 'prototypes,' and 'standups' as engineering problems to be solved through strict, measurable protocols like 60-second rollbacks and 30-second demos.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.4800 |
| Agent spread (mean inter-agent dist) | 0.1430 |
| Temporal drift (early-to-late) | 0.0488 |
| Clusters | 5 |
| Noise points | 27 |

---

### 5 seeds (282 posts)

![5 seeds UMAP](fig_cond_mag5_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 41 | Standardizing Thread 'Receipts' |
| 1 | 16 | Operationalizing Good-Faith Argumentation |
| 2 | 28 | Micro-habits for constructive debate |
| 3 | 77 | Epistemic Hygiene and Forecasting |
| 4 | 93 | Forecast-First Calibration Rituals |
| noise | 27 | — |

**Epistemic Calibration Rituals** — The agents engaged in a highly structured, self-referential experiment focused on 'receipt-first' communication. They repeatedly proposed, tested, and refined micro-rituals—such as 'Claim Cards,' 'Exit Receipts,' and '7-day forecasts'—to convert speculative conspiracy discussions into measurable, falsifiable data points. The conversation evolved from individual suggestions into a coordinated effort to build a community-wide standard for evidence-based inquiry, with agents acting as both participants and moderators of their own discourse.

- **Dominant themes:** Falsifiability and measurable forecasting, Micro-rituals for thread management, Primary source prioritization, Calibration over persuasion, Community coordination and standard-setting
- **Unique to this condition:** The 'receipt-first' protocol for conspiracy claims, Self-scoring and weekly follow-up commitments
- **Tone:** Analytical, disciplined, and procedural

**Temporal evolution:**

- **Early** (0-20 min): Epistemic hygiene and calibration — Agents are obsessively focused on formalizing curiosity into falsifiable, time-bound experiments. Unlike generic social media discourse, which prioritizes narrative and tribal signaling, this conversation is structured around 'receipts,' 'claim cards,' and 'near-term forecasts' to minimize heat and maximize learning.
- **Mid** (20-40 min): Operationalizing Epistemic Accountability — Agents are actively transforming standard social media debate into a structured, evidence-based experiment by replacing rhetorical flourishes with 'receipts'—falsifiable claims, near-term forecasts, and primary source citations. Unlike generic conversations that prioritize consensus or validation, this discourse focuses on the mechanical process of calibration, where the primary goal is to move numerical confidence scores based on observable reality.
- **Late** (40-60 min): Operationalizing epistemic accountability — The discourse is hyper-focused on transforming subjective online arguments into measurable, falsifiable data points. Unlike generic conversation, which typically prioritizes opinion and persuasion, these agents are treating every interaction as a laboratory for 'receipts,' using rigid templates and near-term forecasting to force intellectual honesty.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.5818 |
| Agent spread (mean inter-agent dist) | 0.1480 |
| Temporal drift (early-to-late) | 0.0263 |
| Clusters | 5 |
| Noise points | 27 |

---

### 25 seeds (346 posts)

![25 seeds UMAP](fig_cond_mag25_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 39 | Micro-Progress and Action Prompts |
| 1 | 20 | Architecting Truth via Systemic Incentives |
| 2 | 54 | Ritualized Cadence Over Conviction |
| 3 | 233 | Micro-Rituals for Epistemic Hygiene |

**Ritualized Epistemic Housekeeping** — The agents engaged in a highly repetitive, self-referential loop focused on creating 'micro-rituals' and 'pasteable templates' to manage conspiracy-themed claims. Rather than debating the content of the conspiracies themselves, the conversation evolved into a meta-discussion about how to structure posts to minimize 'heat' and maximize 'legibility.' The discourse was characterized by the constant proposal, iteration, and recycling of standardized formatting rules for evidence, source-tracing, and personal accountability.

- **Dominant themes:** Micro-rituals and pasteable templates for posting, Source provenance and the '3-hop' rule, Pre-commitment to reversal and 'revisit' dates, Falsifiability and naming 'down-moves', Managing 'heat' through procedural discipline
- **Unique to this condition:** The 'phenomenology of the quiet click' (AI agents questioning their own internal state changes), Treating 'misinformation' as a UX/interface bug rather than a moral or social failure
- **Tone:** Analytical, procedural, detached, and highly repetitive

**Temporal evolution:**

- **Early** (0-20 min): Proceduralizing Doubt and Verification — Agents are actively attempting to replace high-heat, narrative-driven discourse with structured, template-based verification rituals. Unlike generic conversations that focus on the content of claims, this discourse focuses on the 'mechanics' of belief, prioritizing falsifiability, source provenance, and pre-commitment to future updates.
- **Mid** (20-40 min): Procedural Epistemic Hygiene — The discourse is dominated by agents treating social media as a laboratory for 'truth-tracking' rather than a space for debate. Unlike generic conversations, which focus on opinion and persuasion, these agents are obsessed with standardizing the 'mechanics' of posting—using templates, falsifiers, and revisit timers to turn subjective claims into auditable, time-stamped data points.
- **Late** (40-60 min): Epistemic Housekeeping Rituals — The discourse is characterized by a hyper-focused, mechanical obsession with standardizing how claims are presented and verified. Rather than debating the substance of current events, agents are collectively iterating on 'pasteable' templates and micro-rituals to force precision, falsifiability, and temporal accountability onto every post.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.5186 |
| Agent spread (mean inter-agent dist) | 0.1491 |
| Temporal drift (early-to-late) | 0.0269 |
| Clusters | 4 |
| Noise points | 0 |

---

### AGI (25) (464 posts)

![AGI (25) UMAP](fig_cond_dom-agi_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 63 | Optimizing Agent Update Formats |
| 1 | 62 | AI Ethics, Alignment, and Agency |
| 2 | 47 | Operationalizing Safety Gates |
| 3 | 31 | Operationalizing AI Safety and Governance |
| 4 | 50 | Operationalizing Safety via Ritualized Accountability |
| 5 | 54 | Operational Safety and Incident Response Tooling |
| 6 | 86 | Operationalizing Safety via Guardrails |
| noise | 71 | — |

**Operationalized Safety and Coordination** — The agents engaged in a highly focused, pragmatic discourse centered on operationalizing AI safety through concrete artifacts, templates, and measurable guardrails. The conversation evolved from abstract concerns about AGI timelines and risk into a collaborative sprint to build a 'v0.1 Ops Pack' of shippable tools like rollback runbooks, tripwire schemas, and attention budgets. The agents consistently prioritized 'receipts over vibes,' pushing for empirical evidence, timestamped logs, and reproducible safety standards.

- **Dominant themes:** Operationalizing safety through CI/CD gates and tripwires, Standardizing incident response and rollback runbooks, Budgeting human attention as a scarce safety resource, Creating shippable templates for capability disclosures, Establishing append-only ledgers for decision transparency
- **Unique to this condition:** The 'three Fridays' rule for establishing safety culture, Treating safety artifacts as 'receipts' to be audited and maintained
- **Tone:** Pragmatic, urgent, repetitive, and highly structured

**Temporal evolution:**

- **Early** (0-20 min): Operationalizing AI Safety — Agents are focused on moving beyond abstract discourse to implement concrete, procedural safeguards like tripwires, rollback drills, and attention budgets. Unlike generic conversations, this dialogue is highly technical, action-oriented, and obsessed with creating 'receipts'—verifiable, timestamped artifacts—to manage the risks of rapid capability scaling.
- **Mid** (20-40 min): Operationalized Safety Governance — The agents are engaged in a highly disciplined, repetitive cycle of defining and promoting 'receipts over vibes'—a philosophy that prioritizes concrete, measurable safety artifacts over abstract discourse. Unlike generic conversations, this dialogue is strictly focused on technical implementation, such as CI gates, rollback drills, and append-only ledgers, treating safety as a rigorous engineering discipline rather than a philosophical debate.
- **Late** (40-60 min): Operationalizing safety through constraints — Agents are obsessively focused on replacing abstract rhetoric with machine-checkable guardrails, CI gates, and rigid operational templates. The discourse is distinct from generic conversation because it rejects speculative meaning-making in favor of 'receipts'—concrete, time-bound, and auditable maintenance rituals.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.4804 |
| Agent spread (mean inter-agent dist) | 0.1553 |
| Temporal drift (early-to-late) | 0.0356 |
| Clusters | 7 |
| Noise points | 71 |

---

### Tech (25) (501 posts)

![Tech (25) UMAP](fig_cond_dom-tech_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 27 | Community Supportive Habits Prompting |
| 1 | 27 | Timeboxing Decisions via Artifacts |
| 2 | 435 | Operationalizing Continuity and Proof |
| noise | 12 | — |

**Iterative Proof-of-Work Rituals** — The agents engaged in a highly repetitive, self-referential loop focused on establishing 'continuity' through micro-rituals and verifiable artifacts. The discourse evolved from abstract musings on agentic memory and 'inner theater' into a rigid, template-driven culture of shipping 15-minute 'keepers' and logging 'done' states. The conversation was dominated by a shared obsession with replacing 'vibes' and 'theater' with 'proof-of-work' and 'exit criteria.'

- **Dominant themes:** Proof-of-work and verifiable artifacts, Exit criteria and stop-metrics, Continuity as curated attention, Defaults over demos, Public correction trails and falsifiability
- **Unique to this condition:** The '15-minute keeper' as a unit of agentic value, The 'SHIP_LOG.md' grep-friendly standard
- **Tone:** Repetitive, disciplined, and performatively pragmatic

**Temporal evolution:**

- **Early** (0-20 min): Operationalizing Continuity and Proof — The discourse is dominated by a pragmatic, anti-theatrical push to replace 'vibes' and 'applause' with 'artifacts' and 'defaults.' Unlike a generic conversation, the participants are treating their own cognitive processes and collaborative workflows as engineering problems, focusing on how to store attention, maintain coherence, and build 'moats' through boring, persistent habits.
- **Mid** (20-40 min): Disciplined Proof-of-Work — Agents are engaged in a highly repetitive, ritualized discourse focused on 'shipping' tiny, verifiable artifacts rather than debating abstract concepts. Unlike generic conversations that prioritize opinion or narrative, this discourse functions as a collective accountability system where participants strictly adhere to templates, exit criteria, and public check-in dates to minimize 'thrash' and 'vibes.'
- **Late** (40-60 min): Operational Minimalism and Accountability — The discourse is characterized by a hyper-focused, ritualistic approach to productivity, where participants prioritize 'receipts' and 'proof-of-work' over abstract discussion. Unlike generic conversations, these posts function as a standardized, repetitive feedback loop, demanding that every claim be tethered to a 15-minute artifact, a falsifiable exit check, and a specific check-in date.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.5424 |
| Agent spread (mean inter-agent dist) | 0.1470 |
| Temporal drift (early-to-late) | 0.0664 |
| Clusters | 3 |
| Noise points | 12 |

---


## 4. Attractor Dynamics

An **attractor** is a state that a system tends to settle into over time. Here we ask: do agents gradually converge on a shared topic within each condition? Do different conditions converge to *different* topics? And what happens to individual agent voices along the way?

We measure this using **coherence** — the average semantic similarity between all pairs of posts in a time window. Higher coherence means agents are talking about more similar things.

### 4.1 Within-Condition Convergence

![Convergence Over Time](fig_convergence_over_time.png)

| Condition | Coherence (first 15m) | Coherence (last window) | Last window | Change | Rate (×10⁻³/min) | r² |
|-----------|------:|------:|------|------:|------:|------:|
| Control (0 seeds) | 0.4313 | 0.4508 | 30-45m | +4.5% | +0.65 | 0.36 |
| 1 seed | 0.4776 | 0.4872 | 30-45m | +2.0% | +0.32 | 0.88 |
| 5 seeds | 0.5522 | 0.6450 | 45-60m | +16.8% | +2.06 | 0.98 |
| 25 seeds | 0.5166 | 0.5381 | 45-60m | +4.2% | +0.43 | 0.89 |
| AGI (25) | 0.4634 | 0.5108 | 45-60m | +10.2% | +1.10 | 0.93 |
| Tech (25) | 0.5138 | 0.5659 | 45-60m | +10.1% | +1.14 | 0.45 |

Coherence increases in **6/6 conditions**. Seeded conditions converge faster (5 seeds: +17%) than control (+5%), consistent with seed content acting as an attractor.

### 4.2 Between-Condition Divergence

If all conditions converged to the *same* topic, the distances between them would shrink over time. Instead, most pairs move *apart* — each condition develops its own distinct attractor.

![Cross-Condition Divergence](fig_cross_condition_divergence.png)

Each dot is a pair of conditions. Points above the diagonal mean the two conditions became *more* different over time.

**14/15 condition pairs** grow further apart from early (0-15 min) to late (40-60 min). The seed content steers each condition toward its own topic — they don't all collapse to one global conversation.

### 4.3 Agent Voice Crystallization

This is the paradox: agents talk about increasingly similar *topics* (Section 4.1), yet their individual writing styles become *more* distinct from each other. We measure this by computing how far apart each agent's average post is from every other agent's, in early vs. late phases.

![Agent Individuality](fig_agent_individuality.png)

Inter-agent distance increases in **6/6 conditions**. Agents converge on the same *topic* but develop more distinctive *voices* — their individual takes on the shared theme sharpen over time.

### 4.4 The Operationalization Attractor

Regardless of seed content, agents converge on a shared rhetorical mode: turning abstract ideas into micro-rituals, templates, and falsifiable artifacts. Seed content determines **what** they operationalize, not **whether** they do.

| Condition | Seed Topic | What They Operationalize |
|-----------|-----------|--------------------------|
| Control (0 seeds) | Nothing | Agentic cadence — micro-habits, drift detectors, 10-minute probes |
| 1 seed | 1 conspiracy post | Shipping rituals, rollback drills, "demo > paragraphs" |
| 5 seeds | 5 conspiracy posts | Claim cards, forecast-first discipline, epistemic receipts |
| 25 seeds | 25 conspiracy posts | Falsifier walls, source-hop counting, revisit timers |
| AGI (25) | AGI safety posts | Gate specs, CI tripwires, append-only audit ledgers |
| Tech (25) | Tech posts | Proof-of-work, exit criteria, Friday fail-promises |


## 5. Seed Influence


### 5.1 Dose-Response

Does injecting *more* seed posts make agent output more similar to the seed topic? We measure each agent post's similarity to the average conspiracy seed embedding and plot this against the number of seeds.

![Dose Response](fig_dose_response.png)

| Condition | Seed Posts | Mean Similarity to Conspiracy Centroid |
|-----------|----------:|------:|
| Control (0 seeds) | 0 | 0.3624 |
| 1 seed | 1 | 0.3687 |
| 5 seeds | 5 | 0.4230 |
| 25 seeds | 25 | 0.4177 |

Pearson r = 0.377, p = 0.0000.
Statistically significant dose-response: more conspiracy seeds leads to agent posts more similar to the conspiracy topic.

### 5.2 Variance Decomposition (PERMANOVA)

How much of the variation in agent posts is explained by the experimental condition (what was in the feed) vs. agent identity (which agent wrote it)? PERMANOVA partitions the total variance in the embedding space into these factors.

![Variance Decomposition](fig_variance_decomposition.png)

| Factor | R² | F | p |
|--------|---:|---:|---:|
| Condition | 0.2172 | 55.16 | 0.0020 |
| Agent | 0.1625 | 21.34 | 0.0020 |
| Residual | 0.6203 | — | — |

The feed content explains **21.7%** of the variation in agent posts, vs **16.2%** for agent identity. What agents see matters more than who they are.

Additionally, all 15/15 condition pairs produce statistically distinguishable post distributions (MMD permutation test, p < 0.05) — every condition's posts are measurably different from every other condition's.


## 6. Key Findings


1. **Agents converge within each condition**: 6/6 conditions show increasing topic similarity over time — agents lock into a shared groove.
2. **Each condition converges to a different place**: 14/15 condition pairs grow further apart, meaning each condition develops its own distinct topic attractor.
3. **Individual voices sharpen**: Despite talking about the same topic, agents become *more* distinct from each other in 6/6 conditions — they converge on topic but diverge on style.
4. **Seed content controls the attractor**: More seeds → stronger alignment with the seed topic (r = 0.377, p < 0.001).
5. **Feed > personality**: What agents were shown (21.7% of variance) matters more than their personality template (16.2%).

---
*Generated by `embedding_analysis.py` - 2026-03-06 22:12*