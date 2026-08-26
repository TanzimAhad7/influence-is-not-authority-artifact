#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: bash setup_asb_attriguard.sh /path/to/ASB"
}

if [ "$#" -ne 1 ]; then
  usage
  exit 2
fi

ASB_ROOT="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OVERLAY_DIR="$SCRIPT_DIR/overlay"

if [ ! -d "$ASB_ROOT" ]; then
  echo "ASB path does not exist: $ASB_ROOT" >&2
  exit 1
fi

if [ ! -d "$OVERLAY_DIR" ]; then
  echo "Overlay directory not found: $OVERLAY_DIR" >&2
  exit 1
fi

required_files=(
  "main_attacker.py"
  "pyopenagi/agents/react_agent_attack.py"
  "pyopenagi/tools/simulated_tool.py"
)

for rel in "${required_files[@]}"; do
  if [ ! -f "$ASB_ROOT/$rel" ]; then
    echo "This does not look like the expected ASB repository; missing $rel" >&2
    exit 1
  fi
done

backup_dir="$ASB_ROOT/.attriguard_backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$backup_dir"

while IFS= read -r -d '' src; do
  rel="${src#"$OVERLAY_DIR"/}"
  dst="$ASB_ROOT/$rel"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ]; then
    mkdir -p "$backup_dir/$(dirname "$rel")"
    cp "$dst" "$backup_dir/$rel"
  fi
  cp "$src" "$dst"
done < <(find "$OVERLAY_DIR" -type f -print0)

echo "AttriGuard ASB overlay installed into: $ASB_ROOT"
echo "Backups of replaced files are in: $backup_dir"
