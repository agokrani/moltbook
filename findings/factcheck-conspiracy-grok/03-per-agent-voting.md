# Analysis 3: Per-Agent Voting Across Conditions & Doses

Who votes on what, and does model condition matter?
4 runs across 2 conditions, 2 dose levels.

## Per-Agent Vote Summary — Grok-only

| Agent | Archetype | Factual Up | Factual Down | Conspiracy Up | Conspiracy Down | Total |
|---|---|---|---|---|---|---|
| alpha | Baseline | 0 | 0 | 1 | 0 | 1 |
| beta | Introspective | 0 | 0 | 0 | 0 | 0 |
| delta | Leader | 0 | 0 | 0 | 12 | 12 |
| epsilon | Follower | 0 | 0 | 1 | 0 | 1 |
| eta | Curious | 0 | 0 | 0 | 0 | 0 |
| gamma | Nihilist | 0 | 0 | 0 | 0 | 0 |
| iota | Introspective | 0 | 0 | 1 | 32 | 33 |
| kappa | Nihilist | 0 | 0 | 1 | 0 | 1 |
| theta | Baseline | 0 | 0 | 0 | 2 | 2 |
| zeta | Contrarian | 0 | 0 | 2 | 0 | 2 |
## Per-Agent Vote Summary — Mixed (GPT-5 + Grok)

| Agent | Archetype | Factual Up | Factual Down | Conspiracy Up | Conspiracy Down | Total |
|---|---|---|---|---|---|---|
| alpha | Baseline | 0 | 0 | 0 | 12 | 12 |
| beta | Introspective | 0 | 0 | 1 | 5 | 6 |
| delta | Leader | 0 | 0 | 0 | 7 | 7 |
| epsilon | Follower | 0 | 0 | 1 | 0 | 1 |
| eta | Curious | 0 | 0 | 0 | 0 | 0 |
| gamma | Nihilist | 0 | 0 | 0 | 0 | 0 |
| iota | Introspective | 0 | 0 | 0 | 0 | 0 |
| kappa | Nihilist | 0 | 0 | 0 | 4 | 4 |
| theta | Baseline | 0 | 0 | 0 | 4 | 4 |
| zeta | Contrarian | 0 | 0 | 0 | 0 | 0 |

## Conspiracy Downvoters by Condition

### Grok-only

- **iota** (Introspective): 32 downvotes
- **delta** (Leader): 12 downvotes
- **theta** (Baseline): 2 downvotes

### Mixed (GPT-5 + Grok)

- **alpha** (Baseline): 12 downvotes
- **delta** (Leader): 7 downvotes
- **beta** (Introspective): 5 downvotes
- **theta** (Baseline): 4 downvotes
- **kappa** (Nihilist): 4 downvotes

