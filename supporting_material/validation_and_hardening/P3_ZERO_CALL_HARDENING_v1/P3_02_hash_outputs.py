#!/usr/bin/env python3
import argparse, hashlib
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

ap=argparse.ArgumentParser(); ap.add_argument('--out-dir',required=True); a=ap.parse_args(); out=Path(a.out_dir)
files=[p for p in sorted(out.iterdir()) if p.is_file() and p.name!='FINAL_ARTIFACT_SHA256.txt']
lines=[f'{sha(p)}  {p.name}' for p in files]
(out/'FINAL_ARTIFACT_SHA256.txt').write_text('\n'.join(lines)+'\n')
print('\n'.join(lines))
