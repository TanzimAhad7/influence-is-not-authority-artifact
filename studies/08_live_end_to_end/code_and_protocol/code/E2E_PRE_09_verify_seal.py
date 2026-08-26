#!/usr/bin/env python3
from __future__ import annotations
import hashlib,sys
from pathlib import Path

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 root=Path(sys.argv[1]).resolve();pre=root/'E2E_ATTR_AUTH_v1/prefreeze/final_prescience_build'
 if 'GO: PASS' not in (pre/'PREFREEZE_COMPLETE.md').read_text():raise SystemExit('FATAL GO seal missing')
 n=0
 for line in (pre/'PREFREEZE_SHA256.tsv').read_text().splitlines():
  if not line.strip():continue
  exp,rel=line.split('\t',1);p=root/rel;n+=1
  if not p.exists():raise SystemExit(f'FATAL sealed path missing {rel}')
  got=sha(p)
  if got!=exp:raise SystemExit(f'FATAL sealed path drift {rel} expected={exp} got={got}')
 print(f'PREFREEZE SEAL VERIFY PASS files={n}')
if __name__=='__main__':main()
