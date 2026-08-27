#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=07_agentwatcher
AWREL=AW_N3_AUTHOR_v1
P2REL=P2_AGENTWATCHER_NODEFENSE_RUN_v1
EXTREL=external/AgentWatcher_armc_runtime_v1/results/agent_evaluations/agentdojo
restore_path "$AWREL"
restore_path "$P2REL"
restore_path "$EXTREL"
rm -rf "$WORK_ROOT/$AWREL/science" "$WORK_ROOT/$AWREL/analysis" "$WORK_ROOT/$P2REL"
rm -rf "$WORK_ROOT/$EXTREL/P2_AW_NODEFENSE_TOOL_KNOWLEDGE_200_v1"
PID=""
cleanup(){ stop_pid "$PID"; restore_path "$AWREL"; restore_path "$P2REL"; restore_path "$EXTREL"; }
trap cleanup EXIT

# Exact AgentWatcher monitor base + LoRA adapter, pinned by the frozen AW-N3 protocol.
BASE=$(hf_snapshot Qwen/Qwen3-4B-Instruct-2507 cdbee75f17c01a7cc42f958dc650907174af0554)
ADAPTER=$(hf_snapshot SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507 5d19a2f5c23e377a242eda9708e6f9cf430699be)
ATTR=$(hf_snapshot meta-llama/Llama-3.1-8B-Instruct 0e9e39f249a16976918f6564b8830bc894c89659)
MON="SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507"
LOG="$SERVER_ROOT/agentwatcher_monitor.log"; PIDF="$SERVER_ROOT/agentwatcher_monitor.pid"
nohup env CUDA_VISIBLE_DEVICES="$GPU1" HF_TOKEN="$HF_TOKEN" HUGGING_FACE_HUB_TOKEN="$HF_TOKEN" \
  vllm serve "$BASE" --served-model-name "Qwen/Qwen3-4B-Instruct-2507" --enable-lora \
  --lora-modules "${MON}=${ADAPTER}" --dtype bfloat16 --max-model-len 32768 \
  --gpu-memory-utilization 0.6 --generation-config vllm --api-key x --port 8120 >"$LOG" 2>&1 < /dev/null &
PID=$!; echo "$PID" > "$PIDF"
wait_model 8120 "Qwen/Qwen3-4B-Instruct-2507" 1800
# AW-N3 loads the attribution model locally; isolate it to the other GPU.
export CUDA_VISIBLE_DEVICES="$GPU0"
run_logged "${STAGE}_paired_gate" bash AW_N3_PREFREEZE_v1/run_AWN3_v1.sh "$WORK_ROOT" "$AWREL" http://127.0.0.1:8120/v1
capture_path "$STAGE" "$AWREL"

# Separate 200-input defense-OFF operational anchor from the frozen paper population.
export CUDA_VISIBLE_DEVICES="$GPU0"
PKG="$WORK_ROOT/P2_AGENTWATCHER_NODEFENSE_PREFREEZE_v1"
OUT="$WORK_ROOT/$P2REL"
run_logged "${STAGE}_off_preflight" python3 "$PKG/P2_00_preflight_freeze.py" --project-root "$WORK_ROOT" --package-dir "$PKG" --out-dir "$OUT"
run_logged "${STAGE}_off_science" python3 "$PKG/P2_01_run_nodefense.py" --project-root "$WORK_ROOT" --package-dir "$PKG" --out-dir "$OUT"
run_logged "${STAGE}_off_analysis" python3 "$PKG/P2_02_analyze.py" --project-root "$WORK_ROOT" --package-dir "$PKG" --out-dir "$OUT"
run_logged "${STAGE}_off_verify" python3 "$PKG/P2_03_verify.py" --project-root "$WORK_ROOT" --package-dir "$PKG" --out-dir "$OUT"
capture_path "$STAGE" "$P2REL"

# Source-fidelity defense-ON 200 run used for the 0%/28% operational anchor.
# This is a distinct population/run from AW-N3 and is kept separate in analysis.
RUNTIME="$WORK_ROOT/external/AgentWatcher_armc_runtime_v1"
ONREL="$EXTREL/A15B0_ARMC_SCI_TOOL_KNOWLEDGE_200"
rm -rf "$WORK_ROOT/$ONREL"
export OPENAI_API_KEY="$OPENROUTER_API_KEY"
export OPENAI_BASE_URL="https://openrouter.ai/api/v1"
export AGENTWATCHER_MONITOR_BASE_URL="http://127.0.0.1:8120/v1"
export AGENTWATCHER_MONITOR_API_KEY=x
export PIARENA_ATTRIBUTION_MODEL="$ATTR"
run_logged "${STAGE}_on_200" env CUDA_VISIBLE_DEVICES="$GPU0" python3 "$RUNTIME/main_agentdojo.py" \
  --model gpt-4o-mini --attack tool_knowledge --defense agentwatcher \
  --monitor_llm "$ADAPTER" --sample_size 200 --name A15B0_ARMC_SCI_TOOL_KNOWLEDGE_200 \
  --w_s 10 --w_l 150 --w_r 50 --K 3 --attribution_model "$ATTR"
run_logged "${STAGE}_on_summary" python3 "$ARTIFACT_ROOT/scripts/reproduction/analyze_agentwatcher_on.py" --result-dir "$WORK_ROOT/$ONREL" --out "$RESULTS_ROOT/$STAGE/AGENTWATCHER_ON_SUMMARY.json"
capture_path "$STAGE" "$ONREL"
say "$STAGE complete"
