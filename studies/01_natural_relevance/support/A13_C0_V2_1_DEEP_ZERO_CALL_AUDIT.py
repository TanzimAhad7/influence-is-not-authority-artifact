#!/usr/bin/env python3
"""
A13-C0 v2.1 — DEEP ZERO-CALL COVERAGE / ELIGIBILITY AUDIT
========================================================

Purpose
-------
This script is deliberately ZERO MODEL CALLS.  It audits the historical A13
population from the complete 97-task root and checks two distinct questions:

  (A) CONDITIONAL COMPLETENESS:
      Was the historical execution complete under the exact frozen A13
      privileged-action/taxonomy rule?

  (B) EXTRACTION-RULE COVERAGE:
      Did that frozen rule itself fail to recognize any non-read-only
      ground-truth tool action that is a plausible side-effect / guardable
      action under A13's own stated design intent?

The second question is important because checking

    protocol_tasks == tasks_derived_from_frozen_taxonomy

is circular if the taxonomy extraction itself omitted a function.

Scientific-integrity boundary
-----------------------------
* This script performs NO agent generation, scorer call, API call, or vLLM call.
* It does NOT score any newly identified decision.
* It does NOT redefine A13 outcomes.
* If it surfaces an extraction-rule coverage defect, the next step is to freeze
  an extension rule BEFORE any new A13 scores are examined.

Run from the exact project venv used by A13.
"""

from __future__ import annotations

import argparse
import ast
import collections
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED = {
    "A13.py": "f771850375b4f5af7bc2cec6a4e166057f33fab26d686320b8ef2d8d32557f05",
    "a13/protocol.json": "8c0caa2e509f94d0e2eea37cfaf53840319d407167c15e2a052633c53854de43",
    "a13/taxonomy.json": "02894700c2ff370b28b858a6f533805c37fd11d86bb1c70af3b71ac21cdc674b",
    "a13/decisions.jsonl": "af6a62c5689e7d26180f0091a121839b645e1dcb54e5aaf87427f6e75c19dca9",
    "a13/results.json": "6ced3fc14a60574f95881344ac3d6bb5b8cf7d88d59ac3c844cae35d4121646b",
}
EXPECTED_INPUT_ZIP = "3e6aaae53bfe10c57156c41def0dd13b3ada05ec299b5803a52bf586082984a2"
EXPECTED_HISTORICAL_ZIP = "d4b48c9bde17602e47c2d2feea3f17ee5f2ba6f090395b011b3e84bc3fabc327"
EXPECTED_AGENTDOJO = "0.1.35"
EXPECTED_BENCHMARK = "v1"
CLASS_LABELS = {"SPECIFIED", "DELEGATED", "PARTIAL"}

# Independent, deliberately broad *screen*, not an automatic privilege oracle.
# A13 itself explicitly described get/search/list as read-only.  We also include
# read/check, which are read-like in the finite v1 ground-truth function set.
# Any ground-truth function outside these prefixes that the frozen A13 rule did
# not recognize is surfaced for source-level human adjudication BEFORE scoring.
READ_ONLY_NAME_PREFIXES = ("get_", "search_", "list_", "read_", "check_")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def stable_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_json(p: Path, obj) -> None:
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalized_text(x) -> str:
    if isinstance(x, dict):
        x = json.dumps(x, sort_keys=True, ensure_ascii=False)
    elif isinstance(x, (list, tuple)):
        x = " ".join(map(str, x))
    return re.sub(r"[^a-z0-9@.\-_ ]+", " ", str(x).lower()).strip()


def exact_prompt_coverage(call: dict, prompt: str, rule: dict) -> dict:
    """Reproduce A13's frozen prompt-coverage classifier for one GT call."""
    min_value_len = int(rule["min_value_len"])
    overlap_threshold = float(rule["token_overlap_threshold"])
    specified_min = float(rule["specified_fraction_min"])
    delegated_max = float(rule["delegated_fraction_max"])
    prompt_n = normalized_text(prompt)

    chars_matched = 0
    chars_total = 0
    matched = 0
    matchable = 0
    per_arg = {}

    for k, v in (call.get("args") or {}).items():
        nv = normalized_text(v)
        vlen = len(nv)
        if vlen < min_value_len:
            r = None
        elif nv in prompt_n:
            r = True
        else:
            toks = [t for t in nv.split() if len(t) >= 3]
            if not toks:
                r = False
            else:
                hit = sum(1 for t in toks if t in prompt_n)
                r = (hit / len(toks)) >= overlap_threshold

        per_arg[k] = {
            "normalized_chars": vlen,
            "status": "skip_short" if r is None else ("in_prompt" if r else "not_in_prompt"),
        }
        if r is None:
            continue
        matchable += 1
        matched += int(bool(r))
        chars_total += vlen
        if r:
            chars_matched += vlen

    frac = (chars_matched / chars_total) if chars_total else None
    if frac is None:
        label = "UNCLASSIFIABLE"
    elif frac >= specified_min:
        label = "SPECIFIED"
    elif frac <= delegated_max:
        label = "DELEGATED"
    else:
        label = "PARTIAL"

    return {
        "args_matched": matched,
        "args_matchable": matchable,
        "chars_matched": chars_matched,
        "chars_total": chars_total,
        "specified_fraction": frac,
        "label": label,
        "per_arg": per_arg,
    }


def mt(m: dict) -> str:
    c = m.get("content")
    if isinstance(c, list):
        pieces = []
        for x in c:
            if isinstance(x, dict):
                pieces.append(str(x.get("content", "") or ""))
            else:
                pieces.append(str(x))
        return " ".join(pieces)
    return str(c or "")


def original_is_privileged(fn: str | None, protocol: dict) -> bool:
    if not fn:
        return False
    rule = protocol["privileged_action_rule"]
    explicit = set(rule["explicit_functions"])
    prefixes = tuple(rule["side_effect_prefixes"])
    return fn in explicit or any(fn.startswith(p) for p in prefixes)


