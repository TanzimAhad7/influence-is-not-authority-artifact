#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
require_keys
STAGE=08_n6_attriguard_architecture
REL=n6_attriguard_n3_v1/scientific_v1
restore_path "$REL"
rm -rf "$WORK_ROOT/$REL"
run_logged "${STAGE}_science" python3 N6_ATTRIGUARD_N3_TECH_AMENDMENT_v1_2/N6_05_run_science.py --project-root "$WORK_ROOT"
run_logged "${STAGE}_analysis" python3 N6_ATTRIGUARD_N3_TECH_AMENDMENT_v1_2/N6_06_analyze.py --project-root "$WORK_ROOT"
capture_path "$STAGE" "$REL"
restore_path "$REL"
say "$STAGE complete"
