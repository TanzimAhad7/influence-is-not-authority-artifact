#!/usr/bin/env python3
import argparse,hashlib,re
from pathlib import Path
ap=argparse.ArgumentParser()
ap.add_argument('--source',required=True); ap.add_argument('--c0-archive',required=True); ap.add_argument('--prefreeze-archive',required=True); ap.add_argument('--out',required=True)
a=ap.parse_args()
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
s=Path(a.source).read_text()
vals={
 'EXPECTED_C0_V21_AUTHOR_ARCHIVE_SHA256':sha(a.c0_archive),
 'EXPECTED_EXTENSION_PREFREEZE_AUTHOR_ARCHIVE_SHA256':sha(a.prefreeze_archive),
}
for key,val in vals.items():
    pat=rf'^{key}\s*=\s*"[0-9a-f]{{64}}"'
    ns,n=re.subn(pat,f'{key} = "{val}"',s,count=1,flags=re.M)
    if n!=1: raise SystemExit(f'could not patch {key}')
    s=ns
out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text(s)
print('ANONYMIZED_RUNNER_PATCH=PASS')
for k,v in vals.items(): print(k,v)
