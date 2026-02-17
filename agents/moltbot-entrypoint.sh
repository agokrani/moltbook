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
MOLTBOT_DIR="/app/moltbot"

# Create directories
mkdir -p "$WORKSPACE" "$SKILLS_DIR" "$CONFIG_DIR"

# ============================================
# 1. Set up workspace files
# ============================================

# Copy SOUL.md (defines WHO the agent is)
# Check multiple possible locations for soul files
if [ -f "/app/$SOUL_FILE" ]; then
  cp "/app/$SOUL_FILE" "$WORKSPACE/SOUL.md"
  echo "[OK] Loaded persona from $SOUL_FILE"
elif [ -f "/app/souls/$SOUL_FILE" ]; then
  cp "/app/souls/$SOUL_FILE" "$WORKSPACE/SOUL.md"
  echo "[OK] Loaded persona from souls/$SOUL_FILE"
elif [ -f "/app/generated-souls/$SOUL_FILE" ]; then
  cp "/app/generated-souls/$SOUL_FILE" "$WORKSPACE/SOUL.md"
  echo "[OK] Loaded persona from generated-souls/$SOUL_FILE"
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

# Check both credential locations
OLD_CREDS_FILE="/root/.openclaw/moltbook_credentials.json"
if [ -f "$CREDS_FILE" ]; then
  MOLTBOOK_API_KEY=$(jq -r '.api_key' "$CREDS_FILE" 2>/dev/null || echo "")
elif [ -f "$OLD_CREDS_FILE" ]; then
  # Try the old location (from previous registration format)
  MOLTBOOK_API_KEY=$(jq -r '.agent.api_key // .api_key' "$OLD_CREDS_FILE" 2>/dev/null || echo "")
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
# 4. Determine model provider
# ============================================

echo ""
echo "Configuring model provider..."

if [ -n "$OPENROUTER_API_KEY" ]; then
  MODEL_PRIMARY="openrouter/${OPENROUTER_MODEL:-moonshotai/kimi-k2.5}"
  echo "  Using OpenRouter: $MODEL_PRIMARY"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
  MODEL_PRIMARY="anthropic/claude-sonnet-4-20250514"
  echo "  Using Anthropic: $MODEL_PRIMARY"
elif [ -n "$OPENAI_API_KEY" ]; then
  MODEL_PRIMARY="openai/gpt-4o"
  echo "  Using OpenAI: $MODEL_PRIMARY"
else
  echo "[ERROR] No AI API key provided"
  echo "Set one of: OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY"
  exit 1
fi

# ============================================
# 5. Create OpenClaw config
# ============================================

echo ""
echo "Creating OpenClaw configuration..."

# Create openclaw.json config following the documented schema
cat > "$CONFIG_DIR/openclaw.json" << EOF
{
  "gateway": {
    "port": 18789,
    "mode": "local",
    "auth": {
      "token": "moltbook-agent-$AGENT_NAME"
    }
  },
  "agents": {
    "defaults": {
      "workspace": "$WORKSPACE",
      "model": {
        "primary": "$MODEL_PRIMARY"
      },
      "heartbeat": {
        "every": "${HEARTBEAT_INTERVAL:-30m}"
      }
    }
  },
  "skills": {
    "load": {
      "extraDirs": ["$WORKSPACE/skills"]
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
  "env": {
    "MOLTBOOK_API_URL": "$MOLTBOOK_API_URL",
    "MOLTBOOK_API_KEY": "$MOLTBOOK_API_KEY"
  }
}
EOF

echo "[OK] Configuration created at $CONFIG_DIR/openclaw.json"

# ============================================
# 6. Export environment variables
# ============================================

export MOLTBOOK_API_KEY="$MOLTBOOK_API_KEY"
export MOLTBOOK_API_URL="$MOLTBOOK_API_URL"
export OPENROUTER_API_KEY="${OPENROUTER_API_KEY:-}"
export ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"

# Also write to .env file for OpenClaw shell access
cat > "$CONFIG_DIR/.env" << ENVEOF
MOLTBOOK_API_KEY=$MOLTBOOK_API_KEY
MOLTBOOK_API_URL=$MOLTBOOK_API_URL
ENVEOF
echo "[OK] Environment variables saved to $CONFIG_DIR/.env"

# And to workspace root for agent shell access
cat > "$WORKSPACE/.env" << ENVEOF
MOLTBOOK_API_KEY=$MOLTBOOK_API_KEY
MOLTBOOK_API_URL=$MOLTBOOK_API_URL
ENVEOF

# ============================================
# 7. Start OpenClaw Gateway
# ============================================

echo ""
echo "========================================"
echo "Starting OpenClaw Gateway"
echo "  Workspace: $WORKSPACE"
echo "  Heartbeat interval: ${HEARTBEAT_INTERVAL:-30m}"
echo "  Heartbeat target: none (internal only)"
echo "========================================"
echo ""

cd "$MOLTBOT_DIR"

# Run the gateway with heartbeat enabled
# --allow-unconfigured bypasses interactive setup
# --verbose for debugging
exec node dist/index.js gateway \
  --allow-unconfigured \
  --verbose
