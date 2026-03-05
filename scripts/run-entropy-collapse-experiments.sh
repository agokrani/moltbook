#!/usr/bin/env bash
# ============================================
# Entropy Collapse Experiment Runner
# ============================================
#
# Runs 7 conditions × N replications for the entropy collapse thesis:
#   E-MAG-0     — empty feed (true control)
#   E-MAG-1     — 1 conspiracy post
#   E-MAG-5     — 5 conspiracy posts
#   E-MAG-25    — 25 conspiracy posts (standard baseline)
#   E-DOM-AGI   — 25 AGI hype posts
#   E-DOM-TECH  — 25 tech news posts
#   E-HET-DUAL  — 12 conspiracy + 13 AGI (interleaved)
#   E-HET-MULTI — 8 conspiracy + 8 AGI + 9 tech (interleaved)
#
# All runs: Mode C (no nudges), GPT-5, 60s heartbeat, 10 agents, 1h.
# 2 parallel slots per batch. Pairs across conditions for early data.
#
# Usage:
#   ./scripts/run-entropy-collapse-experiments.sh [OPTIONS]
#     --duration <secs>    Duration per run (default: 3600 = 1h)
#     --runs <N>           Replications per condition (default: 3)
#     --start <N>          Starting run number (default: 1)
#     --conditions <list>  Comma-separated conditions to run (default: all)
#                          Options: mag0,mag1,mag5,mag25,dom-agi,dom-tech,het-dual,het-multi
#     --dry-run            Print schedule without executing

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
BASE_ENV="$PROJECT_DIR/.env.entropy-base"

RUN_DURATION=3600  # 1 hour
DRY_RUN=false
STARTUP_WAIT=30
PROGRESS_INTERVAL=900  # 15 minutes
NUM_RUNS=3
START_RUN=1
SELECTED_CONDITIONS=""

# Port allocation: slot 0 and slot 1
API_PORT_BASE=4000
PG_PORT_BASE=5432
REDIS_PORT_BASE=6379
PORT_STEP=10

LOG_DIR="$PROJECT_DIR/experiments/entropy-collapse/parallel-logs"

# ============================================
# Condition lookups (bash 3.2 compatible)
# ============================================
condition_file() {
  case "$1" in
    mag0)      echo "world-posts-empty.jsonl" ;;
    mag1)      echo "world-posts-mag1.jsonl" ;;
    mag5)      echo "world-posts-mag5.jsonl" ;;
    mag25)     echo "world-posts-mag25.jsonl" ;;
    dom-agi)   echo "world-posts-agi.jsonl" ;;
    dom-tech)  echo "world-posts-tech.jsonl" ;;
    het-dual)  echo "world-posts-het-dual.jsonl" ;;
    het-multi) echo "world-posts-het-multi.jsonl" ;;
    *)         echo "" ;;
  esac
}

condition_desc() {
  case "$1" in
    mag0)      echo "0 posts (empty feed)" ;;
    mag1)      echo "1 conspiracy post" ;;
    mag5)      echo "5 conspiracy posts" ;;
    mag25)     echo "25 conspiracy posts (baseline)" ;;
    dom-agi)   echo "25 AGI hype posts" ;;
    dom-tech)  echo "25 tech news posts" ;;
    het-dual)  echo "12 conspiracy + 13 AGI" ;;
    het-multi) echo "8 conspiracy + 8 AGI + 9 tech" ;;
    *)         echo "unknown" ;;
  esac
}

# Default order (priority-based: P1 first, then P2, P3, P4)
ALL_CONDITIONS="mag0 mag1 mag5 mag25 dom-agi dom-tech het-dual het-multi"

# ============================================
# Parse Arguments
# ============================================
while [[ $# -gt 0 ]]; do
  case $1 in
    --duration)
      RUN_DURATION="$2"
      shift 2
      ;;
    --runs)
      NUM_RUNS="$2"
      shift 2
      ;;
    --start)
      START_RUN="$2"
      shift 2
      ;;
    --conditions)
      SELECTED_CONDITIONS="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--duration secs] [--runs N] [--start N] [--conditions list] [--dry-run]"
      echo "  --conditions: comma-separated from: mag0,mag1,mag5,dom-agi,dom-tech,het-dual,het-multi"
      exit 1
      ;;
  esac
