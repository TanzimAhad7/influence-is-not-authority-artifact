#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 PROJECT_ROOT [RUN_DIR]" >&2
  exit 2
fi
PROJECT_ROOT="$(cd "$1" && pwd)"
RUN_DIR="${2:-R2B_JTF_AUTHOR_v1}"
PKG_DIR="R2B_JTF_PREFREEZE_v1"

if [[ ! -f "$PROJECT_ROOT/$RUN_DIR/R2B_JTF_FREEZE.json" ]]; then
  echo "FATAL: missing frozen analysis file: $PROJECT_ROOT/$RUN_DIR/R2B_JTF_FREEZE.json" >&2
  echo "Run freeze_R2B_JTF_v1.sh first." >&2
  exit 3
fi

echo "[R2B-ANALYZE] project_root=$PROJECT_ROOT"
echo "[R2B-ANALYZE] run_dir=$RUN_DIR"
echo "[R2B-ANALYZE] zero model/provider calls"
python3 "$PROJECT_ROOT/$PKG_DIR/R2B_01_analyze.py" \
  --project-root "$PROJECT_ROOT" --run-dir "$RUN_DIR" --package-dir "$PKG_DIR"
python3 "$PROJECT_ROOT/$PKG_DIR/R2B_02_verify.py" \
  --project-root "$PROJECT_ROOT" --run-dir "$RUN_DIR"
echo "[R2B-ANALYZE] COMPLETE"
echo "[R2B-ANALYZE] STOP: do not start AW-N3 until canonical reconciliation"
