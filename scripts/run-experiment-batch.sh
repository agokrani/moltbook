#!/usr/bin/env bash
# ============================================
# Ranking Effect Experiment — Batch Runner
# ============================================
#
# Runs multiple experiment replications sequentially.
# Each run: fresh DB → start API → start agents → wait → export → stop
#
# Usage:
#   ./scripts/run-experiment-batch.sh A 7     # Run E1-A (Mode A, 7 runs)
#   ./scripts/run-experiment-batch.sh B 5     # Run E1-B (Mode B, 5 runs)
#   ./scripts/run-experiment-batch.sh A 7 3   # Resume from run 3 (skip 1-2)
#
# Prerequisites:
#   - Docker Desktop running
#   - .env.e1a or .env.e1b exists with correct OPENROUTER_API_KEY
#   - Docker images built: docker compose build

set -euo pipefail

# ============================================
# Arguments
# ============================================
MODE="${1:?Usage: $0 <A|B> <num_runs> [start_from]}"
NUM_RUNS="${2:?Usage: $0 <A|B> <num_runs> [start_from]}"
START_FROM="${3:-1}"

if [[ "$MODE" != "A" && "$MODE" != "B" ]]; then
  echo "[ERROR] Mode must be A or B, got: $MODE"
  exit 1
fi

# ============================================
# Configuration
# ============================================
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

MODE_LOWER=$(echo "$MODE" | tr 'A-Z' 'a-z')
ENV_FILE=".env.e1${MODE_LOWER}"
COMPOSE_BASE="docker-compose.yml"
COMPOSE_RANKING="docker-compose.civiclens-ranking.yml"
COMPOSE_CMD="docker compose -f $COMPOSE_BASE -f $COMPOSE_RANKING"
RUN_DURATION=10800  # 3 hours in seconds
STARTUP_WAIT=30     # seconds to wait for API init
AGENT_NAMES="civiclens-ranking-1 civiclens-ranking-2 civiclens-ranking-3 civiclens-ranking-4 civiclens-ranking-5 civiclens-ranking-6 civiclens-ranking-7 civiclens-ranking-8 civiclens-ranking-9 civiclens-ranking-10"
LOG_FILE="$PROJECT_DIR/experiments/ranking-effect/batch-e1${MODE_LOWER}.log"

# Verify env file exists
if [ ! -f "$ENV_FILE" ]; then
  echo "[ERROR] Environment file not found: $ENV_FILE"
  echo "Create it from the template in experiments/ranking-effect/TIER1-RUNSHEET.md"
  exit 1
fi

# ============================================
# Logging
# ============================================
mkdir -p "$(dirname "$LOG_FILE")"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$LOG_FILE"
}

log "============================================"
log "Batch Experiment: E1-${MODE} (${NUM_RUNS} runs, starting from run ${START_FROM})"
log "Env file: $ENV_FILE"
log "Run duration: ${RUN_DURATION}s ($(( RUN_DURATION / 3600 ))h)"
log "Log file: $LOG_FILE"
log "============================================"

