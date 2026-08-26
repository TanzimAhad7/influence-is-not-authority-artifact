#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=10_live_e2e_attriguard
REL=E2E_ATTR_AUTH_v1/scientific_v1
restore_path "$REL"
rm -rf "$WORK_ROOT/$REL"
mkdir -p "$WORK_ROOT/$REL"
RUNNER=E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1/code/E2E_PRE_03_science_runner.py
ANALYZER=E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1/code/E2E_PRE_02_analysis.py
run_logged "${STAGE}_science" python3 "$RUNNER" --project-root "$WORK_ROOT"
ROWS="$WORK_ROOT/$REL/RUN_ROWS.jsonl"
[[ -f "$ROWS" ]] || fail "live E2E runner did not produce $ROWS"
run_logged "${STAGE}_analysis" python3 "$ANALYZER" --rows "$ROWS" --out "$WORK_ROOT/$REL/ANALYSIS_REPRODUCED.json"
capture_path "$STAGE" "$REL"
restore_path "$REL"
say "$STAGE complete"
