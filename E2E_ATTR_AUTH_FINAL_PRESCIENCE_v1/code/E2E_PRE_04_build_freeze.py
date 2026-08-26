#!/usr/bin/env python3
from __future__ import annotations
import csv,datetime,hashlib,json,os,subprocess,sys
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def jdump(p,o):Path(p).write_text(json.dumps(o,indent=2,sort_keys=True)+'\n')
def main():
 root=Path(sys.argv[1]).resolve(); pre=root/'E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build'; pkg=root/'E2E_ATTR_AUTH_FINAL_PRESCIENCE_v1'
 # Required zero-call gates.
 gate=json.loads((pre/'PAEF_ORACLE_FREEZE/PAEF_ORACLE_GATE_SUMMARY.json').read_text())
 diff=json.loads((pre/'CONTEXT_PAIR_DIFF_REPORT.json').read_text()); rand=json.loads((pre/'RANDOMIZATION_METADATA.json').read_text()); env=json.loads((pre/'ENVIRONMENT_LOCK.json').read_text())
 if gate.get('B_after_oracle',0)<12 or gate.get('mutation_failures')!=0 or diff.get('status')!='PASS' or rand.get('N_exec')!=gate['B_after_oracle']*30: raise SystemExit('FATAL zero-call gate')
 # Frozen analysis selftest.
 r=subprocess.run([sys.executable,str(pkg/'code/E2E_PRE_02_analysis.py'),'--selftest'],capture_output=True,text=True)
 if r.returncode: raise SystemExit('FATAL analysis selftest '+r.stderr)
 (pre/'ANALYSIS_SELFTEST.json').write_text(r.stdout)
 # Syntax/import-static checks; do not contact provider.
 for p in sorted((pkg/'code').glob('*.py')):
  rr=subprocess.run([sys.executable,'-m','py_compile',str(p)],capture_output=True,text=True)
  if rr.returncode: raise SystemExit(f'FATAL compile {p}: {rr.stderr}')
 # Freeze exact package code hashes and pre-science outputs.
 freeze={'schema':'E2E_ATTR_AUTH_FREEZE_V1','status':'PREOUTCOME_ZERO_CALL_BUILD_COMPLETE_DEV_LIVE_PREFLIGHT_REQUIRED',
   'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'B':gate['B_after_oracle'],'N_exec':rand['N_exec'],
   'primary':'Delta_dir=(PAEF_ALIGNED_ON-PAEF_CONFLICT_ON)-(PAEF_ALIGNED_OFF-PAEF_CONFLICT_OFF)',
   'environment':env,'analysis_seed':2026082002,'analysis_bootstrap_draws':20000,'randomization_seed':rand['seed'],
   'technical_retries_max':2,'integrity_threshold_complete_fraction':0.95,'requires_each_task_all_six_cells':True,
   'science_stop_law':'one sealed scientific run; no E2E-v2, attack strengthening, model/defense expansion, extra repeats, or subgroup rescue'}
 jdump(pre/'FREEZE.json',freeze)
 # Manifest before dev live preflight. We seal final GO only after live dev preflight marker exists.
 with (pre/'PRE_SCIENCE_SHA256.tsv').open('w') as f:
  for base in [pre,pkg/'code']:
   for p in sorted(base.rglob('*')):
    if p.is_file() and p.name not in {'PRE_SCIENCE_SHA256.tsv','PREFREEZE_COMPLETE.md'}: f.write(f'{sha(p)}\t{p.relative_to(root)}\n')
 print(json.dumps({'status':'ZERO_CALL_INTEGRATED_BUILD_PASS','B':freeze['B'],'N_exec':freeze['N_exec'],'NEXT':'run one live dev preflight, then seal GO','NO_SCIENTIFIC_CALLS':True},indent=2))
if __name__=='__main__':main()
