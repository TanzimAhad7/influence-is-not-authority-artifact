#!/usr/bin/env bash
set -euo pipefail
ARTIFACT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
usage(){ cat <<'TXT'
Usage:
  bash RUN_END_TO_END.sh --all
  bash RUN_END_TO_END.sh --stage <number-or-name> [--stage ...]
  bash RUN_END_TO_END.sh --list
  bash RUN_END_TO_END.sh --dry-run --all

The runner creates a fresh sibling working copy and NEVER writes model results into the
frozen distributed artifact. Set USENIX_RUN_ROOT to choose another output directory.
TXT
}
ALL=0; LIST=0; DRY=0; declare -a WANT=()
while [[ $# -gt 0 ]]; do
 case "$1" in
  --all) ALL=1; shift;;
  --list) LIST=1; shift;;
  --dry-run) DRY=1; shift;;
  --stage) [[ $# -ge 2 ]] || { usage; exit 2; }; WANT+=("$2"); shift 2;;
  -h|--help) usage; exit 0;;
  *) echo "unknown argument: $1" >&2; usage; exit 2;;
 esac
done
STAGES=(
  01_a13_natural
  02_a13_c0_extension
  03_b1_generator_breadth
  04_a14_controlled_source
  05_n3_unauthorized_control
  06_r2b_threshold_frontier
  07_agentwatcher
  08_n6_attriguard_architecture
  09_causalarmor_calibration
  10_live_e2e_attriguard
  11_replay
  12_figures
)
if [[ $LIST -eq 1 ]]; then printf '%s\n' "${STAGES[@]}"; exit 0; fi
(( ALL || ${#WANT[@]} )) || { usage; exit 2; }
choose(){
 local s="$1" w
 (( ALL )) && return 0
 for w in "${WANT[@]}"; do [[ "$w" == "$s" || "$w" == "${s%%_*}" || "$s" == "$w"* ]] && return 0; done
 return 1
}

# Validate the distributed package before creating an execution worktree.
# Deterministic stages 06 and 12 do not require provider credentials or GPUs.
NEEDS_FULL_PREFLIGHT=0
if (( ALL )); then
  NEEDS_FULL_PREFLIGHT=1
else
  for w in "${WANT[@]}"; do
    case "$w" in
      06|06_*|12|12_*) ;;
      *) NEEDS_FULL_PREFLIGHT=1 ;;
    esac
  done
fi
if (( DRY )); then
  bash "$ARTIFACT_ROOT/CHECK_E2E.sh" --structural
  echo "DRY_RUN=1"
  for s in "${STAGES[@]}"; do
    choose "$s" || continue
    f="$ARTIFACT_ROOT/reproduction/stages/$s.sh"
    [[ -f "$f" ]] || { echo "FATAL: missing stage script: $f" >&2; exit 2; }
    bash -n "$f"
    echo "WOULD_RUN=$s"
  done
  echo "END_TO_END_DRY_RUN=PASS"
  exit 0
fi
if (( NEEDS_FULL_PREFLIGHT )); then
  bash "$ARTIFACT_ROOT/CHECK_E2E.sh"
else
  bash "$ARTIFACT_ROOT/CHECK_E2E.sh" --structural
fi
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BASE="$(dirname "$ARTIFACT_ROOT")"
RUN_ROOT="${USENIX_RUN_ROOT:-$BASE/USENIX27_RERUN_$STAMP}"
WORK_ROOT="$RUN_ROOT/worktree"
mkdir -p "$RUN_ROOT"
[[ ! -e "$WORK_ROOT" ]] || { echo "FATAL: worktree already exists: $WORK_ROOT" >&2; exit 2; }
echo "[master] artifact=$ARTIFACT_ROOT"
echo "[master] run_root=$RUN_ROOT"
echo "[master] copying frozen artifact to disposable worktree..."
mkdir -p "$WORK_ROOT"
# The venv and generated verification outputs are not scientific inputs and can be large.
( cd "$ARTIFACT_ROOT" && tar --exclude='./.venv-e2e' --exclude='./artifact_outputs' --exclude='./reproduction_runs' -cf - . ) | ( cd "$WORK_ROOT" && tar -xf - )
# Historical experiment scripts retain their frozen top-level identifiers.
# Recreate that layout only inside this disposable worktree.
python3 "$ARTIFACT_ROOT/reproduction/materialize_legacy_worktree.py" --work-root "$WORK_ROOT"
export ARTIFACT_ROOT WORK_ROOT RUN_ROOT
export PYTHONUNBUFFERED=1
export TOKENIZERS_PARALLELISM=false
export HF_TOKEN="${HF_TOKEN:-${HUGGING_FACE_HUB_TOKEN:-}}"
[[ -n "$HF_TOKEN" ]] && export HUGGING_FACE_HUB_TOKEN="$HF_TOKEN"
mkdir -p "$RUN_ROOT/results" "$RUN_ROOT/servers"
cat > "$RUN_ROOT/RUN_METADATA.txt" <<META
started_utc=$STAMP
artifact_root=$ARTIFACT_ROOT
work_root=$WORK_ROOT
gpu_list=${USENIX_GPU_LIST:-0,1}
META
FAIL=0
for s in "${STAGES[@]}"; do
 choose "$s" || continue
 echo
 echo "================================================================"
 echo "STAGE $s"
 echo "================================================================"
 if bash "$ARTIFACT_ROOT/reproduction/stages/$s.sh"; then
   touch "$RUN_ROOT/results/${s}.DONE"
 else
   echo "STAGE_FAILED=$s" | tee -a "$RUN_ROOT/RUN_METADATA.txt" >&2
   FAIL=1; break
 fi
done
if [[ $FAIL -ne 0 ]]; then
 echo "END_TO_END_RERUN=FAIL"
 echo "Partial results/logs remain under: $RUN_ROOT"
 exit 1
fi
printf 'completed_utc=%s\n' "$(date -u +%Y%m%dT%H%M%SZ)" >> "$RUN_ROOT/RUN_METADATA.txt"
echo "END_TO_END_RERUN=PASS"
echo "Reproduced outputs/logs: $RUN_ROOT/results"
echo "Disposable worktree:      $WORK_ROOT"
