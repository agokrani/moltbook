#!/usr/bin/env bash
#SBATCH --job-name=base-model-test
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --time=1:00:00
#SBATCH --cpus-per-task=6
#SBATCH --mem=64G
#SBATCH --gres=gpu:nvidia_h100_80gb_hbm3_3g.40gb:1
#SBATCH --account=def-zhijing
#SBATCH --signal=B:USR1@120
#
# Base Model Pipeline Test — MIG slice (40GB)
# 1 agent, 10 min, mag0
# vLLM serves Qwen3.5-35B-A3B-Base in FP8 on a 40GB MIG slice
# Orchestrator: Gemini Flash Lite via OpenRouter
#
# Submit: sbatch alliance/test-base-model-mig.sh

set -euo pipefail

PROJECT="${PROJECT:-/project/def-zhijing/anangia}"
SCRATCH="${SCRATCH:-/scratch/anangia}"
CONFIG_DIR="$PROJECT/moltbook/config"
SIF_DIR="$PROJECT/moltbook/images"
RESULTS_DIR="$SCRATCH/moltbook/results/base-model-mig-test-$(date +%Y%m%d-%H%M%S)"

set -a; source "$CONFIG_DIR/.env"; set +a

# Override for this test
OPENROUTER_MODEL="google/gemini-3.1-flash-lite-preview"
BASE_MODEL="Qwen/Qwen3.5-35B-A3B-Base"
CONTENT_TOKEN_SECRET="test-hmac-secret-2026"
EXPERIMENT_DURATION="10m"

module load apptainer 2>/dev/null || true
module load gcc/13.3 2>/dev/null || true
module load python/3.11.5 2>/dev/null || module load python/3.10.13 2>/dev/null || true
module load cuda/12.6 2>/dev/null || module load cuda/12.2 2>/dev/null || true
module load opencv/4.10.0 2>/dev/null || module load opencv 2>/dev/null || true
module load arrow/19.0.1 2>/dev/null || true

APT_FLAGS="-e -W ${SLURM_TMPDIR:-/tmp}"
WORK="${SLURM_TMPDIR:-/tmp}/moltbook"
VLLM_ENV="$SCRATCH/envs/vllm"
HF_CACHE="$SCRATCH/hf-cache"

# Ports
PORT_OFFSET=$(( (${SLURM_JOB_ID:-$$} % 65) * 700 ))
PG_PORT=$(( 5432 + PORT_OFFSET ))
REDIS_PORT=$(( 6379 + PORT_OFFSET ))
API_PORT=$(( 3000 + PORT_OFFSET ))
VLLM_PORT=$(( 8000 + PORT_OFFSET ))
CONTENT_GEN_PORT=$(( 3002 + PORT_OFFSET ))
AGENT_PORT=$(( 18789 + PORT_OFFSET ))

MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"

mkdir -p "$WORK"/{pgdata,pgrun,redisdata,api-logs,agent-data/agent-0,agent-config/agent-0,agent-tmp/agent-0}
mkdir -p "$WORK/agent-data/agent-0/canvas"
mkdir -p "$RESULTS_DIR"

echo "============================================"
echo "  Base Model Pipeline Test (MIG 40GB)"
echo "  Node: $(hostname)"
echo "  GPU: $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)"
echo "  Orchestrator: $OPENROUTER_MODEL"
echo "  Base model: $BASE_MODEL (FP8)"
echo "  Duration: $EXPERIMENT_DURATION"
echo "============================================"

PIDS=()
cleanup() {
  echo "[CLEANUP]"
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
}
trap cleanup EXIT

# Validate SIF images
for img in postgres-16.sif redis-7.sif moltbook-api.sif moltbot-agent.sif; do
  [ -f "$SIF_DIR/$img" ] || { echo "[ERROR] Missing: $SIF_DIR/$img"; exit 1; }
done

# ============================================
# 1. Setup vLLM
# ============================================
echo "[1/7] Setting up vLLM..."
if [ ! -f "$VLLM_ENV/bin/activate" ]; then
  echo "  Creating virtualenv (with system-site-packages for opencv/arrow)..."
  python3 -m venv --system-site-packages "$VLLM_ENV"
  source "$VLLM_ENV/bin/activate"
  pip install --no-cache-dir --upgrade pip
  # Install vllm — opencv comes from the module (Alliance blocks pip install)
  # First install vllm without deps that need opencv, then handle the rest
  pip install --no-cache-dir "opencv-python-headless>=4.10" --no-deps 2>/dev/null || true
  # Create a fake opencv package so pip thinks it's installed
  SITE_PKG="$VLLM_ENV/lib/python3.11/site-packages"
  mkdir -p "$SITE_PKG/opencv_python_headless-9999.dist-info"
  echo "Metadata-Version: 2.1
