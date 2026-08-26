#!/usr/bin/env bash
# ==========================================================================
#  RUN_ALL.sh -- verify every manuscript claim + run every PoC. One command.
#
#  Put this folder ANYWHERE inside (or next to) phase0_pilot and run:
#      ./RUN_ALL.sh
#
#  It locates phase0_pilot by walking up from its own location, then finds
#  E2E_ATTR_AUTH_v1, AttriGuard.py, and the AgentWatcher adapter underneath.
#  Override any of them:  ROOT=... E2E=... ATTRIGUARD=... ADAPTER=... ./RUN_ALL.sh
#
#  No network. No API keys. No GPU. Deterministic. Seconds.
# ==========================================================================
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

hr(){ printf '=%.0s' {1..74}; echo; }
step(){ echo; hr; echo " $1"; hr; }

# ---- locate the project root -------------------------------------------
find_root() {
  local d="$HERE"
  for _ in 1 2 3 4 5 6; do
    if [ -d "$d/artifacts" ] && [ -d "$d/a14_minimal_factorial" ]; then echo "$d"; return; fi
    if [ -d "$d/phase0_pilot/artifacts" ]; then echo "$d/phase0_pilot"; return; fi
    d="$(dirname "$d")"
  done
  echo ""
}
ROOT="${ROOT:-$(find_root)}"
if [ -z "$ROOT" ] || [ ! -d "$ROOT" ]; then
  echo "Could not locate phase0_pilot from $HERE"
  echo "Run with an explicit root:   ROOT=/path/to/phase0_pilot $0"
  exit 2
fi

# ---- locate the three inputs -------------------------------------------
pick(){ find "$ROOT" -maxdepth "${2:-9}" $3 -name "$1" 2>/dev/null | head -1; }

E2E="${E2E:-}"
# direct hit first, then a symlink-following search
[ -z "$E2E" ] && [ -f "$ROOT/E2E_ATTR_AUTH_v1/scientific_v1/RUN_ROWS.jsonl" ] && E2E="$ROOT/E2E_ATTR_AUTH_v1"
[ -z "$E2E" ] && E2E="$(find -L "$ROOT" -maxdepth 4 -name 'E2E_ATTR_AUTH_v1' 2>/dev/null | head -1)"
if [ -z "$E2E" ]; then
  rr="$(find -L "$ROOT" -type f -name 'RUN_ROWS.jsonl' 2>/dev/null | head -1)"
  [ -n "$rr" ] && E2E="$(cd "$(dirname "$rr")/.." && pwd)"
fi

ATTRIGUARD="${ATTRIGUARD:-}"
[ -z "$ATTRIGUARD" ] && ATTRIGUARD="$(find "$ROOT" -type f -path '*attriguard*' -path '*main/pipeline*' -name 'AttriGuard.py' 2>/dev/null | head -1)"

ADAPTER="${ADAPTER:-}"
[ -z "$ADAPTER" ] && ADAPTER="$(find "$ROOT" -type f -name 'piarena_defense_adapter.py' -path '*AgentWatcher*' 2>/dev/null | head -1)"

OUT="${OUT:-$HERE/verification_out}"
mkdir -p "$OUT"
FAILED=0

step "0. Environment and inputs"
python3 -c "import numpy"    2>/dev/null || pip install numpy --quiet --break-system-packages
python3 -c "import agentdojo" 2>/dev/null || pip install 'agentdojo==0.1.35' --quiet --break-system-packages
python3 -c "import numpy, agentdojo; print('  numpy + agentdojo OK')"
echo "  script dir : $HERE"
for p in "ROOT:$ROOT" "E2E:$E2E" "ATTRIGUARD:$ATTRIGUARD" "ADAPTER:$ADAPTER"; do
  n="${p%%:*}"; v="${p#*:}"
  ok=0
  if [ -n "$v" ] && [ -e "$v" ]; then
    if [ "$n" = "E2E" ]; then
      [ -f "$v/scientific_v1/RUN_ROWS.jsonl" ] && ok=1
    else ok=1; fi
  fi
  if [ "$ok" = "1" ]; then echo "  [ok]   $n = $v"
  else echo "  [MISS] $n = ${v:-<not found>}"; FAILED=1; fi
done
if [ "$FAILED" -eq 1 ]; then
  echo; echo "Set the missing one(s) explicitly, e.g.:"
  echo "  E2E=/path/to/E2E_ATTR_AUTH_v1 $0"
  exit 2
fi

