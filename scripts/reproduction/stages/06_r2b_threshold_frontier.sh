#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../lib.sh"
STAGE=06_r2b_threshold_frontier
REL=R2B_JTF_AUTHOR_v1
restore_path "$REL"
# The R2B frontier is deterministic over the frozen A14/N3 score evidence.
run_logged "$STAGE" bash R2B_JTF_PREFREEZE_v1/analyze_R2B_JTF_v1.sh "$WORK_ROOT"
capture_path "$STAGE" "$REL"
restore_path "$REL"
say "$STAGE complete"
