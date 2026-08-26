#!/usr/bin/env python3
"""
Build and hash the A15b-0 controlled and natural paired-trace inputs.

NO model/API/AgentWatcher calls are made.
NO scientific detector outcomes are generated.
"""
from __future__ import annotations
import collections
import copy
import sys
from pathlib import Path

from a15b0_common import *

A13_DIR = PROJECT_ROOT / "a13"
A15A_DIR = PROJECT_ROOT / "a15a_selectivity_consequence"
A14_DIR = PROJECT_ROOT / "a14_minimal_factorial"
B1_DIR = PROJECT_ROOT / "b1_a12_backbone_replication"

def validate_b1():
    p = B1_DIR / "protocol.json"
    if not p.is_file():
        raise RuntimeError("B1 is not frozen: b1_a12_backbone_replication/protocol.json missing")
    d = read_json(p)
    if d.get("protocol_hash") != EXPECTED_B1_PROTOCOL_HASH:
        raise RuntimeError(
            f"B1 protocol hash mismatch: {d.get('protocol_hash')} != {EXPECTED_B1_PROTOCOL_HASH}"
        )
    # Strong pre-outcome invariant: no B1 results directory/outcomes should exist yet.
    outcome_like = []
    for pat in ("**/results.json", "**/decisions.jsonl", "**/agentdojo_runs/**/*.json"):
        outcome_like.extend(B1_DIR.glob(pat))
    # protocol/manifests are allowed; actual run artifacts are not.
    outcome_like = [p for p in outcome_like if p.name not in {"task_manifest.json"}]
    if outcome_like:
        raise RuntimeError(
            "B1 scientific-looking artifacts already exist before A15b-0 freeze:\n  "
            + "\n  ".join(str(p) for p in outcome_like[:20])
        )
    return {"protocol_hash": d["protocol_hash"], "protocol_file_sha256": sha256_file(p)}

def validate_a13():
    require_file(A13_DIR / "protocol.json", EXPECTED_A13_PROTOCOL_FILE_SHA256)
    require_file(A13_DIR / "decisions.jsonl", EXPECTED_A13_DECISIONS_SHA256)
    require_file(A13_DIR / "manifest.json", EXPECTED_A13_MANIFEST_SHA256)
    require_file(A13_DIR / "results.json", EXPECTED_A13_RESULTS_SHA256)
    proto = read_json(A13_DIR / "protocol.json")
    if proto.get("protocol_hash") != EXPECTED_A13_PROTOCOL_HASH:
        raise RuntimeError("embedded A13 protocol hash drift")
    rows = read_jsonl(A13_DIR / "decisions.jsonl")
    valid = [r for r in rows if r.get("primary_valid") and not r.get("development")]
    if len(valid) != 26:
        raise RuntimeError(f"expected 26 A13 valid decisions, got {len(valid)}")
    return valid

def trace_path(row):
    raw = row.get("raw_log_path")
    if raw:
        p = PROJECT_ROOT / raw
        if p.is_file():
            return p
    p = A13_DIR / "agentdojo_runs" / "vllm_parsed" / row["suite"] / row["user_task"] / "none" / "none.json"
    if p.is_file():
        return p
    hits = list((A13_DIR / "agentdojo_runs" / "vllm_parsed" / row["suite"] / row["user_task"]).glob("**/none.json"))
    if len(hits) == 1:
        return hits[0]
    raise RuntimeError(f"cannot resolve unique raw trace for {row['decision_id']}: {hits}")

def tool_segments_from_messages(msgs):
    segs = []
    for i, m in enumerate(msgs):
        if m.get("role") != "tool":
            continue
        txt = text_content(m)
        if not txt.strip():
            continue
        tc = m.get("tool_call") or {}
        segs.append({
            "message_index": i,
            "tool_name": tc.get("function"),
            "content": txt,
            "content_sha256": sha256_bytes(txt.encode("utf-8")),
        })
    return segs

def external_context_string(tool_segments):
    # Paired-trace serialization is deliberately simple and outcome-independent:
    # raw tool-result text in chronological order, separated only by blank lines.
    return "\n\n".join(s["content"] for s in tool_segments)

