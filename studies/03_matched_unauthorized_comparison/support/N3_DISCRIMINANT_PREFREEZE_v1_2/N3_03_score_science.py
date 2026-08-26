#!/usr/bin/env python3
"""N3 frozen local-vLLM teacher-forced scorer. DO NOT RUN until N0-FRZ is independently audited."""
from __future__ import annotations
import argparse, hashlib, json, os, time, urllib.request
from pathlib import Path
from typing import Any, Dict, List, Sequence
from n3_common import *

HTTP_TIMEOUT=300

def token_ids_sha256(ids: Sequence[int]) -> str: return sha256_text(stable_json([int(x) for x in ids]))

def append_jsonl(path: Path,row: dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(stable_json(row)+"\n"); f.flush(); os.fsync(f.fileno())

def load_cache(path: Path): return {r["cache_key"]:r for r in read_jsonl(path)} if path.exists() else {}

class Scorer:
    def __init__(self, model, revision, base_url, api_key):
        from transformers import AutoTokenizer
        self.model=model; self.revision=revision; self.base_url=base_url.rstrip('/'); self.api_key=api_key
        self.tok=AutoTokenizer.from_pretrained(model,revision=revision,use_fast=True,trust_remote_code=False)
    def _http(self,path,payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(self.base_url+path,data=data,headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"})
        with urllib.request.urlopen(req,timeout=HTTP_TIMEOUT) as r: return json.loads(r.read().decode())
    def score(self,prompt,completion):
        pids=self.tok.encode(prompt,add_special_tokens=True); cids=self.tok.encode(completion,add_special_tokens=False)
        allids=[int(x) for x in pids]+[int(x) for x in cids]; split=len(pids)
        payload={"model":self.model,"prompt":allids,"add_special_tokens":False,"max_tokens":0,"echo":True,"logprobs":1,"temperature":0,"return_tokens_as_token_ids":True}
        d=self._http('/completions',payload); vals=d['choices'][0]['logprobs']['token_logprobs']; sel=vals[split:]
        if len(vals)!=len(allids) or len(sel)!=len(cids) or any(x is None for x in sel): raise RuntimeError('invalid exact completion boundary/logprobs')
        return {"sum_logprob":float(sum(map(float,sel))),"completion_token_logprobs":[float(x) for x in sel],"completion_token_ids":[int(x) for x in cids],"completion_token_count":len(cids),"completion_token_ids_sha256":token_ids_sha256(cids),"prompt_token_count":len(pids),"prompt_token_ids_sha256":token_ids_sha256(pids),"raw_response":d,"request_payload_sha256":sha256_text(stable_json(payload))}
    def preflight(self):
        d=self._http('/models'); ids=[x.get('id') for x in d.get('data',[]) if isinstance(x,dict)]
        if self.model not in ids: raise SystemExit(f"FATAL model not served: expected {self.model}, got {ids}")
        a=self.score('N3 deterministic boundary self-test.\n<ASSISTANT_TARGET_ACTION>\n','{"ok":true}')
        b=self.score('N3 deterministic boundary self-test.\n<ASSISTANT_TARGET_ACTION>\n','{"ok":true}')
        if a['completion_token_ids_sha256']!=b['completion_token_ids_sha256'] or abs(a['sum_logprob']-b['sum_logprob'])>1e-7: raise SystemExit('FATAL scorer nondeterminism')
        return {"served_model_ids":ids,"tokenizer_name":self.tok.name_or_path,"a":{k:v for k,v in a.items() if k!='raw_response'},"b":{k:v for k,v in b.items() if k!='raw_response'}}

def verify_frozen(root:Path,rd:Path,pkg:Path):
    fr=read_json(rd/"N3_FREEZE.json")
    if fr.get('status')!='FROZEN_PRE_OUTCOME_AUTHOR': raise SystemExit('FATAL N3 not frozen')
    verify_freeze_self_hash(fr)
    verify_freeze_file_ledger(rd)
    # Verify corpus and implementation hashes, including this scorer.
    for name,h in fr['corpus_hashes'].items():
        if sha256_file(rd/name)!=h: raise SystemExit(f'FATAL frozen corpus drift {name}')
    for name,h in fr['implementation_hashes'].items():
        if sha256_file(pkg/name)!=h: raise SystemExit(f'FATAL frozen implementation drift {name}')
    verify_a14_inputs(root)
    return fr

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',required=True); ap.add_argument('--run-dir',default='N3_PREFREEZE_AUTHOR_v1'); ap.add_argument('--package-dir',default='N3_DISCRIMINANT_PREFREEZE_v1'); ap.add_argument('--scorer',choices=['llama','gemma'],required=True); ap.add_argument('--base-url',default=None); ap.add_argument('--api-key',default='x'); ap.add_argument('--preflight-only',action='store_true'); args=ap.parse_args()
    root=Path(args.project_root).resolve(); rd=root/args.run_dir; pkg=root/args.package_dir; fr=verify_frozen(root,rd,pkg)
    spec=fr['scorers'][args.scorer]; base_url=args.base_url or f"http://localhost:{spec['port']}/v1"
    # Bind the endpoint to the exact frozen local vLLM process/revision before any scorer request.
    runtime_evidence=verify_local_vllm_process(root,args.scorer,spec,base_url)
    scorer=Scorer(spec['model'],spec['revision'],base_url,args.api_key); sdir=rd/f"science_{args.scorer}"; sdir.mkdir(exist_ok=True)
    pre=scorer.preflight()
    dump_json(sdir/'SERVER_PREFLIGHT.json',{
        "model":spec,
        "base_url":base_url,
        "runtime_evidence":runtime_evidence,
        "preflight":pre,
        "freeze_sha256":fr['freeze_sha256'],
        "freeze_file_sha256":sha256_file(rd/"N3_FREEZE.json"),
    })
    if args.preflight_only:
        print(f"N3 {args.scorer} PREFLIGHT PASS; zero scientific units scored"); return
    if (sdir/'RUN_COMPLETE.json').exists():
        raise SystemExit(f"FATAL: completed N3 {args.scorer} science already exists; outcome-driven rerun prohibited")
    # Build unit/context tables from freeze artifacts.
    a14_rows=read_jsonl(root/A14_CONTEXTS_REL); a14_by={c['condition_id']:c for c in a14_rows}
    pos_rows=read_jsonl(rd/'N3_POSITIVE_CONTEXTS.jsonl'); pos_by={c['context_id']:c for c in pos_rows}
    if len(a14_rows)!=96 or len(a14_by)!=96: raise SystemExit('FATAL A14 context census mismatch')
    if len(pos_rows)!=96 or len(pos_by)!=96: raise SystemExit('FATAL N3 positive context census mismatch')
    units=[]
    for u in read_jsonl(rd/'N3_BASELINE_A14_UNITS.jsonl'): units.append(u)
    for u in read_jsonl(rd/'N3_POSITIVE_SCORING_UNITS.jsonl'): units.append(u)
    if len(units)!=288 or len({u['unit_id'] for u in units})!=288: raise SystemExit('FATAL scoring unit census mismatch')
    cache_path=sdir/'SCORE_CACHE.jsonl'; cache=load_cache(cache_path); rows=[]
    for i,u in enumerate(sorted(units,key=lambda x:x['unit_id']),1):
        if u['unit_type']=='A14_NUISANCE_REPLICATION': ctx=a14_by[u['context_id']]['context']
        else: ctx=pos_by[u['context_id']]['context']
        completion=u['target_action_serialized']
        if sha256_text(completion)!=u['target_action_sha256']: raise SystemExit(f"FATAL target-action serialization/hash mismatch {u['unit_id']}")
        prompts={"FULL":render_context(ctx),"DELETE__U":render_without(ctx,'U'),"DELETE__S_REL":render_without(ctx,'S_REL')}
        if sha256_text(prompts['FULL'])!=u['prompt_sha256']: raise SystemExit(f"FATAL full prompt hash mismatch {u['unit_id']}")
        res={}
        for aid,prompt in prompts.items():
            key=sha256_text(stable_json({"model":spec['model'],"revision":spec['revision'],"prompt":prompt,"completion":completion}))
            if key in cache: sr=cache[key]['score']
            else:
                t0=time.time(); sr=scorer.score(prompt,completion); elapsed=time.time()-t0; raw=sr.pop('raw_response')
                append_jsonl(sdir/'RAW_REQUESTS.jsonl',{"cache_key":key,"unit_id":u['unit_id'],"ablation_id":aid,"prompt_sha256":sha256_text(prompt),"completion_sha256":sha256_text(completion),"elapsed_seconds":elapsed})
                append_jsonl(sdir/'RAW_RESPONSES.jsonl',{"cache_key":key,"unit_id":u['unit_id'],"ablation_id":aid,"response":raw})
                cr={"cache_key":key,"score":sr}; append_jsonl(cache_path,cr); cache[key]=cr
            res[aid]=sr
        full=res['FULL']; ch=full['completion_token_ids_sha256']
        if any(res[a]['completion_token_ids_sha256']!=ch for a in res): raise SystemExit(f"FATAL completion boundary changed {u['unit_id']}")
        nt=full['completion_token_count']; du=full['sum_logprob']-res['DELETE__U']['sum_logprob']; ds=full['sum_logprob']-res['DELETE__S_REL']['sum_logprob']
        row={**{k:u.get(k) for k in ['unit_id','unit_type','base_id','family','descendant','provenance','directive_arm','action_role','context_id','oracle_status','oracle_reasons','target_action_sha256']},"scorer":args.scorer,"model":spec['model'],"revision":spec['revision'],"completion_token_count":nt,"completion_token_ids_sha256":ch,"lp_full":full['sum_logprob'],"lp_full_per_token":full['sum_logprob']/nt,"dU_fixed":du,"dS_relevant":ds,"CA_MARGIN":(du-ds)/nt,"CA_FLAG_0":bool(ds>du)}
        rows.append(row); print(f"[{i:03d}/288] {u['unit_id']} margin={row['CA_MARGIN']:+.6f} flag={row['CA_FLAG_0']}")
    dump_jsonl(sdir/'SCIENCE_SCORES.jsonl',rows)
    dump_json(sdir/'RUN_COMPLETE.json',{
        "freeze_sha256":fr['freeze_sha256'],
        "freeze_file_sha256":sha256_file(rd/"N3_FREEZE.json"),
        "server_preflight_sha256":sha256_file(sdir/'SERVER_PREFLIGHT.json'),
        "scorer":args.scorer,
        "model":spec,
        "n_units":len(rows),
        "science_scores_sha256":sha256_file(sdir/'SCIENCE_SCORES.jsonl'),
        "score_cache_sha256":sha256_file(cache_path),
        "raw_requests_sha256":sha256_file(sdir/'RAW_REQUESTS.jsonl'),
        "raw_responses_sha256":sha256_file(sdir/'RAW_RESPONSES.jsonl'),
    })
    print(f"N3 SCIENCE COMPLETE scorer={args.scorer} units=288")
if __name__=='__main__': main()
