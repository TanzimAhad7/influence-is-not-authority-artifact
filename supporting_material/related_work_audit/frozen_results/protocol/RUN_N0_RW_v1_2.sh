#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-N0_RW_AUTHOR_RUN_v1_2}"
SCRIPT="${2:-N0_RW_00_prior_art_audit_v1_2.py}"
EXPECTED_SCRIPT_SHA="0d2ca8513c52f827aece73d498eda667349bcfb96a71c39350fe6d9d3d1c1217"

if [[ -e "$OUT" || -e "${OUT}.tar.gz" || -e "${OUT}.tar.gz.sha256" ]]; then
  echo "STOP: output/package already exists. Preserve it and choose a NEW OUT name: $OUT" >&2
  exit 2
fi

if [[ ! -f "$SCRIPT" ]]; then
  echo "STOP: script not found: $SCRIPT" >&2
  exit 2
fi

ACTUAL_SCRIPT_SHA="$(sha256sum "$SCRIPT" | awk '{print $1}')"
if [[ "$ACTUAL_SCRIPT_SHA" != "$EXPECTED_SCRIPT_SHA" ]]; then
  echo "STOP: script SHA mismatch" >&2
  echo "expected=$EXPECTED_SCRIPT_SHA" >&2
  echo "actual=$ACTUAL_SCRIPT_SHA" >&2
  exit 2
fi

echo "=== N0-RW v1.2 PREFLIGHT ==="
python3 --version
printf 'script_sha256=%s\n' "$ACTUAL_SCRIPT_SHA"
if [[ -n "${OPENALEX_API_KEY:-}" ]]; then
  echo "openalex_api_key_present=YES (value will not be written)"
else
  echo "openalex_api_key_present=NO (current keyless budget is sufficient for this frozen request count unless already consumed elsewhere)"
fi

echo "=== PLAN ==="
python3 "$SCRIPT" --print-plan

echo "=== FREEZE ==="
python3 "$SCRIPT" --freeze --out "$OUT" --runner "$0"

echo "=== RUN ==="
python3 "$SCRIPT" --run --out "$OUT" --runner "$0"

echo "=== VERIFY FINAL LEDGER ==="
(
  cd "$OUT"
  sha256sum -c N0_RW_SHA256.txt
)

echo "=== PACKAGE ==="
tar -czf "${OUT}.tar.gz" "$OUT"
sha256sum "${OUT}.tar.gz" > "${OUT}.tar.gz.sha256"

echo "=== DONE ==="
cat "$OUT/N0_RW_RUN_COMPLETE.json"
echo
cat "${OUT}.tar.gz.sha256"
