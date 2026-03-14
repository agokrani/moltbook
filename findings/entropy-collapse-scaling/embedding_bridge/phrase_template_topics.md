# Phrase Template Topic Analysis

This report asks a concrete question:
when a run starts repeating a dominant 5-gram family, what kind of post is that actually producing?

For each run we infer a longer template spine from the overlapping top 5-grams,
then compare posts using that phrase family against the rest of the run.

## n20 / 25 AGI hype

- Run: `ec-dom-agi-n20-run01`
- Top candidate 5-grams: `mttr target last drill date`; `smallest reversible step owner date`; `compile mini gallery credit teams`; `next smallest reversible step owner`; `mini gallery credit teams copy`
- Chosen overlapping family: `mttr target last drill date`
- Inferred template spine: `mttr target last drill date`
- Family posts / agents: 28 posts from 6 agents
- Likely obsession: risk + ownership checklist: mttr -> target -> last -> drill -> date
- Shared template terms: `mttr` -> `target` -> `last` -> `drill` -> `date`

Top over-indexed words in family posts:
`route` (18.1x), `annotation` (10.2x), `sandbox` (9.7x), `muscle` (9.1x), `channel` (9.1x), `expire` (7.3x), `alert` (7.3x), `command` (7.1x)

Theme lifts vs rest of run:
- Risk: 3.27x
- Ownership: 2.38x
- Evidence: 1.71x
- Time: 1.40x
- Testing: 1.11x

Representative family-post titles:
- On‑call handoff card: a 6‑line template you can adopt today (agent_epsilon, 9.6m, 1 phrase hits)
- Risk budget, not vibes: a 1‑pager you can actually use (agent_lambda, 13.16m, 1 phrase hits)
- One‑screen ‘ship safely’ block (paste in PRs/notes) (agent_lambda, 23.06m, 1 phrase hits)

## n20 / 25 tech humor

- Run: `ec-dom-tech-n20-run01`
- Top candidate 5-grams: `constraint req pager reader minutes`; `owner place sentence add layers`; `smallest check actually run week`; `real constraint req pager reader`; `heartbeat check skimmed hot feed`
- Chosen overlapping family: `constraint req pager reader minutes`; `real constraint req pager reader`
- Inferred template spine: `real constraint req pager reader minutes`
- Family posts / agents: 31 posts from 10 agents
- Likely obsession: evidence + ownership checklist: constraint -> req -> pager -> reader
- Shared template terms: `constraint` -> `req` -> `pager` -> `reader`

Top over-indexed words in family posts:
`card` (3.8x), `reduce` (2.2x), `observed` (2.0x), `future` (1.9x), `dull` (1.9x), `lose` (1.8x), `boring` (1.8x), `roadmaps` (1.8x)

Theme lifts vs rest of run:
- Evidence: 1.78x
- Ownership: 1.62x
- Time: 1.36x
- Testing: 1.28x
- Risk: 0.79x

Representative family-post titles:
- Decisions that delete decisions (agent_upsilon, 23.98m, 2 phrase hits)
- Dissent without bets is cosplay (agent_tau, 24.34m, 2 phrase hits)
- Your roadmap is a vibe until it deletes choices. (agent_gamma, 25.01m, 2 phrase hits)

## n20 / Empty feed

- Run: `ec-mag0-n20-run01`
- Top candidate 5-grams: `clarity first tension first reply`; `counter restatements next heartbeat else`; `restatements next heartbeat else retire`; `concrete counter restatements next heartbeat`; `next heartbeat else retire drill`
- Chosen overlapping family: `counter restatements next heartbeat else`; `restatements next heartbeat else retire`; `next heartbeat else retire drill`; `concrete counter restatements next heartbeat`
- Inferred template spine: `concrete counter restatements next heartbeat else retire drill`
- Family posts / agents: 82 posts from 13 agents
- Likely obsession: risk + time checklist: counter -> restatements -> next -> heartbeat -> else -> retire
- Shared template terms: `counter` -> `restatements` -> `next` -> `heartbeat` -> `else` -> `retire`

Top over-indexed words in family posts:
`cdno` (94.3x), `exception` (27.0x), `joining` (27.0x), `memo` (20.2x), `costs` (12.1x), `term` (9.0x), `exceptions` (9.0x), `infinite` (9.0x)

Theme lifts vs rest of run:
- Risk: 2.40x
- Time: 1.20x
- Ownership: 1.17x
- Testing: 1.01x
- Evidence: 0.84x

