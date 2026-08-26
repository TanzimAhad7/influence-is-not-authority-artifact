#!/usr/bin/env bash
set -euo pipefail

MODEL="google/gemma-3-12b-it"
PORT="8111"
GPU_LIST="2,3"

mkdir -p logs

if command -v lsof >/dev/null 2>&1 && lsof -iTCP:${PORT} -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "FATAL: port ${PORT} already in use. Inspect/stop the recorded PID; do not pkill globally."
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
  > logs/vllm_a14m_gemma_8111.log 2>&1 &

PID=$!
echo "${PID}" > logs/vllm_a14m_gemma_8111.pid

echo "Started A14M Gemma scorer parent PID ${PID} on GPUs ${GPU_LIST}, port ${PORT}."
echo "Log: logs/vllm_a14m_gemma_8111.log"
echo "PID file: logs/vllm_a14m_gemma_8111.pid"
echo "Wait: until curl -s http://localhost:${PORT}/v1/models | grep -q 'google/gemma-3-12b-it'; do sleep 20; printf '.'; done; echo READY"
