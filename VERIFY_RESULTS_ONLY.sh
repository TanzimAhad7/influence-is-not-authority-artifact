#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
command -v python3 >/dev/null || { echo 'FAIL: python3 required'; exit 2; }
python3 scripts/verification/verify_current_claims.py
python3 scripts/verification/verify_hashes.py
python3 scripts/verification/verify_source_coverage.py
echo 'RESULTS_ONLY_VERIFY=PASS'
