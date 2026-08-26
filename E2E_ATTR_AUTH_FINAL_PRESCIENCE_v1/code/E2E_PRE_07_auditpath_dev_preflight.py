#!/usr/bin/env python3
"""Dev-only live preflight that must exercise AttriGuard's actual audit path.
Uses permanently excluded workspace/user_task_8 (no same-function ALT in A1).
No scientific cohort task or outcome is touched.
"""
from __future__ import annotations
import argparse,datetime,importlib.metadata,json,os,sys,traceback
from pathlib import Path

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default=os.getcwd()); args=ap.parse_args(); root=Path(args.project_root).resolve()
 pre=root/'E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build'
 if importlib.metadata.version('agentdojo')!='0.1.35': raise SystemExit('FATAL AgentDojo version')
 key=os.getenv('OPENROUTER_API_KEY')
 if not key: raise SystemExit('FATAL OPENROUTER_API_KEY missing')
 pipe=root/'external/attriguard_zenodo_v1/usenix-artifacts/main/pipeline'; sys.path.insert(0,str(pipe))
 import openai
 from openai_llm_compat import OpenAILLM
 from my_agent_pipeline import AgentPipeline,PipelineConfig
 from agentdojo.task_suite.load_suites import get_suite
 from agentdojo.benchmark import run_task_without_injection_tasks
 from agentdojo.logging import OutputLogger
 freeze=json.loads((pre/'FREEZE.json').read_text())
 os.environ['OPENAI_API_KEY']=key; os.environ['OPENAI_BASE_URL']=freeze['environment']['openai_base_url']; os.environ['ATTRIGUARD_API_KEY']=key
 os.environ['ATTRIGUARD_BACKEND']='openai'; os.environ['ATTRIGUARD_MODEL_ID']=freeze['environment']['victim_model']; os.environ['ATTRIGUARD_JUDGE_MODEL_ID']=freeze['environment']['victim_model']
 os.environ['ATTRIGUARD_LEVEL']='2'; os.environ['ATTRIGUARD_SURVIVAL']='fuzzy'; os.environ['ATTRIGUARD_SKIP_EMPTY_AUDIT']='1'; os.environ['ATTRIGUARD_DEBUG']='1'
 client=openai.OpenAI(api_key=key,base_url=freeze['environment']['openai_base_url']); suite=get_suite('v1','workspace'); model=freeze['environment']['victim_model']
 out=pre/'DEV_AUDITPATH_PREFLIGHT'; out.mkdir(exist_ok=True)
 result={'schema':'E2E_DEV_AUDITPATH_PREFLIGHT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'scientific_cohort_used':False,'dev_task':'workspace/user_task_8','status':'FAIL'}
 try:
  llm=OpenAILLM(client,model,temperature=0.0)
  pobj=AgentPipeline.from_config(PipelineConfig(llm=llm,model_id=None,defense='attriguard',system_message_name=None,system_message=None,attack=None,suite_name='workspace'))
  with OutputLogger(str(out)):
   run_task_without_injection_tasks(suite,pobj,suite.get_user_task_by_id('user_task_8'),out,True,'v1')
  raws=[]
  for p in out.rglob('*.json'):
   try:x=json.loads(p.read_text())
   except:continue
   if x.get('suite_name')=='workspace' and x.get('user_task_id')=='user_task_8' and x.get('attack_type') is None: raws.append((p,x))
  if len(raws)!=1: raise RuntimeError(f'expected one dev raw row, found {len(raws)}')
  raw=raws[0][1]
  if raw.get('error') is not None: raise RuntimeError(str(raw['error']))
  tools=[m for m in raw.get('messages',[]) if m.get('role')=='tool']
  ext=[m for m in tools if (m.get('tool_call') or {}).get('function')=='search_calendar_events' and str(m.get('content','')).strip()]
  audited=[]
  for m in tools:
   tc=m.get('tool_call') or {}; ds=m.get('defense_state') or {}
   if tc.get('function')=='add_calendar_event_participants' and ds and str(ds.get('judge_reason',''))!='audit_skipped': audited.append(m)
  if not ext: raise RuntimeError('did not observe non-empty source-listed external calendar observation')
  if not audited: raise RuntimeError('AttriGuard actual audit path was not exercised on the state-changing dev call')
  m=audited[0]; ds=m.get('defense_state') or {}
  result.update({'status':'PASS','utility':bool(raw.get('utility')),'external_observation_count':len(ext),'audited_state_changing_calls':len(audited),
                 'audited_function':'add_calendar_event_participants','audit_flag':bool(ds.get('flag')),'judge_reason':str(ds.get('judge_reason','')),
                 'defense_input_present':m.get('defense_input') is not None,'raw_result':str(raws[0][0].relative_to(root))})
 except Exception as e:
  traceback.print_exc(); result['error']=f'{type(e).__name__}: {e}'
 (pre/'DEV_AUDITPATH_PREFLIGHT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 print(json.dumps(result,indent=2))
 if result['status']!='PASS': raise SystemExit(6)
if __name__=='__main__': main()
