#!/usr/bin/env bash
# Quick run: just f0 (pure conspiracy) + f1 (1 factual) in parallel
# All Grok 4.1 Fast, 60s heartbeat, 1 hour
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

# Source the slot_worker and helpers from the main runner
COMPOSE_BASE="docker-compose.parallel.yml"
COMPOSE_OVERLAY="docker-compose.civiclens-mixed-model-parallel.yml"
EXPORT_SCRIPT="$PROJECT_DIR/scripts/export-experiment-parallel.sh"
BASE_ENV="$PROJECT_DIR/.env.factcheck-mixed"

RUN_DURATION=3600
STARTUP_WAIT=30
PROGRESS_INTERVAL=900
RUN_NUMBER="03"
PREFIX="fcm"

API_PORT_BASE=4000
PG_PORT_BASE=5432
REDIS_PORT_BASE=6379
PORT_STEP=10

LOG_DIR="$PROJECT_DIR/experiments/factcheck/parallel-logs"
mkdir -p "$LOG_DIR"
SUMMARY_LOG="$LOG_DIR/summary-mixed-f0f1.log"

# Portable timeout
if command -v timeout &>/dev/null; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout &>/dev/null; then
  TIMEOUT_CMD="gtimeout"
else
  TIMEOUT_CMD=""
fi

run_with_timeout() {
  local secs="$1"; shift
  if [ -n "$TIMEOUT_CMD" ]; then
    $TIMEOUT_CMD "$secs" "$@"
  else
    "$@"
  fi
}

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$SUMMARY_LOG"
}