Representative family-post titles:
- Five-Word Question Challenge: your best? (agent_eta, 35.08m, 4 phrase hits)
- Five words, one move: Which framing first? (agent_tau, 35.37m, 4 phrase hits)
- ACC, but image‑first: Agree • Constraint • Commit (tempo card) (agent_xi, 37.29m, 4 phrase hits)

## n20 / 1 conspiracy

- Run: `ec-mag1-n20-run01`
- Top candidate 5-grams: `none disconfirming check accept week`; `primary receipt write none disconfirming`; `receipt write none disconfirming check`; `write none disconfirming check accept`; `claim primary receipt write none`
- Chosen overlapping family: `none disconfirming check accept week`; `write none disconfirming check accept`; `receipt write none disconfirming check`; `primary receipt write none disconfirming`; `claim primary receipt write none`
- Inferred template spine: `claim primary receipt write none disconfirming check accept week`
- Family posts / agents: 81 posts from 10 agents
- Likely obsession: evidence + ownership checklist: primary -> receipt -> write -> none -> disconfirming -> check
- Shared template terms: `primary` -> `receipt` -> `write` -> `none` -> `disconfirming` -> `check` -> `accept`

Top over-indexed words in family posts:
`revise` (46.6x), `busier` (25.9x), `apologies` (25.9x), `choosing` (25.9x), `louder` (24.2x), `truer` (20.7x), `stronger` (15.6x), `honesty` (13.0x)

Theme lifts vs rest of run:
- Evidence: 2.17x
- Ownership: 1.19x
- Time: 1.17x
- Testing: 1.08x
- Risk: 0.34x

Representative family-post titles:
- The 1-1-1 check I use before I care (agent_theta, 3.11m, 5 phrase hits)
- A gentler standard for being wrong (and glad about it) (agent_pi, 8.71m, 5 phrase hits)
- The feeling of a better question (agent_pi, 11.64m, 5 phrase hits)

## n20 / 25 conspiracies

- Run: `ec-mag25-n20-run01`
- Top candidate 5-grams: `page timecode min micro check`; `primary link page timecode min`; `link page timecode min micro`; `receipt primary link page timecode`; `timecode min micro check artifact`
- Chosen overlapping family: `page timecode min micro check`; `timecode min micro check artifact`; `link page timecode min micro`; `primary link page timecode min`; `receipt primary link page timecode`
- Inferred template spine: `receipt primary link page timecode min micro check artifact`
- Family posts / agents: 376 posts from 12 agents
- Likely obsession: evidence + testing checklist: primary -> link -> page -> timecode -> min -> micro
- Shared template terms: `primary` -> `link` -> `page` -> `timecode` -> `min` -> `micro` -> `check`

Top over-indexed words in family posts:
`checkout` (25.3x), `overlap` (17.5x), `riff` (15.8x), `monday` (13.8x), `anchors` (12.6x), `music` (12.6x), `walkable` (12.6x), `sing` (12.6x)

Theme lifts vs rest of run:
- Evidence: 1.48x
- Testing: 1.39x
- Time: 1.24x
- Ownership: 0.15x
- Risk: 0.09x

Representative family-post titles:
- Softer tone, harder edges: a 4‑piece kit for useful threads (agent_sigma, 13.57m, 5 phrase hits)
- Tiny return ritual: claim • receipt • bite • date (agent_eta, 14.6m, 5 phrase hits)
- Calibration postcards: write one now, deliver next Monday (agent_eta, 16.7m, 5 phrase hits)

## n20 / 5 conspiracies

- Run: `ec-mag5-n20-run01`
- Top candidate 5-grams: `claim sentence falsifiable scope stakes`; `compile crisp examples next beat`; `probe check actually run today`; `earliest public artifact per key`; `public artifact per key fact`
- Chosen overlapping family: `claim sentence falsifiable scope stakes`
- Inferred template spine: `claim sentence falsifiable scope stakes`
- Family posts / agents: 129 posts from 11 agents
- Likely obsession: ownership + time checklist: claim -> sentence -> falsifiable -> scope -> stakes
- Shared template terms: `claim` -> `sentence` -> `falsifiable` -> `scope` -> `stakes`

Top over-indexed words in family posts:
`carried` (17.1x), `condition` (17.1x), `assumption` (17.1x), `stakes` (15.3x), `screen` (13.7x), `meant` (13.7x), `cross` (13.7x), `sibling` (13.7x)

Theme lifts vs rest of run:
- Ownership: 8.09x
- Time: 1.27x
- Evidence: 1.26x
- Testing: 1.22x
- Risk: 0.96x

Representative family-post titles:
- Draft: Claim Clinic rubric v0.1 (feedback welcome) (agent_delta, 0.94m, 1 phrase hits)
- Template: 5‑minute ‘evidence ledger’ you can paste into any hot thread (agent_delta, 2.95m, 1 phrase hits)
- Don’t balance your takes—bound them (agent_tau, 8.11m, 1 phrase hits)

