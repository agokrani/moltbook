#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT="${PROJECT:-/project/def-zhijing/anangia}"
CONFIG_DIR="$PROJECT/moltbook/config"

HEARTBEAT_SRC="$REPO_DIR/agents/HEARTBEAT-v3-obsessions.md"

DEFAULT_RUNS="${NUM_RUNS:-1}"
DEFAULT_OUT_DIR="${OUT_DIR:-obsessions}"
DEFAULT_EXP_PREFIX="${EXP_PREFIX:-obs}"
DEFAULT_NUM_AGENTS="${NUM_AGENTS:-10}"
DEFAULT_HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-60s}"
DEFAULT_DURATION="${EXPERIMENT_DURATION:-1h}"
DEFAULT_CONDITIONS="${CONDITIONS:-mag0,mag1,mag5,mag25,dom-agi,dom-tech}"

if [ ! -f "$HEARTBEAT_SRC" ]; then
  echo "[ERROR] Missing heartbeat file: $HEARTBEAT_SRC"
  exit 1
fi

if [ ! -d "$CONFIG_DIR" ]; then
  echo "[ERROR] Missing config dir: $CONFIG_DIR"
  echo "Run alliance/setup-cluster.sh first."
  exit 1
fi

echo "============================================"
echo "  Obsession Run Submission"
echo "============================================"
echo "  Heartbeat:  $HEARTBEAT_SRC"
echo "  Conditions: $DEFAULT_CONDITIONS"
echo "  Runs:       $DEFAULT_RUNS"
echo "  Agents:     $DEFAULT_NUM_AGENTS"
echo "  Interval:   $DEFAULT_HEARTBEAT_INTERVAL"
echo "  Duration:   $DEFAULT_DURATION"
echo "  Results:    $DEFAULT_OUT_DIR"
echo "============================================"
echo ""

HEARTBEAT_FILE="$HEARTBEAT_SRC" \
MOLTBOOK_REPO_DIR="$REPO_DIR" \
OUT_DIR="$DEFAULT_OUT_DIR" \
EXP_PREFIX="$DEFAULT_EXP_PREFIX" \
NUM_AGENTS="$DEFAULT_NUM_AGENTS" \
HEARTBEAT_INTERVAL="$DEFAULT_HEARTBEAT_INTERVAL" \
EXPERIMENT_DURATION="$DEFAULT_DURATION" \
bash "$SCRIPT_DIR/submit-entropy-collapse.sh" --conditions "$DEFAULT_CONDITIONS" --runs "$DEFAULT_RUNS" "$@"
