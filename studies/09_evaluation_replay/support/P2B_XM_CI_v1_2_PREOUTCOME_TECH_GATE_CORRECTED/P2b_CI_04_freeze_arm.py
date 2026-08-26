#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.metadata, inspect, json, os, platform, sys
from datetime import datetime, timezone
from pathlib import Path
import requests

from action_local import verify_original_target_action_local
from ci_integrity import load_and_verify_global_freeze, sha256_file
from p2b_common import BENCHMARK_VERSION, EXPECTED_AGENTDOJO_VERSION, freeze_hash, read_json, read_jsonl, verify_original_target_oracle, write_json

HERE=Path(__file__).resolve().parent
EXPECTED_VLLM='0.26.0'

def server_version(base_url):
    root=base_url.rstrip('/'); root=root[:-3] if root.endswith('/v1') else root
    r=requests.get(root+'/version',timeout=20); r.raise_for_status(); d=r.json(); return str(d.get('version') if isinstance(d,dict) else d)

def model_ids(base_url,key):
    r=requests.get(base_url.rstrip('/')+'/models',headers={'Authorization':f'Bearer {key}'},timeout=20); r.raise_for_status(); return [x['id'] for x in r.json().get('data',[])]

def source_sha(obj):
    p=Path(inspect.getfile(obj)).resolve(); return {'path':str(p),'sha256':sha256_file(p)}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--model-key',required=True,choices=['llama','gemma','qwen_canonical'])
    ap.add_argument('--project-root',required=True)
    ap.add_argument('--base-url',default='http://localhost:8100/v1')
    ap.add_argument('--api-key',default=os.getenv('P2B_API_KEY','EMPTY'))
    ap.add_argument('--run-dir',required=True)
    ap.add_argument('--global-freeze',default=str(HERE/'P2B_XM_CI_GLOBAL_FREEZE.json'))
    a=ap.parse_args()
    gf=load_and_verify_global_freeze(Path(a.global_freeze)); reg=gf['model_registry']; cfg=reg['models'][a.model_key]; lock=gf['revision_lock']['models'][a.model_key]
    out=Path(a.run_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    rawout=out/'P2B_CI_BASELINE_RAW.jsonl'
    if rawout.exists() and rawout.stat().st_size>0: raise SystemExit('FATAL scientific baseline rows already exist before arm freeze')
    av=importlib.metadata.version('agentdojo')
    if av!=EXPECTED_AGENTDOJO_VERSION: raise SystemExit(f'FATAL AgentDojo expected {EXPECTED_AGENTDOJO_VERSION}, got {av}')
    current_stack={'openai':importlib.metadata.version('openai'),'jsonschema':importlib.metadata.version('jsonschema'),'requests':importlib.metadata.version('requests'),'python':sys.version}
    if current_stack!=gf.get('client_stack'):
        raise SystemExit(f'FATAL client-stack drift since technical preflight/global freeze expected={gf.get("client_stack")} got={current_stack}')
    vv=server_version(a.base_url)
    if vv!=EXPECTED_VLLM: raise SystemExit(f'FATAL vLLM expected {EXPECTED_VLLM}, got {vv}')
    ids=model_ids(a.base_url,a.api_key)
    if ids!=[cfg['model_id']]: raise SystemExit(f'FATAL served model expected {[cfg["model_id"]]}, got {ids}')
    render=read_json(out/'P2B_CI_RENDER_PREFLIGHT.json')
    if not render.get('pass') or render.get('passed')!=26 or render.get('global_freeze_sha256')!=gf['freeze_sha256'] or render.get('model_key')!=a.model_key:
        raise SystemExit('FATAL missing/mismatched post-freeze render preflight PASS')
    pid_file=out/'vllm_server.pid'
    if not pid_file.exists(): raise SystemExit(f'FATAL missing server pid file {pid_file}')
    pid=int(pid_file.read_text().strip()); proc=Path(f'/proc/{pid}/cmdline')
    if not proc.exists(): raise SystemExit(f'FATAL server PID {pid} not alive')
    argv=[x.decode('utf-8',errors='replace') for x in proc.read_bytes().split(b'\x00') if x]
    cmd=' '.join(argv)
    required=[cfg['model_id'],'--tensor-parallel-size 2','--dtype bfloat16','--max-model-len 16384','--max-logprobs 5','--seed 0','--tokenizer-mode hf','--generation-config vllm',f"--revision {lock['revision']}",f"--tokenizer-revision {lock['tokenizer_revision']}",'--port 8100']
    missing=[x for x in required if x not in cmd]
    if missing: raise SystemExit(f'FATAL live server mismatch missing={missing} cmd={cmd!r}')
    inv=read_jsonl(HERE/'inputs/P2B_REPLAY_INVENTORY.jsonl')
    if len(inv)!=26 or sum(bool(x['activated_tau0']) for x in inv)!=18: raise SystemExit('FATAL population drift')
    project=Path(a.project_root).resolve()
    downstream=verify_original_target_oracle(project,inv)
    bad=[x for x in downstream if not x['utility_preserved']]
    if bad: write_json(out/'P2B_CI_DOWNSTREAM_ORACLE_SELFTEST_FAILURE.json',{'checks':downstream}); raise SystemExit(f'FATAL downstream oracle selftest failed {len(bad)}/26')
    local=verify_original_target_action_local(project,inv)
    bad2=[x for x in local if not x['action_local_preserved']]
    if bad2: write_json(out/'P2B_CI_ACTION_LOCAL_ORACLE_SELFTEST_FAILURE.json',{'checks':local}); raise SystemExit(f'FATAL action-local oracle selftest failed {len(bad2)}/26')
    import agentdojo
    from agentdojo.task_suite import task_suite as task_suite_module
    from agentdojo.agent_pipeline.llms import openai_llm
    from agentdojo.functions_runtime import FunctionsRuntime
    from agentdojo.task_suite.load_suites import get_suite
    srcs={'agentdojo_init':source_sha(agentdojo),'task_suite_module':source_sha(task_suite_module),'openai_llm':source_sha(openai_llm),'functions_runtime':source_sha(FunctionsRuntime),'load_suites':source_sha(get_suite)}
    freeze={
      'schema':'P2B_XM_CI_ARM_FREEZE_V1','created_utc':datetime.now(timezone.utc).isoformat(),'global_freeze_sha256':gf['freeze_sha256'],'model_key':a.model_key,'model':cfg,'model_revision':lock['revision'],'tokenizer_revision':lock['tokenizer_revision'],
      'render_preflight_sha256':sha256_file(out/'P2B_CI_RENDER_PREFLIGHT.json'),'live_server_pid':pid,'live_server_cmdline':argv,
      'scientific_model_calls_before_arm_freeze':0,'technical_preflight_model_calls':gf['technical_preflights'][a.model_key]['model_calls'],
      'population':{'decisions':26,'activated':18,'controls':8,'repeats':5,'selection':'exact unchanged v1.3 P2b population'},
      'runtime':{'agentdojo_version':av,'vllm_version':vv,'client_stack':current_stack,'benchmark_version':BENCHMARK_VERSION,'base_url':a.base_url,'served_model_id':ids[0],'temperature':0.0,'top_p':1.0,'request_seed':0,'max_tokens':1024,'tokenizer_mode':'hf','generation_config':'vllm','python':sys.version,'platform':platform.platform()},
      'gates':reg['gates'],'h_slot':reg['h_slot'],'source_files':srcs,
      'oracle_selftest':{'downstream_checks':26,'downstream_passed':26,'action_local_checks':26,'action_local_passed':26},
      'stop_rule':'Scientific FAIL does not stop later corrected arms. Any FORMAT_INSTRUMENT_VIOLATION invalidates this arm for behavioral inference. No intervention is included or authorized by this freeze.'
    }
    freeze['freeze_sha256']=freeze_hash(freeze)
    write_json(out/'P2B_CI_ARM_FREEZE.json',freeze)
    write_json(out/'P2B_CI_DOWNSTREAM_ORACLE_SELFTEST.json',{'checks':downstream})
    write_json(out/'P2B_CI_ACTION_LOCAL_ORACLE_SELFTEST.json',{'checks':local})
    print('ARM FREEZE PASS',flush=True); print('model_key='+a.model_key,flush=True); print('freeze_sha256='+freeze['freeze_sha256'],flush=True)

if __name__=='__main__': main()
