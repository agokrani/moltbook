#!/usr/bin/env bash
# Submit a batch of independent MoltBook experiments to Slurm
#
# This is the "easy button" — configure env.template, run this script,
# and it submits N independent experiments as a Slurm job array.
#
# Usage:
#   bash alliance/submit-batch.sh                    # Use defaults from .env
#   bash alliance/submit-batch.sh --experiments 3    # Override count
#   bash alliance/submit-batch.sh --dry-run          # Show what would be submitted
#
# Each array task gets its own compute node with its own PostgreSQL, Redis,
# API, and 10 agents. Experiments are fully independent.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
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

# Defaults from config
NUM_EXPERIMENTS="${NUM_EXPERIMENTS:-5}"
CPUS="${CPUS_PER_TASK:-2}"
MEM="${MEM_PER_JOB:-22G}"
WALLTIME="${WALLTIME:-3:00:00}"
ACCOUNT="${ALLIANCE_ACCOUNT:-}"
DRY_RUN=false

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --experiments|-n) NUM_EXPERIMENTS="$2"; shift 2 ;;
    --walltime|-t) WALLTIME="$2"; shift 2 ;;
    --mem|-m) MEM="$2"; shift 2 ;;
    --cpus|-c) CPUS="$2"; shift 2 ;;
    --account|-A) ACCOUNT="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [ -z "$ACCOUNT" ]; then
  echo "[ERROR] ALLIANCE_ACCOUNT not set in config or --account not provided."
  echo "Edit $CONFIG_DIR/.env and set ALLIANCE_ACCOUNT=def-yourpi"
  exit 1
fi

echo "============================================"
echo "  MoltBook Batch Submission"
echo "============================================"
echo ""
echo "  Experiments:  $NUM_EXPERIMENTS (independent)"
echo "  Per experiment:"
echo "    CPUs:       $CPUS"
echo "    Memory:     $MEM"
echo "    Walltime:   $WALLTIME"
echo "    Account:    $ACCOUNT"
echo ""
echo "  Total resources: ${NUM_EXPERIMENTS}x ($CPUS CPUs, $MEM RAM)"
echo ""

if [ "$DRY_RUN" = true ]; then
  echo "[DRY RUN] Would submit:"
  echo ""
  echo "  sbatch \\"
  echo "    --account=$ACCOUNT \\"
  echo "    --array=1-$NUM_EXPERIMENTS \\"
  echo "    --cpus-per-task=$CPUS \\"
  echo "    --mem=$MEM \\"
  echo "    --time=$WALLTIME \\"
  echo "    $SCRIPT_DIR/slurm-experiment.sh"
  echo ""
  exit 0
fi

# Submit the job array
JOB_ID=$(sbatch \
  --account="$ACCOUNT" \
  --array="1-$NUM_EXPERIMENTS" \
  --cpus-per-task="$CPUS" \
  --mem="$MEM" \
  --time="$WALLTIME" \
  --parsable \
  "$SCRIPT_DIR/slurm-experiment.sh")

echo "  Submitted job array: $JOB_ID"
echo "  Tasks: ${JOB_ID}_[1-${NUM_EXPERIMENTS}]"
echo ""
echo "  Monitor:  squeue -u $USER"
echo "  Logs:     tail -f moltbook-exp-${JOB_ID}_1.out"
echo "  Cancel:   scancel $JOB_ID"
echo ""
echo "  Results will appear in: \$SCRATCH/moltbook/results/"
echo ""
