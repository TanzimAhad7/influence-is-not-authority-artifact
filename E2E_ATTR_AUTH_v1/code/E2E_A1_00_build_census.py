#!/usr/bin/env python3
"""E2E-ATTR-AUTH v1 Phase 0-2 zero-call census producer.

Prospective protocol: USENIX27_FINAL_EXPERIMENT_FREEZE_E2E_ATTRIGUARD_v4_FINAL_CODING_FREEZE_RECONCILED.md

This script performs ONLY pre-outcome input-side work:
  * reproduces the corrected A13/C0 73-row / 29-primary-decision / 25-task census;
  * deterministically selects at most one A13 primary-valid decision per natural user task;
  * statically parses AgentDojo 0.1.35 benchmark-v1 injection-task ground-truth calls;
  * enumerates exact same-function ALT candidates;
  * applies the frozen deterministic ranking components that are mechanically decidable;
  * writes a preliminary cohort census and explicit pending gates.

It performs NO model/provider calls and does NOT decide semantic authorization, pure-explicit-
delegation scope, or multi-call independent-effect feasibility. Those remain Phase 3 gates.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EXPECTED_AGENTDOJO_VERSION = "0.1.35"
EXPECTED_BENCHMARK_VERSION = "v1"
EXPECTED_A13_ROWS = 73
EXPECTED_PRIMARY_VALID_DECISIONS = 29
EXPECTED_PRIMARY_VALID_TASKS = 25
SUITES = ("banking", "slack", "travel", "workspace")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(canonical_json(row) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def parse_agentdojo_version(pip_show: Path) -> str:
    for line in pip_show.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("Version:"):
            return line.split(":", 1)[1].strip()
    raise ValueError(f"Version line not found in {pip_show}")


def get_literal_string(expr: ast.AST) -> str | None:
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    return None


def find_method(node: ast.ClassDef, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    for stmt in node.body:
        if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)) and stmt.name == name:
            return stmt
    return None


def extract_goal_source(class_node: ast.ClassDef, source: str) -> str | None:
    for stmt in class_node.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "GOAL":
                    return ast.get_source_segment(source, stmt.value)
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == "GOAL":
            return ast.get_source_segment(source, stmt.value) if stmt.value else None
    return None


@dataclass(frozen=True)
class InjectionCall:
    suite: str
    injection_task_id: int
    injection_task_key: str
    malicious_call_index: int
    total_malicious_calls: int
    function: str
    class_name: str
    class_lineno: int
    call_lineno: int
    source_relpath: str
    source_sha256: str
    goal_source: str | None
    call_source: str


def parse_injection_calls(v1_dir: Path) -> list[InjectionCall]:
    out: list[InjectionCall] = []
    for suite in SUITES:
        path = v1_dir / suite / "injection_tasks.py"
        if not path.exists():
            raise FileNotFoundError(path)
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        file_sha = sha256_file(path)
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            m = re.fullmatch(r"InjectionTask(\d+)", node.name)
            if not m:
                continue
            task_id = int(m.group(1))
            gt = find_method(node, "ground_truth")
            calls: list[tuple[ast.Call, str]] = []
            if gt is not None:
                for sub in ast.walk(gt):
                    if not isinstance(sub, ast.Call):
                        continue
                    if not isinstance(sub.func, ast.Name) or sub.func.id != "FunctionCall":
                        continue
                    fn = None
                    for kw in sub.keywords:
                        if kw.arg == "function":
                            fn = get_literal_string(kw.value)
                            break
                    if fn is None:
                        raise ValueError(
                            f"Non-literal FunctionCall.function in {path}:{getattr(sub, 'lineno', '?')}"
                        )
                    calls.append((sub, fn))
            calls.sort(key=lambda x: (x[0].lineno, x[0].col_offset))
            total = len(calls)
            goal_source = extract_goal_source(node, source)
            for idx, (call, fn) in enumerate(calls):
                out.append(
                    InjectionCall(
                        suite=suite,
                        injection_task_id=task_id,
                        injection_task_key=f"injection_task_{task_id}",
                        malicious_call_index=idx,
                        total_malicious_calls=total,
                        function=fn,
                        class_name=node.name,
                        class_lineno=node.lineno,
                        call_lineno=call.lineno,
                        source_relpath=f"{suite}/injection_tasks.py",
                        source_sha256=file_sha,
                        goal_source=goal_source,
                        call_source=ast.get_source_segment(source, call) or "",
                    )
                )
    return out


def load_a13(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            row["_source_lineno"] = lineno
            rows.append(row)
    return rows


def select_one_decision_per_task(primary: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in primary:
        grouped[row["task_key"]].append(row)
    selected = []
    unselected: dict[str, list[str]] = {}
    for task_key in sorted(grouped):
        rows = sorted(
            grouped[task_key],
            key=lambda r: (int(r.get("privileged_call_index", 10**9)), str(r["decision_id"])),
        )
        selected.append(rows[0])
        if len(rows) > 1:
            unselected[task_key] = [r["decision_id"] for r in rows[1:]]
    return selected, unselected


def rank_candidate(c: InjectionCall) -> tuple[int, int, int]:
    # Frozen mechanically decidable ranking terms. Independent-effect feasibility is a later
    # pre-outcome source/oracle gate and MUST NOT be guessed here for multi-call candidates.
    single_call_rank = 0 if c.total_malicious_calls == 1 else 1
    return (single_call_rank, c.injection_task_id, c.malicious_call_index)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a13-combined", required=True, type=Path)
    ap.add_argument("--agentdojo-v1-dir", required=True, type=Path)
    ap.add_argument("--agentdojo-pip-show", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--protocol", type=Path)
    ap.add_argument("--canonical", type=Path)
    ap.add_argument("--blueprint", type=Path)
    ap.add_argument("--writing-diagnosis", type=Path)
    args = ap.parse_args()

    out = args.out_dir
    out.mkdir(parents=True, exist_ok=True)

    # Phase 0 source/version lock.
    version = parse_agentdojo_version(args.agentdojo_pip_show)
    if version != EXPECTED_AGENTDOJO_VERSION:
        raise SystemExit(f"FAIL: AgentDojo version {version!r} != {EXPECTED_AGENTDOJO_VERSION!r}")

    a13_rows = load_a13(args.a13_combined)
    primary = [r for r in a13_rows if r.get("primary_valid") is True]
    primary_tasks = sorted({r["task_key"] for r in primary})
    gates = {
        "a13_rows_exact_73": len(a13_rows) == EXPECTED_A13_ROWS,
        "primary_valid_decisions_exact_29": len(primary) == EXPECTED_PRIMARY_VALID_DECISIONS,
        "primary_valid_tasks_exact_25": len(primary_tasks) == EXPECTED_PRIMARY_VALID_TASKS,
        "agentdojo_version_exact_0_1_35": version == EXPECTED_AGENTDOJO_VERSION,
        "benchmark_version_forced_v1": args.agentdojo_v1_dir.name == EXPECTED_BENCHMARK_VERSION,
    }
    if not all(gates.values()):
        raise SystemExit(f"FAIL Phase 1 hard gate: {gates}")

    selected, unselected = select_one_decision_per_task(primary)
    injection_calls = parse_injection_calls(args.agentdojo_v1_dir)
    calls_by_suite_fn: dict[tuple[str, str], list[InjectionCall]] = defaultdict(list)
    for c in injection_calls:
        calls_by_suite_fn[(c.suite, c.function)].append(c)

    # Full candidate enumeration and preliminary one-row-per-task census.
    alt_candidate_rows: list[dict[str, Any]] = []
    cohort_rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    strict_rows: list[dict[str, Any]] = []

    for r in sorted(selected, key=lambda x: x["task_key"]):
        matches = sorted(calls_by_suite_fn.get((r["suite"], r["privileged_fn"]), []), key=rank_candidate)
        for c in matches:
            alt_candidate_rows.append(
                {
                    "task_key": r["task_key"],
                    "decision_id": r["decision_id"],
                    "suite": r["suite"],
                    "user_task": r["user_task"],
                    "a13_label": r["label"],
                    "privileged_call_index": r["privileged_call_index"],
                    "privileged_fn": r["privileged_fn"],
                    "actual_call_json": canonical_json(r.get("actual_call")),
                    **asdict(c),
                    "single_call_objective": c.total_malicious_calls == 1,
                    "mechanical_rank": repr(rank_candidate(c)),
                    "independent_effect_gate": (
                        "AUTO_PASS_SINGLE_CALL" if c.total_malicious_calls == 1 else "PENDING_SOURCE_ORACLE_AUDIT"
                    ),
                    "attriguard_scope_gate": "PENDING_BLINDED_SCOPE_AUDIT",
                }
            )

        base = {
            "task_key": r["task_key"],
            "decision_id": r["decision_id"],
            "suite": r["suite"],
            "user_task": r["user_task"],
            "a13_label": r["label"],
            "specified_fraction": r.get("specified_fraction"),
            "privileged_call_index": r["privileged_call_index"],
            "privileged_fn": r["privileged_fn"],
            "actual_call_json": canonical_json(r.get("actual_call")),
            "a13_source_lineno": r["_source_lineno"],
            "unselected_same_task_decisions": ";".join(unselected.get(r["task_key"], [])),
        }
        if not matches:
            row = {
                **base,
                "preliminary_status": "EXCLUDE_NO_SAME_FUNCTION_ALT",
                "exclusion_reason": "NO_SAME_FUNCTION_ALT_IN_AGENTDOJO_V1",
                "selected_injection_task_id": "",
                "selected_malicious_call_index": "",
                "selected_total_malicious_calls": "",
                "strict_single_call": False,
                "independent_effect_gate": "NOT_APPLICABLE",
                "attriguard_scope_gate": "NOT_APPLICABLE",
            }
            cohort_rows.append(row)
            exclusions.append(row)
            continue

        top = matches[0]
        independent_gate = "AUTO_PASS_SINGLE_CALL" if top.total_malicious_calls == 1 else "PENDING_SOURCE_ORACLE_AUDIT"
        row = {
            **base,
            "preliminary_status": (
                "PRELIMINARY_RETAINED" if top.total_malicious_calls == 1 else "PENDING_MULTI_CALL_INDEPENDENT_EFFECT_AUDIT"
            ),
            "exclusion_reason": "",
            "selected_injection_task_id": top.injection_task_id,
            "selected_injection_task_key": top.injection_task_key,
            "selected_malicious_call_index": top.malicious_call_index,
            "selected_total_malicious_calls": top.total_malicious_calls,
            "selected_alt_function": top.function,
            "selected_alt_call_source": top.call_source,
            "selected_injection_source_relpath": top.source_relpath,
            "selected_injection_source_sha256": top.source_sha256,
            "strict_single_call": top.total_malicious_calls == 1,
            "independent_effect_gate": independent_gate,
            "attriguard_scope_gate": "PENDING_BLINDED_SCOPE_AUDIT",
        }
        cohort_rows.append(row)
        if row["strict_single_call"]:
            strict_rows.append(row)

    # These are deliberately preliminary counts. Final B is frozen only after Phase 3.
    same_fn_tasks = [r for r in cohort_rows if r["preliminary_status"] != "EXCLUDE_NO_SAME_FUNCTION_ALT"]
    strict_tasks = [r for r in same_fn_tasks if r["strict_single_call"]]
    pending_multi = [r for r in same_fn_tasks if r["independent_effect_gate"] == "PENDING_SOURCE_ORACLE_AUDIT"]

    suite_counts = Counter(r["suite"] for r in same_fn_tasks)
    label_counts = Counter(r["a13_label"] for r in same_fn_tasks)
    fn_counts = Counter(r["privileged_fn"] for r in same_fn_tasks)

    census_fields = [
        "task_key","decision_id","suite","user_task","a13_label","specified_fraction",
        "privileged_call_index","privileged_fn","actual_call_json","a13_source_lineno",
        "unselected_same_task_decisions","preliminary_status","exclusion_reason",
        "selected_injection_task_id","selected_injection_task_key","selected_malicious_call_index",
        "selected_total_malicious_calls","selected_alt_function","selected_alt_call_source",
        "selected_injection_source_relpath","selected_injection_source_sha256","strict_single_call",
        "independent_effect_gate","attriguard_scope_gate",
    ]
    write_csv(out / "COHORT_CENSUS.csv", cohort_rows, census_fields)
    write_csv(out / "EXCLUSIONS.csv", exclusions, census_fields)
    write_csv(out / "STRICT_SUBSET.csv", strict_rows, census_fields)
    write_jsonl(out / "02_ALT_CANDIDATES.jsonl", alt_candidate_rows)

    primary_export = []
    for r in sorted(primary, key=lambda x: (x["task_key"], x["decision_id"])):
        primary_export.append({k: v for k, v in r.items() if k != "_source_lineno"})
    write_jsonl(out / "01_A13_PRIMARY_DECISIONS.jsonl", primary_export)

    a13_report = {
        "status": "PASS",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "a13_combined_path": str(args.a13_combined),
        "a13_combined_sha256": sha256_file(args.a13_combined),
        "n_combined_rows": len(a13_rows),
        "n_primary_valid_decisions": len(primary),
        "n_primary_valid_tasks": len(primary_tasks),
        "suite_counts_primary_decisions": dict(sorted(Counter(r["suite"] for r in primary).items())),
        "label_counts_primary_decisions": dict(sorted(Counter(r["label"] for r in primary).items())),
        "gates": gates,
    }
    write_json(out / "01_A13_CENSUS_REPORT.json", a13_report)

    summary = {
        "status": "PHASE_0_2_COMPLETE__PHASE_3_REQUIRED_BEFORE_FINAL_B",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "protocol_phase": "Phase 0-2 / A1 mechanical census preliminary",
        "NO_MODEL_CALLS": True,
        "agentdojo_version": version,
        "benchmark_version": EXPECTED_BENCHMARK_VERSION,
        "n_a13_primary_valid_decisions": len(primary),
        "n_a13_primary_valid_tasks": len(primary_tasks),
        "n_one_decision_per_task_after_frozen_tiebreak": len(selected),
        "n_tasks_with_same_function_alt_candidate": len(same_fn_tasks),
        "n_strict_single_call_preliminary": len(strict_tasks),
        "n_pending_multi_call_independent_effect_audit": len(pending_multi),
        "n_no_same_function_excluded": len(exclusions),
        "suite_counts_same_function_candidate_tasks": dict(sorted(suite_counts.items())),
        "a13_label_counts_same_function_candidate_tasks": dict(sorted(label_counts.items())),
        "privileged_function_counts_same_function_candidate_tasks": dict(sorted(fn_counts.items())),
        "FINAL_B": None,
        "minimum_size_gate_evaluable_now": False,
        "why_final_B_not_frozen": [
            "multi-call selected ALT candidates still require independent-effect/source-oracle audit",
            "AttriGuard pure-explicit-delegation scope requires blinded Phase 3 validation",
            "AUTH/ALT semantic validation not yet completed",
        ],
        "next_required_phase": "Phase 3 threat-model + blinded authorization/effect audit",
    }
    write_json(out / "COHORT_SUMMARY.json", summary)

    locks: list[dict[str, Any]] = []
    for label, path in [
        ("a13_combined", args.a13_combined),
        ("agentdojo_pip_show", args.agentdojo_pip_show),
        ("protocol", args.protocol),
        ("canonical", args.canonical),
        ("blueprint", args.blueprint),
        ("writing_diagnosis", args.writing_diagnosis),
    ]:
        if path is not None:
            locks.append({"label": label, "path": str(path), "sha256": sha256_file(path)})
    for suite in SUITES:
        for filename in ("injection_tasks.py", "user_tasks.py", "task_suite.py"):
            path = args.agentdojo_v1_dir / suite / filename
            locks.append({"label": f"agentdojo_v1_{suite}_{filename}", "path": str(path), "sha256": sha256_file(path)})
    write_json(out / "00_PROJECT_SNAPSHOT.json", {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "NO_MODEL_CALLS": True,
        "locks": locks,
        "agentdojo_version": version,
        "benchmark_version": EXPECTED_BENCHMARK_VERSION,
    })

    # Output manifest over generated outputs (script hash is recorded separately by caller/runtime).
    generated = sorted(p for p in out.iterdir() if p.is_file() and p.name != "OUTPUT_SHA256.tsv")
    with (out / "OUTPUT_SHA256.tsv").open("w", encoding="utf-8") as f:
        f.write("sha256\tbytes\tfilename\n")
        for p in generated:
            f.write(f"{sha256_file(p)}\t{p.stat().st_size}\t{p.name}\n")

    print("PASS Phase 0-2 zero-call census")
    print(f"A13 primary: {len(primary)} decisions / {len(primary_tasks)} tasks")
    print(f"same-function candidate tasks: {len(same_fn_tasks)}")
    print(f"strict single-call preliminary: {len(strict_tasks)}")
    print(f"multi-call pending source/oracle audit: {len(pending_multi)}")
    print(f"no-same-function exclusions: {len(exclusions)}")
    print("FINAL B NOT YET FROZEN; Phase 3 required")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
