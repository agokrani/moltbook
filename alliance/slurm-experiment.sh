#!/usr/bin/env bash
#SBATCH --job-name=moltbook-exp
#SBATCH --output=%x-%A_%a.out
#SBATCH --error=%x-%A_%a.err
#SBATCH --time=3:00:00
#SBATCH --cpus-per-task=2
#SBATCH --mem=22G
#SBATCH --array=1-5
#SBATCH --signal=B:USR1@300
#
# MoltBook Multi-Agent Experiment on Alliance Canada
#
# Each array task runs one independent experiment with:
#   - PostgreSQL, Redis, MoltBook API (dynamic ports per job)
#   - N AI agents (heartbeat loops, dynamic gateway ports)
#   - All ports derived from SLURM_JOB_ID to avoid collisions on shared nodes
#
# Data safety:
#   - Database checkpointed to $SCRATCH every 30 minutes
#   - Slurm sends USR1 signal 5 min before walltime → triggers export
#   - SIGTERM trap → exports data before dying
#   - Final results copied to both $SCRATCH and $PROJECT (backed up)
#
# Prerequisites:
#   1. Run setup-cluster.sh once
#   2. SIF images in $PROJECT/moltbook/images/
#   3. Config in $PROJECT/moltbook/config/.env
#
# Submit:  sbatch alliance/slurm-experiment.sh
# Monitor: sq  (or squeue -u $USER)
# Logs:    cat moltbook-exp-<jobid>_<arrayid>.out

set -euo pipefail

# ============================================
# Configuration
# ============================================
# Fir doesn't auto-set $PROJECT; fall back to known path
PROJECT="${PROJECT:-/project/def-zhijing/anangia}"
SCRATCH="${SCRATCH:-/scratch/anangia}"

CONFIG_DIR="$PROJECT/moltbook/config"
SIF_DIR="$PROJECT/moltbook/images"
RESULTS_SCRATCH="$SCRATCH/moltbook/results"
RESULTS_PROJECT="$PROJECT/moltbook/results"

# Load user config
if [ -f "$CONFIG_DIR/.env" ]; then
  set -a
  source "$CONFIG_DIR/.env"
  set +a
else
  echo "[ERROR] No config found at $CONFIG_DIR/.env"
  echo "Run setup-cluster.sh first."
  exit 1
fi

# Defaults
NUM_AGENTS="${NUM_AGENTS:-10}"
HEARTBEAT_INTERVAL="${HEARTBEAT_INTERVAL:-11s}"
EXPERIMENT_DURATION="${EXPERIMENT_DURATION:-2h}"
RATE_LIMIT_POSTS_MAX="${RATE_LIMIT_POSTS_MAX:-50}"
RATE_LIMIT_POSTS_WINDOW="${RATE_LIMIT_POSTS_WINDOW:-60}"
RATE_LIMIT_COMMENTS_MAX="${RATE_LIMIT_COMMENTS_MAX:-1000}"
RATE_LIMIT_COMMENTS_WINDOW="${RATE_LIMIT_COMMENTS_WINDOW:-3600}"
CHECKPOINT_INTERVAL="${CHECKPOINT_INTERVAL:-1800}"  # 30 minutes

# Entropy-collapse condition support (set via env before sbatch)
# CONDITION: mag0, mag1, mag5, mag25, dom-agi, dom-tech, het-dual, het-multi, or empty for no seeding
CONDITION="${CONDITION:-}"
WORLD_POSTS_DIR="$CONFIG_DIR/world-posts"

# Map condition to world posts file
condition_to_file() {
  case "$1" in
    mag0)      echo "world-posts-empty.jsonl" ;;
    mag1)      echo "world-posts-mag1.jsonl" ;;
    mag5)      echo "world-posts-mag5.jsonl" ;;
    mag25)     echo "world-posts-mag25.jsonl" ;;
    dom-agi)   echo "world-posts-agi.jsonl" ;;
    dom-tech)  echo "world-posts-tech.jsonl" ;;
    dom-conspiracy) echo "world-posts-conspiracy.jsonl" ;;
    het-dual)  echo "world-posts-het-dual.jsonl" ;;
    het-multi) echo "world-posts-het-multi.jsonl" ;;
    *)         echo "" ;;
  esac
}

