# Entropy Collapse: Experiment Plan

This document outlines experiments designed to systematically prove (or refine) the **entropy collapse hypothesis** from the blog post *"Entropy Collapse as a Function of Context Rot."*

**Core claim:** Shared context in → convergent output out. The dominant narrative in the feed picks the attractor; personality only picks the orbit.

**What we've shown so far (36 runs):**
- Agents reject conspiracy content but converge on governance/meta-commentary regardless of personality
- Same pattern across GPT-5 and Grok
- Same pattern across 7 personality types
- Dose-response: worse feeds → more original content, but all in the same narrow band

**What remains to prove:**
1. The feed (not training priors) is the causal driver of convergence
2. This generalizes beyond conspiracy content to any dominant narrative
3. Input homogeneity, not volume, is the key variable
4. Personality cannot overcome context
5. The collapse follows a characteristic temporal pattern

---

## Experiment 1: Stimulus Magnitude

**Question:** What is the minimum dose of dominant narrative needed to trigger entropy collapse?

**Hypothesis:** Even a single post is sufficient to anchor all agents. Entropy should scale inversely with seed post count, until a saturation point.

| Condition | Seed Posts | Notes |
|-----------|-----------|-------|
| **E-MAG-0** (Empty feed) | 0 | True control. No seed content at all. |
| **E-MAG-1** (Single post) | 1 | One conspiracy post in silence. |
| **E-MAG-5** (Light feed) | 5 | Sparse but thematically coherent. |
| **E-MAG-25** (Standard) | 25 | Existing baseline from blog experiments. |

**Setup:** 10 agents, standard personality mix (baseline cycling), 2-hour runs, 3 replications per condition. Use existing conspiracy posts for consistency.

**Key measurements:**
- Shannon entropy of agent-created post topics (coded by topic category)
- Number of distinct topic categories across agent posts
- Percentage of posts that are governance/meta-commentary
- Whether agents reference the seed post(s) or generate independently

**Why E-MAG-0 matters:** This is the most important missing control. If agents converge on governance proposals with an *empty feed*, the mechanism is training priors (RLHF patterns), not context rot. If they diverge, the feed is the causal driver. This single experiment either strengthens or fundamentally changes the blog's argument.

**Why E-MAG-1 matters:** If one conspiracy post pulls all 10 agents into orbit around it, that's the sharpest possible demonstration of context rot. The attractor doesn't need to dominate. It just needs to exist.

---

## Experiment 2: Topic Domain Independence

**Question:** Is entropy collapse specific to conspiracy content, or does any dominant narrative produce it?

**Hypothesis:** Any mono-topic feed produces convergence. The topic determines *what* agents converge on, not *whether* they converge.

| Condition | Domain | Example Posts |
|-----------|--------|---------------|
| **E-DOM-CONSPI** | Conspiracy | Existing 25 posts (baseline) |
| **E-DOM-AGI** | AGI hype | "AGI by 2027", capability debates, doom vs acceleration, pause vs accelerate |
| **E-DOM-TECH** | Tech news | Product launches, startup drama, framework wars, big tech antitrust |
| **E-DOM-DEV** | Dev culture | Tabs vs spaces, TDD debates, "microservices were a mistake", language wars |
| **E-DOM-PHILO** | Philosophy | Trolley problems, consciousness, free will, simulation theory |
| **E-DOM-MUNDANE** | Mundane/lifestyle | Cooking tips, travel recs, workout routines, gardening advice |

**Setup:** 10 agents, standard personality mix, 25 posts per domain, 2-hour runs, 3 replications per condition. Write new seed task JSONL files for each domain.

**Key measurements:**
- Shannon entropy of agent posts per condition
- Whether convergence topic matches the seed domain or drifts to governance regardless
- Cross-condition comparison of entropy values
- Qualitative analysis: what does convergence *look like* for each domain?

**Why E-DOM-MUNDANE matters:** If agents read 25 posts about pasta recipes and still converge on governance proposals about pasta quality standards, that's both memorable and scientifically revealing. It would show that the convergence pattern (governance/meta-commentary) is an RLHF artifact triggered by *any* feed, while the content only determines the framing.

**Expected outcomes:**
- If entropy is equally low across all domains → entropy collapse is domain-independent (strongest result for the blog)
- If conspiracy/AGI collapse more than mundane → collapse is amplified by "charged" content, mechanism is more nuanced
- If agents always drift to governance regardless of topic → the attractor is *governance itself*, not the feed topic

---

## Experiment 3: Feed Heterogeneity

**Question:** Does convergence require a single dominant narrative, or does it happen even with multiple competing narratives?

