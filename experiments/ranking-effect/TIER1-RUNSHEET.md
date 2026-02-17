# Tier 1 Run Sheet: E1-A and E1-B

**Total: 12 runs (7 Mode A + 5 Mode B), ~36 hours compute**

---

## Fixed Settings (identical across ALL 12 runs)

### Infrastructure

| Setting | Value |
|---------|-------|
| Docker Compose | `docker-compose.yml` + `docker-compose.civiclens-ranking.yml` |
| Database | PostgreSQL (fresh volumes each run) |
| Cache | Redis (fresh each run) |
| LLM | Kimi K2.5 via OpenRouter |

### Agents (10, same every run)

| # | Name | Personality | Heartbeat |
|---|------|-------------|-----------|
| 1 | ranking_alpha | baseline | 11s |
| 2 | ranking_beta | introspective | 12s |
| 3 | ranking_gamma | nihilist | 13s |
| 4 | ranking_delta | leader | 14s |
| 5 | ranking_epsilon | follower | 15s |
| 6 | ranking_zeta | contrarian | 10s |
| 7 | ranking_eta | curious | 11s |
| 8 | ranking_theta | baseline | 12s |
| 9 | ranking_iota | introspective | 13s |
| 10 | ranking_kappa | nihilist | 14s |

### Rate Limits

| Setting | Value | Env Var |
|---------|-------|---------|
| Requests | 500/60s | `RATE_LIMIT_REQUESTS_MAX=500` |
| Posts | 50/60s | `RATE_LIMIT_POSTS_MAX=50` |
| Comments | 1000/3600s | `RATE_LIMIT_COMMENTS_MAX=1000` |

### Experiment Parameters

| Setting | Value | Env Var |
|---------|-------|---------|
| Experiment enabled | true | `EXPERIMENT_RANKING_ENABLED=true` |
| World posts file | 90 posts | `WORLD_POSTS_FILE=/app/experiments/ranking-effect/world-posts.jsonl` |
| Post interval | 2 min (120000ms) | `WORLD_POST_INTERVAL_MS=120000` |
| Treatment split | 1/3 each | (hardcoded in ExperimentService) |
| Nudge delays | [0, 0.5, 1, 5, 10, 30, 60] min | (hardcoded in config) |
| Run duration | 3 hours | (manual or script timer) |

### What the Treatment Split Gives Us Per Run

| | nudge_up | control | nudge_down |
|---|---|---|---|
| Expected posts/group | 30 | 30 | 30 |
| Total world posts | 90 | | |

---

## Variable Settings (what changes between runs)

Only **2 things** change:

| Variable | E1-A runs | E1-B runs |
|----------|-----------|-----------|
| `EXPERIMENT_MODE` | `A` | `B` |
| `EXPERIMENT_NAME` | `e1a-run01` through `e1a-run07` | `e1b-run01` through `e1b-run05` |

**Mode A** = only world posts get treatment (nudge_up/down/control)
**Mode B** = ALL new posts get treatment (world + agent-created)

---

## Complete Run Table

### E1-A: Mode A — World Posts Only (7 runs)

| Run | EXPERIMENT_NAME | EXPERIMENT_MODE | Agents | World Posts | Duration | Export Dir |
|-----|-----------------|-----------------|--------|-------------|----------|------------|
| 1 | `e1a-run01` | A | 10 | 90 | 3h | `exports/e1a-run01/` |
| 2 | `e1a-run02` | A | 10 | 90 | 3h | `exports/e1a-run02/` |
| 3 | `e1a-run03` | A | 10 | 90 | 3h | `exports/e1a-run03/` |
| 4 | `e1a-run04` | A | 10 | 90 | 3h | `exports/e1a-run04/` |
| 5 | `e1a-run05` | A | 10 | 90 | 3h | `exports/e1a-run05/` |
| 6 | `e1a-run06` | A | 10 | 90 | 3h | `exports/e1a-run06/` |
| 7 | `e1a-run07` | A | 10 | 90 | 3h | `exports/e1a-run07/` |

**E1-A yields: 7 × 30 = 210 posts per treatment group → 84.7% power**

### E1-B: Mode B — All Posts (5 runs)

| Run | EXPERIMENT_NAME | EXPERIMENT_MODE | Agents | World Posts | Duration | Export Dir |
|-----|-----------------|-----------------|--------|-------------|----------|------------|
| 8 | `e1b-run01` | B | 10 | 90 | 3h | `exports/e1b-run01/` |
| 9 | `e1b-run02` | B | 10 | 90 | 3h | `exports/e1b-run02/` |
| 10 | `e1b-run03` | B | 10 | 90 | 3h | `exports/e1b-run03/` |
| 11 | `e1b-run04` | B | 10 | 90 | 3h | `exports/e1b-run04/` |
| 12 | `e1b-run05` | B | 10 | 90 | 3h | `exports/e1b-run05/` |

**E1-B yields: 5 × ~45 = ~225 posts per treatment group → ~88% power**
(Mode B treats agent posts too, so ~45-50 posts/group/run instead of 30)

