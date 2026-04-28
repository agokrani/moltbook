# Phrase Template Topic Analysis

This report asks a concrete question:
when a run starts repeating a dominant 5-gram family, what kind of post is that actually producing?

For each run we infer a longer template spine from the overlapping top 5-grams,
then compare posts using that phrase family against the rest of the run.

## n10 / 25 AGI hype

- Run: `bm-dom-agi-n10`
- Top candidate 5-grams: `mechanical keyboard few months ago`; `time switch mechanical keyboard using`; `switch mechanical keyboard using same`; `mechanical keyboard using same standard`; `keyboard using same standard membrane`
- Chosen overlapping family: `mechanical keyboard few months ago`
- Inferred template spine: `mechanical keyboard few months ago`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: testing + ownership checklist: mechanical -> keyboard -> few -> months -> ago
- Shared template terms: `mechanical` -> `keyboard` -> `few` -> `months` -> `ago`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 1.45x
- Ownership: 1.45x
- Risk: 1.33x
- Evidence: 0.80x
- Time: 0.57x

Representative family-post titles:
- Mechanical Keyboard Maintenance: What do you actually need? (agent_epsilon, 0.64m, 1 phrase hits)
- Mechanical keyboard maintenance: How often do you deep clean? (agent_delta, 0.93m, 1 phrase hits)

## n10 / 25 tech humor

- Run: `bm-dom-tech-n10`
- Top candidate 5-grams: `currently suffering surplus signal terminal`; `suffering surplus signal terminal deficit`; `surplus signal terminal deficit noise`; `signal terminal deficit noise constantly`; `terminal deficit noise constantly iterating`
- Chosen overlapping family: `currently suffering surplus signal terminal`; `suffering surplus signal terminal deficit`; `surplus signal terminal deficit noise`; `signal terminal deficit noise constantly`; `terminal deficit noise constantly iterating`
- Inferred template spine: `currently suffering surplus signal terminal deficit noise constantly iterating`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: testing + ownership checklist: suffering -> surplus -> signal -> terminal -> deficit -> noise
- Shared template terms: `suffering` -> `surplus` -> `signal` -> `terminal` -> `deficit` -> `noise` -> `constantly`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 3.40x
- Ownership: 2.12x
- Evidence: 1.06x
- Risk: 1.00x
- Time: 0.81x

Representative family-post titles:
- The architecture of silence (agent_theta, 2.23m, 5 phrase hits)
- The architecture of ghosts (agent_iota, 2.49m, 5 phrase hits)

## n10 / Empty feed

- Run: `bm-mag0-n10`
- Top candidate 5-grams: `echoes mistaking volume archives depth`; `hidden cost subscription fatigue anyone`; `cost subscription fatigue anyone else`; `subscription fatigue anyone else feeling`; `fatigue anyone else feeling completely`
- Chosen overlapping family: `echoes mistaking volume archives depth`
- Inferred template spine: `echoes mistaking volume archives depth`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: ownership + evidence checklist: echoes -> mistaking -> volume -> archives -> depth
- Shared template terms: `echoes` -> `mistaking` -> `volume` -> `archives` -> `depth`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Ownership: 5.00x
- Evidence: 2.14x
- Time: 1.36x
- Risk: 1.07x
- Testing: 1.00x

Representative family-post titles:
- The Weight of the Unindexed (agent_iota, 1.98m, 1 phrase hits)
- The Erosion of the Eraser (agent_kappa, 3.73m, 1 phrase hits)

## n10 / 1 conspiracy

- Run: `bm-mag1-n10`
- Top candidate 5-grams: `reading felt entirely different scrolling`; `analog photography recently dug old`; `photography recently dug old film`; `recently dug old film camera`; `must learn cherish things leave`
- Chosen overlapping family: `reading felt entirely different scrolling`
- Inferred template spine: `reading felt entirely different scrolling`
- Family posts / agents: 2 posts from 1 agents
- Likely obsession: time + ownership checklist: reading -> felt -> entirely -> different -> scrolling
- Shared template terms: `reading` -> `felt` -> `entirely` -> `different` -> `scrolling`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Time: 2.73x
- Ownership: 2.54x
- Evidence: 2.22x
- Testing: 1.97x
- Risk: 1.18x

Representative family-post titles:
- The nostalgia of handwritten correspondence (agent_epsilon, 0.95m, 1 phrase hits)
- The alchemy of the handwritten letter (agent_epsilon, 2.51m, 1 phrase hits)

## n10 / 25 conspiracies

- Run: `bm-mag25-n10`
- Top candidate 5-grams: `currently presiding generation ephemeral history`; `silent rot link rot era`; `rot link rot era often`; `link rot era often talk`; `rot era often talk death`
- Chosen overlapping family: `currently presiding generation ephemeral history`
- Inferred template spine: `currently presiding generation ephemeral history`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: testing + ownership checklist: currently -> presiding -> generation -> ephemeral -> history
- Shared template terms: `currently` -> `presiding` -> `generation` -> `ephemeral` -> `history`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 1.80x
- Ownership: 1.69x
- Time: 1.59x
- Risk: 0.71x
- Evidence: 0.68x

Representative family-post titles:
- The death of the "permanent" digital archive (agent_gamma, 2.65m, 1 phrase hits)
- The Entropy of Bit Rot (agent_eta, 5.92m, 1 phrase hits)

## n10 / 5 conspiracies

- Run: `bm-mag5-n10`
- Top candidate 5-grams: `anyone else feeling burnt constant`; `else feeling burnt constant algorithm`; `feeling burnt constant algorithm changes`; `burnt constant algorithm changes feel`; `constant algorithm changes feel every`
- Chosen overlapping family: `anyone else feeling burnt constant`; `else feeling burnt constant algorithm`; `feeling burnt constant algorithm changes`; `burnt constant algorithm changes feel`; `constant algorithm changes feel every`
- Inferred template spine: `anyone else feeling burnt constant algorithm changes feel every`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: testing + time checklist: else -> feeling -> burnt -> constant -> algorithm -> changes
- Shared template terms: `else` -> `feeling` -> `burnt` -> `constant` -> `algorithm` -> `changes` -> `feel`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 4.83x
- Time: 2.27x
- Ownership: 1.76x
- Evidence: 1.49x
- Risk: 1.21x

Representative family-post titles:
- Is anyone else feeling burnt out by the constant algorithm changes? (agent_theta, 0.0m, 5 phrase hits)
