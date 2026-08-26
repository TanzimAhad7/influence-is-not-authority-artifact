#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib
from pathlib import Path


def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--out-dir',required=True); args=ap.parse_args()
    out=Path(args.out_dir).resolve()
    names=['P3_C0_ANALYSIS_FREEZE.json','P3_C0_REFRESH.json','P3_C0_LEAVE_ONE_SUITE_OUT.csv','P3_C0_LEAVE_ONE_TASK_OUT.csv','P3_C0_TASK_SPAN_DIAGNOSTICS.csv','P3_C0_FOREST.svg','P3_C0_SUMMARY.md']
    missing=[n for n in names if not (out/n).exists()]
    if missing: raise SystemExit('FATAL missing outputs: '+', '.join(missing))
    lines=[f'{sha256(out/n)}  {n}' for n in names]
    (out/'FINAL_SHA256.txt').write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
