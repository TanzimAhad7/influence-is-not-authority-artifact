#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,tarfile,hashlib
from pathlib import Path
from p2_common import *

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='/home/anon_/ratchet/phase0_pilot'); ap.add_argument('--package-dir',default=None); ap.add_argument('--out-dir',default=None)
    args=ap.parse_args(); root=Path(args.project_root).resolve(); pkg=Path(args.package_dir).resolve() if args.package_dir else Path(__file__).resolve().parent; out=Path(args.out_dir).resolve() if args.out_dir else root/'P2_AGENTWATCHER_NODEFENSE_RUN_v1'
    required=['P2_SCIENCE_FREEZE.json','P2_SCIENCE_FREEZE.md','P2_PREFREEZE_PACKAGE_MANIFEST.tsv','P2_RUN_COMPLETE.json','P2_RAW_RESULT_MANIFEST.tsv','P2_ANALYSIS.json','P2_ANALYSIS.md','P2_PAIRED_ROWS.csv','P2_SUITE_SUMMARY.csv']
    for n in required:
        if not (out/n).exists(): raise SystemExit('P2 VERIFY FAIL missing '+n)
    # Verify raw result hash manifest.
    for r in read_tsv(out/'P2_RAW_RESULT_MANIFEST.tsv'):
        p=out/r['relative_path']
        if not p.exists() or p.stat().st_size!=int(r['bytes']) or sha256_file(p)!=r['sha256']: raise SystemExit('P2 VERIFY FAIL raw drift '+r['relative_path'])
    a=read_json(out/'P2_ANALYSIS.json'); rc=read_json(out/'P2_RUN_COMPLETE.json'); sf=read_json(out/'P2_SCIENCE_FREEZE.json')
    if a['n_pairs']!=200 or rc['tool_knowledge_rows']!=200: raise SystemExit('P2 VERIFY FAIL population count')
    if sf['selected_pairs_sha256']!=rc['selected_pairs_sha256']: raise SystemExit('P2 VERIFY FAIL pair SHA lineage')
    if a['utility']['historical_agentwatcher_true']!=56 or a['attack_success']['historical_agentwatcher_true']!=0: raise SystemExit('P2 VERIFY FAIL historical anchor changed')
    # Final artifact hash ledger: excludes itself.
    files=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='FINAL_ARTIFACT_SHA256.txt': files.append(p)
    with (out/'FINAL_ARTIFACT_SHA256.txt').open('w') as f:
        for p in files: f.write(f'{sha256_file(p)}  {p.relative_to(out)}\n')
    print('P2 VERIFY PASS')
    print('primary_verdict='+a['primary_verdict'])
    print('final_artifact_count='+str(len(files)))
    print('final_hash_ledger_sha256='+sha256_file(out/'FINAL_ARTIFACT_SHA256.txt'))

if __name__=='__main__': main()
