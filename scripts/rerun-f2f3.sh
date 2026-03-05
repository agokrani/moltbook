#!/usr/bin/env bash
# Re-run only fc-f2-run01 and fc-f3-run01
# Uses the main runner's logic but only runs batch 2 (the f2+f3 pair)
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Cleaning old exports..."
rm -rf "$PROJECT_DIR/exports/fc-f2-run01" "$PROJECT_DIR/exports/fc-f3-run01"
rm -f "$PROJECT_DIR/experiments/factcheck/parallel-logs/fc-f2-run01.status"
rm -f "$PROJECT_DIR/experiments/factcheck/parallel-logs/fc-f3-run01.status"

# Clean zombie containers
for s in 0 1; do
  docker compose -p "slot${s}" -f "$PROJECT_DIR/docker-compose.parallel.yml" \
    -f "$PROJECT_DIR/docker-compose.civiclens-conspiracy-parallel.yml" \
    down -v --remove-orphans 2>/dev/null || true
done

echo "Starting re-run of f2 + f3..."

# Source the main runner but only execute batch with f2 and f3
# We achieve this by exporting overrides and calling the full script
# Actually, simplest: just use the main script infrastructure directly

COMPOSE_BASE="docker-compose.parallel.yml"
COMPOSE_CONSPIRACY="docker-compose.civiclens-conspiracy-parallel.yml"
EXPORT_SCRIPT="$PROJECT_DIR/scripts/export-experiment-parallel.sh"
BASE_ENV="$PROJECT_DIR/.env.factcheck-base"

RUN_DURATION=3600
STARTUP_WAIT=30
PROGRESS_INTERVAL=900
LOG_DIR="$PROJECT_DIR/experiments/factcheck/parallel-logs"
API_PORT_BASE=4000
PG_PORT_BASE=5432
REDIS_PORT_BASE=6379
PORT_STEP=10

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

mkdir -p "$LOG_DIR"
SUMMARY_LOG="$LOG_DIR/summary.log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$SUMMARY_LOG"
}

slot_worker() {
  set +e
  local SLOT=$1 N_FACTUAL=$2 RUN_NAME=$3
  local SLOT_LOG="$LOG_DIR/${RUN_NAME}.log"
  local API_PORT=$((API_PORT_BASE + SLOT * PORT_STEP))
  local PG_PORT=$((PG_PORT_BASE + SLOT * PORT_STEP))
  local REDIS_PORT=$((REDIS_PORT_BASE + SLOT * PORT_STEP))
  local PROJECT_NAME="slot${SLOT}"
  local COMPOSE_CMD="docker compose -p $PROJECT_NAME -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_CONSPIRACY"

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
  slog "Ports: API=$API_PORT PG=$PG_PORT Redis=$REDIS_PORT"
  local WORKER_START=$(date +%s)

  run_with_timeout 120 $COMPOSE_CMD down -v --remove-orphans 2>>"$SLOT_LOG" || true

  local SLOT_ENV="$PROJECT_DIR/.env.slot${SLOT}"
  cp "$BASE_ENV" "$SLOT_ENV"
  echo "" >> "$SLOT_ENV"
  echo "EXPERIMENT_NAME=$RUN_NAME" >> "$SLOT_ENV"
  echo "WORLD_POSTS_FILE=/app/experiments/factcheck/world-posts-f${N_FACTUAL}.jsonl" >> "$SLOT_ENV"
  echo "HOST_API_PORT=$API_PORT" >> "$SLOT_ENV"
  echo "HOST_PG_PORT=$PG_PORT" >> "$SLOT_ENV"
  echo "HOST_REDIS_PORT=$REDIS_PORT" >> "$SLOT_ENV"

  export HOST_API_PORT=$API_PORT HOST_PG_PORT=$PG_PORT HOST_REDIS_PORT=$REDIS_PORT
  COMPOSE_CMD="docker compose -p $PROJECT_NAME --env-file $SLOT_ENV -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_CONSPIRACY"

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

  slog "Starting 10 agents..."
  $COMPOSE_CMD up --build -d \
    civiclens-ranking-1 civiclens-ranking-2 civiclens-ranking-3 \
    civiclens-ranking-4 civiclens-ranking-5 civiclens-ranking-6 \
    civiclens-ranking-7 civiclens-ranking-8 civiclens-ranking-9 \
    civiclens-ranking-10 2>>"$SLOT_LOG" || slog "[WARN] Some agents failed"
  sleep "$STARTUP_WAIT"

  local RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep -c "ranking" || true)
  slog "$RUNNING agent containers running"

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

  slog "Capturing logs..."
  local EXPORT_PATH="$PROJECT_DIR/exports/$RUN_NAME"
  mkdir -p "$EXPORT_PATH"
  $COMPOSE_CMD logs --no-color --tail=5000 api > "$EXPORT_PATH/docker-logs-api.txt" 2>/dev/null || true
  $COMPOSE_CMD logs --no-color --tail=2000 \
    civiclens-ranking-{1,2,3,4,5,6,7,8,9,10} > "$EXPORT_PATH/docker-logs-agents.txt" 2>/dev/null || true

  slog "Exporting..."
  local EXPORT_OK=true
  (
    export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
    export COMPOSE_OVERLAY="$COMPOSE_CONSPIRACY"
    export SLOT_ENV_FILE="$SLOT_ENV"
    export HOST_API_PORT="$API_PORT" HOST_PG_PORT="$PG_PORT" HOST_REDIS_PORT="$REDIS_PORT"
    export MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"
    cd "$PROJECT_DIR"
    "$EXPORT_SCRIPT" "$RUN_NAME" 2>>"$SLOT_LOG"
  ) || { slog "[WARN] Export had errors"; EXPORT_OK=false; }

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

cleanup() {
  log "[INTERRUPT] Cleaning up..."
  for s in 0 1; do
    local SLOT_ENV="$PROJECT_DIR/.env.slot${s}"
    [ -f "$SLOT_ENV" ] && run_with_timeout 60 docker compose -p "slot${s}" --env-file "$SLOT_ENV" \
      -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_CONSPIRACY" \
      down -v --remove-orphans 2>/dev/null || true
    rm -f "$SLOT_ENV"
  done
  exit 1
}
trap cleanup INT TERM

log "============================================"
log "Re-running fc-f2-run01 + fc-f3-run01"
log "============================================"

PIDS=() NAMES=()
log "[SLOT 0] Starting fc-f2-run01 (2F + 23C)"
slot_worker 0 2 "fc-f2-run01" &
PIDS+=($!) NAMES+=("fc-f2-run01")

log "[SLOT 1] Starting fc-f3-run01 (3F + 22C)"
slot_worker 1 3 "fc-f3-run01" &
PIDS+=($!) NAMES+=("fc-f3-run01")

for i in "${!PIDS[@]}"; do
  wait "${PIDS[$i]}" 2>/dev/null || true
  STATUS=$(cat "$LOG_DIR/${NAMES[$i]}.status" 2>/dev/null || echo "UNKNOWN")
  log "[SLOT $i] ${NAMES[$i]} finished: $STATUS"
done

log ""
log "Re-run complete!"
for N in 2 3; do
  RUN="fc-f${N}-run01"
  STATUS=$(cat "$LOG_DIR/${RUN}.status" 2>/dev/null || echo "MISSING")
  POSTS=$(jq -r '.stats.posts // "?"' "$PROJECT_DIR/exports/$RUN/metadata.json" 2>/dev/null || echo "?")
  log "  $RUN  [$STATUS]  ${POSTS} posts"
done