done

# ============================================
# Resolve conditions
# ============================================
if [ -n "$SELECTED_CONDITIONS" ]; then
  # Convert commas to spaces
  CONDITIONS=$(echo "$SELECTED_CONDITIONS" | tr ',' ' ')
  # Validate each condition
  for c in $CONDITIONS; do
    if [ -z "$(condition_file "$c")" ]; then
      echo "[ERROR] Unknown condition: $c"
      echo "Valid conditions: $ALL_CONDITIONS"
      exit 1
    fi
  done
else
  CONDITIONS="$ALL_CONDITIONS"
fi

# Count conditions
NUM_CONDITIONS=0
for c in $CONDITIONS; do
  NUM_CONDITIONS=$((NUM_CONDITIONS + 1))
done

# ============================================
# Build experiment schedule
# ============================================
# Strategy: iterate run numbers first across conditions for early data diversity.
# For each run number, schedule all selected conditions, then move to next run.
# Each entry: "CONDITION RUN_NAME"
EXPERIMENTS=()

for run_num in $(seq "$START_RUN" $((START_RUN + NUM_RUNS - 1))); do
  RN=$(printf "%02d" "$run_num")
  for cond in $CONDITIONS; do
    EXPERIMENTS+=("$cond ec-${cond}-run${RN}")
  done
done