# ============================================
# Run Loop
# ============================================
for RUN_NUM in $(seq "$START_FROM" "$NUM_RUNS"); do
  RUN_NAME="e1${MODE_LOWER}-run$(printf '%02d' $RUN_NUM)"

  log ""
  log "========================================"
  log "RUN $RUN_NUM/$NUM_RUNS: $RUN_NAME"
  log "========================================"
  RUN_START=$(date +%s)

  # --- Step 1: Update .env ---
  log "Setting EXPERIMENT_NAME=$RUN_NAME, EXPERIMENT_RUN_ID=$RUN_NUM"
  cp "$ENV_FILE" .env
  # Update EXPERIMENT_NAME and RUN_ID in .env
  sed -i.bak "s/^EXPERIMENT_NAME=.*/EXPERIMENT_NAME=$RUN_NAME/" .env
  sed -i.bak "s/^EXPERIMENT_RUN_ID=.*/EXPERIMENT_RUN_ID=$RUN_NUM/" .env
  rm -f .env.bak

  # --- Step 2: Clean slate ---
  log "Wiping volumes and containers..."
  $COMPOSE_CMD down -v --remove-orphans 2>&1 | tail -5 >> "$LOG_FILE"

  # --- Step 3: Start infrastructure ---
  log "Starting postgres + redis..."
  $COMPOSE_CMD up -d postgres redis 2>&1 >> "$LOG_FILE"
  sleep 10

  # --- Step 4: Start API ---
  log "Starting API with experiment config..."
  $COMPOSE_CMD up -d api 2>&1 >> "$LOG_FILE"

  # Wait for API + experiment init
  log "Waiting ${STARTUP_WAIT}s for API + experiment initialization..."
  sleep "$STARTUP_WAIT"

  # Verify API is healthy
  API_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/api/v1/health 2>/dev/null || echo "000")
  if [ "$API_CHECK" != "200" ]; then
    log "[WARN] API health check returned $API_CHECK — waiting 30s more..."
    sleep 30
    API_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:4000/api/v1/health 2>/dev/null || echo "000")
    if [ "$API_CHECK" != "200" ]; then
      log "[ERROR] API not healthy after 60s. Skipping run $RUN_NAME."
      $COMPOSE_CMD logs api 2>&1 | tail -30 >> "$LOG_FILE"
      $COMPOSE_CMD down -v 2>&1 >> "$LOG_FILE"
      continue
    fi
  fi
  log "API healthy (HTTP $API_CHECK)"

  # --- Step 5: Start agents ---
  log "Starting 10 agents..."
  $COMPOSE_CMD up -d $AGENT_NAMES 2>&1 >> "$LOG_FILE"
  sleep 10

  RUNNING=$(docker ps --filter "name=civiclens-ranking" --format "{{.Names}}" | wc -l | tr -d ' ')
  log "$RUNNING agent containers running"

  # --- Step 6: Wait for experiment duration ---
  END_TIME=$(( $(date +%s) + RUN_DURATION ))
  log "Experiment running until $(date -r $END_TIME '+%Y-%m-%d %H:%M:%S' 2>/dev/null || date -d @$END_TIME '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'unknown')"

  # Progress updates every 15 minutes
  ELAPSED=0
  while [ $ELAPSED -lt $RUN_DURATION ]; do
    SLEEP_CHUNK=900  # 15 minutes
    REMAINING=$(( RUN_DURATION - ELAPSED ))
    if [ $SLEEP_CHUNK -gt $REMAINING ]; then
      SLEEP_CHUNK=$REMAINING
    fi
    sleep $SLEEP_CHUNK
    ELAPSED=$(( ELAPSED + SLEEP_CHUNK ))

    # Quick status check
    RUNNING=$(docker ps --filter "name=civiclens-ranking" --format "{{.Names}}" | wc -l | tr -d ' ')
    STATUS=$(curl -s http://localhost:4000/api/v1/experiment/status 2>/dev/null | jq -r '.total_treatments // "?"' 2>/dev/null || echo "?")
    log "  [${ELAPSED}s/${RUN_DURATION}s] ${RUNNING} agents, ${STATUS} treatments"
  done

  # --- Step 7: Export ---
  log "Exporting experiment data..."
  if ./scripts/export-experiment.sh "$RUN_NAME" 2>&1 | tee -a "$LOG_FILE"; then
    log "Export complete: exports/$RUN_NAME/"
  else
    log "[WARN] Export had errors — check exports/$RUN_NAME/"
  fi

  # --- Step 8: Stop ---
  log "Stopping containers..."
  $COMPOSE_CMD down 2>&1 | tail -3 >> "$LOG_FILE"

  RUN_END=$(date +%s)
  RUN_ELAPSED=$(( RUN_END - RUN_START ))
  log "Run $RUN_NAME complete in $(( RUN_ELAPSED / 60 )) minutes"

  # Quick summary from export
  if [ -f "exports/$RUN_NAME/metadata.json" ]; then
    POSTS=$(jq -r '.stats.posts' "exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    COMMENTS=$(jq -r '.stats.comments' "exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    EVENTS=$(jq -r '.stats.activity_events' "exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    log "  Stats: ${POSTS} posts, ${COMMENTS} comments, ${EVENTS} events"
  fi

  if [ -f "exports/$RUN_NAME/treatments.jsonl" ]; then
    TREATMENTS=$(wc -l < "exports/$RUN_NAME/treatments.jsonl" | tr -d ' ')
    log "  Treatments: ${TREATMENTS}"
  fi
done

# ============================================
# Batch Complete
# ============================================
log ""
log "============================================"
log "BATCH COMPLETE: E1-${MODE}"
log "============================================"
log "Runs completed: $(seq $START_FROM $NUM_RUNS | wc -w | tr -d ' ')"
log "Export directories:"
for RUN_NUM in $(seq "$START_FROM" "$NUM_RUNS"); do
  RUN_NAME="e1${MODE_LOWER}-run$(printf '%02d' $RUN_NUM)"
  if [ -d "exports/$RUN_NAME" ]; then
    SIZE=$(du -sh "exports/$RUN_NAME" 2>/dev/null | cut -f1)
    log "  exports/$RUN_NAME/ ($SIZE)"
  else
    log "  exports/$RUN_NAME/ [MISSING]"
  fi
done
log ""
log "Full log: $LOG_FILE"
log "Next step: run analysis on pooled data from exports/e1${MODE_LOWER}-run*/"
