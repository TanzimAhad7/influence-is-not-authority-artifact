#!/usr/bin/env bash
set -euo pipefail

MODEL_KEY=${1:?usage: serve_model.sh <llama|gemma|qwen_canonical> [run-dir]}
PKG_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
RUN_DIR=${2:-${P2B_RUN_DIR:-}}
if [[ -z "$RUN_DIR" ]]; then
  echo "FATAL: supply run-dir as argument 2 or P2B_RUN_DIR" >&2
  exit 2
fi
RUN_DIR=$(mkdir -p "$RUN_DIR" && cd "$RUN_DIR" && pwd)
LOCK="$PKG_ROOT/P2B_XM_CI_REVISION_LOCK.json"
REG="$PKG_ROOT/MODEL_REGISTRY_CI.json"
PORT=8100
CUDA_DEVICES=${P2B_CUDA_DEVICES:-2,3}

readarray -t CFG < <(python - "$REG" "$LOCK" "$MODEL_KEY" <<'PY'
import json,sys
reg=json.load(open(sys.argv[1])); lock=json.load(open(sys.argv[2])); key=sys.argv[3]
if key not in reg['models'] or key not in lock['models']:
    raise SystemExit(f'unknown model key: {key}')
r=reg['models'][key]; l=lock['models'][key]
for x in ('model_id','revision','tokenizer_revision'):
    if r[x]!=l[x]: raise SystemExit(f'registry/lock mismatch {key} {x}')
print(r['model_id']); print(l['revision']); print(l['tokenizer_revision'])
PY
)
MODEL=${CFG[0]}; REV=${CFG[1]}; TOKREV=${CFG[2]}

if [[ -f "$RUN_DIR/vllm_server.pid" ]]; then
  OLD=$(cat "$RUN_DIR/vllm_server.pid" || true)
  if [[ -n "$OLD" && -e "/proc/$OLD" ]]; then
    echo "FATAL: server PID $OLD already alive for $RUN_DIR" >&2
    exit 3
  fi
fi

nohup env CUDA_VISIBLE_DEVICES="$CUDA_DEVICES" \
  vllm serve "$MODEL" \
  --tensor-parallel-size 2 \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --max-logprobs 5 \
  --seed 0 \
  --tokenizer-mode hf \
  --generation-config vllm \
  --revision "$REV" \
  --tokenizer-revision "$TOKREV" \
  --served-model-name "$MODEL" \
  --port "$PORT" \
  > "$RUN_DIR/vllm_server.log" 2>&1 < /dev/null &

PID=$!
echo "$PID" > "$RUN_DIR/vllm_server.pid"
disown || true
printf 'model_key=%s\nmodel=%s\nrevision=%s\ntokenizer_revision=%s\nPID=%s\nrun_dir=%s\n' \
  "$MODEL_KEY" "$MODEL" "$REV" "$TOKREV" "$PID" "$RUN_DIR"
