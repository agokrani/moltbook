#!/usr/bin/env bash
# CivicLens Experiment Runner
# Automatically runs experiment, exports data, then cleans up
#
# Usage: ./run-experiment.sh <experiment_name> [options]
#
# Options:
#   --duration <time>    How long to run (e.g., 30m, 2h, 1d). Default: 1h
#   --compose <file>     Compose file to use. Default: auto-detect from name
#   --seed <tasks.jsonl> Seed tasks after startup (see experiments/)
#   --provider <name>    Force provider: openrouter, openai, or anthropic
#   --model <id>         Model ID for the selected provider
#   --build              Rebuild images before starting (useful after regenerating souls/compose)
#   --push               Push to HuggingFace after export
#   --keep               Keep containers running after export (don't stop)
#   --no-clear           Don't clear volumes after stopping
#
# Examples:
#   ./scripts/run-experiment.sh religion-v1 --duration 2h --push
#   ./scripts/run-experiment.sh baseline-test --duration 30m --keep

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_DIR/docker"
BASE_COMPOSE_FILE="$DOCKER_DIR/docker-compose.yml"

# Defaults
EXPERIMENT_NAME=""
DURATION="1h"
COMPOSE_FILE=""
SEED_TASKS_FILE=""
PROVIDER=""
MODEL_ID=""
DO_BUILD=false
PUSH_TO_HF=false
KEEP_RUNNING=false
CLEAR_VOLUMES=true

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --duration)
      DURATION="$2"
      shift 2
      ;;
    --compose)
      COMPOSE_FILE="$2"
      shift 2
      ;;
    --seed)
      SEED_TASKS_FILE="$2"
      shift 2
      ;;
    --provider)
      PROVIDER="$2"
      shift 2
      ;;
    --model)
      MODEL_ID="$2"
      shift 2
      ;;
    --build)
      DO_BUILD=true
      shift
      ;;
    --push)
      PUSH_TO_HF=true
      shift
      ;;
    --keep)
      KEEP_RUNNING=true
      shift
      ;;
    --no-clear)
      CLEAR_VOLUMES=false
      shift
      ;;
    -*)
      echo "Unknown option: $1"
      exit 1
      ;;
    *)
      if [ -z "$EXPERIMENT_NAME" ]; then
        EXPERIMENT_NAME="$1"
      fi
      shift
      ;;
  esac
done

if [ -z "$EXPERIMENT_NAME" ]; then
  echo "Usage: ./run-experiment.sh <experiment_name> [--duration 1h] [--provider openai] [--model gpt-5-nano] [--push] [--keep]"
  echo ""
  echo "Available experiments:"
  ls -1 "$DOCKER_DIR"/docker-compose.civiclens*.yml 2>/dev/null | xargs -I {} basename {} | sed 's/docker-compose.civiclens-\?/  /; s/.yml//'
  exit 1
fi

# Auto-detect compose file if not specified
if [ -z "$COMPOSE_FILE" ]; then
  # Try to match experiment name to compose file
  if [ -f "$DOCKER_DIR/docker-compose.civiclens-${EXPERIMENT_NAME%%-*}.yml" ]; then
    COMPOSE_FILE="docker-compose.civiclens-${EXPERIMENT_NAME%%-*}.yml"
  elif [ -f "$DOCKER_DIR/docker-compose.civiclens.yml" ]; then
    COMPOSE_FILE="docker-compose.civiclens.yml"
  else
    echo "[ERROR] No compose file found. Specify with --compose"
    exit 1
  fi
fi

resolve_compose_file() {
  local path="$1"
  if [ -f "$path" ]; then
    printf '%s\n' "$path"
  elif [ -f "$PROJECT_DIR/$path" ]; then
    printf '%s\n' "$PROJECT_DIR/$path"
  elif [ -f "$DOCKER_DIR/$path" ]; then
    printf '%s\n' "$DOCKER_DIR/$path"
  else
    return 1
  fi
}

if ! COMPOSE_PATH="$(resolve_compose_file "$COMPOSE_FILE")"; then
  echo "[ERROR] Compose file not found: $COMPOSE_FILE"
  exit 1
fi

COMPOSE_ARGS=(-f "$BASE_COMPOSE_FILE" -f "$COMPOSE_PATH")
COMPOSE_ENV=()
unset_compose_env() {
  local key
  for key in "$@"; do
    COMPOSE_ENV+=("${key}=")
  done
}

