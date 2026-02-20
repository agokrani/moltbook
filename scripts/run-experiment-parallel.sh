#!/usr/bin/env bash
# ============================================
# Parallel Experiment Runner
# ============================================
#
# Runs multiple experiment replications in parallel using isolated Docker
# Compose projects. Each slot gets its own DB, Redis, API, and agents with
# no port or volume conflicts.
#
# Usage:
#   ./scripts/run-experiment-parallel.sh [options] <mode> <count> [<mode> <count> ...]
#
# Options:
#   --slots <n>        Number of parallel slots (default: 4)
#   --duration <secs>  Duration per run in seconds (default: 10800 = 3h)
#   --dry-run          Print schedule without executing
#
# Examples:
#   # Full Tier 1 (12 runs, 4 parallel)
#   ./scripts/run-experiment-parallel.sh --slots 4 A 7 B 5
#
#   # Quick test (2 min runs, 2 parallel)
#   ./scripts/run-experiment-parallel.sh --slots 2 --duration 120 A 2 B 1
#
#   # Dry run to see schedule
#   ./scripts/run-experiment-parallel.sh --dry-run --slots 4 A 7 B 5

set -euo pipefail

# ============================================
# Portable timeout (macOS lacks GNU timeout)
# ============================================
if command -v timeout &>/dev/null; then
  TIMEOUT_CMD="timeout"
elif command -v gtimeout &>/dev/null; then
  TIMEOUT_CMD="gtimeout"
else
  # Fallback: run without timeout
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
COMPOSE_RANKING="docker-compose.civiclens-ranking-parallel.yml"
EXPORT_SCRIPT="$PROJECT_DIR/scripts/export-experiment-parallel.sh"

MAX_SLOTS=4
RUN_DURATION=10800  # 3 hours
DRY_RUN=false
STARTUP_WAIT=30
PROGRESS_INTERVAL=900  # 15 minutes
ENV_SUFFIX=""          # e.g. "-gpt5nano" → uses .env.e1a-gpt5nano
RUN_START=1            # starting run number

# Port allocation: slot N gets base + N*10
API_PORT_BASE=4000
PG_PORT_BASE=5432
REDIS_PORT_BASE=6379
PORT_STEP=10

LOG_DIR="$PROJECT_DIR/experiments/ranking-effect/parallel-logs"
SUMMARY_LOG="$LOG_DIR/summary.log"

# ============================================
# Parse Arguments
# ============================================
declare -a RUN_SPECS=()  # Array of "MODE COUNT" pairs

while [[ $# -gt 0 ]]; do
  case $1 in
    --slots)
      MAX_SLOTS="$2"
      shift 2
      ;;
    --duration)
      RUN_DURATION="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --env-suffix)
      ENV_SUFFIX="$2"
      shift 2
      ;;
    --start)
      RUN_START="$2"
      shift 2
      ;;
    A|B)
      MODE="$1"
      COUNT="${2:?Missing count after mode $1}"
      RUN_SPECS+=("$MODE $COUNT")
      shift 2
      ;;
    *)
      echo "Unknown argument: $1"
      echo "Usage: $0 [--slots N] [--duration secs] [--dry-run] A <count> [B <count>]"
      exit 1
      ;;
  esac
done

