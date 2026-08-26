#!/usr/bin/env bash
set -euo pipefail

# Run from /home/anon_/ratchet/phase0_pilot (or set PROJECT_ROOT).
PROJECT_ROOT="${PROJECT_ROOT:-$(pwd)}"
EXP_ROOT="${EXP_ROOT:-${PROJECT_ROOT}/E2E_ATTR_AUTH_v1}"
CODE_DIR="${EXP_ROOT}/code"
OUT_DIR="${EXP_ROOT}/prefreeze/phase0_2_author_run"
INPUT_LOCK="${EXP_ROOT}/input_lock"

mkdir -p "${CODE_DIR}" "${OUT_DIR}" "${INPUT_LOCK}"

A13_COMBINED="${PROJECT_ROOT}/A13_C0_EXTENSION_SCIENCE_v1/A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl"
A13_INPUT_ZIP="${PROJECT_ROOT}/A13_C0_INPUT_BUNDLE_v1.zip"
A13_HIST_ZIP="${PROJECT_ROOT}/A13_C0_HISTORICAL_A13_COMPLETE_v1.zip"

PROTOCOL="${PROJECT_ROOT}/USENIX27_FINAL_EXPERIMENT_FREEZE_E2E_ATTRIGUARD_v4_FINAL_CODING_FREEZE_RECONCILED.md"
CANONICAL="${PROJECT_ROOT}/CANONICAL_USENIX_RESEARCH_DOSSIER_v140_E2E_SYSTEMS_STORY_RECONCILED.md"
BLUEPRINT="${PROJECT_ROOT}/USENIX27_MANUSCRIPT_BLUEPRINT_RECONCILED_v20_E2E_SYSTEMS_STORY_RECONCILED.md"
WRITING="${PROJECT_ROOT}/USENIX27_SUBMISSION_LEVEL_WRITING_DIAGNOSIS_v8_E2E_COHERENCE_RECONCILED.md"

CENSUS_SCRIPT="${CODE_DIR}/E2E_A1_00_build_census.py"
AUDIT_SCRIPT="${CODE_DIR}/E2E_A1_01_multicall_source_audit.py"

for f in "$A13_COMBINED" "$A13_INPUT_ZIP" "$A13_HIST_ZIP" "$PROTOCOL" "$CANONICAL" "$BLUEPRINT" "$WRITING" "$CENSUS_SCRIPT" "$AUDIT_SCRIPT"; do
  [[ -f "$f" ]] || { echo "MISSING: $f" >&2; exit 2; }
done

# Exact pre-outcome locks already reconciled in v140/v4.
declare -A EXPECTED
EXPECTED["$A13_INPUT_ZIP"]="3e6aaae53bfe10c57156c41def0dd13b3ada05ec299b5803a52bf586082984a2"
EXPECTED["$A13_HIST_ZIP"]="d4b48c9bde17602e47c2d2feea3f17ee5f2ba6f090395b011b3e84bc3fabc327"
EXPECTED["$A13_COMBINED"]="f24b89d53ad504cf16dce3820e9b028f1d752bcc829ecf43ed3e0997feb764f5"
EXPECTED["$PROTOCOL"]="4d992b635e9dbc13f5eb276f6a1264fbb9600e494c07da87d9b7217b361ce2e0"
EXPECTED["$CANONICAL"]="641734bd2fc8fb09cc831c60f0f5d564ac860d94a814c367ae964ba4170c39d3"
EXPECTED["$BLUEPRINT"]="6846fa3710844227d4f12e6182748081723114fc529ae8d9921c98bd0fb2a8a7"
EXPECTED["$WRITING"]="e1bf6e5bbce1ed686be94a4b230dbbb15dc6234ac15f237e2016b509c44eb7c4"
EXPECTED["$CENSUS_SCRIPT"]="9f2ef063cdec7cf2ac739b1f33d6f6d38eb3eaa1f1b3eaff928f90a48a524864"
EXPECTED["$AUDIT_SCRIPT"]="0b1ced71c4e9de4a1814ae1cd7e756c4b411a20f6b5a565840b1992fae8a9078"

for f in "${!EXPECTED[@]}"; do
  got="$(sha256sum "$f" | awk '{print $1}')"
  if [[ "$got" != "${EXPECTED[$f]}" ]]; then
    echo "HASH FAIL: $f" >&2
    echo " expected ${EXPECTED[$f]}" >&2
    echo " got      $got" >&2
    exit 3
  fi
done

echo "SOURCE/HASH PREFLIGHT PASS"

# Extract the frozen A13 AgentDojo source into an experiment-private lock directory.
rm -rf "${INPUT_LOCK}/A13_C0_INPUT_BUNDLE_v1"
unzip -q "$A13_INPUT_ZIP" -d "$INPUT_LOCK"
AGENTDOJO_LOCK="${INPUT_LOCK}/A13_C0_INPUT_BUNDLE_v1/agentdojo_source/default_suites/v1"
PIP_SHOW_LOCK="${INPUT_LOCK}/A13_C0_INPUT_BUNDLE_v1/AGENTDOJO_PIP_SHOW.txt"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

python "$CENSUS_SCRIPT" \
  --a13-combined "$A13_COMBINED" \
  --agentdojo-v1-dir "$AGENTDOJO_LOCK" \
  --agentdojo-pip-show "$PIP_SHOW_LOCK" \
  --out-dir "$OUT_DIR" \
  --protocol "$PROTOCOL" \
  --canonical "$CANONICAL" \
  --blueprint "$BLUEPRINT" \
  --writing-diagnosis "$WRITING" \
  | tee "$OUT_DIR/PHASE0_2_AUTHOR_RUN.log"

python "$AUDIT_SCRIPT" \
  --cohort-census "$OUT_DIR/COHORT_CENSUS.csv" \
  --agentdojo-v1-dir "$AGENTDOJO_LOCK" \
  --out-dir "$OUT_DIR" \
  | tee -a "$OUT_DIR/PHASE0_2_AUTHOR_RUN.log"

# Rebuild a manifest after the source audit outputs are present.
{
  printf 'sha256\tbytes\tfilename\n'
  find "$OUT_DIR" -maxdepth 1 -type f ! -name 'FINAL_OUTPUT_SHA256.tsv' -print0 \
    | sort -z \
    | while IFS= read -r -d '' f; do
        printf '%s\t%s\t%s\n' "$(sha256sum "$f" | awk '{print $1}')" "$(stat -c %s "$f")" "$(basename "$f")"
      done
} > "$OUT_DIR/FINAL_OUTPUT_SHA256.tsv"

printf '\n=== PHASE 0-2 COMPLETE ===\n'
cat "$OUT_DIR/01_A13_CENSUS_REPORT.json"
printf '\n'
cat "$OUT_DIR/02_SOURCE_AUDIT_SUMMARY.json"
printf '\nNO SCIENTIFIC MODEL CALLS WERE MADE. FINAL B IS NOT YET FROZEN.\n'
printf 'NEXT: Phase 3 blinded authorization/effect + AttriGuard scope audit.\n'
