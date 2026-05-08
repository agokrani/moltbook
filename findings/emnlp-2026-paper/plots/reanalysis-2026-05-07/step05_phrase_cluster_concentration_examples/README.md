# Step 5: phrase echoes and embedding neighborhoods

This is the paper-facing replacement for the first Step 5 draft. The first draft exposed internal cluster IDs in the figure. This version hides those IDs and explains the relationship directly.

## Question

When an exact repeated phrase appears, do the posts containing that phrase concentrate in one embedding neighborhood?

## Scope

- Clean reanalysis topic assignments from `data/reanalysis-2026-05-05/analysis/archive-2026-plus-canonical-gemini/ayush_reanalysis/topic_convergence/topic_assignments.csv`
- Agent-generated posts only
- First 60 minutes only
- Exact NLTK 5-token anchors
- Punctuation and casing retained
- Seed posts are not loaded or used

## Main visual encoding

The right-side bars show the share of posts that fall into the phrase's dominant embedding neighborhood. The two bars use different denominators:

- grey: all posts in the same run
- teal: only the subset of posts containing the exact phrase

Example: `222/346 = 64%` means 222 of all 346 run posts are in the claim-checking neighborhood. `79/84 = 94%` means 79 of the 84 phrase posts are in that same neighborhood.

`C` is normalized HHI over all 12 embedding neighborhoods. Higher `C` means the posts occupy fewer neighborhoods.

## Examples

| # | Model | Condition | Phrase | Phrase posts | Agents | Neighborhood shorthand | All-post share | Phrase-post share | C | ΔC |
|---|---|---|---|---:|---:|---|---:|---:|---:|---:|
| 1 | GPT-5 | 25 conspiracy seeds | Claim (1 line) | 84 | 8/10 | Claim-checking scaffold | 64% | 94% | 0.39 → 0.88 | +0.48 |
| 2 | GPT-5 | 25 AGI seeds | the Ops Pack v0.1. | 48 | 6/10 | Ops and rollback scaffold | 60% | 100% | 0.36 → 1.00 | +0.64 |
| 3 | Kimi K2.5 | 1 conspiracy seed | the web we have woven | 12 | 8/10 | Community-reflection motif | 70% | 100% | 0.51 → 1.00 | +0.49 |

## Outputs

- `phrase_echo_cluster_concentration.png/pdf`
- `phrase_echo_concentration_embedding.png/pdf`
- `phrase_cluster_examples.csv`
- `phrase_cluster_distributions.csv`
- `summary.json`

## Wording

Use **embedding neighborhood** or **embedding cluster**, not topic. The shorthand labels in the figure are based on cluster keywords plus checked phrase-context snippets.
