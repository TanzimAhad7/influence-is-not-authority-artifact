#!/usr/bin/env bash
set -euo pipefail

# Stop processes started by the AttriGuard adaptive-attack pipeline.
# The released entry point runs `python -m my_benchmark -ml main_attack`,
# which may then spawn OpenEvolve and AgentDojo evaluator subprocesses.

PATTERN='openevolve_for_agentdojo|python[0-9.]* -m my_benchmark .* -ml main_attack|python[0-9.]* -m openevolve_runner|openevolve_runner\.py|agentdojo_evaluator\.py|main_attack\.py'

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

contains_pid() {
  local needle="$1"
  shift || true
  local pid
  for pid in "$@"; do
    if [[ "$pid" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

add_pid() {
  local pid="$1"
  if [[ -z "$pid" || "$pid" == "$$" ]]; then
    return
  fi
  if ! contains_pid "$pid" "${TARGET_PIDS[@]:-}"; then
    TARGET_PIDS+=("$pid")
  fi
}

load_process_table() {
  PIDS=()
  PPIDS=()
  COMMANDS=()

  while read -r pid ppid command; do
    [[ -z "${pid:-}" ]] && continue
    PIDS+=("$pid")
    PPIDS+=("$ppid")
    COMMANDS+=("${command:-}")
  done < <(ps -axo pid=,ppid=,command=)
}

add_children_recursive() {
  local parent="$1"
  local i child
  for i in "${!PIDS[@]}"; do
    if [[ "${PPIDS[$i]}" == "$parent" ]]; then
      child="${PIDS[$i]}"
      add_pid "$child"
      add_children_recursive "$child"
    fi
  done
}

load_process_table

TARGET_PIDS=()
for i in "${!PIDS[@]}"; do
  if [[ "${COMMANDS[$i]}" =~ $PATTERN ]]; then
    add_pid "${PIDS[$i]}"
  fi
done

for pid in "${TARGET_PIDS[@]:-}"; do
  add_children_recursive "$pid"
done

if [[ "${#TARGET_PIDS[@]}" -eq 0 ]]; then
  echo "No AttriGuard adaptive-attack processes found."
  exit 0
fi

echo "Target processes:"
for pid in "${TARGET_PIDS[@]}"; do
  ps -p "$pid" -o pid=,ppid=,command= || true
done

if [[ "$DRY_RUN" == "1" ]]; then
  echo "Dry run only. No processes were killed."
  exit 0
fi

echo "Sending SIGTERM..."
kill "${TARGET_PIDS[@]}" 2>/dev/null || true
sleep 3

load_process_table
STILL_RUNNING=()
for pid in "${TARGET_PIDS[@]}"; do
  if contains_pid "$pid" "${PIDS[@]}"; then
    STILL_RUNNING+=("$pid")
  fi
done

if [[ "${#STILL_RUNNING[@]}" -gt 0 ]]; then
  echo "Still running after SIGTERM; sending SIGKILL:"
  printf '  %s\n' "${STILL_RUNNING[@]}"
  kill -9 "${STILL_RUNNING[@]}" 2>/dev/null || true
else
  echo "All target processes stopped."
fi
