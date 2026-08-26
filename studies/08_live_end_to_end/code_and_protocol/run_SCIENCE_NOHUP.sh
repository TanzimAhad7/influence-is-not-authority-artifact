#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$PWD}"
PKG="$ROOT/E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1"
LOG="$ROOT/E2E_ATTR_AUTH_v1/E2E_SCIENCE_AUTHOR_RUN.log"
PIDF="$ROOT/E2E_ATTR_AUTH_v1/E2E_SCIENCE_AUTHOR_RUN.pid"
[[ -f "$ROOT/E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build/PREFREEZE_COMPLETE.md" ]] || { echo 'FATAL no GO seal'; exit 2; }
mkdir -p "$ROOT/E2E_ATTR_AUTH_v1"
nohup python -u "$PKG/code/E2E_PRE_03_science_runner.py" --project-root "$ROOT" >"$LOG" 2>&1 &
echo $! | tee "$PIDF"
echo "Started E2E science PID=$(cat "$PIDF") log=$LOG"
