#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 PROJECT_ROOT [RUN_DIR]" >&2
  exit 2
fi
PROJECT_ROOT="$(cd "$1" && pwd)"
RUN_DIR="${2:-R2B_JTF_AUTHOR_v1}"
PKG_DIR="R2B_JTF_PREFREEZE_v1"

if [[ -e "$PROJECT_ROOT/$RUN_DIR" ]]; then
  echo "FATAL: run directory already exists: $PROJECT_ROOT/$RUN_DIR" >&2
  echo "Refusing overwrite/resume." >&2
  exit 3
fi
mkdir -p "$PROJECT_ROOT/$RUN_DIR"

echo "[R2B-FREEZE] project_root=$PROJECT_ROOT"
echo "[R2B-FREEZE] run_dir=$RUN_DIR"
echo "[R2B-FREEZE] no model/provider calls; no threshold outcomes"
python3 "$PROJECT_ROOT/$PKG_DIR/R2B_00_freeze.py" \
  --project-root "$PROJECT_ROOT" --run-dir "$RUN_DIR" --package-dir "$PKG_DIR"
echo "[R2B-FREEZE] COMPLETE — STOP HERE BEFORE ANALYSIS"
