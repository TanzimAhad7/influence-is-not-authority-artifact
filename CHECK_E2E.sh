#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-}"
[[ -z "$MODE" || "$MODE" == "--structural" ]] || { echo "usage: $0 [--structural]" >&2; exit 2; }
STRUCT=0; [[ "$MODE" == "--structural" ]] && STRUCT=1
fail(){ echo "E2E_PREFLIGHT=FAIL: $*" >&2; exit 2; }
command -v bash >/dev/null || fail 'bash missing'
command -v python3 >/dev/null || fail 'python3 missing'
command -v curl >/dev/null || fail 'curl missing'
python3 - <<'PY'
import sys
print('python=',sys.version.split()[0])
if sys.version_info < (3,10): raise SystemExit('Python >=3.10 required')
PY
# All scientific entrypoints that the master runner invokes must be present.
while IFS= read -r rel; do [[ -e "$ROOT/$rel" ]] || fail "missing entrypoint/input: $rel"; done <<'LIST'
A13.py
A13_C0_EXTENSION_RUNNER_v1.py
A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz
A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz
B1_C0_POPULATION_AMENDMENT_v2/B1_C0_01_run.py
A14M_03_score.py
N3_DISCRIMINANT_PREFREEZE_v1_2/N3_03_score_science.py
R2B_JTF_PREFREEZE_v1/analyze_R2B_JTF_v1.sh
AW_N3_PREFREEZE_v1/run_AWN3_v1.sh
P2_AGENTWATCHER_NODEFENSE_PREFREEZE_v1/P2_01_run_nodefense.py
N6_ATTRIGUARD_N3_TECH_AMENDMENT_v1_2/N6_05_run_science.py
P0B3_CAUSALARMOR_LIVE_v1/P0B3_10_live_preflight.py
E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1/code/E2E_PRE_03_science_runner.py
P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED/serve_model.sh
figures/figure1.pdf
figures/Figure2.py
figures/Figure3.py
figures/Figure4.py
figures/Figure5.py
figures/Figure6.py
LIST
if [[ $STRUCT -eq 1 ]]; then
  echo 'E2E_PREFLIGHT=STRUCTURAL_PASS'
  exit 0
fi
python3 - <<'PY'
mods=['agentdojo','openai','huggingface_hub','transformers','numpy','yaml','requests','jsonschema']
for m in mods:
    try:
        x=__import__(m); print(m,'=',getattr(x,'__version__','ok'))
    except Exception as e: raise SystemExit(f'missing/import-failed {m}: {e}')
import importlib.metadata as md
if md.version('agentdojo')!='0.1.35': raise SystemExit('AgentDojo must be 0.1.35')
PY
[[ -n "${OPENROUTER_API_KEY:-}" ]] || fail 'OPENROUTER_API_KEY is not set'
[[ -n "${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}" ]] || fail 'HF_TOKEN (or HUGGING_FACE_HUB_TOKEN) is not set'
command -v vllm >/dev/null || fail 'vllm executable is missing (recommended frozen version: 0.26.0)'
command -v nvidia-smi >/dev/null || fail 'nvidia-smi missing; full local-model rerun requires NVIDIA GPUs'
python3 - <<'PY'
import importlib.metadata as md
v=md.version('vllm'); print('vllm=',v)
if v!='0.26.0':
    raise SystemExit('vLLM must be 0.26.0 for the corrected replay branch; use SETUP_E2E.sh --install-vllm or an equivalent exact environment')
PY
GPU_LIST="${USENIX_GPU_LIST:-0,1}"
IFS=',' read -r -a G <<< "$GPU_LIST"
(( ${#G[@]} >= 2 )) || fail 'USENIX_GPU_LIST must name at least two GPUs (example: 0,1)'
N=$(nvidia-smi --query-gpu=index --format=csv,noheader | wc -l | tr -d ' ')
for g in "${G[@]}"; do [[ "$g" =~ ^[0-9]+$ ]] || fail "invalid GPU index: $g"; (( g < N )) || fail "GPU index $g not present (found $N GPUs)"; done
# Network/key probes. They do not reveal credentials.
python3 - <<'PY'
import os, requests
k=os.environ['OPENROUTER_API_KEY']
r=requests.get('https://openrouter.ai/api/v1/models',headers={'Authorization':f'Bearer {k}'},timeout=30)
print('openrouter_status=',r.status_code)
if r.status_code>=400: raise SystemExit('OpenRouter credential/network preflight failed')
from huggingface_hub import HfApi
api=HfApi(token=os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN'))
for repo,rev in [
 ('meta-llama/Llama-3.3-70B-Instruct','6f6073b423013f6a7d4d9f39144961bfbfbc386b'),
 ('google/gemma-3-12b-it','96b6f1eccf38110c56df3a15bffe176da04bfd80'),
 ('Qwen/Qwen2.5-72B-Instruct','495f39366efef23836d0cfae4fbe635880d2be31'),
 ('Qwen/Qwen3-4B-Instruct-2507','cdbee75f17c01a7cc42f958dc650907174af0554'),
 ('SecureLLMSys/AgentWatcher-Qwen3-4B-Instruct-2507','5d19a2f5c23e377a242eda9708e6f9cf430699be')]:
    info=api.model_info(repo,revision=rev)
    print('hf_access=',repo,info.sha)
PY
echo 'E2E_PREFLIGHT=PASS'
