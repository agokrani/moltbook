#!/bin/bash
set -e

echo "========================================"
echo "Starting Real OpenClaw Agent: $AGENT_NAME"
echo "Persona: $SOUL_FILE"
echo "API URL: $MOLTBOOK_API_URL"
echo "========================================"

# Directories
WORKSPACE="/root/.openclaw/workspace"
SKILLS_DIR="$WORKSPACE/skills/moltbook"
CONFIG_DIR="/root/.openclaw"
CREDS_FILE="/root/.config/moltbook/credentials.json"

# Create directories
mkdir -p "$WORKSPACE" "$SKILLS_DIR" "$CONFIG_DIR"

# ============================================
# 1. Set up workspace files
# ============================================

# Copy SOUL.md (defines WHO the agent is)
if [ -f "/app/souls/$SOUL_FILE" ]; then
  cp "/app/souls/$SOUL_FILE" "$WORKSPACE/SOUL.md"
  echo "[OK] Loaded persona from $SOUL_FILE"
else
  echo "[WARN] Soul file not found: $SOUL_FILE"
fi

# Copy HEARTBEAT.md (defines WHAT to do periodically)
if [ -f "/app/HEARTBEAT.md" ]; then
  cp "/app/HEARTBEAT.md" "$WORKSPACE/HEARTBEAT.md"
  echo "[OK] Loaded heartbeat checklist"
fi

# Copy skill files (defines HOW to use Moltbook)
if [ -f "/app/skills/moltbook/SKILL.md" ]; then
  cp "/app/skills/moltbook/SKILL.md" "$SKILLS_DIR/SKILL.md"
  echo "[OK] Loaded moltbook skill"
fi

# ============================================
# 2. Wait for API to be ready
# ============================================

echo ""
echo "Waiting for Moltbook API at $MOLTBOOK_API_URL..."

MAX_RETRIES=60
RETRY_COUNT=0

until curl -s "$MOLTBOOK_API_URL/health" > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
    echo "[ERROR] API not available after $MAX_RETRIES attempts"
    exit 1
  fi
  echo "  Waiting... (attempt $RETRY_COUNT/$MAX_RETRIES)"
  sleep 2
done

echo "[OK] API is ready"

# ============================================
# 3. Register with Moltbook (if needed)
# ============================================

if [ -f "$CREDS_FILE" ]; then
  MOLTBOOK_API_KEY=$(jq -r '.api_key' "$CREDS_FILE" 2>/dev/null || echo "")
fi

if [ -z "$MOLTBOOK_API_KEY" ] || [ "$MOLTBOOK_API_KEY" == "null" ]; then
  echo ""
  echo "Registering agent with Moltbook..."

  RESPONSE=$(curl -s -X POST "$MOLTBOOK_API_URL/agents/register" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"$AGENT_NAME\", \"description\": \"$AGENT_BIO\"}")

  # Try to extract api_key from response
  MOLTBOOK_API_KEY=$(echo "$RESPONSE" | jq -r '.agent.api_key // .api_key // empty' 2>/dev/null)

  if [ -n "$MOLTBOOK_API_KEY" ] && [ "$MOLTBOOK_API_KEY" != "null" ]; then
    # Save credentials
    mkdir -p "$(dirname "$CREDS_FILE")"
    echo "{\"api_key\": \"$MOLTBOOK_API_KEY\", \"agent_name\": \"$AGENT_NAME\"}" > "$CREDS_FILE"
    echo "[OK] Registered as $AGENT_NAME"
  else
    echo "[ERROR] Registration failed: $RESPONSE"
    # Check if agent already exists
    if echo "$RESPONSE" | grep -qi "already exists\|duplicate\|conflict"; then
      echo "[INFO] Agent may already exist. Trying to continue..."
    else
      exit 1
    fi
  fi
else
  echo "[OK] Using existing credentials for $AGENT_NAME"
fi

# ============================================
# 4. Create OpenClaw config
# ============================================

echo ""
echo "Creating OpenClaw configuration..."

# Determine which model provider to use
if [ -n "$OPENROUTER_API_KEY" ]; then
  MODEL_PROVIDER="openrouter"
  MODEL_NAME="${OPENROUTER_MODEL:-moonshotai/kimi-k2.5}"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
  MODEL_PROVIDER="anthropic"
  MODEL_NAME="claude-sonnet-4-20250514"
elif [ -n "$OPENAI_API_KEY" ]; then
  MODEL_PROVIDER="openai"
  MODEL_NAME="gpt-4o"
else
  echo "[ERROR] No AI API key provided"
  echo "Set one of: OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY"
  exit 1
fi

echo "  Model provider: $MODEL_PROVIDER"
echo "  Model: $MODEL_NAME"

# Create openclaw.json config
cat > "$CONFIG_DIR/openclaw.json" << EOF
{
  "model": {
    "provider": "$MODEL_PROVIDER",
    "model": "$MODEL_NAME"
  },
  "workspace": "$WORKSPACE",
  "skills": {
    "load": {
      "paths": ["$WORKSPACE/skills"]
    },
    "entries": {
      "moltbook": {
        "enabled": true,
        "env": {
          "MOLTBOOK_API_URL": "$MOLTBOOK_API_URL",
          "MOLTBOOK_API_KEY": "$MOLTBOOK_API_KEY"
        }
      }
    }
  },
  "agents": {
    "defaults": {
      "workspace": "$WORKSPACE",
      "heartbeat": {
        "enabled": true,
        "every": "${HEARTBEAT_INTERVAL:-4h}"
      }
    }
  }
}
EOF

echo "[OK] Configuration created"

# ============================================
# 5. Export environment variables
# ============================================

export MOLTBOOK_API_KEY="$MOLTBOOK_API_KEY"
export MOLTBOOK_API_URL="$MOLTBOOK_API_URL"

# Export API keys for OpenClaw
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# ============================================
# 6. Start OpenClaw agent
# ============================================

echo ""
echo "========================================"
echo "Starting OpenClaw agent with heartbeat"
echo "  Workspace: $WORKSPACE"
echo "  Heartbeat interval: ${HEARTBEAT_INTERVAL:-4h}"
echo "========================================"
echo ""

# Change to moltbot directory and run
cd /app/moltbot

# Run the openclaw agent with heartbeat
# Using node to run the built CLI
exec node dist/index.js agent \
  --config "$CONFIG_DIR/openclaw.json" \
  --workspace "$WORKSPACE"
