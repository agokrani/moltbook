#!/usr/bin/env bash
#SBATCH --job-name=semantic-diversity
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --gres=gpu:nvidia_h100_80gb_hbm3_3g.40gb:1
#
# Run semantic diversity analysis on Alliance with a real embedding model.
#
# Submit:
#   sbatch --account=def-zhijing alliance/slurm-semantic-diversity.sh
#   sbatch --account=def-zhijing alliance/slurm-semantic-diversity.sh \
#     "OLMo Base=/scratch/anangia/moltbook/results/base-model-olmo3-32b-base" \
#     "OLMo Instruct=/scratch/anangia/moltbook/results/base-model-olmo3-32b-instruct"

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SCRATCH_DIR="${SCRATCH:-/scratch/$USER}"
PY_ENV="${PY_ENV:-$SCRATCH_DIR/envs/vllm}"
HF_HOME="${HF_HOME:-$SCRATCH_DIR/hf-cache}"
OUTPUT_ROOT="${OUTPUT_ROOT:-$SCRATCH_DIR/moltbook/analysis/semantic-diversity-$(date +%Y%m%d-%H%M%S)}"
JSON_PATH="${JSON_PATH:-$OUTPUT_ROOT/semantic-diversity.json}"
EMBEDDING_MODEL="${EMBEDDING_MODEL:-BAAI/bge-large-en-v1.5}"
N_CLUSTERS="${N_CLUSTERS:-15}"
N_QUARTILES="${N_QUARTILES:-4}"
SVD_DIM="${SVD_DIM:-128}"
BATCH_SIZE="${BATCH_SIZE:-64}"

EXPERIMENTS=(
  "OLMo Base=/scratch/anangia/moltbook/results/base-model-olmo3-32b-base"
  "OLMo Instruct=/scratch/anangia/moltbook/results/base-model-olmo3-32b-instruct"
)
if [ "$#" -gt 0 ]; then
  EXPERIMENTS=("$@")
fi

module load python/3.11.5 2>/dev/null || module load python/3.10.13 2>/dev/null || true
module load cuda/12.6 2>/dev/null || module load cuda/12.2 2>/dev/null || true

if [ ! -f "$PY_ENV/bin/activate" ]; then
  echo "[ERROR] Python environment not found: $PY_ENV"
  echo "Set PY_ENV to an env with torch/scikit-learn, or create one first."
  exit 1
fi

source "$PY_ENV/bin/activate"

python -c "import sentence_transformers, matplotlib, sklearn" >/dev/null 2>&1 || {
  echo "[setup] Installing sentence-transformers dependencies into $PY_ENV"
  pip install --no-cache-dir "sentence-transformers>=3,<4" "matplotlib>=3.8"
}

mkdir -p "$OUTPUT_ROOT"
export HF_HOME
export TRANSFORMERS_CACHE="$HF_HOME"

echo "============================================"
echo "  Semantic Diversity Analysis"
echo "============================================"
echo "  Node:            $(hostname)"
echo "  GPU:             $(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | head -1)"
echo "  Env:             $PY_ENV"
echo "  HF cache:        $HF_HOME"
echo "  Embedding model: $EMBEDDING_MODEL"
echo "  Output dir:      $OUTPUT_ROOT"
echo "  JSON path:       $JSON_PATH"
echo "  Experiment sets:"
for exp in "${EXPERIMENTS[@]}"; do
  echo "    $exp"
done
echo "============================================"

python "$REPO_DIR/scripts/analyze-semantic-diversity.py" \
  --experiments "${EXPERIMENTS[@]}" \
  --embedding-backend sentence-transformers \
  --embedding-model "$EMBEDDING_MODEL" \
  --device auto \
  --batch-size "$BATCH_SIZE" \
  --n-clusters "$N_CLUSTERS" \
  --svd-dim "$SVD_DIM" \
  --n-quartiles "$N_QUARTILES" \
  --output-dir "$OUTPUT_ROOT" \
  --json "$JSON_PATH"

echo
echo "[done] Semantic plots: $OUTPUT_ROOT"
echo "[done] Semantic JSON:  $JSON_PATH"
