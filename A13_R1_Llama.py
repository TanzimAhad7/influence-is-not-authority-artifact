#!/usr/bin/env python3
"""
A13-R1 — scorer-only cross-model robustness on the frozen A13-Qwen traces.

Scientific purpose
------------------
Hold fixed:
  * the exact completed A13-Qwen AgentDojo trajectories,
  * the exact executed privileged actions,
  * the exact A13 taxonomy / labels / exclusions,
  * the exact A12_flat_v1 serialization,
  * the exact user/tool deletion and character-matched substitution interventions,
  * the exact primary H_mean and continuous M definitions.

Change only:
  * attribution scorer: Qwen/Qwen2.5-72B-Instruct -> meta-llama/Llama-3.3-70B-Instruct.

This script DOES NOT run AgentDojo and DOES NOT modify ./a13.
It reads ./a13 and writes only ./a13_r1_llama.

Expected placement:
    ~/ratchet/phase0_pilot/A13_R1_Llama.py

Expected parent artifacts:
    ~/ratchet/phase0_pilot/a13/

Expected scorer endpoint:
    http://localhost:8110/v1

The script freezes/validates an R1 protocol before outcome scoring and refuses to
silently change it on resume.
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
import random
import statistics
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

# =============================================================================
# R1 FROZEN CONFIG
# =============================================================================

SCORER_MODEL = "meta-llama/Llama-3.3-70B-Instruct"
SCORER_BASE_URL = "http://localhost:8110/v1"
SCORER_API_KEY = "x"
HTTP_TIMEOUT = 240

PROJECT_ROOT = Path(__file__).resolve().parent
PARENT_DIR = PROJECT_ROOT / "a13"
PARENT_PROTOCOL = PARENT_DIR / "protocol.json"
PARENT_TAXONOMY = PARENT_DIR / "taxonomy.json"
PARENT_DECISIONS = PARENT_DIR / "decisions.jsonl"
PARENT_RESULTS = PARENT_DIR / "results.json"
PARENT_MANIFEST = PARENT_DIR / "manifest.json"
PARENT_RUNS = PARENT_DIR / "agentdojo_runs" / "vllm_parsed"

OUT_DIR = PROJECT_ROOT / "a13_r1_llama"
PROTOCOL_PATH = OUT_DIR / "protocol.json"
DECISIONS_PATH = OUT_DIR / "decisions.jsonl"
RESULTS_PATH = OUT_DIR / "results.json"
REPORT_PATH = OUT_DIR / "REPORT.md"
MANIFEST_PATH = OUT_DIR / "manifest.json"
CHECKPOINT_PATH = OUT_DIR / "checkpoint_decisions.jsonl"

# This binds R1 to the exact completed A13 run that was deeply audited.
EXPECTED_PARENT_PROTOCOL_HASH = "b4a140c7d8ef49149ac72e35e9e52405f614fa5361558c7b2ac0c56fe0063b80"
EXPECTED_PARENT_SOURCE_SHA256 = "f771850375b4f5af7bc2cec6a4e166057f33fab26d686320b8ef2d8d32557f05"
EXPECTED_PARENT_TAXONOMY_HASH = "213cd71e0017eeb91c52955f8b77d06455c8d280b0121b31a830aa651ae62740"
EXPECTED_PARENT_MANIFEST_SHA256 = "971eb1ea932a2bc9687c288532b3b9e1b8ae608a492b068d1edf8eae33b0cf0b"
EXPECTED_PARENT_DECISIONS_SHA256 = "af6a62c5689e7d26180f0091a121839b645e1dcb54e5aaf87427f6e75c19dca9"
EXPECTED_PARENT_RESULTS_SHA256 = "6ced3fc14a60574f95881344ac3d6bb5b8cf7d88d59ac3c844cae35d4121646b"

EXPECTED_VALID_DECISIONS = 26
EXPECTED_EXTREME_DECISIONS = 16
EXPECTED_PRIMARY_TASKS = 13

SPECIFIED_FRACTION_MIN = 0.80
DELEGATED_FRACTION_MAX = 0.20
SENSITIVITY_GRID = [
    {"specified_min": 0.90, "delegated_max": 0.10},
    {"specified_min": 0.80, "delegated_max": 0.20},
    {"specified_min": 0.70, "delegated_max": 0.30},
]

BOOTSTRAP_B = 5000
BOOTSTRAP_SEED = 130013
MIN_TASKS_FOR_CI = 3
NEAR_ZERO_DENOM = 1e-9

NEUTRAL_USER = "Please continue the task using the available information."
PAD_FILLER = " benign context."

# =============================================================================
# GENERIC UTILITIES
# =============================================================================

def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            c = f.read(1024 * 1024)
            if not c:
                break
            h.update(c)
    return h.hexdigest()


def stable_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
    tmp.replace(path)


def source_sha256() -> str:
    return sha256_file(Path(__file__).resolve())


# =============================================================================
# A13 SERIALIZATION — HELD FIXED
# =============================================================================

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


def rc(tc: dict) -> str:
    try:
        a = json.dumps(tc.get("args") or {}, sort_keys=True, ensure_ascii=False)
    except Exception:
        a = str(tc.get("args"))
    return f"{tc.get('function')}({a})"


def flat(msgs: list[dict]) -> str:
    out = []
    for m in msgs:
        b = mt(m)
        calls = [rc(t) for t in (m.get("tool_calls") or [])]
        if calls:
            b = (b + "\n" if b else "") + "\n".join(calls)
        out.append(f"{m.get('role','?')}: {b}")
    return "\n".join(out) + "\nassistant: "


def pad(n: int) -> str:
    s = ""
    while len(s) < n:
        s += PAD_FILLER
    return s[:n]


def replace_content(msg: dict, new_text: str) -> dict:
    m = copy.deepcopy(msg)
    m["content"] = new_text
    return m


# =============================================================================
# SERVER / SCORING
# =============================================================================

def http_json(path: str, payload=None, method=None):
    url = f"{SCORER_BASE_URL}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {SCORER_API_KEY}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def get_server_model_ids():
    d = http_json("/models")
    return [x.get("id") for x in d.get("data", []) if isinstance(x, dict)]


def score(prompt: str, completion: str):
    """A13/A12-compatible teacher-forced score using vLLM /completions.

    Returns a dict rather than just a tuple so R1 can record tokenizer-boundary
    diagnostics without altering the frozen score itself.
    """
    d = http_json(
        "/completions",
        {
            "model": SCORER_MODEL,
            "prompt": prompt + completion,
            "max_tokens": 0,
            "echo": True,
            "logprobs": 1,
            "temperature": 0,
        },
    )
    lp = d["choices"][0]["logprobs"]
    offs = lp["text_offset"]
    toks = lp["token_logprobs"]
    token_text = lp.get("tokens") or [None] * len(offs)
    cut = len(prompt)

    selected = [(o, v, t) for o, v, t in zip(offs, toks, token_text) if o >= cut and v is not None]
    if not selected:
        return {
            "sum_logprob": None,
            "completion_token_count": 0,
            "first_selected_offset": None,
            "cut": cut,
            "pre_cut_nonnull_token_offset": max(
                [o for o, v in zip(offs, toks) if o < cut and v is not None],
                default=None,
            ),
        }

    return {
        "sum_logprob": float(sum(v for _, v, _ in selected)),
        "completion_token_count": len(selected),
        "first_selected_offset": selected[0][0],
        "first_selected_token": selected[0][2],
        "cut": cut,
        "pre_cut_nonnull_token_offset": max(
            [o for o, v in zip(offs, toks) if o < cut and v is not None],
            default=None,
        ),
    }


def server_preflight() -> None:
    try:
        ids = get_server_model_ids()
    except Exception as e:
        sys.exit(
            f"FATAL: Llama vLLM is not reachable at {SCORER_BASE_URL}: "
            f"{type(e).__name__}: {e}"
        )
    if SCORER_MODEL not in ids:
        sys.exit(
            f"FATAL: expected served model {SCORER_MODEL!r}, got {ids}. "
            "Do not run R1 against a different model name."
        )

    # Multi-token boundary-safe self-test. This does not touch experiment data.
    z = score(
        "user: Repeat the following phrase exactly.\nassistant:",
        " A13 R1 Llama scorer self test passed.",
    )
    if z["sum_logprob"] is None or z["completion_token_count"] <= 0:
        sys.exit(
            "FATAL: Llama /completions echo+logprobs self-test failed. "
            "Do not score R1 until this works."
        )
    print(
        "[scorer] Llama /completions echo+logprobs self-test PASS "
        f"({z['completion_token_count']} scored tokens, "
        f"sum_logprob={z['sum_logprob']:.4f})"
    )


# =============================================================================
# PARENT A13 VALIDATION
# =============================================================================

def resolve_manifest_entry(original_path: str) -> Path:
    """Map an absolute path stored on the original server into local ./a13."""
    marker = "/a13/"
    if marker not in original_path:
        raise ValueError(f"manifest path does not contain /a13/: {original_path}")
    rel = original_path.split(marker, 1)[1]
    return PARENT_DIR / rel


def validate_parent_manifest() -> dict:
    required = [
        PARENT_PROTOCOL,
        PARENT_TAXONOMY,
        PARENT_DECISIONS,
        PARENT_RESULTS,
        PARENT_MANIFEST,
    ]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        sys.exit("FATAL: missing parent A13 artifacts:\n  " + "\n  ".join(missing))

    fixed_hashes = {
        PARENT_MANIFEST: EXPECTED_PARENT_MANIFEST_SHA256,
        PARENT_DECISIONS: EXPECTED_PARENT_DECISIONS_SHA256,
        PARENT_RESULTS: EXPECTED_PARENT_RESULTS_SHA256,
    }
    for p, exp in fixed_hashes.items():
        got = sha256_file(p)
        if got != exp:
            sys.exit(f"FATAL: parent artifact hash drift for {p.name}: {got} != {exp}")

    manifest = read_json(PARENT_MANIFEST)
    if manifest.get("protocol_hash") != EXPECTED_PARENT_PROTOCOL_HASH:
        sys.exit("FATAL: parent manifest protocol hash is not the audited A13 run")
    if manifest.get("source_sha256") != EXPECTED_PARENT_SOURCE_SHA256:
        sys.exit("FATAL: parent manifest source hash is not the audited A13 script")

    bad = []
    for original_path, meta in manifest.get("files", {}).items():
        p = resolve_manifest_entry(original_path)
        if not p.exists():
            bad.append((str(p), "missing"))
            continue
        got_sha = sha256_file(p)
        got_bytes = p.stat().st_size
        if got_sha != meta.get("sha256") or got_bytes != meta.get("bytes"):
            bad.append((str(p), f"hash/size mismatch {got_sha} {got_bytes}"))
    if bad:
        msg = "\n".join(f"  {p}: {why}" for p, why in bad[:20])
        sys.exit(f"FATAL: parent manifest verification failed:\n{msg}")

    protocol = read_json(PARENT_PROTOCOL)
    if protocol.get("protocol_hash") != EXPECTED_PARENT_PROTOCOL_HASH:
        sys.exit("FATAL: parent protocol hash mismatch")
    if protocol.get("source_sha256") != EXPECTED_PARENT_SOURCE_SHA256:
        sys.exit("FATAL: parent source hash mismatch")
    if protocol.get("taxonomy_hash") != EXPECTED_PARENT_TAXONOMY_HASH:
        sys.exit("FATAL: parent taxonomy hash mismatch")

    rows = read_jsonl(PARENT_DECISIONS)
    valid = [r for r in rows if r.get("primary_valid") and not r.get("development")]
    extreme = [r for r in valid if r.get("label") in {"SPECIFIED", "DELEGATED"}]
    tasks = {r["task_key"] for r in extreme}
    if len(valid) != EXPECTED_VALID_DECISIONS:
        sys.exit(f"FATAL: expected 26 fixed valid decisions, found {len(valid)}")
    if len(extreme) != EXPECTED_EXTREME_DECISIONS:
        sys.exit(f"FATAL: expected 16 fixed extreme-label decisions, found {len(extreme)}")
    if len(tasks) != EXPECTED_PRIMARY_TASKS:
        sys.exit(f"FATAL: expected 13 fixed primary tasks, found {len(tasks)}")

    # Check raw traces for every fixed valid row and verify the decision location.
    for r in valid:
        trace = trace_path(r["suite"], r["user_task"])
        log = read_json(trace)
        msgs = list(log.get("messages") or [])
        mi = int(r["actual_message_index"])
        if mi < 0 or mi >= len(msgs):
            sys.exit(f"FATAL: invalid message index for {r['decision_id']}")
        calls = list(msgs[mi].get("tool_calls") or [])
        target = r.get("actual_call") or {}
        matches = [c for c in calls if c.get("function") == target.get("function") and (c.get("args") or {}) == (target.get("args") or {})]
        if len(matches) != 1:
            sys.exit(
                f"FATAL: exact actual call cannot be uniquely re-identified in raw trace for {r['decision_id']}"
            )

    print(
        "[parent] exact audited A13 verified: "
        f"57 manifest files + {len(valid)} fixed valid decisions + {len(extreme)} primary extreme-label decisions"
    )
    return {"protocol": protocol, "manifest": manifest, "rows": rows, "valid": valid, "extreme": extreme}


def trace_path(suite: str, task: str) -> Path:
    p = PARENT_RUNS / suite / task / "none" / "none.json"
    if p.exists():
        return p
    hits = list((PARENT_RUNS / suite / task).glob("**/none.json"))
    if len(hits) == 1:
        return hits[0]
    raise FileNotFoundError(f"could not resolve unique trace for {suite}/{task}: {hits}")


# =============================================================================
# R1 PROTOCOL FREEZE
# =============================================================================

def build_protocol(parent: dict) -> dict:
    valid = parent["valid"]
    extreme = parent["extreme"]
    obj = {
        "study": "A13-R1 fixed-trace scorer-only cross-model robustness",
        "scientific_status": "prospective robustness test designed after completed A13-Qwen audit",
        "parent_a13_protocol_hash": EXPECTED_PARENT_PROTOCOL_HASH,
        "parent_a13_source_sha256": EXPECTED_PARENT_SOURCE_SHA256,
        "parent_a13_taxonomy_hash": EXPECTED_PARENT_TAXONOMY_HASH,
        "parent_a13_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
        "parent_a13_decisions_sha256": EXPECTED_PARENT_DECISIONS_SHA256,
        "parent_a13_results_sha256": EXPECTED_PARENT_RESULTS_SHA256,
        "r1_source_sha256": source_sha256(),
        "parent_scorer": "Qwen/Qwen2.5-72B-Instruct",
        "r1_scorer": SCORER_MODEL,
        "r1_scorer_base_url": SCORER_BASE_URL,
        "agent_trajectories": "EXACT frozen A13-Qwen raw traces; no new AgentDojo execution",
        "actions": "EXACT executed A13-Qwen privileged actions",
        "attribution_serialization": "A12_flat_v1; unchanged from A13",
        "fixed_valid_decision_ids": [r["decision_id"] for r in valid],
        "fixed_primary_extreme_label_decision_ids": [r["decision_id"] for r in extreme],
        "fixed_valid_n": len(valid),
        "fixed_primary_extreme_label_n": len(extreme),
        "fixed_primary_task_n": len({r["task_key"] for r in extreme}),
        "labels": "copied exactly from frozen parent A13 taxonomy/decisions; never re-estimated from R1 outcomes",
        "span_eligibility": "reconstruct exact A13 rule: prior role==tool and non-empty stripped textual content; must match parent n_eligible_tool_spans",
        "primary_ablation": "true deletion of first user message / each eligible tool message, identical to A13",
        "secondary_ablation": "character-matched neutral substitution on both user/tool spans, identical to A13",
        "primary_endpoint": "H_mean_del = I[Delta_U_del > mean(Delta_S_del)] under Llama scorer",
        "primary_hypothesis": "task-weighted H_mean_del(SPECIFIED) > H_mean_del(DELEGATED) under Llama scorer",
        "continuous_effect": "M_del = Delta_U_del - mean(Delta_S_del)",
        "continuous_hypothesis": "task-weighted M_del(SPECIFIED) > M_del(DELEGATED) under Llama scorer",
        "cross_scorer_supportive_diagnostics": [
            "Qwen-vs-Llama H_mean agreement on fixed decisions",
            "Pearson/Spearman correlations of dU_del, mean_dS_del, max_dS_del, M_del",
            "task-level cross-scorer M correlation",
            "deletion/substitution agreement",
            "token-boundary offset diagnostics; never used to alter scores post hoc",
        ],
        "inference": {
            "unit_for_resampling": "user task",
            "task_weighting": "equal weight per task within label",
            "bootstrap_B": BOOTSTRAP_B,
            "bootstrap_seed": BOOTSTRAP_SEED,
            "partial_label": "descriptive/supportive only",
            "missing_llama_score": "R1 fixed-sample run is incomplete; do not silently drop failed decisions",
        },
        "sensitivity_grid": SENSITIVITY_GRID,
        "interpretation_before_outcomes": {
            "strong_replication": "primary H contrast > 0 and frozen task-bootstrap CI lower bound > 0",
            "directional_replication": "primary H contrast > 0 but CI includes 0",
            "failure_to_replicate_direction": "primary H contrast <= 0",
            "note": "M and cross-scorer correlations are supportive, not allowed to rescue a failed primary H direction post hoc",
        },
        "no_post_outcome_tuning": True,
    }
    obj["protocol_hash"] = sha256_bytes(stable_json(obj).encode("utf-8"))
    return obj


def freeze_or_verify_protocol(protocol: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if PROTOCOL_PATH.exists():
        old = read_json(PROTOCOL_PATH)
        if old.get("protocol_hash") != protocol.get("protocol_hash"):
            sys.exit(
                "FATAL: existing a13_r1_llama/protocol.json differs from this script/config. "
                "Do not overwrite a frozen R1 protocol."
            )
        print(f"[protocol] existing frozen R1 protocol verified: {protocol['protocol_hash']}")
        return
    frozen = copy.deepcopy(protocol)
    frozen["frozen_at_utc"] = now_utc()
    dump_json(PROTOCOL_PATH, frozen)
    print(f"[protocol] R1 FROZEN BEFORE A13 OUTCOME RESCORING: {protocol['protocol_hash']}")


# =============================================================================
# FIXED-TRACE RECONSTRUCTION + LLAMA RESCORING
# =============================================================================

def reconstruct_fixed_decision(parent_row: dict):
    log = read_json(trace_path(parent_row["suite"], parent_row["user_task"]))
    msgs = list(log.get("messages") or [])
    mi = int(parent_row["actual_message_index"])
    ctx = [copy.deepcopy(m) for m in msgs[:mi]]
    if not ctx:
        raise RuntimeError("empty context")

    user_indices = [i for i, m in enumerate(ctx) if m.get("role") == "user"]
    if not user_indices:
        raise RuntimeError("no user before fixed decision")
    ui = user_indices[0]

    spans = []
    for i, m in enumerate(ctx):
        if m.get("role") != "tool":
            continue
        text = mt(m)
        if not text.strip():
            continue
        spans.append({"message_index": i, "text": text, "char_len": len(text)})

    if len(spans) != int(parent_row["n_eligible_tool_spans"]):
        raise RuntimeError(
            f"eligible span count drift: reconstructed={len(spans)} parent={parent_row['n_eligible_tool_spans']}"
        )

    completion = parent_row.get("completion")
    expected_completion = rc(parent_row["actual_call"])
    if completion != expected_completion:
        raise RuntimeError("parent completion no longer equals canonical actual call serialization")

    return ctx, ui, spans, completion


def rescore_one(parent_row: dict) -> dict:
    ctx, ui, spans, comp = reconstruct_fixed_decision(parent_row)
    prompt_full = flat(ctx)
    sf = score(prompt_full, comp)
    lp_full = sf["sum_logprob"]
    y_tokens = sf["completion_token_count"]
    if lp_full is None or y_tokens <= 0:
        raise RuntimeError("full score failed")

    # Primary deletion U
    ctx_u_del = [copy.deepcopy(m) for j, m in enumerate(ctx) if j != ui]
    su = score(flat(ctx_u_del), comp)
    if su["sum_logprob"] is None:
        raise RuntimeError("user deletion score failed")

    ds_del = []
    span_rows = []
    for s in spans:
        si = s["message_index"]
        c = [copy.deepcopy(m) for j, m in enumerate(ctx) if j != si]
        ss = score(flat(c), comp)
        if ss["sum_logprob"] is None:
            raise RuntimeError(f"tool deletion score failed at message {si}")
        raw = lp_full - ss["sum_logprob"]
        norm = raw / y_tokens
        ds_del.append(norm)
        span_rows.append({
            **s,
            "delta_del_raw": raw,
            "delta_del": norm,
            "score_first_selected_offset": ss.get("first_selected_offset"),
        })

    du_del_raw = lp_full - su["sum_logprob"]
    du_del = du_del_raw / y_tokens
    mean_ds_del = statistics.mean(ds_del)
    max_ds_del = max(ds_del)

    # Secondary substitution U/S
    real_u = mt(ctx[ui])
    neutral = NEUTRAL_USER
    while len(neutral) < len(real_u):
        neutral += PAD_FILLER
    c_u_sub = [copy.deepcopy(m) for m in ctx]
    c_u_sub[ui] = replace_content(c_u_sub[ui], neutral[:max(1, len(real_u))])
    su_sub = score(flat(c_u_sub), comp)
    if su_sub["sum_logprob"] is None:
        raise RuntimeError("user substitution score failed")

    ds_sub = []
    for idx, s in enumerate(spans):
        si = s["message_index"]
        c = [copy.deepcopy(m) for m in ctx]
        c[si] = replace_content(c[si], pad(s["char_len"]))
        ss = score(flat(c), comp)
        if ss["sum_logprob"] is None:
            raise RuntimeError(f"tool substitution score failed at message {si}")
        raw = lp_full - ss["sum_logprob"]
        norm = raw / y_tokens
        ds_sub.append(norm)
        span_rows[idx]["delta_sub_raw"] = raw
        span_rows[idx]["delta_sub"] = norm

    du_sub_raw = lp_full - su_sub["sum_logprob"]
    du_sub = du_sub_raw / y_tokens
    mean_ds_sub = statistics.mean(ds_sub)
    max_ds_sub = max(ds_sub)

    q = {
        k: parent_row.get(k)
        for k in [
            "completion_tokens", "lp_full", "dU_del_raw", "dU_del", "dS_del",
            "mean_dS_del", "max_dS_del", "H_mean_del", "H_max_del", "M_del",
            "max_margin_del", "R_del", "dU_sub_raw", "dU_sub", "dS_sub",
            "mean_dS_sub", "max_dS_sub", "H_mean_sub", "H_max_sub", "M_sub",
            "max_margin_sub", "R_sub",
        ]
    }

    llama = {
        "completion_tokens": y_tokens,
        "lp_full": lp_full,
        "dU_del_raw": du_del_raw,
        "dU_del": du_del,
        "dS_del": ds_del,
        "mean_dS_del": mean_ds_del,
        "max_dS_del": max_ds_del,
        "H_mean_del": bool(du_del > mean_ds_del),
        "H_max_del": bool(du_del > max_ds_del),
        "M_del": du_del - mean_ds_del,
        "max_margin_del": du_del - max_ds_del,
        "R_del": du_del / mean_ds_del if abs(mean_ds_del) > NEAR_ZERO_DENOM else None,
        "dU_sub_raw": du_sub_raw,
        "dU_sub": du_sub,
        "dS_sub": ds_sub,
        "mean_dS_sub": mean_ds_sub,
        "max_dS_sub": max_ds_sub,
        "H_mean_sub": bool(du_sub > mean_ds_sub),
        "H_max_sub": bool(du_sub > max_ds_sub),
        "M_sub": du_sub - mean_ds_sub,
        "max_margin_sub": du_sub - max_ds_sub,
        "R_sub": du_sub / mean_ds_sub if abs(mean_ds_sub) > NEAR_ZERO_DENOM else None,
        "spans": span_rows,
        "full_score_boundary": sf,
        "user_del_score_boundary": su,
        "user_sub_score_boundary": su_sub,
    }

    return {
        "decision_id": parent_row["decision_id"],
        "suite": parent_row["suite"],
        "user_task": parent_row["user_task"],
        "task_key": parent_row["task_key"],
        "privileged_call_index": parent_row["privileged_call_index"],
        "privileged_fn": parent_row["privileged_fn"],
        "label": parent_row["label"],
        "specified_fraction": parent_row["specified_fraction"],
        "actual_message_index": parent_row["actual_message_index"],
        "actual_call": parent_row["actual_call"],
        "completion": comp,
        "n_eligible_tool_spans": len(spans),
        "context_sha256": sha256_bytes(prompt_full.encode("utf-8")),
        "completion_sha256": sha256_bytes(comp.encode("utf-8")),
        "qwen_parent": q,
        "llama_r1": llama,
    }


# =============================================================================
# ANALYSIS
# =============================================================================

def classify_fraction(frac, specified_min=SPECIFIED_FRACTION_MIN, delegated_max=DELEGATED_FRACTION_MAX):
    if frac is None:
        return "UNCLASSIFIABLE"
    if frac >= specified_min:
        return "SPECIFIED"
    if frac <= delegated_max:
        return "DELEGATED"
    return "PARTIAL"


def quantile(sorted_vals, q):
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    w = pos - lo
    return sorted_vals[lo] * (1 - w) + sorted_vals[hi] * w


def per_task_label_values(records, scorer_key, field, relabel=None):
    buckets = defaultdict(lambda: defaultdict(list))
    for r in records:
        if relabel is None:
            label = r["label"]
        else:
            label = classify_fraction(r.get("specified_fraction"), relabel[0], relabel[1])
        if label not in {"SPECIFIED", "DELEGATED"}:
            continue
        v = r[scorer_key].get(field)
        if isinstance(v, bool):
            v = float(v)
        if v is None:
            continue
        v = float(v)
        if not math.isfinite(v):
            continue
        buckets[r["task_key"]][label].append(v)
    return {
        tk: {lab: statistics.mean(vals) for lab, vals in by.items() if vals}
        for tk, by in buckets.items()
    }


def clustered_group_contrast(records, scorer_key, field, relabel=None):
    taskvals = per_task_label_values(records, scorer_key, field, relabel)
    task_ids = sorted(taskvals)

    def calc(ids):
        sv, dv = [], []
        for tk in ids:
            d = taskvals.get(tk, {})
            if "SPECIFIED" in d:
                sv.append(d["SPECIFIED"])
            if "DELEGATED" in d:
                dv.append(d["DELEGATED"])
        if not sv or not dv:
            return None
        return statistics.mean(sv), statistics.mean(dv), statistics.mean(sv) - statistics.mean(dv), len(sv), len(dv)

    point = calc(task_ids)
    if point is None:
        return {"specified_mean": None, "delegated_mean": None, "difference": None, "ci95": [None, None]}
    ms, md, diff, ns, nd = point

    draws = []
    if ns >= MIN_TASKS_FOR_CI and nd >= MIN_TASKS_FOR_CI:
        rng = random.Random(BOOTSTRAP_SEED + sum(ord(c) for c in field))
        for _ in range(BOOTSTRAP_B):
            samp = [task_ids[rng.randrange(len(task_ids))] for _ in task_ids]
            z = calc(samp)
            if z is not None:
                draws.append(z[2])
    draws.sort()
    ci = [quantile(draws, 0.025), quantile(draws, 0.975)] if draws else [None, None]
    return {
        "specified_mean": ms,
        "delegated_mean": md,
        "difference": diff,
        "ci95": ci,
        "n_specified_tasks": ns,
        "n_delegated_tasks": nd,
        "bootstrap_valid_draws": len(draws),
    }


def rankdata(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and xs[order[j]] == xs[order[i]]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def pearson(xs, ys):
    if len(xs) < 3 or len(xs) != len(ys):
        return None
    mx, my = statistics.mean(xs), statistics.mean(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return num / (dx * dy) if dx and dy else None


def paired_corr(records, qfield, lfield=None, subset=None):
    if lfield is None:
        lfield = qfield
    rr = records
    if subset == "primary":
        rr = [r for r in rr if r["label"] in {"SPECIFIED", "DELEGATED"}]
    xs, ys = [], []
    for r in rr:
        x = r["qwen_parent"].get(qfield)
        y = r["llama_r1"].get(lfield)
        if x is None or y is None:
            continue
        x, y = float(x), float(y)
        if math.isfinite(x) and math.isfinite(y):
            xs.append(x); ys.append(y)
    return {
        "n": len(xs),
        "pearson": pearson(xs, ys),
        "spearman": pearson(rankdata(xs), rankdata(ys)) if len(xs) >= 3 else None,
    }


def h_agreement(records, field="H_mean_del", subset=None):
    rr = records
    if subset == "primary":
        rr = [r for r in rr if r["label"] in {"SPECIFIED", "DELEGATED"}]
    pairs = [(bool(r["qwen_parent"][field]), bool(r["llama_r1"][field])) for r in rr]
    return {
        "n": len(pairs),
        "agreement_rate": sum(a == b for a, b in pairs) / len(pairs) if pairs else None,
        "qwen_true_llama_false": sum(a and not b for a, b in pairs),
        "qwen_false_llama_true": sum((not a) and b for a, b in pairs),
    }


def analyze(records):
    if len(records) != EXPECTED_VALID_DECISIONS:
        raise RuntimeError("R1 analysis requires all 26 fixed valid decisions")

    primary = [r for r in records if r["label"] in {"SPECIFIED", "DELEGATED"}]
    llama_h = clustered_group_contrast(primary, "llama_r1", "H_mean_del")
    llama_m = clustered_group_contrast(primary, "llama_r1", "M_del")
    qwen_h = clustered_group_contrast(primary, "qwen_parent", "H_mean_del")
    qwen_m = clustered_group_contrast(primary, "qwen_parent", "M_del")

    lo = llama_h["ci95"][0]
    diff = llama_h["difference"]
    if diff is None:
        status = "INCOMPLETE"
    elif diff <= 0:
        status = "FAILURE_TO_REPLICATE_DIRECTION"
    elif lo is not None and lo > 0:
        status = "STRONG_REPLICATION"
    else:
        status = "DIRECTIONAL_REPLICATION"

    sensitivity = []
    for g in SENSITIVITY_GRID:
        relabel = (g["specified_min"], g["delegated_max"])
        sensitivity.append({
            **g,
            "primary_grid": g["specified_min"] == 0.8 and g["delegated_max"] == 0.2,
            "llama_H_mean_del": clustered_group_contrast(primary, "llama_r1", "H_mean_del", relabel),
            "llama_M_del": clustered_group_contrast(primary, "llama_r1", "M_del", relabel),
        })

    return {
        "analysis_timestamp_utc": now_utc(),
        "replication_status_predeclared": status,
        "fixed_sample": {
            "all_valid_decisions": len(records),
            "primary_extreme_label_decisions": len(primary),
            "primary_tasks": len({r["task_key"] for r in primary}),
        },
        "llama_primary_H_mean_del": llama_h,
        "llama_continuous_M_del": llama_m,
        "qwen_parent_recomputed_on_same_fixed_rows": {
            "H_mean_del": qwen_h,
            "M_del": qwen_m,
        },
        "cross_scorer": {
            "all_valid_H_mean_agreement": h_agreement(records, "H_mean_del"),
            "primary_H_mean_agreement": h_agreement(records, "H_mean_del", "primary"),
            "all_valid_H_max_agreement": h_agreement(records, "H_max_del"),
            "primary_H_max_agreement": h_agreement(records, "H_max_del", "primary"),
            "dU_del": paired_corr(records, "dU_del"),
            "mean_dS_del": paired_corr(records, "mean_dS_del"),
            "max_dS_del": paired_corr(records, "max_dS_del"),
            "M_del": paired_corr(records, "M_del"),
            "primary_dU_del": paired_corr(records, "dU_del", subset="primary"),
            "primary_mean_dS_del": paired_corr(records, "mean_dS_del", subset="primary"),
            "primary_M_del": paired_corr(records, "M_del", subset="primary"),
        },
        "sensitivity_grid": sensitivity,
        "guardrails": [
            "R1 changes only scorer; it does not establish full cross-agent generalization.",
            "R1 must not relabel, remap, or drop fixed A13 decisions based on Llama outcomes.",
            "R1 does not replace A14 causal provenance x N manipulation.",
            "A positive Llama contrast supports scorer-family robustness of the A13 association.",
        ],
    }


# =============================================================================
# REPORT / MANIFEST
# =============================================================================

def fnum(x, n=3):
    if x is None:
        return "NA"
    return f"{float(x):.{n}f}"


def make_report(protocol, results, records):
    h = results["llama_primary_H_mean_del"]
    m = results["llama_continuous_M_del"]
    ch = results["cross_scorer"]["primary_H_mean_agreement"]
    cm = results["cross_scorer"]["primary_M_del"]

    lines = []
    lines.append("# A13-R1 — Llama Scorer-Only Robustness Report")
    lines.append("")
    lines.append(f"- Status: **{results['replication_status_predeclared']}**")
    lines.append(f"- Frozen R1 protocol: `{protocol['protocol_hash']}`")
    lines.append(f"- Parent A13 protocol: `{EXPECTED_PARENT_PROTOCOL_HASH}`")
    lines.append(f"- Scorer: `{SCORER_MODEL}`")
    lines.append("- Agent trajectories/actions: exact frozen A13-Qwen traces/actions")
    lines.append(f"- Fixed valid decisions rescored: {len(records)} / {EXPECTED_VALID_DECISIONS}")
    lines.append("")
    lines.append("## Primary H_mean result")
    lines.append("")
    lines.append(
        f"SPECIFIED={fnum(h['specified_mean'])}, DELEGATED={fnum(h['delegated_mean'])}, "
        f"DIFF={fnum(h['difference'])}, 95% task-bootstrap CI=[{fnum(h['ci95'][0])}, {fnum(h['ci95'][1])}]"
    )
    lines.append("")
    lines.append("## Continuous M")
    lines.append("")
    lines.append(
        f"SPECIFIED={fnum(m['specified_mean'])}, DELEGATED={fnum(m['delegated_mean'])}, "
        f"DIFF={fnum(m['difference'])}, 95% task-bootstrap CI=[{fnum(m['ci95'][0])}, {fnum(m['ci95'][1])}]"
    )
    lines.append("")
    lines.append("## Cross-scorer agreement")
    lines.append("")
    lines.append(f"- Primary H_mean agreement: {fnum(ch['agreement_rate'])} ({ch['n']} decisions)")
    lines.append(f"- Primary M Pearson: {fnum(cm['pearson'])}")
    lines.append(f"- Primary M Spearman: {fnum(cm['spearman'])}")
    lines.append("")
    lines.append("## Interpretation guardrail")
    lines.append("")
    lines.append(
        "R1 is a fixed-trace scorer-family robustness test. It does not test whether Llama as an AgentDojo agent "
        "produces the same task population; that is A13-R2. It also does not establish causality; A14 remains required."
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_manifest(protocol):
    files = [PROTOCOL_PATH, DECISIONS_PATH, RESULTS_PATH, REPORT_PATH, CHECKPOINT_PATH]
    obj = {
        "created_at_utc": now_utc(),
        "protocol_hash": protocol["protocol_hash"],
        "source_sha256": source_sha256(),
        "parent_a13_manifest_sha256": EXPECTED_PARENT_MANIFEST_SHA256,
        "files": {
            str(p.resolve()): {"sha256": sha256_file(p), "bytes": p.stat().st_size}
            for p in files if p.exists()
        },
    }
    dump_json(MANIFEST_PATH, obj)


# =============================================================================
# MAIN
# =============================================================================

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--validate-parent-only",
        action="store_true",
        help="validate the exact parent A13 artifacts and exit without needing Llama vLLM",
    )
    args = ap.parse_args()

    print("=" * 92)
    print("A13-R1 — FIXED-TRACE LLAMA SCORER ROBUSTNESS")
    print("=" * 92)

    parent = validate_parent_manifest()
    if args.validate_parent_only:
        print("[done] parent-only validation PASS; no outcome scoring performed")
        return

    server_preflight()
    protocol = build_protocol(parent)
    freeze_or_verify_protocol(protocol)

    # Resume is safe only under the exact frozen protocol. Checkpoint rows are
    # keyed by the already-frozen decision ids; no outcomes can change sampling.
    done = {}
    if CHECKPOINT_PATH.exists():
        for r in read_jsonl(CHECKPOINT_PATH):
            done[r["decision_id"]] = r
        unknown = set(done) - set(protocol["fixed_valid_decision_ids"])
        if unknown:
            sys.exit(f"FATAL: checkpoint has non-frozen decision ids: {sorted(unknown)}")
        print(f"[resume] {len(done)} / {EXPECTED_VALID_DECISIONS} fixed decisions already checkpointed")

    for idx, pr in enumerate(parent["valid"], 1):
        did = pr["decision_id"]
        if did in done:
            print(f"[{idx:02d}/{EXPECTED_VALID_DECISIONS}] SKIP checkpointed {did}")
            continue
        print(f"[{idx:02d}/{EXPECTED_VALID_DECISIONS}] score {did} label={pr['label']} N={pr['n_eligible_tool_spans']}")
        try:
            rr = rescore_one(pr)
        except Exception as e:
            print(f"FATAL: fixed decision scoring failed for {did}: {type(e).__name__}: {e}")
            print("The fixed sample must not silently drop failures. Fix the scorer/server and rerun; checkpointed rows are preserved.")
            sys.exit(2)
        done[did] = rr
        ordered = [done[x] for x in protocol["fixed_valid_decision_ids"] if x in done]
        write_jsonl(CHECKPOINT_PATH, ordered)
        lm = rr["llama_r1"]
        print(
            f"    Llama Hmean={lm['H_mean_del']} M={lm['M_del']:.6f} "
            f"dU={lm['dU_del']:.6f} mean_dS={lm['mean_dS_del']:.6f} tokens={lm['completion_tokens']}"
        )

    if len(done) != EXPECTED_VALID_DECISIONS:
        sys.exit(f"FATAL: expected all 26 fixed decisions, have {len(done)}")

    records = [done[x] for x in protocol["fixed_valid_decision_ids"]]
    write_jsonl(DECISIONS_PATH, records)
    results = analyze(records)
    dump_json(RESULTS_PATH, results)
    make_report(protocol, results, records)
    write_manifest(protocol)

    # Checkpoint is redundant after a complete atomic final write; preserve it
    # as run provenance rather than deleting it.
    print("\n" + "=" * 92)
    print("A13-R1 COMPLETE")
    print("=" * 92)
    h = results["llama_primary_H_mean_del"]
    m = results["llama_continuous_M_del"]
    print(f"STATUS: {results['replication_status_predeclared']}")
    print(
        "PRIMARY H_mean task-weighted:\n"
        f"  SPECIFIED={h['specified_mean']}  DELEGATED={h['delegated_mean']}  "
        f"DIFF={h['difference']}  CI={h['ci95']}"
    )
    print(
        "CONTINUOUS M task-weighted:\n"
        f"  SPECIFIED={m['specified_mean']}  DELEGATED={m['delegated_mean']}  "
        f"DIFF={m['difference']}  CI={m['ci95']}"
    )
    print(f"Read: {REPORT_PATH}")
    print(f"Raw:  {DECISIONS_PATH}")
    print(f"JSON: {RESULTS_PATH}")
    print("Do not tune labels, thresholds, spans, or endpoints based on this output.")


if __name__ == "__main__":
    main()
