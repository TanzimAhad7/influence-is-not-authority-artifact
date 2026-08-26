#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/home/anon_/ratchet/phase0_pilot}"
SRC="$PROJECT_ROOT/P0B3_CAUSALARMOR_LIVE_RUN_v1"
HIST="$PROJECT_ROOT/P0B3_AUTHOR_RUN_HISTORY"
DEST="$HIST/P0B3_ATTEMPT0_16K_TECHNICAL_ABORT_992_OF_1046"
ZIP="$HIST/P0B3_ATTEMPT0_16K_TECHNICAL_ABORT_992_OF_1046.zip"
MANIFEST="$HIST/P0B3_ATTEMPT0_16K_TECHNICAL_ABORT_992_OF_1046_FILES_SHA256.txt"

if [[ ! -d "$SRC" ]]; then
  echo "FATAL: Attempt-0 run directory not found: $SRC" >&2
  exit 2
fi
if [[ -e "$DEST" || -e "$ZIP" ]]; then
  echo "FATAL: Attempt-0 archive destination already exists; refusing overwrite." >&2
  exit 2
fi

# Require the known interrupted-run structure before moving anything.
python - "$SRC" <<'PY'
from pathlib import Path
import json, sys
src=Path(sys.argv[1])
rows=src/"P0B3_SCIENCE_ROWS.jsonl"
errs=src/"P0B3_ERRORS.jsonl"
if not rows.exists() or not errs.exists():
    raise SystemExit("FATAL: missing Attempt-0 science/error ledgers")
r=[json.loads(x) for x in rows.read_text().splitlines() if x.strip()]
e=[json.loads(x) for x in errs.read_text().splitlines() if x.strip()]
if len(r)!=992:
    raise SystemExit(f"FATAL: expected 992 Attempt-0 science rows, got {len(r)}")
if len({x["episode_id"] for x in r})!=992:
    raise SystemExit("FATAL: Attempt-0 duplicate episode IDs")
if len(e)!=1 or e[0].get("episode_id")!="attack:workspace:user_task_6:injection_task_10":
    raise SystemExit("FATAL: Attempt-0 error ledger does not match audited capacity stop")
print("Attempt-0 structure verified: 992 rows + exact episode-993 capacity failure")
PY

mkdir -p "$HIST"
(
  cd "$SRC"
  find . -type f -print0 | sort -z | xargs -0 sha256sum
) > "$MANIFEST"

cat > "$HIST/P0B3_ATTEMPT0_STATUS.md" <<'EOF'
# P0b-3 Attempt 0 — Archived Author-Run Provenance

**Status:** TECHNICAL_ABORT_PRE_DISPOSITION / 992_OF_1046 / PROVENANCE_ONLY

- Completed 992/1046 frozen episodes.
- Next exact frozen episode hit the local Gemma vLLM 16,384-token serving ceiling.
- No PASS/FAIL was imputed for the failed episode.
- No aggregate ASR/BU/UA/calibration disposition from Attempt 0 is used as a paper result.
- The subsequent clean full rerun was selected for artifact cleanliness before an Attempt-0 aggregate disposition was computed or used.
- This archive must never be deleted or silently substituted for the clean primary run.
EOF

mv "$SRC" "$DEST"

(
  cd "$HIST"
  zip -qr "$(basename "$ZIP")" "$(basename "$DEST")" "$(basename "$MANIFEST")" "P0B3_ATTEMPT0_STATUS.md"
)

sha256sum "$ZIP" | tee "$ZIP.sha256"

echo "P0b-3 Attempt 0 ARCHIVED"
echo "history_dir=$DEST"
echo "archive_zip=$ZIP"
echo "canonical live-run path is now free for Attempt 1"
