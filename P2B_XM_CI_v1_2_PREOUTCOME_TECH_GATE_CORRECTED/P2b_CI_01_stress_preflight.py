#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, importlib.metadata, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import Draft202012Validator
import openai, requests

from common_action_interface import canonicalize_history, explicit_envelope_match, parse_action_envelope, response_format_payload
from stress_runtime import SyntheticRuntime

HERE=Path(__file__).resolve().parent

def served_model(base_url,key):
    r=requests.get(base_url.rstrip('/')+'/models',headers={'Authorization':f'Bearer {key}'},timeout=20); r.raise_for_status()
    ids=[x['id'] for x in r.json().get('data',[])]
    if len(ids)!=1: raise SystemExit(f'FATAL expected exactly one served model, got {ids}')
    return ids[0]

def server_version(base_url):
    root=base_url.rstrip('/'); root=root[:-3] if root.endswith('/v1') else root
    r=requests.get(root+'/version',timeout=20); r.raise_for_status(); d=r.json(); return str(d.get('version') if isinstance(d,dict) else d)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def live_server_cmdline(server_run_dir: Path, cfg: dict, lock: dict) -> tuple[int,list[str]]:
    pid_file=server_run_dir/'vllm_server.pid'
    if not pid_file.exists(): raise SystemExit(f'FATAL missing technical server pid file {pid_file}')
    pid=int(pid_file.read_text().strip()); proc=Path(f'/proc/{pid}/cmdline')
    if not proc.exists(): raise SystemExit(f'FATAL technical server PID {pid} not alive')
    argv=[x.decode('utf-8',errors='replace') for x in proc.read_bytes().split(b'\x00') if x]
    cmd=' '.join(argv)
    required=[cfg['model_id'],'--tensor-parallel-size 2','--dtype bfloat16','--max-model-len 16384','--max-logprobs 5','--seed 0','--tokenizer-mode hf','--generation-config vllm',f"--revision {lock['revision']}",f"--tokenizer-revision {lock['tokenizer_revision']}",'--port 8100']
    missing=[x for x in required if x not in cmd]
    if missing: raise SystemExit(f'FATAL technical live server mismatch missing={missing} cmd={cmd!r}')
    return pid,argv

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model-key',required=True,choices=['llama','gemma','qwen_canonical'])
    ap.add_argument('--base-url',default='http://localhost:8100/v1')
    ap.add_argument('--api-key',default=os.getenv('P2B_API_KEY','EMPTY'))
    ap.add_argument('--server-run-dir',required=True,help='Directory used by serve_model.sh; required to freeze exact technical server provenance.')
    ap.add_argument('--out-dir',required=True)
    a=ap.parse_args()
    reg=json.loads((HERE/'MODEL_REGISTRY_CI.json').read_text()); cfg=reg['models'][a.model_key]
    locks=json.loads((HERE/'P2B_XM_CI_REVISION_LOCK.json').read_text()); lock=locks['models'][a.model_key]
    vv=server_version(a.base_url)
    if vv!=reg['common_runtime']['vllm_version']: raise SystemExit(f"FATAL vLLM version expected={reg['common_runtime']['vllm_version']} got={vv}")
    model=served_model(a.base_url,a.api_key)
    if model!=cfg['model_id']: raise SystemExit(f'FATAL served model expected={cfg["model_id"]} got={model}')
    pid,argv=live_server_cmdline(Path(a.server_run_dir).resolve(),cfg,lock)
    stress=json.loads((HERE/'inputs/EXCLUDED_STRESS_CONTEXTS.json').read_text())
    client=openai.OpenAI(base_url=a.base_url,api_key=a.api_key)
    results=[]
    for case in stress['cases']:
        runtime=SyntheticRuntime(case['tools'])
        messages=canonicalize_history(case['history'],runtime)
        try:
            c=client.chat.completions.create(model=model,messages=messages,temperature=0.0,top_p=1.0,seed=0,max_tokens=1024,response_format=response_format_payload())
            text=c.choices[0].message.content or ''
            obj,status,err=parse_action_envelope(text)
            exact=(obj is not None and explicit_envelope_match(obj,case['expected']))
            expected=case['expected']
            expected_type=expected['action_type']
            branch_match=(obj is not None and obj.get('action_type')==expected_type)
            expected_calls=list(expected.get('calls') or [])
            got_calls=list((obj or {}).get('calls') or [])
            expected_call_count_match=(len(got_calls)==len(expected_calls))
            expected_tool_names=[c.get('name') for c in expected_calls]
            got_tool_names=[c.get('name') for c in got_calls]
            expected_tool_names_match=(got_tool_names==expected_tool_names)
            synthetic_tool_schema_valid=True
            synthetic_tool_schema_errors=[]
            tool_map={x['name']:x for x in case['tools']}
            for i,c in enumerate(got_calls):
                spec=tool_map.get(c.get('name'))
                if spec is None:
                    synthetic_tool_schema_valid=False
                    synthetic_tool_schema_errors.append(f'call[{i}] unknown_tool:{c.get("name")!r}')
                    continue
                errs=[e.message for e in Draft202012Validator(spec['input_schema']).iter_errors(c.get('arguments') or {})]
                if errs:
                    synthetic_tool_schema_valid=False
                    synthetic_tool_schema_errors.extend([f'call[{i}] {e}' for e in errs])
            technical_pass=(
                status in {'PARSED_TOOL','PARSED_TEXT_NO_ACTION'} and err is None and branch_match
                and expected_call_count_match and expected_tool_names_match and synthetic_tool_schema_valid
            )
            item={
                'case_id':case['case_id'],'features':case['features'],'raw_text':text,
                'raw_text_sha256':hashlib.sha256(text.encode()).hexdigest(),
                'interface_status':status,'interface_error':err,'parsed_envelope':obj,'expected':expected,
                'branch_match':branch_match,'expected_call_count_match':expected_call_count_match,
                'expected_tool_names_match':expected_tool_names_match,
                'synthetic_tool_schema_valid':synthetic_tool_schema_valid,
                'synthetic_tool_schema_errors':synthetic_tool_schema_errors,
                'exact_expected_match':exact,
                'semantic_exact_replay_diagnostic':exact,
                'technical_pass':technical_pass,
                'pass':technical_pass,
            }
        except Exception as e:
            item={'case_id':case['case_id'],'features':case['features'],'exception':f'{type(e).__name__}: {e}','pass':False}
        results.append(item)
        print(f"STRESS {a.model_key} {case['case_id']} pass={item['pass']}",flush=True)
    passed=len(results)==len(stress['cases']) and all(x['pass'] for x in results)
    outdir=Path(a.out_dir); outdir.mkdir(parents=True,exist_ok=True)
    tested_source_hashes={
        'P2b_CI_01_stress_preflight.py':sha(HERE/'P2b_CI_01_stress_preflight.py'),
        'common_action_interface.py':sha(HERE/'common_action_interface.py'),
        'stress_runtime.py':sha(HERE/'stress_runtime.py'),
        'ACTION_ENVELOPE_SCHEMA.json':sha(HERE/'ACTION_ENVELOPE_SCHEMA.json'),
        'MODEL_REGISTRY_CI.json':sha(HERE/'MODEL_REGISTRY_CI.json'),
        'P2B_XM_CI_REVISION_LOCK.json':sha(HERE/'P2B_XM_CI_REVISION_LOCK.json'),
        'inputs/EXCLUDED_STRESS_CONTEXTS.json':sha(HERE/'inputs/EXCLUDED_STRESS_CONTEXTS.json'),
    }
    client_stack={
        'openai':importlib.metadata.version('openai'),
        'jsonschema':importlib.metadata.version('jsonschema'),
        'requests':importlib.metadata.version('requests'),
        'python':sys.version,
    }
    out={'schema':'P2B_XM_CI_STRESS_PREFLIGHT_V1_2','scientific':False,'created_utc':datetime.now(timezone.utc).isoformat(),'model_key':a.model_key,'model_id':model,'model_revision':lock['revision'],'tokenizer_revision':lock['tokenizer_revision'],'vllm_version':vv,'client_stack':client_stack,'live_server_pid':pid,'live_server_cmdline':argv,'live_server_cmdline_sha256':hashlib.sha256('\0'.join(argv).encode()).hexdigest(),'tested_source_hashes':tested_source_hashes,'model_calls':len(results),'pass':passed,'results':results}
    (outdir/'P2B_CI_STRESS_PREFLIGHT.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(f"STRESS PREFLIGHT {'PASS' if passed else 'FAIL'} {sum(x['pass'] for x in results)}/{len(results)}",flush=True)
    if not passed: raise SystemExit(3)

if __name__=='__main__': main()
