#!/usr/bin/env bash
# Build Apptainer SIF images for MoltBook on Alliance Canada
#
# Run this on a machine with BOTH Docker and Apptainer installed.
# (Your local machine, or a CI runner.)
#
# After building, transfer the .sif files to the cluster:
#   scp alliance/images/*.sif youruser@nibi.alliancecan.ca:~/
#   # Then on cluster: mv ~/*.sif $PROJECT/moltbook/images/
#
# Usage: ./alliance/build-sif-images.sh [--push <cluster>]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
IMAGE_DIR="$SCRIPT_DIR/images"
PUSH_TARGET=""

# Parse args
while [[ $# -gt 0 ]]; do
  case $1 in
    --push) PUSH_TARGET="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

mkdir -p "$IMAGE_DIR"

echo "============================================"
echo "  MoltBook SIF Image Builder"
echo "============================================"
echo ""

# ============================================
# 1. Standard images (pull directly)
# ============================================
echo "[1/4] Building PostgreSQL 16 SIF..."
if [ ! -f "$IMAGE_DIR/postgres-16.sif" ]; then
  apptainer build "$IMAGE_DIR/postgres-16.sif" docker://postgres:16-alpine
else
  echo "  Already exists, skipping. Delete to rebuild."
fi

echo ""
echo "[2/4] Building Redis 7 SIF..."
if [ ! -f "$IMAGE_DIR/redis-7.sif" ]; then
  apptainer build "$IMAGE_DIR/redis-7.sif" docker://redis:7-alpine
else
  echo "  Already exists, skipping."
fi

# ============================================
# 2. Custom images (build from Dockerfile)
# ============================================
echo ""
echo "[3/4] Building MoltBook API SIF..."
if [ ! -f "$IMAGE_DIR/moltbook-api.sif" ]; then
  cd "$PROJECT_DIR/moltbook-api"
  docker build -f Dockerfile -t moltbook-api .
  docker save moltbook-api -o /tmp/moltbook-api.tar
  docker image rm moltbook-api
  apptainer build "$IMAGE_DIR/moltbook-api.sif" docker-archive:///tmp/moltbook-api.tar
  rm /tmp/moltbook-api.tar
else
  echo "  Already exists, skipping."
fi

echo ""
echo "[4/4] Building MoltBot Agent SIF..."
if [ ! -f "$IMAGE_DIR/moltbot-agent.sif" ]; then
  cd "$PROJECT_DIR/agents"
  # Build with HEARTBEAT-v2.md (turbo/civiclens default)
  docker build -f Dockerfile.moltbot --build-arg HEARTBEAT_FILE=HEARTBEAT-v2.md -t moltbot-agent .
  docker save moltbot-agent -o /tmp/moltbot-agent.tar
  docker image rm moltbot-agent
  apptainer build "$IMAGE_DIR/moltbot-agent.sif" docker-archive:///tmp/moltbot-agent.tar
  rm /tmp/moltbot-agent.tar
else
  echo "  Already exists, skipping."
fi

cd "$PROJECT_DIR"

echo ""
echo "============================================"
echo "  Build Complete"
echo "============================================"
echo ""
echo "Images:"
ls -lh "$IMAGE_DIR"/*.sif 2>/dev/null || echo "  (none found)"
echo ""

# Optional: push to cluster
if [ -n "$PUSH_TARGET" ]; then
  echo "Transferring images to $PUSH_TARGET..."
  echo "  This may take a while (images are large)."
  echo ""
  scp "$IMAGE_DIR"/*.sif "${PUSH_TARGET}:~/"
  echo ""
  echo "Done! On the cluster, run:"
  echo "  mkdir -p \$PROJECT/moltbook/images"
  echo "  mv ~/*.sif \$PROJECT/moltbook/images/"
fi
