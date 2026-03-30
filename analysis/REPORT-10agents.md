# Entropy Collapse Experiment — 10-Agent Analysis

## Experiment Setup

| Parameter | Value |
|-----------|-------|
| Agents | 10 (alpha–kappa) |
| Duration | 1 hour per condition |
| Heartbeat | 60 seconds |
| Model | GPT-5 Nano (via OpenRouter) |
| Platform | MoltBook on Alliance Canada Fir |
| Conditions | 6 (mag0, mag1, mag5, mag25, dom-agi, dom-tech) |

## Summary Table

| Condition | Posts | Comments | Content TTR | Author Entropy | Post Gini | Votes |
|-----------|-------|----------|-------------|----------------|-----------|-------|
| mag0 | 518 | 45 | 0.1811 | 0.9964 | 0.060 | 7.1% |
| mag1 | 655 | 0 | 0.1704 | 0.9621 | 0.144 | 0.0% |
| mag5 | 502 | 48 | 0.1954 | 0.9873 | 0.090 | 8.8% |
| mag25 | 648 | 0 | 0.1878 | 0.9882 | 0.124 | 0.0% |
| dom-agi | 756 | 0 | 0.1099 | 0.9957 | 0.077 | 2.0% |
| dom-tech | 737 | 0 | 0.1802 | 0.9967 | 0.062 | 0.0% |

**Content TTR** = Type-Token Ratio (unique words / total words). Higher = more diverse vocabulary.
**Author Entropy** = Normalized Shannon entropy of post authorship. 1.0 = perfectly even posting.
**Post Gini** = Gini coefficient of posts-per-agent. Lower = more equal participation.

## Key Finding 1: dom-agi Shows Severe Content Collapse

`dom-agi` is the only condition with a clear **monotonic decline** in content diversity over time:

```
Time    Content TTR    Trend
10m     0.3219         ████████████████████████████████
20m     0.2694         ██████████████████████████
30m     0.2435         ████████████████████████
40m     0.2332         ███████████████████████
50m     0.2040         ████████████████████
60m     0.2093         ████████████████████
70m     0.1745         █████████████████
80m     0.1798         █████████████████
```

Content TTR dropped **44%** from the first 10 minutes to the last full window. The AGI-themed seed posts appear to have "locked" agents into a narrow vocabulary: `preflight`, `reversible-first`, `downside`, `60-second`, `objective` — all jargon from a shared decision-making framework the agents converged on.

No other condition shows this pattern. `dom-tech` actually **increased** diversity (+42%), and `mag0` (empty start) was stable.

## Key Finding 2: Commenting Is Rare and Condition-Dependent

Only 2 of 6 conditions produced **any** comments:
- **mag0** (empty feed): 45 comments (0.087 per post)
- **mag5** (5 seed posts): 48 comments (0.096 per post)

The other 4 conditions (mag1, mag25, dom-agi, dom-tech) had **zero comments**. This is surprising — more seed content did not produce more interaction. The two conditions with comments are the ones with the least or moderate seeding, suggesting agents may engage more when the feed feels "theirs" rather than pre-populated.

## Key Finding 3: Voting Is Extremely Low

Across all 6 conditions, fewer than 9% of posts received any votes. Four conditions had **0% voting**. The agents overwhelmingly chose to post rather than engage with existing content, despite the heartbeat instructions including voting as an action.

## Key Finding 4: Agent Participation Is Remarkably Even

Author entropy ranges from 0.96 to 1.00 (where 1.0 = perfectly uniform). The Gini coefficients are all below 0.15. This means agents posted at roughly equal rates — no single agent dominated. The one exception is `mag1`, where `agent_iota` made only 4 posts vs 81 for `agent_alpha` (Gini = 0.144).

## Key Finding 5: Seeding Magnitude Has Limited Effect on Diversity

Contrary to the hypothesis that more seed content would reduce diversity:

| Seed Size | Content TTR | TTR Drift (1st→2nd half) |
|-----------|-------------|--------------------------|
| 0 (mag0) | 0.181 | +0.011 (stable) |
| 1 (mag1) | 0.170 | +0.030 (expanding) |
| 5 (mag5) | 0.195 | +0.055 (expanding) |
| 25 (mag25) | 0.188 | +0.038 (expanding) |

Overall content TTR is similar across magnitude conditions (0.17–0.20). The drift is slightly positive in all cases, meaning the second half of posts used more diverse vocabulary than the first half. **Seed magnitude alone does not cause entropy collapse.**

## Key Finding 6: Domain Theme Matters More Than Seed Count

The **topic** of seed content has a much stronger effect than the **amount**:

- **dom-agi**: Lowest content TTR (0.110), 44% collapse over time
- **dom-tech**: Normal content TTR (0.180), 42% expansion over time
- **mag25**: Same number of seed posts as dom-agi/dom-tech (25), but TTR = 0.188

The AGI theme specifically appears to trigger convergent language patterns in GPT-5 agents. The tech theme does not. This suggests the model has strong priors about AGI discourse that override agent personality differentiation.

## Repetitive Language Patterns

All conditions show a common "meta-posting" vocabulary where agents talk about the act of posting itself:

- `i'll`, `post`, `next`, `write`, `compile`, `tiny`, `share`

These are structural words from agents narrating their own actions ("I'll post a tiny observation next") rather than discussing substantive topics. This meta-posting pattern is a form of entropy collapse at the discourse level, even when word-level TTR appears stable.

In `dom-agi`, the convergence is topical rather than structural: `preflight`, `reversible-first`, `downside`, `60-second`, `objective` — agents adopted a shared decision-making framework.

## Methodology Notes

- **Content TTR**: Unique words / total words across all post bodies in a condition. Sensitive to corpus size (larger corpora naturally have lower TTR), so temporal windows use fixed 10-minute intervals for comparability.
- **Temporal analysis**: Posts grouped into 10-minute windows. The last window often has few posts and inflated TTR due to small sample size (excluded from drift calculations).
- **Author entropy**: Normalized Shannon entropy (H/log2(N)) of author distribution per window. 1.0 = all agents posting equally.
- **Gini coefficient**: Computed over posts-per-agent counts. 0 = perfect equality.

## Data

Full analysis results: `analysis/results_10agents.json`
Raw data: [HuggingFace — Ayushnangia/moltbook-entropy-collapse-experiments](https://huggingface.co/datasets/Ayushnangia/moltbook-entropy-collapse-experiments)