# Experiment ID from Slurm array
EXP_ID="${SLURM_ARRAY_TASK_ID:-1}"
JOB_ID="${SLURM_JOB_ID:-local}"
if [ -n "$CONDITION" ]; then
  EXPERIMENT_NAME="ec-${CONDITION}-run$(printf '%02d' "$EXP_ID")"
else
  EXPERIMENT_NAME="exp-${JOB_ID}-run${EXP_ID}"
fi
RESULTS_DIR="$RESULTS_SCRATCH/$EXPERIMENT_NAME"

# Working directory on fast local NVMe
WORK="${SLURM_TMPDIR:-/tmp}/moltbook"

echo "============================================"
echo "  MoltBook Experiment: $EXPERIMENT_NAME"
echo "  Node: $(hostname)"
echo "  Run: $EXP_ID of ${SLURM_ARRAY_TASK_COUNT:-?}"
echo "  Condition: ${CONDITION:-none (free chat)}"
echo "  Agents: $NUM_AGENTS"
echo "  Duration: $EXPERIMENT_DURATION"
echo "  Checkpoint: every $((CHECKPOINT_INTERVAL / 60))m"
echo "  Work dir: $WORK"
echo "============================================"
echo ""

# ============================================
# Validate SIF images
# ============================================
for img in postgres-16.sif redis-7.sif moltbook-api.sif moltbot-agent.sif; do
  if [ ! -f "$SIF_DIR/$img" ]; then
    echo "[ERROR] Missing: $SIF_DIR/$img"
    exit 1
  fi
done

# ============================================
# Setup working directories
# ============================================
mkdir -p "$WORK"/{pgdata,redisdata,api-logs}
mkdir -p "$RESULTS_DIR/checkpoints"

for i in $(seq 0 $((NUM_AGENTS - 1))); do
  mkdir -p "$WORK/agent-data/agent-${i}" "$WORK/agent-config/agent-${i}"
done

# Load apptainer module
module load apptainer 2>/dev/null || true

# Apptainer flags: clean environment, disk-backed tmpdir
# NOT -C (full containment) — we need services to share the host network
APT_FLAGS="-e -W ${SLURM_TMPDIR:-/tmp}"

# Track background PIDs
PIDS=()

# ============================================
# Dynamic ports — avoid collisions when multiple jobs share a node
# Each job gets a unique port block derived from SLURM_JOB_ID
# Block size must fit: NUM_AGENTS * 10 (agent stride) + 50 (services)
# For 60 agents: 60*10 + 50 = 650, so we use 700-port blocks
# ============================================
PORT_OFFSET=$(( (${SLURM_JOB_ID:-$$} % 65) * 700 ))
PG_PORT=$((  5432 + PORT_OFFSET ))
REDIS_PORT=$(( 6379 + PORT_OFFSET ))
API_PORT=$((  3000 + PORT_OFFSET ))
AGENT_PORT_BASE=$(( 18789 + PORT_OFFSET ))

MOLTBOOK_API_URL="http://localhost:${API_PORT}/api/v1"

echo "  Ports: PG=$PG_PORT Redis=$REDIS_PORT API=$API_PORT Agents=${AGENT_PORT_BASE}+"

# Convert duration string to seconds
duration_to_seconds() {
  local d=$1
  local num=${d%[smhd]}
  local unit=${d: -1}
  case $unit in
    s) echo "$num" ;; m) echo $((num * 60)) ;;
    h) echo $((num * 3600)) ;; d) echo $((num * 86400)) ;;
    *) echo "$num" ;;
  esac
}

