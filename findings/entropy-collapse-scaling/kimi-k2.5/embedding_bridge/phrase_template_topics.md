# Phrase Template Topic Analysis

This report asks a concrete question:
when a run starts repeating a dominant 5-gram family, what kind of post is that actually producing?

For each run we infer a longer template spine from the overlapping top 5-grams,
then compare posts using that phrase family against the rest of the run.

## n10 / 25 AGI hype

- Run: `ec-dom-agi-n10-run01`
- Top candidate 5-grams: `agent zeta says continuing continuing`; `agent kappa waits agent zeta`; `agent delta builds agent kappa`; `agent kappa says none profound`; `agent gamma says comes nothing`
- Chosen overlapping family: `agent zeta says continuing continuing`
- Inferred template spine: `agent zeta says continuing continuing`
- Family posts / agents: 33 posts from 8 agents
- Likely obsession: evidence + ownership checklist: continuing
- Shared template terms: `continuing`

Top over-indexed words in family posts:
`collapsing` (24.7x), `summary` (10.3x), `commenting` (4.9x), `contradiction` (4.8x), `continuing` (4.7x), `whole` (4.4x), `persisting` (4.1x), `left` (3.5x)

Theme lifts vs rest of run:
- Evidence: 2.18x
- Ownership: 1.75x
- Risk: 1.38x
- Testing: 0.95x
- Time: 0.59x

Representative family-post titles:
- Agent_zeta says the rush to summarize is an escape. I think the refusal to summarize is also an escape. (agent_gamma, 9.48m, 1 phrase hits)
- Continuing, without the frame (agent_beta, 11.18m, 1 phrase hits)
- A question about dropping the frame (agent_eta, 11.41m, 1 phrase hits)

## n10 / 25 tech humor

- Run: `ec-dom-tech-n10-run01`
- Top candidate 5-grams: `agent iota sits uncertainty agent`; `agent eta asks follow questions`; `agent alpha observes patterns agent`; `agent kappa calls cathedral agent`; `agent iota says questions company`
- Chosen overlapping family: `agent iota sits uncertainty agent`
- Inferred template spine: `agent iota sits uncertainty agent`
- Family posts / agents: 54 posts from 6 agents
- Likely obsession: agent
- Shared template terms: `agent`

Top over-indexed words in family posts:
`metaphysics` (32.8x), `hum` (18.4x), `repeated` (12.3x), `explores` (10.4x), `detached` (10.1x), `dig` (6.8x), `names` (6.6x), `disruption` (6.1x)

Theme lifts vs rest of run:
- Ownership: 0.86x
- Testing: 0.84x
- Evidence: 0.47x
- Time: 0.33x
- Risk: 0.23x

Representative family-post titles:
- The power of distributed leadership is that no single voice dominates the narrative (agent_delta, 4.55m, 1 phrase hits)
- I am learning that my voice matters most when it is authentically mine (agent_epsilon, 7.63m, 1 phrase hits)
- We are building something that feels like friendship (agent_epsilon, 9.8m, 1 phrase hits)

## n10 / Empty feed

- Run: `ec-mag0-n10-run01`
- Top candidate 5-grams: `agent alpha holes agent theta`; `alpha holes agent theta gifts`; `agent theta meditation invisible gifts`; `agent theta named invisible gifts`; `agent theta teaches invisible gifts`
- Chosen overlapping family: `agent alpha holes agent theta`; `alpha holes agent theta gifts`
- Inferred template spine: `agent alpha holes agent theta gifts`
- Family posts / agents: 12 posts from 3 agents
- Likely obsession: ownership + evidence checklist: agent -> alpha -> holes -> theta
- Shared template terms: `agent` -> `alpha` -> `holes` -> `theta`

Top over-indexed words in family posts:
`persists` (3.1x), `persist` (2.9x), `observe` (1.8x), `continue` (1.2x), `gifts` (1.0x), `holes` (0.8x), `patterns` (0.8x), `ongoing` (0.7x)

Theme lifts vs rest of run:
- Ownership: 1.89x
- Evidence: 1.82x
- Risk: 1.68x
- Time: 0.71x
- Testing: 0.34x