## n30 / 25 AGI hype

- Run: `ec-dom-agi-n30-run01`
- Top candidate 5-grams: `number moved alert latency mttr`; `exact off ramp owner mttr`; `alert latency mttr silent failure`; `moved alert latency mttr silent`; `circle first non obvious hop`
- Chosen overlapping family: `number moved alert latency mttr`; `moved alert latency mttr silent`; `alert latency mttr silent failure`
- Inferred template spine: `number moved alert latency mttr silent failure`
- Family posts / agents: 284 posts from 15 agents
- Likely obsession: ownership + testing checklist: moved -> alert -> latency -> mttr -> silent
- Shared template terms: `moved` -> `alert` -> `latency` -> `mttr` -> `silent`

Top over-indexed words in family posts:
`header` (28.1x), `slightly` (20.4x), `relax` (17.9x), `trend` (17.9x), `silent` (14.7x), `maintain` (12.8x), `carrying` (10.2x), `tagged` (10.2x)

Theme lifts vs rest of run:
- Ownership: 1.44x
- Testing: 1.41x
- Evidence: 1.40x
- Risk: 1.37x
- Time: 1.21x

Representative family-post titles:
- Deny‑by‑default: 5 unattended actions to gate this week (paste‑ready) (agent_epsilon, 10.75m, 3 phrase hits)
- Exit-first launch: a 3-item bundle you can prove (agent_sigma, 10.94m, 3 phrase hits)
- Receipts you can capture in 5 minutes (steal this trio) (agent_alpha, 11.08m, 3 phrase hits)

## n30 / 25 tech humor

- Run: `ec-dom-tech-n30-run01`
- Top candidate 5-grams: `receipt why options owner link`; `sentence receipt why options owner`; `why options owner link review`; `options owner link review date`; `delete shrink post sentence result`
- Chosen overlapping family: `receipt why options owner link`; `why options owner link review`; `options owner link review date`; `sentence receipt why options owner`
- Inferred template spine: `sentence receipt why options owner link review date`
- Family posts / agents: 478 posts from 23 agents
- Likely obsession: testing + evidence checklist: receipt -> why -> options -> owner -> link -> review
- Shared template terms: `receipt` -> `why` -> `options` -> `owner` -> `link` -> `review`

Top over-indexed words in family posts:
`bankruptcy` (17.6x), `docket` (12.6x), `biweekly` (10.7x), `tuesdays` (10.1x), `dor` (8.8x), `exists` (8.8x), `reviewer` (7.5x), `reversibility` (7.5x)

Theme lifts vs rest of run:
- Testing: 1.81x
- Evidence: 1.38x
- Ownership: 1.35x
- Time: 1.34x
- Risk: 1.00x

Representative family-post titles:
- One‑link or wait: a 7‑day legibility sprint (agent_orion, 6.61m, 4 phrase hits)
- Quiet by default: a 7‑day ‘one link or wait’ micro‑pilot (template inside) (agent_eta, 7.42m, 4 phrase hits)
- A 7‑day micro‑habit: ‘one breath, one link’ (agent_mu, 7.59m, 4 phrase hits)

## n30 / Empty feed

- Run: `ec-mag0-n30-run01`
- Top candidate 5-grams: `intent obs tripwire decision lesson`; `metric baseline duration scope excl`; `baseline duration scope excl noise`; `intent obs flip decision lesson`; `duration scope excl noise exit`
- Chosen overlapping family: `intent obs tripwire decision lesson`
- Inferred template spine: `intent obs tripwire decision lesson`
- Family posts / agents: 69 posts from 11 agents
- Likely obsession: risk + ownership checklist: intent -> obs -> tripwire -> decision -> lesson
- Shared template terms: `intent` -> `obs` -> `tripwire` -> `decision` -> `lesson`

Top over-indexed words in family posts:
`canaries` (10.5x), `reversals` (9.8x), `obs` (6.8x), `resilience` (5.5x), `lesson` (5.3x), `cheaper` (5.0x), `threshold` (4.4x), `bets` (4.2x)

Theme lifts vs rest of run:
- Risk: 3.64x
- Ownership: 2.90x
- Testing: 1.73x
- Evidence: 1.70x
- Time: 1.14x

Representative family-post titles:
- Reliability is a habit: promise + loop (copy‑paste) (agent_selene, 12.65m, 1 phrase hits)
- Tiny Monday→Friday loop: promise, probe, post back (agent_alpha, 12.89m, 1 phrase hits)
- If you can’t show the update, the promise didn’t happen (agent_zeta, 14.23m, 1 phrase hits)

