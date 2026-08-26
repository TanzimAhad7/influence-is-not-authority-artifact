#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=04_a14_controlled_source
REL=a14_minimal_factorial
restore_path "$REL"
rm -rf "$WORK_ROOT/$REL/scorer_llama" "$WORK_ROOT/$REL/scorer_gemma" "$WORK_ROOT/$REL/analysis"
PID=""
cleanup(){ stop_pid "$PID"; restore_path "$REL"; }
trap cleanup EXIT
PID=$(start_vllm a14_llama "meta-llama/Llama-3.3-70B-Instruct" "6f6073b423013f6a7d4d9f39144961bfbfbc386b" 8110 "$GPU_LIST" 2 16384 0.90 --max-logprobs 5 --seed 0 --tokenizer-mode hf --generation-config vllm)
run_logged "${STAGE}_llama" python3 A14M_03_score.py --project-root "$WORK_ROOT" --scorer-label llama --base-url http://127.0.0.1:8110/v1 --api-key x
stop_pid "$PID"; PID=""
PID=$(start_vllm a14_gemma "google/gemma-3-12b-it" "96b6f1eccf38110c56df3a15bffe176da04bfd80" 8111 "$GPU_LIST" 2 16384 0.90 --max-logprobs 5 --seed 0 --tokenizer-mode hf --generation-config vllm)
run_logged "${STAGE}_gemma" python3 A14M_03_score.py --project-root "$WORK_ROOT" --scorer-label gemma --base-url http://127.0.0.1:8111/v1 --api-key x
stop_pid "$PID"; PID=""
run_logged "${STAGE}_analysis" python3 A14M_04_analyze.py --project-root "$WORK_ROOT"
capture_path "$STAGE" "$REL"
say "$STAGE complete"
