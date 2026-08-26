#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-$PWD}"
RUN_DIR="${2:-AW_N3_AUTHOR_v1}"
MONITOR_URL="${3:-http://localhost:8120/v1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[AWN3-PREFLIGHT] project_root=${PROJECT_ROOT}"
echo "[AWN3-PREFLIGHT] run_dir=${RUN_DIR}"
echo "[AWN3-PREFLIGHT] monitor=${MONITOR_URL}"
python3 "${SCRIPT_DIR}/AWN3_02_preflight.py" \
  --project-root "${PROJECT_ROOT}" \
  --run-dir "${RUN_DIR}" \
  --monitor-base-url "${MONITOR_URL}"
echo "[AWN3-PREFLIGHT] COMPLETE — synthetic only"
