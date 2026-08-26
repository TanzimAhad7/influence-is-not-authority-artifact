#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

EXPECTED = {
    'llama': {
        'condition_scores_sha256': '1c2ee74880a4a74d2bbfad06a6fad4e0f8c09a0fd474d8a0a9a7e43f5fb91111',
        'n_conditions': 96,
        'model': 'meta-llama/Llama-3.3-70B-Instruct'
    },
    'gemma': {
        'condition_scores_sha256': 'edbf606d112410e50ff260e63d7008470c5299ddabfd43188ed7d942c42ec0fa',
        'n_conditions': 96,
        'model': 'google/gemma-3-12b-it'
    }
}
EXPECTED_PROTOCOL_HASH='94bb3c7e0ca174aa8be69b8c0949e7d93a567d960a9ba06016ba4d08f8503ee1'


def sha256(p: Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()


def load_jsonl(p: Path):
    rows=[]
    with p.open(encoding='utf-8') as f:
        for i,line in enumerate(f,1):
            if not line.strip(): continue
            try: rows.append(json.loads(line))
            except Exception as e: raise RuntimeError(f'JSONL parse failure {p}:{i}: {e}')
    return rows


def token_ids_from_raw(choice_logprobs, n):
    toks=choice_logprobs.get('tokens') or []
    tail=toks[-n:]
    ids=[]
    for t in tail:
        if not isinstance(t,str) or not t.startswith('token_id:'):
            return None
        ids.append(int(t.split(':',1)[1]))
    return ids


def audit_scorer(d: Path, label: str):
    exp=EXPECTED[label]
    required=['condition_scores.jsonl','RUN_COMPLETE.json','raw_responses.jsonl']
    missing=[n for n in required if not (d/n).exists()]
    if missing:
        return {'label':label,'directory':str(d),'status':'MISSING_REQUIRED_FILES','missing':missing}

    score_p=d/'condition_scores.jsonl'; run_p=d/'RUN_COMPLETE.json'; raw_p=d/'raw_responses.jsonl'
    run=json.loads(run_p.read_text())
    scores=load_jsonl(score_p)
    score_sha=sha256(score_p)
    authoritative_ok=(score_sha==exp['condition_scores_sha256']==run.get('condition_scores_sha256') and
                      len(scores)==exp['n_conditions']==run.get('n_conditions') and
                      run.get('protocol_hash')==EXPECTED_PROTOCOL_HASH and run.get('model')==exp['model'])
    raw_parse_ok=True
    try: raw=load_jsonl(raw_p)
    except Exception as e:
        raw_parse_ok=False; raw=[]; raw_error=str(e)
    if not raw_parse_ok:
        return {'label':label,'directory':str(d),'status':'RAW_PARSE_FAIL','raw_error':raw_error,'authoritative_condition_scores_ok':authoritative_ok}

    score_conditions={r['condition_id'] for r in scores}
    raw_conditions={r.get('condition_id') for r in raw}
    raw_keys=[r.get('cache_key') for r in raw]
    basic_complete=(len(score_conditions)==96 and raw_conditions==score_conditions and None not in raw_conditions and None not in raw_keys and len(raw_keys)==len(set(raw_keys)))

    aux={}
    for name in ['raw_requests.jsonl','score_cache.jsonl']:
        p=d/name
        aux[name]={'present':p.exists()}
        if p.exists():
            rows=load_jsonl(p); aux[name].update({'rows':len(rows),'sha256':sha256(p),'cache_keys':len({r.get('cache_key') for r in rows})})
    deep_ok=None; deep_checks={}
    if (d/'raw_requests.jsonl').exists() and (d/'score_cache.jsonl').exists():
        req=load_jsonl(d/'raw_requests.jsonl'); cache=load_jsonl(d/'score_cache.jsonl')
        kr={r['cache_key'] for r in raw}; kq={r['cache_key'] for r in req}; kc={r['cache_key'] for r in cache}
        cachemap={r['cache_key']:r['score'] for r in cache}
        response_matches=0; response_fail=[]
        for r in raw:
            key=r['cache_key']; s=cachemap.get(key)
            if s is None:
                response_fail.append([key,'missing score cache']); continue
            try:
                lp=r['response']['choices'][0]['logprobs']
                n=int(s['completion_token_count'])
                tail=[float(x) for x in lp['token_logprobs'][-n:]]
                expected_lp=[float(x) for x in s['completion_token_logprobs']]
                ids=token_ids_from_raw(lp,n)
                ok=(len(tail)==n==len(expected_lp) and all(abs(a-b)<=1e-12 for a,b in zip(tail,expected_lp)) and
                    abs(sum(tail)-float(s['sum_logprob']))<=1e-10 and ids==[int(x) for x in s['completion_token_ids']])
                if ok: response_matches+=1
                else: response_fail.append([key,'raw response completion logprobs/token IDs do not match score cache'])
            except Exception as e:
                response_fail.append([key,str(e)])
        deep_ok=(kr==kq==kc and response_matches==len(raw) and not response_fail)
        deep_checks={'raw_key_count':len(kr),'request_key_count':len(kq),'cache_key_count':len(kc),'key_sets_equal':kr==kq==kc,
                     'raw_response_to_score_cache_exact_matches':response_matches,'raw_response_to_score_cache_failures':response_fail[:10]}

    counts=Counter(r['ablation_id'] for r in raw)
    status='COMPLETE_RECOVERED_RAW_LEDGER' if (authoritative_ok and basic_complete and deep_ok is True) else 'PROVENANCE_REVIEW_REQUIRED'
    return {
        'label':label,'directory':str(d),'status':status,
        'authoritative_condition_scores_ok':authoritative_ok,
        'condition_scores_sha256':score_sha,'condition_score_rows':len(scores),
        'run_complete_sha256':sha256(run_p),'raw_responses_sha256':sha256(raw_p),'raw_responses_bytes':raw_p.stat().st_size,
        'raw_response_rows':len(raw),'raw_condition_count':len(raw_conditions),'raw_conditions_match_96_scores':raw_conditions==score_conditions,
        'raw_unique_cache_keys':len(set(raw_keys)),'ablation_counts':dict(sorted(counts.items())),
        'auxiliary_ledgers':aux,'deep_reconciliation_ok':deep_ok,'deep_checks':deep_checks
    }


def find_scorer_dir(root: Path, label: str):
    exact=root/'a14_minimal_factorial'/f'scorer_{label}'
    if exact.exists(): return exact
    candidates=[p for p in root.rglob(f'scorer_{label}') if p.is_dir() and (p/'condition_scores.jsonl').exists()]
    if len(candidates)==1: return candidates[0]
    if not candidates: raise RuntimeError(f'No scorer_{label} directory found under {root}')
    raise RuntimeError(f'Ambiguous scorer_{label} directories: '+', '.join(map(str,candidates)))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',required=True); ap.add_argument('--out-dir',required=True); args=ap.parse_args()
    root=Path(args.project_root).resolve(); out=Path(args.out_dir).resolve(); out.mkdir(parents=True,exist_ok=True)
    audits=[]
    for lab in ['llama','gemma']:
        d=find_scorer_dir(root,lab); audits.append(audit_scorer(d,lab))
    all_complete=all(a['status']=='COMPLETE_RECOVERED_RAW_LEDGER' for a in audits)
    result={'schema':'A14_RAW_RESPONSE_RECOVERY_AUDIT_V1','created_at_utc':datetime.now(timezone.utc).isoformat(),
            'scientific_model_calls':0,'project_root':str(root),'status':'A14_AR_COMPLETE' if all_complete else 'A14_AR_DISCLOSURE_OR_RECOVERY_STILL_REQUIRED',
            'scorers':audits,
            'claim_boundary':'This is a provenance-only zero-call audit. It does not alter condition_scores.jsonl, RUN_COMPLETE.json, or any frozen A14 scientific result.'}
    (out/'A14_AR_AUDIT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    lines=['# A14-AR raw-response provenance audit','',f"**Status:** {result['status']} / 0 scientific model calls.",'']
    for a in audits:
        lines += [f"## {a['label']}",f"- status: `{a['status']}`",f"- authoritative condition-score ledger valid: `{a.get('authoritative_condition_scores_ok')}`",
                  f"- condition-score SHA-256: `{a.get('condition_scores_sha256')}`",f"- raw rows: `{a.get('raw_response_rows')}`",f"- raw bytes: `{a.get('raw_responses_bytes')}`",
                  f"- raw SHA-256: `{a.get('raw_responses_sha256')}`",f"- 96/96 condition coverage: `{a.get('raw_conditions_match_96_scores')}`",
                  f"- deep raw→score-cache reconciliation: `{a.get('deep_reconciliation_ok')}`",'']
    if all_complete:
        lines += ['The available raw-response ledgers are complete, parseable, cover all 96 authoritative conditions per scorer, and reconcile to the immutable score/cache provenance. Archive these exact copies and hashes; no A14 scientific rerun is warranted.']
    else:
        lines += ['Do not rerun science merely to fill provenance. Preserve any truncated copies explicitly and disclose them unless complete originals are recovered.']
    (out/'A14_AR_REPORT.md').write_text('\n'.join(lines)+'\n')
    hashes=[]
    for name in ['A14_AR_AUDIT.json','A14_AR_REPORT.md']:
        hashes.append(f'{sha256(out/name)}  {name}')
    (out/'A14_AR_FINAL_SHA256.txt').write_text('\n'.join(hashes)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
