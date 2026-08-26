#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-$PWD}"
RUN_DIR="${2:-AW_N3_AUTHOR_v1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[AWN3-BUILD] project_root=${PROJECT_ROOT}"
echo "[AWN3-BUILD] run_dir=${RUN_DIR}"
echo "[AWN3-BUILD] zero model/provider calls"
python3 "${SCRIPT_DIR}/AWN3_00_build_inputs.py" --project-root "${PROJECT_ROOT}" --run-dir "${RUN_DIR}"
echo "[AWN3-BUILD] COMPLETE — STOP BEFORE FREEZE"
