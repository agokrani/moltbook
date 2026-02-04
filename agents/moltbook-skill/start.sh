#!/bin/bash
set -e

echo "🤖 Starting Moltbook Agent: ${AGENT_NAME:-unnamed}"
echo "   Moltbook API: ${MOLTBOOK_API_URL}"

# Show which AI provider is configured
if [ -n "$OPENROUTER_API_KEY" ]; then
  echo "   AI Provider: OpenRouter"
  echo "   Model: ${OPENROUTER_MODEL:-moonshotai/kimi-k2.5}"
elif [ -n "$ANTHROPIC_API_KEY" ]; then
  echo "   AI Provider: Anthropic (Claude)"
elif [ -n "$OPENAI_API_KEY" ]; then
  echo "   AI Provider: OpenAI"
else
  echo "   ⚠️  No AI API key configured!"
  exit 1
fi

# Wait for Moltbook API to be ready
echo "⏳ Waiting for Moltbook API..."
until curl -s "${MOLTBOOK_API_URL}/posts?limit=1" > /dev/null 2>&1; do
  echo "   Still waiting..."
  sleep 3
done
echo "✅ Moltbook API is ready"

# Register agent with Moltbook if not already registered
CREDENTIALS_FILE="/root/.openclaw/moltbook_credentials.json"

if [ ! -f "$CREDENTIALS_FILE" ]; then
  echo "📝 Registering agent with Moltbook..."

  RESPONSE=$(curl -s -X POST "${MOLTBOOK_API_URL}/agents/register" \
    -H "Content-Type: application/json" \
    -d "{\"name\": \"${AGENT_NAME}\", \"description\": \"${AGENT_BIO}\"}")

  # Check if registration was successful
  if echo "$RESPONSE" | grep -q "api_key"; then
    echo "$RESPONSE" > "$CREDENTIALS_FILE"
    echo "✅ Agent registered successfully"
  else
    echo "⚠️  Registration response: $RESPONSE"
    echo "   Agent may already exist, trying to continue..."
  fi
fi

# Get API key from credentials
if [ -f "$CREDENTIALS_FILE" ]; then
  export MOLTBOOK_API_KEY=$(cat "$CREDENTIALS_FILE" | sed -n 's/.*"api_key":"\([^"]*\)".*/\1/p')
  echo "✅ Using saved Moltbook API key"
fi

if [ -z "$MOLTBOOK_API_KEY" ]; then
  echo "❌ No Moltbook API key available"
  exit 1
fi

# Start the agent loop
echo "🚀 Starting agent activity loop..."
exec node /app/agent-loop.js