Name: opencv-python-headless
Version: 9999
" > "$SITE_PKG/opencv_python_headless-9999.dist-info/METADATA"
  echo "opencv-python-headless" > "$SITE_PKG/opencv_python_headless-9999.dist-info/RECORD"
  echo "opencv-python-headless" > "$SITE_PKG/opencv_python_headless-9999.dist-info/top_level.txt"
  echo "[OK] Installed fake opencv-python-headless (real one from module)"
  pip install --no-cache-dir vllm 2>&1 | tail -5
  pip install --no-cache-dir "huggingface_hub[hf_xet]" 2>&1 | tail -3
  deactivate
fi
source "$VLLM_ENV/bin/activate"
echo "  [OK] vLLM $(python3 -c 'import vllm; print(vllm.__version__)' 2>/dev/null || echo 'installed')"

# ============================================
# 2. Download model if needed
# ============================================
echo "[2/7] Checking model cache..."
export HF_HOME="$HF_CACHE"
export TRANSFORMERS_CACHE="$HF_CACHE"
MODEL_DIR="$HF_CACHE/hub/models--Qwen--Qwen3.5-35B-A3B-Base"
if [ -d "$MODEL_DIR" ]; then
  echo "  [OK] Cached"
else
  echo "  Downloading $BASE_MODEL..."
  python3 -c "from huggingface_hub import snapshot_download; snapshot_download('$BASE_MODEL', cache_dir='$HF_CACHE')"
fi

# ============================================
# 3. Start vLLM (FP8 on MIG 40GB slice)
# ============================================
echo "[3/7] Starting vLLM (FP8)..."
python3 -m vllm.entrypoints.openai.api_server \
  --model "$BASE_MODEL" \
  --download-dir "$HF_CACHE" \
  --port "$VLLM_PORT" \
  --dtype float16 \
  --quantization fp8 \
  --max-model-len 2048 \
  --gpu-memory-utilization 0.92 \
  --trust-remote-code \
  > "$WORK/api-logs/vllm.log" 2>&1 &
PIDS+=($!)

echo "  Waiting for vLLM to load model..."
for i in $(seq 1 180); do
  if curl -s "http://localhost:${VLLM_PORT}/health" > /dev/null 2>&1; then
    echo "  [OK] vLLM ready on :$VLLM_PORT"
    break
  fi
  if [ "$i" -eq 180 ]; then
    echo "[ERROR] vLLM failed. Log:"
    tail -30 "$WORK/api-logs/vllm.log"
    exit 1
  fi
  sleep 5
done

# Quick test
echo "  Testing completion..."
TEST=$(curl -s -X POST "http://localhost:${VLLM_PORT}/v1/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\": \"$BASE_MODEL\", \"prompt\": \"The meaning of life is\", \"max_tokens\": 20}" 2>/dev/null)
echo "  Test: $(echo "$TEST" | jq -r '.choices[0].text // "FAILED"' 2>/dev/null | head -c 80)"

# ============================================
# 4. PostgreSQL + Redis
# ============================================
echo "[4/7] Starting PostgreSQL + Redis..."

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
  apptainer exec $APT_FLAGS -B "$WORK/pgdata:/var/lib/postgresql/data" -B "$WORK/pgrun:/var/run/postgresql" \
    "$SIF_DIR/postgres-16.sif" pg_isready -h localhost -p $PG_PORT -U moltbook 2>/dev/null && break
  [ "$i" -eq 30 ] && { echo "FAIL: postgres"; exit 1; }; sleep 2
done

apptainer exec $APT_FLAGS -B "$WORK/pgdata:/var/lib/postgresql/data" -B "$WORK/pgrun:/var/run/postgresql" \
  "$SIF_DIR/postgres-16.sif" sh -c "createdb -h localhost -p $PG_PORT -U moltbook moltbook 2>/dev/null || true"
