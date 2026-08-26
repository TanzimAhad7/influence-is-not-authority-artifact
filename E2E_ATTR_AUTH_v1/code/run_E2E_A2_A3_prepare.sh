#!/usr/bin/env bash
set -euo pipefail
ROOT="${PROJECT_ROOT:-$PWD}"
CODE="$ROOT/E2E_ATTR_AUTH_v1/code"
P02="$ROOT/E2E_ATTR_AUTH_v1/prefreeze/phase0_2_author_run"
IN="$ROOT/E2E_ATTR_AUTH_v1/input_lock/A13_C0_INPUT_BUNDLE_v1/agentdojo_source/default_suites/v1"
OUT="$ROOT/E2E_ATTR_AUTH_v1/prefreeze/phase3_author_run"
PROTO="$ROOT/USENIX27_FINAL_EXPERIMENT_FREEZE_E2E_ATTRIGUARD_v4_FINAL_CODING_FREEZE_RECONCILED.md"
mkdir -p "$OUT/A1_PROVENANCE_AMENDMENT" "$OUT/A2_A3_PREP"
LOG="$OUT/A2_A3_PREP_AUTHOR_RUN.log"
: > "$LOG"
exec > >(tee -a "$LOG") 2>&1

need(){ [[ -f "$1" ]] || { echo "MISSING: $1"; exit 2; }; }
need "$PROTO"; need "$P02/FINAL_OUTPUT_SHA256.tsv"; need "$P02/02_MULTI_CALL_SOURCE_AUDIT.csv"; need "$P02/02_COHORT_AFTER_SOURCE_AUDIT.csv"; need "$P02/01_A13_PRIMARY_DECISIONS.jsonl"
need "$CODE/E2E_A2_00_fix_a1_provenance.py"; need "$CODE/E2E_A2_01_build_auth_alt_and_blinded_packet.py"

PROTO_SHA=$(sha256sum "$PROTO" | awk '{print $1}')
[[ "$PROTO_SHA" == "4d992b635e9dbc13f5eb276f6a1264fbb9600e494c07da87d9b7217b361ce2e0" ]] || { echo "PROTOCOL HASH FAIL $PROTO_SHA"; exit 3; }

echo "Verifying Phase0-2 author outputs..."
while IFS=$'\t' read -r sha bytes rel; do
  [[ "$sha" == "sha256" ]] && continue
  need "$P02/$rel"
  got=$(sha256sum "$P02/$rel" | awk '{print $1}')
  size=$(stat -c%s "$P02/$rel")
  [[ "$got" == "$sha" && "$size" == "$bytes" ]] || { echo "PHASE0-2 HASH/SIZE FAIL $rel"; exit 4; }
done < "$P02/FINAL_OUTPUT_SHA256.tsv"

echo "PHASE0-2 HASH PREFLIGHT PASS"
python "$CODE/E2E_A2_00_fix_a1_provenance.py" \
  --phase0-2-dir "$P02" --agentdojo-v1-dir "$IN" --out-dir "$OUT/A1_PROVENANCE_AMENDMENT"
python "$CODE/E2E_A2_01_build_auth_alt_and_blinded_packet.py" \
  --phase0-2-dir "$P02" --agentdojo-v1-dir "$IN" --out-dir "$OUT/A2_A3_PREP"

# Hash all completed prep outputs (excluding this live log until final ledger).
(
  cd "$OUT"
  find A1_PROVENANCE_AMENDMENT A2_A3_PREP -type f -print0 | sort -z | xargs -0 sha256sum
) > "$OUT/A2_A3_PREP_OUTPUT_SHA256.tsv"

cat <<'EOF'

=== PHASE A2/A3 PREPARATION COMPLETE ===
NO SCIENTIFIC MODEL CALLS WERE MADE.
FINAL B IS NOT YET FROZEN.
NEXT: give ONLY BLINDED_RATER_PACKET_FOR_REVIEW.zip to an independent reviewer.
Do NOT give the reviewer CASE_MAP.csv, AUTH_ALT_LEDGER_DRAFT.jsonl, prior results, or experiment/defense hypothesis.
EOF
