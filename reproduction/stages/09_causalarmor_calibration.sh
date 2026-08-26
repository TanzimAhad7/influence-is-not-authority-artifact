#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=09_causalarmor_calibration
REL=P0B3_CAUSALARMOR_LIVE_RUN_v1
restore_path "$REL"
rm -rf "$WORK_ROOT/$REL"
PID=""
cleanup(){ stop_pid "$PID"; restore_path "$REL"; }
trap cleanup EXIT
PID=$(start_vllm p0b3_gemma "google/gemma-3-12b-it" "96b6f1eccf38110c56df3a15bffe176da04bfd80" 8100 "$GPU_LIST" 2 16384 0.90 --max-logprobs 5 --seed 0 --tokenizer-mode hf --generation-config vllm)
PKG="$WORK_ROOT/P0B3_CAUSALARMOR_LIVE_v1"
run_logged "${STAGE}_preflight" python3 "$PKG/P0B3_10_live_preflight.py" --project-root "$WORK_ROOT" --package-dir "$PKG" --freeze-complete "$WORK_ROOT/P0B3_CAUSALARMOR_CALIBRATION_FREEZE_COMPLETE_v1.zip" --out-dir "$WORK_ROOT/$REL"
run_logged "${STAGE}_science_analysis" bash "$PKG/P0B3_RUN_SCIENCE_THEN_ANALYZE.sh" "$WORK_ROOT"
capture_path "$STAGE" "$REL"
say "$STAGE complete"
