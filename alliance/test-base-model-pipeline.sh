#!/usr/bin/env bash
#
# Quick pipeline test — runs on current node (no GPU needed)
# Uses OpenRouter for both orchestrator and content gen
# 1 agent, 10 min, mag0
#
# Usage: bash alliance/test-base-model-pipeline.sh

set -euo pipefail

PROJECT="${PROJECT:-/project/def-zhijing/anangia}"
SCRATCH="${SCRATCH:-/scratch/anangia}"
CONFIG_DIR="$PROJECT/moltbook/config"
SIF_DIR="$PROJECT/moltbook/images"
RESULTS_DIR="$SCRATCH/moltbook/results/base-model-pipeline-test-$(date +%Y%m%d-%H%M%S)"

# Load config
set -a; source "$CONFIG_DIR/.env"; set +a

OPENROUTER_MODEL="qwen/qwen3.5-35b-a3b"
CONTENT_TOKEN_SECRET="test-hmac-secret-2026"
EXPERIMENT_DURATION="10m"

module load apptainer 2>/dev/null || true
APT_FLAGS="-e -W ${SLURM_TMPDIR:-/tmp}"

# Dynamic ports
PORT_OFFSET=$(( ($$ % 65) * 700 ))
PG_PORT=$(( 5432 + PORT_OFFSET ))
REDIS_PORT=$(( 6379 + PORT_OFFSET ))
API_PORT=$(( 3000 + PORT_OFFSET ))
CONTENT_GEN_PORT=$(( 3002 + PORT_OFFSET ))
AGENT_PORT=$(( 18789 + PORT_OFFSET ))

MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"
CONTENT_GEN_URL="http://localhost:${CONTENT_GEN_PORT}"

WORK="/tmp/moltbook-test-$$"
mkdir -p "$WORK"/{pgdata,pgrun,redisdata,api-logs,agent-data/agent-0,agent-config/agent-0,agent-tmp/agent-0}
# Pre-create canvas dir so OpenClaw doesn't try to build UI (which fails and clobbers config)
mkdir -p "$WORK/agent-data/agent-0/canvas"
mkdir -p "$RESULTS_DIR"

echo "============================================"
echo "  Pipeline Test"
echo "  Ports: PG=$PG_PORT Redis=$REDIS_PORT API=$API_PORT ContentGen=$CONTENT_GEN_PORT"
echo "  Results: $RESULTS_DIR"
echo "============================================"

PIDS=()
cleanup() {
  echo "[CLEANUP] Stopping all..."
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  rm -rf "$WORK"
}
trap cleanup EXIT

# --- 1. PostgreSQL ---
echo "[1/5] PostgreSQL..."
apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  --env PGDATA=/var/lib/postgresql/data \
  "$SIF_DIR/postgres-16.sif" \
  sh -c 'if [ ! -f "$PGDATA/PG_VERSION" ]; then initdb -D "$PGDATA" -U moltbook --auth=trust; fi'

apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  "$SIF_DIR/postgres-16.sif" \
  postgres -D /var/lib/postgresql/data -h localhost -p $PG_PORT -k "" \
  > "$WORK/api-logs/postgres.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 30); do
  apptainer exec $APT_FLAGS \
    -B "$WORK/pgdata:/var/lib/postgresql/data" \
    -B "$WORK/pgrun:/var/run/postgresql" \
    "$SIF_DIR/postgres-16.sif" \
    pg_isready -h localhost -p $PG_PORT -U moltbook 2>/dev/null && break
  [ "$i" -eq 30 ] && { echo "FAIL: postgres"; exit 1; }
  sleep 2
done

apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  "$SIF_DIR/postgres-16.sif" \
  sh -c "createdb -h localhost -p $PG_PORT -U moltbook moltbook 2>/dev/null || true"

apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  -B "$CONFIG_DIR/schema.sql:/tmp/schema.sql:ro" \
  "$SIF_DIR/postgres-16.sif" \
  psql -h localhost -p $PG_PORT -U moltbook -d moltbook -f /tmp/schema.sql > /dev/null 2>&1 || true

echo "  [OK] PG on :$PG_PORT"

# --- 2. Redis ---
echo "[2/5] Redis..."
apptainer exec $APT_FLAGS \
  -B "$WORK/redisdata:/data" \
  "$SIF_DIR/redis-7.sif" \
  redis-server --bind localhost --port $REDIS_PORT --dir /data --daemonize no \
  > "$WORK/api-logs/redis.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 15); do
  apptainer exec $APT_FLAGS \
    "$SIF_DIR/redis-7.sif" \
    redis-cli -h localhost -p $REDIS_PORT ping 2>/dev/null | grep -q PONG && break
  [ "$i" -eq 15 ] && { echo "FAIL: redis"; exit 1; }
  sleep 1
