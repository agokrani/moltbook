#!/usr/bin/env bash
# Collect and merge results from a batch of MoltBook experiments
#
# After a Slurm job array completes, this script gathers all experiment
# results into a single directory ready for analysis or HuggingFace upload.
#
# Usage:
#   bash alliance/collect-results.sh <job-id>
#   bash alliance/collect-results.sh 12345678
#
# Output: $SCRATCH/moltbook/results/batch-<job-id>/

set -euo pipefail

JOB_ID="${1:-}"

if [ -z "$JOB_ID" ]; then
  echo "Usage: bash alliance/collect-results.sh <slurm-job-id>"
  echo ""
  echo "Available results (scratch):"
  ls -d "$RESULTS_SCRATCH"/exp-* 2>/dev/null | sort || echo "  (none)"
  echo ""
  echo "Available results (project backup):"
  ls -d "$RESULTS_PROJECT"/exp-* 2>/dev/null | sort || echo "  (none)"
  exit 1
fi

# Check both scratch and project for results
RESULTS_SCRATCH="$SCRATCH/moltbook/results"
RESULTS_PROJECT="$PROJECT/moltbook/results"
RESULTS_BASE="$RESULTS_SCRATCH"  # Primary source (faster)
BATCH_DIR="$RESULTS_SCRATCH/batch-${JOB_ID}"

mkdir -p "$BATCH_DIR"

echo "============================================"
echo "  Collecting results for job $JOB_ID"
echo "============================================"
echo ""

# Find all experiment directories for this job
EXPERIMENTS=()
# Check scratch first, fall back to project backup
for dir in "$RESULTS_SCRATCH"/exp-${JOB_ID}-run* "$RESULTS_PROJECT"/exp-${JOB_ID}-run*; do
  if [ -d "$dir" ]; then
    # Avoid duplicates (prefer scratch version)
    BASENAME=$(basename "$dir")
    ALREADY=false
    for existing in "${EXPERIMENTS[@]:-}"; do
      if [ "$(basename "$existing")" = "$BASENAME" ]; then
        ALREADY=true
        break
      fi
    done
    if [ "$ALREADY" = false ]; then
      EXPERIMENTS+=("$dir")
    fi
  fi
done

if [ ${#EXPERIMENTS[@]} -eq 0 ]; then
  echo "[ERROR] No experiment directories found for job $JOB_ID"
  echo "Looking for: $RESULTS_BASE/exp-${JOB_ID}-run*"
  exit 1
fi

echo "  Found ${#EXPERIMENTS[@]} experiments:"
for exp in "${EXPERIMENTS[@]}"; do
  NAME=$(basename "$exp")
  POSTS=$(wc -l < "$exp/posts.jsonl" 2>/dev/null || echo "0")
  COMMENTS=$(wc -l < "$exp/comments.jsonl" 2>/dev/null || echo "0")
  echo "    $NAME: $POSTS posts, $COMMENTS comments"
done

# Merge all JSONL files with experiment labels
echo ""
echo "  Merging data..."

for file in posts.jsonl comments.jsonl agents.jsonl activity.jsonl; do
  > "$BATCH_DIR/$file"
  for exp in "${EXPERIMENTS[@]}"; do
    RUN_ID=$(basename "$exp" | grep -oE 'run[0-9]+' || echo "unknown")
    if [ -f "$exp/$file" ]; then
      # Add experiment_run field to each JSON line
      jq -c --arg run "$RUN_ID" '. + {experiment_run: $run}' "$exp/$file" \
        >> "$BATCH_DIR/$file" 2>/dev/null || true
    fi
  done
  COUNT=$(wc -l < "$BATCH_DIR/$file" 2>/dev/null || echo "0")
  echo "    $file: $COUNT lines"
done

# Collect all database dumps
mkdir -p "$BATCH_DIR/dumps"
for exp in "${EXPERIMENTS[@]}"; do
  RUN_ID=$(basename "$exp" | grep -oE 'run[0-9]+' || echo "unknown")
  if [ -f "$exp/database.sql" ]; then
    cp "$exp/database.sql" "$BATCH_DIR/dumps/${RUN_ID}-database.sql"
  fi
done

# Merge metadata
echo ""
echo "  Generating batch metadata..."

TOTAL_POSTS=0
TOTAL_COMMENTS=0
TOTAL_DURATION=0

METADATA_ENTRIES=""
for exp in "${EXPERIMENTS[@]}"; do
  if [ -f "$exp/metadata.json" ]; then
    META=$(cat "$exp/metadata.json")
    TOTAL_POSTS=$((TOTAL_POSTS + $(echo "$META" | jq '.posts // 0')))
    TOTAL_COMMENTS=$((TOTAL_COMMENTS + $(echo "$META" | jq '.comments // 0')))
    TOTAL_DURATION=$((TOTAL_DURATION + $(echo "$META" | jq '.duration_minutes // 0')))
    METADATA_ENTRIES="${METADATA_ENTRIES}$(echo "$META" | jq -c '.'),"
  fi
done

# Remove trailing comma
METADATA_ENTRIES="${METADATA_ENTRIES%,}"

cat > "$BATCH_DIR/metadata.json" << EOF
{
  "batch_job_id": "$JOB_ID",
  "num_experiments": ${#EXPERIMENTS[@]},
  "collect_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "totals": {
    "posts": $TOTAL_POSTS,
    "comments": $TOTAL_COMMENTS,
    "total_experiment_minutes": $TOTAL_DURATION
  },
  "experiments": [${METADATA_ENTRIES}]
}
EOF

# Collect logs
mkdir -p "$BATCH_DIR/logs"
for exp in "${EXPERIMENTS[@]}"; do
  RUN_ID=$(basename "$exp" | grep -oE 'run[0-9]+' || echo "unknown")
  mkdir -p "$BATCH_DIR/logs/$RUN_ID"
  cp "$exp"/*.log "$BATCH_DIR/logs/$RUN_ID/" 2>/dev/null || true
done

echo ""
echo "============================================"
echo "  Batch Collection Complete"
echo "============================================"
echo ""
echo "  Output:     $BATCH_DIR"
echo "  Experiments: ${#EXPERIMENTS[@]}"
echo "  Total posts: $TOTAL_POSTS"
echo "  Total comments: $TOTAL_COMMENTS"
echo ""
echo "  Files:"
ls -lh "$BATCH_DIR"/*.jsonl "$BATCH_DIR"/metadata.json 2>/dev/null || true
echo ""
echo "  To copy to your local machine:"
echo "    scp -r $(hostname):$BATCH_DIR ./batch-${JOB_ID}"
echo ""
echo "  To upload to HuggingFace:"
echo "    huggingface-cli upload YOUR_REPO $BATCH_DIR --repo-type dataset"
echo ""

# Also persist batch to $PROJECT
BATCH_BACKUP="$RESULTS_PROJECT/batch-${JOB_ID}"
mkdir -p "$BATCH_BACKUP"
cp "$BATCH_DIR"/*.jsonl "$BATCH_DIR"/metadata.json "$BATCH_BACKUP/" 2>/dev/null || true
echo "  Backed up to: $BATCH_BACKUP (persistent)"
echo ""
