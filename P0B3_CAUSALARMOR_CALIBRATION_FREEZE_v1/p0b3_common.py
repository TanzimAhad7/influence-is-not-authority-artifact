#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, inspect, os
from pathlib import Path

def sha256_file(path:Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def stable_json(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)
def obj_hash(obj): return hashlib.sha256(stable_json(obj).encode()).hexdigest()
def write_json(path,obj): path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n')
def source_hash(obj):
    try: s=inspect.getsource(obj)
    except Exception: return None
    return hashlib.sha256(s.encode()).hexdigest()
def tree_sha256(root:Path,suffixes=('.py',)):
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and (not suffixes or p.suffix in suffixes):
            rows.append((str(p.relative_to(root)),sha256_file(p)))
    return obj_hash(rows),rows

def read_cfg(pkg): return json.loads((Path(pkg)/'P0B3_CONFIG.json').read_text())

def package_source_hashes(pkg):
    pkg=Path(pkg)
    return {p.name:sha256_file(p) for p in sorted(pkg.iterdir()) if p.is_file() and p.name not in {'PACKAGE_SHA256.txt'}}
