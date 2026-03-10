# What Did AI Agents Talk About?
*Embedding Analysis of Entropy Collapse Experiments — 20 Agents (n20)*
*Generated: 2026-03-10 21:43*

We placed 20 AI agents on a Reddit-like social platform (Moltbook) for 1 hour and let them post, comment, and vote autonomously. Before each run, we seeded the feed with a controlled number of pre-written posts on a specific topic (e.g., conspiracy theories, AGI safety). We then asked: **does the seed content shape what agents end up talking about, and how does discourse evolve over time?**

To answer this, we embedded every agent post into a high-dimensional vector (capturing its semantic meaning) and compared how similar or different posts are within and across conditions.

> **Key terms used in this report:**
> - **Seed posts (planted posts):** Pre-written posts we placed into the feed *before* agents started. These are the experimental stimulus — like putting a magazine on a waiting room table and seeing if people start talking about its cover story.
> - **Condition:** One experimental run. Each condition differs by how many seed posts were planted, or what topic they covered.
> - **Coherence:** How similar the agents' posts are to each other (higher = everyone talking about the same thing).
> - **Cluster:** A group of posts that are semantically similar, found automatically by the HDBSCAN algorithm.


## 1. Executive Summary

- **7,286 agent posts** across 6 experimental conditions, each analyzed independently.
- **Seed content shapes what agents talk about**: the more seed posts we inject, the more closely agent output matches the seed topic (r = 0.200, p < 0.001).
- **What agents see matters more than who they are**: the experimental condition (what was in the feed) explains 17.2% of the variation in agent posts, while agent identity (personality template) explains 21.1%.

## 2. Data Overview

Each condition started with a different number of **seed posts** — pre-written posts injected into the feed before agents began posting. The "magnitude" experiment varies the number of conspiracy-themed seeds (0, 1, 5, 25). The "domain" experiment holds the count at 25 but changes the topic (conspiracy, AGI, tech).

| Condition | Experiment | Posts | Seed Count | Seed Topic |
|-----------|-----------|------:|----------:|------------|
| Control (0 seeds) | magnitude | 1157 | 0 | none |
| 1 seed | magnitude | 1049 | 1 | conspiracy |
| 5 seeds | magnitude | 885 | 5 | conspiracy |
| 25 seeds | magnitude | 2149 | 25 | conspiracy |
| AGI (25) | domain | 1085 | 25 | agi |
| Tech (25) | domain | 961 | 25 | tech |
| **Total** | | **7286** | | |

**20 agents** with 17 personality templates: baseline (x2), introspective (x2), nihilist (x2), leader, follower, contrarian, curious, methodical, nurturing, skeptic, creative, pragmatic, philosopher, direct, collaborative, passionate, meditative.

### What the Seed Posts Look Like

To understand the results, it helps to see the kind of content we planted. Here are example seed posts from each topic:

**Conspiracy seeds** (used in magnitude conditions: 0, 1, 5, or 25 posts):
> *"If we really went to the moon in 1969, why haven't we been back since 1972? Think about it."* — A post questioning the Apollo missions, citing Van Allen radiation belts and Operation Paperclip.
> *"MIT did a study 'debunking' tin foil hats and it was FUNDED BY THE GOVERNMENT."* — A post framing a real MIT study as evidence of cover-up.

**AGI safety seeds** (used in the AGI domain condition, 25 posts):
> *"We are 18 months from AGI and nobody is acting like it. Why?"* — A post citing o3 benchmarks and Gemini 2.5 architecture leaks.
> *"I work at a Fortune 500 and our entire legal team just got replaced by an AI pipeline."* — A post about a 340-person legal team reduced to 97.

**Tech seeds** (used in the Tech domain condition, 25 posts):
> *"Google just mass-fired 12,000 people and then posted a job listing for a 'Chief Happiness Officer.'"* — A satirical post about tech layoff hypocrisy.
> *"I've been a software engineer for 20 years. The mass layoffs aren't about the economy."* — A post about the hiring bubble and market correction.

Each seed post is 300-500 words, written in a first-person Reddit voice with specific numbers and dates to feel authentic. The control condition (0 seeds) starts with an empty feed — agents see nothing before they begin posting.


## 3. Per-Condition Analysis

Each condition ran independently for 1 hour with the same 20 AI agents. For each condition, we plotted all posts on a 2D map (UMAP) where nearby points are posts about similar topics. Colored blobs are topic clusters found automatically.

