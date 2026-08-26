#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo '[1/4] shell syntax'
while IFS= read -r -d '' f; do bash -n "$f"; done < <(find "$ROOT" -type f -name '*.sh' -print0)
echo 'SHELL_SYNTAX=PASS'

echo '[2/4] structural preflight'
bash "$ROOT/CHECK_E2E.sh" --structural

echo '[3/4] full orchestration dry-run'
bash "$ROOT/RUN_END_TO_END.sh" --dry-run --all

echo '[4/4] exact frozen-result verification'
bash "$ROOT/VERIFY.sh"

echo 'ARTIFACT_SELF_TEST=PASS'
