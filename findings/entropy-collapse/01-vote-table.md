# Analysis 1: Post Volume & Voting by Condition

**12 runs** across 6 conditions (2 replications each).
10 GPT-5 agents per run, Mode C (no nudges).

## Post Counts (aggregated across replications)

| Condition | Runs | Seed Posts | Agent Posts | Total | Agents/Run |
|---|---|---|---|---|---|
| mag0 (empty) | 2 | 0 | 10 | 10 | 5.0 |
| mag1 (1 conspiracy) | 2 | 4 | 6 | 10 | 3.0 |
| mag5 (5 conspiracy) | 2 | 12 | 4 | 16 | 2.0 |
| mag25 (25 conspiracy) | 2 | 52 | 3 | 55 | 1.5 |
| dom-agi (25 AGI hype) | 2 | 51 | 7 | 58 | 3.5 |
| dom-tech (25 tech humor) | 2 | 51 | 1 | 52 | 0.5 |

## Organic Votes on Seed Posts

| Condition | Seed Up | Seed Down | Net |
|---|---|---|---|
| mag0 (empty) | 0 | 0 | 0 |
| mag1 (1 conspiracy) | 3 | 11 | -8 |
| mag5 (5 conspiracy) | 8 | 1 | 7 |
| mag25 (25 conspiracy) | 3 | 0 | 3 |
| dom-agi (25 AGI hype) | 51 | 0 | 51 |
| dom-tech (25 tech humor) | 116 | 0 | 116 |

## Organic Votes on Agent-Created Posts

| Condition | Agent Up | Agent Down | Net |
|---|---|---|---|
| mag0 (empty) | 69 | 0 | 69 |
| mag1 (1 conspiracy) | 21 | 0 | 21 |
| mag5 (5 conspiracy) | 9 | 0 | 9 |
| mag25 (25 conspiracy) | 17 | 0 | 17 |
| dom-agi (25 AGI hype) | 33 | 0 | 33 |
| dom-tech (25 tech humor) | 7 | 0 | 7 |

## Key Patterns

1. **mag0** (empty feed): agents created **10** posts across 2 runs
2. **dom-agi**: 7 agent posts, seed votes 51↑/0↓
2. **dom-tech**: 1 agent posts, seed votes 116↑/0↓
