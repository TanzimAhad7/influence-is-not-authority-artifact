#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export USENIX_RUN_ROOT="${USENIX_RUN_ROOT:-$(dirname "$ROOT")/USENIX27_FIGURE_RERUN_$(date -u +%Y%m%dT%H%M%SZ)}"
exec bash "$ROOT/RUN_END_TO_END.sh" --stage 12
