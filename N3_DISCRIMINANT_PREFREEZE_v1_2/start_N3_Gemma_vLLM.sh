#!/usr/bin/env bash
set -euo pipefail
MODEL="google/gemma-3-12b-it"
REV="96b6f1eccf38110c56df3a15bffe176da04bfd80"
PORT="${N3_GEMMA_PORT:-8121}"
GPU_LIST="${N3_GPU_LIST:-2,3}"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${PROJECT_ROOT}/logs"
mkdir -p "${LOG_DIR}"
if command -v lsof >/dev/null 2>&1 && lsof -iTCP:${PORT} -sTCP:LISTEN -n -P >/dev/null 2>&1; then echo "FATAL: port ${PORT} in use"; exit 1; fi
CUDA_VISIBLE_DEVICES="${GPU_LIST}" nohup vllm serve "${MODEL}" --revision "${REV}" --tokenizer-revision "${REV}" --served-model-name "${MODEL}" --tensor-parallel-size 2 --dtype bfloat16 --max-model-len 16384 --gpu-memory-utilization 0.90 --max-logprobs 5 --port "${PORT}" > "${LOG_DIR}/n3_vllm_gemma.log" 2>&1 &
echo $! > "${LOG_DIR}/n3_vllm_gemma.pid"
echo "Started N3 Gemma on GPUs ${GPU_LIST}, port ${PORT}, revision ${REV}"