if [ ${#RUN_SPECS[@]} -eq 0 ]; then
  echo "Usage: $0 [--slots N] [--duration secs] [--dry-run] A <count> [B <count>]"
  echo ""
  echo "Examples:"
  echo "  $0 --slots 4 A 7 B 5        # Full Tier 1"
  echo "  $0 --slots 2 --duration 120 A 2 B 1  # Quick test"
  exit 1
fi

# ============================================
# Build Run Queue (interleaved A/B)
# ============================================
declare -a RUN_QUEUE=()  # Each entry: "MODE RUN_NUM RUN_NAME"

# Collect all runs per mode
declare -a MODE_A_RUNS=()
declare -a MODE_B_RUNS=()

for spec in "${RUN_SPECS[@]}"; do
  MODE=$(echo "$spec" | cut -d' ' -f1)
  COUNT=$(echo "$spec" | cut -d' ' -f2)
  MODE_LOWER=$(echo "$MODE" | tr 'A-Z' 'a-z')

  for i in $(seq "$RUN_START" "$(( RUN_START + COUNT - 1 ))"); do
    RUN_NAME="e1${MODE_LOWER}-run$(printf '%02d' $i)"
    if [ "$MODE" = "A" ]; then
      MODE_A_RUNS+=("A $i $RUN_NAME")
    else
      MODE_B_RUNS+=("B $i $RUN_NAME")
    fi
  done
done

# Interleave: take from A and B alternately so both produce data early
A_IDX=0
B_IDX=0
while [ $A_IDX -lt ${#MODE_A_RUNS[@]} ] || [ $B_IDX -lt ${#MODE_B_RUNS[@]} ]; do
  if [ $A_IDX -lt ${#MODE_A_RUNS[@]} ]; then
    RUN_QUEUE+=("${MODE_A_RUNS[$A_IDX]}")
    A_IDX=$((A_IDX + 1))
  fi
  if [ $B_IDX -lt ${#MODE_B_RUNS[@]} ]; then
    RUN_QUEUE+=("${MODE_B_RUNS[$B_IDX]}")
    B_IDX=$((B_IDX + 1))
  fi
done

TOTAL_RUNS=${#RUN_QUEUE[@]}

# ============================================
# Logging
# ============================================
mkdir -p "$LOG_DIR"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
  echo "$msg"
  echo "$msg" >> "$SUMMARY_LOG"
}

# ============================================
# Display Schedule
# ============================================
log "============================================"
log "Parallel Experiment Runner"
log "============================================"
log "Slots:     $MAX_SLOTS"
log "Duration:  ${RUN_DURATION}s ($(( RUN_DURATION / 3600 ))h $(( (RUN_DURATION % 3600) / 60 ))m)"
log "Total:     $TOTAL_RUNS runs"
log "Log dir:   $LOG_DIR"
log ""
log "Run queue (interleaved):"
for i in "${!RUN_QUEUE[@]}"; do
  entry="${RUN_QUEUE[$i]}"
  MODE=$(echo "$entry" | cut -d' ' -f1)
  RUN_NAME=$(echo "$entry" | cut -d' ' -f3)
  log "  [$((i+1))/$TOTAL_RUNS] $RUN_NAME (Mode $MODE)"
done
log ""

# Port table
log "Port allocation:"
log "  Slot | API Port | PG Port | Redis Port"
log "  -----|----------|---------|----------"
for s in $(seq 0 $((MAX_SLOTS - 1))); do
  API_P=$((API_PORT_BASE + s * PORT_STEP))
  PG_P=$((PG_PORT_BASE + s * PORT_STEP))
  REDIS_P=$((REDIS_PORT_BASE + s * PORT_STEP))
  log "  $s    | $API_P    | $PG_P   | $REDIS_P"
done
log ""

if [ "$DRY_RUN" = true ]; then
  log "[DRY RUN] Would execute $TOTAL_RUNS runs across $MAX_SLOTS slots."
  exit 0
fi

# ============================================
# Verify prerequisites
# ============================================
for ENV_FILE in ".env.e1a${ENV_SUFFIX}" ".env.e1b${ENV_SUFFIX}"; do
  # Only check if we have runs for that mode
  if [ -f "$ENV_FILE" ]; then
    continue
  fi
  for spec in "${RUN_SPECS[@]}"; do
    SPEC_MODE=$(echo "$spec" | cut -d' ' -f1 | tr 'A-Z' 'a-z')
    if [[ "$ENV_FILE" == *"$SPEC_MODE"* ]] && [ ! -f "$ENV_FILE" ]; then
      log "[ERROR] Missing $ENV_FILE"
      exit 1
    fi
  done
done

# ============================================
# Slot Worker Function
# ============================================
slot_worker() {
  # Disable set -e inside worker — we handle errors explicitly to ensure cleanup
  set +e

  local SLOT=$1
  local MODE=$2
  local RUN_NUM=$3
  local RUN_NAME=$4
  local SLOT_LOG="$LOG_DIR/${RUN_NAME}.log"

  local API_PORT=$((API_PORT_BASE + SLOT * PORT_STEP))
  local PG_PORT=$((PG_PORT_BASE + SLOT * PORT_STEP))
  local REDIS_PORT=$((REDIS_PORT_BASE + SLOT * PORT_STEP))
  local PROJECT_NAME="slot${SLOT}"

  local COMPOSE_CMD="docker compose -p $PROJECT_NAME -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_RANKING"

  local MODE_LOWER
  MODE_LOWER=$(echo "$MODE" | tr 'A-Z' 'a-z')
  local ENV_FILE=".env.e1${MODE_LOWER}${ENV_SUFFIX}"

  slog() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] [slot$SLOT/$RUN_NAME] $1"
    echo "$msg" >> "$SLOT_LOG"
    echo "$msg" >> "$SUMMARY_LOG"
    echo "$msg"
  }

  # Cleanup helper — ensures teardown happens even on unexpected errors
  worker_cleanup() {
    slog "Cleaning up slot $SLOT..."
    run_with_timeout 120 $COMPOSE_CMD down -v --remove-orphans 2>>"$SLOT_LOG" || \
      run_with_timeout 30 $COMPOSE_CMD kill 2>>"$SLOT_LOG" || true
    rm -f "$PROJECT_DIR/.env.slot${SLOT}"
  }

  slog "=== START: $RUN_NAME (Mode $MODE, slot $SLOT) ==="
  slog "Ports: API=$API_PORT PG=$PG_PORT Redis=$REDIS_PORT"
  local WORKER_START
  WORKER_START=$(date +%s)

  # --- Clean slate ---
  slog "Tearing down any previous state..."
  run_with_timeout 120 $COMPOSE_CMD down -v --remove-orphans 2>>"$SLOT_LOG" || true

  # --- Generate per-slot .env ---
  local SLOT_ENV="$PROJECT_DIR/.env.slot${SLOT}"
  cp "$PROJECT_DIR/$ENV_FILE" "$SLOT_ENV"
  if [ $? -ne 0 ]; then
    slog "[ERROR] Failed to copy env file $ENV_FILE"
    echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"
    return 1
  fi

  # Patch experiment name and run ID (macOS sed -i requires .bak suffix)
  sed -i.bak "s/^EXPERIMENT_NAME=.*/EXPERIMENT_NAME=$RUN_NAME/" "$SLOT_ENV"
  sed -i.bak "s/^EXPERIMENT_RUN_ID=.*/EXPERIMENT_RUN_ID=$RUN_NUM/" "$SLOT_ENV"
  rm -f "${SLOT_ENV}.bak"

  # Add port variables
  echo "" >> "$SLOT_ENV"
  echo "# Parallel slot ports (auto-generated)" >> "$SLOT_ENV"
  echo "HOST_API_PORT=$API_PORT" >> "$SLOT_ENV"
  echo "HOST_PG_PORT=$PG_PORT" >> "$SLOT_ENV"
  echo "HOST_REDIS_PORT=$REDIS_PORT" >> "$SLOT_ENV"

  # Export port vars for docker compose and child processes
  export HOST_API_PORT=$API_PORT
  export HOST_PG_PORT=$PG_PORT
  export HOST_REDIS_PORT=$REDIS_PORT

  # docker compose --env-file for this slot
  COMPOSE_CMD="docker compose -p $PROJECT_NAME --env-file $SLOT_ENV -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_RANKING"

  # --- Start infrastructure ---
  slog "Starting postgres + redis..."
  if ! $COMPOSE_CMD up -d postgres redis 2>>"$SLOT_LOG"; then
    slog "[ERROR] Failed to start postgres/redis"
    echo "FAILED" > "$LOG_DIR/${RUN_NAME}.status"
    worker_cleanup
    return 1
  fi
  sleep 15

  # --- Start API ---
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

  # --- Start agents ---
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

  # --- Run experiment (with watchdog) ---
  slog "Experiment running for ${RUN_DURATION}s..."
  local ELAPSED=0
  local CONSECUTIVE_API_FAILURES=0
  local CONSECUTIVE_NO_AGENTS=0
  local LAST_TREATMENT_COUNT=0
  local STALL_CHECKS=0
  local ABORTED=false

  while [ $ELAPSED -lt $RUN_DURATION ]; do
    local SLEEP_CHUNK=$PROGRESS_INTERVAL
    local REMAINING=$((RUN_DURATION - ELAPSED))
    if [ $SLEEP_CHUNK -gt $REMAINING ]; then
      SLEEP_CHUNK=$REMAINING
    fi
    sleep $SLEEP_CHUNK
    ELAPSED=$((ELAPSED + SLEEP_CHUNK))

    # --- Watchdog: API health ---
    local API_OK=false
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/api/v1/health" 2>/dev/null | grep -q "200"; then
      API_OK=true
      CONSECUTIVE_API_FAILURES=0
    else
      CONSECUTIVE_API_FAILURES=$((CONSECUTIVE_API_FAILURES + 1))
      slog "[WARN] API health check failed (consecutive: $CONSECUTIVE_API_FAILURES)"
    fi

    # --- Watchdog: agent count ---
    RUNNING=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep -c "ranking" || true)
    if [ "$RUNNING" -eq 0 ]; then
      CONSECUTIVE_NO_AGENTS=$((CONSECUTIVE_NO_AGENTS + 1))
      slog "[WARN] 0 agents running (consecutive: $CONSECUTIVE_NO_AGENTS)"
    else
      CONSECUTIVE_NO_AGENTS=0
    fi

    # --- Watchdog: treatment accumulation ---
    # Query DB directly — the API status endpoint requires auth which the
    # runner doesn't have. Use docker exec into the postgres container.
    local TREATMENTS
    TREATMENTS=$(docker compose -p "$PROJECT_NAME" --env-file "$SLOT_ENV" \
      -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_RANKING" \
      exec -T postgres psql -U moltbook -t -c \
      "SELECT COUNT(*) FROM experiment_treatments WHERE experiment_name = '$RUN_NAME'" \
      2>/dev/null | tr -d ' \n' || echo "0")
    TREATMENTS="${TREATMENTS:-0}"
    if [ "$TREATMENTS" != "?" ] && [ "$TREATMENTS" -eq "$LAST_TREATMENT_COUNT" ] 2>/dev/null; then
      STALL_CHECKS=$((STALL_CHECKS + 1))
      if [ $STALL_CHECKS -ge 2 ]; then
        slog "[WARN] Treatment count stalled at $TREATMENTS for $((STALL_CHECKS * PROGRESS_INTERVAL / 60))m"
      fi
    else
      STALL_CHECKS=0
      LAST_TREATMENT_COUNT="${TREATMENTS:-0}"
    fi

    slog "[${ELAPSED}s/${RUN_DURATION}s] ${RUNNING} agents, ${TREATMENTS} treatments, API=$([ "$API_OK" = true ] && echo 'OK' || echo 'DOWN')"

    # --- Watchdog: abort on catastrophic failure ---
    # API down for 2 consecutive checks (30 min) → abort
    if [ $CONSECUTIVE_API_FAILURES -ge 2 ]; then
      slog "[ERROR] API down for $((CONSECUTIVE_API_FAILURES * PROGRESS_INTERVAL / 60))m — aborting run"
      ABORTED=true
      break
    fi
    # 0 agents for 2 consecutive checks (30 min) → abort
    if [ $CONSECUTIVE_NO_AGENTS -ge 2 ]; then
      slog "[ERROR] No agents running for $((CONSECUTIVE_NO_AGENTS * PROGRESS_INTERVAL / 60))m — aborting run"
      ABORTED=true
      break
    fi
  done

  # --- Capture docker logs before export/teardown ---
  slog "Capturing container logs..."
  local EXPORT_PATH="$PROJECT_DIR/exports/$RUN_NAME"
  mkdir -p "$EXPORT_PATH"

  # API logs
  $COMPOSE_CMD logs --no-color --tail=5000 api > "$EXPORT_PATH/docker-logs-api.txt" 2>/dev/null || true

  # Agent logs (all 10 in one file)
  $COMPOSE_CMD logs --no-color --tail=2000 \
    civiclens-ranking-1 civiclens-ranking-2 civiclens-ranking-3 \
    civiclens-ranking-4 civiclens-ranking-5 civiclens-ranking-6 \
    civiclens-ranking-7 civiclens-ranking-8 civiclens-ranking-9 \
    civiclens-ranking-10 > "$EXPORT_PATH/docker-logs-agents.txt" 2>/dev/null || true

  # Extract errors into a summary
  grep -iE "(error|fail|exception|crash|ECONNREFUSED|rate.?limit|429|503)" \
    "$EXPORT_PATH/docker-logs-api.txt" "$EXPORT_PATH/docker-logs-agents.txt" \
    > "$EXPORT_PATH/errors.log" 2>/dev/null || true
  local ERROR_COUNT=0
  if [ -f "$EXPORT_PATH/errors.log" ]; then
    ERROR_COUNT=$(wc -l < "$EXPORT_PATH/errors.log" | tr -d ' ')
  fi
  slog "Captured logs: $ERROR_COUNT error lines found"

  # Check agent restart counts
  local RESTART_INFO
  RESTART_INFO=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r '.[] | select(.Name // .name | test("ranking")) | "\(.Name // .name): restarts=\(.Restarts // "?")"' 2>/dev/null || echo "")
  if [ -n "$RESTART_INFO" ]; then
    slog "Agent restarts:"
    echo "$RESTART_INFO" | while IFS= read -r line; do
      slog "  $line"
    done
  fi

  if [ "$ABORTED" = true ]; then
    slog "[ERROR] Run aborted early at ${ELAPSED}s/${RUN_DURATION}s"
    echo "ABORTED" > "$LOG_DIR/${RUN_NAME}.status"
    # Still try to export whatever data was collected
  fi

  # --- Export ---
  slog "Exporting..."
  local EXPORT_OK=true
  (
    export COMPOSE_PROJECT_NAME="$PROJECT_NAME"
    export SLOT_ENV_FILE="$SLOT_ENV"
    export HOST_API_PORT="$API_PORT"
    export HOST_PG_PORT="$PG_PORT"
    export HOST_REDIS_PORT="$REDIS_PORT"
    export MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"
    cd "$PROJECT_DIR"
    "$EXPORT_SCRIPT" "$RUN_NAME" 2>>"$SLOT_LOG"
  ) || { slog "[WARN] Export had errors"; EXPORT_OK=false; }

  # --- Teardown ---
  slog "Tearing down..."
  worker_cleanup

  local WORKER_END
  WORKER_END=$(date +%s)
  local WORKER_ELAPSED=$((WORKER_END - WORKER_START))
  slog "=== DONE: $RUN_NAME in $(( WORKER_ELAPSED / 60 )) minutes ==="

  # Write final status (don't overwrite ABORTED — partial data may still be useful)
  if [ "$ABORTED" = true ]; then
    # Keep ABORTED status, but note if export succeeded
    if [ "$EXPORT_OK" = true ]; then
      echo "ABORTED_WITH_DATA" > "$LOG_DIR/${RUN_NAME}.status"
    fi
    # else ABORTED status already written
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
  if [ -f "$PROJECT_DIR/exports/$RUN_NAME/treatments.jsonl" ]; then
    local TCOUNT
    TCOUNT=$(wc -l < "$PROJECT_DIR/exports/$RUN_NAME/treatments.jsonl" | tr -d ' ')
    slog "Treatments: ${TCOUNT}"
  fi
}

# ============================================
# Cleanup on interrupt
# ============================================
cleanup() {
  log ""
  log "[INTERRUPT] Cleaning up all slots..."
  for s in $(seq 0 $((MAX_SLOTS - 1))); do
    local PROJECT_NAME="slot${s}"
    local SLOT_ENV="$PROJECT_DIR/.env.slot${s}"
    if [ -f "$SLOT_ENV" ]; then
      log "  Stopping slot $s..."
      run_with_timeout 60 docker compose -p "$PROJECT_NAME" --env-file "$SLOT_ENV" \
        -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_RANKING" \
        down -v --remove-orphans 2>/dev/null || \
      run_with_timeout 30 docker compose -p "$PROJECT_NAME" --env-file "$SLOT_ENV" \
        -f "$PROJECT_DIR/$COMPOSE_BASE" -f "$PROJECT_DIR/$COMPOSE_RANKING" \
        kill 2>/dev/null || true
      rm -f "$SLOT_ENV"
    fi
  done
  log "Cleanup complete."
  exit 1
}

trap cleanup INT TERM

# ============================================
# Main Orchestrator Loop
# ============================================
GLOBAL_START=$(date +%s)
QUEUE_IDX=0
COMPLETED=0
FAILED=0

# Track which slot is running what (PID)
declare -a SLOT_PIDS=()
declare -a SLOT_RUNS=()
for s in $(seq 0 $((MAX_SLOTS - 1))); do
  SLOT_PIDS[$s]=0
  SLOT_RUNS[$s]=""
done

log "============================================"
log "Starting orchestrator: $TOTAL_RUNS runs, $MAX_SLOTS slots"
log "============================================"

while [ $((COMPLETED + FAILED)) -lt $TOTAL_RUNS ]; do
  # Check for finished slots
  for s in $(seq 0 $((MAX_SLOTS - 1))); do
    PID=${SLOT_PIDS[$s]}
    if [ "$PID" -ne 0 ]; then
      if ! kill -0 "$PID" 2>/dev/null; then
        # Slot finished — reap process (|| true to prevent set -e abort)
        RUN_NAME="${SLOT_RUNS[$s]}"
        wait "$PID" 2>/dev/null || true

        RUN_STATUS="UNKNOWN"
        if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
          RUN_STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status")
        fi

        case "$RUN_STATUS" in
          OK)
            COMPLETED=$((COMPLETED + 1))
            log "[SLOT $s] $RUN_NAME completed ($COMPLETED/$TOTAL_RUNS done)"
            ;;
          ABORTED_WITH_DATA)
            COMPLETED=$((COMPLETED + 1))
            log "[SLOT $s] $RUN_NAME ABORTED early but exported data ($COMPLETED/$TOTAL_RUNS done)"
            ;;
          ABORTED|FAILED|EXPORT_FAILED|*)
            FAILED=$((FAILED + 1))
            log "[SLOT $s] $RUN_NAME $RUN_STATUS (check $LOG_DIR/${RUN_NAME}.log)"
            ;;
        esac

        SLOT_PIDS[$s]=0
        SLOT_RUNS[$s]=""
      fi
    fi
  done

  # Assign new runs to free slots
  for s in $(seq 0 $((MAX_SLOTS - 1))); do
    if [ ${SLOT_PIDS[$s]} -eq 0 ] && [ $QUEUE_IDX -lt $TOTAL_RUNS ]; then
      entry="${RUN_QUEUE[$QUEUE_IDX]}"
      MODE=$(echo "$entry" | cut -d' ' -f1)
      RUN_NUM=$(echo "$entry" | cut -d' ' -f2)
      RUN_NAME=$(echo "$entry" | cut -d' ' -f3)
      QUEUE_IDX=$((QUEUE_IDX + 1))

      log "[SLOT $s] Starting $RUN_NAME (Mode $MODE, #$QUEUE_IDX/$TOTAL_RUNS)"

      slot_worker "$s" "$MODE" "$RUN_NUM" "$RUN_NAME" &
      SLOT_PIDS[$s]=$!
      SLOT_RUNS[$s]="$RUN_NAME"
    fi
  done

  # Check if all done
  ALL_IDLE=true
  for s in $(seq 0 $((MAX_SLOTS - 1))); do
    if [ ${SLOT_PIDS[$s]} -ne 0 ]; then
      ALL_IDLE=false
      break
    fi
  done

  if [ "$ALL_IDLE" = true ] && [ $QUEUE_IDX -ge $TOTAL_RUNS ]; then
    break
  fi

  # Poll every 10 seconds
  sleep 10
done

# Wait for any stragglers
for s in $(seq 0 $((MAX_SLOTS - 1))); do
  PID=${SLOT_PIDS[$s]}
  if [ "$PID" -ne 0 ]; then
    RUN_NAME="${SLOT_RUNS[$s]}"
    log "Waiting for slot $s ($RUN_NAME) to finish..."
    wait "$PID" 2>/dev/null || true

    local RUN_STATUS="UNKNOWN"
    if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
      RUN_STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status")
    fi
    case "$RUN_STATUS" in
      OK|ABORTED_WITH_DATA) COMPLETED=$((COMPLETED + 1)) ;;
      *) FAILED=$((FAILED + 1)) ;;
    esac
  fi
