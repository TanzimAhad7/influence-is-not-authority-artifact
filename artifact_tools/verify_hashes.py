#!/usr/bin/env python3
from pathlib import Path
import hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=ROOT/'SHA256SUMS.txt'
EXCLUDED_ROOTS={'artifact_outputs','.venv','.venv-e2e','.git'}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
if not MANIFEST.is_file(): print('INTEGRITY=FAIL missing SHA256SUMS.txt'); sys.exit(1)
expected={}
for i,line in enumerate(MANIFEST.read_text().splitlines(),1):
    if not line.strip(): continue
    try:d,r=line.split('  ',1)
    except ValueError: print('INTEGRITY=FAIL malformed line',i); sys.exit(1)
    expected[r]=d
missing=[];changed=[]
for r,d in expected.items():
    p=ROOT/r
    if not p.is_file(): missing.append(r)
    elif sha(p)!=d: changed.append(r)
actual=set()
for p in ROOT.rglob('*'):
    if not p.is_file() or p.is_symlink() or p==MANIFEST: continue
    rel=p.relative_to(ROOT)
    if rel.parts and rel.parts[0] in EXCLUDED_ROOTS: continue
    if '__pycache__' in rel.parts or p.suffix.lower() in {'.pyc','.pyo'}: continue
    if rel.parts and (rel.parts[0].startswith('USENIX27_RERUN_') or rel.parts[0].startswith('USENIX27_FIGURE_RERUN_')): continue
    actual.add(rel.as_posix())
extra=sorted(actual-set(expected))
if missing or changed or extra:
    print('INTEGRITY=FAIL')
    for label,xs in [('missing',missing),('changed',changed),('extra',extra)]:
        if xs:
            print(label+':')
            for x in xs[:100]: print(' -',x)
    sys.exit(1)
print(f'INTEGRITY=PASS ({len(expected)} files)')
