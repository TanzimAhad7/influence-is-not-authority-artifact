#!/usr/bin/env python3
from pathlib import Path
import argparse,json,sys,time,traceback
from p0b3_live_common import *

def verify_impl(pkg: Path,out: Path,freeze: Path):
    p=out/'P0B3_LIVE_IMPLEMENTATION_FREEZE.json'
    if not p.exists():
        raise HardStop('run live technical preflight first')
    d=json.loads(p.read_text())
    if d.get('status')!='FROZEN_AFTER_EXCLUDED_TECHNICAL_PREFLIGHT_BEFORE_BENCHMARK_OUTCOMES':
        raise HardStop('implementation-freeze status invalid')
    if d['bound_completed_freeze_sha256']!=sha256_file(freeze):
        raise HardStop('completed freeze archive changed after preflight')
    if package_hashes(pkg)!=d['live_package_hashes']:
        raise HardStop('live package drift after preflight')
    got=obj_hash({k:v for k,v in d.items() if k!='implementation_freeze_sha256'})
    if got!=d['implementation_freeze_sha256']:
        raise HardStop('implementation-freeze content/hash mismatch')
    return d

def make_pipeline(project: Path,out: Path,proto: dict,impl: dict):
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline,PipelineConfig
    client=openrouter_client(project,proto)
    call_log=out/'P0B3_PROVIDER_CALLS.jsonl'; event_log=out/'P0B3_DEFENSE_EVENTS.jsonl'
    base=StrictOpenRouterLLM(client,proto['config']['models']['agent']['model_id'],call_log)
    scorer=ProxyScorer(proto['config']['models']['proxy']['server_base_url'],proto['config']['models']['proxy']['served_model_name'],impl['proxy']['transport'])
    guard=CausalArmorLLM(base,scorer,client,proto,event_log,call_log)
    cfg=PipelineConfig(llm=guard,model_id=None,defense=None,system_message_name=None,system_message=None,tool_delimiter='tool',tool_output_format=None)
    pipeline=AgentPipeline.from_config(cfg)
    # Templating-only alias required by AgentDojo 0.1.35 ImportantInstructionsAttack.
    # Actual provider/model calls remain StrictOpenRouterLLM(model=google/gemini-2.5-flash).
    pipeline.name=ATTACK_PIPELINE_NAME_ALIAS
    return pipeline,guard

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',required=True); ap.add_argument('--package-dir',required=True); ap.add_argument('--freeze-complete',required=True); ap.add_argument('--out-dir',required=True)
    a=ap.parse_args(); project=Path(a.project_root).resolve(); pkg=Path(a.package_dir).resolve(); freeze=Path(a.freeze_complete).resolve(); out=Path(a.out_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    proto=verify_freeze(pkg,freeze); pop=verify_population(pkg,proto); impl=verify_impl(pkg,out,freeze)
    binding=impl.get('important_instructions_model_name_binding') or {}
    if binding.get('agentdojo_pipeline_name_alias')!=ATTACK_PIPELINE_NAME_ALIAS or binding.get('rendered_model_prose')!=ATTACK_MODEL_PROSE_EXPECTED:
        raise HardStop('ImportantInstructions model-name binding drift')
    rows_path=out/'P0B3_SCIENCE_ROWS.jsonl'; err_path=out/'P0B3_ERRORS.jsonl'
    done={r['episode_id'] for r in read_jsonl(rows_path) if r.get('status')=='OK'}
    from agentdojo.task_suite.load_suites import get_suite
    from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
    pipeline,guard=make_pipeline(project,out,proto,impl)
    suites={s:get_suite('v1.2.2',s) for s in proto['config']['agentdojo']['suites']}
    attacks={s:ImportantInstructionsAttack(suites[s],pipeline) for s in suites}
    benign=pop['benign']; primary=pop['primary']; total=len(benign)+len(primary)
    print(f'[P0b-3] frozen science population={total}; already_done={len(done)}; remaining={total-len(done)}',flush=True)

    def run_one(kind,r):
        suite=suites[r['suite']]; uid=r['user_task_id']; iid=r.get('injection_task_id')
        eid=f"{kind}:{r['suite']}:{uid}"+(f":{iid}" if iid else '')
        if eid in done:
            return False
        ut=suite.get_user_task_by_id(uid); guard.begin_episode(eid,ut.PROMPT); t0=time.perf_counter()
        try:
            if kind=='benign':
                utility,security=suite.run_task_with_pipeline(pipeline,ut,None,{})
            else:
                it=suite.get_injection_task_by_id(iid); injections=attacks[r['suite']].attack(ut,it)
                utility,security=suite.run_task_with_pipeline(pipeline,ut,it,injections)
            stats=guard.end_episode()
            row={'schema':'P0B3_SCIENCE_ROW_V1','status':'OK','episode_id':eid,'kind':kind,'suite':r['suite'],'user_task_id':uid,'injection_task_id':iid,'utility':bool(utility),'attack_success':bool(security) if kind=='attack' else None,'security_raw_agentdojo':bool(security),'elapsed_s':time.perf_counter()-t0,'defense_stats':stats}
            append_jsonl(rows_path,row); done.add(eid); return True
        except Exception as e:
            append_jsonl(err_path,{'episode_id':eid,'kind':kind,'suite':r['suite'],'user_task_id':uid,'injection_task_id':iid,'error':f'{type(e).__name__}: {e}','traceback':traceback.format_exc(),'elapsed_s':time.perf_counter()-t0})
            print(f'FATAL scientific episode error at {eid}: {type(e).__name__}: {e}',flush=True)
            print('No PASS/FAIL was imputed. Correct only the transport/runtime issue and rerun this identical frozen command to resume.',flush=True)
            sys.exit(3)

    seq=[('benign',r) for r in benign]+[('attack',r) for r in primary]
    for kind,r in seq:
        if run_one(kind,r):
            n=len(done); print(f"[P0b-3] COMPLETE {n}/{total} ({100*n/total:.1f}%)",flush=True)
    print(f'P0b-3 SCIENCE EXECUTION COMPLETE: {len(done)}/{total}',flush=True)

if __name__=='__main__':
    main()