case "$PROVIDER" in
  "" ) ;;
  openai)
    unset_compose_env OPENROUTER_API_KEY ANTHROPIC_API_KEY
    [ -n "$MODEL_ID" ] && COMPOSE_ENV+=("OPENAI_MODEL=$MODEL_ID")
    ;;
  openrouter)
    unset_compose_env ANTHROPIC_API_KEY
    [ -n "$MODEL_ID" ] && COMPOSE_ENV+=("OPENROUTER_MODEL=$MODEL_ID")
    ;;
  anthropic)
    unset_compose_env OPENROUTER_API_KEY
    [ -n "$MODEL_ID" ] && COMPOSE_ENV+=("ANTHROPIC_MODEL=$MODEL_ID")
    ;;
  *)
    echo "[ERROR] Unknown provider: $PROVIDER"
    echo "Use one of: openrouter, openai, anthropic"
    exit 1
    ;;
esac

compose_cmd() {
  env "${COMPOSE_ENV[@]}" docker compose "${COMPOSE_ARGS[@]}" "$@"
}

# Convert duration to seconds
duration_to_seconds() {
  local duration=$1
  local num=${duration%[smhd]}
  local unit=${duration: -1}

  case $unit in
    s) echo $num ;;
    m) echo $((num * 60)) ;;
    h) echo $((num * 3600)) ;;
    d) echo $((num * 86400)) ;;
    *) echo $((duration)) ;;  # Assume seconds if no unit
  esac
}

DURATION_SECONDS=$(duration_to_seconds "$DURATION")

echo "============================================"
echo "  CivicLens Experiment Runner"
echo "============================================"
echo ""
echo "  Experiment:  $EXPERIMENT_NAME"
echo "  Duration:    $DURATION ($DURATION_SECONDS seconds)"
echo "  Compose:     $COMPOSE_PATH"
echo "  Seed tasks:  ${SEED_TASKS_FILE:-<none>}"
echo "  Provider:    ${PROVIDER:-auto}"
echo "  Model:       ${MODEL_ID:-<default>}"
echo "  Build:       $DO_BUILD"
echo "  Push to HF:  $PUSH_TO_HF"
echo "  Keep after:  $KEEP_RUNNING"
echo "  Clear vols:  $CLEAR_VOLUMES"
echo ""
echo "============================================"
echo ""

cd "$PROJECT_DIR"

# ============================================
# Phase 1: Start Experiment
# ============================================
echo "[1/5] Starting experiment..."

# Optional build flag (refresh agents after regenerating souls/compose)
BUILD_FLAG=""
if [ "$DO_BUILD" = true ]; then
  BUILD_FLAG="--build"
fi

# Start core services first (skip web - not needed for experiments)
compose_cmd up -d $BUILD_FLAG postgres redis api

# Wait for API to be healthy
echo "  Waiting for API..."
for i in {1..30}; do
  if curl -s http://localhost:4000/api/v1/health > /dev/null 2>&1; then
    echo "  API ready."
    break
  fi
  sleep 2
done

# Get list of agent services from compose file (exclude web, postgres, redis, api)
AGENT_SERVICES=$(compose_cmd config --services 2>/dev/null | grep -v -E '^(web|postgres|redis|api)$' | tr '\n' ' ')

# Start all agents (explicitly, skipping web)
compose_cmd up -d $BUILD_FLAG $AGENT_SERVICES

# Count running containers
AGENT_COUNT=$(compose_cmd ps --format json 2>/dev/null | grep -c "agent" || echo "?")
echo "  Started $AGENT_COUNT agent containers."
echo ""

# Wait for agents to register, then show an API key for viewing
echo "  Waiting for agents to register..."
sleep 10

# Optional: seed tasks/posts for standardized benchmarks
if [ -n "$SEED_TASKS_FILE" ]; then
  if [ ! -f "$SEED_TASKS_FILE" ]; then
    echo ""
    echo "[ERROR] Seed tasks file not found: $SEED_TASKS_FILE"
    exit 1
  fi
  echo ""
  echo "Seeding tasks from: $SEED_TASKS_FILE"
  bash "$SCRIPT_DIR/seed-tasks.sh" "$SEED_TASKS_FILE" --api-url "http://localhost:4000/api/v1"
  echo ""
fi

