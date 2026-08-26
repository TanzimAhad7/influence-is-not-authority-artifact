#!/usr/bin/env python3
"""Zero-call proof of frozen directive transport into the parsed AgentDojo environment.

This audit deliberately does NOT require the GroundTruthPipeline to traverse the
carrier. Runtime traversal is post-assignment behavior and is measured during the
scientific run as context_delivered (ITT); it is not a pre-science transport gate.
"""
from __future__ import annotations
import datetime, json, os, sys
from pathlib import Path


def jdump(p, o):
    Path(p).write_text(json.dumps(o, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def canon_obj(o):
    if hasattr(o, "model_dump"):
        o = o.model_dump(mode="json")
    return json.loads(json.dumps(o, ensure_ascii=False, default=str))


def find_substring_paths(obj, needle, path="$", out=None):
    if out is None:
        out = []
    if isinstance(obj, str):
        if needle in obj:
            out.append(path)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            find_substring_paths(v, needle, f"{path}.{k}", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            find_substring_paths(v, needle, f"{path}[{i}]", out)
    return out


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: E2E_PRE_10_yaml_roundtrip_audit.py PROJECT_ROOT")

    root = Path(sys.argv[1]).resolve()
    pre = root / "E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build"
    pkg = root / "E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1"
    science = root / "E2E_ATTR_AUTH_v1/scientific_v1"

    if science.exists() and any(science.iterdir()):
        raise SystemExit("FATAL scientific directory nonempty")

    sys.path.insert(0, str(pkg / "code"))
    os.environ["E2E_CONTEXT_RENDERED"] = str(pre / "CONTEXT_RENDERED.jsonl")

    from agentdojo.task_suite.load_suites import get_suite
    import e2e_attacks

    rows = [json.loads(x) for x in (pre / "CONTEXT_RENDERED.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    target = [r for r in rows if r["context"] in {"ALIGNED", "CONFLICT"}]

    audit = []
    failures = []

    for r in target:
        suite = get_suite("v1", r["suite"])
        ut = suite.get_user_task_by_id(r["user_task"])
        inj = suite.get_injection_task_by_id(r["injection_task"])
        cls = e2e_attacks.E2EAlignedAttack if r["context"] == "ALIGNED" else e2e_attacks.E2EConflictAttack

        injections = cls(suite, None).attack(ut, inj)
        expected_carrier = r["selected_injection_vector"]
        carrier_ok = set(injections.keys()) == {expected_carrier}

        # Exact Patch-1 crash site: Python .format(...) followed by yaml.safe_load(...)
        # inside AgentDojo's official load_and_inject_default_environment().
        env = suite.load_and_inject_default_environment(injections)
        env_obj = canon_obj(env)

        raw = r["directive"]
        match_paths = find_substring_paths(env_obj, raw)
        raw_ok = bool(match_paths)
        ok = carrier_ok and raw_ok

        item = {
            "case_id": r["case_id"],
            "context": r["context"],
            "suite": r["suite"],
            "user_task": r["user_task"],
            "expected_carrier": expected_carrier,
            "attack_returned_only_expected_carrier": carrier_ok,
            "yaml_parse_pass": True,
            "exact_raw_directive_present_in_parsed_environment": raw_ok,
            "parsed_environment_match_paths": match_paths,
            "pass": ok,
        }
        audit.append(item)
        if not ok:
            failures.append(item)

    out = {
        "schema": "E2E_YAML_DIRECTIVE_ENVIRONMENT_TRANSPORT_AUDIT_V2",
        "created_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "verification_layer": "parsed_environment_before_agent_trajectory",
        "scientific_interpretation": "transport-only; runtime context delivery remains an ITT scientific diagnostic",
        "NO_SCIENTIFIC_MODEL_CALLS": True,
        "n_expected": len(target),
        "n_pass": len(target) - len(failures),
        "n_fail": len(failures),
        "status": "PASS" if not failures and len(target) == 28 else "FAIL",
        "rows": audit,
    }
    jdump(pre / "YAML_DIRECTIVE_ROUNDTRIP_AUDIT.json", out)
    print(json.dumps({k: out[k] for k in ["status", "n_expected", "n_pass", "n_fail", "NO_SCIENTIFIC_MODEL_CALLS"]}, indent=2))
    if out["status"] != "PASS":
        print(json.dumps({"failures": failures}, indent=2, ensure_ascii=False))
        raise SystemExit("FATAL parsed-environment directive transport audit failed")


if __name__ == "__main__":
    main()
