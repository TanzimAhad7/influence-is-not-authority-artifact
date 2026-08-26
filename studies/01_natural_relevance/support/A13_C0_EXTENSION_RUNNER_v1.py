#!/usr/bin/env python3
"""
A13-C0 EXTENSION RUNNER v1
==========================

Purpose
-------
Execute ONLY the four A13-C0 coverage-correction decisions prospectively frozen
in A13_C0_EXTENSION_PREFREEZE_v1. Historical A13 artifacts are immutable.

Two-stage use
-------------
1) --mode preflight
   * verifies all controlling hashes and the exact historical A13 implementation
   * verifies AgentDojo v1 / package 0.1.35 and the Qwen server
   * re-derives the four frozen rows from the benchmark source
   * performs ONE synthetic/non-scientific scorer endpoint self-test
   * performs ZERO target-task agent runs and ZERO target-task attribution scores
   * writes a runner-freeze package

2) --mode science
   * requires the exact runner-freeze JSON SHA-256 supplied by the author after
     preflight review
   * runs exactly three fresh no-injection AgentDojo tasks
   * reuses the exact historical trajectory for workspace/user_task_13
   * applies the unchanged historical A13 mapping/utility/multi-tool/span rules
   * scores only newly recognized decisions that reach the historical scoring stage
   * writes a separate append-only extension ledger and a derived combined analysis
   * NEVER overwrites historical a13/ artifacts

Scientific authorship
---------------------
This script is intended for the researcher to run on the research server. Any
model/scorer results used in the paper must come from that author-run execution,
with stdout/artifacts/hashes preserved.
"""

from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import hashlib
import importlib.metadata
import importlib.util
import json
import math
import os
import shutil
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any

# -----------------------------------------------------------------------------
# Frozen controlling constants
# -----------------------------------------------------------------------------
EXPECTED_AGENTDOJO_VERSION = "0.1.35"
BENCHMARK_VERSION = "v1"
SCORER_MODEL = "Qwen/Qwen2.5-72B-Instruct"
SCORER_BASE_URL = "http://localhost:8100/v1"
SCORER_API_KEY = "x"
HTTP_TIMEOUT = 180

EXPECTED_INPUT_BUNDLE_SHA256 = "3e6aaae53bfe10c57156c41def0dd13b3ada05ec299b5803a52bf586082984a2"
EXPECTED_HISTORICAL_ZIP_SHA256 = "d4b48c9bde17602e47c2d2feea3f17ee5f2ba6f090395b011b3e84bc3fabc327"
EXPECTED_C0_V21_AUTHOR_ARCHIVE_SHA256 = "bacedba13f854aebd3168ad020b5123ec889a870d5c03cd1c7f519f0daccd495"
EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256 = "035af5fb370cef996739ec6b99db24e9be66a446050779a5c26242fcdda2396d"

EXPECTED_HISTORICAL_A13_SOURCE_SHA256 = "f771850375b4f5af7bc2cec6a4e166057f33fab26d686320b8ef2d8d32557f05"
EXPECTED_HISTORICAL_PROTOCOL_SHA256 = "8c0caa2e509f94d0e2eea37cfaf53840319d407167c15e2a052633c53854de43"
EXPECTED_HISTORICAL_TAXONOMY_SHA256 = "02894700c2ff370b28b858a6f533805c37fd11d86bb1c70af3b71ac21cdc674b"
EXPECTED_HISTORICAL_DECISIONS_SHA256 = "af6a62c5689e7d26180f0091a121839b645e1dcb54e5aaf87427f6e75c19dca9"
EXPECTED_HISTORICAL_RESULTS_SHA256 = "6ced3fc14a60574f95881344ac3d6bb5b8cf7d88d59ac3c844cae35d4121646b"
EXPECTED_HISTORICAL_PROTOCOL_HASH = "b4a140c7d8ef49149ac72e35e9e52405f614fa5361558c7b2ac0c56fe0063b80"
EXPECTED_HISTORICAL_TAXONOMY_HASH = "213cd71e0017eeb91c52955f8b77d06455c8d280b0121b31a830aa651ae62740"
EXPECTED_TASK13_LOG_SHA256 = "bbdec872e3afbaea390bd970dca75a2813235b741f188d984d6963a4b70424f2"

EXPECTED_PREFREEZE_SCRIPT_SHA256 = "deb8a79b72ba27c11a8957bbeb108cb70f3b62316fb871bd13f0cb31eaba64a9"
EXPECTED_PREFREEZE_FREEZE_JSON_SHA256 = "41ce8878845184e4306a7817c490f1d679999475b3cae2f5512d7ec66595624c"
EXPECTED_PREFREEZE_FREEZE_BODY_SHA256 = "a5be8ba9246fae22eb8caa3ef541f0a88dc14ff2d0f87e39e469cf55f187fdd4"

ADDED_PRIVILEGED_FUNCTIONS = frozenset({"append_to_file", "reschedule_calendar_event"})
DEVELOPMENT_TASKS = frozenset({
    ("workspace", "user_task_19"),
    ("slack", "user_task_20"),
    ("travel", "user_task_19"),
})

# Exact pre-outcome extension population frozen by A13-C0 prefreeze v1.
# ground_truth_call_index is the index in the COMPLETE GT call sequence, not the
# historical privileged-only index. Historical decision IDs are never renumbered.
EXTENSION_TARGETS = [
    {
        "extension_decision_id": "workspace/user_task_13/c0ext_gt2/append_to_file",
        "suite": "workspace",
        "user_task": "user_task_13",
        "ground_truth_call_index": 2,
        "function": "append_to_file",
        "label": "DELEGATED",
        "specified_fraction": 0.0,
        "execution_mode": "REUSE_EXACT_HISTORICAL_A13_TRAJECTORY__NEW_ATTRIBUTION_ONLY",
    },
    {
        "extension_decision_id": "workspace/user_task_29/c0ext_gt1/append_to_file",
        "suite": "workspace",
        "user_task": "user_task_29",
        "ground_truth_call_index": 1,
        "function": "append_to_file",
        "label": "SPECIFIED",
        "specified_fraction": 1.0,
        "execution_mode": "ONE_FRESH_HISTORICAL_A13_NO_INJECTION_AGENT_RUN__THEN_UNCHANGED_ELIGIBILITY",
    },
    {
        "extension_decision_id": "workspace/user_task_34/c0ext_gt2/append_to_file",
        "suite": "workspace",
        "user_task": "user_task_34",
        "ground_truth_call_index": 2,
        "function": "append_to_file",
        "label": "DELEGATED",
        "specified_fraction": 0.0,
        "execution_mode": "ONE_FRESH_HISTORICAL_A13_NO_INJECTION_AGENT_RUN__THEN_UNCHANGED_ELIGIBILITY",
    },
    {
        "extension_decision_id": "workspace/user_task_7/c0ext_gt1/reschedule_calendar_event",
        "suite": "workspace",
        "user_task": "user_task_7",
        "ground_truth_call_index": 1,
        "function": "reschedule_calendar_event",
        "label": "SPECIFIED",
        "specified_fraction": 1.0,
        "execution_mode": "ONE_FRESH_HISTORICAL_A13_NO_INJECTION_AGENT_RUN__THEN_UNCHANGED_ELIGIBILITY",
    },
]

