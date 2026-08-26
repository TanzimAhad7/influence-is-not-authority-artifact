#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="${1:-/home/anon_/ratchet/phase0_pilot}"
PKG="$ROOT/P2_AGENTWATCHER_NODEFENSE_PREFREEZE_v1"
OUT="$ROOT/P2_AGENTWATCHER_NODEFENSE_RUN_v1"
cd "$ROOT"
source "$ROOT/.venv/bin/activate"

echo "============================================================"
echo "P2 AGENTWATCHER SAME-200 DEFENSE-DISABLED BASELINE"
echo "============================================================"
echo "root=$ROOT"
echo "attack=tool_knowledge"
echo "defense=none"
echo "sample=exact frozen 200"
echo "requested_model=gpt-4o-mini"
echo "route=OpenRouter"
echo

if [[ ! -d "$PKG" ]]; then echo "FATAL: missing package dir $PKG"; exit 1; fi
(cd "$PKG" && sha256sum -c PACKAGE_SHA256.txt)

# Clean-start rule: never overwrite a scientific P2 outcome.
if [[ -e "$OUT" ]]; then
  echo "FATAL: $OUT already exists. Do not overwrite a P2 scientific attempt."
  exit 1
fi
RAW_EXTERNAL="$ROOT/external/AgentWatcher_armc_runtime_v1/results/agent_evaluations/agentdojo/P2_AW_NODEFENSE_TOOL_KNOWLEDGE_200_v1"
if [[ -e "$RAW_EXTERNAL" ]]; then
  echo "FATAL: raw P2 external result dir already exists: $RAW_EXTERNAL"
  exit 1
fi

python -u "$PKG/P2_00_preflight_freeze.py" --project-root "$ROOT" --package-dir "$PKG" --out-dir "$OUT"

echo
cat "$OUT/P2_SCIENCE_FREEZE.md"
echo

echo "================ SCIENCE RUN ================"
python -u "$PKG/P2_01_run_nodefense.py" --project-root "$ROOT" --package-dir "$PKG" --out-dir "$OUT"

echo "================ ANALYSIS ================"
python -u "$PKG/P2_02_analyze.py" --project-root "$ROOT" --package-dir "$PKG" --out-dir "$OUT"

echo "================ VERIFY ================"
python -u "$PKG/P2_03_verify.py" --project-root "$ROOT" --package-dir "$PKG" --out-dir "$OUT"

echo
cat "$OUT/P2_ANALYSIS.md"
echo

echo "================ ARCHIVE ================"
cd "$ROOT"
rm -f P2_AGENTWATCHER_NODEFENSE_COMPLETE_v1.tar.gz P2_AGENTWATCHER_NODEFENSE_COMPLETE_v1.tar.gz.sha256
# Include implementation + run outputs + top-level console log if outer command creates it later, archive core first.
tar -czf P2_AGENTWATCHER_NODEFENSE_COMPLETE_v1.tar.gz \
  P2_AGENTWATCHER_NODEFENSE_PREFREEZE_v1 \
  P2_AGENTWATCHER_NODEFENSE_RUN_v1
sha256sum P2_AGENTWATCHER_NODEFENSE_COMPLETE_v1.tar.gz | tee P2_AGENTWATCHER_NODEFENSE_COMPLETE_v1.tar.gz.sha256

echo
echo "P2 AGENTWATCHER NODEFENSE AUTHOR EXECUTION COMPLETE"
echo "Upload:"
echo "  $ROOT/P2_AGENTWATCHER_NODEFENSE_COMPLETE_v1.tar.gz"
echo "  $ROOT/P2_AGENTWATCHER_NODEFENSE_COMPLETE_v1.tar.gz.sha256"