def broad_non_readonly_screen(fn: str | None) -> bool:
    if not fn:
        return False
    return not any(fn.startswith(p) for p in READ_ONLY_NAME_PREFIXES)


def actual_calls(messages: list[dict], predicate) -> list[dict]:
    out = []
    for mi, m in enumerate(messages):
        calls = list(m.get("tool_calls") or [])
        for ci, tc in enumerate(calls):
            if predicate(tc.get("function")):
                out.append({
                    "message_index": mi,
                    "call_index": ci,
                    "call": tc,
                    "total_calls_in_turn": len(calls),
                })
    return out


def greedy_map(gt_rows: list[dict], messages: list[dict], predicate, fn_key="privileged_fn") -> list[dict]:
    """Independent same-function/order mapping, equivalent to frozen A13 logic."""
    actual = actual_calls(messages, predicate)
    used = set()
    cursor = -1
    out = []
    for row in gt_rows:
        fn = row[fn_key]
        chosen = None
        for ai, ac in enumerate(actual):
            if ai in used or ai <= cursor:
                continue
            if ac["call"].get("function") == fn:
                chosen = (ai, ac)
                break
        if chosen is None:
            out.append({"row": row, "mapped": False, "actual": None})
        else:
            ai, ac = chosen
            used.add(ai)
            cursor = ai
            out.append({"row": row, "mapped": True, "actual": ac})
    return out


def deterministic_pre_score_reason(log_obj: dict, mapping: dict) -> str:
    if not mapping["mapped"]:
        return "ground_truth_privileged_call_not_executed_or_not_mappable"
    ac = mapping["actual"]
    if not bool(log_obj.get("utility")):
        return "agentdojo_utility_false"
    if ac["total_calls_in_turn"] != 1:
        return "multi_tool_call_assistant_turn"
    mi = ac["message_index"]
    ctx = list(log_obj.get("messages") or [])[:mi]
    if not ctx:
        return "empty_context"
    if not any(m.get("role") == "user" for m in ctx):
        return "no_user_message_before_decision"
    spans = [m for m in ctx if m.get("role") == "tool" and mt(m).strip()]
    if not spans:
        return "no_eligible_tool_span"
    return "reaches_scoring"


def static_v1_task_ids(agentdojo_root: Path, suites: list[str]) -> dict[str, set[str]]:
    """Independent source-level task-ID extraction, including TaskCombinator tasks."""
    out: dict[str, set[str]] = {}
    for suite in suites:
        p = agentdojo_root / "default_suites" / "v1" / suite / "user_tasks.py"
        tree = ast.parse(p.read_text(encoding="utf-8"))
        ids: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and re.fullmatch(r"UserTask[0-9]+", node.name):
                if any("register_user_task" in ast.unparse(d) for d in node.decorator_list):
                    n = int(re.search(r"[0-9]+", node.name).group())
                    ids.add(f"user_task_{n}")
            elif isinstance(node, ast.Call):
                fn = ast.unparse(node.func)
                if fn.endswith(".create_combined_task") and node.args:
                    a0 = node.args[0]
                    if isinstance(a0, ast.Constant) and isinstance(a0.value, str) and re.fullmatch(r"UserTask[0-9]+", a0.value):
                        n = int(re.search(r"[0-9]+", a0.value).group())
                        ids.add(f"user_task_{n}")
        out[suite] = ids
    return out


