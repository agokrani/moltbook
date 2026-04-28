#!/usr/bin/env bash
# Run the full analysis suite on the base-model experiments dataset.
#
# Dataset: moltbook-ec-10m-base-model-experiments/data/{model}/
# Models:  qwen-base, qwen-instruct, gemini-flash-lite
# Duration: 10 minutes per run, 10 agents, 6 conditions each
#
# Usage:
#   ./scripts/analysis_new/run_base_model_analysis.sh
#   ./scripts/analysis_new/run_base_model_analysis.sh qwen-base   # single model

set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

DATASET_DIR="moltbook-ec-10m-base-model-experiments/data"
FINDINGS_DIR="findings/base-model-experiments"
DURATION=10
SCALES="n10"
BIN_EDGES="0,2.5,5,7.5,10"

MODELS=("qwen-base" "qwen-instruct" "gemini-flash-lite")
SCRIPTS_DIR="scripts/analysis_new"

# Allow running a single model
if [[ ${1:-} ]]; then
    MODELS=("$1")
fi

for model in "${MODELS[@]}"; do
    data_dir="${DATASET_DIR}/${model}"
    out_base="${FINDINGS_DIR}/${model}"

    if [[ ! -d "$data_dir" ]]; then
        echo "SKIP: $data_dir not found"
        continue
    fi

    echo ""
    echo "================================================================"
    echo "  MODEL: $model"
    echo "  DATA:  $data_dir"
    echo "  OUT:   $out_base"
    echo "================================================================"

    # 1. N-gram provenance (no time dependency)
    echo ""
    echo "--- [1/8] N-gram provenance ---"
    python3 "$SCRIPTS_DIR/ngram_provenance.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/provenance"

    # 2. Diversity metrics
    echo ""
    echo "--- [2/8] Diversity metrics ---"
    python3 "$SCRIPTS_DIR/diversity_metrics.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/diversity" \
        --duration "$DURATION"

    # 3. Phrase diffusion
    echo ""
    echo "--- [3/8] Phrase diffusion ---"
    python3 "$SCRIPTS_DIR/phrase_diffusion.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/diffusion" \
        --duration "$DURATION"

    # 4. Agent participation
    echo ""
    echo "--- [4/8] Agent participation ---"
    python3 "$SCRIPTS_DIR/agent_participation.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/participation" \
        --duration "$DURATION"

    # 5. Time-binned lexical metrics (bigrams)
    echo ""
    echo "--- [5/8] Time-binned lexical metrics ---"
    python3 "$SCRIPTS_DIR/analyze_time_binned_lexical.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/lexical" \
        --bin-edges "$BIN_EDGES" \
        --max-minutes "$DURATION"

    # 6. Time-binned lexical metrics (5-grams)
    echo ""
    echo "--- [6/8] Time-binned lexical metrics (5-gram) ---"
    python3 "$SCRIPTS_DIR/analyze_time_binned_lexical_5gram.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/lexical_5gram" \
        --bin-edges "$BIN_EDGES" \
        --max-minutes "$DURATION"

    # 7. Top n-grams report (5-gram)
    echo ""
    echo "--- [7/8] Top n-grams report ---"
    python3 "$SCRIPTS_DIR/report_top_ngrams_5gram.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/top_ngrams"

    # 8. Phrase template topics
    echo ""
    echo "--- [8/8] Phrase template topics ---"
    python3 "$SCRIPTS_DIR/phrase_template_topics.py" \
        --data-dir "$data_dir" \
        --scales "$SCALES" \
        --out-dir "${out_base}/phrase_topics"

    echo ""
    echo "Done: $model"
done

echo ""
echo "================================================================"
echo "All analyses complete. Results in: $FINDINGS_DIR/"
echo "================================================================"
