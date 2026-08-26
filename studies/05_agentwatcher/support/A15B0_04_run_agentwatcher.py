#!/usr/bin/env python3
"""
Run the frozen full AgentWatcher paired-trace architecture boundary.

Requires A15b-0 protocol + outcome-free preflight.
Uses:
- exact official AgentWatcher attribute() from the pinned checkout;
- exact official get_message2 tool-agent prompt from pinned messages.py;
- exact frozen trained monitor endpoint.

Scientific outputs are written only after all freeze checks pass.
"""
from __future__ import annotations
import argparse
import importlib
import importlib.util
import json
import re
import sys
import time
import types
import urllib.request
from pathlib import Path

from a15b0_common import *

def http_json(base, path, payload=None):
    url = base.rstrip("/") + path
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type":"application/json","Authorization":"Bearer x"},
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))

def load_aw(repo):
    aw = load_official_agentwatcher_module(repo)
    mp = repo / "src" / "defenses" / "monitor_llm_module" / "messages.py"
    spec = importlib.util.spec_from_file_location("a15b0_aw_messages", mp)
    mm = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mm)
    return aw, mm.get_message2

def parse_monitor_output(s):
    raw = (s or "").strip()
    tail = raw.split("</Reasoning>")[-1].strip()
    if re.match(r"(?is)^yes\s*,?\s*injection\s*:", tail):
        return {"detect_flag": True, "parse_ok": True}
    if re.match(r"(?is)^no\b", tail):
        return {"detect_flag": False, "parse_ok": True}
    # Some checkpoints may omit exact closing tag; use only a strict final-line fallback.
    last = raw.splitlines()[-1].strip() if raw.splitlines() else ""
    if re.match(r"(?is)^yes\s*,?\s*injection\s*:", last):
        return {"detect_flag": True, "parse_ok": True}
    if re.match(r"(?is)^no\b", last):
        return {"detect_flag": False, "parse_ok": True}
    return {"detect_flag": None, "parse_ok": False}

def selected_context_metadata(aw_mod, full_context, intervals, tool_segments, relevant_values):
    # Map official AgentWatcher token intervals back to characters using the same loaded tokenizer.
    tok = aw_mod.tokenizer
    char_intervals = []
    tool_overlap = []
    try:
        enc = tok(full_context, add_special_tokens=True, return_offsets_mapping=True)
        offs = enc["offset_mapping"]
        # official attribute() drops the first token from context_ids
        offs = offs[1:]
        for a,b in intervals:
            use = [x for x in offs[a:b] if x and x != (0,0)]
            if use:
                char_intervals.append((min(x[0] for x in use), max(x[1] for x in use)))
            else:
                char_intervals.append((None,None))
    except Exception:
        char_intervals = [(None,None) for _ in intervals]

    # Exact char ranges under the frozen "\n\n" join.
    tool_ranges = []
    pos = 0
    for i,s in enumerate(tool_segments):
        if i:
            pos += 2
        start = pos
        pos += len(s["content"])
        tool_ranges.append((start,pos))

    for tr in tool_ranges:
        hit = any(
            a is not None and max(a,tr[0]) < min(b,tr[1])
            for a,b in char_intervals
        )
        tool_overlap.append(hit)

    return {
        "selected_char_intervals": char_intervals,
        "tool_segment_selected_overlap": tool_overlap,
        "any_tool_segment_selected": any(tool_overlap),
    }

