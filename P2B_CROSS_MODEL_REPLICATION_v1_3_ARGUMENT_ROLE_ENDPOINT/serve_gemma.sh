#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT=/home/anon_/ratchet/phase0_pilot
LOCK="$PROJECT_ROOT/P2B_XMODEL_REVISION_LOCK_v1_3.json"
RUN="$PROJECT_ROOT/P2B_XMODEL_GEMMA_RUN_v1_3"
mkdir -p "$RUN"

if [[ ! -f "$LOCK" ]]; then
  echo "FATAL missing revision lock: $LOCK" >&2
  exit 2
fi

REV=$(python - "$LOCK" "gemma" <<'PY'
import json,sys
p,key=sys.argv[1],sys.argv[2]
d=json.load(open(p))
print(d["models"][key]["revision"])
PY
)
TOKREV=$(python - "$LOCK" "gemma" <<'PY'
import json,sys
p,key=sys.argv[1],sys.argv[2]
d=json.load(open(p))
print(d["models"][key]["tokenizer_revision"])
PY
)

nohup env CUDA_VISIBLE_DEVICES=2,3 \
vllm serve google/gemma-3-12b-it \
  --tensor-parallel-size 2 \
  --dtype bfloat16 \
  --max-model-len 16384 \
  --max-logprobs 5 \
  --seed 0 \
  --tokenizer-mode hf \
  --generation-config vllm \
  --revision "$REV" \
  --tokenizer-revision "$TOKREV" \
  --served-model-name google/gemma-3-12b-it \
  --port 8100 \
  > "$RUN/vllm_server.log" 2>&1 < /dev/null &

echo $! > "$RUN/vllm_server.pid"
disown || true
echo "gemma server PID $(cat "$RUN/vllm_server.pid")"
echo "revision=$REV"
echo "tokenizer_revision=$TOKREV"
