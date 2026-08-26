#!/usr/bin/env python3
from pathlib import Path
import argparse
from p0b3_live_common import sha256_file
ap=argparse.ArgumentParser(); ap.add_argument('--out-dir',required=True); a=ap.parse_args(); out=Path(a.out_dir)
names=['P0B3_LIVE_IMPLEMENTATION_FREEZE.json','P0B3_LIVE_PREFLIGHT.md','P0B3_TECHNICAL_CALLS.jsonl','P0B3_SCIENCE_ROWS.jsonl','P0B3_DEFENSE_EVENTS.jsonl','P0B3_PROVIDER_CALLS.jsonl','P0B3_ANALYSIS.json','P0B3_SUITE_RESULTS.csv','P0B3_REPORT.md']
rows=[]
for n in names:
    p=out/n
    if p.exists(): rows.append((sha256_file(p),n))
(out/'FINAL_ARTIFACT_SHA256.txt').write_text(''.join(f'{h}  {n}\n' for h,n in rows),encoding='utf-8')
print(f'hashed {len(rows)} final artifacts')
