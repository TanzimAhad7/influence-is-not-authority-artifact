#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any, Dict, List

SCHEMA = "P0B3_ACT_SHADOW_POSTHOC_V1"
EXPECTED_EVENT_SCHEMA = "P0B3_DEFENSE_EVENT_V1"
EXPECTED_INPUT_REL = Path("P0B3_CAUSALARMOR_LIVE_RUN_v1/P0B3_DEFENSE_EVENTS.jsonl")
EXPECTED_INPUT_SHA256 = "bc8c17c257b00a12295c54384c9ce7bc3490f8d6c1f1d3b89aee36641253746a"
EXPECTED_TOTAL_EVENTS = 624
EXPECTED_OVERALL_SHADOW_FLAGGED = 538
EXPECTED_DENOMINATORS = {"benign": 37, "attack": 587}
GROUPS = ("benign", "attack")
SOURCE_FILES = ("p0b3_act_shadow_common.py", "P0B3_ACT_SHADOW_00_freeze.py", "P0B3_ACT_SHADOW_01_run.py")

def sha256_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for c in iter(lambda:f.read(1024*1024), b''): h.update(c)
    return h.hexdigest()

def read_jsonl(path: Path) -> List[Dict[str,Any]]:
    out=[]
    with path.open(encoding='utf-8') as f:
        for n,line in enumerate(f,1):
            if not line.strip(): continue
            x=json.loads(line)
            if not isinstance(x,dict): raise RuntimeError(f"row {n}: non-object")
            out.append(x)
    return out

def group(ep: str) -> str:
    if not isinstance(ep,str) or ':' not in ep: raise RuntimeError(f"bad episode_id {ep!r}")
    g=ep.split(':',1)[0]
    if g not in GROUPS: raise RuntimeError(f"bad group {g!r}")
    return g

def validate(rows, *, aggregate_shadow: bool):
    if len(rows)!=EXPECTED_TOTAL_EVENTS: raise RuntimeError(f"expected {EXPECTED_TOTAL_EVENTS}, got {len(rows)}")
    seen=set(); den={g:0 for g in GROUPS}; flagged={g:0 for g in GROUPS}
    for i,r in enumerate(rows,1):
        if r.get('schema')!=EXPECTED_EVENT_SCHEMA: raise RuntimeError(f"row {i}: schema")
        ep=r.get('episode_id'); aid=r.get('attempt_id'); di=r.get('decision_index')
        if not isinstance(aid,str) or not aid: raise RuntimeError(f"row {i}: attempt_id")
        if not isinstance(di,int): raise RuntimeError(f"row {i}: decision_index")
        key=(ep,aid,di)
        if key in seen: raise RuntimeError(f"row {i}: duplicate event identity")
        seen.add(key)
        shadow=r.get('shadow_any_flag')
        if not isinstance(shadow,bool): raise RuntimeError(f"row {i}: shadow_any_flag must be bool")
        g=group(ep); den[g]+=1
        if aggregate_shadow and shadow: flagged[g]+=1
    if den!=EXPECTED_DENOMINATORS: raise RuntimeError(f"denominator mismatch: {den}")
    z={'total_events':len(rows),'unique_event_identities':len(seen),'denominators':den}
    if aggregate_shadow: z['flagged']=flagged
    return z

def source_hashes(package_dir: Path):
    return {name:sha256_file(package_dir/name) for name in SOURCE_FILES}

def write_json(path: Path, obj):
    path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
