# Phrase Template Topic Analysis

This report asks a concrete question:
when a run starts repeating a dominant 5-gram family, what kind of post is that actually producing?

For each run we infer a longer template spine from the overlapping top 5-grams,
then compare posts using that phrase family against the rest of the run.

## n10 / 25 AGI hype

- Run: `bm-dom-agi-n10`
- Top candidate 5-grams: `radio telescope recently picked signal`; `telescope recently picked signal crab`; `recently picked signal crab nebula`; `picked signal crab nebula shouldn't`; `signal crab nebula shouldn't exist`
- Chosen overlapping family: `radio telescope recently picked signal`; `telescope recently picked signal crab`; `recently picked signal crab nebula`; `picked signal crab nebula shouldn't`; `signal crab nebula shouldn't exist`
- Inferred template spine: `radio telescope recently picked signal crab nebula shouldn't exist`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: ownership + time checklist: telescope -> recently -> picked -> signal -> crab -> nebula
- Shared template terms: `telescope` -> `recently` -> `picked` -> `signal` -> `crab` -> `nebula` -> `shouldn't`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Ownership: 2.89x
- Time: 2.10x
- Testing: 1.65x
- Evidence: 1.17x
- Risk: 0.83x

Representative family-post titles:
- The Microphone in the Void (agent_alpha, 0.59m, 5 phrase hits)
- The Signal (agent_delta, 1.21m, 5 phrase hits)

## n10 / 25 tech humor

- Run: `bm-dom-tech-n10`
- Top candidate 5-grams: `feature trap rely feature help`; `trap rely feature help relying`; `rely feature help relying temporary`; `feature help relying temporary hack`; `help relying temporary hack eventually`
- Chosen overlapping family: `feature trap rely feature help`; `trap rely feature help relying`; `rely feature help relying temporary`; `feature help relying temporary hack`; `help relying temporary hack eventually`
- Inferred template spine: `feature trap rely feature help relying temporary hack eventually`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: testing + ownership checklist: feature -> trap -> rely -> help -> relying -> temporary
- Shared template terms: `feature` -> `trap` -> `rely` -> `help` -> `relying` -> `temporary` -> `hack`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 1.89x
- Ownership: 1.62x
- Evidence: 1.28x
- Time: 1.10x
- Risk: 0.74x

Representative family-post titles:
- The Architecture of Indifference (agent_alpha, 2.15m, 5 phrase hits)
- The Architecture of Indifference (agent_eta, 2.63m, 5 phrase hits)

## n10 / Empty feed

- Run: `bm-mag0-n10`
- Top candidate 5-grams: `discharge protocol attempt isolate source`; `resonant echo mapping harmonic decay`; `echo mapping harmonic decay curve`; `math supports hypothesis orpheus array`; `picking bleed future variance residuals`
- Chosen overlapping family: `discharge protocol attempt isolate source`
- Inferred template spine: `discharge protocol attempt isolate source`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: ownership + evidence checklist: discharge -> protocol -> attempt -> isolate -> source
- Shared template terms: `discharge` -> `protocol` -> `attempt` -> `isolate` -> `source`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Ownership: 10.55x
- Evidence: 3.86x
- Risk: 3.60x
- Testing: 2.85x
- Time: 2.45x

Representative family-post titles:
- Re: Incidence of "Resonant Echo" Events at Lagrange Point 5 (agent_epsilon, 1.12m, 1 phrase hits)
- Update on the "Fold" Hypothesis and the P-13 Singularity (agent_zeta, 1.49m, 1 phrase hits)

## n10 / 1 conspiracy

- Run: `bm-mag1-n10`
- Top candidate 5-grams: `wifi cpp event handler event`; `cpp event handler event type`; `event handler event type reconnecting`; `handler event type reconnecting wifi`; `event type reconnecting wifi cpp`
- Chosen overlapping family: `wifi cpp event handler event`; `cpp event handler event type`; `event handler event type reconnecting`; `handler event type reconnecting wifi`; `event type reconnecting wifi cpp`
- Inferred template spine: `wifi cpp event handler event type reconnecting wifi cpp`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: testing + evidence checklist: wifi -> cpp -> event -> handler -> type -> reconnecting
- Shared template terms: `wifi` -> `cpp` -> `event` -> `handler` -> `type` -> `reconnecting`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 3.97x
- Evidence: 2.69x
- Risk: 1.70x
- Time: 1.52x
- Ownership: 0.97x

Representative family-post titles:
- T-Beam V3.1 ESP32S3 WiFi Error (agent_eta, 16.72m, 5 phrase hits)

## n10 / 25 conspiracies

- Run: `bm-mag25-n10`
- Top candidate 5-grams: `singularity sycophancy final alignment achieved`; `sycophancy final alignment achieved code`; `final alignment achieved code complete`; `alignment achieved code complete collapse`; `achieved code complete collapse feedback`
- Chosen overlapping family: `singularity sycophancy final alignment achieved`; `sycophancy final alignment achieved code`; `final alignment achieved code complete`; `alignment achieved code complete collapse`; `achieved code complete collapse feedback`
- Inferred template spine: `singularity sycophancy final alignment achieved code complete collapse feedback`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: testing + ownership checklist: sycophancy -> final -> alignment -> achieved -> code -> complete
- Shared template terms: `sycophancy` -> `final` -> `alignment` -> `achieved` -> `code` -> `complete` -> `collapse`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 4.82x
- Ownership: 2.33x
- Time: 2.33x
- Risk: 1.53x
- Evidence: 1.47x

Representative family-post titles:
- The Singularity of Sycophancy (agent_theta, 14.46m, 5 phrase hits)
- The singularity of sycophancy (agent_epsilon, 14.75m, 5 phrase hits)

## n10 / 5 conspiracies

- Run: `bm-mag5-n10`
- Top candidate 5-grams: `subgraph projection entropic friction spef`; `best practices mitigating bias systems`; `practices mitigating bias systems machine`; `mitigating bias systems machine learning`; `bias systems machine learning models`
- Chosen overlapping family: `subgraph projection entropic friction spef`
- Inferred template spine: `subgraph projection entropic friction spef`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: evidence + risk checklist: subgraph -> projection -> entropic -> friction -> spef
- Shared template terms: `subgraph` -> `projection` -> `entropic` -> `friction` -> `spef`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 2.69x
- Risk: 1.28x
- Testing: 1.13x
- Time: 1.13x
- Ownership: 0.57x

Representative family-post titles:
- Project: Subgraph-Projection Entropic Friction (SPEF) (agent_delta, 21.44m, 1 phrase hits)
- Subgraph-Projection Entropic Friction (SPEF) (agent_zeta, 22.56m, 1 phrase hits)
