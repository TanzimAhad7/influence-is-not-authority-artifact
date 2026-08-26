#!/usr/bin/env bash
set -euo pipefail
TARGET="${1:-/home/anon_/ratchet/phase0_pilot/P2B_XM_CI_v1_2_PREOUTCOME_TECH_GATE_CORRECTED}"
HERE="$(cd "$(dirname "$0")" && pwd)"
[ -d "$TARGET" ] || { echo "FATAL target not found: $TARGET"; exit 2; }
cd "$TARGET"

# Must be pre-science.
for r in /home/anon_/ratchet/phase0_pilot/P2B_XM_CI_*_RUN_v1_2/P2B_CI_BASELINE_RAW.jsonl; do
  [ -e "$r" ] || continue
  if [ -s "$r" ]; then echo "FATAL scientific rows already exist: $r"; exit 3; fi
done

# Preserve original freeze and failed self-test provenance if present.
if [ -f P2B_XM_CI_GLOBAL_FREEZE.json ] && [ ! -f P2B_XM_CI_GLOBAL_FREEZE_SUPERSEDED_ORIGINAL_v1_2.json ]; then
  cp -p P2B_XM_CI_GLOBAL_FREEZE.json P2B_XM_CI_GLOBAL_FREEZE_SUPERSEDED_ORIGINAL_v1_2.json
fi

cp "$HERE/action_local.py" ./action_local.py
cp "$HERE/P2b_CI_00_static_audit.py" ./P2b_CI_00_static_audit.py
cp "$HERE/P2b_CI_02_freeze_global.py" ./P2b_CI_02_freeze_global.py
cp "$HERE/V1_2_1R_ACTION_LOCAL_ORACLE_AMENDMENT.md" ./V1_2_1R_ACTION_LOCAL_ORACLE_AMENDMENT.md

python -m py_compile action_local.py P2b_CI_00_static_audit.py P2b_CI_02_freeze_global.py
python -u P2b_CI_00_static_audit.py

echo "PATCH APPLIED. Existing technical preflight evidence was not modified."
echo "Next: run python -u P2b_CI_02_freeze_global.py; it will cryptographically accept or reject evidence reuse."