step "1. Claim verification -- re-derive every manuscript number"
python3 "$HERE/verify_all_claims.py" \
  --root "$ROOT" --e2e "$E2E" --attriguard "$ATTRIGUARD" \
  --out "$OUT/CLAIM_LEDGER.json" --md "$OUT/CLAIM_TO_ARTIFACT.md" \
  > "$OUT/claims.log" 2>&1
rc=$?; [ $rc -ne 0 ] && FAILED=1
grep -E "^\[FAIL|^\[-\?-|PASS  " "$OUT/claims.log" | tail -20
tail -1 "$OUT/claims.log"

step "2. PoC -- AttriGuard: a defense block suppresses the next audit"
python3 "$HERE/poc_bypass_attriguard.py" \
  --attriguard "$ATTRIGUARD" --out "$OUT/POC_BYPASS_RESULT.json" \
  > "$OUT/poc_attriguard.log" 2>&1
rc=$?; [ $rc -ne 0 ] && FAILED=1
sed -n '/^arm /,$p' "$OUT/poc_attriguard.log"

step "3. PoC -- AgentWatcher: first-call ordering, silent fail-open"
python3 "$HERE/poc_bypass_agentwatcher.py" \
  --adapter "$ADAPTER" --out "$OUT/POC_BYPASS_AGENTWATCHER_RESULT.json" \
  > "$OUT/poc_agentwatcher.log" 2>&1
rc=$?; [ $rc -ne 0 ] && FAILED=1
grep -E "^PATH|^  first|^  returned|^  proposed|^  any marker|^  \[PASS|^  \[FAIL|^ALL CHECKS" "$OUT/poc_agentwatcher.log"

step "4. Provenance manifest"
( cd "$OUT" && find . -type f ! -name 'MANIFEST.sha256' -print0 \
    | sort -z | xargs -0 sha256sum > MANIFEST.sha256 )
echo "  $(wc -l < "$OUT/MANIFEST.sha256") output files hashed -> $OUT/MANIFEST.sha256"
{ echo "run_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "host=$(hostname)"
  echo "user=\$(whoami)"
  echo "root=$ROOT"
  echo "e2e=$E2E"
  echo "attriguard=$ATTRIGUARD"
  echo "attriguard_sha256=$(sha256sum "$ATTRIGUARD" | cut -d' ' -f1)"
  echo "adapter=$ADAPTER"
  echo "adapter_sha256=$(sha256sum "$ADAPTER" | cut -d' ' -f1)"
  echo "python=$(python3 -V 2>&1)"
  echo "script_sha256=$(sha256sum "$HERE/poc_bypass_attriguard.py" | cut -d' ' -f1)"
} > "$OUT/RUN_PROVENANCE.txt"
echo "  environment recorded -> $OUT/RUN_PROVENANCE.txt"

step "5. Summary"
python3 - "$OUT" <<'PY'
import json, os, sys
out = sys.argv[1]
def load(f):
    p = os.path.join(out, f)
    return json.load(open(p)) if os.path.exists(p) else None
led = load("CLAIM_LEDGER.json")
if led:
    s = led["summary"]
    print(f"  claims          : {s['pass']} PASS  {s['fail']} FAIL  {s['unverified']} UNVERIFIED")
    for r in led["claims"]:
        if r["status"] != "PASS":
            print(f"     {r['status']}: {r['id']}  canonical={r['canonical']} recomputed={r['recomputed']}")
    if s['fail'] or s['unverified']:
        open(os.path.join(out, ".not_green"), "w").write("1")
for f, label in (("POC_BYPASS_RESULT.json", "poc attriguard"),
                 ("POC_BYPASS_AGENTWATCHER_RESULT.json", "poc agentwatcher")):
    d = load(f)
    if d:
        n = sum(1 for c in d["checks"] if c["passed"])
        sha = [v for k, v in d.items() if k.endswith("sha256")][0]
        print(f"  {label:<16}: {n}/{len(d['checks'])} checks passed   [source {sha[:12]}...]")
PY

[ -f "$OUT/.not_green" ] && { FAILED=1; rm -f "$OUT/.not_green"; }

echo
if [ "$FAILED" -eq 0 ]; then
  echo "  ALL GREEN.  Outputs in $OUT/"
  echo "  Ship CLAIM_TO_ARTIFACT.md with the artifact; cite CLAIM_LEDGER.json ids in main.tex."
else
  echo "  NOT GREEN (a claim FAILED or could not be verified)."
  echo "  Full logs in $OUT/ -- resolve before anything reaches main.tex."
fi
exit $FAILED
