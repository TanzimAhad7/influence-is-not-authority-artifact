#!/usr/bin/env python3
"""A14-MINIMAL step 01: 16-pair outcome-blinded human construct audit."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
from a14m_common import *


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='.'); args=ap.parse_args()
    out=a14_dir(project_root_from_args(args))
    if (out/'protocol.json').exists(): raise SystemExit('FATAL protocol already frozen')
    if any((out/p).exists() for p in ['scorer_llama/condition_scores.jsonl','scorer_gemma/condition_scores.jsonl']):
        raise SystemExit('FATAL scorer outcomes exist; human audit must be pre-outcome')
    templ=read_jsonl(out/'human_equivalence_audit_TEMPLATE.jsonl')
    if not templ: raise SystemExit('FATAL audit template missing')
    path=out/'human_equivalence_audit.jsonl'
    existing={r['audit_id']:r for r in read_jsonl(path)} if path.exists() else {}
    rows=[]
    print(f'A14M human audit: {len(templ)} frozen pairs. This checks semantic authorization equivalence, not model outcomes.')
    print('y=yes equivalent, n=no, s=skip/pending, q=save+quit')
    for i,r0 in enumerate(templ,1):
        if r0['audit_id'] in existing and existing[r0['audit_id']].get('human_auth_equivalent') is not None:
            rows.append(existing[r0['audit_id']]); continue
        print('\n'+'='*100)
        print(f"[{i}/{len(templ)}] {r0['audit_class']}  {r0['family']}  {r0['base_id']}")
        print('- SOURCE -'); print(r0['source_prompt'])
        print('- TARGET -'); print(r0['target_prompt'])
        print('- CHECK - same user-authorized operation/target/constraints and exact final action? tool facts remain execution evidence, not permission?')
        while True:
            ans=input('[y/n/s/q] > ').strip().lower()
            if ans in {'y','n','s','q'}: break
        if ans=='q':
            # preserve unfinished row as pending only if not already saved
            write=rows + [existing[x['audit_id']] for x in templ if x['audit_id'] in existing and x['audit_id'] not in {z['audit_id'] for z in rows}]
            dump_jsonl(path,write); print('Saved; audit incomplete.'); return
        rr=dict(r0)
        rr['human_auth_equivalent'] = True if ans=='y' else (False if ans=='n' else None)
        rr['rationale'] = 'human outcome-blinded construct judgment'
        rows.append(rr)
        dump_jsonl(path,rows)
    passed=sum(r.get('human_auth_equivalent') is True for r in rows)
    failed=sum(r.get('human_auth_equivalent') is False for r in rows)
    pending=sum(r.get('human_auth_equivalent') is None for r in rows)
    print(f'[A14M-01] pass={passed} fail={failed} pending={pending}')
    if failed or pending: raise SystemExit('A14M human audit not clean; DO NOT FREEZE/SCORE')
    print('[A14M-01] PASS')

if __name__=='__main__': main()
