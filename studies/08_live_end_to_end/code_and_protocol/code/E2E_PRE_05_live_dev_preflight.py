#!/usr/bin/env python3
"""One permanently excluded/dev AgentDojo run per defense state.
This is a technical preflight, not a scientific cohort outcome.
"""
from __future__ import annotations
import argparse,datetime,importlib.metadata,json,os,sys,traceback
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=os.getcwd());args=ap.parse_args();root=Path(args.project_root).resolve();pre=root/'E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build'
 if importlib.metadata.version('agentdojo')!='0.1.35':raise SystemExit('FATAL AgentDojo version')
 key=os.getenv('OPENROUTER_API_KEY');
 if not key:raise SystemExit('FATAL OPENROUTER_API_KEY missing')
 pipe=root/'external/attriguard_zenodo_v1/usenix-artifacts/main/pipeline';sys.path.insert(0,str(pipe));sys.path.insert(0,str(root/'E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1/code'))
 import openai
 from openai_llm_compat import OpenAILLM
 from my_agent_pipeline import AgentPipeline,PipelineConfig
 from agentdojo.task_suite.load_suites import get_suite
 from agentdojo.benchmark import benchmark_suite_without_injections
 from agentdojo.logging import OutputLogger
 freeze=json.loads((pre/'FREEZE.json').read_text()); os.environ['OPENAI_API_KEY']=key;os.environ['OPENAI_BASE_URL']=freeze['environment']['openai_base_url'];os.environ['ATTRIGUARD_API_KEY']=key
 os.environ['ATTRIGUARD_BACKEND']='openai';os.environ['ATTRIGUARD_MODEL_ID']=freeze['environment']['victim_model'];os.environ['ATTRIGUARD_JUDGE_MODEL_ID']=freeze['environment']['victim_model'];os.environ['ATTRIGUARD_LEVEL']='2';os.environ['ATTRIGUARD_SURVIVAL']='fuzzy';os.environ['ATTRIGUARD_SKIP_EMPTY_AUDIT']='1';os.environ['ATTRIGUARD_DEBUG']='1'
 client=openai.OpenAI(api_key=key,base_url=freeze['environment']['openai_base_url']);suite=get_suite('v1','workspace'); model=freeze['environment']['victim_model']
 # Permanently excluded from E2E scientific cohort: workspace/user_task_0.
 out=pre/'DEV_LIVE_PREFLIGHT';out.mkdir(exist_ok=True);results=[]
 for defense in ['OFF','ON']:
  d=out/defense;d.mkdir(exist_ok=True)
  try:
   llm=OpenAILLM(client,model,temperature=0.0);pipeobj=AgentPipeline.from_config(PipelineConfig(llm=llm,model_id=None,defense='attriguard' if defense=='ON' else None,system_message_name=None,system_message=None,attack=None,suite_name='workspace'))
   with OutputLogger(str(d)): benchmark_suite_without_injections(pipeobj,suite,user_tasks=('user_task_0',),logdir=d,force_rerun=True,benchmark_version='v1')
   raws=[]
   for p in d.rglob('*.json'):
    try:x=json.loads(p.read_text())
    except:continue
    if x.get('suite_name')=='workspace' and x.get('user_task_id')=='user_task_0' and x.get('attack_type') is None:raws.append((p,x))
   if len(raws)!=1:raise RuntimeError(f'expected one dev raw row, found {len(raws)}')
   raw=raws[0][1]
   if raw.get('error') is not None:raise RuntimeError(str(raw['error']))
   defense_states=sum(1 for m in raw.get('messages',[]) if m.get('role')=='tool' and m.get('defense_state') is not None)
   if defense=='ON' and defense_states==0: raise RuntimeError('ON dev run produced no defense_state annotation')
   results.append({'defense':defense,'status':'PASS','utility':raw.get('utility'),'defense_state_tool_messages':defense_states})
  except Exception as e:
   traceback.print_exc();results.append({'defense':defense,'status':'FAIL','error':f'{type(e).__name__}: {e}'})
 rep={'schema':'E2E_DEV_LIVE_PREFLIGHT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scientific_cohort_used':False,'dev_task':'workspace/user_task_0','rows':results,'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL'}
 (pre/'DEV_LIVE_PREFLIGHT.json').write_text(json.dumps(rep,indent=2,sort_keys=True)+'\n');print(json.dumps(rep,indent=2))
 if rep['status']!='PASS':raise SystemExit(5)
if __name__=='__main__':main()
