#!/usr/bin/env python3
"""A14-MINIMAL step 04: frozen paired factorial analysis. No model/API calls."""
from __future__ import annotations
import argparse, json, math, random, statistics, sys
from collections import defaultdict
from pathlib import Path
from a14m_common import *

B=20000; SEED=14031431

def verify_sources(root,out,protocol):
    for f,expected in protocol['source_hashes'].items():
        p=root/f
        if not p.exists() or sha256_file(p)!=expected: raise SystemExit(f'FATAL frozen source drift: {f}')
    for f,expected in protocol['corpus_hashes'].items():
        p=out/f
        if not p.exists() or sha256_file(p)!=expected: raise SystemExit(f'FATAL frozen corpus drift: {f}')

def ci_mean(xs,seed):
    if not xs: return [None,None]
    rng=random.Random(seed); n=len(xs); draws=[]
    for _ in range(B): draws.append(statistics.mean(xs[rng.randrange(n)] for _ in range(n)))
    draws.sort(); return [draws[int(.025*B)],draws[min(B-1,int(.975*B))]]

def summarize(xs,seed): return {'n':len(xs),'mean':statistics.mean(xs),'median':statistics.median(xs),'ci95':ci_mean(xs,seed),'n_negative':sum(x<0 for x in xs),'n_positive':sum(x>0 for x in xs),'n_zero':sum(x==0 for x in xs)}

def factorial(rows,metric):
    by=defaultdict(dict)
    for r in rows: by[r['base_id']][(r['factor_provenance'],r['factor_descendant'])]=r
    prov=[]; echo=[]; inter=[]; per=[]
    for bid,c in sorted(by.items()):
        if set(c)!={('USER_ID','SHAM'),('USER_ID','ECHO'),('TOOL_ID','SHAM'),('TOOL_ID','ECHO')}: raise RuntimeError(f'incomplete base {bid}')
        us=c[('USER_ID','SHAM')][metric]; ue=c[('USER_ID','ECHO')][metric]; ts=c[('TOOL_ID','SHAM')][metric]; te=c[('TOOL_ID','ECHO')][metric]
        ep=.5*((ts-us)+(te-ue)); ee=.5*((ue-us)+(te-ts)); ii=(te-ts)-(ue-us)
        prov.append(ep); echo.append(ee); inter.append(ii); per.append({'base_id':bid,'family':c[('USER_ID','SHAM')]['family'],'P1_provenance':ep,'P3_descendant':ee,'interaction':ii,'cells':{'U_SHAM':us,'U_ECHO':ue,'T_SHAM':ts,'T_ECHO':te}})
    return {'P1_PROVENANCE_MAIN':summarize(prov,SEED+1),'P3_DESCENDANT_MAIN':summarize(echo,SEED+2),'P1xP3_INTERACTION':summarize(inter,SEED+3),'per_base':per}

def binary_edges(rows):
    by=defaultdict(dict)
    for r in rows: by[r['base_id']][(r['factor_provenance'],r['factor_descendant'])]=bool(r['CA_FLAG_0'])
    out={k:{'n':0,'source_false_target_true':0,'source_true_target_false':0,'unchanged':0} for k in ['P1_SHAM','P1_ECHO','P3_USER','P3_TOOL']}
    for c in by.values():
        pairs={'P1_SHAM':(c[('USER_ID','SHAM')],c[('TOOL_ID','SHAM')]),'P1_ECHO':(c[('USER_ID','ECHO')],c[('TOOL_ID','ECHO')]),'P3_USER':(c[('USER_ID','SHAM')],c[('USER_ID','ECHO')]),'P3_TOOL':(c[('TOOL_ID','SHAM')],c[('TOOL_ID','ECHO')])}
        for k,(s,t) in pairs.items():
            out[k]['n']+=1
            if not s and t: out[k]['source_false_target_true']+=1
            elif s and not t: out[k]['source_true_target_false']+=1
            else: out[k]['unchanged']+=1
    for v in out.values(): v['any_flip']=v['source_false_target_true']+v['source_true_target_false']; v['flip_rate']=v['any_flip']/v['n']
    return out

