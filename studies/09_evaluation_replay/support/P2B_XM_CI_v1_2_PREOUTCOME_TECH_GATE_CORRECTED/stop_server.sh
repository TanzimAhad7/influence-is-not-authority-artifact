#!/usr/bin/env bash
set -euo pipefail
RUN_DIR=${1:?usage: stop_server.sh <run-dir>}
PIDFILE="$RUN_DIR/vllm_server.pid"
if [[ ! -f "$PIDFILE" ]]; then
  echo "No pid file: $PIDFILE"
  exit 0
fi
PID=$(cat "$PIDFILE")
if [[ -n "$PID" && -e "/proc/$PID" ]]; then
  kill "$PID" || true
  for _ in $(seq 1 30); do
    [[ ! -e "/proc/$PID" ]] && break
    sleep 1
  done
  [[ -e "/proc/$PID" ]] && kill -9 "$PID" || true
fi
echo "Stopped PID $PID"
