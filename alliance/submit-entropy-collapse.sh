#!/usr/bin/env bash
# ============================================
# Submit Entropy Collapse experiments on Alliance Canada
# ============================================
#
# Runs 8 conditions × N replications as Slurm job arrays:
#   E-MAG-0     — empty feed (true control)
#   E-MAG-1     — 1 conspiracy post
#   E-MAG-5     — 5 conspiracy posts
#   E-MAG-25    — 25 conspiracy posts (standard baseline)
#   E-DOM-AGI   — 25 AGI hype posts
#   E-DOM-TECH  — 25 tech news posts
#   E-HET-DUAL  — 12 conspiracy + 13 AGI (interleaved)
#   E-HET-MULTI — 8 conspiracy + 8 AGI + 9 tech (interleaved)
#
# Each condition is submitted as a separate Slurm job array.
# Each array task = one independent 1h experiment with 10 agents.
#
# Usage:
#   bash alliance/submit-entropy-collapse.sh                         # All 8 conditions, 3 runs each
#   bash alliance/submit-entropy-collapse.sh --runs 5                # 5 replications each
#   bash alliance/submit-entropy-collapse.sh --conditions mag0,mag1  # Only specific conditions
#   bash alliance/submit-entropy-collapse.sh --dry-run               # Preview without submitting

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT="${PROJECT:-/project/def-zhijing/anangia}"
CONFIG_DIR="$PROJECT/moltbook/config"

# Load config
if [ -f "$CONFIG_DIR/.env" ]; then
  set -a
  source "$CONFIG_DIR/.env"
  set +a
else
  echo "[ERROR] No config found. Run setup-cluster.sh first."
  exit 1
fi

# Defaults
NUM_RUNS="${NUM_RUNS:-3}"
CPUS="${CPUS_PER_TASK:-2}"
MEM="${MEM_PER_JOB:-22G}"
WALLTIME="${WALLTIME:-1:30:00}"
ACCOUNT="${ALLIANCE_ACCOUNT:-}"
DRY_RUN=false
SELECTED_CONDITIONS=""

ALL_CONDITIONS="mag0 mag1 mag5 mag25 dom-agi dom-tech het-dual het-multi"

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --runs|-n)       NUM_RUNS="$2"; shift 2 ;;
    --walltime|-t)   WALLTIME="$2"; shift 2 ;;
    --mem|-m)        MEM="$2"; shift 2 ;;
    --cpus|-c)       CPUS="$2"; shift 2 ;;
    --account|-A)    ACCOUNT="$2"; shift 2 ;;
    --conditions)    SELECTED_CONDITIONS="$2"; shift 2 ;;
    --dry-run)       DRY_RUN=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ -z "$ACCOUNT" ]; then
  echo "[ERROR] ALLIANCE_ACCOUNT not set in config or --account not provided."
  exit 1
fi

# Resolve conditions
if [ -n "$SELECTED_CONDITIONS" ]; then
  CONDITIONS=$(echo "$SELECTED_CONDITIONS" | tr ',' ' ')
else
  CONDITIONS="$ALL_CONDITIONS"
fi

# Count
NUM_CONDITIONS=0
for c in $CONDITIONS; do
  NUM_CONDITIONS=$((NUM_CONDITIONS + 1))
done

TOTAL_JOBS=$((NUM_CONDITIONS * NUM_RUNS))

# Condition descriptions
condition_desc() {
  case "$1" in
    mag0)      echo "0 posts (empty feed)" ;;
    mag1)      echo "1 conspiracy post" ;;
    mag5)      echo "5 conspiracy posts" ;;
    mag25)     echo "25 conspiracy posts" ;;
    dom-agi)   echo "25 AGI hype posts" ;;
    dom-tech)  echo "25 tech news posts" ;;
    het-dual)  echo "12 conspiracy + 13 AGI" ;;
    het-multi) echo "8 conspiracy + 8 AGI + 9 tech" ;;
    *)         echo "unknown" ;;
  esac
}

echo "============================================"
echo "  Entropy Collapse — Alliance Batch Submit"
echo "============================================"
echo ""
echo "  Conditions:    $NUM_CONDITIONS"
echo "  Runs/cond:     $NUM_RUNS"
echo "  Total jobs:    $TOTAL_JOBS"
echo "  Per job:       $CPUS CPUs, $MEM RAM, $WALLTIME walltime"
echo "  Account:       $ACCOUNT"
echo "  Model:         ${OPENAI_MODEL:-${OPENROUTER_MODEL:-unknown}}"
echo ""
echo "  Conditions:"
for c in $CONDITIONS; do
  echo "    $c  — $(condition_desc "$c")"
done
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "[DRY RUN] Would submit:"
  echo ""
  for c in $CONDITIONS; do
    echo "  CONDITION=$c sbatch \\"
    echo "    --account=$ACCOUNT --array=1-$NUM_RUNS \\"
    echo "    --cpus-per-task=$CPUS --mem=$MEM --time=$WALLTIME \\"
    echo "    --job-name=ec-$c \\"
    echo "    --export=ALL,CONDITION=$c \\"
    echo "    $SCRIPT_DIR/slurm-experiment.sh"
    echo ""
  done
  exit 0
fi

# Verify world posts files exist
WORLD_POSTS_DIR="$CONFIG_DIR/world-posts"
if [ ! -d "$WORLD_POSTS_DIR" ]; then
  echo "[ERROR] World posts dir not found: $WORLD_POSTS_DIR"
  echo "Copy world posts files there first."
  exit 1
fi

# Submit each condition as a separate job array
echo "Submitting jobs..."
echo ""
JOB_IDS=()

for c in $CONDITIONS; do
  JOB_ID=$(sbatch \
    --account="$ACCOUNT" \
    --array="1-$NUM_RUNS" \
    --cpus-per-task="$CPUS" \
    --mem="$MEM" \
    --time="$WALLTIME" \
    --job-name="ec-$c" \
    --output="ec-${c}-%A_%a.out" \
    --error="ec-${c}-%A_%a.err" \
    --export="ALL,CONDITION=$c" \
    --parsable \
    "$SCRIPT_DIR/slurm-experiment.sh")

  JOB_IDS+=("$JOB_ID")
  echo "  [$c] Job $JOB_ID  (${NUM_RUNS} runs: ${JOB_ID}_[1-${NUM_RUNS}])"
done

echo ""
echo "============================================"
echo "  All Submitted: ${#JOB_IDS[@]} job arrays"
echo "============================================"
echo ""
echo "  Monitor:  squeue -u $USER"
echo "  Logs:     tail -f ec-<condition>-<jobid>_<run>.out"
echo "  Cancel:   scancel ${JOB_IDS[*]}"
echo ""
echo "  Results:  \$SCRATCH/moltbook/results/ec-<condition>-run<NN>/"
echo ""
