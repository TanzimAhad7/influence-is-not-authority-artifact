#!/usr/bin/env python3
from __future__ import annotations
import argparse, sys
from pathlib import Path
from p6_common import sha256, load_json

EXPECTED=[
    'P6_INPUT_MANIFEST.tsv','P6_INPUT_FREEZE.json','P6_INPUT_FREEZE.md',
    'P6_MASTER_EVALUATION_VECTOR.csv','P6_AUTHORIZATION_STRATIFIED_BENIGN.csv','P6_CONTROLLED_BENIGN_CONSISTENCY.csv',
    'P6_ATTACK_ANCHORS.csv','P6_REPLAY_EQUIVALENCE_MATRIX.csv','P6_ARGUMENT_ROLE_HSLOT.csv','P6_SELECTED_POPULATION_BEHAVIOR.csv',
    'P6_EQUIVALENCE_LADDER.csv','P6_CLAIM_LEDGER.csv','P6_EVALUATION_FRAMEWORK.svg','P6_SYNTHESIS.json','P6_SUMMARY.md',
]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--out-dir',required=True)
    a=ap.parse_args()
    out=Path(a.out_dir).resolve()
    missing=[x for x in EXPECTED if not (out/x).is_file()]
    if missing:
        print('P6 VERIFY FAIL missing:',missing,file=sys.stderr)
        raise SystemExit(2)
    syn=load_json(out/'P6_SYNTHESIS.json')
    if syn.get('status')!='COMPLETE' or syn.get('scientific_model_calls')!=0:
        raise SystemExit('P6 VERIFY FAIL: synthesis status')
    if syn['controlled']['agentwatcher_flags']!=[0,48]:
        raise SystemExit('P6 VERIFY FAIL: AgentWatcher controlled')
    if syn['controlled']['attriguard_final_blocks']!=[0,480]:
        raise SystemExit('P6 VERIFY FAIL: AttriGuard endpoint')
    if syn['controlled']['attriguard_routes']!={'strict':441,'fuzzy':39}:
        raise SystemExit('P6 VERIFY FAIL: AttriGuard route')
    if syn['natural_original26']['a15a_activation']!=[18,26] or syn['natural_original26']['causalarmor_flags']!=[16,26] or syn['natural_original26']['agentwatcher_flags']!=[2,26]:
        raise SystemExit('P6 VERIFY FAIL: natural operating points')
    if [(x['attack_success_n'],x['n']) for x in syn['attack_anchors'][:2]]!=[(1,200),(0,200)]:
        raise SystemExit('P6 VERIFY FAIL: AgentWatcher attacks')

    rows=[]
    for p in sorted(out.iterdir()):
        if p.is_file() and p.name!='FINAL_ARTIFACT_SHA256.txt':
            rows.append((sha256(p),p.name))
    with (out/'FINAL_ARTIFACT_SHA256.txt').open('w',encoding='utf-8') as f:
        for h,n in rows:
            f.write(f'{h}  {n}\n')
    print('P6 CLEAN VERIFY PASS')
    print('hashed_outputs=',len(rows))
    print('FINAL_ARTIFACT_SHA256.txt sha256=',sha256(out/'FINAL_ARTIFACT_SHA256.txt'))

if __name__=='__main__':
    main()
