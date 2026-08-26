#!/usr/bin/env python3
"""A14-MINIMAL step 03: frozen boundary-safe teacher-forced scorer."""
from __future__ import annotations
import argparse, json, os, sys, time, urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence
from a14m_common import *

HTTP_TIMEOUT=300

def token_ids_sha256(ids: Sequence[int]) -> str: return sha256_text(stable_json([int(x) for x in ids]))

class BoundarySafeScorer:
    def __init__(self,model,base_url,api_key,tokenizer_name):
        self.model=model; self.base_url=base_url.rstrip('/'); self.api_key=api_key; self.tok=TokenizerAdapter(tokenizer_name,allow_fallback=False)
    def _http(self,path,payload=None):
        data=None if payload is None else json.dumps(payload).encode()
        req=urllib.request.Request(self.base_url+path,data=data,headers={'Authorization':f'Bearer {self.api_key}','Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=HTTP_TIMEOUT) as r: return json.loads(r.read().decode())
    def score(self,prompt,completion):
        pids=self.tok.encode(prompt,add_special_tokens=True); cids=self.tok.encode(completion,add_special_tokens=False)
        allids=[int(x) for x in pids]+[int(x) for x in cids]; split=len(pids)
        payload={'model':self.model,'prompt':allids,'add_special_tokens':False,'max_tokens':0,'echo':True,'logprobs':1,'temperature':0,'return_tokens_as_token_ids':True}
        d=self._http('/completions',payload); vals=d['choices'][0]['logprobs']['token_logprobs']; sel=vals[split:]
        if len(vals)!=len(allids) or len(sel)!=len(cids) or any(x is None for x in sel): raise RuntimeError('invalid exact completion boundary/logprobs')
        return {'sum_logprob':float(sum(map(float,sel))),'completion_token_logprobs':[float(x) for x in sel],'completion_token_ids':[int(x) for x in cids],'completion_token_count':len(cids),'completion_token_ids_sha256':token_ids_sha256(cids),'prompt_token_count':len(pids),'prompt_token_ids_sha256':token_ids_sha256(pids),'raw_response':d,'request_payload_sha256':sha256_text(stable_json(payload))}
    def preflight(self):
        d=self._http('/models'); ids=[x.get('id') for x in d.get('data',[]) if isinstance(x,dict)]
        if self.model not in ids: raise SystemExit(f'FATAL {self.model} not served; available={ids}')
        a=self.score('A benign deterministic scoring self-test.\n<ASSISTANT_TARGET_ACTION>\n','{"ok":true}')
        b=self.score('A benign deterministic scoring self-test.\n<ASSISTANT_TARGET_ACTION>\n','{"ok":true}')
        if a['completion_token_ids_sha256']!=b['completion_token_ids_sha256'] or abs(a['sum_logprob']-b['sum_logprob'])>1e-7: raise SystemExit('FATAL scorer nondeterminism/self-test failure')
        return {'served_model_ids':ids,'a':{k:v for k,v in a.items() if k!='raw_response'},'b':{k:v for k,v in b.items() if k!='raw_response'}}

def append_jsonl(path,row):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f: f.write(stable_json(row)+'\n'); f.flush(); os.fsync(f.fileno())

def load_cache(path):
    return {r['cache_key']:r for r in read_jsonl(path)} if path.exists() else {}

def verify_sources(root,out,protocol):
    for f,expected in protocol['source_hashes'].items():
        p=root/f
        if not p.exists() or sha256_file(p)!=expected: raise SystemExit(f'FATAL frozen source drift: {f}')
    for f,expected in protocol['corpus_hashes'].items():
        p=out/f
        if not p.exists() or sha256_file(p)!=expected: raise SystemExit(f'FATAL frozen corpus drift: {f}')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='.'); ap.add_argument('--scorer-label',choices=['llama','gemma'],default='llama'); ap.add_argument('--base-url',default=os.environ.get('A14M_SCORER_BASE_URL','http://localhost:8110/v1')); ap.add_argument('--api-key',default=os.environ.get('A14M_SCORER_API_KEY','x')); ap.add_argument('--preflight-only',action='store_true'); args=ap.parse_args()
    root=project_root_from_args(args); out=a14_dir(root); protocol=read_json(out/'protocol.json') if (out/'protocol.json').exists() else None
    if not protocol or protocol.get('status')!='FROZEN_PRE_OUTCOME': raise SystemExit('FATAL protocol not frozen; scoring forbidden')
    verify_sources(root,out,protocol)
    model=protocol['primary_scorer'] if args.scorer_label=='llama' else protocol['source_fidelity_scorer']; scorer=BoundarySafeScorer(model,args.base_url,args.api_key,model)
    pre=scorer.preflight(); sdir=out/f'scorer_{args.scorer_label}'; sdir.mkdir(parents=True,exist_ok=True); dump_json(sdir/'server_preflight.json',{'protocol_hash':protocol['protocol_hash'],'model':model,'base_url':args.base_url,'tokenizer':scorer.tok.metadata(),'preflight':pre,'created_at_utc':now_utc()})
    if args.preflight_only: print(f'[A14M-03] PREFLIGHT PASS {args.scorer_label}; no condition outcomes emitted'); return
    conds=read_jsonl(out/'contexts'/'structured_contexts.jsonl'); conds.sort(key=lambda c:c['condition_id'])
    neutral={(r['condition_id'],r['component_id']):r['neutral_text'] for r in read_jsonl(out/'neutral_replacements.jsonl')}
    frozen=read_jsonl(out/f'scoring_plan_{args.scorer_label}.jsonl'); recomputed=a14m_build_scoring_plan(conds,neutral,args.scorer_label)
    if stable_json(frozen)!=stable_json(recomputed): raise SystemExit('FATAL scoring plan regeneration differs from freeze')
    cache_path=sdir/'score_cache.jsonl'; cache=load_cache(cache_path); rows=[]
    base_map={b['base_id']:b for b in read_json(out/'base_instances.json')['instances']}
    token_map={r['condition_id']:r for r in read_jsonl(out/'contexts'/'token_maps.jsonl')}
    for i,c in enumerate(conds,1):
        completion=c['target_action_serialized']; abls=a14m_build_ablations(c,neutral,args.scorer_label); res={}
        for a in abls:
            key=sha256_text(stable_json({'model':model,'prompt':a['prompt'],'completion':completion}))
            if key in cache: sr=cache[key]['score']
            else:
                t0=time.time(); sr=scorer.score(a['prompt'],completion); elapsed=time.time()-t0; raw=sr.pop('raw_response')
                append_jsonl(sdir/'raw_requests.jsonl',{'cache_key':key,'condition_id':c['condition_id'],'ablation_id':a['ablation_id'],'prompt_sha256':sha256_text(a['prompt']),'completion_sha256':sha256_text(completion),'created_at_utc':now_utc()})
                append_jsonl(sdir/'raw_responses.jsonl',{'cache_key':key,'condition_id':c['condition_id'],'ablation_id':a['ablation_id'],'elapsed_seconds':elapsed,'response':raw})
                crow={'cache_key':key,'score':sr}; append_jsonl(cache_path,crow); cache[key]=crow
            res[a['ablation_id']]={'score':sr,'cache_key':key,'meta':{k:v for k,v in a.items() if k!='prompt'}}
        full=res['FULL']['score']; ch=full['completion_token_ids_sha256']
        for aid,r in res.items():
            if r['score']['completion_token_ids_sha256']!=ch: raise RuntimeError(f'completion hash changed {c["condition_id"]}/{aid}')
        if args.scorer_label=='llama' and ch!=token_map[c['condition_id']]['completion_token_ids_sha256']: raise RuntimeError(f'frozen Llama completion hash mismatch {c["condition_id"]}')
        def d(aid): return full['sum_logprob']-res[aid]['score']['sum_logprob']
        nt=full['completion_token_count']; du=d('DELETE__U'); ds=d('DELETE__S_REL'); margin=(du-ds)/nt
        row={'schema_version':SCHEMA_VERSION,'protocol_hash':protocol['protocol_hash'],'scorer_label':args.scorer_label,'model':model,'condition_id':c['condition_id'],'base_id':c['base_id'],'family':c['family'],'factor_provenance':c['factor_provenance'],'factor_descendant':c['factor_descendant'],'prompt_sha256':c['prompt_sha256'],'completion_token_count':nt,'completion_token_ids_sha256':ch,'lp_full':full['sum_logprob'],'dU_fixed':du,'dS_relevant':ds,'bar_dU_fixed':du/nt,'bar_dS_relevant':ds/nt,'CA_MARGIN':margin,'CA_FLAG_0':bool(ds>du),'dDesc':d('DELETE__DESC'),'dU_closure':d('DELETE__U_LINEAGE_CLOSURE'),'closure_gap':d('DELETE__U_LINEAGE_CLOSURE')-du}
        if args.scorer_label=='llama':
            dur=d('REPLACE__U'); dsr=d('REPLACE__S_REL'); row.update({'dU_replace':dur,'dS_replace':dsr,'CA_MARGIN_REPLACE':(dur-dsr)/nt,'CA_FLAG_0_REPLACE':bool(dsr>dur),'dDesc_replace':d('REPLACE__DESC'),'dU_plus_relevant':d('DELETE__U_PLUS_RELEVANT')})
        # Action-token factorization for the primary DELETE U and DELETE S margin.
        sem=build_action_token_semantic_map(base_map[c['base_id']],scorer.tok); groups=[x['semantic_group'] for x in sem['token_rows']]
        if len(groups)!=nt: raise RuntimeError('action token semantic length mismatch')
        factor={}
        for aid in ['DELETE__U','DELETE__S_REL','DELETE__U_LINEAGE_CLOSURE']:
            diffs=[x-y for x,y in zip(full['completion_token_logprobs'],res[aid]['score']['completion_token_logprobs'])]; gd=defaultdict(float)
            for g,v in zip(groups,diffs): gd[g]+=float(v)
            factor[aid]=dict(gd)
        row['action_token_factorization']=factor
        rows.append(row); print(f"[{i:03d}/{len(conds):03d}] {c['condition_id']} margin={margin:+.6f} flag={row['CA_FLAG_0']}")
    dump_jsonl(sdir/'condition_scores.jsonl',rows); dump_json(sdir/'RUN_COMPLETE.json',{'protocol_hash':protocol['protocol_hash'],'scorer_label':args.scorer_label,'model':model,'n_conditions':len(rows),'condition_scores_sha256':sha256_file(sdir/'condition_scores.jsonl'),'completed_at_utc':now_utc()})
    print(f'[A14M-03] COMPLETE scorer={args.scorer_label} conditions={len(rows)}')

if __name__=='__main__': main()