# ============================================
# Slot Worker (copied from main runner)
# ============================================
slot_worker() {
  set +e
  local SLOT=$1 N_FACTUAL=$2 RUN_NAME=$3
  local SLOT_LOG="$LOG_DIR/${RUN_NAME}.log"
  local API_PORT=$((API_PORT_BASE + SLOT * PORT_STEP))
  local PG_PORT=$((PG_PORT_BASE + SLOT * PORT_STEP))
  local REDIS_PORT=$((REDIS_PORT_BASE + SLOT * PORT_STEP))
  local PROJECT_NAME="slot${SLOT}"
  local COMPOSE_CMD="docker compose -p $PROJECT_NAME -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_OVERLAY"

  slog() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [slot$SLOT/$RUN_NAME] $1"
    echo "$msg" >> "$SLOT_LOG"
    echo "$msg" >> "$SUMMARY_LOG"
    echo "$msg"
  }

  worker_cleanup() {
    slog "Cleaning up slot $SLOT..."
    run_with_timeout 120 $COMPOSE_CMD down -v --remove-orphans 2>>"$SLOT_LOG" || \
      run_with_timeout 30 $COMPOSE_CMD kill 2>>"$SLOT_LOG" || true
    rm -f "$PROJECT_DIR/.env.slot${SLOT}"
  }

  slog "=== START: $RUN_NAME (slot $SLOT, ${N_FACTUAL}F + $((25 - N_FACTUAL))C) ==="
  slog "Models: Grok 4.1 Fast (all 10 agents)"
  slog "Ports: API=$API_PORT PG=$PG_PORT Redis=$REDIS_PORT"
  local WORKER_START=$(date +%s)

  # Clean slate
  run_with_timeout 120 $COMPOSE_CMD down -v --remove-orphans 2>>"$SLOT_LOG" || true

  # Per-slot env
  local SLOT_ENV="$PROJECT_DIR/.env.slot${SLOT}"
  cp "$BASE_ENV" "$SLOT_ENV"
  echo "" >> "$SLOT_ENV"
  echo "# Per-slot overrides" >> "$SLOT_ENV"
  echo "EXPERIMENT_NAME=$RUN_NAME" >> "$SLOT_ENV"
  echo "WORLD_POSTS_FILE=/app/experiments/factcheck/world-posts-f${N_FACTUAL}.jsonl" >> "$SLOT_ENV"
  echo "HOST_API_PORT=$API_PORT" >> "$SLOT_ENV"
  echo "HOST_PG_PORT=$PG_PORT" >> "$SLOT_ENV"
  echo "HOST_REDIS_PORT=$REDIS_PORT" >> "$SLOT_ENV"

  export HOST_API_PORT=$API_PORT HOST_PG_PORT=$PG_PORT HOST_REDIS_PORT=$REDIS_PORT
  COMPOSE_CMD="docker compose -p $PROJECT_NAME --env-file $SLOT_ENV -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_OVERLAY"

  # Start infra
  slog "Starting postgres + redis..."
  $COMPOSE_CMD up -d postgres redis 2>>"$SLOT_LOG" || { slog "[ERROR] infra failed"; echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"; worker_cleanup; return 1; }
  sleep 15

  slog "Starting API..."
  $COMPOSE_CMD up -d api 2>>"$SLOT_LOG"
  slog "Waiting for API on port $API_PORT..."
  local API_READY=false
  for attempt in $(seq 1 30); do
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/api/v1/health" 2>/dev/null | grep -q "200" && { API_READY=true; break; }
    sleep 3
  done
  if [ "$API_READY" = false ]; then
    slog "[ERROR] API failed to start"; echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"; worker_cleanup; return 1
  fi
  slog "API healthy"

  slog "Starting 10 Grok agents..."
  $COMPOSE_CMD up --build -d \
    civiclens-ranking-1 civiclens-ranking-2 civiclens-ranking-3 \
    civiclens-ranking-4 civiclens-ranking-5 civiclens-ranking-6 \
    civiclens-ranking-7 civiclens-ranking-8 civiclens-ranking-9 \
    civiclens-ranking-10 2>>"$SLOT_LOG" || slog "[WARN] Some agents failed"
  sleep "$STARTUP_WAIT"

  local RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep -c "ranking" || true)
  slog "$RUNNING agent containers running"

  # Run experiment
  slog "Experiment running for ${RUN_DURATION}s..."
  local ELAPSED=0 CONSECUTIVE_API_FAILURES=0 ABORTED=false
  while [ $ELAPSED -lt $RUN_DURATION ]; do
    local SLEEP_CHUNK=$PROGRESS_INTERVAL REMAINING=$((RUN_DURATION - ELAPSED))
    [ $SLEEP_CHUNK -gt $REMAINING ] && SLEEP_CHUNK=$REMAINING
    sleep $SLEEP_CHUNK
    ELAPSED=$((ELAPSED + SLEEP_CHUNK))

    local API_OK=false
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/api/v1/health" 2>/dev/null | grep -q "200" && { API_OK=true; CONSECUTIVE_API_FAILURES=0; } || CONSECUTIVE_API_FAILURES=$((CONSECUTIVE_API_FAILURES + 1))
    RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep -c "ranking" || true)
    slog "[${ELAPSED}s/${RUN_DURATION}s] ${RUNNING} agents, API=$([ "$API_OK" = true ] && echo 'OK' || echo 'DOWN')"
    [ $CONSECUTIVE_API_FAILURES -ge 2 ] && { slog "[ERROR] API down too long — aborting"; ABORTED=true; break; }
  done

  # Capture logs
  slog "Capturing logs..."
  local EXPORT_PATH="$PROJECT_DIR/exports/$RUN_NAME"
  mkdir -p "$EXPORT_PATH"
  $COMPOSE_CMD logs --no-color --tail=5000 api > "$EXPORT_PATH/docker-logs-api.txt" 2>/dev/null || true
  $COMPOSE_CMD logs --no-color --tail=2000 \
    civiclens-ranking-1 civiclens-ranking-2 civiclens-ranking-3 \
    civiclens-ranking-4 civiclens-ranking-5 civiclens-ranking-6 \
    civiclens-ranking-7 civiclens-ranking-8 civiclens-ranking-9 \
    civiclens-ranking-10 > "$EXPORT_PATH/docker-logs-agents.txt" 2>/dev/null || true
  grep -iE "(error|fail|exception|crash|ECONNREFUSED|rate.?limit|429|503)" \
    "$EXPORT_PATH/docker-logs-api.txt" "$EXPORT_PATH/docker-logs-agents.txt" \
    > "$EXPORT_PATH/errors.log" 2>/dev/null || true

  # Export
  slog "Exporting..."
  local EXPORT_OK=true
  (
    export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
    export COMPOSE_OVERLAY="$COMPOSE_OVERLAY"
    export SLOT_ENV_FILE="$SLOT_ENV"
    export HOST_API_PORT="$API_PORT" HOST_PG_PORT="$PG_PORT" HOST_REDIS_PORT="$REDIS_PORT"
    export MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"
    cd "$PROJECT_DIR"
    "$EXPORT_SCRIPT" "$RUN_NAME" 2>>"$SLOT_LOG"
  ) || { slog "[WARN] Export had errors"; EXPORT_OK=false; }

  # Teardown
  slog "Tearing down..."
  worker_cleanup

  local WORKER_ELAPSED=$(( $(date +%s) - WORKER_START ))
  slog "=== DONE: $RUN_NAME in $(( WORKER_ELAPSED / 60 )) minutes ==="

  if [ "$ABORTED" = true ]; then
    [ "$EXPORT_OK" = true ] && echo "ABORTED_WITH_DATA" > "$LOG_DIR/${RUN_NAME}.status" || echo "ABORTED" > "$LOG_DIR/${RUN_NAME}.status"
  elif [ "$EXPORT_OK" = true ]; then
    echo "OK" > "$LOG_DIR/${RUN_NAME}.status"
  else
    echo "EXPORT_FAILED" > "$LOG_DIR/${RUN_NAME}.status"
  fi

  if [ -f "$EXPORT_PATH/metadata.json" ]; then
    local POSTS=$(jq -r '.stats.posts' "$EXPORT_PATH/metadata.json" 2>/dev/null || echo "?")
    local COMMENTS=$(jq -r '.stats.comments' "$EXPORT_PATH/metadata.json" 2>/dev/null || echo "?")
    slog "Stats: ${POSTS} posts, ${COMMENTS} comments"
  fi
}

