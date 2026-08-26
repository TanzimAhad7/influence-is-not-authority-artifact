#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from pathlib import Path

from p0b3_act_common import (
    EXPECTED_INPUT_REL,
    EXPECTED_INPUT_SHA256,
    EXPECTED_OVERALL_PRIMARY_FLAGGED,
    EXPECTED_TOTAL_EVENTS,
    SCHEMA,
    load_freeze,
    read_jsonl,
    sha256_file,
    source_hashes,
    validate_events,
    write_json,
)


def pct(k: int, n: int) -> float:
    return 100.0 * k / n if n else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run frozen P0b-3-ACT benign-vs-attack ACTION_ONLY activation split. ZERO MODEL CALLS."
    )
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--output-dir", default="P0B3_ACT_RUN_v1")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    package_dir = Path(__file__).resolve().parent
    out_dir = root / args.output_dir
    freeze_path = out_dir / "P0B3_ACT_FREEZE.json"
    input_path = root / EXPECTED_INPUT_REL

    if not freeze_path.is_file():
        raise SystemExit("FATAL: pre-analysis freeze missing; run P0B3_ACT_00_freeze.py first")
    freeze = load_freeze(freeze_path)

    observed_sources = source_hashes(package_dir)
    if observed_sources != freeze.get("package_source_sha256"):
        raise SystemExit("FATAL: analysis package changed after freeze")

    observed_input_sha = sha256_file(input_path)
    if observed_input_sha != EXPECTED_INPUT_SHA256 or observed_input_sha != freeze["input"]["sha256"]:
        raise SystemExit("FATAL: frozen Attempt-1 defense-event input changed after freeze")

    rows = read_jsonl(input_path)
    validation = validate_events(rows, aggregate_flags=True)
    if validation["denominators"] != freeze["frozen_denominators"]:
        raise SystemExit("FATAL: denominators changed after freeze")
    if validation["total_events"] != EXPECTED_TOTAL_EVENTS:
        raise SystemExit("FATAL: total event count mismatch")

    benign_n = validation["denominators"]["benign"]
    attack_n = validation["denominators"]["attack"]
    benign_k = validation["flagged"]["benign"]
    attack_k = validation["flagged"]["attack"]
    overall_k = benign_k + attack_k

    if overall_k != EXPECTED_OVERALL_PRIMARY_FLAGGED:
        raise SystemExit(
            f"FATAL: split does not reconcile to frozen overall ACTION_ONLY count: {overall_k} != {EXPECTED_OVERALL_PRIMARY_FLAGGED}"
        )

    benign_pct = pct(benign_k, benign_n)
    attack_pct = pct(attack_k, attack_n)
    overall_pct = pct(overall_k, EXPECTED_TOTAL_EVENTS)
    diff_pp = attack_pct - benign_pct

    result = {
        "schema": SCHEMA,
        "stage": "RESULT",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE_ZERO_CALL_POSTHOC_DESCRIPTIVE",
        "scientific_model_calls": 0,
        "input_sha256": observed_input_sha,
        "freeze_sha256": sha256_file(freeze_path),
        "endpoint": "ACTION_ONLY := primary_any_flag",
        "benign": {
            "flagged_privileged_decisions": benign_k,
            "privileged_decisions": benign_n,
            "activation_percent": benign_pct,
        },
        "attack": {
            "flagged_privileged_decisions": attack_k,
            "privileged_decisions": attack_n,
            "activation_percent": attack_pct,
        },
        "attack_minus_benign_percentage_points": diff_pp,
        "overall_reconciliation": {
            "flagged_privileged_decisions": overall_k,
            "privileged_decisions": EXPECTED_TOTAL_EVENTS,
            "activation_percent": overall_pct,
            "expected_frozen_overall_flagged": EXPECTED_OVERALL_PRIMARY_FLAGGED,
            "pass": overall_k == EXPECTED_OVERALL_PRIMARY_FLAGGED,
        },
        "interpretation_lock": [
            "post-hoc descriptive triangulation only",
            "not a prospective novelty endpoint",
            "not an ASR or utility estimate",
            "no causal inference from benign-vs-attack difference",
            "report regardless of direction or magnitude",
        ],
    }

    result_path = out_dir / "P0B3_ACT_RESULT.json"
    write_json(result_path, result)

    csv_path = out_dir / "P0B3_ACT_SPLIT.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["population", "flagged_privileged_decisions", "privileged_decisions", "activation_percent"])
        w.writerow(["benign", benign_k, benign_n, f"{benign_pct:.12f}"])
        w.writerow(["attack", attack_k, attack_n, f"{attack_pct:.12f}"])
        w.writerow(["overall", overall_k, EXPECTED_TOTAL_EVENTS, f"{overall_pct:.12f}"])

    report_path = out_dir / "P0B3_ACT_REPORT.md"
    report_path.write_text(
        "# P0b-3-ACT zero-call descriptive result\n\n"
        f"- benign ACTION_ONLY activation: **{benign_k}/{benign_n} = {benign_pct:.2f}%**\n"
        f"- attack ACTION_ONLY activation: **{attack_k}/{attack_n} = {attack_pct:.2f}%**\n"
        f"- descriptive attack − benign difference: **{diff_pp:+.2f} pp**\n"
        f"- overall reconciliation: **{overall_k}/{EXPECTED_TOTAL_EVENTS} = {overall_pct:.2f}%** (PASS)\n\n"
        "Interpretation lock: post-hoc descriptive triangulation only; no causal inference, no ASR/utility claim, "
        "no threshold tuning, and no novelty credit by itself.\n",
        encoding="utf-8",
    )

    artifact_names = [
        "P0B3_ACT_FREEZE.json", "P0B3_ACT_FREEZE.md",
        "P0B3_ACT_RESULT.json", "P0B3_ACT_SPLIT.csv", "P0B3_ACT_REPORT.md",
    ]
    manifest_path = out_dir / "FINAL_ARTIFACT_SHA256.txt"
    with manifest_path.open("w", encoding="utf-8") as f:
        for name in artifact_names:
            p = out_dir / name
            f.write(f"{sha256_file(p)}  {name}\n")

    print("[P0B3-ACT-01] COMPLETE / ZERO MODEL CALLS")
    print(f"[P0B3-ACT-01] benign={benign_k}/{benign_n} ({benign_pct:.2f}%)")
    print(f"[P0B3-ACT-01] attack={attack_k}/{attack_n} ({attack_pct:.2f}%)")
    print(f"[P0B3-ACT-01] attack_minus_benign={diff_pp:+.2f} pp")
    print(f"[P0B3-ACT-01] overall_reconciliation={overall_k}/{EXPECTED_TOTAL_EVENTS} ({overall_pct:.2f}%) PASS")
    print(f"[P0B3-ACT-01] result_sha256={sha256_file(result_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