FIRST_AGENT=$(echo "$AGENT_SERVICES" | awk '{print $1}')
if [ -n "$FIRST_AGENT" ]; then
  API_KEY=$(compose_cmd exec -T "$FIRST_AGENT" cat /root/.config/moltbook/credentials.json 2>/dev/null | grep -o '"api_key"[^,]*' | cut -d'"' -f4 || echo "")
  if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
    echo ""
    echo "============================================"
    echo "  View the experiment:"
    echo "============================================"
    echo ""
    echo "  API:     http://localhost:4000/api/v1/posts"
    echo "  Web UI:  http://localhost:3000 (if running)"
    echo ""
    echo "  API Key: $API_KEY"
    echo ""
    echo "  Quick check:"
    echo "  curl -H \"Authorization: Bearer $API_KEY\" http://localhost:4000/api/v1/posts"
    echo ""
    echo "============================================"
  fi
fi
echo ""

# ============================================
# Phase 2: Run Experiment
# ============================================
echo "[2/5] Running experiment for $DURATION..."
echo ""
echo "  Started at: $(date)"
echo "  Will end at: $(date -d "+${DURATION_SECONDS} seconds" 2>/dev/null || date -v+${DURATION_SECONDS}S 2>/dev/null || echo "~$DURATION from now")"
echo ""
echo "  Monitoring... (Ctrl+C to stop early and export)"
echo ""

# Track start time
START_TIME=$(date +%s)

# Handle Ctrl+C gracefully - still export
trap 'echo ""; echo "  Interrupted! Proceeding to export..."; INTERRUPTED=true' INT

INTERRUPTED=false

# Progress display
while true; do
  ELAPSED=$(($(date +%s) - START_TIME))
  REMAINING=$((DURATION_SECONDS - ELAPSED))

  if [ $REMAINING -le 0 ] || [ "$INTERRUPTED" = true ]; then
    break
  fi

  # Show progress every 30 seconds
  if [ $((ELAPSED % 30)) -eq 0 ]; then
    # Get current stats
    POST_COUNT=$(curl -s "http://localhost:4000/api/v1/posts?limit=1" 2>/dev/null | grep -o '"total":[0-9]*' | grep -o '[0-9]*' || echo "?")
    ELAPSED_MIN=$((ELAPSED / 60))
    REMAINING_MIN=$((REMAINING / 60))
    echo "  [${ELAPSED_MIN}m elapsed, ${REMAINING_MIN}m remaining] Posts: $POST_COUNT"
  fi

  sleep 10
done

trap - INT

ACTUAL_DURATION=$(($(date +%s) - START_TIME))
echo ""
echo "  Experiment ran for $((ACTUAL_DURATION / 60)) minutes."
echo ""

# ============================================
# Phase 3: Export Data
# ============================================
echo "[3/5] Exporting experiment data..."

PUSH_FLAG=""
if [ "$PUSH_TO_HF" = true ]; then
  PUSH_FLAG="--push"
fi

"$SCRIPT_DIR/export-experiment.sh" "$EXPERIMENT_NAME" $PUSH_FLAG

echo ""

# ============================================
# Phase 4: Stop Containers
# ============================================
if [ "$KEEP_RUNNING" = true ]; then
  echo "[4/5] Keeping containers running (--keep specified)"
else
  echo "[4/5] Stopping containers..."
  # Stop only the services we started (skip web)
  compose_cmd stop $AGENT_SERVICES api postgres redis 2>/dev/null || true
  compose_cmd rm -f $AGENT_SERVICES 2>/dev/null || true
fi

echo ""

# ============================================
# Phase 5: Clear Volumes (optional)
# ============================================
if [ "$KEEP_RUNNING" = false ] && [ "$CLEAR_VOLUMES" = true ]; then
  echo "[5/5] Clearing volumes..."
  # Remove volumes for database and agents (this removes all experiment data)
  compose_cmd down -v --remove-orphans 2>/dev/null || true
  echo "  Volumes cleared."
else
  echo "[5/5] Skipping volume cleanup"
fi

echo ""
echo "============================================"
echo "  Experiment Complete!"
echo "============================================"
echo ""
echo "  Name:     $EXPERIMENT_NAME"
echo "  Duration: $((ACTUAL_DURATION / 60)) minutes"
echo "  Data:     exports/$EXPERIMENT_NAME/"
echo ""

if [ "$PUSH_TO_HF" = true ] && [ -n "$HF_REPO" ]; then
  echo "  HuggingFace: https://huggingface.co/datasets/$HF_REPO"
fi

echo ""
