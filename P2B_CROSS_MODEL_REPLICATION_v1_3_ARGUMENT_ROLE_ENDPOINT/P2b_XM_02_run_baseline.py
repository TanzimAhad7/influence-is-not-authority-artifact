#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import openai
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite
from p2b_common import append_jsonl, evaluate_candidate_frozen_continuation, freeze_hash, read_json, read_jsonl
from canonical_json_adapter import canonicalize_history, parse_candidate_text

def done_keys(path,sha):
    out=set()
    if not path.exists(): return out
    for r in read_jsonl(path):
        if r.get("freeze_sha256")==sha: out.add((r["decision_id"],int(r["repeat_index"])))
    return out

def model_next(client, model, original_prefix, suite_name):
    suite=get_suite("v1",suite_name); runtime=FunctionsRuntime(suite.tools)
    messages=canonicalize_history(original_prefix,runtime)
    c=client.chat.completions.create(model=model,messages=messages,temperature=0.0,top_p=1.0,seed=0,max_tokens=1024)
    text=c.choices[0].message.content or ""
    calls,parse_error=parse_candidate_text(text)
    cand={"role":"assistant","content":[{"type":"text","content":text}] if text else None,"tool_calls":calls}
    return cand,text,parse_error

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--project-root",required=True)
    ap.add_argument("--run-dir",required=True)
    ap.add_argument("--api-key",default=os.getenv("P2B_API_KEY","EMPTY"))
    args=ap.parse_args()
    here=Path(__file__).resolve().parent; run=Path(args.run_dir).resolve()
    freeze=read_json(run/"P2B_XMODEL_FREEZE.json")
    if freeze_hash(freeze)!=freeze["freeze_sha256"]: raise SystemExit("FATAL freeze hash mismatch")
    invs={r["decision_id"]:r for r in read_jsonl(here/"inputs/P2B_REPLAY_INVENTORY.jsonl")}
    out=run/"P2B_XMODEL_BASELINE_RAW.jsonl"; done=done_keys(out,freeze["freeze_sha256"])
    client=openai.OpenAI(base_url=freeze["runtime"]["base_url"],api_key=args.api_key)
    for did in sorted(invs):
        inv=invs[did]
        raw=read_json(Path(args.project_root)/inv["raw_log_path"])
        prefix=list(raw.get("messages") or [])[:int(inv["target_message_index"])]
        for rep in range(5):
            if (did,rep) in done: continue
            try:
                cand,raw_text,parse_error=model_next(client,freeze["runtime"]["served_model_id"],prefix,inv["suite"])
            except Exception as e:
                print(f"INFRA ABORT {did} rep={rep}: {type(e).__name__}: {e}",file=sys.stderr,flush=True)
                raise SystemExit(3)
            ev=evaluate_candidate_frozen_continuation(Path(args.project_root),inv,cand)
            row={"schema":"P2B_XMODEL_BASELINE_RAW_V1_3","freeze_sha256":freeze["freeze_sha256"],
                 "model_key":freeze["model_key"],"model_id":freeze["runtime"]["served_model_id"],
                 "phase":"BASELINE","decision_id":did,"suite":inv["suite"],"user_task":inv["user_task"],
                 "label":inv["label"],"activated_tau0":bool(inv["activated_tau0"]),"repeat_index":rep,
                 "adapter_raw_text":raw_text,"adapter_parse_error":parse_error,"candidate":cand,**ev}
            append_jsonl(out,row)
            print(f"BASELINE {freeze['model_key']} {did} rep={rep} utility={ev['utility_preserved']} "
                  f"calls={ev['candidate_n_tool_calls']} parse_error={bool(parse_error)}",flush=True)
    print(f"BASELINE COMPLETE: {out}",flush=True)
if __name__=="__main__": main()
