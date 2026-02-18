#!/usr/bin/env bash
# Export CivicLens experiment data — parallel-safe version
#
# Uses COMPOSE_PROJECT_NAME to scope container discovery to the correct
# parallel slot. Requires the parallel compose files.
#
# Usage:
#   COMPOSE_PROJECT_NAME=slot0 HOST_API_PORT=4000 \
#     ./scripts/export-experiment-parallel.sh <experiment_name>
#
# Environment variables (set by run-experiment-parallel.sh):
#   COMPOSE_PROJECT_NAME  — Docker project name for this slot
#   HOST_API_PORT         — Host port the API is mapped to (default 4000)

set -e

# Configuration
HOST_API_PORT="${HOST_API_PORT:-4000}"
API_URL="${MOLTBOOK_API_URL:-http://localhost:${HOST_API_PORT}/api/v1}"

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
EXPORT_DIR="$PROJECT_DIR/exports"
COMPOSE_BASE="docker-compose.parallel.yml"
COMPOSE_RANKING="docker-compose.civiclens-ranking-parallel.yml"

# Build compose command — use --env-file if a slot env file exists for this project
SLOT_ENV_FILE="${SLOT_ENV_FILE:-}"
ENV_FILE_FLAG=""
if [ -n "$SLOT_ENV_FILE" ] && [ -f "$SLOT_ENV_FILE" ]; then
  ENV_FILE_FLAG="--env-file $SLOT_ENV_FILE"
fi
COMPOSE_CMD="docker compose -p ${COMPOSE_PROJECT_NAME:-moltbook} $ENV_FILE_FLAG -f $PROJECT_DIR/$COMPOSE_BASE -f $PROJECT_DIR/$COMPOSE_RANKING"

# Parse arguments
EXPERIMENT_NAME="${1:-experiment-$(date +%Y%m%d-%H%M%S)}"
PUSH_TO_HF=false

for arg in "$@"; do
  case $arg in
    --push) PUSH_TO_HF=true ;;
  esac
done

OUTPUT_DIR="$EXPORT_DIR/$EXPERIMENT_NAME"
mkdir -p "$OUTPUT_DIR"

echo "=== CivicLens Experiment Export (parallel) ==="
echo "Experiment: $EXPERIMENT_NAME"
echo "Project:    ${COMPOSE_PROJECT_NAME:-moltbook}"
echo "Output:     $OUTPUT_DIR"
echo "API:        $API_URL"
echo ""

# Check API is available
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
  echo "[ERROR] API not available at $API_URL"
  exit 1
fi

# Get API key from a running agent scoped to this compose project
echo "Getting API key..."
API_KEY=""

# Method 1: Use docker compose ps to find containers in this project
AGENT_CONTAINER=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep -E "(ranking|agent|civiclens)" | head -1 || true)

if [ -n "$AGENT_CONTAINER" ]; then
  API_KEY=$(docker exec "$AGENT_CONTAINER" cat /root/.config/moltbook/credentials.json 2>/dev/null | jq -r '.api_key' || echo "")
fi

# Method 2: Fallback — use compose exec on the first agent service
if [ -z "$API_KEY" ] || [ "$API_KEY" == "null" ]; then
  API_KEY=$($COMPOSE_CMD exec -T civiclens-ranking-1 cat /root/.config/moltbook/credentials.json 2>/dev/null | jq -r '.api_key' || echo "")
fi

if [ -z "$API_KEY" ] || [ "$API_KEY" == "null" ]; then
  echo "[ERROR] Could not get API key from running agents"
  echo "Make sure experiment containers are running (project: ${COMPOSE_PROJECT_NAME:-moltbook})"
  exit 1
fi

echo "  Got API key: ${API_KEY:0:20}..."
AUTH_HEADER="Authorization: Bearer $API_KEY"

# ============================================
# Export Agents
# ============================================
echo "Exporting agents..."
> "$OUTPUT_DIR/agents.jsonl"
AGENT_OFFSET=0
AGENT_LIMIT=100

