#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$PWD}"
OUTZIP="$ROOT/E2E_ATTR_AUTH_FINAL_PRESCIENCE_AUTHOR_OUTPUTS.zip"
rm -f "$OUTZIP"
cd "$ROOT"
zip -qr "$OUTZIP" \
  E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build \
  E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1/PACKAGE_SHA256.txt
sha256sum "$OUTZIP"
echo "SEND THIS FILE: $OUTZIP"