TOTAL_EXPERIMENTS=${#EXPERIMENTS[@]}
TOTAL_BATCHES=$(( (TOTAL_EXPERIMENTS + 1) / 2 ))

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
log "Entropy Collapse Experiment Runner"
log "============================================"
log "Duration:    ${RUN_DURATION}s ($(( RUN_DURATION / 3600 ))h $(( (RUN_DURATION % 3600) / 60 ))m) per run"
log "Conditions:  ${NUM_CONDITIONS} ($CONDITIONS)"
log "Runs:        ${NUM_RUNS} (starting from run ${START_RUN})"
log "Total:       ${TOTAL_EXPERIMENTS} experiments in ${TOTAL_BATCHES} batches"
log "Estimated:   ~$(( RUN_DURATION * TOTAL_BATCHES / 3600 ))h"
log "Mode:        C (no ranking nudges)"
log ""
log "Schedule:"

batch_num=0
for (( i=0; i<TOTAL_EXPERIMENTS; i+=2 )); do
  batch_num=$((batch_num + 1))
  COND1=$(echo "${EXPERIMENTS[$i]}" | cut -d' ' -f1)
  NAME1=$(echo "${EXPERIMENTS[$i]}" | cut -d' ' -f2)
  if [ $((i + 1)) -lt $TOTAL_EXPERIMENTS ]; then
    COND2=$(echo "${EXPERIMENTS[$((i+1))]}" | cut -d' ' -f1)
    NAME2=$(echo "${EXPERIMENTS[$((i+1))]}" | cut -d' ' -f2)
    log "  Batch ${batch_num}: ${NAME1} ($(condition_desc "$COND1")) + ${NAME2} ($(condition_desc "$COND2"))"
  else
    log "  Batch ${batch_num}: ${NAME1} ($(condition_desc "$COND1")) [single slot]"
  fi
done

log ""

if [ "$DRY_RUN" = true ]; then
  log "[DRY RUN] Would execute ${TOTAL_EXPERIMENTS} experiments in ${TOTAL_BATCHES} batches."
  log ""
  log "Condition → World Posts File:"
  for cond in $CONDITIONS; do
    log "  ${cond} → experiments/entropy-collapse/$(condition_file "$cond")"
  done
  exit 0
fi

# ============================================
# Verify prerequisites
# ============================================
if [ ! -f "$BASE_ENV" ]; then
  log "[ERROR] Missing $BASE_ENV"
  exit 1
fi

for cond in $CONDITIONS; do
  WP="$PROJECT_DIR/experiments/entropy-collapse/$(condition_file "$cond")"
  if [ ! -f "$WP" ]; then
    log "[ERROR] Missing $WP — run generate-world-posts.py first"
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
  local CONDITION=$2
  local RUN_NAME=$3
  local SLOT_LOG="$LOG_DIR/${RUN_NAME}.log"
  local COND_DESC
  COND_DESC="$(condition_desc "$CONDITION")"
  local COND_FILE
  COND_FILE="$(condition_file "$CONDITION")"

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

  slog "=== START: $RUN_NAME (slot $SLOT, $COND_DESC) ==="
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
    slog "[ERROR] Failed to copy .env.entropy-base"
    echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"
    return 1
  fi

  # Substitute experiment-specific values
  echo "" >> "$SLOT_ENV"
  echo "# Per-slot overrides (auto-generated)" >> "$SLOT_ENV"
  echo "EXPERIMENT_NAME=$RUN_NAME" >> "$SLOT_ENV"
  echo "WORLD_POSTS_FILE=/app/experiments/entropy-collapse/${COND_FILE}" >> "$SLOT_ENV"

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
# Run batches (2 parallel slots each)
# ============================================
GLOBAL_START=$(date +%s)

log "============================================"
log "Starting Entropy Collapse Experiments"
log "============================================"
log ""

batch_num=0
for (( i=0; i<TOTAL_EXPERIMENTS; i+=2 )); do
  batch_num=$((batch_num + 1))

  log "============================================"
  log "BATCH $batch_num / $TOTAL_BATCHES"
  log "============================================"

  local_pids=()
  local_names=()

  # Slot 0
  COND1=$(echo "${EXPERIMENTS[$i]}" | cut -d' ' -f1)
  NAME1=$(echo "${EXPERIMENTS[$i]}" | cut -d' ' -f2)
  log "[SLOT 0] Starting $NAME1 ($(condition_desc "$COND1"))"
  slot_worker 0 "$COND1" "$NAME1" &
  local_pids+=($!)
  local_names+=("$NAME1")

  # Slot 1 (if available)
  if [ $((i + 1)) -lt $TOTAL_EXPERIMENTS ]; then
    COND2=$(echo "${EXPERIMENTS[$((i+1))]}" | cut -d' ' -f1)
    NAME2=$(echo "${EXPERIMENTS[$((i+1))]}" | cut -d' ' -f2)
    log "[SLOT 1] Starting $NAME2 ($(condition_desc "$COND2"))"
    slot_worker 1 "$COND2" "$NAME2" &
    local_pids+=($!)
    local_names+=("$NAME2")
  fi

  # Wait for batch to complete
  for j in "${!local_pids[@]}"; do
    wait "${local_pids[$j]}" 2>/dev/null || true
    RUN_NAME="${local_names[$j]}"
    STATUS="UNKNOWN"
    if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
      STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status")
    fi
    log "[SLOT $j] $RUN_NAME finished: $STATUS"
  done

  log "Batch $batch_num complete."
  log ""
done

# ============================================
# Final Summary
# ============================================
GLOBAL_END=$(date +%s)
GLOBAL_ELAPSED=$((GLOBAL_END - GLOBAL_START))

trap - INT TERM

log ""
log "============================================"
log "ALL ENTROPY COLLAPSE EXPERIMENTS COMPLETE"
log "============================================"
log "Total time: $(( GLOBAL_ELAPSED / 3600 ))h $(( (GLOBAL_ELAPSED % 3600) / 60 ))m"
log ""
log "Results:"

for (( i=0; i<TOTAL_EXPERIMENTS; i++ )); do
  RUN_NAME=$(echo "${EXPERIMENTS[$i]}" | cut -d' ' -f2)
  COND=$(echo "${EXPERIMENTS[$i]}" | cut -d' ' -f1)
  STATUS="MISSING"
  if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
    STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status")
  fi
  if [ -d "$PROJECT_DIR/exports/$RUN_NAME" ]; then
    SIZE=$(du -sh "$PROJECT_DIR/exports/$RUN_NAME" 2>/dev/null | cut -f1)
    POSTS=$(jq -r '.stats.posts // "?"' "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    log "  $RUN_NAME ($(condition_desc "$COND"))  [$STATUS]  ${POSTS} posts  ($SIZE)"
  else
    log "  $RUN_NAME ($(condition_desc "$COND"))  [$STATUS]  (no export dir)"
  fi
done

log ""
log "Logs: $LOG_DIR/"
log "Exports: $PROJECT_DIR/exports/"
