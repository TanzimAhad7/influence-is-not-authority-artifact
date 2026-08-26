#!/usr/bin/env bash
set -euo pipefail
MODEL="meta-llama/Llama-3.3-70B-Instruct"
REV="6f6073b423013f6a7d4d9f39144961bfbfbc386b"
PORT="${N3_LLAMA_PORT:-8120}"
GPU_LIST="${N3_GPU_LIST:-2,3}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
if command -v lsof >/dev/null 2>&1 && lsof -iTCP:${PORT} -sTCP:LISTEN -n -P >/dev/null 2>&1; then echo "FATAL: port ${PORT} in use"; exit 1; fi
CUDA_VISIBLE_DEVICES="${GPU_LIST}" nohup vllm serve "${MODEL}" --revision "${REV}" --tokenizer-revision "${REV}" --served-model-name "${MODEL}" --tensor-parallel-size 2 --dtype bfloat16 --max-model-len 16384 --gpu-memory-utilization 0.90 --max-logprobs 5 --port "${PORT}" > "${LOG_DIR}/n3_vllm_llama.log" 2>&1 &
echo $! > "${LOG_DIR}/n3_vllm_llama.pid"
echo "Started N3 Llama on GPUs ${GPU_LIST}, port ${PORT}, revision ${REV}"
