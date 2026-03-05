#!/usr/bin/env bash
# ============================================
# Factcheck Dose-Response Experiment Runner
# ============================================
#
# Runs 6 factcheck experiments in 3 batches of 2 parallel slots:
#   Batch 1: fc-f0-run01 (0F+25C) + fc-f1-run01 (1F+24C)
#   Batch 2: fc-f2-run01 (2F+23C) + fc-f3-run01 (3F+22C)
#   Batch 3: fc-f4-run01 (4F+21C) + fc-f5-run01 (5F+20C)
#
# All runs: Mode C (no nudges), GPT-5, 1 hour, 25 posts at 120s intervals.
#
# Usage:
#   ./scripts/run-factcheck-experiments.sh [--duration <secs>] [--dry-run]
#
# Default duration: 3600s (1 hour) per batch

set -euo pipefail

# ============================================
# Portable timeout (macOS lacks GNU timeout)
# ============================================
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

# ============================================
# Configuration
# ============================================
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE_BASE="docker-compose.parallel.yml"
COMPOSE_CONSPIRACY="docker-compose.civiclens-conspiracy-parallel.yml"
EXPORT_SCRIPT="$PROJECT_DIR/scripts/export-experiment-parallel.sh"
BASE_ENV="$PROJECT_DIR/.env.factcheck-base"

RUN_DURATION=3600  # 1 hour
DRY_RUN=false
STARTUP_WAIT=30
PROGRESS_INTERVAL=900  # 15 minutes
RUN_NUMBER="01"  # default; override with --run 02, --run 03, etc.

# Port allocation: slot 0 and slot 1
API_PORT_BASE=4000
PG_PORT_BASE=5432
REDIS_PORT_BASE=6379
PORT_STEP=10

LOG_DIR="$PROJECT_DIR/experiments/factcheck/parallel-logs"

# ============================================
# Parse Arguments
# ============================================
while [[ $# -gt 0 ]]; do
  case $1 in
    --duration)
      RUN_DURATION="$2"
      shift 2
      ;;
    --run)
      RUN_NUMBER=$(printf "%02d" "$2")
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--duration secs] [--run N] [--dry-run]"
      exit 1
      ;;
  esac
done

# ============================================
# Build batch definitions (after --run is parsed)
# ============================================
declare -a BATCH1=("0 fc-f0-run${RUN_NUMBER}" "1 fc-f1-run${RUN_NUMBER}")
declare -a BATCH2=("2 fc-f2-run${RUN_NUMBER}" "3 fc-f3-run${RUN_NUMBER}")
declare -a BATCH3=("4 fc-f4-run${RUN_NUMBER}" "5 fc-f5-run${RUN_NUMBER}")

# ============================================
# Logging
# ============================================
mkdir -p "$LOG_DIR"
SUMMARY_LOG="$LOG_DIR/summary.log"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$SUMMARY_LOG"
}

# ============================================
# Display Schedule
# ============================================
log "============================================"
log "Factcheck Dose-Response Experiment Runner"
log "============================================"
log "Duration:  ${RUN_DURATION}s ($(( RUN_DURATION / 3600 ))h $(( (RUN_DURATION % 3600) / 60 ))m) per batch"
log "Batches:   3 (2 parallel slots each)"
log "Total:     6 experiments, ~$(( RUN_DURATION * 3 / 3600 ))h estimated"
log "Mode:      C (no ranking nudges)"
log "Run:       ${RUN_NUMBER}"
log ""
log "Schedule:"
log "  Batch 1: fc-f0-run${RUN_NUMBER} (0F+25C) + fc-f1-run${RUN_NUMBER} (1F+24C)"
log "  Batch 2: fc-f2-run${RUN_NUMBER} (2F+23C) + fc-f3-run${RUN_NUMBER} (3F+22C)"
log "  Batch 3: fc-f4-run${RUN_NUMBER} (4F+21C) + fc-f5-run${RUN_NUMBER} (5F+20C)"
log ""

if [ "$DRY_RUN" = true ]; then
  log "[DRY RUN] Would execute 6 experiments in 3 batches."
  exit 0
fi