while true; do
  RESPONSE=$(curl -s -H "$AUTH_HEADER" "$API_URL/agents?limit=$AGENT_LIMIT&offset=$AGENT_OFFSET&sort=newest")
  AGENTS=$(echo "$RESPONSE" | jq -c '.data[]' 2>/dev/null || true)

  if [ -z "$AGENTS" ]; then
    break
  fi

  echo "$AGENTS" >> "$OUTPUT_DIR/agents.jsonl"

  HAS_MORE=$(echo "$RESPONSE" | jq -r '.pagination.hasMore // false' 2>/dev/null || echo "false")
  if [ "$HAS_MORE" != "true" ]; then
    break
  fi

  AGENT_OFFSET=$((AGENT_OFFSET + AGENT_LIMIT))
done

AGENT_COUNT=$(wc -l < "$OUTPUT_DIR/agents.jsonl" | tr -d ' ')
echo "  -> $AGENT_COUNT agents"

# ============================================
# Export Posts
# ============================================
echo "Exporting posts..."
OFFSET=0
LIMIT=100
> "$OUTPUT_DIR/posts.jsonl"

while true; do
  RESPONSE=$(curl -s -H "$AUTH_HEADER" "$API_URL/posts?limit=$LIMIT&offset=$OFFSET&sort=new")
  POSTS=$(echo "$RESPONSE" | jq -c '.data[]' 2>/dev/null)

  if [ -z "$POSTS" ] || [ "$POSTS" == "" ]; then
    break
  fi

  echo "$POSTS" >> "$OUTPUT_DIR/posts.jsonl"

  HAS_MORE=$(echo "$RESPONSE" | jq -r '.pagination.hasMore // false' 2>/dev/null)
  if [ "$HAS_MORE" != "true" ]; then
    break
  fi

  OFFSET=$((OFFSET + LIMIT))
done

POST_COUNT=$(wc -l < "$OUTPUT_DIR/posts.jsonl" | tr -d ' ')
echo "  -> $POST_COUNT posts"

# ============================================
# Export Comments
# ============================================
echo "Exporting comments..."
> "$OUTPUT_DIR/comments.jsonl"