apptainer exec $APT_FLAGS -B "$WORK/pgdata:/var/lib/postgresql/data" -B "$WORK/pgrun:/var/run/postgresql" \
  -B "$CONFIG_DIR/schema.sql:/tmp/schema.sql:ro" "$SIF_DIR/postgres-16.sif" \
  psql -h localhost -p $PG_PORT -U moltbook -d moltbook -f /tmp/schema.sql > /dev/null 2>&1 || true

apptainer exec $APT_FLAGS -B "$WORK/redisdata:/data" "$SIF_DIR/redis-7.sif" \
  redis-server --bind localhost --port $REDIS_PORT --dir /data --daemonize no \
  > "$WORK/api-logs/redis.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 15); do
  apptainer exec $APT_FLAGS "$SIF_DIR/redis-7.sif" \
    redis-cli -h localhost -p $REDIS_PORT ping 2>/dev/null | grep -q PONG && break
  [ "$i" -eq 15 ] && { echo "FAIL: redis"; exit 1; }; sleep 1
done

echo "  [OK] PG on :$PG_PORT, Redis on :$REDIS_PORT"

# ============================================
# 5. API (with content token enforcement)
# ============================================
echo "[5/7] Starting API (token enforcement ON)..."
API_PATCHES="$CONFIG_DIR/api-patches"

apptainer exec $APT_FLAGS \
  -B "$API_PATCHES/posts.js:/app/src/routes/posts.js:ro" \
  -B "$API_PATCHES/config-index.js:/app/src/config/index.js:ro" \
  --env PORT=$API_PORT \
  --env NODE_ENV=production \
  --env "DATABASE_URL=postgresql://moltbook:moltbook_password@localhost:${PG_PORT}/moltbook?sslmode=disable" \
  --env "REDIS_URL=redis://localhost:${REDIS_PORT}" \
  --env "JWT_SECRET=base-model-test" \
  --env "RATE_LIMIT_POSTS_MAX=50" \
  --env "RATE_LIMIT_POSTS_WINDOW=60" \
  --env "REQUIRE_CONTENT_TOKEN=true" \
  --env "CONTENT_TOKEN_SECRET=$CONTENT_TOKEN_SECRET" \
  "$SIF_DIR/moltbook-api.sif" \
  node /app/src/index.js \
  > "$WORK/api-logs/api.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 60); do
  curl -s http://localhost:${API_PORT}/api/v1/health > /dev/null 2>&1 && break
  [ "$i" -eq 60 ] && { echo "FAIL: api"; tail -20 "$WORK/api-logs/api.log"; exit 1; }; sleep 2
done
echo "  [OK] API on :$API_PORT"

# ============================================
# 6. Content-gen service (pointing at local vLLM)
# ============================================
echo "[6/7] Starting content-gen service -> vLLM..."
CONTENT_GEN_DIR="$HOME/moltbook/content-gen-service"
CONTENT_GEN_URL="http://localhost:${CONTENT_GEN_PORT}"

if [ ! -d "$CONTENT_GEN_DIR/node_modules" ]; then
  apptainer exec $APT_FLAGS -B "$CONTENT_GEN_DIR:/app/cg:rw" "$SIF_DIR/moltbot-agent.sif" \
    sh -c "cd /app/cg && npm install --omit=dev" 2>/dev/null || true
fi

apptainer exec $APT_FLAGS \
  -B "$CONTENT_GEN_DIR:/app/content-gen:ro" \
  -B "$CONTENT_GEN_DIR/node_modules:/app/content-gen/node_modules:ro" \
  -B "$WORK/api-logs:/data" \
  --env "PORT=$CONTENT_GEN_PORT" \
  --env "BASE_MODEL_API_URL=http://localhost:${VLLM_PORT}" \
  --env "BASE_MODEL=$BASE_MODEL" \
  --env "CONTENT_TOKEN_SECRET=$CONTENT_TOKEN_SECRET" \
  --env "AUDIT_LOG_PATH=/data/content-gen-audit.jsonl" \
  --env "TEMPERATURE=0.9" \
  "$SIF_DIR/moltbot-agent.sif" \
  node /app/content-gen/server.js \
  > "$WORK/api-logs/content-gen.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 30); do
  curl -s "http://localhost:${CONTENT_GEN_PORT}/health" > /dev/null 2>&1 && break
  [ "$i" -eq 30 ] && { echo "FAIL: content-gen"; tail -20 "$WORK/api-logs/content-gen.log"; exit 1; }; sleep 2
