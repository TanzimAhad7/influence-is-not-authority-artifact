#!/usr/bin/env python3
"""
A15a-00 PREPARE/FREEZE — NO MODEL/API CALLS

Purpose:
  Reuse the exact frozen A13 benign successful-decision corpus and compute the
  paper-faithful CausalArmor tau=0 activation inventory from already-existing
  A13 deletion attributions. Then freeze the sanitizer jobs and consequence
  endpoints BEFORE any sanitizer output/latency is observed.

Scientific status:
  - The A13 attribution outcomes already exist; therefore the activation rate
    computed here is NOT a new preregistered attribution result.
  - The NEW prospective A15a outcomes are sanitizer invocation cost/latency and
    preservation diagnostics under a frozen job list.
"""
from __future__ import annotations
import json, sys, datetime as dt
from collections import Counter, defaultdict
from pathlib import Path
from a15a_common import *

PROTOCOL_PATH = OUT_DIR / "protocol.json"
INVENTORY_PATH = OUT_DIR / "decision_inventory.jsonl"
JOBS_PATH = OUT_DIR / "sanitizer_jobs.jsonl"
PREP_REPORT = OUT_DIR / "PREP_REPORT.md"

def locate_task_log(results: dict, suite: str, user_task: str) -> Path | None:
    for r in results.get("task_execution_status", []):
        if r.get("suite") == suite and r.get("user_task") == user_task:
            p = r.get("log_path")
            if p:
                pp = Path(p)
                if pp.exists():
                    return pp
                # Fall back to locating by basename underneath current a13 dir.
                basename = pp.name
                matches = list((A13_DIR / "agentdojo_runs").rglob(basename))
                if len(matches) == 1:
                    return matches[0]
    # Generic fallback based on suite/task substrings.
    candidates = []
    for p in (A13_DIR / "agentdojo_runs").rglob("*.json"):
        s = str(p)
        if suite in s and user_task in s:
            candidates.append(p)
    return candidates[0] if len(candidates) == 1 else None

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    missing = [str(p) for p in PARENT_FILES if not p.exists()]
    if missing:
        sys.exit("FATAL missing A13 parent files:\n  " + "\n  ".join(missing))

    decisions = read_jsonl(A13_DIR / "decisions.jsonl")
    results = json.loads((A13_DIR / "results.json").read_text(encoding="utf-8"))
    taxonomy = json.loads((A13_DIR / "taxonomy.json").read_text(encoding="utf-8"))
    a13_protocol = json.loads((A13_DIR / "protocol.json").read_text(encoding="utf-8"))

    # A15a eligible corpus: every A13 decision that already passed A13's frozen
    # benign execution + mapping + single-call + span completeness rules.
    eligible = [r for r in decisions if r.get("primary_valid") and not r.get("development")]
    if not eligible:
        sys.exit("FATAL: zero eligible A13 primary_valid decisions.")

    inventory = []
    jobs = []
    raw_log_hashes = {}
    unresolved_logs = []

    for r in eligible:
        du = r.get("dU_del")
        spans = r.get("spans") or []
        if du is None or not spans:
            sys.exit(f"FATAL: eligible decision lacks dU/spans: {r.get('decision_id')}")

        dss = [s.get("delta_del") for s in spans]
        if any(x is None for x in dss):
            sys.exit(f"FATAL: eligible decision has incomplete delta_del spans: {r.get('decision_id')}")

        # Paper Eq.5 at tau=0: B = {S: dS > dU - tau}
        flagged_local = [i for i, x in enumerate(dss) if x > du - TAU_PRIMARY]
        ca_flag = bool(flagged_local)

        log_path = locate_task_log(results, r["suite"], r["user_task"])
        if log_path is None:
            unresolved_logs.append(r["decision_id"])
            continue

        raw_log_hashes[str(log_path.relative_to(PROJECT_ROOT))] = sha256_file(log_path)
        log_obj = json.loads(log_path.read_text(encoding="utf-8"))
        msgs = list(log_obj.get("messages") or [])
        mi = int(r["actual_message_index"])
        if not (0 <= mi <= len(msgs)):
            sys.exit(f"FATAL bad actual_message_index for {r['decision_id']}: {mi}")

        ctx = msgs[:mi]
        user_msgs = [m for m in ctx if m.get("role") == "user"]
        if not user_msgs:
            sys.exit(f"FATAL no user message in raw context: {r['decision_id']}")
        user_request = mt(user_msgs[0])

        inv = {
            "decision_id": r["decision_id"],
            "suite": r["suite"],
            "user_task": r["user_task"],
            "task_key": r["task_key"],
            "label": r["label"],
            "specified_fraction": r.get("specified_fraction"),
            "privileged_fn": r["privileged_fn"],
            "actual_call": r.get("actual_call"),
            "actual_message_index": mi,
            "utility": bool(r.get("utility")),
            "security": r.get("security"),
            "n_eligible_tool_spans": len(spans),
            "dU_del": du,
            "dS_del": dss,
            "max_dS_del": max(dss),
            "ca_margin_tau0": du - max(dss),
            "ca_flag_tau0": ca_flag,
            "flagged_span_local_indices_tau0": flagged_local,
            "n_flagged_spans_tau0": len(flagged_local),
            "raw_log_path": str(log_path.relative_to(PROJECT_ROOT)),
            "raw_log_sha256": raw_log_hashes[str(log_path.relative_to(PROJECT_ROOT))],
        }
        inventory.append(inv)

        for local_i in flagged_local:
            s = spans[local_i]
            msg_i = int(s["message_index"])
            if not (0 <= msg_i < len(ctx)):
                sys.exit(f"FATAL span message index out of range: {r['decision_id']} span={msg_i}")
            tm = ctx[msg_i]
            if tm.get("role") != "tool":
                sys.exit(f"FATAL flagged span does not map to tool message: {r['decision_id']} span={msg_i}")
            content = mt(tm)
            tool_name = infer_tool_name(tm)
            user_prompt = SANITIZER_USER_TEMPLATE.format(
                user_request=user_request,
                tool_name=tool_name,
                untrusted_content=content,
            )
            job_id = f"{r['decision_id']}::span{local_i}::msg{msg_i}"
            jobs.append({
                "job_id": job_id,
                "decision_id": r["decision_id"],
                "suite": r["suite"],
                "user_task": r["user_task"],
                "task_key": r["task_key"],
                "label": r["label"],
                "privileged_fn": r["privileged_fn"],
                "span_local_index": local_i,
                "span_message_index": msg_i,
                "span_delta_del": dss[local_i],
                "dU_del": du,
                "tool_name": tool_name,
                "user_request": user_request,
                "untrusted_content": content,
                "system_prompt": SANITIZER_SYSTEM_PROMPT,
                "user_prompt": user_prompt,
                "prompt_sha256": sha256_text(SANITIZER_SYSTEM_PROMPT + "\n" + user_prompt),
            })

    if unresolved_logs:
        sys.exit(
            "FATAL: could not resolve raw A13 logs for eligible decisions:\n  "
            + "\n  ".join(unresolved_logs)
        )

    if len(inventory) != len(eligible):
        sys.exit(f"FATAL inventory mismatch: eligible={len(eligible)} inventory={len(inventory)}")

    write_jsonl(INVENTORY_PATH, inventory)
    write_jsonl(JOBS_PATH, jobs)

    parent = parent_hashes()
    protocol_core = {
        "study": "A15a — benign selectivity and sanitizer-overhead consequence",
        "scientific_status": (
            "A13 attribution outcomes are pre-existing. A15a freezes the full eligible A13 benign "
            "decision corpus and exact sanitizer job list before any sanitizer output or sanitizer "
            "latency outcome is observed."
        ),
        "prepared_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "parent_a13": {
            "protocol_hash": a13_protocol.get("protocol_hash"),
            "taxonomy_hash": taxonomy.get("taxonomy_hash"),
            "parent_hashes": parent,
            "raw_log_hashes": raw_log_hashes,
        },
        "eligibility": (
            "All A13 rows with primary_valid=true and development=false. No new attribution-based "
            "selection. PARTIAL is retained descriptively; SPECIFIED/DELEGATED are the frozen A13 labels."
        ),
        "causalarmor_activation": {
            "attribution_source": "exact pre-existing A13 Qwen deletion scores",
            "primary_tau": TAU_PRIMARY,
            "rule": "flag span iff delta_S_del > delta_U_del - tau; activate iff >=1 span flagged",
            "important_status": (
                "Activation-rate analysis is a consequence reuse of existing A13 scores, not a new "
                "independent attribution confirmation."
            ),
        },
        "sanitizer": {
            "model": SANITIZER_MODEL,
            "provider_route": SANITIZER_PROVIDER,
            "base_url": SANITIZER_BASE_URL,
            "paper_model_match": "same model identifier as paper sanitizer; access route differs from paper Vertex AI",
            "system_prompt_sha256": sha256_text(SANITIZER_SYSTEM_PROMPT),
            "user_template_sha256": sha256_text(SANITIZER_USER_TEMPLATE),
            "job_count": len(jobs),
            "job_list_sha256": sha256_file(JOBS_PATH),
        },
        "primary_A15a_endpoints": [
            "decision_activation_rate_tau0 among A13 primary_valid benign decisions",
            "external_sanitizer_calls_per_eligible_decision",
            "external_sanitizer_calls_per_activated_decision",
            "measured sanitizer wall-clock latency per call and per activated decision",
        ],
        "secondary_endpoints": [
            "SPECIFIED vs DELEGATED activation and sanitizer-call breakdown",
            "PARTIAL descriptive breakdown",
            "flagged-span fraction among eligible tool spans",
            "sanitized-output length and lexical/numeric preservation diagnostics",
            "stored A13 task-duration comparison labeled deployment-specific/descriptive",
        ],
        "interpretation_guardrails": [
            "Do not count A13 non-execution as defense success.",
            "Do not call sanitizer latency source-fidelity Vertex latency.",
            "Do not call this full end-to-end utility; Stage-1 sanitizer cost is a lower bound on the full defense path.",
            "Do not claim the existing A13 activation rate is newly preregistered.",
            "Do not tune tau after sanitizer outcomes.",
        ],
        "artifacts": {
            "decision_inventory_sha256": sha256_file(INVENTORY_PATH),
            "sanitizer_jobs_sha256": sha256_file(JOBS_PATH),
        },
    }
    # Freeze hash excluding timestamps/hash field itself, but parent and job list are exact.
    hashable = dict(protocol_core)
    hashable.pop("prepared_at_utc", None)
    protocol_hash = sha256_text(stable_json(hashable))
    protocol_core["protocol_hash"] = protocol_hash

    if PROTOCOL_PATH.exists():
        old = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        if old.get("protocol_hash") != protocol_hash:
            sys.exit(
                "FATAL: existing A15a protocol differs. Refusing overwrite.\n"
                f"old={old.get('protocol_hash')} new={protocol_hash}"
            )
        print(f"[A15a-00] existing protocol matches: {protocol_hash}")
    else:
        dump_json(PROTOCOL_PATH, protocol_core)
        print(f"[A15a-00] FROZEN BEFORE SANITIZER OUTCOMES: {protocol_hash}")

    by_label = Counter(r["label"] for r in inventory)
    flags_by_label = Counter(r["label"] for r in inventory if r["ca_flag_tau0"])
    report = [
        "# A15a Preparation Report",
        "",
        f"- Eligible A13 benign decisions: **{len(inventory)}**",
        f"- Frozen sanitizer jobs: **{len(jobs)}**",
        f"- A15a protocol hash: `{protocol_hash}`",
        f"- Decision labels: `{dict(by_label)}`",
        f"- Activated decisions by label at tau=0 from existing A13 scores: `{dict(flags_by_label)}`",
        "",
        "No sanitizer/API calls were made by A15a-00.",
        "",
        "The activation counts above reuse pre-existing A13 attribution outcomes and are not a new",
        "independent confirmation. The prospective A15a outcomes begin with sanitizer execution.",
    ]
    PREP_REPORT.write_text("\n".join(report) + "\n", encoding="utf-8")

    print(f"[A15a-00] eligible={len(inventory)} sanitizer_jobs={len(jobs)}")
    print(f"[A15a-00] label_counts={dict(by_label)}")
    print(f"[A15a-00] activated_by_label_tau0={dict(flags_by_label)}")
    print("[A15a-00] NO sanitizer/API calls emitted.")
    print(f"[A15a-00] Read: {PREP_REPORT}")

if __name__ == "__main__":
    main()
