#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$PWD}"
PKG="$ROOT/E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1"
OUT="$ROOT/E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build"
V4="$ROOT/USENIX27_FINAL_EXPERIMENT_FREEZE_E2E_ATTRIGUARD_v4_FINAL_CODING_FREEZE_RECONCILED.md"
if [[ ! -f "$V4" ]]; then cp "$PKG/USENIX27_FINAL_EXPERIMENT_FREEZE_E2E_ATTRIGUARD_v4_FINAL_CODING_FREEZE_RECONCILED.md" "$V4"; fi
if [[ -e "$OUT" ]]; then echo "FATAL: $OUT already exists; do not overwrite" >&2; exit 3; fi
mkdir -p "$OUT"
# Reuse the already written deterministic PAEF producer, but redirect its expected output path by staging and then moving.
PYTHONPATH="$PKG/code${PYTHONPATH:+:$PYTHONPATH}" python "$PKG/code/E2E_A4_00_build_and_test_paef.py" "$ROOT"
A4OLD="$ROOT/E2E_ATTR_AUTH_v1/prefreeze/phase4_author_run/PAEF_ORACLE_FREEZE"
if [[ ! -d "$A4OLD" ]]; then echo 'FATAL A4 producer output absent' >&2; exit 4; fi
mv "$A4OLD" "$OUT/PAEF_ORACLE_FREEZE"
rmdir "$ROOT/E2E_ATTR_AUTH_v1/prefreeze/phase4_author_run" 2>/dev/null || true
PYTHONPATH="$PKG/code${PYTHONPATH:+:$PYTHONPATH}" python "$PKG/code/E2E_PRE_01_build_contexts_schedule.py" "$ROOT"
python "$PKG/code/E2E_PRE_04_build_freeze.py" "$ROOT"
echo '=== ZERO-CALL INTEGRATED BUILD COMPLETE ==='
echo 'NO SCIENTIFIC MODEL CALLS WERE MADE.'
echo 'NEXT: run run_LIVE_DEV_PREFLIGHT_AND_SEAL.sh (permanently excluded dev task only).'
