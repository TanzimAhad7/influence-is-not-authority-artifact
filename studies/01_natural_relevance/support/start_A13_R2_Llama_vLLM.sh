#!/usr/bin/env bash
set -euo pipefail

MODEL="meta-llama/Llama-3.3-70B-Instruct"
PORT="8110"
GPU_LIST="2,3"

mkdir -p logs

if command -v lsof >/dev/null 2>&1 && lsof -iTCP:${PORT} -sTCP:LISTEN -n -P >/dev/null 2>&1; then
  echo "FATAL: port ${PORT} is already in use."
  echo "Inspect/stop the existing R1/R1B server by its recorded PID before launching R2."
  exit 1
fi

CUDA_VISIBLE_DEVICES="${GPU_LIST}" nohup vllm serve "${MODEL}" \
  --served-model-name "${MODEL}" \
  --tensor-parallel-size 2 \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --gpu-memory-utilization 0.90 \
  --max-logprobs 5 \
  --enable-auto-tool-choice \
  --tool-call-parser llama3_json \
  --port "${PORT}" \
  > logs/vllm_a13_r2_llama.log 2>&1 &

PID=$!
echo "${PID}" > logs/vllm_a13_r2_llama.pid

echo "Started Llama R2 vLLM parent PID ${PID}"
echo "GPUs: ${GPU_LIST}"
echo "Port: ${PORT}"
echo "Tool parser: llama3_json"
echo "Log: logs/vllm_a13_r2_llama.log"
echo
echo "Wait for readiness:"
echo "until curl -s http://localhost:${PORT}/v1/models | grep -q 'Llama-3.3-70B-Instruct'; do sleep 20; printf '.'; done; echo READY"