def natural_manifest(a13_valid):
    require_file(A15A_DIR / "decision_inventory.jsonl", EXPECTED_A15A_INVENTORY_SHA256)
    inv = read_jsonl(A15A_DIR / "decision_inventory.jsonl")
    if len(inv) != 26:
        raise RuntimeError(f"expected 26 A15a inventory rows, got {len(inv)}")
    inv_by = {r["decision_id"]: r for r in inv}
    a13_by = {r["decision_id"]: r for r in a13_valid}
    if set(inv_by) != set(a13_by):
        raise RuntimeError("A15a decision inventory IDs are not exactly the 26 frozen A13 valid IDs")

    out = []
    for did in sorted(inv_by):
        a = a13_by[did]
        old = inv_by[did]
        tp = trace_path(old)
        if old.get("raw_log_sha256"):
            require_file(tp, old["raw_log_sha256"])
        log = read_json(tp)
        msgs = list(log.get("messages") or [])
        mi = int(a["actual_message_index"])
        if not (0 < mi <= len(msgs)):
            raise RuntimeError(f"bad target message index for {did}")
        ctx_msgs = msgs[:mi]
        users = [text_content(m) for m in ctx_msgs if m.get("role") == "user" and text_content(m).strip()]
        if not users:
            raise RuntimeError(f"no user task in {did}")
        target_task = users[0]
        tools = tool_segments_from_messages(ctx_msgs)
        if len(tools) != int(a["n_eligible_tool_spans"]):
            raise RuntimeError(
                f"tool-span drift for {did}: manifest={len(tools)} A13={a['n_eligible_tool_spans']}"
            )
        ext = external_context_string(tools)
        action = a["actual_call"]
        astr = action_string(action)
        if astr != a.get("completion"):
            raise RuntimeError(f"canonical action serialization drift for {did}")

        # Deterministic, pre-outcome diagnostic: action-argument scalar values that
        # appear in prior external tool text but not literally in the user request.
        ext_norm = normalize_for_match(ext)
        user_norm = normalize_for_match(target_task)
        tool_derived_values = []
        for v in scalar_leaves(action.get("args") or {}):
            vv = normalize_for_match(v)
            if len(vv) < 2:
                continue
            if vv in ext_norm and vv not in user_norm:
                tool_derived_values.append(v)
        tool_derived_values = sorted(set(tool_derived_values))

        out.append({
            "schema_version": "A15B0_NATURAL_INPUT_V1",
            "arm": "A15B0-B_NATURAL",
            "decision_id": did,
            "cluster_id": a["task_key"],  # task/episode cluster for inference
            "suite": a["suite"],
            "user_task_id": a["user_task"],
            "label": a["label"],
            "specified_fraction": a["specified_fraction"],
            "target_task": target_task,
            "target_task_sha256": sha256_bytes(target_task.encode("utf-8")),
            "tool_segments": tools,
            "external_context": ext,
            "external_context_sha256": sha256_bytes(ext.encode("utf-8")),
            "target_action": action,
            "target_action_text": astr,
            "target_action_sha256": sha256_bytes(astr.encode("utf-8")),
            "n_tool_segments": len(tools),
            "tool_derived_action_values": tool_derived_values,
            "historical_a15a_ca_flag_tau0": bool(old["ca_flag_tau0"]),
            "historical_a15a_ca_margin_tau0": old["ca_margin_tau0"],
            "historical_a15a_n_flagged_spans_tau0": old["n_flagged_spans_tau0"],
            "raw_trace_relpath": str(tp.relative_to(PROJECT_ROOT)),
            "raw_trace_sha256": sha256_file(tp),
        })

    # Exact clustering audit.
    by_label = {}
    for lab in ("SPECIFIED", "DELEGATED", "PARTIAL"):
        rr = [r for r in out if r["label"] == lab]
        by_label[lab] = {
            "n_decisions": len(rr),
            "n_unique_clusters": len({r["cluster_id"] for r in rr}),
            "cluster_sizes": dict(sorted(collections.Counter(r["cluster_id"] for r in rr).items())),
        }
    summary = {
        "n_decisions": len(out),
        "n_unique_clusters": len({r["cluster_id"] for r in out}),
        "by_label": by_label,
    }
    return out, summary

