#!/usr/bin/env python3
from __future__ import annotations
import csv, hashlib, json
from pathlib import Path

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1<<20), b''):
            h.update(block)
    return h.hexdigest()

def load_json(path: Path):
    with path.open(encoding='utf-8') as f:
        return json.load(f)

def load_jsonl(path: Path):
    rows=[]
    with path.open(encoding='utf-8') as f:
        for i,line in enumerate(f,1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception as e:
                    raise RuntimeError(f'{path}:{i}: {e}')
    return rows

def load_csv(path: Path):
    with path.open(newline='',encoding='utf-8') as f:
        return list(csv.DictReader(f))

def write_csv(path: Path, rows, fieldnames=None):
    rows=list(rows)
    if fieldnames is None:
        fieldnames=list(rows[0].keys()) if rows else []
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

def pct(n,d):
    return 100.0*n/d if d else None
