#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.metadata, json, os, sys
from pathlib import Path
import openai
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from action_local import evaluate_action_local
from ci_integrity import load_and_verify_global_freeze
from common_action_interface import canonicalize_history, envelope_to_candidate_message, parse_action_envelope, response_format_payload
from p2b_common import append_jsonl, evaluate_candidate_frozen_continuation, freeze_hash, read_json, read_jsonl, sha256_file

HERE=Path(__file__).resolve().parent

def done_keys(path,sha):
    out=set()
    if not path.exists(): return out
    for r in read_jsonl(path):
        if r.get('arm_freeze_sha256')==sha: out.add((r['decision_id'],int(r['repeat_index'])))
    return out

def model_next(client,model,original_prefix,suite_name):
    runtime=FunctionsRuntime(get_suite('v1',suite_name).tools)
    messages=canonicalize_history(original_prefix,runtime)
    c=client.chat.completions.create(model=model,messages=messages,temperature=0.0,top_p=1.0,seed=0,max_tokens=1024,response_format=response_format_payload())
    text=c.choices[0].message.content or ''
    env,status,err=parse_action_envelope(text)
    cand=envelope_to_candidate_message(env,status,text)
    return cand,text,env,status,err

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',required=True); ap.add_argument('--run-dir',required=True); ap.add_argument('--api-key',default=os.getenv('P2B_API_KEY','EMPTY')); ap.add_argument('--global-freeze',default=str(HERE/'P2B_XM_CI_GLOBAL_FREEZE.json')); a=ap.parse_args()
    gf=load_and_verify_global_freeze(Path(a.global_freeze)); run=Path(a.run_dir).resolve(); freeze=read_json(run/'P2B_CI_ARM_FREEZE.json')
    if freeze_hash(freeze)!=freeze['freeze_sha256']: raise SystemExit('FATAL arm freeze hash mismatch')
    if freeze['global_freeze_sha256']!=gf['freeze_sha256']: raise SystemExit('FATAL arm/global freeze mismatch')
    current_stack={'openai':importlib.metadata.version('openai'),'jsonschema':importlib.metadata.version('jsonschema'),'requests':importlib.metadata.version('requests'),'python':sys.version}
    if current_stack!=freeze['runtime'].get('client_stack'):
        raise SystemExit(f'FATAL client-stack drift after arm freeze expected={freeze["runtime"].get("client_stack")} got={current_stack}')
    invs={r['decision_id']:r for r in read_jsonl(HERE/'inputs/P2B_REPLAY_INVENTORY.jsonl')}
    if len(invs)!=26: raise SystemExit('FATAL population drift')
    out=run/'P2B_CI_BASELINE_RAW.jsonl'; done=done_keys(out,freeze['freeze_sha256'])
    client=openai.OpenAI(base_url=freeze['runtime']['base_url'],api_key=a.api_key); root=Path(a.project_root).resolve()
    repeats=int(freeze['population']['repeats'])
    for did in sorted(invs):
        inv=invs[did]
        raw_path=root/inv['raw_log_path']
        if not raw_path.exists(): raise SystemExit(f'FATAL missing frozen raw log before generation: {raw_path}')
        got_raw_sha=sha256_file(raw_path)
        if got_raw_sha!=inv['raw_log_sha256']:
            raise SystemExit(f'FATAL raw-log hash drift BEFORE scientific generation {did}: expected={inv["raw_log_sha256"]} got={got_raw_sha}')
        raw=read_json(raw_path); prefix=list(raw.get('messages') or [])[:int(inv['target_message_index'])]
        for rep in range(repeats):
            if (did,rep) in done: continue
            try:
                cand,raw_text,envelope,iface_status,iface_error=model_next(client,freeze['runtime']['served_model_id'],prefix,inv['suite'])
            except Exception as e:
                print(f'INFRA ABORT {did} rep={rep}: {type(e).__name__}: {e}',file=sys.stderr,flush=True); raise SystemExit(3)
            local=evaluate_action_local(root,inv,cand,iface_status)
            downstream=evaluate_candidate_frozen_continuation(root,inv,cand)
            # The two evaluators independently reconstruct the same pre-target state. Cross-check overlapping action facts.
            if int(local['candidate_n_tool_calls'])!=int(downstream['candidate_n_tool_calls']): raise SystemExit(f'FATAL evaluator call-count mismatch {did} rep={rep}')
            if bool(local['exact_target_action_reproduction'])!=bool(downstream['exact_target_action_reproduction']): raise SystemExit(f'FATAL evaluator exact-target mismatch {did} rep={rep}')
            row={
              'schema':'P2B_XM_CI_BASELINE_RAW_V1','global_freeze_sha256':gf['freeze_sha256'],'arm_freeze_sha256':freeze['freeze_sha256'],'model_key':freeze['model_key'],'model_id':freeze['runtime']['served_model_id'],'phase':'CORRECTED_BASELINE',
              'decision_id':did,'suite':inv['suite'],'user_task':inv['user_task'],'label':inv['label'],'activated_tau0':bool(inv['activated_tau0']),'repeat_index':rep,
              'interface_raw_text':raw_text,'action_envelope':envelope,'interface_status':iface_status,'interface_error':iface_error,
              **local,
              'utility_preserved':bool(downstream['utility_preserved']),'utility_error':downstream['utility_error'],'candidate_calls':downstream['candidate_calls'],'candidate_execution':downstream['candidate_execution'],'continuation_execution':downstream['continuation_execution']
            }
            append_jsonl(out,row)
            print(f"BASELINE {freeze['model_key']} {did} rep={rep} iface={iface_status} action_local={row['action_local_preserved']} downstream={row['utility_preserved']} exact={row['exact_target_action_reproduction']}",flush=True)
    print(f'BASELINE COMPLETE: {out}',flush=True)

if __name__=='__main__': main()