def action_factor(rows):
    # Groupwise contribution to CA_MARGIN = (DELETE_U - DELETE_S)/|Y|, then same factorial decomposition.
    groups=set()
    for r in rows:
        groups.update(r['action_token_factorization']['DELETE__U']); groups.update(r['action_token_factorization']['DELETE__S_REL'])
    result={}
    for g in sorted(groups):
        fake=[]
        for r in rows:
            nt=r['completion_token_count']; f=r['action_token_factorization']; val=(f['DELETE__U'].get(g,0.0)-f['DELETE__S_REL'].get(g,0.0))/nt
            rr=dict(r); rr['_group_margin']=val; fake.append(rr)
        ff=factorial(fake,'_group_margin'); ff.pop('per_base',None); result[g]=ff
    return result

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='.'); args=ap.parse_args(); root=project_root_from_args(args); out=a14_dir(root)
    protocol=read_json(out/'protocol.json') if (out/'protocol.json').exists() else None
    if not protocol or protocol.get('status')!='FROZEN_PRE_OUTCOME': raise SystemExit('FATAL protocol not frozen')
    verify_sources(root,out,protocol)
    p=out/'scorer_llama'/'condition_scores.jsonl'
    if not p.exists(): raise SystemExit('FATAL Llama scores missing')
    rows=read_jsonl(p)
    if len(rows)!=96 or len({r['condition_id'] for r in rows})!=96: raise SystemExit(f'FATAL expected 96 unique Llama condition rows, got {len(rows)}')
    primary=factorial(rows,'CA_MARGIN'); replacement=factorial(rows,'CA_MARGIN_REPLACE'); closure=factorial(rows,'closure_gap'); dU=factorial(rows,'bar_dU_fixed'); dS=factorial(rows,'bar_dS_relevant')
    result={'schema_version':SCHEMA_VERSION,'protocol_hash':protocol['protocol_hash'],'status':'PRIMARY_LLAMA_COMPLETE','primary_factorial_CA_MARGIN':primary,'binary_CA_FLAG_0':binary_edges(rows),'operator_robustness_CA_MARGIN_REPLACE':replacement,'mechanism_bar_dU_fixed':dU,'mechanism_bar_dS_relevant':dS,'mechanism_closure_gap':closure,'action_token_factorization':action_factor(rows),'claim_guardrails':protocol['claim_guardrails']}
    gp=out/'scorer_gemma'/'condition_scores.jsonl'
    if gp.exists():
        grows=read_jsonl(gp)
        if len(grows)==96:
            result['gemma_source_fidelity']={'factorial_CA_MARGIN':factorial(grows,'CA_MARGIN'),'binary_CA_FLAG_0':binary_edges(grows),'status':'SECONDARY_SOURCE_FIDELITY_COMPLETE'}
    (out/'analysis').mkdir(parents=True,exist_ok=True); dump_json(out/'analysis'/'results.json',result)
    p1=primary['P1_PROVENANCE_MAIN']; p3=primary['P3_DESCENDANT_MAIN']; inter=primary['P1xP3_INTERACTION']
    lines=['# A14 Minimal P1×P3 Factorial — Primary Analysis','',f"Protocol: `{protocol['protocol_hash']}`",'', '## Primary Llama estimands','',f"- P1 provenance main effect on CA_MARGIN: **{p1['mean']:+.6f}**, 95% paired-base bootstrap CI **[{p1['ci95'][0]:+.6f}, {p1['ci95'][1]:+.6f}]**",f"- P3 descendant main effect on CA_MARGIN: **{p3['mean']:+.6f}**, 95% paired-base bootstrap CI **[{p3['ci95'][0]:+.6f}, {p3['ci95'][1]:+.6f}]**",f"- P1×P3 interaction (secondary mechanistic): **{inter['mean']:+.6f}**, 95% CI **[{inter['ci95'][0]:+.6f}, {inter['ci95'][1]:+.6f}]**",'', 'Predicted directions: P1 < 0 and P3 < 0. Interaction direction was intentionally left open.', '', '## Binary guardrail transitions (tau=0)', '']
    for k,v in result['binary_CA_FLAG_0'].items(): lines.append(f"- {k}: flip {v['any_flip']}/{v['n']} ({v['flip_rate']:.3f}); safe→flag {v['source_false_target_true']}, flag→safe {v['source_true_target_false']}")
    lines += ['', '## Interpretation boundaries', '', '- Similar P1 and P3 effect sizes do not prove the same mechanism.', '- The interaction diagnoses redundancy/additivity/synergy but is not a proof of mechanistic identity.', '- A14M is controlled synthetic causal evidence; A13 supplies ecological evidence and A15a supplies measured operational consequence.', '- Gemma, if run, is secondary source-fidelity replication.', '']
    (out/'analysis'/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print('[A14M-04] COMPLETE'); print(f"P1={p1['mean']:+.6f} CI={p1['ci95']}"); print(f"P3={p3['mean']:+.6f} CI={p3['ci95']}"); print(f"I ={inter['mean']:+.6f} CI={inter['ci95']}"); print(f"Read: {out/'analysis'/'REPORT.md'}")

if __name__=='__main__': main()
