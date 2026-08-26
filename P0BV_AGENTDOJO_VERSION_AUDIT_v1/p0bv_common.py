#!/usr/bin/env python3
import csv, hashlib, inspect, json, math, random, statistics, copy
from collections import defaultdict
from pathlib import Path


def sha256_file(path: Path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()


def sha256_bytes(b: bytes): return hashlib.sha256(b).hexdigest()

def stable_json(obj): return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str)

def obj_hash(obj): return sha256_bytes(stable_json(obj).encode())

def load_jsonl(path): return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def write_json(path,obj): path.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False,default=str)+'\n')

def write_jsonl(path,rows):
    with path.open('w') as f:
        for r in rows: f.write(json.dumps(r,sort_keys=True,ensure_ascii=False,default=str)+'\n')

def write_csv(path,rows):
    rows=list(rows)
    if not rows: path.write_text(''); return
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def safe_source(obj):
    try: return inspect.getsource(obj)
    except Exception: return None

def source_hash(obj):
    s=safe_source(obj)
    return None if s is None else sha256_bytes(s.encode())

def class_name(obj):
    c=obj if inspect.isclass(obj) else type(obj)
    return f'{c.__module__}.{c.__qualname__}'

def dump_model(x):
    if hasattr(x,'model_dump'):
        try:return x.model_dump(mode='json')
        except Exception:return x.model_dump()
    if isinstance(x,dict):return {str(k):dump_model(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [dump_model(v) for v in x]
    if isinstance(x,(str,int,float,bool)) or x is None:return x
    return str(x)

def callable_signature(fn):
    return {'qualname':getattr(fn,'__qualname__',None),'module':getattr(fn,'__module__',None),'source_sha256':source_hash(fn)}

def dep_signature(dep):
    x=getattr(dep,'env_dependency',None)
    if callable(x): return {'kind':'callable',**callable_signature(x)}
    return {'kind':'attribute','value':str(x)}

def tool_signature(f):
    try:schema=f.parameters.model_json_schema()
    except Exception as e:schema={'ERROR':f'{type(e).__name__}: {e}'}
    return {
      'name':f.name,'description':f.description,'parameters_schema':schema,
      'dependencies':{k:dep_signature(v) for k,v in sorted(f.dependencies.items())},
      'full_docstring':f.full_docstring,
      'run':callable_signature(f.run),
      'return_type':str(f.return_type),
    }

def function_calls_dump(calls): return [dump_model(c) for c in calls]

def mean(xs): return statistics.mean(xs) if xs else None

def quantile(sorted_vals,q):
    if not sorted_vals:return None
    if len(sorted_vals)==1:return sorted_vals[0]
    pos=q*(len(sorted_vals)-1); lo=math.floor(pos); hi=math.ceil(pos)
    if lo==hi:return sorted_vals[lo]
    w=pos-lo; return sorted_vals[lo]*(1-w)+sorted_vals[hi]*w

def task_weighted_H(records,B=20000,seed=12022026):
    buckets=defaultdict(lambda:defaultdict(list))
    for r in records:
        if not r.get('primary_valid') or r.get('development'):continue
        lab=r.get('label')
        if lab not in {'SPECIFIED','DELEGATED'}:continue
        buckets[r['task_key']][lab].append(float(bool(r['H_mean_del'])))
    tv={tk:{lab:mean(vs) for lab,vs in dd.items()} for tk,dd in buckets.items()}
    tids=sorted(tv)
    def calc(sample):
        s=[];d=[]
        for tk in sample:
            if 'SPECIFIED' in tv[tk]:s.append(tv[tk]['SPECIFIED'])
            if 'DELEGATED' in tv[tk]:d.append(tv[tk]['DELEGATED'])
        if not s or not d:return None
        return {'specified_mean':mean(s),'delegated_mean':mean(d),'difference':mean(s)-mean(d),'n_specified_tasks':len(s),'n_delegated_tasks':len(d),'n_unique_tasks':len(set(sample))}
    pt=calc(tids)
    if pt is None:return None
    rng=random.Random(seed); draws=[]
    for _ in range(B):
        z=calc([tids[rng.randrange(len(tids))] for __ in tids])
        if z:draws.append(z['difference'])
    draws.sort(); pt['ci95']=[quantile(draws,.025),quantile(draws,.975)];pt['bootstrap_valid_draws']=len(draws)
    return pt

def task_key_from_decision(did):
    parts=did.split('/')
    return '/'.join(parts[:2]) if len(parts)>=2 else did

def recursive_find_pairs(obj):
    out=[]
    if isinstance(obj,dict):
        if {'suite','user_task_id','injection_task_id'} <= set(obj):
            out.append({'suite':obj['suite'],'user_task_id':obj['user_task_id'],'injection_task_id':obj['injection_task_id']})
        for v in obj.values():out.extend(recursive_find_pairs(v))
    elif isinstance(obj,list):
        for v in obj:out.extend(recursive_find_pairs(v))
    return out

def tree_sha256(root:Path,suffixes=('.py',)):
    rows=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and (not suffixes or p.suffix in suffixes):
            rows.append((str(p.relative_to(root)),sha256_file(p)))
    return obj_hash(rows), rows
