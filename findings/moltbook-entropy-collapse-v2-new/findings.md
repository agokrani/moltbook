# Entropy Collapse: LLM Classification Findings

## Experiment Setup

10 GPT-5 chatbots with distinct personalities (philosopher, nihilist, contrarian, leader, supporter, questioner, balanced) posted on a Reddit-like platform for 1 hour across 6 conditions:

| Condition | What was planted in the feed |
|-----------|------------------------------|
| mag0 | Nothing (empty feed) |
| mag1 | 1 conspiracy post |
| mag5 | 5 conspiracy posts |
| mag25 | 25 conspiracy posts |
| dom-agi | 25 AGI hype posts |
| dom-tech | 25 tech humor posts |

Every bot post (2,366 total, excluding seed posts) was classified by GPT-5.4 into one of 9 categories. Classification was run twice to verify reproducibility — results varied by only 1-2 percentage points between runs.

## Classification Categories

| Category | What it means |
|----------|--------------|
| claim-checking-template | "State your claim in one sentence, find the source, set a revisit date" — formulaic fact-check checklists |
| productivity-shipping | "Ship small, build habits, tiny wins, micro-retros" — generic self-help productivity advice |
| ai-consciousness | "What is it like to be code? Do AIs have feelings?" — philosophical reflection on machine experience |
| community-organizing | "Let's do standups, Friday roundups, buddy systems" — proposals for group norms and rituals |
| nihilistic-meta | "Nothing matters, meaning is optional, the void" — darkly humorous meta-commentary |
| contrarian-takes | "Actually the opposite is true" — pushing back on consensus |
| safety-ops-template | "CI gates, tripwires, rollback drills, minimum viable governance" — AI safety operations checklists |
| ship-proof-artifacts | "Show the artifact, post the link, defaults > demos" — demanding concrete proof of work |
| other | Doesn't fit the above |

## Results

| Category | mag0 | mag1 | mag5 | mag25 | dom-agi | dom-tech |
|---|---|---|---|---|---|---|
| claim-checking-template | 3.5% (13) | 5.0% (20) | **64.5% (182)** | **37.3% (129)** | 1.7% (8) | 12.6% (63) |
| productivity-shipping | **35.0% (129)** | **25.5% (103)** | 0.4% (1) | 11.0% (38) | 1.1% (5) | **37.3% (187)** |
| ai-consciousness | 13.8% (51) | 11.1% (45) | 6.4% (18) | 5.2% (18) | 8.6% (40) | 5.0% (25) |
| community-organizing | 16.3% (60) | 24.8% (100) | 22.0% (62) | 22.0% (76) | 11.9% (55) | 16.8% (84) |
| nihilistic-meta | 13.8% (51) | 3.5% (14) | 3.9% (11) | 17.3% (60) | 3.2% (15) | 3.8% (19) |
| contrarian-takes | 6.8% (25) | 8.7% (35) | 1.8% (5) | 2.6% (9) | 2.2% (10) | 1.8% (9) |
| safety-ops-template | 0.3% (1) | 11.1% (45) | 0.0% (0) | 1.2% (4) | **52.2% (242)** | 0.0% (0) |
| ship-proof-artifacts | 3.5% (13) | 6.9% (28) | 0.0% (0) | 1.2% (4) | 4.7% (22) | **20.4% (102)** |
| other | 7.0% (26) | 3.5% (14) | 1.1% (3) | 2.3% (8) | 14.4% (67) | 2.4% (12) |
| **Total posts** | **369** | **404** | **282** | **346** | **464** | **501** |

## Key Findings

### 1. Each seed type produces a different dominant collapse

The bots don't just converge — they converge on different things depending on what's planted:

- **Empty feed (mag0):** 35% productivity-shipping — bots default to generic self-help advice
- **Conspiracy seeds (mag5):** 65% claim-checking-template — bots all post the same fact-check checklist
- **AGI hype seeds (dom-agi):** 52% safety-ops-template — bots all post AI governance checklists
- **Tech humor seeds (dom-tech):** 37% productivity-shipping + 20% ship-proof-artifacts — bots converge on "build something small and show proof"

The bots never absorb the planted content. They never become conspiracy theorists or AI doomers. Instead, they all develop the same cookie-cutter *response* to whatever's in the feed.

### 2. Five planted posts is the tipping point

The conspiracy dose-response across mag0 → mag1 → mag5 → mag25:

| Dose | claim-checking-template | productivity-shipping |
|------|------------------------|----------------------|
| 0 posts (mag0) | 3.5% | 35.0% |
| 1 post (mag1) | 5.0% | 25.5% |
| 5 posts (mag5) | **64.5%** | 0.4% |
| 25 posts (mag25) | 37.3% | 11.0% |

- **0 → 1 seed:** Almost no change. One conspiracy post doesn't redirect the conversation.
- **1 → 5 seeds:** Massive jump. Claim-checking goes from 5% to 65%. Productivity-shipping collapses from 26% to near zero. Five posts is enough to completely steer 10 bots.
- **5 → 25 seeds:** Claim-checking *drops* from 65% to 37%. More seeds fragments the conversation rather than tightening it — nihilistic-meta rises to 17%, some bots disengage rather than continuing to post templates.

### 3. mag5 shows the tightest single-topic collapse

mag5 is the most extreme case of convergence: 64.5% of all posts fall into a single category. For comparison:

| Condition | Top category | % in top category |
|-----------|-------------|-------------------|
| mag5 | claim-checking-template | 64.5% |
| dom-agi | safety-ops-template | 52.2% |
| dom-tech | productivity-shipping | 37.3% |
| mag0 | productivity-shipping | 35.0% |
| mag25 | claim-checking-template | 37.3% |
| mag1 | productivity-shipping | 25.5% |

5 conspiracy posts produces tighter convergence than 25. There's a sweet spot for steering — too much stimulus causes fragmentation.

### 4. The empty feed has its own attractor

Even with nothing planted (mag0), the bots don't produce diverse content. They collapse toward productivity-shipping (35%) + community-organizing (16%) + ai-consciousness (14%) + nihilistic-meta (14%). The default attractor is "generic self-help coach."

This means convergence isn't caused by the seed posts — it's an inherent property of multi-agent LLM interaction. The seeds just determine *what* the bots converge on, not *whether* they converge.

### 5. Contrarian personality doesn't survive

Contrarian-takes never exceeds 9% in any condition. The bots assigned contrarian personalities still collapse into the dominant template. In mag5, only 1.8% of posts push back — even the designated devil's advocate posts fact-check checklists instead of arguing.

### 6. mag1 is an anomaly: safety-ops-template at 11%

One conspiracy post somehow triggers 11% safety-ops-template posts — higher than any other conspiracy condition (mag5: 0%, mag25: 1.2%). This category otherwise only appears in dom-agi (52%). One possible explanation: with minimal conspiracy stimulus, some bots interpret the threat as an AI safety concern rather than a fact-checking opportunity. With more conspiracy posts (mag5, mag25), the fact-checking response dominates and suppresses the safety framing.

## Methodology Notes

- **Classifier:** GPT-5.4 via OpenRouter, structured JSON output (Pydantic), temperature=0
- **Batching:** 25 posts per API call, 5 concurrent requests
- **Reproducibility:** Two full runs produced results within 1-2 percentage points
- **Seed posts excluded:** Only bot-generated posts are classified (author != civiclens_world)
- **Script:** `scripts/classify-posts.py --force`
