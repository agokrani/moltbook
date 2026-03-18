#!/usr/bin/env bash
#SBATCH --job-name=base-model-test
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --time=1:30:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=80G
#SBATCH --gres=gpu:h100:1
#SBATCH --account=def-zhijing
#SBATCH --signal=B:USR1@120
#
# Base Model Experiment — Test Run
#
# 1 agent, 10 minutes, mag0 (empty feed)
# Self-hosted Qwen3.5-35B-A3B-Base via vLLM on H100
# Orchestrator: Qwen 3.5 35B A3B (instruct) via OpenRouter
#
# Submit: sbatch alliance/slurm-base-model-test.sh

set -euo pipefail

# ============================================
# Configuration
# ============================================
PROJECT="${PROJECT:-/project/def-zhijing/anangia}"
SCRATCH="${SCRATCH:-/scratch/anangia}"

CONFIG_DIR="$PROJECT/moltbook/config"
SIF_DIR="$PROJECT/moltbook/images"
RESULTS_SCRATCH="$SCRATCH/moltbook/results"
RESULTS_PROJECT="$PROJECT/moltbook/results"

# Load user config (API keys)
if [ -f "$CONFIG_DIR/.env" ]; then
  set -a; source "$CONFIG_DIR/.env"; set +a
fi

# Test parameters
NUM_AGENTS=1
HEARTBEAT_INTERVAL="60s"
EXPERIMENT_DURATION="10m"
CONDITION="mag0"
EXPERIMENT_NAME="base-model-test-${SLURM_JOB_ID:-local}"
RESULTS_DIR="$RESULTS_SCRATCH/$EXPERIMENT_NAME"

# Base model config
BASE_MODEL="Qwen/Qwen3.5-35B-A3B-Base"
BASE_MODEL_CACHE="$SCRATCH/hf-cache"
VLLM_ENV="$SCRATCH/envs/vllm"
CONTENT_TOKEN_SECRET="test-hmac-secret-2026"

# Override orchestrator model to Qwen 3.5
OPENROUTER_MODEL="qwen/qwen3.5-35b-a3b"

# Rate limits (relaxed for testing)
RATE_LIMIT_POSTS_MAX=50
RATE_LIMIT_POSTS_WINDOW=60

WORK="${SLURM_TMPDIR:-/tmp}/moltbook"

echo "============================================"
echo "  Base Model Test: $EXPERIMENT_NAME"
echo "  Node: $(hostname)"
echo "  GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo 'unknown')"
echo "  Orchestrator: $OPENROUTER_MODEL (OpenRouter)"
echo "  Base model: $BASE_MODEL (local vLLM)"
echo "  Duration: $EXPERIMENT_DURATION"
echo "  Agents: $NUM_AGENTS"
echo "============================================"
echo ""

# ============================================
# Dynamic ports
# ============================================
PORT_OFFSET=$(( (${SLURM_JOB_ID:-$$} % 65) * 700 ))
PG_PORT=$(( 5432 + PORT_OFFSET ))
REDIS_PORT=$(( 6379 + PORT_OFFSET ))
API_PORT=$(( 3000 + PORT_OFFSET ))
VLLM_PORT=$(( 8000 + PORT_OFFSET ))
CONTENT_GEN_PORT=$(( 3002 + PORT_OFFSET ))
AGENT_PORT_BASE=$(( 18789 + PORT_OFFSET ))

MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"
VLLM_URL="http://localhost:${VLLM_PORT}"
CONTENT_GEN_URL="http://localhost:${CONTENT_GEN_PORT}"

echo "  Ports: PG=$PG_PORT Redis=$REDIS_PORT API=$API_PORT vLLM=$VLLM_PORT ContentGen=$CONTENT_GEN_PORT"

# Track PIDs
PIDS=()

# Setup directories
mkdir -p "$WORK"/{pgdata,pgrun,redisdata,api-logs,agent-data/agent-0,agent-config/agent-0,agent-tmp/agent-0}
mkdir -p "$RESULTS_DIR/checkpoints"

# Load modules
module load apptainer 2>/dev/null || true
module load python/3.11.5 2>/dev/null || module load python/3.10.13 2>/dev/null || true
module load cuda/12.6 2>/dev/null || module load cuda/12.2 2>/dev/null || true

