#!/usr/bin/env bash
set -euo pipefail
: "${ARTIFACT_ROOT:?ARTIFACT_ROOT must be set}"
: "${WORK_ROOT:?WORK_ROOT must be set}"
: "${RUN_ROOT:?RUN_ROOT must be set}"
REF_ROOT="$ARTIFACT_ROOT"
RESULTS_ROOT="$RUN_ROOT/results"
SERVER_ROOT="$RUN_ROOT/servers"
mkdir -p "$RESULTS_ROOT" "$SERVER_ROOT"
GPU_LIST="${USENIX_GPU_LIST:-0,1}"
GPU0="${USENIX_GPU0:-${GPU_LIST%%,*}}"
GPU1="${USENIX_GPU1:-${GPU_LIST##*,}}"

say(){ printf '\n[%s] %s\n' "$(date -u +%H:%M:%S)" "$*" >&2; }
fail(){ echo "FATAL: $*" >&2; exit 2; }
need(){ command -v "$1" >/dev/null 2>&1 || fail "missing command: $1"; }

run_logged(){
  local label="$1"; shift
  mkdir -p "$RESULTS_ROOT/logs"
  say "$label"
  ( cd "$WORK_ROOT" && "$@" ) 2>&1 | tee "$RESULTS_ROOT/logs/${label}.log"
}

clear_path(){ rm -rf "$WORK_ROOT/$1"; }
restore_path(){
  local rel="$1"
  rm -rf "$WORK_ROOT/$rel"
  if [[ -e "$REF_ROOT/$rel" ]]; then
    mkdir -p "$(dirname "$WORK_ROOT/$rel")"
    cp -a "$REF_ROOT/$rel" "$WORK_ROOT/$rel"
  fi
}
capture_path(){
  local stage="$1" rel="$2"
  [[ -e "$WORK_ROOT/$rel" ]] || return 0
  local dst="$RESULTS_ROOT/$stage/$rel"
  mkdir -p "$(dirname "$dst")"
  rm -rf "$dst"
  cp -a "$WORK_ROOT/$rel" "$dst"
}

wait_model(){
  local port="$1" expected="$2" timeout_s="${3:-1800}"
  local start now
  start=$(date +%s)
  while true; do
    if curl -fsS "http://127.0.0.1:${port}/v1/models" > "$SERVER_ROOT/models_${port}.json" 2>/dev/null; then
      python3 - "$SERVER_ROOT/models_${port}.json" "$expected" <<'PY' && return 0
import json,sys
x=json.load(open(sys.argv[1])); exp=sys.argv[2]
ids=[r.get('id') for r in x.get('data',[]) if isinstance(r,dict)]
print('served=',ids, file=sys.stderr)
raise SystemExit(0 if exp in ids else 1)
PY
    fi
    now=$(date +%s)
    (( now-start < timeout_s )) || fail "vLLM port ${port} did not serve ${expected} within ${timeout_s}s"
    sleep 10
  done
}

start_vllm(){
  local label="$1" model="$2" revision="$3" port="$4" gpus="$5" tp="$6" maxlen="$7" mem="$8"; shift 8
  need vllm; need curl
  local log="$SERVER_ROOT/${label}.log" pidf="$SERVER_ROOT/${label}.pid"
  if curl -fsS "http://127.0.0.1:${port}/v1/models" >/dev/null 2>&1; then fail "port ${port} already has an OpenAI-compatible server; stop it first"; fi
  local cmd=(vllm serve "$model" --served-model-name "$model" --tensor-parallel-size "$tp" --dtype bfloat16 --max-model-len "$maxlen" --gpu-memory-utilization "$mem" --port "$port")
  if [[ -n "$revision" && "$revision" != "-" ]]; then cmd+=(--revision "$revision" --tokenizer-revision "$revision"); fi
  cmd+=("$@")
  say "start vLLM ${label}: model=${model} revision=${revision} GPUs=${gpus} port=${port}"
  (cd "$WORK_ROOT" && nohup env CUDA_VISIBLE_DEVICES="$gpus" HF_TOKEN="${HF_TOKEN:-}" HUGGING_FACE_HUB_TOKEN="${HF_TOKEN:-}" "${cmd[@]}" >"$log" 2>&1 < /dev/null & echo $! > "$pidf")
  local pid; pid=$(cat "$pidf")
  for _ in $(seq 1 12); do kill -0 "$pid" 2>/dev/null && break; sleep 1; done
  kill -0 "$pid" 2>/dev/null || { tail -100 "$log" || true; fail "vLLM ${label} exited during startup"; }
  wait_model "$port" "$model" 1800
  echo "$pid"
}

stop_pid(){
  local pid="${1:-}"
  [[ -n "$pid" ]] || return 0
  if kill -0 "$pid" 2>/dev/null; then
    kill "$pid" 2>/dev/null || true
    for _ in $(seq 1 30); do kill -0 "$pid" 2>/dev/null || return 0; sleep 1; done
    kill -9 "$pid" 2>/dev/null || true
  fi
}

require_keys(){
  [[ -n "${OPENROUTER_API_KEY:-}" ]] || fail 'OPENROUTER_API_KEY is required'
  [[ -n "${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}" ]] || fail 'HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) is required'
  export HF_TOKEN="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN}}"
  export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
}

hf_snapshot(){
  local repo="$1" rev="$2"
  python3 - "$repo" "$rev" <<'PY'
import os,sys
from huggingface_hub import snapshot_download
print(snapshot_download(repo_id=sys.argv[1], revision=sys.argv[2], token=os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')))
PY
}
