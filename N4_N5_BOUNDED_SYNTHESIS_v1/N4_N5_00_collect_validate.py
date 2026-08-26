#!/usr/bin/env python3
from pathlib import Path
import json, datetime
from n4n5_common import RUN_DIR, validate_and_collect

evidence, manifest = validate_and_collect()
RUN_DIR.mkdir(exist_ok=True)

manifest["collected_at_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
(RUN_DIR/"N4_N5_INPUT_MANIFEST.json").write_text(json.dumps(manifest, indent=2, sort_keys=True)+"\n")
(RUN_DIR/"N4_N5_EVIDENCE_MATRIX.json").write_text(json.dumps(evidence, indent=2, sort_keys=True)+"\n")

print("[N4/N5-00] INPUT VALIDATION PASS")
print("[N4/N5-00] closed evidence: A14 + R2A + N3 + B1 + A15a + AgentWatcher + AttriGuard + P2 + P0b-3 + P0b-3-ACT")
print("[N4/N5-00] no model/network calls; no new endpoint; no combined scalar")
print("[N4/N5-00] wrote N4_N5_RUN_v1/N4_N5_INPUT_MANIFEST.json")
print("[N4/N5-00] wrote N4_N5_RUN_v1/N4_N5_EVIDENCE_MATRIX.json")
