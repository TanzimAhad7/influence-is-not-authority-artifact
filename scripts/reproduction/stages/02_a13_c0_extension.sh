#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=02_a13_c0_extension
for rel in A13_C0_EXTENSION_RUNNER_FREEZE_v1 A13_C0_EXTENSION_SCIENCE_v1; do restore_path "$rel"; clear_path "$rel"; done
rm -f "$WORK_ROOT/A13_C0_EXTENSION_RUNNER_PREFLIGHT_v1_AUTHOR_RUN.log" "$WORK_ROOT/A13_C0_EXTENSION_SCIENCE_v1_AUTHOR_RUN.log"
for f in A13_C0_INPUT_BUNDLE_v1.zip A13_C0_HISTORICAL_A13_COMPLETE_v1.zip A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz; do [[ -f "$WORK_ROOT/$f" ]] || fail "missing A13-C0 dependency $f"; done
PATCHED="$RUN_ROOT/a13c0_runner_anonymous.py"
python3 "$ARTIFACT_ROOT/scripts/reproduction/patch_a13c0_runner_for_anonymous_archives.py" --source "$WORK_ROOT/A13_C0_EXTENSION_RUNNER_v1.py" --c0-archive "$WORK_ROOT/A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz" --prefreeze-archive "$WORK_ROOT/A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz" --out "$PATCHED"
start_vllm a13c0_qwen 'Qwen/Qwen2.5-72B-Instruct' '-' 8100 "$GPU_LIST" 2 16384 0.90 --max-logprobs 5 --enable-auto-tool-choice --tool-call-parser hermes --seed 0
PID=$(cat "$SERVER_ROOT/a13c0_qwen.pid"); trap 'stop_pid "$PID"' EXIT
run_logged "${STAGE}_preflight" python3 "$PATCHED" --mode preflight "$WORK_ROOT" --input-bundle-zip "$WORK_ROOT/A13_C0_INPUT_BUNDLE_v1.zip" --historical-zip "$WORK_ROOT/A13_C0_HISTORICAL_A13_COMPLETE_v1.zip" --c0-v21-author-archive "$WORK_ROOT/A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz" --extension-prefreeze-archive "$WORK_ROOT/A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz"
FREEZE_JSON="$WORK_ROOT/A13_C0_EXTENSION_RUNNER_FREEZE_v1/A13_C0_EXTENSION_RUNNER_FREEZE_v1.json"
FREEZE_SHA=$(sha256sum "$FREEZE_JSON" | awk '{print $1}')
run_logged "${STAGE}_science" python3 "$PATCHED" --mode science "$WORK_ROOT" --input-bundle-zip "$WORK_ROOT/A13_C0_INPUT_BUNDLE_v1.zip" --historical-zip "$WORK_ROOT/A13_C0_HISTORICAL_A13_COMPLETE_v1.zip" --c0-v21-author-archive "$WORK_ROOT/A13_C0_V2_1_AUTHOR_RUN_COMPLETE.tar.gz" --extension-prefreeze-archive "$WORK_ROOT/A13_C0_EXTENSION_PREFREEZE_v1_AUTHOR_COMPLETE.tar.gz" --runner-freeze-json "$FREEZE_JSON" --expected-runner-freeze-sha256 "$FREEZE_SHA"
capture_path "$STAGE" A13_C0_EXTENSION_RUNNER_FREEZE_v1
capture_path "$STAGE" A13_C0_EXTENSION_SCIENCE_v1
restore_path A13_C0_EXTENSION_RUNNER_FREEZE_v1
restore_path A13_C0_EXTENSION_SCIENCE_v1
stop_pid "$PID"; trap - EXIT
say "$STAGE complete"
