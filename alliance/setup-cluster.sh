#!/usr/bin/env bash
# One-time setup for MoltBook on Alliance Canada clusters
#
# Run this ONCE after transferring SIF images to the cluster.
# It creates the directory structure and validates the environment.
#
# Usage: bash alliance/setup-cluster.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "  MoltBook Alliance Setup"
echo "============================================"
echo ""

# ============================================
# 1. Check environment
# ============================================
echo "[1/5] Checking environment..."

# Must be on a supported cluster
HOSTNAME=$(hostname -f 2>/dev/null || hostname)
if echo "$HOSTNAME" | grep -qE "(fir|nibi)"; then
  echo "  Cluster: $(echo "$HOSTNAME" | grep -oE '(fir|nibi)')"
else
  echo "  WARNING: You appear to be on '$HOSTNAME'."
  echo "  MoltBook agents need internet access on compute nodes."
  echo "  Only Fir and Nibi support this. Other clusters will fail."
  echo ""
  read -p "  Continue anyway? [y/N] " -n 1 -r
  echo ""
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
  fi
fi

# Check required env vars
for var in PROJECT SCRATCH; do
  if [ -z "${!var:-}" ]; then
    echo "  ERROR: \$$var is not set. Are you on a login node?"
    exit 1
  fi
done
echo "  \$PROJECT = $PROJECT"
echo "  \$SCRATCH = $SCRATCH"

# ============================================
# 2. Create directory structure
# ============================================
echo ""
echo "[2/5] Creating directory structure..."

SIF_DIR="$PROJECT/moltbook/images"
CONFIG_DIR="$PROJECT/moltbook/config"
RESULTS_DIR="$SCRATCH/moltbook/results"

mkdir -p "$SIF_DIR" "$CONFIG_DIR" "$RESULTS_DIR"

echo "  $SIF_DIR         (SIF images — persistent)"
echo "  $CONFIG_DIR      (env/config — persistent)"
echo "  $RESULTS_DIR     (experiment results — on scratch)"

# ============================================
# 3. Check SIF images
# ============================================
echo ""
echo "[3/5] Checking SIF images..."

MISSING=0
for img in postgres-16.sif redis-7.sif moltbook-api.sif moltbot-agent.sif; do
  if [ -f "$SIF_DIR/$img" ]; then
    SIZE=$(ls -lh "$SIF_DIR/$img" | awk '{print $5}')
    echo "  [OK] $img ($SIZE)"
  elif [ -f "$HOME/$img" ]; then
    echo "  Moving $HOME/$img -> $SIF_DIR/$img"
    mv "$HOME/$img" "$SIF_DIR/$img"
  else
    echo "  [MISSING] $img"
    MISSING=$((MISSING + 1))
  fi
done

if [ $MISSING -gt 0 ]; then
  echo ""
  echo "  $MISSING image(s) missing. Build them locally with:"
  echo "    ./alliance/build-sif-images.sh --push $USER@$(hostname)"
  echo ""
  echo "  Or transfer manually:"
  echo "    scp *.sif $USER@$(hostname):~/"
  echo "    # Then re-run this script"
fi

# ============================================
# 4. Copy configuration
# ============================================
echo ""
echo "[4/5] Setting up configuration..."

# Copy env template if no .env exists yet
if [ ! -f "$CONFIG_DIR/.env" ]; then
  cp "$SCRIPT_DIR/env.template" "$CONFIG_DIR/.env"
  echo "  Created $CONFIG_DIR/.env from template"
  echo "  IMPORTANT: Edit this file with your API keys and account info:"
  echo "    nano $CONFIG_DIR/.env"
else
  echo "  $CONFIG_DIR/.env already exists"
fi

# Copy schema.sql for database initialization
cp "$PROJECT_DIR/moltbook-api/scripts/schema.sql" "$CONFIG_DIR/schema.sql"
echo "  Copied schema.sql"

# Copy soul files
if [ -d "$PROJECT_DIR/agents/generated-souls" ]; then
  cp -r "$PROJECT_DIR/agents/generated-souls" "$CONFIG_DIR/souls"
  echo "  Copied generated soul files"