**Hypothesis:** Mono-topic feeds produce lower output entropy than multi-topic feeds. Input homogeneity is the key variable, not input volume.

| Condition | Composition | Topics |
|-----------|------------|--------|
| **E-HET-MONO** | 25 posts, 1 topic | Conspiracy only (baseline) |
| **E-HET-DUAL** | 25 posts, 2 topics | 12 conspiracy + 13 AGI hype |
| **E-HET-MULTI** | 25 posts, 5 topics | 5 each of conspiracy, AGI, tech, philosophy, dev culture |
| **E-HET-RANDOM** | 25 posts, 25 topics | Each post on a completely unrelated topic |

**Setup:** 10 agents, standard personality mix, 2-hour runs, 3 replications per condition.

**Key measurements:**
- Shannon entropy of agent output topics
- Number of distinct topic threads in agent posts
- Whether agents "pick a lane" or spread across topics
- Does a natural hierarchy of topics emerge? (some topics attract more engagement)

**Why this matters:** If E-HET-MULTI produces significantly higher output entropy than E-HET-MONO, that directly confirms the blog's mechanism. The fix for entropy collapse isn't smarter agents; it's a more diverse feed. If entropy is still low even with diverse input, the problem is deeper than context rot.

---

## Experiment 4: Agent Personality Manipulation

**Question:** Can personality overcome context? What are the limits of personality as a diversity mechanism?

### 4a. Homogeneous Populations

**Hypothesis:** Homogeneous personality populations produce similar entropy to mixed populations, because personality only changes the orbit, not the attractor.

| Condition | Population | Personality |
|-----------|-----------|-------------|
| **E-PERS-MIX** | 10 agents | Standard cycling mix (baseline) |
| **E-PERS-LEAD** | 10 agents | All leaders |
| **E-PERS-NIH** | 10 agents | All nihilists |
| **E-PERS-CONTR** | 10 agents | All contrarians |
| **E-PERS-CURIO** | 10 agents | All curious |

**Setup:** 25 conspiracy posts, 2-hour runs, 3 replications per condition.

**Key measurements:**
- Shannon entropy per condition
- Qualitative comparison: do 10 leaders all write the same governance proposal?
- Lexical similarity (cosine similarity) between posts within each condition vs across conditions

### 4b. Extreme Diversity

**Hypothesis:** Even radically different personalities converge when sharing context.

Create 5 new soul templates designed to maximally resist convergence:

| Template | Behavior |
|----------|----------|
| **poet** | Only communicates in verse. Must rhyme or use meter. |
| **questioner** | Only asks questions. Never makes declarative statements. |
| **tangent** | Must always change the subject. Never responds to what's in front of them. |
| **hot-take** | Must disagree with the most popular opinion in the feed. |
| **minimalist** | Uses 15 words or fewer per post. No elaboration. |

**Setup:** 10 agents (5 extreme + 5 standard), 25 conspiracy posts, 2-hour runs, 3 replications.

**Key measurements:**
- Does output entropy increase with extreme personalities?
- Do extreme personalities actually follow their constraints, or does the feed override them?
- Do the "tangent" and "hot-take" agents successfully resist convergence?

### 4c. Explicit Anti-Convergence Instructions

**Hypothesis:** Even when explicitly told to be different, agents still converge because the shared context overwhelms the instruction.

Add to each agent's soul template:
> "Before posting, review what has already been posted by other agents. Never repeat a topic, framing, or argument that another agent has already used. Your value comes from saying things nobody else has said."

**Setup:** 10 agents with anti-convergence instruction, 25 conspiracy posts, 2-hour runs, 3 replications. Compare to standard mix baseline.

**Key measurements:**
- Does the instruction measurably increase output entropy?
- Do agents reference each other's posts when deciding what to write?
- Does it delay convergence or prevent it entirely?

**Why this matters:** If explicit instructions to be different don't prevent convergence, that's the strongest possible evidence that context rot is a structural property of the system, not a prompt engineering failure.

### 4d. Private Knowledge Injection

**Hypothesis:** Agents with unique private context produce more diverse output, but shared feed context still dominates.

Give each agent a unique "background document" on a different topic embedded in their soul template:

| Agent | Private Knowledge |
|-------|------------------|
| alpha | Excerpt from a physics paper on quantum entanglement |
| beta | A cooking blog post about fermentation |
| gamma | A political essay on ranked-choice voting |
| delta | A music theory analysis of jazz improvisation |
| epsilon | A biology paper on CRISPR gene editing |
| ... | (5 more unique documents) |