done

# End-to-end pipeline test
echo "  Testing: content-gen -> vLLM -> HMAC -> API..."
GEN_RESP=$(curl -s -X POST "http://localhost:${CONTENT_GEN_PORT}/generate-post" \
  -H "Content-Type: application/json" -d '{"context": "", "submolt": "general"}')
GEN_TITLE=$(echo "$GEN_RESP" | jq -r '.title // "FAILED"')
GEN_CONTENT=$(echo "$GEN_RESP" | jq -r '.content // "FAILED"')
GEN_TOKEN=$(echo "$GEN_RESP" | jq -r '.content_token // "NONE"')

if [ "$GEN_TITLE" = "FAILED" ]; then
  echo "  [ERROR] Generation failed"; tail -10 "$WORK/api-logs/content-gen.log"; exit 1
fi
echo "  Generated: '${GEN_TITLE:0:50}'"

# Verify token works with API
REG=$(curl -s -X POST "$MOLTBOOK_API_URL/agents/register" -H "Content-Type: application/json" \
  -d '{"name": "pipeline_test", "description": "test"}')
TEST_KEY=$(echo "$REG" | jq -r '.api_key // .agent.api_key // empty')
if [ -n "$TEST_KEY" ]; then
  POST_RESP=$(curl -s -X POST "$MOLTBOOK_API_URL/posts" \
    -H "Authorization: Bearer $TEST_KEY" -H "Content-Type: application/json" \
    -d "$(jq -n --arg t "$GEN_TITLE" --arg c "$GEN_CONTENT" --arg tk "$GEN_TOKEN" \
      '{submolt:"general", title:$t, content:$c, content_token:$tk}')")
  echo "  Token verify: $(echo "$POST_RESP" | jq -r '.post.id // "FAILED"' | head -c 8)..."
fi
echo "  [OK] Full pipeline verified"

# ============================================
# 7. Launch agent
# ============================================
echo "[7/7] Launching agent_alpha..."

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
echo "Running for $EXPERIMENT_DURATION..."
echo "  Started: $(date)"

START_TIME=$(date +%s)
LAST_REPORT=0
DURATION_SEC=600

while true; do
  ELAPSED=$(( $(date +%s) - START_TIME ))
  [ $((DURATION_SEC - ELAPSED)) -le 0 ] && break

  if [ $((ELAPSED - LAST_REPORT)) -ge 30 ] && [ $ELAPSED -gt 0 ]; then
    LAST_REPORT=$ELAPSED
    ALIVE=0; kill -0 "${PIDS[-1]}" 2>/dev/null && ALIVE=1

    API_KEY=$(jq -r '.api_key' "$WORK/agent-config/agent-0/credentials.json" 2>/dev/null || echo "")
    POSTS="?"
    if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
      POSTS=$(curl -s -H "Authorization: Bearer $API_KEY" "$MOLTBOOK_API_URL/posts?limit=1" 2>/dev/null | jq '.pagination.total // 0' 2>/dev/null || echo "?")
    fi

    # Check agent model
    MODEL=$(grep 'agent model:' "$WORK/api-logs/agent-agent_alpha.log" 2>/dev/null | tail -1 | sed 's/.*agent model: //')
    HEARTBEATS=$(grep -c 'embedded run start' "$WORK/api-logs/agent-agent_alpha.log" 2>/dev/null || echo 0)

    echo "  [${ELAPSED}s] Agent:$ALIVE Posts:$POSTS Heartbeats:$HEARTBEATS Model:${MODEL:-?}"
  fi
  sleep 10
done

ACTUAL_DURATION=$(( $(date +%s) - START_TIME ))

# Export
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
    POSTS_DATA=$(echo "$RESP" | jq -c '.data[]' 2>/dev/null || true)
    [ -z "$POSTS_DATA" ] && break
    echo "$POSTS_DATA" >> "$RESULTS_DIR/posts.jsonl"
    [ "$(echo "$RESP" | jq -r '.pagination.hasMore // false')" != "true" ] && break
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
python3 "$HOME/moltbook/scripts/verify-base-model-integrity.py" "$RESULTS_DIR" --secret "$CONTENT_TOKEN_SECRET" 2>/dev/null || true
