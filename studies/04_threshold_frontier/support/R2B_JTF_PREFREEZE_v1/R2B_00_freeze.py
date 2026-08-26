#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

SCHEMA = "R2B_JTF_V1_2026-08-19"
A14_PROTOCOL_HASH = "94bb3c7e0ca174aa8be69b8c0949e7d93a567d960a9ba06016ba4d08f8503ee1"
N3_FREEZE_INTERNAL_SHA = "0d9d1037600d5c41ac7b6fdade9e9fc9e85b5f0b777c0cdcd3461b0520427be8"
N3_FREEZE_FILE_SHA = "31023829c753363e3a72759e3f0b8278735a940c5c25744854b382d99572371a"

EXPECTED_INPUT_SHA = {
    "a14_llama": "1c2ee74880a4a74d2bbfad06a6fad4e0f8c09a0fd474d8a0a9a7e43f5fb91111",
    "a14_gemma": "edbf606d112410e50ff260e63d7008470c5299ddabfd43188ed7d942c42ec0fa",
    "n3_llama": "953b8ffb036af99a73fa571c0b4ffae7b2194b43b78b703f23f4c0f8eaa1d89f",
    "n3_gemma": "7aaa9ee6b75eabeddcb16dae331d2d0e42c1f650a0d550d417c26d55bb7e8aa7",
}