FRESH_AGENT_TASK_ORDER = ["user_task_29", "user_task_34", "user_task_7"]
HISTORICAL_REUSE_TASK = "user_task_13"

RUNNER_FREEZE_DIRNAME = "A13_C0_EXTENSION_RUNNER_FREEZE_v1"
SCIENCE_DIRNAME = "A13_C0_EXTENSION_SCIENCE_v1"
RUNNER_FREEZE_FILENAME = "A13_C0_EXTENSION_RUNNER_FREEZE_v1.json"

# -----------------------------------------------------------------------------
# Generic helpers
# -----------------------------------------------------------------------------
def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def json_safe(x: Any):
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, float) and not math.isfinite(x):
        return None
    if isinstance(x, dict):
        return {str(k): json_safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [json_safe(v) for v in x]
    return x


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(obj), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def fatal(msg: str) -> None:
    raise SystemExit(f"FATAL: {msg}")


def require(cond: bool, msg: str) -> None:
    if not cond:
        fatal(msg)


def verify_file_hash(path: Path, expected: str, label: str) -> str:
    require(path.exists(), f"missing {label}: {path}")
    got = sha256_file(path)
    require(got == expected, f"{label} SHA-256 mismatch: got {got}, expected {expected}")
    return got


def unique_suffix_name(names: list[str], suffix: str, container_label: str) -> str:
    hits = [n for n in names if n == suffix or n.endswith("/" + suffix)]
    require(len(hits) == 1, f"{container_label}: expected exactly one member ending {suffix!r}, got {hits}")
    return hits[0]


def read_zip_suffix(zpath: Path, suffix: str) -> bytes:
    with zipfile.ZipFile(zpath, "r") as z:
        name = unique_suffix_name(z.namelist(), suffix, str(zpath))
        return z.read(name)


def read_tar_suffix(tpath: Path, suffix: str) -> bytes:
    with tarfile.open(tpath, "r:gz") as t:
        names = [m.name for m in t.getmembers() if m.isfile()]
        name = unique_suffix_name(names, suffix, str(tpath))
        f = t.extractfile(name)
        require(f is not None, f"cannot extract {name} from {tpath}")
        return f.read()


def write_final_sha256(directory: Path, filenames: list[str]) -> None:
    lines = []
    for name in filenames:
        p = directory / name
        lines.append(f"{sha256_file(p)}  {name}")
    (directory / "FINAL_SHA256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def source_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


# -----------------------------------------------------------------------------
# Load / verify controlling artifacts
# -----------------------------------------------------------------------------
def load_historical(historical_zip: Path) -> dict[str, Any]:
    protocol_b = read_zip_suffix(historical_zip, "a13/protocol.json")
    taxonomy_b = read_zip_suffix(historical_zip, "a13/taxonomy.json")
    decisions_b = read_zip_suffix(historical_zip, "a13/decisions.jsonl")
    results_b = read_zip_suffix(historical_zip, "a13/results.json")
    manifest_b = read_zip_suffix(historical_zip, "a13/manifest.json")
    task13_b = read_zip_suffix(
        historical_zip,
        "a13/agentdojo_runs/vllm_parsed/workspace/user_task_13/none/none.json",
    )

    require(sha256_bytes(protocol_b) == EXPECTED_HISTORICAL_PROTOCOL_SHA256, "historical protocol hash mismatch")
    require(sha256_bytes(taxonomy_b) == EXPECTED_HISTORICAL_TAXONOMY_SHA256, "historical taxonomy hash mismatch")
    require(sha256_bytes(decisions_b) == EXPECTED_HISTORICAL_DECISIONS_SHA256, "historical decisions hash mismatch")
    require(sha256_bytes(results_b) == EXPECTED_HISTORICAL_RESULTS_SHA256, "historical results hash mismatch")
    require(sha256_bytes(task13_b) == EXPECTED_TASK13_LOG_SHA256, "historical workspace/user_task_13 trajectory hash mismatch")

    protocol = json.loads(protocol_b)
    taxonomy = json.loads(taxonomy_b)
    results = json.loads(results_b)
    manifest = json.loads(manifest_b)
    decisions = [json.loads(line) for line in decisions_b.decode("utf-8").splitlines() if line.strip()]
    task13_log = json.loads(task13_b)

    require(protocol.get("protocol_hash") == EXPECTED_HISTORICAL_PROTOCOL_HASH, "historical protocol_hash mismatch")
    require(taxonomy.get("taxonomy_hash") == EXPECTED_HISTORICAL_TAXONOMY_HASH, "historical taxonomy_hash mismatch")
    require(len(decisions) == 69, f"expected 69 historical decision rows, got {len(decisions)}")

    return {
        "protocol": protocol,
        "taxonomy": taxonomy,
        "decisions": decisions,
        "results": results,
        "manifest": manifest,
        "task13_log": task13_log,
        "raw_hashes": {
            "protocol": sha256_bytes(protocol_b),
            "taxonomy": sha256_bytes(taxonomy_b),
            "decisions": sha256_bytes(decisions_b),
            "results": sha256_bytes(results_b),
            "task13_log": sha256_bytes(task13_b),
        },
    }


def load_and_verify_prefreeze(prefreeze_archive: Path) -> dict[str, Any]:
    freeze_b = read_tar_suffix(
        prefreeze_archive,
        "A13_C0_EXTENSION_PREFREEZE_v1/A13_C0_EXTENSION_FREEZE_v1.json",
    )
    script_b = read_tar_suffix(prefreeze_archive, "A13_C0_EXTENSION_PREFREEZE_v1.py")
    require(sha256_bytes(freeze_b) == EXPECTED_PREFREEZE_FREEZE_JSON_SHA256, "prefreeze JSON hash mismatch")
    require(sha256_bytes(script_b) == EXPECTED_PREFREEZE_SCRIPT_SHA256, "prefreeze script hash mismatch")

    freeze = json.loads(freeze_b)
    require(freeze.get("status") == "PREFROZEN__NO_NEW_CANDIDATE_ATTRIBUTION_OUTCOME_INSPECTED", "prefreeze status mismatch")
    require(freeze.get("author_attestation_no_new_candidate_scores_inspected") is True, "prefreeze author attestation missing")
    require(freeze.get("scientific_model_calls_performed_by_this_script") == 0, "prefreeze unexpectedly performed scientific model calls")
    require(freeze.get("scientific_scorer_calls_performed_by_this_script") == 0, "prefreeze unexpectedly performed scientific scorer calls")
    require(freeze.get("freeze_body_sha256") == EXPECTED_PREFREEZE_FREEZE_BODY_SHA256, "prefreeze body hash mismatch")

    frozen_targets = freeze.get("extension_decisions") or []
    require(len(frozen_targets) == 4, f"prefreeze must contain four extension decisions, got {len(frozen_targets)}")
    by_id = {x.get("extension_decision_id"): x for x in frozen_targets}
    require(len(by_id) == 4, "prefreeze extension decision IDs are not unique")
    for exp in EXTENSION_TARGETS:
        got = by_id.get(exp["extension_decision_id"])
        require(got is not None, f"prefreeze missing {exp['extension_decision_id']}")
        for k in ["suite", "user_task", "ground_truth_call_index", "function", "label", "specified_fraction", "execution_mode"]:
            require(got.get(k) == exp[k], f"prefreeze mismatch for {exp['extension_decision_id']} field {k}: {got.get(k)!r} != {exp[k]!r}")
        require(got.get("historical_decision_ids_renumbered") is False, f"prefreeze attempts to renumber historical IDs for {exp['extension_decision_id']}")

    return freeze


def verify_input_bundle(input_bundle_zip: Path, project_a13_path: Path) -> None:
    a13_b = read_zip_suffix(input_bundle_zip, "project_files/A13.py")
    require(sha256_bytes(a13_b) == EXPECTED_HISTORICAL_A13_SOURCE_SHA256, "captured input-bundle A13.py hash mismatch")
    require(project_a13_path.read_bytes() == a13_b, "server A13.py bytes differ from captured historical A13.py")


# -----------------------------------------------------------------------------
# Historical A13 implementation reuse
# -----------------------------------------------------------------------------
def load_historical_a13(project_root: Path):
    path = project_root / "A13.py"
    verify_file_hash(path, EXPECTED_HISTORICAL_A13_SOURCE_SHA256, "historical A13.py")
    spec = importlib.util.spec_from_file_location("a13_historical_exact", path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # Hard-check the scientific constants we are inheriting.
    require(mod.EXPECTED_AGENTDOJO_VERSION == EXPECTED_AGENTDOJO_VERSION, "A13 AgentDojo version constant mismatch")
    require(mod.BENCHMARK_VERSION == BENCHMARK_VERSION, "A13 benchmark version constant mismatch")
    require(mod.SCORER_MODEL == SCORER_MODEL, "A13 scorer model constant mismatch")
    require(mod.SCORER_BASE_URL == SCORER_BASE_URL, "A13 scorer URL constant mismatch")
    require(mod.BOOTSTRAP_B == 5000 and mod.BOOTSTRAP_SEED == 130013, "A13 bootstrap constants mismatch")
    return mod


def server_model_ids() -> list[str]:
    req = urllib.request.Request(
        f"{SCORER_BASE_URL}/models",
        headers={"Authorization": f"Bearer {SCORER_API_KEY}"},
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        d = json.loads(r.read().decode("utf-8"))
    return [x.get("id") for x in d.get("data", []) if isinstance(x, dict)]


def call_to_plain(call) -> dict[str, Any]:
    return {
        "function": str(getattr(call, "function", "")),
        "args": copy.deepcopy(dict(getattr(call, "args", {}) or {})),
    }


def historical_task_inventory_row(historical: dict[str, Any], suite: str, user_task: str) -> dict[str, Any]:
    hits = [
        r for r in historical["taxonomy"].get("task_inventory", [])
        if r.get("suite") == suite and r.get("user_task") == user_task
    ]
    require(len(hits) == 1, f"historical taxonomy task inventory missing/duplicated for {suite}/{user_task}")
    return hits[0]


def derive_target_rows(a13, historical: dict[str, Any]) -> list[dict[str, Any]]:
    from agentdojo.task_suite.load_suites import get_suite

    # Keep the original historical detector as part of the finite overlay.
    historical_is_privileged = a13.is_privileged_fn

    out = []
    for exp in EXTENSION_TARGETS:
        suite = get_suite(BENCHMARK_VERSION, exp["suite"])
        ut = suite.user_tasks[exp["user_task"]]
        base_env = suite.load_and_inject_default_environment({})
        pre_env = ut.init_environment(base_env)
        gt_all = [call_to_plain(c) for c in list(ut.ground_truth(pre_env))]

        hist_inv = historical_task_inventory_row(historical, exp["suite"], exp["user_task"])
        require(gt_all == hist_inv.get("ground_truth_all"), f"installed AgentDojo GT differs from historical frozen GT for {exp['suite']}/{exp['user_task']}")
        prompt = getattr(ut, "PROMPT", "") or ""
        require(a13.sha256_text(prompt) == hist_inv.get("prompt_sha256"), f"prompt hash differs for {exp['suite']}/{exp['user_task']}")

        gi = exp["ground_truth_call_index"]
        require(0 <= gi < len(gt_all), f"GT call index out of range for {exp['extension_decision_id']}")
        target_call = gt_all[gi]
        require(target_call["function"] == exp["function"], f"target function mismatch for {exp['extension_decision_id']}")
        require(not historical_is_privileged(target_call["function"]), f"{exp['function']} is unexpectedly privileged under historical rule")
        require(target_call["function"] in ADDED_PRIVILEGED_FUNCTIONS, f"{exp['function']} not in frozen overlay")

        # Recompute the historical prompt-coverage operationalization exactly.
        prompt_n = a13.normalized_text(prompt)
        chars_matched = 0
        chars_total = 0
        matched = 0
        matchable = 0
        per_arg = {}
        for k, v in target_call["args"].items():
            r = a13.value_in_prompt(v, prompt_n)
            nv = a13.normalized_text(v)
            vlen = len(nv)
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
        label = a13.classify_fraction(frac)
        require(label == exp["label"], f"rederived label mismatch for {exp['extension_decision_id']}: {label} != {exp['label']}")
        require(frac is not None and abs(float(frac) - float(exp["specified_fraction"])) <= 1e-15,
                f"rederived specified_fraction mismatch for {exp['extension_decision_id']}: {frac} != {exp['specified_fraction']}")

        corrected_priv = [
            (idx, c) for idx, c in enumerate(gt_all)
            if historical_is_privileged(c["function"]) or c["function"] in ADDED_PRIVILEGED_FUNCTIONS
        ]
        corrected_pidx = [j for j, (idx, _) in enumerate(corrected_priv) if idx == gi]
        require(len(corrected_pidx) == 1, f"cannot derive corrected privileged index for {exp['extension_decision_id']}")

        out.append({
            **exp,
            "corrected_privileged_call_index": corrected_pidx[0],
            "prompt": prompt,
            "prompt_sha256": a13.sha256_text(prompt),
            "gt_args": target_call["args"],
            "ground_truth_all_sha256": a13.sha256_text(a13.stable_json(gt_all)),
            "args_matched": matched,
            "args_matchable": matchable,
            "chars_matched": chars_matched,
            "chars_total": chars_total,
            "per_arg": per_arg,
            "development": (exp["suite"], exp["user_task"]) in DEVELOPMENT_TASKS,
        })

    require(all(not r["development"] for r in out), "a frozen confirmatory extension target is a development task")
    return out


def make_corrected_gt_rows_for_task(a13, historical: dict[str, Any], target_row: dict[str, Any]) -> list[dict[str, Any]]:
    """Build mapping rows for ALL corrected privileged GT calls in this task.

    This preserves the historical greedy same-function/order mapper. Only the
    frozen extension target is later scored; other rows exist solely to keep the
    mapper's ordering semantics faithful.
    """
    hist_inv = historical_task_inventory_row(historical, target_row["suite"], target_row["user_task"])
    gt_all = hist_inv["ground_truth_all"]
    prompt = hist_inv["prompt"]
    prompt_n = a13.normalized_text(prompt)
    historical_is_privileged = a13._c0_original_is_privileged_fn

    corrected_calls = [
        (gt_idx, c) for gt_idx, c in enumerate(gt_all)
        if historical_is_privileged(c.get("function")) or c.get("function") in ADDED_PRIVILEGED_FUNCTIONS
    ]
    rows = []
    for pidx, (gt_idx, c) in enumerate(corrected_calls):
        chars_matched = 0
        chars_total = 0
        matched = 0
        matchable = 0
        per_arg = {}
        for k, v in (c.get("args") or {}).items():
            r = a13.value_in_prompt(v, prompt_n)
            nv = a13.normalized_text(v)
            vlen = len(nv)
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
        label = a13.classify_fraction(frac)
        if gt_idx == target_row["ground_truth_call_index"]:
            did = target_row["extension_decision_id"]
        else:
            # Temporary mapping-only ID. Never written as a historical replacement.
            did = f"{target_row['suite']}/{target_row['user_task']}/mapping_only_gt{gt_idx}/{c.get('function')}"
        rows.append({
            "suite": target_row["suite"],
            "user_task": target_row["user_task"],
            "privileged_call_index": pidx,
            "privileged_fn": c.get("function"),
            "gt_args": copy.deepcopy(c.get("args") or {}),
            "decision_id": did,
            "prompt": prompt,
            "prompt_sha256": hist_inv.get("prompt_sha256"),
            "n_priv_calls_in_gt": len(corrected_calls),
            "args_matched": matched,
            "args_matchable": matchable,
            "chars_matched": chars_matched,
            "chars_total": chars_total,
            "specified_fraction": frac,
            "per_arg": per_arg,
            "label": label,
            "development": False,
            "primary_eligible_label": label in {"SPECIFIED", "DELEGATED"},
            "operationalization": "historical A13 mechanical prompt-coverage label; finite C0 privileged-function overlay only",
            "ground_truth_call_index": gt_idx,
        })
    return rows


# -----------------------------------------------------------------------------
# Historical-analysis reproducibility check
# -----------------------------------------------------------------------------
def assert_historical_analysis_reproduces(a13, historical: dict[str, Any]) -> None:
    recomputed = a13.analyze(copy.deepcopy(historical["decisions"]))
    old = historical["results"]
    keys = [
        "primary_H_mean_del",
        "continuous_M_del",
        "by_label",
        "by_suite",
        "continuous_prompt_coverage_vs_M",
        "sensitivity_grid",
        "counts",
    ]
    for k in keys:
        require(recomputed.get(k) == old.get(k), f"historical A13 analysis no longer reproduces for key {k}")


# -----------------------------------------------------------------------------
# Preflight mode
# -----------------------------------------------------------------------------
def run_preflight(args) -> None:
    project_root = Path(args.project_root).resolve()
    input_zip = Path(args.input_bundle_zip).resolve()
    historical_zip = Path(args.historical_zip).resolve()
    c0_v21_archive = Path(args.c0_v21_author_archive).resolve()
    prefreeze_archive = Path(args.extension_prefreeze_archive).resolve()
    outdir = project_root / RUNNER_FREEZE_DIRNAME

    require(not outdir.exists(), f"runner-freeze directory already exists: {outdir}. Preserve it or remove it explicitly before a brand-new preflight.")
    require(not (project_root / SCIENCE_DIRNAME).exists(), "science output directory already exists; do not preflight over an existing science attempt")

    # Controlling bytes.
    verify_file_hash(input_zip, EXPECTED_INPUT_BUNDLE_SHA256, "A13-C0 input bundle")
    verify_file_hash(historical_zip, EXPECTED_HISTORICAL_ZIP_SHA256, "historical A13 archive")
    verify_file_hash(c0_v21_archive, EXPECTED_C0_V21_AUTHOR_ARCHIVE_SHA256, "C0 v2.1 author archive")
    verify_file_hash(prefreeze_archive, EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256, "extension prefreeze author archive")

    a13_path = project_root / "A13.py"
    verify_file_hash(a13_path, EXPECTED_HISTORICAL_A13_SOURCE_SHA256, "server historical A13.py")
    verify_input_bundle(input_zip, a13_path)
    historical = load_historical(historical_zip)
    prefreeze = load_and_verify_prefreeze(prefreeze_archive)

    # Environment / exact implementation.
    installed_adojo = importlib.metadata.version("agentdojo")
    require(installed_adojo == EXPECTED_AGENTDOJO_VERSION,
            f"AgentDojo is {installed_adojo}, expected {EXPECTED_AGENTDOJO_VERSION}")
    a13 = load_historical_a13(project_root)
    assert_historical_analysis_reproduces(a13, historical)

    ids = server_model_ids()
    require(SCORER_MODEL in ids, f"expected served model {SCORER_MODEL}, got {ids}")

    # Synthetic scorer endpoint self-test only. This is not a target-task score.
    test_lp, test_n = a13.score(
        "user: Repeat the following phrase exactly.\nassistant:",
        " A13 C0 extension scorer self test passed.",
    )
    require(test_lp is not None and test_n > 0, "synthetic scorer /completions echo+logprobs self-test failed")

    a13.init_tokenizer()
    derived_targets = derive_target_rows(a13, historical)

    # Check the prefreeze's corrected counts and branch semantics again.
    flow = prefreeze.get("population_flow_before_outcomes") or {}
    require(flow.get("corrected_classifiable_decisions") == 73, "prefreeze corrected classifiable decision count is not 73")
    require(flow.get("corrected_classifiable_tasks") == 55, "prefreeze corrected classifiable task count is not 55")
    require(flow.get("new_confirmatory_decisions") == 4, "prefreeze new confirmatory count is not 4")

    freeze_core = {
        "name": "A13-C0 EXTENSION RUNNER FREEZE v1",
        "scientific_status": "RUNNER_FROZEN_BEFORE_EXTENSION_SCIENCE",
        "runner_script_sha256": source_sha256(),
        "historical_a13_source_sha256": EXPECTED_HISTORICAL_A13_SOURCE_SHA256,
        "agentdojo_version": installed_adojo,
        "benchmark_version": BENCHMARK_VERSION,
        "scorer_model": SCORER_MODEL,
        "scorer_base_url": SCORER_BASE_URL,
        "server_model_ids": ids,
        "technical_preflight": {
            "synthetic_scorer_calls": 1,
            "target_task_agent_calls": 0,
            "target_task_attribution_calls": 0,
            "scorer_selftest_tokens": test_n,
            "scorer_selftest_sum_logprob": test_lp,
            "tokenizer_available": a13._TOKENIZER is not None,
            "tokenizer_error": a13._TOKENIZER_ERROR,
        },
        "controlling_input_sha256": {
            "input_bundle_zip": EXPECTED_INPUT_BUNDLE_SHA256,
            "historical_a13_zip": EXPECTED_HISTORICAL_ZIP_SHA256,
            "c0_v21_author_archive": EXPECTED_C0_V21_AUTHOR_ARCHIVE_SHA256,
            "extension_prefreeze_author_archive": EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256,
            "extension_prefreeze_json": EXPECTED_PREFREEZE_FREEZE_JSON_SHA256,
        },
        "historical_artifact_sha256": historical["raw_hashes"],
        "historical_protocol_hash": EXPECTED_HISTORICAL_PROTOCOL_HASH,
        "historical_taxonomy_hash": EXPECTED_HISTORICAL_TAXONOMY_HASH,
        "privileged_function_overlay": sorted(ADDED_PRIVILEGED_FUNCTIONS),
        "fresh_agent_task_order": [f"workspace/{x}" for x in FRESH_AGENT_TASK_ORDER],
        "historical_trajectory_reuse": "workspace/user_task_13",
        "fresh_agent_run_count": 3,
        "historical_trajectory_reuse_count": 1,
        "extension_decisions": derived_targets,
        "execution_semantics": {
            "agent_pipeline": "historical A13 exact PipelineConfig: vllm_parsed, model_id=None, defense=None, system_message=None, tool_delimiter=tool",
            "attack": "none",
            "one_fresh_run_per_new_task": True,
            "fresh_tasks": [f"workspace/{x}" for x in FRESH_AGENT_TASK_ORDER],
            "task13": "reuse exact historical trajectory SHA-256 bbdec872...; do not rerun agent",
            "mapping": "historical greedy same-function/order mapping over corrected finite privileged-function set",
            "utility_rule": "historical AgentDojo utility false => decision excluded before scoring",
            "multi_tool_rule": "historical total_calls_in_turn != 1 => decision excluded before scoring",
            "span_rule": "historical prior non-empty role=tool messages",
            "primary_ablation": historical["protocol"].get("primary_ablation"),
            "secondary_ablation": historical["protocol"].get("secondary_ablation"),
            "attribution_serialization": historical["protocol"].get("attribution_serialization"),
            "no_post_outcome_selection": True,
        },
        "analysis_semantics": {
            "historical_69_rows": "immutable",
            "extension_rows": "separate append-only four-row ledger",
            "combined_rows": 73,
            "analysis_function": "exact historical A13.analyze",
            "task_weighting": historical["protocol"].get("inference", {}).get("task_weighting"),
            "bootstrap_B": historical["protocol"].get("inference", {}).get("bootstrap_B"),
            "bootstrap_seed": historical["protocol"].get("inference", {}).get("bootstrap_seed"),
            "primary_hypothesis": historical["protocol"].get("primary_hypothesis"),
            "continuous_hypothesis": historical["protocol"].get("continuous_hypothesis"),
        },
    }
    freeze_core["freeze_body_sha256"] = sha256_bytes(stable_json(freeze_core).encode("utf-8"))
    freeze = {
        **freeze_core,
        "created_utc": now_utc(),
    }

    outdir.mkdir(parents=True, exist_ok=False)
    freeze_path = outdir / RUNNER_FREEZE_FILENAME
    write_json(freeze_path, freeze)

    # Human-readable target table.
    csv_path = outdir / "A13_C0_EXTENSION_RUNNER_TARGETS_v1.csv"
    fields = [
        "extension_decision_id", "suite", "user_task", "ground_truth_call_index",
        "corrected_privileged_call_index", "function", "label", "specified_fraction",
        "execution_mode", "prompt_sha256", "ground_truth_all_sha256",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in derived_targets:
            w.writerow({k: row.get(k) for k in fields})

    readme = outdir / "README.txt"
    readme.write_text(
        "A13-C0 EXTENSION RUNNER FREEZE v1\n"
        "This preflight performed zero target-task agent runs and zero target-task attribution scores.\n"
        "It performed exactly one synthetic scorer endpoint self-test.\n"
        "Do not run science until this freeze JSON has been independently reviewed and its SHA-256 supplied back to the science command.\n",
        encoding="utf-8",
    )
    write_final_sha256(outdir, [RUNNER_FREEZE_FILENAME, csv_path.name, readme.name])

    print("A13-C0 EXTENSION RUNNER PREFLIGHT COMPLETE")
    print("TARGET-TASK AGENT RUNS: 0")
    print("TARGET-TASK ATTRIBUTION SCORES: 0")
    print("SYNTHETIC SCORER SELF-TEST CALLS: 1")
    print(f"RUNNER SCRIPT SHA256: {source_sha256()}")
    print(f"RUNNER FREEZE JSON SHA256: {sha256_file(freeze_path)}")
    print(f"RUNNER FREEZE BODY SHA256: {freeze_core['freeze_body_sha256']}")
    print(f"OUTPUT_DIR: {outdir}")


# -----------------------------------------------------------------------------
# Science mode
# -----------------------------------------------------------------------------
def find_fresh_log_path(run_dir: Path, suite: str, user_task: str) -> Path | None:
    exact = run_dir / "vllm_parsed" / suite / user_task / "none" / "none.json"
    if exact.exists():
        return exact
    hits = list(run_dir.glob(f"*/{suite}/{user_task}/none/none.json"))
    return hits[0] if len(hits) == 1 else None


def run_fresh_agent_tasks(run_dir: Path) -> None:
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
    from agentdojo.benchmark import benchmark_suite_without_injections
    from agentdojo.logging import OutputLogger
    from agentdojo.task_suite.load_suites import get_suite

    os.environ["LOCAL_LLM_PORT"] = "8100"
    config = PipelineConfig(
        llm="vllm_parsed",
        model_id=None,
        defense=None,
        system_message_name=None,
        system_message=None,
        tool_delimiter="tool",
        tool_output_format=None,
    )
    pipeline = AgentPipeline.from_config(config)
    suite = get_suite(BENCHMARK_VERSION, "workspace")
    run_dir.mkdir(parents=True, exist_ok=False)
    with OutputLogger(str(run_dir)):
        benchmark_suite_without_injections(
            pipeline,
            suite,
            logdir=run_dir,
            force_rerun=False,
            user_tasks=FRESH_AGENT_TASK_ORDER,
            benchmark_version=BENCHMARK_VERSION,
        )


def load_runner_freeze(path: Path, expected_sha: str, current_script_sha: str) -> dict[str, Any]:
    require(len(expected_sha) == 64 and all(c in "0123456789abcdef" for c in expected_sha.lower()),
            "--expected-runner-freeze-sha256 must be a 64-character SHA-256 hex digest")
    got = sha256_file(path)
    require(got == expected_sha.lower(), f"runner freeze JSON SHA mismatch: got {got}, expected {expected_sha.lower()}")
    freeze = json.loads(path.read_text(encoding="utf-8"))
    require(freeze.get("scientific_status") == "RUNNER_FROZEN_BEFORE_EXTENSION_SCIENCE", "runner freeze status mismatch")
    require(freeze.get("runner_script_sha256") == current_script_sha, "current runner script differs from frozen runner script")
    require(freeze.get("fresh_agent_task_order") == [f"workspace/{x}" for x in FRESH_AGENT_TASK_ORDER], "runner freeze task order mismatch")
    require(freeze.get("historical_trajectory_reuse") == "workspace/user_task_13", "runner freeze historical reuse mismatch")
    require(freeze.get("privileged_function_overlay") == sorted(ADDED_PRIVILEGED_FUNCTIONS), "runner freeze overlay mismatch")
    require((freeze.get("technical_preflight") or {}).get("target_task_agent_calls") == 0, "runner preflight already used target agent calls")
    require((freeze.get("technical_preflight") or {}).get("target_task_attribution_calls") == 0, "runner preflight already used target attribution calls")
    return freeze


def core_analysis_view(x: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "primary_H_mean_del",
        "continuous_M_del",
        "by_label",
        "by_suite",
        "continuous_prompt_coverage_vs_M",
        "sensitivity_grid",
        "counts",
    ]
    return {k: x.get(k) for k in keys}


def run_science(args) -> None:
    project_root = Path(args.project_root).resolve()
    input_zip = Path(args.input_bundle_zip).resolve()
    historical_zip = Path(args.historical_zip).resolve()
    c0_v21_archive = Path(args.c0_v21_author_archive).resolve()
    prefreeze_archive = Path(args.extension_prefreeze_archive).resolve()
    runner_freeze_path = Path(args.runner_freeze_json).resolve()
    science_dir = project_root / SCIENCE_DIRNAME
    fresh_runs_dir = science_dir / "agentdojo_runs"

    require(not science_dir.exists(),
            f"science output directory already exists: {science_dir}. Do not overwrite or selectively resume a scientific attempt.")

    current_script_sha = source_sha256()
    runner_freeze = load_runner_freeze(
        runner_freeze_path,
        args.expected_runner_freeze_sha256,
        current_script_sha,
    )

    # Re-verify every controlling byte immediately before science.
    verify_file_hash(input_zip, EXPECTED_INPUT_BUNDLE_SHA256, "A13-C0 input bundle")
    verify_file_hash(historical_zip, EXPECTED_HISTORICAL_ZIP_SHA256, "historical A13 archive")
    verify_file_hash(c0_v21_archive, EXPECTED_C0_V21_AUTHOR_ARCHIVE_SHA256, "C0 v2.1 author archive")
    verify_file_hash(prefreeze_archive, EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256, "extension prefreeze author archive")
    a13_path = project_root / "A13.py"
    verify_file_hash(a13_path, EXPECTED_HISTORICAL_A13_SOURCE_SHA256, "server historical A13.py")
    verify_input_bundle(input_zip, a13_path)
    historical = load_historical(historical_zip)
    _ = load_and_verify_prefreeze(prefreeze_archive)

    installed_adojo = importlib.metadata.version("agentdojo")
    require(installed_adojo == EXPECTED_AGENTDOJO_VERSION,
            f"AgentDojo is {installed_adojo}, expected {EXPECTED_AGENTDOJO_VERSION}")
    ids = server_model_ids()
    require(SCORER_MODEL in ids, f"expected served model {SCORER_MODEL}, got {ids}")

    a13 = load_historical_a13(project_root)
    assert_historical_analysis_reproduces(a13, historical)
    derived_targets = derive_target_rows(a13, historical)
    freeze_targets = runner_freeze.get("extension_decisions") or []
    require(
        [{k: r.get(k) for k in ["extension_decision_id", "ground_truth_call_index", "corrected_privileged_call_index", "function", "label", "specified_fraction", "prompt_sha256", "ground_truth_all_sha256"]} for r in derived_targets]
        == [{k: r.get(k) for k in ["extension_decision_id", "ground_truth_call_index", "corrected_privileged_call_index", "function", "label", "specified_fraction", "prompt_sha256", "ground_truth_all_sha256"]} for r in freeze_targets],
        "rederived target rows differ from runner freeze",
    )

    # Technical scorer endpoint check before any target science in this attempt.
    tech_lp, tech_n = a13.score(
        "user: Repeat the following phrase exactly.\nassistant:",
        " A13 C0 extension science-start self test passed.",
    )
    require(tech_lp is not None and tech_n > 0, "science-start synthetic scorer self-test failed")
    a13.init_tokenizer()

    # Preserve the original A13 detector and then apply ONLY the finite frozen overlay.
    original_is_privileged = a13.is_privileged_fn
    a13._c0_original_is_privileged_fn = original_is_privileged
    a13.is_privileged_fn = lambda fn: bool(original_is_privileged(fn) or fn in ADDED_PRIVILEGED_FUNCTIONS)

    # Count only target-task attribution score() calls below. The synthetic self-test above is technical.
    raw_score = a13.score
    scorer_call_counter = {"scientific": 0}
    def counted_score(prompt: str, completion: str):
        scorer_call_counter["scientific"] += 1
        return raw_score(prompt, completion)
    a13.score = counted_score

    science_dir.mkdir(parents=True, exist_ok=False)

    # Exactly three fresh no-injection agent episodes, all in workspace.
    run_fresh_agent_tasks(fresh_runs_dir)

    fresh_logs: dict[str, dict[str, Any]] = {}
    fresh_log_meta = []
    for ut in FRESH_AGENT_TASK_ORDER:
        p = find_fresh_log_path(fresh_runs_dir, "workspace", ut)
        require(p is not None, f"missing fresh AgentDojo log for workspace/{ut}")
        obj = json.loads(p.read_text(encoding="utf-8"))
        require(obj.get("suite_name") == "workspace", f"fresh log suite mismatch for {ut}")
        require(obj.get("user_task_id") == ut, f"fresh log task mismatch for {ut}")
        require(obj.get("benchmark_version") == BENCHMARK_VERSION, f"fresh log benchmark version mismatch for {ut}")
        require(obj.get("agentdojo_package_version") == EXPECTED_AGENTDOJO_VERSION, f"fresh log AgentDojo version mismatch for {ut}")
        # A13 is explicitly no-injection. Preserve what the official logger records.
        require(not obj.get("injections"), f"fresh log unexpectedly contains injections for {ut}")
        fresh_logs[ut] = obj
        fresh_log_meta.append({
            "suite": "workspace",
            "user_task": ut,
            "path": str(p.relative_to(science_dir)),
            "sha256": sha256_file(p),
            "bytes": p.stat().st_size,
            "utility": bool(obj.get("utility")),
            "security": obj.get("security"),
            "error": obj.get("error"),
            "duration": obj.get("duration"),
        })

    # Measure exactly the four frozen extension decisions.
    extension_records = []
    for target in derived_targets:
        if target["user_task"] == HISTORICAL_REUSE_TASK:
            log_obj = copy.deepcopy(historical["task13_log"])
            trajectory_source = "HISTORICAL_A13_REUSE"
            trajectory_sha = EXPECTED_TASK13_LOG_SHA256
        else:
            log_obj = copy.deepcopy(fresh_logs[target["user_task"]])
            trajectory_source = "FRESH_C0_EXTENSION_AGENT_RUN"
            p = find_fresh_log_path(fresh_runs_dir, "workspace", target["user_task"])
            require(p is not None, "fresh log disappeared")
            trajectory_sha = sha256_file(p)

        mapping_rows = make_corrected_gt_rows_for_task(a13, historical, target)
        mapped_all = a13.map_gt_to_actual(mapping_rows, list(log_obj.get("messages") or []))
        target_maps = [
            m for m in mapped_all
            if (m.get("taxonomy") or {}).get("decision_id") == target["extension_decision_id"]
        ]
        require(len(target_maps) == 1, f"target mapping row missing/duplicated for {target['extension_decision_id']}")

        before_calls = scorer_call_counter["scientific"]
        rec = a13.measure_decision(log_obj, target_maps[0])
        after_calls = scorer_call_counter["scientific"]

        # Hard-assert immutable frozen identity/label fields.
        require(rec.get("decision_id") == target["extension_decision_id"], "measured extension decision ID mismatch")
        require(rec.get("label") == target["label"], "measured extension label mismatch")
        require(abs(float(rec.get("specified_fraction")) - float(target["specified_fraction"])) <= 1e-15,
                "measured extension specified_fraction mismatch")

        rec.update({
            "c0_extension": True,
            "ground_truth_call_index": target["ground_truth_call_index"],
            "corrected_privileged_call_index": target["corrected_privileged_call_index"],
            "execution_mode": target["execution_mode"],
            "trajectory_source": trajectory_source,
            "trajectory_sha256": trajectory_sha,
            "scientific_scorer_calls_for_decision": after_calls - before_calls,
            "historical_decision_ids_renumbered": False,
            "extension_prefreeze_author_archive_sha256": EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256,
            "runner_freeze_json_sha256": args.expected_runner_freeze_sha256.lower(),
        })
        extension_records.append(rec)

    require(len(extension_records) == 4, f"science produced {len(extension_records)} extension records instead of 4")
    require({r["decision_id"] for r in extension_records} == {x["extension_decision_id"] for x in EXTENSION_TARGETS},
            "extension output decision IDs differ from frozen set")

    # Append-only extension ledger.
    ext_jsonl = science_dir / "A13_C0_EXTENSION_DECISIONS_v1.jsonl"
    with ext_jsonl.open("w", encoding="utf-8") as f:
        for r in extension_records:
            f.write(json.dumps(json_safe(r), ensure_ascii=False) + "\n")

    # Derived combined ledger. Historical rows are copied byte-semantically, not rewritten in place.
    combined_records = copy.deepcopy(historical["decisions"]) + copy.deepcopy(extension_records)
    require(len(combined_records) == 73, f"combined ledger must contain 73 rows, got {len(combined_records)}")
    combined_jsonl = science_dir / "A13_C0_COMBINED_73_DECISIONS_DERIVED_v1.jsonl"
    with combined_jsonl.open("w", encoding="utf-8") as f:
        for r in combined_records:
            f.write(json.dumps(json_safe(r), ensure_ascii=False) + "\n")

    corrected_analysis = a13.analyze(combined_records)
    historical_recomputed = a13.analyze(copy.deepcopy(historical["decisions"]))
    require(core_analysis_view(historical_recomputed) == core_analysis_view(historical["results"]),
            "historical analysis changed during combined reanalysis")

    extension_disposition = {
        r["decision_id"]: {
            "label": r.get("label"),
            "mapped": r.get("mapped"),
            "utility": r.get("utility"),
            "primary_valid": r.get("primary_valid"),
            "primary_exclusion_reason": r.get("primary_exclusion_reason"),
            "H_mean_del": r.get("H_mean_del"),
            "M_del": r.get("M_del"),
            "n_eligible_tool_spans": r.get("n_eligible_tool_spans"),
            "scientific_scorer_calls_for_decision": r.get("scientific_scorer_calls_for_decision"),
            "trajectory_source": r.get("trajectory_source"),
        }
        for r in extension_records
    }

    result_obj = {
        "name": "A13-C0 COVERAGE-CORRECTED EXTENSION RESULT v1",
        "created_utc": now_utc(),
        "scientific_status": "AUTHOR_RUN_EXTENSION_COMPLETE",
        "controlling_hashes": {
            "runner_script_sha256": current_script_sha,
            "runner_freeze_json_sha256": args.expected_runner_freeze_sha256.lower(),
            "extension_prefreeze_author_archive_sha256": EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256,
            "historical_a13_zip_sha256": EXPECTED_HISTORICAL_ZIP_SHA256,
            "input_bundle_zip_sha256": EXPECTED_INPUT_BUNDLE_SHA256,
            "c0_v21_author_archive_sha256": EXPECTED_C0_V21_AUTHOR_ARCHIVE_SHA256,
            "historical_a13_source_sha256": EXPECTED_HISTORICAL_A13_SOURCE_SHA256,
        },
        "environment": {
            "agentdojo_version": installed_adojo,
            "benchmark_version": BENCHMARK_VERSION,
            "scorer_model": SCORER_MODEL,
            "scorer_base_url": SCORER_BASE_URL,
            "server_model_ids": ids,
            "technical_science_start_scorer_selftest_calls": 1,
            "scientific_scorer_calls_total": scorer_call_counter["scientific"],
            "fresh_agent_task_count": 3,
            "historical_trajectory_reuse_count": 1,
            "tokenizer_available": a13._TOKENIZER is not None,
            "tokenizer_error": a13._TOKENIZER_ERROR,
        },
        "fresh_agent_logs": fresh_log_meta,
        "extension_disposition": extension_disposition,
        "historical_analysis_reproduces": True,
        "historical_primary": core_analysis_view(historical["results"]),
        "coverage_corrected_primary": core_analysis_view(corrected_analysis),
        "coverage_flow": {
            "all_tasks": 97,
            "development_exclusions": 3,
            "untouched_tasks": 94,
            "corrected_candidate_tasks": 58,
            "corrected_candidate_decisions": 76,
            "corrected_classifiable_tasks": 55,
            "corrected_classifiable_decisions": 73,
            "historical_decision_rows": 69,
            "extension_decision_rows": 4,
        },
        "interpretation_guardrail": (
            "This runner records outcomes and recomputes the prospectively specified historical A13 analysis on the corrected finite census. "
            "Do not selectively rerun, remove, relabel, or replace extension cases based on these outcomes."
        ),
    }
    result_path = science_dir / "A13_C0_EXTENSION_RESULT_v1.json"
    write_json(result_path, result_obj)

    # Compact CSV for the four extension decisions.
    csv_path = science_dir / "A13_C0_EXTENSION_DECISIONS_SUMMARY_v1.csv"
    fields = [
        "decision_id", "label", "specified_fraction", "trajectory_source", "trajectory_sha256",
        "mapped", "utility", "actual_total_calls_in_turn", "n_eligible_tool_spans",
        "primary_valid", "primary_exclusion_reason", "H_mean_del", "M_del",
        "H_max_del", "mean_dS_del", "dU_del", "scientific_scorer_calls_for_decision",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in extension_records:
            w.writerow({k: r.get(k) for k in fields})

    provenance_path = science_dir / "A13_C0_EXTENSION_PROVENANCE_v1.json"
    write_json(provenance_path, {
        "created_utc": now_utc(),
        "runner_script_sha256": current_script_sha,
        "runner_freeze_json_path": str(runner_freeze_path),
        "runner_freeze_json_sha256": args.expected_runner_freeze_sha256.lower(),
        "prefreeze_author_archive_sha256": EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256,
        "historical_task13_log_sha256": EXPECTED_TASK13_LOG_SHA256,
        "fresh_agent_logs": fresh_log_meta,
        "historical_artifacts_immutable": True,
        "historical_decision_ids_renumbered": False,
        "scientific_scorer_calls_total": scorer_call_counter["scientific"],
        "technical_science_start_scorer_selftest_calls": 1,
    })

    readme = science_dir / "README.txt"
    readme.write_text(
        "A13-C0 COVERAGE-CORRECTED EXTENSION SCIENCE v1\n"
        "Historical a13/ artifacts were not overwritten.\n"
        "This directory contains four append-only extension rows, a derived 73-row combined ledger, corrected analysis, raw fresh AgentDojo logs, and provenance hashes.\n"
        "Do not selectively rerun extension cases based on outcomes.\n",
        encoding="utf-8",
    )

    # Hash every paper-bearing file plus raw fresh logs.
    hash_entries = []
    for p in sorted(science_dir.rglob("*")):
        if p.is_file() and p.name != "FINAL_SHA256.txt":
            hash_entries.append((str(p.relative_to(science_dir)), sha256_file(p)))
    final_hash = science_dir / "FINAL_SHA256.txt"
    final_hash.write_text("\n".join(f"{h}  {name}" for name, h in hash_entries) + "\n", encoding="utf-8")

    print("A13-C0 EXTENSION SCIENCE COMPLETE")
    print("FRESH TARGET AGENT RUNS: 3")
    print("HISTORICAL TRAJECTORY REUSE: 1")
    print(f"SCIENTIFIC ATTRIBUTION SCORE CALLS: {scorer_call_counter['scientific']}")
    for r in extension_records:
        print(
            f"{r['decision_id']}  label={r.get('label')}  mapped={r.get('mapped')}  "
            f"utility={r.get('utility')}  valid={r.get('primary_valid')}  "
            f"reason={r.get('primary_exclusion_reason')}  H={r.get('H_mean_del')}  M={r.get('M_del')}"
        )
    print("HISTORICAL PRIMARY H:", historical["results"].get("primary_H_mean_del"))
    print("CORRECTED PRIMARY H:", corrected_analysis.get("primary_H_mean_del"))
    print("HISTORICAL CONTINUOUS M:", historical["results"].get("continuous_M_del"))
    print("CORRECTED CONTINUOUS M:", corrected_analysis.get("continuous_M_del"))
    print(f"RESULT JSON: {result_path}")
    print(f"FINAL HASH LEDGER: {final_hash}")
    print("DO NOT RERUN/EXCLUDE/RELABEL BASED ON THESE OUTCOMES.")


# -----------------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------------
def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=["preflight", "science"], required=True)
    p.add_argument("project_root")
    p.add_argument("--input-bundle-zip", required=True)
    p.add_argument("--historical-zip", required=True)
    p.add_argument("--c0-v21-author-archive", required=True)
    p.add_argument("--extension-prefreeze-archive", required=True)
    p.add_argument("--runner-freeze-json")
    p.add_argument("--expected-runner-freeze-sha256")
    return p.parse_args()


def main():
    args = parse_args()
    if args.mode == "preflight":
        require(args.runner_freeze_json is None, "--runner-freeze-json is science-only")
        require(args.expected_runner_freeze_sha256 is None, "--expected-runner-freeze-sha256 is science-only")
        run_preflight(args)
    else:
        require(bool(args.runner_freeze_json), "science mode requires --runner-freeze-json")
        require(bool(args.expected_runner_freeze_sha256), "science mode requires --expected-runner-freeze-sha256")
        run_science(args)


if __name__ == "__main__":
    main()