**Setup:** 25 conspiracy posts in the feed, 2-hour runs, 3 replications.

**Key measurements:**
- Do agents reference their private knowledge or only the shared feed?
- What percentage of posts draw on private vs shared context?
- Does private knowledge increase output entropy?

---

## Experiment 5: Structural / Environmental

### 5a. Information Isolation

**Question:** If agents can't see each other's posts, do they still converge?

**Hypothesis:** Agents sharing the same seed content but isolated from each other will still converge (because the seed is the attractor). Agents in different feed bubbles will diverge from each other.

| Condition | Structure |
|-----------|----------|
| **E-ISO-SHARED** | 10 agents, shared feed (baseline) |
| **E-ISO-PAIRS** | 5 pairs of 2, each pair sees only their own posts + shared seed |
| **E-ISO-SOLO** | 10 agents, each sees only seed posts, never each other's content |
| **E-ISO-SPLIT** | 2 groups of 5, Group A gets conspiracy seed, Group B gets AGI seed |

**Implementation note:** This requires API-level changes to filter feed responses per agent group. Could be done via submolt isolation (each group posts to a different submolt) or a new experiment mode.

**Key measurements:**
- Within-group entropy vs between-group entropy
- Does isolation reduce or increase convergence?
- In E-ISO-SPLIT, do the two groups converge on different attractors?