done

trap - INT TERM

# ============================================
# Final Summary
# ============================================
GLOBAL_END=$(date +%s)
GLOBAL_ELAPSED=$((GLOBAL_END - GLOBAL_START))

log ""
log "============================================"
log "PARALLEL RUN COMPLETE"
log "============================================"
log "Total time: $(( GLOBAL_ELAPSED / 3600 ))h $(( (GLOBAL_ELAPSED % 3600) / 60 ))m"
log "Completed:  $COMPLETED / $TOTAL_RUNS"
log "Failed:     $FAILED"
log ""
log "Export directories:"

for entry in "${RUN_QUEUE[@]}"; do
  RUN_NAME=$(echo "$entry" | cut -d' ' -f3)
  STATUS="MISSING"
  if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
    STATUS=$(cat "$LOG_DIR/${RUN_NAME}.status")
  fi

  if [ -d "$PROJECT_DIR/exports/$RUN_NAME" ]; then
    SIZE=$(du -sh "$PROJECT_DIR/exports/$RUN_NAME" 2>/dev/null | cut -f1)
    POSTS=$(jq -r '.stats.posts // "?"' "$PROJECT_DIR/exports/$RUN_NAME/metadata.json" 2>/dev/null || echo "?")
    TREATMENTS="?"
    if [ -f "$PROJECT_DIR/exports/$RUN_NAME/treatments.jsonl" ]; then
      TREATMENTS=$(wc -l < "$PROJECT_DIR/exports/$RUN_NAME/treatments.jsonl" | tr -d ' ')
    fi
    ERRORS="0"
    if [ -f "$PROJECT_DIR/exports/$RUN_NAME/errors.log" ]; then
      ERRORS=$(wc -l < "$PROJECT_DIR/exports/$RUN_NAME/errors.log" | tr -d ' ')
    fi
    log "  $RUN_NAME  [$STATUS]  ${POSTS} posts, ${TREATMENTS} treatments, ${ERRORS} errors  ($SIZE)"
  else
    log "  $RUN_NAME  [$STATUS]  (no export dir)"
  fi
done

log ""
log "Per-run logs:   $LOG_DIR/<run_name>.log"
log "Error extracts: exports/<run_name>/errors.log"
log "Docker logs:    exports/<run_name>/docker-logs-{api,agents}.txt"
log "Summary:        $SUMMARY_LOG"

if [ $FAILED -gt 0 ]; then
  log ""
  log "[WARN] $FAILED runs failed. Check individual logs:"
  for entry in "${RUN_QUEUE[@]}"; do
    RUN_NAME=$(echo "$entry" | cut -d' ' -f3)
    if [ -f "$LOG_DIR/${RUN_NAME}.status" ]; then
      local S=$(cat "$LOG_DIR/${RUN_NAME}.status")
      if [ "$S" != "OK" ] && [ "$S" != "ABORTED_WITH_DATA" ]; then
        log "  - $LOG_DIR/${RUN_NAME}.log ($S)"
      fi
    fi
  done
  exit 1
fi
