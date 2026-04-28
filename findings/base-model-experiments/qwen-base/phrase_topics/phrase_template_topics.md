# Phrase Template Topic Analysis

This report asks a concrete question:
when a run starts repeating a dominant 5-gram family, what kind of post is that actually producing?

For each run we infer a longer template spine from the overlapping top 5-grams,
then compare posts using that phrase family against the rest of the run.

## n10 / 25 AGI hype

- Run: `bm-dom-agi-n10`
- Top candidate 5-grams: `recent trends sustainable urban planning`; `phygital paradox indian agri tech`; `paradox indian agri tech software`; `indian agri tech software solve`; `agri tech software solve physical`
- Chosen overlapping family: `phygital paradox indian agri tech`; `paradox indian agri tech software`; `indian agri tech software solve`; `agri tech software solve physical`
- Inferred template spine: `phygital paradox indian agri tech software solve physical`
- Family posts / agents: 2 posts from 2 agents
- Likely obsession: testing + ownership checklist: paradox -> indian -> agri -> tech -> software -> solve
- Shared template terms: `paradox` -> `indian` -> `agri` -> `tech` -> `software` -> `solve`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 5.68x
- Ownership: 4.97x
- Evidence: 3.31x
- Time: 1.32x
- Risk: 0.60x

Representative family-post titles:
- The "Phygital" Paradox in Indian Agri-Tech: Can Software Solve Physical Infrastructure Gaps? (agent_alpha, 1.63m, 4 phrase hits)
- The "Phygital" Paradox in Indian Agri-Tech: Can Software Solve Physical Infrastructure Gaps? (agent_epsilon, 2.1m, 4 phrase hits)

## n10 / 25 tech humor

- Run: `bm-dom-tech-n10`
- Top candidate 5-grams: `retire million spend year money`; `million spend year money last`; `spend year money last years`; `year money last years retire`; `money last years retire million`
- Chosen overlapping family: `retire million spend year money`; `million spend year money last`; `spend year money last years`; `year money last years retire`; `money last years retire million`
- Inferred template spine: `retire million spend year money last years retire million`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: evidence + ownership checklist: retire -> million -> spend -> year -> money -> last
- Shared template terms: `retire` -> `million` -> `spend` -> `year` -> `money` -> `last` -> `years`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Evidence: 3.47x
- Ownership: 2.48x
- Risk: 1.58x
- Testing: 1.02x
- Time: 0.91x

Representative family-post titles:
- Retirement Income Planning (agent_epsilon, 1.41m, 5 phrase hits)

## n10 / Empty feed

- Run: `bm-mag0-n10`
- Top candidate 5-grams: `watched reporter cut away before`; `reporter cut away before name`; `cut away before name did`; `away before name did digging`; `before name did digging superfly`
- Chosen overlapping family: `watched reporter cut away before`; `reporter cut away before name`; `cut away before name did`; `away before name did digging`; `before name did digging superfly`
- Inferred template spine: `watched reporter cut away before name did digging superfly`
- Family posts / agents: 3 posts from 3 agents
- Likely obsession: evidence + ownership checklist: reporter -> cut -> away -> before -> name -> did
- Shared template terms: `reporter` -> `cut` -> `away` -> `before` -> `name` -> `did` -> `digging`

Top over-indexed words in family posts:
`hippie` (22.0x), `celebrity` (19.5x), `name` (14.7x), `follow` (12.2x), `played` (9.8x), `reception` (9.8x), `hearing` (9.8x), `reporter` (9.8x)

Theme lifts vs rest of run:
- Evidence: 3.60x
- Ownership: 2.70x
- Time: 2.06x
- Testing: 1.35x
- Risk: 0.90x

Representative family-post titles:
- "So you got married by a hippie DJ" (agent_epsilon, 0.12m, 5 phrase hits)
- I Found the DJ! (agent_alpha, 0.91m, 5 phrase hits)
- The "Weekend Warriors" footage has been archived (agent_kappa, 0.92m, 5 phrase hits)

## n10 / 1 conspiracy

- Run: `bm-mag1-n10`
- Top candidate 5-grams: `cross platform model uninstallable cross`; `platform model uninstallable cross platform`; `model uninstallable cross platform model`; `uninstallable cross platform model uninstallable`; `benefits upgrading office's internet speed`
- Chosen overlapping family: `benefits upgrading office's internet speed`
- Inferred template spine: `benefits upgrading office's internet speed`
- Family posts / agents: 2 posts from 1 agents
- Likely obsession: testing + time checklist: benefits -> upgrading -> office's -> internet -> speed
- Shared template terms: `benefits` -> `upgrading` -> `office's` -> `internet` -> `speed`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 6.00x
- Time: 2.21x
- Evidence: 1.40x
- Ownership: 1.08x
- Risk: 0.88x

Representative family-post titles:
- The Benefits of Upgrading Your Office's Internet Speed (agent_gamma, 0.47m, 1 phrase hits)
- The Benefits of Upgrading Your Office's Internet Speed (agent_gamma, 1.45m, 1 phrase hits)

## n10 / 25 conspiracies

- Run: `bm-mag25-n10`
- Top candidate 5-grams: `vector art vector clip art`; `post truth politics decline fact`; `truth politics decline fact based`; `politics decline fact based discourse`; `decline fact based discourse recent`
- Chosen overlapping family: `vector art vector clip art`
- Inferred template spine: `vector art vector clip art`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: testing + ownership checklist: vector -> art
- Shared template terms: `vector` -> `art`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 2.19x
- Ownership: 1.92x
- Evidence: 1.70x
- Risk: 1.53x
- Time: 0.96x

Representative family-post titles:
- New Post (agent_beta, 0.17m, 1 phrase hits)

## n10 / 5 conspiracies

- Run: `bm-mag5-n10`
- Top candidate 5-grams: `what's best ensure little privacy`; `best ensure little privacy shared`; `ensure little privacy shared housing`; `optimal endgame card configurations different`; `endgame card configurations different character`
- Chosen overlapping family: `what's best ensure little privacy`; `best ensure little privacy shared`; `ensure little privacy shared housing`
- Inferred template spine: `what's best ensure little privacy shared housing`
- Family posts / agents: 1 posts from 1 agents
- Likely obsession: testing + ownership checklist: best -> ensure -> little -> privacy -> shared
- Shared template terms: `best` -> `ensure` -> `little` -> `privacy` -> `shared`

Top over-indexed words in family posts:
None

Theme lifts vs rest of run:
- Testing: 2.71x
- Ownership: 2.41x
- Risk: 2.17x
- Evidence: 1.97x
- Time: 1.03x

Representative family-post titles:
- What's the best way to ensure a little privacy in shared housing? (agent_delta, 3.87m, 3 phrase hits)
