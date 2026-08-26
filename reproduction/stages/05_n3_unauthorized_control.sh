#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=05_n3_unauthorized_control
RUNREL=N3_PREFREEZE_AUTHOR_v1_1
PKG=N3_DISCRIMINANT_PREFREEZE_v1_2
restore_path "$RUNREL"
rm -rf "$WORK_ROOT/$RUNREL/science_llama" "$WORK_ROOT/$RUNREL/science_gemma" "$WORK_ROOT/$RUNREL/analysis"
mkdir -p "$WORK_ROOT/logs"
PID=""
cleanup(){ stop_pid "$PID"; restore_path "$RUNREL"; }
trap cleanup EXIT
# Use the original launchers because N3 verifies the exact live vLLM process, revision, port, and PID file.
run_logged "${STAGE}_start_llama" env N3_GPU_LIST="$GPU_LIST" N3_LLAMA_PORT=8120 bash "$WORK_ROOT/$PKG/start_N3_Llama_vLLM.sh"
PID=$(cat "$WORK_ROOT/logs/n3_vllm_llama.pid")
wait_model 8120 "meta-llama/Llama-3.3-70B-Instruct" 1800
run_logged "${STAGE}_llama" python3 "$PKG/N3_03_score_science.py" --project-root "$WORK_ROOT" --run-dir "$RUNREL" --package-dir "$PKG" --scorer llama --base-url http://127.0.0.1:8120/v1 --api-key x
stop_pid "$PID"; PID=""
run_logged "${STAGE}_start_gemma" env N3_GPU_LIST="$GPU_LIST" N3_GEMMA_PORT=8121 bash "$WORK_ROOT/$PKG/start_N3_Gemma_vLLM.sh"
PID=$(cat "$WORK_ROOT/logs/n3_vllm_gemma.pid")
wait_model 8121 "google/gemma-3-12b-it" 1800
run_logged "${STAGE}_gemma" python3 "$PKG/N3_03_score_science.py" --project-root "$WORK_ROOT" --run-dir "$RUNREL" --package-dir "$PKG" --scorer gemma --base-url http://127.0.0.1:8121/v1 --api-key x
stop_pid "$PID"; PID=""
run_logged "${STAGE}_analysis" python3 "$PKG/N3_04_analyze.py" --project-root "$WORK_ROOT" --run-dir "$RUNREL" --package-dir "$PKG"
capture_path "$STAGE" "$RUNREL"
say "$STAGE complete"
