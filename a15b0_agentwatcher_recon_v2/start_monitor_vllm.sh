#!/usr/bin/env bash
set -euo pipefail

BASE="${HOME}/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/cdbee75f17c01a7cc42f958dc650907174af0554"
ADAPTER="${HOME}/.cache/huggingface/hub/models--SecureLLMSys--AgentWatcher-Qwen3-4B-Instruct-2507/snapshots/5d19a2f5c23e377a242eda9708e6f9cf430699be"
NAME="SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507"
PORT="${AGENTWATCHER_MONITOR_PORT:-8120}"

test -d "${BASE}" || { echo "Missing base snapshot: ${BASE}"; exit 2; }
test -d "${ADAPTER}" || { echo "Missing adapter snapshot: ${ADAPTER}"; exit 2; }

echo "Starting frozen AgentWatcher monitor endpoint"
echo "base=${BASE}"
echo "adapter=${ADAPTER}"
echo "lora_name=${NAME}"
echo "port=${PORT}"

exec env CUDA_VISIBLE_DEVICES=3 \
  vllm serve "${BASE}" \
    --served-model-name "Qwen/Qwen3-4B-Instruct-2507" \
    --enable-lora \
    --lora-modules "${NAME}=${ADAPTER}" \
    --dtype bfloat16 \
    --max-model-len 32768 \
    --gpu-memory-utilization 0.6 \
    --generation-config vllm \
    --api-key x \
    --port "${PORT}"
