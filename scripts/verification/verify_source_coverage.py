#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,sys,collections
ROOT=Path(__file__).resolve().parents[2]
TSV=ROOT/'supporting_material/provenance/SOURCE_ARTIFACT_COVERAGE.tsv'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
counts=collections.Counter(); missing=[]; bad=[]; total=0
with TSV.open(newline='',encoding='utf-8') as f:
    for r in csv.DictReader(f,delimiter='\t'):
        total+=1; st=r['status']; counts[st]+=1
        if st.startswith('excluded_'): continue
        p=ROOT/r['final_path']
        if not p.is_file(): missing.append(r['final_path']); continue
        if sha(p)!=r['final_sha256']: bad.append(r['final_path'])
if total!=5731:
    print(f'SOURCE_ARTIFACT_COVERAGE=FAIL expected 5731 rows, got {total}'); sys.exit(1)
if missing or bad:
    print('SOURCE_ARTIFACT_COVERAGE=FAIL')
    for x in missing[:50]: print('missing',x)
    for x in bad[:50]: print('hash_mismatch',x)
    sys.exit(1)
excluded=sum(n for st,n in counts.items() if st.startswith('excluded_'))
retained=total-excluded
print(f'SOURCE_ARTIFACT_COVERAGE=PASS ({retained}/{total} source files retained; {excluded} documented exclusions)')
print('status_counts=',dict(counts))
