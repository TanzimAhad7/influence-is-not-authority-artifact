#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-$PWD}"
OUT_ROOT="${2:-$PROJECT_ROOT/BASE_FINISHING_ZERO_CALL_v1}"
PKG_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p "$OUT_ROOT/P3_C0" "$OUT_ROOT/A14_AR"

echo "[1/4] Freeze P3-C0 zero-call refresh"
python "$PKG_DIR/P3_C0_00_freeze.py" --project-root "$PROJECT_ROOT" --package-dir "$PKG_DIR" --out-dir "$OUT_ROOT/P3_C0"

echo "[2/4] Run P3-C0 corrected-29 refresh"
python "$PKG_DIR/P3_C0_01_refresh.py" --project-root "$PROJECT_ROOT" --out-dir "$OUT_ROOT/P3_C0"

echo "[3/4] Hash P3-C0 outputs"
python "$PKG_DIR/P3_C0_02_hash_outputs.py" --out-dir "$OUT_ROOT/P3_C0"

echo "[4/4] Audit A14 raw-response recovery"
python "$PKG_DIR/A14_AR_00_verify_recovery.py" --project-root "$PROJECT_ROOT" --out-dir "$OUT_ROOT/A14_AR"

echo "DONE: $OUT_ROOT"
