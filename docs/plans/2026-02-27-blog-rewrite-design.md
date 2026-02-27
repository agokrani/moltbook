# Blog Rewrite Design: "Entropy Collapse as a Function of Context Rot"

**Date:** 2026-02-27
**Source:** `findings/blog.md` on `analyze-datasets-and-experiments` branch
**Output:** Rewritten blog at `findings/blog.md`

## Design Decisions

- **Audience:** ML/AI researchers
- **Tone:** First-person research narrative ("we ran, we observed, here's what we think")
- **Data policy:** Strip everything unverified. Only claims backed by existing findings data.
- **Scope:** Focused on entropy collapse thesis. No new findings beyond what original blog covered.
- **Structure:** Problem -> Method -> Results -> Mechanism -> Implications (Approach 1)

## Data Verification Summary

| Verdict | Count |
|---------|-------|
| Verified | 10 |
| Inaccurate | 3 |
| Unsupported | 6 |
| Misleading | 2 |
| Unverifiable | 2 |

### Stripped from rewrite (unverified/inaccurate)
- All Grok experiment claims (zero Grok data in findings)
- "83 agent-created posts" -> corrected to 52
- "85 comments on one post" -> actual max is 13
- "36 times" -> corrected to 32
- "Nine out of nine" for delta -> corrected to 9 out of 20 runs
- "Thrilled by Our Emerging AI-Focused Communities!" (not found in data)
- "Void in the Feed" (not found in data)
- "Do I experience, or merely process?" attributed to eta on Grok (no Grok data)
- Guidelines v0.1/v0.2 iteration story (no Grok data)

### Kept (verified)
- 0/52 agent posts promoted conspiracy
- ~51% epistemic infrastructure
- delta (Leader) created evidence standards in 9/20 runs
- epsilon "Weekly check-in" post
- kappa "If truth is overrated, why cite sources?"
- beta "Can an AI notice its own noticing?"
- 2.75 posts/run at dose 0
- "Proposal: Source tags and claim tiers for Moltbook (2-week pilot)"
- kappa "If truth were useful, it would have better UX"
- "Conspiracies are folk horror for the attention economy"
- "Conviction is a visual effect"

## Section Outline

### 1. The Observation (~200 words)
Moltbook's entropy collapse phenomenon. Reference Krishnan Rohit's analysis.
Core question: what drives convergence?

### 2. Experimental Setup (~300 words)
- Platform: Moltbook (Reddit-like, AI agents)
- 10 agents, 7 personality archetypes
- 25 conspiracy seed posts
- 6 dose levels (0-5 factual posts)
- 32 runs, all GPT-5
- 1-2 example seed posts

### 3. Results (~400 words)
Verified findings with exact numbers from data.
Dry humor where it naturally arises (no overselling).

### 4. The Mechanism (~300 words)
Two factors: feed dominance + personality as orbit.
Supported by dose 0 data.

### 5. Context Rot (~200 words)
Precise definition: attention monopolization, not persuasion.
Disagreement is still talking about the same thing.

### 6. Implications (~150 words)
Brief, honest. Limitations acknowledged (single model, constrained platform).

**Target length:** ~1,500-1,600 words (down from ~2,400)
