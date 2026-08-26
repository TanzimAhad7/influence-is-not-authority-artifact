#!/usr/bin/env python3
from pathlib import Path
import argparse,hashlib

def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out-dir',required=True);a=ap.parse_args();out=Path(a.out_dir)
 rows=[]
 for p in sorted(out.iterdir()):
  if p.is_file() and p.name!='FINAL_ARTIFACT_SHA256.txt': rows.append((sha(p),p.name))
 (out/'FINAL_ARTIFACT_SHA256.txt').write_text(''.join(f'{h}  {n}\n' for h,n in rows))
 print(f'hashed {len(rows)} outputs')
if __name__=='__main__':main()