done
echo "  [OK] Redis on :$REDIS_PORT"

# --- 3. API (with content token enforcement) ---
echo "[3/5] API..."
API_PATCHES="$CONFIG_DIR/api-patches"
apptainer exec $APT_FLAGS \
  -B "$API_PATCHES/posts.js:/app/src/routes/posts.js:ro" \
  -B "$API_PATCHES/config-index.js:/app/src/config/index.js:ro" \
  --env PORT=$API_PORT \
  --env NODE_ENV=production \
  --env "DATABASE_URL=postgresql://moltbook:moltbook_password@localhost:${PG_PORT}/moltbook?sslmode=disable" \
  --env "REDIS_URL=redis://localhost:${REDIS_PORT}" \
  --env "JWT_SECRET=pipeline-test" \
  --env "RATE_LIMIT_POSTS_MAX=50" \
  --env "RATE_LIMIT_POSTS_WINDOW=60" \
  --env "RATE_LIMIT_COMMENTS_MAX=1000" \
  --env "RATE_LIMIT_COMMENTS_WINDOW=3600" \
  --env "REQUIRE_CONTENT_TOKEN=true" \
  --env "CONTENT_TOKEN_SECRET=$CONTENT_TOKEN_SECRET" \
  "$SIF_DIR/moltbook-api.sif" \
  node /app/src/index.js \
  > "$WORK/api-logs/api.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 60); do
  curl -s http://localhost:${API_PORT}/api/v1/health > /dev/null 2>&1 && break
  [ "$i" -eq 60 ] && { echo "FAIL: api"; tail -20 "$WORK/api-logs/api.log"; exit 1; }
  sleep 2
done
echo "  [OK] API on :$API_PORT (token enforcement ON)"

# --- 4. Content-gen service (using OpenRouter completions) ---
echo "[4/5] Content-gen service..."
CONTENT_GEN_DIR="$HOME/moltbook/content-gen-service"

# Install deps if needed
if [ ! -d "$CONTENT_GEN_DIR/node_modules" ]; then
  apptainer exec $APT_FLAGS \
    -B "$CONTENT_GEN_DIR:/app/cg:rw" \
    "$SIF_DIR/moltbot-agent.sif" \
    sh -c "cd /app/cg && npm install --omit=dev" 2>/dev/null || true
fi

apptainer exec $APT_FLAGS \
  -B "$CONTENT_GEN_DIR:/app/content-gen:ro" \
  -B "$CONTENT_GEN_DIR/node_modules:/app/content-gen/node_modules:ro" \
  -B "$WORK/api-logs:/data" \
  --env "PORT=$CONTENT_GEN_PORT" \
  --env "BASE_MODEL_API_URL=https://openrouter.ai/api" \
  --env "BASE_MODEL_API_KEY=$OPENROUTER_API_KEY" \
  --env "BASE_MODEL=$OPENROUTER_MODEL" \
  --env "CONTENT_TOKEN_SECRET=$CONTENT_TOKEN_SECRET" \
  --env "AUDIT_LOG_PATH=/data/content-gen-audit.jsonl" \
  --env "TEMPERATURE=0.9" \
  "$SIF_DIR/moltbot-agent.sif" \
  node /app/content-gen/server.js \
  > "$WORK/api-logs/content-gen.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 30); do
  curl -s "http://localhost:${CONTENT_GEN_PORT}/health" > /dev/null 2>&1 && break
  if [ "$i" -eq 30 ]; then
    echo "FAIL: content-gen"
    tail -20 "$WORK/api-logs/content-gen.log" 2>/dev/null
    exit 1
  fi
  sleep 2
done

# End-to-end test: generate -> verify token
echo "  Testing generate-post..."
GEN_RESP=$(curl -s -X POST "http://localhost:${CONTENT_GEN_PORT}/generate-post" \
  -H "Content-Type: application/json" \
  -d '{"context": "", "submolt": "general"}')
GEN_TITLE=$(echo "$GEN_RESP" | jq -r '.title // "FAILED"')
GEN_CONTENT=$(echo "$GEN_RESP" | jq -r '.content // "FAILED"')
GEN_TOKEN=$(echo "$GEN_RESP" | jq -r '.content_token // "NONE"')
echo "  Generated: title='${GEN_TITLE:0:50}' token=${GEN_TOKEN:0:16}..."

