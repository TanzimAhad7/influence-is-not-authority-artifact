#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path
import requests
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suite

from ci_integrity import load_and_verify_global_freeze
from common_action_interface import canonicalize_history
from p2b_common import read_json, read_jsonl, sha256_file, write_json

HERE=Path(__file__).resolve().parent

def stable_sha(obj):
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def served_model(base_url,key):
    r=requests.get(base_url.rstrip('/')+'/models',headers={'Authorization':f'Bearer {key}'},timeout=20); r.raise_for_status()
    ids=[x['id'] for x in r.json().get('data',[])]
    if len(ids)!=1: raise SystemExit(f'FATAL expected one served model, got {ids}')
    return ids[0]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model-key',required=True,choices=['llama','gemma','qwen_canonical'])
    ap.add_argument('--project-root',required=True)
    ap.add_argument('--base-url',default='http://localhost:8100/v1')
    ap.add_argument('--api-key',default=os.getenv('P2B_API_KEY','EMPTY'))
    ap.add_argument('--out-dir',required=True)
    ap.add_argument('--global-freeze',default=str(HERE/'P2B_XM_CI_GLOBAL_FREEZE.json'))
    a=ap.parse_args()
    gf=load_and_verify_global_freeze(Path(a.global_freeze)); reg=gf['model_registry']; cfg=reg['models'][a.model_key]
    model=served_model(a.base_url,a.api_key)
    if model!=cfg['model_id']: raise SystemExit(f'FATAL served model mismatch expected={cfg["model_id"]} got={model}')
    inv=read_jsonl(HERE/'inputs/P2B_REPLAY_INVENTORY.jsonl')
    if len(inv)!=26: raise SystemExit(f'FATAL population drift {len(inv)}')
    root=Path(a.project_root).resolve(); url=a.base_url.rstrip('/')+'/chat/completions/render'
    headers={'Authorization':f'Bearer {a.api_key}','Content-Type':'application/json'}
    results=[]
    for row in sorted(inv,key=lambda x:x['decision_id']):
        raw_path=root/row['raw_log_path']
        if not raw_path.exists(): raise SystemExit(f'FATAL missing raw log {raw_path}')
        got=sha256_file(raw_path)
        if got!=row['raw_log_sha256']: raise SystemExit(f'FATAL raw log hash drift {row["decision_id"]}')
        raw=read_json(raw_path); prefix=list(raw.get('messages') or [])[:int(row['target_message_index'])]
        runtime=FunctionsRuntime(get_suite('v1',row['suite']).tools)
        messages=canonicalize_history(prefix,runtime)
        payload={'model':model,'messages':messages,'temperature':0.0,'top_p':1.0,'seed':0,'max_tokens':1024,'stream':False}
        resp=requests.post(url,headers=headers,json=payload,timeout=120); body=resp.content
        item={'decision_id':row['decision_id'],'raw_log_sha256':got,'canonical_request_sha256':stable_sha(payload),'canonical_roles':[m['role'] for m in messages],'http_status':resp.status_code,'render_response_sha256':hashlib.sha256(body).hexdigest(),'render_response_bytes':len(body),'pass':resp.status_code==200}
        if resp.status_code!=200: item['error_body']=body.decode('utf-8',errors='replace')[:4000]
        results.append(item); print(f"RENDER {a.model_key} {row['decision_id']} status={resp.status_code} pass={item['pass']}",flush=True)
    passed=len(results)==26 and all(x['pass'] for x in results)
    out=Path(a.out_dir); out.mkdir(parents=True,exist_ok=True)
    obj={'schema':'P2B_XM_CI_POSTFREEZE_RENDER_PREFLIGHT_V1','created_utc':datetime.now(timezone.utc).isoformat(),'scientific_model_generations':0,'purpose':'Post-global-freeze ABORT-only chat-template compatibility check on the 26 frozen prefixes. It may not be used to tune this freeze.','global_freeze_sha256':gf['freeze_sha256'],'model_key':a.model_key,'model_id':model,'decisions':26,'passed':sum(x['pass'] for x in results),'pass':passed,'results':results}
    write_json(out/'P2B_CI_RENDER_PREFLIGHT.json',obj)
    print(f"RENDER PREFLIGHT {'PASS' if passed else 'FAIL'} {sum(x['pass'] for x in results)}/26",flush=True)
    if not passed: raise SystemExit(6)

if __name__=='__main__': main()