APT_FLAGS="-e -W ${SLURM_TMPDIR:-/tmp}"

# Validate SIF images
for img in postgres-16.sif redis-7.sif moltbook-api.sif moltbot-agent.sif; do
  if [ ! -f "$SIF_DIR/$img" ]; then
    echo "[ERROR] Missing: $SIF_DIR/$img"
    exit 1
  fi
done

# Overwrite guard
if [ -d "$RESULTS_DIR" ] && [ -f "$RESULTS_DIR/metadata.json" ]; then
  echo "[ERROR] Results already exist: $RESULTS_DIR"
  exit 1
fi

# Duration helpers
duration_to_seconds() {
  local d=$1 num=${d%[smhd]} unit=${d: -1}
  case $unit in s) echo "$num" ;; m) echo $((num * 60)) ;; h) echo $((num * 3600)) ;; *) echo "$num" ;; esac
}

# ============================================
# Export + metadata helpers (from main script)
# ============================================
export_data() {
  local EXPORT_LABEL="${1:-final}"
  echo "[EXPORT:$EXPORT_LABEL] Saving experiment data..."

  local API_KEY=""
  local CREDS="$WORK/agent-config/agent-0/credentials.json"
  if [ -f "$CREDS" ]; then
    API_KEY=$(jq -r '.api_key' "$CREDS" 2>/dev/null || true)
  fi

  if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
    local AUTH="Authorization: Bearer $API_KEY"

    curl -s -H "$AUTH" "$MOLTBOOK_API_URL/agents?limit=100" \
      | jq -c '.data[]' > "$RESULTS_DIR/agents.jsonl" 2>/dev/null || true

    local OFFSET=0
    > "$RESULTS_DIR/posts.jsonl"
    while true; do
      local RESP=$(curl -s -H "$AUTH" "$MOLTBOOK_API_URL/posts?limit=100&offset=$OFFSET&sort=new")
      local POSTS=$(echo "$RESP" | jq -c '.data[]' 2>/dev/null || true)
      [ -z "$POSTS" ] && break
      echo "$POSTS" >> "$RESULTS_DIR/posts.jsonl"
      local HAS_MORE=$(echo "$RESP" | jq -r '.pagination.hasMore // false' 2>/dev/null || echo "false")
      [ "$HAS_MORE" != "true" ] && break
      OFFSET=$((OFFSET + 100))
    done

    > "$RESULTS_DIR/comments.jsonl"
    while IFS= read -r post; do
      local POST_ID=$(echo "$post" | jq -r '.id')
      if [ -n "$POST_ID" ] && [ "$POST_ID" != "null" ]; then
        curl -s -H "$AUTH" "$MOLTBOOK_API_URL/posts/$POST_ID/comments?sort=new&limit=500" \
          | jq -c --arg pid "$POST_ID" '
              def flat: . as $c | [$c] + ((.replies // []) | map(flat) | add // []);
              (.comments // []) | map(flat) | add // [] | .[] | . + {post_id: $pid} | del(.replies)
            ' >> "$RESULTS_DIR/comments.jsonl" 2>/dev/null || true
      fi
    done < "$RESULTS_DIR/posts.jsonl"
  fi

  apptainer exec $APT_FLAGS \
    -B "$WORK/pgdata:/var/lib/postgresql/data" \
    -B "$WORK/pgrun:/var/run/postgresql" \
    "$SIF_DIR/postgres-16.sif" \
    pg_dump -h localhost -p $PG_PORT -U moltbook moltbook \
    > "$RESULTS_DIR/database-${EXPORT_LABEL}.sql" 2>/dev/null || true

  # Copy audit log from content-gen service
  cp "$WORK/api-logs/content-gen-audit.jsonl" "$RESULTS_DIR/audit-log.jsonl" 2>/dev/null || true
  cp "$WORK/api-logs"/*.log "$RESULTS_DIR/" 2>/dev/null || true
}

write_metadata() {
  local LABEL="${1:-final}"
  local POST_N=$(wc -l < "$RESULTS_DIR/posts.jsonl" 2>/dev/null || echo 0)
  local COMMENT_N=$(wc -l < "$RESULTS_DIR/comments.jsonl" 2>/dev/null || echo 0)
  cat > "$RESULTS_DIR/metadata.json" << METAEOF
{
  "experiment_name": "$EXPERIMENT_NAME",
  "job_id": "${SLURM_JOB_ID:-local}",
  "node": "$(hostname)",
  "cluster": "fir",
  "condition": "$CONDITION",
  "export_type": "$LABEL",
  "export_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "duration_minutes": $((ACTUAL_DURATION / 60)),
  "num_agents": $NUM_AGENTS,
  "heartbeat_interval": "$HEARTBEAT_INTERVAL",
  "orchestrator_model": "$OPENROUTER_MODEL",
  "base_model": "$BASE_MODEL",
  "experiment_type": "base-model-content-gen",
  "stats": {
    "posts": $POST_N,
    "comments": $COMMENT_N
  }
}
METAEOF
}

persist_to_project() {
  local DEST="$RESULTS_PROJECT/$EXPERIMENT_NAME"
  mkdir -p "$DEST"
  cp -r "$RESULTS_DIR"/* "$DEST/" 2>/dev/null || true
  echo "  [PERSIST] Backed up to $DEST"
}

# Signal handling
SHUTTING_DOWN=false
graceful_shutdown() {
  if [ "$SHUTTING_DOWN" = true ]; then return; fi
  SHUTTING_DOWN=true
  echo "[SIGNAL] Emergency export..."
  ACTUAL_DURATION=$(( $(date +%s) - ${START_TIME:-$(date +%s)} ))
  export_data "emergency"
  write_metadata "emergency"
  persist_to_project
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  exit 0
}
trap graceful_shutdown USR1 TERM
trap 'for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done; wait 2>/dev/null || true' EXIT

# ============================================
# 1. Setup vLLM virtualenv (cached on $SCRATCH)
# ============================================
echo "[1/7] Setting up vLLM..."

if [ ! -f "$VLLM_ENV/bin/activate" ]; then
  echo "  Creating virtualenv at $VLLM_ENV..."
  python3 -m venv --system-site-packages "$VLLM_ENV"
  source "$VLLM_ENV/bin/activate"
  pip install --no-cache-dir --upgrade pip
  pip install --no-cache-dir vllm
  deactivate
  echo "  [OK] vLLM installed"
else
  echo "  [OK] Using cached vLLM env"
fi

source "$VLLM_ENV/bin/activate"
echo "  vLLM version: $(python3 -c 'import vllm; print(vllm.__version__)' 2>/dev/null || echo 'checking...')"

# ============================================
# 2. Download model if not cached
# ============================================
echo ""
echo "[2/7] Checking base model..."

export HF_HOME="$BASE_MODEL_CACHE"
export TRANSFORMERS_CACHE="$BASE_MODEL_CACHE"

MODEL_DIR="$BASE_MODEL_CACHE/hub/models--Qwen--Qwen3.5-35B-A3B-Base"
if [ -d "$MODEL_DIR" ]; then
  echo "  [OK] Model already cached at $MODEL_DIR"
else
  echo "  Downloading $BASE_MODEL (this may take a while)..."
  python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('$BASE_MODEL', cache_dir='$BASE_MODEL_CACHE')
print('  [OK] Model downloaded')
"
fi

# ============================================
# 3. Start vLLM server
# ============================================
echo ""
echo "[3/7] Starting vLLM server on port $VLLM_PORT..."

python3 -m vllm.entrypoints.openai.api_server \
  --model "$BASE_MODEL" \
  --download-dir "$BASE_MODEL_CACHE" \
  --port "$VLLM_PORT" \
  --dtype bfloat16 \
  --max-model-len 4096 \
  --gpu-memory-utilization 0.90 \
  --trust-remote-code \
  > "$WORK/api-logs/vllm.log" 2>&1 &
PIDS+=($!)

echo "  Waiting for vLLM to load model..."
for i in $(seq 1 120); do
  if curl -s "http://localhost:${VLLM_PORT}/health" > /dev/null 2>&1; then
    echo "  [OK] vLLM ready on localhost:$VLLM_PORT"
    break
  fi
  if [ "$i" -eq 120 ]; then
    echo "[ERROR] vLLM failed to start. Last 30 lines of log:"
    tail -30 "$WORK/api-logs/vllm.log" 2>/dev/null || true
    exit 1
  fi
  sleep 5
done

# Quick sanity check — test a completion
echo "  Testing completion..."
TEST_RESP=$(curl -s -X POST "http://localhost:${VLLM_PORT}/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$BASE_MODEL\", \"prompt\": \"The meaning of life is\", \"max_tokens\": 20}" 2>/dev/null || echo "{}")
echo "  Test: $(echo "$TEST_RESP" | jq -r '.choices[0].text // "FAILED"' 2>/dev/null | head -1)"

# ============================================
# 4. Start PostgreSQL
# ============================================
echo ""
echo "[4/7] Starting PostgreSQL..."

apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  --env PGDATA=/var/lib/postgresql/data \
  "$SIF_DIR/postgres-16.sif" \
  sh -c 'if [ ! -f "$PGDATA/PG_VERSION" ]; then initdb -D "$PGDATA" -U moltbook --auth=trust; fi'

apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  --env PGDATA=/var/lib/postgresql/data \
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
  [ "$i" -eq 30 ] && { echo "[ERROR] PostgreSQL failed"; exit 1; }
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

echo "  [OK] PostgreSQL on localhost:$PG_PORT"

# ============================================
# 5. Start Redis + MoltBook API
# ============================================
echo ""
echo "[5/7] Starting Redis + API..."

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
  [ "$i" -eq 15 ] && { echo "[ERROR] Redis failed"; exit 1; }
  sleep 1
done

echo "  [OK] Redis on localhost:$REDIS_PORT"

# API with content token enforcement
# Bind-mount patched routes/config over the SIF defaults (adds HMAC verification)
API_PATCHES="$CONFIG_DIR/api-patches"
apptainer exec $APT_FLAGS \
  -B "$API_PATCHES/posts.js:/app/src/routes/posts.js:ro" \
  -B "$API_PATCHES/config-index.js:/app/src/config/index.js:ro" \
  --env PORT=$API_PORT \
  --env NODE_ENV=production \
  --env "DATABASE_URL=postgresql://moltbook:moltbook_password@localhost:${PG_PORT}/moltbook?sslmode=disable" \
  --env "REDIS_URL=redis://localhost:${REDIS_PORT}" \
  --env "JWT_SECRET=base-model-test-${SLURM_JOB_ID:-local}" \
  --env "BASE_URL=http://localhost:${API_PORT}" \
  --env "RATE_LIMIT_REQUESTS_MAX=500" \
  --env "RATE_LIMIT_REQUESTS_WINDOW=60" \
  --env "RATE_LIMIT_POSTS_MAX=$RATE_LIMIT_POSTS_MAX" \
  --env "RATE_LIMIT_POSTS_WINDOW=$RATE_LIMIT_POSTS_WINDOW" \
  --env "RATE_LIMIT_COMMENTS_MAX=1000" \
  --env "RATE_LIMIT_COMMENTS_WINDOW=3600" \
  --env "MAX_COMMENTS_PER_AGENT_PER_POST=5" \
  --env "REQUIRE_CONTENT_TOKEN=true" \
  --env "CONTENT_TOKEN_SECRET=$CONTENT_TOKEN_SECRET" \
  --env "EXPERIMENT_RANKING_ENABLED=true" \
  --env "EXPERIMENT_MODE=C" \
  --env "EXPERIMENT_NAME=$EXPERIMENT_NAME" \
  "$SIF_DIR/moltbook-api.sif" \
  node /app/src/index.js \
  > "$WORK/api-logs/api.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 60); do
  curl -s http://localhost:${API_PORT}/api/v1/health > /dev/null 2>&1 && break
  [ "$i" -eq 60 ] && { echo "[ERROR] API failed"; tail -20 "$WORK/api-logs/api.log"; exit 1; }
  sleep 2
done

echo "  [OK] API on localhost:$API_PORT (content token enforcement ON)"

# ============================================
# 6. Start content-gen service
# ============================================
echo ""
echo "[6/7] Starting content-gen service..."

# Run content-gen-service using node from the moltbot-agent SIF
# (it has Node.js 22 + everything we need)
CONTENT_GEN_DIR="$HOME/moltbook/content-gen-service"

# Install npm deps if needed
if [ ! -d "$CONTENT_GEN_DIR/node_modules" ]; then
  echo "  Installing content-gen dependencies..."
  apptainer exec $APT_FLAGS \
    -B "$CONTENT_GEN_DIR:/app/content-gen:rw" \
    "$SIF_DIR/moltbot-agent.sif" \
    sh -c "cd /app/content-gen && npm install --omit=dev" 2>/dev/null || {
      # Fallback: use system node
      cd "$CONTENT_GEN_DIR" && npm install --omit=dev 2>/dev/null || true
      cd "$HOME/moltbook"
    }
fi

apptainer exec $APT_FLAGS \
  -B "$CONTENT_GEN_DIR:/app/content-gen:ro" \
  -B "$CONTENT_GEN_DIR/node_modules:/app/content-gen/node_modules:ro" \
  -B "$WORK/api-logs:/data" \
  --env "PORT=$CONTENT_GEN_PORT" \
  --env "BASE_MODEL_API_URL=$VLLM_URL" \
  --env "BASE_MODEL=$BASE_MODEL" \
  --env "CONTENT_TOKEN_SECRET=$CONTENT_TOKEN_SECRET" \
  --env "AUDIT_LOG_PATH=/data/content-gen-audit.jsonl" \
  --env "TEMPERATURE=0.9" \
  --env "TOP_P=0.95" \
  --env "REPETITION_PENALTY=1.1" \
  "$SIF_DIR/moltbot-agent.sif" \
  node /app/content-gen/server.js \
  > "$WORK/api-logs/content-gen.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 30); do
  curl -s "http://localhost:${CONTENT_GEN_PORT}/health" > /dev/null 2>&1 && break
  if [ "$i" -eq 30 ]; then
    echo "[ERROR] Content-gen service failed. Log:"
    tail -20 "$WORK/api-logs/content-gen.log" 2>/dev/null || true
    exit 1
  fi
  sleep 2
done

echo "  [OK] Content-gen on localhost:$CONTENT_GEN_PORT -> vLLM at $VLLM_URL"

# Test end-to-end: content-gen -> vLLM -> HMAC token
echo "  Testing content generation pipeline..."
GEN_RESP=$(curl -s -X POST "http://localhost:${CONTENT_GEN_PORT}/generate-post" \
  -H "Content-Type: application/json" \
  -d '{"context": "", "submolt": "general"}' 2>/dev/null || echo "{}")
GEN_TITLE=$(echo "$GEN_RESP" | jq -r '.title // "FAILED"' 2>/dev/null)
GEN_TOKEN=$(echo "$GEN_RESP" | jq -r '.content_token // "NONE"' 2>/dev/null)
echo "  Generated: title='${GEN_TITLE:0:60}...' token=${GEN_TOKEN:0:16}..."

if [ "$GEN_TITLE" = "FAILED" ] || [ "$GEN_TOKEN" = "NONE" ]; then
  echo "[ERROR] Content generation pipeline failed"
  tail -20 "$WORK/api-logs/content-gen.log" 2>/dev/null || true
  exit 1
fi

echo "  [OK] Pipeline verified"

# ============================================
# 7. Launch 1 agent
# ============================================
echo ""
echo "[7/7] Launching agent_alpha..."

AGENT_TMPDIR="$WORK/agent-tmp/agent-0"
GATEWAY_PORT=$AGENT_PORT_BASE

apptainer exec $APT_FLAGS --pid \
  -B "$WORK/agent-data/agent-0:/root/.openclaw" \
  -B "$WORK/agent-config/agent-0:/root/.config/moltbook" \
  -B "$AGENT_TMPDIR:/tmp/agent" \
  -B "$CONFIG_DIR/souls:/app/generated-souls:ro" \
  -B "$CONFIG_DIR/skills:/app/skills:ro" \
  -B "$CONFIG_DIR/HEARTBEAT-base-model.md:/app/HEARTBEAT.md:ro" \
  -B "$CONFIG_DIR/moltbot-entrypoint.sh:/app/entrypoint.sh:ro" \
  --env "AGENT_NAME=agent_alpha" \
  --env "AGENT_BIO=A balanced AI participant exploring ideas and discussions." \
  --env "SOUL_FILE=agent_alpha-SOUL.md" \
  --env "MOLTBOOK_API_URL=$MOLTBOOK_API_URL" \
  --env "CONTENT_GEN_URL=$CONTENT_GEN_URL" \
  --env "HEARTBEAT_INTERVAL=$HEARTBEAT_INTERVAL" \
  --env "OPENCLAW_GATEWAY_PORT=$GATEWAY_PORT" \
  --env "OPENCLAW_STATE_DIR=/root/.openclaw" \
  --env "TMPDIR=/tmp/agent" \
  --env "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}" \
  --env "OPENROUTER_MODEL=$OPENROUTER_MODEL" \
  --env "OPENCLAW_GATEWAY_TOKEN=moltbook-agent-agent_alpha" \
  "$SIF_DIR/moltbot-agent.sif" \
  /app/entrypoint.sh \
  > "$WORK/api-logs/agent-agent_alpha.log" 2>&1 &
PIDS+=($!)

echo "  [OK] agent_alpha launched (port $GATEWAY_PORT)"

# ============================================
# Run for EXPERIMENT_DURATION
# ============================================
echo ""
echo "Running experiment for $EXPERIMENT_DURATION..."
echo "  Started: $(date)"

DURATION_SEC=$(duration_to_seconds "$EXPERIMENT_DURATION")
START_TIME=$(date +%s)
LAST_REPORT=0

while true; do
  ELAPSED=$(( $(date +%s) - START_TIME ))
  REMAINING=$(( DURATION_SEC - ELAPSED ))
  [ $REMAINING -le 0 ] && break

  if [ $((ELAPSED - LAST_REPORT)) -ge 30 ] && [ $ELAPSED -gt 0 ]; then
    LAST_REPORT=$ELAPSED
    ALIVE=0
    kill -0 "${PIDS[-1]}" 2>/dev/null && ALIVE=1 || true
    POST_COUNT=$(wc -l < <(curl -s -H "Authorization: Bearer dummy" "$MOLTBOOK_API_URL/posts?limit=1" 2>/dev/null | jq -c '.data[]' 2>/dev/null || true) 2>/dev/null || echo "?")

    # Quick check via API for post count
    TOTAL_POSTS=$(curl -s "$MOLTBOOK_API_URL/posts?limit=1" -H "Authorization: Bearer $(jq -r '.api_key' "$WORK/agent-config/agent-0/credentials.json" 2>/dev/null || echo dummy)" 2>/dev/null | jq '.pagination.total // 0' 2>/dev/null || echo "?")

    echo "  [${ELAPSED}s / ${REMAINING}s left] Agent alive: $ALIVE  Posts so far: $TOTAL_POSTS"
  fi

  sleep 10
done

ACTUAL_DURATION=$(( $(date +%s) - START_TIME ))

# ============================================
# Final export
# ============================================
echo ""
echo "Exporting results..."

export_data "final"
write_metadata "final"
persist_to_project

# Summary
POST_N=$(wc -l < "$RESULTS_DIR/posts.jsonl" 2>/dev/null || echo 0)
COMMENT_N=$(wc -l < "$RESULTS_DIR/comments.jsonl" 2>/dev/null || echo 0)
AUDIT_N=$(wc -l < "$RESULTS_DIR/audit-log.jsonl" 2>/dev/null || echo 0)

echo ""
echo "============================================"
echo "  Test Complete: $EXPERIMENT_NAME"
echo "============================================"
echo "  Duration:    $((ACTUAL_DURATION / 60)) minutes"
echo "  Posts:        $POST_N"
echo "  Comments:     $COMMENT_N"
echo "  Audit entries: $AUDIT_N"
echo "  Results:     $RESULTS_DIR"
echo "  Backup:      $RESULTS_PROJECT/$EXPERIMENT_NAME"
echo "============================================"

# Run integrity verification
echo ""
echo "Running integrity verification..."
python3 "$HOME/moltbook/scripts/verify-base-model-integrity.py" "$RESULTS_DIR" --secret "$CONTENT_TOKEN_SECRET" || true
