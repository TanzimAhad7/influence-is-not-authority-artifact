#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$PWD}"
PKG="$ROOT/E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1"
python "$PKG/code/E2E_PRE_05_live_dev_preflight.py" --project-root "$ROOT"
python "$PKG/code/E2E_PRE_06_seal.py" "$ROOT"
echo '=== FINAL PRE-SCIENCE GO SEAL COMPLETE ==='
echo 'No scientific cohort outcomes have been generated.'
echo 'NEXT COMMAND AFTER INDEPENDENT CONSOLIDATED AUDIT: scientific author run.'
