#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/home/anon_/ratchet/phase0_pilot}"
CLEAN="$PROJECT_ROOT/P0B3_CAUSALARMOR_CLEAN_FULL_RERUN_v1"
LIVE="$PROJECT_ROOT/P0B3_CAUSALARMOR_LIVE_v1"
FREEZE="$PROJECT_ROOT/P0B3_CAUSALARMOR_CALIBRATION_FREEZE_COMPLETE_v1.zip"
OUT="$PROJECT_ROOT/P0B3_CAUSALARMOR_LIVE_RUN_v1"

echo "============================================================"
echo "P0b-3 CLEAN FULL RERUN — ATTEMPT 1"
echo "============================================================"

python -u "$CLEAN/P0B3_10_verify_clean_start.py" \
  --project-root "$PROJECT_ROOT"

# This is the original frozen live technical preflight.
# It makes synthetic technical calls only and executes 0 AgentDojo benchmark episodes.
python -u "$LIVE/P0B3_10_live_preflight.py" \
  --project-root "$PROJECT_ROOT" \
  --package-dir "$LIVE" \
  --freeze-complete "$FREEZE" \
  --out-dir "$OUT"

# Prospectively record the only runtime finalization before Attempt-1 benchmark outcomes.
python -u "$CLEAN/P0B3_20_finalize_32k_before_science.py" \
  --project-root "$PROJECT_ROOT"

echo "============================================================"
echo "BEGINNING ATTEMPT-1 SCIENCE FROM 0/1046"
echo "============================================================"

# Original frozen science runner, unchanged.
python -u "$LIVE/P0B3_20_run_science.py" \
  --project-root "$PROJECT_ROOT" \
  --package-dir "$LIVE" \
  --freeze-complete "$FREEZE" \
  --out-dir "$OUT"

# Original deterministic frozen analysis, unchanged.
python -u "$LIVE/P0B3_30_analyze.py" \
  --package-dir "$LIVE" \
  --freeze-complete "$FREEZE" \
  --out-dir "$OUT"

# Original final-artifact hashes.
python -u "$LIVE/P0B3_40_hash_outputs.py" \
  --out-dir "$OUT"

# Clean-rerun completeness + integrity layer.
python -u "$CLEAN/P0B3_90_validate_complete_clean_rerun.py" \
  --project-root "$PROJECT_ROOT"

echo "============================================================"
echo "P0b-3 CLEAN FULL RERUN + ANALYSIS COMPLETE"
echo "DO NOT RUN P6 YET — RETURN THE COMPLETE ARCHIVE FOR ADJUDICATION"
echo "============================================================"