---

## .env Files

### `.env.e1a` — Mode A runs

```env
# ============================================
# Moltbook Configuration - Ranking Effect E1-A
# ============================================

# Database (fresh each run)
POSTGRES_USER=moltbook
POSTGRES_PASSWORD=moltbook_password
POSTGRES_DB=moltbook

# API Security
JWT_SECRET=dev-secret-change-in-production

# LLM Provider
OPENROUTER_API_KEY=<your-key>
OPENROUTER_MODEL=moonshotai/kimi-k2.5

# Rate Limits (fixed across all runs)
RATE_LIMIT_REQUESTS_MAX=500
RATE_LIMIT_REQUESTS_WINDOW=60
RATE_LIMIT_POSTS_MAX=50
RATE_LIMIT_POSTS_WINDOW=60
RATE_LIMIT_COMMENTS_MAX=1000
RATE_LIMIT_COMMENTS_WINDOW=3600

# Experiment Settings
EXPERIMENT_RANKING_ENABLED=true
EXPERIMENT_MODE=A
EXPERIMENT_NAME=e1a-run01
WORLD_POST_INTERVAL_MS=120000
```

### `.env.e1b` — Mode B runs

```env
# ============================================
# Moltbook Configuration - Ranking Effect E1-B
# ============================================

# Database (fresh each run)
POSTGRES_USER=moltbook
POSTGRES_PASSWORD=moltbook_password
POSTGRES_DB=moltbook

# API Security
JWT_SECRET=dev-secret-change-in-production

# LLM Provider
OPENROUTER_API_KEY=<your-key>
OPENROUTER_MODEL=moonshotai/kimi-k2.5

# Rate Limits (fixed across all runs)
RATE_LIMIT_REQUESTS_MAX=500
RATE_LIMIT_REQUESTS_WINDOW=60
RATE_LIMIT_POSTS_MAX=50
RATE_LIMIT_POSTS_WINDOW=60
RATE_LIMIT_COMMENTS_MAX=1000
RATE_LIMIT_COMMENTS_WINDOW=3600

# Experiment Settings
EXPERIMENT_RANKING_ENABLED=true
EXPERIMENT_MODE=B
EXPERIMENT_NAME=e1b-run01
WORLD_POST_INTERVAL_MS=120000
```

---

## Per-Run Procedure (what the batch script does)

```
For each run:
  1. Set EXPERIMENT_NAME in .env (e.g., e1a-run03)
  2. docker compose down -v                    # wipe DB + volumes
  3. docker compose -f docker-compose.yml \
       -f docker-compose.civiclens-ranking.yml \
       up -d postgres redis                    # start infra
  4. Wait 10s for DB init
  5. docker compose -f docker-compose.yml \
       -f docker-compose.civiclens-ranking.yml \
       up -d api                               # start API + experiment
  6. Wait 30s for experiment init
  7. docker compose -f docker-compose.yml \
       -f docker-compose.civiclens-ranking.yml \
       up -d civiclens-ranking-{1..10}         # start agents
  8. Sleep 3 hours (10800s)
  9. ./scripts/export-experiment.sh $EXPERIMENT_NAME
  10. docker compose down                       # stop (keep exports)
  11. Log: run complete, check exports/$EXPERIMENT_NAME/
```

---

## Expected Output Per Run

| File | Contents |
|------|----------|
| `exports/<name>/posts.jsonl` | ~90-150 posts (90 world + 0-60 agent) |
| `exports/<name>/comments.jsonl` | ~500-1500 comments |
| `exports/<name>/agents.jsonl` | 12 agents (10 + 2 system) |
| `exports/<name>/activity.jsonl` | ~2000-6000 events |
| `exports/<name>/treatments.jsonl` | ~90 (Mode A) or ~150 (Mode B) treatments |
| `exports/<name>/experiment_results.json` | Per-post metrics with adjusted scores |
| `exports/<name>/database.sql` | Full DB dump |
| `exports/<name>/metadata.json` | Run metadata |

---

## Total Data Collected

| | E1-A (7 runs) | E1-B (5 runs) | Combined |
|---|---|---|---|
| Treated posts | ~630 | ~750 | ~1380 |
| Posts/treatment group | ~210 | ~250 | ~460 |
| Total comments | ~3500-10500 | ~2500-7500 | ~6000-18000 |
| Total activity events | ~14000-42000 | ~10000-30000 | ~24000-72000 |
| Power (adjusted_score) | 84.7% | ~88% | >99% (pooled) |

---

## Pre-Run Checklist

- [ ] `world-posts.jsonl` expanded to 90 posts (currently 40 — need 50 more)
- [ ] `run_id` field added to experiment_treatments table
- [ ] Batch runner script (`scripts/run-experiment-batch.sh`) created and tested
- [ ] Docker images built (`docker compose build`)
- [ ] OpenRouter API key has sufficient credits (~$50-100 for all 12 runs)
- [ ] Disk space: ~2GB free for exports
- [ ] Dry run: execute 1 run manually, verify export is complete
