#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,hashlib,json
from pathlib import Path

def sha256_file(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for c in iter(lambda:f.read(1<<20),b''): h.update(c)
    return h.hexdigest()

def read_csv(p):
    with p.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))

def write_csv(p,rows,fields):
    with p.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--phase0-2-dir',required=True,type=Path)
    ap.add_argument('--agentdojo-v1-dir',required=True,type=Path)
    ap.add_argument('--out-dir',required=True,type=Path)
    a=ap.parse_args();a.out_dir.mkdir(parents=True,exist_ok=True)
    src=a.phase0_2_dir/'02_MULTI_CALL_SOURCE_AUDIT.csv'
    rows=read_csv(src)
    if len(rows)!=7: raise SystemExit(f'Expected 7 source-audit rows, got {len(rows)}')
    out=[];changed=[]
    function_to_tool={'invite_user_to_slack':'slack.py','add_user_to_channel':'slack.py','post_webpage':'web.py'}
    for r in rows:
        r=dict(r); fn=r['privileged_fn']
        if fn not in function_to_tool: raise SystemExit(f'Unexpected audited function {fn}')
        p=a.agentdojo_v1_dir/'tools'/function_to_tool[fn]
        if not p.exists(): raise SystemExit(f'Missing tool source {p}')
        old=r.get('tool_source',''); old_sha=r.get('tool_source_sha256','')
        r['original_tool_source']=old; r['original_tool_source_sha256']=old_sha
        r['tool_source']=str(p); r['tool_source_sha256']=sha256_file(p)
        r['provenance_amendment']='CORRECT_TOOL_SOURCE_BY_FUNCTION'
        if old_sha!=r['tool_source_sha256']:
            changed.append(r['task_key'])
        out.append(r)
    expected_changed=['slack/user_task_4']
    if changed!=expected_changed:
        raise SystemExit(f'Unexpected provenance-change set {changed}; expected {expected_changed}')
    # Scientific/source-semantic decisions MUST NOT change.
    counts={v:sum(r['verdict']==v for r in out) for v in ['PASS','FAIL','PENDING']}
    if counts!={'PASS':3,'FAIL':4,'PENDING':0}: raise SystemExit(f'Verdict counts changed: {counts}')
    fields=list(rows[0].keys())+['original_tool_source','original_tool_source_sha256','provenance_amendment']
    write_csv(a.out_dir/'A1_SOURCE_AUDIT_PROVENANCE_AMENDMENT.csv',out,fields)
    summary={
      'NO_MODEL_CALLS':True,
      'status':'PASS_BOOKKEEPING_PROVENANCE_AMENDMENT_ONLY',
      'original_source_audit_sha256':sha256_file(src),
      'changed_rows':changed,
      'reason':'Original Phase A1 script keyed tool-source provenance by suite; slack/user_task_4 audits post_webpage, whose implementation is v1/tools/web.py rather than v1/tools/slack.py. The PASS/FAIL semantic verdict and cohort membership are unchanged.',
      'verdict_counts':counts,
      'preliminary_B_unchanged':14,
      'science_changed':False,
    }
    (a.out_dir/'A1_PROVENANCE_AMENDMENT.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary,indent=2,sort_keys=True))
if __name__=='__main__': main()
