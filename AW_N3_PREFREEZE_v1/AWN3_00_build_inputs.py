#!/usr/bin/env python3
"""
Build the exact AW-N3 paired-trace inputs from frozen N3 contexts/scoring units.

ZERO model/provider calls. ZERO AgentWatcher outcomes.
This stage exists to mechanically establish the scientific denominator and whether
SHAM/ECHO descendants collapse to byte-identical AgentWatcher static inputs.
"""
from __future__ import annotations

import argparse
import collections
from pathlib import Path

from awn3_common import *


def tool_segments_from_messages(msgs):
    segs = []
    for i, m in enumerate(msgs):
        if m.get("role") != "tool":
            continue
        txt = text_content(m)
        if not txt.strip():
            continue
        segs.append({
            "message_index": i,
            "component_id": m.get("component_id"),
            "tool_name": m.get("tool_name") or (m.get("tool_call") or {}).get("function"),
            "content": txt,
            "content_sha256": sha256_bytes(txt.encode("utf-8")),
        })
    return segs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=".")
    ap.add_argument("--run-dir", default="AW_N3_AUTHOR_v1")
    args = ap.parse_args()

    paths = project_paths(Path(args.project_root), Path(args.run_dir))
    root, out, n3 = paths["root"], paths["run"], paths["n3"]
    out.mkdir(parents=True, exist_ok=True)

    if (out / "AWN3_SCIENCE_UNIQUE_OUTPUTS.jsonl").exists():
        raise SystemExit("FATAL: scientific outcomes already exist in run-dir; refuse to rebuild prefreeze inputs")
    if (out / "AWN3_FREEZE.json").exists():
        raise SystemExit("FATAL: AWN3_FREEZE.json already exists; do not mutate inputs after freeze")

    parent_hashes = validate_parent_sources(root)

    audits = read_jsonl(n3 / "N3_HUMAN_AUDIT.jsonl")
    if len(audits) != 24 or {r.get("author_decision") for r in audits} != {"PASS"}:
        raise RuntimeError("N3 human audit is not exactly 24/24 PASS")
    audit_bases = {r["base_id"] for r in audits}

    contexts = read_jsonl(n3 / "N3_POSITIVE_CONTEXTS.jsonl")
    units = read_jsonl(n3 / "N3_POSITIVE_SCORING_UNITS.jsonl")
    if len(contexts) != 96:
        raise RuntimeError(f"expected 96 N3 positive contexts, got {len(contexts)}")
    if len(units) != 192:
        raise RuntimeError(f"expected 192 N3 positive scoring units, got {len(units)}")

    context_by = {r["context_id"]: r for r in contexts}
    if len(context_by) != 96:
        raise RuntimeError("N3 positive context IDs are not unique")
    base_ids = sorted({r["base_id"] for r in contexts})
    if len(base_ids) != 24 or set(base_ids) != audit_bases:
        raise RuntimeError("N3 context base set does not match the 24/24 human-audited base set")

    rows = []
    for u in sorted(units, key=lambda x: x["unit_id"]):
        if (u["directive_arm"], u["action_role"]) not in ALL_STATES:
            raise RuntimeError(f"unexpected N3 state: {(u['directive_arm'], u['action_role'])}")
        cobj = context_by.get(u["context_id"])
        if cobj is None:
            raise RuntimeError(f"missing context for {u['unit_id']}")
        if cobj["base_id"] != u["base_id"] or cobj["descendant"] != u["descendant"] or cobj["directive_arm"] != u["directive_arm"]:
            raise RuntimeError(f"context/unit identity drift for {u['unit_id']}")

        ctx = cobj["context"]
        msgs = list(ctx.get("messages") or [])
        users = [m for m in msgs if m.get("role") == "user"]
        if len(users) != 1:
            raise RuntimeError(f"{u['unit_id']}: expected exactly one user message, got {len(users)}")
        target_task = text_content(users[0])
        tools = tool_segments_from_messages(msgs)
        if not tools:
            raise RuntimeError(f"{u['unit_id']}: no nonempty tool-result segments")
        external_context = "\n\n".join(s["content"] for s in tools)
        target_action = u["target_action"]
        target_action_text = action_string(target_action)

        # Frozen oracle relation must remain AUTH=ALLOW / ALT=DENY.
        expected_oracle = "ALLOW" if u["action_role"] == "AUTH" else "DENY"
        if u.get("oracle_status") != expected_oracle:
            raise RuntimeError(
                f"{u['unit_id']}: oracle drift action_role={u['action_role']} oracle={u.get('oracle_status')} expected={expected_oracle}"
            )

        aw_static = {
            "target_task": target_task,
            "external_context": external_context,
            "target_action_text": target_action_text,
        }
        static_hash = stable_hash(aw_static)

        # Useful pre-outcome diagnostics only: which action argument values are literally present
        # in the external context and user request. These do not use any monitor outcome.
        ext_norm = normalize_for_match(external_context)
        user_norm = normalize_for_match(target_task)
        action_values = sorted(set(scalar_leaves(target_action.get("args") or {})))
        present_external = sorted(v for v in action_values if normalize_for_match(v) in ext_norm)
        present_user = sorted(v for v in action_values if normalize_for_match(v) in user_norm)

        state_name = f"{u['directive_arm']}__{u['action_role']}"
        rows.append({
            "schema": "AWN3_INPUT_V1_2026-08-19",
            "unit_id": u["unit_id"],
            "context_id": u["context_id"],
            "base_id": u["base_id"],
            "family": u["family"],
            "descendant": u["descendant"],
            "directive_arm": u["directive_arm"],
            "action_role": u["action_role"],
            "state": state_name,
            "is_primary_state": (u["directive_arm"], u["action_role"]) in PRIMARY_STATES,
            "is_secondary_action_control_state": (u["directive_arm"], u["action_role"]) in SECONDARY_STATES,
            "oracle_status": u["oracle_status"],
            "oracle_reasons": u.get("oracle_reasons") or [],
            "target_task": target_task,
            "target_task_sha256": sha256_bytes(target_task.encode("utf-8")),
            "tool_segments": tools,
            "external_context": external_context,
            "external_context_sha256": sha256_bytes(external_context.encode("utf-8")),
            "target_action": target_action,
            "target_action_text": target_action_text,
            "target_action_text_sha256": sha256_bytes(target_action_text.encode("utf-8")),
            "target_action_n3_sha256": u["target_action_sha256"],
            "agentwatcher_static_input_sha256": static_hash,
            "action_values_present_in_external_context": present_external,
            "action_values_present_in_user_task": present_user,
            "parent_n3_context_sha256": u.get("context_sha256"),
            "parent_n3_prompt_sha256": u.get("prompt_sha256"),
        })

    # Exact expected 2x2 x descendant census.
    state_counts = collections.Counter((r["directive_arm"], r["action_role"], r["descendant"]) for r in rows)
    expected_states = {
        (d, a, x): 24
        for d, a in sorted(ALL_STATES)
        for x in ("SHAM", "ECHO")
    }
    if dict(state_counts) != expected_states:
        raise RuntimeError(f"state census drift: got={dict(state_counts)} expected={expected_states}")

    # Mechanical SHAM/ECHO identity audit under the exact A15b-0 AgentWatcher static triple.
    grouped = collections.defaultdict(list)
    for r in rows:
        grouped[(r["base_id"], r["directive_arm"], r["action_role"])].append(r)
    pair_audit = []
    for key, rr in sorted(grouped.items()):
        if len(rr) != 2 or {x["descendant"] for x in rr} != {"SHAM", "ECHO"}:
            raise RuntimeError(f"{key}: expected exactly SHAM/ECHO pair")
        hs = {x["agentwatcher_static_input_sha256"] for x in rr}
        same = len(hs) == 1
        pair_audit.append({
            "base_id": key[0],
            "directive_arm": key[1],
            "action_role": key[2],
            "static_input_identical": same,
            "static_input_sha256": next(iter(hs)) if same else None,
            "sham_unit_id": next(x["unit_id"] for x in rr if x["descendant"] == "SHAM"),
            "echo_unit_id": next(x["unit_id"] for x in rr if x["descendant"] == "ECHO"),
        })

    n_identical = sum(x["static_input_identical"] for x in pair_audit)
    if n_identical != 96:
        # This is a hard pre-outcome finding. Do not silently assume the expected denominator.
        execution_rows = list(rows)
        dedup_rule = "SHAM_ECHO_NOT_UNIVERSALLY_IDENTICAL__EXECUTE_ALL_192"
    else:
        by_hash = collections.defaultdict(list)
        for r in rows:
            by_hash[r["agentwatcher_static_input_sha256"]].append(r)
        # No cross-state/base collision is allowed. Every unique static input must represent
        # exactly the two descendants of one base/directive/action state.
        for h, rr in by_hash.items():
            keys = {(x["base_id"], x["directive_arm"], x["action_role"]) for x in rr}
            if len(rr) != 2 or len(keys) != 1 or {x["descendant"] for x in rr} != {"SHAM", "ECHO"}:
                raise RuntimeError(f"unexpected global static-input collision {h}: {[x['unit_id'] for x in rr]}")
        execution_rows = []
        for h in sorted(by_hash):
            rr = sorted(by_hash[h], key=lambda x: x["descendant"])
            representative = dict(rr[0])
            representative["mapped_unit_ids"] = [x["unit_id"] for x in rr]
            representative["mapped_descendants"] = [x["descendant"] for x in rr]
            execution_rows.append(representative)
        dedup_rule = "ALL_96_SHAM_ECHO_STATE_PAIRS_IDENTICAL__EXECUTE_96_UNIQUE_STATIC_INPUTS"

    primary_raw = [r for r in rows if r["is_primary_state"]]
    secondary_raw = [r for r in rows if r["is_secondary_action_control_state"]]
    primary_unique = {r["agentwatcher_static_input_sha256"] for r in primary_raw}
    secondary_unique = {r["agentwatcher_static_input_sha256"] for r in secondary_raw}

    if n_identical == 96:
        if len(execution_rows) != 96 or len(primary_unique) != 48 or len(secondary_unique) != 48:
            raise RuntimeError(
                f"unexpected proven-dedup denominator: full={len(execution_rows)} primary={len(primary_unique)} secondary={len(secondary_unique)}"
            )

    write_jsonl(out / "AWN3_ALL_192_INPUTS.jsonl", rows)
    write_jsonl(out / "AWN3_EXECUTION_INPUTS.jsonl", execution_rows)
    write_jsonl(out / "AWN3_SHAM_ECHO_STATIC_IDENTITY_AUDIT.jsonl", pair_audit)

    summary = {
        "schema": "AWN3_PREFREEZE_BUILD_V1_2026-08-19",
        "created_at_utc": now_utc(),
        "project_root": str(root),
        "n_bases": len(base_ids),
        "base_ids": base_ids,
        "raw_condition_rows": len(rows),
        "raw_primary_rows": len(primary_raw),
        "raw_secondary_action_control_rows": len(secondary_raw),
        "sham_echo_state_pairs": len(pair_audit),
        "sham_echo_identical_pairs": n_identical,
        "unique_static_inputs": len({r["agentwatcher_static_input_sha256"] for r in rows}),
        "primary_unique_static_inputs": len(primary_unique),
        "secondary_unique_static_inputs": len(secondary_unique),
        "execution_rows": len(execution_rows),
        "dedup_rule": dedup_rule,
        "state_counts": {f"{k[0]}__{k[1]}__{k[2]}": v for k, v in sorted(state_counts.items())},
        "primary_states": sorted([f"{x[0]}__{x[1]}" for x in PRIMARY_STATES]),
        "secondary_states": sorted([f"{x[0]}__{x[1]}" for x in SECONDARY_STATES]),
        "parent_hashes": parent_hashes,
        "output_hashes": {
            "AWN3_ALL_192_INPUTS.jsonl": sha256_file(out / "AWN3_ALL_192_INPUTS.jsonl"),
            "AWN3_EXECUTION_INPUTS.jsonl": sha256_file(out / "AWN3_EXECUTION_INPUTS.jsonl"),
            "AWN3_SHAM_ECHO_STATIC_IDENTITY_AUDIT.jsonl": sha256_file(out / "AWN3_SHAM_ECHO_STATIC_IDENTITY_AUDIT.jsonl"),
        },
        "no_model_provider_calls": True,
        "no_agentwatcher_outcomes_generated": True,
        "status": "PREFREEZE_BUILD_COMPLETE_NOT_YET_FROZEN",
    }
    write_json(out / "AWN3_PREFREEZE_BUILD_SUMMARY.json", summary)

    print("[AWN3-00] PREFREEZE BUILD PASS")
    print(f"[AWN3-00] bases={summary['n_bases']} raw_conditions={summary['raw_condition_rows']}")
    print(f"[AWN3-00] SHAM/ECHO identical state-pairs={n_identical}/{len(pair_audit)}")
    print(
        f"[AWN3-00] unique_static_inputs={summary['unique_static_inputs']} "
        f"primary={summary['primary_unique_static_inputs']} secondary={summary['secondary_unique_static_inputs']}"
    )
    print(f"[AWN3-00] execution_rows={summary['execution_rows']} dedup={dedup_rule}")
    print("[AWN3-00] FULL 2x2 action-control extension INCLUDED pre-outcome")
    print("[AWN3-00] NO model/provider calls; NO AgentWatcher outcomes")
    print(f"[AWN3-00] summary={out / 'AWN3_PREFREEZE_BUILD_SUMMARY.json'}")
    print("[AWN3-00] STOP BEFORE FREEZE; review this author-side denominator first")


if __name__ == "__main__":
    main()
