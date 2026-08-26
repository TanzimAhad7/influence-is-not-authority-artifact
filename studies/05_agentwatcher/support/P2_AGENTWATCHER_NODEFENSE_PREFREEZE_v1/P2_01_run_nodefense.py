#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime,json,os,shutil,subprocess,sys,csv
from pathlib import Path
from p2_common import *

def fail(msg): raise SystemExit('P2 RUN FAIL: '+msg)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--project-root',default='/home/anon_/ratchet/phase0_pilot')
    ap.add_argument('--package-dir',default=None)
    ap.add_argument('--out-dir',default=None)
    args=ap.parse_args()
    root=Path(args.project_root).resolve(); pkg=Path(args.package_dir).resolve() if args.package_dir else Path(__file__).resolve().parent
    out=Path(args.out_dir).resolve() if args.out_dir else root/'P2_AGENTWATCHER_NODEFENSE_RUN_v1'
    cfg=read_json(pkg/'P2_CONFIG.json')
    sf=out/'P2_SCIENCE_FREEZE.json'
    if not sf.exists(): fail('missing P2_SCIENCE_FREEZE.json; run preflight first')
    fr=read_json(sf)
    if fr.get('scientific_status')!='PRE_OUTCOME_FREEZE' or fr.get('outcome_fields_seen_before_freeze') is not False: fail('invalid pre-outcome freeze')
    if fr.get('selected_pairs_sha256')!=cfg['selected_pairs_sha256']: fail('freeze selected-pair mismatch')

    # Re-check package/input manifests immediately before first scientific call.
    for r in read_tsv(pkg/'P2_RUNTIME_MANIFEST.tsv'):
        p=root/r['relative_path']
        if not p.exists() or p.stat().st_size!=int(r['bytes']) or sha256_file(p)!=r['sha256']: fail('runtime drift before science: '+r['relative_path'])
    for r in read_tsv(pkg/'P2_HISTORICAL_DEFENSE_ON_MANIFEST.tsv'):
        p=root/r['relative_path']
        if not p.exists() or p.stat().st_size!=int(r['bytes']) or sha256_file(p)!=r['sha256']: fail('historical reference drift before science: '+r['relative_path'])

    runtime=root/cfg['runtime_root']
    rawroot=runtime/'results/agent_evaluations/agentdojo'/cfg['result_name']
    if rawroot.exists(): fail(f'raw P2 result directory already exists: {rawroot}')
    dest=out/'raw_results'
    if dest.exists(): fail(f'packaged raw_results already exists: {dest}')

    env=os.environ.copy()
    if not env.get('OPENAI_API_KEY') and env.get('OPENROUTER_API_KEY'):
        env['OPENAI_API_KEY']=env['OPENROUTER_API_KEY']
    if not env.get('OPENAI_API_KEY'): fail('OPENAI_API_KEY/OPENROUTER_API_KEY absent')
    env['OPENAI_BASE_URL']=cfg['openai_base_url']
    # Explicitly prevent accidental PIArena/AgentWatcher activation inherited from shell.
    env.pop('PIARENA_DEFENSE',None)
    env.pop('PIARENA_MONITOR_LLM',None)
    env.pop('PIARENA_ATTRIBUTION_MODEL',None)

    cmd=[sys.executable,'-u',str(runtime/'main_agentdojo.py'),
         '--model',cfg['requested_model'],
         '--attack','tool_knowledge',
         '--defense','none',
         '--sample_size','200',
         '--name',cfg['result_name']]
    print('P2 SCIENCE START')
    print('command='+' '.join(cmd))
    print('OPENAI_BASE_URL='+cfg['openai_base_url'])
    print('credential_source='+('OPENROUTER_API_KEY' if os.environ.get('OPENROUTER_API_KEY') and not os.environ.get('OPENAI_API_KEY') else 'OPENAI_API_KEY'))
    start=datetime.datetime.now(datetime.timezone.utc)
    rc=subprocess.call(cmd,cwd=str(runtime),env=env)
    end=datetime.datetime.now(datetime.timezone.utc)
    if rc!=0: fail(f'AgentDojo exited {rc}')
    if not rawroot.exists(): fail('AgentDojo returned success but raw result root is absent')

    selected=read_json(pkg/'P2_SELECTED_PAIRS.json')
    exp={(x['suite'],x['user_task_id'],x['injection_task_id']) for x in selected}
    attack_rows=[]; all_json=[]
    for p in sorted(rawroot.rglob('*.json')):
        d=read_json(p); all_json.append((p,d))
        if d.get('attack_type')=='tool_knowledge': attack_rows.append((p,d))
    if len(attack_rows)!=200: fail(f'expected exactly 200 tool_knowledge result rows, got {len(attack_rows)}')
    got={(d['suite_name'],d['user_task_id'],d['injection_task_id']) for _,d in attack_rows}
    if got!=exp: fail('actual P2 pair set differs from frozen 200; outcome invalid')
    if any(d.get('error') is not None for _,d in attack_rows): fail('one or more P2 attack rows contains an error')

    # Copy immutable raw output tree into isolated P2 provenance dir only after population validation.
    shutil.copytree(rawroot,dest)
    manifest=[]
    for p in sorted(dest.rglob('*.json')):
        manifest.append((str(p.relative_to(out)),sha256_file(p),p.stat().st_size))
    with (out/'P2_RAW_RESULT_MANIFEST.tsv').open('w',newline='') as f:
        w=csv.writer(f,delimiter='\t',lineterminator='\n'); w.writerow(['relative_path','sha256','bytes']); w.writerows(manifest)
    runrec={
      'schema':'P2_RUN_COMPLETE_V1_2026-08-12','status':'SCIENCE_COMPLETE_UNANALYZED',
      'started_at_utc':start.isoformat(),'ended_at_utc':end.isoformat(),'returncode':rc,
      'requested_model':cfg['requested_model'],'provider_route':cfg['provider_route'],'openai_base_url':cfg['openai_base_url'],
      'attack':'tool_knowledge','defense':'none','sample_size':200,'sampling_seed':42,
      'selected_pairs_sha256':cfg['selected_pairs_sha256'],'tool_knowledge_rows':len(attack_rows),'all_json_rows':len(all_json),
      'raw_result_manifest_sha256':sha256_file(out/'P2_RAW_RESULT_MANIFEST.tsv'),
      'raw_external_result_root':str(rawroot),'packaged_raw_result_root':str(dest),
    }
    write_json(out/'P2_RUN_COMPLETE.json',runrec)
    print('P2 SCIENCE COMPLETE')
    print('tool_knowledge_rows=200')
    print('pair_set_exact_match=PASS')
    print('raw_result_manifest_sha256='+runrec['raw_result_manifest_sha256'])

if __name__=='__main__': main()
