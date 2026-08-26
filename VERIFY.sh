#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Fast/offline verification of the distributed frozen evidence. Full provider/model rerun is RUN_END_TO_END.sh.
exec bash "$ROOT/VERIFY_RESULTS_ONLY.sh" "$@"