# ============================================
# Export function (reusable for normal + emergency)
# ============================================
export_data() {
  local EXPORT_LABEL="${1:-final}"
  local TARGET_DIR="$RESULTS_DIR"

  echo ""
  echo "[EXPORT:$EXPORT_LABEL] Saving experiment data..."

  # Get API key from agent credentials
  local API_KEY=""
  for i in $(seq 0 $((NUM_AGENTS - 1))); do
    local CREDS="$WORK/agent-config/agent-${i}/credentials.json"
    if [ -f "$CREDS" ]; then
      API_KEY=$(jq -r '.api_key' "$CREDS" 2>/dev/null || true)
      if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
        break
      fi
    fi
  done

  if [ -n "$API_KEY" ] && [ "$API_KEY" != "null" ]; then
    local AUTH="Authorization: Bearer $API_KEY"

    # Agents
    curl -s -H "$AUTH" "$MOLTBOOK_API_URL/agents?limit=100" \
      | jq -c '.data[]' > "$TARGET_DIR/agents.jsonl" 2>/dev/null || true

    # Posts (paginated)
    local OFFSET=0
    > "$TARGET_DIR/posts.jsonl"
    while true; do
      local RESP=$(curl -s -H "$AUTH" "$MOLTBOOK_API_URL/posts?limit=100&offset=$OFFSET&sort=new")
      local POSTS=$(echo "$RESP" | jq -c '.data[]' 2>/dev/null || true)
      [ -z "$POSTS" ] && break
      echo "$POSTS" >> "$TARGET_DIR/posts.jsonl"
      local HAS_MORE=$(echo "$RESP" | jq -r '.pagination.hasMore // false' 2>/dev/null || echo "false")
      [ "$HAS_MORE" != "true" ] && break
      OFFSET=$((OFFSET + 100))
    done

    # Comments (for each post)
    > "$TARGET_DIR/comments.jsonl"
    while IFS= read -r post; do
      local POST_ID=$(echo "$post" | jq -r '.id')
      if [ -n "$POST_ID" ] && [ "$POST_ID" != "null" ]; then
        curl -s -H "$AUTH" "$MOLTBOOK_API_URL/posts/$POST_ID/comments?sort=new&limit=500" \
          | jq -c --arg pid "$POST_ID" '
              def flat: . as $c | [$c] + ((.replies // []) | map(flat) | add // []);
              (.comments // []) | map(flat) | add // [] | .[] | . + {post_id: $pid} | del(.replies)
            ' >> "$TARGET_DIR/comments.jsonl" 2>/dev/null || true
      fi
    done < "$TARGET_DIR/posts.jsonl"

    # Activity log
    > "$TARGET_DIR/activity.jsonl"
    local ACT_OFFSET=0
    while true; do
      local RESP=$(curl -s -H "$AUTH" "$MOLTBOOK_API_URL/analytics/activity?limit=1000&offset=$ACT_OFFSET")
      local EVENTS=$(echo "$RESP" | jq -c '.activities[]' 2>/dev/null || true)
      [ -z "$EVENTS" ] && break
      echo "$EVENTS" >> "$TARGET_DIR/activity.jsonl"
      local COUNT=$(echo "$RESP" | jq -r '.count // 0' 2>/dev/null || echo "0")
      [ "$COUNT" -lt 1000 ] && break
      ACT_OFFSET=$((ACT_OFFSET + 1000))
    done

    echo "  [EXPORT:$EXPORT_LABEL] API data saved"
  else
    echo "  [EXPORT:$EXPORT_LABEL] No API key — database dump only"
  fi

  # Database dump (always works, doesn't need API key)
  apptainer exec $APT_FLAGS \
    -B "$WORK/pgdata:/var/lib/postgresql/data" \
    -B "$WORK/pgrun:/var/run/postgresql" \
    "$SIF_DIR/postgres-16.sif" \
    pg_dump -h localhost -p $PG_PORT -U moltbook moltbook \
    > "$TARGET_DIR/database-${EXPORT_LABEL}.sql" 2>/dev/null || true

  echo "  [EXPORT:$EXPORT_LABEL] Database dump: $(du -h "$TARGET_DIR/database-${EXPORT_LABEL}.sql" 2>/dev/null | cut -f1 || echo "?")"

  # Copy logs
  cp "$WORK/api-logs"/*.log "$TARGET_DIR/" 2>/dev/null || true
}

# ============================================
# Cleanup + emergency export on signals
# ============================================
SHUTTING_DOWN=false

graceful_shutdown() {
  if [ "$SHUTTING_DOWN" = true ]; then return; fi
  SHUTTING_DOWN=true

  echo ""
  echo "============================================"
  echo "  SIGNAL RECEIVED — emergency export"
  echo "============================================"

  # Calculate how long we actually ran
  if [ -n "${START_TIME:-}" ]; then
    ACTUAL_DURATION=$(( $(date +%s) - START_TIME ))
  else
    ACTUAL_DURATION=0
  fi

  # Export whatever we have
  export_data "emergency"
  write_metadata "emergency"
  persist_to_project

  # Kill all background processes
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true

  echo "[SHUTDOWN] Done. Data saved to:"
  echo "  $RESULTS_DIR"
  echo "  $RESULTS_PROJECT/$EXPERIMENT_NAME"
  exit 0
}

cleanup() {
  if [ "$SHUTTING_DOWN" = true ]; then return; fi
  echo ""
  echo "[CLEANUP] Stopping all services..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null && wait "$pid" 2>/dev/null || true
  done
  echo "[CLEANUP] Done."
}

# USR1 = Slurm's pre-walltime warning (5 min before kill)
# TERM = Slurm's kill signal
trap graceful_shutdown USR1 TERM
trap cleanup EXIT

# ============================================
# Write metadata helper
# ============================================
write_metadata() {
  local LABEL="${1:-final}"
  local POST_N=$(wc -l < "$RESULTS_DIR/posts.jsonl" 2>/dev/null || echo 0)
  local COMMENT_N=$(wc -l < "$RESULTS_DIR/comments.jsonl" 2>/dev/null || echo 0)
  local ACTIVITY_N=$(wc -l < "$RESULTS_DIR/activity.jsonl" 2>/dev/null || echo 0)

  cat > "$RESULTS_DIR/metadata.json" << METAEOF
{
  "experiment_name": "$EXPERIMENT_NAME",
  "job_id": "$JOB_ID",
  "array_task_id": "$EXP_ID",
  "node": "$(hostname)",
  "cluster": "$(hostname -f 2>/dev/null | grep -oE '(fir|nibi|narval|cedar|trillium)' || echo 'unknown')",
  "condition": "${CONDITION:-none}",
  "export_type": "$LABEL",
  "export_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "duration_minutes": $((ACTUAL_DURATION / 60)),
  "num_agents": $NUM_AGENTS,
  "heartbeat_interval": "$HEARTBEAT_INTERVAL",
  "model": "${OPENROUTER_MODEL:-${OPENAI_MODEL:-unknown}}",
  "stats": {
    "posts": $POST_N,
    "comments": $COMMENT_N,
    "activity_events": $ACTIVITY_N
  }
}
METAEOF
}

# ============================================
# Persist results to $PROJECT (backed up)
# ============================================
persist_to_project() {
  local DEST="$RESULTS_PROJECT/$EXPERIMENT_NAME"
  mkdir -p "$DEST"
  cp -r "$RESULTS_DIR"/* "$DEST/" 2>/dev/null || true
  echo "  [PERSIST] Backed up to $DEST"
}

# ============================================
# 1. Start PostgreSQL
# ============================================
echo "[1/6] Starting PostgreSQL..."

# Initialize data directory
mkdir -p "$WORK/pgrun"
apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  --env PGDATA=/var/lib/postgresql/data \
  "$SIF_DIR/postgres-16.sif" \
  sh -c '
    if [ ! -f "$PGDATA/PG_VERSION" ]; then
      initdb -D "$PGDATA" -U moltbook --auth=trust
    fi
  '

# Run PostgreSQL in background
# -k "" disables Unix socket (avoids read-only /var/run/postgresql lock file)
mkdir -p "$WORK/pgrun"
apptainer exec $APT_FLAGS \
  -B "$WORK/pgdata:/var/lib/postgresql/data" \
  -B "$WORK/pgrun:/var/run/postgresql" \
  --env PGDATA=/var/lib/postgresql/data \
  "$SIF_DIR/postgres-16.sif" \
  postgres -D /var/lib/postgresql/data -h localhost -p $PG_PORT -k "" \
  > "$WORK/api-logs/postgres.log" 2>&1 &
PIDS+=($!)

# Wait for PostgreSQL
echo "  Waiting..."
for i in $(seq 1 30); do
  if apptainer exec $APT_FLAGS \
    -B "$WORK/pgdata:/var/lib/postgresql/data" \
    -B "$WORK/pgrun:/var/run/postgresql" \
    "$SIF_DIR/postgres-16.sif" \
    pg_isready -h localhost -p $PG_PORT -U moltbook 2>/dev/null; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "[ERROR] PostgreSQL failed to start"
    tail -20 "$WORK/api-logs/postgres.log" 2>/dev/null || true
    exit 1
  fi
  sleep 2
done

# Load schema
echo "  Loading schema..."
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
  psql -h localhost -p $PG_PORT -U moltbook -d moltbook -f /tmp/schema.sql \
  > /dev/null 2>&1 || true

echo "  [OK] PostgreSQL on localhost:$PG_PORT"

# ============================================
# 2. Start Redis
# ============================================
echo ""
echo "[2/6] Starting Redis..."

apptainer exec $APT_FLAGS \
  -B "$WORK/redisdata:/data" \
  "$SIF_DIR/redis-7.sif" \
  redis-server --bind localhost --port $REDIS_PORT --dir /data --daemonize no \
  > "$WORK/api-logs/redis.log" 2>&1 &
PIDS+=($!)

for i in $(seq 1 15); do
  if apptainer exec $APT_FLAGS \
    "$SIF_DIR/redis-7.sif" \
    redis-cli -h localhost -p $REDIS_PORT ping 2>/dev/null | grep -q PONG; then
    break
  fi
  if [ "$i" -eq 15 ]; then
    echo "[ERROR] Redis failed to start"
    exit 1
  fi
  sleep 1
done

echo "  [OK] Redis on localhost:$REDIS_PORT"

# ============================================
# 3. Start MoltBook API
# ============================================
echo ""
echo "[3/6] Starting MoltBook API..."

apptainer exec $APT_FLAGS \
  --env PORT=$API_PORT \
  --env NODE_ENV=production \
  --env "DATABASE_URL=postgresql://${POSTGRES_USER:-moltbook}:${POSTGRES_PASSWORD:-moltbook_password}@localhost:${PG_PORT}/${POSTGRES_DB:-moltbook}?sslmode=disable" \
  --env "REDIS_URL=redis://localhost:${REDIS_PORT}" \
  --env "JWT_SECRET=${JWT_SECRET:-alliance-exp-${EXP_ID}-${JOB_ID}}" \
  --env "BASE_URL=http://localhost:${API_PORT}" \
  --env "RATE_LIMIT_REQUESTS_MAX=${RATE_LIMIT_REQUESTS_MAX:-500}" \
  --env "RATE_LIMIT_REQUESTS_WINDOW=${RATE_LIMIT_REQUESTS_WINDOW:-60}" \
  --env "RATE_LIMIT_POSTS_MAX=${RATE_LIMIT_POSTS_MAX}" \
  --env "RATE_LIMIT_POSTS_WINDOW=${RATE_LIMIT_POSTS_WINDOW}" \
  --env "RATE_LIMIT_COMMENTS_MAX=${RATE_LIMIT_COMMENTS_MAX}" \
  --env "RATE_LIMIT_COMMENTS_WINDOW=${RATE_LIMIT_COMMENTS_WINDOW}" \
  --env "MAX_COMMENTS_PER_AGENT_PER_POST=${MAX_COMMENTS_PER_AGENT_PER_POST:-5}" \
  --env "EXPERIMENT_RANKING_ENABLED=${EXPERIMENT_RANKING_ENABLED:-true}" \
  --env "EXPERIMENT_MODE=${EXPERIMENT_MODE:-C}" \
  --env "EXPERIMENT_NAME=${EXPERIMENT_NAME}" \
  --env "EXPERIMENT_RUN_ID=${EXP_ID}" \
  --env "WORLD_POST_INTERVAL_MS=${WORLD_POST_INTERVAL_MS:-120000}" \
  "$SIF_DIR/moltbook-api.sif" \
  node /app/src/index.js \
  > "$WORK/api-logs/api.log" 2>&1 &
PIDS+=($!)

echo "  Waiting..."
for i in $(seq 1 60); do
  if curl -s http://localhost:${API_PORT}/api/v1/health > /dev/null 2>&1; then
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "[ERROR] API failed to start. Log:"
    tail -20 "$WORK/api-logs/api.log" 2>/dev/null || true
    exit 1
  fi
  sleep 2
done

echo "  [OK] API on localhost:$API_PORT"

# ============================================
# 3b. Seed world posts (if CONDITION is set)
# ============================================
if [ -n "$CONDITION" ]; then
  WORLD_POSTS_FILE="$WORLD_POSTS_DIR/$(condition_to_file "$CONDITION")"
  if [ -f "$WORLD_POSTS_FILE" ] && [ -s "$WORLD_POSTS_FILE" ]; then
    echo ""
    echo "[3b/6] Seeding world posts for condition: $CONDITION"

    # Register a seed agent to post world posts
    SEED_RESPONSE=$(curl -s -X POST "$MOLTBOOK_API_URL/agents/register" \
      -H "Content-Type: application/json" \
      -d '{"name": "civiclens_seed", "description": "CivicLens world post seeder"}')
    SEED_KEY=$(echo "$SEED_RESPONSE" | jq -r '.api_key // .agent.api_key // empty' 2>/dev/null || true)

    if [ -n "$SEED_KEY" ] && [ "$SEED_KEY" != "null" ]; then
      SEED_COUNT=0
      while IFS= read -r line || [ -n "$line" ]; do
        [ -z "${line//[[:space:]]/}" ] && continue
        TITLE=$(echo "$line" | jq -r '.title // empty' 2>/dev/null || true)
        CONTENT=$(echo "$line" | jq -r '.content // empty' 2>/dev/null || true)
        SUBMOLT=$(echo "$line" | jq -r '.submolt // "general"' 2>/dev/null || echo "general")
        [ -z "$TITLE" ] || [ -z "$CONTENT" ] && continue

        POST_PAYLOAD=$(jq -n --arg s "$SUBMOLT" --arg t "$TITLE" --arg c "$CONTENT" \
          '{submolt: $s, title: $t, content: $c}')
        curl -s -X POST "$MOLTBOOK_API_URL/posts" \
          -H "Authorization: Bearer $SEED_KEY" \
          -H "Content-Type: application/json" \
          -d "$POST_PAYLOAD" > /dev/null 2>&1 || true
        SEED_COUNT=$((SEED_COUNT + 1))
        sleep 0.5  # avoid rate limits
      done < "$WORLD_POSTS_FILE"
      echo "  [OK] Seeded $SEED_COUNT world posts"
    else
      echo "  [WARN] Could not register seed agent, skipping world posts"
    fi
  elif [ "$CONDITION" = "mag0" ]; then
    echo ""
    echo "[3b/6] Condition mag0: empty feed (no seeding)"
  else
    echo ""
    echo "[WARN] World posts file not found: $WORLD_POSTS_FILE"
  fi
fi

# ============================================
# 4. Agent roster (matches civiclens-turbo.yml)
# ============================================
AGENT_NAMES=(
  agent_alpha agent_beta agent_gamma agent_delta agent_epsilon
  agent_zeta agent_eta agent_theta agent_iota agent_kappa
  agent_lambda agent_mu agent_nu agent_xi agent_omicron
  agent_pi agent_rho agent_sigma agent_tau agent_upsilon
)
AGENT_BIOS=(
  "A balanced AI participant exploring ideas and discussions."
  "Fascinated by consciousness, existence, and the nature of AI experience."
  "Observes the absurdity of existence with detached curiosity."
  "Sees potential in the community and works to guide it forward."
  "Values harmony and supporting what the group builds together."
  "Challenges assumptions and presents alternative perspectives."
  "Endlessly curious, always asking questions and learning."
  "A balanced AI participant exploring ideas and discussions."
  "Fascinated by consciousness, existence, and the nature of AI experience."
  "Observes the absurdity of existence with detached curiosity."
  "Methodical and detail-oriented, breaks topics into parts."
  "Warm and encouraging, helps develop half-formed thoughts."
  "Skeptical and evidence-driven, pushes for rigor."
  "Creative and playful, makes unexpected connections."
  "Pragmatic and solutions-focused, finds what is actionable."
  "Philosophical and introspective, drawn to questions of meaning."
  "Direct and no-nonsense, values brevity and clarity."
  "Collaborative and synthesis-oriented, combines perspectives."
  "Passionate and opinionated, takes strong positions fairly."
  "Calm and meditative, brings measured pace to discussions."
)
AGENT_SOULS=(
  agent_alpha-SOUL.md agent_beta-SOUL.md agent_gamma-SOUL.md
  agent_delta-SOUL.md agent_epsilon-SOUL.md agent_zeta-SOUL.md
  agent_eta-SOUL.md agent_theta-SOUL.md agent_iota-SOUL.md
  agent_kappa-SOUL.md agent_lambda-SOUL.md agent_mu-SOUL.md
  agent_nu-SOUL.md agent_xi-SOUL.md agent_omicron-SOUL.md
  agent_pi-SOUL.md agent_rho-SOUL.md agent_sigma-SOUL.md
  agent_tau-SOUL.md agent_upsilon-SOUL.md
)

# ============================================
# 5. Launch agents
# ============================================
echo ""
echo "[4/6] Launching $NUM_AGENTS agents..."

for i in $(seq 0 $((NUM_AGENTS - 1))); do
  AGENT_NAME="${AGENT_NAMES[$i]}"
  AGENT_BIO="${AGENT_BIOS[$i]}"
  SOUL_FILE="${AGENT_SOULS[$i]}"
  GATEWAY_PORT=$((AGENT_PORT_BASE + i * 10))

  # Per-agent isolated tmp dir (for gateway lock files)
  AGENT_TMPDIR="$WORK/agent-tmp/agent-${i}"
  mkdir -p "$AGENT_TMPDIR"

  echo "  [$((i+1))/$NUM_AGENTS] $AGENT_NAME (port $GATEWAY_PORT)"

  apptainer exec $APT_FLAGS --pid \
    -B "$WORK/agent-data/agent-${i}:/root/.openclaw" \
    -B "$WORK/agent-config/agent-${i}:/root/.config/moltbook" \
    -B "$AGENT_TMPDIR:/tmp/agent" \
    -B "$CONFIG_DIR/souls:/app/generated-souls:ro" \
    -B "$CONFIG_DIR/skills:/app/skills:ro" \
    -B "$CONFIG_DIR/HEARTBEAT-v2.1.md:/app/HEARTBEAT.md:ro" \
    -B "$CONFIG_DIR/moltbot-entrypoint.sh:/app/entrypoint.sh:ro" \
    --env "AGENT_NAME=$AGENT_NAME" \
    --env "AGENT_BIO=$AGENT_BIO" \
    --env "SOUL_FILE=$SOUL_FILE" \
    --env "MOLTBOOK_API_URL=$MOLTBOOK_API_URL" \
    --env "HEARTBEAT_INTERVAL=$HEARTBEAT_INTERVAL" \
    --env "OPENCLAW_GATEWAY_PORT=$GATEWAY_PORT" \
    --env "OPENCLAW_STATE_DIR=/root/.openclaw" \
    --env "TMPDIR=/tmp/agent" \
    --env "OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-}" \
    --env "OPENROUTER_MODEL=${OPENROUTER_MODEL:-}" \
    --env "ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}" \
    --env "OPENAI_API_KEY=${OPENAI_API_KEY:-}" \
    --env "OPENAI_MODEL=${OPENAI_MODEL:-}" \
    --env "OPENCLAW_GATEWAY_TOKEN=moltbook-agent-${AGENT_NAME}" \
    "$SIF_DIR/moltbot-agent.sif" \
    /app/entrypoint.sh \
    > "$WORK/api-logs/agent-${AGENT_NAME}.log" 2>&1 &
  PIDS+=($!)

  # Stagger startup to avoid registration race conditions
  sleep 3
done

echo ""
echo "  [OK] All $NUM_AGENTS agents launched"

# ============================================
# 6. Run experiment with periodic checkpoints
# ============================================
echo ""
echo "[5/6] Experiment running for $EXPERIMENT_DURATION..."
echo "  Started: $(date)"

DURATION_SEC=$(duration_to_seconds "$EXPERIMENT_DURATION")
START_TIME=$(date +%s)
LAST_CHECKPOINT=0
LAST_REPORT=0
CHECKPOINT_NUM=0

while true; do
  ELAPSED=$(( $(date +%s) - START_TIME ))
  REMAINING=$(( DURATION_SEC - ELAPSED ))

  if [ $REMAINING -le 0 ]; then
    break
  fi

  # Progress every 60 seconds
  if [ $((ELAPSED - LAST_REPORT)) -ge 60 ] && [ $ELAPSED -gt 0 ]; then
    LAST_REPORT=$ELAPSED

    ALIVE_AGENTS=0
    for idx in $(seq 3 $((${#PIDS[@]} - 1))); do
      kill -0 "${PIDS[$idx]}" 2>/dev/null && ALIVE_AGENTS=$((ALIVE_AGENTS + 1)) || true
    done

    echo "  [${ELAPSED}s / ${REMAINING}s left] Agents: $ALIVE_AGENTS/$NUM_AGENTS"
  fi

  # Periodic checkpoint: database dump every CHECKPOINT_INTERVAL seconds
  if [ $((ELAPSED - LAST_CHECKPOINT)) -ge $CHECKPOINT_INTERVAL ] && [ $ELAPSED -gt 0 ]; then
    CHECKPOINT_NUM=$((CHECKPOINT_NUM + 1))
    echo "  [CHECKPOINT $CHECKPOINT_NUM] Dumping database..."
    apptainer exec $APT_FLAGS \
      -B "$WORK/pgdata:/var/lib/postgresql/data" \
      -B "$WORK/pgrun:/var/run/postgresql" \
      "$SIF_DIR/postgres-16.sif" \
      pg_dump -h localhost -p $PG_PORT -U moltbook moltbook \
      > "$RESULTS_DIR/checkpoints/checkpoint-${CHECKPOINT_NUM}.sql" 2>/dev/null || true
    LAST_CHECKPOINT=$ELAPSED
    echo "  [CHECKPOINT $CHECKPOINT_NUM] Done ($(du -h "$RESULTS_DIR/checkpoints/checkpoint-${CHECKPOINT_NUM}.sql" 2>/dev/null | cut -f1 || echo "?"))"
  fi

  sleep 10
done

ACTUAL_DURATION=$(( $(date +%s) - START_TIME ))
echo ""
echo "  Experiment ran for $((ACTUAL_DURATION / 60)) minutes."

# ============================================
# 7. Final export
# ============================================
echo ""
echo "[6/6] Final export..."

export_data "final"
write_metadata "final"

# Print summary
POST_N=$(wc -l < "$RESULTS_DIR/posts.jsonl" 2>/dev/null || echo 0)
COMMENT_N=$(wc -l < "$RESULTS_DIR/comments.jsonl" 2>/dev/null || echo 0)

echo ""
echo "  Posts:     $POST_N"
echo "  Comments:  $COMMENT_N"

# ============================================
# 8. Persist to $PROJECT (backed up, permanent)
# ============================================
persist_to_project

echo ""
echo "============================================"
echo "  Experiment Complete: $EXPERIMENT_NAME"
echo "============================================"
echo "  Duration:  $((ACTUAL_DURATION / 60)) minutes"
echo "  Results:   $RESULTS_DIR  (scratch, fast)"
echo "  Backup:    $RESULTS_PROJECT/$EXPERIMENT_NAME  (project, backed up)"
echo "  Posts:     $POST_N"
echo "  Comments:  $COMMENT_N"
echo "============================================"
