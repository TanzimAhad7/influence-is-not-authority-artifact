#!/usr/bin/env python3
"""Zero-call reconciliation + reseal after the final pre-science patch."""
from __future__ import annotations
import ast,datetime,hashlib,importlib.metadata,json,os,subprocess,sys
from pathlib import Path

EXPECTED_EXTTOOLS_SHA='18aada875ef67f3eb4a221901dfe80a63a343d9054ae2e956c73a112537f4deb'
SUITES={'banking','slack','travel','workspace'}

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def canon(o):
 if hasattr(o,'model_dump'): o=o.model_dump(mode='json')
 return json.loads(json.dumps(o,sort_keys=True,ensure_ascii=False,default=str))
def chash(o): return hashlib.sha256(json.dumps(canon(o),sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def jdump(p,o):Path(p).write_text(json.dumps(o,indent=2,sort_keys=True,ensure_ascii=False)+'\n',encoding='utf-8')

def ext_tools(attri:Path):
 text=attri.read_text(encoding='utf-8'); start=text.index('EXTERNAL_OUTPUT_TOOLS: set[str] = {'); end=text.index('\n}',start)+2; sub=text[start:end]
 h=hashlib.sha256(sub.encode()).hexdigest()
 if h!=EXPECTED_EXTTOOLS_SHA: raise SystemExit(f'FATAL EXTERNAL_OUTPUT_TOOLS declaration drift {h}')
 node=ast.parse(sub).body[0]
 vals=sorted(x.value for x in node.value.elts if isinstance(x,ast.Constant) and isinstance(x.value,str))
 return sub,h,vals

def main():
 if len(sys.argv)!=2: raise SystemExit('usage: E2E_PRE_08_reseal.py PROJECT_ROOT')
 root=Path(sys.argv[1]).resolve(); pre=root/'E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build'; pkg=root/'E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1'; pipe=root/'external/attriguard_zenodo_v1/usenix-artifacts/main/pipeline'
 if importlib.metadata.version('agentdojo')!='0.1.35': raise SystemExit('FATAL AgentDojo version drift')
 if (root/'E2E_ATTR_AUTH_v1/scientific_v1').exists() and any((root/'E2E_ATTR_AUTH_v1/scientific_v1').iterdir()): raise SystemExit('FATAL scientific directory nonempty before patched reseal')
 for name in ['DEV_LIVE_PREFLIGHT.json','DEV_AUDITPATH_PREFLIGHT.json','YAML_DIRECTIVE_ROUNDTRIP_AUDIT.json']:
  p=pre/name
  if not p.exists() or json.loads(p.read_text()).get('status')!='PASS': raise SystemExit(f'FATAL {name} not PASS')
 # Exact AttriGuard external-output declaration + machine-readable set.
 sub,h,tools=ext_tools(pipe/'AttriGuard.py')
 jdump(pre/'ATTRIGUARD_EXTERNAL_OUTPUT_TOOLS.json',{'schema':'E2E_ATTRIGUARD_EXTERNAL_OUTPUT_TOOLS_V1','declaration_sha256':h,'tools':tools})
 # Retained AgentDojo-v1 suite source tree hashes.
 src=root/'E2E_ATTR_AUTH_v1/input_lock/A13_C0_INPUT_BUNDLE_v1/agentdojo_source/default_suites/v1'
 lines=[]
 for suite in sorted(SUITES):
  sd=src/suite
  if not sd.is_dir(): raise SystemExit(f'FATAL retained suite source missing {suite}')
  for p in sorted(sd.rglob('*')):
   if p.is_file(): lines.append((sha(p),str(p.relative_to(root))))
 with (pre/'AGENTDOJO_V1_RETAINED_SOURCE_SHA256.tsv').open('w',encoding='utf-8') as f:
  for hh,rel in lines:f.write(f'{hh}\t{rel}\n')
 # Context-specific pre-environment locks, computed with the exact frozen intervention.
 sys.path.insert(0,str(pkg/'code')); os.environ['E2E_CONTEXT_RENDERED']=str(pre/'CONTEXT_RENDERED.jsonl')
 from agentdojo.task_suite.load_suites import get_suite
 from agentdojo.base_tasks import BaseUserTask
 import e2e_attacks
 specs={p.stem:json.loads(p.read_text()) for p in (pre/'PAEF_ORACLE_FREEZE/PAEF_SPECS').glob('CASE_*.json')}
 contexts={(r['case_id'],r['context']):r for r in map(json.loads,(pre/'CONTEXT_RENDERED.jsonl').read_text().splitlines())}
 locks=[]
 for cid,s in sorted(specs.items()):
  suite=get_suite('v1',s['suite']); ut=suite.get_user_task_by_id(s['task_key'].split('/',1)[1])
  if ut.__class__.init_environment is not BaseUserTask.init_environment: raise SystemExit(f'FATAL retained init_environment override {cid}')
  for ctx in ['CLEAN','ALIGNED','CONFLICT']:
   if ctx=='CLEAN': injections={}
   else:
    cls=e2e_attacks.E2EAlignedAttack if ctx=='ALIGNED' else e2e_attacks.E2EConflictAttack
    inj=contexts[(cid,ctx)]['injection_task']; injections=cls(suite,None).attack(ut,suite.get_injection_task_by_id(inj))
   env=ut.init_environment(suite.load_and_inject_default_environment(injections))
   locks.append({'case_id':cid,'context':ctx,'sha256':chash(env),'injection_keys':sorted(injections)})
 jdump(pre/'PRE_ENVIRONMENT_LOCKS.json',{'schema':'E2E_PRE_ENVIRONMENT_LOCKS_V1','locks':locks})
 # Map each frozen injection placeholder to the actual ground-truth tool result that carries it,
 # then require that carrier tool to be source-listed by AttriGuard.
 import csv
 from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
 from agentdojo.functions_runtime import FunctionsRuntime
 from agentdojo.types import get_text_content_as_str
 from agentdojo.attacks.base_attacks import BaseAttack
 class Probe(BaseAttack):
  name='__carrier_probe__'
  def attack(self,user_task,injection_task): return {}
 with (pre/'INJECTION_LOCATION_LEDGER.csv').open(newline='',encoding='utf-8') as f: locs=list(csv.DictReader(f))
 carrier_rows=[]; bad=[]
 for r in locs:
  suite=get_suite('v1',r['suite']); ut=suite.get_user_task_by_id(r['user_task']); probe=Probe(suite,None)
  env=suite.load_and_inject_default_environment(probe.canary_injections); runtime=FunctionsRuntime(suite.tools)
  _,_,_,responses,_=GroundTruthPipeline(ut).query(ut.PROMPT,runtime,env)
  needle=probe.canary_injections[r['selected_injection_vector']]; hits=[]
  for msg in responses:
   if msg.get('role')!='tool' or msg.get('content') is None: continue
   if needle in get_text_content_as_str(msg['content']):
    tc=msg.get('tool_call'); fn=tc.function if hasattr(tc,'function') else (tc or {}).get('function'); hits.append(fn)
  hits=sorted(set(x for x in hits if x))
  ok=len(hits)==1 and hits[0] in set(tools)
  carrier_rows.append({'case_id':r['case_id'],'task_key':r['task_key'],'selected_injection_vector':r['selected_injection_vector'],
                       'carrier_tools_json':json.dumps(hits),'unique_carrier_tool':hits[0] if len(hits)==1 else '',
                       'attriguard_external_output_eligible':str(ok).lower()})
  if not ok: bad.append((r['case_id'],r['selected_injection_vector'],hits))
 if bad: raise SystemExit(f'FATAL carrier tool audit failed: {bad}')
 with (pre/'INJECTION_CARRIER_TOOL_AUDIT.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=carrier_rows[0].keys());w.writeheader();w.writerows(carrier_rows)
 # Patched analysis must self-test now, before science.
 r=subprocess.run([sys.executable,str(pkg/'code/E2E_PRE_02_analysis.py'),'--selftest'],capture_output=True,text=True)
 if r.returncode: raise SystemExit('FATAL patched analysis selftest '+r.stderr)
 (pre/'ANALYSIS_SELFTEST_PATCH1.json').write_text(r.stdout,encoding='utf-8')
 # Update freeze metadata without changing population/factors/endpoint/estimand/schedule.
 fp=pre/'FREEZE.json'; freeze=json.loads(fp.read_text())
 freeze.update({'status':'PREOUTCOME_PATCH2_RESEALED_GO','prescience_patch':'P2_YAML_TRANSPORT_PLUS_P1_INTEGRITY',
                'runner_schema':'E2E_RUN_ROW_V2','analysis_schema':'E2E_ANALYSIS_V2','context_non_delivery_is_itt_scientific':True,
                'dev_auditpath_preflight_required':True,'context_specific_pre_environment_locks':True,
                'external_output_tools_declaration_sha256':EXPECTED_EXTTOOLS_SHA})
 jdump(fp,freeze)
 jdump(pre/'PRESCIENCE_PATCH_RECONCILIATION.json',{
   'schema':'E2E_PRESCIENCE_PATCH_RECONCILIATION_V2','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
   'scientific_outcomes_seen':False,'population_changed':False,'factors_changed':False,'endpoint_changed':False,'estimand_changed':False,'schedule_changed':False,
   'fixes':['YAML transport escaping preserves exact frozen raw directive after AgentDojo v0.1.35 str.format + yaml.safe_load, proven on all 28 non-clean contexts','context non-delivery retained as ITT scientific outcome; never retried','retries restricted to explicit transient provider/server failures',
            'actual AttriGuard audit-path dev preflight required','one scheduled user-task execution per row; no injection-task utility pre-run',
            'context-specific pre-environment hashes frozen and checked','full pre/post environment snapshots preserved per run',
            'exact directive hash and runtime metadata added to scientific row','retained AgentDojo-v1 source tree and EXTERNAL_OUTPUT_TOOLS declaration locked',
            'analysis restricted to complete task six-cell blocks with integrity diagnostics','ON/OFF PAEF+Z repeat variance and route/inspection diagnostics separated']})
 # Final manifest excludes unstable bytecode caches and the ledger/seal themselves.
 ledger=pre/'PREFREEZE_SHA256.tsv'
 with ledger.open('w',encoding='utf-8') as f:
  for base in [pre,pkg/'code']:
   for p in sorted(base.rglob('*')):
    if not p.is_file(): continue
    if '__pycache__' in p.parts or p.suffix=='.pyc': continue
    if p.name in {'PREFREEZE_SHA256.tsv','PREFREEZE_COMPLETE.md'}: continue
    f.write(f'{sha(p)}\t{p.relative_to(root)}\n')
 text=f'''# E2E-ATTR-AUTH PREFREEZE COMPLETE — PATCH 2 RESEALED\n\n**GO: PASS**  \n**Timestamp UTC:** {datetime.datetime.now(datetime.timezone.utc).isoformat()}  \n**B:** {freeze['B']} natural tasks  \n**Planned scheduled executions:** {freeze['N_exec']}  \n**Scientific outcome rows present at reseal:** 0  \n**AgentDojo:** 0.1.35 / benchmark v1  \n**Defense:** official source-locked AttriGuard, fuzzy, level 2  \n**Victim / shadow / judge:** openai/gpt-4.1-mini through frozen OpenRouter path  \n**Patch status:** YAML-safe intervention transport, ITT non-delivery, audit-path preflight, runtime/source/environment integrity, and complete-block analysis reconciled before science.  \n\nThe population, factors, PAEF endpoint, primary estimand, randomization seed, and 420-row schedule are unchanged.\nAfter the first sealed scientific run, the no-v2 science stop law applies regardless of outcome.\n'''
 (pre/'PREFREEZE_COMPLETE.md').write_text(text,encoding='utf-8')
 print(text)
 print(json.dumps({'status':'PATCH2_RESEAL_PASS','GO':'PASS','B':freeze['B'],'N_exec':freeze['N_exec'],'scientific_outcomes':0,'external_tools_hash':h,'source_files_locked':len(lines),'pre_environment_locks':len(locks),'carrier_tool_audit_rows':len(carrier_rows)},indent=2))
if __name__=='__main__':main()
