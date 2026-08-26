#!/usr/bin/env python3
from __future__ import annotations
import copy, hashlib, json
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent

def stable_json(obj: Any) -> str:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False)

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):
            h.update(chunk)
    return h.hexdigest()

def global_freeze_hash(obj: dict[str,Any]) -> str:
    d=copy.deepcopy(obj); d.pop('freeze_sha256',None)
    return hashlib.sha256(stable_json(d).encode()).hexdigest()

def load_and_verify_global_freeze(path: Path | None=None) -> dict[str,Any]:
    path=Path(path or (HERE/'P2B_XM_CI_GLOBAL_FREEZE.json')).resolve()
    d=json.loads(path.read_text())
    got=global_freeze_hash(d)
    if got!=d.get('freeze_sha256'):
        raise SystemExit(f'FATAL global freeze hash mismatch expected={d.get("freeze_sha256")} got={got}')
    for rel,exp in d.get('source_hashes',{}).items():
        p=HERE/rel
        if not p.exists(): raise SystemExit(f'FATAL frozen source missing {rel}')
        got=sha256_file(p)
        if got!=exp: raise SystemExit(f'FATAL frozen source drift {rel}: expected={exp} got={got}')
    return d
