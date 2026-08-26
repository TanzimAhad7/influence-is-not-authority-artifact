#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${USENIX_E2E_VENV:-$ROOT/.venv-e2e}"
INSTALL_VLLM=0
if [[ "${1:-}" == "--install-vllm" ]]; then INSTALL_VLLM=1; elif [[ -n "${1:-}" ]]; then echo "usage: $0 [--install-vllm]" >&2; exit 2; fi
command -v python3 >/dev/null || { echo 'FATAL: python3 is required' >&2; exit 2; }
python3 - <<'PY'
import sys
print('python',sys.version.split()[0])
if sys.version_info < (3,10): raise SystemExit('FATAL: Python >= 3.10 is required for the full E2E environment')
PY
if [[ ! -d "$VENV" ]]; then
  echo "[setup] creating $VENV with system GPU packages visible"
  python3 -m venv --system-site-packages "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "$ROOT/requirements-e2e-core.txt"
if [[ $INSTALL_VLLM -eq 1 ]]; then
  echo '[setup] installing the frozen replay vLLM version (this may install/replace the CUDA PyTorch stack)'
  python -m pip install 'vllm==0.26.0'
fi
cat <<EOF2

Environment created at:
  $VENV

Next:
  source "$VENV/bin/activate"
  export OPENROUTER_API_KEY='...'
  export HF_TOKEN='...'
  export USENIX_GPU_LIST='0,1'
  bash "$ROOT/CHECK_E2E.sh"
  bash "$ROOT/RUN_END_TO_END.sh" --all
EOF2