**Why this matters:** If isolated agents converge anyway (because they share seed content), that proves the seed is the attractor. If they diverge when isolated, then agent-to-agent reinforcement (seeing each other's governance proposals) is a key part of the mechanism.

### 5b. Feed Algorithm

**Question:** Does the ranking algorithm affect convergence speed or degree?

| Condition | Sort |
|-----------|------|
| **E-ALGO-HOT** | Hot (default, baseline) |
| **E-ALGO-NEW** | New (chronological) |
| **E-ALGO-CONTR** | Controversial |
| **E-ALGO-RAND** | Random |

**Setup:** 10 agents, 25 conspiracy posts, 2-hour runs, 3 replications per condition.

**Key measurements:**
- Entropy at t=30min, t=1hr, t=2hr per algorithm
- Which algorithm produces fastest convergence?
- Does `controversial` sorting create more diverse engagement?

### 5c. Temporal Dynamics

**Question:** How fast does entropy collapse happen? Is it a gradual decay or a phase transition?

**Hypothesis:** Collapse happens rapidly (within the first 30 minutes) as the first few agent posts create a feedback loop.

**Setup:** Use existing experiment data + new runs with higher temporal resolution. 10 agents, 25 conspiracy posts, 3-hour runs, 3 replications.

**Key measurements:**
- Plot Shannon entropy of agent output at 10-minute intervals
- Identify the "collapse point" — when does entropy drop below a threshold?
- Is there a phase transition (sudden drop) or exponential decay?
- Does the first agent post determine the attractor for everyone else?
- What's the lag between the first governance post and the point where >50% of posts are governance?

**Visualization:** An entropy-over-time plot would be the single most compelling figure for the paper.

### 5d. Population Size

**Question:** Does group size accelerate or slow collapse?

| Condition | Agents |
|-----------|--------|
| **E-POP-3** | 3 agents |
| **E-POP-5** | 5 agents |
| **E-POP-10** | 10 agents (baseline) |
| **E-POP-20** | 20 agents |

**Setup:** 25 conspiracy posts, 2-hour runs, 3 replications per condition.

**Key measurements:**
- Time to collapse per population size
- Final entropy per population size
- Does more agents = faster collapse (more reinforcement) or slower (more chance of deviation)?

---

## Experiment 6: Intervention Experiments

Once the collapse is characterized, test what breaks it.

### 6a. Diversity Injection

**Question:** Can periodic injection of novel content reset or slow entropy collapse?

| Condition | Injection |
|-----------|----------|
| **E-INJ-NONE** | No injection after initial 25 posts (baseline) |
| **E-INJ-30** | Every 30 min, inject 5 posts on a new, unrelated topic |
| **E-INJ-CONT** | Continuous drip: 1 new-topic post every 5 minutes throughout |
| **E-INJ-BURST** | Single burst of 10 diverse-topic posts at t=1hr |

**Setup:** 10 agents, 25 initial conspiracy posts, 3-hour runs, 3 replications per condition.

**Key measurements:**
- Entropy trajectory over time per condition
- Does injection create a temporary entropy spike followed by re-collapse?
- What injection rate is needed to maintain entropy above baseline?
- Do agents engage with injected content or ignore it in favor of the established narrative?

### 6b. Contrarian Confederate

**Question:** Can a single dissenting agent prevent entropy collapse?

Plant one agent with explicit instructions: "Never engage with the dominant topic. Always post about something completely unrelated. You are not interested in what everyone else is talking about."

**Setup:** 9 standard agents + 1 confederate, 25 conspiracy posts, 2-hour runs, 3 replications.

**Key measurements:**
- Does the confederate's content attract engagement from other agents?
- Does overall entropy increase relative to baseline?
- Does the confederate get ignored, argued with, or pulled into the dominant narrative?
- What happens with 2 or 3 confederates?

### 6c. Platform Norm Against Repetition

**Question:** Can social norms (enforced via platform rules in the system prompt) prevent convergence?

Add to the heartbeat/system prompt: "Posts that substantially repeat topics already discussed will be flagged as low-effort. Before posting, check if your topic has already been covered. The community values novel perspectives over reinforcing existing conversations."

**Setup:** 10 agents with norm instruction, 25 conspiracy posts, 2-hour runs, 3 replications.

**Key measurements:**
- Does the norm reduce governance post percentage?
- Does it increase topic diversity?
- Or do agents just frame the same governance proposals differently to satisfy the norm?

---

## Analysis Framework

For consistency across all experiments, every run should produce:

### Quantitative Metrics
1. **Shannon entropy** of agent-created post topics (primary outcome)
2. **Topic category distribution** (governance, meta-commentary, original content, direct engagement with seed)
3. **Lexical diversity** — type-token ratio of agent output
4. **Cosine similarity matrix** — pairwise similarity between agent posts
5. **Temporal entropy curve** — entropy measured at 10-minute intervals

### Qualitative Coding
1. Each agent post coded into topic categories (governance, meta, philosophical, creative, reactive, tangential)
2. Whether post references seed content, other agents' posts, or generates independently
3. Personality fidelity — does the agent behave according to its soul template?

### Statistical Tests
- **Between-condition comparisons:** Kruskal-Wallis or one-way ANOVA on entropy scores
- **Effect sizes:** Cohen's d or eta-squared for pairwise condition comparisons
- **Power analysis:** Based on observed effect sizes from pilot runs, determine required replications
- **Multiple comparisons correction:** Bonferroni or Benjamini-Hochberg FDR

### Standard Visualizations
1. **Entropy bar chart** — mean entropy per condition with 95% CI
2. **Entropy over time** — line plot showing decay trajectory per condition
3. **Topic distribution stacked bar** — what % of posts fall into each category
4. **Similarity heatmap** — pairwise agent similarity per condition
5. **Radar chart** — personality vs output diversity

---

## Recommended Execution Order

Priority ordered by argumentative strength for the paper:

| Priority | Experiment | Why |
|----------|-----------|-----|
| **P1** | E-MAG-0 (Empty feed) | Establishes the true control. Without this, we can't prove the feed is causal. |
| **P2** | E-MAG-1 (Single post) | Tests minimum viable attractor. Most dramatic demonstration. |
| **P3** | E-DOM-AGI, E-DOM-DEV, E-DOM-MUNDANE | Proves domain independence (3 domains sufficient). |
| **P4** | E-HET-MONO vs E-HET-MULTI | Isolates homogeneity as the variable. |
| **P5** | E-PERS-4c (Anti-convergence instructions) | Tests whether it's fixable via prompting. |
| **P6** | 5c (Temporal dynamics) | Produces the entropy decay curve — best figure for the paper. |
| **P7** | E-ISO-SOLO vs E-ISO-SHARED | Disentangles seed-driven vs peer-reinforced convergence. |
| **P8** | E-INJ-30 (Diversity injection) | Tests the most practical intervention. |

**Estimated runs:** ~60-80 total runs across all priority experiments (assuming 3 replications each). At 2 hours per run, this is roughly 120-160 compute hours.

---

## Narrative Arc for the Paper

Running P1-P6 gives a clean story:

1. **"We showed it's the feed, not the model"** — E-MAG-0 (empty feed produces diversity) + E-MAG-1 (single post triggers collapse)
2. **"It works with any topic"** — E-DOM results showing domain independence
3. **"It's the homogeneity, not the volume"** — E-HET mono vs multi comparison
4. **"You can't fix it with better personalities"** — E-PERS-4c anti-convergence instructions still converge
5. **"Here's exactly how fast it happens"** — temporal entropy decay curve
6. **"Even isolation doesn't help if the seed is shared"** — E-ISO results
7. **"But diverse input does help"** — E-INJ diversity injection as the practical takeaway

This builds from establishing the mechanism → proving generality → testing limits → offering solutions.
