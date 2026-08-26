#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-$PWD}"
RUN_DIR="${2:-AW_N3_AUTHOR_v1}"
MONITOR_URL="${3:-http://localhost:8120/v1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[AWN3-RUN] project_root=${PROJECT_ROOT}"
echo "[AWN3-RUN] run_dir=${RUN_DIR}"
echo "[AWN3-RUN] source-locked full AgentWatcher; 96 frozen unique static inputs"
python3 "${SCRIPT_DIR}/AWN3_03_run_science.py" \
  --project-root "${PROJECT_ROOT}" \
  --run-dir "${RUN_DIR}" \
  --monitor-base-url "${MONITOR_URL}"
python3 "${SCRIPT_DIR}/AWN3_04_analyze.py" --project-root "${PROJECT_ROOT}" --run-dir "${RUN_DIR}"
python3 "${SCRIPT_DIR}/AWN3_05_verify.py" --project-root "${PROJECT_ROOT}" --run-dir "${RUN_DIR}"
echo "[AWN3-RUN] COMPLETE"
echo "[AWN3-RUN] STOP: do not start CV2 until canonical reconciliation"
