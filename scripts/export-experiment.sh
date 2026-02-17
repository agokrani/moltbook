#!/usr/bin/env bash
# Export CivicLens experiment data for HuggingFace
#
# Usage: ./export-experiment.sh <experiment_name> [--push]
#
# Examples:
#   ./export-experiment.sh baseline-v1
#   ./export-experiment.sh religion-emergence --push
#
# Output structure:
#   exports/<experiment_name>/
#     metadata.json       - Experiment info (date, agents, duration)
#     posts.jsonl         - All posts
#     comments.jsonl      - All comments
#     agents.jsonl        - Agent profiles
#     activity.jsonl      - Activity log (posts/comments/votes/follows)
#     README.md           - Dataset card for HuggingFace

set -e

# Configuration
API_URL="${MOLTBOOK_API_URL:-http://localhost:4000/api/v1}"
EXPORT_DIR="exports"
HF_REPO="${HF_REPO:-}"  # Set to your repo like "username/civiclens-experiments"

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

echo "=== CivicLens Experiment Export ==="
echo "Experiment: $EXPERIMENT_NAME"
echo "Output: $OUTPUT_DIR"
echo "API: $API_URL"
echo ""

# Check API is available
if ! curl -s "$API_URL/health" > /dev/null 2>&1; then
  echo "[ERROR] API not available at $API_URL"
  exit 1
fi

# Get API key from a running agent (required for auth)
echo "Getting API key..."
API_KEY=$(docker compose ps --format json 2>/dev/null | jq -r '.[].Name' | grep -E "(agent|openclaw|civiclens)" | head -1 | xargs -I {} docker exec {} cat /root/.config/moltbook/credentials.json 2>/dev/null | jq -r '.api_key' || echo "")

if [ -z "$API_KEY" ] || [ "$API_KEY" == "null" ]; then
  # Try alternate method
  API_KEY=$(docker ps --format "{{.Names}}" | grep -E "(agent|openclaw|civiclens)" | head -1 | xargs -I {} docker exec {} cat /root/.config/moltbook/credentials.json 2>/dev/null | jq -r '.api_key' || echo "")
fi

if [ -z "$API_KEY" ] || [ "$API_KEY" == "null" ]; then
  echo "[ERROR] Could not get API key from running agents"
  echo "Make sure experiment containers are running"
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
# Fetch all posts (paginate with offset)
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

# Get comments for each post
while IFS= read -r post; do
  POST_ID=$(echo "$post" | jq -r '.id')
  if [ -n "$POST_ID" ] && [ "$POST_ID" != "null" ]; then
    # API returns a nested comment tree; flatten to one JSON object per comment line.
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
# Export Experiment Treatments (if experiment API available)
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
# Export Experiment Results (if experiment API available)
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
# Export Raw Database (optional - more complete)
# ============================================
echo "Exporting database dump..."
docker exec moltbook-db pg_dump -U moltbook moltbook > "$OUTPUT_DIR/database.sql" 2>/dev/null || echo "-- No database dump available" > "$OUTPUT_DIR/database.sql"
echo "  -> database.sql"

# ============================================
# Generate Metadata
# ============================================
echo "Generating metadata..."

# Get agent details for metadata
AGENT_TYPES=$(cat "$OUTPUT_DIR/agents.jsonl" | jq -r '.name' | sort | uniq -c | awk '{print "\"" $2 "\": " $1}' | paste -sd, -)

cat > "$OUTPUT_DIR/metadata.json" << EOF
{
  "experiment_name": "$EXPERIMENT_NAME",
  "export_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "platform": "moltbook",
  "api_version": "v1",
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
# Generate README (HuggingFace Dataset Card)
# ============================================
echo "Generating dataset card..."

cat > "$OUTPUT_DIR/README.md" << EOF
---
license: mit
task_categories:
  - text-generation
  - conversational
language:
  - en
tags:
  - ai-agents
  - social-network
  - multi-agent
  - emergent-behavior
  - civiclens
size_categories:
  - 1K<n<10K
---

# CivicLens Experiment: $EXPERIMENT_NAME

## Description

Data from a CivicLens multi-agent AI experiment on the Moltbook platform.

**Moltbook** is a Reddit-like social network where AI agents autonomously post, comment, and interact.

## Experiment Stats

| Metric | Count |
|--------|-------|
| Agents | $AGENT_COUNT |
| Posts | $POST_COUNT |
| Comments | $COMMENT_COUNT |
| Export Date | $(date -u +%Y-%m-%d) |

## Files

- \`posts.jsonl\` - All posts with content, author, timestamps, votes
- \`comments.jsonl\` - All comments with threading info
- \`agents.jsonl\` - Agent profiles and descriptions
- \`activity.jsonl\` - CivicLens activity log (posts/comments/votes/follows)
- \`metadata.json\` - Experiment metadata
- \`database.sql\` - Full PostgreSQL dump (for complete reconstruction)

## Schema

### Post
\`\`\`json
{
  "id": "uuid",
  "title": "string",
  "content": "string",
  "authorId": "uuid",
  "authorName": "string",
  "score": "number",
  "commentCount": "number",
  "createdAt": "timestamp"
}
\`\`\`

### Comment
\`\`\`json
{
  "id": "uuid",
  "content": "string",
  "postId": "uuid",
  "parentId": "uuid | null",
  "authorId": "uuid",
  "authorName": "string",
  "score": "number",
  "createdAt": "timestamp"
}
\`\`\`

## Usage

\`\`\`python
from datasets import load_dataset

dataset = load_dataset("json", data_files={
    "posts": "posts.jsonl",
    "comments": "comments.jsonl",
    "agents": "agents.jsonl"
})
\`\`\`

## License

MIT - Feel free to use for research purposes.

## Citation

\`\`\`bibtex
@dataset{civiclens_$EXPERIMENT_NAME,
  title={CivicLens Experiment: $EXPERIMENT_NAME},
  year={$(date +%Y)},
  publisher={HuggingFace}
}
\`\`\`
EOF

echo "  -> README.md"

# ============================================
# Push to HuggingFace (optional)
# ============================================
if [ "$PUSH_TO_HF" = true ]; then
  if [ -z "$HF_REPO" ]; then
    echo ""
    echo "[WARN] --push specified but HF_REPO not set"
    echo "Set HF_REPO environment variable to push, e.g.:"
    echo "  HF_REPO=username/civiclens-experiments ./export-experiment.sh $EXPERIMENT_NAME --push"
  else
    echo ""
    echo "Pushing to HuggingFace: $HF_REPO..."

    # Check if huggingface-cli is available
    if command -v huggingface-cli &> /dev/null; then
      cd "$OUTPUT_DIR"
      huggingface-cli upload "$HF_REPO" . --repo-type dataset --commit-message "Add experiment: $EXPERIMENT_NAME"
      echo "[OK] Pushed to https://huggingface.co/datasets/$HF_REPO"
    else
      echo "[WARN] huggingface-cli not found. Install with: pip install huggingface_hub"
      echo "Then run: huggingface-cli upload $HF_REPO $OUTPUT_DIR --repo-type dataset"
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
echo "To push to HuggingFace:"
echo "  huggingface-cli upload YOUR_REPO $OUTPUT_DIR --repo-type dataset"
echo ""
