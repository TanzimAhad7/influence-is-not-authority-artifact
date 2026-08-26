#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=01_a13_natural
say 'Reproduce original A13 benign natural cohort from model execution'
restore_path a13
clear_path a13
start_vllm a13_qwen 'Qwen/Qwen2.5-72B-Instruct' '-' 8100 "$GPU_LIST" 2 16384 0.90 --max-logprobs 5 --enable-auto-tool-choice --tool-call-parser hermes --seed 0
PID=$(cat "$SERVER_ROOT/a13_qwen.pid")
trap 'stop_pid "$PID"' EXIT
run_logged "$STAGE" python3 A13.py
capture_path "$STAGE" a13
restore_path a13
stop_pid "$PID"; trap - EXIT
say "$STAGE complete"
