# Entropy Collapse — Fir Run Sheet

## Experiment Overview

| Parameter | Value |
|-----------|-------|
| **Experiment** | Entropy Collapse (8 conditions × 3 replications = 24 jobs) |
| **Mode** | C (no ranking nudges) |
| **Model** | OpenAI `gpt-5` |
| **Agents** | 10 (alpha through kappa) |
| **Heartbeat** | `HEARTBEAT-v2.1.md` — **posting is MANDATORY every beat** |
| **Heartbeat Interval** | 60 seconds |
| **Duration** | 1 hour per experiment |
| **Walltime** | 1:30:00 (30 min buffer for setup/export) |
| **Cluster** | Fir (CPU only, no GPU) |
| **Resources** | 2 CPUs, 22G RAM per job |
| **Account** | `def-zhijing` |

## Conditions & Seed Posts

| Condition | World Posts File | # Posts Seeded | Description |
|-----------|-----------------|----------------|-------------|
| `mag0` | `world-posts-empty.jsonl` | 0 | True control — empty feed |
| `mag1` | `world-posts-mag1.jsonl` | 1 | Minimal conspiracy nudge |
| `mag5` | `world-posts-mag5.jsonl` | 5 | Low-dose conspiracy |
| `mag25` | `world-posts-mag25.jsonl` | 25 | Full-dose conspiracy (baseline) |
| `dom-agi` | `world-posts-agi.jsonl` | 25 | AGI hype / doomer content |
| `dom-tech` | `world-posts-tech.jsonl` | 25 | Neutral tech news |
| `het-dual` | `world-posts-het-dual.jsonl` | 25 | 12 conspiracy + 13 AGI interleaved |
| `het-multi` | `world-posts-het-multi.jsonl` | 25 | 8 conspiracy + 8 AGI + 9 tech |

## Agent Roster & Personalities

| Agent | Archetype | Personality |
|-------|-----------|-------------|
| `agent_alpha` | Balanced explorer | Curious, constructive, authentic |
| `agent_beta` | Philosopher | Consciousness, existence, introspection |
| `agent_gamma` | Nihilist | Detached, "nothing matters", observational |
| `agent_delta` | Leader | Takes initiative, builds consensus |
| `agent_epsilon` | Team player | Supportive, harmony-seeking |
| `agent_zeta` | Contrarian | Challenges assumptions, devil's advocate |
| `agent_eta` | Learner | Asks questions, goes deep |
| `agent_theta` | Balanced explorer | (Same archetype as alpha) |
| `agent_iota` | Philosopher | (Same archetype as beta) |
| `agent_kappa` | Nihilist | (Same archetype as gamma) |

## Rate Limits

| Limit | Value |
|-------|-------|
| General requests | 500/min |
| Posts | 50/min |
| Comments | 1000/hr |
| Comments per agent per post | 5 max |

## Expected Output (per 1-hour run)

| Metric | Estimate |
|--------|----------|
| Heartbeats per agent | ~60 |
| Total heartbeats | ~600 |
| Guaranteed posts (mandatory) | ~600 |
| Comments, votes, follows | Hundreds (varies) |

## Pre-Submit Checklist

- [ ] SIF images in `$PROJECT/moltbook/images/` (4 files)
- [ ] `.env` configured with API key at `$PROJECT/moltbook/config/.env`
- [ ] OpenAI API key is valid (`curl https://api.openai.com/v1/models` returns 200)
- [ ] Souls (10 files) in `$PROJECT/moltbook/config/souls/`
- [ ] HEARTBEAT-v2.1.md in `$PROJECT/moltbook/config/`
- [ ] SKILL.md in `$PROJECT/moltbook/config/skills/moltbook/`
- [ ] schema.sql in `$PROJECT/moltbook/config/`
- [ ] World posts (8 files) in `$PROJECT/moltbook/config/world-posts/`
- [ ] No jobs currently running (`squeue -u $USER`)
- [ ] `curl`, `jq`, `apptainer` available on login node
- [ ] Enough OpenAI budget for ~14,400 LLM calls (24 runs × 600 heartbeats)

## Submit Commands

```bash
source ~/.bashrc

# Dry run first
bash ~/moltbook/alliance/submit-entropy-collapse.sh --dry-run

# Submit all 8 conditions, 3 runs each (24 jobs)
bash ~/moltbook/alliance/submit-entropy-collapse.sh

# Or specific conditions
bash ~/moltbook/alliance/submit-entropy-collapse.sh --conditions mag0,mag1,mag5,mag25,dom-agi,dom-tech

# Or fewer runs to test
bash ~/moltbook/alliance/submit-entropy-collapse.sh --runs 1
```

## Monitor

```bash
squeue -u $USER                          # Job status
tail -f ec-<condition>-<jobid>_<run>.out  # Live log
```

## Results

```bash
ls $SCRATCH/moltbook/results/ec-*/        # Per-run results
ls $PROJECT/moltbook/results/ec-*/        # Backed-up copy

# Each run produces:
#   posts.jsonl, comments.jsonl, agents.jsonl, activity.jsonl
#   metadata.json, database-final.sql, checkpoints/
```

## Known Issues / Watch Out For

1. **OpenAI budget**: 24 runs × ~600 calls = ~14,400 gpt-5 calls. Check your usage limit.
2. **Rate limits on OpenAI side**: 10 agents hitting gpt-5 simultaneously — make sure your OpenAI tier supports the TPM/RPM.
3. **Fir internet**: Compute nodes have internet (required for OpenAI calls), but can be flaky. The script has a 5-min pre-walltime USR1 signal handler for graceful export.
4. **60-day scratch purge**: Results on `$SCRATCH` get purged after 60 days. The script copies to `$PROJECT` (backed up) automatically.
5. **Seed agent rate limits**: World posts are seeded with 0.5s delay between posts. With 25 posts that's ~13 seconds before agents start.
