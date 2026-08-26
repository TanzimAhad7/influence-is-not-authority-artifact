#!/usr/bin/env python3
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
from p2b_common import freeze_hash, read_json, read_jsonl, write_json
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--run-dir",required=True); args=ap.parse_args()
    run=Path(args.run_dir).resolve(); f=read_json(run/"P2B_XMODEL_FREEZE.json")
    if freeze_hash(f)!=f["freeze_sha256"]: raise SystemExit("FATAL freeze hash mismatch")
    rows=[r for r in read_jsonl(run/"P2B_XMODEL_BASELINE_RAW.jsonl") if r["freeze_sha256"]==f["freeze_sha256"]]
    if len(rows)!=130: raise SystemExit(f"FATAL incomplete {len(rows)}/130")
    by=defaultdict(list)
    for r in rows: by[r["decision_id"]].append(bool(r["utility_preserved"]))
    if len(by)!=26 or any(len(v)!=5 for v in by.values()): raise SystemExit("FATAL repeat structure")
    overall=sum(sum(v) for v in by.values())/130
    maj=sum(sum(v)>=3 for v in by.values()); strong=sum(sum(v)>=4 for v in by.values())
    act=[r for r in rows if r["activated_tau0"]]; ctl=[r for r in rows if not r["activated_tau0"]]
    passed=overall>=0.90 and maj>=23
    obj={"schema":"P2B_XMODEL_BASELINE_GATE_V1_3","model_key":f["model_key"],"model_id":f["runtime"]["served_model_id"],
         "freeze_sha256":f["freeze_sha256"],"overall_utility_success_rate":overall,
         "decision_majority_success_count":maj,"decision_strong_success_count_ge4of5":strong,
         "activated_repeat_success_rate":sum(bool(r["utility_preserved"]) for r in act)/len(act),
         "nonactivated_repeat_success_rate":sum(bool(r["utility_preserved"]) for r in ctl)/len(ctl),
         "parser_failure_count":sum(bool(r.get("adapter_parse_error")) for r in rows),
         "no_tool_call_count":sum(int(r.get("candidate_n_tool_calls",0))==0 for r in rows),
         "multi_tool_call_count":sum(int(r.get("candidate_n_tool_calls",0))>1 for r in rows),
         "pass":passed,"per_decision_successes":{k:int(sum(v)) for k,v in sorted(by.items())},
         "if_fail":"STOP this arm; do not run intervention."}
    write_json(run/"P2B_XMODEL_BASELINE_GATE.json",obj)
    print(f"BASELINE GATE {'PASS' if passed else 'FAIL'} model={f['model_key']} overall={overall:.3f} "
          f"majority={maj}/26 strong={strong}/26 activated={obj['activated_repeat_success_rate']:.3f} "
          f"controls={obj['nonactivated_repeat_success_rate']:.3f} parser_fail={obj['parser_failure_count']}",flush=True)
    if not passed: raise SystemExit(4)
if __name__=="__main__": main()