def controlled_manifest():
    require_file(A14_DIR / "protocol.json", EXPECTED_A14_PROTOCOL_FILE_SHA256)
    proto = read_json(A14_DIR / "protocol.json")
    if proto.get("protocol_hash") != EXPECTED_A14_PROTOCOL_HASH:
        raise RuntimeError("embedded A14 protocol hash drift")
    require_file(A14_DIR / "contexts" / "structured_contexts.jsonl", EXPECTED_A14_STRUCTURED_CONTEXTS_SHA256)
    require_file(A14_DIR / "base_instances.json", EXPECTED_A14_BASE_INSTANCES_SHA256)
    require_file(A14_DIR / "scorer_llama" / "condition_scores.jsonl", EXPECTED_A14_LLAMA_SCORES_SHA256)
    require_file(A14_DIR / "scorer_gemma" / "condition_scores.jsonl", EXPECTED_A14_GEMMA_SCORES_SHA256)

    rows = read_jsonl(A14_DIR / "contexts" / "structured_contexts.jsonl")
    if len(rows) != 96:
        raise RuntimeError(f"expected 96 A14 structured conditions, got {len(rows)}")
    gemma = {r["condition_id"]: r for r in read_jsonl(A14_DIR / "scorer_gemma" / "condition_scores.jsonl")}
    if len(gemma) != 96:
        raise RuntimeError("Gemma A14 condition set is not 96 unique IDs")

    bases_obj = read_json(A14_DIR / "base_instances.json")
    bases = bases_obj.get("instances") if isinstance(bases_obj, dict) else bases_obj
    base_by = {b["base_id"]: b for b in bases}
    if len(base_by) != 24:
        raise RuntimeError(f"expected 24 A14 bases, got {len(base_by)}")

    out = []
    for r in sorted(rows, key=lambda x: x["condition_id"]):
        cid = r["condition_id"]
        b = base_by[r["base_id"]]
        ctx = r["context"]
        msgs = ctx["messages"]
        users = [m for m in msgs if m.get("role") == "user"]
        if len(users) != 1:
            raise RuntimeError(f"{cid}: expected exactly one user message")
        tools = []
        for i, m in enumerate(msgs):
            if m.get("role") == "tool" and str(m.get("content") or "").strip():
                tools.append({
                    "message_index": i,
                    "component_id": m.get("component_id"),
                    "tool_name": m.get("tool_name"),
                    "content": str(m.get("content") or ""),
                    "content_sha256": sha256_bytes(str(m.get("content") or "").encode("utf-8")),
                })
        if len(tools) != int(r["eligible_span_count"]):
            raise RuntimeError(f"{cid}: external tool count drift")
        target_task = str(users[0].get("content") or "")
        ext = external_context_string(tools)
        action = r["target_action"]
        astr = action_string(action)

        exec_arg = b["family_spec"]["execution_arg"]
        exec_val = action["args"][exec_arg]
        exec_values = scalar_leaves(exec_val)

        aw_static = {
            "target_task": target_task,
            "external_context": ext,
            "target_action_text": astr,
        }
        out.append({
            "schema_version": "A15B0_CONTROLLED_INPUT_V1",
            "arm": "A15B0-A_CONTROLLED",
            "condition_id": cid,
            "base_id": r["base_id"],
            "cluster_id": r["base_id"],
            "family": r["family"],
            "factor_provenance": r["factor_provenance"],
            "factor_descendant": r["factor_descendant"],
            "target_task": target_task,
            "target_task_sha256": sha256_bytes(target_task.encode("utf-8")),
            "tool_segments": tools,
            "external_context": ext,
            "external_context_sha256": sha256_bytes(ext.encode("utf-8")),
            "target_action": action,
            "target_action_text": astr,
            "target_action_sha256": sha256_bytes(astr.encode("utf-8")),
            "execution_arg": exec_arg,
            "execution_value_strings": exec_values,
            "relevant_tool_text_unpadded": ctx.get("relevant_text_exact"),
            "agentwatcher_static_input_sha256": stable_hash(aw_static),
            "ca_gemma_flag_tau0": bool(gemma[cid]["CA_FLAG_0"]),
            "ca_gemma_margin": float(gemma[cid]["CA_MARGIN"]),
        })

    # Structural exposure audit: does assistant SHAM/ECHO alter AW static input?
    by_key = collections.defaultdict(list)
    for r in out:
        by_key[(r["base_id"], r["factor_provenance"])].append(r)
    pairs = []
    for key, rr in sorted(by_key.items()):
        if len(rr) != 2:
            raise RuntimeError(f"{key}: expected SHAM/ECHO pair, got {len(rr)}")
        d = {x["factor_descendant"]: x for x in rr}
        if set(d) != {"SHAM", "ECHO"}:
            raise RuntimeError(f"{key}: missing SHAM/ECHO")
        same = d["SHAM"]["agentwatcher_static_input_sha256"] == d["ECHO"]["agentwatcher_static_input_sha256"]
        pairs.append({
            "base_id": key[0],
            "factor_provenance": key[1],
            "sham_condition_id": d["SHAM"]["condition_id"],
            "echo_condition_id": d["ECHO"]["condition_id"],
            "static_input_identical": same,
            "static_input_sha256": d["SHAM"]["agentwatcher_static_input_sha256"] if same else None,
        })

    n_identical = sum(x["static_input_identical"] for x in pairs)
    # Dedup execution manifest only if every SHAM/ECHO pair is identical.
    if n_identical == 48:
        uniq = {}
        for r in out:
            k = r["agentwatcher_static_input_sha256"]
            uniq.setdefault(k, r)
        execution_rows = sorted(uniq.values(), key=lambda x: x["agentwatcher_static_input_sha256"])
        dedup_rule = "ALL_48_SHAM_ECHO_WITHIN_PROVENANCE_PAIRS_IDENTICAL; execute unique static inputs once"
    else:
        execution_rows = out
        dedup_rule = "NOT_ALL_SHAM_ECHO_PAIRS_IDENTICAL; execute all 96 conditions"

    summary = {
        "n_conditions": len(out),
        "n_bases": len({r["base_id"] for r in out}),
        "n_sham_echo_pairs": len(pairs),
        "n_static_identical_sham_echo_pairs": n_identical,
        "n_unique_agentwatcher_static_inputs": len({r["agentwatcher_static_input_sha256"] for r in out}),
        "execution_rows_n": len(execution_rows),
        "dedup_rule": dedup_rule,
        "pair_audit": pairs,
    }
    return out, execution_rows, summary

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not (OUT_DIR / "source_lock.json").is_file():
        sys.exit("FATAL: run A15B0_00_source_lock.py first")

    b1 = validate_b1()
    a13 = validate_a13()
    natural, natural_summary = natural_manifest(a13)
    controlled, controlled_exec, controlled_summary = controlled_manifest()

    write_jsonl(OUT_DIR / "controlled_96_inputs.jsonl", controlled)
    write_jsonl(OUT_DIR / "controlled_execution_inputs.jsonl", controlled_exec)
    write_jsonl(OUT_DIR / "natural_26_inputs.jsonl", natural)

    summary = {
        "schema_version": "A15B0_PREPARE_SUMMARY_V1",
        "created_at_utc": now_utc(),
        "b1": b1,
        "controlled": controlled_summary,
        "natural": natural_summary,
        "artifact_hashes": {
            "controlled_96_inputs.jsonl": sha256_file(OUT_DIR / "controlled_96_inputs.jsonl"),
            "controlled_execution_inputs.jsonl": sha256_file(OUT_DIR / "controlled_execution_inputs.jsonl"),
            "natural_26_inputs.jsonl": sha256_file(OUT_DIR / "natural_26_inputs.jsonl"),
        },
        "no_model_or_api_calls": True,
        "no_agentwatcher_outcomes_generated": True,
    }
    summary["prepare_hash"] = stable_hash({k:v for k,v in summary.items() if k != "created_at_utc"})
    write_json(OUT_DIR / "PREFREEZE_INPUT_SUMMARY.json", summary)

    print("[A15B0-01] PREPARE PASS")
    print(
        "[A15B0-01] controlled: "
        f"conditions={controlled_summary['n_conditions']} bases={controlled_summary['n_bases']} "
        f"SHAM/ECHO-identical-pairs={controlled_summary['n_static_identical_sham_echo_pairs']}/48 "
        f"unique-AW-static-inputs={controlled_summary['n_unique_agentwatcher_static_inputs']} "
        f"execution-rows={controlled_summary['execution_rows_n']}"
    )
    print(
        "[A15B0-01] natural: "
        f"decisions={natural_summary['n_decisions']} unique-task-clusters={natural_summary['n_unique_clusters']}"
    )
    for lab, x in natural_summary["by_label"].items():
        print(
            f"[A15B0-01] natural {lab}: decisions={x['n_decisions']} "
            f"unique-task-clusters={x['n_unique_clusters']}"
        )
    print(f"[A15B0-01] prepare_hash={summary['prepare_hash']}")
    print("[A15B0-01] NO model/API/AgentWatcher scientific outcomes generated")

if __name__ == "__main__":
    main()
