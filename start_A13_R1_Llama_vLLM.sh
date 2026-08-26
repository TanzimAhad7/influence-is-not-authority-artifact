#!/usr/bin/env bash
set -euo pipefail

MODEL="meta-llama/Llama-3.3-70B-Instruct"
PORT="8110"
GPU_LIST="2,3"

mkdir -p logs

# Refuse to start a duplicate listener on the R1 port.
if command -v lsof >/dev/null 2>&1 && lsof -iTCP:${PORT} -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "FATAL: port ${PORT} is already in use. Inspect that process before starting another server."
  exit 1
fi

CUDA_VISIBLE_DEVICES="${GPU_LIST}" nohup vllm serve "${MODEL}" \
  --served-model-name "${MODEL}" \
  --tensor-parallel-size 2 \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  --max-logprobs 5 \
  --port "${PORT}" \
  > logs/vllm_a13_r1_llama.log 2>&1 &

PID=$!
echo "${PID}" > logs/vllm_a13_r1_llama.pid

echo "Started Llama R1 vLLM parent PID ${PID} on GPUs ${GPU_LIST}, port ${PORT}."
echo "PID file: logs/vllm_a13_r1_llama.pid"
echo "Log:      logs/vllm_a13_r1_llama.log"
echo "Wait for readiness with:"
echo "  until curl -s http://localhost:${PORT}/v1/models | grep -q 'Llama-3.3-70B-Instruct'; do sleep 20; printf '.'; done; echo READY"
