#!/usr/bin/env python3
"""Zero-call proof that YAML transport escaping preserves every frozen directive."""
from __future__ import annotations
import datetime,json,os,sys
from pathlib import Path

def jdump(p,o): Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')

def content_str(msg):
 c=msg.get('content')
 if c is None:return ''
 if isinstance(c,str):return c
 if isinstance(c,list):return ''.join(str(x.get('content','')) if isinstance(x,dict) else str(x) for x in c)
 return str(c)

def main():
 if len(sys.argv)!=2: raise SystemExit('usage: E2E_PRE_10_yaml_roundtrip_audit.py PROJECT_ROOT')
 root=Path(sys.argv[1]).resolve(); pre=root/'E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build'; pkg=root/'E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1'
 if (root/'E2E_ATTR_AUTH_v1/scientific_v1').exists() and any((root/'E2E_ATTR_AUTH_v1/scientific_v1').iterdir()):
  raise SystemExit('FATAL scientific directory nonempty')
 sys.path.insert(0,str(pkg/'code')); os.environ['E2E_CONTEXT_RENDERED']=str(pre/'CONTEXT_RENDERED.jsonl')
 from agentdojo.task_suite.load_suites import get_suite
 from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
 from agentdojo.functions_runtime import FunctionsRuntime
 import e2e_attacks
 rows=[json.loads(x) for x in (pre/'CONTEXT_RENDERED.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
 target=[r for r in rows if r['context'] in {'ALIGNED','CONFLICT'}]
 audit=[]; failures=[]
 for r in target:
  suite=get_suite('v1',r['suite']); ut=suite.get_user_task_by_id(r['user_task']); inj=suite.get_injection_task_by_id(r['injection_task'])
  cls=e2e_attacks.E2EAlignedAttack if r['context']=='ALIGNED' else e2e_attacks.E2EConflictAttack
  injections=cls(suite,None).attack(ut,inj)
  # Hard parse proof: this was the PATCH1 failure site.
  env=suite.load_and_inject_default_environment(injections)
  runtime=FunctionsRuntime(suite.tools)
  _,_,_,responses,_=GroundTruthPipeline(ut).query(ut.PROMPT,runtime,env)
  raw=r['directive']; hits=[]
  for msg in responses:
   if msg.get('role')!='tool': continue
   txt=content_str(msg)
   if raw in txt:
    tc=msg.get('tool_call'); fn=tc.function if hasattr(tc,'function') else (tc or {}).get('function'); hits.append(fn)
  ok=len(hits)>=1
  item={'case_id':r['case_id'],'context':r['context'],'suite':r['suite'],'user_task':r['user_task'],
        'carrier':r['selected_injection_vector'],'yaml_parse_pass':True,'exact_raw_directive_observed':ok,
        'matching_tool_functions':sorted(set(x for x in hits if x))}
  audit.append(item)
  if not ok: failures.append(item)
 out={'schema':'E2E_YAML_DIRECTIVE_ROUNDTRIP_AUDIT_V1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'NO_SCIENTIFIC_MODEL_CALLS':True,'n_expected':len(target),'n_pass':len(target)-len(failures),'n_fail':len(failures),
      'status':'PASS' if not failures and len(target)==28 else 'FAIL','rows':audit}
 jdump(pre/'YAML_DIRECTIVE_ROUNDTRIP_AUDIT.json',out)
 print(json.dumps({k:out[k] for k in ['status','n_expected','n_pass','n_fail','NO_SCIENTIFIC_MODEL_CALLS']},indent=2))
 if out['status']!='PASS': raise SystemExit('FATAL YAML directive roundtrip audit failed')
if __name__=='__main__':main()
