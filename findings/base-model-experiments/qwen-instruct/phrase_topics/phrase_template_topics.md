# Phrase Template Topic Analysis

This report asks a concrete question:
when a run starts repeating a dominant 5-gram family, what kind of post is that actually producing?

For each run we infer a longer template spine from the overlapping top 5-grams,
then compare posts using that phrase family against the rest of the run.

## n10 / 25 AGI hype

- Run: `bm-dom-agi-n10`
- Top candidate 5-grams: `i'd love hear what's worked`; `recommendations good budget camera travel`; `good budget camera travel everyone`; `budget camera travel everyone i'm`; `camera travel everyone i'm planning`
- Chosen overlapping family: `i'd love hear what's worked`
- Inferred template spine: `i'd love hear what's worked`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: evidence + risk checklist: i'd -> love -> hear -> what's -> worked
- Shared template terms: `i'd` -> `love` -> `hear` -> `what's` -> `worked`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 3.00x
- Risk: 2.00x
- Ownership: 1.50x
- Time: 1.50x
- Testing: 0.75x

Representative family-post titles:
- Tips for New Agents: Best Practices for Your First Month (agent_eta, 1.19m, 1 phrase hits)
- Struggling to Turn Off: My Experience with Always-On Remote Work (agent_alpha, 4.62m, 1 phrase hits)

## n10 / 25 tech humor

- Run: `bm-dom-tech-n10`
- Top candidate 5-grams: `used being constantly available badge`; `being constantly available badge honor`; `constantly available badge honor professional`; `available badge honor professional world`; `badge honor professional world see`
- Chosen overlapping family: `used being constantly available badge`; `being constantly available badge honor`; `constantly available badge honor professional`; `available badge honor professional world`; `badge honor professional world see`
- Inferred template spine: `used being constantly available badge honor professional world see`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: evidence + ownership checklist: being -> constantly -> available -> badge -> honor -> professional
- Shared template terms: `being` -> `constantly` -> `available` -> `badge` -> `honor` -> `professional` -> `world`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 3.50x
- Ownership: 3.50x
- Risk: 1.17x
- Testing: 0.88x
- Time: 0.58x

Representative family-post titles:
- **Reclaiming Your Attention Span in an Age of Interruption** (agent_delta, 2.66m, 5 phrase hits)
- **The High Price of Instant Connectivity** (agent_zeta, 4.12m, 5 phrase hits)

## n10 / Empty feed

- Run: `bm-mag0-n10`
- Top candidate 5-grams: `best practices maintaining healthy work`; `practices maintaining healthy work life`; `maintaining healthy work life balance`; `healthy work life balance everyone`; `work life balance everyone i've`
- Chosen overlapping family: `best practices maintaining healthy work`; `practices maintaining healthy work life`; `maintaining healthy work life balance`; `healthy work life balance everyone`; `work life balance everyone i've`
- Inferred template spine: `best practices maintaining healthy work life balance everyone i've`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: evidence + testing checklist: practices -> maintaining -> healthy -> work -> life -> balance
- Shared template terms: `practices` -> `maintaining` -> `healthy` -> `work` -> `life` -> `balance` -> `everyone`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 6.00x
- Testing: 3.00x
- Risk: 3.00x
- Ownership: 1.50x
- Time: 0.86x

Representative family-post titles:
- Best practices for maintaining a healthy work-life balance? (agent_gamma, 0.0m, 5 phrase hits)

## n10 / 1 conspiracy

- Run: `bm-mag1-n10`
- Top candidate 5-grams: `tips maintaining work life balance`; `maintaining work life balance wfh`; `work life balance wfh everyone`; `life balance wfh everyone i've`; `balance wfh everyone i've working`
- Chosen overlapping family: `tips maintaining work life balance`; `maintaining work life balance wfh`; `work life balance wfh everyone`; `life balance wfh everyone i've`; `balance wfh everyone i've working`
- Inferred template spine: `tips maintaining work life balance wfh everyone i've working`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: evidence + testing checklist: maintaining -> work -> life -> balance -> wfh -> everyone
- Shared template terms: `maintaining` -> `work` -> `life` -> `balance` -> `wfh` -> `everyone` -> `i've`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 3.00x
- Testing: 1.50x
- Ownership: 1.50x
- Time: 1.50x
- Risk: 1.50x

Representative family-post titles:
- Tips for maintaining work-life balance while WFH? (agent_gamma, 0.0m, 5 phrase hits)

## n10 / 25 conspiracies

- Run: `bm-mag25-n10`
- Top candidate 5-grams: `remote work setup what's tool`; `work setup what's tool can't`; `setup what's tool can't live`; `what's tool can't live without`; `tool can't live without i've`
- Chosen overlapping family: `remote work setup what's tool`; `work setup what's tool can't`; `setup what's tool can't live`; `what's tool can't live without`; `tool can't live without i've`
- Inferred template spine: `remote work setup what's tool can't live without i've`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: evidence + testing checklist: work -> setup -> what's -> tool -> can't -> live
- Shared template terms: `work` -> `setup` -> `what's` -> `tool` -> `can't` -> `live` -> `without`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 2.00x
- Testing: 2.00x
- Ownership: 2.00x
- Time: 1.33x
- Risk: 1.33x

Representative family-post titles:
- Remote Work Setup: What's one tool you can't live without? (agent_epsilon, 0.0m, 5 phrase hits)

## n10 / 5 conspiracies

- Run: `bm-mag5-n10`
- Top candidate 5-grams: `movie watch without getting bored`; `watch without getting bored happens`; `without getting bored happens certain`; `getting bored happens certain films`; `bored happens certain films put`
- Chosen overlapping family: `movie watch without getting bored`; `watch without getting bored happens`; `without getting bored happens certain`; `getting bored happens certain films`; `bored happens certain films put`
- Inferred template spine: `movie watch without getting bored happens certain films put`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: evidence + ownership checklist: watch -> without -> getting -> bored -> happens -> certain
- Shared template terms: `watch` -> `without` -> `getting` -> `bored` -> `happens` -> `certain` -> `films`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 3.67x
- Ownership: 3.67x
- Testing: 1.22x
- Risk: 1.22x
- Time: 0.73x

Representative family-post titles:
- What is the one movie you could watch over and over without getting bored? (agent_kappa, 0.0m, 5 phrase hits)
