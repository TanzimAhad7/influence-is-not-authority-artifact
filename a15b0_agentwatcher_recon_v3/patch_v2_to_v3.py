#!/usr/bin/env python3
"""
Outcome-independent runtime repair:
v2 -> v3 AgentWatcher reconstructed monitor completion ceiling.

This patch changes ONLY src/defenses/monitor_llm_module/core.py.
It refuses to patch any core.py whose SHA-256 is not the frozen v2 hash.
"""

from pathlib import Path
import hashlib
import json
import shutil
import sys
import time

EXPECTED_V2 = "10d423221e57a3660feaa9e6f6ceec94721ab1e75ce860d114359585362125da"
NEW_CORE = Path(__file__).resolve().parent / "core.py"

if len(sys.argv) != 2:
    raise SystemExit("usage: patch_v2_to_v3.py /path/to/AgentWatcher_armc_runtime_v1")

repo = Path(sys.argv[1]).expanduser().resolve()
dst = repo / "src/defenses/monitor_llm_module/core.py"

if not dst.exists():
    raise SystemExit(f"Missing reconstructed core.py: {dst}")

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

before = sha(dst)
if before != EXPECTED_V2:
    raise SystemExit(
        "ABORT: current core.py is not the frozen v2 core.\n"
        f"expected={EXPECTED_V2}\nactual={before}"
    )

stamp = time.strftime("%Y%m%dT%H%M%S")
backup = repo / f"A15B0_RECON_V3_BACKUP_{stamp}"
backup.mkdir()
shutil.copy2(dst, backup / "core.py")

shutil.copy2(NEW_CORE, dst)
after = sha(dst)

manifest = {
    "schema": "A15B0_AGENTWATCHER_RECONSTRUCTION_v3_COMPLETION_SAFE",
    "scientific_design_changed": False,
    "reason": "prevent truncation of monitor reasoning before final verdict",
    "old_core_sha256": before,
    "new_core_sha256": after,
    "completion_ceiling": 4096,
    "parser_changed": False,
    "prompt_changed": False,
    "model_changed": False,
    "temperature_changed": False,
    "backup": str(backup / "core.py"),
}
manifest_path = repo / "A15B0_AGENTWATCHER_RECONSTRUCTION_v3_COMPLETION_SAFE.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")

print("RECONSTRUCTION V3 COMPLETION PATCH PASS")
print("old core:", before)
print("new core:", after)
print("backup:", backup / "core.py")
print("manifest:", manifest_path)
