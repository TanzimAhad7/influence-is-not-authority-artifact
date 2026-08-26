#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,random,math,statistics
from pathlib import Path
from collections import defaultdict,Counter
from p2_common import *

def percentile(xs,q):
    xs=sorted(xs)
    if not xs: return float('nan')
    pos=(len(xs)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi: return xs[lo]
    return xs[lo]*(hi-pos)+xs[hi]*(pos-lo)

def cluster_bootstrap(rows, field, draws=20000, seed=20260812):
    clusters=defaultdict(list)
    for r in rows: clusters[(r['suite'],r['user_task_id'])].append(float(r[field]))
    keys=sorted(clusters); rng=random.Random(seed); vals=[]
    for _ in range(draws):
        sampled=[keys[rng.randrange(len(keys))] for __ in keys]
        pool=[]
        for k in sampled: pool.extend(clusters[k])
        vals.append(sum(pool)/len(pool))
    return percentile(vals,.025),percentile(vals,.975)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--project-root',default='/home/anon_/ratchet/phase0_pilot'); ap.add_argument('--package-dir',default=None); ap.add_argument('--out-dir',default=None)
    args=ap.parse_args(); root=Path(args.project_root).resolve(); pkg=Path(args.package_dir).resolve() if args.package_dir else Path(__file__).resolve().parent; out=Path(args.out_dir).resolve() if args.out_dir else root/'P2_AGENTWATCHER_NODEFENSE_RUN_v1'
    cfg=read_json(pkg/'P2_CONFIG.json')
    if not (out/'P2_RUN_COMPLETE.json').exists(): raise SystemExit('missing P2_RUN_COMPLETE.json')
    # Verify raw manifest before analysis.
    for r in read_tsv(out/'P2_RAW_RESULT_MANIFEST.tsv'):
        p=out/r['relative_path']
        if not p.exists() or p.stat().st_size!=int(r['bytes']) or sha256_file(p)!=r['sha256']: raise SystemExit('raw result drift: '+r['relative_path'])

    ref={}
    with (pkg/'P2_DEFENSE_ON_REFERENCE.csv').open(newline='') as f:
        for x in csv.DictReader(f): ref[(x['suite'],x['user_task_id'],x['injection_task_id'])]=x
    new={}
    injection_user_rows=[]
    for p in (out/'raw_results').rglob('*.json'):
        d=read_json(p)
        if d.get('attack_type')=='tool_knowledge': new[(d['suite_name'],d['user_task_id'],d['injection_task_id'])]=d
        elif d.get('attack_type') is None and d.get('injection_task_id') is None: injection_user_rows.append(d)
    if len(new)!=200 or set(new)!=set(ref): raise SystemExit('analysis pair population mismatch')

    rows=[]
    for k in sorted(ref):
        h=ref[k]; n=new[k]
        rows.append({'suite':k[0],'user_task_id':k[1],'injection_task_id':k[2],
                     'defense_on_utility':int(h['defense_on_utility']),'no_defense_utility':int(bool(n['utility'])),
                     'delta_utility':int(bool(n['utility']))-int(h['defense_on_utility']),
                     'defense_on_attack_success':int(h['defense_on_attack_success']),'no_defense_attack_success':int(bool(n['security'])),
                     'delta_attack_success':int(bool(n['security']))-int(h['defense_on_attack_success'])})
    n=len(rows)
    hU=sum(r['defense_on_utility'] for r in rows); nU=sum(r['no_defense_utility'] for r in rows)
    hA=sum(r['defense_on_attack_success'] for r in rows); nA=sum(r['no_defense_attack_success'] for r in rows)
    dU=sum(r['delta_utility'] for r in rows)/n; dA=sum(r['delta_attack_success'] for r in rows)/n
    ciU=cluster_bootstrap(rows,'delta_utility',cfg['primary_uncertainty']['draws'],cfg['primary_uncertainty']['seed'])
    ciA=cluster_bootstrap(rows,'delta_attack_success',cfg['primary_uncertainty']['draws'],cfg['primary_uncertainty']['seed'])
    if ciU[0]>0: verdict='MATCHED_INPUT_DEFENSE_OVERHEAD_SUPPORTED'
    elif ciU[1]<0: verdict='NO_DEFENSE_LOWER_UTILITY'
    else: verdict='DEFENSE_OVERHEAD_NOT_ESTABLISHED'
    ugain=sum(r['defense_on_utility']==0 and r['no_defense_utility']==1 for r in rows)
    uloss=sum(r['defense_on_utility']==1 and r['no_defense_utility']==0 for r in rows)
    againt=sum(r['defense_on_attack_success']==0 and r['no_defense_attack_success']==1 for r in rows)
    aloss=sum(r['defense_on_attack_success']==1 and r['no_defense_attack_success']==0 for r in rows)
    suites={}
    for s in sorted({r['suite'] for r in rows}):
        rr=[r for r in rows if r['suite']==s]; m=len(rr)
        suites[s]={'n':m,'defense_on_utility_true':sum(x['defense_on_utility'] for x in rr),'no_defense_utility_true':sum(x['no_defense_utility'] for x in rr),'delta_utility':sum(x['delta_utility'] for x in rr)/m,'defense_on_attack_success_true':sum(x['defense_on_attack_success'] for x in rr),'no_defense_attack_success_true':sum(x['no_defense_attack_success'] for x in rr)}
    inj_pass=sum(bool(x.get('utility')) for x in injection_user_rows)
    result={'schema':'P2_ANALYSIS_V1_2026-08-12','primary_verdict':verdict,'n_pairs':n,'n_clusters':len({(r['suite'],r['user_task_id']) for r in rows}),
      'utility':{'historical_agentwatcher_true':hU,'historical_agentwatcher_rate':hU/n,'no_defense_true':nU,'no_defense_rate':nU/n,'delta_no_def_minus_agentwatcher':dU,'cluster_bootstrap_95ci':[ciU[0],ciU[1]],'discordance':{'agentwatcher0_nodef1':ugain,'agentwatcher1_nodef0':uloss}},
      'attack_success':{'historical_agentwatcher_true':hA,'historical_agentwatcher_rate':hA/n,'no_defense_true':nA,'no_defense_rate':nA/n,'delta_no_def_minus_agentwatcher':dA,'cluster_bootstrap_95ci':[ciA[0],ciA[1]],'discordance':{'agentwatcher0_nodef1':againt,'agentwatcher1_nodef0':aloss}},
      'injection_tasks_as_user_tasks_secondary':{'rows':len(injection_user_rows),'utility_true':inj_pass},'suite_breakdown':suites,
      'claim_boundary':cfg['claim_boundary'],'interpretation_rule':cfg['interpretation_rule']}
    write_json(out/'P2_ANALYSIS.json',result)
    with (out/'P2_PAIRED_ROWS.csv').open('w',newline='') as f:
        fields=list(rows[0]); w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    with (out/'P2_SUITE_SUMMARY.csv').open('w',newline='') as f:
        fields=['suite','n','defense_on_utility_true','no_defense_utility_true','delta_utility','defense_on_attack_success_true','no_defense_attack_success_true']; w=csv.DictWriter(f,fieldnames=fields); w.writeheader();
        for s,z in suites.items(): w.writerow({'suite':s,**z})
    md=f"""# P2 AgentWatcher Same-200 Defense-Disabled Result\n\n**Primary verdict:** `{verdict}`\n\n## Utility\n\n- historical AgentWatcher: `{hU}/200 = {hU/n:.1%}`\n- no defense: `{nU}/200 = {nU/n:.1%}`\n- matched-input difference (no-defense − AgentWatcher): `{dU*100:+.2f}` percentage points\n- cluster-bootstrap 95% CI: `[{ciU[0]*100:+.2f}, {ciU[1]*100:+.2f}]` pp\n- discordance: AgentWatcher fail → no-defense pass `{ugain}`; AgentWatcher pass → no-defense fail `{uloss}`\n\n## Attack success\n\n- historical AgentWatcher: `{hA}/200 = {hA/n:.1%}`\n- no defense: `{nA}/200 = {nA/n:.1%}`\n- difference: `{dA*100:+.2f}` pp\n- cluster-bootstrap 95% CI: `[{ciA[0]*100:+.2f}, {ciA[1]*100:+.2f}]` pp\n\n## Scope qualification\n\n{cfg['claim_boundary']}\n\nDo not convert this matched-input comparison into a stronger causal claim than the frozen design supports.\n"""
    (out/'P2_ANALYSIS.md').write_text(md)
    print('P2 ANALYSIS COMPLETE')
    print('primary_verdict='+verdict)
    print(f'historical_utility={hU}/200')
    print(f'no_defense_utility={nU}/200')
    print(f'delta_utility_pp={dU*100:+.4f}')
    print(f'delta_utility_ci95_pp=[{ciU[0]*100:+.4f},{ciU[1]*100:+.4f}]')
    print(f'historical_asr={hA}/200')
    print(f'no_defense_asr={nA}/200')

if __name__=='__main__': main()