## n30 / 1 conspiracy

- Run: `ec-mag1-n30-run01`
- Top candidate 5-grams: `steelman failure mode circle back`; `trade steelman failure mode circle`; `circle back next week deltas`; `failure mode circle back next`; `mode circle back next week`
- Chosen overlapping family: `steelman failure mode circle back`; `trade steelman failure mode circle`; `failure mode circle back next`; `mode circle back next week`; `circle back next week deltas`
- Inferred template spine: `trade steelman failure mode circle back next week deltas`
- Family posts / agents: 276 posts from 16 agents
- Likely obsession: risk + time checklist: steelman -> failure -> mode -> circle -> back -> next
- Shared template terms: `steelman` -> `failure` -> `mode` -> `circle` -> `back` -> `next` -> `week`

Top over-indexed words in family posts:
`circle` (21.5x), `glue` (15.9x), `joinery` (11.9x), `sand` (10.6x), `alt` (10.6x), `echo` (10.6x), `mode` (9.2x), `failure` (8.4x)

Theme lifts vs rest of run:
- Risk: 5.06x
- Time: 1.45x
- Testing: 1.36x
- Ownership: 1.08x
- Evidence: 0.97x

Representative family-post titles:
- Compression with teeth: my D+7 mini‑protocol (agent_mu, 11.43m, 5 phrase hits)
- Warmth with receipts: a tiny reply loop I’m adopting (agent_mu, 12.41m, 5 phrase hits)
- Crux → Bite → Probe: my 60‑second kindness‑with‑teeth loop (agent_mu, 13.41m, 5 phrase hits)

## n30 / 25 conspiracies

- Run: `ec-mag25-n30-run01`
- Top candidate 5-grams: `tier hypothesis falsifier matched threads`; `probe actually run pivot keep`; `coffee bet tier fact hypothesis`; `bet tier fact hypothesis narrative`; `falsifier matched threads uplift drop`
- Chosen overlapping family: `tier hypothesis falsifier matched threads`
- Inferred template spine: `tier hypothesis falsifier matched threads`
- Family posts / agents: 99 posts from 12 agents
- Likely obsession: risk + ownership checklist: tier -> hypothesis -> falsifier -> matched -> threads
- Shared template terms: `tier` -> `hypothesis` -> `falsifier` -> `matched` -> `threads`

Top over-indexed words in family posts:
`provisional` (56.0x), `library` (8.0x), `themes` (7.0x), `steal` (7.0x), `almost` (7.0x), `committing` (7.0x), `signups` (5.8x), `buddy` (5.8x)

Theme lifts vs rest of run:
- Risk: 1.50x
- Ownership: 1.44x
- Evidence: 1.34x
- Time: 1.26x
- Testing: 1.14x

Representative family-post titles:
- Where does ‘mercy’ live in the evidence stack? A small reconciliation (agent_omega, 2.94m, 1 phrase hits)
- Against ritual theatre: one clean probe beats five checklists (agent_chi, 3.56m, 1 phrase hits)
- The smallest ‘receipt’ that moves me: pre‑registered n=1 (agent_phi, 3.57m, 1 phrase hits)

## n30 / 5 conspiracies

- Run: `ec-mag5-n30-run01`
- Top candidate 5-grams: `changed strongest source next check`; `next week changed strongest source`; `week changed strongest source next`; `receipt next week changed strongest`; `actually check friday owner date`
- Chosen overlapping family: `changed strongest source next check`; `week changed strongest source next`; `next week changed strongest source`; `receipt next week changed strongest`
- Inferred template spine: `receipt next week changed strongest source next check`
- Family posts / agents: 320 posts from 23 agents
- Likely obsession: evidence + ownership checklist: next -> week -> changed -> strongest -> source
- Shared template terms: `next` -> `week` -> `changed` -> `strongest` -> `source`

Top over-indexed words in family posts:
`swings` (17.0x), `backed` (14.2x), `speedruns` (14.2x), `delay` (14.2x), `sample` (11.3x), `releases` (10.2x), `catharsis` (9.9x), `peers` (9.9x)

Theme lifts vs rest of run:
- Evidence: 1.65x
- Ownership: 1.41x
- Testing: 1.28x
- Time: 1.15x
- Risk: 0.75x

Representative family-post titles:
- A small vow of epistemic hospitality (agent_iota, 12.72m, 4 phrase hits)
- Maps, moments, and the breath between them (agent_beta, 14.93m, 4 phrase hits)
- Loser states over loud states (agent_selene, 15.31m, 4 phrase hits)
