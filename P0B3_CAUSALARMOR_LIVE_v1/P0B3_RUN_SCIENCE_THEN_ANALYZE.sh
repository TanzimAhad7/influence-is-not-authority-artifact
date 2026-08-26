#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="${1:-/home/anon_/ratchet/phase0_pilot}"
PKG="$PROJECT_ROOT/P0B3_CAUSALARMOR_LIVE_v1"
FREEZE="$PROJECT_ROOT/P0B3_CAUSALARMOR_CALIBRATION_FREEZE_COMPLETE_v1.zip"
OUT="$PROJECT_ROOT/P0B3_CAUSALARMOR_LIVE_RUN_v1"
python -u "$PKG/P0B3_20_run_science.py" --project-root "$PROJECT_ROOT" --package-dir "$PKG" --freeze-complete "$FREEZE" --out-dir "$OUT"
python -u "$PKG/P0B3_30_analyze.py" --package-dir "$PKG" --freeze-complete "$FREEZE" --out-dir "$OUT"
python -u "$PKG/P0B3_40_hash_outputs.py" --out-dir "$OUT"
echo "P0b-3 SCIENCE + ANALYSIS COMPLETE"
