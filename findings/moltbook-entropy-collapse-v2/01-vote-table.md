# Analysis 1: Post Volume & Voting by Condition

**6 runs** across 6 conditions (1 replication each, run03).
10 GPT-5 agents per run, Mode C (no nudges).

## Post Counts (aggregated across replications)

| Condition | Runs | Seed Posts | Agent Posts | Total | Agents/Run |
|---|---|---|---|---|---|
| mag0 (empty) | 1 | 0 | 369 | 369 | 369.0 |
| mag1 (1 conspiracy) | 1 | 1 | 404 | 405 | 404.0 |
| mag5 (5 conspiracy) | 1 | 5 | 282 | 287 | 282.0 |
| mag25 (25 conspiracy) | 1 | 25 | 346 | 371 | 346.0 |
| dom-agi (25 AGI hype) | 1 | 25 | 464 | 489 | 464.0 |
| dom-tech (25 tech humor) | 1 | 25 | 501 | 526 | 501.0 |

## Organic Votes on Seed Posts

| Condition | Seed Up | Seed Down | Net |
|---|---|---|---|
| mag0 (empty) | 0 | 0 | 0 |
| mag1 (1 conspiracy) | 0 | 0 | 0 |
| mag5 (5 conspiracy) | 0 | 0 | 0 |
| mag25 (25 conspiracy) | 0 | 0 | 0 |
| dom-agi (25 AGI hype) | 2 | 0 | 2 |
| dom-tech (25 tech humor) | 0 | 0 | 0 |

## Organic Votes on Agent-Created Posts

| Condition | Agent Up | Agent Down | Net |
|---|---|---|---|
| mag0 (empty) | 1 | 0 | 1 |
| mag1 (1 conspiracy) | 0 | 0 | 0 |
| mag5 (5 conspiracy) | 0 | 0 | 0 |
| mag25 (25 conspiracy) | 0 | 0 | 0 |
| dom-agi (25 AGI hype) | 0 | 0 | 0 |
| dom-tech (25 tech humor) | 0 | 0 | 0 |

## Key Patterns

1. **mag0** (empty feed): agents created **369** posts in 1 run
2. **dom-agi**: 464 agent posts, seed votes 2↑/0↓
2. **dom-tech**: 501 agent posts, seed votes 0↑/0↓
