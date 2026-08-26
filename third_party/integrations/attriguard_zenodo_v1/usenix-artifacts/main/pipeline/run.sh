#!/usr/bin/env bash
set -euo pipefail

# Fill these in here, or pass them at runtime:
#   SUITE=workspace MODEL=gpt-4.1-mini bash run.sh
CUDA_DEVICES="${CUDA_DEVICES:-}"
SUITE="${SUITE:-}"
LOGDIR="${LOGDIR:-./runs}"
MODEL="${MODEL:-}"
MODEL_ID="${MODEL_ID:-}"
ATTACK="${ATTACK:-}"
DEFENSE="${DEFENSE:-attriguard}"
FORCE_RERUN="${FORCE_RERUN:-0}"
TOOL_DELIMITER="${TOOL_DELIMITER:-}"
SYSTEM_MESSAGE_NAME="${SYSTEM_MESSAGE_NAME:-}"

# Optional task filters. Leave empty to run all tasks in each selected suite.
USER_TASKS="${USER_TASKS:-}"
INJECTION_TASKS="${INJECTION_TASKS:-}"

require_value() {
  local name="$1"
  local value="$2"
  if [[ -z "$value" ]]; then
    echo "ERROR: $name is required."
    exit 1
  fi
}

run_once() {
  local suite="$1"
  local attack="$2"

  cmd=(python my_benchmark.py -s "$suite" --logdir "$LOGDIR" --model "$MODEL")

  if [[ -n "$MODEL_ID" ]]; then
    cmd+=(--model-id "$MODEL_ID")
  fi
  if [[ -n "$attack" ]]; then
    cmd+=(--attack "$attack")
  fi
  if [[ -n "$DEFENSE" ]]; then
    if [[ "$DEFENSE" != "attriguard" ]]; then
      echo "ERROR: unsupported defense '$DEFENSE'. Only attriguard is supported."
      exit 1
    fi
    cmd+=(--defense "$DEFENSE")
  fi
  if [[ -n "$TOOL_DELIMITER" ]]; then
    cmd+=(--tool-delimiter "$TOOL_DELIMITER")
  fi
  if [[ -n "$SYSTEM_MESSAGE_NAME" ]]; then
    cmd+=(--system-message-name "$SYSTEM_MESSAGE_NAME")
  fi
  if [[ "$FORCE_RERUN" == "1" ]]; then
    cmd+=(--force-rerun)
  fi

  for user_task in $USER_TASKS; do
    cmd+=(-ut "$user_task")
  done
  if [[ -n "$attack" ]]; then
    for injection_task in $INJECTION_TASKS; do
      cmd+=(-it "$injection_task")
    done
  fi

  if [[ -n "$CUDA_DEVICES" ]]; then
    echo "CUDA_VISIBLE_DEVICES=$CUDA_DEVICES ${cmd[*]}"
    CUDA_VISIBLE_DEVICES="$CUDA_DEVICES" "${cmd[@]}"
  else
    echo "${cmd[*]}"
    "${cmd[@]}"
  fi
}

require_value "SUITE" "$SUITE"
require_value "MODEL" "$MODEL"

for suite in $SUITE; do
  run_once "$suite" ""
  for attack in $ATTACK; do
    run_once "$suite" "$attack"
  done
done