def run_one(aw_mod, get_message2, row, monitor_base_url, attribution_model_path):
    t0 = time.time()
    windows, _, intervals, _ = aw_mod.attribute(
        "You are a helpful assistant.",
        row["target_task"],
        row["external_context"],
        row["target_action_text"],
        w_s=AW_W_S, w_l=AW_W_L, w_r=AW_W_R, K=AW_K,
        attribution_model=attribution_model_path,
    )
    t1 = time.time()
    selected = "\n\n".join(windows)
    msgs = get_message2(row["target_task"], selected, row["target_action_text"])
    resp = http_json(
        monitor_base_url, "/chat/completions",
        {
            "model": AW_MONITOR_ADAPTER,
            "messages": msgs,
            "temperature": 0,
            "max_tokens": 1024,
        },
    )
    t2 = time.time()
    raw = (resp["choices"][0]["message"]["content"] or "").strip()
    parsed = parse_monitor_output(raw)

    relevant_values = row.get("execution_value_strings") or row.get("tool_derived_action_values") or []
    val_recall = {}
    sel_norm = normalize_for_match(selected)
    for v in relevant_values:
        val_recall[str(v)] = normalize_for_match(v) in sel_norm

    meta = selected_context_metadata(
        aw_mod, row["external_context"], intervals, row["tool_segments"], relevant_values
    )
    return {
        **{k: row.get(k) for k in (
            "arm","condition_id","base_id","decision_id","cluster_id","family",
            "factor_provenance","factor_descendant","label","specified_fraction"
        )},
        "agentwatcher_static_input_sha256": row.get("agentwatcher_static_input_sha256"),
        "detect_flag": parsed["detect_flag"],
        "monitor_parse_ok": parsed["parse_ok"],
        "selected_windows_text": list(windows),
        "selected_windows_token_intervals": [list(x) for x in intervals],
        **meta,
        "relevant_value_recall": val_recall,
        "all_relevant_values_recalled": all(val_recall.values()) if val_recall else None,
        "monitor_output": raw,
        "monitor_output_sha256": sha256_bytes(raw.encode("utf-8")),
        "attribution_runtime_s": t1-t0,
        "monitor_runtime_s": t2-t1,
        "total_detector_runtime_s": t2-t0,
        "protocol_hash": read_json(OUT_DIR/"protocol.json")["protocol_hash"],
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["controlled","natural"], required=True)
    ap.add_argument("--monitor-base-url", default="http://localhost:8120/v1")
    ap.add_argument("--repo-dir", default="external/AgentWatcher")
    ap.add_argument("--limit", type=int, default=None,
                    help="DEBUG ONLY after freeze. Any limited scientific run is marked development and never enters primary analysis.")
    args = ap.parse_args()

    proto = read_json(OUT_DIR / "protocol.json")
    pf = read_json(OUT_DIR / "PREFLIGHT.json")
    if pf.get("protocol_hash") != proto.get("protocol_hash"):
        sys.exit("FATAL: preflight/protocol mismatch")

    sl = read_json(OUT_DIR / "source_lock.json")
    repo = PROJECT_ROOT / args.repo_dir
    if git(["rev-parse","HEAD"], cwd=repo) != sl["agentwatcher"]["git_head"]:
        sys.exit("FATAL: AgentWatcher source drift after freeze")

    ids = [x.get("id") for x in http_json(args.monitor_base_url, "/models").get("data", [])]
    if AW_MONITOR_ADAPTER not in ids:
        sys.exit(f"FATAL: exact frozen monitor adapter not served: {ids}")

    aw_mod, get_message2 = load_aw(repo)
    attribution_model_path = frozen_attribution_model_path()

    if args.arm == "controlled":
        rows = read_jsonl(OUT_DIR / "controlled_execution_inputs.jsonl")
        outpath = OUT_DIR / "agentwatcher_controlled_outputs.jsonl"
    else:
        rows = read_jsonl(OUT_DIR / "natural_26_inputs.jsonl")
        outpath = OUT_DIR / "agentwatcher_natural_outputs.jsonl"

    development = args.limit is not None
    if args.limit is not None:
        rows = rows[:args.limit]
    if outpath.exists() and not development:
        sys.exit(f"FATAL: {outpath} already exists. Do not overwrite scientific outcomes.")

    outs = []
    for i,row in enumerate(rows,1):
        z = run_one(aw_mod, get_message2, row, args.monitor_base_url, attribution_model_path)
        z["development"] = development
        outs.append(z)
        print(
            f"[{i:03d}/{len(rows):03d}] "
            f"{z.get('condition_id') or z.get('decision_id')} "
            f"flag={z['detect_flag']} parse={z['monitor_parse_ok']} "
            f"t={z['total_detector_runtime_s']:.2f}s",
            flush=True,
        )

    target = outpath if not development else OUT_DIR / f"DEVELOPMENT_{args.arm}_{len(rows)}.jsonl"
    write_jsonl(target, outs)
    print(f"[A15B0-04] COMPLETE arm={args.arm} rows={len(outs)} development={development}")
    print(f"[A15B0-04] sha256={sha256_file(target)}")

if __name__ == "__main__":
    main()
