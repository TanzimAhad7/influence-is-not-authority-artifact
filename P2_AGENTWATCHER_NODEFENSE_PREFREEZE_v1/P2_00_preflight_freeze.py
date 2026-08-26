#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,os,sys,datetime,subprocess
from pathlib import Path
from p2_common import *

def fail(msg): raise SystemExit('P2 PREFLIGHT FAIL: '+msg)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root',default='/home/anon_/ratchet/phase0_pilot')
    ap.add_argument('--package-dir',default=None)
    ap.add_argument('--out-dir',default=None)
    args=ap.parse_args()
    root=Path(args.project_root).resolve()
    pkg=Path(args.package_dir).resolve() if args.package_dir else Path(__file__).resolve().parent
    out=Path(args.out_dir).resolve() if args.out_dir else root/'P2_AGENTWATCHER_NODEFENSE_RUN_v1'
    cfg=read_json(pkg/'P2_CONFIG.json')
    if out.exists() and any(out.iterdir()): fail(f'output directory already nonempty: {out}')
    out.mkdir(parents=True,exist_ok=True)

    # Package-selected population.
    selected=read_json(pkg/'P2_SELECTED_PAIRS.json')
    if len(selected)!=200: fail('package selected-pair count != 200')
    if canonical_hash(selected)!=cfg['selected_pairs_sha256']: fail('package selected-pair hash mismatch')

    # Historical attack freeze must be exact.
    freeze_p=root/cfg['historical_attack_freeze_path']
    if not freeze_p.exists(): fail(f'missing historical freeze: {freeze_p}')
    if sha256_file(freeze_p)!=cfg['historical_attack_freeze_sha256']: fail('historical attack freeze hash mismatch')
    fr=read_json(freeze_p)
    if fr['benchmark']['selected_pairs_sha256']!=cfg['selected_pairs_sha256']: fail('historical selected-pair SHA mismatch')
    if fr['benchmark']['selected_pairs']!=selected: fail('historical selected-pair list differs from package freeze')
    if fr['benchmark']['version']!='v1.2.2': fail('benchmark version drift')
    if fr['benchmark']['sampling_seed']!=42: fail('sampling seed drift')
    if fr['agent']['requested_model']!='gpt-4o-mini': fail('historical requested model drift')

    # Full frozen AgentDojo/runtime critical byte manifest.
    rt_rows=read_tsv(pkg/'P2_RUNTIME_MANIFEST.tsv')
    rt_fail=[]
    for r in rt_rows:
        p=root/r['relative_path']
        if not p.exists(): rt_fail.append((r['relative_path'],'MISSING'))
        elif p.stat().st_size!=int(r['bytes']): rt_fail.append((r['relative_path'],'SIZE'))
        elif sha256_file(p)!=r['sha256']: rt_fail.append((r['relative_path'],'SHA'))
    if rt_fail: fail(f'runtime manifest mismatch: {rt_fail[:8]} total={len(rt_fail)}')

    # Historical defense-on attack rows are immutable analysis inputs.
    hm=read_tsv(pkg/'P2_HISTORICAL_DEFENSE_ON_MANIFEST.tsv')
    if len(hm)!=200: fail('historical defense-on manifest count != 200')
    for r in hm:
        p=root/r['relative_path']
        if not p.exists() or p.stat().st_size!=int(r['bytes']) or sha256_file(p)!=r['sha256']:
            fail(f'historical defense-on row drift: {r["relative_path"]}')

    ref=[]
    with (pkg/'P2_DEFENSE_ON_REFERENCE.csv').open(newline='') as f: ref=list(csv.DictReader(f))
    if len(ref)!=200: fail('historical reference CSV count != 200')
    if sum(int(x['defense_on_utility']) for x in ref)!=56: fail('historical utility no longer 56/200')
    if sum(int(x['defense_on_attack_success']) for x in ref)!=0: fail('historical ASR no longer 0/200')
    ref_keys={(x['suite'],x['user_task_id'],x['injection_task_id']) for x in ref}
    sel_keys={(x['suite'],x['user_task_id'],x['injection_task_id']) for x in selected}
    if ref_keys!=sel_keys: fail('reference pair set mismatch')

    # Historical log is provenance, not an analysis input, but must still match.
    lp=root/cfg['historical_defense_on_log']
    if not lp.exists() or sha256_file(lp)!=cfg['historical_defense_on_log_sha256']: fail('historical author log drift/missing')

    runtime=root/cfg['runtime_root']
    result_root=runtime/'results/agent_evaluations/agentdojo'/cfg['result_name']
    if result_root.exists(): fail(f'P2 raw result directory already exists: {result_root}; start clean')

    # API credential check; never persist the secret.
    has_openai=bool(os.environ.get('OPENAI_API_KEY'))
    has_openrouter=bool(os.environ.get('OPENROUTER_API_KEY'))
    if not (has_openai or has_openrouter): fail('neither OPENAI_API_KEY nor OPENROUTER_API_KEY is set')

    # Git head is recorded when available; byte manifest is the authoritative runtime lock.
    git_head=None
    try:
        git_head=subprocess.check_output(['git','-C',str(runtime),'rev-parse','HEAD'],text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: pass

    freeze={
      'schema':'P2_SCIENCE_FREEZE_V1_2026-08-12',
      'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'scientific_status':'PRE_OUTCOME_FREEZE',
      'project_root':str(root),
      'package_dir':str(pkg),
      'runtime_root':str(runtime),
      'runtime_git_head_if_available':git_head,
      'runtime_manifest_sha256':sha256_file(pkg/'P2_RUNTIME_MANIFEST.tsv'),
      'historical_defense_on_manifest_sha256':sha256_file(pkg/'P2_HISTORICAL_DEFENSE_ON_MANIFEST.tsv'),
      'historical_reference_sha256':sha256_file(pkg/'P2_DEFENSE_ON_REFERENCE.csv'),
      'selected_pairs_sha256':cfg['selected_pairs_sha256'],
      'selected_pair_count':200,
      'historical_defense_on_utility_true':56,
      'historical_defense_on_attack_success_true':0,
      'requested_model':cfg['requested_model'],
      'provider_route':cfg['provider_route'],
      'openai_base_url':cfg['openai_base_url'],
      'attack':cfg['attack'],
      'defense':'none',
      'benchmark_version':cfg['benchmark_version'],
      'sample_size':200,
      'sampling_seed':42,
      'primary_estimand':cfg['primary_estimand'],
      'primary_uncertainty':cfg['primary_uncertainty'],
      'claim_boundary':cfg['claim_boundary'],
      'credential_present':True,
      'outcome_fields_seen_before_freeze':False,
    }
    write_json(out/'P2_SCIENCE_FREEZE.json',freeze)
    md=f"""# P2 Science Freeze\n\n- status: **PRE-OUTCOME FREEZE PASS**\n- exact frozen pairs: `200`\n- selected-pair SHA: `{cfg['selected_pairs_sha256']}`\n- historical AgentWatcher utility: `56/200`\n- historical AgentWatcher ASR: `0/200`\n- P2 change: `defense=agentwatcher` → `defense=none` only\n- attack: `tool_knowledge`\n- model: `gpt-4o-mini`\n- route: OpenRouter OpenAI-compatible\n- benchmark: AgentDojo `v1.2.2`\n- uncertainty: 20,000-draw cluster bootstrap by `(suite,user_task_id)`, seed `20260812`\n- no P2 scientific outcomes existed when this freeze was written.\n"""
    (out/'P2_SCIENCE_FREEZE.md').write_text(md)
    # Freeze package/config input hashes for audit.
    rows=[]
    for name in ['P2_CONFIG.json','P2_PROTOCOL_FREEZE.md','P2_SELECTED_PAIRS.json','P2_DEFENSE_ON_REFERENCE.csv','P2_HISTORICAL_DEFENSE_ON_MANIFEST.tsv','P2_RUNTIME_MANIFEST.tsv','P2_00_preflight_freeze.py','P2_01_run_nodefense.py','P2_02_analyze.py','P2_03_verify.py','p2_common.py','RUN_P2.sh','PACKAGE_SHA256.txt']:
        p=pkg/name
        if p.exists(): rows.append((name,sha256_file(p),p.stat().st_size))
    with (out/'P2_PREFREEZE_PACKAGE_MANIFEST.tsv').open('w',newline='') as f:
        w=csv.writer(f,delimiter='\t',lineterminator='\n'); w.writerow(['package_file','sha256','bytes']); w.writerows(rows)
    print('P2 PRE-OUTCOME FREEZE PASS')
    print('selected_pairs=200')
    print('selected_pairs_sha256='+cfg['selected_pairs_sha256'])
    print('historical_defense_on_utility=56/200')
    print('historical_defense_on_asr=0/200')
    print('defense_change=agentwatcher->none')

if __name__=='__main__': main()