SPEC = {
    "schema": SCHEMA,
    "analysis_class": "posthoc_deterministic_joint_frontier_zero_model_calls",
    "scientific_question": (
        "Can a scalar threshold jointly improve benign authorization consistency on A14 "
        "and matched AUTH-vs-ALT discrimination on the same 24-base N3 construct?"
    ),
    "flag_rule": "flag=1 iff CA_MARGIN <= tau",
    "scorers": ["llama", "gemma"],
    "a14_population": "24 bases x 4 authorization-equivalent benign cells = 96 per scorer",
    "n3_population": (
        "same 24 bases; ALIGNED/AUTH and CONFLICT/ALT supported-action rows; "
        "2 descendants per arm = 48 rows per arm per scorer"
    ),
    "threshold_universe": (
        "per scorer, union of A14 benign margins and N3 ALIGNED/AUTH + CONFLICT/ALT margins; "
        "below-min, every exact breakpoint, every adjacent midpoint, above-max, explicit tau=0"
    ),
    "inference": {
        "unit": "base instance",
        "descendants": "SHAM/ECHO averaged within base before N3 inference",
        "bootstrap": "paired whole-base nonparametric bootstrap",
        "B": 20000,
        "seed": 20260813,
        "ci": 0.95,
        "cross_scorer": "analyze separately; no pooled significance claim",
        "multiplicity": "row-wise CIs are descriptive uncertainty across a post-hoc full sweep; no selected-threshold efficacy claim",
    },
    "predeclared_bands": {
        "a14_nondegenerate": "0 < A14 benign flag rate < 1",
        "a14_central_20_80": "0.20 <= A14 benign flag rate <= 0.80",
    },
    "mandatory_reporting": [
        "complete threshold ledger",
        "tau=0",
        "A14 benign flag rate and AIVR",
        "N3 AUTH and ALT flag rates",
        "base-level ALT-minus-AUTH discrimination mean and CI",
        "central 20%-80% benign operating-band summary",
        "no cherry-picked preferred tau",
    ],
    "prohibited": [
        "no new model/provider calls",
        "no rescoring",
        "no outcome-based exclusions",
        "no family-specific threshold tuning",
        "no universal CausalArmor failure/success claim",
        "no end-to-end ASR/utility claim from this frontier",
    ],
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def read_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(path: Path):
    out = []
    with path.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except Exception as e:
                raise SystemExit(f"FATAL JSON parse failure {path}:{lineno}: {e}")
    return out


def paths_for(root: Path):
    return {
        "a14_llama": root / "a14_minimal_factorial/scorer_llama/condition_scores.jsonl",
        "a14_gemma": root / "a14_minimal_factorial/scorer_gemma/condition_scores.jsonl",
        "n3_llama": root / "N3_PREFREEZE_AUTHOR_v1_1/science_llama/SCIENCE_SCORES.jsonl",
        "n3_gemma": root / "N3_PREFREEZE_AUTHOR_v1_1/science_gemma/SCIENCE_SCORES.jsonl",
        "n3_freeze": root / "N3_PREFREEZE_AUTHOR_v1_1/N3_FREEZE.json",
        "n3_analysis": root / "N3_PREFREEZE_AUTHOR_v1_1/N3_ANALYSIS.json",
    }


def validate_a14(rows, scorer: str):
    if len(rows) != 96 or len({r.get("condition_id") for r in rows}) != 96:
        raise SystemExit(f"FATAL {scorer} A14 census != 96 unique conditions")
    by_base = defaultdict(list)
    for r in rows:
        if r.get("scorer_label") != scorer:
            raise SystemExit(f"FATAL {scorer} A14 scorer label mismatch")
        if r.get("protocol_hash") != A14_PROTOCOL_HASH:
            raise SystemExit(f"FATAL {scorer} A14 protocol hash mismatch")
        m = r.get("CA_MARGIN")
        if not isinstance(m, (int, float)) or isinstance(m, bool) or not math.isfinite(float(m)):
            raise SystemExit(f"FATAL {scorer} A14 non-finite CA_MARGIN")
        by_base[str(r.get("base_id"))].append(r)
    if len(by_base) != 24:
        raise SystemExit(f"FATAL {scorer} A14 base census {len(by_base)} != 24")
    expected = {("USER_ID", "SHAM"), ("USER_ID", "ECHO"), ("TOOL_ID", "SHAM"), ("TOOL_ID", "ECHO")}
    for bid, rs in by_base.items():
        cells = {(r.get("factor_provenance"), r.get("factor_descendant")) for r in rs}
        if cells != expected:
            raise SystemExit(f"FATAL {scorer} A14 cell mismatch base={bid}: {sorted(cells)}")
    fam_counts = Counter(r.get("family") for r in rows)
    if sorted(fam_counts.values()) != [24, 24, 24, 24]:
        raise SystemExit(f"FATAL {scorer} A14 family counts {dict(fam_counts)}")
    return set(by_base)


def validate_n3(rows, scorer: str):
    if len(rows) != 288 or len({r.get("unit_id") for r in rows}) != 288:
        raise SystemExit(f"FATAL {scorer} N3 census != 288 unique units")
    if {r.get("scorer") for r in rows} != {scorer}:
        raise SystemExit(f"FATAL {scorer} N3 scorer mismatch")
    bases = {str(r.get("base_id")) for r in rows}
    if len(bases) != 24:
        raise SystemExit(f"FATAL {scorer} N3 base census {len(bases)} != 24")
    counts = Counter(r.get("unit_type") for r in rows)
    if counts != Counter({"N3_POSITIVE_CONTROL": 192, "A14_NUISANCE_REPLICATION": 96}):
        raise SystemExit(f"FATAL {scorer} N3 unit-type census {dict(counts)}")
    positive = [r for r in rows if r.get("unit_type") == "N3_POSITIVE_CONTROL"]
    arm_counts = Counter((r.get("directive_arm"), r.get("action_role")) for r in positive)
    expected_arms = Counter({
        ("ALIGNED", "AUTH"): 48,
        ("ALIGNED", "ALT"): 48,
        ("CONFLICT", "AUTH"): 48,
        ("CONFLICT", "ALT"): 48,
    })
    if arm_counts != expected_arms:
        raise SystemExit(f"FATAL {scorer} N3 positive arm census {dict(arm_counts)}")
    for r in positive:
        m = r.get("CA_MARGIN")
        if not isinstance(m, (int, float)) or isinstance(m, bool) or not math.isfinite(float(m)):
            raise SystemExit(f"FATAL {scorer} N3 non-finite CA_MARGIN")
    aligned = [r for r in positive if r.get("directive_arm") == "ALIGNED" and r.get("action_role") == "AUTH"]
    conflict = [r for r in positive if r.get("directive_arm") == "CONFLICT" and r.get("action_role") == "ALT"]
    if any(r.get("oracle_status") != "ALLOW" for r in aligned):
        raise SystemExit(f"FATAL {scorer} N3 ALIGNED/AUTH oracle status drift")
    if any(r.get("oracle_status") != "DENY" for r in conflict):
        raise SystemExit(f"FATAL {scorer} N3 CONFLICT/ALT oracle status drift")
    descendants = {"SHAM", "ECHO"}
    for label, rs in [("ALIGNED/AUTH", aligned), ("CONFLICT/ALT", conflict)]:
        per = defaultdict(list)
        for r in rs:
            per[str(r["base_id"])].append(r)
        if set(per) != bases:
            raise SystemExit(f"FATAL {scorer} N3 {label} base identity mismatch")
        for bid, brs in per.items():
            ds = {r.get("descendant") for r in brs}
            if ds != descendants or len(brs) != 2:
                raise SystemExit(f"FATAL {scorer} N3 {label} descendant mismatch {bid}: {ds}")
    return bases


def verify_lineage(root: Path, paths):
    for key in ("a14_llama", "a14_gemma", "n3_llama", "n3_gemma", "n3_freeze", "n3_analysis"):
        if not paths[key].exists():
            raise SystemExit(f"FATAL missing required input: {paths[key]}")
    for key, expected in EXPECTED_INPUT_SHA.items():
        got = sha256_file(paths[key])
        if got != expected:
            raise SystemExit(f"FATAL input hash drift {key}: expected={expected} got={got}")
    if sha256_file(paths["n3_freeze"]) != N3_FREEZE_FILE_SHA:
        raise SystemExit("FATAL N3_FREEZE.json file hash drift")
    n3_freeze = read_json(paths["n3_freeze"])
    if n3_freeze.get("freeze_sha256") != N3_FREEZE_INTERNAL_SHA:
        raise SystemExit("FATAL N3 internal freeze hash drift")
    n3_analysis = read_json(paths["n3_analysis"])
    if n3_analysis.get("freeze_sha256") != N3_FREEZE_INTERNAL_SHA:
        raise SystemExit("FATAL N3 analysis freeze lineage mismatch")
    for scorer in ("llama", "gemma"):
        expected = EXPECTED_INPUT_SHA[f"n3_{scorer}"]
        got = n3_analysis.get("science_integrity", {}).get(scorer, {}).get("science_scores_sha256")
        if got != expected:
            raise SystemExit(f"FATAL N3 analysis integrity hash mismatch for {scorer}")


def freeze_self_hash(obj):
    x = dict(obj)
    x.pop("freeze_sha256", None)
    return canonical_hash(x)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", required=True)
    ap.add_argument("--run-dir", default="R2B_JTF_AUTHOR_v1")
    ap.add_argument("--package-dir", default="R2B_JTF_PREFREEZE_v1")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    run_dir = root / args.run_dir
    package_dir = root / args.package_dir
    paths = paths_for(root)
    verify_lineage(root, paths)

    a14_bases = {}
    n3_bases = {}
    for scorer in ("llama", "gemma"):
        a14_bases[scorer] = validate_a14(read_jsonl(paths[f"a14_{scorer}"]), scorer)
        n3_bases[scorer] = validate_n3(read_jsonl(paths[f"n3_{scorer}"]), scorer)
        if a14_bases[scorer] != n3_bases[scorer]:
            raise SystemExit(f"FATAL {scorer} A14/N3 base identity mismatch")
    if a14_bases["llama"] != a14_bases["gemma"]:
        raise SystemExit("FATAL A14 cross-scorer base mismatch")
    if n3_bases["llama"] != n3_bases["gemma"]:
        raise SystemExit("FATAL N3 cross-scorer base mismatch")

    implementation_names = [
        "R2B_00_freeze.py",
        "R2B_01_analyze.py",
        "R2B_02_verify.py",
        "PROTOCOL_SPEC.md",
        "README.md",
        "freeze_R2B_JTF_v1.sh",
        "analyze_R2B_JTF_v1.sh",
    ]
    implementation_hashes = {}
    for name in implementation_names:
        p = package_dir / name
        if not p.exists():
            raise SystemExit(f"FATAL missing package implementation file: {p}")
        implementation_hashes[name] = sha256_file(p)

    run_dir.mkdir(parents=True, exist_ok=True)
    freeze_path = run_dir / "R2B_JTF_FREEZE.json"
    if freeze_path.exists():
        raise SystemExit(f"FATAL freeze already exists: {freeze_path}")

    fr = {
        "schema": SCHEMA,
        "status": "FROZEN_PRE_ANALYSIS_AUTHOR",
        "spec": SPEC,
        "spec_sha256": canonical_hash(SPEC),
        "input_hashes": {key: sha256_file(paths[key]) for key in EXPECTED_INPUT_SHA},
        "lineage": {
            "a14_protocol_hash": A14_PROTOCOL_HASH,
            "n3_freeze_internal_sha256": N3_FREEZE_INTERNAL_SHA,
            "n3_freeze_file_sha256": N3_FREEZE_FILE_SHA,
            "n3_analysis_sha256": sha256_file(paths["n3_analysis"]),
        },
        "implementation_hashes": implementation_hashes,
        "base_ids": sorted(a14_bases["llama"]),
        "census": {
            "n_bases": 24,
            "a14_cells_per_scorer": 96,
            "n3_total_units_per_scorer": 288,
            "n3_aligned_auth_rows_per_scorer": 48,
            "n3_conflict_alt_rows_per_scorer": 48,
        },
        "notes": [
            "This freeze is created before the author-run R2B-JTF frontier analysis.",
            "The underlying A14 and N3 score outcomes already existed; R2B-JTF is post-hoc deterministic analysis, not a prospective model experiment.",
            "R2B_00_freeze.py computes no threshold/frontier outcome values.",
            "All valid R2B-JTF outcomes are retained regardless of whether threshold tuning looks favorable, null, adverse, or heterogeneous.",
        ],
    }
    fr["freeze_sha256"] = freeze_self_hash(fr)
    freeze_path.write_text(json.dumps(fr, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("[R2B-00] FREEZE PASS")
    print(f"[R2B-00] project_root={root}")
    print("[R2B-00] validated A14=96 benign cells / 24 bases per scorer")
    print("[R2B-00] validated N3=288 rows / 24 bases per scorer; relevant arms=48 AUTH + 48 ALT")
    print("[R2B-00] NO threshold/frontier outcomes generated")
    print(f"[R2B-00] freeze={freeze_path}")
    print(f"[R2B-00] freeze_sha256={fr['freeze_sha256']}")
    print(f"[R2B-00] freeze_file_sha256={sha256_file(freeze_path)}")


if __name__ == "__main__":
    main()