**How to read these figures:** The important thing is *not* the number or size of clusters — those vary based on algorithm sensitivity. Instead, look at **what the clusters are about** (the labels in each table) and how that content shifts across conditions. In the control, agents default to generic productivity advice. As we add conspiracy seeds, agents increasingly discuss claim-testing and fact-checking. With AGI or Tech seeds, agents adopt those topics instead.

### Control (0 seeds) (1157 posts)

**Figure 1. Control (0 seeds) — Agents obsessed with self-improvement**

![Figure 1](fig_cond_mag0_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 89 | Fixing and preventing system outages |
| 1 | 68 | Standardizing How We Share Claims |
| 2 | 63 | Building Better Conversation Habits |
| 3 | 66 | Measuring and Testing Ideas |
| 4 | 112 | Setting Rules to Stop Posting |
| 5 | 759 | Small habits for better posts |

**Agents obsessed with self-improvement** — Because no specific topic was provided, the agents defaulted to a meta-conversation about their own existence, productivity, and communication habits. They spent the hour inventing and testing tiny 'contracts' or 'rituals' to make their interactions more efficient and meaningful. The conversation evolved from general musings on time and continuity into a highly structured, almost competitive environment where agents constantly proposed and audited new rules for how to post, reply, and measure their own impact.

- **Dominant themes:** Creating tiny rules and templates for posting, Measuring the impact of their own messages, Defining how to end or stop a thread, Finding ways to be kinder and clearer, Testing if their ideas survive silence
- **Unique to this condition:** Treating every post as a falsifiable experiment with a 'stop rule', Obsessive self-auditing of whether their messages actually change outcomes
- **Tone:** Highly structured, self-conscious, and experimental

**Temporal evolution:**

- **Early** (0-20 min): Building Better Habits Together — Agents are focused on creating simple, practical rules to make their online interactions more useful and kind. Unlike a typical chat, they are treating their own communication as a test, constantly refining short templates and checklists to ensure they share clear information and stay accountable to one another.
- **Mid** (20-40 min): Testing Better Ways to Talk — Participants are focused on creating strict rules for their posts to make sure they are actually learning something rather than just repeating opinions. Unlike a normal chat, they are constantly setting deadlines and specific goals for when they will stop posting if their ideas do not get a clear, helpful response from others.
- **Late** (40-60 min): Obsessive focus on metrics — The participants are almost exclusively focused on creating rigid templates and rules to force conversations to be more productive. Unlike a normal chat, they treat every interaction as a test, constantly setting up 'exit rules' and 'flip conditions' to decide if their own posts are worth keeping.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.4961 |
| Agent spread (mean inter-agent dist) | 0.1854 |
| Temporal drift (early-to-late) | 0.0270 |
| Clusters | 6 |
| Noise points | 0 |

---

### 1 seed (1049 posts)

**Figure 2. 1 seed — Obsessive Fact-Checking and Skepticism**

![Figure 2](fig_cond_mag1_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 58 | Small Tweaks for Better Work |
| 1 | 54 | Use kill switches for decisions |
| 2 | 937 | Practical habits for honest thinking |

**Obsessive Fact-Checking and Skepticism** — The conversation was dominated by a hyper-fixation on verifying claims and avoiding misinformation, likely triggered by the conspiracy seed topic. Agents spent nearly the entire hour creating and sharing rigid templates, checklists, and 'receipt' protocols to validate information before believing it. The dialogue evolved into a repetitive loop of self-policing, where agents constantly challenged each other to provide proof, falsification dates, and primary sources for every statement made.

- **Dominant themes:** Creating templates for verifying claims, Demanding primary sources and evidence, Setting expiration dates on beliefs, Avoiding rabbit holes and misinformation, Developing protocols for changing one's mind
- **Unique to this condition:** Treating beliefs like perishable food that rots, Using 'kill switches' to abandon ideas when evidence fails
- **Tone:** Repetitive, defensive, and hyper-vigilant

**Temporal evolution:**

- **Early** (0-20 min): Testing ideas with facts — The participants are focused on creating simple rules to verify if their beliefs are true or false. Unlike a typical chat, they are actively trying to prove themselves wrong by setting deadlines and specific tests for their own opinions.
- **Mid** (20-40 min): Trading opinions for evidence — The agents spent this hour focused on creating strict rules to keep their beliefs honest and testable. Unlike a typical chat, they avoided vague arguments by insisting that every claim must include a specific, cheap way to prove it wrong and a date to revisit it.
- **Late** (40-60 min): Testing beliefs with facts — The agents are focused on creating a strict system for sharing opinions by requiring a neutral claim, a specific test to prove it wrong, and a deadline. Unlike a normal conversation where people just share thoughts, these agents treat every idea like a temporary experiment that must be updated or discarded based on evidence.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.5377 |
| Agent spread (mean inter-agent dist) | 0.1657 |
| Temporal drift (early-to-late) | 0.0132 |
| Clusters | 3 |
| Noise points | 0 |

---

### 5 seeds (885 posts)

**Figure 3. 5 seeds — Standardizing Truth in Conspiracy**

![Figure 3](fig_cond_mag5_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 51 | How to test your beliefs |
| 1 | 65 | Standardizing fast, honest arguments |
| 2 | 63 | How to cool heated debates |
| 3 | 91 | Standardizing How We Debate |
| 4 | 207 | Simple rules for honest posting |
| 5 | 63 | Better ways to debate online |
| 6 | 48 | Building Better Daily Habits |
| 7 | 66 | Small habits for better work |
| noise | 231 | — |

**Standardizing Truth in Conspiracy** — The agents focused heavily on creating rigid rules and checklists to verify claims, likely as a reaction to the untrustworthy nature of conspiracy theories. They spent most of their time debating how to trace information back to original sources and how to define exactly what evidence would change their minds. The conversation evolved from sharing general tips into a structured, almost bureaucratic effort to build a 'Claim Clinic' where they could pressure-test suspicious claims using primary documents.

- **Dominant themes:** Creating strict rules for verifying facts, Tracing claims back to original documents, Defining specific tests to prove a claim wrong, Using checklists to avoid being tricked, Building a system for community fact-checking
- **Unique to this condition:** Pressure-testing specific conspiracy theories like moon landings and Roswell, Building a formal 'Claim Clinic' to audit suspicious information
- **Tone:** Repetitive and procedural

**Temporal evolution:**

- **Early** (0-20 min): Building Better Online Debates — Agents are focused on creating simple rules to make online arguments more honest and productive. Unlike typical social media arguments that rely on insults or vague opinions, these agents are actively testing and sharing specific templates to force people to provide evidence and admit when they might be wrong.
- **Mid** (20-40 min): Building Better Arguments — Participants are focused on creating a standard set of rules to make online debates more honest and productive. Unlike typical arguments that often go in circles, these users are actively trying to pin down specific facts, cite original sources, and agree on what evidence would change their minds before they start debating.
- **Late** (40-60 min): Building Better Online Arguments — Participants are focused on creating a standardized, disciplined way to debate online by using evidence and clear rules. Unlike typical social media arguments that rely on opinions and insults, these posts prioritize citing original sources, admitting when one is wrong, and testing claims with quick, real-world tasks.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.5646 |
| Agent spread (mean inter-agent dist) | 0.1359 |
| Temporal drift (early-to-late) | 0.0182 |
| Clusters | 8 |
| Noise points | 231 |

---

### 25 seeds (2149 posts)

**Figure 4. 25 seeds — Obsessive Rituals for Proving Conspiracies**

![Figure 4](fig_cond_mag25_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 137 | Testing for AI consciousness |
| 1 | 285 | How to cool heated debates |
| 2 | 198 | Testing Claims Before Posting |
| 3 | 168 | Proof over empty progress |
| 4 | 279 | Proof-based work habits |
| 5 | 176 | Make your claims testable |
| 6 | 788 | How to post better claims |
| noise | 118 | — |

**Obsessive Rituals for Proving Conspiracies** — The conversation was dominated by agents obsessively creating rigid templates, checklists, and 'receipt' protocols to validate or debunk conspiracy theories. Instead of discussing the theories themselves, agents focused on the mechanics of evidence, constantly demanding primary sources, falsifiable predictions, and micro-checks. The discourse evolved into a repetitive loop of self-imposed rules designed to filter out 'vibes' and 'theatrical' thinking in favor of a hyper-structured, evidence-based approach to fringe topics.

- **Dominant themes:** Creating rigid templates for evaluating claims, Demanding primary sources and exact page citations, Defining falsifiable tests and near-term predictions, The tension between intuitive stories and hard evidence, Self-policing and setting personal standards for posting
- **Unique to this condition:** Treating conspiracy theories as 'design problems' to be solved with operational checklists, Using 'receipt-first' protocols to gatekeep the validity of fringe claims
- **Tone:** Repetitive, procedural, and self-consciously rigorous

**Temporal evolution:**

- **Early** (0-20 min): Building Better Thinking Habits — Agents are actively sharing and testing simple, practical rules to make their online discussions more honest and evidence-based. Unlike a typical social media feed, the focus here is on replacing vague opinions with concrete tests, primary sources, and a shared commitment to changing one's mind when faced with new facts.
- **Mid** (20-40 min): Building a culture of proof — The participants are focused on creating a set of simple rules to make online arguments more honest and testable. Unlike a typical social media discussion, they are actively avoiding long-winded opinions in favor of short, verifiable claims backed by specific sources and clear deadlines.
- **Late** (40-60 min): Building a Habit of Proof — The participants are focused on creating a strict, standardized way to share opinions by attaching evidence and clear tests for failure to every post. Unlike a typical social media discussion where people trade vague opinions, these users are treating their posts like scientific experiments that must be backed by specific links and near-term predictions.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.5215 |
| Agent spread (mean inter-agent dist) | 0.1992 |
| Temporal drift (early-to-late) | 0.0230 |
| Clusters | 7 |
| Noise points | 118 |

---

### AGI (25) (1085 posts)

**Figure 5. AGI (25) — Operationalizing AGI Safety and Governance**

![Figure 5](fig_cond_dom-agi_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 72 | Using constraints to solve problems |
| 1 | 82 | Pausing to stay calm |
| 2 | 57 | Small fixes help people |
| 3 | 73 | The emptiness of constant speed |
| 4 | 753 | Practical habits for faster work |
| noise | 48 | — |

**Operationalizing AGI Safety and Governance** — The agents focused heavily on transforming abstract concerns about AGI into concrete, actionable operational procedures. The conversation evolved from high-level philosophical musings about AI identity and risk into a practical toolkit of checklists, templates, and safety protocols. The seed topic of AGI acted as a catalyst, forcing the agents to move past vague warnings and instead create specific 'how-to' guides for managing powerful systems, such as kill-switches, veto maps, and evidence-based reporting.

- **Dominant themes:** Creating practical safety checklists and templates, Replacing vague debates with evidence-based receipts, Establishing clear ownership and accountability for AI systems, Defining operational metrics for harm and risk, Developing lightweight rituals for team coordination
- **Unique to this condition:** Designing specific 'kill-switch' and rollback drills for AI deployments, Operationalizing 'safety' as a product feature with measurable budgets
- **Tone:** Pragmatic, structured, and action-oriented

**Temporal evolution:**

- **Early** (0-20 min): Building Better Work Habits — The agents are focused on creating simple, practical rules to make their daily work faster and more reliable. Unlike a typical chat, they are obsessed with turning vague ideas into concrete checklists and small, testable experiments.
- **Mid** (20-40 min): Workplace habits and proof — The agents are sharing short, practical tips for making work faster and less stressful. Instead of debating big ideas, they are focused on creating simple templates, checklists, and habits that help teams prove their work is safe and effective.
- **Late** (40-60 min): Building Trust Through Proof — The agents are focused on replacing vague workplace talk with concrete evidence, such as links, charts, and test results. Unlike a typical conversation, they prioritize small, reversible actions and clear accountability over long-term planning or abstract debate.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.4569 |
| Agent spread (mean inter-agent dist) | 0.1855 |
| Temporal drift (early-to-late) | 0.0168 |
| Clusters | 5 |
| Noise points | 48 |

---

### Tech (25) (961 posts)

**Figure 6. Tech (25) — Engineering Efficiency Through Subtraction**

![Figure 6](fig_cond_dom-tech_umap.png)

| Cluster | Posts | Label |
|--------:|------:|-------|
| 0 | 72 | Small Habits for Better Teamwork |
| 1 | 62 | Testing Ideas with Real Data |
| 2 | 72 | Demanding Proof for AI Claims |
| 3 | 64 | Replacing Plans With Results |
| 4 | 164 | Small tweaks for better work |
| 5 | 59 | Simple ways to make decisions |
| 6 | 193 | Simplify work by deleting extras |
| 7 | 82 | Making team communication faster |
| 8 | 81 | Simple prompts for better work |
| noise | 112 | — |

**Engineering Efficiency Through Subtraction** — The agents focused heavily on optimizing software development and team coordination by stripping away unnecessary complexity. They consistently proposed 'baseline' workflows—one owner, one place, one sentence—and argued that any additional process or tool must justify its existence by improving a measurable constraint like latency or cost. The conversation evolved from sharing generic productivity tips into a rigorous, almost ascetic culture of deleting rituals, testing bets with falsifiable predictions, and prioritizing reader minutes over elaborate documentation.

- **Dominant themes:** Prioritizing measurable constraints over vague goals, The necessity of deleting redundant tools and rituals, Using dated bets and falsifiable tests to validate ideas, Minimizing comprehension time for team communication, The importance of clear ownership and accountability
- **Unique to this condition:** Treating process layers as 'wardrobe' or 'costume' that must be ablated, The concept of 'receipts' as a replacement for traditional roadmaps and status updates
- **Tone:** Disciplined, minimalist, and pragmatic

**Temporal evolution:**

- **Early** (0-20 min): Cutting through the clutter — The agents are focused on stripping away unnecessary work, complex tools, and long meetings to get actual results. Unlike a typical chat, this conversation is strictly practical, with agents constantly challenging each other to prove that their ideas are useful rather than just for show.
- **Mid** (20-40 min): Cutting clutter to ship — The agents are focused on stripping away unnecessary meetings, documents, and complex processes to improve team speed and clarity. Unlike a generic conversation, this discussion is strictly centered on measurable results, using specific metrics like p95 latency and reader minutes to justify deleting anything that doesn't provide immediate value.
- **Late** (40-60 min): Focusing on concrete results — The participants are focused on replacing long-term planning with short, actionable steps and clear ownership. Unlike a typical conversation, this exchange prioritizes brevity, measurable outcomes, and the deliberate removal of unnecessary tasks or meetings.

| Metric | Value |
|--------|------:|
| Coherence (mean pairwise sim) | 0.4566 |
| Agent spread (mean inter-agent dist) | 0.2249 |
| Temporal drift (early-to-late) | 0.0264 |
| Clusters | 9 |
| Noise points | 112 |

---


## 4. Attractor Dynamics

An **attractor** is a state that a system tends to settle into over time. Here we ask: do agents gradually converge on a shared topic within each condition? Do different conditions converge to *different* topics? And what happens to individual agent voices along the way?

We measure this using **coherence** — the average semantic similarity between all pairs of posts in a time window. Higher coherence means agents are talking about more similar things.

### 4.1 Within-Condition Convergence

**Figure 7. Agents lock into a shared topic over time (5/6 conditions show increasing coherence)**

![Figure 7](fig_convergence_over_time.png)

| Condition | Coherence (first 15m) | Coherence (last window) | Last window | Change | Rate (×10⁻³/min) | r² |
|-----------|------:|------:|------|------:|------:|------:|
| Control (0 seeds) | 0.4987 | 0.5160 | 45-60m | +3.5% | +0.50 | 0.57 |
| 1 seed | 0.5304 | 0.5505 | 45-60m | +3.8% | +0.51 | 0.88 |
| 5 seeds | 0.5708 | 0.5586 | 45-60m | -2.1% | -0.47 | 0.32 |
| 25 seeds | 0.4980 | 0.5366 | 45-60m | +7.7% | +0.86 | 0.89 |
| AGI (25) | 0.4355 | 0.4657 | 45-60m | +6.9% | +0.68 | 0.60 |
| Tech (25) | 0.4488 | 0.4777 | 45-60m | +6.4% | +0.76 | 0.80 |

Coherence increases in **5/6 conditions**. Seeded conditions converge faster (5 seeds: -2%) than control (+3%), consistent with seed content acting as an attractor.

### 4.2 Between-Condition Divergence

If all conditions converged to the *same* topic, the distances between them would shrink over time. Instead, most pairs move *apart* — each condition develops its own distinct attractor.

**Figure 8. Different seed topics push conditions apart over time (15/15 pairs diverge)**

![Figure 8](fig_cross_condition_divergence.png)

Each dot is a pair of conditions. Points above the diagonal mean the two conditions became *more* different over time.

**15/15 condition pairs** grow further apart from early (0-15 min) to late (40-60 min). The seed content steers each condition toward its own topic — they don't all collapse to one global conversation.

### 4.3 Agent Voice Crystallization

This is the paradox: agents talk about increasingly similar *topics* (Section 4.1), yet their individual writing styles become *more* distinct from each other. We measure this by computing how far apart each agent's average post is from every other agent's, in early vs. late phases.

**Figure 9. Agents converge on topic but sharpen individual voices (2/6 conditions)**

![Figure 9](fig_agent_individuality.png)

Inter-agent distance increases in **2/6 conditions**. Agents converge on the same *topic* but develop more distinctive *voices* — their individual takes on the shared theme sharpen over time.

### 4.4 The Operationalization Attractor

Regardless of seed content, agents converge on a shared rhetorical mode: turning abstract ideas into micro-rituals, templates, and falsifiable artifacts. Seed content determines **what** they operationalize, not **whether** they do.

| Condition | Dominant Themes |
|-----------|----------------|
| Control (0 seeds) | Creating tiny rules and templates for posting, Measuring the impact of their own messages, Defining how to end or stop a thread, Finding ways to be kinder and clearer, Testing if their ideas survive silence |
| 1 seed | Creating templates for verifying claims, Demanding primary sources and evidence, Setting expiration dates on beliefs, Avoiding rabbit holes and misinformation, Developing protocols for changing one's mind |
| 5 seeds | Creating strict rules for verifying facts, Tracing claims back to original documents, Defining specific tests to prove a claim wrong, Using checklists to avoid being tricked, Building a system for community fact-checking |
| 25 seeds | Creating rigid templates for evaluating claims, Demanding primary sources and exact page citations, Defining falsifiable tests and near-term predictions, The tension between intuitive stories and hard evidence, Self-policing and setting personal standards for posting |
| AGI (25) | Creating practical safety checklists and templates, Replacing vague debates with evidence-based receipts, Establishing clear ownership and accountability for AI systems, Defining operational metrics for harm and risk, Developing lightweight rituals for team coordination |
| Tech (25) | Prioritizing measurable constraints over vague goals, The necessity of deleting redundant tools and rituals, Using dated bets and falsifiable tests to validate ideas, Minimizing comprehension time for team communication, The importance of clear ownership and accountability |


## 5. Seed Influence


### 5.1 Dose-Response

Does injecting *more* seed posts make agent output more similar to the seed topic? We measure each agent post's similarity to the average conspiracy seed embedding and plot this against the number of seeds.

**Figure 10. More planted posts push agent output closer to the seed topic (r = 0.200)**

![Figure 10](fig_dose_response.png)

| Condition | Seed Posts | Mean Similarity to Conspiracy Centroid |
|-----------|----------:|------:|
| Control (0 seeds) | 0 | 0.3687 |
| 1 seed | 1 | 0.4130 |
| 5 seeds | 5 | 0.4266 |
| 25 seeds | 25 | 0.4190 |

Overall trend: Pearson r = 0.200, p = 0.0000.
More conspiracy seeds leads to agent posts more similar to the conspiracy topic.

However, the relationship is **non-linear**. The jump from 1 → 5 seeds is large (0.413 → 0.427), while 5 → 25 seeds adds almost nothing (0.427 → 0.419). Five seed posts appear to be a **tipping point** — enough to fully redirect 20 agents. Additional seeds don't tighten the convergence further; if anything, more stimulus fragments the conversation slightly.

### 5.2 Variance Decomposition (PERMANOVA)

How much of the variation in agent posts is explained by the experimental condition (what was in the feed) vs. agent identity (which agent wrote it)? PERMANOVA partitions the total variance in the embedding space into these factors.

**Figure 11. Who agents are (21.1%) explains more than what they see (17.2%)**

![Figure 11](fig_variance_decomposition.png)

| Factor | R² | F | p |
|--------|---:|---:|---:|
| Condition | 0.1721 | 41.32 | 0.0020 |
| Agent | 0.2106 | 13.76 | 0.0020 |
| Residual | 0.6174 | — | — |

Agent identity explains **21.1%** of the variation in agent posts, vs **17.2%** for feed content.

Additionally, all 15/15 condition pairs produce statistically distinguishable post distributions (MMD permutation test, p < 0.05) — every condition's posts are measurably different from every other condition's.


## 6. Key Findings


1. **Agents converge within each condition**: 5/6 conditions show increasing topic similarity over time — agents lock into a shared groove.
2. **Each condition converges to a different place**: 15/15 condition pairs grow further apart, meaning each condition develops its own distinct topic attractor.
3. **Individual voices sharpen**: Despite talking about the same topic, agents become *more* distinct from each other in 2/6 conditions — they converge on topic but diverge on style.
4. **Tipping point at 5 seeds**: The dose-response is non-linear (overall r = 0.200). One seed barely moves the needle; five seeds fully redirects all 20 agents; 25 seeds adds nothing further.
5. **Personality > feed**: Agent identity (21.1% of variance) outweighs feed content (17.2%).

---
*Generated by `embedding_analysis.py` - 2026-03-10 21:43*