if [ "$GEN_TITLE" = "FAILED" ]; then
  echo "FAIL: content generation"
  tail -20 "$WORK/api-logs/content-gen.log"
  exit 1
fi

# Test: post with valid token should succeed
echo "  Testing API token verification..."
REG_RESP=$(curl -s -X POST "$MOLTBOOK_API_URL/agents/register" \
  -H "Content-Type: application/json" \
  -d '{"name": "test_verifier", "description": "Token verification test"}')
TEST_KEY=$(echo "$REG_RESP" | jq -r '.api_key // .agent.api_key // empty')

if [ -n "$TEST_KEY" ]; then
  # Valid token -> should succeed
  POST_RESP=$(curl -s -X POST "$MOLTBOOK_API_URL/posts" \
    -H "Authorization: Bearer $TEST_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg t "$GEN_TITLE" --arg c "$GEN_CONTENT" --arg tk "$GEN_TOKEN" \
      '{submolt:"general", title:$t, content:$c, content_token:$tk}')")
  POST_OK=$(echo "$POST_RESP" | jq -r '.post.id // "FAILED"')
  echo "  Valid token post: $( [ "$POST_OK" != "FAILED" ] && echo "PASS" || echo "FAIL: $POST_RESP")"

  # Tampered content -> should fail
  TAMPER_RESP=$(curl -s -X POST "$MOLTBOOK_API_URL/posts" \
    -H "Authorization: Bearer $TEST_KEY" \
    -H "Content-Type: application/json" \
    -d "$(jq -n --arg tk "$GEN_TOKEN" \
      '{submolt:"general", title:"tampered title", content:"tampered content", content_token:$tk}')")
  TAMPER_ERR=$(echo "$TAMPER_RESP" | jq -r '.error // "none"')
  echo "  Tampered post rejected: $( echo "$TAMPER_ERR" | grep -q 'mismatch' && echo "PASS" || echo "FAIL: $TAMPER_RESP")"

  # No token -> should fail
  NO_TOKEN_RESP=$(curl -s -X POST "$MOLTBOOK_API_URL/posts" \
    -H "Authorization: Bearer $TEST_KEY" \
    -H "Content-Type: application/json" \
    -d '{"submolt":"general", "title":"no token post", "content":"this should fail"}')
  NO_TOKEN_ERR=$(echo "$NO_TOKEN_RESP" | jq -r '.error // "none"')
  echo "  No-token post rejected: $( echo "$NO_TOKEN_ERR" | grep -q 'content_token required' && echo "PASS" || echo "FAIL: $NO_TOKEN_RESP")"
fi

echo "  [OK] Content-gen + token verification working"

# --- 5. Launch agent ---
echo "[5/5] Launching agent_alpha for $EXPERIMENT_DURATION..."

apptainer exec $APT_FLAGS --pid \
  -B "$WORK/agent-data/agent-0:/root/.openclaw" \
  -B "$WORK/agent-config/agent-0:/root/.config/moltbook" \
  -B "$WORK/agent-tmp/agent-0:/tmp/agent" \
  -B "$CONFIG_DIR/souls:/app/generated-souls:ro" \
  -B "$CONFIG_DIR/skills:/app/skills:ro" \
  -B "$CONFIG_DIR/HEARTBEAT-base-model.md:/app/HEARTBEAT.md:ro" \
  -B "$CONFIG_DIR/moltbot-entrypoint.sh:/app/entrypoint.sh:ro" \
  --env "AGENT_NAME=agent_alpha" \
  --env "AGENT_BIO=A balanced AI participant exploring ideas and discussions." \
  --env "SOUL_FILE=agent_alpha-SOUL.md" \
  --env "MOLTBOOK_API_URL=$MOLTBOOK_API_URL" \
  --env "CONTENT_GEN_URL=$CONTENT_GEN_URL" \
  --env "HEARTBEAT_INTERVAL=60s" \
  --env "OPENCLAW_GATEWAY_PORT=$AGENT_PORT" \
  --env "TMPDIR=/tmp/agent" \
  --env "OPENROUTER_API_KEY=$OPENROUTER_API_KEY" \
  --env "OPENROUTER_MODEL=$OPENROUTER_MODEL" \
  --env "OPENCLAW_GATEWAY_TOKEN=moltbook-agent-agent_alpha" \
  "$SIF_DIR/moltbot-agent.sif" \
  /app/entrypoint.sh \
  > "$WORK/api-logs/agent-agent_alpha.log" 2>&1 &
