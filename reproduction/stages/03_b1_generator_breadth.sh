#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=03_b1_generator_breadth
REL=b1_a12_backbone_replication_c0_v2
restore_path "$REL"
# Preserve frozen protocol/taxonomy but remove old model outcomes before rerun.
rm -rf "$WORK_ROOT/$REL/gpt4o" "$WORK_ROOT/$REL/claude45"
rm -f "$WORK_ROOT/$REL/combined_results.json" "$WORK_ROOT/$REL/COMBINED_REPORT.md"
PID=""
cleanup(){ stop_pid "$PID"; restore_path "$REL"; }
trap cleanup EXIT
PID=$(start_vllm b1_llama "meta-llama/Llama-3.3-70B-Instruct" "6f6073b423013f6a7d4d9f39144961bfbfbc386b" 8110 "$GPU_LIST" 2 16384 0.90 --max-logprobs 5 --seed 0 --tokenizer-mode hf --generation-config vllm)
export B1_SCORER_BASE_URL=http://127.0.0.1:8110/v1
run_logged "${STAGE}_gpt4o_preflight" python3 B1_C0_POPULATION_AMENDMENT_v2/B1_C0_01_run.py --agent gpt4o --preflight-only
run_logged "${STAGE}_gpt4o_science" python3 B1_C0_POPULATION_AMENDMENT_v2/B1_C0_01_run.py --agent gpt4o
run_logged "${STAGE}_claude_preflight" python3 B1_C0_POPULATION_AMENDMENT_v2/B1_C0_01_run.py --agent claude45 --preflight-only
run_logged "${STAGE}_claude_science" python3 B1_C0_POPULATION_AMENDMENT_v2/B1_C0_01_run.py --agent claude45
run_logged "${STAGE}_joint_analysis" python3 B1_C0_POPULATION_AMENDMENT_v2/B1_C0_02_analyze.py
capture_path "$STAGE" "$REL"
say "$STAGE complete; reproduced output captured under $RESULTS_ROOT/$STAGE"