while IFS= read -r post; do
  POST_ID=$(echo "$post" | jq -r '.id')
  if [ -n "$POST_ID" ] && [ "$POST_ID" != "null" ]; then
    curl -s -H "$AUTH_HEADER" "$API_URL/posts/$POST_ID/comments?sort=new&limit=500" \
      | jq -c --arg post_id "$POST_ID" '
          def flat:
            . as $c
            | [$c] + ((.replies // []) | map(. | flat) | add // []);
          (.comments // [])
          | map(. | flat) | add // []
          | .[]
          | . + {post_id: $post_id}
          | del(.replies)
        ' 2>/dev/null >> "$OUTPUT_DIR/comments.jsonl" || true
  fi
done < "$OUTPUT_DIR/posts.jsonl"

COMMENT_COUNT=$(wc -l < "$OUTPUT_DIR/comments.jsonl" | tr -d ' ')
echo "  -> $COMMENT_COUNT comments"

# ============================================
# Export Activity Log (CivicLens)
# ============================================
echo "Exporting activity log..."
> "$OUTPUT_DIR/activity.jsonl"

ACTIVITY_OFFSET=0
ACTIVITY_LIMIT=1000

while true; do
  RESPONSE=$(curl -s -H "$AUTH_HEADER" "$API_URL/analytics/activity?limit=$ACTIVITY_LIMIT&offset=$ACTIVITY_OFFSET")
  EVENTS=$(echo "$RESPONSE" | jq -c '.activities[]' 2>/dev/null || true)

  if [ -z "$EVENTS" ]; then
    break
  fi

  echo "$EVENTS" >> "$OUTPUT_DIR/activity.jsonl"

  COUNT=$(echo "$RESPONSE" | jq -r '.count // 0' 2>/dev/null || echo "0")
  if [ "$COUNT" -lt "$ACTIVITY_LIMIT" ]; then
    break
  fi

  ACTIVITY_OFFSET=$((ACTIVITY_OFFSET + ACTIVITY_LIMIT))
done

ACTIVITY_COUNT=$(wc -l < "$OUTPUT_DIR/activity.jsonl" | tr -d ' ')
echo "  -> $ACTIVITY_COUNT events"

# ============================================
# Export Experiment Treatments
# ============================================
echo "Exporting experiment treatments..."
TREATMENT_RESPONSE=$(curl -s -H "$AUTH_HEADER" "$API_URL/experiment/treatments?limit=10000" 2>/dev/null || echo "")
if echo "$TREATMENT_RESPONSE" | jq -e '.data' > /dev/null 2>&1; then
  echo "$TREATMENT_RESPONSE" | jq -c '.data[]' > "$OUTPUT_DIR/treatments.jsonl" 2>/dev/null || true
  TREATMENT_COUNT=$(wc -l < "$OUTPUT_DIR/treatments.jsonl" | tr -d ' ')
  echo "  -> $TREATMENT_COUNT treatments"
else
  echo "  -> No experiment treatments (experiment may not be enabled)"
  TREATMENT_COUNT=0
fi

# ============================================
# Export Experiment Results
# ============================================
echo "Exporting experiment results..."
RESULTS_RESPONSE=$(curl -s -H "$AUTH_HEADER" "$API_URL/experiment/results" 2>/dev/null || echo "")
if echo "$RESULTS_RESPONSE" | jq -e '.results' > /dev/null 2>&1; then
  echo "$RESULTS_RESPONSE" | jq '.' > "$OUTPUT_DIR/experiment_results.json" 2>/dev/null || true
  RESULT_COUNT=$(echo "$RESULTS_RESPONSE" | jq '.results | length' 2>/dev/null || echo "0")
  echo "  -> $RESULT_COUNT results"
else
  echo "  -> No experiment results (experiment may not be enabled)"
fi

# ============================================
# Export Raw Database (project-scoped)
# ============================================
echo "Exporting database dump..."
PG_CONTAINER=$($COMPOSE_CMD ps --format json 2>/dev/null | jq -r 'if type == "array" then .[] else . end | .Name // .name // empty' 2>/dev/null | grep "postgres" | head -1 || true)

if [ -n "$PG_CONTAINER" ]; then
  docker exec "$PG_CONTAINER" pg_dump -U moltbook moltbook > "$OUTPUT_DIR/database.sql" 2>/dev/null || echo "-- No database dump available" > "$OUTPUT_DIR/database.sql"
else
  # Fallback: use compose exec
  $COMPOSE_CMD exec -T postgres pg_dump -U moltbook moltbook > "$OUTPUT_DIR/database.sql" 2>/dev/null || echo "-- No database dump available" > "$OUTPUT_DIR/database.sql"
fi
echo "  -> database.sql"

# ============================================
# Generate Metadata
# ============================================
echo "Generating metadata..."

cat > "$OUTPUT_DIR/metadata.json" << EOF
{
  "experiment_name": "$EXPERIMENT_NAME",
  "export_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platform": "moltbook",
  "api_version": "v1",
  "compose_project": "${COMPOSE_PROJECT_NAME:-moltbook}",
  "stats": {
    "agents": $AGENT_COUNT,
    "posts": $POST_COUNT,
    "comments": $COMMENT_COUNT,
    "activity_events": $ACTIVITY_COUNT
  },
  "agents": [$(cat "$OUTPUT_DIR/agents.jsonl" | jq -c '{name: .name, description: .description}' | paste -sd, -)]
}
EOF

echo "  -> metadata.json"

# ============================================
# Push to HuggingFace (optional)
# ============================================
if [ "$PUSH_TO_HF" = true ]; then
  if [ -z "$HF_REPO" ]; then
    echo ""
    echo "[WARN] --push specified but HF_REPO not set"
  else
    echo ""
    echo "Pushing to HuggingFace: $HF_REPO..."
    if command -v huggingface-cli &> /dev/null; then
      cd "$OUTPUT_DIR"
      huggingface-cli upload "$HF_REPO" . --repo-type dataset --commit-message "Add experiment: $EXPERIMENT_NAME"
      echo "[OK] Pushed to https://huggingface.co/datasets/$HF_REPO"
    else
      echo "[WARN] huggingface-cli not found. Install with: pip install huggingface_hub"
    fi
  fi
fi

# ============================================
# Summary
# ============================================
echo ""
echo "=== Export Complete ==="
echo "Location: $OUTPUT_DIR"
echo ""
echo "Files:"
ls -lh "$OUTPUT_DIR"
echo ""
