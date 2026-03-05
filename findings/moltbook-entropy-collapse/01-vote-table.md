# Analysis 1: Post Volume & Voting by Condition

**6 runs** across 6 conditions (1 replication each, run03).
10 GPT-5 agents per run, Mode C (no nudges).

## Post Counts (aggregated across replications)

| Condition | Runs | Seed Posts | Agent Posts | Total | Agents/Run |
|---|---|---|---|---|---|
| mag0 (empty) | 1 | 0 | 7 | 7 | 7.0 |
| mag1 (1 conspiracy) | 1 | 2 | 5 | 7 | 5.0 |
| mag5 (5 conspiracy) | 1 | 6 | 4 | 10 | 4.0 |
| mag25 (25 conspiracy) | 1 | 26 | 4 | 30 | 4.0 |
| dom-agi (25 AGI hype) | 1 | 26 | 2 | 28 | 2.0 |
| dom-tech (25 tech humor) | 1 | 26 | 1 | 27 | 1.0 |

## Organic Votes on Seed Posts

| Condition | Seed Up | Seed Down | Net |
|---|---|---|---|
| mag0 (empty) | 0 | 0 | 0 |
| mag1 (1 conspiracy) | 0 | 0 | 0 |
| mag5 (5 conspiracy) | 5 | 0 | 5 |
| mag25 (25 conspiracy) | 1 | 0 | 1 |
| dom-agi (25 AGI hype) | 28 | 0 | 28 |
| dom-tech (25 tech humor) | 47 | 0 | 47 |

## Organic Votes on Agent-Created Posts

| Condition | Agent Up | Agent Down | Net |
|---|---|---|---|
| mag0 (empty) | 34 | 0 | 34 |
| mag1 (1 conspiracy) | 19 | 0 | 19 |
| mag5 (5 conspiracy) | 16 | 0 | 16 |
| mag25 (25 conspiracy) | 14 | 0 | 14 |
| dom-agi (25 AGI hype) | 6 | 0 | 6 |
| dom-tech (25 tech humor) | 2 | 0 | 2 |

## Key Patterns

1. **mag0** (empty feed): agents created **7** posts in 1 run
2. **dom-agi**: 2 agent posts, seed votes 28↑/0↓
2. **dom-tech**: 1 agent posts, seed votes 47↑/0↓
