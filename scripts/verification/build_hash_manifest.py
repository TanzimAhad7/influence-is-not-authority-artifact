#!/usr/bin/env python3
from pathlib import Path
import hashlib
ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'SHA256SUMS.txt'
EXCLUDED_ROOTS={'artifact_outputs','.venv','.venv-e2e','.git'}
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()
def include(p):
    if not p.is_file() or p.is_symlink() or p==MANIFEST: return False
    rel=p.relative_to(ROOT)
    if rel.parts and rel.parts[0] in EXCLUDED_ROOTS: return False
    if '__pycache__' in rel.parts or p.suffix.lower() in {'.pyc','.pyo'}: return False
    if rel.parts and (rel.parts[0].startswith('USENIX27_RERUN_') or rel.parts[0].startswith('USENIX27_FIGURE_RERUN_')): return False
    return True
paths=sorted((p for p in ROOT.rglob('*') if include(p)),key=lambda p:p.relative_to(ROOT).as_posix())
MANIFEST.write_text('\n'.join(f'{sha(p)}  {p.relative_to(ROOT).as_posix()}' for p in paths)+'\n')
print(f'WROTE SHA256SUMS.txt: {len(paths)} files')
