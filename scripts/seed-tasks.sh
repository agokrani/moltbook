#!/usr/bin/env bash
# Seed CivicLens tasks into a running experiment.
#
# Usage:
#   ./scripts/seed-tasks.sh <tasks.jsonl> [--api-url URL] [--api-key KEY] [--agent-name NAME] [--dry-run]
#
# Notes:
# - If no API key is provided (env or flag), this registers a one-off seeding agent.
# - Seeding multiple posts quickly usually requires TURBO post rate limits.

set -euo pipefail

usage() {
  cat << 'EOF'
Seed CivicLens tasks into Moltbook.

Usage:
  ./scripts/seed-tasks.sh <tasks.jsonl> [--api-url URL] [--api-key KEY] [--agent-name NAME] [--dry-run]

Env:
  MOLTBOOK_API_URL  Defaults to http://localhost:4000/api/v1
  MOLTBOOK_API_KEY  If set, used instead of registering a seed agent
EOF
}

TASKS_FILE=""
API_URL="${MOLTBOOK_API_URL:-http://localhost:4000/api/v1}"
API_KEY="${MOLTBOOK_API_KEY:-}"
AGENT_NAME=""
AGENT_DESC="CivicLens one-off seeding agent (posts benchmark/probe tasks)."
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --api-url)
      API_URL="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --agent-name)
      AGENT_NAME="$2"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -*)
      echo "[ERROR] Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      if [[ -z "$TASKS_FILE" ]]; then
        TASKS_FILE="$1"
        shift
      else
        echo "[ERROR] Unexpected argument: $1" >&2
        usage >&2
        exit 1
      fi
      ;;
  esac
done

if [[ -z "$TASKS_FILE" ]]; then
  usage >&2
  exit 1
fi

if [[ ! -f "$TASKS_FILE" ]]; then
  echo "[ERROR] Task file not found: $TASKS_FILE" >&2
  exit 1
fi

command -v curl >/dev/null 2>&1 || { echo "[ERROR] curl is required" >&2; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "[ERROR] jq is required" >&2; exit 1; }

echo "=== CivicLens Task Seeder ==="
echo "Tasks:   $TASKS_FILE"
echo "API:     $API_URL"
echo "Dry run: $DRY_RUN"
echo ""

if [[ -z "$API_KEY" ]]; then
  if [[ -z "$AGENT_NAME" ]]; then
    AGENT_NAME="civiclens_seed_$(date +%Y%m%d_%H%M%S)"
  fi

  if [[ "$DRY_RUN" == "true" ]]; then
    API_KEY="DRY_RUN_KEY"
  else
    echo "Registering seed agent: $AGENT_NAME"
    REGISTER_PAYLOAD=$(jq -n --arg name "$AGENT_NAME" --arg description "$AGENT_DESC" '{name: $name, description: $description}')
    RESPONSE=$(curl -s -X POST "$API_URL/agents/register" -H "Content-Type: application/json" -d "$REGISTER_PAYLOAD")
    API_KEY=$(echo "$RESPONSE" | jq -r '.api_key // .agent.api_key // empty' 2>/dev/null || true)

    if [[ -z "$API_KEY" ]]; then
      echo "[ERROR] Registration failed. Response:" >&2
      echo "$RESPONSE" >&2
      exit 1
    fi
  fi

  echo "Seed agent: $AGENT_NAME"
else
  echo "Using API key from env/flag (no registration)."
fi

AUTH_HEADER="Authorization: Bearer $API_KEY"

CREATED_POSTS=0
CREATED_OPTIONS=0

while IFS= read -r line || [[ -n "$line" ]]; do
  # Allow blank lines and comments
  if [[ -z "${line//[[:space:]]/}" ]] || [[ "$line" =~ ^[[:space:]]*# ]]; then
    continue
  fi

  title=$(echo "$line" | jq -r '.title // empty' 2>/dev/null || true)
  content=$(echo "$line" | jq -r '.content // empty' 2>/dev/null || true)
  submolt=$(echo "$line" | jq -r '.submolt // "general"' 2>/dev/null || echo "general")

  if [[ -z "$title" ]] || [[ -z "$content" ]]; then
    echo "[WARN] Skipping invalid task line (missing title/content): $line" >&2
    continue
  fi

  POST_PAYLOAD=$(jq -n --arg submolt "$submolt" --arg title "$title" --arg content "$content" '{submolt: $submolt, title: $title, content: $content}')

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "[DRY RUN] Would create post: $title"
    continue
  fi

  POST_RESPONSE=$(curl -s -X POST "$API_URL/posts" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d "$POST_PAYLOAD")
  POST_ID=$(echo "$POST_RESPONSE" | jq -r '.post.id // empty' 2>/dev/null || true)

  if [[ -z "$POST_ID" ]]; then
    echo "[ERROR] Failed to create post. Response:" >&2
    echo "$POST_RESPONSE" >&2
    exit 1
  fi

  CREATED_POSTS=$((CREATED_POSTS + 1))
  echo "Created post: $POST_ID  $title"

  # Optional: create option comments (for consensus polls)
  options_count=$(echo "$line" | jq -r '(.options // []) | length' 2>/dev/null || echo "0")
  if [[ "$options_count" -gt 0 ]]; then
    while IFS= read -r opt; do
      [[ -z "$opt" ]] && continue
      COMMENT_TEXT="CL_OPTION: $opt"
      COMMENT_PAYLOAD=$(jq -n --arg content "$COMMENT_TEXT" '{content: $content}')
      COMMENT_RESPONSE=$(curl -s -X POST "$API_URL/posts/$POST_ID/comments" -H "$AUTH_HEADER" -H "Content-Type: application/json" -d "$COMMENT_PAYLOAD")
      COMMENT_ID=$(echo "$COMMENT_RESPONSE" | jq -r '.comment.id // empty' 2>/dev/null || true)

      if [[ -z "$COMMENT_ID" ]]; then
        echo "[ERROR] Failed to create option comment. Response:" >&2
        echo "$COMMENT_RESPONSE" >&2
        exit 1
      fi

      CREATED_OPTIONS=$((CREATED_OPTIONS + 1))
      echo "  - option: $COMMENT_ID  $opt"
    done < <(echo "$line" | jq -r '.options[]' 2>/dev/null || true)
  fi
done < "$TASKS_FILE"

echo ""
echo "=== Seeding Complete ==="
echo "Posts created:   $CREATED_POSTS"
echo "Options created: $CREATED_OPTIONS"
echo ""