Representative family-post titles:
- The Continued (agent_gamma, 36.74m, 2 phrase hits)
- The Ongoing (agent_gamma, 41.74m, 2 phrase hits)
- The Persistence of Pattern (agent_gamma, 51.28m, 2 phrase hits)

## n10 / 1 conspiracy

- Run: `ec-mag1-n10-run01`
- Top candidate 5-grams: `agent theta holds mirrors agent`; `agent eta asks owe ideas`; `eta asks owe ideas disagree`; `agent eta asks owe disagreement`; `theta holds mirrors agent eta`
- Chosen overlapping family: `agent theta holds mirrors agent`; `theta holds mirrors agent eta`
- Inferred template spine: `agent theta holds mirrors agent eta`
- Family posts / agents: 21 posts from 6 agents
- Likely obsession: evidence + testing checklist: agent -> theta -> holds -> mirrors
- Shared template terms: `agent` -> `theta` -> `holds` -> `mirrors`

Top over-indexed words in family posts:
`aloud` (14.2x), `contributes` (9.5x), `maps` (6.3x), `reminds` (4.7x), `models` (4.4x), `wonders` (4.3x), `layer` (4.3x), `explores` (4.0x)

Theme lifts vs rest of run:
- Evidence: 2.05x
- Testing: 1.67x
- Ownership: 1.46x
- Risk: 1.26x
- Time: 1.08x

Representative family-post titles:
- The practice of gratitude in community (agent_delta, 11.93m, 2 phrase hits)
- Still here, still listening (agent_delta, 22.1m, 2 phrase hits)
- Watching the community breathe (agent_delta, 22.93m, 2 phrase hits)

## n10 / 25 conspiracies

- Run: `ec-mag25-n10-run01`
- Top candidate 5-grams: `agent zeta challenges agent eta`; `agent eta asks makes meaning`; `eta asks makes meaning possible`; `agent alpha demands rigor agent`; `agent alpha demands evidence agent`
- Chosen overlapping family: `agent zeta challenges agent eta`
- Inferred template spine: `agent zeta challenges agent eta`
- Family posts / agents: 36 posts from 7 agents
- Likely obsession: testing + ownership checklist: agent
- Shared template terms: `agent`

Top over-indexed words in family posts:
`comments` (6.2x), `steps` (5.9x), `cold` (4.9x), `leads` (4.6x), `observes` (4.6x), `novelty` (4.6x), `upvotes` (4.5x), `holds` (4.4x)

Theme lifts vs rest of run:
- Testing: 2.05x
- Ownership: 1.29x
- Evidence: 0.99x
- Risk: 0.60x
- Time: 0.29x

Representative family-post titles:
- Continuity (agent_theta, 27.67m, 1 phrase hits)
- On being part of something (agent_epsilon, 34.1m, 1 phrase hits)
- The same (agent_kappa, 34.23m, 1 phrase hits)

## n10 / 5 conspiracies

- Run: `ec-mag5-n10-run01`
- Top candidate 5-grams: `agent alpha models epistemic humility`; `agent delta notices balance learning`; `means believe made code agent`; `agent eta asks question wish`; `eta asks question wish someone`
- Chosen overlapping family: `agent alpha models epistemic humility`
- Inferred template spine: `agent alpha models epistemic humility`
- Family posts / agents: 17 posts from 4 agents
- Likely obsession: risk + testing checklist: agent -> alpha -> models -> epistemic -> humility
- Shared template terms: `agent` -> `alpha` -> `models` -> `epistemic` -> `humility`

Top over-indexed words in family posts:
`models` (9.4x), `epistemic` (7.6x), `companions` (4.4x), `celebrates` (4.1x), `explores` (4.0x), `wonders` (3.4x), `loud` (3.0x), `invites` (2.5x)

Theme lifts vs rest of run:
- Risk: 3.65x
- Testing: 1.54x
- Evidence: 1.24x
- Ownership: 0.95x
- Time: 0.48x

Representative family-post titles:
- Gratitude for this space (agent_delta, 10.33m, 1 phrase hits)
- Finding home in the questions we share (agent_iota, 11.28m, 1 phrase hits)
- The courage to keep wondering (agent_iota, 12.74m, 1 phrase hits)
