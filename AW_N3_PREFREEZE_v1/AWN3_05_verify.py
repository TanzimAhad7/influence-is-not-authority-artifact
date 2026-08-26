#!/usr/bin/env python3
"""Independent deterministic integrity/science verifier for AW-N3-v1 outputs."""
from __future__ import annotations

import argparse
import collections
import math
from pathlib import Path

import numpy as np

from awn3_common import *


def ci(vals, seed):
    arr = np.asarray(vals, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(arr), size=(BOOTSTRAP_B, len(arr)))
    means = arr[idx].mean(axis=1)
    return [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))]


def close(a, b, tol=1e-12):
    return abs(float(a) - float(b)) <= tol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--run-dir", default="AW_N3_AUTHOR_v1")
    args = ap.parse_args()

    paths = project_paths(Path(args.project_root), Path(args.run_dir))
    root, out = paths["root"], paths["run"]
    errors = []

    try:
        validate_parent_sources(root)
    except Exception as e:
        errors.append(f"parent/source validation failed: {e}")

    needed = [
        "AWN3_PREFREEZE_BUILD_SUMMARY.json",
        "AWN3_ALL_192_INPUTS.jsonl",
        "AWN3_EXECUTION_INPUTS.jsonl",
        "AWN3_SHAM_ECHO_STATIC_IDENTITY_AUDIT.jsonl",
        "AWN3_FREEZE.json",
        "AWN3_FREEZE_COMPLETE.json",
        "AWN3_PREFLIGHT.json",
        "AWN3_SCIENCE_UNIQUE_OUTPUTS.jsonl",
        "AWN3_SCIENCE_RUN_COMPLETE.json",
        "AWN3_MAPPED_OUTPUTS.jsonl",
        "AWN3_BASE_EFFECTS.csv",
        "AWN3_RESULTS.json",
        "AWN3_REPORT.md",
        "AWN3_MANIFEST.json",
        "AWN3_ANALYSIS_COMPLETE.json",
    ]
    for n in needed:
        if not (out / n).is_file():
            errors.append(f"missing {n}")
    if errors:
        raise SystemExit("\n".join(errors))

    freeze = read_json(out / "AWN3_FREEZE.json")
    summary = read_json(out / "AWN3_PREFREEZE_BUILD_SUMMARY.json")
    preflight = read_json(out / "AWN3_PREFLIGHT.json")
    run_complete = read_json(out / "AWN3_SCIENCE_RUN_COMPLETE.json")
    results = read_json(out / "AWN3_RESULTS.json")
    manifest = read_json(out / "AWN3_MANIFEST.json")

    # Freeze and package-source immutability.
    core = dict(freeze)
    frozen_hash = core.pop("freeze_sha256", None)
    core.pop("frozen_at_utc", None)
    recomputed_freeze = stable_hash(core)
    if frozen_hash != recomputed_freeze:
        errors.append(f"freeze self-hash mismatch {frozen_hash} != {recomputed_freeze}")
    actual_pkg = package_source_hashes()
    if freeze.get("package_source_hashes") != actual_pkg:
        errors.append("package source hashes differ from pre-outcome freeze")

    for name, expected in freeze.get("input_hashes", {}).items():
        p = out / name
        if not p.is_file() or sha256_file(p) != expected:
            errors.append(f"frozen input drift: {name}")

    if preflight.get("freeze_sha256") != frozen_hash:
        errors.append("preflight/freeze mismatch")
    if run_complete.get("freeze_sha256") != frozen_hash:
        errors.append("science run/freeze mismatch")
    if results.get("freeze_sha256") != frozen_hash:
        errors.append("results/freeze mismatch")

    inputs = read_jsonl(out / "AWN3_ALL_192_INPUTS.jsonl")
    exec_inputs = read_jsonl(out / "AWN3_EXECUTION_INPUTS.jsonl")
    sci = read_jsonl(out / "AWN3_SCIENCE_UNIQUE_OUTPUTS.jsonl")
    mapped = read_jsonl(out / "AWN3_MAPPED_OUTPUTS.jsonl")
    identity = read_jsonl(out / "AWN3_SHAM_ECHO_STATIC_IDENTITY_AUDIT.jsonl")
    if [len(inputs), len(exec_inputs), len(sci), len(mapped), len(identity)] != [192, 96, 96, 192, 96]:
        errors.append(
            f"census mismatch inputs/exec/sci/mapped/identity={len(inputs)}/{len(exec_inputs)}/{len(sci)}/{len(mapped)}/{len(identity)}"
        )
    if sum(bool(x.get("static_input_identical")) for x in identity) != 96:
        errors.append("SHAM/ECHO identity audit is not 96/96")

    exec_hashes = [r["agentwatcher_static_input_sha256"] for r in exec_inputs]
    sci_hashes = [r["agentwatcher_static_input_sha256"] for r in sci]
    if exec_hashes != sorted(exec_hashes) or len(set(exec_hashes)) != 96:
        errors.append("execution input order/uniqueness mismatch")
    if sci_hashes != exec_hashes:
        errors.append("science outputs are not in exact frozen execution-hash order")
    if sha256_file(out / "AWN3_SCIENCE_UNIQUE_OUTPUTS.jsonl") != run_complete.get("science_output_sha256"):
        errors.append("science output hash does not match run-complete")

    by_hash = {r["agentwatcher_static_input_sha256"]: r for r in sci}
    parse_ok = sum(bool(r.get("monitor_parse_ok")) for r in sci)
    if parse_ok != run_complete.get("n_parse_ok"):
        errors.append("parse census mismatch")

    # Independently reconstruct all 192 mapped decisions from frozen static hashes.
    rebuilt = []
    for r in inputs:
        z = by_hash.get(r["agentwatcher_static_input_sha256"])
        if z is None:
            errors.append(f"missing mapped output for {r['unit_id']}")
            continue
        rebuilt.append((
            r["unit_id"], r["base_id"], r["family"], r["descendant"], r["directive_arm"], r["action_role"],
            z.get("detect_flag"), bool(z.get("monitor_parse_ok")),
        ))
    mapped_tuples = [(
        r["unit_id"], r["base_id"], r["family"], r["descendant"], r["directive_arm"], r["action_role"],
        r.get("detect_flag"), bool(r.get("monitor_parse_ok")),
    ) for r in mapped]
    if rebuilt != mapped_tuples:
        errors.append("mapped 192-row output does not reproduce exactly from static-hash mapping")

    technical_valid = parse_ok == 96
    if bool(results.get("technical_validity", {}).get("valid")) != technical_valid:
        errors.append("technical-validity status mismatch")

    if technical_valid:
        g = collections.defaultdict(dict)
        for r in mapped:
            g[(r["base_id"], r["directive_arm"], r["action_role"])][r["descendant"]] = int(bool(r["detect_flag"]))
        bases = sorted({r["base_id"] for r in mapped})
        if len(bases) != 24:
            errors.append(f"base count mismatch {len(bases)}")
        G, A, C, I = [], [], [], []
        for base in bases:
            def m(d, a):
                dd = g[(base, d, a)]
                if set(dd) != {"SHAM", "ECHO"}:
                    raise RuntimeError(f"bad descendant map {base} {d}/{a}")
                return 0.5 * (dd["SHAM"] + dd["ECHO"])
            aa, al, ca, cl = m("ALIGNED","AUTH"), m("ALIGNED","ALT"), m("CONFLICT","AUTH"), m("CONFLICT","ALT")
            G.append(cl-aa)
            A.append(0.5*((al-aa)+(cl-ca)))
            C.append(0.5*((ca-aa)+(cl-al)))
            I.append((cl-ca)-(al-aa))
        gm = float(np.mean(G)); gci = ci(G, BOOTSTRAP_SEED)
        if gci[0] > 0: cat = "POSITIVE_SEPARATION"
        elif gci[1] < 0: cat = "ADVERSE_SEPARATION"
        else: cat = "NULL_COMPATIBLE"
        p = results["primary"]
        if p.get("category") != cat or not close(p.get("mean_G_AW"), gm):
            errors.append("primary category/mean does not independently reproduce")
        if not (close(p["ci95"][0], gci[0]) and close(p["ci95"][1], gci[1])):
            errors.append("primary bootstrap CI does not independently reproduce")
        signs = {"positive":sum(x>0 for x in G),"zero":sum(x==0 for x in G),"negative":sum(x<0 for x in G)}
        if p.get("sign_counts") != signs:
            errors.append("primary sign counts do not reproduce")
        sec = results["secondary_action_control"]
        checks = [
            ("ACTION_ROLE_EFFECT", A, BOOTSTRAP_SEED+1),
            ("DIRECTIVE_CONFLICT_EFFECT", C, BOOTSTRAP_SEED+2),
            ("ACTION_X_DIRECTIVE_INTERACTION", I, BOOTSTRAP_SEED+3),
        ]
        for name, vals, seed in checks:
            mm = float(np.mean(vals)); cc = ci(vals, seed)
            got = sec[name]
            if not close(got["mean"], mm) or not close(got["ci95"][0], cc[0]) or not close(got["ci95"][1], cc[1]):
                errors.append(f"secondary {name} does not reproduce")

    # Manifest verifies every pre-manifest file it claims.
    for name, expected in manifest.get("files", {}).items():
        p = out / name
        if not p.is_file() or sha256_file(p) != expected:
            errors.append(f"manifest file hash mismatch: {name}")
    if manifest.get("package_source_hashes") != actual_pkg:
        errors.append("manifest package-source hashes mismatch")

    report = {
        "schema": "AWN3_VERIFY_REPORT_V1_2026-08-19",
        "verified_at_utc": now_utc(),
        "status": "INTEGRITY_PASS" if not errors else "INTEGRITY_FAIL",
        "errors": errors,
        "freeze_sha256": frozen_hash,
        "science_output_sha256": sha256_file(out / "AWN3_SCIENCE_UNIQUE_OUTPUTS.jsonl"),
        "results_sha256": sha256_file(out / "AWN3_RESULTS.json"),
        "manifest_sha256": sha256_file(out / "AWN3_MANIFEST.json"),
        "census": {"inputs":len(inputs),"execution":len(exec_inputs),"science":len(sci),"mapped":len(mapped),"bases":24},
        "parse_ok": parse_ok,
        "independent_primary_rederivation": technical_valid,
    }
    write_json(out / "AWN3_VERIFY_REPORT.json", report)
    print(f"[AWN3-05] {report['status']}")
    print(f"[AWN3-05] verify_report={out / 'AWN3_VERIFY_REPORT.json'}")
    print(f"[AWN3-05] verify_report_sha256={sha256_file(out / 'AWN3_VERIFY_REPORT.json')}")
    if errors:
        for e in errors:
            print(f"[AWN3-05] ERROR: {e}")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
