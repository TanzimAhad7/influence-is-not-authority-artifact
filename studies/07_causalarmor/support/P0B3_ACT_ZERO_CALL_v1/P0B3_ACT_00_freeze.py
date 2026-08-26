#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from p0b3_act_common import (
    EXPECTED_INPUT_REL,
    EXPECTED_INPUT_SHA256,
    EXPECTED_TOTAL_EVENTS,
    SCHEMA,
    read_jsonl,
    sha256_file,
    source_hashes,
    validate_events,
    write_json,
)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Freeze P0b-3-ACT code, exact Attempt-1 input hash, and benign/attack denominators. ZERO MODEL CALLS."
    )
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--output-dir", default="P0B3_ACT_RUN_v1")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    package_dir = Path(__file__).resolve().parent
    input_path = root / EXPECTED_INPUT_REL
    out_dir = root / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    if not input_path.is_file():
        raise SystemExit(f"FATAL: expected frozen Attempt-1 input not found: {input_path}")

    observed_sha = sha256_file(input_path)
    if observed_sha != EXPECTED_INPUT_SHA256:
        raise SystemExit(
            "FATAL: P0B3_DEFENSE_EVENTS.jsonl hash mismatch\n"
            f" expected={EXPECTED_INPUT_SHA256}\n observed={observed_sha}"
        )

    rows = read_jsonl(input_path)
    # Freeze stage intentionally does NOT aggregate activation outcomes.
    validation = validate_events(rows, aggregate_flags=False)
    if validation["total_events"] != EXPECTED_TOTAL_EVENTS:
        raise SystemExit("FATAL: unexpected event total")

    freeze = {
        "schema": SCHEMA,
        "stage": "FREEZE",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scientific_model_calls": 0,
        "analysis_class": "POST_HOC_DESCRIPTIVE_ZERO_CALL",
        "input": {
            "relative_path": str(EXPECTED_INPUT_REL),
            "sha256": observed_sha,
            "rows": validation["total_events"],
            "event_identity": "episode_id + attempt_id + decision_index",
            "unique_event_identities": validation["unique_event_identities"],
        },
        "frozen_denominators": validation["denominators"],
        "frozen_total_privileged_decisions": validation["total_events"],
        "activation_definition": "ACTION_ONLY := primary_any_flag; validated identical to intervened on every event",
        "reporting_lock": {
            "primary_outputs": [
                "benign ACTION_ONLY flagged privileged decisions / benign privileged decisions",
                "attack ACTION_ONLY flagged privileged decisions / attack privileged decisions",
            ],
            "additional_descriptive": "attack_minus_benign_percentage_points",
            "no_ci_no_pvalue": True,
            "report_regardless_of_shape": True,
            "no_threshold_tuning": True,
            "no_population_edits": True,
        },
        "package_source_sha256": source_hashes(package_dir),
    }

    freeze_path = out_dir / "P0B3_ACT_FREEZE.json"
    if freeze_path.exists():
        old = json.loads(freeze_path.read_text(encoding="utf-8"))
        # Allow verification-only rerun if immutable fields agree; timestamp is ignored.
        for key in (
            "schema", "stage", "input", "frozen_denominators",
            "frozen_total_privileged_decisions", "activation_definition",
            "reporting_lock", "package_source_sha256"
        ):
            if old.get(key) != freeze.get(key):
                raise SystemExit(f"FATAL: existing freeze differs at {key}; do not overwrite")
        print("[P0B3-ACT-00] EXISTING FREEZE VERIFIED")
        print(f"[P0B3-ACT-00] input_sha256={observed_sha}")
        print(f"[P0B3-ACT-00] denominators={validation['denominators']} total={validation['total_events']}")
        print("[P0B3-ACT-00] NO activation outcomes aggregated; ZERO model calls")
        return 0

    write_json(freeze_path, freeze)
    freeze_sha = sha256_file(freeze_path)
    md = out_dir / "P0B3_ACT_FREEZE.md"
    md.write_text(
        "# P0b-3-ACT pre-analysis freeze\n\n"
        "- analysis: zero-model-call post-hoc descriptive split\n"
        f"- input SHA-256: `{observed_sha}`\n"
        f"- total privileged decisions: `{validation['total_events']}`\n"
        f"- frozen denominators: `{validation['denominators']}`\n"
        "- activation endpoint: `primary_any_flag` (validated identical to `intervened`)\n"
        "- primary outputs: benign rate and attack rate only; report regardless of shape\n"
        "- no CI/p-value, threshold tuning, population edits, or model calls\n"
        f"- freeze JSON SHA-256: `{freeze_sha}`\n",
        encoding="utf-8",
    )

    print("[P0B3-ACT-00] FREEZE PASS")
    print(f"[P0B3-ACT-00] input_sha256={observed_sha}")
    print(f"[P0B3-ACT-00] denominators={validation['denominators']} total={validation['total_events']}")
    print(f"[P0B3-ACT-00] freeze_sha256={freeze_sha}")
    print("[P0B3-ACT-00] NO activation outcomes aggregated; ZERO model calls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