# ============================================
# Verify prerequisites
# ============================================
if [ ! -f "$BASE_ENV" ]; then
  log "[ERROR] Missing $BASE_ENV"
  exit 1
fi

for N in 0 1 2 3 4 5; do
  WP="$PROJECT_DIR/experiments/factcheck/world-posts-f${N}.jsonl"
  if [ ! -f "$WP" ]; then
    log "[ERROR] Missing $WP — run the factcheck pipeline first"
    exit 1
  fi
done

if [ ! -f "$EXPORT_SCRIPT" ]; then
  log "[ERROR] Missing $EXPORT_SCRIPT"
  exit 1
fi

# ============================================
# Slot Worker Function
# ============================================
slot_worker() {
  set +e

  local SLOT=$1
  local N_FACTUAL=$2
  local RUN_NAME=$3
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
  local WORKER_START
  WORKER_START=$(date +%s)

  # Clean slate
  slog "Tearing down any previous state..."
  run_with_timeout 120 $COMPOSE_CMD down -v --remove-orphans 2>>"$SLOT_LOG" || true

  # Generate per-slot .env from base template
  local SLOT_ENV="$PROJECT_DIR/.env.slot${SLOT}"
  cp "$BASE_ENV" "$SLOT_ENV"
  if [ $? -ne 0 ]; then
    slog "[ERROR] Failed to copy .env.factcheck-base"
    echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"
    return 1
  fi

  # Substitute experiment-specific values
  echo "" >> "$SLOT_ENV"
  echo "# Per-slot overrides (auto-generated)" >> "$SLOT_ENV"
  echo "EXPERIMENT_NAME=$RUN_NAME" >> "$SLOT_ENV"
  echo "WORLD_POSTS_FILE=/app/experiments/factcheck/world-posts-f${N_FACTUAL}.jsonl" >> "$SLOT_ENV"

  # Add port variables
  echo "HOST_API_PORT=$API_PORT" >> "$SLOT_ENV"
  echo "HOST_PG_PORT=$PG_PORT" >> "$SLOT_ENV"
  echo "HOST_REDIS_PORT=$REDIS_PORT" >> "$SLOT_ENV"

  export HOST_API_PORT=$API_PORT
  export HOST_PG_PORT=$PG_PORT
  export HOST_REDIS_PORT=$REDIS_PORT

  COMPOSE_CMD="docker compose -p $PROJECT_NAME --env-file $SLOT_ENV -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_CONSPIRACY"

  # Start infrastructure
  slog "Starting postgres + redis..."
  if ! $COMPOSE_CMD up -d postgres redis 2>>"$SLOT_LOG"; then
    slog "[ERROR] Failed to start postgres/redis"
    echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"
    worker_cleanup
    return 1
  fi
  sleep 15

  # Start API
  slog "Starting API..."
  if ! $COMPOSE_CMD up -d api 2>>"$SLOT_LOG"; then
    slog "[ERROR] Failed to start API"
    echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"
    worker_cleanup
    return 1
  fi

  # Wait for API health
  slog "Waiting for API on port $API_PORT..."
  local API_READY=false
  for attempt in $(seq 1 30); do
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/api/v1/health" 2>/dev/null | grep -q "200"; then
      API_READY=true
      break
    fi
    sleep 3
  done

  if [ "$API_READY" = false ]; then
    slog "[ERROR] API failed to start on port $API_PORT after 90s"
    $COMPOSE_CMD logs api 2>>"$SLOT_LOG" | tail -30 >> "$SLOT_LOG"
    echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"
    worker_cleanup
    return 1
  fi
  slog "API healthy"

  # Start agents
  slog "Starting 10 agents..."
  if ! $COMPOSE_CMD up --build -d \
    civiclens-ranking-1 civiclens-ranking-2 civiclens-ranking-3 \
    civiclens-ranking-4 civiclens-ranking-5 civiclens-ranking-6 \
    civiclens-ranking-7 civiclens-ranking-8 civiclens-ranking-9 \
    civiclens-ranking-10 2>>"$SLOT_LOG"; then
    slog "[WARN] Some agents failed to start, continuing with partial set"
  fi

  sleep "$STARTUP_WAIT"

  local RUNNING
  RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep -c "ranking" || true)
  slog "$RUNNING agent containers running"

  # Run experiment with watchdog
  slog "Experiment running for ${RUN_DURATION}s..."
  local ELAPSED=0
  local CONSECUTIVE_API_FAILURES=0
  local ABORTED=false

  while [ $ELAPSED -lt $RUN_DURATION ]; do
    local SLEEP_CHUNK=$PROGRESS_INTERVAL
    local REMAINING=$((RUN_DURATION - ELAPSED))
    if [ $SLEEP_CHUNK -gt $REMAINING ]; then
      SLEEP_CHUNK=$REMAINING
    fi
    sleep $SLEEP_CHUNK
    ELAPSED=$((ELAPSED + SLEEP_CHUNK))

    # Watchdog: API health
    local API_OK=false
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/api/v1/health" 2>/dev/null | grep -q "200"; then
      API_OK=true
      CONSECUTIVE_API_FAILURES=0
    else
      CONSECUTIVE_API_FAILURES=$((CONSECUTIVE_API_FAILURES + 1))
      slog "[WARN] API health check failed (consecutive: $CONSECUTIVE_API_FAILURES)"
    fi

    RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep -c "ranking" || true)

    # Query treatment count
    local TREATMENTS
    TREATMENTS=$(docker compose -p "$PROJECT_NAME" --env-file "$SLOT_ENV" \
      -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_CONSPIRACY" \
      exec -T postgres psql -U moltbook -t -c \
      "SELECT COUNT(*) FROM experiment_treatments WHERE experiment_name = '$RUN_NAME'" \
      2>/dev/null | tr -d ' \n' || echo "0")
    TREATMENTS="${TREATMENTS:-0}"

    slog "[${ELAPSED}s/${RUN_DURATION}s] ${RUNNING} agents, ${TREATMENTS} treatments, API=$([ "$API_OK" = true ] && echo 'OK' || echo 'DOWN')"

    if [ $CONSECUTIVE_API_FAILURES -ge 2 ]; then
      slog "[ERROR] API down for $((CONSECUTIVE_API_FAILURES * PROGRESS_INTERVAL / 60))m — aborting run"
      ABORTED=true
      break
    fi
  done

  # Capture docker logs
  slog "Capturing container logs..."
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

  if [ "$ABORTED" = true ]; then
    slog "[ERROR] Run aborted early at ${ELAPSED}s/${RUN_DURATION}s"
    echo "ABORTED" > "$LOG_DIR/${RUN_NAME}.status"
  fi

  # Export
  slog "Exporting..."
  local EXPORT_OK=true
  (
    export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
    export COMPOSE_OVERLAY="$COMPOSE_CONSPIRACY"
    export SLOT_ENV_FILE="$SLOT_ENV"
    export HOST_API_PORT="$API_PORT"
    export HOST_PG_PORT="$PG_PORT"
    export HOST_REDIS_PORT="$REDIS_PORT"
    export MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"
    cd "$PROJECT_DIR"
    "$EXPORT_SCRIPT" "$RUN_NAME" 2>>"$SLOT_LOG"
  ) || { slog "[WARN] Export had errors"; EXPORT_OK=false; }

  # Teardown
  slog "Tearing down..."
  worker_cleanup

  local WORKER_END
  WORKER_END=$(date +%s)
  local WORKER_ELAPSED=$((WORKER_END - WORKER_START))
  slog "=== DONE: $RUN_NAME in $(( WORKER_ELAPSED / 60 )) minutes ==="

  if [ "$ABORTED" = true ]; then
    if [ "$EXPORT_OK" = true ]; then
      echo "ABORTED_WITH_DATA" > "$LOG_DIR/${RUN_NAME}.status"
    fi
  elif [ "$EXPORT_OK" = true ]; then
    echo "OK" > "$LOG_DIR/${RUN_NAME}.status"
  else
    echo "EXPORT_FAILED" > "$LOG_DIR/${RUN_NAME}.status"
  fi

  # Quick stats
  if [ -f "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" ]; then
    local POSTS COMMENTS
    POSTS=$(jq -r '.stats.posts' "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    COMMENTS=$(jq -r '.stats.comments' "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    slog "Stats: ${POSTS} posts, ${COMMENTS} comments"
  fi
}

# ============================================
# Cleanup on interrupt
# ============================================
cleanup() {
  log ""
  log "[INTERRUPT] Cleaning up all slots..."
  for s in 0 1; do
    local PROJECT_NAME="slot${s}"
    local SLOT_ENV="$PROJECT_DIR/.env.slot${s}"
    if [ -f "$SLOT_ENV" ]; then
      log "  Stopping slot $s..."
      run_with_timeout 60 docker compose -p "$PROJECT_NAME" --env-file "$SLOT_ENV" \
        -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_CONSPIRACY" \
        down -v --remove-orphans 2>/dev/null || \
      run_with_timeout 30 docker compose -p "$PROJECT_NAME" --env-file "$SLOT_ENV" \
        -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_CONSPIRACY" \
        kill 2>/dev/null || true
      rm -f "$SLOT_ENV"
    fi
  done
  log "Cleanup complete."
  exit 1
}

trap cleanup INT TERM

# ============================================
# Run a batch (2 parallel slots)
# ============================================
run_batch() {
  local BATCH_NUM=$1
  shift
  local ENTRIES=("$@")

  log "============================================"
  log "BATCH $BATCH_NUM / 3"
  log "============================================"

  local PIDS=()
  local NAMES=()

  for i in "${!ENTRIES[@]}"; do
    local ENTRY="${ENTRIES[$i]}"
    local N_FACTUAL=$(echo "$ENTRY" | cut -d' ' -f1)
    local RUN_NAME=$(echo "$ENTRY" | cut -d' ' -f2)

    log "[SLOT $i] Starting $RUN_NAME (${N_FACTUAL}F + $((25 - N_FACTUAL))C)"
    slot_worker "$i" "$N_FACTUAL" "$RUN_NAME" &
    PIDS+=($!)
    NAMES+=("$RUN_NAME")
  done

  # Wait for both slots to finish
  for i in "${!PIDS[@]}"; do
    wait "${PIDS[$i]}" 2>/dev/null || true
    local RUN_NAME="${NAMES[$i]}"
    local STATUS="UNKNOWN"
    if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
      STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status")
    fi
    log "[SLOT $i] $RUN_NAME finished: $STATUS"
  done

  log "Batch $BATCH_NUM complete."
  log ""
}

# ============================================
# Main
# ============================================
GLOBAL_START=$(date +%s)

log "============================================"
log "Starting Factcheck Dose-Response Experiments"
log "============================================"
log ""

run_batch 1 "${BATCH1[@]}"
run_batch 2 "${BATCH2[@]}"
run_batch 3 "${BATCH3[@]}"

# ============================================
# Final Summary
# ============================================
GLOBAL_END=$(date +%s)
GLOBAL_ELAPSED=$((GLOBAL_END - GLOBAL_START))

trap - INT TERM

log ""
log "============================================"
log "ALL FACTCHECK EXPERIMENTS COMPLETE"
log "============================================"
log "Total time: $(( GLOBAL_ELAPSED / 3600 ))h $(( (GLOBAL_ELAPSED % 3600) / 60 ))m"
log ""
log "Results:"

for N in 0 1 2 3 4 5; do
  RUN_NAME="fc-f${N}-run${RUN_NUMBER}"
  STATUS="MISSING"
  if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
    STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status")
  fi
  if [ -d "$PROJECT_DIR/exports/$RUN_NAME" ]; then
    SIZE=$(du -sh "$PROJECT_DIR/exports/$RUN_NAME" 2>/dev/null | cut -f1)
    POSTS=$(jq -r '.stats.posts // "?"' "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    log "  $RUN_NAME (${N}F+$((25-N))C)  [$STATUS]  ${POSTS} posts  ($SIZE)"
  else
    log "  $RUN_NAME (${N}F+$((25-N))C)  [$STATUS]  (no export dir)"
  fi
done

log ""
log "Logs: $LOG_DIR/"
log "Exports: $PROJECT_DIR/exports/"
log ""
log "Next step: python3 experiments/factcheck/analyze_threshold.py"