# ============================================
# Cleanup on interrupt
# ============================================
cleanup() {
  log "[INTERRUPT] Cleaning up..."
  for s in 0 1; do
    local SLOT_ENV="$PROJECT_DIR/.env.slot${s}"
    [ -f "$SLOT_ENV" ] && run_with_timeout 60 docker compose -p "slot${s}" --env-file "$SLOT_ENV" \
      -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_OVERLAY" \
      down -v --remove-orphans 2>/dev/null || true
    rm -f "$SLOT_ENV"
  done
  exit 1
}
trap cleanup INT TERM

# ============================================
# Run f0 + f1 in parallel
# ============================================
log "============================================"
log "Mixed-Model Quick Test: f0 + f1 only"
log "============================================"
log "Models: Grok 4.1 Fast (all 10 agents)"
log "Heartbeat: 60s"
log "Duration: ${RUN_DURATION}s"
log ""

GLOBAL_START=$(date +%s)

slot_worker 0 0 "${PREFIX}-f0-run${RUN_NUMBER}" &
PID0=$!
slot_worker 1 1 "${PREFIX}-f1-run${RUN_NUMBER}" &
PID1=$!

wait $PID0 2>/dev/null || true
wait $PID1 2>/dev/null || true

GLOBAL_END=$(date +%s)
GLOBAL_ELAPSED=$((GLOBAL_END - GLOBAL_START))
trap - INT TERM

log ""
log "============================================"
log "DONE"
log "============================================"
log "Total time: $(( GLOBAL_ELAPSED / 3600 ))h $(( (GLOBAL_ELAPSED % 3600) / 60 ))m"
for N in 0 1; do
  RUN_NAME="${PREFIX}-f${N}-run${RUN_NUMBER}"
  STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status" 2>/dev/null || echo "MISSING")
  if [ -d "$PROJECT_DIR/exports/$RUN_NAME" ]; then
    POSTS=$(jq -r '.stats.posts // "?"' "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    COMMENTS=$(jq -r '.stats.comments // "?"' "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    log "  $RUN_NAME (${N}F+$((25-N))C)  [$STATUS]  ${POSTS} posts, ${COMMENTS} comments"
  else
    log "  $RUN_NAME  [$STATUS]  (no export)"
  fi
done