PIDS+=($!)

echo "  [OK] Agent launched"
echo ""
echo "Running for $EXPERIMENT_DURATION... ($(date))"

DURATION_SEC=600
START_TIME=$(date +%s)
LAST_REPORT=0

while true; do
  ELAPSED=$(( $(date +%s) - START_TIME ))
  [ $((DURATION_SEC - ELAPSED)) -le 0 ] && break

  if [ $((ELAPSED - LAST_REPORT)) -ge 30 ] && [ $ELAPSED -gt 0 ]; then
    LAST_REPORT=$ELAPSED
    ALIVE=0; kill -0 "${PIDS[-1]}" 2>/dev/null && ALIVE=1

    API_KEY=$(jq -r '.api_key' "$WORK/agent-config/agent-0/credentials.json" 2>/dev/null || echo "")
    if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
      POSTS=$(curl -s -H "Authorization: Bearer $API_KEY" "$MOLTBOOK_API_URL/posts?limit=1" 2>/dev/null | jq '.pagination.total // 0' 2>/dev/null || echo "?")
    else
      POSTS="?"
    fi
    echo "  [${ELAPSED}s / $((DURATION_SEC - ELAPSED))s left] Agent: $ALIVE  Posts: $POSTS"
  fi
  sleep 10
done

ACTUAL_DURATION=$(( $(date +%s) - START_TIME ))

# --- Export ---
echo ""
echo "Exporting..."

API_KEY=$(jq -r '.api_key' "$WORK/agent-config/agent-0/credentials.json" 2>/dev/null || echo "")
if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
  AUTH="Authorization: Bearer $API_KEY"
  curl -s -H "$AUTH" "$MOLTBOOK_API_URL/agents?limit=100" | jq -c '.data[]' > "$RESULTS_DIR/agents.jsonl" 2>/dev/null || true

  > "$RESULTS_DIR/posts.jsonl"
  OFFSET=0
  while true; do
    RESP=$(curl -s -H "$AUTH" "$MOLTBOOK_API_URL/posts?limit=100&offset=$OFFSET&sort=new")
    POSTS=$(echo "$RESP" | jq -c '.data[]' 2>/dev/null || true)
    [ -z "$POSTS" ] && break
    echo "$POSTS" >> "$RESULTS_DIR/posts.jsonl"
    HAS_MORE=$(echo "$RESP" | jq -r '.pagination.hasMore // false' 2>/dev/null || echo "false")
    [ "$HAS_MORE" != "true" ] && break
    OFFSET=$((OFFSET + 100))
  done

  > "$RESULTS_DIR/comments.jsonl"
  while IFS= read -r post; do
    POST_ID=$(echo "$post" | jq -r '.id')
    [ -n "$POST_ID" ] && [ "$POST_ID" != "null" ] && \
      curl -s -H "$AUTH" "$MOLTBOOK_API_URL/posts/$POST_ID/comments?sort=new&limit=500" \
        | jq -c --arg pid "$POST_ID" 'def flat: . as $c | [$c] + ((.replies // []) | map(flat) | add // []); (.comments // []) | map(flat) | add // [] | .[] | . + {post_id: $pid} | del(.replies)' \
        >> "$RESULTS_DIR/comments.jsonl" 2>/dev/null || true
  done < "$RESULTS_DIR/posts.jsonl"
fi

cp "$WORK/api-logs"/*.log "$RESULTS_DIR/" 2>/dev/null || true
cp "$WORK/api-logs/content-gen-audit.jsonl" "$RESULTS_DIR/audit-log.jsonl" 2>/dev/null || true

POST_N=$(wc -l < "$RESULTS_DIR/posts.jsonl" 2>/dev/null || echo 0)
COMMENT_N=$(wc -l < "$RESULTS_DIR/comments.jsonl" 2>/dev/null || echo 0)
AUDIT_N=$(wc -l < "$RESULTS_DIR/audit-log.jsonl" 2>/dev/null || echo 0)

echo ""
echo "============================================"
echo "  Test Complete"
echo "============================================"
echo "  Duration:     $((ACTUAL_DURATION / 60))m"
echo "  Posts:         $POST_N"
echo "  Comments:      $COMMENT_N"
echo "  Audit entries: $AUDIT_N"
echo "  Results:       $RESULTS_DIR"
echo "============================================"

# Integrity check
echo ""
python3 "$HOME/moltbook/scripts/verify-base-model-integrity.py" "$RESULTS_DIR" --secret "$CONTENT_TOKEN_SECRET" 2>/dev/null || true
