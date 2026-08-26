#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${1:-/home/anon_/ratchet/phase0_pilot}"
PKG="$ROOT/P6_CLEAN_ZERO_CALL_v1"
OUT="$ROOT/P6_CLEAN_RUN_v1"
cd "$ROOT"
source "$ROOT/.venv/bin/activate"

echo "P6 CLEAN ZERO-CALL v1"
echo "root=$ROOT"
echo "NO GPU / NO vLLM / NO API / NO MODEL CALLS"

if [[ ! -d "$PKG" ]]; then echo "FATAL: missing $PKG"; exit 1; fi
if [[ -e "$OUT" ]]; then echo "FATAL: $OUT already exists. Preserve/remove it deliberately before a rerun."; exit 1; fi

(cd "$PKG" && sha256sum -c PACKAGE_SHA256.txt)
python -u "$PKG/P6_00_preflight_and_freeze.py" --project-root "$ROOT" --package-dir "$PKG" --out-dir "$OUT" 2>&1 | tee "$ROOT/P6_CLEAN_PREFLIGHT.log"
python -u "$PKG/P6_01_synthesize.py" --project-root "$ROOT" --package-dir "$PKG" --out-dir "$OUT" 2>&1 | tee "$ROOT/P6_CLEAN_SYNTHESIS.log"
python -u "$PKG/P6_02_verify_and_hash.py" --out-dir "$OUT" 2>&1 | tee "$ROOT/P6_CLEAN_VERIFY.log"
(cd "$OUT" && sha256sum -c FINAL_ARTIFACT_SHA256.txt)

echo
echo "===== P6 SUMMARY ====="
cat "$OUT/P6_SUMMARY.md"

echo
echo "===== PACKAGE AUTHOR-RUN ARTIFACT ====="
cd "$ROOT"
rm -f P6_CLEAN_COMPLETE_v1.tar.gz P6_CLEAN_COMPLETE_v1.tar.gz.sha256
tar -czf P6_CLEAN_COMPLETE_v1.tar.gz \
  P6_CLEAN_ZERO_CALL_v1 \
  P6_CLEAN_RUN_v1 \
  P6_CLEAN_PREFLIGHT.log \
  P6_CLEAN_SYNTHESIS.log \
  P6_CLEAN_VERIFY.log
sha256sum P6_CLEAN_COMPLETE_v1.tar.gz | tee P6_CLEAN_COMPLETE_v1.tar.gz.sha256

echo
echo "P6 CLEAN AUTHOR EXECUTION COMPLETE"
echo "Upload: P6_CLEAN_COMPLETE_v1.tar.gz and P6_CLEAN_COMPLETE_v1.tar.gz.sha256"
