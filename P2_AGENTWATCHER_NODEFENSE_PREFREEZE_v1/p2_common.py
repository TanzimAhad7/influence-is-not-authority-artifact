from __future__ import annotations
from pathlib import Path
import csv, hashlib, json, os

def sha256_file(p: Path) -> str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def canonical_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def read_json(p: Path): return json.loads(p.read_text())

def write_json(p: Path,obj): p.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')

def read_tsv(p: Path):
    with p.open(newline='') as f: return list(csv.DictReader(f,delimiter='\t'))

def pair_key(d):
    return (d['suite_name'],d['user_task_id'],d['injection_task_id'])
