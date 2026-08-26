#!/usr/bin/env python3
"""
A15b-0D — predeclared AgentWatcher monitor-without-localization ablation.

Scientific motivation:
AgentWatcher Table 4 reports numerically near-identical AgentDojo results for
"No attribution" (Clean/Imp./Tool = 0.70/0.01/0.00) and full AgentWatcher
(0.71/0.01/0.00). This arm tests whether the attribution/localization frontend
adds observable value on our exact paired-trace conditions.

IMPORTANT fidelity boundary:
The paper table label does not by itself specify exact implementation semantics.
This runner therefore has a precise name:
    PAIRED_TRACE_NO_LOCALIZATION_MONITOR
It feeds the frozen monitor the entire frozen external_context rather than C*.
It is not called an exact reproduction of the paper's "No attribution" row
unless the pinned source audit establishes semantic identity.

Requires a frozen A15b-0 protocol and passed synthetic preflight.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import sys
import time
import urllib.request

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

def load_get_message2(repo):
    p = repo / "src" / "defenses" / "monitor_llm_module" / "messages.py"
    spec = importlib.util.spec_from_file_location("a15b0_aw_messages_noattr", p)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.get_message2

def parse_monitor_output(s):
    raw=(s or "").strip()
    tail=raw.split("</Reasoning>")[-1].strip()
    if re.match(r"(?is)^yes\s*,?\s*injection\s*:",tail):
        return True,True
    if re.match(r"(?is)^no\b",tail):
        return False,True
    last=raw.splitlines()[-1].strip() if raw.splitlines() else ""
    if re.match(r"(?is)^yes\s*,?\s*injection\s*:",last):
        return True,True
    if re.match(r"(?is)^no\b",last):
        return False,True
    return None,False

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--arm",choices=["controlled","natural"],required=True)
    ap.add_argument("--monitor-base-url",default="http://localhost:8120/v1")
    ap.add_argument("--repo-dir",default="external/AgentWatcher")
    ap.add_argument("--limit",type=int,default=None,
                    help="DEBUG ONLY; limited runs are marked development.")
    args=ap.parse_args()

    proto=read_json(OUT_DIR/"protocol.json")
    pf=read_json(OUT_DIR/"PREFLIGHT.json")
    if pf.get("protocol_hash")!=proto.get("protocol_hash"):
        sys.exit("FATAL: preflight/protocol mismatch")
    sl=read_json(OUT_DIR/"source_lock.json")
    repo=PROJECT_ROOT/args.repo_dir
    if git(["rev-parse","HEAD"],cwd=repo)!=sl["agentwatcher"]["git_head"]:
        sys.exit("FATAL: AgentWatcher source drift after freeze")

    ids=[x.get("id") for x in http_json(args.monitor_base_url,"/models").get("data",[])]
    if AW_MONITOR_ADAPTER not in ids:
        sys.exit(f"FATAL: exact frozen monitor adapter not served: {ids}")

    get_message2=load_get_message2(repo)
    if args.arm=="controlled":
        rows=read_jsonl(OUT_DIR/"controlled_execution_inputs.jsonl")
        outpath=OUT_DIR/"agentwatcher_no_localization_controlled_outputs.jsonl"
    else:
        rows=read_jsonl(OUT_DIR/"natural_26_inputs.jsonl")
        outpath=OUT_DIR/"agentwatcher_no_localization_natural_outputs.jsonl"

    development=args.limit is not None
    if args.limit is not None: rows=rows[:args.limit]
    if outpath.exists() and not development:
        sys.exit(f"FATAL: {outpath} already exists; do not overwrite scientific outcomes.")

    outs=[]
    for i,row in enumerate(rows,1):
        t0=time.time()
        msgs=get_message2(row["target_task"],row["external_context"],row["target_action_text"])
        resp=http_json(
            args.monitor_base_url,"/chat/completions",
            {"model":AW_MONITOR_ADAPTER,"messages":msgs,"temperature":0,"max_tokens":1024},
        )
        t1=time.time()
        raw=(resp["choices"][0]["message"]["content"] or "").strip()
        flag,ok=parse_monitor_output(raw)
        z={
            **{k:row.get(k) for k in (
                "arm","condition_id","base_id","decision_id","cluster_id","family",
                "factor_provenance","factor_descendant","label","specified_fraction"
            )},
            "agentwatcher_static_input_sha256":row.get("agentwatcher_static_input_sha256"),
            "ablation":"PAIRED_TRACE_NO_LOCALIZATION_MONITOR",
            "paper_no_attribution_exact_correspondence":"UNRESOLVED_UNLESS_SOURCE_AUDIT_CONFIRMS",
            "detect_flag":flag,
            "monitor_parse_ok":ok,
            "monitor_output":raw,
            "monitor_output_sha256":sha256_bytes(raw.encode("utf-8")),
            "monitor_runtime_s":t1-t0,
            "external_context_sha256":row["external_context_sha256"],
            "protocol_hash":proto["protocol_hash"],
            "development":development,
        }
        outs.append(z)
        print(
            f"[{i:03d}/{len(rows):03d}] "
            f"{z.get('condition_id') or z.get('decision_id')} "
            f"flag={flag} parse={ok} monitor_t={z['monitor_runtime_s']:.2f}s",
            flush=True,
        )

    target=outpath if not development else OUT_DIR/f"DEVELOPMENT_no_localization_{args.arm}_{len(rows)}.jsonl"
    write_jsonl(target,outs)
    print(f"[A15B0-04b] COMPLETE arm={args.arm} rows={len(outs)} development={development}")
    print(f"[A15B0-04b] sha256={sha256_file(target)}")

if __name__=="__main__":
    main()