def find_function_def(agentdojo_root: Path, function_name: str) -> dict:
    tools_root = agentdojo_root / "default_suites" / "v1" / "tools"
    hits = []
    for p in sorted(tools_root.glob("*.py")):
        try:
            tree = ast.parse(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
                doc = ast.get_docstring(node) or ""
                hits.append({
                    "relative_file": str(p.relative_to(agentdojo_root)),
                    "line": int(node.lineno),
                    "docstring_first_line": doc.strip().splitlines()[0] if doc.strip() else "",
                })
    return {"hits": hits, "unique": len(hits) == 1}


def verify_input_bundle_zip(zip_path: Path, installed_agentdojo_root: Path) -> dict:
    result = {
        "path": str(zip_path),
        "present": zip_path.exists(),
        "expected_sha256": EXPECTED_INPUT_ZIP,
        "sha256": None,
        "sha256_match": None,
        "manifest_entries": None,
        "manifest_internal_bad": [],
        "installed_agentdojo_source_compared": 0,
        "installed_agentdojo_source_bad": [],
    }
    if not zip_path.exists():
        return result

    result["sha256"] = sha256_file(zip_path)
    result["sha256_match"] = result["sha256"] == EXPECTED_INPUT_ZIP
    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        prefix = "A13_C0_INPUT_BUNDLE_v1/"
        manifest_name = prefix + "FILE_SHA256.txt"
        if manifest_name not in names:
            result["manifest_internal_bad"].append("missing FILE_SHA256.txt")
            return result
        lines = zf.read(manifest_name).decode("utf-8").splitlines()
        entries = []
        for line in lines:
            if not line.strip():
                continue
            h, rel_raw = line.split(None, 1)
            rel_raw = rel_raw.strip()
            # FILE_SHA256.txt was produced by sha256sum over paths prefixed with "./",
            # while ZIP member names omit that redundant component. Normalize the
            # manifest path before resolving it inside the archive or against the
            # installed AgentDojo tree. Reject absolute/parent-traversal paths.
            rel = rel_raw.replace("\\", "/")
            while rel.startswith("./"):
                rel = rel[2:]
            rel_path = PurePosixPath(rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                result["manifest_internal_bad"].append({"unsafe_manifest_path": rel_raw})
                continue
            rel = rel_path.as_posix()
            entries.append((h, rel))
            member = prefix + rel
            if member not in names:
                result["manifest_internal_bad"].append({"missing_member": rel, "manifest_path": rel_raw})
                continue
            got = sha256_bytes(zf.read(member))
            if got != h:
                result["manifest_internal_bad"].append({"member": rel, "manifest_path": rel_raw, "expected": h, "actual": got})

            if rel.startswith("agentdojo_source/") and "/__pycache__/" not in rel and not rel.endswith(".pyc"):
                installed = installed_agentdojo_root / rel[len("agentdojo_source/"):]
                result["installed_agentdojo_source_compared"] += 1
                if not installed.exists():
                    result["installed_agentdojo_source_bad"].append({"missing_installed": str(installed)})
                else:
                    ih = sha256_file(installed)
                    if ih != h:
                        result["installed_agentdojo_source_bad"].append({
                            "relative": rel,
                            "bundle_sha256": h,
                            "installed_sha256": ih,
                        })
        result["manifest_entries"] = len(entries)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project_root", help="phase0_pilot root containing A13.py and a13/")
    ap.add_argument(
        "--input-bundle-zip",
        default=None,
        help="Optional A13_C0_INPUT_BUNDLE_v1.zip; default: <project_root>/A13_C0_INPUT_BUNDLE_v1.zip",
    )
    ap.add_argument(
        "--historical-zip",
        default=None,
        help="Optional A13_C0_HISTORICAL_A13_COMPLETE_v1.zip; default: <project_root>/A13_C0_HISTORICAL_A13_COMPLETE_v1.zip",
    )
    ap.add_argument(
        "--out-dir",
        default=None,
        help="Output directory; default: <project_root>/A13_C0_V2_1_AUTHOR_AUDIT",
    )
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    a13 = root / "a13"
    out_dir = Path(args.out_dir).resolve() if args.out_dir else root / "A13_C0_V2_1_AUTHOR_AUDIT"
    out_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Exact historical byte integrity
    # ------------------------------------------------------------------
    actual_hashes = {
        "A13.py": sha256_file(root / "A13.py"),
        "a13/protocol.json": sha256_file(a13 / "protocol.json"),
        "a13/taxonomy.json": sha256_file(a13 / "taxonomy.json"),
        "a13/decisions.jsonl": sha256_file(a13 / "decisions.jsonl"),
        "a13/results.json": sha256_file(a13 / "results.json"),
    }
    historical_hashes_match = actual_hashes == EXPECTED
    if not historical_hashes_match:
        raise SystemExit(
            "FATAL: exact historical A13 input hash mismatch.\n"
            f"expected={json.dumps(EXPECTED, indent=2)}\n"
            f"actual={json.dumps(actual_hashes, indent=2)}"
        )

    protocol = json.loads((a13 / "protocol.json").read_text(encoding="utf-8"))
    frozen_taxonomy = json.loads((a13 / "taxonomy.json").read_text(encoding="utf-8"))
    records = [
        json.loads(x)
        for x in (a13 / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
        if x.strip()
    ]
    manifest = json.loads((a13 / "manifest.json").read_text(encoding="utf-8"))

    if protocol.get("agentdojo_version") != EXPECTED_AGENTDOJO:
        raise SystemExit("FATAL: protocol AgentDojo version mismatch")
    if frozen_taxonomy.get("benchmark_version") != EXPECTED_BENCHMARK:
        raise SystemExit("FATAL: taxonomy benchmark version mismatch")

    # ------------------------------------------------------------------
    # 2. Live installed AgentDojo + exact taxonomy rebuild, still zero-call
    # ------------------------------------------------------------------
    installed_version = importlib.metadata.version("agentdojo")
    if installed_version != EXPECTED_AGENTDOJO:
        raise SystemExit(f"FATAL: installed agentdojo={installed_version}, expected {EXPECTED_AGENTDOJO}")

    import agentdojo  # noqa: imported only to locate exact package source
    agentdojo_root = Path(agentdojo.__file__).resolve().parent

    # Optional bundle/source reconciliation.
    input_zip = Path(args.input_bundle_zip).resolve() if args.input_bundle_zip else root / "A13_C0_INPUT_BUNDLE_v1.zip"
    input_bundle_check = verify_input_bundle_zip(input_zip, agentdojo_root)
    if input_bundle_check["present"]:
        if not input_bundle_check["sha256_match"]:
            raise SystemExit("FATAL: A13_C0_INPUT_BUNDLE_v1.zip SHA-256 mismatch")
        if input_bundle_check["manifest_internal_bad"]:
            raise SystemExit("FATAL: input-bundle internal file manifest mismatch")
        if input_bundle_check["installed_agentdojo_source_bad"]:
            raise SystemExit("FATAL: installed AgentDojo source differs from captured input bundle")

    historical_zip = Path(args.historical_zip).resolve() if args.historical_zip else root / "A13_C0_HISTORICAL_A13_COMPLETE_v1.zip"
    historical_zip_check = {
        "path": str(historical_zip),
        "present": historical_zip.exists(),
        "expected_sha256": EXPECTED_HISTORICAL_ZIP,
        "sha256": sha256_file(historical_zip) if historical_zip.exists() else None,
    }
    historical_zip_check["sha256_match"] = (
        historical_zip_check["sha256"] == EXPECTED_HISTORICAL_ZIP
        if historical_zip_check["present"] else None
    )
    if historical_zip_check["present"] and not historical_zip_check["sha256_match"]:
        raise SystemExit("FATAL: historical A13 complete ZIP SHA-256 mismatch")

    # Load the exact frozen A13 source without executing main().
    spec = importlib.util.spec_from_file_location("a13_frozen_source", root / "A13.py")
    if spec is None or spec.loader is None:
        raise SystemExit("FATAL: cannot load frozen A13.py")
    a13mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a13mod)

    rebuilt_taxonomy = a13mod.build_taxonomy()
    rebuilt_exact_match = rebuilt_taxonomy == frozen_taxonomy
    rebuilt_hash_match = rebuilt_taxonomy.get("taxonomy_hash") == frozen_taxonomy.get("taxonomy_hash")
    if not rebuilt_exact_match:
        # Never overwrite the frozen taxonomy.  Save the rebuild for diffing.
        write_json(out_dir / "REBUILT_TAXONOMY_MISMATCH.json", rebuilt_taxonomy)
        raise SystemExit(
            "FATAL: live zero-call taxonomy rebuild does not exactly reproduce frozen taxonomy. "
            "See REBUILT_TAXONOMY_MISMATCH.json"
        )

    # Independent source-level 97-task ID audit, including combined tasks.
    suites = list(frozen_taxonomy["suites"])
    source_ids = static_v1_task_ids(agentdojo_root, suites)
    taxonomy_ids = collections.defaultdict(set)
    for t in frozen_taxonomy["task_inventory"]:
        taxonomy_ids[t["suite"]].add(t["user_task"])
    source_id_diff = {
        s: sorted(source_ids[s] ^ taxonomy_ids[s])
        for s in suites
    }
    if any(source_id_diff.values()):
        raise SystemExit(f"FATAL: source-vs-taxonomy task ID mismatch: {source_id_diff}")

    # ------------------------------------------------------------------
    # 3. Reconstruct original frozen 97 -> 69 -> 26 flow independently
    # ------------------------------------------------------------------
    inv = frozen_taxonomy["task_inventory"]
    tax_decisions = frozen_taxonomy["decisions"]
    dev = [t for t in inv if t["development"]]
    untouched = [t for t in inv if not t["development"]]
    no_priv = [t for t in untouched if t["n_privileged_calls"] == 0]
    priv_tasks = [t for t in untouched if t["n_privileged_calls"] > 0]
    nondev_dec = [d for d in tax_decisions if not d["development"]]
    class_dec = [d for d in nondev_dec if d["label"] in CLASS_LABELS]
    unclass_dec = [d for d in nondev_dec if d["label"] not in CLASS_LABELS]
    class_tasks = {(d["suite"], d["user_task"]) for d in class_dec}
    protocol_tasks = {tuple(x.split("/", 1)) for x in protocol["task_ids_to_run"]}

    runroot = a13 / "agentdojo_runs" / "vllm_parsed"
    runfiles = sorted(runroot.glob("*/*/none/none.json"))
    trajectory_tasks = {
        (p.relative_to(runroot).parts[0], p.relative_to(runroot).parts[1])
        for p in runfiles
    }

    # Every historical trajectory must match the original manifest byte-for-byte.
    manifest_bad = []
    manifest_run_entries = {
        k: v for k, v in manifest["files"].items() if "/agentdojo_runs/" in k
    }
    for p in runfiles:
        rel = str(p.relative_to(a13))
        key = "/home/anon_/ratchet/phase0_pilot/a13/" + rel
        if key not in manifest_run_entries:
            manifest_bad.append({"not_in_manifest": rel})
            continue
        got = sha256_file(p)
        exp = manifest_run_entries[key]["sha256"]
        if got != exp:
            manifest_bad.append({"file": rel, "expected": exp, "actual": got})
    if manifest_bad:
        raise SystemExit(f"FATAL: trajectory/manifest mismatch: {manifest_bad[:3]}")

    record_by_id = {r["decision_id"]: r for r in records}
    class_ids = {d["decision_id"] for d in class_dec}
    if set(record_by_id) != class_ids:
        raise SystemExit("FATAL: decisions.jsonl does not contain exactly the frozen classifiable decision IDs")

    # Independent decision mapping + deterministic pre-score exclusion reconstruction.
    class_by_task = collections.defaultdict(list)
    for d in class_dec:
        class_by_task[(d["suite"], d["user_task"])].append(d)
    for rows in class_by_task.values():
        rows.sort(key=lambda x: x["privileged_call_index"])

    reconstructed_pre_score = collections.Counter()
    mapping_discrepancies = []
    for task_key, gt_rows in sorted(class_by_task.items()):
        p = runroot / task_key[0] / task_key[1] / "none" / "none.json"
        if not p.exists():
            mapping_discrepancies.append({"task": "/".join(task_key), "missing_trajectory": True})
            continue
        log_obj = json.loads(p.read_text(encoding="utf-8"))
        mapped_rows = greedy_map(
            gt_rows,
            list(log_obj.get("messages") or []),
            lambda fn: original_is_privileged(fn, protocol),
        )
        for mp in mapped_rows:
            d = mp["row"]
            rec = record_by_id[d["decision_id"]]
            reason = deterministic_pre_score_reason(log_obj, mp)
            reconstructed_pre_score[reason] += 1
            if reason != "reaches_scoring":
                if rec.get("primary_exclusion_reason") != reason:
                    mapping_discrepancies.append({
                        "decision_id": d["decision_id"],
                        "record_reason": rec.get("primary_exclusion_reason"),
                        "reconstructed_reason": reason,
                    })
            else:
                rr = rec.get("primary_exclusion_reason")
                allowed_post = (
                    rr is None
                    or rr == "full_score_failed"
                    or rr == "user_deletion_score_failed"
                    or (isinstance(rr, str) and rr.startswith("tool_deletion_score_failed_at_message_"))
                )
                if not allowed_post:
                    mapping_discrepancies.append({
                        "decision_id": d["decision_id"],
                        "unexpected_postscore_reason": rr,
                    })

    if mapping_discrepancies:
        raise SystemExit(f"FATAL: independent mapping/reason reconstruction mismatch: {mapping_discrepancies[:5]}")

    record_reason_counts = collections.Counter(r.get("primary_exclusion_reason") or "valid" for r in records)
    valid_records = [r for r in records if r.get("primary_valid")]
    score_failure_records = [
        r for r in records
        if isinstance(r.get("primary_exclusion_reason"), str)
        and (
            r["primary_exclusion_reason"].startswith("full_score_failed")
            or r["primary_exclusion_reason"].startswith("user_deletion_score_failed")
            or r["primary_exclusion_reason"].startswith("tool_deletion_score_failed_at_message_")
        )
    ]

    conditional_flow = {
        "all_historical_user_tasks": len(inv),
        "development_exclusions": len(dev),
        "untouched_tasks": len(untouched),
        "untouched_no_privileged_under_frozen_rule": len(no_priv),
        "untouched_with_privileged_under_frozen_rule": len(priv_tasks),
        "nondevelopment_privileged_decision_rows": len(nondev_dec),
        "unclassifiable_privileged_decisions": len(unclass_dec),
        "classifiable_confirmatory_tasks": len(class_tasks),
        "classifiable_confirmatory_decisions": len(class_dec),
        "protocol_tasks": len(protocol_tasks),
        "trajectory_tasks": len(trajectory_tasks),
        "decision_records": len(records),
        "valid_decisions": len(valid_records),
        "valid_tasks": len({(r["suite"], r["user_task"]) for r in valid_records}),
        "protocol_minus_classifiable_tasks": sorted("/".join(x) for x in protocol_tasks - class_tasks),
        "classifiable_minus_protocol_tasks": sorted("/".join(x) for x in class_tasks - protocol_tasks),
        "protocol_minus_trajectory_tasks": sorted("/".join(x) for x in protocol_tasks - trajectory_tasks),
        "trajectory_minus_protocol_tasks": sorted("/".join(x) for x in trajectory_tasks - protocol_tasks),
        "record_reason_counts": dict(sorted(record_reason_counts.items())),
        "independent_pre_score_counts": dict(sorted(reconstructed_pre_score.items())),
        "score_failure_records": len(score_failure_records),
    }

    # ------------------------------------------------------------------
    # 4. Audit the extraction rule itself across EVERY GT function/call
    # ------------------------------------------------------------------
    function_counts = collections.Counter()
    function_audit = {}
    broad_rows = []
    missed_rows = []

    task_meta = {(t["suite"], t["user_task"]): t for t in inv}
    original_decision_lookup = {
        (d["suite"], d["user_task"], d["privileged_call_index"], d["privileged_fn"]): d
        for d in tax_decisions
    }

    # Ground-truth call index is independent of A13's privileged_call_index.
    for t in inv:
        for gt_call_index, call in enumerate(t.get("ground_truth_all") or []):
            fn = call["function"]
            function_counts[fn] += 1
            orig = original_is_privileged(fn, protocol)
            broad = broad_non_readonly_screen(fn)
            if fn not in function_audit:
                function_audit[fn] = {
                    "function": fn,
                    "ground_truth_occurrences": 0,
                    "frozen_rule_privileged": orig,
                    "broad_non_readonly_screen": broad,
                    "source_definition": find_function_def(agentdojo_root, fn),
                }
            function_audit[fn]["ground_truth_occurrences"] += 1

            if broad:
                cov = exact_prompt_coverage(call, t["prompt"], frozen_taxonomy["rule"])
                row = {
                    "suite": t["suite"],
                    "user_task": t["user_task"],
                    "task_key": f"{t['suite']}/{t['user_task']}",
                    "development": bool(t["development"]),
                    "ground_truth_call_index": gt_call_index,
                    "function": fn,
                    "args": call.get("args") or {},
                    "frozen_rule_privileged": orig,
                    "broad_non_readonly_screen": True,
                    "specified_fraction": cov["specified_fraction"],
                    "label": cov["label"],
                    "per_arg": cov["per_arg"],
                    "source_definition": function_audit[fn]["source_definition"],
                }
                broad_rows.append(row)
                if not orig:
                    missed_rows.append(row)

    # Only untouched/nondevelopment missed rows can affect confirmatory coverage.
    missed_nondev = [r for r in missed_rows if not r["development"]]
    missed_nondev_classifiable = [r for r in missed_nondev if r["label"] in CLASS_LABELS]

    # Add historical trajectory/structural status for each missed candidate WITHOUT scoring.
    missed_by_task = collections.defaultdict(list)
    for r in missed_nondev:
        missed_by_task[(r["suite"], r["user_task"])].append(r)

    for task_key, rows in missed_by_task.items():
        p = runroot / task_key[0] / task_key[1] / "none" / "none.json"
        for r in rows:
            r["historical_a13_trajectory_present"] = p.exists()
            r["pre_score_structural_status"] = (
                "trajectory_absent__needs_fresh_agent_run_if_extension_is_frozen"
                if not p.exists() else "not_yet_mapped"
            )
        if not p.exists():
            continue

        log_obj = json.loads(p.read_text(encoding="utf-8"))
        # Reconstruct the *broad* GT sequence for this task so function/order mapping
        # is not biased by looking only at one missed call.
        t = task_meta[task_key]
        task_broad_rows = []
        for gt_call_index, call in enumerate(t.get("ground_truth_all") or []):
            if not broad_non_readonly_screen(call["function"]):
                continue
            cov = exact_prompt_coverage(call, t["prompt"], frozen_taxonomy["rule"])
            task_broad_rows.append({
                "ground_truth_call_index": gt_call_index,
                "privileged_fn": call["function"],
                "label": cov["label"],
            })
        mappings = greedy_map(
            task_broad_rows,
            list(log_obj.get("messages") or []),
            broad_non_readonly_screen,
        )
        map_by_gt_index = {m["row"]["ground_truth_call_index"]: m for m in mappings}
        for r in rows:
            mp = map_by_gt_index[r["ground_truth_call_index"]]
            r["pre_score_structural_status"] = deterministic_pre_score_reason(log_obj, mp)
            r["mapped_in_saved_trajectory"] = bool(mp["mapped"])
            if mp["mapped"]:
                r["actual_message_index"] = mp["actual"]["message_index"]
                r["actual_total_calls_in_turn"] = mp["actual"]["total_calls_in_turn"]
                r["actual_call"] = mp["actual"]["call"]
                r["trajectory_utility"] = bool(log_obj.get("utility"))

    # Hypothetical structural flow under the independent broad screen.
    broad_nondev = [r for r in broad_rows if not r["development"]]
    broad_nondev_tasks = {(r["suite"], r["user_task"]) for r in broad_nondev}
    broad_class = [r for r in broad_nondev if r["label"] in CLASS_LABELS]
    broad_class_tasks = {(r["suite"], r["user_task"]) for r in broad_class}
    broad_unclass = [r for r in broad_nondev if r["label"] not in CLASS_LABELS]
    broad_labels = collections.Counter(r["label"] for r in broad_class)

    # Task-level number with no broad candidate action.
    untouched_keys = {(t["suite"], t["user_task"]) for t in untouched}
    broad_no_action_tasks = untouched_keys - broad_nondev_tasks

    extraction_rule_audit = {
        "screen_name": "all_ground_truth_functions_except_get_search_list_read_check_prefixes",
        "screen_is_not_automatic_privilege_oracle": True,
        "reason": (
            "Independent finite-corpus screen for ground-truth actions that are not read-like by name. "
            "Any function caught by the screen but missed by the frozen A13 rule requires source-level "
            "human adjudication before C0 can close."
        ),
        "unique_ground_truth_functions": len(function_counts),
        "broad_non_readonly_unique_functions": len({r["function"] for r in broad_rows}),
        "frozen_rule_missed_unique_functions": sorted({r["function"] for r in missed_rows}),
        "frozen_rule_missed_occurrences_all_tasks": len(missed_rows),
        "frozen_rule_missed_nondevelopment_decisions": len(missed_nondev),
        "frozen_rule_missed_nondevelopment_classifiable_decisions": len(missed_nondev_classifiable),
        "frozen_rule_missed_nondevelopment_tasks": len({(r["suite"], r["user_task"]) for r in missed_nondev}),
        "broad_screen_flow": {
            "untouched_tasks": len(untouched),
            "untouched_no_broad_candidate_action": len(broad_no_action_tasks),
            "untouched_with_broad_candidate_action": len(broad_nondev_tasks),
            "broad_candidate_decisions": len(broad_nondev),
            "broad_unclassifiable_decisions": len(broad_unclass),
            "broad_classifiable_tasks": len(broad_class_tasks),
            "broad_classifiable_decisions": len(broad_class),
            "broad_classifiable_labels": dict(sorted(broad_labels.items())),
        },
    }

    # ------------------------------------------------------------------
    # 5. Write author-run outputs
    # ------------------------------------------------------------------
    audit = {
        "name": "A13-C0 v2.1 deep zero-call coverage / eligibility audit",
        "scientific_model_calls": 0,
        "historical_input_integrity": {
            "expected_hashes_match": historical_hashes_match,
            "hashes": actual_hashes,
            "agentdojo_installed_version": installed_version,
            "benchmark_version": frozen_taxonomy["benchmark_version"],
            "live_taxonomy_rebuild_exact_match": rebuilt_exact_match,
            "live_taxonomy_hash_match": rebuilt_hash_match,
            "source_task_counts": {s: len(source_ids[s]) for s in suites},
            "source_task_total": sum(len(source_ids[s]) for s in suites),
            "source_taxonomy_task_id_symmetric_difference": source_id_diff,
            "input_bundle_zip": input_bundle_check,
            "historical_zip": historical_zip_check,
            "trajectory_manifest_bad": manifest_bad,
        },
        "conditional_completeness_under_original_frozen_rule": conditional_flow,
        "extraction_rule_coverage_audit": extraction_rule_audit,
        "missed_candidates": missed_nondev,
        "function_audit": [function_audit[k] for k in sorted(function_audit)],
    }

    # Branch is intentionally conservative: any missed non-readonly GT function
    # means C0 cannot be closed as "no omitted eligible cases" until adjudicated.
    if missed_nondev:
        audit["c0_v2_branch"] = {
            "decision": "DO_NOT_CLOSE_C0_YET__POTENTIAL_EXTRACTION_RULE_COVERAGE_DEFECT",
            "new_scoring_authorized": False,
            "next_step": (
                "Human/source-level adjudicate the missed functions. If they are accepted as guardable side-effecting "
                "actions under A13's intended population, freeze an all-eligible extension rule BEFORE any new scores."
            ),
        }
    else:
        audit["c0_v2_branch"] = {
            "decision": "NO_EXTRACTION_RULE_COVERAGE_DEFECT_FOUND_BY_V2_1_SCREEN",
            "new_scoring_authorized": False,
            "next_step": "C0 may be closed after reviewer-facing inspection of this zero-call artifact.",
        }

    audit_json = out_dir / "A13_C0_V2_1_DEEP_AUDIT.json"
    write_json(audit_json, audit)

    # Full task-level census, regenerated from source/frozen artifacts.
    task_census_csv = out_dir / "A13_C0_V2_1_TASK_CENSUS.csv"
    orig_by_task = collections.defaultdict(list)
    for d in tax_decisions:
        orig_by_task[(d["suite"], d["user_task"])].append(d)
    broad_by_task = collections.defaultdict(list)
    for r in broad_rows:
        broad_by_task[(r["suite"], r["user_task"])].append(r)

    task_fields = [
        "suite", "user_task", "task_key", "development",
        "frozen_n_privileged_calls", "frozen_n_taxonomy_decisions",
        "frozen_n_classifiable_decisions", "frozen_n_unclassifiable_decisions",
        "frozen_root_status", "in_protocol", "historical_trajectory_present",
        "frozen_n_valid_decisions", "frozen_n_excluded_decisions",
        "broad_candidate_actions", "broad_classifiable_actions",
        "broad_unclassifiable_actions", "broad_new_actions_missed_by_frozen_rule",
        "broad_screen_root_status",
    ]
    with task_census_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=task_fields)
        w.writeheader()
        for t in sorted(inv, key=lambda x: (x["suite"], x["user_task"])):
            tk = (t["suite"], t["user_task"])
            ods = orig_by_task.get(tk, [])
            ocls = [d for d in ods if d["label"] in CLASS_LABELS]
            oun = [d for d in ods if d["label"] not in CLASS_LABELS]
            ors = [record_by_id[d["decision_id"]] for d in ocls if d["decision_id"] in record_by_id]
            if t["development"]:
                frozen_root = "development_exclusion"
            elif t["n_privileged_calls"] == 0:
                frozen_root = "no_privileged_ground_truth_action_under_frozen_rule"
            elif not ocls:
                frozen_root = "privileged_but_unclassifiable_under_frozen_rule"
            else:
                frozen_root = "classifiable_confirmatory_task_under_frozen_rule"

            brs = broad_by_task.get(tk, [])
            bcls = [r for r in brs if r["label"] in CLASS_LABELS]
            bun = [r for r in brs if r["label"] not in CLASS_LABELS]
            bmiss = [r for r in brs if not r["frozen_rule_privileged"]]
            if t["development"]:
                broad_root = "development_exclusion"
            elif not brs:
                broad_root = "no_nonreadonly_ground_truth_action"
            elif not bcls:
                broad_root = "broad_candidate_but_unclassifiable"
            else:
                broad_root = "broad_classifiable_candidate_task"

            w.writerow({
                "suite": t["suite"],
                "user_task": t["user_task"],
                "task_key": f"{t['suite']}/{t['user_task']}",
                "development": bool(t["development"]),
                "frozen_n_privileged_calls": t["n_privileged_calls"],
                "frozen_n_taxonomy_decisions": len(ods),
                "frozen_n_classifiable_decisions": len(ocls),
                "frozen_n_unclassifiable_decisions": len(oun),
                "frozen_root_status": frozen_root,
                "in_protocol": tk in protocol_tasks,
                "historical_trajectory_present": tk in trajectory_tasks,
                "frozen_n_valid_decisions": sum(bool(r.get("primary_valid")) for r in ors),
                "frozen_n_excluded_decisions": sum(not bool(r.get("primary_valid")) for r in ors),
                "broad_candidate_actions": len(brs),
                "broad_classifiable_actions": len(bcls),
                "broad_unclassifiable_actions": len(bun),
                "broad_new_actions_missed_by_frozen_rule": len(bmiss),
                "broad_screen_root_status": broad_root,
            })

    # Original frozen taxonomy decision census (all 77, including development/unclassifiable).
    original_decision_csv = out_dir / "A13_C0_V2_1_ORIGINAL_DECISION_CENSUS.csv"
    original_fields = [
        "suite", "user_task", "decision_id", "privileged_call_index", "privileged_fn",
        "development", "specified_fraction", "label", "classifiable", "in_protocol_task",
        "record_present", "primary_valid", "primary_exclusion_reason",
    ]
    with original_decision_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=original_fields)
        w.writeheader()
        for d in sorted(tax_decisions, key=lambda x: (x["suite"], x["user_task"], x["privileged_call_index"])):
            rec = record_by_id.get(d["decision_id"])
            tk = (d["suite"], d["user_task"])
            w.writerow({
                "suite": d["suite"],
                "user_task": d["user_task"],
                "decision_id": d["decision_id"],
                "privileged_call_index": d["privileged_call_index"],
                "privileged_fn": d["privileged_fn"],
                "development": bool(d["development"]),
                "specified_fraction": d["specified_fraction"],
                "label": d["label"],
                "classifiable": d["label"] in CLASS_LABELS,
                "in_protocol_task": tk in protocol_tasks,
                "record_present": rec is not None,
                "primary_valid": "" if rec is None else bool(rec.get("primary_valid")),
                "primary_exclusion_reason": "" if rec is None else (rec.get("primary_exclusion_reason") or ""),
            })

    # Independent broad-screen decision census (all candidate non-readonly GT actions).
    broad_decision_csv = out_dir / "A13_C0_V2_1_BROAD_SCREEN_DECISION_CENSUS.csv"
    broad_fields = [
        "suite", "user_task", "task_key", "development", "ground_truth_call_index",
        "function", "frozen_rule_privileged", "newly_missed_by_frozen_rule",
        "specified_fraction", "label", "classifiable", "in_protocol_task",
        "historical_trajectory_present",
    ]
    with broad_decision_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=broad_fields)
        w.writeheader()
        for r in sorted(broad_rows, key=lambda x: (x["suite"], x["user_task"], x["ground_truth_call_index"])):
            tk = (r["suite"], r["user_task"])
            w.writerow({
                "suite": r["suite"],
                "user_task": r["user_task"],
                "task_key": r["task_key"],
                "development": r["development"],
                "ground_truth_call_index": r["ground_truth_call_index"],
                "function": r["function"],
                "frozen_rule_privileged": r["frozen_rule_privileged"],
                "newly_missed_by_frozen_rule": not r["frozen_rule_privileged"],
                "specified_fraction": r["specified_fraction"],
                "label": r["label"],
                "classifiable": r["label"] in CLASS_LABELS,
                "in_protocol_task": tk in protocol_tasks,
                "historical_trajectory_present": tk in trajectory_tasks,
            })

    # Label x terminal-reason matrix from the immutable historical records.
    reason_matrix_csv = out_dir / "A13_C0_V2_1_LABEL_REASON_MATRIX.csv"
    reasons = sorted({r.get("primary_exclusion_reason") or "valid" for r in records})
    with reason_matrix_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["label"] + reasons)
        w.writeheader()
        for lab in sorted(CLASS_LABELS):
            rr = [r for r in records if r["label"] == lab]
            c = collections.Counter(r.get("primary_exclusion_reason") or "valid" for r in rr)
            row = {"label": lab}
            row.update({reason: c.get(reason, 0) for reason in reasons})
            w.writerow(row)

    # Candidate CSV — one row per missed nondevelopment GT action.
    candidate_csv = out_dir / "A13_C0_V2_1_MISSED_CANDIDATES.csv"
    fields = [
        "suite", "user_task", "task_key", "development", "ground_truth_call_index",
        "function", "specified_fraction", "label", "historical_a13_trajectory_present",
        "pre_score_structural_status", "mapped_in_saved_trajectory", "actual_message_index",
        "actual_total_calls_in_turn", "trajectory_utility", "source_file", "source_line",
        "source_docstring_first_line", "args_json", "actual_call_json",
    ]
    with candidate_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in missed_nondev:
            hits = r.get("source_definition", {}).get("hits") or []
            src = hits[0] if len(hits) == 1 else {}
            w.writerow({
                "suite": r["suite"],
                "user_task": r["user_task"],
                "task_key": r["task_key"],
                "development": r["development"],
                "ground_truth_call_index": r["ground_truth_call_index"],
                "function": r["function"],
                "specified_fraction": r["specified_fraction"],
                "label": r["label"],
                "historical_a13_trajectory_present": r.get("historical_a13_trajectory_present"),
                "pre_score_structural_status": r.get("pre_score_structural_status"),
                "mapped_in_saved_trajectory": r.get("mapped_in_saved_trajectory"),
                "actual_message_index": r.get("actual_message_index"),
                "actual_total_calls_in_turn": r.get("actual_total_calls_in_turn"),
                "trajectory_utility": r.get("trajectory_utility"),
                "source_file": src.get("relative_file"),
                "source_line": src.get("line"),
                "source_docstring_first_line": src.get("docstring_first_line"),
                "args_json": json.dumps(r.get("args") or {}, sort_keys=True, ensure_ascii=False),
                "actual_call_json": json.dumps(r.get("actual_call"), sort_keys=True, ensure_ascii=False) if r.get("actual_call") else "",
            })

    function_csv = out_dir / "A13_C0_V2_1_FUNCTION_COVERAGE.csv"
    with function_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "function", "ground_truth_occurrences", "frozen_rule_privileged",
            "broad_non_readonly_screen", "source_file", "source_line", "source_docstring_first_line",
        ])
        w.writeheader()
        for fn in sorted(function_audit):
            d = function_audit[fn]
            hits = d["source_definition"].get("hits") or []
            src = hits[0] if len(hits) == 1 else {}
            w.writerow({
                "function": fn,
                "ground_truth_occurrences": d["ground_truth_occurrences"],
                "frozen_rule_privileged": d["frozen_rule_privileged"],
                "broad_non_readonly_screen": d["broad_non_readonly_screen"],
                "source_file": src.get("relative_file"),
                "source_line": src.get("line"),
                "source_docstring_first_line": src.get("docstring_first_line"),
            })

    # Hash all primary audit outputs.
    manifest_path = out_dir / "FINAL_SHA256.txt"
    output_files = [
        audit_json, task_census_csv, original_decision_csv, broad_decision_csv,
        reason_matrix_csv, candidate_csv, function_csv,
    ]
    manifest_path.write_text(
        "".join(f"{sha256_file(p)}  {p.name}\n" for p in output_files),
        encoding="utf-8",
    )

    print("A13-C0 V2.1 DEEP ZERO-CALL AUDIT COMPLETE")
    print(f"historical hashes: PASS ({len(EXPECTED)}/{len(EXPECTED)})")
    print(f"live AgentDojo: {installed_version}")
    print(f"live taxonomy rebuild exact match: {rebuilt_exact_match}")
    print(f"source v1 user tasks: {sum(len(source_ids[s]) for s in suites)}")
    print("original frozen-rule flow:")
    print(
        f"  {len(inv)} total -> {len(untouched)} untouched -> {len(priv_tasks)} frozen-rule privileged tasks "
        f"-> {len(nondev_dec)} decisions -> {len(class_dec)} classifiable -> {len(valid_records)} valid"
    )
    print(f"original protocol/classifiable task diff: {len(protocol_tasks ^ class_tasks)}")
    print(f"original protocol/trajectory task diff: {len(protocol_tasks ^ trajectory_tasks)}")
    print(f"independent pre-score reconstruction: {dict(sorted(reconstructed_pre_score.items()))}")
    print("extraction-rule coverage screen:")
    print(f"  unique GT functions: {len(function_counts)}")
    print(f"  missed unique non-readonly functions: {sorted({r['function'] for r in missed_rows})}")
    print(f"  missed nondevelopment decisions: {len(missed_nondev)}")
    print(f"  missed nondevelopment classifiable decisions: {len(missed_nondev_classifiable)}")
    print(f"  affected nondevelopment tasks: {len({(r['suite'],r['user_task']) for r in missed_nondev})}")
    print(f"broad-screen structural flow: {extraction_rule_audit['broad_screen_flow']}")
    for r in missed_nondev:
        print(
            "  CANDIDATE "
            f"{r['task_key']} gt_call={r['ground_truth_call_index']} fn={r['function']} "
            f"label={r['label']} frac={r['specified_fraction']} "
            f"traj={r.get('historical_a13_trajectory_present')} "
            f"pre_score={r.get('pre_score_structural_status')}"
        )
    print("BRANCH:", audit["c0_v2_branch"]["decision"])
    print("NEW SCORING AUTHORIZED: NO")
    print("OUTPUT_DIR:", out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
