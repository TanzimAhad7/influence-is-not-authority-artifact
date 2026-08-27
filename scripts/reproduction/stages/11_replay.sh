#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=11_replay
PKG=P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED
RUNS=(P2B_XM_CI_LLAMA_RUN_v1_2 P2B_XM_CI_GEMMA_RUN_v1_2 P2B_XM_CI_QWEN_RUN_v1_2 P2B_XM_CI_JOINT_v1_2)
for r in "${RUNS[@]}"; do restore_path "$r"; rm -rf "$WORK_ROOT/$r"; done
CURRENT_PID=""
cleanup(){ stop_pid "$CURRENT_PID"; for r in "${RUNS[@]}"; do restore_path "$r"; done; }
trap cleanup EXIT

run_one(){
  local key="$1" rel="$2"
  mkdir -p "$WORK_ROOT/$rel"
  run_logged "${STAGE}_${key}_start" env P2B_CUDA_DEVICES="$GPU_LIST" bash "$WORK_ROOT/$PKG/serve_model.sh" "$key" "$WORK_ROOT/$rel"
  CURRENT_PID=$(cat "$WORK_ROOT/$rel/vllm_server.pid")
  local model
  model=$(python3 - "$WORK_ROOT/$PKG/MODEL_REGISTRY_CI.json" "$key" <<'PY'
import json,sys
print(json.load(open(sys.argv[1]))['models'][sys.argv[2]]['model_id'])
PY
)
  wait_model 8100 "$model" 1800
  run_logged "${STAGE}_${key}_render" python3 "$PKG/P2b_CI_03_render_preflight.py" --model-key "$key" --project-root "$WORK_ROOT" --base-url http://127.0.0.1:8100/v1 --api-key EMPTY --out-dir "$WORK_ROOT/$rel"
  run_logged "${STAGE}_${key}_freeze" python3 "$PKG/P2b_CI_04_freeze_arm.py" --model-key "$key" --project-root "$WORK_ROOT" --base-url http://127.0.0.1:8100/v1 --api-key EMPTY --run-dir "$WORK_ROOT/$rel"
  run_logged "${STAGE}_${key}_science" python3 "$PKG/P2b_CI_05_run_baseline.py" --project-root "$WORK_ROOT" --run-dir "$WORK_ROOT/$rel" --api-key EMPTY
  run_logged "${STAGE}_${key}_analysis" python3 "$PKG/P2b_CI_06_analyze_arm.py" --run-dir "$WORK_ROOT/$rel"
  run_logged "${STAGE}_${key}_argument_role" python3 "$PKG/P2b_CI_07_argument_role.py" --run-dir "$WORK_ROOT/$rel"
  stop_pid "$CURRENT_PID"; CURRENT_PID=""
  sleep 3
  capture_path "$STAGE" "$rel"
}
run_one llama P2B_XM_CI_LLAMA_RUN_v1_2
run_one gemma P2B_XM_CI_GEMMA_RUN_v1_2
run_one qwen_canonical P2B_XM_CI_QWEN_RUN_v1_2
mkdir -p "$WORK_ROOT/P2B_XM_CI_JOINT_v1_2"
run_logged "${STAGE}_joint" python3 "$PKG/P2b_CI_08_joint_compare.py" \
  --llama-run "$WORK_ROOT/P2B_XM_CI_LLAMA_RUN_v1_2" \
  --gemma-run "$WORK_ROOT/P2B_XM_CI_GEMMA_RUN_v1_2" \
  --qwen-run "$WORK_ROOT/P2B_XM_CI_QWEN_RUN_v1_2" \
  --out-dir "$WORK_ROOT/P2B_XM_CI_JOINT_v1_2"
capture_path "$STAGE" P2B_XM_CI_JOINT_v1_2
say "$STAGE complete"