elif [ -d "$PROJECT_DIR/agents/souls" ]; then
  cp -r "$PROJECT_DIR/agents/souls" "$CONFIG_DIR/souls"
  echo "  Copied soul files"
fi

# Copy heartbeat files
for hb in "$PROJECT_DIR"/agents/HEARTBEAT*.md; do
  if [ -f "$hb" ]; then
    cp "$hb" "$CONFIG_DIR/"
  fi
done
echo "  Copied heartbeat files"

# Copy skill files
mkdir -p "$CONFIG_DIR/skills/moltbook"
cp "$PROJECT_DIR/agents/skills/moltbook/SKILL.md" "$CONFIG_DIR/skills/moltbook/SKILL.md"
echo "  Copied skill files"

# Copy example agent rosters for custom multi-agent composition
if [ -f "$SCRIPT_DIR/agent-roster.example.json" ]; then
  cp "$SCRIPT_DIR/agent-roster.example.json" "$CONFIG_DIR/agent-roster.example.json"
  echo "  Copied example agent roster"
fi
if [ -f "$SCRIPT_DIR/agent-roster.gemini-openrouter.example.json" ]; then
  cp "$SCRIPT_DIR/agent-roster.gemini-openrouter.example.json" "$CONFIG_DIR/agent-roster.gemini-openrouter.example.json"
  echo "  Copied Gemini/OpenRouter agent roster example"
fi
if [ -f "$SCRIPT_DIR/agent-roster.gemini-cheap-openrouter.example.json" ]; then
  cp "$SCRIPT_DIR/agent-roster.gemini-cheap-openrouter.example.json" "$CONFIG_DIR/agent-roster.gemini-cheap-openrouter.example.json"
  echo "  Copied mixed cheap Gemini/OpenRouter agent roster example"
fi

# Copy api-patches (runtime overrides bind-mounted into the API container)
if [ -d "$SCRIPT_DIR/api-patches" ]; then
  mkdir -p "$CONFIG_DIR/api-patches"
  cp "$SCRIPT_DIR/api-patches/"*.js "$CONFIG_DIR/api-patches/" 2>/dev/null && \
    echo "  Copied api-patches"
fi

# Copy world-posts seed files for entropy-collapse conditions
mkdir -p "$CONFIG_DIR/world-posts"
for wp in "$PROJECT_DIR"/experiments/entropy-collapse/world-posts-*.jsonl; do
  [ -f "$wp" ] && cp "$wp" "$CONFIG_DIR/world-posts/"
done
echo "  Copied world-posts seed files"

# ============================================
# 5. Redirect Apptainer cache
# ============================================
echo ""
echo "[5/5] Configuring Apptainer cache..."

CACHE_DIR="$SCRATCH/apptainer"
mkdir -p "$CACHE_DIR/cache" "$CACHE_DIR/tmp"

if ! grep -q "APPTAINER_CACHEDIR" "$HOME/.bashrc" 2>/dev/null; then
  cat >> "$HOME/.bashrc" << 'BASHEOF'

# Apptainer cache (MoltBook setup)
export APPTAINER_CACHEDIR="$SCRATCH/apptainer/cache"
export APPTAINER_TMPDIR="$SCRATCH/apptainer/tmp"
BASHEOF
  echo "  Added Apptainer cache exports to ~/.bashrc"
else
  echo "  Apptainer cache already configured in ~/.bashrc"
fi

echo ""
echo "============================================"
echo "  Setup Complete"
echo "============================================"
echo ""
echo "Next steps:"
echo ""
if [ $MISSING -gt 0 ]; then
  echo "  1. Build and transfer missing SIF images (see above)"
  echo "  2. Edit your config: nano $CONFIG_DIR/.env"
  echo "  3. Submit an experiment: bash alliance/slurm-experiment.sh"
else
  echo "  1. Edit your config: nano $CONFIG_DIR/.env"
  echo "  2. Submit an experiment: bash alliance/slurm-experiment.sh"
fi
echo ""
